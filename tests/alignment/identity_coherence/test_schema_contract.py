from pathlib import Path

from xic_extractor.alignment.identity_coherence.schema import (
    IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS,
    IDENTITY_COHERENCE_CONTROL_COLUMNS,
    IDENTITY_COHERENCE_DECISION_COLUMNS,
    IDENTITY_COHERENCE_REQUEST_COLUMNS,
    RequestCandidateIdentityStatus,
    RequestIdentityCompletenessStatus,
)


CONTRACT_PATH = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "superpowers"
    / "specs"
    / "2026-05-22-untargeted-identity-coherence-implementation-contract.md"
)


def _schema_block(name: str) -> tuple[str, ...]:
    start = f"<!-- schema:{name}:start -->"
    end = f"<!-- schema:{name}:end -->"
    in_block = False
    values: list[str] = []
    for line in CONTRACT_PATH.read_text(encoding="utf-8").splitlines():
        if line == start:
            in_block = True
            continue
        if line == end:
            break
        if in_block and line:
            values.append(line)
    assert values, f"schema marker block not found: {name}"
    return tuple(values)


def test_schema_constants_match_contract_marker_blocks():
    assert IDENTITY_COHERENCE_REQUEST_COLUMNS == _schema_block(
        "identity_coherence_requests.tsv"
    )
    assert IDENTITY_COHERENCE_DECISION_COLUMNS == _schema_block(
        "identity_coherence_decisions.tsv"
    )
    assert IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS == _schema_block(
        "identity_coherence_cell_evidence.tsv"
    )
    assert IDENTITY_COHERENCE_CONTROL_COLUMNS == _schema_block(
        "identity_coherence_controls.tsv"
    )


def test_schema_constants_have_no_duplicates():
    for columns in (
        IDENTITY_COHERENCE_REQUEST_COLUMNS,
        IDENTITY_COHERENCE_DECISION_COLUMNS,
        IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS,
        IDENTITY_COHERENCE_CONTROL_COLUMNS,
    ):
        assert len(columns) == len(set(columns))


def test_request_status_enum_values_are_stable_strings():
    assert {value.value for value in RequestIdentityCompletenessStatus} == {
        "complete",
        "missing_fragment_observation_mode",
        "missing_precursor_mz",
        "missing_product_mz",
        "missing_fragment_tags",
        "missing_tolerance",
        "missing_mode_specific_constraint",
    }
    assert {value.value for value in RequestCandidateIdentityStatus} == {
        "not_assessed",
        "match",
        "missing_discovery_candidate_join",
        "missing_diagnostic_fragment_evidence",
        "request_candidate_identity_mismatch",
        "unsupported_fragment_observation_mode",
    }
