"""Guards that the diagnostic viz layer never perturbs Gaussian15 detection.

The drift-aware / sub-threshold review surface re-implements parts of
``ms1_peak_modes`` for *display*. These tests pin that the diagnostic helpers
(a) agree with the real detector on what is an accepted peak, (b) are pure, and
(c) do not mutate their inputs. If the detector changes, these fail loudly so
the diagnostic replica is updated in lockstep.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass

from tools.diagnostics import changed_row_mode_overlay_review as review
from xic_extractor.alignment.shared_peak_identity_explanation import ms1_peak_modes


@dataclass(frozen=True)
class _DriftLookup:
    deltas: dict[str, float]
    source: str = "targeted_istd_trend"

    def sample_delta_min(self, sample_stem: str) -> float | None:
        return self.deltas.get(sample_stem)

    def injection_order(self, sample_stem: str) -> int | None:
        return None


def _trace_with_shoulder() -> dict[str, object]:
    intensities = [
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
        2.0, 8.0, 30.0, 70.0, 100.0, 70.0, 30.0, 8.0, 2.0,
        0.0, 0.0,
        4.0, 9.0, 13.0, 14.0, 13.0, 9.0, 4.0,
        0.0, 0.0, 0.0, 0.0,
    ]
    rt = [8.0 + index * 0.04 for index in range(len(intensities))]
    return {
        "sample_stem": "S1",
        "status": "detected",
        "rt": rt,
        "intensity": intensities,
    }


def test_subthreshold_report_accepted_set_matches_detector() -> None:
    trace = _trace_with_shoulder()

    detector_apexes = sorted(
        observation.apex_rt
        for observation in ms1_peak_modes.gaussian15_peak_observations(trace)
    )
    report = review.subthreshold_candidate_report(trace)
    accepted_apexes = sorted(
        candidate.apex_rt for candidate in report if candidate.accepted
    )

    assert accepted_apexes == detector_apexes
    assert len(detector_apexes) >= 1


def test_subthreshold_report_surfaces_rejected_candidate_with_reason() -> None:
    report = review.subthreshold_candidate_report(_trace_with_shoulder())

    rejected = [candidate for candidate in report if not candidate.accepted]
    assert rejected, "expected at least one sub-threshold (missed-peak) candidate"
    assert all(candidate.reject_reasons for candidate in rejected)
    assert any(
        any(reason.startswith("height") for reason in candidate.reject_reasons)
        for candidate in rejected
    )


def test_subthreshold_report_is_deterministic_and_pure() -> None:
    trace = _trace_with_shoulder()
    before = copy.deepcopy(trace)

    first = review.subthreshold_candidate_report(trace)
    second = review.subthreshold_candidate_report(trace)

    assert first == second
    assert trace == before  # input not mutated


def test_drift_corrected_rt_shifts_by_sample_delta() -> None:
    lookup = _DriftLookup(deltas={"S1": 0.30})

    assert review._drift_corrected_rt(9.00, "S1", lookup) == 8.70
    assert review._drift_corrected_rt(9.00, "missing", lookup) is None
    assert review._drift_corrected_rt(9.00, "S1", None) is None
    assert review._drift_corrected_rt(None, "S1", lookup) is None


def _two_modes() -> tuple[ms1_peak_modes.Gaussian15PeakModeWindow, ...]:
    return (
        ms1_peak_modes.Gaussian15PeakModeWindow(
            mode_id="gaussian15_mode_1_8.00min",
            start_rt=7.8,
            end_rt=8.5,
            apex_rt=8.0,
            trace_peak_count=2,
            detected_seed_count=2,
        ),
        ms1_peak_modes.Gaussian15PeakModeWindow(
            mode_id="gaussian15_mode_2_9.00min",
            start_rt=8.5,
            end_rt=9.2,
            apex_rt=9.0,
            trace_peak_count=2,
            detected_seed_count=2,
        ),
    )


def test_drift_verdict_flags_false_split_when_modes_converge() -> None:
    sample_rows = [
        {"sample_stem": "A", "cell_apex_rt": "8.00"},
        {"sample_stem": "B", "cell_apex_rt": "8.02"},
        {"sample_stem": "C", "cell_apex_rt": "9.00"},
        {"sample_stem": "D", "cell_apex_rt": "9.02"},
    ]
    # A/B drift +0.5 late, C/D drift -0.45 early -> corrected apexes collapse.
    lookup = _DriftLookup(
        deltas={"A": -0.50, "B": -0.50, "C": 0.45, "D": 0.45},
    )

    verdict = review._drift_diagnostic_verdict(
        gaussian15_modes=_two_modes(),
        sample_rows=sample_rows,
        drift_lookup=lookup,
    )

    assert verdict == "modes_converge_after_drift|likely_false_split"


def test_drift_verdict_keeps_true_multimodal_when_modes_persist() -> None:
    sample_rows = [
        {"sample_stem": "A", "cell_apex_rt": "8.00"},
        {"sample_stem": "B", "cell_apex_rt": "8.02"},
        {"sample_stem": "C", "cell_apex_rt": "9.00"},
        {"sample_stem": "D", "cell_apex_rt": "9.02"},
    ]
    lookup = _DriftLookup(deltas={"A": 0.01, "B": 0.0, "C": -0.01, "D": 0.0})

    verdict = review._drift_diagnostic_verdict(
        gaussian15_modes=_two_modes(),
        sample_rows=sample_rows,
        drift_lookup=lookup,
    )

    assert verdict == "modes_persist_after_drift|likely_true_multimodal"


def test_drift_verdict_handles_single_mode_and_missing_drift() -> None:
    one_mode = _two_modes()[:1]
    assert (
        review._drift_diagnostic_verdict(
            gaussian15_modes=one_mode,
            sample_rows=[{"sample_stem": "A", "cell_apex_rt": "8.0"}],
            drift_lookup=_DriftLookup(deltas={"A": 0.0}),
        )
        == "single_mode"
    )
    assert (
        review._drift_diagnostic_verdict(
            gaussian15_modes=_two_modes(),
            sample_rows=[{"sample_stem": "A", "cell_apex_rt": "8.0"}],
            drift_lookup=None,
        )
        == "drift_unavailable|raw_modes_only"
    )
