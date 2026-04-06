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
        "label,mz,rt_min,rt_max,ppm_tol,neutral_loss_da,nl_ppm_warn,nl_ppm_max\n"
        "258.1085,258.1085,8.0,10.0,20,116.0474,20,50\n",
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
    assert read_targets()[0]["label"] == "258.1085"


def test_write_targets_round_trips(tmp_config, monkeypatch):
    monkeypatch.setattr("gui.config_io.CONFIG_DIR", tmp_config)
    write_targets(
        [
            {
                "label": "242.1136",
                "mz": "242.1136",
                "rt_min": "11.0",
                "rt_max": "13.0",
                "ppm_tol": "20",
                "neutral_loss_da": "116.0474",
                "nl_ppm_warn": "20",
                "nl_ppm_max": "50",
            }
        ]
    )
    assert read_targets()[0]["label"] == "242.1136"
