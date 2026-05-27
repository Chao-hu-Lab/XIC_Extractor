# Phase 1 / Phase 2 Design Correction Note

**Date:** 2026-05-26
**Status:** Roadmap correction, not implementation
**Inputs:**

- `2026-05-26-phase1-phase2-independent-critique-note.md`
- Read-only implementation review by Codex and subagents
- Current P2b promoted-schema validation artifacts

## Verdict

The critique is materially correct: Phase 1 improved several local behaviors
and audit surfaces, but the original Phase 1 / Phase 2 roadmap still underplays
the handoff architecture. The roadmap over-optimized for low-risk incremental
changes and under-specified the path to a real trace-to-hypothesis-to-audit
spine.

The correction is not to discard Phase 1. The correction is to narrow what
Phase 1 has actually proven and to reorder Phase 2 around the handoff spine
instead of around local cleanup.

## Corrected Phase 1 Claims

### `region_first_safe_merge`

Current reality:

- `region_first_safe_merge` first obtains candidates from
  `find_peak_candidates_local_minimum`.
- Safe merge is a guarded post-selection promotion over adjacent WIS/local
  intervals.
- It is not a true primary region-first resolver.

Correct description:

`region_first_safe_merge` is a conservative
`local_minimum_with_wis_merge_v1` behavior. Keep the public setting for
compatibility, but do not describe it as the final handoff region-first model.

True region-first v2 remains future work: trace/region grouping first,
multi-source hypothesis enumeration second, model selection third.

### P2b / AsLS

Current reality:

- P2b promoted-schema validation clears identity / RT / boundary hard blockers.
- It does not prove AsLS has better absolute accuracy, linearity, blank
  subtraction, or tuned parameters.
- The current promotion is limited to `alignment_cell_integration_audit.tsv`.
- `alignment_matrix.tsv` still uses accepted `cell.area`.

Correct status:

Use `conditional_audit_promotion` for the current AsLS state. Avoid treating
`GO_FOR_PRODUCTION_CANDIDATE` as permission to retire linear-edge or to claim
production-ready baseline truth.

Linear-edge retirement is blocked until a separate AsLS truth validation exists.
Acceptable evidence includes spike-in recovery, blank behavior, linearity, or a
synthetic trace benchmark with known ground truth. RSD and RT/boundary support
are not enough by themselves.

### P7 / 85RAW

Current reality:

P7/P7.5 is not an optimization side quest. It is the reason 85RAW validation can
be executed and audited within a practical time budget.

Correct status:

P7 remains on the critical path for any 85RAW release or cleanup decision that
depends on broad cohort evidence.

## Corrected Phase 2 Strategy

Phase 2 should not start by deleting legacy behavior. It should first establish
the handoff data spine so later cleanup does not need to be repeated.

Recommended ordering:

1. **C0 — Roadmap correction and acceptance rules**
   - Mark Phase 1 claims precisely.
   - Add explicit AsLS truth-validation blocker before linear-edge retirement.
   - Add vision milestone mapping to each C-spec.
2. **C3a / C3b — Hypothesis spine scaffold and dual-write**
   - Make `PeakHypothesis`, `EvidenceVector`, `IntegrationResult`, and
     `AuditTrail` the visible internal spine without changing behavior.
   - Keep legacy models as adapters during a timeboxed dual-write period.
3. **C5 — Area integration single entry, method-preserving**
   - Build one integration entry that can report method and provenance.
   - Do not make it AsLS-only until AsLS truth validation passes.
4. **C2 — Resolver naming and collapse**
   - Rename or alias `region_first_safe_merge` documentation to the honest
     `local_minimum_with_wis_merge_v1` semantics.
   - Keep true region-first v2 as a separate behavior spec.
5. **C4 — Scoring split on the hypothesis spine**
   - Split scoring only after the spine is available, so extracted modules
     consume the future model instead of the legacy table shape.
6. **C6 — Alignment grouping consolidation**
   - Proceed only with golden outputs and byte-identical matrix/review/cell
     parity. Alignment grouping has too many subtle tie-breaks for a casual
     refactor.
7. **C1b — Linear-edge retirement**
   - Last, and only after AsLS truth validation plus C5 migration.

C1a baseline module relocation may still be done early if it is pure import
movement, but it must not imply AsLS-only production or linear-edge retirement.

## Vision Milestones

Every future P-spec or C-spec should state which milestone it advances.

| Milestone | Definition | Current status |
|---|---|---|
| M1 TraceGroup wrapper | Trace / ROI / EIC arrays can be passed as a stable trace-group object | Not started |
| M2 Multi-source hypothesis enumeration | At least two independent proposal sources can emit boundary hypotheses for the same trace | Partial audit-only boundary hypotheses exist |
| M3 EvidenceVector schema freeze | At least three evidence sources contribute through a documented schema | Partial adapter exists; not authoritative |
| M4 Model selection criterion | WIS/AIC/BIC/other criterion selects among hypotheses with a validation target | Not production; WIS is local helper only |
| M5 End-to-end AuditTrail case | One case runs trace -> hypotheses -> selection -> integration -> audit trail | Partial adapter, not end-to-end authoritative |

Specs that advance none of these milestones are cleanup-only. That is allowed,
but they must not be presented as modernization progress.

## Immediate Actions

1. Update modernization and cleanup overviews with this correction.
2. Reword P2b status from production-style GO to conditional audit promotion.
3. Pause any C1b / linear-edge deletion plan until AsLS truth validation exists.
4. Move C3a/C3b earlier in the Phase 2 roadmap.
5. Add a future P2c/P2d truth-validation spec for AsLS parameters and accuracy
   only if the project needs baseline truth strong enough to retire linear-edge.

## Non-Actions

- Do not rename CLI/config values immediately. Treat
  `region_first_safe_merge` as a compatibility name until a migration plan
  exists.
- Do not remove `signal_processing.py`. It is a small compatibility shim; the
  risk is public import surface, not file size.
- Do not rewrite Phase 1 code solely to satisfy naming purity. The priority is
  honest docs, correct gates, and safer Phase 2 ordering.
