# P2b AsLS Production Promotion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Promote `alignment_cell_integration_audit.tsv` production `area_baseline_corrected` from linear-edge to AsLS after the revised P2b gate reaches `GO_FOR_PRODUCTION_CANDIDATE`, while preserving a linear-edge rollback/audit field.

**Architecture:** Keep the promotion inside the integration-audit path. `alignment_matrix.tsv` remains driven by accepted `cell.area`; this plan does not change final matrix quantification because that is a separate downstream contract. `CellIntegrationAuditSummary` becomes explicit about the production baseline method and stores linear-edge sidecar values when AsLS is production.

**Tech Stack:** Python, NumPy, pytest, PowerShell, existing `xic_extractor.peak_detection.baseline` AsLS/linear-edge helpers.

---

## Scope

### Now

- Promote `CellIntegrationAuditSummary.area_baseline_corrected` to AsLS by default.
- Add explicit `baseline_integration_method` config plumbing with default `asls` and rollback value `linear_edge`.
- Emit temporary linear-edge rollback columns from `alignment_cell_integration_audit.tsv` when the production baseline is AsLS.
- Preserve legacy `--emit-baseline-audit-asls` / `BASELINE_AUDIT_METHOD=asls`
  behavior by automatically running `baseline_integration_method=linear_edge`
  unless the user explicitly passes `--baseline-integration-method`.
- Update P2b docs/notes after implementation and validation.

### Later

- Decide whether `PeakHypothesis.integration.area_baseline_corrected`, `peak_candidate_boundaries.tsv`, or targeted candidate TSVs should also migrate to AsLS.
- Decide whether final `alignment_matrix.tsv` should ever use baseline-corrected values instead of `cell.area`.
- Delete linear-edge production fallback only in Cleanup C1b/C5 after this promotion has real-data validation.

### Not In Scope

- Changing `alignment_matrix.tsv` values.
- Removing `integrate_linear_edge_baseline`.
- Changing peak boundary selection, RT correction, ownership, backfill scope, or P7 performance predicates.
- Reinterpreting old P2/P3 artifacts as production inputs.

## Current Dirty Worktree Warning

This worktree currently contains unrelated uncommitted diagnostic cleanup files. Implementation must touch only:

- `xic_extractor/peak_detection/integration_audit.py`
- `xic_extractor/peak_detection/region_audit.py`
- `xic_extractor/alignment/pipeline.py`
- `xic_extractor/alignment/pipeline_outputs.py`
- `xic_extractor/alignment/tsv_writer.py`
- `xic_extractor/configuration/models.py`
- `xic_extractor/configuration/settings.py`
- `xic_extractor/settings_schema.py`
- `config/settings.example.csv`
- `scripts/run_alignment.py`
- promoted-schema diagnostic compatibility files listed in Task 5
- focused tests listed below
- P2b docs/notes listed below

Do not rewrite, revert, or stage unrelated diagnostic cleanup files unless the user explicitly asks for a cleanup commit.

## File Responsibilities

- `xic_extractor/peak_detection/integration_audit.py`
  - Owns per-cell audit integration and production baseline selection.
  - Adds linear-edge rollback fields when AsLS is production.

- `xic_extractor/configuration/models.py`, `xic_extractor/configuration/settings.py`, `xic_extractor/settings_schema.py`, `config/settings.example.csv`
  - Own config contract for `baseline_integration_method`.
  - Default must be `asls`; accepted values are `asls` and `linear_edge`.

- `scripts/run_alignment.py`
  - Adds CLI/env override for `baseline_integration_method`.
  - Keeps `--emit-baseline-audit-asls` backward-compatible by forcing
    `linear_edge` production when no explicit production method was supplied.

- `xic_extractor/alignment/tsv_writer.py`
  - Owns `alignment_cell_integration_audit.tsv` schema.
  - Emits mode-specific schemas:
    promoted AsLS schema = base columns + linear-edge rollback columns;
    legacy P2 shadow schema = base columns + AsLS shadow columns.

- `tools/diagnostics/p2_asls_shadow_gate.py`, `tools/diagnostics/p2_baseline_truth_audit.py`, `tools/diagnostics/area_integration_uncertainty_io.py`
  - Own diagnostic compatibility across old shadow schema and promoted AsLS schema.
  - Must not let old fixture tests pass while promoted schema is misread.

- Tests
  - `tests/test_baseline_integration.py`
  - `tests/test_config.py`
  - `tests/test_run_alignment.py`
  - `tests/test_alignment_pipeline_outputs.py`
  - `tests/test_alignment_tsv_writer.py`
  - `tests/test_untargeted_final_matrix_contract.py`
  - `tests/test_p2_asls_shadow_gate.py`
  - `tests/test_p2_baseline_truth_audit.py`
  - `tests/test_area_integration_uncertainty_audit.py`
  - `tests/test_p2b_asls_promotion_gate.py` only if gate schema/doc expectations need adjustment.

- Docs
  - `docs/superpowers/specs/2026-05-24-peak-pipeline-area-baseline-asls-promotion-spec.md`
  - `docs/superpowers/notes/2026-05-26-p2b-area-mismatch-triage-note.md`
  - New closeout note after implementation:
    `docs/superpowers/notes/2026-05-26-p2b-asls-production-promotion-note.md`

## Promotion Authorization

The previous P2b note required either an owner-accepted production-switch plan
or an explicit 85RAW waiver before changing the default production baseline.
This plan treats the current owner instruction to continue after the revised
P2b `GO_FOR_PRODUCTION_CANDIDATE` as authorization to implement the 8RAW
`production_candidate` switch. It is not a waiver for `production_ready`.

The closeout note must state:

- owner acceptance source: current thread instruction after P2b gate GO;
- 85RAW status: not rerun after the promotion code change;
- gate language: `production_candidate`, not `production_ready`;
- rollback path: set `baseline_integration_method=linear_edge` or use legacy
  `--emit-baseline-audit-asls` for P2 shadow reruns.

---

### Task 1: Lock The Integration-Audit Promotion Contract

**Files:**
- Modify: `tests/test_baseline_integration.py`
- Modify: `xic_extractor/peak_detection/integration_audit.py`

- [ ] **Step 1: Write failing promotion tests**

Add tests that prove the default production audit baseline is AsLS and that linear-edge rollback fields are present:

```python
def test_cell_integration_audit_defaults_to_asls_production_with_linear_edge_rollback() -> None:
    rt = np.asarray([0.0, 0.1, 0.2, 0.3, 0.4, 0.5])
    intensity = np.asarray([8.0, 12.0, 70.0, 65.0, 20.0, 12.0])

    summary = build_cell_integration_audit_summary(
        rt,
        intensity,
        peak_start_rt=0.1,
        peak_end_rt=0.4,
        raw_area=60.0 * float(np.trapezoid(intensity[1:5], rt[1:5])),
    )

    assert summary.baseline_type == "asls"
    assert summary.area_baseline_corrected is not None
    assert summary.baseline_score is not None
    assert summary.area_baseline_corrected_linear_edge is not None
    assert summary.baseline_score_linear_edge is not None
    assert summary.area_uncertainty_formula_version == "baseline_residual_mad_v1"
    assert summary.area_uncertainty_noise_source == "asls_residual"
```

Add rollback test:

```python
def test_cell_integration_audit_can_rollback_to_linear_edge_production() -> None:
    rt = np.asarray([0.0, 0.1, 0.2, 0.3, 0.4])
    intensity = np.asarray([10.0, 25.0, 50.0, 35.0, 20.0])

    summary = build_cell_integration_audit_summary(
        rt,
        intensity,
        peak_start_rt=0.0,
        peak_end_rt=0.4,
        raw_area=1200.0,
        baseline_integration_method="linear_edge",
    )

    assert summary.baseline_type == "linear_edge"
    assert summary.area_baseline_corrected == pytest.approx(390.0)
    assert summary.area_baseline_corrected_linear_edge is None
    assert summary.baseline_score_linear_edge is None
```

Add short-trace fallback test so AsLS promotion does not silently drop audit rows:

```python
def test_cell_integration_audit_falls_back_to_linear_edge_when_asls_unavailable() -> None:
    rt = np.asarray([0.0, 0.1, 0.2])
    intensity = np.asarray([10.0, 80.0, 20.0])

    summary = build_cell_integration_audit_summary(
        rt,
        intensity,
        peak_start_rt=0.0,
        peak_end_rt=0.2,
        raw_area=60.0 * float(np.trapezoid(intensity, rt)),
        baseline_integration_method="asls",
    )

    assert summary.is_empty is False
    assert summary.baseline_type == "linear_edge_fallback"
    assert summary.area_baseline_corrected is not None
    assert summary.area_baseline_corrected_linear_edge is None
```

- [ ] **Step 2: Run failing tests**

Run:

```powershell
python -m pytest tests\test_baseline_integration.py::test_cell_integration_audit_defaults_to_asls_production_with_linear_edge_rollback tests\test_baseline_integration.py::test_cell_integration_audit_can_rollback_to_linear_edge_production tests\test_baseline_integration.py::test_cell_integration_audit_falls_back_to_linear_edge_when_asls_unavailable -q
```

Expected before implementation: first test fails because default `baseline_type` is `linear_edge` and rollback fields do not exist.

- [ ] **Step 3: Implement minimal production selector**

Update imports:

```python
from dataclasses import dataclass, replace
```

Update `CellIntegrationAuditSummary`:

```python
@dataclass(frozen=True)
class CellIntegrationAuditSummary:
    raw_area: float | None = None
    area_baseline_corrected: float | None = None
    area_uncertainty: float | None = None
    area_uncertainty_formula_version: str = ""
    baseline_residual_mad: float | None = None
    area_uncertainty_noise_source: str = ""
    baseline_type: str = ""
    baseline_score: float | None = None
    uncertainty_fraction: float | None = None
    baseline_fraction: float | None = None
    integration_scan_count: int | None = None
    area_baseline_corrected_asls: float | None = None
    baseline_score_asls: float | None = None
    area_baseline_corrected_linear_edge: float | None = None
    baseline_score_linear_edge: float | None = None
```

Update `build_cell_integration_audit_summary` signature:

```python
def build_cell_integration_audit_summary(
    rt_values: np.ndarray,
    intensity_values: np.ndarray,
    *,
    peak_start_rt: float | None,
    peak_end_rt: float | None,
    raw_area: float | None,
    baseline_integration_method: str = "asls",
    baseline_audit_method: str = "",
) -> CellIntegrationAuditSummary:
```

Add validation:

```python
if baseline_integration_method not in {"asls", "linear_edge"}:
    raise ValueError("baseline_integration_method must be 'asls' or 'linear_edge'")
if baseline_audit_method not in {"", "asls"}:
    raise ValueError("baseline_audit_method must be empty or 'asls'")
```

Inside the `try` block compute AsLS once, compute linear-edge once, then choose production:

```python
asls_baseline_values, residual_mad = compute_asls_residual_mad(intensity)
linear_edge = integrate_linear_edge_baseline(
    intensity,
    rt,
    left_index,
    right_index,
    uncertainty_baseline_values=asls_baseline_values,
    baseline_residual_mad=residual_mad,
    baseline_residual_mad_source="asls_residual",
)
asls = (
    integrate_asls_baseline(
        intensity,
        rt,
        left_index,
        right_index,
        baseline_values=asls_baseline_values,
    )
    if asls_baseline_values is not None
    else None
)
if baseline_integration_method == "asls" and asls is not None:
    baseline = asls
    linear_edge_rollback = linear_edge
elif baseline_integration_method == "asls":
    baseline = replace(linear_edge, baseline_type="linear_edge_fallback")
    linear_edge_rollback = None
else:
    baseline = linear_edge
    linear_edge_rollback = None
```

Return production and rollback fields:

```python
area_baseline_corrected_asls=(
    asls.area_baseline_corrected
    if baseline_audit_method == "asls" and asls is not None
    else None
),
baseline_score_asls=(
    asls.baseline_score
    if baseline_audit_method == "asls" and asls is not None
    else None
),
area_baseline_corrected_linear_edge=(
    None if linear_edge_rollback is None else linear_edge_rollback.area_baseline_corrected
),
baseline_score_linear_edge=(
    None if linear_edge_rollback is None else linear_edge_rollback.baseline_score
),
```

- [ ] **Step 4: Run focused baseline tests**

Run:

```powershell
python -m pytest tests\test_baseline_integration.py -q
```

Expected: all baseline integration tests pass after updating old assertions from `linear_edge` default to `asls` where they exercise the default production audit path.

---

### Task 2: Add Config Plumbing For Production Baseline Method

**Files:**
- Modify: `xic_extractor/configuration/models.py`
- Modify: `xic_extractor/configuration/settings.py`
- Modify: `xic_extractor/settings_schema.py`
- Modify: `config/settings.example.csv`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Add failing config tests**

Add tests:

```python
def test_load_config_defaults_baseline_integration_method_to_asls(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    _write_settings(config_dir, {})
    _write_targets(config_dir)

    config, _ = load_config(config_dir)

    assert config.baseline_integration_method == "asls"


def test_load_config_accepts_linear_edge_baseline_integration_method(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    _write_settings(config_dir, {"baseline_integration_method": "linear_edge"})
    _write_targets(config_dir)

    config, _ = load_config(config_dir)

    assert config.baseline_integration_method == "linear_edge"


def test_load_config_rejects_unknown_baseline_integration_method(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    _write_settings(config_dir, {"baseline_integration_method": "airpls"})
    _write_targets(config_dir)

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_dir)

    _assert_error(exc_info, "settings.csv", "baseline_integration_method", "airpls")


def test_settings_example_includes_baseline_integration_method() -> None:
    example_path = Path("config/settings.example.csv")

    with example_path.open(newline="", encoding="utf-8-sig") as handle:
        rows = {row["key"]: row["value"] for row in csv.DictReader(handle)}

    assert rows["baseline_integration_method"] == "asls"
```

- [ ] **Step 2: Run failing config tests**

Run:

```powershell
python -m pytest tests\test_config.py::test_load_config_defaults_baseline_integration_method_to_asls tests\test_config.py::test_load_config_accepts_linear_edge_baseline_integration_method tests\test_config.py::test_load_config_rejects_unknown_baseline_integration_method -q
```

Expected before implementation: attribute/key failures.

- [ ] **Step 3: Add config model/default/parser support**

In `xic_extractor/configuration/models.py`, add:

```python
baseline_integration_method: str = "asls"
```

In `xic_extractor/settings_schema.py`, add default:

```python
"baseline_integration_method": "asls",
```

Add description:

```python
"baseline_integration_method": (
    "Production baseline method for alignment integration audit "
    "(asls or linear_edge; default asls after P2b promotion)"
),
```

In `config/settings.example.csv`, add:

```csv
baseline_integration_method,asls,Production baseline method for alignment integration audit (asls or linear_edge)
```

In `xic_extractor/configuration/settings.py`, parse and validate:

```python
baseline_integration_method=(
    settings.get("baseline_integration_method", "asls").strip().lower()
),
```

Validation:

```python
if parsed.baseline_integration_method not in {"asls", "linear_edge"}:
    raise _config_error(
        settings_path,
        None,
        "baseline_integration_method",
        settings.get("baseline_integration_method", ""),
        "must be asls or linear_edge",
    )
```

- [ ] **Step 4: Run config tests**

Run:

```powershell
python -m pytest tests\test_config.py -q
```

Expected: config tests pass and canonical defaults include `baseline_integration_method=asls`.

---

### Task 3: Propagate Baseline Method Through Alignment

**Files:**
- Modify: `xic_extractor/peak_detection/region_audit.py`
- Modify: `xic_extractor/alignment/pipeline_outputs.py`
- Modify: `scripts/run_alignment.py`
- Modify: `tests/test_alignment_pipeline_outputs.py`
- Modify: `tests/test_run_alignment.py`

- [ ] **Step 1: Write failing propagation tests**

In `tests/test_alignment_pipeline_outputs.py`, assert metadata records the production baseline method:

```python
def test_alignment_metadata_records_baseline_integration_method() -> None:
    peak_config = replace(_peak_config(), baseline_integration_method="linear_edge")

    metadata = alignment_metadata(
        discovery_batch_index=Path("batch.tsv"),
        raw_dir=Path("raw"),
        dll_dir=Path("dll"),
        owner_backfill_xic_backend="raw",
        output_level="machine",
        peak_config=peak_config,
    )

    assert metadata["baseline_integration_method"] == "linear_edge"
```

In `tests/test_run_alignment.py`, add CLI/env coverage by mirroring the existing
`test_run_alignment_cli_passes_paths_settings_and_debug_flags` setup. Use the
same temporary `discovery_batch_index`, `raw_dir`, `dll_dir`, `output_dir`, and
`fake_run_alignment`.

```python
def test_run_alignment_accepts_baseline_integration_method_override(
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
        output_dir.mkdir(parents=True, exist_ok=True)
        return AlignmentRunOutputs(
            workbook=None,
            review_html=None,
            review_tsv=output_dir / "alignment_review.tsv",
            matrix_tsv=output_dir / "alignment_matrix.tsv",
            cells_tsv=None,
            integration_audit_tsv=None,
            backfill_seed_audit_tsv=None,
            status_matrix_tsv=None,
            edge_evidence_tsv=None,
        )

    monkeypatch.setattr(run_alignment, "run_alignment", fake_run_alignment)

    code = run_alignment.main([
        "--discovery-batch-index",
        str(batch_index),
        "--raw-dir",
        str(raw_dir),
        "--dll-dir",
        str(dll_dir),
        "--output-dir",
        str(output_dir),
        "--baseline-integration-method",
        "linear_edge",
    ])

    assert code == 0
    assert captured["peak_config"].baseline_integration_method == "linear_edge"
```

Add legacy flag compatibility assertion to
`test_run_alignment_cli_passes_paths_settings_and_debug_flags`:

```python
assert peak_config.baseline_audit_method == "asls"
assert peak_config.baseline_integration_method == "linear_edge"
```

- [ ] **Step 2: Run failing propagation tests**

Run:

```powershell
python -m pytest tests\test_alignment_pipeline_outputs.py::test_alignment_metadata_records_baseline_integration_method tests\test_run_alignment.py -q
```

Expected before implementation: metadata/CLI override failures.

- [ ] **Step 3: Wire method into region audit and outputs**

In `xic_extractor/peak_detection/region_audit.py`, pass:

```python
baseline_integration_method=getattr(config, "baseline_integration_method", "asls"),
```

beside existing `baseline_audit_method`.

In `alignment_metadata`, add:

```python
"baseline_integration_method": peak_config.baseline_integration_method,
```

In `scripts/run_alignment.py`, add optional CLI/env override:

```python
parser.add_argument(
    "--baseline-integration-method",
    choices=("asls", "linear_edge"),
    help="Production baseline method for alignment integration audit.",
)
```

Add helper:

```python
def _baseline_integration_method(args: argparse.Namespace) -> str:
    if args.baseline_integration_method:
        return args.baseline_integration_method
    if _baseline_audit_method(args) == "asls":
        return "linear_edge"
    env_method = os.environ.get("BASELINE_INTEGRATION_METHOD", "").strip().lower()
    if env_method in {"", "asls"}:
        return "asls"
    if env_method == "linear_edge":
        return env_method
    raise ValueError("BASELINE_INTEGRATION_METHOD must be asls or linear_edge")
```

Update `_peak_config` signature and construction:

```python
def _peak_config(
    raw_dir: Path,
    dll_dir: Path,
    output_dir: Path,
    resolver_mode: str,
    baseline_audit_method: str = "",
    baseline_integration_method: str = "asls",
) -> ExtractionConfig:
    ...
    return ExtractionConfig(
        ...
        baseline_audit_method=baseline_audit_method,
        baseline_integration_method=baseline_integration_method,
    )
```

Update the call site:

```python
"peak_config": _peak_config(
    raw_dir,
    dll_dir,
    output_dir,
    _alignment_production_resolver_mode(args.resolver_mode),
    baseline_audit_method=_baseline_audit_method(args),
    baseline_integration_method=_baseline_integration_method(args),
),
```

- [ ] **Step 4: Run propagation tests**

Run:

```powershell
python -m pytest tests\test_alignment_pipeline_outputs.py tests\test_run_alignment.py -q
```

Expected: tests pass.

---

### Task 4: Update Integration Audit TSV Schema

**Files:**
- Modify: `xic_extractor/alignment/tsv_writer.py`
- Modify: `tests/test_alignment_tsv_writer.py`

- [ ] **Step 1: Write failing writer tests**

Update default integration audit expectations:

```python
def test_write_alignment_cell_integration_audit_tsv_default_schema_reports_asls_and_linear_edge_rollback(
    tmp_path: Path,
) -> None:
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

    assert rows[0]["baseline_type"] == "asls"
    assert "area_baseline_corrected_linear_edge" in rows[0]
    assert "baseline_score_linear_edge" in rows[0]
    assert "area_baseline_corrected_asls" not in rows[0]
    assert "baseline_score_asls" not in rows[0]
```

Add rollback schema test:

```python
def test_write_alignment_cell_integration_audit_tsv_can_emit_legacy_asls_shadow_for_linear_edge(
    tmp_path: Path,
) -> None:
    matrix = AlignmentMatrix(
        clusters=(_cluster(),),
        cells=(_cell("sample-a", "detected", area=10.0, integration=True),),
        sample_order=("sample-a",),
    )

    rows = _read_tsv(
        write_alignment_cell_integration_audit_tsv(
            tmp_path / "alignment_cell_integration_audit.tsv",
            matrix,
            baseline_integration_method="linear_edge",
            baseline_audit_method="asls",
        )
    )

    assert rows[0]["baseline_type"] == "linear_edge"
    assert rows[0]["area_baseline_corrected_asls"] != ""
    assert rows[0]["baseline_score_asls"] != ""
    assert "area_baseline_corrected_linear_edge" not in rows[0]
    assert "baseline_score_linear_edge" not in rows[0]
```

- [ ] **Step 2: Run failing writer tests**

Run:

```powershell
python -m pytest tests\test_alignment_tsv_writer.py::test_write_alignment_cell_integration_audit_tsv_default_schema_reports_asls_and_linear_edge_rollback tests\test_alignment_tsv_writer.py::test_write_alignment_cell_integration_audit_tsv_can_emit_legacy_asls_shadow_for_linear_edge -q
```

Expected before implementation: missing parameter/columns.

- [ ] **Step 3: Implement writer schema**

Keep base, promoted rollback, and legacy shadow columns separate:

```python
BASE_ALIGNMENT_CELL_INTEGRATION_AUDIT_COLUMNS = (
    ...
    "baseline_fraction",
    "integration_scan_count",
)

LINEAR_EDGE_ROLLBACK_ALIGNMENT_CELL_INTEGRATION_AUDIT_COLUMNS = (
    "area_baseline_corrected_linear_edge",
    "baseline_score_linear_edge",
)

ALIGNMENT_CELL_INTEGRATION_AUDIT_COLUMNS = (
    BASE_ALIGNMENT_CELL_INTEGRATION_AUDIT_COLUMNS
    + LINEAR_EDGE_ROLLBACK_ALIGNMENT_CELL_INTEGRATION_AUDIT_COLUMNS
)
```

Add writer parameter:

```python
def write_alignment_cell_integration_audit_tsv(
    path: Path,
    matrix: AlignmentMatrix,
    *,
    baseline_integration_method: str = "asls",
    baseline_audit_method: str = "",
) -> Path:
```

Validate:

```python
if baseline_integration_method not in {"asls", "linear_edge"}:
    raise ValueError("baseline_integration_method must be 'asls' or 'linear_edge'")
```

Build mode-specific columns exactly:

```python
if baseline_integration_method == "asls":
    columns = (
        BASE_ALIGNMENT_CELL_INTEGRATION_AUDIT_COLUMNS
        + LINEAR_EDGE_ROLLBACK_ALIGNMENT_CELL_INTEGRATION_AUDIT_COLUMNS
    )
elif baseline_audit_method == "asls":
    columns = (
        BASE_ALIGNMENT_CELL_INTEGRATION_AUDIT_COLUMNS
        + ASLS_ALIGNMENT_CELL_INTEGRATION_AUDIT_COLUMNS
    )
else:
    columns = BASE_ALIGNMENT_CELL_INTEGRATION_AUDIT_COLUMNS
```

Write rollback values:

```python
"area_baseline_corrected_linear_edge": format_value(
    audit.area_baseline_corrected_linear_edge
),
"baseline_score_linear_edge": format_value(audit.baseline_score_linear_edge),
```

In `alignment_metadata`, add:

```python
"baseline_integration_method": peak_config.baseline_integration_method,
```

In `write_outputs_atomic`, add parameter and pass it to the integration-audit writer:

```python
def write_outputs_atomic(
    ...
    baseline_integration_method: str = "asls",
    baseline_audit_method: str = "",
) -> None:
```

```python
lambda path: write_alignment_cell_integration_audit_tsv(
    path,
    matrix,
    baseline_integration_method=baseline_integration_method,
    baseline_audit_method=baseline_audit_method,
)
```

In `xic_extractor/alignment/pipeline.py`, pass the method from `peak_config`:

```python
baseline_integration_method=getattr(
    peak_config,
    "baseline_integration_method",
    "asls",
),
```

- [ ] **Step 4: Run writer tests**

Run:

```powershell
python -m pytest tests\test_alignment_tsv_writer.py -q
```

Expected: writer tests pass after updating old default assertions from linear-edge to AsLS production.

---

### Task 5: Update Diagnostics For Old And Promoted Schemas

**Files:**
- Modify:
  - `tools/diagnostics/p2_asls_shadow_gate.py`
  - `tools/diagnostics/p2_baseline_truth_audit.py`
  - `tools/diagnostics/area_integration_uncertainty_io.py`
- Test:
  - `tests/test_p2_asls_shadow_gate.py`
  - `tests/test_p2_baseline_truth_audit.py`
  - `tests/test_area_integration_uncertainty_audit.py`
  - `tests/test_evidence_spine_consistency.py`
  - `tests/test_p2b_asls_promotion_gate.py`

- [ ] **Step 1: Add promoted-schema diagnostic fixtures**

Add a promoted-schema fixture to `tests/test_p2_asls_shadow_gate.py` with:

```python
{
    "target_label": "ISTD-A",
    "selected_feature_id": "FAM001",
    "sample_stem": "s1",
    "area": "100",
    "area_baseline_corrected": "92",
    "baseline_type": "asls",
    "area_baseline_corrected_linear_edge": "70",
    "baseline_score_linear_edge": "0.70",
}
```

Assert the diagnostic interprets:

```python
assert row.linear_area == pytest.approx(70.0)
assert row.asls_area == pytest.approx(92.0)
```

Add the same promoted-schema fixture to `tests/test_p2_baseline_truth_audit.py`
and assert the generated review row uses linear-edge rollback as the old
baseline comparison and AsLS production as the promoted baseline comparison.

Keep at least one legacy fixture with:

```python
{
    "area_baseline_corrected": "70",
    "baseline_type": "linear_edge",
    "area_baseline_corrected_asls": "92",
}
```

and assert legacy P2 shadow interpretation still works.

- [ ] **Step 2: Add area-uncertainty method-consistency fixture**

In `tests/test_area_integration_uncertainty_audit.py`, add a fixture where:

```python
targeted_row = {
    "area_baseline_corrected": "70",
}
alignment_row = {
    "area_baseline_corrected": "92",
    "baseline_type": "asls",
    "area_baseline_corrected_linear_edge": "70",
}
```

Assert the area-uncertainty diagnostic compares targeted linear-edge against
alignment `area_baseline_corrected_linear_edge`, not against promoted AsLS:

```python
assert row.targeted_baseline_area == pytest.approx(70.0)
assert row.alignment_baseline_area == pytest.approx(70.0)
assert row.baseline_area_method == "linear_edge_compatible"
```

If the row model currently has no method field, add `baseline_area_method` to
the diagnostic row and TSV so downstream reviewers can see whether the
comparison is `linear_edge_compatible` or `asls_promoted`.

- [ ] **Step 3: Implement diagnostic schema resolvers**

For P2 shadow/truth diagnostics, use:

```python
def _linear_and_asls_area(row: Mapping[str, str]) -> tuple[float | None, float | None]:
    baseline_type = row.get("baseline_type", "").strip()
    if baseline_type == "asls":
        return (
            _optional_float(row.get("area_baseline_corrected_linear_edge")),
            _optional_float(row.get("area_baseline_corrected")),
        )
    return (
        _optional_float(row.get("area_baseline_corrected")),
        _optional_float(row.get("area_baseline_corrected_asls")),
    )
```

For area uncertainty, preserve method consistency with targeted candidate TSVs:

```python
def _alignment_baseline_area_for_targeted_linear(row: Mapping[str, str]) -> tuple[float | None, str]:
    linear_rollback = _optional_float(row.get("area_baseline_corrected_linear_edge"))
    if linear_rollback is not None:
        return linear_rollback, "linear_edge_compatible"
    return _optional_float(row.get("area_baseline_corrected")), "legacy_area_baseline_corrected"
```

Do not make production code read P2/P2b artifacts. These compatibility
resolvers belong only in diagnostic tools.

- [ ] **Step 4: Run diagnostic compatibility tests**

Run:

```powershell
python -m pytest tests\test_p2_asls_shadow_gate.py tests\test_p2_baseline_truth_audit.py tests\test_area_integration_uncertainty_audit.py tests\test_evidence_spine_consistency.py tests\test_p2b_asls_promotion_gate.py -q
```

Expected: old shadow fixtures and promoted-schema fixtures both pass.

---

### Task 6: Documentation And Closeout Note

**Files:**
- Modify: `docs/superpowers/specs/2026-05-24-peak-pipeline-area-baseline-asls-promotion-spec.md`
- Modify: `docs/superpowers/specs/2026-05-24-peak-pipeline-modernization-overview-spec.md`
- Create: `docs/superpowers/notes/2026-05-26-p2b-asls-production-promotion-note.md`

- [ ] **Step 1: Update spec status and scope**

Change P2b status to production promotion implemented after tests pass:

```markdown
**Status:** Production promotion implemented; 8RAW gate remains `GO_FOR_PRODUCTION_CANDIDATE`, 85RAW production-ready validation remains separate
```

Update Required Change section to state:

```markdown
Production `alignment_cell_integration_audit.tsv` now reports `area_baseline_corrected`
with `baseline_type=asls` by default. `area_baseline_corrected_linear_edge` and
`baseline_score_linear_edge` are temporary rollback/audit fields. `alignment_matrix.tsv`
continues to emit accepted `cell.area`; changing final matrix quantification is
outside P2b.
```

- [ ] **Step 2: Create closeout note**

Create:

```markdown
# P2b AsLS Production Promotion Note

Date: 2026-05-26

## Verdict

`production_candidate` for integration-audit area baseline promotion.

## What Changed

- `alignment_cell_integration_audit.tsv` production `area_baseline_corrected`
  defaults to AsLS.
- `baseline_type` defaults to `asls`.
- Linear-edge rollback values are emitted as
  `area_baseline_corrected_linear_edge` and `baseline_score_linear_edge`.
- Legacy `--emit-baseline-audit-asls` keeps linear-edge production plus AsLS
  shadow columns for old P2 diagnostic reruns.
- `alignment_matrix.tsv` is unchanged and still reports accepted `cell.area`.

## Promotion Authorization

- Owner acceptance source: current thread instruction to continue after the
  revised P2b gate returned `GO_FOR_PRODUCTION_CANDIDATE`.
- 85RAW waiver: none. This note authorizes only `production_candidate`
  integration-audit promotion, not `production_ready`.

## Validation

- Unit and diagnostic tests:
  - Record the exact focused pytest command and pass count after execution.
  - Record the compile command and exit status after execution.
  - Record the promoted-schema 8RAW rerun commands and summary statuses after execution.
- P2b gate artifact:
  `output\phase1_p2d_rt_boundary_first_p2b_gate\diagnostics\p2b_asls_promotion_gate_target_rt_trend\p2b_asls_promotion_gate_summary.tsv`

## Remaining Risk

85RAW production-ready validation has not been rerun after the production
promotion code change. Treat the result as `production_candidate`, not
`production_ready`.
```

Replace the validation bullets with exact commands and pass counts before finishing.

- [ ] **Step 3: Docs smoke**

Run:

```powershell
rg -n "Record the exact|Record the compile|Record the P2b" docs\superpowers\notes\2026-05-26-p2b-asls-production-promotion-note.md docs\superpowers\specs\2026-05-24-peak-pipeline-area-baseline-asls-promotion-spec.md
```

Expected: no matches.

---

### Task 7: Final Verification And Review

**Files:**
- No planned source edits unless verification finds a defect.

- [ ] **Step 1: Run focused unit suite**

Run:

```powershell
python -m pytest tests\test_baseline_integration.py tests\test_config.py tests\test_run_alignment.py tests\test_alignment_pipeline_outputs.py tests\test_alignment_tsv_writer.py tests\test_untargeted_final_matrix_contract.py tests\test_p2_asls_shadow_gate.py tests\test_p2_baseline_truth_audit.py tests\test_area_integration_uncertainty_audit.py tests\test_evidence_spine_consistency.py tests\test_p2b_asls_promotion_gate.py -q
```

Expected: all pass.

- [ ] **Step 2: Compile touched Python files**

Run:

```powershell
python -m py_compile xic_extractor\peak_detection\integration_audit.py xic_extractor\peak_detection\region_audit.py xic_extractor\alignment\tsv_writer.py xic_extractor\alignment\pipeline.py xic_extractor\alignment\pipeline_outputs.py xic_extractor\configuration\models.py xic_extractor\configuration\settings.py xic_extractor\settings_schema.py scripts\run_alignment.py tools\diagnostics\p2_asls_shadow_gate.py tools\diagnostics\p2_baseline_truth_audit.py tools\diagnostics\area_integration_uncertainty_io.py
```

Expected: no output and exit code 0.

- [ ] **Step 3: Run promoted-schema 8RAW alignment**

Run:

```powershell
python -m scripts.run_alignment --discovery-batch-index output\phase1_p1_resolver_default_validation\discovery\dR\discovery_batch_index.csv --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation --dll-dir C:\Xcalibur\system\programs --output-dir output\phase1_p2b_asls_production_promotion\alignment\8raw_asls_production --output-level validation --resolver-mode region_first_safe_merge --emit-alignment-cells --emit-alignment-integration-audit --performance-profile validation-fast
```

Expected:

- command exits `0`;
- `alignment_cell_integration_audit.tsv` exists;
- header includes `area_baseline_corrected_linear_edge`;
- header does not include `area_baseline_corrected_asls`;
- `baseline_type` rows are `asls` or documented `linear_edge_fallback`;
- `alignment_matrix.tsv` exists and remains part of the normal output.

- [ ] **Step 4: Re-run upstream diagnostics from promoted 8RAW artifacts**

Run evidence spine:

```powershell
python -m tools.diagnostics.evidence_spine_consistency --targeted-dir output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge --alignment-dir output\phase1_p2b_asls_production_promotion\alignment\8raw_asls_production --output-dir output\phase1_p2b_asls_production_promotion\diagnostics\evidence_spine_consistency
```

Run targeted ISTD benchmark against the promoted alignment:

```powershell
python -m tools.diagnostics.targeted_istd_benchmark --targeted-workbook output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge\xic_results_process_w4.xlsx --alignment-dir output\phase1_p2b_asls_production_promotion\alignment\8raw_asls_production --output-dir output\phase1_p2b_asls_production_promotion\diagnostics\targeted_istd_benchmark
```

Run area uncertainty with promoted schema:

```powershell
python -m tools.diagnostics.area_integration_uncertainty_audit --evidence-spine-rows-tsv output\phase1_p2b_asls_production_promotion\diagnostics\evidence_spine_consistency\evidence_spine_consistency_rows.tsv --targeted-peak-candidates-tsv output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge\peak_candidates.tsv --targeted-boundaries-tsv output\phase1_p1_resolver_default_validation\targeted\region_first_safe_merge\tissue_8raw_region_first_safe_merge\peak_candidate_boundaries.tsv --alignment-integration-audit-tsv output\phase1_p2b_asls_production_promotion\alignment\8raw_asls_production\alignment_cell_integration_audit.tsv --output-dir output\phase1_p2b_asls_production_promotion\diagnostics\area_integration_uncertainty
```

Run P2 shadow gate compatibility on promoted schema:

```powershell
python -m tools.diagnostics.p2_asls_shadow_gate --alignment-integration-audit-tsv output\phase1_p2b_asls_production_promotion\alignment\8raw_asls_production\alignment_cell_integration_audit.tsv --targeted-istd-benchmark-summary-tsv output\phase1_p2b_asls_production_promotion\diagnostics\targeted_istd_benchmark\targeted_istd_benchmark_summary.tsv --output-dir output\phase1_p2b_asls_production_promotion\diagnostics\p2_asls_shadow_gate
```

Run baseline truth audit compatibility on promoted schema:

```powershell
python -m tools.diagnostics.p2_baseline_truth_audit --p2-gate-rows-tsv output\phase1_p2b_asls_production_promotion\diagnostics\p2_asls_shadow_gate\p2_asls_shadow_gate_rows.tsv --alignment-integration-audit-tsv output\phase1_p2b_asls_production_promotion\alignment\8raw_asls_production\alignment_cell_integration_audit.tsv --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation --dll-dir C:\Xcalibur\system\programs --include-gate-status PASS --include-gate-status FAIL --output-dir output\phase1_p2b_asls_production_promotion\diagnostics\baseline_truth_audit_all_statuses
```

Expected:

- diagnostics do not crash on promoted schema;
- area uncertainty reports `unexplained_area_mismatch_count=0`;
- P2 shadow/truth diagnostics interpret linear-edge rollback and promoted AsLS
  explicitly, not by assuming `area_baseline_corrected` is old linear-edge.

- [ ] **Step 5: Run P2b gate smoke from promoted-schema diagnostics**

Run:

```powershell
python -m tools.diagnostics.p2b_asls_promotion_gate --p2-gate-rows-tsv output\phase1_p2b_asls_production_promotion\diagnostics\p2_asls_shadow_gate\p2_asls_shadow_gate_rows.tsv --baseline-truth-summary-tsv output\phase1_p2b_asls_production_promotion\diagnostics\baseline_truth_audit_all_statuses\baseline_truth_audit_summary.tsv --area-uncertainty-summary-tsv output\phase1_p2b_asls_production_promotion\diagnostics\area_integration_uncertainty\area_integration_uncertainty_summary.tsv --evidence-spine-rows-tsv output\phase1_p2b_asls_production_promotion\diagnostics\evidence_spine_consistency\evidence_spine_consistency_rows.tsv --target-rt-trend-summary-tsv output\phase1_p8b_superwindow\diagnostics\targeted_istd_rt_trend_85raw\targeted_istd_rt_drift_summary.tsv --output-dir output\phase1_p2b_asls_production_promotion\diagnostics\p2b_asls_promotion_gate
```

Expected summary:

```text
overall_status=GO_FOR_PRODUCTION_CANDIDATE
hard_blocker_count=0
```

- [ ] **Step 6: Diff hygiene**

Run:

```powershell
git diff --check
git status --short
```

Expected:

- `git diff --check` has no whitespace errors.
- `git status --short` still shows unrelated diagnostic cleanup files; do not stage them with P2b promotion.

- [ ] **Step 5: Implementation review**

Request code review focused on:

- whether `alignment_matrix.tsv` remained unchanged;
- whether AsLS is now the default only for integration-audit `area_baseline_corrected`;
- whether old P2 shadow reruns remain possible with `baseline_integration_method=linear_edge` plus `baseline_audit_method=asls`;
- whether linear-edge rollback fields are clearly labeled and temporary;
- whether any diagnostic accidentally treats promoted AsLS values as old linear-edge values.

Fix any review findings before reporting completion.

---

## Self-Review

- Spec coverage: covers the P2b required production switch for `area_baseline_corrected`, rollback linear-edge audit field, config/default update, and production-artifact separation from P2/P3 diagnostics.
- Draft-token scan: no unfinished angle-bracket tokens are intentionally left in the plan. The closeout-note draft instructs the implementer to replace validation bullets with exact executed commands before finishing.
- Type consistency: use `baseline_integration_method` for production selection and keep `baseline_audit_method` for legacy shadow emission.
- Public contract check: `alignment_matrix.tsv` is explicitly not changed; `alignment_cell_integration_audit.tsv` schema changes are documented and tested.
