from pathlib import Path
from types import SimpleNamespace

import numpy as np

from scripts import validate_ms1_scan_index_xic as ms1_index
from xic_extractor.xic_models import XICRequest, XICTrace


def test_ms1_scan_index_uses_ms1_scans_and_mass_window_max() -> None:
    raw = FakeRawHandle()
    request = XICRequest(mz=100.0, rt_min=1.0, rt_max=3.0, ppm_tol=10000.0)

    index = ms1_index.build_ms1_scan_index(raw)
    trace = ms1_index.extract_index_xic(raw, index, request)

    assert [scan.scan_number for scan in index] == [1, 3]
    assert trace.rt.tolist() == [1.0, 3.0]
    assert trace.intensity.tolist() == [20.0, 40.0]


def test_compare_traces_reports_rt_grid_and_intensity_metrics() -> None:
    vendor = XICTrace.from_arrays([1.0, 2.0, 3.0], [10.0, 20.0, 30.0])
    local = XICTrace.from_arrays([1.0, 2.0, 3.0], [9.0, 18.0, 33.0])

    metrics = ms1_index.compare_traces(vendor, local)

    assert metrics["length_match"] is True
    assert metrics["rt_grid_equal"] is True
    assert metrics["max_abs_intensity_delta"] == 3.0
    assert metrics["intensity_sum_ratio"] == 1.0
    assert metrics["correlation"] > 0.98


class FakeRawHandle:
    def __init__(self) -> None:
        self._raw_file = self
        self.RunHeaderEx = SimpleNamespace(FirstSpectrum=1, LastSpectrum=3)

    def GetFilterForScanNumber(self, scan_number: int) -> SimpleNamespace:
        return SimpleNamespace(MSOrder="Ms2" if scan_number == 2 else "Ms")

    def GetSegmentedScanFromScanNumber(
        self,
        scan_number: int,
        _scan_filter,
    ) -> SimpleNamespace:
        arrays = {
            1: ([99.0, 100.0, 101.0], [5.0, 20.0, 10.0]),
            2: ([100.0], [999.0]),
            3: ([99.0, 100.0, 101.0], [15.0, 40.0, 30.0]),
        }
        masses, intensities = arrays[scan_number]
        return SimpleNamespace(
            Positions=np.asarray(masses, dtype=float),
            Intensities=np.asarray(intensities, dtype=float),
        )

    def RetentionTimeFromScanNumber(self, scan_number: int) -> float:
        return float(scan_number)

    def ScanNumberFromRetentionTime(self, rt: float) -> int:
        return int(round(rt))
