# Task 4 Report: Clarify Alignment Identity Semantics

## Implementation Summary

- Added module and class docstrings clarifying that alignment "family" means a
  cross-sample chemical-entity group/display label, not discovery's per-sample
  peak anchor.
- Documented `group_hypothesis_id` as the identity key for alignment pipeline
  decisions.
- Documented `public_family_id` and legacy `feature_family_id` as output
  compatibility/display labels.
- Updated `docs/product/family-hypothesis-boundary.md` to use `peak_anchor_id`,
  cross-sample group, `group_hypothesis_id`, and `PeakHypothesis` terminology.

## Changed Files

- `xic_extractor/alignment/cross_sample_peak_groups.py`
- `xic_extractor/alignment/owner_clustering.py`
- `xic_extractor/alignment/family_compatibility.py`
- `xic_extractor/alignment/owner_family_successor_contract.py`
- `docs/product/family-hypothesis-boundary.md`
- `.superpowers/sdd/task-4-report.md`

## Behavior / Contract Change

- Behavior changed: no.
- Algorithms changed: no.
- Imports changed: no.
- Dataclass fields changed: no.
- Public output names changed: no. `feature_family_id` and `public_family_id`
  remain preserved output/display surfaces.
- Public contract clarification: yes. Alignment identity decisions should use
  `group_hypothesis_id`; alignment `public_family_id` and legacy
  `feature_family_id` are display labels.

## Tests / Results

- `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_family_compatibility.py tests/test_alignment_owner_family_successor_contract.py -v`
  - Result: passed, 21 tests in 1.17s.
- `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest --tb=short -q`
  - First run timed out at 120s with no failures shown through about 63%.
  - Rerun with longer timeout passed: 4501 passed, 3 skipped in 178.35s.
- `git diff --check`
  - Result: passed. Git reported expected CRLF normalization warnings only.
- Secret/local-path scan over changed source/docs/report files
  - Initial broad scan matched this report's checklist wording only.
  - Follow-up precise scan result: passed, no matches.

## Self-Review

- Verified the change is docs/docstrings-only within the assigned write scope.
- Did not touch discovery code, alignment grouping logic, output schemas, tests,
  imports, or dataclass fields.
- Kept legacy names where they are public contracts while clarifying their
  identity semantics.

## Concerns

- Validation status is `synthetic_only` once the requested pytest commands pass;
  no RAW-backed validation is relevant because this task changes no runtime
  behavior.
- No productization control-plane tier update is needed: this is a docs/docstring
  semantic clarification and does not change maturity tier, active lane,
  output schema, review/replay behavior, selected area/counting, or matrix
  authority.
- No branch handoff update is needed within this implementer slice: the assigned
  write scope provides this task report as the Task 4 handoff artifact, and the
  active branch handoff is outside the allowed write scope.
