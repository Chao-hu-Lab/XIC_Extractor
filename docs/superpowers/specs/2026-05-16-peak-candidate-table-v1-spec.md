# Peak Candidate Table v1 Spec

**Date:** 2026-05-16
**Status:** Reviewed draft spec
**Branch:** `codex/targeted-benchmark-reliability`
**Worktree:** `C:\Users\user\Desktop\XIC_Extractor\.worktrees\targeted-benchmark-reliability`
**Source memo:** `C:\Users\user\Downloads\lcms_gcms_peak_pipeline_handoff.md`

## Summary

The next useful step for peak picking is not another single winning resolver. The
stable foundation is a visible candidate layer: every resolver proposes peak
candidates, existing evidence scoring evaluates them, and the selected peak is
only one row in a larger candidate table.

This spec defines `Peak Candidate Table v1` as a debug/audit output. It does not
change default peak selection, targeted detection status, untargeted matrix
identity, or workbook handoff behavior.

The goal is to make the current pipeline answer this question:

```text
Why did this peak win, what other plausible peaks existed, and what evidence
made them lose?
```

## Context

The current codebase already has several pieces of the larger
`Trace / TraceGroup / PeakHypothesis / EvidenceVector / ModelSelection` vision:

- `PeakCandidate` is already a lightweight peak hypothesis;
- `PeakDetectionResult.candidates` already carries non-selected candidates in
  memory;
- `legacy_savgol` and `local_minimum` already generate candidate sets;
- `arbitrated` mode now treats both resolvers as proposal sources;
- `ScoringContext`, `score_candidate`, and `EvidenceScore` are already an
  evidence-vector-like layer;
- targeted reliability audit already separates `benchmark_eligible`,
  `targeted_review_positive`, `targeted_review`, and `targeted_negative`;
- raw area is integrated from raw intensity arrays in counts-seconds, not from a
  smoothed trace.

The missing piece is persistence. Once extraction finishes, rejected candidates
and resolver disagreements are mostly gone. That makes it hard to debug
wrong-peak cases, compare resolver behavior, or build future CWT / baseline /
ML layers without guessing.

## Problem

The current selected-result outputs answer:

```text
Which peak did the pipeline choose?
```

They do not reliably answer:

```text
Which candidates were available?
Which resolver proposed each candidate?
Was the selected peak the best evidence-supported candidate or just the highest
MS1 apex?
Did another candidate have better NL / RT / shape evidence?
Was the boundary unstable even when the apex was correct?
```

This is the reason `legacy_savgol` versus `local_minimum` feels hard to decide.
Both can be right in different cases. A single output row hides that.

## Product Contract

`Peak Candidate Table v1` is an optional debug/audit artifact.

It must:

- preserve default selected peak behavior;
- expose all candidates considered by `find_peak_and_area`;
- mark exactly one selected candidate when extraction returns `status == OK`;
- include rejected candidates with an explicit reason when scoring is available;
- include proposal provenance, especially `legacy_savgol`, `local_minimum`, and
  `preferred_rt_recovery`;
- rescore audit candidate rows after same-apex CWT provenance is merged so
  `cwt_same_apex_support` is visible as bounded positive evidence;
- include enough RT, boundary, integration, quality, and evidence fields to
  reproduce a selection decision without reopening raw files;
- be TSV-first so downstream diagnostics can consume it without Excel.

It must not:

- change `XIC Results` default columns;
- change the workbook `Matrix`, untargeted final matrix, or alignment contract;
- make `arbitrated` the default resolver;
- introduce CWT as a final resolver authority, ML, or deep learning in v1;
- give CWT-only or far CWT alternatives an automatic confidence bonus or
  demotion authority;
- make local minimum a final boundary authority;
- treat candidate table output as a production quantitative matrix.

## Output Surface

### File

```text
peak_candidates.tsv
```

Default behavior:

```text
emit_peak_candidates = false
```

When enabled, the file should be written beside existing targeted extraction
outputs. In a future alignment implementation, the same schema may be written
beside alignment diagnostics, but this v1 spec is targeted-extraction first.

### Workbook

No workbook sheet is required in v1.

If a later plan adds a workbook sheet, it must be a debug/review sheet and must
not become part of the canonical downstream handoff without a separate schema
review.

## Candidate Row Semantics

Each row represents one candidate interval after candidate-source merging.

For `arbitrated` mode, if two proposal sources produce the same apex index, they
may be merged into one row with multiple proposal sources. If they produce
different apexes or different effective intervals, they remain separate rows.

Candidate identity must be deterministic. Do not use Python object ids.

Suggested candidate id:

```text
candidate_id =
  sample_name + target_label + resolver_mode + proposal_sources
  + rt_apex rounded to 5 decimals
  + rt_left rounded to 5 decimals
  + rt_right rounded to 5 decimals
```

This id is an audit key, not a cross-run scientific feature id.

## Required Columns

### Run And Target Context

| Column | Meaning |
|---|---|
| `sample_name` | Sample name used in `XIC Results`. |
| `group` | Sample group when available. |
| `target_label` | Target label. |
| `role` | `Analyte`, `ISTD`, or existing role text. |
| `istd_pair` | Existing ISTD pair label when available. |
| `analysis_mode` | `targeted` in v1. Future values may include `untargeted` or `alignment_backfill`. |
| `resolver_mode` | Configured resolver mode, such as `legacy_savgol`, `local_minimum`, or `arbitrated`. |
| `candidate_id` | Deterministic candidate audit id. |

### Proposal Provenance

| Column | Meaning |
|---|---|
| `proposal_sources` | Semicolon-separated proposal sources, such as `legacy_savgol`, `local_minimum`, `preferred_rt_recovery`, `centwave_cwt`. |
| `proposal_count` | Number of proposal sources represented by this row. |
| `source_apex_rank` | Rank within the source by source-native order or intensity. |
| `merge_note` | Empty, `same_apex_merged`, `source_only`, or another explicit merge note. |

Proposal sources:

- `centwave_cwt`;
- `rt_prior`;
- `aligned_gapfill`.

Only `centwave_cwt` is implemented after the candidate-table v1 baseline, and
only as an audit proposal. The other names remain reserved candidate proposal
sources. Boundary-only sources such as `derivative_zero_crossing`,
`baseline_return`, and `cwt_width` live in `peak_candidate_boundaries.tsv`, not
in candidate proposal provenance.

### RT And Integration

| Column | Meaning |
|---|---|
| `rt_left_min` | Candidate left boundary in minutes. |
| `rt_apex_min` | Selected/scoring apex RT in minutes. |
| `rt_right_min` | Candidate right boundary in minutes. |
| `raw_apex_rt_min` | Raw apex RT in minutes. |
| `rt_width_min` | `rt_right_min - rt_left_min`. |
| `selection_apex_intensity` | Intensity used by candidate selection. |
| `raw_apex_intensity` | Raw apex intensity. |
| `prominence` | Source-derived prominence. |
| `area_raw_counts_seconds` | Raw trapezoid area in counts-seconds. |
| `area_baseline_corrected` | Debug-only `linear_edge` baseline-corrected area when trace data is available. Empty otherwise. |
| `area_uncertainty` | Debug-only local baseline uncertainty estimate when trace data is available. Empty otherwise. |

### Trace Quality

| Column | Meaning |
|---|---|
| `quality_flags` | Semicolon-separated candidate quality flags. |
| `region_scan_count` | Number of scans in the candidate region when available. |
| `region_duration_min` | Candidate region duration when available. |
| `region_edge_ratio` | Local edge ratio when available. |
| `region_trace_continuity` | Local continuity metric when available. |

### Evidence And Scoring

| Column | Meaning |
|---|---|
| `ms2_present` | Candidate-level MS2 evidence when available. |
| `nl_match` | Candidate-level neutral-loss evidence when available. |
| `ms2_trace_strength` | Existing MS2 trace strength when available. |
| `rt_prior_min` | RT prior used for scoring when available. |
| `rt_prior_sigma` | RT prior sigma when available. |
| `confidence` | Candidate confidence after scoring, when available. |
| `raw_score` | Weighted evidence raw score when available. |
| `support_labels` | Semicolon-separated positive evidence labels. |
| `concern_labels` | Semicolon-separated negative evidence labels. |
| `cap_labels` | Semicolon-separated confidence caps. |
| `reason` | Existing scoring reason text. |

Rows generated without a scoring context may leave evidence columns empty, but
must still include RT, boundary, integration, and proposal provenance fields.

### Selection Outcome

| Column | Meaning |
|---|---|
| `selected` | `TRUE` for the selected candidate, `FALSE` otherwise. |
| `selection_rank` | Rank after final selection when available. |
| `selection_reference_rt_min` | Preferred RT / selection RT used by selection when available. |
| `rejection_reason` | Empty for selected row. For rejected rows, a concise reason such as `lower_score`, `farther_from_preferred_rt`, `lower_confidence`, `quality_penalty`, or `non_selected_candidate`. |

## Data Flow

```text
raw trace
  -> candidate proposal sources
      - legacy_savgol
      - local_minimum
      - preferred_rt_recovery when applicable
  -> candidate merge / provenance preservation
  -> candidate-level MS2 / NL context
  -> scoring
  -> selected candidate
  -> XIC Results row
  -> peak_candidates.tsv rows for all candidates
```

The candidate table is downstream of candidate formation and scoring. It should
not become a new hidden decision engine.

## Implementation Boundary

### Allowed v1 Changes

- Add optional provenance fields to `PeakCandidate` with safe defaults.
- Add a small candidate-table row model and TSV writer.
- Add a targeted extraction accumulator that records candidates for each target
  extraction call.
- Add `emit_peak_candidates` config / CLI / settings schema support with default
  `false`.
- Add tests proving disabled output is a no-op.
- Add tests proving enabled output contains selected and rejected candidates.

### Not Allowed In v1

- No CWT selected-peak behavior change.
- No baseline correction method change.
- No ML classifier.
- No selected-peak behavior change.
- No untargeted production matrix schema change.
- No forced workbook sheet.
- No GC-MS implementation.

## Edge Cases

### No Peak Found

If `find_peak_and_area` returns no candidates, v1 may either:

- emit no candidate rows; or
- emit one diagnostic row with `selected=FALSE` and `rejection_reason=no_candidate`.

The recommended v1 behavior is no candidate rows plus a separate extraction
diagnostic entry, because a candidate table should represent candidate
intervals, not target-level missingness.

### Recovery Candidate

If preferred-RT recovery adds a candidate, it must appear as a row with
`proposal_sources` including `preferred_rt_recovery`.

If recovery wins, the selected row must be the recovery candidate. Other
candidates remain visible with rejection reasons.

### Same Apex From Multiple Sources

If `legacy_savgol` and `local_minimum` produce the same apex index, the row
should preserve both proposal sources. If one source contributes richer local
quality fields, those fields may be retained, but the merged row must not hide
that multiple sources supported the candidate.

### Different Boundary For Same Apex

If sources agree on apex but disagree materially on left/right boundary, v1 may
keep separate rows. This is important because boundary disagreement is one of
the main integration-risk signals.

Material boundary disagreement default:

```text
abs(left_a - left_b) > 0.02 min
or abs(right_a - right_b) > 0.02 min
```

This threshold is an audit merge threshold, not a scientific acceptance rule.

### CWT Audit Proposals

After candidate table v1, `centwave_cwt` is allowed as an audit proposal source
when `emit_peak_candidates=true`. It is inspired by XCMS centWave's multi-scale
chromatographic peak proposal concept, but in this project it is not a resolver
mode and does not select the final peak.

If CWT agrees with the selected apex, the selected row may add `centwave_cwt`
to `proposal_sources` and keep the production interval. If CWT finds an
additional apex, that row must be `selected=FALSE` and available for review or
future model-selection experiments only.

When more than one existing candidate is inside the CWT apex merge window, CWT
provenance must prefer the production-selected candidate. This prevents a
near-apex legacy/local shadow row from carrying CWT support while the selected
row appears unsupported. The merge changes audit provenance only; it must not
change the selected peak, RT, area, or workbook result.

Same-apex CWT support now participates in the candidate-table evidence layer as
the bounded positive label `cwt_same_apex_support`. The support applies only
when `centwave_cwt` is merged with at least one non-CWT proposal source and CWT
scale or ridge-persistence evidence is present. If neutral loss is required,
the candidate must also have matching NL/MS2 evidence before CWT can add
positive support. CWT-only rows and chemically unconfirmed far CWT alternatives
remain audit/challenger context; they do not receive this support bonus and do
not demote the selected peak.

`tools/diagnostics/cwt_peak_candidate_audit.py` summarizes candidate-table CWT
evidence after extraction. It classifies each sample/target/resolver group as:

- `selected_cwt_agreed`: the selected row itself includes `centwave_cwt`;
- `selected_cwt_nearby`: the selected row does not include CWT provenance, but
  the nearest CWT proposal is within the audit RT window;
- `selected_cwt_far_alternative`: CWT proposes a farther apex than the selected
  row, but this is not evidence that the selected peak is wrong;
- `selected_without_cwt`: no CWT proposal exists for the group.

`selected_cwt_nearby` prevents the report from overcalling disagreements when
CWT support merged into a neighboring non-selected candidate inside the same
peak region. The default nearby window is an audit parameter, not a production
selection rule.

Manual review of the 8RAW far-alternative cases found that the selected peaks
were acceptable. Therefore CWT far alternatives are a diagnostic context signal
only; they must not be treated as a hard selection error, demotion reason, or
benchmark failure.

The report also emits `cwt_conditioned_class` to bind CWT shape proposals to
chemical evidence:

- `cwt_selected_support`: CWT agrees with the selected peak or is within the
  nearby audit RT window.
- `cwt_far_unconfirmed`: CWT proposes a farther apex without matching
  `NL=TRUE` and `ms2_trace_strength in {moderate, strong}`.
- `cwt_far_chemically_plausible`: CWT proposes a farther apex that also has
  matching NL and moderate/strong MS2 trace support.
- `no_cwt_proposal`: no CWT proposal exists for the group.

Only `cwt_far_chemically_plausible` should be prioritized as a possible future
selection challenger. `cwt_far_unconfirmed` is shape-only context and should not
increase confidence or trigger demotion.

Weighted interval scheduling (WIS) belongs to the boundary/model-selection audit
layer, not to `EvidenceScore`. WIS can explain which non-overlapping boundary
set is more coherent, but it must not add or subtract candidate evidence points
in this slice.

`tools/diagnostics/peak_candidate_score_calibration_report.py` audits whether
newer evidence labels are exposing stale or overly conservative scoring choices.
It consumes `peak_candidates.tsv` and writes JSON, TSV, and Markdown summaries
without changing production selection. The report separates:

- selected-row risks such as `selected_review_only`, `selected_nl_fail`, and
  `selected_no_ms2`;
- `plausible_nl_dropout_selected`, where the selected row lacks the expected NL
  but still has strong MS1/shape/trace support and no hard local-quality
  concern;
- `apex_evidence_shadow`, where a rejected near-apex row has additional support
  labels and should be treated as provenance/boundary context before it is
  considered a true alternative peak;
- true alternative challengers, including `high_score_rejected_challenger`,
  `strict_nl_rejected_challenger`, and `cwt_supported_rejected_challenger`.

This diagnostic is the preferred gate before changing scoring weights. A high
`apex_evidence_shadow` count means the candidate table is preserving useful
evidence, not that production selected the wrong peak. Only far alternatives
with stronger chemical and shape evidence should become scoring-rule candidates.
Likewise, `plausible_nl_dropout_selected` is not a clean strict-NL positive and
must not be silently promoted to benchmark truth. It is a separate review state
for targets such as `8-oxodG`, where RT/shape can be consistent but MS2/NL
evidence can fail because the expected fragment is not observed.
The split is owned by the shared evidence consistency classifier in
`xic_extractor.evidence_semantics`; targeted reliability diagnostics and
candidate-score calibration must both consume that classifier so the same
MS1/shape/trace/MS2/NL evidence means the same thing across reports.

`tools/diagnostics/cross_report_evidence_consistency.py` is the cross-report
bridge for this contract. It compares `targeted_peak_reliability_rows.tsv` with
selected `peak_candidates.tsv` rows and flags evidence disagreements such as a
clean targeted reliability state paired with hard candidate conflicts, or a
review-positive state whose selected candidate lacks plausible dropout labels.
The report is diagnostic-only and must include target m/z when a targeted
workbook is provided.

The tool writes `cwt_peak_candidate_far_alternatives.tsv` as the focused manual
review surface for far alternatives, including m/z, selected RT, nearest CWT RT,
RT delta, and selected/CWT NL/MS2 evidence.

Manual review outputs must include `target_mz` whenever a targeted workbook is
provided. A target label without m/z is not sufficient for EIC review because it
forces reviewers to look up the precursor again.

### Process Mode

The candidate table accumulator must not pass non-pickleable closures or open
file handles into process workers. Worker payloads should return plain
dataclasses, dictionaries, or TSV-ready rows.

## Acceptance Criteria

Candidate table v1 is ready when all of these are true:

1. Default targeted extraction output is unchanged when `emit_peak_candidates`
   is false.
2. With `emit_peak_candidates=true`, `peak_candidates.tsv` is written.
3. A synthetic two-candidate trace produces at least one selected and one
   rejected candidate row.
4. `arbitrated` mode records both `legacy_savgol` and `local_minimum` provenance
   when both sources contribute candidates.
5. Preferred-RT recovery candidates are visible when recovery is triggered.
6. Rejected rows include enough evidence to explain why they lost.
7. `uv run pytest` targeted candidate-table tests pass.
8. `uv run ruff check .` passes.
9. `uv run mypy xic_extractor` passes.
10. `centwave_cwt` audit proposals can be emitted without changing selected
    peak behavior.
11. An 8RAW smoke run with `emit_peak_candidates=true` completes and writes a
    candidate table without changing `XIC Results` selected rows compared with
    the same run with candidate output disabled.
12. The CWT audit report can summarize 8RAW `peak_candidates.tsv` and separate
    direct agreement, nearby support, far CWT alternatives, and no-CWT groups.
13. CWT manual-review rows include `target_mz` when `--targeted-workbook` is
    provided.
14. CWT far alternatives are split into `cwt_far_unconfirmed` and
    `cwt_far_chemically_plausible` using NL/MS2 evidence, and the focused
    far-alternative TSV is written.
15. Same-apex CWT provenance adds `cwt_same_apex_support` to candidate-table
    scoring, while CWT-only rows and NL-failed rows do not receive the
    same-apex bonus.
16. CWT support is bounded and cannot override a clearly closer RT prior by
    score alone.
17. Score calibration diagnostics can separate selected-row risk, near-apex
    evidence shadows, and true rejected alternative challengers without changing
    production peak selection.
18. CWT audit merge prefers the selected near-apex candidate when multiple
    candidates match the same CWT apex, and workbook comparison remains
    unchanged.
19. Score calibration diagnostics can split plausible NL-dropout selected rows
    from generic `selected_nl_fail` rows, so missing NL does not collapse every
    strong MS1/RT/shape case into the same failure bucket.

## Suggested Test Plan

Unit tests:

- `tests/test_peak_candidate_table.py`
  - candidate id is deterministic;
  - selected/rejected rows are serialized;
  - evidence labels are escaped safely for TSV;
  - disabled writer is a no-op.

- `tests/test_signal_processing.py`
  - `arbitrated` candidates preserve proposal source metadata;
  - same-apex candidates can merge provenance;
  - boundary-disagreement candidates remain separate.

- `tests/test_extractor.py`
  - targeted extraction writes candidate rows when enabled;
  - targeted extraction selected result is unchanged when candidate table is
    enabled;
  - preferred-RT recovery candidate is emitted.

- `tests/test_cwt_proposals.py`
  - CWT creates audit candidates on synthetic traces;
  - CWT agreement merges proposal provenance without changing the selected
    peak;
  - CWT-only rows remain unselected.

- `tests/test_peak_scoring.py`
  - same-apex CWT provenance adds bounded support;
  - CWT-only provenance does not add the same-apex support bonus;
  - the CWT support bonus cannot override a clearly closer RT prior by score
    alone.

Integration validation:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run pytest tests\test_peak_candidate_table.py tests\test_signal_processing.py tests\test_extractor.py -q
uv run ruff check .
uv run mypy xic_extractor
```

Real-data smoke:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run python scripts\validation_harness.py `
  --suite tissue-8raw `
  --base-dir . `
  --output-root output\targeted_candidate_table_v1 `
  --run-id candidate_table_8raw_20260516 `
  --resolver-mode arbitrated `
  --parallel-mode process `
  --parallel-workers 8 `
  --setting emit_peak_candidates=true
```

If the validation harness cannot pass `emit_peak_candidates` as a setting yet,
that support belongs in the implementation plan.

## Future Work

After v1 candidate persistence is stable:

1. Validate weighted interval scheduling boundary audit output on real targeted
   traces, then decide whether local mixture model selection is still needed.
2. Extend the same candidate-table schema to untargeted alignment backfill.
3. Use candidate table rows as training data for a future ML peak-quality
   classifier.

Boundary hypothesis enumeration for the same apex now exists as the separate
debug-only `peak_candidate_boundaries.tsv` artifact, with
`peak_candidate_boundary_summary.tsv` as the smaller manual-review entry point.
It intentionally does not change `peak_candidates.tsv` headers. Boundary review
artifacts include `target_mz` so manual EIC checks do not require a separate
target lookup. Candidate and boundary audit outputs can now populate
`area_baseline_corrected` and `area_uncertainty` from a deterministic
`linear_edge` baseline model, but these fields remain audit evidence and do not
alter selected peak behavior. Boundary non-overlap audit markers now use
weighted interval scheduling over each candidate's top boundary; this is still
review-only and does not become model selection for production outputs.

## Reviewed Verdict

### CEO Review

Verdict: **Hold scope.**

The handoff memo is directionally right, but the product risk is trying to
boil the ocean: Trace/TraceGroup/CWT/baseline/model-selection/ML all at once
would destabilize a pipeline that just regained ISTD reliability. The highest
leverage next step is observability. Candidate table v1 makes every future
algorithm discussion concrete because it shows what candidates existed and why
one won.

Do not start with CWT or ML. Start with the table that makes CWT and ML
debuggable.

### Engineering Review

Verdict: **Implementable if kept debug-only and TSV-first.**

The main engineering risks are schema creep, process-mode payloads, and
accidentally changing selected-peak behavior while adding provenance. The spec
controls those risks by keeping output disabled by default, avoiding workbook
schema changes, using TSV rows, and requiring an enabled-vs-disabled 8RAW
comparison.

The first implementation should be narrow:

1. provenance on `PeakCandidate`;
2. candidate row builder / writer;
3. targeted extraction wiring;
4. tests proving no selected-output drift.

Do not refactor the full peak detection model during this step.
