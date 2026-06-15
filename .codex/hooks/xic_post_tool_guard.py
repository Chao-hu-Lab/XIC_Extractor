# ruff: noqa: E501
from __future__ import annotations

import json
import re
import subprocess
import sys

from xic_hook_policy import (
    CONTROL_PLANE_PATH,
    PRODUCT_SURFACE_PATHS,
    mentions_any_path,
    mentions_path,
    touches_control_plane,
    touches_product_surface,
)

ZERO_TEST_PATTERNS = [
    re.compile(r"collected\s+0\s+items", re.IGNORECASE),
    re.compile(r"no\s+tests\s+ran", re.IGNORECASE),
    re.compile(r"ERROR:\s+not\s+found:", re.IGNORECASE),
]

LOCK_PATTERNS = [
    re.compile(r"\.git[\\/]+index\.lock", re.IGNORECASE),
    re.compile(r"cannot lock ref", re.IGNORECASE),
]

WRITE_COMMAND = re.compile(
    r"\b(apply_patch|Set-Content|Add-Content|Out-File|New-Item|Move-Item|Remove-Item|Copy-Item|"
    r"python\s+-c|python\s+-m|uv\s+run\s+python|ruff\s+check\s+--fix)\b",
    re.IGNORECASE,
)


def emit(payload: dict[str, object]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))


def text_from_response(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        parts: list[str] = []
        for item in value.values():
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, (dict, list)):
                parts.append(text_from_response(item))
        return "\n".join(part for part in parts if part)
    if isinstance(value, list):
        return "\n".join(text_from_response(item) for item in value)
    return ""


def text_from_value(value: object) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return "\n".join(text_from_value(item) for item in value.values())
    if isinstance(value, list):
        return "\n".join(text_from_value(item) for item in value)
    return ""


def is_write_like(event: dict[str, object], command: str) -> bool:
    tool_name = str(event.get("tool_name", "")).lower()
    if any(name in tool_name for name in ("apply_patch", "edit", "write")):
        return True
    tool_input_text = text_from_value(event.get("tool_input"))
    return bool(WRITE_COMMAND.search(f"{command}\n{tool_input_text}"))


def repo_root(cwd: str) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd or ".",
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        return cwd or "."
    if result.returncode != 0:
        return cwd or "."
    return result.stdout.strip() or cwd or "."


def changed_paths(cwd: str) -> list[str]:
    root = repo_root(cwd)
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []

    paths: list[str] = []
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        path_text = line[3:].strip()
        if " -> " in path_text:
            path_text = path_text.split(" -> ", 1)[1].strip()
        if path_text:
            paths.append(path_text.replace("\\", "/"))
    return paths


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    tool_input = event.get("tool_input")
    command = ""
    if isinstance(tool_input, dict) and isinstance(tool_input.get("command"), str):
        command = str(tool_input["command"])

    response_text = text_from_response(event.get("tool_response"))
    combined = f"{command}\n{response_text}"

    if "pytest" in command.lower() and any(pattern.search(combined) for pattern in ZERO_TEST_PATTERNS):
        emit(
            {
                "decision": "block",
                "reason": "Pytest collected zero tests or used an invalid node id. Fix the target and rerun a meaningful test before treating this as validation.",
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": "XIC execution gate: guessed pytest node ids that collect zero tests are not validation.",
                },
            }
        )
        return 0

    if any(pattern.search(combined) for pattern in LOCK_PATTERNS):
        emit(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": "Git lock/ref-lock friction detected. Stop retrying the same shape; inspect the lock/ref state and use the documented Windows git recovery path.",
                }
            }
        )

    if is_write_like(event, command):
        tool_input_text = text_from_value(event.get("tool_input"))
        tool_mentions_product = mentions_any_path(
            tool_input_text,
            PRODUCT_SURFACE_PATHS,
        )
        tool_mentions_control_plane = mentions_path(
            tool_input_text,
            CONTROL_PLANE_PATH,
        )
        paths = changed_paths(str(event.get("cwd", ".")))
        worktree_needs_control_plane = touches_product_surface(paths) and not touches_control_plane(paths)
        tool_needs_control_plane = tool_mentions_product and not tool_mentions_control_plane
        if tool_needs_control_plane or worktree_needs_control_plane:
            emit(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PostToolUse",
                        "additionalContext": (
                            "Product/public surface changes are present, but the productization control plane "
                            "is not changed. Before closeout, update "
                            "docs/superpowers/plans/2026-06-15-productization-control-plane.md or explicitly "
                            "state why this work does not change any maturity tier or active lane."
                        ),
                    }
                }
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
