# P2c - AsLS Truth Validation And Linear-Edge Retirement Gate Spec

**Date:** 2026-05-26
**Status:** Draft v0.4 - B+C correction; Tier C comparator is linear-edge, not manual integration
**Overview:** [Peak pipeline modernization overview](2026-05-24-peak-pipeline-modernization-overview-spec.md)
**Cleanup dependency:** [C1b - Linear Edge Baseline Retirement](2026-05-24-peak-pipeline-cleanup-linear-edge-retirement-spec.md)
**Depends on:** P2 AsLS shadow, P2b conditional audit promotion, P7 validation-cost controls, and 85RAW primary-delivery validation

## Purpose

Define the evidence required to decide whether AsLS can replace linear-edge for
the affected area-integration contract.

P2b already shows that the current AsLS audit-promotion path does not break the
accepted 85RAW primary delivery surface. That is necessary, but it does not
prove absolute baseline truth. This spec adds a separate baseline-retirement
gate and prevents P2b's "linear-edge is not truth" finding from being overread
as "AsLS is proven truth." The gate's comparator is the legacy linear-edge
baseline on the same trace and boundary, not blinded manual integration or a
fixed percent area uplift target.

## Decision Levels

This spec deliberately separates three decisions:

| Decision | Meaning | Required evidence |
|---|---|---|
| `GO_FOR_C1B_PLAN_SYNTHETIC_ONLY` | Engineering may write a C1b plan, but may not delete linear-edge yet. | Tier A guard + locked Tier B1 relevance benchmark pass; Tier B2 stress audit may be unresolved but must be reported |
| `GO_FOR_LINEAR_EDGE_RETIREMENT` | C1b implementation may retire linear-edge after C1a, C5, and rollback-column deprecation have landed. | Tier A guard + Tier B1 pass + Tier B2 stress safety disposition + Tier C AsLS-vs-linear-edge baseline evidence + blank/carryover safety disposition or exclusion + retirement prerequisite manifest |
| `REQUIRES_TIER_C` | C1b planning may be supported, but retirement authority is missing real baseline-evidence or safety evidence. | Tier A guard + Tier B1 pass, but missing required Tier C or stress-safety disposition |
| `REQUIRES_RETIREMENT_PREREQS` | Scientific evidence is sufficient for retirement review, but C1a/C5/rollback-column prerequisites are not proven. | Tier A guard + Tier B1 pass + required Tier B2/Tier C evidence, but missing satisfied prerequisite manifest |
| `NO_GO_KEEP_LINEAR_EDGE` | Keep linear-edge available and make C5 method-preserving. | Tier A failure, Tier B1 relevance hard blocker, or retirement-target evidence failure |

`GO_FOR_C1B_PLAN_SYNTHETIC_ONLY` is a planning status only. It must not be used
as a production-ready or deletion approval.

## Current Evidence State

The project already has useful failure-mode evidence:

- selected ISTD baseline-truth audit plots and metrics show repeated
  `linear_edge_over_subtraction_plausible` behavior;
- old P2 `PASS` and `FAIL` selected families both show the same dominant
  pattern;
- no selected-family truth-audit row had `asls_raw_pct > 100.0`;
- 85RAW validation-minimal plus super-window reproduced accepted primary TSV
  hashes and completed as a foreground run.
- the first locked Tier B smoke was deletion-safe but over-scoped: row-level
  blockers were limited to synthetic blanks, while aggregate blockers came from
  stress classes and 64-point synthetic windows that do not match the selected
  ISTD Tier A boundary distribution.

This is enough to reject the old strict "linear-edge area is truth" comparator
and to justify a scoped B1 relevance gate. It is not enough to claim general
baseline truth or delete linear-edge without a real AsLS-vs-linear-edge
baseline-evidence gate and the cleanup prerequisites below.

## Gate Principle

The gate must answer one practical question:

> For XIC shapes that this pipeline actually integrates, is AsLS at least as
> physically plausible and quantitatively stable as linear-edge, without
> changing RT identity or boundary selection?

The gate does not need to prove AsLS is globally best across all
chromatography, and it must not require a fixed AsLS-vs-linear-edge area uplift
ratio. It must prove that replacing linear-edge for this pipeline's selected
use case is better supported than keeping linear-edge, and it must make the
remaining truth limits explicit. Synthetic stress cases may raise
retirement-safety questions, but they must not silently override the selected
ISTD relevance gate.

## Required Inputs / Tier A Contract

Tier A is **not ground truth**. It is a real-data same-peak and
failure-mode-coverage guard. It prevents synthetic fixtures from validating a
failure mode that was not actually observed.

Required existing artifacts:

| Artifact | Path | Required columns / contents |
|---|---|---|
| Truth rows | `output/phase1_p2_baseline_truth_audit_all_statuses/baseline_truth_audit_rows.tsv` | `target_label`, `feature_family_id`, `sample_stem`, `status`, `raw_area`, `linear_area`, `asls_area`, `linear_raw_pct`, `asls_raw_pct`, `asls_vs_linear_pct`, `linear_baseline_subtracted_pct`, `asls_baseline_subtracted_pct`, `linear_edge_delta_pct`, `outside_background_pct`, `peak_start_rt`, `apex_rt`, `peak_end_rt`, `trace_point_count`, `classification`, `review_reason`, `plot_path` |
| Truth summary | `output/phase1_p2_baseline_truth_audit_all_statuses/baseline_truth_audit_summary.tsv` | `target_label`, `feature_family_id`, `row_count`, `dominant_classification`, `classification_counts`, `median_linear_baseline_subtracted_pct`, `median_asls_baseline_subtracted_pct`, `median_asls_vs_linear_pct`, `max_asls_vs_linear_pct`, `median_linear_edge_delta_pct`, `median_outside_background_pct`, `review_status`, `plot_path` |
| Truth JSON | `output/phase1_p2_baseline_truth_audit_all_statuses/baseline_truth_audit.json` | machine-readable copy of rows, summary, and input metadata |
| Truth report | `output/phase1_p2_baseline_truth_audit_all_statuses/baseline_truth_audit.md` | human-readable summary |
| Plots | `output/phase1_p2_baseline_truth_audit_all_statuses/plots/` | one linked plot per reviewed selected family |

Required Tier A manifest:

- `docs/superpowers/fixtures/asls_truth_tier_a_expected_manifest.json`

The manifest must include:

- `manifest_version`;
- generating command, environment profile, and `generated_by_git_sha`;
- current-code compatibility rule: the manifest must either match the current git
  SHA or cite an accepted current-code compatibility artifact and hash;
- source input paths and hashes for the P2 gate rows and alignment integration
  audit TSV used to generate Tier A;
- expected dataset label, RAW subset, branch family, and P2b semantic version;
- expected selected-family table with `target_label`, `feature_family_id`,
  old P2 status, expected row count, expected sample count, and required plot
  path;
- expected total row count and expected family count;
- expected file hashes for Tier A rows, summary, JSON, and report when the
  manifest is used to validate existing artifacts instead of regenerating them.
- accepted P2b/85RAW primary-delivery validation artifact paths and hashes when
  `decision_target=linear-edge-retirement` is evaluated.

Initial expected selected-family coverage:

| Target | Family | Old P2 status | Expected rows | Expected samples |
|---|---|---:|---:|---:|
| `15N5-8-oxodG` | `FAM000538` | `PASS` | 8 | 8 |
| `d3-5-hmdC` | `FAM000153` | `FAIL` | 8 | 8 |
| `d3-5-medC` | `FAM000031` | `PASS` | 8 | 8 |
| `d3-N6-medA` | `FAM000242` | `PASS` | 8 | 8 |
| `d3-dG-C8-MeIQx` | `FAM001878` | `FAIL` | 8 | 8 |
| `d4-N6-2HE-dA` | `FAM000807` | `FAIL` | 8 | 8 |

Freshness rule:

- artifacts must match the Tier A manifest or be regenerated in the current
  run;
- row/summary schemas above must be present exactly, including no missing,
  extra, or reordered columns and no per-row overflow cells;
- observed family count must be 6 and row count must be 48 unless the manifest
  version is explicitly revised before the gate run;
- both old P2 `PASS` and `FAIL` families must be represented;
- rows, summary, JSON, and `baseline_truth_audit.md` report artifact hashes
  must be recorded in the diagnostic JSON and closeout note;
- if any required Tier A artifact is missing, stale, hash-drifted, or generated
  from incompatible current-code evidence, the gate is
  `INCONCLUSIVE_REGENERATE_TIER_A`, not a scientific `NO_GO`;
- if Tier A artifacts are malformed, unreadable, or schema-incompatible, the
  gate is `INCONCLUSIVE_INVALID_INPUT`.

Regeneration command:

```powershell
.venv\Scripts\python.exe -m tools.diagnostics.p2_baseline_truth_audit `
  --p2-gate-rows-tsv output\phase1_p2_asls_shadow_validation\diagnostics\p2_asls_shadow_gate\p2_asls_shadow_gate_rows.tsv `
  --alignment-integration-audit-tsv output\phase1_p2_asls_shadow_validation\alignment\asls_shadow\alignment_cell_integration_audit.tsv `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\phase1_p2_baseline_truth_audit_all_statuses `
  --include-gate-status FAIL `
  --include-gate-status PASS
```

Tier A pass requirements:

- all expected selected families and row counts from the Tier A manifest are
  present;
- no reviewed row has `asls_raw_pct > 100.0`;
- reviewed rows do not show wrong RT identity or unacceptable boundary
  expansion;
- no selected-family summary is dominated by
  `asls_under_subtraction_plausible`;
- observed morphology/failure modes are mapped to Tier B fixture classes.

`linear_edge_over_subtraction_plausible` is supporting failure-mode evidence,
not ground truth and not sufficient by itself.

## Tier A To Tier B Coverage Matrix

The implementation must emit a coverage table mapping observed real-data
failure modes to synthetic fixtures. The coverage table must separate
production-relevant B1 fixtures from B2 stress-only fixtures so that review
can see which synthetic results are allowed to block C1b planning.

Initial required B1 mapping:

| Observed selected-family pattern | Example selected families | Required B1 fixture classes |
|---|---|---|
| shoulder/tail cut by edge interpolation | `d3-5-hmdC`, `d4-N6-2HE-dA`, `d3-dG-C8-MeIQx` | `tailing_peak`, `adjacent_shoulder`, `sloped_baseline_peak` |
| stable linear-edge over-subtraction in old PASS families | `d3-5-medC`, `15N5-8-oxodG`, `d3-N6-medA` | `sloped_baseline_peak`, `tailing_peak`, `flat_peak_control` |
| low outside background with baseline disagreement | all selected families in the all-status audit | `flat_peak_control` |

B2 stress fixtures must be reported but are not required to cover Tier A
selected-family patterns:

| B2 stress class | Role |
|---|---|
| `blank_noise_control` | synthetic blank/carryover stress; retirement safety only |
| `coeluting_interference` | peak-purity/deconvolution stress; must not be treated as baseline truth unless full integrated signal is the truth target |
| `local_baseline_dip` | local distortion stress; retirement or targeted follow-up only unless observed in Tier A |
| `heteroscedastic_noise_peak` | noise-model stress |
| `low_sn_peak` | low-S/N stress; may be promoted to B1 only when real Tier A/Tier C shows comparable selected rows |
| `saturated_or_clipped_apex` | detector/clipping stress; retirement or targeted follow-up only |

If an observed pattern cannot be mapped, the gate is `INCONCLUSIVE_FIXTURE_GAP`
until the B1 fixture manifest is extended and reviewed. A B2-only stress class
must not satisfy B1 coverage by itself.

## Tier B - Locked Synthetic Known-Ground-Truth Benchmark

Tier B validates algorithm behavior under known generated truth. It is split
into two layers:

- **Tier B1 relevance gate:** synthetic fixtures directly justified by Tier A
  selected ISTD failure modes. B1 can unblock C1b planning when it passes.
- **Tier B2 stress audit:** broader synthetic stress cases. B2 can require Tier C
  or block retirement, but it must not by itself block C1b planning.

Both layers must be pre-registered before implementation using
`asls_truth_validation_fixture_manifest.json`.

The manifest is part of the public diagnostic contract and must include:

- `fixture_version`, initially `synthetic_truth_fixture_v2`;
- `tolerance_profile`, initially `asls_truth_tolerance_v2`;
- AsLS parameters: `lam`, `p`, `n_iter`;
- random generator seed;
- scan spacing and RT unit;
- integration bounds policy and gate layer (`B1_RELEVANCE`,
  `B1_ADJACENT_STRESS`, or `B2_STRESS`) for each fixture row or class;
- true baseline and true peak function for each fixture class;
- parameter grid for peak width, height, S/N, baseline slope/curvature,
  tailing/shoulder offset, coelution intensity, heteroscedastic noise, local
  dips, and saturation/clipping;
- replicate count per class;
- split label: `calibration` or `heldout_gate`;
- expected failure mode for linear-edge when applicable;
- per-threshold rationale for every value in `tolerance_profile`.

Tier B must also include
`docs/superpowers/fixtures/asls_truth_validation_fixture_lock.json`. The lock is
part of the pre-implementation review surface and must freeze:

- every calibration and heldout `fixture_id`;
- fixture class, split, replicate id, strata labels, and exact parameter values;
- true-area formula version, integration bounds policy, and expected bound
  indices;
- per-row generator input hash and a whole-lock hash recorded in the diagnostic
  JSON.

The generator may compute traces from the lock, but it must not choose or drop
heldout rows after comparator code exists. If the lock changes, the gate must
emit `INCONCLUSIVE_FIXTURE_LOCK_CHANGED` until the lock is reviewed again.

Required manifest keys for B1/B2 support:

- each fixture-class definition must include `default_gate_layer`,
  `truth_target_type`, `stress_role`, `allowed_decision_targets`,
  `production_like_bounds_policy`, and
  `promotion_requires_review_evidence`;
- `default_gate_layer` enum values are `B1_RELEVANCE`,
  `B1_ADJACENT_STRESS`, and `B2_STRESS`;
- `truth_target_type` enum values are `baseline_corrected_peak_area`,
  `accepted_boundary_signal`, `blank_zero_area`, and `stress_not_truth`;
- `allowed_decision_targets` must state whether the class can drive
  `c1b-plan`, `linear-edge-retirement`, or reporting-only stress summaries.

Required fixture-lock row keys:

- `gate_layer`;
- `stress_role`;
- `production_like_bounds_status` (`IN_SCOPE`, `ADJACENT_STRESS`, or
  `OUT_OF_SCOPE_STRESS`);
- `scan_density_stratum`;
- `integration_point_count`;
- `integration_width_min`;
- `tier_a_width_quantile_band`;
- `decision_scope` (`C1B_RELEVANCE`, `RETIREMENT_ONLY`, or
  `REPORTING_ONLY`);
- `truth_target_type`;
- `required_for_b1_coverage`;
- `fixture_scope_reason`.

Required B1 relevance fixture classes:

- `flat_peak_control`: flat baseline plus symmetric peak;
- `sloped_baseline_peak`: sloped baseline plus peak;
- `tailing_peak`: asymmetric tail where edge interpolation can cut real signal;
- `adjacent_shoulder`: main peak with adjacent shoulder where the expected truth
  is the accepted integrated signal inside the selected boundary, not
  main-peak-only deconvolution;
- `hump_baseline_peak`: optional B1 only after its locked morphology is shown to
  match Tier A reviewed selected-family plots; otherwise keep it B2.

Required B2 stress fixture classes:

- `coeluting_interference`: nearby interfering peak outside the selected
  boundary; this tests peak purity/deconvolution unless truth is defined as the
  full integrated signal inside the boundary;
- `local_baseline_dip`: local baseline dip before or after the peak;
- `heteroscedastic_noise_peak`: noise increasing with intensity;
- `low_sn_peak`: noisy low-intensity peak near the decision boundary;
- `saturated_or_clipped_apex`: clipped apex control;
- `blank_noise_control`: blank/no-peak trace with noise only.

Minimum fixture coverage:

- each B1 fixture class must include at least 10 calibration replicates and 25
  heldout replicates in production-like bounds;
- each B2 stress fixture class must include enough calibration and heldout rows
  to report stable stress metrics, but B2 counts must be summarized separately
  from B1 counts;
- heldout rows must cover at least three S/N strata for non-blank classes:
  `low` (5-10), `medium` (10-30), and `high` (>30);
- heldout rows must cover at least three peak-width strata:
  `narrow` (0.015-0.03 min sigma), `typical` (0.03-0.06 min), and `wide`
  (0.06-0.10 min);
- each B1-relevant non-blank class should expose all nine S/N x peak-width
  combinations in the lock so a comparator cannot pass by fitting a coupled
  fixture bundle, but rows outside production-like Tier A bounds must be tagged
  `B1_ADJACENT_STRESS` or `B2_STRESS` and excluded from `tier_b1_status`;
- non-blank heldout classes must include both positive and negative baseline
  slope cases when slope is applicable;
- classes involving shoulders, tailing, coelution, dips, or clipping must
  include at least five heldout rows per hard-case stratum.
- blank heldout rows must cover low-noise, high-noise, sloped-baseline,
  hump-baseline, and carryover-like no-true-peak strata with at least five rows
  each; synthetic blank safety is B2 stress evidence and cannot replace Tier C
  blank/carryover disposition for retirement authority.

Initial required parameter ranges:

| Parameter | Range / strata |
|---|---|
| RT scan spacing | 0.005-0.02 min |
| Trace length | at least 121 points |
| Peak apex location | at least 3 peak widths away from trace edge |
| Peak height | 1e4-1e6 intensity units |
| Baseline intercept | 0-10% of peak height |
| Baseline slope | -10% to +10% of peak height per min |
| Hump amplitude | 2-30% of peak height |
| Hump width | 2-8 peak widths |
| Tail factor | 0.2-1.5 peak widths |
| Shoulder offset | 0.5-2.0 peak widths from main apex |
| Shoulder height | 10-80% of main peak height |
| Coeluting interference height | 10-80% of main peak height |
| Local dip depth | 2-20% of peak height |
| Noise model | additive Gaussian plus optional intensity-proportional component |
| Saturation/clipping | apex clipped at 60-95% of true apex height |

Production-like B1 bounds policy:

- B1 heldout integration bounds must be derived from Tier A selected-family
  `trace_point_count` and RT-width quantiles, not a fixed point count;
- initial Tier A reference: selected-family point-count median `11`, max `45`,
  RT-width median `0.4157 min`;
- B1 must include representative point-count strata such as low, median, and
  high Tier A quantiles;
- under-sampled rows and very broad 64-point stress windows may be retained as
  B2 stress rows, but they do not determine B1 pass/fail unless real Tier A/Tier
  C evidence shows they are in production scope.

Calibration / heldout protocol:

- thresholds may be tuned only on `calibration` fixtures before a gate run;
- `heldout_gate` fixtures must remain untouched by threshold tuning;
- any threshold revision after a calibration run requires a new manifest
  version and must record the failed run reference;
- the first `synthetic_truth_fixture_v1` smoke is recorded as a fixture-scope
  mismatch discovery run, not as proof that linear-edge is scientifically better
  on selected ISTDs;
- after one reviewed B1/B2 fixture/tolerance revision, the next B1 heldout run
  must end in `GO_FOR_C1B_PLAN_SYNTHETIC_ONLY`,
  `NO_GO_KEEP_LINEAR_EDGE`, or `INCONCLUSIVE_FIXTURE_SCOPE_MISMATCH`;
- a third B1 synthetic-only revision is not allowed without explicit owner
  approval and a written reason why real Tier C evidence cannot answer the
  remaining question faster.

Legacy fixture migration:

- outputs generated with `synthetic_truth_fixture_v1` or
  `asls_truth_tolerance_v1` are historical discovery artifacts under this spec;
- a B1/B2-aware runner must emit
  `fixture_scope_status=INCONCLUSIVE_FIXTURE_SCOPE_MISMATCH` and
  `legacy_fixture_status=LEGACY_V1_NON_AUTHORITATIVE` when asked to use v1
  outputs as current C1b/retirement authority;
- existing v1 `gate_decision=NO_GO_KEEP_LINEAR_EDGE` summaries must not be cited
  as scientific no-go evidence after this spec version unless they are
  regenerated or reclassified through the v2 B1/B2 lock.

## Tier B Metrics And Acceptance

Required row metrics:

- Tier B layer (`B1_RELEVANCE`, `B1_ADJACENT_STRESS`, or `B2_STRESS`);
- production-like bounds status and scan-density stratum;
- stress role for B2 rows;
- raw area;
- true baseline-corrected area;
- linear-edge corrected area and absolute/relative error;
- AsLS corrected area and absolute/relative error;
- AsLS error divided by linear-edge error;
- whether either method exceeds raw area;
- whether either method produces negative corrected area for non-blank peaks;
- blank false-positive flag;
- baseline residual MAD and area uncertainty when available.

Blank classification definitions:

- synthetic blank rows are B2 stress evidence by default;
- `blank_false_positive=true` when `asls_area` is greater than
  `max(3 * area_uncertainty, 0.005 * reference_nonblank_median_true_area)`;
- `blank_not_quantifiable=true` only when the diagnostic cannot compute area
  uncertainty because required synthetic metadata is missing;
- heldout synthetic blanks must be generated with complete metadata, so
  `blank_not_quantifiable_rate` must be 0 for a valid B2 stress run.

B1 hard blockers for C1b planning:

- any AsLS area exceeds raw area in Tier A or B1;
- any B1 non-blank AsLS corrected area is negative;
- any selected ISTD Tier A row shows wrong RT identity or unacceptable boundary
  expansion;
- B1 fixture coverage is incomplete for a Tier A observed selected-family
  pattern;
- AsLS median absolute error exceeds linear-edge median absolute error on a B1
  production-like class where linear-edge is expected to fail;
- AsLS median relative error exceeds 10% on a B1 production-like non-blank class
  and linear-edge is not worse on the same class;
- AsLS median relative error exceeds 25% on any B1 production-like non-blank
  class regardless of linear-edge performance;
- `flat_peak_control` production-like median relative error exceeds 5%.

B1 caution signals that do not automatically block C1b planning:

- B1 p95 relative error exceeds a class threshold but the median and physical
  impossibility checks pass;
- low scan-density or under-sampled B1-adjacent rows fail while production-like
  rows pass;
- a relevant class passes only by a small margin. The closeout must name the
  class and recommend Tier C follow-up before retirement.

B1 rows with median relative error above 10% but below the absolute hard cap may
support C1b planning only when AsLS is still materially better than linear-edge.
They must set `tier_b1_accuracy_scope=PLANNING_ONLY_REQUIRES_TIER_C` and cannot
contribute to `GO_FOR_LINEAR_EDGE_RETIREMENT` without passing Tier C
AsLS-vs-linear-edge baseline evidence for the affected morphology.

B2 stress blockers for linear-edge retirement:

- any B2 stress row has AsLS area above raw area or negative non-blank area;
- heldout blank false-positive rate exceeds 5%;
- any heldout blank is marked `blank_not_quantifiable`;
- B2 coelution, low-S/N, clipping, or local-distortion failures are unresolved
  by real Tier C or an accepted retirement-safety disposition.

B2 stress blockers must not by themselves emit `NO_GO_KEEP_LINEAR_EDGE` for
`decision_target=c1b-plan`. They emit stress status fields and may keep
`decision_target=linear-edge-retirement` at `REQUIRES_TIER_C` or
`NO_GO_KEEP_LINEAR_EDGE` depending on the supplied real evidence.

These tolerances are initial engineering thresholds. If methodology review
changes them, the change must happen before the heldout gate run and must
produce a new `tolerance_profile` version.

## Tier C - Real AsLS-vs-Linear-Edge Baseline Evidence Axis

Tier C is required for `GO_FOR_LINEAR_EDGE_RETIREMENT`. It is a real-data
baseline-evidence gate, not a manual-integration truth gate. A methodology
waiver may document why Tier C is unavailable and keep the gate planning-only,
but it cannot turn synthetic-only evidence into retirement authority.

For `GO_FOR_LINEAR_EDGE_RETIREMENT`, Tier C must include a current-code
AsLS-vs-linear-edge baseline audit over real selected traces plus a
blank/carryover safety disposition or an explicit exclusion/pass-through
contract. Blank or carryover evidence by itself is supplemental safety evidence,
not retirement authority.

Accepted Tier C axis:

- `asls_vs_linear_edge_baseline_audit`: a real cohort generated by
  `tools/diagnostics/p2_baseline_truth_audit.py` or a schema-compatible
  successor. It must compare AsLS and linear-edge on the same selected trace and
  boundary, emit `baseline_truth_audit_rows.tsv`,
  `baseline_truth_audit_summary.tsv`, `baseline_truth_audit.json`,
  `baseline_truth_audit.md`, and linked baseline plots. It must cover selected
  ISTDs, old P2 PASS/FAIL families that moved area, and high-risk morphology
  rows available in the current validation cohort. Relevant external standards
  or non-ISTD targets may be included when available, but they are not required
  to convert this into a manual truth-comparison exercise.

Tier C GO evidence is qualitative-plus-machine-readable:

- summary rows must support `linear_edge_over_subtraction_plausible` or
  `methods_similar` for the families being used as retirement evidence;
- any `asls_under_subtraction_plausible`, `mixed_or_review_required`,
  `not_assessable`, negative-area, or raw-area-exceedance row must have a
  machine-readable blocker or reviewed disposition;
- linked plots must show the raw trace, linear-edge baseline, AsLS baseline, and
  peak start/apex/end markers for the reviewed families;
- reviewer disposition must reference the plot path and row identifiers
  (`target_label`, `feature_family_id`, `sample_stem`, RT/window);
- `median_asls_vs_linear_pct`, `max_asls_vs_linear_pct`, and subtraction
  percentages are descriptive ranking/context fields only. They must not be
  converted into a fixed required improvement ratio.

Tier C disposition rollup must be machine-readable. `family_dispositions` must
use these statuses:

- `PASS_BASELINE_SUPPORTED`: reviewed rows support
  `linear_edge_over_subtraction_plausible`;
- `PASS_METHODS_SIMILAR`: all reviewed rows are `methods_similar`, so retirement
  is not justified by a large area difference but also is not blocked by this
  family;
- `REQUIRES_REVIEW`: at least one row is `mixed_or_review_required` or
  `not_assessable`, or the plot/review record is incomplete;
- `FAIL`: at least one row has a hard AsLS blocker or reviewed evidence against
  AsLS baseline plausibility;
- `INCONCLUSIVE`: required source artifacts, hashes, row identifiers, or plots
  are missing or stale.

`tier_c_row_blockers` must use a closed enum:

- `asls_under_subtraction_plausible`;
- `asls_area_exceeds_raw_area`;
- `asls_negative_nonblank_area`;
- `mixed_or_review_required`;
- `not_assessable`;
- `missing_or_stale_plot`;
- `missing_row_identifier`;
- `stale_artifact_hash`;
- `unsupported_classification`.

`tier_c_baseline_evidence_status` rolls up from dispositions:

- `PASS` only when every retirement-evidence family is
  `PASS_BASELINE_SUPPORTED` or `PASS_METHODS_SIMILAR`, at least one family is
  `PASS_BASELINE_SUPPORTED`, no row blocker remains unresolved, and all required
  plots/hashes are current;
- `FAIL` when any family disposition is `FAIL` or any hard blocker remains
  unresolved;
- `NOT_PROVIDED` when the evidence file is absent;
- `REQUIRES_REVIEW` family dispositions must not roll up to `PASS`. For
  `decision_target=linear-edge-retirement`, valid but unresolved review
  dispositions emit `REQUIRES_TIER_C`; missing, stale, or incomplete review
  artifacts emit the relevant `INCONCLUSIVE_*` status;
- malformed, stale, unsupported-enum, or incomplete disposition evidence emits
  `INCONCLUSIVE_INVALID_INPUT` or the more specific `INCONCLUSIVE_*` status
  instead of a `PASS`/`FAIL` rollup.

Required supplemental safety disposition:

- blank/carryover behavior on real blank or carryover-control rows when those
  rows are part of the affected output scope; or
- a machine-checkable exclusion/pass-through contract proving the affected
  outputs do not consume blank/carryover quantitation for the retirement scope.

When Tier B2 synthetic blank false positives exceed the stress threshold, a
plain statement that no blank/carryover controls exist is not enough for
retirement. It keeps `decision_target=linear-edge-retirement` at
`REQUIRES_TIER_C` unless the exclusion/pass-through contract above is supplied
and reviewed.

Tier B2 stress results determine which Tier C or safety evidence is required:

- synthetic blank/carryover false positives require real blank/carryover review
  or the machine-checkable exclusion/pass-through contract above;
- coelution stress failures require boundary/peak-purity review unless the
  fixture truth is redefined as full integrated signal inside the accepted
  boundary;
- low-S/N, clipping, or local-distortion stress failures require real cohort
  evidence only when those states are observed in selected ISTD or downstream
  target rows.

Tier C evidence must be provided as
`docs/superpowers/fixtures/asls_truth_tier_c_evidence.json` or an explicit CLI
argument to the same schema. Required fields:

- `tier_c_axis` (`asls_vs_linear_edge_baseline_audit`);
- `tier_c_status` (`PASS`, `FAIL`, `NOT_PROVIDED`, or `MIXED`); this is an
  aggregate display field only and must not drive c1b-plan decisions by itself;
- `tier_c_baseline_evidence_status` (`PASS`, `FAIL`, or `NOT_PROVIDED`);
- `blank_safety_status` (`PASS`, `FAIL`, `NOT_PROVIDED`, or
  `NOT_APPLICABLE_WITH_EXCLUSION`);
- `ratio_metrics_are_descriptive` (`true` required);
- `fixed_area_uplift_threshold` (`null` required);
- `baseline_truth_artifacts`, including rows TSV, summary TSV, JSON, Markdown,
  plot directory, and hashes;
- `family_dispositions`, with one record per reviewed family containing
  `target_label`, `feature_family_id`, covered samples, dominant
  classification, review status, plot path, `family_disposition`,
  `tier_c_row_blockers`, reviewer disposition, and reason;
- `affected_outputs`, listing every public output/consumer included in the
  retirement scope;
- `blank_control_evidence_status` (`PASS`, `FAIL`, `NOT_PROVIDED`, or
  `NOT_APPLICABLE_WITH_EXCLUSION`);
- `blank_rows_absence_proof`, required when blank/carryover controls are not
  present in the scoped artifacts;
- `consumer_contract_tests`, required when
  `blank_safety_status=NOT_APPLICABLE_WITH_EXCLUSION`;
- `stress_axis_dispositions`, a machine-readable list with one record per
  B2 stress axis. Each record must include `stress_axis`, `status` (`PASS`,
  `FAIL`, `NOT_REQUIRED`, or `NOT_PROVIDED`), `decision_scope`
  (`C1B_RELEVANCE` or `RETIREMENT_ONLY`), evidence refs/hashes, and the
  rationale for `NOT_REQUIRED`;
- row/sample counts, raw-file count when applicable, selected ISTD count,
  high-risk morphology count, covered target classes, and known exclusions;
- reviewer or generator identity;
- scope of outputs and target classes covered.

Waiver contract:

If Tier C is unavailable, the methodology owner may provide
`docs/superpowers/fixtures/asls_truth_methodology_waiver.json`. The waiver must
include:

- `methodology_owner` from the approved owner allowlist;
- date and branch/worktree scope;
- exact decision being waived; waiver cannot by itself authorize
  `GO_FOR_LINEAR_EDGE_RETIREMENT`;
- waived Tier C evidence and why it is unavailable or not required;
- exact output contracts covered;
- target classes and sample classes covered;
- explicit blank/carryover disposition;
- accepted residual risks;
- signed or otherwise approved review artifact path and hash;
- parseable expiry date or revalidation trigger that is after the review date;
- evidence artifacts and hashes that support the waiver;
- statement that C1b may delete linear-edge only after C1a, C5, and rollback
  column deprecation prerequisites are satisfied.

Without valid Tier C baseline evidence, a Tier A + B1 pass with unresolved or
passing B2 stress evidence must emit `REQUIRES_TIER_C`, not
`GO_FOR_LINEAR_EDGE_RETIREMENT`, even if a waiver file is present. A waiver
documents why the gate remains planning-only; it is not a retirement substitute.

Retirement prerequisite contract:

Even with passing Tier C, `GO_FOR_LINEAR_EDGE_RETIREMENT`
requires `docs/superpowers/fixtures/asls_truth_retirement_prerequisites.json`
or an explicit CLI argument to the same schema. Required fields:

- `c1a_status` (`LANDED_VALIDATED` required);
- `c5_status` (`LANDED_VALIDATED` required);
- `rollback_column_status` (`DEPRECATED_BY_APPROVED_SCHEMA_NOTE` required);
- links and hashes for the C1a validation note, C5 validation note, and
  rollback-column schema/deprecation note;
- accepted post-rollback audit schema artifact path and hash; this must be a
  tabular TSV/CSV schema artifact, not an arbitrary hashed note or Markdown
  report;
- machine-checkable confirmation that `area_baseline_corrected_linear_edge` and
  `baseline_score_linear_edge` are absent from the accepted post-rollback audit
  schema, represented as a list of non-empty strings;
- the post-rollback schema artifact must still prove the audit surface is the
  expected one by including core columns such as `feature_family_id`,
  `sample_stem`, `status`, `area`, `apex_rt`, `peak_start_rt`, `peak_end_rt`,
  `area_baseline_corrected`, `area_uncertainty`, `baseline_type`,
  `baseline_score`, and `integration_scan_count`;
- affected public contracts reviewed;
- reviewer identity and date.

If Tier A, B1, B2 stress safety, and Tier C baseline evidence pass but the
prerequisite manifest is missing or schema-valid but not satisfied, the gate
must emit `REQUIRES_RETIREMENT_PREREQS`. Input/freshness outcomes must be
separated:

- malformed, unreadable, unsupported-enum, or schema-incompatible supplied
  evidence files emit `INCONCLUSIVE_INVALID_INPUT`;
- evidence artifact references embedded in Tier C, waiver, and prerequisite
  JSON must resolve independently of process cwd; repo-relative paths are
  resolved from the input JSON's repository root;
- Tier A artifact hash drift, stale Tier A artifact hashes, generated SHA
  mismatch, or missing current-code compatibility artifact emit
  `INCONCLUSIVE_REGENERATE_TIER_A`;
- fixture-lock hash drift emits `INCONCLUSIVE_FIXTURE_LOCK_CHANGED`;
- missing P2b/85RAW accepted-output evidence for retirement-target evaluation
  emits `INCONCLUSIVE_MISSING_P2B_85RAW_ACCEPTANCE`.

All of these exit `2` and are evidence/input gaps, not scientific `NO_GO`.

## Diagnostic CLI And Schema Contract

Planned CLI:

```powershell
.venv\Scripts\python.exe -m tools.diagnostics.asls_truth_validation `
  --tier-a-rows output\phase1_p2_baseline_truth_audit_all_statuses\baseline_truth_audit_rows.tsv `
  --tier-a-summary output\phase1_p2_baseline_truth_audit_all_statuses\baseline_truth_audit_summary.tsv `
  --tier-a-json output\phase1_p2_baseline_truth_audit_all_statuses\baseline_truth_audit.json `
  --tier-a-report output\phase1_p2_baseline_truth_audit_all_statuses\baseline_truth_audit.md `
  --tier-a-manifest docs\superpowers\fixtures\asls_truth_tier_a_expected_manifest.json `
  --fixture-manifest docs\superpowers\fixtures\asls_truth_validation_fixture_manifest.json `
  --fixture-lock docs\superpowers\fixtures\asls_truth_validation_fixture_lock.json `
  --p2b-85raw-acceptance-manifest docs\superpowers\fixtures\asls_truth_p2b_85raw_acceptance_manifest.json `
  --tier-c-evidence docs\superpowers\fixtures\asls_truth_tier_c_evidence.json `
  --methodology-waiver docs\superpowers\fixtures\asls_truth_methodology_waiver.json `
  --retirement-prereq-manifest docs\superpowers\fixtures\asls_truth_retirement_prerequisites.json `
  --decision-target c1b-plan `
  --output-dir output\phase1_p2c_asls_truth_validation
```

`--decision-target` values:

- `c1b-plan`: Tier A + Tier B1 can emit
  `GO_FOR_C1B_PLAN_SYNTHETIC_ONLY` when Tier C is absent; Tier B2 is reported as
  stress evidence and cannot by itself emit `NO_GO_KEEP_LINEAR_EDGE`;
- `linear-edge-retirement`: Tier A + Tier B1 + Tier B2 without passing Tier C
  baseline evidence and blank/carryover safety disposition or exclusion must
  emit `REQUIRES_TIER_C`, even when a waiver is supplied.

Decision rollup rule:

- for `decision_target=c1b-plan`, only Tier A plus `tier_b1_status` may drive
  `benchmark_status=FAIL` or `NO_GO_KEEP_LINEAR_EDGE`; Tier B2, blank safety,
  and retirement-only Tier C stress dispositions must be reported separately;
- for `decision_target=linear-edge-retirement`, Tier B2 stress status, Tier C
  baseline evidence, blank safety, and retirement prerequisites participate in
  the final gate decision.

Exit codes:

- `0`: diagnostic completed and `gate_decision` is
  `GO_FOR_LINEAR_EDGE_RETIREMENT`;
- `1`: diagnostic completed and `gate_decision` is `NO_GO_KEEP_LINEAR_EDGE`;
- `2`: invalid input, missing artifact, stale/schema-incompatible input, or
  `INCONCLUSIVE_*`;
- `3`: diagnostic completed and `gate_decision` is
  `GO_FOR_C1B_PLAN_SYNTHETIC_ONLY`, `REQUIRES_TIER_C`, or
  `REQUIRES_RETIREMENT_PREREQS`.

Required outputs:

- `asls_truth_validation_rows.tsv`
- `asls_truth_validation_summary.tsv`
- `asls_truth_validation_coverage.tsv`
- `asls_truth_validation.json`
- `asls_truth_validation_fixture_manifest.json`
- `asls_truth_validation_fixture_lock.json`
- `asls_truth_validation_tier_a_manifest.json`
- `asls_truth_validation_p2b_85raw_acceptance_manifest.json` when supplied
- `asls_truth_validation_tier_c_evidence.json` when Tier C is supplied
- `asls_truth_validation_methodology_waiver.json` when a waiver is supplied
- `asls_truth_validation_retirement_prerequisites.json` when prerequisites are supplied
- `asls_truth_validation.md`
- optional plots under `plots/`

`asls_truth_validation_summary.tsv` required columns:

- `readiness_status` (`diagnostic_only`);
- `benchmark_status` (`PASS`, `FAIL`, `INCONCLUSIVE`), computed from the
  decision-driving status only: B1 for `decision_target=c1b-plan`, and
  B1+B2/Tier C retirement safety for `decision_target=linear-edge-retirement`;
- `synthetic_decision_status` (`PASS`, `FAIL`, or `INCONCLUSIVE`), equal to B1
  status for `decision_target=c1b-plan`;
- `gate_decision`
  (`GO_FOR_C1B_PLAN_SYNTHETIC_ONLY`, `GO_FOR_LINEAR_EDGE_RETIREMENT`,
  `NO_GO_KEEP_LINEAR_EDGE`, `REQUIRES_TIER_C`,
  `REQUIRES_RETIREMENT_PREREQS`, or `INCONCLUSIVE_*`);
- `fixture_version`;
- `tolerance_profile`;
- `legacy_fixture_status` (`CURRENT`, `LEGACY_V1_NON_AUTHORITATIVE`, or
  `NOT_APPLICABLE`);
- `decision_target`;
- `fixture_manifest_hash`;
- `fixture_lock_hash`;
- `tier_a_generated_by_git_sha`;
- `tier_a_current_code_compatibility_status`;
- `tier_a_rows_hash`;
- `tier_a_summary_hash`;
- `tier_a_json_hash`;
- `tier_a_report_hash`;
- `tier_a_manifest_hash`;
- `tier_a_expected_family_count`;
- `tier_a_observed_family_count`;
- `tier_a_expected_row_count`;
- `tier_a_observed_row_count`;
- `tier_a_source_input_hashes`;
- `p2b_85raw_acceptance_ref`;
- `p2b_85raw_acceptance_hash`;
- `asls_lam`;
- `asls_p`;
- `asls_n_iter`;
- `generator_seed`;
- `bounds_policy`;
- `heldout_row_count`;
- `tier_b1_status` (`PASS`, `FAIL`, or `INCONCLUSIVE`);
- `tier_b1_accuracy_scope` (`RETIREMENT_ELIGIBLE`,
  `PLANNING_ONLY_REQUIRES_TIER_C`, or `FAIL`);
- `tier_b2_status` (`PASS`, `FAIL`, `STRESS_REQUIRES_TIER_C`, or
  `NOT_RUN`);
- `fixture_scope_status` (`PASS`, `INCONCLUSIVE_FIXTURE_SCOPE_MISMATCH`, or
  `INCONCLUSIVE_FIXTURE_GAP`);
- `tier_b1_heldout_row_count`;
- `b1_adjacent_stress_row_count`;
- `tier_b2_heldout_row_count`;
- `tier_b1_hard_blocker_count`;
- `tier_b2_stress_blocker_count`;
- `production_like_heldout_row_count`;
- `stress_heldout_row_count`;
- `hard_blocker_count`;
- `max_asls_raw_area_exceedance_count`;
- `max_negative_nonblank_area_count`;
- `blank_false_positive_rate`;
- `blank_not_quantifiable_rate`;
- `blank_synthetic_scope` (`B2_STRESS`);
- `coverage_status`;
- `b1_coverage_status`;
- `b2_stress_status`;
- `unmapped_observed_pattern_count`;
- `tier_c_axis`;
- `tier_c_status`;
- `tier_c_baseline_evidence_status`;
- `tier_c_row_blocker_count`;
- `tier_c_review_required_count`;
- `blank_safety_status`;
- `stress_axis_disposition_statuses`;
- `tier_c_evidence_ref`;
- `tier_c_evidence_hash`;
- `waiver_ref`;
- `methodology_waiver_hash`;
- `methodology_owner`;
- `waiver_scope`;
- `waiver_valid`;
- `waiver_expiry_or_revalidation_trigger`;
- `retirement_prereq_status`;
- `c1a_status`;
- `c5_status`;
- `rollback_column_status`;
- `retirement_prereq_manifest_hash`;
- `worst_heldout_median_relative_error_pct`;
- `worst_heldout_p95_relative_error_pct`;
- `previous_failed_run_refs`.

`asls_truth_validation_rows.tsv` required columns:

- `tier`;
- `tier_b_layer`;
- `split`;
- `fixture_class`;
- `fixture_id`;
- `replicate_id`;
- `stress_role`;
- `production_like_bounds_status`;
- `scan_density_stratum`;
- `integration_point_count`;
- `integration_width_min`;
- `target_label`;
- `feature_family_id`;
- `raw_area`;
- `true_area`;
- `linear_edge_area`;
- `asls_area`;
- `linear_edge_abs_error`;
- `asls_abs_error`;
- `linear_edge_relative_error_pct`;
- `asls_relative_error_pct`;
- `asls_error_over_linear_error`;
- `asls_exceeds_raw_area`;
- `asls_negative_nonblank_area`;
- `blank_false_positive`;
- `blank_not_quantifiable`;
- `asls_area_uncertainty`;
- `asls_baseline_residual_mad`;
- `asls_area_uncertainty_noise_source`;
- `rt_identity_status`;
- `boundary_status`;
- `blocker_scope` (`B1_C1B`, `B2_RETIREMENT`, `CAUTION`,
  `REPORTING_ONLY`, or empty);
- `row_status`;
- `failure_reasons`.

`asls_truth_validation_coverage.tsv` required columns:

- `observed_pattern`;
- `target_label`;
- `feature_family_id`;
- `observed_row_count`;
- `required_b1_fixture_classes`;
- `covered_b1_fixture_classes`;
- `b2_stress_fixture_classes`;
- `coverage_status`;
- `fixture_scope_status`;
- `unmapped_reason`.

`asls_truth_validation.json` must include:

- schema version;
- command line;
- code git SHA when available;
- run timestamp;
- fixture manifest object and hash;
- fixture lock object and hash;
- Tier A manifest, artifact paths for rows/summary/JSON/report, source input
  hashes, and artifact hashes;
- accepted P2b/85RAW validation artifact refs and hashes when supplied;
- Tier A to Tier B coverage records;
- AsLS parameters;
- tolerance profile;
- separate Tier B1 and Tier B2 aggregate summaries, including blocker scopes,
  production-like/stress row counts, and fixture-scope status;
- Tier C evidence object and hash when provided;
- methodology waiver object and hash when provided;
- retirement prerequisite object and hash when provided;
- row records;
- summary records;
- previous failed run references.

## GO / NO-GO Rules

### GO for C1b planning only

The gate may emit `GO_FOR_C1B_PLAN_SYNTHETIC_ONLY` only when:

- Tier A artifacts are present, fresh, and schema-compatible;
- Tier A same-peak guard passes;
- Tier A to Tier B1 coverage matrix is complete;
- Tier B1 production-like heldout benchmark status is `PASS`;
- Tier B2 stress status is reported separately, even when unresolved;
- fixture scope status is `PASS` for the B1 rows used by this decision;
- no AsLS raw-area exceedance appears in Tier A or B1;
- no B1 non-blank synthetic peak has negative AsLS corrected area;
- RT and boundary evidence remains stable on the selected ISTD set;
- Tier C is missing, not yet reviewed, or only fails retirement-only B2 stress
  axes; invalid supplied Tier C is `INCONCLUSIVE_*`;
- supplied Tier C evidence must not contain
  `tier_c_baseline_evidence_status=FAIL` for a B1-relevance observed morphology
  covering the selected ISTD scope.

This permits a C1b plan draft only. It does not permit implementation that
deletes linear-edge.

### GO for linear-edge retirement

The gate may emit `GO_FOR_LINEAR_EDGE_RETIREMENT` only when:

- all `GO_FOR_C1B_PLAN_SYNTHETIC_ONLY` conditions pass;
- Tier B2 stress safety is either passing or explicitly resolved by Tier C /
  retirement-safety disposition;
- Tier C AsLS-vs-linear-edge baseline evidence passes, with ratio metrics marked
  descriptive and no fixed area uplift threshold;
- blank/carryover safety disposition is `PASS` or
  `NOT_APPLICABLE_WITH_EXCLUSION`;
- every B2 stress axis required by the synthetic stress results has `PASS` or
  `NOT_REQUIRED` with a reviewed rationale;
- a valid retirement prerequisite manifest confirms C1a, C5, and rollback-column
  deprecation prerequisites are already landed and validated;
- the closeout note names the affected public contract and confirms whether
  `alignment_matrix.tsv`, `alignment_cell_integration_audit.tsv`, targeted
  candidate TSVs, and downstream consumers are affected;
- the closeout note confirms that P2b temporary linear-edge rollback audit
  columns are either already deprecated by an approved schema note or remain a
  blocker for C1b implementation;
- C1a and C5 are landed and validated before C1b implementation starts.

### NO-GO

The gate emits `NO_GO_KEEP_LINEAR_EDGE` for `decision_target=c1b-plan` only if a
Tier A or B1 relevance hard blocker is present:

- AsLS exceeds raw area in a reviewed Tier A row or B1 production-like row;
- AsLS creates negative corrected area in a B1 non-blank row;
- AsLS is worse than linear-edge on a B1 production-like heldout class where
  linear-edge is expected to fail;
- selected ISTD evidence shows wrong RT identity or unacceptable boundary
  expansion rather than a pure baseline disagreement;
- B1 fixture coverage cannot represent a Tier A observed selected-family
  pattern after reviewed fixture revision;
- a supplied Tier C evidence file has
  `tier_c_baseline_evidence_status=FAIL` for a B1-relevance observed morphology
  covering the selected ISTD scope.

For `decision_target=linear-edge-retirement`, the gate also emits
`NO_GO_KEEP_LINEAR_EDGE` when:

- Tier B2 stress failures remain unresolved after required Tier C or
  retirement-safety evidence is supplied;
- a supplied Tier C evidence file has
  `tier_c_baseline_evidence_status=FAIL`;
- a valid Tier C safety-disposition file shows blank/carryover hard failure.

B2 stress failures such as synthetic blank false positives, coelution-only
truth disagreement, low-S/N stress, or clipping stress must not emit
`NO_GO_KEEP_LINEAR_EDGE` for `decision_target=c1b-plan` unless the fixture class
has been promoted to B1 by reviewed real Tier A/Tier C evidence.

### Inconclusive / Requires More Evidence

Use `INCONCLUSIVE_*` when artifacts are missing, stale, schema-incompatible, or
coverage is incomplete. Use `INCONCLUSIVE_FIXTURE_SCOPE_MISMATCH` when the
fixture lock is valid but the rows used for B1 pass/fail are broader than the
real Tier A selected-family scope, such as fixed 64-point stress windows being
used as production-like rows. Use `REQUIRES_TIER_C` when Tier A and B1 pass but
`decision_target=linear-edge-retirement` and there is no passing Tier C evidence
with `tier_c_baseline_evidence_status=PASS` plus B2/blank safety disposition or
exclusion. Use `REQUIRES_RETIREMENT_PREREQS` when Tier A, B1, B2/Tier C, and
safety evidence pass but the retirement prerequisite manifest is missing or
schema-valid but not satisfied. Use `INCONCLUSIVE_INVALID_INPUT` when a supplied
evidence file is malformed, unreadable, uses unsupported enum values, or is
schema-incompatible. Use `INCONCLUSIVE_REGENERATE_TIER_A` for Tier A
freshness/hash/current-code drift. Use `INCONCLUSIVE_FIXTURE_LOCK_CHANGED` for
fixture-lock hash drift. Use `INCONCLUSIVE_MISSING_P2B_85RAW_ACCEPTANCE` when
retirement-target evaluation lacks accepted P2b/85RAW output refs.

Inconclusive is an evidence gap, not proof that linear-edge is better.

## Implementation Scope

In scope for a future implementation plan:

- frozen fixture manifest and per-row fixture lock under
  `docs/superpowers/fixtures/`;
- B1/B2 gate-layer assignment, production-like bounds derivation from Tier A,
  and fixture-scope mismatch reporting;
- deterministic synthetic trace generator;
- diagnostic runner for Tier A aggregation, B1 benchmark, B2 stress audit, and
  optional Tier C evidence summary;
- unit tests for fixture generation, true-area formulas, comparator metrics,
  gate classification, output schema, and exit-code mapping;
- closeout note recording the decision.

Out of scope:

- changing AsLS parameters in production;
- deleting linear-edge;
- changing `alignment_matrix.tsv`;
- changing RT resolver behavior;
- introducing third-party feature-finding tools;
- requiring `.mzML` conversion.

## Validation Contract

Before using this spec to unblock C1b planning:

1. Review and freeze the fixture manifest, fixture lock, and Tier A manifest
   before the first gate run.
2. Run the synthetic truth-validation diagnostic with B1/B2 split enabled.
3. Verify or regenerate Tier A selected ISTD truth-audit artifacts.
4. Confirm B1 production-like rows derive their bounds from Tier A
   point-count/RT-width distributions, not from fixed broad stress windows.
5. Run narrow tests covering the generator, formulas, comparator, schema, and
   gate summary.
6. Record a closeout note under `docs/superpowers/notes/`.
7. Update C1b only if the closeout note says either
   `GO_FOR_C1B_PLAN_SYNTHETIC_ONLY` or `GO_FOR_LINEAR_EDGE_RETIREMENT`.

Before deleting linear-edge in implementation:

1. Confirm C1a has landed and passed validation.
2. Confirm C5 has migrated all callers to the single integration entry and
   passed behavioral parity validation.
3. Confirm rollback-column schema deprecation has landed and the accepted
   post-rollback audit schema proves linear-edge rollback columns are absent.
4. Confirm this spec has a closeout note with
   `GO_FOR_LINEAR_EDGE_RETIREMENT`.

## Stop Conditions

Stop and request methodology review if:

- the benchmark result contradicts the baseline-truth audit plots or
  reviewer dispositions;
- AsLS looks better only because the synthetic fixture is unrealistic;
- chosen tolerances decide the result rather than trace evidence;
- heldout results differ materially from calibration results;
- B2 stress evidence is being used to block C1b planning without reviewed
  promotion to B1;
- B1 passes but selected ISTD RT/boundary evidence regresses;
- a second synthetic-only iteration is inconclusive.

## Cleanup Handoff

If this spec reaches `GO_FOR_C1B_PLAN_SYNTHETIC_ONLY`, Cleanup may write a C1b
plan but must keep linear-edge deletion blocked. The plan must still preserve a
method-preserving route until Tier C/B2 retirement safety and C1a/C5/rollback
prerequisites are satisfied.

If this spec reaches `GO_FOR_LINEAR_EDGE_RETIREMENT`, Cleanup may implement C1b
only after C1a, C5, and rollback-column schema deprecation have landed and
validated.

If this spec remains `INCONCLUSIVE_*` because of B1 fixture scope, C1b planning
remains paused until the B1 lock is fixed. If it reaches `REQUIRES_TIER_C`, C1b
planning may proceed only when the closeout explicitly says the missing evidence
is retirement-only. If it reaches `NO_GO_KEEP_LINEAR_EDGE`, C5 must stay
method-preserving and C1b deletion remains paused.
