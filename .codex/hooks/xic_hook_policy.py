from __future__ import annotations

import re

CONTROL_PLANE_PATH = "docs/superpowers/plans/2026-06-15-productization-control-plane.md"
HANDOFF_CURRENT_DIR = "docs/superpowers/handoffs/current/"
PRODUCTIZATION_STATUS_HANDOFF_PATH = (
    "docs/superpowers/handoffs/current/cc-framework-improvements-productization.md"
)
HANDOFF_MAX_LINES = 200

PRODUCT_SURFACE_PATHS = [
    "README.md",
    "AGENTS.md",
    "docs/architecture-contract.md",
    "docs/agent/product-validation-contract.md",
    "docs/agent/architecture-public-contracts.md",
    "docs/superpowers/specs/",
    "docs/superpowers/plans/",
    "xic_extractor/extractor.py",
    "xic_extractor/signal_processing.py",
    "xic_extractor/output/",
    "xic_extractor/alignment/",
    "xic_extractor/extraction/",
    "xic_extractor/peak_detection/",
    "xic_extractor/configuration/",
    "xic_extractor/settings_schema.py",
    "scripts/",
    "gui/",
]


def normalize_path_text(text: str) -> str:
    normalized = text.replace("\\", "/")
    while "/./" in normalized:
        normalized = normalized.replace("/./", "/")
    return normalized


def path_match_text(text: str) -> str:
    normalized = normalize_path_text(text)
    return normalized.replace("../", "").replace("./", "")


def mentions_path(text: str, path: str) -> bool:
    normalized_path = normalize_path_text(path).lstrip("./")
    return normalized_path in path_match_text(text)


def mentions_any_path(text: str, paths: list[str]) -> bool:
    return any(mentions_path(text, path) for path in paths)


def path_is_under(path: str, root: str) -> bool:
    normalized_path = normalize_path_text(path).lstrip("./")
    normalized_root = normalize_path_text(root).lstrip("./")
    if normalized_root.endswith("/"):
        return normalized_path.startswith(normalized_root)
    return normalized_path == normalized_root


def touches_product_surface(paths: list[str]) -> bool:
    return any(
        path_is_under(path, root)
        for path in paths
        for root in PRODUCT_SURFACE_PATHS
    )


def touches_control_plane(paths: list[str]) -> bool:
    return any(path_is_under(path, CONTROL_PLANE_PATH) for path in paths)


def touches_handoff(paths: list[str]) -> bool:
    return any(path_is_under(path, HANDOFF_CURRENT_DIR) for path in paths)


def is_productization_status_handoff(path: str) -> bool:
    return path_is_under(path, PRODUCTIZATION_STATUS_HANDOFF_PATH)


def branch_slug(branch: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", branch.strip().lower()).strip("-")


def touched_handoff_paths(paths: list[str]) -> list[str]:
    return [
        normalize_path_text(path).lstrip("./")
        for path in paths
        if path_is_under(path, HANDOFF_CURRENT_DIR)
    ]
