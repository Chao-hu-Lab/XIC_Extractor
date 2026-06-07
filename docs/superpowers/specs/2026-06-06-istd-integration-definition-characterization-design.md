# ISTD Integration-Definition Characterization Study (S1, Stage 1) — WITHDRAWN

**Date:** 2026-06-06
**Status:** ⛔ **WITHDRAWN — not built.** Superseded by
`docs/superpowers/notes/2026-06-06-gaussian15-morphology-smoothing-window-scan-rate-finding-note.md`.

**Why withdrawn** (two independent spec critiques, both grounded in code, converged
on "do not build as framed"):
1. **Wrong comparator (confound):** the spec compared `area_ms1_morphology` against
   `area_raw_counts_seconds`, but the latter integrates **raw intensity including the
   baseline pedestal** (`integration.py:14-25`); the morphology area is
   baseline-subtracted. The `morphology/raw` ratio is dominated by baseline
   inclusion, not by clipping or the window — so analyses 2 & 3 were invalid. The
   correct baseline-subtracted comparator (`area_baseline_corrected`) was overlooked.
2. **Wrong specimen:** ISTDs are isotope-labeled, high-S/N, well-shaped peaks — the
   population *least* likely to exhibit the low-S/N clipping defect, which bites
   low-abundance endogenous analytes. "Clean on ISTDs" would be falsely reassuring.
3. **No decision power:** single-concentration ISTDs (confirmed by the data owner)
   make recovery linearity impossible; %RSD is explicitly not an accuracy criterion
   (smoothing lowers %RSD even when biased); every outcome branch routed back to "defer
   to a dilution series." A consolation study.
4. Mechanical: the planned Wilcoxon does not exist / no scipy in the diagnostics tree
   and is under-powered at n=7; S/N and per-scan Δrt are not in `peak_candidates.tsv`.

**What replaced it:** rather than a study, the one empirically-confirmable, real
finding — that the fixed 15-point smoothing window spans a batch-dependent time-width
(8RAW ~37 s vs 85RAW ~29 s) on the just-promoted morphology area — was captured as a
finding note (link above). No code change; deferred to a future deliberate gated
iteration. The retained content below is kept only as the reasoning trail.

---

**Original (withdrawn) framing:**
Documentation / Diagnostic. Acceptance = internal consistency +
reviewer readability + scientific honesty. **No numerical-equivalence gate, no
Science ground-truth gate, no detection/threshold change.**

## Motivation

The 2026-06-05 scientific review note (`docs/superpowers/notes/2026-06-05-target-untargeted-method-scientific-review-note.md`,
item **S1**, ranked highest) flags that the reported peak area uses a bespoke
definition with no mature-tool / literature analog:

- `reported_peak_area` (`xic_extractor/extractor.py:108-115`) prefers
  `area_ms1_morphology`, falling back to `area_raw_counts_seconds`.
- `area_ms1_morphology` (`xic_extractor/peak_detection/ms1_morphology.py:51-66`,
  `gaussian15_positive_asls_residual_metrics`) integrates the **Gaussian-15-smoothed
  positive AsLS residual**, clipping negatives to 0 (`ms1_morphology.py:64`,
  `np.maximum(residual[left:right], 0.0)`), over a **fixed 15-point window**
  (`DEFAULT_GAUSSIAN15_WINDOW_POINTS = 15`, not scaled to scan rate).
- `area_raw_counts_seconds` (`xic_extractor/peak_detection/hypotheses.py:58,360`,
  `= candidate.peak.area`) is the standard raw trapezoid.

Two specific defects the note names:
1. **Negative clipping** systematically under-integrates shoulders that dip below
   the AsLS baseline estimate.
2. **Fixed 15-point window** spans a different *time* width at different
   acquisition rates → systematic drift across batches.

Mature tools (Thermo Genesis/ICIS, MZmine) **smooth to detect boundaries, then
integrate the raw signal between them.** The note's S1 ask: let spike-in recovery
linearity choose `area_ms1_morphology` vs `area_raw_counts_seconds`.

## Why this is a characterization study, not a linearity study

The gold-standard test (recovery linearity over a concentration series) is **not
feasible with the available data.** Confirmed with the data owner: **all samples
have the ISTD added at identical concentration and volume** — there is no
multi-level concentration series, so no calibration curve can be fit, and absolute
accuracy/recovery cannot be measured.

What fixed-level ISTDs across many samples / two matrices / two batches *can*
support is a **characterization** of the two definitions. This spec scopes exactly
that, and is explicit about the boundary of what it can conclude.

### Can conclude
- **Relative precision** (%RSD) of each definition on identical-concentration
  replicates.
- Whether the **15-point window induces batch-dependent bias** (if the two batches
  differ in scan rate).
- The **magnitude and S/N-dependence** of the morphology-vs-raw divergence (the
  clipping defect's footprint).

### Cannot conclude
- Which definition is more **accurate / linear** — no concentration series.
- **Precision alone can favor a biased-but-smooth integrator** (smoothing reduces
  noise, lowering %RSD, even if clipping introduces a downward bias). This caveat
  must be stated wherever a %RSD comparison appears. A precision win for
  `area_ms1_morphology` is **not** evidence it is the better reported area.

## Data sources (reuse the targeted ISTD benchmark)

Per the data owner, all inputs reference the existing targeted method / its
benchmark. Reuse, do not rebuild:

- **ISTD target definitions (production-consistent source):** read from the targets
  CSV in `config/targets.example.csv` format via the existing `xic_extractor.config`
  `Target` loader, filtering `is_istd == TRUE`. This is the same target definition the
  pipeline itself uses (default setting), preferred over the benchmark's separate
  workbook "Targets" sheet. The example config has **7 ISTDs** (d3-5-hmdC, d3-5-medC,
  d4-N6-2HE-dA, 15N5-8-oxodG, [13C,15N2]-8-oxo-Guo, d3-N6-medA, d3-dG-C8-MeIQx), each
  isotope-labeled with its own RT window; the **per-ISTD compound is the unit of
  analysis** for precision / clipping. (The benchmark's `read_target_definitions`
  remains available as a fallback if a run only has the workbook.)
- **Sample / matrix / batch identity + reliability ("clean point") classification:**
  reuse the benchmark scaffolding (`--targeted-workbook`,
  `--targeted-reliability-json`, `TargetedReliabilityPoint`). Precision is computed
  on **clean/reliable points only**, so a few bad peaks do not contaminate %RSD.
- **Both area definitions per (ISTD, sample):** the targeted **workbook output
  carries only one area** (the reported `area_ms1_morphology`), so it cannot drive
  the comparison. Both areas are emitted only in **`peak_candidates.tsv`** (columns
  `area_raw_counts_seconds` + `area_ms1_morphology`, `peak_candidate_table.py:55-57,
  340-348`), which the extraction writes **only when `config.emit_peak_candidates`
  is True** (`output_dispatch.py:46-50`). Data path:
  - If the existing targeted run was executed with `emit_peak_candidates=True`,
    reuse the `peak_candidates.tsv` next to its output CSV — no re-run.
  - Otherwise, a **cheap re-run** of the 7 ISTD targets with
    `emit_peak_candidates=True`, over both the biological-tissue run and the clean
    STDs folder, produces it.
  The one new loader reads both areas from `peak_candidates.tsv`, keyed by
  (ISTD target, sample stem). (The benchmark's `TargetedPoint` carries only a
  single `area`, `targeted_istd_benchmark_models.py:53`, so it cannot be reused for
  this.)
- **Scan period per batch:** derive from the trace RT spacing (median Δrt) for the
  15-point window-width test. No new acquisition metadata needed.

Sample → (matrix = clean | bio, batch = 8RAW | 85RAW, type = QC | real) mapping,
all derivable from source — no manual labeling needed:
- **`matrix=clean`** = samples from the dedicated STDs acquisition folder
  (`C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\STDs`); everything else is
  `matrix=bio`.
- **`type=QC`** = the `*_pooled_QC*` sample-name pattern.
- **`batch`** = which dataset (8RAW vs 85RAW) the bio sample belongs to.

## Analyses

Each analysis states the conclusion it supports and its limit.

1. **Precision (primary).** Within same-matrix **replicate** groups (the 7 pooled
   QCs are the cleanest replicates; clean-matrix repeat injections next), per ISTD
   compute %RSD of both areas using clean points only. Compare median %RSD
   `area_ms1_morphology` vs `area_raw_counts_seconds`, per-ISTD and aggregated
   (Wilcoxon signed-rank across ISTDs). **Caveat printed inline: precision ≠
   accuracy.** Cross-sample biological replicates are NOT pooled into precision
   (their ISTD area legitimately varies with matrix suppression) — that variation
   belongs to analysis 4.
2. **15-point window batch bias.** Derive scan period per batch from RT spacing. If
   8RAW and 85RAW differ, compute the per-peak `morphology / raw` ratio (raw is the
   scan-rate-invariant reference) and test for a systematic between-batch shift in
   that ratio. A batch-dependent ratio = the fixed-window defect manifesting. **If
   the batches do not differ in scan rate, report `not_assessable`** — do not
   manufacture a result.
3. **Clipping magnitude.** `morphology / raw` ratio vs S/N (or height): is it
   systematically < 1 and worsening at low S/N (where the smoothed residual dips
   below baseline relative to signal)? Report Spearman(ratio, S/N) + binned medians.
4. **Matrix consistency.** Clean vs bio ISTD area: which definition's clean/bio
   ratio is more consistent (less dispersion). **Conflates integrator quality with
   real ion suppression** — stated, reported as descriptive only.
5. **Targeted cross-check.** Compare both areas against the targeted method's
   reported area (sanity that we are reading the right peaks).

## Components (small, focused; reuse over rebuild)

- `tools/diagnostics/integration_definition_characterization.py` — pure analysis
  functions (%RSD; batch-bias detector; clipping trend; matrix consistency).
  Reuse `targeted_istd_benchmark_stats` (`_pearson`, `_spearman`, `_median_abs`,
  `_percentile_abs`, `_mean`).
- A new loader reading both areas per (ISTD, sample) from the peak candidate table.
- `tools/diagnostics/characterize_integration_definition.py` — CLI mirroring the
  benchmark's arg style (`--targeted-workbook`, the peak-candidate-table source,
  `--targeted-reliability-json`, sample-info, `--output-dir`).
- Outputs:
  - per-(ISTD, sample) TSV: both areas, ratio, S/N, matrix, batch, type, clean flag.
  - summary TSV + Markdown: per-ISTD %RSD (both), batch-bias verdict, clipping
    trend stats, matrix consistency.
  - a characterization **note** in `docs/superpowers/notes/` with honest
    conclusions (what can / cannot be concluded, caveats above).

## Tests (Doc-type: helper correctness + internal consistency + honesty)

- Unit: %RSD helper; **batch-bias detector** (synthetic: inject a batch-dependent
  morphology/raw ratio → detected; equal scan rate → `not_assessable`); **clipping
  trend** (synthetic: ratio < 1 increasing at low S/N → detected; flat → not
  flagged); matrix-consistency.
- CLI smoke: small synthetic targeted output → all outputs produced, deterministic
  (byte-stable on re-run).
- **Honesty guard:** single-batch input → 15-point test reports `not_assessable`,
  never a spurious batch result; precision summary always carries the
  precision≠accuracy caveat string.

## Verification

`uv run pytest --tb=short -q`, report pass count. Then run on the real 8RAW + 85RAW
ISTD targeted output, produce the characterization note, and manually sanity-check
the verdicts against a couple of overlay plots.

## Explicit non-goals / frozen

- **No change** to `ms1_morphology.py`, `extractor.reported_peak_area`,
  `hypotheses.py`, or any extraction/alignment behavior.
- **No linearity / accuracy claim.**
- **No detection threshold or selection change.**

## Stage 2 (deferred — not in this spec)

If the characterization shows `area_ms1_morphology` carries a material bias
(clipping and/or batch-dependent window effect) and `area_raw_counts_seconds` is at
least as precise, that motivates a *separate* decision to change the reported area
toward the standard "smooth-to-detect, integrate-raw" definition. That change is
Science-type and should ideally be backed by a real dilution series; it is out of
scope here.

## Risks / honesty

- Precision favors smoothing → **cannot crown an accuracy winner.** Stated in
  outputs.
- 15-point test only works if batches differ in scan rate → `not_assessable`
  otherwise.
- QC replicate n is small (7) → %RSD confidence intervals are wide; report n and
  treat results as indicative, not definitive.
- Matrix-effect analysis conflates integrator quality with real ion suppression.
