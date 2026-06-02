# AsLS Primary Matrix Value Policy Goal

**Date:** 2026-06-02
**Status:** Complete
**Readiness target:** `production_ready` for primary matrix value delivery
**Primary spec:** [AsLS primary matrix value policy](../specs/2026-06-02-asls-primary-matrix-value-policy-spec.md)
**8RAW closeout:** [AsLS primary matrix value 8RAW closeout](../notes/2026-06-02-asls-primary-matrix-value-8raw-closeout.md)
**85RAW closeout:** [AsLS primary matrix value 85RAW closeout](../notes/2026-06-02-asls-primary-matrix-value-85raw-closeout.md)

## GOAL

Complete AP0-AP3 for AsLS primary matrix value policy so the final matrix
primary quantitative value is AsLS-corrected selected integration area, not raw
selected area, legacy `cell.area`, or any retired linear-edge-compatible value.

## CONTEXT TO READ FIRST

- `AGENTS.md`
- `docs/agent-subagent-routing.md`
- `docs/agent-parameter-settings.md`
- `docs/superpowers/specs/2026-06-02-asls-primary-matrix-value-policy-spec.md`
- `docs/superpowers/specs/2026-06-02-mature-package-flow-reference-spec.md`
- `docs/superpowers/specs/2026-05-24-peak-pipeline-area-baseline-asls-promotion-spec.md`

## CONSTRAINTS

- Do not re-enable `linear_edge` as config, fallback, comparator truth, or
  rollback product path.
- Do not copy raw area into `area_baseline_corrected` to satisfy the selector.
- Populate AsLS selected-integration fields on the product path before
  `cell_quality` / `production_decisions`; do not rely on optional audit
  emission, `output_level`, workbook `Audit`, or integration-audit TSV.
- Keep writers as policy consumers. Do not make TSV/XLSX writers choose between
  raw and baseline-corrected area.
- Keep `alignment_matrix.tsv` and workbook `Matrix` shape stable unless a
  separate approved output spec changes schema.
- Treat `alignment_cells.tsv:area` and workbook `Audit:area` as raw audit values
  unless explicitly paired with primary-value/source fields.
- `product_activation` must not auto-write a primary matrix value from raw
  `alignment_cells.tsv:area`.
- Do not bundle C4 scoring migration, C6 owner-family semantic migration, or
  region-boundary promotion.

## PHASES

### AP0 - Characterize Current State

- Add or update focused tests proving current fixture assumptions are migrated:
  raw selected integration is not the product matrix value.
- Pin missing-AsLS behavior as blank/review with
  `missing_asls_primary_area`.

### AP1 - Selector

- Add an alignment-domain selector for primary matrix area.
- It returns a value only when `baseline_type == "asls"` and
  `area_baseline_corrected` is positive finite.
- It returns no product value with a machine-readable missing reason otherwise.

### AP2 - Product-Path AsLS Population

- Update owner/backfill matrix handoff so selected integrations created from
  trace-backed peaks carry AsLS fields before cell-quality decisions.
- No-audit-mode runs must still populate these fields.
- If a path only has scalar area and no trace/provenance, it must remain
  missing-AsLS and not silently write a matrix value.

### AP3 - Production Matrix Value Switch

- Switch `AlignedCell.matrix_area` or its equivalent policy surface to the
  AsLS selector.
- Update `matrix_area_source` vocabulary.
- Keep `ProductionDecisionSet`, TSV writer, and XLSX writer consuming approved
  matrix values.
- Block `product_activation` from writing raw `area` as a matrix value.

## DONE WHEN

- Primary matrix sample cells use `IntegrationResult.area_baseline_corrected`
  with `baseline_type == "asls"`.
- Raw selected area is audit-only.
- Missing AsLS does not fall back to raw selected area or `cell.area`.
- `missing_asls_primary_area` is observable in production/audit/activation
  reason surfaces where a value is blanked for this reason.
- `alignment_matrix.tsv` and workbook `Matrix` shape remain stable.
- `product_activation` no longer writes raw `alignment_cells.tsv:area` into a
  primary matrix value.
- Focused tests prove raw-vs-AsLS divergence, missing-AsLS blanking, no-audit
  population, TSV/XLSX matrix value behavior, and activation-not-raw behavior.

## VERIFY

Run at minimum:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run pytest -q tests/test_alignment_matrix.py tests/test_alignment_cell_quality.py tests/test_alignment_production_decisions.py tests/test_alignment_tsv_writer.py tests/test_alignment_xlsx_writer.py tests/test_alignment_owner_matrix.py tests/test_alignment_owner_backfill.py tests/test_shared_peak_identity_product_activation.py
uv run pytest -q tests/test_untargeted_final_matrix_contract.py tests/test_alignment_pipeline.py tests/test_alignment_pipeline_outputs.py tests/test_config.py tests/test_baseline_integration.py tests/test_peak_hypotheses.py
uv run ruff check xic_extractor tests
uv run mypy xic_extractor
git diff --check
```

If focused tests pass and the code path changes matrix values, preflight and run
an 8RAW `validation-minimal` closeout using `docs/agent-parameter-settings.md`,
unless existing current-code artifacts can answer the same decision.

## CLOSEOUT

Completed on 2026-06-02.

Verification run:

- focused matrix/owner/writer/activation tests: `107 passed`
- final-matrix/pipeline/config/baseline/hypothesis tests: `129 passed`
- activation/schema source-hardening tests: `24 passed`
- full test suite: `2830 passed, 1 skipped`
- `uv run ruff check xic_extractor tests`: pass
- `uv run mypy xic_extractor`: pass
- `git diff --check`: pass with LF/CRLF warnings only
- 8RAW `validation-minimal`, `audit_evidence_mode=none`: pass; see the 8RAW
  closeout note.
- 85RAW `validation-minimal`, `production-equivalent`,
  `audit_evidence_mode=none`: pass; see the 85RAW closeout note.

Additional closeout findings:

- Updated stale raw-area fixture expectations in matrix identity, owner-family,
  primary-consolidation, and single-dR diagnostics tests so characterization
  fixtures provide AsLS selected integrations.
- Updated `matrix_identity_blast_radius` TSV loader to reconstruct AsLS
  `IntegrationResult` only from `primary_matrix_area` with source
  `asls_baseline_corrected`; raw `alignment_cells.tsv:area` remains audit-only.

Final delivery decision:

- `production_ready` for primary matrix value delivery/source semantics
- this is not an absolute baseline-truth claim for spike-in, linearity, blank
  subtraction, carryover, or synthetic known-area validation
- matrix written cells: `2350`
- written-cell source mismatches: `0`
- `missing_asls_primary_area` cells: `2` rescued cells, both blank in Matrix
- 85RAW matrix written cells: `39094`
- 85RAW written-cell source mismatches: `0`
- 85RAW written-cell value mismatches: `0`
- 85RAW `missing_asls_primary_area` cells: `25` rescued cells, all blank in
  Matrix

## STOP RULES

Stop and write a blocker note if:

- AP2 shows many product cells cannot receive AsLS fields without copying raw
  values;
- row inclusion changes for reasons unrelated to missing AsLS primary area;
- writers need a schema change before reviewers can understand value source;
- no-audit-mode population cannot be implemented without making audit mandatory;
- 8RAW output shows widespread missing-AsLS blanks;
- any path tries to restore `linear_edge` fallback.

## SUBAGENT REVIEW GATE

- Before execution, review this goal/spec with `strategy-challenger` and
  `implementation-contract-reviewer`.
- After implementation and local verification, run a read-only implementation
  review focused on missed raw-area bypasses, no-audit behavior, and test gaps.
