# Safe Merge Promotion Provenance Validation

Date: 2026-05-19

Branch: `codex/area-mismatch-production-fix`

Fix commit: `4f4554b fix: persist safe merge promotion provenance`

Decision: `keep_opt_in`

## Scope

This validation checks the corrected provenance path for opt-in
`region_first_safe_merge`.

The fix does not change default extraction, targeted scoring, neutral-loss
logic, targeted reliability state rules, workbook schema, untargeted matrix
identity, or alignment production quantification.

The only public debug schema change is an append-only expansion of
`peak_candidates.tsv` with safe-merge promotion provenance fields.

## Root Cause

The earlier 85RAW comparison report could make `region_first_safe_merge` look as
if it accepted non-adjacent WIS intervals.

The actual gate already enforced the adjacent interval constraint. The report
was mixing evidence from two different times:

- promotion identity from the selected candidate `merge_note`
- interval count and gap from `peak_region_selection_shadow_summary.tsv`

The shadow summary is generated after safe merge has already changed the
selected candidate. It can therefore describe post-promotion region evidence
instead of the pre-promotion gate decision.

The fix persists pre-promotion decision provenance on the promoted
`PeakCandidate` and makes `region_first_safe_merge_comparison.py` prefer those
persisted fields over shadow-summary fallbacks.

## 8RAW Targeted Validation

Artifacts:

- Default targeted output:
  `output/validation_harness/area_mismatch_provenance_8raw_keepcsv/tissue_8raw_local_minimum/`
- Safe-merge targeted output:
  `output/validation_harness/area_mismatch_provenance_8raw_keepcsv/tissue_8raw_region_first_safe_merge/`
- Comparison:
  `output/diagnostics/area_mismatch_provenance_8raw_keepcsv/region_first_safe_merge_comparison.tsv`
- Reliability default:
  `output/diagnostics/area_mismatch_provenance_8raw_keepcsv/targeted_reliability_local_minimum/`
- Reliability safe:
  `output/diagnostics/area_mismatch_provenance_8raw_keepcsv/targeted_reliability_region_first_safe_merge/`

Observed:

- Compared rows: 112
- Changed rows: 10
- Changed ISTD rows: 7
- Max absolute RT delta: `0.00000` min
- Area ratio range: `1.00772` to `1.16560`
- Persisted promotion gap violations: 0
- Area-ratio gate violations above 1.20: 0
- Targeted reliability summary differences: 0
- `d3-N6-medA / NormalBC2312_DNA` area ratio: `1.07008`
- `d3-N6-medA / NormalBC2312_DNA` persisted interval gap: `0.03631`

## 85RAW Targeted Validation

Artifacts:

- Default targeted output:
  `output/validation_harness/area_mismatch_provenance_85raw_keepcsv/tissue_85raw_local_minimum/`
- Safe-merge targeted output:
  `output/validation_harness/area_mismatch_provenance_85raw_keepcsv/tissue_85raw_region_first_safe_merge/`
- Comparison:
  `output/diagnostics/area_mismatch_provenance_85raw_keepcsv/region_first_safe_merge_comparison.tsv`
- Reliability default:
  `output/diagnostics/area_mismatch_provenance_85raw_keepcsv/targeted_reliability_local_minimum/`
- Reliability safe:
  `output/diagnostics/area_mismatch_provenance_85raw_keepcsv/targeted_reliability_region_first_safe_merge/`

Observed:

- Compared rows: 1190
- Changed rows: 107
- Changed ISTD rows: 77
- Max absolute RT delta: `0.00000` min
- Area ratio range: `1.00084` to `1.18883`
- Persisted promotion gap violations: 0
- Area-ratio gate violations above 1.20: 0
- Targeted reliability summary differences: 0
- `15N5-8-oxodG`: 85 / 85 `benchmark_eligible`
- `d3-N6-medA`: 85 / 85 `benchmark_eligible`
- `d3-N6-medA / NormalBC2312_DNA` area ratio: `1.07008`
- `d3-N6-medA / NormalBC2312_DNA` persisted interval gap: `0.03631`
- `5-medC` reliability summary did not regress.
- `5-hmdC` reliability summary did not regress.

## 8RAW Untargeted Audit Bridge

Artifacts:

- Discovery index:
  `output/discovery/area_mismatch_provenance_8raw_dR_region_first_safe_merge/discovery_batch_index.csv`
- Default alignment:
  `output/alignment/area_mismatch_provenance_8raw_local_minimum/`
- Safe-merge alignment mode:
  `output/alignment/area_mismatch_provenance_8raw_region_first_safe_merge/`
- Default ISTD benchmark:
  `output/diagnostics/area_mismatch_provenance_8raw_untargeted_benchmark_local_minimum/`
- Safe ISTD benchmark:
  `output/diagnostics/area_mismatch_provenance_8raw_untargeted_benchmark_region_first_safe_merge/`

Production equivalence:

- `alignment_matrix.tsv`: identical
- `alignment_review.tsv`: identical
- `alignment_cells.tsv`: identical

Hashes:

- `alignment_matrix.tsv`:
  `A3A034FCDC9CC7ACDF95065BE3AF55A1B987798F19430843D4A5077C8F26E461`
- `alignment_review.tsv`:
  `91B28672EF2A97A257C642E67BAF32483950637858C58F2314C2460A88D20B18`
- `alignment_cells.tsv`:
  `AC08D51FCCB4D7B7601D9DBBCCA27DDE82B74D12BA6025CDE3EAA2BB60374C54`

Region audit context:

- Total cells: 18400
- Detected cells: 2961
- Rescued cells: 3326
- Rows with region context: 16966
- Detected rows with region context: 2961
- Rescued rows with region context: 3326

Identity summary:

- `production_family, TRUE`: 272
- `provisional_discovery, FALSE`: 290
- `audit_family, FALSE`: 1738

Strict targeted ISTD benchmark:

- Default alignment: overall `WARN`
- Safe alignment mode: overall `WARN`
- Both runs have matching target statuses.
- `15N5-8-oxodG`: `PASS`
- `d3-N6-medA`: `WARN` with `TARGETED_REVIEW_EVIDENCE`
- No untargeted alignment regression was observed.

## Decision

`region_first_safe_merge` should remain an opt-in targeted resolver.

It is not ready to become the default resolver. The validation supports keeping
the opt-in mode and using persisted provenance for review, but it does not
justify changing targeted scoring, neutral-loss logic, reliability state rules,
untargeted matrix identity, or alignment production quantification.

In untargeted alignment, `region_first_safe_merge` remains audit-only:
production peak picking is coerced to `local_minimum`, while region-first
evidence can be surfaced through `alignment_cells.tsv`.

## Next Work

If this branch opens as a PR, reviewers should focus on:

- append-only `peak_candidates.tsv` schema compatibility
- whether persisted provenance fields are populated only when safe merge
  actually promotes a candidate
- whether comparison diagnostics now read pre-promotion provenance before
  falling back to shadow summaries

Future promotion beyond opt-in would require a separate plan with broader
real-data gates. It should not be bundled into this provenance fix.

