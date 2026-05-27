# Handoff Productization Step 2 - Audit Spine Runtime Contract Closeout

## Verdict

Status: `shadow_ready` / `handoff_spine_runtime_audit_ready`.

The targeted audit runtime now builds one shared `PeakHypothesis` tuple and
projects both `peak_candidates.tsv` and `peak_candidate_boundaries.tsv` from
that tuple. This closes the Step 2 scaffold/runtime gap without changing
production selection, resolver behavior, baseline integration, matrix output,
or frozen TSV schemas.

This is not `production_ready`: it proves the audit projection can consume the
handoff spine at runtime. Production selection still uses the existing path.

## Changed Surface

- `xic_extractor/extraction/peak_candidate_audit.py`
  - Runs CWT audit proposal injection once.
  - Builds one shared audit hypothesis tuple.
  - Projects candidate and boundary audit rows from that tuple.
- `xic_extractor/extraction/peak_candidate_table.py`
  - Adds `build_peak_candidate_audit_hypotheses`.
  - Adds `append_peak_candidate_rows_from_hypotheses`.
  - Keeps the existing `append_peak_candidate_rows` compatibility surface.
- `xic_extractor/extraction/peak_candidate_boundaries.py`
  - Passes trace arrays into hypothesis construction for the legacy builder.
  - Adds `append_peak_candidate_boundary_rows_from_hypotheses`.
  - Keeps the existing `append_peak_candidate_boundary_rows` compatibility
    surface.

## Verification

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -p no:cacheprovider tests\test_peak_hypotheses.py tests\test_peak_candidate_table.py tests\test_peak_candidate_boundaries.py tests\test_peak_candidate_audit.py -q
```

Result: `33 passed`.

```powershell
python -m py_compile xic_extractor\extraction\peak_candidate_audit.py xic_extractor\extraction\peak_candidate_table.py xic_extractor\extraction\peak_candidate_boundaries.py xic_extractor\peak_detection\hypotheses.py
```

Result: passed.

```powershell
uv run ruff check xic_extractor\extraction\peak_candidate_audit.py xic_extractor\extraction\peak_candidate_table.py xic_extractor\extraction\peak_candidate_boundaries.py tests\test_peak_candidate_audit.py tests\test_peak_candidate_boundaries.py
```

Result: `All checks passed!`.

## Review Notes

- TSV headers remain frozen; no emitted column was added or removed.
- Internal `trace_group_id` remains an in-memory spine field and is not emitted.
- CWT source-only boundary rows still keep
  `cwt_audit_filter_reason=legacy_cwt_width_not_real_cwt`.
- The new audit test counts `build_peak_hypotheses` calls and confirms the
  audit appender builds the shared tuple once for both audit row families.

## Next Consumer Target

Next PR should migrate the next narrow consumer behind the same rollback rule:
keep production output unchanged, prove row parity first, then decide whether a
production selection path should consume the spine.
