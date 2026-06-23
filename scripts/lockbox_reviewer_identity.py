"""Reviewer identity guardrails for lockbox truth labels."""

from __future__ import annotations

import re
from collections.abc import Sequence

_AGENTISH_EXACT_TOKENS = frozenset(
    {
        "agent",
        "assistant",
        "automated",
        "bot",
        "chatgpt",
        "claude",
        "codex",
        "llm",
        "subagent",
    },
)
_AI_CONTEXT_TOKENS = frozenset({"challenge", "qa", "review", "reviewer"})


def truth_label_reviewer_id_blocker(
    reviewer_id: str,
    allowed_human_truth_reviewer_ids: Sequence[str] = (),
) -> str | None:
    """Return a reason when ``reviewer_id`` looks like AI/challenge review.

    Agent/subagent review is useful QA, but it cannot satisfy the human truth
    reviewer slots used by the lockbox automation gate.
    """

    normalized = _normalize_reviewer_id(reviewer_id)
    if not normalized:
        return None
    allowed = {
        _normalize_reviewer_id(value)
        for value in allowed_human_truth_reviewer_ids
        if _normalize_reviewer_id(value)
    }
    if allowed and normalized not in allowed:
        return "reviewer_id is not in the allowed human truth reviewer registry"
    tokens = [token for token in re.split(r"[^a-z0-9]+", normalized) if token]
    token_set = set(tokens)
    if token_set & _AGENTISH_EXACT_TOKENS:
        return "agent/subagent reviewer IDs cannot satisfy human truth slots"
    if any(
        token.startswith(("agent", "bot", "gpt", "subagent", "codex"))
        for token in tokens
    ):
        return "model/subagent reviewer IDs cannot satisfy human truth slots"
    if "ai" in token_set and token_set & _AI_CONTEXT_TOKENS:
        return "AI challenge review must be stored outside human truth slots"
    return None


def allowed_human_truth_reviewer_ids_from_schema(schema: object) -> tuple[str, ...]:
    if not isinstance(schema, dict):
        return ()
    contract = schema.get("review_contract", {})
    if not isinstance(contract, dict):
        return ()
    allowed = contract.get("allowed_human_truth_reviewer_ids", [])
    if not isinstance(allowed, list):
        return ()
    return tuple(value for value in allowed if isinstance(value, str) and value)


def _normalize_reviewer_id(reviewer_id: str) -> str:
    return reviewer_id.strip().casefold()
