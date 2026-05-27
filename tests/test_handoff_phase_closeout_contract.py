from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLOSEOUT = (
    ROOT
    / "docs"
    / "superpowers"
    / "notes"
    / "2026-05-28-handoff-productization-phase-closeout.md"
)
C0_NOTE = (
    ROOT
    / "docs"
    / "superpowers"
    / "notes"
    / "2026-05-27-handoff-productization-c0-source-of-truth.md"
)
CHECKLIST = (
    ROOT
    / "docs"
    / "superpowers"
    / "notes"
    / "2026-05-21-lcms-msms-handoff-progress-checklist.md"
)

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
