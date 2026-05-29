# Tier 2 V0 Coherence Criteria Review Design

## Verdict

Gate label: `diagnostic_only`.

This design reviews the criteria behind
`tier2_trace_identity_rescued_coherence_v0`. It does not promote retained
provisional rows, does not change `alignment_matrix.tsv`, and does not make the
Tier 2 RAW trace producer production-ready.

The immediate goal is to decide which v0 metrics are credible positive-support
criteria, which should remain challenge evidence, and which should be demoted to
context until a stronger oracle exists.

## Roadmap Placement

This work advances `EvidenceVector` and `AuditTrail` semantics for Tier 2
backfill review. It does not advance `Trace` / `TraceGroup` models,
multi-source `PeakHypothesis`, `IntegrationResult`, or production model
selection.

## Current Context

The RAW trace re-read producer checkpoint is implemented and committed as a
diagnostic sidecar producer. The current 8RAW smoke produced paired sidecars and
gate output, but no positive Tier 2 support:

```text
producer summary: diagnostic_only 7 7 0 4 0 3 0 False False
producer evidence_status: blocked=4, inconclusive=3
gate summary: diagnostic_only 7 0 False False
gate status: audit=7
```

Observed producer blockers:

- `metric_unavailable;weak_scan_support`: 1 row
- `metric_unavailable;low_scan_support`: 1 row
- `metric_unavailable`: 1 row
- `rescued_boundary_overlap_low`: 1 row
- `rescued_apex_span_wide;rescued_boundary_overlap_low`: 3 rows

This is enough to prove the producer and gate are observable. It is not enough
to prove the criteria are biologically or chromatographically right.

## Decision This Phase Can Close

This phase can close whether the current v0 coherence criteria are internally
coherent enough to remain a `validated_tier2_trace_evidence` gate candidate.

It cannot close production promotion, broad 85RAW readiness, or final matrix
inclusion. Those require a later reviewed plan and separate promotion contract.

Strongest existing oracle:

- the current 8RAW Tier 2 trace evidence sidecar;
- the paired RAW manifest and source artifact hashes;
- the candidate gate consume output proving that no validated support currently
  passes.

Missing independent evidence:

- signal/shape/noise evidence inside the re-read trace region;
- an explicit boundary reference policy for rescued cells;
- drift-aware interpretation of apex span;
- a real neighbor-interference computation.

## Review Focus

### 1. `scan_support_score`

Current behavior:

- effectively `len(scans_in_boundary) / scans_target`, capped at 1.0;
- requires a positive apex;
- does not inspect shape, local signal, baseline noise, or area support.

Concern:

A scan-count ratio can pass for a broad, low-information, noisy, or flat trace.
It can also fail a narrow but clean peak if scan density is low. By itself, it
does not prove identity or coherence.

Design direction:

- keep `trace_scan_count` as an availability denominator;
- split `scan_support_score` into explicit sub-metrics before treating it as
  positive support:
  - scan count / density;
  - signal or local signal-to-noise proxy;
  - shape or apex prominence proxy;
  - optional area support proxy.
- until those sub-metrics exist, scan support should be treated as availability
  plus challenge evidence, not a standalone positive-support gate.

### 2. `rescued_boundary_overlap_min`

Current behavior:

- computes minimum seed-vs-rescued boundary overlap;
- denominator is the larger of the two compared boundary widths.

Concern:

Seed-vs-rescued overlap assumes the seed boundary is the correct reference. That
may be false when the single detected seed is locally shifted, clipped, or
matrix-specific. Pairwise rescued overlap and family consensus may be better
tests of whether rescued cells agree with each other.

Design direction:

Compute and export three boundary-reference views:

- `seed_rescued_boundary_overlap_min`;
- `rescued_pairwise_boundary_overlap_min`;
- `family_consensus_boundary_overlap_min`.

The review should not pick a hard gate until the 8RAW rows show which reference
explains the current blockers. If the three views disagree, the row should stay
`diagnostic_only` with explicit context rather than force a positive decision.

### 3. `rescued_apex_rt_span_sec`

Current behavior:

- computes max-min apex RT span across seed plus supported rescued cells;
- hard blocker when the span is greater than 21.0 seconds.

Concern:

A fixed 21-second span may over-penalize real RT drift, sample-local matrix
effects, or batch-local behavior. It also mixes two questions: whether the
rescued cells agree with each other, and whether the seed belongs to the same
RT neighborhood.

Design direction:

- keep raw apex span as context;
- add separate seed-to-rescued and rescued-only apex span views;
- evaluate a drift-normalized or sample-local reference before using apex span
  as a hard positive-support gate;
- in v0.1, apex span should be a warning/challenge metric unless review shows
  it catches false positives without suppressing plausible matrix-specific
  behavior.

### 4. `neighbor_interference_ratio`

Current behavior:

- the producer does not calculate the ratio;
- blank values are valid only with `neighbor_interference_not_assessed`;
- a nonblank value greater than 0.33 is a hard blocker.

Concern:

An uncomputed metric should not be part of the positive criteria. Keeping it as
a hard positive-support dependency creates a false sense of evidence maturity.

Design direction:

- move neighbor interference out of v0 positive criteria until a formal
  computation exists;
- keep `neighbor_interference_not_assessed` as dependent context;
- define the later computation before reintroducing it as a gate:
  - search window;
  - m/z relationship to the candidate trace;
  - denominator, height or area basis;
  - minimum scans or signal required for assessment;
  - mapping for unavailable, low-confidence, and high-interference cases.

## Proposed V0.1 Posture

V0.1 should separate observable facts from positive-support facts:

| Metric area | V0.1 posture |
|---|---|
| Scan count | availability denominator and challenge evidence |
| Signal / shape / noise | required new context before scan support can become positive support |
| Boundary overlap | compute seed-vs-rescued, rescued-pairwise, and family-consensus views before choosing a hard gate |
| Apex span | context or warning unless drift-normalized evidence justifies a hard gate |
| Neighbor interference | context only until formally computed |

The current criteria version may remain allowlisted for existing diagnostic
artifacts, but a revised criteria contract should use a new criteria version if
any positive-support rule changes.

## Evidence Plan

Now:

- audit the current 8RAW sidecar rows;
- summarize each blocker against the four focus areas;
- inspect whether current blockers are caused by unavailable metrics,
  questionable thresholds, or genuine contradiction;
- draft v0.1 metric columns and status mapping without changing production
  behavior.

Later:

- implement additional diagnostic columns only after a reviewed implementation
  plan;
- rerun 8RAW to compare v0 and v0.1 sidecar labels;
- run 85RAW only after the v0.1 review plan explains what decision the larger
  run can close.

Not in scope:

- product promotion;
- changing `alignment_matrix.tsv`;
- accepting direct review-row Tier 2 tokens as positive support;
- broad Tier 2 evaluation for all provisional rows;
- running 85RAW from this spec alone.

## Acceptance Criteria

The criteria review is complete when:

- every current 8RAW blocker is assigned to one of four causes:
  `metric_unavailable`, insufficient signal/shape evidence, boundary-reference
  ambiguity, or drift/interference policy gap;
- the spec or follow-up plan states which v0 metrics remain hard gates, which
  become context, and which need new columns;
- no conclusion claims `production_ready`;
- the next implementation plan can be tested with unit fixtures plus an 8RAW
  diagnostic rerun;
- any revised positive-support logic receives a new criteria version.

## Fail-Fast And Inconclusive Rules

Stop before implementation if the 8RAW sidecar cannot be loaded or does not
match the committed producer/gate hashes. A stale sidecar cannot justify
criteria changes.

Return `inconclusive` rather than tuning thresholds if the current rows do not
contain enough trace context to distinguish poor criteria from poor data.

Kill or externalize the producer if the added metrics still only restate
owner-backfill provenance and cannot discriminate identity/coherence decisions.

## Review Risks

Strongest assumption: the 8RAW retained-candidate subset is small but still
representative enough to identify criteria failure modes. It is useful for
design review, not production acceptance.

Stale-artifact risk: this review relies on the current
`output\tier2_raw_trace_reread_8raw_current` artifacts and the committed
diagnostic producer checkpoint. Any later code change should rerun 8RAW before
claiming criteria results.

Bias risk: current rows are retained provisional candidates, not a random sample
of all provisional discoveries. A criterion that behaves well here may still be
biased toward one rescued-row class.

## Next Artifact

If this design is approved, write an implementation plan for a
`diagnostic_only` v0 coherence criteria review checkpoint. The plan should
prefer checkpoint mode. Subagent-driven development is optional only if the plan
creates separable read-only review and implementation scopes.
