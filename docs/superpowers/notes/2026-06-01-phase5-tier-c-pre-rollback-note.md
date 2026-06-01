# Phase 5 Tier C Pre-Rollback Evidence Note

**Date:** 2026-06-01
**Branch:** `codex/cleanup-retirement-foundation`
**Status:** `diagnostic_only`

## Verdict

Current-code AsLS truth validation has enough Tier C baseline evidence to move
to rollback-column cleanup, but it does not authorize linear-edge deletion yet.
The gate correctly emits `REQUIRES_RETIREMENT_PREREQS` because the rollback
schema prerequisite has not been completed.

This is the expected Phase 5 result. The final
`GO_FOR_LINEAR_EDGE_RETIREMENT` must be re-run after Phase 6 rollback-column
cleanup and Phase 6b prerequisite manifest validation.

## Evidence Run

Command:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python -m tools.diagnostics.asls_truth_validation --tier-a-rows docs\superpowers\fixtures\asls_truth_tier_a_artifacts\baseline_truth_audit_rows.tsv --tier-a-summary docs\superpowers\fixtures\asls_truth_tier_a_artifacts\baseline_truth_audit_summary.tsv --tier-a-json docs\superpowers\fixtures\asls_truth_tier_a_artifacts\baseline_truth_audit.json --tier-a-report docs\superpowers\fixtures\asls_truth_tier_a_artifacts\baseline_truth_audit.md --tier-a-manifest docs\superpowers\fixtures\asls_truth_tier_a_expected_manifest.json --fixture-manifest docs\superpowers\fixtures\asls_truth_validation_fixture_manifest.json --fixture-lock docs\superpowers\fixtures\asls_truth_validation_fixture_lock.json --tier-c-evidence output\asls_tier_c_baseline_gate_smoke\tier_c_evidence.json --decision-target linear-edge-retirement --output-dir output\cleanup_retirement_phase5_tier_c_pre_rollback
```

Expected non-zero diagnostic exit was normalized during execution:
`expected_exit_code=3 REQUIRES_RETIREMENT_PREREQS`.

Artifacts:

- `output/cleanup_retirement_phase5_tier_c_pre_rollback/asls_truth_validation_summary.tsv`
- `output/cleanup_retirement_phase5_tier_c_pre_rollback/asls_truth_validation.md`
- `output/cleanup_retirement_phase5_tier_c_pre_rollback/asls_truth_validation.json`
- copied fixture / Tier A / Tier C evidence sidecars in the same directory

## Summary Fields

| Field | Value |
|---|---|
| `gate_decision` | `REQUIRES_RETIREMENT_PREREQS` |
| `decision_target` | `linear-edge-retirement` |
| `tier_b1_status` | `PASS` |
| `tier_b2_status` | `STRESS_REQUIRES_TIER_C` |
| `tier_c_status` | `PASS` |
| `tier_c_baseline_evidence_status` | `PASS` |
| `tier_c_c1b_relevance_status` | `PASS` |
| `tier_c_stress_axis_gate_status` | `PASS` |
| `blank_safety_status` | `NOT_APPLICABLE_WITH_EXCLUSION` |
| `retirement_prereq_status` | `NOT_PROVIDED` |

## Interpretation

- Tier C comparator is AsLS vs `linear_edge` on the same trace and boundary.
- Ratio metrics remain descriptive; no fixed uplift threshold is used.
- No RAW rerun was performed in this phase. The run reused the existing hashed
  Tier A fixtures and Tier C evidence artifact.
- Phase 6 must remove/deprecate rollback columns and freeze the post-rollback
  audit schema before Phase 6b can attempt the final retirement GO.
