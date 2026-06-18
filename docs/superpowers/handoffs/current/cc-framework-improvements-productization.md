# XIC productization handoff

Updated: 2026-06-18
Branch: `cc/framework-improvements`
Latest committed checkpoint: `e7e1dfbb Add lockbox AI challenge packet`
Active checkpoint: `lockbox_ai_challenge_result_v1` is in the working tree.

This is the current-state snapshot only. Tier authority lives in
`docs/superpowers/plans/2026-06-15-productization-control-plane.md` plus the
machine-readable validation indexes.

## Current Objective

Continue the low-manual productization path by making every candidate
reviewable and auditable, without turning labels, diagnostics, quality blockers,
ISTD, round-trip oracle evidence, or AI/subagent challenge output into
ProductWriter authority.

Current focus: finish the non-authoritative AI challenge result checkpoint. The
72 lockbox cases have now been challenged by three read-only subagent chunks
plus one main-agent visual chunk. The result is not truth labeling, not
reviewer slot 2, and not writer input.

## What Changed This Round

- Added `scripts/build_lockbox_ai_challenge_pack.py` with `--check-only`.
- Added `tests/test_lockbox_ai_challenge_pack.py`.
- Generated:
  - `docs/superpowers/validation/lockbox_ai_challenge_queue_v1.tsv`
  - `docs/superpowers/validation/lockbox_ai_challenge_template_v1.tsv`
  - `docs/superpowers/validation/lockbox_ai_challenge_summary_v1.json`
  - `docs/superpowers/validation/lockbox_ai_challenge_v1/index.html`
- Updated `productization_status_index_v1.tsv` so
  `peak_choice_truth_lockbox_v1` points to the AI challenge summary.
- Updated `bounded_non_broad_lane_acceptance_v1.tsv` only to refresh the source
  status-index hash.
- Updated `lockbox_label_readme_v1.md` and the control-plane maintenance log.
- Subagent review found two bounded issues and both are fixed:
  non-visual route/evidence rows no longer allow
  `visual_contradiction_suspected`, and `--check-only` now has stale
  `index.html` plus stale summary-authority regression tests.
- Ran the AI challenge result pass:
  - 72 result rows written to
    `docs/superpowers/validation/lockbox_ai_challenge_result_log_v1.tsv`.
  - Summary written to
    `docs/superpowers/validation/lockbox_ai_challenge_result_summary_v1.json`.
  - Outcome: 71 `no_issue`; 1 `visual_contradiction_suspected`.
  - Flagged case: `LOCKBOXV1_60CEB35837FAF38CC4DE9021`.

## Current Lane State

- Current Backfill product authority remains exactly 511.
- Broad Backfill auto-write remains parked.
- Goal 0/1 hardening added.
- Goal 2 added Review Packet / Approval Workflow v1.
- Goal 4 added Missing-Overlay Evidence Recovery v1.
- AI challenge packet for 72 lockbox cases.
- keep only as explanation/triage.
- Targeted MS1 shape identity limited rescue remains production-ready.
- GUI and broader targets remain blocked.
- `sample_metadata_v1` remains production-ready for no-output ordering.
- roles/batch/matrix/exclusion must not alter quant output.
- ReviewAction selected-candidate switch and manual-boundary area recompute remain parked.
- manual-boundary area recompute remain parked.
- classification and planning only.

- `backfill_current_write_ready_scope`: `production_ready`, exactly 511
  generated-policy `write_ready` cells. This remains the only Backfill writer
  authority.
- `broad_backfill_autowrite`: `parked`. The 4613 rows are a candidate/audit
  universe, not writable cells.
- `peak_choice_truth_lockbox_v1`: `production_candidate`.
  Current artifact:
  `docs/superpowers/validation/lockbox_ai_challenge_result_summary_v1.json`.
  AI challenge result for 72 lockbox cases. It reports 71 `no_issue` rows and
  1 owner re-review flag:
  `LOCKBOXV1_60CEB35837FAF38CC4DE9021`. AI findings cannot satisfy reviewer
  slot 2, cannot become truth labels, and cannot grant product authority.
- `review_packet_workflow_v1`, `missing_overlay_evidence_recovery_v1`,
  `productization_authority_firewall_v1`, `mechanical_adjudication_contract_v1`,
  `productization_status_index_v1`, and
  `bounded_non_broad_lane_acceptance_v1`: `production_candidate` guardrails or
  review/evidence assets only.
- `targeted_ms1_shape_identity_limited_rescue_v1`: `production_ready` only for
  the explicit headless 5-hmdC + 5-medC workflow writing `detected_flagged`.
- `sample_metadata_order_projection_v1`: `production_ready` for no-output
  ordering/projection only.
- ReviewAction selected-candidate switch, manual-boundary area writer,
  SampleMetadata output-affecting roles/batch/matrix behavior, broader targeted
  MS1 rescue, calibration/normalization writeback, GUI replay, and GUI parity
  remain parked, blocked, frozen, or out of scope.

## AI Challenge Contract

- Inputs: `lockbox_next_action_plan_v1.tsv`,
  `lockbox_static_review_v1/bundle_index.tsv`,
  `lockbox_reviewer_label_log_v1.tsv`, and
  `lockbox_owner_boundary_confirmation_v1.json`.
- Included rows: all 72 lockbox cases.
- Scope split: 53 `visual_contradiction_challenge` rows for plotted Gaussian15
  cases; 19 route/evidence integrity rows for parked negatives, manual
  negatives, and the boundary-unavailable case.
- Template semantics: one blank AI challenge row per case. No challenge result,
  truth label, reviewer-slot-2 label, or replacement value is prefilled.
- Output rule: AI findings can only flag owner re-review, artifact repair, or
  route mismatch. Only the 53 visual rows may report
  `visual_contradiction_suspected`; the 19 route/evidence rows may not.
- Authority: all ProductWriter/matrix/workbook/selected peak/selected
  area/counted detection/default extraction/GUI/broad Backfill flags remain
  false.

## AI Challenge Result

- Result log:
  `docs/superpowers/validation/lockbox_ai_challenge_result_log_v1.tsv`.
- Summary:
  `docs/superpowers/validation/lockbox_ai_challenge_result_summary_v1.json`.
- Decision: `ai_challenge_owner_recheck_required`.
- Meaning in plain language: the AI/subagent challenge did not find an obvious
  issue in 71 cases. It flagged one case for owner re-review only:
  `LOCKBOXV1_60CEB35837FAF38CC4DE9021`, with note `Boundary cuts off right
  lobe/competing raw peak.`
- This is still a review-routing artifact. It does not alter labels, matrix
  values, selected peak, selected area, counted detection, workbook output, GUI,
  default extraction, broad Backfill, or ProductWriter authority.

## Single-Developer Boundary

The owner/user is the only current domain truth source. Subagents may perform
artifact integrity review, implementation review, link/hash checks, and visual
contradiction challenge. They must not be recorded as human truth reviewers.
`scripts/check_lockbox_label_schema.py` and `scripts/import_lockbox_labels.py`
enforce the explicit human reviewer registry and valid slot 1/2 semantics.

## Validation So Far

Passed this round:

- `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_lockbox_ai_challenge_pack.py`
- `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_lockbox_ai_challenge_pack.py --check-only`
- `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_lockbox_ai_challenge_pack.py -v --tb=short`
  (`12 passed`)
- `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts/build_lockbox_ai_challenge_pack.py tests/test_lockbox_ai_challenge_pack.py`
- `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_productization_state.py`
- `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_bounded_product_lanes.py`
- `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_productization_state_index.py tests/test_lockbox_ai_challenge_pack.py -v --tb=short`
  (`20 passed`)
- `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts/build_lockbox_ai_challenge_pack.py tests/test_lockbox_ai_challenge_pack.py tests/test_productization_state_index.py`
- Subagent review rechecked the packet boundary. Findings were fixed locally:
  visual contradiction outputs are scope-limited, and stale HTML/summary checks
  now have focused regression coverage.
- `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_lockbox_ai_challenge_results.py`
  built the result summary: 72 cases, 1 flagged.
- `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_lockbox_ai_challenge_results.py --check-only`
  returned `Lockbox AI challenge results are valid and non-authoritative.`
- `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_lockbox_ai_challenge_results.py -v --tb=short`
  (`5 passed`)
- `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts/check_lockbox_ai_challenge_results.py tests/test_lockbox_ai_challenge_results.py`

Broader previous local gate remains from committed checkpoint:
`ruff`, `mypy`, `pytest -v --tb=short -x` (`3884 passed, 1 skipped`),
diagnostics index, productization authority, productization state, bounded
lanes, and second-review `--check-only`.

## Rejected Paths

- Do not unpark broad Backfill or derive new writer rules from the 19 non-ready
  lockbox cases.
- Do not treat ISTD, round-trip oracle, or AI challenge output as analyte
  peak-choice or area truth.
- Do not prefill reviewer-slot-2 labels.
- Do not let completed labels or challenge findings feed ProductWriter without
  a later authority manifest, expected-diff, and product goal.
- Do not run 85RAW for this checkpoint; this is artifact/review-surface work.

## Next Actions

1. Build or open a tiny owner re-review packet for
   `LOCKBOXV1_60CEB35837FAF38CC4DE9021`.
2. Commit this checkpoint without
   staging unrelated `AGENTS.md`, `.github/`, `CONTEXT.md`, or
   `docs/engineering-skills/` changes.
3. After owner resolves the single flagged case, rerun the challenge-result
   checker and update the summary. Do not convert this result into writer
   authority.
