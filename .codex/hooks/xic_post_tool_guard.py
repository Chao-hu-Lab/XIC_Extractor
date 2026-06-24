# ruff: noqa: E501
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

from xic_hook_policy import (
    CONTROL_PLANE_PATH,
    HANDOFF_MAX_LINES,
    HANDOFF_PATH,
    PRODUCT_SURFACE_PATHS,
    mentions_any_path,
    mentions_path,
    touches_control_plane,
    touches_handoff,
    touches_product_surface,
)

ZERO_TEST_PATTERNS = [
    re.compile(r"collected\s+0\s+items", re.IGNORECASE),
    re.compile(r"no\s+tests\s+ran", re.IGNORECASE),
    re.compile(r"ERROR:\s+not\s+found:", re.IGNORECASE),
]

LOCK_ERROR_PATTERNS = [
    re.compile(r"(?:fatal|error):.*(?:\.git[\\/]+index\.lock|index\.lock)", re.IGNORECASE | re.DOTALL),
    re.compile(r"(?:unable to create|could not create|file exists).*\.git[\\/]+index\.lock", re.IGNORECASE | re.DOTALL),
    re.compile(r"another git process.*(?:index\.lock|repository)", re.IGNORECASE | re.DOTALL),
    re.compile(r"(?:cannot|could not|failed to|unable to)\s+lock\s+ref", re.IGNORECASE),
]
GIT_COMMAND = re.compile(r"(?:^|[;&|()\r\n])\s*git(?:\.exe)?\s+", re.IGNORECASE)

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


def error_text_from_response(value: object) -> str:
    if isinstance(value, str):
        if re.search(r"Exit code:\s*0\b", value, re.IGNORECASE):
            return ""
        return value
    if isinstance(value, dict):
        parts: list[str] = []
        for key, item in value.items():
            key_text = str(key).lower()
            if key_text in {"stderr", "error", "error_message"} and isinstance(item, str):
                parts.append(item)
            elif isinstance(item, (dict, list)):
                nested = error_text_from_response(item)
                if nested:
                    parts.append(nested)
        return "\n".join(part for part in parts if part)
    if isinstance(value, list):
        return "\n".join(error_text_from_response(item) for item in value)
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


def is_git_lock_friction(command: str, response_text: str) -> bool:
    if not GIT_COMMAND.search(command):
        return False
    return any(pattern.search(response_text) for pattern in LOCK_ERROR_PATTERNS)


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
    # Fixture-only override for deterministic hook tests.
    override = os.environ.get("XIC_POST_TOOL_GUARD_CHANGED_PATHS_JSON")
    if override is not None:
        try:
            value = json.loads(override)
        except json.JSONDecodeError:
            return []
        if isinstance(value, list):
            return [str(item).replace("\\", "/") for item in value]
        return []

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
        if line.startswith("??"):
            continue
        path_text = line[3:].strip()
        if " -> " in path_text:
            path_text = path_text.split(" -> ", 1)[1].strip()
        if path_text:
            paths.append(path_text.replace("\\", "/"))
    return paths


def line_count(path: str) -> int | None:
    override = os.environ.get("XIC_POST_TOOL_GUARD_HANDOFF_LINE_COUNT")
    if override is not None:
        try:
            return int(override)
        except ValueError:
            return None
    try:
        with open(path, encoding="utf-8") as handle:
            return sum(1 for _ in handle)
    except OSError:
        return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    tool_input = event.get("tool_input")
    command = ""
    if isinstance(tool_input, dict) and isinstance(tool_input.get("command"), str):
        command = str(tool_input["command"])

    tool_response = event.get("tool_response")
    response_text = text_from_response(tool_response)
    error_text = error_text_from_response(tool_response)
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

    contexts: list[str] = []

    if is_git_lock_friction(command, error_text):
        contexts.append(
            "Git lock/ref-lock friction detected. Stop retrying the same shape; inspect the lock/ref state and use the documented Windows git recovery path."
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
        tool_mentions_handoff = mentions_path(
            tool_input_text,
            HANDOFF_PATH,
        )
        tool_mentions_managed_surface = (
            tool_mentions_product or tool_mentions_control_plane or tool_mentions_handoff
        )
        paths = (
            changed_paths(str(event.get("cwd", ".")))
            if tool_mentions_managed_surface
            else []
        )
        paths_touch_product = touches_product_surface(paths)
        paths_touch_control_plane = touches_control_plane(paths)
        paths_touch_handoff = touches_handoff(paths)
        worktree_needs_control_plane = paths_touch_product and not (
            paths_touch_control_plane or tool_mentions_control_plane
        )
        tool_needs_control_plane = tool_mentions_product and not tool_mentions_control_plane
        if tool_needs_control_plane or worktree_needs_control_plane:
            contexts.append(
                "Product/public surface changes are present, but the productization control plane "
                "is not changed. Before closeout, update "
                f"{CONTROL_PLANE_PATH} or explicitly "
                "state why this work does not change any maturity tier or active lane."
            )

        handoff_missing_from_tool = (
            tool_mentions_product or tool_mentions_control_plane
        ) and not tool_mentions_handoff
        handoff_missing_from_worktree = (
            paths_touch_product or paths_touch_control_plane
        ) and not (paths_touch_handoff or tool_mentions_handoff)
        if handoff_missing_from_tool or handoff_missing_from_worktree:
            contexts.append(
                "Product/control-plane state may have changed, but the plain-language handoff "
                "is not part of this update. Before closeout, rewrite and prune "
                f"{HANDOFF_PATH} as a current-state snapshot, or explicitly state why the handoff remains current."
            )

        should_check_handoff_size = (
            tool_mentions_managed_surface
            or paths_touch_product
            or paths_touch_control_plane
            or paths_touch_handoff
        )
        handoff_lines = (
            line_count(
                os.path.join(
                    repo_root(str(event.get("cwd", "."))),
                    HANDOFF_PATH,
                )
            )
            if should_check_handoff_size
            else None
        )
        if handoff_lines is not None and handoff_lines > HANDOFF_MAX_LINES:
            contexts.append(
                f"Active handoff is {handoff_lines} lines, above the {HANDOFF_MAX_LINES}-line target. "
                "Before continuing substantial implementation, rewrite it as a compact current-state snapshot; "
                "move completed phase summaries to archive and long logs to notes."
            )

    if contexts:
        emit(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": "\n".join(contexts),
                }
            }
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
