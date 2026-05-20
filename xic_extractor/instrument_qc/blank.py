from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

BlankCapabilityStatus = Literal["supported", "unsupported"]


@dataclass(frozen=True)
class BlankTICBPCCapability:
    status: BlankCapabilityStatus
    tic_supported: bool
    bpc_supported: bool
    reason: str


def probe_blank_tic_bpc_capability(raw_source: object) -> BlankTICBPCCapability:
    """Check whether a RAW source exposes explicit TIC and BPC trace APIs."""
    tic_supported = callable(getattr(raw_source, "extract_tic", None))
    bpc_supported = callable(getattr(raw_source, "extract_bpc", None))
    if tic_supported and bpc_supported:
        return BlankTICBPCCapability(
            status="supported",
            tic_supported=True,
            bpc_supported=True,
            reason="RAW source exposes TIC and BPC extraction APIs.",
        )
    return BlankTICBPCCapability(
        status="unsupported",
        tic_supported=tic_supported,
        bpc_supported=bpc_supported,
        reason="RAW source does not expose explicit TIC/BPC extraction APIs.",
    )
