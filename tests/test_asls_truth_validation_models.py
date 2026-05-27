from __future__ import annotations

import json
from pathlib import Path

from tools.diagnostics.asls_truth_validation_models import (
    GATE_C1B_PLAN,
    GATE_NO_GO,
    GATE_REQUIRES_RETIREMENT_PREREQS,
    GATE_REQUIRES_TIER_C,
    GATE_RETIREMENT,
    INCONCLUSIVE_FIXTURE_LOCK_CHANGED,
    INCONCLUSIVE_INVALID_INPUT,
    INCONCLUSIVE_MISSING_P2B_85RAW_ACCEPTANCE,
    INCONCLUSIVE_REGENERATE_TIER_A,
    ROW_FIELDS,
    SUMMARY_FIELDS,
    TruthValidationOutputs,
    load_json_object,
)


def test_gate_decisions_are_distinct() -> None:
    assert GATE_C1B_PLAN == "GO_FOR_C1B_PLAN_SYNTHETIC_ONLY"
    assert GATE_RETIREMENT == "GO_FOR_LINEAR_EDGE_RETIREMENT"
    assert GATE_REQUIRES_TIER_C == "REQUIRES_TIER_C"
    assert GATE_REQUIRES_RETIREMENT_PREREQS == "REQUIRES_RETIREMENT_PREREQS"
    assert INCONCLUSIVE_INVALID_INPUT == "INCONCLUSIVE_INVALID_INPUT"
    assert INCONCLUSIVE_REGENERATE_TIER_A == "INCONCLUSIVE_REGENERATE_TIER_A"
    assert INCONCLUSIVE_FIXTURE_LOCK_CHANGED == "INCONCLUSIVE_FIXTURE_LOCK_CHANGED"
    assert (
        INCONCLUSIVE_MISSING_P2B_85RAW_ACCEPTANCE
        == "INCONCLUSIVE_MISSING_P2B_85RAW_ACCEPTANCE"
    )
    assert (
        len(
            {
                GATE_C1B_PLAN,
                GATE_RETIREMENT,
                GATE_REQUIRES_TIER_C,
                GATE_REQUIRES_RETIREMENT_PREREQS,
                GATE_NO_GO,
                INCONCLUSIVE_INVALID_INPUT,
                INCONCLUSIVE_REGENERATE_TIER_A,
                INCONCLUSIVE_FIXTURE_LOCK_CHANGED,
                INCONCLUSIVE_MISSING_P2B_85RAW_ACCEPTANCE,
            }
        )
        == 9
    )


def test_summary_schema_has_prereq_and_optional_evidence_fields() -> None:
    for field in (
        "decision_target",
        "fixture_lock_hash",
        "tier_a_generated_by_git_sha",
        "tier_a_current_code_compatibility_status",
        "p2b_85raw_acceptance_hash",
        "tier_c_status",
        "tier_c_nonblank_status",
        "blank_safety_status",
        "methodology_waiver_hash",
        "waiver_valid",
        "retirement_prereq_status",
        "c1a_status",
        "c5_status",
        "rollback_column_status",
    ):
        assert field in SUMMARY_FIELDS


def test_row_schema_has_error_and_blank_fields() -> None:
    for field in (
        "asls_error_over_linear_error",
        "blank_false_positive",
        "blank_not_quantifiable",
        "failure_reasons",
    ):
        assert field in ROW_FIELDS


def test_outputs_include_conditional_evidence_paths(tmp_path: Path) -> None:
    outputs = TruthValidationOutputs.from_output_dir(tmp_path)
    assert outputs.fixture_lock_json.name == "asls_truth_validation_fixture_lock.json"
    assert (
        outputs.p2b_85raw_acceptance_json.name
        == "asls_truth_validation_p2b_85raw_acceptance_manifest.json"
    )
    assert (
        outputs.tier_c_evidence_json.name
        == "asls_truth_validation_tier_c_evidence.json"
    )
    assert (
        outputs.methodology_waiver_json.name
        == "asls_truth_validation_methodology_waiver.json"
    )
    assert (
        outputs.retirement_prereq_json.name
        == "asls_truth_validation_retirement_prerequisites.json"
    )


def test_load_json_object_rejects_non_object(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(["bad"]), encoding="utf-8")

    try:
        load_json_object(path)
    except ValueError as exc:
        assert "must be a JSON object" in str(exc)
    else:
        raise AssertionError("expected ValueError")
