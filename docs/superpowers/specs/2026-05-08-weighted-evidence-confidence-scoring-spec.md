# Weighted Evidence Confidence Scoring — Spec

**Date:** 2026-05-08
**Status:** Draft
**Implementation plan:** `docs/superpowers/plans/2026-05-08-weighted-evidence-confidence-scoring.md`

---

## 1. Background

The current peak confidence model is a pure penalty model:

```text
total_severity = sum(minor/major severities) + quality_penalty

0     -> HIGH
1-2   -> MEDIUM
3-4   -> LOW
>=5   -> VERY_LOW
```

This is stable and simple, but it is no longer expressive enough for the current
selection problem:

- Positive evidence only means "no penalty"; it cannot actively support a peak.
- All major defects have similar numeric size even when the analytical risk is
  very different.
- Some behavior now exists as hard-coded exceptions, for example paired anchor
  mismatch forcing `VERY_LOW`.
- Strong direct evidence such as strict candidate-level NL and ISTD-pair RT
  alignment cannot be represented as a positive reason to trust a weak MS1 peak.
- Weak or contradictory peaks can still look detected unless confidence caps
  and detection summaries are kept in sync.

The next model should make both positive and negative evidence explicit while
preserving the current safety principle: structural contradictions must not be
washed out by unrelated positive evidence.

## 2. Goals

1. Replace pure severity summing with a weighted evidence score.
2. Represent positive evidence and negative evidence separately.
3. Convert current exceptional downgrades into explicit cap rules.
4. Preserve existing public output columns and workbook sheet names.
5. Keep `legacy_savgol` default and keep resolver behavior unchanged.
6. Keep `VERY_LOW` out of detection-rate calculations.
7. Make `Reason` easier to interpret by showing supporting evidence and concerns.
8. Validate with unit tests, 8-raw tissue subset, then 85-raw tissue run.

## 3. Non-Goals

- Do not change XIC extraction, area integration, or local-minimum candidate
  formation.
- Do not tune resolver parameters.
- Do not add target-specific exceptions.
- Do not use positive scoring to force peaks into detected status when NL or RT
  evidence is structurally contradictory.
- Do not change workbook default schema.
- Do not change CLI or GUI settings in this stage.

## 4. Conceptual Model

### 4.1 Score

Every candidate starts from a neutral score:

```text
base_score = 50
raw_score = base_score + positive_points - negative_points
```

The raw score maps to confidence:

| Raw score | Confidence |
|---:|---|
| `>= 80` | `HIGH` |
| `60-79` | `MEDIUM` |
| `40-59` | `LOW` |
| `< 40` | `VERY_LOW` |

### 4.2 Caps

Caps are evaluated after raw score:

```text
confidence = min(score_confidence, strongest_applicable_cap)
```

Caps are not "extra penalties". They express analytical contradictions where a
candidate cannot be trusted above a certain confidence even if other evidence is
strong.

### 4.3 Detection Contract

Default detection rate counts only rows that satisfy all of these:

```text
RT numeric
Area numeric and > 0
NL is OK, WARN, or blank for no-NL targets
Confidence is HIGH, MEDIUM, or LOW
```

Rows with `NL_FAIL`, `NO_MS2` when `count_no_ms2_as_detected=false`, or
`VERY_LOW` are review rows, not detected rows.

### 4.4 Reader Contract

Confidence must map to a user-facing decision, not only an internal score:

| Confidence | Detection role | Reader meaning |
|---|---|---|
| `HIGH` | Counted | Strong accepted detection. |
| `MEDIUM` | Counted | Accepted detection with minor concerns. |
| `LOW` | Counted | Accepted detection that deserves review. |
| `VERY_LOW` | Not counted | Evidence retained for review only. |

Default `Reason` text should lead with the decision, then the strongest cap,
then the evidence. A row with a cap should not start with positive support,
because that hides the reason the row was excluded from detection.

Preferred reason order:

```text
decision: accepted
decision: review only, not counted; cap: VERY_LOW due to anchor mismatch
support: strict NL OK; local S/N strong
concerns: anchor mismatch; RT prior far
```

Reason grammar:

1. The first segment is always `decision: ...`.
2. If a cap exists, the second segment is always `cap: ...`.
3. `support:` appears before `concerns:`.
4. Default reason text shows at most three support labels and four concern
   labels.
5. Extra details stay in optional Score Breakdown, not the default `Reason`
   column.

### 4.5 Accepted Detection Decision Table

This table is the shared contract for Summary, HTML charts, heatmap states, and
Score Breakdown `Detection Counted`.

| Row state | RT | Area | NL | Confidence | Detection Counted | HTML / review state |
|---|---|---:|---|---|---|---|
| Accepted clean detection | numeric | `>0` | `OK`, `WARN_*`, or blank no-NL | `HIGH` or `MEDIUM` | `TRUE` | Clean detected unless separately queued. |
| Accepted review detection | numeric | `>0` | `OK`, `WARN_*`, or blank no-NL | `LOW` | `TRUE` | Detected but review-worthy. |
| Review-only evidence | numeric | `>0` | any allowed value | `VERY_LOW` | `FALSE` | Review only, not detected. |
| Strict NL failure | numeric | `>0` | `NL_FAIL` | any confidence | `FALSE` | Not detected, NL concern. |
| No MS2 excluded by setting | numeric | `>0` | `NO_MS2` | any confidence | `FALSE` when `count_no_ms2_as_detected=false` | Not detected, no-MS2 concern. |
| Zero or invalid area | numeric or missing | `<=0` or invalid | any | any confidence | `FALSE` | Not detected. |
| No peak | `ND` or invalid | `ND` or invalid | any | any confidence | `FALSE` | Not detected. |

## 5. Evidence Categories

### 5.1 Positive Evidence

| Evidence | Points | Conditions |
|---|---:|---|
| `strict_nl_ok` | `+30` | Candidate-aligned strict neutral-loss evidence is OK. |
| `no_nl_required` | `+10` | Target has no neutral-loss requirement and MS1 peak is valid. |
| `rt_prior_close` | `+15` | Candidate is within soft RT-prior threshold. |
| `paired_istd_aligned` | `+20` | Paired analyte is close to target NL anchor or fallback ISTD anchor. |
| `local_sn_strong` | `+10` | Local S/N passes current soft threshold. |
| `shape_clean` | `+10` | Symmetry and width are both clean. |
| `trace_clean` | `+10` | No ADAP-like trace quality flags. |

Positive evidence is deliberately bounded. A peak should not reach `HIGH` by
one feature alone.

### 5.2 Negative Evidence

| Evidence | Points | Conditions |
|---|---:|---|
| `nl_fail` | `-45` | MS2 was present but strict candidate-level NL failed. |
| `no_ms2` | `-25` | No usable MS2 trigger for an NL-required target. |
| `rt_prior_far` | `-35` | Candidate is beyond hard RT-prior threshold. |
| `rt_prior_borderline` | `-15` | Candidate is beyond soft RT-prior threshold. |
| `anchor_mismatch` | `-45` | Paired analyte violates target/fallback anchor tolerance. |
| `local_sn_poor` | `-25` | Local S/N fails hard threshold. |
| `local_sn_borderline` | `-10` | Local S/N fails soft threshold. |
| `shape_poor` | `-20` | Symmetry or width fails hard threshold. |
| `shape_borderline` | `-10` | Symmetry or width fails soft threshold. |
| `low_scan_support` | `-15` | Local-minimum candidate has low scan support. |
| `low_trace_continuity` | `-10` | Trace continuity is poor. |
| `poor_edge_recovery` | `-10` | Peak edges do not recover to local baseline/valley. |
| `hard_quality_flag` | `-25` | Non-ADAP hard quality flag remains after suppression. |

### 5.3 Confidence Caps

| Cap | Max confidence | Conditions |
|---|---|---|
| `nl_fail_cap` | `VERY_LOW` | NL-required target has candidate-level `NL_FAIL`. |
| `no_ms2_cap` | `LOW` | NL-required target has `NO_MS2`; if `count_no_ms2_as_detected=false`, detection still excludes it. |
| `anchor_mismatch_cap` | `VERY_LOW` | Paired analyte violates anchor tolerance. |
| `zero_area_cap` | `VERY_LOW` | Candidate somehow has non-positive area after candidate formation. This should be rare because malformed candidates are filtered earlier. |
| `no_peak_cap` | `ND` | No candidate peak exists. This remains a detection status, not a confidence level. |

Caps should be surfaced in reason text. For example:

```text
decision: review only, not counted; cap: VERY_LOW due to anchor mismatch
support: strict NL OK; local S/N strong
concerns: anchor mismatch; RT prior far
```

## 6. Selection Contract

Candidate selection should use confidence score and selection distance without
lexicographic surprises:

1. Reject no-peak and malformed candidates before scoring.
2. Score every candidate into:
   - `raw_score`
   - `positive_evidence`
   - `negative_evidence`
   - `caps`
   - `confidence`
   - `selection_penalty`
3. If a strict preferred RT is active, distance to the strict RT remains the
   first selector key.
4. Otherwise, compare candidates by:

```text
effective_score = raw_score - selection_distance_penalty - selection_quality_penalty
```

5. `selection_distance_penalty` is proportional to distance from the selection
   reference and must be in score points, not tuple priority.
6. The selector may prefer a lower-confidence candidate only if its
   `effective_score` is higher after distance and quality penalties.
7. `VERY_LOW` candidates may be selected for row-level review, but Summary
   detection does not count them as detected.

## 7. Output Contract

Default workbook columns stay unchanged:

- `Confidence`
- `Reason`
- existing RT/Area/NL/diagnostic columns

Optional Score Breakdown should become more useful if enabled:

Decision fields must appear immediately after identity fields. The sheet is a
debug surface, but it should still answer "why was this counted or not counted?"
before showing raw severity components.

| Field | Meaning |
|---|---|
| `Final Confidence` | Confidence after caps. |
| `Detection Counted` | `TRUE` only if the row satisfies the accepted detection predicate. |
| `Caps` | Applied caps, if any. |
| `Raw Score` | Base + positive - negative. |
| `Support` | Semicolon-separated positive evidence labels. |
| `Concerns` | Semicolon-separated negative evidence labels. |
| `Base Score` | Always `50` in v1. |
| `Positive Points` | Sum of supporting evidence. |
| `Negative Points` | Sum of concerns. |

This optional sheet may change because it is explicitly a debug surface. Default
delivery workbook sheets and row-level columns must stay stable.

HTML review report widgets must use the same accepted-detection predicate as
the workbook Summary. `VERY_LOW` rows may appear in review details, but charts
and detection-rate labels must not present them as detected.

## 8. Real-Data Acceptance

Run in this order:

1. Unit and workbook tests.
2. 8-raw tissue subset with `parallel_workers=4`.
3. 85-raw tissue full run with `parallel_workers=4`.

Acceptance criteria:

- `8-oxo-Guo` remains `2/85` on the full tissue run unless real evidence changes.
- `8-oxodG` mismatched RT rows remain review rows, not detected rows.
- `d3-N6-medA` ISTD remains stable; CV should not regress materially from the
  post-selection-fix run.
- `Area=0` detected rows remain `0`.
- Major changes in `N6-HE-dA`, `N6-medA`, or `dG-C8-MeIQx` must be explained by
  support/concern/cap reason text.

Concrete expected outcomes:

| Case | Expected Summary behavior | Expected row-level behavior |
|---|---|---|
| `8-oxo-Guo` tissue full run | `2/85` accepted detections unless new manual evidence says otherwise. | Other rows may retain RT/Area evidence but must be `VERY_LOW` or otherwise not counted. |
| `8-oxodG` RT/ISTD-mismatched rows | `0/85` if only mismatched rows remain. | Rows should lead with `decision: review only, not counted` and an anchor/RT concern. |
| `d3-N6-medA` ISTD | Accepted ISTD detections should remain stable. | Soft trace-quality concerns must not alone remove good ISTD anchors. |
| `Area=0` rows | Always excluded from detection counts. | Row may exist for audit, but `Detection Counted` must be `FALSE`. |

## 9. Open Design Decisions For Implementation Review

These values are intentionally concrete for v1, but should be reviewed after
the 8-raw and 85-raw outputs:

- Score threshold cutoffs: `80/60/40`.
- `strict_nl_ok = +30`.
- `nl_fail = -45` plus `VERY_LOW` cap.
- Whether `NO_MS2` should cap at `LOW` or `VERY_LOW` for all NL-required analytes.
- Whether `paired_istd_aligned` should require the ISTD itself to be at least
  `LOW` confidence.
