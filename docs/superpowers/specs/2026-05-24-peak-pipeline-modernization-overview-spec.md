# Peak Pipeline Modernization Overview

**Date:** 2026-05-24
**Status:** Roadmap draft v0.1
**Source memo:** `C:\Users\user\Downloads\lcms_gcms_peak_pipeline_handoff.md`
**Progress checklist:** [2026-05-21 LC-MS/MS handoff progress checklist](../notes/2026-05-21-lcms-msms-handoff-progress-checklist.md)
**Second-pass review session:** 2026-05-24 conversation
**Sibling overview:** [Peak pipeline cleanup roadmap](2026-05-24-peak-pipeline-cleanup-roadmap-overview-spec.md)

This file is the entrypoint for the next-phase peak-pipeline modernization. The
detailed contract is split into focused sub-specs so review can separate
resolver behavior, baseline correction, third-party comparison, audit field
hygiene, evidence honesty, and chromatogram-level alignment.

This is Phase 1 of a two-phase plan. Phase 1 changes production behavior
and adds new code paths (shadow columns, selectors, audit filters); Phase 2
(the [cleanup roadmap](2026-05-24-peak-pipeline-cleanup-roadmap-overview-spec.md))
removes legacy paths and consolidates the new ones. The two phases are
sibling workstreams with different validation disciplines — see "Two-Phase
Relationship" below.

## Spec Map

Read in this order:

1. [P1 — Resolver default switch](2026-05-24-peak-pipeline-resolver-default-switch-spec.md)
   - switch production resolver default from `local_minimum` to
     `region_first_safe_merge`
   - conservative gating already lives in the code base
   - validation against strict ISTD benchmark before promotion
2. [P2 — Area integration AsLS baseline](2026-05-24-peak-pipeline-area-baseline-asls-spec.md)
   - add an AsLS-based area integration path next to the existing linear-edge
     path
   - reuse the existing `xic_extractor/baseline.py:asls_baseline`
   - shadow-only first; promotion is a separate decision
3. [P3 — Third-party shadow comparison](2026-05-24-peak-pipeline-third-party-shadow-comparison-spec.md)
   - run `asari` and `MassCube` against the same 8RAW / 85RAW datasets as
     external references
   - compare area, RT residual, peak count, and missingness
   - no production behavior changes; output is decision evidence only
4. [P4 — Area uncertainty formula correction](2026-05-24-peak-pipeline-area-uncertainty-formula-spec.md)
   - replace the in-peak first-difference MAD formula with a baseline-residual
     noise propagation formula
   - audit-only change; no production area mutation
5. [P5 — CWT evidence honesty](2026-05-24-peak-pipeline-cwt-evidence-honesty-spec.md)
   - document that the in-memory `PeakCandidate.cwt_best_scale` and
     `cwt_ridge_persistence` fields are reverse-engineered and the values
     are not interpretable as real CWT signal
   - audit-side filter on the `cwt_width` boundary hypothesis so misleading
     symmetric intervals are not shown to reviewers
   - add a new `cwt_audit_filter_reason` column to
     `peak_candidate_boundaries.tsv` so suppressed boundary hypotheses are
     visible to reviewers
   - production scoring path (`region_safe_merge`, scorer OR gate) remains
     byte-identical
   - optional follow-up: real PyWavelets-based CWT with ridge tracking
6. [P6 — RT correction OBI-Warp shadow](2026-05-24-peak-pipeline-rt-correction-obi-warp-spec.md)
   - introduce pyOpenMS OBI-Warp as a shadow non-linear RT correction option
   - compare against the existing anchor-based LOESS path
   - never mutates production RT or alignment until a separate promotion spec

The non-negotiable order is P1 -> P2 -> P3, with P4 / P5 runnable in parallel,
and P6 contingent on P3 evidence.

## Two-Phase Relationship

```text
Phase 1 — this spec set (P1 .. P6)
  goal: production peak-pipeline output is closer to handoff vision
  validation: strict ISTD benchmark, identity coherence, area RSD
  outcome: behavior changes, structure stays the same

  ↓ after Phase 1 stable

Phase 2 — cleanup roadmap (C1a, C1b, C2 .. C6)
  see: 2026-05-24-peak-pipeline-cleanup-roadmap-overview-spec.md
  goal: code structure is closer to handoff vision
  validation: behavioral parity (hash-identical TSVs)
  outcome: structure changes, behavior stays the same
```

Phase 2 cannot start until Phase 1 stabilizes. Each P-spec carries a
"Cleanup Hook" note describing structural constraints that Phase 1
implementers should honor to keep Phase 2 tractable. Examples:

- P2 selector is a thin wrapper, removable by Phase 2 C1b
- P4 places `residual_mad` on `BaselineIntegration` so Phase 2 C5 can
  carry it through `IntegrationResult` without further refactoring
- P5 audit filter column (`cwt_audit_filter_reason`) is bulk-removable by
  Phase 2 C2
- P3 / P6 diagnostic scripts live in `tools/diagnostics/` only

Without these hooks, Phase 2 work becomes harder; each C-spec records the
risk if a hook is missing.

## Why This Modernization Now

A 2026-05-24 second-pass code review surfaced three discrepancies between the
handoff vision and current production:

- The production resolver is still `local_minimum` (see
  `config/settings.csv:resolver_mode`), even though the handoff asks for local
  minimum to be a weak boundary evidence rather than the final decision. The
  `region_first_safe_merge` resolver is already implemented as a conservative
  production override (`peak_detection/region_safe_merge.py:32-186`) but is not
  the default.
- AsLS baseline is already implemented (`xic_extractor/baseline.py:8-37`) and
  used by S/N scoring (`peak_scoring.py:1006`) but area integration still uses
  linear-edge baseline only (`peak_detection/baseline.py:18-39`). Matrix hump
  and drifting baseline cases are not protected on the area path.
- The CWT resolver in `peak_detection/cwt.py` produces `cwt_best_scale` and
  `cwt_ridge_persistence` that are not derived from CWT mathematics. The
  scorer is immune to the fake values (`peak_scoring.py:776-784` treats them
  as a boolean flag) but the audit TSV exports them and can mislead manual
  review.

These are surgical, low-risk changes. None of them require new architecture.

## Non-Negotiable Implementation Order

```text
P1 resolver default switch
  -> P2 area baseline AsLS (shadow)
  -> P3 third-party shadow comparison
  -> P4 audit field correction          (parallel from P3)
  -> P5 CWT evidence honesty            (parallel from P3)
  -> P6 OBI-Warp RT shadow              (contingent on P3 evidence)
```

P1 must validate clean on the strict ISTD benchmark before P2 begins. P2 must
remain shadow-only until P3 third-party comparison reports a verdict. P4 and
P5 are audit-only at the production-decision boundary but may carry schema
changes to audit TSVs (see TSV Schema Impact below). They may run in parallel
with P3. P6 is contingent on RT residual evidence from P3 indicating that
anchor-based LOESS is the bottleneck.

### Identity Coherence Check Coverage

Per-P-spec validation contracts only run an **explicit** identity coherence
check when the spec touches production decisions:

- P1 (production resolver default) — runs identity coherence explicitly
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
  semantics; consumers with hardcoded thresholds must re-tune. P4 may also
  add a new `baseline_residual_mad` audit column (open question; not yet
  committed)
- P5 adds a new `cwt_audit_filter_reason` column to
  `peak_candidate_boundaries.tsv` so suppressed boundary hypotheses are
  visible to reviewers. P5 also clarifies the in-memory semantics of the
  `PeakCandidate.cwt_best_scale` and `cwt_ridge_persistence` fields
  (reverse-engineered, not real CWT). Those fields are not currently
  emitted as named columns in `peak_candidates.tsv`, so there is no
  existing TSV schema to migrate
- P3 and P6 add new diagnostic files; no change to existing TSVs

Reviewers and downstream consumers should know which spec touches which TSV
before agreeing to land any of them.

## Responsibility Boundary

In scope for this modernization:

- production resolver default value (P1)
- area integration baseline method (P2)
- audit field formula correctness (P4)
- audit field honesty about evidence provenance (P5)
- shadow execution of third-party tools (P3) and pyOpenMS map alignment (P6)

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

- production candidate / matrix output schema must not regress
- strict ISTD benchmark area RSD must not regress beyond pre-change baseline
- any production decision that changes between pre-change and post-change runs
  must produce an audit row explaining the difference
- if rollback is triggered, the change is reverted and the failure mode is
  recorded under `docs/superpowers/notes/`

## Open Questions Carried Across All Specs

- The `d3-N6-medA` area mismatch from the 2026-05-18 uncertainty validation
  did not reproduce. Whether P2 AsLS will reproduce it on biological matrix
  RAW files is unknown.
- Whether asari / MassCube licenses are compatible with this project is
  unconfirmed. P3 must verify before shadow runs.
- Whether pyOpenMS OBI-Warp can consume the existing trace / candidate
  abstraction without a wide adapter is unknown. P6 must scope the adapter
  before promotion.

Each sub-spec restates the open questions relevant to its scope.

## What This Spec Set Is Not

This is not a request to rewrite the pipeline. It is a list of conservative,
sequenced changes that close known gaps between the handoff vision and current
production. Larger ambitions (ADAP-3D, full hypothesis spine, ML classifier)
remain in their existing specs and are not blocked by this set.
