CANONICAL_SETTINGS_DEFAULTS: dict[str, str] = {
    "data_dir": "C:/your/data/folder",
    "dll_dir": "C:\\Xcalibur\\system\\programs",
    "smooth_window": "15",
    "smooth_polyorder": "3",
    "peak_rel_height": "0.95",
    "peak_min_prominence_ratio": "0.10",
    "resolver_mode": "legacy_savgol",
    "resolver_chrom_threshold": "0.05",
    "resolver_min_search_range_min": "0.08",
    "resolver_min_relative_height": "0.0",
    "resolver_min_absolute_height": "25.0",
    "resolver_min_ratio_top_edge": "1.7",
    "resolver_peak_duration_min": "0.0",
    "resolver_peak_duration_max": "2.0",
    "resolver_min_scans": "5",
    "ms2_precursor_tol_da": "1.6",
    "nl_min_intensity_ratio": "0.01",
    "count_no_ms2_as_detected": "false",
    "injection_order_source": "",
    "rolling_window_size": "5",
    "dirty_matrix_mode": "false",
    "rt_prior_library_path": "",
    "emit_score_breakdown": "false",
    "emit_review_report": "false",
    "keep_intermediate_csv": "false",
    "nl_rt_anchor_search_margin_min": "2.0",
    "nl_rt_anchor_half_window_min": "1.0",
    "nl_fallback_half_window_min": "2.0",
    "parallel_mode": "serial",
    "parallel_workers": "1",
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
    "resolver_mode": "峰切割演算法（legacy_savgol 或 local_minimum）",
    "resolver_chrom_threshold": "Local minimum resolver 低強度剪枝百分位（0-1）",
    "resolver_min_search_range_min": "Local minimum 搜尋 valley 的 RT 視窗（分鐘）",
    "resolver_min_relative_height": (
        "Local minimum 最低相對 apex 高度（相對全 trace 最大值）"
    ),
    "resolver_min_absolute_height": "Local minimum 最低絕對 apex 強度",
    "resolver_min_ratio_top_edge": (
        "Local minimum apex 與兩側 edge 的最小比值（需 > 1）"
    ),
    "resolver_peak_duration_min": "Local minimum 峰最短持續時間（分鐘）",
    "resolver_peak_duration_max": "Local minimum 峰最長持續時間（分鐘）",
    "resolver_min_scans": "Local minimum 區段最少 scans 數",
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
    "injection_order_source": (
        "Sample 注射順序來源檔（CSV/XLSX 有 Sample_Name 與 Injection_Order 欄；"
        "留空則 fallback to RAW mtime）"
    ),
    "rolling_window_size": "ISTD RT prior 的滾動視窗半徑（±N 個注射）",
    "dirty_matrix_mode": "髒基質模式（放寬 S/N、收緊峰形；尿液等複雜基質用）",
    "rt_prior_library_path": (
        "developer/debug RT prior library CSV path; leave empty for normal use"
    ),
    "emit_score_breakdown": "是否輸出 Score Breakdown sheet（預設關閉）",
    "emit_review_report": "是否輸出 Review Report HTML（預設關閉）",
    "keep_intermediate_csv": "是否保留中間 CSV 檔（除錯用，預設關閉）",
    "nl_rt_anchor_search_margin_min": (
        "NL 錨定搜尋半徑（min）：以 rt_center ±此值搜尋 NL 確認的 MS2 作為 RT anchor"
    ),
    "nl_rt_anchor_half_window_min": (
        "NL 錨定後的 XIC 半寬（min）：找到 anchor 時，XIC 窗口 = [anchor_rt ± 此值]"
    ),
    "nl_fallback_half_window_min": (
        "NL 錨定失敗時的 fallback XIC 半寬（min）：窗口 = [rt_center ± 此值]"
    ),
    "parallel_mode": "執行後端（serial 或 process；預設 serial）",
    "parallel_workers": "Process mode worker 數量（>= 1；預設 1）",
}
