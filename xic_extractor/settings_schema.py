CANONICAL_SETTINGS_DEFAULTS: dict[str, str] = {
    "data_dir": "C:/your/data/folder",
    "dll_dir": "C:\\Xcalibur\\system\\programs",
    "smooth_window": "15",
    "smooth_polyorder": "3",
    "peak_rel_height": "0.95",
    "peak_min_prominence_ratio": "0.10",
    "ms2_precursor_tol_da": "1.6",
    "nl_min_intensity_ratio": "0.01",
    "count_no_ms2_as_detected": "false",
    "nl_rt_anchor_search_margin_min": "2.0",
    "nl_rt_anchor_half_window_min": "1.0",
    "nl_fallback_half_window_min": "2.0",
}

CANONICAL_SETTINGS_DESCRIPTIONS: dict[str, str] = {
    "data_dir": "資料來源資料夾（換批次只改這裡）",
    "dll_dir": "Xcalibur DLL 路徑（通常不需更改）",
    "smooth_window": "Savitzky-Golay 平滑視窗長度（必須為奇數，建議 9-21）",
    "smooth_polyorder": "Savitzky-Golay 多項式階數（通常 2-4）",
    "peak_rel_height": (
        "Peak 邊界的相對高度（0.95 = 積分到 apex 的 5%，範圍 0.5-0.99）"
    ),
    "peak_min_prominence_ratio": (
        "Peak prominence 至少為 apex 的比例（越低越寬容，0.05-0.20）"
    ),
    "ms2_precursor_tol_da": (
        "MS2 precursor m/z 匹配視窗（Da，建議設為 quadrupole 隔離視窗 + 0.4 Da 緩衝，"
        "Fusion Lumos CID 典型隔離視窗 1.2 Da → 預設 1.6 Da）"
    ),
    "nl_min_intensity_ratio": (
        "NL product 強度至少為該 scan base peak 的比例（1% 排除 noise）"
    ),
    "count_no_ms2_as_detected": (
        "是否將無 MS2 觸發的樣品算為偵測到（DDA 隨機性假陰性補救用）"
    ),
    "nl_rt_anchor_search_margin_min": (
        "NL 錨定搜尋半徑（min）：以 rt_center ±此值搜尋 NL 確認的 MS2 作為 RT anchor"
    ),
    "nl_rt_anchor_half_window_min": (
        "NL 錨定後的 XIC 半寬（min）：找到 anchor 時，XIC 窗口 = [anchor_rt ± 此值]"
    ),
    "nl_fallback_half_window_min": (
        "NL 錨定失敗時的 fallback XIC 半寬（min）：窗口 = [rt_center ± 此值]"
    ),
}
