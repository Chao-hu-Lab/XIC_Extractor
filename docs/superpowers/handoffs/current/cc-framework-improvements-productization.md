# XIC productization handoff

Updated: 2026-06-18
Branch: `cc/framework-improvements`
HEAD before current six-goal sequence: `87c51c05`
Purpose: short current-state snapshot for the next agent/session. The control
plane remains the product tier authority.

## Current Objective

Execute the low-manual productization sequence toward mechanically adjudicated,
reviewable, non-black-box decisions. Goal 0/1 authority/adjudication is being
hardened, Goal 2 review packets are now the active checkpoint, and later goals
must proceed through truth lockbox, missing-overlay evidence recovery, control
plane cleanup, and bounded non-broad lane hardening.

## Current State

- [parked] Broad Backfill auto-write remains parked. The 4613 rows are the
  candidate/audit universe, not writable cells.
- [ready] Current Backfill product authority remains exactly 511
  generated-policy `write_ready` cells. Nothing in this checkpoint changes
  ProductWriter, matrix/workbook semantics, selected peak/area, counted
  detection, extraction defaults, CLI/config, or GUI behavior.
- [active] Goal 0/1 hardening added
  `scripts/check_productization_authority.py`, a reusable fail-closed checker
  for the authority manifest, adjudication schema, and 4613-row index.
- [active] Goal 2 added Review Packet / Approval Workflow v1 as a contract
  artifact:
  - 3015 trace-matched unresolved rows are in `review_queue_v1.tsv` as
    `review_ready`.
  - 1087 missing-overlay rows stay out of review queue and remain Goal 4
    evidence-recovery work.
  - Reviewer actions are limited to
    `approve_candidate;reject_candidate;escalate_unresolved`.
  - Free-form value filling is forbidden.
  - Approval writes only to `review_decision_log_v1.tsv`; it grants no product
    authority and cannot touch matrix values.
- [active] `quality_explanations` and `quality_blockers` are explanation and
  triage inputs only. They cannot grant write authority or become writer
  predicates.
- [active] ISTD evidence is a limited reference anchor only. It does not prove
  analyte peak choice, analyte area truth, or broad Backfill safety.
- [ready] Targeted MS1 shape identity limited rescue remains production-ready
  only for headless `5-hmdC + 5-medC` limited default writing
  `detected_flagged`. GUI and broader targets remain blocked.
- [ready] `sample_metadata_v1` remains production-ready for no-output ordering
  and metadata projection only.
- [parked] ReviewAction selected-candidate switch and manual-boundary area
  recompute remain parked because they would change selected peak/area/counting.

## Files Changed This Round

- `scripts/check_productization_authority.py`: reusable fail-closed authority
  checker.
- `tests/test_check_productization_authority.py`: happy-path and forbidden-scope
  regression tests for the checker.
- `docs/superpowers/specs/review_packet_schema.v1.json`: Review Packet /
  decision-log contract.
- `docs/superpowers/validation/review_queue_v1.tsv`: 3015 structured review
  packets generated from existing artifacts.
- `docs/superpowers/validation/review_decision_log_v1.tsv`: empty structured
  decision-log template.
- `tests/test_review_packet_contract.py`: review queue/log authority and schema
  tests.
- `docs/superpowers/plans/2026-06-15-productization-control-plane.md`: tier and
  maintenance-log updates for this checkpoint.

## Active Decisions

- Authority remains fail-closed: only manifest-registered authority can ever
  write, and current authority is still 511 cells.
- Review Packet approval is not ProductWriter approval. It records structured
  human judgment only.
- 3015 rows are review candidates, not auto-write candidates.
- 1087 missing-overlay rows require evidence recovery before review or product
  claims.
- Broad Backfill can reopen only with a new independent truth source and a later
  expected-diff authority update.
- RAW/85RAW is not needed for this checkpoint because the artifacts are
  contract/index transforms over existing no-RAW evidence.

## Rejected Paths

- [blocked] Treat 4613 candidate/audit rows as approved writes.
- [blocked] Promote broad Backfill from `quality_blockers`, round-trip oracle,
  all-stability, apex-delta, width-only, shape-margin, or another nested writer
  slice.
- [blocked] Use review approval as write authority.
- [blocked] Allow reviewers to free-form fill values.
- [blocked] Auto-write missing-overlay rows without recovered trace evidence.
- [blocked] Use ISTD as analyte peak-choice or area truth without independent
  proof.

## Tests / Validation

- Focused checkpoint tests passed:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_review_packet_contract.py tests/test_check_productization_authority.py tests/test_productization_authority_mechanical_adjudication.py -v --tb=short`
  (`12 passed`).
- Focused lint passed:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts/check_productization_authority.py tests/test_review_packet_contract.py tests/test_check_productization_authority.py tests/test_productization_authority_mechanical_adjudication.py`.
- Checker passed:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_productization_authority.py`.
- JSON parse passed for `review_packet_schema.v1.json`.
- Full local gate passed:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests`,
  `$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor`,
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x`
  (`3792 passed, 1 skipped`), and
  `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_diagnostics_index.py`.
- Subagent review completed. Volta found no blocking findings and verified the
  queue/index/source-audit joins. Anscombe found one stale broadening wording
  issue in the control plane; it was rewritten as fail-closed approved-scope
  replay only.

## Remaining Work

- Commit this checkpoint, then start Goal 3 Peak-Choice Truth Set / Lockbox v1.

## Next Actions

1. Commit current Goal 0/1 + Goal 2 checkpoint.
2. Continue Goal 3 with a small independent lockbox/truth-label contract.
