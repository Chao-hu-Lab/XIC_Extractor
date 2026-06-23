from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.diagnostics import cid_nl_default_activation_gallery_review as review
from xic_extractor.tabular_io import write_tsv


def test_builds_gallery_review_packet_and_overlay_queue(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path)

    payload = review.build_gallery_review_packet(
        successor_packet_dir=paths["successor_dir"],
        target_preflight_summary_json=paths["target_summary"],
        output_dir=tmp_path / "review",
        source_root=tmp_path,
    )

    assert payload["packet_build_status"] == "pass"
    assert payload["overall_status"] == "needs_overlay_batch"
    assert payload["successor_decision_counts"] == {
        "no_write_detected_baseline_preserved": 1,
        "no_write_omitted": 1,
        "write_authorized": 1,
    }
    assert payload["product_writer_changed"] is False
    assert payload["default_quant_matrix_changed"] is False
    assert payload["candidate_rows_are_matrix_rows"] is False
    assert payload["overlay_interpretation_guide_path"].endswith(
        "evidence_overlay_interpretation_guide.html"
    )

    html = Path(payload["gallery_html"]).read_text(encoding="utf-8")
    assert "Evidence Review Gallery - CID-NL Feature Inclusion Review" in html
    assert "<h1>CID-NL Feature Inclusion / Identity Review</h1>" in html
    assert "feature inclusion first" in html
    assert "identity authority separate" in html
    assert 'class="review-table"' in html
    assert "CID-NL Default Activation Review Overlay" not in html
    assert "target_guardrail:focus_300_184" in html
    assert ">Candidate</dt>" in html
    assert ">Existing</dt>" in html
    assert ">Omit</dt>" in html
    assert "CID-NL adoption review only" in html
    assert "Review focus" in html
    assert "Feature inclusion question" in html
    assert "Identity authority question" in html
    assert "Source/successor relationship" in html
    assert "FAM000001 -&gt; FAM000002" in html
    assert "FAM000003 -&gt; &lt;none&gt;" in html
    assert "Target benchmark context only" in html
    assert "write_authorized" in html
    assert "no_write_detected_baseline_preserved" in html
    assert "Overlay orange detected/rescued traces are MS1 trace status only" in html
    assert "How to read these overlays" in html
    assert "evidence_overlay_interpretation_guide.html" in html
    assert "NL=detected required-tag anchors" not in html
    assert "No detected NL anchor on this hypothesis" not in html
    assert "detected-anchor hypothesis evidence" not in html

    representative_tsv = Path(payload["representative_cells_tsv"]).read_text(
        encoding="utf-8",
    )
    assert "source_peak_hypothesis_id" not in representative_tsv
    assert "successor_peak_hypothesis_id" not in representative_tsv
    assert "successor_decision" not in representative_tsv

    queue_rows = Path(payload["overlay_review_queue_tsv"]).read_text(
        encoding="utf-8",
    )
    assert "FAM000002" in queue_rows
    assert "FAM000004" in queue_rows

    differential_rows = Path(payload["differential_review_tsv"]).read_text(
        encoding="utf-8",
    )
    assert "source_peak_hypothesis_id\tsuccessor_peak_hypothesis_id" in (
        differential_rows
    )
    assert "FAM000001\tFAM000002\tFAM000001->FAM000002\t2\t1\t1\t0" in (
        differential_rows
    )
    assert "FAM000003\t<none>\tFAM000003-><none>\t1\t0\t0\t1" in (
        differential_rows
    )
    assert "ready_for_paired_overlay" in differential_rows
    assert "no_successor_target" in differential_rows
    assert "candidate_ms1_feature_inclusion_supported" in differential_rows
    assert "replacement_merge_dedupe_requires_expected_diff" in differential_rows
    assert "source_and_successor_not_mutually_exclusive" in differential_rows
    assert "\t243.099\t23.66\t127.052\tDNA_dR\taudit_family\t0\t" in (
        differential_rows
    )
    assert "\t300.1605\t23.35\t184.113\tDNA_dR\tproduction_family\t85\t" in (
        differential_rows
    )


def test_links_overlay_summary_into_existing_gallery(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path)
    hypothesis_png = tmp_path / "review" / "output" / "review"
    hypothesis_png.mkdir(parents=True)
    (hypothesis_png / "fam_new_hypothesis.png").write_bytes(b"fixture")
    overlay_summary = tmp_path / "overlay_summary.tsv"
    write_tsv(
        overlay_summary,
        [
            _overlay_summary_row("FAM000002"),
        ],
        review.OVERLAY_SUMMARY_COLUMNS,
    )

    payload = review.build_gallery_review_packet(
        successor_packet_dir=paths["successor_dir"],
        target_preflight_summary_json=paths["target_summary"],
        output_dir=tmp_path / "review",
        source_root=tmp_path,
        overlay_batch_summary_tsvs=(overlay_summary,),
    )

    assert payload["overall_status"] == "needs_overlay_batch"
    assert payload["overlay_linked_group_count"] == 1
    groups_tsv = Path(payload["groups_tsv"]).read_text(encoding="utf-8")
    assert "output/review/fam_new.png" in groups_tsv
    html = Path(payload["gallery_html"]).read_text(encoding="utf-8")
    assert 'data-lightbox-src="' in html
    assert "fam_new.png" in html
    assert "MS1 context PNG" in html
    assert "MS1 detected/rescued trace context only; not NL-tag coverage" in html
    assert "detected-anchor hypothesis evidence" not in html


def test_rejects_stale_overlay_summary_identity(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path)
    overlay_summary = tmp_path / "overlay_summary.tsv"
    stale = _overlay_summary_row("FAM000002")
    stale["output_prefix"] = "999_fam000002_stale_review"
    write_tsv(
        overlay_summary,
        [stale],
        review.OVERLAY_SUMMARY_COLUMNS,
    )

    with pytest.raises(ValueError, match="stale overlay link"):
        review.build_gallery_review_packet(
            successor_packet_dir=paths["successor_dir"],
            target_preflight_summary_json=paths["target_summary"],
            output_dir=tmp_path / "review",
            source_root=tmp_path,
            overlay_batch_summary_tsvs=(overlay_summary,),
        )


def test_require_pass_fails_until_overlay_batch_is_linked(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path)

    exit_code = review.main(
        [
            "--successor-packet-dir",
            str(paths["successor_dir"]),
            "--target-preflight-summary-json",
            str(paths["target_summary"]),
            "--output-dir",
            str(tmp_path / "review"),
            "--source-root",
            str(tmp_path),
            "--require-pass",
        ]
    )

    assert exit_code == 2
    payload = json.loads(
        (tmp_path / "review" / "cid_nl_default_activation_gallery_review_summary.json")
        .read_text(encoding="utf-8")
    )
    assert payload["packet_build_status"] == "pass"
    assert payload["overall_status"] == "needs_overlay_batch"
    assert payload["requires_overlay_batch"] is True


def test_blocks_nonpassing_successor_packet(tmp_path: Path) -> None:
    paths = _write_inputs(tmp_path, successor_status="blocked")

    with pytest.raises(ValueError, match="successor authority packet is not pass"):
        review.build_gallery_review_packet(
            successor_packet_dir=paths["successor_dir"],
            target_preflight_summary_json=paths["target_summary"],
            output_dir=tmp_path / "review",
            source_root=tmp_path,
        )


def _write_inputs(
    tmp_path: Path,
    *,
    successor_status: str = "pass",
) -> dict[str, Path]:
    successor_dir = tmp_path / "successor"
    successor_dir.mkdir()
    target_summary = tmp_path / "target_summary.json"
    alignment_review = tmp_path / "alignment_review.tsv"
    alignment_cells = tmp_path / "alignment_backfill_cell_evidence.tsv"

    write_tsv(
        successor_dir / "successor_authority_decisions.tsv",
        [
            _decision("FAM000001", "FAM000002", "SampleA", "write_authorized"),
            _decision(
                "FAM000001",
                "FAM000002",
                "SampleB",
                "no_write_detected_baseline_preserved",
            ),
            _decision("FAM000003", "", "SampleC", "no_write_omitted"),
        ],
        ("schema_version", *review.DECISION_COLUMNS),
    )
    successor_summary_json = (
        successor_dir
        / "cid_nl_default_activation_successor_authority_summary.json"
    )
    successor_summary_json.write_text(
        json.dumps({"overall_status": successor_status}, indent=2) + "\n",
        encoding="utf-8",
    )
    write_tsv(
        alignment_review,
        [
            _alignment(
                "FAM000001",
                mz="243.099",
                rt="23.66",
                product="127.052",
                accepted="0",
                identity="audit_family",
            ),
            _alignment("FAM000002", mz="300.1605", rt="23.35"),
            _alignment("FAM000003", mz="301.165", rt="23.34"),
            _alignment("FAM000004", mz="302.17", rt="23.36"),
        ],
        review.ALIGNMENT_REVIEW_COLUMNS,
    )
    alignment_cells.write_text(
        "feature_family_id\tsample_stem\n"
        "FAM000002\tSampleA\n"
        "FAM000004\tTumorBC2312_DNA\n",
        encoding="utf-8",
    )
    target_summary.write_text(
        json.dumps(
            {
                "artifacts": {
                    "alignment_review_tsv": {"path": str(alignment_review)},
                    "backfill_cell_evidence_tsv": {"path": str(alignment_cells)},
                },
                "target_pairs": {
                    "focus_300_184": {
                        "peak_hypothesis_id": "FAM000004",
                        "status": "pass",
                        "target_tag": "DNA_dR",
                        "target_precursor_mz": 300.1605,
                        "target_product_mz": 184.113,
                        "identity": {
                            "accepted_cell_count": "85",
                            "accepted_sample_count": "85",
                        },
                        "provenance": {
                            "focus_sample_row": {
                                "sample_stem": "TumorBC2312_DNA",
                                "production_cell_status": "detected",
                                "primary_matrix_area_source": "detected",
                                "source_candidate_id": "candidate-1",
                            },
                        },
                    },
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "successor_dir": successor_dir,
        "target_summary": target_summary,
    }


def _decision(
    old_peak: str,
    successor_peak: str,
    sample: str,
    decision: str,
) -> dict[str, str]:
    return {
        "schema_version": "fixture",
        "old_peak_hypothesis_id": old_peak,
        "sample_stem": sample,
        "successor_peak_hypothesis_id": successor_peak,
        "successor_decision": decision,
        "write_authority": "TRUE" if decision == "write_authorized" else "FALSE",
        "matrix_write_allowed": "TRUE" if decision == "write_authorized" else "FALSE",
        "matrix_effect": (
            "write_accepted_backfill"
            if decision == "write_authorized"
            else "no_write_scope_removed"
        ),
        "human_explanation": f"{decision} explanation",
        "input_resolution_status": "write_ready_blank",
        "candidate_new_peak_hypothesis_ids": successor_peak,
        "candidate_baseline_values": "",
        "accepted_quant_value": "123",
    }


def _alignment(
    family: str,
    *,
    mz: str,
    rt: str,
    product: str = "184.113",
    accepted: str = "85",
    identity: str = "production_family",
) -> dict[str, str]:
    return {
        "feature_family_id": family,
        "neutral_loss_tag": "DNA_dR",
        "family_center_mz": mz,
        "family_center_rt": rt,
        "family_product_mz": product,
        "detected_count": "85",
        "accepted_cell_count": accepted,
        "include_in_primary_matrix": "TRUE",
        "identity_decision": identity,
        "identity_confidence": "high",
        "row_flags": "",
        "reason": "fixture",
    }


def _overlay_summary_row(family: str) -> dict[str, str]:
    if family != "FAM000002":
        raise ValueError(f"fixture overlay row not defined for {family}")
    return {
        "rank": "1",
        "feature_family_id": "FAM000002",
        "seed_group_id": "cid_nl_default_activation::FAM000002",
        "mz": "300.161",
        "rt_min": "21.85",
        "rt_max": "24.85",
        "family_center_rt": "23.35",
        "output_prefix": "001_fam000002_cid_nl_activation_review",
        "status": "success",
        "family_verdict": "ms1_shape_supports_family_backfill",
        "png_path": "output/review/fam_new.png",
        "trace_data_json": "output/review/fam_new_trace.json",
        "shape_supported_fraction": "1",
        "absolute_own_max_shape_supported_fraction": "1",
        "local_apex_supported_fraction": "1",
    }
