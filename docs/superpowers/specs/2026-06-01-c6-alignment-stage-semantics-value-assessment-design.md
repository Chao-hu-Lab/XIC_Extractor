# C6 - Alignment Stage Semantics And Value Assessment Design

Doc placement: repo_subcontract_doc
Doc kind: spec
Doc lifecycle: implemented
Repo owner: docs/product/alignment.md
Doc exit rule: Retire or convert to support after docs/product/alignment.md carries the current stage-semantics contract and retained validation fixtures preserve the historical C6 evidence.

**Date:** 2026-06-01
**Status:** Phase 5 implementation snapshot v1.8 — C6-M successor-constructor migration
**Readiness label:** `diagnostic_only`
**Supersedes for implementation:** [C6 alignment grouping consolidation](retired-provenance:a2156b86083c)
**Execution contract:** [Peak pipeline cleanup one-goal phase contract](2026-06-01-peak-pipeline-cleanup-one-goal-phase-contract-spec.md)
**Current-state input:** [Peak pipeline cleanup current-state reassessment](retired-provenance:2ae004032a4f)
**Output contract input:** [Untargeted alignment output contract](retired-provenance:a8d826fd641c)
**Follow-up successor design:** [C6 cross-sample peak group hypothesis shadow contract](retired-provenance:64de5836a40e)

## Verdict

C6 is not a generic grouping consolidation phase anymore.

The current alignment pipeline has several stages that look like grouping, but
they do not all have the same job. Some build candidate/event clusters, some
build owner families, some arbitrate duplicate MS1 peak claims, some decide
winner/loser rows, some deliver matrix identity, and some only explain or audit
evidence.

The next C6 goal is therefore:

```text
inventory alignment stages, name their product value and semantics, and choose
no refactor unless a later slice has a parity oracle and proves identical
semantics.
```

The old `group_by_tolerance`, `eject_and_reattach`, and `tie_break_sort`
primitive plan is historical rationale only. It must not be implemented as the
default C6 direction.

Phase 5 does not support broad helper extraction, but it does support bounded
semantic-survival slices for one named high-risk module family at a time. The
first executable C6-B slice retired the non-public event-family helper path
after no-use evidence and invariant triage. The follow-up public-shim slice
retired the remaining event-first compatibility exports and their delegated
clustering/backfill helpers. A later active-stage hardening slice pinned
writer-visible claim assignment and primary loser-audit surfaces without
changing alignment behavior. The owner-family parity-mapping slice then pinned
the `cluster_sample_local_owners(...)` -> `OwnerAlignedFeature` -> writer path
before any successor-spine migration.

The deeper C6 question is not only "can grouping-like loops be consolidated?"
It is:

```text
has a later evidence-chain or matrix-identity stage made this module's
intermediate concept obsolete, demoted, or only compatibility/audit support?
```

For this question, downstream evidence is allowed to demote an upstream stage's
authority. Demotion alone is not removal evidence, but fused or duplicated
semantics should not be preserved indefinitely. A stage is superseded when the
successor evidence path owns the same product invariant, current consumers can
migrate, and public or diagnostic compatibility has a removal plan.

## Design Decision

Use C6 as a value-assessment and stage-contract phase.

The product priority is fusion-first, not preservation-first. Legacy alignment
concepts are not retained merely because they once had value. If a legacy stage
and the newer hypothesis/evidence spine own overlapping semantics, C6 should
prefer one complete, responsibility-clear system:

- migrate still-valid invariants into the successor spine;
- reduce the old stage to a thin internal constructor or compatibility adapter
  only when current consumers still require it;
- retire implementation-specific tests after successor invariant coverage lands;
- delete the old stage when compatibility and output parity are satisfied.

Keeping two semantically similar systems is a temporary migration state, not an
accepted long-term architecture.

## Pilot Role

C6 is the alignment-stage pilot for the broader technical-debt roadmap. Its job
is to test the same fusion-first method in a more structural area than C4:

```text
legacy grouping / owner-family / claim / matrix stages
  -> successor trace, hypothesis, evidence, and matrix-identity semantics where covered
  -> contract-only or active-stage boundaries where not covered
  -> compatibility adapter, diagnostic role, or retirement after parity proof
```

Future project-wide cleanup should reuse C6's inventory shape for larger
subsystems: name the product value, identify the successor candidate, classify
the relationship, map tests to invariants, and give every row an exit rule. C6
should not become a broad grouping refactor; it is the example for deciding
whether a legacy stage is still a real owner, a migration target, or a retired
mechanic.

## C6-A Concrete Audit Snapshot

Current CodeGraph MCP / `rg` evidence, updated after the public-shim retirement
slice, shows four different classes of alignment stage. They must not be merged
into one cleanup bucket:

- `cluster_candidates(...)`, `_cluster_candidates_greedy(...)`, and
  `backfill_alignment_matrix(...)` have been removed from code after CodeGraph
  MCP impact/caller checks showed test/package-shim consumers only.
  `_build_event_first_matrix(...)` was already removed earlier and now appears
  only in docs/goal references. The event-first path is therefore retired code,
  not an owner-first production path and not a remaining compatibility layer.
- `build_sample_local_owners(...)`, `cluster_sample_local_owners(...)`,
  `select_backfill_features(...)`, `build_owner_backfill_cells(...)`, and
  `build_owner_alignment_matrix(...)` are still called by `run_alignment(...)`.
  They are active owner-first production structure, not dead code.
- `apply_ms1_peak_claim_registry(...)` and
  `consolidate_primary_family_rows(...)` are also called by `run_alignment(...)`
  after matrix construction. They produce duplicate-claim and winner/loser state
  consumed by downstream identity and output decisions; downstream evidence does
  not replace the arbitration step.
- `build_production_decisions(...)` calls
  `build_matrix_identity_decisions(...)` and feeds writer-facing decisions.
  These are policy/projection layers, not grouping helpers.

| Stage family | Current consumer evidence | Successor overlap | Concrete decision | Test migration / exit rule |
|---|---|---|---|---|
| Event-first candidate clustering/backfill: retired `clustering.cluster_candidates`, `_cluster_candidates_greedy`, `backfill_alignment_matrix`, `build_ms1_feature_families`, `integrate_feature_family_matrix` | CodeGraph MCP impact/caller checks and `rg` found no production, script, diagnostic, or package consumer after the public-shim slice; remaining mentions are docs and forbidden-import test strings. | `PeakHypothesis`, `TraceGroup`, owner-first evidence chain, owner-backfill, claim registry, primary consolidation, and PeakHypothesis matrix diagnostics cover the useful successor semantics. | `retired_event_first_path` after explicit public-shim retirement | Do not reintroduce. Any future event-first import or product path needs a new behavior spec, public migration note, and owner-first parity oracle. |
| Sample-local ownership: `ownership.build_sample_local_owners` | Called by `run_alignment(...)`, process backend, and ownership tests | `TraceGroup` can express traces, but does not replace sample-local candidate-to-peak ownership or ambiguous-owner records | `keep_as_stage` with possible future semantic migration | Keep tests in `tests/test_alignment_ownership.py`. Future fusion requires a concrete `TraceGroup`/owner contract that preserves unresolved assignments, identity conflicts, XIC request windows, region-audit context, and process-payload behavior. |
| Owner-family construction: `owner_clustering.cluster_sample_local_owners` and ambiguous review-only features | Called by `run_alignment(...)`, diagnostic probe, and owner-clustering tests | C6-M migrated complete-link owner-family construction into `CrossSamplePeakGroupHypothesis` successor construction, then adapts back to `OwnerAlignedFeature`; C6-D adds `OwnerGroupDeliveryFeature` so owner-backfill, owner-matrix, and process payloads no longer depend on the concrete legacy class | C6-M/C6-D `compatibility_adapter_candidate`; successor owns construction, public DTO remains active | Keep tests now. Do not delete `owner_clustering.py` or `OwnerAlignedFeature` until pre-backfill consolidation, diagnostic probes, adapter tests, and remaining concrete-dataclass consumers accept successor groups or an explicit delivery adapter. Preserve public parity for `alignment_matrix.tsv`, `alignment_cells.tsv`, `alignment_review.tsv`, and `owner_edge_evidence.tsv` when emitted. |
| Pre-backfill family consolidation: `pre_backfill_consolidation.*` | Optional `run_alignment(preconsolidate_owner_families=True)` path and tests | Future family spine may absorb pre-backfill identity consolidation | `contract_harden` / optional active path | Keep as optional policy until a successor owns family consolidation. Exit requires flag-path parity and owner-family ID/seed-center behavior parity. |
| Backfill scope, owner backfill, owner matrix: `select_backfill_features`, `build_owner_backfill_cells`, `build_owner_alignment_matrix` | Called by `run_alignment(...)`; owner-backfill tests include request economics, batching, region audit, rescue/unchecked/absent behavior | Trace evidence is used by region audit, but does not replace backfill cell creation or matrix delivery | `keep_as_stage` / `structural_input`; C6-D contract-hardened input type | Future behavior changes require matrix/cells parity, XIC request economy parity, region-audit behavior parity, and output-level checks. Current delivery input is structural through `OwnerGroupDeliveryFeature`, not the concrete `OwnerAlignedFeature` class. |
| MS1 peak claim registry: `apply_ms1_peak_claim_registry` | Called by `run_alignment(...)`; tests cover same-sample duplicate losers, NL conflicts, rescued winners, review-only conflicts, exact-same-peak claims, sample-local claims, and cells-TSV-visible duplicate assignment | Downstream duplicate flags consume this state but do not create it | `keep_as_stage` / `arbitration_state` | Keep. No C6 cleanup now. Future evidence-aware winner selection needs a separate behavior spec plus claim-assignment parity. |
| Primary consolidation: `consolidate_primary_family_rows` | Called by `run_alignment(...)`; tests cover duplicate-claim family winners, product identity separation, stronger sample peak preference, rescued duplicate demotion, loser audit, and review-TSV-visible loser evidence | Evidence chain may explain conflicts, but does not replace winner/loser row selection | `keep_as_stage` / `arbitration_state` | Keep. No C6 cleanup now. Exit requires either a separately approved model-selection behavior spec or parity-backed migration into a successor primary-family policy. |
| Matrix identity and production projection: `build_cell_quality_decisions`, `build_matrix_identity_decisions`, `classify_backfill_promotion`, `project_machine_decision`, `build_production_decisions`, writers | `build_production_decisions(...)` calls matrix identity and feeds XLSX/TSV/writer-facing decisions; broad tests cover identity, production, and output | Shared evidence can feed these policies, but cannot replace public matrix identity/projection without a behavior spec | `keep_as_stage` / `policy_projection` / `public_projection` | Preserve. Any behavior change needs separate spec plus matrix/review/cells/workbook parity. |
| Identity coherence and shared-peak-identity diagnostics | Diagnostic CLIs and sidecars can emit PeakHypothesis/mode evidence and PeakHypothesis matrix artifacts | Strong conceptual successor for split/wrong-peak evidence, but currently diagnostic or productization-gated, not source alignment mutation | `diagnostic_only` or future `semantic_migration_candidate` per tool | Keep under diagnostic lifecycle. They can justify future migration, but they do not by themselves retire owner-first production stages. |

### C6-A Test Retirement Table

| Test family | Current value | Migration action |
|---|---|---|
| `tests/test_alignment_clustering.py` public/API tests | Protected the now-retired public `cluster_candidates` import and event-first clustering mechanics. | Deleted with the public-shim retirement slice after no-use proof and successor invariant triage. |
| `tests/test_alignment_backfill.py` | Protected the now-retired public `backfill_alignment_matrix` compatibility shim and event-first backfill mechanics. | Deleted with the public-shim retirement slice. Active rescue/unchecked/absent and region-audit behavior stays covered by owner-backfill / owner-matrix tests. |
| `tests/test_alignment_feature_family.py`, `tests/test_alignment_family_integration.py` | Protected non-public event-family helpers with no runtime or public export consumer. | Deleted in C6-B after retained invariants were mapped to owner-family, owner-backfill, claim-registry, primary-consolidation, or obsolete event-family implementation detail. |
| `tests/test_alignment_ownership.py` | Protects active sample-local owner construction. | Keep. Not a C6 deletion target. |
| `tests/test_alignment_owner_clustering.py` | Protects the public `owner_clustering.py` compatibility adapter and legacy-output invariants after C6-M. | Keep now; later port/delete only after downstream consumers stop requiring `OwnerAlignedFeature`. |
| `tests/test_pre_backfill_consolidation.py` | Protects optional pre-backfill identity consolidation. | Keep while flag exists; retire only with flag removal or successor parity. |
| `tests/test_alignment_owner_backfill.py`, `tests/test_alignment_owner_matrix.py`, backfill-scope tests | Protect active backfill/matrix delivery and request economics. | Keep. They are not dead-code tests. |
| `tests/test_alignment_claim_registry.py` and hot-path tests | Protect duplicate-claim arbitration state, including cells-TSV-visible duplicate assignment. | Keep; future refactors must preserve claim-assignment parity. |
| `tests/test_alignment_primary_consolidation.py` | Protect winner/loser consolidation and review-TSV-visible loser audit trail. | Keep; future movement must preserve winner/loser/audit parity. |
| `tests/test_alignment_matrix_identity.py`, `tests/test_alignment_production_decisions.py`, writer tests | Protect production identity and public output projection. | Keep as public/product policy tests. |
| Shared-peak-identity / PeakHypothesis diagnostic tests | Protect successor diagnostic/productization evidence, not current source alignment mutation. | Keep as migration evidence; do not use them as deletion proof until a product wiring contract consumes them. |

C6-A conclusion: the event-first path was the immediate cleanup candidate and
has now been retired. The owner-first production chain remains active.
Owner-family construction has moved into the C6-M successor constructor, but
`owner_clustering.py` and `OwnerAlignedFeature` remain product-active
compatibility delivery surfaces for concrete adapter consumers. C6-D separates
owner-backfill, owner-matrix, and process payloads onto
`OwnerGroupDeliveryFeature`. Claim registry, primary consolidation, matrix
identity, and production decisions remain active policy/projection stages.

## C6-EF Event-First No-Use And Public-Deprecation Audit

This section executes the first C6 follow-up: determine whether the event-first
alignment path can enter retirement/deprecation planning.

Current CodeGraph MCP / `rg` evidence after the public-shim retirement slice:

- `cluster_candidates(...)` CodeGraph impact previously found only
  `tests/test_alignment_clustering.py`, public-import tests in
  `tests/test_alignment_config.py`, and the package-level shim. It now has no
  code symbol after deletion.
- `_cluster_candidates_greedy(...)` was only called by `cluster_candidates(...)`
  and was removed with `xic_extractor/alignment/clustering.py`.
- `_build_event_first_matrix(...)` has been removed from code. Fresh `rg`
  finds only docs/goal references for that symbol.
- `backfill_alignment_matrix(...)` CodeGraph impact previously found only
  `tests/test_alignment_backfill.py` and the package-level shim. It now has no
  code symbol after deleting `xic_extractor/alignment/backfill.py`.
- `MS1BackfillSource` was the only non-event-first utility in `backfill.py`.
  It was folded into `raw_sources.AlignmentRawHandle` before deleting the
  module, so active RAW source adapters keep their protocol contract without
  depending on the retired event-first backfill module.
- `build_ms1_feature_families(...)` and
  `integrate_feature_family_matrix(...)` had test consumers only after
  `_build_event_first_matrix(...)` removal; the C6-B event-family retirement
  slice deleted those non-public helpers and their implementation-only tests.
- `xic_extractor/alignment/__init__.py` no longer exports public
  `cluster_candidates` or `backfill_alignment_matrix`. The package public API is
  the current owner-first contract surface:
  `AlignmentConfig`, `AlignmentCluster`, `AlignedCell`, `AlignmentMatrix`, and
  `CellStatus`.
- Current `run_alignment(...)` owner-first flow uses
  `build_sample_local_owners(...)`, `cluster_sample_local_owners(...)`,
  `select_backfill_features(...)`, `build_owner_backfill_cells(...)`,
  `build_owner_alignment_matrix(...)`, `apply_ms1_peak_claim_registry(...)`,
  and `consolidate_primary_family_rows(...)`; it does not call the event-first
  wrapper.
- Remaining non-test references are historical implementation plans under
  `docs/superpowers/plans/2026-05-10*` and `2026-05-11*`. They are rationale,
  not current product consumers.

### Event-First Surface Classification

| Surface | Current consumer evidence | Public contract? | Concrete decision | Exit rule |
|---|---|---|---|---|
| `xic_extractor.alignment.cluster_candidates` | CodeGraph MCP impact found tests/package shim only before deletion; no product caller found | Former public export | `retired_public_event_first_shim` | Removed from `alignment.__all__` and package attributes. Reintroduction requires a new public migration contract. |
| `xic_extractor.alignment.backfill_alignment_matrix` | CodeGraph MCP impact found tests/package shim only before deletion; no product caller found | Former public export | `retired_public_event_first_shim` | Removed from `alignment.__all__` and package attributes. Reintroduction requires a new public migration contract. |
| `_cluster_candidates_greedy(...)` | Internal helper behind retired public `cluster_candidates` | No | `retired_implementation_detail` | Deleted with `clustering.py`; reintroduction requires a new product-path spec. |
| `_build_event_first_matrix(...)` | Removed from code after no-use proof; remaining references are docs/goal only | No | `historical_reference` after Phase 2 removal | Keep only as migration evidence. Reintroduction would require a new product-path spec and owner-first parity review. |
| `backfill.backfill_alignment_matrix` internals | Test-covered event-first cell construction and region-audit behavior only; no production caller found | Formerly public through package re-export | `retired_event_first_backfill` | Deleted. Active owner-backfill tests preserve retained rescue/unchecked/absent, region-audit, and request-economy semantics. |
| `feature_family.build_ms1_feature_families` | Removed after no-use evidence; previous consumers were tests only | No package-level public export | `retired_event_family_helper` | Reintroduction requires a new product-path spec. Owner-family tests already own neutral-loss/product/observed-loss separation and complete-link semantics; event-family shared-subset mechanics were implementation detail. |
| `family_integration.integrate_feature_family_matrix` | Removed after no-use evidence; previous consumers were tests only | No package-level public export | `retired_event_family_helper` | Reintroduction requires a new product-path spec. Owner-backfill, claim-registry, and primary-consolidation tests own retained region-audit and duplicate-peak semantics. |
| Historical plans mentioning event-first | Docs only | No active product contract | `historical_reference` | Do not update as active specs except to link to current C6 retirement decision if needed. |

### Event-First Invariant Triage

| Legacy invariant in event-first tests | Successor / active owner candidate | Action |
|---|---|---|
| Public import, keyword-only config validation, empty-input behavior | Retired public event-first surface | Delete with shim retirement; no owner-first product invariant depends on importing `cluster_candidates`. |
| Neutral-loss strata and product/observed-loss conflict separation | Owner-family construction, identity coherence / shared evidence diagnostics | Port only if not already covered by `tests/test_alignment_owner_clustering.py` or successor diagnostics. |
| Complete-link / no chain-collapse grouping | Owner-family construction and future cross-sample hypothesis-family tests | Port to owner/hypothesis tests if still product-relevant. |
| Stable IDs and input-order invariance | Public output row identity or successor matrix construction | Event-first internal IDs are implementation details. Keep only owner-first row/family identity tests. |
| Same-sample collision winner/ejection/reattach mechanics | Owner-local ownership, claim registry, primary consolidation | Treat as obsolete unless a matching owner-first invariant is missing. |
| Anchor backfill cell rescue/unchecked/absent behavior | `owner_backfill` / `owner_matrix` | Already owned by owner-first tests; event-first tests deleted. |
| Region audit receives trace context | `cell_region_audit`, `owner_backfill`, `family_ms1_overlay` diagnostics | Preserved through owner-backfill/diagnostic tests; event-family-specific trace-group tests were deleted with the unused helper. |
| Duplicate MS1 peak assignment to nearest/protected family | `claim_registry` and `primary_consolidation` | Preserved under claim/consolidation tests; event-family duplicate winner mechanics were not product authority. |

### C6-EF Executed Implementation Slice

Phase 2 executed the first event-first retirement/deprecation slice in this
order:

1. Run a final no-use check for event-first symbols:
   `cluster_candidates`, `_cluster_candidates_greedy`,
   `backfill_alignment_matrix`, `_build_event_first_matrix`,
   `build_ms1_feature_families`, and `integrate_feature_family_matrix`.
2. Kept public imports `cluster_candidates` and `backfill_alignment_matrix` on
   a deprecate-first compatibility path while the public removal decision was
   still pending.
3. Port or confirm successor coverage for the small set of reusable invariants:
   neutral-loss separation, complete-link grouping, region-audit trace context,
   and duplicate-peak arbitration.
4. Removed `_build_event_first_matrix(...)` after no callers remained.
5. Kept non-public event-first helper modules and their implementation-detail
   tests for later invariant triage because public compatibility shims still
   delegated to some of those helpers at that point.
6. Updated `xic_extractor/alignment/__init__.py`,
   `tests/test_alignment_config.py`, this spec, and the technical-debt roadmap
   in the same phase. Public export names did not change in Phase 2.

The public-shim retirement slice then amended that Phase 2 constraint with
explicit cleanup approval and review. It removed the remaining package-level
`cluster_candidates` and `backfill_alignment_matrix` exports, deleted
`clustering.py` / `backfill.py`, and folded the only still-useful `backfill.py`
protocol into `raw_sources.AlignmentRawHandle`.

This is a cleanup/contract slice. It must not change `run_alignment(...)`
owner-first output, `alignment_matrix.tsv`, `alignment_cells.tsv`,
`alignment_review.tsv`, workbook sheets, matrix identity, or production
decision behavior.

### C6-EF Execution Closeout

Phase 2 applied the first safe event-first cleanup slice:

- Removed private `_build_event_first_matrix(...)` from
  `xic_extractor/alignment/pipeline.py` after fresh `rg` evidence showed no
  production, script, diagnostic, or package consumer.
- Removed the now-unused event-first imports from `pipeline.py`:
  `backfill_alignment_matrix`, `build_ms1_feature_families`, and
  `integrate_feature_family_matrix`.
- Kept package-level public imports `cluster_candidates` and
  `backfill_alignment_matrix` available in `xic_extractor.alignment` as explicit
  deprecate-first compatibility shims.
- Added
  `tests/test_alignment_config.py::test_event_first_public_imports_are_compatibility_shims`
  to lock the chosen shim behavior.

The follow-up public-shim slice applied the reviewed breaking-change cleanup:

- Removed `cluster_candidates` and `backfill_alignment_matrix` from
  `xic_extractor.alignment.__all__` and package attributes.
- Deleted `xic_extractor/alignment/clustering.py` and
  `xic_extractor/alignment/backfill.py`.
- Deleted `tests/test_alignment_clustering.py` and
  `tests/test_alignment_backfill.py`.
- Moved the raw-source protocol dependency out of the retired backfill module by
  defining `raw_sources.AlignmentRawHandle` directly.
- Preserved the package import boundary by making
  `alignment.matrix.IntegrationResult` a type-checking-only import with a
  runtime `Any` fallback, so importing `xic_extractor.alignment` and resolving
  `AlignedCell` type hints do not pull in `raw_reader`.

No owner-first production stage moved. `run_alignment(...)` still uses
`build_sample_local_owners(...)`, `cluster_sample_local_owners(...)`,
`select_backfill_features(...)`, `build_owner_backfill_cells(...)`,
`build_owner_alignment_matrix(...)`, `apply_ms1_peak_claim_registry(...)`, and
`consolidate_primary_family_rows(...)`.

Residual no-use scan classification:

| Residual hit family | Classification | Current action |
|---|---|---|
| Former `xic_extractor/alignment/__init__.py` public `cluster_candidates` / `backfill_alignment_matrix` names | `retired_public_event_first_shim` | Removed from the package public surface. |
| Former `xic_extractor/alignment/clustering.py::cluster_candidates` and `_cluster_candidates_greedy` | `retired_implementation_detail` | Deleted after CodeGraph MCP impact showed tests/package shim only. |
| Former `xic_extractor/alignment/backfill.py::backfill_alignment_matrix` | `retired_event_first_backfill` | Deleted after CodeGraph MCP impact showed tests/package shim only; retained raw-source protocol moved to `raw_sources.py`. |
| `xic_extractor/alignment/feature_family.py::build_ms1_feature_families` | `retired_event_family_helper` | Deleted in the C6-B event-family retirement slice after CodeGraph/`rg` showed test-only consumers and retained invariants were mapped to owner-family or obsolete implementation detail. |
| `xic_extractor/alignment/family_integration.py::integrate_feature_family_matrix` | `retired_event_family_helper` | Deleted in the same C6-B slice after region-audit and duplicate-peak semantics were confirmed under owner-backfill, claim-registry, and primary-consolidation tests. |
| `tests/test_alignment_config.py` and `tests/test_alignment_boundaries.py` references | `public_contract_test` | Updated to prove the owner-first package public surface excludes the retired event-first exports. |
| `tests/test_alignment_clustering.py` public import tests | `retired_public_contract_test` | Deleted with the retired public shim. |
| `tests/test_alignment_backfill.py` | `retired_public_compatibility_and_implementation_test` | Deleted with the retired event-first backfill path. |
| `tests/test_alignment_feature_family.py`, `tests/test_alignment_family_integration.py` | `retired_implementation_tests` | Deleted with their non-public event-family helpers. |
| `docs/superpowers/specs/2026-06-01-*` and current goal references | `current_spec_or_goal` / `migration_note` | Keep as current contract and evidence record. |
| `docs/superpowers/plans/2026-05-10*` and `2026-05-11*` references | `historical_doc` | Do not treat as product consumers. |

There are no `unknown` residual hits and no unreviewed `active_consumer` hits
for the removed `_build_event_first_matrix(...)` symbol.

### C6-B Event-Family Retirement Closeout

The follow-up C6-B slice retired the non-public event-family helper path:

- Deleted `xic_extractor/alignment/feature_family.py`.
- Deleted `xic_extractor/alignment/family_integration.py`.
- Deleted `tests/test_alignment_feature_family.py`.
- Deleted `tests/test_alignment_family_integration.py`.
- Removed event-family-only `event_clusters` merge/seed-candidate support from
  `primary_consolidation.py` and `matrix_identity.py`.

This was allowed because CodeGraph / `rg` showed
`build_ms1_feature_families(...)`, `build_ms1_feature_family(...)`,
`MS1FeatureFamily`, and `integrate_feature_family_matrix(...)` had no current
production, script, diagnostic, package-level public export, or compatibility
shim consumer after `_build_event_first_matrix(...)` was removed. Their only
live consumers were implementation tests for the now-unused alternate
event-family path.

Invariant disposition:

| Deleted event-family invariant | Current owner or disposition |
|---|---|
| Shared detected overlap and high-subset family folding | Obsolete event-family implementation detail; owner-first grouping uses complete-link owner evidence rather than event-matrix overlap. |
| MS2 signature/product/observed-loss conflict separation | Covered by `tests/test_alignment_owner_clustering.py` product/observed-loss and neutral-loss separation tests plus identity-coherence fragment tests. |
| Non-anchor median family center | Obsolete event-family implementation detail; owner-first feature centers come from `OwnerAlignedFeature` construction. |
| Family-centered missing-sample rescue/unchecked/absent cells | Covered by owner-backfill and owner-matrix tests for owner-centered rescue, unchecked, absent, and output delivery. |
| Region audit opt-in and trace context | Covered by owner-backfill region-audit tests and diagnostics; event-family-specific `source="family_integration"` is not product authority. |
| Duplicate MS1 peak assignment to nearest/protected family | Covered by claim-registry and primary-consolidation tests; event-family local duplicate winner mechanics are obsolete. |
| Primary consolidation propagation of event-family `event_clusters` | Obsolete event-family compatibility branch; owner-first consolidation preserves `owners` and `event_cluster_ids`. |

The follow-up public-shim slice removed the remaining event-first compatibility
surface: `xic_extractor.alignment.cluster_candidates` and
`xic_extractor.alignment.backfill_alignment_matrix` are no longer package
exports, and their delegated implementation modules, `clustering.py` and
`backfill.py`, have been deleted.

Do not merge modules just because they all group rows. Each stage must first be
classified by the product decision it protects:

- candidate/event grouping;
- sample-local owner construction;
- owner-family grouping;
- event-family grouping;
- backfill scope or matrix delivery;
- claim arbitration;
- winner/loser consolidation;
- matrix identity policy;
- diagnostic or evidence review.

After classification, each stage gets one disposition:

- `keep_as_stage` - stage has distinct product semantics and should remain a
  named pipeline step.
- `rename_or_document` - behavior is useful, but the name or docs hide its role.
- `contract_harden` - keep behavior, add characterization tests or clearer
  invariants before future edits.
- `targeted_cleanup_candidate` - small cleanup may be safe after parity surfaces
  are named.
- `retire_candidate` - possible only when no production, diagnostic, handoff,
  or compatibility value remains and a removal plan exists.
- `semantic_migration_candidate` - stage still has live consumers, but its
  product concept is now better owned by a newer hypothesis/evidence spine and
  should be migrated instead of preserved as a parallel system.

Every C6-A row also gets a separate C6 targetability label:

- `primitive_candidate` - cross-stage helper extraction might be possible after
  identical semantics and parity are proven.
- `stage_local_cleanup_only` - cleanup may be possible inside the stage, but not
  through a shared primitive.
- `contract_only` - the stage protects product or public-output policy; C6 can
  document or harden it, not consolidate it.
- `diagnostic_preserve` - the module is diagnostic/evidence support and must not
  be mistaken for dead code.
- `out_of_scope_adapter` - IO, backend, validation, or wrapper code whose
  cleanup belongs to a separate adapter-focused spec.

Every C6-A row also gets a semantic-survival label:

- `structural_input` - downstream evidence consumes this stage's output and
  cannot currently reconstruct it independently.
- `candidate_source` - the stage proposes hypotheses or families; downstream
  evidence may accept, demote, or reject them.
- `arbitration_state` - the stage resolves conflicts into concrete cell or row
  state consumed by later policy.
- `compatibility_or_alternate_path` - the stage may no longer be the dominant
  product path, but it still preserves a public import, alternate output path,
  diagnostic path, or migration surface.
- `policy_projection` - the stage translates evidence and upstream state into
  public row/cell decisions or gate outcomes.
- `public_projection` - the stage writes or shapes public artifacts without
  owning the scientific decision.
- `diagnostic_oracle` - the stage is evidence review or validation support that
  can challenge product behavior but does not replace production stages by
  itself.
- `adapter_or_contract` - the stage is IO/backend/config/model infrastructure;
  C6 can check drift, but evidence-chain supersession is not the right question.
- `superseded_candidate` - the stage might be obsolete, but only after no-use
  evidence, consumer migration, and parity/removal plan are produced.
- `merged_into_successor` - the stage's product invariant is already represented
  by a newer successor model, but some compatibility or implementation surface
  still needs migration before deletion.

## Why This Replaces The Old C6 Plan

The old C6 spec saw repeated mechanics: tolerance checks, tie-break sorting,
candidate attachment, duplicate detection, and ejection. Those mechanics are
real, but similarity at the loop level is not enough.

Current alignment behavior also includes:

- graph-like relationships between duplicate or near-duplicate identities;
- sample-local owner and cross-sample family semantics;
- review-only identity conflict evidence;
- per-sample MS1 peak claim arbitration;
- primary/provisional/audit matrix identity decisions;
- loser row demotion and audit traceability;
- downstream `alignment_matrix.tsv`, `alignment_review.tsv`, and
  `alignment_cells.tsv` delivery.

A blind primitive extraction could preserve line-level structure while erasing
the product reason each stage exists. C6 must first prove which behavior is
mechanical duplication and which behavior is domain policy.

## Evidence-Chain Substitution Audit

This section answers the deeper C6 survival question for all alignment module
families covered by the C6 CodeGraph scan. `clustering.py`,
`owner_clustering.py`, and `claim_registry.py` are important examples, but they
are not the scope limit.

### Supersession Test

A later evidence-chain stage has "beaten" an earlier module only when all of
these are true:

- the later stage no longer needs the earlier module's output as an input;
- it can independently reconstruct the same family, claim, or row state needed
  by downstream writers and diagnostics;
- current tests and output parity prove the replacement preserves or
  intentionally migrates public behavior;
- compatibility imports, alternate paths, and diagnostic consumers have either
  migrated or have an accepted removal plan;
- the old concept is not still useful as audit evidence explaining a product
  decision.

If downstream evidence only marks an upstream family as `review_only`,
`audit_family`, `duplicate_claim_pressure`, provisional, or low-confidence, that
is demotion evidence. It is not retirement evidence.

If a newer successor already owns the same invariant, the desired end state is
not two maintained systems. The old module should either become a thin
compatibility adapter with a removal date, or the invariant should be migrated
to successor tests and the old implementation/tests removed.

### Test Retirement Rule

C6 must not keep legacy tests merely because they exist. Tests protect product
contracts, not old implementations.

When a module is fused into or superseded by a successor:

1. Identify the product invariant the legacy test was protecting.
2. Move that invariant to the successor model's tests, writer parity tests, or a
   public migration test.
3. Delete implementation-specific legacy tests once the successor test proves
   the invariant.
4. Keep only a short compatibility/import/config test while a public migration
   window exists.
5. Delete the compatibility test together with the compatibility shim when the
   removal plan lands.

Do not delete legacy tests first. Delete them after the successor invariant is
covered, or when the test is proven to assert an obsolete implementation detail
with no remaining product contract.

### Current Survival Decisions

| Module family / modules | Concept it defines | Downstream evidence relationship | Can evidence-chain replace it now? | Semantic-survival label | C6 disposition |
| --- | --- | --- | --- | --- | --- |
| Pipeline orchestration: `pipeline.run_alignment` | Stage ordering, output routing, timing, and side-effect boundaries for the owner-first production path. | Evidence-chain stages run inside this sequence; they do not replace sequence ownership. | No. Supersession is not the right question for `run_alignment`; changing it is orchestration/contract work. | `adapter_or_contract` plus `structural_input`. | `contract_only`; preserve sequence owner. |
| Event-first grouping path: retired `clustering.cluster_candidates`, `backfill.backfill_alignment_matrix`, `feature_family.build_ms1_feature_families`, `family_integration.integrate_feature_family_matrix` | Event-first clusters and event-first cells have no remaining code consumer after public-shim retirement. | `PeakHypothesis` / `TraceGroup`, owner-first owner-family/backfill, claim registry, and primary consolidation cover the useful successor concepts with richer evidence and boundary semantics. | Retired. Public clustering/backfill shims and non-public event-family helpers have been deleted after no-use and invariant triage. | `retired_event_first_path`; event-family subpath is `retired_event_family_helper`. | Do not reintroduce without a new product-path spec and owner-first parity oracle. |
| Sample-local ownership: `ownership.build_sample_local_owners`, `ownership_models.*` | Per-sample MS1 owner evidence and ambiguous-owner records. | Downstream family grouping, backfill, diagnostics, and matrix delivery consume ownership records. Later evidence can challenge confidence, not recreate raw owner assignment without this stage. | No. This is a structural input to the owner-first path. | `structural_input` and `candidate_source`. | `keep_as_stage` / `contract_only`; future edits need owner-assignment parity. |
| Owner-family construction: `owner_clustering.cluster_sample_local_owners`, `cross_sample_peak_groups.construct_cross_sample_peak_group_hypotheses`, `pre_backfill_consolidation.*` | Cross-sample owner groups, complete-link edge evidence, identity-conflict review groups, ambiguous review-only groups, and pre-backfill family consolidation. | C6-M moves construction ownership into the cross-sample peak group hypothesis constructor. C6-D moves owner-backfill, owner-matrix, and process payload input typing to `OwnerGroupDeliveryFeature`, but `owner_clustering.py` still supplies the public concrete adapter and pre-backfill consolidation still uses the dataclass shape. | Partially replaced now. `owner_clustering.py` is a compatibility adapter candidate, not the semantic construction owner. Downstream delivery is contract-hardened but not fully successor-native. | `merged_into_successor` for owner-family construction; `adapter_or_contract` for `OwnerAlignedFeature`; `structural_input` remains for downstream delivery. | C6-M/C6-D `compatibility_adapter_candidate`; no deletion until pre-backfill consolidation, diagnostic probes, adapter tests, and remaining concrete-dataclass consumers migrate to successor groups or explicit delivery adapters with TSV/debug parity. |
| Backfill scope and owner matrix delivery: `backfill_scope.*`, `owner_backfill.*`, `owner_matrix.*`, `owner_area.*` | Which families are backfilled, rescued cell construction, owner matrix rows, and owner-area rollups. | Matrix identity and production projection rely on detected/rescued/absent cell state from this family. Later evidence may classify quality but does not replace cell construction. | No. These are production structural inputs. | `structural_input`. | `keep_as_stage` / `contract_hardened_input`; C6-D proves these functions accept `OwnerGroupDeliveryFeature` rather than only `OwnerAlignedFeature`. Behavior changes still need cell-status parity. |
| Claim and primary consolidation policy: `claim_registry.*`, `primary_consolidation.*` | Duplicate MS1 claim arbitration and primary/loser demotion. | Matrix identity and production decisions consume duplicate/loser state as pressure or audit evidence. Later flags are downstream effects, not replacements. | No. These stages create arbitration and winner/loser state for the current product path. | `arbitration_state` and `structural_input`. | `keep_as_stage` after C6-B active-stage hardening; future cleanup needs claim-assignment and winner/loser/audit parity or a separate behavior spec. |
| Near-duplicate folding and audit: `folding.*`, `near_duplicate_audit.*` | Near-duplicate folding and audit counts. | Matrix identity and diagnostics consume fold state and audit counts; later diagnostics may explain them but do not remove the current fold/audit contract. | No for folding. Near-duplicate audit is diagnostic and replaceable only by an accepted diagnostic equivalent. | `arbitration_state`, `structural_input`, and `diagnostic_oracle`. | `contract_harden` / `diagnostic_preserve`; harden fold threshold/order parity before cleanup, and keep audit until replacement evidence exists. |
| Matrix identity and production projection: `cell_quality.*`, `matrix_identity.*`, `promotion_policy.*`, `machine_decision.*`, `production_decisions.*`, `production_candidate_gate.*` | Cell quality, primary/provisional/audit identity, backfill promotion, machine decision, writer-facing production decisions, and candidate-gate outcomes. | This is the downstream evidence/policy layer itself. It can demote earlier concepts but does not remove the need for upstream structural inputs. | No. It can supersede old scoring authority, but not owner/claim/matrix construction. | `policy_projection`. | `keep_as_stage` / `contract_only`; behavior changes need separate spec. |
| Compatibility and evidence helpers: `compatibility.*`, `family_compatibility.*`, `edge_scoring.*`, `drift_evidence.*`, `rt_normalization.*`, `adduct_annotation.*`, `trace_context.*` | Shared compatibility, edge scoring, drift/RT normalization, adduct annotations, and trace-context identifiers. | These helpers feed upstream construction and downstream evidence. Later evidence may consume or reinterpret them, but does not prove they are obsolete. | Not as a family. Individual helpers can be retired only after consumer and parity audit. | `structural_input` or `candidate_source` per helper. | `contract_harden`; local cleanup only after consumers are named. |
| Public delivery and report projection: `tsv_writer.*`, `xlsx_writer.*`, `html_report.*`, `debug_writer.*`, `pipeline_outputs.*`, `output_rows.*`, `output_levels.*` | Public TSV/XLSX/HTML/debug output, output-level routing, atomic writes, and row projection helpers. | Evidence-chain decisions are already upstream of these writers. Writers should not recompute or replace evidence. | No. Supersession is public-contract migration, not evidence-chain replacement. | `public_projection` and `adapter_or_contract`. | `keep_as_stage` / `contract_only`; protect output schema/value parity. |
| Tier2 trace and candidate-gate sidecars: `tier2_trace_producer.*`, `production_candidate_gate.*`, related diagnostics | Diagnostic/gate sidecar evidence for production-candidate review and Tier2 trace support. | These can challenge whether provisional rows should be promoted, but current sidecars are evidence support, not replacement for family construction. | No for production structural stages. A sidecar can replace an older diagnostic only with schema and decision parity. | `diagnostic_oracle` plus `policy_projection`. | `diagnostic_preserve` / `contract_only`; no production promotion without explicit gate spec. |
| Identity coherence and region diagnostics: `identity_coherence_adapter.*`, `identity_coherence/*`, `identity_coherence_validation/*`, `identity_coherence_*` helpers, `cell_region_audit.*` | Coherence verdicts, control manifests, trace retrieval, region audit evidence, output validation, and acceptance bundles. | These diagnostics can falsify confidence or reveal failure modes, but they are review/evidence surfaces unless an explicit production policy consumes them. | No for production stages. They may supersede older diagnostics only after diagnostic-output parity and replacement acceptance. | `diagnostic_oracle`. | `keep_as_stage` / `diagnostic_preserve`; retirement requires replacement evidence. |
| Shared peak identity explanation: `shared_peak_identity_explanation/*` | Shared-peak root-cause explanations, hypothesis consistency, mode/RT/MS1/MS2 evidence, product activation, and writers. | This is a newer evidence/explanation layer that can demote older labels, but it is not yet a universal replacement for alignment construction. | No for alignment structural stages. It may later absorb diagnostic explanation roles by explicit migration. | `diagnostic_oracle` and `policy_projection` where product activation is used. | `diagnostic_preserve` / `contract_only`; migrate deliberately, not by cleanup. |
| IO, backend, and validation adapters: `csv_io.*`, `legacy_io.*`, `raw_sources.*`, `ms1_index_source.*`, `process_backend.*`, `validation_pipeline.*`, `validation_writer.*`, `validation_compare.*` | File IO, RAW/index sources, process payloads, legacy import support, and validation harness outputs. | Evidence-chain semantics may depend on their data, but adapters are not semantic competitors. | Not applicable. Cleanup belongs to adapter/validation specs, not C6 evidence supersession. | `adapter_or_contract`. | `out_of_scope_adapter`; preserve unless a separate adapter cleanup owns it. |
| Models and public contracts: `models.*`, `matrix.*`, `config.AlignmentConfig`, `output_levels.AlignmentOutputLevel`, package `__init__` exports | Dataclasses, config, matrix containers, output-level contracts, and public imports. | Later evidence may require new fields, but it does not obsolete contracts without migration. | Not applicable without a public contract migration. | `adapter_or_contract` and `structural_input`. | `contract_only`; no renames or field moves in C6. |

### Immediate C6-B/C Candidate From This Audit

The first C6-B/C execution slices retired event-first clustering/backfill after a
bounded semantic-survival audit. The active-stage hardening slice then closed the
claim-registry and primary-consolidation `contract_harden` rows for C6 cleanup
disposition by adding writer-visible claim and loser-audit parity tests. The
remaining C6 semantic migration candidate is owner-family construction, not the
retired event-first path and not the claim/consolidation policy now pinned as an
active product stage.

Current CodeGraph-assisted mapping plus C6-D says `OwnerAlignedFeature` is still
a real handoff DTO, but not every downstream function is tied to its concrete
class:

- `pipeline.run_alignment(...)` creates it through
  `cluster_sample_local_owners(...)`;
- `select_backfill_features(...)`, `build_owner_backfill_cells(...)`,
  `build_owner_alignment_matrix(...)`, and process-backfill payloads now consume
  the structural `OwnerGroupDeliveryFeature` contract;
- optional pre-backfill consolidation, diagnostic probes, adapter tests, and
  public `cluster_sample_local_owners(...)` compatibility still consume or
  construct the concrete `OwnerAlignedFeature`;
- `TraceGroup` is currently a sample-local trace context, and `PeakHypothesis`
  is currently a local peak/integration hypothesis. They do not yet represent a
  cross-sample owner family with stable family ID, owner membership,
  complete-link edge semantics, review-only identity conflicts, backfill seed
  centers, and writer-visible matrix/cell/review projection.

Therefore this slice does not migrate `owner_clustering.py`. It pins the smallest
public oracle for a later migration:
`test_owner_family_construction_is_writer_visible` proves that owner-family
construction survives into `alignment_matrix.tsv`, `alignment_cells.tsv`, and
`alignment_review.tsv`.

1. List current production, diagnostic, public-import, and test consumers of
   `OwnerAlignedFeature` construction and owner-family outputs.
2. Map legacy tests to product invariants: candidate grouping, family grouping,
   edge evidence, winner/demotion behavior, and public compatibility.
3. Decide which invariants are already owned by `PeakHypothesis` / `TraceGroup`
   or successor cross-sample hypothesis tests.
4. Move still-valid invariants to successor tests or public migration tests.
5. Delete obsolete implementation-specific tests after successor coverage lands.
6. Reclassify each family as active production behavior, internal constructor,
   compatibility adapter, diagnostic support, or retirement candidate.
7. If it is a retirement candidate, require no-use evidence, output parity or
   migration tests, and a removal plan before any deletion.

Then check the remaining families for the same decision shape: whether the
evidence chain merely demotes the concept, whether a newer diagnostic replaces
only an older diagnostic, or whether a true no-use/migration case exists.
`claim_registry.py` and `primary_consolidation.py` should not be treated as
superseded by the current evidence chain yet; their jobs are arbitration and
winner/loser policy. `owner_clustering.py` is different: it is still a
structural input today, but its product concept is close enough to the successor
hypothesis/family spine that it should be treated as a semantic migration
candidate rather than a permanent parallel system.

### Owner-Family Successor Mapping

| Owner-family invariant | Current owner-first source | Current writer/public oracle | Successor-spine gap before migration |
| --- | --- | --- | --- |
| Stable cross-sample family ID and owner membership | `OwnerAlignedFeature.feature_family_id`, `owners`, `event_cluster_ids`, `event_member_count` | `test_owner_family_construction_is_writer_visible`; `alignment_review.tsv` event fields | Successor needs a cross-sample family/hypothesis object, not only per-sample `TraceGroup` / `PeakHypothesis` IDs. |
| Complete-link family construction and drift-prior edge evidence | `cluster_sample_local_owners(...)`, `edge_scoring.evaluate_owner_edge(...)` | owner-clustering complete-link, drift-prior, weak-edge, and edge-sink tests | C6-A2 projects emitted edge evidence into shadow support/challenge facts, but complete-link construction policy remains active. Replacement still waits for construction-policy, backfill/matrix, and public-output parity. |
| Hard family split gates | owner-clustering neutral-loss, product-m/z, observed-loss, impossible-m/z, same-sample exclusion checks | owner-clustering conflict/split tests plus matrix/cells parity when construction changes | C6-A3 can expose blocked-edge hard-gate observations from projected `OwnerEdgeEvidence`, but construction-time split gates remain `active_policy`. |
| Review-only owner records | `identity_conflict` features and `review_only_features_from_ambiguous_records(...)` | owner-clustering ambiguous/review-only tests; owner-matrix ambiguous cell tests | C6-A3 projects review-only shadow facts for identity-conflict and ambiguous-owner features, without changing review-only production behavior or matrix delivery. |
| Backfill seed and matrix delivery contract | `OwnerGroupDeliveryFeature.family_center_*`, `backfill_seed_centers`, `confirm_local_owners_with_backfill` | owner-backfill, owner-matrix, process backend, pre-backfill consolidation tests; writer-visible owner-family test | C6-D contract-hardens owner-backfill, owner-matrix, and process payloads. Successor still must cover concrete adapter consumers and prove `alignment_matrix.tsv`, `alignment_cells.tsv`, and `alignment_review.tsv` parity before `OwnerAlignedFeature` can retire. |

### C6 Owner-Family Successor Contract Snapshot

Execution added behavior-neutral internal contract modules:
`xic_extractor/alignment/cross_sample_peak_groups.py` and
`xic_extractor/alignment/owner_family_successor_contract.py`.

C6-A1/C6-A2/C6-A3 turn owner membership, emitted edge evidence, and
review-only observations into machine-checkable shadow projections while
preserving the remaining blockers:

| Invariant | Current C6 disposition | Why |
| --- | --- | --- |
| Stable cross-sample family ID and owner membership | `successor_owned` | C6-A1 adds `CrossSamplePeakGroupHypothesis` projection, and C6-M makes the same successor contract construct public family ID, owner IDs, flattened event IDs including supporting events, and event member count. |
| Owner edge evidence projection | `successor_owned` when `owner_family_successor_mapping(feature, edge_evidence=...)` receives projected edge facts, or no edge is required for the feature | C6-A2 adds `CrossSamplePeakGroupEdgeFact`; C6-M keeps edge evidence projection observable while construction runs through the successor constructor. |
| Complete-link family construction | `successor_owned` | C6-M moves the all-strong-pair complete-link grouping rule into `construct_cross_sample_peak_group_hypotheses(...)`. |
| Hard family split gates | `successor_owned` | C6-M moves same-sample, neutral-loss, precursor, product, and observed-loss construction gates into the successor constructor. |
| Review-only owner records | `successor_owned` | C6-M constructs identity-conflict and ambiguous review-only records in the successor path before adapting back to `OwnerAlignedFeature`. |
| Backfill seed and matrix delivery contract | `compatibility_adapter_candidate` | Successor groups carry delivery metadata; C6-D exposes the downstream delivery shape as `OwnerGroupDeliveryFeature` for owner-backfill, owner-matrix, and process payloads. `OwnerAlignedFeature` remains the public concrete adapter for pre-backfill consolidation, diagnostic probes, adapter tests, and public compatibility. |

C6-M disposition for `owner_clustering.py`:
`compatibility_adapter_candidate`.

C6-M does attempt and accept a constructor/adaptor experiment. The successor
constructor owns cross-sample group construction, while `owner_clustering.py`
keeps the public `OwnerAlignedFeature` facade for downstream delivery.

Exit rule:

```text
Do not retire owner_clustering.py or replace OwnerAlignedFeature until
pre-backfill consolidation, diagnostic probes, public adapter tests, and
remaining concrete-dataclass consumers accept successor groups or an explicit
delivery adapter directly, with public parity proven
for alignment_matrix.tsv, alignment_cells.tsv, alignment_review.tsv, and
owner_edge_evidence.tsv when emitted.
```

Focused tests:

- `tests/test_alignment_owner_family_successor_contract.py::test_owner_family_successor_mapping_names_all_required_invariants`
- `tests/test_alignment_owner_family_successor_contract.py::test_cross_sample_peak_group_hypothesis_projects_owner_membership`
- `tests/test_alignment_owner_family_successor_contract.py::test_strong_owner_edge_projects_support_fact_and_marks_successor_owned`
- `tests/test_alignment_owner_family_successor_contract.py::test_weak_owner_edge_projects_challenge_fact`
- `tests/test_alignment_owner_family_successor_contract.py::test_blocked_owner_edge_projects_challenge_fact_without_policy_promotion`
- `tests/test_alignment_owner_family_successor_contract.py::test_identity_conflict_review_only_feature_projects_review_challenge_fact`
- `tests/test_alignment_owner_family_successor_contract.py::test_ambiguous_review_only_feature_projects_candidate_review_details`
- `tests/test_alignment_owner_family_successor_contract.py::test_blocked_edge_projects_hard_gate_observation_without_policy_promotion`
- `tests/test_alignment_owner_family_successor_contract.py::test_owner_clustering_keeps_stage_after_review_fact_projection`
- `tests/test_alignment_owner_family_successor_contract.py::test_c6_b_final_disposition_keeps_stage_after_shadow_evidence`
- `tests/test_alignment_owner_family_successor_contract.py::test_compact_owner_family_tsv_triad_keeps_full_schema_and_rows`
- `tests/test_alignment_owner_family_successor_contract.py::test_cross_sample_peak_group_shadow_has_no_production_path_imports`

No product wiring changed. The contract module is not called by
`run_alignment(...)`, writers, claim registry, primary consolidation, or process
payloads. It exists to prevent future cleanup work from treating owner-family
construction as obsolete before successor and public-output parity exist. It is
a migration guard, not a permanent semantic owner; once a successor cross-sample
family object lands, this contract should be updated or reversed through the
same public TSV parity gate.

## Phase Shape

### C6-A - Stage Semantics And Value Assessment Inventory

**Type:** docs-only / `diagnostic_only`

Purpose:

- map every grouping-looking alignment stage to its actual role;
- identify which stages are production behavior, diagnostic evidence, or
  compatibility support;
- identify whether later evidence-chain stages only demote an upstream concept
  or actually supersede it;
- name the smallest future cleanup candidate, or explicitly close C6 as
  docs-only if no safe cleanup exists.

Allowed changes:

- write a current-state inventory table;
- add module-level notes or spec links if they clarify stage ownership;
- name characterization tests or golden parity surfaces for later phases.

Forbidden changes:

- moving source code;
- extracting generic helpers;
- changing selected alignment rows, winner/loser decisions, owner membership,
  matrix identity, TSV schemas, or review reasons.

DONE WHEN:

- every listed stage has a semantics class, product value statement, public
  surface, current test or missing-test note, risk if merged, disposition, C6
  targetability, semantic-survival label, and required next action / exit rule;
- every CodeGraph module family row is covered by at least one inventory row, or
  explicitly marked `out_of_scope_adapter` with a reason;
- the inventory identifies either one parity-backed C6-B/C follow-up or says no
  refactor is justified now;
- old C6 generic-primitives wording remains marked historical.

### C6-B - Stage Contract Hardening

**Type:** characterization tests / no behavior change

C6-B is optional and only follows C6-A if one or more stages have valuable but
underspecified behavior.

Allowed changes:

- add focused characterization tests for one named stage;
- document invariants that must survive later cleanup;
- name the exact TSV or row-level oracle used by the test.

Forbidden changes:

- changing stage output;
- broad helper extraction;
- turning diagnostic-only evidence into production behavior.

### C6-C - Targeted Cleanup Candidate

**Type:** narrow cleanup / parity required

C6-C is optional and only follows C6-A/C6-B if the inventory proves that a small
cleanup has identical semantics and a clear oracle.

Allowed changes:

- remove local duplication inside one stage;
- rename private helpers if tests prove public behavior is unchanged;
- extract a helper only when it is stage-local or when identical cross-stage
  semantics have been proven.

Forbidden changes:

- generic `group_by_tolerance`, `eject_and_reattach`, or `tie_break_sort`
  extraction by default;
- changing alignment matrix/review/cells values;
- changing winner/loser, owner, primary/provisional, review, duplicate, or
  claim semantics.

## Inventory Template

Every C6-A row must use this shape:

| Field | Meaning |
| --- | --- |
| Stage | Human-readable pipeline stage name. |
| Module / entrypoint | Exact module and function or public stage hook. |
| Pipeline position | Where it runs relative to clustering, owner build, backfill, matrix build, claim registry, and primary consolidation. |
| Purpose / product value | Why this stage exists for the product, not just what loop it runs. |
| Input model | Main objects or tables consumed. |
| Output model | Main objects, cells, rows, or decisions emitted. |
| Public surfaces affected | TSVs, review rows, audit fields, matrix identity, or downstream behavior affected by this stage. |
| Semantics class | One of the approved classes in this spec. |
| Tests / golden surfaces | Existing test, missing characterization test, or TSV parity surface. |
| Risk if merged/extracted | What product semantics could be erased by a generic helper or module merge. |
| Disposition | `keep_as_stage`, `rename_or_document`, `contract_harden`, `semantic_migration_candidate`, `targeted_cleanup_candidate`, or `retire_candidate`. |
| C6 targetability | `primitive_candidate`, `stage_local_cleanup_only`, `contract_only`, `diagnostic_preserve`, or `out_of_scope_adapter`. |
| Semantic-survival label | `structural_input`, `candidate_source`, `arbitration_state`, `compatibility_or_alternate_path`, `policy_projection`, `public_projection`, `diagnostic_oracle`, `adapter_or_contract`, `merged_into_successor`, or `superseded_candidate` when the row can be challenged by downstream evidence. |
| Required next action / exit rule | Exact action that closes the row, or the condition that reclassifies it after C6-A/C6-B. |

## Phase 5 C6-A Stage Inventory

This table is the Phase 5 closeout inventory. It is intentionally compact; each
row preserves the required C6-A fields by naming product value, public surface,
oracle or missing oracle, risk if merged, disposition, targetability,
semantic-survival label, and exit rule.

| Stage | Module / entrypoint | Product value / public surface | Semantics class | Oracle or missing oracle | Risk if merged/extracted | Disposition / targetability | Semantic-survival label | Required next action / exit rule |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Candidate event clustering | retired `xic_extractor.alignment.clustering.cluster_candidates` | Former event-first candidate/event grouping and public `cluster_candidates` import surface. Product authority is now superseded by owner-first and successor evidence concepts. | retired candidate/event grouping | CodeGraph MCP impact found tests/package shim only; successor invariants live in owner-family, ownership, identity-coherence, and hypothesis/trace diagnostics. | Reintroducing a generic grouping helper would recreate a parallel legacy candidate system. | `retired` | `retired_event_first_path` | Do not reintroduce without a new product-path spec, public migration note, and parity oracle. |
| Sample-local owner build | `xic_extractor.alignment.ownership.build_sample_local_owners` | Assigns MS1 trace ownership per sample and emits owner/ambiguous records used by production alignment. | sample-local owner construction | Existing ownership and pipeline backend tests; `event_to_ms1_owner.tsv` and `ambiguous_ms1_owners.tsv` parity when emitted. | Shared grouping would hide RAW-backed ownership and ambiguous-owner semantics. | `keep_as_stage` / `contract_only` | `structural_input` and `candidate_source` | Preserve as named stage; future edits need owner assignment parity. |
| Owner family grouping | `xic_extractor.alignment.owner_clustering.cluster_sample_local_owners` and `xic_extractor.alignment.cross_sample_peak_groups.construct_cross_sample_peak_group_hypotheses` | Builds cross-sample owner groups and edge evidence for owner-first matrix delivery; C6-D downstream delivery consumers use `OwnerGroupDeliveryFeature`, while concrete adapter consumers still use `OwnerAlignedFeature`. | successor-owned owner-family construction plus compatibility delivery adapter | Existing owner-clustering tests cover complete-link grouping, drift-prior edges, same-sample exclusion, neutral-loss/product/observed-loss conflict splits, impossible m/z rejection, edge evidence sink, and review-only identity-conflict features. C6-M/C6-D tests cover successor constructor parity, adapter delivery fields, structural delivery input for backfill/matrix/process, compact TSV triad parity, and `owner_edge_evidence.tsv` parity when emitted. | Deleting the adapter too early would break pre-backfill consolidation, diagnostics, adapter tests, or public compatibility. | `compatibility_adapter_candidate` / `contract_only` | `merged_into_successor` for construction; `adapter_or_contract` for delivery | Keep `owner_clustering.py` as public adapter. Do not retire or replace `OwnerAlignedFeature` until concrete adapter consumers migrate to successor groups or explicit delivery adapters with public parity. |
| Pre-backfill consolidation | `xic_extractor.alignment.pre_backfill_consolidation.consolidate_pre_backfill_identity_families` | Consolidates identity families before backfill scope selection. | identity-family consolidation before backfill | Existing alignment tests plus missing row-level pre/post consolidation fixture. | Generic merge could change which family enters backfill. | `contract_harden` / `stage_local_cleanup_only` | `structural_input` | Add focused consolidation fixture before cleanup; otherwise keep as stage. |
| Event-first backfill | retired `xic_extractor.alignment.backfill.backfill_alignment_matrix` | Former event-first matrix cell construction for the alternate alignment path. | retired event-first backfill and cell construction | CodeGraph MCP impact found tests/package shim only; owner-backfill / owner-matrix tests cover active cell delivery semantics. | Reintroduction could conflate owner-first and event-first backfill semantics again. | `retired` | `retired_event_first_path` | Do not reintroduce without a new product-path spec and matrix/cells parity oracle. |
| Owner backfill | `xic_extractor.alignment.owner_backfill.build_owner_backfill_cells` | Rescues owner-family cells and feeds owner matrix delivery. | backfill scope and matrix cell creation | Owner backfill tests, process backend tests, `alignment_cells.tsv` parity. | Generic backfill helper could change detected/rescued/absent labels. | `keep_as_stage` / `contract_hardened_input` | `structural_input` | C6-D narrowed input to `OwnerGroupDeliveryFeature`; future behavior edits still require cell status parity. |
| Owner alignment matrix | `xic_extractor.alignment.owner_matrix.build_owner_alignment_matrix` | Delivers owner-first alignment matrix rows. | matrix delivery | Matrix tests and `alignment_matrix.tsv` parity. | Merge could change row ordering, family identity, or downstream schema. | `keep_as_stage` / `contract_only` | `structural_input` | Preserve as delivery stage. |
| MS1 peak claim registry | `xic_extractor.alignment.claim_registry.apply_ms1_peak_claim_registry` | Arbitrates duplicate MS1 peak claims into concrete cell status/reason state consumed by matrix identity and production decisions. | claim arbitration | Existing claim tests plus `test_claim_registry_duplicate_assignment_is_cells_tsv_visible` protect winner/duplicate assignment and the writer-visible status/reason/peak fields. | Shared grouping could change winner/duplicate assignment; treating downstream duplicate flags as a replacement would skip the arbitration step that creates those flags. | `keep_as_stage` / `contract_only` | `arbitration_state` and `structural_input` | No C6 cleanup now. Future evidence-aware winner selection needs a separate behavior spec and claim-assignment parity. |
| Primary family consolidation | `xic_extractor.alignment.primary_consolidation.consolidate_primary_family_rows` | Selects primary rows, demotes losers, and preserves loser audit traceability. | winner/loser consolidation | Existing primary consolidation tests plus `test_consolidation_loser_audit_is_review_tsv_visible` protect winner/loser and review-TSV-visible audit parity. | Generic consolidation could erase winner/loser and near-duplicate demotion semantics. | `keep_as_stage` / `contract_only` | `arbitration_state` and `structural_input` | No C6 cleanup now. Future movement requires winner/loser/audit parity or a separate model-selection behavior spec. |
| Matrix identity decisions | `xic_extractor.alignment.matrix_identity.build_matrix_identity_decisions` | Classifies primary/provisional/audit matrix identity. | matrix identity policy | Matrix identity and production decision tests; matrix/review/cells parity. | Merging with grouping would turn identity policy into tolerance mechanics. | `keep_as_stage` / `contract_only` | `policy_projection` | Preserve; behavior changes require separate spec. |
| Production decisions | `xic_extractor.alignment.production_decisions.build_production_decisions` | Projects writer-facing row/cell decisions. | writer-facing production projection | Production decision and writer tests; output-level oracle matrix. | Generic output grouping could change public TSV values. | `keep_as_stage` / `contract_only` | `policy_projection` and `public_projection` | Preserve as public projection owner. |
| Event-first feature family path | `feature_family.build_ms1_feature_families`, `family_integration.integrate_feature_family_matrix` | Former alternate/event-first feature-family integration path. | event-family grouping and matrix integration | C6-B no-use scan plus successor invariant mapping. | Reintroduction would recreate a parallel feature-family system without a product consumer. | `retired_event_family_helper` | obsolete implementation detail after no-use proof | Deleted in C6-B; reintroduction requires a new product-path spec. |
| Near-duplicate folding | `xic_extractor.alignment.folding.fold_near_duplicate_clusters` | Folds near-duplicate clusters before downstream review. | near-duplicate folding behavior | Folding tests plus near-duplicate row parity if touched. | Shared primitive could alter fold threshold/order semantics. | `contract_harden` / `stage_local_cleanup_only` | `arbitration_state` and `structural_input` | Add threshold/order fixture before local cleanup. |
| Near-duplicate audit | `xic_extractor.alignment.near_duplicate_audit.count_near_duplicate_pairs` | Diagnostic evidence for near-duplicate behavior. | diagnostic or evidence review | Diagnostic count tests or report parity if touched. | Could be falsely retired as non-production despite validation value. | `keep_as_stage` / `diagnostic_preserve` | `diagnostic_oracle` | Preserve diagnostic evidence; retirement requires no-use evidence. |
| Identity gates | `xic_extractor.alignment.identity_gates.*` | Applies identity/evidence gate policy using `CommonEvidence`. | identity/evidence gate policy | Identity gate tests and decision parity. | Grouping consolidation would hide evidence policy behind mechanics. | `keep_as_stage` / `contract_only` | `policy_projection` | Preserve; policy changes need behavior spec. |
| Identity coherence adapter | `xic_extractor.alignment.identity_coherence_adapter.run_identity_coherence_diagnostic` | Bridges production alignment evidence into identity-coherence diagnostics. | diagnostic or evidence review | Identity coherence adapter/pipeline tests. | Could be mistaken as duplicate diagnostic code despite current validation role. | `keep_as_stage` / `diagnostic_preserve` | `diagnostic_oracle` | Preserve diagnostic bridge. |
| Identity coherence diagnostics | `xic_extractor.alignment.identity_coherence.*` | Emits diagnostic verdicts/status/reasons for coherence review. | diagnostic or evidence review | Identity coherence diagnostic tests and output parity. | Broad consolidation could erase diagnostic semantics. | `keep_as_stage` / `diagnostic_preserve` | `diagnostic_oracle` | Preserve; retirement requires diagnostic replacement. |
| Shared peak identity explanation | `xic_extractor.alignment.shared_peak_identity_explanation.*` | Explains shared-peak/wrong-peak root causes for review. | diagnostic or evidence review | Existing explanation tests or diagnostic report parity if touched. | Could be misclassified as dead code; it provides evidence for product decisions. | `keep_as_stage` / `diagnostic_preserve` | `diagnostic_oracle` and `policy_projection` | Preserve unless a replacement diagnostic is accepted. |

## CodeGraph Module Function Map

This map is based on the 2026-06-01 CodeGraph-assisted scan of
`xic_extractor/alignment/`. It exists to keep C6-A from inspecting only the
modules that visibly "cluster" rows.

CodeGraph snapshot at this update:

- index status: up to date;
- alignment package files: 113;
- repository nodes: 13,848;
- repository edges: 31,043.

| Module family | Modules / entrypoints | C6-A role | Phase 5 disposition / oracle or out-of-scope reason |
| --- | --- | --- | --- |
| Pipeline orchestration | `pipeline.run_alignment` | sequence owner for the current owner-first production path; records where each active stage runs and which output path it can affect | `contract_only`; preserve as sequence owner. Oracle: `tests/test_run_alignment.py`, pipeline output/atomic-write tests, and output-level artifact parity when routing is touched. `_build_event_first_matrix` was removed in Phase 2 and now belongs only to event-first migration history. |
| Event-first grouping path | retired `clustering.cluster_candidates`, `backfill.backfill_alignment_matrix`, `feature_family.build_ms1_feature_families`, `family_integration.integrate_feature_family_matrix` | formerly public compatibility shims plus delegated event-first clustering/backfill support; the full event-first path has been removed | `retired_event_first_path`. Oracle: CodeGraph MCP impact/caller checks, `rg` no-use scan, owner-first focused test shard, and public API contract tests that exclude retired exports. |
| Owner-first production path | `ownership.build_sample_local_owners`, `cross_sample_peak_groups.construct_cross_sample_peak_group_hypotheses`, `owner_clustering.cluster_sample_local_owners`, `pre_backfill_consolidation.consolidate_pre_backfill_identity_families`, `backfill_scope.select_backfill_features`, `owner_backfill.build_owner_backfill_cells`, `owner_matrix.build_owner_alignment_matrix` | current production path that builds sample-local owners, constructs successor owner groups, adapts them to `OwnerAlignedFeature`, then delivers backfill/matrix/process through `OwnerGroupDeliveryFeature`; downstream evidence judges these objects rather than replacing delivery | `compatibility_adapter_candidate`, `keep_as_stage`, or `contract_hardened_input` per row above. Oracle: successor-constructor, owner/backfill/matrix/process tests plus `alignment_matrix.tsv` and `alignment_cells.tsv` parity. |
| Claim and consolidation policy | `claim_registry.apply_ms1_peak_claim_registry`, `primary_consolidation.consolidate_primary_family_rows` | duplicate claim, winner/loser, demotion, and loser audit semantics; not generic grouping and not replaced by downstream duplicate-pressure flags | `keep_as_stage` after C6-B active-stage hardening. Oracle: claim registry / primary consolidation tests plus cells/review writer-visible parity. |
| Matrix identity and production projection | `cell_quality.build_cell_quality_decisions`, `matrix_identity.build_matrix_identity_decisions`, `promotion_policy.classify_backfill_promotion`, `machine_decision.project_machine_decision`, `production_decisions.build_production_decisions`, `production_candidate_gate.evaluate_production_candidate_gate` | production/provisional/audit policy and writer-facing row/cell decisions; C6 can only characterize these, not merge them into grouping helpers | `keep_as_stage` / `contract_only`; policy changes need separate behavior spec. Oracle: matrix identity, production decision, production gate, and public output parity tests. |
| Compatibility and scoring helpers | `compatibility.*`, `family_compatibility.*`, `edge_scoring.evaluate_owner_edge`, `drift_evidence.*`, `rt_normalization.*`, `adduct_annotation.*`, `owner_area.*`, `trace_context.*` | evidence, compatibility, area-rollup, trace-context, and annotation helpers used by stages; inventory their consumers before moving or sharing them | `contract_harden`; local cleanup only after consumers and parity fixture are named. Oracle: compatibility/edge evidence/drift/adduct/owner-area tests plus owner-edge and matrix parity when emitted. |
| Output and public delivery | `tsv_writer.write_alignment_matrix_tsv`, `tsv_writer.write_alignment_review_tsv`, `tsv_writer.write_alignment_cells_tsv`, `xlsx_writer.write_alignment_results_xlsx`, `html_report.write_alignment_review_html`, `debug_writer.*`, `pipeline_outputs.write_outputs_atomic`, `output_rows.*`, `output_levels.*` | public contract projection; any C6-B/C oracle must name which writer-facing values are protected | `keep_as_stage` / `contract_only`; no grouping consolidation. Oracle: writer tests, debug writer tests, output-level tests, and the Public Output Oracle Matrix in this spec. |
| Tier2 trace and candidate-gate sidecars | `tier2_trace_producer.build_tier2_trace_evidence_rows`, `production_candidate_gate.evaluate_production_candidate_gate`, `tools/diagnostics/tier2_raw_trace_reread_producer.py`, `tools/diagnostics/provisional_backfill_candidate_gate.py` | diagnostic/gate sidecar family that can support production-candidate decisions and shared-peak evidence review | `diagnostic_preserve` / `contract_only`; no grouping consolidation. Oracle: sidecar schema/value/provenance parity plus candidate-gate decision parity. |
| Diagnostics and evidence review | `identity_coherence_adapter.run_identity_coherence_diagnostic`, `identity_coherence/*`, `identity_coherence_validation/*`, `shared_peak_identity_explanation/*`, `near_duplicate_audit.count_near_duplicate_pairs`, `cell_region_audit.*` | maintained diagnostic/evidence code; do not classify as dead code merely because it is outside the primary matrix path | `keep_as_stage` / `diagnostic_preserve`; no retirement without replacement evidence. Oracle: diagnostic verdict/status/reason parity and existing diagnostic tests. |
| IO, backend, and validation adapters | `csv_io.*`, `raw_sources.*`, `ms1_index_source.*`, `process_backend.*`, `legacy_io.*`, `validation_pipeline.*`, `validation_writer.*`, `validation_compare.*` | adapter and validation surfaces; C6 should not move them unless a separate IO/backend cleanup slice owns the public contract | `out_of_scope_adapter`; belongs to IO/backend/validation cleanup, not C6 grouping. Oracle must be defined in that separate adapter spec. |
| Models and contracts | `models.*`, `matrix.*`, `ownership_models.*`, `config.AlignmentConfig`, `output_levels.AlignmentOutputLevel`, package `__init__` exports | shared contracts; inventory consumers before renaming fields, moving dataclasses, or changing compatibility imports | `contract_only`; no renames or field movement in C6. Oracle: import/schema/consumer parity and output-level tests if touched. |

Initial C6-A classification from this map:

- `keep_as_stage`: owner-first production path stages after C6-M except the
  owner-family construction semantics now owned by the successor constructor;
  claim registry, primary consolidation, matrix identity, production
  projection, public writers.
- `compatibility_adapter_candidate`: `owner_clustering.py` after C6-M. It keeps
  the public `OwnerAlignedFeature` facade while successor groups own
  construction; C6-D narrows concrete DTO dependency by routing
  owner-backfill, owner-matrix, and process payloads through
  `OwnerGroupDeliveryFeature`.
- `semantic_migration_candidate`: no active owner-family C6-B row remains in
  this state. Future owner-family migration must reopen a parity-backed cleanup
  slice instead of treating A1/A2/A3 shadow projections as production
  ownership. The event-first path / `clustering.py` has moved from semantic
  migration candidate to retired after public-shim no-use proof.
- `contract_harden`: pre-backfill consolidation, near-duplicate folding,
  backfill scope, promotion/machine-decision projection, compatibility helpers
  with broad consumers.
- `rename_or_document`: modules whose names hide whether they are product
  policy or diagnostic projection after C6-A inventory.
- `targeted_cleanup_candidate`: only a helper or module with identical
  semantics, named consumers, and a parity oracle.
- `retired`: event-first `clustering.py` / `backfill.py` and the prior
  event-family helpers after C6-B/C public-shim no-use proof. New retire
  candidates still need the same production/diagnostic/handoff/public-consumer
  scan plus a removal/migration plan.

## Disposition Result-To-Action Rules

C6-A is complete only if every row has a mechanical exit:

| Disposition | Required row-level result |
| --- | --- |
| `keep_as_stage` | Name the invariant already protected, the existing oracle or public surface that protects it, and say `no C6 cleanup now`. |
| `rename_or_document` | Name the exact doc/module note/name to change, or close the row as `keep_as_stage` if the name is acceptable. |
| `contract_harden` | Name the missing invariant/test/oracle, the blocker it protects against, and the reclassification rule after hardening. After C6-B, the row must become `keep_as_stage` or `targeted_cleanup_candidate`. |
| `semantic_migration_candidate` | Name the successor model, legacy invariants to migrate, legacy tests to port/delete, compatibility surface, and stop condition. After migration, the row must become `keep_as_stage` internal implementation, `rename_or_document` compatibility adapter, or `retire_candidate`. |
| `targeted_cleanup_candidate` | Name one cleanup slice, affected files, affected public surfaces, and the required parity oracle before edits. |
| `retire_candidate` | Name no-use evidence, compatibility impact, removal plan, and rollback/verification. |

`contract_harden` is not a permanent parking state. If C6-A cannot name the
missing test or invariant for a `contract_harden` row, the row must be
reclassified as `keep_as_stage` with a residual-risk note instead of pretending
that an unspecified hardening task exists.

## Value Assessment Rules

A stage has current value if any of these are true:

- it affects production matrix rows or identity decisions;
- it protects duplicate, claim, winner/loser, owner, primary, provisional, or
  review semantics;
- it emits audit evidence that explains a product decision;
- it supports diagnostics needed to validate product behavior;
- it defines a stable handoff surface for downstream analysis;
- it is a compatibility surface that cannot be removed without a migration
  contract.

A stage can become `retire_candidate` only if all of these are true:

- no production pipeline entrypoint uses it;
- no current tests, diagnostics, docs, or handoff notes depend on it;
- it does not preserve a compatibility import or file format;
- no diagnostic or audit value remains;
- removal has a compatibility and verification plan.

## Golden Parity Surfaces

Any future C6-B/C implementation must name the smallest relevant oracle before
editing code. Candidate surfaces include:

- focused unit tests for the touched stage;
- row-level parity for `alignment_matrix.tsv`;
- row-level parity for `alignment_review.tsv`;
- row-level parity for `alignment_cells.tsv`;
- claim registry winner/duplicate assignment parity;
- primary consolidation winner/loser/audit parity;
- matrix identity primary/provisional/audit parity.

Hash-identical TSV output is preferred for broad move-only refactors. Narrow
stage tests are acceptable only when the touched helper cannot affect downstream
matrix delivery or when the phase explains why the narrower oracle is enough.

### Public Output Oracle Matrix

When a C6-B/C cleanup can affect writer-facing behavior, use this matrix before
editing. The canonical output-level source is
`xic_extractor/alignment/output_levels.py`; path construction is in
`xic_extractor/alignment/pipeline_outputs.py`; output contract rationale is in
[Untargeted alignment output contract](retired-provenance:a8d826fd641c).

| Surface | Minimum oracle for C6-B/C |
| --- | --- |
| `alignment_matrix.tsv` | Schema/order parity plus row/value parity; broad refactors require hash-identical output. |
| `alignment_review.tsv` | Schema/order parity plus row-level `decision`, `confidence`, counts, flags, and reason parity. |
| `alignment_cells.tsv` | Schema/order parity plus row-level status, source candidate, area, RT, trace quality, and claim/duplicate fields parity. |
| `alignment_cell_integration_audit.tsv` | Schema/order parity plus row/value parity when the integration audit is emitted. |
| `alignment_owner_backfill_seed_audit.tsv` | Schema/order parity plus backfill seed, dependency, and support-label parity when emitted. |
| `alignment_matrix_status.tsv` | Schema/order parity plus status-cell parity when emitted. |
| `event_to_ms1_owner.tsv` | Row parity for event-to-owner assignment and owner metadata when emitted. |
| `ambiguous_ms1_owners.tsv` | Row parity for ambiguous-owner records and reasons when emitted. |
| `owner_edge_evidence.tsv` | Row parity for edge evidence that is intentionally emitted; envelope-rejected pairs remain governed by the existing owner-edge contract. |
| `skipped_evidence_ledger.tsv` | Schema/order parity plus skipped reason/status count parity when emitted. |
| `alignment_results.xlsx` | Workbook sheet-name/order and Matrix sheet value parity when emitted; deeper workbook sheets follow their underlying TSV/projection oracle. |
| `review_report.html` | Content-smoke parity for summary counts, duplicate/claim warnings, and linked artifact names; byte-identical HTML is not required unless the phase changes rendering only. |
| `alignment_run_metadata.json` | Metadata key parity when output-level, runner, baseline, or emitted artifact behavior is touched. |
| `alignment_production_candidate_gate.tsv` | Schema/order parity plus row-level gate decision, blocker, context, evidence-tier, and Tier2 availability parity when candidate-gate sidecars are emitted or consumed. |
| `alignment_production_candidate_gate.json` | Key/value parity for gate summary, source artifact hashes, Tier2 subset metadata, and emitted artifact paths when candidate-gate sidecars are emitted. |
| `alignment_tier2_trace_evidence.tsv` | Schema/order parity plus row-level evidence status, raw/provenance fields, scan/intensity metrics, blocker labels, criteria version, producer version, and subset hash parity. |
| `alignment_tier2_raw_manifest.tsv` | Schema/order parity plus raw path/sample/provenance/hash rows when Tier2 trace evidence is regenerated or consumed. |
| `alignment_tier2_trace_evidence_summary.json` | Key/value parity for Tier2 evidence counts, provenance, source artifact hashes, and generated artifact metadata. |
| identity coherence outputs | Diagnostic verdict/status/reason parity when the identity coherence diagnostic is emitted or when C6 touches its inputs. |

If the touched stage affects `output_level` routing, writer inclusion, or
artifact naming, `tests/test_alignment_output_levels.py`,
`tests/test_alignment_pipeline_outputs.py`, and the relevant writer tests become
part of the required oracle.

## Stop Rules

Stop C6 and write a separate behavior spec if the work requires:

- changing alignment output values;
- changing TSV schemas;
- changing primary/provisional/audit identity policy;
- changing owner membership or claim assignment behavior;
- changing winner/loser demotion;
- changing review reasons or diagnostic labels;
- deleting a diagnostic evidence source that still supports validation;
- extracting a helper that needs stage-specific side effects to remain correct.

## Verification

C6-A is docs-only. Required smoke checks:

```powershell
codegraph status
codegraph files --filter xic_extractor/alignment --format flat --no-metadata
rg -n "run_alignment|_build_event_first_matrix|cluster_candidates|build_sample_local_owners|cluster_sample_local_owners|select_backfill_features|build_owner_backfill_cells|build_owner_alignment_matrix|backfill_alignment_matrix|build_ms1_feature_families|integrate_feature_family_matrix|fold_near_duplicate_clusters|count_near_duplicate_pairs|apply_ms1_peak_claim_registry|consolidate_primary_family_rows|build_matrix_identity_decisions|build_production_decisions|build_cell_quality_decisions|classify_backfill_promotion|project_machine_decision|evaluate_production_candidate_gate|consolidate_pre_backfill_identity_families|run_identity_coherence_diagnostic|identity_gates|write_alignment_matrix_tsv|write_alignment_review_tsv|write_alignment_cells_tsv|write_alignment_results_xlsx|write_alignment_review_html|write_outputs_atomic|artifact_names_for_output_level" xic_extractor/alignment tests
git diff --check
```

If C6-B/C later touches code, that later phase must add focused tests for the
touched stage and run the CI-equivalent shard required by the one-goal phase
contract.

## Review Requirements

Before using this spec to launch C6 implementation:

- `implementation-contract-reviewer` checks whether public surfaces and parity
  oracles are named strongly enough.
- `strategy-challenger` is required only if the phase tries to convert C6 from
  inventory into implementation or if it claims a module can be retired.

Reviewer challenge should focus on:

- whether the stage disposition is based on product value rather than file
  aesthetics;
- whether the proposed oracle can catch matrix identity, claim, and
  winner/loser drift;
- whether any diagnostic evidence path is being mistaken for dead code;
- whether C6 is drifting back into broad grouping consolidation without proof.

## Done When For C6

C6 can close without code changes. That is acceptable if the inventory proves
that the modules have distinct value.

The phase is complete when:

- this spec is linked from the historical C6 spec;
- the current inventory is complete enough for the next one-goal cleanup phase;
- every stage has a semantics class, disposition, targetability label,
  semantic-survival label where applicable, and required next action / exit
  rule;
- every CodeGraph module family has a disposition, oracle, or out-of-scope
  reason;
- no implementation slice is selected without a parity oracle;
- any deferred cleanup candidate has a named blocker or required test.
