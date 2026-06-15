from __future__ import annotations

import csv
import hashlib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from xic_extractor.tabular_io import read_delimited_rows, write_tsv

REVIEW_ACTION_SCHEMA_VERSION = "review_action_v1"
REVIEW_ACTION_APPLICATION_PLAN_SCHEMA_VERSION = "review_action_application_plan_v1"
REVIEW_ACTION_EXPECTED_DIFF_SCHEMA_VERSION = "review_action_expected_diff_v1"
REVIEW_ACTION_APPLY_READINESS_SCHEMA_VERSION = "review_action_apply_readiness_v1"
REVIEW_ACTION_APPLY_CHANGESET_SCHEMA_VERSION = "review_action_apply_changeset_v1"
REVIEW_ACTION_COLUMNS: tuple[str, ...] = (
    "schema_version",
    "sample_name",
    "target_label",
    "action_type",
    "candidate_id",
    "boundary_id",
    "rt_left_min",
    "rt_apex_min",
    "rt_right_min",
    "comment",
    "reviewer",
    "reviewed_at",
    "expected_diff_required",
)
ReviewActionType = Literal[
    "accept_current",
    "mark_unresolved",
    "reject_current",
    "select_candidate",
    "set_manual_boundary",
]
REVIEW_ACTION_TYPES: frozenset[str] = frozenset(
    {
        "accept_current",
        "mark_unresolved",
        "reject_current",
        "select_candidate",
        "set_manual_boundary",
    }
)
PRODUCT_MUTATING_REVIEW_ACTIONS: frozenset[str] = frozenset(
    {
        "reject_current",
        "select_candidate",
        "set_manual_boundary",
    }
)
TARGETED_REVIEW_STATE_COLUMNS: tuple[str, ...] = (
    "Product State",
    "Counted Detection",
    "Review State",
)
REVIEW_ACTION_APPLICATION_PLAN_COLUMNS: tuple[str, ...] = (
    "schema_version",
    "sample_name",
    "target_label",
    "action_type",
    "application_status",
    "product_mutating",
    "current_product_state",
    "current_counted_detection",
    "current_review_state",
    "candidate_id",
    "boundary_id",
    "rt_left_min",
    "rt_apex_min",
    "rt_right_min",
    "expected_diff_required",
    "expected_diff_status",
    "reason",
    "reviewer",
    "reviewed_at",
    "comment",
)
REVIEW_ACTION_EXPECTED_DIFF_COLUMNS: tuple[str, ...] = (
    "schema_version",
    "stable_row_id",
    "sample_name",
    "target_label",
    "action_type",
    "candidate_id",
    "boundary_id",
    "rt_left_min",
    "rt_apex_min",
    "rt_right_min",
    "expected_public_outputs_touched",
    "expected_matrix_value_impact",
    "evidence_sources",
    "evidence_summary",
    "validation_tier",
    "reviewer_verdict",
    "final_label",
    "reviewer",
    "reviewed_at",
    "comment",
    "approval_notes",
)
REVIEW_ACTION_APPLY_READINESS_COLUMNS: tuple[str, ...] = (
    "schema_version",
    "sample_name",
    "target_label",
    "action_type",
    "apply_readiness_status",
    "product_mutating",
    "current_product_state",
    "current_counted_detection",
    "current_review_state",
    "expected_diff_stable_row_id",
    "expected_diff_approval_status",
    "expected_diff_validation_tier",
    "expected_matrix_value_impact",
    "expected_public_outputs_touched",
    "evidence_sources",
    "evidence_summary",
    "candidate_id",
    "boundary_id",
    "rt_left_min",
    "rt_apex_min",
    "rt_right_min",
    "reason",
    "reviewer",
    "reviewed_at",
    "comment",
    "approval_notes",
)
REVIEW_ACTION_APPLY_CHANGESET_COLUMNS: tuple[str, ...] = (
    "schema_version",
    "sample_name",
    "target_label",
    "action_type",
    "changeset_status",
    "apply_readiness_status",
    "operation",
    "product_mutating",
    "output_scope",
    "requires_expected_diff_approval",
    "expected_diff_stable_row_id",
    "expected_diff_validation_tier",
    "expected_matrix_value_impact",
    "expected_public_outputs_touched",
    "evidence_sources",
    "evidence_summary",
    "candidate_id",
    "boundary_id",
    "rt_left_min",
    "rt_apex_min",
    "rt_right_min",
    "proposed_product_state",
    "proposed_counted_detection",
    "proposed_review_state",
    "requires_area_recompute",
    "requires_candidate_sidecar",
    "reason",
    "reviewer",
    "reviewed_at",
    "comment",
    "approval_notes",
)
REVIEW_ACTION_EXPECTED_DIFF_FINAL_LABELS = frozenset(
    {"expected_diff", "blocked_diff", "inconclusive"}
)
REVIEW_ACTION_EXPECTED_DIFF_REVIEWER_VERDICTS = frozenset(
    {"approved", "blocked", "inconclusive"}
)
REVIEW_ACTION_EXPECTED_DIFF_VALIDATION_TIERS = frozenset(
    {
        "synthetic_fixture",
        "targeted_benchmark",
        "8raw",
        "manual_eic_ms2_review",
        "not_validated",
    }
)
REVIEW_ACTION_EXPECTED_DIFF_MATRIX_VALUE_IMPACTS = frozenset(
    {"none", "area_value_changed", "presence_changed", "not_assessed"}
)
_EXPECTED_DIFF_OUTPUTS_BY_ACTION: dict[str, tuple[str, ...]] = {
    "reject_current": ("targeted_long_csv", "workbook", "final_matrix"),
    "select_candidate": ("targeted_long_csv", "workbook", "final_matrix"),
    "set_manual_boundary": ("targeted_long_csv", "workbook", "final_matrix"),
}
_EXPECTED_DIFF_MATRIX_IMPACT_BY_ACTION: dict[str, str] = {
    "reject_current": "presence_changed",
    "select_candidate": "area_value_changed",
    "set_manual_boundary": "area_value_changed",
}


@dataclass(frozen=True)
class ReviewAction:
    sample_name: str
    target_label: str
    action_type: ReviewActionType
    candidate_id: str = ""
    boundary_id: str = ""
    rt_left_min: float | None = None
    rt_apex_min: float | None = None
    rt_right_min: float | None = None
    comment: str = ""
    reviewer: str = ""
    reviewed_at: str = ""
    expected_diff_required: bool = False

    @property
    def product_mutating(self) -> bool:
        return self.action_type in PRODUCT_MUTATING_REVIEW_ACTIONS


@dataclass(frozen=True)
class ReviewActionTargetState:
    sample_name: str
    target_label: str
    product_state: str = ""
    counted_detection: str = ""
    review_state: str = ""


@dataclass(frozen=True)
class ReviewActionApplication:
    action: ReviewAction
    application_status: str
    expected_diff_status: str
    reason: str
    target_state: ReviewActionTargetState | None = None

    @property
    def product_mutating(self) -> bool:
        return self.action.product_mutating


@dataclass(frozen=True)
class ReviewActionExpectedDiffTemplate:
    application: ReviewActionApplication
    stable_row_id: str
    expected_public_outputs_touched: tuple[str, ...]
    expected_matrix_value_impact: str


@dataclass(frozen=True)
class ReviewActionExpectedDiffApproval:
    stable_row_id: str
    sample_name: str
    target_label: str
    action_type: ReviewActionType
    candidate_id: str
    boundary_id: str
    rt_left_min: float | None
    rt_apex_min: float | None
    rt_right_min: float | None
    expected_public_outputs_touched: tuple[str, ...]
    expected_matrix_value_impact: str
    evidence_sources: tuple[str, ...]
    evidence_summary: str
    validation_tier: str
    reviewer_verdict: str
    final_label: str
    reviewer: str
    reviewed_at: str
    comment: str
    approval_notes: str


@dataclass(frozen=True)
class ReviewActionApplyReadiness:
    application: ReviewActionApplication
    apply_readiness_status: str
    reason: str
    expected_diff_stable_row_id: str = ""
    expected_diff_approval: ReviewActionExpectedDiffApproval | None = None


@dataclass(frozen=True)
class ReviewActionApplyReadinessPlan:
    rows: tuple[ReviewActionApplyReadiness, ...]
    unused_expected_diff_approvals: tuple[ReviewActionExpectedDiffApproval, ...]


@dataclass(frozen=True)
class ReviewActionApplyChangeset:
    readiness: ReviewActionApplyReadiness
    changeset_status: str
    operation: str
    output_scope: tuple[str, ...]
    proposed_product_state: str = ""
    proposed_counted_detection: str = ""
    proposed_review_state: str = ""
    requires_area_recompute: bool = False
    requires_candidate_sidecar: bool = False
    reason: str = ""


@dataclass(frozen=True)
class ReviewActionApplyChangesetPlan:
    rows: tuple[ReviewActionApplyChangeset, ...]


class ReviewActionError(ValueError):
    """Raised when a review action import cannot be trusted."""


def load_review_actions(path: Path) -> tuple[ReviewAction, ...]:
    return parse_review_actions(
        _read_review_action_rows(path),
        source=str(path),
    )


def load_review_action_target_states(path: Path) -> tuple[ReviewActionTargetState, ...]:
    if not path.is_file():
        raise ReviewActionError(f"{path}: targeted output file not found")
    delimiter = "\t" if path.suffix.lower() in {".tsv", ".txt"} else ","
    try:
        rows = read_delimited_rows(
            path,
            required_columns=("SampleName", "Target"),
            delimiter=delimiter,
            encoding="utf-8-sig",
        )
    except ValueError as exc:
        raise ReviewActionError(str(exc)) from exc
    return tuple(_target_state_from_row(row) for row in rows)


def plan_review_action_applications(
    actions: Sequence[ReviewAction],
    target_states: Sequence[ReviewActionTargetState],
) -> tuple[ReviewActionApplication, ...]:
    state_by_key = _index_target_states(target_states)
    action_counts_by_key: dict[tuple[str, str], int] = {}
    for action in actions:
        key = _action_key(action)
        action_counts_by_key[key] = action_counts_by_key.get(key, 0) + 1

    applications: list[ReviewActionApplication] = []
    for action in actions:
        key = _action_key(action)
        target_state = state_by_key.get(key)
        if target_state is None:
            applications.append(
                ReviewActionApplication(
                    action=action,
                    application_status="blocked",
                    expected_diff_status=_expected_diff_status(action),
                    reason="target_row_missing",
                    target_state=None,
                )
            )
            continue
        if action_counts_by_key[key] > 1:
            applications.append(
                ReviewActionApplication(
                    action=action,
                    application_status="blocked",
                    expected_diff_status=_expected_diff_status(action),
                    reason="multiple_actions_for_target",
                    target_state=target_state,
                )
            )
            continue
        applications.append(_plan_single_application(action, target_state))
    return tuple(applications)


def write_review_action_application_plan(
    path: Path,
    applications: Sequence[ReviewActionApplication],
) -> None:
    write_tsv(
        path,
        [review_action_application_to_row(application) for application in applications],
        REVIEW_ACTION_APPLICATION_PLAN_COLUMNS,
        lineterminator="\n",
    )


def plan_review_action_expected_diff_templates(
    applications: Sequence[ReviewActionApplication],
) -> tuple[ReviewActionExpectedDiffTemplate, ...]:
    templates: list[ReviewActionExpectedDiffTemplate] = []
    for application in applications:
        if application.application_status != "blocked_expected_diff_review":
            continue
        action = application.action
        templates.append(
            ReviewActionExpectedDiffTemplate(
                application=application,
                stable_row_id=review_action_expected_diff_stable_row_id(action),
                expected_public_outputs_touched=_expected_diff_outputs(action),
                expected_matrix_value_impact=_expected_diff_matrix_impact(action),
            )
        )
    return tuple(templates)


def write_review_action_expected_diff_template(
    path: Path,
    templates: Sequence[ReviewActionExpectedDiffTemplate],
) -> None:
    write_tsv(
        path,
        [
            review_action_expected_diff_template_to_row(template)
            for template in templates
        ],
        REVIEW_ACTION_EXPECTED_DIFF_COLUMNS,
        lineterminator="\n",
    )


def load_review_action_expected_diff_approvals(
    path: Path,
) -> dict[str, ReviewActionExpectedDiffApproval]:
    if not path.is_file():
        raise ReviewActionError(f"{path}: review action expected-diff file not found")
    try:
        rows = read_delimited_rows(
            path,
            required_columns=REVIEW_ACTION_EXPECTED_DIFF_COLUMNS,
            delimiter="\t",
            encoding="utf-8-sig",
        )
    except ValueError as exc:
        raise ReviewActionError(str(exc)) from exc

    approvals: dict[str, ReviewActionExpectedDiffApproval] = {}
    for row_number, row in enumerate(rows, start=2):
        approval = _parse_expected_diff_approval_row(
            row,
            source=str(path),
            row_number=row_number,
        )
        if approval.stable_row_id in approvals:
            raise ReviewActionError(
                f"{path}:{row_number}: duplicate stable_row_id "
                f"{approval.stable_row_id!r}"
            )
        approvals[approval.stable_row_id] = approval
    return approvals


def plan_review_action_apply_readiness(
    applications: Sequence[ReviewActionApplication],
    expected_diff_approvals: Mapping[str, ReviewActionExpectedDiffApproval],
) -> ReviewActionApplyReadinessPlan:
    rows: list[ReviewActionApplyReadiness] = []
    used_approval_ids: set[str] = set()
    for application in applications:
        if application.application_status == "blocked_expected_diff_review":
            stable_row_id = review_action_expected_diff_stable_row_id(
                application.action
            )
            approval = expected_diff_approvals.get(stable_row_id)
            if approval is not None:
                used_approval_ids.add(stable_row_id)
                rows.append(
                    ReviewActionApplyReadiness(
                        application=application,
                        apply_readiness_status="ready_expected_diff_approved",
                        reason="approved_expected_diff_available",
                        expected_diff_stable_row_id=stable_row_id,
                        expected_diff_approval=approval,
                    )
                )
                continue
            rows.append(
                ReviewActionApplyReadiness(
                    application=application,
                    apply_readiness_status="blocked_expected_diff_missing",
                    reason="approved_expected_diff_required",
                    expected_diff_stable_row_id=stable_row_id,
                )
            )
            continue
        if application.application_status == "planned_no_output_change":
            rows.append(
                ReviewActionApplyReadiness(
                    application=application,
                    apply_readiness_status="ready_no_output_change",
                    reason="accept_current_has_no_product_mutation",
                )
            )
            continue
        if application.application_status == "planned_review_state_only":
            rows.append(
                ReviewActionApplyReadiness(
                    application=application,
                    apply_readiness_status="blocked_review_state_apply_not_implemented",
                    reason="review_state_write_contract_missing",
                )
            )
            continue
        rows.append(
            ReviewActionApplyReadiness(
                application=application,
                apply_readiness_status="blocked_application_plan",
                reason=application.reason,
            )
        )
    unused = tuple(
        approval
        for stable_row_id, approval in sorted(expected_diff_approvals.items())
        if stable_row_id not in used_approval_ids
    )
    return ReviewActionApplyReadinessPlan(
        rows=tuple(rows),
        unused_expected_diff_approvals=unused,
    )


def write_review_action_apply_readiness_plan(
    path: Path,
    plan: ReviewActionApplyReadinessPlan,
) -> None:
    write_tsv(
        path,
        [review_action_apply_readiness_to_row(row) for row in plan.rows],
        REVIEW_ACTION_APPLY_READINESS_COLUMNS,
        lineterminator="\n",
    )


def plan_review_action_apply_changesets(
    readiness_plan: ReviewActionApplyReadinessPlan,
) -> ReviewActionApplyChangesetPlan:
    return ReviewActionApplyChangesetPlan(
        rows=tuple(
            _changeset_from_readiness(readiness)
            for readiness in readiness_plan.rows
        )
    )


def write_review_action_apply_changeset_plan(
    path: Path,
    plan: ReviewActionApplyChangesetPlan,
) -> None:
    write_tsv(
        path,
        [review_action_apply_changeset_to_row(row) for row in plan.rows],
        REVIEW_ACTION_APPLY_CHANGESET_COLUMNS,
        lineterminator="\n",
    )


def parse_review_actions(
    rows: Iterable[Mapping[str, object]],
    *,
    source: str = "<memory>",
) -> tuple[ReviewAction, ...]:
    parsed: list[ReviewAction] = []
    for index, row in enumerate(rows, start=2):
        normalized = _normalize_row(row)
        if not any(normalized.values()):
            continue
        parsed.append(_parse_action_row(normalized, source=source, row_number=index))
    return tuple(parsed)


def _target_state_from_row(row: Mapping[str, str]) -> ReviewActionTargetState:
    return ReviewActionTargetState(
        sample_name=_clean_text(row.get("SampleName", "")),
        target_label=_clean_text(row.get("Target", "")),
        product_state=_clean_text(row.get("Product State", "")),
        counted_detection=_clean_text(row.get("Counted Detection", "")),
        review_state=_clean_text(row.get("Review State", "")),
    )


def _index_target_states(
    target_states: Sequence[ReviewActionTargetState],
) -> dict[tuple[str, str], ReviewActionTargetState]:
    indexed: dict[tuple[str, str], ReviewActionTargetState] = {}
    for target_state in target_states:
        key = (target_state.sample_name, target_state.target_label)
        if key in indexed:
            sample_name, target_label = key
            raise ReviewActionError(
                "targeted output contains duplicate review target rows: "
                f"sample_name={sample_name!r}, target_label={target_label!r}"
            )
        indexed[key] = target_state
    return indexed


def _action_key(action: ReviewAction) -> tuple[str, str]:
    return (action.sample_name, action.target_label)


def _plan_single_application(
    action: ReviewAction,
    target_state: ReviewActionTargetState,
) -> ReviewActionApplication:
    if action.action_type == "accept_current":
        return ReviewActionApplication(
            action=action,
            application_status="planned_no_output_change",
            expected_diff_status="not_required",
            reason="accept_current_records_review_only",
            target_state=target_state,
        )
    if action.action_type == "mark_unresolved":
        return ReviewActionApplication(
            action=action,
            application_status="planned_review_state_only",
            expected_diff_status="not_required",
            reason="mark_unresolved_requires_audit_before_product_write",
            target_state=target_state,
        )
    return ReviewActionApplication(
        action=action,
        application_status="blocked_expected_diff_review",
        expected_diff_status="required_before_apply",
        reason=f"{action.action_type}_requires_reintegration_slice",
        target_state=target_state,
    )


def _expected_diff_status(action: ReviewAction) -> str:
    if action.product_mutating:
        return "required_before_apply"
    return "not_required"


def _expected_diff_outputs(action: ReviewAction) -> tuple[str, ...]:
    return _EXPECTED_DIFF_OUTPUTS_BY_ACTION[action.action_type]


def _expected_diff_matrix_impact(action: ReviewAction) -> str:
    return _EXPECTED_DIFF_MATRIX_IMPACT_BY_ACTION[action.action_type]


def review_action_expected_diff_stable_row_id(action: ReviewAction) -> str:
    digest_source = "|".join(
        (
            action.sample_name,
            action.target_label,
            action.action_type,
            action.candidate_id,
            action.boundary_id,
            _stable_float(action.rt_left_min),
            _stable_float(action.rt_apex_min),
            _stable_float(action.rt_right_min),
        )
    )
    digest = hashlib.sha256(digest_source.encode("utf-8")).hexdigest()[:16]
    return f"review_action_expected_diff:{digest}"


def _read_review_action_rows(path: Path) -> list[Mapping[str, object]]:
    if not path.is_file():
        raise ReviewActionError(f"{path}: review action file not found")
    delimiter = "\t" if path.suffix.lower() in {".tsv", ".txt"} else ","
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if reader.fieldnames is None:
            raise ReviewActionError(f"{path}: missing review action header")
        missing = [
            header
            for header in REVIEW_ACTION_COLUMNS
            if header not in reader.fieldnames
        ]
        if missing:
            raise ReviewActionError(
                f"{path}: missing review action columns: {', '.join(missing)}"
            )
        return list(reader)


def _parse_action_row(
    row: Mapping[str, str],
    *,
    source: str,
    row_number: int,
) -> ReviewAction:
    schema_version = row["schema_version"]
    if schema_version != REVIEW_ACTION_SCHEMA_VERSION:
        raise ReviewActionError(
            f"{source}:{row_number}: unsupported schema_version {schema_version!r}"
        )
    sample_name = _required_text(row, "sample_name", source, row_number)
    target_label = _required_text(row, "target_label", source, row_number)
    action_type = _required_text(row, "action_type", source, row_number)
    if action_type not in REVIEW_ACTION_TYPES:
        raise ReviewActionError(
            f"{source}:{row_number}: unsupported action_type {action_type!r}"
        )
    candidate_id = row["candidate_id"]
    boundary_id = row["boundary_id"]
    rt_left_min = _optional_float(row["rt_left_min"], "rt_left_min", source, row_number)
    rt_apex_min = _optional_float(row["rt_apex_min"], "rt_apex_min", source, row_number)
    rt_right_min = _optional_float(
        row["rt_right_min"],
        "rt_right_min",
        source,
        row_number,
    )
    expected_diff_required = _parse_bool(
        row["expected_diff_required"],
        "expected_diff_required",
        source,
        row_number,
    )

    _validate_action_requirements(
        action_type,
        candidate_id=candidate_id,
        rt_left_min=rt_left_min,
        rt_apex_min=rt_apex_min,
        rt_right_min=rt_right_min,
        comment=row["comment"],
        expected_diff_required=expected_diff_required,
        source=source,
        row_number=row_number,
    )
    return ReviewAction(
        sample_name=sample_name,
        target_label=target_label,
        action_type=action_type,  # type: ignore[arg-type]
        candidate_id=candidate_id,
        boundary_id=boundary_id,
        rt_left_min=rt_left_min,
        rt_apex_min=rt_apex_min,
        rt_right_min=rt_right_min,
        comment=row["comment"],
        reviewer=row["reviewer"],
        reviewed_at=row["reviewed_at"],
        expected_diff_required=expected_diff_required,
    )


def _parse_expected_diff_approval_row(
    row: Mapping[str, str],
    *,
    source: str,
    row_number: int,
) -> ReviewActionExpectedDiffApproval:
    schema_version = row["schema_version"]
    if schema_version != REVIEW_ACTION_EXPECTED_DIFF_SCHEMA_VERSION:
        raise ReviewActionError(
            f"{source}:{row_number}: unsupported schema_version {schema_version!r}"
        )

    stable_row_id = _required_text(row, "stable_row_id", source, row_number)
    action_type = _required_text(row, "action_type", source, row_number)
    if action_type not in PRODUCT_MUTATING_REVIEW_ACTIONS:
        raise ReviewActionError(
            f"{source}:{row_number}: expected-diff approvals only support "
            "product-mutating review actions"
        )
    sample_name = _required_text(row, "sample_name", source, row_number)
    target_label = _required_text(row, "target_label", source, row_number)
    candidate_id = row["candidate_id"]
    boundary_id = row["boundary_id"]
    rt_left_min = _optional_float(row["rt_left_min"], "rt_left_min", source, row_number)
    rt_apex_min = _optional_float(row["rt_apex_min"], "rt_apex_min", source, row_number)
    rt_right_min = _optional_float(
        row["rt_right_min"],
        "rt_right_min",
        source,
        row_number,
    )
    expected_public_outputs_touched = _split_multi(
        _required_text(
            row,
            "expected_public_outputs_touched",
            source,
            row_number,
        )
    )
    expected_matrix_value_impact = _required_enum(
        row,
        "expected_matrix_value_impact",
        REVIEW_ACTION_EXPECTED_DIFF_MATRIX_VALUE_IMPACTS,
        source,
        row_number,
    )
    evidence_sources = _split_multi(
        _required_text(row, "evidence_sources", source, row_number)
    )
    evidence_summary = _required_text(row, "evidence_summary", source, row_number)
    validation_tier = _required_enum(
        row,
        "validation_tier",
        REVIEW_ACTION_EXPECTED_DIFF_VALIDATION_TIERS,
        source,
        row_number,
    )
    reviewer_verdict = _required_enum(
        row,
        "reviewer_verdict",
        REVIEW_ACTION_EXPECTED_DIFF_REVIEWER_VERDICTS,
        source,
        row_number,
    )
    final_label = _required_enum(
        row,
        "final_label",
        REVIEW_ACTION_EXPECTED_DIFF_FINAL_LABELS,
        source,
        row_number,
    )
    reviewer = _required_text(row, "reviewer", source, row_number)
    reviewed_at = _required_text(row, "reviewed_at", source, row_number)
    comment = row["comment"]

    action = ReviewAction(
        sample_name=sample_name,
        target_label=target_label,
        action_type=cast(ReviewActionType, action_type),
        candidate_id=candidate_id,
        boundary_id=boundary_id,
        rt_left_min=rt_left_min,
        rt_apex_min=rt_apex_min,
        rt_right_min=rt_right_min,
        comment=comment,
        reviewer=reviewer,
        reviewed_at=reviewed_at,
        expected_diff_required=True,
    )
    _validate_action_requirements(
        action_type,
        candidate_id=candidate_id,
        rt_left_min=rt_left_min,
        rt_apex_min=rt_apex_min,
        rt_right_min=rt_right_min,
        comment=comment,
        expected_diff_required=True,
        source=source,
        row_number=row_number,
    )
    expected_stable_row_id = review_action_expected_diff_stable_row_id(action)
    if stable_row_id != expected_stable_row_id:
        raise ReviewActionError(
            f"{source}:{row_number}: stable_row_id does not match review action "
            "identity"
        )
    _validate_approved_expected_diff_row(
        source,
        row_number,
        final_label=final_label,
        reviewer_verdict=reviewer_verdict,
        validation_tier=validation_tier,
        expected_public_outputs_touched=expected_public_outputs_touched,
        expected_matrix_value_impact=expected_matrix_value_impact,
        evidence_sources=evidence_sources,
        evidence_summary=evidence_summary,
    )
    return ReviewActionExpectedDiffApproval(
        stable_row_id=stable_row_id,
        sample_name=sample_name,
        target_label=target_label,
        action_type=cast(ReviewActionType, action_type),
        candidate_id=candidate_id,
        boundary_id=boundary_id,
        rt_left_min=rt_left_min,
        rt_apex_min=rt_apex_min,
        rt_right_min=rt_right_min,
        expected_public_outputs_touched=expected_public_outputs_touched,
        expected_matrix_value_impact=expected_matrix_value_impact,
        evidence_sources=evidence_sources,
        evidence_summary=evidence_summary,
        validation_tier=validation_tier,
        reviewer_verdict=reviewer_verdict,
        final_label=final_label,
        reviewer=reviewer,
        reviewed_at=reviewed_at,
        comment=comment,
        approval_notes=row["approval_notes"],
    )


def _validate_approved_expected_diff_row(
    source: str,
    row_number: int,
    *,
    final_label: str,
    reviewer_verdict: str,
    validation_tier: str,
    expected_public_outputs_touched: tuple[str, ...],
    expected_matrix_value_impact: str,
    evidence_sources: tuple[str, ...],
    evidence_summary: str,
) -> None:
    if final_label != "expected_diff" or reviewer_verdict != "approved":
        raise ReviewActionError(
            f"{source}:{row_number}: expected-diff approval rows must be "
            "approved expected_diff records"
        )
    if validation_tier == "not_validated":
        raise ReviewActionError(
            f"{source}:{row_number}: expected-diff approval is not validated"
        )
    if not evidence_sources or not evidence_summary.strip():
        raise ReviewActionError(
            f"{source}:{row_number}: expected-diff approval lacks evidence"
        )
    if "final_matrix" in expected_public_outputs_touched:
        if expected_matrix_value_impact == "not_assessed":
            raise ReviewActionError(
                f"{source}:{row_number}: matrix-affecting expected diff must "
                "assess matrix impact"
            )
        if validation_tier == "synthetic_fixture":
            raise ReviewActionError(
                f"{source}:{row_number}: matrix-affecting expected diff "
                "requires real-data validation"
            )


def _validate_action_requirements(
    action_type: str,
    *,
    candidate_id: str,
    rt_left_min: float | None,
    rt_apex_min: float | None,
    rt_right_min: float | None,
    comment: str,
    expected_diff_required: bool,
    source: str,
    row_number: int,
) -> None:
    if action_type == "select_candidate" and not candidate_id:
        raise ReviewActionError(
            f"{source}:{row_number}: select_candidate requires candidate_id"
        )
    if action_type == "reject_current" and not comment:
        raise ReviewActionError(
            f"{source}:{row_number}: reject_current requires comment"
        )
    if action_type == "set_manual_boundary":
        if rt_left_min is None or rt_apex_min is None or rt_right_min is None:
            raise ReviewActionError(
                f"{source}:{row_number}: set_manual_boundary requires "
                "rt_left_min, rt_apex_min, and rt_right_min"
            )
        if not rt_left_min <= rt_apex_min <= rt_right_min:
            raise ReviewActionError(
                f"{source}:{row_number}: manual boundary must satisfy "
                "rt_left_min <= rt_apex_min <= rt_right_min"
            )
    if action_type in PRODUCT_MUTATING_REVIEW_ACTIONS and not expected_diff_required:
        raise ReviewActionError(
            f"{source}:{row_number}: {action_type} requires expected_diff_required"
        )


def _normalize_row(row: Mapping[str, object]) -> dict[str, str]:
    return {
        header: _clean_text(row.get(header, ""))
        for header in REVIEW_ACTION_COLUMNS
    }


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _required_text(
    row: Mapping[str, str],
    key: str,
    source: str,
    row_number: int,
) -> str:
    value = row[key]
    if not value:
        raise ReviewActionError(f"{source}:{row_number}: {key} is required")
    return value


def _optional_float(
    value: str,
    key: str,
    source: str,
    row_number: int,
) -> float | None:
    if not value:
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise ReviewActionError(
            f"{source}:{row_number}: {key} must be numeric"
        ) from exc


def _parse_bool(
    value: str,
    key: str,
    source: str,
    row_number: int,
) -> bool:
    if not value:
        return False
    normalized = value.upper()
    if normalized == "TRUE":
        return True
    if normalized == "FALSE":
        return False
    raise ReviewActionError(f"{source}:{row_number}: {key} must be TRUE or FALSE")


def _required_enum(
    row: Mapping[str, str],
    key: str,
    allowed: frozenset[str],
    source: str,
    row_number: int,
) -> str:
    value = _required_text(row, key, source, row_number)
    if value not in allowed:
        raise ReviewActionError(
            f"{source}:{row_number}: {key} must be one of "
            f"{', '.join(sorted(allowed))}"
        )
    return value


def _split_multi(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(";") if part.strip())


def _stable_float(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.8g}"


def _changeset_from_readiness(
    readiness: ReviewActionApplyReadiness,
) -> ReviewActionApplyChangeset:
    action = readiness.application.action
    if readiness.apply_readiness_status == "ready_no_output_change":
        return ReviewActionApplyChangeset(
            readiness=readiness,
            changeset_status="ready_audit_only",
            operation="record_accept_current",
            output_scope=("audit_trail",),
            proposed_review_state="accepted_current",
            reason="records_review_intent_without_product_mutation",
        )
    if readiness.apply_readiness_status != "ready_expected_diff_approved":
        return ReviewActionApplyChangeset(
            readiness=readiness,
            changeset_status="blocked",
            operation="",
            output_scope=(),
            reason=readiness.reason,
        )
    if action.action_type == "reject_current":
        return ReviewActionApplyChangeset(
            readiness=readiness,
            changeset_status="ready_pending_product_writer",
            operation="reject_current",
            output_scope=(
                "product_state",
                "counted_detection",
                "targeted_long_csv",
                "workbook",
                "final_matrix",
                "audit_trail",
            ),
            proposed_product_state="rejected_by_review",
            proposed_counted_detection="FALSE",
            reason="approved_expected_diff_allows_future_reject_current",
        )
    if action.action_type == "select_candidate":
        return ReviewActionApplyChangeset(
            readiness=readiness,
            changeset_status="ready_pending_product_writer",
            operation="select_candidate",
            output_scope=(
                "selected_candidate",
                "selected_peak",
                "targeted_long_csv",
                "workbook",
                "final_matrix",
                "audit_trail",
            ),
            requires_candidate_sidecar=True,
            reason="approved_expected_diff_allows_future_candidate_switch",
        )
    if action.action_type == "set_manual_boundary":
        return ReviewActionApplyChangeset(
            readiness=readiness,
            changeset_status="ready_pending_product_writer",
            operation="set_manual_boundary",
            output_scope=(
                "selected_boundary",
                "area",
                "targeted_long_csv",
                "workbook",
                "final_matrix",
                "audit_trail",
            ),
            requires_area_recompute=True,
            reason="approved_expected_diff_allows_future_manual_boundary",
        )
    return ReviewActionApplyChangeset(
        readiness=readiness,
        changeset_status="blocked",
        operation="",
        output_scope=(),
        reason="unsupported_ready_review_action",
    )


def summarize_review_actions(actions: Sequence[ReviewAction]) -> dict[str, object]:
    counts_by_type = {action_type: 0 for action_type in sorted(REVIEW_ACTION_TYPES)}
    product_mutating_count = 0
    for action in actions:
        counts_by_type[action.action_type] += 1
        if action.product_mutating:
            product_mutating_count += 1
    return {
        "schema_version": REVIEW_ACTION_SCHEMA_VERSION,
        "action_count": len(actions),
        "product_mutating_action_count": product_mutating_count,
        "counts_by_type": counts_by_type,
    }


def summarize_review_action_applications(
    applications: Sequence[ReviewActionApplication],
) -> dict[str, object]:
    counts_by_status: dict[str, int] = {}
    expected_diff_required_count = 0
    product_mutating_count = 0
    blocked_count = 0
    for application in applications:
        counts_by_status[application.application_status] = (
            counts_by_status.get(application.application_status, 0) + 1
        )
        if application.expected_diff_status == "required_before_apply":
            expected_diff_required_count += 1
        if application.product_mutating:
            product_mutating_count += 1
        if application.application_status.startswith("blocked"):
            blocked_count += 1
    return {
        "schema_version": REVIEW_ACTION_APPLICATION_PLAN_SCHEMA_VERSION,
        "application_count": len(applications),
        "blocked_application_count": blocked_count,
        "product_mutating_action_count": product_mutating_count,
        "expected_diff_required_count": expected_diff_required_count,
        "counts_by_status": dict(sorted(counts_by_status.items())),
    }


def summarize_review_action_expected_diff_approvals(
    approvals: Mapping[str, ReviewActionExpectedDiffApproval],
) -> dict[str, object]:
    counts_by_action_type: dict[str, int] = {}
    counts_by_validation_tier: dict[str, int] = {}
    counts_by_matrix_value_impact: dict[str, int] = {}
    for approval in approvals.values():
        counts_by_action_type[approval.action_type] = (
            counts_by_action_type.get(approval.action_type, 0) + 1
        )
        counts_by_validation_tier[approval.validation_tier] = (
            counts_by_validation_tier.get(approval.validation_tier, 0) + 1
        )
        counts_by_matrix_value_impact[approval.expected_matrix_value_impact] = (
            counts_by_matrix_value_impact.get(
                approval.expected_matrix_value_impact,
                0,
            )
            + 1
        )
    return {
        "schema_version": REVIEW_ACTION_EXPECTED_DIFF_SCHEMA_VERSION,
        "approval_count": len(approvals),
        "counts_by_action_type": dict(sorted(counts_by_action_type.items())),
        "counts_by_validation_tier": dict(sorted(counts_by_validation_tier.items())),
        "counts_by_matrix_value_impact": dict(
            sorted(counts_by_matrix_value_impact.items())
        ),
    }


def summarize_review_action_apply_readiness_plan(
    plan: ReviewActionApplyReadinessPlan,
) -> dict[str, object]:
    counts_by_status: dict[str, int] = {}
    ready_count = 0
    blocked_count = 0
    for row in plan.rows:
        counts_by_status[row.apply_readiness_status] = (
            counts_by_status.get(row.apply_readiness_status, 0) + 1
        )
        if row.apply_readiness_status.startswith("ready"):
            ready_count += 1
        if row.apply_readiness_status.startswith("blocked"):
            blocked_count += 1
    return {
        "schema_version": REVIEW_ACTION_APPLY_READINESS_SCHEMA_VERSION,
        "row_count": len(plan.rows),
        "ready_count": ready_count,
        "blocked_count": blocked_count,
        "unused_expected_diff_approval_count": len(
            plan.unused_expected_diff_approvals
        ),
        "counts_by_status": dict(sorted(counts_by_status.items())),
    }


def summarize_review_action_apply_changeset_plan(
    plan: ReviewActionApplyChangesetPlan,
) -> dict[str, object]:
    counts_by_status: dict[str, int] = {}
    counts_by_operation: dict[str, int] = {}
    ready_count = 0
    blocked_count = 0
    area_recompute_count = 0
    candidate_sidecar_count = 0
    for row in plan.rows:
        counts_by_status[row.changeset_status] = (
            counts_by_status.get(row.changeset_status, 0) + 1
        )
        if row.operation:
            counts_by_operation[row.operation] = (
                counts_by_operation.get(row.operation, 0) + 1
            )
        if row.changeset_status.startswith("ready"):
            ready_count += 1
        if row.changeset_status.startswith("blocked"):
            blocked_count += 1
        if row.requires_area_recompute:
            area_recompute_count += 1
        if row.requires_candidate_sidecar:
            candidate_sidecar_count += 1
    return {
        "schema_version": REVIEW_ACTION_APPLY_CHANGESET_SCHEMA_VERSION,
        "row_count": len(plan.rows),
        "ready_count": ready_count,
        "blocked_count": blocked_count,
        "requires_area_recompute_count": area_recompute_count,
        "requires_candidate_sidecar_count": candidate_sidecar_count,
        "counts_by_status": dict(sorted(counts_by_status.items())),
        "counts_by_operation": dict(sorted(counts_by_operation.items())),
    }


def review_action_application_to_row(
    application: ReviewActionApplication,
) -> dict[str, object]:
    action = application.action
    target_state = application.target_state
    return {
        "schema_version": REVIEW_ACTION_APPLICATION_PLAN_SCHEMA_VERSION,
        "sample_name": action.sample_name,
        "target_label": action.target_label,
        "action_type": action.action_type,
        "application_status": application.application_status,
        "product_mutating": action.product_mutating,
        "current_product_state": target_state.product_state if target_state else "",
        "current_counted_detection": (
            target_state.counted_detection if target_state else ""
        ),
        "current_review_state": target_state.review_state if target_state else "",
        "candidate_id": action.candidate_id,
        "boundary_id": action.boundary_id,
        "rt_left_min": action.rt_left_min,
        "rt_apex_min": action.rt_apex_min,
        "rt_right_min": action.rt_right_min,
        "expected_diff_required": action.expected_diff_required,
        "expected_diff_status": application.expected_diff_status,
        "reason": application.reason,
        "reviewer": action.reviewer,
        "reviewed_at": action.reviewed_at,
        "comment": action.comment,
    }


def review_action_apply_changeset_to_row(
    changeset: ReviewActionApplyChangeset,
) -> dict[str, object]:
    readiness = changeset.readiness
    application = readiness.application
    action = application.action
    approval = readiness.expected_diff_approval
    expected_public_outputs_touched = (
        ";".join(approval.expected_public_outputs_touched) if approval else ""
    )
    evidence_sources = ";".join(approval.evidence_sources) if approval else ""
    return {
        "schema_version": REVIEW_ACTION_APPLY_CHANGESET_SCHEMA_VERSION,
        "sample_name": action.sample_name,
        "target_label": action.target_label,
        "action_type": action.action_type,
        "changeset_status": changeset.changeset_status,
        "apply_readiness_status": readiness.apply_readiness_status,
        "operation": changeset.operation,
        "product_mutating": action.product_mutating,
        "output_scope": ";".join(changeset.output_scope),
        "requires_expected_diff_approval": action.product_mutating,
        "expected_diff_stable_row_id": readiness.expected_diff_stable_row_id,
        "expected_diff_validation_tier": approval.validation_tier if approval else "",
        "expected_matrix_value_impact": (
            approval.expected_matrix_value_impact if approval else ""
        ),
        "expected_public_outputs_touched": expected_public_outputs_touched,
        "evidence_sources": evidence_sources,
        "evidence_summary": approval.evidence_summary if approval else "",
        "candidate_id": action.candidate_id,
        "boundary_id": action.boundary_id,
        "rt_left_min": action.rt_left_min,
        "rt_apex_min": action.rt_apex_min,
        "rt_right_min": action.rt_right_min,
        "proposed_product_state": changeset.proposed_product_state,
        "proposed_counted_detection": changeset.proposed_counted_detection,
        "proposed_review_state": changeset.proposed_review_state,
        "requires_area_recompute": changeset.requires_area_recompute,
        "requires_candidate_sidecar": changeset.requires_candidate_sidecar,
        "reason": changeset.reason,
        "reviewer": action.reviewer,
        "reviewed_at": action.reviewed_at,
        "comment": action.comment,
        "approval_notes": approval.approval_notes if approval else "",
    }


def review_action_apply_readiness_to_row(
    readiness: ReviewActionApplyReadiness,
) -> dict[str, object]:
    application = readiness.application
    action = application.action
    target_state = application.target_state
    approval = readiness.expected_diff_approval
    expected_public_outputs_touched = (
        ";".join(approval.expected_public_outputs_touched) if approval else ""
    )
    evidence_sources = ";".join(approval.evidence_sources) if approval else ""
    return {
        "schema_version": REVIEW_ACTION_APPLY_READINESS_SCHEMA_VERSION,
        "sample_name": action.sample_name,
        "target_label": action.target_label,
        "action_type": action.action_type,
        "apply_readiness_status": readiness.apply_readiness_status,
        "product_mutating": action.product_mutating,
        "current_product_state": target_state.product_state if target_state else "",
        "current_counted_detection": (
            target_state.counted_detection if target_state else ""
        ),
        "current_review_state": target_state.review_state if target_state else "",
        "expected_diff_stable_row_id": readiness.expected_diff_stable_row_id,
        "expected_diff_approval_status": (
            approval.reviewer_verdict if approval else ""
        ),
        "expected_diff_validation_tier": approval.validation_tier if approval else "",
        "expected_matrix_value_impact": (
            approval.expected_matrix_value_impact if approval else ""
        ),
        "expected_public_outputs_touched": expected_public_outputs_touched,
        "evidence_sources": evidence_sources,
        "evidence_summary": approval.evidence_summary if approval else "",
        "candidate_id": action.candidate_id,
        "boundary_id": action.boundary_id,
        "rt_left_min": action.rt_left_min,
        "rt_apex_min": action.rt_apex_min,
        "rt_right_min": action.rt_right_min,
        "reason": readiness.reason,
        "reviewer": action.reviewer,
        "reviewed_at": action.reviewed_at,
        "comment": action.comment,
        "approval_notes": approval.approval_notes if approval else "",
    }


def review_action_expected_diff_template_to_row(
    template: ReviewActionExpectedDiffTemplate,
) -> dict[str, object]:
    action = template.application.action
    return {
        "schema_version": REVIEW_ACTION_EXPECTED_DIFF_SCHEMA_VERSION,
        "stable_row_id": template.stable_row_id,
        "sample_name": action.sample_name,
        "target_label": action.target_label,
        "action_type": action.action_type,
        "candidate_id": action.candidate_id,
        "boundary_id": action.boundary_id,
        "rt_left_min": action.rt_left_min,
        "rt_apex_min": action.rt_apex_min,
        "rt_right_min": action.rt_right_min,
        "expected_public_outputs_touched": ";".join(
            template.expected_public_outputs_touched
        ),
        "expected_matrix_value_impact": template.expected_matrix_value_impact,
        "evidence_sources": "",
        "evidence_summary": "",
        "validation_tier": "not_validated",
        "reviewer_verdict": "inconclusive",
        "final_label": "inconclusive",
        "reviewer": action.reviewer,
        "reviewed_at": action.reviewed_at,
        "comment": action.comment,
        "approval_notes": "",
    }
