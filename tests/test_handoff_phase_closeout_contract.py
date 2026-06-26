from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "handoff_phase_closeout"
CLOSEOUT = (
    FIXTURE_DIR
    / "phase_closeout_contract.md"
)
C0_NOTE = (
    FIXTURE_DIR
    / "c0_source_reference.md"
)
CHECKLIST = (
    FIXTURE_DIR
    / "checklist_reference.md"
)
OBSIDIAN_HANDOFF_CONTRACT = ROOT / "docs" / "agent" / "obsidian-handoff-contract.md"

VALID_LABELS = {
    "retire_now",
    "facade_only",
    "needs_behavior_spec",
    "keep_for_now",
    "externalize",
}

REQUIRED_SURFACE_TOKENS = (
    "TraceGroup",
    "PeakHypothesis",
    "handoff_spine_runtime.py",
    "ExtractionResult.selected_hypothesis",
    "Targeted CSV projection",
    "peak_candidates.tsv",
    "PeakDetectionResult",
    "output.messages",
    "Anchor diagnostics",
    "alignment_matrix.tsv",
    "Legacy resolver surfaces",
    "Baseline / ASLS surfaces",
)
MATRIX_HEADER = (
    "| Surface | Owner | Label | Evidence | Blocker | Next action | "
    "Next PR target |"
)


def test_handoff_phase_closeout_contract_is_decision_ready() -> None:
    text = CLOSEOUT.read_text(encoding="utf-8")

    assert "Pending final execution" not in text
    assert not re.search(r"Status:.*production_ready", text)
    assert "alignment_matrix.tsv migration done" not in text
    assert "85RAW acceptance passed" not in text
    assert "default resolver switch ready" not in text
    assert "default baseline switch ready" not in text

    rows = _matrix_rows(text)
    surfaces = {row["Surface"] for row in rows}
    for token in REQUIRED_SURFACE_TOKENS:
        assert any(token in surface for surface in surfaces), token

    next_targets = 0
    for row in rows:
        assert _cell_text(row["Label"]) in VALID_LABELS
        assert _cell_text(row["Evidence"])
        assert _cell_text(row["Blocker"])
        assert _cell_text(row["Next action"])
        if _cell_text(row["Next PR target"]).lower() == "yes":
            next_targets += 1

    assert next_targets == 1 or ("`no_go`" in text and next_targets == 0)
    assert "## Recommended Next PR" in text
    assert "alignment_matrix_handoff_behavior_spec" in text

    closeout_name = CLOSEOUT.name
    assert closeout_name in C0_NOTE.read_text(encoding="utf-8")
    assert closeout_name in CHECKLIST.read_text(encoding="utf-8")


def test_selected_handoff_peak_call_surface_remains_targeted_only() -> None:
    occurrences = _source_occurrences("selected_handoff_peak(")
    files = {path for path, _line_number in occurrences}

    expected = {
        Path("xic_extractor/extraction/handoff_spine_runtime.py"),
        Path("xic_extractor/extraction/target_extraction.py"),
    }
    assert expected.issubset(files)

    unexpected = sorted(files - expected)
    assert unexpected == []


def test_obsidian_handoff_contract_defines_branch_closeout_guardrails() -> None:
    text = OBSIDIAN_HANDOFF_CONTRACT.read_text(encoding="utf-8")

    assert "public contract" in text
    assert "docs governance" in text
    assert "approved file moves" in text
    assert "normal durable closeout surface" in text
    assert "The PR body seed must be short" in text
    assert "entire closeout summary" in text


def test_obsidian_handoff_contract_defines_doc_placement_taxonomy() -> None:
    text = OBSIDIAN_HANDOFF_CONTRACT.read_text(encoding="utf-8")

    assert "## Placement marker and taxonomy" in text
    assert "Doc placement:" in text
    assert "Repo owner:" in text
    for placement in (
        "formal_repo_doc",
        "repo_active_stub",
        "branch_closeout_summary",
        "repo_stub_plus_obsidian",
        "private_obsidian_note",
        "ignored_artifact",
        "throwaway_scratch",
    ):
        assert placement in text
    for field in (
        "repo: XIC_Extractor",
        "branch: <branch-name>",
        "source_type:",
        "visibility: internal",
        "status: draft",
        "repo_owner:",
        "active_stub:",
        "source_hash:",
        "created_at:",
    ):
        assert field in text
    assert "Staged tracked deletions are not adjudicated by placement markers" in text
    assert "## Daily document routing" in text


def _matrix_rows(text: str) -> list[dict[str, str]]:
    lines = text.splitlines()
    start = lines.index(MATRIX_HEADER)
    header = _split_row(lines[start])
    rows: list[dict[str, str]] = []
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        cells = _split_row(line)
        assert len(cells) == len(header)
        rows.append(dict(zip(header, cells, strict=True)))
    assert rows
    return rows


def _split_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _cell_text(value: str) -> str:
    return value.replace("`", "").strip()


def _source_occurrences(pattern: str) -> list[tuple[Path, int]]:
    occurrences: list[tuple[Path, int]] = []
    for path in (ROOT / "xic_extractor").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if pattern in line:
                occurrences.append((path.relative_to(ROOT), line_number))
    return occurrences
