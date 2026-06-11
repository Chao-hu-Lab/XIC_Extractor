from __future__ import annotations

import csv
from pathlib import Path

from scripts.xlsx_to_targets import TargetRow, _assign_istd_pairs, write_targets_csv


def test_assign_istd_pairs_preserves_standard_claims_and_istd_rows() -> None:
    standard_a = _target("5-hmdC", rt=8.0)
    standard_b = _target("8-oxo-Guo", rt=12.0)
    istd_a = _target("d3-5-hmdC", rt=8.1, is_istd=True)
    istd_b = _target("d3-8-oxo-Guo", rt=12.2, is_istd=True)
    targets = [standard_a, istd_a, standard_b, istd_b]

    _assign_istd_pairs(targets)

    assert standard_a["istd_pair"] == "d3-5-hmdC"
    assert standard_b["istd_pair"] == "d3-8-oxo-Guo"
    assert istd_a["istd_pair"] == ""
    assert istd_b["istd_pair"] == ""


def test_assign_istd_pairs_keeps_hard_rt_gate(capsys) -> None:
    standard = _target("5-hmdC", rt=20.0)
    istd = _target("d3-5-hmdC", rt=8.0, is_istd=True)

    _assign_istd_pairs([standard, istd])

    assert standard["istd_pair"] == ""
    assert "no standard matched for ISTD 'd3-5-hmdC'" in capsys.readouterr().err


def test_write_targets_csv_preserves_public_csv_contract(
    tmp_path: Path,
    capsys,
) -> None:
    output_path = tmp_path / "targets.csv"
    target = _target("5-hmdC", rt=8.0)

    write_targets_csv([target], output_path)

    raw = output_path.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")
    assert b"\r\n" in raw
    with output_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == [
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
        rows = list(reader)
    assert rows == [
        {
            "label": "5-hmdC",
            "mz": "100.0",
            "rt_min": "7.9",
            "rt_max": "8.1",
            "ppm_tol": "20",
            "neutral_loss_da": "116.0474",
            "nl_ppm_warn": "20",
            "nl_ppm_max": "50",
            "is_istd": "false",
            "istd_pair": "",
        }
    ]
    assert f"Written 1 targets to {output_path}" in capsys.readouterr().out


def _target(label: str, *, rt: float, is_istd: bool = False) -> TargetRow:
    return {
        "label": label,
        "mz": 100.0,
        "rt_min": rt - 0.1,
        "rt_max": rt + 0.1,
        "ppm_tol": 20,
        "neutral_loss_da": 116.0474,
        "nl_ppm_warn": 20,
        "nl_ppm_max": 50,
        "is_istd": "true" if is_istd else "false",
        "istd_pair": "",
    }
