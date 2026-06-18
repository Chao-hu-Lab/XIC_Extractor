# XIC productization handoff

Updated: 2026-06-18
Branch: `cc/framework-improvements`
Latest committed checkpoint: `caecd5d6 Add lockbox single-owner AI challenge gate`
Active checkpoint in working tree: `lockbox_shadow_automation_experiment_v1`

This is the short current-state snapshot. Tier authority lives in
`docs/superpowers/plans/2026-06-15-productization-control-plane.md` plus the
machine-readable validation indexes.

## Current Objective

Continue the low-manual productization path by turning lockbox review evidence
into auditable, read-only experiment assets. The current slice makes the
single-owner + AI-challenge closure executable as a shadow-only automation
experiment design, without creating ProductWriter, matrix, workbook, selected
peak/area, counted-detection, GUI, default-extraction, or broad Backfill
authority.

## What Changed This Round

- `AGENTS.md` has a small routing wording update from the side conversation:
  canonical references are routing targets, not a per-turn mandatory checklist.
- Added `scripts/build_lockbox_shadow_automation_experiment_design.py`.
- Added
  `docs/superpowers/validation/lockbox_shadow_automation_cases_v1.tsv` and
  `docs/superpowers/validation/lockbox_shadow_automation_experiment_v1.json`.
- Added `tests/test_lockbox_shadow_automation_experiment_design.py`.
- Read-only subagent reviewer `Averroes` found no blockers. Its P3 suggestion
  was adopted: `may_satisfy_reviewer_slot2=false` is now a machine-readable
  authority rule in the shadow experiment summary.
- Updated `productization_status_index_v1.tsv` so
  `peak_choice_truth_lockbox_v1` now points at
  `lockbox_shadow_automation_experiment_v1.json`.
- Updated `bounded_non_broad_lane_acceptance_v1.tsv` only to refresh the source
  status-index hash.
- Updated `lockbox_label_readme_v1.md` and this control-plane/handoff surface
  with the Gaussian15 review boundary policy.

Plain meaning: all 72 lockbox cases now have a shadow-experiment route. 53
owner-clean Gaussian15 cases plus 6 existing manual wrong-peak/no-peak controls
may be used in a shadow-only scoring experiment. 12 round-trip-oracle negative
rows and 1 Gaussian-boundary-unavailable row remain excluded from shadow
scoring. The output may only become shadow scores and review flags.

## Current Lane State

- `backfill_current_write_ready_scope`: `production_ready`, exactly 511 current
  Backfill writer-authority cells. This remains the only Backfill write
  authority.
- `broad_backfill_autowrite`: `parked`. The 4613 rows remain a candidate/audit
  universe, not writable cells.
- `peak_choice_truth_lockbox_v1`: `production_candidate`. Current artifact:
  `docs/superpowers/validation/lockbox_shadow_automation_experiment_v1.json`.
  It is a read-only shadow experiment design manifest, not truth completion or
  product authority.
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
  SampleMetadata output-affecting role/batch/matrix behavior, broader Targeted
  MS1 rescue, calibration/normalization writeback, GUI replay, and GUI parity
  remain parked, blocked, frozen, or out of scope.
- Quality explanation sidecars: keep only as explanation/triage.
- Targeted MS1 broader-target work: GUI and broader targets remain blocked.
- SampleMetadata role/value behavior: roles/batch/matrix/exclusion must not alter quant output.
- ReviewAction: ReviewAction selected-candidate switch and manual-boundary area recompute remain parked.
- Manual boundary writer: manual-boundary area recompute remain parked.
- Calibration/normalization activation: classification and planning only.
- GUI replay/parity: GUI and broader targets remain blocked.

## Active Boundary

- Gaussian15-smoothed boundaries are the review basis for lockbox cases.
- For raw-trace doublets, accept only when the Backfill/detect reference is on
  the left peak. If the reference is indistinguishable or on the right peak,
  keep the case flagged for review.
- Single-owner + AI challenge evidence can support shadow-only experiment
  design, but it cannot satisfy `reviewer_slot=2`, truth completion, or writer
  authority.
- Manual negative controls may challenge a shadow scorer; they cannot grant
  write authority.
- Round-trip-oracle negative rows remain nontruth evidence and excluded from
  shadow scoring.

## Validation Status

Already run for this slice:

- `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_lockbox_shadow_automation_experiment_design.py`
  built the design packet.
- `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/build_lockbox_shadow_automation_experiment_design.py --check-only`
  passed.
- `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_lockbox_shadow_automation_experiment_design.py -v --tb=short`
  passed `9`.
- `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check scripts/build_lockbox_shadow_automation_experiment_design.py tests/test_lockbox_shadow_automation_experiment_design.py`
  passed.
- `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_productization_state.py`
  passed.
- `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_bounded_product_lanes.py`
  passed.
- `$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/check_diagnostics_index.py`
  passed.
- `$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_productization_state_index.py tests/test_lockbox_shadow_automation_experiment_design.py -v --tb=short`
  passed `19`.

Read-only subagent review completed with no blockers. The only P3 suggestion
was to machine-record that this cannot satisfy reviewer slot 2; that fix is now
in the JSON summary and tests. Git lock/ref sanity found no `.lock` files.

Still required before commit: final `git diff --check`, scoped secret/local-path
scan confirmation, staging, and commit.

No RAW/85RAW rerun is planned for this slice because it is a read-only
artifact design over existing lockbox/static/AI-challenge evidence and does not
change extraction or product output behavior.

## Rejected Paths

- Do not unpark broad Backfill or derive writer predicates from this manifest.
- Do not treat ISTD, round-trip oracle, AI challenge output, or a single-owner
  label as independent analyte peak-choice or area truth.
- Do not prefill reviewer-slot-2 labels.
- Do not let shadow scores, manual negative controls, or challenge findings
  feed ProductWriter without a later authority manifest update, expected-diff,
  focused output tests, and an explicit product goal.

## Next Actions

1. Run the remaining focused productization checks and status-index tests.
2. Dispatch read-only subagent review for this shadow experiment design slice.
3. Fix any review findings, then commit the scoped diff including the side
   `AGENTS.md` wording update.
