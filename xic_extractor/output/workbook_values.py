from __future__ import annotations

ND_ERROR = {"ND", "ERROR"}
_FORMULA_PREFIXES = ("=", "+", "-", "@")


def _safe_float(value: object) -> float | None:
    if not isinstance(value, str | int | float):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _excel_text(value: object) -> object:
    if not isinstance(value, str):
        return value
    if value.startswith(_FORMULA_PREFIXES):
        return "'" + value
    return value


def _nl_to_display(value: str) -> str:
    if value == "OK":
        return "✓"
    if value.startswith("WARN_"):
        return "⚠ " + value[5:]
    if value == "NL_FAIL":
        return "✗ NL"
    if value == "NO_MS2":
        return "— MS2"
    if value == "ND":
        return "✗"
    return value
