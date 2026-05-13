from pathlib import Path

import tomllib

from scripts import run_alignment_validation
from xic_extractor.alignment.validation_pipeline import AlignmentValidationOutputs


def test_cli_resolves_alignment_dir_and_passes_paths(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    alignment_dir = tmp_path / "alignment"
    alignment_dir.mkdir()
    (alignment_dir / "alignment_review.tsv").write_text("review", encoding="utf-8")
    (alignment_dir / "alignment_matrix.tsv").write_text("matrix", encoding="utf-8")
    legacy = tmp_path / "fh.tsv"
    legacy.write_text("legacy", encoding="utf-8")
    output_dir = tmp_path / "validation"
    captured = {}

    def fake_run_alignment_validation(**kwargs):
        captured.update(kwargs)
        output_dir.mkdir(parents=True, exist_ok=True)
        summary = output_dir / "alignment_validation_summary.tsv"
        matches = output_dir / "alignment_legacy_matches.tsv"
        summary.write_text("summary", encoding="utf-8")
        matches.write_text("matches", encoding="utf-8")
        return AlignmentValidationOutputs(summary_tsv=summary, matches_tsv=matches)

    monkeypatch.setattr(
        run_alignment_validation,
        "run_alignment_validation",
        fake_run_alignment_validation,
    )

    code = run_alignment_validation.main(
        [
            "--alignment-dir",
            str(alignment_dir),
            "--legacy-fh-tsv",
            str(legacy),
            "--output-dir",
            str(output_dir),
            "--match-ppm",
            "10",
            "--match-rt-sec",
            "30",
            "--sample-scope",
            "intersection",
            "--match-distance-warn-median",
            "0.25",
            "--match-distance-warn-p90",
            "0.75",
        ]
    )

    assert code == 0
    assert captured["alignment_review"] == (
        alignment_dir / "alignment_review.tsv"
    ).resolve()
    assert captured["alignment_matrix"] == (
        alignment_dir / "alignment_matrix.tsv"
    ).resolve()
    assert captured["legacy_fh_tsv"] == legacy.resolve()
    assert captured["match_ppm"] == 10.0
    assert captured["match_rt_sec"] == 30.0
    assert captured["sample_scope"] == "intersection"
    assert captured["match_distance_warn_median"] == 0.25
    assert captured["match_distance_warn_p90"] == 0.75
    assert "Validation summary TSV:" in capsys.readouterr().out


def test_cli_accepts_explicit_alignment_files(tmp_path: Path, monkeypatch) -> None:
    review = tmp_path / "review.tsv"
    matrix = tmp_path / "matrix.tsv"
    legacy = tmp_path / "fix.xlsx"
    review.write_text("review", encoding="utf-8")
    matrix.write_text("matrix", encoding="utf-8")
    legacy.write_text("legacy", encoding="utf-8")
    captured = {}

    def fake_run_alignment_validation(**kwargs):
        captured.update(kwargs)
        output_dir = kwargs["output_dir"]
        return AlignmentValidationOutputs(
            summary_tsv=output_dir / "alignment_validation_summary.tsv",
            matches_tsv=output_dir / "alignment_legacy_matches.tsv",
        )

    monkeypatch.setattr(
        run_alignment_validation,
        "run_alignment_validation",
        fake_run_alignment_validation,
    )

    code = run_alignment_validation.main(
        [
            "--alignment-review",
            str(review),
            "--alignment-matrix",
            str(matrix),
            "--legacy-combine-fix-xlsx",
            str(legacy),
        ]
    )

    assert code == 0
    assert captured["alignment_review"] == review.resolve()
    assert captured["alignment_matrix"] == matrix.resolve()
    assert captured["legacy_combine_fix_xlsx"] == legacy.resolve()


def test_cli_rejects_missing_alignment_files(tmp_path: Path, capsys) -> None:
    legacy = tmp_path / "fh.tsv"
    legacy.write_text("legacy", encoding="utf-8")

    code = run_alignment_validation.main(
        [
            "--alignment-review",
            str(tmp_path / "missing-review.tsv"),
            "--alignment-matrix",
            str(tmp_path / "missing-matrix.tsv"),
            "--legacy-fh-tsv",
            str(legacy),
        ]
    )

    assert code == 2
    assert "alignment review does not exist" in capsys.readouterr().err


def test_cli_rejects_zero_legacy_sources(tmp_path: Path, capsys) -> None:
    alignment_dir = tmp_path / "alignment"
    alignment_dir.mkdir()
    (alignment_dir / "alignment_review.tsv").write_text("review", encoding="utf-8")
    (alignment_dir / "alignment_matrix.tsv").write_text("matrix", encoding="utf-8")

    code = run_alignment_validation.main(["--alignment-dir", str(alignment_dir)])

    assert code == 2
    assert "at least one legacy source" in capsys.readouterr().err


def test_cli_rejects_invalid_sample_scope() -> None:
    code = run_alignment_validation.main(["--sample-scope", "all"])

    assert code == 2


def test_pyproject_registers_alignment_validation_cli_script() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert (
        pyproject["project"]["scripts"]["xic-align-validate-cli"]
        == "scripts.run_alignment_validation:main"
    )
