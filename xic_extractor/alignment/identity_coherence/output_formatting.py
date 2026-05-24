from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping
from enum import Enum


def project_columns(
    columns: tuple[str, ...],
    values: Mapping[str, object],
) -> dict[str, str]:
    return {column: format_tsv_value(values.get(column)) for column in columns}


def format_tsv_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        return f"{value:.12g}"
    if isinstance(value, tuple):
        return ";".join(format_tsv_value(item) for item in value)
    if isinstance(value, list):
        return ";".join(format_tsv_value(item) for item in value)
    if isinstance(value, set):
        return ";".join(format_tsv_value(item) for item in sorted(value))
    text = str(value)
    if text.startswith(("=", "+", "-", "@")):
        return f"'{text}"
    return text


def control_pass_is_true(value: object) -> bool:
    if value is True:
        return True
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return False


def enum_value(value: object) -> str:
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def counter_table(counter: Counter[str], label: str) -> list[str]:
    if not counter:
        return [
            f"| {label} | Count |",
            "| --- | ---: |",
            "| `none` | 0 |",
            "",
        ]
    return [
        f"| {label} | Count |",
        "| --- | ---: |",
        *[f"| `{key}` | {count} |" for key, count in sorted(counter.items())],
        "",
    ]
