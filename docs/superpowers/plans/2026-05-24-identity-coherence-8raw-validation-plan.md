# Identity Coherence 8RAW Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a diagnostic-only 8RAW validation runner that proves identity coherence serial-vs-process output parity and writes an auditable validation report.

**Architecture:** A standalone script wraps the existing `scripts/run_alignment.py` CLI twice: once with the conservative serial RAW/XIC policy and once with `validation-fast` (`raw_workers=8`, `raw_xic_batch_size=64`). It compares only frozen identity coherence diagnostic artifacts, then writes a validation TSV and Markdown report. It does not import or change Backfill, RAW retrieval, final matrix filtering, or alignment decision logic.

**Tech Stack:** Python 3.11+, `argparse`, `csv`, `dataclasses`, `pathlib`, `subprocess`, `pytest`, existing `scripts/run_alignment.py` CLI, PowerShell.

---

## Scope Boundary

In scope:

- Add `scripts/validate_identity_coherence_8raw.py`.
- Add `tests/test_validate_identity_coherence_8raw.py`.
- Validate deterministic parity for the identity coherence diagnostic bundle:
  - `untargeted_identity_coherence_requests.tsv`
  - `untargeted_identity_coherence_decisions.tsv`
  - `untargeted_identity_coherence_cell_evidence.tsv`
  - `untargeted_identity_coherence_controls.tsv`
- Check `untargeted_identity_coherence_summary.md` presence only. The frozen TSVs
  are the parity contract; Markdown summary text is a review surface and may
  contain path/timing context.
- Treat `raw_workers` and `raw_xic_batch_size` as execution policy only. They may change runtime counters and wall time; they must not change frozen TSV row order or values.
- Emit validation outputs under a caller-provided `--output-root`.
- Support an optional controls manifest pass-through. If no manifest is supplied,
  the report must say controls are `not_assessed`; this is acceptable for
  serial-vs-process parity but not enough for method interpretation.
- Even when a controls manifest is supplied, this runner may only report
  controls artifact parity unless it adds explicit positive-control sensitivity
  and decoy specificity checks. A provided manifest is not the same as method
  validation.

Out of scope:

- No changes to `xic_extractor/alignment/identity_coherence_adapter.py`.
- No changes to `xic_extractor/alignment/process_backend.py`.
- No changes to `xic_extractor/raw_reader.py`, RAW/XIC retrieval, `owner_backfill`, Backfill semantics, final matrix filtering, workbook rendering, or downstream statistical filtering.
- No new ISTD/positive-control manifest content in this slice.
- No 85RAW threshold policy.
- No claim that would-primary rows are final retained features. This runner validates the diagnostic sidecar only.

## Existing Inputs

Use the same 8RAW validation input paths already documented in `docs/validation-harness.md`:

```powershell
$discoveryBatchIndex = "output\discovery\timing_phase0_8raw\discovery_batch_index.csv"
$rawDir = "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation"
$dllDir = "C:\Xcalibur\system\programs"
```

`validation-fast` expands to `raw_workers=8` and `raw_xic_batch_size=64` in `scripts/run_alignment.py`.

## Required Working Directory

Run every command in this plan from the pinned worktree:

```powershell
Set-Location "C:\Users\user\Desktop\XIC_Extractor\.worktrees\untargeted-backfill-logic-reset"
git status --short
uv run python scripts\run_alignment.py --help
```

If `git status --short` reports dubious ownership, stop and configure this exact
worktree as a safe directory before continuing:

```powershell
git config --global --add safe.directory "C:/Users/user/Desktop/XIC_Extractor/.worktrees/untargeted-backfill-logic-reset"
```

## File Structure

Create:

```text
scripts/validate_identity_coherence_8raw.py
tests/test_validate_identity_coherence_8raw.py
```

Modify only if needed for import packaging:

```text
tests/__init__.py
```

Do not modify:

```text
scripts/run_alignment.py
xic_extractor/alignment/identity_coherence_adapter.py
xic_extractor/alignment/process_backend.py
xic_extractor/alignment/pipeline.py
xic_extractor/raw_reader.py
```

## Validation Output Contract

The script writes:

```text
output\identity_coherence_8raw_validation\serial\...
output\identity_coherence_8raw_validation\process\...
output\identity_coherence_8raw_validation\identity_coherence_8raw_validation_summary.tsv
output\identity_coherence_8raw_validation\identity_coherence_8raw_validation_report.md
```

The summary TSV columns are fixed inside this script:

```python
VALIDATION_SUMMARY_COLUMNS = (
    "check_name",
    "status",
    "serial_value",
    "process_value",
    "details",
)
```

Status values:

- `pass`
- `fail`
- `not_assessed`

The script exits:

- `0` when all parity checks pass.
- `1` when any parity check fails.
- `2` for invalid CLI inputs, failed child commands, or missing expected artifacts.

## Task 0: Preflight And Base Commit

This task does not edit files.

### Step 1: Capture base commit for the scope guard

```powershell
$baseCommit = git rev-parse HEAD
$baseCommit
```

Keep this value for Task 5. Do not replace it with `HEAD~N`.

### Step 2: Check real-data prerequisites

```powershell
Test-Path output\discovery\timing_phase0_8raw\discovery_batch_index.csv
Test-Path "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation"
Test-Path "C:\Xcalibur\system\programs"
```

If the discovery batch index check returns `False`, continue implementing and
unit-testing the validation script, but skip the real 8RAW command in Task 4.
Do not synthesize a fake real-data path and do not treat a skipped real-data run
as parity evidence.

## Task 1: Add TSV Comparator And Report Models

**Files:**

- Create: `scripts/validate_identity_coherence_8raw.py`
- Create: `tests/test_validate_identity_coherence_8raw.py`

### Step 1: RED tests for deterministic TSV comparison

Add these tests to `tests/test_validate_identity_coherence_8raw.py`:

```python
from __future__ import annotations

from pathlib import Path

from scripts.validate_identity_coherence_8raw import (
    DiagnosticBundle,
    compare_identity_coherence_bundles,
    read_tsv_rows,
)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _bundle(root: Path, *, suffix: str = "") -> DiagnosticBundle:
    return DiagnosticBundle(
        requests_tsv=root / f"untargeted_identity_coherence_requests{suffix}.tsv",
        decisions_tsv=root / f"untargeted_identity_coherence_decisions{suffix}.tsv",
        cell_evidence_tsv=(
            root / f"untargeted_identity_coherence_cell_evidence{suffix}.tsv"
        ),
        controls_tsv=root / f"untargeted_identity_coherence_controls{suffix}.tsv",
        summary_md=root / f"untargeted_identity_coherence_summary{suffix}.md",
    )


def _write_bundle(root: Path, *, decision_rows: str) -> DiagnosticBundle:
    bundle = _bundle(root)
    _write(bundle.requests_tsv, "request_id\tseed_candidate_id\nICR-1\tC1\n")
    _write(bundle.decisions_tsv, "decision_id\tdecision\n" + decision_rows)
    _write(bundle.cell_evidence_tsv, "decision_id\tsample_id\nICD-1\tS2\n")
    _write(bundle.controls_tsv, "control_id\tcontrol_pass\n")
    _write(bundle.summary_md, "# Summary\n")
    return bundle


def test_read_tsv_rows_preserves_header_and_order(tmp_path: Path) -> None:
    path = _write(tmp_path / "rows.tsv", "a\tb\n1\t2\n3\t4\n")

    rows = read_tsv_rows(path)

    assert rows.header == ("a", "b")
    assert rows.rows == (("1", "2"), ("3", "4"))


def test_compare_bundles_passes_identical_tsvs(tmp_path: Path) -> None:
    serial = _write_bundle(
        tmp_path / "serial",
        decision_rows="ICD-1\twould_primary_provisional_identity_family_support\n",
    )
    process = _write_bundle(
        tmp_path / "process",
        decision_rows="ICD-1\twould_primary_provisional_identity_family_support\n",
    )

    result = compare_identity_coherence_bundles(serial, process)

    assert result.failed_count == 0
    assert {row.check_name: row.status for row in result.rows}[
        "decisions_tsv_exact"
    ] == "pass"
    assert {row.check_name: row.status for row in result.rows}[
        "controls_manifest_assessment"
    ] == "not_assessed"
    assert {row.check_name: row.details for row in result.rows}[
        "controls_tsv_parity_only"
    ].startswith("controls file parity only")


def test_compare_bundles_fails_when_row_order_changes(tmp_path: Path) -> None:
    serial = _write_bundle(
        tmp_path / "serial",
        decision_rows="ICD-1\treview_only_insufficient_identity_support\n"
        "ICD-2\twould_primary_provisional_identity_family_support\n",
    )
    process = _write_bundle(
        tmp_path / "process",
        decision_rows="ICD-2\twould_primary_provisional_identity_family_support\n"
        "ICD-1\treview_only_insufficient_identity_support\n",
    )

    result = compare_identity_coherence_bundles(serial, process)

    assert result.failed_count == 1
    assert {row.check_name: row.status for row in result.rows}[
        "decisions_tsv_exact"
    ] == "fail"
```

### Step 2: GREEN implementation

In `scripts/validate_identity_coherence_8raw.py`, add:

```python
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


IDENTITY_COHERENCE_FILES = {
    "requests_tsv": "untargeted_identity_coherence_requests.tsv",
    "decisions_tsv": "untargeted_identity_coherence_decisions.tsv",
    "cell_evidence_tsv": "untargeted_identity_coherence_cell_evidence.tsv",
    "controls_tsv": "untargeted_identity_coherence_controls.tsv",
    "summary_md": "untargeted_identity_coherence_summary.md",
}

VALIDATION_SUMMARY_COLUMNS = (
    "check_name",
    "status",
    "serial_value",
    "process_value",
    "details",
)


@dataclass(frozen=True)
class DiagnosticBundle:
    requests_tsv: Path
    decisions_tsv: Path
    cell_evidence_tsv: Path
    controls_tsv: Path
    summary_md: Path


@dataclass(frozen=True)
class TsvRows:
    header: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class ValidationRow:
    check_name: str
    status: str
    serial_value: str
    process_value: str
    details: str


@dataclass(frozen=True)
class RunMetadata:
    mode: str
    command_line: str
    output_dir: Path
    returncode: int


@dataclass(frozen=True)
class ValidationResult:
    rows: tuple[ValidationRow, ...]
    run_metadata: tuple[RunMetadata, ...] = ()

    @property
    def failed_count(self) -> int:
        return sum(1 for row in self.rows if row.status == "fail")


def bundle_from_output_dir(output_dir: Path) -> DiagnosticBundle:
    identity_dir = output_dir / "identity_coherence"
    return DiagnosticBundle(
        requests_tsv=identity_dir / IDENTITY_COHERENCE_FILES["requests_tsv"],
        decisions_tsv=identity_dir / IDENTITY_COHERENCE_FILES["decisions_tsv"],
        cell_evidence_tsv=identity_dir / IDENTITY_COHERENCE_FILES["cell_evidence_tsv"],
        controls_tsv=identity_dir / IDENTITY_COHERENCE_FILES["controls_tsv"],
        summary_md=identity_dir / IDENTITY_COHERENCE_FILES["summary_md"],
    )


def read_tsv_rows(path: Path) -> TsvRows:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle, dialect="excel-tab")
        rows = tuple(tuple(row) for row in reader)
    if not rows:
        raise ValueError(f"{path}: empty TSV")
    return TsvRows(header=rows[0], rows=rows[1:])


def compare_identity_coherence_bundles(
    serial: DiagnosticBundle,
    process: DiagnosticBundle,
    *,
    controls_manifest: Path | None = None,
) -> ValidationResult:
    rows = [
        _compare_tsv("requests_tsv_exact", serial.requests_tsv, process.requests_tsv),
        _compare_tsv("decisions_tsv_exact", serial.decisions_tsv, process.decisions_tsv),
        _compare_tsv(
            "cell_evidence_tsv_exact",
            serial.cell_evidence_tsv,
            process.cell_evidence_tsv,
        ),
        _compare_tsv(
            "controls_tsv_parity_only",
            serial.controls_tsv,
            process.controls_tsv,
            success_details=(
                "controls file parity only; no biological controls assessed here"
            ),
        ),
        _controls_manifest_row(controls_manifest),
        _compare_summary_presence(serial.summary_md, process.summary_md),
    ]
    return ValidationResult(rows=tuple(rows))


def _compare_tsv(
    check_name: str,
    serial_path: Path,
    process_path: Path,
    *,
    success_details: str = "exact header and row-order match",
) -> ValidationRow:
    serial_rows = read_tsv_rows(serial_path)
    process_rows = read_tsv_rows(process_path)
    if serial_rows == process_rows:
        return ValidationRow(
            check_name=check_name,
            status="pass",
            serial_value=str(len(serial_rows.rows)),
            process_value=str(len(process_rows.rows)),
            details=success_details,
        )
    return ValidationRow(
        check_name=check_name,
        status="fail",
        serial_value=_tsv_digest(serial_rows),
        process_value=_tsv_digest(process_rows),
        details="TSV differs; row order is part of the frozen contract",
    )


def _controls_manifest_row(controls_manifest: Path | None) -> ValidationRow:
    if controls_manifest is None:
        return ValidationRow(
            check_name="controls_manifest_assessment",
            status="not_assessed",
            serial_value="not_provided",
            process_value="not_provided",
            details=(
                "serial/process parity only; no positive-control or decoy "
                "method validation"
            ),
        )
    return ValidationRow(
        check_name="controls_manifest_assessment",
        status="not_assessed",
        serial_value="provided",
        process_value="provided",
        details=(
            "manifest passed through; this runner reports artifact parity, not "
            "positive-control sensitivity or decoy specificity"
        ),
    )


def _compare_summary_presence(serial_path: Path, process_path: Path) -> ValidationRow:
    serial_exists = serial_path.is_file()
    process_exists = process_path.is_file()
    return ValidationRow(
        check_name="summary_md_presence",
        status="pass" if serial_exists and process_exists else "fail",
        serial_value=str(serial_exists).lower(),
        process_value=str(process_exists).lower(),
        details="summary markdown is reviewed manually; TSVs are exact-compared",
    )


def _tsv_digest(rows: TsvRows) -> str:
    return f"header={len(rows.header)} rows={len(rows.rows)}"
```

### Step 3: Verify

```powershell
uv run pytest tests\test_validate_identity_coherence_8raw.py -q
```

Expected: new tests pass.

### Step 4: Commit

```powershell
git add scripts\validate_identity_coherence_8raw.py tests\test_validate_identity_coherence_8raw.py
git commit -m "feat: compare identity coherence validation bundles"
```

## Task 2: Add Command Builder And Fake Runner Tests

**Files:**

- Modify: `scripts/validate_identity_coherence_8raw.py`
- Modify: `tests/test_validate_identity_coherence_8raw.py`

### Step 1: RED tests for serial/process commands

Update the import block in `tests/test_validate_identity_coherence_8raw.py` to
include `build_alignment_command`, then append only the test functions below.
Do not add imports in the middle of the file.

```python
def test_build_serial_command_omits_validation_fast_profile(tmp_path: Path) -> None:
    command = build_alignment_command(
        mode="serial",
        discovery_batch_index=tmp_path / "batch.csv",
        raw_dir=tmp_path / "raw",
        dll_dir=tmp_path / "dll",
        output_dir=tmp_path / "out" / "serial",
        controls_manifest=None,
    )

    joined = " ".join(str(part) for part in command)
    assert "--emit-identity-coherence-diagnostic" in joined
    assert "--identity-coherence-output-dir" in joined
    assert "--performance-profile" not in command
    assert "validation-fast" not in command
    assert command[command.index("--raw-workers") + 1] == "1"
    assert command[command.index("--raw-xic-batch-size") + 1] == "1"


def test_build_process_command_uses_validation_fast_profile(tmp_path: Path) -> None:
    command = build_alignment_command(
        mode="process",
        discovery_batch_index=tmp_path / "batch.csv",
        raw_dir=tmp_path / "raw",
        dll_dir=tmp_path / "dll",
        output_dir=tmp_path / "out" / "process",
        controls_manifest=tmp_path / "controls.tsv",
    )

    assert "--performance-profile" in command
    assert "validation-fast" in command
    assert "--identity-coherence-controls-manifest" in command
    assert str(tmp_path / "controls.tsv") in command
```

### Step 2: GREEN command builder

Update the production import block in
`scripts/validate_identity_coherence_8raw.py`:

```python
import csv
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
```

Add:

```python
def build_alignment_command(
    *,
    mode: str,
    discovery_batch_index: Path,
    raw_dir: Path,
    dll_dir: Path,
    output_dir: Path,
    controls_manifest: Path | None,
) -> list[str]:
    if mode not in {"serial", "process"}:
        raise ValueError("mode must be 'serial' or 'process'")
    identity_output_dir = output_dir / "identity_coherence"
    command = [
        sys.executable,
        str(Path(__file__).resolve().parent / "run_alignment.py"),
        "--discovery-batch-index",
        str(discovery_batch_index),
        "--raw-dir",
        str(raw_dir),
        "--dll-dir",
        str(dll_dir),
        "--output-dir",
        str(output_dir),
        "--output-level",
        "machine",
        "--emit-alignment-cells",
        "--emit-identity-coherence-diagnostic",
        "--identity-coherence-output-dir",
        str(identity_output_dir),
        "--timing-output",
        str(output_dir / "alignment_timing.json"),
    ]
    if mode == "serial":
        command.extend(["--raw-workers", "1", "--raw-xic-batch-size", "1"])
    if mode == "process":
        command.extend(
            [
                "--performance-profile",
                "validation-fast",
            ]
        )
    if controls_manifest is not None:
        command.extend(
            [
                "--identity-coherence-controls-manifest",
                str(controls_manifest),
            ]
        )
    return command
```

### Step 3: Add fake runner orchestration tests

Update the top import block to include `subprocess`, `pytest`, and
`run_validation`, then append:

```python
def test_run_validation_invokes_serial_then_process_and_writes_report(
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []

    def fake_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        output_dir = Path(command[command.index("--output-dir") + 1])
        _write_bundle(
            output_dir / "identity_coherence",
            decision_rows="ICD-1\twould_primary_provisional_identity_family_support\n",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    result = run_validation(
        discovery_batch_index=tmp_path / "batch.csv",
        raw_dir=tmp_path / "raw",
        dll_dir=tmp_path / "dll",
        output_root=tmp_path / "validation",
        controls_manifest=None,
        runner=fake_runner,
    )

    assert result.failed_count == 0
    assert len(calls) == 2
    assert "validation-fast" not in calls[0]
    assert "validation-fast" in calls[1]
    assert result.failed_count == 0


def test_run_validation_raises_with_child_failure_details(tmp_path: Path) -> None:
    def fake_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            command,
            3,
            stdout="serial out",
            stderr="serial err",
        )

    with pytest.raises(RuntimeError, match="serial alignment failed"):
        run_validation(
            discovery_batch_index=tmp_path / "batch.csv",
            raw_dir=tmp_path / "raw",
            dll_dir=tmp_path / "dll",
            output_root=tmp_path / "validation",
            controls_manifest=None,
            runner=fake_runner,
        )


def test_run_validation_clears_previous_mode_outputs(tmp_path: Path) -> None:
    stale = (
        tmp_path
        / "validation"
        / "serial"
        / "identity_coherence"
        / "untargeted_identity_coherence_decisions.tsv"
    )
    stale.parent.mkdir(parents=True)
    stale.write_text("decision_id\tdecision\nSTALE\told\n", encoding="utf-8")

    def fake_runner(command: list[str]) -> subprocess.CompletedProcess[str]:
        output_dir = Path(command[command.index("--output-dir") + 1])
        _write_bundle(
            output_dir / "identity_coherence",
            decision_rows="ICD-1\twould_primary_provisional_identity_family_support\n",
        )
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    result = run_validation(
        discovery_batch_index=tmp_path / "batch.csv",
        raw_dir=tmp_path / "raw",
        dll_dir=tmp_path / "dll",
        output_root=tmp_path / "validation",
        controls_manifest=None,
        runner=fake_runner,
    )

    assert result.failed_count == 0
    assert "STALE" not in stale.read_text(encoding="utf-8")
```

### Step 4: GREEN runner

Add:

```python
class CommandRunner(Protocol):
    def __call__(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        ...


def run_validation(
    *,
    discovery_batch_index: Path,
    raw_dir: Path,
    dll_dir: Path,
    output_root: Path,
    controls_manifest: Path | None,
    runner: CommandRunner | None = None,
) -> ValidationResult:
    output_root.mkdir(parents=True, exist_ok=True)
    runner = runner or _run_command
    serial_output = output_root / "serial"
    process_output = output_root / "process"
    _reset_run_dir(serial_output)
    _reset_run_dir(process_output)
    metadata: list[RunMetadata] = []
    for mode, output_dir in (
        ("serial", serial_output),
        ("process", process_output),
    ):
        command = build_alignment_command(
            mode=mode,
            discovery_batch_index=discovery_batch_index,
            raw_dir=raw_dir,
            dll_dir=dll_dir,
            output_dir=output_dir,
            controls_manifest=controls_manifest,
        )
        completed = runner(command)
        metadata.append(
            RunMetadata(
                mode=mode,
                command_line=subprocess.list2cmdline(command),
                output_dir=output_dir,
                returncode=completed.returncode,
            )
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"{mode} alignment failed with exit code {completed.returncode}: "
                f"command={subprocess.list2cmdline(command)} "
                f"stdout={_tail(completed.stdout)} "
                f"stderr={_tail(completed.stderr)}"
            )
    result = compare_identity_coherence_bundles(
        bundle_from_output_dir(serial_output),
        bundle_from_output_dir(process_output),
        controls_manifest=controls_manifest,
    )
    return ValidationResult(rows=result.rows, run_metadata=tuple(metadata))


def _run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=False,
        text=True,
        capture_output=True,
    )


def _reset_run_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _tail(text: str | None, *, limit: int = 1000) -> str:
    if not text:
        return ""
    return text[-limit:]
```

`run_validation()` intentionally does not write report files in Task 2. Report
writing starts in Task 3 so the implementation remains green task-by-task.

### Step 5: Verify and commit

```powershell
uv run pytest tests\test_validate_identity_coherence_8raw.py -q
uv run ruff check scripts\validate_identity_coherence_8raw.py tests\test_validate_identity_coherence_8raw.py
git add scripts\validate_identity_coherence_8raw.py tests\test_validate_identity_coherence_8raw.py
git commit -m "feat: run identity coherence 8raw parity validation"
```

## Task 3: Add Summary TSV And Markdown Report

**Files:**

- Modify: `scripts/validate_identity_coherence_8raw.py`
- Modify: `tests/test_validate_identity_coherence_8raw.py`

### Step 1: RED report tests

Update the grouped
`from scripts.validate_identity_coherence_8raw import (...)` import block in
`tests/test_validate_identity_coherence_8raw.py`; keep the existing
`subprocess`, `Path`, and `pytest` imports:

```python
from scripts.validate_identity_coherence_8raw import (
    DiagnosticBundle,
    ValidationResult,
    ValidationRow,
    build_alignment_command,
    compare_identity_coherence_bundles,
    read_tsv_rows,
    run_validation,
    write_validation_outputs,
)
```

Append:

```python
def test_write_validation_outputs_labels_controls_not_assessed(
    tmp_path: Path,
) -> None:
    result = ValidationResult(
        rows=(
            ValidationRow(
                check_name="requests_tsv_exact",
                status="pass",
                serial_value="1",
                process_value="1",
                details="ok",
            ),
        )
    )

    write_validation_outputs(
        output_root=tmp_path,
        result=result,
        controls_manifest=None,
    )

    report = (
        tmp_path / "identity_coherence_8raw_validation_report.md"
    ).read_text(encoding="utf-8")
    assert "Controls: not_assessed" in report
    assert "diagnostic-only" in report
    assert "does not validate final matrix filtering" in report
    assert "not final retained feature inclusion" in report
    summary = (
        tmp_path / "identity_coherence_8raw_validation_summary.tsv"
    ).read_text(encoding="utf-8")
    assert "controls_manifest_assessment\tnot_assessed" in summary
```

### Step 2: GREEN report writer

Add:

```python
def write_validation_outputs(
    *,
    output_root: Path,
    result: ValidationResult,
    controls_manifest: Path | None,
    run_metadata: tuple[RunMetadata, ...] = (),
) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    metadata = run_metadata if run_metadata else result.run_metadata
    _write_summary_tsv(
        output_root / "identity_coherence_8raw_validation_summary.tsv",
        result,
    )
    _write_report_md(
        output_root / "identity_coherence_8raw_validation_report.md",
        result=result,
        controls_manifest=controls_manifest,
        run_metadata=metadata,
    )


def _write_summary_tsv(path: Path, result: ValidationResult) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=VALIDATION_SUMMARY_COLUMNS,
            dialect="excel-tab",
        )
        writer.writeheader()
        for row in result.rows:
            writer.writerow(
                {
                    "check_name": row.check_name,
                    "status": row.status,
                    "serial_value": row.serial_value,
                    "process_value": row.process_value,
                    "details": row.details,
                }
            )


def _write_report_md(
    path: Path,
    *,
    result: ValidationResult,
    controls_manifest: Path | None,
    run_metadata: tuple[RunMetadata, ...] = (),
) -> None:
    parity_result = "PASS" if result.failed_count == 0 else "FAIL"
    controls_status = (
        "provided_not_assessed"
        if controls_manifest is not None
        else "not_assessed"
    )
    lines = [
        "# Identity Coherence 8RAW Validation",
        "",
        f"Parity result: {parity_result}",
        "",
        "This report is diagnostic-only. It validates identity coherence sidecar "
        "parity and does not validate final matrix filtering. It is not method "
        "validation and does not establish positive-control sensitivity or decoy "
        "specificity unless those checks are explicitly reported.",
        "",
        "`would_primary_provisional_identity_family_support` is a diagnostic "
        "sidecar label, not final retained feature inclusion.",
        "",
        f"Controls: {controls_status}",
        "",
        "## Run Metadata",
        "",
        "| Mode | Return Code | Output Dir | Command |",
        "| --- | ---: | --- | --- |",
    ]
    if not run_metadata:
        lines.append("| `not_assessed` | 0 |  | metadata not supplied |")
    for item in run_metadata:
        lines.append(
            "| "
            f"`{item.mode}` | {item.returncode} | `{item.output_dir}` | "
            f"`{item.command_line}` |"
        )
    lines.extend([
        "",
        "## Parity Checks",
        "",
        "| Check | Status | Serial | Process | Details |",
        "| --- | --- | ---: | ---: | --- |",
    ])
    for row in result.rows:
        lines.append(
            "| "
            f"`{row.check_name}` | `{row.status}` | {row.serial_value} | "
            f"{row.process_value} | {row.details} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
```

### Step 3: Verify and commit

```powershell
uv run pytest tests\test_validate_identity_coherence_8raw.py -q
uv run ruff check scripts\validate_identity_coherence_8raw.py tests\test_validate_identity_coherence_8raw.py
git add scripts\validate_identity_coherence_8raw.py tests\test_validate_identity_coherence_8raw.py
git commit -m "feat: report identity coherence validation parity"
```

## Task 4: Add CLI, Preflight, And Real 8RAW Command

**Files:**

- Modify: `scripts/validate_identity_coherence_8raw.py`
- Modify: `tests/test_validate_identity_coherence_8raw.py`

### Step 1: RED CLI tests

Add this import at the top of `tests/test_validate_identity_coherence_8raw.py`,
beside the other module imports:

```python
from scripts import validate_identity_coherence_8raw as validation_script
```

Then append:

```python
def test_main_rejects_missing_controls_manifest(tmp_path: Path, capsys) -> None:
    batch = tmp_path / "batch.csv"
    raw_dir = tmp_path / "raw"
    dll_dir = tmp_path / "dll"
    batch.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir.mkdir()
    dll_dir.mkdir()

    code = validation_script.main(
        [
            "--discovery-batch-index",
            str(batch),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--output-root",
            str(tmp_path / "out"),
            "--controls-manifest",
            str(tmp_path / "missing.tsv"),
        ]
    )

    assert code == 2
    assert "controls manifest does not exist" in capsys.readouterr().err


def test_main_returns_one_when_parity_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch = tmp_path / "batch.csv"
    raw_dir = tmp_path / "raw"
    dll_dir = tmp_path / "dll"
    batch.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir.mkdir()
    dll_dir.mkdir()

    def fake_run_validation(**kwargs) -> ValidationResult:
        return ValidationResult(
            rows=(
                ValidationRow(
                    check_name="decisions_tsv_exact",
                    status="fail",
                    serial_value="a",
                    process_value="b",
                    details="different",
                ),
            )
        )

    monkeypatch.setattr(validation_script, "run_validation", fake_run_validation)

    code = validation_script.main(
        [
            "--discovery-batch-index",
            str(batch),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--output-root",
            str(tmp_path / "out"),
        ]
    )

    assert code == 1


def test_main_returns_two_when_validation_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch = tmp_path / "batch.csv"
    raw_dir = tmp_path / "raw"
    dll_dir = tmp_path / "dll"
    batch.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir.mkdir()
    dll_dir.mkdir()

    def fake_run_validation(**kwargs) -> ValidationResult:
        raise RuntimeError("serial alignment failed")

    monkeypatch.setattr(validation_script, "run_validation", fake_run_validation)

    code = validation_script.main(
        [
            "--discovery-batch-index",
            str(batch),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--output-root",
            str(tmp_path / "out"),
        ]
    )

    assert code == 2
```

### Step 2: GREEN CLI

Update the production import block to add `argparse`, then add:

```python
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run serial-vs-process 8RAW validation for the identity coherence "
            "diagnostic sidecar."
        )
    )
    parser.add_argument("--discovery-batch-index", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--dll-dir", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--controls-manifest", type=Path)
    args = parser.parse_args(argv)

    if not args.discovery_batch_index.is_file():
        print(
            f"{args.discovery_batch_index}: discovery batch index does not exist",
            file=sys.stderr,
        )
        return 2
    if not args.raw_dir.is_dir():
        print(f"{args.raw_dir}: raw directory does not exist", file=sys.stderr)
        return 2
    if not args.dll_dir.is_dir():
        print(f"{args.dll_dir}: dll directory does not exist", file=sys.stderr)
        return 2
    if args.controls_manifest is not None and not args.controls_manifest.is_file():
        print(
            f"{args.controls_manifest}: controls manifest does not exist",
            file=sys.stderr,
        )
        return 2

    try:
        result = run_validation(
            discovery_batch_index=args.discovery_batch_index,
            raw_dir=args.raw_dir,
            dll_dir=args.dll_dir,
            output_root=args.output_root,
            controls_manifest=args.controls_manifest,
        )
        write_validation_outputs(
            output_root=args.output_root,
            result=result,
            controls_manifest=args.controls_manifest,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if result.failed_count:
        print(
            f"FAIL identity_coherence_sidecar_parity failed={result.failed_count}",
            file=sys.stderr,
        )
        return 1
    print(
        "PASS identity_coherence_sidecar_parity "
        f"summary={args.output_root / 'identity_coherence_8raw_validation_report.md'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

### Step 3: Unit verification

```powershell
uv run pytest tests\test_validate_identity_coherence_8raw.py -q
uv run ruff check scripts\validate_identity_coherence_8raw.py tests\test_validate_identity_coherence_8raw.py
```

Expected: tests and lint pass.

### Step 4: Real 8RAW parity validation

Run the real diagnostic parity command:

```powershell
uv run python scripts\validate_identity_coherence_8raw.py `
  --discovery-batch-index output\discovery\timing_phase0_8raw\discovery_batch_index.csv `
  --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" `
  --dll-dir "C:\Xcalibur\system\programs" `
  --output-root output\identity_coherence_8raw_validation
```

Expected:

```text
PASS identity_coherence_sidecar_parity summary=output\identity_coherence_8raw_validation\identity_coherence_8raw_validation_report.md
```

Interpretation:

- If this command passes without `--controls-manifest`, it proves serial/process parity for the identity coherence diagnostic mechanics.
- It does not prove positive-control sensitivity or decoy specificity.
- Do not inspect or modify final matrix outputs as part of this task.

### Step 5: Optional controls run

Only when a reviewed controls manifest already exists, run:

```powershell
uv run python scripts\validate_identity_coherence_8raw.py `
  --discovery-batch-index output\discovery\timing_phase0_8raw\discovery_batch_index.csv `
  --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" `
  --dll-dir "C:\Xcalibur\system\programs" `
  --output-root output\identity_coherence_8raw_validation_controls `
  --controls-manifest docs\superpowers\fixtures\identity_coherence_controls_manifest_8raw.tsv
```

If `docs\superpowers\fixtures\identity_coherence_controls_manifest_8raw.tsv` does not exist, skip this optional command. Do not create a manifest in this implementation slice.

### Step 6: Commit

```powershell
git add scripts\validate_identity_coherence_8raw.py tests\test_validate_identity_coherence_8raw.py
git commit -m "feat: validate identity coherence 8raw parity"
```

## Task 5: Scope Guard

Before final handoff, run:

```powershell
git diff --name-only $baseCommit..HEAD
```

The diff may include only:

```text
scripts/validate_identity_coherence_8raw.py
tests/test_validate_identity_coherence_8raw.py
```

Run boundary searches:

```powershell
rg -n "owner_backfill|primary_matrix|final_matrix|workbook|raw_reader|open_raw|extract_xic" scripts\validate_identity_coherence_8raw.py tests\test_validate_identity_coherence_8raw.py
rg -n "from xic_extractor\.alignment|import xic_extractor\.alignment|owner_matrix|pipeline\.run_alignment" scripts\validate_identity_coherence_8raw.py tests\test_validate_identity_coherence_8raw.py
rg -n "run_identity_coherence_diagnostic|identity_coherence_adapter|process_backend" scripts\validate_identity_coherence_8raw.py
```

Expected:

- The first command may match only explanatory strings in the Markdown report or test expectations. It must not show imports from RAW, Backfill, workbook, or matrix modules.
- The second command should show no matches. This validation runner must not import `xic_extractor.alignment` internals.
- The third command should show no matches. This validation runner must call the public `scripts/run_alignment.py` CLI, not the internal diagnostic adapter.

Run broader checks:

```powershell
uv run pytest tests\test_validate_identity_coherence_8raw.py tests\test_run_alignment.py tests\test_alignment_identity_coherence_adapter.py -q
uv run ruff check scripts\validate_identity_coherence_8raw.py tests\test_validate_identity_coherence_8raw.py
```

## Self-Review Checklist

- [ ] The validation script is diagnostic-only and does not import RAW/Backfill internals.
- [ ] Serial mode omits `validation-fast`.
- [ ] Process mode uses `validation-fast`.
- [ ] Frozen TSV comparison is exact and row-order-sensitive.
- [ ] Summary Markdown is presence-checked but not exact-compared.
- [ ] Missing controls manifest is a CLI error only when explicitly provided.
- [ ] No-controls run reports controls as `not_assessed`.
- [ ] The real 8RAW command uses `raw_workers=8` and `raw_xic_batch_size=64` through `validation-fast`.
- [ ] Output interpretation does not claim final matrix filtering validity.
- [ ] No 85RAW policy is introduced.
