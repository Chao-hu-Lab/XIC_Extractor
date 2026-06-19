import json
from pathlib import Path

import pytest

from xic_extractor.alignment.quant_matrix_artifacts import (
    artifact_record,
    cell_provenance_rerun_problems,
    is_sha256,
    read_json_object,
    resolve_real_bundle_paths,
    source_relpath_reference,
    source_summary_input_hash_problems,
)
from xic_extractor.tabular_io import file_sha256


def test_resolve_real_bundle_paths_accepts_externalized_cell_provenance(
    tmp_path: Path,
) -> None:
    bundle = tmp_path / "bundle"
    quant_dir = bundle / "quant_matrix_version"
    quant_dir.mkdir(parents=True)
    baseline = quant_dir / "quant_matrix.tsv"
    summary = quant_dir / "cell_provenance_summary.json"
    fixture = quant_dir / "cell_provenance_minimal_fixture.tsv"
    baseline.write_text("Mz\tRT\tSampleA\n1\t2\t3\n", encoding="utf-8")
    summary.write_text('{"source_sha256": "' + "A" * 64 + '"}\n', encoding="utf-8")
    fixture.write_text("id\nA\n", encoding="utf-8")
    payload = {
        "artifacts": {
            "baseline_quant_matrix": {"path": "quant_matrix_version/quant_matrix.tsv"},
            "cell_provenance": {
                "path": "quant_matrix_version/cell_provenance.tsv",
                "externalized": True,
                "replacement_or_summary": (
                    "quant_matrix_version/cell_provenance_summary.json"
                ),
            },
            "cell_provenance_minimal_fixture": {
                "path": "quant_matrix_version/cell_provenance_minimal_fixture.tsv",
            },
        },
    }

    paths = resolve_real_bundle_paths(
        payload,
        bundle / "quant_matrix_real_bundle_summary.json",
        required_labels=("baseline_quant_matrix",),
        include_cell_provenance=True,
        include_cell_provenance_reference=True,
        optional_labels=("cell_provenance_minimal_fixture",),
    )

    assert paths["baseline_quant_matrix"] == baseline.resolve(strict=False)
    assert paths["cell_provenance_reference"] == (
        quant_dir / "cell_provenance.tsv"
    ).resolve(strict=False)
    assert paths["cell_provenance_summary"] == summary.resolve(strict=False)
    assert paths["cell_provenance_minimal_fixture"] == fixture.resolve(strict=False)
    assert "cell_provenance" not in paths


def test_resolve_real_bundle_paths_rejects_path_escape(tmp_path: Path) -> None:
    payload = {
        "artifacts": {
            "baseline_quant_matrix": {"path": "../quant_matrix.tsv"},
        },
    }

    with pytest.raises(ValueError, match="bundle-relative"):
        resolve_real_bundle_paths(
            payload,
            tmp_path / "bundle/summary.json",
            required_labels=("baseline_quant_matrix",),
        )


def test_cell_provenance_rerun_problems_compare_source_sha(tmp_path: Path) -> None:
    provenance = tmp_path / "cell_provenance.tsv"
    summary = tmp_path / "cell_provenance_summary.json"
    provenance.write_text("id\nA\n", encoding="utf-8")
    summary.write_text(
        json.dumps({"source_sha256": file_sha256(provenance)}, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    assert (
        cell_provenance_rerun_problems(
            provenance,
            summary,
            invalid_message_prefix="invalid",
            mismatch_message="rerun mismatch",
        )
        == []
    )
    summary.write_text(
        json.dumps({"source_sha256": "0" * 64}, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    assert cell_provenance_rerun_problems(
        provenance,
        summary,
        invalid_message_prefix="invalid",
        mismatch_message="rerun mismatch",
    ) == ["rerun mismatch"]


def test_source_summary_input_hash_problems(tmp_path: Path) -> None:
    inputs = {}
    for label, value in (
        ("baseline_quant_matrix", "matrix"),
        ("input_matrix_identity", "identity"),
        ("production_acceptance_manifest", "manifest"),
        ("expected_diff", "diff"),
    ):
        path = tmp_path / f"{label}.tsv"
        path.write_text(value + "\n", encoding="utf-8")
        inputs[label] = path
    source_summary = tmp_path / "source_summary.tsv"
    source_summary.write_text(
        "\t".join(
            (
                "schema_version",
                "input_quant_matrix_sha256",
                "input_matrix_identity_sha256",
                "production_acceptance_manifest_sha256",
                "expected_diff_sha256",
            )
        )
        + "\n"
        + "\t".join(
            (
                "quant_matrix_source_summary_v1",
                file_sha256(inputs["baseline_quant_matrix"]),
                file_sha256(inputs["input_matrix_identity"]),
                file_sha256(inputs["production_acceptance_manifest"]),
                file_sha256(inputs["expected_diff"]),
            )
        )
        + "\n",
        encoding="utf-8",
    )

    assert source_summary_input_hash_problems(
        source_summary,
        expected_inputs=inputs,
    ) == []
    inputs["expected_diff"].write_text("changed\n", encoding="utf-8")

    assert source_summary_input_hash_problems(
        source_summary,
        expected_inputs=inputs,
    ) == ["source_summary expected_diff_sha256 mismatch"]


def test_json_record_and_reference_helpers(tmp_path: Path) -> None:
    path = tmp_path / "out/report.json"
    path.parent.mkdir(parents=True)
    path.write_text('{"ok": true}\n', encoding="utf-8")
    outside = tmp_path.parent / "outside.tsv"

    assert read_json_object(path) == {"ok": True}
    assert artifact_record(path, base_dir=tmp_path) == {
        "path": "out/report.json",
        "sha256": file_sha256(path),
    }
    assert source_relpath_reference(path, source_root=tmp_path) == "out/report.json"
    assert str(outside.resolve(strict=False)) == source_relpath_reference(
        outside,
        source_root=tmp_path,
    )
    assert is_sha256("A" * 64)
    assert not is_sha256("A" * 63)
