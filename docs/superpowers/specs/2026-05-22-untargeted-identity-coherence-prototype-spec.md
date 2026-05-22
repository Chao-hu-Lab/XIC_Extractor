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
Can pre-Backfill seed specificity plus independent per-sample trace identity
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
| Seed qualification is load-bearing | Accepted | Weak or low-specificity seeds cannot be rescued by recurrence alone. Seed specificity must be promoted from a loose filter to a first-class gate. |
| All discrimination should live in seed qualification | Modified | Non-seed samples often lack MS2 evidence, so seed specificity anchors the identity while MS1 trace identity checks support cross-sample coherence. |
| Shape/scoring can wait until a later phase | Rejected for MVP | At least one non-RT trace identity basis must be present in v0.3, otherwise coherence collapses back to RT-local Backfill-like peak finding. |
| Targeted ISTDs should all pass | Modified | ISTDs are positive-control yardsticks, not a blanket pass rule. Only mapped targeted/stable control rows have expected diagnostic outcomes, and misses must be explained. |
| Post-hoc `alignment-dir` can drive the diagnostic | Rejected as primary path | Current TSVs distinguish `detected` and `rescued`, but they are not a complete pre-Backfill owner-state snapshot. Post-hoc mode is comparison/reporting only. |
| Four frozen TSV schemas are too heavy for prototype learning | Accepted with constraint | Freeze only `decisions.tsv`, `cell_evidence.tsv`, and `summary.md`; keep broader evidence tables exploratory until 8RAW review. |
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

- seed specificity before any across-sample scan;
- per-sample trace identity / shape quality;
- recurrence background guard.

The resulting decision should then be benchmarked against targeted ISTD or
stable-control yardsticks. Control labels validate the diagnostic; they do not
promote identities.

RT coherence is necessary but not sufficient.

## Reuse Existing Foundations

This reset is not a rewrite-from-zero. The current untargeted path has already
built useful foundations, and the targeted path is a major source of validated
methods.

Untargeted foundations to reuse:

- `DiscoveryCandidate` joined by `candidate_id` as the primary seed-specificity
  evidence surface;
- `build_sample_local_owners` and `SampleLocalMS1Owner` as the pre-Backfill
  owner geometry surface;
- `cluster_sample_local_owners` and `OwnerAlignedFeature` as the starting
  identity-family grouping surface;
- ambiguous-owner and duplicate-owner signals as seed specificity and
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
- seed specificity metrics derived before Backfill;
- trace identity / shape metrics derived from diagnostic candidate traces;

Validation-only evidence:

- targeted ISTD benchmark/control labels and positive-control classes;
- targeted benchmark diagnostics emitted by `tools/diagnostics/*`;
- current production `production_decisions`, `matrix_identity`, and workbook
  outputs;
- post-hoc `alignment-dir` joins used only for comparison/reporting.

Validation-only evidence may appear in summary tables, benchmark sections, and
positive-control columns. It must not change `decision`,
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

## Discriminator Model

V0.3 promotion requires three layers. A candidate that fails any blocking layer
stays Review-only.

```text
medium seed specificity
  -> RT-local candidate trace retrieval
  -> independent trace identity checks
  -> diagnostic would-primary / review-only decision
```

### Layer 1: Seed Specificity

Seed qualification is the load-bearing gate. In V0.3 the seed-specificity
surface is:

```text
SampleLocalMS1Owner geometry
  + DiscoveryCandidate joined by primary_identity_event.candidate_id
```

`SampleLocalMS1Owner` keeps the pre-Backfill owner peak and identity event, but
it does not carry every discovery scoring field. Inline mode must therefore
retain a candidate lookup keyed by `candidate_id`. A missing join is Review-only
because the diagnostic cannot audit seed specificity.

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
- `abs(ms1_seed_delta_min) <= seed_ms1_delta_max_min` when the joined
  `DiscoveryCandidate` provides the field;
- `ms1_trace_quality` is not a poor/missing quality label;
- `ms1_scan_support_score >= seed_min_scan_support_score` when a numeric score
  is available.

`high evidence score` is not required as a blanket rule, but low-specificity
seeds cannot be rescued by recurrence alone.

Baseline seed-specificity parameters:

| Parameter | Default | Source | Meaning |
| --- | ---: | --- | --- |
| `seed_ms1_delta_max_min` | `0.20` | `DiscoverySettings.ms1_search_padding_min` | Max MS1 apex to MS2 seed RT delta for seed coherence. |
| `seed_min_scan_support_score` | `0.50` | `AlignmentConfig.anchor_min_scan_support_score` | Minimum numeric scan support when available. |
| `poor_ms1_trace_quality_labels` | `POOR, MISSING` | discovery evidence semantics | Labels that force low specificity when numeric scan support is absent or poor. |

Context fields recorded but not used as hard gates before 8RAW review:

```text
neutral_loss_mass_error_ppm
matched_tag_count
tag_intersection_status
evidence_score
evidence_tier
```

These fields may split high vs medium reporting labels, but both high and medium
can support V0.3 promotion. Only `low_specificity` blocks promotion.

Required seed diagnostic fields:

```text
seed_specificity_class =
  high_specificity | medium_specificity | low_specificity

seed_reject_reason =
  missing_fragment_evidence
  no_quantifiable_owner
  missing_discovery_candidate_join
  ambiguous_owner
  duplicate_loser
  backfill_only_evidence
  nonfinite_peak
  seed_rt_outside_owner_peak
  ms1_seed_delta_out_of_bounds
  poor_ms1_trace_quality
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
tier 1: rt + fragment_match
tier 2: rt + shape_similarity
tier 3: rt + prototype_width
```

Tier 1 is available when that sample has pre-Backfill MS2/NL evidence matching
the row identity: neutral-loss tag, product m/z, and observed loss all remain
inside tolerance.

Tier 2 is available when enough XIC points exist to compare normalized local
shape against the seed or group prototype.

Tier 3 is a fallback. Width must be compared to a prototype width, defined as
the median width of complete candidates used for the stable provisional center,
not only to the seed sample width. A single co-eluted seed peak must not become
the reference width for every sample.

Baseline/interference and area/height pattern are review flags in V0.3. They
must not admit a cell as promotion evidence by themselves. Flat area patterns
can describe either stable controls or background, so area-pattern flatness is
not an identity basis without a separate biological expectation model.

A row can be `would_primary_independent_identity_support` only if at least one
non-seed coherent sample is admitted by tier 1 or tier 2. Tier-3-only rows are
Review-only weak-basis rows for V0.3.

Required cell evidence category:

```text
cell_identity_basis =
  seed_sample
  tier1_rt_fragment_match
  tier2_rt_shape_similarity
  tier3_rt_prototype_width
  rt_only_review_only
  blocked_infrastructure
  data_quality_reject
```

`rt_only_review_only` is never allowed to support would-primary.
Baseline and area-pattern concerns must be emitted as review flags, not as
`cell_identity_basis`.

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
low_specificity or blocked seed
  -> no Layer 2 cross-sample XIC retrieval
```

Required counters:

```text
layer1_candidate_count
layer1_low_specificity_count
layer1_blocked_count
layer2_xic_request_count
raw_chromatogram_call_count
xic_point_count
wall_time_sec
per_raw_xic_request_count
```

If an MS1 scan-index or approximate fast path is used, it must be marked as an
explicit approximate diagnostic mode. It must not silently replace vendor XIC as
an equivalent path.

## Positive Controls And Yardsticks

V0.3 must include a cheap positive-control yardstick before interpreting 8RAW
results.

Required if available:

- targeted ISTD benchmark output from existing `tools/diagnostics/targeted_istd_benchmark.py`;
- selected stable-like ISTD or targeted control rows mapped to untargeted
  candidate families;
- expected outcome for each control:
  - pass seed specificity where applicable;
  - pass trace identity checks;
  - explain misses explicitly when not promoted.

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
seed_specificity_class
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
fragment_confirmed_sample_count
weak_basis_only
background_recurrence_pattern
rt_only_candidate_count
blocked_infrastructure_count
data_quality_reject_count
forbidden_evidence_seen
positive_control_class
positive_control_expected_decision
notes
```

Decision enum:

```text
would_primary_independent_identity_support
review_only_low_seed_specificity
review_only_rt_only_support
review_only_insufficient_support
review_only_center_unstable
review_only_background_recurrence_pattern
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
rt_delta_center_sec
rt_gate_result
identity_basis_tier
non_rt_identity_basis
non_rt_identity_result
fragment_match_status
shape_similarity_status
prototype_width_status
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
`would_primary_independent_identity_support` unless 8RAW review explicitly
changes this contract.

### Required `summary.md` Sections

- command and mode;
- inline pre-Backfill input source or explicit reason a post-hoc run is
  comparison-only;
- input hashes and row counts;
- positive-control artifact and mapped control rows;
- evidence firewall assertion;
- seed specificity counts;
- RT-only candidate counts;
- independent trace identity pass counts by tier;
- fragment-confirmed sample counts;
- weak-basis-only row counts;
- per-sample evidence coverage and missing-basis counts;
- infrastructure-blocked counts;
- data-quality reject counts;
- threshold count and fraction summaries;
- RAW/XIC request, point, per-RAW, and timing counters;
- positive-control mapping counts and ambiguous/unmapped controls;
- Go / No-Go / Pivot table.

## CLI / Invocation Contract

Preferred inline mode:

```powershell
python scripts\run_alignment.py `
  <existing args> `
  --emit-identity-coherence-diagnostic `
  --identity-coherence-output-dir <diagnostic_output_dir>
```

Equivalent diagnostic module mode is acceptable only if it consumes an explicit
pre-Backfill owner-state export produced before `owner_backfill`:

```powershell
python -m tools.diagnostics.untargeted_identity_coherence `
  --pre-backfill-owner-state <owner_state.jsonl> `
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

## Failure Modes That Must Be Explainable

Infrastructure-blocked:

- missing required input file;
- missing required input column;
- missing RAW source;
- RAW extraction error;
- process worker failure;
- malformed pre-Backfill owner-state export.

Data-quality or identity rejects:

- missing fragment evidence;
- low seed specificity from seed-owner evidence;
- missing discovery-candidate join;
- seed RT outside owner peak;
- MS1 seed delta outside seed-specificity bounds;
- poor MS1 trace quality;
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
| Positive-control ISTD/stable rows pass with independent identity support | Proceed to 85RAW threshold-policy review. |
| Controls fail because only RT support is present | No-Go; add trace identity metrics before continuing. |
| Low-specificity seeds become would-primary through recurrence | No-Go; fix seed-specificity gate. |
| Rows are promoted by broad cross-sample background recurrence | No-Go; tighten background recurrence guard. |
| Most would-primary rows are admitted only by tier 3 width fallback | Pivot; require fragment/shape support or revise identity basis. |
| Any row is promoted by Backfill/rescued evidence | No-Go; fix evidence firewall. |
| Most would-primary rows are `rt_only_review_only` before non-RT checks | Pivot to shape/trace scoring before expanding scope. |
| 8RAW threshold looks good but fraction would be trivial in 85RAW | Define count+fraction policy before 85RAW. |
| Multi-seed/overflow dominates candidate decisions | Pivot to Phase 2 graph merge/split spec. |
| RAW/XIC request count projects poorly to 85RAW | Add request-budget/locality design before 85RAW. |
| Infrastructure-blocked count is high | Fix run/input infrastructure before scientific interpretation. |

## Acceptance Criteria Before Implementation

This spec is ready for implementation only after review signs off on:

- the method difference from Backfill is explicit and accepted;
- seed specificity uses `DiscoveryCandidate` joined by `candidate_id` plus
  `SampleLocalMS1Owner` geometry;
- low-specificity seed gates are defined in terms of seed-owner RT co-location,
  MS1 seed delta, trace quality, and scan support;
- background recurrence is a post-scan decision pattern, not a seed class;
- tiered non-RT identity checks are defined in V0.3 MVP;
- 8RAW and 85RAW threshold policies are separated;
- seed sample counting is explicit (`seed + at least 2 non-seed` for 8RAW);
- targeted ISTD/control rows are named or a benchmark artifact is provided;
- positive-control mapping criteria and ambiguous/unmapped counts are defined;
- RAW/XIC request counters are first-class and Layer 1 rejects skip Layer 2 XIC;
- inline pre-Backfill data flow is accepted as the primary path;
- output scope is limited to `decisions.tsv`, `cell_evidence.tsv`, and
  `summary.md` as frozen contracts for the first run.

## Review Questions

1. Are the hard low-specificity gates strict enough for 8RAW without requiring
   a high evidence score?
2. Is tier-3-only support correctly Review-only for V0.3?
3. Which targeted ISTD or stable rows should be the 8RAW positive controls?
4. Is `seed + 2 non-seed coherent samples` the right 8RAW support threshold?
5. What count+fraction policy should be reviewed before 85RAW?
6. Is post-hoc `alignment-dir` mode acceptable only as comparison/reporting?
