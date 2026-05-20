from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Protocol

import numpy as np

from xic_extractor.config import ExtractionConfig
from xic_extractor.injection_rolling import read_injection_order
from xic_extractor.instrument_qc.classification import (
    InstrumentQCClass,
    classify_instrument_qc_raw,
)
from xic_extractor.instrument_qc.mixstds import (
    discover_mixstds_raws,
    load_mixstds_target_registry,
)
from xic_extractor.instrument_qc.models import (
    InstrumentQCDiagnostic,
    InstrumentQCRunOutput,
    InstrumentQCStatus,
    SDOLEKTrendRow,
)
from xic_extractor.instrument_qc.targets import SDOLEK_TARGETS, InstrumentQCTarget
from xic_extractor.instrument_qc.workbook import write_sdolek_workbook
from xic_extractor.instrument_qc.writers import (
    write_diagnostics_tsv,
    write_sdolek_json,
    write_trend_tsv,
)
from xic_extractor.peak_detection.facade import find_peak_and_area
from xic_extractor.raw_reader import open_raw
from xic_extractor.settings_schema import CANONICAL_SETTINGS_DEFAULTS

DEFAULT_DLL_DIR = Path(CANONICAL_SETTINGS_DEFAULTS["dll_dir"])


class XICSource(Protocol):
    def extract_xic(
        self,
        mz: float,
        rt_min: float,
        rt_max: float,
        ppm_tol: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        ...


RawOpener = Callable[[Path], AbstractContextManager[XICSource]]


def run_sdolek_pipeline(
    *,
    raw_dir: Path,
    output_dir: Path,
    injection_order_source: Path | None = None,
    dll_dir: Path | None = None,
    raw_opener: RawOpener | None = None,
    emit_mixstds: bool = False,
    mixstds_target_registry: Path | None = None,
) -> InstrumentQCRunOutput:
    diagnostics: list[InstrumentQCDiagnostic] = []
    raw_paths = _discover_sdolek_raws(raw_dir, diagnostics)
    injection_order = _read_optional_injection_order(
        injection_order_source,
        raw_paths,
        diagnostics,
    )
    effective_dll_dir = dll_dir or DEFAULT_DLL_DIR
    opener = raw_opener or (lambda path: open_raw(path, effective_dll_dir))
    rows: list[SDOLEKTrendRow] = []

    for raw_path in raw_paths:
        sample_name = raw_path.stem
        try:
            with opener(raw_path) as raw:
                for target in SDOLEK_TARGETS:
                    try:
                        rows.append(
                            _extract_target_row(
                                raw=raw,
                                raw_path=raw_path,
                                sample_name=sample_name,
                                injection_order=injection_order.get(sample_name),
                                target=target,
                                dll_dir=effective_dll_dir,
                            )
                        )
                    except Exception as exc:
                        diagnostics.append(
                            InstrumentQCDiagnostic(
                                sample_name=sample_name,
                                raw_path=raw_path,
                                issue="TARGET_EXTRACTION_ERROR",
                                detail=f"{target.compound}: {exc}",
                            )
                        )
                        rows.append(
                            _error_row(
                                raw_path=raw_path,
                                sample_name=sample_name,
                                injection_order=injection_order.get(sample_name),
                                target=target,
                                reason=str(exc),
                            )
                        )
        except Exception as exc:
            diagnostics.append(
                InstrumentQCDiagnostic(
                    sample_name=sample_name,
                    raw_path=raw_path,
                    issue="RAW_EXTRACTION_ERROR",
                    detail=str(exc),
                )
            )
            rows.extend(
                _error_row(
                    raw_path=raw_path,
                    sample_name=sample_name,
                    injection_order=injection_order.get(sample_name),
                    target=target,
                    reason=str(exc),
                )
                for target in SDOLEK_TARGETS
            )

    mixstds_rows: tuple[SDOLEKTrendRow, ...] = ()
    mixstds_diagnostics: list[InstrumentQCDiagnostic] = []
    if emit_mixstds:
        mixstds_rows = _run_mixstds_extraction(
            raw_dir=raw_dir,
            injection_order=injection_order,
            opener=opener,
            dll_dir=effective_dll_dir,
            target_registry=mixstds_target_registry,
            diagnostics=mixstds_diagnostics,
        )

    trend_tsv = output_dir / "instrument_qc_sdolek_trend.tsv"
    trend_json = output_dir / "instrument_qc_sdolek_trend.json"
    diagnostics_tsv = output_dir / "instrument_qc_sdolek_diagnostics.tsv"
    workbook = output_dir / "instrument_qc_trend_sdolek.xlsx"
    mixstds_trend_tsv = (
        output_dir / "instrument_qc_mixstds_trend.tsv" if emit_mixstds else None
    )
    mixstds_trend_json = (
        output_dir / "instrument_qc_mixstds_trend.json" if emit_mixstds else None
    )
    mixstds_diagnostics_tsv = (
        output_dir / "instrument_qc_mixstds_diagnostics.tsv"
        if emit_mixstds
        else None
    )
    write_trend_tsv(trend_tsv, rows)
    metadata_source_status = _metadata_source_status(injection_order_source)
    write_sdolek_json(
        trend_json,
        rows,
        diagnostics,
        metadata_source_status=metadata_source_status,
    )
    write_diagnostics_tsv(diagnostics_tsv, diagnostics)
    if mixstds_trend_tsv is not None:
        write_trend_tsv(mixstds_trend_tsv, mixstds_rows)
    if mixstds_trend_json is not None:
        write_sdolek_json(
            mixstds_trend_json,
            mixstds_rows,
            mixstds_diagnostics,
            metadata_source_status={
                "target_registry_source": str(mixstds_target_registry or ""),
                "target_registry_status": (
                    "provided" if mixstds_target_registry else "missing"
                ),
            },
        )
    if mixstds_diagnostics_tsv is not None:
        write_diagnostics_tsv(mixstds_diagnostics_tsv, mixstds_diagnostics)
    write_sdolek_workbook(
        workbook,
        rows,
        diagnostics,
        metadata_source_status=metadata_source_status,
        mixstds_rows=mixstds_rows if emit_mixstds else None,
    )
    return InstrumentQCRunOutput(
        trend_rows=tuple(rows),
        diagnostics=tuple(diagnostics + mixstds_diagnostics),
        trend_tsv=trend_tsv,
        trend_json=trend_json,
        diagnostics_tsv=diagnostics_tsv,
        workbook=workbook,
        mixstds_rows=mixstds_rows,
        mixstds_trend_tsv=mixstds_trend_tsv,
        mixstds_trend_json=mixstds_trend_json,
        mixstds_diagnostics_tsv=mixstds_diagnostics_tsv,
    )


def _run_mixstds_extraction(
    *,
    raw_dir: Path,
    injection_order: dict[str, int],
    opener: RawOpener,
    dll_dir: Path,
    target_registry: Path | None,
    diagnostics: list[InstrumentQCDiagnostic],
) -> tuple[SDOLEKTrendRow, ...]:
    registry = load_mixstds_target_registry(target_registry)
    if registry.status != "loaded":
        diagnostics.append(
            InstrumentQCDiagnostic(
                sample_name="",
                raw_path=target_registry or raw_dir,
                issue=f"MIXSTDS_TARGET_REGISTRY_{registry.status.upper()}",
                detail=registry.reason,
            )
        )
        return ()

    rows: list[SDOLEKTrendRow] = []
    raw_paths = discover_mixstds_raws(raw_dir, diagnostics)
    if not raw_paths:
        diagnostics.append(
            InstrumentQCDiagnostic(
                sample_name="",
                raw_path=raw_dir,
                issue="MIXSTDS_RAW_MISSING",
                detail="No Mix STDs RAW files found under STDs or Pairs.",
            )
        )
        return ()

    for raw_path in raw_paths:
        sample_name = raw_path.stem
        try:
            with opener(raw_path) as raw:
                for target in registry.targets:
                    try:
                        rows.append(
                            _extract_target_row(
                                raw=raw,
                                raw_path=raw_path,
                                sample_name=sample_name,
                                injection_order=injection_order.get(sample_name),
                                target=target,
                                dll_dir=dll_dir,
                            )
                        )
                    except Exception as exc:
                        diagnostics.append(
                            InstrumentQCDiagnostic(
                                sample_name=sample_name,
                                raw_path=raw_path,
                                issue="MIXSTDS_TARGET_EXTRACTION_ERROR",
                                detail=f"{target.compound}: {exc}",
                            )
                        )
                        rows.append(
                            _error_row(
                                raw_path=raw_path,
                                sample_name=sample_name,
                                injection_order=injection_order.get(sample_name),
                                target=target,
                                reason=str(exc),
                            )
                        )
        except Exception as exc:
            diagnostics.append(
                InstrumentQCDiagnostic(
                    sample_name=sample_name,
                    raw_path=raw_path,
                    issue="MIXSTDS_RAW_EXTRACTION_ERROR",
                    detail=str(exc),
                )
            )
            rows.extend(
                _error_row(
                    raw_path=raw_path,
                    sample_name=sample_name,
                    injection_order=injection_order.get(sample_name),
                    target=target,
                    reason=str(exc),
                )
                for target in registry.targets
            )
    return tuple(rows)


def _discover_sdolek_raws(
    raw_dir: Path,
    diagnostics: list[InstrumentQCDiagnostic],
) -> tuple[Path, ...]:
    sdolek_dir = raw_dir / "SDOLEK"
    if not sdolek_dir.exists():
        raise FileNotFoundError(f"Missing expected SDOLEK folder: {sdolek_dir}")
    candidates = sorted(sdolek_dir.glob("*.raw"))
    selected: list[Path] = []
    seen_stems: set[str] = set()
    for path in candidates:
        if classify_instrument_qc_raw(path, raw_dir) != InstrumentQCClass.SDOLEK:
            continue
        normalized_stem = path.stem.casefold()
        if normalized_stem in seen_stems:
            diagnostics.append(
                InstrumentQCDiagnostic(
                    sample_name=path.stem,
                    raw_path=path,
                    issue="DUPLICATE_RAW_STEM",
                    detail="Duplicate SDOLEK RAW stem skipped.",
                )
            )
            continue
        seen_stems.add(normalized_stem)
        selected.append(path)
    return tuple(selected)


def _read_optional_injection_order(
    path: Path | None,
    raw_paths: tuple[Path, ...],
    diagnostics: list[InstrumentQCDiagnostic],
) -> dict[str, int]:
    if path is None:
        for raw_path in raw_paths:
            diagnostics.append(
                InstrumentQCDiagnostic(
                    sample_name=raw_path.stem,
                    raw_path=raw_path,
                    issue="INJECTION_ORDER_MISSING",
                    detail="No injection-order file supplied.",
                )
            )
        return {}
    return read_injection_order(path)


def _metadata_source_status(path: Path | None) -> dict[str, str]:
    if path is None:
        return {
            "injection_order_source": "",
            "injection_order_status": "missing",
        }
    return {
        "injection_order_source": str(path),
        "injection_order_status": "provided",
    }


def _extract_target_row(
    *,
    raw: XICSource,
    raw_path: Path,
    sample_name: str,
    injection_order: int | None,
    target: InstrumentQCTarget,
    dll_dir: Path,
) -> SDOLEKTrendRow:
    rt, intensity = raw.extract_xic(
        mz=target.precursor_mz,
        rt_min=target.rt_min,
        rt_max=target.rt_max,
        ppm_tol=target.ppm_tol,
    )
    result = find_peak_and_area(rt, intensity, _peak_config(raw_path.parent, dll_dir))
    if result.peak is None or result.status != "OK":
        return _error_row(
            raw_path=raw_path,
            sample_name=sample_name,
            injection_order=injection_order,
            target=target,
            reason=result.status,
            status="not_detected",
        )
    peak = result.peak
    base_width = peak.peak_end - peak.peak_start
    rt_delta = peak.rt - target.reference_rt_min
    width_ratio = (
        base_width / target.reference_base_width_min
        if target.reference_base_width_min
        else None
    )
    flags = _trend_flags(rt_delta=rt_delta, width_ratio=width_ratio)
    return SDOLEKTrendRow(
        sample_name=sample_name,
        raw_path=raw_path,
        injection_order=injection_order,
        compound=target.compound,
        precursor_mz=target.precursor_mz,
        identity_evidence="MS1_ONLY",
        reference_rt_min=target.reference_rt_min,
        rt_delta_to_reference_min=rt_delta,
        apex_rt_min=peak.rt,
        area=peak.area,
        base_width_min=base_width,
        reference_base_width_min=target.reference_base_width_min,
        base_width_ratio_to_reference=width_ratio,
        peak_start_rt_min=peak.peak_start,
        peak_end_rt_min=peak.peak_end,
        trend_confidence="warning" if flags else "clean",
        trend_flags=flags,
        status="detected",
        reason="OK",
    )


def _error_row(
    *,
    raw_path: Path,
    sample_name: str,
    injection_order: int | None,
    target: InstrumentQCTarget,
    reason: str,
    status: InstrumentQCStatus = "error",
) -> SDOLEKTrendRow:
    return SDOLEKTrendRow(
        sample_name=sample_name,
        raw_path=raw_path,
        injection_order=injection_order,
        compound=target.compound,
        precursor_mz=target.precursor_mz,
        identity_evidence="MS1_ONLY",
        reference_rt_min=target.reference_rt_min,
        rt_delta_to_reference_min=None,
        apex_rt_min=None,
        area=None,
        base_width_min=None,
        reference_base_width_min=target.reference_base_width_min,
        base_width_ratio_to_reference=None,
        peak_start_rt_min=None,
        peak_end_rt_min=None,
        trend_confidence="low",
        trend_flags=("LOW_PEAK_CONFIDENCE",),
        status=status,
        reason=reason,
    )


def _trend_flags(
    *,
    rt_delta: float,
    width_ratio: float | None,
) -> tuple[str, ...]:
    flags: list[str] = []
    if abs(rt_delta) > 0.50:
        flags.append("RT_OUTLIER")
    if width_ratio is not None and (width_ratio < 0.50 or width_ratio > 1.75):
        flags.append("WIDTH_OUTLIER")
    return tuple(flags)


def _peak_config(data_dir: Path, dll_dir: Path) -> ExtractionConfig:
    return ExtractionConfig(
        data_dir=data_dir,
        dll_dir=dll_dir,
        output_csv=Path("instrument_qc.csv"),
        diagnostics_csv=Path("instrument_qc_diagnostics.csv"),
        smooth_window=7,
        smooth_polyorder=2,
        peak_rel_height=0.5,
        peak_min_prominence_ratio=0.05,
        ms2_precursor_tol_da=0.5,
        nl_min_intensity_ratio=0.01,
        resolver_mode="local_minimum",
    )
