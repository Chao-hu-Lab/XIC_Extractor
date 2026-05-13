from __future__ import annotations

from dataclasses import dataclass

import pytest

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.edge_scoring import evaluate_owner_edge
from xic_extractor.alignment.ownership_models import (
    IdentityEvent,
    SampleLocalMS1Owner,
)


@dataclass(frozen=True)
class _DriftLookup:
    deltas: dict[str, float]
    orders: dict[str, int]
    source: str = "batch_istd_trend"

    def sample_delta_min(self, sample_stem: str) -> float | None:
        return self.deltas.get(sample_stem)

    def injection_order(self, sample_stem: str) -> int | None:
        return self.orders.get(sample_stem)


def _owner(
    sample_stem: str,
    *,
    neutral_loss_tag: str = "DNA_dR",
    precursor_mz: float = 250.0,
    product_mz: float = 150.0,
    observed_neutral_loss_da: float = 100.0,
    owner_apex_rt: float = 10.00,
    owner_area: float = 1000.0,
    evidence_score: int = 80,
    seed_event_count: int = 2,
    assignment_reason: str = "same_apex_window",
    identity_conflict: bool = False,
    support_seed_rt: float | None = None,
) -> SampleLocalMS1Owner:
    primary = IdentityEvent(
        candidate_id=f"{sample_stem}#primary",
        sample_stem=sample_stem,
        raw_file=f"{sample_stem}.raw",
        neutral_loss_tag=neutral_loss_tag,
        precursor_mz=precursor_mz,
        product_mz=product_mz,
        observed_neutral_loss_da=observed_neutral_loss_da,
        seed_rt=owner_apex_rt,
        evidence_score=evidence_score,
        seed_event_count=seed_event_count,
    )
    support = ()
    if support_seed_rt is not None:
        support = (
            IdentityEvent(
                candidate_id=f"{sample_stem}#support",
                sample_stem=sample_stem,
                raw_file=f"{sample_stem}.raw",
                neutral_loss_tag=neutral_loss_tag,
                precursor_mz=precursor_mz,
                product_mz=product_mz,
                observed_neutral_loss_da=observed_neutral_loss_da,
                seed_rt=support_seed_rt,
                evidence_score=evidence_score,
                seed_event_count=1,
            ),
        )
    return SampleLocalMS1Owner(
        owner_id=f"OWN-{sample_stem}",
        sample_stem=sample_stem,
        raw_file=f"{sample_stem}.raw",
        precursor_mz=precursor_mz,
        owner_apex_rt=owner_apex_rt,
        owner_peak_start_rt=owner_apex_rt - 0.05,
        owner_peak_end_rt=owner_apex_rt + 0.05,
        owner_area=owner_area,
        owner_height=100.0,
        primary_identity_event=primary,
        supporting_events=support,
        identity_conflict=identity_conflict,
        assignment_reason=assignment_reason,
    )


def test_blocked_edge_reports_neutral_loss_reason() -> None:
    edge = evaluate_owner_edge(
        _owner("s1", neutral_loss_tag="DNA_dR"),
        _owner("s2", neutral_loss_tag="DNA_base_loss"),
        config=AlignmentConfig(),
    )

    assert edge.decision == "blocked_edge"
    assert edge.failure_reason == "neutral_loss_tag_mismatch"
    assert edge.reason == "blocked: neutral_loss_tag_mismatch"
    assert edge.score == 0


@pytest.mark.parametrize(
    ("left", "right", "expected_reason"),
    [
        (_owner("s1"), _owner("s1"), "same_sample"),
        (
            _owner("s1", precursor_mz=250.0000),
            _owner("s2", precursor_mz=250.0200),
            "precursor_mz_out_of_tolerance",
        ),
        (
            _owner("s1", product_mz=150.0000),
            _owner("s2", product_mz=150.0100),
            "product_mz_out_of_tolerance",
        ),
        (
            _owner("s1", observed_neutral_loss_da=100.0000),
            _owner("s2", observed_neutral_loss_da=100.0100),
            "observed_loss_out_of_tolerance",
        ),
    ],
)
def test_numeric_and_sample_hard_gates(
    left: SampleLocalMS1Owner,
    right: SampleLocalMS1Owner,
    expected_reason: str,
) -> None:
    edge = evaluate_owner_edge(left, right, config=AlignmentConfig())

    assert edge.decision == "blocked_edge"
    assert edge.failure_reason == expected_reason
    assert edge.reason == f"blocked: {expected_reason}"


def test_non_detected_owner_blocks_edge() -> None:
    edge = evaluate_owner_edge(
        _owner("s1"),
        _owner("s2"),
        config=AlignmentConfig(),
        right_detected_owner=False,
    )

    assert edge.decision == "blocked_edge"
    assert edge.failure_reason == "non_detected_owner"


def test_ambiguous_owner_blocks_edge() -> None:
    edge = evaluate_owner_edge(
        _owner("s1"),
        _owner("s2"),
        config=AlignmentConfig(),
        left_ambiguous_owner=True,
    )

    assert edge.decision == "blocked_edge"
    assert edge.failure_reason == "ambiguous_owner"


def test_missing_drift_and_raw_over_strict_window_is_weak() -> None:
    edge = evaluate_owner_edge(
        _owner("s1", owner_apex_rt=10.00),
        _owner("s2", owner_apex_rt=10.75),
        config=AlignmentConfig(preferred_rt_sec=30.0, max_rt_sec=120.0),
    )

    assert edge.decision == "weak_edge"
    assert edge.failure_reason == ""
    assert edge.rt_raw_delta_sec == pytest.approx(45.0)
    assert edge.rt_drift_corrected_delta_sec is None
    assert edge.drift_prior_source == "none"


def test_drift_corrected_close_edge_is_strong_even_when_raw_exceeds_strict() -> None:
    edge = evaluate_owner_edge(
        _owner("s1", owner_apex_rt=10.00),
        _owner("s2", owner_apex_rt=10.75),
        config=AlignmentConfig(preferred_rt_sec=30.0, max_rt_sec=120.0),
        drift_lookup=_DriftLookup(
            deltas={"s1": 0.00, "s2": 0.50},
            orders={"s1": 10, "s2": 13},
        ),
    )

    assert edge.decision == "strong_edge"
    assert edge.rt_raw_delta_sec == pytest.approx(45.0)
    assert edge.rt_drift_corrected_delta_sec == pytest.approx(15.0)
    assert edge.drift_prior_source == "batch_istd_trend"
    assert edge.injection_order_gap == 3
    assert edge.seed_support_level == "strong"
    assert edge.owner_quality == "clean"
    assert edge.score >= 60


def test_weak_seed_support_keeps_hard_pass_edge_weak() -> None:
    edge = evaluate_owner_edge(
        _owner("s1", evidence_score=35, seed_event_count=1),
        _owner("s2", evidence_score=35, seed_event_count=1),
        config=AlignmentConfig(),
    )

    assert edge.decision == "weak_edge"
    assert edge.seed_support_level == "weak"


def test_identity_conflict_blocks_edge() -> None:
    edge = evaluate_owner_edge(
        _owner("s1", identity_conflict=True),
        _owner("s2"),
        config=AlignmentConfig(),
    )

    assert edge.decision == "blocked_edge"
    assert edge.failure_reason == "identity_conflict"


def test_edge_depending_on_backfill_is_blocked() -> None:
    edge = evaluate_owner_edge(
        _owner("s1"),
        _owner("s2"),
        config=AlignmentConfig(),
        edge_depends_on_backfill=True,
    )

    assert edge.decision == "blocked_edge"
    assert edge.failure_reason == "backfill_bridge"
