# Handoff Productization MVP - Step2 Through Step4 Contract Spec

**Date:** 2026-05-28
**Branch / worktree:** `codex/handoff-productization-mvp` /
`.worktrees\handoff-productization-step2`
**Status:** draft for review
**Source of truth:** `docs/superpowers/notes/2026-05-27-handoff-productization-c0-source-of-truth.md`

## Decision

Fold Step2, Step3, and the Step4 downstream handoff contract note into one
handoff productization MVP PR.

The PR should move the handoff spine from audit-only runtime projection to a
small production-candidate consumer while preserving current production outputs:

```text
TraceGroup -> PeakHypothesis -> EvidenceVector -> IntegrationResult
  -> AuditTrail -> ExtractionResult / audit projections -> downstream matrix
```

The PR may claim `handoff_spine_mvp_ready` and `production_candidate`. It must
not claim `production_ready`, default-switch readiness, legacy retirement, or
85RAW acceptance.

## Why This Is One PR

Step2 alone proves runtime audit projection but still stops at debug TSVs.
Step3 alone would need the Step2 shared hypothesis runtime. Step4 is only a
contract note unless a production consumer exists. Combining these three closes
one coherent decision:

> Can the targeted runtime build a shared hypothesis spine and use it as a
> product-facing internal contract without changing current output behavior?

This is a better PR boundary than landing Step2 as another audit-only milestone
and then immediately opening another branch to prove the same runtime object can
feed product code.

## Current Baseline

Already implemented on this branch:

- `append_peak_audit_rows(...)` runs CWT audit proposal injection once.
- The audit path builds one shared `tuple[PeakHypothesis, ...]`.
- `peak_candidates.tsv` and `peak_candidate_boundaries.tsv` project from that
  tuple.
- Focused tests pass for candidate table, boundary table, audit appender, and
  hypothesis models.

Remaining gap:

- Production `ExtractionResult` assembly still reads directly from
  `PeakDetectionResult`, `PeakCandidate`, `Target`, and scattered selected
  candidate helpers. The spine is not yet a production-candidate internal
  consumer.

## MVP Scope

### Step2 - Shared Audit Spine Runtime

Keep the current Step2 implementation, with these constraints:

- `peak_candidates.tsv` header/order unchanged.
- `peak_candidate_boundaries.tsv` header/order unchanged.
- CWT audit proposals remain audit-only.
- Internal `trace_group_id` remains in-memory only and is not emitted.
- CWT proposal injection runs once per target audit call, not once per writer.

### Step3 - Selected Hypothesis Production-Candidate Consumer

Add a narrow production-candidate consumer for the selected hypothesis:

1. Build production-safe hypotheses from the original production
   `PeakDetectionResult`.
   - Do not include CWT audit-only proposal injection.
   - Do not rescore or change selected candidate.
   - Use the existing `TraceGroup` when available.
   - Use only already-available selected/cached MS2 evidence; do not force
     expensive MS2 evidence generation for every candidate in production result
     assembly.
   - Preserve post-selection `PeakDetectionResult` confidence/reason for the
     selected hypothesis. Candidate-level scores may be stale after penalties
     such as paired-anchor mismatch downgrades, so the selected production
     hypothesis must not resurrect pre-penalty confidence.
   - Keep this builder in a neutral extraction/runtime module, not inside TSV
     writer modules. Production assembly must not import
     `peak_candidate_table.py`, `peak_candidate_boundaries.py`, or
     `peak_candidate_audit.py`.

2. Add a selected-hypothesis helper.
   - It should return the `PeakHypothesis` whose `AuditTrail.selected` is true.
   - It should return `None` for no-peak / no-selected-candidate results.
   - It should not invent selection behavior.

3. Add an `ExtractionResult` assembly path that can consume the selected
   hypothesis.
   - It may keep `PeakDetectionResult` inside `ExtractionResult` for public
     compatibility.
   - It should source role, ISTD pair, confidence, reason, quality labels, and
     selected-candidate evidence from the selected hypothesis when present.
   - It must preserve current fallbacks. In particular, if the selected
     hypothesis has no scoring confidence but `peak_result.peak` exists,
     `ExtractionResult.confidence` must still be `HIGH`, matching the current
     `build_extraction_result(...)` behavior.
   - It must preserve output parity with the current
     `build_extraction_result(...)` path for deterministic fixtures.

4. Wire targeted extraction to build the production-safe selected hypothesis
   once and pass it to result assembly.
   - Current matrix values, result peak, diagnostics, resolver behavior, and
     NL/product logic must remain unchanged.
   - Audit rows may continue using the audit hypothesis tuple with CWT proposal
     injection because that is a separate audit projection.

This makes the spine a product-facing internal contract without making it the
production selector.

### Step4 - Downstream Matrix Handoff Contract Note

Add a closeout / contract note that records:

- `alignment_matrix.tsv` remains the downstream correction/statistics delivery
  surface.
- This MVP does not change matrix values, matrix schema, resolver defaults,
  baseline method, or production area integration.
- `ExtractionResult` is now the first product-facing consumer that can be
  assembled from the selected handoff hypothesis.
- The next productization decision is whether selection / integration should be
  natively represented by the spine, not whether to add more audit reports.
- Future downstream matrix work must prove parity first, then explicitly decide
  whether any matrix value change is intended.

## Out Of Scope

- Phase2 cleanup.
- `alignment_matrix.tsv` value or schema changes.
- Default resolver changes.
- Baseline default changes or linear-edge retirement.
- CWT production promotion.
- ASLS production switch.
- 8RAW / 85RAW acceptance gate.
- New public CLI/config/workbook fields.
- Broad refactors of `PeakDetectionResult`, `PeakCandidate`, or alignment
  matrix internals.

## Acceptance Criteria

- Step2 focused tests still pass.
- New tests cover the neutral production-safe handoff runtime helper, including
  selected-only MS2 mapping and `TraceGroup` reuse when provided.
- New tests prove final selected `PeakDetectionResult` confidence/reason win
  over stale candidate-level score summaries.
- New tests prove selected-hypothesis result assembly parity against
  `build_extraction_result(...)`.
- New tests prove the production selected-hypothesis path does not import or
  call CWT audit proposal injection.
- No public TSV headers change.
- No production matrix output code changes.
- No audit-only CWT proposals enter production result assembly.
- No extra MS2 evidence builder calls are introduced for production assembly.
- Closeout note uses `handoff_spine_mvp_ready` / `production_candidate`, not
  `production_ready`.
- Post-implementation review confirms the diff is product-facing handoff
  scaffolding, not another audit-only adapter, and fixes any blocker before PR.

## Verification

Focused unit tests:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_peak_hypotheses.py tests\test_handoff_spine_runtime.py tests\test_peak_candidate_table.py tests\test_peak_candidate_boundaries.py tests\test_peak_candidate_audit.py tests\test_result_assembly.py tests\test_target_extraction.py tests\test_csv_writers.py tests\test_messages.py -q
```

Static checks:

```powershell
python -m py_compile xic_extractor\extraction\peak_candidate_audit.py xic_extractor\extraction\peak_candidate_table.py xic_extractor\extraction\peak_candidate_boundaries.py xic_extractor\extraction\handoff_spine_runtime.py xic_extractor\extraction\result_assembly.py xic_extractor\extraction\target_extraction.py xic_extractor\peak_detection\hypotheses.py
uv run ruff check xic_extractor\extraction\peak_candidate_audit.py xic_extractor\extraction\peak_candidate_table.py xic_extractor\extraction\peak_candidate_boundaries.py xic_extractor\extraction\handoff_spine_runtime.py xic_extractor\extraction\result_assembly.py xic_extractor\extraction\target_extraction.py xic_extractor\peak_detection\hypotheses.py tests\test_peak_candidate_audit.py tests\test_peak_candidate_boundaries.py tests\test_handoff_spine_runtime.py tests\test_result_assembly.py tests\test_target_extraction.py
git diff --check
```

Broader validation is not required for this PR unless parity tests expose a
production output change. If implementation changes matrix code, stop and split
the work into a separate downstream matrix PR.

## Stop Rules

Stop before implementation or split the PR if:

- preserving parity requires changing resolver selection, baseline integration,
  NL matching, diagnostics, or matrix values;
- the selected production result cannot be represented by
  `PeakHypothesis` / `EvidenceVector` / `IntegrationResult` / `AuditTrail`
  without adding a semantic field;
- production assembly needs CWT audit-only candidates to pass;
- result assembly would need to generate MS2 evidence for all candidates rather
  than reuse selected/cached evidence;
- Phase2 cleanup files become necessary to complete the MVP.

## Review Questions

1. Does Step3 truly advance product behavior, or is it only another audit
   adapter?
2. Does the spec keep CWT audit-only evidence out of production assembly?
3. Is `ExtractionResult` the right first production-candidate consumer, or
   should the PR instead target resolver/model-selection?
4. Is Step4 only a contract note, and is it explicit enough to prevent accidental
   matrix behavior changes?
5. Are the stop rules strong enough to avoid another over-wide phase?
