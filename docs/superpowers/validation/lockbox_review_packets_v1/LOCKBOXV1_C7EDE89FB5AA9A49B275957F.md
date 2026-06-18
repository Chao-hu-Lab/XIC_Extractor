# Lockbox Review Packet: LOCKBOXV1_C7EDE89FB5AA9A49B275957F

Status: human label packet only; no product write authority.

## Identity

- Row ID: `3A01197FB74DD37423E65C28BD986FE922BF11BB082F8822DB761577A4906E03`
- Family ID: `FAM018580`
- Sample ID: `Breast_Cancer_Tissue_pooled_QC_4`
- Analyte: `not_applicable_untargeted_backfill`
- Source stratum: `missing_overlay_evidence_gap`
- Current machine decision: `evidence_required`

## Candidate Peak

- area=388568; height=not_available; apex_rt_min=not_available; start_rt_min=not_available; end_rt_min=not_available
- Known blockers: `missing_overlay_path`
- Risk tags: `missing_overlay`

## Evidence

- Evidence status: `recovered_visual_evidence`
- Missing evidence reason: `none`
- Trace data: `output/standard_peak_backfill_preset_85raw_20260610/alignment_preset_dna_dr_85raw_validation_minimal/standard_peak_backfill_preset/chunks/r481_600/family_ms1_overlay_batch/530_fam018580_retained_backfill_missing_overlay_trace_data.json`
- Overlay PNG: `output/standard_peak_backfill_preset_85raw_20260610/alignment_preset_dna_dr_85raw_validation_minimal/standard_peak_backfill_preset/chunks/r481_600/family_ms1_overlay_batch/530_fam018580_retained_backfill_missing_overlay.png`
- Hypothesis PNG: `output/standard_peak_backfill_preset_85raw_20260610/alignment_preset_dna_dr_85raw_validation_minimal/standard_peak_backfill_preset/chunks/r481_600/family_ms1_overlay_batch/530_fam018580_retained_backfill_missing_overlay_hypothesis.png`
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

`lockbox_sampling_manifest=6EE391F1689030DB325DEEB7CAA09AA067D189F091A11367ABAB00CFAB0E2D17;mechanical_adjudication_index=B3F1ECE9FEC7EB65BCD76C6D09FB2F9A277FF3D8C2759E0149BC322FB73AEAA7;source_audit=C503494F6B72D195C38968A89AEE04B88702BCD4E820B94FAF4444E7A3971EC1;trace_overlay_recovery_report=6271A73ECA48A686B83A5AE88AA5EDF87DA861108211AA76A927E77DF8678615;trace=3A5113380C074B8A0C92D0FD87433E876D3297F32C33788B208BE9D16E13F290;overlay=70BDF1BA3A81959F3CF983D702D0515B91B48E6CDC58A37FE85AFF0C8573A227;hypothesis=1B92EF61C475CA5749EDE4D32F8A7AFAEEF9D2E55D082FAED5FD81CFCD5FA438`
