# P2B Area Mismatch Triage Note

> Historical validation note: retained as evidence/provenance, not live
> source-of-truth. Current rerun policy and stable target conclusions live in
> `docs/diagnostic-ledger.md`; product tier and matrix authority live in
> `docs/superpowers/plans/2026-06-15-productization-control-plane.md`,
> `docs/superpowers/validation/productization_status_index_v1.tsv`, and
> `docs/superpowers/specs/productization_authority_manifest.v1.json`. Removal or
> private-note migration requires an explicit removal approval plus a
> repo-self-contained referrer pass.

Date: 2026-05-26

## Verdict

`production_candidate` for P2B gate interpretation.

The 85RAW P8b super-window run is production-candidate for performance and
primary-output equivalence. The two strict `AREA_MISMATCH` rows do not justify
holding P2B as `no_go` by themselves.

`AREA_MISMATCH` should not be treated as a single hard blocker class. The two
current failures have different meanings:

- `d4-N6-2HE-dA`: benchmark area mismatch is explained by isotope-shift
  matching. This should be a warning or separate diagnostic bucket, not a P2B
  blocker by itself.
- `d3-N6-medA`: exact-match family has known severe biological-matrix RT drift.
  Targeted and alignment RT distributions agree globally; the remaining
  sample-level outliers are row-level review items, not a P2B blocker.

## Evidence Inputs

- 85RAW alignment:
  `output\phase1_p8b_superwindow\alignment\85raw_validation_minimal_superwindow`
- Strict targeted benchmark:
  `output\phase1_p8b_superwindow\diagnostics\targeted_istd_benchmark_85raw_superwindow`
- Strict benchmark with targeted reliability:
  `output\phase1_p8b_superwindow\diagnostics\targeted_istd_benchmark_85raw_superwindow_strict_reliability`
- 85RAW targeted reliability:
  `output\phase1_p8b_superwindow\diagnostics\targeted_reliability_85raw_region_first_safe_merge`
- Target-only ISTD RT trend audit:
  `output\phase1_p8b_superwindow\diagnostics\targeted_istd_rt_trend_85raw`
- Selected-families integration audit:
  `output\phase1_p8b_superwindow\alignment\85raw_selected_area_mismatch_boundary_audit`
- Focused evidence spine:
  `output\phase1_p8b_superwindow\diagnostics\evidence_spine_consistency_85raw_area_mismatch_focused`
- Focused evidence spine, rerun against final alignment after primary-match
  diagnostic fix:
  `output\phase1_p8b_superwindow\diagnostics\evidence_spine_consistency_85raw_area_mismatch_final_alignment_primary_match`
- Focused area uncertainty:
  `output\phase1_p8b_superwindow\diagnostics\area_integration_uncertainty_85raw_area_mismatch_focused`

## d4-N6-2HE-dA

Selected benchmark match:

- Target: `d4-N6-2HE-dA`
- Selected family: `FAM007724`
- Match type: `isotope_shift`
- Mass shift: `+1.003355 Da`
- Target m/z: `300.161`
- Family center m/z: `301.165`
- Sample RT p95 absolute delta: `0.0416 min`

Observed area relationship:

- Alignment area / targeted workbook area median: `0.106335`
- Alignment area / targeted raw area median: `0.106335`
- Workbook area / targeted raw area median: `1.0`

Interpretation: this is expected to be area-incommensurable because the
benchmark paired the target against an isotope-shifted family. The RT and
identity match are stable enough for audit, but the area comparison should not
be interpreted as baseline failure.

## d3-N6-medA

Selected benchmark match:

- Target: `d3-N6-medA`
- Selected family: `FAM002625`
- Match type: `exact`
- Targeted reliability: `85 / 85 benchmark_eligible`
- Sample RT p95 absolute delta: `0.083 min`
- Targeted RT range: `24.1827-26.3365 min`
- Alignment RT range: `24.1827-26.3365 min`
- Targeted RT median: `25.7409 min`
- Alignment RT median: `25.7409 min`
- Max paired sample RT delta observed in detailed triage: `1.2896 min`

Observed area relationship:

- Alignment area / targeted workbook area median: `0.999999`
- Alignment area / targeted raw area median: `0.999999`
- Workbook area / targeted raw area median: `1.0`
- Alignment area / targeted baseline-corrected area median: `1.14093`

This is not mainly a baseline-definition mismatch, and it is not a global RT
identity failure. The target-only ISTD RT trend audit confirms that
`d3-N6-medA` has the widest global RT movement among the ISTDs:

- target-only RT range: `2.1538 min`
- global-median absolute RT delta p95: `1.4571 min`
- local rolling-median absolute RT delta p95, using `±4` injections:
  `0.0483 min`
- local moderate/severe drift rows: `0 / 85`

Interpretation: `d3-N6-medA` has a strong injection-order / batch-scale RT
trend in the targeted method itself, but it is locally coherent. This supports
the user's target-summary observation: large absolute RT differences for this
ISTD are expected context, not a standalone absence or identity failure. The
targeted summary and alignment cells agree on the full RT range and median.
Most rows compare well, but a small set of rows have local RT or boundary
outliers large enough to dominate Pearson correlation.

Representative review rows:

| Sample | Target RT | Alignment RT | RT delta min | Alignment / targeted raw area | Root symptom |
|---|---:|---:|---:|---:|---|
| `TumorBC2267_DNA` | 24.4228 | 25.7124 | 1.2896 | 0.000537 | wrong production cell |
| `TumorBC2270_DNA` | 24.4431 | 24.6924 | 0.2493 | 0.010396 | boundary/ownership shifted right |
| `TumorBC2275_DNA` | 24.4825 | 24.7319 | 0.2494 | 0.014106 | boundary/ownership shifted right |
| `TumorBC2286_DNA` | 24.8323 | 25.0399 | 0.2076 | 0.015261 | boundary/ownership shifted right |
| `NormalBC2312_DNA` | 26.1492 | 26.2320 | 0.0828 | 0.129728 | clipped/shifted boundary |

Review direction: `primary_family_consolidation` merges the correct identity
family, but a few sample-level observations are sourced from a smaller detected
MS2 owner or clipped boundary while a stronger local peak exists in nearby
backfill evidence. This is an ownership/consolidation review item, not an ASLS
baseline blocker and not a P2B hard blocker.

The original focused evidence-spine run overcounted mismatches because the
diagnostic matcher sometimes preferred a single-sample audit loser with a
slightly closer m/z/RT distance over the final primary-consolidated family. The
matcher now prefers primary-consolidated rows first, then compares RT and m/z
within that production layer.

Updated final-alignment evidence spine:

- rows checked: `170`
- matched rows: `85`
- consistent rows: `54`
- missing alignment rows: `85` (`d4-N6-2HE-dA`, explained by isotope-shift
  matching rather than exact m/z matching)
- `d3-N6-medA` residual mismatch categories:
  - `boundary_end_delta_gt_0.10`: `16`
  - `boundary_start_delta_gt_0.10;area_ratio_outside_2x`: `5`
  - `boundary_start_delta_gt_0.10`: `4`
  - `boundary_start_delta_gt_0.10;boundary_end_delta_gt_0.10;area_ratio_outside_2x`: `4`
  - `boundary_end_delta_gt_0.10;area_ratio_outside_2x`: `2`

Largest remaining RT/boundary review rows:

| Sample | Family | Target RT | Alignment RT | RT delta min | Alignment / targeted area | Reason |
|---|---|---:|---:|---:|---:|---|
| `TumorBC2275_DNA` | `FAM002625` | 24.4825 | 24.7319 | 0.2494 | 0.0141 | boundary / area tail |
| `TumorBC2270_DNA` | `FAM002625` | 24.4431 | 24.6924 | 0.2493 | 0.0104 | boundary / area tail |
| `TumorBC2286_DNA` | `FAM002625` | 24.8323 | 25.0399 | 0.2076 | 0.0153 | boundary / area tail |
| `TumorBC2277_DNA` | `FAM002625` | 24.5408 | 24.4578 | -0.0830 | 0.1980 | area tail |
| `TumorBC2264_DNA` | `FAM002625` | 24.2849 | 24.2020 | -0.0829 | 0.1612 | area tail |
| `NormalBC2312_DNA` | `FAM002625` | 26.1492 | 26.2320 | 0.0828 | 0.1297 | area tail |

`TumorBC2267_DNA` remains the largest benchmark-selected-family outlier:
`FAM002625` is at RT `25.7124` while targeted selected RT is `24.4228`.
The final evidence-spine matcher finds a nearby audit loser family
(`FAM002723`, RT `24.4648`, area ratio `0.2456`) instead of the production
family because the production-family row is outside the exact-match RT
threshold. This is an ownership/consolidation tail, not evidence that the
target is globally absent or that P2B should be blocked.

## P2B Gate Interpretation

Do not block P2B on area mismatch as a generic class.

Block only when the area mismatch is coupled to at least one of:

- target-level identity or coverage regression;
- benchmark `DRIFT`, `MISS`, `SPLIT`, or `COVERAGE` failure;
- global targeted-vs-alignment RT distribution disagreement not explained by
  known target drift;
- row-level boundary outliers that change the target-level decision, not just a
  small localized area-correlation tail;
- unexplained area mismatch after baseline and isotope-shift explanations are
  removed.

Under that rule:

- `d4-N6-2HE-dA`: non-blocking warning.
- `d3-N6-medA`: non-blocking warning / row-level review item. The strict area
  failure is real as a diagnostic, but it is not a P2B no-go condition because
  identity, coverage, targeted reliability, and global RT drift behavior are
  preserved.

## Machine Gate Status

The 85RAW strict reliability decision report was regenerated with the two
`AREA_MISMATCH` rows declared as known exceptions:

`output\phase1_p8b_superwindow\diagnostics\alignment_decision_report_85raw_superwindow_strict_reliability_complete\alignment_decision_report.html`

Result:

- Verdict: `WARN`
- ISTD pass: `3`
- ISTD warning: `1`
- Known ISTD exceptions: `2`
- Unhandled ISTD failures: `0`

This keeps strict targeted reliability warnings visible while preventing them
from being misclassified as hard P2B failures.

The P2B AsLS promotion gate now has an optional
`--target-rt-trend-summary-tsv` input. A selected-family RT delta above
`0.5 sec` is still a blocker when unexplained, but it is accepted as
target-trend-supported when the target summary is locally coherent
(`local_abs_delta_p95_min <= 0.10` and no local moderate/severe drift rows).
This keeps severe local-drift targets such as `d3-N6-medA` from being blocked
solely because their absolute RT differs from the targeted reference.

## Next Action

Proceed with P2B as `production_candidate` while tracking the `d3-N6-medA`
localized ownership/boundary tails as a separate post-P2B review item. Keep
target RT trend evidence wired into P2B reruns so large absolute RT shifts are
classified by local coherence instead of treated as standalone failures.
