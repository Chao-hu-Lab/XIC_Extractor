# XIC Extractor Agent Contract

Repo-local rules for communication, code design, domain evidence, and
maintenance. Global Codex rules still apply. This file should stay short enough
to influence implementation choices.

For directory layout, file placement rules, and scratch directory hygiene, see
[`docs/project-layout.md`](docs/project-layout.md).
For stable local Python runners, Thermo RAW/DLL paths, and validation tiers, see
[`docs/agent-parameter-settings.md`](docs/agent-parameter-settings.md).

## Human Communication And Review Surfaces

- Non-trivial task wrap-ups must state a clear current verdict first: what is
  done, what is still blocked, and what the next recommended step is.
- Final answers for implementation or validation work should include, in this
  order when applicable: conclusion, changed files or artifact paths,
  verification run, remaining risk, and next action.
- Separate machine artifacts from human review surfaces. TSV/JSON are allowed to
  be exhaustive; Markdown plans/specs are primarily for agents; human-facing
  reports should be short, visual or indexed, and decision-oriented.
- When asking for manual review, provide a compact review index instead of a long
  raw table. Include the identifiers needed to find the row without extra lookup:
  sample, label or family id, m/z, RT/window, status, reason, and linked
  artifact path. Link the full TSV/JSON as supporting evidence only.
- HTML/XLSX reports should summarize the decision, top blockers, and next action
  before detailed tables. If a table is large, show top-ranked rows and provide a
  separate full export.
- Worktree or PR closeout should leave an operator-readable handoff: branch/task
  purpose, current verdict, important artifacts, validation commands/results, and
  explicit next-step recommendation.

## Execution Hygiene And Gates

- Before non-trivial edits, confirm the intended worktree, branch, and dirty diff
  scope. Classify unrelated dirty files, and do not stage, rewrite, or revert
  them unless explicitly requested.
- Before running commands that depend on Python environment, Thermo RAW files,
  DLLs, or common validation data, read `docs/agent-parameter-settings.md` and
  use its documented paths and runners. Task-specific artifacts belong in the
  active spec, plan, validation note, or output index, not in the long-lived
  agent settings file.
- Treat `docs/agent-parameter-settings.md` as maintained operational memory.
  After a RAW / validation run establishes a reusable command shape, or after a
  launch pattern repeatedly fails, update that file with the stable parameters,
  anti-pattern, and evidence note before repeating the workflow.
- Keep outputs organized under task-specific `output/` or `docs/superpowers/`
  paths. Do not drop diagnostic graphs, TSVs, notebooks, or one-off artifacts in
  the repo root. Every new diagnostic output group should have a summary or
  index that points to the detailed files.
- State validation status using explicit gate language: `diagnostic_only`,
  `shadow_ready`, `production_candidate`, `production_ready`, or `inconclusive`.
  Tests passing is not the same as production readiness.
- For extraction, alignment, scoring, and matrix behavior changes, report whether
  validation used synthetic tests only, 8-RAW, 85-RAW, targeted benchmark, or
  manual EIC review. If real-data validation was skipped, say why and mark the
  remaining risk.
- For long RAW / validation runs, preflight the exact command shape before
  launch: documented runner, sample set, output level, expected artifacts,
  heartbeat sidecars, timeout / stop condition, and whether existing artifacts
  can answer the question without rerunning. If a run stalls or exceeds the
  expected heartbeat, stop and inspect timing / profiling output instead of
  relaunching the same command.
- For alignment validation or downstream handoff, prefer
  `--output-level validation-minimal`: `alignment_matrix.tsv` is the downstream
  correction/statistics contract, while targeted benchmark diagnostics also need
  `alignment_review.tsv` and `alignment_cells.tsv`. Do not generate `.xlsx`,
  HTML, owner-edge, status-matrix, event-owner, or ambiguous-owner artifacts for
  large validation runs unless a human review or debug task explicitly needs
  them.
- Do not run 85-RAW validation by launching a background `Start-Process` from
  the Codex shell and then returning to poll it. That pattern has repeatedly
  failed in this environment. Use the foreground command shape documented in
  `docs/agent-parameter-settings.md` with heartbeat sidecars, or get explicit
  user approval for an external terminal / automation.
- Plans should separate `Now`, `Later`, and `Not in scope`, with checkpoint-level
  acceptance criteria and stop conditions. Do not let a plan imply production
  changes when the current phase is only audit, shadow, or validation.

## Planning And Evidence Budget

- Before a phase plan or expensive validation run, name the decision it can
  close, the strongest existing internal oracle, the missing independent
  evidence, expected runtime/artifacts, and the fail-fast or inconclusive path.
- Search `tools/diagnostics/INDEX.md`, relevant notes, and existing validation
  outputs before inventing a new workflow. Reuse them unless they cannot answer
  the current phase decision.
- Any `audit_only`, `shadow_only`, or `diagnostic_only` path needs an exit rule:
  promote, kill, externalize, or name the single missing evidence.
- Do not expand validation when the result cannot change the next action. Use
  the smallest confirmation plus rollback guard.

## Product Roadmap Discipline

- P-specs, C-specs, and implementation plans must state whether they advance
  `Trace` / `TraceGroup`, multi-source `PeakHypothesis`, `EvidenceVector`,
  `IntegrationResult`, model selection, or `AuditTrail`. If they advance none,
  label them cleanup-only and do not present them as modernization progress.
- Separate infrastructure existence from product behavior. Diagnostic TSVs,
  shadow reports, wrappers, and sidecars prove observability, not product
  usability.
- Prefer establishing the minimal future spine or dual-write contract before
  polishing legacy DTOs, resolver names, or scoring split points likely to move
  during handoff migration.
- CWT, WIS, local minima, curvature, derivative, and region-first logic are
  evidence or hypothesis sources. A phase touching them must declare one mode:
  audit-only, hypothesis enumeration, model-selection calibration, production
  candidate, or retirement.

## Validation Phase Types

- Science phase: require independent domain evidence capable of disproving false
  confidence. Median RSD alone is not enough.
- Cleanup phase: require numerical parity against the settled baseline; behavior
  changes relabel the phase.
- Engineering phase: require characterization parity and maintainability gain;
  do not bundle behavior changes.
- Documentation / diagnostic phase: require consistency and reviewer
  readability; no numerical gate language applies.

## Design Principles

- Make logic, dependencies, and data flow obvious.
- Prefer explicit interfaces over hidden coupling or global context.
- Keep one reason-to-change per module. Split by responsibility, not by fashion.
- Keep high-level domain behavior independent from IO, GUI, workbook rendering,
  process backends, and CLI wrappers.
- Use orchestration modules to coordinate focused submodules; do not let the
  orchestrator become the permanent home for every implementation detail.
- Add abstraction only when it reduces real coupling, duplication, or cognitive
  load. Avoid both monoliths and many tiny indistinguishable modules.
- Preserve public contracts unless an approved plan says otherwise.

## LC-MS/MS Evidence Rules

- Treat RT as contextual evidence, not a single hard identity veto. Large,
  reproducible, or unmodeled RT shifts may trigger ambiguity or confidence
  demotion, especially when inconsistent with biological ISTD transfer evidence,
  but RT alone must not prove analyte absence or override co-eluting,
  candidate-aligned MS1/MS2 evidence unless an explicit hard RT exclusion policy
  exists.
- For ISTDs, when a coherent evidence chain exists, such as aligned MS1 peak
  shape/area plus candidate-aligned NL/product/MS2/trace evidence, do not
  downgrade only because of RT prior, RT window, or centrality concerns. If this
  changes, add an explicit contract doc and regression tests.
- Treat missing DDA MS2/product/NL evidence as `not_observed` by default. Use it
  as negative evidence only when acquisition opportunity, local sensitivity,
  precursor selection or scan coverage, and comparable positive controls show
  that the evidence should have been observable.
- Product ions, neutral losses, adducts, and in-source fragments are candidate
  evidence only when co-eluting, boundary-aligned, and assigned to the same
  precursor or candidate. Shared class fragments or common neutral losses support
  class or substructure confidence, not analyte-specific proof by themselves.
- Prefer evidence chains over single-metric authority. CWT, WIS, iRT, local
  minima, RT models, and shape similarity are evidence inputs; none should
  silently overrule the selected peak or matrix identity by itself. Any evidence
  source that changes production behavior needs explicit config or contract,
  machine-readable reason/status fields, and regression tests.
- Keep source roles explicit when manifests, method docs, or target registries
  declare them:
  - SDO/LEK are dedicated clean standards and are expected only in their own
    standard samples.
  - MixSTDs are non-biological clean standards containing ISTDs and external
    standards.
  - Non-ISTD MixSTD targets are external standards; do not use them as required
    biological-sample anchors unless explicitly spiked or validated.
  - When biological samples receive ISTDs, those ISTDs are the primary transfer
    evidence for real-matrix RT/response behavior because they share the sample
    matrix, ion suppression/enhancement, RT drift, and sample-prep context.
- Clean standards can describe instrument behavior and support authentic
  reference checks, RT-aware preview, and audit or library work, but cannot alone
  justify production correction of biological matrices. Calibration-derived
  production RT/area/scoring/matrix gate changes require current-code biological
  transfer evidence, row-level coverage or exclusion policy, and machine-readable
  GO/NO-GO blockers.
- Keep audit and production gates separate. Extrapolated, sparse, missing, or
  low-coverage evidence stays review-only until an explicit production policy
  exists.
- When manual EIC/MS2 review contradicts a diagnostic label, investigate whether
  the shared evidence rule, diagnostic wording, or reviewed row is wrong. Fix the
  shared rule and add regression tests when the diagnostic logic is wrong; do not
  encode one-off sample or target exceptions as the primary solution.
- Targeted and untargeted workflows may use different priors and reporting, but
  shared evidence concepts such as traces, candidates, boundaries, regions,
  integration audit, and product/NL evidence should use common low-level models
  when this prevents schema drift. Do not force shared concrete implementations
  before the semantics match.
- Targeted outputs may serve as benchmarks, validation evidence, or shared
  low-level evidence, but must not leak target labels or targeted pass/fail logic
  into untargeted production matrix identity unless an approved contract says so.

## Architecture And Clean Code Rules

- Keep one reason to change per module. If code mixes setup, parsing, domain
  logic, diagnostics, rendering, and IO, split it or make the file an explicit
  orchestration facade.
- Preserve dependency direction. Domain algorithms may use arrays, config,
  typed context objects, and small models, but must not import GUI, workbook
  builders, CLI scripts, process backends, report renderers, or RAW/CSV adapters.
  IO/rendering/adapters depend inward on domain helpers.
- Public entry points and compatibility facades should stay thin. Move behavior
  into focused modules while keeping old imports working when they are public.
- Treat `tools/diagnostics/` as maintained product code. Diagnostic CLIs should
  parse, validate, and orchestrate only; reusable loading, classification,
  models, summaries, plotting, and writers belong in focused modules.
- Before any PR that adds, removes, or renames a CLI entry-point in
  `tools/diagnostics/`, read `tools/diagnostics/INDEX.md` and cite which
  existing entries were considered. Every PR that changes the set of
  entry-points must update `INDEX.md` in the same diff (Purpose, Topic
  group, Originating spec/plan for new entries; tombstone for retired
  ones). Full lifecycle rules live in
  `docs/superpowers/specs/2026-05-26-diagnostic-tool-lifecycle-spec.md`.
- Diagnostic writers render TSV/JSON/HTML/XLSX/plots only. They must not
  recompute domain evidence or re-scan RAW files; pass typed summaries from the
  code path where trace context already exists.
- Gate diagnostics must emit machine-readable status/reason fields plus a short
  human summary with the blocker and next action. Missing inputs, missing
  columns, stale artifacts, and unsupported schemas should name the expected
  file/column and how to regenerate or bypass the artifact.
- Optional diagnostics should use sidecar artifacts. Do not silently change
  established TSV/workbook schemas unless an approved contract says so.
- Shared dataclasses and protocols belong in small model/contract modules when
  they prevent circular imports or schema drift. Do not create shared concrete
  implementations before targeted/untargeted semantics actually match.
- Windows process mode must receive pickleable payloads only. Do not pass nested
  closures or non-pickleable factories across process boundaries.
- Move behavior before changing behavior. Do not mix structural refactors with
  scoring thresholds, peak selection rules, neutral-loss matching, or area
  integration changes.
- Add characterization tests before moving behavior that is not already covered.
  Tests should live in `tests/`, mirror the focused module, and prove behavior
  or public contracts with small deterministic fixtures before real RAW data.
- Separate real-data validation from normal unit tests. Use explicit validation
  scripts or fixture gates for RAW/workbook checks, and use 8-RAW validation for
  extraction/output refactors that can affect real workbook output.
- For output changes, pair narrow writer/sheet tests with a workbook or schema
  contract test. For process-mode changes, add a no-RAW spawn/pickling smoke
  test before raw-data benchmarking.
- Line count is a signal, not a hard rule. Pause when a module is near 500 lines
  and a change adds a responsibility, or near 800 lines and the change is not a
  local bug fix. Responsibility count matters more than exact length.

## CodeGraph Tooling Preference

- Prefer the `codegraph` CLI for CodeGraph-assisted repository inspection.
  Treat the CodeGraph MCP tools as a fallback when the CLI is unavailable,
  insufficient for the specific query, or explicitly requested.
- For subagent reviews, tell reviewers to avoid CodeGraph MCP by default. They
  should use `codegraph` CLI, `rg`, and targeted file reads unless MCP access is
  intentionally part of the task.

## Public Contracts

Treat these as public unless a plan explicitly changes them:

- CLI commands under `scripts/`
- `xic_extractor.extractor.run`
- `xic_extractor.signal_processing.find_peak_and_area`
- `scripts.csv_to_excel.run`
- config keys and example/default settings
- CSV schemas
- workbook sheet names, order, hidden states, and columns
- HTML report path naming
- run metadata keys

## Current Decomposition Targets

These modules are known maintainability targets:

- `scripts/csv_to_excel.py`: keep as CLI/import wrapper; move workbook logic to
  `xic_extractor/output/` modules.
- `xic_extractor/extractor.py`: keep as public extraction facade; move pipeline,
  backend, pre-pass, target extraction, anchor, drift, and output dispatch logic
  into `xic_extractor/extraction/`.
- `xic_extractor/signal_processing.py`: keep as compatibility facade; move
  models, resolver implementations, selection, recovery, integration, and trace
  quality into focused peak-detection modules.
- `xic_extractor/peak_scoring.py`: split scoring models, score component
  calculations, and selection helpers only after characterization tests pin
  current confidence/reason outputs.
- `xic_extractor/alignment/primary_consolidation.py`: add characterization tests
  before splitting graph construction, winner selection, cell merge, or loser
  audit helpers.

See:

- `docs/superpowers/specs/2026-05-06-workbook-and-extraction-module-decomposition-spec.md`
- `docs/superpowers/specs/2026-05-16-module-responsibility-inventory.md`
- `docs/superpowers/specs/2026-05-16-alignment-module-responsibility-contract.md`
