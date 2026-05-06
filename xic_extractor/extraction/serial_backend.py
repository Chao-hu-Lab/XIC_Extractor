from __future__ import annotations

import gc
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.extraction.istd_prepass import extract_istd_anchors_only
from xic_extractor.extraction.pipeline import (
    fallback_injection_order_from_mtime,
    resolve_injection_order,
    resolve_rt_prior_library,
)
from xic_extractor.extraction.scoring_factory import build_scoring_context_factory
from xic_extractor.extraction.target_extraction import extract_raw_file_result
from xic_extractor.output.messages import DiagnosticRecord
from xic_extractor.rt_prior_library import LibraryEntry

if TYPE_CHECKING:
    from xic_extractor.extractor import FileResult, RunOutput


def run_serial(
    config: ExtractionConfig,
    targets: list[Target],
    *,
    raw_paths: list[Path],
    progress_callback: Callable[[int, int, str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
    injection_order: dict[str, int] | None = None,
    rt_prior_library: dict[tuple[str, str], LibraryEntry] | None = None,
) -> RunOutput:
    from xic_extractor import extractor

    resolved_injection_order = resolve_injection_order(
        config, raw_paths, injection_order
    )
    resolved_rt_prior_library = resolve_rt_prior_library(config, rt_prior_library)
    istd_targets = [target for target in targets if target.is_istd]
    istd_rts_by_sample: dict[str, dict[str, float]] = {}
    for raw_path in raw_paths:
        if should_stop is not None and should_stop():
            break
        prepass = extract_istd_anchors_only(config, istd_targets, raw_path)
        if prepass is None:
            continue
        anchors, _, _, _ = prepass
        for istd_label, anchor_rt in anchors.items():
            istd_rts_by_sample.setdefault(istd_label, {})[raw_path.stem] = anchor_rt

    scoring_context_factory = build_scoring_context_factory(
        config=config,
        injection_order=(
            resolved_injection_order
            if resolved_injection_order is not None
            else fallback_injection_order_from_mtime(raw_paths)
        ),
        istd_rts_by_sample=istd_rts_by_sample,
        rt_prior_library=resolved_rt_prior_library or {},
    )

    file_results: list[FileResult] = []
    diagnostics: list[DiagnosticRecord] = []
    total = len(raw_paths)

    for index, raw_path in enumerate(raw_paths, start=1):
        if should_stop is not None and should_stop():
            break

        raw_result = extract_raw_file_result(
            index,
            config,
            targets,
            raw_path,
            scoring_context_factory=scoring_context_factory,
        )
        file_results.append(raw_result.file_result)
        diagnostics.extend(raw_result.diagnostics)

        if progress_callback is not None:
            progress_callback(index, total, raw_path.name)
        if index % 50 == 0:
            gc.collect()

    return extractor.RunOutput(file_results=file_results, diagnostics=diagnostics)
