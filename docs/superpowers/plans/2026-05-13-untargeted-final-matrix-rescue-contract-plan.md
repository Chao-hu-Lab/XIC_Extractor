# Untargeted Final Matrix Rescue Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the untargeted alignment production workbook and matrix outputs match the final-matrix contract: accepted numeric values only in the primary matrix, invalid/review-only rows excluded from that primary matrix, and rescue/blank reasoning preserved in audit diagnostics.

**Architecture:** Add a small production-decision layer inside `xic_extractor/alignment/` that classifies each alignment cell and row before writers render outputs. Keep the underlying `AlignmentMatrix` and debug TSVs intact so diagnostics remain complete. Wire TSV/XLSX writers and guardrails through the decision layer, then add a reproducible internal-standard false-missing validation fixture.

**Tech Stack:** Python dataclasses, existing `AlignmentMatrix` model, `AlignmentConfig`, `openpyxl`, TSV/CSV writers, `pytest`.

---

## Prerequisites

Use this worktree:

```text
C:\Users\user\Desktop\XIC_Extractor\.worktrees\untargeted-discovery-v1-implementation
```

The spec this plan implements is:

```text
docs/superpowers/specs/2026-05-13-untargeted-final-matrix-and-rescue-evidence-spec.md
```

Keep these rules stable:

- Production matrix sample cells contain only accepted numeric area values or blanks.
- Production matrix rows require at least one accepted quantitative cell and valid row-level identity support.
- Diagnostics keep all raw status, rescue tier, blank reason, and row flags.
- Targeted labels are validation fixtures only, not production identity rules.

## File Structure

- Create `xic_extractor/alignment/production_decisions.py`
  - Classifies cell write/blank decisions, rescue tiers, blank reasons, and row-level flags.
  - Owns primary matrix row inclusion.
- Modify `xic_extractor/alignment/output_rows.py`
  - Reuse production decisions for matrix area rendering without changing debug formatting helpers.
- Modify `xic_extractor/alignment/tsv_writer.py`
  - Use production row filtering in `alignment_matrix.tsv`.
  - Keep `alignment_cells.tsv` and `alignment_matrix_status.tsv` complete.
  - Add production decision fields to `alignment_review.tsv`.
- Modify `xic_extractor/alignment/xlsx_writer.py`
  - Use production row filtering in workbook `Matrix`.
  - Add an `Audit` sheet between `Review` and `Metadata`.
- Modify `xic_extractor/alignment/pipeline.py`
  - Pass `AlignmentConfig` to TSV/XLSX production writers.
- Modify `tools/diagnostics/untargeted_alignment_guardrails.py`
  - Split broad rescue/backfill guardrails into acceptance, review, identity, duplicate, negative checkpoint, and ISTD recovery metrics.
- Create `tools/diagnostics/build_istd_false_missing_fixture.py`
  - Converts the old matrix and targeted workbook evidence into a small reproducible CSV.
- Create `tests/fixtures/untargeted_alignment/istd_false_missing_fixture.csv`
  - Committed fixture with the 16 old-missing internal-standard cells and targeted evidence.
- Add/update tests:
  - `tests/test_alignment_production_decisions.py`
  - `tests/test_alignment_tsv_writer.py`
  - `tests/test_alignment_xlsx_writer.py`
  - `tests/test_alignment_pipeline.py`
  - `tests/test_untargeted_alignment_guardrails.py`
  - `tests/test_istd_false_missing_fixture.py`

## Task 1: Add Production Decision Model

**Files:**
- Create: `xic_extractor/alignment/production_decisions.py`
- Test: `tests/test_alignment_production_decisions.py`

- [ ] **Step 1: Write failing tests for cell decisions and row inclusion**

Create `tests/test_alignment_production_decisions.py`:

```python
import math
from pathlib import Path
from types import SimpleNamespace

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.production_decisions import (
    build_production_decisions,
)


def test_detected_and_supported_rescue_write_numeric_values():
    matrix = _matrix(
        clusters=(_feature("FAM001", evidence="single_sample_local_owner"),),
        cells=(
            _cell("s1", "FAM001", "detected", 100.0),
            _cell("s2", "FAM001", "rescued", 90.0),
        ),
        sample_order=("s1", "s2"),
    )

    decisions = build_production_decisions(matrix, AlignmentConfig())

    assert decisions.cell("FAM001", "s1").write_matrix_value is True
    assert decisions.cell("FAM001", "s1").production_status == "detected"
    assert decisions.cell("FAM001", "s1").matrix_value == 100.0
    assert decisions.cell("FAM001", "s2").write_matrix_value is True
    assert decisions.cell("FAM001", "s2").production_status == "accepted_rescue"
    assert decisions.cell("FAM001", "s2").rescue_tier == "accepted_rescue"
    assert decisions.row("FAM001").include_in_primary_matrix is True
    assert decisions.row("FAM001").row_flags == ("rescue_heavy",)


def test_rescue_without_identity_support_is_review_only_and_row_is_excluded():
    matrix = _matrix(
        clusters=(_feature("FAM001", evidence="", has_anchor=False),),
        cells=(
            _cell("s1", "FAM001", "rescued", 90.0),
            _cell("s2", "FAM001", "absent", None),
        ),
        sample_order=("s1", "s2"),
    )

    decisions = build_production_decisions(matrix, AlignmentConfig())

    assert decisions.cell("FAM001", "s1").write_matrix_value is False
    assert decisions.cell("FAM001", "s1").production_status == "review_rescue"
    assert decisions.cell("FAM001", "s1").blank_reason == "missing_row_identity_support"
    assert decisions.row("FAM001").include_in_primary_matrix is False
    assert decisions.row("FAM001").row_flags == ("rescue_only_review",)


def test_duplicate_ambiguous_absent_unchecked_and_invalid_areas_are_blank():
    matrix = _matrix(
        clusters=(_feature("FAM001", evidence="single_sample_local_owner"),),
        cells=(
            _cell("duplicate", "FAM001", "duplicate_assigned", 10.0),
            _cell("ambiguous", "FAM001", "ambiguous_ms1_owner", 20.0),
            _cell("absent", "FAM001", "absent", None),
            _cell("unchecked", "FAM001", "unchecked", None),
            _cell("zero", "FAM001", "detected", 0.0),
            _cell("nan", "FAM001", "detected", math.nan),
        ),
        sample_order=("duplicate", "ambiguous", "absent", "unchecked", "zero", "nan"),
    )

    decisions = build_production_decisions(matrix, AlignmentConfig())

    assert decisions.cell("FAM001", "duplicate").blank_reason == "duplicate_loser"
    assert decisions.cell("FAM001", "ambiguous").blank_reason == "ambiguous_ms1_owner"
    assert decisions.cell("FAM001", "absent").blank_reason == "absent"
    assert decisions.cell("FAM001", "unchecked").blank_reason == "unchecked"
    assert decisions.cell("FAM001", "zero").blank_reason == "invalid_area"
    assert decisions.cell("FAM001", "nan").blank_reason == "invalid_area"
    assert decisions.row("FAM001").include_in_primary_matrix is False


def test_identity_anchor_lost_row_is_excluded_until_review_passes():
    matrix = _matrix(
        clusters=(_feature("FAM001", evidence="single_sample_local_owner"),),
        cells=(
            _cell("s1", "FAM001", "duplicate_assigned", 100.0),
            _cell("s2", "FAM001", "rescued", 90.0),
        ),
        sample_order=("s1", "s2"),
    )

    decisions = build_production_decisions(matrix, AlignmentConfig())

    assert decisions.cell("FAM001", "s2").production_status == "review_rescue"
    assert decisions.row("FAM001").include_in_primary_matrix is False
    assert decisions.row("FAM001").row_flags == (
        "rescue_only_review",
        "duplicate_claim_pressure",
        "identity_anchor_lost",
    )


def _matrix(
    *,
    clusters: tuple[object, ...],
    cells: tuple[AlignedCell, ...],
    sample_order: tuple[str, ...],
) -> AlignmentMatrix:
    return AlignmentMatrix(clusters=clusters, cells=cells, sample_order=sample_order)


def _feature(
    feature_family_id: str,
    *,
    evidence: str,
    has_anchor: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        feature_family_id=feature_family_id,
        neutral_loss_tag="DNA_dR",
        family_center_mz=500.123,
        family_center_rt=8.49,
        family_product_mz=384.076,
        family_observed_neutral_loss_da=116.047,
        has_anchor=has_anchor,
        event_cluster_ids=("OWN-s1-000001",),
        event_member_count=1,
        evidence=evidence,
        review_only=False,
    )


def _cell(
    sample_stem: str,
    cluster_id: str,
    status: str,
    area: float | None,
) -> AlignedCell:
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=cluster_id,
        status=status,  # type: ignore[arg-type]
        area=area,
        apex_rt=8.49 if area is not None else None,
        height=100.0 if area is not None else None,
        peak_start_rt=8.4 if area is not None else None,
        peak_end_rt=8.6 if area is not None else None,
        rt_delta_sec=0.0 if area is not None else None,
        trace_quality="clean" if area is not None else status,
        scan_support_score=0.8 if area is not None else None,
        source_candidate_id=f"{sample_stem}#1" if status == "detected" else None,
        source_raw_file=Path(f"{sample_stem}.raw") if status == "detected" else None,
        reason=(
            "duplicate MS1 peak claim; winner=FAM000000; original_status=detected"
            if status == "duplicate_assigned"
            else status
        ),
    )
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_production_decisions.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'xic_extractor.alignment.production_decisions'`.

- [ ] **Step 3: Implement production decisions**

Create `xic_extractor/alignment/production_decisions.py`:

```python
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.output_rows import cells_by_cluster, row_id

ProductionStatus = Literal[
    "detected",
    "accepted_rescue",
    "review_rescue",
    "rejected_rescue",
    "blank",
]
RescueTier = Literal["", "accepted_rescue", "review_rescue", "rejected_rescue"]


@dataclass(frozen=True)
class ProductionCellDecision:
    feature_family_id: str
    sample_stem: str
    raw_status: str
    production_status: ProductionStatus
    rescue_tier: RescueTier
    write_matrix_value: bool
    matrix_value: float | None
    blank_reason: str


@dataclass(frozen=True)
class ProductionRowDecision:
    feature_family_id: str
    include_in_primary_matrix: bool
    accepted_cell_count: int
    detected_count: int
    accepted_rescue_count: int
    review_rescue_count: int
    duplicate_assigned_count: int
    row_flags: tuple[str, ...]


@dataclass(frozen=True)
class ProductionDecisionSet:
    cells: dict[tuple[str, str], ProductionCellDecision]
    rows: dict[str, ProductionRowDecision]

    def cell(self, feature_family_id: str, sample_stem: str) -> ProductionCellDecision:
        return self.cells[(feature_family_id, sample_stem)]

    def row(self, feature_family_id: str) -> ProductionRowDecision:
        return self.rows[feature_family_id]


def build_production_decisions(
    matrix: AlignmentMatrix,
    config: AlignmentConfig,
) -> ProductionDecisionSet:
    clusters_by_id = {row_id(cluster): cluster for cluster in matrix.clusters}
    grouped_cells = cells_by_cluster(matrix)
    cell_decisions: dict[tuple[str, str], ProductionCellDecision] = {}
    row_decisions: dict[str, ProductionRowDecision] = {}

    for cluster in matrix.clusters:
        cluster_id = row_id(cluster)
        cluster_cells = grouped_cells.get(cluster_id, ())
        row_has_identity = _has_row_identity_support(cluster)
        row_anchor_lost = _identity_anchor_lost(cluster_cells)

        for cell in cluster_cells:
            decision = _cell_decision(
                cell,
                cluster=clusters_by_id[cluster_id],
                config=config,
                row_has_identity=row_has_identity and not row_anchor_lost,
            )
            cell_decisions[(cell.cluster_id, cell.sample_stem)] = decision

        cluster_decisions = tuple(
            cell_decisions[(cell.cluster_id, cell.sample_stem)]
            for cell in cluster_cells
        )
        row_decisions[cluster_id] = _row_decision(
            cluster_id,
            cluster_cells,
            cluster_decisions,
            row_anchor_lost=row_anchor_lost,
        )

    return ProductionDecisionSet(cells=cell_decisions, rows=row_decisions)


def _cell_decision(
    cell: AlignedCell,
    *,
    cluster: Any,
    config: AlignmentConfig,
    row_has_identity: bool,
) -> ProductionCellDecision:
    if cell.status == "detected":
        area = _valid_area(cell.area)
        if area is None:
            return _blank(cell, "detected", "", "invalid_area")
        if not row_has_identity:
            return _blank(cell, "blank", "", "missing_row_identity_support")
        return ProductionCellDecision(
            feature_family_id=cell.cluster_id,
            sample_stem=cell.sample_stem,
            raw_status=cell.status,
            production_status="detected",
            rescue_tier="",
            write_matrix_value=True,
            matrix_value=area,
            blank_reason="",
        )
    if cell.status == "rescued":
        return _rescue_decision(
            cell,
            config=config,
            row_has_identity=row_has_identity,
        )
    if cell.status == "duplicate_assigned":
        return _blank(cell, "blank", "", "duplicate_loser")
    if cell.status == "ambiguous_ms1_owner":
        return _blank(cell, "blank", "", "ambiguous_ms1_owner")
    if cell.status == "absent":
        return _blank(cell, "blank", "", "absent")
    if cell.status == "unchecked":
        return _blank(cell, "blank", "", "unchecked")
    return _blank(cell, "blank", "", f"unsupported_status:{cell.status}")


def _rescue_decision(
    cell: AlignedCell,
    *,
    config: AlignmentConfig,
    row_has_identity: bool,
) -> ProductionCellDecision:
    area = _valid_area(cell.area)
    if area is None:
        return _blank(cell, "rejected_rescue", "rejected_rescue", "invalid_area")
    if not row_has_identity:
        return _blank(
            cell,
            "review_rescue",
            "review_rescue",
            "missing_row_identity_support",
        )
    if not _has_complete_peak(cell):
        return _blank(cell, "review_rescue", "review_rescue", "incomplete_peak")
    if cell.rt_delta_sec is None or abs(cell.rt_delta_sec) > config.max_rt_sec:
        return _blank(cell, "review_rescue", "review_rescue", "rt_outside_max")
    return ProductionCellDecision(
        feature_family_id=cell.cluster_id,
        sample_stem=cell.sample_stem,
        raw_status=cell.status,
        production_status="accepted_rescue",
        rescue_tier="accepted_rescue",
        write_matrix_value=True,
        matrix_value=area,
        blank_reason="",
    )


def _row_decision(
    cluster_id: str,
    cells: tuple[AlignedCell, ...],
    decisions: tuple[ProductionCellDecision, ...],
    *,
    row_anchor_lost: bool,
) -> ProductionRowDecision:
    detected_count = sum(1 for cell in cells if cell.status == "detected")
    accepted_rescue_count = sum(
        1 for decision in decisions if decision.production_status == "accepted_rescue"
    )
    review_rescue_count = sum(
        1 for decision in decisions if decision.production_status == "review_rescue"
    )
    duplicate_count = sum(1 for cell in cells if cell.status == "duplicate_assigned")
    accepted_cell_count = sum(1 for decision in decisions if decision.write_matrix_value)

    flags: list[str] = []
    if accepted_rescue_count > detected_count and detected_count > 0:
        flags.append("rescue_heavy")
    if accepted_cell_count == 0 and review_rescue_count > 0:
        flags.append("rescue_only_review")
    if duplicate_count > 0:
        flags.append("duplicate_claim_pressure")
    if row_anchor_lost:
        flags.append("identity_anchor_lost")

    return ProductionRowDecision(
        feature_family_id=cluster_id,
        include_in_primary_matrix=accepted_cell_count > 0 and not row_anchor_lost,
        accepted_cell_count=accepted_cell_count,
        detected_count=detected_count,
        accepted_rescue_count=accepted_rescue_count,
        review_rescue_count=review_rescue_count,
        duplicate_assigned_count=duplicate_count,
        row_flags=tuple(flags),
    )


def _blank(
    cell: AlignedCell,
    production_status: ProductionStatus,
    rescue_tier: RescueTier,
    blank_reason: str,
) -> ProductionCellDecision:
    return ProductionCellDecision(
        feature_family_id=cell.cluster_id,
        sample_stem=cell.sample_stem,
        raw_status=cell.status,
        production_status=production_status,
        rescue_tier=rescue_tier,
        write_matrix_value=False,
        matrix_value=None,
        blank_reason=blank_reason,
    )


def _valid_area(value: float | None) -> float | None:
    if value is None or not math.isfinite(value) or value <= 0:
        return None
    return float(value)


def _has_complete_peak(cell: AlignedCell) -> bool:
    return all(
        _finite(value)
        for value in (
            cell.apex_rt,
            cell.height,
            cell.peak_start_rt,
            cell.peak_end_rt,
        )
    )


def _finite(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _has_row_identity_support(cluster: Any) -> bool:
    if bool(getattr(cluster, "review_only", False)):
        return False
    evidence = _family_evidence(cluster)
    if evidence in {"single_sample_local_owner", "owner_identity"}:
        return True
    if evidence.startswith("owner_complete_link;"):
        return True
    if evidence.startswith("cid_nl_only;"):
        return True
    if bool(getattr(cluster, "has_anchor", False)):
        return True
    return False


def _identity_anchor_lost(cells: tuple[AlignedCell, ...]) -> bool:
    has_detected = any(cell.status == "detected" for cell in cells)
    if has_detected:
        return False
    has_duplicate = any(
        cell.status == "duplicate_assigned"
        and "original_status=detected" in (cell.reason or "")
        for cell in cells
    )
    has_rescue = any(cell.status == "rescued" for cell in cells)
    return has_duplicate and has_rescue


def _family_evidence(cluster: Any) -> str:
    if hasattr(cluster, "evidence"):
        return str(cluster.evidence)
    if hasattr(cluster, "fold_evidence"):
        return str(cluster.fold_evidence)
    return ""


def _event_member_count(cluster: Any) -> int:
    if hasattr(cluster, "event_member_count"):
        return int(cluster.event_member_count)
    if hasattr(cluster, "members"):
        return len(cluster.members) + int(getattr(cluster, "folded_member_count", 0))
    return 0
```

- [ ] **Step 4: Run production-decision tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_production_decisions.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add xic_extractor/alignment/production_decisions.py tests/test_alignment_production_decisions.py
git commit -m "feat: classify untargeted production matrix decisions"
```

## Task 2: Apply Production Decisions To Matrix TSV

**Files:**
- Modify: `xic_extractor/alignment/output_rows.py`
- Modify: `xic_extractor/alignment/tsv_writer.py`
- Modify: `tests/test_alignment_tsv_writer.py`

- [ ] **Step 1: Add failing TSV tests for row filtering and rescue review blanks**

First update the `REVIEW_COLUMNS` constant in `tests/test_alignment_tsv_writer.py` by inserting these values immediately after `"present_rate"`:

```python
    "accepted_cell_count",
    "accepted_rescue_count",
    "review_rescue_count",
    "include_in_primary_matrix",
    "row_flags",
```

In `test_write_alignment_review_tsv_columns_counts_rates_and_reason`, add these fields to the expected row immediately after `"present_rate": "0.5"`:

```python
        "accepted_cell_count": "2",
        "accepted_rescue_count": "1",
        "review_rescue_count": "0",
        "include_in_primary_matrix": "TRUE",
        "row_flags": "",
```

In `test_write_alignment_matrix_tsv_blanks_missing_and_invalid_areas`, change the matrix cluster from `_cluster()` to:

```python
        clusters=(_cluster(fold_evidence="owner_complete_link;owner_count=2"),),
```

This keeps that existing test focused on cell-value rendering while the new tests below cover review-only rescue exclusion.

Append to `tests/test_alignment_tsv_writer.py`:

```python
def test_write_alignment_matrix_tsv_excludes_rows_without_accepted_cells(
    tmp_path: Path,
):
    from xic_extractor.alignment.tsv_writer import write_alignment_matrix_tsv

    matrix = AlignmentMatrix(
        clusters=(
            _cluster(cluster_id="ALN000001", fold_evidence="owner_complete_link;owner_count=2"),
            _cluster(cluster_id="ALN000002", has_anchor=False, fold_evidence=""),
            _cluster(cluster_id="ALN000003", fold_evidence="owner_complete_link;owner_count=2"),
        ),
        cells=(
            _cell("sample-a", "detected", cluster_id="ALN000001", area=100.0),
            _cell("sample-a", "rescued", cluster_id="ALN000002", area=200.0),
            _cell("sample-a", "duplicate_assigned", cluster_id="ALN000003", area=300.0),
        ),
        sample_order=("sample-a",),
    )

    rows = _read_tsv(write_alignment_matrix_tsv(tmp_path / "matrix.tsv", matrix))

    assert [row["feature_family_id"] for row in rows] == ["ALN000001"]
    assert rows[0]["sample-a"] == "100"


def test_write_alignment_review_tsv_includes_production_decision_columns(
    tmp_path: Path,
):
    from xic_extractor.alignment.tsv_writer import write_alignment_review_tsv

    matrix = AlignmentMatrix(
        clusters=(_cluster(has_anchor=False, fold_evidence=""),),
        cells=(_cell("sample-a", "rescued", area=200.0),),
        sample_order=("sample-a",),
    )

    rows = _read_tsv(write_alignment_review_tsv(tmp_path / "review.tsv", matrix))

    assert rows[0]["accepted_cell_count"] == "0"
    assert rows[0]["accepted_rescue_count"] == "0"
    assert rows[0]["review_rescue_count"] == "1"
    assert rows[0]["include_in_primary_matrix"] == "FALSE"
    assert rows[0]["row_flags"] == "rescue_only_review"
```

- [ ] **Step 2: Run TSV tests and verify they fail**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_tsv_writer.py -v
```

Expected: FAIL because matrix TSV still writes all rows and review TSV lacks production decision columns.

- [ ] **Step 3: Update output-row helper for production values**

Modify `xic_extractor/alignment/output_rows.py` by adding this import guard and function. Keep the existing `matrix_area()` function for callers that still need raw detected/rescued behavior. Do not runtime-import `production_decisions.py` here, because `production_decisions.py` already imports `cells_by_cluster()` and `row_id()` from this module.

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from xic_extractor.alignment.production_decisions import ProductionCellDecision
```

Add below `matrix_area()`:

```python
def production_matrix_area(decision: ProductionCellDecision | None) -> str:
    if decision is None or not decision.write_matrix_value:
        return ""
    assert decision.matrix_value is not None
    return format_float(decision.matrix_value)
```

- [ ] **Step 4: Update TSV writer to use decisions**

Modify imports in `xic_extractor/alignment/tsv_writer.py`:

```python
from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.production_decisions import build_production_decisions
```

Replace the `output_rows` import of `matrix_area` with `production_matrix_area`:

```python
from xic_extractor.alignment.output_rows import (
    cells_by_cluster,
    count_status,
    escape_excel_formula,
    format_value,
    production_matrix_area,
    row_id,
    safe_rate,
)
```

Extend `ALIGNMENT_REVIEW_COLUMNS` by adding these columns after `present_rate`:

```python
    "accepted_cell_count",
    "accepted_rescue_count",
    "review_rescue_count",
    "include_in_primary_matrix",
    "row_flags",
```

Change `write_alignment_matrix_tsv` signature and body:

```python
def write_alignment_matrix_tsv(
    path: Path,
    matrix: AlignmentMatrix,
    *,
    alignment_config: AlignmentConfig | None = None,
) -> Path:
    config = alignment_config or AlignmentConfig()
    decisions = build_production_decisions(matrix, config)
    columns = (
        "feature_family_id",
        "neutral_loss_tag",
        "family_center_mz",
        "family_center_rt",
        *matrix.sample_order,
    )
    rows: list[dict[str, object]] = []
    grouped_cells = cells_by_cluster(matrix)
    for cluster in matrix.clusters:
        cluster_id = row_id(cluster)
        row_decision = decisions.row(cluster_id)
        if not row_decision.include_in_primary_matrix:
            continue
        cells = grouped_cells.get(cluster_id, ())
        cells_by_sample = {cell.sample_stem: cell for cell in cells}
        row: dict[str, object] = {
            "feature_family_id": cluster_id,
            "neutral_loss_tag": cluster.neutral_loss_tag,
            "family_center_mz": format_value(_family_center_mz(cluster)),
            "family_center_rt": format_value(_family_center_rt(cluster)),
        }
        for sample_stem in matrix.sample_order:
            cell = cells_by_sample.get(sample_stem)
            decision = (
                decisions.cell(cluster_id, sample_stem)
                if cell is not None
                else None
            )
            row[sample_stem] = production_matrix_area(decision)
        rows.append(row)
    return _write_tsv(path, columns, rows)
```

Change `write_alignment_review_tsv` signature:

```python
def write_alignment_review_tsv(
    path: Path,
    matrix: AlignmentMatrix,
    *,
    alignment_config: AlignmentConfig | None = None,
) -> Path:
    config = alignment_config or AlignmentConfig()
    return _write_tsv(
        path,
        ALIGNMENT_REVIEW_COLUMNS,
        _review_rows(matrix, alignment_config=config),
    )
```

Change `_review_rows` signature and add decisions:

```python
def _review_rows(
    matrix: AlignmentMatrix,
    *,
    alignment_config: AlignmentConfig,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    grouped_cells = cells_by_cluster(matrix)
    decisions = build_production_decisions(matrix, alignment_config)
    sample_count = len(matrix.sample_order)
```

Inside the cluster loop, before `rows.append(...)`, add:

```python
        row_decision = decisions.row(cluster_id)
```

Add these keys to the review row dict after `"present_rate"`:

```python
                "accepted_cell_count": row_decision.accepted_cell_count,
                "accepted_rescue_count": row_decision.accepted_rescue_count,
                "review_rescue_count": row_decision.review_rescue_count,
                "include_in_primary_matrix": row_decision.include_in_primary_matrix,
                "row_flags": ";".join(row_decision.row_flags),
```

- [ ] **Step 5: Run TSV tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_tsv_writer.py tests/test_alignment_production_decisions.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

Run:

```powershell
git add xic_extractor/alignment/output_rows.py xic_extractor/alignment/tsv_writer.py tests/test_alignment_tsv_writer.py
git commit -m "feat: filter untargeted production matrix rows"
```

## Task 3: Add Workbook Audit Sheet And Production Row Filtering

**Files:**
- Modify: `xic_extractor/alignment/xlsx_writer.py`
- Modify: `tests/test_alignment_xlsx_writer.py`

- [ ] **Step 1: Add failing XLSX tests**

Modify `tests/test_alignment_xlsx_writer.py`:

1. Update the expected sheet list in `test_alignment_results_xlsx_has_matrix_review_metadata_sheets`:

```python
    assert workbook.sheetnames == ["Matrix", "Review", "Audit", "Metadata"]
```

2. Replace the old `Review["H2"]` assertion in that test with explicit count checks:

```python
    assert workbook["Review"]["C2"].value == 1
    assert workbook["Review"]["K2"].value == 1
```

3. In `test_alignment_results_xlsx_blanks_duplicate_assigned_matrix_area`, replace the old duplicate-count assertion with:

```python
    assert workbook["Review"]["J2"].value == 1
```

4. Add these tests:

```python
def test_alignment_results_xlsx_excludes_review_only_rows_from_matrix(
    tmp_path: Path,
):
    matrix = AlignmentMatrix(
        clusters=(
            sample_feature("FAM000001", evidence="owner_complete_link;owner_count=2"),
            sample_feature("FAM000002", evidence="", has_anchor=False),
        ),
        sample_order=("s1",),
        cells=(
            sample_cell("s1", "FAM000001", "detected", 100.0),
            sample_cell("s1", "FAM000002", "rescued", 200.0),
        ),
    )

    path = write_alignment_results_xlsx(
        tmp_path / "alignment_results.xlsx",
        matrix,
        metadata={"schema_version": "alignment-results-v1"},
    )

    workbook = load_workbook(path, data_only=True)
    assert workbook["Matrix"]["A2"].value == "FAM000001"
    assert workbook["Matrix"]["A3"].value is None
    assert workbook["Audit"]["A2"].value == "FAM000001"
    assert workbook["Audit"]["A3"].value == "FAM000002"
    assert workbook["Audit"]["H3"].value == "review_rescue"
    assert workbook["Audit"]["J3"].value == "missing_row_identity_support"


def test_alignment_results_xlsx_audit_explains_duplicate_blank(
    tmp_path: Path,
):
    matrix = AlignmentMatrix(
        clusters=(sample_feature("FAM000001", evidence="owner_complete_link;owner_count=2"),),
        sample_order=("s1",),
        cells=(sample_cell("s1", "FAM000001", "duplicate_assigned", 200.0),),
    )

    path = write_alignment_results_xlsx(
        tmp_path / "alignment_results.xlsx",
        matrix,
        metadata={"schema_version": "alignment-results-v1"},
    )

    workbook = load_workbook(path, data_only=True)
    assert workbook["Matrix"]["A2"].value is None
    assert workbook["Audit"]["A2"].value == "FAM000001"
    assert workbook["Audit"]["F2"].value == "duplicate_assigned"
    assert workbook["Audit"]["I2"].value is False
    assert workbook["Audit"]["J2"].value == "duplicate_loser"
```

Add this helper near `sample_alignment_matrix()`:

```python
def sample_feature(
    feature_family_id: str,
    *,
    evidence: str,
    has_anchor: bool = True,
):
    return SimpleNamespace(
        feature_family_id=feature_family_id,
        neutral_loss_tag="DNA_dR",
        family_center_mz=242.114,
        family_center_rt=12.593,
        family_product_mz=126.066,
        family_observed_neutral_loss_da=116.048,
        has_anchor=has_anchor,
        event_cluster_ids=("OWN-s1-000001",),
        event_member_count=1,
        evidence=evidence,
        review_only=False,
    )
```

- [ ] **Step 2: Run XLSX tests and verify they fail**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_xlsx_writer.py -v
```

Expected: FAIL because the workbook has no `Audit` sheet and `Matrix` still writes review-only rows.

- [ ] **Step 3: Update XLSX writer**

Modify imports in `xic_extractor/alignment/xlsx_writer.py`:

```python
from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.production_decisions import (
    ProductionDecisionSet,
    build_production_decisions,
)
from xic_extractor.alignment.output_rows import (
    cells_by_cluster,
    count_status,
    production_matrix_area,
    row_id,
)
```

Change the public function:

```python
def write_alignment_results_xlsx(
    path: Path,
    matrix: AlignmentMatrix,
    *,
    metadata: dict[str, str],
    alignment_config: AlignmentConfig | None = None,
) -> Path:
    config = alignment_config or AlignmentConfig()
    decisions = build_production_decisions(matrix, config)
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    matrix_sheet = workbook.active
    matrix_sheet.title = "Matrix"
    _write_matrix_sheet(matrix_sheet, matrix, decisions)
    _write_review_sheet(workbook.create_sheet("Review"), matrix, decisions)
    _write_audit_sheet(workbook.create_sheet("Audit"), matrix, decisions)
    _write_metadata_sheet(workbook.create_sheet("Metadata"), metadata)
    workbook.save(path)
    return path
```

Change `_write_matrix_sheet`:

```python
def _write_matrix_sheet(
    sheet: Any,
    matrix: AlignmentMatrix,
    decisions: ProductionDecisionSet,
) -> None:
    headers = [
        "feature_family_id",
        "neutral_loss_tag",
        "family_center_mz",
        "family_center_rt",
        *matrix.sample_order,
    ]
    sheet.append(headers)
    grouped_cells = cells_by_cluster(matrix)
    for cluster in matrix.clusters:
        cluster_id = row_id(cluster)
        if not decisions.row(cluster_id).include_in_primary_matrix:
            continue
        cells = {
            cell.sample_stem: cell for cell in grouped_cells.get(cluster_id, ())
        }
        sheet.append(
            [
                cluster_id,
                cluster.neutral_loss_tag,
                _family_center_mz(cluster),
                _family_center_rt(cluster),
                *[
                    _xlsx_area(
                        decisions.cell(cluster_id, sample)
                        if sample in cells
                        else None
                    )
                    for sample in matrix.sample_order
                ],
            ],
        )
```

Change `_write_review_sheet` signature and add production columns:

```python
def _write_review_sheet(
    sheet: Any,
    matrix: AlignmentMatrix,
    decisions: ProductionDecisionSet,
) -> None:
    sheet.append(
        [
            "feature_family_id",
            "neutral_loss_tag",
            "detected_count",
            "rescued_count",
            "accepted_cell_count",
            "accepted_rescue_count",
            "review_rescue_count",
            "absent_count",
            "unchecked_count",
            "duplicate_assigned_count",
            "ambiguous_ms1_owner_count",
            "include_in_primary_matrix",
            "row_flags",
        ],
    )
    grouped_cells = cells_by_cluster(matrix)
    for cluster in matrix.clusters:
        cluster_id = row_id(cluster)
        cells = grouped_cells.get(cluster_id, ())
        row_decision = decisions.row(cluster_id)
        sheet.append(
            [
                cluster_id,
                cluster.neutral_loss_tag,
                count_status(cells, "detected"),
                count_status(cells, "rescued"),
                row_decision.accepted_cell_count,
                row_decision.accepted_rescue_count,
                row_decision.review_rescue_count,
                count_status(cells, "absent"),
                count_status(cells, "unchecked"),
                count_status(cells, "duplicate_assigned"),
                count_status(cells, "ambiguous_ms1_owner"),
                row_decision.include_in_primary_matrix,
                ";".join(row_decision.row_flags),
            ],
        )
```

Add `_write_audit_sheet`:

```python
def _write_audit_sheet(
    sheet: Any,
    matrix: AlignmentMatrix,
    decisions: ProductionDecisionSet,
) -> None:
    sheet.append(
        [
            "feature_family_id",
            "sample_stem",
            "neutral_loss_tag",
            "family_center_mz",
            "family_center_rt",
            "raw_status",
            "production_status",
            "rescue_tier",
            "write_matrix_value",
            "blank_reason",
            "area",
            "apex_rt",
            "rt_delta_sec",
            "claim_state",
            "row_flags",
            "reason",
        ],
    )
    clusters_by_id = {row_id(cluster): cluster for cluster in matrix.clusters}
    for cell in matrix.cells:
        cluster = clusters_by_id[cell.cluster_id]
        decision = decisions.cell(cell.cluster_id, cell.sample_stem)
        row_decision = decisions.row(cell.cluster_id)
        sheet.append(
            [
                cell.cluster_id,
                cell.sample_stem,
                cluster.neutral_loss_tag,
                _family_center_mz(cluster),
                _family_center_rt(cluster),
                decision.raw_status,
                decision.production_status,
                decision.rescue_tier,
                decision.write_matrix_value,
                decision.blank_reason,
                cell.area,
                cell.apex_rt,
                cell.rt_delta_sec,
                _claim_state(cell),
                ";".join(row_decision.row_flags),
                cell.reason,
            ],
        )
```

Replace `_xlsx_area`:

```python
def _xlsx_area(decision) -> float | None:
    text = production_matrix_area(decision)
    return float(text) if text else None
```

Add `_claim_state`:

```python
def _claim_state(cell: AlignedCell) -> str:
    if cell.status == "duplicate_assigned":
        return "loser"
    if cell.status in {"detected", "rescued"}:
        return "winner_or_unclaimed"
    return ""
```

- [ ] **Step 4: Run XLSX tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_xlsx_writer.py tests/test_alignment_production_decisions.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add xic_extractor/alignment/xlsx_writer.py tests/test_alignment_xlsx_writer.py
git commit -m "feat: add untargeted alignment audit workbook sheet"
```

## Task 4: Wire AlignmentConfig Through Pipeline Writers

**Files:**
- Modify: `xic_extractor/alignment/pipeline.py`
- Modify: `tests/test_alignment_pipeline.py`

- [ ] **Step 1: Add failing pipeline writer-config test**

Append to `tests/test_alignment_pipeline.py`:

```python
def test_pipeline_passes_alignment_config_to_production_writers(monkeypatch, tmp_path):
    from xic_extractor.alignment import pipeline as alignment_pipeline
    from xic_extractor.alignment.config import AlignmentConfig
    from xic_extractor.alignment.matrix import AlignmentMatrix

    seen = {"xlsx": None, "matrix_tsv": None, "review_tsv": None}
    matrix = AlignmentMatrix(clusters=(), cells=(), sample_order=())
    config = AlignmentConfig(max_rt_sec=77.0)
    outputs = alignment_pipeline.AlignmentRunOutputs(
        workbook=tmp_path / "alignment_results.xlsx",
        matrix_tsv=tmp_path / "alignment_matrix.tsv",
        review_tsv=tmp_path / "alignment_review.tsv",
    )

    def fake_xlsx(path, matrix_arg, *, metadata, alignment_config=None):
        seen["xlsx"] = alignment_config
        path.write_text("xlsx", encoding="utf-8")
        return path

    def fake_matrix_tsv(path, matrix_arg, *, alignment_config=None):
        seen["matrix_tsv"] = alignment_config
        path.write_text("matrix", encoding="utf-8")
        return path

    def fake_review_tsv(path, matrix_arg, *, alignment_config=None):
        seen["review_tsv"] = alignment_config
        path.write_text("review", encoding="utf-8")
        return path

    monkeypatch.setattr(alignment_pipeline, "write_alignment_results_xlsx", fake_xlsx)
    monkeypatch.setattr(alignment_pipeline, "write_alignment_matrix_tsv", fake_matrix_tsv)
    monkeypatch.setattr(alignment_pipeline, "write_alignment_review_tsv", fake_review_tsv)

    alignment_pipeline._write_outputs_atomic(
        outputs,
        matrix,
        metadata={"schema_version": "alignment-results-v1"},
        ownership=_empty_ownership(),
        alignment_config=config,
    )

    assert seen == {"xlsx": config, "matrix_tsv": config, "review_tsv": config}
```

If `tests/test_alignment_pipeline.py` has no existing `_empty_ownership()` helper, add:

```python
def _empty_ownership():
    from xic_extractor.alignment.ownership import OwnershipBuildResult

    return OwnershipBuildResult(assignments=(), ambiguous_records=(), owners=())
```

- [ ] **Step 2: Run pipeline test and verify it fails**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_pipeline.py::test_pipeline_passes_alignment_config_to_production_writers -v
```

Expected: FAIL because `_write_outputs_atomic()` does not accept `alignment_config`.

- [ ] **Step 3: Update pipeline writer wiring**

Modify `_write_outputs_atomic` signature in `xic_extractor/alignment/pipeline.py`:

```python
def _write_outputs_atomic(
    outputs: AlignmentRunOutputs,
    matrix: AlignmentMatrix,
    *,
    metadata: dict[str, str],
    ownership: OwnershipBuildResult,
    alignment_config: AlignmentConfig,
    edge_evidence: Sequence[OwnerEdgeEvidence] = (),
) -> None:
```

Update the caller in `run_alignment`:

```python
            _write_outputs_atomic(
                outputs,
                matrix,
                metadata=_metadata(
                    discovery_batch_index=discovery_batch_index,
                    raw_dir=raw_dir,
                    dll_dir=dll_dir,
                    output_level=output_level,
                    peak_config=peak_config,
                ),
                ownership=ownership,
                alignment_config=alignment_config,
                edge_evidence=edge_evidence or (),
            )
```

Update writer lambdas:

```python
                lambda path: write_alignment_results_xlsx(
                    path,
                    matrix,
                    metadata=metadata,
                    alignment_config=alignment_config,
                ),
```

```python
            (
                outputs.matrix_tsv,
                lambda path: write_alignment_matrix_tsv(
                    path,
                    matrix,
                    alignment_config=alignment_config,
                ),
            ),
```

```python
            (
                outputs.review_tsv,
                lambda path: write_alignment_review_tsv(
                    path,
                    matrix,
                    alignment_config=alignment_config,
                ),
            ),
```

- [ ] **Step 4: Run pipeline and writer tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_pipeline.py tests/test_alignment_tsv_writer.py tests/test_alignment_xlsx_writer.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add xic_extractor/alignment/pipeline.py tests/test_alignment_pipeline.py
git commit -m "feat: pass alignment config to production writers"
```

## Task 5: Split Rescue And Identity Guardrail Metrics

**Files:**
- Modify: `tools/diagnostics/untargeted_alignment_guardrails.py`
- Modify: `tests/test_untargeted_alignment_guardrails.py`

- [ ] **Step 1: Add failing guardrail tests for split metrics**

Append to `tests/test_untargeted_alignment_guardrails.py`:

```python
def test_guardrails_report_rescue_identity_and_duplicate_metrics(tmp_path: Path):
    alignment_dir = tmp_path / "alignment"
    alignment_dir.mkdir(parents=True)
    _write_tsv(
        alignment_dir / "alignment_review.tsv",
        [
            {
                "feature_family_id": "FAM001",
                "family_center_mz": 500.0,
                "family_center_rt": 5.0,
                "accepted_cell_count": 2,
                "accepted_rescue_count": 1,
                "review_rescue_count": 0,
                "include_in_primary_matrix": "TRUE",
                "row_flags": "rescue_heavy",
            },
            {
                "feature_family_id": "FAM002",
                "family_center_mz": 501.0,
                "family_center_rt": 5.1,
                "accepted_cell_count": 0,
                "accepted_rescue_count": 0,
                "review_rescue_count": 1,
                "include_in_primary_matrix": "FALSE",
                "row_flags": "rescue_only_review;identity_anchor_lost",
            },
            {
                "feature_family_id": "FAM003",
                "family_center_mz": 502.0,
                "family_center_rt": 5.2,
                "accepted_cell_count": 0,
                "accepted_rescue_count": 0,
                "review_rescue_count": 0,
                "include_in_primary_matrix": "FALSE",
                "row_flags": "duplicate_claim_pressure",
            },
        ],
    )
    _write_tsv(
        alignment_dir / "alignment_cells.tsv",
        [
            _cell_row("FAM001", "detected"),
            _cell_row("FAM001", "rescued"),
            _cell_row("FAM002", "rescued"),
            _cell_row("FAM003", "duplicate_assigned"),
        ],
    )

    metrics = guardrails.compute_guardrails(alignment_dir)

    assert metrics.accepted_rescue_cells == 1
    assert metrics.accepted_quantitative_cells == 2
    assert metrics.accepted_rescue_rate == 0.5
    assert metrics.review_rescue_count == 1
    assert metrics.rescue_only_review_families == 1
    assert metrics.identity_anchor_lost_families == 1
    assert metrics.duplicate_claim_pressure_families == 1
```

Modify `test_compare_guardrails_fails_when_candidate_metric_increases` so the expected metric list is:

```python
    rows = guardrails.compare_guardrails(
        {
            "duplicate_only_families": 1,
            "zero_present_families": 2,
            "review_rescue_count": 1,
            "rescue_only_review_families": 0,
            "identity_anchor_lost_families": 0,
            "duplicate_claim_pressure_families": 1,
            "negative_checkpoint_production_families": 4,
        },
        {
            "duplicate_only_families": 2,
            "zero_present_families": 2,
            "review_rescue_count": 3,
            "rescue_only_review_families": 1,
            "identity_anchor_lost_families": 0,
            "duplicate_claim_pressure_families": 1,
            "negative_checkpoint_production_families": 5,
        },
    )

    assert [row["metric"] for row in rows] == [
        "duplicate_only_families",
        "zero_present_families",
        "review_rescue_count",
        "rescue_only_review_families",
        "identity_anchor_lost_families",
        "duplicate_claim_pressure_families",
        "negative_checkpoint_production_families",
    ]
    assert [row["status"] for row in rows] == [
        "FAIL",
        "PASS",
        "FAIL",
        "FAIL",
        "PASS",
        "PASS",
        "FAIL",
    ]
```

- [ ] **Step 2: Run guardrail tests and verify they fail**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_untargeted_alignment_guardrails.py -v
```

Expected: FAIL because the new metric fields do not exist.

- [ ] **Step 3: Update guardrail dataclass and comparison metrics**

In `tools/diagnostics/untargeted_alignment_guardrails.py`, replace `COMPARISON_METRICS` with:

```python
COMPARISON_METRICS = [
    "duplicate_only_families",
    "zero_present_families",
    "review_rescue_count",
    "rescue_only_review_families",
    "identity_anchor_lost_families",
    "duplicate_claim_pressure_families",
    "negative_checkpoint_production_families",
]
```

Replace `GuardrailMetrics` with:

```python
@dataclass(frozen=True)
class GuardrailMetrics:
    zero_present_families: int
    duplicate_only_families: int
    high_backfill_dependency_families: int
    negative_8oxodg_production_families: int
    negative_checkpoint_production_families: int
    accepted_quantitative_cells: int
    accepted_rescue_cells: int
    accepted_rescue_rate: float
    review_rescue_count: int
    rescue_only_review_families: int
    identity_anchor_lost_families: int
    duplicate_claim_pressure_families: int
    istd_false_missing_recovery: int
    case_assertions: dict[str, CaseAssertion]
```

In `compute_guardrails`, initialize these counters before the family loop:

```python
    accepted_quantitative_cells = 0
    accepted_rescue_cells = 0
    review_rescue_count = 0
    rescue_only_review = 0
    identity_anchor_lost = 0
    duplicate_claim_pressure = 0
```

Inside the family loop, after `review_row = review_by_family.get(family_id, {})`, add:

```python
        accepted_cells = _int_value(review_row.get("accepted_cell_count"))
        accepted_rescues = _int_value(review_row.get("accepted_rescue_count"))
        review_rescues = _int_value(review_row.get("review_rescue_count"))
        row_flags = _row_flags(review_row)
        accepted_quantitative_cells += accepted_cells
        accepted_rescue_cells += accepted_rescues
        review_rescue_count += review_rescues
        if "rescue_only_review" in row_flags:
            rescue_only_review += 1
        if "identity_anchor_lost" in row_flags:
            identity_anchor_lost += 1
        if "duplicate_claim_pressure" in row_flags:
            duplicate_claim_pressure += 1
```

Replace the negative checkpoint condition in the same loop:

```python
        if accepted_cells > 0 and _row_in_mz_window(
            review_row,
            "family_center_mz",
            284.0989,
            20.0,
        ):
            negative_8oxodg += 1
```

Replace the return block with:

```python
    accepted_rescue_rate = (
        accepted_rescue_cells / accepted_quantitative_cells
        if accepted_quantitative_cells
        else 0.0
    )
    return GuardrailMetrics(
        zero_present_families=zero_present,
        duplicate_only_families=duplicate_only,
        high_backfill_dependency_families=high_backfill,
        negative_8oxodg_production_families=negative_8oxodg,
        negative_checkpoint_production_families=negative_8oxodg,
        accepted_quantitative_cells=accepted_quantitative_cells,
        accepted_rescue_cells=accepted_rescue_cells,
        accepted_rescue_rate=accepted_rescue_rate,
        review_rescue_count=review_rescue_count,
        rescue_only_review_families=rescue_only_review,
        identity_anchor_lost_families=identity_anchor_lost,
        duplicate_claim_pressure_families=duplicate_claim_pressure,
        istd_false_missing_recovery=0,
        case_assertions=_compute_case_assertions(
            review_rows,
            status_counts,
            edge_rows,
        ),
    )
```

Add helper:

```python
def _row_flags(row: Mapping[str, str]) -> set[str]:
    value = row.get("row_flags", "")
    return {part for part in value.split(";") if part}
```

Update `_metrics_for_comparison`:

```python
def _metrics_for_comparison(metrics: GuardrailMetrics) -> dict[str, int]:
    return {
        "zero_present_families": metrics.zero_present_families,
        "duplicate_only_families": metrics.duplicate_only_families,
        "review_rescue_count": metrics.review_rescue_count,
        "rescue_only_review_families": metrics.rescue_only_review_families,
        "identity_anchor_lost_families": metrics.identity_anchor_lost_families,
        "duplicate_claim_pressure_families": metrics.duplicate_claim_pressure_families,
        "negative_checkpoint_production_families": (
            metrics.negative_checkpoint_production_families
        ),
    }
```

- [ ] **Step 4: Run guardrail tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_untargeted_alignment_guardrails.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```powershell
git add tools/diagnostics/untargeted_alignment_guardrails.py tests/test_untargeted_alignment_guardrails.py
git commit -m "feat: split untargeted rescue guardrail metrics"
```

## Task 6: Create Internal-Standard False-Missing Fixture

**Files:**
- Create: `tools/diagnostics/build_istd_false_missing_fixture.py`
- Create: `tests/fixtures/untargeted_alignment/istd_false_missing_fixture.csv`
- Test: `tests/test_istd_false_missing_fixture.py`

- [ ] **Step 1: Write fixture builder tests**

Create `tests/test_istd_false_missing_fixture.py`:

```python
import csv
from pathlib import Path

from openpyxl import Workbook

from tools.diagnostics.build_istd_false_missing_fixture import (
    build_istd_false_missing_fixture,
    main,
)


def test_build_istd_false_missing_fixture_maps_qc_names_and_targeted_evidence(
    tmp_path: Path,
):
    old_path = tmp_path / "old.xlsx"
    targeted_path = tmp_path / "targeted.xlsx"
    output_csv = tmp_path / "fixture.csv"
    _write_old_matrix(old_path)
    _write_targeted_workbook(targeted_path)

    rows = build_istd_false_missing_fixture(
        old_matrix_path=old_path,
        targeted_workbook_path=targeted_path,
        output_csv=output_csv,
    )

    assert len(rows) == 2
    assert rows[0]["old_sample_id"] == "Breast_Cancer_Tissue_pooled_QC_1"
    assert rows[0]["targeted_sample_id"] == "Breast_Cancer_Tissue_pooled_QC1"
    assert rows[0]["targeted_confidence"] == "HIGH"
    assert rows[0]["targeted_nl"] == "✓"
    assert rows[1]["old_sample_id"] == "TumorBC2257_DNA"
    assert rows[1]["targeted_area"] == "8959790.66"
    assert _read_csv(output_csv) == rows


def test_fixture_builder_main_writes_csv(tmp_path: Path):
    old_path = tmp_path / "old.xlsx"
    targeted_path = tmp_path / "targeted.xlsx"
    output_csv = tmp_path / "fixture.csv"
    _write_old_matrix(old_path)
    _write_targeted_workbook(targeted_path)

    code = main(
        [
            "--old-matrix",
            str(old_path),
            "--targeted-workbook",
            str(targeted_path),
            "--output-csv",
            str(output_csv),
        ],
    )

    assert code == 0
    assert output_csv.exists()


def _write_old_matrix(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "RawIntensity"
    sheet.append(
        [
            "Mz/RT",
            "Breast_Cancer_Tissue_pooled_QC_1",
            "TumorBC2257_DNA",
            "Imputation_Tag_Reasons",
        ],
    )
    sheet.append(["245.1332/12.28", None, 123.0, ""])
    sheet.append(["261.1283/8.97", 456.0, None, ""])
    workbook.save(path)


def _write_targeted_workbook(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "XIC Results"
    sheet.append(
        [
            "SampleName",
            "Group",
            "Target",
            "Role",
            "ISTD Pair",
            "RT",
            "Area",
            "NL",
            "Int",
            "PeakStart",
            "PeakEnd",
            "PeakWidth",
            "Confidence",
            "Reason",
        ],
    )
    sheet.append(
        [
            "Breast_Cancer_Tissue_pooled_QC1",
            "QC",
            "d3-5-medC",
            "ISTD",
            None,
            11.3876,
            23305406.99,
            "✓",
            100,
            11.2,
            11.5,
            0.3,
            "HIGH",
            "decision: accepted; support: strict NL OK",
        ],
    )
    sheet.append(
        [
            "TumorBC2257_DNA",
            "Tumor",
            "d3-5-hmdC",
            "ISTD",
            None,
            9.2009,
            8959790.66,
            "✓",
            100,
            9.0,
            9.3,
            0.3,
            "HIGH",
            "decision: accepted; support: strict NL OK",
        ],
    )
    workbook.save(path)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))
```

- [ ] **Step 2: Run fixture builder tests and verify they fail**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_istd_false_missing_fixture.py -v
```

Expected: FAIL because the builder module does not exist.

- [ ] **Step 3: Implement fixture builder**

Create `tools/diagnostics/build_istd_false_missing_fixture.py`:

```python
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections.abc import Sequence
from pathlib import Path

from openpyxl import load_workbook

OLD_ROW_TO_TARGET = {
    "245.1332/12.28": "d3-5-medC",
    "261.1283/8.97": "d3-5-hmdC",
}

FIELDNAMES = (
    "old_matrix_path",
    "old_matrix_sheet",
    "targeted_workbook_path",
    "targeted_sheet",
    "old_row_coordinate",
    "targeted_identity",
    "old_sample_id",
    "targeted_sample_id",
    "sample_mapping_rule",
    "targeted_rt",
    "targeted_area",
    "targeted_nl",
    "targeted_confidence",
    "targeted_reason",
)


def build_istd_false_missing_fixture(
    *,
    old_matrix_path: Path,
    targeted_workbook_path: Path,
    output_csv: Path,
    old_matrix_sheet: str = "RawIntensity",
    targeted_sheet: str = "XIC Results",
) -> list[dict[str, str]]:
    old_missing = _old_missing_samples(old_matrix_path, old_matrix_sheet)
    targeted_rows = _targeted_rows(targeted_workbook_path, targeted_sheet)
    rows: list[dict[str, str]] = []
    for old_row_coordinate, target_label in OLD_ROW_TO_TARGET.items():
        for old_sample_id in old_missing[old_row_coordinate]:
            targeted_sample_id = _map_sample_id(old_sample_id)
            targeted = targeted_rows.get((target_label, targeted_sample_id))
            if targeted is None:
                raise ValueError(
                    "Missing targeted evidence for "
                    f"{target_label} / {targeted_sample_id}",
                )
            rows.append(
                {
                    "old_matrix_path": str(old_matrix_path),
                    "old_matrix_sheet": old_matrix_sheet,
                    "targeted_workbook_path": str(targeted_workbook_path),
                    "targeted_sheet": targeted_sheet,
                    "old_row_coordinate": old_row_coordinate,
                    "targeted_identity": target_label,
                    "old_sample_id": old_sample_id,
                    "targeted_sample_id": targeted_sample_id,
                    "sample_mapping_rule": "regex:_QC_(number)->_QC(number)",
                    "targeted_rt": _text(targeted["RT"]),
                    "targeted_area": _text(targeted["Area"]),
                    "targeted_nl": _text(targeted["NL"]),
                    "targeted_confidence": _text(targeted["Confidence"]),
                    "targeted_reason": _text(targeted["Reason"]),
                },
            )
    _write_csv(output_csv, rows)
    return rows


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        build_istd_false_missing_fixture(
            old_matrix_path=args.old_matrix,
            targeted_workbook_path=args.targeted_workbook,
            output_csv=args.output_csv,
        )
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build ISTD false-missing validation fixture.",
    )
    parser.add_argument("--old-matrix", type=Path, required=True)
    parser.add_argument("--targeted-workbook", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    return parser.parse_args(argv)


def _old_missing_samples(path: Path, sheet_name: str) -> dict[str, list[str]]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = workbook[sheet_name]
        header = list(next(sheet.iter_rows(min_row=1, max_row=1, values_only=True)))
        result: dict[str, list[str]] = {}
        for row in sheet.iter_rows(min_row=2, values_only=True):
            coordinate = _text(row[0])
            if coordinate not in OLD_ROW_TO_TARGET:
                continue
            missing: list[str] = []
            for column_name, value in zip(header[1:], row[1:]):
                if column_name is None or str(column_name).startswith("Imputation"):
                    continue
                if value in (None, ""):
                    missing.append(str(column_name))
            result[coordinate] = missing
        for coordinate in OLD_ROW_TO_TARGET:
            if coordinate not in result:
                raise KeyError(f"Old matrix is missing row: {coordinate}")
        return result
    finally:
        workbook.close()


def _targeted_rows(path: Path, sheet_name: str) -> dict[tuple[str, str], dict[str, object]]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = workbook[sheet_name]
        header = list(next(sheet.iter_rows(min_row=1, max_row=1, values_only=True)))
        indexes = {str(name): index for index, name in enumerate(header) if name}
        required = {"SampleName", "Target", "RT", "Area", "NL", "Confidence", "Reason"}
        missing = required - set(indexes)
        if missing:
            raise KeyError(f"Targeted workbook is missing columns: {sorted(missing)}")
        rows: dict[tuple[str, str], dict[str, object]] = {}
        current_sample = ""
        for row in sheet.iter_rows(min_row=2, values_only=True):
            sample = row[indexes["SampleName"]]
            if sample not in (None, ""):
                current_sample = str(sample)
            target = row[indexes["Target"]]
            if target in (None, ""):
                continue
            rows[(str(target), current_sample)] = {
                "RT": row[indexes["RT"]],
                "Area": row[indexes["Area"]],
                "NL": row[indexes["NL"]],
                "Confidence": row[indexes["Confidence"]],
                "Reason": row[indexes["Reason"]],
            }
        return rows
    finally:
        workbook.close()


def _map_sample_id(sample_id: str) -> str:
    return re.sub(r"_QC_(\d+)$", r"_QC\1", sample_id)


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(FIELDNAMES))
        writer.writeheader()
        writer.writerows(rows)


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run fixture builder tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_istd_false_missing_fixture.py -v
```

Expected: PASS.

- [ ] **Step 5: Generate the real fixture CSV**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python tools/diagnostics/build_istd_false_missing_fixture.py --old-matrix "C:\Users\user\Desktop\NTU cancer\Processed Data\DNA\Mzmine\new_test\full pipeline\20-10\ALL_metabcombiner_fh_format_20260422_213805_combined_fix_20260505_134549.xlsx" --targeted-workbook "C:\Users\user\Desktop\XIC_Extractor\output\xic_results_20260512_1200.xlsx" --output-csv tests\fixtures\untargeted_alignment\istd_false_missing_fixture.csv
```

Expected: PASS and `tests\fixtures\untargeted_alignment\istd_false_missing_fixture.csv` contains 16 rows. When projected to `old_row_coordinate,targeted_identity,old_sample_id,targeted_sample_id,targeted_confidence,targeted_nl`, it contains:

```text
245.1332/12.28,d3-5-medC,Breast_Cancer_Tissue_pooled_QC_1,Breast_Cancer_Tissue_pooled_QC1,HIGH,✓
245.1332/12.28,d3-5-medC,TumorBC2257_DNA,TumorBC2257_DNA,HIGH,✓
245.1332/12.28,d3-5-medC,NormalBC2263_DNA,NormalBC2263_DNA,HIGH,✓
245.1332/12.28,d3-5-medC,NormalBC2277_DNA,NormalBC2277_DNA,HIGH,✓
245.1332/12.28,d3-5-medC,NormalBC2282_DNA,NormalBC2282_DNA,HIGH,✓
261.1283/8.97,d3-5-hmdC,TumorBC2257_DNA,TumorBC2257_DNA,HIGH,✓
261.1283/8.97,d3-5-hmdC,Breast_Cancer_Tissue_pooled_QC_2,Breast_Cancer_Tissue_pooled_QC2,HIGH,✓
261.1283/8.97,d3-5-hmdC,Breast_Cancer_Tissue_pooled_QC_3,Breast_Cancer_Tissue_pooled_QC3,HIGH,✓
261.1283/8.97,d3-5-hmdC,TumorBC2312_DNA,TumorBC2312_DNA,HIGH,✓
261.1283/8.97,d3-5-hmdC,NormalBC2265_DNA,NormalBC2265_DNA,HIGH,✓
261.1283/8.97,d3-5-hmdC,NormalBC2275_DNA,NormalBC2275_DNA,HIGH,✓
261.1283/8.97,d3-5-hmdC,NormalBC2292_DNA,NormalBC2292_DNA,HIGH,✓
261.1283/8.97,d3-5-hmdC,NormalBC2312_DNA,NormalBC2312_DNA,HIGH,✓
261.1283/8.97,d3-5-hmdC,NormalBC2313_DNA,NormalBC2313_DNA,HIGH,✓
261.1283/8.97,d3-5-hmdC,BenignfatBC1116_DNA,BenignfatBC1116_DNA,HIGH,✓
261.1283/8.97,d3-5-hmdC,BenignfatBC1228_DNA,BenignfatBC1228_DNA,HIGH,✓
```

- [ ] **Step 6: Commit**

Run:

```powershell
git add tools/diagnostics/build_istd_false_missing_fixture.py tests/test_istd_false_missing_fixture.py tests/fixtures/untargeted_alignment/istd_false_missing_fixture.csv
git commit -m "test: add ISTD false missing validation fixture"
```

## Task 7: Add Final Contract Integration Tests

**Files:**
- Create: `tests/test_untargeted_final_matrix_contract.py`

- [ ] **Step 1: Write final contract tests**

Create `tests/test_untargeted_final_matrix_contract.py`:

```python
import csv
from pathlib import Path
from types import SimpleNamespace

from openpyxl import load_workbook

from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.tsv_writer import write_alignment_matrix_tsv
from xic_extractor.alignment.xlsx_writer import write_alignment_results_xlsx


def test_primary_outputs_hide_status_strings_and_keep_audit_reasons(tmp_path: Path):
    matrix = AlignmentMatrix(
        clusters=(
            _feature("FAM001", evidence="owner_complete_link;owner_count=2"),
            _feature("FAM002", evidence="", has_anchor=False),
            _feature("FAM003", evidence="owner_complete_link;owner_count=2"),
        ),
        sample_order=("s1", "s2"),
        cells=(
            _cell("s1", "FAM001", "detected", 100.0),
            _cell("s2", "FAM001", "rescued", 90.0),
            _cell("s1", "FAM002", "rescued", 80.0),
            _cell("s2", "FAM002", "absent", None),
            _cell("s1", "FAM003", "duplicate_assigned", 70.0),
            _cell("s2", "FAM003", "ambiguous_ms1_owner", None),
        ),
    )

    matrix_tsv = write_alignment_matrix_tsv(tmp_path / "alignment_matrix.tsv", matrix)
    workbook_path = write_alignment_results_xlsx(
        tmp_path / "alignment_results.xlsx",
        matrix,
        metadata={"schema_version": "alignment-results-v1"},
    )

    tsv_rows = _read_tsv(matrix_tsv)
    assert [row["feature_family_id"] for row in tsv_rows] == ["FAM001"]
    assert tsv_rows[0]["s1"] == "100"
    assert tsv_rows[0]["s2"] == "90"
    assert "rescued" not in tsv_rows[0].values()

    workbook = load_workbook(workbook_path, data_only=True)
    assert workbook["Matrix"]["A2"].value == "FAM001"
    assert workbook["Matrix"]["E2"].value == 100.0
    assert workbook["Matrix"]["F2"].value == 90.0
    assert workbook["Matrix"]["A3"].value is None
    audit_blank_reasons = [cell.value for cell in workbook["Audit"]["J"][1:]]
    assert "missing_row_identity_support" in audit_blank_reasons
    assert "duplicate_loser" in audit_blank_reasons
    assert "ambiguous_ms1_owner" in audit_blank_reasons


def test_istd_fixture_records_explicit_matching_fields():
    fixture = Path(
        "tests/fixtures/untargeted_alignment/istd_false_missing_fixture.csv",
    )
    rows = _read_csv(fixture)

    assert len(rows) == 16
    assert {row["targeted_identity"] for row in rows} == {
        "d3-5-medC",
        "d3-5-hmdC",
    }
    assert all(row["targeted_confidence"] == "HIGH" for row in rows)
    assert all(row["targeted_nl"] == "✓" for row in rows)
    assert all(row["sample_mapping_rule"] for row in rows)
    assert {
        (row["old_row_coordinate"], row["targeted_identity"])
        for row in rows
    } == {
        ("245.1332/12.28", "d3-5-medC"),
        ("261.1283/8.97", "d3-5-hmdC"),
    }


def _feature(
    feature_family_id: str,
    *,
    evidence: str,
    has_anchor: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        feature_family_id=feature_family_id,
        neutral_loss_tag="DNA_dR",
        family_center_mz=500.123,
        family_center_rt=8.49,
        family_product_mz=384.076,
        family_observed_neutral_loss_da=116.047,
        has_anchor=has_anchor,
        event_cluster_ids=("OWN-s1-000001",),
        event_member_count=1,
        evidence=evidence,
        review_only=False,
    )


def _cell(
    sample_stem: str,
    cluster_id: str,
    status: str,
    area: float | None,
) -> AlignedCell:
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=cluster_id,
        status=status,  # type: ignore[arg-type]
        area=area,
        apex_rt=8.49 if area is not None else None,
        height=100.0 if area is not None else None,
        peak_start_rt=8.4 if area is not None else None,
        peak_end_rt=8.6 if area is not None else None,
        rt_delta_sec=0.0 if area is not None else None,
        trace_quality="clean" if area is not None else status,
        scan_support_score=0.8 if area is not None else None,
        source_candidate_id=f"{sample_stem}#1" if status == "detected" else None,
        source_raw_file=Path(f"{sample_stem}.raw") if status == "detected" else None,
        reason=(
            "duplicate MS1 peak claim; winner=FAM001; original_status=detected"
            if status == "duplicate_assigned"
            else status
        ),
    )


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))
```

- [ ] **Step 2: Run final contract tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_untargeted_final_matrix_contract.py -v
```

Expected: PASS after Tasks 1 through 6 are complete.

- [ ] **Step 3: Run focused regression suite**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_production_decisions.py tests/test_alignment_tsv_writer.py tests/test_alignment_xlsx_writer.py tests/test_alignment_pipeline.py tests/test_untargeted_alignment_guardrails.py tests/test_istd_false_missing_fixture.py tests/test_untargeted_final_matrix_contract.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

Run:

```powershell
git add tests/test_untargeted_final_matrix_contract.py
git commit -m "test: cover untargeted final matrix contract"
```

## Task 8: Final Review And Documentation Check

**Files:**
- Modify only if needed after review: `docs/superpowers/specs/2026-05-13-untargeted-final-matrix-and-rescue-evidence-spec.md`

- [ ] **Step 1: Search for forbidden placeholders in the implementation**

Run:

```powershell
$patterns = @('TO' + 'DO', 'TB' + 'D', 'implement lat' + 'er', 'fill ' + 'in')
$paths = @(
    'xic_extractor',
    'tests',
    'tools',
    'docs/superpowers/plans/2026-05-13-untargeted-final-matrix-rescue-contract-plan.md',
    'docs/superpowers/specs/2026-05-13-untargeted-final-matrix-and-rescue-evidence-spec.md'
)
foreach ($pattern in $patterns) {
    rg $pattern $paths
}
```

Expected: no output.

- [ ] **Step 2: Run the focused regression suite again**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_production_decisions.py tests/test_alignment_tsv_writer.py tests/test_alignment_xlsx_writer.py tests/test_alignment_pipeline.py tests/test_untargeted_alignment_guardrails.py tests/test_istd_false_missing_fixture.py tests/test_untargeted_final_matrix_contract.py -v
```

Expected: PASS.

- [ ] **Step 3: Confirm Git state and commit any doc-only adjustment**

Run:

```powershell
git status --short
```

Expected after Task 7: clean.

If Step 1 or Step 2 forced a wording-only change in the spec or plan, commit it:

```powershell
git add docs/superpowers/specs/2026-05-13-untargeted-final-matrix-and-rescue-evidence-spec.md docs/superpowers/plans/2026-05-13-untargeted-final-matrix-rescue-contract-plan.md
git commit -m "docs: align final matrix rescue contract plan"
```

## Self-Review

Spec coverage:

- Final matrix cell contract is implemented by Tasks 1, 2, 3, and 7.
- Primary row inclusion is implemented by Tasks 1, 2, 3, and 7.
- In-workbook audit/review sheet is implemented by Task 3.
- Rescue tier and blank reason traceability is implemented by Tasks 1, 2, and 3.
- Guardrail split is implemented by Task 5.
- Old-pipeline internal-standard false missing evidence is implemented by Task 6.
- Validation fixture explicit sample mapping and evidence fields are covered by Tasks 6 and 7.
- Negative checkpoint remains validation-only through guardrail naming in Task 5; no production target-label exception is introduced.

Placeholder scan:

- The plan avoids unresolved placeholders and gives concrete commands, paths, test bodies, and implementation snippets.

Type consistency:

- `ProductionCellDecision`, `ProductionRowDecision`, and `ProductionDecisionSet` are introduced in Task 1 and reused by Tasks 2 and 3.
- `build_production_decisions(matrix, config)` has the same signature across all tasks.
- `write_alignment_matrix_tsv(..., alignment_config=...)`, `write_alignment_review_tsv(..., alignment_config=...)`, and `write_alignment_results_xlsx(..., alignment_config=...)` use the same optional keyword pattern.
