# XIC Extractor Agent Contract

Repo-local rules for communication, validation, domain evidence, and code
boundaries. Global Codex rules still apply. Keep this file short enough to
influence every turn; move runbooks, roadmaps, and long contracts into docs.

Canonical references:

- Directory layout and scratch hygiene: [`docs/project-layout.md`](docs/project-layout.md)
- Python runners, Thermo RAW/DLL paths, validation tiers, and command shapes:
  [`docs/agent-parameter-settings.md`](docs/agent-parameter-settings.md)
- Known diagnostic conclusions: [`docs/diagnostic-ledger.md`](docs/diagnostic-ledger.md)
- Subagent roles, goal usage, and review routing:
  [`docs/agent-subagent-routing.md`](docs/agent-subagent-routing.md)
- LC-MS/MS domain evidence contract:
  [`docs/lcms-msms-evidence-rules.md`](docs/lcms-msms-evidence-rules.md)
- Architecture and decomposition contract:
  [`docs/architecture-contract.md`](docs/architecture-contract.md)
- Repo-local XIC overlay skills: [`.codex/skills`](.codex/skills), only when
  they add an execution checklist beyond the routing docs.

## Communication And Review Surfaces

- Non-trivial wrap-ups must state the current verdict first: what is done, what
  is still blocked, and the next recommended step.
- Use plain language before implementation detail. Say what changed, where,
  how it was checked, what was skipped, and what risk remains.
- Final answers for implementation or validation work should include, when
  applicable: conclusion, changed files or artifact paths, verification run,
  remaining risk, and next action.
- Separate machine artifacts from human review surfaces. TSV/JSON may be
  exhaustive; Markdown specs are mostly for agents; human-facing reports should
  be short, visual or indexed, and decision-oriented.
- Manual review requests should include a compact review index with identifiers:
  sample, label or family id, m/z, RT/window, status, reason, and linked
  artifact path.
- Worktree or PR closeout should leave an operator-readable handoff: branch/task
  purpose, verdict, important artifacts, validation commands/results, and an
  explicit next-step recommendation.

## Execution Gates

- Before non-trivial edits, confirm intended worktree, branch, and dirty diff
  scope. Do not stage, rewrite, or revert unrelated user changes.
- Before Python, RAW, DLL, or validation commands, read
  `docs/agent-parameter-settings.md` and use documented runners and paths.
- Keep outputs under task-specific `output/` or `docs/superpowers/` paths. New
  diagnostic output groups need a summary or index.
- State validation status explicitly: `diagnostic_only`, `shadow_ready`,
  `production_candidate`, `production_ready`, or `inconclusive`.
- Tests passing is not the same as production readiness. For extraction,
  alignment, scoring, and matrix behavior changes, report whether validation
  used synthetic tests, 8RAW, 85RAW, targeted benchmark, or manual EIC/MS2
  review.
- Do not launch 85RAW or likely long RAW runs through background
  `Start-Process` from the Codex shell. Use the foreground heartbeat/timing
  command shapes in `docs/agent-parameter-settings.md`, or get explicit approval
  for an external terminal or automation.
- Search `tools/diagnostics/INDEX.md`, relevant notes, and existing validation
  outputs before inventing a new diagnostic workflow.
- Search `docs/diagnostic-ledger.md` before rerunning known targets or failure
  modes.
- When sandbox, PowerShell syntax, output path, network approval, or RAW runner
  choice is uncertain, preflight with `python -m scripts.agent_sandbox_doctor`
  before launching expensive or permission-sensitive commands.
- Treat `.codex/config.toml`, hooks, execpolicy, and subagent TOML as
  execution-affecting config. Changes need docs/handoff review and a smoke
  check.
- Before staging docs/settings/config changes, scan the diff for secrets,
  private local paths, absolute machine-specific paths, and accidentally tracked
  local Codex config.

## PR Verification Gate

Before opening, updating, or marking a PR ready, run the CI-equivalent commands
from `.github/workflows/ci.yml` in the current worktree:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x
```

If a command fails because of real lint/type/test errors, fix the root cause and
rerun the failed gate. If it fails only because sandbox blocks dependency
resolution, executable spawn, or DLL loading, rerun the same command with
approval instead of substituting a narrower check. PR descriptions and closeout
notes must list exact commands and observed results.

## Planning And Review

- Before phase plans or expensive validation, name the decision the run can
  close, strongest existing oracle, missing independent evidence, expected
  runtime/artifacts, and fail-fast or inconclusive path.
- Any `audit_only`, `shadow_only`, or `diagnostic_only` path needs an exit rule:
  promote, kill, externalize, or name the single missing evidence.
- Do not expand validation when the result cannot change the next action.
- Use a goal-shaped contract for long-running, multi-step, cross-turn, or
  repeatedly drifting work. Goal contracts must point to canonical local
  surfaces, active specs/plans, and existing diagnostics or validation outputs.
- Non-trivial specs, plans, docs, workflow rules, and implementations need a
  critical-thinking review angle: strongest assumption, stale-artifact risk,
  cheaper existing oracle, or condition that would invalidate the path.
- When the user asks for subagent review, follow
  `docs/agent-subagent-routing.md`. Do not replace a requested multi-angle review
  with one generic reviewer unless a runtime limit blocks it and the bypass is
  reported.
- Repo-local execution subagents are opt-in. The main agent owns synthesis,
  edits, final judgment, and verification.
- Reusable workflows belong in global skills first. Repo-local `.codex/skills/`
  entries should exist only for XIC-specific checklists that cannot live cleanly
  in routing docs.

## Product And Validation Discipline

- P-specs, C-specs, and implementation plans must state whether they advance
  `Trace` / `TraceGroup`, multi-source `PeakHypothesis`, `EvidenceVector`,
  `IntegrationResult`, model selection, or `AuditTrail`. If they advance none,
  label them cleanup-only.
- Diagnostic TSVs, shadow reports, wrappers, and sidecars prove observability,
  not product usability.
- Prefer establishing the future spine or dual-write contract before polishing
  legacy DTOs, resolver names, or scoring split points likely to move during
  handoff migration.
- CWT, WIS, local minima, curvature, derivative, and region-first logic are
  evidence or hypothesis sources. A phase touching them must declare one mode:
  audit-only, hypothesis enumeration, model-selection calibration, production
  candidate, or retirement.
- Science phases require independent domain evidence capable of disproving false
  confidence. Median RSD alone is not enough.
- Cleanup phases require numerical parity against the settled baseline; behavior
  changes relabel the phase.
- Engineering phases require characterization parity and maintainability gain;
  do not bundle behavior changes.
- Documentation and diagnostic phases require consistency and reviewer
  readability; no numerical gate language applies.

## Domain Evidence Guardrails

Full contract: `docs/lcms-msms-evidence-rules.md`.

- Prefer evidence chains over single-metric authority. RT, CWT, WIS, iRT, local
  minima, RT models, shape similarity, product ions, neutral losses, adducts,
  and in-source fragments are evidence inputs, not silent vetoes.
- RT is contextual evidence. It must not prove analyte absence or override
  co-eluting, candidate-aligned MS1/MS2 evidence unless an explicit hard RT
  exclusion policy exists.
- Missing DDA MS2/product/NL evidence is `not_observed` by default. Treat it as
  negative evidence only when acquisition opportunity and comparable controls
  show it should have been observable.
- Clean standards can support audit, library, and instrument interpretation, but
  cannot alone justify production correction of biological matrices.
- Keep audit and production gates separate. Sparse, extrapolated, or low-coverage
  evidence stays review-only until a production policy exists.
- Targeted outputs may be benchmarks or shared low-level evidence, but target
  labels and targeted pass/fail logic must not leak into untargeted production
  matrix identity without an approved contract.

## Architecture Guardrails

Full contract: `docs/architecture-contract.md`.

- Preserve dependency direction. Domain logic must not import GUI, workbook
  builders, CLI scripts, process backends, report renderers, or RAW/CSV
  adapters.
- Keep public entry points and compatibility facades thin while moving behavior
  into focused modules.
- Treat `tools/diagnostics/` as maintained product-adjacent code. CLIs
  orchestrate; reusable loading, classification, models, summaries, plotting,
  and writers belong in package modules.
- Diagnostic writers render only. They must not recompute domain evidence or
  re-scan RAW files.
- Shared dataclasses and protocols belong in small model/contract modules when
  they prevent circular imports or schema drift.
- Move behavior before changing behavior. Add characterization tests before
  moving uncovered behavior.
- Separate real-data validation from normal unit tests.

## CodeGraph

- Prefer the `codegraph` CLI for broad indexed search, status, files, and
  context-building when it can answer the question cleanly.
- Use CodeGraph MCP when the query needs capabilities the CLI does not expose or
  exposes less clearly, especially caller/callee/impact tracing, single-symbol
  source lookup, or explicit MCP-requested structural context.
- For subagent reviews, tell reviewers to start with `codegraph` CLI, `rg`, and
  targeted file reads for simple no-use checks. Allow CodeGraph MCP when the
  review asks a structural caller/callee/impact question or CLI output is
  insufficient.

## Public Contracts

Treat these as public unless an approved plan explicitly changes them:

- CLI commands under `scripts/`
- `xic_extractor.extractor.run`
- `xic_extractor.signal_processing.find_peak_and_area`
- `scripts.csv_to_excel.run`
- config keys and example/default settings
- CSV schemas
- workbook sheet names, order, hidden states, and columns
- HTML report path naming
- run metadata keys
