from __future__ import annotations

from dataclasses import dataclass

_REQUIRED_COLUMNS = (
    "sample_name",
    "target_label",
    "resolver_mode",
    "candidate_id",
    "proposal_sources",
    "rt_apex_min",
    "selected",
    "confidence",
    "raw_score",
    "support_labels",
    "concern_labels",
    "cap_labels",
    "reason",
    "rejection_reason",
    "ms2_present",
    "nl_match",
    "ms2_trace_strength",
)


_APEX_SHADOW_RT_WINDOW_MIN = 0.08


_SUMMARY_COLUMNS = (
    "candidate_row_count",
    "candidate_group_count",
    "selected_row_count",
    "rejected_row_count",
    "selected_review_only_count",
    "selected_nl_fail_count",
    "selected_no_ms2_count",
    "plausible_nl_dropout_selected_count",
    "apex_evidence_shadow_group_count",
    "high_score_rejected_challenger_group_count",
    "strict_nl_rejected_challenger_group_count",
    "cwt_supported_rejected_challenger_group_count",
)


_RISK_COLUMNS = (
    "group_id",
    "sample_name",
    "target_label",
    "resolver_mode",
    "risk_type",
    "selected_candidate_id",
    "selected_rt_apex_min",
    "selected_raw_score",
    "selected_confidence",
    "selected_support_labels",
    "selected_concern_labels",
    "challenger_candidate_id",
    "challenger_rt_apex_min",
    "challenger_raw_score",
    "challenger_confidence",
    "challenger_support_labels",
    "challenger_concern_labels",
    "reason",
)


_LABEL_COLUMNS = (
    "label_kind",
    "label",
    "selected_count",
    "rejected_count",
    "selected_rate",
    "selected_median_raw_score",
    "rejected_median_raw_score",
)


@dataclass(frozen=True)
class PeakCandidateScoreRow:
    sample_name: str
    target_label: str
    resolver_mode: str
    candidate_id: str
    proposal_sources: str
    rt_apex_min: float | None
    selected: bool
    confidence: str
    raw_score: float | None
    support_labels: tuple[str, ...]
    concern_labels: tuple[str, ...]
    cap_labels: tuple[str, ...]
    reason: str
    rejection_reason: str
    ms2_present: str
    nl_match: str
    ms2_trace_strength: str

    @property
    def group_id(self) -> str:
        return "|".join((self.sample_name, self.target_label, self.resolver_mode))

    @property
    def source_set(self) -> frozenset[str]:
        return frozenset(_split_labels(self.proposal_sources))

    @property
    def support_set(self) -> frozenset[str]:
        return frozenset(self.support_labels)

    @property
    def concern_set(self) -> frozenset[str]:
        return frozenset(self.concern_labels)


@dataclass(frozen=True)
class ScoreRiskRow:
    group_id: str
    sample_name: str
    target_label: str
    resolver_mode: str
    risk_type: str
    selected_candidate_id: str
    selected_rt_apex_min: float | None
    selected_raw_score: float | None
    selected_confidence: str
    selected_support_labels: str
    selected_concern_labels: str
    challenger_candidate_id: str
    challenger_rt_apex_min: float | None
    challenger_raw_score: float | None
    challenger_confidence: str
    challenger_support_labels: str
    challenger_concern_labels: str
    reason: str


@dataclass(frozen=True)
class ScoreLabelImpactRow:
    label_kind: str
    label: str
    selected_count: int
    rejected_count: int
    selected_rate: float | None
    selected_median_raw_score: float | None
    rejected_median_raw_score: float | None


def _split_labels(value: str) -> list[str]:
    return [part.strip() for part in value.split(";") if part.strip()]
