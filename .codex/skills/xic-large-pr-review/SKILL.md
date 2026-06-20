---
name: xic-large-pr-review
description: XIC Extractor large-PR review overlay. Use this whenever the user asks to review an XIC PR, especially large diagnostics, architecture, clean-code, preset-performance, parity-gate, 8RAW/85RAW, matrix-only/deep-audit, activation, value-delta, matrix identity, or RAW-access locality PRs. This skill is read-only review, not PR closeout or merge workflow.
---

# XIC Large PR Review

Use after adopting normal code-review stance: findings first, ordered by
severity, with exact file and line references when findings exist.

This skill is read-only. Do not edit files, stage, push, update PRs, or merge
unless the user separately asks.

## Review Order

Build a blast-radius map instead of spreading attention evenly:

1. Shared helpers used by many writers or diagnostics.
2. Public contracts: CLI/config, TSV/CSV/workbook schemas, matrix identity,
   activation, value deltas, output paths.
3. Diagnostic architecture boundary between orchestration and reusable package
   logic.
4. RAW locality, batching, caching, fallback paths, and evidence availability.
5. Product-vs-diagnostic claims.
6. Focused tests, parity gates, and real-data evidence matching PR intent.

## Evidence Labels

State strongest evidence actually reviewed: `synthetic_only`, `focused_tests`,
`ci_green`, `8RAW_parity`, `85RAW_parity`, `targeted_benchmark`,
`manual_eic_ms2_review`, `diagnostic_only`, or `inconclusive`.

Do not treat 8RAW as proof of 85RAW readiness. Skipped 85RAW is residual risk,
not automatically a finding.

## Output Shape

```markdown
**Findings**

- [P1/P2/P3] <issue title> - <file:line>
  <why this can break behavior, schema, validation, or reviewability>

**Open Questions / Assumptions**
**Verification Reviewed**
**Residual Risk**
```

If no blocking issue exists, say so clearly. Do not invent findings.

## References

- Scope commands, blast-radius details, parity checks, and stop rules:
  `references/large-pr-review-contract.md`
- Trigger and near-neighbor cases:
  `evals/trigger-cases.md`
- Portable skill interface metadata:
  `agents/interface.yaml`
