import csv
import json
from dataclasses import replace
from pathlib import Path

from tests.alignment.identity_coherence.output_fixtures import output_record
from xic_extractor.alignment.identity_coherence.models import (
    CellEvidenceResult,
    IdentityDecisionSummary,
)
from xic_extractor.alignment.identity_coherence.schema import (
    CellIdentityBasis,
    IdentityDecision,
    SeedGateClass,
    SeedRejectReason,
)

FIXTURE_DIR = (
    Path(__file__).parents[2]
    / "fixtures"
    / "identity_coherence"
    / "firewall_spoof"
)


def _jsonl_rows(path: Path) -> tuple[dict[str, object], ...]:
    with path.open("r", encoding="utf-8") as handle:
        return tuple(json.loads(line) for line in handle if line.strip())


def _tsv_rows(path: Path) -> tuple[dict[str, str], ...]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return tuple(csv.DictReader(handle, dialect="excel-tab"))


def _record_from_fixture(row: dict[str, object], *, spoofed: bool):
    record = output_record()
    decision = _decision_from_fixture(
        record.row_result.decision,
        row,
        forbidden_evidence_seen=spoofed,
    )
    cells = _cells_from_fixture(
        record.row_result.cells,
        row,
        forbidden_evidence_seen=spoofed,
    )
    seed_gate = replace(
        record.seed_gate,
        seed_gate_class=SeedGateClass(str(row["seed_gate_class"])),
        seed_reject_reason=(
            SeedRejectReason.LOW_MS1_SCAN_SUPPORT
            if row["seed_gate_class"] == "review_only_seed_gate_failed"
            else None
        ),
        resolved_request=replace(
            record.seed_gate.resolved_request,
            decision_id=str(row["decision_id"]),
            seed_candidate_id=str(row["seed_candidate_id"]),
            seed_sample=str(row["seed_sample"]),
        ),
    )
    return replace(
        record,
        seed_gate=seed_gate,
        row_result=replace(record.row_result, cells=cells, decision=decision),
    )


def _decision_from_fixture(
    decision: IdentityDecisionSummary,
    row: dict[str, object],
    *,
    forbidden_evidence_seen: bool,
) -> IdentityDecisionSummary:
    return replace(
        decision,
        decision_id=str(row["decision_id"]),
        identity_family_id=str(row["identity_family_id"]),
        seed_candidate_id=str(row["seed_candidate_id"]),
        seed_sample=str(row["seed_sample"]),
        seed_gate_class=SeedGateClass(str(row["seed_gate_class"])),
        decision=IdentityDecision(str(row["expected_decision"])),
        total_coherent_sample_count=int(row["total_coherent_sample_count"]),
        non_seed_coherent_sample_count=int(row["non_seed_coherent_sample_count"]),
        tier12_non_seed_identity_sample_count=int(
            row["tier12_non_seed_identity_sample_count"]
        ),
        forbidden_evidence_seen=forbidden_evidence_seen,
        forbidden_evidence_used=False,
    )


def _cells_from_fixture(
    cells: tuple[CellEvidenceResult, ...],
    row: dict[str, object],
    *,
    forbidden_evidence_seen: bool,
) -> tuple[CellEvidenceResult, ...]:
    if row["cell_identity_basis"] == "none":
        return ()
    return tuple(
        replace(
            cell,
            decision_id=str(row["decision_id"]),
            identity_family_id=str(row["identity_family_id"]),
            cell_identity_basis=CellIdentityBasis(str(row["cell_identity_basis"])),
            forbidden_evidence_seen=forbidden_evidence_seen,
        )
        for cell in cells
    )


def _decision_projection(record) -> dict[str, object]:
    decision = record.row_result.decision
    basis = (
        "none"
        if not record.row_result.cells
        else str(record.row_result.cells[0].cell_identity_basis.value)
    )
    return {
        "decision_id": decision.decision_id,
        "decision": decision.decision.value,
        "total_coherent_sample_count": decision.total_coherent_sample_count,
        "non_seed_coherent_sample_count": decision.non_seed_coherent_sample_count,
        "tier12_non_seed_identity_sample_count": (
            decision.tier12_non_seed_identity_sample_count
        ),
        "seed_gate_class": decision.seed_gate_class.value,
        "cell_identity_basis": basis,
        "forbidden_evidence_seen": decision.forbidden_evidence_seen,
        "forbidden_evidence_used": decision.forbidden_evidence_used,
    }


def _apply_firewall_spoof_fixture(
    baseline_records: tuple[object, ...],
    spoof_rows: tuple[dict[str, str], ...],
) -> tuple[object, ...]:
    """Test adapter for the firewall A/B fixture contract."""

    required_spoof_columns = {
        "decision_id",
        "production_status",
        "include_in_primary_matrix",
        "backfill_status",
        "workbook_area",
    }
    for row in spoof_rows:
        missing = required_spoof_columns.difference(row)
        assert not missing
        assert row["production_status"]
        assert row["include_in_primary_matrix"]
        assert row["backfill_status"]
        assert row["workbook_area"]

    spoofed_decision_ids = {row["decision_id"] for row in spoof_rows}
    updated = []
    for record in baseline_records:
        seen = record.row_result.decision.decision_id in spoofed_decision_ids
        decision = replace(
            record.row_result.decision,
            forbidden_evidence_seen=seen,
            forbidden_evidence_used=False,
        )
        cells = tuple(
            replace(cell, forbidden_evidence_seen=seen)
            for cell in record.row_result.cells
        )
        updated.append(
            replace(
                record,
                row_result=replace(record.row_result, decision=decision, cells=cells),
            )
        )
    return tuple(updated)


def test_firewall_spoof_fixture_files_exist() -> None:
    assert (FIXTURE_DIR / "pre_backfill_owner_state.jsonl").is_file()
    assert (FIXTURE_DIR / "post_backfill_spoof.tsv").is_file()
    assert (FIXTURE_DIR / "expected_decisions.tsv").is_file()


def test_firewall_spoof_marks_seen_without_changing_identity_decisions() -> None:
    baseline_rows = _jsonl_rows(FIXTURE_DIR / "pre_backfill_owner_state.jsonl")
    spoof_rows = _tsv_rows(FIXTURE_DIR / "post_backfill_spoof.tsv")
    expected_rows = _tsv_rows(FIXTURE_DIR / "expected_decisions.tsv")

    baseline_records = tuple(
        _record_from_fixture(row, spoofed=False) for row in baseline_rows
    )
    spoof_records = _apply_firewall_spoof_fixture(baseline_records, spoof_rows)

    baseline_projection = [_decision_projection(record) for record in baseline_records]
    spoof_projection = [_decision_projection(record) for record in spoof_records]

    for before, after in zip(baseline_projection, spoof_projection, strict=True):
        assert before["decision_id"] == after["decision_id"]
        assert before["decision"] == after["decision"]
        assert before["total_coherent_sample_count"] == (
            after["total_coherent_sample_count"]
        )
        assert before["non_seed_coherent_sample_count"] == (
            after["non_seed_coherent_sample_count"]
        )
        assert before["tier12_non_seed_identity_sample_count"] == (
            after["tier12_non_seed_identity_sample_count"]
        )
        assert before["seed_gate_class"] == after["seed_gate_class"]
        assert before["cell_identity_basis"] == after["cell_identity_basis"]
        assert before["forbidden_evidence_used"] is False
        assert after["forbidden_evidence_used"] is False
        assert after["forbidden_evidence_seen"] is True

    expected_by_id = {row["decision_id"]: row for row in expected_rows}
    for projected in spoof_projection:
        expected = expected_by_id[projected["decision_id"]]
        assert projected["decision"] == expected["decision"]
        assert str(projected["total_coherent_sample_count"]) == (
            expected["total_coherent_sample_count"]
        )
        assert str(projected["non_seed_coherent_sample_count"]) == (
            expected["non_seed_coherent_sample_count"]
        )
        assert str(projected["tier12_non_seed_identity_sample_count"]) == (
            expected["tier12_non_seed_identity_sample_count"]
        )
        assert projected["seed_gate_class"] == expected["seed_gate_class"]
        assert projected["cell_identity_basis"] == expected["cell_identity_basis"]
        assert str(projected["forbidden_evidence_seen"]).lower() == (
            expected["forbidden_evidence_seen"]
        )
