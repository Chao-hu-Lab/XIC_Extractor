# XIC productization handoff

Updated: 2026-06-20 00:33 +08:00
Branch: `cc/framework-improvements`

This is the compact current-state snapshot. Tier authority remains in
`docs/superpowers/plans/2026-06-15-productization-control-plane.md`.

## Current Verdict

The default numeric matrix remains usable for downstream analysis as the current
detected + 511 accepted-Backfill product output. ProductWriter default output is
activated for detected values plus the current accepted Backfill cells.

The missing `d4-N6-2HE-dA` monoisotopic row has been traced to Discovery row
creation and the Discovery precursor-inference path is fixed. New 8RAW
diagnostic validation confirms that the `300.1605 -> 184.113` feature now
survives into alignment and is emitted as a primary matrix row in the
validation-minimal base alignment output.

Important boundary: the already activated default matrix bundle still predates
this Discovery/alignment rerun. Do not claim the tracked default activation
bundle already contains the `300.1605 -> 184.113` row until a later default
activation expected-diff rerun regenerates and locks that public surface.

Validation status for the new Discovery/alignment evidence:
`diagnostic_only`. The parser and winner-resolved duplicate-claim fixes are
test-covered, but this run does not promote a new maturity tier or writer
authority.

The current follow-up direction is a CID-NL Discovery architecture decision, not
another default matrix activation. Two docs now define the next gate:

- `docs/superpowers/plans/LC-MS CID Neutral Loss Discovery plan.md`
- `docs/superpowers/plans/LC-MS CID Neutral Loss Discovery Architecture Alternatives Brief.md`

Decision Spike v1 result: do not build the B feature-primary temporary adapter
yet. A one-RAW rerun confirms current A still recovers `300.1605 -> 184.113`
and preserves `301.165 -> 185.116`, but the new successor checker correctly
fails the current A CSV because it lacks explicit `discovery_candidate_state`
and `ms1_feature_row_id`. Next work is A incremental owner-deepening of those
fields in the existing Discovery path, then rerun the successor checker. B can
reopen only after A passes that successor contract and a B adapter can show a
material one-RAW gain without becoming a second maintained Discovery system.

## Product State

- Current tier: `product_ready_default_matrix_activated`.
- Product authority scope: `backfill_policy_write_ready_rows`.
- Current Backfill writer authority: exactly 511 accepted Backfill cells.
- Broad 4613-row Backfill remains parked.
- No scorer was run.
- No ProductWriter/default activation rerun was launched in this validation.
- No workbook, GUI, default extraction, selected peak/area, counted detection,
  or Backfill authority changed.
- CID-NL Decision Spike v1 added only a diagnostic checker, one-RAW Discovery
  output under `output/`, and docs/handoff updates. No control-plane maturity
  tier, active lane, matrix schema, or Backfill writer authority changed.
- Control plane maintenance note updated for the matrix-decision behavior fix.
  Maturity tier, active lane, matrix schema, and Backfill writer authority are
  unchanged.

Status-index anchors remain fail-closed only: `product_ready_default_matrix_activated`; Broad Backfill auto-write remains parked; Goal 0/1 hardening added; machine-adjudicated without granting new writer authority; Goal 2 added Review Packet / Approval Workflow v1; lockbox_shadow_automation_experiment_v1; Goal 4 added Missing-Overlay Evidence Recovery v1; keep only as explanation/triage; Targeted MS1 shape identity limited rescue remains production-ready; GUI and broader targets remain blocked; `sample_metadata_v1` remains production-ready for no-output ordering; roles/batch/matrix/exclusion must not alter quant output; ReviewAction selected-candidate switch and manual-boundary area recompute remain parked; manual-boundary area recompute remain parked; classification and planning only.

## Active References

- Control plane:
  `docs/superpowers/plans/2026-06-15-productization-control-plane.md`
- Default matrix activation bundle:
  `docs/superpowers/validation/quant_matrix_default_product_activation_v1/`
- Current 8RAW Discovery output:
  `output/discovery/step3_precursor_inference_8raw_20260619/`
- Current 8RAW alignment output after parser + claim fix:
  `output/alignment/step3_precursor_inference_8raw_20260619_parserfix_claimfix/`
- Discovery parser contract:
  `xic_extractor/alignment/csv_io.py`
- Discovery CSV writer contract:
  `xic_extractor/discovery/csv_writer.py`
- Focused parser tests:
  `tests/test_alignment_csv_io.py`
- CID-NL Discovery architecture plan:
  `docs/superpowers/plans/LC-MS CID Neutral Loss Discovery plan.md`
- CID-NL A/B alternatives brief:
  `docs/superpowers/plans/LC-MS CID Neutral Loss Discovery Architecture Alternatives Brief.md`
- Deep research input:
  `docs/deepresearch/LC-MS CID Neutral Loss Discovery.md`
- Successor A/B checker:
  `scripts/check_discovery_architecture_ab_artifact.py`
- Focused successor checker tests:
  `tests/test_discovery_architecture_ab_artifact.py`
- Current one-RAW A baseline for the decision spike:
  `output/discovery_architecture_ab/a_incremental/one_raw_tumorbc2312/`

## Discovery And Alignment Evidence

Single-RAW TumorBC2312_DNA Discovery at RT 22-25 passed the checker with 157
candidates. The fixed precursor inference recovered product-plus-neutral-loss
rows including the missing `300/184` evidence, proving the issue was not limited
to one manually noticed feature. Full 8RAW Discovery completed with 31,807
candidates: 28,906 `product_plus_neutral_loss`, 1,513 `scan_precursor`, and
1,388 `mixed`. For `300.1605 -> 184.113` near RT 23.x, 8RAW Discovery found 21
candidate rows; TumorBC2312_DNA contributed
`TumorBC2312_DNA#19561@mz300.160635_p184.113235`, priority `HIGH`, tier `A`,
apex RT `23.3417`, area `2.05086e+08`, basis `product_plus_neutral_loss`.

The first 8RAW alignment attempt failed before RAW work because the alignment
CSV reader compared high-precision `candidate_id` mz values against display
rounded discovery CSV columns with a fixed 0.001 Da tolerance. The parser now
uses CSV display precision for this guard while preserving sample, scan,
precursor, and product identity checks.

The parser + claim-fix 8RAW alignment completed successfully:

- `alignment_review.tsv`: 5,765 rows
- `alignment_matrix.tsv`: 815 rows
- `alignment_matrix_identity.tsv`: 815 rows
- `alignment_backfill_cell_evidence.tsv`: 17,745 rows
- `skipped_evidence_ledger.tsv`: 8,015 rows

`300.1605 -> 184.113` now has a primary matrix row:

- review family: `FAM001390`
- identity row index: `182`
- matrix row: `Mz=300.16`, `RT=23.4313`
- accepted cells: 8/8
- Breast_Cancer_Tissue_pooled_QC3 matrix value: `1.7552e+08`
- Breast_Cancer_Tissue_pooled_QC3 apex RT: `23.261`
- TumorBC2312_DNA matrix value: `1.7986e+08`
- TumorBC2312_DNA source candidate:
  `TumorBC2312_DNA#19561@mz300.160635_p184.113235`

QC3 was present all along: Discovery and the sidecar had apex RT `23.261`.
The bug was matrix decision ownership, not peak detection. The QC3 cell had
been moved into the correct winner family but still carried loser claim state;
resolved winner claims now write as `accepted_rescue`, while true wrong-
hypothesis claims remain review-only.

Decision Spike v1 one-RAW rerun:

- Output:
  `output/discovery_architecture_ab/a_incremental/one_raw_tumorbc2312/`
- Row count: 157.
- Legacy precursor-inference checker: pass, SHA256
  `E69C53CE5F054C3D6385A2A66BD1B85B9D0F567F91BBC7F5A78BAC7D73953C44`.
- Successor checker:
  `architecture_ab_check.json` is `diagnostic_only` and intentionally `fail`
  because current A lacks `discovery_candidate_state` and
  `ms1_feature_row_id`; alignment parser compatibility for the current CSV is
  `pass`.
- Decision: A incremental owner-deepening first; no B adapter yet.

## Tailing And Duplicate Hypotheses

The user-supplied Thermo screenshots are consistent with tailing/baseline
duplicate hypotheses around the same tag/product families. The fix intentionally
does not suppress these in Discovery; Discovery should be permissive enough to
avoid missing seeded tag features. Alignment/model selection must decide which
hypotheses become matrix rows.

The 8RAW alignment already suppresses many duplicate/tailing hypotheses into
`audit_family`, `provisional_discovery`, `duplicate_claim_pressure`,
`rescue_only_review`, or `ambiguous_only` rows. Remaining multi-sample primary
rows are follow-up model-selection evidence, not a reason to revert precursor
inference.

## Boundaries

- Do not demote or delete the `301.165` isotope row. It can legitimately be a
  product row when it carries its own tag evidence.
- Do not treat Discovery candidates as matrix rows. Candidate volume is high by
  design after precursor inference is restored.
- Do not start the B feature-primary adapter until A emits explicit
  `discovery_candidate_state` and `ms1_feature_row_id`, and the successor
  one-RAW checker passes. If B is later attempted, it must stay out of
  `scripts/run_discovery.py` CLI/config flags and be deleted or left unmerged
  unless it materially beats A on the same oracle.
- Do not treat the parser-fixed 8RAW alignment as default matrix activation.
- Do not launch 85RAW unless the next step names a product decision that 8RAW
  cannot close.
- Keep broad Backfill parked.
- Keep all generated validation outputs under `output/` unless a later contract
  explicitly promotes a summary, hash, index, or minimal fixture.

## Verification

- `uv run pytest tests/test_alignment_csv_io.py tests/test_discovery_csv.py -v --tb=short`:
  44 passed.
- `uv run pytest tests/test_alignment_production_decisions.py -v --tb=short`:
  23 passed.
- `uv run ruff check xic_extractor/alignment/csv_io.py tests/test_alignment_csv_io.py`:
  passed.
- `uv run python scripts/check_productization_state.py`: passed,
  fail-closed state index consistent.
- `git diff --check`: passed with Windows line-ending warnings only.
- Parser regression coverage includes the failing rounded-mz case, a writer to
  reader roundtrip, and a just-outside-tolerance negative case.
- Single-RAW Discovery checker, 8RAW Discovery, 8RAW alignment preflight, and
  parser + claim-fix 8RAW alignment completed successfully.
- Decision Spike v1 focused checker tests:
  `python -m pytest tests\test_discovery_architecture_ab_artifact.py tests\test_discovery_precursor_inference_artifact.py -q`
  (`13 passed`).
- Decision Spike v1 ruff:
  `uv run ruff check scripts/check_discovery_architecture_ab_artifact.py tests/test_discovery_architecture_ab_artifact.py`
  passed.
- Decision Spike v1 one-RAW A baseline command completed and emitted
  `discovery_candidates.csv`, `discovery_review.csv`, and `timing.json`.

## Next Actions

1. Implement A incremental owner-deepening in the existing Discovery owners:
   add explicit `discovery_candidate_state` and `ms1_feature_row_id` with
   writer/reader roundtrip and parser tests.
2. Rerun the one-RAW successor checker. Only consider a B temporary adapter if
   A passes the successor checker and B can test a material gain without a
   public runtime flag or second maintained Discovery path.
3. Keep default matrix activation separate. Only open that expected-diff task
   when the public default `quant_matrix.tsv` should materialize the
   `300.1605 -> 184.113` row.
