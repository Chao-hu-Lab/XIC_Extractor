from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from xic_extractor.alignment.config import AlignmentConfig
from xic_extractor.alignment.models import AlignmentCluster


def cluster_candidates(
    candidates: Sequence[Any],
    config: AlignmentConfig | None = None,
) -> tuple[AlignmentCluster, ...]:
    if candidates:
        raise NotImplementedError("alignment clustering is not implemented yet")
    return ()
