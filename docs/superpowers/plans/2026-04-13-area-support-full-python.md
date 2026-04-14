# Area Support & Full-Python Architecture — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Source spec:** `docs/superpowers/specs/2026-04-13-area-support-design.md`

**Goal:** Add LC-MS peak area support and replace the PowerShell extraction path with a testable Python pipeline. The new pipeline must write apex RT, raw apex intensity, raw integrated area, peak boundaries, four-state neutral-loss results, and diagnostics, while keeping CLI and GUI behavior on one shared execution path.

**Architecture:** Introduce a new `xic_extractor/` package. `config.py` owns schema loading and migration, `raw_reader.py` owns Thermo `.NET` interop, `signal_processing.py` owns scipy peak detection and integration, `neutral_loss.py` owns MS2 confirmation, and `extractor.py` orchestrates per-file extraction and CSV writes. `scripts/run_extraction.py` and `gui/workers/pipeline_worker.py` both call the same `extractor.run(config, targets, ...)`. `scripts/csv_to_excel.py` consumes both output CSVs to build Data, Summary, and Diagnostics sheets.

**Tech Stack:** Python 3.10+, PyQt6, openpyxl, numpy, scipy, pythonnet, pytest, pytest-cov, uv, Windows PowerShell.

---

## Guardrails

- Keep the current PowerShell pipeline as a reference until migration validation passes. Do not delete `scripts/01_extract_xic.ps1` until Task 11.
- Do not overwrite user-edited live config/data files. Only `config/settings.example.csv` and `config/targets.example.csv` are versioned; all runtime config/profile CSVs under `config/` stay local and ignored. Prefer updating `.example.csv` files and tests; only touch `config/settings.csv` or `config/targets.csv` when explicitly needed for migration behavior.
- `raw_reader.py` must not import or load `pythonnet`/Thermo DLLs at module import time. Lazy-load on first `open_raw()` call so tests run on machines without DLLs.
- Production numeric outputs use raw intensity for apex intensity and area. Smoothed intensity is retained only for validation diagnostics.
- `ND` stays coarse in `xic_results.csv`; detailed reasons go to `xic_diagnostics.csv` and the Excel Diagnostics sheet.
- CLI and GUI must share `load_config(config_dir)` and `extractor.run()`. No duplicated settings parsing in GUI worker or Excel generation.
- Developer-only validation and security gates must not create routine GUI workload. Normal users should see clear "what happened / what to fix" messages, not migration workbooks, override fields, or audit jargon.
- Use TDD where practical. At minimum, write tests before implementing each pure or mockable module.
- Use PowerShell-compatible commands in docs and handoffs.

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `xic_extractor/__init__.py` | Package marker and public package metadata |
| Create | `xic_extractor/config.py` | Typed config dataclasses, legacy migration, schema validation |
| Create | `xic_extractor/signal_processing.py` | Savitzky-Golay smoothing, scipy peak detection, trapezoid area |
| Create | `xic_extractor/raw_reader.py` | Lazy pythonnet/Thermo DLL wrapper and context manager |
| Create | `xic_extractor/neutral_loss.py` | Four-state NL confirmation with diagnostic ppm/counts |
| Create | `xic_extractor/extractor.py` | Main run orchestration, result models, CSV writing, diagnostics |
| Create | `scripts/run_extraction.py` | CLI entry point using the shared Python pipeline |
| Modify | `scripts/csv_to_excel.py` | Area columns, Diagnostics sheet, new Summary metrics, overload-style `run()` |
| Modify | `gui/workers/pipeline_worker.py` | Remove PS1 subprocess path; call Python extractor directly |
| Modify | `gui/sections/settings_section.py` | New settings controls and non-strict migration on load |
| Modify | `gui/config_io.py` | Preserve/backfill descriptions for migrated settings keys |
| Modify | `gui/sections/results_section.py` | New summary cards and diagnostics count |
| Modify | `config/settings.example.csv` | New canonical 9-key schema |
| Modify | `pyproject.toml` | Add numpy/scipy/pythonnet/pytest-cov, CLI script, package discovery |
| Modify | `.github/workflows/ci.yml` | Pin shared workflow reference instead of floating `@main` |
| Modify | `.github/workflows/build.yml` | Pin shared action reference before release-capable builds |
| Create | `tests/test_config.py` | Config validation and migration tests |
| Create | `tests/test_signal_processing.py` | Synthetic signal tests, highest priority |
| Create | `tests/test_raw_reader.py` | Mocked pythonnet/Thermo tests |
| Create | `tests/test_neutral_loss.py` | Four-state NL tests |
| Create | `tests/test_extractor.py` | Mock raw-reader integration and CSV tests |
| Modify | `tests/test_csv_to_excel.py` | Area/Summary/Diagnostics tests |
| Modify | `tests/test_pipeline_worker.py` | Structured summary tests, no stdout regex |
| Modify | `tests/test_config_io.py` | Settings description migration/backfill tests |
| Create | `scripts/validate_migration.py` | Real `.raw` comparison gate before merge |
| Delete | `scripts/01_extract_xic.ps1` | Remove only after validation sign-off |

---

## Task 1: Dependencies and Package Scaffold

**Files:**
- Modify: `pyproject.toml`
- Create: `xic_extractor/__init__.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/build.yml`

- [ ] **Step 1: Update project dependencies**

In `pyproject.toml`, add `numpy>=1.26`, `scipy>=1.11`, `pythonnet>=3.0`, `pytest-cov>=5.0`, and include `xic_extractor*` in package discovery.

Do **not** add the `xic-extractor-cli` entry point yet. Add it in Task 7 after `scripts/run_extraction.py` exists, so intermediate packaging checks never point at a missing module.

- [ ] **Step 1b: Pin release-capable CI references**

Replace floating shared workflow/action references such as `Chao-hu-Lab/shared-workflows/...@main` with a reviewed tag or commit SHA. This is invisible to users, but it prevents a release build from changing behavior because another repository's `main` branch moved.

- [ ] **Step 2: Create package marker**

Create `xic_extractor/__init__.py` with a short package docstring and, if desired, `__all__ = []`.

- [ ] **Step 3: Sync environment**

```powershell
uv sync --extra dev
```

If dependency download fails due to sandbox/network restrictions, rerun with approval.

- [ ] **Step 4: Verify imports**

```powershell
uv run python -c "import numpy, scipy; print('scientific deps OK')"
```

Expected: `scientific deps OK`.

- [ ] **Step 5: Verify dependency lock and audit**

```powershell
uv lock --check
uvx pip-audit
```

If `pip-audit` cannot run in the local environment, record it as `SKIPPED — tool unavailable` in the task notes and rely on Dependabot for ongoing monitoring. Do not block normal GUI users on this audit.

- [ ] **Step 6: Commit**

```powershell
git add pyproject.toml uv.lock xic_extractor/__init__.py .github/workflows/ci.yml .github/workflows/build.yml
git commit -m "chore: scaffold python extraction package"
```

---

## Task 2: Config Module and Settings Migration

**Files:**
- Create: `xic_extractor/config.py`
- Create: `tests/test_config.py`
- Modify: `config/settings.example.csv`
- Modify: `gui/config_io.py`
- Modify: `tests/test_config_io.py`

### Step 2a: Tests first

- [ ] **Step 1: Add config validation tests**

Create `tests/test_config.py` covering:

- `load_config()` derives `output_csv` and `diagnostics_csv` from `config_dir.parent / "output"`.
- `load_config()` creates the output directory.
- `migrate_settings_dict()` renames `smooth_points` to `smooth_window`.
- `migrate_settings_dict()` drops `smooth_sigma` with a warning.
- Missing new keys are filled from defaults with warnings.
- Invalid `smooth_window` even number raises `ConfigError`.
- Invalid `smooth_polyorder >= smooth_window` raises `ConfigError`.
- Invalid ranges for `peak_rel_height`, `peak_min_prominence_ratio`, `ms2_precursor_tol_da`, and `nl_min_intensity_ratio` raise `ConfigError`.
- Duplicate target labels raise `ConfigError`.
- `istd_pair` must reference an existing target with `is_istd=True`.
- NL targets require positive `neutral_loss_da`, `nl_ppm_warn`, and `nl_ppm_max`, with warn <= max.
- No-NL targets ignore empty NL threshold fields.

- [ ] **Step 2: Add GUI settings description tests**

Extend `tests/test_config_io.py` so `write_settings()` preserves existing descriptions and backfills new canonical descriptions when a migrated key such as `smooth_window` replaces legacy `smooth_points`.

- [ ] **Step 3: Run tests and expect failures**

```powershell
uv run pytest tests/test_config.py tests/test_config_io.py -v
```

Expected: new config tests fail because `xic_extractor.config` does not exist yet; any unrelated existing test failures must be noted before continuing.

### Step 2b: Implementation

- [ ] **Step 4: Implement dataclasses and defaults**

In `xic_extractor/config.py`, create `ExtractionConfig`, `Target`, `ConfigError`, `migrate_settings_dict(raw)`, and `load_config(config_dir)`. Use `dataclass(frozen=True)` for `ExtractionConfig` and `Target`. Error messages must include file path, row number where applicable, column name, and offending value.

- [ ] **Step 5: Implement strict settings validation**

Validate `data_dir`, `dll_dir`, `smooth_window`, `smooth_polyorder`, `peak_rel_height`, `peak_min_prominence_ratio`, `ms2_precursor_tol_da`, `nl_min_intensity_ratio`, and `count_no_ms2_as_detected` exactly as the source spec defines.

- [ ] **Step 6: Implement target validation**

Validate label uniqueness, numeric mz/ppm/RT fields, boolean `is_istd`, ISTD pair references, and NL threshold consistency exactly as the source spec defines.

- [ ] **Step 7: Update `config/settings.example.csv`**

Replace legacy smoothing keys with the canonical schema from spec section 3.3: `data_dir`, `dll_dir`, `smooth_window`, `smooth_polyorder`, `peak_rel_height`, `peak_min_prominence_ratio`, `ms2_precursor_tol_da`, `nl_min_intensity_ratio`, `count_no_ms2_as_detected`.

- [ ] **Step 8: Update settings description backfill**

In `gui/config_io.py`, keep `read_settings()` raw. Update `write_settings()` so canonical keys get descriptions from existing rows when present, or from a local canonical description mapping when missing.

- [ ] **Step 9: Verify**

```powershell
uv run pytest tests/test_config.py tests/test_config_io.py -v
```

Expected: all selected tests pass.

- [ ] **Step 10: Commit**

```powershell
git add xic_extractor/config.py tests/test_config.py tests/test_config_io.py gui/config_io.py config/settings.example.csv
git commit -m "feat: add typed extraction config loading"
```

---

## Task 3: Signal Processing Module

**Files:**
- Create: `xic_extractor/signal_processing.py`
- Create: `tests/test_signal_processing.py`

### Step 3a: Tests first

- [ ] **Step 1: Add synthetic signal fixtures**

In `tests/test_signal_processing.py`, create helper fixtures for Gaussian peaks, two different-height peaks, pure noise, flat zero signal, short signal, edge peak, narrow peak, and negative baseline noise. Use a small fake `ExtractionConfig` instance from `xic_extractor.config`.

- [ ] **Step 2: Add critical tests**

Assertions:

- Clean peak returns `status == "OK"`.
- RT error <= 0.01 min.
- raw apex intensity within 2%.
- area within 2% of synthetic reference where applicable.
- two-peak case chooses the highest peak.
- pure noise returns `PEAK_NOT_FOUND`.
- zero signal returns `NO_SIGNAL`.
- short signal returns `WINDOW_TOO_SHORT`.
- edge peak produces clamped valid boundaries.
- `area` is computed from raw intensity, not smoothed intensity.

- [ ] **Step 3: Run tests and expect failures**

```powershell
uv run pytest tests/test_signal_processing.py -v
```

Expected: import failure until module exists.

### Step 3b: Implementation

- [ ] **Step 4: Implement result dataclasses**

Create `PeakResult` and `PeakDetectionResult` with the exact status literals from the spec: `OK`, `NO_SIGNAL`, `WINDOW_TOO_SHORT`, `PEAK_NOT_FOUND`.

- [ ] **Step 5: Implement `find_peak_and_area()`**

Algorithm:

1. Empty input => `NO_SIGNAL`.
2. `len(intensity) < smooth_window` => `WINDOW_TOO_SHORT`.
3. Smooth with `scipy.signal.savgol_filter`.
4. `max(smoothed) <= 0` => `NO_SIGNAL`.
5. `find_peaks(smoothed, prominence=max_smoothed * peak_min_prominence_ratio)`.
6. No peaks => `PEAK_NOT_FOUND`.
7. Pick highest smoothed peak.
8. Use `peak_widths(..., rel_height=peak_rel_height)` for boundaries.
9. Clamp boundaries.
10. Integrate raw intensity via `numpy.trapezoid(intensity[left:right], rt[left:right])`.
11. Return raw apex intensity, smoothed apex intensity, area, start, end.

- [ ] **Step 6: Verify focused coverage**

```powershell
uv run pytest tests/test_signal_processing.py --cov=xic_extractor.signal_processing --cov-report=term-missing -v
```

Expected: tests pass; target coverage >= 95%.

- [ ] **Step 7: Commit**

```powershell
git add xic_extractor/signal_processing.py tests/test_signal_processing.py
git commit -m "feat: detect peaks and integrate raw XIC area"
```

---

## Task 4: Raw Reader Module

**Files:**
- Create: `xic_extractor/raw_reader.py`
- Create: `tests/test_raw_reader.py`

### Step 4a: Tests first

- [ ] **Step 1: Add mock-based tests**

Create `tests/test_raw_reader.py` with mocked `clr` and mocked Thermo class tree. Cover:

- importing `xic_extractor.raw_reader` does not require pythonnet or DLLs.
- `open_raw()` raises `RawReaderError` when DLL load fails.
- preflight failures return actionable messages for missing `pythonnet`, missing .NET runtime, missing `dll_dir`, and missing expected Thermo DLL files.
- `open_raw()` loads only expected Thermo assemblies from the resolved `dll_dir`, never from cwd or `PATH` fallback.
- `RawFileHandle.__exit__()` calls `Dispose()`.
- `extract_xic()` returns empty numpy arrays when chromatogram data is empty.
- `iter_ms2_scans()` yields `Ms2ScanEvent(scan=...)` for parsed scans.
- scan parse errors are yielded as `Ms2ScanEvent(parse_error=...)`, not silently swallowed.

- [ ] **Step 2: Run tests and expect failures**

```powershell
uv run pytest tests/test_raw_reader.py -v
```

Expected: import failure until module exists.

### Step 4b: Implementation

- [ ] **Step 3: Implement dataclasses and errors**

Create `RawReaderError`, `RawFileHandle`, `Ms2ScanEvent`, `Ms2Scan`, and `open_raw(path, dll_dir)`.

- [ ] **Step 4: Implement lazy pythonnet loading**

Keep CLR import/loading inside a private helper called from `open_raw()`. Cache the loaded state so references are added once per process.

- [ ] **Step 4b: Add low-friction runtime preflight**

Add a small preflight helper used by CLI and GUI at run time, not on Settings tab load. It should check:

- `pythonnet` import availability.
- .NET runtime availability when detectable.
- `dll_dir.resolve()` exists.
- expected Thermo DLL filenames exist under `dll_dir`.

The user-facing error should be one paragraph with the failed check, the path inspected, and the next action, e.g. "Xcalibur DLLs were not found in `C:\...`; open Settings and correct DLL directory." Do not expose stack traces in GUI errors.

- [ ] **Step 4c: Restrict DLL load surface**

Use explicit absolute DLL paths built from `dll_dir.resolve()` and a fixed expected assembly filename list. Do not let `clr.AddReference()` search cwd, `PATH`, or arbitrary assembly names from config.

- [ ] **Step 5: Implement context manager cleanup**

`RawFileHandle.__exit__()` must call `Dispose()` on the underlying `.NET` raw object. It must tolerate cleanup exceptions only if they are logged or wrapped intentionally.

- [ ] **Step 6: Implement XIC and MS2 methods**

Translate Thermo chromatogram and spectrum data into numpy arrays. Ensure empty XIC returns empty arrays, `base_peak` is `max(intensities)` or `0.0`, MS2 scan iteration respects `[rt_min, rt_max]`, and per-scan parse failures become parse-error events.

- [ ] **Step 7: Verify**

```powershell
uv run pytest tests/test_raw_reader.py -v
```

Expected: mock tests pass without real Thermo DLLs.

- [ ] **Step 8: Manual DLL smoke test**

Only when a real `.raw` and valid `dll_dir` are available, run a one-file smoke script through `uv run python`. Mark this as skipped if no `.raw` file is available.

- [ ] **Step 9: Commit**

```powershell
git add xic_extractor/raw_reader.py tests/test_raw_reader.py
git commit -m "feat: add thermo raw reader wrapper"
```

---

## Task 5: Neutral Loss Module

**Files:**
- Create: `xic_extractor/neutral_loss.py`
- Create: `tests/test_neutral_loss.py`

### Step 5a: Tests first

- [ ] **Step 1: Add mock raw handle tests**

Create tests for:

- `OK`: best ppm <= warn threshold.
- `WARN`: warn < best ppm <= max threshold.
- `NL_FAIL` with `best_ppm`: product found inside diagnostic window but outside `nl_ppm_max`.
- `NL_FAIL` with no `best_ppm`: no product inside diagnostic window.
- `NO_MS2`: no precursor-matched MS2 scan.
- parse-error events increment `parse_error_count`.
- low-intensity product below `nl_min_intensity_ratio` is ignored.
- empty/all-zero spectrum does not produce a false match.

- [ ] **Step 2: Run tests and expect failures**

```powershell
uv run pytest tests/test_neutral_loss.py -v
```

Expected: import failure until module exists.

### Step 5b: Implementation

- [ ] **Step 3: Implement `NLResult`**

Fields: `status`, `best_ppm`, `valid_ms2_scan_count`, `parse_error_count`, and `matched_scan_count`. `to_token()` returns only `OK`, `WARN_12.3ppm`, `NL_FAIL`, or `NO_MS2`.

- [ ] **Step 4: Implement `check_nl()`**

Use `diagnostic_ppm = max(3 * nl_ppm_max, NL_DIAGNOSTIC_PPM_FLOOR)` and `expected_product = precursor_mz - neutral_loss_da`. Classify exactly as the spec: no matched precursor scans => `NO_MS2`; no candidate product inside diagnostic window => `NL_FAIL`; best ppm > max => `NL_FAIL`; warn < best ppm <= max => `WARN`; best ppm <= warn => `OK`.

- [ ] **Step 5: Verify**

```powershell
uv run pytest tests/test_neutral_loss.py -v
```

Expected: all pass.

- [ ] **Step 6: Commit**

```powershell
git add xic_extractor/neutral_loss.py tests/test_neutral_loss.py
git commit -m "feat: add four-state neutral loss confirmation"
```

---

## Task 6: Extractor Orchestrator and CSV Outputs

**Files:**
- Create: `xic_extractor/extractor.py`
- Create: `tests/test_extractor.py`

### Step 6a: Tests first

- [ ] **Step 1: Add mocked extraction integration tests**

Use monkeypatching/fakes for `open_raw()`, `find_peak_and_area()`, and `check_nl()`. Cover:

- one `.raw` file and one no-NL target writes `RT/Int/Area/PeakStart/PeakEnd`.
- NL target writes the extra `_NL` column.
- failed peak writes `ND` for RT/Int/Area/PeakStart/PeakEnd`.
- file-level error writes `ERROR` across target columns and a `FILE_ERROR` diagnostic.
- `NL_FAIL` and `NO_MS2` create diagnostics.
- `WINDOW_TOO_SHORT`, `NO_SIGNAL`, and `PEAK_NOT_FOUND` create distinct diagnostics.
- `progress_callback(current, total, filename)` fires after each file.
- `should_stop()` is checked between files and returns already-processed results.
- CSV headers omit `_NL` for no-NL targets.

- [ ] **Step 2: Run tests and expect failures**

```powershell
uv run pytest tests/test_extractor.py -v
```

Expected: import failure until module exists.

### Step 6b: Implementation

- [ ] **Step 3: Implement result dataclasses**

Create `DiagnosticRecord`, `ExtractionResult`, `FileResult`, and `RunOutput`.

- [ ] **Step 4: Implement `_build_diagnostic()`**

Keep the mapping from peak/NL/file failure to diagnostics as a small pure function. Include numeric detail in `reason`.

- [ ] **Step 5: Implement CSV writing**

Write `config.output_csv` and `config.diagnostics_csv` using `utf-8-sig`, `csv.DictWriter`, stable target order, and token formatting:

- numeric values rounded consistently with existing output style.
- failed peak values => `ND`.
- file error values => `ERROR`.
- NL token from `NLResult.to_token()`.

- [ ] **Step 6: Implement `run()`**

Loop `*.raw` in `config.data_dir`. For each file:

- open raw via context manager.
- process every target.
- run peak detection first.
- run NL independently for targets with `neutral_loss_da`.
- catch single-file raw errors and continue.
- call `gc.collect()` every 50 files.
- check `should_stop()` between files.

- [ ] **Step 7: Verify**

```powershell
uv run pytest tests/test_extractor.py tests/test_signal_processing.py tests/test_neutral_loss.py -v
```

Expected: all pass.

- [ ] **Step 8: Commit**

```powershell
git add xic_extractor/extractor.py tests/test_extractor.py
git commit -m "feat: orchestrate python XIC extraction outputs"
```

---

## Task 7: CLI Entry Point

**Files:**
- Create: `scripts/run_extraction.py`
- Modify: `scripts/__init__.py` if needed
- Modify: `pyproject.toml`

- [ ] **Step 1: Implement CLI**

Create `scripts/run_extraction.py`:

- argparse `--base-dir`
- argparse `--skip-excel`
- call `load_config(args.base_dir / "config")`
- call `extractor.run(config, targets, progress_callback=...)`
- print processed file count and diagnostics count
- call `csv_to_excel.run(config, targets)` unless skipped

- [ ] **Step 2: Add CLI entry point**

In `pyproject.toml`, add:

```toml
[project.scripts]
xic-extractor-cli = "scripts.run_extraction:main"
```

Keep the existing `xic-extractor = "gui.main:main"` entry point.

- [ ] **Step 3: Smoke test help**

```powershell
uv run python -m scripts.run_extraction --help
```

Expected: help text prints and exits 0.

- [ ] **Step 4: Commit**

```powershell
git add scripts/run_extraction.py scripts/__init__.py pyproject.toml
git commit -m "feat: add python extraction cli"
```

---

## Task 8: Excel Conversion Updates

**Files:**
- Modify: `scripts/csv_to_excel.py`
- Modify: `tests/test_csv_to_excel.py`

### Step 8a: Tests first

- [ ] **Step 1: Update column metadata tests**

Add tests confirming `_load_column_meta()` creates `ms1_area`, `ms1_peak_start`, `ms1_peak_end`, and `ms2_nl` for each target, with `_NL` omitted for no-NL targets.

- [ ] **Step 2: Update Data sheet tests**

Use rows with numeric area, `ND`, `ERROR`, `OK`, `WARN_12.3ppm`, `NL_FAIL`, and `NO_MS2`. Assert display symbols/fills for each token.

Also add formula-injection tests for user-controlled text fields. `SampleName` and target `label` values beginning with `=`, `+`, `-`, or `@` must render as literal text in Excel, not formulas.

- [ ] **Step 3: Update Summary tests**

Assert:

- `Mean Int` row removed.
- `Median Area` row added.
- `Area / ISTD ratio` row added.
- `NL ✓/⚠/✗/—` row added.
- `RT Δ vs ISTD (%)` retained.
- `_is_detected()` honors `count_no_ms2_as_detected`.
- ratio eligibility evaluates analyte and ISTD independently.

- [ ] **Step 4: Add Diagnostics sheet tests**

Create synthetic `xic_diagnostics.csv`; assert workbook contains `Diagnostics` sheet, expected headers, issue rows, and auto-filter. When diagnostics rows exist, assert the saved workbook opens with `Diagnostics` as the active sheet.

- [ ] **Step 5: Run tests and expect failures**

```powershell
uv run pytest tests/test_csv_to_excel.py -v
```

Expected: failures until implementation is updated.

### Step 8b: Implementation

- [ ] **Step 6: Add overload-style `run()`**

Support both `run(base_dir: Path) -> Path` and `run(config: ExtractionConfig, targets: list[Target]) -> Path`. The `Path` mode calls `load_config(base_dir / "config")` and recurses.

- [ ] **Step 7: Update Data sheet**

Extend metadata and formatting for `Area`, `PeakStart`, `PeakEnd`, and four-state NL tokens. Use dimmer target palette variants for peak boundaries.

Sanitize only Excel text cells that come from filenames or config labels by forcing literal text for values starting with Excel formula prefixes (`=`, `+`, `-`, `@`). This is invisible to normal users except that dangerous-looking names open safely.

- [ ] **Step 8: Update Summary sheet**

Implement `_is_detected(row, rt_key, area_key, nl_key, count_no_ms2)`, median area, area/ISTD ratio as `mean±SD (n=count)`, four-count NL row, and retained RT delta row.

- [ ] **Step 9: Add Diagnostics sheet**

Read `config.diagnostics_csv` if present. Add `Diagnostics` sheet with `SampleName`, `Target`, `Issue`, and `Reason`. Include auto-filter and issue-based color fills. If at least one diagnostic row exists, set the workbook active sheet to `Diagnostics` before saving so `os.startfile()` opens the workbook on the problem sheet without OS automation.

- [ ] **Step 10: Verify**

```powershell
uv run pytest tests/test_csv_to_excel.py -v
```

Expected: all pass.

- [ ] **Step 11: Commit**

```powershell
git add scripts/csv_to_excel.py tests/test_csv_to_excel.py
git commit -m "feat: add area and diagnostics to Excel output"
```

---

## Task 9: GUI Integration

**Files:**
- Modify: `gui/workers/pipeline_worker.py`
- Modify: `tests/test_pipeline_worker.py`
- Modify: `gui/sections/settings_section.py`
- Modify: `gui/sections/results_section.py`
- Modify: `gui/main_window.py`

### Step 9a: Worker tests first

- [ ] **Step 1: Replace stdout parser tests**

Remove `_parse_summary()` tests. Add tests that monkeypatch `xic_extractor.config.load_config`, `xic_extractor.extractor.run`, and `scripts.csv_to_excel.run`.

Assert:

- worker emits structured `finished` summary.
- worker passes `progress_callback`.
- worker passes `should_stop`.
- `ConfigError` emits `設定檔錯誤：...`.
- `RawReaderError` emits `Raw file 讀取失敗：...`.
- `stop()` calls `requestInterruption()`.
- worker constructor receives a `config_dir: Path`, and `load_config()` is called with that exact path.
- `MainWindow._on_run()` constructs `PipelineWorker(_ROOT / "config")`, not `_SCRIPTS_DIR`, so frozen builds read the user-writable config directory rather than the read-only bundle.

- [ ] **Step 2: Run tests and expect failures**

```powershell
uv run pytest tests/test_pipeline_worker.py -v
```

Expected: failures until worker is refactored.

### Step 9b: Worker implementation

- [ ] **Step 3: Refactor `PipelineWorker`**

Change the constructor to `PipelineWorker(config_dir: Path)` and store `self._config_dir`. Remove `subprocess.Popen`, `_run_ps1()`, `_run_python()`, `_parse_summary()`, and `_stop_requested`. Add `stop()` as a thin `requestInterruption()` wrapper. Implement `run()` as `load_config(self._config_dir)` -> `extractor.run()` -> `csv_to_excel.run(config, targets)` -> `build_summary()`.

- [ ] **Step 3b: Update `MainWindow` worker wiring**

In `gui/main_window.py`, replace `PipelineWorker(_SCRIPTS_DIR)` with `PipelineWorker(_ROOT / "config")`. Keep `_SCRIPTS_DIR` only if another codepath still needs bundled scripts; otherwise remove the stale constant when `scripts/01_extract_xic.ps1` is deleted.

- [ ] **Step 4: Implement `build_summary()`**

Produce:

```python
{
    "total_files": int,
    "excel_path": str,
    "targets": [
        {
            "label": str,
            "detected": int,
            "total": int,
            "nl_ok": int,
            "nl_warn": int,
            "nl_fail": int,
            "nl_no_ms2": int,
            "median_area": float | None,
        },
    ],
    "istd_warnings": [
        {"label": str, "detected": int, "total": int},
    ],
    "diagnostics_count": int,
}
```

Use `config.count_no_ms2_as_detected` when counting detection.

- [ ] **Step 5: Verify worker tests**

```powershell
uv run pytest tests/test_pipeline_worker.py -v
```

Expected: all pass.

### Step 9c: Settings UI

- [ ] **Step 6: Add settings controls**

In `SettingsSection`, replace old `smooth_points`/`smooth_sigma` UI with `smooth_window`, `smooth_polyorder`, `peak_rel_height`, `peak_min_prominence_ratio`, `ms2_precursor_tol_da`, `nl_min_intensity_ratio`, and `count_no_ms2_as_detected`. Group them under "Signal processing" and "MS2 / NL".

- [ ] **Step 7: Add non-strict migration on load**

`SettingsSection.load()` should accept raw dicts, call `migrate_settings_dict()` only, populate the form, avoid strict path validation, and return `True` when the loaded values were canonicalized or default-filled. Surface warnings through a non-blocking status label if practical.

- [ ] **Step 7b: Persist first-run settings migration**

In `MainWindow._load_config()`, if `SettingsSection.load(settings)` returns `True`, immediately call `write_settings(self._settings.get_values())`. Add a test or focused widget check proving a legacy settings dict with `smooth_points`/`smooth_sigma` is rewritten to canonical keys on GUI load, without requiring valid `data_dir`/`dll_dir`.

- [ ] **Step 8: Update `get_values()` and `is_valid()`**

Return canonical schema only. GUI-level validation should mirror key numeric rules, but strict full validation remains in `load_config()` at run time.

### Step 9d: Results UI

- [ ] **Step 9: Update result cards**

For each target card:

- main value: `detected/total`
- detail: `✓{nl_ok} ⚠{nl_warn} ✗{nl_fail} —{nl_no_ms2}`
- include `Median Area` if useful within current card layout.

Add a Diagnostics card with `diagnostics_count`.

- [ ] **Step 10: Excel open behavior**

Do not add platform-specific Excel automation. Rely on Task 8 setting `Diagnostics` as the workbook active sheet when diagnostics rows exist; `_open_excel()` can continue to call `os.startfile(self._excel_path)`.

- [ ] **Step 11: Run GUI-related tests**

```powershell
uv run pytest tests/test_pipeline_worker.py tests/test_config_io.py tests/test_targets_section.py -v
```

Expected: all pass.

- [ ] **Step 12: Commit**

```powershell
git add gui/workers/pipeline_worker.py gui/sections/settings_section.py gui/sections/results_section.py gui/main_window.py tests/test_pipeline_worker.py
git commit -m "feat: run extraction through shared python pipeline"
```

---

## Task 10: Migration Validation Script

**Files:**
- Create: `scripts/validate_migration.py`
- Optional Create: `docs/superpowers/specs/2026-04-13-migration-artifacts/`
- Output: `docs/superpowers/specs/2026-04-13-migration-validation.xlsx`

**UX boundary:** This is a developer/merge-time tool only. It must never appear in the normal GUI run path, and it must not require routine users to review screenshots or fill sign-off fields.

- [ ] **Step 1: Implement validation CLI skeleton**

Support `--old-worktree`, `--new-worktree`, `--raw-file`, repeated `--case NAME=PATH` or a small config section inside the script, `--strict`, and `--output`.

- [ ] **Step 2: Run old and new pipelines**

Old pipeline: use the master/reference worktree, run `scripts/01_extract_xic.ps1`, and collect old `xic_results.csv`.

New pipeline: use current branch/worktree and call the Python extraction stack in a validation mode that preserves `PeakResult.intensity_smoothed`. Do **not** rely only on `xic_results.csv`, because production CSV intentionally omits smoothed intensity.

Required validation-only output:

```csv
SampleName,Target,RT_New,Int_New_Raw,Int_New_Smoothed,Area_New,PeakStart_New,PeakEnd_New,NL_New
```

This can be produced either by importing `load_config()` + `extractor.run()` inside `validate_migration.py` and walking `RunOutput.file_results`, or by invoking a dedicated validation helper subprocess. In both cases, keep smoothed intensity out of `xic_results.csv`; it belongs only in validation artifacts.

- [ ] **Step 3: Compare thresholds**

Implement spec thresholds:

- median `|RT_new - RT_old| <= 0.003` min.
- max `|RT_new - RT_old| <= 0.010` min.
- area/intensity sanity ratio in `[0.5, 2.0]`.
- smoothed apex comparison median in `[0.95, 1.05]`, max deviation < 20%.
- NL status agreement >= 95% after mapping `NL_FAIL` and `NO_MS2` to old `ND`.

If `Int_New_Smoothed` is missing for any OK peak, `--strict` must fail before threshold comparison. A migration gate with missing validation columns is not a pass.

- [ ] **Step 4: Write validation workbook**

Create sheets `Summary`, `PerTarget`, and `FAIL`. Include skipped acceptance cases with justification.

The `FAIL` sheet may include optional override columns, but they are only for maintainers who intentionally accept a strict-threshold failure as an algorithmic improvement:

- `OverrideDecision` — empty by default; optional value `ACCEPT_NEW_ALGORITHM`
- `OverrideReason` — required only if `OverrideDecision` is set
- `Reviewer` — optional
- `ScreenshotPath` — optional, never required

Do not require screenshots or manual review for passing validation runs. Most users should never know these fields exist.

- [ ] **Step 5: Strict exit behavior**

With `--strict`, exit non-zero if any threshold fails. Optional override evidence is only honored when the script is explicitly run in an override-accepting mode, e.g. `--allow-overrides`. The default strict path must stay fully automatic.

- [ ] **Step 6: Commit script**

Do not commit generated validation workbook until it has been run on real user-designated `.raw` files.

```powershell
git add scripts/validate_migration.py
git commit -m "test: add migration validation harness"
```

---

## Task 11: End-to-End Verification and PowerShell Removal

**Files:**
- Delete: `scripts/01_extract_xic.ps1`
- Modify: `README.md`

- [ ] **Step 1: Run focused test suite**

```powershell
uv run pytest tests/test_config.py tests/test_signal_processing.py tests/test_neutral_loss.py tests/test_extractor.py tests/test_csv_to_excel.py tests/test_pipeline_worker.py tests/test_config_io.py tests/test_targets_section.py -v
```

Expected: all pass.

- [ ] **Step 2: Run coverage check**

```powershell
uv run pytest --cov=xic_extractor --cov=scripts.csv_to_excel --cov=gui --cov-report=term-missing
```

Expected: overall coverage >= 80%; `signal_processing.py` >= 95%.

- [ ] **Step 3: Run CLI help and no-raw smoke**

```powershell
uv run python -m scripts.run_extraction --help
```

Expected: exits 0.

- [ ] **Step 4: Run migration validation**

After the user designates acceptance `.raw` files:

```powershell
uv run python scripts/validate_migration.py --strict
```

Expected: exits 0, or failures are documented as algorithmic improvements with user sign-off.

- [ ] **Step 5: Delete PowerShell extraction script**

Only after Task 11 Step 4 passes or receives explicit user sign-off:

```powershell
git rm scripts/01_extract_xic.ps1
```

- [ ] **Step 6: Update user-facing docs**

Update `README.md` to document:

- the new `xic-extractor-cli` command and `uv run python -m scripts.run_extraction` fallback.
- the canonical `settings.csv` schema.
- the new Area, PeakStart, PeakEnd, `NL_FAIL`, `NO_MS2`, and Diagnostics outputs.
- the quantitative meaning of each metric: `Area` is the primary quantitation metric; `Int` is raw apex intensity; `PeakStart` and `PeakEnd` are diagnostic boundaries.
- common run-time errors in user language: missing data folder, missing Xcalibur DLL folder, missing .NET/pythonnet runtime, unreadable `.raw` file.
- that `scripts/01_extract_xic.ps1` is no longer the supported extraction entry point.

- [ ] **Step 7: Search for stale references**

```powershell
rg -n "01_extract_xic|smooth_points|smooth_sigma|_parse_summary|subprocess.Popen|Mean Int" .
```

Expected: no stale production references, except migration docs/specs where historical references are intentional.

- [ ] **Step 8: Final review**

Review:

- correctness against the source spec.
- regression risk in GUI first-run settings migration.
- security risk from external file paths and DLL loading.
- test gaps around real Thermo DLL behavior.
- unnecessary complexity or duplicated parsing.

- [ ] **Step 9: Final commit**

```powershell
git add -A
git commit -m "refactor: replace powershell extraction with python area pipeline"
```

---

## Acceptance Checklist

- [ ] `xic_extractor.config.load_config()` is the single strict config loader for CLI and GUI runs.
- [ ] `SettingsSection.load()` can migrate legacy settings without requiring valid `data_dir`/`dll_dir`.
- [ ] GUI first-run migration persists canonical settings back to `settings.csv`.
- [ ] Signal processing returns explicit failure statuses and never throws for empty/short/noisy windows.
- [ ] Area is integrated from raw intensity over scipy peak boundaries.
- [ ] Raw apex intensity is written to production CSV.
- [ ] Smoothed apex intensity remains available in validation artifacts but is not written to main CSV.
- [ ] NL output supports `OK`, `WARN_*`, `NL_FAIL`, and `NO_MS2`.
- [ ] `xic_results.csv` has no dead `_NL` column for no-NL targets.
- [ ] `xic_diagnostics.csv` records all non-OK peak/NL/file issues.
- [ ] Excel has Data, Summary, and Diagnostics sheets.
- [ ] Workbooks with diagnostics rows save `Diagnostics` as the active sheet.
- [ ] Excel output treats filename/label text as literal text, preventing formula injection without changing normal display.
- [ ] GUI worker no longer launches PowerShell or parses stdout.
- [ ] GUI worker receives `_ROOT / "config"` and never reads bundled read-only settings in frozen mode.
- [ ] Runtime preflight reports missing pythonnet/.NET/Thermo DLL problems as actionable user messages, not raw tracebacks.
- [ ] Thermo DLL loading uses explicit expected filenames under resolved `dll_dir`, with no cwd/PATH fallback.
- [ ] CI shared workflow/action references are pinned to reviewed tags or commit SHAs.
- [ ] CLI and GUI share identical runtime parameters via `settings.csv`.
- [ ] Tests pass with no real Thermo DLLs.
- [ ] Migration validation on real `.raw` files passes automatically, or maintainer-only override evidence is explicitly provided with `--allow-overrides`.
- [ ] Routine GUI users never need to review migration FAIL sheets or fill sign-off fields.

---

## Rollback Plan

If the Python pipeline fails migration validation:

1. Keep `scripts/01_extract_xic.ps1` in place.
2. Leave GUI worker on the old subprocess path until the failing module is fixed.
3. Use `scripts/validate_migration.py` FAIL sheet to isolate whether drift is from smoothing, peak selection, area boundary, or NL classification.
4. Fix the smallest responsible module and rerun focused tests before rerunning full migration validation.

If `pythonnet` causes GUI instability:

1. Preserve the `raw_reader.open_raw()` interface.
2. Move Thermo DLL calls behind a child-process backend.
3. Keep `extractor.run()` and downstream CSV/Excel/GUI APIs unchanged.

---

## Notes for Future Enhancements

Out of scope for this implementation:

- per-target prominence overrides.
- baseline correction.
- peak asymmetry/tailing metrics.
- S/N ratio.
- peak overlay plots.
- runtime smoothing method toggle.
- PyInstaller packaging validation.
