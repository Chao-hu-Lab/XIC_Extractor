from dataclasses import dataclass
from pathlib import Path

from xic_extractor.alignment.identity_coherence.models import (
    CandidateIdentityMatch,
    SeedCandidateEvidence,
    SeedGateConfig,
    SeedGateResult,
)
from xic_extractor.alignment.identity_coherence.request_builder import (
    build_identity_coherence_request,
)
from xic_extractor.alignment.identity_coherence.schema import (
    IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS,
    IDENTITY_COHERENCE_CONTROL_COLUMNS,
    IDENTITY_COHERENCE_DECISION_COLUMNS,
    IDENTITY_COHERENCE_REQUEST_COLUMNS,
    EvidenceStage,
    RequestCandidateIdentityStatus,
    RequestIdentityCompletenessStatus,
    SeedGateClass,
    SeedRejectReason,
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


def test_identity_coherence_facade_exports_stable_contract():
    import xic_extractor.alignment.identity_coherence as identity_coherence

    assert identity_coherence.FragmentIdentity is not None
    assert identity_coherence.CidNeutralLossConstraint is not None
    assert identity_coherence.IdentityCoherenceRequest is not None
    assert identity_coherence.build_identity_coherence_request is not None
    assert identity_coherence.format_fragment_tags is not None
    assert identity_coherence.IDENTITY_COHERENCE_REQUEST_COLUMNS


@dataclass
class CandidateLike:
    candidate_id: str = "CAND-1"
    sample_name: str = "RAW-1"
    precursor_mz: float = 500.0
    product_mz: float = 384.0
    observed_neutral_loss_da: float = 116.0
    matched_tag_names: object = ("MeR", "dR")
    neutral_loss_tag: str = "dR"


def _request():
    return build_identity_coherence_request(
        CandidateLike(),
        request_id="REQ-1",
        decision_id="DEC-1",
        precursor_tolerance_ppm=10.0,
        product_tolerance_ppm=10.0,
        cid_observed_loss_tolerance_ppm=10.0,
        fragment_profile_id="profile-a",
    )


def test_seed_gate_enum_values_are_stable_strings():
    assert {value.value for value in EvidenceStage} == {
        "pre_backfill",
        "backfill_only",
        "post_backfill",
    }
    assert {value.value for value in SeedGateClass} == {
        "coherent_seed",
        "review_only_seed_gate_failed",
        "blocked_seed",
    }
    assert {value.value for value in SeedRejectReason} == {
        "missing_request_identity_constraint",
        "no_quantifiable_owner",
        "missing_discovery_candidate_join",
        "missing_diagnostic_fragment_evidence",
        "ambiguous_owner",
        "duplicate_loser",
        "backfill_only_evidence",
        "nonfinite_peak",
        "seed_rt_outside_owner_peak",
        "low_ms1_scan_support",
        "request_candidate_identity_mismatch",
        "unsupported_fragment_observation_mode",
        "multi_seed_requires_phase2",
    }


def test_seed_gate_models_hold_a_resolved_gate_result():
    evidence = SeedCandidateEvidence(
        candidate_id="CAND-1",
        precursor_mz=500.0,
        product_mz=384.0,
        cid_observed_loss_da=116.0,
        fragment_tags=("MeR", "dR"),
        best_seed_rt=7.83,
        ms1_scan_support_score=0.80,
    )
    match = CandidateIdentityMatch(
        request_candidate_identity_status=RequestCandidateIdentityStatus.MATCH,
        precursor_error_ppm=0.0,
        product_error_ppm=0.0,
        cid_observed_loss_error_ppm=0.0,
        cid_observed_loss_error_da=0.0,
        missing_fields=(),
        mismatch_fields=(),
        fragment_tags_supported=("dR",),
    )

    result = SeedGateResult(
        resolved_request=_request(),
        seed_gate_class=SeedGateClass.COHERENT_SEED,
        seed_reject_reason=None,
        candidate_match=match,
        review_flags=(),
    )

    assert evidence.evidence_stage is EvidenceStage.PRE_BACKFILL
    assert result.seed_gate_class is SeedGateClass.COHERENT_SEED
    assert result.resolved_request.seed_candidate_id == "CAND-1"
    assert SeedGateConfig().min_ms1_scan_support_score == 0.5
