from collections.abc import Iterator

import numpy as np
import pytest

from xic_extractor.neutral_loss import check_nl, find_nl_anchor_rt
from xic_extractor.raw_reader import Ms2Scan, Ms2ScanEvent

PRECURSOR_MZ = 258.0969
NEUTRAL_LOSS_DA = 131.0405
EXPECTED_PRODUCT_MZ = PRECURSOR_MZ - NEUTRAL_LOSS_DA


def test_check_nl_returns_ok_when_best_ppm_is_at_or_below_warn() -> None:
    raw = _FakeRaw(
        [
            _scan_event(
                precursor_mz=PRECURSOR_MZ,
                masses=[120.0, _mass_at_ppm(EXPECTED_PRODUCT_MZ, 5.0)],
                intensities=[100.0, 80.0],
            )
        ]
    )

    result = _check(raw)

    assert result.status == "OK"
    assert result.best_ppm == pytest.approx(5.0)
    assert result.valid_ms2_scan_count == 1
    assert result.matched_scan_count == 1
    assert result.parse_error_count == 0
    assert result.to_token() == "OK"


def test_check_nl_returns_warn_token_when_ppm_is_between_warn_and_max() -> None:
    raw = _FakeRaw(
        [
            _scan_event(
                precursor_mz=PRECURSOR_MZ,
                masses=[_mass_at_ppm(EXPECTED_PRODUCT_MZ, 12.34)],
                intensities=[100.0],
            )
        ]
    )

    result = _check(raw)

    assert result.status == "WARN"
    assert result.best_ppm == pytest.approx(12.34)
    assert result.to_token() == "WARN_12.3ppm"


def test_check_nl_returns_fail_with_best_ppm_when_product_is_only_diagnostic() -> None:
    raw = _FakeRaw(
        [
            _scan_event(
                precursor_mz=PRECURSOR_MZ,
                masses=[_mass_at_ppm(EXPECTED_PRODUCT_MZ, 55.0)],
                intensities=[100.0],
            )
        ]
    )

    result = _check(raw)

    assert result.status == "NL_FAIL"
    assert result.best_ppm == pytest.approx(55.0)
    assert result.to_token() == "NL_FAIL"


def test_check_nl_returns_fail_without_best_ppm_when_no_product_is_diagnostic() -> None:
    raw = _FakeRaw(
        [
            _scan_event(
                precursor_mz=PRECURSOR_MZ,
                masses=[_mass_at_ppm(EXPECTED_PRODUCT_MZ, 1200.0)],
                intensities=[100.0],
            )
        ]
    )

    result = _check(raw)

    assert result.status == "NL_FAIL"
    assert result.best_ppm is None
    assert result.matched_scan_count == 1


def test_check_nl_returns_no_ms2_when_no_scan_matches_precursor() -> None:
    raw = _FakeRaw(
        [
            _scan_event(
                precursor_mz=PRECURSOR_MZ + 2.0,
                masses=[_mass_at_ppm(EXPECTED_PRODUCT_MZ, 1.0)],
                intensities=[100.0],
            )
        ]
    )

    result = _check(raw)

    assert result.status == "NO_MS2"
    assert result.best_ppm is None
    assert result.valid_ms2_scan_count == 1
    assert result.matched_scan_count == 0
    assert result.to_token() == "NO_MS2"


def test_check_nl_skips_parse_errors_but_counts_them() -> None:
    raw = _FakeRaw(
        [
            Ms2ScanEvent(scan=None, parse_error="bad filter", scan_number=7),
            _scan_event(
                scan_number=8,
                precursor_mz=PRECURSOR_MZ,
                masses=[_mass_at_ppm(EXPECTED_PRODUCT_MZ, 1.0)],
                intensities=[100.0],
            ),
        ]
    )

    result = _check(raw)

    assert result.status == "OK"
    assert result.parse_error_count == 1
    assert result.valid_ms2_scan_count == 1
    assert result.matched_scan_count == 1


def test_check_nl_ignores_product_below_intensity_ratio() -> None:
    raw = _FakeRaw(
        [
            _scan_event(
                precursor_mz=PRECURSOR_MZ,
                masses=[EXPECTED_PRODUCT_MZ, 150.0],
                intensities=[4.0, 100.0],
            )
        ]
    )

    result = _check(raw)

    assert result.status == "NL_FAIL"
    assert result.best_ppm is None


def test_check_nl_ignores_all_zero_spectrum_without_divide_by_zero() -> None:
    raw = _FakeRaw(
        [
            _scan_event(
                precursor_mz=PRECURSOR_MZ,
                masses=[EXPECTED_PRODUCT_MZ],
                intensities=[0.0],
            )
        ]
    )

    result = _check(raw)

    assert result.status == "NL_FAIL"
    assert result.best_ppm is None
    assert result.matched_scan_count == 1


def test_find_nl_anchor_rt_without_reference_uses_strongest_base_peak() -> None:
    raw = _FakeRaw(
        [
            _scan_event(
                precursor_mz=PRECURSOR_MZ,
                rt=8.10,
                masses=[EXPECTED_PRODUCT_MZ, 150.0],
                intensities=[100.0, 250.0],
            ),
            _scan_event(
                precursor_mz=PRECURSOR_MZ,
                rt=8.90,
                masses=[EXPECTED_PRODUCT_MZ, 150.0],
                intensities=[80.0, 900.0],
            ),
        ]
    )

    anchor_rt = _anchor(raw)

    assert anchor_rt == pytest.approx(8.90)


def test_find_nl_anchor_rt_with_reference_uses_nearest_scan_even_when_weaker() -> None:
    raw = _FakeRaw(
        [
            _scan_event(
                precursor_mz=PRECURSOR_MZ,
                rt=8.10,
                masses=[EXPECTED_PRODUCT_MZ, 150.0],
                intensities=[80.0, 900.0],
            ),
            _scan_event(
                precursor_mz=PRECURSOR_MZ,
                rt=8.75,
                masses=[EXPECTED_PRODUCT_MZ, 150.0],
                intensities=[100.0, 250.0],
            ),
        ]
    )

    anchor_rt = _anchor(raw, reference_rt=8.80)

    assert anchor_rt == pytest.approx(8.75)


def test_find_nl_anchor_rt_with_reference_breaks_distance_tie_by_base_peak() -> None:
    raw = _FakeRaw(
        [
            _scan_event(
                precursor_mz=PRECURSOR_MZ,
                rt=8.00,
                masses=[EXPECTED_PRODUCT_MZ, 150.0],
                intensities=[100.0, 250.0],
            ),
            _scan_event(
                precursor_mz=PRECURSOR_MZ,
                rt=9.00,
                masses=[EXPECTED_PRODUCT_MZ, 150.0],
                intensities=[80.0, 900.0],
            ),
        ]
    )

    anchor_rt = _anchor(raw, reference_rt=8.50)

    assert anchor_rt == pytest.approx(9.00)


def _check(raw: "_FakeRaw"):
    return check_nl(
        raw,
        precursor_mz=PRECURSOR_MZ,
        rt_min=8.0,
        rt_max=9.0,
        neutral_loss_da=NEUTRAL_LOSS_DA,
        nl_ppm_warn=10.0,
        nl_ppm_max=20.0,
        ms2_precursor_tol_da=0.5,
        nl_min_intensity_ratio=0.05,
    )


def _anchor(raw: "_FakeRaw", reference_rt: float | None = None) -> float | None:
    return find_nl_anchor_rt(
        raw,
        precursor_mz=PRECURSOR_MZ,
        rt_center=8.5,
        search_margin_min=1.0,
        neutral_loss_da=NEUTRAL_LOSS_DA,
        nl_ppm_max=20.0,
        ms2_precursor_tol_da=0.5,
        nl_min_intensity_ratio=0.05,
        reference_rt=reference_rt,
    )


def _mass_at_ppm(mass: float, ppm: float) -> float:
    return mass * (1.0 + ppm / 1_000_000.0)


def _scan_event(
    *,
    precursor_mz: float,
    masses: list[float],
    intensities: list[float],
    scan_number: int = 1,
    rt: float = 8.5,
) -> Ms2ScanEvent:
    return Ms2ScanEvent(
        scan=Ms2Scan(
            scan_number=scan_number,
            rt=rt,
            precursor_mz=precursor_mz,
            masses=np.asarray(masses, dtype=float),
            intensities=np.asarray(intensities, dtype=float),
            base_peak=max(intensities) if intensities else 0.0,
        ),
        parse_error=None,
        scan_number=scan_number,
    )


class _FakeRaw:
    def __init__(self, events: list[Ms2ScanEvent]) -> None:
        self.events = events
        self.requested_window: tuple[float, float] | None = None

    def iter_ms2_scans(self, rt_min: float, rt_max: float) -> Iterator[Ms2ScanEvent]:
        self.requested_window = (rt_min, rt_max)
        yield from self.events
