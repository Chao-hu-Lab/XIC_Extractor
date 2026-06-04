# Selected Envelope Paired-RT Root Cause Note

**Date:** 2026-06-03
**Readiness label:** `diagnostic_only`

## Verdict

`TumorBC2263_DNA / 8-oxodG` was not primarily a selected-envelope boundary
failure. The earlier plot was following the wrong target candidate at
18-19 min. Manual Xcalibur review showed the expected 8-oxodG/15N5-8-oxodG
pair near 16 min.

Root cause:

- the paired ISTD `15N5-8-oxodG` was correctly selected at 16.642 min with
  strong MS1/MS2/NL evidence;
- the analyte `8-oxodG` was allowed to use a distant target-specific NL anchor
  at 18.30999 min as the extraction-window anchor;
- that shifted the analyte XIC window to 17.3-19.3 min, excluding the real
  16 min peak from candidate enumeration;
- selected-envelope diagnostics then correctly revealed a wrong-peak conflict,
  but boundary tuning could not fix the upstream candidate-window error.

## Contract Update

In paired targeted mode, paired ISTD RT is the primary biological-matrix
transfer anchor. Target-specific NL/product anchors are supporting evidence
only when they are close to the paired ISTD RT. A distant target-specific NL
anchor must not move the extraction window away from the ISTD-supported RT
region by itself.

This is targeted-only product behavior. It does not make targeted labels or
targeted pass/fail logic untargeted identity authority.

The paired ISTD RT guard is not a hard STD/analyte backfill rule. ISTD-centered
fallback only reopens the candidate search/review window. If the paired
STD/analyte is absent or has unsupported MS1-only evidence, it remains
`not_counted`; product detection still requires an approved analyte/STD evidence
policy.

## Code Change

Changed:

- `xic_extractor/extraction/rt_windows.py`
- `xic_extractor/extraction/target_extraction.py`
- `xic_extractor/extraction/anchors.py`
- `tests/test_extractor.py`

Added regression coverage:

- `test_paired_analyte_ignores_target_nl_anchor_far_from_istd_anchor`
- `test_paired_analyte_istd_rt_fallback_does_not_force_counted_detection`

The focused regression proved the old behavior first:

```text
preferred_rts == [13.70, 15.10]
```

After the fix, paired analyte extraction stays ISTD-centered when the
target-specific NL anchor is far from the paired ISTD:

```text
preferred_rts == [13.70, 13.70]
analyte XIC window == [12.70, 14.70]
```

The companion product regression keeps fallback separate from counted
detection:

```text
paired analyte fallback RT/area may be reported for review
NL_FAIL + no approved analyte policy -> Counted Detection = FALSE
```

## Real-Data Check

Current 8RAW run after the paired-RT guard:

```text
output/selected_full_envelope_realdata_preflight/fe4_8raw_selected_envelope_paired_rt_20260603/
```

Key TumorBC2263 rows:

```text
15N5-8-oxodG ISTD:
  selected apex RT = 16.64200
  confidence = HIGH
  NL = TRUE
  MS2 trace = strong

8-oxodG analyte:
  selected apex RT = 16.64200
  selection reference RT = 16.56013
  confidence = VERY_LOW
  NL = FALSE
  MS2 trace = none
```

The analyte now follows the 16 min paired RT region instead of the previous
18-19 min wrong peak.

Selected-envelope status for this row remains review-only:

```text
row_boundary_decision = externalize
boundary_change_class = overmerge_rejected
boundary_stop_reason = selected_envelope_narrower_than_resolver
area_delta_ratio = -0.00717
```

That residual boundary issue is a conservative selected-envelope gate, not the
old wrong-peak root cause.

## Next Gate

Rebuild the changed-row review queue and overlay plots from the paired-RT run.
The FE4 selected-envelope gate remains `externalize` until reviewed boundary
oracles exist for promotion-critical rows.
