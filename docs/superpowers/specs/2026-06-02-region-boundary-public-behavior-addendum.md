# Region-Boundary Public Behavior Addendum

**Date:** 2026-06-02
**Parent launch contract:**
[C4 / C6 / Region Public Behavior Retirement Productization Design](2026-06-02-public-behavior-retirement-productization-design.md)
**Base design:**
[Region-Boundary Decision Owner Design](2026-06-02-region-boundary-decision-owner-design.md)
**Status:** Draft v0.3 - Phase 1 disposition and exit-evidence table locked;
implementation must still be verified against this contract
**Behavior label:** public behavior change

## Objective

Make `RegionSelectionDecision` the public product decision projection for
region and boundary behavior. Resolver modes may still form proposals and keep
compatibility names, but product output must no longer look as if
`region_first_safe_merge` or `shadow_verdict` alone made the decision.

Phase 1 is deliberately narrow:

- promote only the already gated adjacent-WIS safe-merge class;
- expose every other region verdict as explicit product review / no-change
  state;
- add machine-readable decision/status/reason projection to public audit and
  alignment cell/audit surfaces;
- preserve final matrix numeric values unless the existing safe-merge promotion
  already changed the selected integration result.

This addendum does not approve a new boundary oracle, CWT-only promotion,
neighbor-apex switching, split handling, or wider-boundary promotion.

## Launch Contract Closure

This addendum closes the Phase 1 launch-contract questions from the parent
productization design:

- `region_first_safe_merge` remains a public compatibility token in Phase 1.
  Its implementation is a narrow adapter over `RegionSelectionDecision`, not a
  separate product-rule family.
- `RegionSelectionDecision` is the source of product-facing region decision
  fields.
- Existing `shadow_status`, `shadow_verdict`, and safe-merge provenance fields
  remain compatibility/audit projections.
- Each verdict class below has an explicit Phase 1 disposition and exit
  evidence.

Implementation may continue only inside this disposition table. Any row that
cannot be represented by the table fails closed to `behavior_change_required`
or `review_only`; it must not silently promote a boundary, apex, area, score, or
matrix value.

## Product Owner Decision

`RegionSelectionDecision` owns the product-facing decision vocabulary:

| Field family | Product meaning |
|---|---|
| `decision_status` | Whether the region decision was evaluated or skipped. |
| `decision_class` | Evidence-backed class such as current-supported, merge-suggested, split-supported, wider-boundary-preferred, or neighbor-apex-preferred. |
| `product_action` | Product disposition: `no_change`, `safe_merge_eligible`, `review_only`, `not_counted_candidate`, or `behavior_change_required`. |
| `selected_candidate_id` / `selected_boundary_id` | Current product candidate and boundary before any approved promotion. |
| `alternate_boundary_ids` | Alternate or promoted boundary evidence considered by the decision. |
| `support_reasons` / `conflict_reasons` | Machine-readable evidence labels. |
| `audit_reason` / `promotion_reason` | Human-readable audit text and the required reason for product promotion. |
| `baseline_method` | Current baseline provenance. Under this PR it must be `asls`. |

`shadow_status`, `shadow_verdict`, `merge_suggestion_source`, and legacy
safe-merge audit fields remain compatibility projections. They are still useful,
but they are not the first-class public decision contract after Phase 1.

## Phase 1 Propagation Invariant

Decision fields must be sourced from `RegionSelectionDecision` and carried
forward. Writers must not reconstruct `decision_status`, `decision_class`,
`product_action`, `promotion_reason`, or `baseline_method` by reinterpreting
legacy `shadow_verdict`, `merge_suggestion_source`, or `merge_note` fields.

The required propagation chain is:

```text
RegionSelectionDecision
  -> PeakRegionAuditSummary
  -> AlignedCell
  -> TSV / XLSX writers
```

`PeakRegionAuditSummary` and `AlignedCell` are adapters. They may preserve
legacy `region_shadow_*` fields, but they must carry the successor decision
projection as explicit fields.

This is not a full RB2 handoff-spine migration. Formal storage of region facts
inside `IntegrationResult`, `AuditTrail`, `EvidenceVector`, or
`PeakHypothesis` remains a later slice. Phase 1 closes the public behavior
projection and prevents renderers from owning the decision.

## Legacy Resolver Disposition

`region_first_safe_merge` remains an accepted compatibility resolver token and
the current tracked settings / validation-harness default. Its semantics are
redefined for Phase 1 as:

```text
local-minimum candidate formation
  -> RegionSelectionDecision
  -> product_action gate
  -> adjacent-WIS safe-merge promotion only when safe gates pass
```

It is not a separate product-rule family and not true generalized region-first
model selection. The public name stays stable in Phase 1 to avoid config, GUI,
and validation harness churn.

`legacy_savgol` and `local_minimum` remain proposal / resolver compatibility
inputs. They do not become independent final-authority product decision systems
when region decision fields are available.

`arbitrated` remains retired.

## Verdict Exit Table

| Current `shadow_status` / `shadow_verdict` | Current Phase 1 `product_action` | Product disposition for Phase 1 | Required exit evidence |
|---|---|---|---|
| non-`evaluated` status / `insufficient_evidence` or skipped decision | `review_only` | Do not promote, switch boundaries, switch apex, or alter selected area. Keep the current selected boundary when one exists. `not_counted_candidate` is reserved for a future no-candidate policy and is not introduced by Phase 1. | Machine-readable skipped status, skipped reason, unchanged selected candidate/boundary ids, and unchanged public selected RT/area fields. |
| `evaluated` / `current_supported` | `no_change` | Product decision accepts the current selected boundary. Keep selected apex, bounds, area, confidence, and reason unchanged. | Public projection proves the current boundary was evaluated and explicitly supported, not merely retained because no alternate won. Support reasons must come from `RegionSelectionDecision`. |
| `evaluated` / `merge_suggested` with `merge_suggestion_source=adjacent_wis_local_minimum_merge` | `safe_merge_eligible` | This is the only Phase 1 class eligible to change selected bounds or selected area in extraction. `region_first_safe_merge` is only the compatibility route into this product action. | `RegionSelectionDecision.product_action == "safe_merge_eligible"` plus existing safe gates: selected interval count, interval gap, area ratio, apex delta, continuous-envelope eligibility, and `baseline_method == "asls"`. If a later gate rejects, selected output stays unchanged and `safe_merge_rejection_reason` names the blocker. |
| `evaluated` / `merge_suggested` without `adjacent_wis_local_minimum_merge` | `behavior_change_required` | Do not auto-promote. Expose the row as behavior-change-required review evidence or leave it as diagnostic-only until a stronger oracle exists. | Conflict reason names the unsupported merge source or missing safe gate. No selected-boundary, selected-area, confidence, reason, matrix, TSV schema, or workbook schema change is allowed from this class. |
| `evaluated` / `wider_boundary_preferred` | `behavior_change_required` | Do not widen boundaries in Phase 1. The product output must not look like the concern was ignored; it must carry behavior-change-required review state. | Changed-row note and validation-evidence review are required before any future automatic widening. Phase 1 evidence is only projection parity: unchanged selected boundary plus explicit conflict reason. |
| `evaluated` / `neighbor_apex_preferred` | `behavior_change_required` | Do not switch apex in Phase 1. Neighbor-apex evidence remains review-only unless a future apex identity oracle is approved. | Apex identity oracle, changed-row contract, and public projection tests are required before future promotion. Phase 1 must prove unchanged selected apex and explicit conflict reason. |
| `evaluated` / `split_supported` | `behavior_change_required` | Treat as mixed or compound interval evidence. Do not collapse it into a single promoted boundary in Phase 1. | Split/mixed-peak oracle, downstream matrix policy, and expected changed rows are required before future promotion. Phase 1 must prove unchanged selected boundary/area and explicit conflict reason. |
| Any future or unrecognized evaluated verdict class | `behavior_change_required` unless a reviewed addendum says otherwise | Fail closed. New verdict vocabulary is not product authority by default. | New row in this table, output-contract tests, and reviewer-approved public behavior addendum before promotion. |

The only Phase 1 class allowed to change selected bounds or selected area in
extraction is the existing adjacent-WIS safe-merge class after all safe gates
pass. Alignment Phase 1 does not use this class to promote matrix numeric
values.

The exit evidence must be produced from `RegionSelectionDecision` fields or
direct adapters that carry those fields. Tests may compare legacy
`shadow_verdict` columns for compatibility, but they must not prove Phase 1
product behavior by recomputing the decision from legacy columns in writers.

## Public Surface Contract

### Extraction product result

`find_peak_and_area(...)` keeps its return shape. The selected peak result may
change only for approved safe-merge promotion, which already exists today under
the `region_first_safe_merge` resolver.

Phase 1 implementation must ensure that safe-merge promotion is visibly sourced
from `RegionSelectionDecision.product_action == "safe_merge_eligible"`, not
from resolver name alone.

### Peak candidate TSV

`peak_candidates.tsv` already exposes safe-merge promotion and rejection fields.
Phase 1 preserves those fields and does not add peak-candidate columns. The
candidate table remains a compatibility surface for selected-candidate audit;
the canonical public region decision projection is the region shadow TSV plus
cell-level alignment audit projection.

### Region shadow TSVs

`peak_region_selection_shadow.tsv` and
`peak_region_selection_shadow_summary.tsv` become the first public audit surface
for the product decision projection. They must add these columns:

- `decision_status`
- `decision_class`
- `product_action`
- `selected_candidate_id`
- `selected_boundary_id`
- `alternate_boundary_ids`
- `evidence_sources`
- `support_reasons`
- `conflict_reasons`
- `audit_reason`
- `promotion_reason`
- `baseline_method`

The old `shadow_*` columns stay for compatibility and side-by-side audit.

### Alignment outputs

`alignment_matrix.tsv` and workbook `Matrix` numeric cells do not receive new
columns in Phase 1. Their numeric values remain owned by the selected
`IntegrationResult` / AsLS primary matrix value policy.

`alignment_cells.tsv` must expose the region decision when the source cell has
region audit context. Required new cell fields:

- `region_decision_status`
- `region_decision_class`
- `region_product_action`
- `region_promotion_reason`
- `region_baseline_method`

Existing `region_shadow_*` fields remain compatibility projections.

`alignment_review.tsv` and workbook `Review` are family-level surfaces. Phase 1
does not add family-level region decision fields there because multiple cells in
one family may disagree. A future C6/Region follow-up may add deterministic
aggregate fields after it defines row-level aggregation semantics.

Workbook `Audit` is cell-level and must add the same `region_decision_*` fields
as `alignment_cells.tsv`. Workbook `Matrix` and `Review` headers remain
unchanged.

Workbook metadata `schema_version` must become `alignment-results-v2` when the
Audit sheet carries the new region decision columns. This is an intentional
public schema bump for the workbook. `alignment_matrix.tsv` keeps its existing
schema. TSV files do not currently carry a metadata schema version; their
header-order tests are the contract.

### Config, GUI, CLI, and validation harness

No resolver default changes in Phase 1:

- settings schema default remains `region_first_safe_merge`;
- GUI resolver choice remains available;
- discovery CLI continues to accept `region_first_safe_merge` and default to its
  current workflow-specific value;
- alignment CLI continues to accept `region_first_safe_merge`;
- alignment production metadata may continue to coerce
  `region_first_safe_merge` to `local_minimum` until a separate alignment
  validation spec promotes true region-safe-merge behavior for alignment.

This is intentional. Phase 1 productizes the decision projection and the
already approved safe-merge promotion class; it does not use a resolver rename
as the product change.

The alignment coercion is part of Phase 1's safety boundary, not an accidental
legacy leak. Alignment may project region decision evidence for review, but
alignment matrix numeric production remains on the existing `local_minimum`
coercion path.

## Expected Public Diff

Expected changes:

- New machine-readable region decision columns in region shadow TSVs.
- New region decision projection columns in `alignment_cells.tsv` and workbook
  `Audit` when those surfaces are emitted.
- Workbook metadata `schema_version` changes to `alignment-results-v2` when the
  new workbook Audit columns are emitted.
- Extraction safe-merge product behavior remains gated by
  `RegionSelectionDecision`, with no new auto-promotion classes.
- Existing safe-merge selected-boundary/area changes remain possible only in the
  extraction `region_first_safe_merge` path.

Expected non-changes:

- No new `linear_edge` semantics.
- No selected-boundary or selected-area changes for wider-boundary,
  neighbor-apex, split, or unsupported merge verdicts.
- No `alignment_matrix.tsv` schema change.
- No workbook `Matrix` sheet schema change.
- No workbook `Review` sheet schema change.
- No resolver default or accepted-value change.
- No CWT-only promotion.
- No alignment numeric-matrix promotion from region decision fields.

## Test And Verification Contract

Minimum focused Phase 1 command:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_signal_processing.py tests/test_signal_processing_selection.py tests/test_region_model_selection.py tests/test_region_safe_merge.py tests/test_peak_region_selection_shadow.py tests/test_boundary_hypotheses.py tests/test_boundary_scoring.py tests/test_peak_candidate_boundaries.py tests/test_peak_candidate_table.py tests/test_cwt_proposals.py tests/test_cwt_peak_candidate_audit.py tests/test_config.py tests/test_settings_section.py tests/test_settings_section_advanced.py tests/test_settings_new_fields.py tests/test_gui_main.py tests/test_run_discovery.py tests/test_discovery_pipeline.py tests/test_csv_writers.py tests/test_csv_to_excel.py tests/test_excel_pipeline.py tests/test_excel_sheets_contract.py tests/test_alignment_tsv_writer.py tests/test_alignment_xlsx_writer.py tests/test_alignment_owner_matrix.py tests/test_run_alignment.py tests/test_validation_harness.py
```

Required focused assertions:

- `RegionSelectionDecision` fills decision/product projection fields for every
  verdict class.
- Safe-merge eligibility requires `product_action == "safe_merge_eligible"`.
- Unsupported merge, wider-boundary, neighbor-apex, and split verdicts remain
  non-promoting public review states.
- Region shadow TSV headers include the new decision projection.
- `PeakRegionAuditSummary` and `AlignedCell` carry decision fields directly
  from `RegionSelectionDecision`; writer tests must not prove decision fields
  only by recomputing from `shadow_verdict`.
- `alignment_cells.tsv` and workbook `Audit` include the new per-cell region
  decision projection.
- `alignment_review.tsv` and workbook `Review` headers remain unchanged in
  Phase 1.
- Workbook Metadata records `schema_version=alignment-results-v2` for the new
  workbook schema.
- Config/GUI/CLI defaults and accepted resolver modes remain unchanged.
- `alignment_matrix.tsv` numeric cells and schema remain unchanged in synthetic
  output-contract tests unless an existing safe-merge selected integration is
  explicitly part of the fixture.

Real-data validation is not mandatory for this phase unless implementation
changes final matrix numeric values beyond the existing safe-merge behavior.
If representative output changes final matrix values, add a changed-row note
and run `validation-evidence-reviewer` acceptance before committing.

## Stop Rules

Stop and return to design if implementation would:

- promote wider-boundary, neighbor-apex, split, or unsupported merge verdicts;
- change resolver defaults or reject currently accepted resolver values;
- alter `alignment_matrix.tsv` schema;
- change workbook `Matrix` schema;
- add region decision fields to family-level alignment review outputs without a
  deterministic aggregation contract;
- reintroduce `linear_edge`;
- use CWT, WIS, local minima, RT, shape, S/N, or score as a hidden
  single-source authority;
- require RAW validation without a reviewed preflight and changed-row contract.
