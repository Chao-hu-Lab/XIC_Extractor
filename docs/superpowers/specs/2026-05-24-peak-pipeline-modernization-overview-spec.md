# Peak Pipeline Modernization Overview

**Date:** 2026-05-24
**Status:** Phase 1 implemented through supported scope; P2b revised gate is 8RAW production_candidate and P6 not triggered
**Source memo:** `C:\Users\user\Downloads\lcms_gcms_peak_pipeline_handoff.md`
**Progress checklist:** [2026-05-21 LC-MS/MS handoff progress checklist](../notes/2026-05-21-lcms-msms-handoff-progress-checklist.md)
**Second-pass review session:** 2026-05-24 conversation
**Sibling overview:** [Peak pipeline cleanup roadmap](2026-05-24-peak-pipeline-cleanup-roadmap-overview-spec.md)

This file is the entrypoint for the next-phase peak-pipeline modernization. The
detailed contract is split into focused sub-specs so review can separate
resolver behavior, baseline correction, third-party comparison, audit field
hygiene, evidence honesty, and chromatogram-level alignment.

This is Phase 1 of a two-phase plan. This worktree is scoped to Phase 1.
Cleanup is explicitly on hold until Phase 1 has GO / NO-GO notes. Phase 1
changed the targeted / extraction default surface and added new code paths
(shadow columns, selectors, audit filters); Phase 2 (the
[cleanup roadmap](2026-05-24-peak-pipeline-cleanup-roadmap-overview-spec.md))
removes legacy paths and consolidates the new ones only after those decisions
are stable. The two phases are sibling workstreams with different validation
disciplines — see "Two-Phase Relationship" below.

## Spec Map

Read in this order:

1. [P1 — Resolver default switch](2026-05-24-peak-pipeline-resolver-default-switch-spec.md)
   - switch targeted / extraction defaults from `local_minimum` to
     `region_first_safe_merge`
   - keep untargeted alignment production quantification on `local_minimum`;
     use region-first evidence as audit context there
   - conservative gating already lives in the code base
   - validation against strict ISTD benchmark before promotion
2. [P2 — Area integration AsLS baseline](2026-05-24-peak-pipeline-area-baseline-asls-spec.md)
   - add an AsLS-based area integration path next to the existing linear-edge
     path
   - reuse the existing `xic_extractor/baseline.py:asls_baseline`
   - shadow-only first; promotion is a separate decision
3. [P3 — Third-party shadow comparison](2026-05-24-peak-pipeline-third-party-shadow-comparison-spec.md)
   - 8RAW diagnostic completed as `diagnostic_only`
   - limited asari support; MassCube unavailable under the isolated runner
   - no production behavior changes, no P2b GO, and no P6 escalation
   - external runner / joiner code is not retained as maintained Phase 1 code
4. [P2b — Area integration AsLS promotion](2026-05-24-peak-pipeline-area-baseline-asls-promotion-spec.md)
   - old strict RSD gate was `NO-GO`; RT/boundary-first revised 8RAW gate is
     `GO_FOR_PRODUCTION_CANDIDATE`
   - switches production `area_baseline_corrected` to AsLS only after a GO
     note
   - current note does not switch production area; Cleanup cannot assume AsLS
     production until a separate production-switch step lands
5. [P4 — Area uncertainty formula correction](2026-05-24-peak-pipeline-area-uncertainty-formula-spec.md)
   - 8RAW audit-only correction completed with formula version
     `baseline_residual_mad_v1`
   - audit-only change; no production area mutation
6. [P5 — CWT evidence honesty](2026-05-24-peak-pipeline-cwt-evidence-honesty-spec.md)
   - 8RAW audit-only correction completed
   - document that the in-memory `PeakCandidate.cwt_best_scale` and
     `cwt_ridge_persistence` fields are reverse-engineered and the values
     are not interpretable as real CWT signal
   - added `cwt_audit_filter_reason` to `peak_candidate_boundaries.tsv`
     and marked 44 source-only `cwt_width` rows with
     `legacy_cwt_width_not_real_cwt`
   - `peak_candidates.tsv` stayed at 172 rows and
     `peak_candidate_boundaries.tsv` stayed at 529 rows
   - production scoring path (`region_safe_merge`, scorer OR gate) remains
     byte-identical
   - optional follow-up: real PyWavelets-based CWT with ridge tracking
7. [P6 — RT correction OBI-Warp shadow](2026-05-24-peak-pipeline-rt-correction-obi-warp-spec.md)
   - introduce pyOpenMS OBI-Warp as a shadow non-linear RT correction option
   - compare against the existing anchor-based LOESS path
   - never mutates production RT or alignment until a separate promotion spec

The non-negotiable order is P1 -> P2 -> P3. P4 / P5 can run in parallel after
P3 begins because they are audit-boundary changes. P2b is a promotion gate
after P2 / P3 / P4 evidence; the old strict RSD gate is `NO-GO`, but the
RT/boundary-first revised 8RAW gate records `GO_FOR_PRODUCTION_CANDIDATE`. P6
is contingent on P3 evidence; the current closeout does not trigger it.

Phase 1 closeout note:
[2026-05-25 Phase 1 modernization closeout](../notes/2026-05-25-phase1-modernization-closeout-note.md).

## Two-Phase Relationship

```text
Phase 1 — this spec set (P1 .. P6, plus P2b if AsLS promotion is accepted)
  goal: production peak-pipeline output is closer to handoff vision
  validation: strict ISTD benchmark, identity coherence, area RSD
  outcome: behavior changes and shadow evidence; structure stays the same

  ↓ after Phase 1 stable

Phase 2 — cleanup roadmap (C1a, C1b, C2 .. C6)
  see: 2026-05-24-peak-pipeline-cleanup-roadmap-overview-spec.md
  goal: code structure is closer to handoff vision
  validation: behavioral parity (hash-identical TSVs)
  outcome: structure changes, behavior stays the same
```

Cleanup Phase 2 cannot start until Phase 1 stabilizes. In this worktree,
Cleanup specs are review material only; do not implement C-specs before the
full Phase 1 modernization has GO / NO-GO notes. P2 inside this Phase 1 spec set
may begin after the P1 validation note records a P2-entry GO. Each P-spec
carries a "Cleanup Hook" note describing structural
constraints that Phase 1 implementers should honor to keep Phase 2 tractable.
Examples:

- P2 selector is a thin wrapper, removable by Phase 2 C1b
- P2b is the only spec that can make AsLS production. Without P2b GO, Phase 2
  cannot assume linear-edge retirement is legal
- P4 may place `residual_mad` on `BaselineIntegration` and/or the audit
  summary so Phase 2 C5 can carry it through the unified integration result
  without recomputing it
- P5 audit filter column (`cwt_audit_filter_reason`) is bulk-removable by
  Phase 2 C2
- P3 retained findings/output evidence only; no asari/MassCube runner stack is
  kept as maintained code. P6 diagnostic scripts, if later needed, must stay
  under `tools/diagnostics/` only.

Without these hooks, Phase 2 work becomes harder; each C-spec records the
risk if a hook is missing.

## Why This Modernization Now

A 2026-05-24 second-pass code review surfaced three discrepancies between the
handoff vision and current production:

- The targeted / extraction default was not wired to
  `region_first_safe_merge` on the public surfaces:
  `config/settings.example.csv`, `CANONICAL_SETTINGS_DEFAULTS`, and validation
  harness defaults still exposed legacy defaults. Alignment has a separate
  contract: `scripts/run_alignment.py` may accept `region_first_safe_merge` but
  keeps production quantification on `local_minimum` and emits region-first
  audit context. The handoff asks for local minimum to be weak boundary evidence
  rather than the final targeted decision. The `region_first_safe_merge`
  resolver is already implemented as a conservative targeted production override
  (`peak_detection/region_safe_merge.py:32-186`).
- AsLS baseline is already implemented (`xic_extractor/baseline.py:8-37`) and
  used by S/N scoring (`peak_scoring.py:1006`) but area integration still uses
  linear-edge baseline only (`peak_detection/baseline.py:18-39`). Matrix hump
  and drifting baseline cases are not protected on the area path.
- The CWT resolver in `peak_detection/cwt.py` produces `cwt_best_scale` and
  `cwt_ridge_persistence` that are not derived from CWT mathematics. The
  scorer is immune to the fake values (`peak_scoring.py:776-784` treats them
  as a boolean flag), but the boundary audit can render `cwt_width` symmetric
  intervals that look more meaningful than they are.

These are surgical, low-risk changes. None of them require new architecture.

## Non-Negotiable Implementation Order

```text
P1 resolver default switch
  -> P2 area baseline AsLS (shadow)
  -> P3 third-party shadow comparison
  -> P4 audit field correction          (parallel from P3)
  -> P5 CWT evidence honesty            (parallel from P3)
  -> P2b AsLS production promotion      (only after P2/P3/P4 evidence)
  -> P6 OBI-Warp RT shadow              (contingent on P3 evidence)
```

P1 must validate clean on the strict ISTD benchmark, identity coherence, and
area-uncertainty gates before P2 begins. The 2026-05-24/25 P1 validation note
records a P2-entry GO at `production_candidate` strength for 8RAW; it is not
85RAW or `production_ready`. P2 must remain shadow-only until P2b records a
separate promotion GO note. P3 provided diagnostic-only decision evidence and
did not trigger P6. The RT/boundary-first revised P2b gate records
`GO_FOR_PRODUCTION_CANDIDATE` for 8RAW, but production area has not been
switched. P6 is not triggered. P4 and P5 are audit-only at the
production-decision boundary but may carry schema changes to audit TSVs (see
TSV Schema Impact below). They may run in parallel with P3. P6 is contingent
on RT residual evidence from P3 indicating that anchor-based LOESS is the
bottleneck.

### Identity Coherence Check Coverage

Per-P-spec validation contracts only run an **explicit** identity coherence
check when the spec touches production decisions:

- P1 (targeted / extraction resolver default and alignment audit context) —
  runs identity coherence explicitly
- P2 (shadow-only) — production untouched, no explicit identity coherence
  check (upstream invariant)
- P3 / P6 (shadow / diagnostic only) — not applicable
- P4 (audit-only formula change) — no production decision affected
- P5 (audit honesty + audit-side column addition) — production scoring
  byte-identical, so identity coherence trivially unchanged

A spec that omits explicit identity coherence in its validation contract
is doing so because the spec scope cannot move identity coherence verdicts.
Reviewers should confirm this scope claim during PR review rather than
assume the omission is an oversight.

### TSV Schema Impact Across P-specs

- P2 adds optional columns `area_baseline_corrected_asls`,
  `baseline_score_asls` to `alignment_cell_integration_audit.tsv` (additive,
  off by default)
- P4 keeps the column name `area_uncertainty` but changes its numeric
  semantics. Because TSV schemas are public contracts, P4 must also record a
  formula-version / compatibility note and must either emit
  `baseline_residual_mad` or document how the new value can be reproduced.
  P4 emits TSV-local provenance next to `area_uncertainty` in
  `alignment_cell_integration_audit.tsv`, `peak_candidates.tsv`, and
  `peak_candidate_boundaries.tsv`. Consumers with hardcoded thresholds must
  re-tune.
- P5 adds a new `cwt_audit_filter_reason` column to
  `peak_candidate_boundaries.tsv` so source-only CWT-width hypotheses remain
  visible but are clearly marked as `legacy_cwt_width_not_real_cwt`. P5 also
  clarifies the in-memory semantics of the
  `PeakCandidate.cwt_best_scale` and `cwt_ridge_persistence` fields
  (reverse-engineered, not real CWT). Those fields are not currently
  emitted as named columns in `peak_candidates.tsv`, so there is no
  existing TSV schema to migrate
- P3 retained local diagnostic output artifacts only; no change to existing
  TSVs. P6, if later run, adds new diagnostic files only.

Reviewers and downstream consumers should know which spec touches which TSV
before agreeing to land any of them.

## Responsibility Boundary

In scope for this modernization:

- targeted / extraction resolver default value plus alignment audit context (P1)
- area integration baseline method (P2)
- optional AsLS production promotion (P2b)
- audit field formula correctness (P4)
- audit field honesty about evidence provenance (P5)
- shadow execution of third-party tools (P3 findings only) and pyOpenMS map
  alignment (P6, contingent)

Out of scope for this modernization:

- new architecture for `Trace` / `TraceGroup` / `PeakHypothesis` (the handoff
  vision; already partially implemented under existing specs)
- ML / DL peak classifier (handoff Phase 8)
- production RT correction promotion beyond Level 2 alignment-support
- response / area correction (Level 4 / Level 5 no-go per progress checklist)
- matrix effect or ion suppression correction
- pooled QC drift correction (SERRF / QC-RLSC) — separate later spec
- adduct / isotope / in-source fragment annotation
- credentialing for true endogenous vs artifact

## Validation Harness Reuse

All P-specs reuse the existing strict ISTD benchmark and 8RAW / 85RAW
infrastructure:

- `scripts/run_alignment.py` for end-to-end extraction
- `scripts/validate_identity_coherence_8raw.py` (or its successor) for the
  identity-coherence acceptance gate
- `tools/diagnostics/targeted_peak_reliability_audit.py` for area / RT trend
- `tools/diagnostics/area_integration_uncertainty_audit.py` for area-path audit
- `docs/superpowers/notes/` for go / no-go decision records

Each P-spec must declare which subset of the harness is its acceptance gate.

## Rollback Protocol

Each P-spec includes a rollback subsection. Common rules:

- P1 production-candidate / matrix output schema must not regress
- strict ISTD benchmark area RSD must not regress beyond pre-change baseline
- any production decision that changes between pre-change and post-change runs
  must produce an audit row explaining the difference
- if rollback is triggered, the change is reverted and the failure mode is
  recorded under `docs/superpowers/notes/`

## Open Questions Carried Across All Specs

- The `d3-N6-medA` area mismatch from the 2026-05-18 uncertainty validation
  did not reproduce. Whether P2 AsLS will reproduce it on biological matrix
  RAW files is unknown.
- P3 verified enough to run locally in an isolated venv; MassCube metadata
  reported `CC BY-NC 4.0`, so MassCube-derived artifacts stay local unless
  redistribution is separately reviewed.
- Whether pyOpenMS OBI-Warp can consume the existing trace / candidate
  abstraction without a wide adapter is unknown. P6 must scope the adapter
  before promotion.

Each sub-spec restates the open questions relevant to its scope.

## What This Spec Set Is Not

This is not a request to rewrite the pipeline. It is a list of conservative,
sequenced changes that close known gaps between the handoff vision and current
production. Larger ambitions (ADAP-3D, full hypothesis spine, ML classifier)
remain in their existing specs and are not blocked by this set.
