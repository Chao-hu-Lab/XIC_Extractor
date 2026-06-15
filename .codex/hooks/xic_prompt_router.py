# ruff: noqa: E501
from __future__ import annotations

import json
import re
import sys

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
            "XIC goal context detected: use xic-goal-execution for phase-sized or drifting work. "
            "Keep one objective and name context, constraints, verification, done condition, stop rules, and handoff."
        )

    if any(re.search(pattern, prompt, re.IGNORECASE) for pattern in PRODUCTIZATION_PATTERNS):
        contexts.append(
            "XIC productization context detected: before claiming a feature is productized, read "
            "docs/superpowers/plans/2026-06-15-productization-control-plane.md. "
            "Name the current/proposed maturity tier and, if the tier or active lane changes, update the board "
            "or explicitly state why no control-plane update is needed."
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
