# Peak / Backfill Outside-Frame Research Note

Date: 2026-06-09

Status: `research_input`. This note records bounded outside-frame literature and
source-code ideas for XIC Extractor peak picking, PeakHypothesis backfill, and
nonstandard peak integration policy. It does not define product authority or
change matrix behavior.

## Verdict

The strongest cross-source pattern is not to replace the current picker with a
single external algorithm. Mature LC-MS tools and recent literature instead
separate:

- hypothesis enumeration;
- boundary and shape evidence;
- fill / gap provenance;
- identity confidence;
- quantitative integration confidence;
- review or uncertainty flags.

For XIC Extractor, this supports keeping `PeakHypothesis` as the product unit
while adding explicit integration-quality and fill-provenance evidence. Same-peak
own-max MS1 evidence can support identity, but it must not silently upgrade a
nonstandard area into standard quantitative use.

## Source Patterns

### MZmine Peak Finder Gap Filling

MZmine's Peak finder gap filler returns to the expected m/z and RT region for a
missing aligned feature, scans candidate points, groups candidate segments,
requires a local maximum, applies a minimum data-point filter, and marks
gap-filled features as `ESTIMATED` while leaving no-evidence rows empty.

Design input:

- Backfill should be represented as `filled` or `estimated` provenance, not as a
  detected peak clone.
- Candidate segment evidence should include local maximum, scan count, RT/mz
  tolerance source, and no-evidence state.

Minimum XIC experiment:

- Mask 20-50 high-confidence detected cells, rerun a backfill-only diagnostic,
  and compare recovered apex RT, boundary, scan count, and area ratio against
  the original detected cell.

### xcms `fillChromPeaks`

xcms records filled peaks with `is_filled=TRUE`. Its newer
`ChromPeakAreaParam` defines fill regions from detected chromatographic peak
areas, commonly using quantiles of detected boundaries, while the older
feature-range method is documented as less preferred because it can underestimate
area.

Design input:

- Use donor-derived boundary distributions rather than one broad row-wide
  window when possible.
- Preserve `is_filled`, fill method, region policy, and actual integrated
  m/z/RT range.
- Compare quantile / median / min-max fill windows before choosing a production
  policy.

Minimum XIC experiment:

- For the same candidate gaps, compute `minmax`, `iqr/quantile`, and
  `median-donor-boundary` windows and report area sensitivity. High sensitivity
  should downgrade integration confidence.

### OpenMS FeatureFinderMetabo

OpenMS FeatureFinderMetabo treats metabolite feature finding as hypothesis
assembly from mass traces and scores compatibility by RT, m/z, and isotope
intensity pattern evidence.

Design input:

- `PeakHypothesis` should become an evidence bundle, not just a selected peak
  label.
- Ambiguous local regions should support multiple hypotheses with explicit
  assembly status such as `assembled`, `singleton`, `low_overlap`, or
  `isotope_unsupported`.

Minimum XIC experiment:

- For a small ambiguous/backfill set, emit top candidate hypotheses with RT
  overlap, m/z consistency, isotope/adduct/MS2 support, and boundary evidence,
  without changing the final matrix.

### Algorithm Disagreement And Peak Quality Literature

Peak-picker comparison and peak-quality work supports treating algorithm
disagreement as an uncertainty signal rather than selecting one algorithm as an
authority. Recent peak-quality studies also support simple interpretable metrics
for false-positive reduction and reviewer triage.

Design input:

- Add `boundary_disagreement` and `integration_uncertainty` fields when CWT,
  local minima, raw descent, or selected-owner windows disagree.
- Add a compact `quality_bucket` taxonomy such as `clean`, `tailing`,
  `shoulder`, `coelution_suspect`, `boundary_uncertain`,
  `low_signal_uncertain`, and `unassessable`.
- Start with explainable features before a heavier ML model.

Minimum XIC experiment:

- On manually reviewed nonstandard peaks, calculate apex prominence, boundary
  valley depth, tail asymmetry, neighbor ratio, scan count, baseline ratio, and
  boundary-method disagreement. Evaluate whether the metrics rank known manual
  rejects above standard peaks.

### Gap Filling And Missingness Literature

Metabolomics missing-value literature separates preprocessing misses from
left-censored / below-LOD observations and from no-evidence gaps. Fill peaks can
represent targeted re-extraction, but they should not be confused with general
imputation.

Design input:

- Backfill should target `recoverable_signal_candidate` rows.
- `left_censored_candidate`, `no_evidence`, and `interference_risk` should stay
  explicit and usually should not produce a standard area.

Minimum XIC experiment:

- Classify gaps into `recoverable_signal_candidate`, `left_censored_candidate`,
  `no_evidence`, and `interference_risk` using existing trace availability,
  local signal, RT/mz compatibility, and interference evidence.

## Recommended Next Design Slice

Do not start by replacing the picker. Start with a diagnostic-only
`PeakHypothesis integration quality` slice:

- input: selected questioned/backfill cells plus current RAW-backed trace or
  existing trace JSON;
- output: one TSV keyed by PeakHypothesis / feature family / seed group / sample;
- fields: `is_filled`, `fill_method`, `donor_boundary_source`,
  `search_box_source`, `rt_error_to_family`, `mz_error_ppm`, `scan_count`,
  `local_max_present`, `snr_or_baseline_ratio`, `boundary_disagreement`,
  `neighbor_interference_flag`, `identity_confidence`,
  `integration_confidence`, `quality_bucket`, `matrix_quantitative_use`;
- first validation: masked-positive detected-cell recovery, not production
  correction;
- exit rule: promote only if masked-positive false-positive risk and area
  sensitivity are bounded; otherwise keep as review-only uncertainty evidence.

This keeps the current true-signal recovery goal alive while avoiding the main
failure mode: silently writing a plausible same-peak identity with an unreliable
nonstandard area.
