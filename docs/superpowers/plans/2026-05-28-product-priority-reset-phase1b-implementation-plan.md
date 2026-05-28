# Product Priority Reset Phase 1b Implementation Plan

**Date:** 2026-05-28
**Status:** reviewed and revised
**Branch:** `codex/product-priority-reset`

## Objective

Implement the same-PR Phase 1b correction from
`docs/superpowers/specs/2026-05-28-product-priority-reset-decision-spec.md`:
replace weak-seed / high-backfill-dependency as a family-level production proxy
with a cell-evidence-backed untargeted promotion policy, then validate whether
the qualitative selection gate can return one final classification.

This plan is not a new scaffold phase. It changes production decision behavior
only where the current gate is `NO_GO`: untargeted discovery / alignment matrix
promotion for rescued-heavy single-dR rows.

## Current Decision To Close

`QUAL_SELECTION_READY_FOR_NEXT_BEHAVIOR_PR`

Allowed final classifications:

- `GO_FOR_NEXT_NARROW_BEHAVIOR_PR`
- `GO_FOR_NEXT_PRODUCT_DECISION_PR`
- `NO_GO_FIX_SELECTION_OR_BOUNDARY_FIRST`
- `INCONCLUSIVE_NEEDS_NAMED_MINIMAL_EVIDENCE`

## Non-Goals

- Do not change targeted extractor scoring, targeted workbooks, or
  `xic_extractor/peak_scoring.py`.
- Do not change resolver defaults, baseline defaults, ASLS promotion, CWT
  production behavior, or boundary selector defaults.
- Do not add ML/DL scaffolding, external untargeted tool gates, broad report
  surfaces, HTML/XLSX validation deliverables, or Phase2 cleanup.
- Do not create target-specific exceptions for `FAM000264`, `d3-N6-medA`,
  `TumorBC2289_DNA`, or `TumorBC2290_DNA`.
- Do not globally retune emitted discovery `evidence_score` unless a separate
  before/after ranking collateral contract is added. The default path avoids
  that.

## Current Implementation Surface

Confirmed with CodeGraph and targeted file reads:

- Production row decision owner:
  `xic_extractor/alignment/matrix_identity.py`
  - `decide_matrix_identity_row()`
  - `_promotion_decision()`
  - `_row_flags()`
  - `_single_dr_backfill_dependency()`
- Current weak-seed / backfill risk helper:
  `xic_extractor/alignment/identity_gates.py`
  - `SeedQualitySummary`
  - `summarize_detected_seed_quality()`
  - `classify_single_dr_backfill_dependency()`
- Discovery scoring surface:
  `xic_extractor/discovery/evidence_score.py`
  - `DiscoveryEvidence`
  - `score_discovery_evidence()`
  - `classify_ms1_support()`
  - `classify_rt_alignment()`
- Diagnostic gate surface:
  `tools/diagnostics/single_dr_production_gate_decision_report.py`
  - `build_decision_report()`
  - `_classify_family()`
- Existing tests to extend:
  - `tests/test_alignment_matrix_identity.py`
  - `tests/test_single_dr_production_gate_decision_report.py`
  - `tests/test_discovery_evidence.py`
  - `tests/test_alignment_tsv_writer.py` or the existing alignment-review writer
    contract equivalent.

## Design Shape

Add one shared promotion policy owner inside `xic_extractor/alignment/`.
Preferred name:

- `xic_extractor/alignment/promotion_policy.py`

The module should expose a small typed contract used by both production and the
single-dR diagnostic:

- `BackfillPromotionEvidence`
- `BackfillPromotionDecision`
- `classify_backfill_promotion()`
- canonical reason constants:
  - `cell_evidence_supported_backfill`
  - `dda_limited_ms2_but_ms1_shape_supported`
  - `neighboring_ms1_interference_blocked`
  - `low_ms1_assessable_coverage_blocked`
  - `rescue_only_blocked`

The shared policy must evaluate:

- row-level counts: detected, rescued, duplicate, ambiguous, total cells;
- row-level risk: rescue-heavy / high-backfill / weak-seed context;
- detected-seed quality from `SeedQualitySummary`;
- available cell-level signals from `AlignedCell` and `CellQualityDecision`:
  status, quality status, RT delta, trace quality, scan support, selected
  integration / region fields, source candidate id, and reason text;
- discovery candidate evidence only through existing candidate lookup /
  `CommonEvidence` conversion where already available.

Do not make production depend on optional overlay plots, manual EIC screenshots,
or a diagnostic-only sidecar. If true shape similarity is required but is not
available in the production path, stop with the canonical
`INCONCLUSIVE_NEEDS_NAMED_MINIMAL_EVIDENCE` classification and name the missing
production-path signal. If the missing signal would require a new public
contract, classify the current attempt as `NO_GO_FIX_SELECTION_OR_BOUNDARY_FIRST`
or revise the spec before coding; do not encode a target/family exception.

The diagnostic path must not maintain a second classifier. If the production
policy consumes in-memory `AlignedCell` / `CellQualityDecision` objects, add an
explicit `alignment_review.tsv` + `alignment_cells.tsv` adapter into
`BackfillPromotionEvidence` so the single-dR diagnostic calls the same policy on
serialized artifacts. Add a parity test proving the production fixture and the
TSV adapter produce the same decision, reason, confidence cap, and flags.

## Policy Rules

Hard blocks:

- `q_detected == 0` and rescued cells exist: reason `rescue_only_blocked`;
- duplicate claim pressure exceeds detected support;
- local apex / selected region cannot be assessed for the rescued row being
  promoted;
- high neighboring MS1 interference without selected-apex support;
- low MS1 assessable coverage that prevents local-apex / MS1 continuity
  evaluation;
- extreme backfill burden with weak or unavailable cell-level support.

Allowed support paths:

- `RT + chemical`: candidate-aligned product, fragment, or neutral-loss support
  in the same selected region;
- `RT + MS1 shape`: DDA / MS2 evidence is weak or absent, but the rescued cell
  has seed/family-compatible MS1 support and acceptable local-apex evidence;
- `RT + MS1 continuity`: selected apex is inside the expected local RT region,
  local-apex support is present, interference is below blocking threshold, and
  at least one additional MS1 signal is present: scan support, trace continuity,
  selected-peak dominance, or available shape/seed support.

`RT + local apex + low interference` alone is insufficient. At least one extra
MS1 or chemical support signal is required.

High family rescue burden is not a standalone veto. It should cap confidence or
add `high_backfill_dependency_capped` when cell-level evidence supports
production.

## Implementation Steps

- [ ] **Step 0: Preflight scope**
  - Confirm `git status --short --branch`.
  - Confirm only the active spec/plan/goal/code/tests for this PR are dirty.
  - Read `docs/agent-parameter-settings.md` before any RAW command.

- [ ] **Step 1: Add failing tests before production wiring**
  - Add focused tests for the shared promotion policy and production path.
  - Add or update tests before changing implementation:
    - total `evidence_score` alone cannot promote;
    - `RT + local apex + low interference` alone cannot promote;
    - DDA-limited support can promote when MS1 continuity / scan support /
      seed-compatible evidence is present;
    - rescue-only blocks;
    - duplicate pressure blocks or caps;
    - low assessable coverage blocks;
    - high neighboring interference blocks;
    - extreme backfill with unavailable support blocks.
  - Add matrix identity tests proving changed `include_in_primary_matrix`,
    `identity_reason`, `identity_confidence`, and `row_flags` through
    `decide_matrix_identity_row()` or `build_matrix_identity_decisions()`.
  - Add diagnostic parity tests proving the TSV adapter and production path use
    the same shared policy, not parallel weak-seed logic.
  - Add TSV contract tests for canonical `identity_reason` and supplemental
    `row_flags`.
  - Add delta-table tests for newly promoted, newly blocked, and reason-changed
    rows before writing the delta emitter.
  - Prefer deterministic synthetic fixtures, no RAW.

- [ ] **Step 2: Implement shared policy module**
  - Add `xic_extractor/alignment/promotion_policy.py`.
  - Keep it independent of CLI, diagnostics, writers, GUI, workbook output, and
    RAW readers.
  - Reuse `SeedQualitySummary` and existing `CommonEvidence` conversion rather
    than duplicating seed scoring.
  - Return both final reason and supplemental flags.
  - Provide two construction paths:
    - in-memory production evidence from `AlignedCell` / `CellQualityDecision`;
    - serialized diagnostic evidence from `alignment_review.tsv` /
      `alignment_cells.tsv` rows.

- [ ] **Step 3: Wire production matrix decisions**
  - Update `matrix_identity.py` so `_promotion_decision()` consumes the shared
    policy for single-dR rescued-heavy / weak-seed / high-backfill rows.
  - Keep existing review-only, consolidation-loser, duplicate-only,
    ambiguous-only, zero-detected, and duplicate-pressure hard blocks unless
    the shared policy gives a stricter reason.
  - Put the canonical final reason in `identity_reason`.
  - Put risk modifiers in `row_flags`, including
    `high_backfill_dependency_capped` when appropriate.
  - Do not overload `primary_evidence`.

- [ ] **Step 4: Preserve discovery score semantics**
  - If promotion components are needed, add them as typed internal summaries or
    helper functions.
  - Do not change `score_discovery_evidence()` output for existing fixtures.
  - Extend `tests/test_discovery_evidence.py` to prove existing scores and tiers
    remain stable while promotion components can differ.

- [ ] **Step 5: Wire the diagnostic to the same policy**
  - Update `tools/diagnostics/single_dr_production_gate_decision_report.py` so
    `_classify_family()` uses the shared policy result instead of maintaining a
    parallel weak-seed fork.
  - Add report rows for supported, blocked, capped, and unresolved decisions.
  - If adding a new diagnostic entry point, update `tools/diagnostics/INDEX.md`.
    Prefer extending the existing diagnostic to avoid index churn.

- [ ] **Step 6: Add output contract coverage**
  - Extend alignment-review writer tests or the closest existing TSV contract
    test to prove:
    - canonical `identity_reason` values are emitted;
    - supplemental `row_flags` are emitted;
    - no unexpected columns are added in no-new-column mode.

- [ ] **Step 7: Add or update delta/collateral artifact generation**
  - The Phase 1b gate note needs a table for newly promoted, newly blocked, and
    reason-changed rows.
  - Prefer adding this to the existing single-dR diagnostic output. If a helper
    script is introduced, it must be covered by tests and `tools/diagnostics/INDEX.md`.
  - The table must include family id, old/new status, old/new reason, evidence
    components, and whether cell-level evidence supported the decision.

- [ ] **Step 8: Focused no-RAW verification**
  - Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest `
  tests\test_alignment_matrix_identity.py `
  tests\test_single_dr_production_gate_decision_report.py `
  tests\test_discovery_evidence.py `
  tests\test_alignment_tsv_writer.py `
  -q
```

  - If the worktree `.venv` gains pytest, prefer:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
.venv\Scripts\python.exe -m pytest <same shard> -q
```

- [ ] **Step 9: 8RAW validation**
  - Use the documented foreground command shape from
    `docs/agent-parameter-settings.md`.
  - Before the full run, verify the worktree runner and launch contract:

```powershell
Test-Path .venv\Scripts\python.exe
.venv\Scripts\python.exe -m scripts.run_alignment `
  --discovery-batch-index "C:\Users\user\Desktop\XIC_Extractor\local_validation_artifacts\discovery\accepted_p8b\8raw\discovery_batch_index.csv" `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\product_priority_reset_phase1b\alignment_8raw_validation_minimal_superwindow `
  --expected-sample-count 8 `
  --output-level validation-minimal `
  --resolver-mode region_first_safe_merge `
  --backfill-scope production-equivalent `
  --audit-evidence-mode none `
  --performance-profile validation-fast `
  --owner-backfill-window-strategy super-window `
  --owner-backfill-superwindow-span-factor 2 `
  --timing-output output\product_priority_reset_phase1b\alignment_8raw_validation_minimal_superwindow\timing.json `
  --timing-live-output output\product_priority_reset_phase1b\alignment_8raw_validation_minimal_superwindow\timing.live.json `
  --preflight-only
```

  - Output directory:
    `output\product_priority_reset_phase1b\alignment_8raw_validation_minimal_superwindow`
  - Required flags:
    `--expected-sample-count 8`, `--output-level validation-minimal`,
    `--resolver-mode region_first_safe_merge`,
    `--backfill-scope production-equivalent`, `--audit-evidence-mode none`,
    `--performance-profile validation-fast`,
    `--owner-backfill-window-strategy super-window`,
    `--owner-backfill-superwindow-span-factor 2`,
    `--timing-output`, `--timing-live-output`.
  - Run single-dR production gate diagnostic on the output.
  - Acceptance:
    - all 13 current risky weak-seed rows are supported or blocked;
    - at most three named rows may be inconclusive;
    - no target/family exception is needed;
    - `FAM000264 / d3-N6-medA` passes only by the shared policy.

- [ ] **Step 10: 85RAW validation only after 8RAW closes**
  - Do not run 85RAW if 8RAW is `NO_GO` or broad `INCONCLUSIVE`.
  - If 8RAW passes, fresh PR70 / current validation evidence may be reused only
    when it is reclassified under the new shared policy and produces the full
    required production delta table. Stale pre-correction status/reason/row-flag
    evidence cannot support `GO_FOR_NEXT_PRODUCT_DECISION_PR` by itself.
  - Run a new 85RAW foreground refresh only when:
    - the active worktree has a verified `.venv` junction;
    - the command passes `--expected-sample-count 85 --preflight-only`;
    - the result can change the Phase 1b classification.
  - Output directory:
    `output\product_priority_reset_phase1b\alignment_85raw_validation_minimal_superwindow`
  - Acceptance:
    - all five hardened risky rows classified;
    - every production status / identity reason / confidence / row-flag delta
      is listed or zero-asserted outside the five named rows;
    - strict `AREA_MISMATCH` remains quantitative follow-up when identity, RT,
      boundary, and delivery are accepted.

- [ ] **Step 11: Gate note update**
  - Update or create:
    `docs/superpowers/notes/2026-05-28-qualitative-selection-acceptance-gate-note.md`
  - Include:
    - command shapes and output paths;
    - policy summary;
    - risky-row collateral table;
    - 8RAW classification;
    - 85RAW reuse/refresh decision;
    - exactly one `Final Classification:` line.

- [ ] **Step 12: Implementation review**
  - Dispatch read-only reviewers after code + note changes:
    - `implementation-contract-reviewer`
    - `validation-evidence-reviewer` with mode `acceptance`
    - `strategy-challenger` if the classification is `GO`
  - Fix blockers directly.
  - If a blocker reveals missing production evidence, convert the final
    classification to `NO_GO` or `INCONCLUSIVE`; do not paper over the blocker.

## Stop Rules

Stop and report before continuing if:

- the active worktree or branch is not `codex/product-priority-reset`;
- production requires true MS1 shape similarity but that signal is available
  only from optional diagnostic overlays;
- the implementation requires target-specific exceptions;
- targeted scoring changes are required to pass the gate;
- the emitted total `evidence_score` would need a global semantic change;
- 8RAW remains `NO_GO` or has more than three unresolved rows;
- reused or refreshed 85RAW evidence cannot be reclassified under the new policy
  with a complete production delta table;
- 85RAW has unlisted or unexplained production deltas;
- any RAW run starts repeating a known bad launch pattern, lacks heartbeat, or
  fails preflight.

## Completion Criteria

- Focused no-RAW tests pass.
- 8RAW validation and single-dR diagnostic close the 13 risky rows as supported
  or blocked, or the gate note names the limited inconclusive blockers.
- 85RAW is either safely reused, safely refreshed, or explicitly not run because
  the 8RAW result blocks escalation.
- The gate note contains exactly one final classification.
- Review blockers from required subagents are fixed or become explicit
  `NO_GO` / `INCONCLUSIVE` reasons.

## Plan Review Record

Reviewed with three read-only subagent angles before execution:

- `strategy-challenger`: initial blocker on non-canonical inconclusive label and
  under-specified 85RAW reuse. Fixed by routing missing production-path evidence
  to canonical final classifications and requiring reused 85RAW artifacts to be
  reclassified under the new policy with a full production delta table. Recheck:
  PASS.
- `implementation-contract-reviewer`: initial blocker on TSV diagnostic drift
  and test ordering. Fixed by requiring an `alignment_review.tsv` /
  `alignment_cells.tsv` policy adapter, production-vs-diagnostic parity tests,
  and pre-implementation matrix / diagnostic / TSV / delta-table tests. Recheck:
  PASS.
- `validation-evidence-reviewer` (`preflight+science`): initial blocker on spec
  command using root repo `.venv` for `<8-or-85>`. Fixed by changing the spec
  command to active-worktree `.venv\Scripts\python.exe` and adding explicit
  runner preflight. Recheck: PASS.
