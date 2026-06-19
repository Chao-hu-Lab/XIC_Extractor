# XIC productization handoff

Updated: 2026-06-20
Branch: `cc/framework-improvements`

This is a compact current-state snapshot. It is not product authority. Tier,
active lane, and promotion gate authority remain in
`docs/superpowers/plans/2026-06-15-productization-control-plane.md`.

## Current Verdict

The default numeric matrix remains usable as the current detected + 511
accepted-Backfill product output. ProductWriter default output is activated for
detected values plus the current accepted Backfill cells.

The CID-NL Discovery A owner-deepening focused slice is now implemented for the
successor CSV/parser contract: `discovery_candidates.csv` has additive
`discovery_candidate_state` and `ms1_feature_row_id` fields, and the alignment
reader fails closed on invalid state/identity combinations, including
`ms1_feature_row_id` sample/tag/precursor/RT mismatches.

The one-RAW successor oracle for `TumorBC2312_DNA` RT `22-25` now passes. A
recovers `300.1605 -> 184.113` and preserves `301.165 -> 185.116` as a distinct
`DNA_dR` tag-evidence row with its own `ms1_feature_row_id`.

This remains `diagnostic_only`. No ProductWriter/default matrix/workbook/GUI,
selected peak/area, counted detection, or Backfill writer authority changed.
The productization control plane was not updated because no maturity tier,
active lane, matrix schema, default activation bundle, or Backfill writer
authority changed.

## Product State

- Current tier: `product_ready_default_matrix_activated`.
- Product authority scope: `backfill_policy_write_ready_rows`.
- Current Backfill writer authority: exactly 511 accepted Backfill cells.
- Broad 4613-row Backfill remains parked.
- No default activation, 85RAW, workbook, GUI, ProductWriter, or Backfill
  authority run was launched in this slice.
- New Discovery successor fields are additive Discovery/alignment parser
  contract fields, not matrix-row authority.

## Status Index Anchors

These short anchors keep `scripts/check_productization_state.py` fail-closed
without making this handoff the tier authority:

- `product_ready_default_matrix_activated`
- Broad Backfill auto-write remains parked
- Goal 0/1 hardening added
- machine-adjudicated without granting new writer authority
- Goal 2 added Review Packet / Approval Workflow v1
- lockbox_shadow_automation_experiment_v1
- Goal 4 added Missing-Overlay Evidence Recovery v1
- keep only as explanation/triage
- Targeted MS1 shape identity limited rescue remains production-ready
- GUI and broader targets remain blocked
- `sample_metadata_v1` remains production-ready for no-output ordering
- roles/batch/matrix/exclusion must not alter quant output
- ReviewAction selected-candidate switch and manual-boundary area recompute remain parked
- manual-boundary area recompute remain parked
- classification and planning only

## Current CID-NL Decision

Decision Spike v1 still stands:

- Do not build the B feature-primary temporary adapter yet.
- Keep the completed A owner-deepening pass in existing Discovery owners.
- B remains closed because the one-RAW oracle shows no material advantage for a
  second Discovery system.

8RAW was not run because focused tests plus the one-RAW oracle answered the
architecture decision. 85RAW and default activation remain out of scope.

## Files Changed In Current Slice

- `xic_extractor/discovery/models.py`
- `xic_extractor/discovery/ms1_backfill.py`
- `xic_extractor/alignment/csv_io.py`
- `tests/test_discovery_csv.py`
- `tests/test_alignment_csv_io.py`
- `tests/test_discovery_architecture_ab_artifact.py`
- `tests/alignment_pipeline_helpers.py`
- `tests/test_shared_peak_identity_candidate_ms2_pattern.py`

## Active Decisions

- `discovery.models` owns `discovery_candidate_state` vocabulary and
  `ms1_feature_row_id` construction.
- `DiscoveryCandidate.from_values` assigns:
  - `scan_precursor` + MS1 peak: `ms1_feature_nl_supported`;
  - `product_plus_neutral_loss` or `mixed` + MS1 peak:
    `ms1_feature_nl_rescued`;
  - no MS1 peak: `review_only_orphan_nl` with blank `ms1_feature_row_id`.
- `ms1_feature_row_id` is sample/tag/precursor/RT-feature based and does not use
  representative MS2 scan id.
- `alignment.csv_io` rejects invalid state enums, blank normal/rescued
  `ms1_feature_row_id`, normal/rescued rows without MS1 peak,
  orphan rows with MS1 peak or nonblank id, and duplicate normal/rescued
  `ms1_feature_row_id` in the same sample/tag scope.
- `alignment.csv_io` also validates that nonblank `ms1_feature_row_id` matches
  the candidate row's sample, neutral-loss tag, precursor identity, and MS1
  feature RT within parser tolerance.
- `alignment.csv_io` still reads legacy candidate CSVs that predate the two
  additive successor columns; the successor checker remains the authority for
  requiring those fields in new A/B evidence.
- CSV writer remains render-only.

## Boundaries

- Do not maintain two Discovery systems.
- Do not make CID-NL/MS2 evidence direct ProductWriter authority.
- Do not change default matrix/ProductWriter/workbook/GUI/Backfill authority.
- Do not run default activation in this CID-NL owner-deepening slice.
- Do not run 85RAW unless a later product decision explicitly requires it.
- Do not treat candidates as matrix rows.
- Do not demote or delete `301.165 -> 185.116` when it carries its own tag
  evidence.
- Do not hide any B temporary adapter behind `scripts/run_discovery.py`
  CLI/config flags.

## Latest Local Checks

- `python -m pytest tests/test_discovery_csv.py tests/test_alignment_csv_io.py tests/test_discovery_architecture_ab_artifact.py tests/test_discovery_ms1_backfill.py tests/test_discovery_precursor_inference_artifact.py -q`
  passed: `92 passed`.
- `$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor/discovery/models.py xic_extractor/discovery/ms1_backfill.py xic_extractor/alignment/csv_io.py tests/test_discovery_csv.py tests/test_alignment_csv_io.py tests/test_discovery_architecture_ab_artifact.py tests/alignment_pipeline_helpers.py tests/test_shared_peak_identity_candidate_ms2_pattern.py`
  passed.
- `python scripts/check_productization_state.py` passed.
- One-RAW discovery rerun succeeded for `TumorBC2312_DNA` RT `22-25`.
- Legacy precursor checker passed with 157 rows and SHA256
  `5267A602D520FAE4F3B11E2CDB99525849D7FD2C01F33ACC37F6D4548194114D`.
- Successor architecture checker passed with `diagnostic_only` readiness label.
- One-RAW state counts: 46 `ms1_feature_nl_rescued`, 5
  `ms1_feature_nl_supported`, 106 `review_only_orphan_nl`.

## Next Actions

1. Finish subagent review and commit the task-scoped code/tests/docs.
2. Keep default matrix activation separate; only open that expected-diff task
   when the public default `quant_matrix.tsv` should materialize the
   `300.1605 -> 184.113` row.
3. Reopen B only with new evidence that materially beats A on the one-RAW
   oracle and names a deletion/facade endpoint; do not hide B behind
   `scripts/run_discovery.py` flags.
