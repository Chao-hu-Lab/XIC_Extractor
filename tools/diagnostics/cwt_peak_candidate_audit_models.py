from __future__ import annotations

from dataclasses import dataclass

_CWT_SOURCE = "centwave_cwt"


_DEFAULT_NEAR_RT_WINDOW_MIN = 0.08


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
    "reason",
)


_SUMMARY_COLUMNS = (
    "candidate_row_count",
    "candidate_group_count",
    "cwt_row_count",
    "cwt_only_row_count",
    "selected_cwt_agreed_group_count",
    "selected_cwt_nearby_group_count",
    "selected_cwt_far_alternative_group_count",
    "selected_without_cwt_group_count",
    "cwt_selected_support_group_count",
    "cwt_far_unconfirmed_group_count",
    "cwt_far_chemically_plausible_group_count",
)


_GROUP_COLUMNS = (
    "group_id",
    "sample_name",
    "target_label",
    "target_mz",
    "resolver_mode",
    "cwt_agreement_class",
    "cwt_conditioned_class",
    "candidate_count",
    "cwt_row_count",
    "cwt_only_row_count",
    "selected_candidate_id",
    "selected_rt_apex_min",
    "selected_proposal_sources",
    "selected_ms2_present",
    "selected_nl_match",
    "selected_ms2_trace_strength",
    "nearest_cwt_candidate_id",
    "nearest_cwt_rt_apex_min",
    "nearest_cwt_delta_min",
    "nearest_cwt_ms2_present",
    "nearest_cwt_nl_match",
    "nearest_cwt_ms2_trace_strength",
    "selected_confidence",
    "selected_raw_score",
    "selected_reason",
)


_CWT_ONLY_COLUMNS = (
    "group_id",
    "sample_name",
    "target_label",
    "target_mz",
    "resolver_mode",
    "candidate_id",
    "rt_apex_min",
    "confidence",
    "raw_score",
    "reason",
)


@dataclass(frozen=True)
class CwtCandidateRow:
    sample_name: str
    target_label: str
    resolver_mode: str
    candidate_id: str
    proposal_sources: str
    rt_apex_min: float
    selected: bool
    confidence: str
    raw_score: str
    reason: str
    ms2_present: str
    nl_match: str
    ms2_trace_strength: str

    @property
    def group_id(self) -> str:
        return "|".join((self.sample_name, self.target_label, self.resolver_mode))

    @property
    def source_set(self) -> frozenset[str]:
        return frozenset(
            source.strip()
            for source in self.proposal_sources.split(";")
            if source.strip()
        )

    @property
    def has_cwt(self) -> bool:
        return _CWT_SOURCE in self.source_set

    @property
    def cwt_only(self) -> bool:
        return self.source_set == frozenset({_CWT_SOURCE})


@dataclass(frozen=True)
class CwtGroupAuditRow:
    group_id: str
    sample_name: str
    target_label: str
    target_mz: float | None
    resolver_mode: str
    cwt_agreement_class: str
    cwt_conditioned_class: str
    candidate_count: int
    cwt_row_count: int
    cwt_only_row_count: int
    selected_candidate_id: str
    selected_rt_apex_min: float | None
    selected_proposal_sources: str
    selected_ms2_present: str
    selected_nl_match: str
    selected_ms2_trace_strength: str
    nearest_cwt_candidate_id: str
    nearest_cwt_rt_apex_min: float | None
    nearest_cwt_delta_min: float | None
    nearest_cwt_ms2_present: str
    nearest_cwt_nl_match: str
    nearest_cwt_ms2_trace_strength: str
    selected_confidence: str
    selected_raw_score: str
    selected_reason: str


@dataclass(frozen=True)
class CwtOnlyAuditRow:
    group_id: str
    sample_name: str
    target_label: str
    target_mz: float | None
    resolver_mode: str
    candidate_id: str
    rt_apex_min: float
    confidence: str
    raw_score: str
    reason: str
