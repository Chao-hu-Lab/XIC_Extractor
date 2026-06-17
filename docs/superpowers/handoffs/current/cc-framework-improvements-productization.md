# XIC productization handoff

Updated: 2026-06-18
Branch: `cc/framework-improvements`
HEAD before current six-goal sequence: `87c51c05`
Current HEAD before Goal 4 checkpoint: `eb5286f5`
Purpose: short current-state snapshot for the next agent/session. The control
plane remains the product tier authority.

## Current Objective

Execute the low-manual productization sequence toward mechanically adjudicated,
reviewable, non-black-box decisions. Goal 0/1 authority firewall, Goal 2 review
packets, and Goal 3 truth lockbox are committed. Goal 4 missing-overlay
evidence recovery is the active checkpoint; it recovers evidence links only and
does not create writer authority.

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
- [active] Goal 3 added Peak-Choice Truth Set / Lockbox v1:
  - 72 deterministic cases cover approved 511 controls, 3015 unresolved review
    rows, 1087 missing-overlay evidence gaps, failed heldout-oracle negatives,
    and manual wrong-peak/no-peak fixtures.
  - Each case is split by `family_id`, requires two independent reviewers, and
    separates peak-choice labels from area labels.
  - Missing-overlay evidence-gap cases are not forced into fake area labels:
    `area_label_required=FALSE`, with `not_assessed/unavailable` allowed.
  - No labels have been collected yet; agreement metrics are intentionally
    `null`.
  - Lockbox labels cannot write matrix values or grant ProductWriter authority.
- [active] Goal 4 added Missing-Overlay Evidence Recovery v1:
  - All 1087 source `missing_overlay_path` rows are linked to existing
    family-level trace JSON, overlay PNG, hypothesis PNG, and sample-level trace
    fields from 114 families.
  - The report changes their evidence state only to
    `C_trace_recovered` / `evidence_required`.
  - It does not create review approval, ProductWriter authority, matrix writes,
    selected peak/area changes, or counted-detection changes.
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
- `scripts/build_peak_choice_truth_lockbox.py`: deterministic lockbox generator.
- `docs/superpowers/specs/peak_choice_truth_protocol.v1.md`: lockbox protocol.
- `docs/superpowers/specs/truth_label_schema.v1.json`: truth-label schema.
- `docs/superpowers/validation/lockbox_sampling_manifest_v1.tsv`: 72-case
  lockbox sampling manifest.
- `docs/superpowers/validation/reviewer_label_log_v1.tsv`: empty structured
  label log.
- `docs/superpowers/validation/inter_reviewer_agreement_summary_v1.json`: empty
  agreement summary.
- `tests/test_peak_choice_truth_lockbox_contract.py`: lockbox contract tests.
- `scripts/build_trace_overlay_recovery_report.py`: deterministic recovery
  report generator for the 1087 missing-overlay rows.
- `docs/superpowers/specs/trace_overlay_recovery_contract.v1.json`: recovery
  report schema and authority boundary.
- `docs/superpowers/validation/trace_overlay_recovery_report_v1.tsv`: 1087-row
  recovery report.
- `docs/superpowers/validation/missing_overlay_resolution_summary_v1.json`:
  recovery summary.
- `tests/test_trace_overlay_recovery_contract.py`: recovery report contract
  tests.
- `docs/superpowers/plans/2026-06-15-productization-control-plane.md`: tier and
  maintenance-log updates for this checkpoint.

## Active Decisions

- Authority remains fail-closed: only manifest-registered authority can ever
  write, and current authority is still 511 cells.
- Review Packet approval is not ProductWriter approval. It records structured
  human judgment only.
- 3015 rows are review candidates, not auto-write candidates.
- 1087 missing-overlay rows now have recovered trace/overlay evidence links, but
  still require review/truth/reintegration decisions before any product claim.
- Broad Backfill can reopen only with a new independent truth source and a later
  expected-diff authority update.
- RAW/85RAW is not needed for this checkpoint because the artifacts are
  contract/index transforms over existing no-RAW evidence.
- Lockbox review output is truth evidence only. It must not be consumed by
  ProductWriter without a later authority manifest and expected-diff goal.

## Rejected Paths

- [blocked] Treat 4613 candidate/audit rows as approved writes.
- [blocked] Promote broad Backfill from `quality_blockers`, round-trip oracle,
  all-stability, apex-delta, width-only, shape-margin, or another nested writer
  slice.
- [blocked] Use review approval as write authority.
- [blocked] Allow reviewers to free-form fill values.
- [blocked] Auto-write missing-overlay rows because trace evidence was
  recovered.
- [blocked] Use ISTD as analyte peak-choice or area truth without independent
  proof.
- [blocked] Treat lockbox sampling membership or future reviewer labels as
  automatic write authority.

## Tests / Validation

- Focused checkpoint tests passed:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_review_packet_contract.py tests/test_check_productization_authority.py tests/test_productization_authority_mechanical_adjudication.py -v --tb=short`
  (`12 passed`).
- Focused lint passed:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts/check_productization_authority.py tests/test_review_packet_contract.py tests/test_check_productization_authority.py tests/test_productization_authority_mechanical_adjudication.py`.
- Checker passed:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_productization_authority.py`.
- JSON parse passed for `review_packet_schema.v1.json`.
- Goal 3 focused tests passed:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_peak_choice_truth_lockbox_contract.py -v --tb=short`
  (`6 passed`).
- Goal 3 focused lint passed:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts/build_peak_choice_truth_lockbox.py tests/test_peak_choice_truth_lockbox_contract.py`.
- JSON parse passed for `truth_label_schema.v1.json` and
  `inter_reviewer_agreement_summary_v1.json`.
- Subagent Goal 3 review completed. Lovelace found no docs/control-plane
  issues. Pauli found a P2 gap where missing-overlay rows were forced to area
  labels; fixed by adding `not_assessed/unavailable` and setting
  `area_label_required=FALSE` for missing-overlay cases, then rerunning focused
  tests/lint.
- Goal 4 focused tests passed:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_trace_overlay_recovery_contract.py -v --tb=short`
  (`5 passed`).
- Goal 4 focused lint passed:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts/build_trace_overlay_recovery_report.py tests/test_trace_overlay_recovery_contract.py`.
- JSON parse passed for `trace_overlay_recovery_contract.v1.json` and
  `missing_overlay_resolution_summary_v1.json`.
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

- Goal 4 needs subagent review, any fixes, final gate, and commit.
- Next implementation goal after that: Goal 5 productization control-plane
  cleanup.

## Next Actions

1. Subagent review Goal 4 recovery contract.
2. Fix review findings and run final gate.
3. Commit, then continue Goal 5 control-plane cleanup.
