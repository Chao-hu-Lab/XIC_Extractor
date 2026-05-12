from pathlib import Path

from tests.test_alignment_xlsx_writer import sample_alignment_matrix
from xic_extractor.alignment.html_report import write_alignment_review_html


def test_alignment_review_html_contains_visual_summary_not_full_cell_table(
    tmp_path: Path,
):
    path = write_alignment_review_html(
        tmp_path / "review_report.html",
        sample_alignment_matrix(),
    )

    html = path.read_text(encoding="utf-8")
    assert "Alignment Review" in html
    assert "Detected / Rescued / Ambiguous" in html
    assert "Ownership pressure" in html
    assert "alignment_cells.tsv" not in html
    assert "<table" not in html.lower()
