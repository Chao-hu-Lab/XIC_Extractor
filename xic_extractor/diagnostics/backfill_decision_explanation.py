from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class BackfillDecisionExplanation:
    decision: str
    reasons: tuple[str, ...]
    warnings: tuple[str, ...] = ()
    production_gap: str = ""

    @property
    def reason_text(self) -> str:
        return ";".join(self.reasons)

    @property
    def warning_text(self) -> str:
        return ";".join(self.warnings)


def decision_explanation(
    decision: str,
    reason: str | Sequence[str],
    *,
    warnings: Sequence[str] = (),
    production_gap: str = "",
) -> BackfillDecisionExplanation:
    reasons = (reason,) if isinstance(reason, str) else tuple(reason)
    return BackfillDecisionExplanation(
        decision=decision,
        reasons=reasons,
        warnings=tuple(warnings),
        production_gap=production_gap,
    )
