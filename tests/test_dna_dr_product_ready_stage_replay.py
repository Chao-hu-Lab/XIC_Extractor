from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.diagnostics import dna_dr_product_ready_stage_replay as replay
from tools.diagnostics.standard_peak_backfill_preset import (
    StandardPeakBackfillPresetOutputs,
)
from xic_extractor.diagnostics.product_ready_preset_publication_check import (
    ProductReadyPresetPublicationCheckOutputs,
)


def test_stage_replay_copies_inputs_and_writes_manifest(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "replay"
    raw_dir = tmp_path / "raw"
    dll_dir = tmp_path / "dll"
    cache_dir = tmp_path / "overlay_cache"
    raw_dir.mkdir()
    dll_dir.mkdir()
    _write_source_alignment(source)
    captured_standard_peak: dict[str, object] = {}
    captured_publication: dict[str, object] = {}

    def fake_standard_peak_runner(**kwargs) -> StandardPeakBackfillPresetOutputs:
        captured_standard_peak.update(kwargs)
        summary = (
            output
            / "standard_peak_backfill_preset"
            / "standard_peak_backfill_preset_summary.json"
        )
        summary.parent.mkdir(parents=True, exist_ok=True)
        summary.write_text('{"status":"pass"}\n', encoding="utf-8")
        manifest = output / "standard_peak_default_matrix_manifest.json"
        manifest.write_text('{"status":"pass"}\n', encoding="utf-8")
        return StandardPeakBackfillPresetOutputs(
            summary_json=summary,
            published_alignment_manifest_json=manifest,
        )

    def fake_publication_checker(**kwargs) -> ProductReadyPresetPublicationCheckOutputs:
        captured_publication.update(kwargs)
        summary = (
            output
            / "product_ready_preset_publication_check"
            / "product_ready_preset_publication_summary.json"
        )
        checks = summary.with_name("product_ready_preset_publication_checks.tsv")
        summary.parent.mkdir(parents=True, exist_ok=True)
        summary.write_text('{"status":"pass"}\n', encoding="utf-8")
        checks.write_text("check_id\tstatus\nok\tpass\n", encoding="utf-8")
        return ProductReadyPresetPublicationCheckOutputs(
            summary_json=summary,
            checks_tsv=checks,
            status="pass",
        )

    outputs = replay.run_stage_replay(
        source_alignment_dir=source,
        output_dir=output,
        raw_dir=raw_dir,
        dll_dir=dll_dir,
        timing_output=output / "timing.json",
        timing_live_output=output / "timing.live.json",
        evidence_cache_dir=cache_dir,
        standard_peak_runner=fake_standard_peak_runner,
        publication_checker=fake_publication_checker,
    )

    manifest = json.loads(outputs.manifest_json.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == replay.SCHEMA_VERSION
    assert manifest["status"] == "pass"
    assert manifest["run_config"]["chunk_workers"] == 2
    assert captured_standard_peak["alignment_dir"] == output.resolve()
    assert captured_standard_peak["raw_dir"] == raw_dir.resolve()
    assert captured_standard_peak["dll_dir"] == dll_dir.resolve()
    assert captured_standard_peak["publication_mode"] == "matrix-only"
    assert captured_standard_peak["evidence_cache_dir"] == cache_dir.resolve()
    assert manifest["run_config"]["evidence_cache_dir"] == str(cache_dir.resolve())
    assert captured_publication["alignment_dir"] == output.resolve()
    matrix_input = manifest["input_artifacts"]["alignment_matrix.tsv"]
    assert matrix_input["row_count"] == 1
    assert len(matrix_input["sha256"]) == 64
    assert (
        manifest["output_artifacts"]["standard_peak_summary_json"]["path"]
        == str(outputs.standard_peak_summary_json.resolve())
    )
    assert outputs.timing_json == (output / "timing.json").resolve()


def test_stage_replay_fails_when_output_dir_is_not_empty(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "replay"
    raw_dir = tmp_path / "raw"
    dll_dir = tmp_path / "dll"
    raw_dir.mkdir()
    dll_dir.mkdir()
    output.mkdir()
    (output / "existing.txt").write_text("x\n", encoding="utf-8")
    _write_source_alignment(source)

    with pytest.raises(ValueError, match="output_dir must be empty"):
        replay.run_stage_replay(
            source_alignment_dir=source,
            output_dir=output,
            raw_dir=raw_dir,
            dll_dir=dll_dir,
            standard_peak_runner=_unused_standard_peak_runner,
            publication_checker=_unused_publication_checker,
        )


def test_stage_replay_requires_cell_evidence(tmp_path: Path) -> None:
    source = tmp_path / "source"
    output = tmp_path / "replay"
    raw_dir = tmp_path / "raw"
    dll_dir = tmp_path / "dll"
    raw_dir.mkdir()
    dll_dir.mkdir()
    _write_source_alignment(source, include_cell_evidence=False)

    with pytest.raises(ValueError, match="alignment_backfill_cell_evidence"):
        replay.run_stage_replay(
            source_alignment_dir=source,
            output_dir=output,
            raw_dir=raw_dir,
            dll_dir=dll_dir,
            standard_peak_runner=_unused_standard_peak_runner,
            publication_checker=_unused_publication_checker,
        )


def _write_source_alignment(
    source: Path,
    *,
    include_cell_evidence: bool = True,
) -> None:
    source.mkdir(parents=True, exist_ok=True)
    for name in (
        "alignment_review.tsv",
        "alignment_matrix.tsv",
        "alignment_matrix_identity.tsv",
        "alignment_owner_backfill_seed_audit.tsv",
        "alignment_matrix.pre_standard_peak_backfill.tsv",
        "alignment_matrix_identity.pre_standard_peak_backfill.tsv",
        "skipped_evidence_ledger.tsv",
    ):
        (source / name).write_text("id\tvalue\nrow\t1\n", encoding="utf-8")
    if include_cell_evidence:
        (source / "alignment_backfill_cell_evidence.tsv").write_text(
            "feature_family_id\tsample_stem\nF1\tS1\n",
            encoding="utf-8",
        )


def _unused_standard_peak_runner(**_kwargs) -> StandardPeakBackfillPresetOutputs:
    raise AssertionError("standard peak runner should not be called")


def _unused_publication_checker(**_kwargs) -> ProductReadyPresetPublicationCheckOutputs:
    raise AssertionError("publication checker should not be called")
