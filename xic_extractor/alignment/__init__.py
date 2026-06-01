import xic_extractor.alignment.backfill as backfill
import xic_extractor.alignment.clustering as clustering
import xic_extractor.alignment.config as config
import xic_extractor.alignment.matrix as matrix
import xic_extractor.alignment.models as models
from xic_extractor.alignment.backfill import (
    backfill_alignment_matrix as _event_first_backfill_alignment_matrix,
)
from xic_extractor.alignment.clustering import (
    cluster_candidates as _event_first_cluster_candidates,
)
from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.matrix import AlignedCell, AlignmentMatrix, CellStatus
from xic_extractor.alignment.models import AlignmentCluster

__all__ = (
    "AlignmentConfig",
    "AlignmentCluster",
    "AlignedCell",
    "AlignmentMatrix",
    "CellStatus",
    "cluster_candidates",
    "backfill_alignment_matrix",
)


def __dir__() -> tuple[str, ...]:
    return __all__


def cluster_candidates(candidates, *, config=None):
    """Deprecated event-first compatibility shim.

    The product alignment path is owner-first through `run_alignment(...)`.
    This public import remains available during the event-first retirement
    window for compatibility with callers and tests that still exercise the
    legacy event-first clustering contract.
    """

    return _event_first_cluster_candidates(candidates, config=config)


def backfill_alignment_matrix(
    clusters,
    *,
    sample_order,
    raw_sources,
    alignment_config,
    peak_config,
    emit_region_audit=False,
):
    """Deprecated event-first compatibility shim.

    The product alignment path is owner-first through `run_alignment(...)`.
    This public import remains available during the event-first retirement
    window for compatibility with callers and tests that still exercise the
    legacy event-first backfill contract.
    """

    return _event_first_backfill_alignment_matrix(
        clusters,
        sample_order=sample_order,
        raw_sources=raw_sources,
        alignment_config=alignment_config,
        peak_config=peak_config,
        emit_region_audit=emit_region_audit,
    )


del backfill
del clustering
del config
del matrix
del models
