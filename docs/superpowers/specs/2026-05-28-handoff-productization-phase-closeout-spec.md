# Handoff Productization Phase Closeout Spec

**Date:** 2026-05-28
**Branch / worktree:** `codex/handoff-productization-closeout` /
`.worktrees\handoff-productization-closeout`
**Status:** accepted and implemented by the phase closeout note; this spec is
supporting contract history, not the current verdict surface
**Authoritative inputs:**

- `docs/superpowers/notes/2026-05-27-handoff-productization-c0-source-of-truth.md`
- `docs/superpowers/notes/2026-05-28-handoff-productization-mvp-closeout.md`
- `docs/superpowers/notes/2026-05-28-handoff-productization-consumer-migration-closeout.md`
- `docs/superpowers/notes/2026-05-28-handoff-productization-consumer-migration-review-note.md`
- `docs/agent-subagent-routing.md`
- CodeGraph initialized in this worktree for current call-surface evidence

## Decision

Close the current handoff productization phase by producing a single canonical
phase closeout artifact and a legacy retirement readiness matrix.

This closeout may claim for the phase artifact:

- `handoff_productization_phase_closed`

It may record `production_candidate` only for the already verified targeted
handoff / CSV consumer surfaces. It must not use `production_candidate` as a
blanket status for the whole repository, alignment matrix handoff, resolver
behavior, baseline behavior, CWT promotion, ASLS promotion, or broad legacy
retirement.

It must not claim:

- `production_ready`
- `alignment_matrix.tsv` migration
- default resolver or baseline switch readiness
- CWT production promotion
- ASLS promotion
- full legacy retirement

The closeout is a decision artifact plus narrow verification. It is not another
audit-only report and not a behavior-change PR.

The closeout must nominate exactly one next PR direction from the retirement
matrix, or explicitly state `no_go` with the single blocker that prevents
choosing one. This is the difference between a phase decision and another
passive inventory.

## Why This Step Exists

The previous handoff productization PRs established the spine scaffold, added a
production-facing selected-hypothesis handoff, and migrated targeted CSV numeric
projection to `ExtractionResult` accessors. That is meaningful progress, but it
does not answer the practical closeout questions:

- Which parts are now product-facing enough to keep building on?
- Which legacy paths can be retired, wrapped as compatibility facades, or must
  stay until a behavior spec exists?
- Which old docs are now historical inventory instead of planning authority?
- What exact next PR should continue the handoff roadmap without slipping back
  into audit-only work?

Without this closeout, future work can easily overclaim readiness, retry already
settled audit questions, or start Phase2 cleanup before the product direction is
actually handed off.

## Current Evidence Baseline

Current CodeGraph and source inspection show:

- `selected_handoff_peak(...)` has one production caller:
  `xic_extractor/extraction/target_extraction.py::extract_one_target`.
- `ExtractionResult` selected integration accessors are consumed by targeted
  CSV projection and covered by focused tests.
- `alignment_matrix.tsv` is still produced by the alignment owner/backfill path
  and has not consumed the handoff spine.
- `output.detection`, `output.messages`, anchor diagnostics, ISTD recovery, and
  scoring factory still legitimately inspect legacy `PeakDetectionResult` /
  `PeakCandidate` state.
- Audit projection surfaces still exist for `peak_candidates.tsv` and
  `peak_candidate_boundaries.tsv`; these are debug/audit projections, not the
  canonical domain model.

This means the phase can be closed as productization progress, but broad legacy
retirement is not yet justified.

## Scope

### C1 - Canonical Phase Closeout Note

Create:

- `docs/superpowers/notes/2026-05-28-handoff-productization-phase-closeout.md`

The note must include:

- phase verdict and allowed status language;
- what actually changed across C0, MVP, and consumer migration;
- public contracts preserved;
- validation actually run for this closeout;
- legacy retirement readiness matrix;
- next PR recommendation;
- explicit non-goals and remaining risks.

The closeout note becomes the newest handoff productization phase closeout and
milestone-status source of truth. It does not supersede the C0 product
direction, runtime contracts, schema headers, or older closeout evidence. It
summarizes their current meaning for the next handoff productization decision.

### C2 - Legacy Retirement Decision Matrix

The closeout note must classify each relevant surface with one of these labels:

| Label | Meaning |
| --- | --- |
| `retire_now` | Dead or superseded surface can be removed without behavior drift. |
| `facade_only` | Keep public compatibility, but future code should depend on spine-facing accessors or adapters. |
| `needs_behavior_spec` | Retirement would change production value, schema, score, diagnostics, or downstream handoff. |
| `keep_for_now` | Still owns active semantics not represented by the spine. |
| `externalize` | Keep only as optional diagnostic/reference outside the production sequence. |

Minimum surfaces to classify:

- `TraceGroup`
- `PeakHypothesis` / `EvidenceVector` / `IntegrationResult` / `AuditTrail`
- `handoff_spine_runtime.py`
- `ExtractionResult.selected_hypothesis` and selected integration accessors
- targeted CSV projection
- `peak_candidates.tsv` / `peak_candidate_boundaries.tsv` projection builders
- `PeakDetectionResult` / `PeakCandidate` / `PeakResult`
- `output.messages` and `output.detection`
- anchor diagnostics and ISTD recovery helpers
- `alignment_matrix.tsv` / `AlignedCell` / owner-backfill path
- legacy resolver or baseline method surfaces touched by recent planning

Each row must name:

- current owner;
- retirement label;
- evidence;
- missing blocker if not retired;
- next action;
- whether this row is the recommended next PR target.

At least one row must be classified as `facade_only`, `needs_behavior_spec`, or
`externalize` with a concrete next action. If every row is `keep_for_now`, the
closeout has failed to close the phase decision and must be revised.

### C3 - Documentation Source-Of-Truth Cleanup

Update only the minimal durable docs needed to prevent stale planning authority:

- Link the new closeout note from the C0 source-of-truth note.
- If older checklist wording still reads like active planning authority, mark it
  as historical inventory and point to the new closeout.
- Do not rewrite the whole historical checklist unless a specific stale line
  would mislead the next phase.

### C4 - Focused Verification

Run no-RAW verification that proves current product-facing handoff contracts are
still intact:

- existing focused handoff/CSV tests;
- no-RAW closeout contract test for retirement matrix completeness,
  overclaim wording, and selected-handoff call surface;
- `py_compile` for touched runtime modules if code changed;
- `ruff` for touched Python/test files if code changed;
- `git diff --check`;
- grep or CodeGraph-backed drift checks for accidental overclaims and forbidden
  dependency drift.

This closeout should not run 8RAW or 85RAW. No behavior change is planned, and
real-data validation would not change the decision.

## Out Of Scope

- Phase2 cleanup.
- Retiring `PeakDetectionResult`, `PeakCandidate`, `PeakResult`, resolver
  defaults, baseline methods, or alignment owner models.
- Migrating `alignment_matrix.tsv`.
- Changing CSV/TSV/workbook schemas.
- Changing resolver selection, scoring, baseline, ASLS, CWT, NL matching, RT
  policy, diagnostics, or matrix values.
- Running 8RAW / 85RAW validation.
- Adding new audit TSVs, dashboards, or human reports.

## Public Contracts

These must remain unchanged:

- `alignment_matrix.tsv` downstream correction/statistics contract;
- `xic_results.csv`, `xic_results_long.csv`, and `xic_score_breakdown.csv`
  schemas and formatting;
- `peak_candidates.tsv` and `peak_candidate_boundaries.tsv` schemas;
- CLI flags, config keys, workbook schemas, resolver defaults, baseline
  defaults, and diagnostic status meanings.

## Acceptance Criteria

- A phase closeout note exists and is the newest handoff productization phase
  closeout / milestone-status source of truth.
- The closeout includes a legacy retirement decision matrix with the required
  labels, evidence, blockers, and next actions.
- The matrix nominates exactly one next PR direction, or records a `no_go`
  blocker that explains why no direction is currently executable.
- C0 or checklist docs no longer imply that stale milestone language is the
  current planning authority.
- The closeout clearly distinguishes infrastructure existence from product
  behavior.
- The closeout explicitly states that targeted CSV consumer migration is done,
  while `alignment_matrix.tsv` migration and broad legacy retirement are not.
- Focused tests and static checks pass or a precise blocker is recorded.
- No production behavior, schema, resolver, baseline, scoring, or matrix code is
  changed unless a later reviewed plan explicitly justifies a tiny docs-test or
  smoke-test addition.
- Post-implementation review confirms the closeout answers legacy retirement
  readiness rather than creating another audit-only backlog item.

## Verification

Focused tests:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_handoff_spine_runtime.py tests\test_result_assembly.py tests\test_target_extraction.py tests\test_csv_writers.py tests\test_peak_candidate_table.py tests\test_peak_candidate_boundaries.py tests\test_peak_candidate_audit.py tests\test_handoff_phase_closeout_contract.py -q
```

Static / artifact checks:

```powershell
$repo = (Resolve-Path .).Path
git -c safe.directory="$repo" diff --check
rg -n "phase closeout|handoff_productization_phase_closed|legacy retirement" docs\superpowers\notes\2026-05-27-handoff-productization-c0-source-of-truth.md docs\superpowers\notes\2026-05-21-lcms-msms-handoff-progress-checklist.md
python -c "from pathlib import Path; paths=[Path('docs/superpowers/specs/2026-05-28-handoff-productization-phase-closeout-spec.md'), Path('docs/superpowers/plans/2026-05-28-handoff-productization-phase-closeout-goal.md'), Path('docs/superpowers/notes/2026-05-28-handoff-productization-phase-closeout.md')]; bad=[str(p) for p in paths if p.exists() and sum(1 for line in p.read_text(encoding='utf-8').splitlines() if line.startswith(chr(96)*3)) % 2]; raise SystemExit('Unbalanced markdown fences: '+', '.join(bad) if bad else 0)"
codegraph status
```

The closeout contract test is the mechanical gate for overclaim wording,
retirement-matrix completeness, exactly-one next PR target, source-of-truth
links, and the selected-handoff call surface.

If Python docs tests are added later, they must be no-RAW and deterministic.

## Stop Rules

Stop and revise the spec or plan if:

- answering legacy retirement readiness requires behavior changes;
- a retirement row lacks evidence or a blocker;
- the closeout would be true only after `alignment_matrix.tsv` migration;
- preserving the public contract requires touching resolver, scoring, baseline,
  NL, diagnostics, or matrix logic;
- review finds that this is just another audit-only report without a next
  product decision;
- verification would require 8RAW / 85RAW to prove a docs-only closeout.

## Review Questions

1. Does this close a real phase decision, or just add another summary document?
2. Is the legacy retirement matrix concrete enough to guide the next PR?
3. Are the labels conservative without preserving bad legacy paths by default?
4. Does the spec avoid overclaiming `production_ready`?
5. Is skipping 8RAW / 85RAW justified by the no-behavior-change scope?
