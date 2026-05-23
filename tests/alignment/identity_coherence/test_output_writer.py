import csv
from dataclasses import replace
from pathlib import Path

import pytest

from tests.alignment.identity_coherence.output_fixtures import output_record
from xic_extractor.alignment.identity_coherence.output import (
    IdentityCoherenceOutputRecord,
    write_identity_coherence_cell_evidence_tsv,
    write_identity_coherence_controls_tsv,
    write_identity_coherence_decisions_tsv,
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
