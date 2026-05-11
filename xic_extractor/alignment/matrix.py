from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

from xic_extractor.alignment.models import AlignmentCluster

CellStatus = Literal["detected", "rescued", "absent", "unchecked"]


class AlignmentRowLike(Protocol):
    neutral_loss_tag: str
    has_anchor: bool


@dataclass(frozen=True)
class AlignedCell:
    sample_stem: str
    cluster_id: str
    status: CellStatus
    area: float | None
    apex_rt: float | None
    height: float | None
    peak_start_rt: float | None
    peak_end_rt: float | None
    rt_delta_sec: float | None
    trace_quality: str
    scan_support_score: float | None
    source_candidate_id: str | None
    source_raw_file: Path | None
    reason: str


@dataclass(frozen=True)
class AlignmentMatrix:
    clusters: tuple[AlignmentCluster | AlignmentRowLike, ...]
    cells: tuple[AlignedCell, ...]
    sample_order: tuple[str, ...]
