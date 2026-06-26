# Lockbox Review Packet: LOCKBOXV1_E32D6B3E2CFC30E75E498693

Status: human label packet only; no product write authority.

## Identity

- Row ID: `38C513A9E6073937493662BEF21D3A262C2DCF7533D6EED3EE97A9E90F210998`
- Family ID: `FAM016101`
- Sample ID: `TumorBC2290_DNA`
- Analyte: `not_applicable_untargeted_backfill`
- Source stratum: `unresolved_low_height`
- Current machine decision: `evidence_required`

## Candidate Peak

- area=266661; height=38417.7; apex_rt_min=13.2825; start_rt_min=12.6743; end_rt_min=13.3661
- Known blockers: `shape_lt_0.95;height_lt_2000000;width_outside_0.30_0.65;scan_count_gt_9`
- Risk tags: `shape;height;width;scan_count`

## Evidence

- Evidence status: `complete_visual_evidence`
- Missing evidence reason: `none`
- Trace data: `output/standard_peak_backfill_preset_85raw_20260610/alignment_preset_dna_dr_85raw_validation_minimal/standard_peak_backfill_preset/chunks/r121_240/family_ms1_overlay_batch/155_fam016101_retained_backfill_missing_overlay_trace_data.json`
- Overlay PNG: `output/standard_peak_backfill_preset_85raw_20260610/alignment_preset_dna_dr_85raw_validation_minimal/standard_peak_backfill_preset/chunks/r121_240/family_ms1_overlay_batch/155_fam016101_retained_backfill_missing_overlay.png`
- Hypothesis PNG: `output/standard_peak_backfill_preset_85raw_20260610/alignment_preset_dna_dr_85raw_validation_minimal/standard_peak_backfill_preset/chunks/r121_240/family_ms1_overlay_batch/155_fam016101_retained_backfill_missing_overlay_hypothesis.png`
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

`lockbox_sampling_manifest=6EE391F1689030DB325DEEB7CAA09AA067D189F091A11367ABAB00CFAB0E2D17;review_queue=F3DA270A98B162F0523486E67BB03B19AEE86F48889214FB602607DB9AA22B5C;mechanical_adjudication_index=B3F1ECE9FEC7EB65BCD76C6D09FB2F9A277FF3D8C2759E0149BC322FB73AEAA7;review_queue=F3DA270A98B162F0523486E67BB03B19AEE86F48889214FB602607DB9AA22B5C;trace=EF63387F59CBE5F7A97A12119D72378186C3C8DB89CED3FAEAA627066EED7602;overlay=1D57E9206AE640FE505C696169AD98BA7F69D2B059744C1C98AE0374B400888E;hypothesis=CA1D5CD5F2BA74DC986D12BAA38759EBDA225EF9E38D49AA9296E74001715F1E`
