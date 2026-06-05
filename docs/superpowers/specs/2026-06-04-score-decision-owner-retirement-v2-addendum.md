# Score Decision Owner Retirement v2 Addendum

**Date:** 2026-06-04
**Branch:** `codex/cleanup-retirement-foundation`
**Status:** implementation addendum
**Readiness label after this slice:** `production_ready`
**Parent design:** [C4 - Peak Scoring Evidence-Decision Design](2026-06-01-c4-peak-scoring-evidence-decision-design.md)

## Verdict

Product candidate decision now belongs to typed candidate evidence facts, not to
legacy weighted score mechanics.

`EvidenceScore`, `raw_score`, `support_labels`, `concern_labels`, `cap_labels`,
`score_breakdown`, and the legacy reason formatter remain public
compatibility/debug projections. They may be rendered into candidate tables,
CSV/XLSX, and score debugging surfaces, but they must not decide selection,
detected/not-counted, result confidence/reason, matrix presence, or summary
counts when typed projection exists.

This slice is `production_ready` for the Score Decision Owner retirement after
canonical 8RAW baseline comparison plus row-level targeted benchmark
adjudication. Legacy score is no longer an active product-decision authority.

This does not make every future matrix/evidence-chain policy production-ready.
New MS2/NL, RT, boundary, or product-presence policy changes still require their
own gate and row-level adjudication.

## Owner Chain

```text
PeakCandidate + ScoringContext
  -> CandidateEvidenceFacts
  -> EvidenceDecisionSemantics
  -> projected confidence/reason
  -> select_candidate_by_evidence / model_select_peak_hypothesis
  -> PeakHypothesisSelectionDecision
  -> ExtractionResult / TargetedProductProjection / public outputs
```

Legacy score projection is attached beside the facts:

```text
EvidenceScore / raw_score / labels / score_breakdown
  -> compatibility/debug output only
```

## Field And Disposition Table

| Typed field family | Source | Legacy equivalent | Selection usage | Projection usage | Tests | Disposition |
|---|---|---|---|---|---|---|
| `TraceEvidenceFacts.local_sn_ratio`, `local_sn_quality`, `baseline_method`, `residual_mad`, `noise_source` | `ScoringContext` local S/N and baseline inputs | local S/N score signals | Candidate ranking uses local S/N quality through decision semantics and quality/conflict ranks. | `ms1_coherent`, trace review/conflict reasons. | `test_candidate_evidence_facts.py`, `test_peak_scoring.py` | active typed facts |
| `TraceEvidenceFacts.symmetry_quality`, `width_quality`, `noise_shape_quality` | symmetry, FWHM, and noise-shape metrics | severity points and concern labels | Shape/noise concerns become trace morphology conflict/review, not raw-score subtraction. | confidence/reason projection via `EvidenceDecisionSemantics`. | `test_peak_scoring.py`, `test_evidence_semantics.py` | active typed facts |
| `TraceEvidenceFacts.scan_count`, `duration_min`, `edge_ratio`, `continuity`, `quality_flags`, `hard_quality_flags` | candidate region metadata and quality flags | quality penalty, ADAP-like labels, trace caps | Soft flags can demote selection quality; hard flags can create hard quality conflict. Legacy-equivalent ADAP flags are suppressed from hard conflicts. | trace morphology review/conflict and hard-quality projection. | `test_peak_scoring.py`, `test_candidate_evidence_selection.py` | active typed facts |
| `ChemicalEvidenceFacts.ms2_present`, `nl_match`, `nl_status`, `acquisition_opportunity` | `ScoringContext` and later `CandidateMS2Evidence` | NL severity, `no_ms2_cap`, `nl_fail_cap` | Strict NL support and missing/NL conflict are typed chemical evidence. MS2 trigger without key NL/product tag is acquisition opportunity, not identity support. | missing-MS2, plausible NL dropout, and candidate-aligned MS2/NL projection. | `test_candidate_evidence_facts.py`, `test_peak_scoring.py`, `test_scoring_context.py` | active typed facts |
| `ChemicalEvidenceFacts.ms2_trace_strength`, `loss_ppm`, `ms2_rt_delta_min`, `trigger_scan_count`, `strict_nl_scan_count`, `alignment_source`, `product_absence_reason` | `ScoringContext` now; `CandidateMS2Evidence` enrichment later | MS2 trace support/concern labels | Used as chemical tiebreak and evidence completeness, not as score points. | debug/detail facts; compact reason projects to decision-level labels. | `test_candidate_evidence_facts.py`, `test_peak_scoring.py` | active typed facts, partial enrichment |
| `RtEvidenceFacts.selected_apex_rt_min`, `rt_min`, `rt_max`, `rt_prior_min`, `rt_prior_sigma_min`, `rt_prior_delta_min`, `window_status` | candidate apex and target/prior RT context | RT prior/window severity and caps | RT distance and typed RT status influence ranking; RT alone is contextual evidence and not absence proof. | `role_aware_rt_support`, `targeted_rt_conflict`, `targeted_rt_review`. | `test_candidate_evidence_facts.py`, `test_peak_scoring.py` | active typed facts |
| `RtEvidenceFacts.paired_istd_anchor_rt_min`, `paired_istd_delta_min`, `paired_istd_status`, `role`, `istd_pair`, `prefer_rt_prior_tiebreak` | target role, paired ISTD context, scoring context | paired ISTD support label | Supports role-aware RT tiebreak; analyte candidates more than 1.0 min from paired ISTD are anchor mismatches and become not-counted when strict NL/product support is absent. | role-aware RT support, paired ISTD support, anchor conflict, paired-RT mismatch not-counted policy. | `test_candidate_evidence_facts.py`, `test_candidate_evidence_selection.py`, `test_peak_selection_decision.py` | active typed facts |
| `BoundaryEvidenceFacts.proposal_sources`, `cwt_same_apex_observed`, `cwt_best_scale`, `cwt_ridge_persistence`, `chrom_peak_segment_present`, `boundary_sources` | candidate proposal/boundary metadata | CWT same-apex label and legacy proposal tokens | Boundary/morphology context is a tiebreak/review input; CWT alone is not standalone identity authority. | CWT/chrom segment context reasons. | `test_candidate_evidence_facts.py`, `test_peak_scoring.py`, `test_evidence_semantics.py` | active typed facts |
| `CandidateEvidenceFacts.abundance`, `area`, `height`, `quality_penalty`, `selection_quality_penalty` | candidate area/height and quality helpers | score tiebreaks and penalty points | Selection key uses abundance guard and typed quality penalty directly. | retained as facts/debug projection. | `test_candidate_evidence_selection.py`, `test_signal_processing_selection.py` | active typed facts |
| `PeakCandidateScore.raw_score`, labels, caps, `score_breakdown` | legacy `EvidenceScore` | weighted score owner | No active selection/model-selection authority when typed facts exist. | Output compatibility/debug only. | `test_score_retirement_legacy_authority.py`, CSV/XLSX/candidate-table tests | `legacy_projection_only` |

## Legacy Authority Audit

| Consumer | Legacy fields observed | Current classification | Guard |
|---|---|---|---|
| `peak_detection.facade` active scoring path | legacy `EvidenceScore` is still computed for output summary | active decision is retired from score; `select_candidate_by_evidence` is used | `test_signal_processing_selection.py`, `test_score_retirement_legacy_authority.py` |
| `peak_detection.candidate_selection.select_candidate_by_evidence` | none in active key | typed product selector | source guard asserts no `raw_score` or label tie-break in selector body |
| `peak_detection.candidate_selection.select_candidate_with_confidence` | `confidence`, `raw_score`, labels | compatibility only | package active code must not import it; `peak_scoring.py` may re-export it |
| `peak_detection.candidate_scoring.score_candidate` | computes `EvidenceScore` | mixed builder: typed projection primary, legacy output preserved | scoring tests assert typed reason/confidence plus legacy labels/caps |
| `peak_detection.hypotheses.EvidenceVector` | keeps legacy score fields | legacy projection plus typed facts/projection | if `evidence_facts` exists, decision semantics and projected values come from facts |
| `peak_detection.selection_decision` | may expose legacy fields as evidence sources | product projection owner | projected confidence/reason wins over stale legacy confidence/reason |
| `peak_detection.model_selection` | legacy fields retained for parity metadata | product ranking no longer uses raw score or label count | model-selection guard mutates raw score/labels adversarially |
| `extraction.result_assembly` | legacy `peak_result.confidence/reason` fallback | product projection primary | typed selection decision overrides stale final confidence/reason |
| `output.detection` | fallback can inspect confidence/NL when projection absent | compatibility fallback only | product callers must use `require_projection=True` or carry `TargetedProductProjection` |
| Candidate table, CSV, CSV-to-XLSX, Excel workbook writers | render confidence, reason, raw score, labels, caps | `legacy_projection_only` | schema/output tests keep columns stable; no feedback into product decisions |
| `peak_scoring.py`, `scoring_reason.py`, `peak_scoring_evidence.py` | public imports, reason formatting, arithmetic | compatibility/debug only | minimal legacy tests retain import/arithmetic/projection behavior |
| diagnostics and shadow reports | may print score/labels | `diagnostic_only` | reports must not recompute product decisions |

## Leak Guards

Required guard classes for this slice:

- Product selector is invariant under adversarial legacy raw score and labels
  when typed facts are unchanged.
- Result assembly uses typed projected confidence/reason when typed facts exist.
- Model selection does not rank by legacy raw score or label count.
- Candidate tables and workbooks may print legacy fields but do not feed those
  fields back into product selection.
- Package active code does not import `select_candidate_with_confidence`; the
  name remains in `peak_scoring.py` for compatibility.

## Expected Diff Record

Any changed selection, presence, confidence, reason, or matrix value must carry a
row-level bundle before it can be promoted beyond `production_candidate`:

| Required item | Meaning |
|---|---|
| stable row id, sample, target | exact row identity |
| legacy candidate id, successor candidate id | selected-candidate diff |
| selected RT, area, boundary | peak/boundary consequence |
| confidence, reason, presence impact | public behavior impact |
| typed facts completeness | whether all trace/chemical/RT/boundary facts were present |
| retired legacy inputs | which raw score/labels/caps were ignored |
| MS2/NL opportunity status | whether missing product/NL was observable |
| RT/ISTD rationale | role-aware RT evidence |
| evidence tier | synthetic, no-RAW, tissue-8raw, targeted benchmark, manual review |
| reviewer verdict | approved, rejected, inconclusive |

MS2/NL-only or RT-only diffs remain `inconclusive` without manual EIC/MS2 or
targeted benchmark support. Do not escalate to 85RAW if tissue-8raw is
inconclusive.

## Validation Contract

Required no-RAW gate:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_evidence_semantics.py tests/test_peak_hypotheses.py tests/test_peak_model_selection.py tests/test_peak_selection_decision.py tests/test_result_assembly.py tests/test_signal_processing_selection.py tests/test_peak_candidate_table.py tests/test_csv_writers.py tests/test_csv_to_excel.py tests/test_excel_pipeline.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```

Production readiness gate:

- Run targeted `tissue-8raw` only after the no-RAW gate passes.
- Treat unadjudicated 8RAW compare diffs as `production_candidate` only.
- Promote this slice to `production_ready` only if every changed row has either
  no selection/presence impact or a row-level targeted benchmark / reliability
  adjudication.
- Do not run 85RAW while 8RAW changed rows remain inconclusive.

## Current Slice Verification

Observed commands on 2026-06-04:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_candidate_evidence_facts.py tests/test_candidate_evidence_selection.py tests/test_score_retirement_legacy_authority.py tests/test_evidence_semantics.py tests/test_peak_hypotheses.py tests/test_peak_model_selection.py tests/test_peak_selection_decision.py tests/test_result_assembly.py tests/test_signal_processing_selection.py tests/test_peak_candidate_table.py tests/test_csv_writers.py tests/test_csv_to_excel.py tests/test_excel_pipeline.py
# 164 passed

$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_peak_scoring.py tests/test_scoring_context.py::test_strict_nl_candidate_beats_candidate_with_trigger_but_failed_nl
# 40 passed

$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_peak_scoring_evidence.py tests/test_peak_scoring_selection.py tests/test_peak_candidate_score_calibration_report.py
# 33 passed

$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_peak_detection_module_boundaries.py
# 9 passed

$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests
# All checks passed

$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
# Success: no issues found in 291 source files

.venv\Scripts\python.exe scripts\validation_harness.py --suite tissue-8raw --run-id score_decision_owner_v2_20260604 --output-root output\validation_harness
# tissue-8raw: passed, compare=not_requested
```

8RAW output:

```text
output\validation_harness\score_decision_owner_v2_20260604\tissue_8raw_region_first_safe_merge\xic_results_process_w4.xlsx
```

The first 8RAW run did not compare against an approved baseline and therefore
was only `production_candidate`.

## Production-Ready Follow-Up

Observed follow-up commands on 2026-06-04 used a clean canonical validation
base under `C:\tmp\XIC_score_v2_validation_base_20260604` so ignored local
`config\targets.csv` could not contaminate the comparison.

Baseline and current runs:

```powershell
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe scripts\validation_harness.py --suite tissue-8raw --run-id score_decision_owner_v2_candidate_audit_canonical_20260604 --base-dir C:\tmp\XIC_score_v2_validation_base_20260604 --output-root C:\Users\user\Desktop\XIC_Extractor\output\validation_baselines --setting emit_peak_candidates=true
# tissue-8raw: passed, compare=not_requested

C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe scripts\validation_harness.py --suite tissue-8raw --run-id score_decision_owner_v2_candidate_audit_canonical_20260604 --base-dir C:\tmp\XIC_score_v2_validation_base_20260604 --output-root output\validation_harness --baseline-root output\validation_baselines --setting emit_peak_candidates=true
# tissue-8raw: failed, compare=fail
```

The compare failure is expected because confidence/reason and selected
candidate projection changed from legacy score to typed facts. It is not by
itself a no-go; the changed-row bundle is the authority.

Adjudication artifacts:

```text
output\validation_harness\score_decision_owner_v2_candidate_audit_canonical_20260604\score_decision_owner_v2_changed_row_bundle.tsv
output\validation_harness\score_decision_owner_v2_candidate_audit_canonical_20260604\score_decision_owner_v2_changed_row_summary.tsv
output\validation_harness\score_decision_owner_v2_candidate_audit_canonical_20260604\targeted_reliability_audit\targeted_peak_reliability_rows.tsv
output\validation_harness\score_decision_owner_v2_candidate_audit_canonical_20260604\targeted_nl_dropout_root_cause\targeted_nl_dropout_root_cause_rows.tsv
output\validation_harness\score_decision_owner_v2_candidate_audit_canonical_20260604\score_decision_owner_v2_changed_row_adjudication.tsv
output\validation_harness\score_decision_owner_v2_candidate_audit_canonical_20260604\score_decision_owner_v2_changed_row_adjudication_summary.tsv
```

Adjudication summary:

| Verdict | Count | Production-ready blocker |
|---|---:|---|
| `approved_expected_typed_projection` | 45 | no |
| `approved_targeted_negative_no_matrix_presence` | 6 | no |
| `approved_targeted_benchmark_supported` | 1 | no |
| unresolved / inconclusive | 0 | no |

The seven non-projection rows are explicitly adjudicated:

| Row | Impact | Verdict |
|---|---|---|
| `Breast_Cancer_Tissue_pooled_QC3|d3-N6-medA|ISTD` | selected candidate / boundary changed; counted `TRUE -> TRUE` | `approved_targeted_benchmark_supported` |
| `Breast_Cancer_Tissue_pooled_QC5|8-oxodG|Analyte` | `ambiguous -> not_counted`; counted `FALSE -> FALSE` | `approved_targeted_negative_no_matrix_presence` |
| `Breast_Cancer_Tissue_pooled_QC5|dG-C8-MeIQx|Analyte` | selected candidate changed; counted `FALSE -> FALSE` | `approved_targeted_negative_no_matrix_presence` |
| `NormalBC2263_DNA|dG-C8-MeIQx|Analyte` | selected candidate changed; counted `FALSE -> FALSE` | `approved_targeted_negative_no_matrix_presence` |
| `NormalBC2312_DNA|8-oxodG|Analyte` | selected candidate changed; counted `FALSE -> FALSE` | `approved_targeted_negative_no_matrix_presence` |
| `NormalBC2312_DNA|dG-C8-MeIQx|Analyte` | `ambiguous -> not_counted`; counted `FALSE -> FALSE` | `approved_targeted_negative_no_matrix_presence` |
| `TumorBC2263_DNA|8-oxodG|Analyte` | `ambiguous -> not_counted`; counted `FALSE -> FALSE` | `approved_targeted_negative_no_matrix_presence` |

One public projection leak was fixed during follow-up: long-form public output
confidence now follows product projection for `ambiguous`, `excluded`, and
`not_counted` rows, so candidate-level `HIGH` confidence cannot be displayed
beside product `not_counted`.

Final no-RAW gate:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_candidate_evidence_facts.py tests/test_candidate_evidence_selection.py tests/test_score_retirement_legacy_authority.py tests/test_evidence_semantics.py tests/test_peak_hypotheses.py tests/test_peak_model_selection.py tests/test_peak_selection_decision.py tests/test_result_assembly.py tests/test_signal_processing_selection.py tests/test_peak_candidate_table.py tests/test_csv_writers.py tests/test_csv_to_excel.py tests/test_excel_pipeline.py
# 166 passed

$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests
# All checks passed

$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
# Success: no issues found in 291 source files
```

Final readiness verdict: `production_ready` with the current adjudication
artifacts intact.
