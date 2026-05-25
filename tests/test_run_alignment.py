import json
import tomllib
from pathlib import Path

import pytest

from scripts import run_alignment
from xic_extractor.alignment.pipeline import AlignmentRunOutputs
from xic_extractor.raw_reader import RawReaderError


def test_run_alignment_cli_passes_paths_settings_and_debug_flags(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    output_dir = tmp_path / "alignment"
    captured = {}

    def fake_run_alignment(**kwargs):
        captured.update(kwargs)
        output_dir.mkdir(parents=True, exist_ok=True)
        review = output_dir / "alignment_review.tsv"
        matrix = output_dir / "alignment_matrix.tsv"
        cells = output_dir / "alignment_cells.tsv"
        integration = output_dir / "alignment_cell_integration_audit.tsv"
        backfill_seed = output_dir / "alignment_owner_backfill_seed_audit.tsv"
        status = output_dir / "alignment_matrix_status.tsv"
        for path in (review, matrix, cells, integration, backfill_seed, status):
            path.write_text("x\n", encoding="utf-8")
        return AlignmentRunOutputs(
            workbook=output_dir / "alignment_results.xlsx",
            review_html=output_dir / "review_report.html",
            review_tsv=review,
            matrix_tsv=matrix,
            cells_tsv=cells,
            integration_audit_tsv=integration,
            backfill_seed_audit_tsv=backfill_seed,
            status_matrix_tsv=status,
            edge_evidence_tsv=output_dir / "owner_edge_evidence.tsv",
        )

    monkeypatch.setattr(run_alignment, "run_alignment", fake_run_alignment)

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--output-dir",
            str(output_dir),
            "--resolver-mode",
            "legacy_savgol",
            "--emit-alignment-cells",
            "--emit-alignment-integration-audit",
            "--emit-alignment-backfill-seed-audit",
            "--emit-alignment-status-matrix",
            "--emit-baseline-audit-asls",
        ]
    )

    assert code == 0
    assert captured["discovery_batch_index"] == batch_index.resolve()
    assert captured["raw_dir"] == raw_dir.resolve()
    assert captured["dll_dir"] == dll_dir.resolve()
    assert captured["output_dir"] == output_dir.resolve()
    assert captured["alignment_config"].max_ppm == 50.0
    peak_config = captured["peak_config"]
    assert peak_config.data_dir == raw_dir.resolve()
    assert peak_config.dll_dir == dll_dir.resolve()
    assert peak_config.output_csv == output_dir.resolve() / "xic_results.csv"
    assert peak_config.diagnostics_csv == output_dir.resolve() / "xic_diagnostics.csv"
    assert peak_config.resolver_mode == "legacy_savgol"
    assert peak_config.baseline_audit_method == "asls"
    assert captured["output_level"] == "machine"
    assert captured["emit_alignment_cells"] is True
    assert captured["emit_alignment_integration_audit"] is True
    assert captured["emit_alignment_backfill_seed_audit"] is True
    assert captured["emit_alignment_status_matrix"] is True
    assert captured["raw_workers"] == 1
    assert captured["raw_xic_batch_size"] == 1
    assert captured["drift_lookup"] is None
    stdout = capsys.readouterr().out
    assert "Alignment review TSV:" in stdout
    assert "alignment_review.tsv" in stdout
    assert "alignment_cell_integration_audit.tsv" in stdout
    assert "alignment_owner_backfill_seed_audit.tsv" in stdout
    assert "alignment_matrix_status.tsv" in stdout
    assert "Owner edge evidence TSV:" in stdout


def test_run_alignment_env_enables_asls_baseline_audit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    output_dir = tmp_path / "alignment"
    captured = {}

    def fake_run_alignment(**kwargs):
        captured.update(kwargs)
        return AlignmentRunOutputs()

    monkeypatch.setattr(run_alignment, "run_alignment", fake_run_alignment)
    monkeypatch.setenv("BASELINE_AUDIT_METHOD", "asls")

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert code == 0
    assert captured["peak_config"].baseline_audit_method == "asls"


def test_run_alignment_cli_passes_identity_coherence_flags(monkeypatch, tmp_path):
    batch = tmp_path / "batch.csv"
    raw_dir = tmp_path / "raw"
    dll_dir = tmp_path / "dll"
    out_dir = tmp_path / "out"
    controls = tmp_path / "controls.tsv"
    batch.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir.mkdir()
    dll_dir.mkdir()
    controls.write_text("control_id\n", encoding="utf-8")
    seen = {}

    def fake_run_alignment(**kwargs):
        seen.update(kwargs)
        return AlignmentRunOutputs(
            identity_coherence_output_dir=out_dir / "identity",
        )

    monkeypatch.setattr(run_alignment, "run_alignment", fake_run_alignment)

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--output-dir",
            str(out_dir),
            "--emit-identity-coherence-diagnostic",
            "--identity-coherence-output-dir",
            str(out_dir / "identity"),
            "--identity-coherence-controls-manifest",
            str(controls),
        ]
    )

    assert code == 0
    assert seen["emit_identity_coherence_diagnostic"] is True
    assert seen["identity_coherence_output_dir"] == out_dir / "identity"
    assert seen["identity_coherence_controls_manifest"] == controls


def test_run_alignment_cli_ignores_identity_manifest_when_diagnostic_disabled(
    monkeypatch,
    tmp_path,
) -> None:
    batch = tmp_path / "batch.csv"
    raw_dir = tmp_path / "raw"
    dll_dir = tmp_path / "dll"
    out_dir = tmp_path / "out"
    missing_controls = tmp_path / "missing-controls.tsv"
    batch.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir.mkdir()
    dll_dir.mkdir()
    seen = {}

    def fake_run_alignment(**kwargs):
        seen.update(kwargs)
        return AlignmentRunOutputs()

    monkeypatch.setattr(run_alignment, "run_alignment", fake_run_alignment)

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--output-dir",
            str(out_dir),
            "--identity-coherence-controls-manifest",
            str(missing_controls),
        ]
    )

    assert code == 0
    assert seen["emit_identity_coherence_diagnostic"] is False
    assert seen["identity_coherence_controls_manifest"] is None


def test_run_alignment_cli_accepts_output_level_debug(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    captured = {}

    def fake_run_alignment(**kwargs):
        captured.update(kwargs)
        return AlignmentRunOutputs()

    monkeypatch.setattr(run_alignment, "run_alignment", fake_run_alignment)

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--output-level",
            "debug",
        ],
    )

    assert code == 0
    assert captured["output_level"] == "debug"


def test_run_alignment_cli_defaults_to_local_minimum_production_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    captured = {}

    def fake_run_alignment(**kwargs):
        captured.update(kwargs)
        return AlignmentRunOutputs()

    monkeypatch.setattr(run_alignment, "run_alignment", fake_run_alignment)

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
        ],
    )

    assert code == 0
    assert captured["peak_config"].resolver_mode == "local_minimum"


def test_run_alignment_cli_keeps_region_first_safe_merge_out_of_production_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    captured = {}

    def fake_run_alignment(**kwargs):
        captured.update(kwargs)
        return AlignmentRunOutputs()

    monkeypatch.setattr(run_alignment, "run_alignment", fake_run_alignment)

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--resolver-mode",
            "region_first_safe_merge",
        ],
    )

    assert code == 0
    assert captured["peak_config"].resolver_mode == "local_minimum"


def test_run_alignment_cli_passes_raw_workers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    captured = {}

    def fake_run_alignment(**kwargs):
        captured.update(kwargs)
        return AlignmentRunOutputs()

    monkeypatch.setattr(run_alignment, "run_alignment", fake_run_alignment)

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--raw-workers",
            "4",
        ],
    )

    assert code == 0
    assert captured["raw_workers"] == 4


def test_run_alignment_cli_passes_raw_xic_batch_size(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    captured = {}

    def fake_run_alignment(**kwargs):
        captured.update(kwargs)
        return AlignmentRunOutputs()

    monkeypatch.setattr(run_alignment, "run_alignment", fake_run_alignment)

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--raw-xic-batch-size",
            "64",
        ],
    )

    assert code == 0
    assert captured["raw_xic_batch_size"] == 64


def test_run_alignment_cli_passes_owner_backfill_xic_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    captured = {}

    def fake_run_alignment(**kwargs):
        captured.update(kwargs)
        return AlignmentRunOutputs()

    monkeypatch.setattr(run_alignment, "run_alignment", fake_run_alignment)

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--owner-backfill-xic-backend",
            "ms1-index",
        ],
    )

    assert code == 0
    assert captured["owner_backfill_xic_backend"] == "ms1_index"


def test_run_alignment_cli_passes_hybrid_owner_backfill_xic_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    captured = {}

    def fake_run_alignment(**kwargs):
        captured.update(kwargs)
        return AlignmentRunOutputs()

    monkeypatch.setattr(run_alignment, "run_alignment", fake_run_alignment)

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--owner-backfill-xic-backend",
            "ms1-index-hybrid",
        ],
    )

    assert code == 0
    assert captured["owner_backfill_xic_backend"] == "ms1_index_hybrid"


def test_run_alignment_cli_passes_preconsolidate_owner_families(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    captured = {}

    def fake_run_alignment(**kwargs):
        captured.update(kwargs)
        return AlignmentRunOutputs()

    monkeypatch.setattr(run_alignment, "run_alignment", fake_run_alignment)

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--preconsolidate-owner-families",
        ],
    )

    assert code == 0
    assert captured["preconsolidate_owner_families"] is True


def test_run_alignment_cli_validation_fast_profile_sets_raw_execution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    captured = {}

    def fake_run_alignment(**kwargs):
        captured.update(kwargs)
        return AlignmentRunOutputs()

    monkeypatch.setattr(run_alignment, "run_alignment", fake_run_alignment)

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--performance-profile",
            "validation-fast",
        ],
    )

    assert code == 0
    assert captured["raw_workers"] == 8
    assert captured["raw_xic_batch_size"] == 64


def test_run_alignment_cli_explicit_raw_options_override_performance_profile(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    captured = {}

    def fake_run_alignment(**kwargs):
        captured.update(kwargs)
        return AlignmentRunOutputs()

    monkeypatch.setattr(run_alignment, "run_alignment", fake_run_alignment)

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--performance-profile",
            "validation-fast",
            "--raw-workers",
            "3",
            "--raw-xic-batch-size",
            "16",
        ],
    )

    assert code == 0
    assert captured["raw_workers"] == 3
    assert captured["raw_xic_batch_size"] == 16


def test_run_alignment_cli_requires_sample_info_and_targeted_istd_together(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(tmp_path / "missing.csv"),
            "--raw-dir",
            str(tmp_path / "missing-raws"),
            "--dll-dir",
            str(tmp_path / "missing-dll"),
            "--sample-info",
            str(tmp_path / "sample_info.csv"),
        ],
    )

    assert code == 2
    assert (
        "--sample-info is required with --targeted-istd-workbook, "
        "and both must be provided together"
    ) in capsys.readouterr().err


def test_run_alignment_cli_builds_and_passes_drift_lookup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    sample_info = tmp_path / "sample_info.csv"
    sample_info.write_text("sample\nSample_A\n", encoding="utf-8")
    targeted_workbook = tmp_path / "targeted.xlsx"
    targeted_workbook.write_text("workbook", encoding="utf-8")
    drift_lookup = object()
    captured = {}

    def fake_read_targeted_istd_drift_evidence(**kwargs):
        captured["drift_kwargs"] = kwargs
        return drift_lookup

    def fake_run_alignment(**kwargs):
        captured["run_kwargs"] = kwargs
        return AlignmentRunOutputs()

    monkeypatch.setattr(
        run_alignment,
        "read_targeted_istd_drift_evidence",
        fake_read_targeted_istd_drift_evidence,
    )
    monkeypatch.setattr(run_alignment, "run_alignment", fake_run_alignment)

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--sample-info",
            str(sample_info),
            "--targeted-istd-workbook",
            str(targeted_workbook),
            "--raw-workers",
            "3",
            "--raw-xic-batch-size",
            "16",
        ],
    )

    assert code == 0
    assert captured["drift_kwargs"] == {
        "targeted_workbook": targeted_workbook.resolve(),
        "sample_info": sample_info.resolve(),
        "local_window": 40,
    }
    assert captured["run_kwargs"]["drift_lookup"] is drift_lookup
    assert captured["run_kwargs"]["raw_workers"] == 3
    assert captured["run_kwargs"]["raw_xic_batch_size"] == 16


def test_run_alignment_cli_passes_custom_drift_local_window(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    sample_info = tmp_path / "sample_info.csv"
    sample_info.write_text("sample\nSample_A\n", encoding="utf-8")
    targeted_workbook = tmp_path / "targeted.xlsx"
    targeted_workbook.write_text("workbook", encoding="utf-8")
    captured = {}

    def fake_read_targeted_istd_drift_evidence(**kwargs):
        captured["drift_kwargs"] = kwargs
        return object()

    monkeypatch.setattr(
        run_alignment,
        "read_targeted_istd_drift_evidence",
        fake_read_targeted_istd_drift_evidence,
    )
    monkeypatch.setattr(
        run_alignment,
        "run_alignment",
        lambda **kwargs: AlignmentRunOutputs(),
    )

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--sample-info",
            str(sample_info),
            "--targeted-istd-workbook",
            str(targeted_workbook),
            "--drift-local-window",
            "12",
        ],
    )

    assert code == 0
    assert captured["drift_kwargs"]["local_window"] == 12


def test_run_alignment_cli_rejects_missing_sample_info_with_targeted_workbook(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    targeted_workbook = tmp_path / "targeted.xlsx"
    targeted_workbook.write_text("workbook", encoding="utf-8")

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--sample-info",
            str(tmp_path / "missing_sample_info.csv"),
            "--targeted-istd-workbook",
            str(targeted_workbook),
        ],
    )

    assert code == 2
    assert "sample info does not exist" in capsys.readouterr().err


def test_run_alignment_cli_rejects_missing_targeted_workbook_with_sample_info(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    sample_info = tmp_path / "sample_info.csv"
    sample_info.write_text("sample\nSample_A\n", encoding="utf-8")

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--sample-info",
            str(sample_info),
            "--targeted-istd-workbook",
            str(tmp_path / "missing_targeted.xlsx"),
        ],
    )

    assert code == 2
    assert "targeted ISTD workbook does not exist" in capsys.readouterr().err


@pytest.mark.parametrize("exc", [OSError("cannot read workbook"), KeyError("Sample")])
def test_run_alignment_cli_returns_2_for_drift_reader_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    exc: Exception,
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    sample_info = tmp_path / "sample_info.csv"
    sample_info.write_text("sample\nSample_A\n", encoding="utf-8")
    targeted_workbook = tmp_path / "targeted.xlsx"
    targeted_workbook.write_text("workbook", encoding="utf-8")

    def fail_read_targeted_istd_drift_evidence(**kwargs):
        raise exc

    monkeypatch.setattr(
        run_alignment,
        "read_targeted_istd_drift_evidence",
        fail_read_targeted_istd_drift_evidence,
    )

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--sample-info",
            str(sample_info),
            "--targeted-istd-workbook",
            str(targeted_workbook),
        ],
    )

    assert code == 2
    assert str(exc) in capsys.readouterr().err


def test_run_alignment_cli_passes_owner_backfill_min_detected_samples(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    captured = {}

    def fake_run_alignment(**kwargs):
        captured.update(kwargs)
        return AlignmentRunOutputs()

    monkeypatch.setattr(run_alignment, "run_alignment", fake_run_alignment)

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--owner-backfill-min-detected-samples",
            "3",
        ],
    )

    assert code == 0
    assert captured["alignment_config"].owner_backfill_min_detected_samples == 3


def test_run_alignment_cli_writes_timing_json(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()
    timing_path = tmp_path / "diagnostics" / "alignment_timing.json"

    def fake_run_alignment(**kwargs):
        timing_recorder = kwargs["timing_recorder"]
        with timing_recorder.stage(
            "alignment.read_candidates",
            metrics={"candidate_count": 0},
        ):
            pass
        return AlignmentRunOutputs()

    monkeypatch.setattr(run_alignment, "run_alignment", fake_run_alignment)

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
            "--timing-output",
            str(timing_path),
        ],
    )

    assert code == 0
    payload = json.loads(timing_path.read_text(encoding="utf-8"))
    assert payload["pipeline"] == "alignment"
    assert payload["records"][0]["stage"] == "alignment.read_candidates"
    assert payload["records"][0]["metrics"] == {"candidate_count": 0}
    assert "Timing JSON:" in capsys.readouterr().out


def test_run_alignment_cli_rejects_invalid_raw_workers(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()

    with pytest.raises(SystemExit) as exc_info:
        run_alignment.main(
            [
                "--discovery-batch-index",
                str(batch_index),
                "--raw-dir",
                str(raw_dir),
                "--dll-dir",
                str(dll_dir),
                "--raw-workers",
                "0",
            ],
        )

    assert exc_info.value.code == 2
    assert "value must be an integer >= 1" in capsys.readouterr().err


def test_run_alignment_cli_rejects_missing_batch_index(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(tmp_path / "missing.csv"),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
        ]
    )

    assert code == 2
    assert "discovery batch index does not exist" in capsys.readouterr().err


def test_run_alignment_cli_rejects_missing_raw_dir(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(tmp_path / "missing-raws"),
            "--dll-dir",
            str(dll_dir),
        ]
    )

    assert code == 2
    assert "raw directory does not exist" in capsys.readouterr().err


def test_run_alignment_cli_rejects_missing_dll_dir(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(tmp_path / "missing-dll"),
        ]
    )

    assert code == 2
    assert "dll directory does not exist" in capsys.readouterr().err


@pytest.mark.parametrize("exc", [RawReaderError("raw fail"), ValueError("bad input")])
def test_run_alignment_cli_returns_2_for_user_visible_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    exc: Exception,
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text("sample_stem,raw_file,candidate_csv\n", encoding="utf-8")
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()

    def fail_run_alignment(**kwargs):
        raise exc

    monkeypatch.setattr(run_alignment, "run_alignment", fail_run_alignment)

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
        ]
    )

    assert code == 2
    assert str(exc) in capsys.readouterr().err


def test_run_alignment_cli_returns_2_for_missing_candidate_csv(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    batch_index = tmp_path / "discovery_batch_index.csv"
    batch_index.write_text(
        "sample_stem,raw_file,candidate_csv\n"
        "Sample_A,C:/stale/Sample_A.raw,missing/discovery_candidates.csv\n",
        encoding="utf-8",
    )
    raw_dir = tmp_path / "raws"
    raw_dir.mkdir()
    dll_dir = tmp_path / "dll"
    dll_dir.mkdir()

    code = run_alignment.main(
        [
            "--discovery-batch-index",
            str(batch_index),
            "--raw-dir",
            str(raw_dir),
            "--dll-dir",
            str(dll_dir),
        ]
    )

    assert code == 2
    stderr = capsys.readouterr().err
    assert "missing" in stderr
    assert "discovery_candidates.csv" in stderr


def test_pyproject_registers_alignment_cli_script() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert (
        pyproject["project"]["scripts"]["xic-align-cli"]
        == "scripts.run_alignment:main"
    )
