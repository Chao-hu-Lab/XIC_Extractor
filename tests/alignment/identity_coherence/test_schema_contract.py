import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

from xic_extractor.alignment.identity_coherence.models import (
    CandidateIdentityMatch,
    CandidateTrace,
    CellCandidateEvidence,
    CellEvidenceResult,
    EngineeringConfig,
    IdentityCoherenceConfig,
    IdentityDecisionSummary,
    RtCenterResult,
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
    AreaHeightStatus,
    BaselineAuditStatus,
    CellAssessmentStatus,
    CellBlockedReason,
    CellDataQualityReason,
    CellIdentityBasis,
    CellIdentityTier,
    ControlStatus,
    ControlType,
    DecisionReason,
    DecoyGenerationMethod,
    EvidenceStage,
    FragmentMatchStatus,
    FragmentObservationMode,
    IdentityDecision,
    NonRtIdentityResult,
    PositiveControlMappingStatus,
    RequestCandidateIdentityStatus,
    RequestIdentityCompletenessStatus,
    RtCenterDecision,
    RtGateStatus,
    SeedGateClass,
    SeedRejectReason,
    ShapeAuditStatus,
    ShapeReferenceBasis,
    ShapeStatus,
    WeakBasisReason,
    WidthStatus,
)

CONTRACT_PATH = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "superpowers"
    / "specs"
    / "2026-05-22-untargeted-identity-coherence-implementation-contract.md"
)
IDENTITY_COHERENCE_PACKAGE = "xic_extractor.alignment.identity_coherence"
FORBIDDEN_IDENTITY_COHERENCE_SURFACES = ("controls", "output")


def _is_forbidden_identity_coherence_module(module_name: str) -> bool:
    for surface in FORBIDDEN_IDENTITY_COHERENCE_SURFACES:
        forbidden_module = f"{IDENTITY_COHERENCE_PACKAGE}.{surface}"
        if module_name == forbidden_module or module_name.startswith(
            f"{forbidden_module}."
        ):
            return True
    return False


def _is_relative_forbidden_surface(module_name: str) -> bool:
    surface = module_name.split(".", maxsplit=1)[0]
    return surface in FORBIDDEN_IDENTITY_COHERENCE_SURFACES


def _forbidden_identity_coherence_imports(source: str) -> list[str]:
    tree = ast.parse(source)
    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if _is_forbidden_identity_coherence_module(alias.name):
                    violations.append(f"line {node.lineno}: import {alias.name}")
            continue

        if not isinstance(node, ast.ImportFrom):
            continue

        module_name = node.module or ""
        if node.level:
            if module_name and _is_relative_forbidden_surface(module_name):
                violations.append(f"line {node.lineno}: from .{module_name} import")
            elif not module_name:
                for alias in node.names:
                    if alias.name in FORBIDDEN_IDENTITY_COHERENCE_SURFACES:
                        violations.append(
                            f"line {node.lineno}: from . import {alias.name}"
                        )
            continue

        if _is_forbidden_identity_coherence_module(module_name):
            violations.append(f"line {node.lineno}: from {module_name} import")
        elif module_name == IDENTITY_COHERENCE_PACKAGE:
            for alias in node.names:
                if alias.name in FORBIDDEN_IDENTITY_COHERENCE_SURFACES:
                    violations.append(
                        f"line {node.lineno}: from {module_name} import {alias.name}"
                    )

    return violations


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

    schema_enums = (
        IdentityDecision,
        WeakBasisReason,
        RtCenterDecision,
        CellAssessmentStatus,
        CellIdentityTier,
        CellIdentityBasis,
        FragmentMatchStatus,
        RtGateStatus,
        NonRtIdentityResult,
        ShapeStatus,
        ShapeReferenceBasis,
        ShapeAuditStatus,
        WidthStatus,
        BaselineAuditStatus,
        AreaHeightStatus,
        CellBlockedReason,
        CellDataQualityReason,
        DecisionReason,
    )
    for schema_enum in schema_enums:
        assert getattr(identity_coherence, schema_enum.__name__) is schema_enum
        assert schema_enum.__name__ in identity_coherence.__all__

    assert identity_coherence.FragmentIdentity is not None
    assert identity_coherence.CidNeutralLossConstraint is not None
    assert identity_coherence.IdentityCoherenceRequest is not None
    assert identity_coherence.CandidateIdentityMatch is not None
    assert identity_coherence.SeedCandidateEvidence is not None
    assert identity_coherence.SeedGateConfig is not None
    assert identity_coherence.SeedGateResult is not None
    assert identity_coherence.EvidenceStage is not None
    assert identity_coherence.SeedGateClass is not None
    assert identity_coherence.SeedRejectReason is not None
    assert identity_coherence.build_identity_coherence_request is not None
    assert identity_coherence.build_seed_candidate_evidence is not None
    assert identity_coherence.match_request_to_candidate is not None
    assert identity_coherence.evaluate_seed_gate is not None
    assert identity_coherence.format_fragment_tags is not None
    assert identity_coherence.has_fragment_tags is not None
    assert identity_coherence.normalize_fragment_tags is not None
    assert identity_coherence.IDENTITY_COHERENCE_REQUEST_COLUMNS
    assert identity_coherence.CellCandidateEvidence is not None
    assert identity_coherence.CellEvidenceResult is not None
    assert identity_coherence.CandidateTrace is not None
    assert identity_coherence.ShapeConfig is not None
    assert identity_coherence.WidthConfig is not None
    assert identity_coherence.ShapeReferenceResult is not None
    assert identity_coherence.ShapeComparisonResult is not None
    assert identity_coherence.PrototypeWidthResult is not None
    assert identity_coherence.WidthAssessmentResult is not None
    assert identity_coherence.IdentityCoherenceConfig is not None
    assert identity_coherence.IdentityCoherenceRowResult is not None
    assert identity_coherence.IdentityDecisionSummary is not None
    assert identity_coherence.RtCenterResult is not None
    assert identity_coherence.estimate_rt_center is not None
    assert identity_coherence.estimate_prototype_width is not None
    assert identity_coherence.assess_width_against_prototype is not None
    assert identity_coherence.estimate_shape_reference is not None
    assert identity_coherence.create_seed_shape_reference is not None
    assert identity_coherence.compare_shape_to_reference is not None
    assert identity_coherence.normalize_trace_for_shape is not None
    assert identity_coherence.evaluate_cell_evidence is not None
    assert identity_coherence.evaluate_identity_coherence_row is not None
    assert identity_coherence.select_cell_evidence_for_sample is not None
    assert identity_coherence.summarize_identity_decision is not None
    assert identity_coherence.match_identity_constraints_to_candidate is not None
    assert "match_identity_constraints_to_candidate" in identity_coherence.__all__


def test_identity_coherence_facade_exports_output_writer_surface():
    import xic_extractor.alignment.identity_coherence as identity_coherence

    assert identity_coherence.IdentityCoherenceOutputContext is not None
    assert identity_coherence.IdentityCoherenceOutputPaths is not None
    assert identity_coherence.IdentityCoherenceOutputRecord is not None
    assert identity_coherence.project_request_row is not None
    assert identity_coherence.project_decision_row is not None
    assert identity_coherence.project_cell_evidence_row is not None
    assert identity_coherence.project_control_row is not None
    assert identity_coherence.render_identity_coherence_summary is not None
    assert identity_coherence.write_identity_coherence_outputs is not None
    assert identity_coherence.write_identity_coherence_requests_tsv is not None
    assert identity_coherence.write_identity_coherence_decisions_tsv is not None
    assert identity_coherence.write_identity_coherence_cell_evidence_tsv is not None
    assert identity_coherence.write_identity_coherence_controls_tsv is not None


def test_identity_coherence_facade_exports_controls_surface():
    import xic_extractor.alignment.identity_coherence as identity_coherence

    exported_names = (
        "ControlType",
        "ControlStatus",
        "DecoyGenerationMethod",
        "PositiveControlMappingStatus",
        "IdentityControlEvaluationResult",
        "IdentityControlManifestEntry",
        "IdentityControlsConfig",
        "IdentityDecoySource",
        "read_identity_controls_manifest",
        "read_identity_controls_manifest_tsv",
        "evaluate_positive_control",
        "evaluate_identity_decoy",
        "evaluate_identity_controls",
    )

    for name in exported_names:
        assert getattr(identity_coherence, name) is not None
        assert name in identity_coherence.__all__

    assert identity_coherence.ControlType is ControlType
    assert identity_coherence.ControlStatus is ControlStatus
    assert identity_coherence.DecoyGenerationMethod is DecoyGenerationMethod
    assert (
        identity_coherence.PositiveControlMappingStatus
        is PositiveControlMappingStatus
    )


def test_identity_coherence_facade_exports_process_payload_surface():
    import xic_extractor.alignment.identity_coherence as identity_coherence

    assert identity_coherence.EngineeringConfig is not None
    assert identity_coherence.IdentityCoherenceResult is not None
    assert identity_coherence.IdentityCoherenceTraceRequest is not None
    assert identity_coherence.IdentityCoherenceTraceResult is not None
    assert "EngineeringConfig" in identity_coherence.__all__
    assert "IdentityCoherenceResult" in identity_coherence.__all__
    assert "IdentityCoherenceTraceRequest" in identity_coherence.__all__
    assert "IdentityCoherenceTraceResult" in identity_coherence.__all__


def test_identity_coherence_process_payload_stays_no_raw_boundary() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    source = (
        repo_root / "xic_extractor/alignment/identity_coherence/process_payload.py"
    ).read_text(encoding="utf-8")
    forbidden_snippets = (
        "raw_reader",
        "ms1_index_source",
        "owner_backfill",
        "alignment.pipeline",
        "scripts.run_alignment",
        "source_for_owner_backfill_backend",
        "xic_extractor.output",
        "workbook",
        "report",
    )

    # Syntactic-only firewall: tighten to an AST import scan once this module
    # grows beyond payload dataclasses and the no-RAW smoke worker.
    for snippet in forbidden_snippets:
        assert snippet not in source


def test_domain_modules_do_not_import_controls_or_output_surfaces():
    package_root = (
        Path(__file__).resolve().parents[3]
        / "xic_extractor"
        / "alignment"
        / "identity_coherence"
    )
    domain_modules = (
        "candidate_matcher.py",
        "cell_evidence.py",
        "decision.py",
        "models.py",
        "request_builder.py",
        "row_evaluator.py",
        "rt_center.py",
        "schema.py",
        "seed_gate.py",
        "shape.py",
        "tags.py",
        "width.py",
    )
    violations = []
    for module_name in domain_modules:
        source = (package_root / module_name).read_text(encoding="utf-8")
        for violation in _forbidden_identity_coherence_imports(source):
            violations.append(f"{module_name}: {violation}")

    assert violations == []


def test_forbidden_import_scan_ignores_comments_docstrings_and_plain_strings():
    source = '''
"""Mention xic_extractor.alignment.identity_coherence.output in docs."""
# from xic_extractor.alignment.identity_coherence import output
TEXT = "identity_coherence.output"
'''

    assert _forbidden_identity_coherence_imports(source) == []


@pytest.mark.parametrize(
    "source",
    (
        "import xic_extractor.alignment.identity_coherence.controls\n",
        "import xic_extractor.alignment.identity_coherence.output\n",
        "from xic_extractor.alignment.identity_coherence.controls import X\n",
        "from xic_extractor.alignment.identity_coherence.output import X\n",
        "from xic_extractor.alignment.identity_coherence import controls\n",
        "from xic_extractor.alignment.identity_coherence import output\n",
        "from . import controls\n",
        "from . import output\n",
        "from .controls import X\n",
        "from .output import X\n",
    ),
)
def test_forbidden_import_scan_detects_controls_and_output_surfaces(source):
    assert _forbidden_identity_coherence_imports(source)


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


def test_cell_evidence_enum_values_are_stable_strings():
    assert {value.value for value in CellAssessmentStatus} == {
        "assessed",
        "blocked",
        "data_quality_reject",
        "not_assessed",
    }
    assert {value.value for value in CellIdentityTier} == {
        "tier1",
        "tier2",
        "tier3",
        "rt_only",
        "blocked",
        "data_quality",
    }
    assert {value.value for value in CellIdentityBasis} == {
        "rt_fragment_support",
        "rt_shape_similarity",
        "rt_prototype_width",
        "none",
    }
    assert {value.value for value in FragmentMatchStatus} == {
        "pass",
        "fail",
        "ambiguous",
        "not_assessed",
    }
    assert {value.value for value in RtGateStatus} == {
        "pass",
        "fail",
        "not_assessed",
    }
    assert {value.value for value in ShapeStatus} == {
        "pass",
        "fail",
        "low_points",
        "zero_signal",
        "not_assessed",
    }
    assert {value.value for value in ShapeReferenceBasis} == {
        "tier1_supported_medoid",
        "morphology_rt_medoid",
        "seed_fallback",
        "none",
    }
    assert {value.value for value in ShapeAuditStatus} == {
        "pass",
        "fail",
        "shoulder",
        "bimodal",
        "coelution",
        "saturated",
        "clipped",
        "unavailable",
        "not_assessed",
    }
    assert {value.value for value in WidthStatus} == {
        "pass",
        "fail",
        "not_assessed",
    }
    assert {value.value for value in BaselineAuditStatus} == {
        "pass",
        "fail",
        "unavailable",
        "not_assessed",
    }
    assert {value.value for value in AreaHeightStatus} == {
        "pass",
        "fail",
        "not_assessed",
    }
    assert {value.value for value in NonRtIdentityResult} == {
        "pass",
        "fail",
        "not_assessed",
        "blocked",
    }
    assert {value.value for value in CellBlockedReason} == {
        "backfill_only_evidence",
    }
    assert {value.value for value in CellDataQualityReason} == {
        "invalid_peak_morphology",
    }
    assert {value.value for value in DecisionReason} == {
        "tier1_support",
        "tier2_shape_support",
    }


def test_decision_and_center_enum_values_are_stable_strings():
    assert {value.value for value in IdentityDecision} == {
        "would_primary_provisional_identity_family_support",
        "review_only_seed_gate_failed",
        "review_only_rt_only_support",
        "review_only_insufficient_support",
        "review_only_center_unstable",
        "review_only_weak_basis_tier3_only",
        "review_only_weak_basis_single_tier12_plus_tier3",
        "review_only_multi_seed_requires_phase2",
        "blocked_infrastructure",
    }
    assert {value.value for value in WeakBasisReason} == {
        "none",
        "tier3_only",
        "single_tier12_plus_tier3",
        "seed_shape_fallback_only",
        "rt_only",
    }
    assert {value.value for value in RtCenterDecision} == {
        "seed_anchored",
        "recentered_stable",
        "center_unstable_review_only",
    }


def test_identity_coherence_config_defaults_match_v04_review_values():
    config = IdentityCoherenceConfig()

    assert config.promotion.min_total_coherent_samples == 3
    assert config.promotion.min_non_seed_coherent_samples == 2
    assert config.promotion.min_non_seed_tier12_identity_samples == 2
    assert config.rt.max_rt_sec == 180.0
    assert config.rt.preferred_rt_sec == 60.0
    assert config.rt.seed_center_candidate_sec == 30.0
    assert config.rt.max_center_drift_sec == 30.0
    assert config.shape.min_points == 7
    assert config.shape.resample_points == 25
    assert config.shape.min_cosine == 0.85
    assert config.shape.prototype_min_candidates == 3
    assert config.shape.prototype_min_non_seed_candidates == 2
    assert config.shape.allow_seed_shape_fallback is True
    assert config.shape.allow_morphology_rt_medoid is True
    assert config.width.prototype_min_candidates == 3
    assert config.width.min_ratio == 0.50
    assert config.width.max_ratio == 2.00
    assert isinstance(config.engineering, EngineeringConfig)
    assert config.engineering.max_infrastructure_blocked_fraction == 0.05
    assert config.engineering.max_projected_85raw_identity_xic_requests is None


@pytest.mark.parametrize(
    ("engineering_config_kwargs", "message"),
    (
        (
            {"max_infrastructure_blocked_fraction": -0.01},
            "max_infrastructure_blocked_fraction must be nonnegative",
        ),
        (
            {"max_infrastructure_blocked_fraction": 1.01},
            "max_infrastructure_blocked_fraction must be <= 1",
        ),
        (
            {"max_projected_85raw_identity_xic_requests": True},
            "max_projected_85raw_identity_xic_requests must be nonnegative",
        ),
        (
            {"max_projected_85raw_identity_xic_requests": -1},
            "max_projected_85raw_identity_xic_requests must be nonnegative",
        ),
    ),
)
def test_engineering_config_rejects_invalid_bounds(
    engineering_config_kwargs,
    message,
):
    with pytest.raises(ValueError, match=message):
        EngineeringConfig(**engineering_config_kwargs)


def test_candidate_trace_is_nested_domain_model_not_flat_schema_columns():
    trace = CandidateTrace(
        rt_min=(7.75, 7.80, 7.85),
        intensity=(1.0, 5.0, 1.0),
        shape_audit_status=ShapeAuditStatus.PASS,
    )

    candidate = CellCandidateEvidence(
        sample_id="S2",
        candidate_evidence=SeedCandidateEvidence(
            candidate_id="C2",
            precursor_mz=500.0,
            product_mz=384.0,
            cid_observed_loss_da=116.0,
            fragment_tags=("MeR", "dR"),
            best_seed_rt=7.80,
            ms1_scan_support_score=0.75,
        ),
        apex_rt=7.80,
        peak_start_rt=7.75,
        peak_end_rt=7.85,
        area=10.0,
        height=5.0,
        point_count=3,
        trace=trace,
    )

    assert candidate.trace is trace
    assert "rt_min" not in IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS
    assert "intensity" not in IDENTITY_COHERENCE_CELL_EVIDENCE_COLUMNS


def test_candidate_trace_rejects_mismatched_rt_and_intensity_lengths():
    with pytest.raises(ValueError, match="rt_min and intensity"):
        CandidateTrace(
            rt_min=(7.75, 7.80, 7.85),
            intensity=(1.0, 5.0),
            shape_audit_status=ShapeAuditStatus.PASS,
        )


def test_cell_and_decision_models_hold_tier1_slice_state():
    candidate = SeedCandidateEvidence(
        candidate_id="CAND-2",
        precursor_mz=500.0,
        product_mz=384.0,
        cid_observed_loss_da=116.0,
        fragment_tags=("MeR", "dR"),
        best_seed_rt=7.90,
        ms1_scan_support_score=0.75,
    )
    cell_candidate = CellCandidateEvidence(
        sample_id="RAW-2",
        candidate_evidence=candidate,
        apex_rt=7.90,
        peak_start_rt=7.80,
        peak_end_rt=8.00,
        area=1000.0,
        height=200.0,
        point_count=9,
    )
    center = RtCenterResult(
        center_rt_min=7.85,
        center_rt_sec=471.0,
        center_decision=RtCenterDecision.RECENTERED_STABLE,
        center_candidate_count=2,
        center_drift_sec=1.2,
    )
    cell = CellEvidenceResult(
        decision_id="DEC-1",
        identity_family_id="IDF-1",
        sample_id=cell_candidate.sample_id,
        candidate_id=cell_candidate.candidate_evidence.candidate_id,
        cell_assessment_status=CellAssessmentStatus.ASSESSED,
        cell_identity_tier=CellIdentityTier.TIER1,
        cell_identity_basis=CellIdentityBasis.RT_FRAGMENT_SUPPORT,
        fragment_observation_mode=FragmentObservationMode.CID_NEUTRAL_LOSS,
        fragment_match_status=FragmentMatchStatus.PASS,
        fragment_tags_supported=("MeR", "dR"),
        rt_delta_center_sec=3.0,
        rt_gate_status=RtGateStatus.PASS,
        shape_status=ShapeStatus.NOT_ASSESSED,
        shape_similarity_cosine=None,
        shape_reference_basis=ShapeReferenceBasis.NONE,
        shape_reference_candidate_id="",
        shape_fallback_used=False,
        shape_audit_status=ShapeAuditStatus.NOT_ASSESSED,
        width_status=WidthStatus.NOT_ASSESSED,
        width_ratio_to_prototype=None,
        baseline_audit_status=BaselineAuditStatus.NOT_ASSESSED,
        area_height_status=AreaHeightStatus.PASS,
        non_rt_identity_result=NonRtIdentityResult.PASS,
        coherent_count_contribution=True,
        tier12_count_contribution=True,
        blocked_reason="",
        data_quality_reason="",
        forbidden_evidence_seen=False,
    )
    summary = IdentityDecisionSummary(
        decision_id="DEC-1",
        identity_family_id="IDF-1",
        seed_candidate_id="CAND-1",
        seed_sample="RAW-1",
        seed_gate_class=SeedGateClass.COHERENT_SEED,
        request_identity_completeness_status=(
            RequestIdentityCompletenessStatus.COMPLETE
        ),
        request_candidate_identity_status=RequestCandidateIdentityStatus.MATCH,
        decision=IdentityDecision.WOULD_PRIMARY,
        decision_reason=DecisionReason.TIER1_SUPPORT.value,
        total_coherent_sample_count=3,
        non_seed_coherent_sample_count=2,
        tier12_non_seed_identity_sample_count=2,
        tier1_fragment_confirmed_sample_count=2,
        tier2_shape_supported_sample_count=0,
        tier2_seed_shape_fallback_sample_count=0,
        tier3_width_only_sample_count=0,
        min_total_coherent_samples=3,
        min_non_seed_coherent_samples=2,
        min_non_seed_tier12_identity_samples=2,
        weak_basis_reason=WeakBasisReason.NONE,
        shape_reference_basis=ShapeReferenceBasis.NONE,
        shape_reference_candidate_id="",
        prototype_width_sec=None,
        center_rt_source="recentered_stable",
        center=center,
        coherent_fraction=0.375,
        infrastructure_blocked_sample_count=0,
        data_quality_reject_sample_count=0,
        forbidden_evidence_seen=False,
        forbidden_evidence_used=False,
    )

    assert cell.coherent_count_contribution is True
    assert summary.total_coherent_sample_count == 3
