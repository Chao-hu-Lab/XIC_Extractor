import json
from dataclasses import replace
from pathlib import Path

import pytest

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.extraction.output_dispatch import write_outputs
from xic_extractor.extractor import RunOutput
from xic_extractor.output.method_manifest import (
    METHOD_MANIFEST_SCHEMA_VERSION,
    MethodManifestContext,
    MethodManifestError,
    build_method_manifest,
    load_method_manifest_for_replay,
    write_method_manifest,
)


def test_build_method_manifest_labels_hashes_as_fragments(tmp_path: Path) -> None:
    config = _config(tmp_path)
    targets = [_target("Analyte"), _target("ISTD", is_istd=True)]
    _write_config_inputs(tmp_path)

    payload = build_method_manifest(
        config,
        targets,
        context=MethodManifestContext(
            entrypoint="xic-extractor-cli",
            argv=("--base-dir", str(tmp_path)),
            base_dir=tmp_path,
            config_dir=tmp_path / "config",
            settings_overrides={"data_dir": str(config.data_dir)},
            output_mode="csv_only",
        ),
    )

    assert payload["schema_version"] == METHOD_MANIFEST_SCHEMA_VERSION
    assert payload["run_kind"] == "targeted_extraction"
    assert payload["invocation"] == {
        "entrypoint": "xic-extractor-cli",
        "argv": ["--base-dir", str(tmp_path)],
        "base_dir": str(tmp_path),
        "config_dir": str(tmp_path / "config"),
        "settings_overrides": {"data_dir": str(config.data_dir)},
        "output_mode": "csv_only",
    }
    assert set(payload["input_artifacts"]) == {
        "settings_csv",
        "targets_csv",
        "raw_dir",
        "dll_dir",
        "injection_order_source",
        "rt_prior_library",
        "target_pair_rt_calibration",
        "expected_diff_approval_registry",
    }
    assert set(payload["output_artifacts"]) == {
        "output_csv",
        "long_csv",
        "diagnostics_csv",
        "score_breakdown_csv",
        "method_manifest_json",
    }
    assert payload["input_artifacts"]["settings_csv"]["exists"] is True
    assert len(payload["input_artifacts"]["settings_csv"]["sha256"]) == 64
    assert payload["input_artifacts"]["raw_dir"]["sha256"] is None
    assert payload["config_fragments"]["config_hash"] == {
        "value": "cfg12345",
        "scope": "targets_csv + settings_csv_effective_bytes",
        "is_full_method_hash": False,
    }
    assert payload["config_fragments"]["target_config_hash"] == {
        "value": "tgt12345",
        "scope": "targets_csv_bytes",
        "is_full_method_hash": False,
    }
    assert payload["target_summary"] == {
        "target_count": 2,
        "analyte_count": 1,
        "istd_count": 1,
        "sample_applicability_values": ["all"],
        "isotope_label_type_values": ["unknown"],
    }
    assert payload["output_schema"] == {
        "targeted_output_schema_version": "targeted_output_v1",
        "xic_results_long_csv": {
            "schema_version": "targeted_long_csv_v1",
            "headers": [
                "SampleName",
                "Group",
                "Target",
                "Role",
                "ISTD Pair",
                "RT",
                "Area",
                "NL",
                "Int",
                "PeakStart",
                "PeakEnd",
                "PeakWidth",
                "Confidence",
                "Reason",
                "Product State",
                "Counted Detection",
                "Review State",
                "Projection Reason",
                "Projection Support Reasons",
                "Projection Review Reasons",
                "Projection Conflict Reasons",
                "Projection Not Counted Reasons",
                "Projection Exclusion Reasons",
                "Legacy Authority Status",
                "Benchmark Eligibility State",
            ],
        },
        "xic_diagnostics_csv": {
            "schema_version": "targeted_diagnostics_csv_v1",
            "headers": ["SampleName", "Target", "Issue", "Reason"],
        },
        "xic_score_breakdown_csv": {
            "schema_version": "targeted_score_breakdown_csv_v1",
            "headers": [
                "SampleName",
                "Target",
                "Final Confidence",
                "Detection Counted",
                "Product State",
                "Review State",
                "Projection Reason",
                "Legacy Authority Status",
                "Caps",
                "Raw Score",
                "Support",
                "Concerns",
                "Base Score",
                "Positive Points",
                "Negative Points",
                "symmetry",
                "local_sn",
                "nl_support",
                "rt_prior",
                "rt_centrality",
                "noise_shape",
                "peak_width",
                "Quality Penalty",
                "Quality Flags",
                "Total Severity",
                "Confidence",
                "Prior RT",
                "Prior Source",
            ],
        },
    }
    assert payload["replay_status"] == {
        "capability": "manifest_driven_cli_replay",
        "exact_replay_ready": False,
        "blockers": [
            "timestamped_workbook_hash_not_recorded",
        ],
    }


def test_write_outputs_emits_manifest_without_intermediate_csv(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    output = RunOutput(file_results=[], diagnostics=[])

    write_outputs(config, [_target("Analyte")], output)

    manifest_path = config.output_csv.with_name("method_manifest.json")
    assert manifest_path.exists()
    assert not config.output_csv.exists()
    assert not config.output_csv.with_name("xic_results_long.csv").exists()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == METHOD_MANIFEST_SCHEMA_VERSION
    assert payload["output_artifacts"]["output_csv"]["exists"] is False
    assert payload["output_artifacts"]["method_manifest_json"]["exists"] is True
    assert payload["output_artifacts"]["method_manifest_json"]["sha256"] is None


def test_write_method_manifest_overwrites_with_cli_context(tmp_path: Path) -> None:
    config = _config(tmp_path)
    targets = [_target("Analyte")]

    write_method_manifest(config, targets)
    write_method_manifest(
        config,
        targets,
        context=MethodManifestContext(
            entrypoint="xic-extractor-cli",
            argv=("--skip-excel",),
            base_dir=tmp_path,
            config_dir=tmp_path / "config",
            output_mode="csv_only",
        ),
    )

    payload = json.loads(
        config.output_csv.with_name("method_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["invocation"]["entrypoint"] == "xic-extractor-cli"
    assert payload["invocation"]["argv"] == ["--skip-excel"]
    assert payload["invocation"]["output_mode"] == "csv_only"


def test_load_method_manifest_for_replay_validates_required_hashes(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    targets = [_target("Analyte")]
    _write_config_inputs(tmp_path)

    manifest_path = write_method_manifest(
        config,
        targets,
        context=MethodManifestContext(
            entrypoint="xic-extractor-cli",
            argv=("--base-dir", str(tmp_path), "--skip-excel"),
            base_dir=tmp_path,
            config_dir=tmp_path / "config",
            settings_overrides={"data_dir": str(config.data_dir)},
            output_mode="csv_only",
        ),
    )

    replay = load_method_manifest_for_replay(manifest_path)

    assert replay.manifest_path == manifest_path.resolve()
    assert replay.base_dir == tmp_path.resolve()
    assert replay.config_dir == (tmp_path / "config").resolve()
    assert replay.settings_overrides == {"data_dir": str(config.data_dir)}
    assert replay.output_mode == "csv_only"
    assert replay.parallel_mode == "serial"
    assert replay.parallel_workers == 1


def test_load_method_manifest_for_replay_rejects_drifted_config(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    targets = [_target("Analyte")]
    _write_config_inputs(tmp_path)
    manifest_path = write_method_manifest(
        config,
        targets,
        context=MethodManifestContext(
            entrypoint="xic-extractor-cli",
            base_dir=tmp_path,
            config_dir=tmp_path / "config",
            output_mode="excel",
        ),
    )
    (tmp_path / "config" / "settings.csv").write_text(
        "key,value\nsmooth_window,17\n",
        encoding="utf-8",
    )

    with pytest.raises(MethodManifestError, match="settings_csv sha256 mismatch"):
        load_method_manifest_for_replay(manifest_path)


def test_load_method_manifest_for_replay_rejects_drifted_optional_artifact(
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "expected_diff_approvals.tsv"
    registry_path.write_text("stable\n", encoding="utf-8")
    config = replace(
        _config(tmp_path),
        model_selection_expected_diff_approval_registry=registry_path,
    )
    targets = [_target("Analyte")]
    _write_config_inputs(tmp_path)
    manifest_path = write_method_manifest(
        config,
        targets,
        context=MethodManifestContext(
            entrypoint="xic-extractor-cli",
            base_dir=tmp_path,
            config_dir=tmp_path / "config",
            output_mode="excel",
        ),
    )
    registry_path.write_text("drifted\n", encoding="utf-8")

    with pytest.raises(
        MethodManifestError,
        match="expected_diff_approval_registry sha256 mismatch",
    ):
        load_method_manifest_for_replay(manifest_path)


def _config(tmp_path: Path) -> ExtractionConfig:
    data_dir = tmp_path / "raw"
    output_dir = tmp_path / "output"
    dll_dir = tmp_path / "dll"
    data_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    dll_dir.mkdir(exist_ok=True)
    return ExtractionConfig(
        data_dir=data_dir,
        dll_dir=dll_dir,
        output_csv=output_dir / "xic_results.csv",
        diagnostics_csv=output_dir / "xic_diagnostics.csv",
        smooth_window=15,
        smooth_polyorder=3,
        ms1_morphology_smoothing_window_points=15,
        peak_rel_height=0.95,
        peak_min_prominence_ratio=0.10,
        ms2_precursor_tol_da=0.5,
        nl_min_intensity_ratio=0.01,
        parallel_mode="serial",
        parallel_workers=1,
        config_hash="cfg12345",
        target_config_hash="tgt12345",
    )


def _target(label: str, *, is_istd: bool = False) -> Target:
    return Target(
        label=label,
        mz=284.0989,
        rt_min=15.0,
        rt_max=18.0,
        ppm_tol=20.0,
        neutral_loss_da=116.0474,
        nl_ppm_warn=20.0,
        nl_ppm_max=50.0,
        is_istd=is_istd,
        istd_pair="",
    )


def _write_config_inputs(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "settings.csv").write_text(
        "key,value\nsmooth_window,15\n",
        encoding="utf-8",
    )
    (config_dir / "targets.csv").write_text(
        "label,mz\nAnalyte,284.0989\n",
        encoding="utf-8",
    )
