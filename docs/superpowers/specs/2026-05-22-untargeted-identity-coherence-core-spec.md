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
`DiscoveryCandidate`.

The request owns the declared identity constraints:

```text
request_precursor_mz
request_product_mz
request_neutral_loss_tag_or_profile
request_observed_loss_da
request_tolerances
```

`candidate_id` is a provenance join key. It retrieves the pre-Backfill
`DiscoveryCandidate`, but it does not prove that the candidate satisfies the
request identity. Layer 1 must compare the request identity constraints with
the joined candidate evidence before the seed can become `coherent_seed`.

This is required for identity decoys: a decoy may preserve provenance while
changing the declared identity request, and the mismatch must be rejected by the
core seed gate rather than silently satisfied by the original candidate.

## Layer 1: Seed Coherence Gate And Specificity Context

The seed gate establishes seed-owner coherence, quantifiability, and sampling
sufficiency. It is not a complete seed specificity classifier.

Minimum v0.4 seed requirements:

- a `DiscoveryCandidate` join exists for the owner identity event;
- request-declared precursor m/z, product m/z, neutral-loss tag/profile, and
  observed loss match the joined candidate within the request tolerances;
- the candidate has diagnostic neutral-loss evidence within declared
  m/z/loss tolerances;
- a pre-Backfill sample-local MS1 owner exists;
- owner apex, start RT, end RT, area, and height are finite;
- `best_seed_rt` lies inside the owner peak boundaries;
- owner is not ambiguous and not a duplicate loser;
- `ms1_scan_support_score >= seed_min_ms1_scan_support_score` when available.

Record-only seed context:

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

`evidence_score` and `evidence_tier` are review-ranking context. They are not
identity-promotion gates unless a future diagnostic-owned seed-specificity rule
is explicitly defined.

Seed output:

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
  request_candidate_identity_mismatch
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
tier 1: rt + diagnostic_nl_support
tier 2: rt + shape_similarity
tier 3: rt + prototype_width
```

### Tier 1: Diagnostic Neutral-Loss Support

Tier 1 is diagnostic neutral-loss support, not library-grade MS/MS fragment
confirmation. It supports only provisional identity-family coherence.

Minimum tier 1 join criteria:

- same non-seed sample;
- same neutral-loss tag or declared profile identity;
- precursor m/z, product m/z, and observed neutral loss remain inside declared
  tolerances, with ppm units recorded per cell;
- matched candidate is pre-Backfill discovery evidence, not `owner_backfill`
  rescue output;
- collision energy, instrument mode, and source profile are recorded when
  available;
- precursor isolation or coelution ambiguity is recorded as a review flag when
  available.

Ambiguous tier 1 matches must not silently promote a cell. Tie-break:

1. same neutral-loss tag plus smallest absolute precursor ppm error;
2. smallest absolute observed-loss ppm error;
3. closest apex RT to row center;
4. if still tied, mark `diagnostic_nl_status = ambiguous` and do not use the
   cell as promotion evidence.

### Tier 2: Shape Similarity

Tier 2 is available when enough XIC points exist to compare normalized local
shape against the seed or group prototype.

V0.4 shape contract:

- both traces must have at least `shape_min_points` points inside peak
  boundaries;
- subtract local minimum intensity inside peak boundaries and clip at zero;
- normalize each trace to unit L2 norm after baseline subtraction;
- resample both traces to `shape_resample_points` over normalized RT positions;
- compute cosine similarity on resampled vectors;
- pass when `shape_similarity_score >= shape_similarity_min_cosine`;
- emit review flags for low points, zero signal, shoulder/bimodal audit, or
  baseline incompatibility when available.

If the metric cannot be calculated, emit
`shape_similarity_status = not_assessed`; it must not support promotion.

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
- center unstable;
- multi-seed ambiguity requiring Phase 2.

Required reporting:

```text
total_coherent_sample_count
non_seed_coherent_sample_count
tier12_non_seed_identity_sample_count
assessed_sample_count
coherent_sample_fraction
weak_basis_reason =
  none | tier3_only | single_tier12_plus_tier3 | rt_only
```

For 85RAW, the 8RAW threshold cannot be copied blindly. `3/8` and `3/85` have
different meaning. A reviewed count+fraction policy is required before 85RAW
interpretation.

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
- `ms1_seed_delta_min`, `ms1_trace_quality`, `evidence_score`, and
  `evidence_tier` are record-only context;
- tier 1 diagnostic neutral-loss support, tier 2 shape similarity, and tier 3
  prototype-width fallback are defined;
- would-primary requires at least two non-seed tier-1/tier-2 cells for 8RAW;
- false independent feature suppression is explicit and separate from
  downstream final-matrix filtering.
