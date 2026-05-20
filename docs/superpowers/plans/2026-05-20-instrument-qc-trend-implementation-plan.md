# Instrument QC Trend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an opt-in instrument-only QC pipeline that discovers SDOLEK RAW files, extracts SDO/LEK MS1 trend evidence, and emits TSV/JSON diagnostics without changing targeted or untargeted production outputs.

**Architecture:** Add a new `xic_extractor.instrument_qc` package with focused classification, target constants, models, pipeline orchestration, and writers. The existing extraction pipeline remains unchanged; `scripts/run_instrument_qc.py` is the only Phase 1 entry point.

**Tech Stack:** Python 3.14-compatible code, `pytest`, `uv`, existing `raw_reader.open_raw`, existing `signal_processing.find_peak_and_area`, existing `injection_rolling.read_injection_order`.

---

## Scope

Implement Phase 1 from `docs/superpowers/specs/2026-05-20-instrument-only-qc-trend-spec.md`.

In scope:

- Independent `instrument_qc.classification`.
- Fixed SDO/LEK MS1 targets.
- SDOLEK RAW discovery under `<raw-dir>/SDOLEK/*.raw`.
- SDO/LEK MS1 XIC extraction with `find_peak_and_area`.
- Machine-readable TSV / JSON / diagnostics outputs.
- Optional injection-order file using existing `Sample_Name,Injection_Order` contract.
- Separate CLI: `scripts/run_instrument_qc.py`.

Out of scope:

- No workbook output.
- No `xic_results` changes.
- No `scripts/run_extraction.py` integration.
- No `sample_groups.py` changes.
- No MixSTDs / Blank / HCD / wHCD / lifecycle dataset.
- No hidden writes to user home.

## File Structure

Create:

- `xic_extractor/instrument_qc/__init__.py`
  - Public package exports only.
- `xic_extractor/instrument_qc/classification.py`
  - Path-aware instrument-only RAW classification. No RAW IO.
- `xic_extractor/instrument_qc/targets.py`
  - SDO/LEK constants and NoSplit priors.
- `xic_extractor/instrument_qc/models.py`
  - Dataclasses and literal enums for rows, diagnostics, and run outputs.
- `xic_extractor/instrument_qc/pipeline.py`
  - Discovery, extraction orchestration, injection-order join, result assembly.
- `xic_extractor/instrument_qc/writers.py`
  - TSV and JSON serialization only.
- `scripts/run_instrument_qc.py`
  - CLI parsing, exit codes, and user-facing errors.
- `tests/test_instrument_qc_classification.py`
- `tests/test_instrument_qc_pipeline.py`
- `tests/test_instrument_qc_writers.py`
- `tests/test_run_instrument_qc.py`

Modify only if needed:

- `pyproject.toml`
  - Add an optional console script only if repo conventions require it. Do not add this unless tests explicitly target it.

Do not modify:

- `xic_extractor/sample_groups.py`
- `scripts/run_extraction.py`
- targeted extraction modules
- untargeted alignment modules
- workbook output modules

## Shared Constants And Defaults

Use these exact Phase 1 constants unless a later reviewed plan changes them:

```python
SDO_MZ = 311.0814
LEK_MZ = 556.2771
SDO_REFERENCE_RT_MIN = 6.26
LEK_REFERENCE_RT_MIN = 6.40
SDO_REFERENCE_BASE_WIDTH_MIN = 0.83
LEK_REFERENCE_BASE_WIDTH_MIN = 0.85
SDOLEK_IDENTITY_EVIDENCE = "MS1_ONLY"
DEFAULT_RT_MIN = 0.0
DEFAULT_RT_MAX = 12.0
DEFAULT_PPM_TOL = 10.0
```

Trend confidence v1:

- `clean`: detected, no trend flags.
- `warning`: detected with one or more trend flags.
- `low`: not detected or extraction error.

Trend flags v1:

- `RT_OUTLIER`: `abs(apex_rt_min - reference_rt_min) > 0.50`.
- `WIDTH_OUTLIER`: `base_width_ratio_to_reference < 0.50` or `> 1.75`.
- `LOW_PEAK_CONFIDENCE`: peak status is not `OK`, or peak is missing.

These thresholds are intentionally review flags, not pass/fail identity gates.

---

## Checkpoint 0: Worktree Guard And Plan Commit

**Files:**

- Create: `docs/superpowers/plans/2026-05-20-instrument-qc-trend-implementation-plan.md`

- [ ] **Step 1: Confirm worktree and branch**

Run:

```powershell
git -C C:\Users\user\Desktop\XIC_Extractor\.worktrees\instrument-qc-trend status --short --branch
```

Expected:

```text
## codex/instrument-qc-trend...origin/master [ahead 3]
```

or the same branch with only this plan file dirty.

- [ ] **Step 2: Confirm no production code is dirty before implementation**

Run:

```powershell
git -C C:\Users\user\Desktop\XIC_Extractor\.worktrees\instrument-qc-trend diff --name-only
```

Expected before committing this plan:

```text
docs/superpowers/plans/2026-05-20-instrument-qc-trend-implementation-plan.md
```

- [ ] **Step 3: Commit the plan**

Run:

```powershell
git -C C:\Users\user\Desktop\XIC_Extractor\.worktrees\instrument-qc-trend add docs/superpowers/plans/2026-05-20-instrument-qc-trend-implementation-plan.md
git -C C:\Users\user\Desktop\XIC_Extractor\.worktrees\instrument-qc-trend commit -m "docs: plan instrument qc trend implementation"
```

Review gate:

- Plan commit contains docs only.
- Plan does not require changing `sample_groups.py`.

---

## Checkpoint 1: Classification, Targets, And Models

**Files:**

- Create: `xic_extractor/instrument_qc/__init__.py`
- Create: `xic_extractor/instrument_qc/classification.py`
- Create: `xic_extractor/instrument_qc/targets.py`
- Create: `xic_extractor/instrument_qc/models.py`
- Test: `tests/test_instrument_qc_classification.py`

### Task 1.1: Write Classification Tests

- [ ] **Step 1: Create the failing classification test file**

Create `tests/test_instrument_qc_classification.py`:

```python
from pathlib import Path

from xic_extractor.instrument_qc.classification import (
    InstrumentQCClass,
    classify_instrument_qc_raw,
)


def test_sdolek_folder_classifies_as_sdolek() -> None:
    root = Path("C:/data/batch")
    raw = root / "SDOLEK" / "SDO LEK - 1.raw"

    assert classify_instrument_qc_raw(raw, root) == InstrumentQCClass.SDOLEK


def test_sdolek_filename_classifies_as_sdolek() -> None:
    root = Path("C:/data/batch")
    raw = root / "validation" / "SDOLEK-pretest.raw"

    assert classify_instrument_qc_raw(raw, root) == InstrumentQCClass.SDOLEK


def test_biological_root_raw_is_not_instrument_qc() -> None:
    root = Path("C:/data/batch")
    raw = root / "TumorBC2257_DNA.raw"

    assert classify_instrument_qc_raw(raw, root) is None


def test_non_sdolek_folders_are_not_phase1_instrument_qc() -> None:
    root = Path("C:/data/batch")

    for folder in ("RNA", "Pairs", "validation", "except sample", "STDs"):
        raw = root / folder / "TumorBC2257_DNA.raw"
        assert classify_instrument_qc_raw(raw, root) is None


def test_classification_is_path_only_and_does_not_require_existing_file() -> None:
    root = Path("C:/missing/batch")
    raw = root / "SDOLEK" / "missing.raw"

    assert classify_instrument_qc_raw(raw, root) == InstrumentQCClass.SDOLEK
```

- [ ] **Step 2: Run tests and verify they fail because module is missing**

Run:

```powershell
uv --cache-dir .uv-cache run pytest tests\test_instrument_qc_classification.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'xic_extractor.instrument_qc'
```

### Task 1.2: Implement Classification And Targets

- [ ] **Step 1: Add package init**

Create `xic_extractor/instrument_qc/__init__.py`:

```python
"""Instrument-only QC helpers for opt-in acquisition trend reports."""
```

- [ ] **Step 2: Add classification module**

Create `xic_extractor/instrument_qc/classification.py`:

```python
from enum import StrEnum
from pathlib import Path


class InstrumentQCClass(StrEnum):
    SDOLEK = "SDOLEK"


def classify_instrument_qc_raw(
    raw_path: Path,
    data_root: Path,
) -> InstrumentQCClass | None:
    """Classify instrument-only RAW files from path context only."""
    try:
        relative_parts = raw_path.resolve().relative_to(data_root.resolve()).parts
    except ValueError:
        relative_parts = raw_path.parts

    folder_parts = [part.casefold() for part in relative_parts[:-1]]
    stem = raw_path.stem.strip().casefold()

    if any(part == "sdolek" for part in folder_parts):
        return InstrumentQCClass.SDOLEK
    if stem.startswith("sdolek") or stem.startswith("sdo"):
        return InstrumentQCClass.SDOLEK
    return None
```

- [ ] **Step 3: Add target constants**

Create `xic_extractor/instrument_qc/targets.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class InstrumentQCTarget:
    compound: str
    precursor_mz: float
    reference_mz: float
    reference_rt_min: float
    reference_base_width_min: float
    rt_min: float = 0.0
    rt_max: float = 12.0
    ppm_tol: float = 10.0


SDOLEK_TARGETS: tuple[InstrumentQCTarget, ...] = (
    InstrumentQCTarget(
        compound="SDO",
        precursor_mz=311.0814,
        reference_mz=311.0814,
        reference_rt_min=6.26,
        reference_base_width_min=0.83,
    ),
    InstrumentQCTarget(
        compound="LEK",
        precursor_mz=556.2771,
        reference_mz=556.2772,
        reference_rt_min=6.40,
        reference_base_width_min=0.85,
    ),
)
```

### Task 1.3: Add Models

- [ ] **Step 1: Create model dataclasses**

Create `xic_extractor/instrument_qc/models.py`:

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


TrendConfidence = Literal["clean", "warning", "low"]
InstrumentQCStatus = Literal["detected", "not_detected", "error"]


@dataclass(frozen=True)
class InstrumentQCDiagnostic:
    sample_name: str
    raw_path: Path
    issue: str
    detail: str


@dataclass(frozen=True)
class SDOLEKTrendRow:
    sample_name: str
    raw_path: Path
    injection_order: int | None
    compound: str
    precursor_mz: float
    identity_evidence: str
    reference_rt_min: float | None
    rt_delta_to_reference_min: float | None
    apex_rt_min: float | None
    area: float | None
    base_width_min: float | None
    reference_base_width_min: float | None
    base_width_ratio_to_reference: float | None
    peak_start_rt_min: float | None
    peak_end_rt_min: float | None
    trend_confidence: TrendConfidence
    trend_flags: tuple[str, ...]
    status: InstrumentQCStatus
    reason: str


@dataclass(frozen=True)
class InstrumentQCRunOutput:
    trend_rows: tuple[SDOLEKTrendRow, ...]
    diagnostics: tuple[InstrumentQCDiagnostic, ...]
    trend_tsv: Path
    trend_json: Path
    diagnostics_tsv: Path
```

- [ ] **Step 2: Run classification tests**

Run:

```powershell
uv --cache-dir .uv-cache run pytest tests\test_instrument_qc_classification.py -q
```

Expected:

```text
5 passed
```

- [ ] **Step 3: Review checkpoint 1 diff**

Run:

```powershell
git -C C:\Users\user\Desktop\XIC_Extractor\.worktrees\instrument-qc-trend diff -- xic_extractor\instrument_qc tests\test_instrument_qc_classification.py
```

Review checklist:

- `sample_groups.py` unchanged.
- No imports from workbook, GUI, alignment, or extraction pipeline.
- Classification does not open RAW files.

- [ ] **Step 4: Commit checkpoint 1**

Run:

```powershell
git -C C:\Users\user\Desktop\XIC_Extractor\.worktrees\instrument-qc-trend add xic_extractor/instrument_qc tests/test_instrument_qc_classification.py
git -C C:\Users\user\Desktop\XIC_Extractor\.worktrees\instrument-qc-trend commit -m "feat: add instrument qc classification models"
```

---

## Checkpoint 2: SDOLEK Pipeline And Writers

**Files:**

- Create: `xic_extractor/instrument_qc/pipeline.py`
- Create: `xic_extractor/instrument_qc/writers.py`
- Test: `tests/test_instrument_qc_pipeline.py`
- Test: `tests/test_instrument_qc_writers.py`

### Task 2.1: Write Pipeline Tests With Fake RAW Source

- [ ] **Step 1: Create pipeline test file**

Create `tests/test_instrument_qc_pipeline.py`:

```python
from pathlib import Path

import numpy as np

from xic_extractor.instrument_qc.pipeline import run_sdolek_pipeline


class FakeRaw:
    def __init__(self, traces: dict[float, tuple[np.ndarray, np.ndarray]]) -> None:
        self.traces = traces
        self.requests: list[tuple[float, float, float, float]] = []

    def __enter__(self) -> "FakeRaw":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def extract_xic(
        self,
        mz: float,
        rt_min: float,
        rt_max: float,
        ppm_tol: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        self.requests.append((mz, rt_min, rt_max, ppm_tol))
        return self.traces[mz]


def _write_raw(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


def _trace(apex_rt: float) -> tuple[np.ndarray, np.ndarray]:
    rt = np.array([apex_rt - 0.2, apex_rt, apex_rt + 0.2])
    intensity = np.array([0.0, 1000.0, 0.0])
    return rt, intensity


def test_sdolek_pipeline_extracts_two_compounds_and_writes_outputs(
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "raw"
    raw_path = raw_root / "SDOLEK" / "SDO LEK - 1.raw"
    _write_raw(raw_path)
    output_dir = tmp_path / "out"
    injection_order = tmp_path / "order.csv"
    injection_order.write_text(
        "Sample_Name,Injection_Order\nSDO LEK - 1,4\n",
        encoding="utf-8",
    )

    fake_raw = FakeRaw(
        {
            311.0814: _trace(6.26),
            556.2771: _trace(6.40),
        }
    )

    output = run_sdolek_pipeline(
        raw_dir=raw_root,
        output_dir=output_dir,
        injection_order_source=injection_order,
        raw_opener=lambda _path: fake_raw,
    )

    assert len(output.trend_rows) == 2
    assert {row.compound for row in output.trend_rows} == {"SDO", "LEK"}
    assert {row.injection_order for row in output.trend_rows} == {4}
    assert all(row.identity_evidence == "MS1_ONLY" for row in output.trend_rows)
    assert output.trend_tsv.exists()
    assert output.trend_json.exists()
    assert output.diagnostics_tsv.exists()


def test_sdolek_pipeline_reports_missing_injection_order_without_failing(
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "raw"
    raw_path = raw_root / "SDOLEK" / "SDOLEK-pretest.raw"
    _write_raw(raw_path)

    output = run_sdolek_pipeline(
        raw_dir=raw_root,
        output_dir=tmp_path / "out",
        raw_opener=lambda _path: FakeRaw(
            {
                311.0814: _trace(6.26),
                556.2771: _trace(6.40),
            }
        ),
    )

    assert all(row.injection_order is None for row in output.trend_rows)
    assert any(diag.issue == "INJECTION_ORDER_MISSING" for diag in output.diagnostics)


def test_sdolek_pipeline_ignores_biological_root_raws(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    _write_raw(raw_root / "TumorBC2257_DNA.raw")
    _write_raw(raw_root / "SDOLEK" / "SDO-posttest.raw")

    output = run_sdolek_pipeline(
        raw_dir=raw_root,
        output_dir=tmp_path / "out",
        raw_opener=lambda _path: FakeRaw(
            {
                311.0814: _trace(6.26),
                556.2771: _trace(6.40),
            }
        ),
    )

    assert {row.sample_name for row in output.trend_rows} == {"SDO-posttest"}


def test_sdolek_pipeline_fails_clearly_when_sdolek_folder_missing(
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "raw"
    raw_root.mkdir()

    try:
        run_sdolek_pipeline(
            raw_dir=raw_root,
            output_dir=tmp_path / "out",
            raw_opener=lambda _path: FakeRaw({}),
        )
    except FileNotFoundError as exc:
        assert "SDOLEK" in str(exc)
    else:
        raise AssertionError("Expected missing SDOLEK folder to fail clearly")
```

- [ ] **Step 2: Run pipeline tests and verify they fail**

Run:

```powershell
uv --cache-dir .uv-cache run pytest tests\test_instrument_qc_pipeline.py -q
```

Expected:

```text
ModuleNotFoundError: No module named 'xic_extractor.instrument_qc.pipeline'
```

### Task 2.2: Write Writer Tests

- [ ] **Step 1: Create writer test file**

Create `tests/test_instrument_qc_writers.py`:

```python
import csv
import json
from pathlib import Path

from xic_extractor.instrument_qc.models import (
    InstrumentQCDiagnostic,
    SDOLEKTrendRow,
)
from xic_extractor.instrument_qc.writers import (
    TREND_TSV_COLUMNS,
    write_diagnostics_tsv,
    write_sdolek_json,
    write_trend_tsv,
)


def _row(raw_path: Path) -> SDOLEKTrendRow:
    return SDOLEKTrendRow(
        sample_name="SDOLEK-pretest",
        raw_path=raw_path,
        injection_order=4,
        compound="SDO",
        precursor_mz=311.0814,
        identity_evidence="MS1_ONLY",
        reference_rt_min=6.26,
        rt_delta_to_reference_min=0.01,
        apex_rt_min=6.27,
        area=123.4,
        base_width_min=0.83,
        reference_base_width_min=0.83,
        base_width_ratio_to_reference=1.0,
        peak_start_rt_min=5.90,
        peak_end_rt_min=6.73,
        trend_confidence="clean",
        trend_flags=(),
        status="detected",
        reason="OK",
    )


def test_write_trend_tsv_uses_contract_columns(tmp_path: Path) -> None:
    path = tmp_path / "trend.tsv"
    write_trend_tsv(path, [_row(tmp_path / "a.raw")])

    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = list(reader)

    assert reader.fieldnames == TREND_TSV_COLUMNS
    assert rows[0]["compound"] == "SDO"
    assert rows[0]["identity_evidence"] == "MS1_ONLY"


def test_write_diagnostics_tsv_uses_contract_columns(tmp_path: Path) -> None:
    path = tmp_path / "diagnostics.tsv"
    write_diagnostics_tsv(
        path,
        [
            InstrumentQCDiagnostic(
                sample_name="S1",
                raw_path=tmp_path / "S1.raw",
                issue="INJECTION_ORDER_MISSING",
                detail="No injection-order file supplied.",
            )
        ],
    )

    text = path.read_text(encoding="utf-8")
    assert text.splitlines()[0] == "sample_name\traw_path\tissue\tdetail"


def test_write_sdolek_json_contains_summary_and_rows(tmp_path: Path) -> None:
    path = tmp_path / "trend.json"
    write_sdolek_json(
        path,
        [_row(tmp_path / "a.raw")],
        [
            InstrumentQCDiagnostic(
                sample_name="S1",
                raw_path=tmp_path / "S1.raw",
                issue="INJECTION_ORDER_MISSING",
                detail="No injection-order file supplied.",
            )
        ],
    )

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["summary"]["total_rows"] == 1
    assert payload["summary"]["status_counts"] == {"detected": 1}
    assert payload["rows"][0]["compound"] == "SDO"
```

### Task 2.3: Implement Writers

- [ ] **Step 1: Add writer module**

Create `xic_extractor/instrument_qc/writers.py`:

```python
import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from xic_extractor.instrument_qc.models import (
    InstrumentQCDiagnostic,
    SDOLEKTrendRow,
)


TREND_TSV_COLUMNS = [
    "sample_name",
    "raw_path",
    "injection_order",
    "compound",
    "precursor_mz",
    "identity_evidence",
    "reference_rt_min",
    "rt_delta_to_reference_min",
    "apex_rt_min",
    "area",
    "base_width_min",
    "reference_base_width_min",
    "base_width_ratio_to_reference",
    "peak_start_rt_min",
    "peak_end_rt_min",
    "trend_confidence",
    "trend_flags",
    "status",
    "reason",
]

DIAGNOSTIC_TSV_COLUMNS = ["sample_name", "raw_path", "issue", "detail"]


def write_trend_tsv(path: Path, rows: Iterable[SDOLEKTrendRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=TREND_TSV_COLUMNS, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow(_trend_row_to_dict(row))


def write_diagnostics_tsv(
    path: Path,
    diagnostics: Iterable[InstrumentQCDiagnostic],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=DIAGNOSTIC_TSV_COLUMNS,
            delimiter="\t",
        )
        writer.writeheader()
        for diagnostic in diagnostics:
            writer.writerow(
                {
                    "sample_name": diagnostic.sample_name,
                    "raw_path": str(diagnostic.raw_path),
                    "issue": diagnostic.issue,
                    "detail": diagnostic.detail,
                }
            )


def write_sdolek_json(
    path: Path,
    rows: Iterable[SDOLEKTrendRow],
    diagnostics: Iterable[InstrumentQCDiagnostic],
) -> None:
    row_list = list(rows)
    diagnostic_list = list(diagnostics)
    payload = {
        "summary": {
            "total_rows": len(row_list),
            "status_counts": _counts(row.status for row in row_list),
            "compound_counts": _counts(row.compound for row in row_list),
            "diagnostic_counts": _counts(diag.issue for diag in diagnostic_list),
        },
        "rows": [_trend_row_to_dict(row) for row in row_list],
        "diagnostics": [_diagnostic_to_dict(diag) for diag in diagnostic_list],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _trend_row_to_dict(row: SDOLEKTrendRow) -> dict[str, object]:
    values = asdict(row)
    values["raw_path"] = str(row.raw_path)
    values["trend_flags"] = ";".join(row.trend_flags)
    return values


def _diagnostic_to_dict(diagnostic: InstrumentQCDiagnostic) -> dict[str, object]:
    return {
        "sample_name": diagnostic.sample_name,
        "raw_path": str(diagnostic.raw_path),
        "issue": diagnostic.issue,
        "detail": diagnostic.detail,
    }


def _counts(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts
```

### Task 2.4: Implement Pipeline

- [ ] **Step 1: Add pipeline module**

Create `xic_extractor/instrument_qc/pipeline.py`:

```python
from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Protocol

import numpy as np

from xic_extractor.config import ExtractionConfig
from xic_extractor.injection_rolling import read_injection_order
from xic_extractor.instrument_qc.classification import (
    InstrumentQCClass,
    classify_instrument_qc_raw,
)
from xic_extractor.instrument_qc.models import (
    InstrumentQCDiagnostic,
    InstrumentQCRunOutput,
    InstrumentQCStatus,
    SDOLEKTrendRow,
)
from xic_extractor.instrument_qc.targets import InstrumentQCTarget, SDOLEK_TARGETS
from xic_extractor.instrument_qc.writers import (
    write_diagnostics_tsv,
    write_sdolek_json,
    write_trend_tsv,
)
from xic_extractor.raw_reader import open_raw
from xic_extractor.signal_processing import find_peak_and_area


class XICSource(Protocol):
    def extract_xic(
        self,
        mz: float,
        rt_min: float,
        rt_max: float,
        ppm_tol: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        ...


RawOpener = Callable[[Path], AbstractContextManager[XICSource]]


def run_sdolek_pipeline(
    *,
    raw_dir: Path,
    output_dir: Path,
    injection_order_source: Path | None = None,
    dll_dir: Path | None = None,
    raw_opener: RawOpener | None = None,
) -> InstrumentQCRunOutput:
    diagnostics: list[InstrumentQCDiagnostic] = []
    raw_paths = _discover_sdolek_raws(raw_dir, diagnostics)
    injection_order = _read_optional_injection_order(
        injection_order_source,
        raw_paths,
        diagnostics,
    )
    opener = raw_opener or (lambda path: open_raw(path, dll_dir or Path("lib")))
    rows: list[SDOLEKTrendRow] = []

    for raw_path in raw_paths:
        sample_name = raw_path.stem
        try:
            with opener(raw_path) as raw:
                for target in SDOLEK_TARGETS:
                    try:
                        rows.append(
                            _extract_target_row(
                                raw=raw,
                                raw_path=raw_path,
                                sample_name=sample_name,
                                injection_order=injection_order.get(sample_name),
                                target=target,
                            )
                        )
                    except Exception as exc:
                        diagnostics.append(
                            InstrumentQCDiagnostic(
                                sample_name=sample_name,
                                raw_path=raw_path,
                                issue="TARGET_EXTRACTION_ERROR",
                                detail=f"{target.compound}: {exc}",
                            )
                        )
                        rows.append(
                            _error_row(
                                raw_path=raw_path,
                                sample_name=sample_name,
                                injection_order=injection_order.get(sample_name),
                                target=target,
                                reason=str(exc),
                            )
                        )
        except Exception as exc:
            diagnostics.append(
                InstrumentQCDiagnostic(
                    sample_name=sample_name,
                    raw_path=raw_path,
                    issue="RAW_EXTRACTION_ERROR",
                    detail=str(exc),
                )
            )
            rows.extend(
                _error_row(
                    raw_path=raw_path,
                    sample_name=sample_name,
                    injection_order=injection_order.get(sample_name),
                    target=target,
                    reason=str(exc),
                )
                for target in SDOLEK_TARGETS
            )

    trend_tsv = output_dir / "instrument_qc_sdolek_trend.tsv"
    trend_json = output_dir / "instrument_qc_sdolek_trend.json"
    diagnostics_tsv = output_dir / "instrument_qc_sdolek_diagnostics.tsv"
    write_trend_tsv(trend_tsv, rows)
    write_sdolek_json(trend_json, rows, diagnostics)
    write_diagnostics_tsv(diagnostics_tsv, diagnostics)
    return InstrumentQCRunOutput(
        trend_rows=tuple(rows),
        diagnostics=tuple(diagnostics),
        trend_tsv=trend_tsv,
        trend_json=trend_json,
        diagnostics_tsv=diagnostics_tsv,
    )


def _discover_sdolek_raws(
    raw_dir: Path,
    diagnostics: list[InstrumentQCDiagnostic],
) -> tuple[Path, ...]:
    sdolek_dir = raw_dir / "SDOLEK"
    if not sdolek_dir.exists():
        raise FileNotFoundError(f"Missing expected SDOLEK folder: {sdolek_dir}")
    candidates = sorted(sdolek_dir.glob("*.raw"))
    selected: list[Path] = []
    seen_stems: set[str] = set()
    for path in candidates:
        if classify_instrument_qc_raw(path, raw_dir) != InstrumentQCClass.SDOLEK:
            continue
        normalized_stem = path.stem.casefold()
        if normalized_stem in seen_stems:
            diagnostics.append(
                InstrumentQCDiagnostic(
                    sample_name=path.stem,
                    raw_path=path,
                    issue="DUPLICATE_RAW_STEM",
                    detail="Duplicate SDOLEK RAW stem skipped.",
                )
            )
            continue
        seen_stems.add(normalized_stem)
        selected.append(path)
    return tuple(selected)


def _read_optional_injection_order(
    path: Path | None,
    raw_paths: tuple[Path, ...],
    diagnostics: list[InstrumentQCDiagnostic],
) -> dict[str, int]:
    if path is None:
        for raw_path in raw_paths:
            diagnostics.append(
                InstrumentQCDiagnostic(
                    sample_name=raw_path.stem,
                    raw_path=raw_path,
                    issue="INJECTION_ORDER_MISSING",
                    detail="No injection-order file supplied.",
                )
            )
        return {}
    return read_injection_order(path)


def _extract_target_row(
    *,
    raw: XICSource,
    raw_path: Path,
    sample_name: str,
    injection_order: int | None,
    target: InstrumentQCTarget,
) -> SDOLEKTrendRow:
    rt, intensity = raw.extract_xic(
        mz=target.precursor_mz,
        rt_min=target.rt_min,
        rt_max=target.rt_max,
        ppm_tol=target.ppm_tol,
    )
    result = find_peak_and_area(rt, intensity, _peak_config(raw_path.parent))
    if result.peak is None or result.status != "OK":
        return _error_row(
            raw_path=raw_path,
            sample_name=sample_name,
            injection_order=injection_order,
            target=target,
            reason=result.status,
            status="not_detected",
        )
    peak = result.peak
    base_width = peak.peak_end - peak.peak_start
    rt_delta = peak.rt - target.reference_rt_min
    width_ratio = (
        base_width / target.reference_base_width_min
        if target.reference_base_width_min
        else None
    )
    flags = _trend_flags(rt_delta=rt_delta, width_ratio=width_ratio)
    return SDOLEKTrendRow(
        sample_name=sample_name,
        raw_path=raw_path,
        injection_order=injection_order,
        compound=target.compound,
        precursor_mz=target.precursor_mz,
        identity_evidence="MS1_ONLY",
        reference_rt_min=target.reference_rt_min,
        rt_delta_to_reference_min=rt_delta,
        apex_rt_min=peak.rt,
        area=peak.area,
        base_width_min=base_width,
        reference_base_width_min=target.reference_base_width_min,
        base_width_ratio_to_reference=width_ratio,
        peak_start_rt_min=peak.peak_start,
        peak_end_rt_min=peak.peak_end,
        trend_confidence="warning" if flags else "clean",
        trend_flags=flags,
        status="detected",
        reason="OK",
    )


def _error_row(
    *,
    raw_path: Path,
    sample_name: str,
    injection_order: int | None,
    target: InstrumentQCTarget,
    reason: str,
    status: InstrumentQCStatus = "error",
) -> SDOLEKTrendRow:
    return SDOLEKTrendRow(
        sample_name=sample_name,
        raw_path=raw_path,
        injection_order=injection_order,
        compound=target.compound,
        precursor_mz=target.precursor_mz,
        identity_evidence="MS1_ONLY",
        reference_rt_min=target.reference_rt_min,
        rt_delta_to_reference_min=None,
        apex_rt_min=None,
        area=None,
        base_width_min=None,
        reference_base_width_min=target.reference_base_width_min,
        base_width_ratio_to_reference=None,
        peak_start_rt_min=None,
        peak_end_rt_min=None,
        trend_confidence="low",
        trend_flags=("LOW_PEAK_CONFIDENCE",),
        status=status,
        reason=reason,
    )


def _trend_flags(
    *,
    rt_delta: float,
    width_ratio: float | None,
) -> tuple[str, ...]:
    flags: list[str] = []
    if abs(rt_delta) > 0.50:
        flags.append("RT_OUTLIER")
    if width_ratio is not None and (width_ratio < 0.50 or width_ratio > 1.75):
        flags.append("WIDTH_OUTLIER")
    return tuple(flags)


def _peak_config(data_dir: Path) -> ExtractionConfig:
    return ExtractionConfig(
        data_dir=data_dir,
        dll_dir=Path("lib"),
        output_csv=Path("instrument_qc.csv"),
        diagnostics_csv=Path("instrument_qc_diagnostics.csv"),
        smooth_window=7,
        smooth_polyorder=2,
        peak_rel_height=0.5,
        peak_min_prominence_ratio=0.05,
        ms2_precursor_tol_da=0.5,
        nl_min_intensity_ratio=0.01,
        resolver_mode="local_minimum",
    )
```

- [ ] **Step 2: Run focused tests**

Run:

```powershell
uv --cache-dir .uv-cache run pytest tests\test_instrument_qc_pipeline.py tests\test_instrument_qc_writers.py -q
```

Expected:

```text
6 passed
```

This implementation should keep status literals type-clean. If mypy still flags
the context manager protocol, adjust `RawOpener` rather than weakening types in
the domain models.

- [ ] **Step 3: Review checkpoint 2 diff**

Run:

```powershell
git -C C:\Users\user\Desktop\XIC_Extractor\.worktrees\instrument-qc-trend diff -- xic_extractor\instrument_qc tests\test_instrument_qc_pipeline.py tests\test_instrument_qc_writers.py
```

Review checklist:

- Writers do not import RAW reader or peak detection.
- Pipeline imports RAW reader only at the orchestration boundary.
- Tests use fake RAW/XIC, not Thermo RAW files.
- Missing injection order remains diagnostic-only.

- [ ] **Step 4: Commit checkpoint 2**

Run:

```powershell
git -C C:\Users\user\Desktop\XIC_Extractor\.worktrees\instrument-qc-trend add xic_extractor/instrument_qc tests/test_instrument_qc_pipeline.py tests/test_instrument_qc_writers.py
git -C C:\Users\user\Desktop\XIC_Extractor\.worktrees\instrument-qc-trend commit -m "feat: add sdolek instrument qc pipeline"
```

---

## Checkpoint 3: CLI Entry

**Files:**

- Create: `scripts/run_instrument_qc.py`
- Test: `tests/test_run_instrument_qc.py`

### Task 3.1: Write CLI Tests

- [ ] **Step 1: Create CLI test file**

Create `tests/test_run_instrument_qc.py`:

```python
from pathlib import Path

from scripts import run_instrument_qc
from xic_extractor.instrument_qc.models import InstrumentQCRunOutput


def _fake_output(output_dir: Path) -> InstrumentQCRunOutput:
    trend_tsv = output_dir / "instrument_qc_sdolek_trend.tsv"
    trend_json = output_dir / "instrument_qc_sdolek_trend.json"
    diagnostics_tsv = output_dir / "instrument_qc_sdolek_diagnostics.tsv"
    output_dir.mkdir(parents=True, exist_ok=True)
    trend_tsv.write_text("sample_name\n", encoding="utf-8")
    trend_json.write_text("{}\n", encoding="utf-8")
    diagnostics_tsv.write_text("sample_name\traw_path\tissue\tdetail\n", encoding="utf-8")
    return InstrumentQCRunOutput(
        trend_rows=(),
        diagnostics=(),
        trend_tsv=trend_tsv,
        trend_json=trend_json,
        diagnostics_tsv=diagnostics_tsv,
    )


def test_run_instrument_qc_cli_calls_sdolek_pipeline(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    calls: dict[str, object] = {}

    def fake_run_sdolek_pipeline(**kwargs):
        calls.update(kwargs)
        return _fake_output(kwargs["output_dir"])

    monkeypatch.setattr(run_instrument_qc, "run_sdolek_pipeline", fake_run_sdolek_pipeline)

    rc = run_instrument_qc.main(
        [
            "--raw-dir",
            str(tmp_path / "raw"),
            "--output-dir",
            str(tmp_path / "out"),
            "--mode",
            "sdolek",
        ]
    )

    assert rc == 0
    assert calls["raw_dir"] == tmp_path / "raw"
    assert calls["output_dir"] == tmp_path / "out"
    assert "instrument_qc_sdolek_trend.tsv" in capsys.readouterr().out


def test_run_instrument_qc_cli_rejects_unknown_mode(capsys) -> None:
    rc = run_instrument_qc.main(
        [
            "--raw-dir",
            "raw",
            "--output-dir",
            "out",
            "--mode",
            "blank",
        ]
    )

    assert rc == 2
    assert "unsupported mode" in capsys.readouterr().err
```

- [ ] **Step 2: Run CLI tests and verify they fail**

Run:

```powershell
uv --cache-dir .uv-cache run pytest tests\test_run_instrument_qc.py -q
```

Expected:

```text
ImportError: cannot import name 'run_instrument_qc' from 'scripts'
```

### Task 3.2: Implement CLI

- [ ] **Step 1: Create script**

Create `scripts/run_instrument_qc.py`:

```python
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from xic_extractor.instrument_qc.pipeline import run_sdolek_pipeline
from xic_extractor.raw_reader import RawReaderError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run opt-in instrument-only QC trend extraction.",
    )
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--mode", default="sdolek")
    parser.add_argument("--injection-order-source", type=Path)
    parser.add_argument("--dll-dir", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.mode != "sdolek":
        print(
            f"unsupported mode: {args.mode}. Phase 1 supports only 'sdolek'.",
            file=sys.stderr,
        )
        return 2
    try:
        output = run_sdolek_pipeline(
            raw_dir=args.raw_dir,
            output_dir=args.output_dir,
            injection_order_source=args.injection_order_source,
            dll_dir=args.dll_dir,
        )
    except RawReaderError as exc:
        print(f"RAW reader error: {exc}", file=sys.stderr)
        return 2
    except FileNotFoundError as exc:
        print(f"File not found: {exc}", file=sys.stderr)
        return 2

    print(f"Wrote {output.trend_tsv}")
    print(f"Wrote {output.trend_json}")
    print(f"Wrote {output.diagnostics_tsv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run CLI tests**

Run:

```powershell
uv --cache-dir .uv-cache run pytest tests\test_run_instrument_qc.py -q
```

Expected:

```text
2 passed
```

- [ ] **Step 3: Confirm main extraction entry remains untouched**

Run:

```powershell
git -C C:\Users\user\Desktop\XIC_Extractor\.worktrees\instrument-qc-trend diff --name-only
```

Expected dirty files include `scripts/run_instrument_qc.py` and tests, not `scripts/run_extraction.py`.

- [ ] **Step 4: Commit checkpoint 3**

Run:

```powershell
git -C C:\Users\user\Desktop\XIC_Extractor\.worktrees\instrument-qc-trend add scripts/run_instrument_qc.py tests/test_run_instrument_qc.py
git -C C:\Users\user\Desktop\XIC_Extractor\.worktrees\instrument-qc-trend commit -m "feat: add instrument qc cli"
```

---

## Checkpoint 4: Regression And Real-Data Smoke

**Files:**

- No required production file changes.
- Optional docs note only if real-data smoke reveals a contract clarification:
  - `docs/superpowers/specs/2026-05-20-instrument-only-qc-trend-spec.md`

### Task 4.1: Run Focused And Regression Tests

- [ ] **Step 1: Run all instrument QC tests**

Run:

```powershell
uv --cache-dir .uv-cache run pytest tests\test_instrument_qc_classification.py tests\test_instrument_qc_pipeline.py tests\test_instrument_qc_writers.py tests\test_run_instrument_qc.py -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 2: Run regression guards**

Run:

```powershell
uv --cache-dir .uv-cache run pytest tests\test_injection_rolling.py tests\test_excel_pipeline.py tests\test_output_schema_contract.py -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 3: Run lint and typecheck**

Run:

```powershell
uv --cache-dir .uv-cache run ruff check .
uv --cache-dir .uv-cache run mypy xic_extractor
```

Expected:

```text
All checks passed!
Success: no issues found
```

### Task 4.2: Run Real SDOLEK Smoke

- [ ] **Step 1: Run opt-in SDOLEK CLI**

Run:

```powershell
uv --cache-dir .uv-cache run python scripts\run_instrument_qc.py `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --output-dir output\instrument_qc\20260105_sdo_lek `
  --mode sdolek
```

Expected artifacts:

```text
output\instrument_qc\20260105_sdo_lek\instrument_qc_sdolek_trend.tsv
output\instrument_qc\20260105_sdo_lek\instrument_qc_sdolek_trend.json
output\instrument_qc\20260105_sdo_lek\instrument_qc_sdolek_diagnostics.tsv
```

- [ ] **Step 2: Inspect real output shape**

Run:

```powershell
Import-Csv output\instrument_qc\20260105_sdo_lek\instrument_qc_sdolek_trend.tsv -Delimiter "`t" |
  Group-Object compound,status |
  Select-Object Name,Count
```

Expected:

- Both `SDO` and `LEK` appear.
- Biological sample stems such as `TumorBC2257_DNA` do not appear.
- `identity_evidence` is `MS1_ONLY` for all rows.

- [ ] **Step 3: Confirm existing production outputs were not touched**

Run:

```powershell
git -C C:\Users\user\Desktop\XIC_Extractor\.worktrees\instrument-qc-trend status --short
```

Expected:

- No tracked production outputs modified.
- `output\instrument_qc\...` may exist locally but must not be committed.

### Task 4.3: Final Review And Commit Any Needed Docs Clarification

- [ ] **Step 1: If real smoke requires a spec clarification, patch docs only**

Allowed example clarification:

```markdown
Real-data smoke may report `INJECTION_ORDER_MISSING` when no method-doc-derived
order file is supplied. That is expected in Phase 1 and does not fail the run.
```

Do not commit real-data output.

- [ ] **Step 2: Commit docs-only clarification if any**

Run only if docs changed:

```powershell
git -C C:\Users\user\Desktop\XIC_Extractor\.worktrees\instrument-qc-trend add docs/superpowers/specs/2026-05-20-instrument-only-qc-trend-spec.md
git -C C:\Users\user\Desktop\XIC_Extractor\.worktrees\instrument-qc-trend commit -m "docs: record instrument qc smoke findings"
```

Final acceptance:

- Existing targeted and untargeted behavior unchanged.
- `sample_groups.py` unchanged.
- `scripts/run_extraction.py` unchanged.
- Instrument QC can run independently.
- Missing injection order is visible in diagnostics.
- No workbook/lifecycle/user-home side effects.

---

## Execution Notes

Implementation should stop and report instead of expanding scope if any of these occur:

- SDOLEK folder is absent in the real RAW root.
- Thermo RAW reader cannot open the real files.
- Real SDO/LEK traces are present but `find_peak_and_area` returns systematic `PEAK_NOT_FOUND`.
- Adding CLI support appears to require modifying main extraction CLI.
- Tests suggest `sample_groups.py` needs instrument-only classes.

Those cases require a new reviewed decision, not silent scope expansion.

## Self-Review

Spec coverage:

- Independent classification: Checkpoint 1.
- NoSplit priors and SDO/LEK constants: Checkpoint 1.
- SDOLEK discovery and extraction: Checkpoint 2.
- TSV/JSON/diagnostics output: Checkpoint 2.
- Optional injection order: Checkpoint 2.
- Opt-in CLI: Checkpoint 3.
- Regression and real-data smoke: Checkpoint 4.
- No HCD/MixSTDs/Blank/workbook/main-pipeline changes: enforced in scope and review gates.

Placeholder scan:

- No placeholder markers or undefined future implementation step is required for
  Phase 1.

Type consistency:

- `InstrumentQCClass`, `InstrumentQCTarget`, `SDOLEKTrendRow`, `InstrumentQCDiagnostic`, and `InstrumentQCRunOutput` are defined before use.
- `run_sdolek_pipeline()` signature is used consistently by CLI tests and script.

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | Not run | Not required for this docs-to-plan conversion; scope was already user-approved. |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | Not run | Not required before implementation; no production code changed. |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | CLEAR | Fixed 4 execution risks: missing SDOLEK folder behavior, context-manager typing, per-target extraction errors, and status literal typing. |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | Not run | No UI or visual output in Phase 1. |
| DX Review | `/plan-devex-review` | Developer experience gaps | 1 | CLEAR | Fixed CLI/reporting friction: missing SDOLEK folder now fails clearly and CLI tests verify user-visible errors. |

- **UNRESOLVED:** 0.
- **VERDICT:** ENG + DX CLEARED — ready to implement checkpoint-by-checkpoint.
