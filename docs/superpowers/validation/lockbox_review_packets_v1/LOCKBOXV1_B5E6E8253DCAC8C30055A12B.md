# Lockbox Review Packet: LOCKBOXV1_B5E6E8253DCAC8C30055A12B

Status: human label packet only; no product write authority.

## Identity

- Row ID: `38D3AD60B5B0D846F90D37C460BA51EE1C83614AB265C2885961535631CDDA93`
- Family ID: `FAM017737`
- Sample ID: `Breast_Cancer_Tissue_pooled_QC3`
- Analyte: `not_applicable_untargeted_backfill`
- Source stratum: `missing_overlay_evidence_gap`
- Current machine decision: `evidence_required`

## Candidate Peak

- area=2.18143e+06; height=not_available; apex_rt_min=not_available; start_rt_min=not_available; end_rt_min=not_available
- Known blockers: `missing_overlay_path`
- Risk tags: `missing_overlay`

## Evidence

- Evidence status: `recovered_visual_evidence`
- Missing evidence reason: `none`
- Trace data: `output/standard_peak_backfill_preset_85raw_20260610/alignment_preset_dna_dr_85raw_validation_minimal/standard_peak_backfill_preset/chunks/r241_360/family_ms1_overlay_batch/307_fam017737_retained_backfill_missing_overlay_trace_data.json`
- Overlay PNG: `output/standard_peak_backfill_preset_85raw_20260610/alignment_preset_dna_dr_85raw_validation_minimal/standard_peak_backfill_preset/chunks/r241_360/family_ms1_overlay_batch/307_fam017737_retained_backfill_missing_overlay.png`
- Hypothesis PNG: `output/standard_peak_backfill_preset_85raw_20260610/alignment_preset_dna_dr_85raw_validation_minimal/standard_peak_backfill_preset/chunks/r241_360/family_ms1_overlay_batch/307_fam017737_retained_backfill_missing_overlay_hypothesis.png`
- Nearest competing candidate: `not_available_in_current_artifacts`

## Review Question

Label peak choice from the available evidence. Area and boundary may be `not_assessable` when trace evidence is insufficient.

## Why This Is Not Auto-Written

recover_trace_overlay_or_reintegration_evidence

## Label Fields

- `peak_choice_label`: correct | wrong_peak | wrong_family | unresolved | insufficient_evidence
- `area_label`: acceptable | unacceptable | not_assessable
- `boundary_label`: acceptable | too_wide | too_narrow | shifted | not_assessable
- `reviewer_confidence`: high | medium | low
- `reviewer_reason_code`: use one allowed code from the README
- `evidence_viewed`: packet | packet_trace_overlay_hypothesis | packet_recovered_trace_overlay_hypothesis | packet_missing_evidence_record

Do not enter replacement values. Keep source artifact hashes unchanged. Labels do not grant ProductWriter authority.

## Source Hashes

`lockbox_sampling_manifest=6EE391F1689030DB325DEEB7CAA09AA067D189F091A11367ABAB00CFAB0E2D17;mechanical_adjudication_index=B3F1ECE9FEC7EB65BCD76C6D09FB2F9A277FF3D8C2759E0149BC322FB73AEAA7;source_audit=C503494F6B72D195C38968A89AEE04B88702BCD4E820B94FAF4444E7A3971EC1;trace_overlay_recovery_report=6271A73ECA48A686B83A5AE88AA5EDF87DA861108211AA76A927E77DF8678615;trace=5CE2978AFB78CE6688D50776310EA82DB3D530E89B972030232E088EBDCFD5AF;overlay=264AA5A8D73293F4B82062569DDC25369E7AA0B76AC4C50456748680E8889111;hypothesis=E5CE6959A421C86241962D7C52B16E4D05CC477816A1D121200E27A8769AE6AE`
