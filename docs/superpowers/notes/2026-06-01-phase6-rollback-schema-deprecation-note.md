# Phase 6 Rollback Schema Deprecation Note

Status: production_candidate schema cleanup.

Decision: deprecate and remove the temporary linear-edge rollback columns from
the accepted `alignment_cell_integration_audit.tsv` schema:

- `area_baseline_corrected_linear_edge`
- `baseline_score_linear_edge`

Rationale:

- Phase 5 ended at `REQUIRES_RETIREMENT_PREREQS`, with Tier C baseline evidence
  passing and rollback schema cleanup still required before final linear-edge
  retirement.
- The rollback columns were temporary promotion support from the AsLS rollout.
  Keeping them in the accepted schema would continue requiring default AsLS
  audit generation to recompute linear-edge rollback values.
- `linear_edge` itself is not deleted in this phase. Legacy comparator
  diagnostics may still read historical rows with these columns, and
  `baseline_integration_method=linear_edge` plus `baseline_audit_method=asls`
  still supports legacy AsLS shadow comparison until the final deletion phase.

Reviewer disposition:

- `implementation-contract-reviewer`: PASS for Phase 6 only.
- `validation-evidence-reviewer` with mode `acceptance`: PASS to proceed to
  rollback schema cleanup; final deletion remains blocked until Phase 6b emits
  `GO_FOR_LINEAR_EDGE_RETIREMENT`.

Post-removal schema snapshot:

- Artifact:
  `docs/superpowers/fixtures/alignment_cell_integration_audit_post_rollback_schema.tsv`
- SHA256:
  `1c0b41a4892205925fdc45fa7103cfe84ad30421c4aa17d39b546d4c025b0618`

Exact header order:

```text
feature_family_id
sample_stem
status
area
apex_rt
peak_start_rt
peak_end_rt
neutral_loss_tag
family_center_mz
family_center_rt
area_baseline_corrected
area_uncertainty
area_uncertainty_formula_version
baseline_residual_mad
area_uncertainty_noise_source
baseline_type
baseline_score
uncertainty_fraction
baseline_fraction
integration_scan_count
```

Diagnostic reader contract:

- `p2_baseline_truth_audit` and `p2_asls_shadow_gate` keep accepting historical
  promoted-AsLS rows that include `area_baseline_corrected_linear_edge`.
- For post-rollback rows with `baseline_type=asls` and no rollback comparator,
  `area_baseline_corrected` is interpreted as AsLS, not as linear-edge.
- `p2_asls_shadow_gate` reports
  `baseline_comparison_columns_unavailable` when a post-rollback schema is used
  for a shadow comparison that still needs paired linear-edge/AsLS columns.
- `area_integration_uncertainty_audit` continues to use the reported baseline
  area when the rollback column is absent.

Phase 6b usage:

- The retirement prerequisite manifest should reference the schema artifact
  above as `post_rollback_audit_schema_artifact`.
- `post_rollback_absent_columns` must include both removed rollback columns.
