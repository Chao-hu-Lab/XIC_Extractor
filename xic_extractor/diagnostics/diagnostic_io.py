"""Compatibility shim for diagnostic tabular helpers.

The canonical implementation lives in :mod:`xic_extractor.tabular_io` so domain
modules do not need to import through the diagnostics namespace.
"""

from __future__ import annotations

from xic_extractor.tabular_io import (
    bool_value,
    file_sha256,
    format_diagnostic_value,
    has_semicolon_token,
    numeric_equal,
    optional_float,
    optional_int,
    read_delimited_rows,
    read_tsv_required,
    require_fields,
    required_float,
    required_indexes,
    rows_by_text_field,
    split_semicolon_labels,
    text_value,
    write_delimited_rows,
    write_tsv,
)

__all__ = [
    "bool_value",
    "file_sha256",
    "format_diagnostic_value",
    "has_semicolon_token",
    "numeric_equal",
    "optional_float",
    "optional_int",
    "read_delimited_rows",
    "read_tsv_required",
    "require_fields",
    "required_float",
    "required_indexes",
    "rows_by_text_field",
    "split_semicolon_labels",
    "text_value",
    "write_delimited_rows",
    "write_tsv",
]
