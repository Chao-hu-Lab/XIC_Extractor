# Region-Boundary Decision Owner Design

**Date:** 2026-06-02
**Status:** Draft v0.1 - product/shadow overlap closeout design
**Readiness label:** `diagnostic_only`
**Repo-wide inventory:** [Repo semantic-overlap inventory](2026-06-02-repo-semantic-overlap-inventory-spec.md)
**Current-state input:** [Peak pipeline cleanup current-state reassessment](2026-06-01-peak-pipeline-cleanup-current-state-reassessment-spec.md)
**Related region specs:** [Boundary hypothesis enumeration v1](2026-05-16-boundary-hypothesis-enumeration-v1-spec.md), [Region-first model-selection shadow report v1](2026-05-18-region-first-model-selection-shadow-report-v1-spec.md), [Region-first safe merge promotion v1](2026-05-18-region-first-safe-merge-promotion-v1-spec.md)
**Related evidence specs:** [CWT evidence honesty](2026-05-24-peak-pipeline-cwt-evidence-honesty-spec.md), [C3 hypothesis model unification](2026-05-24-peak-pipeline-cleanup-hypothesis-model-unification-spec.md), [C4 peak scoring evidence-decision design](2026-06-01-c4-peak-scoring-evidence-decision-design.md)
**External research input:** [Region-boundary decision deep research note](../notes/2026-06-02-region-boundary-decision-deep-research-note.md)

## Verdict

Region and boundary logic should be treated as a product/shadow overlap, not as
dead code and not as two promoted product owners.

Today, production peak selection is still owned by the resolver path behind
`find_peak_and_area(...)`. `region_first_safe_merge` is the only promoted
region-decision behavior, and it is deliberately narrow: it may widen/merge a
selected local-minimum region only when the shadow region decision satisfies the
safe adjacent-WIS merge gate.

The shadow region model-selection path is still mostly audit/explanation:
boundary hypotheses, WIS, CWT proposal evidence, and
`RegionSelectionDecision` can explain why the current product interval may be
too narrow, split, or pointed at a weaker neighboring apex. Those signals do not
become product authority unless a promotion spec says so.

The next implementation goal should therefore not delete region logic. It should
make one region-boundary decision contract that:

- names the production owner and shadow owner explicitly;
- keeps `region_first_safe_merge` as a compatibility resolver token while its
  internals are clarified;
- moves valid region facts toward `PeakHypothesis`, `EvidenceVector`,
  `IntegrationResult`, and `AuditTrail`;
- prevents CWT, WIS, local minima, RT, shape, or scoring from silently becoming
  a single-source authority;
- defines when shadow evidence may promote, stay audit-only, externalize, or
  retire.

This design authorizes no selected-peak, area, score, confidence, reason,
schema, GUI, config, workbook, TSV, or alignment matrix behavior change.

## Why This Spec Exists

The repo already has several good region pieces, but their ownership is not
clear enough for long-term maintenance:

- candidate selection chooses a production candidate;
- boundary hypotheses enumerate alternate intervals;
- region model selection emits audit/shadow verdicts;
- safe merge promotes one narrow subset of those verdicts;
- CWT can propose or corroborate apex/boundary evidence;
- C3/C4 handoff spine models can carry selected and rejected evidence, but do
  not yet own region decision policy.

Without a single ownership contract, future cleanup could make either mistake:

1. preserve duplicated product and shadow semantics forever; or
2. delete useful evidence just because it is not yet the final product owner.

This spec chooses the middle path: fuse valid evidence into the future spine,
keep current production behavior stable, and give every region surface an exit
rule.

## Current Ownership Map

| Surface | Current role | Authority today | Future disposition |
|---|---|---|---|
| `peak_detection/facade.py::find_peak_and_area` | Public production extraction facade. | Product owner for selected peak result. | Keep as public facade. Future internals may delegate to a region-decision owner. |
| `xic_extractor.signal_processing.find_peak_and_area` | Public compatibility re-export. | Public import contract, not separate behavior owner. | Preserve as thin compatibility facade unless a public migration spec says otherwise. |
| `xic_extractor.extractor.find_peak_and_area` | Extraction-module compatibility alias through `signal_processing`. | Public/import compatibility for existing callers. | Preserve import and return-shape compatibility during RB0/RB1. |
| `peak_detection/selection.py::select_candidate` | Selects strongest or RT-nearest candidate before scoring/merge logic. | Active production helper. | Characterize before movement; migrate only when a successor selected-hypothesis policy exists. |
| `peak_detection/region_safe_merge.py::apply_region_first_safe_merge` | Applies the narrow adjacent-WIS safe-merge promotion. | Product behavior only when `resolver_mode=region_first_safe_merge`. | Keep now; later decide whether it becomes an internal constructor, adapter behind the public token, or retirement candidate. |
| `peak_detection/region_model_selection.py::decide_region_selection` | Converts boundary evidence into region shadow verdicts. | Audit/shadow decision primitive; product input only through safe-merge eligibility. | Become the shared region-decision contract or delegate into one. |
| `peak_detection/boundaries.py` and boundary scoring | Enumerates and scores alternate intervals. | Audit/proposal evidence. | Keep as proposal source; route facts into `IntegrationResult` / `AuditTrail` when the successor spine is ready. |
| `extraction/peak_region_selection_shadow.py` and output writer | Renders shadow verdicts from boundary rows. | Diagnostic/review output only. | Preserve as review surface until promotion/retirement evidence exists. |
| `peak_detection/cwt.py` | Adds CWT apex proposals and same-apex provenance. | Evidence/proposal source, not final authority. | Test named roles, starting with apex proposal source; do not call it "support only" in a way that demotes valid evidence. |
| `PeakHypothesis`, `EvidenceVector`, `IntegrationResult`, `AuditTrail` | Handoff spine for candidate, evidence, integration, and audit state. | Partial audit/runtime projection today. | Successor carrier for region facts, but not yet a production selector. |

## Stale-Spec Correction

The 2026-05-16 boundary hypothesis spec was written before the AsLS baseline
retirement work settled. It mentions a deterministic `linear_edge` audit model
for boundary baseline-corrected area.

Current region-boundary work must not revive `linear_edge`. Future boundary and
region audit fields must use the current AsLS-only baseline integration/audit
contract, or explicitly mark historical linear-edge readers as historical
diagnostic evidence. Any product or audit selector that accepts
`linear_edge` again requires a new behavior spec.

## Product / Shadow Boundary

### Product owner today

Production selected peak behavior is:

```text
raw trace
  -> resolver candidate formation
  -> selected candidate / scorer / recovery path
  -> optional region_first_safe_merge product gate
  -> selected PeakDetectionResult / IntegrationResult projection
```

The product owner is allowed to decide:

- selected candidate;
- selected apex;
- selected integration bounds;
- selected area;
- selected score/confidence/reason projection;
- selected result emitted to CSV/XLSX/TSV alignment inputs.

Any change to those values is a behavior change.

Resolver surfaces are workflow-specific. `region_first_safe_merge` is an
accepted public resolver token, but alignment/discovery wrappers may normalize
or route that token differently under their own current contracts. A
region-boundary implementation plan must inventory each public entry point
before claiming the mode is promoted, defaulted, or retired everywhere:

- settings schema / GUI resolver choices;
- `ExtractionConfig.resolver_mode` programmatic behavior;
- `find_peak_and_area(...)` and targeted extraction;
- public compatibility imports from `xic_extractor.signal_processing` and
  `xic_extractor.extractor`;
- `scripts/run_discovery.py`;
- `scripts/run_alignment.py` and alignment quantification;
- validation harness defaults.

Cleanup wording must not use one workflow's resolver behavior as proof for all
workflow surfaces.

### Shadow owner today

Shadow region model selection is:

```text
peak candidates
  -> boundary hypotheses
  -> boundary scoring and WIS audit selection
  -> RegionSelectionDecision
  -> peak_region_selection_shadow.tsv / summary / blast-radius
```

The shadow owner is allowed to decide:

- whether the current interval is contradicted by alternate evidence;
- whether a wider boundary, split, neighbor apex, or merge deserves review;
- whether evidence is insufficient or malformed;
- which rows should be prioritized for manual review or future promotion.

The shadow owner must not change selected peak, selected area, confidence,
reason text, resolver defaults, workbook values, or alignment matrix output.

### Shared decision primitive

`RegionSelectionDecision` is currently the closest shared domain primitive. It
is used by both shadow reporting and the safe-merge gate. That is acceptable
only because `region_safe_merge` applies a narrower product eligibility filter.

Future work must keep this separation explicit:

```text
RegionSelectionDecision
  -> shadow verdicts: all verdicts visible for review
  -> product promotion: only explicitly gated verdict/source combinations
```

## Evidence Role Rules

No single evidence family should silently select or reject a peak region.

| Evidence family | Allowed role | Disallowed role without new behavior spec |
|---|---|---|
| Local minimum | Candidate/valley proposal and shallow-split evidence. | Final integrator or final split authority. |
| WIS | Audit/model-selection explanation for non-overlapping interval sets. | Hidden production selector except through the existing safe-merge gate. |
| Boundary hypotheses | Alternate interval evidence and area sensitivity. | Direct product boundary replacement. |
| CWT | Apex proposal, same-apex corroboration, possible future width/ridge/shoulder evidence after a named role gate. | Standalone peak-existence, identity, or integration authority. |
| RT prior | Contextual targeted evidence, especially role-aware ISTD/STD cases. | Sole identity or absence veto. |
| Shape/width/SN | Trace morphology evidence. | Unilateral rejection without conflict/quality policy. |
| Scorer support/cap labels | Compatibility projection and active C4 policy today. | Future first-class region policy target. |

CWT wording must be precise: CWT is not "only support" in the sense of being
low-value evidence. It is an evidence source whose authority depends on role,
opportunity, comparator, and corroborating evidence.

## Future Region-Decision Contract

The future owner should expose one contract for region decisions, even if the
implementation stays split internally.

Minimum fields:

| Field | Purpose |
|---|---|
| `decision_status` | evaluated, insufficient evidence, invalid trace, missing candidate, or low scan support. |
| `decision_class` | current supported, merge suggested, split supported, wider boundary preferred, neighbor apex preferred, or future class. |
| `product_action` | no change, safe merge eligible, review only, not counted candidate, or behavior-change required. |
| `selected_candidate_id` | Current product candidate. |
| `selected_boundary_id` | Current product boundary. |
| `alternate_boundary_ids` | Candidate alternate boundaries used by the decision. |
| `evidence_sources` | local minimum, WIS, CWT, half-height, baseline return, derivative, scorer, MS2/NL, RT, shape/SN as applicable. |
| `support_reasons` | Machine-readable support labels. |
| `conflict_reasons` | Machine-readable concern/conflict labels. |
| `audit_reason` | Human-readable explanation for review surfaces. |
| `promotion_reason` | Required when product behavior changes. Empty otherwise. |
| `baseline_method` | Must be `asls` under the current production/audit contract. |

The contract can be implemented later as a new model, or by hardening
`RegionSelectionDecision`. This spec does not require a new module name, but the
eventual implementation should keep domain logic in `xic_extractor/peak_detection`
and keep TSV/HTML/XLSX rendering in extraction/output/diagnostic layers.

## Migration Slices

### RB0 - Current-state characterization

Pin the current behavior before movement:

- product selected candidate and area with `legacy_savgol`, `local_minimum`, and
  `region_first_safe_merge`;
- public resolver token behavior separately for settings schema, GUI,
  `ExtractionConfig`, targeted extraction, discovery, alignment, and validation
  harness entry points;
- safe-merge eligibility and rejection reasons;
- shadow verdict rows and summary rows;
- boundary-hypothesis rows and AsLS baseline fields;
- CWT audit proposal rows and CWT-only guardrails.

This slice is cleanup/characterization only. Behavior changes are out of scope.

### RB1 - Region decision contract projection

Add or harden a single region-decision projection without changing behavior.
Both product safe-merge and shadow output should consume the same typed decision
facts, but product promotion must still pass the narrower safe-merge gate.

Allowed RB1 changes:

- add or harden internal typed fields;
- refactor domain logic behind existing functions;
- add internal tests proving existing public outputs are unchanged.

Disallowed RB1 changes:

- no new columns in existing public TSVs or workbooks;
- no header order changes;
- no row inclusion or row order changes;
- no selected RT, area, confidence, reason, candidate id, boundary id,
  `merge_note`, or `selected_integration` mapping changes;
- no new diagnostic sidecar artifacts;
- no resolver accepted-value, default, GUI, CLI, or validation-harness changes.

Any new sidecar, new column, or schema-compatible extension must move to a
later diagnostic-lifecycle or public-output spec. RB1 is strict parity, not
schema extension.

### RB2 - Handoff spine mapping

Map region facts to the handoff spine:

- selected/current boundary to `IntegrationResult`;
- alternate/rejected boundary facts to `AuditTrail`;
- CWT/local-minimum/WIS/source provenance to `EvidenceVector` or a future trace
  morphology evidence component;
- product action and review reason to the selected `PeakHypothesis`.

This is a projection/mapping slice unless an approved behavior spec changes
selection.

### RB3 - Public resolver token decision

Decide the future of `region_first_safe_merge`:

| Option | Meaning | When to choose |
|---|---|---|
| Keep public token | It remains a visible resolver mode. | User-facing config compatibility matters and the behavior remains distinct. |
| Internal constructor behind local-minimum policy | The public token stays temporarily, but implementation is one region-decision pipeline. | Successor contract owns the logic and compatibility needs a transition period. |
| Rename/alias | Public name changes to a clearer local-minimum-with-safe-merge name. | Only if config/GUI/docs migration is worth the churn. |
| Retire | Mode is rejected like `arbitrated`. | Only after successor default or another mode covers the invariant and compatibility migration is approved. |

No option is selected by this spec. It defines the decision that a later C2/RB
slice must close.

### RB4 - CWT named-role gate

CWT remains audit/proposal evidence until a named role gate proves value.

First role to test remains:

```text
apex proposal source
```

Do not combine CWT apex proposal, width prior, ridge/persistence, and shoulder
evidence into one promotion gate. Each role needs its own comparator and manual
review or artifact oracle.

## Test And Validation Strategy

### Unit / characterization tests

Minimum narrow tests before movement:

- `tests/test_region_model_selection.py`
- `tests/test_region_safe_merge.py`
- `tests/test_peak_region_selection_shadow.py`
- `tests/test_boundary_hypotheses.py`
- `tests/test_boundary_scoring.py`
- `tests/test_peak_candidate_boundaries.py`
- `tests/test_cwt_proposals.py`
- `tests/test_cwt_peak_candidate_audit.py`
- relevant C4/C3 projection tests when facts move into `EvidenceVector`,
  `IntegrationResult`, or `AuditTrail`

### Public contract tests

Any slice touching output must prove:

- `xic_extractor.signal_processing.find_peak_and_area` and
  `xic_extractor.extractor.find_peak_and_area` imports still work and preserve
  return shape;
- `peak_candidates.tsv` header tuple, header order, row count, row order, and
  cell values are unchanged;
- `peak_candidate_boundaries.tsv` header tuple, header order, row count, row
  order, and cell values are unchanged;
- `peak_region_selection_shadow.tsv`,
  `peak_region_selection_shadow_summary.tsv`, and
  `peak_region_selection_shadow_blast_radius.tsv` header tuple, header order,
  row count, row order, and cell values are unchanged;
- extraction workbook sheet names, sheet order, hidden states, column headers,
  selected RT, selected area, confidence, reason, and row inclusion are
  unchanged;
- `alignment_matrix.tsv`, `alignment_review.tsv`, and `alignment_cells.tsv`
  header tuple, header order, row count, row order, and cell values are
  unchanged when a region-boundary change touches alignment paths;
- alignment workbook `Matrix`, `Review`, `Audit`, and `Metadata` sheets keep
  sheet names, sheet order, headers, row inclusion, and matrix values unchanged
  when a region-boundary change touches alignment paths;
- config, GUI, CLI, and validation harness accepted resolver modes and defaults
  are unchanged unless a resolver migration spec says otherwise.

Minimum RB0/RB1 test command group:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_signal_processing.py tests/test_signal_processing_selection.py tests/test_region_model_selection.py tests/test_region_safe_merge.py tests/test_peak_region_selection_shadow.py tests/test_boundary_hypotheses.py tests/test_boundary_scoring.py tests/test_peak_candidate_boundaries.py tests/test_cwt_proposals.py tests/test_cwt_peak_candidate_audit.py tests/test_csv_writers.py tests/test_excel_pipeline.py tests/test_alignment_tsv_writer.py tests/test_alignment_xlsx_writer.py tests/test_alignment_owner_matrix.py tests/test_run_alignment.py tests/test_validation_harness.py
```

An implementation plan may split this command into smaller shards, but it must
name any omitted file and the reason it cannot be affected.

Product safe-merge code must not depend on extraction TSV row builders,
shadow-output writers, or diagnostic CLIs. Those layers may render region
decisions, but they must not become product inputs.

### RAW validation

Do not launch 8RAW/85RAW merely because this spec exists. RAW validation is
justified only after an implementation slice can change a product decision or a
registered diagnostic gate can close a concrete decision.

For cleanup-only slices, narrow unit and TSV parity tests are the primary gate.
For behavior-changing region promotion, use:

- focused synthetic tests first;
- targeted benchmark or 8RAW comparison for selected rows;
- row-level changed-decision TSV;
- manual EIC review for high-risk changed rows;
- validation-evidence review before any default or production promotion.

## Stop Rules

Stop and return to design if any implementation attempt:

- changes selected peak, RT, area, confidence, reason, or workbook output during
  a cleanup-only slice;
- treats `peak_region_selection_shadow.tsv` as production input;
- reintroduces `linear_edge`;
- lets CWT-only evidence promote a region;
- merges CWT, WIS, local-minimum, and scorer policy into one opaque score;
- changes resolver defaults or public config values without a resolver migration
  spec;
- requires RAW validation before a changed-row schema and manual-review plan
  exist.

## Recommended Next Goal Shape

The next executable goal should be RB0 + RB1 only:

```text
Pin current region-boundary behavior and introduce/harden one typed
region-decision projection consumed by both safe-merge and shadow outputs,
without changing selected peaks, areas, schemas, resolver defaults, or workbook
values.
```

Do not include RB2/RB3/RB4 in the same first implementation goal unless RB0/RB1
finish cleanly and a review confirms the write scope remains small.

## RB0/RB1 Execution Closeout

**Status:** Implemented as cleanup/semantic-convergence groundwork.
**Behavior label:** no public behavior change.

RB0 current-state characterization is covered by existing and strengthened test
families:

- resolver candidate behavior:
  `tests/test_signal_processing.py`,
  `tests/test_signal_processing_selection.py`,
  `tests/test_region_safe_merge.py`;
- safe-merge eligibility, rejection, and promotion guardrails:
  `tests/test_region_safe_merge.py`;
- region shadow verdict classes and CWT-only guardrails:
  `tests/test_region_model_selection.py`,
  `tests/test_peak_region_selection_shadow.py`;
- boundary hypothesis, boundary scoring, AsLS baseline audit fields, and CWT
  boundary audit rows:
  `tests/test_boundary_hypotheses.py`,
  `tests/test_boundary_scoring.py`,
  `tests/test_peak_candidate_boundaries.py`,
  `tests/test_cwt_proposals.py`,
  `tests/test_cwt_peak_candidate_audit.py`;
- workflow-specific resolver surfaces:
  `tests/test_config.py`,
  `tests/test_settings_section.py`,
  `tests/test_settings_section_advanced.py`,
  `tests/test_settings_new_fields.py`,
  `tests/test_gui_main.py`,
  `tests/test_run_discovery.py`,
  `tests/test_discovery_pipeline.py`,
  `tests/test_run_alignment.py`,
  `tests/test_validation_harness.py`.

RB1 hardens `RegionSelectionDecision` as the internal typed region-decision
projection. The existing public fields remain intact for current shadow writer
and safe-merge consumers. New internal fields make the shared contract explicit:

- `decision_status` and `decision_class` mirror the evaluated shadow status and
  verdict;
- `product_action` is `no_change`, `review_only`,
  `safe_merge_eligible`, or `behavior_change_required`;
- `selected_candidate_id`, `selected_boundary_id`, and
  `alternate_boundary_ids` identify current and alternate intervals;
- `evidence_sources`, `support_reasons`, and `conflict_reasons` preserve the
  proposal/boundary evidence considered by the decision;
- `audit_reason`, `promotion_reason`, and `baseline_method` keep review,
  promotion, and AsLS baseline context internal to the decision object.

`region_safe_merge.eligibility_for_region_first_safe_merge(...)` now also checks
the internal `product_action == "safe_merge_eligible"` fact, while retaining the
existing narrower gates for evaluated status, merge verdict,
`adjacent_wis_local_minimum_merge`, selected interval count, WIS gap, area ratio,
and apex proximity. This makes product promotion consume the same typed decision
facts as shadow reporting without widening product authority.

No new TSV columns, workbook sheets, sidecars, resolver modes, defaults, GUI
choices, config keys, run metadata, selected peaks, selected areas, score,
confidence, reason text, or alignment outputs are authorized by this closeout.
RB2/RB3/RB4 remain follow-up work.

## Acceptance Criteria For This Spec

- Product owner, shadow owner, and shared decision primitive are named.
- `region_first_safe_merge` is treated as active opt-in behavior, not dead code.
- CWT is treated as evidence with named roles, not as standalone authority and
  not as low-value "support only" wording.
- Linear-edge boundary-audit wording is explicitly marked stale.
- Future implementation is constrained to cleanup/characterization first.
- Every path that could change selected peak, area, score, reason, schema,
  resolver defaults, or matrix output requires a separate behavior/promotion
  spec.
