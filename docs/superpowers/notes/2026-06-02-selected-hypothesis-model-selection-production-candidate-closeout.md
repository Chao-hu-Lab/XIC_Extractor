# Selected-Hypothesis Model Selection Production-Candidate Closeout

**Spec:** `docs/superpowers/specs/2026-06-02-selected-hypothesis-model-selection-parity-spec.md`
**Plan:** `docs/superpowers/plans/2026-06-02-selected-hypothesis-model-selection-parity-implementation-plan.md`
**Status:** `production_candidate`

## Verdict

The selected-hypothesis model-selection gate now exists as an internal
machine-readable audit and switch surface. It is wired through the targeted
handoff path, carried on `ExtractionResult` as an optional audit fact, and can
consume explicit expected-diff approval records from the extraction runtime.

This is not `production_ready`, and it does not retire legacy peak scoring. The
successor selector now chooses over `PeakHypothesis` evidence when no explicit
successor id is provided. Product switching remains blocked for unapproved
mismatches; the runtime falls back to the legacy-selected hypothesis unless the
model-selection result is parity-clean or matched to an approved expected-diff
record.

## Closed In This Slice

- Phase 1 characterization map exists and names required fixture families.
- `PeakModelSelectionResult` records `parity`, `expected_diff`, `blocked_diff`,
  or `inconclusive`.
- `ExpectedDiffApprovalRecord` exists and gates expected diffs.
- `blocked_diff` and `inconclusive` always prevent product switching.
- Forced `parity` mismatch records diff reasons and prevents product switching.
- Matrix-affecting expected diffs require assessed impact and stronger evidence
  than synthetic-only fixtures.
- MS2/NL-driven expected diffs are `inconclusive` under
  `limited_evidence_shadow`.
- `public_projection` includes `confidence`, `reason`, and compatibility labels.
- `model_selection_result` is carried through target extraction to
  `ExtractionResult`.
- Successor-vs-legacy mismatches are observable in the product path, but
  unapproved mismatches fall back to the legacy-selected hypothesis.
- Optional expected-diff approval records pass through `extractor.run`,
  pipeline, serial backend, process jobs, per-file extraction, target
  extraction, and handoff runtime.
- Approval records are applied only when stable row id, sample, target, legacy
  candidate id, and successor candidate id all match the current model-selection
  result.
- Expected-diff approval records cannot under-declare actual public-output
  impact. The gate derives selected marker, selected RT, area, boundary,
  confidence, reason, and matrix-value impact from the legacy-vs-successor
  hypotheses before allowing product switch.
- Candidate table and boundary audit selected markers are projected from the
  product-selected hypothesis when an approved expected diff switches
  selection, including CWT audit merges that change the audit candidate id by
  adding `centwave_cwt` proposal source evidence.
- Durable expected-diff approval registry ingestion exists as a TSV projection
  of `ExpectedDiffApprovalRecord`. It rejects duplicate, incomplete,
  non-approved, unvalidated, missing-file, and matrix-affecting synthetic-only
  rows before runtime use.
- Product entry points can now consume the registry through settings key
  `model_selection_expected_diff_approval_registry` or CLI override
  `--model-selection-expected-diff-approvals`.
- The `target_extraction.py` module boundary guard now checks semantic
  delegation to diagnostics, handoff runtime, audit rows, and result assembly
  instead of a fixed line-count ceiling.

## Still Open

- No real matrix-affecting expected-diff approval records were added in this
  slice. A concrete row still needs targeted benchmark, 8RAW, or manual EIC/MS2
  evidence before it can be added to the durable registry.
- Legacy `score_candidate(...)` and `select_candidate_with_confidence(...)`
  remain the current oracle and must not be deleted in this slice.

## Reviewer Outcome

Read-only reviewer passes were completed after implementation:

- `strategy-challenger`: no blocker for `shadow_ready`; blocks product switch,
  `production_ready`, and scorer retirement claims.
- `implementation-contract-reviewer`: no blocker after re-check; confirms public
  projection, parity mismatch, matrix expected-diff, MS2/NL limited evidence, and
  target product-path audit fixes.
- follow-up approval-gate review: found blockers for under-declared
  matrix-affecting diffs, candidate table selected-marker drift, and weak stable
  row binding. These are closed by derived impact checks, product-selected audit
  marker projection, and computed stable row ids tied to the current
  legacy/successor candidate pair.
- xhigh re-review: confirmed impact derivation and stable row binding, then
  found a remaining selected-marker blocker where CWT audit merging could change
  a hypothesis id after product selection. This is closed by exact-id-first
  marker projection with a unique peak-fingerprint fallback, plus candidate TSV
  and boundary TSV regression coverage.
- final xhigh re-review: no remaining P1 blocker for CWT audit id-change marker
  projection. The reviewer confirmed exact-id-first matching, unique fallback,
  target-to-audit pass-through, and candidate/boundary TSV synchronization.

## Verification

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_peak_scoring.py tests/test_peak_scoring_selection.py tests/test_peak_scoring_evidence.py tests/test_scoring_context.py tests/test_peak_hypotheses.py tests/test_evidence_semantics.py tests/test_peak_selection_decision.py tests/test_result_assembly.py tests/test_target_extraction.py tests/test_handoff_spine_runtime.py tests/test_peak_model_selection.py tests/test_peak_candidate_table.py tests/test_peak_candidate_score_calibration_report.py tests/test_csv_writers.py tests/test_csv_to_excel.py tests/test_excel_pipeline.py tests/test_excel_sheets_contract.py tests/test_signal_processing_selection.py
```

Result before approval pass-through hardening: `278 passed, 2 warnings`.

After adding expected-diff approval pass-through:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_peak_model_selection.py tests/test_handoff_spine_runtime.py tests/test_target_extraction.py tests/test_extractor_run.py tests/test_parallel_execution.py
```

Result before reviewer blocker fixes: `46 passed`.

After approval-gate hardening, CWT audit id-change marker projection, and
semantic module-boundary guard update:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_peak_scoring.py tests/test_peak_scoring_selection.py tests/test_peak_scoring_evidence.py tests/test_scoring_context.py tests/test_peak_hypotheses.py tests/test_evidence_semantics.py tests/test_peak_selection_decision.py tests/test_result_assembly.py tests/test_target_extraction.py tests/test_handoff_spine_runtime.py tests/test_peak_model_selection.py tests/test_peak_candidate_table.py tests/test_peak_candidate_audit.py tests/test_peak_candidate_boundaries.py tests/test_peak_candidate_score_calibration_report.py tests/test_csv_writers.py tests/test_csv_to_excel.py tests/test_excel_pipeline.py tests/test_excel_sheets_contract.py tests/test_signal_processing_selection.py tests/test_extractor_run.py tests/test_parallel_execution.py tests/test_extraction_module_boundaries.py
```

Result: `331 passed, 2 warnings`.

Full no-RAW test suite was also rerun after the expected-diff gate hardening:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x
```

Result after final durable-registry and CLI guard fixes:
`2865 passed, 1 skipped, 16 warnings`.

After durable approval-registry ingestion:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_model_selection_approval_registry.py tests/test_settings_new_fields.py tests/test_config.py tests/test_config_hash.py tests/test_run_extraction.py tests/test_validation_harness.py tests/test_extractor_run.py tests/test_parallel_execution.py tests/test_peak_model_selection.py tests/test_handoff_spine_runtime.py
```

Result: `170 passed`.

After adding the missing-file guard for durable approval registry ingestion:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_model_selection_approval_registry.py tests/test_settings_new_fields.py tests/test_run_extraction.py
```

Result: `26 passed`.

Real-data smoke:

```powershell
.venv\Scripts\python.exe scripts\validation_harness.py --suite tissue-8raw --run-id model_selection_registry_default_smoke --output-root output\model_selection_registry_validation
```

Result: `tissue-8raw` passed with `raw_count=8`,
`compare=not_requested`, output workbook
`output\model_selection_registry_validation\model_selection_registry_default_smoke\tissue_8raw_region_first_safe_merge\xic_results_process_w4.xlsx`.

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
git diff --check
```

Result: all passed. `git diff --check` reported CRLF normalization warnings
only.
