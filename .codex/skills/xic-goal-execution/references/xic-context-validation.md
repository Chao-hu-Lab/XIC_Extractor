# XIC Context And Validation

Use this when an XIC goal touches code, validation, RAW, product evidence, or PR
readiness.

## Required Context

Every non-trivial XIC goal should read:

- `AGENTS.md`;
- `docs/agent-subagent-routing.md`;
- `docs/agent-parameter-settings.md` when Python, RAW, validation, DLLs, timing,
  output levels, or long-running commands are involved;
- active spec, plan, note, PR, diagnostic index, or validation output named by
  the user;
- existing artifacts under `output/` or `docs/superpowers/` before rerunning
  expensive validation.

## Constraints To Consider

- Preserve public contracts: CLI flags, config keys, TSV/workbook schemas,
  `alignment_matrix.tsv`, downstream handoff fields, and diagnostic marker maps.
- Distinguish `diagnostic_only`, `shadow_ready`, `production_candidate`,
  `production_ready`, and `inconclusive`.
- Do not treat wrapper/report/sidecar existence as product behavior.
- Do not run 85RAW through background `Start-Process` from the Codex shell.
- Do not generate large `.xlsx`, HTML, owner-edge, status-matrix, event-owner,
  or ambiguous-owner artifacts for validation unless explicitly needed.
- Do not let cleanup phases change production behavior unless the goal says so.
- Do not polish legacy DTOs when handoff productization is the goal unless it
  directly advances the spine contract.

## Verification Tiers

Name the strongest tier in `VERIFY` and final output:

- synthetic no-RAW tests;
- focused unit/contract tests;
- 8RAW validation;
- 85RAW validation;
- targeted benchmark;
- manual EIC/MS2 review;
- CI shard / GitHub checks.

If real-data validation is skipped, say why and what future evidence would close
the risk.

## RAW Stop Rules

Stop instead of guessing when:

- public schemas, workbook sheets, CLI/config keys, or `alignment_matrix.tsv`
  would change without a contract update;
- RAW runner paths, Thermo DLLs, or output levels are unclear;
- a long RAW run lacks heartbeat/timing sidecars or repeats a known failed
  launch pattern;
- the goal's gate cannot change the next action;
- reviewer findings contradict product direction and need a decision.
