# Design: Area Support & Full-Python Architecture

**Date:** 2026-04-13
**Branch:** `feat/area-support` (via `git worktree`)
**Status:** Approved (pending user review of spec document)

---

## Overview

This spec covers two coordinated changes to the XIC Extractor:

1. **Area integration** — record peak area (via trapezoidal integration over scipy-detected peak boundaries) alongside existing RT and apex intensity. Area is the canonical quantitative metric for LC-MS and is more robust than apex intensity against smoothing parameters.
2. **Full-Python architecture** — replace the PowerShell extraction script (`scripts/01_extract_xic.ps1`) with a Python package using `pythonnet` to call the Thermo `.NET` DLLs directly. This removes the dual-language split, enables unit testing of signal processing, and opens access to the scipy ecosystem (`savgol_filter`, `find_peaks`, `peak_widths`).

The two changes are bundled because: (a) scipy is Python-only, so adding `find_peaks`/`peak_widths`-based peak detection forces the architecture move; (b) peak detection and area integration share the same processing pipeline — separating them would mean refactoring the same code twice.

**Development strategy:** implement on a separate `git worktree`. The main branch retains the current Gaussian + PS1 architecture during development, providing a known-good reference for validation. Merge only after comparing outputs on real `.raw` files.

**Non-goals:**
- PyInstaller packaging validation (deferred; functional correctness first, per user direction)
- Per-target prominence override (recorded as a known future enhancement)
- Runtime smoothing method toggle (eliminated by worktree development strategy)

---

## 1. Module Structure

```
xic_extractor/                   # NEW Python package (repo root)
├── __init__.py
├── config.py                    # Typed config loading + schema validation
├── raw_reader.py                # pythonnet wrapper for Thermo DLLs
├── signal_processing.py         # scipy-based smoothing + peak detection + integration
├── neutral_loss.py              # MS2 NL confirmation (4-state output)
└── extractor.py                 # Orchestrator: loops over (file, target), returns results

scripts/
├── 01_extract_xic.ps1           # REMOVED
├── run_extraction.py            # NEW: CLI entry point
└── csv_to_excel.py              # MODIFIED: new columns, β summary, Diagnostics sheet

gui/workers/
└── pipeline_worker.py           # REFACTOR: call extractor.run() directly (no subprocess)

tests/
├── test_signal_processing.py    # NEW — highest priority (synthetic signal validation)
├── test_raw_reader.py           # NEW — mock-based
├── test_neutral_loss.py         # NEW
├── test_extractor.py            # NEW — integration with mock raw_reader
├── test_config.py               # NEW — schema validation
├── test_csv_to_excel.py         # UPDATED — new columns, 4-state NL, β summary
├── test_pipeline_worker.py      # UPDATED — mock extractor.run() (no stdout regex)
└── test_targets_section.py      # UNCHANGED
```

**Single execution path guarantee:** both `scripts/run_extraction.py` (CLI) and `gui/workers/pipeline_worker.py` (GUI) call **the same** `extractor.run(config, targets, ...)` function. CLI and GUI differ only in how they build the `ExtractionConfig` object. Once built, runtime behavior is identical.

---

## 2. Public Module Interfaces

### 2.1 `xic_extractor/config.py`

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class ExtractionConfig:
    data_dir: Path
    dll_dir: Path
    output_csv: Path                         # derived: base_dir / "output" / "xic_results.csv"
    diagnostics_csv: Path                    # derived: base_dir / "output" / "xic_diagnostics.csv"
    # Signal processing
    smooth_window: int                       # odd, >= 3
    smooth_polyorder: int                    # 2..4 typical, < smooth_window
    peak_rel_height: float                   # 0.5..0.99 (default 0.95)
    peak_min_prominence_ratio: float         # 0.01..0.50 (default 0.10)
    # NL
    ms2_precursor_tol_da: float              # default 0.5
    nl_min_intensity_ratio: float            # default 0.01
    # Summary behavior
    count_no_ms2_as_detected: bool = False   # default conservative

@dataclass(frozen=True)
class Target:
    label: str
    mz: float
    rt_min: float
    rt_max: float
    ppm_tol: float
    neutral_loss_da: float | None            # None => no NL check
    nl_ppm_warn: float | None
    nl_ppm_max: float | None
    is_istd: bool
    istd_pair: str                           # empty string => no pairing

class ConfigError(Exception):
    """Raised on schema/validation failures. Message includes file + row + column."""

def load_config(config_dir: Path) -> tuple[ExtractionConfig, list[Target]]:
    """Load + validate settings.csv and targets.csv. Raises ConfigError on bad data.

    Path derivation (single source of truth, used by both CLI and GUI):
      base_dir          = config_dir.parent
      output_dir        = base_dir / "output"
      output_csv        = output_dir / "xic_results.csv"
      diagnostics_csv   = output_dir / "xic_diagnostics.csv"

    `output_dir` is created via `mkdir(parents=True, exist_ok=True)` here (not in
    extractor.run), so callers can rely on the directory existing after load.
    """
```

**Validation rules enforced:**

*settings.csv (global):*
- `data_dir` and `dll_dir` must exist as directories.
- `smooth_window` must be odd and ≥ 3.
- `smooth_polyorder` must be in `[1, smooth_window - 1]`.
- `0.5 ≤ peak_rel_height ≤ 0.99`.
- `0.01 ≤ peak_min_prominence_ratio ≤ 0.50`.
- `ms2_precursor_tol_da > 0`.
- `0 < nl_min_intensity_ratio ≤ 1`.

*targets.csv (per row):*
- `label` non-empty; duplicate `label` values raise `ConfigError`.
- `mz > 0`.
- `ppm_tol > 0`.
- `rt_min < rt_max` (both finite, non-negative).
- `is_istd` is a boolean token (`true`/`false`, case-insensitive).
- Every non-empty `istd_pair` must reference an existing label whose `is_istd=True`.
- If `neutral_loss_da` is empty → `nl_ppm_warn`, `nl_ppm_max` are ignored (must be empty or will be warned and ignored).
- If `neutral_loss_da` is non-empty:
  - `neutral_loss_da > 0`.
  - `neutral_loss_da < mz` (expected_product = mz - neutral_loss_da must be positive).
  - `nl_ppm_warn` required, `> 0`.
  - `nl_ppm_max` required, `> 0`.
  - `nl_ppm_warn ≤ nl_ppm_max` (equal is allowed — collapses WARN band to empty but is semantically valid).

All rule violations raise `ConfigError` with file path, row number, column name, and offending value.

**Legacy settings migration:**

The migration logic is factored into a **pure function** that does NOT touch the filesystem or validate paths, so the GUI can call it at startup even when `data_dir` / `dll_dir` haven't been configured yet:

```python
def migrate_settings_dict(raw: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    """Rename legacy keys, drop removed keys, fill defaults for new keys.
    Returns (migrated_dict, warnings). No filesystem I/O, no path validation."""
```

Migration rules:
- `smooth_points` → renamed to `smooth_window` (value preserved).
- `smooth_sigma` → dropped (savgol has no sigma). Warning emitted.
- Any new key missing → filled from defaults, warning emitted.

`load_config()` orchestrates: reads raw CSV → calls `migrate_settings_dict` → applies **strict validation** (path existence, odd window, ranges, etc.) → constructs `ExtractionConfig`. It is only used when actually running extraction (CLI main, GUI `PipelineWorker.run`).

GUI `SettingsSection.load()` uses `migrate_settings_dict` **alone** (no strict validation), so users can open the Settings tab and see a fully-populated form even on first launch when `data_dir` is still the example placeholder. Strict validation happens when the user clicks "Run" and `PipelineWorker` calls `load_config`. Warnings from both layers surface through the `logging` module at WARNING level.

### 2.2 `xic_extractor/raw_reader.py`

```python
class RawReaderError(Exception): ...

class RawFileHandle:
    """Context manager — ensures .NET Dispose() is always called."""
    def __enter__(self) -> "RawFileHandle": ...
    def __exit__(self, *args) -> None: ...

    def extract_xic(
        self, mz: float, rt_min: float, rt_max: float, ppm_tol: float
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return (rt_array, intensity_array). Empty arrays mean no signal in window."""

    def iter_ms2_scans(
        self, rt_min: float, rt_max: float
    ) -> Iterator["Ms2ScanEvent"]:
        """Yield one Ms2ScanEvent per MS2 scan in [rt_min, rt_max].
        Parse errors are reported as events (not silently swallowed) so callers can
        accurately count valid vs errored scans."""

@dataclass(frozen=True)
class Ms2ScanEvent:
    """Either a successfully parsed scan or a parse error. Exactly one field is set."""
    scan: Ms2Scan | None                 # populated on success
    parse_error: str | None              # populated on failure (human-readable detail)
    scan_number: int                     # always populated (for logging)

@dataclass(frozen=True)
class Ms2Scan:
    scan_number: int
    precursor_mz: float
    masses: np.ndarray
    intensities: np.ndarray
    base_peak: float         # max(intensities); 0.0 when spectrum is empty or all-zero

def open_raw(path: Path, dll_dir: Path) -> RawFileHandle:
    """Lazy-load Thermo DLLs (via pythonnet). Raises RawReaderError on failure."""
```

**Design notes:**
- `clr.AddReference()` happens on first `open_raw` call, not at module import. This lets `tests/test_raw_reader.py` import the module on machines without the DLLs (mocking the .NET surface).
- `RawFileHandle.__exit__` calls `Dispose()` on the underlying .NET object; `try/finally` equivalent to the PS1 code.

### 2.3 `xic_extractor/signal_processing.py`

```python
from typing import Literal

@dataclass(frozen=True)
class PeakResult:
    rt: float                # apex RT (from smoothed argmax position)
    intensity: float         # RAW intensity at apex position (written to xic_results.csv)
    intensity_smoothed: float  # SMOOTHED intensity at apex position (validation only — NOT in main CSV)
    area: float              # trapezoidal integral over RAW intensities in [peak_start, peak_end]
    peak_start: float        # RT at left boundary (from peak_widths)
    peak_end: float          # RT at right boundary

@dataclass(frozen=True)
class PeakDetectionResult:
    """Wraps find_peak_and_area output so failure modes are preserved for Diagnostics."""
    status: Literal["OK", "NO_SIGNAL", "WINDOW_TOO_SHORT", "PEAK_NOT_FOUND"]
    peak: PeakResult | None              # populated iff status == "OK"
    n_points: int                        # number of XIC points inspected (for diagnostic context)
    max_smoothed: float | None           # max of smoothed signal (for PEAK_NOT_FOUND diagnostics); None when WINDOW_TOO_SHORT
    n_prominent_peaks: int               # number of peaks returned by find_peaks AFTER the prominence filter (scipy find_peaks applies prominence in-call); 0 if detection did not reach step 5

def find_peak_and_area(
    rt: np.ndarray,
    intensity: np.ndarray,
    config: ExtractionConfig,
) -> PeakDetectionResult:
    """
    B+C hybrid strategy; always returns a PeakDetectionResult (never None).

    1. If len(intensity) == 0:
         → PeakDetectionResult(status="NO_SIGNAL", peak=None, n_points=0, ...)
    2. If len(intensity) < smooth_window:
         → PeakDetectionResult(status="WINDOW_TOO_SHORT", peak=None, n_points=len(intensity), ...)
    3. Smooth via scipy.signal.savgol_filter(intensity, smooth_window, smooth_polyorder).
    4. apex_hint = max(smoothed). If apex_hint <= 0:
         → PeakDetectionResult(status="NO_SIGNAL", peak=None, max_smoothed=apex_hint, ...)
    5. peaks, _ = find_peaks(smoothed, prominence=apex_hint * peak_min_prominence_ratio).
    6. If len(peaks) == 0:
         → PeakDetectionResult(status="PEAK_NOT_FOUND", peak=None,
                               max_smoothed=apex_hint, n_prominent_peaks=0, ...)
    7. best_idx = peaks[argmax(smoothed[peaks])]   # highest peak wins
    8. widths = peak_widths(smoothed, [best_idx], rel_height=peak_rel_height)
    9. left = floor(widths[2][0]); right = ceil(widths[3][0]) + 1
    10. Clamp: left = max(0, left); right = min(len(rt), right)
    11. area = trapezoid(intensity[left:right], rt[left:right]) * 60  # RAW intensity; ×60 converts counts·min → counts·sec
    12. peak = PeakResult(rt=rt[best_idx], intensity=intensity[best_idx],
                         intensity_smoothed=smoothed[best_idx], area=area,
                         peak_start=rt[left], peak_end=rt[right - 1])
        → PeakDetectionResult(status="OK", peak=peak, n_prominent_peaks=len(peaks), ...)
    """
```

**Failure taxonomy explicitly preserved in the return type.** Callers can write a simple mapping from `status` to the Diagnostics sheet's `Issue` column without guessing.

**Key algorithmic decisions (rationale embedded):**
- Apex intensity uses **raw** array, not smoothed, so Excel values match what users see in Xcalibur at the apex scan.
- Area integration uses **raw** intensity — area is conservative under integration; smoothed would underestimate.
- **Area unit is `counts·seconds`**: Thermo's `GetChromatogramData` returns rt in minutes, so `trapezoid(intensity, rt)` natively produces `counts·minutes`. We multiply by 60 so area matches Xcalibur / MassHunter / manual-integration convention (chemists otherwise see numbers ~60× too small and area < height, which is physically impossible).
- Smoothed array is used only for detection (peak finding) and boundary (peak_widths), never for the final quantitative numbers.
- Multi-peak selection: highest peak wins. Rationale: `rt_min/rt_max` windows are already user-set; within the window the strongest signal is the target. If RT has drifted significantly, picking the strongest makes the anomaly visible rather than systematically picking wrong peaks.

### 2.4 `xic_extractor/neutral_loss.py`

```python
from typing import Literal

# Diagnostic search window: wider than nl_ppm_max so NL_FAIL can report how close
# the nearest product ion was. Set to max(3 × nl_ppm_max, 500 ppm) — wide enough
# to record meaningful diagnostics but narrow enough to avoid matching unrelated
# fragments in crowded MS2 spectra.
NL_DIAGNOSTIC_PPM_FLOOR = 500.0

@dataclass(frozen=True)
class NLResult:
    status: Literal["OK", "WARN", "NL_FAIL", "NO_MS2"]
    best_ppm: float | None       # Best ppm found within the DIAGNOSTIC window.
                                 #   OK:      best_ppm <= nl_ppm_warn
                                 #   WARN:    nl_ppm_warn < best_ppm <= nl_ppm_max
                                 #   NL_FAIL: best_ppm > nl_ppm_max, OR None if nothing
                                 #            found even in the diagnostic window
                                 #   NO_MS2:  None (no matching MS2 scan to search in)
    valid_ms2_scan_count: int    # MS2 scans successfully parsed + yielded in [rt_min, rt_max].
                                 # Scans that raised parse errors inside raw_reader are NOT
                                 # counted here — they surface as DEBUG log entries, and
                                 # the parse_error count is reported separately (see below).
    parse_error_count: int       # MS2 scans in window that raw_reader skipped due to parse
                                 # errors. Typically 0. Non-zero values indicate data quality
                                 # issues and are included verbatim in the Diagnostics reason.
    matched_scan_count: int      # Valid MS2 scans whose precursor matched within ms2_precursor_tol_da.

    def to_token(self) -> str:
        """CSV serialization of status only:
        'OK' | 'WARN_12.3ppm' | 'NL_FAIL' | 'NO_MS2'
        The numeric best_ppm is written into xic_diagnostics.csv, not the main CSV."""

def check_nl(
    raw: RawFileHandle,
    precursor_mz: float,
    rt_min: float,
    rt_max: float,
    neutral_loss_da: float,
    nl_ppm_warn: float,
    nl_ppm_max: float,
    ms2_precursor_tol_da: float,
    nl_min_intensity_ratio: float,
) -> NLResult:
    """
    Algorithm (updated to preserve diagnostic ppm for NL_FAIL):

    diagnostic_ppm = max(3 * nl_ppm_max, NL_DIAGNOSTIC_PPM_FLOOR)
    expected_product = precursor_mz - neutral_loss_da
    best_ppm = None
    valid_ms2_scan_count = 0
    parse_error_count = 0
    matched_scan_count = 0

    1. Iterate Ms2ScanEvents in [rt_min, rt_max].
       - If event.parse_error is set: parse_error_count += 1; log at DEBUG; continue.
       - Else: valid_ms2_scan_count += 1; scan = event.scan.
    2. For each valid scan: if |scan.precursor_mz - precursor_mz| > ms2_precursor_tol_da, skip.
    3. For matching scans: matched_scan_count += 1.
    4. In matching scans, consider only product ions whose intensity
       >= scan.base_peak * nl_min_intensity_ratio.
       - If scan.base_peak <= 0 (empty or all-zero spectrum), treat as if no product
         ions passed the intensity filter (contributes nothing to best_ppm).
    5. Find the product ion nearest to expected_product (by |delta_mz|) among the
       intensity-filtered ions. Compute its ppm = |delta_mz| / expected_product * 1e6.
    6. If ppm <= diagnostic_ppm and (best_ppm is None or ppm < best_ppm): best_ppm = ppm.
    7. After iterating all events, classify:
       - matched_scan_count == 0               → status="NO_MS2",  best_ppm=None
       - best_ppm is None                      → status="NL_FAIL", best_ppm=None
       - best_ppm > nl_ppm_max                 → status="NL_FAIL", best_ppm=actual
       - nl_ppm_warn < best_ppm <= nl_ppm_max  → status="WARN"
       - best_ppm <= nl_ppm_warn               → status="OK"
    """
```

**Behavioral changes from current PS1 implementation:**
- NL status split from 3 categories (`OK`/`WARN_*`/`ND`) to 4 (`OK`/`WARN_*`/`NL_FAIL`/`NO_MS2`). `ND` is eliminated in favor of the two more specific states.
- Product ion filter adds **intensity floor** (`nl_min_intensity_ratio`) — rejects noise being counted as confirmed NL.
- **Diagnostic search window (`3 × nl_ppm_max` or 500 ppm, whichever larger) is wider than the classification window (`nl_ppm_max`)**, so `NL_FAIL.best_ppm` can report how close the nearest candidate product was. This closes the spec-algorithm contradiction where NL_FAIL's best_ppm was previously defined as impossible.
- Single-scan parse errors are caught and the scan is skipped; only total absence of matching scans returns `NO_MS2`.

### 2.5 `xic_extractor/extractor.py`

```python
from typing import Callable, Literal

@dataclass(frozen=True)
class DiagnosticRecord:
    """One row in xic_diagnostics.csv. Issued whenever a (sample, target)
    produces a non-OK result, or when a file-level error occurs."""
    sample_name: str
    target_label: str                       # empty string for file-level errors
    issue: Literal[
        "PEAK_NOT_FOUND", "NO_SIGNAL", "WINDOW_TOO_SHORT",
        "NL_FAIL", "NO_MS2", "FILE_ERROR",
    ]
    reason: str                             # human-readable detail with numbers

@dataclass(frozen=True)
class ExtractionResult:
    peak_result: PeakDetectionResult        # always present (even on NO_SIGNAL etc.)
    nl: NLResult | None                     # None iff target has no neutral_loss_da

@dataclass
class FileResult:
    sample_name: str
    results: dict[str, ExtractionResult]    # target_label → ExtractionResult
    error: str | None = None                # file-level error; if set, results is empty

@dataclass
class RunOutput:
    """Structured return value of extractor.run(). Mirrors the two CSVs written."""
    file_results: list[FileResult]
    diagnostics: list[DiagnosticRecord]

def run(
    config: ExtractionConfig,
    targets: list[Target],
    progress_callback: Callable[[int, int, str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> RunOutput:
    """
    Main entry point. Iterates *.raw files in config.data_dir, processes each target,
    calls progress_callback(current, total, filename) after each file, and checks
    should_stop() between files. On stop, returns already-processed results (graceful).

    Side effects (written regardless of whether caller consumes the return value):
    - config.output_csv          (xic_results.csv — main, token-based)
    - config.diagnostics_csv     (xic_diagnostics.csv — structured issue detail)

    Both paths resolved in ExtractionConfig (see §2.1). Directories are auto-created.
    """
```

**Why two CSVs:**
- `xic_results.csv` is the **main table**, one row per sample, columns per target. Keeps existing downstream workflows (GUI Excel generation, user scripts) readable.
- `xic_diagnostics.csv` is **long-format** (one row per issue), containing the structured reasons and numeric details (best_ppm, scan counts, etc.) that would otherwise balloon the main CSV.
- `csv_to_excel.py` reads **both** CSVs to populate Data sheet + Summary + new Diagnostics sheet.

**Mapping from internal results to diagnostic rows:**

| Condition | issue | reason example |
|-----------|-------|----------------|
| `peak_result.status == "NO_SIGNAL"` | `NO_SIGNAL` | `"XIC empty in window [8.0, 10.0] for m/z 258.1085 ± 20 ppm"` |
| `peak_result.status == "WINDOW_TOO_SHORT"` | `WINDOW_TOO_SHORT` | `"Only 7 scans in window; savgol requires >= 15"` |
| `peak_result.status == "PEAK_NOT_FOUND"` | `PEAK_NOT_FOUND` | `"No peak met prominence >= 10% of max smoothed (max=1234)"` |
| `nl.status == "NL_FAIL"` with best_ppm | `NL_FAIL` | `"Precursor 258.1085 triggered 3 MS2 scans; best NL product 78.4 ppm (limit 50 ppm)"` |
| `nl.status == "NL_FAIL"` no best_ppm | `NL_FAIL` | `"Precursor 258.1085 triggered 3 MS2 scans; no product within 500 ppm diagnostic window"` |
| `nl.status == "NO_MS2"` | `NO_MS2` | `"No MS2 scan targeting precursor 258.1085 ± 0.5 Da within RT [8.0, 10.0]; 42 valid MS2 scans in window (2 parse errors)"` |
| `FileResult.error` set | `FILE_ERROR` | `"Failed to open .raw: COMException: file locked"` (target_label = empty) |

Each mapping lives in `extractor._build_diagnostic()` (small pure function, unit-testable).

---

## 3. CSV Output Format

### 3.1 Columns per target

Targets **with** `neutral_loss_da` emit 6 columns:

```
{label}_RT  {label}_Int  {label}_Area  {label}_PeakStart  {label}_PeakEnd  {label}_NL
```

Targets **without** `neutral_loss_da` (i.e. `neutral_loss_da` cell is empty in `targets.csv`) emit 5 columns — the `_NL` column is **omitted entirely**, preserving the current PS1 behavior:

```
{label}_RT  {label}_Int  {label}_Area  {label}_PeakStart  {label}_PeakEnd
```

This keeps the CSV header self-describing (no dead `NO_CHECK` tokens) and matches how Summary's predicate already treats missing `nl_key` (§4.2). `csv_to_excel` builds columns per target by inspecting the target's `neutral_loss_da`; Diagnostics never emits `NL_FAIL`/`NO_MS2` rows for no-NL targets.

### 3.2 Value tokens

| Cell value | Meaning |
|------------|---------|
| Numeric (float) | Successfully detected |
| `ND` | No detection (peak not found OR no signal in window) |
| `ERROR` | File-level read error |
| `OK` | NL confirmed within `nl_ppm_warn` |
| `WARN_12.3ppm` | NL within `nl_ppm_warn` < x ≤ `nl_ppm_max` |
| `NL_FAIL` | MS2 triggered but no NL product found |
| `NO_MS2` | No MS2 scan in window matching precursor |

**Why `ND` is not further subdivided in CSV:** the distinction between "no signal" vs "signal but no peak" is only useful for debugging and would add an extra column per target (10 targets = 10 extra columns, doubling the sheet width). This detail lives in the new Diagnostics sheet instead.

### 3.3 Settings.csv new schema

```csv
key,value,description
data_dir,C:/your/data/folder,資料來源資料夾（換批次只改這裡）
dll_dir,C:\Xcalibur\system\programs,Xcalibur DLL 路徑（通常不需更改）
smooth_window,15,Savitzky-Golay 平滑視窗長度（必須為奇數，建議 9-21）
smooth_polyorder,3,Savitzky-Golay 多項式階數（通常 2-4）
peak_rel_height,0.95,Peak 邊界的相對高度（0.95 = 積分到 apex 的 5%，範圍 0.5-0.99）
peak_min_prominence_ratio,0.10,Peak prominence 至少為 apex 的比例（越低越寬容，0.05-0.20）
ms2_precursor_tol_da,0.5,MS2 precursor m/z 匹配視窗（Da，對應 DDA quadrupole 隔離寬度）
nl_min_intensity_ratio,0.01,NL product 強度至少為該 scan base peak 的比例（1% 排除 noise）
count_no_ms2_as_detected,false,是否將無 MS2 觸發的樣品算為偵測到（DDA 隨機性假陰性補救用）
```

---

## 4. Excel Output (`csv_to_excel.py`)

### 4.0 Entry point signature

The module's public entry point gains an overload that accepts `(ExtractionConfig, list[Target])` so it does not re-parse `settings.csv` (avoiding divergence from the extractor). The original `run(base_dir)` signature is kept **by reusing the same name** — true backward compatibility for existing callers:

```python
from typing import overload

@overload
def run(config: ExtractionConfig, targets: list[Target]) -> Path: ...
@overload
def run(base_dir: Path) -> Path: ...

def run(
    config_or_base_dir: ExtractionConfig | Path,
    targets: list[Target] | None = None,
) -> Path:
    """
    Two calling conventions:
      run(base_dir)              — legacy; internally calls load_config then recurses.
      run(config, targets)       — preferred; no re-parse of settings.csv.
    Returns the xlsx path. Uses config.count_no_ms2_as_detected for Summary logic.
    """
    if isinstance(config_or_base_dir, Path):
        config, targets = load_config(config_or_base_dir / "config")
        return run(config, targets)
    assert targets is not None, "targets required when config is passed"
    ...  # actual implementation
```

Existing call sites (`tests/test_csv_to_excel.py:159`, `gui/workers/pipeline_worker.py:97`, any user scripts) that call `run(base_dir)` keep working unchanged; new code passes `(config, targets)`. No rename, no alias — the dispatch is done via runtime `isinstance` on the first arg, which is small, local, and testable.

### 4.1 Data sheet changes

- Column metadata types extended: `ms1_rt`, `ms1_int`, `ms1_area` (new), `ms1_peak_start` (new, diagnostic styling), `ms1_peak_end` (new, diagnostic styling), `ms2_nl`.
- `ms1_peak_start` / `ms1_peak_end` use a **dimmer palette variant** (e.g. blend `palette.light` with 50% white) to visually demote them as diagnostic-only fields.
- NL cell display handles 4 tokens:
  - `OK` → "✓" on green (`C8E6C9`)
  - `WARN_*` → "⚠ Xppm" on yellow (`FFF9C4`)
  - `NL_FAIL` → "✗" on red (`FFCDD2`)
  - `NO_MS2` → "—" on grey (`E0E0E0`)
  - `ERROR` → "ERROR" on orange (`FF7043`)

### 4.2 Summary sheet changes (option β)

**Removed:** `Mean Int` row.
**Added:** `Median Area` row, `Area / ISTD ratio` row.
**Modified:** `NL ✓/⚠/✗` row → `NL ✓/⚠/✗/—` showing 4 counts.
**Retained (explicit — was in current Summary, stays):** `RT Δ vs ISTD (%)` row. The isotope-pair RT drift metric is unchanged in logic; it just reads from the new `_RT` column (same name as before).

Detection predicate becomes:

```python
def _is_detected(row, rt_key, area_key, nl_key, count_no_ms2) -> bool:
    area = _safe_float(row.get(area_key, ""))
    if area is None or area <= 0:
        return False
    if nl_key:
        nl = row.get(nl_key, "")
        if nl == "OK" or nl.startswith("WARN_"):
            return True
        if nl == "NO_MS2" and count_no_ms2:
            return True
        return False
    return True
```

**`count_no_ms2_as_detected` rationale (embedded in code comments):** DDA is a stochastic sampling method. A precursor can escape TopN selection even when the compound is present, producing false negatives at the MS2 level while MS1 clearly shows the peak. Defaulting to `False` keeps the Summary scientifically conservative; setting `True` is appropriate when investigating borderline cases where MS1 peak shape and RT strongly suggest the compound despite missing MS2 confirmation.

**`Area / ISTD ratio` calculation:**

The detection predicate for ratio eligibility is evaluated **per-target independently**, because NL may be configured on either side, both sides, or neither. A target (analyte or ISTD) is considered "usable for ratio" in a sample when `_is_detected(row, rt_key, area_key, nl_key, count_no_ms2)` returns `True`. If a target has no NL (`neutral_loss_da` empty), `nl_key` is `None`, so the predicate collapses to "area is a positive number" (see §4.2 predicate definition — the `if nl_key:` branch is skipped).

```python
# For each analyte target with non-empty istd_pair:
#   Let ISTD target = targets[istd_pair]   (validated at load_config time)
#   For each sample:
#     if not _is_detected(sample, analyte):   continue   # honors NL if analyte has NL
#     if not _is_detected(sample, istd):      continue   # honors NL if ISTD has NL
#     if istd.area <= 0:                      continue
#     ratio = analyte.area / istd.area
#   Display: "mean±SD (n=count)"  or  "—" if no valid pairs.
```

Four supported pairing shapes, all handled uniformly by the predicate:

| Analyte has NL? | ISTD has NL? | Detection requirement |
|-----------------|--------------|------------------------|
| yes | yes | Both pass NL (OK/WARN, or NO_MS2 if `count_no_ms2_as_detected`) AND both have positive area |
| yes | no  | Analyte passes NL; ISTD just needs positive area |
| no  | yes | Analyte just needs positive area; ISTD passes NL |
| no  | no  | Both need positive area only |

**Rationale for the symmetric predicate:** treating NL absence as "no MS2 check configured" (not "MS2 required but missing") keeps the ratio calculation scientifically honest — we never silently exclude a sample because a column the user didn't configure MS2 for. The `count_no_ms2_as_detected` toggle propagates through both sides of the ratio symmetrically.

### 4.3 New Diagnostics sheet

Third worksheet `Diagnostics`. Only lists problematic (sample, target) pairs.

| Column | Content |
|--------|---------|
| SampleName | sample identifier (or `(file-level)` for file errors) |
| Target | target label (or `—` for file-level errors) |
| Issue | one of: `PEAK_NOT_FOUND`, `NO_SIGNAL`, `WINDOW_TOO_SHORT`, `NL_FAIL`, `NO_MS2`, `FILE_ERROR` |
| Reason | human-readable detail with numbers (best ppm, scan count, etc.) |

Colored by issue type (red/yellow/grey matching Data sheet conventions). Uses Excel auto-filter so users can sort/filter by issue type.

**Rule of thumb for what lands in Diagnostics:** any (sample, target) where the Data sheet shows `ND`, `NL_FAIL`, or `NO_MS2` generates one row; any file-level failure generates one row with `Target = (file-level)`.

---

## 5. GUI Integration

### 5.1 `pipeline_worker.py` refactor

**Removed:**
- `subprocess.Popen` for PowerShell.
- `_parse_summary` stdout regex parsing (replaced by structured data from `extractor.run()`).

**New structure:**

```python
class PipelineWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(dict)           # summary dict (structured, not parsed)
    error = pyqtSignal(str)

    def run(self) -> None:
        try:
            config, targets = load_config(self._config_dir)
            # extraction phase (records go to xic_results.csv + xic_diagnostics.csv)
            run_output: RunOutput = extractor.run(
                config, targets,
                progress_callback=self._emit_progress,
                should_stop=self.isInterruptionRequested,
            )
            if self.isInterruptionRequested():
                return
            # excel phase — shares the same config object; no re-parse
            excel_path = csv_to_excel.run(config, targets)
            # build summary dict for ResultsSection (uses both file_results and diagnostics)
            summary = build_summary(
                run_output.file_results, run_output.diagnostics, excel_path
            )
            self.finished.emit(summary)
        except ConfigError as e:
            self.error.emit(f"設定檔錯誤：{e}")
        except RawReaderError as e:
            self.error.emit(f"Raw file 讀取失敗：{e}")
        except Exception as e:
            self.error.emit(str(e))
```

### 5.2 Summary dict new structure (passed to `ResultsSection`)

```python
summary = {
    "total_files": int,
    "excel_path": str,
    "targets": [
        {
            "label": str,
            "detected": int,              # OK + WARN (+ NO_MS2 if count_no_ms2_as_detected)
            "total": int,
            "nl_ok": int,
            "nl_warn": int,
            "nl_fail": int,
            "nl_no_ms2": int,
            "median_area": float | None,
        },
        ...
    ],
    "istd_warnings": [
        {"label": str, "detected": int, "total": int},
        ...
    ],
    "diagnostics_count": int,             # total rows in Diagnostics sheet
}
```

### 5.3 `ResultsSection` card changes

- Main number: detected count (honors `count_no_ms2_as_detected`).
- Subtitle: `✓{nl_ok} ⚠{nl_warn} ✗{nl_fail} —{nl_no_ms2}`.
- New "Diagnostics" card showing total issue count; clicking `開啟 Excel` opens to Diagnostics sheet when count > 0 (otherwise opens Data sheet as before).

### 5.4 `gui/config_io.py` migration and settings schema sync

The GUI already uses `config_io` as the only read/write path for `settings.csv`; `load_config` (§2.1) only reads. This keeps writes in one place. Required changes:

1. **`config/settings.example.csv`** — update to the full 9-key schema in §3.3 (adds `smooth_window` replacing `smooth_points`; adds `smooth_polyorder`, `peak_rel_height`, `peak_min_prominence_ratio`, `ms2_precursor_tol_da`, `nl_min_intensity_ratio`, `count_no_ms2_as_detected`; drops `smooth_sigma`). Bundled into PyInstaller via existing `_BUNDLE` path.

2. **`config_io.read_settings()`** — unchanged signature, but callers (GUI `SettingsSection`) must tolerate the new keys. `read_settings` is a raw dict reader; it's `load_config()` that applies the legacy migration and fills defaults.

3. **`config_io.write_settings()`** — no logic change needed (existing two-sequential-`with` structure is correct). Extend `tests/test_config_io.py` to confirm that `description` columns for migrated keys (e.g. `smooth_window` replacing `smooth_points`) are preserved or backfilled with the new defaults rather than left empty.

4. **`gui/sections/settings_section.py`** — add input widgets for the 6 new keys, grouped under "Signal processing" and "MS2 / NL". Validation (numeric range, odd window) mirrors `ConfigError` rules so the GUI rejects bad values before they hit `load_config`.

5. **First-run migration for existing users' `config/settings.csv`** — when a user upgrades, their `settings.csv` may still have `smooth_points` / `smooth_sigma` and lack the new keys. Strategy (depends on the `migrate_settings_dict` split in §2.1):
   - GUI's `SettingsSection.load()` calls `read_settings()` then `migrate_settings_dict()` — **strict path validation is skipped here**, so the form still loads when the user hasn't yet pointed `data_dir` at their own folder. Warnings shown in a non-blocking status label.
   - After the migrated dict is populated into the form, `SettingsSection` calls `write_settings()` to persist the canonical schema to disk. Legacy keys are rewritten on first GUI open; subsequent CLI runs see the canonical schema.
   - Strict validation happens only when the user clicks "Run"; `PipelineWorker` invokes `load_config` which raises `ConfigError` on bad paths/ranges. Error dialog surfaces the issue without corrupting `settings.csv`.

### 5.5 Stop behavior

- `QThread.requestInterruption()` is the canonical stop signal.
- `extractor.run()` checks `should_stop()` between files.
- Already-processed results are written to CSV on graceful stop (not discarded).

**Backward compatibility with existing GUI call site:** `gui/main_window.py:150` currently calls `self._worker.stop()`. The refactored `PipelineWorker` keeps `stop()` as a **thin wrapper** so `MainWindow` needs no change:

```python
class PipelineWorker(QThread):
    def stop(self) -> None:
        """Requests graceful interruption; processing halts between files."""
        self.requestInterruption()
```

No `subprocess.terminate` path is needed (subprocess is gone). The wrapper exists solely so existing callers continue to work without a coordinated edit to `MainWindow`.

---

## 6. CLI Entry Point (`scripts/run_extraction.py`)

```python
import argparse
from pathlib import Path
from xic_extractor.config import load_config
from xic_extractor.extractor import run as extractor_run
from scripts.csv_to_excel import run as csv_to_excel_run

def main() -> None:
    parser = argparse.ArgumentParser(description="Extract XIC apex + area + NL from Thermo .raw files.")
    parser.add_argument("--base-dir", type=Path, default=Path(__file__).resolve().parent.parent,
                        help="Root with config/ and output/ subdirectories")
    parser.add_argument("--skip-excel", action="store_true",
                        help="Skip xlsx generation (produce only CSV)")
    args = parser.parse_args()

    config, targets = load_config(args.base_dir / "config")
    run_output = extractor_run(
        config, targets,
        progress_callback=lambda i, n, name: print(f"  [{i:3}/{n}] {name}"),
    )
    print(f"Processed {len(run_output.file_results)} files, "
          f"{len(run_output.diagnostics)} diagnostic rows")
    if not args.skip_excel:
        csv_to_excel_run(config, targets)

if __name__ == "__main__":
    main()
```

**CLI/GUI parameter sync guarantee:** both CLI and GUI call `load_config(config_dir)`, which reads the same `settings.csv`. The `settings.csv` file is the single source of truth for runtime parameters. GUI's `config_io.write_settings()` updates this file; CLI has no write path (intentional — CLI is read-only w.r.t. configuration).

---

## 7. Error Handling

| Failure mode | Behavior |
|--------------|----------|
| `pythonnet` import fails | Fatal at startup (before processing). GUI shows dialog; CLI exits non-zero. |
| Thermo DLL load fails | Same as above. Message includes `dll_dir` path for user correction. |
| `settings.csv` / `targets.csv` invalid | Fatal at startup. `ConfigError` with file+row+column. |
| Single `.raw` file unreadable | Logged; row written with all columns = `ERROR`; processing continues. One Diagnostics row with `FILE_ERROR`. |
| Peak not found | Row: `ND` for RT/Int/Area/PeakStart/PeakEnd; NL independently evaluated. Diagnostics row with specific reason. |
| MS2 scan parse fails | `raw_reader` yields an `Ms2ScanEvent` with `parse_error` set; `check_nl` counts it in `parse_error_count`; logged at DEBUG level. Does not fail the target. Diagnostics reason includes the parse-error count for visibility. |
| GUI user hits Stop | Processing halts between files. Already-processed results written to CSV. No ERROR rows. |
| XIC too short for savgol | `PeakDetectionResult(status="WINDOW_TOO_SHORT", peak=None, ...)`. Row: `ND`. Diagnostics row with reason `"Only N scans in window; savgol requires >= smooth_window"`. |

**No silent failures:** every failure path either logs a WARN/ERROR entry, adds a Diagnostics row, or raises a typed exception. No path where a bad result gets written without trace.

### 7b. Process isolation risk (subprocess → in-process trade-off)

Removing `subprocess.Popen` means Thermo DLL faults now share the GUI process. Three realistic failure classes + mitigations:

| Risk | Mitigation (this spec) | Deferred mitigation |
|------|------------------------|---------------------|
| Thermo DLL managed exception (`COMException`, `IOException`, etc.) | Each file processed in a `try/except` in `extractor.run`; one bad file → `FILE_ERROR` row, loop continues. Extractor never exposes unhandled managed exceptions to Qt event loop. | — |
| Thermo DLL native crash (`SEHException`, segfault, stack corruption) | **Not catchable from Python.** Accepted as in-process risk for current scale. Rationale: (1) Thermo DLLs are widely used and crashes are rare in practice on well-formed `.raw` files; (2) moving to subprocess adds serialization/IPC overhead and complicates the interface. | If a native crash is observed in production, swap `raw_reader` backend to `multiprocessing.Process` worker. The context-manager interface makes the swap local to `raw_reader.py`. |
| DLL hang on malformed `.raw` | `PipelineWorker` runs in `QThread`; GUI remains responsive. User can hit Stop; `QThread.requestInterruption()` signals between-file cancellation (won't abort an in-progress DLL call, but no scan can hang indefinitely in normal Thermo DLL usage — documented known limitation). | Per-file timeout via `concurrent.futures.ProcessPoolExecutor` with `timeout` parameter, if hangs observed in production. |
| Memory leak in `.NET` interop across hundreds of files | `RawFileHandle.__exit__` enforces `Dispose()`. Explicit `gc.collect()` called every 50 files in `extractor.run` to reclaim CLR wrapper objects. | Move extraction to child process if leak is sustained. |

**Decision recorded:** in-process is acceptable for current scale (typically ≤ 100 `.raw` files per run). If user reports GUI crashes attributable to DLL faults, revisit with a subprocess-based `raw_reader` backend (interface is already a context manager, so the swap would be local).

---

## 8. Testing Strategy

### 8.1 Unit tests

**`tests/test_signal_processing.py` (highest priority, target ≥ 95% coverage)**

Synthetic Gaussian peaks with known ground-truth area (`height × width × √π`). Tolerance: area within 2%, RT within 0.01 min, intensity within 2%.

Critical test cases:
- Single clean peak in window
- Two peaks of different heights (assert highest wins)
- Pure noise (assert `status == "PEAK_NOT_FOUND"`)
- Signal shorter than smooth_window (assert `status == "WINDOW_TOO_SHORT"`, no exception)
- Flat-zero window (assert `status == "NO_SIGNAL"`)
- Peak near window edge
- Very narrow peak (fewer than polyorder+1 points on FWHM)
- Negative noise around baseline

**`tests/test_raw_reader.py`**

Mock-based. Patches `clr` and the .NET class tree. Validates:
- `open_raw` raises `RawReaderError` on DLL failure
- `extract_xic` returns empty arrays when underlying `ChromatogramData` is empty
- `iter_ms2_scans` yields only scans in the specified RT range
- `__exit__` calls `Dispose()`

**`tests/test_neutral_loss.py`**

Mock raw with synthetic MS2 scans. Validates all 4 states: `OK`, `WARN`, `NL_FAIL`, `NO_MS2`.

**`tests/test_config.py`**

Validates all `ConfigError` paths + legacy migration behavior.

### 8.2 Integration tests

**`tests/test_extractor.py`** — mock `raw_reader`, assert `extractor.run()` produces expected `FileResult` structure, respects `should_stop`, writes CSV correctly.

**`tests/test_pipeline_worker.py`** — mock `extractor.run()`, verify Qt signals fire with correct structured summary (no more stdout parsing).

**`tests/test_csv_to_excel.py`** — synthetic CSV rows with all 4 NL states + ERROR → verify Data sheet columns, Summary metrics (Median Area, Area/ISTD ratio), Diagnostics sheet population.

### 8.3 Migration validation (one-shot gate before worktree merge)

**Script:** `scripts/validate_migration.py` — runs old PS1 pipeline (on `master` via `git worktree`) and new Python pipeline (on `feat/area-support` worktree) against the same `.raw` files, writes `docs/superpowers/specs/2026-04-13-migration-validation.xlsx` as merge evidence. xlsx is chosen (over CSV) so the report can have multiple sheets (`Summary`, `PerTarget`, `FAIL`) and embed chromatogram screenshots inline when humans sign off on algorithmic improvements.

**Acceptance raw file set (required; any subset that covers all four cases):**

| Case | What it proves | Minimum files |
|------|----------------|---------------|
| Clean high-signal standards | Baseline agreement on apex / area / NL | 1 |
| Low-signal / near-noise endogenous | Prominence filter doesn't mistakenly reject real peaks | 1 |
| DDA sample where some targets have no MS2 | NO_MS2 vs ND categorization correct | 1 |
| Off-window / blank | Both pipelines return ND; no false positive areas | 1 |

User will designate the four files at validation time (paths saved into the script's config section). If the user cannot supply one of the cases, that row in the acceptance matrix is marked `SKIPPED — justification: ...` and the merge still requires the other three.

**Per-target pass thresholds (stricter than prior spec):**

| Metric | Threshold | Failure means |
|--------|-----------|---------------|
| `|RT_new − RT_old|` | median ≤ 0.003 min, max ≤ 0.010 min | Peak selection drift; investigate prominence / boundary logic |
| `Area_new / Int_old × 1/FWHM_proxy` sanity ratio | Within [0.5, 2.0] across targets (we don't have Area_old; we cross-check that new Area scales with old Int monotonically) | Integration window too wide/narrow |
| `Int_new_smoothed / Int_old` | median ∈ [0.95, 1.05], max deviation < 20% | Smoothing regression (savgol vs Gaussian impact at apex). **Must compare like-with-like:** old PS1 writes smoothed intensity (`01_extract_xic.ps1` line 102 takes argmax of smoothed), so validation requires the new pipeline to *also* expose a smoothed apex intensity in the validation report, even though the production CSV records raw intensity. |
| `Int_new_raw` (informational) | No threshold — reported so humans can see the raw-vs-smoothed delta and confirm it's consistent with Thermo's own "raw vs 15G" comparison in Xcalibur | N/A |
| NL status agreement | ≥ 95% when mapping: new `OK`→old `OK`, new `WARN_*`→old `WARN_*`, new `NL_FAIL`∪`NO_MS2`→old `ND` | NL thresholding regression |

**Failure protocol:**
1. Any target failing any threshold blocks merge.
2. Script prints the failing rows and writes them to the validation xlsx's `FAIL` sheet.
3. Investigator must either (a) fix the regression and re-run, or (b) document a justified algorithmic improvement (e.g., new pipeline correctly rejects a peak the old one wrongly accepted) with a chromatogram screenshot embedded in the `FAIL` sheet. Option (b) requires user sign-off recorded in the spec's merge commit message.
4. No merge commit is allowed until `validate_migration.py --strict` exits 0 OR the user signs off (b).

**Validation xlsx preserved** at `docs/superpowers/specs/2026-04-13-migration-validation.xlsx`; referenced from the merge commit as the evidence trail. Large raw artifacts (full chromatogram CSVs per target, screenshots too big to embed) live in a sibling `docs/superpowers/specs/2026-04-13-migration-artifacts/` directory, also committed.

### 8.4 Existing tests

| File | Action |
|------|--------|
| `tests/conftest.py` | Add fixtures for synthetic XIC and mock raw handle |
| `tests/test_config_io.py` | Keep; extend to verify new settings fields |
| `tests/test_targets_section.py` | Keep unchanged |
| `tests/test_csv_to_excel.py` | Major update (see above) |
| `tests/test_pipeline_worker.py` | Major update (see above) |

**Overall coverage target:** ≥ 80%, with `signal_processing.py` specifically ≥ 95%.

---

## 9. Implementation Order (for writing-plans reference)

The plan writer should consider phasing in this order to maintain testability throughout:

1. **Scaffold package + config module** — `xic_extractor/__init__.py`, `config.py`, `tests/test_config.py`. No .NET dependency yet. Verifies schema loading works end-to-end.
2. **Signal processing module** — `signal_processing.py` + comprehensive unit tests. The most algorithmically critical piece; validate with synthetic signals before integrating.
3. **Raw reader module (pythonnet integration)** — `raw_reader.py` + mock-based tests. Manual verification on one real `.raw` file to confirm DLL interop works.
4. **Neutral loss module** — `neutral_loss.py` + unit tests. Straightforward once raw_reader is in place.
5. **Extractor orchestrator + CLI** — `extractor.py`, `scripts/run_extraction.py`. First end-to-end runs; writes `xic_results.csv`.
6. **csv_to_excel updates** — new columns, new Summary, Diagnostics sheet. Tests updated.
7. **GUI worker refactor** — remove subprocess path, connect to `extractor.run()`. ResultsSection updates.
8. **Migration validation** — run `validate_migration.py` against real `.raw` files. Document findings.
9. **Delete `scripts/01_extract_xic.ps1`** and related dead code.
10. **Packaging verification** — deferred. Handle PyInstaller concerns only after functional acceptance.

---

## 9b. pyproject.toml changes

The new Python-only pipeline requires three additions and one package-discovery update:

```toml
[project]
dependencies = [
    "PyQt6>=6.6",
    "openpyxl>=3.1",
    "numpy>=1.26",          # NEW — XIC arrays, trapezoid integration
    "scipy>=1.11",          # NEW — savgol_filter, find_peaks, peak_widths
    "pythonnet>=3.0",       # NEW — Thermo .NET DLL interop (Windows)
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
]

[project.scripts]
xic-extractor     = "gui.main:main"
xic-extractor-cli = "scripts.run_extraction:main"   # NEW CLI entry

[tool.setuptools.packages.find]
include = ["gui*", "scripts*", "xic_extractor*"]    # add new package
exclude = ["tests*"]
```

**Install note for contributors:** `pythonnet` requires .NET 6+ runtime on Windows.
CI already runs on `[self-hosted, Windows, X64]` which has this. Linux CI (if any)
should skip tests tagged `requires_dotnet`. Add `pytest.mark.requires_dotnet` for
`test_raw_reader.py` (real-DLL paths only; mock-based tests stay unmarked).

Version pins justified:
- `numpy>=1.26` — matches pandas 2.x CoW era; `trapezoid` is stable.
- `scipy>=1.11` — `peak_widths` signature stabilized; savgol boundary handling correct.
- `pythonnet>=3.0` — 3.x is the actively maintained line; 2.x is legacy.

---

## 10. Known Future Enhancements (out of scope for this spec)

- Per-target prominence override in `targets.csv` (for handling weak endogenous signals alongside strong ISTDs).
- Peak asymmetry / tailing metric.
- Baseline correction (rolling ball, asymmetric least squares).
- Peak overlay plots per target (would benefit from persisting XIC points, currently in-memory only).
- S/N ratio column (requires baseline estimation).
- Swap smoothing method via config (`smoothing_method: savgol | gaussian`) — only if migration validation reveals unacceptable differences.
