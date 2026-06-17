# XIC productization handoff

Updated: 2026-06-17
Branch: `cc/framework-improvements`
HEAD after latest productization commit: `a2c7d347`
Purpose: short current-state snapshot for the next agent/session. This file is
not the product tier authority; use the control plane first.

## Current Objective

Converge non-GUI productization lanes to `production_candidate`,
`production_ready`, `parked`, `diagnostic_only`, or `blocked` with clear
evidence. GUI wiring/replay remains out of scope until the main GUI branch is
connected.

## Current State

- [scope warning] The goal/rule/handoff-prune dirty diff belongs to a side
  session. Preserve it, do not revert it, and do not mix it into a Backfill
  productization commit unless that side session explicitly owns the commit.
- [active] Backfill generated policy writer is `production_ready` only for
  current approved evidence classes plus row-specific observed-oracle rows:
  latest no-RAW replay classified 4613 rows as 511 `write_ready`, 0
  `detected_flagged`, and 4102 `blocked`; writer expected-diff passed 511/511.
- [active] Latest Backfill change adds
  `standard_peak_backfill_policy_quality_explanations.tsv`, an
  explanation-only sidecar for all 4613 generated policy rows. It does not
  change policy row content, writer authority, selected peaks, areas, counted
  detections, workbook output, or matrix values. It explains why blocked rows
  stayed blocked: 1087 are missing overlay path, and most of the rest combine
  shape/height/width/scan/apex-delta blockers or still need a new approved
  evidence class/passing oracle. Subagent review found no P1/P2; P3 row-count
  evidence gaps were fixed by adding focused row-parity tests and
  `backfill_policy_quality_explanation_row_count=4613` in the policy summary.
- [active] Broad Backfill 4613-row write is still `production_candidate`, not
  ready. The 4102 blocked rows need trace overlay/reintegration evidence or a
  new approved evidence class with oracle + expected-diff.
- [active] Backfill ready writer surfaces currently include five scoped slices
  totaling 439 cells before observed-oracle promotion: 72 high-signal clean,
  42 low-scan clean, 57 low-height clean, 69 low-height-low-scan clean, and
  220 low-height reintegration-stable. The 72 formerly `detected_flagged` rows
  then passed row-specific full-trace oracle and bring the current writer total
  to 511.
- [blocked] All-stability 299-row candidate pool cannot be promoted directly:
  formal family oracle was 19/20 with `FAM000949/NormalBC2261_DNA` area error
  `0.19621`, above the accepted 10% ceiling.
- [active] Shape-clean + reintegration-stable is useful candidate evidence, not
  writer authority: family oracle passed 20/20, but writer probe found 0 new
  writes / 104 unchanged pre-existing values.
- [blocked] Apex-delta, width-only, and shape-margin probes remain
  `production_candidate` only because heldout oracle checks failed.
- [active] Targeted MS1 shape identity limited rescue is `production_ready` for
  headless `5-hmdC + 5-medC` limited default that writes only
  `detected_flagged`. GUI and broader target rescue are blocked.
- [active] `sample_metadata_v1` is `production_ready` for no-output order
  projection only: extraction injection order, instrument-QC sidecar, alignment
  sample-column ordering, and RT-normalization anchor lookup can share the
  resolver. Roles/batch/matrix/exclusion must not change quant output without a
  separate expected-diff gate.
- [parked] ReviewAction audited apply copy exists and candidate sidecar verifier
  is `production_candidate`; selected-candidate switch and manual-boundary area
  recompute remain parked because they would change selected peak/area/counting.
- [active] Handoff mechanism has been pruned as a demo case. Old phase history
  is summarized in `docs/superpowers/handoffs/archive/2026-06-17_cc-framework-improvements_productization_handoff-prune_34cdf61d.md`.
  Second-pass read-only subagent review accepted the rule/hook/handoff changes.

## Files Changed

- `AGENTS.md`: added a short root rule that active handoffs must stay current,
  short, and pruned around the 200-line target.
- `.codex/skills/xic-goal-execution/SKILL.md`: added XIC-specific handoff
  snapshot discipline for `$goal-execution` usage.
- `C:\Users\user\.codex\skills\goal-execution\SKILL.md`: global goal execution
  now requires current-state handoff snapshots, archive summaries, optional
  notes, status labels, and pruning.
- `C:\Users\user\.codex\skills\handoff\SKILL.md`: direct `$handoff` usage now
  follows the same three-layer model.
- `.codex/hooks/*` and `.codex/hooks/fixtures/assert_hook_outputs.py`: hooks
  remind about stale/oversized handoff only; they do not author handoff content.
- `docs/agent/codex-operating-system.md` and
  `docs/agent/communication-review.md`: synced the handoff contract.
- `tests/test_standard_peak_backfill_productization.py`,
  `xic_extractor/diagnostics/standard_peak_backfill_productization.py`,
  `docs/superpowers/specs/2026-06-13-backfill-integration-policy-spec.md`, and
  `docs/superpowers/plans/2026-06-15-productization-control-plane.md`:
  Backfill quality-explanation sidecar contract/test/code/control-plane entry.

## Active Decisions

- Control plane owns maturity tier and active lane decisions:
  `docs/superpowers/plans/2026-06-15-productization-control-plane.md`.
- Active handoff is a current-state snapshot, not a chronological log. Archive
  stores completed phase summaries; notes are optional for long scratch logs.
- Hooks only remind or block deterministic failure modes. The executing agent
  owns handoff rewrite/prune judgment after reading diff and validation state.
- Backfill product authority must flow through generated policy, oracle evidence,
  and expected-diff; no manual TSV allowlist.
- No default extraction behavior, workbook schema, selected peak/area, counted
  detection, or primary matrix semantics may change without explicit
  expected-diff/product contract.

## Rejected Paths

- [superseded] Append-only handoff updates. Rewrite/prune this file instead.
- [blocked] Directly promote broad 4613-row Backfill writes from scoped slices.
- [blocked] Promote all-stability 299-row pool after the 19/20 oracle result.
- [blocked] Add a shape-clean writer flag while it has 0 new matrix writes.
- [parked] ReviewAction selected-candidate/manual-boundary product writeback.
- [blocked] Let sample roles/QC/blank/batch/matrix/exclusion alter quant output
  without a new expected-diff gate.

## Tests / Validation

- Handoff mechanism checks after rule changes: `python .codex\hooks\fixtures\assert_hook_outputs.py` passed; `git diff --check` passed with only LF/CRLF warnings; `python -m py_compile .codex\hooks\*.py .codex\hooks\fixtures\assert_hook_outputs.py` passed.
- Subagent review result: first reviewer found hook-noise and wording/placement
  gaps; fixes were applied. Second reviewer found no remaining P2/P3 issues and
  confirmed active handoff is 127 lines, archive is phase-summary only, and hook
  fixture/diff-check pass.
- Backfill quality sidecar checkpoint: focused Backfill tests, focused ruff,
  focused mypy, and the no-RAW 85RAW replay under
  `generated_policy_quality_explained_no_raw_productization/` passed after
  reviewer fixes. Full local gate after the commit scope also passed:
  `ruff check xic_extractor tests`, `mypy xic_extractor`,
  `pytest -v --tb=short -x` (`3780 passed, 1 skipped`), and
  `scripts/check_diagnostics_index.py`. No RAW or 85RAW rerun was needed because
  existing artifacts answered the decision.
- RAW policy: do not rerun 85RAW unless a new production-readiness decision
  needs it and existing artifacts cannot answer the question.

## Remaining Work

- [active] Keep this handoff under 200 lines during future checkpoints. Remove
  `[done]` and `[superseded]` items on the next prune unless they prevent a
  repeated mistake.
- [done] Backfill quality sidecar slice was subagent-reviewed, P3 findings were
  fixed, and commit `a2c7d347` landed.
- [blocked] Broad Backfill promotion needs broader oracle/product-writer evidence
  for missing/blocked cells, not another narrow dataset-specific slice.
- [blocked] GUI replay/parity waits for GUI branch reconnection.

## Next Actions

1. Continue Backfill broadening from the quality sidecar blocker distribution:
   choose one simple evidence class that can be tested with existing artifacts
   or a small no-RAW replay.
2. Do not promote rows directly from `quality_blockers`; any writer expansion
   still needs generated-policy evidence class, oracle evidence, and
   expected-diff.
3. GUI replay/parity remains out of scope until GUI is reconnected.
