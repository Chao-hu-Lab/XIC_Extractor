# Matrix-Only Backfill Activation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decouple reviewed backfill matrix activation from full `alignment_cells.tsv` read/write cost.

**Architecture:** Keep `alignment_cells.tsv` as an audit/debug ledger. Add a matrix-only activation path in the existing shared-peak `product_activation` owner that consumes product-authorized activation values, `alignment_matrix.tsv`, `alignment_matrix_identity.tsv`, and lightweight `alignment_review.tsv` row metadata, then writes only activated matrix/identity plus activation summary/value-delta artifacts. The full activation path remains responsible for review/cell ledger mutation and backfill evidence projection.

**Tech Stack:** Python, TSV diagnostics, pytest, ruff, mypy.

---

### Task 1: Matrix-Only Activation Contract

**Files:**
- Modify: `xic_extractor/alignment/shared_peak_identity_explanation/product_activation.py`
- Modify: `tools/diagnostics/apply_shared_peak_identity_activation.py`
- Test: `tests/test_shared_peak_identity_product_activation.py`

- [x] **Step 1: Write the failing test**

Add a test that calls the CLI with `--matrix-only`, `--activation-values-tsv`,
`--alignment-matrix-tsv`, `--alignment-matrix-identity-tsv`, and
`--alignment-review-tsv`, but no `--alignment-cells-tsv`. Expected output:
`alignment_matrix.tsv`, `alignment_matrix_identity.tsv`,
`activation_hypothesis_identity.tsv`, `activation_value_delta.tsv`, and
`activation_application_summary.tsv`; no `alignment_cells.tsv` or
`alignment_review.tsv`.

- [x] **Step 2: Verify RED**

Run:

```powershell
python -m pytest tests\test_shared_peak_identity_product_activation.py::test_activation_application_cli_matrix_only_uses_activation_values_without_cells -q
```

Expected: fail because `--matrix-only` is not implemented.

- [x] **Step 3: Implement minimal matrix-only path**

Add a product-activation function that:

- validates activation decisions and acceptance;
- reads the public/formal matrix and matrix identity;
- reads `alignment_review.tsv` for row metadata only;
- reads activation value rows keyed by `(peak_hypothesis_id, sample)`;
- applies `auto_activate` by writing values from the activation value rows;
- writes matrix, matrix identity, hypothesis identity, value delta, and summary;
- does not read, require, or write `alignment_cells.tsv`.

- [x] **Step 4: Verify GREEN**

Run the targeted test and then the product activation shard.

### Task 2: 85RAW Normal-Peak Smoke

**Files:**
- Use existing 85RAW artifacts under `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/`

- [x] **Step 1: Run matrix-only activation on current 85RAW normal-peak transfer**

Use the raw85-keyed transfer promotion cells as `--activation-values-tsv`.
The run must not pass `--alignment-cells-tsv`.

- [x] **Step 2: Run existing post-activation acceptance**

Expected:

- `acceptance_status=pass`
- `changed_matrix_cell_count=11`
- `unexpected_matrix_diff_count=0`
- `missing_matrix_diff_count=0`
- `value_mismatch_count=0`

### Task 3: Documentation And Index

**Files:**
- Modify: `docs/superpowers/notes/2026-06-07-backfill-evidence-reconciliation-productization-note.md`
- Modify: `docs/superpowers/plans/2026-06-08-peakhypothesis-backfill-promotion-policy.md`
- Modify: `tools/diagnostics/INDEX.md`

- [x] **Step 1: Record the architecture decision**

Document that `alignment_cells.tsv` remains an audit/debug ledger and is no
longer required for reviewed normal-peak matrix-only activation when
product-authorized activation values are available.

- [x] **Step 2: Verify**

Run relevant pytest shard, ruff, and mypy.

Observed result, 2026-06-09:

- matrix-only output:
  `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_transfer_matrix_only/`;
- post-activation acceptance:
  `output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_acceptance_matrix_only/backfill_peakhypothesis_activation_acceptance_summary.json`;
- `acceptance_status=pass`;
- `changed_matrix_cell_count=11`;
- `unexpected_matrix_diff_count=0`;
- `missing_matrix_diff_count=0`;
- `value_mismatch_count=0`.

Architecture conclusion: `alignment_cells.tsv` remains the audit/debug ledger
for full activation and evidence projection, but reviewed normal-peak backfill
does not need to read or rewrite it once product-authorized activation values
exist. The matrix-only path writes only the public matrix, matrix identity,
PeakHypothesis identity, value delta, and application summary.

Provenance closure, 2026-06-09: `activation_value_delta.tsv` first became the
per-cell matrix value provenance sidecar in schema v2. A matrix-only written
value is explicitly tagged as `matrix_value_kind=backfill_activation`,
`matrix_value_source=activation_values_tsv`, and
`matrix_value_source_field=projected_matrix_value`. This keeps reviewed
same-peak normal-peak backfill writable while preventing the public matrix value
from being confused with a primary detected value.

Input-provenance closure, 2026-06-09: matrix-only `activation_values.tsv` input
now requires `projected_matrix_value_source`, `source_artifact_schema_version`,
`source_artifact_sha256`, `source_row_sha256`, and
`source_provenance_detail`. `activation_value_delta.tsv` is schema v3 and
preserves the source artifact schema/hash plus source row hash for each matrix
write. For the 85RAW normal-peak transfer source, `source_artifact_sha256` is the
actual content bundle hash of `normal_peak_decisions_tsv + activation_trial_tsv`,
not a synthetic id-derived hash. The source-bundle artifact-only rerun passed
under
`output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_acceptance_matrix_only_source_bundle/`
with `changed_matrix_cell_count=11`, `unexpected_matrix_diff_count=0`,
`missing_matrix_diff_count=0`, `value_mismatch_count=0`, and
`value_delta_mismatch_count=0`; all 11 promotion, transfer, and value-delta rows
carry the same source bundle hash. The earlier v3 artifact-only rerun passed
under
`output/backfill_peakhypothesis_normal_peak_override_85raw_20260609/activation_acceptance_matrix_only_v3_provenance_no_normal_decisions/`
with `changed_matrix_cell_count=11`, `unexpected_matrix_diff_count=0`,
`missing_matrix_diff_count=0`, and `value_delta_mismatch_count=0`.
