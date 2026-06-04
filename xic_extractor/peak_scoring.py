"""Compatibility facade for legacy peak scoring imports."""

from __future__ import annotations

from xic_extractor.peak_detection.candidate_scoring import (
    score_candidate as score_candidate,
)
from xic_extractor.peak_detection.candidate_selection import (
    select_candidate_with_confidence as select_candidate_with_confidence,
)
from xic_extractor.peak_detection.scoring_cwt_support import (
    has_same_apex_cwt_support as _successor_has_same_apex_cwt_support,
)
from xic_extractor.peak_detection.scoring_metrics import (
    compute_local_sn_cache as compute_local_sn_cache,
)
from xic_extractor.peak_detection.scoring_metrics import (
    local_sn_severity as local_sn_severity,
)
from xic_extractor.peak_detection.scoring_metrics import (
    nl_support_severity as nl_support_severity,
)
from xic_extractor.peak_detection.scoring_metrics import (
    noise_shape_severity as noise_shape_severity,
)
from xic_extractor.peak_detection.scoring_metrics import (
    peak_width_severity as peak_width_severity,
)
from xic_extractor.peak_detection.scoring_metrics import (
    rt_centrality_severity as rt_centrality_severity,
)
from xic_extractor.peak_detection.scoring_metrics import (
    rt_prior_severity as rt_prior_severity,
)
from xic_extractor.peak_detection.scoring_metrics import (
    symmetry_severity as symmetry_severity,
)
from xic_extractor.peak_detection.scoring_models import (
    Confidence as Confidence,
)
from xic_extractor.peak_detection.scoring_models import (
    ScoredCandidate as ScoredCandidate,
)
from xic_extractor.peak_detection.scoring_models import (
    ScoringContext as ScoringContext,
)
from xic_extractor.peak_detection.scoring_models import (
    confidence_from_total as confidence_from_total,
)
from xic_extractor.peak_detection.scoring_quality import (
    candidate_quality_penalty as candidate_quality_penalty,
)
from xic_extractor.peak_detection.scoring_quality import (
    candidate_selection_quality_penalty as candidate_selection_quality_penalty,
)
from xic_extractor.peak_detection.scoring_quality import (
    hard_quality_flags as hard_quality_flags,
)
from xic_extractor.peak_detection.scoring_quality import (
    is_adap_like_quality_flag as is_adap_like_quality_flag,
)
from xic_extractor.peak_detection.scoring_quality import (
    trace_quality_severities as trace_quality_severities,
)
from xic_extractor.peak_detection.scoring_reason import (
    build_evidence_reason as build_evidence_reason,
)
from xic_extractor.peak_detection.scoring_reason import (
    build_reason as build_reason,
)
from xic_extractor.peak_detection.scoring_reason import (
    score_breakdown_fields as score_breakdown_fields,
)

_has_same_apex_cwt_support = _successor_has_same_apex_cwt_support
