from collections.abc import Iterator
from dataclasses import dataclass
from typing import Literal, Protocol

import numpy as np

from xic_extractor.raw_reader import Ms2Scan, Ms2ScanEvent

NL_DIAGNOSTIC_PPM_FLOOR = 500.0
NLStatus = Literal["OK", "WARN", "NL_FAIL", "NO_MS2"]


class MS2ScanSource(Protocol):
    def iter_ms2_scans(self, rt_min: float, rt_max: float) -> Iterator[Ms2ScanEvent]:
        """Yield MS2 scan events for the requested retention-time window."""
        ...


@dataclass(frozen=True)
class NLResult:
    status: NLStatus
    best_ppm: float | None
    best_scan_rt: float | None
    valid_ms2_scan_count: int
    parse_error_count: int
    matched_scan_count: int

    def to_token(self) -> str:
        if self.status == "WARN" and self.best_ppm is not None:
            return f"WARN_{self.best_ppm:.1f}ppm"
        return self.status


def find_nl_anchor_rt(
    raw: MS2ScanSource,
    *,
    precursor_mz: float,
    rt_center: float,
    search_margin_min: float,
    neutral_loss_da: float,
    nl_ppm_max: float,
    ms2_precursor_tol_da: float,
    nl_min_intensity_ratio: float,
    reference_rt: float | None = None,
) -> float | None:
    """在 rt_center ± search_margin_min 範圍內搜尋 NL 確認的 MS2 scan，回傳最合適的 RT。

    選擇邏輯依 reference_rt 而定：
    - reference_rt 為 None：選 base_peak 最高的 scan。
      適用於 ISTD（無同 m/z 異構體干擾）及無 ISTD pair 的 analyte（無外部 RT
      基準時，訊號強度最可靠）。
    - reference_rt 有值：選距 reference_rt 最近的 scan。
      適用於有 ISTD pair 的 analyte，傳入 ISTD 的 anchor_rt 以區分同 RT
      窗口內的異構體（如 5-medC vs N4-medC）。
    """
    rt_min = max(0.0, rt_center - search_margin_min)
    rt_max = rt_center + search_margin_min
    expected_product = precursor_mz - neutral_loss_da
    diagnostic_ppm = max(3.0 * nl_ppm_max, NL_DIAGNOSTIC_PPM_FLOOR)

    best_rt: float | None = None
    if reference_rt is None:
        best_base_peak: float = -1.0
    else:
        best_distance: float = float("inf")

    for event in raw.iter_ms2_scans(rt_min, rt_max):
        if event.parse_error is not None or event.scan is None:
            continue
        if abs(event.scan.precursor_mz - precursor_mz) > ms2_precursor_tol_da:
            continue
        ppm = _best_product_ppm(
            event.scan,
            expected_product=expected_product,
            min_intensity_ratio=nl_min_intensity_ratio,
            diagnostic_ppm=diagnostic_ppm,
        )
        if ppm is None or ppm > nl_ppm_max:
            continue
        if reference_rt is None:
            if event.scan.base_peak > best_base_peak:
                best_base_peak = event.scan.base_peak
                best_rt = event.scan.rt
        else:
            distance = abs(event.scan.rt - reference_rt)
            if distance < best_distance:
                best_distance = distance
                best_rt = event.scan.rt

    return best_rt


def check_nl(
    raw: MS2ScanSource,
    *,
    precursor_mz: float,
    rt_min: float,
    rt_max: float,
    neutral_loss_da: float,
    nl_ppm_warn: float,
    nl_ppm_max: float,
    ms2_precursor_tol_da: float,
    nl_min_intensity_ratio: float,
) -> NLResult:
    expected_product = precursor_mz - neutral_loss_da
    diagnostic_ppm = max(3.0 * nl_ppm_max, NL_DIAGNOSTIC_PPM_FLOOR)

    valid_count = 0
    parse_error_count = 0
    matched_count = 0
    best_ppm: float | None = None
    best_scan_rt: float | None = None

    for event in raw.iter_ms2_scans(rt_min, rt_max):
        if event.parse_error is not None:
            parse_error_count += 1
            continue
        if event.scan is None:
            continue

        valid_count += 1
        if abs(event.scan.precursor_mz - precursor_mz) > ms2_precursor_tol_da:
            continue

        matched_count += 1
        candidate_ppm = _best_product_ppm(
            event.scan,
            expected_product=expected_product,
            min_intensity_ratio=nl_min_intensity_ratio,
            diagnostic_ppm=diagnostic_ppm,
        )
        if candidate_ppm is not None and (best_ppm is None or candidate_ppm < best_ppm):
            best_ppm = candidate_ppm
            best_scan_rt = event.scan.rt

    status = _classify_nl_result(
        matched_scan_count=matched_count,
        best_ppm=best_ppm,
        nl_ppm_warn=nl_ppm_warn,
        nl_ppm_max=nl_ppm_max,
    )
    return NLResult(
        status=status,
        best_ppm=best_ppm,
        best_scan_rt=best_scan_rt,
        valid_ms2_scan_count=valid_count,
        parse_error_count=parse_error_count,
        matched_scan_count=matched_count,
    )


def _best_product_ppm(
    scan: Ms2Scan,
    *,
    expected_product: float,
    min_intensity_ratio: float,
    diagnostic_ppm: float,
) -> float | None:
    if expected_product <= 0.0 or scan.base_peak <= 0.0:
        return None

    masses = np.asarray(scan.masses, dtype=float)
    intensities = np.asarray(scan.intensities, dtype=float)
    intensity_floor = scan.base_peak * min_intensity_ratio
    best_ppm: float | None = None

    for mass, intensity in zip(masses, intensities):
        if intensity < intensity_floor:
            continue
        ppm = abs(float(mass) - expected_product) / expected_product * 1_000_000.0
        if ppm <= diagnostic_ppm and (best_ppm is None or ppm < best_ppm):
            best_ppm = ppm
    return best_ppm


def _classify_nl_result(
    *,
    matched_scan_count: int,
    best_ppm: float | None,
    nl_ppm_warn: float,
    nl_ppm_max: float,
) -> NLStatus:
    if matched_scan_count == 0:
        return "NO_MS2"
    if best_ppm is None or best_ppm > nl_ppm_max:
        return "NL_FAIL"
    if best_ppm > nl_ppm_warn:
        return "WARN"
    return "OK"
