# Claim Registry Hot Path Optimization Spec

**Date:** 2026-05-20
**Branch:** `codex/claim-registry-hot-path`
**Worktree:** `.worktrees/claim-registry-hot-path`
**Status:** Implemented and validated; retained as historical plan

## Summary

Optimize `xic_extractor/alignment/claim_registry.py` as the first
production-side hot path after diagnostics decomposition. This is an
equivalence-preserving refactor/optimization: matrix identity, cell status
semantics, winner selection, output schemas, and alignment pipeline order must
remain unchanged.

The current implementation is already well covered for core duplicate-claim
behavior. This phase adds a small benchmark/timing fixture, then optimizes only
the measured claim grouping path if the benchmark shows a meaningful target.

## Goals

- Preserve observable `AlignmentMatrix` results exactly for existing and new
  synthetic cases.
- Reduce unnecessary sorting / compatibility scans in sample-local claim
  grouping if benchmarked as meaningful.
- Keep `apply_ms1_peak_claim_registry()` as the public entry point.
- Keep `claim_registry.py` focused on matrix-level MS1 claim arbitration only.
- Avoid touching clustering, owner backfill, family integration, matrix identity,
  production gates, scoring, reliability, TSV/XLSX schemas, or workbook output.

## Non-Goals

- No change to duplicate assignment semantics.
- No new production gate.
- No real RAW rerun requirement for this phase unless synthetic and existing
  alignment tests expose a behavioral risk.
- No broad alignment architecture split.
- No optimization of `clustering.py`, `family_integration.py`, or
  `owner_backfill.py`.

## Current Contract To Preserve

- Only `detected` and `rescued` cells with finite `area`, `apex_rt`,
  `peak_start_rt`, and `peak_end_rt` can claim an MS1 peak.
- Claims are sample-local.
- Exact same peak claims are resolved even when m/z is outside the fuzzy gate.
- Fuzzy claims require m/z ppm, apex delta, and window overlap compatibility.
- Fuzzy grouping uses complete-link behavior: one bridge candidate must not
  merge two mutually incompatible endpoint claims.
- Production candidates beat review-only candidates.
- If all conflicting candidates are review-only, all are marked
  `duplicate_assigned` with `winner=none`.
- Winner sort order remains:
  detected support, event member count, event cluster count, detected over
  rescued, RT delta, cluster id, sample.

## Checkpoints

### Checkpoint 0: Preflight

- Confirm worktree and branch:
  - `.worktrees/claim-registry-hot-path`
  - `codex/claim-registry-hot-path`
- Confirm base includes PR #56 merge.
- Confirm no dirty changes except this spec.
- Run current claim registry tests:

```powershell
uv --cache-dir .uv-cache run pytest tests\test_alignment_claim_registry.py -q
```

### Checkpoint 1: Benchmark / Operation-Count Fixture

- Add a small deterministic benchmark-style test or diagnostic helper for
  sample-local claim grouping.
- Use synthetic `AlignmentMatrix` input only; no RAW files.
- Include scenarios:
  - many samples with one claim each,
  - one sample with many compatible claims,
  - one sample with many sparse m/z groups,
  - exact duplicate claims outside fuzzy m/z gate.
- The CI fixture must assert output equivalence and expose deterministic
  operation counts, such as compatibility checks and group winner evaluations.
- Optional elapsed timing may be printed by a manual diagnostic helper, but no
  wall-clock threshold may be required in CI.
- The fixture must keep using the public
  `apply_ms1_peak_claim_registry()` entry point; instrumentation may wrap private
  helpers only inside tests or diagnostics.

Review gate: verify benchmark fixture does not make CI flaky and does not
encode a new behavior contract beyond existing claim semantics.

### Checkpoint 2: Narrow Optimization

Only optimize if Checkpoint 1 shows the current path has a clear local target.
Allowed changes:

- Reduce repeated `min(..., key=_winner_sort_key)` calls while preserving winner
  tie-break order.
- Cache candidate compatibility inputs that are invariant within a sample.
- Keep exact claim grouping before fuzzy claim grouping.
- Keep complete-link compatibility for fuzzy groups.

Disallowed changes:

- Replacing complete-link grouping with single-link clustering.
- Changing winner tie-break order.
- Letting review-only candidates win production claims.
- Dropping exact duplicate handling outside fuzzy m/z gate.

Review gate: run targeted tests and inspect diff for behavior-only drift.

### Checkpoint 3: Validation

Run:

```powershell
uv --cache-dir .uv-cache run pytest tests\test_alignment_claim_registry.py -q
uv --cache-dir .uv-cache run pytest tests\test_alignment_owner_backfill.py tests\test_alignment_tsv_writer.py tests\test_alignment_pipeline.py -q
uv --cache-dir .uv-cache run ruff check xic_extractor\alignment\claim_registry.py tests\test_alignment_claim_registry.py
uv --cache-dir .uv-cache run mypy xic_extractor
```

If production code changes affect broader alignment behavior, also run:

```powershell
uv --cache-dir .uv-cache run pytest tests\test_untargeted_final_matrix_contract.py tests\test_alignment_production_decisions.py -q
```

### Checkpoint 4: Decision Note

Record one of:

- `keep_current`: benchmark does not justify code change.
- `optimized_equivalent`: optimization landed and all equivalence checks pass.
- `needs_behavior_plan`: meaningful improvement requires changing semantics.

The decision note must include:

- benchmark fixture shape,
- before/after deterministic operation-count evidence,
- optional local elapsed timing if collected outside CI,
- validation commands,
- explicit statement that matrix/review/cell schemas are unchanged.

## Stop Conditions

- Stop if the optimization changes duplicate winner decisions.
- Stop if complete-link behavior becomes ambiguous.
- Stop if output equality fails outside intentionally changed benchmark helper
  output.
- Stop if the improvement requires changing matrix identity, production gate,
  or scoring semantics; write a separate behavior-change plan instead.

## Expected Outcome

This phase should either land a small safe `claim_registry` optimization, or
prove that current code is acceptable and should not be touched before higher
impact production modules.
