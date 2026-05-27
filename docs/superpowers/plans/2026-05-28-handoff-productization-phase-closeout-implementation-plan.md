# Handoff Productization Phase Closeout Implementation Plan

> **For agentic workers:** Execute this as a docs / decision closeout. Do not
> migrate behavior while following this plan. If implementation pressure appears,
> record it as a `needs_behavior_spec` retirement row and stop short of code
> changes.

> **Execution status:** Implemented. Treat this file as the reviewed execution
> recipe; current verdict, retirement matrix, verification results, and next
> PR direction are recorded in
> `docs/superpowers/notes/2026-05-28-handoff-productization-phase-closeout.md`.
> Completed checkboxes below reflect the executed state in
> `codex/handoff-productization-closeout`; reuse the commands as a historical
> recipe only after re-validating the current worktree.

**Goal:** Close the current handoff productization phase with one canonical
phase closeout note, a legacy retirement readiness matrix, and a single
recommended next PR direction.

**Spec:** `docs/superpowers/specs/2026-05-28-handoff-productization-phase-closeout-spec.md`

**Goal prompt:** `docs/superpowers/plans/2026-05-28-handoff-productization-phase-closeout-goal.md`

**Architecture stance:** The spine exists and is now product-facing for targeted
selected-hypothesis assembly plus targeted CSV numeric projection. The phase is
not product-ready across the downstream matrix. This plan turns that boundary
into an explicit decision artifact rather than another audit backlog.

---

## File Map

- Create:
  `docs/superpowers/notes/2026-05-28-handoff-productization-phase-closeout.md`
- Create:
  `tests/test_handoff_phase_closeout_contract.py`
- Modify:
  `docs/superpowers/notes/2026-05-27-handoff-productization-c0-source-of-truth.md`
- Modify only if still misleading after inspection:
  `docs/superpowers/notes/2026-05-21-lcms-msms-handoff-progress-checklist.md`
- Do not modify runtime code unless a later reviewed plan changes scope.

## Now

### Task 1: Preflight Current Surface

- [x] Confirm branch and dirty scope:

```powershell
$repo = (Resolve-Path .).Path
git -c safe.directory="$repo" status --short --branch
codegraph status
```

Expected: branch is `codex/handoff-productization-closeout`; only closeout
planning docs are dirty or untracked.

- [x] Confirm current call-surface evidence:

```powershell
codegraph query selected_handoff_peak
codegraph context "ExtractionResult selected integration targeted CSV projection alignment_matrix legacy handoff closeout"
```

Expected evidence:

- `selected_handoff_peak` has `extract_one_target` as its production caller.
- targeted CSV projection consumes `ExtractionResult` reporting accessors.
- `alignment_matrix.tsv` is still owned by alignment / owner-backfill logic.

If the CLI context output does not show caller detail, use the CodeGraph MCP
`codegraph_callers` tool as the fallback for this one structural check.

### Task 2: Write The Canonical Phase Closeout

- [x] Create
  `docs/superpowers/notes/2026-05-28-handoff-productization-phase-closeout.md`.

Use this structure:

```markdown
# Handoff Productization Phase Closeout

## Verdict

Status: `handoff_productization_phase_closed`.

Targeted handoff / CSV consumer surfaces remain `production_candidate`. This is
not `production_ready`.

## What Actually Changed

## Public Contracts Preserved

## Legacy Retirement Readiness Matrix

| Surface | Owner | Label | Evidence | Blocker | Next action | Next PR target |
| --- | --- | --- | --- | --- | --- | --- |

## Recommended Next PR

## Non-Decisions

## Verification

## Remaining Risk
```

- [x] Populate the retirement matrix with every surface required by the spec.

Classification guidance:

- Active spine contracts such as `TraceGroup`, `PeakHypothesis`,
  `EvidenceVector`, `IntegrationResult`, `AuditTrail`, and
  `handoff_spine_runtime.py` should normally be `keep_for_now` because they are
  the future-facing surface, not retirement candidates.
- `ExtractionResult.selected_hypothesis` and selected integration accessors are
  compatibility bridge surfaces; classify as `facade_only` unless current code
  evidence shows another active semantic owner.
- targeted CSV projection is a migrated consumer; classify as `facade_only`
  because the emitted CSV remains the public compatibility surface.
- `peak_candidates.tsv` / `peak_candidate_boundaries.tsv` projection builders
  are debug/audit projections; classify as `externalize` or `keep_for_now`
  depending on whether the note recommends moving future product behavior away
  from them.
- `PeakDetectionResult`, `PeakCandidate`, `PeakResult`, `output.messages`,
  `output.detection`, anchor diagnostics, and ISTD recovery helpers still own
  behavior not represented by the spine; classify as `keep_for_now` or
  `needs_behavior_spec`, not `retire_now`.
- `alignment_matrix.tsv` / `AlignedCell` / owner-backfill should be
  `needs_behavior_spec` because it is the downstream delivery surface and has
  not consumed the handoff spine.
- recent resolver / baseline surfaces should be `needs_behavior_spec` unless a
  separate reviewed behavior plan already authorizes promotion or retirement.

- [x] Nominate exactly one recommended next PR direction.

Default recommendation unless evidence contradicts it:

`alignment_matrix_handoff_behavior_spec`: write a parity / behavior spec for
whether and how the downstream `alignment_matrix.tsv` contract should consume a
spine-derived selected integration contract. This is the highest-value next PR
because `alignment_matrix.tsv` is the correction/statistics delivery surface.

Do not implement that migration in this closeout.

### Task 3: Update Source-Of-Truth Pointers

- [x] Update the C0 source-of-truth note to point to the phase closeout as the
  newest handoff productization phase closeout / milestone-status source of
  truth.

Required wording:

- C0 remains historical scaffold rationale.
- Phase closeout owns current handoff status and next PR direction.
- `peak_candidates.tsv` remains a debug/audit projection, not a product matrix.

- [x] Inspect the old handoff progress checklist.

If it still reads like active planning authority, add a short banner at the top:

```markdown
> Historical inventory. Current handoff productization status and next PR
> direction are in
> `docs/superpowers/notes/2026-05-28-handoff-productization-phase-closeout.md`.
```

Do not rewrite the checklist.

### Task 4: Run Focused Verification

- [x] Run focused no-RAW tests:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_handoff_spine_runtime.py tests\test_result_assembly.py tests\test_target_extraction.py tests\test_csv_writers.py tests\test_peak_candidate_table.py tests\test_peak_candidate_boundaries.py tests\test_peak_candidate_audit.py -q
```

- [x] Replace the closeout note's verification placeholder with the exact
  command/result summary from this branch.

- [x] Run final focused tests, including the closeout contract test:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_handoff_spine_runtime.py tests\test_result_assembly.py tests\test_target_extraction.py tests\test_csv_writers.py tests\test_peak_candidate_table.py tests\test_peak_candidate_boundaries.py tests\test_peak_candidate_audit.py tests\test_handoff_phase_closeout_contract.py -q
```

- [x] Run static / artifact checks:

```powershell
$repo = (Resolve-Path .).Path
git -c safe.directory="$repo" diff --check
rg -n "phase closeout|handoff_productization_phase_closed|legacy retirement" docs\superpowers\notes\2026-05-27-handoff-productization-c0-source-of-truth.md docs\superpowers\notes\2026-05-21-lcms-msms-handoff-progress-checklist.md
python -c "from pathlib import Path; paths=[Path('docs/superpowers/specs/2026-05-28-handoff-productization-phase-closeout-spec.md'), Path('docs/superpowers/plans/2026-05-28-handoff-productization-phase-closeout-goal.md'), Path('docs/superpowers/plans/2026-05-28-handoff-productization-phase-closeout-implementation-plan.md'), Path('docs/superpowers/notes/2026-05-28-handoff-productization-phase-closeout.md')]; bad=[str(p) for p in paths if p.exists() and sum(1 for line in p.read_text(encoding='utf-8').splitlines() if line.startswith(chr(96)*3)) % 2]; raise SystemExit('Unbalanced markdown fences: '+', '.join(bad) if bad else 0)"
codegraph status
git -c safe.directory="$repo" status --short --branch
```

Expected:

- focused tests pass;
- no diff whitespace errors;
- closeout contract test passes, including overclaim wording, matrix
  completeness, exactly-one next PR target, source-of-truth links, and
  selected-handoff call-surface assertions;
- C0/checklist pointer check shows current closeout wording;
- CodeGraph remains up to date.

### Task 5: Post-Implementation Review

Perform read-only review from two angles before declaring complete:

- critical artifact review:
  - Does the closeout overclaim production readiness?
  - Does the retirement matrix classify every required surface?
  - Is the recommended next PR concrete enough to execute?
  - Are stale docs demoted without rewriting history?
- devex review:
  - Can the next agent find the source of truth quickly?
  - Are verification commands runnable in PowerShell?
  - Are "done", "not done", and "next" unambiguous?

Fix blockers and rerun the smallest affected verification.

## Later

- Write the recommended next PR spec if the closeout nominates
  `alignment_matrix_handoff_behavior_spec`.
- Phase2 cleanup remains deferred until handoff productization no longer needs
  the same core files.

## Not In Scope

- Runtime behavior changes.
- `alignment_matrix.tsv` migration.
- Resolver, scoring, baseline, ASLS, CWT production, NL, RT, workbook, CLI, or
  config changes.
- 8RAW / 85RAW validation.
- Large historical doc rewrites.

## Self-Review Before Execution

- [x] The plan closes a phase decision rather than creating another audit-only
  artifact.
- [x] The plan forces exactly one next PR direction or an explicit `no_go`.
- [x] The plan does not rely on 8RAW / 85RAW for docs-only closeout.
- [x] Verification commands are PowerShell-safe and do not treat "no grep
  matches" as failure.
- [x] Any behavior-changing retirement is recorded as `needs_behavior_spec`,
  not implemented here.
