# Backfill Broad Auto-Write Feasibility Gate v1

Status: read-only decision packet.

Decision: `park_broad_backfill`.

This packet does not grant matrix write authority. It does not create a new
sidecar family, writer slice, heuristic threshold family, or ProductWriter
change.

## Decision Meaning

`park_broad_backfill` means:

- keep the current 511 `write_ready` cells and existing negative evidence;
- stop broad Backfill sidecars/diagnostics that only add more profile summaries;
- do not run 85RAW for broad Backfill unless a future product decision names a
  new evidence source that can change this gate;
- do not derive writer predicates from `quality_blockers` or the round-trip
  reintegration oracle.

Broad Backfill may be reopened only with a new independent evidence source for
peak-choice / family identity, not by renaming all-stability, apex-delta,
width-only, shape-margin, or another nested height/scan/shape slice.

## 1. Fact Revalidation

The current candidate universe is 4613 generated-policy / source-audit rows.
It is not 4613 writable cells.

| Claim | Revalidated value |
| --- | --- |
| policy universe | 4613 rows |
| current product authority | 511 `write_ready` cells |
| detected-flagged remainder | 0 rows |
| blocked rows | 4102 rows |
| unresolved trace-matched rows | 3015 rows needing a new approved evidence class or passing oracle |
| missing trace rows | 1087 rows needing trace overlay or reintegration evidence |
| writer acceptance | `pass`, 511 eligible / 511 written |

Artifact hashes:

| Artifact | SHA256 |
| --- | --- |
| `output/productization_realdata_seed_guard_85raw_20260617/generated_policy_quality_explained_no_raw_productization/standard_peak_backfill_policy_summary.json` | `01D7E07B7545293323BCCFD75FA156B33216AF838F564191ACEDB7DEFA90A405` |
| `output/productization_realdata_seed_guard_85raw_20260617/generated_policy_quality_explained_no_raw_productization/standard_peak_backfill_policy.tsv` | `1585F9EBF6C216677406A03C57868EEA38A25B663F00566A9C84C37898D11659` |
| `output/productization_realdata_seed_guard_85raw_20260617/generated_policy_quality_explained_no_raw_productization/standard_peak_backfill_policy_quality_explanations.tsv` | `023AD7794D7C79258BC06CE3A33E8ECA26B5D6866B7D4F0421B2ACECC6C8E4D4` |
| `output/productization_realdata_seed_guard_85raw_20260617/generated_policy_quality_explained_no_raw_productization/narrow_product_writer_expected_diff_acceptance.json` | `093E4F4894D0D7FB05A54FDFDA8454618FEBA0A4AC93EFEC7B77CA64AE97458D` |
| `output/productization_realdata_seed_guard_85raw_20260617/low_height_low_scan_clean_activation_scope_audit/activation_high_signal_clean_scope_audit.tsv` | `C503494F6B72D195C38968A89AEE04B88702BCD4E820B94FAF4444E7A3971EC1` |
| `output/productization_realdata_seed_guard_85raw_20260617/reintegration_stability_audit/reintegration_stability_audit.tsv` | `592B9660588A3FD2D987D5196437E59D2601FCD7F9D934448A53D8C789C5F2FF` |

No 85RAW rerun was needed. Existing artifacts are sufficient to decide that the
broad gate is not feasible as a short product rule.

## 2. ISTD Reference Assessment

ISTD can be used as an independent anchor for limited questions:

- target-to-family mapping through `targeted_istd_benchmark.selected_feature_id`;
- whether active ISTDs are retained in untargeted families;
- RT consistency within the targeted benchmark;
- constant-concentration sanity checks for gross area behavior.

ISTD cannot prove:

- analyte peak-choice correctness;
- analyte area truth;
- broad Backfill write authority;
- that a dirty analyte row is safe because an ISTD family behaved similarly;
- that family-confusion / wrong-small-peak risks are absent.

ISTD artifacts:

| Artifact | SHA256 |
| --- | --- |
| `output/backfill_product_policy_same_peak_activation_85raw_20260608/targeted_istd_benchmark_current_alignment/targeted_istd_benchmark_summary.tsv` | `9319095C6354D4437C9E06F6FD7EFDCFAD170B7C2389536236E06D56A3C7F3DD` |
| `output/backfill_product_policy_same_peak_activation_85raw_20260608/targeted_istd_benchmark_current_alignment/targeted_istd_benchmark_matches.tsv` | `A7D03401C6522A5CAABD8B148A8ADCEB6C76228C818F12CF442FBA8E453E670D` |
| `output/backfill_product_policy_same_peak_activation_85raw_20260608/alignment_seed_audit/alignment_matrix.tsv` | `6BC9D62142FA91B6124DDD061AC8DE4FBF8C59E790FB1957C70513F0D09DEE40` |
| `output/backfill_product_policy_same_peak_activation_85raw_20260608/alignment_seed_audit/alignment_matrix_identity.tsv` | `61A6871D578679829D0CA4DDC9D3181E3F90A8964D8917B9E3BFF3273FBB6EC8` |

All six active ISTDs had 85/85 untargeted positives, but three failed the strict
benchmark by `AREA_MISMATCH`. The worst anchor is d3-N6-medA: 199 candidate
matches, Pearson `0.122663`, and severe low-side matrix outliers. This is useful
failure-mode evidence, not product authority.

The current ISTD matrix check found no active ISTD family with samples above
`3x` its median, and each family had low-side outliers. That supports a working
hypothesis of under-integration risk, but it does not rule out smaller high-side
area errors and does not prove analyte truth.

## 3. 3015 vs 511 Profile Comparison

The unresolved 3015 pool is not treated as negative labels. It is treated as
rows without current write authority.

Summary:

| Group | Count | Trace status | Current meaning |
| --- | ---: | --- | --- |
| approved 511 | 511 | all `matched` | current write authority |
| unresolved 3015 | 3015 | all `matched` | no approved evidence class / oracle |
| missing trace 1087 | 1087 | all `missing_overlay_path` | unverifiable under current contract |

Profile comparison:

| Metric | Approved 511 median | Unresolved 3015 median | Decision impact |
| --- | ---: | ---: | --- |
| `cell_height` | `703906` | `172346` | unresolved pool is lower, but ranges overlap |
| `integration_scan_count` | `13` | `5` | unresolved pool has fewer scans, but ranges overlap |
| `apex_aligned_shape_similarity` | `0.960603` | `0.881808` | unresolved pool is worse, but ranges overlap |
| `boundary_width_min` | `0.4572` | `0.20641` | unresolved pool is narrower, but ranges overlap |
| `apex_delta_abs_min` | `0.0673` | `0.089` | weak separation only |
| `local_window_to_global_max_ratio` | `1` | `1` | not discriminating at the median |

The p10-p90 ranges overlap for all checked numeric features. The 3015 pool is
also not homogeneous: its top blocker combinations include low height, width
outside the clean range, low scan count, low shape, apex-delta, and mixed
scan-count states. It spans 141 feature families; 114 families have at least 5
rows.

The comparison does not prove the 3015 rows are wrong. It also does not prove
they are safe. It shows that profile-only separation cannot produce a short,
defensible product gate.

Wrong peak / wrong family / unresolved identity risk remains open:

- current profile columns do not prove selected peak identity;
- round-trip reintegration does not prove the starting peak was correct;
- ISTD d3-N6-medA shows that high candidate-match contexts can carry severe
  area mismatch / wrong-small-peak risk;
- no current artifact supplies independent analyte peak-choice truth for the
  3015 pool.

## 4. Gate-Or-Park Decision

Output: `park_broad_backfill`.

Reason:

The existing artifacts are enough to decide against broad auto-write feasibility
for the next goal. The 3015 rows are trace-matched but not separable into a
short, human-explainable, truth-like gate; ISTD evidence is useful but does not
prove analyte peak-choice or area truth; and existing round-trip oracle evidence
must not become peak-choice ground truth.

This decision does not kill current Backfill. It preserves:

- the current 511 `write_ready` cells;
- existing expected-diff evidence for those cells;
- existing negative evidence for all-stability, apex-delta, width-only,
  shape-margin, and shape-clean writer attempts;
- generated policy as the control point for already approved evidence.

It closes broad Backfill productization until a genuinely new independent
truth source exists.
