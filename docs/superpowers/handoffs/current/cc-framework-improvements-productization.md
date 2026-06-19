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

Discovery/alignment evidence recovered the missing `300.1605 -> 184.113`
feature in diagnostic validation, but the already activated default matrix
bundle still predates that rerun. Do not claim the tracked default activation
bundle contains that row until a separate default activation expected-diff rerun
regenerates and locks the public surface.

Current follow-up is CID-NL Discovery architecture owner-deepening, not another
default matrix activation.

## Product State

- Current tier: `product_ready_default_matrix_activated`.
- Product authority scope: `backfill_policy_write_ready_rows`.
- Current Backfill writer authority: exactly 511 accepted Backfill cells.
- Broad 4613-row Backfill remains parked.
- No scorer was run for the CID-NL decision spike.
- No ProductWriter/default activation rerun was launched.
- No workbook, GUI, selected peak/area, counted detection, or Backfill authority
  changed.
- New Discovery/alignment and A/B checker evidence remains `diagnostic_only`.
- No control-plane maturity tier, active lane, matrix schema, or Backfill writer
  authority changed in the docs/addendum work.

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

## Canonical References

- Tier / active lane / promotion gate:
  `docs/superpowers/plans/2026-06-15-productization-control-plane.md`
- Next execution contract:
  `docs/superpowers/plans/LC-MS CID Neutral Loss Discovery plan.md`
- A/B decision record:
  `docs/superpowers/plans/LC-MS CID Neutral Loss Discovery Architecture Alternatives Brief.md`
- Deep research input:
  `docs/deepresearch/LC-MS CID Neutral Loss Discovery.md`
- Discovery parser contract:
  `xic_extractor/alignment/csv_io.py`
- Discovery CSV writer contract:
  `xic_extractor/discovery/csv_writer.py`
- Successor A/B checker:
  `scripts/check_discovery_architecture_ab_artifact.py`
- Current one-RAW A baseline:
  `output/discovery_architecture_ab/a_incremental/one_raw_tumorbc2312/`
- Archived completed evidence summary:
  `docs/superpowers/handoffs/archive/2026-06-20_cc-framework-improvements_cid-nl-decision-spike-v1_21dcca68.md`

## Current CID-NL Decision

Decision Spike v1 result:

- Do not build the B feature-primary temporary adapter yet.
- Proceed with one bounded A owner-deepening pass in existing Discovery owners.
- Add explicit `discovery_candidate_state` and `ms1_feature_row_id`.
- Require writer/reader/parser tests, including fail-closed parser coverage for
  invalid state + row-identity combinations.
- Rerun the one-RAW successor checker on `TumorBC2312_DNA` RT `22-25`.

A is the next implementation path because current one-RAW evidence already
recovers `300.1605 -> 184.113` and preserves `301.165 -> 185.116`; this is not
a claim that the old A design was clean. The next pass absorbs B's useful
feature-first/evidence-late concepts into A.

B can reopen only through the gates in the plan addendum: material one-RAW gain
after A passes, or a documented A structural blocker. A does not get an
unbounded cleanup loop.

## Boundaries

- Do not maintain two Discovery systems.
- Do not make CID-NL/MS2 evidence direct ProductWriter authority.
- Do not change default matrix/ProductWriter/workbook/GUI/Backfill authority.
- Do not run default activation in the CID-NL owner-deepening slice.
- Do not run 85RAW unless a later product decision explicitly requires it.
- Do not treat candidates as matrix rows.
- Do not demote or delete `301.165 -> 185.116` when it carries its own tag
  evidence.
- Do not hide any B temporary adapter behind `scripts/run_discovery.py`
  CLI/config flags.

## Evidence Snapshot

- One-RAW A baseline output:
  `output/discovery_architecture_ab/a_incremental/one_raw_tumorbc2312/`
- Legacy precursor-inference checker passed that output with 157 rows and
  SHA256 `E69C53CE5F054C3D6385A2A66BD1B85B9D0F567F91BBC7F5A78BAC7D73953C44`.
- Successor checker intentionally failed the current A CSV because it lacks
  `discovery_candidate_state` and `ms1_feature_row_id`; parser compatibility
  for current CSV was `pass`.
- Completed parser/8RAW/alignment evidence is archived, not repeated here.

## Next Actions

1. Start from the plan addendum's `/goal` and execute A owner-deepening in the
   existing Discovery owners.
2. Run focused checker/parser/writer tests before RAW validation.
3. Rerun the one-RAW successor checker and document whether A closes, A has a
   structural blocker, or B reopens under temporary-adapter constraints.
4. Keep default matrix activation separate; only open that expected-diff task
   when the public default `quant_matrix.tsv` should materialize the
   `300.1605 -> 184.113` row.

## Latest Local Checks

- Decision Spike v1 focused tests passed before this handoff prune:
  `python -m pytest tests\test_discovery_architecture_ab_artifact.py tests\test_discovery_precursor_inference_artifact.py -q`
  (`13 passed`).
- Decision Spike v1 ruff passed:
  `uv run ruff check scripts/check_discovery_architecture_ab_artifact.py tests/test_discovery_architecture_ab_artifact.py`.
- This docs/prune closeout still needs current diff checks before commit.
