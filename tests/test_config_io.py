import csv

import pytest

from gui.config_io import read_settings, read_targets, write_settings, write_targets


@pytest.fixture()
def tmp_config(tmp_path):
    (tmp_path / "settings.csv").write_text(
        "key,value,description\ndata_dir,C:\\data,資料目錄\ndll_dir,C:\\dll,DLL路徑\n"
        "smooth_sigma,3.0,sigma\nsmooth_points,15,points\n",
        encoding="utf-8-sig",
    )
    (tmp_path / "targets.csv").write_text(
        "label,mz,rt_min,rt_max,ppm_tol,neutral_loss_da,nl_ppm_warn,nl_ppm_max,is_istd,istd_pair\n"
        "5-hmdC,258.1085,8.0,10.0,20,116.0474,20,50,false,d3-5-hmdC\n"
        "d3-5-hmdC,261.1273,8.0,10.0,20,116.0474,20,50,true,\n",
        encoding="utf-8-sig",
    )
    return tmp_path


def test_read_settings(tmp_config, monkeypatch):
    monkeypatch.setattr("gui.config_io.CONFIG_DIR", tmp_config)
    assert read_settings()["smooth_sigma"] == "3.0"


def test_write_settings_round_trips(tmp_config, monkeypatch):
    monkeypatch.setattr("gui.config_io.CONFIG_DIR", tmp_config)
    write_settings(
        {
            "data_dir": "C:\\new",
            "dll_dir": "C:\\d",
            "smooth_sigma": "4.0",
            "smooth_points": "11",
        }
    )
    assert read_settings()["data_dir"] == "C:\\new"


def test_write_settings_preserves_description(tmp_config, monkeypatch):
    monkeypatch.setattr("gui.config_io.CONFIG_DIR", tmp_config)
    write_settings(
        {
            "data_dir": "C:\\x",
            "dll_dir": "C:\\y",
            "smooth_sigma": "3.0",
            "smooth_points": "15",
        }
    )
    rows = list(
        csv.DictReader((tmp_config / "settings.csv").open(encoding="utf-8-sig"))
    )
    assert {row["key"]: row["description"] for row in rows}["data_dir"] == "資料目錄"


def test_read_targets(tmp_config, monkeypatch):
    monkeypatch.setattr("gui.config_io.CONFIG_DIR", tmp_config)
    assert read_targets()[0]["label"] == "5-hmdC"


def test_write_targets_round_trips(tmp_config, monkeypatch):
    monkeypatch.setattr("gui.config_io.CONFIG_DIR", tmp_config)
    write_targets(
        [
            {
                "label": "5-hmdC",
                "mz": "258.1085",
                "rt_min": "8.0",
                "rt_max": "10.0",
                "ppm_tol": "20",
                "neutral_loss_da": "116.0474",
                "nl_ppm_warn": "20",
                "nl_ppm_max": "50",
                "is_istd": "false",
                "istd_pair": "d3-5-hmdC",
            }
        ]
    )
    assert read_targets()[0]["label"] == "5-hmdC"


def test_write_targets_round_trips_with_istd_fields(tmp_config, monkeypatch):
    monkeypatch.setattr("gui.config_io.CONFIG_DIR", tmp_config)
    write_targets(
        [
            {
                "label": "5-hmdC",
                "mz": "258.1085",
                "rt_min": "8.0",
                "rt_max": "10.0",
                "ppm_tol": "20",
                "neutral_loss_da": "116.0474",
                "nl_ppm_warn": "20",
                "nl_ppm_max": "50",
                "is_istd": "false",
                "istd_pair": "d3-5-hmdC",
            }
        ]
    )
    targets = read_targets()
    assert targets[0]["is_istd"] == "false"
    assert targets[0]["istd_pair"] == "d3-5-hmdC"


def test_read_targets_backward_compat_missing_istd_cols(tmp_path, monkeypatch):
    """Old CSV without is_istd/istd_pair columns reads without error."""
    (tmp_path / "targets.csv").write_text(
        "label,mz,rt_min,rt_max,ppm_tol,neutral_loss_da,nl_ppm_warn,nl_ppm_max\n"
        "5-hmdC,258.1085,8,10,20,116.0474,20,50\n",
        encoding="utf-8-sig",
    )
    monkeypatch.setattr("gui.config_io.CONFIG_DIR", tmp_path)
    targets = read_targets()
    assert targets[0]["label"] == "5-hmdC"
    assert targets[0].get("is_istd", "false") == "false"


def test_read_settings_copies_example_when_missing(tmp_path, monkeypatch):
    """read_settings() 在 settings.csv 不存在時自動複製 .example.csv。"""
    (tmp_path / "settings.example.csv").write_text(
        "key,value,description\ndata_dir,/placeholder,資料目錄\n",
        encoding="utf-8-sig",
    )
    monkeypatch.setattr("gui.config_io.CONFIG_DIR", tmp_path)
    result = read_settings()
    assert result["data_dir"] == "/placeholder"
    assert (tmp_path / "settings.csv").exists()


def test_read_targets_copies_example_when_missing(tmp_path, monkeypatch):
    """read_targets() 在 targets.csv 不存在時自動複製 .example.csv。"""
    (tmp_path / "targets.example.csv").write_text(
        "label,mz,rt_min,rt_max,ppm_tol,neutral_loss_da,nl_ppm_warn,nl_ppm_max\n"
        "ExA,258.1085,8.0,10.0,20,116.0474,20,50\n",
        encoding="utf-8-sig",
    )
    monkeypatch.setattr("gui.config_io.CONFIG_DIR", tmp_path)
    result = read_targets()
    assert result[0]["label"] == "ExA"
    assert (tmp_path / "targets.csv").exists()
