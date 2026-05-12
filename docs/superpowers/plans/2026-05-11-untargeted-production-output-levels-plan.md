# Untargeted Production Output Levels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate production, machine, debug, and validation alignment outputs so users can get `alignment_results.xlsx` plus `review_report.html` as the production surface while developers can opt into TSV/debug artifacts. The CLI default remains machine-compatible until owner-based 8-RAW and 85-RAW acceptance passes.

**Architecture:** Add an explicit output-level model and writers for production workbook and visual review. Keep TSV writers as machine/debug contracts. Wire `scripts/run_alignment.py` to support output levels now, but keep `machine` as the default until owner-based alignment semantics pass validation.

**Tech Stack:** Python dataclasses, existing alignment matrix model, existing TSV writers, `openpyxl` workbook support already used by the project, static HTML rendering, `pytest`.

---

## Prerequisites

Complete these plans first:

1. `docs/superpowers/plans/2026-05-11-sample-local-ms1-ownership-core-plan.md`
2. `docs/superpowers/plans/2026-05-11-owner-based-alignment-pipeline-plan.md`

Do not switch production defaults while the event-first pipeline is still the primary alignment algorithm.

## Output Contract

Follow:

```text
docs/superpowers/specs/2026-05-11-untargeted-alignment-output-contract.md
```

Artifacts by level:

| Level | Artifacts |
|---|---|
| `production` | `alignment_results.xlsx`, `review_report.html` |
| `machine` | production artifacts plus `alignment_matrix.tsv`, `alignment_review.tsv` |
| `debug` | machine artifacts plus `alignment_cells.tsv`, `alignment_matrix_status.tsv`, `event_to_ms1_owner.tsv`, `ambiguous_ms1_owners.tsv` |
| `validation` | debug artifacts plus legacy validation TSVs when validation command is used |

## File Structure

- Create `xic_extractor/alignment/output_levels.py`
  - `AlignmentOutputLevel`
  - artifact list resolver
  - level validation
- Create `xic_extractor/alignment/xlsx_writer.py`
  - `alignment_results.xlsx`
  - sheets: `Matrix`, `Review`, `Metadata`
- Create `xic_extractor/alignment/output_rows.py`
  - Shared matrix/review row helpers for TSV and XLSX writers.
  - Prevents XLSX writer from importing private TSV writer helpers.
- Create `xic_extractor/alignment/html_report.py`
  - `review_report.html`
  - visual QC blocks, not a TSV copy
- Create `xic_extractor/alignment/debug_writer.py`
  - `event_to_ms1_owner.tsv`
  - `ambiguous_ms1_owners.tsv`
- Modify `xic_extractor/alignment/pipeline.py`
  - accept `output_level`
  - write artifacts by level
  - write each output level as one atomic artifact set with rollback
- Modify `scripts/run_alignment.py`
  - add `--output-level production|machine|debug|validation`
  - default to `machine` in this PR; switch to `production` only after owner-based semantics are accepted by 8-RAW and 85-RAW validation
- Tests:
  - `tests/test_alignment_output_levels.py`
  - `tests/test_alignment_xlsx_writer.py`
  - `tests/test_alignment_html_report.py`
  - update `tests/test_alignment_pipeline.py`
  - update `tests/test_run_alignment.py`

## Task 1: Add Output Level Model

**Files:**
- Create: `xic_extractor/alignment/output_levels.py`
- Test: `tests/test_alignment_output_levels.py`

- [ ] **Step 1: Write output level tests**

Create `tests/test_alignment_output_levels.py`:

```python
import pytest

from xic_extractor.alignment.output_levels import (
    AlignmentOutputLevel,
    artifact_names_for_output_level,
    parse_alignment_output_level,
)


def test_production_output_level_artifacts_are_xlsx_and_html_only():
    assert artifact_names_for_output_level("production") == (
        "alignment_results.xlsx",
        "review_report.html",
    )


def test_machine_output_level_adds_review_and_matrix_tsv():
    assert artifact_names_for_output_level("machine") == (
        "alignment_results.xlsx",
        "review_report.html",
        "alignment_matrix.tsv",
        "alignment_review.tsv",
    )


def test_debug_output_level_adds_cell_status_and_owner_debug_tsvs():
    assert artifact_names_for_output_level("debug") == (
        "alignment_results.xlsx",
        "review_report.html",
        "alignment_matrix.tsv",
        "alignment_review.tsv",
        "alignment_cells.tsv",
        "alignment_matrix_status.tsv",
        "event_to_ms1_owner.tsv",
        "ambiguous_ms1_owners.tsv",
    )


def test_parse_alignment_output_level_rejects_unknown_value():
    with pytest.raises(ValueError, match="output_level"):
        parse_alignment_output_level("everything")
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_output_levels.py -v
```

Expected: FAIL because `output_levels.py` does not exist.

- [ ] **Step 3: Implement output level model**

Create `xic_extractor/alignment/output_levels.py`:

```python
from __future__ import annotations

from typing import Literal

AlignmentOutputLevel = Literal["production", "machine", "debug", "validation"]


_ARTIFACTS: dict[AlignmentOutputLevel, tuple[str, ...]] = {
    "production": (
        "alignment_results.xlsx",
        "review_report.html",
    ),
    "machine": (
        "alignment_results.xlsx",
        "review_report.html",
        "alignment_matrix.tsv",
        "alignment_review.tsv",
    ),
    "debug": (
        "alignment_results.xlsx",
        "review_report.html",
        "alignment_matrix.tsv",
        "alignment_review.tsv",
        "alignment_cells.tsv",
        "alignment_matrix_status.tsv",
        "event_to_ms1_owner.tsv",
        "ambiguous_ms1_owners.tsv",
    ),
    "validation": (
        "alignment_results.xlsx",
        "review_report.html",
        "alignment_matrix.tsv",
        "alignment_review.tsv",
        "alignment_cells.tsv",
        "alignment_matrix_status.tsv",
        "event_to_ms1_owner.tsv",
        "ambiguous_ms1_owners.tsv",
    ),
}


def parse_alignment_output_level(value: str) -> AlignmentOutputLevel:
    if value not in _ARTIFACTS:
        raise ValueError(
            "output_level must be one of production, machine, debug, validation",
        )
    return value  # type: ignore[return-value]


def artifact_names_for_output_level(level: AlignmentOutputLevel) -> tuple[str, ...]:
    return _ARTIFACTS[level]
```

- [ ] **Step 4: Run output level tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_output_levels.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/alignment/output_levels.py tests/test_alignment_output_levels.py
git commit -m "feat: define untargeted alignment output levels"
```

## Task 2: Extract Shared Output Rows

**Files:**
- Create: `xic_extractor/alignment/output_rows.py`
- Modify: `xic_extractor/alignment/tsv_writer.py`
- Test: `tests/test_alignment_tsv_writer.py`

- [ ] **Step 1: Add TSV characterization test for shared row semantics**

Append to `tests/test_alignment_tsv_writer.py`:

```python
def test_alignment_review_tsv_counts_ambiguous_owner_cells(tmp_path):
    cluster = _row_like("FAM000001")
    matrix = AlignmentMatrix(
        clusters=(cluster,),
        sample_order=("s1", "s2"),
        cells=(
            _cell("s1", "FAM000001", "detected", area=100.0),
            _cell("s2", "FAM000001", "ambiguous_ms1_owner", area=None),
        ),
    )

    path = write_alignment_review_tsv(tmp_path / "alignment_review.tsv", matrix)

    text = path.read_text(encoding="utf-8")
    assert "ambiguous_ms1_owner_count" in text.splitlines()[0]
    assert "\t1\t" in text
```

- [ ] **Step 2: Run test before refactor**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_tsv_writer.py -v
```

Expected: PASS or FAIL only because `ambiguous_ms1_owner_count` is not present yet.

- [ ] **Step 3: Create shared output row helpers**

Create `xic_extractor/alignment/output_rows.py`:

```python
from __future__ import annotations

import math
from typing import Any

from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix


def cells_by_cluster(matrix: AlignmentMatrix) -> dict[str, tuple[AlignedCell, ...]]:
    grouped: dict[str, list[AlignedCell]] = {}
    for cell in matrix.cells:
        grouped.setdefault(cell.cluster_id, []).append(cell)
    return {cluster_id: tuple(cells) for cluster_id, cells in grouped.items()}


def matrix_area(cell: AlignedCell | None) -> str:
    if cell is None or cell.status not in {"detected", "rescued"}:
        return ""
    area = cell.area
    if area is None or not math.isfinite(area) or area <= 0:
        return ""
    return format_float(area)


def format_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        return format_float(value)
    return escape_excel_formula(str(value))


def format_float(value: float) -> str:
    return f"{value:.6g}"


def escape_excel_formula(value: str) -> str:
    if value.startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value


def row_id(row: Any) -> str:
    if hasattr(row, "feature_family_id"):
        return str(row.feature_family_id)
    return str(row.cluster_id)
```

- [ ] **Step 4: Update TSV writer to use shared helpers**

In `xic_extractor/alignment/tsv_writer.py`, import:

```python
from xic_extractor.alignment.output_rows import (
    cells_by_cluster,
    escape_excel_formula,
    format_float,
    format_value,
    matrix_area,
    row_id,
)
```

Then replace private helper calls:

```python
_cells_by_cluster(...) -> cells_by_cluster(...)
_matrix_area(...) -> matrix_area(...)
_format_value(...) -> format_value(...)
_format_float(...) -> format_float(...)
_escape_excel_formula(...) -> escape_excel_formula(...)
_row_id(...) -> row_id(...)
```

Keep old private helper names only if existing tests import them. If tests do,
leave compatibility wrappers:

```python
_cells_by_cluster = cells_by_cluster
_matrix_area = matrix_area
_format_value = format_value
_format_float = format_float
_escape_excel_formula = escape_excel_formula
_row_id = row_id
```

- [ ] **Step 5: Add ambiguous count to review TSV**

Add `"ambiguous_ms1_owner_count"` after `"unchecked_count"` in
`ALIGNMENT_REVIEW_COLUMNS`, and populate it from:

```python
ambiguous_ms1_owner_count = _count(cells, "ambiguous_ms1_owner")
```

- [ ] **Step 6: Run TSV writer tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_tsv_writer.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add xic_extractor/alignment/output_rows.py xic_extractor/alignment/tsv_writer.py tests/test_alignment_tsv_writer.py
git commit -m "refactor: share alignment output row helpers"
```

## Task 3: Add Production XLSX Writer

**Files:**
- Create: `xic_extractor/alignment/xlsx_writer.py`
- Test: `tests/test_alignment_xlsx_writer.py`

- [ ] **Step 1: Write workbook contract tests**

Create `tests/test_alignment_xlsx_writer.py`:

```python
from types import SimpleNamespace

from openpyxl import load_workbook

from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix
from xic_extractor.alignment.xlsx_writer import write_alignment_results_xlsx


def test_alignment_results_xlsx_has_matrix_review_metadata_sheets(tmp_path):
    matrix = _matrix()

    path = write_alignment_results_xlsx(
        tmp_path / "alignment_results.xlsx",
        matrix,
        metadata={"schema_version": "alignment-results-v1", "resolver_mode": "local_minimum"},
    )

    workbook = load_workbook(path, data_only=True)
    assert workbook.sheetnames == ["Matrix", "Review", "Metadata"]
    assert workbook["Matrix"]["A1"].value == "feature_family_id"
    assert workbook["Matrix"]["E2"].value == 100.0
    assert workbook["Matrix"]["F2"].value is None
    assert workbook["Review"]["A1"].value == "feature_family_id"
    assert workbook["Metadata"]["A1"].value == "key"


def _matrix():
    cluster = SimpleNamespace(
        feature_family_id="FAM000001",
        neutral_loss_tag="DNA_dR",
        family_center_mz=242.114,
        family_center_rt=12.593,
        family_product_mz=126.066,
        family_observed_neutral_loss_da=116.048,
        has_anchor=True,
        event_cluster_ids=("OWN-s1-000001",),
        event_member_count=1,
        evidence="owner_identity",
    )
    return AlignmentMatrix(
        clusters=(cluster,),
        sample_order=("s1", "s2"),
        cells=(
            _cell("s1", "FAM000001", "detected", 100.0),
            _cell("s2", "FAM000001", "ambiguous_ms1_owner", None),
        ),
    )


def _cell(sample, cluster_id, status, area):
    return AlignedCell(
        sample_stem=sample,
        cluster_id=cluster_id,
        status=status,
        area=area,
        apex_rt=12.593 if area else None,
        height=1000.0 if area else None,
        peak_start_rt=12.55 if area else None,
        peak_end_rt=12.64 if area else None,
        rt_delta_sec=0.0 if area else None,
        trace_quality=status,
        scan_support_score=None,
        source_candidate_id="s1#6095" if area else None,
        source_raw_file=None,
        reason=status,
    )
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_xlsx_writer.py -v
```

Expected: FAIL because `xlsx_writer.py` does not exist.

- [ ] **Step 3: Implement XLSX writer**

Create `xic_extractor/alignment/xlsx_writer.py`:

```python
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

from xic_extractor.alignment.matrix import AlignmentMatrix
from xic_extractor.alignment.output_rows import cells_by_cluster, matrix_area


def write_alignment_results_xlsx(
    path: Path,
    matrix: AlignmentMatrix,
    *,
    metadata: dict[str, str],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    matrix_sheet = workbook.active
    matrix_sheet.title = "Matrix"
    _write_matrix_sheet(matrix_sheet, matrix)
    review_sheet = workbook.create_sheet("Review")
    _write_review_sheet(review_sheet, matrix)
    metadata_sheet = workbook.create_sheet("Metadata")
    _write_metadata_sheet(metadata_sheet, metadata)
    workbook.save(path)
    return path


def _write_matrix_sheet(sheet, matrix: AlignmentMatrix) -> None:
    headers = ["feature_family_id", "neutral_loss_tag", "family_center_mz", "family_center_rt", *matrix.sample_order]
    sheet.append(headers)
    grouped_cells = cells_by_cluster(matrix)
    for cluster in matrix.clusters:
        row_id = str(cluster.feature_family_id)
        cells = {cell.sample_stem: cell for cell in grouped_cells.get(row_id, ())}
        sheet.append(
            [
                row_id,
                cluster.neutral_loss_tag,
                cluster.family_center_mz,
                cluster.family_center_rt,
                *[_xlsx_area(cells.get(sample)) for sample in matrix.sample_order],
            ]
        )


def _write_review_sheet(sheet, matrix: AlignmentMatrix) -> None:
    sheet.append(
        [
            "feature_family_id",
            "neutral_loss_tag",
            "detected_count",
            "rescued_count",
            "duplicate_assigned_count",
            "ambiguous_ms1_owner_count",
            "unchecked_count",
        ]
    )
    grouped_cells = cells_by_cluster(matrix)
    for cluster in matrix.clusters:
        row_id = str(cluster.feature_family_id)
        cells = grouped_cells.get(row_id, ())
        sheet.append(
            [
                row_id,
                cluster.neutral_loss_tag,
                _count(cells, "detected"),
                _count(cells, "rescued"),
                _count(cells, "duplicate_assigned"),
                _count(cells, "ambiguous_ms1_owner"),
                _count(cells, "unchecked"),
            ]
        )


def _write_metadata_sheet(sheet, metadata: dict[str, str]) -> None:
    sheet.append(["key", "value"])
    for key in sorted(metadata):
        sheet.append([key, metadata[key]])


def _xlsx_area(cell) -> float | None:
    text = matrix_area(cell)
    return float(text) if text else None


def _count(cells, status: str) -> int:
    return sum(1 for cell in cells if cell.status == status)
```

- [ ] **Step 4: Run XLSX tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_xlsx_writer.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/alignment/xlsx_writer.py tests/test_alignment_xlsx_writer.py
git commit -m "feat: write production alignment workbook"
```

## Task 4: Add Visual HTML Review Report

**Files:**
- Create: `xic_extractor/alignment/html_report.py`
- Test: `tests/test_alignment_html_report.py`

- [ ] **Step 1: Write HTML report tests**

Create `tests/test_alignment_html_report.py`:

```python
from tests.test_alignment_xlsx_writer import _matrix

from xic_extractor.alignment.html_report import write_alignment_review_html


def test_alignment_review_html_contains_visual_summary_not_full_cell_table(tmp_path):
    path = write_alignment_review_html(tmp_path / "review_report.html", _matrix())

    html = path.read_text(encoding="utf-8")
    assert "Alignment Review" in html
    assert "Detected / Rescued / Ambiguous" in html
    assert "Ownership pressure" in html
    assert "alignment_cells.tsv" not in html
    assert "<table" not in html.lower()
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_html_report.py -v
```

Expected: FAIL because `html_report.py` does not exist.

- [ ] **Step 3: Implement minimal static visual report**

Create `xic_extractor/alignment/html_report.py`:

```python
from __future__ import annotations

import html
from pathlib import Path

from xic_extractor.alignment.matrix import AlignmentMatrix


def write_alignment_review_html(path: Path, matrix: AlignmentMatrix) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    counts = _status_counts(matrix)
    max_count = max(counts.values(), default=1)
    bars = "\n".join(
        _bar(label, count, max_count)
        for label, count in counts.items()
    )
    path.write_text(
        f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Alignment Review</title>
<style>
body {{ font-family: Segoe UI, Arial, sans-serif; margin: 32px; color: #1f2933; }}
.chart {{ max-width: 960px; }}
.row {{ display: grid; grid-template-columns: 180px 1fr 80px; gap: 12px; align-items: center; margin: 10px 0; }}
.track {{ background: #e5e7eb; height: 20px; }}
.bar {{ background: #2563eb; height: 20px; }}
.warn {{ background: #b45309; }}
</style>
</head>
<body>
<h1>Alignment Review</h1>
<section class="chart">
<h2>Detected / Rescued / Ambiguous</h2>
{bars}
</section>
<section>
<h2>Ownership pressure</h2>
<p>{html.escape(_ownership_pressure_text(counts))}</p>
</section>
</body>
</html>
""",
        encoding="utf-8",
    )
    return path


def _status_counts(matrix: AlignmentMatrix) -> dict[str, int]:
    counts = {
        "detected": 0,
        "rescued": 0,
        "duplicate_assigned": 0,
        "ambiguous_ms1_owner": 0,
        "absent": 0,
        "unchecked": 0,
    }
    for cell in matrix.cells:
        counts[cell.status] = counts.get(cell.status, 0) + 1
    return counts


def _bar(label: str, count: int, max_count: int) -> str:
    width = 0 if max_count <= 0 else round(count / max_count * 100, 1)
    klass = "bar warn" if label in {"duplicate_assigned", "ambiguous_ms1_owner"} else "bar"
    return (
        f'<div class="row"><div>{html.escape(label)}</div>'
        f'<div class="track"><div class="{klass}" style="width:{width}%"></div></div>'
        f"<div>{count}</div></div>"
    )


def _ownership_pressure_text(counts: dict[str, int]) -> str:
    duplicate = counts.get("duplicate_assigned", 0)
    ambiguous = counts.get("ambiguous_ms1_owner", 0)
    if duplicate or ambiguous:
        return f"{duplicate} duplicate-assigned cells and {ambiguous} ambiguous owner cells need review."
    return "No duplicate-assigned or ambiguous owner cells were produced."
```

- [ ] **Step 4: Run HTML report tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_html_report.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor/alignment/html_report.py tests/test_alignment_html_report.py
git commit -m "feat: add alignment visual review report"
```

## Task 5: Wire Pipeline Output Levels

**Files:**
- Modify: `xic_extractor/alignment/pipeline.py`
- Modify: `scripts/run_alignment.py`
- Test: `tests/test_alignment_pipeline.py`
- Test: `tests/test_run_alignment.py`

- [ ] **Step 1: Add pipeline artifact-list tests**

Add to `tests/test_alignment_pipeline.py`:

```python
def test_run_alignment_production_level_writes_xlsx_and_html_only(tmp_path):
    outputs = _run_minimal_alignment(tmp_path, output_level="production")

    names = sorted(path.name for path in tmp_path.joinpath("out").iterdir())
    assert names == ["alignment_results.xlsx", "review_report.html"]
    assert outputs.workbook.name == "alignment_results.xlsx"
    assert outputs.review_html.name == "review_report.html"


def test_run_alignment_debug_level_writes_machine_and_debug_artifacts(tmp_path):
    _run_minimal_alignment(tmp_path, output_level="debug")

    names = sorted(path.name for path in tmp_path.joinpath("out").iterdir())
    assert names == [
        "alignment_cells.tsv",
        "alignment_matrix.tsv",
        "alignment_matrix_status.tsv",
        "alignment_results.xlsx",
        "alignment_review.tsv",
        "ambiguous_ms1_owners.tsv",
        "event_to_ms1_owner.tsv",
        "review_report.html",
    ]


def test_run_alignment_default_stays_machine_until_owner_validation_acceptance(tmp_path):
    _run_minimal_alignment(tmp_path)

    names = sorted(path.name for path in tmp_path.joinpath("out").iterdir())
    assert names == [
        "alignment_matrix.tsv",
        "alignment_results.xlsx",
        "alignment_review.tsv",
        "review_report.html",
    ]


def test_run_alignment_rolls_back_artifact_set_when_replace_fails(tmp_path, monkeypatch):
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    old_workbook = out_dir / "alignment_results.xlsx"
    old_html = out_dir / "review_report.html"
    old_workbook.write_text("old workbook", encoding="utf-8")
    old_html.write_text("old html", encoding="utf-8")
    replace_calls = 0
    original_replace = Path.replace

    def flaky_replace(self, target):
        nonlocal replace_calls
        replace_calls += 1
        if Path(target).name == "review_report.html":
            raise PermissionError("locked by Excel/browser")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", flaky_replace)

    with pytest.raises(PermissionError):
        _run_minimal_alignment(tmp_path, output_level="production")

    assert old_workbook.read_text(encoding="utf-8") == "old workbook"
    assert old_html.read_text(encoding="utf-8") == "old html"
```

Implement `_run_minimal_alignment()` using the existing fake batch/raw helpers in `tests/test_alignment_pipeline.py`; it should call `run_alignment(..., output_level=output_level)` only when `output_level` is not `None`. Use `None` as the helper default so the test covers the CLI/pipeline default.

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_pipeline.py::test_run_alignment_production_level_writes_xlsx_and_html_only tests/test_alignment_pipeline.py::test_run_alignment_debug_level_writes_machine_and_debug_artifacts tests/test_alignment_pipeline.py::test_run_alignment_default_stays_machine_until_owner_validation_acceptance tests/test_alignment_pipeline.py::test_run_alignment_rolls_back_artifact_set_when_replace_fails -v
```

Expected: FAIL because `run_alignment()` does not accept `output_level`.

- [ ] **Step 3: Extend pipeline outputs**

Modify `AlignmentRunOutputs`:

```python
@dataclass(frozen=True)
class AlignmentRunOutputs:
    workbook: Path
    review_html: Path
    matrix_tsv: Path | None = None
    review_tsv: Path | None = None
    cells_tsv: Path | None = None
    status_matrix_tsv: Path | None = None
    event_to_owner_tsv: Path | None = None
    ambiguous_owners_tsv: Path | None = None
```

Modify `run_alignment()` signature:

```python
    output_level: AlignmentOutputLevel = "machine",
```

Write artifacts according to `artifact_names_for_output_level(output_level)`.
This PR deliberately keeps `machine` as the default because TSVs are still the
trusted validation/debug surface while owner-based semantics are being accepted.
Changing the default to `production` is a separate gated task after 8-RAW and
85-RAW validation artifacts are reviewed.

Add imports:

```python
from collections.abc import Callable
```

Use an artifact-set writer rather than independent writes:

```python
def _write_alignment_artifacts_atomic(
    writers: tuple[tuple[Path, Callable[[Path], None]], ...],
) -> None:
    tmp_paths: list[Path] = []
    backup_paths: list[tuple[Path, Path]] = []
    replaced: list[Path] = []
    try:
        for final_path, writer in writers:
            tmp_path = final_path.with_name(f"{final_path.name}.tmp")
            writer(tmp_path)
            tmp_paths.append(tmp_path)
        for final_path, _writer in writers:
            if final_path.exists():
                backup_path = final_path.with_name(f"{final_path.name}.bak")
                if backup_path.exists():
                    backup_path.unlink()
                final_path.replace(backup_path)
                backup_paths.append((final_path, backup_path))
        for final_path, _writer in writers:
            tmp_path = final_path.with_name(f"{final_path.name}.tmp")
            tmp_path.replace(final_path)
            replaced.append(final_path)
    except Exception:
        for final_path in replaced:
            if final_path.exists():
                final_path.unlink()
        for final_path, backup_path in backup_paths:
            if backup_path.exists():
                backup_path.replace(final_path)
        raise
    finally:
        for tmp_path in tmp_paths:
            if tmp_path.exists():
                tmp_path.unlink()
        for _final_path, backup_path in backup_paths:
            if backup_path.exists():
                backup_path.unlink()
```

Construct writers conditionally:

```python
writers: list[tuple[Path, Callable[[Path], None]]] = [
    (outputs.workbook, lambda path: write_alignment_results_xlsx(path, matrix, metadata=_metadata(...))),
    (outputs.review_html, lambda path: write_alignment_review_html(path, matrix)),
]
if outputs.matrix_tsv is not None:
    writers.append((outputs.matrix_tsv, lambda path: write_alignment_matrix_tsv(path, matrix)))
if outputs.review_tsv is not None:
    writers.append((outputs.review_tsv, lambda path: write_alignment_review_tsv(path, matrix)))
_write_alignment_artifacts_atomic(tuple(writers))
```

The rollback rule applies to every artifact in the selected output level: failure
while writing temp files, backing up old files, or replacing final files must not
leave a mixed old/new production pair or machine pair.

- [ ] **Step 4: Add CLI flag**

In `scripts/run_alignment.py`, add:

```python
parser.add_argument(
    "--output-level",
    choices=("production", "machine", "debug", "validation"),
    default="machine",
    help=(
        "Alignment artifact level: production, machine, debug, or validation. "
        "Default remains machine until owner-based validation acceptance."
    ),
)
```

Pass `output_level=args.output_level` into `run_alignment()`.

- [ ] **Step 5: Update CLI tests**

Add to `tests/test_run_alignment.py`:

```python
def test_run_alignment_cli_accepts_output_level_debug(tmp_path):
    result = _run_cli(tmp_path, "--output-level", "debug")

    assert result.returncode == 0
    assert (tmp_path / "out" / "alignment_cells.tsv").exists()
    assert (tmp_path / "out" / "alignment_results.xlsx").exists()


def test_run_alignment_cli_default_is_machine_until_acceptance_gate(tmp_path):
    result = _run_cli(tmp_path)

    assert result.returncode == 0
    assert (tmp_path / "out" / "alignment_matrix.tsv").exists()
    assert (tmp_path / "out" / "alignment_review.tsv").exists()
    assert (tmp_path / "out" / "alignment_results.xlsx").exists()
    assert (tmp_path / "out" / "review_report.html").exists()
    assert not (tmp_path / "out" / "alignment_cells.tsv").exists()
```

If `tests/test_run_alignment.py` does not already provide a subprocess helper,
add this local helper:

```python
import subprocess
import sys


def _run_cli(tmp_path, *extra_args):
    batch_index, raw_dir, dll_dir = _prepare_minimal_alignment_inputs(tmp_path)
    output_dir = tmp_path / "out"
    return subprocess.run(
        [
            sys.executable,
            "scripts/run_alignment.py",
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--output-dir",
            str(output_dir),
            *extra_args,
        ],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )
```

Use the same `_prepare_minimal_alignment_inputs()` helper as the pipeline test
added in Task 5. That helper must write one candidate CSV, one batch index, and
one fake `.raw` path under `tmp_path`.

- [ ] **Step 6: Run pipeline and CLI tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_pipeline.py tests/test_run_alignment.py tests/test_alignment_output_levels.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add xic_extractor/alignment/pipeline.py scripts/run_alignment.py tests/test_alignment_pipeline.py tests/test_run_alignment.py
git commit -m "feat: wire untargeted alignment output levels"
```

## Task 6: Add Debug Ownership TSVs

**Files:**
- Create: `xic_extractor/alignment/debug_writer.py`
- Test: `tests/test_alignment_debug_writer.py`

- [ ] **Step 1: Write debug writer tests**

Create `tests/test_alignment_debug_writer.py`:

```python
from xic_extractor.alignment.debug_writer import (
    write_ambiguous_ms1_owners_tsv,
    write_event_to_ms1_owner_tsv,
)
from xic_extractor.alignment.ownership_models import AmbiguousOwnerRecord, OwnerAssignment


def test_event_to_owner_debug_tsv(tmp_path):
    path = write_event_to_ms1_owner_tsv(
        tmp_path / "event_to_ms1_owner.tsv",
        (
            OwnerAssignment("s1#6095", "OWN-s1-000001", "primary", "primary_identity_event"),
            OwnerAssignment("s1#6096", "OWN-s1-000001", "supporting", "owner_exact_apex_match"),
        ),
    )

    assert path.read_text(encoding="utf-8").splitlines() == [
        "candidate_id\towner_id\tassignment_status\treason",
        "s1#6095\tOWN-s1-000001\tprimary\tprimary_identity_event",
        "s1#6096\tOWN-s1-000001\tsupporting\towner_exact_apex_match",
    ]


def test_ambiguous_owner_debug_tsv(tmp_path):
    path = write_ambiguous_ms1_owners_tsv(
        tmp_path / "ambiguous_ms1_owners.tsv",
        (
            AmbiguousOwnerRecord(
                "AMB-s1-000001",
                "s1",
                ("s1#8001", "s1#8002"),
                "owner_multiplet_ambiguity",
            ),
        ),
    )

    assert path.read_text(encoding="utf-8").splitlines() == [
        "ambiguity_id\tsample_stem\tcandidate_ids\treason",
        "AMB-s1-000001\ts1\ts1#8001;s1#8002\towner_multiplet_ambiguity",
    ]
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_debug_writer.py -v
```

Expected: FAIL because `debug_writer.py` does not exist.

- [ ] **Step 3: Implement debug writer**

Create `xic_extractor/alignment/debug_writer.py`:

```python
from __future__ import annotations

import csv
from pathlib import Path

from xic_extractor.alignment.ownership_models import (
    AmbiguousOwnerRecord,
    OwnerAssignment,
)


def write_event_to_ms1_owner_tsv(
    path: Path,
    assignments: tuple[OwnerAssignment, ...],
) -> Path:
    rows = [
        {
            "candidate_id": assignment.candidate_id,
            "owner_id": assignment.owner_id or "",
            "assignment_status": assignment.assignment_status,
            "reason": assignment.reason,
        }
        for assignment in assignments
    ]
    return _write_tsv(
        path,
        ("candidate_id", "owner_id", "assignment_status", "reason"),
        rows,
    )


def write_ambiguous_ms1_owners_tsv(
    path: Path,
    records: tuple[AmbiguousOwnerRecord, ...],
) -> Path:
    rows = [
        {
            "ambiguity_id": record.ambiguity_id,
            "sample_stem": record.sample_stem,
            "candidate_ids": ";".join(record.candidate_ids),
            "reason": record.reason,
        }
        for record in records
    ]
    return _write_tsv(
        path,
        ("ambiguity_id", "sample_stem", "candidate_ids", "reason"),
        rows,
    )


def _write_tsv(path: Path, fieldnames: tuple[str, ...], rows: list[dict[str, str]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return path
```

- [ ] **Step 4: Wire debug TSVs into debug output level**

In `xic_extractor/alignment/pipeline.py`, retain the `ownership` build result and call:

```python
if outputs.event_to_owner_tsv is not None:
    write_event_to_ms1_owner_tsv(outputs.event_to_owner_tsv, ownership.assignments)
if outputs.ambiguous_owners_tsv is not None:
    write_ambiguous_ms1_owners_tsv(outputs.ambiguous_owners_tsv, ownership.ambiguous_records)
```

- [ ] **Step 5: Run debug writer and pipeline tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_debug_writer.py tests/test_alignment_pipeline.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add xic_extractor/alignment/debug_writer.py tests/test_alignment_debug_writer.py xic_extractor/alignment/pipeline.py tests/test_alignment_pipeline.py
git commit -m "feat: emit opt-in MS1 owner debug tables"
```

## Task 7: Final Verification

**Files:**
- No code changes unless tests expose a reproducible bug.

- [ ] **Step 1: Run output tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_output_levels.py tests/test_alignment_xlsx_writer.py tests/test_alignment_html_report.py tests/test_alignment_debug_writer.py -v
```

Expected: PASS.

- [ ] **Step 2: Run alignment contract tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_pipeline.py tests/test_run_alignment.py tests/test_alignment_tsv_writer.py tests/test_alignment_owner_matrix.py -v
```

Expected: PASS.

- [ ] **Step 3: Run ruff**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor/alignment scripts tests/test_alignment_output_levels.py tests/test_alignment_xlsx_writer.py tests/test_alignment_html_report.py
```

Expected: PASS.

- [ ] **Step 4: Run production output smoke**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts/run_alignment.py --discovery-batch-index output\discovery_8raw\discovery_batch_index.csv --raw-dir "C:\Xcalibur\data\20251219_need process data\XIC test" --dll-dir "C:\Xcalibur\system\programs" --output-dir output\alignment\production_output_smoke --output-level production
```

Expected:

- `alignment_results.xlsx` exists;
- `review_report.html` exists;
- no TSV files exist in the production output directory.

## Acceptance Criteria

- Production output is XLSX + HTML.
- Current CLI default remains `machine` until owner-based validation acceptance;
  `production` is available by explicit `--output-level production`.
- Machine/debug TSVs are selected by output level, not mixed into explicit
  production runs.
- All artifacts in the selected output level are written as one rollback-protected
  artifact set; failures cannot leave mixed old/new XLSX/HTML/TSV pairs.
- XLSX `Matrix` sheet blanks missing/duplicate/ambiguous values.
- HTML contains visual summary blocks and does not duplicate the full cell table.
- Debug owner/event evidence remains available through debug output level.

## Stop Conditions

Stop and report before changing defaults if:

- Owner-based alignment validation has not passed on the 8-RAW smoke set.
- Workbook writer cannot preserve blank semantics for missing/duplicate/ambiguous cells.
- HTML review becomes a table dump rather than a visual QC entry point.
