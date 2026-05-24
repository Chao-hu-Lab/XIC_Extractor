from __future__ import annotations

from typing import cast

from xic_extractor.instrument_qc.hcd_evidence import MS2Source, build_hcd_audit_row
from xic_extractor.instrument_qc.models import (
    ActivationMethod,
    HCDAuditRow,
    HCDProductIon,
    SDOLEKTrendRow,
)
from xic_extractor.instrument_qc.pipeline_contracts import XICSource


def append_hcd_audit_row(
    hcd_rows: list[HCDAuditRow],
    *,
    trend_row: SDOLEKTrendRow,
    raw: XICSource,
    products: tuple[HCDProductIon, ...],
    manifest_context: dict[str, tuple[str, ActivationMethod]],
    hcd_product_group: str | None,
    hcd_mapping_source: str,
    cid_neutral_loss_da: float | None,
) -> None:
    if not hasattr(raw, "iter_ms2_scans"):
        return
    instrument_method, activation_method = manifest_context.get(
        trend_row.sample_name,
        ("", "unknown"),
    )
    row = build_hcd_audit_row(
        trend_row=trend_row,
        raw=cast(MS2Source, raw),
        products=products,
        instrument_method=instrument_method,
        activation_method=activation_method,
        hcd_product_group=hcd_product_group,
        hcd_mapping_source=hcd_mapping_source,
        cid_neutral_loss_da=cid_neutral_loss_da,
    )
    if row is not None:
        hcd_rows.append(row)
