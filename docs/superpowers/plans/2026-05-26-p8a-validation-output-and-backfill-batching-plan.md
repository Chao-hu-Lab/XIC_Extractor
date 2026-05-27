# P8a Validation Output And Backfill Batching Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce 85RAW validation turnaround without changing production alignment, peak picking, area integration, or final matrix semantics.

**Architecture:** Split validation delivery from human/debug delivery. Add a lean `validation-minimal` output level for machine gates, and add sidecar-only owner-backfill batch diagnostics to quantify batching inefficiency before any request-fusion or super-window optimization.

**Tech Stack:** Python, pytest, existing alignment output-level registry, existing timing recorder, existing owner_backfill chunking helpers.

---

## Contract

Downstream correction and statistics consume the final matrix, not a workbook:

- required for correction/statistics: `alignment_matrix.tsv`
- required for targeted ISTD benchmark: `alignment_matrix.tsv`, `alignment_review.tsv`, `alignment_cells.tsv`
- required for auditability: `alignment_run_metadata.json`, `timing.json`, `timing.live.json`, and `skipped_evidence_ledger.tsv` when P7 scope controls are used

`alignment_results.xlsx`, `review_report.html`, `owner_edge_evidence.tsv`,
`alignment_matrix_status.tsv`, `event_to_ms1_owner.tsv`, and
`ambiguous_ms1_owners.tsv` are debug or human/debug surfaces. They must not be
required for the 85RAW production-equivalent validation gate.

## Files

- Modify: `xic_extractor/alignment/output_levels.py`
  - Add `validation-minimal` output level with only matrix, review, and cells TSV.
- Modify: `scripts/run_alignment.py`
  - Accept `--output-level validation-minimal`.
  - Keep heartbeat/timing behavior unchanged.
- Modify: `xic_extractor/alignment/pipeline_outputs.py`
  - Ensure metadata and skipped-evidence sidecars still emit through existing P7 path.
- Modify: `xic_extractor/alignment/owner_backfill.py`
  - Add sidecar-friendly batch diagnostics helpers without changing chunk ordering or extraction behavior.
- Modify: `xic_extractor/alignment/pipeline.py`
  - Record owner-backfill batch diagnostic summary in timing metrics.
- Test: `tests/test_alignment_output_levels.py`
- Test: `tests/test_run_alignment.py`
- Test: `tests/test_alignment_pipeline_outputs.py`
- Test: `tests/test_alignment_owner_backfill.py`
- Test: `tests/test_alignment_pipeline_timing.py`

## Task 1: Add `validation-minimal` Output Contract

**Files:**
- Modify: `xic_extractor/alignment/output_levels.py`
- Modify: `scripts/run_alignment.py`
- Test: `tests/test_alignment_output_levels.py`
- Test: `tests/test_run_alignment.py`

- [ ] **Step 1: Write failing output-level test**

Add this test:

```python
def test_validation_minimal_output_level_is_machine_gate_surface_only():
    assert artifact_names_for_output_level("validation-minimal") == (
        "alignment_matrix.tsv",
        "alignment_review.tsv",
        "alignment_cells.tsv",
    )
```

- [ ] **Step 2: Run red test**

Run:

```powershell
python -m pytest tests\test_alignment_output_levels.py::test_validation_minimal_output_level_is_machine_gate_surface_only -q
```

Expected: fail because `validation-minimal` is not accepted.

- [ ] **Step 3: Implement output level**

Add `"validation-minimal"` to `AlignmentOutputLevel` and `_ARTIFACTS`.

The artifact tuple must be exactly:

```python
(
    "alignment_matrix.tsv",
    "alignment_review.tsv",
    "alignment_cells.tsv",
)
```

- [ ] **Step 4: Add CLI parsing test**

Add or update a `run_alignment` test that calls the CLI with
`--output-level validation-minimal` and asserts the captured `output_level`
passed to `run_alignment(...)` is `"validation-minimal"`.

- [ ] **Step 5: Run task tests**

Run:

```powershell
python -m pytest tests\test_alignment_output_levels.py tests\test_run_alignment.py -q
```

Expected: pass.

## Task 2: Prove Minimal Output Keeps Benchmark Contract

**Files:**
- Modify: `tests/test_alignment_pipeline_outputs.py`
- Modify: `tests/test_targeted_istd_benchmark.py` only if existing fixture assumptions require a new fixture helper.

- [ ] **Step 1: Write failing output path test**

Add a test that calls `resolve_alignment_outputs(...)` with
`output_level="validation-minimal"` and P7 skipped-ledger emission enabled.

Assert:

```python
assert outputs.matrix_tsv is not None
assert outputs.review_tsv is not None
assert outputs.cells_tsv is not None
assert outputs.workbook is None
assert outputs.review_html is None
assert outputs.edge_evidence_tsv is None
assert outputs.status_matrix_tsv is None
assert outputs.event_to_owner_tsv is None
assert outputs.ambiguous_owners_tsv is None
assert outputs.skipped_evidence_ledger_tsv is not None
assert outputs.run_metadata_json is not None
```

- [ ] **Step 2: Run red test**

Run:

```powershell
python -m pytest tests\test_alignment_pipeline_outputs.py::test_validation_minimal_outputs_keep_gate_artifacts_without_debug_surfaces -q
```

Expected: fail until output level is implemented.

- [ ] **Step 3: Keep implementation minimal**

No additional writer changes should be required because
`resolve_alignment_outputs(...)` already maps artifact names to paths and P7
sidecars are controlled by `emit_skipped_evidence_ledger`.

- [ ] **Step 4: Run task tests**

Run:

```powershell
python -m pytest tests\test_alignment_pipeline_outputs.py tests\test_targeted_istd_benchmark.py -q
```

Expected: pass.

## Task 3: Add Owner-Backfill Batch Diagnostic Metrics

**Files:**
- Modify: `xic_extractor/alignment/owner_backfill.py`
- Modify: `xic_extractor/alignment/pipeline.py`
- Test: `tests/test_alignment_owner_backfill.py`
- Test: `tests/test_alignment_pipeline_timing.py`

- [ ] **Step 1: Write failing helper tests**

Add tests for a helper that summarizes `_scan_window_aware_chunks(...)` output
without changing chunking:

```python
summary = summarize_owner_backfill_batches(
    source,
    items,
    chunk_size=64,
)
assert summary["request_count"] == 3
assert summary["chunk_count"] == 2
assert summary["max_chunk_size"] == 2
assert summary["mean_chunk_size"] == 1.5
assert summary["exact_scan_window_group_count"] == 2
```

Also test that the existing `_scan_window_aware_chunks(...)` result is unchanged
for the same fixture.

- [ ] **Step 2: Run red helper tests**

Run:

```powershell
python -m pytest tests\test_alignment_owner_backfill.py::test_owner_backfill_batch_summary_reports_exact_scan_window_efficiency -q
```

Expected: fail because the helper does not exist.

- [ ] **Step 3: Implement sidecar helper**

Add a pure helper in `owner_backfill.py`:

```python
def summarize_owner_backfill_batches(
    source: OwnerBackfillSource,
    items: tuple[_RequestItem, ...],
    *,
    chunk_size: int,
) -> dict[str, int | float]:
    ...
```

The helper must call `_scan_window_aware_chunks(...)` and calculate:

- `request_count`
- `chunk_count`
- `max_chunk_size`
- `mean_chunk_size`
- `exact_scan_window_group_count`

It must not call `extract_xic`, `extract_xic_many`, `find_peak_and_area`, or any
RAW API.

- [ ] **Step 4: Record summary in timing**

In `pipeline.py`, record aggregate diagnostic metrics in
`alignment.backfill_scope` or `alignment.owner_backfill` timing metrics:

- `estimated_extract_request_count`
- `estimated_exact_scan_window_group_count`
- `estimated_mean_batch_size`

Use request construction already available in memory; do not rescan RAW and do
not change extraction order.

- [ ] **Step 5: Run task tests**

Run:

```powershell
python -m pytest tests\test_alignment_owner_backfill.py tests\test_alignment_pipeline_timing.py -q
```

Expected: pass.

## Task 4: Validate With 8RAW Minimal Output

**Files:**
- No code changes unless tests expose a defect.

- [ ] **Step 1: Run focused unit shard**

Run:

```powershell
python -m pytest tests\test_alignment_output_levels.py tests\test_alignment_pipeline_outputs.py tests\test_alignment_owner_backfill.py tests\test_alignment_pipeline_timing.py tests\test_run_alignment.py -q
```

Expected: pass.

- [ ] **Step 2: Run 8RAW validation-minimal smoke**

Run:

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment `
  --discovery-batch-index output\phase1_p1_resolver_default_validation\discovery\dR\discovery_batch_index.csv `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir output\phase1_p8a_validation_minimal\alignment\8raw_validation_minimal `
  --output-level validation-minimal `
  --resolver-mode region_first_safe_merge `
  --backfill-scope production-equivalent `
  --audit-evidence-mode none `
  --performance-profile validation-fast `
  --timing-output output\phase1_p8a_validation_minimal\alignment\8raw_validation_minimal\timing.json `
  --timing-live-output output\phase1_p8a_validation_minimal\alignment\8raw_validation_minimal\timing.live.json
```

Expected:

- alignment run exits 0
- output dir contains `alignment_matrix.tsv`, `alignment_review.tsv`,
  `alignment_cells.tsv`, `skipped_evidence_ledger.tsv`,
  `alignment_run_metadata.json`, `timing.json`, and `timing.live.json`
- output dir does not contain `alignment_results.xlsx`, `review_report.html`,
  `owner_edge_evidence.tsv`, `alignment_matrix_status.tsv`,
  `event_to_ms1_owner.tsv`, or `ambiguous_ms1_owners.tsv`

- [ ] **Step 3: Run targeted benchmark on minimal output**

Run:

```powershell
python -m tools.diagnostics.targeted_istd_benchmark `
  --targeted-workbook output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge\xic_results_process_w4.xlsx `
  --alignment-dir output\phase1_p8a_validation_minimal\alignment\8raw_validation_minimal `
  --output-dir output\phase1_p8a_validation_minimal\diagnostics\targeted_istd_benchmark_8raw_validation_minimal
```

Expected: command produces benchmark summary artifacts. Benchmark status may
reflect existing area-gate behavior; this task only proves artifact sufficiency.

## Self-Review

- Spec coverage: covers the user's delivery contract concern, the benchmark
  dependency on `alignment_cells.tsv`, and the request-batching diagnostic
  question.
- Placeholder scan: no TBD/TODO placeholders.
- Behavior safety: no task changes peak selection, area integration, row
  promotion, backfill request eligibility, RAW backend, `.mzML`, or `ms1-index`.
