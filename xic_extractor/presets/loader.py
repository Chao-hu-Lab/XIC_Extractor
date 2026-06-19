from __future__ import annotations

import math
import tomllib
from collections.abc import Mapping
from importlib.resources import files
from pathlib import Path
from typing import Any, cast

from xic_extractor.presets.models import (
    SUPPORTED_COMBINE_MODES,
    SUPPORTED_STRATEGIES,
    CombineMode,
    Preset,
    PresetError,
    PresetTag,
)

_BUILTIN_PACKAGE = "xic_extractor.presets.data"
_BUILTIN_PRESETS = ("dna_dr",)

_TOP_LEVEL_KEYS = frozenset(
    {
        "name",
        "description",
        "combine_mode",
        "tag",
        "discovery",
        "alignment",
    }
)
_TAG_KEYS = frozenset({"strategy", "name", "value"})

DISCOVERY_TUNING_OVERRIDE_KEYS = frozenset(
    {
        "nl_tolerance_ppm",
        "precursor_mz_tolerance_ppm",
        "product_mz_tolerance_ppm",
        "product_search_ppm",
        "ms2_precursor_tol_da",
        "nl_min_intensity_ratio",
        "seed_rt_gap_min",
        "ms1_search_padding_min",
        "rt_min",
        "rt_max",
        "resolver_mode",
    }
)

ALIGNMENT_RUNTIME_OVERRIDE_KEYS = frozenset(
    {
        "standard_peak_backfill",
        "standard_peak_backfill_chunk_size",
        "standard_peak_backfill_publication_mode",
        "standard_peak_backfill_write_gallery",
        "standard_peak_backfill_reuse_existing",
        "standard_peak_backfill_min_shape_r",
    }
)


def list_presets() -> tuple[str, ...]:
    return _BUILTIN_PRESETS


def load_preset(name_or_path: str | Path) -> Preset:
    path = Path(name_or_path)
    if path.is_file():
        return _load_path(path)

    if path.exists():
        raise PresetError(f"preset file is not a file: {name_or_path}")

    if isinstance(name_or_path, Path):
        raise PresetError(f"preset file not found: {name_or_path}")

    if name_or_path.endswith(".toml"):
        raise PresetError(f"preset file not found: {name_or_path}")

    if name_or_path not in _BUILTIN_PRESETS:
        available = ", ".join(_BUILTIN_PRESETS)
        raise PresetError(
            f"unknown built-in preset {name_or_path!r}; "
            f"available built-in presets: {available}"
        )

    resource = files(_BUILTIN_PACKAGE).joinpath(f"{name_or_path}.toml")
    source = f"builtin:{name_or_path}"
    return _parse_toml(resource.read_bytes(), source=source)


def _load_path(path: Path) -> Preset:
    return _parse_toml(path.read_bytes(), source=str(path))


def _parse_toml(raw: bytes, *, source: str) -> Preset:
    try:
        parsed = tomllib.loads(raw.decode("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
        raise PresetError(f"{source}: invalid TOML: {exc}") from exc

    data = cast(Mapping[str, Any], parsed)
    _reject_unknown_keys(data, _TOP_LEVEL_KEYS, label="top-level")

    name = _required_string(data, "name")
    description = _required_string(data, "description")
    combine_mode_text = _required_string(data, "combine_mode")
    if combine_mode_text not in SUPPORTED_COMBINE_MODES:
        supported = ", ".join(sorted(SUPPORTED_COMBINE_MODES))
        raise PresetError(
            f"combine_mode {combine_mode_text!r} is not supported; "
            f"supported modes: {supported}"
        )
    combine_mode = cast(CombineMode, combine_mode_text)

    tags = _parse_tags(data.get("tag"))
    if combine_mode == "single" and len(tags) != 1:
        raise PresetError('combine_mode "single" requires exactly one tag')

    discovery_overrides = _parse_discovery_overrides(data.get("discovery"))
    alignment_overrides = _parse_alignment_overrides(data.get("alignment"))

    return Preset(
        name=name,
        description=description,
        tags=tags,
        combine_mode=combine_mode,
        discovery_overrides=discovery_overrides,
        alignment_overrides=alignment_overrides,
        source=source,
    )


def _reject_unknown_keys(
    table: Mapping[str, Any],
    allowed: frozenset[str],
    *,
    label: str,
) -> None:
    unknown = sorted(set(table) - allowed)
    if unknown:
        raise PresetError(f"unknown {label} key: {unknown[0]}")


def _required_string(table: Mapping[str, Any], key: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value.strip():
        raise PresetError(f"{key} must be a non-empty string")
    return value


def _parse_tags(value: Any) -> tuple[PresetTag, ...]:
    if not isinstance(value, list) or not value:
        raise PresetError("tag must be a non-empty [[tag]] list")

    tags: list[PresetTag] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, Mapping):
            raise PresetError(f"tag #{index} must be a table")
        tag_table = cast(Mapping[str, Any], item)
        _reject_unknown_keys(tag_table, _TAG_KEYS, label=f"tag #{index}")
        strategy = _required_string(tag_table, "strategy")
        tag_name = _required_string(tag_table, "name")
        tag_value = _parse_tag_value(tag_table.get("value"), tag_name=tag_name)

        if strategy not in SUPPORTED_STRATEGIES:
            supported = ", ".join(sorted(SUPPORTED_STRATEGIES))
            raise PresetError(
                f"tag {tag_name!r} uses unsupported strategy {strategy!r}; "
                f"supported strategies: {supported}"
            )

        tags.append(PresetTag(strategy=strategy, name=tag_name, value=tag_value))

    return tuple(tags)


def _parse_tag_value(value: Any, *, tag_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise PresetError(f"tag {tag_name!r} value must be a finite number")

    numeric_value = float(value)
    if not math.isfinite(numeric_value):
        raise PresetError(f"tag {tag_name!r} value must be a finite number")
    return numeric_value


def _parse_discovery_overrides(value: Any) -> dict[str, object]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise PresetError("[discovery] must be a table")

    table = cast(Mapping[str, Any], value)
    _reject_unknown_keys(
        table,
        DISCOVERY_TUNING_OVERRIDE_KEYS,
        label="[discovery]",
    )
    return dict(table)


def _parse_alignment_overrides(value: Any) -> dict[str, object]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise PresetError("[alignment] must be a table")

    table = cast(Mapping[str, Any], value)
    _reject_unknown_keys(
        table,
        ALIGNMENT_RUNTIME_OVERRIDE_KEYS,
        label="[alignment]",
    )
    return dict(table)
