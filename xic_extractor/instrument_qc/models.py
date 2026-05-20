from dataclasses import dataclass
from pathlib import Path
from typing import Literal

TrendConfidence = Literal["clean", "warning", "low"]
InstrumentQCStatus = Literal["detected", "not_detected", "error"]


@dataclass(frozen=True)
class InstrumentQCDiagnostic:
    sample_name: str
    raw_path: Path
    issue: str
    detail: str


@dataclass(frozen=True)
class SDOLEKTrendRow:
    sample_name: str
    raw_path: Path
    injection_order: int | None
    compound: str
    precursor_mz: float
    identity_evidence: str
    reference_rt_min: float | None
    rt_delta_to_reference_min: float | None
    apex_rt_min: float | None
    area: float | None
    base_width_min: float | None
    reference_base_width_min: float | None
    base_width_ratio_to_reference: float | None
    peak_start_rt_min: float | None
    peak_end_rt_min: float | None
    trend_confidence: TrendConfidence
    trend_flags: tuple[str, ...]
    status: InstrumentQCStatus
    reason: str


@dataclass(frozen=True)
class InstrumentQCRunOutput:
    trend_rows: tuple[SDOLEKTrendRow, ...]
    diagnostics: tuple[InstrumentQCDiagnostic, ...]
    trend_tsv: Path
    trend_json: Path
    diagnostics_tsv: Path
    workbook: Path
