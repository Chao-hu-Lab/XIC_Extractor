# Cross-Sample Peak Group Public Behavior Addendum

**Date:** 2026-06-02
**Status:** Reviewed implementation contract
**Parent launch contract:** `2026-06-02-public-behavior-retirement-productization-design.md`
**Foundation contract:** `2026-06-02-c6-cross-sample-peak-group-hypothesis-shadow-contract-design.md`
**Behavior label:** public behavior change

## Review Record

Two xhigh read-only reviewers checked this addendum on 2026-06-02:

- `strategy-challenger` initially blocked the draft because it still allowed
  `OwnerAlignedFeature` / `family` to remain the real delivery owner,
  `backfill_seed_and_matrix_delivery` could pass as adapter debt, optional
  pre-backfill consolidation could remain a second family system, and group /
  gap-fill state could remain hidden in `cluster_id` and prose reasons.
  Re-check verdict: `PASS`.
- `implementation-contract-reviewer` initially blocked the draft because v3
  public schema details, metadata keys, additive-only parity, process tests,
  allowed literals, and pre-backfill completion rules were not concrete enough.
  A second check blocked a duplicate workbook `Audit` `claim_state` contract;
  this was fixed by using `group_claim_state` for the new structured group field
  while preserving the existing workbook `claim_state` column. Re-check verdict:
  `PASS`.

Historical roadmap alias: this phase was previously tracked as `C6`; product
contracts should use cross-sample peak group terminology instead of the phase
code.

## Verdict

This phase should not rebuild owner clustering. The current code already builds
cross-sample groups through `CrossSamplePeakGroupHypothesis` and then adapts
those hypotheses back to the public `OwnerAlignedFeature` facade.

The remaining product gap is public delivery:

```text
CrossSamplePeakGroupHypothesis
  -> OwnerGroupDeliveryFeature structural delivery protocol
  -> OwnerAlignedFeature compatibility facade where needed
  -> matrix / cells / review / workbook / process payloads
```

After this phase, `family` and `FAM######` remain compatibility output
language. The semantic owner is the cross-sample peak group hypothesis. Public
outputs must expose that ownership and the missing-observation / gap-fill state
instead of leaving those decisions hidden behind legacy row IDs and
`owner_backfill` wording.

The phase is not allowed to pass by adding constant successor-looking columns
to `OwnerAlignedFeature`. At least one focused acceptance path must drive a
non-`OwnerAlignedFeature` delivery object, sourced from
`CrossSamplePeakGroupHypothesis` semantics, through matrix/backfill/writer
projection. That test is the guard that this phase moved delivery semantics
instead of only renaming the legacy facade.

This phase still does not own numeric quantitation. Matrix values remain owned by the
AsLS `IntegrationResult` / primary matrix value policy.

This phase must preserve primary matrix quantitation. `alignment_matrix.tsv`
sample value columns and workbook `Matrix` sample values must remain unchanged.
Review/audit surfaces gain additive group projection columns, and backfill
queries that were actually attempted but did not produce an accepted group
rescue become explicit `unchecked` query outcomes instead of being silently
collapsed into synthetic `absent` cells. If primary matrix numeric values change,
stop and reclassify the phase as a separate validation-backed behavior diff.

## Current Codebase Snapshot

CodeGraph and targeted file reads on 2026-06-02 show:

| Surface | Current state | Phase 2 disposition |
|---|---|---|
| `cross_sample_peak_groups.py` | `CrossSamplePeakGroupHypothesis` owns constructor semantics, complete-link grouping, same-sample exclusion, hard split gates, review-only records, edge facts, and delivery metadata. | `successor_owned`; extend only when public delivery needs explicit successor projection. |
| `owner_clustering.py` | Public entrypoint returns `OwnerAlignedFeature` by adapting successor hypotheses. | `compatibility_adapter`; do not delete or rename. |
| `owner_group_delivery.py` | Structural protocol already allows `owner_backfill`, `owner_matrix`, `backfill_scope`, and process payloads to avoid concrete `OwnerAlignedFeature` dependency. | `successor_delivery_protocol`; must carry successor identity, group-delivery role, and missing-observation / gap-fill projection. |
| `owner_backfill.py` | Queries missing samples from delivery features and emits `rescued` cells with `owner_backfill` reason. | `gap_fill_adapter`; must emit machine-readable missing-observation / gap-fill state. |
| `owner_matrix.py` | Materializes detected, rescued, ambiguous, and absent cells from delivery features. | `group_projection_adapter`; must stamp successor group identity and gap-fill state on every cell. |
| `claim_registry.py` | Operates on `AlignmentMatrix` clusters/cells and may mark duplicate claim losers. | `matrix_policy_adapter`; preserve successor projection while changing claim status. |
| `primary_consolidation.py` | Consolidates duplicate primary rows after claim registry and may move cells to a winner row. | `matrix_policy_adapter`; preserve source and winner group projection without redefining numeric values. |
| `pre_backfill_consolidation.py` | Optional pre-backfill identity consolidation still depends on concrete `OwnerAlignedFeature` and `replace(...)`. | `successor-adapter required when enabled`; it cannot remain an excluded path for Phase 2 completion. |
| TSV/XLSX writers | Matrix uses `feature_family_id`; Cells/Audit expose cell status/reason; Review exposes row counts/evidence. | Public projection must expose successor group identity and gap-fill state on review/audit surfaces. |
| Process payloads | `OwnerBackfillSampleJob.features` uses `OwnerGroupDeliveryFeatures` and is pickleable. | Preserve payload compatibility; add only pickleable scalar/string fields. |

## Product Owner Rules

### Successor Owner

`CrossSamplePeakGroupHypothesis` owns:

- group identity;
- public compatibility row ID mapping;
- owner membership and owner order;
- same-sample exclusion;
- complete-link edge support/challenge evidence;
- hard split gate observations;
- review-only and ambiguous-owner facts;
- backfill seed centers and confirmation intent as group delivery metadata;
- successor-visible provenance for downstream cells.

### Delivery Protocol

`OwnerGroupDeliveryFeature` is the only allowed structural delivery protocol
for cross-sample group downstream stages in this phase. It must expose enough successor
projection to let `owner_backfill`, `owner_matrix`, process payloads, and
writers avoid treating `OwnerAlignedFeature` as the semantic owner.

The delivery protocol is considered successor-owned only when tests prove both:

- a normal `OwnerAlignedFeature` facade preserves current public compatibility;
- a non-`OwnerAlignedFeature` object carrying the same successor fields can flow
  through matrix/backfill/writer/process-smoke paths and produce the same public
  row values plus the new successor projection.

Required successor-delivery projection:

| Field | Meaning |
|---|---|
| `group_hypothesis_id` | Semantic cross-sample peak group identity. Initially may equal `FAM######`; future divergence requires a separate migration. |
| `public_family_id` | Compatibility public row ID. This remains the value currently written as `feature_family_id`. |
| `group_construction_role` | One of the allowed literals below, explaining where the group came from. |
| `group_delivery_role` | One of the allowed literals below, proving the row/cell came through the group delivery contract. |
| `group_membership_source` | One of the allowed literals below, naming the membership source. |

`OwnerAlignedFeature` may implement these as properties that map to its existing
public ID and evidence. It must remain a compatibility facade, not a second
semantic group system.

`backfill_seed_and_matrix_delivery` must not remain a non-blocking adapter debt
after this phase. The successor contract must record it as either:

- `successor_owned`, when group delivery, seed centers, missing-observation
  state, gap-fill state, matrix cell projection, writer projection, and process
  payload smoke tests pass; or
- a blocking `successor_gap`, which means this phase cannot be committed as
  complete.

`compatibility_adapter_candidate` is allowed only for the concrete
`OwnerAlignedFeature` facade itself, not for the product invariant
`backfill_seed_and_matrix_delivery`.

Allowed literals:

| Field | Allowed values |
|---|---|
| `group_construction_role` | `successor_constructor`, `successor_projection_adapter`, `pre_backfill_successor_adapter` |
| `group_delivery_role` | `successor_delivery_protocol`, `owner_aligned_feature_compatibility_facade`, `pre_backfill_successor_adapter` |
| `group_membership_source` | `cross_sample_peak_group_hypothesis`, `owner_aligned_feature_successor_projection`, `pre_backfill_cross_sample_peak_group_projection` |
| `gap_fill_state` | `observed_member`, `gap_fill_rescued`, `not_filled` |
| `missing_observation_state` | `observed`, `queried_and_detected`, `missing_not_observed`, `missing_unchecked`, `ambiguous_observation`, `duplicate_claim_loser` |
| `gap_fill_reason` | `local_owner_detected`, `group_centered_query_detected`, `not_requested_no_gap_fill`, `not_requested_review_only`, `not_requested_scope_excluded`, `not_requested_duplicate_loser`, `not_requested_ambiguous_owner`, `query_attempt_not_detected` |
| `group_claim_state` | `unclaimed_or_winner`, `duplicate_loser`, `review_only_duplicate_loser` |
| `consolidation_state` | `not_consolidated`, `primary_winner`, `primary_loser`, `moved_to_primary_winner` |

### Numeric Boundary

This phase must not change:

- selected integration;
- `area`;
- `primary_matrix_area`;
- `primary_matrix_area_source`;
- matrix sample-cell values;
- AsLS baseline policy;
- duplicate/blanking policy except for adding projection fields.

If any matrix numeric value changes, stop and reclassify the change as a
separate validation-backed behavior diff.

## Public Output Diff

### Preserved

These surfaces must keep existing row/value behavior:

- `alignment_matrix.tsv` sample value columns and Matrix workbook sheet;
- `feature_family_id` as the public compatibility row ID;
- `owner_edge_evidence.tsv` schema and values when emitted;
- output-level routing;
- process-mode pickleability;
- public `cluster_sample_local_owners(...)` return type.

### Changed

These review/audit surfaces must expose successor group projection:

| Surface | Required group projection additions |
|---|---|
| `alignment_review.tsv` | `group_hypothesis_id`, `public_family_id`, `group_construction_role`, `group_delivery_role`, `group_membership_source` |
| `alignment_cells.tsv` | review fields above plus `gap_fill_state`, `gap_fill_reason`, `missing_observation_state` |
| Workbook `Review` | row-level group projection fields above |
| Workbook `Audit` | cell-level group projection plus gap-fill/missing-observation fields |
| Workbook / run metadata | schema version bump and group policy keys |
| `alignment_owner_backfill_seed_audit.tsv` | group projection plus gap-fill request state when this sidecar is emitted |

Backfill attempts that fail validation, cannot be assessed, or find no accepted
peak must be visible on Cells/Audit/Review as `unchecked` query outcomes with
`gap_fill_state=not_filled`, `gap_fill_reason=query_attempt_not_detected`, and
`missing_observation_state=missing_unchecked`. They must not write primary matrix
values.

`alignment_matrix.tsv` may keep only `feature_family_id` to preserve downstream
statistics contracts. The phase must instead make the row-level successor
mapping visible in `alignment_review.tsv`, workbook `Review`, workbook
`Metadata`, and cell/audit surfaces.

The workbook / metadata schema must bump from `alignment-results-v2` to
`alignment-results-v3` because Phase 2 adds public group projection columns. The closeout must
state that v3 is an additive review/audit schema change and not a matrix value
change.

### Exact V3 Schema Additions

New columns must be inserted in the exact positions below.

| Surface | Existing anchor | Add immediately after anchor, in this order |
|---|---|---|
| `alignment_review.tsv` | `feature_family_id` | `group_hypothesis_id`, `public_family_id`, `group_construction_role`, `group_delivery_role`, `group_membership_source`, `consolidation_state`, `consolidation_winner_group_hypothesis_id`, `consolidation_source_group_hypothesis_id` |
| Workbook `Review` | `feature_family_id` | same columns as `alignment_review.tsv` |
| `alignment_cells.tsv` | `feature_family_id` | `group_hypothesis_id`, `public_family_id`, `group_construction_role`, `group_delivery_role`, `group_membership_source`, `gap_fill_state`, `gap_fill_reason`, `missing_observation_state`, `group_claim_state`, `claim_winner_group_hypothesis_id`, `claim_source_group_hypothesis_id`, `consolidation_state`, `consolidation_winner_group_hypothesis_id`, `consolidation_source_group_hypothesis_id` |
| Workbook `Audit` | `feature_family_id` | same columns as `alignment_cells.tsv`; the existing workbook `claim_state` column remains in its current later position and preserves existing values |
| `alignment_owner_backfill_seed_audit.tsv` | `feature_family_id` | `group_hypothesis_id`, `public_family_id`, `group_construction_role`, `group_delivery_role`, `group_membership_source`, `gap_fill_state`, `gap_fill_reason`, `missing_observation_state` |

Existing columns after the insertion point must preserve their current relative
order and values.

Metadata must include these exact keys and values:

| Key | Value |
|---|---|
| `schema_version` | `alignment-results-v3` |
| `cross_sample_peak_group_policy` | `cross_sample_peak_group_hypothesis_v1` |
| `public_family_id_policy` | `fam_compatibility_id` |
| `group_delivery_policy` | `owner_group_delivery_successor_projection_v1` |
| `gap_fill_policy` | `missing_observation_gap_fill_v1` |
| `legacy_owner_backfill_role` | `owner_backfill_as_gap_fill_materialization` |
| `pre_backfill_projection_policy` | `pre_backfill_successor_projection_required_when_enabled` |
| `matrix_value_policy` | `gaussian15_positive_asls_residual_primary` |

## Gap-Fill / Missing-Observation Semantics

Backfill is renamed semantically but not as a public CLI/config token in this
phase. The product meaning is:

```text
missing-observation query / gap-fill materialization attached to a selected
cross-sample peak group hypothesis
```

Cell projection must use a deterministic mapping:

| Cell status | `gap_fill_state` | `missing_observation_state` | Meaning |
|---|---|---|---|
| `detected` | `observed_member` | `observed` | Sample has a local owner member in the selected group. |
| `rescued` | `gap_fill_rescued` | `queried_and_detected` | Sample lacked or had a weak local owner and was materialized by group-centered query. |
| `absent` | `not_filled` | `missing_not_observed` | Sample has no accepted local owner and no accepted group-centered rescue. |
| `unchecked` | `not_filled` | `missing_unchecked` | Sample had a group-centered query attempted without an accepted rescue, or was not assessable under current scope. |
| `ambiguous_ms1_owner` | `not_filled` | `ambiguous_observation` | Local MS1 region cannot be assigned to this group without review. |
| `duplicate_assigned` | `not_filled` | `duplicate_claim_loser` | Cell lost a matrix claim to another row. |

`gap_fill_reason` must be one of the allowed literals above. It may reuse existing
`reason` text only as supporting detail; it must not force downstream users to
parse prose.

Duplicate and consolidation provenance must also be structured. A cell that
loses a claim or is moved to a winner row must not expose only prose such as
`winner=...` or `source_family=...`. It must carry machine-readable provenance:

| Field | Meaning |
|---|---|
| `group_claim_state` | `unclaimed_or_winner`, `duplicate_loser`, or `review_only_duplicate_loser`. This is the structured group claim state and does not replace the existing workbook `Audit` `claim_state` column. |
| `claim_winner_group_hypothesis_id` | Winner group identity for duplicate claim losers, blank otherwise. |
| `claim_source_group_hypothesis_id` | Original group identity for claim/consolidation provenance. |
| `consolidation_state` | `not_consolidated`, `primary_winner`, `primary_loser`, or `moved_to_primary_winner`. |
| `consolidation_winner_group_hypothesis_id` | Winner group when a row/cell is consolidated. |
| `consolidation_source_group_hypothesis_id` | Source group for moved cells or loser rows. |

Backfill CLI/config names may remain unchanged for compatibility. Human-facing
docs and metadata should explain that `owner_backfill` is now a compatibility
implementation name for gap-fill materialization.

## Legacy Disposition

| Legacy surface | Disposition after Phase 2 | Exit rule |
|---|---|---|
| `OwnerAlignedFeature` | `compatibility_adapter` | Keep while public API/tests and optional pre-backfill adapter still require the concrete dataclass. |
| `feature_family_id` / `FAM######` | `public_compatibility_id` | Keep as row ID; semantic identity is `group_hypothesis_id`. |
| `owner_clustering.py` | `public_facade_and_adapter` | Must call successor constructor; no independent clustering policy. |
| `OwnerGroupDeliveryFeature` | `successor_delivery_protocol` | Must expose successor identity and gap-fill metadata and pass non-legacy-object acceptance tests. |
| `owner_backfill` wording | `compatibility_implementation_name` | Product state is missing-observation / gap-fill; do not rename CLI/config in this phase. |
| `pre_backfill_consolidation.py` | `pre_backfill_successor_adapter` | It may remain non-default, but if enabled it must create or project successor group identity first, emit explicit `group_delivery_role=pre_backfill_successor_adapter`, preserve successor IDs, and have focused tests. If it only rewrites `OwnerAlignedFeature` fields with `replace(...)`, Phase 2 stops. |
| `claim_registry.py` | `matrix_policy_adapter` | May blank duplicate claims but must preserve group projection fields. |
| `primary_consolidation.py` | `matrix_policy_adapter` | May merge duplicate primary rows but must preserve winner/source group projection. |

## Phase 2 Checkpoints

Implementation must close these checkpoints in order. If any checkpoint cannot
be closed locally, stop for review instead of skipping to writer changes.

1. **Delivery protocol:** successor projection fields exist on the structural
   protocol; `OwnerAlignedFeature` is only one implementation; a
   non-`OwnerAlignedFeature` fixture satisfies the same protocol.
2. **Cell projection:** `AlignedCell` has structured group, gap-fill, claim,
   and consolidation fields; detected/absent/ambiguous/rescued paths stamp
   deterministic values.
3. **Gap-fill adapter:** `owner_backfill` emits `gap_fill_rescued` /
   `queried_and_detected` cells with AsLS `selected_integration` preserved.
4. **Claim and primary preservation:** claim registry and primary consolidation
   preserve projection fields and structured winner/source provenance.
5. **Pre-backfill containment:** optional pre-backfill consolidation stamps
   `pre_backfill_successor_adapter` successor projection with tests. Phase 2
   cannot be complete while this public config path lacks projection.
6. **Public writer migration:** TSV/XLSX/metadata v3 expose the additive group
   columns; matrix values and Matrix workbook values remain unchanged.
7. **Process payload smoke:** new delivery fields are pickleable and survive
   process job creation.
8. **Successor contract:** `owner_family_successor_contract.py` reports
   `backfill_seed_and_matrix_delivery` as `successor_owned` only after the
   public projection tests above exist.

## Expected Implementation Shape

1. Add successor projection properties to `OwnerGroupDeliveryFeature` and
   `OwnerAlignedFeature`. Where useful, make `CrossSamplePeakGroupHypothesis`
   satisfy the same delivery protocol through compatibility properties.
2. Add group projection fields to `AlignedCell`.
3. Stamp those fields in `owner_matrix` for detected, absent, ambiguous, and
   rescued cells, and in `owner_backfill` for gap-fill rescue cells.
4. Preserve fields through claim registry and primary consolidation. If a
   consolidation moves a cell to a winner row, the winner row ID may change but
   the cell must still expose the winner `group_hypothesis_id` and preserve
   source detail in structured provenance.
5. Add TSV/XLSX/metadata projection columns only on review/audit surfaces named
   above. Do not add sample-like columns to `alignment_matrix.tsv`.
6. Update `owner_family_successor_contract.py` so
   `backfill_seed_and_matrix_delivery` is no longer merely a hidden adapter
   claim; it must cite public projection tests for group and gap-fill state.

## Verification

Minimum focused tests:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_alignment_owner_family_successor_contract.py tests/test_alignment_owner_clustering.py tests/test_pre_backfill_consolidation.py tests/test_backfill_scope.py tests/test_alignment_owner_backfill.py tests/test_alignment_owner_matrix.py tests/test_alignment_claim_registry.py tests/test_alignment_primary_consolidation.py tests/test_alignment_matrix_identity.py tests/test_alignment_production_decisions.py tests/test_alignment_tsv_writer.py tests/test_alignment_xlsx_writer.py tests/test_alignment_debug_writer.py tests/test_alignment_output_levels.py tests/test_run_alignment.py tests/test_alignment_pipeline.py tests/test_alignment_pipeline_outputs.py
```

Include these public-contract/process tests in the same focused gate:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_alignment_process_backend.py tests/test_untargeted_final_matrix_contract.py
```

Also run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
git diff --check
```

Required new or updated tests:

- delivery protocol accepts non-`OwnerAlignedFeature` payload with successor
  projection fields and carries it through matrix/backfill/writer outputs;
- `CrossSamplePeakGroupHypothesis` can satisfy or adapt to the delivery
  protocol without changing public row values;
- `owner_matrix` stamps group projection and missing-observation state for
  detected, rescued, ambiguous, absent, unchecked, and duplicate cells;
- `owner_backfill` stamps `gap_fill_rescued` and preserves AsLS
  `selected_integration`;
- failed / unassessable `owner_backfill` queries stamp `unchecked`,
  `query_attempt_not_detected`, and `missing_unchecked` without writing matrix
  values;
- claim registry preserves group projection when marking duplicate losers;
- primary consolidation preserves projection on winner and moved cells;
- optional pre-backfill consolidation is covered by successor projection tests
  when enabled;
- TSV and XLSX tests assert additive group projection columns and metadata v3;
- public-output tests prove Matrix value parity, additive group projection
  columns, metadata v3, and the expected query-attempt `unchecked` audit diff;
- process backend pickle smoke proves the new delivery fields remain
  process-safe.

## Stop Conditions

Stop and re-review if:

- `alignment_matrix.tsv` sample values or Matrix workbook values change;
- public `FAM######` IDs are renamed or removed;
- `OwnerAlignedFeature` deletion becomes necessary;
- a non-`OwnerAlignedFeature` delivery object cannot pass matrix/backfill/writer
  projection tests;
- `backfill_seed_and_matrix_delivery` remains `compatibility_adapter_candidate`
  instead of becoming `successor_owned`;
- `owner_backfill` CLI/config names are renamed;
- cross-sample group code starts importing sample-local `PeakHypothesis` or
  `shared_peak_identity_explanation` product activation logic;
- pre-backfill consolidation creates row identity, seed centers, or owner
  membership outside successor projection;
- a test proves the successor projection is only a field rename and does not
  expose missing-observation / gap-fill state.

## Closeout Requirements

The Phase 2 closeout must state:

- public schema version and exact added columns;
- `alignment_matrix.tsv` / Matrix value parity result;
- final disposition of every legacy owner-family surface in the table above;
- whether validation used only synthetic/output-contract tests or real RAW;
- remaining risk for optional `pre_backfill_consolidation.py`;
- next owner-family cleanup candidate, if any.
