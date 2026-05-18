# Region-first Safe Merge Validation Decision

Date: 2026-05-18

Branch: `codex/region-first-safe-merge-validation`

Decision: `keep_opt_in`

## Scope

This validation only evaluates whether opt-in `region_first_safe_merge` should
remain available and whether it is safe to advance toward broader use.

The validation did not change:

- default resolver behavior
- `XIC Results` schema
- workbook schema
- targeted reliability state rules
- untargeted final matrix identity contract

## 8RAW Targeted Verdict

Verdict: pass for targeted opt-in validation.

Artifacts:

- Default targeted output:
  `output/validation_harness/region_safe_merge_v1_8raw/tissue_8raw_local_minimum/`
- Safe-merge targeted output:
  `output/validation_harness/region_safe_merge_v1_8raw/tissue_8raw_region_first_safe_merge/`
- Comparison:
  `output/diagnostics/region_safe_merge_v1_8raw/region_first_safe_merge_comparison.tsv`
- Reliability default:
  `output/diagnostics/region_safe_merge_v1_8raw/targeted_reliability_local_minimum/`
- Reliability safe:
  `output/diagnostics/region_safe_merge_v1_8raw/targeted_reliability_region_first_safe_merge/`

Observed:

- Compared rows: 112
- Changed rows: 10
- Changed ISTD rows: 7
- Max absolute RT delta: 0.00000 min
- Area ratio range: 1.00772 to 1.16560
- All changed rows persisted `adjacent_wis_local_minimum_merge` as the
  promotion source.
- Targeted reliability summary was unchanged between default and safe.

`d3-N6-medA` reproduced a local-minimum under-integration case in targeted
output. Safe merge increased the selected area from `335942538.22` to
`359486573.78` while preserving selected RT and NL state. It should be treated
as improved area integration evidence, not as proof that every targeted
reliability edge case is fully solved.

## 85RAW Targeted Verdict

Verdict: pass for targeted opt-in validation.

Artifacts:

- Default targeted output:
  `output/validation_harness/region_safe_merge_v1_85raw/tissue_85raw_local_minimum/`
- Safe-merge targeted output:
  `output/validation_harness/region_safe_merge_v1_85raw/tissue_85raw_region_first_safe_merge/`
- Comparison:
  `output/diagnostics/region_safe_merge_v1_85raw/region_first_safe_merge_comparison.tsv`
- Reliability default:
  `output/diagnostics/region_safe_merge_v1_85raw/targeted_reliability_local_minimum/`
- Reliability safe:
  `output/diagnostics/region_safe_merge_v1_85raw/targeted_reliability_region_first_safe_merge/`

Observed:

- Compared rows: 1190
- Changed rows: 107
- Changed ISTD rows: 77
- Max absolute RT delta: 0.00000 min
- Area ratio range: 1.00084 to 1.18883
- All changed rows persisted `adjacent_wis_local_minimum_merge` as the
  promotion source.
- Targeted reliability summary was unchanged between default and safe.
- `5-medC` was not changed.
- `5-hmdC` had changed area rows, but no detection or reliability regression.
- Low-detection target changes were recorded only as observations, not success
  criteria.

## Untargeted Audit Bridge Verdict

Verdict: fail for production alignment use.

Artifacts:

- Discovery index:
  `output/discovery/region_safe_merge_v1_8raw_dR/discovery_batch_index.csv`
- Default alignment:
  `output/alignment/region_safe_merge_v1_8raw_local_minimum/`
- Safe-merge alignment:
  `output/alignment/region_safe_merge_v1_8raw_region_first_safe_merge/`
- Default ISTD benchmark:
  `output/diagnostics/region_safe_merge_v1_8raw/untargeted_istd_benchmark_local_minimum/`
- Safe ISTD benchmark:
  `output/diagnostics/region_safe_merge_v1_8raw/untargeted_istd_benchmark_region_first_safe_merge/`

Observed:

- `alignment_cells.tsv` includes region audit context columns, including
  selected proposal sources, selected merge note, shadow status, shadow verdict,
  merge suggestion source, area ratio, selected interval count, local mixture
  diagnostic, and review reason.
- Default matrix row count: 272.
- Safe-merge matrix row count: 270.
- Default identity summary:
  - `production_family, TRUE`: 272
  - `provisional_discovery, FALSE`: 289
  - `audit_family, FALSE`: 1739
- Safe identity summary:
  - `production_family, TRUE`: 270
  - `provisional_discovery, FALSE`: 291
  - `audit_family, FALSE`: 1736
- Strict ISTD benchmark changed from default `WARN` overall to safe `FAIL`
  overall.
- Safe alignment introduced `15N5-8-oxodG` `AREA_MISMATCH` in the strict ISTD
  benchmark.

This means the audit bridge did not preserve final matrix identity/gate. The
resolver mode cannot be applied directly to untargeted alignment production
logic in this form.

## Final Decision

`region_first_safe_merge` should stay as an opt-in targeted resolver.

It is not a default candidate yet, and it should not be used as an untargeted
alignment production resolver. The next safe direction is to keep untargeted
integration on the current production resolver and attach region/candidate/
boundary evidence as audit-only context, or to add a stricter alignment-specific
gate that proves matrix identity and ISTD benchmark stability before promotion.

Real-data outputs were generated for validation only and are not committed.
