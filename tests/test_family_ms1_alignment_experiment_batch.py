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


def _read_tsv(path: Path) -> list[dict[str, str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    header = lines[0].split("\t")
    return [dict(zip(header, line.split("\t"), strict=False)) for line in lines[1:]]
