from __future__ import annotations

from pathlib import Path

from scripts.validation_artifact_contracts import check_summary_artifact_hashes
from xic_extractor.tabular_io import file_sha256


def test_externalized_artifact_may_be_absent_in_clean_checkout(tmp_path: Path) -> None:
    payload = {
        "input_artifacts": {
            "source_cells_tsv": {
                "path": "output/validation/missing/source_cells.tsv",
                "sha256": "A" * 64,
            },
        },
    }
    problems: list[str] = []

    check_summary_artifact_hashes(
        payload,
        root=tmp_path,
        problems=problems,
        section_names=("input_artifacts",),
    )

    assert problems == []


def test_tracked_artifact_must_exist_in_clean_checkout(tmp_path: Path) -> None:
    payload = {
        "input_artifacts": {
            "checks_tsv": {
                "path": "docs/superpowers/validation/checks.tsv",
                "sha256": "A" * 64,
            },
        },
    }
    problems: list[str] = []

    check_summary_artifact_hashes(
        payload,
        root=tmp_path,
        problems=problems,
        section_names=("input_artifacts",),
    )

    assert any("summary input_artifacts checks_tsv missing" in p for p in problems)


def test_retention_decision_cannot_externalize_tracked_path(
    tmp_path: Path,
) -> None:
    payload = {
        "input_artifacts": {
            "checks_tsv": {
                "path": "docs/superpowers/validation/checks.tsv",
                "retention_decision": "externalize",
                "sha256": "A" * 64,
            },
        },
    }
    problems: list[str] = []

    check_summary_artifact_hashes(
        payload,
        root=tmp_path,
        problems=problems,
        section_names=("input_artifacts",),
    )

    assert any("summary input_artifacts checks_tsv missing" in p for p in problems)


def test_externalized_prefix_cannot_escape_to_tracked_path(
    tmp_path: Path,
) -> None:
    payload = {
        "input_artifacts": {
            "checks_tsv": {
                "path": "output/../docs/superpowers/validation/checks.tsv",
                "sha256": "A" * 64,
            },
        },
    }
    problems: list[str] = []

    check_summary_artifact_hashes(
        payload,
        root=tmp_path,
        problems=problems,
        section_names=("input_artifacts",),
    )

    assert any("summary input_artifacts checks_tsv missing" in p for p in problems)


def test_existing_externalized_artifact_still_hashes(tmp_path: Path) -> None:
    artifact = tmp_path / "output/validation/source_cells.tsv"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("cell\n", encoding="utf-8")
    payload = {
        "input_artifacts": {
            "source_cells_tsv": {
                "path": "output/validation/source_cells.tsv",
                "sha256": "A" * 64,
            },
        },
    }
    problems: list[str] = []

    check_summary_artifact_hashes(
        payload,
        root=tmp_path,
        problems=problems,
        section_names=("input_artifacts",),
    )

    assert any(
        "summary input_artifacts source_cells_tsv sha256 mismatch" in p
        for p in problems
    )


def test_text_artifact_hash_allows_checkout_line_ending_difference(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "docs/superpowers/validation/checks.tsv"
    artifact.parent.mkdir(parents=True)
    lf_content = "check_id\tstatus\none\tpass\n"
    artifact.write_text(lf_content, encoding="utf-8", newline="\n")
    crlf_hash = file_sha256_from_bytes(lf_content.replace("\n", "\r\n").encode())
    payload = {
        "artifacts": {
            "checks_tsv": {
                "path": "docs/superpowers/validation/checks.tsv",
                "sha256": crlf_hash,
            },
        },
    }
    problems: list[str] = []

    check_summary_artifact_hashes(
        payload,
        root=tmp_path,
        problems=problems,
        section_names=("artifacts",),
    )

    assert problems == []


def test_existing_tracked_artifact_hash_passes(tmp_path: Path) -> None:
    artifact = tmp_path / "docs/superpowers/validation/checks.tsv"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("check\n", encoding="utf-8")
    payload = {
        "input_artifacts": {
            "checks_tsv": {
                "path": "docs/superpowers/validation/checks.tsv",
                "sha256": file_sha256(artifact),
            },
        },
    }
    problems: list[str] = []

    check_summary_artifact_hashes(
        payload,
        root=tmp_path,
        problems=problems,
        section_names=("input_artifacts",),
    )

    assert problems == []


def file_sha256_from_bytes(value: bytes) -> str:
    import hashlib

    return hashlib.sha256(value).hexdigest().upper()
