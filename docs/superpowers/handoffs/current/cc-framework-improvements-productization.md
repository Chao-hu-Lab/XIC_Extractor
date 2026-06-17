# XIC productization handoff

Updated: 2026-06-18
Branch: `cc/framework-improvements`
HEAD before current authority/adjudication goal: `f00685ca`
Purpose: short current-state snapshot for the next agent/session. The control
plane remains the product tier authority.

## Current Objective

Implement **Productization Authority + Mechanical Adjudication Contract v1**:
freeze current write authority, classify every Backfill candidate mechanically,
and make unsupported rows review/evidence tasks instead of ProductWriter input.
Do not modify ProductWriter, matrix/workbook semantics, selected peak/area,
counted detection, default extraction, GUI, or broad Backfill behavior.

## Current State

- [parked] Broad Backfill auto-write is parked by
  `docs/superpowers/notes/backfill_broad_autowrite_feasibility_gate_v1.md`.
  The 4613 rows are the candidate/audit universe, not writable cells.
- [ready] Current Backfill product authority remains exactly 511
  generated-policy `write_ready` cells. The same replay has 0
  `detected_flagged`, 4102 `blocked`, and writer expected-diff 511/511 pass.
- [active] This round adds a fail-closed authority manifest and mechanical
  adjudication index:
  - 511 rows are `write_ready` with registered authority.
  - 3015 trace-matched unresolved rows are `evidence_required` for independent
    peak-choice/area truth.
  - 1087 missing-trace rows are `evidence_required` for trace/overlay or
    reintegration evidence.
  - all non-write rows have `write_authority=FALSE` and `may_touch_matrix=FALSE`.
- [active] `quality_explanations` and `quality_blockers` are explanation and
  triage inputs only. They cannot grant write authority or become writer
  predicates.
- [active] ISTD evidence is a limited reference anchor only. It does not prove
  analyte peak choice, analyte area truth, or broad Backfill safety.
- [ready] Targeted MS1 shape identity limited rescue is production-ready only
  for headless `5-hmdC + 5-medC` limited default writing `detected_flagged`.
  GUI and broader targets remain blocked.
- [ready] `sample_metadata_v1` is production-ready for no-output ordering and
  metadata projection only. Roles/QC/blank/batch/matrix/exclusion must not alter
  quant output without a separate expected-diff gate.
- [parked] ReviewAction selected-candidate switch and manual-boundary area
  recompute remain parked because they would change selected peak/area/counting.

## Files Changed This Round

- `docs/superpowers/notes/backfill_broad_autowrite_feasibility_gate_v1.md`:
  read-only decision packet outputting `park_broad_backfill`.
- `docs/superpowers/specs/productization_authority_manifest.v1.json`:
  fail-closed product authority manifest; only
  `backfill_policy_write_ready_rows` is currently allowed.
- `docs/superpowers/specs/mechanical_adjudication_schema.v1.json`:
  schema for machine decisions:
  `write_ready | review_ready | evidence_required | rejected | parked`.
- `docs/superpowers/validation/mechanical_adjudication_index_v1.tsv`:
  read-only index for the current 4613-row Backfill universe.
- `tests/test_productization_authority_mechanical_adjudication.py`:
  focused contract tests for parked/blocked/explanation-only/unregistered
  authority behavior.
- `docs/superpowers/plans/2026-06-15-productization-control-plane.md`:
  maintenance log and current tier wording for the parked broad Backfill and
  authority/adjudication contract.

## Active Decisions

- Authority is fail-closed: unregistered scopes cannot be consumed as product
  authority. The manifest, not a sidecar or blocker token, is the gate.
- `quality_blockers` may explain why a row is blocked or what evidence is
  missing, but they cannot activate writes.
- Negative evidence scopes remain blocked under any name: all-stability,
  apex-delta, width-only, shape-margin, and shape-clean reintegration-stable
  writer probe.
- Broad Backfill can reopen only with a new independent truth source or a later
  implementation goal using masked/product-writer oracle and expected-diff.
- RAW/85RAW was not rerun for this decision because existing no-RAW artifacts
  already answer the authority/adjudication question.
- Keep this handoff current-state oriented. Prune old `[done]` entries instead
  of appending phase history.

## Rejected Paths

- [blocked] Treat 4613 candidate/audit rows as approved writes.
- [blocked] Promote broad Backfill from `quality_blockers`, round-trip oracle,
  all-stability, apex-delta, width-only, shape-margin, or another nested writer
  slice.
- [blocked] Auto-write missing-overlay rows without recovered trace evidence.
- [blocked] Use ISTD as analyte peak-choice or area truth without independent
  proof.
- [blocked] Let sample roles/QC/blank/batch/matrix/exclusion change quant output
  without expected-diff approval.
- [parked] ReviewAction product writeback for selected-candidate or manual
  boundary area changes.

## Tests / Validation

- Current focused gate passed:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_productization_authority_mechanical_adjudication.py -v --tb=short`
  (`5 passed`).
- Current focused lint passed:
  `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tests/test_productization_authority_mechanical_adjudication.py`.
- Current full local gate passed:
  `ruff check xic_extractor tests`, `mypy xic_extractor`,
  `pytest -v --tb=short -x` (`3785 passed, 1 skipped`), and
  `scripts/check_diagnostics_index.py`.
- `git diff --check` passed with only Windows LF/CRLF warnings for Markdown
  files.
- Subagent review completed. Hume confirmed manifest/schema/index are
  fail-closed and no ProductWriter/matrix/workbook behavior changed. Mendel
  found stale broad-Backfill wording in the control plane; those current-summary
  and historical-log entries were rewritten as `parked` / superseded and routed
  to authority/adjudication, review, truth, or trace-evidence recovery.

## Remaining Work

- Next productization work should build structured review packets or a
  peak-choice truth/lockbox path, not broad Backfill writer revival.

## Next Actions

1. Validate the current authority/adjudication diff.
2. Commit after final validation if no blocking issue remains.
