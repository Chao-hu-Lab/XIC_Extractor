import csv
from pathlib import Path

import pytest

from xic_extractor.config import ConfigError, load_config, migrate_settings_dict
from xic_extractor.settings_schema import CANONICAL_SETTINGS_DEFAULTS

SETTINGS_FIELDS = ["key", "value", "description"]
TARGET_FIELDS = [
    "label",
    "mz",
    "rt_min",
    "rt_max",
    "ppm_tol",
    "neutral_loss_da",
    "nl_ppm_warn",
    "nl_ppm_max",
    "is_istd",
    "istd_pair",
]


def _settings_rows(config_dir: Path) -> dict[str, str]:
    data_dir = config_dir.parent / "raw"
    dll_dir = config_dir.parent / "dll"
    data_dir.mkdir(parents=True)
    dll_dir.mkdir(parents=True)
    return {
        "data_dir": str(data_dir),
        "dll_dir": str(dll_dir),
        "smooth_window": "15",
        "smooth_polyorder": "3",
        "peak_rel_height": "0.95",
        "peak_min_prominence_ratio": "0.10",
        "ms2_precursor_tol_da": "0.5",
        "nl_min_intensity_ratio": "0.01",
        "count_no_ms2_as_detected": "false",
    }


def _write_settings(config_dir: Path, overrides: dict[str, str] | None = None) -> None:
    rows = _settings_rows(config_dir)
    if overrides:
        rows.update(overrides)

    config_dir.mkdir(parents=True, exist_ok=True)
    with (config_dir / "settings.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=SETTINGS_FIELDS)
        writer.writeheader()
        for key, value in rows.items():
            writer.writerow({"key": key, "value": value, "description": key})


def _target_row(**overrides: str) -> dict[str, str]:
    row = {
        "label": "Analyte",
        "mz": "258.1085",
        "rt_min": "8.0",
        "rt_max": "10.0",
        "ppm_tol": "20",
        "neutral_loss_da": "116.0474",
        "nl_ppm_warn": "20",
        "nl_ppm_max": "50",
        "is_istd": "false",
        "istd_pair": "",
    }
    row.update(overrides)
    return row


def _write_targets(config_dir: Path, rows: list[dict[str, str]] | None = None) -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    with (config_dir / "targets.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=TARGET_FIELDS)
        writer.writeheader()
        for row in rows or [_target_row()]:
            writer.writerow({field: row.get(field, "") for field in TARGET_FIELDS})


def _write_valid_config(config_dir: Path) -> None:
    _write_settings(config_dir)
    _write_targets(config_dir)


def _assert_error(exc_info: pytest.ExceptionInfo[ConfigError], *parts: str) -> None:
    message = str(exc_info.value)
    for part in parts:
        assert part in message


def test_load_config_derives_output_paths_and_creates_output_dir(
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / "config"
    _write_valid_config(config_dir)

    config, targets = load_config(config_dir)

    assert config.output_csv == tmp_path / "output" / "xic_results.csv"
    assert config.diagnostics_csv == tmp_path / "output" / "xic_diagnostics.csv"
    assert config.output_csv.parent.exists()
    assert config.smooth_window == 15
    assert config.smooth_polyorder == 3
    assert config.count_no_ms2_as_detected is False
    assert config.resolver_mode == "legacy_savgol"
    assert config.resolver_chrom_threshold == pytest.approx(0.05)
    assert config.resolver_min_search_range_min == pytest.approx(0.08)
    assert config.resolver_min_relative_height == pytest.approx(0.0)
    assert config.resolver_min_absolute_height == pytest.approx(25.0)
    assert config.resolver_min_ratio_top_edge == pytest.approx(1.7)
    assert config.resolver_peak_duration_min == pytest.approx(0.0)
    assert config.resolver_peak_duration_max == pytest.approx(2.0)
    assert config.resolver_min_scans == 5
    assert config.parallel_mode == "serial"
    assert config.parallel_workers == 1
    assert targets[0].label == "Analyte"
    assert targets[0].neutral_loss_da == pytest.approx(116.0474)


def test_load_config_hash_reflects_settings_overrides(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    _write_valid_config(config_dir)
    validation_dir = tmp_path / "validation"
    validation_dir.mkdir()

    base_config, _ = load_config(config_dir)
    override_config, _ = load_config(
        config_dir,
        settings_overrides={"data_dir": str(validation_dir)},
    )

    assert override_config.data_dir == validation_dir
    assert override_config.config_hash != base_config.config_hash


def test_load_config_uses_examples_when_runtime_files_are_missing(
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / "config"
    _write_valid_config(config_dir)
    (config_dir / "settings.csv").rename(config_dir / "settings.example.csv")
    (config_dir / "targets.csv").rename(config_dir / "targets.example.csv")

    config, targets = load_config(config_dir)

    assert config.data_dir == tmp_path / "raw"
    assert targets[0].label == "Analyte"
    assert config.config_hash
    assert not (config_dir / "settings.csv").exists()
    assert not (config_dir / "targets.csv").exists()


def test_load_config_missing_settings_file_raises_config_error(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    _write_targets(config_dir)

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_dir)

    _assert_error(exc_info, "settings.csv")


def test_load_config_missing_targets_file_raises_config_error(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    _write_settings(config_dir)

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_dir)

    _assert_error(exc_info, "targets.csv")


def test_load_config_rejects_settings_missing_required_columns(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "settings.csv").write_text(
        "name,value\ndata_dir,C:\\data\n",
        encoding="utf-8-sig",
    )
    _write_targets(config_dir)

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_dir)

    _assert_error(exc_info, "settings.csv", "column key")


def test_load_config_rejects_targets_missing_required_columns(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    _write_settings(config_dir)
    (config_dir / "targets.csv").write_text(
        "label,mz,rt_min,rt_max\nAnalyte,258.1085,8.0,10.0\n",
        encoding="utf-8-sig",
    )

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_dir)

    _assert_error(exc_info, "targets.csv", "column ppm_tol")


def test_load_config_rejects_empty_targets_file(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    _write_settings(config_dir)
    (config_dir / "targets.csv").write_text(
        ",".join(TARGET_FIELDS) + "\n",
        encoding="utf-8-sig",
    )

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_dir)

    _assert_error(exc_info, "targets.csv", "label")


def test_migrate_settings_dict_renames_legacy_key_and_backfills_defaults() -> None:
    migrated, warnings = migrate_settings_dict(
        {
            "data_dir": "C:/data",
            "dll_dir": "C:/dll",
            "smooth_points": "17",
        }
    )

    assert migrated["smooth_window"] == "17"
    assert "smooth_points" not in migrated
    assert migrated["smooth_polyorder"] == "3"
    assert migrated["peak_rel_height"] == "0.95"
    assert migrated["parallel_mode"] == "serial"
    assert migrated["parallel_workers"] == "1"
    assert any(
        "smooth_points" in warning and "smooth_window" in warning
        for warning in warnings
    )
    assert any("smooth_polyorder" in warning for warning in warnings)


def test_migrate_settings_dict_drops_smooth_sigma_with_warning() -> None:
    migrated, warnings = migrate_settings_dict({"smooth_sigma": "3.0"})

    assert "smooth_sigma" not in migrated
    assert any("smooth_sigma" in warning for warning in warnings)


def test_load_config_accepts_local_minimum_resolver_settings(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    _write_settings(
        config_dir,
        {
            "resolver_mode": "local_minimum",
            "resolver_chrom_threshold": "0.08",
            "resolver_min_search_range_min": "0.06",
            "resolver_min_relative_height": "0.12",
            "resolver_min_absolute_height": "90",
            "resolver_min_ratio_top_edge": "1.8",
            "resolver_peak_duration_min": "0.04",
            "resolver_peak_duration_max": "0.80",
            "resolver_min_scans": "9",
        },
    )
    _write_targets(config_dir)

    config, _ = load_config(config_dir)

    assert config.resolver_mode == "local_minimum"
    assert config.resolver_chrom_threshold == pytest.approx(0.08)
    assert config.resolver_min_search_range_min == pytest.approx(0.06)
    assert config.resolver_min_relative_height == pytest.approx(0.12)
    assert config.resolver_min_absolute_height == pytest.approx(90.0)
    assert config.resolver_min_ratio_top_edge == pytest.approx(1.8)
    assert config.resolver_peak_duration_min == pytest.approx(0.04)
    assert config.resolver_peak_duration_max == pytest.approx(0.80)
    assert config.resolver_min_scans == 9


def test_load_config_accepts_zero_local_minimum_floor_values(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    _write_settings(
        config_dir,
        {
            "resolver_mode": "local_minimum",
            "resolver_min_relative_height": "0.0",
            "resolver_peak_duration_min": "0.0",
            "resolver_peak_duration_max": "10.0",
        },
    )
    _write_targets(config_dir)

    config, _ = load_config(config_dir)

    assert config.resolver_min_relative_height == pytest.approx(0.0)
    assert config.resolver_peak_duration_min == pytest.approx(0.0)
    assert config.resolver_peak_duration_max == pytest.approx(10.0)


def test_load_config_accepts_process_parallel_settings(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    _write_settings(
        config_dir,
        {
            "parallel_mode": "process",
            "parallel_workers": "4",
        },
    )
    _write_targets(config_dir)

    config, _ = load_config(config_dir)

    assert config.parallel_mode == "process"
    assert config.parallel_workers == 4


def test_canonical_settings_defaults_include_parallel_settings() -> None:
    assert CANONICAL_SETTINGS_DEFAULTS["parallel_mode"] == "serial"
    assert CANONICAL_SETTINGS_DEFAULTS["parallel_workers"] == "1"


def test_canonical_settings_defaults_include_local_minimum_preset() -> None:
    assert CANONICAL_SETTINGS_DEFAULTS["resolver_chrom_threshold"] == "0.05"
    assert CANONICAL_SETTINGS_DEFAULTS["resolver_min_search_range_min"] == "0.08"
    assert CANONICAL_SETTINGS_DEFAULTS["resolver_min_relative_height"] == "0.0"
    assert CANONICAL_SETTINGS_DEFAULTS["resolver_min_absolute_height"] == "25.0"
    assert CANONICAL_SETTINGS_DEFAULTS["resolver_min_ratio_top_edge"] == "1.7"
    assert CANONICAL_SETTINGS_DEFAULTS["resolver_peak_duration_min"] == "0.0"
    assert CANONICAL_SETTINGS_DEFAULTS["resolver_peak_duration_max"] == "2.0"
    assert CANONICAL_SETTINGS_DEFAULTS["resolver_min_scans"] == "5"


def test_settings_example_includes_parallel_settings() -> None:
    example_path = Path("config/settings.example.csv")

    with example_path.open(newline="", encoding="utf-8-sig") as handle:
        rows = {row["key"]: row["value"] for row in csv.DictReader(handle)}

    assert rows["parallel_mode"] == "serial"
    assert rows["parallel_workers"] == "1"


def test_settings_example_includes_review_report_setting() -> None:
    example_path = Path("config/settings.example.csv")

    with example_path.open(newline="", encoding="utf-8-sig") as handle:
        rows = {row["key"]: row["value"] for row in csv.DictReader(handle)}

    assert rows["emit_review_report"] == "false"


def test_settings_example_includes_local_minimum_preset() -> None:
    example_path = Path("config/settings.example.csv")

    with example_path.open(newline="", encoding="utf-8-sig") as handle:
        rows = {row["key"]: row["value"] for row in csv.DictReader(handle)}

    assert rows["resolver_chrom_threshold"] == "0.05"
    assert rows["resolver_min_search_range_min"] == "0.08"
    assert rows["resolver_min_relative_height"] == "0.0"
    assert rows["resolver_min_absolute_height"] == "25.0"
    assert rows["resolver_min_ratio_top_edge"] == "1.7"
    assert rows["resolver_peak_duration_min"] == "0.0"
    assert rows["resolver_peak_duration_max"] == "2.0"
    assert rows["resolver_min_scans"] == "5"


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("smooth_window", "14"),
        ("smooth_polyorder", "15"),
        ("peak_rel_height", "0.49"),
        ("peak_rel_height", "1.00"),
        ("peak_min_prominence_ratio", "0.00"),
        ("peak_min_prominence_ratio", "0.51"),
        ("ms2_precursor_tol_da", "0"),
        ("nl_min_intensity_ratio", "0"),
        ("nl_min_intensity_ratio", "1.1"),
        ("nl_rt_anchor_search_margin_min", "0"),
        ("nl_rt_anchor_search_margin_min", "-0.1"),
        ("nl_rt_anchor_half_window_min", "0"),
        ("nl_rt_anchor_half_window_min", "-0.1"),
        ("nl_fallback_half_window_min", "0"),
        ("nl_fallback_half_window_min", "-0.1"),
        ("rolling_window_size", "0"),
        ("rolling_window_size", "-1"),
        ("resolver_chrom_threshold", "-0.01"),
        ("resolver_chrom_threshold", "1.01"),
        ("resolver_min_search_range_min", "0"),
        ("resolver_min_relative_height", "-0.01"),
        ("resolver_min_relative_height", "1.1"),
        ("resolver_min_absolute_height", "-1"),
        ("resolver_min_ratio_top_edge", "1.0"),
        ("resolver_peak_duration_min", "-0.01"),
        ("resolver_peak_duration_max", "0"),
        ("resolver_min_scans", "0"),
        ("parallel_workers", "0"),
        ("parallel_workers", "-1"),
    ],
)
def test_load_config_rejects_invalid_settings(
    tmp_path: Path, column: str, value: str
) -> None:
    config_dir = tmp_path / "config"
    _write_settings(config_dir, {column: value})
    _write_targets(config_dir)

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_dir)

    _assert_error(exc_info, "settings.csv", column, value)


def test_load_config_rejects_unknown_resolver_mode(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    _write_settings(config_dir, {"resolver_mode": "wavelet"})
    _write_targets(config_dir)

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_dir)

    _assert_error(exc_info, "settings.csv", "resolver_mode", "wavelet")


def test_load_config_rejects_unknown_parallel_mode(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    _write_settings(config_dir, {"parallel_mode": "thread"})
    _write_targets(config_dir)

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_dir)

    _assert_error(exc_info, "settings.csv", "parallel_mode", "thread")


def test_load_config_rejects_peak_duration_min_above_max(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    _write_settings(
        config_dir,
        {
            "resolver_peak_duration_min": "0.40",
            "resolver_peak_duration_max": "0.20",
        },
    )
    _write_targets(config_dir)

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_dir)

    _assert_error(exc_info, "settings.csv", "resolver_peak_duration_min", "0.40")


def test_load_config_rejects_duplicate_target_labels(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    _write_settings(config_dir)
    _write_targets(config_dir, [_target_row(), _target_row()])

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_dir)

    _assert_error(exc_info, "targets.csv", "row 3", "label", "Analyte")


def test_load_config_rejects_istd_pair_that_is_not_an_istd(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    _write_settings(config_dir)
    _write_targets(
        config_dir,
        [
            _target_row(label="Analyte", istd_pair="Candidate"),
            _target_row(label="Candidate", is_istd="false"),
        ],
    )

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_dir)

    _assert_error(exc_info, "targets.csv", "row 2", "istd_pair", "Candidate")


def test_load_config_rejects_istd_with_istd_pair(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    _write_settings(config_dir)
    _write_targets(
        config_dir,
        [
            _target_row(label="ISTD-A", is_istd="true", istd_pair="ISTD-B"),
            _target_row(label="ISTD-B", is_istd="true"),
        ],
    )

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_dir)

    _assert_error(exc_info, "targets.csv", "row 2", "istd_pair", "ISTD-B")


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("neutral_loss_da", "0"),
        ("neutral_loss_da", "300"),
        ("nl_ppm_warn", ""),
        ("nl_ppm_warn", "0"),
        ("nl_ppm_max", ""),
        ("nl_ppm_max", "0"),
    ],
)
def test_load_config_rejects_invalid_neutral_loss_fields(
    tmp_path: Path, column: str, value: str
) -> None:
    config_dir = tmp_path / "config"
    _write_settings(config_dir)
    _write_targets(config_dir, [_target_row(**{column: value})])

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_dir)

    _assert_error(exc_info, "targets.csv", "row 2", column, value)


def test_load_config_rejects_warn_threshold_above_max(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    _write_settings(config_dir)
    _write_targets(config_dir, [_target_row(nl_ppm_warn="60", nl_ppm_max="50")])

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_dir)

    _assert_error(exc_info, "targets.csv", "row 2", "nl_ppm_warn", "60")


def test_load_config_allows_no_nl_target_with_empty_thresholds(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    _write_settings(config_dir)
    _write_targets(
        config_dir,
        [
            _target_row(
                neutral_loss_da="",
                nl_ppm_warn="",
                nl_ppm_max="",
            )
        ],
    )

    _, targets = load_config(config_dir)

    assert targets[0].neutral_loss_da is None
    assert targets[0].nl_ppm_warn is None
    assert targets[0].nl_ppm_max is None
