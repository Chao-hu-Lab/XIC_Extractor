# Handoff Productization Consumer Migration Closeout

## Verdict

Status: `handoff_spine_consumer_migration_ready` / `production_candidate`.

The targeted CSV projection now reads the selected-hypothesis integration
projection through `ExtractionResult` accessors. This is a consumer migration
only: it preserves the public CSV schemas and legacy selected-hypothesis values,
and it does not change resolver, scoring, baseline, CWT, NL, workbook, CLI, or
alignment-matrix behavior.

## Public Contracts

- `xic_results.csv` and `xic_results_long.csv` keep their existing headers and
  formatting.
- Legacy runtime-selected hypotheses keep byte-equivalent row values in the
  focused row-builder tests.
- Divergent selected integration values are projected from
  `PeakHypothesis.integration` through `ExtractionResult`.
- Selected integration `PeakWidth` preserves the existing non-negative width
  contract by projecting `abs(IntegrationResult.rt_width_min)`.
- No-peak rows remain `ND`, including a malformed defensive case where a
  candidate exists without a legacy peak.
- Numeric MS1 fields use all-or-ND peak detection: if a future projection lacks
  any required peak metric, the writer emits the established `ND` row rather
  than partial numeric columns.
- Score-breakdown `Detection Counted` remains legacy detection logic by design;
  this PR migrates wide/long CSV numeric projection only.

## Verification

- `$env:PYTHONDONTWRITEBYTECODE='1'; python -m pytest -p no:cacheprovider tests\test_result_assembly.py tests\test_target_extraction.py tests\test_csv_writers.py tests\test_messages.py tests\test_handoff_spine_runtime.py -q`
  - `28 passed in 1.73s`
- `$env:PYTHONDONTWRITEBYTECODE='1'; python -c "import typing; from xic_extractor.extractor import ExtractionResult; print(typing.get_type_hints(ExtractionResult)['selected_hypothesis'])"`
  - resolved to `xic_extractor.peak_detection.hypotheses.PeakHypothesis | None`
- `python -m py_compile xic_extractor\extractor.py xic_extractor\extraction\result_assembly.py xic_extractor\extraction\target_extraction.py xic_extractor\extraction\handoff_spine_runtime.py xic_extractor\output\csv_writers.py`
  - passed
- `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor\extractor.py xic_extractor\extraction\result_assembly.py xic_extractor\extraction\target_extraction.py xic_extractor\extraction\handoff_spine_runtime.py xic_extractor\output\csv_writers.py tests\test_result_assembly.py tests\test_target_extraction.py tests\test_csv_writers.py tests\test_messages.py tests\test_handoff_spine_runtime.py`
  - passed without escalation; `.uv-cache/` is ignored
- `git diff --check`
  - passed; Git reported only LF-to-CRLF working-copy warnings
- `rg -n "add_cwt_proposals_for_audit|peak_candidate_table|peak_candidate_boundaries|peak_candidate_audit" xic_extractor\extractor.py xic_extractor\output\csv_writers.py xic_extractor\extraction\result_assembly.py xic_extractor\extraction\handoff_spine_runtime.py`
  - no matches
- `rg -n "peak_result\.peak|result\.peak_result\.peak" xic_extractor\output\csv_writers.py`
  - no matches

## Post-Implementation Review

Self-review found one contract edge case: using `reported_rt` alone as the
writer's "has peak" predicate could change malformed no-peak rows into RT-only
rows. The predicate was tightened to require selected/legacy integration metrics
instead, and the no-peak CSV test now covers the defensive candidate-without-peak
case.

The implementation-contract reviewer found one medium issue: selected
integration width was being recomputed from left/right boundaries instead of
projecting `IntegrationResult.rt_width_min`. A later critical artifact review
tightened this further: the projected width must also preserve the legacy
non-negative width contract. `ExtractionResult.reported_peak_width` now uses
`abs(rt_width_min)` when a selected integration exists, and the result assembly
plus CSV tests intentionally use a negative divergent `rt_width_min` so this
cannot pass by accident.

The critical artifact reviewer also found that public runtime type-hint
introspection was broken for `ExtractionResult`. `PeakHypothesis` and
`IntegrationResult` are now runtime imports, and the focused tests cover
`typing.get_type_hints(ExtractionResult)`.

The DX reviewer found that the implementation plan looked unexecuted, ruff
reproducibility was not clear enough, and reviewer evidence needed a durable
artifact. The plan now has an execution-status banner, ruff uses
`$env:UV_CACHE_DIR='.uv-cache'`, and the review synthesis is recorded in
`docs/superpowers/notes/2026-05-28-handoff-productization-consumer-migration-review-note.md`.

## Next Decision

Future matrix handoff requires a separate parity and behavior spec. This PR does
not migrate `alignment_matrix.tsv` or promote any new production behavior beyond
the targeted CSV consumer path.
