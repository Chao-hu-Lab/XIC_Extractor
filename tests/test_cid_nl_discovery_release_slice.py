from __future__ import annotations

from types import SimpleNamespace

from scripts import check_cid_nl_discovery_release_slice as release_slice


def test_current_cid_nl_discovery_release_slice_is_stable() -> None:
    assert release_slice.check_cid_nl_discovery_release_slice() == []


def test_release_slice_propagates_artifact_retention_problems(monkeypatch) -> None:
    monkeypatch.setattr(
        release_slice,
        "check_validation_artifact_retention",
        lambda: SimpleNamespace(problems=("inventory drift",)),
    )

    problems = release_slice.check_cid_nl_discovery_release_slice()

    assert "validation_artifact_retention: inventory drift" in problems


def test_release_slice_propagates_bounded_lane_problems(monkeypatch) -> None:
    monkeypatch.setattr(
        release_slice,
        "check_bounded_product_lanes",
        lambda: ["lane drift"],
    )

    problems = release_slice.check_cid_nl_discovery_release_slice()

    assert "bounded_product_lanes: lane drift" in problems
