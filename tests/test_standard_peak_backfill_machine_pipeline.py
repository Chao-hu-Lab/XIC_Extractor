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
    )

    assert summary_path.is_file()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["status"] == "pass"
    assert summary["min_shape_r"] == 0.95
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
    pack_args = dict(zip(calls[1][1][::2], calls[1][1][1::2], strict=False))
    assert pack_args["--min-shape-r"] == "0.95"
    product_args = calls[-1][1]
    assert "--write-gallery" in product_args
    assert "--shift-aware-standard-peak-gate-tsv" in product_args


def test_machine_pipeline_can_render_overlays_and_build_reconciliation_groups(
    tmp_path: Path,
    monkeypatch,
) -> None:
    inputs = _write_inputs(tmp_path)
    calls: list[tuple[str, list[str]]] = []

    def fake_overlay(argv):
        args = _arg_dict(argv)
        calls.append(("overlay", list(argv)))
        output_dir = Path(args["--output-dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "family_ms1_overlay_batch_summary.tsv").write_text(
            "\t".join(
                [
                    "rank",
                    "feature_family_id",
                    "seed_group_id",
                    "output_prefix",
                    "status",
                ],
            )
            + "\n"
            + "1\tFAM001\tseed::FAM001\t001_fam001\tsuccess\n"
            + "2\tFAM002\tseed::FAM002\t002_fam002\tsuccess\n",
            encoding="utf-8",
        )
        return 0

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

    monkeypatch.setattr(pipeline.family_ms1_overlay_batch, "main", fake_overlay)
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
    overlay_args = calls[0][1]
    assert "--no-pdf" in overlay_args
    assert "--reuse-existing" in overlay_args
    assert _arg_dict(overlay_args)["--limit"] == "2"


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
    return paths


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
