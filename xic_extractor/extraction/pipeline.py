from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.extraction.output_dispatch import write_outputs
from xic_extractor.injection_rolling import read_injection_order
from xic_extractor.raw_reader import RawReaderError, preflight_raw_reader
from xic_extractor.rt_prior_library import LibraryEntry, load_library

if TYPE_CHECKING:
    from xic_extractor.extractor import RunOutput


def resolve_injection_order(
    config: ExtractionConfig,
    raw_paths: list[Path],
    injection_order: dict[str, int] | None,
) -> dict[str, int] | None:
    if injection_order is not None:
        return injection_order
    if config.injection_order_source is not None:
        return read_injection_order(config.injection_order_source)
    if not raw_paths:
        return None
    return fallback_injection_order_from_mtime(raw_paths)


def resolve_rt_prior_library(
    config: ExtractionConfig,
    rt_prior_library: dict[tuple[str, str], LibraryEntry] | None,
) -> dict[tuple[str, str], LibraryEntry]:
    if rt_prior_library is not None:
        return rt_prior_library
    if config.rt_prior_library_path is None:
        return {}
    return load_library(config.rt_prior_library_path, config.config_hash)


def fallback_injection_order_from_mtime(raw_paths: list[Path]) -> dict[str, int]:
    ordered_paths = sorted(
        raw_paths,
        key=lambda path: (path.stat().st_mtime, path.name),
    )
    return {path.stem: index for index, path in enumerate(ordered_paths, start=1)}


def run_pipeline(
    config: ExtractionConfig,
    targets: list[Target],
    *,
    progress_callback: Callable[[int, int, str], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
    injection_order: dict[str, int] | None = None,
    rt_prior_library: dict[tuple[str, str], LibraryEntry] | None = None,
) -> RunOutput:
    reader_errors = preflight_raw_reader(config.dll_dir)
    if reader_errors:
        raise RawReaderError(" ".join(reader_errors))

    raw_paths = sorted(config.data_dir.glob("*.raw"))

    if config.parallel_mode == "process":
        from xic_extractor.extraction.process_backend import run_process

        output = run_process(
            config,
            targets,
            raw_paths=raw_paths,
            progress_callback=progress_callback,
            should_stop=should_stop,
            injection_order=injection_order,
            rt_prior_library=rt_prior_library,
        )
    else:
        from xic_extractor.extraction.serial_backend import run_serial

        output = run_serial(
            config,
            targets,
            raw_paths=raw_paths,
            progress_callback=progress_callback,
            should_stop=should_stop,
            injection_order=injection_order,
            rt_prior_library=rt_prior_library,
        )

    write_outputs(config, targets, output)
    return output
