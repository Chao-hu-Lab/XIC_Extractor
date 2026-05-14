from types import SimpleNamespace

import numpy as np

from tools.diagnostics import ms1_index_backfill_audit as audit
from xic_extractor.config import ExtractionConfig
from xic_extractor.xic_models import XICRequest, XICTrace


def test_audit_requests_compares_max_and_sum_against_vendor() -> None:
    summary, examples = audit.audit_requests_for_sample(
        sample_stem="sample-a",
        raw=FakeRawHandle(),
        requests=(
            XICRequest(mz=100.0, rt_min=1.0, rt_max=7.0, ppm_tol=10000.0),
        ),
        peak_config=_peak_config(),
        example_limit=5,
    )

    assert summary["request_count"] == 1
    assert summary["modes"]["max"]["peak_status_match_count"] == 1
    assert summary["modes"]["sum"]["peak_status_match_count"] == 1
    assert summary["modes"]["max"]["area_relative_delta_median"] > 0.0
    assert summary["modes"]["sum"]["area_relative_delta_median"] == 0.0
    assert examples[0]["sample_stem"] == "sample-a"
    assert examples[0]["mode"] == "max"


class FakeRawHandle:
    def __init__(self) -> None:
        self._raw_file = self
        self.RunHeaderEx = SimpleNamespace(FirstSpectrum=1, LastSpectrum=7)

    def extract_xic_many(self, requests):
        traces = []
        for request in requests:
            assert request.mz == 100.0
            traces.append(
                XICTrace.from_arrays(
                    [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0],
                    [0.0, 10.0, 60.0, 100.0, 60.0, 10.0, 0.0],
                )
            )
        return tuple(traces)

    def extract_xic(self, mz, rt_min, rt_max, ppm_tol):
        return self.extract_xic_many(
            (XICRequest(mz=mz, rt_min=rt_min, rt_max=rt_max, ppm_tol=ppm_tol),)
        )[0]

    def GetFilterForScanNumber(self, scan_number: int) -> SimpleNamespace:
        return SimpleNamespace(MSOrder="Ms")

    def GetSegmentedScanFromScanNumber(
        self,
        scan_number: int,
        _scan_filter,
    ) -> SimpleNamespace:
        profile = {
            1: 0.0,
            2: 10.0,
            3: 60.0,
            4: 100.0,
            5: 60.0,
            6: 10.0,
            7: 0.0,
        }
        height = profile[scan_number]
        masses = [99.0, 100.0, 101.0]
        intensities = [height * 0.2, height * 0.6, height * 0.2]
        return SimpleNamespace(
            Positions=np.asarray(masses, dtype=float),
            Intensities=np.asarray(intensities, dtype=float),
        )

    def RetentionTimeFromScanNumber(self, scan_number: int) -> float:
        return float(scan_number)

    def ScanNumberFromRetentionTime(self, rt: float) -> int:
        return int(round(rt))


def _peak_config() -> ExtractionConfig:
    return ExtractionConfig(
        data_dir=".",
        dll_dir=".",
        output_csv="out.csv",
        diagnostics_csv="diag.csv",
        smooth_window=3,
        smooth_polyorder=1,
        peak_rel_height=0.95,
        peak_min_prominence_ratio=0.01,
        ms2_precursor_tol_da=1.6,
        nl_min_intensity_ratio=0.01,
    )
