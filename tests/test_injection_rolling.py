from pathlib import Path

from xic_extractor.injection_rolling import read_injection_order, rolling_median_rt


def test_read_csv(tmp_path: Path) -> None:
    p = tmp_path / "info.csv"
    p.write_text("Sample_Name,Injection_Order\nS_A,1\nS_B,2\n", encoding="utf-8")
    assert read_injection_order(p) == {"S_A": 1, "S_B": 2}


def test_read_strips_whitespace(tmp_path: Path) -> None:
    p = tmp_path / "info.csv"
    p.write_text("Sample_Name,Injection_Order\n  S_A  ,5\n", encoding="utf-8")
    assert read_injection_order(p) == {"S_A": 5}


def test_rolling_median_uses_window() -> None:
    rts = {f"s{i}": float(i) for i in range(1, 11)}
    order = {f"s{i}": i for i in range(1, 11)}
    assert rolling_median_rt("istd", "s5", rts, order, window=2) == 5.0


def test_rolling_median_respects_gaps() -> None:
    rts = {"s1": 1.0, "s2": 2.0, "s10": 10.0}
    order = {"s1": 1, "s2": 2, "s10": 10}
    assert rolling_median_rt("istd", "s10", rts, order, window=1) is None


def test_rolling_median_missing_target_returns_none() -> None:
    assert rolling_median_rt("istd", "unknown", {}, {}, window=5) is None


def test_read_xlsx(tmp_path: Path) -> None:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["Sample_Name", "Injection_Order"])
    ws.append(["S_X", 3])
    ws.append(["S_Y", 7])
    p = tmp_path / "info.xlsx"
    wb.save(p)
    assert read_injection_order(p) == {"S_X": 3, "S_Y": 7}
