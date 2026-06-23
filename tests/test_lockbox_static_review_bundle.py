import csv
import json
from pathlib import Path

from scripts.build_lockbox_label_collection_pack import PACKET_INDEX_HEADER
from scripts.build_lockbox_static_review_bundle import (
    OUTPUT_DIR,
    build_lockbox_static_review_bundle,
    check_lockbox_static_review_bundle,
)


def test_current_static_review_bundle_validates() -> None:
    problems = check_lockbox_static_review_bundle()

    assert problems == []


def test_current_static_review_bundle_counts_and_authority() -> None:
    rows = _read_tsv(OUTPUT_DIR / "bundle_index.tsv")
    plotted = [row for row in rows if row["plot_status"] == "plotted_gaussian15"]
    missing = [
        row for row in rows if row["plot_status"] == "missing_evidence_recorded"
    ]
    boundary_unavailable = [
        row
        for row in rows
        if row["plot_status"] == "gaussian_review_boundary_unavailable"
    ]

    assert len(rows) == 72
    assert len(plotted) == 53
    assert len(missing) == 18
    assert len(boundary_unavailable) == 1
    assert {row["gaussian_smoothing_method"] for row in rows} == {"gaussian_15"}
    assert {row["gaussian_window_points"] for row in rows} == {"15"}
    assert {row["may_touch_matrix"] for row in rows} == {"FALSE"}
    assert {row["may_grant_product_authority"] for row in rows} == {"FALSE"}
    assert {
        row["gaussian_review_area_source"] for row in plotted
    } == {"gaussian15_positive_asls_residual"}
    assert all(row["gaussian_review_boundary_start_rt"] for row in plotted)
    assert all(row["gaussian_review_boundary_end_rt"] for row in plotted)
    assert all(not row["gaussian_review_boundary_start_rt"] for row in missing)
    assert all(
        not row["gaussian_review_boundary_start_rt"]
        for row in boundary_unavailable
    )
    first_plot = Path(plotted[0]["review_plot_png_path"])
    assert first_plot.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    html = (OUTPUT_DIR / "index.html").read_text(encoding="utf-8")
    assert "Gaussian15" in html
    assert "ProductWriter authority" in html


def test_static_review_builder_generates_synthetic_gaussian_bundle(
    tmp_path: Path,
) -> None:
    packet_index, label_template = _write_synthetic_inputs(tmp_path)

    result = build_lockbox_static_review_bundle(
        packet_index_path=packet_index,
        label_template_path=label_template,
        output_dir=tmp_path / "bundle",
    )
    rows = _read_tsv(Path(result["bundle_index"]))

    assert result["case_count"] == 2
    assert result["plot_count"] == 1
    assert rows[0]["plot_status"] == "plotted_gaussian15"
    assert rows[0]["review_plot_png_path"]
    assert rows[0]["gaussian_review_boundary_start_rt"]
    assert rows[0]["gaussian_review_boundary_end_rt"]
    assert rows[0]["gaussian_review_area_source"] == (
        "gaussian15_positive_asls_residual"
    )
    assert Path(rows[0]["review_plot_png_path"]).read_bytes().startswith(
        b"\x89PNG\r\n\x1a\n",
    )
    assert rows[1]["plot_status"] == "missing_evidence_recorded"
    assert rows[1]["review_plot_png_path"] == ""
    assert rows[1]["gaussian_review_boundary_start_rt"] == ""
    case_html = Path(rows[0]["case_html_path"]).read_text(encoding="utf-8")
    assert "Gaussian15 Review Plot" in case_html
    assert "Gaussian review boundary" in case_html
    assert "packet_trace_overlay_hypothesis" in case_html


def test_static_review_builder_marks_zero_signal_trace_boundary_unavailable(
    tmp_path: Path,
) -> None:
    packet_index, label_template = _write_synthetic_inputs(tmp_path)
    trace_path = tmp_path / "trace.json"
    payload = json.loads(trace_path.read_text(encoding="utf-8"))
    payload["traces"][0]["intensity"] = [0 for _ in payload["traces"][0]["rt"]]
    trace_path.write_text(json.dumps(payload), encoding="utf-8")

    result = build_lockbox_static_review_bundle(
        packet_index_path=packet_index,
        label_template_path=label_template,
        output_dir=tmp_path / "bundle",
    )
    rows = _read_tsv(Path(result["bundle_index"]))

    assert result["plot_count"] == 0
    assert rows[0]["plot_status"] == "gaussian_review_boundary_unavailable"
    assert rows[0]["review_plot_png_path"] == ""
    assert rows[0]["gaussian_review_boundary_start_rt"] == ""
    assert "not assessable" in Path(rows[0]["case_html_path"]).read_text(
        encoding="utf-8",
    )


def test_current_browser_case_uses_gaussian_boundary_not_raw_candidate_window() -> None:
    rows = _read_tsv(OUTPUT_DIR / "bundle_index.tsv")
    row = next(
        item
        for item in rows
        if item["lockbox_case_id"] == "LOCKBOXV1_030FE0B6917F8D9F8B9D8ADC"
    )

    assert float(row["gaussian_review_boundary_start_rt"]) < 32.7987
    assert float(row["gaussian_review_boundary_end_rt"]) > 33.0894
    assert row["gaussian_review_boundary_source"] == "baseline_return"
    assert row["gaussian_review_segment_class"] == "isolated_peak"


def test_static_review_checker_rejects_missing_plot(tmp_path: Path) -> None:
    packet_index, label_template = _write_synthetic_inputs(tmp_path)
    build_lockbox_static_review_bundle(
        packet_index_path=packet_index,
        label_template_path=label_template,
        output_dir=tmp_path / "bundle",
    )
    header, rows = _read_tsv_with_header(tmp_path / "bundle" / "bundle_index.tsv")
    rows[0]["review_plot_png_path"] = str(tmp_path / "bundle" / "missing.png")
    _write_tsv(tmp_path / "bundle" / "bundle_index.tsv", header, rows)

    problems = check_lockbox_static_review_bundle(
        packet_index_path=packet_index,
        label_template_path=label_template,
        output_dir=tmp_path / "bundle",
        expected_case_count=2,
    )

    assert any("plot PNG missing" in problem for problem in problems)


def test_static_review_checker_rejects_authority_flags(tmp_path: Path) -> None:
    packet_index, label_template = _write_synthetic_inputs(tmp_path)
    build_lockbox_static_review_bundle(
        packet_index_path=packet_index,
        label_template_path=label_template,
        output_dir=tmp_path / "bundle",
    )
    header, rows = _read_tsv_with_header(tmp_path / "bundle" / "bundle_index.tsv")
    rows[0]["may_touch_matrix"] = "TRUE"
    rows[0]["may_grant_product_authority"] = "TRUE"
    _write_tsv(tmp_path / "bundle" / "bundle_index.tsv", header, rows)

    problems = check_lockbox_static_review_bundle(
        packet_index_path=packet_index,
        label_template_path=label_template,
        output_dir=tmp_path / "bundle",
        expected_case_count=2,
    )

    assert any("may_touch_matrix must be FALSE" in problem for problem in problems)
    assert any(
        "may_grant_product_authority must be FALSE" in problem
        for problem in problems
    )


def test_static_review_checker_rejects_missing_gaussian_boundary(
    tmp_path: Path,
) -> None:
    packet_index, label_template = _write_synthetic_inputs(tmp_path)
    build_lockbox_static_review_bundle(
        packet_index_path=packet_index,
        label_template_path=label_template,
        output_dir=tmp_path / "bundle",
    )
    header, rows = _read_tsv_with_header(tmp_path / "bundle" / "bundle_index.tsv")
    rows[0]["gaussian_review_boundary_start_rt"] = ""
    _write_tsv(tmp_path / "bundle" / "bundle_index.tsv", header, rows)

    problems = check_lockbox_static_review_bundle(
        packet_index_path=packet_index,
        label_template_path=label_template,
        output_dir=tmp_path / "bundle",
        expected_case_count=2,
    )

    assert any(
        "gaussian_review_boundary_start_rt missing" in problem
        for problem in problems
    )


def test_static_review_checker_rejects_stale_packet_index(
    tmp_path: Path,
) -> None:
    packet_index, label_template = _write_synthetic_inputs(tmp_path)
    build_lockbox_static_review_bundle(
        packet_index_path=packet_index,
        label_template_path=label_template,
        output_dir=tmp_path / "bundle",
    )
    packet_index.write_text(
        packet_index.read_text(encoding="utf-8").replace(
            "FAM_SYNTH",
            "FAM_CHANGED",
        ),
        encoding="utf-8",
    )

    problems = check_lockbox_static_review_bundle(
        packet_index_path=packet_index,
        label_template_path=label_template,
        output_dir=tmp_path / "bundle",
        expected_case_count=2,
    )

    assert any(
        "source_packet_index_sha256 mismatch" in problem for problem in problems
    )
    assert any("family_id mismatch" in problem for problem in problems)


def test_static_review_checker_rejects_stale_label_template(
    tmp_path: Path,
) -> None:
    packet_index, label_template = _write_synthetic_inputs(tmp_path)
    build_lockbox_static_review_bundle(
        packet_index_path=packet_index,
        label_template_path=label_template,
        output_dir=tmp_path / "bundle",
    )
    label_template.write_text(
        "schema_version\tlockbox_case_id\treviewer_id\n",
        encoding="utf-8",
    )

    problems = check_lockbox_static_review_bundle(
        packet_index_path=packet_index,
        label_template_path=label_template,
        output_dir=tmp_path / "bundle",
        expected_case_count=2,
    )

    assert any("label_template_sha256 mismatch" in problem for problem in problems)


def test_static_review_checker_rejects_stale_source_hashes(
    tmp_path: Path,
) -> None:
    packet_index, label_template = _write_synthetic_inputs(tmp_path)
    build_lockbox_static_review_bundle(
        packet_index_path=packet_index,
        label_template_path=label_template,
        output_dir=tmp_path / "bundle",
    )
    header, rows = _read_tsv_with_header(tmp_path / "bundle" / "bundle_index.tsv")
    rows[0]["source_artifact_hashes"] = "synthetic=stale"
    _write_tsv(tmp_path / "bundle" / "bundle_index.tsv", header, rows)

    problems = check_lockbox_static_review_bundle(
        packet_index_path=packet_index,
        label_template_path=label_template,
        output_dir=tmp_path / "bundle",
        expected_case_count=2,
    )

    assert any("source_artifact_hashes mismatch" in problem for problem in problems)


def _write_synthetic_inputs(tmp_path: Path) -> tuple[Path, Path]:
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(
        json.dumps(
            {
                "traces": [
                    {
                        "sample_stem": "SampleA",
                        "trace_apex_rt": 1.0,
                        "rt": [index / 10 for index in range(21)],
                        "intensity": [
                            0,
                            0,
                            0,
                            2,
                            5,
                            11,
                            20,
                            44,
                            76,
                            94,
                            100,
                            94,
                            76,
                            44,
                            20,
                            11,
                            5,
                            2,
                            0,
                            0,
                            0,
                        ],
                    }
                ]
            },
        ),
        encoding="utf-8",
    )
    packet_index = tmp_path / "packet_index.tsv"
    packet_rows = [
        _packet_row(
            "LOCKBOXV1_SYNTH_A",
            "SampleA",
            evidence_status="complete_visual_evidence",
            trace_path=str(trace_path),
        ),
        _packet_row(
            "LOCKBOXV1_SYNTH_B",
            "SampleB",
            evidence_status="missing_evidence_recorded",
            missing_reason="trace_overlay_hypothesis_not_available",
        ),
    ]
    _write_tsv(packet_index, PACKET_INDEX_HEADER, packet_rows)
    label_template = tmp_path / "lockbox_label_template_v1.tsv"
    label_template.write_text("schema_version\tlockbox_case_id\n", encoding="utf-8")
    return packet_index, label_template


def _packet_row(
    case_id: str,
    sample_id: str,
    *,
    evidence_status: str,
    trace_path: str = "",
    missing_reason: str = "",
) -> dict[str, str]:
    row = {field: "" for field in PACKET_INDEX_HEADER}
    row.update(
        {
            "schema_version": "lockbox_review_packet_v1",
            "lockbox_case_id": case_id,
            "packet_path": f"{case_id}.md",
            "row_id": f"row-{case_id}",
            "family_id": "FAM_SYNTH",
            "sample_id": sample_id,
            "analyte": "synthetic",
            "source_stratum": "synthetic_review_case",
            "current_machine_decision": "evidence_required",
            "evidence_status": evidence_status,
            "missing_evidence_reason": missing_reason,
            "candidate_peak_summary": (
                "area=100; height=10; apex_rt_min=1.0; "
                "start_rt_min=0.8; end_rt_min=1.2"
            ),
            "trace_data_path": trace_path,
            "source_artifact_hashes": "synthetic=hash",
            "reviewer_question": "Label the synthetic case.",
            "may_touch_matrix": "FALSE",
            "may_grant_product_authority": "FALSE",
        },
    )
    return row


def _read_tsv(path: Path) -> list[dict[str, str]]:
    return _read_tsv_with_header(path)[1]


def _read_tsv_with_header(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return list(reader.fieldnames or []), list(reader)


def _write_tsv(path: Path, header: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)
