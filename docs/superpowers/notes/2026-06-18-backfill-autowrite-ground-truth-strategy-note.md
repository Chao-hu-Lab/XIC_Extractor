# Backfill Auto-Write Ground-Truth Strategy - 2026-06-18

Purpose: code- and data-verified strategy for the Backfill **auto-write** north
star (minimize manual review, stay auditable). Strategy/spec note meant to feed
the two-round independent critique (Sonnet local + Opus fundamental) before any
implementation. Companion to
`docs/superpowers/pulse-reports/2026-06-17-2340-productization-evidence-inventory.md`.

Status: design input, not an implementation plan. The execution gate is the
companion critical review:
`docs/superpowers/notes/2026-06-18-backfill-autowrite-ground-truth-critical-review.md`.
Do not start degradation/model work from this note directly; first produce the
single `backfill_ground_truth_gate_v1` packet described there.

## North Star (confirmed with owner)

- Goal is **auto-write**, not a human-review triage queue. Shrink manual
  intervention toward its identifiability floor by perfecting the rule.
- Hard constraint: the rule must be **auditable / not a black box**. Every
  auto-written cell traces to a rule + evidence.
- Owner accepts a model-based classifier to generalize the rule. Accumulated
  human ReviewAction verdicts are ~zero (only module/scripts/tests; no
  `output/**` verdict data), so labels cannot come from humans.

## What "Backfill" Actually Does (verified)

The writer **promotes a value the extractor already computed**, it does not
reconstruct a missing measurement.

- `product_activation.py:246` -> `_matrix_value_for_activation(source_cell)`
  (`:2030-2038`) returns `source_cell["primary_matrix_area"]` only if
  `primary_matrix_area_source` is in `ACTIVE_PRIMARY_MATRIX_AREA_SOURCES`, whose
  sole member is `MS1_MORPHOLOGY_PRIMARY_MATRIX_AREA_SOURCE` (`:30-34`).
- So Backfill = promote the cell's own MS1-morphology area into the matrix. No
  cross-sample transfer, no sibling reconstruction.

> Correction logged: an earlier draft proposed a sibling-consensus / leave-one-out
> reconstruction oracle and a synthetic-trace fallback. Both were wrong targets —
> the writer promotes the cell's own morphology area, so validation must target
> **morphology peak selection + integration on the cell's own signal**.

## The 4613 Candidate Universe (verified)

The candidate universe is the activation value-delta rows, so all 4613 are
already shadow-written morphology areas. "Blocked" = no promotion authority, not
"no value". Buckets from
`standard_peak_backfill_productization.py:1414-1427`:

| Group | Count | What it is |
| --- | --- | --- |
| `write_ready` | 511 | area written + trace loaded (`matched`) + features in 1 of 6 clean slices |
| blocked `approved_evidence_class_required` | 3015 | area written + trace loaded, features "dirty", in no clean slice |
| blocked `trace_overlay_required` | 1087 | area written but no overlay/trace stored (`missing_overlay_path`) -> unverifiable |

`write_ready` requires `matrix_value_effect=="written"` AND
`trace_match_status=="matched"` (`:1313-1327`). `matched`
(`standard_peak_activation_scope_audit.py:837`) only means the stored morphology
trace exists and loaded (provenance), **not** that the peak is correct.

The auto-write expansion target is the **3015** dirty-but-written-and-traced
cells. The 1087 no-trace cells are out of scope (no verifiable provenance).

## Why the Gate Is Stuck

1. The gate is **6 hand-carved slices OR'd together**
   (`standard_peak_backfill_productization.py:1257-1327`), each discovered
   empirically on one dataset (85RAW). More slices = more forking-path
   comparisons on the same data.
2. The supporting `heldout_trace_reintegration_oracle` is a **round-trip /
   determinism check**: it re-integrates the same stored trace that defined the
   truth and compares to its own boundary/area
   (`standard_peak_heldout_trace_oracle.py:661-666`, `:895-905`, `:953-954`); the
   `mask`/`heldout` tokens are declarative, no masking code. It is **blind to
   peak-selection error** — the dominant failure mode for the 3015 dirty cells.

## The ISTD Gold-Set Anchor (verified) — resolves the independence problem

Internal standards are externally certified, constant-concentration, and
reliably present. They are the independent truth that "clean" (a morphology
self-assessment) is not.

- Targets: `config/targets.example.csv`. Six active analyte/ISTD pairs after
  excluding the RNA-only `8-oxo-Guo / [13C,15N2]-8-oxo-Guo` pair (never detected
  in the dR method) and noting `N6-HE-dA` external is a known absence.
- Authoritative target->untargeted-family bridge: the **`targeted_istd_benchmark`**
  artifact (use `selected_feature_id`), NOT a hand-rolled m/z grep. Untargeted
  families can be centered on an isotope-shifted ion: e.g. **d4-N6-2HE-dA
  ([M+H]+ 300.1605) -> FAM007866 @ 301.165** (`match_type=isotope_shift`). A naive
  monoisotopic grep misses it and falsely reads "method dropped the ISTD".
- Evidence (`output/backfill_product_policy_same_peak_activation_85raw_20260608/targeted_istd_benchmark_current_alignment/`):
  **all 6 active ISTDs detected 85/85** -> families FAM001553 (d3-5-hmdC),
  FAM000306 (d3-5-medC), FAM007866 (d4-N6-2HE-dA), FAM005383 (15N5-8-oxodG),
  FAM002532 (d3-N6-medA), FAM017220 (d3-dG-C8-MeIQx). The method is not dropping
  ISTDs.
- Two truth axes per ISTD: (a) **location** from the target table (m/z + RT
  window, isotope_shift-aware); (b) **magnitude consistency** from constant
  concentration across the 85 real samples (exclude QC).

## Key Empirical Finding: current ISTD matrix evidence points to under-estimation

Using constant concentration (the p5-p95 cluster median is the per-sample truth
proxy), per-sample untargeted areas for the ISTD families
(`.../alignment_seed_audit/alignment_matrix.tsv`) show low-side outliers and no
`>3x median` high outliers in the checked families:

- d3-N6-medA: cluster 1.5e8-4.8e8; **0 samples >3x median**, 3 samples low,
  including TumorBC2267 / TumorBC2264 at ~5.7e5-6.1e5 (~**640x under**). This
  alone drives its area-correlation gate to pearson 0.12 (outlier-driven, not
  uniform scatter; its family had 199 candidate matches -> wrong-small-peak in
  those matrices).
- d3-dG-C8-MeIQx (gate PASS): 0 high, 3 mildly low.
- d3-5-hmdC (gate FAIL): 0 high, 1 low (~9x).

Conclusion: in the current six active ISTD selected families, the observed
untargeted morphology failures look like under-integration
(clipping / wrong-small-peak behavior), not obvious inflation. This is a
working hypothesis for gate design, not a product-wide error law. It does not
rule out smaller but still material high-side area errors inside the `3x median`
screen.

Implication: the next gate must quantify signed area error, not just absolute
pass/fail. Before any ProductWriter expansion, join targeted per-sample areas or
another independent reference where available, and set explicit signed-area
acceptance thresholds.

## Possible Later Strategy (not the current next step)

This section is background only. Do not implement it until
`backfill_ground_truth_gate_v1` proves a short numeric gate is plausible.

### 1. Degradation oracle candidate

ISTDs are always clean/detected, so they never naturally populate the dirty
regime of the 3015 target cells. Degradation could be one bridge, but only if
the read-only gate shows synthetic dirty traces match real dirty profiles:

- Seed = per-sample ISTD cells that are confidently correct: apex RT in target
  window, area in the family's main cluster, clean feature profile.
- Degrade each seed's stored trace along axes that map to the blocker tokens:
  scan_count (decimate scans), height (scale down + noise), shape (noise /
  asymmetry), apex/baseline (drift, neighbor interference) — across a grid.
- Re-run morphology peak selection + integration on the degraded trace.
- Label per (seed, level): selection correct? (apex/boundary within 0.1 min of
  the seed truth) and **signed** area error (capture the under-estimation
  direction).

This might measure the production mechanism and yield
`(feature_profile -> correctness, signed area bias)` labels with no manual
labeling. It is not approved yet.

### 2. Model = the gate that generalizes, kept auditable

- Calibrate `feature_profile -> P(selection correct), area-bias` on degradation
  labels. Features are the per-cell metrics already computed (shape, height,
  scan_count, boundary_width, apex_delta, local/global ratio).
- Only if the gate packet supports it, replace hand-carved slices with one
  learned, **monotonic/interpretable** boundary.
- Each auto-written cell carries: feature bin, measured P(correct), measured
  area bias, holdout id, plus the existing sha256 evidence chain. White-box.

### 3. Lockbox / cross-batch validation (anti cherry-pick)

- Pre-register feature set, model family, threshold + tolerance before the final
  run; fit on a dev split; evaluate once on a sealed lockbox.
- If using 8RAW, describe it as a smaller historical validation subset unless
  independence is specifically justified.
- Log how many model/threshold variants were tried.

## Limits / Risks To Stress In Critique

1. **Degradation realism**: the entire dirty-regime evidence is synthetic
   degradation of clean ISTDs. If synthetic dirty != real dirty at the same
   feature profile, labels overstate safety. Spot-check degraded-ISTD behavior
   against the few real dirty cells with any independent truth.
2. **Identity-independence**: only 6 ISTDs (modest chemical diversity). The bet
   is morphology error depends on trace shape, not compound identity. Test by
   checking the error curves agree across the 6 chemically-distinct ISTDs.
3. **Family-confusion blind spot**: the worst real failure (d3-N6-medA, 199
   candidate families, wrong-small-peak in Tumor samples) is an
   alignment/family-assignment error, not single-trace integration. Degrading one
   clean trace will NOT reproduce wrong-family selection, so the degradation
   oracle may underestimate the true failure rate. Family-confusion needs a
   separate check.
4. **Direction is known (under)**: the gate must especially bound
   under-estimation; over-estimation is not the observed risk.

## Irreducible Floor

- 1087 `missing_overlay_path` cells: no stored trace -> cannot verify -> must not
  auto-write (would be an unauditable black box). Need trace regeneration or stay
  blocked.
- Dirty profiles with low measured P(correct) on the holdout: auto-writing them
  ships known-wrong (under-estimated) areas. Irreducible manual remainder.

Target: shrink manual remainder from "all 4102 blocked" to "(1087 no-trace) +
(low-correctness profiles)"; convert the holdout-passing share of the 3015 into
principled, auditable auto-writes. Not zero — floor set by data identifiability.

## Next Step

Produce one read-only `backfill_ground_truth_gate_v1` packet with four sections:
facts, ISTD truth, dirty-profile comparison, and numeric acceptance table. If
that packet cannot express a short defensible product gate, park broad Backfill
instead of adding more diagnostics or starting a model/degradation track.

## Hard Warnings

- A model does not manufacture ground truth; it only generalizes the labels you
  give it. Do not train on existing features + the round-trip oracle — that
  relearns the blind slices.
- Map targets to untargeted families via `targeted_istd_benchmark`
  (`selected_feature_id`), never a monoisotopic m/z grep (isotope_shift).
- Round-trip / determinism passes are not peak-selection correctness.
- Do not auto-write `missing_overlay_path` cells.
- Counts/areas here are from the listed 85RAW outputs; re-confirm against the
  current replay before any acceptance run.
