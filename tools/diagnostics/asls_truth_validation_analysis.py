"""Gate decision logic for the P2c AsLS truth-validation diagnostic."""

from __future__ import annotations

from tools.diagnostics.asls_truth_validation_models import (
    GATE_C1B_PLAN,
    GATE_NO_GO,
    GATE_REQUIRES_RETIREMENT_PREREQS,
    GATE_REQUIRES_TIER_C,
    GATE_RETIREMENT,
    INCONCLUSIVE_FIXTURE_GAP,
    INCONCLUSIVE_INVALID_INPUT,
)


INCONCLUSIVE_TIER_B_NOT_PASS = "INCONCLUSIVE_TIER_B_NOT_PASS"

_VALID_DECISION_TARGETS = {"c1b-plan", "linear-edge-retirement"}
_INCONCLUSIVE_PREFIX = "INCONCLUSIVE"
_PASS = "PASS"
_FAIL = "FAIL"
_VALID = "VALID"
_NOT_APPLICABLE_WITH_EXCLUSION = "NOT_APPLICABLE_WITH_EXCLUSION"
_STRESS_REQUIRES_TIER_C = "STRESS_REQUIRES_TIER_C"
_C1B_RELEVANCE = "C1B_RELEVANCE"


def decide_gate(
    *,
    decision_target: str,
    tier_a_status: str,
    tier_b1_status: str,
    tier_b2_status: str = "NOT_RUN",
    b1_hard_blockers: tuple[str, ...] = (),
    b2_retirement_blockers: tuple[str, ...] = (),
    coverage_status: str,
    tier_c_status: str,
    tier_c_nonblank_status: str,
    tier_c_nonblank_decision_scope: str = _C1B_RELEVANCE,
    blank_safety_status: str,
    waiver_state: str,
    retirement_prereq_status: str,
) -> str:
    """Return the deletion-safe P2c gate decision."""

    if decision_target not in _VALID_DECISION_TARGETS:
        return INCONCLUSIVE_INVALID_INPUT

    statuses = [
        tier_a_status,
        tier_b1_status,
        coverage_status,
        tier_c_status,
        tier_c_nonblank_status,
        blank_safety_status,
        waiver_state,
        retirement_prereq_status,
    ]
    if decision_target == "linear-edge-retirement":
        statuses.insert(2, tier_b2_status)
    inconclusive = _first_inconclusive(tuple(statuses))
    if inconclusive:
        return inconclusive

    if tier_a_status != _PASS:
        return GATE_NO_GO
    if coverage_status != _PASS:
        return INCONCLUSIVE_FIXTURE_GAP
    if b1_hard_blockers or tier_b1_status == _FAIL:
        return GATE_NO_GO
    if tier_c_nonblank_status == _FAIL and (
        decision_target == "linear-edge-retirement"
        or tier_c_nonblank_decision_scope == _C1B_RELEVANCE
    ):
        return GATE_NO_GO
    if tier_b1_status != _PASS:
        return INCONCLUSIVE_TIER_B_NOT_PASS

    if decision_target == "linear-edge-retirement":
        if tier_b2_status == _FAIL:
            return GATE_NO_GO
        if tier_b2_status == _STRESS_REQUIRES_TIER_C or b2_retirement_blockers:
            return GATE_REQUIRES_TIER_C
        if tier_b2_status != _PASS:
            return GATE_REQUIRES_TIER_C
        if tier_c_status != _PASS:
            return GATE_REQUIRES_TIER_C
        if tier_c_nonblank_status != _PASS:
            return GATE_REQUIRES_TIER_C
        if blank_safety_status == _FAIL:
            return GATE_NO_GO
        if blank_safety_status not in {_PASS, _NOT_APPLICABLE_WITH_EXCLUSION}:
            return GATE_REQUIRES_TIER_C
        if retirement_prereq_status != _VALID:
            return GATE_REQUIRES_RETIREMENT_PREREQS
        return GATE_RETIREMENT

    return GATE_C1B_PLAN


def exit_code_for_gate(gate_decision: str) -> int:
    if gate_decision == GATE_RETIREMENT:
        return 0
    if gate_decision == GATE_NO_GO:
        return 1
    if gate_decision.startswith(_INCONCLUSIVE_PREFIX):
        return 2
    return 3


def _first_inconclusive(statuses: tuple[str, ...]) -> str:
    if INCONCLUSIVE_INVALID_INPUT in statuses:
        return INCONCLUSIVE_INVALID_INPUT
    for status in statuses:
        if status.startswith(_INCONCLUSIVE_PREFIX):
            return status
    return ""
