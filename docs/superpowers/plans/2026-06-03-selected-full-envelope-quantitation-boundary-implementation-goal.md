# Selected Full-Envelope Quantitation Boundary Implementation Goal

**Date:** 2026-06-03
**Status:** Reviewed; FE0-FE4 foundation exists; executing FE1 OpenMS-first
policy slice
**Readiness target:** `production_candidate` only after the scale gate and
conditional product-wiring slice pass with manual/expert overlay and changed-row
evidence. FE0-FE4 are `diagnostic_only` or `shadow_ready`, not product
promotion.
**Primary spec:** [Selected full-envelope quantitation boundary spec](../specs/2026-06-03-selected-full-envelope-quantitation-boundary-spec.md)
**Related specs:** [AsLS primary matrix value policy](../specs/2026-06-02-asls-primary-matrix-value-policy-spec.md), [Region-boundary decision owner design](../specs/2026-06-02-region-boundary-decision-owner-design.md), [Region-boundary public behavior addendum](../specs/2026-06-02-region-boundary-public-behavior-addendum.md)

Reviewer gate:

- `strategy-challenger` xhigh review: initial blockers closed; re-check pass.
- `implementation-contract-reviewer` xhigh review: initial blockers closed;
  re-check pass.
- `validation-evidence-reviewer` xhigh review: initial blockers closed;
  re-check pass.

```text
/goal
GOAL:
Implement the selected full-envelope quantitation boundary path so final
quantitative area can move from narrow resolver intervals to bounded
selected-peak envelopes, while keeping AsLS as the existing area/baseline owner
and proving the behavior with diagnostic, fixture, manual/overlay, and changed-row
evidence before any product promotion.

CONTEXT:
- Repository/worktree:
  `C:\Users\user\Desktop\XIC_Extractor`, current branch.
- Required repo instructions:
  `AGENTS.md`,
  `docs/agent-subagent-routing.md`,
  `docs/agent-parameter-settings.md` before Python, RAW, DLL, long validation,
  or output-level commands.
- Primary spec:
  `docs/superpowers/specs/2026-06-03-selected-full-envelope-quantitation-boundary-spec.md`.
- Related baseline/value source policy:
  `docs/superpowers/specs/2026-06-02-asls-primary-matrix-value-policy-spec.md`.
- Related region/boundary policy:
  `docs/superpowers/specs/2026-06-02-region-boundary-decision-owner-design.md`,
  `docs/superpowers/specs/2026-06-02-region-boundary-public-behavior-addendum.md`.
- Validation references:
  `docs/validation-harness.md`,
  `docs/diagnostic-ledger.md`,
  `tools/diagnostics/INDEX.md`.
- Current product gap:
  AsLS is now the primary value source, but selected integrations may still use
  resolver-provided `peak_start` / `peak_end`, which can clip real peak flanks.
- Core product direction:
  integrate the selected peak's full baseline-supported envelope over raw/original
  XIC via the existing AsLS `IntegrationResult.area_baseline_corrected`; do not
  sum every positive AsLS residual inside the broader RT context.
- Code surfaces to inspect first:
  `xic_extractor/peak_detection/facade.py`,
  `xic_extractor/peak_detection/hypotheses.py`,
  `xic_extractor/peak_detection/baseline.py`,
  `xic_extractor/peak_detection/local_minimum.py`,
  `xic_extractor/peak_detection/region_model_selection.py`,
  `xic_extractor/peak_detection/region_safe_merge.py`,
  `xic_extractor/alignment/ownership.py`,
  `xic_extractor/alignment/matrix_handoff.py`,
  `xic_extractor/alignment/primary_matrix_area.py`,
  `xic_extractor/extractor.py`,
  `xic_extractor/extraction/result_assembly.py`,
  `xic_extractor/extraction/peak_candidate_boundaries.py`,
  `xic_extractor/extraction/peak_candidate_table.py`,
  `xic_extractor/output/schema.py`,
  `xic_extractor/output/csv_writers.py`,
  `xic_extractor/output/excel_pipeline.py`,
  `xic_extractor/output/workbook_builder.py`,
  `tools/diagnostics/INDEX.md`.
- Test surfaces to inspect first:
  `tests/test_baseline_integration.py`,
  `tests/test_peak_hypotheses.py`,
  `tests/test_peak_region_selection_shadow.py`,
  `tests/test_signal_processing_selection.py`,
  `tests/test_alignment_ownership.py`,
  `tests/test_peak_candidate_table.py`,
  `tests/test_peak_candidate_boundaries.py`,
  `tests/test_output_schema_contract.py`,
  `tests/test_csv_writers.py`,
  `tests/test_excel_pipeline.py`,
  `tests/test_excel_sheets_contract.py`,
  `tests/test_alignment_tsv_writer.py`,
  `tests/test_alignment_xlsx_writer.py`,
  `tests/test_result_assembly.py`,
  `tests/test_handoff_spine_runtime.py`,
  plus any existing diagnostic or validation-harness tests that already compare
  resolver area, AsLS area, manual truth, or boundary rows.

CONSTRAINTS:
- Do not re-enable `linear_edge` as product area, fallback, comparator truth, or
  rollback path.
- Do not implement context-wide positive-residual integration. Every envelope is
  anchored to one selected candidate or `PeakHypothesis`.
- Do not make Savitzky-Golay, CWT, local minimum, WIS, RT, shape, S/N, score, or
  region-first fields a single-source product authority.
- Do not use smoothed trace area as the final matrix value. Smoothed traces may
  support boundary evidence only.
- Treat the selected-envelope boundary policy as OpenMS-first: selected
  candidate / `PeakHypothesis`, named morphology trace, explicit boundary,
  raw/original XIC integration, and AsLS baseline subtraction.
- The first morphology trace candidate should be `smooth_15`-style because it
  matches the analyst's Xcalibur review practice. Any implementation must name
  the smoothing method, window, and effective point count in diagnostics.
- Do not let a one-scan residual dip, local minimum, or single-point baseline
  return terminate the selected envelope. Short intra-peak dips must be bridged
  unless independent split/neighbor evidence externalizes the row.
- Do not let positive residual clipping decide boundary expansion. It is a
  low-level AsLS integration detail only.
- Do not resurrect `region_first_safe_merge` / `safe_merge` as a first-class
  product boundary mode. It may appear only as `legacy_resolver_provenance` or
  equivalent audit provenance for selected-envelope work. Existing
  `region_first_safe_merge` compatibility behavior remains characterized and
  must not be used as fallback authorization for selected-envelope promotion.
- Preserve current targeted CSV/workbook `Area` semantics unless a separate
  approved public-output spec changes them. Targeted `Area` is currently raw
  integrated area; alignment primary matrix area is the AsLS-selected product
  value path.
- Do not make targeted workbook area, old strict area mismatch, target label, or
  target pass/fail logic a boundary oracle.
- Manual or expert-reviewed overlay boundaries/areas are the boundary oracle for
  FE2. Targeted benchmark subsets may only select rows, provide role-aware
  controls, or calibrate expectations.
- Output writers, workbook builders, and TSV/HTML renderers consume selected
  `IntegrationResult` and audit fields. They must not recompute boundaries or
  rescan RAW files.
- Any selected-envelope domain carrier must make resolver interval, selected
  envelope, quantitation context, change class, stop reason, and legacy
  provenance explicit. This can be an `IntegrationResult` extension, an attached
  domain DTO, or a selected-hypothesis audit model, but it must have a named
  compatibility strategy before implementation.
- `peak_candidate_boundaries` and other diagnostic row builders must consume the
  domain evaluator output for selected-envelope diagnostics. They must not
  recompute selected-envelope baseline areas during row rendering.
- Public schema changes for diagnostic TSVs, workbook advanced sheets, or
  alignment outputs must be documented and covered by contract tests.
- Keep FE0-FE2 diagnostic/fixture/manual-oracle work separate from product
  promotion. Do not switch primary matrix values until the explicit gate allows
  it.
- RAW-backed validation must follow `docs/agent-parameter-settings.md`: no
  background 85RAW `Start-Process`, no unclear DLL path guessing, and no RAW run
  if the result cannot change the next action.
- Verification integrity: do not weaken tests, assertions, schema checks,
  generated-output checks, lint, typecheck, or validation gates to make the goal
  pass.
- Keep unrelated dirty worktree changes out of this goal. Do not stage, commit,
  push, merge, or open a PR unless the user explicitly asks.

SUBAGENT / XHIGH REVIEW PROTOCOL:
- Before execution, review this goal with repo-routed read-only subagents:
  `strategy-challenger`, `implementation-contract-reviewer`, and
  `validation-evidence-reviewer`, all with xhigh reasoning if runtime supports it.
- Fix every blocker in this document before implementation starts.
- After fixing blockers, ask the original blocker reviewer to re-check.
- During implementation, after each phase completes, run a read-only review:
  - FE0/FE1/FE2: `implementation-contract-reviewer`;
  - FE3/FE4/FE5a: `validation-evidence-reviewer`;
  - FE5b or any product promotion / legacy-retirement wording:
    `strategy-challenger` and `implementation-contract-reviewer`.
- Do not replace requested multi-angle review with one generic reviewer unless
  thread limits block it; if blocked, run reviewers sequentially and report it.

PHASES:

Phase FE0 - Implementation Contract Preflight
Purpose:
- Lock public output contracts and internal carriers before writing selected
  envelope behavior.
Allowed work:
- Document whether selected-envelope fields are emitted as a diagnostic sidecar,
  appended diagnostic TSV columns, workbook advanced/audit fields, or a
  combination.
- Confirm targeted CSV/workbook `Area` remains raw integrated area for this
  goal, while alignment primary matrix values continue to use the AsLS selected
  product path.
- Choose and document the domain carrier for resolver interval, selected
  envelope, quantitation context, boundary change class, stop reason, evidence
  sources, area delta, and legacy provenance:
  `IntegrationResult` extension, attached domain DTO, selected-hypothesis audit
  model, or another named package-level model.
- Characterize existing `region_first_safe_merge` behavior so it remains a
  compatibility path and cannot authorize selected-envelope promotion by
  fallback.
- Characterize existing diagnostic row builders, especially
  `peak_candidate_boundaries`, and identify every place that currently recomputes
  baseline/integration during rendering.
- Add or update tests that protect targeted `Area` raw semantics, alignment
  primary matrix AsLS semantics, diagnostic rendering-only behavior, and
  `region_first_safe_merge` non-fallback behavior.
Forbidden work:
- No selected-envelope evaluator implementation yet except minimal type stubs if
  tests require a carrier.
- No product matrix switch.
- No RAW launch.
Done when:
- The chosen carrier and public projection strategy are recorded in tests and/or
  docs.
- Focused tests fail if writers recompute selected-envelope area, targeted
  `Area` silently changes to AsLS, or `region_first_safe_merge` is used as
  selected-envelope promotion fallback.

Phase FE1 - Synthetic Boundary Policy Fixtures
Purpose:
- Lock selected-envelope semantics before building the evaluator against real
  data.
Allowed work:
- Add synthetic tests for:
  clean single peak with clipped resolver flanks;
  clean single peak where resolver already matches envelope;
  normal single peak with a short internal dip that `local_minimum` would cut
  but OpenMS-style morphology should bridge;
  deep internal valley plus independent apex/split evidence that must be
  externalized, not bridged;
  two resolved neighboring peaks;
  shoulder peak requiring split/review;
  tailing peak with uncertain tail;
  low-S/N trace;
  carryover or blank-like context peak;
  low scan support or malformed trace.
- Define named, audited policies for:
  quantitation context fence,
  morphology trace method/window,
  sustained baseline return,
  internal-dip bridge,
  tail stop,
  max envelope width,
  neighboring apex / split conflict,
  carryover / blank-like conflict.
- Keep exact numeric thresholds fixture-backed and visible in diagnostics.
Forbidden work:
- Do not hide thresholds as dead constants.
- Do not use target-specific patches to pass fixtures.
Done when:
- Synthetic fixture tests fail on known unsafe interpretations and pass on the
  bounded selected-envelope behavior.
- SavGol, CWT, local minimum, derivative, WIS, RT, shape, and S/N are represented
  as evidence sources, not final authority.
- The evaluator fails tests if it behaves like single-point
  local-minimum/valley-to-valley termination on a normal single peak with a
  short internal dip.
- FE1 review finds no unbounded context, tail, or neighbor-apex swallowing path.

Phase FE2 - Diagnostic Characterization
Purpose:
- Build a diagnostic-only comparison between the current resolver interval and
  candidate selected full-envelope interval under the same selected peak and
  AsLS baseline, using the FE0 carrier and FE1 policies.
Allowed work:
- Add the selected-envelope evaluator or diagnostic helper under
  `xic_extractor/peak_detection`, keeping baseline area ownership in existing
  AsLS `IntegrationResult`.
- Define and expose the diagnostic fields from the spec:
  `selected_candidate_id`,
  `selected_boundary_mode`,
  `row_boundary_decision`,
  `legacy_resolver_provenance`,
  `resolver_rt_start/end`,
  `envelope_rt_start/end`,
  `quantitation_context_rt_start/end`,
  `morphology_trace_method`,
  `morphology_trace_window_points`,
  `morphology_trace_effective_points`,
  `policy_snapshot`,
  `resolved_baseline_return_threshold`,
  `boundary_change_class`,
  `boundary_evidence_sources`,
  `boundary_stop_reason`,
  `asls_area_old_interval`,
  `asls_area_selected_envelope`,
  `area_delta_ratio`,
  and `plot_path` when plots are produced.
- Add a minimal GO/NO-GO manifest schema for diagnostic output:
  `gate_decision`,
  `changed_row_count`,
  `changed_row_denominator`,
  `high_risk_strata`,
  `unresolved_blocker_count`,
  `blocked_reasons`,
  `next_gate`.
- Register any new diagnostic CLI or output group in `tools/diagnostics/INDEX.md`.
Forbidden work:
- No primary matrix value switch.
- No 8RAW or 85RAW launch.
- No final product promotion wording.
Done when:
- Focused tests prove resolver interval and selected-envelope interval can be
  compared without recomputing baseline in writers.
- Diagnostic output can represent no-change, flank-recovered, split-supported,
  neighbor-apex, tail-uncertain, overmerge-rejected, carryover/blank-like, and
  malformed/low-scan cases.
- Row-level `row_boundary_decision` can be `accept_candidate`, `reject`,
  `externalize`, or `defer`. Aggregate `gate_decision` remains a manifest-only
  field that can be `promote`, `no_go`, `externalize`, or `defer`; manifest
  `no_go` kills the selected-envelope product path before RAW scale-up.

Phase FE3 - Manual / Expert Overlay Oracle
Purpose:
- Prove that the selected-envelope candidate is closer to manual or
  expert-reviewed boundary/area on rows where a boundary oracle exists.
Allowed work:
- Use `manual-2raw` rows only when they match the boundary decision being tested.
- Add or extend a boundary oracle artifact that records expert-reviewed RT
  bounds, area, shape status, clean/split/tailing labels, and acceptable error
  bands.
- Use targeted benchmark subsets only as row selectors, role-aware controls, or
  calibration inputs; do not treat workbook area or target pass/fail as boundary
  truth.
- Include SavGol as a clean single-peak comparator when the row is marked clean
  and single-peak.
- Produce overlay plots for changed rows and high-risk rows:
  raw/original XIC,
  AsLS baseline,
  current resolver interval,
  candidate selected-envelope interval,
  manual/expert overlay interval when available.
Forbidden work:
- Do not use old linear-edge workbook area as a hard gate.
- Do not infer untargeted identity from targeted labels.
Done when:
- Manual/expert overlay comparison reports area/boundary deltas for current
  resolver interval versus selected full-envelope interval.
- Rows without a true boundary oracle are marked benchmark/control only.
- Gate manifest states whether 8RAW changed-row review is allowed:
  `promote`, `no_go`, `externalize`, or `defer`.

Phase FE4 - 8RAW Changed-Row Review
Purpose:
- Test the diagnostic behavior on a small real-data surface before any 85RAW run
  or product switch.
Allowed work:
- Run a foreground 8RAW changed-row diagnostic only after FE0-FE3 are reviewed
  as ready and `docs/agent-parameter-settings.md` runner requirements are checked.
- Report changed-row denominator by status/role stratum.
- Stratify changed rows by flank recovery, area decrease, area increase, split,
  neighbor apex, tail uncertainty, overmerge rejected, carryover/blank-like, low
  scan support, and malformed trace.
- Generate overlay plots for high area-decrease, high area-increase, and every
  high-risk stratum needed to decide the gate.
- Ask `validation-evidence-reviewer` to accept or reject FE4.
Forbidden work:
- Do not advance to 85RAW on `no_go`.
- Do not hide unresolved blockers behind representative plots.
- Do not switch primary matrix values during FE4.
Done when:
- FE4 manifest emits `promote`, `no_go`, `externalize`, or `defer`.
- `promote` has zero unresolved blockers and required expert-reviewed overlay
  verdicts for promotion-critical changed/high-risk rows.
- `no_go` or unresolved false merge, tail inflation, carryover absorption, or
  neighbor-apex switching stops the goal before FE5a.
- `externalize` keeps the selected-envelope behavior diagnostic/review-only.
- `defer` names one bounded follow-up gate.

Phase FE5a - Scale Gate
Purpose:
- Decide whether selected full-envelope boundaries can become eligible for a
  product-wiring slice.
Allowed work:
- If FE4 is `promote`, run the approved 85RAW or production-equivalent scale gate
  using repo RAW runner rules.
- Report changed-row counts, area delta distribution by status/role, high-risk
  stratum coverage, unresolved blocker counts, representative plots, and final
  `gate_decision`.
- Require machine-readable expert-reviewed overlay verdicts for
  promotion-critical changed/high-risk rows. Plots are review evidence, not
  boundary oracle.
Forbidden work:
- Do not claim `production_ready` from FE5a alone.
- Do not promote rows with unresolved false merge, tail inflation, carryover
  absorption, or neighbor-apex switching clusters.
- Do not restore linear-edge, SavGol-area, or context-wide residual behavior as
  fallback.
Done when:
- FE5a closeout states `promote`, `no_go`, `externalize`, or `defer`.
- `promote` authorizes only FE5b product wiring; it does not itself mutate
  primary matrix behavior.
- `no_go` kills the product path and keeps only safe diagnostic artifacts.
- `externalize` keeps the behavior diagnostic/review-only and documents why.
- `defer` names the single bounded follow-up gate that can close the missing
  evidence.

Phase FE5b - Conditional Product Wiring
Purpose:
- Switch product primary matrix behavior only after FE5a authorizes promotion.
Allowed work:
- Update product wiring so primary matrix values use
  `asls_area_selected_envelope` through selected `IntegrationResult`.
- Preserve targeted CSV/workbook `Area` raw semantics unless a separate approved
  output contract says otherwise.
- Update docs/tests to mark selected-envelope behavior `production_candidate`.
- Keep diagnostic/audit fields available for reviewer inspection and downstream
  migration.
Forbidden work:
- Do not run this phase unless FE5a `gate_decision=promote`.
- Do not claim `production_ready` from FE5b alone.
- Do not change public output schema or targeted `Area` semantics without tests
  and explicit docs.
Done when:
- Product matrix behavior changes only through selected `IntegrationResult`.
- Public schema/CSV/workbook/alignment writer tests prove no unintended output
  drift.
- The final readiness label is explicitly reported as `production_candidate` or
  `inconclusive`, unless a separate accepted production-ready closeout exists.

DONE WHEN:
- FE0-FE5b are completed or stopped by a named gate decision.
- Existing AsLS `IntegrationResult.area_baseline_corrected` remains the area
  owner; this goal does not create a parallel baseline formula owner.
- Selected-envelope boundaries are bounded by named context, baseline-return,
  tail, max-width, neighbor/split, and carryover/blank-like gates.
- Diagnostic/audit outputs distinguish resolver interval, selected envelope,
  quantitation context, boundary evidence, stop reason, area delta, and gate
  decision.
- Manual/expert overlay is the only boundary oracle. Targeted benchmark rows are
  role-aware controls or row selectors only.
- 8RAW and 85RAW gates, if run, use machine-readable gate manifests,
  plot-backed changed-row review, and expert-reviewed overlay verdicts for
  promotion-critical changed/high-risk rows.
- Primary matrix product behavior changes only after the explicit promote gate.
- No stale `linear_edge`, SavGol-area, context-wide residual, or first-class
  `safe_merge` product authority returns.
- No unrelated dirty files are staged or reverted.

VERIFY:
- Start with focused no-RAW tests for selected-envelope evaluator,
  `IntegrationResult` ownership, synthetic fixtures, diagnostic schema, and
  GO/NO-GO manifest.
- Run likely focused shards as implementation surfaces dictate, starting with:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_baseline_integration.py tests/test_peak_hypotheses.py tests/test_peak_region_selection_shadow.py tests/test_signal_processing_selection.py tests/test_alignment_ownership.py tests/test_peak_candidate_table.py tests/test_peak_candidate_boundaries.py`
- Run public output/schema shards when any diagnostic/output/result projection is
  touched:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_output_schema_contract.py tests/test_csv_writers.py tests/test_excel_pipeline.py tests/test_excel_sheets_contract.py tests/test_alignment_tsv_writer.py tests/test_alignment_xlsx_writer.py tests/test_result_assembly.py tests/test_handoff_spine_runtime.py`
- Run lint/type checks on touched implementation/test surfaces:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests`
  `$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor`
- Run `git diff --check`.
- If FE4/FE5a require RAW data, preflight with `docs/agent-parameter-settings.md`
  and `xic-raw-validation` expectations before launch; record exact command,
  output root, timing, and gate manifest.
- If a command fails because sandbox blocks dependency resolution, executable
  spawn, or DLL loading, rerun the same command with approval rather than
  replacing it with a weaker proof.

OUTPUT:
- Changed files grouped by domain logic, diagnostics, tests, docs, and validation
  artifacts.
- Current readiness label.
- Gate manifest summary for the latest completed FE phase.
- Key decisions about context fence, baseline-return threshold, tail stop, max
  width, neighbor/split behavior, carryover/blank-like behavior, and SavGol
  comparator placement.
- Exact verification commands and observed results.
- Artifact paths for diagnostics, overlay plots, changed-row TSVs, and closeout
  notes.
- Remaining risk and the next gate if the goal stops as `defer`,
  `externalize`, `no_go`, or `inconclusive`.

STOP RULES:
- Stop if the implementation needs a product decision not made by the spec, such
  as allowing context-wide integration or treating targeted workbook area as a
  boundary oracle.
- Stop if context fence, tail stop, max width, or neighbor/split behavior cannot
  be made machine-readable before promotion.
- Stop before FE4, FE5a, or FE5b if the previous gate is `no_go`,
  `externalize`, or unresolved `defer`.
- Stop before any RAW run if runner path, Thermo DLL path, output root, runtime
  expectation, or heartbeat/timing requirement is unclear.
- Stop if a change would weaken tests, schema checks, diagnostics, lint,
  typecheck, validation, or generated-output checks to pass.
- Stop after three failed attempts on the same symptom and revisit the
  root-cause hypothesis instead of adding patches.
- Do not mark complete until the current state is audited against every
  applicable `DONE WHEN` item and the latest FE gate decision is recorded.
```
