from __future__ import annotations

import json
import re
import sys


DESTRUCTIVE_COMMANDS = [
    (
        re.compile(r"\bgit\s+reset\s+--hard\b", re.IGNORECASE),
        "git reset --hard is blocked. Do not discard user work; inspect the diff and ask for explicit rollback approval.",
    ),
    (
        re.compile(r"\bgit\s+checkout\s+--\b", re.IGNORECASE),
        "git checkout -- is blocked because it reverts files. Use targeted review and explicit user approval.",
    ),
    (
        re.compile(r"\bgit\s+clean\s+-(?:[^\s]*f[^\s]*d|[^\s]*d[^\s]*f|x?fd|fxd)\b", re.IGNORECASE),
        "git clean with force/delete flags is blocked by the hook. Inspect untracked paths before deletion.",
    ),
]

RAW_BACKGROUND = re.compile(r"\bStart-Process\b.*(?:85\s*-?\s*RAW|\.raw\b|RAW-backed|preset)", re.IGNORECASE)
EXEC_CONFIG_PATHS = [
    "AGENTS.md",
    ".codex/hooks.json",
    ".codex/rules/",
    ".codex/hooks/",
    ".codex/agents/",
    "docs/agent/",
]


def emit(payload: dict[str, object]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))


def deny(reason: str) -> None:
    emit(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    )


def context(message: str) -> None:
    emit(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": message,
            }
        }
    )


def get_command(event: dict[str, object]) -> str:
    tool_input = event.get("tool_input")
    if isinstance(tool_input, dict):
        command = tool_input.get("command")
        if isinstance(command, str):
            return command
    return ""


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    command = get_command(event)
    if not command:
        return 0

    for pattern, reason in DESTRUCTIVE_COMMANDS:
        if pattern.search(command):
            deny(reason)
            return 0

    if RAW_BACKGROUND.search(command):
        deny(
            "Background RAW launch through Start-Process is blocked. Use the documented foreground heartbeat/timing command shape, or get explicit external-terminal approval."
        )
        return 0

    normalized = command.replace("\\", "/")
    if any(path.replace("\\", "/") in normalized for path in EXEC_CONFIG_PATHS):
        context(
            "Execution-affecting XIC agent config may be edited. After the change, run hook/script smoke checks, git diff --check, and a secret/local-path scan before closeout."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
