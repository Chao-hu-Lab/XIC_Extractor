# Peak Scoring Redesign — Tier-Based Confidence with ΔRT Anchoring

**Date:** 2026-04-20
**Status:** Design (pending implementation plan)
**Author:** brainstorming session (user + Claude)

---

## 1. Problem Statement

The current peak-picking logic (`xic_extractor/signal_processing.py :: _select_candidate`)
chooses peaks using only two signals: **intensity** and **distance to a single-sample
`preferred_rt`**. It also has a binary notion of success — a candidate either passes
`find_peak_candidates` and is kept, or it fails and is dropped.

This works on clean tissue samples (DNA-adduct assay, 85 samples, ISTD RT σ < 0.2 min
for most internal standards) but degrades badly on dirty urine matrices:

- True peaks are dropped because their absolute intensity is low vs. matrix noise humps.
- Asymmetric but real peaks lose to taller but spurious peaks in `max(intensity)`.
- There is no way to rescue borderline peaks that a human analyst would accept
  (example urine samples 2286 at RT 9.07, 2287 at RT 9.01).

Two secondary issues surfaced during design review:

- `d3-N6-medA` has bimodal RT distribution in the tissue batch
  (`tumor ≈ 24 min`, `normal ≈ 26 min`). This was initially attributed to
  matrix effect, but `SampleInfo.xlsx` shows the run was a **block run**
  (tumor = injections 2–35, normal = injections 36–64, benign fat = 70–90).
  The RT shift is almost certainly **column drift by injection order**, not
  biology. Any design that groups RT priors by `sample_groups` would bake
  column drift into the prior as if it were a group-level signal.
- There is no mechanism to carry over knowledge across batches.

## 2. Goals

1. Make selection robust to dirty matrix without rejecting borderline real peaks.
2. Output every candidate with a **confidence label** and a **human-readable reason**,
   never auto-reject.
3. Anchor RT priors to signals that survive **column drift** (ΔRT to paired ISTD,
   injection-order rolling medians), not to group labels that correlate with
   drift.
4. Let the prior strengthen over time via an optional external library keyed on a
   config fingerprint.
5. Keep the main Excel output readable for a non-programmer analyst. Heavy
   diagnostics go to a secondary sheet that is off by default.
6. Implement in two regression-guarded stages: tissue first, urine second.

## 3. Non-Goals (for this spec)

- Isotope-pattern support (e.g., M+1, M+2 consistency). Schema may leave room but
  the scoring signal is deferred.
- Co-eluting interference detection beyond local baseline/noise checks.
- Automatic weight learning from labelled data.
- Rewriting peak detection itself (`find_peak_candidates` stays; only selection
  and post-hoc scoring change).

## 4. Key Design Decisions

### 4.1 Abandon group-level RT consensus

The `sample_groups` column (tumor / normal / QC / benign fat / urine / tissue)
correlates with injection block in the production batches we have. Using it as
the grouping key for RT consensus would make column drift look like a biological
signal. The group column is **kept for reporting and summary statistics** only.

### 4.2 Primary RT prior: ΔRT (analyte RT − paired ISTD RT)

For every analyte with an `istd_pair`, the primary RT prior is the **difference**
between its RT and the RT of its paired ISTD **in the same sample**.
Because ISTD and analyte co-elute under the same conditions, ΔRT is largely
invariant to column aging. The library stores ΔRT (per analyte × config
fingerprint), not absolute RT.

### 4.3 Secondary RT prior for ISTDs: injection-order rolling median

ISTDs themselves have no "paired ISTD" to anchor against. For an ISTD in
sample at injection order *i*, the absolute-RT prior is the median RT of the
same ISTD in samples with injection order in `[i − W, i + W]`, where `W`
defaults to 5. This uses time-local neighbours regardless of sample group,
so it adapts to column drift rather than treating it as a group property.

Fallbacks, in order:

1. Rolling window (need ≥ 3 samples inside the window).
2. Whole-batch median (need ≥ 3 samples total).
3. External RT prior library lookup (must match `config_hash`).
4. `rt_min + rt_max)/2` as last resort.

### 4.4 Injection-order source

The `SampleInfo.xlsx`-style metadata provides `Sample_Name → Injection_Order`.
The settings file gains:

- `injection_order_source: <path>` — optional path to a CSV/XLSX with columns
  `Sample_Name`, `Injection_Order`.
- When not provided, fall back to RAW file modification time as a proxy, with
  a warning in Diagnostics that the rolling window may be unreliable.

### 4.5 Tier-based scoring, no weights, no auto-reject

Seven signals, each emitting severity `0` (PASS) / `1` (MINOR) / `2` (MAJOR):

| # | Signal | Physical meaning | MAJOR (2) typically | MINOR (1) typically |
|---|---|---|---|---|
| 1 | symmetry | left/right half-width ratio | ratio < 0.3 or > 3.0 | < 0.5 or > 2.0 |
| 2 | local_SN | peak height vs. local baseline (AsLS/SNIP) residual MAD | < 2× | < 3× |
| 3 | nl_support | MS2 neutral-loss evidence | MS2 present but no NL | no MS2 present at all |
| 4 | rt_prior | deviation from ΔRT prior (or ISTD rolling prior) | > 5σ or > 1 min when no σ | > 2σ |
| 5 | rt_centrality | distance to rt_min/rt_max window edges | within 1 % of boundary | within 10 % |
| 6 | noise_shape | jaggedness / ragged index of peak region | > 0.5 | > 0.3 |
| 7 | peak_width | FWHM ratio vs. paired ISTD FWHM | ratio < 0.3 or > 3.0 | < 0.5 or > 2.0 |

**No HARD-FAIL.** Every candidate is reported.

**No weights, no profile presets.** Severity thresholds are physical and
individually tunable.

**Confidence label from total severity:**

| Total severity | Confidence |
|---|---|
| 0 | HIGH |
| 1–2 | MEDIUM |
| 3–4 | LOW |
| 5+ | VERY_LOW |

### 4.6 Multiple-candidate selection rule

When more than one candidate survives `find_peak_candidates`:

1. Sort by Confidence (HIGH > MEDIUM > LOW > VERY_LOW).
2. Tie-break by distance to RT prior (ΔRT prior for analytes, rolling median
   for ISTDs).
3. Final tie-break by smoothed apex intensity.

### 4.7 Special handling for `nl_support`

Three states, not two:

- **MS2 present and NL match** → severity 0.
- **MS2 present but no NL** → severity 2 (actively suspicious).
- **No MS2 triggered at this RT** → severity 1 (unknown, modest penalty).

This prevents systematically penalising low-abundance true peaks that DDA
failed to trigger on.

### 4.8 Baseline estimator for `local_SN`

Replace MAD-of-raw-trace with **Asymmetric Least Squares (AsLS)** or **SNIP**
baseline estimation. MAD is then computed on the residual (trace − baseline)
in a window around the peak. This handles structured urine baseline humps
(urea / creatinine adducts) that make MAD-only estimates underestimate noise
and overestimate S/N.

### 4.9 ISTD Confidence propagation to analytes

When an analyte uses an anchor from its paired ISTD, the ISTD's Confidence
label is propagated into the analyte's Reason string:

```
concerns: rt_prior (minor); ISTD anchor was LOW
```

This ensures a reviewer reading the analyte row alone knows the anchor itself
was suspect, without having to cross-reference ISTD rows.

### 4.10 Dirty-matrix operator flag

Optional settings flag `dirty_matrix_mode: bool`. When on:

- `local_SN` MAJOR threshold relaxed from `< 2×` to `< 1.3×`.
- `symmetry` and `peak_width` severity thresholds tightened (since shape
  becomes the main evidence when S/N drops).
- `rt_prior` kept strict (drift-corrected priors are still reliable).

The flag is an operator decision ("I know this batch is dirty"), not an
auto-detected mode.

### 4.11 Single-sample execution

No fallback to the old logic. Scoring always runs. The `rt_prior` signal
is the only thing that differs:

- If an external RT prior library row exists matching `config_hash` and target
  identity, use it.
- Otherwise `rt_prior` signal is skipped (neither 0 nor 2 — simply not
  contributing to the total severity).

### 4.12 Pre-pass + main-pass architecture

To avoid running full extraction twice while still providing batch priors:

1. **Pre-pass:** iterate every RAW file, extract only ISTD XICs, collect
   apex RT and Confidence. No analyte work, no output artefacts.
2. **Assemble priors:** from pre-pass results, build the injection-rolling
   RT prior per ISTD and the ΔRT library update candidates per analyte
   (deferred until Pass 2 since analyte RTs aren't known yet).
3. **Main pass:** iterate every RAW file, extract every target, score, select,
   write output.

Progress callback is weighted 0–50 % for pre-pass, 50–100 % for main pass.
`should_stop` is honoured in both. If pre-pass is interrupted, the batch
priors are marked partial and the main pass uses external library fallback
rather than partial batch data.

## 5. External RT Prior Library

**Path:** `config/rt_prior_library.csv`

**Schema:**

| Column | Type | Notes |
|---|---|---|
| `config_hash` | str | SHA-256[:8] of `targets.csv` + `settings.csv` content |
| `target_label` | str | Analyte or ISTD label |
| `role` | str | `ISTD` or `analyte` |
| `istd_pair` | str | For analytes, the paired ISTD label (empty for ISTDs) |
| `median_delta_rt` | float | For analytes; empty for ISTDs |
| `sigma_delta_rt` | float | For analytes; empty for ISTDs |
| `median_abs_rt` | float | For ISTDs; optional sanity column for analytes |
| `sigma_abs_rt` | float | For ISTDs |
| `n_samples` | int | How many samples contributed |
| `updated_at` | ISO datetime | |

**Update policy:**

- After each batch run finishes, the program writes a proposed update block
  to a `*.pending.csv` next to the library file. The user must explicitly
  confirm to merge it — no silent append. This mirrors the scientific-method
  guardrail (don't accumulate noise into priors).
- Rows with non-matching `config_hash` are silently ignored during lookup.
  Nothing is deleted — the library is append-only, and stale rows simply stop
  being queried once the config changes.

## 6. Output Changes

**"XIC Results" sheet:** add two columns only.

- `Confidence` — one of `HIGH` / `MEDIUM` / `LOW` / `VERY_LOW`.
- `Reason` — single short string. Format:
  - If Confidence == HIGH: `"all checks passed"`.
  - Otherwise: `"concerns: <signal1> (minor|major); <signal2> (...)"` listing
    every signal with severity ≥ 1, plus any propagated ISTD anchor warning.

**"Diagnostics" sheet:** unchanged.

**"Summary" sheet:** add per-target `Confidence distribution`
(HIGH/MEDIUM/LOW/VERY_LOW counts) as one extra column. No other changes.

**"Score Breakdown" sheet (new, OFF by default):**

Full per-candidate breakdown — seven severity values, the prior RT / ΔRT used,
and the prior source (rolling / batch / library / window-centre). Enabled via
`settings.emit_score_breakdown: bool` (default `false`). This is where advanced
users or future us debug threshold tuning.

## 7. Module Layout

New files:

- `xic_extractor/peak_scoring.py` — seven-signal scorer, Confidence/Reason
  mapping, multi-candidate selection. Pure functions; no I/O. Target < 400 lines.
- `xic_extractor/injection_rolling.py` — read injection-order metadata, compute
  rolling median priors per ISTD. Target < 200 lines.
- `xic_extractor/rt_prior_library.py` — read library CSV, filter by
  `config_hash`, write `*.pending.csv` update proposals. Target < 250 lines.

Modified files:

- `xic_extractor/signal_processing.py` — keep `find_peak_candidates` as is.
  Replace `_select_candidate` with a thin wrapper delegating to
  `peak_scoring.select_candidate_with_confidence(...)`.
- `xic_extractor/extractor.py` — split `run()` into `_pre_pass` and `_main_pass`.
  Plumb scoring context (rolling priors, library, config hash, injection order)
  through to `_extract_one_target`.
- `xic_extractor/settings_schema.py` — add fields:
  `injection_order_source`, `rolling_window_size`, `dirty_matrix_mode`,
  `rt_prior_library_path`, `emit_score_breakdown`.
- `xic_extractor/config.py` — compute `config_hash` from targets+settings content.

Not touched:

- `neutral_loss.py`, `raw_reader.py`, `sample_groups.py` — no behaviour change.

## 8. Testing Strategy

### 8.1 Stage 1 — Tissue regression gate

- Baseline: current output `output/xic_results_20260420_0309.xlsx` (85 samples,
  tissue block run).
- Regression fixture: a subset (e.g. 10 representative samples covering tumor,
  normal, benign fat, QC) stored under `tests/fixtures/tissue_regression/`.
- Test assertion: every target that previously produced a detected peak must
  still produce a detected peak with RT within ±0.05 min, and Confidence must
  be `HIGH` or `MEDIUM`. Area values must be within 5 % of the baseline.
- New unit tests per module:
  - `peak_scoring`: table-driven tests for each signal's severity thresholds,
    plus multi-candidate selection tie-breakers.
  - `injection_rolling`: rolling-window median with gaps in injection order,
    fallback paths.
  - `rt_prior_library`: config-hash filtering, pending-write round-trip.

### 8.2 Stage 2 — Urine validation

- New fixture: representative urine samples under
  `tests/fixtures/urine_validation/`.
- Manual ground-truth annotation from the user for borderline peaks
  (including 2286 / 2287).
- New tests assert that annotated "acceptable" peaks appear in output with
  Confidence ≥ `LOW` (not `VERY_LOW`) and that `Reason` correctly surfaces
  the expected concern (e.g. low S/N).
- **Gate:** Stage 2 is not merged unless it also passes Stage 1 regression.

### 8.3 Scoring-threshold regression protection

The seven severity thresholds are constants in `peak_scoring.py`. Any change
to them must:

- Update tissue regression fixture expectations if behaviour shifts, **and**
- Pass both tissue and urine suites in the same PR.

## 9. Rollout Plan

1. **Plan (writing-plans skill, next step after this spec is approved).**
2. **Stage 1 PR** — implement modules + tissue regression suite + flip
   `signal_processing.py` wiring. Ship behind `emit_score_breakdown=false`,
   `dirty_matrix_mode=false`, empty external library, no injection-order
   file (fallback to mtime proxy). Must pass tissue regression with no
   material change to existing results.
3. **Stage 2 PR** — urine fixtures, threshold tuning, `dirty_matrix_mode`
   finalisation, external-library seeding from tissue batch.
4. **Stage 3 (future)** — isotope checks, co-elution detection, optional
   GUI for threshold exploration.

## 10. Risks and Open Questions

- **AsLS parameters** (`lam`, `p`) are themselves tunable. Default to common
  literature values (`lam=1e5`, `p=0.01`) and expose via settings if tuning
  proves necessary. Not exposed initially.
- **`nl_support` severity 1 when no MS2** may be too harsh for fully MS1-only
  runs. If the batch has literally zero MS2 scans, we suppress the `nl_support`
  signal entirely (skip it rather than give severity 1 everywhere).
- **Injection-order metadata format:** we commit to `Sample_Name` +
  `Injection_Order` columns. If existing workflows use different column names,
  a light mapping in settings can be added later.
- **ΔRT library starts empty.** First batches have no ΔRT prior; this is fine —
  `rt_prior` signal just doesn't contribute until the library accumulates.
- **Confidence label vs. existing Diagnostics `Issue`** may duplicate
  information for some failure modes. We keep both: `Issue` is categorical
  failure, `Confidence` is graded quality. They can co-exist.
