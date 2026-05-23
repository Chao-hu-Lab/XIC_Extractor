import csv
from dataclasses import replace
from pathlib import Path

import pytest

from tests.alignment.identity_coherence.output_fixtures import output_record
from xic_extractor.alignment.identity_coherence.output import (
    IdentityCoherenceOutputContext,
    IdentityCoherenceOutputPaths,
    IdentityCoherenceOutputRecord,
    render_identity_coherence_summary,
    write_identity_coherence_cell_evidence_tsv,
    write_identity_coherence_controls_tsv,
    write_identity_coherence_decisions_tsv,
    write_identity_coherence_outputs,
    write_identity_coherence_requests_tsv,
)
from xic_extractor.alignment.identity_coherence.schema import (
    IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS,
    IDENTITY_COHERENCE_CONTROL_COLUMNS,
    IDENTITY_COHERENCE_DECISION_COLUMNS,
    IDENTITY_COHERENCE_REQUEST_COLUMNS,
)


def _read_tsv(path: Path) -> tuple[dict[str, str], ...]:
    with path.open(newline="", encoding="utf-8") as handle:
        return tuple(csv.DictReader(handle, delimiter="\t"))


def _read_header(path: Path) -> tuple[str, ...]:
    first_line = path.read_text(encoding="utf-8").splitlines()[0]
    return tuple(first_line.split("\t"))


def _record() -> IdentityCoherenceOutputRecord:
    return output_record()


def _assert_in_order(text: str, headings: tuple[str, ...]) -> None:
    positions = [text.index(heading) for heading in headings]
    assert positions == sorted(positions)


def test_request_decision_and_cell_tsv_writers_use_contract_headers(tmp_path):
    record = _record()

    requests_path = write_identity_coherence_requests_tsv(
        tmp_path / "requests.tsv",
        (record,),
    )
    decisions_path = write_identity_coherence_decisions_tsv(
        tmp_path / "decisions.tsv",
        (record,),
    )
    cells_path = write_identity_coherence_cell_evidence_tsv(
        tmp_path / "cells.tsv",
        (record,),
    )

    assert _read_header(requests_path) == IDENTITY_COHERENCE_REQUEST_COLUMNS
    assert _read_header(decisions_path) == IDENTITY_COHERENCE_DECISION_COLUMNS
    assert _read_header(cells_path) == IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS
    assert _read_tsv(requests_path)[0]["request_id"] == "REQ-1"
    assert _read_tsv(decisions_path)[0]["decision_id"] == "DEC-1"
    assert _read_tsv(cells_path)[0]["sample_id"] == "RAW-2"


def test_controls_writer_writes_header_when_rows_are_empty(tmp_path):
    path = write_identity_coherence_controls_tsv(tmp_path / "controls.tsv", ())

    text = path.read_text(encoding="utf-8")

    assert text.startswith("control_id\tcontrol_type\tcontrol_name")
    assert _read_header(path) == IDENTITY_COHERENCE_CONTROL_COLUMNS
    assert len(text.splitlines()) == 1


def test_cell_writer_rejects_seed_sample_cell(tmp_path):
    record = _record()
    seed_cell = replace(record.row_result.cells[0], sample_id="RAW-1")
    bad_row = replace(record.row_result, cells=(seed_cell,))
    bad_record = replace(record, row_result=bad_row)

    with pytest.raises(ValueError, match="seed sample"):
        write_identity_coherence_cell_evidence_tsv(
            tmp_path / "cells.tsv",
            (bad_record,),
        )


def test_cell_writer_rejects_unresolved_seed_sample(tmp_path):
    record = _record()
    bad_seed_gate = replace(
        record.seed_gate,
        resolved_request=replace(
            record.seed_gate.resolved_request,
            seed_sample=None,
        ),
    )
    bad_decision = replace(record.row_result.decision, seed_sample=None)
    bad_row = replace(record.row_result, decision=bad_decision)
    bad_record = replace(record, seed_gate=bad_seed_gate, row_result=bad_row)

    with pytest.raises(ValueError, match="resolved seed_sample"):
        write_identity_coherence_cell_evidence_tsv(
            tmp_path / "cells.tsv",
            (bad_record,),
        )


def test_writers_reject_mismatched_record_join_keys(tmp_path):
    record = _record()
    bad_decision = replace(record.row_result.decision, decision_id="OTHER")
    bad_row = replace(record.row_result, decision=bad_decision)
    bad_record = replace(record, row_result=bad_row)

    with pytest.raises(ValueError, match="decision_id"):
        write_identity_coherence_decisions_tsv(
            tmp_path / "decisions.tsv",
            (bad_record,),
        )


def test_writers_reject_forbidden_evidence_used(tmp_path):
    record = _record()
    bad_decision = replace(
        record.row_result.decision,
        forbidden_evidence_used=True,
    )
    bad_row = replace(record.row_result, decision=bad_decision)
    bad_record = replace(record, row_result=bad_row)

    with pytest.raises(ValueError, match="forbidden_evidence_used"):
        write_identity_coherence_decisions_tsv(
            tmp_path / "decisions.tsv",
            (bad_record,),
        )


def test_summary_renderer_reports_required_sections_and_counts():
    markdown = render_identity_coherence_summary(
        (_record(),),
        context=IdentityCoherenceOutputContext(
            command="identity-coherence --inline",
            mode="inline_pre_backfill",
            input_source="pre_backfill_ownership",
            input_hashes=(("ownership.pkl", "sha256:def"),),
            control_manifest_path="not_provided",
            projected_85raw_identity_request_count=255,
        ),
        control_rows=(),
    )

    headings = (
        "# Untargeted Identity Coherence Summary",
        "## Run Context",
        "## Input Hashes",
        "## Request Status Counts",
        "## Evidence Firewall",
        "## Seed Gate Counts",
        "## Decision Counts",
        "## Tier Support Counts",
        "## RT-Only Candidate Counts",
        "## Shape And Width Review",
        "## Per-Sample Evidence Coverage",
        "## Infrastructure And Data Quality",
        "## Threshold Count And Fraction Summaries",
        "## Weak Basis Counts",
        "## Controls Pass-Through",
        "## Cost Counters",
        "## Writer Contract Checks",
    )
    for heading in headings:
        assert heading in markdown
    _assert_in_order(markdown, headings)
    assert "| `promotion_used_forbidden_evidence` | `false` |" in markdown
    assert "| `would_primary_provisional_identity_family_support` | 1 |" in markdown
    assert "| raw_xic_request_count | not_assessed |" in markdown
    assert "| xic_point_count | not_assessed |" in markdown
    assert "| projected_85raw_identity_request_count | 255 |" in markdown


def test_summary_renderer_reports_control_rows_without_interpreting_them():
    markdown = render_identity_coherence_summary(
        (_record(),),
        context=IdentityCoherenceOutputContext(
            command="pytest",
            mode="inline_pre_backfill",
            input_source="synthetic",
            control_manifest_path="controls.tsv",
        ),
        control_rows=(
            {
                "control_id": "CTRL-1",
                "control_type": "positive_identity_control",
                "control_status": "assessed",
                "control_pass": True,
            },
        ),
    )

    assert "| control_manifest_path | `controls.tsv` |" in markdown
    assert "| `positive_identity_control` | 1 |" in markdown
    assert "| `true` | 1 |" in markdown
    assert "reported only, not evaluated by this writer slice" in markdown


def test_write_identity_coherence_outputs_writes_all_frozen_paths(tmp_path):
    paths = write_identity_coherence_outputs(
        tmp_path,
        (_record(),),
        context=IdentityCoherenceOutputContext(
            command="pytest",
            mode="inline_pre_backfill",
            input_source="synthetic",
            input_hashes=(("synthetic.tsv", "sha256:abc"),),
            projected_85raw_identity_request_count=255,
        ),
        control_rows=(),
    )

    assert isinstance(paths, IdentityCoherenceOutputPaths)
    assert paths.requests_tsv.name == "untargeted_identity_coherence_requests.tsv"
    assert paths.decisions_tsv.name == "untargeted_identity_coherence_decisions.tsv"
    assert paths.cell_evidence_tsv.name == (
        "untargeted_identity_coherence_cell_evidence.tsv"
    )
    assert paths.controls_tsv.name == "untargeted_identity_coherence_controls.tsv"
    assert paths.summary_md.name == "untargeted_identity_coherence_summary.md"
    assert paths.requests_tsv.is_file()
    assert paths.decisions_tsv.is_file()
    assert paths.cell_evidence_tsv.is_file()
    assert paths.controls_tsv.is_file()
    assert paths.summary_md.is_file()


def test_summary_renderer_rejects_mixed_threshold_rows():
    record = _record()
    bad_decision = replace(
        record.row_result.decision,
        min_total_coherent_samples=4,
    )
    bad_row = replace(record.row_result, decision=bad_decision)
    bad_record = replace(record, row_result=bad_row)

    with pytest.raises(ValueError, match="min_total_coherent_samples"):
        render_identity_coherence_summary(
            (record, bad_record),
            context=IdentityCoherenceOutputContext(
                command="pytest",
                mode="inline_pre_backfill",
                input_source="synthetic",
            ),
            control_rows=(),
        )
