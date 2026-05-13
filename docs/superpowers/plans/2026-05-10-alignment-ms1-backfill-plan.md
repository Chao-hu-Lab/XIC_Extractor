# Alignment MS1 Backfill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert Plan 1 alignment clusters into a cluster x sample matrix by conservatively re-extracting MS1 XIC only for missing cells in reliable anchor clusters.

**Architecture:** `xic_extractor.alignment` stays a focused domain/backfill package. Plan 2 accepts already-opened XIC sources from the caller, reuses `find_peak_and_area`, and returns in-memory matrix models only. It does not open RAW files and does not write output files.

**Tech Stack:** Python, numpy, pytest, existing `AlignmentConfig` / `AlignmentCluster`, existing `ExtractionConfig`, existing `find_peak_and_area`.

---

## Core Decision

Plan 2 uses conservative backfill:

- `has_anchor=True` clusters: missing sample cells are checked with MS1 XIC backfill.
- `has_anchor=False` clusters: missing sample cells are `unchecked`, not `absent` or `rescued`.
- Detected cluster members are never re-extracted.

This protects v1 from turning weak discovery hypotheses into batch-wide false rescued peaks.

## Scope

In scope:

- Add matrix models: `CellStatus`, `AlignedCell`, `AlignmentMatrix`.
- Add `MS1BackfillSource` protocol.
- Add `backfill_alignment_matrix()`.
- Emit one cell per `(cluster, sample)` pair.
- Support `detected`, `rescued`, `absent`, `unchecked`.
- Synthetic tests and fake XIC sources only.

Out of scope:

- RAW opening / lifecycle.
- Discovery CSV reading.
- Alignment TSV/CSV output.
- CLI / GUI integration.
- RT drift correction.
- Known target annotation.
- Real RAW validation.

## Contracts

### Cell Status

```python
CellStatus = Literal["detected", "rescued", "absent", "unchecked"]
```

- `detected`: sample already has a `DiscoveryCandidate` in `cluster.members`.
- `rescued`: anchor cluster had no candidate for the sample, raw source was checked, and MS1 peak detection succeeded.
- `absent`: anchor cluster had no candidate for the sample, raw source was checked, and MS1 peak detection failed.
- `unchecked`: no check was performed or a check could not be completed.

`absent` must only mean "checked and no peak." Missing RAW/source errors are `unchecked`.

### Backfill Window

For anchor-cluster missing cells:

- XIC m/z: `cluster.cluster_center_mz`
- XIC ppm tolerance: `alignment_config.preferred_ppm`
- RT window: `cluster.cluster_center_rt +/- alignment_config.max_rt_sec / 60`
- Peak picker: `find_peak_and_area(..., preferred_rt=cluster.cluster_center_rt, strict_preferred_rt=False)`
- Rescue guard: rescued apex must remain within `alignment_config.max_rt_sec` of cluster center.

### Traceability

`AlignedCell` must contain enough fields for Plan 3 output without re-running peak detection:

```python
@dataclass(frozen=True)
class AlignedCell:
    sample_stem: str
    cluster_id: str
    status: CellStatus
    area: float | None
    apex_rt: float | None
    height: float | None
    peak_start_rt: float | None
    peak_end_rt: float | None
    rt_delta_sec: float | None
    trace_quality: str
    scan_support_score: float | None
    source_candidate_id: str | None
    source_raw_file: Path | None
    reason: str
```

Use `area`, not `intensity`, as the matrix value field.

### Matrix Shape

```python
@dataclass(frozen=True)
class AlignmentMatrix:
    clusters: tuple[AlignmentCluster, ...]
    cells: tuple[AlignedCell, ...]
    sample_order: tuple[str, ...]
```

Rules:

- `sample_order` must be unique.
- Every detected member sample must exist in `sample_order`.
- A cluster cannot contain two primary members with the same `sample_stem`.
- Cell order is cluster input order, then `sample_order`.
- Backfill does not modify clusters, centers, members, anchors, or IDs.

## File Structure

Create:

- `xic_extractor/alignment/matrix.py`
- `xic_extractor/alignment/backfill.py`
- `tests/test_alignment_matrix.py`
- `tests/test_alignment_backfill.py`

Modify:

- `xic_extractor/alignment/__init__.py`
- `docs/superpowers/plans/2026-05-10-untargeted-cross-sample-alignment.md`

`xic_extractor/alignment/backfill.py` must not import RAW readers, CLI modules, GUI, workbook output, HTML report code, discovery pipeline orchestration, or CSV writers.

## Public API

After Plan 2, `xic_extractor.alignment` exports:

- `AlignmentConfig`
- `AlignmentCluster`
- `AlignedCell`
- `AlignmentMatrix`
- `CellStatus`
- `cluster_candidates`
- `backfill_alignment_matrix`

Function signature:

```python
def backfill_alignment_matrix(
    clusters: tuple[AlignmentCluster, ...],
    *,
    sample_order: tuple[str, ...],
    raw_sources: Mapping[str, MS1BackfillSource],
    alignment_config: AlignmentConfig,
    peak_config: ExtractionConfig,
) -> AlignmentMatrix:
    ...
```

The caller owns RAW opening and closing. Plan 3 will build `raw_sources`.

## Tasks

### Task 0: Dependency Check

**Files:**
- Read: `xic_extractor/alignment/config.py`
- Read: `xic_extractor/alignment/models.py`
- Read: `xic_extractor/alignment/clustering.py`

- [ ] Confirm Plan 1 files exist.

Run:

```powershell
Test-Path xic_extractor\alignment\config.py
Test-Path xic_extractor\alignment\models.py
Test-Path xic_extractor\alignment\clustering.py
```

Expected: all three output `True`.

- [ ] Confirm Plan 1 tests are green.

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_config.py tests/test_alignment_models.py tests/test_alignment_compatibility.py tests/test_alignment_clustering.py -v
```

Expected: PASS. If not, stop and complete Plan 1 first.

### Task 1: Matrix Models

**Files:**
- Create: `xic_extractor/alignment/matrix.py`
- Modify: `xic_extractor/alignment/__init__.py`
- Test: `tests/test_alignment_matrix.py`

- [ ] Write red tests:
  - `test_cell_status_contract_values`
  - `test_aligned_cell_exposes_traceability_fields`
  - `test_alignment_matrix_preserves_cluster_and_sample_order`

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_matrix.py -v
```

Expected red: missing `xic_extractor.alignment.matrix`.

- [ ] Implement `CellStatus`, `AlignedCell`, `AlignmentMatrix`.
- [ ] Export `AlignedCell`, `AlignmentMatrix`, `CellStatus` from `xic_extractor/alignment/__init__.py`.
- [ ] Re-run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_matrix.py -v
```

Expected: PASS.

- [ ] Commit:

```powershell
git add xic_extractor\alignment\matrix.py xic_extractor\alignment\__init__.py tests\test_alignment_matrix.py
git commit -m "feat(alignment): add matrix cell models"
```

### Task 2: Backfill Validation Shell

**Files:**
- Create: `xic_extractor/alignment/backfill.py`
- Test: `tests/test_alignment_backfill.py`

- [ ] Write red tests using fake `AlignmentCluster` and `DiscoveryCandidate` factories:
  - `test_backfill_rejects_duplicate_sample_order`
  - `test_backfill_rejects_member_sample_missing_from_sample_order`
  - `test_backfill_rejects_duplicate_members_for_same_sample`
  - `test_empty_clusters_returns_empty_matrix_with_sample_order`

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_backfill.py -v
```

Expected red: missing `xic_extractor.alignment.backfill`.

- [ ] Implement:
  - `MS1BackfillSource` protocol with `extract_xic(mz, rt_min, rt_max, ppm_tol)`.
  - `backfill_alignment_matrix()` validation shell.
  - `AlignmentMatrix(clusters=clusters, cells=(), sample_order=sample_order)` for empty clusters.

- [ ] Re-run focused tests:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_backfill.py -v
```

Expected: validation tests pass; later status tests may not exist yet.

- [ ] Commit:

```powershell
git add xic_extractor\alignment\backfill.py tests\test_alignment_backfill.py
git commit -m "feat(alignment): add backfill input validation"
```

### Task 3: Detected And Non-Anchor Cells

**Files:**
- Modify: `xic_extractor/alignment/backfill.py`
- Test: `tests/test_alignment_backfill.py`

- [ ] Add red tests:
  - `test_detected_cell_uses_existing_candidate_without_raw_extraction`
  - `test_non_anchor_missing_sample_is_unchecked_without_raw_extraction`
  - `test_matrix_emits_one_cell_per_cluster_sample_pair`

Assertions:

- detected cell copies `ms1_area`, `ms1_apex_rt`, `ms1_height`, peak start/end, scan support, candidate ID, raw file.
- detected cell `rt_delta_sec` is `(candidate.ms1_apex_rt - cluster.cluster_center_rt) * 60`.
- non-anchor missing cell is `unchecked` with reason `backfill skipped for non-anchor cluster`.
- fake raw source receives no calls for detected cells or non-anchor missing cells.

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_backfill.py -v
```

Expected red: cells are missing or status branches are incomplete.

- [ ] Implement detected cells and non-anchor unchecked cells.
- [ ] Re-run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_backfill.py -v
```

Expected: PASS for validation, detected, non-anchor, and shape tests.

- [ ] Commit:

```powershell
git add xic_extractor\alignment\backfill.py tests\test_alignment_backfill.py
git commit -m "feat(alignment): emit detected and skipped matrix cells"
```

### Task 4: Anchor Cluster MS1 Backfill

**Files:**
- Modify: `xic_extractor/alignment/backfill.py`
- Modify: `xic_extractor/alignment/__init__.py`
- Test: `tests/test_alignment_backfill.py`

- [ ] Add red tests:
  - `test_anchor_missing_sample_extracts_cluster_center_xic`
  - `test_anchor_missing_sample_rescues_peak`
  - `test_anchor_missing_sample_no_peak_is_absent`
  - `test_anchor_missing_sample_without_raw_source_is_unchecked`
  - `test_anchor_backfill_peak_outside_max_rt_is_absent`

Assertions:

- fake source call equals `(cluster_center_mz, center_rt - max_rt_sec/60, center_rt + max_rt_sec/60, preferred_ppm)`.
- rescued cell has `status="rescued"`, area/apex/height/start/end filled, `source_candidate_id=None`, and reason `MS1 peak rescued at cluster center`.
- no-peak result is `absent`, not `unchecked`.
- missing source is `unchecked`, not `absent`.

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_backfill.py -v
```

Expected red: anchor missing cells are not backfilled yet.

- [ ] Implement anchor backfill:
  - extract XIC with `preferred_ppm`.
  - call `find_peak_and_area` with cluster center as preferred RT.
  - use `peak_config.resolver_min_scans` for scan-support denominator.
  - classify `OK` as `rescued` only when apex is within `max_rt_sec`.
  - classify non-OK as `absent`.
  - classify missing source, malformed trace, or extraction exception as `unchecked`.
- [ ] Export `backfill_alignment_matrix` from `xic_extractor/alignment/__init__.py`.
- [ ] Re-run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_backfill.py tests/test_alignment_matrix.py -v
```

Expected: PASS.

- [ ] Commit:

```powershell
git add xic_extractor\alignment\backfill.py xic_extractor\alignment\__init__.py tests\test_alignment_backfill.py
git commit -m "feat(alignment): backfill anchor clusters with MS1 XIC"
```

### Task 5: Package Boundary And Docs Sync

**Files:**
- Modify: `docs/superpowers/plans/2026-05-10-untargeted-cross-sample-alignment.md`
- Test: `tests/test_alignment_boundaries.py` or existing package-boundary test file if one exists.

- [ ] Add/extend boundary tests:
  - `xic_extractor.alignment.backfill` does not import `xic_extractor.raw_reader`.
  - it does not import CLI scripts, GUI, workbook output, HTML report, discovery pipeline, or CSV writers.
  - `xic_extractor.alignment` exports the Plan 2 public API names.

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_boundaries.py -v
```

Expected red if the boundary test file or exports are missing.

- [ ] Implement missing export or boundary fixes.
- [ ] Update roadmap index:
  - Plan 2 links to this file.
  - Plan 2 model uses `area`, not `intensity`.
  - Conservative anchor-only backfill is explicitly stated.
- [ ] Check stale wording:

```powershell
rg -n "intensity: float \\| None" docs\superpowers\plans\2026-05-10-untargeted-cross-sample-alignment.md docs\superpowers\plans\2026-05-10-alignment-ms1-backfill-plan.md
rg -n "Cross-Sample MS1 Backfill.*pending" docs\superpowers\plans\2026-05-10-untargeted-cross-sample-alignment.md
```

Expected: no matches.

- [ ] Re-run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_boundaries.py tests/test_alignment_backfill.py tests/test_alignment_matrix.py -v
```

Expected: PASS.

- [ ] Commit:

```powershell
git add xic_extractor\alignment\__init__.py tests\test_alignment_boundaries.py docs\superpowers\plans\2026-05-10-untargeted-cross-sample-alignment.md docs\superpowers\plans\2026-05-10-alignment-ms1-backfill-plan.md
git commit -m "docs(alignment): define MS1 backfill contract"
```

## Validation

Run after implementation:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_matrix.py tests/test_alignment_backfill.py tests/test_alignment_boundaries.py -v
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_config.py tests/test_alignment_models.py tests/test_alignment_compatibility.py tests/test_alignment_clustering.py -v
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```

No real RAW validation is required for Plan 2. Plan 3 owns RAW opening and CLI-level validation.

## Acceptance Criteria

- Exactly one `AlignedCell` exists for each `(cluster, sample)` pair.
- `detected` cells come only from Plan 1 cluster members.
- `rescued` cells come only from anchor-cluster MS1 backfill.
- `absent` means checked and no peak.
- `unchecked` means skipped or unable to check.
- Non-anchor clusters are detected-only.
- Backfill uses cluster center, `preferred_ppm`, and `max_rt_sec`.
- Backfill does not mutate clusters or affect cluster identity.
- Alignment backfill has no RAW reader, CLI, GUI, workbook, report, discovery pipeline, or CSV writer dependency.

## Self-Review Notes

- This plan is intentionally smaller than the earlier draft to reduce execution context cost.
- Plan 2 does not define output files; Plan 3 owns schema and CLI.
- Plan 2 does not validate real RAW files; fake XIC sources cover the domain behavior.
