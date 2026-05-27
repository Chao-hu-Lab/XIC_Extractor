# Handoff Productization Step 2 - Audit Spine Runtime Contract Spec

**Date:** 2026-05-27
**Status:** Draft for goal execution
**Branch / worktree:**
`codex/handoff-productization-step2` /
`C:\Users\user\Desktop\XIC_Extractor\.worktrees\handoff-productization-step2`
**Current source of truth:** [Handoff productization C0](../notes/2026-05-27-handoff-productization-c0-source-of-truth.md)
**Base sync:** reviewed after PR #66; worktree fast-forwarded to `f077a12`
(`master` / `origin/master`) before implementation.

## Purpose

Step 1 proved that `TraceGroup -> PeakHypothesis -> EvidenceVector ->
IntegrationResult -> AuditTrail` can project into the frozen
`peak_candidates.tsv` and `peak_candidate_boundaries.tsv` debug/audit schemas.

Step 2 must make that scaffold operational in the targeted runtime path without
changing production selection, resolver behavior, baseline integration, or
matrix output. The next useful move is not another report. It is to make the
targeted audit handoff build the hypothesis spine once and pass that spine to
the audit row projectors.

This moves the code one step away from parallel legacy wrappers:

```text
targeted trace -> audited PeakDetectionResult -> PeakHypothesis tuple
  -> candidate TSV projection
  -> boundary TSV projection
```

`PeakDetectionResult` remains the public return shape for this slice. The
hypothesis spine becomes the internal handoff between targeted extraction and
audit projection.

Adoption reason: this slice has value only if it makes the targeted audit
runtime consume one shared hypothesis spine and reduces duplicated legacy
wrapping. If implementation merely renames helpers while preserving two
independent wrappers, stop and revise the plan.

## Current State

The scaffold already exists:

- `Trace` / `TraceGroup` models live in
  `xic_extractor/peak_detection/traces.py`.
- `PeakHypothesis`, `EvidenceVector`, `IntegrationResult`, and `AuditTrail`
  live in `xic_extractor/peak_detection/hypotheses.py`.
- `build_peak_candidate_rows_from_hypotheses(...)` and
  `build_peak_candidate_boundary_rows_from_hypotheses(...)` can write rows from
  hypotheses while preserving TSV schemas.
- `extract_one_target(...)` creates a targeted `TraceGroup` when
  `emit_peak_candidates` is enabled.

The runtime still has duplicated wrapping:

- `append_peak_audit_rows(...)` creates one audited `PeakDetectionResult`.
- `append_peak_candidate_rows(...)` wraps that result into hypotheses for the
  candidate table.
- `append_peak_candidate_boundary_rows(...)` wraps the same result into
  hypotheses again for the boundary table.

That duplication is small, but it weakens the product direction: the audit
handoff still looks legacy-first even though the projection layer has already
moved to the spine.

## Required Change

### Step 1 - Keep the behavior contract frozen

Before implementation, confirm the current public surfaces:

- `peak_candidates.tsv` header/order comes from `PEAK_CANDIDATE_HEADERS`.
- `peak_candidate_boundaries.tsv` header/order comes from
  `PEAK_CANDIDATE_BOUNDARY_HEADERS`.
- `find_peak_and_area(...)` still returns `PeakDetectionResult`.
- `alignment_matrix.tsv` remains the downstream correction/statistics delivery
  surface and is not touched by this spec.

Do not add columns, metadata sidecars, config flags, or new output files.

### Step 2 - Build audited hypotheses once

Inside `xic_extractor/extraction/peak_candidate_audit.py`, after CWT audit
proposal injection and any audit rescoring, build one
`tuple[PeakHypothesis, ...]` for the audited result.

The tuple must include the same information currently emitted by both audit
tables:

- sample / target / role / ISTD pair / resolver metadata;
- selected candidate status, score, reason, support / concern / cap labels;
- MS2 / neutral-loss audit evidence;
- RT, area, baseline, uncertainty, and provenance values;
- CWT audit-only proposal markers.

Use the existing `TraceGroup` when available so all downstream projections read
the same trace arrays and `trace_group_id`.

### Step 3 - Make audit row appenders consume prebuilt hypotheses

Add narrow append helpers, or extend the current appenders with keyword-only
optional inputs, so the candidate and boundary audit emitters can project from
the same prebuilt hypothesis tuple.

The public compatibility functions must keep working:

- `append_peak_candidate_rows(...)`
- `append_peak_candidate_boundary_rows(...)`
- `build_peak_candidate_rows(...)`
- `build_peak_candidate_boundary_rows(...)`

Compatibility callers may still pass `PeakDetectionResult`; this slice only
makes the targeted audit orchestrator use the spine path internally.

### Step 4 - Preserve audit rescoring semantics

Candidate-table rescoring currently happens before the candidate rows are built.
If moving the hypothesis construction requires extracting that logic from
`peak_candidate_table.py`, keep it as a focused helper and add tests around it.

Do not change:

- scoring weights;
- selected candidate;
- confidence / reason wording;
- `safe_merge_*` fields;
- CWT source-only audit marker behavior.

### Step 5 - Record the next consumer boundary

After implementation, add a short closeout note under `docs/superpowers/notes/`
that states:

- which runtime path now consumes the hypothesis tuple directly;
- which legacy model remains public or internal;
- the next candidate consumer for migration;
- whether the next step is productization, cleanup, or blocked by a missing
  spine field.

Do not claim `production_ready`. The closeout verdict must use status
`handoff_spine_runtime_audit_ready` and gate language `shadow_ready`; do not
present either as product behavior readiness.

## Parallel Ownership Preflight

Before implementation, check the Phase2 cleanup worktree for in-flight edits.
This spec owns targeted audit projection files, which are intentionally avoided
by the C1a cleanup slice. Do not start implementation if another branch has
unmerged changes to the same files.

Suggested check:

```powershell
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/phase2-cleanup-safe-slice -C C:\Users\user\Desktop\XIC_Extractor\.worktrees\phase2-cleanup-safe-slice diff --name-only
git -c safe.directory=C:/Users/user/Desktop/XIC_Extractor/.worktrees/phase2-cleanup-safe-slice -C C:\Users\user\Desktop\XIC_Extractor\.worktrees\phase2-cleanup-safe-slice status --short
```

If the cleanup worktree is editing `peak_candidate_audit.py`,
`peak_candidate_table.py`, `peak_candidate_boundaries.py`, or `hypotheses.py`,
pause and reassign ownership before coding.

## File Scope

Allowed implementation files for this spec:

- `xic_extractor/extraction/peak_candidate_audit.py`
- `xic_extractor/extraction/peak_candidate_table.py`
- `xic_extractor/extraction/peak_candidate_boundaries.py`
- `xic_extractor/peak_detection/hypotheses.py` only if a missing field is
  required for exact projection parity
- focused tests under `tests/test_peak_candidate_audit.py`,
  `tests/test_peak_candidate_table.py`, `tests/test_peak_candidate_boundaries.py`,
  and `tests/test_peak_hypotheses.py`
- one closeout note under `docs/superpowers/notes/`

Avoid editing these files in this PR:

- `xic_extractor/peak_detection/baseline.py`
- `xic_extractor/peak_scoring.py`
- `xic_extractor/alignment/*`
- `xic_extractor/peak_detection/facade.py`
- `xic_extractor/peak_detection/models.py`
- public CLI / config / workbook / matrix writers

If implementation requires one of the avoided files, stop and update this spec
before coding further.

## Validation Contract

Focused tests:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_peak_hypotheses.py tests\test_peak_candidate_table.py tests\test_peak_candidate_boundaries.py tests\test_peak_candidate_audit.py -q
```

Contract assertions to add or preserve:

- `append_peak_audit_rows(...)` builds or receives one audited hypothesis tuple
  and both audit row surfaces project from it.
- A deterministic fixture that includes scored candidates, MS2/NL evidence,
  safe-merge fields, and a CWT-only audit proposal compares shared-hypothesis
  runtime rows against the legacy compatibility builder rows across every
  emitted header field.
- Candidate and boundary row fieldnames remain exactly equal to their header
  constants.
- Extra internal fields, including `trace_group_id`, are not emitted.
- Candidate and boundary rows use the same candidate ids for the same audited
  hypothesis.
- CWT source-only boundary rows retain
  `cwt_audit_filter_reason=legacy_cwt_width_not_real_cwt`.

Real RAW validation is not required for this slice unless emitted TSV rows
change beyond deterministic formatting or tests cannot prove row parity.

## Rollback Condition

Revert the Step 2 runtime wiring back to the Step 1 projection scaffold if any
of the following happen:

- any frozen TSV header, order, or row value changes without a separate approved
  behavior/schema spec;
- any compatibility entry point stops accepting its legacy inputs;
- preserving parity requires editing an avoided file;
- the shared-hypothesis runtime path needs a partial adapter that cannot express
  current audit rows exactly.

Rollback should keep the Step 1 `*_from_hypotheses` projection builders and
tests. Do not leave a half-migrated targeted runtime path in place.

## Acceptance

This spec is complete when:

- targeted audit runtime creates a single audited hypothesis tuple for candidate
  and boundary projection;
- frozen audit TSV headers and order are unchanged;
- public compatibility functions still accept the legacy inputs;
- focused tests pass;
- a closeout note records the remaining legacy surface and next consumer;
- no production matrix, resolver, baseline, or scoring behavior changes.

## Stop Conditions

Stop and ask for spec revision if:

- a required TSV field cannot be represented by `PeakHypothesis`,
  `EvidenceVector`, `IntegrationResult`, or `AuditTrail`;
- preserving row parity requires changing scoring, selection, resolver, or
  baseline semantics;
- implementation starts touching alignment, baseline relocation, or linear-edge
  retirement;
- the Phase2 cleanup branch needs to edit the same files in the same window.

## Review Requirement

Before implementation, review the implementation plan against this spec with the
critical artifact review contract in `docs/agent-subagent-routing.md`. If
subagents are not explicitly requested or available, perform the same review
locally and report the bypass reason.

- Does this actually move the product spine forward, or only rename wrappers?
- Does it preserve public output contracts?
- Does it reduce duplicated legacy wrapping without creating a bigger adapter?
- Is any `audit_only` path given a clear next exit rule?
- Is ownership / placement still correct between global skills, XIC overlays,
  runtime code, and docs?

After implementation, run the same review again. If findings are concrete, fix
them before opening a PR.
