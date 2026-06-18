# Lockbox Review Packet: LOCKBOXV1_1B346808EB5F8C1F2B2AB9E4

Status: human label packet only; no product write authority.

## Identity

- Row ID: `9350DD43FD96896E65CC0125BA4500013FB22E15DF0C47D92509BB600321874A`
- Family ID: `FAM015251`
- Sample ID: `TumorBC2281_DNA`
- Analyte: `not_applicable_untargeted_backfill`
- Source stratum: `missing_overlay_evidence_gap`
- Current machine decision: `evidence_required`

## Candidate Peak

- area=27702.8; height=not_available; apex_rt_min=not_available; start_rt_min=not_available; end_rt_min=not_available
- Known blockers: `missing_overlay_path`
- Risk tags: `missing_overlay`

## Evidence

- Evidence status: `recovered_visual_evidence`
- Missing evidence reason: `none`
- Trace data: `output/standard_peak_backfill_preset_85raw_20260610/alignment_preset_dna_dr_85raw_validation_minimal/standard_peak_backfill_preset/chunks/r361_480/family_ms1_overlay_batch/412_fam015251_retained_backfill_missing_overlay_trace_data.json`
- Overlay PNG: `output/standard_peak_backfill_preset_85raw_20260610/alignment_preset_dna_dr_85raw_validation_minimal/standard_peak_backfill_preset/chunks/r361_480/family_ms1_overlay_batch/412_fam015251_retained_backfill_missing_overlay.png`
- Hypothesis PNG: `output/standard_peak_backfill_preset_85raw_20260610/alignment_preset_dna_dr_85raw_validation_minimal/standard_peak_backfill_preset/chunks/r361_480/family_ms1_overlay_batch/412_fam015251_retained_backfill_missing_overlay_hypothesis.png`
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

`lockbox_sampling_manifest=6EE391F1689030DB325DEEB7CAA09AA067D189F091A11367ABAB00CFAB0E2D17;mechanical_adjudication_index=B3F1ECE9FEC7EB65BCD76C6D09FB2F9A277FF3D8C2759E0149BC322FB73AEAA7;source_audit=C503494F6B72D195C38968A89AEE04B88702BCD4E820B94FAF4444E7A3971EC1;trace_overlay_recovery_report=6271A73ECA48A686B83A5AE88AA5EDF87DA861108211AA76A927E77DF8678615;trace=04255C5164F48C1017962893391B4B27C22350C432B110F1C3A2A6CC26B64DFB;overlay=5159D114A8B54271FDDDF1F9ACBD3B405C0C1DBF3FF2F1A5AE690591658CEC0A;hypothesis=61585B2E6A859E2F47AA7EC68806F456B10758AFFA9E7A96410558CAF3DA2267`
