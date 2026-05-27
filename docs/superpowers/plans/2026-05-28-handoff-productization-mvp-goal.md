# Goal Contract - Handoff Productization MVP

## GOAL

Complete one PR on `codex/handoff-productization-mvp` that integrates Step2,
Step3, and the Step4 contract note: the targeted runtime must build and reuse a
shared handoff hypothesis spine for audit projections, and production
`ExtractionResult` assembly must be able to consume the selected production-safe
`PeakHypothesis` while preserving current output behavior.

Final status may be `handoff_spine_mvp_ready` / `production_candidate`. Do not
claim `production_ready`.

## CONTEXT

- Repo: `XIC_Extractor`
- Worktree: `.worktrees\handoff-productization-step2`
- Branch: `codex/handoff-productization-mvp`
- Spec:
  `docs/superpowers/specs/2026-05-28-handoff-productization-mvp-step2-step4-spec.md`
- Source of truth:
  `docs/superpowers/notes/2026-05-27-handoff-productization-c0-source-of-truth.md`
- Existing Step2 commits:
  - `27acadb docs: define handoff audit spine step2`
  - `7691511 feat: share audit peak hypothesis spine`

Read first:

- `xic_extractor/peak_detection/hypotheses.py`
- `xic_extractor/extraction/peak_candidate_audit.py`
- `xic_extractor/extraction/peak_candidate_table.py`
- `xic_extractor/extraction/peak_candidate_boundaries.py`
- `xic_extractor/extraction/result_assembly.py`
- `xic_extractor/extraction/target_extraction.py`
- `tests/test_peak_hypotheses.py`
- `tests/test_peak_candidate_audit.py`
- `tests/test_peak_candidate_table.py`
- `tests/test_peak_candidate_boundaries.py`
- `tests/test_target_extraction.py`

Current baseline:

- Step2 audit appender already builds one shared audit hypothesis tuple.
- Candidate and boundary audit row projections already consume that tuple.
- Production `ExtractionResult` assembly still reads legacy models directly.

## CONSTRAINTS

- Stay in the handoff MVP worktree and branch.
- Do not touch Phase2 cleanup files or continue cleanup scope.
- Do not change resolver selection, resolver defaults, scoring weights,
  baseline defaults, ASLS promotion, CWT production behavior, NL matching,
  diagnostics semantics, or matrix values.
- Do not change public TSV headers, workbook schemas, CLI flags, config keys, or
  `alignment_matrix.tsv` schema.
- Production selected-hypothesis helpers must live in a neutral extraction /
  runtime module. Production result assembly must not import TSV writer modules:
  `peak_candidate_table.py`, `peak_candidate_boundaries.py`, or
  `peak_candidate_audit.py`.
- Audit-only CWT proposal injection must not enter production
  `ExtractionResult` assembly.
- Production assembly must reuse selected/cached MS2 evidence and must not force
  MS2 evidence generation for every candidate.
- Preserve current fallbacks, including `ExtractionResult.confidence == "HIGH"`
  when a peak exists but no scoring confidence is present.
- Preserve post-selection `PeakDetectionResult` confidence/reason when they
  differ from stale selected-candidate score summaries, such as after paired
  anchor mismatch downgrades.

## DONE WHEN

- Step2 shared audit runtime still works and remains covered by focused tests.
- A neutral production-safe handoff runtime helper exists for building
  hypotheses from the original production `PeakDetectionResult`.
- A selected-hypothesis helper returns the selected `PeakHypothesis` or `None`
  without inventing selection behavior.
- `ExtractionResult` assembly can consume the selected hypothesis and preserves
  parity with the existing `build_extraction_result(...)` behavior.
- Tests cover stale candidate-score protection so selected hypotheses do not
  undo final confidence/reason downgrades already applied to `PeakDetectionResult`.
- `extract_one_target(...)` builds the production-safe selected hypothesis once
  and passes it to result assembly.
- Audit rows still use the audit tuple with CWT proposal injection, separate
  from production assembly.
- A closeout / contract note records:
  - `alignment_matrix.tsv` remains the downstream delivery surface;
  - this PR does not change matrix values or schema;
  - status is `handoff_spine_mvp_ready` / `production_candidate`, not
    `production_ready`;
  - the next decision is native spine-backed selection/integration or matrix
    handoff, not more audit-only reports.
- A post-implementation review checks whether the diff really advances
  product-facing handoff behavior, preserves parity, and avoids writer/audit
  dependencies in production code; any blocker found there is fixed before PR.
- Worktree has no unrelated dirty files.

## VERIFY

Run focused tests:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_peak_hypotheses.py tests\test_handoff_spine_runtime.py tests\test_peak_candidate_table.py tests\test_peak_candidate_boundaries.py tests\test_peak_candidate_audit.py tests\test_result_assembly.py tests\test_target_extraction.py tests\test_csv_writers.py tests\test_messages.py -q
```

Run static checks:

```powershell
python -m py_compile xic_extractor\extraction\peak_candidate_audit.py xic_extractor\extraction\peak_candidate_table.py xic_extractor\extraction\peak_candidate_boundaries.py xic_extractor\extraction\handoff_spine_runtime.py xic_extractor\extraction\result_assembly.py xic_extractor\extraction\target_extraction.py xic_extractor\peak_detection\hypotheses.py
uv run ruff check xic_extractor\extraction\peak_candidate_audit.py xic_extractor\extraction\peak_candidate_table.py xic_extractor\extraction\peak_candidate_boundaries.py xic_extractor\extraction\handoff_spine_runtime.py xic_extractor\extraction\result_assembly.py xic_extractor\extraction\target_extraction.py xic_extractor\peak_detection\hypotheses.py tests\test_peak_candidate_audit.py tests\test_peak_candidate_boundaries.py tests\test_handoff_spine_runtime.py tests\test_result_assembly.py tests\test_target_extraction.py
git diff --check
```

Inspect:

- `git status --short --branch`
- `git diff --stat`
- `rg -n "add_cwt_proposals_for_audit|peak_candidate_table|peak_candidate_boundaries|peak_candidate_audit" xic_extractor\extraction\result_assembly.py xic_extractor\extraction\handoff_spine_runtime.py xic_extractor\extraction\target_extraction.py`
- Changed docs and the final closeout note for accidental overclaim wording:
  `production_ready`, `85RAW acceptance`, `matrix values changed`, or
  `default switch`. Do not scan all historical docs as a pass/fail gate because
  older notes legitimately contain those phrases.

If any verification command cannot run because of environment permissions,
report the exact failing command, rerun with the documented safe escalation if
appropriate, and do not claim the goal complete without fresh equivalent
evidence.

## OUTPUT

Final report must include:

- verdict;
- changed files;
- verification commands and result;
- whether public TSV/matrix schemas changed;
- remaining risk;
- next recommended action.

PR description must include:

- why Step2+Step3+Step4 are one coherent MVP;
- what changed in runtime behavior;
- what explicitly did not change;
- tests/static checks run;
- status language: `handoff_spine_mvp_ready` / `production_candidate`.

## STOP RULES

Stop and ask before continuing if:

- preserving parity requires changing resolver selection, baseline integration,
  NL matching, diagnostics, matrix values, or public output schemas;
- the selected production result cannot be represented by
  `PeakHypothesis` / `EvidenceVector` / `IntegrationResult` / `AuditTrail`
  without adding a semantic field;
- production assembly requires CWT audit-only proposals;
- result assembly needs to generate MS2 evidence for all candidates;
- Phase2 cleanup files become necessary;
- three attempts fail on the same symptom.

Do not mark complete until the final state is checked against `DONE WHEN`.
