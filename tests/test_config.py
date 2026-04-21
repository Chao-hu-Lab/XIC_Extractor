import csv
from pathlib import Path

import pytest

from xic_extractor.config import ConfigError, load_config, migrate_settings_dict

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
    assert targets[0].label == "Analyte"
    assert targets[0].neutral_loss_da == pytest.approx(116.0474)


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
    assert any(
        "smooth_points" in warning and "smooth_window" in warning
        for warning in warnings
    )
    assert any("smooth_polyorder" in warning for warning in warnings)


def test_migrate_settings_dict_drops_smooth_sigma_with_warning() -> None:
    migrated, warnings = migrate_settings_dict({"smooth_sigma": "3.0"})

    assert "smooth_sigma" not in migrated
    assert any("smooth_sigma" in warning for warning in warnings)


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
