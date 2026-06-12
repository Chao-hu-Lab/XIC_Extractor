from __future__ import annotations

from collections.abc import Mapping, Sequence

from xic_extractor.tabular_io import split_semicolon_labels, text_value


def has_semicolon_token(value: object, token: str) -> bool:
    return token in set(split_semicolon_labels(value))


def rows_by_family_sample_key(
    rows: Sequence[Mapping[str, str]],
    *,
    duplicate_label: str,
) -> dict[tuple[str, str], Mapping[str, str]]:
    by_key: dict[tuple[str, str], Mapping[str, str]] = {}
    for row in rows:
        family_id = text_value(row.get("feature_family_id"))
        sample_stem = text_value(row.get("sample_stem") or row.get("sample_id"))
        if family_id and sample_stem:
            key = (family_id, sample_stem)
            if key in by_key:
                raise ValueError(
                    f"duplicate {duplicate_label} key: {family_id}, {sample_stem}"
                )
            by_key[key] = row
    return by_key


def allowlist_rows_by_family_sample_key(
    rows: Sequence[Mapping[str, str]],
    *,
    expected_schema_version: str,
    schema_label: str,
    missing_label: str,
    duplicate_label: str,
) -> dict[tuple[str, str], Mapping[str, str]]:
    by_key: dict[tuple[str, str], Mapping[str, str]] = {}
    for row in rows:
        schema_version = text_value(row.get("schema_version"))
        if schema_version != expected_schema_version:
            raise ValueError(
                f"unsupported {schema_label} schema version: {schema_version!r}"
            )
        family_id = text_value(row.get("feature_family_id"))
        sample_stem = text_value(row.get("sample_stem"))
        if not family_id or not sample_stem:
            raise ValueError(
                f"{missing_label} allowlist rows require "
                "feature_family_id and sample_stem"
            )
        key = (family_id, sample_stem)
        if key in by_key:
            raise ValueError(
                f"duplicate {duplicate_label} key: {family_id}, {sample_stem}"
            )
        by_key[key] = row
    return by_key
