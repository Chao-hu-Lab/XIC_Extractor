# Region-Boundary RB0/RB1 Semantic Convergence Goal

**Status:** Complete for RB0/RB1 semantic-convergence foundation.
**Closeout:** [C4 / C6 / Region foundation closeout](../notes/2026-06-02-c4-c6-region-foundation-closeout.md)

```text
/goal
GOAL:
Complete the first region-boundary semantic convergence PR: characterize current
region/boundary behavior and introduce or harden one internal typed
region-decision projection shared by safe-merge and shadow outputs, without
changing selected peaks, selected areas, confidence/reason values, public
schemas, resolver defaults, GUI/config behavior, workbook values, or alignment
matrix outputs.

This is a semantic convergence goal, not a legacy deletion goal. It should make
the current product owner, shadow owner, and shared decision facts explicit so
later behavior-changing region work can be judged row by row.

CONTEXT:
- Repository/worktree:
  `C:\Users\user\Desktop\XIC_Extractor`, current branch.
- Required repo instructions:
  `AGENTS.md`,
  `docs/agent-subagent-routing.md`,
  `docs/agent-parameter-settings.md`.
- Primary specs and notes:
  `docs/superpowers/specs/2026-06-02-region-boundary-decision-owner-design.md`,
  `docs/superpowers/specs/2026-06-02-mature-package-flow-reference-spec.md`,
  `docs/superpowers/notes/2026-06-02-region-boundary-decision-deep-research-note.md`,
  `docs/superpowers/specs/2026-06-02-repo-semantic-overlap-inventory-spec.md`,
  `docs/superpowers/specs/2026-06-01-peak-pipeline-cleanup-current-state-reassessment-spec.md`.
- Related historical inputs:
  `docs/superpowers/specs/2026-05-16-boundary-hypothesis-enumeration-v1-spec.md`,
  `docs/superpowers/specs/2026-05-18-region-first-model-selection-shadow-report-v1-spec.md`,
  `docs/superpowers/specs/2026-05-18-region-first-safe-merge-promotion-v1-spec.md`,
  `docs/superpowers/specs/2026-05-24-peak-pipeline-cwt-evidence-honesty-spec.md`,
  `docs/superpowers/specs/2026-05-24-peak-pipeline-cleanup-hypothesis-model-unification-spec.md`,
  `docs/superpowers/specs/2026-06-01-c4-peak-scoring-evidence-decision-design.md`.
- Code surfaces to inspect first:
  `xic_extractor/peak_detection/facade.py`,
  `xic_extractor/peak_detection/selection.py`,
  `xic_extractor/peak_detection/region_safe_merge.py`,
  `xic_extractor/peak_detection/region_model_selection.py`,
  `xic_extractor/peak_detection/boundaries.py`,
  `xic_extractor/peak_detection/boundary_scoring.py`,
  `xic_extractor/peak_detection/cwt.py`,
  `xic_extractor/extraction/peak_region_selection_shadow.py`,
  `xic_extractor/extraction/peak_candidate_boundaries.py`,
  `xic_extractor/signal_processing.py`,
  `xic_extractor/extractor.py`,
  `scripts/run_discovery.py`,
  `scripts/run_alignment.py`.
- Current baseline:
  Product selected peak behavior is owned by the resolver path behind
  `find_peak_and_area(...)`. `region_first_safe_merge` is active opt-in
  behavior under a narrow safe adjacent-WIS merge gate. Boundary hypotheses,
  WIS, CWT proposal evidence, and `RegionSelectionDecision` are mostly
  audit/shadow explanation today.
- Product-flow correction:
  mature LC-MS workflows treat boundary/integration/gap-filling decisions as
  product stages once their gates are accepted. RB0/RB1 are therefore foundation
  phases only; closeout must name the RB2/RB3 product gate or externalization
  decision they unlock.

CONSTRAINTS:
- Keep scope to RB0/RB1 only.
- Do not implement RB2 handoff-spine mapping, RB3 resolver-token migration, or
  RB4 CWT named-role promotion in this goal.
- Preserve public contracts:
  CLI flags, config keys, accepted resolver modes, defaults, GUI-visible
  choices, public imports, TSV schemas, workbook sheets, alignment TSVs,
  alignment workbooks, run metadata keys, and validation harness defaults.
- Do not add public columns, sidecars, output files, workbook sheets, or
  schema-compatible public extensions in RB1.
- Do not change selected candidate, selected apex, selected integration bounds,
  selected area, confidence, reason text, raw score, score labels, cap labels,
  `merge_note`, `selected_integration`, row inclusion, row order, or matrix
  values.
- Do not reintroduce `linear_edge`; boundary and integration audit facts must
  use the current AsLS-only baseline contract.
- Do not let CWT, WIS, local minima, RT, shape, S/N, scorer labels, or any
  single evidence family silently become product authority.
- Product safe-merge code must not depend on extraction TSV row builders,
  shadow-output writers, diagnostic CLIs, or report rendering.
- This is docs/test/refactor cleanup. RAW validation is not required unless the
  implementation can change a product decision.
- Verification integrity:
  do not weaken or bypass tests, assertions, schema checks, lint, typecheck, or
  reviewer blockers to make the goal pass. Fix the root cause or record the
  blocker.

SUBAGENT / XHIGH REVIEW PROTOCOL:
- Before execution, review this goal with repo-routed read-only subagents:
  `strategy-challenger` and `implementation-contract-reviewer`, both with
  xhigh reasoning if the runtime supports it.
- After RB0 and before committing RB0, ask `implementation-contract-reviewer`
  to confirm the characterization surfaces and public-output parity oracle are
  sufficient.
- After RB1 and before committing RB1, ask `implementation-contract-reviewer`
  to confirm typed projection did not become a public schema or product
  behavior change. Ask `strategy-challenger` to re-check only if the fix changes
  scope, owner, or migration sequence.
- Use the repo fix/re-check loop:
  fix blocker -> ask the original blocker reviewer to re-check -> add a third
  reviewer only if the fix moved into validation, docs-handoff, or ops scope.

PHASES:

Phase 0 - Goal Contract And Review
Purpose:
- Land this goal after read-only xhigh review.
Done when:
- `strategy-challenger` and `implementation-contract-reviewer` report no
  blocking findings, or every blocker is fixed in this document.
- Dirty scope is recorded and unrelated dirty files are not staged.

Phase 1 - RB0 Current-State Characterization
Purpose:
- Pin current product, shadow, resolver, and public output behavior before
  movement.
Allowed work:
- Add or update characterization tests for:
  `legacy_savgol`, `local_minimum`, and `region_first_safe_merge`;
  safe-merge eligibility and rejection reasons;
  `RegionSelectionDecision` classes;
  boundary-hypothesis rows;
  AsLS baseline fields;
  CWT proposal rows and CWT-only guardrails;
  workflow-specific resolver token behavior in settings, targeted extraction,
  discovery, alignment, and validation harness surfaces.
- Add an internal current-state note only if needed to explain fixture/oracle
  coverage.
Forbidden work:
- No production behavior, output schema, resolver default, GUI/config, or
  workbook/matrix value changes.
Done when:
- Current behavior is protected by focused tests or explicitly mapped to an
  existing named test.
- Resolver-token behavior is inventoried per workflow instead of generalized
  from one entry point.
- The RB0 closeout records which tests protect each public parity surface.

Phase 2 - RB1 Internal Region-Decision Projection
Purpose:
- Add or harden one internal typed region-decision projection consumed by both
  product safe-merge and shadow output paths while preserving current product
  action gates.
Allowed work:
- Introduce or harden internal typed fields equivalent to:
  `decision_status`, `decision_class`, `product_action`,
  `selected_candidate_id`, `selected_boundary_id`,
  `alternate_boundary_ids`, `evidence_sources`, `support_reasons`,
  `conflict_reasons`, `audit_reason`, `promotion_reason`, and
  `baseline_method`.
- Refactor domain logic behind existing functions only when tests prove public
  outputs are unchanged.
- Keep `RegionSelectionDecision` as the implementation if it can carry the
  contract cleanly; a new model is optional, not required.
Forbidden work:
- No new public TSV/workbook fields or sidecar artifacts.
- No behavior change to safe-merge promotion eligibility.
- No direct dependency from product code to shadow writers or diagnostics.
Done when:
- Safe-merge and shadow paths consume the same typed decision facts or a
  documented adapter over the same internal projection.
- Product promotion still passes the narrower safe-merge gate.
- Unit and public contract tests prove selected outputs are unchanged.

Phase 3 - Closeout And Verification
Purpose:
- Prove the goal converged semantics without making product behavior changes.
Done when:
- Region-boundary spec records the executed RB0/RB1 closeout and any remaining
  RB2/RB3/RB4 follow-up.
- The closeout states the mature-flow verdict: RB0/RB1 did not finish region
  productization; they either unlock a named product-gate spec, externalize the
  shadow path, or name the missing oracle.
- No unrelated files are staged for this goal.
- Focused tests and docs smoke checks have fresh results.

DONE WHEN:
- Current product owner, shadow owner, and shared region-decision projection are
  explicit in code/tests/docs.
- `region_first_safe_merge` remains active opt-in behavior, not dead code and
  not a generalized product selector.
- Local minimum, legacy Savgol, safe merge, CWT, WIS, shape/S/N, RT, and scorer
  evidence are represented as proposal/evidence facts, not standalone final
  authority.
- Public selected peak, area, score/confidence/reason, schemas, resolver
  defaults, GUI/config behavior, workbook values, and alignment outputs are
  unchanged.
- Public parity is exact for every touched surface: header tuple, header order,
  row count, row order, cell values, workbook sheet names/order/hidden states,
  selected RT/area/confidence/reason values, matrix values, accepted resolver
  modes, defaults, and public import return shape must remain unchanged.
- RB2/RB3/RB4 are listed as follow-up only, with no hidden behavior promotion in
  this goal.
- RB2/RB3/RB4 follow-up has an exit rule for every shadow verdict class:
  promote, keep review-only, externalize, retire, or inconclusive with one
  missing oracle.

VERIFY:
Run focused tests, split into smaller shards if needed:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run pytest tests/test_signal_processing.py tests/test_signal_processing_selection.py tests/test_region_model_selection.py tests/test_region_safe_merge.py tests/test_peak_region_selection_shadow.py tests/test_boundary_hypotheses.py tests/test_boundary_scoring.py tests/test_peak_candidate_boundaries.py tests/test_peak_candidate_table.py tests/test_cwt_proposals.py tests/test_cwt_peak_candidate_audit.py tests/test_config.py tests/test_settings_section.py tests/test_settings_section_advanced.py tests/test_settings_new_fields.py tests/test_gui_main.py tests/test_run_discovery.py tests/test_discovery_pipeline.py tests/test_csv_writers.py tests/test_csv_to_excel.py tests/test_excel_pipeline.py tests/test_excel_sheets_contract.py tests/test_alignment_tsv_writer.py tests/test_alignment_xlsx_writer.py tests/test_alignment_owner_matrix.py tests/test_run_alignment.py tests/test_validation_harness.py
uv run ruff check xic_extractor tests
uv run mypy xic_extractor
git diff --check
git status --short --branch
```

Inspect:
- no public TSV/workbook/schema/default resolver diff unless a reviewed blocker
  explains why the goal must stop;
- product code does not import shadow writers or diagnostic CLIs;
- touched docs do not overclaim `production_ready` or CWT/default promotion.
- if any public surface named in the constraints is omitted from the focused
  shard, the implementation closeout must name it and explain why the diff
  cannot affect it; otherwise the relevant test or exact artifact parity check
  is required.

OUTPUT:
- Phase-by-phase status.
- Changed files by phase.
- Reviewer findings and fixes.
- Verification commands and results.
- Whether public outputs/config/imports changed. Expected answer: no.
- Remaining RB2/RB3/RB4 follow-up.

STOP RULES:
- Stop if a cleanup-only change alters selected peak, RT, area, confidence,
  reason, workbook output, alignment matrix, or resolver defaults.
- Stop if product code starts consuming `peak_region_selection_shadow.tsv`.
- Stop if a proposal/evidence source becomes single-source product authority.
- Stop if a new public field or sidecar is needed; write a public-output or
  diagnostic-lifecycle spec instead.
- Stop if RAW validation becomes necessary before a changed-row schema and
  manual-review plan exist.
- Stop after three failed fixes for the same symptom and revisit the root-cause
  hypothesis.
- Do not mark complete until the current state is checked against `DONE WHEN`.
```
