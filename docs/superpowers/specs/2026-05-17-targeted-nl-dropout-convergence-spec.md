# Targeted NL Dropout Convergence Spec

## Problem

Targeted reliability audit originally used only workbook-level `XIC Results`
and optional `Score Breakdown` evidence. On 85RAW outputs, some visible,
reasonable selected peaks were classified as `targeted_review` with
`hard_nl_conflict` because the workbook row had `NL_FAIL` / `VERY_LOW` and no
score-breakdown details.

The peak-candidate table already contains lower-level evidence for these
cases: selected candidate, coherent MS1 trace, CWT/local-minimum support,
present MS2, and failed NL. That evidence should be enough to identify a
plausible NL dropout review case without pretending the targeted hit is clean.

## Contract

`tools/diagnostics/targeted_peak_reliability_audit.py` may optionally consume
`peak_candidates.tsv` through `--peak-candidates-tsv`.

When the optional TSV is provided:

- selected candidate evidence is joined by `(sample_name, target_label)`;
- exactly one selected candidate is required for candidate-based enrichment;
- selected candidate evidence can turn workbook-only `NL_FAIL` from
  `hard_nl_conflict` into `plausible_nl_dropout`;
- `plausible_nl_dropout` rows classify as `targeted_review_positive`, not
  `benchmark_eligible`;
- hard candidate conflicts such as `shape_poor`, quality flags, missing MS2,
  or other hard local quality labels must keep the row as `targeted_review`;
- targeted-side blockers such as `weak_area_rank`, `quality_flags`, `no_ms2`,
  or `hard_nl_conflict` remain valid reasons to keep a candidate-supported
  dropout row as `targeted_review`;
- `weak_area_rank` must be explainable from exported numeric context, not only
  a label. Reliability rows append `target_area_median`,
  `area_to_target_median_ratio`, and `weak_area_threshold_ratio`;
- diagnostic messages for candidate-aligned `NL_FAIL` rows should expose the
  product-probe subcause and nearest product context when available, so review
  does not stop at a generic "NL not detected" message;
- missing or malformed optional candidate TSV fails clearly.

When the optional TSV is absent, workbook-only behavior remains unchanged.

## Non-goals

- Do not change targeted extraction, peak selection, integration, or scoring.
- Do not change strict ISTD benchmark denominator semantics:
  `benchmark_eligible` remains the only clean coverage denominator state.
- Do not use targeted labels inside untargeted production identity logic.
- Do not treat NL dropout as a clean positive.
- Do not special-case individual targets.

## Validation

Required tests:

- workbook-only `NL_FAIL` remains `targeted_review` / `hard_nl_conflict`;
- candidate-supported NL dropout becomes `targeted_review_positive`;
- candidate hard conflict remains `targeted_review`;
- missing candidate TSV columns fail clearly;
- targeted ISTD benchmark still excludes review-positive rows from clean
  coverage denominator.

Real-data smoke:

- rerun targeted reliability audit on current 85RAW targeted workbook with
  `--peak-candidates-tsv`;
- rerun cross-report consistency;
- expected improvement: previous
  `targeted_review_candidate_suggests_dropout` rows should collapse if their
  selected candidate evidence is `plausible_nl_dropout`;
- candidate-supported dropout rows with targeted-side blockers such as
  `weak_area_rank` should be treated as consistent `targeted_review`, not as
  upgrade mismatches;
- cross-report consistency rows should pass through
  `targeted_area_to_median_ratio` when the reliability rows provide it, so weak
  area blockers can be reviewed without reopening the workbook;
- any remaining mismatch should be reviewed as evidence disagreement, not
  silently forced into review-positive.

Observed smoke on the 2026-05-17 product-probe rerun:

- 8RAW cross-report consistency: `384 / 384` consistent, `0` mismatch.
- 85RAW cross-report consistency: `4080 / 4080` consistent, `0` mismatch.
