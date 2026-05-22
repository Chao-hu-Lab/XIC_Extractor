# Untargeted Identity Coherence Core Spec

**Date:** 2026-05-22
**Status:** Split review draft v0.4

This spec defines identity-family formation only. It depends on the overview:

- [Overview](2026-05-22-untargeted-identity-coherence-prototype-spec.md)

Validation controls and engineering surfaces are separate:

- [Controls spec](2026-05-22-untargeted-identity-coherence-controls-spec.md)
- [Implementation contract](2026-05-22-untargeted-identity-coherence-implementation-contract.md)
- [Downstream audit boundary](2026-05-22-untargeted-identity-coherence-downstream-audit-boundary.md)

## Purpose

The core identity layer decides whether pre-Backfill evidence supports a
provisional identity family. It may suppress false independent features such as
duplicate activations, duplicate-owner losers, and RT-drifted observations that
belong to an existing family.

It must not perform final-matrix filtering, area correction, normalization,
imputation, or statistical eligibility decisions.

## Inputs

Allowed identity inputs:

- `DiscoveryCandidate`, joined by `candidate_id`;
- `SampleLocalMS1Owner` geometry from pre-Backfill ownership;
- `OwnerAlignedFeature` / owner grouping context before `owner_backfill`;
- diagnostic XIC traces collected before Backfill;
- typed identity configuration supplied by the implementation layer.

Validation-only inputs such as targeted ISTD labels or decoys may be used only
by the controls spec to evaluate decisions. They cannot promote a row.

## Identity Request Contract

The diagnostic evaluates an `IdentityCoherenceRequest`, not only a joined
`DiscoveryCandidate`. In normal inline mode, each seed `DiscoveryCandidate`
emits one seed-level request. V0.4 does not create family-level requests; any
case that needs multiple seed requests to define one identity is
`review_only_multi_seed_requires_phase2`.

The request owns one normalized `FragmentIdentity`. `FragmentIdentity` is the
shared abstraction for CID neutral-loss evidence, HCD base-product evidence, and
future HCD-observed neutral-loss evidence. The current executable v0.4 mode is:

```text
fragment_observation_mode = cid_neutral_loss
```

HCD is not a separate future identity pipeline. It must enter as another
fragment observation mode with its own typed mode-specific constraint.

The implementation contract is the schema single source of truth for the
domain model and TSV projection. The core spec owns the behavior:

- Layer 1 must verify request identity constraints against the joined candidate
  evidence;
- `candidate_id` is provenance, not identity proof;
- incomplete requests or unsupported modes cannot become `coherent_seed`.

`FragmentIdentity` uses a common identity surface plus typed mode payload:

```text
FragmentIdentity
  common:
    fragment_observation_mode
    precursor_mz
    product_mz
    fragment_tags
    fragment_tag_match_policy
    precursor_tolerance_ppm
    product_tolerance_ppm
    fragment_profile_id
    fragment_profile_hash

  mode_specific:
    cid_neutral_loss:
      cid_observed_loss_da
      cid_observed_loss_tolerance_ppm
```

Required v0.4 fields for seed coherence:

- `fragment_observation_mode = cid_neutral_loss`;
- `precursor_mz`;
- `product_mz`;
- `fragment_tags`;
- `precursor_tolerance_ppm`;
- `product_tolerance_ppm`;
- `cid_observed_loss_da`;
- `cid_observed_loss_tolerance_ppm`.

All mass/loss gates use ppm. Da loss error may be emitted as review context,
but a request with only a Da tolerance cannot become `coherent_seed`.

`fragment_tags` output format:

```text
tagA|tagB|tagC
```

Rules:

- normalize with one helper shared by request and candidate evidence;
- trim whitespace and preserve exact case;
- do not case-fold or merge case-only variants;
- stable unique ordering for TSV output;
- empty tag after trim is invalid;
- if case-only variants are seen, emit `fragment_tag_case_variant_seen`;
- `fragment_tag_match_policy = all_request_tags_supported`;
- all request tags are required for seed consistency and tier 1 non-seed
  diagnostic fragment support.

Legacy discovery fields such as `matched_tag_names` and `neutral_loss_tag` are
adapter inputs only. The request builder may read them; Layer 1 and later
domain logic must read only normalized `FragmentIdentity`.

Profile-level identity may support `fragment_tags` only when the profile
deterministically expands to the requested tag set in this diagnostic context.
If a profile cannot be expanded, the seed lacks auditable diagnostic fragment
evidence.

`fragment_profile_hash` is required on the request audit surface for
traceability. If the current profile system cannot provide a stable hash, emit
`fragment_profile_hash = unavailable` and add
`fragment_profile_hash_unavailable` to request review flags. Missing profile
hash does not fail the seed gate.

`candidate_id` is a provenance join key. It retrieves the pre-Backfill
`DiscoveryCandidate`, but it does not prove that the candidate satisfies the
request identity. Layer 1 must compare the request identity constraints with
the joined candidate evidence before the seed can become `coherent_seed`.

This is required for identity decoys: a decoy may preserve provenance while
changing the declared identity request, and the mismatch must be rejected by the
core seed gate rather than silently satisfied by the original candidate.

Request status:

```text
request_identity_completeness_status =
  complete |
  missing_fragment_observation_mode |
  missing_precursor_mz |
  missing_product_mz |
  missing_fragment_tags |
  missing_mode_specific_constraint

request_candidate_identity_status =
  not_assessed |
  match |
  missing_discovery_candidate_join |
  missing_diagnostic_fragment_evidence |
  request_candidate_identity_mismatch |
  unsupported_fragment_observation_mode
```

`request_candidate_identity_status = not_assessed` is allowed only when the
request is incomplete or the candidate join is missing. If the request is
complete and a candidate is joined, the candidate identity status must resolve
to a concrete evidence/match status. `unsupported_fragment_observation_mode` is
Review-only and cannot become `coherent_seed`.

Seed gate failure order:

1. missing request required field -> `missing_request_identity_constraint`;
2. unsupported request mode -> `unsupported_fragment_observation_mode`;
3. missing candidate join -> `missing_discovery_candidate_join`;
4. joined candidate lacks required diagnostic fragment evidence field or
   unexpandable profile evidence -> `missing_diagnostic_fragment_evidence`;
5. request and joined candidate are complete but outside ppm tolerance or tag
   set mismatch -> `request_candidate_identity_mismatch`.

## Layer 1: Seed Coherence Gate And Specificity Context

The seed gate establishes seed-owner coherence, quantifiability, and sampling
sufficiency. It is not a complete seed specificity classifier.

Minimum v0.4 seed requirements:

- request identity completeness status is `complete`;
- a `DiscoveryCandidate` join exists for the owner identity event;
- request-declared precursor m/z, product m/z, fragment tag set, and
  mode-specific fragment constraint match the joined candidate within the
  request ppm tolerances;
- the candidate has diagnostic fragment evidence within declared ppm
  tolerances;
- a pre-Backfill sample-local MS1 owner exists;
- owner apex, start RT, end RT, area, and height are finite;
- `best_seed_rt` lies inside the owner peak boundaries;
- owner is not ambiguous and not a duplicate loser;
- `ms1_scan_support_score >= seed_min_ms1_scan_support_score` when available.

Record-only seed context:

```text
ms1_seed_delta_min
ms1_trace_quality
fragment_mass_error_ppm
matched_tag_count
tag_intersection_status
evidence_score
evidence_tier
ms2_support
ms1_support
rt_alignment
family_context
```

`evidence_score` and `evidence_tier` are review-ranking context. They are not
identity-promotion gates unless a future diagnostic-owned seed-specificity rule
is explicitly defined.

Seed output:

```text
seed_gate_class =
  coherent_seed | review_only_seed_gate_failed | blocked_seed

seed_reject_reason =
  missing_request_identity_constraint
  no_quantifiable_owner
  missing_discovery_candidate_join
  missing_diagnostic_fragment_evidence
  ambiguous_owner
  duplicate_loser
  backfill_only_evidence
  nonfinite_peak
  seed_rt_outside_owner_peak
  low_ms1_scan_support
  request_candidate_identity_mismatch
  unsupported_fragment_observation_mode
  overflow_or_multi_seed_requires_phase2
```

## Layer 2: RT-Local Candidate Retrieval

XIC retrieval collects candidate traces. It is not promotion evidence by
itself.

The broad retrieval window may use `max_rt_sec = 180`. Final RT acceptance uses
the tighter `preferred_rt_sec = 60` after the independent trace checks below.

Layer 1 rejects and blocked seeds must not trigger Layer 2 cross-sample XIC
retrieval.

## RT Center Rules

The seed sample anchors the first provisional center.

For v0.4:

- non-seed candidates can contribute to a recentered provisional center only
  after basic morphology completeness;
- candidates farther than `seed_center_candidate_sec` from the seed RT are not
  used to estimate the center;
- center is the median apex RT of complete accepted center candidates;
- `max_center_drift_sec` must be tighter than `preferred_rt_sec`;
- unstable or mixed centers are Review-only.

Default review values:

| Parameter | Default | Unit | Meaning |
| --- | ---: | --- | --- |
| `max_rt_sec` | 180 | seconds | Broad retrieval window. |
| `preferred_rt_sec` | 60 | seconds | Final RT acceptance gate. |
| `seed_center_candidate_sec` | 30 | seconds | Max seed distance for center-estimation candidates. |
| `max_center_drift_sec` | 30 | seconds | Seed-anchor guard, tighter than final RT gate. |

Promotion must report:

```text
center_method
center_candidate_count
center_drift_sec
center_decision =
  seed_anchored | recentered_stable | center_unstable_review_only
```

## Layer 3: Tiered Identity Checks

Every non-seed sample that contributes to would-primary must pass RT plus a
tiered non-RT identity basis.

```text
tier 1: rt + diagnostic_fragment_support
tier 2: rt + shape_similarity
tier 3: rt + prototype_width
```

### Tier 1: Diagnostic Fragment Support

Tier 1 is diagnostic fragment support, not library-grade MS/MS confirmation. It
supports only provisional identity-family coherence.

Minimum tier 1 join criteria:

- same non-seed sample;
- all `fragment_tags` are supported by the non-seed diagnostic candidate, or by
  a deterministic profile expansion to the same tag set;
- precursor m/z, product m/z, and mode-specific fragment constraints remain
  inside declared ppm tolerances, with ppm errors recorded per cell;
- matched candidate is pre-Backfill discovery evidence, not `owner_backfill`
  rescue output;
- collision energy, instrument mode, and source profile are recorded when
  available;
- precursor isolation or coelution ambiguity is recorded as a review flag when
  available.

Ambiguous tier 1 matches must not silently promote a cell. Tie-break:

1. same fragment tag set plus smallest absolute precursor ppm error;
2. smallest absolute mode-specific fragment ppm error;
3. closest apex RT to row center;
4. if still tied, mark `fragment_match_status = ambiguous` and do not use the
   cell as promotion evidence.

### Tier 2: Shape Similarity

Tier 2 is available when enough XIC points exist to compare normalized local
shape against a prototype shape reference. V0.4 uses prototype medoid first and
seed shape only as an explicitly flagged fallback.

Shape reference methods:

```text
shape_reference_method =
  prototype_medoid | seed_shape_fallback | not_available

shape_reference_basis =
  tier1_supported_medoid | morphology_rt_medoid | seed_fallback

shape_alignment_method = boundary_normalized_linear_resample
```

Forbidden shape alignment methods:

```text
dynamic_time_warping
free_shift_cross_correlation
```

Prototype shape candidate pool:

- pre-Backfill candidate trace only;
- RT gate pass after final center;
- finite apex, start, end, area, height;
- `candidate_area > 0` and `candidate_height > 0`;
- valid boundary ordering `start < apex < end`;
- `candidate_point_count >= shape_min_points` inside its own peak boundaries;
- not duplicate loser;
- not ambiguous owner;
- not blocked infrastructure;
- not data-quality reject.

The seed trace may be included in the prototype shape candidate pool, but the
prototype cannot be seed-only. V0.4 requires:

```text
min_prototype_shape_candidates = 3
min_non_seed_prototype_shape_candidates = 2
```

Prototype reference construction:

1. Normalize and resample every prototype candidate trace.
2. Compute pairwise cosine similarity.
3. Pick the candidate with the highest average similarity as medoid.
4. Tie-break by tier 1 diagnostic fragment support, then higher scan support, then
   closest apex RT to row center.
5. Record `shape_reference_candidate_id`.

The prototype pool is not limited to tier 1 cells. If tier 1 candidates are
available, they are preferred in medoid tie-breaks and reported through
`shape_reference_basis = tier1_supported_medoid`. If no tier 1 medoid is
available, `morphology_rt_medoid` may still support provisional would-primary,
but it is a weaker support class and must be summarized separately.

V0.4 shape contract:

- both traces must have at least `shape_min_points` points inside peak
  boundaries;
- use each candidate's own original peak boundaries, not a common RT window;
- subtract local minimum intensity inside peak boundaries and clip at zero;
- normalize each trace to unit L2 norm after baseline subtraction;
- resample both traces to `shape_resample_points` over normalized RT positions;
- compute cosine similarity on resampled vectors;
- pass when `shape_similarity_score >= shape_similarity_min_cosine`;
- pass requires `width_sanity_status = pass`;
- emit review flags for low points, zero signal, shoulder/bimodal audit, or
  baseline incompatibility when available.

Shape similarity is intensity-invariant. Area and intensity pattern are review
context only, not promotion basis.

`shape_min_points = 7`, `shape_resample_points = 25`, and
`shape_similarity_min_cosine = 0.85` are V0.4 initial diagnostic values, not
validated final constants. Resampling does not rescue low raw point count.

If a reliable shape audit marks shoulder, bimodal, coelution, saturated, or
clipped trace, shape fails. If shape audit is unavailable, emit
`shape_audit_unavailable`; do not pretend that audit gate ran.

Width sanity uses the same prototype median width and ratio range as the Tier 3
width fallback, but it is an anti-pathology guard for Tier 2, not promotion
evidence:

```text
width_sanity_status = pass | fail | not_assessed
```

Tier 1 diagnostic fragment support is not hard-failed by width sanity. If a tier 1
cell has `width_sanity_status = fail`, keep tier 1 support but add
`width_sanity_failed_on_tier1_cell` and report the count.

If the metric cannot be calculated, emit
`shape_similarity_status = not_assessed`; it must not support promotion.

Seed shape fallback:

- seed fallback can count as tier 2 only when prototype medoid is unavailable;
- every seed fallback pass must set `shape_seed_fallback_used = true`;
- would-primary cannot rely only on seed fallback shape cells;
- at least one non-seed tier 1 cell or one non-seed prototype-medoid tier 2 cell
  is required when seed fallback contributes to the two non-seed tier1/tier2
  minimum.

### Tier 3: Prototype Width Fallback

Tier 3 is a fallback. Width is compared to a prototype width, not only to the
seed sample width.

Prototype width inputs:

- pre-Backfill candidates with finite apex, start, end, area, and height;
- candidate passes RT gate and morphology completeness;
- candidate is inside `seed_center_candidate_sec` of the seed RT before
  recentering;
- at least `prototype_width_min_candidates` candidates are required;
- otherwise `prototype_width_status = not_assessed`.

Tier 3 passes only when the candidate width divided by prototype median width
is inside `prototype_width_ratio_min..prototype_width_ratio_max`.

Tier 3 contributes to `total_coherent_sample_count`. It does not contribute to
`tier12_non_seed_identity_sample_count` and cannot satisfy
`min_non_seed_tier12_identity_samples`.

Tier 3 may contribute to audit counts, but it must not be the filler that turns
one tier-1/tier-2 cell into would-primary.

## Would-Primary Rule

Default 8RAW support thresholds:

```text
min_total_coherent_samples = 3
seed_counts_toward_total = true
min_non_seed_coherent_samples = 2
min_non_seed_tier12_identity_samples = 2
```

A row can be `would_primary_provisional_identity_family_support` only if at
least `min_non_seed_tier12_identity_samples` non-seed coherent samples are
admitted by tier 1 or tier 2.

Review-only weak-basis cases:

- RT-only support;
- tier-3-only support;
- `seed + 1 tier1/tier2 + 1 tier3`;
- `seed + 2 seed_shape_fallback tier2` with no tier 1 and no prototype-medoid
  tier 2;
- center unstable;
- multi-seed ambiguity requiring Phase 2.

Allowed would-primary tier compositions include:

- `seed + 2 non-seed tier1`;
- `seed + 1 non-seed tier1 + 1 non-seed prototype-shape tier2`;
- `seed + 2 non-seed prototype-shape tier2`;
- `seed + 1 non-seed prototype-shape tier2 + 1 non-seed seed-shape-fallback
  tier2`;
- `seed + 1 non-seed tier1 + 1 non-seed seed-shape-fallback tier2`.

`seed + 2 non-seed prototype-shape tier2` is provisional would-primary, but it
must be summarized as tier2-only support.

Required reporting:

```text
total_coherent_sample_count
non_seed_coherent_sample_count
tier12_non_seed_identity_sample_count
assessed_sample_count
coherent_sample_fraction
weak_basis_reason =
  none | tier3_only | single_tier12_plus_tier3 |
  seed_shape_fallback_only | rt_only
```

Count invariant:

```text
if tier12_non_seed_identity_sample_count >= 2
and seed_counts_toward_total = true
then total_coherent_sample_count >= 3
```

For 85RAW, the 8RAW threshold cannot be copied blindly. `3/8` and `3/85` have
different meaning. A reviewed count+fraction policy is required before 85RAW
interpretation.

## Core Identity Go / No-Go

The core spec owns identity-decision invariants. Engineering feasibility and
control pass rates are owned by the implementation and controls specs.

| Observation after 8RAW | Decision |
| --- | --- |
| Every would-primary satisfies `total_coherent_sample_count >= min_total_coherent_samples` | Proceed for identity-rule review. |
| Any would-primary violates `min_total_coherent_samples` | No-Go; the implementation promoted insufficient support. |
| Every would-primary satisfies `tier12_non_seed_identity_sample_count >= min_non_seed_tier12_identity_samples` | Proceed for identity-rule review. |
| Any would-primary violates `min_non_seed_tier12_identity_samples` | No-Go; the implementation promoted weak tier-3/RT-only support. |
| `forbidden_evidence_used_count = 0` | Proceed; identity decisions stayed inside the evidence firewall. |
| `forbidden_evidence_used_count > 0` | No-Go; identity promotion used Backfill/downstream evidence. |
| `seed_shape_fallback_only` appears only as a Review-only `weak_basis_reason` | Proceed. |
| `seed_shape_fallback_only` becomes would-primary's only tier-2 support class | No-Go; seed fallback was over-promoted. |
| `unsupported_fragment_observation_mode` never becomes `coherent_seed` | Proceed. |
| Any unsupported fragment mode becomes `coherent_seed` | No-Go; unsupported mode crossed the seed gate. |

## Decision Enum

```text
would_primary_provisional_identity_family_support
review_only_seed_gate_failed
review_only_rt_only_support
review_only_insufficient_support
review_only_center_unstable
review_only_weak_basis_tier3_only
review_only_weak_basis_single_tier12_plus_tier3
review_only_multi_seed_requires_phase2
blocked_infrastructure
```

Background / blank / QC audit must not add a row-decision enum here.

## Downstream Boundary Reference

A core identity decision is not final-matrix eligibility. Contaminant,
blank/QC, area-correction, normalization, and statistics consequences are owned
by the [downstream audit boundary](2026-05-22-untargeted-identity-coherence-downstream-audit-boundary.md).

## Acceptance Criteria

Core identity spec is ready when:

- seed gate uses `DiscoveryCandidate` joined by `candidate_id` plus
  `SampleLocalMS1Owner` geometry;
- seed gate verifies request-declared identity constraints against the joined
  candidate rather than treating `candidate_id` as identity proof;
- v0.4 executable fragment mode is `cid_neutral_loss`, with
  `cid_observed_loss_da` and `cid_observed_loss_tolerance_ppm` as typed
  mode-specific constraints;
- `fragment_tags` is a stable, case-sensitive, all-tags-required set;
- `ms1_seed_delta_min`, `ms1_trace_quality`, `evidence_score`, and
  `evidence_tier` are record-only context;
- tier 1 diagnostic fragment support, tier 2 prototype-medoid shape
  similarity with flagged seed fallback, and tier 3 prototype-width fallback are
  defined;
- tier 2 shape pass is intensity-invariant, uses boundary-normalized linear
  resampling, and requires width sanity;
- would-primary requires at least two non-seed tier-1/tier-2 cells for 8RAW;
- seed-shape-fallback-only support is Review-only through `weak_basis_reason`;
- false independent feature suppression is explicit and separate from
  downstream final-matrix filtering.
