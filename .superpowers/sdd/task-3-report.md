# Task 3 Report: Rename discovery family to peak anchor

## Implementation Summary

- Renamed `xic_extractor/discovery/feature_family.py` to
  `xic_extractor/discovery/peak_anchor.py` with `git mv`.
- Renamed the public discovery assignment function from
  `assign_feature_families` to `assign_peak_anchors`.
- Renamed internal helpers from strict-family wording to peak-anchor wording:
  `_assign_peak_anchors`, `_matching_anchor_index`, `_same_peak_anchor`,
  `_anchor_ids`, `_group_sort_key`, and `_group_identity_key`.
- Updated discovery pipeline imports, calls, and timing stage name to
  `discover.peak_anchor`.
- Renamed `tests/test_discovery_feature_family.py` to
  `tests/test_discovery_peak_anchor.py` and updated test function names/calls.
- Updated the direct timing-stage assertion in `tests/test_discovery_pipeline.py`
  because the brief explicitly changed the pipeline stage name.

## Contract Preservation

- `DiscoveryCandidate.feature_family_id` remains the sole dataclass field name.
- `DiscoveryCandidate.feature_family_size` remains unchanged.
- No `peak_anchor_id` property or alias was added.
- Output column names remain `feature_family_id` and `public_family_id`.
- ID format remains `@F{index:04d}`.
- No compatibility facade/import for `xic_extractor.discovery.feature_family`
  was added.
- This is structural rename only; no grouping, scoring, schema, or output-value
  behavior was intentionally changed.

## Tests and Checks

- PASS: `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_peak_anchor.py -v`
  - Result: 5 passed.
- PASS: `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_pipeline.py::test_single_raw_pipeline_records_discovery_timing_stages -q`
  - Result: 1 passed.
- PASS: `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest --tb=short -q`
  - Result: 4501 passed, 3 skipped.
- PASS: `rg -n "assign_feature_families|discovery\.feature_family|test_discovery_feature_family" xic_extractor tests docs`
  - Remaining hits are docs-only historical plan/spec text under
    `docs/superpowers/`; no `xic_extractor` or `tests` hits remain.
- PASS: `git diff --cached --check`
  - Result: no whitespace errors.
- PASS: staged-diff secret/local-path scan with strict key/local path patterns.
  - Result: no hits.
- PASS: `python .codex/hooks/fixtures/assert_hook_outputs.py`
  - Result: hook fixture smoke passed.
- PASS: `python -m scripts.agent_sandbox_doctor --command "git status --short"`
  - Result: `Sandbox doctor status: ok`.

## Self-Review

- Checked that the rename did not add `peak_anchor_id`.
- Checked that pipeline production import now uses
  `xic_extractor.discovery.peak_anchor`.
- Checked that the old `assign_feature_families` production/test references are
  gone.
- The only test expectation adjusted outside the renamed test file was the
  discovery timing stage assertion, directly required by the brief.

## Concerns

- No compatibility import remains by design. Any downstream import of
  `xic_extractor.discovery.feature_family` will now fail, which matches the Task
  3 plan.
- Validation tier: synthetic/no-RAW test suite only. This task intentionally did
  not run RAW-backed validation because behavior and output schema were not
  changed.
