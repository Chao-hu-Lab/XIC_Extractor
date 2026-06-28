# Task 2 Report: Remove superfamily concept from discovery

## Implementation summary

- Removed discovery superfamily fields from `DiscoveryCandidate` and from
  `DISCOVERY_CANDIDATE_REVIEW_COLUMNS` / `DISCOVERY_CANDIDATE_COLUMNS`.
- Removed `family_context` from `DiscoveryCandidate`,
  `DISCOVERY_BRIEF_COLUMNS`, and discovery review notes.
- Simplified `assign_feature_families(...)` to strict family assignment followed
  by `_score_all_evidence(...)`.
- Removed superfamily grouping helpers and superfamily evidence-score weights.
- Updated `alignment/csv_io.py` so discovery candidate parsing no longer
  requires removed superfamily or `family_context` columns.
- Updated focused discovery tests and direct CSV/schema fixtures that failed
  because the public discovery candidate schema changed.

## Changed files

- `xic_extractor/discovery/feature_family.py`
- `xic_extractor/discovery/models.py`
- `xic_extractor/discovery/evidence_score.py`
- `xic_extractor/discovery/evidence_config.py`
- `xic_extractor/discovery/csv_writer.py`
- `xic_extractor/alignment/csv_io.py`
- `tests/test_discovery_feature_family.py`
- `tests/test_discovery_evidence.py`
- `tests/test_discovery_csv.py`
- `tests/test_discovery_review_csv.py`
- `tests/test_alignment_csv_io.py`
- `tests/alignment_pipeline_helpers.py`
- `tests/test_alignment_compatibility.py`
- `tests/test_alignment_identity_coherence_adapter.py`
- `tests/test_alignment_models.py`
- `tests/test_shared_peak_identity_candidate_ms2_pattern.py`
- `.superpowers/sdd/task-2-report.md`

## Tests and checks

- `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_feature_family.py tests/test_discovery_evidence.py -v`
  - Result: `18 passed in 0.94s`
- `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest --tb=short -q`
  - First attempt: timed out at 120s with no failure shown before timeout.
  - Second attempt: `9 failed, 4492 passed, 3 skipped`; all failures were stale
    removed-column keys in
    `tests/test_shared_peak_identity_candidate_ms2_pattern.py` fixture rows.
  - Final result after fixture update: `4501 passed, 3 skipped in 205.76s`
- `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_shared_peak_identity_candidate_ms2_pattern.py -q`
  - Result: `10 passed in 1.20s`
- `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor/discovery xic_extractor/alignment/csv_io.py tests/test_discovery_feature_family.py tests/test_discovery_evidence.py tests/test_discovery_csv.py tests/test_discovery_review_csv.py tests/test_alignment_csv_io.py tests/alignment_pipeline_helpers.py tests/test_alignment_identity_coherence_adapter.py tests/test_alignment_compatibility.py tests/test_alignment_models.py tests/test_shared_peak_identity_candidate_ms2_pattern.py`
  - Result: `All checks passed!`
- `git diff --check`
  - Result: passed; only line-ending warnings were printed.

## Self-review

- `feature_family_id`, `feature_family_size`, and `evidence_score` remain
  present and are not renamed.
- `alignment/csv_io.py` was updated with the removed fields, as required by the
  global constraints.
- `_complete_link_groups` and alignment grouping logic were not edited.
- Remaining broad `family_context` references are alignment/shared-peak identity
  domain context or diagnostics concepts, not the removed discovery candidate
  `family_context` field.
- No control-plane tier or active product lane is changed by this task. The
  output schema changes are the accepted Task 2 contract diff, so
  `docs/superpowers/plans/2026-06-15-productization-control-plane.md` was not
  updated.
- No branch handoff update was needed. The task-specific durable closeout is
  this report, and no active handoff state was changed.
- No hook/config files were edited, so hook/config smoke checks were not
  applicable beyond confirming no execution-affecting paths changed.

## Remaining concerns

- Validation is synthetic/unit only. No 8RAW, 85RAW, targeted benchmark, or
  manual EIC/MS2 review was run for this schema/scoring cleanup.
- This is intentionally breaking for
  `discovery_candidates.csv` superfamily columns and `discovery_review.csv`
  `family_context`.
