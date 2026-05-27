# Handoff Productization MVP Closeout

## Verdict

Status: `handoff_spine_mvp_ready` / `production_candidate`.

This PR keeps the Step2 shared audit spine and adds the first production-facing
consumer: targeted `ExtractionResult` assembly can consume the selected
production-safe `PeakHypothesis` while preserving current output behavior.

This is not `production_ready`. It does not authorize default switches, legacy
retirement, CWT production promotion, ASLS promotion, or matrix value changes.

## Public Contracts

- `peak_candidates.tsv`: header/order unchanged.
- `peak_candidate_boundaries.tsv`: header/order unchanged.
- `alignment_matrix.tsv`: remains the downstream correction/statistics delivery
  surface and is not changed by this PR.
- CLI flags, config keys, workbook schemas, resolver defaults, and baseline
  defaults are unchanged.

## Runtime Change

- Audit projection builds one shared audit hypothesis tuple and projects both
  candidate and boundary audit rows from it.
- Production result assembly builds a separate production-safe hypothesis tuple
  from the original production `PeakDetectionResult`.
- Production assembly uses the selected hypothesis as an internal handoff
  contract, without using CWT audit-only proposals.
- Final `PeakDetectionResult` confidence/reason remains authoritative when
  candidate-level score summaries are stale after post-selection downgrades.

## Verification

Focused tests:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_peak_hypotheses.py tests\test_handoff_spine_runtime.py tests\test_peak_candidate_table.py tests\test_peak_candidate_boundaries.py tests\test_peak_candidate_audit.py tests\test_result_assembly.py tests\test_target_extraction.py tests\test_csv_writers.py tests\test_messages.py -q
```

Result: `55 passed in 2.16s`.

Compile:

```powershell
python -m py_compile xic_extractor\extraction\peak_candidate_audit.py xic_extractor\extraction\peak_candidate_table.py xic_extractor\extraction\peak_candidate_boundaries.py xic_extractor\extraction\handoff_spine_runtime.py xic_extractor\extraction\result_assembly.py xic_extractor\extraction\target_extraction.py xic_extractor\peak_detection\hypotheses.py
```

Result: passed.

Ruff:

```powershell
uv run ruff check xic_extractor\extraction\peak_candidate_audit.py xic_extractor\extraction\peak_candidate_table.py xic_extractor\extraction\peak_candidate_boundaries.py xic_extractor\extraction\handoff_spine_runtime.py xic_extractor\extraction\result_assembly.py xic_extractor\extraction\target_extraction.py xic_extractor\peak_detection\hypotheses.py tests\test_peak_candidate_audit.py tests\test_peak_candidate_boundaries.py tests\test_handoff_spine_runtime.py tests\test_result_assembly.py tests\test_target_extraction.py
```

Result: `All checks passed!`.

Diff check:

```powershell
git diff --check
```

Result: passed.

Architecture drift check:

```powershell
rg -n "add_cwt_proposals_for_audit|peak_candidate_table|peak_candidate_boundaries|peak_candidate_audit" xic_extractor\extraction\result_assembly.py xic_extractor\extraction\handoff_spine_runtime.py xic_extractor\extraction\target_extraction.py
```

Result: only `target_extraction.py` imports `append_peak_audit_rows`; the
production helper and result assembly have no audit writer / CWT proposal
dependency.

## Post-Implementation Review

- Product-facing handoff behavior advanced: `ExtractionResult` assembly now has
  a selected-hypothesis consumer instead of only audit TSV projections.
- Output parity remains the guardrail: tests cover legacy parity, `HIGH`
  fallback, and stale candidate-score protection.
- Production code does not import TSV writer modules or CWT audit-only proposal
  logic.
- No resolver selection, scoring weight, baseline default, NL matching,
  diagnostic semantics, matrix writer, public TSV header, CLI flag, config key,
  or workbook schema was intentionally changed.

## Next Decision

The next handoff productization decision is whether selected peak/integration
behavior should be natively represented by the spine, or whether downstream
matrix handoff should consume a spine-derived contract. It should not be another
audit-only report unless it closes a specific production decision.
