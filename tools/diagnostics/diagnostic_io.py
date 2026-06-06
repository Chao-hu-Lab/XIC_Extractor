"""Compatibility shim for package-owned diagnostic IO helpers."""

from __future__ import annotations

from xic_extractor.diagnostics.diagnostic_io import (
    bool_value,
    format_diagnostic_value,
    optional_float,
    optional_int,
    read_delimited_rows,
    read_tsv_required,
    require_fields,
    required_float,
    required_indexes,
    split_semicolon_labels,
    text_value,
    write_delimited_rows,
    write_tsv,
)

__all__ = [
    "bool_value",
    "format_diagnostic_value",
    "optional_float",
    "optional_int",
    "read_delimited_rows",
    "read_tsv_required",
    "required_float",
    "required_indexes",
    "require_fields",
    "split_semicolon_labels",
    "text_value",
    "write_delimited_rows",
    "write_tsv",
]
