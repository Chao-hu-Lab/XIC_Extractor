# Untargeted RAW XIC Throughput Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce untargeted alignment wall time beyond `--raw-workers` by cutting repeated Thermo RAW XIC API calls while preserving full-output equivalence by default.

**Architecture:** Add a small neutral XIC request/trace model, teach the RAW adapter to execute bounded batches, then refactor alignment ownership/backfill to collect requests per sample and resolve peaks after traces return. Keep process execution and timing in orchestration/backend layers; domain helpers only depend on protocols and neutral models.

**Tech Stack:** Python 3, pytest, NumPy, Thermo RawFileReader via pythonnet, existing `TimingRecorder`, existing 8-RAW validation subset.

---

## Context

Phase 0 timing showed alignment dominates the 8-RAW run. The dominant inner cost is RAW XIC extraction:

- `alignment.build_owners.extract_xic`: 3343 requests, about 56.6 sec in serial inner timing.
- `alignment.owner_backfill.extract_xic`: 3466 requests, about 52.8 sec in serial inner timing.
- `--raw-workers 8` improves wall time, but worker 4 vs 8 already shows diminishing returns. We should keep workers available, but the next useful optimization must reduce work per worker.

External references support the next hypotheses:

- Thermo RawFileReader's official example calls `GetChromatogramData(new IChromatogramSettings[] { settings }, startScan, endScan)`, so the API shape already accepts a settings array: `https://github.com/thermofisherlsms/RawFileReader/blob/main/ExampleProgram/NetCore/Program.cs`
- ThermoRawFileParser exposes `xic` as "one or more chromatograms" from JSON input, which supports the idea that multiple XIC traces can be requested as one logical operation: `https://github.com/CompOmics/ThermoRawFileParser`
- MZmine and OpenMS build chromatographic features from per-run MS1 scan/mass structures, but that is a larger algorithmic change. We should treat scan-level indexing as a later prototype, not the first production change: `https://mzmine.github.io/mzmine_documentation/module_docs/lc-ms_featdet/featdet_adap_chromatogram_builder/adap-chromatogram-builder.html`, `https://www.openms.org/documentation/html/classOpenMS_1_1MassTraceDetection.html`

## Decision

Prioritize equivalent optimizations first:

1. Batch XIC requests through the RAW adapter and prove single-request equivalence.
2. Add request census metrics so cache and locality assumptions are measured, not guessed.
3. Use batching in `build_sample_local_owners()` and `build_owner_backfill_cells()` while preserving output order and TSV hashes.
4. Consider exact-cache and request ordering only after request census shows meaningful reuse or locality.
5. Keep scan-level materialized indexes as a separate spike because they can alter trace construction semantics.

Non-equivalent behavior remains explicit opt-in only. The existing `--owner-backfill-min-detected-samples` fast mode stays separate from this plan.

## File Structure

- Create: `xic_extractor/xic_models.py`
  - Owns neutral `XICRequest` and `XICTrace` dataclasses.
  - Must not import RAW reader, CLI, process backend, workbook, or GUI modules.
- Modify: `xic_extractor/raw_reader.py`
  - Adds `RawFileHandle.extract_xic_many()`.
  - Tracks `raw_chromatogram_call_count` by incrementing once per `GetChromatogramData()` call.
  - Keeps `extract_xic()` as the compatibility wrapper.
- Modify: `xic_extractor/alignment/ownership.py`
  - Adds batch-aware request collection for sample-local owner building.
  - Keeps domain behavior independent of process backend and RAW reader implementation.
- Modify: `xic_extractor/alignment/owner_backfill.py`
  - Adds batch-aware request collection for owner-centered backfill.
  - Preserves `owner_backfill_min_detected_samples` semantics.
- Modify: `xic_extractor/alignment/pipeline.py`
  - Keeps timing aggregation and `_TimedRawSource` metrics accurate for both single and batch extraction.
- Modify: `xic_extractor/alignment/process_backend.py`
  - Makes worker-side timing source expose `extract_xic_many()` when the underlying source supports it.
  - Ensures payloads remain pickleable.
- Modify: `scripts/run_alignment.py`
  - Adds an explicit public switch only after the batch path is implemented and tested.
  - Proposed CLI: `--raw-xic-batch-size N`, default `1` in the first implementation commit.
- Create: `scripts/validate_raw_xic_batch_equivalence.py`
  - Validation-only CLI for real RAW micro-smoke before alignment refactors.
  - Reads the discovery batch index, selects real candidate mz/RT windows, and compares single vs batch RAW traces.
- Test: `tests/test_xic_models.py`
- Test: `tests/test_raw_reader.py`
- Test: `tests/test_alignment_ownership.py`
- Test: `tests/test_alignment_owner_backfill.py`
- Test: `tests/test_alignment_pipeline.py`
- Test: `tests/test_alignment_process_backend.py`
- Test: `tests/test_run_alignment.py`

## Acceptance Criteria

- Unit tests prove `extract_xic_many([request])` matches `extract_xic(...)`.
- Unit tests prove multiple requests sharing a scan window call `GetChromatogramData()` once with multiple settings.
- Unit tests prove mixed scan windows return traces in original request order.
- Ownership and owner-backfill tests prove batch-capable sources reduce source method calls without changing cells, assignments, or ordering.
- Process-backend tests prove the batch path is spawn/pickle safe without requiring real RAW files.
- 8-RAW validation with full backfill and `--raw-workers 8` produces matching machine TSV hashes for:
  - `alignment_review.tsv`
  - `alignment_matrix.tsv`
  - `alignment_cells.tsv`
- Timing output reports both request count and API call count:
  - `extract_xic_count`
  - `extract_xic_batch_count`
  - `point_count`
- Stop and do not enable batching by default if real RAW single-vs-batch traces differ beyond exact array equality for sampled requests.

---

### Task 1: Add Neutral XIC Models

**Files:**
- Create: `xic_extractor/xic_models.py`
- Create: `tests/test_xic_models.py`

- [ ] **Step 1: Write the failing tests**

```python
import numpy as np

from xic_extractor.xic_models import XICRequest, XICTrace


def test_xic_request_rejects_invalid_bounds() -> None:
    try:
        XICRequest(mz=258.0, rt_min=10.0, rt_max=8.0, ppm_tol=20.0)
    except ValueError as exc:
        assert "rt_min must be <= rt_max" in str(exc)
    else:
        raise AssertionError("XICRequest accepted an inverted RT window")


def test_xic_trace_normalizes_arrays_to_float() -> None:
    trace = XICTrace.from_arrays([8.1, 8.2], [10, 20])

    assert isinstance(trace.rt, np.ndarray)
    assert isinstance(trace.intensity, np.ndarray)
    assert trace.rt.dtype == float
    assert trace.intensity.dtype == float
    assert trace.rt.tolist() == [8.1, 8.2]
    assert trace.intensity.tolist() == [10.0, 20.0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
uv run pytest tests\test_xic_models.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'xic_extractor.xic_models'`.

- [ ] **Step 3: Implement the model**

```python
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class XICRequest:
    mz: float
    rt_min: float
    rt_max: float
    ppm_tol: float

    def __post_init__(self) -> None:
        if self.rt_min > self.rt_max:
            raise ValueError("rt_min must be <= rt_max")
        if self.ppm_tol <= 0:
            raise ValueError("ppm_tol must be > 0")


@dataclass(frozen=True)
class XICTrace:
    rt: NDArray[np.float64]
    intensity: NDArray[np.float64]

    @classmethod
    def empty(cls) -> "XICTrace":
        return cls(np.array([], dtype=float), np.array([], dtype=float))

    @classmethod
    def from_arrays(cls, rt: object, intensity: object) -> "XICTrace":
        rt_array = np.asarray(rt, dtype=float)
        intensity_array = np.asarray(intensity, dtype=float)
        if (
            rt_array.ndim != 1
            or intensity_array.ndim != 1
            or rt_array.shape != intensity_array.shape
        ):
            raise ValueError("XIC trace arrays must be matching 1D arrays")
        return cls(rt_array, intensity_array)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
uv run pytest tests\test_xic_models.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor\xic_models.py tests\test_xic_models.py
git commit -m "feat: add neutral xic request models"
```

---

### Task 2: Add RawFileHandle.extract_xic_many

**Files:**
- Modify: `xic_extractor/raw_reader.py`
- Modify: `tests/test_raw_reader.py`

- [ ] **Step 1: Write failing batch RAW adapter tests**

Append these tests near existing `extract_xic` tests in `tests/test_raw_reader.py`:

```python
def test_extract_xic_many_batches_shared_scan_window() -> None:
    from xic_extractor.raw_reader import RawFileHandle
    from xic_extractor.xic_models import XICRequest

    raw = _FakeRaw(
        chromatogram=_FakeChromatogram(
            positions=[[8.1, 8.2], [8.1, 8.2]],
            intensities=[[10.0, 20.0], [30.0, 40.0]],
        )
    )
    handle = RawFileHandle(raw, _fake_thermo(raw))

    traces = handle.extract_xic_many(
        (
            XICRequest(mz=258.0, rt_min=8.0, rt_max=10.0, ppm_tol=20.0),
            XICRequest(mz=259.0, rt_min=8.0, rt_max=10.0, ppm_tol=20.0),
        )
    )

    assert len(traces) == 2
    assert traces[0].rt.tolist() == [8.1, 8.2]
    assert traces[0].intensity.tolist() == [10.0, 20.0]
    assert traces[1].rt.tolist() == [8.1, 8.2]
    assert traces[1].intensity.tolist() == [30.0, 40.0]
    assert raw.chromatogram_calls == [((1, 2), 2)]
    assert handle.raw_chromatogram_call_count == 1


def test_extract_xic_many_preserves_order_for_mixed_scan_windows() -> None:
    from xic_extractor.raw_reader import RawFileHandle
    from xic_extractor.xic_models import XICRequest

    raw = _FakeRaw(
        chromatogram_by_window={
            (1, 2): _FakeChromatogram([[8.1]], [[10.0]]),
            (2, 2): _FakeChromatogram([[8.2]], [[20.0]]),
        }
    )
    handle = RawFileHandle(raw, _fake_thermo(raw))

    traces = handle.extract_xic_many(
        (
            XICRequest(mz=258.0, rt_min=8.0, rt_max=10.0, ppm_tol=20.0),
            XICRequest(mz=259.0, rt_min=8.5, rt_max=10.0, ppm_tol=20.0),
            XICRequest(mz=260.0, rt_min=8.0, rt_max=10.0, ppm_tol=20.0),
        )
    )

    assert [trace.intensity.tolist() for trace in traces] == [[10.0], [20.0], [10.0]]
    assert raw.chromatogram_calls == [((1, 2), 2), ((2, 2), 1)]
    assert handle.raw_chromatogram_call_count == 2
```

Update `_FakeChromatogram` and `_FakeRaw` in the same file so the tests can express multiple chromatograms:

```python
class _FakeChromatogram:
    def __init__(self, positions, intensities) -> None:
        if positions and not isinstance(positions[0], list):
            positions = [positions]
        if intensities and not isinstance(intensities[0], list):
            intensities = [intensities]
        self.PositionsArray = positions
        self.IntensitiesArray = intensities


class _FakeRaw:
    def __init__(
        self,
        *,
        chromatogram: _FakeChromatogram | None = None,
        chromatogram_by_window: dict[tuple[int, int], _FakeChromatogram] | None = None,
        filters: dict[int, object] | None = None,
        scans: dict[int, object] | None = None,
        scan_errors: dict[int, Exception] | None = None,
    ) -> None:
        self.disposed = False
        self.chromatogram = chromatogram or _FakeChromatogram([8.1], [10.0])
        self.chromatogram_by_window = chromatogram_by_window or {}
        self.chromatogram_calls: list[tuple[tuple[int, int], int]] = []
        self.filters = filters or {}
        self.scans = scans or {}
        self.scan_errors = scan_errors or {}

    def GetChromatogramData(self, settings, start_scan, end_scan):
        self.chromatogram_calls.append(((start_scan, end_scan), len(settings)))
        return self.chromatogram_by_window.get((start_scan, end_scan), self.chromatogram)
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
uv run pytest tests\test_raw_reader.py::test_extract_xic_many_batches_shared_scan_window tests\test_raw_reader.py::test_extract_xic_many_preserves_order_for_mixed_scan_windows -q
```

Expected: FAIL with `AttributeError: 'RawFileHandle' object has no attribute 'extract_xic_many'`.

- [ ] **Step 3: Implement `extract_xic_many`**

Add imports:

```python
from collections import defaultdict
from collections.abc import Sequence

from xic_extractor.xic_models import XICRequest, XICTrace
```

Replace `extract_xic()` with a compatibility wrapper and add the batch method:

```python
    @property
    def raw_chromatogram_call_count(self) -> int:
        return self._raw_chromatogram_call_count

    def extract_xic(
        self, mz: float, rt_min: float, rt_max: float, ppm_tol: float
    ) -> tuple[np.ndarray, np.ndarray]:
        trace = self.extract_xic_many(
            (XICRequest(mz=mz, rt_min=rt_min, rt_max=rt_max, ppm_tol=ppm_tol),)
        )[0]
        return trace.rt, trace.intensity

    def extract_xic_many(
        self, requests: Sequence[XICRequest]
    ) -> tuple[XICTrace, ...]:
        if not requests:
            return ()
        grouped: dict[tuple[int, int], list[tuple[int, Any]]] = defaultdict(list)
        for index, request in enumerate(requests):
            start_scan = self._raw_file.ScanNumberFromRetentionTime(request.rt_min)
            end_scan = self._raw_file.ScanNumberFromRetentionTime(request.rt_max)
            settings = self._build_chromatogram_settings(request.mz, request.ppm_tol)
            grouped[(start_scan, end_scan)].append((index, settings))

        traces: list[XICTrace | None] = [None] * len(requests)
        for (start_scan, end_scan), indexed_settings in grouped.items():
            settings = [item[1] for item in indexed_settings]
            self._raw_chromatogram_call_count += 1
            data = self._raw_file.GetChromatogramData(settings, start_scan, end_scan)
            for offset, (original_index, _settings) in enumerate(indexed_settings):
                positions = _item_or_empty(data.PositionsArray, offset)
                intensities = _item_or_empty(data.IntensitiesArray, offset)
                if len(intensities) == 0:
                    traces[original_index] = XICTrace.empty()
                else:
                    traces[original_index] = XICTrace.from_arrays(
                        positions,
                        intensities,
                    )
        if any(trace is None for trace in traces):
            raise RawReaderError("Thermo RAW batch extraction returned incomplete traces")
        return tuple(trace for trace in traces if trace is not None)
```

Initialize the counter in `RawFileHandle.__init__()`:

```python
        self._raw_chromatogram_call_count = 0
```

Add helper near `_first_or_empty`:

```python
def _item_or_empty(values: object, index: int) -> object:
    try:
        return values[index]  # type: ignore[index]
    except (IndexError, TypeError):
        return []
```

- [ ] **Step 4: Run adapter tests**

Run:

```powershell
uv run pytest tests\test_raw_reader.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor\raw_reader.py tests\test_raw_reader.py
git commit -m "feat: batch raw xic extraction"
```

---

### Task 3: Real RAW Batch Micro-Smoke

**Files:**
- Create: `scripts/validate_raw_xic_batch_equivalence.py`

- [ ] **Step 1: Create the validation script**

```python
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from xic_extractor.alignment.csv_io import (
    read_discovery_batch_index,
    read_discovery_candidates_csv,
)
from xic_extractor.raw_reader import open_raw
from xic_extractor.xic_models import XICRequest, XICTrace


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate Thermo RAW XIC single-vs-batch equivalence."
    )
    parser.add_argument("--discovery-batch-index", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--dll-dir", type=Path, required=True)
    parser.add_argument("--sample-count", type=int, default=1)
    parser.add_argument("--request-count", type=int, default=6)
    parser.add_argument("--rt-window-min", type=float, default=0.5)
    parser.add_argument("--ppm", type=float, default=20.0)
    args = parser.parse_args(argv)

    batch = read_discovery_batch_index(args.discovery_batch_index)
    checked_samples = 0
    checked_requests = 0
    raw_call_total = 0
    for sample_stem in batch.sample_order:
        if checked_samples >= args.sample_count:
            break
        raw_path = _raw_path(args.raw_dir, batch.raw_files[sample_stem], sample_stem)
        if not raw_path.exists():
            continue
        candidates = read_discovery_candidates_csv(batch.candidate_csvs[sample_stem])
        requests = _candidate_requests(
            candidates,
            request_count=args.request_count,
            rt_window_min=args.rt_window_min,
            ppm=args.ppm,
        )
        if len(requests) < 2:
            continue
        with open_raw(raw_path, args.dll_dir) as raw:
            _assert_single_request_equivalence(raw, requests)
            _assert_same_window_batch_equivalence(raw, requests)
            raw_call_total += raw.raw_chromatogram_call_count
        checked_samples += 1
        checked_requests += len(requests)

    if checked_samples == 0:
        raise SystemExit("No RAW samples with enough discovery candidates were checked")
    print(
        "PASS raw_xic_batch_equivalence "
        f"samples={checked_samples} requests={checked_requests} "
        f"raw_chromatogram_call_count={raw_call_total}"
    )
    return 0


def _raw_path(raw_dir: Path, raw_file: Path | None, sample_stem: str) -> Path:
    if raw_file is not None and str(raw_file):
        return raw_dir / raw_file.name
    return raw_dir / f"{sample_stem}.raw"


def _candidate_requests(
    candidates,
    *,
    request_count: int,
    rt_window_min: float,
    ppm: float,
) -> tuple[XICRequest, ...]:
    requests: list[XICRequest] = []
    for candidate in candidates:
        rt = (
            candidate.ms1_apex_rt
            if candidate.ms1_apex_rt is not None
            else candidate.best_seed_rt
        )
        requests.append(
            XICRequest(
                mz=float(candidate.precursor_mz),
                rt_min=rt - rt_window_min,
                rt_max=rt + rt_window_min,
                ppm_tol=ppm,
            )
        )
        if len(requests) >= request_count:
            break
    return tuple(requests)


def _assert_single_request_equivalence(raw, requests: tuple[XICRequest, ...]) -> None:
    for request in requests:
        direct = _trace_from_pair(
            raw.extract_xic(
                request.mz,
                request.rt_min,
                request.rt_max,
                request.ppm_tol,
            )
        )
        batched = raw.extract_xic_many((request,))[0]
        _assert_trace_equal(direct, batched, context=f"single {request}")


def _assert_same_window_batch_equivalence(
    raw,
    requests: tuple[XICRequest, ...],
) -> None:
    window = requests[0]
    same_window = tuple(
        XICRequest(
            mz=request.mz,
            rt_min=window.rt_min,
            rt_max=window.rt_max,
            ppm_tol=request.ppm_tol,
        )
        for request in requests[: min(4, len(requests))]
    )
    direct = tuple(
        _trace_from_pair(
            raw.extract_xic(
                request.mz,
                request.rt_min,
                request.rt_max,
                request.ppm_tol,
            )
        )
        for request in same_window
    )
    batched = raw.extract_xic_many(same_window)
    for index, (left, right) in enumerate(zip(direct, batched, strict=True)):
        _assert_trace_equal(left, right, context=f"same-window index={index}")


def _trace_from_pair(pair) -> XICTrace:
    rt, intensity = pair
    return XICTrace.from_arrays(rt, intensity)


def _assert_trace_equal(left: XICTrace, right: XICTrace, *, context: str) -> None:
    if not np.array_equal(left.rt, right.rt) or not np.array_equal(
        left.intensity,
        right.intensity,
    ):
        raise SystemExit(f"RAW XIC batch mismatch: {context}")


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run real RAW micro-smoke before touching alignment domain helpers**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run python scripts\validate_raw_xic_batch_equivalence.py --discovery-batch-index output\discovery\timing_phase0_8raw\discovery_batch_index.csv --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" --dll-dir "C:\Xcalibur\system\programs" --sample-count 1 --request-count 6 --rt-window-min 0.5 --ppm 20
```

Expected: prints `PASS raw_xic_batch_equivalence ... raw_chromatogram_call_count=...`.

- [ ] **Step 3: Stop if real RAW semantics differ**

If the command reports `RAW XIC batch mismatch`, stop. Do not continue to alignment batching. Record the failing sample/request and either keep `extract_xic()` on the old direct path or redesign the adapter around the actual Thermo return shape.

- [ ] **Step 4: Commit**

```powershell
git add scripts\validate_raw_xic_batch_equivalence.py
git commit -m "test: add raw xic batch equivalence smoke"
```

---

### Task 4: Add Batch Request Census Metrics

**Files:**
- Modify: `xic_extractor/alignment/pipeline.py`
- Modify: `xic_extractor/alignment/process_backend.py`
- Modify: `tests/test_alignment_pipeline.py`
- Modify: `tests/test_alignment_process_backend.py`

- [ ] **Step 1: Write failing metrics tests**

Add to `tests/test_alignment_pipeline.py` near existing inner timing tests:

```python
def test_timed_raw_source_records_batch_calls() -> None:
    import xic_extractor.alignment.pipeline as pipeline_module
    from xic_extractor.xic_models import XICRequest, XICTrace

    class BatchSource:
        def __init__(self) -> None:
            self.raw_chromatogram_call_count = 0

        def extract_xic_many(self, requests):
            self.raw_chromatogram_call_count += 1
            return tuple(
                XICTrace.from_arrays([request.rt_min], [request.mz])
                for request in requests
            )

        def extract_xic(self, mz, rt_min, rt_max, ppm_tol):
            self.raw_chromatogram_call_count += 1
            return [rt_min], [mz]

    stats = pipeline_module._RawSourceTimingStats(
        sample_stem="Sample_A",
        stage="alignment.build_owners.extract_xic",
    )
    source = pipeline_module._TimedRawSource(BatchSource(), stats=stats)

    traces = source.extract_xic_many(
        (
            XICRequest(mz=258.0, rt_min=8.0, rt_max=9.0, ppm_tol=20.0),
            XICRequest(mz=259.0, rt_min=8.0, rt_max=9.0, ppm_tol=20.0),
        )
    )

    assert [trace.intensity.tolist() for trace in traces] == [[258.0], [259.0]]
    assert stats.extract_xic_count == 2
    assert stats.extract_xic_batch_count == 1
    assert stats.raw_chromatogram_call_count == 1
    assert stats.point_count == 2
```

Add to `tests/test_alignment_process_backend.py`:

```python
def test_timed_process_raw_source_records_batch_calls() -> None:
    import xic_extractor.alignment.process_backend as process_module
    from xic_extractor.xic_models import XICRequest, XICTrace

    class BatchSource:
        def __init__(self) -> None:
            self.raw_chromatogram_call_count = 0

        def extract_xic_many(self, requests):
            self.raw_chromatogram_call_count += 1
            return tuple(
                XICTrace.from_arrays([request.rt_min], [request.mz])
                for request in requests
            )

        def extract_xic(self, mz, rt_min, rt_max, ppm_tol):
            self.raw_chromatogram_call_count += 1
            return [rt_min], [mz]

    stats = process_module._TimedProcessStats(sample_stem="Sample_A")
    source = process_module._TimedProcessRawSource(BatchSource(), stats=stats)

    traces = source.extract_xic_many(
        (
            XICRequest(mz=258.0, rt_min=8.0, rt_max=9.0, ppm_tol=20.0),
            XICRequest(mz=259.0, rt_min=8.0, rt_max=9.0, ppm_tol=20.0),
        )
    )

    assert [trace.intensity.tolist() for trace in traces] == [[258.0], [259.0]]
    assert stats.extract_xic_count == 2
    assert stats.extract_xic_batch_count == 1
    assert stats.raw_chromatogram_call_count == 1
    assert stats.point_count == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
uv run pytest tests\test_alignment_pipeline.py::test_timed_raw_source_records_batch_calls tests\test_alignment_process_backend.py::test_timed_process_raw_source_records_batch_calls -q
```

Expected: FAIL because `extract_xic_batch_count` and `extract_xic_many` are missing.

- [ ] **Step 3: Implement stats**

In both `_ExtractionStats` and worker stats dataclasses, add:

```python
    extract_xic_batch_count: int = 0
```

In single-request timing wrappers, increment both request count and batch count:

```python
            self._stats.extract_xic_count += 1
            self._stats.extract_xic_batch_count += 1
            self._stats.point_count += len(intensity)
```

Add batch wrapper method:

```python
    def extract_xic_many(self, requests):
        requests = tuple(requests)
        if hasattr(self._source, "extract_xic_many"):
            raw_call_count_before = _raw_chromatogram_call_count(self._source)
            start = self._timer()
            try:
                traces = tuple(self._source.extract_xic_many(requests))
            finally:
                self._stats.elapsed_sec += self._timer() - start
            traces = self._source.extract_xic_many(requests)
            self._stats.extract_xic_count += len(requests)
            self._stats.extract_xic_batch_count += 1 if requests else 0
            self._stats.point_count += sum(len(trace.intensity) for trace in traces)
            self._stats.raw_chromatogram_call_count += _raw_call_delta(
                raw_call_count_before,
                _raw_chromatogram_call_count(self._source),
            )
            return traces
        traces = []
        for request in requests:
            rt, intensity = self.extract_xic(
                request.mz,
                request.rt_min,
                request.rt_max,
                request.ppm_tol,
            )
            traces.append(XICTrace.from_arrays(rt, intensity))
        return tuple(traces)
```

Add helper functions in both `pipeline.py` and `process_backend.py`:

```python
def _raw_chromatogram_call_count(source: object) -> int | None:
    value = getattr(source, "raw_chromatogram_call_count", None)
    if isinstance(value, int):
        return value
    return None


def _raw_call_delta(before: int | None, after: int | None) -> int:
    if before is None or after is None:
        return 0
    return max(0, after - before)
```

When recording timing metrics, include:

```python
"extract_xic_batch_count": stats.extract_xic_batch_count,
"raw_chromatogram_call_count": stats.raw_chromatogram_call_count,
```

- [ ] **Step 4: Run metrics tests**

Run:

```powershell
uv run pytest tests\test_alignment_pipeline.py::test_timed_raw_source_records_batch_calls tests\test_alignment_process_backend.py::test_timed_process_raw_source_records_batch_calls -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor\alignment\pipeline.py xic_extractor\alignment\process_backend.py tests\test_alignment_pipeline.py tests\test_alignment_process_backend.py
git commit -m "perf: record raw xic call counts"
```

---

### Task 5: Batch Sample-Local Owner Build

**Files:**
- Modify: `xic_extractor/alignment/ownership.py`
- Modify: `tests/test_alignment_ownership.py`

- [ ] **Step 1: Write failing ownership batch test**

Add to `tests/test_alignment_ownership.py`:

```python
def test_build_sample_local_owners_uses_batch_source_when_available() -> None:
    from xic_extractor.xic_models import XICTrace

    class BatchSource:
        def __init__(self) -> None:
            self.batch_sizes: list[int] = []

        def extract_xic_many(self, requests):
            requests = tuple(requests)
            self.batch_sizes.append(len(requests))
            return tuple(
                XICTrace.from_arrays([request.rt_min, request.rt_max], [0.0, 100.0])
                for request in requests
            )

        def extract_xic(self, mz, rt_min, rt_max, ppm_tol):
            raise AssertionError("batch-capable source should not call extract_xic")

    source = BatchSource()
    candidates = (
        _candidate("c1", "Sample_A", precursor_mz=258.0, rt=8.0),
        _candidate("c2", "Sample_A", precursor_mz=259.0, rt=8.1),
    )

    result = build_sample_local_owners(
        candidates,
        raw_sources={"Sample_A": source},
        alignment_config=AlignmentConfig(),
        peak_config=ExtractionConfig(),
        peak_resolver=_always_peak_at_seed,
        raw_xic_batch_size=64,
    )

    assert source.batch_sizes == [2]
    assert len(result.assignments) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
uv run pytest tests\test_alignment_ownership.py::test_build_sample_local_owners_uses_batch_source_when_available -q
```

Expected: FAIL because ownership still calls `extract_xic()`.

- [ ] **Step 3: Refactor owner build request flow**

Add imports:

```python
from xic_extractor.xic_models import XICRequest, XICTrace
```

Replace the direct tuple comprehension in `build_sample_local_owners()` with a batch resolver:

```python
    if raw_xic_batch_size < 1:
        raise ValueError("raw_xic_batch_size must be >= 1")
    outcomes = _resolve_candidates(
        candidates,
        raw_sources,
        alignment_config,
        peak_config,
        active_peak_resolver,
        raw_xic_batch_size,
    )
```

Add the keyword to the `build_sample_local_owners()` signature:

```python
    raw_xic_batch_size: int = 1,
```

Add helper:

```python
def _resolve_candidates(
    candidates: Sequence[Any],
    raw_sources: Mapping[str, OwnershipXICSource],
    alignment_config: AlignmentConfig,
    peak_config: ExtractionConfig,
    peak_resolver: PeakResolver,
    raw_xic_batch_size: int,
) -> tuple[_ResolutionOutcome, ...]:
    outcomes: list[_ResolutionOutcome | None] = [None] * len(candidates)
    requests_by_sample: dict[str, list[tuple[int, Any, float, XICRequest]]] = defaultdict(list)
    for index, candidate in enumerate(candidates):
        sample_stem = str(candidate.sample_stem)
        source = raw_sources.get(sample_stem)
        if source is None:
            outcomes[index] = _unresolved_outcome(candidate, "missing_raw_source")
            continue
        seed_rt = _candidate_seed_rt(candidate)
        rt_min = seed_rt - alignment_config.max_rt_sec / 60.0
        rt_max = seed_rt + alignment_config.max_rt_sec / 60.0
        requests_by_sample[sample_stem].append(
            (
                index,
                candidate,
                seed_rt,
                XICRequest(
                    mz=float(candidate.precursor_mz),
                    rt_min=rt_min,
                    rt_max=rt_max,
                    ppm_tol=alignment_config.preferred_ppm,
                ),
            )
        )
    for sample_stem, sample_requests in requests_by_sample.items():
        source = raw_sources[sample_stem]
        for chunk in _chunked(tuple(sample_requests), raw_xic_batch_size):
            traces = _extract_many(source, tuple(item[3] for item in chunk))
            for (index, candidate, seed_rt, _request), trace in zip(chunk, traces):
                outcomes[index] = _resolve_candidate_trace(
                    candidate,
                    seed_rt,
                    trace,
                    peak_config,
                    peak_resolver,
                )
    return tuple(outcome for outcome in outcomes if outcome is not None)
```

Split the post-extraction part of `_resolve_candidate()` into:

```python
def _resolve_candidate_trace(
    candidate: Any,
    seed_rt: float,
    trace: XICTrace,
    peak_config: ExtractionConfig,
    peak_resolver: PeakResolver,
) -> _ResolutionOutcome:
    rt_array, intensity_array = _validated_trace_arrays(trace.rt, trace.intensity)
    peak = peak_resolver(candidate, rt_array, intensity_array, peak_config, seed_rt)
    if peak is None:
        return _unresolved_outcome(candidate, "peak_not_found")
    return _ResolutionOutcome(
        resolved=_ResolvedCandidate(
            candidate=candidate,
            event=_identity_event(candidate, seed_rt=seed_rt),
            apex_rt=peak.rt,
            peak_start_rt=peak.peak_start,
            peak_end_rt=peak.peak_end,
            area=peak.area,
            height=peak.intensity,
        ),
        unresolved=None,
    )
```

Add fallback:

```python
def _extract_many(
    source: OwnershipXICSource,
    requests: tuple[XICRequest, ...],
) -> tuple[XICTrace, ...]:
    if hasattr(source, "extract_xic_many"):
        return tuple(source.extract_xic_many(requests))  # type: ignore[attr-defined]
    traces: list[XICTrace] = []
    for request in requests:
        rt, intensity = source.extract_xic(
            request.mz,
            request.rt_min,
            request.rt_max,
            request.ppm_tol,
        )
        traces.append(XICTrace.from_arrays(rt, intensity))
    return tuple(traces)


def _chunked(
    items: tuple[Any, ...],
    chunk_size: int,
) -> tuple[tuple[Any, ...], ...]:
    if chunk_size < 1:
        raise ValueError("raw_xic_batch_size must be >= 1")
    return tuple(
        items[index : index + chunk_size]
        for index in range(0, len(items), chunk_size)
    )
```

- [ ] **Step 4: Run ownership tests**

Run:

```powershell
uv run pytest tests\test_alignment_ownership.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor\alignment\ownership.py tests\test_alignment_ownership.py
git commit -m "perf: batch sample-local owner xic extraction"
```

---

### Task 6: Batch Owner Backfill

**Files:**
- Modify: `xic_extractor/alignment/owner_backfill.py`
- Modify: `tests/test_alignment_owner_backfill.py`

- [ ] **Step 1: Write failing owner-backfill batch test**

Add to `tests/test_alignment_owner_backfill.py`:

```python
def test_owner_backfill_uses_batch_source_when_available() -> None:
    from xic_extractor.xic_models import XICTrace

    class BatchSource:
        def __init__(self) -> None:
            self.batch_sizes: list[int] = []

        def extract_xic_many(self, requests):
            requests = tuple(requests)
            self.batch_sizes.append(len(requests))
            return tuple(
                XICTrace.from_arrays([request.rt_min, request.rt_max], [0.0, 100.0])
                for request in requests
            )

        def extract_xic(self, mz, rt_min, rt_max, ppm_tol):
            raise AssertionError("batch-capable source should not call extract_xic")

    source_b = BatchSource()
    source_c = BatchSource()
    features = (
        _feature("F1", owners=("Sample_A",), mz=258.0, rt=8.0),
        _feature("F2", owners=("Sample_A",), mz=259.0, rt=8.1),
    )

    cells = build_owner_backfill_cells(
        features,
        sample_order=("Sample_A", "Sample_B", "Sample_C"),
        raw_sources={"Sample_B": source_b, "Sample_C": source_c},
        alignment_config=AlignmentConfig(),
        peak_config=ExtractionConfig(),
        raw_xic_batch_size=64,
    )

    assert source_b.batch_sizes == [2]
    assert source_c.batch_sizes == [2]
    assert [(cell.cluster_id, cell.sample_stem) for cell in cells] == [
        ("F1", "Sample_B"),
        ("F1", "Sample_C"),
        ("F2", "Sample_B"),
        ("F2", "Sample_C"),
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
uv run pytest tests\test_alignment_owner_backfill.py::test_owner_backfill_uses_batch_source_when_available -q
```

Expected: FAIL because owner backfill still calls `extract_xic()`.

- [ ] **Step 3: Refactor owner backfill request flow**

Add imports:

```python
from collections import defaultdict
from xic_extractor.xic_models import XICRequest, XICTrace
```

Add the keyword to the `build_owner_backfill_cells()` signature:

```python
    raw_xic_batch_size: int = 1,
```

Inside `build_owner_backfill_cells()`, validate and collect requests first:

```python
    if raw_xic_batch_size < 1:
        raise ValueError("raw_xic_batch_size must be >= 1")
    pending: dict[str, list[tuple[OwnerAlignedFeature, str, XICRequest]]] = defaultdict(list)
    rt_window_min = alignment_config.max_rt_sec / 60.0
    for feature in features:
        if feature.review_only:
            continue
        detected_samples = {owner.sample_stem for owner in feature.owners}
        if (
            len(detected_samples)
            < alignment_config.owner_backfill_min_detected_samples
        ):
            continue
        for sample_stem in sample_order:
            if sample_stem in detected_samples or sample_stem not in raw_sources:
                continue
            pending[sample_stem].append(
                (
                    feature,
                    sample_stem,
                    XICRequest(
                        mz=feature.family_center_mz,
                        rt_min=feature.family_center_rt - rt_window_min,
                        rt_max=feature.family_center_rt + rt_window_min,
                        ppm_tol=alignment_config.preferred_ppm,
                    ),
                )
            )
```

Resolve in `sample_order` batches, but store results by `(feature_id, sample_stem)` and emit cells in the original feature-major order:

```python
    rescued_by_feature_sample: dict[tuple[str, str], AlignedCell] = {}
    for sample_stem in sample_order:
        sample_requests = pending.get(sample_stem, [])
        if not sample_requests:
            continue
        source = raw_sources[sample_stem]
        for chunk in _chunked(tuple(sample_requests), raw_xic_batch_size):
            traces = _extract_many(source, tuple(item[2] for item in chunk))
            for (feature, requested_sample, _request), trace in zip(chunk, traces):
                cell = _backfill_feature_sample_trace(
                    feature,
                    requested_sample,
                    trace,
                    peak_config=peak_config,
                )
                if cell is not None:
                    rescued_by_feature_sample[
                        (feature.feature_family_id, requested_sample)
                    ] = cell

    for feature in features:
        if feature.review_only:
            continue
        for sample_stem in sample_order:
            cell = rescued_by_feature_sample.get(
                (feature.feature_family_id, sample_stem)
            )
            if cell is not None:
                cells.append(cell)
    return tuple(cells)
```

Split `_backfill_feature_sample()` into a trace resolver:

```python
def _backfill_feature_sample_trace(
    feature: OwnerAlignedFeature,
    sample_stem: str,
    trace: XICTrace,
    *,
    peak_config: ExtractionConfig,
) -> AlignedCell | None:
    try:
        rt_array, intensity_array = _validated_trace_arrays(trace.rt, trace.intensity)
    except ValueError:
        return None
    result = find_peak_and_area(
        rt_array,
        intensity_array,
        peak_config,
        preferred_rt=feature.family_center_rt,
        strict_preferred_rt=False,
    )
    if result.status != "OK" or result.peak is None:
        return None
    peak = result.peak
    return AlignedCell(
        sample_stem=sample_stem,
        cluster_id=feature.feature_family_id,
        status="rescued",
        area=peak.area,
        apex_rt=peak.rt,
        height=peak.intensity,
        peak_start_rt=peak.peak_start,
        peak_end_rt=peak.peak_end,
        rt_delta_sec=(peak.rt - feature.family_center_rt) * 60.0,
        trace_quality="owner_backfill",
        scan_support_score=None,
        source_candidate_id=None,
        source_raw_file=None,
        reason="owner-centered MS1 backfill",
    )
```

Add owner-backfill extraction helpers:

```python
def _extract_many(
    source: OwnerBackfillSource,
    requests: tuple[XICRequest, ...],
) -> tuple[XICTrace, ...]:
    if hasattr(source, "extract_xic_many"):
        return tuple(source.extract_xic_many(requests))  # type: ignore[attr-defined]
    traces: list[XICTrace] = []
    for request in requests:
        rt, intensity = source.extract_xic(
            request.mz,
            request.rt_min,
            request.rt_max,
            request.ppm_tol,
        )
        traces.append(XICTrace.from_arrays(rt, intensity))
    return tuple(traces)


def _chunked(
    items: tuple[object, ...],
    chunk_size: int,
) -> tuple[tuple[object, ...], ...]:
    if chunk_size < 1:
        raise ValueError("raw_xic_batch_size must be >= 1")
    return tuple(
        items[index : index + chunk_size]
        for index in range(0, len(items), chunk_size)
    )
```

- [ ] **Step 4: Run owner-backfill tests**

Run:

```powershell
uv run pytest tests\test_alignment_owner_backfill.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add xic_extractor\alignment\owner_backfill.py tests\test_alignment_owner_backfill.py
git commit -m "perf: batch owner backfill xic extraction"
```

---

### Task 7: Add CLI Gate for Batch Size

**Files:**
- Modify: `scripts/run_alignment.py`
- Modify: `xic_extractor/alignment/pipeline.py`
- Modify: `xic_extractor/alignment/process_backend.py`
- Modify: `tests/test_run_alignment.py`
- Modify: `tests/test_alignment_pipeline.py`

- [ ] **Step 1: Write failing CLI test**

Add to `tests/test_run_alignment.py`:

```python
def test_run_alignment_cli_passes_raw_xic_batch_size(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_run_alignment_pipeline(**kwargs):
        captured.update(kwargs)
        return _alignment_result()

    monkeypatch.setattr(run_alignment, "run_alignment_pipeline", fake_run_alignment_pipeline)

    run_alignment.main(
        [
            "--discovery-batch-index",
            str(_write_batch_index(tmp_path)),
            "--raw-dir",
            str(tmp_path),
            "--dll-dir",
            str(tmp_path),
            "--output-dir",
            str(tmp_path / "out"),
            "--raw-xic-batch-size",
            "64",
        ]
    )

    assert captured["raw_xic_batch_size"] == 64
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
uv run pytest tests\test_run_alignment.py::test_run_alignment_cli_passes_raw_xic_batch_size -q
```

Expected: FAIL because the argument does not exist.

- [ ] **Step 3: Implement CLI and pipeline parameter**

In `scripts/run_alignment.py`, add parser argument:

```python
    parser.add_argument(
        "--raw-xic-batch-size",
        type=_positive_int,
        default=1,
        help=(
            "Maximum XIC requests per RAW API batch. Default 1 preserves the "
            "pre-batch execution shape until real RAW equivalence is accepted."
        ),
    )
```

Pass it to `run_alignment_pipeline()`:

```python
            raw_xic_batch_size=args.raw_xic_batch_size,
```

In `run_alignment_pipeline()`, accept:

```python
    raw_xic_batch_size: int = 1,
```

Validate:

```python
    if raw_xic_batch_size < 1:
        raise ValueError("raw_xic_batch_size must be >= 1")
```

Pass `raw_xic_batch_size` into serial ownership and backfill calls:

```python
                ownership = build_sample_local_owners(
                    candidates,
                    raw_sources=timed_raw_sources,
                    alignment_config=alignment_config,
                    peak_config=peak_config,
                    raw_xic_batch_size=raw_xic_batch_size,
                )
```

```python
                rescued_cells = build_owner_backfill_cells(
                    owner_features,
                    sample_order=batch.sample_order,
                    raw_sources=timed_raw_sources,
                    alignment_config=alignment_config,
                    peak_config=peak_config,
                    raw_xic_batch_size=raw_xic_batch_size,
                )
```

Pass `raw_xic_batch_size` into process backend entry points:

```python
                owner_output = run_owner_build_process(
                    candidates,
                    sample_order=batch.sample_order,
                    raw_paths=raw_paths,
                    dll_dir=dll_dir,
                    alignment_config=alignment_config,
                    peak_config=peak_config,
                    max_workers=raw_workers,
                    raw_xic_batch_size=raw_xic_batch_size,
                )
```

```python
                process_output = run_owner_backfill_process(
                    owner_features,
                    sample_order=batch.sample_order,
                    raw_paths=raw_paths,
                    dll_dir=dll_dir,
                    alignment_config=alignment_config,
                    peak_config=peak_config,
                    max_workers=raw_workers,
                    raw_xic_batch_size=raw_xic_batch_size,
                )
```

Add `raw_xic_batch_size: int` to `OwnerBuildSampleJob` and `OwnerBackfillSampleJob`, and pass it inside worker functions:

```python
            ownership = build_sample_local_owners(
                job.candidates,
                raw_sources={job.sample_stem: timed_raw},
                alignment_config=job.alignment_config,
                peak_config=job.peak_config,
                raw_xic_batch_size=job.raw_xic_batch_size,
            )
```

```python
            cells = build_owner_backfill_cells(
                job.features,
                sample_order=(job.sample_stem,),
                raw_sources={job.sample_stem: timed_raw},
                alignment_config=job.alignment_config,
                peak_config=job.peak_config,
                raw_xic_batch_size=job.raw_xic_batch_size,
            )
```

When constructing jobs, set:

```python
raw_xic_batch_size=raw_xic_batch_size,
```

- [ ] **Step 4: Run CLI tests**

Run:

```powershell
uv run pytest tests\test_run_alignment.py tests\test_alignment_pipeline.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add scripts\run_alignment.py xic_extractor\alignment\pipeline.py xic_extractor\alignment\process_backend.py tests\test_run_alignment.py tests\test_alignment_pipeline.py
git commit -m "feat: gate raw xic batching from alignment cli"
```

---

### Task 8: Real RAW Full-Run Equivalence And Timing Validation

**Files:**
- No production files required.
- Output artifacts under `output\alignment\...` and `output\diagnostics\...` are validation artifacts and should remain untracked unless explicitly requested.

- [ ] **Step 1: Run baseline with batch disabled**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run python scripts\run_alignment.py --discovery-batch-index output\discovery\timing_phase0_8raw\discovery_batch_index.csv --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" --dll-dir "C:\Xcalibur\system\programs" --output-dir output\alignment\timing_phase5_batch1_workers8_8raw --timing-output output\diagnostics\timing_phase5_batch1_workers8_8raw\alignment_timing.json --emit-alignment-cells --raw-workers 8 --raw-xic-batch-size 1
```

Expected: command succeeds. Machine TSV row counts match previous full workers8 baseline.

- [ ] **Step 2: Run candidate batch size**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run python scripts\run_alignment.py --discovery-batch-index output\discovery\timing_phase0_8raw\discovery_batch_index.csv --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" --dll-dir "C:\Xcalibur\system\programs" --output-dir output\alignment\timing_phase5_batch64_workers8_8raw --timing-output output\diagnostics\timing_phase5_batch64_workers8_8raw\alignment_timing.json --emit-alignment-cells --raw-workers 8 --raw-xic-batch-size 64
```

Expected: command succeeds. If Windows process permissions fail inside the sandbox, rerun this same command with explicit escalation approval.

- [ ] **Step 3: Compare machine TSV hashes**

Run:

```powershell
Get-FileHash output\alignment\timing_phase5_batch1_workers8_8raw\alignment_review.tsv, output\alignment\timing_phase5_batch64_workers8_8raw\alignment_review.tsv, output\alignment\timing_phase5_batch1_workers8_8raw\alignment_matrix.tsv, output\alignment\timing_phase5_batch64_workers8_8raw\alignment_matrix.tsv, output\alignment\timing_phase5_batch1_workers8_8raw\alignment_cells.tsv, output\alignment\timing_phase5_batch64_workers8_8raw\alignment_cells.tsv -Algorithm SHA256
```

Expected: paired hashes match for review, matrix, and cells. If any hash differs, stop and inspect the first differing row before continuing.

- [ ] **Step 4: Summarize timing**

Run:

```powershell
uv run python scripts\summarize_timing.py output\diagnostics\timing_phase5_batch1_workers8_8raw\alignment_timing.json output\diagnostics\timing_phase5_batch64_workers8_8raw\alignment_timing.json
```

If `scripts\summarize_timing.py` does not exist yet, use this one-off PowerShell-readable Python command:

```powershell
uv run python -c "import json,sys; [print(p, json.load(open(p, encoding='utf-8')).get('total_elapsed_sec')) for p in sys.argv[1:]]" output\diagnostics\timing_phase5_batch1_workers8_8raw\alignment_timing.json output\diagnostics\timing_phase5_batch64_workers8_8raw\alignment_timing.json
```

Expected: batch64 has lower `raw_chromatogram_call_count` than batch1. Also inspect `extract_xic_batch_count` as a wrapper-level sanity check. Wall time should improve enough to justify the complexity; use 15 percent as the minimum practical threshold on the 8-RAW subset.

- [ ] **Step 5: Commit docs update if validation passes**

Update `docs/superpowers/specs/2026-05-12-untargeted-performance-architecture-spec.md` with:

```markdown
### 2026-05-12 RAW XIC Batch Addendum

Batching RAW XIC requests is accepted as an equivalent optimization when:

- `alignment_review.tsv`, `alignment_matrix.tsv`, and `alignment_cells.tsv` hashes match `--raw-xic-batch-size 1`.
- Timing output shows reduced `raw_chromatogram_call_count`.
- The 8-RAW validation run improves alignment wall time by at least 15%.

The initial CLI default remains `--raw-xic-batch-size 1` until this validation is recorded.
```

Commit:

```powershell
git add docs\superpowers\specs\2026-05-12-untargeted-performance-architecture-spec.md
git commit -m "docs: record raw xic batch validation"
```

---

## Stop Conditions

Stop implementation and report findings if any of these happen:

- Real RAW batch traces do not exactly match single-request traces for the same scan windows.
- Batch output TSV hashes differ from batch-disabled output.
- Timing improves less than 15 percent on the 8-RAW subset after `raw_chromatogram_call_count` drops.
- Process-worker payloads require non-pickleable objects.
- Domain modules need to import `raw_reader`, `pipeline`, `process_backend`, CLI scripts, or diagnostics infrastructure.

## Follow-Up Ideas Not In This Plan

- Exact request cache: add only if request census shows repeated `(sample, mz, rt_min, rt_max, ppm)` keys. Otherwise it adds memory and code without benefit.
- Request sorting by scan locality: add only if batching is equivalent but API calls still stay high because scan windows are fragmented.
- Sample-local MS1 scan index: keep as a separate prototype because it changes the extraction mechanism from vendor XIC calls to local scan traversal. It may become valuable, but it needs its own equivalence suite against vendor XIC traces.

## 2026-05-13 Execution Notes

The plan was executed through the 8-RAW validation subset.

- `batch1`, unsorted `batch64`, sorted `batch64`, and `batch100000` produced
  identical `alignment_review.tsv`, `alignment_matrix.tsv`, and
  `alignment_cells.tsv` hashes.
- Unsorted `batch64` reduced wrapper batch count, but barely reduced true
  Thermo calls.
- Sorting owner-backfill requests by RT window before chunking reduced
  `owner_backfill` Thermo calls from `3466` to `2951` with exact machine TSV
  output.
- `build_owners` stayed at `3343` Thermo calls even at the per-sample batch
  upper bound, so larger batch sizes and request sorting do not solve the main
  bottleneck.
- Direct discovery-field reuse and local MS1 scan-index prototypes are not
  equivalent replacements for vendor XIC output on this subset.

Conclusion: keep the small exact owner-backfill locality sort, but stop
optimizing by batch size alone. The remaining meaningful performance paths need
their own plan because they either change the extraction mechanism or reduce
the owner-build candidate set.

## 2026-05-14 Request Census Follow-Up

The request census diagnostic confirms that this throughput plan did not remove
the alignment pipeline's logical repeated work; it only reduced vendor RAW calls
where scan-window batching was possible.

8-RAW census command:

```powershell
uv run python scripts\analyze_xic_request_locality.py `
  --discovery-batch-index output\discovery\timing_phase0_8raw\discovery_batch_index.csv `
  --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" `
  --dll-dir "C:\Xcalibur\system\programs" `
  --alignment-review output\alignment\timing_phase0_8raw\alignment_review.tsv `
  --alignment-cells output\alignment\timing_phase0_8raw\alignment_cells.tsv `
  --raw-xic-batch-size 64 `
  --near-mz-ppm 20 `
  --near-rt-sec 30 `
  --output-json output\diagnostics\timing_phase0_8raw\xic_request_census_batch64.json
```

Stage-level result:

| Stage | Requests | Exact duplicate excess | Same scan-window excess keys | Near-redundant excess keys | Interpretation |
| --- | ---: | ---: | ---: | ---: | --- |
| `build_owners` | 3,343 | 0 | 0 | 1,102 | No exact cache or scan-window batching opportunity; remaining redundancy is algorithmic/candidate-level. |
| `owner_backfill` | 11,703 | 6 | 6,879 | 6,486 | Batching is real and exact-safe here, but logical request count is still high. |

Conclusion: do not continue tuning `raw_xic_batch_size` for `build_owners`.
The next meaningful performance work should target candidate/family promotion
or an explicit `alignment algorithm v2`; local MS1 scan-index remains a separate
non-equivalent prototype until validated under its own scientific acceptance
criteria.

## Self-Review

- Spec coverage: this plan covers the next equivalent optimization path after Phase 0 timing, while preserving existing worker and backfill gate behavior.
- Boundary check: RAW adapter owns Thermo API calls; domain helpers only use protocols and neutral models; process backend remains orchestration/backend code.
- Placeholder scan: no open implementation placeholders are intentionally left in the task steps.
- Type consistency: all tasks use `XICRequest`, `XICTrace`, `extract_xic_many()`, `extract_xic_count`, `extract_xic_batch_count`, `raw_chromatogram_call_count`, and `point_count` consistently.
