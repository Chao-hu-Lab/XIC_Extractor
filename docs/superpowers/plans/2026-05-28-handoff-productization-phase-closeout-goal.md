/goal
GOAL:
Close the current handoff productization phase by creating a canonical phase
closeout note and legacy retirement readiness matrix, then verify that the
existing handoff/CSV contracts still hold without changing production behavior.

CONTEXT:
- Repo: `XIC_Extractor`
- Worktree: `.worktrees\handoff-productization-closeout`
- Branch: `codex/handoff-productization-closeout`
- Spec:
  `docs/superpowers/specs/2026-05-28-handoff-productization-phase-closeout-spec.md`
- Read first:
  - `AGENTS.md`
  - `docs/agent-subagent-routing.md`
  - `docs/agent-parameter-settings.md`
  - `docs/superpowers/notes/2026-05-27-handoff-productization-c0-source-of-truth.md`
  - `docs/superpowers/notes/2026-05-28-handoff-productization-mvp-closeout.md`
  - `docs/superpowers/notes/2026-05-28-handoff-productization-consumer-migration-closeout.md`
  - `docs/superpowers/notes/2026-05-28-handoff-productization-consumer-migration-review-note.md`
  - `xic_extractor/extraction/handoff_spine_runtime.py`
  - `xic_extractor/extractor.py`
  - `xic_extractor/output/csv_writers.py`
  - `xic_extractor/alignment/pipeline.py`
  - `xic_extractor/alignment/matrix.py`
- CodeGraph is initialized in this worktree and should be used for current
  call-surface checks before editing.

CONSTRAINTS:
- Keep scope limited to phase closeout, source-of-truth cleanup, and retirement
  readiness documentation.
- Verification integrity: do not weaken or bypass tests, assertions, lint,
  generated-output checks, or external blockers to make the goal pass; fix the
  root cause or report the blocker.
- Do not change production selection, resolver defaults, scoring, baseline,
  ASLS, CWT production behavior, NL matching, RT policy, diagnostics semantics,
  workbook schemas, CLI flags, config keys, CSV/TSV schemas, or matrix values.
- Do not migrate `alignment_matrix.tsv`.
- Do not retire `PeakDetectionResult`, `PeakCandidate`, `PeakResult`, alignment
  owner models, or legacy resolver/baseline paths in this goal.
- Do not run 8RAW or 85RAW; this closeout has no intended behavior change.
- Use status language honestly: the phase artifact may claim
  `handoff_productization_phase_closed`; it may record `production_candidate`
  only for already verified targeted handoff / CSV consumer surfaces. Do not
  claim `production_ready` or blanket `production_candidate` for the whole repo.
- If the closeout reveals a behavior-changing retirement, record it as
  `needs_behavior_spec` and stop short of implementing it.

DONE WHEN:
- `docs/superpowers/notes/2026-05-28-handoff-productization-phase-closeout.md`
  exists and is the newest handoff productization phase closeout /
  milestone-status source of truth.
- The closeout note summarizes C0, MVP, and consumer migration outcomes without
  duplicating full historical notes.
- The closeout includes a legacy retirement readiness matrix with labels,
  evidence, blockers, and next actions for all surfaces required by the spec.
- The matrix nominates exactly one next PR direction, or records a `no_go`
  blocker that explains why no direction is currently executable.
- C0/checklist docs point to the new closeout where stale planning authority
  would otherwise mislead the next phase.
- The closeout explicitly says targeted CSV consumer migration is done, while
  `alignment_matrix.tsv` migration, broad legacy retirement, and production
  readiness are not done.
- Focused no-RAW tests and static checks from the spec pass, or an exact blocker
  is recorded.
- Worktree has no unrelated dirty files.

VERIFY:
- Run focused tests:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_handoff_spine_runtime.py tests\test_result_assembly.py tests\test_target_extraction.py tests\test_csv_writers.py tests\test_peak_candidate_table.py tests\test_peak_candidate_boundaries.py tests\test_peak_candidate_audit.py tests\test_handoff_phase_closeout_contract.py -q
```

- Run static / artifact checks:

```powershell
$repo = (Resolve-Path .).Path
git -c safe.directory="$repo" diff --check
rg -n "phase closeout|handoff_productization_phase_closed|legacy retirement" docs\superpowers\notes\2026-05-27-handoff-productization-c0-source-of-truth.md docs\superpowers\notes\2026-05-21-lcms-msms-handoff-progress-checklist.md
python -c "from pathlib import Path; paths=[Path('docs/superpowers/specs/2026-05-28-handoff-productization-phase-closeout-spec.md'), Path('docs/superpowers/plans/2026-05-28-handoff-productization-phase-closeout-goal.md'), Path('docs/superpowers/notes/2026-05-28-handoff-productization-phase-closeout.md')]; bad=[str(p) for p in paths if p.exists() and sum(1 for line in p.read_text(encoding='utf-8').splitlines() if line.startswith(chr(96)*3)) % 2]; raise SystemExit('Unbalanced markdown fences: '+', '.join(bad) if bad else 0)"
codegraph status
git -c safe.directory="$repo" status --short --branch
```

- Inspect the final closeout note for overclaims, stale source-of-truth wording,
  missing retirement blockers, and next-step ambiguity.
- Treat `tests\test_handoff_phase_closeout_contract.py` as the mechanical gate
  for overclaim wording, matrix completeness, exactly-one next PR target,
  source-of-truth links, and selected-handoff call surface.
- If verification cannot run, stop and report the exact missing dependency or
  failing command.

OUTPUT:
- Changed files
- Legacy retirement verdict by label
- Key product decisions and non-decisions
- Recommended next PR direction, or `no_go` blocker
- Verification commands and results
- Remaining risk

STOP RULES:
- Stop on secrets, production credentials, destructive data operations,
  production data mutation, or unclear product decisions.
- Stop if any required retirement decision cannot be supported by current code,
  docs, tests, or CodeGraph evidence.
- Stop if the work expands into `alignment_matrix.tsv` migration, resolver,
  scoring, baseline, CWT, ASLS, NL, diagnostics, or matrix behavior changes.
- Stop if 8RAW / 85RAW appears necessary to justify the closeout; revise scope
  instead.
- Stop after three failed attempts on the same symptom and revisit the
  root-cause hypothesis.
- Do not mark complete until the current state has been checked against
  `DONE WHEN`.
