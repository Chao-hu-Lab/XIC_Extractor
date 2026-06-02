# C6 - Cross-Sample Peak Group Hypothesis Migration Contract Design

**Date:** 2026-06-02
**Status:** Implementation snapshot v0.8 — successor constructor migration
**Readiness label:** `production_candidate`
**Parent spec:** [C6 alignment stage semantics and value assessment](2026-06-01-c6-alignment-stage-semantics-value-assessment-design.md)
**Related contract:** `xic_extractor/alignment/owner_family_successor_contract.py`
**Product-flow reference:** [Mature package flow reference](2026-06-02-mature-package-flow-reference-spec.md)
**Closeout note:** [C4 / C6 / Region foundation closeout](../notes/2026-06-02-c4-c6-region-foundation-closeout.md)

## Verdict

C6 should stop treating `family` as the semantic center.

The product concept is not "this RT/mz region is one true family." The product
concept is:

```text
these sample-local peak observations may represent the same cross-sample peak,
and that claim can be supported, challenged, split, or demoted by evidence.
```

The first C6 slice introduced a shadow `CrossSamplePeakGroupHypothesis`
contract. The follow-up C6-M migration now makes that successor contract own
cross-sample owner-group construction internally. It is still not a
`CrossSampleFamily` contract and not the existing sample-local
`PeakHypothesis` model.

`FAM######` remains as a public/output compatibility row ID. It is not the
domain truth. `OwnerAlignedFeature` remains the active public delivery DTO for
downstream owner-backfill, matrix, claim, primary-consolidation, writer, and
process-payload consumers, but `owner_clustering.py` is now a compatibility
adapter candidate rather than the semantic construction owner.

The mature-package flow reference tightens the C6 endpoint: C6 is not complete
merely because construction can build successor hypotheses internally. The
end-to-end product flow is complete only when downstream grouping,
missing-observation query/backfill, matrix, claim registry, consolidation,
writer, and process-payload consumers either consume the successor group
contract directly or consume an explicit structural delivery adapter with
parity. Until then, `OwnerAlignedFeature` is active delivery compatibility, not
semantic ownership.

## Product Semantics

### Terms

| Term | Meaning |
| --- | --- |
| `CrossSamplePeakGroupHypothesis` | The internal successor owner-group membership claim that multiple sample-local owners may represent the same matrix-level peak group. It now owns constructor semantics before adapting back to the public `OwnerAlignedFeature` DTO. |
| sample-local `PeakHypothesis` | Existing `xic_extractor.peak_detection.hypotheses.PeakHypothesis`. It remains a per-trace/per-sample peak candidate and is not replaced by C6-A1. |
| shared-peak `peak_hypothesis_id` | Existing diagnostic/product-activation identity in `shared_peak_identity_explanation`. C6-A1 must not write, consume, or redefine it. |
| `public_family_id` | Existing `FAM######` row identity used by TSV/XLSX/output contracts. Compatibility ID only. |
| `OwnerAlignedFeature` | Current active public DTO returned by `cluster_sample_local_owners(...)` and consumed by backfill, matrix, claim, primary consolidation, and writers. It is compatibility delivery language after C6-M, not the semantic construction owner. |
| `family` | Legacy/output term. Do not use it as the semantic authority for new C6 work. |
| `backfill` | Current missing-observation query and matrix materialization operation. It is not the C6-A1 focus; later work may rename or absorb it as a stateful gap-filling adapter with accepted/review/rejected rescue semantics. |

### Ontology Boundary

`CrossSamplePeakGroupHypothesis` is deliberately narrower than
`PeakHypothesis`.

C6-A1 is only an owner-group membership shadow. It must not:

- add or consume a `peak_hypothesis_id`;
- change sample-local `PeakHypothesis`;
- join `shared_peak_identity_explanation` outputs;
- become product activation row identity;
- become a formal matrix row identity;
- claim edge, split-gate, review-only, or backfill authority.

The term "group" is intentional. It prevents the new contract from looking like
a second product `PeakHypothesis` ontology while still making the old
`family` language subordinate to hypothesis-based reasoning.

### Why `family` Is Demoted

Several observed failure modes show that one local RT/mz region can contain
multiple plausible peaks. A row group is therefore not proof that every member
belongs to one true chemical or biological entity.

C6 must model the grouping as a hypothesis:

- it can be accepted into the matrix;
- it can require review;
- it can be split;
- it can be demoted;
- it can remain output-compatible with `FAM######`.

This matches the direction already established by C4: evidence chains support
or challenge candidate interpretations instead of letting a single legacy score
or grouping primitive decide product truth. C4 remains sample-local; C6-A1 adds
the cross-sample peak group hypothesis boundary.

## Scope

### In Scope For C6-A1

Create a behavior-neutral shadow contract:

```text
OwnerAlignedFeature
  -> CrossSamplePeakGroupHypothesis shadow projection
  -> tests prove identity and membership parity
  -> writer-visible parity harness proves public output is unchanged
```

C6-A1 owns only the first invariant group:

- `public_family_id`;
- owner membership;
- owner IDs / event IDs;
- event member count.

After C6-A1, only `stable_cross_sample_family_membership` may be marked as
successor-covered in `owner_family_successor_contract.py`, and only with an
explicit shadow-contract reason. Complete-link edge semantics, hard split gates,
review-only owner records, and backfill seed / matrix delivery must remain
`active_policy` or `successor_gap` blockers.

### Out Of Scope For C6-A1

- No production-path replacement.
- No change to `cluster_sample_local_owners(...)`.
- No change to `OwnerAlignedFeature` constructor or fields.
- No change to `run_alignment(...)`.
- No change to `alignment_matrix.tsv`, `alignment_cells.tsv`,
  `alignment_review.tsv`, workbook sheets, output-level routing, or process
  payloads.
- No edge-scoring migration yet.
- No hard split gate migration yet.
- No review-only family migration yet.
- No backfill retirement or behavior change.
- No `FAM######` ID migration.
- No shared-peak product activation or `peak_hypothesis_id` migration.

## Proposed Shadow Model

The first implementation slice must add the fixed internal model module
`xic_extractor/alignment/cross_sample_peak_groups.py`.

Candidate shape:

```python
@dataclass(frozen=True)
class CrossSamplePeakGroupHypothesis:
    group_hypothesis_id: str
    public_family_id: str
    owner_ids: tuple[str, ...]
    event_ids: tuple[str, ...]
    event_member_count: int
    source: str = "owner_aligned_feature_shadow"
    edge_facts: tuple[CrossSamplePeakGroupEdgeFact, ...] = ()
```

Allowed projection:

```python
cross_sample_peak_group_hypothesis_from_owner_feature(
    feature: OwnerAlignedFeature,
) -> CrossSamplePeakGroupHypothesis
```

The first version may set `group_hypothesis_id == public_family_id` to preserve
public parity. It must not use the name `peak_hypothesis_id`. A future semantic
ID migration must be a separate public-contract decision.

C6-A2 adds a companion shadow edge fact:

```python
@dataclass(frozen=True)
class CrossSamplePeakGroupEdgeFact:
    left_owner_id: str
    right_owner_id: str
    owner_pair_ids: tuple[str, str]
    decision: EdgeDecision
    role: Literal["membership_support", "membership_challenge"]
    failure_reason: HardGateFailureReason | Literal[""]
    rt_raw_delta_sec: float
    rt_drift_corrected_delta_sec: float | None
    drift_prior_source: DriftPriorSource
    injection_order_gap: int | None
    score: int
    reason: str
    construction_policy: Literal[
        "none",
        "construction_time_hard_gate_observed",
    ] = "none"
    source: str = "owner_edge_evidence_shadow"
```

Strong edges project to `membership_support`. Weak edges project to
`membership_challenge`. Blocked edges may project to challenge facts with
`construction_time_hard_gate_observed`, but this is only a shadow observation of
the current construction gate. C6-A2 does not promote construction-time hard
gates into successor production policy.

## Contract Rules

### C6-A1 Parity

For any projected owner feature:

```text
OwnerAlignedFeature.feature_family_id
  == CrossSamplePeakGroupHypothesis.public_family_id

OwnerAlignedFeature.event_cluster_ids
  == CrossSamplePeakGroupHypothesis.owner_ids

flatten(owner.event_candidate_ids for owner in OwnerAlignedFeature.owners)
  == CrossSamplePeakGroupHypothesis.event_ids

OwnerAlignedFeature.event_member_count
  == CrossSamplePeakGroupHypothesis.event_member_count
```

The projected hypothesis must preserve owner order exactly as current output
rows do.

The focused projection fixture must include at least one owner with non-empty
`supporting_events`. A projection that only copies the primary event ID is not
acceptable.

### Writer-Visible Parity Harness

C6-A1 must add a compact golden triad fixture that writes and compares complete
schema/order plus row/value parity for:

- `alignment_matrix.tsv`;
- `alignment_cells.tsv`;
- `alignment_review.tsv`.

The fixture should not protect only selected fields. It should compare the full
header and full row dictionaries or exact line snapshots for the compact
fixture.

The fixture must cover at least these value families through full-row parity:

| Surface | Required parity fields |
| --- | --- |
| `alignment_matrix.tsv` | family IDs, neutral-loss/mz/RT centers, sample area cells, identity decision / reason, row flags, warnings, and reason fields when present |
| `alignment_cells.tsv` | family/sample keys, status, area, RT, height, source candidate, trace quality, reason, region fields, duplicate/ambiguous/absent blanking |
| `alignment_review.tsv` | event counts/IDs, family evidence, include flags, identity/review decisions, warnings, reasons, loser/duplicate audit fields when present |

C6-A1 must also run existing XLSX writer coverage, or add a compact XLSX smoke
for Matrix / Review / Audit sheet presence and key row preservation if the
implementation touches workbook-adjacent helpers. Since C6-A1 should not touch
writers, existing XLSX tests are sufficient unless the implementation expands
scope.

This harness does not prove successor equivalence by itself. It only gives the
later migration a public-output oracle.

## Successor Relationship

Current state:

- `TraceGroup` is sample-local and rejects mixed-sample traces.
- sample-local `PeakHypothesis` is a local peak/integration hypothesis with a
  `trace_group_id`; it does not own cross-sample membership.
- shared-peak `peak_hypothesis_id` is diagnostic/product-activation identity,
  not the C6-A1 owner-group membership shadow.
- `OwnerAlignedFeature` currently owns cross-sample membership and writer
  delivery fields.

C6-A1 should therefore introduce `CrossSamplePeakGroupHypothesis` as a shadow
successor contract only. It must not claim product authority until later phases
prove edge/gate/review-only/backfill and public-output parity.

## Phase Plan

### C6-A1 — Identity And Membership Shadow Contract

Purpose:

- define `CrossSamplePeakGroupHypothesis`;
- project it from `OwnerAlignedFeature`;
- prove family ID / membership / event parity;
- add writer-visible parity harness.

Historical disposition after C6-A1, before C6-M:

```text
owner_clustering.py = keep_as_stage
OwnerAlignedFeature = active delivery DTO
CrossSamplePeakGroupHypothesis = shadow successor contract
```

C6-A1 implementation closeout:

- `xic_extractor/alignment/cross_sample_peak_groups.py` defines the internal
  `CrossSamplePeakGroupHypothesis` shadow contract and projection from
  `OwnerAlignedFeature`;
- `stable_cross_sample_family_membership` is `successor_owned` only for
  shadow identity and membership parity;
- complete-link edge semantics, hard split gates, review-only owner records,
  and backfill seed / matrix delivery remain blockers, so
  `owner_clustering.py` remains `keep_as_stage` at the C6-A1 checkpoint;
- evidence: `tests/test_alignment_owner_family_successor_contract.py` covers
  supporting-event projection, membership mapping, disposition blocking, and
  compact TSV triad full-header/full-row parity.

### C6-A2 — Edge Evidence Migration

Purpose:

- move complete-link-compatible edge evidence into successor-owned shadow
  tests;
- preserve drift-prior, tolerance, and edge-strength evidence as
  support/challenge facts on the cross-sample peak group hypothesis;
- document construction-time hard gates that shape edge eligibility without
  reclassifying those gates as successor-owned policy yet;
- prove that edge evidence currently emitted by owner-family construction is
  still observable through the successor contract.

Allowed work:

- extend `CrossSamplePeakGroupHypothesis` or a companion internal model with
  edge/support/challenge evidence fields;
- add projection tests from current owner-family edge evidence into successor
  evidence;
- update `owner_family_successor_contract.py` only for invariants proven by
  focused characterization tests.

Forbidden work:

- no change to complete-link merge behavior;
- no change to family membership, edge thresholds, review-only records, or
  writer output;
- no production consumer may depend on the successor edge evidence yet.

Done when:

- every edge invariant named in the parent C6 owner-family row is covered by an
  existing or new focused test;
- the successor contract can explain whether each edge supports, challenges, or
  blocks membership;
- hard gates and review-only records remain `active_policy` unless C6-A3 proves
  a shadow fact plus a compatible disposition;
- matrix/cells/review writer-visible parity still holds for the compact golden
  triad.

C6-A2 implementation closeout:

- `xic_extractor/alignment/cross_sample_peak_groups.py` defines
  `CrossSamplePeakGroupEdgeFact` and projections from current
  `OwnerEdgeEvidence`;
- strong edges are shadow support facts, weak edges are shadow challenge facts,
  and blocked edges remain construction-gate observations rather than
  successor production policy;
- `owner_family_successor_mapping(feature, edge_evidence=...)` marks only
  `owner_edge_evidence_projection` as `successor_owned` when owner edge
  evidence was projected into successor edge facts;
- at the C6-A2 checkpoint, complete-link family construction remains
  `active_policy` because A2 does not replace the all-strong-pair grouping
  rule;
- at the C6-A2 checkpoint, hard split gates and review-only owner records
  remain `active_policy`; backfill seed / matrix delivery remains
  `successor_gap`;
- `owner_clustering.py` remains `keep_as_stage` after A2 at that historical
  checkpoint because complete-link construction, split, review-only, and
  backfill blockers are still live;
- C6-M below supersedes this historical checkpoint after constructor parity is
  proven;
- evidence:
  `tests/test_alignment_owner_family_successor_contract.py` covers strong edge
  support projection, weak edge challenge projection, blocked-edge shadow
  projection, post-edge-projection disposition blocking, and production-path
  no-use guards.

### C6-A3 — Split Gate And Review-Only Semantics

Purpose:

- project hard split gate observations from emitted blocked owner-edge evidence
  into successor-visible shadow challenge/demotion facts;
- preserve review-only owner records as hypothesis challenges instead of
  letting them disappear inside `OwnerAlignedFeature`;
- make projected blocked-edge conflict reasons and ambiguous-owner reasons
  explicit successor facts without claiming full construction-gate coverage.

Allowed work:

- add shadow challenge/demotion/split fields or a companion audit structure;
- add tests that prove current split/review-only cases project into successor
  facts without changing owner-family output;
- document which reasons remain active policy rather than successor-owned
  product behavior.

Forbidden work:

- no change to split thresholds or review-only classification;
- no removal of review-only owner records;
- no change to `alignment_review.tsv`, duplicate/loser audit, or production
  decision reasons.

Done when:

- current hard split and review-only invariants are either represented as
  successor shadow facts while their live invariant disposition remains
  `active_policy`, or explicitly listed as `successor_gap`;
- no new disposition label is introduced unless
  `owner_family_successor_contract.py` is deliberately expanded with tests;
- successor facts preserve the current reason vocabulary or document the exact
  compatibility mapping;
- compact TSV parity confirms public output is unchanged.

C6-A3 implementation closeout:

- `xic_extractor/alignment/cross_sample_peak_groups.py` defines
  `CrossSamplePeakGroupReviewFact` and
  `CrossSamplePeakGroupHardGateChallengeFact` as internal shadow facts;
- review-only facts are projected only from current `OwnerAlignedFeature`
  fields: `review_only`, `identity_conflict`, `ambiguous_sample_stem`,
  `ambiguous_candidate_ids`, `evidence`, and `feature_family_id`;
- identity-conflict review-only features project an `identity_conflict`
  review challenge, and ambiguous-owner review-only features preserve the
  ambiguous sample stem and candidate IDs;
- blocked `OwnerEdgeEvidence` can project a hard-gate challenge observation,
  preserving the current failure reason vocabulary, but this remains an
  observation of construction-time policy;
- at the C6-A3 checkpoint, envelope-only construction gates that do not emit
  blocked `OwnerEdgeEvidence` remain unprojected `active_policy` blockers; C6-M
  below supersedes this after constructor parity is proven;
- `owner_family_successor_mapping(...)` may mark
  `review_only_owner_records` as `successor_owned` only when review-only facts
  are actually projected for a review-only feature;
- at the C6-A3 checkpoint, `hard_family_split_gates` remains `active_policy`;
  C6-A3 does not claim successor ownership of same-sample, neutral-loss,
  precursor, product, or observed-loss construction gates;
- at the C6-A3 checkpoint, `complete_link_edge_semantics` remains
  `active_policy`, and `backfill_seed_and_matrix_delivery` remains
  `successor_gap`;
- `owner_clustering.py` remains `keep_as_stage` after A3 at that historical
  checkpoint because complete-link construction, hard-gate construction policy,
  and backfill/matrix delivery still block retirement or adapter promotion;
- C6-M below supersedes this historical closeout by moving construction into
  the successor constructor while keeping public delivery as an adapter;
- evidence:
  `tests/test_alignment_owner_family_successor_contract.py` covers
  identity-conflict review fact projection, ambiguous-owner candidate detail
  projection, blocked-edge hard-gate challenge observations without policy
  promotion, and post-review-fact disposition blocking.

### C6-M — Successor Constructor Migration

Purpose:

- make owner-family construction internally build
  `CrossSamplePeakGroupHypothesis` first;
- adapt the successor hypothesis back to `OwnerAlignedFeature` so downstream
  public contracts do not change;
- move `owner_clustering.py` from active construction owner to one concrete
  compatibility-adapter disposition.

Final outcome:

- `owner_clustering.py` disposition:
  `compatibility_adapter_candidate`;
- `cross_sample_peak_groups.construct_cross_sample_peak_group_hypotheses(...)`
  owns complete-link construction, hard split gates, identity-conflict
  review-only construction records, ambiguous review-only construction records,
  and delivery metadata needed to adapt back to `OwnerAlignedFeature`;
- `owner_clustering.cluster_sample_local_owners(...)` remains the public
  entrypoint and adapts successor hypotheses back to `OwnerAlignedFeature`;
- `OwnerAlignedFeature` remains the active public delivery DTO for backfill,
  matrix, claim registry, primary consolidation, writers, and process payloads;
- public output behavior is unchanged by focused parity tests.

Forbidden outcomes:

- direct deletion of `owner_clustering.py`;
- removal or public rename of `OwnerAlignedFeature`;
- changing `FAM######` output identity;
- changing matrix/cells/review values, workbook sheets, output-level routing, or
  process payloads.

Done when:

- C6-M names exactly one disposition for `owner_clustering.py`;
- constructor/adaptor promotion has focused parity for family IDs, owner order,
  complete-link grouping, hard gates, edge evidence, review-only records,
  ambiguous records, delivery fields, and compact TSV row/value parity for
  `alignment_matrix.tsv`, `alignment_cells.tsv`, and `alignment_review.tsv`;
- `owner_edge_evidence.tsv` row parity is proven when debug or validation output
  emits it;
- optional pre-backfill consolidation and backfill-scope consumers are covered
  when the constructor/adaptor can affect seed centers, family membership,
  review-only state, or backfill eligibility;
- focused owner-clustering tests still prove complete-link, drift-prior,
  conflict split, review-only, and no-same-sample invariants;
- `owner_family_successor_contract.py` records which invariants are successor
  owned, adapter-only, still active policy, or still successor gaps;
- legacy cleanup candidates are deferred to a later parity-backed cleanup goal.

C6-M implementation closeout:

- `owner_family_successor_contract.py` returns
  `compatibility_adapter_candidate` when no invariant remains `active_policy`
  or `successor_gap`;
- `complete_link_edge_semantics` and `hard_family_split_gates` are
  `successor_owned`;
- `backfill_seed_and_matrix_delivery` is
  `compatibility_adapter_candidate`, meaning successor metadata adapts to the
  old DTO but downstream consumers have not migrated;
- `OwnerAlignedFeature` is unchanged and remains the active delivery DTO;
- public output behavior is unchanged.

Later cleanup candidates:

- migrate owner-backfill, owner-matrix, claim registry, primary consolidation,
  writers, and process payloads to consume successor groups directly;
- only after that downstream migration, consider whether `OwnerAlignedFeature`
  becomes a thinner public compatibility wrapper or can be retired;
- keep parity for `alignment_matrix.tsv`, `alignment_cells.tsv`,
  `alignment_review.tsv`, and `owner_edge_evidence.tsv` when emitted.

## Allowed Implementation Scope By Phase

C6-A1 implementation may touch only:

- `xic_extractor/alignment/cross_sample_peak_groups.py`;
- `xic_extractor/alignment/owner_family_successor_contract.py` to record the
  C6-A1 shadow membership coverage without clearing the remaining blockers;
- focused tests for projection parity and writer-visible parity;
- this spec or its direct implementation plan.

C6-A1 implementation must not touch or import the new shadow model from:

- `xic_extractor/alignment/__init__.py`;
- `xic_extractor/alignment/pipeline.py`;
- `xic_extractor/alignment/pipeline_outputs.py`;
- `xic_extractor/alignment/process_backend.py`;
- `xic_extractor/alignment/owner_backfill.py`;
- `xic_extractor/alignment/owner_matrix.py`;
- `xic_extractor/alignment/tsv_writer.py`;
- `xic_extractor/alignment/xlsx_writer.py`;
- `xic_extractor/peak_detection/hypotheses.py`;
- `xic_extractor/alignment/shared_peak_identity_explanation/*`;
- `xic_extractor/alignment/shared_peak_identity_explanation/product_activation.py`.

If any of those files need changes, C6-A1 has become a behavior or public
contract migration and must stop.

C6-A1 must also use a mechanical changed-file and forbidden-symbol check. The
closeout must show:

- changed files are within the C6-A1 allowlist above;
- the new internal shadow module does not import or reference
  `PeakHypothesis`, `peak_hypothesis_id`, `shared_peak_identity_explanation`,
  or `product_activation`;
- forbidden production-path files did not gain `CrossSamplePeakGroupHypothesis`
  or `cross_sample_peak_group` references.

C6-A2 and C6-A3 may touch only:

- the internal cross-sample peak group successor module;
- focused owner-family successor contract tests;
- focused owner-clustering characterization tests;
- `owner_family_successor_contract.py`;
- this spec or its direct implementation plan.

C6-A2/A3 must stop if they need to change `cluster_sample_local_owners(...)`,
writer code, `run_alignment(...)`, output DTO fields, or production decisions.

C6-B may touch `owner_clustering.py` only if A1/A2/A3 are already green and the
change is behavior-neutral. Any C6-B touch to `owner_clustering.py` must keep
`cluster_sample_local_owners(...)` as the public entrypoint and prove exact
public-output parity. C6-B still must not touch:

- `xic_extractor/peak_detection/hypotheses.py`;
- `xic_extractor/alignment/shared_peak_identity_explanation/product_activation.py`;
- public package exports;
- writer schemas, workbook sheet contracts, output-level routing, or process
  payload compatibility.

## Verification

C6-A1 should run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run pytest -q tests/test_alignment_owner_family_successor_contract.py tests/test_alignment_owner_clustering.py tests/test_alignment_owner_matrix.py tests/test_alignment_tsv_writer.py tests/test_alignment_xlsx_writer.py
uv run ruff check xic_extractor tests
uv run mypy xic_extractor
rg -n "CrossSamplePeakGroupHypothesis|cross_sample_peak_group" xic_extractor
git diff --check
```

The `rg` no-use check must show the shadow model only in the internal model
module, `owner_family_successor_contract.py` if updated, and focused tests. Any
production-path hit is a blocker.

If implementation touches `run_alignment(...)`, `owner_backfill.py`,
`owner_matrix.py`, public writers, output-level routing, or process payloads,
C6-A1 has exceeded scope and must stop for a behavior spec.

C6-A2/A3 should additionally run the owner-clustering and successor-contract
tests that cover the new edge/challenge/split facts.

C6-B should run the focused C6 owner-family shard plus public-output parity:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run pytest -q tests/test_alignment_owner_family_successor_contract.py tests/test_alignment_owner_clustering.py tests/test_pre_backfill_consolidation.py tests/test_backfill_scope.py tests/test_alignment_owner_backfill.py tests/test_alignment_owner_matrix.py tests/test_alignment_claim_registry.py tests/test_alignment_primary_consolidation.py tests/test_alignment_matrix_identity.py tests/test_alignment_production_decisions.py tests/test_alignment_tsv_writer.py tests/test_alignment_xlsx_writer.py tests/test_alignment_debug_writer.py tests/test_alignment_output_levels.py tests/test_run_alignment.py tests/test_alignment_pipeline.py tests/test_alignment_pipeline_outputs.py
uv run ruff check xic_extractor tests
uv run mypy xic_extractor
git diff --check
```

If C6-B changes a broad constructor path, the closeout must cite exact
row/value parity for the compact golden triad plus `owner_edge_evidence.tsv`
when emitted. If a narrower oracle is used, the closeout must explain why the
change cannot affect broader TSV/workbook/debug output.

Mechanical no-use / import checks for A1 through B:

```powershell
git diff --name-only
rg -n "PeakHypothesis|peak_hypothesis_id|shared_peak_identity_explanation|product_activation" xic_extractor\alignment\cross_sample_peak_groups.py tests\test_alignment_owner_family_successor_contract.py
rg -n "CrossSamplePeakGroupHypothesis|cross_sample_peak_group" xic_extractor\alignment\__init__.py xic_extractor\alignment\pipeline.py xic_extractor\alignment\pipeline_outputs.py xic_extractor\alignment\process_backend.py xic_extractor\alignment\owner_backfill.py xic_extractor\alignment\owner_matrix.py xic_extractor\alignment\tsv_writer.py xic_extractor\alignment\xlsx_writer.py xic_extractor\peak_detection\hypotheses.py xic_extractor\alignment\shared_peak_identity_explanation
```

The forbidden-symbol checks should return no hits in those paths. If the first
check must inspect a file that does not exist in a phase, the closeout must say
that explicitly rather than silently skipping the ontology guard.

## Review Requirements

Before implementation, run xhigh read-only review using repo routing:

- `strategy-challenger`: challenge whether `CrossSamplePeakGroupHypothesis` is
  a real semantic successor or just `OwnerAlignedFeature` renamed.
- `implementation-contract-reviewer`: check public-output parity surfaces,
  tests, and stop rules.

Fix blockers and re-check with the original reviewer. Do not proceed to
implementation while either reviewer says this spec can still preserve a
parallel family system without migration pressure.

## Done When

This design is ready for an implementation plan when:

- `family` is explicitly demoted to output compatibility language;
- `CrossSamplePeakGroupHypothesis` owns C6-A1 identity/membership semantics and
  has explicit A2/A3 extension points for edge, challenge, split, and
  review-only facts;
- `OwnerAlignedFeature` remains the current delivery DTO;
- backfill is named as downstream missing-observation query / materialization
  and not retired in this slice;
- verification and stop rules protect matrix/cells/review public outputs;
- C6-A1 has a supporting-events projection fixture;
- C6-A2 has edge evidence migration acceptance criteria;
- C6-A3 has split-gate and review-only acceptance criteria;
- C6-B has a constructor/adaptor disposition rule, forbids direct deletion, and
  protects `owner_edge_evidence.tsv`, pre-backfill, and backfill-scope
  consumers;
- allowed write/import scope prevents production-path adoption;
- only invariants proven by the current phase may become shadow-successor
  covered in `owner_family_successor_contract.py`;
- xhigh strategy and implementation-contract reviews have no blockers.
