# Peak Pipeline Cleanup One-Goal Phase Contract Spec

**Date:** 2026-06-01
**Status:** Draft v0.1 - rules for a future one-goal cleanup execution
**Readiness label:** `diagnostic_only`
**Current-state input:** [Peak pipeline cleanup current-state reassessment](2026-06-01-peak-pipeline-cleanup-current-state-reassessment-spec.md)
**Related roadmaps:** [Technical debt and dead-code cleanup roadmap v2](2026-06-01-technical-debt-and-dead-code-cleanup-roadmap-v2-spec.md), [Peak pipeline cleanup roadmap overview](2026-05-24-peak-pipeline-cleanup-roadmap-overview-spec.md)
**2026-06-02 foundation closeout:** [C4 / C6 / Region foundation closeout](../notes/2026-06-02-c4-c6-region-foundation-closeout.md)

## Verdict

It is acceptable to execute the remaining peak-pipeline cleanup under one
runtime goal, but only if the goal is a sequence of bounded phases with separate
commit boundaries, review gates, and stop rules.

The goal must not be "clean up everything." It must be:

```text
bring the remaining peak-pipeline cleanup surfaces into a handoff-spine-aligned
state without changing selected peaks, areas, confidence, reason text, matrix
identity, or downstream TSV schemas unless a phase stops and opens a separate
behavior spec.
```

This spec is the contract that must exist before writing or executing that
goal.

## Source Priority

Future goal execution reads sources in this order:

1. `AGENTS.md`
2. `docs/agent-parameter-settings.md`
3. `docs/agent-subagent-routing.md`
4. this one-goal phase contract
5. [mature package flow reference](2026-06-02-mature-package-flow-reference-spec.md)
6. [current-state reassessment](2026-06-01-peak-pipeline-cleanup-current-state-reassessment-spec.md)
7. [technical-debt roadmap v2](2026-06-01-technical-debt-and-dead-code-cleanup-roadmap-v2-spec.md)
8. current C4/C6 design updates when the phase reaches those surfaces, if they
   have landed in the branch
9. older C2/C3/C4/C6 specs as historical rationale, file lists, and parity
   constraints only

If the old C-spec wording conflicts with this contract, this contract wins for
the next one-goal cleanup execution.

## Non-Negotiable Rules

- Do not reintroduce `linear_edge`.
- Do not reintroduce `arbitrated`.
- Do not delete `legacy_savgol`.
- Do not delete local-minimum internals.
- Do not promote or delete CWT without a pre-registered CWT evidence gate.
- Do not mechanically split `peak_scoring.py` just to reduce line count.
- Do not extract C6 generic grouping primitives before inventory and
  characterization prove shared semantics.
- Do not edit ignored runtime `config/settings.csv` in a PR unless the user
  explicitly asks to update this machine's local runtime config.
- Do not change selected peak, area, confidence, reason text, matrix identity,
  downstream TSV schema, workbook schema, or public config value set under the
  label "cleanup."

## Goal Shape

The future runtime goal should have one objective:

```text
Complete the remaining peak-pipeline cleanup foundation by aligning resolver
contracts, CWT evidence-role planning, handoff-spine migration planning,
scoring-decision design, and alignment-grouping characterization rules with the
current codebase, using one ordered phase sequence and one commit per phase.
```

The goal can include docs-only and narrow implementation phases, but every
phase must satisfy its own `DONE WHEN` and `VERIFY` before the next phase starts.
If one phase fails a stop rule, the goal pauses at that phase instead of
continuing into later cleanup.

## Phase Map

### Phase 0 - Spec Adoption And Stale-Wording Housekeeping

**Type:** docs-only / contract cleanup

Purpose:

- make this phase contract and the current-state reassessment visible from the
  canonical cleanup entrypoints;
- fix tracked stale wording that is already contradicted by completed
  retirements;
- avoid touching runtime-local ignored config.

Allowed changes:

- link this contract from the reassessment, v2 roadmap, and peak cleanup
  overview;
- clarify that `linear_edge` is retired and `baseline_integration_method`
  supports `asls` only on tracked example/docs surfaces;
- clarify that local `config/settings.csv` is ignored runtime state.

Forbidden changes:

- any code behavior change;
- any generated output schema change;
- editing ignored local runtime config unless explicitly requested.

DONE WHEN:

- canonical docs point to this phase contract;
- tracked stale `linear_edge` wording is either fixed or explicitly listed as a
  later Phase 1 contract surface;
- `git diff --check` passes.

VERIFY:

```powershell
rg -n "baseline_integration_method.*linear_edge|linear_edge.*baseline integration.*supported" README.md config\settings.example.csv docs\superpowers\specs
git diff --check
```

The `rg` command intentionally scans the tracked config example, not ignored
runtime `config/settings.csv`. It may still find historical retirement specs,
diagnostic truth-validation docs, and this command block. It must not find
current user-facing config wording that claims `linear_edge` is supported.

### Phase 1 - C2 Resolver Public-Surface Contract Cleanup

**Type:** contract cleanup with focused tests

Purpose:

- make resolver public surfaces explicit and consistent;
- preserve valid resolver behavior for accepted modes;
- fix unsupported programmatic resolver fallback if implemented in this phase.

Allowed changes:

- update README / config example wording to distinguish canonical settings
  default, accepted modes, and alignment production coercion;
- preserve `legacy_savgol`, `local_minimum`, and `region_first_safe_merge` as
  accepted values unless a separate migration contract exists;
- keep `ExtractionConfig.resolver_mode = "legacy_savgol"` only if it is
  documented as a programmatic compatibility default and covered by a test;
- change unknown programmatic resolver values to fail explicitly with an
  actionable error, provided accepted-mode behavior is unchanged;
- add focused config/facade/CLI/GUI tests for the touched surfaces.

Forbidden changes:

- deleting `legacy_savgol`;
- deleting local-minimum internals;
- renaming `region_first_safe_merge` without a public migration contract;
- changing selected peaks, areas, confidence, reason text, or TSV outputs for
  accepted resolver values.

DONE WHEN:

- README, settings schema/example, GUI choices, CLI defaults/coercion, facade
  handling, and `ExtractionConfig` default policy are classified as synchronized
  or intentionally divergent;
- validation harness defaults and accepted/rejected resolver modes are
  classified against the same public contract;
- retired `arbitrated` still fails fast;
- unsupported programmatic resolver fallback is either fixed or explicitly
  deferred with a test gap note;
- `ExtractionConfig.resolver_mode` default policy is covered by a focused test
  whether the default is kept or changed;
- focused tests cover every changed public surface.

VERIFY:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_config.py tests/test_validation_harness.py tests/test_signal_processing.py tests/test_signal_processing_selection.py tests/test_run_alignment.py tests/test_run_discovery.py tests/test_settings_section_advanced.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```

### Phase 2 - CWT Evidence-Role Inventory And Gate Spec

**Type:** diagnostic_only / docs-first

Purpose:

- decide what evidence role CWT should be tested for before any behavior
  change;
- prevent CWT from becoming permanent vague audit-only code;
- prevent expensive RAW validation that cannot change action.

Allowed changes:

- write or update a CWT evidence-role spec;
- inventory current CWT fields, labels, proposal sources, scoring points, cap
  interactions, and audit outputs;
- fill the pre-registered CWT gate table from the reassessment for exactly one
  tested role: apex proposal, width prior, ridge/persistence support, or
  shoulder/coelution proposal support.

Forbidden changes:

- changing CWT score points or cap rules;
- changing selected peaks, areas, confidence, or reason text;
- running 8RAW unless the tested role, comparator, artifacts, metrics, and
  promote / keep-audit / externalize-or-kill conditions are already written;
- calling CWT `production_ready`.

DONE WHEN:

- CWT is classified as one of: `promote_to_evidence_source`, `keep_audit_only`,
  `externalize_or_kill`, or `inconclusive_pending_named_evidence`;
- if no RAW run is justified, the spec says why and names the missing evidence;
- if a RAW run is justified, the exact command shape, artifacts, and stop
  condition are written before launch.

VERIFY:

```powershell
rg -n "cwt_same_apex_support|centwave_cwt|find_peaks_cwt|CWT" xic_extractor tests docs\superpowers
git diff --check
```

RAW validation, if authorized by the completed gate table, must use the
repo-local RAW validation rules and record `run_ok`, `gate_ok`,
`production_ready`, and `inconclusive`.

### Phase 3 - C3 Handoff-Spine Consumer Inventory And First Migration Slice

**Type:** inventory plus one parity-backed migration

Purpose:

- make `PeakHypothesis` / `EvidenceVector` / `IntegrationResult` / `AuditTrail`
  the surface future cleanup can target;
- avoid deleting legacy DTOs before consumer semantics are mapped.

Allowed changes:

- write a current-state consumer inventory for `PeakResult`, `PeakCandidate`,
  `PeakCandidatesResult`, `PeakDetectionResult`, `PeakCandidateScore`,
  `CommonEvidence`, `EvidenceSignalSet`, `PeakHypothesis`, `EvidenceVector`,
  `IntegrationResult`, and `AuditTrail`;
- classify each consumer as producer, reader, audit writer, public shim,
  compatibility adapter, or shared-evidence boundary;
- migrate one low-risk consumer to the handoff spine if parity can be proven by
  focused tests.

Recommended first consumer:

- candidate or boundary audit projection, because it is already partly
  hypothesis-aware and can be tested without changing production selection.

Forbidden changes:

- deleting `PeakCandidate` or `PeakDetectionResult`;
- breaking `xic_extractor.signal_processing` imports;
- changing public TSV column names or row values;
- using C3 to change resolver, scoring, area, or matrix behavior.

DONE WHEN:

- inventory exists and names the first migration target;
- one named current consumer or projection path is migrated and reduces one
  legacy DTO dependency, or the phase is explicitly closed as
  `diagnostic_only` because the spine lacks a named field;
- a `diagnostic_only` C3 closeout does not unlock C4 implementation work;
- public import compatibility is covered;
- candidate/boundary output parity is covered by focused tests or explicitly
  marked as requiring later 8RAW validation.

VERIFY:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_target_extraction.py tests/test_peak_candidate_table.py tests/test_peak_candidate_boundaries.py tests/test_signal_processing.py
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```

If the exact test files differ at implementation time, the phase note must name
the replacement tests and why they cover the same public projection surface.
If the migration touches shim, hypothesis, runtime spine, or shared-evidence
surfaces, include the relevant focused tests from:
`tests/test_peak_detection_module_boundaries.py`, `tests/test_peak_hypotheses.py`,
`tests/test_handoff_spine_runtime.py`, and `tests/test_evidence_semantics.py`.

### Phase 4 - C4 Evidence-Decision Design Spec

**Type:** docs-only design

Purpose:

- replace the stale "split `peak_scoring.py` into a package" framing with a
  design that separates evidence extraction, evidence interpretation, decision
  policy, and reason/audit projection.

Allowed changes:

- classify `peak_scoring.py` responsibilities;
- decide whether the future public import path remains
  `xic_extractor.peak_scoring`, becomes a package with a shim, or moves
  implementation under a differently named internal package;
- define characterization tests required before any split.

Forbidden changes:

- moving scorer code in this phase;
- changing score weights, confidence thresholds, cap rules, or reason text;
- introducing a package/module collision without a migration strategy.

DONE WHEN:

- C4 has a replacement design spec or the old C4 spec is marked superseded for
  implementation;
- each future split target has an owner, preserved public API, and parity test
  surface.

VERIFY:

```powershell
rg -n "from xic_extractor\.peak_scoring|import xic_extractor\.peak_scoring|score_candidate|select_candidate_with_confidence|score_breakdown_fields" xic_extractor tests scripts
git diff --check
```

### Phase 5 - C6 Alignment Grouping Characterization Spec

**Type:** docs-only / characterization planning

Purpose:

- prevent a broad grouping refactor from erasing alignment-specific semantics;
- identify the first safe C6 refactor slice only after golden parity surfaces
  are named.

Allowed changes:

- inventory grouping-like stages in `xic_extractor/alignment/`;
- classify each stage as generic grouping, identity/gate policy, review/audit
  policy, or matrix delivery;
- define the smallest characterization test/golden parity target for a future
  split.

Forbidden changes:

- extracting `group_by_tolerance`, `eject_and_reattach`, or `tie_break_sort`
  before the inventory proves shared semantics;
- changing alignment matrix/review/cells values;
- changing winner/loser, owner, primary/provisional, or review semantics.

DONE WHEN:

- C6 has a current-state characterization spec;
- a future implementation slice is either selected with parity surfaces or
  explicitly deferred.

VERIFY:

```powershell
rg -n "cluster|owner|primary|winner|loser|matrix_identity|fold|group" xic_extractor\alignment tests
git diff --check
```

## Commit Boundaries

The future one-goal execution should use one commit per completed phase:

1. docs: adopt peak cleanup one-goal phase contract
2. refactor/test/docs: align resolver public-surface contract
3. docs: define CWT evidence-role gate
4. refactor/test/docs or docs: advance C3 handoff-spine inventory/migration
5. docs: replace C4 with evidence-decision design
6. docs: characterize C6 alignment grouping semantics

If a phase is deferred by a stop rule, do not create a fake commit. Record the
blocker and stop the goal or ask the user whether to continue with later
docs-only phases.

## Review Requirements

Before the goal starts:

- `strategy-challenger` reviews the goal to ensure it is not an unbounded
  backlog;
- `implementation-contract-reviewer` reviews Phase 1 / Phase 3 public surfaces;
- `validation-evidence-reviewer` reviews Phase 2 if any RAW run is considered.

During execution:

- implementation phases get focused tests before moving on;
- docs-only design phases get at least local critical-artifact self-review;
- if the runtime exposes subagents and the user requests them, use the
  repo-local routing in `docs/agent-subagent-routing.md`.

## End-Of-Goal Verification

Run CI-equivalent gates before PR closeout or marking the PR ready:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x
```

If the goal ends after docs-only phases and no code/config/test behavior changed,
the final note may justify a docs-only smoke instead. If any Python source,
config loader, GUI, CLI, or test changed, run the CI-equivalent gate.

## Stop Rules

Stop the goal and write a separate behavior spec if any phase requires:

- selected peak changes;
- area changes;
- confidence or reason text changes;
- resolver default or accepted-value removal;
- CWT score/cap rule changes;
- matrix identity or alignment TSV value changes;
- workbook schema changes;
- 85RAW validation;
- a public breaking change to `signal_processing`, `peak_scoring`, config keys,
  CLI flags, or exported TSV/workbook columns.

Stop and ask the user if:

- the next phase is still possible but no longer advances the handoff spine;
- the phase would mostly produce speculative docs without closing a decision;
- a reviewer challenges the phase as preserving a stale architecture.

## Done When For The Future Goal

The future goal is complete only when:

- Phase 0 adoption is complete;
- Phase 1 resolver public-surface contract is synchronized or explicitly
  classified;
- Phase 2 CWT has a role/gate outcome or named missing evidence;
- Phase 3 has a current-state C3 inventory and either one parity-backed
  migration that reduces a named legacy DTO dependency, or a named spine field
  blocker recorded as `diagnostic_only` that does not unlock C4 implementation;
- Phase 4 has a C4 evidence-decision design that supersedes the stale package
  split;
- Phase 5 has a C6 characterization spec that prevents premature generic
  primitive extraction;
- every completed phase has its own commit-ready diff;
- verification evidence is recorded in the closeout note.
