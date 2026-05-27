# P2c AsLS Truth Validation Implementation Closeout

**Date:** 2026-05-26
**Superseded by:** `docs/superpowers/notes/2026-05-27-p2c-b1-b2-truth-validation-closeout-note.md`
**Verdict:** `NO_GO_KEEP_LINEAR_EDGE` for both P2c smoke targets.
**Readiness:** `diagnostic_only`.

This note records the original v1 synthetic Tier B closeout. It is no longer
current decision authority after the reviewed B1/B2 redesign. Use the superseding
2026-05-27 closeout for C1b planning and linear-edge retirement decisions.

## What Landed

- Added `python -m tools.diagnostics.asls_truth_validation`.
- Added locked Tier A manifest, synthetic Tier B fixture manifest, and per-row
  fixture lock under `docs/superpowers/fixtures/`.
- Added Tier A, Tier C, methodology waiver, and retirement-prerequisite
  validators.
- Added deletion-safe gate evaluator and exit-code mapping:
  - exit `0`: only `GO_FOR_LINEAR_EDGE_RETIREMENT`;
  - exit `1`: `NO_GO_KEEP_LINEAR_EDGE`;
  - exit `2`: invalid/stale/inconclusive evidence;
  - exit `3`: non-final diagnostic states.
- Added TSV/JSON/Markdown outputs with provenance, copied manifests, optional
  evidence copies, and fallback summary/JSON for invalid required inputs.

No production extraction behavior changed. No linear-edge deletion happened.

## Verification

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

Result: `121 passed`.

```powershell
git diff --check -- `
  tools\diagnostics\asls_truth_validation.py `
  tools\diagnostics\asls_truth_validation_synthetic.py `
  tests\test_asls_truth_validation_cli.py `
  tests\test_asls_truth_validation_synthetic.py
```

Result: no whitespace errors.

## Smoke Results

Planning target:

```powershell
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m tools.diagnostics.asls_truth_validation `
  --tier-a-rows output\phase1_p2_baseline_truth_audit_all_statuses\baseline_truth_audit_rows.tsv `
  --tier-a-summary output\phase1_p2_baseline_truth_audit_all_statuses\baseline_truth_audit_summary.tsv `
  --tier-a-json output\phase1_p2_baseline_truth_audit_all_statuses\baseline_truth_audit.json `
  --tier-a-report output\phase1_p2_baseline_truth_audit_all_statuses\baseline_truth_audit.md `
  --tier-a-manifest docs\superpowers\fixtures\asls_truth_tier_a_expected_manifest.json `
  --fixture-manifest docs\superpowers\fixtures\asls_truth_validation_fixture_manifest.json `
  --fixture-lock docs\superpowers\fixtures\asls_truth_validation_fixture_lock.json `
  --decision-target c1b-plan `
  --output-dir output\phase1_p2c_asls_truth_validation\c1b_plan
```

Result: exit `1`, `gate_decision=NO_GO_KEEP_LINEAR_EDGE`.

Retirement target:

```powershell
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m tools.diagnostics.asls_truth_validation `
  --tier-a-rows output\phase1_p2_baseline_truth_audit_all_statuses\baseline_truth_audit_rows.tsv `
  --tier-a-summary output\phase1_p2_baseline_truth_audit_all_statuses\baseline_truth_audit_summary.tsv `
  --tier-a-json output\phase1_p2_baseline_truth_audit_all_statuses\baseline_truth_audit.json `
  --tier-a-report output\phase1_p2_baseline_truth_audit_all_statuses\baseline_truth_audit.md `
  --tier-a-manifest docs\superpowers\fixtures\asls_truth_tier_a_expected_manifest.json `
  --fixture-manifest docs\superpowers\fixtures\asls_truth_validation_fixture_manifest.json `
  --fixture-lock docs\superpowers\fixtures\asls_truth_validation_fixture_lock.json `
  --decision-target linear-edge-retirement `
  --output-dir output\phase1_p2c_asls_truth_validation\linear_edge_retirement
```

Result: exit `1`, `gate_decision=NO_GO_KEEP_LINEAR_EDGE`.

## Current Blockers

Both smoke runs fail Tier B, not Tier A:

- `benchmark_status=FAIL`;
- `heldout_row_count=275`;
- `hard_blocker_count=30`;
- `coverage_status=PASS`;
- `max_asls_raw_area_exceedance_count=0`;
- `max_negative_nonblank_area_count=0`;
- `blank_false_positive_rate=0.542857`;
- row-level hard blockers: 19 `blank_false_positive` rows, all in
  `blank_noise_control`.

After enforcing the full spec hard blockers, aggregate Tier B also reports
relative-error and AsLS-vs-linear-edge failures across several synthetic
classes. This means P2c does **not** currently support C1b planning or
linear-edge retirement.

Primary artifacts:

- `output/phase1_p2c_asls_truth_validation/c1b_plan/asls_truth_validation_summary.tsv`
- `output/phase1_p2c_asls_truth_validation/c1b_plan/asls_truth_validation_rows.tsv`
- `output/phase1_p2c_asls_truth_validation/c1b_plan/asls_truth_validation.json`
- `output/phase1_p2c_asls_truth_validation/linear_edge_retirement/asls_truth_validation_summary.tsv`
- `output/phase1_p2c_asls_truth_validation/linear_edge_retirement/asls_truth_validation_rows.tsv`
- `output/phase1_p2c_asls_truth_validation/linear_edge_retirement/asls_truth_validation.json`

## Handoff

C1b remains blocked. C5 must stay method-preserving. P2b rollback-column
deprecation, C1a, C5, and retirement prerequisite manifests are still required
before any linear-edge deletion can be considered.

Next recommended step: review whether the locked synthetic Tier B fixtures and
hard-blocker tolerances are scientifically aligned with the real selected ISTD
evidence. Do not change production AsLS parameters or delete linear-edge from
this P2c result alone.
