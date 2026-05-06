from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from xic_extractor.config import ExtractionConfig, Target
from xic_extractor.extraction.output_dispatch import write_outputs
from xic_extractor.raw_reader import RawReaderError, preflight_raw_reader
from xic_extractor.rt_prior_library import LibraryEntry

if TYPE_CHECKING:
    from xic_extractor.extractor import RunOutput


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

    if config.parallel_mode == "process":
        from xic_extractor.extraction.process_backend import run_process

        output = run_process(
            config,
            targets,
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
            progress_callback=progress_callback,
            should_stop=should_stop,
            injection_order=injection_order,
            rt_prior_library=rt_prior_library,
        )

    write_outputs(config, targets, output)
    return output
