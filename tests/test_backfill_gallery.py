"""Wiring tests for the GUI backfill review gallery orchestrator.

The three underlying steps are exercised elsewhere; here we pin the composition:
the retained gate's review queue drives whether the overlay render runs, and the
overlay summary is threaded into the reconciliation gallery only when families
were actually queued.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from gui.workers import backfill_gallery as bg


@dataclass
class _FakeGate:
    tsv: Path
    review_overlay_queue_tsv: Path


@dataclass
class _FakeGalleryOutputs:
    gallery_html: Path


def _write_queue(path: Path, family_count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["feature_family_id"])
        for index in range(family_count):
            writer.writerow([f"F{index}"])


def _inputs(tmp_path: Path) -> bg.BackfillGalleryInputs:
    return bg.BackfillGalleryInputs(
        alignment_review_tsv=tmp_path / "alignment_review.tsv",
        alignment_cells_tsv=tmp_path / "alignment_cells.tsv",
        alignment_matrix_tsv=tmp_path / "alignment_matrix.tsv",
        raw_dir=tmp_path / "raw",
        dll_dir=tmp_path / "dll",
        backfill_seed_audit_tsv=tmp_path / "seed_audit.tsv",
    )


def _patch_steps(
    monkeypatch: pytest.MonkeyPatch,
    *,
    family_count: int,
    calls: dict[str, Any],
) -> Path:
    def fake_gate(**kwargs: Any) -> _FakeGate:
        output_dir = kwargs["output_dir"]
        queue = output_dir / "alignment_retained_backfill_overlay_review_queue.tsv"
        _write_queue(queue, family_count)
        gate_tsv = output_dir / "alignment_retained_backfill_evidence_gate.tsv"
        gate_tsv.write_text("feature_family_id\n", encoding="utf-8")
        return _FakeGate(tsv=gate_tsv, review_overlay_queue_tsv=queue)

    def fake_overlay(**kwargs: Any) -> list[dict[str, Any]]:
        calls["overlay"] = kwargs
        return [{"status": "success"}]

    def fake_write_outputs(output_dir: Path, rows: Any, **_: Any) -> None:
        calls["write_outputs"] = output_dir
        (output_dir / "family_ms1_overlay_batch_summary.tsv").parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        (output_dir / "family_ms1_overlay_batch_summary.tsv").write_text(
            "feature_family_id\n",
            encoding="utf-8",
        )

    def fake_gallery(**kwargs: Any) -> _FakeGalleryOutputs:
        calls["gallery"] = kwargs
        html = kwargs["output_dir"] / "backfill_evidence_reconciliation_gallery.html"
        html.parent.mkdir(parents=True, exist_ok=True)
        html.write_text("<html></html>", encoding="utf-8")
        return _FakeGalleryOutputs(gallery_html=html)

    monkeypatch.setattr(bg, "run_retained_backfill_evidence_gate", fake_gate)
    monkeypatch.setattr(
        bg.family_ms1_overlay_batch,
        "run_overlay_batch",
        fake_overlay,
    )
    monkeypatch.setattr(
        bg.family_ms1_overlay_batch,
        "_write_outputs",
        fake_write_outputs,
    )
    monkeypatch.setattr(bg, "run_reconciliation_gallery", fake_gallery)
    return Path()


def test_overlay_render_runs_and_feeds_gallery_when_families_queued(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, Any] = {}
    _patch_steps(monkeypatch, family_count=3, calls=calls)

    html = bg.build_backfill_review_gallery(
        _inputs(tmp_path),
        output_dir=tmp_path / "gallery",
        dpi=140,
        workers=4,
    )

    assert html.exists()
    # Overlay render was driven by the queued family count, PDF off.
    assert calls["overlay"]["limit"] == 3
    assert calls["overlay"]["write_pdf"] is False
    assert calls["overlay"]["dpi"] == 140
    assert calls["overlay"]["workers"] == 4
    # The rendered overlay summary is threaded into the gallery.
    summary = (
        tmp_path / "gallery" / "family_ms1_overlay_batch"
        / "family_ms1_overlay_batch_summary.tsv"
    )
    assert calls["gallery"]["overlay_batch_summary_tsvs"] == (summary,)


def test_overlay_render_skipped_when_no_family_queued(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, Any] = {}
    _patch_steps(monkeypatch, family_count=0, calls=calls)

    html = bg.build_backfill_review_gallery(
        _inputs(tmp_path),
        output_dir=tmp_path / "gallery",
        workers=4,
    )

    assert html.exists()
    assert "overlay" not in calls  # render skipped entirely
    assert calls["gallery"]["overlay_batch_summary_tsvs"] == ()
