# Untargeted Performance Phase 0 Timing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add low-overhead JSON timing for untargeted discovery and alignment so the next performance decision is based on measured bottlenecks.

**Architecture:** Introduce a focused `xic_extractor.diagnostics.timing` module with a small recorder/context-manager API. Thread an optional recorder through discovery and alignment orchestration only; domain algorithms continue to receive normal data and do not import CLI, GUI, workbook, or process backends. CLI commands create and write timing JSON only when `--timing-output` is provided, keeping default behavior unchanged.

**Tech Stack:** Python 3.10+, stdlib `time.perf_counter`, stdlib `json`, pytest, existing fake RAW sources.

---

## Scope

This plan implements only Phase 0 from:

- `docs/superpowers/specs/2026-05-12-untargeted-performance-architecture-spec.md`

It does not add process workers, change discovery science, change alignment ownership, convert `.raw` files, add Parquet, add Polars, or add plots.

No commit steps are included because the global repo rule says not to commit unless the user explicitly requests it.

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `xic_extractor/diagnostics/__init__.py` | Create | Package marker for diagnostics helpers. |
| `xic_extractor/diagnostics/timing.py` | Create | Timing dataclasses, recorder, context manager, JSON writer. |
| `tests/test_timing.py` | Create | Unit tests for recorder behavior independent of RAW files. |
| `xic_extractor/discovery/pipeline.py` | Modify | Record discovery stage timing and CSV write timing. |
| `tests/test_discovery_pipeline.py` | Modify | Verify discovery stages and metrics with fake RAW sources. |
| `scripts/run_discovery.py` | Modify | Add `--timing-output` and write discovery timing JSON on success. |
| `tests/test_run_discovery.py` | Modify | Verify CLI passes recorder only when requested and writes JSON. |
| `xic_extractor/alignment/pipeline.py` | Modify | Record alignment stage timing around orchestration steps. |
| `tests/test_alignment_pipeline.py` | Modify | Verify alignment stages with monkeypatched pipeline helpers. |
| `scripts/run_alignment.py` | Modify | Add `--timing-output` and write alignment timing JSON on success. |
| `tests/test_run_alignment.py` | Modify | Verify CLI timing JSON behavior. |

## Data Flow

```text
CLI --timing-output path
  -> TimingRecorder("discovery" or "alignment")
  -> run_discovery/run_alignment(..., timing_recorder=recorder)
  -> orchestration wraps each stage with recorder.stage(...)
  -> CLI writes recorder.write_json(path) after successful run
```

Disabled path:

```text
No --timing-output
  -> CLI does not create recorder
  -> pipeline receives None
  -> pipeline uses disabled recorder internally
  -> no JSON file, no output contract changes
```

## Task 1: Timing Recorder Foundation

**Files:**
- Create: `xic_extractor/diagnostics/__init__.py`
- Create: `xic_extractor/diagnostics/timing.py`
- Create: `tests/test_timing.py`

- [ ] **Step 1: Add failing unit tests for the timing recorder**

Create `tests/test_timing.py` with this content:

```python
import json
from pathlib import Path

import pytest

from xic_extractor.diagnostics.timing import TimingRecorder


def test_timing_recorder_records_stage_metrics_and_writes_json(tmp_path: Path) -> None:
    recorder = TimingRecorder("discovery", run_id="run-1", timer=_Timer([10.0, 12.5]))

    with recorder.stage(
        "discover.ms2_seeds",
        sample_stem="Sample_A",
        metrics={"seed_count": 0},
    ) as stage:
        stage.metrics["seed_count"] = 3
        stage.metrics["raw_file"] = Path("Sample_A.raw")

    assert len(recorder.records) == 1
    record = recorder.records[0]
    assert record.stage == "discover.ms2_seeds"
    assert record.sample_stem == "Sample_A"
    assert record.elapsed_sec == pytest.approx(2.5)
    assert record.metrics == {
        "seed_count": 3,
        "raw_file": "Sample_A.raw",
    }

    output_path = tmp_path / "diagnostics" / "timing.json"
    recorder.write_json(output_path)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["run_id"] == "run-1"
    assert payload["pipeline"] == "discovery"
    assert payload["records"] == [
        {
            "sample_stem": "Sample_A",
            "stage": "discover.ms2_seeds",
            "elapsed_sec": pytest.approx(2.5),
            "metrics": {
                "seed_count": 3,
                "raw_file": "Sample_A.raw",
            },
        }
    ]


def test_timing_recorder_records_exception_stage_before_reraising() -> None:
    recorder = TimingRecorder("alignment", run_id="run-2", timer=_Timer([1.0, 1.25]))

    with pytest.raises(ValueError, match="boom"):
        with recorder.stage("alignment.claim_registry"):
            raise ValueError("boom")

    assert len(recorder.records) == 1
    assert recorder.records[0].stage == "alignment.claim_registry"
    assert recorder.records[0].elapsed_sec == pytest.approx(0.25)


def test_timing_recorder_disabled_mode_records_nothing() -> None:
    recorder = TimingRecorder.disabled("discovery", timer=_Timer([1.0, 2.0]))

    with recorder.stage("discover.group_seeds") as stage:
        stage.metrics["group_count"] = 7

    assert recorder.records == ()


def test_timing_recorder_nested_stages_keep_completion_order() -> None:
    recorder = TimingRecorder("alignment", run_id="run-3", timer=_Timer([1.0, 2.0, 3.0, 5.0]))

    with recorder.stage("alignment.outer"):
        with recorder.stage("alignment.inner"):
            pass

    assert [record.stage for record in recorder.records] == [
        "alignment.inner",
        "alignment.outer",
    ]
    assert [record.elapsed_sec for record in recorder.records] == [
        pytest.approx(1.0),
        pytest.approx(4.0),
    ]


class _Timer:
    def __init__(self, values: list[float]) -> None:
        self._values = values
        self._index = 0

    def __call__(self) -> float:
        value = self._values[self._index]
        self._index += 1
        return value
```

- [ ] **Step 2: Run the new timing tests and verify they fail**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_timing.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'xic_extractor.diagnostics'`.

- [ ] **Step 3: Add the diagnostics package marker**

Create `xic_extractor/diagnostics/__init__.py` with this content:

```python
"""Diagnostics helpers for optional runtime instrumentation."""
```

- [ ] **Step 4: Implement the timing recorder**

Create `xic_extractor/diagnostics/timing.py` with this content:

```python
from __future__ import annotations

import json
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

JsonMetric = str | int | float | bool | None


@dataclass(frozen=True)
class TimingRecord:
    stage: str
    elapsed_sec: float
    sample_stem: str = ""
    metrics: dict[str, JsonMetric] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, object]:
        return {
            "sample_stem": self.sample_stem,
            "stage": self.stage,
            "elapsed_sec": self.elapsed_sec,
            "metrics": dict(self.metrics),
        }


@dataclass
class TimingStage:
    metrics: dict[str, JsonMetric] = field(default_factory=dict)


class TimingRecorder:
    def __init__(
        self,
        pipeline: str,
        *,
        run_id: str | None = None,
        enabled: bool = True,
        timer: Callable[[], float] = perf_counter,
    ) -> None:
        self.pipeline = pipeline
        self.run_id = run_id or _default_run_id()
        self.enabled = enabled
        self._timer = timer
        self._records: list[TimingRecord] = []

    @classmethod
    def disabled(
        cls,
        pipeline: str,
        *,
        timer: Callable[[], float] = perf_counter,
    ) -> "TimingRecorder":
        return cls(pipeline, enabled=False, timer=timer)

    @property
    def records(self) -> tuple[TimingRecord, ...]:
        return tuple(self._records)

    @contextmanager
    def stage(
        self,
        stage: str,
        *,
        sample_stem: str = "",
        metrics: Mapping[str, object] | None = None,
    ) -> Iterator[TimingStage]:
        scope = TimingStage(_clean_metrics(metrics or {}))
        if not self.enabled:
            yield scope
            return

        start = self._timer()
        try:
            yield scope
        finally:
            elapsed = self._timer() - start
            self._records.append(
                TimingRecord(
                    stage=stage,
                    elapsed_sec=max(0.0, elapsed),
                    sample_stem=sample_stem,
                    metrics=_clean_metrics(scope.metrics),
                )
            )

    def write_json(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "run_id": self.run_id,
            "pipeline": self.pipeline,
            "records": [record.to_json_dict() for record in self._records],
        }
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return path


def _clean_metrics(metrics: Mapping[str, object]) -> dict[str, JsonMetric]:
    return {str(key): _clean_metric(value) for key, value in metrics.items()}


def _clean_metric(value: object) -> JsonMetric:
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    return str(value)


def _default_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
```

- [ ] **Step 5: Run recorder tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_timing.py -v
```

Expected: PASS.

## Task 2: Discovery Pipeline Timing

**Files:**
- Modify: `xic_extractor/discovery/pipeline.py`
- Modify: `tests/test_discovery_pipeline.py`

- [ ] **Step 1: Add failing discovery timing tests**

Add this import to `tests/test_discovery_pipeline.py`:

```python
from xic_extractor.diagnostics.timing import TimingRecorder
```

Add these tests before `test_pipeline_uses_injected_raw_opener_with_dll_dir_and_closes_context`:

```python
def test_single_raw_pipeline_records_discovery_timing_stages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = _FakeRawHandle(
        [_scan_event(scan_number=101, rt=7.80, product_intensity=3000.0)],
        rt=np.array([7.70, 7.80, 8.00]),
        intensity=np.array([10.0, 600.0, 20.0]),
    )
    monkeypatch.setattr(
        "xic_extractor.discovery.ms1_backfill.find_peak_and_area",
        lambda *args, **kwargs: _ok_peak(
            rt=7.80,
            intensity=600.0,
            area=42.0,
            start=7.70,
            end=8.00,
        ),
    )
    recorder = TimingRecorder("discovery", run_id="test-discovery")

    run_discovery(
        tmp_path / "Sample.raw",
        output_dir=tmp_path / "out",
        settings=_settings(),
        peak_config=_peak_config(tmp_path),
        raw_opener=lambda path, dll_dir: raw,
        timing_recorder=recorder,
    )

    records_by_stage = {record.stage: record for record in recorder.records}
    assert set(records_by_stage) == {
        "discover.ms2_seeds",
        "discover.group_seeds",
        "discover.ms1_backfill",
        "discover.feature_family",
        "discover.write_candidates_csv",
        "discover.write_review_csv",
    }
    assert records_by_stage["discover.ms2_seeds"].sample_stem == "Sample"
    assert records_by_stage["discover.ms2_seeds"].metrics["seed_count"] == 1
    assert records_by_stage["discover.group_seeds"].metrics["group_count"] == 1
    assert records_by_stage["discover.ms1_backfill"].metrics["candidate_count"] == 1
    assert records_by_stage["discover.feature_family"].metrics["candidate_count"] == 1
    assert records_by_stage["discover.write_candidates_csv"].metrics["row_count"] == 1
    assert records_by_stage["discover.write_review_csv"].metrics["row_count"] == 1


def test_batch_pipeline_records_batch_index_timing(tmp_path: Path) -> None:
    raw_path = tmp_path / "Blank.raw"
    raw = _FakeRawHandle(events=[])
    recorder = TimingRecorder("discovery", run_id="test-batch")

    run_discovery_batch(
        (raw_path,),
        output_dir=tmp_path / "out",
        settings=_settings(),
        peak_config=_peak_config(tmp_path),
        raw_opener=lambda path, dll_dir: raw,
        timing_recorder=recorder,
    )

    records_by_stage = {record.stage: record for record in recorder.records}
    assert records_by_stage["discover.write_batch_index"].metrics == {
        "raw_count": 1,
        "row_count": 1,
    }
```

- [ ] **Step 2: Run discovery timing tests and verify they fail**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_discovery_pipeline.py::test_single_raw_pipeline_records_discovery_timing_stages tests/test_discovery_pipeline.py::test_batch_pipeline_records_batch_index_timing -v
```

Expected: FAIL with `TypeError` because `run_discovery()` and `run_discovery_batch()` do not accept `timing_recorder`.

- [ ] **Step 3: Thread the optional recorder through discovery pipeline**

In `xic_extractor/discovery/pipeline.py`, add:

```python
from xic_extractor.diagnostics.timing import TimingRecorder
```

Update `run_discovery()` signature:

```python
def run_discovery(
    raw_path: Path,
    *,
    output_dir: Path,
    settings: DiscoverySettings,
    peak_config: ExtractionConfig,
    raw_opener: RawOpener | None = None,
    timing_recorder: TimingRecorder | None = None,
) -> DiscoveryRunOutputs:
```

Use this body shape:

```python
    opener = raw_opener or _default_raw_opener
    recorder = timing_recorder or TimingRecorder.disabled("discovery")
    sample_stem = raw_path.stem
    discovered = _discover_raw_file(
        raw_path,
        settings=settings,
        peak_config=peak_config,
        raw_opener=opener,
        timing_recorder=recorder,
    )
    with recorder.stage(
        "discover.feature_family",
        sample_stem=sample_stem,
        metrics={"input_count": len(discovered)},
    ) as stage:
        candidates = assign_feature_families(discovered, settings=settings)
        stage.metrics["candidate_count"] = len(candidates)
    return _write_dual_csvs(
        output_dir,
        candidates,
        timing_recorder=recorder,
        sample_stem=sample_stem,
    )
```

Update `run_discovery_batch()` signature:

```python
def run_discovery_batch(
    raw_paths: tuple[Path, ...],
    *,
    output_dir: Path,
    settings: DiscoverySettings,
    peak_config: ExtractionConfig,
    raw_opener: RawOpener | None = None,
    timing_recorder: TimingRecorder | None = None,
) -> DiscoveryBatchOutputs:
```

Inside `run_discovery_batch()`, create `recorder = timing_recorder or TimingRecorder.disabled("discovery")`, pass it into `_discover_raw_file()`, wrap `assign_feature_families()` with a `discover.feature_family` stage in `pipeline.py`, and pass it into `_write_dual_csvs()` and `_write_batch_index()`.

Use this per-RAW loop shape:

```python
    for raw_path in raw_paths:
        sample_stem = raw_path.stem
        discovered = _discover_raw_file(
            raw_path,
            settings=settings,
            peak_config=peak_config,
            raw_opener=opener,
            timing_recorder=recorder,
        )
        with recorder.stage(
            "discover.feature_family",
            sample_stem=sample_stem,
            metrics={"input_count": len(discovered)},
        ) as stage:
            candidates = assign_feature_families(discovered, settings=settings)
            stage.metrics["candidate_count"] = len(candidates)
        sample_output_dir = output_dir / sample_stem
        outputs = _write_dual_csvs(
            sample_output_dir,
            candidates,
            timing_recorder=recorder,
            sample_stem=sample_stem,
        )
```

- [ ] **Step 4: Instrument `_discover_raw_file()`**

Update `_discover_raw_file()` signature:

```python
def _discover_raw_file(
    raw_path: Path,
    *,
    settings: DiscoverySettings,
    peak_config: ExtractionConfig,
    raw_opener: RawOpener,
    timing_recorder: TimingRecorder,
) -> tuple[DiscoveryCandidate, ...]:
```

Replace its body with this structure:

```python
    sample_stem = raw_path.stem
    with raw_opener(raw_path, peak_config.dll_dir) as raw:
        with timing_recorder.stage("discover.ms2_seeds", sample_stem=sample_stem) as stage:
            seeds = collect_strict_nl_seeds(raw, raw_file=raw_path, settings=settings)
            stage.metrics["seed_count"] = len(seeds)
        with timing_recorder.stage("discover.group_seeds", sample_stem=sample_stem) as stage:
            groups = group_discovery_seeds(seeds, settings=settings)
            stage.metrics["group_count"] = len(groups)
        with timing_recorder.stage("discover.ms1_backfill", sample_stem=sample_stem) as stage:
            candidates = backfill_ms1_candidates(
                raw,
                groups,
                settings=settings,
                peak_config=peak_config,
            )
            stage.metrics["candidate_count"] = len(candidates)
        return candidates
```

- [ ] **Step 5: Instrument CSV writes**

Update `_write_dual_csvs()` signature:

```python
def _write_dual_csvs(
    output_dir: Path,
    candidates: tuple[DiscoveryCandidate, ...],
    *,
    timing_recorder: TimingRecorder,
    sample_stem: str,
) -> DiscoveryRunOutputs:
```

Wrap the two writer calls:

```python
        with timing_recorder.stage(
            "discover.write_candidates_csv",
            sample_stem=sample_stem,
            metrics={"row_count": len(candidates)},
        ):
            write_discovery_candidates_csv(candidates_tmp, candidates)
        with timing_recorder.stage(
            "discover.write_review_csv",
            sample_stem=sample_stem,
            metrics={"row_count": len(candidates)},
        ):
            write_discovery_review_csv(review_tmp, candidates)
```

Update `_write_batch_index()` signature:

```python
def _write_batch_index(
    output_path: Path,
    rows: list[dict[str, str]],
    *,
    timing_recorder: TimingRecorder,
) -> Path:
```

Wrap the writer:

```python
    with timing_recorder.stage(
        "discover.write_batch_index",
        metrics={"raw_count": len(rows), "row_count": len(rows)},
    ):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=_BATCH_INDEX_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
    return output_path
```

- [ ] **Step 6: Run discovery tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_timing.py tests/test_discovery_pipeline.py -v
```

Expected: PASS.

## Task 3: Discovery CLI Timing Flag

**Files:**
- Modify: `scripts/run_discovery.py`
- Modify: `tests/test_run_discovery.py`

- [ ] **Step 1: Add a failing CLI test for discovery timing JSON**

Add this import to `tests/test_run_discovery.py`:

```python
import json
```

Add this test before `test_run_discovery_cli_rejects_missing_raw`:

```python
def test_run_discovery_cli_writes_timing_json_for_batch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    raw_path = raw_dir / "A.raw"
    raw_path.write_text("", encoding="utf-8")
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    output_dir = tmp_path / "out"
    timing_path = tmp_path / "diagnostics" / "discovery_timing.json"

    def _fake_run_discovery_batch(
        raw_paths,
        *,
        output_dir,
        settings,
        peak_config,
        timing_recorder=None,
    ):
        assert timing_recorder is not None
        with timing_recorder.stage(
            "discover.write_batch_index",
            metrics={"raw_count": len(raw_paths), "row_count": len(raw_paths)},
        ):
            pass
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "discovery_batch_index.csv"
        output_path.write_text("sample_stem\n", encoding="utf-8")
        return DiscoveryBatchOutputs(batch_index_csv=output_path, per_sample=())

    monkeypatch.setattr(run_discovery, "run_discovery_batch", _fake_run_discovery_batch)

    code = run_discovery.main(
        [
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--output-dir",
            str(output_dir),
            "--timing-output",
            str(timing_path),
        ]
    )

    assert code == 0
    payload = json.loads(timing_path.read_text(encoding="utf-8"))
    assert payload["pipeline"] == "discovery"
    assert payload["records"][0]["stage"] == "discover.write_batch_index"
    assert payload["records"][0]["metrics"] == {"raw_count": 1, "row_count": 1}
    assert "Timing JSON:" in capsys.readouterr().out
```

- [ ] **Step 2: Run the discovery CLI timing test and verify it fails**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_run_discovery.py::test_run_discovery_cli_writes_timing_json_for_batch -v
```

Expected: FAIL because `--timing-output` is not recognized.

- [ ] **Step 3: Add CLI timing support**

In `scripts/run_discovery.py`, add:

```python
from xic_extractor.diagnostics.timing import TimingRecorder
```

Add this parser argument after `--output-dir`:

```python
    parser.add_argument(
        "--timing-output",
        type=Path,
        help="Optional JSON path for discovery stage timing.",
    )
```

In `main()`, after `peak_config = ...`, add:

```python
    timing_recorder = (
        TimingRecorder("discovery") if args.timing_output is not None else None
    )
```

Pass the recorder only when requested so existing tests with narrow fakes keep working:

```python
    timing_kwargs = (
        {"timing_recorder": timing_recorder}
        if timing_recorder is not None
        else {}
    )
```

Update both `run_discovery()` and `run_discovery_batch()` calls by adding `**timing_kwargs`.

After the success prints, add:

```python
    if timing_recorder is not None:
        timing_path = args.timing_output.resolve()
        timing_recorder.write_json(timing_path)
        print(f"Timing JSON: {timing_path}")
```

- [ ] **Step 4: Run discovery CLI tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_run_discovery.py -v
```

Expected: PASS.

## Task 4: Alignment Pipeline Timing

**Files:**
- Modify: `xic_extractor/alignment/pipeline.py`
- Modify: `tests/test_alignment_pipeline.py`

- [ ] **Step 1: Add failing alignment pipeline timing test**

Add this import to `tests/test_alignment_pipeline.py`:

```python
from xic_extractor.diagnostics.timing import TimingRecorder
```

Add this test after `test_pipeline_loads_candidates_builds_owners_backfills_and_writes_defaults`:

```python
def test_pipeline_records_alignment_timing_stages(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch_index = _write_batch(tmp_path, ("Sample_A",))
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "Sample_A.raw").write_text("raw", encoding="utf-8")
    _patch_owner_pipeline_to_matrix(monkeypatch)
    recorder = TimingRecorder("alignment", run_id="test-alignment")

    pipeline_module.run_alignment(
        discovery_batch_index=batch_index,
        raw_dir=raw_dir,
        dll_dir=tmp_path / "dll",
        output_dir=tmp_path / "out",
        alignment_config=AlignmentConfig(),
        peak_config=_peak_config(),
        raw_opener=FakeRawOpener(),
        timing_recorder=recorder,
    )

    stages = [record.stage for record in recorder.records]
    assert stages == [
        "alignment.read_batch_index",
        "alignment.read_candidates",
        "alignment.open_raw_sources",
        "alignment.build_owners",
        "alignment.cluster_owners",
        "alignment.owner_backfill",
        "alignment.build_matrix",
        "alignment.claim_registry",
        "alignment.write_outputs",
    ]
    records_by_stage = {record.stage: record for record in recorder.records}
    assert records_by_stage["alignment.read_candidates"].metrics["candidate_count"] == 1
    assert records_by_stage["alignment.open_raw_sources"].metrics["raw_count"] == 1
```

- [ ] **Step 2: Run the alignment timing test and verify it fails**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_pipeline.py::test_pipeline_records_alignment_timing_stages -v
```

Expected: FAIL with `TypeError` because `run_alignment()` does not accept `timing_recorder`.

- [ ] **Step 3: Thread recorder through `run_alignment()`**

In `xic_extractor/alignment/pipeline.py`, add:

```python
from xic_extractor.diagnostics.timing import TimingRecorder
```

Update `run_alignment()` signature:

```python
def run_alignment(
    *,
    discovery_batch_index: Path,
    raw_dir: Path,
    dll_dir: Path,
    output_dir: Path,
    alignment_config: AlignmentConfig,
    peak_config: ExtractionConfig,
    output_level: AlignmentOutputLevel = "machine",
    emit_alignment_cells: bool = False,
    emit_alignment_status_matrix: bool = False,
    raw_opener: RawOpener | None = None,
    timing_recorder: TimingRecorder | None = None,
) -> AlignmentRunOutputs:
```

At the start of the function, add:

```python
    recorder = timing_recorder or TimingRecorder.disabled("alignment")
```

- [ ] **Step 4: Wrap alignment orchestration stages**

Replace the initial batch/candidate loading with this structure:

```python
    with recorder.stage("alignment.read_batch_index"):
        batch = read_discovery_batch_index(discovery_batch_index)
    with recorder.stage("alignment.read_candidates") as stage:
        candidates = tuple(
            candidate
            for sample_stem in batch.sample_order
            for candidate in read_discovery_candidates_csv(
                batch.candidate_csvs[sample_stem]
            )
        )
        stage.metrics["candidate_count"] = len(candidates)
    opener = raw_opener or _default_raw_opener
```

Inside the existing `ExitStack()`, wrap each major stage:

```python
        with recorder.stage("alignment.open_raw_sources") as stage:
            raw_sources = {
                sample_stem: stack.enter_context(opener(raw_path, dll_dir))
                for sample_stem, raw_path in _existing_raw_paths(
                    sample_order=batch.sample_order,
                    raw_files=batch.raw_files,
                    raw_dir=raw_dir,
                ).items()
            }
            stage.metrics["raw_count"] = len(raw_sources)
        with recorder.stage("alignment.build_owners"):
            ownership = build_sample_local_owners(
                candidates,
                raw_sources=raw_sources,
                alignment_config=alignment_config,
                peak_config=peak_config,
            )
        with recorder.stage("alignment.cluster_owners"):
            owner_features = cluster_sample_local_owners(
                ownership.owners,
                config=alignment_config,
            )
            owner_features = (
                *owner_features,
                *review_only_features_from_ambiguous_records(
                    ownership.ambiguous_records,
                    start_index=len(owner_features) + 1,
                ),
            )
        with recorder.stage("alignment.owner_backfill"):
            rescued_cells = build_owner_backfill_cells(
                owner_features,
                sample_order=batch.sample_order,
                raw_sources=raw_sources,
                alignment_config=alignment_config,
                peak_config=peak_config,
            )
        with recorder.stage("alignment.build_matrix"):
            matrix = build_owner_alignment_matrix(
                owner_features,
                sample_order=batch.sample_order,
                ambiguous_by_sample={},
                rescued_cells=rescued_cells,
            )
        with recorder.stage("alignment.claim_registry"):
            matrix = apply_ms1_peak_claim_registry(matrix, alignment_config)
```

Wrap `_write_outputs_atomic(...)` with:

```python
        with recorder.stage("alignment.write_outputs"):
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
            )
```

- [ ] **Step 5: Run alignment pipeline tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_pipeline.py::test_pipeline_records_alignment_timing_stages tests/test_alignment_pipeline.py::test_pipeline_loads_candidates_builds_owners_backfills_and_writes_defaults -v
```

Expected: PASS.

## Task 5: Alignment CLI Timing Flag

**Files:**
- Modify: `scripts/run_alignment.py`
- Modify: `tests/test_run_alignment.py`

- [ ] **Step 1: Add failing CLI test for alignment timing JSON**

Add this import to `tests/test_run_alignment.py`:

```python
import json
```

Add this test after `test_run_alignment_cli_accepts_output_level_debug`:

```python
def test_run_alignment_cli_writes_timing_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    timing_path = tmp_path / "diagnostics" / "alignment_timing.json"

    def fake_run_alignment(**kwargs):
        timing_recorder = kwargs["timing_recorder"]
        with timing_recorder.stage(
            "alignment.read_candidates",
            metrics={"candidate_count": 0},
        ):
            pass
        return AlignmentRunOutputs()

    monkeypatch.setattr(run_alignment, "run_alignment", fake_run_alignment)

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--timing-output",
            str(timing_path),
        ],
    )

    assert code == 0
    payload = json.loads(timing_path.read_text(encoding="utf-8"))
    assert payload["pipeline"] == "alignment"
    assert payload["records"][0]["stage"] == "alignment.read_candidates"
    assert payload["records"][0]["metrics"] == {"candidate_count": 0}
    assert "Timing JSON:" in capsys.readouterr().out
```

- [ ] **Step 2: Run the alignment CLI timing test and verify it fails**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_run_alignment.py::test_run_alignment_cli_writes_timing_json -v
```

Expected: FAIL because `--timing-output` is not recognized.

- [ ] **Step 3: Add CLI timing support**

In `scripts/run_alignment.py`, add:

```python
from xic_extractor.diagnostics.timing import TimingRecorder
```

Add this parser argument after `--output-dir`:

```python
    parser.add_argument(
        "--timing-output",
        type=Path,
        help="Optional JSON path for alignment stage timing.",
    )
```

In `main()`, before calling `run_alignment()`, add:

```python
    timing_recorder = (
        TimingRecorder("alignment") if args.timing_output is not None else None
    )
    timing_kwargs = (
        {"timing_recorder": timing_recorder}
        if timing_recorder is not None
        else {}
    )
```

Add `**timing_kwargs` to the `run_alignment()` call.

After output path prints, add:

```python
    if timing_recorder is not None:
        timing_path = args.timing_output.resolve()
        timing_recorder.write_json(timing_path)
        print(f"Timing JSON: {timing_path}")
```

- [ ] **Step 4: Run alignment CLI tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_run_alignment.py -v
```

Expected: PASS.

## Task 6: Narrow Regression Suite

**Files:**
- No new files.

- [ ] **Step 1: Run all touched narrow tests**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_timing.py tests/test_discovery_pipeline.py tests/test_run_discovery.py tests/test_alignment_pipeline.py tests/test_run_alignment.py -v
```

Expected: PASS.

- [ ] **Step 2: Run import/package smoke**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python -m py_compile xic_extractor/diagnostics/timing.py xic_extractor/discovery/pipeline.py xic_extractor/alignment/pipeline.py scripts/run_discovery.py scripts/run_alignment.py
```

Expected: no output and exit code 0.

- [ ] **Step 3: Confirm default CLI behavior still avoids timing files**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_run_discovery.py::test_run_discovery_cli_passes_raw_dir_batch_settings tests/test_run_alignment.py::test_run_alignment_cli_passes_paths_settings_and_debug_flags -v
```

Expected: PASS. These tests use fakes that do not accept timing unless the flag is present, so passing confirms default CLI behavior is unchanged.

## Task 7: Real-Data Timing Smoke

**Files:**
- No source files.
- Outputs are written under `output/`.

- [ ] **Step 1: Run 8-RAW discovery with timing enabled**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts\run_discovery.py `
  --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" `
  --dll-dir "C:\Xcalibur\system\programs" `
  --output-dir output\discovery\timing_phase0_8raw `
  --timing-output output\diagnostics\timing_phase0_8raw\discovery_timing.json
```

Expected:

- `output\discovery\timing_phase0_8raw\discovery_batch_index.csv` exists.
- `output\diagnostics\timing_phase0_8raw\discovery_timing.json` exists.
- JSON `pipeline` is `discovery`.
- JSON contains `discover.ms2_seeds`, `discover.ms1_backfill`, `discover.feature_family`, and CSV write stages.

- [ ] **Step 2: Run alignment on the timed discovery output**

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run python scripts\run_alignment.py `
  --discovery-batch-index output\discovery\timing_phase0_8raw\discovery_batch_index.csv `
  --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" `
  --dll-dir "C:\Xcalibur\system\programs" `
  --output-dir output\alignment\timing_phase0_8raw `
  --output-level machine `
  --emit-alignment-cells `
  --timing-output output\diagnostics\timing_phase0_8raw\alignment_timing.json
```

Expected:

- `output\alignment\timing_phase0_8raw\alignment_review.tsv` exists.
- `output\diagnostics\timing_phase0_8raw\alignment_timing.json` exists.
- JSON `pipeline` is `alignment`.
- JSON contains `alignment.build_owners`, `alignment.owner_backfill`, `alignment.claim_registry`, and `alignment.write_outputs`.

- [ ] **Step 3: Generate ranked timing notes**

Run:

```powershell
function Get-StageRows {
  param([string]$Path)
  $payload = Get-Content $Path -Raw | ConvertFrom-Json
  $rows = $payload.records |
    Group-Object stage |
    ForEach-Object {
      [pscustomobject]@{
        Stage = $_.Name
        ElapsedSec = [math]::Round(($_.Group | Measure-Object elapsed_sec -Sum).Sum, 3)
        Count = $_.Count
      }
    }
  $rank = 0
  $rows |
    Sort-Object ElapsedSec -Descending |
    ForEach-Object {
      $rank++
      [pscustomobject]@{
        Rank = $rank
        Stage = $_.Stage
        ElapsedSec = $_.ElapsedSec
        Count = $_.Count
      }
    }
}

function ConvertTo-MarkdownTable {
  param($Rows)
  $lines = @("| Rank | Stage | Total elapsed sec | Count |", "|---:|---|---:|---:|")
  foreach ($row in $Rows) {
    $lines += "| $($row.Rank) | $($row.Stage) | $($row.ElapsedSec) | $($row.Count) |"
  }
  return $lines
}

$discoveryRows = @(Get-StageRows "output\diagnostics\timing_phase0_8raw\discovery_timing.json")
$alignmentRows = @(Get-StageRows "output\diagnostics\timing_phase0_8raw\alignment_timing.json")
$notesPath = "output\diagnostics\timing_phase0_8raw\phase0_timing_notes.md"

$notes = @(
  "# Phase 0 Timing Notes",
  "",
  "## Command Context",
  "",
  "- Branch: codex/untargeted-discovery-v1-implementation",
  "- Discovery timing: output\diagnostics\timing_phase0_8raw\discovery_timing.json",
  "- Alignment timing: output\diagnostics\timing_phase0_8raw\alignment_timing.json",
  "- RAW directory: C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation",
  "- DLL directory: C:\Xcalibur\system\programs",
  "",
  "## Discovery Stage Ranking",
  ""
)
$notes += ConvertTo-MarkdownTable $discoveryRows
$notes += @(
  "",
  "## Alignment Stage Ranking",
  ""
)
$notes += ConvertTo-MarkdownTable $alignmentRows
$notes += @(
  "",
  "## Decision",
  "",
  "- Proceed to Phase 1 discovery per-RAW process backend: pending",
  "- Reason: review the ranked timing tables above before deciding."
)
New-Item -ItemType Directory -Force -Path (Split-Path $notesPath) | Out-Null
Set-Content -Path $notesPath -Value $notes -Encoding utf8
Get-Content $notesPath
```

Expected:

- `output\diagnostics\timing_phase0_8raw\phase0_timing_notes.md` exists.
- The discovery ranking is sorted by total `elapsed_sec` descending.
- The alignment ranking is sorted by total `elapsed_sec` descending.
- The Decision section is explicitly `pending`, not blank.

- [ ] **Step 4: Record the timing decision**

Open `output\diagnostics\timing_phase0_8raw\phase0_timing_notes.md` and update only the Decision section.

Use one of these exact outcomes:

```markdown
- Proceed to Phase 1 discovery per-RAW process backend: yes
- Reason: discovery RAW-local stages dominate the measured run; per-RAW workers are the next bottleneck to test.
```

```markdown
- Proceed to Phase 1 discovery per-RAW process backend: no
- Reason: alignment stages dominate the measured run; optimize alignment or revisit scope before adding discovery workers.
```

```markdown
- Proceed to Phase 1 discovery per-RAW process backend: pending
- Reason: timing is inconclusive; bring the timing notes back to the user before implementing Phase 1.
```

If alignment dominates the 8-RAW run and discovery is not the main bottleneck, stop before implementing Phase 1 and bring the timing notes back to the user.

## Self-Review Checklist

- [ ] The plan implements only Phase 0 timing.
- [ ] No `.mzML`, Parquet, Polars, Dask, Ray, GPU, or Numba work is included.
- [ ] Timing is optional and disabled by default.
- [ ] Existing CSV/TSV/XLSX output contracts remain unchanged.
- [ ] Discovery and alignment are timed as separate surfaces.
- [ ] Tests cover recorder basics, discovery pipeline stages, alignment pipeline stages, and CLI JSON writes.
- [ ] Real-data smoke produces JSON files before any Phase 1 worker design begins.
