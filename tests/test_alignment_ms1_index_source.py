from types import SimpleNamespace

import numpy as np

from xic_extractor.alignment.ms1_index_source import MS1IndexedRawSource
from xic_extractor.xic_models import XICRequest


def test_ms1_indexed_raw_source_extracts_mass_window_maxima() -> None:
    source = MS1IndexedRawSource(FakeRawHandle())

    traces = source.extract_xic_many(
        (
            XICRequest(mz=100.0, rt_min=1.0, rt_max=3.0, ppm_tol=10000.0),
            XICRequest(mz=101.0, rt_min=1.0, rt_max=1.0, ppm_tol=1.0),
        )
    )

    assert [trace.rt.tolist() for trace in traces] == [[1.0, 3.0], [1.0]]
    assert [trace.intensity.tolist() for trace in traces] == [[20.0, 40.0], [10.0]]


def test_ms1_indexed_raw_source_delegates_scan_window_lookup() -> None:
    source = MS1IndexedRawSource(FakeRawHandle())

    assert source.scan_window_for_request(
        XICRequest(mz=100.0, rt_min=1.0, rt_max=3.0, ppm_tol=10000.0)
    ) == (1, 3)


class FakeRawHandle:
    def __init__(self) -> None:
        self._raw_file = self
        self.RunHeaderEx = SimpleNamespace(FirstSpectrum=1, LastSpectrum=3)

    @property
    def raw_chromatogram_call_count(self) -> int:
        return 0

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
