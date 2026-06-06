# Peak Pipeline Cleanup Roadmap Overview

**Date:** 2026-05-24
**Status:** Roadmap closeout v0.5 — DESIGN CORRECTION APPLIED; C1a, C5,
C1b linear-edge retirement, and C2 `arbitrated` retirement completed in the
2026-06-01 cleanup-retirement branch; remaining cleanup is scoped follow-up
**Sibling overview:** [Peak pipeline modernization overview](2026-05-24-peak-pipeline-modernization-overview-spec.md)
**2026-05-28 handoff mainline update:** the product-priority reset spec
(`2026-05-28-product-priority-reset-decision-spec.md`) supersedes this roadmap's
"next allowed work" wording for handoff mainline selection until
`QUAL_SELECTION_READY_FOR_NEXT_BEHAVIOR_PR` resolves. Cleanup remains valid as
historical/product-led input, but must not run as the mainline before that gate.
**Precondition:** modernization Phase 1 closeout records the supported scope:
P2b conditional audit promotion, 85RAW primary-delivery validation with known
exceptions, and no P6 trigger. Method-preserving cleanup may proceed under that
scope. If Cleanup assumes AsLS-only production or linear-edge retirement, P2b
audit promotion is not enough; [P2c AsLS truth validation](2026-05-26-peak-pipeline-asls-truth-validation-spec.md)
must reach `GO_FOR_LINEAR_EDGE_RETIREMENT`.

**Correction note:** [Phase 1 / Phase 2 design correction](../notes/2026-05-26-phase1-phase2-design-correction-note.md)
**Current C0 source of truth:** [Handoff productization C0](../notes/2026-05-27-handoff-productization-c0-source-of-truth.md)
**2026-06-01 repo-wide cleanup update:** this roadmap is now the
peak-pipeline chapter of the broader
[Technical debt and dead-code cleanup roadmap v2](2026-06-01-technical-debt-and-dead-code-cleanup-roadmap-v2-spec.md).
Use the v2 roadmap for repo-wide cleanup sequencing, diagnostic lifecycle,
dependency-direction cleanup, and dead-code classification. Use this file for
the C1-C6 peak-pipeline cleanup slices only.
**2026-06-01 current-state reassessment:** for remaining C2/C3/C4/C6 work, use
[Peak pipeline cleanup current-state reassessment](2026-06-01-peak-pipeline-cleanup-current-state-reassessment-spec.md)
as the current interpretation. It supersedes older wording that treats
`legacy_savgol` or CWT as straightforward deletion targets and reframes C4/C6
as inventory/design-before-refactor work.
**2026-06-01 one-goal execution contract:** if the remaining cleanup is executed
as one runtime goal, use
[Peak pipeline cleanup one-goal phase contract](2026-06-01-peak-pipeline-cleanup-one-goal-phase-contract-spec.md)
for phase order, commit boundaries, validation, and stop rules.

**2026-06-01 execution closeout:** the cleanup-retirement one-pass branch
satisfied the C1b gate chain and retired `linear_edge` production/config
behavior. It also retired only the `arbitrated` portion of C2. Treat older
language below about C1b being blocked as historical rationale unless this
closeout section or the C1b spec says otherwise.

This file is the entrypoint for Phase 2 structural cleanup. It is the
companion to the modernization roadmap. Phase 1 (the modernization overview)
defines *what behavior to change*. Phase 2 (this overview) defines *what
structural debt to remove* after Phase 1 has stabilized.

The two overviews are siblings, not parent-child. This worktree is focused on
Phase 1 first. Phase 2 cannot be implemented or landed before Phase 1
stabilizes, and Cleanup is not a continuation of any single P-spec — it is a
separate workstream with its own validation contract.

## Relationship to the Modernization Roadmap

```text
Phase 1 — modernization (P1 .. P6, plus P2b if AsLS promotion is accepted)
  goal: production peak-pipeline output is closer to handoff vision
  outcome: behavioral change (resolver, baseline, audit, RT)
  validation: strict ISTD benchmark, identity coherence, area RSD

  ↓ only after Phase 1 stable, and after P2b GO if AsLS is assumed

Phase 2 — structural cleanup (C1a, C1b, C2 .. C6)
  goal: code structure is closer to handoff vision
  outcome: structural change (one baseline, one resolver, one model, one entry)
  validation: behavioral parity (refactored output must hash-match Phase 1
              output for the same input set)
```

Phase 2 introduces no production behavior by default. Every C-spec validation
is "before and after this refactor produce byte-identical TSVs / hashes /
matrix values". Behavior is locked to Phase 1's final state unless a separate
behavior spec explicitly changes it. The 2026-06-01 cleanup-retirement branch
is the explicit exception for the approved `linear_edge` and `arbitrated`
retirements after their gates passed.

## 2026-05-26 Design Correction

The first cleanup roadmap over-weighted local cleanup and under-weighted the
handoff spine. The corrected strategy is:

- establish the hypothesis/evidence/integration/audit spine before retiring
  behavior;
- treat current AsLS as `conditional_audit_promotion`, not production-ready
  baseline truth;
- require P2c `GO_FOR_LINEAR_EDGE_RETIREMENT` before any linear-edge deletion;
  the 2026-06-01 cleanup-retirement branch later satisfied this gate and
  completed C1b;
- describe `region_first_safe_merge` honestly as a compatibility name for
  conservative `local_minimum_with_wis_merge_v1` behavior;
- keep P7/P7.5 on the critical path for any 85RAW-backed cleanup decision.

The old implementation order remains useful historical context, but is not the
current recommended order.

## Spec Map

Listed in original cleanup-slice order. The corrected recommended order is in
"Corrected Recommended Order" below.

1. [C1a — Baseline module relocation](2026-05-24-peak-pipeline-cleanup-baseline-module-consolidation-spec.md)
   - move `asls_baseline` from `xic_extractor/baseline.py` into
     `xic_extractor/peak_detection/baseline.py`
   - keep the top-level module as a compatibility re-export unless a
     breaking-change note explicitly allows deletion
   - landed in `codex/cleanup-retirement-foundation` with the top-level
     compatibility shim preserved
2. [C2 — Resolver collapse](2026-05-24-peak-pipeline-cleanup-resolver-collapse-spec.md)
   - removed the `arbitrated` resolver mode after the one-shot 8RAW comparison
     showed no material advantage
   - older deletion-oriented wording about retiring CWT or demoting
     `legacy_savgol` is superseded by the 2026-06-01 current-state
     reassessment: keep `legacy_savgol` as a useful clean-trace /
     compatibility path, keep local-minimum internals, and assess CWT as a
     future evidence-chain source rather than dead code
   - converge on a single hypothesis-spine-based resolver
   - remaining C2 work is follow-up; `legacy_savgol`, `local_minimum`, and
     `region_first_safe_merge` compatibility remain accepted
3. [C5 — Area integration single entry](2026-05-24-peak-pipeline-cleanup-area-integration-single-entry-spec.md)
   - converge the four baseline-corrected-area call sites onto one entry
   - thin adapters where production / audit needs differ
   - defines a local `AreaIntegrationResult`; C3 may later adopt or map it
   - landed before C1b in the 2026-06-01 one-pass branch
4. [C1b — Linear edge retirement](2026-05-24-peak-pipeline-cleanup-linear-edge-retirement-spec.md)
   - delete `integrate_linear_edge_baseline` and the
     linear-edge selector support after C5 has migrated all callers
   - single AsLS source of truth on the area integration path
   - completed after C5, C1a, P2c/Tier C evidence, and rollback-column
     deprecation gates passed; `integrate_with_baseline` remains only as an
     AsLS-only compatibility guard that rejects `linear_edge`
5. [C3 — Hypothesis model unification](2026-05-24-peak-pipeline-cleanup-hypothesis-model-unification-spec.md)
   - migrate `PeakCandidate` / `PeakResult` / `PeakDetectionResult`
     consumers to the `PeakHypothesis` / `EvidenceVector` /
     `IntegrationResult` / `AuditTrail` spine while preserving public
     `signal_processing` compatibility imports
   - delete or shim legacy dataclasses only after public import smoke tests
   - depends on C1a, C2, C5, C1b
6. [C4 — peak_scoring split](2026-05-24-peak-pipeline-cleanup-peak-scoring-split-spec.md)
   - split `peak_scoring.py` (~1092 lines) into focused modules
   - target: scorer, existing `peak_scoring_evidence.py`, local-S/N,
     severity gates, quality flags
   - depends on C3
   - current-state reassessment says to rewrite this as an evidence-extraction /
     evidence-interpretation / decision-policy design before implementing a
     package split
7. [C6 — Alignment grouping consolidation](2026-05-24-peak-pipeline-cleanup-alignment-grouping-consolidation-spec.md)
   - collapse the multiple owner / cluster / family / fold / consolidation
     stages into a smaller set of grouping primitives
   - pure Scope A refactor only; algorithm upgrades require a separate spec
   - depends on Phase 1 + P3 findings
   - current-state reassessment says to run inventory and characterization
     before extracting generic primitives

Order rationale and dependencies are superseded by "Corrected Recommended
Order" below.

## Vision Milestones

Every future P-spec or C-spec should state which milestone it advances. If a
spec advances none of these, it is cleanup-only and must not be presented as
handoff modernization.

| Milestone | Definition | Current status |
|---|---|---|
| M1 TraceGroup wrapper | Trace / ROI / EIC arrays can be passed as a stable trace-group object | Minimal wrapper exists for targeted/audit paths; not a universal engine |
| M2 Multi-source hypothesis enumeration | At least two independent proposal sources can emit boundary hypotheses for the same trace | Partial audit-only boundary hypotheses exist |
| M3 EvidenceVector schema freeze | At least three evidence sources contribute through a documented schema | Partial targeted adapter exists; not authoritative |
| M4 Model selection criterion | WIS/AIC/BIC/other criterion selects among hypotheses with a validation target | Not production; WIS is local helper only |
| M5 End-to-end AuditTrail case | One case runs trace -> hypotheses -> selection -> integration -> audit trail | One synthetic targeted scaffold path is contract-tested; not productized |

## Why Phase 2 Cannot Be Merged Into Phase 1

Phase 1 specs are deliberately surgical: change focused defaults, add one
shadow column, fix one formula. Reviewers can validate each P-spec
independently against ISTD benchmarks. If a P-spec also tried to refactor
the surrounding module, the validation surface would explode — a single
regression could come from either the behavior change or the refactor, and
bisecting would be expensive.

Phase 2 specs are deliberately structural: they touch many files but
change no observable output. Reviewers validate each C-spec against
behavioral parity (hash-identical outputs). This is a different review
discipline.

Mixing the two would make every PR ambiguous. Splitting them keeps each
review tractable.

## Corrected Recommended Order

When cleanup is run as part of the repo-wide debt pass, apply the 2026-06-01 v2
preflight first:

```text
Close or isolate in-flight behavior work
  -> R1 dependency-direction cleanup
  -> R2 diagnostic lifecycle / gate placement
  -> peak-pipeline C-slices only when the relevant product decision allows them
```

Within the peak-pipeline chapter, the current remaining-work order is:

```text
Phase 1 conditional blockers resolved
  -> C0  roadmap correction / acceptance rules
  -> C2  resolver public-surface contract cleanup, preserving useful modes
  -> CWT evidence-role inventory with a pre-registered gate
  -> C3  current-state inventory + one parity-backed consumer migration
  -> C4  evidence-decision design before scorer split
  -> C6  grouping semantics inventory + characterization parity
```

Dependencies:

- C1a baseline module relocation may still run early if it is pure import
  movement. It must not imply AsLS-only production.
- C3a/C3b should move earlier because the handoff spine is the main architecture
  boundary. Later cleanup should target this spine rather than the legacy table
  model.
- C5 was method-preserving until AsLS truth validation passed. It unified
  integration mechanics before the later C1b deletion.
- C2 should not describe `region_first_safe_merge` as true region-first. Treat
  it as conservative `local_minimum_with_wis_merge_v1` unless a future v2 spec
  implements primary region/hypothesis enumeration.
- C4 depends on C3 because splitting `peak_scoring.py` cleanly assumes the
  hypothesis spine is already visible.
- C6 requires golden parity for matrix/review/cells and should not proceed as a
  casual grouping refactor.
- C1b is complete for `linear_edge`. Deleting any future baseline method still
  requires the same pattern: migration, truth evidence, and audit schema
  deprecation before removal.

## Cleanup Hooks Phase 1 Should Provide

Each Phase 1 spec lands with a "Cleanup Hook" note that lists structural
constraints to keep Phase 2 tractable. These are documented in the
modernization overview and re-stated in each P-spec. Examples:

- P2's `integrate_with_baseline` selector is a thin wrapper. Phase 2's
  C1b removes the wrapper after C5 has migrated callers.
- P4 places `residual_mad` on the integration/audit boundary so Phase 2 C5
  can carry the value through its local result DTO without a wider refactor.
- P5's `cwt_audit_filter_reason` column is the single canonical marker
  Phase 2's C2 historically planned to use for CWT audit-row cleanup. The
  2026-06-01 current-state reassessment supersedes bulk-removal assumptions:
  CWT should first be assessed as an evidence-chain source with a pre-registered
  promote / keep-audit / externalize-or-kill gate.
- P3 and P6 diagnostic scripts live in `tools/diagnostics/` and never
  imported by `xic_extractor/` production code. Phase 2 can move or delete
  them without touching production.

If a Phase 1 spec lands without its cleanup hook, Phase 2 work for that area
becomes harder. The corresponding C-spec records the missing hook as risk.

## Validation Philosophy

Phase 2 refactors must satisfy behavioral parity, defined per C-spec:

- `peak_candidates.tsv` hash unchanged
- `alignment_matrix.tsv` hash unchanged
- `alignment_review.tsv` hash unchanged
- `alignment_cells.tsv` hash unchanged
- strict ISTD benchmark area RSD identical to within numerical noise
  (tolerance: less than 0.01 absolute percentage points)
- identity coherence verdicts unchanged
- diagnostic TSV outputs unchanged for shadow columns

`alignment_matrix.tsv` is the downstream delivery surface for correction and
statistics. `peak_candidates.tsv` is a public/generated audit projection surface:
it must remain parity-stable during cleanup, but it is not the production
quantitative matrix.

If a C-spec validation fails parity, the refactor is incorrect — fix it
before landing. Do not loosen the parity threshold to accommodate the
refactor; that path leads back to behavioral drift, which is what Phase 2 is
trying to prevent.

## Responsibility Boundary

In scope for this cleanup roadmap:

- module structure of peak detection, baseline, integration, scoring
- consolidation of resolver modes and data models
- consolidation of alignment grouping stages
- splitting oversized files into focused modules

Out of scope:

- any behavioral change (those are P-specs)
- new algorithms, new evidence sources, new resolvers
- ML / DL infrastructure
- output schema changes (Phase 2 may rename internal types but must keep
  TSV column names identical)
- new external dependencies (no `pybaselines`, no `pyOpenMS` introduction
  in cleanup; those are P-spec dependencies)

## What This Spec Set Is Not

This is not a "v2 rewrite". The codebase is not being rebuilt — it is being
collapsed onto the data model that the handoff document already defined and
that Phase 1 has already partially realized.

This is also not a request to land all six C-specs together. Each is its
own PR with its own validation. Phase 2 may take several months to fully
land. That is the cost of doing structural work safely.

## Open Questions Carried Across All C-specs

- Should C4 (peak_scoring split) introduce a `peak_scoring/` package, or
  keep `peak_scoring.py` as a thin re-export shim for backward
  compatibility? Decision deferred until C3 lands.
- C6 alignment grouping consolidation is Scope A only in this roadmap.
  Any graph-based or EM-style algorithm upgrade is a separate behavior
  spec after Phase 1 evidence.
- The `arbitrated` resolver mode was user-confirmed as an experimental
  algorithm and is now retired. C2 still has remaining follow-up work for
  resolver public-surface contract cleanup, `legacy_savgol` compatibility,
  local-minimum internals, CWT evidence-chain assessment, and resolver naming.

Each C-spec restates the open questions relevant to its scope.
