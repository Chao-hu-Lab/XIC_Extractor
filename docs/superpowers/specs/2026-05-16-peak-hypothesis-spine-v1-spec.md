# Peak Hypothesis Spine v1 Spec

**Date:** 2026-05-16
**Status:** Implementation slice
**Branch:** `codex/targeted-benchmark-reliability`
**Worktree:** `C:\Users\user\Desktop\XIC_Extractor\.worktrees\targeted-benchmark-reliability`
**Source memo:** `C:\Users\user\Downloads\lcms_gcms_peak_pipeline_handoff.md`

## Summary

Candidate table v1 made rejected peaks visible. The next safe step toward the
handoff architecture is a domain spine that names the object already implied by
the code: a candidate interval plus evidence plus integration plus audit
metadata.

This phase introduces `PeakHypothesis`, `EvidenceVector`, `IntegrationResult`,
and `AuditTrail` as internal peak-detection models and provides an adapter from
existing `PeakDetectionResult` / `PeakCandidateScore` objects. It does not change
peak selection, scoring thresholds, output schema, or workbook behavior.

## Product Contract

This phase must:

- preserve all existing selected peak behavior;
- keep `peak_candidates.tsv` schema unchanged;
- expose the current selected/rejected candidate table through a hypothesis
  model instead of table-specific ad hoc wiring;
- keep local minimum, CWT, baseline correction, and ML as proposal/evidence
  sources, not final authorities;
- provide stable fields that later boundary enumeration and model selection can
  consume.

This phase must not:

- implement CWT;
- implement new baseline correction;
- alter `local_minimum` or `legacy_savgol` decision behavior;
- change targeted reliability states;
- change untargeted matrix identity or alignment gates.

## Domain Model

### IntegrationResult

Represents the quantitative interval result for one hypothesis.

Required v1 fields:

- `rt_left_min`
- `rt_apex_min`
- `rt_right_min`
- `area_raw_counts_seconds`
- `height_raw`
- `height_smoothed`
- `integration_method`
- optional future fields: `area_baseline_corrected`,
  `area_uncertainty`, `baseline_type`, `baseline_score`, `raw_scan_indices`.

### EvidenceVector

Represents evidence already available in current scoring.

Required v1 fields:

- `confidence`
- `raw_score`
- `support_labels`
- `concern_labels`
- `cap_labels`
- `reason`
- `quality_flags`
- `prominence`
- `region_scan_count`
- `region_duration_min`
- `region_edge_ratio`
- `region_trace_continuity`
- `ms2_present`
- `nl_match`
- `ms2_trace_strength`
- `rt_prior_min`

Reserved future fields include CWT ridge, baseline, shape, mz stability, blank,
QC, isotope, adduct, coelution, ion ratio, GC spectral similarity, and retention
index evidence.

### AuditTrail

Represents why the hypothesis exists and what happened to it.

Required v1 fields:

- `proposal_sources`
- `source_apex_rank`
- `merge_note`
- `selected`
- `selection_rank`
- `selection_reference_rt_min`
- `rejection_reason`

### PeakHypothesis

Combines interval, evidence, integration, and audit metadata.

Required v1 fields:

- `hypothesis_id`
- `trace_group_id`
- `target_label`
- `role`
- `istd_pair`
- `analysis_mode`
- `resolver_mode`
- `integration`
- `evidence`
- `audit`

## Data Flow

```text
PeakDetectionResult
  -> PeakHypothesis adapter
  -> candidate table rows
  -> future boundary/model-selection diagnostics
```

The adapter is intentionally downstream of current scoring. It must not become a
hidden selector in this phase.

## Acceptance Criteria

1. Synthetic selected/rejected candidates can be converted to deterministic
   `PeakHypothesis` objects.
2. Exactly one hypothesis is selected when `PeakDetectionResult.status == OK`.
3. `selection_reference_rt_min` reflects the RT actually used by selection, not
   merely the NL anchor found during windowing.
4. Candidate table output remains byte-schema compatible with v1 headers.
5. Existing targeted output remains unchanged when candidate output is disabled.
6. Narrow tests, `ruff`, and `mypy` pass.

## Future Work

After this spine is stable:

1. Add baseline model output into `IntegrationResult`.
2. Add CWT as another proposal/evidence source.
3. Add boundary hypothesis enumeration that yields multiple `PeakHypothesis`
   objects for one apex.
4. Add model selection over non-overlapping hypotheses.
5. Extend the same hypothesis model to untargeted alignment backfill.
