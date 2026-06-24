from __future__ import annotations

import json
from pathlib import Path

from tools.diagnostics import standard_peak_backfill_machine_pipeline as pipeline


def test_machine_pipeline_wires_post_overlay_steps(
    tmp_path: Path,
    monkeypatch,
) -> None:
    inputs = _write_inputs(tmp_path)
    calls: list[tuple[str, list[str]]] = []

    def fake_shift_batch(**kwargs):
        shift_dir = kwargs["output_dir"]
        shift_dir.mkdir(parents=True, exist_ok=True)
        calls.append(
            (
                "shift_batch",
                [
                    str(kwargs["overlay_batch_summary_tsv"]),
                    str(kwargs["cell_evidence_tsv"]),
                    str(kwargs["start_rank"]),
                    str(kwargs["limit"]),
                    str(kwargs["reuse_existing"]),
                    str(kwargs["source_family_by_family_sample"]),
                    str(kwargs["workers"]),
                    str(kwargs["dpi"]),
                ],
            ),
        )
        return (
            [
                {
                    "rank": "1",
                    "feature_family_id": "FAM001",
                    "seed_group_id": "seed::FAM001",
                    "overlay_status": "success",
                    "alignment_status": "rendered",
                    "output_prefix": "001_fam001_shift_aware",
                    "trace_data_json": str(inputs["trace"]),
                    "source_best_shift_summary_tsv": str(
                        shift_dir
                        / "001_fam001_shift_aware_source_family_best_shift_summary.tsv",
                    ),
                    "source_best_shift_png": str(
                        shift_dir / (
                            "001_fam001_shift_aware_"
                            "source_family_best_shift_alignment.png"
                        ),
                    ),
                    "failure_reason": "",
                }
            ],
            {
                "selected_row_count": 1,
                "status_counts": {"rendered": 1},
                "successful_shift_aware_row_count": 1,
            },
        )

    def fake_step(name: str):
        def _fake(argv):
            calls.append((name, list(argv)))
            _write_step_outputs(name, tmp_path / "out", argv)
            return 0

        return _fake

    monkeypatch.setattr(
        pipeline.family_ms1_alignment_experiment_batch,
        "run_alignment_experiment_batch",
        fake_shift_batch,
    )
    monkeypatch.setattr(
        pipeline.shift_aware_backfill_calibration_pack,
        "main",
        fake_step("pack"),
    )
    monkeypatch.setattr(
        pipeline.shift_aware_standard_peak_gate_calibration,
        "main",
        fake_step("gate"),
    )
    monkeypatch.setattr(
        pipeline.standard_peak_ms1_authority_bundle,
        "main",
        fake_step("authority"),
    )
    monkeypatch.setattr(
        pipeline.shadow_production_projection,
        "main",
        fake_step("projection"),
    )
    monkeypatch.setattr(
        pipeline.standard_peak_backfill_productization,
        "main",
        fake_step("productization"),
    )

    summary_path = pipeline.run_machine_pipeline(
        overlay_batch_summary_tsv=inputs["overlay"],
        alignment_review_tsv=inputs["review"],
        alignment_cells_tsv=inputs["cells"],
        alignment_matrix_tsv=inputs["matrix"],
        alignment_matrix_identity_tsv=inputs["identity"],
        retained_gate_tsv=inputs["gate"],
        reconciliation_groups_tsv=inputs["groups"],
        output_dir=tmp_path / "out",
        source_run_id="unit-run",
        write_gallery=True,
        reuse_existing=True,
        limit=5,
        render_workers=3,
        render_dpi=111,
        source_family_by_family_sample={"FAM001": {"SampleA_DNA": "FAM001"}},
    )

    assert summary_path.is_file()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["status"] == "pass"
    assert summary["min_shape_r"] == 0.95
    assert summary["render_workers"] == 3
    assert summary["render_dpi"] == 111
    assert summary["overlay_source_mode"] == "existing_overlay_summary"
    assert summary["overlay_selected_row_count"] == 1
    assert summary["shift_aware_successful_row_count"] == 1
    assert summary["matrix_cells_written"] == 1
    assert [name for name, _ in calls] == [
        "shift_batch",
        "pack",
        "gate",
        "authority",
        "projection",
        "productization",
    ]
    assert calls[0][1][-3:] == [
        "{'FAM001': {'SampleA_DNA': 'FAM001'}}",
        "3",
        "111",
    ]
    pack_args = dict(zip(calls[1][1][::2], calls[1][1][1::2], strict=False))
    assert pack_args["--min-shape-r"] == "0.95"
    product_args = calls[-1][1]
    assert "--write-gallery" in product_args
    assert "--shift-aware-standard-peak-gate-tsv" in product_args


def test_machine_pipeline_can_defer_projection_to_consolidation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    inputs = _write_inputs(tmp_path)
    calls: list[str] = []

    def fake_shift_batch(**kwargs):
        kwargs["output_dir"].mkdir(parents=True, exist_ok=True)
        calls.append("shift_batch")
        return (
            [
                {
                    "rank": "1",
                    "feature_family_id": "FAM001",
                    "seed_group_id": "seed::FAM001",
                    "overlay_status": "success",
                    "alignment_status": "rendered",
                    "output_prefix": "001_fam001_shift_aware",
                    "trace_data_json": str(inputs["trace"]),
                    "source_best_shift_summary_tsv": str(
                        kwargs["output_dir"]
                        / "001_fam001_shift_aware_source_family_best_shift_summary.tsv",
                    ),
                    "source_best_shift_png": "",
                    "failure_reason": "",
                }
            ],
            {
                "selected_row_count": 1,
                "status_counts": {"rendered": 1},
                "successful_shift_aware_row_count": 1,
            },
        )

    def fake_step(name: str):
        def _fake(argv):
            calls.append(name)
            _write_step_outputs(name, tmp_path / "out", list(argv))
            return 0

        return _fake

    monkeypatch.setattr(
        pipeline.family_ms1_alignment_experiment_batch,
        "run_alignment_experiment_batch",
        fake_shift_batch,
    )
    monkeypatch.setattr(
        pipeline.shift_aware_backfill_calibration_pack,
        "main",
        fake_step("pack"),
    )
    monkeypatch.setattr(
        pipeline.shift_aware_standard_peak_gate_calibration,
        "main",
        fake_step("gate"),
    )
    monkeypatch.setattr(
        pipeline.standard_peak_ms1_authority_bundle,
        "main",
        fake_step("authority"),
    )
    monkeypatch.setattr(
        pipeline.shadow_production_projection,
        "main",
        fake_step("projection"),
    )
    monkeypatch.setattr(
        pipeline.standard_peak_backfill_productization,
        "main",
        fake_step("productization"),
    )

    summary_path = pipeline.run_machine_pipeline(
        overlay_batch_summary_tsv=inputs["overlay"],
        alignment_review_tsv=inputs["review"],
        alignment_cells_tsv=inputs["cells"],
        alignment_matrix_tsv=inputs["matrix"],
        alignment_matrix_identity_tsv=inputs["identity"],
        retained_gate_tsv=inputs["gate"],
        reconciliation_groups_tsv=inputs["groups"],
        output_dir=tmp_path / "out",
        source_run_id="unit-run",
        defer_projection=True,
    )

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["status"] == "pass"
    assert summary["projection_mode"] == "deferred_to_consolidation"
    assert summary["shadow_projection_cells_tsv"] == ""
    assert Path(summary["productization_summary_json"]).exists()
    assert Path(summary["authorized_ms1_pattern_tsv"]).exists()
    assert calls == ["shift_batch", "pack", "gate", "authority"]


def test_machine_pipeline_can_render_overlays_and_build_reconciliation_groups(
    tmp_path: Path,
    monkeypatch,
) -> None:
    inputs = _write_inputs(tmp_path)
    calls: list[tuple[str, list[str]]] = []

    def fake_overlay_run(**kwargs):
        calls.append(
            (
                "overlay",
                [
                    f"limit={kwargs['limit']}",
                    f"reuse_existing={kwargs['reuse_existing']}",
                    f"write_pdf={kwargs['write_pdf']}",
                    f"workers={kwargs['workers']}",
                    f"dpi={kwargs['dpi']}",
                ],
            )
        )
        kwargs["metrics"].update(
            {
                "raw_open_count": 2,
                "extract_xic_count": 4,
                "raw_chromatogram_call_count": 2,
            }
        )
        return [
            _overlay_batch_row(1, "FAM001", trace_data_json=inputs["trace"]),
            _overlay_batch_row(2, "FAM002", trace_data_json=inputs["trace"]),
        ]

    def fake_gallery(**kwargs):
        calls.append(
            (
                "gallery",
                [
                    str(kwargs["overlay_batch_summary_tsvs"][0]),
                    str(kwargs["retained_backfill_gate_tsv"]),
                ],
            ),
        )
        output_dir = kwargs["output_dir"]
        output_dir.mkdir(parents=True, exist_ok=True)
        groups = output_dir / "backfill_evidence_reconciliation_groups.tsv"
        groups.write_text("placeholder\n", encoding="utf-8")
        return type("Outputs", (), {"groups_tsv": groups})()

    def fake_shift_batch(**kwargs):
        kwargs["output_dir"].mkdir(parents=True, exist_ok=True)
        calls.append(
            (
                "shift_batch",
                [
                    str(kwargs["overlay_batch_summary_tsv"]),
                    str(kwargs["reuse_existing"]),
                    str(kwargs["workers"]),
                    str(kwargs["dpi"]),
                ],
            ),
        )
        return (
            [
                {
                    "rank": "1",
                    "feature_family_id": "FAM001",
                    "seed_group_id": "seed::FAM001",
                    "overlay_status": "success",
                    "alignment_status": "rendered",
                    "output_prefix": "001_fam001_shift_aware",
                    "trace_data_json": "",
                    "source_best_shift_summary_tsv": "",
                    "source_best_shift_png": "",
                    "failure_reason": "",
                }
            ],
            {
                "selected_row_count": 1,
                "status_counts": {"rendered": 1},
                "successful_shift_aware_row_count": 1,
            },
        )

    def fake_step(name: str):
        def _fake(argv):
            calls.append((name, list(argv)))
            _write_step_outputs(name, tmp_path / "out", argv)
            return 0

        return _fake

    monkeypatch.setattr(
        pipeline.family_ms1_overlay_batch,
        "run_overlay_batch",
        fake_overlay_run,
    )
    monkeypatch.setattr(pipeline, "run_reconciliation_gallery", fake_gallery)
    monkeypatch.setattr(
        pipeline.family_ms1_alignment_experiment_batch,
        "run_alignment_experiment_batch",
        fake_shift_batch,
    )
    monkeypatch.setattr(
        pipeline.shift_aware_backfill_calibration_pack,
        "main",
        fake_step("pack"),
    )
    monkeypatch.setattr(
        pipeline.shift_aware_standard_peak_gate_calibration,
        "main",
        fake_step("gate"),
    )
    monkeypatch.setattr(
        pipeline.standard_peak_ms1_authority_bundle,
        "main",
        fake_step("authority"),
    )
    monkeypatch.setattr(
        pipeline.shadow_production_projection,
        "main",
        fake_step("projection"),
    )
    monkeypatch.setattr(
        pipeline.standard_peak_backfill_productization,
        "main",
        fake_step("productization"),
    )

    summary_path = pipeline.run_machine_pipeline(
        review_queue_tsv=inputs["queue"],
        raw_dir=tmp_path / "raw",
        dll_dir=tmp_path / "dll",
        alignment_review_tsv=inputs["review"],
        alignment_cells_tsv=inputs["cells"],
        alignment_matrix_tsv=inputs["matrix"],
        alignment_matrix_identity_tsv=inputs["identity"],
        retained_gate_tsv=inputs["gate"],
        output_dir=tmp_path / "out",
        source_run_id="unit-run",
        reuse_existing=True,
        write_overlay_pdf=False,
        render_workers=4,
        render_dpi=123,
    )

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["status"] == "pass"
    assert summary["overlay_source_mode"] == "rendered_from_review_queue"
    assert summary["overlay_queue_row_count"] == 2
    assert summary["requested_limit"] is None
    assert summary["effective_overlay_limit"] == 2
    assert Path(summary["overlay_batch_summary_tsv"]).parts[-2:] == (
        "family_ms1_overlay_batch",
        "family_ms1_overlay_batch_summary.tsv",
    )
    assert Path(summary["reconciliation_groups_tsv"]).parts[-2:] == (
        "reconciliation_group_index",
        "backfill_evidence_reconciliation_groups.tsv",
    )
    assert [name for name, _ in calls] == [
        "overlay",
        "gallery",
        "shift_batch",
        "pack",
        "gate",
        "authority",
        "projection",
        "productization",
    ]
    assert calls[0][1] == [
        "limit=2",
        "reuse_existing=True",
        "write_pdf=False",
        "workers=4",
        "dpi=123",
    ]
    assert calls[2][1][-2:] == ["4", "123"]
    overlay_metrics = json.loads(
        (
            tmp_path
            / "out"
            / "family_ms1_overlay_batch"
            / "family_ms1_overlay_batch_summary.json"
        ).read_text(encoding="utf-8")
    )["metrics"]
    assert overlay_metrics["raw_open_count"] == 2
    assert overlay_metrics["raw_chromatogram_call_count"] == 2


def test_machine_pipeline_can_generate_evidence_only_overlay_summary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    inputs = _write_inputs(tmp_path)
    calls: list[tuple[str, list[str]]] = []

    def fake_overlay_run(**kwargs):
        calls.append(
            (
                "overlay",
                [
                    f"evidence_only={kwargs['evidence_only']}",
                    f"write_pdf={kwargs['write_pdf']}",
                ],
            )
        )
        kwargs["metrics"].update(
            {
                "raw_open_count": 1,
                "extract_xic_count": 1,
                "raw_chromatogram_call_count": 1,
            }
        )
        return [_overlay_batch_row(1, "FAM001", trace_data_json=inputs["trace"])]

    def fake_gallery(**kwargs):
        calls.append(("gallery", [str(kwargs["overlay_batch_summary_tsvs"][0])]))
        output_dir = kwargs["output_dir"]
        output_dir.mkdir(parents=True, exist_ok=True)
        groups = output_dir / "backfill_evidence_reconciliation_groups.tsv"
        groups.write_text("placeholder\n", encoding="utf-8")
        return type("Outputs", (), {"groups_tsv": groups})()

    def fake_shift_batch(**kwargs):
        kwargs["output_dir"].mkdir(parents=True, exist_ok=True)
        calls.append(
            (
                "shift_batch",
                [
                    str(kwargs["overlay_batch_summary_tsv"]),
                    str(kwargs["render_images"]),
                ],
            ),
        )
        return (
            [
                {
                    "rank": "1",
                    "feature_family_id": "FAM001",
                    "seed_group_id": "seed::FAM001",
                    "overlay_status": "success",
                    "alignment_status": "rendered",
                    "output_prefix": "001_fam001_shift_aware",
                    "trace_data_json": str(inputs["trace"]),
                    "source_best_shift_summary_tsv": "",
                    "source_best_shift_png": "",
                    "failure_reason": "",
                }
            ],
            {
                "selected_row_count": 1,
                "status_counts": {"rendered": 1},
                "successful_shift_aware_row_count": 1,
            },
        )

    def fake_step(name: str):
        def _fake(argv):
            calls.append((name, list(argv)))
            _write_step_outputs(name, tmp_path / "out", argv)
            return 0

        return _fake

    monkeypatch.setattr(
        pipeline.family_ms1_overlay_batch,
        "run_overlay_batch",
        fake_overlay_run,
    )
    monkeypatch.setattr(pipeline, "run_reconciliation_gallery", fake_gallery)
    monkeypatch.setattr(
        pipeline.family_ms1_alignment_experiment_batch,
        "run_alignment_experiment_batch",
        fake_shift_batch,
    )
    monkeypatch.setattr(
        pipeline.shift_aware_backfill_calibration_pack,
        "main",
        fake_step("pack"),
    )
    monkeypatch.setattr(
        pipeline.shift_aware_standard_peak_gate_calibration,
        "main",
        fake_step("gate"),
    )
    monkeypatch.setattr(
        pipeline.standard_peak_ms1_authority_bundle,
        "main",
        fake_step("authority"),
    )
    monkeypatch.setattr(
        pipeline.shadow_production_projection,
        "main",
        fake_step("projection"),
    )
    monkeypatch.setattr(
        pipeline.standard_peak_backfill_productization,
        "main",
        fake_step("productization"),
    )

    summary_path = pipeline.run_machine_pipeline(
        review_queue_tsv=inputs["queue"],
        raw_dir=tmp_path / "raw",
        dll_dir=tmp_path / "dll",
        alignment_review_tsv=inputs["review"],
        alignment_cells_tsv=inputs["cells"],
        alignment_matrix_tsv=inputs["matrix"],
        alignment_matrix_identity_tsv=inputs["identity"],
        retained_gate_tsv=inputs["gate"],
        output_dir=tmp_path / "out",
        source_run_id="unit-run",
        publication_mode="matrix-only",
        evidence_only=True,
    )

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert calls[0][1] == ["evidence_only=True", "write_pdf=False"]
    assert summary["status"] == "pass"
    assert summary["publication_mode"] == "matrix-only"
    assert summary["evidence_source_mode"] == "evidence_only"
    assert summary["rendered_image_count"] == 0
    assert summary["shift_aware_render_images"] is False
    assert summary["overlay_source_mode"] == "evidence_from_review_queue"
    overlay_metrics = json.loads(
        (
            tmp_path
            / "out"
            / "family_ms1_overlay_batch"
            / "family_ms1_overlay_batch_summary.json"
        ).read_text(encoding="utf-8")
    )["metrics"]
    assert overlay_metrics["extract_xic_count"] == 1
    shift_calls = [call for call in calls if call[0] == "shift_batch"]
    assert shift_calls[0][1][-1] == "False"


def test_machine_pipeline_rejects_ambiguous_overlay_source(
    tmp_path: Path,
) -> None:
    inputs = _write_inputs(tmp_path)

    try:
        pipeline.run_machine_pipeline(
            overlay_batch_summary_tsv=inputs["overlay"],
            review_queue_tsv=inputs["queue"],
            raw_dir=tmp_path / "raw",
            dll_dir=tmp_path / "dll",
            alignment_review_tsv=inputs["review"],
            alignment_cells_tsv=inputs["cells"],
            alignment_matrix_tsv=inputs["matrix"],
            alignment_matrix_identity_tsv=inputs["identity"],
            retained_gate_tsv=inputs["gate"],
            output_dir=tmp_path / "out",
        )
    except ValueError as exc:
        assert "Choose one source mode" in str(exc)
    else:  # pragma: no cover - explicit failure branch.
        raise AssertionError("ambiguous overlay inputs should fail")


def test_write_overlay_batch_summary_slice_keeps_chunk_ranks(
    tmp_path: Path,
) -> None:
    source = tmp_path / "global_overlay.tsv"
    source.write_text(
        "rank\tfeature_family_id\tstatus\tfamily_verdict\n"
        "1\tFAM001\tsuccess\tms1_shape_supports_family_backfill\n"
        "2\tFAM002\tsuccess\tms1_shape_supports_family_backfill\n"
        "3\tFAM003\tsuccess\tms1_shape_supports_family_backfill\n",
        encoding="utf-8",
    )

    sliced = pipeline.write_overlay_batch_summary_slice(
        source_overlay_batch_summary_tsv=source,
        output_dir=tmp_path / "chunk_overlay",
        start_rank=2,
        limit=1,
    )

    lines = sliced.read_text(encoding="utf-8").splitlines()
    assert lines[0].split("\t")[:3] == ["rank", "feature_family_id", "seed_group_id"]
    assert len(lines) == 2
    assert lines[1].split("\t")[:2] == ["2", "FAM002"]


def test_machine_pipeline_marks_zero_shift_success_incomplete(
    tmp_path: Path,
    monkeypatch,
) -> None:
    inputs = _write_inputs(tmp_path)

    def fake_shift_batch(**kwargs):
        kwargs["output_dir"].mkdir(parents=True, exist_ok=True)
        return ([], {"selected_row_count": 0, "successful_shift_aware_row_count": 0})

    def fake_step(name: str):
        def _fake(argv):
            _write_step_outputs(name, tmp_path / "out", argv)
            return 0

        return _fake

    monkeypatch.setattr(
        pipeline.family_ms1_alignment_experiment_batch,
        "run_alignment_experiment_batch",
        fake_shift_batch,
    )
    monkeypatch.setattr(
        pipeline.shift_aware_backfill_calibration_pack,
        "main",
        fake_step("pack"),
    )
    monkeypatch.setattr(
        pipeline.shift_aware_standard_peak_gate_calibration,
        "main",
        fake_step("gate"),
    )
    monkeypatch.setattr(
        pipeline.standard_peak_ms1_authority_bundle,
        "main",
        fake_step("authority"),
    )
    monkeypatch.setattr(
        pipeline.shadow_production_projection,
        "main",
        fake_step("projection"),
    )
    monkeypatch.setattr(
        pipeline.standard_peak_backfill_productization,
        "main",
        fake_step("productization"),
    )

    summary_path = pipeline.run_machine_pipeline(
        overlay_batch_summary_tsv=inputs["overlay"],
        alignment_review_tsv=inputs["review"],
        alignment_cells_tsv=inputs["cells"],
        alignment_matrix_tsv=inputs["matrix"],
        alignment_matrix_identity_tsv=inputs["identity"],
        retained_gate_tsv=inputs["gate"],
        reconciliation_groups_tsv=inputs["groups"],
        output_dir=tmp_path / "out",
    )

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["status"] == "incomplete"
    assert "shift_aware_no_success_rows" in summary["status_reasons"]


def _write_inputs(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "overlay": tmp_path / "overlay.tsv",
        "trace": tmp_path / "trace.json",
        "queue": tmp_path / "review_queue.tsv",
        "review": tmp_path / "review.tsv",
        "cells": tmp_path / "cells.tsv",
        "matrix": tmp_path / "matrix.tsv",
        "identity": tmp_path / "identity.tsv",
        "gate": tmp_path / "retained_gate.tsv",
        "groups": tmp_path / "groups.tsv",
    }
    for path in paths.values():
        path.write_text("placeholder\n", encoding="utf-8")
    paths["overlay"].write_text(
        "\t".join(
            [
                "rank",
                "feature_family_id",
                "seed_group_id",
                "output_prefix",
                "status",
                "trace_data_json",
            ],
        )
        + "\n"
        + f"1\tFAM001\tseed::FAM001\t001_fam001\tsuccess\t{paths['trace']}\n",
        encoding="utf-8",
    )
    paths["queue"].write_text(
        "feature_family_id\nFAM001\nFAM002\n",
        encoding="utf-8",
    )
    paths["review"].write_text(
        "\t".join(["feature_family_id", "neutral_loss_tag"]) + "\n"
        "FAM001\tNL-A\n"
        "FAM002\tNL-B\n",
        encoding="utf-8",
    )
    paths["cells"].write_text(
        "\t".join(["feature_family_id", "sample_stem", "reason"]) + "\n"
        "FAM001\tSampleA_DNA\tsource_family=FAM001\n"
        "FAM002\tSampleB_DNA\tsource_family=FAM002\n",
        encoding="utf-8",
    )
    paths["gate"].write_text(
        "\t".join(["feature_family_id", "seed_group_id", "seed_source_samples"])
        + "\n"
        "FAM001\tseed::FAM001\tSampleA_DNA\n"
        "FAM002\tseed::FAM002\tSampleB_DNA\n",
        encoding="utf-8",
    )
    return paths


def _overlay_batch_row(
    rank: int,
    family_id: str,
    *,
    trace_data_json: Path,
) -> dict[str, object]:
    prefix = f"{rank:03d}_{family_id.lower()}"
    return {
        "rank": rank,
        "feature_family_id": family_id,
        "seed_group_id": f"seed::{family_id}",
        "mz": 251.165,
        "ppm": 20.0,
        "rt_min": 1.0,
        "rt_max": 1.5,
        "family_center_rt": 1.25,
        "output_prefix": prefix,
        "status": "success",
        "family_verdict": "ms1_shape_supports_family_backfill",
        "dda_trigger_limited_ms2_support": "",
        "detected_count": 1,
        "rescued_count": 1,
        "detected_rescued_count": 2,
        "evaluable_trace_count": 2,
        "global_apex_assessable_trace_count": 2,
        "global_apex_assessable_fraction": 1.0,
        "selected_apex_in_trace_window_count": 2,
        "selected_apex_in_trace_window_fraction": 1.0,
        "local_apex_assessable_trace_count": 2,
        "global_apex_interference_count": 0,
        "shape_supported_fraction": 1.0,
        "absolute_own_max_evaluable_trace_count": 2,
        "absolute_own_max_shape_supported_count": 2,
        "absolute_own_max_shape_supported_fraction": 1.0,
        "absolute_trace_apex_assessable_count": 2,
        "absolute_trace_apex_cluster_count": 2,
        "absolute_trace_apex_cluster_fraction": 1.0,
        "absolute_trace_apex_delta_abs_median_min": 0.0,
        "global_apex_interference_fraction": 0.0,
        "local_apex_supported_count": 2,
        "local_apex_supported_fraction": 1.0,
        "png_path": "",
        "pdf_path": "",
        "trace_summary_tsv": "",
        "trace_data_json": str(trace_data_json),
        "failure_reason": "",
    }


def _write_step_outputs(name: str, root: Path, argv: list[str]) -> None:
    args = dict(zip(argv[::2], argv[1::2], strict=False))
    if name == "pack":
        output_dir = Path(args["--output-dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "shift_aware_backfill_calibration_pack.tsv").write_text(
            "placeholder\n",
            encoding="utf-8",
        )
    elif name == "gate":
        output_dir = Path(args["--output-dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "shift_aware_standard_peak_gate_calibration.tsv").write_text(
            "placeholder\n",
            encoding="utf-8",
        )
    elif name == "authority":
        output_dir = Path(args["--output-dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        (
            output_dir
            / "shared_peak_identity_ms1_pattern_coherence_product_authorized.tsv"
        ).write_text("placeholder\n", encoding="utf-8")
    elif name == "projection":
        output_dir = Path(args["--output-dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "shadow_production_projection_cells.tsv").write_text(
            "placeholder\n",
            encoding="utf-8",
        )
    elif name == "productization":
        output_dir = Path(args["--output-dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "standard_peak_backfill_productization_summary.json").write_text(
            json.dumps(
                {
                    "status": "pass",
                    "activation_acceptance_status": "pass",
                    "activation_application_status": "applied",
                    "selected_activation_row_count": 1,
                    "matrix_cells_written": 1,
                    "activation_value_delta_written_count": 1,
                    "product_behavior_changed": "TRUE",
                },
            ),
            encoding="utf-8",
        )


def _arg_dict(argv: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    index = 0
    while index < len(argv):
        flag = argv[index]
        if not flag.startswith("--"):
            index += 1
            continue
        next_index = index + 1
        if next_index >= len(argv) or argv[next_index].startswith("--"):
            values[flag] = ""
            index += 1
            continue
        values[flag] = argv[next_index]
        index += 2
    return values
