from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from xic_extractor.xic_models import XICRequest, XICTrace

OwnerBackfillXicBackend = Literal["raw", "ms1_index"]
MS1IndexIntensityMode = Literal["max", "sum"]


@dataclass(frozen=True)
class MS1Scan:
    scan_number: int
    rt: float
    masses: NDArray[np.float64]
    intensities: NDArray[np.float64]


class MS1IndexedRawSource:
    def __init__(self, source: Any) -> None:
        self._source = source
        self._index: tuple[MS1Scan, ...] | None = None

    @property
    def raw_chromatogram_call_count(self) -> int:
        value = getattr(self._source, "raw_chromatogram_call_count", 0)
        return value if isinstance(value, int) else 0

    def extract_xic(
        self,
        mz: float,
        rt_min: float,
        rt_max: float,
        ppm_tol: float,
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        trace = self.extract_xic_many(
            (XICRequest(mz=mz, rt_min=rt_min, rt_max=rt_max, ppm_tol=ppm_tol),)
        )[0]
        return trace.rt, trace.intensity

    def extract_xic_many(
        self,
        requests: tuple[XICRequest, ...],
    ) -> tuple[XICTrace, ...]:
        if not requests:
            return ()
        index = self._ms1_index()
        return tuple(
            extract_index_xic(self._source, index, request)
            for request in requests
        )

    def scan_window_for_request(self, request: XICRequest) -> tuple[int, int]:
        resolver = getattr(self._source, "scan_window_for_request", None)
        if callable(resolver):
            start_scan, end_scan = resolver(request)
            return int(start_scan), int(end_scan)
        raw_file = _raw_file(self._source)
        return (
            int(raw_file.ScanNumberFromRetentionTime(request.rt_min)),
            int(raw_file.ScanNumberFromRetentionTime(request.rt_max)),
        )

    def _ms1_index(self) -> tuple[MS1Scan, ...]:
        if self._index is None:
            self._index = build_ms1_scan_index(self._source)
        return self._index


def source_for_owner_backfill_backend(
    source: Any,
    backend: OwnerBackfillXicBackend,
) -> Any:
    if backend == "raw":
        return source
    if backend == "ms1_index":
        return MS1IndexedRawSource(source)
    raise ValueError(f"unsupported owner backfill XIC backend: {backend}")


def build_ms1_scan_index(source: Any) -> tuple[MS1Scan, ...]:
    raw_file = _raw_file(source)
    header = raw_file.RunHeaderEx
    scans: list[MS1Scan] = []
    for scan_number in range(int(header.FirstSpectrum), int(header.LastSpectrum) + 1):
        filter_obj = raw_file.GetFilterForScanNumber(scan_number)
        if str(getattr(filter_obj, "MSOrder", "")) != "Ms":
            continue
        masses, intensities = _scan_arrays(raw_file, scan_number)
        if (
            masses.ndim != 1
            or intensities.ndim != 1
            or masses.shape != intensities.shape
        ):
            continue
        scans.append(
            MS1Scan(
                scan_number=scan_number,
                rt=float(raw_file.RetentionTimeFromScanNumber(scan_number)),
                masses=masses,
                intensities=intensities,
            )
        )
    return tuple(scans)


def extract_index_xic(
    source: Any,
    index: tuple[MS1Scan, ...],
    request: XICRequest,
    *,
    intensity_mode: MS1IndexIntensityMode = "max",
) -> XICTrace:
    start_scan, end_scan = _scan_window(source, request)
    tolerance = request.mz * request.ppm_tol / 1e6
    rt_values: list[float] = []
    intensity_values: list[float] = []
    for scan in index:
        if scan.scan_number < start_scan or scan.scan_number > end_scan:
            continue
        left = int(np.searchsorted(scan.masses, request.mz - tolerance, side="left"))
        right = int(np.searchsorted(scan.masses, request.mz + tolerance, side="right"))
        intensity = _window_intensity(
            scan.intensities[left:right],
            intensity_mode=intensity_mode,
        )
        rt_values.append(scan.rt)
        intensity_values.append(intensity)
    return XICTrace.from_arrays(rt_values, intensity_values)


def _window_intensity(
    intensities: NDArray[np.float64],
    *,
    intensity_mode: MS1IndexIntensityMode,
) -> float:
    if len(intensities) == 0:
        return 0.0
    if intensity_mode == "max":
        return float(np.max(intensities))
    if intensity_mode == "sum":
        return float(np.sum(intensities))
    raise ValueError(f"unsupported MS1 index intensity mode: {intensity_mode}")


def _scan_window(source: Any, request: XICRequest) -> tuple[int, int]:
    resolver = getattr(source, "scan_window_for_request", None)
    if callable(resolver):
        start_scan, end_scan = resolver(request)
        return int(start_scan), int(end_scan)
    raw_file = _raw_file(source)
    return (
        int(raw_file.ScanNumberFromRetentionTime(request.rt_min)),
        int(raw_file.ScanNumberFromRetentionTime(request.rt_max)),
    )


def _scan_arrays(
    raw_file: Any,
    scan_number: int,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    if hasattr(raw_file, "GetSegmentedScanFromScanNumber"):
        scan = raw_file.GetSegmentedScanFromScanNumber(scan_number, None)
        masses = getattr(scan, "Positions", [])
    else:
        scan = raw_file.GetSimplifiedScan(scan_number)
        masses = getattr(scan, "Masses", [])
    return (
        np.asarray(masses, dtype=float),
        np.asarray(getattr(scan, "Intensities", []), dtype=float),
    )


def _raw_file(source: Any) -> Any:
    return getattr(source, "_raw_file", source)
