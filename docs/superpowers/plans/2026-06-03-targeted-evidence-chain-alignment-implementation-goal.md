# Targeted Evidence-Chain Alignment Implementation Goal

**Date:** 2026-06-03
**Status:** Executed in current branch; pending PR closeout
**Readiness target:** `production_ready` for targeted product detection after
focused no-RAW tests, 2RAW sentinel, full default-target run, consumer audit,
blast-radius report, and review acceptance pass. A 2RAW-only closeout is only
`production_candidate` and does not complete this goal.
**Primary spec:** [Targeted evidence-chain alignment spec](../specs/2026-06-03-targeted-evidence-chain-alignment-spec.md)
**Accepted validation root:**
`output/targeted_projection_default_targets_20260603_030225/`

**Final accepted gate artifact:**
`targeted_projection_acceptance_summary_after_selection_anchor_guard.tsv`

/goal
GOAL:
Implement the targeted evidence-chain alignment so targeted product detection is
decided by typed `TargetedProductProjection`, not direct legacy
score/confidence/cap/NL tokens, while preserving targeted/untargeted boundaries
and proving the default-target sentinel behavior with tests and RAW-backed
evidence.

CONTEXT:
- Repository/worktree:
  `C:\Users\user\Desktop\XIC_Extractor`, current branch.
- Required repo instructions:
  `AGENTS.md`,
  `docs/agent-subagent-routing.md`,
  `docs/agent-parameter-settings.md`.
- Primary spec:
  `docs/superpowers/specs/2026-06-03-targeted-evidence-chain-alignment-spec.md`.
- Durable evidence rules to keep aligned:
  `docs/lcms-msms-evidence-rules.md`.
- Targeted validation config:
  `config/targets.example.csv`,
  `config/settings.csv` unchanged unless a separate approved config spec exists.
- Real-data sentinel:
  `TumorBC2289_DNA / d3-5-medC` should move from legacy not-counted
  `NL_FAIL` / `VERY_LOW` review evidence to targeted `detected_flagged` when
  the typed policy conditions are met.
  `TumorBC2258_DNA / d3-N6-medA` must remain detected.
- Observed current-code sentinel workbook:
  `output/targeted_default_targets_example_sentinel_20260603/base/output/xic_results_20260603_0127.xlsx`.
- Code surfaces to inspect first:
  `xic_extractor/extractor.py`,
  `xic_extractor/extraction/result_assembly.py`,
  `xic_extractor/extraction/target_extraction.py`,
  `xic_extractor/peak_detection/facade.py`,
  `xic_extractor/peak_detection/hypotheses.py`,
  `xic_extractor/evidence_semantics.py`,
  `xic_extractor/output/detection.py`,
  `xic_extractor/output/csv_writers.py`,
  `xic_extractor/output/workbook_inputs.py`,
  `xic_extractor/output/sheet_summary.py`,
  `xic_extractor/output/review_metrics.py`,
  `xic_extractor/output/review_report.py`,
  `scripts/csv_to_excel.py`.
- Test surfaces to inspect first:
  `tests/test_target_extraction.py`,
  `tests/test_result_assembly.py`,
  `tests/test_evidence_semantics.py`,
  `tests/test_peak_hypotheses.py`,
  `tests/test_peak_scoring.py`,
  `tests/test_peak_scoring_evidence.py`,
  `tests/test_csv_writers.py`,
  `tests/test_review_metrics.py`,
  `tests/test_csv_to_excel.py`,
  `tests/test_excel_pipeline.py`,
  `tests/test_excel_sheets_contract.py`,
  `tests/test_targeted_peak_reliability_audit.py`.

CONSTRAINTS:
- Do not hard-code sample IDs, target labels, workbook row numbers, or local
  output paths into production behavior.
- Do not auto-promote analyte `NL_FAIL` rows. ISTD dropout handling is role- and
  context-specific.
- Do not make targeted pass/fail labels authoritative for untargeted matrix
  identity, owner/family/cell decisions, or cross-sample hypothesis selection.
- Do not change target config defaults or `targets.example.csv` to make the
  sentinel pass.
- Keep legacy score/confidence/cap/NL fields available as audit evidence unless
  a phase explicitly retires product authority for a consumer.
- Do not remove `score_candidate(...)` or public `xic_extractor.peak_scoring`
  compatibility during this goal.
- Writers and report builders are projection consumers. They must not recompute
  evidence semantics or infer product state from free-text `Reason`,
  `Confidence`, `NL`, or cap labels.
- Primary projection transport is stable advanced long-row fields in the
  targeted long CSV/workbook path, not a best-effort sidecar. This is a public
  schema change and must be covered by schema tests and closeout notes.
- Wide-only CSV-to-XLSX input without projection fields is legacy compatibility
  mode. It must not be used as an acceptance oracle for this goal and must not
  silently claim projection-driven product behavior.
- RAW-backed validation must follow `docs/agent-parameter-settings.md`: RAW
  commands use `.venv\Scripts\python.exe`; no bare `python` for RAW; no 85RAW
  background `Start-Process`; stop on missing stable RAW/DLL paths.
- Verification integrity: do not weaken tests, assertions, schema checks,
  review metrics, or RAW gates to make the goal pass.
- Keep unrelated dirty worktree changes out of this goal and do not stage or
  revert user changes.

PROJECTION TRANSPORT AND CONSUMER CONTRACT:
- Add `ExtractionResult.targeted_product_projection:
  TargetedProductProjection | None`.
- Render these stable advanced long-row fields at minimum:
  `Product State`,
  `Counted Detection`,
  `Review State`,
  `Projection Reason`,
  `Projection Support Reasons`,
  `Projection Review Reasons`,
  `Projection Conflict Reasons`,
  `Projection Not Counted Reasons`,
  `Projection Exclusion Reasons`,
  `Legacy Authority Status`,
  and `Benchmark Eligibility State` when benchmark/reliability reporting needs
  it.
- Score-breakdown output must include enough projection fields to prove
  `Detection Counted` came from projection, not `Confidence` or `NL`.
- `workbook_inputs`, `excel_pipeline`, `csv_writers`, workbook builders,
  `sheet_summary`, `review_metrics`, `review_report`, review queue/model
  surfaces, console/run summaries, and `output.detection` must consume
  projection fields or be explicitly fenced as `legacy_compatibility`,
  `evidence_only`, or `diagnostic_only`.
- In Phase 2 product mode, absence of required projection fields is an error or
  blocker. Do not silently fall back to `Confidence`, `NL`, caps, or free-text
  `Reason`.
- `output.detection` should become a projection reader for product paths. Any
  remaining legacy string helper must be named and documented as compatibility
  only, and tests must prove product consumers do not call it when projection is
  available or required.
- Add a no-leak gate proving targeted projection labels such as
  `TargetedProductProjection`, `detected_flagged`, product-state columns, and
  `targeted_review_positive` are not used as untargeted identity authority,
  owner/family/cell policy, or clean benchmark denominator without an approved
  contract.

SUBAGENT / XHIGH REVIEW PROTOCOL:
- Before execution, review this goal with repo-routed read-only subagents:
  `strategy-challenger` and `implementation-contract-reviewer`, both with
  xhigh reasoning if the runtime supports it.
- If implementation touches RAW validation or full default-target acceptance,
  add `validation-evidence-reviewer` before launch or acceptance.
- After implementation and focused verification, run a read-only implementation
  review focused on missed legacy detection bypasses, output schema drift, and
  target/untarget leakage.
- Use the repo fix/re-check loop:
  fix blocker -> ask the original blocker reviewer to re-check -> add another
  reviewer only if the fix moved into validation, docs-handoff, or ops scope.

PHASES:

Phase 0 - Goal Contract And Review
Purpose:
- Land this implementation goal after xhigh review.
Done when:
- `strategy-challenger` and `implementation-contract-reviewer` report no
  blocking findings, or every blocker is fixed in this document.
- Dirty scope is recorded and unrelated files are not staged.

Phase 1 - Typed Projection Core
Purpose:
- Add the typed targeted product oracle without changing workbook/summary
  behavior before tests define the new authority.
Allowed work:
- Add `TargetedPriorContext` and `TargetedProductProjection` in a targeted
  peak-domain module or approved selection-decision extension.
- Add projection states:
  `detected_clean`, `detected_flagged`, `not_counted`, `excluded`, `ambiguous`.
- Add `counted_detection`, `review_state`, stable projection reasons,
  support/review/conflict/not-counted/exclusion reason lists,
  `legacy_evidence`, `legacy_authority_status`, and optional
  `benchmark_eligibility_state`.
- Build targeted adapter/view inputs from existing peak evidence and target
  metadata without creating a new durable evidence spine.
- Add adversarial unit tests proving:
  same legacy `Confidence`/`NL` can count differently when typed projection
  differs;
  ISTD `NL_FAIL + VERY_LOW` can be `detected_flagged` when the dropout policy is
  satisfied;
  analyte `NL_FAIL` is not counted only because the ISTD rule exists.
Forbidden work:
- No output consumer migration yet unless Phase 1 tests require a minimal
  object field on `ExtractionResult`.
- No hidden target-name exception for `d3-5-medC`.
Done when:
- Typed projection tests pass.
- Shared evidence semantics still does not directly assert targeted presence or
  counted detection.

Phase 2 - Product Consumer Migration
Purpose:
- Make targeted product surfaces consume typed projection instead of legacy
  detection helpers.
Allowed work:
- Add projection to `ExtractionResult` and assembly paths.
- Update result assembly, targeted extraction, CSV writer, workbook conversion,
  summary detected counts, review metrics, score-breakdown detection counted
  field, and any final targeted matrix consumer to use `counted_detection` /
  `product_state`.
- Add the long-row projection transport fields listed in this goal, and update
  CSV-to-XLSX workbook input parsing to consume them. Wide-only fallback remains
  legacy compatibility and is not a product acceptance path.
- Keep legacy `Confidence`, `NL`, score, and caps rendered as audit evidence.
- Add contract tests that fail if workbook/summary/review consumers fall back to
  legacy strings when projection is present or required.
- Add an absent-projection test proving product mode fails or blocks rather than
  silently deriving detection from `Confidence`, `NL`, caps, or `Reason`.
- Add no-leak tests or static audits for targeted projection vocabulary in
  untargeted identity, owner/family/cell, and benchmark-denominator paths.
- Update output schema tests if projection fields become visible workbook/CSV
  columns.
Forbidden work:
- Do not let output modules recompute evidence semantics.
- Do not replace untargeted identity or alignment decisions with targeted
  product projection.
Done when:
- Workbook rows, summary detected counts, review metrics, score breakdown, and
  targeted final matrix value presence are projection-driven.
- Legacy string detection helpers are either removed from product paths or
  fenced as legacy compatibility/audit-only.

Phase 3 - Retirement Gate, Sentinel Validation, And Docs Sync
Purpose:
- Prove the behavior with the requested default target config and close the
  legacy product-authority exit rule for this goal.
Allowed work:
- Add a consumer audit or focused static/test check listing all remaining
  product consumers of legacy score/confidence/cap/NL tokens and their status:
  `legacy_evidence`, `evidence_only`, `diagnostic_only`, `retired`, or blocker.
- Add a dirty-scope snapshot before implementation and before closeout:
  `git status --short --branch`, with unrelated files explicitly excluded from
  staging/commit scope.
- Add a blast-radius report over the default-target run:
  all ISTD not-detected rows with explicit blockers;
  all analyte `NL_FAIL` rows newly counted;
  remaining legacy product consumers.
- Add machine-verifiable 2RAW staging provenance:
  `targets.example.csv` hash,
  `settings.csv` hash,
  exact staged RAW basenames,
  output path,
  and projection assertion result.
- Run the 2RAW sentinel with unchanged `config/targets.example.csv` and
  unchanged `config/settings.csv`.
- If the sentinel passes and the blast-radius report is bounded, run the full
  default-target tissue RAW run and ask `validation-evidence-reviewer` for
  acceptance review. If this run is skipped or blocked, this goal cannot close
  as complete; close as blocked/incomplete with a `production_candidate`
  handoff.
- Sync durable accepted behavior into `docs/lcms-msms-evidence-rules.md` and any
  targeted output contract touched by the implementation.
Done when:
- `TumorBC2289_DNA / d3-5-medC` projects as `detected_flagged` with plausible
  DDA NL dropout reasoning.
- `TumorBC2258_DNA / d3-N6-medA` remains detected.
- Analyte `NL_FAIL` rows are not auto-counted.
- Every ISTD not projected as detected has an explicit blocker.
- No product path maps score/confidence/cap/NL directly to detected/ND.
- Full default-target validation is `gate_ok`, or the goal stops before being
  marked complete.

DONE WHEN:
- Targeted product detection has exactly one authority:
  `TargetedProductProjection.counted_detection` / `product_state`.
- Legacy score/confidence/cap/NL remains observable as audit evidence but cannot
  decide workbook detected versus ND, summary detected counts, review metrics,
  score-breakdown detection counted, or targeted matrix value presence.
- Shared evidence semantics and untargeted identity remain independent from
  targeted product pass/fail labels.
- ISTD DDA NL dropout is represented as `detected_flagged` only when the typed
  targeted dropout policy is satisfied.
- General analyte `NL_FAIL` rows are not counted without a separate approved
  analyte policy.
- The 2RAW sentinel passes with unchanged default target/settings files.
- The full default-target run passes with a validation-evidence acceptance
  review; otherwise the goal is not complete.
- Blast-radius and consumer-audit artifacts identify remaining blockers or
  prove remaining legacy users are audit/evidence/diagnostic only.
- No-leak guard proves targeted product projection is not untargeted identity
  authority or a clean benchmark denominator.
- Focused no-RAW tests, lint/type checks appropriate to the touched surfaces,
  and docs smoke checks have fresh results.
- No unrelated dirty files are staged or reverted.

VERIFY:
Run focused no-RAW tests first, split if needed:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run pytest -q tests/test_target_extraction.py tests/test_result_assembly.py tests/test_evidence_semantics.py tests/test_peak_hypotheses.py tests/test_peak_scoring.py tests/test_peak_scoring_evidence.py tests/test_csv_writers.py tests/test_review_metrics.py tests/test_csv_to_excel.py tests/test_excel_pipeline.py tests/test_excel_sheets_contract.py tests/test_targeted_peak_reliability_audit.py
uv run ruff check xic_extractor tests
uv run mypy xic_extractor
git diff --check
git status --short --branch
```

Run RAW-backed sentinel only after focused tests pass and preflight confirms
stable paths:

```powershell
Get-Command python | Select-Object -ExpandProperty Source
python --version
.venv\Scripts\python.exe --version
.venv\Scripts\python.exe -c "import importlib.util; print('pythonnet', importlib.util.find_spec('pythonnet') is not None); print('pytest', importlib.util.find_spec('pytest') is not None)"
.venv\Scripts\python.exe -m scripts.run_extraction --help
Test-Path "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R"
Test-Path "C:\Xcalibur\system\programs"
```

Then run a staged 2RAW targeted extraction using unchanged
`config/targets.example.csv` and unchanged `config/settings.csv`:

```powershell
.venv\Scripts\python.exe -m scripts.run_extraction `
  --base-dir <staged-base-with-targets.example.csv-and-settings.csv> `
  --data-dir <staged-TumorBC2258_DNA-and-TumorBC2289_DNA-raw-dir>
```

After the 2RAW run, assert machine-readable rows for:

- `TumorBC2289_DNA / d3-5-medC`:
  `Product State = detected_flagged`,
  `Counted Detection = TRUE`,
  projection reason includes plausible DDA NL dropout,
  legacy `NL` may remain `NL_FAIL`.
- `TumorBC2258_DNA / d3-N6-medA`:
  counted detection remains true.

For full default-target validation, record the command, output workbook or
machine artifact paths, ISTD blocker list, analyte `NL_FAIL` promotion list,
consumer audit result, and validation-evidence reviewer verdict.

OUTPUT:
- Phase-by-phase status.
- Changed files by phase.
- Product projection schema/transport decision.
- Consumer audit table.
- Blast-radius artifact paths.
- Sentinel workbook/report paths and key row verdicts.
- Reviewer findings and fixes.
- Verification commands and observed results.
- Remaining risk and next action.

STOP RULES:
- Stop if projection transport cannot be typed and must rely on free-text
  `Reason`, `Confidence`, `NL`, or legacy score parsing.
- Stop if ISTD/analyte role cannot be determined without target-name exceptions.
- Stop if supporting MS1/RT/shape evidence is not available in targeted product
  outputs and cannot be carried without a new spec.
- Stop if a visible schema change is required but not covered by schema tests
  and output-contract notes.
- Stop if analyte `NL_FAIL` rows become counted without an approved analyte
  product policy.
- Stop if untargeted matrix identity starts trusting targeted pass/fail labels.
- Stop if RAW stable paths or DLL paths are missing.
- Stop after three failed fixes for the same symptom and revisit the root-cause
  hypothesis.
- Do not mark complete until the current state is checked against `DONE WHEN`.
