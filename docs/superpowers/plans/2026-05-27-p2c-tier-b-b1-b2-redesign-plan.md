# P2c Tier B B1/B2 Redesign Implementation Plan

**Date:** 2026-05-27
**Status:** Implemented v0.3 - focused shard and smoke validation passed
**Spec:** `docs/superpowers/specs/2026-05-26-peak-pipeline-asls-truth-validation-spec.md`

## Goal

Bring the existing P2c AsLS truth-validation diagnostic up to the reviewed v0.3
B1/B2 contract:

- B1 relevance fixtures drive `decision_target=c1b-plan`.
- B2 stress fixtures are reported separately and cannot by themselves create a
  c1b `NO_GO_KEEP_LINEAR_EDGE`.
- v1 synthetic outputs are explicitly non-authoritative under the B1/B2
  contract.
- linear-edge retirement remains blocked unless B1, B2/Tier C safety, nonblank
  Tier C truth, and cleanup prerequisites all pass.

## Now

1. **Schema and model contract**
   - Update `tools/diagnostics/asls_truth_validation_models.py` with the new
     summary, row, and coverage fields.
   - Add constants/enums for `tier_b_layer`, `blocker_scope`,
     `legacy_fixture_status`, `tier_b1_accuracy_scope`,
     `production_like_bounds_status`, and stress-axis disposition fields.
   - Redesign the benchmark seam so `SyntheticBenchmarkResult` carries B1 hard
     blockers, B1 caution/planning-only signals, and B2 retirement blockers as
     separate fields. No caller may pass a single mixed `hard_blockers` tuple
     into c1b decision logic.
   - Add schema tests that assert exact `SUMMARY_FIELDS`, `ROW_FIELDS`,
     `COVERAGE_FIELDS`, JSON schema version, and gate decision constants.

2. **Manifest and lock parsing**
   - Extend `tools/diagnostics/asls_truth_validation_manifests.py` to parse the
     required v2 manifest keys and per-row fixture-lock keys.
   - Review/freeze `docs/superpowers/fixtures/asls_truth_tier_a_expected_manifest.json`
     before deriving B1 production-like bounds or running the gate.
   - Validate Tier A current-code compatibility, source input hashes, expected
     selected-family counts, artifact hashes, and freshness; stale/hash-drifted
     Tier A evidence must emit `INCONCLUSIVE_REGENERATE_TIER_A`.
   - Regenerate and freeze
     `docs/superpowers/fixtures/asls_truth_validation_fixture_manifest.json` and
     `docs/superpowers/fixtures/asls_truth_validation_fixture_lock.json` as
     `synthetic_truth_fixture_v2` / `asls_truth_tolerance_v2`.
   - Recompute per-row generator hashes and the whole-lock hash, and add a
     review/freeze marker in the fixture lock metadata.
   - Add lock-drift tests proving changed lock hashes emit
     `INCONCLUSIVE_FIXTURE_LOCK_CHANGED`.
   - Preserve v1 loading only as legacy discovery evidence:
     `fixture_scope_status=INCONCLUSIVE_FIXTURE_SCOPE_MISMATCH` and
     `legacy_fixture_status=LEGACY_V1_NON_AUTHORITATIVE`.
   - Add tests for valid v2 rows, missing gate-layer keys, lock drift, and v1
     migration.

3. **Synthetic fixture classification**
   - Update `tools/diagnostics/asls_truth_validation_synthetic.py` so every
     synthetic row carries `tier_b_layer`, `decision_scope`,
     `production_like_bounds_status`, scan-density/bounds metadata, and
     `blocker_scope`.
   - Split hard-blocker evaluation into B1 relevance blockers, B1 caution /
     planning-only accuracy signals, and B2 retirement-stress blockers.
   - Derive B1 production-like bounds from Tier A point-count and RT-width
     quantiles instead of fixed 64-point heldout windows.
   - Emit Tier A -> B1 coverage records. B1 coverage must be complete for every
     observed selected-family pattern before c1b planning can be GO; B2-only
     classes must not satisfy B1 coverage.
   - Preserve calibration/heldout separation: thresholds may use calibration
     rows only, heldout rows cannot be dropped or retuned after comparator code
     exists, and threshold changes must create a new manifest version plus
     `previous_failed_run_refs`.

4. **Gate decision rollup**
   - Update `tools/diagnostics/asls_truth_validation_analysis.py` so
     `decision_target=c1b-plan` uses Tier A + B1 + supplied B1-scope nonblank
     Tier C failures for final `gate_decision` and c1b `NO_GO`.
     `synthetic_decision_status` remains B1-only and must not relabel real Tier
     C failures as synthetic failures.
   - Split Tier C into `tier_c_nonblank_status`, `blank_safety_status`, and
     `stress_axis_dispositions`.
   - Remove `ACCEPTED_NO_CONTROLS` as a retirement pass; only `PASS` or
     `NOT_APPLICABLE_WITH_EXCLUSION` can satisfy blank safety.
   - Update `tools/diagnostics/asls_truth_validation_inputs.py` so no-controls
     statements no longer authorize retirement; only a machine-checkable
     exclusion/pass-through contract can produce
     `NOT_APPLICABLE_WITH_EXCLUSION`.
   - Add exit-code tests: `GO_FOR_C1B_PLAN_SYNTHETIC_ONLY` and `REQUIRES_*`
     exit `3`, `INCONCLUSIVE_*` exits `2`, and scientific no-go exits `1`.

5. **CLI outputs and reports**
   - Update `tools/diagnostics/asls_truth_validation.py` to emit the v0.3
     columns, JSON summaries, markdown summary, copied fixture artifacts, and
     target-specific `benchmark_status`.
   - Ensure existing v1 outputs are not silently treated as scientific no-go
     evidence.
   - Update `tools/diagnostics/INDEX.md` so the tool entry no longer says the
     current v1 synthetic smoke is authoritative `NO_GO_KEEP_LINEAR_EDGE`.
   - Update or add CLI tests for legacy v1 output, v2 B1/B2 output, exact schema
     order, and `asls_truth_validation_v2` JSON schema version.

6. **Closeout evidence**
   - Run the focused P2c pytest shard.
   - Run a v1 legacy smoke proving it emits an inconclusive/non-authoritative
     state.
   - Run the v2 B1/B2 c1b-plan smoke. The expected result is not hard-coded as
     GO; the required property is that any c1b no-go is traceable to B1, not B2.
   - Write a closeout note with gate decision, artifact paths, and remaining
     retirement-only evidence gaps.
   - The closeout must include machine-readable cleanup authority fields:
     `c1b_planning_allowed`, `linear_edge_deletion_allowed`,
     `c5_method_preserving_required`, and `cleanup_specs_to_update`.

## Later

- Build or collect real Tier C nonblank truth evidence if B1 only reaches
  planning authority.
- Use B2 stress results to define targeted blank/carryover, coelution, low-S/N,
  or clipping follow-up only when those states matter to selected ISTD or
  downstream target rows.
- Return to Cleanup C1b only after P2c closeout says either planning authority
  or retirement authority, and keep deletion blocked unless retirement authority
  is explicit.

## Not In Scope

- Changing production AsLS parameters.
- Changing RT resolver or boundary resolver behavior.
- Deleting linear-edge.
- Changing `alignment_matrix.tsv` or primary 85RAW delivery outputs.
- Introducing `.mzML` conversion or third-party feature-finding tools.
- Running another full 85RAW validation unless the implementation changes a
  production delivery path.

## Acceptance Criteria

- `git diff --check` passes for changed files.
- Focused pytest shard passes:

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

- v1 fixture artifacts are reported as
  `LEGACY_V1_NON_AUTHORITATIVE` /
  `INCONCLUSIVE_FIXTURE_SCOPE_MISMATCH` when used as current authority.
- v2 fixture manifest and lock are regenerated, reviewed/frozen, hash-recorded,
  and included in the diff.
- Tier A expected manifest is reviewed/frozen, hash-recorded, and enforced for
  freshness/current-code compatibility before B1 bounds or coverage are derived.
- Tier A artifact hash drift, stale generated SHA, source input drift, or missing
  compatibility evidence emits `INCONCLUSIVE_REGENERATE_TIER_A`.
- Lock drift emits `INCONCLUSIVE_FIXTURE_LOCK_CHANGED`.
- Tier A -> B1 coverage is complete before c1b planning can be GO; unmapped
  selected-family patterns emit `INCONCLUSIVE_FIXTURE_GAP`; B2-only fixtures do
  not satisfy B1 coverage.
- For `decision_target=c1b-plan`, B2 blank/coelution/low-SN/clipping stress
  blockers do not set `benchmark_status=FAIL` or `NO_GO_KEEP_LINEAR_EDGE`.
- For `decision_target=c1b-plan`, supplied
  `tier_c_nonblank_status=FAIL` covering the selected ISTD/B1 scope blocks GO.
- `synthetic_decision_status` remains B1-only even when real Tier C evidence
  blocks the final gate decision.
- Any `NO_GO_KEEP_LINEAR_EDGE` for c1b-plan names a B1 relevance blocker.
- For `decision_target=linear-edge-retirement`, missing nonblank Tier C truth,
  unresolved B2 safety, missing blank safety, or missing cleanup prerequisites
  prevent retirement authority.
- `ACCEPTED_NO_CONTROLS` no longer authorizes retirement; no-controls statements
  require `REQUIRES_TIER_C` unless backed by a machine-checkable
  exclusion/pass-through contract.
- CLI exit codes match the spec for GO, planning-only, no-go, and inconclusive
  states.
- `tools/diagnostics/INDEX.md` reflects the B1/B2 contract and marks v1 smoke
  as non-authoritative discovery evidence.
- Closeout states cleanup authority explicitly:
  `c1b_planning_allowed`, `linear_edge_deletion_allowed`,
  `c5_method_preserving_required`, and `cleanup_specs_to_update`.
- Any non-`GO_FOR_LINEAR_EDGE_RETIREMENT` closeout states that C5 remains
  method-preserving and linear-edge deletion is blocked.

## Stop Conditions

- B1 production-like rows cannot be derived from Tier A quantiles without
  inventing undocumented assumptions.
- B1 reveals AsLS raw-area exceedance, wrong RT identity, unacceptable boundary
  expansion, or nonblank negative area.
- A second B1/B2 synthetic-only revision is inconclusive.
- The implementation would require changing production extraction/alignment
  behavior to make the diagnostic pass.
