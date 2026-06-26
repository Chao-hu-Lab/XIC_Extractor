# Lockbox Review Packet: LOCKBOXV1_5E855976CC5B80B8E6CBB752

Status: human label packet only; no product write authority.

## Identity

- Row ID: `B729B05046E35638A342031F521A1CF5DC7FF30C87F6061D7377208ECAC8BCDA`
- Family ID: `FAM017220`
- Sample ID: `Breast_Cancer_Tissue_pooled_QC2`
- Analyte: `not_applicable_untargeted_backfill`
- Source stratum: `unresolved_apex_delta`
- Current machine decision: `evidence_required`

## Candidate Peak

- area=4.73447e+07; height=4.87774e+06; apex_rt_min=40.375; start_rt_min=40.2502; end_rt_min=40.7494
- Known blockers: `apex_delta_gt_0.15;scan_count_gt_9;height_gte_2000000`
- Risk tags: `apex_delta;scan_count;height`

## Evidence

- Evidence status: `complete_visual_evidence`
- Missing evidence reason: `none`
- Trace data: `output/standard_peak_backfill_preset_85raw_20260610/alignment_preset_dna_dr_85raw_validation_minimal/standard_peak_backfill_preset/chunks/r601_671/family_ms1_overlay_batch/662_fam017220_retained_backfill_missing_overlay_trace_data.json`
- Overlay PNG: `output/standard_peak_backfill_preset_85raw_20260610/alignment_preset_dna_dr_85raw_validation_minimal/standard_peak_backfill_preset/chunks/r601_671/family_ms1_overlay_batch/662_fam017220_retained_backfill_missing_overlay.png`
- Hypothesis PNG: `output/standard_peak_backfill_preset_85raw_20260610/alignment_preset_dna_dr_85raw_validation_minimal/standard_peak_backfill_preset/chunks/r601_671/family_ms1_overlay_batch/662_fam017220_retained_backfill_missing_overlay_hypothesis.png`
- Nearest competing candidate: `not_available_in_current_artifacts`

## Review Question

Independently label peak choice, area acceptability, and boundary quality. Do not enter replacement values.

## Why This Is Not Auto-Written

independent_peak_choice_or_area_truth

## Label Fields

- `peak_choice_label`: correct | wrong_peak | wrong_family | unresolved | insufficient_evidence
- `area_label`: acceptable | unacceptable | not_assessable
- `boundary_label`: acceptable | too_wide | too_narrow | shifted | not_assessable
- `reviewer_confidence`: high | medium | low
- `reviewer_reason_code`: use one allowed code from the README
- `evidence_viewed`: packet | packet_trace_overlay_hypothesis | packet_recovered_trace_overlay_hypothesis | packet_missing_evidence_record

Do not enter replacement values. Keep source artifact hashes unchanged. Labels do not grant ProductWriter authority.

## Source Hashes

`lockbox_sampling_manifest=6EE391F1689030DB325DEEB7CAA09AA067D189F091A11367ABAB00CFAB0E2D17;review_queue=F3DA270A98B162F0523486E67BB03B19AEE86F48889214FB602607DB9AA22B5C;mechanical_adjudication_index=B3F1ECE9FEC7EB65BCD76C6D09FB2F9A277FF3D8C2759E0149BC322FB73AEAA7;review_queue=F3DA270A98B162F0523486E67BB03B19AEE86F48889214FB602607DB9AA22B5C;trace=D3559B3343B93CB83FFD3DE79EAB9B8987E4CD8C04E5EE88C34B8411B861EC31;overlay=09545DEA073CD4904E6658D504A262B08CEA36FFC2A896461F8E9C7BD31EA8DB;hypothesis=AC6A456AAC989F83904314AE6F9A40C066C0F61AF7654DD740BD1E1E142A2206`
