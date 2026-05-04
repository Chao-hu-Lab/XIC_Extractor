from collections.abc import Iterator
from dataclasses import dataclass
from typing import Literal, Protocol

import numpy as np

from xic_extractor.raw_reader import Ms2Scan, Ms2ScanEvent

NL_DIAGNOSTIC_PPM_FLOOR = 500.0
CandidateMS2AlignmentSource = Literal["region", "apex_fallback", "none"]
NLStatus = Literal["OK", "WARN", "NL_FAIL", "NO_MS2"]
_CANDIDATE_MS2_APEX_FALLBACK_MIN = 0.08


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


@dataclass(frozen=True)
class MS2ProductEvidence:
    scan_rt: float
    precursor_mz: float
    product_mz: float
    product_intensity: float
    product_base_ratio: float
    target_product_ppm: float
    observed_loss_da: float
    observed_loss_error_ppm: float


@dataclass(frozen=True)
class CandidateMS2Evidence:
    ms2_present: bool
    nl_match: bool
    nl_status: NLStatus
    trigger_scan_count: int
    strict_nl_scan_count: int
    best_loss_ppm: float | None
    best_scan_rt: float | None
    best_product_base_ratio: float | None
    alignment_source: CandidateMS2AlignmentSource


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
    diagnostic_ppm = max(3.0 * nl_ppm_max, NL_DIAGNOSTIC_PPM_FLOOR)

    best_rt: float | None = None
    best_base_peak: float = -1.0
    best_distance: float = float("inf")

    for event in raw.iter_ms2_scans(rt_min, rt_max):
        if event.parse_error is not None or event.scan is None:
            continue
        if abs(event.scan.precursor_mz - precursor_mz) > ms2_precursor_tol_da:
            continue
        evidence = _best_product_evidence(
            event.scan,
            target_precursor_mz=precursor_mz,
            neutral_loss_da=neutral_loss_da,
            nl_ppm_max=nl_ppm_max,
            min_intensity_ratio=nl_min_intensity_ratio,
            diagnostic_ppm=diagnostic_ppm,
        )
        if evidence is None or evidence.observed_loss_error_ppm > nl_ppm_max:
            continue
        if reference_rt is None:
            if event.scan.base_peak > best_base_peak:
                best_base_peak = event.scan.base_peak
                best_rt = event.scan.rt
        else:
            distance = abs(event.scan.rt - reference_rt)
            distance_tied = np.isclose(distance, best_distance, rtol=0.0, atol=1e-12)
            if distance < best_distance or (
                distance_tied and event.scan.base_peak > best_base_peak
            ):
                best_distance = distance
                best_base_peak = event.scan.base_peak
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
        evidence = _best_product_evidence(
            event.scan,
            target_precursor_mz=precursor_mz,
            neutral_loss_da=neutral_loss_da,
            nl_ppm_max=nl_ppm_max,
            min_intensity_ratio=nl_min_intensity_ratio,
            diagnostic_ppm=diagnostic_ppm,
        )
        if evidence is not None and (
            best_ppm is None or evidence.observed_loss_error_ppm < best_ppm
        ):
            best_ppm = evidence.observed_loss_error_ppm
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


def collect_candidate_ms2_evidence(
    raw: MS2ScanSource,
    *,
    candidate: object,
    precursor_mz: float,
    neutral_loss_da: float,
    nl_ppm_warn: float,
    nl_ppm_max: float,
    ms2_precursor_tol_da: float,
    nl_min_intensity_ratio: float,
) -> CandidateMS2Evidence:
    peak = getattr(candidate, "peak")
    peak_start = float(getattr(peak, "peak_start"))
    peak_end = float(getattr(peak, "peak_end"))
    apex_rt = float(getattr(candidate, "selection_apex_rt"))
    rt_min = max(0.0, min(peak_start, apex_rt) - _CANDIDATE_MS2_APEX_FALLBACK_MIN)
    rt_max = max(peak_end, apex_rt) + _CANDIDATE_MS2_APEX_FALLBACK_MIN
    diagnostic_ppm = max(3.0 * nl_ppm_max, NL_DIAGNOSTIC_PPM_FLOOR)

    trigger_scan_count = 0
    strict_nl_scan_count = 0
    best_evidence: MS2ProductEvidence | None = None
    region_trigger_seen = False
    fallback_trigger_seen = False

    for event in raw.iter_ms2_scans(rt_min, rt_max):
        if event.parse_error is not None or event.scan is None:
            continue
        scan = event.scan
        if abs(scan.precursor_mz - precursor_mz) > ms2_precursor_tol_da:
            continue

        inside_region = peak_start <= scan.rt <= peak_end
        near_apex = abs(scan.rt - apex_rt) <= _CANDIDATE_MS2_APEX_FALLBACK_MIN
        if not inside_region and not near_apex:
            continue

        trigger_scan_count += 1
        region_trigger_seen = region_trigger_seen or inside_region
        fallback_trigger_seen = fallback_trigger_seen or (not inside_region and near_apex)

        evidence = _best_product_evidence(
            scan,
            target_precursor_mz=precursor_mz,
            neutral_loss_da=neutral_loss_da,
            nl_ppm_max=nl_ppm_max,
            min_intensity_ratio=nl_min_intensity_ratio,
            diagnostic_ppm=diagnostic_ppm,
        )
        if evidence is None:
            continue
        if evidence.observed_loss_error_ppm <= nl_ppm_max:
            strict_nl_scan_count += 1
        if (
            best_evidence is None
            or evidence.observed_loss_error_ppm
            < best_evidence.observed_loss_error_ppm
        ):
            best_evidence = evidence

    best_loss_ppm = (
        best_evidence.observed_loss_error_ppm if best_evidence is not None else None
    )
    nl_status = _classify_nl_result(
        matched_scan_count=trigger_scan_count,
        best_ppm=best_loss_ppm,
        nl_ppm_warn=nl_ppm_warn,
        nl_ppm_max=nl_ppm_max,
    )
    if region_trigger_seen:
        alignment_source: CandidateMS2AlignmentSource = "region"
    elif fallback_trigger_seen:
        alignment_source = "apex_fallback"
    else:
        alignment_source = "none"

    return CandidateMS2Evidence(
        ms2_present=trigger_scan_count > 0,
        nl_match=nl_status in {"OK", "WARN"},
        nl_status=nl_status,
        trigger_scan_count=trigger_scan_count,
        strict_nl_scan_count=strict_nl_scan_count,
        best_loss_ppm=best_loss_ppm,
        best_scan_rt=best_evidence.scan_rt if best_evidence is not None else None,
        best_product_base_ratio=(
            best_evidence.product_base_ratio if best_evidence is not None else None
        ),
        alignment_source=alignment_source,
    )


def _best_product_evidence(
    scan: Ms2Scan,
    *,
    target_precursor_mz: float,
    neutral_loss_da: float,
    nl_ppm_max: float,
    min_intensity_ratio: float,
    diagnostic_ppm: float,
) -> MS2ProductEvidence | None:
    expected_product = scan.precursor_mz - neutral_loss_da
    if expected_product <= 0.0 or target_precursor_mz <= 0.0 or scan.base_peak <= 0.0:
        return None

    masses = np.asarray(scan.masses, dtype=float)
    intensities = np.asarray(scan.intensities, dtype=float)
    intensity_floor = scan.base_peak * min_intensity_ratio

    scan_product_ppm = np.abs(masses - expected_product) / expected_product * 1_000_000.0
    mask = (intensities >= intensity_floor) & (scan_product_ppm <= diagnostic_ppm)
    if not mask.any():
        return None

    target_product = target_precursor_mz - neutral_loss_da
    if target_product <= 0.0:
        return None

    candidates: list[MS2ProductEvidence] = []
    for index in np.flatnonzero(mask):
        product_mz = float(masses[int(index)])
        observed_loss_da = scan.precursor_mz - product_mz
        observed_loss_error_ppm = (
            abs(observed_loss_da - neutral_loss_da) / neutral_loss_da * 1_000_000.0
        )
        if observed_loss_error_ppm > max(diagnostic_ppm, 3.0 * nl_ppm_max):
            continue
        candidates.append(
            MS2ProductEvidence(
                scan_rt=scan.rt,
                precursor_mz=scan.precursor_mz,
                product_mz=product_mz,
                product_intensity=float(intensities[int(index)]),
                product_base_ratio=float(intensities[int(index)] / scan.base_peak),
                target_product_ppm=float(
                    abs(product_mz - target_product) / target_product * 1_000_000.0
                ),
                observed_loss_da=observed_loss_da,
                observed_loss_error_ppm=observed_loss_error_ppm,
            )
        )

    if not candidates:
        return None
    return min(candidates, key=lambda evidence: evidence.observed_loss_error_ppm)


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

    ppm = np.abs(masses - expected_product) / expected_product * 1_000_000.0
    mask = (intensities >= intensity_floor) & (ppm <= diagnostic_ppm)
    if not mask.any():
        return None
    return float(ppm[mask].min())


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
