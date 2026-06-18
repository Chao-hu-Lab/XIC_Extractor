# Backfill Evidence Gate Productization Implementation Plan

> Historical product-candidate slice as of 2026-06-18. Keep for provenance and
> validation context. Do not use this plan to reopen broad Backfill or derive a
> new writer slice; current Backfill authority and next work live in the
> productization control plane and evidence lifecycle blueprint.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Backfill may still enumerate and render review candidates, but high-risk rescue promotion must stop depending on scan support or owner-backfill labels alone. A rescued cell can support matrix promotion only when typed evidence explains RT, MS1 pattern/QC, and chemical/MS2 context.

**Architecture:** Keep owner backfill candidate generation unchanged for this slice. Add a typed `backfill_*` evidence projection on `AlignedCell`, carry it through `alignment_cells.tsv`, and make `promotion_policy` fail closed when high/weak dependency rescue cells lack independent evidence. Existing shared-peak sidecars can later populate this projection without becoming direct writers.

**Tech Stack:** Python dataclasses, existing alignment decision modules, pytest.

---

## Acceptance Criteria

- [x] Scan-support-only rescued cells no longer support `extreme_backfill_dependency` or `weak_seed_backfill_dependency` promotion.
- [x] Owner-backfill trace labels alone do not support promotion.
- [x] RT support is close RT or drift-corrected compatible RT, not broad `max_rt_sec` membership alone.
- [x] MS1 support comes from machine-observed sample pattern or QC pattern reference, not generic scan count.
- [x] Chemical support comes from candidate-aligned MS2/NL evidence or explicit non-dispositive DDA context; missing NL is not treated as negative by default.
- [x] `alignment_cells.tsv` exposes the backfill evidence projection so diagnostic TSV adapters and product decisions share the same facts.
- [x] Unsupported rescued cells are withheld per-cell without blanking otherwise valid detected seed cells from the same family row.
- [x] No-RAW focused tests pass for matrix identity, production decisions, and single-DR gate parity.

## Validation Framing

- This slice can close whether legacy scan-support-only high-risk backfill is retired from product authority.
- Strongest cheap oracle: no-RAW unit/adapter parity tests plus existing 8RAW selected/manual review artifacts.
- Missing independent evidence: full row-level EIC/MS2 or targeted benchmark adjudication for all changed 8RAW rows.
- Stop condition: if no-RAW parity cannot be made coherent, do not run RAW; fix product contract first.
- Readiness ceiling after no-RAW + 8RAW: `production_candidate`. `production_ready` requires changed-row bundle adjudication.

## Tasks

- [x] Add typed backfill evidence projection fields to `AlignedCell` and TSV output.
- [x] Update `promotion_policy` to require independent RT + MS1 pattern/QC + chemical/MS2 context for high-risk rescue promotion.
- [x] Split row admission from rescue-cell admission: unsupported rescued cells are review-only while detected seed cells remain writable when row identity is otherwise retained.
- [x] Retarget old scan-support promotion tests to fail-closed cell behavior and add explicit supported-evidence cases.
- [x] Update diagnostic TSV adapter fixtures to include the same typed projection.
- [x] Make the single-DR TSV adapter fail closed on stale/missing backfill projection columns and read `primary_matrix_area` before legacy `area`.
- [x] Run focused no-RAW tests.
- [x] Populate `backfill_*` projection from shared-peak machine evidence sidecars in the shared-peak activation product path.
- [x] Reassert matrix identity layering: downstream `alignment_matrix.tsv` remains `Mz` / `RT` / sample columns; `peak_hypothesis_id` is an internal product identity sidecar; `feature_family_id` is provenance/debug only and must not become downstream row identity.

## Current Status 2026-06-05

- Product behavior changed: high-risk unsupported rescue no longer promotes a rescued value into the matrix, but it also no longer deletes detected seed values from an otherwise retained row.
- Diagnostic adapter behavior changed: stale `alignment_cells.tsv` files that lack `backfill_*` projection columns now fail closed instead of producing a misleading gate report.
- Activation product behavior changed: `apply_shared_peak_identity_activation.py` can now ingest typed `candidate_ms2_pattern`, `ms1_pattern_coherence`, `qc_ms1_pattern_reference`, and `matrix_rt_drift_policy` sidecars and project them onto rescued cells as `backfill_*` fields. The projection is fail-closed: without sidecars or existing projection columns, activation does not invent evidence.
- Output contract corrected: formal activation writes downstream `alignment_matrix.tsv` as `Mz` / `RT` / sample columns and writes `peak_hypothesis_id` rows to `activation_hypothesis_identity.tsv`. `feature_family_id` is not a final matrix identity because family-level grouping can merge distinct MS1 peaks.
- No-RAW verification passed:
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_shared_peak_identity_product_activation.py tests/test_untargeted_final_matrix_contract.py` -> 21 passed.
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_backfill_evidence_projection.py tests/test_shared_peak_identity_product_activation.py` -> 21 passed.
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_backfill_evidence_projection.py tests/test_shared_peak_identity_product_activation.py tests/test_shared_peak_identity_mode_hypothesis_assignment.py tests/test_shared_peak_identity_mode_hypothesis_assignment_cli.py tests/test_shared_peak_identity_hypothesis_consistency.py tests/test_shared_peak_identity_peak_hypothesis_selection.py tests/test_shared_peak_identity_peak_hypothesis_matrix.py tests/test_shared_peak_identity_mode_window_assignment_gate.py tests/test_alignment_matrix_identity.py tests/test_alignment_production_decisions.py tests/test_single_dr_production_gate_decision_report.py tests/test_alignment_tsv_writer.py tests/test_alignment_xlsx_writer.py tests/test_alignment_owner_backfill.py tests/test_alignment_owner_matrix.py tests/test_untargeted_final_matrix_contract.py tests/test_production_candidate_gate.py` -> 237 passed.
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests tools/diagnostics/apply_shared_peak_identity_activation.py` -> passed.
  - `$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor` -> passed.
- Readiness label for the product-path slice is now `production_candidate` after
  the 8RAW activation/gate rerun used the final `Mz` / `RT` / sample matrix
  contract plus hypothesis sidecar and produced a changed-row bundle.
  `production_ready` still requires changed-row EIC/MS2 or targeted benchmark
  adjudication.

## 8RAW Follow-Up Boundary, 2026-06-05

The first 8RAW projection proved that typed `backfill_*` sidecars can be
generated and that the single-dR gate can classify risky rescue-heavy rows, but
the run also exposed a contract mismatch: the formal activation bridge expected
a `feature_family_id` matrix, while the real downstream matrix is `Mz` / `RT` /
sample columns with `alignment_matrix_identity.tsv` as the row-identity sidecar.

Decision: do not promote a FamilyID matrix path. The next product step is to let
activation/gate consumers read the public `Mz` / `RT` matrix through the
existing identity sidecar, apply decisions at `peak_hypothesis_id` level, and
leave `feature_family_id` as provenance only.

## 8RAW Product-Path Result, 2026-06-05

- Formal no-op activation with the public matrix contract wrote
  `output/backfill_evidence_gate_8raw_20260605/formal_activation_mzrt_contract/`.
  Summary: `input_matrix_rows=326`, `output_matrix_rows=326`,
  `matrix_row_identity=mz_rt_sample_columns`,
  `canonical_row_identity_ready=TRUE`, and
  `canonical_row_identity_blockers=none`.
- The single-dR gate over that output wrote
  `output/backfill_evidence_gate_8raw_20260605/single_dr_gate_mzrt_contract/`.
  It emitted 39 `auto_block` activation decisions and 39 changed-row bundle rows
  for `dr_backfill_policy_blocked`; all bundle rows remain
  `reviewer_verdict=pending_manual_review`.
- Applying those decisions wrote
  `output/backfill_evidence_gate_8raw_20260605/formal_activation_mzrt_contract_gate_applied/`.
  The formal downstream matrix stayed `Mz` / `RT` / sample columns and changed
  from 326 rows to 287 rows, with `families_removed_from_matrix=39`.
- A second gate pass over the gate-applied matrix wrote
  `output/backfill_evidence_gate_8raw_20260605/single_dr_gate_mzrt_contract_after_apply/`.
  `single_dr_gate_activation_decisions.tsv` has 0 rows, so there are no pending
  product-affecting activation decisions for this 8RAW slice. Remaining
  `keep_warning` signals stay review/monitoring evidence.
- Manual review plots for all 39 changed rows were generated under
  `output/backfill_evidence_gate_8raw_20260605/changed_row_ms1_overlay_review_20260605/`.
  The gallery entry point is `review_gallery.html`; all 39 RAW-backed overlays
  succeeded. Verdict counts: 19 `ms1_shape_supports_family_backfill`, 18
  `review_required_neighboring_ms1_interference`, 1
  `review_required_low_ms1_assessable_coverage`, and 1
  `review_required_uncertain_ms1_shape`.
- A follow-up mode-aware review surface was generated from those same trace
  JSONs without re-reading RAW under
  `output/backfill_evidence_gate_8raw_20260605/changed_row_mode_overlay_review_20260605/`.
  The entry point is `mode_aware_review_gallery.html`. It writes
  `changed_row_rt_mode_evidence.tsv`,
  `changed_row_peak_hypothesis_selection.tsv`,
  `changed_row_mode_sample_review.tsv`, and
  `changed_row_mode_overlay_summary.tsv`. Its mode-colored MS1 plots display
  Gaussian15-smoothed traces while preserving selected-cell and global-trace
  apex markers. This surface treats
  `feature_family_id` as provenance and exposes `peak_hypothesis_id`,
  selected-apex raw mode, global trace-apex mode, and active identity status.
  All 39 changed rows are `removed_by_active_gate`; 15 are
  `review_required_raw_multimodal_family`, 17 are
  `single_mode_supported_raw_review_only`, and 7 are
  `review_required_raw_mode`. RAW-overlay-derived mode evidence remains
  review-only, not typed iRT or product authority.
- The same mode-aware review run now also writes a review-only quick-similarity
  panel: `changed_row_similarity_review.tsv` and
  `changed_row_similarity_summary.tsv`. It combines Gaussian15-smoothed
  selected-mode shape similarity, selected-vs-global apex conflict,
  `matrix_rt_drift_policy` status, and optional MS1 pattern coherence sidecar
  facts into human triage badges. In the regenerated 8RAW artifact, the 312
  sample-level review rows are distributed as: 136
  `shape_coherent_review_only`, 70 `review_required_wrong_apex_risk`, 46
  `review_required_multimodal_family`, 34
  `review_required_partial_similarity`, 18
  `review_required_inconclusive_similarity`, and 8
  `review_required_shape_conflict`. These badges are diagnostic triage aids
  only; they do not change activation, backfill presence, or matrix area.
- Targeted ISTD benchmark was run against both no-op formal activation and the
  gate-applied formal activation:
  `targeted_istd_benchmark_formal_noop/` and
  `targeted_istd_benchmark_gate_applied/`. Their summary and matches TSVs are
  identical. The strict benchmark still exits with 3 known `AREA_MISMATCH`
  failures (`d3-5-hmdC`, `d3-5-medC`, `d3-N6-medA`), but the 39 row removals do
  not introduce targeted ISTD MISS/DRIFT or match regression.

Current verdict: `production_candidate`. The product path is wired end to end,
the public matrix contract is preserved, and unsupported high-risk backfill is
removed from product output. It is not `production_ready` because the 39
changed-row bundle entries still need manual EIC/MS2 review or targeted
benchmark adjudication.
