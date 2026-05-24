# P5 — CWT Evidence Honesty Spec

**Date:** 2026-05-24
**Status:** Audit-only correction draft v0.1
**Overview:** [Peak pipeline modernization overview](2026-05-24-peak-pipeline-modernization-overview-spec.md)
**Parallel to:** P3, P4

## Purpose

`peak_detection/cwt.py` exports two evidence fields whose values are
reverse-engineered from non-CWT decisions, not from CWT mathematics:

- `cwt_best_scale` is the wavelet scale index whose width best matches the
  *final region width*, which was determined by `scipy.signal.peak_widths`
  on raw intensity at `rel_height`, not by maximum wavelet coefficient
  search. See `cwt.py:194 _best_scale_for_width(widths, right - left)`.
- `cwt_ridge_persistence` is `min_length / len(widths)`, where `min_length`
  is the scipy `find_peaks_cwt(min_length=...)` parameter. This is a fixed
  ratio derived from configuration, not a ridge tracking length across
  scales. See `cwt.py:210`.

The scorer (`peak_scoring.py:776-784`) is immune to these values because it
treats them as a boolean flag (`_positive_finite_metric(value)`). The risk
is on the in-memory dataclass surface: `PeakCandidate.cwt_best_scale` and
`PeakCandidate.cwt_ridge_persistence` (`xic_extractor/peak_detection/models.py`)
are accessible to any future code path or audit emitter that imports the model.

Note: these two fields are **not currently emitted as named columns** in
either `peak_candidates.tsv` (written by
`xic_extractor/extraction/peak_candidate_table.py`, header constant
`PEAK_CANDIDATE_HEADERS`) or any other TSV. They live only on the in-memory
model. P5 must keep this property unless a real CWT upgrade (P5b) lands
later.

This spec restores audit honesty without breaking the scorer's existing OR
gate behavior. A separate follow-up (P5b in this spec) describes how to
replace the fields with real CWT measurements if that becomes a priority.

## P5a — Required Honesty Change

The in-memory fields stay (the scorer needs them), but their values are
documented as flag-only and the model dataclass docstring records the
caveat:

- in `xic_extractor/peak_detection/models.py`, add a docstring note on
  `PeakCandidate.cwt_best_scale` and `PeakCandidate.cwt_ridge_persistence`:
  "audit-flag use only; value is reverse-engineered from non-CWT decisions
  and not interpretable as a CWT scale or ridge length"
- in `xic_extractor/peak_detection/hypotheses.py`, add the same note on
  `PeakHypothesis.cwt_best_scale` and `PeakHypothesis.cwt_ridge_persistence`
- if any future audit TSV emitter wants to expose these fields, it must
  rename them to `cwt_proposal_present` (boolean) or suffix with
  `_legacy_audit` plus a header-comment explaining the provenance. P5 does
  not pre-emit such a column; the rule is documented for future emitters.

Scorer change (`peak_scoring.py:776-784`):

- replace the `cwt_best_scale OR cwt_ridge_persistence` check with the
  explicit `centwave_cwt in proposal_sources AND any other source in
  proposal_sources` check, dropping the numeric-truthy probe
- behavior remains identical (the existing check was effectively the same
  thing, just expressed in misleading terms)

## P5b — Optional Real CWT Upgrade

If audit honesty alone is insufficient and the project decides it wants real
CWT evidence in `EvidenceVector`, the upgrade is:

- add `pywavelets` (PyWavelets) as a project dependency
- in `peak_detection/cwt.py`, replace `find_peaks_cwt` with:
  - `pywt.cwt(intensity, scales, "mexh")` to obtain a true coefficient
    matrix of shape `(len(scales), n_points)`
  - implement Du, Kibbe, Lin 2006 algorithm 1 ridge tracking: connect
    coefficient maxima across scales by nearest-neighbor in the column
    dimension; a ridge is a connected sequence of maxima spanning at least
    `min_ridge_length` scales
- expose three honest fields per ridge:
  - `cwt_ridge_max_coef` (numeric)
  - `cwt_ridge_length` (integer, number of scales the ridge spans)
  - `cwt_best_scale` (scale index of the coefficient maximum on the ridge)
- replace the existing OR flag with a calibrated check, for example
  `ridge_length >= 5 AND ridge_max_coef > threshold * residual_mad`

P5b requires re-tuning the scorer's `_CWT_SAME_APEX_SUPPORT_POINTS` weight
because the new check is a real signal, not a coexistence flag.

P5b is not part of the minimum acceptable P5 change. It is recorded here so a
future spec can pick it up without re-doing the analysis.

## Boundary Implications

`peak_detection/boundaries.py:176-190` uses `cwt_best_scale` to construct a
`cwt_width` boundary hypothesis. Under the current fake-value regime this
hypothesis is a symmetric apex-centered interval with `width_scans =
cwt_best_scale`, which is the final region width found by a different
method.

### Interaction with P1

`enumerate_boundary_hypotheses` is called in two places:

- `xic_extractor/extraction/peak_candidate_boundaries.py:93` — audit-only
  emission for `peak_candidates.tsv`
- `xic_extractor/peak_detection/region_safe_merge.py:198` — production
  candidate scoring when `resolver_mode = region_first_safe_merge`

Once P1 lands, `region_first_safe_merge` is the production resolver default.
Changing the default `sources` tuple of `enumerate_boundary_hypotheses` would
therefore mutate production candidate scoring.

P5a must not change production scoring. To prevent that, P5a takes the
audit-side-only path:

1. Keep `cwt_width` in the default `sources` tuple of
   `enumerate_boundary_hypotheses`. Do not change `boundaries.py`.
2. At the audit emitter (`peak_candidate_boundaries.py`), suppress the
   `cwt_width` row when the source-only boundary cannot be backed by real
   CWT evidence. Use an explicit `cwt_audit_filter_reason` column so
   reviewers see why a hypothesis was hidden rather than silently dropped.
3. The `region_safe_merge` path continues to receive the full source set so
   its `RegionSelectionDecision` is byte-identical before and after P5a.

If a later spec (P5b) introduces real CWT, the audit filter is removed and
`cwt_width` is restored as a meaningful audit row.

### Alternatives Considered

- (b) Run a with-vs-without `cwt_width` driftless validation on the strict
  ISTD benchmark before P5a lands. This works but adds a full re-validation
  cycle and serializes P5 behind P1. Rejected as too costly.
- (c) Make the CWT resolver emit `cwt_best_scale = None`, so the existing
  `_cwt_width_interval` returns `None` naturally. This avoids the audit
  filter but also disables the boundary in `region_safe_merge`, which is the
  exact production change we are trying to avoid. Rejected for the same
  reason.

Path (a) keeps production scoring untouched and is the only option that lets
P5 land in parallel with or after P1 without coupling them.

## Validation Contract

P5a is a pure rename / audit-wiring change. Validation:

- 8RAW strict ISTD benchmark must produce identical peak selection and
  scoring outputs before / after the change (only audit column names and the
  audit-side `cwt_width` hypothesis filtering differ)
- `peak_candidates.tsv` row count must be identical
- `alignment_matrix.tsv` and `alignment_review.tsv` hashes must be identical
- `peak_candidate_boundaries.tsv` (or equivalent boundary audit TSV) may show
  fewer `cwt_width` rows, accompanied by `cwt_audit_filter_reason` entries
- `RegionSelectionDecision` outputs in the region-first audit surface must be
  byte-identical before and after the change

If production peak selection or `RegionSelectionDecision` differs, treat as a
bug in the audit filter (it touched the production path when it should not
have).

## What This Spec Does Not Change (P5a)

- production peak selection
- area / RT / baseline values
- alignment / matrix outputs
- the `centwave_cwt` proposal source itself (still runs, still flags
  candidates)
- the `cwt_same_apex_support` evidence signal in
  `peak_scoring.py` (still grants `_CWT_SAME_APEX_SUPPORT_POINTS = 5`)
- the default `sources` tuple of `enumerate_boundary_hypotheses` in
  `peak_detection/boundaries.py`
- `RegionSelectionDecision` output in region-first scoring

## Rollback Condition (P5a)

Restore the previous audit column names and the OR check if reviewers depend
on the numeric `cwt_best_scale` or `cwt_ridge_persistence` columns through
external scripts that were not visible at spec time.

## Open Questions

- Are there external scripts (outside this repo) consuming
  `cwt_best_scale` or `cwt_ridge_persistence` columns in audit TSVs? If so,
  the rename to `_legacy_audit` is required, not optional.
- Does the project want to schedule P5b? If yes, that is a new spec under
  `2026-MM-DD-peak-pipeline-real-cwt-ridge-tracking-spec.md`.

## Cleanup Hook

Implementation should leave a clean marker so Phase 2 C2 (resolver collapse)
can identify CWT-related audit rows for bulk removal if the project decides
to retire the CWT proposal source entirely:

- the new `cwt_audit_filter_reason` column is the **single canonical marker**
  for CWT-suppressed boundary hypotheses. Do not introduce parallel markers
  (e.g. a separate `cwt_filtered_*` flag elsewhere). C2 will grep for this
  one column when deleting CWT audit rows.
- keep the `centwave_cwt` proposal source name unchanged. C2 may decide to
  delete the proposal source entirely; using the same string makes the
  removal mechanical.
- the audit-side filter logic in `peak_candidate_boundaries.py` is a
  **separate code path** from production scoring. Do not share helpers with
  `region_safe_merge.py`'s use of `enumerate_boundary_hypotheses`.

## Acceptance Owner

Same protocol. Validation outputs reviewed, before / after diff is empty for
P5a, go / no-go note recorded.
