# Selected Full-Envelope FE4 Preflight

**Date:** 2026-06-03
**Goal:** [Selected full-envelope quantitation boundary implementation goal](../plans/2026-06-03-selected-full-envelope-quantitation-boundary-implementation-goal.md)
**Spec:** [Selected full-envelope quantitation boundary spec](../specs/2026-06-03-selected-full-envelope-quantitation-boundary-spec.md)
**Readiness label:** `diagnostic_only`

## Verdict

FE4 must stop at `gate_decision=defer`.

The 8RAW runner surface itself is clear enough for a future run, but the current
selected-envelope work has only package-level FE2/FE3 contracts. It does not yet
have real selected-envelope changed-row diagnostics or a machine-readable
manual/expert boundary oracle manifest.

Phase naming note: the active implementation goal names this preflight `FE4`
because FE4 is the goal's 8RAW changed-row phase. The older spec text describes
the same 8RAW changed-row gate as `FE3`. This note follows the active goal while
preserving the same gate semantics: no RAW launch before real boundary-oracle
promotion.

Launching 8RAW now would produce output that cannot close the FE4 gate because
the previous oracle gate has not produced real-data `promote` evidence.

Machine-readable preflight manifest:

- [selected_full_envelope_fe4_preflight_manifest.json](../fixtures/selected_full_envelope_fe4_preflight_manifest.json)

## Gate Manifest

```text
gate_decision=defer
raw_launch_allowed=FALSE
readiness_label=diagnostic_only
changed_row_count=0
changed_row_denominator=0
changed_row_artifact_present=FALSE
changed_row_artifact_sha256=
expert_oracle_row_count=0
boundary_oracle_artifact_present=FALSE
boundary_oracle_artifact_sha256=
blocked_reasons=diagnostic_gate_not_promote:no_evaluated_rows;oracle_gate_not_promote:no_boundary_oracle_rows;no_changed_rows_to_review;missing_changed_row_artifact;no_expert_boundary_oracle_rows;missing_boundary_oracle_artifact
next_gate=bounded_follow_up_required
```

## Existing Artifact Check

Existing nearby artifacts do not satisfy the FE4 boundary-oracle requirement:

- `docs/superpowers/fixtures/asls_truth_tier_a_artifacts/` is AsLS-vs-current
  area/baseline evidence. It is not selected-envelope boundary truth.
- `output/validation_harness/targeted_ms2_trace_manual2/` is manual-2raw
  resolver calibration / workbook evidence. It does not currently expose the
  selected-envelope carrier fields or FE3 oracle manifest.
- `docs/superpowers/fixtures/shared_peak_identity_manual_oracle_v1.tsv` and
  related output oracles are identity / peak-selection oracles. They do not
  provide reviewed selected-envelope RT bounds and area truth.
- Existing targeted workbook controls are benchmark/control evidence only and
  must not be promoted to boundary truth.

## RAW Preflight Facts

No RAW run was launched.

Cheap no-RAW path checks:

- `local_validation_artifacts/discovery/accepted_p8b/8raw/discovery_batch_index.csv`
  exists.
- The accepted 8RAW discovery input has `8` rows.
- `C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation` exists.
- `C:\Xcalibur\system\programs` exists.

These facts mean the runner surface is not the blocker. The missing evidence is
the blocker.

## Required Bounded Follow-Up

Run a bounded FE3b/FE4-prep slice before any 8RAW changed-row diagnostic:

1. Generate or load real selected-envelope diagnostic rows using the FE2 carrier.
2. Attach machine-readable manual/expert reviewed boundary oracle rows for the
   changed or promotion-critical rows.
3. Build the FE3 oracle manifest from those comparisons.
4. Proceed to FE4 only if that manifest emits `gate_decision=promote`.

Until then, selected full-envelope remains `diagnostic_only` and product matrix
behavior must not change.

## Verification

Focused selected-envelope package shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_selected_full_envelope_changed_row_review.py tests/test_selected_full_envelope_oracle.py tests/test_selected_full_envelope_diagnostics.py tests/test_selected_full_envelope_policy.py tests/test_selected_full_envelope_fe0_contract.py tests/test_baseline_integration.py tests/test_peak_candidate_boundaries.py
```

Observed result:

```text
72 passed in 1.87s
```
