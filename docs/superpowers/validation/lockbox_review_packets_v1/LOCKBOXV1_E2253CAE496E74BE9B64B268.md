# Lockbox Review Packet: LOCKBOXV1_E2253CAE496E74BE9B64B268

Status: human label packet only; no product write authority.

## Identity

- Row ID: `not_available`
- Family ID: `TARGET::N6-HE-dA`
- Sample ID: `BenignfatBC0980_DNA`
- Analyte: `N6-HE-dA`
- Source stratum: `manual_wrong_peak_or_no_peak`
- Current machine decision: `known_manual_negative`

## Candidate Peak

- area=not_available; height=not_available; apex_rt_min=not_available; start_rt_min=not_available; end_rt_min=not_available
- Known blockers: `block_candidate_switch`
- Risk tags: `wrong_peak`

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

Manual negative control; do not promote without independent truth.

## Label Fields

- `peak_choice_label`: correct | wrong_peak | wrong_family | unresolved | insufficient_evidence
- `area_label`: acceptable | unacceptable | not_assessable
- `boundary_label`: acceptable | too_wide | too_narrow | shifted | not_assessable
- `reviewer_confidence`: high | medium | low
- `reviewer_reason_code`: use one allowed code from the README
- `evidence_viewed`: packet | packet_trace_overlay_hypothesis | packet_recovered_trace_overlay_hypothesis | packet_missing_evidence_record

Do not enter replacement values. Keep source artifact hashes unchanged. Labels do not grant ProductWriter authority.

## Source Hashes

`lockbox_sampling_manifest=6EE391F1689030DB325DEEB7CAA09AA067D189F091A11367ABAB00CFAB0E2D17;manual_negative_fixture=C3B6896653A46DC60281528EAA8B414020D3FBCE8A6A0FD4E0C047E3CA2C5A38`
