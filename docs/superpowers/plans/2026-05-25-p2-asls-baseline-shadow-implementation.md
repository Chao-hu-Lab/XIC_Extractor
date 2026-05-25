# P2 AsLS Baseline Shadow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in AsLS shadow area baseline to `alignment_cell_integration_audit.tsv` without changing production `area_baseline_corrected`.

**Architecture:** Keep production integration on the existing linear-edge baseline. Add AsLS as an audit-only shadow result carried by `CellIntegrationAuditSummary`, emitted by the alignment integration-audit TSV only when `baseline_audit_method=asls` is enabled. Store the opt-in on `ExtractionConfig` so serial and process alignment paths receive the same pickleable payload without adding a parallel plumbing tree.

**Tech Stack:** Python, NumPy, existing `xic_extractor.baseline.asls_baseline`, pytest, existing alignment sidecar writers and diagnostic CLIs.

---

## Current State

- Worktree: `C:\Users\user\Desktop\XIC_Extractor\.worktrees\peak-pipeline-modernization`
- Branch: `codex/peak-pipeline-modernization`
- P1 status: `production_candidate` for P2 entry, not 85RAW / not `production_ready`
- Cleanup C-specs: on hold; do not implement cleanup tasks in this plan
- P2 scope: `shadow_ready` target only; P2b owns any production AsLS promotion

## Plan Review Log

- Review status: completed and patched before implementation.
- CodeGraph CLI status: index up to date for this worktree.
- Review findings fixed:
  - Removed note-template tokens that could be saved without real command output.
  - Kept TSV AsLS columns conditional so default `alignment_cell_integration_audit.tsv`
    schema stays unchanged.
  - Kept the opt-in on `ExtractionConfig` so process workers receive a
    pickleable payload and no module-level cache is introduced.
- Scope check: P2 only; no P2b production promotion and no Cleanup C-spec work.

## Now / Not In Scope

Now:

- Add `integrate_asls_baseline(...)` and `integrate_with_baseline(...)` beside the current linear-edge helper.
- Add opt-in AsLS shadow fields to `CellIntegrationAuditSummary`.
- Emit `area_baseline_corrected_asls` and `baseline_score_asls` only when the AsLS audit flag is enabled.
- Add CLI/env/config entry points that enable only the audit shadow.
- Add a P2 diagnostic gate that summarizes AsLS-vs-linear audit evidence.
- Record P2 implementation and validation notes.

Not in scope:

- Do not change production `area_baseline_corrected`.
- Do not change safe-merge, hypothesis spine, targeted extraction, matrix identity, owner grouping, or resolver behavior.
- Do not remove `linear_edge`, resolver modes, or public contract fields.
- Do not implement Cleanup C1a/C1b/C5 or any C-spec.
- Do not promote AsLS to production; P2b requires a separate GO note.

## File Map

- Modify `xic_extractor/peak_detection/baseline.py`: add AsLS integration and the thin selector.
- Modify `xic_extractor/peak_detection/integration_audit.py`: carry optional AsLS shadow values.
- Modify `xic_extractor/peak_detection/region_audit.py`: pass `config.baseline_audit_method` to the audit summary builder.
- Modify `xic_extractor/alignment/tsv_writer.py`: conditionally append AsLS shadow columns.
- Modify `xic_extractor/alignment/pipeline_outputs.py`: pass the audit method into the integration-audit writer.
- Modify `xic_extractor/alignment/pipeline.py`: pass `peak_config.baseline_audit_method` into output writers and metadata.
- Modify `xic_extractor/configuration/models.py`: add `ExtractionConfig.baseline_audit_method`.
- Modify `xic_extractor/configuration/settings.py`: parse and validate `baseline_audit_method`.
- Modify `xic_extractor/settings_schema.py` and `config/settings.example.csv`: add the default empty opt-in setting.
- Modify `scripts/run_alignment.py`: add `--emit-baseline-audit-asls` and `BASELINE_AUDIT_METHOD=asls` support.
- Create `tools/diagnostics/p2_asls_shadow_gate.py`: summarize 8RAW AsLS shadow metrics.
- Modify tests:
  - `tests/test_baseline_integration.py`
  - `tests/test_alignment_tsv_writer.py`
  - `tests/test_alignment_pipeline_outputs.py`
  - `tests/test_run_alignment.py`
  - `tests/test_config.py`
  - `tests/test_alignment_process_backend.py`
  - Create `tests/test_p2_asls_shadow_gate.py`
- Create notes:
  - `docs/superpowers/notes/2026-05-25-p2-asls-baseline-shadow-implementation-note.md`
  - `docs/superpowers/notes/2026-05-25-p2-asls-baseline-shadow-validation-note.md`

---

## Task 1: Baseline Helpers

**Files:**

- Modify: `tests/test_baseline_integration.py`
- Modify: `xic_extractor/peak_detection/baseline.py`

- [x] **Step 1: Add failing tests for AsLS integration and selector**

Add these imports in `tests/test_baseline_integration.py`:

```python
from xic_extractor.peak_detection.baseline import (
    bounded_trace_interval,
    integrate_asls_baseline,
    integrate_linear_edge_baseline,
    integrate_with_baseline,
)
```

Add tests:

```python
def test_asls_baseline_integrates_shadow_area_without_exceeding_raw() -> None:
    rt = np.asarray([0.0, 0.1, 0.2, 0.3, 0.4, 0.5])
    intensity = np.asarray([8.0, 12.0, 70.0, 65.0, 20.0, 12.0])

    result = integrate_asls_baseline(intensity, rt, 1, 5)

    assert result.baseline_type == "asls"
    assert result.area_uncertainty is None
    assert result.area_baseline_corrected > 0.0
    raw_area = 60.0 * float(np.trapezoid(intensity[1:5], rt[1:5]))
    assert result.area_baseline_corrected <= raw_area
    assert result.baseline_score is not None
    assert 0.0 <= result.baseline_score <= 1.0


def test_integrate_with_baseline_dispatches_supported_methods() -> None:
    rt = np.asarray([0.0, 0.1, 0.2, 0.3])
    intensity = np.asarray([10.0, 30.0, 25.0, 12.0])

    linear = integrate_with_baseline(
        intensity,
        rt,
        0,
        4,
        baseline_method="linear_edge",
    )
    asls = integrate_with_baseline(
        intensity,
        rt,
        0,
        4,
        baseline_method="asls",
    )

    assert linear.baseline_type == "linear_edge"
    assert asls.baseline_type == "asls"


def test_integrate_with_baseline_rejects_unknown_method() -> None:
    rt = np.asarray([0.0, 0.1, 0.2])
    intensity = np.asarray([10.0, 20.0, 12.0])

    with pytest.raises(ValueError, match="baseline_method"):
        integrate_with_baseline(
            intensity,
            rt,
            0,
            3,
            baseline_method="airpls",
        )
```

- [x] **Step 2: Run the focused failing tests**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_baseline_integration.py -q
```

Expected: fails because `integrate_asls_baseline` and `integrate_with_baseline` do not exist yet.

- [x] **Step 3: Implement the helpers**

In `xic_extractor/peak_detection/baseline.py`, add:

```python
from typing import Literal

from xic_extractor.baseline import asls_baseline

BaselineMethod = Literal["linear_edge", "asls"]
```

Add:

```python
def integrate_asls_baseline(
    intensity_values: np.ndarray,
    rt_values: np.ndarray,
    left: int,
    right: int,
    *,
    lam: float = 1e5,
    p: float = 0.01,
    n_iter: int = 10,
    baseline_values: np.ndarray | None = None,
) -> BaselineIntegration:
    rt = np.asarray(rt_values, dtype=float)
    intensity = np.asarray(intensity_values, dtype=float)
    _validate_trace_arrays(rt, intensity)
    left_index, right_index = bounded_trace_interval(left, right, len(rt))
    full_baseline = (
        np.asarray(baseline_values, dtype=float)
        if baseline_values is not None
        else asls_baseline(intensity, lam=lam, p=p, n_iter=n_iter)
    )
    if full_baseline.shape != intensity.shape:
        raise ValueError("baseline_values must match intensity_values shape")
    segment = intensity[left_index:right_index]
    segment_rt = rt[left_index:right_index]
    baseline_segment = full_baseline[left_index:right_index]
    corrected = np.maximum(segment - baseline_segment, 0.0)
    corrected_area = _area_counts_seconds(corrected, segment_rt)
    raw_area = integrate_area_counts_seconds(intensity, rt, left_index, right_index)
    return BaselineIntegration(
        area_baseline_corrected=corrected_area,
        area_uncertainty=None,
        baseline_type="asls",
        baseline_score=_safe_ratio(corrected_area, raw_area),
    )


def integrate_with_baseline(
    intensity_values: np.ndarray,
    rt_values: np.ndarray,
    left: int,
    right: int,
    *,
    baseline_method: BaselineMethod = "linear_edge",
) -> BaselineIntegration:
    if baseline_method == "linear_edge":
        return integrate_linear_edge_baseline(intensity_values, rt_values, left, right)
    if baseline_method == "asls":
        return integrate_asls_baseline(intensity_values, rt_values, left, right)
    raise ValueError("baseline_method must be 'linear_edge' or 'asls'")
```

- [x] **Step 4: Verify Task 1**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_baseline_integration.py -q
```

Expected: `tests/test_baseline_integration.py` passes.

---

## Task 2: Integration Audit Shadow Fields

**Files:**

- Modify: `tests/test_baseline_integration.py`
- Modify: `xic_extractor/peak_detection/integration_audit.py`
- Modify: `xic_extractor/peak_detection/region_audit.py`

- [x] **Step 1: Add failing tests for shadow summary behavior**

Add to `tests/test_baseline_integration.py`:

```python
def test_cell_integration_audit_can_emit_asls_shadow_values() -> None:
    rt = np.asarray([0.0, 0.1, 0.2, 0.3, 0.4, 0.5])
    intensity = np.asarray([8.0, 12.0, 70.0, 65.0, 20.0, 12.0])

    summary = build_cell_integration_audit_summary(
        rt,
        intensity,
        peak_start_rt=0.1,
        peak_end_rt=0.4,
        raw_area=60.0 * float(np.trapezoid(intensity[1:5], rt[1:5])),
        baseline_audit_method="asls",
    )

    assert summary.baseline_type == "linear_edge"
    assert summary.area_baseline_corrected is not None
    assert summary.area_baseline_corrected_asls is not None
    assert summary.baseline_score_asls is not None
    assert 0.0 <= summary.baseline_score_asls <= 1.0


def test_cell_integration_audit_default_has_no_asls_shadow_values() -> None:
    rt = np.asarray([0.0, 0.1, 0.2, 0.3])
    intensity = np.asarray([10.0, 30.0, 25.0, 12.0])

    summary = build_cell_integration_audit_summary(
        rt,
        intensity,
        peak_start_rt=0.0,
        peak_end_rt=0.3,
        raw_area=100.0,
    )

    assert summary.area_baseline_corrected_asls is None
    assert summary.baseline_score_asls is None
```

- [x] **Step 2: Run the focused failing tests**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_baseline_integration.py -q
```

Expected: fails because the summary has no AsLS shadow fields yet.

- [x] **Step 3: Add shadow fields and opt-in computation**

In `CellIntegrationAuditSummary`, add:

```python
    area_baseline_corrected_asls: float | None = None
    baseline_score_asls: float | None = None
```

Change `build_cell_integration_audit_summary(...)` signature:

```python
def build_cell_integration_audit_summary(
    rt_values: np.ndarray,
    intensity_values: np.ndarray,
    *,
    peak_start_rt: float | None,
    peak_end_rt: float | None,
    raw_area: float | None,
    baseline_audit_method: str = "",
) -> CellIntegrationAuditSummary:
```

Inside the existing `try` block, keep linear-edge as production and add:

```python
        asls_shadow = (
            integrate_with_baseline(
                intensity,
                rt,
                left_index,
                right_index,
                baseline_method="asls",
            )
            if baseline_audit_method == "asls"
            else None
        )
```

Return:

```python
        area_baseline_corrected_asls=(
            None if asls_shadow is None else asls_shadow.area_baseline_corrected
        ),
        baseline_score_asls=(
            None if asls_shadow is None else asls_shadow.baseline_score
        ),
```

If `baseline_audit_method` is not `""` or `"asls"`, raise:

```python
raise ValueError("baseline_audit_method must be empty or 'asls'")
```

In `build_peak_region_audit_summary`, pass:

```python
baseline_audit_method=getattr(config, "baseline_audit_method", ""),
```

- [x] **Step 4: Verify Task 2**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_baseline_integration.py tests\test_peak_region_audit.py tests\test_alignment_owner_matrix.py -q
```

Expected: all pass; existing linear-edge assertions remain unchanged.

---

## Task 3: Conditional TSV Contract

**Files:**

- Modify: `tests/test_alignment_tsv_writer.py`
- Modify: `xic_extractor/alignment/tsv_writer.py`
- Modify: `xic_extractor/alignment/pipeline_outputs.py`
- Modify: `xic_extractor/alignment/pipeline.py`

- [x] **Step 1: Add failing writer tests**

In `tests/test_alignment_tsv_writer.py`, update `_cell(...)` so the integration fixture includes AsLS values:

```python
                area_baseline_corrected_asls=8.0,
                baseline_score_asls=0.8,
```

Add:

```python
def test_write_alignment_cell_integration_audit_tsv_default_schema_is_unchanged(
    tmp_path: Path,
) -> None:
    from xic_extractor.alignment.tsv_writer import (
        ALIGNMENT_CELL_INTEGRATION_AUDIT_COLUMNS,
        write_alignment_cell_integration_audit_tsv,
    )

    matrix = AlignmentMatrix(
        clusters=(_cluster(),),
        cells=(_cell("sample-a", "detected", area=10.0, integration=True),),
        sample_order=("sample-a",),
    )

    rows = _read_tsv(
        write_alignment_cell_integration_audit_tsv(
            tmp_path / "alignment_cell_integration_audit.tsv",
            matrix,
        )
    )

    assert list(rows[0]) == list(ALIGNMENT_CELL_INTEGRATION_AUDIT_COLUMNS)
    assert "area_baseline_corrected_asls" not in rows[0]
    assert "baseline_score_asls" not in rows[0]


def test_write_alignment_cell_integration_audit_tsv_emits_asls_shadow_columns(
    tmp_path: Path,
) -> None:
    from xic_extractor.alignment.tsv_writer import (
        write_alignment_cell_integration_audit_tsv,
    )

    matrix = AlignmentMatrix(
        clusters=(_cluster(),),
        cells=(_cell("sample-a", "detected", area=10.0, integration=True),),
        sample_order=("sample-a",),
    )

    rows = _read_tsv(
        write_alignment_cell_integration_audit_tsv(
            tmp_path / "alignment_cell_integration_audit.tsv",
            matrix,
            baseline_audit_method="asls",
        )
    )

    assert rows[0]["area_baseline_corrected"] == "7.5"
    assert rows[0]["baseline_score"] == "0.75"
    assert rows[0]["area_baseline_corrected_asls"] == "8"
    assert rows[0]["baseline_score_asls"] == "0.8"
```

- [x] **Step 2: Run failing writer tests**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_alignment_tsv_writer.py -q
```

Expected: fails because the writer does not accept `baseline_audit_method`.

- [x] **Step 3: Implement conditional columns**

In `xic_extractor/alignment/tsv_writer.py`, add:

```python
ASLS_ALIGNMENT_CELL_INTEGRATION_AUDIT_COLUMNS = (
    "area_baseline_corrected_asls",
    "baseline_score_asls",
)
```

Change `write_alignment_cell_integration_audit_tsv(...)`:

```python
def write_alignment_cell_integration_audit_tsv(
    path: Path,
    matrix: AlignmentMatrix,
    *,
    baseline_audit_method: str = "",
) -> Path:
```

Before writing, set:

```python
    if baseline_audit_method not in {"", "asls"}:
        raise ValueError("baseline_audit_method must be empty or 'asls'")
    columns = (
        (*ALIGNMENT_CELL_INTEGRATION_AUDIT_COLUMNS, *ASLS_ALIGNMENT_CELL_INTEGRATION_AUDIT_COLUMNS)
        if baseline_audit_method == "asls"
        else ALIGNMENT_CELL_INTEGRATION_AUDIT_COLUMNS
    )
```

When building each row, add the AsLS fields only for the opt-in case:

```python
        if baseline_audit_method == "asls":
            row["area_baseline_corrected_asls"] = format_value(
                audit.area_baseline_corrected_asls
            )
            row["baseline_score_asls"] = format_value(audit.baseline_score_asls)
```

Return:

```python
return _write_tsv(path, columns, rows)
```

In `pipeline_outputs.write_outputs_atomic(...)`, add a keyword:

```python
    baseline_audit_method: str = "",
```

Pass it to the writer:

```python
lambda path: write_alignment_cell_integration_audit_tsv(
    path,
    matrix,
    baseline_audit_method=baseline_audit_method,
)
```

In `pipeline.run_alignment(...)`, pass:

```python
baseline_audit_method=peak_config.baseline_audit_method,
```

to `_write_outputs_atomic(...)`.

- [x] **Step 4: Verify Task 3**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_alignment_tsv_writer.py tests\test_alignment_pipeline_outputs.py -q
```

Expected: all pass; default TSV schema remains unchanged.

---

## Task 4: Public Config, CLI, And Environment Opt-In

**Files:**

- Modify: `tests/test_config.py`
- Modify: `tests/test_run_alignment.py`
- Modify: `tests/test_alignment_pipeline_outputs.py`
- Modify: `tests/test_alignment_process_backend.py`
- Modify: `xic_extractor/configuration/models.py`
- Modify: `xic_extractor/configuration/settings.py`
- Modify: `xic_extractor/settings_schema.py`
- Modify: `config/settings.example.csv`
- Modify: `scripts/run_alignment.py`

- [x] **Step 1: Add failing config and CLI tests**

Add to `tests/test_config.py`:

```python
def test_load_config_accepts_asls_baseline_audit_method(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    _write_settings(config_dir, {"baseline_audit_method": "asls"})
    _write_targets(config_dir)

    config, _ = load_config(config_dir)

    assert config.baseline_audit_method == "asls"


def test_load_config_rejects_unknown_baseline_audit_method(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    _write_settings(config_dir, {"baseline_audit_method": "airpls"})
    _write_targets(config_dir)

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_dir)

    _assert_error(exc_info, "settings.csv", "baseline_audit_method", "airpls")
```

Add to the canonical/default tests:

```python
assert CANONICAL_SETTINGS_DEFAULTS["baseline_audit_method"] == ""
```

Add to `test_settings_example_includes_local_minimum_preset` or a new settings-example test:

```python
assert rows["baseline_audit_method"] == ""
```

In `tests/test_run_alignment.py`, extend `test_run_alignment_cli_passes_paths_settings_and_debug_flags`:

```python
            "--emit-baseline-audit-asls",
```

and assert:

```python
    assert peak_config.baseline_audit_method == "asls"
```

Add:

```python
def test_run_alignment_env_enables_asls_baseline_audit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    output_dir = tmp_path / "alignment"
    captured = {}

    def fake_run_alignment(**kwargs):
        captured.update(kwargs)
        return AlignmentRunOutputs()

    monkeypatch.setattr(run_alignment, "run_alignment", fake_run_alignment)
    monkeypatch.setenv("BASELINE_AUDIT_METHOD", "asls")

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert code == 0
    assert captured["peak_config"].baseline_audit_method == "asls"
```

Add process smoke coverage in `tests/test_alignment_process_backend.py` by extending the existing job-capture tests to assert `job.peak_config.baseline_audit_method == "asls"` when the supplied config has that field.

- [x] **Step 2: Run failing config/CLI tests**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_config.py tests\test_run_alignment.py tests\test_alignment_process_backend.py -q
```

Expected: fails because `baseline_audit_method` is not yet defined.

- [x] **Step 3: Implement config and CLI opt-in**

In `ExtractionConfig`, add:

```python
    baseline_audit_method: str = ""
```

In `settings_schema.py`, add:

```python
    "baseline_audit_method": "",
```

and description:

```python
    "baseline_audit_method": (
        "Audit-only baseline comparison method; leave empty for default TSV schema, "
        "or set to asls to emit AsLS shadow area columns."
    ),
```

In `configuration/settings.py`, add `baseline_audit_method` to `_ParsedSettings`, parse it as a raw string, validate:

```python
    if parsed.baseline_audit_method not in {"", "asls"}:
        raise _config_error(
            settings_path,
            None,
            "baseline_audit_method",
            settings["baseline_audit_method"],
            "must be empty or asls",
        )
```

and pass it into `ExtractionConfig(...)`.

In `config/settings.example.csv`, add:

```csv
baseline_audit_method,,Audit-only baseline comparison method; leave empty for default TSV schema or set to asls to emit AsLS shadow area columns
```

In `scripts/run_alignment.py`, import `os`, add parser flag:

```python
parser.add_argument(
    "--emit-baseline-audit-asls",
    action="store_true",
    help="Emit AsLS shadow columns in alignment_cell_integration_audit.tsv.",
)
```

Add:

```python
def _baseline_audit_method(args: argparse.Namespace) -> str:
    env_method = os.environ.get("BASELINE_AUDIT_METHOD", "").strip().lower()
    if args.emit_baseline_audit_asls:
        return "asls"
    if env_method in {"", "asls"}:
        return env_method
    raise ValueError("BASELINE_AUDIT_METHOD must be empty or asls")
```

Pass `_baseline_audit_method(args)` into `_peak_config(...)`, and add the same value to `ExtractionConfig(...)`.

- [x] **Step 4: Verify Task 4**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_config.py tests\test_run_alignment.py tests\test_alignment_pipeline_outputs.py tests\test_alignment_process_backend.py -q
```

Expected: all pass; default run still has empty `baseline_audit_method`.

---

## Task 5: P2 AsLS Shadow Diagnostic Gate

**Files:**

- Create: `tools/diagnostics/p2_asls_shadow_gate.py`
- Create: `tests/test_p2_asls_shadow_gate.py`

- [x] **Step 1: Add failing diagnostic tests**

Create `tests/test_p2_asls_shadow_gate.py` with:

```python
from __future__ import annotations

import csv
from pathlib import Path

from tools.diagnostics.p2_asls_shadow_gate import run_p2_asls_shadow_gate


def _write_tsv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_p2_asls_shadow_gate_passes_when_asls_rsd_is_close(tmp_path: Path) -> None:
    audit = tmp_path / "alignment_cell_integration_audit.tsv"
    summary = tmp_path / "targeted_istd_benchmark_summary.tsv"
    _write_tsv(
        audit,
        [
            {
                "feature_family_id": "FAM001",
                "sample_stem": "S1",
                "status": "detected",
                "area": "100",
                "area_baseline_corrected": "80",
                "area_baseline_corrected_asls": "78",
                "baseline_score_asls": "0.78",
            },
            {
                "feature_family_id": "FAM001",
                "sample_stem": "S2",
                "status": "detected",
                "area": "110",
                "area_baseline_corrected": "88",
                "area_baseline_corrected_asls": "86",
                "baseline_score_asls": "0.7818",
            },
        ],
    )
    _write_tsv(
        summary,
        [
            {
                "target_label": "ISTD-A",
                "role": "ISTD",
                "active_tag": "TRUE",
                "selected_feature_id": "FAM001",
            }
        ],
    )

    outputs, result = run_p2_asls_shadow_gate(
        alignment_integration_audit_tsv=audit,
        targeted_istd_benchmark_summary_tsv=summary,
        output_dir=tmp_path / "gate",
    )

    assert result.overall_status == "PASS"
    assert result.failed_count == 0
    assert outputs.summary_tsv.exists()
    assert outputs.rows_tsv.exists()


def test_p2_asls_shadow_gate_fails_when_asls_exceeds_raw_area(tmp_path: Path) -> None:
    audit = tmp_path / "alignment_cell_integration_audit.tsv"
    summary = tmp_path / "targeted_istd_benchmark_summary.tsv"
    _write_tsv(
        audit,
        [
            {
                "feature_family_id": "FAM001",
                "sample_stem": "S1",
                "status": "detected",
                "area": "100",
                "area_baseline_corrected": "80",
                "area_baseline_corrected_asls": "120",
                "baseline_score_asls": "1.2",
            },
            {
                "feature_family_id": "FAM001",
                "sample_stem": "S2",
                "status": "detected",
                "area": "100",
                "area_baseline_corrected": "80",
                "area_baseline_corrected_asls": "118",
                "baseline_score_asls": "1.18",
            },
        ],
    )
    _write_tsv(
        summary,
        [
            {
                "target_label": "ISTD-A",
                "role": "ISTD",
                "active_tag": "TRUE",
                "selected_feature_id": "FAM001",
            }
        ],
    )

    _outputs, result = run_p2_asls_shadow_gate(
        alignment_integration_audit_tsv=audit,
        targeted_istd_benchmark_summary_tsv=summary,
        output_dir=tmp_path / "gate",
    )

    assert result.overall_status == "FAIL"
    assert result.failed_count == 1
    assert "asls_area_exceeds_raw_area" in result.rows[0].failure_reasons
```

- [x] **Step 2: Run failing diagnostic tests**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_p2_asls_shadow_gate.py -q
```

Expected: fails because the diagnostic tool does not exist.

- [x] **Step 3: Implement the diagnostic**

Create `tools/diagnostics/p2_asls_shadow_gate.py` with:

- `run_p2_asls_shadow_gate(...)`
- row output: `target_label`, `selected_feature_id`, `sample_count`, `linear_area_rsd_pct`, `asls_area_rsd_pct`, `area_rsd_delta_pct`, `median_abs_relative_diff_pct`, `diff_gt_5pct_count`, `asls_reduced_area_count`, `asls_exceeds_raw_area_count`, `status`, `failure_reasons`
- summary output: `overall_status`, `failed_count`, `target_count`, `max_area_rsd_delta_pct`, `max_median_abs_relative_diff_pct`, `max_asls_exceeds_raw_area_count`, `max_rsd_regression_pct`
- JSON and Markdown reports with the same fields
- default gate: fail if AsLS RSD is more than +0.3 percentage points above linear-edge RSD, or any AsLS area exceeds raw `area`
- CLI exit codes: `0` pass, `1` gate fail, `2` invalid input

- [x] **Step 4: Verify Task 5**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_p2_asls_shadow_gate.py -q
```

Expected: diagnostic tests pass.

---

## Task 6: Unit Verification And Implementation Note

**Files:**

- Create: `docs/superpowers/notes/2026-05-25-p2-asls-baseline-shadow-implementation-note.md`

- [x] **Step 1: Run focused unit tests**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_baseline_integration.py tests\test_alignment_tsv_writer.py tests\test_alignment_pipeline_outputs.py tests\test_alignment_process_backend.py tests\test_run_alignment.py tests\test_config.py tests\test_p2_asls_shadow_gate.py -q
```

Expected: all selected tests pass.

- [x] **Step 2: Run compile smoke**

Run:

```powershell
.\.venv\Scripts\python.exe -m py_compile xic_extractor\peak_detection\baseline.py xic_extractor\peak_detection\integration_audit.py xic_extractor\peak_detection\region_audit.py xic_extractor\alignment\tsv_writer.py xic_extractor\alignment\pipeline_outputs.py xic_extractor\alignment\pipeline.py xic_extractor\configuration\models.py xic_extractor\configuration\settings.py xic_extractor\settings_schema.py scripts\run_alignment.py tools\diagnostics\p2_asls_shadow_gate.py
```

Expected: exit code `0`.

- [x] **Step 3: Write implementation note**

Create `docs/superpowers/notes/2026-05-25-p2-asls-baseline-shadow-implementation-note.md`:

```markdown
# P2 AsLS Baseline Shadow Implementation Note

**Date:** 2026-05-25
**Branch:** codex/peak-pipeline-modernization
**Worktree:** .worktrees/peak-pipeline-modernization
**Gate status:** diagnostic_only

## Decision

- P2 implementation status: implemented for unit/contract testing.
- Production `area_baseline_corrected` remains linear-edge.
- AsLS is emitted only as audit shadow columns when `baseline_audit_method=asls` or `--emit-baseline-audit-asls` is set.
- P2 is not a production promotion. P2b remains required before Cleanup can assume AsLS production.

## Changed Files

- `xic_extractor/peak_detection/baseline.py`
- `xic_extractor/peak_detection/integration_audit.py`
- `xic_extractor/peak_detection/region_audit.py`
- `xic_extractor/alignment/tsv_writer.py`
- `xic_extractor/alignment/pipeline_outputs.py`
- `xic_extractor/alignment/pipeline.py`
- `xic_extractor/configuration/models.py`
- `xic_extractor/configuration/settings.py`
- `xic_extractor/settings_schema.py`
- `config/settings.example.csv`
- `scripts/run_alignment.py`
- `tools/diagnostics/p2_asls_shadow_gate.py`
- `tests/test_baseline_integration.py`
- `tests/test_alignment_tsv_writer.py`
- `tests/test_alignment_pipeline_outputs.py`
- `tests/test_alignment_process_backend.py`
- `tests/test_run_alignment.py`
- `tests/test_config.py`
- `tests/test_p2_asls_shadow_gate.py`

## Verification

- Focused pytest: record the exact Task 6 Step 1 command and observed result.
- Compile smoke: record the exact Task 6 Step 2 command and observed result.

## Remaining Real-Data Risk

- 8RAW AsLS shadow alignment and P2 diagnostic gate are not run in this implementation note.
- Real-data status remains `diagnostic_only` until the validation note records the 8RAW shadow gate.
```

Do not save the implementation note until the two verification bullets contain
the actual commands and observed results from the current worktree.

---

## Task 7: 8RAW Shadow Validation And Validation Note

**Files:**

- Create: `docs/superpowers/notes/2026-05-25-p2-asls-baseline-shadow-validation-note.md`
- Write outputs under: `output/phase1_p2_asls_shadow_validation/`

- [x] **Step 1: Run 8RAW alignment with AsLS shadow enabled**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m scripts.run_alignment `
  --discovery-batch-index output\phase1_p1_resolver_default_validation\discovery\dR\discovery_batch_index.csv `
  --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" `
  --dll-dir "C:\Xcalibur\system\programs" `
  --output-dir output\phase1_p2_asls_shadow_validation\alignment\asls_shadow `
  --output-level validation `
  --resolver-mode region_first_safe_merge `
  --emit-alignment-cells `
  --emit-alignment-integration-audit `
  --emit-baseline-audit-asls `
  --raw-workers 1 `
  --raw-xic-batch-size 1
```

Expected:

- exit code `0`
- `alignment_cell_integration_audit.tsv` exists
- TSV header includes `area_baseline_corrected_asls` and `baseline_score_asls`
- `alignment_matrix.tsv` production values remain available and are not rewritten to AsLS

- [x] **Step 2: Run targeted ISTD benchmark on the same alignment output**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m tools.diagnostics.targeted_istd_benchmark `
  --targeted-workbook output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge\xic_results_process_w4.xlsx `
  --alignment-dir output\phase1_p2_asls_shadow_validation\alignment\asls_shadow `
  --output-dir output\phase1_p2_asls_shadow_validation\diagnostics\targeted_istd_benchmark
```

Expected:

- exit code `0`
- no new strict ISTD active failures relative to the P1 hotfix benchmark

- [x] **Step 3: Run P2 AsLS shadow diagnostic gate**

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m tools.diagnostics.p2_asls_shadow_gate `
  --alignment-integration-audit-tsv output\phase1_p2_asls_shadow_validation\alignment\asls_shadow\alignment_cell_integration_audit.tsv `
  --targeted-istd-benchmark-summary-tsv output\phase1_p2_asls_shadow_validation\diagnostics\targeted_istd_benchmark\targeted_istd_benchmark_summary.tsv `
  --output-dir output\phase1_p2_asls_shadow_validation\diagnostics\p2_asls_shadow_gate
```

Expected:

- exit code `0` for P2 shadow GO
- if exit code `1`, write a NO-GO validation note and do not start P3
- if exit code `2`, write `Gate status: inconclusive` with the exact failing input

- [ ] **Step 4: Re-run area integration uncertainty audit**

Status: stopped by Step 3 NO-GO. `p2_asls_shadow_gate_summary.tsv` reported
`overall_status=FAIL`, `failed_count=3`, `max_area_rsd_delta_pct=3.85879`.
Do not run this downstream gate unless a reviewed P2 retuning or gate-revision
plan explicitly reopens validation.

Run the current-alignment evidence spine first:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m tools.diagnostics.evidence_spine_consistency `
  --targeted-dir output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge `
  --alignment-dir output\phase1_p2_asls_shadow_validation\alignment\asls_shadow `
  --output-dir output\phase1_p2_asls_shadow_validation\diagnostics\evidence_spine_consistency
```

Then run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m tools.diagnostics.area_integration_uncertainty_audit `
  --evidence-spine-rows-tsv output\phase1_p2_asls_shadow_validation\diagnostics\evidence_spine_consistency\evidence_spine_consistency_rows.tsv `
  --targeted-peak-candidates-tsv output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge\peak_candidates.tsv `
  --targeted-boundaries-tsv output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge\peak_candidate_boundaries.tsv `
  --alignment-integration-audit-tsv output\phase1_p2_asls_shadow_validation\alignment\asls_shadow\alignment_cell_integration_audit.tsv `
  --output-dir output\phase1_p2_asls_shadow_validation\diagnostics\area_integration_uncertainty
```

Expected:

- exit code `0`
- evidence spine command exits `0`
- `unexplained_area_mismatch_count=0`

- [x] **Step 5: Write validation note**

Create `docs/superpowers/notes/2026-05-25-p2-asls-baseline-shadow-validation-note.md` with:

```markdown
# P2 AsLS Baseline Shadow Validation Note

**Date:** 2026-05-25
**Branch:** codex/peak-pipeline-modernization
**Worktree:** .worktrees/peak-pipeline-modernization
**Gate status:** shadow_ready

## Decision

- P2 AsLS shadow decision: GO for P3 planning if all gates passed.
- Production `area_baseline_corrected` remains linear-edge.
- P2b is still required for AsLS production promotion.

## Artifacts

- Alignment: `output/phase1_p2_asls_shadow_validation/alignment/asls_shadow/`
- Targeted ISTD benchmark: `output/phase1_p2_asls_shadow_validation/diagnostics/targeted_istd_benchmark/`
- P2 AsLS shadow gate: `output/phase1_p2_asls_shadow_validation/diagnostics/p2_asls_shadow_gate/`
- Area integration uncertainty: `output/phase1_p2_asls_shadow_validation/diagnostics/area_integration_uncertainty/`

## Gate Results

| Gate | Result | Evidence |
|---|---|---|
| AsLS shadow columns emitted | observed gate result | `alignment_cell_integration_audit.tsv` header |
| P2 AsLS shadow gate | observed gate result | `p2_asls_shadow_gate_summary.tsv` |
| Strict ISTD benchmark | observed gate result | `targeted_istd_benchmark_summary.tsv` |
| Area integration uncertainty | observed gate result | `area_integration_uncertainty_summary.tsv` |

## Remaining Real-Data Risk

- 85RAW not run.
- P2 is shadow-only and cannot justify Cleanup linear-edge retirement.
```

Do not save the validation note until every `observed gate result` cell is
replaced with the actual current run result and the evidence path exists.

---

## Final Verification For P2

Run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe -m pytest tests\test_baseline_integration.py tests\test_alignment_tsv_writer.py tests\test_alignment_pipeline_outputs.py tests\test_alignment_process_backend.py tests\test_run_alignment.py tests\test_config.py tests\test_p2_asls_shadow_gate.py -q

.\.venv\Scripts\python.exe -m py_compile xic_extractor\peak_detection\baseline.py xic_extractor\peak_detection\integration_audit.py xic_extractor\peak_detection\region_audit.py xic_extractor\alignment\tsv_writer.py xic_extractor\alignment\pipeline_outputs.py xic_extractor\alignment\pipeline.py xic_extractor\configuration\models.py xic_extractor\configuration\settings.py xic_extractor\settings_schema.py scripts\run_alignment.py tools\diagnostics\p2_asls_shadow_gate.py
```

Expected:

- focused pytest passes
- compile smoke exits `0`
- `git diff --check` exits `0`

## Stop Conditions

Stop and ask before implementation continues if:

- enabling AsLS would require changing production `area_baseline_corrected`
- the conditional TSV column design conflicts with an existing downstream contract
- real-data P2 validation shows AsLS shadow area violates `area_baseline_corrected_asls <= area`
- strict ISTD benchmark introduces a new active failure
- `unexplained_area_mismatch_count` becomes nonzero
- any implementation step requires Cleanup C-spec work
