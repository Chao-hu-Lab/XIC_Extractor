# C4 / C6 / Region Foundation Closeout

**Date:** 2026-06-02
**Status:** Complete for end-to-end semantic-convergence foundation
**Behavior label:** no public behavior change

## Verdict

The #4 cleanup thread is complete for the scope that was actually safe to close
in this PR:

- C4 scorer/evidence overlap has one future direction and a tested compatibility
  projection boundary.
- C6 owner-family construction now has a tested successor-constructor path and
  `owner_clustering.py` is classified as a compatibility adapter candidate.
- Region/boundary RB0/RB1 has a shared internal decision projection and focused
  parity tests.

This is not a claim that legacy scorer policy, `OwnerAlignedFeature` delivery,
or region productization are retired. Those are later behavior or adapter
migration slices.

## Structural Evidence

CodeGraph and focused test inspection confirmed the current state:

| Area | Current product owner | Successor / shared contract | Closeout disposition |
|---|---|---|---|
| C4 scoring and selection | `peak_scoring.py::score_candidate(...)` and `select_candidate_with_confidence(...)` | `EvidenceVector`, `CommonEvidence`, and `EvidenceDecisionSemantics` projections | `peak_scoring.py` remains `active_policy`; public score/reason fields are `legacy_compatibility_projection`; successor direction is C4-D selected-hypothesis model selection. |
| C6 owner-family construction | `owner_clustering.cluster_sample_local_owners(...)` public entry point returning `OwnerAlignedFeature` | `cross_sample_peak_groups.construct_cross_sample_peak_group_hypotheses(...)` and `CrossSamplePeakGroupHypothesis` | `owner_clustering.py` is `compatibility_adapter_candidate`; downstream concrete DTO consumers are not yet retired. |
| Region/boundary | resolver path behind `find_peak_and_area(...)`; `region_first_safe_merge` as opt-in safe merge | `RegionSelectionDecision` typed projection | RB0/RB1 complete as groundwork; RB2/RB3/RB4 must decide promote / review-only / externalize / retire for each shadow verdict class. |

## Verification

Focused verification run on 2026-06-02:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_peak_scoring.py tests/test_peak_scoring_selection.py tests/test_peak_scoring_evidence.py tests/test_scoring_context.py tests/test_peak_hypotheses.py tests/test_evidence_semantics.py tests/test_peak_candidate_table.py tests/test_peak_candidate_score_calibration_report.py tests/test_csv_writers.py tests/test_csv_to_excel.py tests/test_excel_pipeline.py tests/test_excel_sheets_contract.py tests/test_signal_processing_selection.py
```

Result: `245 passed, 2 warnings`.

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_alignment_owner_family_successor_contract.py tests/test_alignment_owner_clustering.py tests/test_pre_backfill_consolidation.py tests/test_backfill_scope.py tests/test_alignment_owner_backfill.py tests/test_alignment_owner_matrix.py tests/test_alignment_claim_registry.py tests/test_alignment_primary_consolidation.py tests/test_alignment_matrix_identity.py tests/test_alignment_production_decisions.py tests/test_alignment_tsv_writer.py tests/test_alignment_xlsx_writer.py tests/test_alignment_debug_writer.py tests/test_alignment_output_levels.py tests/test_run_alignment.py tests/test_alignment_pipeline.py tests/test_alignment_pipeline_outputs.py
```

Result: `249 passed`.

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_signal_processing.py tests/test_signal_processing_selection.py tests/test_region_model_selection.py tests/test_region_safe_merge.py tests/test_peak_region_selection_shadow.py tests/test_boundary_hypotheses.py tests/test_boundary_scoring.py tests/test_peak_candidate_boundaries.py tests/test_peak_candidate_table.py tests/test_cwt_proposals.py tests/test_cwt_peak_candidate_audit.py tests/test_config.py tests/test_settings_section.py tests/test_settings_section_advanced.py tests/test_settings_new_fields.py tests/test_gui_main.py tests/test_run_discovery.py tests/test_discovery_pipeline.py tests/test_csv_writers.py tests/test_csv_to_excel.py tests/test_excel_pipeline.py tests/test_excel_sheets_contract.py tests/test_alignment_tsv_writer.py tests/test_alignment_xlsx_writer.py tests/test_alignment_owner_matrix.py tests/test_run_alignment.py tests/test_validation_harness.py
```

Result: `445 passed, 6 warnings`.

The warnings are existing synthetic-peak `PeakPropertyWarning` cases in focused
C4/region fixtures and do not indicate changed production output.

## What Is Complete

- C4-A/B/C are complete as semantic bridge / compatibility projection work.
  Future work must not pretend raw score, confidence cap, or reason text parity
  is the future product oracle.
- C6-A1/A2/A3/B/M are complete as successor-constructor foundation. The
  successor constructs owner groups internally, then adapts back to
  `OwnerAlignedFeature`.
- RB0/RB1 are complete as characterization and internal typed decision
  projection. `region_first_safe_merge` remains active opt-in behavior, not dead
  code and not generalized default authority.

## What Remains Later

- C4-D: move from scorer active policy toward selected-hypothesis model
  selection only after selected candidate, decision class, explanation, and
  public projection parity are proven or a behavior spec approves changes.
- C6-D: migrate owner-backfill, owner-matrix, claim registry, primary
  consolidation, writers, and process payloads to structural successor
  consumers or explicit delivery adapters. This is where stateful
  missing-observation / gap-filling semantics should be designed.
- Region RB2/RB3/RB4: decide whether each shadow verdict class promotes to
  product behavior, stays review-only, is externalized as maintained diagnostic
  output, is retired, or remains inconclusive with one named missing oracle.

## Stop-Line

Do not use this closeout as approval to:

- delete `peak_scoring.py` active policy;
- delete or rename `OwnerAlignedFeature` or public `FAM######` outputs;
- promote CWT, WIS, local minima, RT, shape, or S/N as single-source product
  authority;
- change selected peaks, selected areas, confidence, reason text, workbook
  schemas, TSV schemas, resolver defaults, or matrix values under the label
  cleanup.
