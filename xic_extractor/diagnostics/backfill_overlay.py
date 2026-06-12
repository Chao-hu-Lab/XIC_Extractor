from __future__ import annotations

from collections.abc import Mapping, Sequence

from xic_extractor.diagnostics.diagnostic_io import text_value


def selected_overlay_row(
    rows: Sequence[Mapping[str, str]],
    *,
    seed_group_id: str,
    support_verdict: str,
    allow_legacy_family_row: bool,
) -> Mapping[str, str]:
    if not rows:
        return {}
    seed_specific = [
        row
        for row in rows
        if text_value(row.get("seed_group_id")) == seed_group_id
    ]
    legacy_family_rows = [
        row for row in rows if not text_value(row.get("seed_group_id"))
    ]
    selected = seed_specific or (legacy_family_rows if allow_legacy_family_row else ())
    if not selected:
        return {}
    return sorted(
        selected,
        key=lambda row: overlay_verdict_sort_key(row, support_verdict=support_verdict),
    )[0]


def overlay_verdict_sort_key(
    row: Mapping[str, str],
    *,
    support_verdict: str,
) -> tuple[int, str]:
    verdict = text_value(row.get("family_verdict"))
    if verdict and verdict != support_verdict:
        return (0, verdict)
    if verdict == support_verdict:
        return (1, verdict)
    return (2, verdict)
