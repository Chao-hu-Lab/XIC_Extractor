# P2c B1/B2 AsLS Truth Validation Closeout

**Date:** 2026-05-27
**Readiness:** `diagnostic_only`
**Verdict:** `GO_FOR_C1B_PLAN_SYNTHETIC_ONLY` for `decision_target=c1b-plan`; `REQUIRES_TIER_C` for `decision_target=linear-edge-retirement`.

## Decision Fields

```json
{
  "c1b_planning_allowed": true,
  "linear_edge_deletion_allowed": false,
  "c5_method_preserving_required": true,
  "cleanup_specs_to_update": [
    "docs/superpowers/specs/2026-05-24-peak-pipeline-cleanup-area-integration-single-entry-spec.md",
    "docs/superpowers/specs/2026-05-24-peak-pipeline-cleanup-linear-edge-retirement-spec.md"
  ]
}
```

## What Changed

- P2c synthetic Tier B is now split into B1 relevance and B2 stress layers.
- `decision_target=c1b-plan` consumes Tier A + B1 only. B2 blank/coelution/low-S/N/clipping stress findings are reported but cannot by themselves produce a C1b `NO_GO_KEEP_LINEAR_EDGE`.
- v1 synthetic fixtures are non-authoritative under the B1/B2 contract and emit `LEGACY_V1_NON_AUTHORITATIVE` / `INCONCLUSIVE_FIXTURE_SCOPE_MISMATCH`.
- B1 hard-blocker logic now follows the v0.3 spec: low median relative error classes do not fail merely because the improvement is under 20%; the 20% improvement / 3% absolute-error rule only applies once median relative error exceeds 10%.
- C1b gate rollup ignores unresolved B2 stress status. B2 inconclusive/stress blockers only affect retirement decisions unless the same evidence is explicitly promoted into B1.

No production extraction, alignment, RT resolver, boundary resolver, or matrix output behavior changed.

## Verification

Focused shard:

```powershell
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest `
  tests\test_asls_truth_validation_models.py `
  tests\test_asls_truth_validation_manifests.py `
  tests\test_asls_truth_validation_synthetic.py `
  tests\test_asls_truth_validation_inputs.py `
  tests\test_asls_truth_validation_analysis.py `
  tests\test_asls_truth_validation_cli.py `
  -q -p no:cacheprovider
```

Result: `128 passed`.

## Smoke Results

### v2 C1b Planning

Command output path:

- `output/phase1_p2c_truth_validation_v2_c1b_smoke/asls_truth_validation_summary.tsv`
- `output/phase1_p2c_truth_validation_v2_c1b_smoke/asls_truth_validation_rows.tsv`
- `output/phase1_p2c_truth_validation_v2_c1b_smoke/asls_truth_validation.json`
- `output/phase1_p2c_truth_validation_v2_c1b_smoke/asls_truth_validation.md`

Result:

- `gate_decision=GO_FOR_C1B_PLAN_SYNTHETIC_ONLY`
- `LASTEXITCODE=3`
- `benchmark_status=PASS`
- `synthetic_decision_status=PASS`
- `tier_b1_status=PASS`
- `tier_b1_accuracy_scope=PLANNING_ONLY_REQUIRES_TIER_C`
- `tier_b2_status=STRESS_REQUIRES_TIER_C`
- `tier_b1_hard_blocker_count=0`
- `tier_b2_stress_blocker_count=1`
- `coverage_status=PASS`

Interpretation: B1 supports writing the C1b plan. This is not retirement authority.

### v2 Linear-Edge Retirement

Command output path:

- `output/phase1_p2c_truth_validation_v2_retirement_smoke/asls_truth_validation_summary.tsv`
- `output/phase1_p2c_truth_validation_v2_retirement_smoke/asls_truth_validation_rows.tsv`
- `output/phase1_p2c_truth_validation_v2_retirement_smoke/asls_truth_validation.json`
- `output/phase1_p2c_truth_validation_v2_retirement_smoke/asls_truth_validation.md`

Result:

- `gate_decision=REQUIRES_TIER_C`
- `LASTEXITCODE=3`

Interpretation: linear-edge deletion remains blocked because B2 stress safety and nonblank Tier C retirement evidence are not complete.

### Legacy v1 Scope Check

Command output path:

- `output/phase1_p2c_truth_validation_legacy_v1_smoke/asls_truth_validation_summary.tsv`
- `output/phase1_p2c_truth_validation_legacy_v1_smoke/asls_truth_validation.json`

Result:

- `gate_decision=INCONCLUSIVE_FIXTURE_SCOPE_MISMATCH`
- `LASTEXITCODE=2`
- `legacy_fixture_status=LEGACY_V1_NON_AUTHORITATIVE`
- `fixture_scope_status=INCONCLUSIVE_FIXTURE_SCOPE_MISMATCH`

Interpretation: v1 smoke output can no longer be used as current scientific authority.

## Remaining Risk

- B2 blank stress still reports `blank_false_positive`; that is a retirement/Tier C safety question, not a C1b planning blocker.
- B1 p95 relative-error cautions remain, so the closeout is planning-only. It does not authorize deletion of linear-edge columns, rollback columns, or compatibility facades.
- C5 must remain method-preserving unless a later closeout explicitly reaches `GO_FOR_LINEAR_EDGE_RETIREMENT`.

## Next Step

Proceed to C1b planning with B1 evidence as planning authority. Do not start linear-edge deletion until Tier C nonblank evidence, B2 stress safety disposition, blank safety disposition, C1a/C5 prerequisites, and rollback-column deprecation evidence are all present.
