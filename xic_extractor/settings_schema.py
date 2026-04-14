CANONICAL_SETTINGS_DEFAULTS: dict[str, str] = {
    "data_dir": "C:/your/data/folder",
    "dll_dir": "C:\\Xcalibur\\system\\programs",
    "smooth_window": "15",
    "smooth_polyorder": "3",
    "peak_rel_height": "0.95",
    "peak_min_prominence_ratio": "0.10",
    "ms2_precursor_tol_da": "0.5",
    "nl_min_intensity_ratio": "0.01",
    "count_no_ms2_as_detected": "false",
}

CANONICAL_SETTINGS_DESCRIPTIONS: dict[str, str] = {
    "data_dir": "資料來源資料夾（換批次只改這裡）",
    "dll_dir": "Xcalibur DLL 路徑（通常不需更改）",
    "smooth_window": "Savitzky-Golay 平滑視窗長度（必須為奇數，建議 9-21）",
    "smooth_polyorder": "Savitzky-Golay 多項式階數（通常 2-4）",
    "peak_rel_height": "Peak 邊界的相對高度（0.95 = 積分到 apex 的 5%，範圍 0.5-0.99）",
    "peak_min_prominence_ratio": "Peak prominence 至少為 apex 的比例（越低越寬容，0.05-0.20）",
    "ms2_precursor_tol_da": "MS2 precursor m/z 匹配視窗（Da，對應 DDA quadrupole 隔離寬度）",
    "nl_min_intensity_ratio": "NL product 強度至少為該 scan base peak 的比例（1% 排除 noise）",
    "count_no_ms2_as_detected": "是否將無 MS2 觸發的樣品算為偵測到（DDA 隨機性假陰性補救用）",
}
