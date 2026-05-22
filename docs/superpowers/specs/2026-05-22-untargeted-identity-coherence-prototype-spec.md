# Untargeted Identity Coherence Diagnostic Prototype Spec

**Date:** 2026-05-22
**Status:** Method review draft v0.3
**Branch:** `codex/untargeted-backfill-logic-reset`
**Worktree:** `C:\Users\user\Desktop\XIC_Extractor\.worktrees\untargeted-backfill-logic-reset`

---

## Summary

This spec keeps the correct abstraction boundary:

```text
identity formation first
Backfill / value recovery second
```

However, v0.2 had a methodological flaw: an RT-windowed peak search before
Backfill is still methodologically close to Backfill. It prevents leakage from
Backfill outputs, but it does not by itself prove identity quality.

V0.3 therefore changes the prototype question:

```text
Can pre-Backfill seed coherence plus independent per-sample trace identity
checks separate plausible untargeted identities from RT-coherent background or
rescue-heavy rows?
```

This is not a full rejection of the coherence diagnostic. It is a narrower
claim: RT-only coherence is useful as a retrieval and audit signal, but it is
not enough to promote an identity.

The diagnostic remains non-mutating. It must not change `alignment_matrix.tsv`,
workbooks, current Backfill behavior, or production promotion logic.

## Design Stance After External Review

The external review raised valid risks, but this spec does not accept every
claim unchanged. The resulting design stance is:

| Review point | Decision | Rationale |
| --- | --- | --- |
| RT-windowed peak finding is too close to Backfill | Accepted | A pre-Backfill run prevents output leakage, but methodologically it is still similar to Backfill if it only checks peak presence and RT. |
| Therefore the diagnostic is useless | Rejected | The diagnostic still catches single-sample seeds, insufficient recurrence, center instability, Backfill evidence leakage, threshold-policy errors, and multi-seed ambiguity. |
| Seed qualification is load-bearing | Accepted with narrower scope | Weak seeds cannot be rescued by recurrence alone, but the hard V0.3 seed gate is coherence and sampling sufficiency, not a complete specificity classifier. |
| All discrimination should live in seed qualification | Modified | Non-seed samples often lack MS2 evidence, so the seed gate anchors a coherent starting point while per-sample trace identity checks and post-scan recurrence guards carry the remaining discrimination. |
| Shape/scoring can wait until a later phase | Rejected for MVP | At least one non-RT trace identity basis must be present in v0.3, otherwise coherence collapses back to RT-local Backfill-like peak finding. |
| Targeted ISTDs should all pass | Modified | ISTDs are positive-control yardsticks, not a blanket pass rule. Only mapped targeted/stable control rows have expected diagnostic outcomes, and misses must be explained. |
| Post-hoc `alignment-dir` can drive the diagnostic | Rejected as primary path | Current TSVs distinguish `detected` and `rescued`, but they are not a complete pre-Backfill owner-state snapshot. Post-hoc mode is comparison/reporting only. |
| Four frozen TSV schemas are too heavy for prototype learning | Accepted with constraint | Freeze only `decisions.tsv`, `cell_evidence.tsv`, `controls.tsv`, and `summary.md`; keep broader evidence tables exploratory until 8RAW review. |
| A major untargeted redesign means starting from scratch | Rejected | Existing untargeted owner/alignment modules and targeted extraction/scoring diagnostics are reusable foundations, not legacy debris. |

## Method Correction

The prototype must not define coherence as only:

```text
seed center -> broad RT window -> find peak -> RT gate -> would-primary
```

That is too close to current owner Backfill mechanics. It can promote the same
rescue-heavy rows when broad background signal has RT-windowed peaks in many
samples.

The useful part of the diagnostic is not "Backfill earlier." The useful part is
making identity promotion observable before value recovery:

- which seed is allowed to ask the cross-sample question;
- which samples pass independent identity checks;
- which rows are only RT-local recurrence;
- which apparent support depends on Backfill evidence;
- which threshold policy would break when moving from 8RAW to 85RAW.

V0.3 may still use XIC extraction to collect candidate traces, but promotion
requires evidence that is independent of simple RT-windowed peak presence:

- seed coherence and evidence sufficiency before any across-sample scan;
- per-sample trace identity / shape quality;
- recurrence background guard.

The resulting decision should then be benchmarked against targeted ISTD or
stable-control yardsticks. Control labels validate the diagnostic; they do not
promote identities.

RT coherence is necessary but not sufficient.

V0.3 confidence ceiling: a positive diagnostic decision is only provisional
identity-family support. It is not MSI Level 1 identification and must not be
worded as library/authentic-standard confirmation unless a future contract adds
library-grade MS/MS or authentic-standard evidence. This follows the same
confidence discipline behind metabolomics identification reporting standards
and non-target screening confidence levels:

- Sumner et al. 2007, Metabolomics Standards Initiative,
  <https://doi.org/10.1007/s11306-007-0082-2>
- Schymanski et al. 2014, non-target identification confidence,
  <https://doi.org/10.1021/es5002105>

## Reuse Existing Foundations

This reset is not a rewrite-from-zero. The current untargeted path has already
built useful foundations, and the targeted path is a major source of validated
methods.

Untargeted foundations to reuse:

- `DiscoveryCandidate` joined by `candidate_id` as the primary seed gate and
  specificity-context evidence surface;
- `build_sample_local_owners` and `SampleLocalMS1Owner` as the pre-Backfill
  owner geometry surface;
- `cluster_sample_local_owners` and `OwnerAlignedFeature` as the starting
  identity-family grouping surface;
- ambiguous-owner and duplicate-owner signals as seed-gate and
  Review-only pressure;
- `pre_backfill_consolidation` logic as prior art for compatible owner grouping,
  not as the final identity algorithm;
- existing `trace_quality`, `scan_support_score`, `region_*`, and integration
  audit fields as candidate identity inputs, using discovery candidate fields
  where owner models intentionally keep only geometry;
- current `production_decisions`, `matrix_identity`, and TSV writers as
  comparison surfaces, not promotion evidence.

Targeted foundations to reuse:

- targeted peak detection and integration primitives, including peak width,
  baseline, scan support, and boundary/integration audit metrics;
- targeted scoring concepts such as support/concern labels, raw score,
  `shape_clean`, `shape_poor`, and CWT/shape support where available;
- targeted ISTD benchmark diagnostics as positive-control yardsticks;
- targeted peak reliability and NL-dropout diagnostics as examples for
  separating infrastructure failure, data-quality failure, and plausible
  biological signal;
- targeted RT/ISTD drift evidence as validation or drift-calibration context,
  not direct row identity-promotion evidence.

Dependency boundary:

- `xic_extractor.alignment.identity_coherence` may reuse small domain primitives,
  typed models, and metric functions that are already independent of IO.
- It must not import `tools.diagnostics.*`, workbook/report renderers, GUI code,
  CLI scripts, or process backends.
- Targeted diagnostics can provide validation artifacts and metric definitions.
  If a diagnostic metric becomes required for promotion, first extract it into a
  small domain/shared module with focused tests, then import that module from the
  identity-coherence implementation.

Design rule:

```text
reuse mature extraction, scoring, audit, and benchmark primitives;
rewrite only the identity-promotion layer that combines them for untargeted rows.
```

Reuse is not inheritance. The implementation may reuse stable signals,
domain primitives, and validation methods, but it must not inherit thresholds,
status semantics, or policy couplings unless they are methodologically valid for
identity promotion. When existing foundations are too thin, misleading, or tied
to Backfill-era behavior, the spec should say so explicitly and either downgrade
the field to review context or define a new diagnostic-owned parameter.

The new diagnostic should therefore be thin orchestration around existing
signals wherever possible. New code is justified when the existing module lacks
the untargeted-specific identity contract, not merely because the old algorithm
will be replaced.

MVP does not change `NeutralLossProfile`. Neutral-loss specificity remains a
Phase 2 curation option. V0.3 uses existing discovery fields such as
`matched_tag_count` and `tag_intersection_status` as zero-schema-change
specificity context.

## Non-Goals

- No production matrix behavior change.
- No replacement of current `owner_backfill.py`.
- No new default Backfill gate.
- No production graph merge/split implementation.
- No GUI change.
- No workbook schema change.
- No frozen broad multi-table diagnostic schema before 8RAW learning.

## Prototype Data Flow

The primary implementation path is inline pre-Backfill:

```text
build_owners
  -> cluster_owners
  -> identity_coherence_diagnostic       # new opt-in diagnostic stage
  -> owner_backfill                      # unchanged production path
  -> build_matrix / review / cells       # unchanged production path
```

This is the only clean path for promotion evidence because the diagnostic needs
pre-Backfill owner state.

Post-run `--alignment-dir` mode is allowed only for comparison and report
joining. It must not be the source of promotion evidence unless the input
artifact explicitly encodes pre-Backfill provenance.

Current `alignment_cells.tsv` has useful `status` and `source_candidate_id`
columns, and `rescued` cells are distinguishable from `detected` cells. That is
not enough to make a post-hoc run the canonical source of pre-Backfill owner
state, because the diagnostic needs all candidate/owner context before
Backfill and before production consolidation decisions.

## Evidence Firewall

Allowed for identity promotion:

- neutral loss tag from the active discovery/profile context;
- product m/z and observed neutral loss tolerance evidence;
- pre-Backfill sample-local MS1 owner evidence;
- diagnostic vendor XIC traces collected before Backfill;
- seed coherence and evidence-sufficiency gates derived before Backfill;
- trace identity / shape metrics derived from diagnostic candidate traces;

Validation-only evidence:

- targeted ISTD benchmark/control labels and positive-control classes;
- targeted benchmark diagnostics emitted by `tools/diagnostics/*`;
- discovery `evidence_score` and `evidence_tier` as review-ranking context
  unless a diagnostic-owned seed-specificity rule is explicitly added later;
- current production `production_decisions`, `matrix_identity`, and workbook
  outputs;
- post-hoc `alignment-dir` joins used only for comparison/reporting.

Validation-only evidence may appear in summary tables, benchmark sections, and
control columns. It must not change `decision`,
`total_coherent_sample_count`, `non_seed_coherent_sample_count`, or any
promotion gate.

Forbidden for identity promotion:

- `owner_backfill` rescued area/status;
- `backfill`, `rescued`, `absent`, `unchecked` production statuses;
- final `include_in_primary_matrix`;
- workbook values;
- family-center re-extraction after Backfill;
- post-Backfill row inclusion or rescue dependency.

The summary must assert:

```text
promotion_used_forbidden_evidence = false
```

The decisions table should keep `forbidden_evidence_seen` when comparison
inputs contain forbidden evidence. It should not carry a per-row "used"
column that is defined to be always false.

The firewall needs a regression fixture before implementation: provide
conflicting post-Backfill fields such as `rescued`, `include_in_primary_matrix`,
or workbook-derived values and prove that `decision`, coherent counts, and gate
outcomes do not change while `forbidden_evidence_seen` becomes true.

## Identity Coherence Configuration

All diagnostic policy must be explicit in an `IdentityCoherenceConfig`. Domain
logic may receive this as a typed config object, but it must not import CLI,
process, RAW, workbook, or diagnostic-tool modules to discover policy.

V0.3 config keys:

```text
seed_min_ms1_scan_support_score = 0.50
precursor_mz_tolerance_ppm = declared
product_mz_tolerance_ppm = declared
observed_loss_tolerance_ppm = declared
max_rt_sec = 180
preferred_rt_sec = 60
seed_center_candidate_sec = 30
max_center_drift_sec = 30
shape_min_points = 7
shape_resample_points = 25
shape_similarity_min_cosine = 0.85
prototype_width_min_candidates = 3
prototype_width_ratio_min = 0.50
prototype_width_ratio_max = 2.00
blank_max_detection_fraction = 0.25
sample_blank_area_ratio_min = 5.00
qc_cv_max = 0.30
max_infrastructure_blocked_fraction = 0.05
min_positive_control_pass_fraction = 1.00
max_negative_control_promoted_count = 0
max_tier3_only_would_primary_fraction = 0.00
max_rt_only_promoted_count = 0
max_forbidden_evidence_used_count = 0
max_projected_85raw_xic_requests = required before 85RAW
positive_control_manifest = optional path before 8RAW, required before interpretation
negative_control_manifest = optional path before 8RAW, required before 85RAW
```

The diagnostic summary must echo every effective config value, its source
(default, CLI/config file, or benchmark artifact), and the units. Broad
retrieval tolerances such as `max_rt_sec = 180` are not identity confidence
claims; they only define candidate retrieval.

## Discriminator Model

V0.3 promotion requires three layers. A candidate that fails any blocking layer
stays Review-only.

```text
seed coherence gate + specificity context
  -> RT-local candidate trace retrieval
  -> independent trace identity checks
  -> diagnostic would-primary / review-only decision
```

### Layer 1: Seed Coherence Gate And Specificity Context

Seed qualification is the first load-bearing gate, but V0.3 must be precise
about what this gate can and cannot prove. The hard gate establishes
seed-owner coherence, quantifiability, and sampling sufficiency. It does not
claim to solve background specificity by itself.

The seed evidence surface is:

```text
SampleLocalMS1Owner geometry
  + DiscoveryCandidate joined by primary_identity_event.candidate_id
```

`SampleLocalMS1Owner` keeps the pre-Backfill owner peak and identity event, but
it does not carry every discovery scoring field. Inline mode must therefore
retain a candidate lookup keyed by `candidate_id`. A missing join is Review-only
because the diagnostic cannot audit seed evidence.

Minimum v0.3 seed requirements:

- neutral loss tag matches the active profile;
- product m/z is inside tolerance;
- observed neutral loss is inside tolerance;
- sample-local MS1 owner exists before Backfill;
- area, apex RT, height, start RT, and end RT are finite;
- owner is not ambiguous and not a duplicate loser;
- the joined `DiscoveryCandidate.best_seed_rt` or
  `primary_identity_event.seed_rt` falls inside
  `owner_peak_start_rt..owner_peak_end_rt`;
- `ms1_scan_support_score >= seed_min_ms1_scan_support_score` when a numeric score
  is available.

`high evidence score` is not required as a blanket rule. The current discovery
`evidence_score` / `evidence_tier` is a review-ranking score, not a pure
identity-specificity gate: it mixes MS1 peak presence, strict seed count,
MS1-vs-seed RT delta, product intensity, MS1 area, scan support, and
superfamily role. V0.3 records it and its component labels for 8RAW review, but
does not use tier A/B/C as a promotion gate.

`ms1_seed_delta_min` is recorded but is not a hard V0.3 gate. Do not derive a
seed co-location threshold from `DiscoverySettings.ms1_search_padding_min`;
that setting is the XIC search-window padding used to find an MS1 peak, not a
scientific identity threshold. If the 8RAW review shows that peak-boundary
co-location is too loose, a later revision must derive a delta threshold from
observed peak widths or prototype-width distributions.

`ms1_trace_quality` is also recorded but not a V0.3 gate. The current discovery
producer emits `clean` when an MS1 peak is found and `missing` when no MS1 peak
is found, so it does not provide an independent graded owner-quality signal.

Baseline seed-gate parameters:

| Parameter | Default | Source | Meaning |
| --- | ---: | --- | --- |
| `seed_min_ms1_scan_support_score` | `0.50` | new identity-coherence diagnostic parameter | Minimum numeric MS1 scan sampling support for a seed owner. Initial value may mirror the current anchor heuristic, but implementation must not import or bind to `AlignmentConfig.anchor_min_scan_support_score`. |

Scan support is a sampling-sufficiency guard, not a background-specificity
guard. It can reject under-sampled peaks, but broad background features may also
have high scan support.

Context fields recorded but not used as hard gates before 8RAW review:

```text
ms1_seed_delta_min
ms1_trace_quality
neutral_loss_mass_error_ppm
matched_tag_count
tag_intersection_status
evidence_score
evidence_tier
ms2_support
ms1_support
rt_alignment
family_context
```

These fields are specificity context, not V0.3 blocking gates. If 8RAW shows
that formally coherent seeds still behave like background, the next revision
should either define a diagnostic-owned seed-specificity gate from these
components or introduce profile-level specificity metadata. Do not silently
reuse discovery review-ranking tiers as identity-promotion thresholds.

Required seed diagnostic fields:

```text
seed_gate_class =
  coherent_seed | review_only_seed_gate_failed | blocked_seed

seed_reject_reason =
  missing_diagnostic_neutral_loss_evidence
  no_quantifiable_owner
  missing_discovery_candidate_join
  ambiguous_owner
  duplicate_loser
  backfill_only_evidence
  nonfinite_peak
  seed_rt_outside_owner_peak
  low_ms1_scan_support
```

Cross-sample background behavior is not a seed-specificity class. It is reported
later as `background_recurrence_pattern` after recurrence evidence exists.

### Layer 2: RT-Local Candidate Retrieval

XIC extraction in V0.3 is candidate retrieval, not promotion evidence by
itself.

RT units must be explicit:

```text
initial_rt_min = seed_rt_min - (max_rt_sec / 60.0)
initial_rt_max = seed_rt_min + (max_rt_sec / 60.0)
```

The retrieval window may default to `max_rt_sec = 180` for 8RAW exploration,
but the extracted peak is only a candidate for further checks.

### Layer 3: Tiered Identity Checks

Every non-seed sample that contributes to would-primary must pass RT plus a
tiered non-RT identity basis. This is not a loose OR gate.

V0.3 identity basis tiers:

```text
tier 1: rt + diagnostic_nl_support
tier 2: rt + shape_similarity
tier 3: rt + prototype_width
```

Tier 1 is diagnostic neutral-loss support, not library-grade MS/MS fragment
confirmation. It supports only provisional identity-family coherence unless a
future contract adds spectral-library or authentic-standard evidence. The source
is the current run's `DiscoveryCandidate` collection, joined by `sample_stem`
and row identity constraints, not by post-Backfill cell status.

Minimum tier 1 join criteria:

- same non-seed sample;
- same neutral-loss tag or declared profile identity;
- precursor m/z, product m/z, and observed neutral loss remain inside
  `IdentityCoherenceConfig` tolerances, with ppm units recorded per cell;
- the matched candidate is pre-Backfill discovery evidence, not owner_backfill
  rescue output;
- collision energy, instrument mode, and source profile are recorded when
  available;
- precursor isolation or coelution ambiguity is recorded as a review flag when
  available.

Ambiguous tier 1 candidate matches must be exposed as review flags and must not
silently promote a cell. Tie-break rules are:

1. prefer same neutral-loss tag plus smallest absolute precursor ppm error;
2. then smallest absolute observed-loss ppm error;
3. then closest apex RT to the row center;
4. if still tied, mark `diagnostic_nl_status = ambiguous` and do not use the
   cell as promotion evidence.

Tier 2 is available when enough XIC points exist to compare normalized local
shape against the seed or group prototype.

V0.3 shape contract:

- both traces must have at least `shape_min_points` points inside their peak
  boundaries;
- subtract the local minimum intensity inside the peak boundaries and clip at
  zero;
- normalize each trace to unit L2 norm after baseline subtraction;
- resample both traces to `shape_resample_points` over normalized RT positions
  from peak start to peak end;
- compute cosine similarity on the resampled vectors;
- pass when `shape_similarity_score >= shape_similarity_min_cosine`;
- emit review flags for low points, zero signal, shoulder/bimodal audit, or
  baseline incompatibility when available.

If the implementation cannot calculate this metric, Tier 2 must be emitted as
`shape_similarity_status = not_assessed` and must not support promotion.

Tier 3 is a fallback. Width must be compared to a prototype width, defined as
the median width of complete candidates used for the stable provisional center,
not only to the seed sample width. A single co-eluted seed peak must not become
the reference width for every sample.

Prototype width inputs:

- use only pre-Backfill candidates with finite apex, start, end, area, and
  height;
- the candidate must pass the RT gate and morphology completeness;
- the candidate must be inside `seed_center_candidate_sec` of the seed RT before
  recentering;
- at least `prototype_width_min_candidates` candidates are required;
- otherwise set `prototype_width_status = not_assessed`.

Tier 3 passes only when the candidate width divided by prototype median width is
inside `prototype_width_ratio_min..prototype_width_ratio_max`. Tier-3-only rows
remain Review-only in V0.3.

Baseline/interference and area/height pattern are review flags in V0.3. They
must not admit a cell as promotion evidence by themselves. Flat area patterns
can describe either stable controls or background, so area-pattern flatness is
not an identity basis without a separate biological expectation model.

A row can be `would_primary_provisional_identity_family_support` only if at
least one non-seed coherent sample is admitted by tier 1 or tier 2.
Tier-3-only rows are Review-only weak-basis rows for V0.3.

Required cell evidence categories:

```text
identity_basis_tier =
  seed_sample
  tier1
  tier2
  tier3
  rt_only
  blocked
  data_quality

non_rt_identity_basis =
  seed_sample
  rt_diagnostic_nl_support
  rt_shape_similarity
  rt_prototype_width
  none
```

`rt_only` and `none` are never allowed to support would-primary.
Baseline and area-pattern concerns must be emitted as review flags, not as
`non_rt_identity_basis`.

### Background Recurrence Guard

`background_recurrence_pattern` is a decision signal, not a label to infer by
eye. V0.3 must calculate a guard status for every row:

```text
background_guard_status =
  pass | background_like | not_assessed
```

Required inputs when available:

- process blanks or solvent blanks;
- QC pools or repeated stable samples;
- sample order / injection order;
- per-cell area or height for assessed samples;
- sample-vs-blank area ratio;
- blank detection count and blank detection fraction;
- QC CV or equivalent repeatability measure.

Default v0.3 background-like criteria:

```text
blank_detection_fraction > blank_max_detection_fraction
median_sample_blank_area_ratio < sample_blank_area_ratio_min
QC CV > qc_cv_max for rows expected to be stable
carryover/run-order flag present
```

Any one background-like criterion sets
`background_guard_status = background_like` and the row decision must be
`review_only_background_recurrence_pattern`.

If blanks/QC/run-order inputs are unavailable, set
`background_guard_status = not_assessed`. A not-assessed background guard is not
evidence of identity. Rows with `not_assessed` may be reviewed in the 8RAW
prototype, but they cannot be used as a Go signal for 85RAW expansion and must
be counted separately in the summary.

## RT Center Rules

The provisional center is another load-bearing step and must not be hand-waved.

For v0.3:

- the seed sample always anchors the first provisional center;
- non-seed candidates can contribute to the provisional center only after
  passing basic morphology completeness;
- candidates farther than `seed_center_candidate_sec` from the seed RT are not
  used to estimate the center;
- `max_center_drift_sec` must be tighter than `preferred_rt_sec`.

Baseline review parameters for 8RAW:

| Parameter | Default | Unit | Meaning |
| --- | ---: | --- | --- |
| `max_rt_sec` | 180 | seconds | Broad retrieval window. |
| `preferred_rt_sec` | 60 | seconds | Final RT acceptance gate after independent checks. |
| `seed_center_candidate_sec` | 30 | seconds | Max seed distance for center-estimation candidates. |
| `max_center_drift_sec` | 30 | seconds | Seed-anchor guard; intentionally tighter than the 60 sec gate. |

Promotion must report:

```text
center_method
center_candidate_count
center_drift_sec
center_decision =
  seed_anchored | recentered_stable | center_unstable_review_only
```

## Support Thresholds

Do not treat `min_coherent_samples = 3` as a dataset-independent product rule.

For the 8RAW review subset:

```text
min_total_coherent_samples = 3
seed_counts_toward_total = true
min_non_seed_coherent_samples = 2
```

The diagnostic must report both absolute count and fraction:

```text
total_coherent_sample_count
non_seed_coherent_sample_count
assessed_sample_count
coherent_sample_fraction
```

For 85RAW, the 8RAW threshold cannot be copied blindly because `3/8` and
`3/85` have very different meaning. 85RAW validation must use a reviewed
threshold policy, such as a minimum count plus minimum fraction, before any
production interpretation.

## RAW/XIC Cost Budget

The diagnostic must keep request cost first-class because 85RAW viability
depends on avoiding unnecessary vendor XIC calls.

Layer 1 is the cost gate:

```text
review_only_seed_gate_failed or blocked_seed
  -> no Layer 2 cross-sample XIC retrieval
```

Required counters:

```text
layer1_candidate_count
layer1_seed_gate_failed_count
layer1_blocked_count
layer2_xic_request_count
extract_xic_batch_count
raw_chromatogram_call_count
xic_point_count
xic_request_cache_hit_count
xic_request_deduplicated_count
wall_time_sec
per_raw_xic_request_count
per_decision_xic_request_count
projected_85raw_xic_request_count
```

The summary must state whether request projection used observed 8RAW request
rate, expected sample count, candidate count, or a more explicit locality model.
If `max_projected_85raw_xic_requests` is unset before 85RAW, the run cannot be a
Go decision.

If an MS1 scan-index or approximate fast path is used, it must be marked as an
explicit approximate diagnostic mode. It must not silently replace vendor XIC as
an equivalent path.

## Control Manifests And Yardsticks

V0.3 must include a cheap positive-control yardstick before interpreting 8RAW
results.

Required before interpretation:

- targeted ISTD benchmark output from existing `tools/diagnostics/targeted_istd_benchmark.py`;
- selected stable-like ISTD or targeted control rows mapped to untargeted
  candidate families;
- expected outcome for each control:
  - pass the seed coherence gate where applicable;
  - pass trace identity checks;
  - explain misses explicitly when not promoted.

The control set must be declared in a small manifest before an 8RAW result can
be interpreted:

```text
identity_coherence_controls.tsv or identity_coherence_controls.yml
```

Required manifest fields:

```text
control_id
control_type = positive_istd | stable_positive | negative_blank | negative_background | decoy
targeted_benchmark_artifact
target_label
sample_stem_or_group
expected_mapping_status
expected_decision
precursor_mz_tolerance_ppm
product_mz_tolerance_ppm
observed_loss_tolerance_ppm
rt_tolerance_sec
required_failure_reason_when_missed
```

Positive controls test sensitivity, not specificity. V0.3 must also include at
least one negative yardstick before 85RAW expansion: a blank/background row,
known ubiquitous/background row, ambiguous mapping, or decoy RT/mass/NL control.

Control mapping must be audited before interpreting pass/fail:

- map controls to untargeted candidate families by neutral-loss tag, precursor
  m/z, and RT within declared tolerances;
- report `mapped`, `unmapped`, and `ambiguous_mapping` counts;
- for every mapped control, report targeted label, candidate family id,
  precursor m/z delta, RT delta, and tag match status.

The Go/No-Go table cannot use vague "expected stable-like rows" without naming
the control set or linking the benchmark artifact.

## Diagnostic Output Contract

V0.3 intentionally freezes only the minimum review surface needed to audit both
row-level decisions and the load-bearing per-sample non-RT evidence:

```text
untargeted_identity_coherence_decisions.tsv
untargeted_identity_coherence_cell_evidence.tsv
untargeted_identity_coherence_controls.tsv
untargeted_identity_coherence_summary.md
```

Exploratory aggregate/detail tables are allowed but not frozen before 8RAW:

```text
untargeted_identity_coherence_candidates.tsv
untargeted_identity_coherence_groups.tsv
```

The optional tables should be emitted when useful, but their schema may change
until the first 8RAW review identifies the fields that actually matter.

### Required `decisions.tsv` Columns

```text
decision_id
source_feature_family_id
primary_seed_id
seed_sample_stem
seed_gate_class
seed_reject_reason
seed_rt_inside_owner_peak
seed_ms1_delta_min
seed_ms1_trace_quality
seed_ms1_scan_support_score
seed_neutral_loss_mass_error_ppm
seed_matched_tag_count
seed_tag_intersection_status
seed_evidence_score
seed_evidence_tier
seed_ms2_support
seed_ms1_support
seed_rt_alignment
seed_family_context
decision
decision_reason
total_coherent_sample_count
non_seed_coherent_sample_count
assessed_sample_count
coherent_sample_fraction
min_total_coherent_samples
min_non_seed_coherent_samples
center_decision
center_drift_sec
non_rt_identity_pass_count
tier1_cell_count
tier2_cell_count
tier3_cell_count
diagnostic_nl_supported_sample_count
weak_basis_only
background_recurrence_pattern
background_guard_status
rt_only_candidate_count
blocked_infrastructure_count
data_quality_reject_count
forbidden_evidence_seen
control_class
control_expected_decision
notes
```

Decision enum:

```text
would_primary_provisional_identity_family_support
review_only_seed_gate_failed
review_only_rt_only_support
review_only_insufficient_support
review_only_center_unstable
review_only_background_recurrence_pattern
review_only_background_guard_not_assessed
review_only_weak_basis_tier3_only
review_only_multi_seed_requires_phase2
blocked_infrastructure
```

`blocked_infrastructure` is separate from data-quality rejection. It covers
missing RAW, unreadable files, extraction crashes, and malformed required
inputs. Non-finite traces or bad peak fields are data-quality outcomes unless
they prevent the run from assessing the sample at all.

### Required `cell_evidence.tsv` Columns

This table is narrow but frozen because every non-seed coherent sample must have
an auditable non-RT identity basis. It is not the old broad `cells.tsv` schema.

```text
decision_id
source_feature_family_id
sample_stem
sample_role
cell_decision
candidate_apex_rt_min
candidate_peak_start_rt_min
candidate_peak_end_rt_min
candidate_peak_width_sec
candidate_area
candidate_height
candidate_point_count
rt_delta_center_sec
rt_gate_result
identity_basis_tier
non_rt_identity_basis
non_rt_identity_result
diagnostic_nl_status
precursor_mz_delta_ppm
product_mz_delta_ppm
observed_loss_delta_ppm
shape_similarity_status
shape_similarity_score
shape_point_count
prototype_width_status
prototype_width_sec
prototype_width_ratio
background_guard_status
xic_rt_min
xic_rt_max
xic_point_count
xic_request_id
review_flags
evidence_source
reject_reason
```

`sample_role` enum:

```text
seed
non_seed
```

`cell_decision` enum:

```text
coherent_identity_supported
rt_only_review_only
outside_rt_gate
data_quality_reject
blocked_infrastructure
not_assessed
```

For a `non_seed` sample to contribute to
`non_seed_coherent_sample_count`, `cell_decision` must be
`coherent_identity_supported`, `rt_gate_result` must be pass, and
`non_rt_identity_result` must be pass. RT-only rows remain review evidence, not
promotion evidence. Tier-3-only rows must not become
`would_primary_provisional_identity_family_support` unless 8RAW review explicitly
changes this contract.

Required categorical values:

```text
rt_gate_result = pass | fail | not_assessed
identity_basis_tier = seed | tier1 | tier2 | tier3 | rt_only | blocked | data_quality
non_rt_identity_basis =
  seed_sample | rt_diagnostic_nl_support | rt_shape_similarity |
  rt_prototype_width | none
non_rt_identity_result = pass | fail | not_assessed | blocked
diagnostic_nl_status = pass | fail | ambiguous | not_assessed
shape_similarity_status = pass | fail | low_points | zero_signal | not_assessed
prototype_width_status = pass | fail | too_few_candidates | not_assessed
background_guard_status = pass | background_like | not_assessed
```

### Required `controls.tsv` Columns

This table records machine-readable positive and negative yardstick mapping.

```text
control_id
control_type
targeted_benchmark_artifact
target_label
sample_stem_or_group
expected_mapping_status
actual_mapping_status
expected_decision
actual_decision
source_feature_family_id
precursor_mz_delta_ppm
product_mz_delta_ppm
observed_loss_delta_ppm
rt_delta_sec
tag_match_status
failure_reason
```

### Required `summary.md` Sections

- command and mode;
- inline pre-Backfill input source or explicit reason a post-hoc run is
  comparison-only;
- input hashes and row counts;
- positive-control artifact and mapped control rows;
- positive and negative control manifest paths;
- evidence firewall assertion and `forbidden_evidence_used_count`;
- seed gate counts and seed specificity context distributions;
- RT-only candidate counts;
- independent trace identity pass counts by tier;
- diagnostic-NL-supported sample counts;
- weak-basis-only row counts;
- background guard status counts;
- per-sample evidence coverage and missing-basis counts;
- infrastructure-blocked counts;
- data-quality reject counts;
- threshold count and fraction summaries;
- RAW/XIC request, point, per-RAW, and timing counters;
- per-decision XIC request counts and projected 85RAW request estimate;
- positive/negative-control mapping counts, ambiguous/unmapped controls, and
  negative-control promotion count;
- Go / No-Go / Pivot table.

## CLI / Invocation Contract

Preferred inline mode:

```powershell
python scripts\run_alignment.py `
  <existing args> `
  --emit-identity-coherence-diagnostic `
  --identity-coherence-config <identity_coherence_config.yml> `
  --identity-coherence-output-dir <diagnostic_output_dir>
```

Equivalent diagnostic module mode is acceptable only if it consumes an explicit
pre-Backfill owner-state export produced before `owner_backfill`:

```powershell
python -m tools.diagnostics.untargeted_identity_coherence `
  --pre-backfill-owner-state <owner_state.jsonl> `
  --identity-coherence-config <identity_coherence_config.yml> `
  --raw-dir <raw_dir> `
  --output-dir <diagnostic_output_dir>
```

Post-hoc comparison mode:

```powershell
python -m tools.diagnostics.untargeted_identity_coherence_report `
  --alignment-dir <existing_alignment_output_dir> `
  --diagnostic-dir <diagnostic_output_dir>
```

Post-hoc comparison mode must not promote identities.

Process-mode orchestration contract:

- `xic_extractor.alignment.identity_coherence` domain code receives typed
  owner/candidate/config/trace payloads only.
- Serial and process orchestration may call RAW adapters or schedule XIC
  extraction, but that remains outside domain logic.
- Process workers receive pickleable request/result payloads. Do not pass open
  RAW handles, nested closures, GUI objects, workbook objects, or report writers.
- Before implementation is accepted, add a no-RAW process-mode smoke test that
  proves the diagnostic request payloads can be pickled and round-tripped.

## Failure Modes That Must Be Explainable

Infrastructure-blocked:

- missing required input file;
- missing required input column;
- missing RAW source;
- RAW extraction error;
- process worker failure;
- malformed pre-Backfill owner-state export.

Data-quality or identity rejects:

- missing diagnostic neutral-loss evidence;
- seed coherence/sampling gate failed;
- missing discovery-candidate join;
- seed RT outside owner peak;
- low MS1 scan support;
- background recurrence pattern;
- ambiguous owner;
- duplicate loser;
- Backfill-only evidence rejected;
- non-finite trace or peak field;
- zero candidate peak;
- incomplete peak boundaries;
- center drift unstable;
- outside recentered RT gate;
- RT-only support with no independent trace identity basis;
- insufficient total or non-seed coherent samples;
- multi-seed ambiguity requiring Phase 2.

## Go / No-Go / Pivot Rules

| Observation after 8RAW | Decision |
| --- | --- |
| `positive_control_pass_fraction >= min_positive_control_pass_fraction` and every miss has an explicit acceptable reason | Proceed to 85RAW threshold-policy review. |
| `positive_control_pass_fraction < min_positive_control_pass_fraction` | No-Go; add trace identity metrics or fix mapping before continuing. |
| `negative_control_promoted_count > max_negative_control_promoted_count` | No-Go; background/decoy controls are being promoted. |
| `layer1_seed_gate_failed_count` contributes to any would-primary row | No-Go; fix seed-gate enforcement. |
| `background_guard_status = background_like` on any would-primary row | No-Go; tighten background recurrence guard or downgrade the row. |
| `background_guard_status = not_assessed` on any would-primary row before 85RAW | Pivot; add blank/QC/order guard inputs or mark the 85RAW interpretation unavailable. |
| `tier3_only_would_primary_fraction > max_tier3_only_would_primary_fraction` | Pivot; require diagnostic NL or shape support before promotion. |
| `rt_only_promoted_count > max_rt_only_promoted_count` | No-Go; RT-only support must remain Review-only. |
| `forbidden_evidence_used_count > max_forbidden_evidence_used_count` | No-Go; fix evidence firewall. |
| 8RAW count threshold passes but the coherent fraction would be below the reviewed 85RAW fraction policy | Define count+fraction policy before 85RAW. |
| Multi-seed/overflow dominates candidate decisions by reviewed rate | Pivot to Phase 2 graph merge/split spec. |
| `projected_85raw_xic_request_count > max_projected_85raw_xic_requests`, or the max is unset before 85RAW | Add request-budget/locality design before 85RAW. |
| `infrastructure_blocked_fraction > max_infrastructure_blocked_fraction` | Fix run/input infrastructure before scientific interpretation. |

## Acceptance Criteria Before Implementation

This spec is ready for implementation only after review signs off on:

- the method difference from Backfill is explicit and accepted;
- seed gate and specificity context use `DiscoveryCandidate` joined by `candidate_id` plus
  `SampleLocalMS1Owner` geometry;
- seed gates are defined in terms of seed-owner peak-boundary
  co-location and seed-owner scan support;
- `ms1_seed_delta_min` and `ms1_trace_quality` are record-only context fields
  until 8RAW evidence justifies real thresholds;
- `evidence_score` / `evidence_tier` are explicitly review-ranking context, not
  identity-promotion gates;
- background recurrence is a post-scan decision pattern, not a seed class;
- tiered non-RT identity checks are defined in V0.3 MVP, including the
  `rt_diagnostic_nl_support` confidence ceiling and shape-similarity metric;
- `background_guard_status` is operationalized with blank/QC/order inputs and
  explicit `not_assessed` behavior;
- all thresholds live in `IdentityCoherenceConfig`, and the domain module does
  not import or bind to `AlignmentConfig`, CLI, process, RAW, workbook, report,
  or diagnostic-tool surfaces;
- 8RAW and 85RAW threshold policies are separated;
- seed sample counting is explicit (`seed + at least 2 non-seed` for 8RAW);
- targeted ISTD/control rows and negative controls are declared in a
  machine-readable control manifest;
- positive/negative-control mapping criteria and ambiguous/unmapped counts are
  defined in `untargeted_identity_coherence_controls.tsv`;
- RAW/XIC request counters are first-class and Layer 1 rejects skip Layer 2 XIC;
- inline pre-Backfill data flow and process-mode pickleable payload boundaries
  are accepted as the primary path;
- an evidence-firewall fixture proves post-Backfill/rescued evidence can be seen
  but cannot change decisions, counts, or gates;
- output scope is limited to `decisions.tsv`, `cell_evidence.tsv`,
  `controls.tsv`, and `summary.md` as frozen contracts for the first run;
- Go/No-Go uses config-backed numeric counters rather than subjective review
  language.

## Review Questions

1. Is V0.3 acceptable as a seed coherence/sampling gate, with specificity
   context reviewed after 8RAW rather than hard-gated now?
2. Should a later diagnostic-owned seed-specificity gate be derived from
   evidence components, NL profile metadata, or both?
3. Is `rt_diagnostic_nl_support` the right name for tier 1, given that V0.3
   does not claim library-grade fragment confirmation?
4. Are the default shape-similarity settings acceptable for the first 8RAW run?
5. Which targeted ISTD/stable rows and negative/decoy rows should seed the
   control manifest?
6. Is `seed + 2 non-seed coherent samples` the right 8RAW support threshold?
7. What count+fraction and RAW/XIC budget policy must be reviewed before 85RAW?
8. Is post-hoc `alignment-dir` mode acceptable only as comparison/reporting?
