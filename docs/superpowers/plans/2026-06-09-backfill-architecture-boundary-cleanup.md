# Backfill Architecture Boundary Cleanup

**Goal status:** production-boundary cleanup for reviewed normal-peak backfill.

## Decision

Reviewed PeakHypothesis-level same-peak normal-peak evidence can trigger
backfill matrix writes. The cleanup target is not to block same-peak evidence;
it is to keep the authority and provenance precise:

- activation keys are `peak_hypothesis_id + sample`, not legacy FAM ids;
- FAM ids remain source/debug provenance when they are needed;
- matrix-written values must be tagged as backfill activation values, not primary
  detected values;
- nonstandard peaks remain outside this production slice until the integration
  policy is defined.

## Closed In This Slice

- Matrix-only activation can write reviewed normal-peak backfill values without
  reading or rewriting `alignment_cells.tsv`.
- `activation_values.tsv` input rows now require explicit value/source
  provenance before matrix-only activation can consume them:
  `projected_matrix_value_source`, `source_artifact_schema_version`,
  `source_artifact_sha256`, `source_row_sha256`, and
  `source_provenance_detail`.
- For 85RAW transfer promotions, `source_artifact_sha256` is the actual content
  bundle hash of `normal_peak_decisions_tsv + activation_trial_tsv`; source
  PeakHypothesis/FAM ids remain audit-only labels and are not used to invent a
  provenance hash.
- `activation_value_delta.tsv` is schema v3 and records per-cell matrix value
  provenance:
  - `matrix_value_kind`;
  - `matrix_value_source`;
  - `matrix_value_source_field`;
  - `matrix_value_source_detail`;
  - source artifact schema/hash and source row hash.
- Matrix-only written cells are tagged as
  `matrix_value_kind=backfill_activation`,
  `matrix_value_source=activation_values_tsv`, and
  `matrix_value_source_field=projected_matrix_value`.
- Owner-backfill now has an all-candidate sidecar,
  `alignment_owner_backfill_candidate_audit.tsv`, emitted alongside
  `alignment_owner_backfill_seed_audit.tsv` when the backfill seed audit flag is
  enabled. It records queried seed/window, candidate outcome, and whether the
  candidate became the selected output cell.
- Current 85RAW artifact-only matrix validation passes after the schema v3
  provenance/hash update:
  - output:
    `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_acceptance_matrix_only_v3_provenance_no_normal_decisions/`;
  - `changed_matrix_cell_count=11`;
  - `unexpected_matrix_diff_count=0`;
  - `missing_matrix_diff_count=0`;
  - `value_mismatch_count=0`;
- Source-bundle provenance rerun:
  `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_acceptance_matrix_only_source_bundle/`
  passes with `changed_matrix_cell_count=11`,
  `unexpected_matrix_diff_count=0`, `missing_matrix_diff_count=0`,
  `value_mismatch_count=0`, and `value_delta_mismatch_count=0`; all 11
  promotion, transfer, and value-delta rows carry the actual
  `normal_peak_decisions_tsv + activation_trial_tsv` content bundle hash.
  - `value_delta_mismatch_count=0`.

## Still Open

- Define nonstandard peak integration policy separately. Same-peak identity
  support can be strong, but quantitative integration for nonstandard shapes is
  not product-ready in this goal.
- Add masked-positive recovery validation when we move from reviewed normal-peak
  transfer to broader automatic weak-signal recovery.
