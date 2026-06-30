from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tools.diagnostics.docs_management_audit import parse_yaml_frontmatter

ALWAYS_MANUAL_SUBDIRS = {"needs-merge", "needs-split", "needs-review"}


@dataclass(frozen=True)
class AutoAcceptDecision:
    action: str  # "auto_accept" | "manual_review" | "always_manual"
    reason: str


def parse_auto_accept_config(
    config_path: Path,
) -> tuple[set[str], float]:
    """Parse auto-accept settings from wiki config file.

    Returns (auto_accept_classes, min_confidence_threshold).
    """
    values: dict[str, str] = {}
    for line in config_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")

    raw_classes = values.get("WIKI_AUTO_ACCEPT_CLASSES", "")
    classes = {c.strip() for c in raw_classes.split(",") if c.strip()}

    try:
        threshold = float(values.get("WIKI_AUTO_ACCEPT_MIN_CONFIDENCE", "1.0"))
    except ValueError:
        threshold = 1.0

    return classes, threshold


def decide_auto_accept(
    doc_class: str,
    base_confidence: float,
    staging_subdir: str,
    auto_accept_classes: set[str],
    min_confidence: float,
) -> AutoAcceptDecision:
    """Decide whether a staged page can be auto-accepted."""
    if staging_subdir in ALWAYS_MANUAL_SUBDIRS:
        return AutoAcceptDecision(
            action="always_manual",
            reason=f"staging subdir '{staging_subdir}' requires manual review",
        )

    if not auto_accept_classes:
        return AutoAcceptDecision(
            action="manual_review",
            reason="no auto-accept classes configured",
        )

    if doc_class not in auto_accept_classes:
        return AutoAcceptDecision(
            action="manual_review",
            reason=f"doc class '{doc_class}' not in auto-accept list",
        )

    if base_confidence < min_confidence:
        return AutoAcceptDecision(
            action="manual_review",
            reason=(
                f"confidence {base_confidence:.2f} below"
                f" threshold {min_confidence:.2f}"
            ),
        )

    return AutoAcceptDecision(
        action="auto_accept",
        reason=(
            f"class '{doc_class}' in auto-accept list"
            f" and confidence {base_confidence:.2f} >= {min_confidence:.2f}"
        ),
    )


def extract_page_metadata(text: str) -> tuple[str, float]:
    """Extract doc_class and base_confidence from vault page frontmatter."""
    fm = parse_yaml_frontmatter(text)
    doc_class = fm.get("doc_class", "")
    try:
        confidence = float(fm.get("base_confidence", "0.0"))
    except ValueError:
        confidence = 0.0
    return doc_class, confidence
