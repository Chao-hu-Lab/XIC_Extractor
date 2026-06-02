# Selected-Hypothesis Evidence Decision Closeout

**Date:** 2026-06-02
**Branch:** `codex/cleanup-retirement-foundation`
**Behavior label:** production extraction-result projection, output values
preserved
**Readiness:** `production_candidate` for projection; `active_policy_remaining`
for model selection and legacy scorer retirement
**Spec:** [Selected-Hypothesis Evidence Decision Public Behavior Addendum](../specs/2026-06-02-selected-hypothesis-evidence-decision-public-behavior-addendum.md)

## Verdict

This phase does not retire `peak_scoring.py`.

It moves selected-hypothesis evidence-decision projection into the normal
production extraction path:

- `PeakHypothesisSelectionDecision` is defined in the peak-domain layer.
- `selected_handoff_peak(...)` builds the decision from the selected
  `PeakHypothesis`.
- `extract_one_target(...)` passes the decision to result assembly.
- `build_extraction_result(...)` derives public `confidence` and `reason` from
  `selection_decision.projected_confidence` and
  `selection_decision.projected_reason` when a decision exists.
- Existing selected candidate, RT, area, score breakdown, reason text, CSV,
  XLSX, workbook, and candidate-table schemas are preserved.

The legacy scorer and selector remain the current oracle:
`legacy_projection_status=active_policy_remaining` and
`compatibility_oracle=legacy_peak_scoring_current_oracle`.

## Public Diff

Allowed new public Python attribute:

- `ExtractionResult.selection_decision`

No writer schema changes were made:

- no candidate TSV column additions;
- no CSV column additions;
- no XLSX/workbook sheet or column additions;
- no score-breakdown schema changes.

## Reviewer Record

Spec review:

- `strategy-challenger` initially blocked overclaiming full productization while
  legacy scorer remained active. Re-check verdict: PASS after the addendum was
  relabeled as production projection with `active_policy_remaining` exit.
- `implementation-contract-reviewer` initially blocked missing concrete fields
  and decorative-wrapper risk. Re-check verdict: PASS after the addendum
  required concrete fields and public confidence/reason projection through
  `selection_decision`.

Implementation review:

- `implementation-contract-reviewer` verdict: PASS. No blocking contract drift.
  It confirmed peak-domain placement, normal path pass-through, public
  confidence/reason projection through the decision, and writer schema no-drift.

## Verification

Focused C4 shard:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_peak_scoring.py tests/test_peak_scoring_selection.py tests/test_peak_scoring_evidence.py tests/test_scoring_context.py tests/test_peak_hypotheses.py tests/test_evidence_semantics.py tests/test_peak_selection_decision.py tests/test_result_assembly.py tests/test_target_extraction.py tests/test_peak_candidate_table.py tests/test_peak_candidate_score_calibration_report.py tests/test_csv_writers.py tests/test_csv_to_excel.py tests/test_excel_pipeline.py tests/test_excel_sheets_contract.py tests/test_signal_processing_selection.py
```

Result: `259 passed, 2 warnings`.

Lint:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests
```

Result: `All checks passed!`

Typecheck:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```

Result: `Success: no issues found in 267 source files`.

Diff hygiene:

```powershell
git diff --check
```

Result: no whitespace errors; Git reported CRLF conversion warnings only.

## Remaining Risk And Next Artifact

Remaining state: `active_policy_remaining`.

`score_candidate(...)`, `select_candidate_with_confidence(...)`, scorer
severity helpers, raw score, confidence caps, and legacy reason text still own
current active candidate policy and compatibility projection. They are not
future product truth, but they are still the current oracle.

Next required artifact:

- selected-hypothesis model-selection parity spec, if the next goal wants to
  retire scorer selection without expected behavior changes; or
- selected-hypothesis expected-diff behavior spec, if the next goal intentionally
  changes selected rows / confidence / reason semantics; or
- legacy-retirement spec for narrower scorer surfaces after successor parity is
  proven.
