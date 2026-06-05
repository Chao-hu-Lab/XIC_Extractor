# Full Untarget PeakHypothesis Final Matrix Contract

## Status

Product writer contract active; full upstream split construction remains
incomplete. The main product writers now emit clean `Mz` / `RT` / sample-column
matrix rows with `alignment_matrix_identity.tsv` sidecar rows, can expand
explicit `PeakHypothesis` child rows when supplied with complete provenance and
a total/unique accepted-cell partition, and fail closed on unresolved
projections, incomplete split identity, or multi-family row collapse. No-split
rows use the successor `group_hypothesis_id` as the product identity when it is
available; `feature_family_id` remains source provenance. This does not by
itself prove all-family split science readiness or `production_ready` status.

This spec supersedes the final-matrix row-identity direction in
`2026-05-14-final-matrix-identity-contract.md`. The older contract kept
`production_family` as the product row identity. The new contract keeps the old
pipeline matrix shape, but changes the internal row identity to
`PeakHypothesis`.

Subagent review status: tightened after `strategy-challenger` and
`implementation-contract-reviewer` review. The blocking clarification is that
old family rows cannot be relabeled as no-split hypotheses merely because split
evidence is absent. A product no-split hypothesis needs an explicit complete
split-evaluation basis. Both reviewers re-checked the tightened contract and
reported no remaining blockers.

## Verdict

The untargeted final quantitative matrix must remain a clean old-pipeline-style
matrix:

- `Mz`
- `RT`
- sample columns

The row behind each displayed `Mz`/`RT` must be a `PeakHypothesis`. Legacy
`feature_family_id` values are provenance, compatibility inputs, or possible
internal identifiers for unsplit hypotheses. They are not the product row
semantics anymore.

`family_projection` is not allowed to be product behavior. It may appear only in
migration diagnostics, bridge outputs, or audit artifacts that explicitly report
the matrix as incomplete for canonical row identity.

This is a deliberate public behavior change from the retired writer contract.
The active product writers keep family-based fields such as `feature_family_id`,
`neutral_loss_tag`, `family_center_mz`, and `family_center_rt` out of the primary
`Matrix` surface and place identity/provenance in sidecars/review surfaces.

## Product Surface

Primary product outputs:

- `alignment_matrix.tsv`
- workbook `Matrix`

These outputs must expose only:

- `Mz`
- `RT`
- sample columns

They must not expose:

- `peak_hypothesis_id`
- `feature_family_id`
- `row_identity_basis`
- `family_projection`
- evidence tokens
- review status columns
- audit-only or provisional row labels

All identity, source, split, center-calculation, and evidence details belong in
sidecars or review/audit outputs.

## Internal Row Identity

Every row in the product matrix has exactly one internal `PeakHypothesis`
identity.

No-split case:

- If complete split evaluation finds no product-ready split, the old family and
  the new hypothesis are semantically equivalent for product output.
- The internal `peak_hypothesis_id` is the successor `group_hypothesis_id` when
  available, and may reuse the old `feature_family_id` only when no successor
  group id exists.
- No synthetic suffix such as `::singleton` is required.
- The displayed matrix still uses only `Mz` and `RT`, not the id.

A no-split product row is allowed only when all of these are true:

- `row_identity_basis=no_split_peak_hypothesis`;
- `split_evaluation_status=complete_no_product_ready_split`;
- `projection_status=not_projection`;
- `source_feature_family_ids` names the source family provenance;
- the row was produced by the product matrix construction path, not by excluding
  unresolved projections from a partial diagnostic output.

Absence of split evidence, skipped split evaluation, excluded projection rows,
or an incomplete evidence scope must remain blocked as projection/incomplete
scope. It must not be relabeled as a no-split hypothesis.

Split case:

- If product-ready evidence supports multiple peaks inside the previous family
  region, the parent unsplit hypothesis is replaced by explicit split
  hypotheses.
- Each explicit split child must carry a non-empty `peak_hypothesis_id` and
  exactly one `source_feature_family_id`.
- The product matrix must not keep a parent aggregate row beside its split
  children.
- Each sample cell is written to one accepted hypothesis row only.
- Duplicate counting through both parent and child rows is forbidden.

Projection case:

- A row whose identity is only `<feature_family_id>::family_projection` is an
  unresolved migration row.
- Projection rows are acceptable only in explicit diagnostic opt-in artifacts.
  Bridge/formal product-shaped outputs must exclude them by default and report
  the excluded projection scope separately.
- Projection rows must block product promotion and complete identity gates.

## Evidence And Split Rules

The final matrix follows the evidence-chain direction, not a score-weighted
family winner direction.

A split may enter the product matrix only when it is supported by product-ready
evidence. Valid evidence can include typed RT/mode evidence, MS1 shape and trace
pattern consistency, candidate-aligned MS2 or neutral-loss evidence, RT drift or
QC context, and conflict evidence that distinguishes co-existing peaks. The
important rule is not that one evidence source is decisive. The rule is that the
evidence chain supports a concrete hypothesis well enough to change product row
identity.

Raw overlay windows, inferred raw-mode windows, and review-only candidates do
not split the product matrix by themselves. They stay in sidecars until a
product-ready contract promotes them.

Missing or review-only candidate cells do not get written into the product
matrix. They remain blank in the final matrix and stay explainable through
review/audit sidecars.

Wrong-hypothesis cells must move to the accepted hypothesis row or stay out of
the product matrix. They must not be kept in an aggregate parent row as a
fallback.

## Mz And RT Centers

`Mz` and `RT` are the displayed center of the product `PeakHypothesis`.

No-split case:

- The center should match the legacy family center when the accepted cells are
  equivalent to the old family support.

Split case:

- Each split hypothesis has its own `Mz` and `RT` center.
- The parent family center is not used as a product row once the row has been
  split.

Center calculation:

- The displayed `Mz`/`RT` center is recomputed from accepted product cells in
  each run.
- The initial weighting basis should be the accepted cell's primary matrix area
  or intensity, following the existing quantitative value source.
- Stable traceability is provided by the sidecar identity row, not by freezing
  the displayed `Mz`/`RT` forever.

If the accepted-cell center and the previous family center diverge materially,
the sidecar must expose the basis and enough provenance to explain why.

## Required Sidecars

`alignment_matrix_identity.tsv` is required once this contract is implemented.
It is the machine-readable bridge between the clean product matrix and the
internal identity/evidence model.

Exact required header order:

- `identity_schema_version`
- `matrix_row_index`
- `Mz`
- `RT`
- `peak_hypothesis_id`
- `row_identity_basis`
- `split_evaluation_status`
- `projection_status`
- `source_feature_family_ids`
- `source_feature_family_count`
- `center_mz_basis`
- `center_rt_basis`
- `center_weight_basis`
- `accepted_cell_count`
- `accepted_sample_count`
- `evidence_status`
- `parent_peak_hypothesis_id`
- `child_peak_hypothesis_ids`

The sidecar must have one row per product matrix row, in product matrix order.
It must not be optional when the product matrix no longer exposes row ids.

Column contracts:

- `identity_schema_version` is the literal
  `untargeted_peak_hypothesis_matrix_identity_v1`.
- `matrix_row_index` is 1-based product matrix row order, excluding the header.
- `Mz` and `RT` must exactly match the displayed product matrix values for the
  same row.
- `source_feature_family_ids` is a semicolon-delimited provenance list with no
  whitespace padding.
- `source_feature_family_count` is the count of unique ids in
  `source_feature_family_ids`.
- `parent_peak_hypothesis_id` is blank for ordinary no-split rows and contains
  the retired parent id only when a split row replaces a previous unsplit
  hypothesis.
- `child_peak_hypothesis_ids` is blank on product rows unless the row is
  represented in a review/audit sidecar as a retired parent; the primary matrix
  itself must not include parent aggregate rows beside children.

Allowed `row_identity_basis` tokens for product rows:

- `no_split_peak_hypothesis`
- `split_peak_hypothesis`

Forbidden `row_identity_basis` tokens for product rows:

- `family_projection`
- `family_projection_no_split_evidence`
- any raw-overlay-only, review-only, bridge-only, or diagnostic-only basis

Allowed `split_evaluation_status` tokens for product rows:

- `complete_no_product_ready_split`
- `complete_product_ready_split`

Forbidden `split_evaluation_status` tokens for product rows:

- `not_evaluated`
- `incomplete_scope`
- `review_only`
- `raw_overlay_only`

Allowed `projection_status` token for product rows:

- `not_projection`

Any other `projection_status` blocks product promotion.

Cell-level and review-level sidecars should continue to carry the detailed
sample assignments, candidate evidence, rejected candidates, and review-only
signals. The final matrix remains clean because those details are available
elsewhere, not because they are discarded.

## Product Implementation Lock

This contract must be implemented through the real untargeted product path, not
only through diagnostics:

- `scripts/run_alignment.py`
- `xic_extractor.alignment.pipeline.run_alignment`
- `xic_extractor.alignment.pipeline_outputs.write_outputs_atomic`
- `xic_extractor.alignment.tsv_writer.write_alignment_matrix_tsv`
- `xic_extractor.alignment.xlsx_writer.write_alignment_results_xlsx`

The existing diagnostic matrix constructor can remain a bridge/audit tool, but
it cannot be the only implementation surface. A passing diagnostic is not a
product behavior change unless the primary `alignment_matrix.tsv`, workbook
`Matrix`, and required `alignment_matrix_identity.tsv` are emitted through the
product writer path.

The implementation must update output-level/path wiring so that
`alignment_matrix_identity.tsv` is emitted whenever the primary matrix is
emitted. If an output level intentionally omits `alignment_matrix.tsv`, it may
omit the identity sidecar too.

## Promotion Gates

A matrix is not product-ready under this contract if any of the following are
true:

- Any product row has `row_identity_basis=family_projection`.
- Any product row has `row_identity_basis=family_projection_no_split_evidence`.
- Any product row has `projection_status` other than `not_projection`.
- Any no-split product row lacks
  `split_evaluation_status=complete_no_product_ready_split`.
- Any matrix summary reports `family_projection_rows > 0`.
- Any matrix summary reports `family_projection_rows_excluded > 0`.
- Complete identity is claimed after simply excluding unresolved projections.
- A split family keeps both the parent aggregate row and split child rows in the
  product matrix.
- A product row lists more than one `source_feature_family_id`; this is treated
  as multi-family collapse, not as a valid PeakHypothesis.
- A sample cell contributes value to more than one product hypothesis row for
  the same source peak.
- Review-only or raw-overlay-only candidates write values into the product
  matrix.

The current stop gate is:

```powershell
uv run python tools/diagnostics/build_peak_hypothesis_matrix.py `
  --require-complete-peak-hypothesis-identity
```

The gate must fail while unresolved projection rows remain. A projection-free
partial output is useful for debugging, but it is not a complete product matrix.

## Current Evidence Snapshot

The current no-RAW audit path is:

`output/untargeted_hypothesis_product_path_audit_20260603/`

Observed summary:

- `source_matrix_rows=610`
- `output_matrix_rows=611`
- `explicit_peak_hypothesis_rows=4`
- `family_projection_rows=610`
- `projected_cell_count=39091`
- `canonical_row_identity_ready=FALSE`
- `canonical_row_identity_blockers=family_projection_present`
- `construction_gate_status=blocked`
- `diagnostic_only=TRUE`

This historical diagnostic construction snapshot proved the then-existing path
was still mostly a legacy family-projection bridge, not a complete
PeakHypothesis final matrix. Current formal activation output excludes
unresolved projections by default and reports the excluded scope separately.

The formal canonical-only probe can emit only explicit hypothesis rows after
excluding projections, but that output remains incomplete:

`output/untargeted_activation_contract_recheck_20260603/formal_canonical_only_probe/`

Observed summary:

- `canonical_row_identity_ready=FALSE`
- `canonical_row_identity_blockers=family_projection_excluded_incomplete_scope`
- `canonical_row_identity_scope=partial_canonical_peak_hypothesis_rows_only`
- `family_projection_semantics=excluded_from_canonical_output`
- `family_projection_rows=0`
- `family_projection_rows_excluded=610`
- `family_projection_cells_excluded=39089`
- `output_matrix_rows=2`

This means "projection-free emitted rows" is not the same as "complete final
matrix".

## Implementation Direction

Phase 1: contract and schema lock.

- Add or update tests that define the final matrix public shape:
  `Mz`, `RT`, sample columns.
- Add or update tests that require one identity sidecar row per matrix row.
- Add or update tests that reject `family_projection`,
  `family_projection_no_split_evidence`, incomplete split evaluation, and any
  non-`not_projection` product row identity.
- Add or update tests that prove `alignment_matrix.tsv` and workbook `Matrix`
  use the same clean shape and row order.
- Add or update tests that prove `alignment_matrix_identity.tsv` uses the exact
  schema and row order defined above.

Phase 2: full hypothesis row construction.

- Convert every product matrix row into a `PeakHypothesis`.
- Reuse old `feature_family_id` as the internal hypothesis id only when complete
  split evaluation emits an explicit `no_split_peak_hypothesis` basis.
- Keep `feature_family_id` as provenance in sidecars.
- Emit `alignment_matrix_identity.tsv`.

Phase 3: split-aware cell assignment.

- Apply product-ready split evidence before product matrix writing.
- Write each sample value to only the accepted hypothesis row.
- Leave review-only candidates blank in the product matrix.
- Preserve candidate evidence in review/audit sidecars.
- Add characterization tests that parent and child rows cannot both write to the
  product matrix, and that one source peak cannot contribute to two product rows.

Phase 4: product wiring and retirement.

- Wire the complete PeakHypothesis matrix into the main untargeted product path.
- Keep bridge/projection tooling as diagnostic-only until no longer needed.
- Retire `family_projection` from product outputs after parity and gate evidence
  are stable.

## Non-goals

This spec does not:

- change AsLS baseline or quantitative integration policy;
- make target labels part of untargeted product identity;
- expose internal ids in the final matrix;
- promote raw-overlay-only evidence into product behavior;
- require deleting all legacy family code immediately.

Legacy code can remain as constructor, adapter, provenance, or diagnostic code
while the product matrix moves to the PeakHypothesis contract. What must end is
the maintenance of a second product row semantics in the final matrix.
