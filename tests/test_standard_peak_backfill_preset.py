from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from tools.diagnostics import standard_peak_backfill_preset
from xic_extractor.diagnostics.retained_backfill_evidence_gate import (
    RetainedBackfillGateOutputs,
)
from xic_extractor.diagnostics.standard_peak_backfill_chunk_consolidation import (
    StandardPeakChunkConsolidationOutputs,
)
from xic_extractor.diagnostics.timing import TimingRecorder


def test_standard_peak_backfill_preset_skips_machine_pipeline_without_queue(
    monkeypatch,
    tmp_path: Path,
) -> None:
    alignment_dir = _write_alignment_artifacts(tmp_path)
    output_dir = tmp_path / "preset"

    def fake_gate(**_kwargs):
        gate_dir = output_dir / "retained_backfill_evidence_gate"
        gate_dir.mkdir(parents=True, exist_ok=True)
        gate_tsv = gate_dir / "retained_backfill_evidence_gate.tsv"
        queue = gate_dir / "review_overlay_queue.tsv"
        gate_tsv.write_text("feature_family_id\n", encoding="utf-8")
        queue.write_text("feature_family_id\n", encoding="utf-8")
        missing = gate_dir / "missing_overlay_queue.tsv"
        missing.write_text("feature_family_id\n", encoding="utf-8")
        return RetainedBackfillGateOutputs(
            tsv=gate_tsv,
            json=gate_dir / "retained_backfill_evidence_gate.json",
            missing_overlay_queue_tsv=missing,
            review_overlay_queue_tsv=queue,
        )

    def fail_machine(**_kwargs):
        raise AssertionError("machine pipeline should not run without queue rows")

    monkeypatch.setattr(
        standard_peak_backfill_preset,
        "run_retained_backfill_evidence_gate",
        fake_gate,
    )
    outputs = standard_peak_backfill_preset.run_standard_peak_backfill_preset(
        alignment_dir=alignment_dir,
        raw_dir=tmp_path / "raws",
        dll_dir=tmp_path / "dll",
        output_dir=output_dir,
        machine_pipeline_runner=fail_machine,
    )

    summary = json.loads(outputs.summary_json.read_text(encoding="utf-8"))
    assert summary["status"] == "pass"
    assert summary["review_queue_row_count"] == "0"
    assert summary["chunk_count"] == "0"
    assert summary["status_reasons"] == "no_standard_peak_backfill_review_rows"


def test_standard_peak_backfill_preset_chunks_and_publishes_alignment_output(
    monkeypatch,
    tmp_path: Path,
) -> None:
    alignment_dir = _write_alignment_artifacts(tmp_path)
    raw_dir = tmp_path / "raws"
    dll_dir = tmp_path / "dll"
    output_dir = tmp_path / "preset"
    raw_dir.mkdir()
    dll_dir.mkdir()
    machine_calls: list[dict[str, object]] = []
    consolidation_calls: list[dict[str, object]] = []

    def fake_gate(**_kwargs):
        gate_dir = output_dir / "retained_backfill_evidence_gate"
        gate_dir.mkdir(parents=True, exist_ok=True)
        gate_tsv = gate_dir / "retained_backfill_evidence_gate.tsv"
        queue = gate_dir / "review_overlay_queue.tsv"
        gate_tsv.write_text("feature_family_id\n", encoding="utf-8")
        queue.write_text(
            "feature_family_id\nFAM1\nFAM2\nFAM3\n",
            encoding="utf-8",
        )
        missing = gate_dir / "missing_overlay_queue.tsv"
        missing.write_text("feature_family_id\n", encoding="utf-8")
        return RetainedBackfillGateOutputs(
            tsv=gate_tsv,
            json=gate_dir / "retained_backfill_evidence_gate.json",
            missing_overlay_queue_tsv=missing,
            review_overlay_queue_tsv=queue,
        )

    def fake_machine(**kwargs):
        machine_calls.append(dict(kwargs))
        summary_path = Path(kwargs["output_dir"]) / "summary.json"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text('{"status": "pass"}', encoding="utf-8")
        return summary_path

    def fake_consolidation(**kwargs):
        consolidation_calls.append(dict(kwargs))
        output = Path(kwargs["output_dir"])
        output.mkdir(parents=True, exist_ok=True)
        summary_json = output / "summary.json"
        summary_json.write_text(
            '{"status": "pass", "matrix_cells_written": 3}',
            encoding="utf-8",
        )
        summary_tsv = output / "summary.tsv"
        summary_tsv.write_text("status\npass\n", encoding="utf-8")
        shadow_tsv = output / "consolidated_shadow_projection_cells.tsv"
        shadow_tsv.write_text("x\n", encoding="utf-8")
        gallery = output / "gallery.html"
        gallery.write_text("<html></html>", encoding="utf-8")
        return StandardPeakChunkConsolidationOutputs(
            summary_tsv=summary_tsv,
            summary_json=summary_json,
            status="pass",
            merged_shadow_projection_cells_tsv=shadow_tsv,
            productization=SimpleNamespace(reconciliation_gallery_html=gallery),
            formal_product_output_dir=output / "formal",
            formal_product_manifest_json=output / "formal_manifest.json",
            published_alignment_output_dir=alignment_dir,
            published_alignment_manifest_json=output / "publish_manifest.json",
        )

    monkeypatch.setattr(
        standard_peak_backfill_preset,
        "run_retained_backfill_evidence_gate",
        fake_gate,
    )
    outputs = standard_peak_backfill_preset.run_standard_peak_backfill_preset(
        alignment_dir=alignment_dir,
        raw_dir=raw_dir,
        dll_dir=dll_dir,
        output_dir=output_dir,
        source_run_id="preset:test",
        chunk_size=2,
        write_gallery=True,
        machine_pipeline_runner=fake_machine,
        consolidation_runner=fake_consolidation,
    )

    assert [call["start_rank"] for call in machine_calls] == [1, 3]
    assert [call["limit"] for call in machine_calls] == [2, 1]
    assert all(call["raw_dir"] == raw_dir for call in machine_calls)
    assert all(call["dll_dir"] == dll_dir for call in machine_calls)
    assert consolidation_calls[0]["publish_to_source_alignment_output"] is True
    assert (
        consolidation_calls[0]["publish_alignment_matrix_tsv"]
        == alignment_dir / "alignment_matrix.tsv"
    )
    assert (
        consolidation_calls[0]["publish_alignment_matrix_identity_tsv"]
        == alignment_dir / "alignment_matrix_identity.tsv"
    )
    summary = json.loads(outputs.summary_json.read_text(encoding="utf-8"))
    assert summary["status"] == "pass"
    assert summary["review_queue_row_count"] == "3"
    assert summary["chunk_count"] == "2"
    assert summary["matrix_cells_written"] == "3"
    assert outputs.published_alignment_manifest_json == output_dir / (
        "consolidated/publish_manifest.json"
    )
    assert outputs.gallery_html == output_dir / "consolidated/gallery.html"


def test_standard_peak_backfill_preset_matrix_only_uses_evidence_only_chunks(
    monkeypatch,
    tmp_path: Path,
) -> None:
    alignment_dir = _write_alignment_artifacts(tmp_path)
    raw_dir = tmp_path / "raws"
    dll_dir = tmp_path / "dll"
    output_dir = tmp_path / "preset"
    raw_dir.mkdir()
    dll_dir.mkdir()
    machine_calls: list[dict[str, object]] = []
    consolidation_calls: list[dict[str, object]] = []

    def fake_gate(**_kwargs):
        gate_dir = output_dir / "retained_backfill_evidence_gate"
        gate_dir.mkdir(parents=True, exist_ok=True)
        gate_tsv = gate_dir / "retained_backfill_evidence_gate.tsv"
        queue = gate_dir / "review_overlay_queue.tsv"
        gate_tsv.write_text("feature_family_id\n", encoding="utf-8")
        queue.write_text("feature_family_id\nFAM1\nFAM2\n", encoding="utf-8")
        missing = gate_dir / "missing_overlay_queue.tsv"
        missing.write_text("feature_family_id\n", encoding="utf-8")
        return RetainedBackfillGateOutputs(
            tsv=gate_tsv,
            json=gate_dir / "retained_backfill_evidence_gate.json",
            missing_overlay_queue_tsv=missing,
            review_overlay_queue_tsv=queue,
        )

    def fake_machine(**kwargs):
        machine_calls.append(dict(kwargs))
        summary_path = Path(kwargs["output_dir"]) / (
            "standard_peak_backfill_machine_pipeline_summary.json"
        )
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text('{"status": "pass"}', encoding="utf-8")
        return summary_path

    def fake_consolidation(**kwargs):
        consolidation_calls.append(dict(kwargs))
        output = Path(kwargs["output_dir"])
        output.mkdir(parents=True, exist_ok=True)
        summary_json = output / "summary.json"
        summary_json.write_text(
            '{"status": "pass", "matrix_cells_written": 2}',
            encoding="utf-8",
        )
        return StandardPeakChunkConsolidationOutputs(
            summary_tsv=output / "summary.tsv",
            summary_json=summary_json,
            status="pass",
            merged_shadow_projection_cells_tsv=output / "shadow.tsv",
            productization=SimpleNamespace(reconciliation_gallery_html=None),
            formal_product_output_dir=output / "formal",
            formal_product_manifest_json=output / "formal_manifest.json",
            published_alignment_output_dir=alignment_dir,
            published_alignment_manifest_json=output / "publish_manifest.json",
        )

    monkeypatch.setattr(
        standard_peak_backfill_preset,
        "run_retained_backfill_evidence_gate",
        fake_gate,
    )
    recorder = TimingRecorder("alignment", run_id="test-standard-peak")

    outputs = standard_peak_backfill_preset.run_standard_peak_backfill_preset(
        alignment_dir=alignment_dir,
        raw_dir=raw_dir,
        dll_dir=dll_dir,
        output_dir=output_dir,
        chunk_size=2,
        publication_mode="matrix-only",
        write_gallery=True,
        machine_pipeline_runner=fake_machine,
        consolidation_runner=fake_consolidation,
        timing_recorder=recorder,
    )

    assert machine_calls[0]["publication_mode"] == "matrix-only"
    assert machine_calls[0]["evidence_only"] is True
    assert machine_calls[0]["timing_recorder"] is recorder
    assert consolidation_calls[0]["write_gallery"] is False
    assert outputs.gallery_html is None
    stages = [record.stage for record in recorder.records]
    assert "standard_peak.retained_gate" in stages
    assert "standard_peak.chunk" in stages
    assert "standard_peak.consolidation" in stages
    summary = json.loads(outputs.summary_json.read_text(encoding="utf-8"))
    assert summary["publication_mode"] == "matrix-only"
    assert summary["matrix_cells_written"] == "2"


def test_standard_peak_backfill_preset_reuses_completed_chunk_summaries(
    monkeypatch,
    tmp_path: Path,
) -> None:
    alignment_dir = _write_alignment_artifacts(tmp_path)
    raw_dir = tmp_path / "raws"
    dll_dir = tmp_path / "dll"
    output_dir = tmp_path / "preset"
    raw_dir.mkdir()
    dll_dir.mkdir()
    completed_summary = (
        output_dir
        / "chunks"
        / "r1_2"
        / "standard_peak_backfill_machine_pipeline_summary.json"
    )
    completed_summary.parent.mkdir(parents=True)
    completed_summary.write_text(
        json.dumps(
            {
                "status": "pass",
                "publication_mode": "deep-audit",
                "start_rank": 1,
                "effective_overlay_limit": 2,
                "min_shape_r": 0.95,
                "source_run_id": "standard-peak-backfill-r1-2",
            },
        ),
        encoding="utf-8",
    )
    machine_calls: list[dict[str, object]] = []
    consolidation_calls: list[dict[str, object]] = []

    def fake_gate(**_kwargs):
        gate_dir = output_dir / "retained_backfill_evidence_gate"
        gate_dir.mkdir(parents=True, exist_ok=True)
        gate_tsv = gate_dir / "retained_backfill_evidence_gate.tsv"
        queue = gate_dir / "review_overlay_queue.tsv"
        gate_tsv.write_text("feature_family_id\n", encoding="utf-8")
        queue.write_text("feature_family_id\nFAM1\nFAM2\nFAM3\n", encoding="utf-8")
        missing = gate_dir / "missing_overlay_queue.tsv"
        missing.write_text("feature_family_id\n", encoding="utf-8")
        return RetainedBackfillGateOutputs(
            tsv=gate_tsv,
            json=gate_dir / "retained_backfill_evidence_gate.json",
            missing_overlay_queue_tsv=missing,
            review_overlay_queue_tsv=queue,
        )

    def fake_machine(**kwargs):
        machine_calls.append(dict(kwargs))
        summary_path = Path(kwargs["output_dir"]) / (
            "standard_peak_backfill_machine_pipeline_summary.json"
        )
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text('{"status": "pass"}', encoding="utf-8")
        return summary_path

    def fake_consolidation(**kwargs):
        consolidation_calls.append(dict(kwargs))
        output = Path(kwargs["output_dir"])
        output.mkdir(parents=True, exist_ok=True)
        summary_json = output / "summary.json"
        summary_json.write_text('{"status": "pass"}', encoding="utf-8")
        return StandardPeakChunkConsolidationOutputs(
            summary_tsv=output / "summary.tsv",
            summary_json=summary_json,
            status="pass",
            merged_shadow_projection_cells_tsv=output / "shadow.tsv",
            productization=SimpleNamespace(reconciliation_gallery_html=None),
        )

    monkeypatch.setattr(
        standard_peak_backfill_preset,
        "run_retained_backfill_evidence_gate",
        fake_gate,
    )

    standard_peak_backfill_preset.run_standard_peak_backfill_preset(
        alignment_dir=alignment_dir,
        raw_dir=raw_dir,
        dll_dir=dll_dir,
        output_dir=output_dir,
        chunk_size=2,
        reuse_existing=True,
        machine_pipeline_runner=fake_machine,
        consolidation_runner=fake_consolidation,
    )

    assert [call["start_rank"] for call in machine_calls] == [3]
    assert consolidation_calls[0]["machine_pipeline_summary_jsons"] == (
        completed_summary,
        output_dir
        / "chunks"
        / "r3_3"
        / "standard_peak_backfill_machine_pipeline_summary.json",
    )


def test_standard_peak_backfill_preset_reruns_failed_reuse_summary(
    monkeypatch,
    tmp_path: Path,
) -> None:
    alignment_dir = _write_alignment_artifacts(tmp_path)
    raw_dir = tmp_path / "raws"
    dll_dir = tmp_path / "dll"
    output_dir = tmp_path / "preset"
    raw_dir.mkdir()
    dll_dir.mkdir()
    failed_summary = (
        output_dir
        / "chunks"
        / "r1_2"
        / "standard_peak_backfill_machine_pipeline_summary.json"
    )
    failed_summary.parent.mkdir(parents=True)
    failed_summary.write_text(
        json.dumps(
            {
                "status": "fail",
                "publication_mode": "deep-audit",
                "start_rank": 1,
                "effective_overlay_limit": 2,
                "min_shape_r": 0.95,
                "source_run_id": "preset:test-r1-2",
            },
        ),
        encoding="utf-8",
    )
    machine_calls: list[dict[str, object]] = []
    consolidation_calls: list[dict[str, object]] = []

    def fake_gate(**_kwargs):
        gate_dir = output_dir / "retained_backfill_evidence_gate"
        gate_dir.mkdir(parents=True, exist_ok=True)
        gate_tsv = gate_dir / "retained_backfill_evidence_gate.tsv"
        queue = gate_dir / "review_overlay_queue.tsv"
        gate_tsv.write_text("feature_family_id\n", encoding="utf-8")
        queue.write_text("feature_family_id\nFAM1\nFAM2\nFAM3\n", encoding="utf-8")
        missing = gate_dir / "missing_overlay_queue.tsv"
        missing.write_text("feature_family_id\n", encoding="utf-8")
        return RetainedBackfillGateOutputs(
            tsv=gate_tsv,
            json=gate_dir / "retained_backfill_evidence_gate.json",
            missing_overlay_queue_tsv=missing,
            review_overlay_queue_tsv=queue,
        )

    def fake_machine(**kwargs):
        machine_calls.append(dict(kwargs))
        summary_path = Path(kwargs["output_dir"]) / (
            "standard_peak_backfill_machine_pipeline_summary.json"
        )
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(
            json.dumps(
                {
                    "status": "pass",
                    "publication_mode": kwargs["publication_mode"],
                    "start_rank": kwargs["start_rank"],
                    "effective_overlay_limit": kwargs["limit"],
                    "min_shape_r": kwargs["min_shape_r"],
                    "source_run_id": kwargs["source_run_id"],
                },
            ),
            encoding="utf-8",
        )
        return summary_path

    def fake_consolidation(**kwargs):
        consolidation_calls.append(dict(kwargs))
        output = Path(kwargs["output_dir"])
        output.mkdir(parents=True, exist_ok=True)
        summary_json = output / "summary.json"
        summary_json.write_text('{"status": "pass"}', encoding="utf-8")
        return StandardPeakChunkConsolidationOutputs(
            summary_tsv=output / "summary.tsv",
            summary_json=summary_json,
            status="pass",
            merged_shadow_projection_cells_tsv=output / "shadow.tsv",
            productization=SimpleNamespace(reconciliation_gallery_html=None),
        )

    monkeypatch.setattr(
        standard_peak_backfill_preset,
        "run_retained_backfill_evidence_gate",
        fake_gate,
    )

    standard_peak_backfill_preset.run_standard_peak_backfill_preset(
        alignment_dir=alignment_dir,
        raw_dir=raw_dir,
        dll_dir=dll_dir,
        output_dir=output_dir,
        source_run_id="preset:test",
        chunk_size=2,
        reuse_existing=True,
        machine_pipeline_runner=fake_machine,
        consolidation_runner=fake_consolidation,
    )

    assert [call["start_rank"] for call in machine_calls] == [1, 3]
    assert consolidation_calls[0]["machine_pipeline_summary_jsons"] == (
        output_dir
        / "chunks"
        / "r1_2"
        / "standard_peak_backfill_machine_pipeline_summary.json",
        output_dir
        / "chunks"
        / "r3_3"
        / "standard_peak_backfill_machine_pipeline_summary.json",
    )


def test_standard_peak_backfill_preset_reuse_summary_requires_matching_provenance(
    tmp_path: Path,
) -> None:
    summary_json = tmp_path / "summary.json"
    reusable_summary = {
        "status": "pass",
        "publication_mode": "deep-audit",
        "start_rank": 1,
        "effective_overlay_limit": 2,
        "min_shape_r": 0.95,
        "source_run_id": "preset:test-r1-2",
    }
    summary_json.write_text(json.dumps(reusable_summary), encoding="utf-8")
    assert standard_peak_backfill_preset._can_reuse_chunk_summary(
        summary_json,
        publication_mode="deep-audit",
        start_rank=1,
        limit=2,
        source_run_id="preset:test-r1-2",
        min_shape_r=0.95,
    )

    for field, value in (
        ("status", "fail"),
        ("publication_mode", "matrix-only"),
        ("start_rank", 2),
        ("effective_overlay_limit", 1),
        ("source_run_id", "other-run-r1-2"),
        ("min_shape_r", 0.9),
    ):
        stale_summary = dict(reusable_summary)
        stale_summary[field] = value
        summary_json.write_text(json.dumps(stale_summary), encoding="utf-8")
        assert not standard_peak_backfill_preset._can_reuse_chunk_summary(
            summary_json,
            publication_mode="deep-audit",
            start_rank=1,
            limit=2,
            source_run_id="preset:test-r1-2",
            min_shape_r=0.95,
        )


def _write_alignment_artifacts(tmp_path: Path) -> Path:
    alignment_dir = tmp_path / "alignment"
    alignment_dir.mkdir()
    for name in (
        "alignment_review.tsv",
        "alignment_cells.tsv",
        "alignment_owner_backfill_seed_audit.tsv",
        "alignment_matrix.tsv",
        "alignment_matrix_identity.tsv",
    ):
        (alignment_dir / name).write_text("x\n", encoding="utf-8")
    return alignment_dir
