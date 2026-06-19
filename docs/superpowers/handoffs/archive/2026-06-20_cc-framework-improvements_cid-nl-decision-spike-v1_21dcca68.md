# CID-NL Discovery decision spike v1 archive

Archived: 2026-06-20
Branch: `cc/framework-improvements`
Related commit: `21dcca68`
Source current handoff before prune: 218 lines

This archive keeps completed evidence details out of the active handoff. Read
the current handoff first:
`docs/superpowers/handoffs/current/cc-framework-improvements-productization.md`.

## Completed Phase Summary

The missing `d4-N6-2HE-dA` monoisotopic row was traced to Discovery row
creation and the Discovery precursor-inference path. Diagnostic Discovery and
alignment validation recovered `300.1605 -> 184.113` into the
validation-minimal alignment output. The tracked default activation bundle still
predates that rerun.

Full 8RAW Discovery completed with 31,807 candidates:

- 28,906 `product_plus_neutral_loss`
- 1,513 `scan_precursor`
- 1,388 `mixed`

For `300.1605 -> 184.113` near RT 23.x, 8RAW Discovery found 21 candidate rows.
`TumorBC2312_DNA` contributed
`TumorBC2312_DNA#19561@mz300.160635_p184.113235`, priority `HIGH`, tier `A`,
apex RT `23.3417`, area `2.05086e+08`, basis `product_plus_neutral_loss`.

The first 8RAW alignment attempt failed before RAW work because the alignment
CSV reader compared high-precision `candidate_id` mz values against display
rounded CSV columns with a fixed `0.001 Da` tolerance. The parser now uses CSV
display precision for that guard while preserving sample, scan, precursor, and
product identity checks.

The parser + claim-fix 8RAW alignment completed:

- `alignment_review.tsv`: 5,765 rows
- `alignment_matrix.tsv`: 815 rows
- `alignment_matrix_identity.tsv`: 815 rows
- `alignment_backfill_cell_evidence.tsv`: 17,745 rows
- `skipped_evidence_ledger.tsv`: 8,015 rows

`300.1605 -> 184.113` had a primary matrix row in that diagnostic alignment:

- review family: `FAM001390`
- identity row index: `182`
- matrix row: `Mz=300.16`, `RT=23.4313`
- accepted cells: 8/8
- Breast_Cancer_Tissue_pooled_QC3 matrix value: `1.7552e+08`
- Breast_Cancer_Tissue_pooled_QC3 apex RT: `23.261`
- TumorBC2312_DNA matrix value: `1.7986e+08`
- TumorBC2312_DNA source candidate:
  `TumorBC2312_DNA#19561@mz300.160635_p184.113235`

QC3 was present in Discovery and sidecar evidence; the issue was matrix decision
ownership, not peak detection. Resolved winner claims now write as
`accepted_rescue`; true wrong-hypothesis claims remain review-only.

## Decision Spike v1 Evidence

Single-RAW TumorBC2312_DNA Discovery at RT `22-25` ran successfully under:
`output/discovery_architecture_ab/a_incremental/one_raw_tumorbc2312/`.

Legacy precursor-inference checker:

- status: pass
- row count: 157
- SHA256:
  `E69C53CE5F054C3D6385A2A66BD1B85B9D0F567F91BBC7F5A78BAC7D73953C44`

Successor architecture checker:

- summary:
  `output/discovery_architecture_ab/a_incremental/one_raw_tumorbc2312/architecture_ab_check.json`
- label: `diagnostic_only`
- current result: intentional fail
- reason: current A CSV lacks `discovery_candidate_state` and
  `ms1_feature_row_id`
- alignment parser compatibility for current CSV: pass
- basis counts: 146 `product_plus_neutral_loss`, 6 `mixed`, 5
  `scan_precursor`

Decision:

- Do not build B feature-primary temporary adapter yet.
- Implement A owner-deepening first in existing Discovery owners.
- B reopens only if A later shows material one-RAW weakness or a documented
  structural blocker under the plan addendum gates.

## Tailing And Duplicate Hypotheses

Thermo screenshot evidence was consistent with tailing/baseline duplicate
hypotheses around the same tag/product families. Discovery should remain
permissive enough to avoid missing seeded tag features; alignment/model
selection decides which hypotheses become matrix rows.

The 8RAW alignment already suppresses many duplicate/tailing hypotheses into
`audit_family`, `provisional_discovery`, `duplicate_claim_pressure`,
`rescue_only_review`, or `ambiguous_only` rows. Remaining multi-sample primary
rows are follow-up model-selection evidence, not a reason to revert precursor
inference.

## Verification Recorded Before Archive

- `uv run pytest tests/test_alignment_csv_io.py tests/test_discovery_csv.py -v --tb=short`:
  44 passed.
- `uv run pytest tests/test_alignment_production_decisions.py -v --tb=short`:
  23 passed.
- `uv run ruff check xic_extractor/alignment/csv_io.py tests/test_alignment_csv_io.py`:
  passed.
- `uv run python scripts/check_productization_state.py`: passed,
  fail-closed state index consistent.
- `git diff --check`: passed with Windows line-ending warnings only.
- Parser regression coverage included the rounded-mz case, writer/reader
  roundtrip, and just-outside-tolerance negative case.
- Decision Spike v1 focused checker tests:
  `python -m pytest tests\test_discovery_architecture_ab_artifact.py tests\test_discovery_precursor_inference_artifact.py -q`
  (`13 passed`).
- Decision Spike v1 ruff:
  `uv run ruff check scripts/check_discovery_architecture_ab_artifact.py tests/test_discovery_architecture_ab_artifact.py`
  passed.

## Authority Boundary

All evidence in this archive is historical or diagnostic unless a later
activation contract promotes it. It does not change the current product tier,
active lane, ProductWriter/default matrix authority, workbook/GUI behavior, or
the 511-cell Backfill writer authority.
