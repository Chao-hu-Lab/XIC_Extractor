# Peak Pipeline Cleanup Roadmap Overview

**Date:** 2026-05-24
**Status:** Roadmap draft v0.2 — ON HOLD until Phase 1 GO / NO-GO notes
**Sibling overview:** [Peak pipeline modernization overview](2026-05-24-peak-pipeline-modernization-overview-spec.md)
**Precondition:** modernization Phase 1 validation reports clean. If Cleanup
assumes AsLS production, [P2b — Area integration AsLS promotion](2026-05-24-peak-pipeline-area-baseline-asls-promotion-spec.md)
must also have a GO note.

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

Phase 2 introduces no new behavior. Every C-spec validation is "before and
after this refactor produce byte-identical TSVs / hashes / matrix values".
Behavior is locked to Phase 1's final state. Until Phase 1 has GO / NO-GO
notes, every C-spec is planning material only.

## Spec Map

Listed in implementation order (matches Non-Negotiable Order below):

1. [C1a — Baseline module relocation](2026-05-24-peak-pipeline-cleanup-baseline-module-consolidation-spec.md)
   - move `asls_baseline` from `xic_extractor/baseline.py` into
     `xic_extractor/peak_detection/baseline.py`
   - keep the top-level module as a compatibility re-export unless a
     breaking-change note explicitly allows deletion
   - can land first only after Phase 1 and P2b are stable
2. [C2 — Resolver collapse](2026-05-24-peak-pipeline-cleanup-resolver-collapse-spec.md)
   - remove the `arbitrated` resolver mode (no production caller)
   - retire the standalone `cwt` resolver_mode; keep `centwave_cwt` as a
     proposal source only
   - demote `legacy_savgol` from a top-level resolver_mode to a SG utility
   - converge on a single hypothesis-spine-based resolver
   - can run in parallel with C1a
3. [C5 — Area integration single entry](2026-05-24-peak-pipeline-cleanup-area-integration-single-entry-spec.md)
   - converge the four baseline-corrected-area call sites onto one entry
   - thin adapters where production / audit needs differ
   - defines a local `AreaIntegrationResult`; C3 may later adopt or map it
   - depends on C1a and P2b
4. [C1b — Linear edge retirement](2026-05-24-peak-pipeline-cleanup-linear-edge-retirement-spec.md)
   - delete `integrate_linear_edge_baseline` and the
     `integrate_with_baseline` selector wrapper after C5 has migrated all
     callers
   - single AsLS source of truth on the area integration path
   - depends on C5
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
7. [C6 — Alignment grouping consolidation](2026-05-24-peak-pipeline-cleanup-alignment-grouping-consolidation-spec.md)
   - collapse the multiple owner / cluster / family / fold / consolidation
     stages into a smaller set of grouping primitives
   - pure Scope A refactor only; algorithm upgrades require a separate spec
   - depends on Phase 1 + P3 findings

Order rationale and dependencies are listed under "Non-Negotiable Order"
below.

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

## Non-Negotiable Order

```text
all of Phase 1 must be stable and validated
  -> P2b AsLS promotion GO if Cleanup assumes AsLS production
  -> C1a baseline module relocation       (independent)
  -> C2  resolver collapse                (after P5 stable; can parallel C1a)
  -> C5  area integration single entry    (after C1a + P2b)
  -> C1b linear edge retirement           (after C5)
  -> C3  hypothesis model unification     (after C1a, C2, C5, C1b)
  -> C4  peak_scoring split               (after C3)
  -> C6  alignment grouping consolidation (after P3 evidence + Phase 1 stable)
```

Dependencies:

- C1a and C2 are largely independent and can run in parallel after Phase 1,
  but C1a cannot delete the top-level baseline import surface without an
  explicit compatibility decision
- C5 depends on C1a because the single integration entry imports AsLS from
  the relocated module; it also depends on P2b if the entry is meant to be
  AsLS production-only
- C1b depends on C5 because deleting `integrate_linear_edge_baseline`
  requires no remaining callers
- C3 depends on C1a, C2, and C5 because the unified model assumes one
  baseline module, one resolver path, and one area entry point
- C4 depends on C3 because splitting `peak_scoring.py` cleanly assumes the
  hypothesis spine is already authoritative
- C6 depends on P3 evidence and Phase 1 stability only to decide whether the
  pure refactor is worth prioritizing. Its scope stays Scope A; behavior
  upgrades require a separate spec

## Cleanup Hooks Phase 1 Should Provide

Each Phase 1 spec lands with a "Cleanup Hook" note that lists structural
constraints to keep Phase 2 tractable. These are documented in the
modernization overview and re-stated in each P-spec. Examples:

- P2's `integrate_with_baseline` selector is a thin wrapper. Phase 2's
  C1b removes the wrapper after C5 has migrated callers.
- P4 places `residual_mad` on the integration/audit boundary so Phase 2 C5
  can carry the value through its local result DTO without a wider refactor.
- P5's `cwt_audit_filter_reason` column is the single canonical marker
  Phase 2's C2 uses to identify CWT audit rows for bulk removal when
  retiring the resolver.
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
- The `arbitrated` resolver mode has no production caller today. Is that
  confirmed across all branches / deployments outside this repo? The C2
  spec lists this as a precondition for removal.

Each C-spec restates the open questions relevant to its scope.
