from enum import StrEnum
from pathlib import Path


class InstrumentQCClass(StrEnum):
    SDOLEK = "SDOLEK"
    MIX_STDS = "MIX_STDS"
    BLANK = "BLANK"
    POOLED_QC = "POOLED_QC"
    UNKNOWN = "UNKNOWN"


def classify_instrument_qc_raw(
    raw_path: Path,
    data_root: Path,
) -> InstrumentQCClass | None:
    """Classify instrument-only RAW files from path context only."""
    try:
        relative_parts = raw_path.resolve().relative_to(data_root.resolve()).parts
    except ValueError:
        relative_parts = raw_path.parts

    folder_parts = [part.casefold() for part in relative_parts[:-1]]
    stem = raw_path.stem.strip().casefold()

    if any(part == "sdolek" for part in folder_parts):
        return InstrumentQCClass.SDOLEK
    if stem.startswith("sdolek") or stem.startswith("sdo"):
        return InstrumentQCClass.SDOLEK
    return None
