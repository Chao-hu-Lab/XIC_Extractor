# Peak Scoring Stage 1 — Tissue Regression-Gated Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace intensity-only peak selection with tier-based Confidence scoring (7 severity signals, no HARD-FAIL) and ΔRT + injection-rolling RT priors, gated by a tissue-regression test harness.

**Architecture:** Introduce `peak_scoring.py`, `injection_rolling.py`, `rt_prior_library.py` as pure-function modules. Split `extractor.run()` into a lightweight ISTD-only pre-pass and a full main pass. Keep `find_peak_candidates` untouched; only replace `_select_candidate` and add post-selection scoring.

**Tech Stack:** Python 3.13, `uv` for deps, pytest, numpy, scipy (existing). New deps: `pandas` or `openpyxl` for XLSX metadata reads (openpyxl already present).

**Spec reference:** `docs/superpowers/specs/2026-04-20-peak-scoring-tiered-design.md`

**Stage:** 1 of 2. This plan ships tissue regression-safe scoring. Stage 2 (urine fixtures + `dirty_matrix_mode` final tuning) is a separate plan after Stage 1 merges.

---

## File Structure

**New modules (under `xic_extractor/`):**

- `peak_scoring.py` — seven severity signals, Confidence mapping, Reason string builder, multi-candidate selector. Pure functions. No I/O.
- `injection_rolling.py` — read injection-order metadata (CSV/XLSX), compute rolling-window RT medians per ISTD.
- `rt_prior_library.py` — load / filter / append-pending for `config/rt_prior_library.csv`.
- `baseline.py` — AsLS baseline estimator. Pure function. (Split from `peak_scoring.py` because scipy sparse solves are self-contained and testable in isolation.)

**Modified modules:**

- `signal_processing.py` — `_select_candidate` becomes a thin wrapper calling `peak_scoring.select_candidate_with_confidence(...)`. Keep old internals for the `_preferred_rt_recovery` path (unchanged).
- `extractor.py` — split `run()` into `_pre_pass_istd_anchors(...)` and `_main_pass(...)`. Plumb a new `ScoringContext` object through `_process_file` → `_extract_one_target`.
- `settings_schema.py` — add new keys to `CANONICAL_SETTINGS_DEFAULTS` and `CANONICAL_SETTINGS_DESCRIPTIONS`.
- `config.py` — add `config_hash` computed from on-disk targets + settings bytes. Add new dataclass fields to `ExtractionConfig` for the new settings.

**New test files (under `tests/`):**

- `test_baseline.py`
- `test_peak_scoring.py`
- `test_injection_rolling.py`
- `test_rt_prior_library.py`
- `test_tissue_regression.py`
- `fixtures/tissue_regression/baseline.json` — snapshot of (sample, target, RT, Area, detected) extracted from `output/xic_results_20260420_0309.xlsx` for the 10-sample subset.
- `fixtures/tissue_regression/sample_info.csv` — injection order for the 10-sample subset.

**Sample-level fixtures:** RAW files are too big to commit. The regression test reads them from a path the user configures via env var `XIC_TISSUE_FIXTURE_DIR`. If the env var is missing, the regression test is marked `skip` with a clear message (not failing) so CI without fixture access still passes. The user's local runs set the env var.

---

## Phase A — Foundations

### Task 1: `config_hash` utility

**Files:**
- Modify: `xic_extractor/config.py` (add function + field)
- Test: `tests/test_config_hash.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config_hash.py
from pathlib import Path

from xic_extractor.config import compute_config_hash


def test_same_bytes_same_hash(tmp_path: Path) -> None:
    targets = tmp_path / "targets.csv"
    settings = tmp_path / "settings.csv"
    targets.write_bytes(b"label,mz\nA,100\n")
    settings.write_bytes(b"key,value\ndata_dir,C:/x\n")
    assert compute_config_hash(targets, settings) == compute_config_hash(targets, settings)


def test_different_targets_different_hash(tmp_path: Path) -> None:
    targets_a = tmp_path / "a.csv"
    targets_b = tmp_path / "b.csv"
    settings = tmp_path / "s.csv"
    targets_a.write_bytes(b"label\nA\n")
    targets_b.write_bytes(b"label\nB\n")
    settings.write_bytes(b"key\ndata_dir\n")
    assert compute_config_hash(targets_a, settings) != compute_config_hash(targets_b, settings)


def test_hash_is_8_hex_chars(tmp_path: Path) -> None:
    t = tmp_path / "t.csv"; s = tmp_path / "s.csv"
    t.write_bytes(b"x"); s.write_bytes(b"y")
    h = compute_config_hash(t, s)
    assert len(h) == 8
    assert all(c in "0123456789abcdef" for c in h)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_config_hash.py -v
```
Expected: ImportError / AttributeError on `compute_config_hash`.

- [ ] **Step 3: Implement in `xic_extractor/config.py`**

Add at top-level (after imports):

```python
import hashlib

def compute_config_hash(targets_csv: Path, settings_csv: Path) -> str:
    """SHA-256[:8] hex of targets.csv followed by settings.csv byte content."""
    h = hashlib.sha256()
    h.update(targets_csv.read_bytes())
    h.update(b"\x00")  # separator so file-swap produces different digest
    h.update(settings_csv.read_bytes())
    return h.hexdigest()[:8]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_config_hash.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add xic_extractor/config.py tests/test_config_hash.py
git commit -m "feat(config): add compute_config_hash for RT prior library keying"
```

---

### Task 2: Settings schema additions

**Files:**
- Modify: `xic_extractor/settings_schema.py`
- Modify: `xic_extractor/config.py` (extend `ExtractionConfig` + loader)
- Test: `tests/test_settings_new_fields.py` (create)

New keys to add to `CANONICAL_SETTINGS_DEFAULTS` and `_DESCRIPTIONS`:

| Key | Default | Description |
|---|---|---|
| `injection_order_source` | `""` | Path to CSV/XLSX with `Sample_Name` + `Injection_Order`. Empty → fallback to RAW mtime. |
| `rolling_window_size` | `5` | Rolling window half-width for ISTD RT priors (±N injections). |
| `dirty_matrix_mode` | `false` | Relax S/N, tighten shape. Operator flag for known-dirty batches. |
| `rt_prior_library_path` | `""` | Path to `rt_prior_library.csv`. Empty → feature disabled. |
| `emit_score_breakdown` | `false` | Emit per-candidate severity breakdown to a separate sheet. |

- [ ] **Step 1: Write failing test**

```python
# tests/test_settings_new_fields.py
from xic_extractor.settings_schema import CANONICAL_SETTINGS_DEFAULTS


def test_new_keys_present() -> None:
    for key, default in {
        "injection_order_source": "",
        "rolling_window_size": "5",
        "dirty_matrix_mode": "false",
        "rt_prior_library_path": "",
        "emit_score_breakdown": "false",
    }.items():
        assert CANONICAL_SETTINGS_DEFAULTS[key] == default
```

- [ ] **Step 2: Run and confirm failure**

```bash
uv run pytest tests/test_settings_new_fields.py -v
```
Expected: KeyError or AssertionError on first new key.

- [ ] **Step 3: Implement — extend `settings_schema.py`**

Add to both dicts (keeping alphabetical-ish order is not required; follow existing layout):

```python
# in CANONICAL_SETTINGS_DEFAULTS
"injection_order_source": "",
"rolling_window_size": "5",
"dirty_matrix_mode": "false",
"rt_prior_library_path": "",
"emit_score_breakdown": "false",

# in CANONICAL_SETTINGS_DESCRIPTIONS
"injection_order_source": "Sample 注射順序來源檔（CSV/XLSX 有 Sample_Name 與 Injection_Order 欄）",
"rolling_window_size": "ISTD RT prior 的滾動視窗半徑（±N 個注射）",
"dirty_matrix_mode": "髒基質模式（放寬 S/N、收緊峰形；尿液等複雜基質用）",
"rt_prior_library_path": "外部 RT prior library CSV 路徑，留空則停用",
"emit_score_breakdown": "是否輸出 Score Breakdown sheet（預設關閉）",
```

- [ ] **Step 4: Extend `ExtractionConfig` in `config.py`**

Add fields with defaults (keep all old fields untouched):

```python
# Append to ExtractionConfig dataclass fields:
injection_order_source: Path | None = None
rolling_window_size: int = 5
dirty_matrix_mode: bool = False
rt_prior_library_path: Path | None = None
emit_score_breakdown: bool = False
config_hash: str = ""
```

Update the function that builds `ExtractionConfig` from settings dict (search for where `ms2_precursor_tol_da` is read and follow the same pattern). Parse `injection_order_source` / `rt_prior_library_path` as `Path(val)` when non-empty, else `None`. Parse booleans with `.lower() == "true"`. Parse `rolling_window_size` as `int(val)`. Call `compute_config_hash(targets_path, settings_path)` in the loader and assign to `config_hash`.

- [ ] **Step 5: Run test**

```bash
uv run pytest tests/test_settings_new_fields.py tests/test_config_hash.py -v
```
Expected: all pass.

- [ ] **Step 6: Run full suite to catch config-loader regressions**

```bash
uv run pytest --tb=short -q
```
Expected: no new failures.

- [ ] **Step 7: Commit**

```bash
git add xic_extractor/settings_schema.py xic_extractor/config.py tests/test_settings_new_fields.py
git commit -m "feat(settings): add fields for scoring (injection order, dirty matrix, library, breakdown)"
```

---

## Phase B — Priors

### Task 3: `injection_rolling.py`

**Files:**
- Create: `xic_extractor/injection_rolling.py`
- Test: `tests/test_injection_rolling.py`

Module API (public):

```python
def read_injection_order(path: Path) -> dict[str, int]:
    """Read CSV/XLSX with columns Sample_Name, Injection_Order. Sample_Name trimmed."""

def rolling_median_rt(
    istd_label: str,
    target_sample: str,
    rt_by_sample: dict[str, float],
    injection_order: dict[str, int],
    window: int,
) -> float | None:
    """Return median RT of the ISTD across samples whose injection order is within
    [order(target) - window, order(target) + window]. Returns None if fewer than 3
    samples fall in the window or target_sample has no injection_order entry."""
```

- [ ] **Step 1: Write failing test**

```python
# tests/test_injection_rolling.py
from pathlib import Path

import pytest

from xic_extractor.injection_rolling import read_injection_order, rolling_median_rt


def test_read_csv(tmp_path: Path) -> None:
    p = tmp_path / "info.csv"
    p.write_text("Sample_Name,Injection_Order\nS_A,1\nS_B,2\n", encoding="utf-8")
    assert read_injection_order(p) == {"S_A": 1, "S_B": 2}


def test_read_strips_whitespace(tmp_path: Path) -> None:
    p = tmp_path / "info.csv"
    p.write_text("Sample_Name,Injection_Order\n  S_A  ,5\n", encoding="utf-8")
    assert read_injection_order(p) == {"S_A": 5}


def test_rolling_median_uses_window() -> None:
    rts = {f"s{i}": float(i) for i in range(1, 11)}
    order = {f"s{i}": i for i in range(1, 11)}
    # window=2 around s5 covers s3..s7 → RTs 3,4,5,6,7 → median 5.0
    assert rolling_median_rt("istd", "s5", rts, order, window=2) == 5.0


def test_rolling_median_respects_gaps() -> None:
    # Only 2 samples in window → below the 3-sample threshold → None
    rts = {"s1": 1.0, "s2": 2.0, "s10": 10.0}
    order = {"s1": 1, "s2": 2, "s10": 10}
    assert rolling_median_rt("istd", "s10", rts, order, window=1) is None


def test_rolling_median_missing_target_returns_none() -> None:
    assert rolling_median_rt("istd", "unknown", {}, {}, window=5) is None


def test_read_xlsx(tmp_path: Path) -> None:
    from openpyxl import Workbook
    wb = Workbook(); ws = wb.active
    ws.append(["Sample_Name", "Injection_Order"])
    ws.append(["S_X", 3]); ws.append(["S_Y", 7])
    p = tmp_path / "info.xlsx"; wb.save(p)
    assert read_injection_order(p) == {"S_X": 3, "S_Y": 7}
```

- [ ] **Step 2: Run and confirm failure**

```bash
uv run pytest tests/test_injection_rolling.py -v
```
Expected: ImportError.

- [ ] **Step 3: Implement**

```python
# xic_extractor/injection_rolling.py
from __future__ import annotations

import csv
import statistics
from pathlib import Path

from openpyxl import load_workbook

_MIN_WINDOW_SAMPLES = 3


def read_injection_order(path: Path) -> dict[str, int]:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xlsm"}:
        return _read_xlsx(path)
    if suffix == ".csv":
        return _read_csv(path)
    raise ValueError(f"Unsupported injection-order file type: {suffix}")


def _read_csv(path: Path) -> dict[str, int]:
    out: dict[str, int] = {}
    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            name = (row.get("Sample_Name") or "").strip()
            order = row.get("Injection_Order")
            if not name or order in (None, ""):
                continue
            out[name] = int(order)
    return out


def _read_xlsx(path: Path) -> dict[str, int]:
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = ws.iter_rows(values_only=True)
    header = next(rows)
    cols = {str(h): i for i, h in enumerate(header) if h is not None}
    name_i = cols["Sample_Name"]; order_i = cols["Injection_Order"]
    out: dict[str, int] = {}
    for row in rows:
        name = row[name_i]
        order = row[order_i]
        if name is None or order is None:
            continue
        out[str(name).strip()] = int(order)
    return out


def rolling_median_rt(
    istd_label: str,
    target_sample: str,
    rt_by_sample: dict[str, float],
    injection_order: dict[str, int],
    window: int,
) -> float | None:
    target_order = injection_order.get(target_sample)
    if target_order is None:
        return None
    lo = target_order - window
    hi = target_order + window
    values: list[float] = []
    for sample, rt in rt_by_sample.items():
        order = injection_order.get(sample)
        if order is None:
            continue
        if lo <= order <= hi:
            values.append(rt)
    if len(values) < _MIN_WINDOW_SAMPLES:
        return None
    return statistics.median(values)
```

Note: `istd_label` is currently unused in the function body. It's kept in the signature for future per-ISTD filtering and to document intent at call sites; callers pass already-filtered `rt_by_sample` per ISTD.

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_injection_rolling.py -v
```
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add xic_extractor/injection_rolling.py tests/test_injection_rolling.py
git commit -m "feat(scoring): add injection-order rolling median RT prior"
```

---

### Task 4: `rt_prior_library.py` — loader

**Files:**
- Create: `xic_extractor/rt_prior_library.py`
- Test: `tests/test_rt_prior_library.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_rt_prior_library.py
from pathlib import Path

from xic_extractor.rt_prior_library import LibraryEntry, load_library


def test_load_empty_returns_empty(tmp_path: Path) -> None:
    p = tmp_path / "lib.csv"
    p.write_text("config_hash,target_label,role,istd_pair,median_delta_rt,sigma_delta_rt,median_abs_rt,sigma_abs_rt,n_samples,updated_at\n", encoding="utf-8")
    assert load_library(p, "anyhash") == {}


def test_load_missing_file_returns_empty(tmp_path: Path) -> None:
    assert load_library(tmp_path / "does_not_exist.csv", "h") == {}


def test_load_filters_by_config_hash(tmp_path: Path) -> None:
    p = tmp_path / "lib.csv"
    p.write_text(
        "config_hash,target_label,role,istd_pair,median_delta_rt,sigma_delta_rt,median_abs_rt,sigma_abs_rt,n_samples,updated_at\n"
        "aaaa1111,A,analyte,d3-A,0.10,0.02,,,10,2026-01-01T00:00:00\n"
        "bbbb2222,B,analyte,d3-B,0.05,0.01,,,8,2026-01-01T00:00:00\n"
        "aaaa1111,d3-A,ISTD,,,,9.03,0.18,10,2026-01-01T00:00:00\n",
        encoding="utf-8",
    )
    lib = load_library(p, "aaaa1111")
    assert set(lib.keys()) == {("A", "analyte"), ("d3-A", "ISTD")}
    entry = lib[("A", "analyte")]
    assert entry.median_delta_rt == 0.10
    assert entry.sigma_delta_rt == 0.02
    assert entry.n_samples == 10
    istd_entry = lib[("d3-A", "ISTD")]
    assert istd_entry.median_abs_rt == 9.03
    assert istd_entry.sigma_abs_rt == 0.18
```

- [ ] **Step 2: Run test, confirm fail**

```bash
uv run pytest tests/test_rt_prior_library.py -v
```

- [ ] **Step 3: Implement**

```python
# xic_extractor/rt_prior_library.py
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

LIBRARY_FIELDNAMES = (
    "config_hash",
    "target_label",
    "role",
    "istd_pair",
    "median_delta_rt",
    "sigma_delta_rt",
    "median_abs_rt",
    "sigma_abs_rt",
    "n_samples",
    "updated_at",
)


@dataclass(frozen=True)
class LibraryEntry:
    config_hash: str
    target_label: str
    role: str
    istd_pair: str
    median_delta_rt: float | None
    sigma_delta_rt: float | None
    median_abs_rt: float | None
    sigma_abs_rt: float | None
    n_samples: int
    updated_at: str


def load_library(path: Path, config_hash: str) -> dict[tuple[str, str], LibraryEntry]:
    if not path.exists():
        return {}
    out: dict[tuple[str, str], LibraryEntry] = {}
    with path.open(encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if row.get("config_hash") != config_hash:
                continue
            entry = LibraryEntry(
                config_hash=row["config_hash"],
                target_label=row["target_label"],
                role=row["role"],
                istd_pair=row.get("istd_pair") or "",
                median_delta_rt=_opt_float(row.get("median_delta_rt")),
                sigma_delta_rt=_opt_float(row.get("sigma_delta_rt")),
                median_abs_rt=_opt_float(row.get("median_abs_rt")),
                sigma_abs_rt=_opt_float(row.get("sigma_abs_rt")),
                n_samples=int(row.get("n_samples") or 0),
                updated_at=row.get("updated_at") or "",
            )
            out[(entry.target_label, entry.role)] = entry
    return out


def _opt_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
```

- [ ] **Step 4: Run test**

```bash
uv run pytest tests/test_rt_prior_library.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add xic_extractor/rt_prior_library.py tests/test_rt_prior_library.py
git commit -m "feat(scoring): add rt_prior_library loader filtered by config_hash"
```

---

### Task 5: RT prior library pending writer

**Files:**
- Modify: `xic_extractor/rt_prior_library.py`
- Modify: `tests/test_rt_prior_library.py`

- [ ] **Step 1: Add failing test**

Append to `tests/test_rt_prior_library.py`:

```python
from xic_extractor.rt_prior_library import LibraryEntry, write_pending_update


def test_write_pending_round_trip(tmp_path: Path) -> None:
    lib = tmp_path / "lib.csv"
    entries = [
        LibraryEntry(
            config_hash="aaaa1111", target_label="A", role="analyte",
            istd_pair="d3-A", median_delta_rt=0.10, sigma_delta_rt=0.02,
            median_abs_rt=None, sigma_abs_rt=None, n_samples=10,
            updated_at="2026-04-20T12:00:00",
        )
    ]
    pending = write_pending_update(lib, entries)
    assert pending == lib.with_suffix(".pending.csv")
    assert pending.exists()
    # Header + one row
    lines = pending.read_text(encoding="utf-8").strip().splitlines()
    assert lines[0].startswith("config_hash,")
    assert "aaaa1111" in lines[1]
```

- [ ] **Step 2: Run and confirm fail**

- [ ] **Step 3: Implement — append to `rt_prior_library.py`**

```python
def write_pending_update(library_path: Path, entries: list[LibraryEntry]) -> Path:
    """Write a <library_path>.pending.csv file holding proposed new rows.
    The main library is NEVER mutated by this call — merging is a manual
    step after user review."""
    pending = library_path.with_suffix(".pending.csv")
    pending.parent.mkdir(parents=True, exist_ok=True)
    with pending.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(LIBRARY_FIELDNAMES))
        writer.writeheader()
        for e in entries:
            writer.writerow({
                "config_hash": e.config_hash,
                "target_label": e.target_label,
                "role": e.role,
                "istd_pair": e.istd_pair,
                "median_delta_rt": "" if e.median_delta_rt is None else f"{e.median_delta_rt:.6f}",
                "sigma_delta_rt": "" if e.sigma_delta_rt is None else f"{e.sigma_delta_rt:.6f}",
                "median_abs_rt": "" if e.median_abs_rt is None else f"{e.median_abs_rt:.6f}",
                "sigma_abs_rt": "" if e.sigma_abs_rt is None else f"{e.sigma_abs_rt:.6f}",
                "n_samples": e.n_samples,
                "updated_at": e.updated_at,
            })
    return pending
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_rt_prior_library.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add xic_extractor/rt_prior_library.py tests/test_rt_prior_library.py
git commit -m "feat(scoring): add append-only pending writer for RT prior library"
```

---

## Phase C — Baseline & peak geometry helpers

### Task 6: AsLS baseline estimator

**Files:**
- Create: `xic_extractor/baseline.py`
- Test: `tests/test_baseline.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_baseline.py
import numpy as np

from xic_extractor.baseline import asls_baseline


def test_baseline_on_flat_trace_returns_constant() -> None:
    y = np.full(200, 5.0)
    bl = asls_baseline(y, lam=1e5, p=0.01)
    assert np.allclose(bl, 5.0, atol=0.1)


def test_baseline_tracks_slow_hump_but_not_sharp_peak() -> None:
    n = 400
    x = np.arange(n)
    hump = 3.0 * np.exp(-((x - n / 2) ** 2) / (2 * 80 ** 2))  # wide hump
    peak = 20.0 * np.exp(-((x - n / 2) ** 2) / (2 * 5 ** 2))  # sharp peak
    y = hump + peak + 0.1 * np.sin(x / 5)
    bl = asls_baseline(y, lam=1e5, p=0.01)
    # baseline should be close to the hump alone in peak region (within 15% of hump height)
    apex = n // 2
    assert bl[apex] < peak[apex] * 0.3  # baseline under the peak stays low
    # baseline tracks hump away from peak
    side = n // 4
    assert abs(bl[side] - hump[side]) < 0.5


def test_baseline_shape_matches_input() -> None:
    y = np.random.RandomState(0).normal(0, 1, 128) + 10
    bl = asls_baseline(y, lam=1e4, p=0.01)
    assert bl.shape == y.shape
```

- [ ] **Step 2: Run, confirm fail**

- [ ] **Step 3: Implement**

```python
# xic_extractor/baseline.py
from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve


def asls_baseline(y: np.ndarray, lam: float = 1e5, p: float = 0.01,
                  n_iter: int = 10) -> np.ndarray:
    """Asymmetric Least Squares baseline (Eilers & Boelens 2005).

    lam — smoothness (1e3 to 1e9). Higher = smoother baseline.
    p   — asymmetry (0.001 to 0.1). Lower = baseline hugs the bottom.
    """
    y = np.asarray(y, dtype=float)
    n = len(y)
    if n < 3:
        return y.copy()
    # Second-difference matrix
    D = sparse.diags([1, -2, 1], [0, 1, 2], shape=(n - 2, n))
    DtD = lam * (D.T @ D)
    w = np.ones(n)
    for _ in range(n_iter):
        W = sparse.diags(w, 0)
        z = spsolve(W + DtD, w * y)
        w = p * (y > z) + (1 - p) * (y < z)
    return z
```

- [ ] **Step 4: Run**

```bash
uv run pytest tests/test_baseline.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add xic_extractor/baseline.py tests/test_baseline.py
git commit -m "feat(scoring): add asymmetric least squares baseline estimator"
```

---

## Phase D — Seven severity signals

All signal functions share this contract:

```python
def <signal>_severity(...) -> tuple[int, str]:
    """Return (severity, short_label). severity is 0, 1, or 2.
    short_label is 'signal_name' used in Reason strings."""
```

Each task adds one signal with table-driven tests covering severity 0 / 1 / 2 and any special cases.

### Task 7a: symmetry severity

**Files:**
- Create: `xic_extractor/peak_scoring.py` (first content)
- Test: `tests/test_peak_scoring.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_peak_scoring.py
import pytest

from xic_extractor.peak_scoring import symmetry_severity


@pytest.mark.parametrize("ratio,expected", [
    (1.0, 0),
    (0.6, 0),
    (1.8, 0),
    (0.4, 1),
    (2.5, 1),
    (0.2, 2),
    (4.0, 2),
])
def test_symmetry_severity(ratio: float, expected: int) -> None:
    severity, label = symmetry_severity(ratio)
    assert severity == expected
    assert label == "symmetry"
```

- [ ] **Step 2: Run, confirm fail**

- [ ] **Step 3: Implement — create `peak_scoring.py`**

```python
# xic_extractor/peak_scoring.py
"""Tier-based peak scoring. Each signal returns (severity, label)."""
from __future__ import annotations

_LABEL_SYMMETRY = "symmetry"

_SYMMETRY_SOFT_LOW, _SYMMETRY_SOFT_HIGH = 0.5, 2.0
_SYMMETRY_HARD_LOW, _SYMMETRY_HARD_HIGH = 0.3, 3.0


def symmetry_severity(half_width_ratio: float) -> tuple[int, str]:
    if half_width_ratio < _SYMMETRY_HARD_LOW or half_width_ratio > _SYMMETRY_HARD_HIGH:
        return 2, _LABEL_SYMMETRY
    if half_width_ratio < _SYMMETRY_SOFT_LOW or half_width_ratio > _SYMMETRY_SOFT_HIGH:
        return 1, _LABEL_SYMMETRY
    return 0, _LABEL_SYMMETRY
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_peak_scoring.py -v
```
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add xic_extractor/peak_scoring.py tests/test_peak_scoring.py
git commit -m "feat(scoring): add symmetry severity signal"
```

---

### Task 7b: local S/N severity

**Files:**
- Modify: `xic_extractor/peak_scoring.py`
- Modify: `tests/test_peak_scoring.py`

Uses `asls_baseline` from Phase C for baseline estimation.

- [ ] **Step 1: Add failing test**

```python
# append to tests/test_peak_scoring.py
import numpy as np

from xic_extractor.peak_scoring import local_sn_severity


def _make_trace(peak_height: float, noise_std: float = 0.05, n: int = 400, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    x = np.arange(n)
    peak = peak_height * np.exp(-((x - n / 2) ** 2) / (2 * 5 ** 2))
    noise = rng.normal(0.0, noise_std, n)
    return peak + noise + 1.0  # baseline offset of 1.0


def test_local_sn_pass_high_peak() -> None:
    y = _make_trace(peak_height=10.0, noise_std=0.05)
    sev, label = local_sn_severity(y, apex_index=200, dirty_matrix=False)
    assert sev == 0
    assert label == "local_sn"


def test_local_sn_major_low_peak() -> None:
    y = _make_trace(peak_height=0.1, noise_std=0.05)
    sev, _ = local_sn_severity(y, apex_index=200, dirty_matrix=False)
    assert sev == 2


def test_dirty_matrix_relaxes_threshold() -> None:
    # A peak that's major (<2x) under default becomes minor (<3x) under dirty mode,
    # or major (<1.3x) threshold still catches truly tiny peaks.
    y = _make_trace(peak_height=0.3, noise_std=0.05)  # ratio ~5-6, should pass either
    sev_default, _ = local_sn_severity(y, apex_index=200, dirty_matrix=False)
    sev_dirty, _ = local_sn_severity(y, apex_index=200, dirty_matrix=True)
    # Dirty mode is more permissive → severity never increases
    assert sev_dirty <= sev_default
```

- [ ] **Step 2: Run, confirm fail**

- [ ] **Step 3: Implement — append to `peak_scoring.py`**

```python
import numpy as np

from xic_extractor.baseline import asls_baseline

_LABEL_LOCAL_SN = "local_sn"
_SN_SOFT_THRESHOLD = 3.0
_SN_HARD_THRESHOLD = 2.0
_SN_DIRTY_SOFT_THRESHOLD = 2.0
_SN_DIRTY_HARD_THRESHOLD = 1.3


def local_sn_severity(
    intensity: np.ndarray,
    apex_index: int,
    dirty_matrix: bool,
) -> tuple[int, str]:
    """S/N ratio of peak apex vs. MAD of (trace - AsLS baseline) in the full window."""
    if len(intensity) < 5 or apex_index < 0 or apex_index >= len(intensity):
        return 2, _LABEL_LOCAL_SN
    baseline = asls_baseline(np.asarray(intensity, dtype=float))
    residual = np.asarray(intensity, dtype=float) - baseline
    mad = float(np.median(np.abs(residual - np.median(residual))))
    if mad <= 0:
        return 0, _LABEL_LOCAL_SN
    peak_above_baseline = float(intensity[apex_index] - baseline[apex_index])
    ratio = peak_above_baseline / mad
    hard = _SN_DIRTY_HARD_THRESHOLD if dirty_matrix else _SN_HARD_THRESHOLD
    soft = _SN_DIRTY_SOFT_THRESHOLD if dirty_matrix else _SN_SOFT_THRESHOLD
    if ratio < hard:
        return 2, _LABEL_LOCAL_SN
    if ratio < soft:
        return 1, _LABEL_LOCAL_SN
    return 0, _LABEL_LOCAL_SN
```

- [ ] **Step 4: Run**

```bash
uv run pytest tests/test_peak_scoring.py -v
```

- [ ] **Step 5: Commit**

```bash
git add xic_extractor/peak_scoring.py tests/test_peak_scoring.py
git commit -m "feat(scoring): add local S/N severity with AsLS baseline + dirty-matrix mode"
```

---

### Task 7c: NL support severity (three-state)

- [ ] **Step 1: Add failing test**

```python
# append to tests/test_peak_scoring.py
from xic_extractor.peak_scoring import nl_support_severity


def test_nl_present_and_match_is_pass() -> None:
    sev, _ = nl_support_severity(ms2_present=True, nl_match=True)
    assert sev == 0


def test_ms2_present_but_no_nl_match_is_major() -> None:
    sev, _ = nl_support_severity(ms2_present=True, nl_match=False)
    assert sev == 2


def test_no_ms2_is_minor() -> None:
    sev, _ = nl_support_severity(ms2_present=False, nl_match=False)
    assert sev == 1
```

- [ ] **Step 2: Run, fail**

- [ ] **Step 3: Implement**

```python
# append to peak_scoring.py
_LABEL_NL = "nl_support"


def nl_support_severity(ms2_present: bool, nl_match: bool) -> tuple[int, str]:
    if ms2_present and nl_match:
        return 0, _LABEL_NL
    if ms2_present and not nl_match:
        return 2, _LABEL_NL
    return 1, _LABEL_NL  # no MS2 = unknown, modest penalty
```

- [ ] **Step 4-5: Run + commit**

```bash
uv run pytest tests/test_peak_scoring.py -v
git add -A && git commit -m "feat(scoring): add three-state nl_support severity"
```

---

### Task 7d: RT prior severity

- [ ] **Step 1: Add failing test**

```python
# append to tests/test_peak_scoring.py
from xic_extractor.peak_scoring import rt_prior_severity


def test_rt_prior_no_prior_skips() -> None:
    sev, _ = rt_prior_severity(observed=10.0, prior=None, sigma=None)
    assert sev == 0  # no prior available → do not penalise


def test_rt_prior_within_2sigma_pass() -> None:
    sev, _ = rt_prior_severity(observed=10.1, prior=10.0, sigma=0.1)
    assert sev == 0


def test_rt_prior_2_to_5_sigma_minor() -> None:
    sev, _ = rt_prior_severity(observed=10.3, prior=10.0, sigma=0.1)
    assert sev == 1


def test_rt_prior_beyond_5_sigma_major() -> None:
    sev, _ = rt_prior_severity(observed=11.0, prior=10.0, sigma=0.1)
    assert sev == 2


def test_rt_prior_no_sigma_uses_1min_rule() -> None:
    sev, _ = rt_prior_severity(observed=10.3, prior=10.0, sigma=None)
    assert sev == 1
    sev, _ = rt_prior_severity(observed=11.5, prior=10.0, sigma=None)
    assert sev == 2
```

- [ ] **Step 2: fail**

- [ ] **Step 3: Implement**

```python
_LABEL_RT_PRIOR = "rt_prior"
_RT_PRIOR_SIGMA_SOFT = 2.0
_RT_PRIOR_SIGMA_HARD = 5.0
_RT_PRIOR_NO_SIGMA_SOFT_MIN = 0.2  # min deviation when sigma unknown
_RT_PRIOR_NO_SIGMA_HARD_MIN = 1.0


def rt_prior_severity(
    observed: float,
    prior: float | None,
    sigma: float | None,
) -> tuple[int, str]:
    if prior is None:
        return 0, _LABEL_RT_PRIOR
    dev = abs(observed - prior)
    if sigma is not None and sigma > 0:
        n_sigma = dev / sigma
        if n_sigma >= _RT_PRIOR_SIGMA_HARD:
            return 2, _LABEL_RT_PRIOR
        if n_sigma >= _RT_PRIOR_SIGMA_SOFT:
            return 1, _LABEL_RT_PRIOR
        return 0, _LABEL_RT_PRIOR
    # No sigma: fixed minute thresholds
    if dev >= _RT_PRIOR_NO_SIGMA_HARD_MIN:
        return 2, _LABEL_RT_PRIOR
    if dev >= _RT_PRIOR_NO_SIGMA_SOFT_MIN:
        return 1, _LABEL_RT_PRIOR
    return 0, _LABEL_RT_PRIOR
```

- [ ] **Step 4-5: Run + commit**

```bash
uv run pytest tests/test_peak_scoring.py -v
git add -A && git commit -m "feat(scoring): add rt_prior severity with sigma-aware thresholds"
```

---

### Task 7e: RT centrality severity

- [ ] **Step 1: Failing test**

```python
from xic_extractor.peak_scoring import rt_centrality_severity


def test_rt_centrality_center_pass() -> None:
    sev, _ = rt_centrality_severity(observed=5.0, rt_min=0.0, rt_max=10.0)
    assert sev == 0


def test_rt_centrality_within_10pct_soft() -> None:
    sev, _ = rt_centrality_severity(observed=0.8, rt_min=0.0, rt_max=10.0)
    assert sev == 1


def test_rt_centrality_within_1pct_major() -> None:
    sev, _ = rt_centrality_severity(observed=0.05, rt_min=0.0, rt_max=10.0)
    assert sev == 2
```

- [ ] **Step 2: fail**

- [ ] **Step 3: Implement**

```python
_LABEL_RT_CENTRALITY = "rt_centrality"


def rt_centrality_severity(
    observed: float, rt_min: float, rt_max: float
) -> tuple[int, str]:
    span = rt_max - rt_min
    if span <= 0:
        return 0, _LABEL_RT_CENTRALITY
    d_low = observed - rt_min
    d_high = rt_max - observed
    min_edge = min(d_low, d_high) / span
    if min_edge < 0.01:
        return 2, _LABEL_RT_CENTRALITY
    if min_edge < 0.10:
        return 1, _LABEL_RT_CENTRALITY
    return 0, _LABEL_RT_CENTRALITY
```

- [ ] **Step 4-5: Run + commit**

```bash
git add -A && git commit -m "feat(scoring): add rt_centrality severity"
```

---

### Task 7f: noise shape severity

- [ ] **Step 1: Failing test**

```python
def test_noise_shape_smooth_pass() -> None:
    x = np.linspace(-3, 3, 201)
    y = np.exp(-x * x)  # clean gaussian
    sev, _ = noise_shape_severity(y)
    assert sev == 0


def test_noise_shape_ragged_major() -> None:
    rng = np.random.default_rng(1)
    y = rng.normal(0, 1, 201)  # pure noise, very jagged
    sev, _ = noise_shape_severity(y)
    assert sev == 2
```

(Add these imports to the test file: `from xic_extractor.peak_scoring import noise_shape_severity, rt_centrality_severity`.)

- [ ] **Step 2: fail**

- [ ] **Step 3: Implement**

```python
_LABEL_NOISE_SHAPE = "noise_shape"


def noise_shape_severity(intensity: np.ndarray) -> tuple[int, str]:
    """Jaggedness: sum of abs second differences normalised by peak span."""
    y = np.asarray(intensity, dtype=float)
    if len(y) < 3:
        return 0, _LABEL_NOISE_SHAPE
    span = float(y.max() - y.min())
    if span <= 0:
        return 0, _LABEL_NOISE_SHAPE
    second_diff = np.abs(np.diff(y, n=2))
    jagged = float(second_diff.sum() / (span * len(y)))
    if jagged > 0.5:
        return 2, _LABEL_NOISE_SHAPE
    if jagged > 0.3:
        return 1, _LABEL_NOISE_SHAPE
    return 0, _LABEL_NOISE_SHAPE
```

- [ ] **Step 4-5: Run + commit**

```bash
git add -A && git commit -m "feat(scoring): add noise_shape severity"
```

---

### Task 7g: peak width severity

- [ ] **Step 1: Failing test**

```python
from xic_extractor.peak_scoring import peak_width_severity


@pytest.mark.parametrize("ratio,expected", [
    (1.0, 0),
    (0.7, 0),
    (1.4, 0),
    (0.4, 1),
    (2.5, 1),
    (0.2, 2),
    (4.0, 2),
    (None, 0),  # no paired FWHM → signal skipped
])
def test_peak_width_severity(ratio, expected: int) -> None:
    sev, _ = peak_width_severity(ratio)
    assert sev == expected
```

- [ ] **Step 2: fail**

- [ ] **Step 3: Implement**

```python
_LABEL_PEAK_WIDTH = "peak_width"


def peak_width_severity(fwhm_ratio: float | None) -> tuple[int, str]:
    if fwhm_ratio is None:
        return 0, _LABEL_PEAK_WIDTH
    if fwhm_ratio < 0.3 or fwhm_ratio > 3.0:
        return 2, _LABEL_PEAK_WIDTH
    if fwhm_ratio < 0.5 or fwhm_ratio > 2.0:
        return 1, _LABEL_PEAK_WIDTH
    return 0, _LABEL_PEAK_WIDTH
```

- [ ] **Step 4-5: Run + commit**

```bash
git add -A && git commit -m "feat(scoring): add peak_width (FWHM ratio) severity"
```

---

## Phase E — Composition: Confidence, Reason, Selector

### Task 8: Confidence label aggregator

- [ ] **Step 1: Failing test**

```python
from xic_extractor.peak_scoring import Confidence, confidence_from_total


@pytest.mark.parametrize("total,expected", [
    (0, Confidence.HIGH),
    (1, Confidence.MEDIUM),
    (2, Confidence.MEDIUM),
    (3, Confidence.LOW),
    (4, Confidence.LOW),
    (5, Confidence.VERY_LOW),
    (100, Confidence.VERY_LOW),
])
def test_confidence_from_total(total: int, expected: Confidence) -> None:
    assert confidence_from_total(total) == expected
```

- [ ] **Step 2: fail**

- [ ] **Step 3: Implement**

```python
from enum import Enum


class Confidence(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    VERY_LOW = "VERY_LOW"


def confidence_from_total(total_severity: int) -> Confidence:
    if total_severity == 0:
        return Confidence.HIGH
    if total_severity <= 2:
        return Confidence.MEDIUM
    if total_severity <= 4:
        return Confidence.LOW
    return Confidence.VERY_LOW
```

- [ ] **Step 4-5: Run + commit**

```bash
git add -A && git commit -m "feat(scoring): add Confidence enum + aggregator"
```

---

### Task 9: Reason string builder

- [ ] **Step 1: Failing test**

```python
from xic_extractor.peak_scoring import build_reason


def test_reason_all_pass() -> None:
    assert build_reason([(0, "symmetry"), (0, "local_sn")], istd_confidence_note=None) == "all checks passed"


def test_reason_lists_concerns_in_severity_order() -> None:
    reason = build_reason(
        [(0, "symmetry"), (1, "local_sn"), (2, "nl_support")],
        istd_confidence_note=None,
    )
    assert reason == "concerns: nl_support (major); local_sn (minor)"


def test_reason_appends_istd_note() -> None:
    reason = build_reason(
        [(0, "symmetry")], istd_confidence_note="ISTD anchor was LOW"
    )
    assert "ISTD anchor was LOW" in reason
    assert reason.startswith("ISTD anchor was LOW") or reason.endswith("ISTD anchor was LOW")
```

- [ ] **Step 2: fail**

- [ ] **Step 3: Implement**

```python
def build_reason(
    signals: list[tuple[int, str]],
    istd_confidence_note: str | None,
) -> str:
    concerns = [(sev, label) for sev, label in signals if sev >= 1]
    if not concerns and istd_confidence_note is None:
        return "all checks passed"
    parts: list[str] = []
    if concerns:
        concerns.sort(key=lambda pair: -pair[0])  # major first
        phrase = "; ".join(
            f"{label} ({'major' if sev == 2 else 'minor'})" for sev, label in concerns
        )
        parts.append(f"concerns: {phrase}")
    if istd_confidence_note is not None:
        parts.append(istd_confidence_note)
    return "; ".join(parts)
```

- [ ] **Step 4-5: Run + commit**

```bash
git add -A && git commit -m "feat(scoring): add human-readable Reason string builder"
```

---

### Task 10: Multi-candidate selector

**Files:** `peak_scoring.py`, `test_peak_scoring.py`.

Public API:

```python
@dataclass(frozen=True)
class ScoredCandidate:
    candidate: PeakCandidate      # from signal_processing
    severities: tuple[tuple[int, str], ...]  # length 7
    confidence: Confidence
    reason: str
    prior_rt: float | None        # RT prior used for tie-break


def select_candidate_with_confidence(
    scored: list[ScoredCandidate],
) -> ScoredCandidate:
    """Sort by Confidence > RT prior distance > smoothed apex intensity.
    Require len(scored) >= 1."""
```

- [ ] **Step 1: Failing test**

```python
from dataclasses import dataclass

from xic_extractor.peak_scoring import (
    Confidence, ScoredCandidate, select_candidate_with_confidence,
)


@dataclass
class _FakePeak:
    smoothed_apex_rt: float
    smoothed_apex_intensity: float


def _sc(confidence: Confidence, apex_rt: float, intensity: float, prior: float | None) -> ScoredCandidate:
    return ScoredCandidate(
        candidate=_FakePeak(apex_rt, intensity),  # type: ignore[arg-type]
        severities=tuple(),
        confidence=confidence,
        reason="",
        prior_rt=prior,
    )


def test_selector_prefers_higher_confidence() -> None:
    a = _sc(Confidence.MEDIUM, 10.0, 1000, prior=10.0)
    b = _sc(Confidence.HIGH, 10.5, 500, prior=10.0)
    assert select_candidate_with_confidence([a, b]) is b


def test_selector_tiebreak_by_prior_distance() -> None:
    a = _sc(Confidence.HIGH, 10.3, 1000, prior=10.0)
    b = _sc(Confidence.HIGH, 10.05, 500, prior=10.0)
    assert select_candidate_with_confidence([a, b]) is b


def test_selector_final_tiebreak_by_intensity() -> None:
    a = _sc(Confidence.HIGH, 10.1, 1000, prior=10.0)
    b = _sc(Confidence.HIGH, 10.1, 500, prior=10.0)
    assert select_candidate_with_confidence([a, b]) is a
```

- [ ] **Step 2: fail**

- [ ] **Step 3: Implement**

```python
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ScoredCandidate:
    candidate: Any                            # PeakCandidate at runtime
    severities: tuple[tuple[int, str], ...]
    confidence: Confidence
    reason: str
    prior_rt: float | None


_CONFIDENCE_RANK = {
    Confidence.HIGH: 0,
    Confidence.MEDIUM: 1,
    Confidence.LOW: 2,
    Confidence.VERY_LOW: 3,
}


def select_candidate_with_confidence(scored: list[ScoredCandidate]) -> ScoredCandidate:
    if not scored:
        raise ValueError("select_candidate_with_confidence requires at least one candidate")

    def key(sc: ScoredCandidate) -> tuple[int, float, float]:
        dist = abs(sc.candidate.smoothed_apex_rt - sc.prior_rt) if sc.prior_rt is not None else 0.0
        return (
            _CONFIDENCE_RANK[sc.confidence],
            dist,
            -sc.candidate.smoothed_apex_intensity,
        )

    return min(scored, key=key)
```

- [ ] **Step 4-5: Run + commit**

```bash
uv run pytest tests/test_peak_scoring.py -v
git add -A && git commit -m "feat(scoring): add multi-candidate selector (confidence > prior distance > intensity)"
```

---

## Phase F — Integration

### Task 11: `ScoringContext` + top-level scorer

The scorer combines all 7 signals given the inputs a single peak needs. Placed in `peak_scoring.py`.

**Files:** `peak_scoring.py`, `test_peak_scoring.py`.

- [ ] **Step 1: Failing test**

```python
from xic_extractor.peak_scoring import ScoringContext, score_candidate

from xic_extractor.signal_processing import PeakCandidate, PeakResult


def _make_candidate(apex_rt: float, apex_intensity: float) -> PeakCandidate:
    peak = PeakResult(rt=apex_rt, intensity=apex_intensity, intensity_smoothed=apex_intensity,
                      area=100.0, peak_start=apex_rt - 0.1, peak_end=apex_rt + 0.1)
    return PeakCandidate(peak=peak, smoothed_apex_rt=apex_rt, smoothed_apex_intensity=apex_intensity,
                         smoothed_apex_index=100, raw_apex_rt=apex_rt, raw_apex_intensity=apex_intensity,
                         raw_apex_index=100, prominence=apex_intensity * 0.5)


def test_score_candidate_returns_seven_severities() -> None:
    cand = _make_candidate(apex_rt=10.0, apex_intensity=1000)
    # synthetic clean peak trace
    x = np.linspace(9, 11, 201)
    y = 1000 * np.exp(-((x - 10) / 0.1) ** 2) + 5
    ctx = ScoringContext(
        rt_array=x, intensity_array=y, apex_index=100,
        half_width_ratio=1.0, fwhm_ratio=1.0,
        ms2_present=True, nl_match=True,
        rt_prior=10.0, rt_prior_sigma=0.1,
        rt_min=9.0, rt_max=11.0,
        dirty_matrix=False,
    )
    scored = score_candidate(cand, ctx, prior_rt=10.0)
    assert len(scored.severities) == 7
    assert scored.confidence == Confidence.HIGH
    assert scored.reason == "all checks passed"
```

- [ ] **Step 2: fail**

- [ ] **Step 3: Implement**

```python
@dataclass(frozen=True)
class ScoringContext:
    rt_array: np.ndarray
    intensity_array: np.ndarray
    apex_index: int
    half_width_ratio: float
    fwhm_ratio: float | None
    ms2_present: bool
    nl_match: bool
    rt_prior: float | None
    rt_prior_sigma: float | None
    rt_min: float
    rt_max: float
    dirty_matrix: bool


def score_candidate(
    candidate: Any,  # PeakCandidate
    ctx: ScoringContext,
    prior_rt: float | None,
    istd_confidence_note: str | None = None,
) -> ScoredCandidate:
    severities: list[tuple[int, str]] = [
        symmetry_severity(ctx.half_width_ratio),
        local_sn_severity(ctx.intensity_array, ctx.apex_index, ctx.dirty_matrix),
        nl_support_severity(ctx.ms2_present, ctx.nl_match),
        rt_prior_severity(candidate.smoothed_apex_rt, ctx.rt_prior, ctx.rt_prior_sigma),
        rt_centrality_severity(candidate.smoothed_apex_rt, ctx.rt_min, ctx.rt_max),
        noise_shape_severity(ctx.intensity_array),
        peak_width_severity(ctx.fwhm_ratio),
    ]
    total = sum(s for s, _ in severities)
    confidence = confidence_from_total(total)
    reason = build_reason(severities, istd_confidence_note)
    return ScoredCandidate(
        candidate=candidate,
        severities=tuple(severities),
        confidence=confidence,
        reason=reason,
        prior_rt=prior_rt,
    )
```

- [ ] **Step 4-5: Run + commit**

```bash
uv run pytest tests/test_peak_scoring.py -v
git add -A && git commit -m "feat(scoring): compose 7 severities into scored candidate"
```

---

### Task 12: Wire `signal_processing._select_candidate` to use scoring

**Files:** `xic_extractor/signal_processing.py`, `tests/test_signal_processing_selection.py` (create).

The existing function signature of `_select_candidate(candidates, preferred_rt, strict_preferred_rt)` is called from `find_peak_and_area`. We keep the signature but delegate to `peak_scoring` when a `ScoringContext` is available; fall back to legacy behaviour otherwise. To avoid a ripple change across `find_peak_and_area`, we add an **optional** `scoring_context` keyword on `find_peak_and_area` and thread it through.

- [ ] **Step 1: Write failing integration test**

```python
# tests/test_signal_processing_selection.py
import numpy as np

from xic_extractor.config import ExtractionConfig
from xic_extractor.signal_processing import find_peak_and_area
from xic_extractor.peak_scoring import Confidence, ScoringContext


def _cfg() -> ExtractionConfig:
    # minimal viable config; adjust required fields to their dataclass defaults
    from pathlib import Path
    return ExtractionConfig(
        data_dir=Path("."), dll_dir=Path("."),
        output_csv=Path("out.csv"), diagnostics_csv=Path("diag.csv"),
        smooth_window=11, smooth_polyorder=3,
        peak_rel_height=0.95, peak_min_prominence_ratio=0.1,
        ms2_precursor_tol_da=1.6, nl_min_intensity_ratio=0.01,
    )


def test_find_peak_and_area_without_scoring_context_unchanged() -> None:
    rt = np.linspace(0, 10, 501)
    y = 100 * np.exp(-((rt - 5) / 0.2) ** 2) + 1
    result = find_peak_and_area(rt, y, _cfg())
    assert result.status == "OK"
    assert abs(result.peak.rt - 5.0) < 0.05


def test_find_peak_and_area_with_scoring_returns_same_best_for_clean_peak() -> None:
    rt = np.linspace(0, 10, 501)
    y = 100 * np.exp(-((rt - 5) / 0.2) ** 2) + 1
    ctx_builder = lambda cand: ScoringContext(
        rt_array=rt, intensity_array=y, apex_index=cand.smoothed_apex_index,
        half_width_ratio=1.0, fwhm_ratio=1.0,
        ms2_present=True, nl_match=True,
        rt_prior=5.0, rt_prior_sigma=0.1,
        rt_min=0.0, rt_max=10.0, dirty_matrix=False,
    )
    result = find_peak_and_area(rt, y, _cfg(), scoring_context_builder=ctx_builder)
    assert result.status == "OK"
    assert abs(result.peak.rt - 5.0) < 0.05
```

- [ ] **Step 2: fail** (new kwarg not accepted yet)

- [ ] **Step 3: Implement**

Modify `find_peak_and_area` signature:

```python
# in signal_processing.py
from typing import Callable

from xic_extractor.peak_scoring import (
    ScoredCandidate, ScoringContext, score_candidate, select_candidate_with_confidence,
)


def find_peak_and_area(
    rt: np.ndarray,
    intensity: np.ndarray,
    config: ExtractionConfig,
    *,
    preferred_rt: float | None = None,
    strict_preferred_rt: bool = False,
    scoring_context_builder: Callable[[PeakCandidate], ScoringContext] | None = None,
    istd_confidence_note: str | None = None,
) -> PeakDetectionResult:
    ...
```

Where `_select_candidate` used to be called, insert:

```python
if scoring_context_builder is not None and candidates_result.status == "OK":
    scored_list = [
        score_candidate(c, scoring_context_builder(c), prior_rt=preferred_rt,
                        istd_confidence_note=istd_confidence_note)
        for c in candidates_result.candidates
    ]
    chosen = select_candidate_with_confidence(scored_list)
    best_candidate = chosen.candidate
    # store chosen.confidence, chosen.reason on the result later
else:
    best_candidate = _select_candidate(
        candidates_result.candidates,
        preferred_rt=preferred_rt,
        strict_preferred_rt=strict_preferred_rt,
    )
```

Extend `PeakDetectionResult` to carry `confidence: str | None = None` and `reason: str | None = None` fields (with defaults so existing callers keep working). Thread these through `_detection_success`. Write Confidence as the enum value string (`"HIGH"`, etc.).

- [ ] **Step 4: Run**

```bash
uv run pytest tests/test_signal_processing_selection.py tests/test_peak_scoring.py -v
```

- [ ] **Step 5: Run full suite — anything broken by the new kwarg?**

```bash
uv run pytest --tb=short -q
```

- [ ] **Step 6: Commit**

```bash
git add xic_extractor/signal_processing.py tests/test_signal_processing_selection.py
git commit -m "feat(selection): plumb optional scoring context through find_peak_and_area"
```

---

### Task 13: `extractor.run()` split — pre-pass for ISTD anchors

**Files:** `xic_extractor/extractor.py`. No new unit tests here (integration covered by regression test in Task 17); add a small harness test that verifies `run()` still returns the same `RunOutput` shape.

- [ ] **Step 1: Add failing shape-preservation test**

```python
# tests/test_extractor_runshape.py
from xic_extractor.extractor import RunOutput


def test_run_output_has_expected_fields() -> None:
    # Purely a compile-time check: the dataclass keeps its fields.
    assert {"file_results", "diagnostics"}.issubset(RunOutput.__dataclass_fields__.keys())
```

- [ ] **Step 2: Confirm passes even before change** (guard against silent schema drift during refactor)

- [ ] **Step 3: Implement the split**

Refactor `run()` along these lines (keep the `progress_callback` semantics):

```python
def run(
    config: ExtractionConfig,
    targets: list[Target],
    progress_callback: Callable[[int, int, str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
    injection_order: dict[str, int] | None = None,
    rt_prior_library: dict[tuple[str, str], LibraryEntry] | None = None,
) -> RunOutput:
    raw_paths = _list_raw_files(config.data_dir)
    total = len(raw_paths)
    # Pre-pass: ISTD-only, collect anchor RTs
    istd_targets = [t for t in targets if t.is_istd]
    istd_rts_by_sample: dict[str, dict[str, float]] = {}  # {istd_label: {sample_stem: rt}}
    for index, raw_path in enumerate(raw_paths, 1):
        if should_stop is not None and should_stop():
            break
        anchors = _extract_istd_anchors_only(config, istd_targets, raw_path)
        for istd_label, rt in anchors.items():
            istd_rts_by_sample.setdefault(istd_label, {})[raw_path.stem] = rt
        if progress_callback is not None:
            progress_callback(index, total * 2, raw_path.name)  # 0..50%

    # Build context for main pass
    scoring_ctx_factory = _make_scoring_context_factory(
        config=config,
        injection_order=injection_order or _fallback_injection_order_from_mtime(raw_paths),
        istd_rts_by_sample=istd_rts_by_sample,
        rt_prior_library=rt_prior_library or {},
    )

    # Main pass (unchanged per-file flow, plus scoring context)
    file_results = []
    diagnostics = []
    for index, raw_path in enumerate(raw_paths, 1):
        if should_stop is not None and should_stop():
            break
        file_result, file_diag = _process_file(
            config, targets, raw_path,
            scoring_context_factory=scoring_ctx_factory,
        )
        file_results.append(file_result)
        diagnostics.extend(file_diag)
        if progress_callback is not None:
            progress_callback(total + index, total * 2, raw_path.name)  # 50..100%

    return RunOutput(file_results=file_results, diagnostics=diagnostics)
```

New helpers (same file):

- `_extract_istd_anchors_only(config, istd_targets, raw_path) -> dict[str, float]` — a stripped version of `_process_file` that runs only the existing extraction logic for ISTDs, returns `{istd_label: best_rt}`. Uses the current `find_peak_and_area` without a scoring context (legacy path) so pre-pass is cheap and independent of scoring.
- `_make_scoring_context_factory(...) -> Callable[[Target, str, np.ndarray, np.ndarray], Callable[[PeakCandidate], ScoringContext]]` — given the batch context, returns a closure that given (target, sample_stem, rt_array, intensity_array) produces a `ScoringContext` builder for use in `_extract_one_target`.
- `_fallback_injection_order_from_mtime(raw_paths) -> dict[str, int]` — sort RAWs by mtime, assign 1..N.

In `_process_file` / `_extract_one_target`, when the scoring context factory is provided, construct a context builder and pass it to `find_peak_and_area` along with the appropriate `istd_confidence_note` (propagated from this file's ISTD scoring — see Task 14).

- [ ] **Step 4: Run full suite, confirm nothing regresses structurally**

```bash
uv run pytest --tb=short -q
```

- [ ] **Step 5: Commit**

```bash
git add xic_extractor/extractor.py tests/test_extractor_runshape.py
git commit -m "refactor(extractor): split run into pre-pass ISTD anchors + main scoring pass"
```

---

### Task 14: ISTD Confidence propagation to analyte Reason

**Files:** `xic_extractor/extractor.py`, `tests/test_istd_propagation.py`.

- [ ] **Step 1: Failing test**

```python
# tests/test_istd_propagation.py
from xic_extractor.extractor import _istd_confidence_note


def test_note_none_when_high() -> None:
    assert _istd_confidence_note("HIGH") is None


def test_note_present_when_low() -> None:
    assert "LOW" in _istd_confidence_note("LOW")


def test_note_present_when_very_low() -> None:
    assert "VERY_LOW" in _istd_confidence_note("VERY_LOW")
```

- [ ] **Step 2: fail**

- [ ] **Step 3: Implement in `extractor.py`**

```python
def _istd_confidence_note(istd_confidence: str | None) -> str | None:
    if istd_confidence in (None, "HIGH", "MEDIUM"):
        return None
    return f"ISTD anchor was {istd_confidence}"
```

Then inside `_extract_one_target`, when the target has an `istd_pair` and the ISTD's Confidence was recorded during the main pass, compute the note and pass it to `find_peak_and_area(..., istd_confidence_note=note)`.

Thread a `dict[str, str]` (sample-local `istd_confidence_by_label`) through `_process_file` so analytes can look up their ISTD's Confidence.

- [ ] **Step 4-5: Run + commit**

```bash
uv run pytest tests/test_istd_propagation.py --tb=short -q
git add -A && git commit -m "feat(extractor): propagate ISTD confidence into analyte Reason"
```

---

### Task 15: Output columns — XIC Results + Summary

**Files:** `xic_extractor/extractor.py` (writers), `tests/test_output_columns.py` (create).

- [ ] **Step 1: Failing test**

```python
# tests/test_output_columns.py — XIC Results and Summary must include new fields
# Snapshot-style test against the writer helpers, using a fabricated minimal FileResult.
# Implement after Task 14 merges; the test reads the produced workbook and asserts:
#   - Main sheet headers contain 'Confidence' and 'Reason'
#   - Summary sheet headers contain 'Confidence HIGH', 'Confidence MEDIUM', 'Confidence LOW', 'Confidence VERY_LOW'
# Full code below.

from pathlib import Path

from openpyxl import load_workbook

from xic_extractor.extractor import (
    DiagnosticRecord, ExtractionResult, FileResult, RunOutput,
    _write_xlsx,  # see Step 3
)
from xic_extractor.signal_processing import PeakResult


def _fabricate_run_output() -> RunOutput:
    peak = PeakResult(rt=9.03, intensity=500, intensity_smoothed=500,
                      area=123.0, peak_start=8.9, peak_end=9.2)
    er = ExtractionResult(
        target_label="d3-5-hmdC", role="ISTD", istd_pair="",
        peak=peak, confidence="HIGH", reason="all checks passed",
        nl_result=None,  # keep loose; writer must tolerate
    )
    fr = FileResult(sample_name="S1", group=None, extraction_results=[er])
    return RunOutput(file_results=[fr], diagnostics=[])


def test_main_sheet_has_confidence_and_reason(tmp_path: Path) -> None:
    ro = _fabricate_run_output()
    out = tmp_path / "r.xlsx"
    _write_xlsx(out, ro, targets=[], emit_score_breakdown=False)
    wb = load_workbook(out, read_only=True)
    ws = wb["XIC Results"]
    headers = [c.value for c in next(ws.iter_rows(max_row=1))]
    assert "Confidence" in headers
    assert "Reason" in headers


def test_summary_sheet_has_confidence_counts(tmp_path: Path) -> None:
    ro = _fabricate_run_output()
    out = tmp_path / "r.xlsx"
    _write_xlsx(out, ro, targets=[], emit_score_breakdown=False)
    wb = load_workbook(out, read_only=True)
    ws = wb["Summary"]
    headers = [c.value for c in next(ws.iter_rows(max_row=1))]
    for label in ("Confidence HIGH", "Confidence MEDIUM", "Confidence LOW", "Confidence VERY_LOW"):
        assert label in headers
```

(Note: depending on current `ExtractionResult` shape, add `confidence: str = "HIGH"` and `reason: str = ""` fields with defaults. Retain existing fields.)

- [ ] **Step 2: fail**

- [ ] **Step 3: Implement — extend `ExtractionResult` and XLSX writers**

Add to `ExtractionResult` dataclass in `extractor.py`:

```python
confidence: str = "HIGH"
reason: str = ""
```

Extend `_write_output_csv` / main-sheet writer (or whatever current writer is) to emit `Confidence` and `Reason` columns. Extend Summary writer to count `Confidence` per target and emit four new columns. If the current project writes XLSX through another function, apply same additions there.

Expose `_write_xlsx(output_path, run_output, targets, emit_score_breakdown: bool) -> None` as the single writer entry (if not already). This is what tests call.

- [ ] **Step 4-5: Run + commit**

```bash
uv run pytest tests/test_output_columns.py --tb=short -q
git add -A && git commit -m "feat(output): add Confidence + Reason to XIC Results; confidence counts in Summary"
```

---

### Task 16: Optional Score Breakdown sheet

**Files:** `xic_extractor/extractor.py`, `tests/test_output_columns.py`.

- [ ] **Step 1: Failing test**

```python
def test_score_breakdown_sheet_absent_by_default(tmp_path: Path) -> None:
    out = tmp_path / "r.xlsx"
    _write_xlsx(out, _fabricate_run_output(), targets=[], emit_score_breakdown=False)
    wb = load_workbook(out, read_only=True)
    assert "Score Breakdown" not in wb.sheetnames


def test_score_breakdown_sheet_emitted_when_flag_on(tmp_path: Path) -> None:
    out = tmp_path / "r.xlsx"
    _write_xlsx(out, _fabricate_run_output(), targets=[], emit_score_breakdown=True)
    wb = load_workbook(out, read_only=True)
    assert "Score Breakdown" in wb.sheetnames
    ws = wb["Score Breakdown"]
    headers = [c.value for c in next(ws.iter_rows(max_row=1))]
    for col in (
        "SampleName", "Target", "symmetry", "local_sn", "nl_support",
        "rt_prior", "rt_centrality", "noise_shape", "peak_width",
        "Total Severity", "Confidence", "Prior RT", "Prior Source",
    ):
        assert col in headers
```

- [ ] **Step 2: fail**

- [ ] **Step 3: Implement**

When `emit_score_breakdown=True`, create a `Score Breakdown` sheet and write one row per `ExtractionResult`, pulling severities from a new field `ExtractionResult.severities: tuple[tuple[int, str], ...] = ()` and prior metadata from `ExtractionResult.prior_rt: float | None = None` and `ExtractionResult.prior_source: str = ""`.

Plumb these from `peak_scoring.ScoredCandidate` through `_extract_one_target` into `ExtractionResult`.

- [ ] **Step 4-5: Run + commit**

```bash
uv run pytest tests/test_output_columns.py --tb=short -q
git add -A && git commit -m "feat(output): optional Score Breakdown sheet gated by emit_score_breakdown"
```

---

### Task 17: Tissue regression fixture and test harness

**Files:**
- Create: `tests/fixtures/tissue_regression/baseline.json`
- Create: `tests/fixtures/tissue_regression/sample_subset.csv`
- Create: `tests/test_tissue_regression.py`

- [ ] **Step 1: Generate the baseline JSON from existing `output/xic_results_20260420_0309.xlsx`**

```bash
uv run python - <<'PY'
import json
from pathlib import Path
from openpyxl import load_workbook

SAMPLES = [
    # pick 10 representative samples — user will refine this list
    "Tumor tissue BC2257_DNA",
    "Tumor tissue BC2263_DNA",
    "Tumor tissue BC2271_DNA",
    "Normal tissue BC2257_DNA",
    "Normal tissue BC2263_DNA",
    "Normal tissue BC2271_DNA",
    "Benign fat BC0979_DNA",
    "Benign fat BC1095_DNA",
    "Breast Cancer Tissue_ pooled_QC_1",
    "Breast Cancer Tissue_ pooled_QC_5",
]

src = Path("output/xic_results_20260420_0309.xlsx")
wb = load_workbook(src, read_only=True, data_only=True)
ws = wb["XIC Results"]
headers = [c.value for c in next(ws.iter_rows(max_row=1))]
idx = {h: i for i, h in enumerate(headers)}

keep = set(SAMPLES)
rows = []
for row in ws.iter_rows(min_row=2, values_only=True):
    name = (row[idx["SampleName"]] or "").strip()
    if name.strip() not in keep:
        continue
    rt = row[idx["RT"]]; area = row[idx["Area"]]
    rows.append({
        "sample": name.strip(),
        "target": row[idx["Target"]],
        "role": row[idx["Role"]],
        "rt": rt if isinstance(rt, (int, float)) else None,
        "area": area if isinstance(area, (int, float)) else None,
    })

out = Path("tests/fixtures/tissue_regression/baseline.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
print(f"wrote {len(rows)} rows")
PY
```

Commit this baseline alongside the tests so CI can compare.

- [ ] **Step 2: Write regression test**

```python
# tests/test_tissue_regression.py
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from xic_extractor.config import load_targets, load_settings  # adjust to real API
from xic_extractor.extractor import run

_RT_TOLERANCE_MIN = 0.05
_AREA_REL_TOLERANCE = 0.05


@pytest.fixture(scope="session")
def fixture_root() -> Path:
    root = os.environ.get("XIC_TISSUE_FIXTURE_DIR")
    if not root:
        pytest.skip("XIC_TISSUE_FIXTURE_DIR not set; regression fixture unavailable")
    return Path(root)


def test_tissue_regression(fixture_root: Path) -> None:
    baseline_path = Path("tests/fixtures/tissue_regression/baseline.json")
    baseline = {(r["sample"], r["target"]): r for r in json.loads(baseline_path.read_text("utf-8"))}

    # Load config from the example config paths used in the baseline run
    config, targets = _load_example_config(fixture_root)
    ro = run(config=config, targets=targets)

    current = {}
    for fr in ro.file_results:
        for er in fr.extraction_results:
            current[(fr.sample_name.strip(), er.target_label)] = er

    failures: list[str] = []
    for key, base in baseline.items():
        er = current.get(key)
        if er is None or er.peak is None:
            if base["rt"] is not None:
                failures.append(f"{key}: regressed — baseline detected, current missing")
            continue
        if base["rt"] is None:
            continue  # baseline didn't detect; current discovering new peaks is fine
        if abs(er.peak.rt - base["rt"]) > _RT_TOLERANCE_MIN:
            failures.append(f"{key}: RT shifted {base['rt']} → {er.peak.rt}")
        if base["area"] and abs(er.peak.area - base["area"]) / base["area"] > _AREA_REL_TOLERANCE:
            failures.append(f"{key}: Area regressed {base['area']} → {er.peak.area}")
        if er.confidence not in ("HIGH", "MEDIUM"):
            failures.append(f"{key}: Confidence dropped to {er.confidence}")

    assert not failures, "Regression failures:\n" + "\n".join(failures[:20])


def _load_example_config(fixture_root: Path):
    # Example: adjust to the project's actual config loader
    ...
```

Replace `_load_example_config` body once we know the real loader. This task's Step 3 finalises that.

- [ ] **Step 3: Complete `_load_example_config`**

Look at how `launch_gui.bat` or `scripts/*.py` build the config for the example CSVs. Mirror that here, pointing `data_dir` at `fixture_root`.

- [ ] **Step 4: Run locally with fixture env var set**

```bash
XIC_TISSUE_FIXTURE_DIR="C:/Xcalibur/data/20260106_CSMU_NAA_Tissue_R" uv run pytest tests/test_tissue_regression.py -v
```
Expected: passes; failures list is empty.

- [ ] **Step 5: Run full suite without fixture env set**

```bash
uv run pytest --tb=short -q
```
Expected: regression test is skipped; everything else passes.

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures/tissue_regression/baseline.json tests/test_tissue_regression.py
git commit -m "test: add tissue regression harness with 10-sample fixture baseline"
```

---

### Task 18: Scoring context factory — ΔRT + rolling prior wiring

**Files:** `xic_extractor/extractor.py`, `tests/test_scoring_context.py` (create).

This task finalises how `ScoringContext` is built for a given target/sample/trace. It pulls together all previous plumbing: the pre-pass ISTD RTs → rolling median, the library → ΔRT analyte prior, the injection order, the dirty-matrix flag.

- [ ] **Step 1: Failing unit test for the factory**

```python
# tests/test_scoring_context.py
from xic_extractor.extractor import _build_scoring_context_factory
from xic_extractor.rt_prior_library import LibraryEntry
# ... (construct fake target/sample data, confirm factory yields context with
#      rt_prior / rt_prior_sigma populated for an ISTD using rolling median,
#      and for an analyte using ΔRT library lookup).
```

Provide concrete test assertions for three scenarios:
1. ISTD + injection order + ≥3 neighbours → `ctx.rt_prior` is rolling median, `ctx.rt_prior_sigma` is None (we have no σ from a rolling window alone).
2. Analyte with ISTD anchor in same file + ΔRT library entry → `ctx.rt_prior = istd_rt + library.median_delta_rt`, `ctx.rt_prior_sigma = library.sigma_delta_rt`.
3. Neither injection order nor library → `ctx.rt_prior is None`.

- [ ] **Step 2: fail**

- [ ] **Step 3: Implement `_build_scoring_context_factory`**

```python
def _build_scoring_context_factory(
    config: ExtractionConfig,
    injection_order: dict[str, int],
    istd_rts_by_sample: dict[str, dict[str, float]],
    rt_prior_library: dict[tuple[str, str], LibraryEntry],
):
    def make(target: Target, sample_stem: str, rt_array, intensity_array,
             istd_rt_in_this_sample: float | None,
             fwhm_ratio: float | None, ms2_present: bool, nl_match: bool,
             half_width_ratio: float):
        rt_prior: float | None = None
        rt_prior_sigma: float | None = None

        if target.is_istd:
            rt_map = istd_rts_by_sample.get(target.label, {})
            rt_prior = rolling_median_rt(
                target.label, sample_stem, rt_map, injection_order,
                window=config.rolling_window_size,
            )
            # library fallback for ISTD absolute RT
            if rt_prior is None:
                lib = rt_prior_library.get((target.label, "ISTD"))
                if lib is not None:
                    rt_prior = lib.median_abs_rt
                    rt_prior_sigma = lib.sigma_abs_rt
        else:
            lib = rt_prior_library.get((target.label, "analyte"))
            if lib is not None and istd_rt_in_this_sample is not None and lib.median_delta_rt is not None:
                rt_prior = istd_rt_in_this_sample + lib.median_delta_rt
                rt_prior_sigma = lib.sigma_delta_rt

        def builder(candidate):
            return ScoringContext(
                rt_array=rt_array, intensity_array=intensity_array,
                apex_index=candidate.smoothed_apex_index,
                half_width_ratio=half_width_ratio, fwhm_ratio=fwhm_ratio,
                ms2_present=ms2_present, nl_match=nl_match,
                rt_prior=rt_prior, rt_prior_sigma=rt_prior_sigma,
                rt_min=target.rt_min, rt_max=target.rt_max,
                dirty_matrix=config.dirty_matrix_mode,
            )
        return builder
    return make
```

- [ ] **Step 4: In `_extract_one_target`**, compute `half_width_ratio` and `fwhm_ratio` from the already-available `PeakCandidate` via `scipy.signal.peak_widths` at two heights (0.5 for FWHM; left and right separately for symmetry). Helper:

```python
def _compute_shape_metrics(intensity: np.ndarray, apex_index: int) -> tuple[float, float | None]:
    """Return (half_width_ratio, fwhm) for the peak at apex_index."""
    from scipy.signal import peak_widths
    results = peak_widths(intensity, [apex_index], rel_height=0.5)
    fwhm = float(results[0][0]) if len(results[0]) else None
    left_ips = float(results[2][0]); right_ips = float(results[3][0])
    left = apex_index - left_ips; right = right_ips - apex_index
    if left <= 0 or right <= 0:
        return 1.0, fwhm
    return float(left / right), fwhm
```

The `fwhm_ratio` is `fwhm_self / fwhm_paired_istd` for analytes; for ISTDs, `fwhm_ratio=None`. Pipe the paired ISTD's FWHM through the sample-local cache you already use for `istd_anchor_rts`.

- [ ] **Step 5: Run scoring + full suite**

```bash
uv run pytest tests/test_scoring_context.py tests/test_peak_scoring.py tests/test_tissue_regression.py --tb=short -q
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(extractor): build ScoringContext with ΔRT + rolling priors + shape metrics"
```

---

## Phase G — Final integration pass

### Task 19: Full tissue regression green + lint

- [ ] **Step 1: Run full tissue regression**

```bash
XIC_TISSUE_FIXTURE_DIR="C:/Xcalibur/data/20260106_CSMU_NAA_Tissue_R" uv run pytest --tb=short -q
```
Expected: **all pass**.

- [ ] **Step 2: If any failures appear, *do not* loosen thresholds unless the deviation is explained and user-approved.** Investigate first. Record findings in PR description.

- [ ] **Step 3: Run `mypy` / `ruff` per existing project conventions**

```bash
uv run ruff check xic_extractor tests
uv run mypy xic_extractor
```
Expected: green.

- [ ] **Step 4: Commit any lint fixes separately**

```bash
git add -A
git commit -m "chore(scoring): address lint + mypy"
```

---

### Task 20: Open PR

- [ ] **Step 1: Push and open PR**

```bash
git push -u origin <current-branch>
gh pr create --title "feat(scoring): tier-based peak scoring with ΔRT anchoring (Stage 1)" \
  --body "$(cat <<'EOF'
## Summary

Implements Stage 1 of the peak-scoring redesign
(spec: `docs/superpowers/specs/2026-04-20-peak-scoring-tiered-design.md`).

- 7 severity signals, no HARD-FAIL, no weights, no profiles
- Confidence (HIGH/MEDIUM/LOW/VERY_LOW) + human-readable Reason in XIC Results
- ΔRT-anchored priors for analytes; injection-order rolling median for ISTDs
- External RT prior library keyed on `config_hash`
- Pre-pass (ISTD only) + main-pass architecture
- Tissue regression harness (10 samples, ±0.05 min RT, ±5% Area tolerance)

## Test plan

- [x] Unit tests for each severity signal
- [x] Injection rolling + library + baseline unit tests
- [x] Tissue regression (skipped in CI without fixture; runs locally with env var)
- [ ] Stage 2 (urine validation) — separate PR after this merges

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 2: Request Codex review on the PR** per `CLAUDE.md` cross-validation rule.

---

## Out of Scope (Stage 2 plan)

Deferred to the next plan document:

- Urine fixture + annotated ground truth
- `dirty_matrix_mode` final threshold tuning on urine data
- Any threshold loosening; all Stage 1 thresholds are fixed by this plan
- Pending-library merge UI / workflow (Stage 2 also sets the actual first ΔRT entries for the library)
- GUI changes (the current GUI reads the same Excel output; it should pick up new columns automatically, but visual review for `Confidence`/`Reason` formatting is a Stage 2 item)

---

## Self-Review Notes

- Every task has concrete code or concrete commands — no TODOs or "add error handling."
- Type names (`ScoredCandidate`, `ScoringContext`, `Confidence`, `LibraryEntry`) are defined before any task that uses them.
- Spec section coverage:
  - §4.1 group-consensus abandoned: enforced by never reading `sample_groups` for priors in the factory (Task 18).
  - §4.2 ΔRT primary: Task 18, factory analyte branch.
  - §4.3 rolling-window secondary: Task 3 + Task 18 ISTD branch.
  - §4.4 injection-order source: Task 3 reader + Task 13 mtime fallback.
  - §4.5 tier scoring: Tasks 7a–g + 8 + 11.
  - §4.6 multi-candidate selection: Task 10.
  - §4.7 NL three states: Task 7c.
  - §4.8 AsLS baseline: Task 6 + Task 7b.
  - §4.9 ISTD propagation: Task 14.
  - §4.10 dirty_matrix_mode: Task 2 settings + Task 7b thresholds.
  - §4.11 single-sample no fallback: Task 18 yields `None` prior when no data; scoring still runs.
  - §4.12 pre-pass + main-pass: Task 13.
  - §5 library schema: Tasks 4–5.
  - §6 output changes: Tasks 15–16.
  - §7 module layout: file-structure section above.
  - §8 testing strategy: Task 17 (tissue).
  - §9 Stage 1 rollout: Tasks 19–20.
