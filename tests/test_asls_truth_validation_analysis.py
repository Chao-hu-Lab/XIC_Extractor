from __future__ import annotations

from tools.diagnostics.asls_truth_validation_analysis import (
    INCONCLUSIVE_TIER_B_NOT_PASS,
    decide_gate,
    exit_code_for_gate,
)
from tools.diagnostics.asls_truth_validation_inputs import (
    FAIL,
    NOT_APPLICABLE_WITH_EXCLUSION,
    NOT_PROVIDED,
    NOT_SATISFIED,
    PASS,
    VALID,
)
from tools.diagnostics.asls_truth_validation_models import (
    GATE_C1B_PLAN,
    GATE_NO_GO,
    GATE_REQUIRES_RETIREMENT_PREREQS,
    GATE_REQUIRES_TIER_C,
    GATE_RETIREMENT,
    INCONCLUSIVE_FIXTURE_GAP,
    INCONCLUSIVE_FIXTURE_LOCK_CHANGED,
    INCONCLUSIVE_INVALID_INPUT,
    INCONCLUSIVE_REGENERATE_TIER_A,
)


def test_tier_a_fail_is_no_go() -> None:
    assert _decide(tier_a_status=FAIL) == GATE_NO_GO


def test_tier_a_inconclusive_returns_same_inconclusive_status() -> None:
    assert _decide(tier_a_status=INCONCLUSIVE_REGENERATE_TIER_A) == (
        INCONCLUSIVE_REGENERATE_TIER_A
    )
    assert exit_code_for_gate(INCONCLUSIVE_REGENERATE_TIER_A) == 2


def test_c1b_plan_can_go_with_tier_a_and_b_pass_without_tier_c() -> None:
    result = _decide(decision_target="c1b-plan")

    assert result == GATE_C1B_PLAN
    assert exit_code_for_gate(result) == 3


def test_retirement_requires_tier_c_when_tier_c_is_missing() -> None:
    result = _decide(decision_target="linear-edge-retirement")

    assert result == GATE_REQUIRES_TIER_C
    assert exit_code_for_gate(result) == 3


def test_tier_b_inconclusive_is_not_planning_go() -> None:
    result = _decide(tier_b1_status=INCONCLUSIVE_FIXTURE_LOCK_CHANGED)

    assert result == INCONCLUSIVE_FIXTURE_LOCK_CHANGED
    assert exit_code_for_gate(result) == 2


def test_tier_b_not_provided_is_inconclusive_not_planning_go() -> None:
    result = _decide(tier_b1_status=NOT_PROVIDED)

    assert result == INCONCLUSIVE_TIER_B_NOT_PASS
    assert exit_code_for_gate(result) == 2


def test_valid_tier_c_fail_blocks_before_requires_tier_c() -> None:
    result = _decide(
        decision_target="linear-edge-retirement",
        tier_c_status=FAIL,
        tier_c_nonblank_status=FAIL,
    )

    assert result == GATE_NO_GO
    assert exit_code_for_gate(result) == 1


def test_invalid_optional_evidence_returns_invalid_input() -> None:
    for field in ("tier_c_status", "waiver_state", "retirement_prereq_status"):
        result = _decide(**{field: INCONCLUSIVE_INVALID_INPUT})
        assert result == INCONCLUSIVE_INVALID_INPUT
        assert exit_code_for_gate(result) == 2


def test_valid_waiver_without_nonblank_tier_c_still_requires_tier_c() -> None:
    result = _decide(
        decision_target="linear-edge-retirement",
        waiver_state=VALID,
    )

    assert result == GATE_REQUIRES_TIER_C


def test_blank_only_tier_c_still_requires_nonblank_tier_c() -> None:
    result = _decide(
        decision_target="linear-edge-retirement",
        tier_c_status=PASS,
        tier_c_nonblank_status=NOT_PROVIDED,
        blank_safety_status=PASS,
    )

    assert result == GATE_REQUIRES_TIER_C


def test_nonblank_tier_c_without_blank_safety_requires_tier_c() -> None:
    result = _decide(
        decision_target="linear-edge-retirement",
        tier_c_status=PASS,
        tier_c_nonblank_status=PASS,
        blank_safety_status=NOT_PROVIDED,
    )

    assert result == GATE_REQUIRES_TIER_C


def test_nonblank_tier_c_and_blank_safety_require_retirement_prereqs() -> None:
    result = _decide(
        decision_target="linear-edge-retirement",
        tier_b2_status=PASS,
        tier_c_status=PASS,
        tier_c_nonblank_status=PASS,
        blank_safety_status=NOT_APPLICABLE_WITH_EXCLUSION,
        retirement_prereq_status=NOT_SATISFIED,
    )

    assert result == GATE_REQUIRES_RETIREMENT_PREREQS
    assert exit_code_for_gate(result) == 3


def test_retirement_requires_top_level_tier_c_pass() -> None:
    result = _decide(
        decision_target="linear-edge-retirement",
        tier_c_status=NOT_PROVIDED,
        tier_c_nonblank_status=PASS,
        blank_safety_status=PASS,
        retirement_prereq_status=VALID,
    )

    assert result == GATE_REQUIRES_TIER_C
    assert exit_code_for_gate(result) == 3


def test_full_retirement_evidence_is_only_zero_exit_gate() -> None:
    result = _decide(
        decision_target="linear-edge-retirement",
        tier_b2_status=PASS,
        tier_c_status=PASS,
        tier_c_nonblank_status=PASS,
        blank_safety_status=PASS,
        retirement_prereq_status=VALID,
    )

    assert result == GATE_RETIREMENT
    assert exit_code_for_gate(result) == 0


def test_hard_blockers_are_no_go() -> None:
    result = _decide(b1_hard_blockers=("asls_exceeds_raw_area",))

    assert result == GATE_NO_GO
    assert exit_code_for_gate(result) == 1


def test_b2_retirement_blockers_do_not_block_c1b_plan() -> None:
    result = _decide(
        tier_b2_status="STRESS_REQUIRES_TIER_C",
        b2_retirement_blockers=("blank_false_positive",),
    )

    assert result == GATE_C1B_PLAN
    assert exit_code_for_gate(result) == 3


def test_b2_inconclusive_does_not_block_c1b_plan() -> None:
    result = _decide(tier_b2_status=INCONCLUSIVE_FIXTURE_LOCK_CHANGED)

    assert result == GATE_C1B_PLAN


def test_b2_inconclusive_blocks_retirement_target() -> None:
    result = _decide(
        decision_target="linear-edge-retirement",
        tier_b2_status=INCONCLUSIVE_FIXTURE_LOCK_CHANGED,
    )

    assert result == INCONCLUSIVE_FIXTURE_LOCK_CHANGED
    assert exit_code_for_gate(result) == 2


def test_retirement_scoped_nonblank_fail_does_not_block_c1b_plan() -> None:
    result = _decide(
        tier_c_status=FAIL,
        tier_c_nonblank_status=FAIL,
        tier_c_nonblank_decision_scope="RETIREMENT_ONLY",
    )

    assert result == GATE_C1B_PLAN


def test_fixture_coverage_gap_is_inconclusive() -> None:
    result = _decide(coverage_status=INCONCLUSIVE_FIXTURE_GAP)

    assert result == INCONCLUSIVE_FIXTURE_GAP
    assert exit_code_for_gate(result) == 2


def test_invalid_decision_target_is_invalid_input() -> None:
    assert _decide(decision_target="delete-linear-now") == INCONCLUSIVE_INVALID_INPUT


def test_exit_code_mapping_is_deletion_safe() -> None:
    assert exit_code_for_gate(GATE_RETIREMENT) == 0
    assert exit_code_for_gate(GATE_NO_GO) == 1
    assert exit_code_for_gate(GATE_REQUIRES_TIER_C) == 3
    assert exit_code_for_gate(GATE_C1B_PLAN) == 3
    assert exit_code_for_gate(INCONCLUSIVE_FIXTURE_GAP) == 2


def _decide(**overrides: object) -> str:
    kwargs = {
        "decision_target": "c1b-plan",
        "tier_a_status": PASS,
        "tier_b1_status": PASS,
        "tier_b2_status": "NOT_RUN",
        "b1_hard_blockers": (),
        "b2_retirement_blockers": (),
        "coverage_status": PASS,
        "tier_c_status": NOT_PROVIDED,
        "tier_c_nonblank_status": NOT_PROVIDED,
        "tier_c_nonblank_decision_scope": "C1B_RELEVANCE",
        "blank_safety_status": NOT_PROVIDED,
        "waiver_state": NOT_PROVIDED,
        "retirement_prereq_status": NOT_PROVIDED,
    }
    kwargs.update(overrides)
    return decide_gate(**kwargs)
