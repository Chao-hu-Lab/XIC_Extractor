import json
from pathlib import Path

from tools.diagnostics.multi_tag_adduct_audit import main


def test_multi_tag_adduct_audit_writes_summary_outputs(tmp_path: Path) -> None:
    alignment_dir = tmp_path / "alignment"
    baseline_dir = tmp_path / "baseline"
    output_dir = tmp_path / "diagnostics"
    _write_review(alignment_dir / "alignment_review.tsv", matrix=False)
    _write_review(baseline_dir / "alignment_review.tsv", matrix=False)
    (alignment_dir / "alignment_cells.tsv").write_text(
        "feature_family_id\tsample_stem\tstatus\n",
        encoding="utf-8",
    )
    adduct_path = tmp_path / "Artificial_Adduct_List.csv"
    adduct_path.write_text(
        "Artificial Adduct No.,Artificial Adduct m/z,Artificial Adduct Name\n"
        "1,21.981945,M+Na-H\n",
        encoding="utf-8",
    )

    code = main(
        [
            "--alignment-dir",
            str(alignment_dir),
            "--baseline-alignment-dir",
            str(baseline_dir),
            "--artificial-adduct-list",
            str(adduct_path),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert code == 0
    payload = json.loads((output_dir / "multi_tag_adduct.json").read_text())
    assert payload["selected_tags"] == ["dR", "R", "MeR"]
    assert payload["tag_combine_mode"] == "union"
    assert payload["matrix_row_count"] == 0
    assert payload["review_row_count"] == 2
    assert payload["tag_overlap"] == {"dR": 1, "R": 1}
    assert payload["artificial_adduct_pair_count"] == 1
    assert payload["matrix_row_delta_vs_baseline"] == 0
    assert (output_dir / "multi_tag_adduct_summary.tsv").is_file()
    assert (output_dir / "multi_tag_adduct_pairs.tsv").is_file()
    assert (output_dir / "multi_tag_adduct.md").is_file()


def _write_review(path: Path, *, matrix: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "feature_family_id\tneutral_loss_tag\tfamily_center_mz\tfamily_center_rt\t"
        "matched_tag_names\tinclude_in_primary_matrix\n"
        f"F001\tdR\t300.000000\t5.000\tdR\t{'TRUE' if matrix else 'FALSE'}\n"
        "F002\tR\t321.981945\t5.020\tR\tFALSE\n",
        encoding="utf-8",
    )
