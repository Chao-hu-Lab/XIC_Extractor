# XIC productization handoff archive

Archived: 2026-06-17
Branch: `cc/framework-improvements`
Source active handoff before prune: 1615 lines
Reason: convert append-heavy continuation handoff into a compact current-state
snapshot.

This archive is a phase summary, not a log. Read the current handoff first:
`docs/superpowers/handoffs/current/cc-framework-improvements-productization.md`.

## Completed Phase Summary

### Method Manifest / Replay

- `method_manifest_v1` and headless targeted CLI replay parity reached
  `production_ready` with schema/fixture coverage.
- GUI replay remains out of scope until GUI is reconnected.

### ReviewAction

- Audited apply-copy and expected-diff planning infrastructure exists.
- Candidate sidecar verifier now checks `select_candidate` IDs against targeted
  `peak_candidates.tsv` and fails closed on missing, duplicate, or ambiguous
  candidates.
- Selected-candidate product switch and manual-boundary area recompute remain
  parked because they would rewrite selected peak/area/counting.

### Sample Metadata

- `sample_metadata_v1` resolver is usable across extraction injection order,
  instrument-QC sidecar, alignment sample-column ordering, and RT-normalization
  anchor lookup.
- Tier: `production_ready` for no-output order projection only.
- Value-changing role behavior remains blocked until expected-diff/product
  contract exists.

### Targeted MS1 Shape Identity

- Limited headless support reached `production_ready` for
  `limited_5hmdc_5medc_v1`, `5-hmdC + 5-medC`, and `detected_flagged` only.
- Explicit support TSV, auto-limited CLI, and canonical no-flag headless default
  were validated with focused tests plus existing 8RAW/85RAW artifacts.
- GUI and broader target rescue remain blocked.

### Backfill Standard Seed Guard

- Product direction changed away from a hard `height >= 2e6` rule. Height is a
  rollout guardrail/demonstrator, not a durable product definition.
- Ready scoped writer slices:
  - 72 high-signal clean rows.
  - 42 low-scan clean rows.
  - 57 low-height clean rows.
  - 69 low-height-low-scan clean rows.
  - 220 low-height reintegration-stable rows.
- Five ready slices had a 439-cell union before row-specific observed-oracle
  promotion.
- Generated policy engine replaced manual writer TSV authority. It consumes a
  source activation audit and classifies rows as `write_ready`,
  `detected_flagged`, or `blocked`; writer only replays generated
  `write_ready`.
- Row-specific observed-oracle bridge promoted the previous 72
  `detected_flagged` rows after 72/72 full-trace reintegration passed accepted
  `0.1 min / 10% area` tolerance.
- Latest no-RAW replay over 4613 rows: 511 `write_ready`, 0
  `detected_flagged`, 4102 `blocked`; writer expected-diff passed 511/511.
- Broad 4613-row Backfill remains `production_candidate`.

## Important Decisions

- Control plane remains the tier authority; handoff is only a continuation
  summary.
- Diagnostic TSVs, sidecars, wrappers, and reports prove observability, not
  production behavior.
- Backfill broadening must add a named evidence class, oracle/product-writer
  evidence, and expected-diff. Dataset-specific nested slices are staging
  evidence unless they close a broader product decision.
- Manual TSVs cannot be writer authority. Generated policy + provenance +
  expected-diff are required.
- Sample metadata roles must not alter quant output without a separate
  value-changing product gate.

## Rejected Or Parked Paths

- Broad 4613-row Backfill direct promotion from scoped writer success.
- All-stability 299-row writer promotion: formal family oracle failed 19/20
  because one area error exceeded 10%.
- Apex-delta, width-only, and shape-margin writer promotions: heldout oracles
  failed.
- Shape-clean writer flag: oracle passed, but writer probe had 0 new writes and
  104 unchanged rows.
- ReviewAction selected-candidate and manual-boundary product writeback:
  parked until expected-diff and product apply contracts are explicit.
- GUI replay/parity: blocked until GUI branch is connected.

## Final Validation Snapshot From Archived Handoff

- Handoff/rule mechanism checks after prune-rule implementation:
  `python .codex\hooks\fixtures\assert_hook_outputs.py` passed;
  `git diff --check` passed with LF/CRLF warnings only;
  `python -m py_compile` for hook scripts passed.
- Read-only subagent review first found hook-noise and wording/placement gaps;
  fixes were applied. Second review found no remaining P2/P3 issues and accepted
  the active handoff / archive split.
- Prior productization gates recorded in the old handoff included multiple
  focused Backfill shards, ruff/mypy/diagnostics-index passes, and full pytest
  runs. Treat those as historical evidence only; rerun current gates before PR
  because the worktree has dirty productization files.

## Pointers

- Current handoff:
  `docs/superpowers/handoffs/current/cc-framework-improvements-productization.md`
- Control plane:
  `docs/superpowers/plans/2026-06-15-productization-control-plane.md`
- Deep research background:
  `docs/deepresearch/Backfill Production Gate.md`
