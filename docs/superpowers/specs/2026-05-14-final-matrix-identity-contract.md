# Final Matrix Identity Contract

## Goal

Keep the final untargeted matrix clean enough for quantitative comparison while
preserving weak or rare discovery evidence for later review. The old pipeline
matrix shape is the product target for the primary matrix. The new pipeline may
carry more evidence, but that evidence belongs in Review/Audit unless it earns
primary row identity.

## Identity Tiers

`production_family` is the only tier allowed into `alignment_matrix.tsv` and the
workbook `Matrix` sheet. It requires primary identity support, not just a
backfilled value. In v1 this means owner/multi-sample evidence with at least two
quantifiable detected identity-support cells, and not a high-risk single-`dR`
backfill dependency pattern.

`provisional_discovery` is retained discovery evidence. It is not a failed or
discarded feature. It is a row with non-zero detected support that is not yet
strong enough for the primary quantitative matrix, such as a single-sample local
owner, an anchored single detected family, or another low-support detected row.
It appears in `alignment_review.tsv`, workbook `Review`, and workbook `Audit`.

`audit_family` is evidence that should stay out of the primary matrix and should
not be interpreted as a provisional discovery signal. Examples include
backfill-only/rescue-only rows, duplicate-only rows, ambiguous-only rows,
zero-present rows, review-only rows, and family consolidation losers.

## Promotion Contract

`include_in_primary_matrix` remains the only primary matrix gate. A row can enter
the Matrix only when `identity_decision == "production_family"` and it has at
least one accepted production cell.

Backfill and rescue can fill cells for an existing family, but they cannot create
primary row identity. Rescued cells do not count as detected identity support.
Backfill is expected to restore missing cells for highly detected features. A
single-`dR` family with only one or two quantifiable detected identity-support
cells and at least 70% quantifiable rescue cells is treated as
`provisional_discovery`, not `production_family`.

A single-`dR` family with no more than three quantifiable detected
identity-support cells, at least 60% quantifiable rescue cells, and weak detected
seed quality is also treated as `provisional_discovery`. Weak seed quality means
at least one detected seed has `evidence_score < 60`, `seed_event_count < 2`,
`abs(neutral_loss_mass_error_ppm) > 10`, or cannot be joined back to its detected
source candidate.

Duplicate pressure is a promotion input, not just a warning. If duplicate
assigned cells outnumber detected identity-support cells, the row remains
`audit_family` unless a separate family-winner consolidation step creates a
supported production family.

Targeted ISTD evidence is validation. It can confirm whether the untargeted
matrix behaves correctly, but production identity logic must not depend on target
labels.

## Output Contract

Primary outputs:

- `alignment_matrix.tsv`
- workbook `Matrix`

These outputs include only `production_family` rows and numeric matrix values.
They must not expose raw status strings, provisional rows, or audit-only rows.

Review/Audit outputs:

- `alignment_review.tsv`
- workbook `Review`
- workbook `Audit`

These outputs must expose `identity_decision`, `identity_confidence`,
`primary_evidence`, `identity_reason`, `include_in_primary_matrix`, and
`row_flags`, so weak discovery evidence remains inspectable without polluting the
primary matrix.

