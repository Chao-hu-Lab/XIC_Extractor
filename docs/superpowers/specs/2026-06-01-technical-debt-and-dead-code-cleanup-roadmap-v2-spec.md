# Technical Debt and Dead-Code Cleanup Roadmap v2

**Date:** 2026-06-01
**Status:** Execution closeout v1.8 - C4 projection closeout and C6 event-first retirement completed
**Related peak-pipeline chapter:** [Peak pipeline cleanup roadmap overview](2026-05-24-peak-pipeline-cleanup-roadmap-overview-spec.md)
**Current peak-pipeline reassessment:** [Peak pipeline cleanup current-state reassessment](2026-06-01-peak-pipeline-cleanup-current-state-reassessment-spec.md)
**One-goal execution contract:** [Peak pipeline cleanup one-goal phase contract](2026-06-01-peak-pipeline-cleanup-one-goal-phase-contract-spec.md)
**Related governance:** [Diagnostic tool lifecycle spec](2026-05-26-diagnostic-tool-lifecycle-spec.md)
**Mainline constraint:** [Product priority reset decision spec](2026-05-28-product-priority-reset-decision-spec.md)

## Verdict

The original peak-pipeline cleanup roadmap is still useful, but it is not a
repo-wide technical-debt inventory. Treat it as the peak-pipeline chapter of
this broader roadmap.

The next cleanup pass should not start by deleting code that merely looks old,
but it also must not leave overlapping legacy systems in place indefinitely.
The project-level cleanup principle is fusion-first modernization:

```text
new spine absorbs valid legacy concepts
  -> product invariants move to successor models and tests
  -> old paths become adapters / diagnostic-only / retired inputs
  -> implementation-specific legacy tests are deleted
  -> obsolete implementation is removed
```

The safer order is:

1. close or isolate in-flight behavior work;
2. fix package dependency direction where production/package code imports
   tool-only modules;
3. identify semantic overlap between old systems and the newer hypothesis /
   evidence / handoff spine;
4. migrate still-valid product invariants and tests into the successor spine;
5. promote, externalize, or retire maintained diagnostics according to
   lifecycle rules;
6. deprecate public compatibility modes before deleting them;
7. split oversized modules only behind characterization tests;
8. delete obsolete implementation and implementation-specific tests after the
   successor coverage and compatibility plan are in place.

C4 and C6 are the first pilot cases for this rule. They should be used to prove
the cleanup method before broadening it: identify the legacy concept, name the
newer successor semantics, decide whether the old path is still product policy,
then migrate tests and consumers before deleting code. After those pilots, run a
second repo-wide semantic-overlap inventory to find other designs that should be
merged, reduced to adapters, externalized as diagnostics, or retired.

The 2026-06-01 one-pass cleanup branch used this roadmap as the broader
cleanup chapter, then executed the explicitly authorized retirement slices for
`linear_edge` and `arbitrated` after their gates passed. This spec still does
not authorize additional behavior changes, broad schema changes, resolver
default changes, or deletion outside the named retirement phases.

Broad unaudited dead-code deletion is explicitly deferred. Active technical-debt
retirement is not deferred. If code is old but still preserves a unique product
invariant, keep or migrate it. If code overlaps with a newer, clearer spine,
make the migration explicit instead of maintaining two semantic systems.

## External Modernization Inputs

External modernization guidance supports this direction, with local adaptation:

- Martin Fowler's Strangler Fig description frames legacy modernization as a
  gradual movement of behavior from the old system into the new system, not a
  big-bang rewrite and not permanent dual maintenance:
  <https://martinfowler.com/bliki/StranglerFigApplication.html>
- Fowler's Branch by Abstraction describes using an abstraction layer so old and
  new implementations can coexist during replacement, then deleting the old
  supplier and possibly the temporary abstraction once migration completes:
  <https://www.martinfowler.com/bliki/BranchByAbstraction.html>
- Microsoft Azure's Strangler Fig pattern similarly recommends incrementally
  replacing functionality, reducing the legacy system's responsibilities, then
  decommissioning the old system and removing or narrowing the facade:
  <https://learn.microsoft.com/en-us/azure/architecture/patterns/strangler-fig>
- Kent C. Dodds' testing guidance is not repo-specific, but it matches the test
  cleanup rule here: tests that assert implementation details become brittle
  during refactors, while behavior-oriented tests protect the product contract:
  <https://kentcdodds.com/blog/testing-implementation-details>

These sources are design inputs, not product authority. XIC cleanup still needs
repo-local parity, public-surface, and scientific-evidence gates before behavior
changes.

## Fusion-First Modernization Rule

For any old subsystem that overlaps a newer model, evidence chain, or handoff
spine, classify the relationship before cleanup:

| Relationship | Meaning | Required action |
|---|---|---|
| `unique_invariant` | Old subsystem protects a product invariant the successor does not yet express. | Keep it or migrate the invariant first. Do not delete. |
| `successor_overlap` | New spine expresses the same or better semantic concept, but consumers/tests still depend on the old path. | Write a migration slice: map invariants, port tests, keep temporary adapters, then retire old implementation. |
| `adapter_only` | Old path only preserves public import/config/CLI/schema compatibility. | Keep a thin adapter with an exit rule, warning/rejection behavior, and deletion condition. |
| `diagnostic_only` | Old path only supports investigation or evidence review. | Keep under diagnostic lifecycle, externalize, or retire with replacement evidence. |
| `obsolete_implementation_detail` | Old tests or helpers assert mechanics no longer tied to product behavior. | Delete after successor invariant coverage or no-contract evidence is recorded. |

Default posture is `successor_overlap`, not `keep forever`, whenever a newer
spine plausibly covers the same semantics. Preservation requires a named
independent invariant.

### Test Migration Rule

Legacy tests are not protected assets. They are useful only when they protect a
current product invariant, public compatibility behavior, or diagnostic contract.

For migration/fusion work:

1. Identify the invariant behind each legacy test.
2. Port still-valid invariants to successor tests, public output parity tests,
   or compatibility tests.
3. Delete tests that only assert legacy implementation mechanics.
4. Keep compatibility tests only while the compatibility surface exists.
5. Remove compatibility tests with the shim or public mode when the retirement
   lands.

## C4/C6 Pilot And Follow-Up Inventory

C4 and C6 are demonstration cases, not one-off exceptions.

- C4 tests whether legacy peak scoring responsibilities should survive as
  production decision policy, move into `EvidenceVector` / `CommonEvidence` /
  `PeakHypothesis`, or shrink into compatibility projection.
- C6 tests whether legacy alignment grouping and owner-family concepts still
  define product structure, or whether newer trace/hypothesis/evidence-chain
  semantics have absorbed enough of their job to migrate or retire them.

The first concrete pilot inventory is now captured in:

- [C4 peak scoring evidence-decision design](2026-06-01-c4-peak-scoring-evidence-decision-design.md):
  scorer evidence projection overlaps the successor spine, but
  selection/confidence policy remains active. The C4-1 field map now separates
  successor-owned projection fields from missing successor facts and active
  scorer policy.
- [C6 alignment stage semantics design](2026-06-01-c6-alignment-stage-semantics-value-assessment-design.md):
  event-first alignment is the strongest retirement/compatibility candidate,
  while owner-first construction, claim arbitration, consolidation, matrix
  identity, and production projection remain active stages. The C6-EF audit now
  records no-use evidence for the event-first wrapper and defines a
  reviewed public-retirement path for `cluster_candidates` and
  `backfill_alignment_matrix`. The first execution slice removed the private
  `_build_event_first_matrix(...)` wrapper and made the package-level public
  event-first imports explicit compatibility shims. The follow-up C6-B slice
  then removed the non-public event-family helper path
  (`feature_family.py`, `family_integration.py`) and its implementation-only
  tests after invariant triage. The public-shim slice then removed
  `clustering.py`, `backfill.py`, the package-level `cluster_candidates` /
  `backfill_alignment_matrix` exports, and their implementation-only tests after
  CodeGraph MCP impact/caller checks found no product, script, diagnostic, or
  package consumer.

The follow-up inventory should use the same unit of analysis for every candidate
design:

| Field | Required question |
|---|---|
| Legacy design | What old module, mode, helper, config path, or test family are we judging? |
| Product invariant | What user-visible, scientific, matrix, diagnostic, or public-contract behavior does it protect? |
| Successor candidate | Which newer model or spine could own the same concept: `Trace`, `TraceGroup`, `PeakHypothesis`, `EvidenceVector`, `IntegrationResult`, model selection, `AuditTrail`, output contract, or diagnostic lifecycle? |
| Consumer surface | Who still imports, configures, calls, or reads the old path? Include tests only after naming the product behavior they protect. |
| Relationship | `unique_invariant`, `successor_overlap`, `adapter_only`, `diagnostic_only`, or `obsolete_implementation_detail`. |
| Migration action | Port invariant, keep active policy, create compatibility adapter, externalize diagnostic, or retire. |
| Exit rule | The exact test, parity oracle, public migration, or no-consumer evidence that allows deletion or reclassification. |

This inventory is not a dead-code hunt. It is a maintainability pass that asks
where the project is still carrying two semantic systems for one product job.
If a legacy design has a real invariant, preserve that invariant. If the newer
spine already covers it, migrate the invariant and delete the old mechanics.

## 2026-06-01 Cleanup-Retirement Closeout

The branch `codex/cleanup-retirement-foundation` completed the following scoped
cleanup/retirement work under
`docs/superpowers/plans/2026-06-01-cleanup-retirement-one-pass-goal.md`:

- R1 package dependency-direction cleanup: shared diagnostic IO now lives at
  `xic_extractor/diagnostics/diagnostic_io.py`; `tools/diagnostics/diagnostic_io.py`
  is a compatibility shim.
- R2 index/lifecycle refresh: `tools/diagnostics/INDEX.md` records the current
  entry-point count and shared-infrastructure owner.
- C1a baseline relocation: `asls_baseline` lives in
  `xic_extractor/peak_detection/baseline.py`; `xic_extractor/baseline.py`
  remains a compatibility re-export.
- C5 integration entry closeout: production integration calls use the
  consolidated integration path documented by the C5 closeout note.
- C1b linear-edge retirement: production/config/CLI selector behavior no longer
  accepts `linear_edge`; old inputs fail with a migration message, the accepted
  cell-integration audit schema no longer emits linear-edge rollback columns,
  and historical diagnostics retain only legacy comparison readers.
- C2 partial resolver collapse: the experimental `arbitrated` resolver mode is
  retired and rejected with a migration message. `legacy_savgol`,
  `local_minimum`, and the public `region_first_safe_merge` compatibility name
  remain accepted pending a separate C2 follow-up.

Broad dead-code deletion, `legacy_savgol` demotion, CWT retirement, resolver
renaming, C3/C4/C6 structural work, and large active-module splits remain out of
scope for this closeout. After user calibration and current-code review, the
current-state reassessment supersedes any older wording that treats
`legacy_savgol` or CWT as straightforward deletion targets.

## Review Disposition

Subagent review, follow-up inventory, and user calibration changed this draft in
five ways:

- R1 is confirmed as a real ownership-boundary issue, not a claim that the main
  pipeline must ignore diagnostic evidence. Diagnostic evidence can be product
  evidence; reusable evidence/IO contracts need a product-owned canonical path,
  while `tools/diagnostics/` remains the CLI/report wrapper surface.
- R1 is still the first implementation candidate if we choose to clean this
  boundary, but the canonical helper path, compatibility shim, lifecycle
  wording, and `INDEX.md` guidance must be fixed together.
- R2 must not promote a broad topic group by proximity. Each gate needs its own
  gate id, decision target, exit status/code contract, and frozen schema before
  it moves toward `GATED`.
- `arbitrated` and `linear_edge` were retirement-directed, not undecided legacy
  options. The one-pass cleanup branch completed their scoped retirements after
  migration/gate sequencing; remaining references are historical docs,
  rejection tests, migration messages, or legacy diagnostic readers.
- Low textual reference count, large file size, old names, and temporary product
  policies are not deletion evidence.

## Why This Exists

The 2026-05-24 cleanup roadmap focused on C1-C6 peak-pipeline structure:
baseline placement, resolver collapse, integration entry consolidation,
hypothesis model unification, `peak_scoring.py` split, and alignment grouping
consolidation. That leaves several active debt classes outside the C-spec set:

- diagnostic lifecycle and gate placement;
- package-to-tools import direction;
- dormant but still public compatibility modes;
- oversized diagnostic/productization modules;
- test and report files that are large because they are frozen contract
  surfaces;
- historical scripts that are validation tools, not production entry points.

The 2026-05-26 diagnostic lifecycle audit also showed that "no obvious caller"
is a weak deletion oracle in this repo. An initial retired-candidate list was
retracted after strict docs/test/schema review. Future deletion work must use a
stricter classification.

## Current Evidence Snapshot

Evidence from the 2026-06-01 scan:

- CodeGraph is initialized and current for this repo: 703 files, 13,817 nodes,
  and 32,639 edges.
- Phase 2 refreshed `tools/diagnostics/INDEX.md` to 48 entry-point headings and
  130 top-level Python files, counted from the catalog headings and
  `tools/diagnostics/*.py`.
- `xic_extractor/diagnostics/` now contains runtime timing helpers plus the
  package-owned `diagnostic_io.py` shared infrastructure carveout; gate
  placement remains underused.
- Several `xic_extractor/alignment/shared_peak_identity_explanation/*` modules
  import `tools.diagnostics.diagnostic_io`. That is acceptable as a temporary
  user-authorized evidence bridge, but long-term shared evidence/IO contracts
  should not live only under a tool-only namespace.
- No tracked `scripts/*.ps1` extraction script remains; the old PowerShell
  extraction deletion from the area-support plan is not a current cleanup item.
- `arbitrated`, `legacy_savgol`, and `linear_edge` were not simple dead code:
  they had public config/test/diagnostic or retirement-gate semantics. The
  current state is that `arbitrated` and `linear_edge` are retired public inputs,
  while `legacy_savgol` remains an accepted clean-trace / compatibility path
  unless a later public migration contract changes that surface.
- The largest current line-pressure targets include:
  `shared_peak_identity_explanation/machine_evidence_support.py`,
  `shared_peak_identity_explanation/schema.py`,
  `shared_peak_identity_explanation/peak_hypothesis_matrix.py`,
  `alignment/process_backend.py`, `alignment/production_candidate_gate.py`,
  `alignment/pipeline.py`, `alignment/owner_backfill.py`,
  `alignment/primary_consolidation.py`, `peak_scoring.py`,
  `tools/diagnostics/asls_truth_validation_inputs.py`, and large contract tests.

This snapshot is planning evidence only. Re-run targeted scans before any
implementation PR.

## Classification States

Every cleanup candidate must be classified before implementation.

| State | Meaning | Allowed action |
|---|---|---|
| `delete_now` | No public contract, no production/package/script caller, no current docs reference, no frozen-schema test, and no active lifecycle state. | Delete in a narrow PR with caller/docs/test scan evidence. |
| `deprecate_first` | Public config, CLI, GUI, docs, or test fixtures still mention it, but it is no longer a preferred path. | Add deprecation/migration behavior first; delete only in a later PR. |
| `move_only` | Code is useful but lives at the wrong layer or import direction. | Move with compatibility shim and no behavior/schema change. |
| `split_only` | Code is active but too broad or oversized. | Split after characterization tests pin behavior and public output. |
| `retire_planned` | Product direction is settled toward retirement, but public config, rollback evidence, selected values, or tests still need a sequenced migration. | Deprecate or gate first; delete only in the PR named by the retirement spec. |
| `semantic_migration` | A newer model/evidence spine should absorb the old subsystem's valid concepts, but live consumers or tests still depend on the old path. | Port product invariants and tests to the successor, keep temporary adapter if needed, then retire old implementation. |
| `adapter_only` | The old path only exists for public import/config/CLI/schema compatibility. | Keep thin compatibility behavior with an exit rule; do not add new product behavior here. |
| `obsolete_test_or_helper` | A test/helper asserts implementation mechanics that no longer correspond to a product invariant. | Delete after successor coverage or no-contract evidence is recorded. |
| `diagnostic_lifecycle` | Tool belongs to candidate/active/gated/retired diagnostic lifecycle review. | Promote, keep, externalize, or retire according to lifecycle spec. |
| `blocked_by_product_decision` | Deletion would settle behavior, selected peaks, area values, matrix identity, or downstream contracts. | Do not cleanup until the product decision lands. |

Ambiguous candidates default to `deprecate_first`, `move_only`, or
`semantic_migration`, not `delete_now`.

## Candidate Inventory

| Candidate | Current classification | Rationale | Next action |
|---|---|---|---|
| `tools.diagnostics.diagnostic_io` imported by package modules | `move_only` | Shared IO helpers are active and may support product evidence, but their canonical owner should not be only `tools.*`. | Move shared helpers to a package-owned canonical module if this boundary cleanup is accepted, leave `tools/diagnostics/diagnostic_io.py` as a shim, update lifecycle/INDEX wording, and add canonical plus shim import/schema tests. |
| `xic_extractor/diagnostics/` package path | `diagnostic_lifecycle` | Only `timing.py` lives there, while the lifecycle spec reserves this namespace for `GATED` diagnostics. | Use this path for gates only, or explicitly carve out schema-neutral shared infrastructure before moving generic IO helpers there. |
| Phase gate tools such as P1/P2/P2b/P7 evidence gates | `diagnostic_lifecycle` | Lifecycle spec identifies promotion candidates, but several related tools are still `diagnostic_only`, sidecar-only, or human-triggered active tools. | Promote one individually gated group per PR only after it has a gate id, decision target, exit status/code contract, and frozen schema; preserve CLI shims. |
| Backfill review trio (`seed_aware`, `family_ms1`, `low_ms1_coverage`) | `diagnostic_lifecycle` + `split_only` | They may be orthogonal review axes or redundant views; prior audit says spec first. | Write an axis-semantics spec before consolidation. |
| `arbitrated` resolver mode | retired in Phase 8 | It was an experimental resolver. The one-shot 8RAW comparison did not show a material advantage over the supported conservative path, and public config/CLI/GUI/tests now reject it with a migration message. | Keep historical docs/tests only as migration evidence; future C2 work should focus on `legacy_savgol`, `local_minimum`, CWT evidence, and resolver naming. |
| `legacy_savgol` top-level resolver mode | keep / contract cleanup | User calibration says it still performs well for normal clean peaks. The issue is complex-matrix robustness, not that the SG path is dead. | Keep the mode or explicitly classify it as compatibility/advanced through C2; do not demote, alias, or delete it without a public migration contract. |
| `region_first_safe_merge` naming | `deprecate_first` | It is the public default name but actually means conservative `local_minimum_with_wis_merge_v1`. | Rename/alias only through C2 with docs and config compatibility. |
| `integrate_linear_edge_baseline` and selector support | retired in Phase 7 | C1a, C5, Tier C AsLS-vs-linear-edge evidence, blank/stress safety, and rollback-column deprecation were resolved in the one-pass branch. The linear-edge implementation was deleted; the remaining selector is an AsLS-only compatibility guard that rejects `linear_edge`. | Preserve the rejection contract and historical diagnostic readers; do not reintroduce linear-edge production support without a new behavior spec. |
| `xic_extractor/baseline.py` top-level AsLS module | completed move-only | C1a relocated implementation while keeping compatibility re-export. | Keep as public compatibility shim unless a breaking-change plan removes the top-level import. |
| `PeakDetectionResult`, `PeakCandidate`, `PeakResult` | `blocked_by_product_decision` | They still own resolver/scoring/message/fallback behavior. | Migrate one consumer at a time through C3; do not bulk delete. |
| `peak_candidates.tsv` and boundary projection builders | `split_only` / keep | They are debug/audit projections with frozen headers, not canonical product model. | Keep as externalized projection surfaces. |
| `alignment_matrix.tsv` owner/backfill path | `blocked_by_product_decision` | It is the downstream correction/statistics delivery surface. | Requires a separate parity/behavior spec before migration. |
| `peak_scoring.py` legacy scorer responsibilities | `semantic_migration` | `EvidenceVector`, `CommonEvidence`, `TraceGroup`, and `PeakHypothesis` now overlap scorer evidence semantics, but scorer policy still owns confidence, caps, and selection. | Follow C4-0 semantic-survival audit: port valid scorer invariants to successor tests, keep active policy until model-selection parity exists, and delete implementation-specific tests after coverage migrates. |
| `alignment/clustering.py` and `alignment/backfill.py` event-first grouping/backfill | retired | Candidate/event grouping and event-first matrix backfill were superseded by owner-first and successor evidence concepts; CodeGraph MCP impact/caller checks found only tests/package shims before deletion. | Keep historical docs as rationale only. Reintroduction requires a new product-path spec, public migration note, and owner-first parity oracle. |
| `alignment/owner_clustering.py` owner-family construction | `semantic_migration` | Cross-sample owner-family grouping is conceptually close to future cross-sample hypothesis/family construction, but `OwnerAlignedFeature` still feeds production backfill/matrix stages. | Characterize family-edge/demotion invariants, migrate them into the successor spine when available, and avoid maintaining a permanent parallel family system. |
| `shared_peak_identity_explanation/*` large modules | `split_only` | Active diagnostic/productization code; size and schema coupling are the debt. | Split behind schema/CLI tests; no product label changes. |
| `matrix_value_conflict_policy=max_area_pending_baseline` and related shared-identity activation wording | `blocked_by_product_decision` | This is a temporary pre-AsLS conflict policy, not dead code. Changing it would affect matrix values and product labels. | Keep until the baseline/AsLS policy lands, then replace or retire through the activation/baseline behavior spec with machine-readable rollback evidence. |
| `alignment/process_backend.py` | `split_only` | Process payload, raw-source, and orchestration logic are mixed; spawn/pickle risks are high. | Split only with no-RAW spawn/pickling smoke tests. |
| `peak_scoring.py` | `split_only` | Existing decomposition target; split is cleaner after C3 exposes the hypothesis spine. | Wait for C3 or add characterization tests before local split. |
| `scripts/local_minimum_param_sweep.py`, `compare_resolvers.py`, validation scripts | `diagnostic_lifecycle` | Development/validation tools may be dormant between investigations. | Keep unless strict retired audit passes. |
| `alignment/legacy_io.py` and validation compare modules | keep | Despite the name, this is the bridge loader for legacy/FH/metabCombiner/combine_fix matrices used by alignment validation. | Not a dead-code candidate; consider a future rename only if it reduces confusion without changing validation behavior. |

## Revised Cleanup Order

### R0 - Branch And Behavior Isolation

Do not mix repo-wide cleanup with an in-flight behavior branch unless the cleanup
is required for that branch. The current AsLS / linear-edge branch should close
or explicitly isolate its diff before broad cleanup begins.

Until `QUAL_SELECTION_READY_FOR_NEXT_BEHAVIOR_PR` resolves in the product reset
decision spec, cleanup is non-mainline maintenance only. It must not touch
product-decision write surfaces such as selected peaks, area values, resolver
defaults, matrix labels, or downstream matrix contracts.

Acceptance:

- `git status --short --branch` is recorded before implementation;
- unrelated dirty files are classified;
- the cleanup PR names whether it is docs-only, move-only, split-only, or
  behavior-affecting.

### R1 - Package Dependency Direction Cleanup

First actionable cleanup target if we clean this boundary: separate
product-owned evidence/IO helpers from tool-only CLI/report wrappers. This does
not remove diagnostic evidence from the main pipeline.

Proposed move:

- move shared diagnostic IO helpers from `tools/diagnostics/diagnostic_io.py`
  to a package-owned canonical module, with `xic_extractor/diagnostics/io.py`
  allowed only if the diagnostic lifecycle spec explicitly treats it as
  schema-neutral shared infrastructure rather than a lifecycle state;
- keep `tools/diagnostics/diagnostic_io.py` as a compatibility shim;
- update package imports to use the package module;
- leave tool imports working through the shim or migrate them in the same PR if
  the diff stays mechanical.

Acceptance:

- no `xic_extractor/` module imports `tools.diagnostics.*`;
- `tools/diagnostics/INDEX.md` names the canonical helper path and identifies
  `tools/diagnostics/diagnostic_io.py` as a compatibility shim;
- the diagnostic lifecycle spec is updated if the chosen package path needs a
  shared-infrastructure carveout;
- existing diagnostic TSV read/write behavior is unchanged;
- canonical-path `diagnostic_io` tests and a shim smoke test both pass, including
  public helper names, TSV formatting, UTF-8-SIG read behavior, and missing-column
  error behavior;
- affected shared-peak-identity tests pass;
- no RAW validation is required because this is move-only.

### R2 - Diagnostic Gate Placement And Lifecycle

After R1, apply the diagnostic lifecycle spec to gate-like tools.

Order:

1. refresh `tools/diagnostics/INDEX.md` counts and shared-infrastructure wording;
2. promote one clearly gated group at a time;
3. preserve public CLI entry points through `tools/diagnostics/` shims;
4. add no-RAW import smoke tests;
5. avoid schema changes during moves.

Do not delete diagnostic tools in the same PR as a promotion unless each
deleted file independently satisfies `delete_now`.

Do not promote a broad topic group just because it lives near a phase gate.
`diagnostic_only`, sidecar-only, and product-label activation tools stay outside
`GATED` placement until a product wiring or activation spec accepts their output
as a required contract.

### R3 - Backfill Review Axis Decision

Before consolidating backfill review tools, define whether seed-level,
family-level, and row-classifier-level review are distinct product questions or
duplicate presentations.

Acceptance:

- one short spec states the axes, owners, inputs, outputs, and retirement rule;
- no consolidation implementation starts before that spec is accepted.

### R4 - Peak-Pipeline Cleanup Chapter

Then return to the existing C-specs, but read them through this broader order:

1. C1a can run early if it is pure relocation plus compatibility re-export.
2. C3a/C3b remain the key handoff-spine scaffolding before deep scoring splits
   or semantic retirement.
3. C5 should stay method-preserving until baseline retirement is authorized.
4. C2 can deprecate or collapse resolver modes only after public config and
   diagnostic fixture migration is explicit.
5. C4 starts with C4-0 semantic-survival audit, not package splitting: decide
   which scorer invariants are successor-owned, active policy, adapter-only, or
   retirement candidates.
6. C6 event-first clustering/backfill has completed its semantic-survival audit
   and retirement. Remaining C6 work starts with owner-family construction and
   other active owner-first stages, not generic grouping primitives.
7. C1b was executed after its linear-edge retirement prerequisites passed in the
   one-pass branch. Future cleanup should treat linear-edge as retired, not as a
   pending rollback option.

Use the
[2026-06-01 current-state reassessment](2026-06-01-peak-pipeline-cleanup-current-state-reassessment-spec.md)
before executing the remaining C2/C3/C4/C6 instructions. Current interpretation:

- keep `legacy_savgol` as a useful clean-trace / compatibility path unless a
  separate public migration contract changes it;
- keep local-minimum internals as boundary/proposal evidence;
- treat CWT as evidence-chain assessment work, not dead-code deletion;
- make C3 current-state inventory and small parity-backed migration the next
  handoff-spine cleanup target;
- rewrite C4 around fusion-first evidence-decision responsibilities before
  implementation;
- run C6 semantic-survival inventory before extracting generic grouping
  primitives or preserving legacy grouping tests.

### R5 - Oversized Active Module Splits

Split active large modules only when the split reduces a named responsibility
problem and has characterization coverage.

Initial targets:

- `shared_peak_identity_explanation/schema.py`: schema constants and value-set
  rules may need submodules by artifact family.
- `shared_peak_identity_explanation/machine_evidence_support.py`: evidence
  support classification should be split by evidence source only after schema
  tests pin output.
- `shared_peak_identity_explanation/peak_hypothesis_matrix.py`: matrix
  construction, expanded-candidate extraction, and writers are likely separate
  responsibilities.
- `alignment/process_backend.py`: process payload and raw-source orchestration
  need spawn-safe tests before movement.
- `alignment/production_candidate_gate.py`, `alignment/pipeline.py`,
  `alignment/owner_backfill.py`, and `alignment/primary_consolidation.py`: line
  pressure exists, but these touch product gating and alignment delivery, so
  they are split-only or product-decision-blocked until characterization and
  parity evidence is named.

### R6 - Strict Dead-Code Deletion

Only after R1-R5 can deletion PRs become routine. Each deletion candidate needs
a short evidence block:

```text
Candidate:
Classification:
Caller scan:
Docs/index scan:
Public contract touched:
Tests removed or updated:
Rollback path:
```

Deletion is not allowed when the candidate is only "old", "large", "legacy",
"low refs", or "not preferred".

## Validation Rules

Use validation proportional to cleanup class:

- docs-only roadmap changes: Markdown grep/smoke, stale wording scan, diff
  check;
- move-only module relocation: focused import tests, existing unit tests for
  moved behavior, no-RAW smoke;
- split-only refactor: focused characterization tests plus lint/typecheck on
  touched modules;
- public config/CLI/schema deprecation: contract tests and docs/index update;
- behavior-affecting cleanup: separate behavior spec and RAW/parity validation
  named by that spec.

CI-equivalent PR gate remains:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -v --tb=short -x
```

## Non-Goals

- No resolver default change.
- No additional AsLS / linear-edge behavior claim beyond the completed Phase 7
  retirement closeout.
- No further public config-value deletion beyond the completed `linear_edge`
  and `arbitrated` retirement inputs.
- No matrix identity or value migration.
- No CWT production promotion.
- No mass deletion of diagnostics based on low textual reference counts.
- No new external dependency or static-analysis tool requirement.

## Open Questions

1. For remaining resolver compatibility values such as `legacy_savgol` and
   `local_minimum`, should old config values warn, map to the supported default,
   or remain accepted silently during a future deprecation PR?
2. Which diagnostic gate should be promoted first after R1, and does it already
   have a gate id, decision target, exit status/code contract, frozen schema, and
   explicit exclusion of diagnostic-only sidecars?

## Recommended Next Plan

After this one-pass cleanup PR, the next plan should not re-open `linear_edge`
or `arbitrated`. If the user chooses one runtime goal, follow the one-goal phase
contract. Otherwise, read the current-state reassessment first, then choose one
remaining slice:

- fusion-first semantic-survival audit for the next highest-overlap legacy
  systems: remaining C4 scorer responsibilities and C6 owner-family
  construction. C6 event-first clustering/backfill is already retired and should
  not be reopened without a new product-path spec;
- C2 follow-up for resolver public-surface contract cleanup, preserving
  `legacy_savgol` and local-minimum internals unless a migration contract says
  otherwise;
- CWT evidence-role inventory with a pre-registered promote / keep-audit /
  externalize-or-kill gate;
- C3 handoff-spine current-state inventory plus one parity-backed consumer
  migration that reduces legacy DTO dependency;
- a narrow split-only plan for an oversized active module with characterization
  tests;
- a strict retired-state audit if the user explicitly wants dead-code deletion.
