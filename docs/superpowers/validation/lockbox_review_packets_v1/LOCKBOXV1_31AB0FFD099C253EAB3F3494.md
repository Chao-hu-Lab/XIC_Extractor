# Lockbox Review Packet: LOCKBOXV1_31AB0FFD099C253EAB3F3494

Status: human label packet only; no product write authority.

## Identity

- Row ID: `not_available`
- Family ID: `FAM015133`
- Sample ID: `BenignfatBC1181_DNA`
- Analyte: `not_applicable_untargeted_backfill`
- Source stratum: `failed_oracle_negative`
- Current machine decision: `oracle_negative_only`

## Candidate Peak

- area=1.6765e+07; height=not_available; apex_rt_min=not_available; start_rt_min=8.37621; end_rt_min=8.70762
- Known blockers: `fail_boundary`
- Risk tags: `failed_oracle:fail_boundary`

## Evidence

- Evidence status: `missing_evidence_recorded`
- Missing evidence reason: `trace_overlay_hypothesis_not_available`
- Trace data: `not_available`
- Overlay PNG: `not_available`
- Hypothesis PNG: `not_available`
- Nearest competing candidate: `not_available_in_current_artifacts`

## Review Question

Is there enough evidence to label peak choice? If not, use `insufficient_evidence` and `not_assessable` labels.

## Why This Is Not Auto-Written

Heldout oracle failure is negative evidence; round-trip oracle is not truth.

## Label Fields

- `peak_choice_label`: correct | wrong_peak | wrong_family | unresolved | insufficient_evidence
- `area_label`: acceptable | unacceptable | not_assessable
- `boundary_label`: acceptable | too_wide | too_narrow | shifted | not_assessable
- `reviewer_confidence`: high | medium | low
- `reviewer_reason_code`: use one allowed code from the README
- `evidence_viewed`: packet | packet_trace_overlay_hypothesis | packet_recovered_trace_overlay_hypothesis | packet_missing_evidence_record

Do not enter replacement values. Keep source artifact hashes unchanged. Labels do not grant ProductWriter authority.

## Source Hashes

`lockbox_sampling_manifest=6EE391F1689030DB325DEEB7CAA09AA067D189F091A11367ABAB00CFAB0E2D17;oracle_results=4B942E5FA6DA69B7335FA4ACFBBF6675321DE3FAB8E3A6BE006B701B4995D206`
