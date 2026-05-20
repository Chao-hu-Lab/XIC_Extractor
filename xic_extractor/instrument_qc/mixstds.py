from __future__ import annotations

import csv
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from xic_extractor.instrument_qc.classification import (
    InstrumentQCClass,
    classify_instrument_qc_raw,
)
from xic_extractor.instrument_qc.models import InstrumentQCDiagnostic
from xic_extractor.instrument_qc.targets import InstrumentQCTarget

MIXSTDS_TARGET_COLUMNS = (
    "compound",
    "precursor_mz",
    "rt_min",
    "rt_max",
    "ppm_tol",
)
XIC_TARGET_COLUMNS = ("label", "mz", "rt_min", "rt_max", "ppm_tol")


@dataclass(frozen=True)
class MixSTDSTargetRegistry:
    source: Path | None
    status: str
    reason: str
    targets: tuple[InstrumentQCTarget, ...]


def load_mixstds_target_registry(path: Path | None) -> MixSTDSTargetRegistry:
    """Load a reviewed instrument-QC Mix STDs target registry."""
    if path is None:
        return MixSTDSTargetRegistry(
            source=None,
            status="missing",
            reason="Mix STDs target registry was not supplied.",
            targets=(),
        )
    if not path.exists():
        return MixSTDSTargetRegistry(
            source=path,
            status="missing",
            reason=f"Mix STDs target registry does not exist: {path}",
            targets=(),
        )

    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        schema = _detect_target_schema(fieldnames)
        if schema is None:
            missing = [
                column
                for column in MIXSTDS_TARGET_COLUMNS
                if column not in fieldnames
            ]
            return MixSTDSTargetRegistry(
                source=path,
                status="invalid",
                reason=(
                    "Missing required Mix STDs target columns: "
                    + ", ".join(missing)
                ),
                targets=(),
            )
        targets = tuple(
            _target_from_row(row, schema=schema)
            for row in reader
            if _target_label(row, schema).strip()
        )
    reason = (
        "Loaded Mix STDs target registry."
        if targets
        else "Mix STDs target registry has no target rows."
    )
    return MixSTDSTargetRegistry(
        source=path,
        status="loaded" if targets else "empty",
        reason=reason,
        targets=targets,
    )


def discover_mixstds_raws(
    raw_dir: Path,
    diagnostics: list[InstrumentQCDiagnostic],
) -> tuple[Path, ...]:
    """Discover Mix STDs RAW files, preferring /STDs over /Pairs duplicates."""
    candidates = [
        path
        for folder in ("STDs", "Pairs")
        for path in sorted((raw_dir / folder).glob("*.raw"))
        if classify_instrument_qc_raw(path, raw_dir) == InstrumentQCClass.MIX_STDS
    ]
    selected: list[Path] = []
    selected_by_stem: dict[str, Path] = {}
    for path in sorted(candidates, key=_mixstds_sort_key):
        normalized_stem = path.stem.casefold()
        kept = selected_by_stem.get(normalized_stem)
        if kept is not None:
            diagnostics.append(
                InstrumentQCDiagnostic(
                    sample_name=path.stem,
                    raw_path=path,
                    issue="DUPLICATE_MIXSTDS_RAW_STEM",
                    detail=f"Duplicate Mix STDs RAW skipped: {path}; kept {kept}.",
                )
            )
            continue
        selected_by_stem[normalized_stem] = path
        selected.append(path)
    return tuple(selected)


def _detect_target_schema(fieldnames: Sequence[str]) -> str | None:
    if all(column in fieldnames for column in MIXSTDS_TARGET_COLUMNS):
        return "instrument_qc"
    if all(column in fieldnames for column in XIC_TARGET_COLUMNS):
        return "xic_targets"
    return None


def _target_label(row: dict[str, str], schema: str) -> str:
    if schema == "xic_targets":
        return row["label"].strip()
    return row["compound"].strip()


def _target_mz(row: dict[str, str], schema: str) -> float:
    if schema == "xic_targets":
        return float(row["mz"])
    return float(row["precursor_mz"])


def _target_from_row(row: dict[str, str], *, schema: str) -> InstrumentQCTarget:
    precursor_mz = _target_mz(row, schema)
    rt_min = float(row["rt_min"])
    rt_max = float(row["rt_max"])
    return InstrumentQCTarget(
        compound=_target_label(row, schema),
        precursor_mz=precursor_mz,
        reference_mz=precursor_mz,
        reference_rt_min=(rt_min + rt_max) / 2.0,
        reference_base_width_min=0.0,
        rt_min=rt_min,
        rt_max=rt_max,
        ppm_tol=float(row["ppm_tol"]),
    )


def _mixstds_sort_key(path: Path) -> tuple[int, str]:
    folder = path.parent.name.casefold()
    priority = 0 if folder == "stds" else 1
    return priority, path.stem.casefold()
