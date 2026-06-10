from __future__ import annotations

import json
from pathlib import Path

from tools.diagnostics import family_ms1_alignment_experiment_batch as batch


def test_batch_renders_shift_aware_outputs_from_overlay_summary(
    tmp_path: Path,
) -> None:
    trace_json = tmp_path / "fam001_trace_data.json"
    trace_json.write_text(
        json.dumps(
            {
                "family_id": "FAM001",
                "mz": 123.45,
                "ppm": 20.0,
                "rt_min": 7.0,
                "rt_max": 9.0,
                "family_center_rt": 8.0,
                "provenance": {"output_prefix": "001_fam001_overlay"},
                "evidence_summary": {
                    "absolute_trace_apex_cluster_fraction": 0.75,
                    "absolute_own_max_shape_supported_fraction": 0.8,
                    "shape_supported_fraction": 0.3,
                },
                "traces": [
                    _trace_json(
                        "detected-a",
                        status="detected",
                        group="detected_seed",
                    ),
                    _trace_json("rescued-a", status="rescued"),
                ],
            },
        ),
        encoding="utf-8",
    )
    cell_evidence = tmp_path / "cells.tsv"
    cell_evidence.write_text(
        "\t".join(("feature_family_id", "sample_stem", "reason"))
        + "\n"
        + "\t".join(
            (
                "FAM001",
                "detected-a",
                "primary family consolidation; source_family=FAM000001",
            ),
        )
        + "\n"
        + "\t".join(
            (
                "FAM001",
                "rescued-a",
                "primary family consolidation; source_family=FAM000002",
            ),
        )
        + "\n",
        encoding="utf-8",
    )
    overlay_summary = tmp_path / "family_ms1_overlay_batch_summary.tsv"
    overlay_summary.write_text(
        "\t".join(
            (
                "rank",
                "feature_family_id",
                "seed_group_id",
                "output_prefix",
                "status",
                "trace_data_json",
            ),
        )
        + "\n"
        + "\t".join(
            (
                "1",
                "FAM001",
                "seed::FAM001",
                "001_fam001_retained_backfill_missing_overlay",
                "success",
                str(trace_json),
            ),
        )
        + "\n"
        + "\t".join(
            (
                "2",
                "FAM002",
                "seed::FAM002",
                "002_fam002_retained_backfill_missing_overlay",
                "failure",
                "",
            ),
        )
        + "\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "shift"

    code = batch.main(
        [
            "--overlay-batch-summary-tsv",
            str(overlay_summary),
            "--cell-evidence-tsv",
            str(cell_evidence),
            "--output-dir",
            str(out_dir),
        ],
    )

    assert code == 0
    rows = _read_tsv(out_dir / "family_ms1_alignment_experiment_batch_summary.tsv")
    assert rows[0]["alignment_status"] == "rendered"
    assert rows[0]["output_prefix"] == "001_fam001_shift_aware"
    assert Path(rows[0]["source_best_shift_summary_tsv"]).is_file()
    assert rows[1]["alignment_status"] == "skipped"
    assert rows[1]["failure_reason"] == "overlay_status_not_success:failure"


def test_batch_no_images_writes_best_shift_summary_without_png(
    tmp_path: Path,
) -> None:
    trace_json = tmp_path / "fam001_trace_data.json"
    trace_json.write_text(
        json.dumps(
            {
                "family_id": "FAM001",
                "mz": 123.45,
                "ppm": 20.0,
                "rt_min": 7.0,
                "rt_max": 9.0,
                "family_center_rt": 8.0,
                "provenance": {"output_prefix": "001_fam001_overlay"},
                "evidence_summary": {
                    "absolute_trace_apex_cluster_fraction": 0.75,
                    "absolute_own_max_shape_supported_fraction": 0.8,
                    "shape_supported_fraction": 0.3,
                },
                "traces": [
                    _trace_json(
                        "detected-a",
                        status="detected",
                        group="detected_seed",
                    ),
                    _trace_json("rescued-a", status="rescued"),
                ],
            },
        ),
        encoding="utf-8",
    )
    cell_evidence = tmp_path / "cells.tsv"
    cell_evidence.write_text(
        "\t".join(("feature_family_id", "sample_stem", "reason"))
        + "\n"
        + "\t".join(
            (
                "FAM001",
                "detected-a",
                "primary family consolidation; source_family=FAM000001",
            ),
        )
        + "\n"
        + "\t".join(
            (
                "FAM001",
                "rescued-a",
                "primary family consolidation; source_family=FAM000002",
            ),
        )
        + "\n",
        encoding="utf-8",
    )
    overlay_summary = tmp_path / "family_ms1_overlay_batch_summary.tsv"
    overlay_summary.write_text(
        "\t".join(
            (
                "rank",
                "feature_family_id",
                "seed_group_id",
                "output_prefix",
                "status",
                "trace_data_json",
            ),
        )
        + "\n"
        + "\t".join(
            (
                "1",
                "FAM001",
                "seed::FAM001",
                "001_fam001_retained_backfill_missing_overlay",
                "success",
                str(trace_json),
            ),
        )
        + "\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "shift"

    code = batch.main(
        [
            "--overlay-batch-summary-tsv",
            str(overlay_summary),
            "--cell-evidence-tsv",
            str(cell_evidence),
            "--output-dir",
            str(out_dir),
            "--no-images",
        ],
    )

    assert code == 0
    rows = _read_tsv(out_dir / "family_ms1_alignment_experiment_batch_summary.tsv")
    assert rows[0]["alignment_status"] == "rendered"
    assert rows[0]["source_best_shift_png"] == ""
    assert Path(rows[0]["source_best_shift_summary_tsv"]).is_file()
    assert not list(out_dir.glob("*.png"))


def test_batch_preloads_cell_evidence_once_for_selected_families(
    tmp_path: Path,
    monkeypatch,
) -> None:
    trace_json_1 = _write_trace_json(tmp_path, family_id="FAM001")
    trace_json_2 = _write_trace_json(tmp_path, family_id="FAM002")
    cell_evidence = tmp_path / "cells.tsv"
    cell_evidence.write_text(
        "\t".join(("feature_family_id", "sample_stem", "reason"))
        + "\n"
        + "\t".join(
            (
                "FAM001",
                "FAM001-detected",
                "primary family consolidation; source_family=FAM000001",
            ),
        )
        + "\n"
        + "\t".join(
            (
                "FAM001",
                "FAM001-rescued",
                "primary family consolidation; source_family=FAM000002",
            ),
        )
        + "\n"
        + "\t".join(
            (
                "FAM002",
                "FAM002-detected",
                "primary family consolidation; source_family=FAM000003",
            ),
        )
        + "\n"
        + "\t".join(
            (
                "FAM002",
                "FAM002-rescued",
                "primary family consolidation; source_family=FAM000004",
            ),
        )
        + "\n",
        encoding="utf-8",
    )
    overlay_summary = tmp_path / "family_ms1_overlay_batch_summary.tsv"
    overlay_summary.write_text(
        "\t".join(
            (
                "rank",
                "feature_family_id",
                "seed_group_id",
                "output_prefix",
                "status",
                "trace_data_json",
            ),
        )
        + "\n"
        + "\t".join(
            (
                "1",
                "FAM001",
                "seed::FAM001",
                "001_fam001_retained_backfill_missing_overlay",
                "success",
                str(trace_json_1),
            ),
        )
        + "\n"
        + "\t".join(
            (
                "2",
                "FAM002",
                "seed::FAM002",
                "002_fam002_retained_backfill_missing_overlay",
                "success",
                str(trace_json_2),
            ),
        )
        + "\n",
        encoding="utf-8",
    )
    original_loader = (
        batch.family_ms1_alignment_experiment.load_source_family_by_family_sample
    )
    load_calls: list[tuple[str, ...]] = []

    def tracking_loader(
        path: Path,
        *,
        family_ids=None,
    ) -> dict[str, dict[str, str]]:
        load_calls.append(tuple(family_ids or ()))
        return original_loader(path, family_ids=family_ids)

    def fail_single_family_loader(*_args, **_kwargs) -> dict[str, str]:
        raise AssertionError("batch should not load source families per row")

    monkeypatch.setattr(
        batch.family_ms1_alignment_experiment,
        "load_source_family_by_family_sample",
        tracking_loader,
    )
    monkeypatch.setattr(
        batch.family_ms1_alignment_experiment,
        "load_source_family_by_sample",
        fail_single_family_loader,
    )
    out_dir = tmp_path / "shift"

    rows, summary = batch.run_alignment_experiment_batch(
        overlay_batch_summary_tsv=overlay_summary,
        cell_evidence_tsv=cell_evidence,
        output_dir=out_dir,
        render_images=False,
    )

    assert load_calls == [("FAM001", "FAM002")]
    assert [row["alignment_status"] for row in rows] == ["rendered", "rendered"]
    assert summary["successful_shift_aware_row_count"] == 2


def test_batch_reuses_existing_best_shift_summary(tmp_path: Path) -> None:
    overlay_summary = tmp_path / "family_ms1_overlay_batch_summary.tsv"
    trace_json = tmp_path / "fam001_trace_data.json"
    trace_json.write_text("{}", encoding="utf-8")
    overlay_summary.write_text(
        "\t".join(
            (
                "rank",
                "feature_family_id",
                "seed_group_id",
                "output_prefix",
                "status",
                "trace_data_json",
            ),
        )
        + "\n"
        + "\t".join(
            (
                "1",
                "FAM001",
                "seed::FAM001",
                "001_fam001_retained_backfill_missing_overlay",
                "success",
                str(trace_json),
            ),
        )
        + "\n",
        encoding="utf-8",
    )
    cell_evidence = tmp_path / "cells.tsv"
    cell_evidence.write_text(
        "feature_family_id\tsample_stem\treason\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "shift"
    out_dir.mkdir()
    existing = out_dir / "001_fam001_shift_aware_source_family_best_shift_summary.tsv"
    existing.write_text(
        "feature_family_id\tsource_family\nFAM001\tFAM000001\n",
        encoding="utf-8",
    )
    existing_png = (
        out_dir / "001_fam001_shift_aware_source_family_best_shift_alignment.png"
    )
    existing_png.write_bytes(b"png")

    code = batch.main(
        [
            "--overlay-batch-summary-tsv",
            str(overlay_summary),
            "--cell-evidence-tsv",
            str(cell_evidence),
            "--output-dir",
            str(out_dir),
            "--reuse-existing",
        ],
    )

    assert code == 0
    rows = _read_tsv(out_dir / "family_ms1_alignment_experiment_batch_summary.tsv")
    assert rows[0]["alignment_status"] == "reused"
    assert rows[0]["source_best_shift_summary_tsv"] == str(existing)


def _trace_json(
    sample: str,
    *,
    status: str,
    group: str = "top_rescued_ms1_area",
) -> dict[str, object]:
    return {
        "sample_stem": sample,
        "status": status,
        "group": group,
        "cell_area": 1000.0,
        "cell_height": 100.0,
        "cell_apex_rt": 8.0,
        "cell_start_rt": 7.9,
        "cell_end_rt": 8.1,
        "trace_max_intensity": 100.0,
        "trace_apex_rt": 8.0,
        "region_shadow_verdict": "",
        "source_candidate_id": "",
        "rt": [7.9, 8.0, 8.1],
        "intensity": [0.0, 100.0, 0.0],
    }


def _write_trace_json(tmp_path: Path, *, family_id: str) -> Path:
    path = tmp_path / f"{family_id.lower()}_trace_data.json"
    path.write_text(
        json.dumps(
            {
                "family_id": family_id,
                "mz": 123.45,
                "ppm": 20.0,
                "rt_min": 7.0,
                "rt_max": 9.0,
                "family_center_rt": 8.0,
                "provenance": {"output_prefix": f"{family_id.lower()}_overlay"},
                "evidence_summary": {
                    "absolute_trace_apex_cluster_fraction": 0.75,
                    "absolute_own_max_shape_supported_fraction": 0.8,
                    "shape_supported_fraction": 0.3,
                },
                "traces": [
                    _trace_json(
                        f"{family_id}-detected",
                        status="detected",
                        group="detected_seed",
                    ),
                    _trace_json(f"{family_id}-rescued", status="rescued"),
                ],
            },
        ),
        encoding="utf-8",
    )
    return path


def _read_tsv(path: Path) -> list[dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    header = lines[0].split("\t")
    return [dict(zip(header, line.split("\t"), strict=False)) for line in lines[1:]]
