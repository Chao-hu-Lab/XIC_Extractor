from pathlib import Path

import pytest
from openpyxl import Workbook

from xic_extractor.alignment.drift_evidence import (
    DriftEvidenceLookup,
    SampleDriftEvidence,
    read_targeted_istd_drift_evidence,
)


def test_lookup_returns_median_sample_delta_and_injection_order() -> None:
    lookup = DriftEvidenceLookup(
        points=(
            SampleDriftEvidence(
                sample_stem="sample-a",
                injection_order=7,
                trend_id="trend-001",
                istd_rt_min=1.9,
                local_trend_rt_min=2.1,
                rt_drift_delta_min=-0.2,
                source="targeted_istd_trend",
            ),
            SampleDriftEvidence(
                sample_stem="sample-a",
                injection_order=7,
                trend_id="trend-002",
                istd_rt_min=2.0,
                local_trend_rt_min=2.0,
                rt_drift_delta_min=0.0,
                source="targeted_istd_trend",
            ),
            SampleDriftEvidence(
                sample_stem="sample-b",
                injection_order=10,
                trend_id="trend-001",
                istd_rt_min=2.1,
                local_trend_rt_min=2.0,
                rt_drift_delta_min=0.1,
                source="batch_istd_trend",
            ),
        )
    )

    assert lookup.source == "targeted_istd_trend"
    assert lookup.sample_delta_min("sample-a") == -0.1
    assert lookup.sample_delta_min("sample-b") == 0.1
    assert lookup.sample_delta_min("missing") is None
    assert lookup.injection_order("sample-a") == 7
    assert lookup.injection_order("missing") is None


def test_lookup_rejects_conflicting_injection_orders_for_sample() -> None:
    lookup = DriftEvidenceLookup(
        points=(
            SampleDriftEvidence(
                sample_stem="sample-a",
                injection_order=7,
                trend_id="trend-001",
                istd_rt_min=1.9,
                local_trend_rt_min=2.1,
                rt_drift_delta_min=-0.2,
                source="targeted_istd_trend",
            ),
            SampleDriftEvidence(
                sample_stem="sample-a",
                injection_order=8,
                trend_id="trend-002",
                istd_rt_min=2.0,
                local_trend_rt_min=2.0,
                rt_drift_delta_min=0.0,
                source="targeted_istd_trend",
            ),
        )
    )

    with pytest.raises(ValueError, match="conflicting injection order"):
        lookup.injection_order("sample-a")


def test_read_targeted_istd_drift_evidence_uses_opaque_trends_and_no_target_context(
    tmp_path: Path,
) -> None:
    workbook = tmp_path / "targeted.xlsx"
    sample_info = tmp_path / "sample_info.csv"
    sample_info.write_text(
        "Sample_Name,Injection_Order\nsample-a,1\nsample-b,2\nsample-c,3\n",
        encoding="utf-8",
    )
    _write_targeted_workbook(workbook)

    lookup = read_targeted_istd_drift_evidence(
        targeted_workbook=workbook,
        sample_info=sample_info,
        local_window=10,
    )

    assert lookup.source == "targeted_istd_trend"
    assert [point.trend_id for point in lookup.points] == [
        "trend-001",
        "trend-001",
        "trend-001",
    ]
    assert [point.sample_stem for point in lookup.points] == [
        "sample-a",
        "sample-b",
        "sample-c",
    ]
    assert [point.injection_order for point in lookup.points] == [1, 2, 3]
    assert [round(point.rt_drift_delta_min, 2) for point in lookup.points] == [
        -0.10,
        0.0,
        0.10,
    ]
    assert [point.source for point in lookup.points] == [
        "targeted_istd_trend",
        "targeted_istd_trend",
        "targeted_istd_trend",
    ]
    assert lookup.sample_delta_min("sample-a") == pytest.approx(-0.10)
    assert lookup.sample_delta_min("sample-b") == 0.0
    assert lookup.sample_delta_min("sample-c") == pytest.approx(0.10)

    point = lookup.points[0]
    assert not hasattr(point, "istd_label")
    assert not hasattr(point, "target_label")


def _write_targeted_workbook(path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "XIC Results"
    ws.append(["SampleName", "Target", "Role", "RT", "GT Pass"])
    ws.append(["sample-a", "Analyte A", "Target", 4.0, "PASS"])
    ws.append([None, "ISTD-B", "ISTD", 1.9, "FAIL"])
    ws.append([None, "ISTD-B", "ISTD", "not numeric", "PASS"])
    ws.append(["sample-b", "Analyte B", "Target", 4.1, "PASS"])
    ws.append([None, "ISTD-B", "ISTD", 2.0, "PASS"])
    ws.append(["sample-c", "Analyte C", "Target", 4.2, "PASS"])
    ws.append([None, "ISTD-B", "ISTD", 2.1, "PASS"])
    wb.save(path)
