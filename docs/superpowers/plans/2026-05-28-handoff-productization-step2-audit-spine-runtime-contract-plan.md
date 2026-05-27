# Handoff Productization Step 2 - Audit Spine Runtime Contract Plan

**Goal:** Make the targeted audit runtime build one shared
`PeakHypothesis` tuple and project both `peak_candidates.tsv` and
`peak_candidate_boundaries.tsv` from that tuple, without changing production
selection, resolver behavior, baseline integration, matrix output, or frozen
TSV schemas.

**Spec:** `docs/superpowers/specs/2026-05-27-handoff-productization-step2-audit-spine-runtime-contract-spec.md`

**Base:** reviewed after PR #66; worktree is fast-forwarded to `f077a12`
(`master` / `origin/master`).

## Review Verdict

Local critical review before implementation: `NO BLOCKER`.

- Product direction: advances the handoff spine because runtime projection, not
  only synthetic tests, will consume shared hypotheses.
- Contract: audit TSV headers and compatibility appenders must remain frozen.
- Ownership / placement: this branch owns targeted audit projection files only;
  Phase2 cleanup owns baseline relocation and must not touch these files.
- Adoption reason: proceed only if duplicated legacy wrapping is reduced. If the
  implementation becomes a larger adapter with no shared runtime spine, stop.

Subagent review bypass reason: this turn did not explicitly request subagents.
The same critical artifact review checklist from `docs/agent-subagent-routing.md`
was applied locally.

## Now

1. Add a shared hypothesis builder path in
   `xic_extractor/extraction/peak_candidate_audit.py`.
   - Inject CWT audit proposals.
   - Apply candidate-table audit rescoring before hypothesis construction.
   - Build one `tuple[PeakHypothesis, ...]` with the existing `TraceGroup` when
     available.

2. Add or extend narrow projection helpers.
   - Candidate rows can consume prebuilt hypotheses.
   - Boundary rows can consume the same prebuilt hypotheses.
   - Existing public compatibility functions still accept `PeakDetectionResult`
     and legacy arguments.

3. Add parity tests.
   - Shared-hypothesis runtime rows match legacy builder rows across emitted
     header fields.
   - Candidate and boundary fieldnames equal header constants.
   - `trace_group_id` and other internal fields are not emitted.
   - CWT source-only boundary rows keep
     `cwt_audit_filter_reason=legacy_cwt_width_not_real_cwt`.

4. Add closeout note.
   - State `handoff_spine_runtime_audit_ready`.
   - Gate language: `shadow_ready`, not product behavior readiness.
   - Name next consumer migration target.

## Later

- Migrate another consumer only after this runtime audit path has row parity.
- Decide separately whether production selection should consume the spine.

## Not In Scope

- No production matrix, resolver, baseline, scoring weight, selection, CLI,
  config, workbook, or schema changes.
- No Phase2 cleanup or baseline relocation edits.
- No RAW validation unless focused deterministic tests cannot prove row parity.

## Verification

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_peak_hypotheses.py tests\test_peak_candidate_table.py tests\test_peak_candidate_boundaries.py tests\test_peak_candidate_audit.py -q
python -m py_compile xic_extractor\extraction\peak_candidate_audit.py xic_extractor\extraction\peak_candidate_table.py xic_extractor\extraction\peak_candidate_boundaries.py xic_extractor\peak_detection\hypotheses.py
git diff --check
```

## Stop Conditions

- A required TSV field cannot be represented by the existing spine models.
- Preserving row parity requires changing scoring, selection, resolver, or
  baseline semantics.
- The implementation touches Phase2 cleanup files or alignment/matrix output.
- Candidate and boundary projections cannot share the same hypothesis tuple
  without losing current audit evidence.
