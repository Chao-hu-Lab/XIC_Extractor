# Shared Peak Identity V2 Diagnostic Note

## Verdict

V2 completed as `exploratory_only`.

The current seed-row shadow labels can organize the manual semantics, but the
machine-only evidence chain is not ready for autonomous pass/fail labels.

After the literature-backed provenance update, the more precise verdict is:
the current machine status labels are often directionally close to manual labels,
but the decisive shape / pattern / opportunity facts are still proxy-only or
manual-oracle-derived rather than machine-observed.

After adding optional CWT-shape and Tier2 raw-trace evidence inputs, the current
verdict is sharper again: machine-observed evidence is now present but partial.
CWT and raw-trace sidecars remove the need to call shape and intensity
opportunity entirely manual-derived, but they expose conflicts and still do not
provide candidate-aligned MS2 / neutral-loss pattern evidence or a DDA
opportunity policy.

After adding literature-guarded CID neutral-loss / product-ion context from
`alignment_review.tsv`, family-level pattern context is recorded only as
context/proxy evidence. It can explain why a family-level DNA-dR-like hypothesis
is plausible, but it no longer closes row-level `formal_pattern_metric`.
Row-level pattern evidence must come from a candidate/source-aligned sidecar or
the explicit RAW-boundary fallback described below.

After tightening CWT conflict semantics and support-status accounting, rows are
counted as `machine_observed_sufficient` when all decisive manual tags have
machine-observed basis and `missing_machine_evidence` is empty. CWT now compares
only against manual shape tags; it no longer treats every manual `fail` as a
shape failure. RT conflict also has a machine-observed component when
`rt_delta_sec` exceeds the alignment preferred RT window.

The follow-up implementation adds a fail-closed
`--candidate-ms2-pattern-evidence-tsv` input contract and a matching
`--candidate-ms2-pattern-batch-index` producer for sample/candidate-aligned MS2
pattern evidence. The real run below now generates
`shared_peak_identity_candidate_ms2_pattern_evidence.tsv` from the same 8RAW
discovery batch index that fed the alignment run. This intentionally does not
use `output/peak_candidates.tsv`, because that file is target-label oriented and
does not provide a reviewed `feature_family_id + sample_stem` join for these
oracle rows.

The latest checkpoint adds an opt-in RAW-backed fallback for rows that lack
`alignment_cells.source_candidate_id`. It reuses the existing Thermo RAW reader
and `neutral_loss.collect_candidate_ms2_evidence`; it does not add a new MS/MS
interpretation model. The fallback is deliberately conservative after literature
review: strict neutral-loss / product-ion observations may support a row, but
missing DDA product evidence is not treated as absence. A conflict is reported
only when a boundary-aligned precursor MS2 scan exists and the nearest
non-matching product peak is the spectrum base peak outside the diagnostic
product window.

## Run

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python -m tools.diagnostics.shared_peak_identity_explanation `
  --manual-oracle-tsv docs\superpowers\fixtures\shared_peak_identity_manual_oracle_v1.tsv `
  --alignment-review-tsv output\tiered_backfill_candidate_gate_8raw_current\alignment_review.tsv `
  --alignment-cells-tsv output\tiered_backfill_candidate_gate_8raw_current\alignment_cells.tsv `
  --candidate-gate-tsv output\tier2_v0_1_coherence_8raw_current_gate\alignment_production_candidate_gate.tsv `
  --enable-blast-radius `
  --blast-radius-8raw-run output\tiered_backfill_candidate_gate_8raw_current `
  --blast-radius-85raw-run output\tiered_backfill_candidate_gate_85raw_current `
  --optional-blast-radius-artifact candidate_gate_8raw=output\tiered_backfill_candidate_gate_8raw_current\alignment_production_candidate_gate.tsv `
  --optional-blast-radius-artifact candidate_gate_85raw=output\tiered_backfill_candidate_gate_85raw_current\alignment_production_candidate_gate.tsv `
  --enable-shadow-label-alignment `
  --cwt-shape-evidence-tsv output\tier2_v0_1_coherence_8raw_current\alignment_tier2_cwt_manual_agreement_probe_relaxed.tsv `
  --tier2-trace-evidence-tsv output\tier2_v0_1_coherence_8raw_current\alignment_tier2_trace_evidence.tsv `
  --candidate-ms2-pattern-batch-index local_validation_artifacts\discovery\accepted_p8b\8raw\discovery_batch_index.csv `
  --candidate-ms2-pattern-raw-dll-dir C:\Xcalibur\system\programs `
  --output-dir output\shared_peak_identity_evidence_explanation_v2
```

## Output

- `output/shared_peak_identity_evidence_explanation_v2/shared_peak_identity_shadow_labels.tsv`
- `output/shared_peak_identity_evidence_explanation_v2/shared_peak_identity_shadow_alignment_summary.tsv`
- `output/shared_peak_identity_evidence_explanation_v2/shared_peak_identity_v2_readiness.tsv`
- `output/shared_peak_identity_evidence_explanation_v2/shared_peak_identity_candidate_ms2_pattern_evidence.tsv`
- `output/shared_peak_identity_evidence_explanation_v2/shared_peak_identity_machine_evidence_support.tsv`
- `output/shared_peak_identity_evidence_explanation_v2/shared_peak_identity_v2_report.md`

## Key Facts

- `v2_gate_status`: `exploratory_only`
- `machine_only_labeler_ready`: `FALSE`
- `semantic_generalization_evidence`: `seed_only_manual_oracle_derived`
- `machine_evidence_basis`: `machine_observed_partial`
- `machine_evidence_supported_rows`: `12`
- `machine_observed_partial_rows`: `9`
- `machine_observed_conflict_rows`: `7`
- `machine_proxy_only_rows`: `3`
- `manual_oracle_derived_rows`: `11`
- `machine_evidence_coverage_fraction`: `0.387097`
- `blast_radius_assessed`: `not_assessed`
- `max_overfit_risk`: `unassessed`
- `blast_radius_stale_artifact_count`: `0`
- seed rows total: `39`
- shadow rows total: `40` including one context row
- aligned or partial decision rows: `31`
- contradicted rows: `0`
- context-only rows: `1`
- human-unjudgeable rows: `8`

Current machine status-label proximity:

- `proxy_agrees`: `21`
- `proxy_partial`: `2`
- `proxy_contradicts`: `8`
- `not_evaluable`: `8`
- `context_only`: `1`

Machine evidence provenance after CWT/Tier2 sidecars, candidate-MS2 sidecar /
RAW-boundary fallback, and shape-tag-aligned CWT conflict semantics:

- `machine_observed_sufficient`: `12`
- `machine_observed_partial`: `9`
- `machine_observed_conflict`: `7`
- `blocked_missing_metric`: `3`
- `not_evaluable`: `8`
- `context_only`: `1`
- `pattern_basis_status=machine_observed`: `26`
- `pattern_basis_status=mixed`: `8`
- `pattern_basis_status=machine_proxy`: `5`
- `pattern_basis_status=not_available`: `1`

Candidate-MS2 producer status counts:

- `candidate_ms2_pattern_status=supportive`: `25`
  - `21` from RAW boundary fallback.
  - `4` from direct discovery source candidates.
- `candidate_ms2_pattern_status=not_observed`: `9`
- `candidate_ms2_pattern_status=not_available`: `4`
- `candidate_ms2_pattern_status=conflict`: `1`

Supportive rows from direct discovery source candidates:

- FAM000610 / TumorBC2263: `TumorBC2263_DNA#10747`, `ms2_support=strong`,
  `matched_tag_count=1`, `matched_tag_names=DNA_dR`.
- FAM001227 / TumorBC2312: `TumorBC2312_DNA#3290`, `ms2_support=moderate`,
  `matched_tag_count=1`, `matched_tag_names=DNA_dR`.
- FAM001589 / TumorBC2312: `TumorBC2312_DNA#5954`, `ms2_support=moderate`,
  `matched_tag_count=1`, `matched_tag_names=DNA_dR`.
- FAM002175 / TumorBC2263: `TumorBC2263_DNA#26931`, `ms2_support=moderate`,
  `matched_tag_count=1`, `matched_tag_names=DNA_dR`.

FAM000144 remains fail-closed for candidate-aligned MS2 evidence:

FAM000144 now shows the intended distinction:

- BenignfatBC1151 still emits `not_available` because the current alignment cell
  is `absent` and has no boundary context for RAW MS2 probing.
- NormalBC2312 emits `supportive / sample_boundary_aligned`: `3` precursor MS2
  triggers in the boundary probe, `1` strict neutral-loss/product match,
  `best_loss_ppm=9.70487`, `raw_ms2_trace_strength=moderate`.
- TumorBC2312 emits `conflict / sample_boundary_aligned`: `1` boundary-aligned
  precursor MS2 trigger, `0` strict neutral-loss/product matches,
  `diagnostic_product_absence_reason=product_outside_diagnostic_window`, nearest
  product loss error `147223 ppm`, nearest product base ratio `1.0`. This closes
  the earlier `candidate_aligned_ms2_pattern` blocker for this reviewed fail
  row without using an RT/mz heuristic join.

The follow-up QC-near-injection MS1 pattern trial adds a separate
`diagnostic_only` sidecar. It is now wired into the V2 machine-evidence support
contract through `--qc-ms1-pattern-reference-evidence-tsv`, but remains an
evidence input rather than a product label switch:

- Tool: `tools/diagnostics/qc_ms1_pattern_reference.py`.
- Source traces:
  `output/shared_peak_identity_manual_followup/family_ms1_overlay_fam000144_qc_reference/fam000144_qc_reference_trace_data.json`.
- Sidecar:
  `output/shared_peak_identity_manual_followup/family_ms1_overlay_fam000144_qc_reference/fam000144_qc_reference_qc_ms1_pattern_reference.tsv`.
- The naive nearest-QC rule first selected QC3 for `TumorBC2312_DNA`, but QC3
  had no complete peak in this window. The producer therefore uses the nearest
  QC with a complete local peak before issuing a decisive status.
- With that guard, `TumorBC2312_DNA` is flagged `conflict` against
  `Breast_Cancer_Tissue_pooled_QC5`: target/QC apex separation is `78.3054 sec`,
  both local windows have complete signal, and pairwise shape similarity is
  `0.259605`. This matches the manual note that the RT 18.5 signal and the QC5
  RT 19.5 signal are not the same peak.
- `NormalBC2312_DNA` and `BenignfatBC1151_DNA` are `partial_support` against
  QC5: apex separations are `2.3197 sec` and `1.15036 sec`, respectively, but
  the conservative target-vs-QC shape score did not reach full supportive status.
- When rerun through
  `output/shared_peak_identity_evidence_explanation_v2_qc_ms1_reference_trial/`,
  the QC reference rows appear in `observed_machine_metrics` as
  `qc_ms1_reference_*` fields. The FAM000144 `TumorBC2312_DNA` row remains
  `machine_observed_sufficient`; the two pass rows move to
  `pattern_basis_status=machine_observed` but still carry
  `dda_opportunity_policy`, so they remain `machine_observed_partial`.
- The run-level verdict is still `exploratory_only` with
  `machine_evidence_basis=machine_observed_partial`; this integration improves
  the evidence chain but does not by itself make V2 product labels ready.

Rows currently counted as machine-observed sufficient:

- FAM000144: TumorBC2312.
- FAM000610: BenignfatBC1151, QC3, QC5, NormalBC2263, NormalBC2312,
  TumorBC2312.
- FAM001227: QC5, TumorBC2312.
- FAM002175: QC3, QC5, TumorBC2263.

## Required Evidence To Promote

The dominant missing or conflicting machine evidence is:

- `shape_metric_not_supportive`: `14`
- `formal_pattern_metric`: `8`
- `human_review_or_retire_from_training`: `8`
- `dda_opportunity_policy`: `6`
- `manual_scope_policy`: `3`
- `sample_level_negative_evidence`: `3`
- `matrix_rt_drift_policy`: `2`
- `delta_mass_family_model`: `1`

The V2 readiness artifact additionally reports these active machine-evidence
blockers after CWT/Tier2 evidence and CID/NL context:

- `dda_opportunity_policy`
- `formal_pattern_metric`
- `shape_metric_not_supportive`
- `manual_scope_policy`
- `sample_level_negative_evidence`
- `matrix_rt_drift_policy`

## MS1 Pattern / RT Drift Preconditions Follow-up

The 2026-05-30 follow-up adds diagnostic contracts for two missing V2 product
label preconditions:

- `--ms1-pattern-coherence-evidence-tsv`: sample-keyed MS1 constellation
  evidence for apex coherence, boundary overlap, shape correlation, relative
  pattern stability, local interference, and drift compatibility. Supportive
  rows can close `formal_pattern_metric`; contradictory rows fail closed as
  `pattern_metric_not_supportive`.
- `--matrix-rt-drift-policy-tsv`: sample-keyed independent RT drift policy
  evidence. `rt_drift_possible` closes when a machine-observed row is either
  `rt_close` or `drift_supported`, with `drift_compatible_status=compatible`;
  unsupported drift rows fail closed as `matrix_rt_drift_policy_not_supportive`.

The next checkpoint adds a diagnostic-only matrix RT drift policy producer. The
CLI can now write `shared_peak_identity_matrix_rt_drift_policy.tsv` from existing
alignment/RT artifacts via:

- `--generate-matrix-rt-drift-policy`: emits an alignment-cell-backed policy
  sidecar even when no external drift artifact exists, so `rt_close` and
  `inconclusive` are explicit machine-readable outcomes.
- `--matrix-rt-drift-policy-owner-edge-tsv`: consumes `owner_edge_evidence.tsv`
  rows with `rt_raw_delta_sec`, `rt_drift_corrected_delta_sec`, and
  `drift_prior_source`.
- `--matrix-rt-drift-policy-rt-normalization-families-tsv`: consumes
  `rt_normalization_families.tsv` rows with raw-vs-normalized family RT range
  improvement.
- `--matrix-rt-drift-policy-targeted-istd-summary-tsv` plus
  `--matrix-rt-drift-policy-rt-normalization-leave-one-out-tsv`: consumes
  target-level ISTD benchmark coverage plus injection-local leave-one-anchor-out
  trend evidence. This path is coverage-gated and is intended for 85RAW-like
  injection-order evidence, not 8RAW method-smoke subsets.

The producer prioritizes row-level `rt_close`, then owner-edge drift-corrected
support/conflict, then family-level RT-normalization support/conflict, then
target-level ISTD anchor-local trend support. Missing or unjoinable evidence
remains `inconclusive`, which does not close the V2 blocker.

## Matrix RT Drift Closeout Run

The closeout run used current 8RAW / 85RAW artifacts and did not read RAW or
fit a new RT model:

```powershell
python -m tools.diagnostics.shared_peak_identity_explanation `
  --manual-oracle-tsv docs\superpowers\fixtures\shared_peak_identity_manual_oracle_v1.tsv `
  --alignment-review-tsv output\tiered_backfill_candidate_gate_8raw_current\alignment_review.tsv `
  --alignment-cells-tsv output\tiered_backfill_candidate_gate_8raw_current\alignment_cells.tsv `
  --candidate-gate-tsv output\tier2_v0_1_coherence_8raw_current_gate\alignment_production_candidate_gate.tsv `
  --enable-blast-radius `
  --blast-radius-8raw-run output\tiered_backfill_candidate_gate_8raw_current `
  --blast-radius-85raw-run output\tiered_backfill_candidate_gate_85raw_current `
  --optional-blast-radius-artifact candidate_gate_8raw=output\tiered_backfill_candidate_gate_8raw_current\alignment_production_candidate_gate.tsv `
  --optional-blast-radius-artifact candidate_gate_85raw=output\tiered_backfill_candidate_gate_85raw_current\alignment_production_candidate_gate.tsv `
  --enable-shadow-label-alignment `
  --cwt-shape-evidence-tsv output\tier2_v0_1_coherence_8raw_current\alignment_tier2_cwt_manual_agreement_probe_relaxed.tsv `
  --tier2-trace-evidence-tsv output\tier2_v0_1_coherence_8raw_current\alignment_tier2_trace_evidence.tsv `
  --candidate-ms2-pattern-evidence-tsv output\shared_peak_identity_evidence_explanation_v2\shared_peak_identity_candidate_ms2_pattern_evidence.tsv `
  --generate-matrix-rt-drift-policy `
  --output-dir output\shared_peak_identity_evidence_explanation_v2_matrix_rt_drift_closeout
```

Generated output:

- `output/shared_peak_identity_evidence_explanation_v2_matrix_rt_drift_closeout/shared_peak_identity_matrix_rt_drift_policy.tsv`
- `output/shared_peak_identity_evidence_explanation_v2_matrix_rt_drift_closeout/shared_peak_identity_machine_evidence_support.tsv`
- `output/shared_peak_identity_evidence_explanation_v2_matrix_rt_drift_closeout/shared_peak_identity_v2_readiness.tsv`

Matrix RT drift policy status counts:

- `rt_close`: `31`
- `inconclusive`: `8`

Inconclusive reasons:

- `no_supportive_matrix_rt_drift_artifact`: `4`
- `rt_delta_missing`: `4`

The run also exposed and fixed an artifact parsing risk: `alignment_cells.tsv`
can contain Excel-safe negative numeric values such as `'-67.8621`. The producer
now accepts those as numeric RT deltas instead of reporting `rt_delta_missing`.

Current RT drift blocker state:

- FAM001227 / NormalBC2312 is no longer a matrix-RT blocker because the generated
  policy reports `rt_close` with `raw_rt_delta_sec=51.2562`, inside the
  preferred RT window.
- FAM001227 / TumorBC2263 remains blocked:
  `raw_rt_delta_sec=67.8621`, `matrix_rt_drift_status=inconclusive`, and no
  owner-edge or RT-normalization artifact exists in current outputs to support
  that drift.

Updated readiness from the closeout run:

- `v2_gate_status`: `exploratory_only`
- `machine_only_labeler_ready`: `FALSE`
- `machine_evidence_basis`: `machine_observed_partial`
- `machine_evidence_supported_rows`: `13`
- `machine_observed_partial_rows`: `8`
- `machine_observed_conflict_rows`: `7`
- `machine_evidence_coverage_fraction`: `0.419355`
- active blockers:
  `formal_pattern_metric`, `dda_opportunity_policy`,
  `shape_metric_not_supportive`, `manual_scope_policy`,
  `sample_level_negative_evidence`, `matrix_rt_drift_policy`

This is still a precondition checkpoint, not V2 product promotion. The sidecars
provide machine-readable hooks for the evidence that manual EIC review was using
visually, but broader validation is still needed before product labels can rely
on them.

## d3-N6-medA 85RAW Drift Probe

The d3-N6-medA validation used existing current 85RAW artifacts only. It did not
rerun RAW extraction and did not use the 8RAW subset as drift support because the
8RAW sample selection is method-smoke oriented and injection order is not a
linear representative series.

Inputs and outputs:

- targeted workbook:
  `output/validation_harness/targeted_ms2_trace_selection_fix_85raw/tissue_85raw_local_minimum/xic_results_process_w4.xlsx`
- sample metadata:
  external local `SampleInfo.xlsx` injection-order workbook (not committed)
- alignment:
  `output/tiered_backfill_candidate_gate_85raw_current`
- targeted benchmark:
  `output/d3_n6_meda_85raw_current_targeted_benchmark/targeted_istd_benchmark_summary.tsv`
- injection-local RT normalization:
  `output/d3_n6_meda_85raw_current_rt_normalization/rt_normalization_leave_one_anchor_out.tsv`
- d3-only shared-identity probe:
  `output/d3_n6_meda_85raw_current_rt_normalization/shared_peak_identity_d3_probe/`
- injection-order phase summaries:
  `output/d3_n6_meda_85raw_current_rt_normalization/d3_n6_meda_rt_by_injection_order.tsv`
  and
  `output/d3_n6_meda_85raw_current_rt_normalization/d3_n6_meda_injection_phase_summary.tsv`

Current 85RAW target match:

- `d3-N6-medA` selected feature: `FAM002625`
- primary match count: `1`
- targeted positives: `85 / 85`
- current alignment cells: `85 / 85` present (`39 detected`, `46 rescued`)
- strict benchmark status remains `FAIL` only for `AREA_MISMATCH`; this is not a
  target-level absence or RT identity failure.

Injection-local evidence:

- target-level sample RT p95 abs delta: `0.1242 min`
- leave-one-anchor-out status for d3-N6-medA: `PASS`
- leave-one-anchor-out p95 abs error: `0.0589932 min`
- leave-one-anchor-out evaluated count: `85`

The diagnostic interpretation matches the manual observation: early injections
elute earlier, the middle of the run is closer to the stable region, and late
injections are later but locally coherent.

| Phase | Injection order | n | RT min | RT median | RT max | RT IQR |
|---|---:|---:|---:|---:|---:|---:|
| early | 1-31 | 29 | 24.1827 | 24.6903 | 25.9377 | 0.6349 |
| mid | 32-61 | 30 | 25.3385 | 25.7567 | 26.1067 | 0.35235 |
| late | 62-91 | 26 | 26.0617 | 26.2013 | 26.3365 | 0.113075 |
| overall | 1-91 | 85 | 24.1827 | 25.7525 | 26.3365 | 1.1149 |

Policy probe rows:

- `Breast_Cancer_Tissue_pooled_QC1`: raw RT delta `82.6536 sec`,
  drift-corrected proxy `7.452 sec`, `drift_supported`.
- `TumorBC2264_DNA`: raw RT delta `81.4939 sec`, drift-corrected proxy
  `7.452 sec`, `drift_supported`.
- `TumorBC2263_DNA`: raw RT delta `77.452 sec`, drift-corrected proxy
  `7.452 sec`, `drift_supported`.
- `NormalBC2312_DNA`: raw RT delta `40.3064 sec`, already `rt_close`.
- `BenignfatBC1151_DNA`: raw RT delta `43.3859 sec`, already `rt_close`.

Result: this closes the design gap for known severe, locally coherent
injection-order drift when 85RAW-style coverage and target-level ISTD local trend
evidence are available. It does not justify globally relaxing RT windows, and it
does not promote V2 product labels by itself because shape and MS1/MS2 pattern
evidence still need broader validation.

## MS1 Pattern Coherence Closeout Run

The MS1 pattern closeout adds a diagnostic-only producer:

- `--generate-ms1-pattern-coherence-evidence` writes
  `shared_peak_identity_ms1_pattern_coherence_evidence.tsv`.
- The producer uses existing `alignment_cells.tsv` apex, integration boundary,
  family-reference width stability, local co-eluting cell count, and optional
  matrix RT drift policy evidence.
- It does not read RAW and does not compute real trace-shape correlation. The
  `shape_correlation_score` field is intentionally empty for generated rows.
- Boundary-only disagreement and unmodeled RT shifts are `inconclusive`, not
  negative identity evidence. This avoids turning a coarse artifact mismatch
  into a false `pattern_metric_not_supportive` blocker.

Shared V2 closeout command:

```powershell
python -m tools.diagnostics.shared_peak_identity_explanation `
  --manual-oracle-tsv docs\superpowers\fixtures\shared_peak_identity_manual_oracle_v1.tsv `
  --alignment-review-tsv output\tiered_backfill_candidate_gate_8raw_current\alignment_review.tsv `
  --alignment-cells-tsv output\tiered_backfill_candidate_gate_8raw_current\alignment_cells.tsv `
  --candidate-gate-tsv output\tier2_v0_1_coherence_8raw_current_gate\alignment_production_candidate_gate.tsv `
  --enable-blast-radius `
  --blast-radius-8raw-run output\tiered_backfill_candidate_gate_8raw_current `
  --blast-radius-85raw-run output\tiered_backfill_candidate_gate_85raw_current `
  --optional-blast-radius-artifact candidate_gate_8raw=output\tiered_backfill_candidate_gate_8raw_current\alignment_production_candidate_gate.tsv `
  --optional-blast-radius-artifact candidate_gate_85raw=output\tiered_backfill_candidate_gate_85raw_current\alignment_production_candidate_gate.tsv `
  --enable-shadow-label-alignment `
  --cwt-shape-evidence-tsv output\tier2_v0_1_coherence_8raw_current\alignment_tier2_cwt_manual_agreement_probe_relaxed.tsv `
  --tier2-trace-evidence-tsv output\tier2_v0_1_coherence_8raw_current\alignment_tier2_trace_evidence.tsv `
  --candidate-ms2-pattern-evidence-tsv output\shared_peak_identity_evidence_explanation_v2\shared_peak_identity_candidate_ms2_pattern_evidence.tsv `
  --generate-ms1-pattern-coherence-evidence `
  --generate-matrix-rt-drift-policy `
  --output-dir output\shared_peak_identity_evidence_explanation_v2_ms1_pattern_closeout
```

Shared V2 readiness after MS1 pattern producer:

- `v2_gate_status`: `exploratory_only`
- `machine_only_labeler_ready`: `FALSE`
- `machine_evidence_supported_rows`: `16`
- `machine_observed_partial_rows`: `5`
- `machine_observed_conflict_rows`: `7`
- `machine_evidence_coverage_fraction`: `0.516129`
- active blockers:
  `formal_pattern_metric`, `dda_opportunity_policy`,
  `shape_metric_not_supportive`, `manual_scope_policy`,
  `sample_level_negative_evidence`, `matrix_rt_drift_policy`

Interpretation:

- MS1 boundary-constellation evidence improves machine-observed support, but it
  cannot close rows where the current machine cell is absent or where RT drift is
  still unmodeled.
- The remaining `formal_pattern_metric` rows are not a wiring bug; they are
  evidence-limited rows that need either RAW trace-level MS1 shape/pattern
  evidence, candidate-aligned MS2 pattern evidence, or a stronger matrix drift
  policy.

d3-N6-medA MS1 pattern probe command:

```powershell
python -m tools.diagnostics.shared_peak_identity_explanation `
  --manual-oracle-tsv output\d3_n6_meda_85raw_current_rt_normalization\d3_n6_meda_manual_oracle.tsv `
  --alignment-review-tsv output\tiered_backfill_candidate_gate_85raw_current\alignment_review.tsv `
  --alignment-cells-tsv output\tiered_backfill_candidate_gate_85raw_current\alignment_cells.tsv `
  --enable-shadow-label-alignment `
  --generate-ms1-pattern-coherence-evidence `
  --generate-matrix-rt-drift-policy `
  --matrix-rt-drift-policy-targeted-istd-summary-tsv output\d3_n6_meda_85raw_current_targeted_benchmark\targeted_istd_benchmark_summary.tsv `
  --matrix-rt-drift-policy-rt-normalization-leave-one-out-tsv output\d3_n6_meda_85raw_current_rt_normalization\rt_normalization_leave_one_anchor_out.tsv `
  --output-dir output\d3_n6_meda_85raw_current_rt_normalization\shared_peak_identity_d3_probe_ms1_pattern
```

d3-specific result:

- All five reviewed d3 rows now have machine-observed MS1 pattern basis through
  `sample_boundary_constellation`.
- `formal_pattern_metric` is closed for the d3 probe.
- The d3 probe remains `exploratory_only` because `formal_shape_metric` is still
  missing. This is expected: the generated MS1 pattern sidecar does not claim raw
  trace-shape correlation.

## Verification

```powershell
python -m pytest tests\test_shared_peak_identity_ms1_pattern_coherence.py tests\test_shared_peak_identity_matrix_rt_drift_policy.py tests\test_shared_peak_identity_shadow_labels.py tests\test_shared_peak_identity_cli.py -q
# 48 passed

python -m pytest tests -q -k shared_peak_identity
# 104 passed, 2607 deselected

uv --cache-dir .uv-cache run ruff check tools\diagnostics\shared_peak_identity_explanation.py xic_extractor\alignment\shared_peak_identity_explanation tests\test_shared_peak_identity_ms1_pattern_coherence.py tests\test_shared_peak_identity_matrix_rt_drift_policy.py tests\test_shared_peak_identity_shadow_labels.py tests\test_shared_peak_identity_cli.py
# All checks passed

uv --cache-dir .uv-cache run mypy xic_extractor\alignment\shared_peak_identity_explanation tools\diagnostics\shared_peak_identity_explanation.py
# Success: no issues found in 14 source files

git diff --check
# exit 0; CRLF warnings only

python -m pytest tests\test_shared_peak_identity_matrix_rt_drift_policy.py tests\test_shared_peak_identity_cli.py -q
# 25 passed

python -m pytest tests -q -k shared_peak_identity
# 96 passed, 2607 deselected

uv --cache-dir .uv-cache run ruff check tools\diagnostics\shared_peak_identity_explanation.py xic_extractor\alignment\shared_peak_identity_explanation tests\test_shared_peak_identity_matrix_rt_drift_policy.py tests\test_shared_peak_identity_cli.py
# All checks passed

uv --cache-dir .uv-cache run mypy xic_extractor\alignment\shared_peak_identity_explanation tools\diagnostics\shared_peak_identity_explanation.py
# Success: no issues found in 13 source files

python -m tools.diagnostics.shared_peak_identity_explanation --manual-oracle-tsv output\d3_n6_meda_85raw_current_rt_normalization\d3_n6_meda_manual_oracle.tsv --alignment-review-tsv output\tiered_backfill_candidate_gate_85raw_current\alignment_review.tsv --alignment-cells-tsv output\tiered_backfill_candidate_gate_85raw_current\alignment_cells.tsv --candidate-gate-tsv output\tiered_backfill_candidate_gate_85raw_current\alignment_production_candidate_gate.tsv --enable-shadow-label-alignment --matrix-rt-drift-policy-targeted-istd-summary-tsv output\d3_n6_meda_85raw_current_targeted_benchmark\targeted_istd_benchmark_summary.tsv --matrix-rt-drift-policy-rt-normalization-leave-one-out-tsv output\d3_n6_meda_85raw_current_rt_normalization\rt_normalization_leave_one_anchor_out.tsv --output-dir output\d3_n6_meda_85raw_current_rt_normalization\shared_peak_identity_d3_probe
# exit 0

python -m pytest tests\test_shared_peak_identity_matrix_rt_drift_policy.py tests\test_shared_peak_identity_shadow_labels.py tests\test_shared_peak_identity_cli.py -q
# 36 passed

python -m pytest tests -q -k shared_peak_identity
# 92 passed, 2607 deselected

uv --cache-dir .uv-cache run ruff check tools\diagnostics\shared_peak_identity_explanation.py xic_extractor\alignment\shared_peak_identity_explanation tests\test_shared_peak_identity_matrix_rt_drift_policy.py tests\test_shared_peak_identity_shadow_labels.py tests\test_shared_peak_identity_cli.py
# All checks passed

uv --cache-dir .uv-cache run mypy xic_extractor\alignment\shared_peak_identity_explanation tools\diagnostics\shared_peak_identity_explanation.py
# Success: no issues found in 13 source files

git diff --check
# exit 0; CRLF warnings only

python -m pytest tests\test_shared_peak_identity_shadow_labels.py tests\test_shared_peak_identity_cli.py tests\test_shared_peak_identity_schema.py -q
# 33 passed

python -m pytest tests -q -k shared_peak_identity
# 81 passed, 2607 deselected

uv --cache-dir .uv-cache run ruff check tools\diagnostics\shared_peak_identity_explanation.py xic_extractor\alignment\shared_peak_identity_explanation tests\test_shared_peak_identity_shadow_labels.py tests\test_shared_peak_identity_cli.py tests\test_shared_peak_identity_schema.py
# All checks passed

uv --cache-dir .uv-cache run mypy xic_extractor\alignment\shared_peak_identity_explanation tools\diagnostics\shared_peak_identity_explanation.py
# Success: no issues found in 12 source files

python -m pytest tests\test_shared_peak_identity_shadow_labels.py tests\test_shared_peak_identity_candidate_ms2_pattern.py tests\test_shared_peak_identity_cli.py -q
# 28 passed

python -m pytest tests -q -k shared_peak_identity
# 77 passed, 2607 deselected

uv --cache-dir .uv-cache run ruff check xic_extractor\alignment\shared_peak_identity_explanation tools\diagnostics\shared_peak_identity_explanation.py tests\test_shared_peak_identity_schema.py tests\test_shared_peak_identity_shadow_labels.py tests\test_shared_peak_identity_candidate_ms2_pattern.py tests\test_shared_peak_identity_cli.py
# All checks passed

uv --cache-dir .uv-cache run mypy xic_extractor\alignment\shared_peak_identity_explanation tools\diagnostics\shared_peak_identity_explanation.py
# Success: no issues found in 12 source files

git diff --check
# exit 0; CRLF warnings only
```

## Non-Delta Evidence Chain Closeout Contract

The latest goal explicitly excludes the future `delta_mass_family_model` PR and
keeps FAM001227/FAM001239-style related-family evidence as context-only.

All other V2 evidence-chain threads now have an explicit diagnostic contract:

- QC-nearby MS1 reference is a machine-observed pattern input through
  `--qc-ms1-pattern-reference-evidence-tsv`.
- RAW-backed MS1 overlays can close `formal_shape_metric` only when both trace
  shape and peak-quality vector provenance are present; low shape correlation
  with low selected-cell height dominance remains inconclusive rather than
  negative identity evidence.
- ISTD / matrix RT drift policy can carry d3-N6-medA injection-order and phase
  summary provenance, but the anchor-local trend route stays coverage-gated for
  85RAW-like evidence instead of 8RAW method-smoke subsets.
- Missing expected NL/MS2 is not a hard negative. A DDA missing-NL case can be
  marked `dda_missing_nl_policy_status=not_dispositive` only when MS1 identity
  evidence is supportive, MS1 intensity is at least `2.5e4`, boundary-aligned
  RAW MS2 trigger count is at least `3`, and the MS2 trace-strength proxy is
  `moderate` or `strong`.
- Sample-level negative evidence is no longer a single opaque blocker. The
  optional `--sample-negative-evidence-tsv` sidecar can close
  `sample_level_negative_evidence` only when it provides a machine-observed
  `negative_evidence_class` in:
  `no_candidate_ms1_evidence`, `pattern_mismatch`, `rt_not_explained`, or
  `local_peak_not_decisive`. The narrower `negative_evidence_detail` carries
  review/debug reasons such as `ugly_shape`, `bad_boundary`,
  `multi_peak_interference`, or `qc_reference_conflict`.

This keeps V2 in `diagnostic_only` mode while making the remaining non-delta
evidence obligations auditable by machine-readable fields instead of broad
human-only notes.

Trial output:

- `output/shared_peak_identity_evidence_explanation_v2_non_delta_closeout/shared_peak_identity_machine_evidence_support.tsv`
- `output/shared_peak_identity_evidence_explanation_v2_non_delta_closeout/shared_peak_identity_v2_readiness.tsv`

The no-RAW rerun remains `exploratory_only` with
`machine_evidence_basis=machine_observed_partial`. This is expected because no
sample-negative sidecar has yet supplied machine-observed classes for the three
scope-derived FAM001227 fail rows, and the current candidate-MS2 artifacts do
not satisfy the conservative DDA non-dispositive policy for all
low-opportunity pass rows.

## Evidence-Chain Contract Checkpoint

The next V2 checkpoint has now moved the DeepResearch conclusion from planning
into a diagnostic-only implementation contract: `formal_shape_metric` is no
longer allowed to mean only "overlay shape correlation exists." For MS1 overlay
evidence to count as the richer V2 formal shape chain, the row must now carry:

- `trace_constellation` MS1 pattern evidence;
- `shape_metric_source=family_ms1_overlay_raw_trace`;
- `family_ms1_overlay_trace_data_json`;
- a non-empty `shape_correlation_score`;
- `peak_quality_vector_basis=family_ms1_overlay_raw_trace_vector`; and
- `peak_quality_vector_status` of `supportive` or `partial_support`.

The generated MS1 pattern sidecar can now add optional `peak_quality_*` fields
from the existing overlay `rt` / `intensity` arrays: trace point count, boundary
point count, S/N proxy, FWHM, sharpness, zigzag/noise, tailing, boundary margin,
feature count, status, basis, and reason. Older overlay JSON remains readable,
but it stays below the V2 formal-shape chain because it lacks the raw trace
vector.

Current verdict remains `diagnostic_only` / `exploratory_only`. This checkpoint
strengthens the evidence chain for shape and selected-cell quality, but it does
not close V2 product-label readiness. Remaining blockers are still MS2/DDA
opportunity policy, stratified oracle/generalization, and calibration of how
`supportive` vs `partial_support` vector states should influence future labels.

Verification:

```powershell
python -m pytest tests\test_shared_peak_identity_ms1_pattern_coherence.py tests\test_shared_peak_identity_shadow_labels.py tests\test_shared_peak_identity_cli.py -q
# 48 passed

python -m pytest tests -q -k shared_peak_identity
# 114 passed, 2607 deselected

$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\alignment\shared_peak_identity_explanation\ms1_pattern_coherence.py xic_extractor\alignment\shared_peak_identity_explanation\ms1_peak_quality_vector.py xic_extractor\alignment\shared_peak_identity_explanation\machine_evidence_support.py tests\test_shared_peak_identity_ms1_pattern_coherence.py tests\test_shared_peak_identity_shadow_labels.py tests\test_shared_peak_identity_cli.py
# All checks passed

$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
# Success: no issues found in 255 source files
```

## Literature Guard

Future metric changes must cite primary literature or official method
documentation. The current support sidecar uses ref ids for:

- SciPy `find_peaks_cwt` / `find_peaks` / `peak_widths` official docs: CWT and
  peak properties are 1-D peak detection / shape evidence, not chemical identity
  evidence.
- LC-MS peak shape / EIC quality: Tautenhahn 2008 centWave, Zhang 2014 EIC
  quality, Kumler 2023 peak-quality metrics.
- MS2 / neutral-loss pattern: product-ion / neutral-loss annotation evidence,
  Watrous 2012 GNPS molecular networking, Huber 2021 Spec2Vec, Biesinger 2022
  modified-cosine / neutral-loss comparison.
- DDA opportunity: Koelmel 2017 iterative exclusion and 2017 target-directed
  DDA coverage work.
- RT drift / orthogonal evidence: Prince 2006 OBI-Warp and Sumner 2007 MSI
  chemical-analysis reporting standards.

## Candidate-MS2 Targeted Threshold Correction

The V2 candidate-MS2 producer now preserves the existing targeted neutral-loss
threshold contract instead of inventing a stricter V2-only rule:

- `best_ppm <= nl_ppm_warn` maps to `candidate_ms2_pattern_status=supportive`.
- `nl_ppm_warn < best_ppm <= nl_ppm_max` maps to
  `candidate_ms2_pattern_status=partial_support`.
- `best_ppm > nl_ppm_max` can support `conflict` for the MS2/NL sidecar.

For the current targeted DNA evidence chain this means `nl_ppm_warn=20` and
`nl_ppm_max=50`. A neutral-loss observation in the warning band is useful MS2
evidence with reduced confidence; it must not be reported as missing evidence or
chemical absence. RAW boundary fallback follows the same mapping: `OK` remains
`supportive`, `WARN` is `partial_support`, and only decisive non-matching
boundary-aligned precursor MS2 evidence becomes `conflict`.

The manual FAM000144 TumorBC2312 review also surfaced an RT-drift support
pattern that is not yet a product rule: choose the QC sample nearest to, or near,
the sample in injection order and compare whether the local MS1 peak
constellation around the candidate RT is similar. This should become a
diagnostic-only injection-local QC reference surface in the next RT-drift/MS1
pattern checkpoint, with explicit QC sample and injection-order provenance.

## Interpretation

This closes the RAW-backed candidate-MS2 pattern checkpoint, still as a
diagnostic artifact rather than a product gate. The important change is that the
machine evidence chain now reproduces the key human distinction inside
FAM000144: NormalBC2312 has boundary-aligned NL/product support, while the
extra TumorBC2312 rescue has boundary-aligned precursor MS2 with a decisive
non-matching base peak.

The remaining blockers have shifted. The dominant semantic gaps are now DDA
opportunity policy, CWT/shape calibration conflicts on several manual-pass rows,
manual scope-derived negative evidence, and matrix RT-drift policy. Pinning old
85RAW artifacts would improve freshness accounting, but it still would not make
the labeler autonomous until those evidence rules are resolved.

## Overlay Shape + ISTD Trend Provenance Checkpoint

Gate: `diagnostic_only`.

This checkpoint wires existing RAW-backed `family_ms1_overlay_plot` metrics into
the generated MS1 pattern sidecar and carries ISTD RT trend provenance through
the generated matrix RT drift policy sidecar. It does not change selected peaks,
backfill behavior, `alignment_matrix.tsv`, workbooks, or production labels.

Implementation surfaces:

- `shared_peak_identity_ms1_pattern_coherence_evidence.tsv` can now include
  `shape_correlation_score`, `shape_metric_source`,
  `family_ms1_overlay_verdict`, local-window metrics, selected-cell / local-max
  intensity metrics, and the overlay JSON path when
  `--ms1-pattern-coherence-overlay-trace-data-json` is supplied together with
  `--generate-ms1-pattern-coherence-evidence`.
- `shared_peak_identity_matrix_rt_drift_policy.tsv` can now include
  `drift_reference_artifacts`, `istd_trend_sample_count`,
  `istd_trend_injection_order_span`, and `istd_phase_summary` when the producer
  receives paired targeted-ISTD / leave-one-anchor-out evidence plus ISTD
  injection-order and phase-summary TSVs.

RAW-backed d3-N6-medA probe:

```powershell
python -m scripts.agent_sandbox_doctor --command ".venv\Scripts\python.exe -m tools.diagnostics.family_ms1_overlay_plot --alignment-cells output\tiered_backfill_candidate_gate_85raw_current\alignment_cells.tsv --family-id FAM002625 --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R --dll-dir C:\Xcalibur\system\programs --mz 269.145 --rt-min 24.0 --rt-max 26.6 --ppm 10 --output-dir output\shared_peak_identity_manual_followup\family_ms1_overlay_d3_n6_meda_wide --output-prefix fam002625_d3_n6_meda_overlay_wide"
# Sandbox doctor status: ok

.venv\Scripts\python.exe -m tools.diagnostics.family_ms1_overlay_plot --alignment-cells output\tiered_backfill_candidate_gate_85raw_current\alignment_cells.tsv --family-id FAM002625 --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R --dll-dir C:\Xcalibur\system\programs --mz 269.145 --rt-min 24.0 --rt-max 26.6 --ppm 10 --output-dir output\shared_peak_identity_manual_followup\family_ms1_overlay_d3_n6_meda_wide --output-prefix fam002625_d3_n6_meda_overlay_wide
# exit 0
# Family MS1 verdict: ms1_shape_supports_family_backfill
```

Generated overlay artifacts:

- `output\shared_peak_identity_manual_followup\family_ms1_overlay_d3_n6_meda_wide\fam002625_d3_n6_meda_overlay_wide_trace_data.json`
- `output\shared_peak_identity_manual_followup\family_ms1_overlay_d3_n6_meda_wide\fam002625_d3_n6_meda_overlay_wide_trace_summary.tsv`
- `output\shared_peak_identity_manual_followup\family_ms1_overlay_d3_n6_meda_wide\fam002625_d3_n6_meda_overlay_wide.png`
- `output\shared_peak_identity_manual_followup\family_ms1_overlay_d3_n6_meda_wide\fam002625_d3_n6_meda_overlay_wide.pdf`

V2 sidecar probe:

```powershell
python -m tools.diagnostics.shared_peak_identity_explanation --manual-oracle-tsv output\d3_n6_meda_85raw_current_rt_normalization\d3_n6_meda_manual_oracle.tsv --alignment-review-tsv output\tiered_backfill_candidate_gate_85raw_current\alignment_review.tsv --alignment-cells-tsv output\tiered_backfill_candidate_gate_85raw_current\alignment_cells.tsv --candidate-gate-tsv output\tiered_backfill_candidate_gate_85raw_current\alignment_production_candidate_gate.tsv --output-dir output\shared_peak_identity_overlay_rt_trend_v2_probe_wide --enable-shadow-label-alignment --generate-ms1-pattern-coherence-evidence --ms1-pattern-coherence-overlay-trace-data-json output\shared_peak_identity_manual_followup\family_ms1_overlay_d3_n6_meda_wide\fam002625_d3_n6_meda_overlay_wide_trace_data.json --matrix-rt-drift-policy-targeted-istd-summary-tsv output\d3_n6_meda_85raw_current_targeted_benchmark\targeted_istd_benchmark_summary.tsv --matrix-rt-drift-policy-rt-normalization-leave-one-out-tsv output\d3_n6_meda_85raw_current_rt_normalization\rt_normalization_leave_one_anchor_out.tsv --matrix-rt-drift-policy-istd-rt-trend-tsv output\d3_n6_meda_85raw_current_rt_normalization\d3_n6_meda_rt_by_injection_order.tsv --matrix-rt-drift-policy-istd-phase-summary-tsv output\d3_n6_meda_85raw_current_rt_normalization\d3_n6_meda_injection_phase_summary.tsv
# exit 0
```

Generated V2 artifacts:

- `output\shared_peak_identity_overlay_rt_trend_v2_probe_wide\shared_peak_identity_ms1_pattern_coherence_evidence.tsv`
- `output\shared_peak_identity_overlay_rt_trend_v2_probe_wide\shared_peak_identity_matrix_rt_drift_policy.tsv`
- `output\shared_peak_identity_overlay_rt_trend_v2_probe_wide\shared_peak_identity_machine_evidence_support.tsv`
- `output\shared_peak_identity_overlay_rt_trend_v2_probe_wide\shared_peak_identity_v2_readiness.tsv`

Observed result:

- `formal_shape_metric` is no longer empty for the d3 probe rows; every row has
  a machine-observed RAW-backed shape basis.
- `BenignfatBC1151_DNA`, `Breast_Cancer_Tissue_pooled_QC1`, and
  `TumorBC2263_DNA` are machine-observed sufficient under the current sidecar
  rules.
- `NormalBC2312_DNA` and `TumorBC2264_DNA` are now machine-observed partial,
  not conflicts. Their overlay rows have `local_window_to_global_max_ratio=1`,
  so the expected local peak is present. They also have lower selected-cell to
  local-window height ratios (`NormalBC2312_DNA`: `0.308020`;
  `TumorBC2264_DNA`: `0.564048`) than the three sufficient rows, which are near
  `1.0`. The low `shape_correlation_score` is therefore treated as an apex /
  selected-cell-height reliability limitation
  (`shape_metric_inconclusive_apex_or_height`) rather than as negative identity
  evidence.
- Matrix RT drift rows for early-drift samples now cite the targeted ISTD
  summary, leave-one-anchor-out TSV, `d3_n6_meda_rt_by_injection_order.tsv`,
  and `d3_n6_meda_injection_phase_summary.tsv`; the phase summary carries
  early/mid/late/overall medians and IQRs.

Current V2 readiness remains `exploratory_only` / `diagnostic_only`.
The d3-specific probe has `machine_observed_sufficient=3`,
`machine_observed_partial=2`, and `machine_observed_conflict=0`. The active
blockers are `shape_metric_inconclusive_apex_or_height` and
`pattern_metric_inconclusive_apex_or_height`, not missing formal shape evidence
or shape/pattern-not-supportive conflicts.

## Wrong-Peak And DDA Gate Closeout

Gate: `diagnostic_only`.

This closeout uses the 85RAW mapped representative sidecar under
`output\shared_peak_identity_v2_85raw_risk_closeout\shared_peak_identity_explanation_85raw_mapped_wrong_peak_dda\`.
The generated artifacts remain ignored validation output; this note captures the
tracked contract conclusion.

Two manual-review rules are now represented by the sidecar decision layer:

1. A selected peak may have normal local shape but still be the wrong identity
   peak if it loses to a family-consensus competing peak.
2. Missing sample-level NL/PI can only be treated as DDA stochasticity when the
   family has at least one required NL/PI observation from candidate MS2
   evidence or existing alignment family context.

FAM011810 / TumorBC2263 is the representative wrong-peak case. The selected
cell remains at RT `6.55874` min, but the family members and competing later
peak support the later RT region. The sidecar now emits:

- `ms1_pattern_status=conflict`
- `reason=family_ms1_overlay_competing_peak_matches_family_consensus`
- `shape_correlation_score=0.904053`
- `peak_quality_vector_status=supportive`
- `evidence_support_status=machine_observed_sufficient`

Interpretation: this is not a "bad shape" fail. It is an identity-pattern fail:
the selected 6-min peak is shape-normal but family-inconsistent.

The DDA missing-NL/PI gate now has explicit states:

- sample-level tag observed:
  `dda_missing_nl_policy_status=sample_required_tag_observed`
- sample tag missing but family-level required tag exists and local opportunity
  evidence is adequate:
  `dda_missing_nl_policy_status=not_dispositive`
- no family-level required tag in candidate MS2 or alignment context:
  `missing_machine_evidence=family_required_tag_gate` and
  `dda_missing_nl_policy_status=family_required_tag_not_observed`

The last state is a hard stop for DDA-stochastic rescue. It means "do not route
this family into extra MS1/RT evidence to rescue missing NL/PI"; it is not a
request for more sidecar evidence.

The current representative run contains no rows with
`family_required_tag_gate` after accepting existing alignment family context as
valid family-level NL/PI evidence. This avoids falsely blocking rows such as
FAM019990 where the generated RAW candidate row does not observe the tag, but
the alignment context already records family-level NL/PI evidence.

## DeepResearch Absorption

The user-supplied external local markdown
`Feature Recognition_deepresearch_MLDL_chatgpt_deepresearch.md` has been
absorbed as design input for the next Shared Peak Identity V2 evidence-chain
checkpoint. The source file remains uncommitted.

The practical conclusion is not "add deep learning now." The stronger conclusion
is that V2 should keep candidate generation and peak-quality judgment separate:
alignment/rescue/backfill candidates keep recall high, while a diagnostic
peak-quality evidence vector improves precision and explains manual-vs-machine
differences.

This changes the next checkpoint in three ways:

- `formal_shape_metric` should expand from "RAW-backed correlation exists" into a
  machine-readable MS1 peak-quality vector. The first vector should be
  interpretable: local S/N or noise, FWHM/scan-count width, prominence or
  sharpness, bell-shape similarity, local zigzag/noise, tailing/asymmetry when
  available, boundary/margin context, and selected-cell height dominance such as
  `cell_to_local_window_max_ratio`.
- RAW-backed `family_ms1_overlay_*` traces should remain the provenance source.
  A NeatMS-like fixed-length trace plus boundary mask is useful as a diagnostic
  artifact shape, but it does not imply CNN training or product inference.
- Before any classifier-like V2 labeler, build a small stratified oracle by
  intensity, RT drift phase, matrix/sample type, boundary quality, MS2/DDA
  opportunity, and failure mode. `human_unjudgeable` and borderline rows remain
  explicit labels, not forced binary truth.

This reinforces the current verdict: PR #76 makes the missing formal shape basis
observable for d3-style probes, but it does not make V2 product labels ready.
The remaining evidence gaps are now sharper: richer MS1 peak-quality features,
MS2/DDA opportunity policy, and generalization evidence over a stratified oracle.

Verification:

```powershell
python -m pytest tests\test_shared_peak_identity_ms1_pattern_coherence.py tests\test_shared_peak_identity_matrix_rt_drift_policy.py tests\test_shared_peak_identity_shadow_labels.py tests\test_shared_peak_identity_cli.py -q
# 56 passed

python -m pytest tests -q -k shared_peak_identity
# 112 passed, 2607 deselected

$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests tools\diagnostics\shared_peak_identity_explanation.py
# All checks passed

$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
# Success: no issues found in 254 source files

git diff --check
# exit 0; CRLF warnings only
```
