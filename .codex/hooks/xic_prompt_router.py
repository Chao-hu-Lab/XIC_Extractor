# ruff: noqa: E501
from __future__ import annotations

import json
import re
import sys

from xic_hook_policy import CONTROL_PLANE_PATH, HANDOFF_CURRENT_DIR

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bOPENAI_API_KEY\s*=\s*['\"]?[^'\"\s]+", re.IGNORECASE),
    re.compile(r"\b(?:api[_-]?key|token|password)\s*[:=]\s*['\"]?[^'\"\s]{12,}", re.IGNORECASE),
]

ARCHITECTURE_PATTERNS = [
    r"\bRAW\b",
    r"85\s*-?\s*RAW",
    r"8\s*-?\s*RAW",
    r"matrix",
    r"activation",
    r"value[\s_-]?delta",
    r"CID[\s_-]?NL",
    r"HCD[\s_-]?PI",
    r"Delta Mass",
    r"evidence",
    r"diagnostic",
    r"performance|perf|bottleneck|cache|batch",
    r"架構|效能|瓶頸|診斷|證據",
]

PR_REVIEW_PATTERNS = [
    r"\bPR\b",
    r"pull request",
    r"review",
    r"code review",
]

GOAL_PATTERNS = [
    r"\bgoal\b",
    r"\$goal-execution",
    r"設定.*goal",
    r"用.*goal",
    r"目標",
]

PRODUCTIZATION_PATTERNS = [
    r"producti[sz]e|producti[sz]ation",
    r"production[_\s-]?(surface|ready|candidate)",
    r"shadow_ready|diagnostic_only|maturity\s+tier",
    r"\bpromotion\b|\bpromote\b",
    r"method_manifest|review_roundtrip|sample_metadata_contract|alignment_output_contract",
    r"control\s+plane",
    r"產品化|推到產品|正式推|正式產品|正式功能|正式輸出|正式矩陣",
    r"成熟度|控制板|控制台",
]

HANDOFF_PATTERNS = [
    r"\bhandoff\b",
    r"worktree[-_\s]?report",
    r"context\s+(window|compaction)",
    r"\bcompaction\b",
    r"compact\s+context",
    r"long\s+pause",
    r"next\s+(agent|session)",
    r"收尾|交接|交接文檔|交接文件|下一個\s*(agent|session|會話)",
    r"壓縮|上下文|長會話|長暫停",
]


def emit(payload: dict[str, object]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    prompt = str(event.get("prompt", ""))
    if not prompt:
        return 0

    if any(pattern.search(prompt) for pattern in SECRET_PATTERNS):
        emit(
            {
                "decision": "block",
                "reason": "Prompt appears to include a secret-like value. Remove the secret and use environment variables or a secret manager.",
            }
        )
        return 0

    contexts: list[str] = []
    if any(re.search(pattern, prompt, re.IGNORECASE) for pattern in ARCHITECTURE_PATTERNS):
        contexts.append(
            "XIC high-risk work detected: before edits, use xic-architecture-preflight. "
            "Name existing owner/helper reuse, evidence-provider role, call-cost model, "
            "public contracts at risk, validation gate, and stop rule."
        )

    if any(re.search(pattern, prompt, re.IGNORECASE) for pattern in PR_REVIEW_PATTERNS):
        contexts.append(
            "XIC PR/review context detected: use xic-large-pr-review for large or diagnostics-heavy PRs. "
            "Start read-only, map blast radius, lead with findings, and label strongest evidence reviewed."
        )

    if any(re.search(pattern, prompt, re.IGNORECASE) for pattern in GOAL_PATTERNS):
        contexts.append(
            "XIC goal context detected: use the global goal-execution contract for phase-sized or drifting work. "
            "Keep one objective and name context, constraints, verification, done condition, stop rules, and handoff."
        )

    if any(re.search(pattern, prompt, re.IGNORECASE) for pattern in PRODUCTIZATION_PATTERNS):
        contexts.append(
            "XIC productization context detected: before claiming a feature is productized, read "
            f"{CONTROL_PLANE_PATH}. "
            "Name the current/proposed maturity tier and, if the tier or active lane changes, update the board "
            "or explicitly state why no control-plane update is needed."
        )

    if any(re.search(pattern, prompt, re.IGNORECASE) for pattern in HANDOFF_PATTERNS):
        contexts.append(
            "XIC handoff/closeout context detected: first resolve the active branch handoff from the goal, PR workflow, "
            f"or a branch-scoped file under {HANDOFF_CURRENT_DIR}<branch-slug>-<topic>.md. "
            "Do not default to another branch's handoff; only update an existing handoff when its Branch/status matches this work. "
            "Rewrite and prune that active snapshot when branch status, validation evidence, productization tier, or next action changed. "
            "Do not append chronological notes; keep only current objective/state, active decisions, validation, blockers, "
            "rejected paths still likely to recur, and next 1-3 actions. "
            "For PR closeout, condense the current handoff into the PR body and archive only completed phase summaries that must remain in repo. "
            "The global $handoff skill writes a temporary conversation handoff; it is not the repo branch handoff. "
            f"If productization tier or active lane changed, sync {CONTROL_PLANE_PATH} too. "
            "Hooks only remind; the executing agent owns the handoff rewrite."
        )

    if not contexts:
        return 0

    emit(
        {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": "\n".join(contexts),
            }
        }
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
