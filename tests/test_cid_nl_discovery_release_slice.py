from __future__ import annotations

from types import SimpleNamespace

from scripts import check_cid_nl_discovery_release_slice as release_slice


def test_current_cid_nl_discovery_release_slice_is_stable() -> None:
    assert release_slice.check_cid_nl_discovery_release_slice() == []


def test_release_slice_handoff_can_name_later_active_goal(tmp_path) -> None:
    roadmap = tmp_path / "roadmap.md"
    handoff = tmp_path / "handoff.md"
    control_plane = tmp_path / "control-plane.md"
    roadmap.write_text(
        "\n".join(
            [
                "CID-NL Discovery Product Roadmap",
                "Do not reopen broad Backfill",
                "accepted_discovery_cell_count",
                "cid_nl_discovery_full_scope_classification_v1",
                "cid_nl_85raw_universe_closure_v1",
            ]
        ),
        encoding="utf-8",
    )
    handoff.write_text(
        "\n".join(
            [
                "Current objective: Backfill expansion productization.",
                "CID-NL default product activation v1 remains production-ready.",
                "Do not expand CID-NL beyond 95 cells.",
                "Broad Backfill auto-write remains parked.",
            ]
        ),
        encoding="utf-8",
    )
    control_plane.write_text(
        "\n".join(
            [
                "CID-NL Discovery Lane Terminology Cleanup v1",
                "accepted_discovery_cell_count=95",
                "legacy_quant_matrix_effect",
                "CID-NL Discovery Full-Scope Classification v1",
                "CID-NL 85RAW Universe Closure v1",
            ]
        ),
        encoding="utf-8",
    )

    problems: list[str] = []
    release_slice._check_docs(
        roadmap=roadmap,
        handoff=handoff,
        control_plane=control_plane,
        problems=problems,
    )

    assert problems == []


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


def test_release_slice_propagates_85raw_universe_closure_problems(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        release_slice,
        "check_cid_nl_85raw_universe_closure",
        lambda: ["closure drift"],
    )

    problems = release_slice.check_cid_nl_discovery_release_slice()

    assert "85raw_universe_closure: closure drift" in problems
