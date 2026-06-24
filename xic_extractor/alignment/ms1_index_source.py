from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from xic_extractor.xic_models import XICRequest, XICTrace

OwnerBuildXicBackend = Literal["raw", "raw_superwindow", "ms1_index"]
OwnerBackfillXicBackend = Literal["raw", "ms1_index", "ms1_index_hybrid"]
MS1IndexIntensityMode = Literal["max", "sum"]

_WindowedRequest = tuple[int, XICRequest, tuple[int, int]]


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


class RawSuperWindowSource:
    def __init__(
        self,
        source: Any,
        *,
        superwindow_span_factor: int = 2,
    ) -> None:
        if superwindow_span_factor < 1:
            raise ValueError("superwindow_span_factor must be >= 1")
        self._source = source
        self._superwindow_span_factor = superwindow_span_factor
        self._retention_time_cache: dict[int, float] = {}

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
        groups = _superwindow_groups(
            self,
            requests,
            superwindow_span_factor=self._superwindow_span_factor,
        )
        if groups is None:
            return _extract_source_many(self._source, requests)

        traces: list[XICTrace | None] = [None] * len(requests)
        for group in groups:
            union_start = min(scan_window[0] for _index, _request, scan_window in group)
            union_end = max(scan_window[1] for _index, _request, scan_window in group)
            union_rt_min = self.retention_time_for_scan(union_start)
            union_rt_max = self.retention_time_for_scan(union_end)
            if union_rt_min > union_rt_max:
                union_rt_min, union_rt_max = union_rt_max, union_rt_min
            union_requests = tuple(
                XICRequest(
                    mz=request.mz,
                    rt_min=union_rt_min,
                    rt_max=union_rt_max,
                    ppm_tol=request.ppm_tol,
                )
                for _index, request, _scan_window in group
            )
            union_traces = _extract_source_many(self._source, union_requests)
            for trace, (original_index, _request, scan_window) in zip(
                union_traces,
                group,
                strict=True,
            ):
                traces[original_index] = _crop_trace_to_scan_window(
                    self,
                    trace,
                    scan_window,
                )
        if any(trace is None for trace in traces):
            raise RuntimeError("super-window extraction returned incomplete traces")
        return tuple(trace for trace in traces if trace is not None)

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

    def retention_time_for_scan(self, scan_number: int) -> float:
        scan_number = int(scan_number)
        cached = self._retention_time_cache.get(scan_number)
        if cached is not None:
            return cached
        resolver = getattr(self._source, "retention_time_for_scan", None)
        if callable(resolver):
            value = float(resolver(scan_number))
        else:
            raw_file = _raw_file(self._source)
            value = float(raw_file.RetentionTimeFromScanNumber(scan_number))
        self._retention_time_cache[scan_number] = value
        return value


def source_for_owner_backfill_backend(
    source: Any,
    backend: OwnerBackfillXicBackend,
) -> Any:
    if backend == "raw":
        return source
    if backend in {"ms1_index", "ms1_index_hybrid"}:
        return MS1IndexedRawSource(source)
    raise ValueError(f"unsupported owner backfill XIC backend: {backend}")


def source_for_owner_build_backend(
    source: Any,
    backend: OwnerBuildXicBackend,
) -> Any:
    if backend == "raw":
        return source
    if backend == "raw_superwindow":
        return RawSuperWindowSource(source)
    if backend == "ms1_index":
        return MS1IndexedRawSource(source)
    raise ValueError(f"unsupported owner build XIC backend: {backend}")


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


def _extract_source_many(
    source: Any,
    requests: tuple[XICRequest, ...],
) -> tuple[XICTrace, ...]:
    if hasattr(source, "extract_xic_many"):
        return tuple(source.extract_xic_many(requests))
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


def _superwindow_groups(
    source: RawSuperWindowSource,
    requests: tuple[XICRequest, ...],
    *,
    superwindow_span_factor: int,
) -> tuple[tuple[_WindowedRequest, ...], ...] | None:
    windowed_requests: list[_WindowedRequest] = []
    try:
        for index, request in enumerate(requests):
            scan_window = source.scan_window_for_request(request)
            source.retention_time_for_scan(scan_window[0])
            source.retention_time_for_scan(scan_window[1])
            windowed_requests.append((index, request, scan_window))
    except (AttributeError, NotImplementedError):
        return None
    if not windowed_requests:
        return ()

    ordered = tuple(sorted(windowed_requests, key=_windowed_request_sort_key))
    groups: list[tuple[_WindowedRequest, ...]] = []
    current: list[_WindowedRequest] = []
    current_start = 0
    current_end = 0
    current_max_span = 1
    for windowed_request in ordered:
        scan_start, scan_end = windowed_request[2]
        item_span = _scan_span(scan_start, scan_end)
        if not current:
            current = [windowed_request]
            current_start = scan_start
            current_end = scan_end
            current_max_span = item_span
            continue

        proposed_start = min(current_start, scan_start)
        proposed_end = max(current_end, scan_end)
        proposed_max_span = max(current_max_span, item_span)
        overlaps_current = scan_start <= current_end
        within_span_limit = (
            _scan_span(proposed_start, proposed_end)
            <= proposed_max_span * superwindow_span_factor
        )
        if overlaps_current and within_span_limit:
            current.append(windowed_request)
            current_start = proposed_start
            current_end = proposed_end
            current_max_span = proposed_max_span
            continue

        groups.append(tuple(current))
        current = [windowed_request]
        current_start = scan_start
        current_end = scan_end
        current_max_span = item_span
    if current:
        groups.append(tuple(current))
    return tuple(groups)


def _windowed_request_sort_key(
    windowed_request: _WindowedRequest,
) -> tuple[int, int, float, int]:
    original_index, request, scan_window = windowed_request
    return (scan_window[0], scan_window[1], request.mz, original_index)


def _crop_trace_to_scan_window(
    source: RawSuperWindowSource,
    trace: XICTrace,
    scan_window: tuple[int, int],
) -> XICTrace:
    rt_min = source.retention_time_for_scan(scan_window[0])
    rt_max = source.retention_time_for_scan(scan_window[1])
    if rt_min > rt_max:
        rt_min, rt_max = rt_max, rt_min
    mask = (trace.rt >= rt_min) & (trace.rt <= rt_max)
    return XICTrace.from_arrays(trace.rt[mask], trace.intensity[mask])


def _scan_span(start_scan: int, end_scan: int) -> int:
    return max(1, abs(end_scan - start_scan) + 1)


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
