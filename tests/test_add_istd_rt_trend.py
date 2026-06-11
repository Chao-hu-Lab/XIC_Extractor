from __future__ import annotations

from scripts.add_istd_rt_trend import InjectionOrderRow, _compute_medians


def test_compute_medians_prefers_qc_pool_when_three_qc_values_exist() -> None:
    rows: list[InjectionOrderRow] = [
        {"inj_name": "QC 1", "sample_type": "QC", "injection_order": 1},
        {"inj_name": "QC 2", "sample_type": "QC", "injection_order": 2},
        {"inj_name": "QC 3", "sample_type": "QC", "injection_order": 3},
        {"inj_name": "sample 1", "sample_type": "Sample", "injection_order": 4},
    ]
    inj_to_raw = {
        "QC 1": "raw-qc-1",
        "QC 2": "raw-qc-2",
        "QC 3": "raw-qc-3",
        "sample 1": "raw-sample-1",
    }
    istd_data = {
        "raw-qc-1": {"ISTD-A": "1.0", "ISTD-B": "10.0"},
        "raw-qc-2": {"ISTD-A": "2.0", "ISTD-B": "bad"},
        "raw-qc-3": {"ISTD-A": "3.0"},
        "raw-sample-1": {"ISTD-A": "99.0", "ISTD-B": "20.0"},
    }

    medians = _compute_medians(
        ["ISTD-A", "ISTD-B", "missing"],
        rows,
        inj_to_raw,
        istd_data,
    )

    assert medians == {"ISTD-A": 2.0, "ISTD-B": 15.0, "missing": None}


def test_compute_medians_falls_back_to_all_values_when_qc_pool_is_small() -> None:
    rows: list[InjectionOrderRow] = [
        {"inj_name": "QC 1", "sample_type": "QC", "injection_order": 1},
        {"inj_name": "sample 1", "sample_type": "Sample", "injection_order": 2},
        {"inj_name": "unmatched", "sample_type": "Sample", "injection_order": 3},
    ]
    inj_to_raw = {
        "QC 1": "raw-qc-1",
        "sample 1": "raw-sample-1",
        "unmatched": "",
    }
    istd_data = {
        "raw-qc-1": {"ISTD-A": "1.0"},
        "raw-sample-1": {"ISTD-A": "5.0"},
    }

    medians = _compute_medians(["ISTD-A"], rows, inj_to_raw, istd_data)

    assert medians == {"ISTD-A": 3.0}
