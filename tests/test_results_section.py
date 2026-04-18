from PyQt6.QtWidgets import QLabel

from gui.sections.results_section import ResultsSection


def test_results_section_shows_target_nl_counts_median_area_and_diagnostics(qtbot):
    section = ResultsSection()
    qtbot.addWidget(section)

    section.update_results(
        {
            "total_files": 4,
            "excel_path": "C:\\out\\xic_results.xlsx",
            "targets": [
                {
                    "label": "Analyte",
                    "detected": 2,
                    "total": 4,
                    "nl_ok": 1,
                    "nl_warn": 0,
                    "nl_fail": 1,
                    "nl_no_ms2": 2,
                    "median_area": 12345.67,
                }
            ],
            "istd_warnings": [],
            "diagnostics_count": 3,
        }
    )

    texts = _label_texts(section)

    assert "ANALYTE" in texts
    assert "2/4" in texts
    assert "✓1 ⚠0 ✗1 —2\nMedian Area: 12,345.67" in texts
    assert "DIAGNOSTICS" in texts
    assert "3" in texts
    assert "Issue rows" in texts
    assert "TOTAL FILES" in texts
    assert "4" in texts


def test_results_section_shows_istd_warning_in_new_summary_shape(qtbot):
    section = ResultsSection()
    qtbot.addWidget(section)

    section.update_results(
        {
            "total_files": 2,
            "excel_path": "",
            "targets": [],
            "istd_warnings": [{"label": "ISTD", "detected": 1, "total": 2}],
            "diagnostics_count": 0,
        }
    )

    texts = _label_texts(section)

    assert "⚠ ISTD 未全偵測：ISTD (1/2)" in texts


def _label_texts(section: ResultsSection) -> list[str]:
    return [label.text() for label in section.findChildren(QLabel) if label.text()]
