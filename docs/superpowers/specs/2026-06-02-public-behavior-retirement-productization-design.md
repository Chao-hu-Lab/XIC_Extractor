# C4 / C6 / Region Public Behavior Retirement Productization Design

**Date:** 2026-06-02
**Branch:** `codex/cleanup-retirement-foundation`
**Status:** Reviewed launch contract; Phase 1 addendum required before
implementation
**Behavior label:** public behavior change

## Objective

Move the remaining C4, C6, and Region retirement work from
`no public behavior change` foundation into production behavior in one goal with
three ordered phases. This document is a launch contract: implementation may not
start until each phase has a reviewed behavior addendum that closes the owner,
public diff, legacy disposition, and exit-rule table for that phase.

This goal is not a cleanup-only pass. It is allowed to change selected
boundaries, selected candidates, public confidence/reason projections, cross
sample group ownership, gap-fill/backfill semantics, matrix row/group delivery,
and review/audit provenance only when the phase behavior spec names the expected
diff, the output contract records the decision reason, and tests or validation
prove the new behavior is intentional.

## Context To Read First

- `AGENTS.md`
- `docs/agent-subagent-routing.md`
- `docs/agent-parameter-settings.md`
- `docs/superpowers/notes/2026-06-02-c4-c6-region-foundation-closeout.md`
- `docs/superpowers/specs/2026-06-01-c4-peak-scoring-evidence-decision-design.md`
- `docs/superpowers/specs/2026-06-02-c6-cross-sample-peak-group-hypothesis-shadow-contract-design.md`
- `docs/superpowers/specs/2026-06-02-region-boundary-decision-owner-design.md`
- `docs/superpowers/specs/2026-06-02-mature-package-flow-reference-spec.md`

## Subagent Review Record

Two xhigh read-only reviewers checked this launch contract on 2026-06-02:

- `strategy-challenger` initially blocked the draft because C4/C6 successor
  owners were too abstract, phase order did not match the mature-flow reference,
  C6 adapter language could preserve a bad legacy path, and Region lacked a
  per-verdict exit table. Re-check verdict: prior blockers closed for
  launch-contract purposes.
- `implementation-contract-reviewer` initially blocked the draft because Region
  output-contract coverage was incomplete, C6 overclaimed matrix value
  ownership, and schema/versioning detail was deferred too far. Re-check
  verdict: prior blockers closed for the top-level launch contract.

This review does not approve immediate implementation. The next executable step
is a Phase 1 Region behavior addendum with the same xhigh review gate.

## Current Foundation Verdict

| Area | Current product owner | Successor state | Retirement gap |
|---|---|---|---|
| Region / boundary | Resolver path behind `find_peak_and_area(...)`, with `region_first_safe_merge` as an opt-in safe-merge mode. | `RegionSelectionDecision` exists as typed internal projection. | Boundary decision is not yet the default product owner. Resolver tokens still shape product behavior. |
| C4 scoring / evidence decision | `peak_scoring.py::score_candidate(...)` and `select_candidate_with_confidence(...)`. | `EvidenceVector`, `CommonEvidence`, and decision-semantics projections exist. | Raw score, caps, and legacy reason projection still own candidate selection and public confidence/reason. |
| C6 cross-sample owner / family | `OwnerAlignedFeature` delivery through `owner_clustering.py`, backfill, owner matrix, claim registry, primary consolidation, and writers. | `CrossSamplePeakGroupHypothesis` exists and can construct groups before adapting back to `OwnerAlignedFeature`. | Downstream group delivery, row identity, provenance, and gap-fill/backfill still consume legacy delivery DTOs. |

## Non-Negotiable Product Rules

- `linear_edge` remains retired from product quantitation. No phase may
  reintroduce linear-edge area, naming, fallback, or final-matrix semantics.
- ASLS remains the product baseline for area integration unless a separate
  baseline behavior spec changes it.
- Evidence chains own decisions. CWT, WIS, local minima, RT, shape, local S/N,
  MS2 trace, product ions, and neutral loss evidence are allowed to support or
  challenge a decision, but no single evidence source may silently overrule the
  whole decision.
- Public import facades may remain for compatibility, but their product
  semantics must point inward to the successor owner after the relevant phase.
- Every product behavior change must emit machine-readable reason/status fields
  or preserve a documented projection into existing public fields.
- Public schema changes require explicit schema migration language. If a phase
  preserves old column names while changing semantics, the compatibility meaning
  must be documented in the phase closeout.
- Each phase must complete and commit before the next phase starts.

## Goal Shape

**Goal:** Productize the successor behavior for Region, C4, and C6, then retire
or demote the matching legacy behavior owners so the project no longer maintains
two product-rule systems for the same decision.

**Done when:**

1. Region product behavior is owned by an evidence-backed boundary decision
   surface instead of a resolver-only rule path.
2. C6 product cross-sample grouping, missing-observation / gap-fill state, and
   delivery adapter boundaries are owned by `CrossSamplePeakGroupHypothesis`,
   while the numeric primary matrix value remains owned by the AsLS
   `IntegrationResult` / primary matrix value policy.
3. C4 product candidate selection and confidence/reason projection are owned by
   a concrete selected-hypothesis decision surface instead of raw score/cap
   authority.
4. Each phase has:
   - a behavior spec update or phase addendum;
   - xhigh subagent review of that behavior spec before implementation;
   - implementation review after the behavior change;
   - focused tests and output-contract tests;
   - one commit;
   - a short closeout note naming expected public diffs and remaining risks.
5. The final branch passes the CI-equivalent PR gate:

   ```powershell
   $env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests
   $env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
   $env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x
   ```

**Stop if:**

- a phase cannot name the successor product owner;
- a phase changes final matrix values, selected peaks, selected areas,
  confidence, reason text, workbook schemas, TSV schemas, or config behavior
  without an expected-diff contract;
- a reviewer identifies a blocker that would change phase direction and the
  blocker cannot be closed locally;
- verification proves the successor only renames the legacy owner rather than
  absorbing its invariant;
- the required validation becomes expensive enough that a
  `validation-evidence-reviewer` preflight is needed but has not been completed.

## Mandatory Phase Gate

Each phase follows the same sequence:

1. Update the relevant behavior spec or add a phase addendum.
2. Dispatch xhigh read-only subagent review before implementation:
   - `strategy-challenger` checks product direction, strongest assumption,
     decision ownership, exit rule, and whether the phase is trying to preserve
     a bad legacy path.
   - `implementation-contract-reviewer` checks public contract touched,
     downstream surface, tests, schema/config/CLI/workbook/TSV implications, and
     whether the successor can actually own the invariant.
   - Add `validation-evidence-reviewer` in `preflight` mode before any 8RAW,
     85RAW, or production-equivalent validation run.
3. Main agent fixes blocking review findings in the spec.
4. Implement the phase.
5. Run focused tests and output-contract tests.
6. Dispatch xhigh implementation review:
   - `implementation-contract-reviewer` is mandatory.
   - Add `tester` when behavior or output tests changed enough that
     independent verification matters.
   - Add `validation-evidence-reviewer` in `acceptance` mode when the phase
     relies on real-data or production-equivalent validation.
7. Fix blockers, rerun the relevant tests, write closeout, and commit.

## Phase Order

Run phases in this order:

1. Region / boundary productization.
2. C6 cross-sample group and delivery productization.
3. C4 selected-hypothesis evidence decision productization.

This order follows the mature-flow reference:

1. Region settles single-trace boundary/area decision ownership first.
2. C6 then migrates cross-sample grouping and missing-observation delivery while
   using the settled MS1 morphology / primary matrix area policy for numeric
   values.
3. C4 moves selected-hypothesis confidence/reason ownership last, after the
   cross-sample delivery spine is less dependent on legacy scorer wording.

If a phase closeout proves the next phase order no longer closes the next
highest-risk product decision, stop and re-review the remaining order before
continuing.

## Launch-Readiness Tables

Each phase addendum must fill the table below before implementation starts.
This top-level table names the required owner boundaries and reviewer exit
conditions.

| Phase | Concrete successor product owner | Public diff owner | Legacy disposition required before implementation | Exit rule |
|---|---|---|---|---|
| Region | Existing `RegionSelectionDecision` with `decision_status`, `decision_class`, `product_action`, `selected_candidate_id`, `selected_boundary_id`, `support_reasons`, `conflict_reasons`, and `baseline_method`. | `find_peak_and_area(...)`, candidate/region TSVs, extraction workbook, resolver config/GUI/CLI, downstream alignment outputs when areas propagate. | `region_first_safe_merge` becomes a compatibility token or narrow adapter inside `RegionSelectionDecision`; `legacy_savgol` and `local_minimum` become proposal/resolver compatibility inputs, not independent final-authority systems. | Region addendum lists every current `shadow_verdict/product_action` class as promote, no-change, review-only, externalized diagnostic, or retired. |
| C6 | Existing `CrossSamplePeakGroupHypothesis` owns group identity, group membership, same-sample exclusion, drift-edge facts, review-only facts, missing-observation / gap-fill state, and successor-visible provenance. | `alignment_cells.tsv`, `alignment_review.tsv`, `alignment_matrix.tsv` row/group identity, workbook review/audit/metadata, process payloads, `FAM######` compatibility IDs, successor group IDs. Numeric sample-cell value remains owned by the MS1 morphology / primary matrix area policy and is not owned by C6. | `OwnerAlignedFeature` may remain only as a delivery adapter sourced from successor hypotheses. Claim registry, owner matrix, primary consolidation, backfill, and writers must either consume successor groups directly or be explicitly named adapters. | C6 addendum separates group/gap-fill ownership from numeric primary matrix value ownership and proves every downstream consumer is successor-owned or adapter-owned. |
| C4 | New concrete `PeakHypothesisSelectionDecision` product surface, backed by `EvidenceVector.decision_semantics` / `CommonEvidence`, with selected candidate, decision class, confidence projection, reason projection, support reasons, and conflict reasons. | Candidate selection, `confidence`, `reason`, score/calibration report projection, candidate TSV, CSV/XLSX/workbook fields, and any target/discovery public output that exposes support or concern text. | `peak_scoring.py` remains only a compatibility facade or diagnostic support module after the phase; raw score/cap cannot remain final product authority. | C4 addendum proves selected-candidate and public-projection behavior by decision oracle or names expected changed rows; raw-score parity is not the product oracle. |

## Phase 1 - Region / Boundary Productization

### Product Decision

`RegionSelectionDecision` becomes the internal product owner for boundary
selection and integration decisions. Resolver modes may still provide candidate
intervals or compatibility entry points, but the final product boundary decision
must be represented as an evidence-backed `RegionSelectionDecision`.

`region_first_safe_merge` should stop being a separate product-rule family. It
should become either:

- a compatibility token that routes into the evidence-backed boundary policy; or
- a narrow adapter for the specific safe-merge promotion class inside the
  boundary decision owner.

The phase behavior spec must choose one of those two dispositions before code
changes start.

### Region Verdict Exit Table

The Phase 1 addendum must start from this table and may tighten it only with
reviewed evidence:

| Current `shadow_status` / `shadow_verdict` | Current `product_action` | Product disposition for Phase 1 | Required exit evidence |
|---|---|---|---|
| non-`evaluated` statuses with `insufficient_evidence` | `review_only` | Product decision is visible review-only; no boundary promotion. | Machine-readable skipped reason and unchanged selected boundary. |
| `evaluated` / `current_supported` | `no_change` | Product decision accepts the current selected boundary. | Public projection proves the current boundary is explicitly supported, not merely retained by absence of evidence. |
| `evaluated` / `merge_suggested` with `adjacent_wis_local_minimum_merge` and safe gates | `safe_merge_eligible` | Promote through the region decision owner; `region_first_safe_merge` is only the compatibility route. | Area-ratio, interval-gap, apex-delta, selected-interval count, and AsLS baseline provenance checks pass. |
| `evaluated` / `merge_suggested` without the adjacent-WIS safe gates | `behavior_change_required` or `review_only` | Do not auto-promote in Phase 1; expose as review-only or externalized diagnostic unless the addendum names a stronger oracle. | Addendum must name why promotion is safe or why review-only is the product behavior. |
| `evaluated` / `wider_boundary_preferred` | `behavior_change_required` | Do not silently retain current boundary; route to reviewed product state or explicit expected changed rows. | Changed-row note, output-contract tests, and validation-evidence review when matrix values change. |
| `evaluated` / `neighbor_apex_preferred` | `behavior_change_required` | Do not auto-switch apex without a named oracle; route to reviewed product state or expected changed rows. | Apex identity oracle, changed-row note, and public projection tests. |
| `evaluated` / `split_supported` | `behavior_change_required` | Treat as mixed/compound interval evidence; no single promoted boundary unless the addendum proves split handling. | Split/mixed-peak oracle, downstream matrix policy, and expected changed rows or review-only status. |

### Allowed Public Behavior Diff

- Selected left/right boundary, selected RT, integration area, and candidate
  audit rows may change when the evidence-backed decision promotes or rejects a
  boundary.
- Existing resolver tokens may be retained, aliased, deprecated, or rejected
  only if the phase spec names the public config/GUI/CLI migration.
- `legacy_savgol` and `local_minimum` remain useful proposal sources unless the
  phase proves their product role is fully absorbed.
- CWT may contribute named morphology/boundary evidence, but it must not become
  a single-source authority.

### Verification

Minimum focused tests:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_signal_processing.py tests/test_signal_processing_selection.py tests/test_region_model_selection.py tests/test_region_safe_merge.py tests/test_peak_region_selection_shadow.py tests/test_boundary_hypotheses.py tests/test_boundary_scoring.py tests/test_peak_candidate_boundaries.py tests/test_peak_candidate_table.py tests/test_cwt_proposals.py tests/test_cwt_peak_candidate_audit.py tests/test_config.py tests/test_settings_section.py tests/test_settings_section_advanced.py tests/test_settings_new_fields.py tests/test_gui_main.py tests/test_run_discovery.py tests/test_discovery_pipeline.py tests/test_csv_writers.py tests/test_csv_to_excel.py tests/test_excel_pipeline.py tests/test_excel_sheets_contract.py tests/test_alignment_tsv_writer.py tests/test_alignment_xlsx_writer.py tests/test_alignment_owner_matrix.py tests/test_run_alignment.py tests/test_validation_harness.py
```

If selected areas or matrix-delivery values change in representative output,
the phase must add either targeted real-data validation or an explicit
`validation-evidence-reviewer` approved reason why synthetic/output-contract
tests are sufficient for this phase.

## Phase 2 - C6 Cross-Sample Group And Delivery Productization

### Product Decision

`CrossSamplePeakGroupHypothesis` becomes the product owner for cross-sample
group identity, group membership, same-sample exclusion, drift-edge evidence,
review-only facts, missing-observation / gap-fill state, and successor-visible
cell provenance.

C6 does not own the numeric primary matrix value. Quantitative cell values stay
under the MS1 morphology / primary matrix area policy:

```text
prefer IntegrationResult.area_ms1_morphology
where IntegrationResult.ms1_morphology_area_source
    == "gaussian15_positive_asls_residual";
fallback to AsLS only for legacy integrations without typed morphology facts
```

`OwnerAlignedFeature` may remain only as:

- a compatibility adapter for old writer/process payload contracts; or
- a public facade whose semantics are explicitly sourced from successor
  hypotheses.

Public `FAM######` identifiers may remain as compatibility IDs, but the semantic
owner should be `group_hypothesis_id`, `peak_group_id`, or another explicitly
chosen successor identifier. The phase behavior spec must decide whether public
exports add a successor ID, preserve only the compatibility ID, or migrate with
both.

### Allowed Public Behavior Diff

- Group/family row identity, membership, review/audit status, gap-fill state,
  and provenance may change only when the successor grouping or gap-fill policy
  names the expected diff.
- `alignment_matrix.tsv` and workbook `Matrix` numeric sample-cell values may
  change only as a consequence of selected integration / MS1 morphology primary
  value policy, not because C6 redefines the numeric value owner.
- Claim registry, owner matrix, primary consolidation, backfill, debug writers,
  TSV/XLSX writers, and process payloads must either consume successor groups
  directly or be marked as explicit delivery adapters.
- Backfill must be reframed as missing-observation / gap-fill evidence attached
  to the selected group hypothesis, not as a second family system.
- Same-sample merge prevention, drift-edge evidence, identity conflicts,
  review-only records, and matrix cell provenance must be successor-visible.

### Verification

Minimum focused tests:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_alignment_owner_family_successor_contract.py tests/test_alignment_owner_clustering.py tests/test_pre_backfill_consolidation.py tests/test_backfill_scope.py tests/test_alignment_owner_backfill.py tests/test_alignment_owner_matrix.py tests/test_alignment_claim_registry.py tests/test_alignment_primary_consolidation.py tests/test_alignment_matrix_identity.py tests/test_alignment_production_decisions.py tests/test_alignment_tsv_writer.py tests/test_alignment_xlsx_writer.py tests/test_alignment_debug_writer.py tests/test_alignment_output_levels.py tests/test_run_alignment.py tests/test_alignment_pipeline.py tests/test_alignment_pipeline_outputs.py
```

If alignment matrix or cell values change on representative fixtures, the phase
must include an expected-diff note and a `validation-evidence-reviewer`
acceptance review. For large RAW-backed validation, use
`docs/agent-parameter-settings.md` and `xic-raw-validation` before launch.

## Phase 3 - C4 Evidence Decision Productization

### Product Decision

`PeakHypothesisSelectionDecision` becomes the concrete product surface for
candidate selection, confidence projection, and public reason projection. It is
backed by `EvidenceVector.decision_semantics`, `CommonEvidence`, and selected
`PeakHypothesis` facts. The behavior addendum must define at least these fields:

- `selected_candidate_id`;
- `decision_class`;
- `confidence_projection`;
- `reason_projection`;
- `support_reasons`;
- `conflict_reasons`;
- `evidence_sources`;
- `legacy_projection_status`.

Raw score, caps, and weighted-score tie breaking must be demoted to
compatibility projection, diagnostic support, or deleted code only after the
phase proves the replacement decision and output contract.

The product owner expresses decisions as evidence support/challenge classes
rather than as a single weighted score. Public `confidence` and `reason` fields
may remain, but their semantics must project from
`PeakHypothesisSelectionDecision`.

### Allowed Public Behavior Diff

- Selected candidate may change when the selected-hypothesis decision has
  stronger multi-evidence support than the legacy score winner.
- Confidence labels and reason text may change when legacy caps are replaced by
  evidence decision classes.
- Local S/N must account for the ASLS baseline state; old local-S/N expectations
  based on retired linear-edge semantics are not an oracle.
- RT, shape, width, CWT, MS2 trace, product ion, neutral-loss, ISTD, and STD
  evidence should be represented as evidence facts. They must not act as
  undocumented hard vetoes.
- ISTD/STD role-aware RT rules apply only to the relevant source roles:
  biological ISTDs are expected to be stable transfer evidence because they are
  added to biological matrices, while non-ISTD external standards are not
  required biological-sample anchors unless explicitly spiked or validated.

### Verification

Minimum focused tests:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_peak_scoring.py tests/test_peak_scoring_selection.py tests/test_peak_scoring_evidence.py tests/test_scoring_context.py tests/test_peak_hypotheses.py tests/test_evidence_semantics.py tests/test_peak_candidate_table.py tests/test_peak_candidate_score_calibration_report.py tests/test_csv_writers.py tests/test_csv_to_excel.py tests/test_excel_pipeline.py tests/test_excel_sheets_contract.py tests/test_signal_processing_selection.py
```

The phase must also include public-output projection tests for candidate TSV,
CSV/XLSX, and any workbook fields that expose confidence, reason, support, or
concern text.

If candidate selection changes on real representative data, the phase must
capture the expected-diff rows in a validation note rather than treating
selection parity as the only acceptable result.

## Final Closeout

After all three phases:

- write one final closeout note under `docs/superpowers/notes/`;
- list each legacy owner as `retired`, `compatibility_adapter`,
  `diagnostic_only`, or `active_policy_remaining`;
- list exact public behavior changes and expected diffs;
- run the CI-equivalent PR gate;
- state validation label explicitly: `production_candidate`,
  `production_ready`, or `inconclusive` for each phase.

## Non-Goals

- No new baseline method.
- No reintroduction of `linear_edge`.
- No broad rewrite of the extractor, alignment pipeline, or workbook renderer
  unrelated to the three behavior-owner migrations.
- No deletion of public import facades unless the phase behavior spec includes
  a public migration or rejection contract.
- No 85RAW run by default. Use 8RAW, targeted representative validation, or
  existing artifacts unless a phase reviewer explains why 85RAW is the smallest
  evidence that can close the decision.
