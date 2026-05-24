# C2 — Resolver Collapse Spec

**Date:** 2026-05-24
**Status:** Cleanup slice draft v0.1
**Overview:** [Peak pipeline cleanup roadmap overview](2026-05-24-peak-pipeline-cleanup-roadmap-overview-spec.md)
**Precondition:** P1 (resolver default switch) and P5 (CWT evidence honesty)
both validated clean. Confirmation that no external caller depends on the
`arbitrated` resolver_mode.

## Purpose

Collapse five resolver modes into one production path plus a small set of
internal proposal sources. The current `resolver_mode` flag exposes
historical implementation choices that have lost their independent meaning
after P1.

This refactor introduces no behavioral change for the supported (post-P1)
production mode. Validation is behavioral parity.

## Current State

`xic_extractor/peak_detection/facade.py:208-223` dispatches on
`resolver_mode` with four explicit branches plus an additional proposal
source (CWT) that is not a top-level `resolver_mode`:

| Mode (top-level dispatch) | Role | Post-P1 status |
|---------------------------|------|----------------|
| `legacy_savgol` | SG smoothing + prominence | Fallback branch in `facade.py` |
| `local_minimum` | Local minimum boundary | Routed via the `{local_minimum, region_first_safe_merge}` branch; remains the proposal source for region-first |
| `arbitrated` | Merge legacy + local results | **No production caller** |
| `region_first_safe_merge` | Local minimum + safe-merge promotion | **Production default after P1** |

Plus a **non-dispatched proposal source** (not a `resolver_mode` value, no
`facade.py` branch): `centwave_cwt` invoked via `peak_detection/cwt.py`
infrastructure. After P5 the CWT call only produces flag evidence; it does
not function as a top-level resolver.

Additional hardcoded `resolver_mode = "local_minimum"`:

- `xic_extractor/discovery/models.py:117`
- `xic_extractor/instrument_qc/pipeline.py:593`

These hardcoded sites bypass the global `config/settings.csv:resolver_mode`
setting and were addressed as an open question in P1.

## Required Change

### Step 1 — Remove the `arbitrated` resolver mode

Verify no external caller (other repos, deployment configs, CI scripts) uses
`resolver_mode=arbitrated`. If confirmed:

- delete the `arbitrated` branch from `facade.py:212-217`
- delete the supporting functions: `_find_peak_candidates_arbitrated`,
  `_merge_resolver_candidates`, `_matching_merge_index`,
  `_merged_candidate`, `_material_boundary_disagreement`,
  `_candidate_detail_score`, `_source_apex_rank`,
  `_max_result_smoothed`, `_strongest_failure_result`
- **do NOT delete `_combine_proposal_sources`**: it is shared between the
  arbitrated path (`facade.py:315` inside `_merged_candidate`) and the
  recovery path (`facade.py:485` inside `_append_or_merge_recovery_candidate`).
  After the arbitrated path is removed, the recovery caller still needs
  this helper. Leave the function in place; only delete its arbitrated
  call site
- update `config/settings.csv` documentation: remove `arbitrated` from the
  permitted value list

If external callers exist, defer the removal and document the constraint
under `docs/superpowers/notes/`.

### Step 2 — Convert `legacy_savgol` from resolver_mode to utility

After P1, no production caller depends on `legacy_savgol` as a top-level
resolver. The SG noise floor estimation in
`legacy_savgol.py:_prominence_threshold` (line 138-148) is still useful as a
noise estimator.

Plan:

- move `_prominence_threshold` (MAD-on-SG-residual noise floor) to a new
  module `xic_extractor/peak_detection/noise_estimation.py`
- delete `find_peak_candidates_legacy_savgol` and its private helpers from
  `legacy_savgol.py`
- delete the `legacy_savgol.py` file
- delete the `legacy_savgol` fallback branch from `facade.py:218-223`
- update `config/settings.csv` permitted values

### Step 3 — Retire the standalone CWT resolver mode

After P5, CWT emits audit-flag-only evidence; it does not function as a
peak finder. Plan:

- delete the standalone `cwt` branch handling from `facade.py` (if any
  remains — verify at refactor time)
- keep `centwave_cwt` as a proposal source called from the unified resolver
  for the `cwt_same_apex_support` evidence flag
- if P5b (real CWT) has not happened, also consider deleting `cwt.py`
  entirely and removing the proposal source. This sub-decision depends on
  whether `_CWT_SAME_APEX_SUPPORT_POINTS = 5` evidence is empirically
  useful — see open question

### Step 4 — Address hardcoded resolver_mode sites

Two sites pin `resolver_mode` to `"local_minimum"` independently of the
global `config/settings.csv` value, but their nature differs:

- `discovery/models.py:117` — **dataclass field default**:
  `resolver_mode: str = "local_minimum"` on a `DiscoverySettings`-like
  dataclass. Edit semantics: change the default literal, or remove the
  field if the caller path can inherit from the global config object.
- `instrument_qc/pipeline.py:593` — **inline keyword argument**:
  `resolver_mode="local_minimum"` passed when constructing the QC config.
  Edit semantics: change or remove the keyword argument.

The post-collapse resolver_mode permitted values reduce to one production
value: `region_first_safe_merge`. The hardcoded sites should either inherit
the global default or be deleted as dead overrides. Treat them as
separate diffs since the edit kind is different.

### Step 5 — Rename `resolver_mode` (optional)

After collapse, `resolver_mode` has one permitted value, which makes the
config field redundant. Two options:

- (a) keep the field with `region_first_safe_merge` literal for
  forward-compatibility (when an alternative resolver lands later)
- (b) remove the field entirely, hardcoding the resolver in `facade.py`

Decision: keep (a). Matches the same logic as C1's `baseline_type` field.

## Validation Contract

Behavioral parity required:

1. Run 8RAW with `resolver_mode = region_first_safe_merge` (Phase 1 final
   state)
2. Apply C2 refactor
3. Re-run 8RAW
4. `peak_candidates.tsv`, `alignment_matrix.tsv`, `alignment_review.tsv`,
   `alignment_cells.tsv` must hash-match
5. Strict ISTD benchmark area / RT / RSD identical
6. Identity coherence verdicts unchanged

Additional check:

- before deletion, run a one-shot scan with `resolver_mode=arbitrated` on
  8RAW; result must be either equivalent to or strictly worse than the
  region-first run. If `arbitrated` is materially better on any ISTD, the
  collapse is premature — record findings and defer

## Rollback Condition

Restore deleted modes if any of:

- a non-internal caller of `arbitrated` surfaces during validation
- hash mismatch on parity TSVs (would indicate the dispatch deletion changed
  behavior unexpectedly)
- the noise estimation extracted in Step 2 changes `_prominence_threshold`
  output for any ISTD

## What This Spec Does Not Change

- production peak selection for `region_first_safe_merge`
- AsLS baseline (owned by C1)
- area integration entry (owned by C5)
- hypothesis spine (owned by C3)
- scoring weights
- TSV column names

## Open Questions

- Has anyone enabled `arbitrated` in a downstream config? No grep evidence
  in this repo. Confirmation from production deployment owners needed.
- Does `_CWT_SAME_APEX_SUPPORT_POINTS = 5` give measurable benefit on the
  strict ISTD benchmark? If not, P5 followup (delete CWT entirely) can be
  bundled into C2. If yes, keep the proposal source through C2.
- Should `noise_estimation.py` accept the SG-smoothed array as an argument,
  or compute it internally? Decision deferred to refactor time.
- Does `discovery/models.py:117`'s `resolver_mode = "local_minimum"` override
  serve a discovery-specific purpose (e.g. discovery needs a different
  cutoff than extraction)? Verify by running discovery with
  `region_first_safe_merge` on 8RAW; if discovery output differs in a
  meaningful way, document the override before deletion.

## Acceptance Owner

Engineering owner confirms no external `arbitrated` caller, runs parity
validation, records under `docs/superpowers/notes/`. PR includes the parity
report and the resolved mode-removal checklist.
