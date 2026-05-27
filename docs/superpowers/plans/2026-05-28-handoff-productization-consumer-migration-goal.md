/goal
GOAL:
Complete one PR on `codex/handoff-productization-consumer-migration` that
migrates targeted CSV row projection to consume a selected-hypothesis-derived
integration view from `ExtractionResult`, while preserving current emitted CSV
schemas and values.

Final status may be `handoff_spine_consumer_migration_ready` /
`production_candidate`. Do not claim `production_ready`.

CONTEXT:
- Repo: `XIC_Extractor`
- Worktree: `.worktrees\handoff-productization-consumer-migration`
- Branch: `codex/handoff-productization-consumer-migration`
- Spec:
  `docs/superpowers/specs/2026-05-28-handoff-productization-consumer-migration-spec.md`
- Source-of-truth note:
  `docs/superpowers/notes/2026-05-27-handoff-productization-c0-source-of-truth.md`
- Prior closeout:
  `docs/superpowers/notes/2026-05-28-handoff-productization-mvp-closeout.md`
- Required repo-local workflow context: `AGENTS.md`,
  `docs/agent-subagent-routing.md`, and `docs/agent-parameter-settings.md`

Read first:
- `xic_extractor/extractor.py`
- `xic_extractor/extraction/handoff_spine_runtime.py`
- `xic_extractor/extraction/result_assembly.py`
- `xic_extractor/extraction/target_extraction.py`
- `xic_extractor/output/csv_writers.py`
- `tests/test_result_assembly.py`
- `tests/test_target_extraction.py`
- `tests/test_csv_writers.py`

Current baseline:
- The previous MVP already builds a production-safe selected `PeakHypothesis`
  and passes it into `build_extraction_result(...)`.
- `ExtractionResult` assembly can consume selected-hypothesis metadata.
- Targeted CSV output row builders still project RT / area / intensity /
  boundary values from legacy `PeakDetectionResult.peak`.

CONSTRAINTS:
- Stay in the consumer-migration worktree and branch.
- Keep scope limited to the reviewed spec and plan; do not add unrelated cleanup
  or convenient refactors.
- Respect repository instructions and existing patterns.
- Preserve verification integrity: do not weaken or bypass tests, assertions,
  lint, typecheck, validation, generated-output checks, or external blockers to
  make the goal pass; fix the root cause or report the blocker.
- Do not change resolver selection, scoring weights, baseline defaults, ASLS
  promotion, CWT production behavior, NL matching, diagnostics semantics,
  output schemas, workbook schemas, CLI flags, config keys, or matrix values.
- Do not touch Phase2 cleanup scope.
- Do not change `alignment_matrix.tsv`; future matrix handoff work requires a
  separate spec.
- Do not let audit-only CWT proposal injection enter production output
  projection.
- Do not silently replace emitted raw `Area` with baseline-corrected area.
- This is code/API consumer migration, not a database or production-data
  migration. `dry-run` is not applicable unless the scope unexpectedly expands
  into data mutation; if it does, stop and write a new data-migration contract.
- Rollback/recovery evidence is git-level revertability plus focused parity
  tests. Integrity evidence is schema/header checks, row counts, and row-value
  parity tests, not a destructive data migration report.

DONE WHEN:
- `ExtractionResult` retains the selected hypothesis or exposes an equivalent
  selected integration view with legacy fallback.
- `build_extraction_result(...)` passes through the selected hypothesis supplied
  by the existing production handoff runtime.
- Targeted CSV row builders use the selected integration view for RT, area,
  intensity, peak start, peak end, and peak width.
- `csv_writers.py` no longer directly reads `result.peak_result.peak` for RT,
  area, intensity, peak start, peak end, or peak width projection; legacy
  fallback is owned by `ExtractionResult` accessors.
- Current wide, long, diagnostics, and score-breakdown CSV schemas remain
  unchanged.
- Focused tests cover selected-integration projection, legacy fallback, existing
  row parity, a CSV-level divergent selected-integration fixture, a
  runtime-selected-hypothesis CSV parity fixture, and no-peak CSV regression.
- A closeout note records that this PR migrated targeted output projection only,
  did not change `alignment_matrix.tsv`, and remains `production_candidate`.
- Post-implementation review includes `implementation-contract-reviewer` for
  the public CSV contract. Docs-handoff or self-review alone does not clear the
  full handoff productization route.
- Worktree has no unrelated dirty files.

VERIFY:
Run focused tests and inspect fresh output from this run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_result_assembly.py tests\test_target_extraction.py tests\test_csv_writers.py tests\test_messages.py tests\test_handoff_spine_runtime.py -q
```

Run static checks and inspect fresh output from this run:

```powershell
python -m py_compile xic_extractor\extractor.py xic_extractor\extraction\result_assembly.py xic_extractor\extraction\target_extraction.py xic_extractor\extraction\handoff_spine_runtime.py xic_extractor\output\csv_writers.py
$env:UV_CACHE_DIR='.uv-cache'
uv run ruff check xic_extractor\extractor.py xic_extractor\extraction\result_assembly.py xic_extractor\extraction\target_extraction.py xic_extractor\extraction\handoff_spine_runtime.py xic_extractor\output\csv_writers.py tests\test_result_assembly.py tests\test_target_extraction.py tests\test_csv_writers.py tests\test_messages.py tests\test_handoff_spine_runtime.py
git diff --check
```

Inspect:
- `git status --short --branch`
- `git diff --stat`
- audit dependency grep from the spec
- `rg -n "peak_result\.peak|result\.peak_result\.peak" xic_extractor\output\csv_writers.py`
- changed docs for accidental overclaim wording such as `production_ready`,
  `85RAW acceptance`, `alignment_matrix.tsv migrated`, or `default switch`

If verification cannot run, stop and report the exact blocker. Do not claim the
goal complete without fresh equivalent evidence.

OUTPUT:
- Changed files
- Key decisions
- Verification commands and results
- Whether public CSV/TSV/matrix schemas changed
- Remaining risk
- Next recommended action

PR description must include:
- why targeted CSV projection is the next consumer migration;
- what changed in runtime/output behavior;
- what explicitly did not change;
- tests/static checks run;
- status language: `handoff_spine_consumer_migration_ready` /
  `production_candidate`.

STOP RULES:
- Stop on secrets, production credentials, destructive data operations,
  production data mutation, or unclear product decisions.
- Stop if preserving parity requires changing resolver selection, baseline
  integration, scoring, NL matching, diagnostics, matrix values, or public
  output schemas.
- Stop if output writers need to rebuild hypotheses or import audit TSV helpers.
- Stop if selected `IntegrationResult` cannot represent current emitted RT /
  area / intensity / boundary values without semantic loss.
- Stop if baseline-corrected area would need to replace current raw emitted
  `Area`.
- Stop if Phase2 cleanup or alignment matrix code becomes necessary.
- Stop after three failed attempts on the same symptom and revisit the
  root-cause hypothesis.
- Do not mark complete until the final state is checked against `DONE WHEN`.
