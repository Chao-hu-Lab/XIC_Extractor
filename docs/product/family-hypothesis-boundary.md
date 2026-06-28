# Family And Hypothesis Boundary

This page defines the durable boundary between legacy family identifiers,
cross-sample group hypotheses, peak hypotheses, and product projections. Use it
when a change touches discovery grouping, alignment owner construction,
Backfill activation, or any matrix identity sidecar.

## Contract

- `family` and `feature_family_id` are compatibility and review containers.
  They help group related evidence, route review, and preserve public row
  traceability. They are not promotion units by themselves.
- `CrossSamplePeakGroupHypothesis` owns cross-sample group identity: membership,
  owner edge evidence, hard split gates, review-only records, and group delivery
  metadata.
- `PeakHypothesis` owns candidate chromatographic identity: the physical peak
  candidate, selected integration, typed evidence, and selected-hypothesis
  decision semantics.
- Workflow projection owns product decisions. Targeted projection, alignment
  projection, Backfill authority, and ProductWriter gates decide counted
  detection, matrix presence, and product output values.
- Legacy score, confidence, family role, and review tokens may rank, annotate,
  or preserve compatibility behavior. They must not become standalone product
  truth.

## Roles

| Concept | Owns | Must not own |
| --- | --- | --- |
| Discovery `feature_family_id` / `feature_superfamily_id` | Per-sample candidate grouping and review context | Cross-sample matrix identity, Backfill promotion, selected-peak truth |
| Alignment `public_family_id` / legacy `feature_family_id` | Stable public row label and compatibility traceability | Canonical identity proof when a group hypothesis exists |
| `CrossSamplePeakGroupHypothesis` | Cross-sample owner/group identity and successor group metadata | Per-peak integration truth or ProductWriter authority |
| `PeakHypothesis` | Candidate peak identity, evidence context, selected hypothesis semantics | Cross-sample grouping policy or final matrix writing |
| Product projection / ProductWriter | Counted detection, product state, matrix value authority | Low-level evidence extraction or review-only grouping |

## Migration Rule

The codebase is in a compatibility transition. Some legacy surfaces still expose
`feature_family_id` while newer sidecars also expose `group_hypothesis_id` or
`peak_hypothesis_id`. Treat this as an adapter state:

1. Preserve legacy IDs when they are public output contracts.
2. Add successor IDs alongside legacy IDs when identity semantics become
   product-relevant.
3. Do not collapse multiple source families into one product row unless an
   explicit split/consolidation contract and tests approve it.
4. Keep review-only family context out of ProductWriter authority unless it is
   converted into typed same-peak or group-hypothesis evidence.

## Design Red Lines

- Do not say "the score decides whether the peak is trustworthy." Say which
  evidence facts, selected hypothesis, and workflow projection own the decision.
- Do not use family membership as same-peak proof. Same-peak support needs a
  typed anchor, selected mode, or PeakHypothesis-level reason.
- Do not let `alignment_review.tsv` display tokens promote rows. Positive
  product support needs provenance-valid sidecars or explicit authority records.
- Do not treat `family_projection` rows as canonical identity proof. They are
  unresolved projection rows until replaced by explicit PeakHypothesis
  assignments or an approved product contract says they are out of scope.

## Codebase Smells To Audit

These patterns are not automatically bugs, but they require close review before
refactor or promotion:

- A family assignment function writes `evidence_score`, `evidence_tier`,
  confidence, or product-like status.
- A cross-sample alignment path keys product behavior only by
  `feature_family_id` when `group_hypothesis_id` or `peak_hypothesis_id` is
  available.
- A diagnostic sidecar exposes supportive labels without product-authority
  provenance.
- A new helper extracts shared code by moving discovery/alignment policy into
  `peak_detection/` instead of keeping the helper trace-level and role-neutral.

## Verification

Before changing family, owner, group-hypothesis, or PeakHypothesis behavior,
require the relevant subset of:

- focused tests for row identity, sidecar columns, and deterministic duplicate
  policy;
- expected-diff approval if selected peak, selected area, counted detection,
  matrix values, or product row identity can change;
- artifact provenance checks for Backfill evidence used as product support;
- RAW-tier evidence label matching the claim.

## See Also

- [Evidence spine](evidence-spine.md)
- [Alignment](alignment.md)
- [Backfill](backfill.md)
- [Peak model selection](peak-model-selection.md)
- [LC-MS/MS evidence rules](../lcms-msms-evidence-rules.md)
- [Architecture contract](../architecture-contract.md)
