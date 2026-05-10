import ast
import csv
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest

from xic_extractor.config import ExtractionConfig
from xic_extractor.discovery.models import (
    DiscoveryBatchOutputs,
    DiscoveryRunOutputs,
    DiscoverySettings,
    NeutralLossProfile,
)
from xic_extractor.discovery.pipeline import run_discovery, run_discovery_batch
from xic_extractor.raw_reader import Ms2Scan, Ms2ScanEvent
from xic_extractor.signal_processing import PeakDetectionResult, PeakResult

NEUTRAL_LOSS_DA = 116.0474


def test_single_raw_pipeline_groups_strict_ms2_seeds_and_writes_dual_csvs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_path = tmp_path / "TumorBC2312_DNA.raw"
    output_dir = tmp_path / "out"
    raw = _FakeRawHandle(
        [
            _scan_event(scan_number=101, rt=7.80, product_intensity=3000.0),
            _scan_event(scan_number=202, rt=7.86, product_intensity=9000.0),
        ],
        rt=np.array([7.70, 7.86, 8.00]),
        intensity=np.array([10.0, 600.0, 20.0]),
    )
    monkeypatch.setattr(
        "xic_extractor.discovery.ms1_backfill.find_peak_and_area",
        lambda *args, **kwargs: _ok_peak(
            rt=7.86,
            intensity=600.0,
            area=42.0,
            start=7.70,
            end=8.00,
        ),
    )

    outputs = run_discovery(
        raw_path,
        output_dir=output_dir,
        settings=_settings(seed_rt_gap_min=0.20),
        peak_config=_peak_config(tmp_path),
        raw_opener=lambda path, dll_dir: raw,
    )

    assert outputs == DiscoveryRunOutputs(
        candidates_csv=output_dir / "discovery_candidates.csv",
        review_csv=output_dir / "discovery_review.csv",
    )
    rows = _read_csv(outputs.candidates_csv)
    assert len(rows) == 1
    assert rows[0]["candidate_id"] == "TumorBC2312_DNA#202"
    assert rows[0]["best_ms2_scan_id"] == "202"
    assert rows[0]["seed_scan_ids"] == "101;202"
    assert rows[0]["seed_event_count"] == "2"
    assert rows[0]["ms1_peak_found"] == "TRUE"
    review_rows = _read_csv(outputs.review_csv)
    assert len(review_rows) == 1
    assert review_rows[0]["candidate_id"] == "TumorBC2312_DNA#202"
    assert "review_note" in review_rows[0]


def test_pipeline_writes_header_only_csv_when_no_strict_seeds(tmp_path: Path) -> None:
    raw = _FakeRawHandle(events=[])

    outputs = run_discovery(
        tmp_path / "Blank.raw",
        output_dir=tmp_path / "out",
        settings=_settings(),
        peak_config=_peak_config(tmp_path),
        raw_opener=lambda path, dll_dir: raw,
    )

    with outputs.candidates_csv.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    with outputs.review_csv.open(newline="", encoding="utf-8") as handle:
        review_rows = list(csv.reader(handle))

    assert len(rows) == 1
    assert "candidate_id" in rows[0]
    assert len(review_rows) == 1
    assert "review_note" in review_rows[0]


def test_batch_pipeline_writes_per_sample_csvs_and_index(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_paths = (
        tmp_path / "TumorBC2312_DNA.raw",
        tmp_path / "NormalBC2257_DNA.raw",
    )
    raw_by_path = {
        raw_paths[0]: _FakeRawHandle(
            [_scan_event(scan_number=101, rt=7.80, product_intensity=3000.0)],
            rt=np.array([7.70, 7.80, 8.00]),
            intensity=np.array([10.0, 600.0, 20.0]),
        ),
        raw_paths[1]: _FakeRawHandle(
            [_scan_event(scan_number=202, rt=9.10, product_intensity=7000.0)],
            rt=np.array([9.00, 9.10, 9.30]),
            intensity=np.array([15.0, 900.0, 25.0]),
        ),
    }
    monkeypatch.setattr(
        "xic_extractor.discovery.ms1_backfill.find_peak_and_area",
        lambda rt, intensity, peak_config, **kwargs: _ok_peak(
            rt=float(rt[1]),
            intensity=float(intensity[1]),
            area=float(intensity[1] * 0.1),
            start=float(rt[0]),
            end=float(rt[-1]),
        ),
    )

    outputs = run_discovery_batch(
        raw_paths,
        output_dir=tmp_path / "out",
        settings=_settings(),
        peak_config=_peak_config(tmp_path),
        raw_opener=lambda path, dll_dir: raw_by_path[path],
    )

    assert isinstance(outputs, DiscoveryBatchOutputs)
    assert outputs.batch_index_csv == tmp_path / "out" / "discovery_batch_index.csv"
    assert len(outputs.per_sample) == 2
    index_rows = _read_csv(outputs.batch_index_csv)
    assert [row["sample_stem"] for row in index_rows] == [
        "TumorBC2312_DNA",
        "NormalBC2257_DNA",
    ]
    assert [row["candidate_count"] for row in index_rows] == ["1", "1"]
    assert [row["medium_count"] for row in index_rows] == ["1", "1"]
    assert [
        Path(row["candidate_csv"]).name for row in index_rows
    ] == ["discovery_candidates.csv", "discovery_candidates.csv"]
    assert [
        Path(row["review_csv"]).name for row in index_rows
    ] == ["discovery_review.csv", "discovery_review.csv"]

    first_rows = _read_csv(
        tmp_path / "out" / "TumorBC2312_DNA" / "discovery_candidates.csv"
    )
    first_review_rows = _read_csv(
        tmp_path / "out" / "TumorBC2312_DNA" / "discovery_review.csv"
    )
    second_rows = _read_csv(
        tmp_path / "out" / "NormalBC2257_DNA" / "discovery_candidates.csv"
    )
    assert [row["candidate_id"] for row in first_rows] == ["TumorBC2312_DNA#101"]
    assert [row["candidate_id"] for row in first_review_rows] == [
        "TumorBC2312_DNA#101"
    ]
    assert [row["candidate_id"] for row in second_rows] == ["NormalBC2257_DNA#202"]
    assert not (tmp_path / "out" / "discovery_candidates.csv").exists()
    assert all(raw.entered and raw.closed for raw in raw_by_path.values())


def test_batch_pipeline_escapes_excel_formula_strings_in_index(
    tmp_path: Path,
) -> None:
    raw_path = Path("=cmd.raw")
    raw = _FakeRawHandle(events=[])

    outputs = run_discovery_batch(
        (raw_path,),
        output_dir=tmp_path / "out",
        settings=_settings(),
        peak_config=_peak_config(tmp_path),
        raw_opener=lambda path, dll_dir: raw,
    )

    row = _read_csv(outputs.batch_index_csv)[0]
    assert row["sample_stem"] == "'=cmd"
    assert row["raw_file"].startswith("'=")
    assert row["candidate_csv"].endswith("discovery_candidates.csv")
    assert row["review_csv"].endswith("discovery_review.csv")


def test_run_discovery_keeps_stale_pair_when_review_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    stale_full = output_dir / "discovery_candidates.csv"
    stale_review = output_dir / "discovery_review.csv"
    stale_full.write_text("stale full\n", encoding="utf-8")
    stale_review.write_text("stale review\n", encoding="utf-8")
    raw = _FakeRawHandle(events=[])

    def _fail_review(path: Path, candidates: object) -> Path:
        raise OSError("simulated review writer failure")

    monkeypatch.setattr(
        "xic_extractor.discovery.pipeline.write_discovery_review_csv",
        _fail_review,
    )

    with pytest.raises(OSError, match="simulated review writer failure"):
        run_discovery(
            tmp_path / "Blank.raw",
            output_dir=output_dir,
            settings=_settings(),
            peak_config=_peak_config(tmp_path),
            raw_opener=lambda path, dll_dir: raw,
        )

    assert stale_full.read_text(encoding="utf-8") == "stale full\n"
    assert stale_review.read_text(encoding="utf-8") == "stale review\n"
    assert not (output_dir / "discovery_candidates.csv.tmp").exists()
    assert not (output_dir / "discovery_review.csv.tmp").exists()


def test_pipeline_uses_injected_raw_opener_with_dll_dir_and_closes_context(
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / "Sample.raw"
    peak_config = _peak_config(tmp_path)
    raw = _FakeRawHandle(events=[])
    calls: list[tuple[Path, Path]] = []

    def _open(path: Path, dll_dir: Path) -> _FakeRawHandle:
        calls.append((path, dll_dir))
        return raw

    run_discovery(
        raw_path,
        output_dir=tmp_path / "out",
        settings=_settings(),
        peak_config=peak_config,
        raw_opener=_open,
    )

    assert calls == [(raw_path, peak_config.dll_dir)]
    assert raw.entered is True
    assert raw.closed is True


def test_pipeline_does_not_import_targeted_extractor_module() -> None:
    pipeline_path = (
        Path(__file__).resolve().parents[1]
        / "xic_extractor"
        / "discovery"
        / "pipeline.py"
    )
    tree = ast.parse(pipeline_path.read_text(encoding="utf-8"))

    imported_modules = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported_from_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }

    assert "xic_extractor.extractor" not in imported_modules | imported_from_modules


def _settings(**overrides: float) -> DiscoverySettings:
    values = {
        "neutral_loss_profile": NeutralLossProfile("DNA_dR", NEUTRAL_LOSS_DA),
        **overrides,
    }
    return DiscoverySettings(**values)


def _peak_config(tmp_path: Path) -> ExtractionConfig:
    return ExtractionConfig(
        data_dir=tmp_path,
        dll_dir=tmp_path / "dll",
        output_csv=tmp_path / "xic_results.csv",
        diagnostics_csv=tmp_path / "xic_diagnostics.csv",
        smooth_window=15,
        smooth_polyorder=3,
        peak_rel_height=0.95,
        peak_min_prominence_ratio=0.10,
        ms2_precursor_tol_da=0.5,
        nl_min_intensity_ratio=0.01,
        resolver_mode="local_minimum",
    )


def _scan_event(
    *,
    scan_number: int,
    rt: float,
    product_intensity: float,
) -> Ms2ScanEvent:
    precursor_mz = 258.1085
    product_mz = precursor_mz - NEUTRAL_LOSS_DA
    return Ms2ScanEvent(
        scan=Ms2Scan(
            scan_number=scan_number,
            rt=rt,
            precursor_mz=precursor_mz,
            masses=np.asarray([product_mz], dtype=float),
            intensities=np.asarray([product_intensity], dtype=float),
            base_peak=product_intensity,
        ),
        parse_error=None,
        scan_number=scan_number,
    )


def _ok_peak(
    *,
    rt: float,
    intensity: float,
    area: float,
    start: float,
    end: float,
) -> PeakDetectionResult:
    return PeakDetectionResult(
        status="OK",
        peak=PeakResult(
            rt=rt,
            intensity=intensity,
            intensity_smoothed=intensity,
            area=area,
            peak_start=start,
            peak_end=end,
        ),
        n_points=3,
        max_smoothed=intensity,
        n_prominent_peaks=1,
    )


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


class _FakeRawHandle:
    def __init__(
        self,
        events: list[Ms2ScanEvent],
        *,
        rt: np.ndarray | None = None,
        intensity: np.ndarray | None = None,
    ) -> None:
        self._events = events
        self._rt = np.asarray([] if rt is None else rt, dtype=float)
        self._intensity = np.asarray(
            [] if intensity is None else intensity, dtype=float
        )
        self.entered = False
        self.closed = False

    def __enter__(self) -> "_FakeRawHandle":
        self.entered = True
        return self

    def __exit__(self, *_args: object) -> None:
        self.closed = True

    def iter_ms2_scans(self, rt_min: float, rt_max: float) -> Iterator[Ms2ScanEvent]:
        yield from self._events

    def extract_xic(
        self,
        mz: float,
        rt_min: float,
        rt_max: float,
        ppm_tol: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        return self._rt, self._intensity
