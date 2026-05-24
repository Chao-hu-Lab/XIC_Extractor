# P1 — Resolver Default Switch Spec

**Date:** 2026-05-24
**Status:** Implementation slice draft v0.2, hotfix-aligned
**Overview:** [Peak pipeline modernization overview](2026-05-24-peak-pipeline-modernization-overview-spec.md)

## Purpose

Switch the extraction / targeted-validation default surface from
`local_minimum` to `region_first_safe_merge` while keeping untargeted alignment
production quantification on `local_minimum`.

Both resolvers already exist in the code base. The new targeted default
activates the existing safe-merge gating so that local minimum remains the
underlying proposal source but cannot make the final boundary decision in cases
where adjacent WIS evidence supports a single merged region. Untargeted
alignment is different: the 2026-05-18 validation decision and P1 8RAW hotfix
showed that allowing `region_first_safe_merge` to mutate alignment production
quantification can regress strict ISTD evidence. In alignment, region-first
evidence remains audit context only until a separate production promotion gate
passes.

## Why This Switch Is Safe

`peak_detection/region_safe_merge.py` already implements four conservative
gates that must all pass before a merge is promoted:

- `SAFE_MERGE_APEX_DELTA_MAX_MIN = 0.03` (apex movement < 1.8 sec)
- `SAFE_MERGE_AREA_RATIO_MIN = 1.0` and `SAFE_MERGE_AREA_RATIO_MAX = 1.20`
  (area may grow up to 20%, never shrink)
- `SAFE_MERGE_GAP_MAX_MIN = 0.08` (merged-interval gap < 4.8 sec)
- decision source must be `adjacent_wis_local_minimum_merge`

If any gate fails, the resolver falls back to the original local-minimum
candidate. Most candidates will not change. Only candidates where the existing
region-first evidence already classified them as `merge_suggested` and all
four gates pass will see a different production area.

## Inputs Already Available

- `xic_extractor/peak_detection/facade.py:208-223` selects the resolver based on
  `resolver_mode`
- `xic_extractor/peak_detection/region_safe_merge.py:54-186` implements the
  promotion logic
- `xic_extractor/peak_detection/region_model_selection.py` produces the
  `RegionSelectionDecision` consumed by safe merge
- `config/settings.example.csv`, `xic_extractor/settings_schema.py`
  (`CANONICAL_SETTINGS_DEFAULTS`), `scripts/run_alignment.py --resolver-mode`,
  and `scripts/validation_harness.py --resolver-mode` are the public config
  surfaces
- Pre-P1 `scripts/run_alignment.py` routed the alignment production run through
  a resolver-mode adapter that converted `region_first_safe_merge` back to
  `local_minimum`, so config alone did not switch the end-to-end alignment
  default

## Required Change

P1 must update every targeted / extraction default surface:

```text
# config/settings.example.csv
resolver_mode,region_first_safe_merge,峰切割演算法...
```

- update `CANONICAL_SETTINGS_DEFAULTS["resolver_mode"]` to
  `region_first_safe_merge`
- update `scripts/run_alignment.py --resolver-mode` CLI default to
  `region_first_safe_merge`, but keep the alignment production resolver guard
  that rewrites `region_first_safe_merge` to `local_minimum`
- update `scripts/validation_harness.py --resolver-mode` default to
  `region_first_safe_merge`
- update any tests or validation harness defaults that assert
  `local_minimum` as the targeted / extraction default

Do not touch the discovery / instrument-QC hardcoded overrides in P1 unless
validation shows they participate in this production acceptance path. C2 owns
the wider cleanup of those overrides.

## Validation Contract

Before promoting the new default, run the following acceptance gates:

1. Strict ISTD benchmark on 8RAW (`scripts/run_alignment.py` plus
   `tools/diagnostics/targeted_peak_reliability_audit.py`):
   - per-ISTD area RSD must not increase by more than 0.5 absolute percentage
     points relative to the `local_minimum` baseline
   - per-ISTD RT residual median must not shift by more than 0.5 sec
   - the `d3-N6-medA` row must remain `consistent` when evidence-spine
     consistency is evaluated on the same production surface. For the hotfix
     alignment path, compare targeted `local_minimum` output against the
     hotfix alignment output. A targeted `region_first_safe_merge` artifact
     compared directly against hotfix alignment is a cross-resolver drift probe,
     not the hard rollback gate.
2. Identity coherence 8RAW acceptance (`scripts/validate_identity_coherence_8raw.py`
   or successor):
   - controls / decoy verdicts must match the pre-change run
   - identity-family count must be within +/- 2 of the pre-change run
3. Area integration uncertainty audit on 8RAW
   (`tools/diagnostics/area_integration_uncertainty_audit.py`):
   - `unexplained_area_mismatch` count must remain 0
   - `boundary_sensitive` count must not increase by more than 1

## Audit Surface

Each candidate that takes the safe-merge promotion path must:

- expose the `RegionSelectionDecision` fields in `peak_candidates.tsv` via the
  existing `peak_candidate_audit` writer
- record `merge_note = same_apex_merged` or the existing region-first audit
  string so downstream review can identify promoted candidates

If a candidate would have been promoted but failed a gate, the rejection
reason must be visible in the audit row. The current helper
`is_region_first_safe_merge_eligible(...)` is bool-only, so P1 must add a
reason-bearing result (for example `SafeMergeEligibility(eligible, reason)`)
or an adjacent helper that exposes the failed gate name without changing the
promotion thresholds.

## Rollback Condition

Revert the P1 targeted / extraction default surfaces
(`config/settings.example.csv`, `CANONICAL_SETTINGS_DEFAULTS`,
`scripts/run_alignment.py --resolver-mode` default, and
`scripts/validation_harness.py`) to `local_minimum` if any of:

- any ISTD area RSD regresses by more than 0.5 absolute percentage points
- same-surface production evidence-spine comparison changes the `d3-N6-medA`
  row from `consistent`
- identity coherence controls / decoy verdict differs from pre-change run
- `unexplained_area_mismatch` becomes nonzero

Record the rollback under
`docs/superpowers/notes/2026-MM-DD-resolver-default-switch-rollback.md`.

## What This Spec Does Not Change

- `local_minimum.py`, `legacy_savgol.py`, `cwt.py` internal logic
- `region_safe_merge.py` gate thresholds
- alignment cluster behavior, family consolidation, owner backfill
- output schema for `peak_candidates.tsv`, `alignment_matrix.tsv`,
  `alignment_review.tsv`, `alignment_cells.tsv`
- targeted reliability state values
- scoring weights or evidence-vector field meaning

## Open Questions

- Should the activation be a single global switch or per-mode
  (`extraction`, `discovery`, `instrument_qc`)? Current code path
  (`discovery/models.py:117`, `instrument_qc/pipeline_extraction.py:126`)
  hardcodes `local_minimum` inside discovery and instrument_qc; the global
  default switch alone will not change those callers. **Resolution path:** P1
  lands with the global switch only. The hardcoded sites are removed by
  Phase 2 [C2 — Resolver collapse](2026-05-24-peak-pipeline-cleanup-resolver-collapse-spec.md)
  Step 4, after P1 stability is confirmed. P1 reviewers should not expect
  P1 itself to touch the hardcoded sites.
- If the global switch lands but discovery / instrument_qc continue to pin
  `local_minimum`, is the inconsistency acceptable as an interim state? See
  above — yes, the interim is acceptable; C2 owns the cleanup.
- Should the rollback condition `0.5 percentage points` be relaxed for ISTDs
  that already show high RSD baselines?

## Cleanup Hook

Implementation should leave the following structure intact so Phase 2 C2
(resolver collapse) can land without rework:

- do not delete `local_minimum.py`, `legacy_savgol.py`, `cwt.py`, or
  `arbitrated`-related helpers in `facade.py` as part of P1. They are
  removed by C2 after P1 is validated stable.
- do not change the `resolver_mode` permitted-value list in
  `config/settings.example.csv` / `RESOLVER_MODES` beyond switching the
  default. C2 owns the value narrowing.
- the hardcoded `resolver_mode = "local_minimum"` in
  `discovery/models.py:117` and `instrument_qc/pipeline_extraction.py:126`
  can stay for P1 (already noted as an open question); C2 owns their removal.

## Acceptance Owner

Engineering owner reviews the validation outputs and writes a go / no-go note
under `docs/superpowers/notes/`. Without the note this spec is not landed.
