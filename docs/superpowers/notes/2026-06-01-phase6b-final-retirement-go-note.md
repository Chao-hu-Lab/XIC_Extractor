# Phase 6b Final Retirement Gate Note

Status: `GO_FOR_LINEAR_EDGE_RETIREMENT` emitted.

Decision target: `linear-edge-retirement`

Verdict:

- C1a, C5, and rollback-column prerequisites are now represented by a valid
  retirement prerequisite manifest.
- The final AsLS truth-validation gate emits
  `GO_FOR_LINEAR_EDGE_RETIREMENT`.
- This authorizes the next phase to delete maintained `linear_edge` production
  support. It does not itself delete the legacy implementation.

Retirement prerequisite manifest:

- Path: `docs/superpowers/fixtures/asls_truth_retirement_prerequisites.json`
- SHA256:
  `87abec5b13912d86d847759671663a19f72936784d3a22fea0d3837e3bb9b778`

Referenced prerequisite notes:

- C1a: `docs/superpowers/notes/2026-06-01-c1a-baseline-module-consolidation-closeout-note.md`
- C5: `docs/superpowers/notes/2026-06-01-c5-single-integration-entry-closeout-note.md`
- Rollback schema:
  `docs/superpowers/notes/2026-06-01-phase6-rollback-schema-deprecation-note.md`
- Post-rollback schema artifact:
  `docs/superpowers/fixtures/alignment_cell_integration_audit_post_rollback_schema.tsv`

Command:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python -m tools.diagnostics.asls_truth_validation --tier-a-rows docs\superpowers\fixtures\asls_truth_tier_a_artifacts\baseline_truth_audit_rows.tsv --tier-a-summary docs\superpowers\fixtures\asls_truth_tier_a_artifacts\baseline_truth_audit_summary.tsv --tier-a-json docs\superpowers\fixtures\asls_truth_tier_a_artifacts\baseline_truth_audit.json --tier-a-report docs\superpowers\fixtures\asls_truth_tier_a_artifacts\baseline_truth_audit.md --tier-a-manifest docs\superpowers\fixtures\asls_truth_tier_a_expected_manifest.json --fixture-manifest docs\superpowers\fixtures\asls_truth_validation_fixture_manifest.json --fixture-lock docs\superpowers\fixtures\asls_truth_validation_fixture_lock.json --tier-c-evidence output\asls_tier_c_baseline_gate_smoke\tier_c_evidence.json --retirement-prereq-manifest docs\superpowers\fixtures\asls_truth_retirement_prerequisites.json --decision-target linear-edge-retirement --output-dir output\cleanup_retirement_phase6b_final_retirement_go
```

Observed result:

- Exit code: `0`
- Gate decision: `GO_FOR_LINEAR_EDGE_RETIREMENT`
- Retirement prerequisite status: `VALID`
- C1a status: `LANDED_VALIDATED`
- C5 status: `LANDED_VALIDATED`
- Rollback column status: `DEPRECATED_BY_APPROVED_SCHEMA_NOTE`
- Tier C baseline evidence: `PASS`
- Blank safety: `NOT_APPLICABLE_WITH_EXCLUSION`

Primary artifacts:

- `output/cleanup_retirement_phase6b_final_retirement_go/asls_truth_validation_summary.tsv`
- `output/cleanup_retirement_phase6b_final_retirement_go/asls_truth_validation.md`
- `output/cleanup_retirement_phase6b_final_retirement_go/asls_truth_validation.json`
- `output/cleanup_retirement_phase6b_final_retirement_go/asls_truth_validation_retirement_prerequisites.json`

Old public `linear_edge` input behavior for the deletion phase:

- Use rejection, not silent aliasing.
- `baseline_integration_method=linear_edge`,
  `--baseline-integration-method linear_edge`, and
  `BASELINE_INTEGRATION_METHOD=linear_edge` should raise or return an
  actionable error that says `linear_edge` is retired and `asls` is the
  replacement.
- Phase 7 must add tests for this public-input behavior before deleting the
  selector branch and legacy implementation.
