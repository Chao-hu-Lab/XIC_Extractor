from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.extraction import target_extraction
from xic_extractor.extraction.scoring_factory import allow_prepass_anchor
from xic_extractor.output.messages import DiagnosticRecord
from xic_extractor.raw_reader import open_raw

if TYPE_CHECKING:
    from xic_extractor.extractor import ExtractionResult


def extract_istd_anchors_only(
    config: ExtractionConfig, istd_targets: list[Target], raw_path: Path
) -> tuple[
    dict[str, float],
    dict[str, ExtractionResult],
    list[DiagnosticRecord],
    dict[str, tuple[float, float | None]],
] | None:
    if not istd_targets:
        return {}, {}, [], {}
    try:
        with open_raw(raw_path, config.dll_dir) as raw:
            results: dict[str, ExtractionResult] = {}
            diagnostics: list[DiagnosticRecord] = []
            anchors: dict[str, float] = {}
            shape_metrics_by_label: dict[str, tuple[float, float | None]] = {}
            for target in istd_targets:
                anchor_rt = target_extraction.extract_one_target(
                    raw,
                    config,
                    raw_path.stem,
                    target,
                    reference_rt=None,
                    strict_preferred_rt=False,
                    results=results,
                    diagnostics=diagnostics,
                    shape_metrics_by_label=shape_metrics_by_label,
                )
                result = results.get(target.label)
                if (
                    anchor_rt is not None
                    and result is not None
                    and allow_prepass_anchor(result.peak_result)
                ):
                    anchors[target.label] = anchor_rt
            return anchors, results, diagnostics, shape_metrics_by_label
    except Exception:
        return None
