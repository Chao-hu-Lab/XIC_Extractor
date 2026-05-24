from __future__ import annotations

import re
from collections.abc import Iterable

_TAG_SPLIT_RE = re.compile(r"[;|,]")


def format_fragment_tags(tags: tuple[str, ...]) -> str:
    return ";".join(tags)


def has_fragment_tags(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Iterable):
        return any(str(item).strip() for item in value)
    return bool(str(value).strip())


def normalize_fragment_tags(value: object) -> tuple[tuple[str, ...], tuple[str, ...]]:
    flags: list[str] = []
    raw_parts: list[str] = []
    if value is None:
        return (), ()
    if isinstance(value, str):
        raw_parts.extend(_TAG_SPLIT_RE.split(value))
    elif isinstance(value, Iterable):
        for item in value:
            raw_parts.extend(_TAG_SPLIT_RE.split(str(item)))
    else:
        raw_parts.extend(_TAG_SPLIT_RE.split(str(value)))

    tags = tuple(sorted({part.strip() for part in raw_parts if part.strip()}))
    lowered: dict[str, set[str]] = {}
    for tag in tags:
        lowered.setdefault(tag.lower(), set()).add(tag)
    if any(len(variants) > 1 for variants in lowered.values()):
        flags.append("fragment_tag_case_variant_seen")
    return tags, tuple(flags)
