from pathlib import Path

import pytest

from xic_extractor.alignment.identity_coherence_validation.bundle import (
    bundle_from_output_dir,
    read_tsv_dict_rows,
    read_tsv_rows,
    tsv_digest,
)


def _write(path: Path, text: str, *, encoding: str = "utf-8") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding=encoding)
    return path


def test_bundle_from_output_dir_uses_frozen_identity_coherence_names(
    tmp_path: Path,
) -> None:
    bundle = bundle_from_output_dir(tmp_path / "run")

    assert bundle.requests_tsv == (
        tmp_path
        / "run"
        / "identity_coherence"
        / "untargeted_identity_coherence_requests.tsv"
    )
    assert bundle.decisions_tsv.name == "untargeted_identity_coherence_decisions.tsv"
    assert (
        bundle.cell_evidence_tsv.name
        == "untargeted_identity_coherence_cell_evidence.tsv"
    )
    assert bundle.controls_tsv.name == "untargeted_identity_coherence_controls.tsv"
    assert bundle.summary_md.name == "untargeted_identity_coherence_summary.md"


def test_read_tsv_rows_preserves_header_and_order(tmp_path: Path) -> None:
    path = _write(tmp_path / "rows.tsv", "a\tb\n1\t2\n3\t4\n")

    rows = read_tsv_rows(path)

    assert rows.header == ("a", "b")
    assert rows.rows == (("1", "2"), ("3", "4"))
    assert tsv_digest(rows) == "header=2 rows=2"


def test_read_tsv_rows_rejects_empty_file(tmp_path: Path) -> None:
    path = _write(tmp_path / "empty.tsv", "")

    with pytest.raises(ValueError, match="empty TSV"):
        read_tsv_rows(path)


def test_read_tsv_dict_rows_handles_utf8_sig(tmp_path: Path) -> None:
    path = _write(tmp_path / "controls.tsv", "a\tb\n1\t2\n", encoding="utf-8-sig")

    rows = read_tsv_dict_rows(path)

    assert rows == ({"a": "1", "b": "2"},)
