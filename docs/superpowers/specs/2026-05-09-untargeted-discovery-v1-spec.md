# Untargeted Discovery V1 Spec

**Date:** 2026-05-09
**Status:** Draft
**Implementation plan:** Not written yet. This document defines the first focused discovery workflow only.

---

## 1. Summary

Untargeted discovery v1 is a new workflow parallel to targeted extraction.

The goal is not full untargeted feature finding, batch alignment, GUI review, or automatic target-list expansion. The first useful version should solve one concrete gap:

> Given one Thermo RAW file or a small RAW directory, find strict MS2 neutral-loss seed events, group them into file-level discovery candidates, then backfill MS1 XIC evidence including apex, height, area, and trace quality.

This keeps the workflow close to what FH already does well while adding the part FH does not provide: chromatographic candidate-level MS1 validation.

## 2. Product Positioning

### 2.1 What FH already provides

FH-style Program2 output is useful because it can scan MS2 events and record neutral-loss evidence:

- one row per MS2 event,
- precursor m/z,
- product m/z,
- observed neutral loss,
- mass error,
- MS2 scan id,
- RT,
- precursor intensity at that scan.

The limitation is output granularity. One MS2 scan per row is traceable, but it is not a chromatographic candidate. Across a file or batch, it becomes difficult to know whether repeated rows are:

- multiple MS2 scans across one real peak,
- multiple nearby chromatographic peaks,
- matrix/product-ion noise,
- co-elution artifacts,
- or alignment artifacts.

### 2.2 What XIC Extractor should add

XIC Extractor should turn strict MS2 neutral-loss events into reviewable discovery candidates:

```text
strict MS2 NL seed events
-> conservative single-file grouping
-> MS1 XIC extraction around the seed group
-> MS1 peak validation and area integration
-> candidate-level CSV output
```

The candidate, not the individual MS2 scan, is the primary review unit.

## 3. Scope

### 3.1 In scope

- Single RAW file discovery.
- Small multi-RAW directory discovery that runs the single-file workflow for each RAW and writes a batch index.
- Strict MS2 neutral-loss seed detection.
- Conservative within-file seed grouping.
- MS1 XIC extraction for grouped precursor m/z.
- MS1 peak search inside seed-group RT range plus padding.
- MS1 apex RT, height, area, and trace-quality evidence.
- Candidate-level review priority.
- One default candidate CSV per RAW: `discovery_candidates.csv`.
- One batch index CSV for `--raw-dir`: `discovery_batch_index.csv`.
- Optional implementation seams for later event-level detail, plots, GUI mode, and batch consensus.

### 3.2 Out of scope

- Cross-sample alignment.
- Batch-level consensus candidates.
- Full MS1 feature-first untargeted detection.
- GUI mode switching.
- Excel workbook output.
- HTML report output by default.
- Automatic target-list updates.
- Changes to the targeted extraction workflow.
- Changes to targeted workbook schema.
- Changing default targeted resolver or scoring behavior.

## 4. Workflow Contract

### 4.1 Inputs

Minimum v1 inputs:

| Input | Meaning |
|---|---|
| `raw_path` | Single Thermo RAW file. |
| `neutral_loss_profile` | Discovery neutral-loss profile. DNA `116.0474` must be supported. |
| `nl_tolerance_ppm` | Tolerance for observed neutral-loss matching. |
| `precursor_mz_tolerance_ppm` | Tolerance used for grouping precursor m/z and extracting MS1 XIC. |
| `product_mz_tolerance_ppm` | Tolerance used for grouping product m/z when available. |
| `seed_rt_gap_min` | Maximum RT gap for conservative seed grouping. |
| `ms1_search_padding_min` | Padding around grouped seed RT range for MS1 peak search. |
| `resolver_mode` | Resolver used for MS1 XIC validation. This should be explicit in CLI/config for discovery mode. |

The first implementation may keep several values as conservative internal defaults if no public discovery config surface exists yet, but the run metadata or CLI log should make them visible enough to reproduce a result.

### 4.2 Seed detection

A discovery seed is created only when an MS2 scan has strict observed neutral-loss evidence.

Strict means:

- the scan has a precursor m/z,
- the scan has a product ion consistent with the configured neutral loss,
- observed neutral loss is calculated from scan precursor and product m/z,
- mass error is inside tolerance.

Target-window borrowing is not allowed because discovery mode has no configured target window.

### 4.3 Conservative grouping

Within one RAW file, strict seeds are grouped into a file-level candidate only when they are close by all relevant dimensions:

- same neutral-loss profile or tag,
- precursor m/z within tolerance,
- product m/z within tolerance when product m/z is present,
- observed neutral loss within tolerance,
- RT gap no larger than `seed_rt_gap_min`.

This is intentionally conservative. It may produce duplicate candidates in v1, but it should avoid merging chemically or chromatographically distinct events.

Future versions may upgrade grouping to use MS1 peak boundaries:

```text
v1: precursor/product/NL/RT proximity grouping
v2: merge seed groups that fall inside the same validated MS1 peak region
```

### 4.4 MS1 XIC backfill

Each grouped candidate must be evaluated against MS1 XIC evidence.

For a seed group:

```text
ms1_search_rt_min = rt_seed_min - ms1_search_padding_min
ms1_search_rt_max = rt_seed_max + ms1_search_padding_min
```

The workflow extracts an MS1 XIC for the representative precursor m/z and searches for a peak inside that padded RT window.

Required MS1 fields:

- `ms1_peak_found`
- `ms1_apex_rt`
- `ms1_height`
- `ms1_area`
- `ms1_peak_rt_start`
- `ms1_peak_rt_end`
- `ms1_trace_quality`
- `ms1_seed_delta_min`

MS1 area is a core value proposition. A discovery row without MS1 area is only an FH-like event summary, not an XIC Extractor discovery candidate.

## 5. Output Contract

### 5.1 Default output

The default v1 single-RAW output is exactly one candidate CSV:

```text
discovery_candidates.csv
```

One raw file should not produce several default CSV files. Event-level details and plot outputs may be added later as opt-in artifacts, not as default output.

For `--raw-dir`, v1 is batch execution, not batch alignment. The default output is:

```text
discovery_batch_index.csv
<sample_stem>/discovery_candidates.csv
```

The index is only a navigation and summary file. It must not imply cross-sample alignment or batch-level consensus.

### 5.2 Row granularity

One row is one grouped file-level discovery candidate.

It is not:

- one MS2 scan,
- one product ion record,
- one aligned batch feature,
- one final identified compound.

### 5.3 Candidate id

The candidate id should stay simple and traceable:

```text
<sample_stem>#<best_ms2_scan_id>
```

Example:

```text
TumorBC2312_DNA#6095
```

If a grouped candidate contains multiple seed scans, the best scan should be selected by a deterministic rule, for example:

1. highest product-ion intensity,
2. smallest neutral-loss mass error,
3. closest to MS1 apex RT if MS1 peak is found,
4. smallest scan number as final tie-break.

All seed scan ids should remain available in `seed_scan_ids`.

### 5.4 Required CSV columns

The CSV must be review-first. The first visible columns should answer the user's first questions without horizontal scrolling:

1. Is this worth opening in Xcalibur?
2. What scan/RT/mass should I inspect?
3. Did XIC Extractor find an MS1 peak and area?
4. Why is this row ranked this way?

The first columns are therefore fixed for v1. Feature family fields are part of
the review surface because they explain whether the row is a singleton,
representative, or member of a likely duplicate MS1 peak signal:

| Order | Column | Meaning |
|---:|---|---|
| 1 | `review_priority` | `HIGH`, `MEDIUM`, or `LOW`. Primary sort key. |
| 2 | `evidence_tier` | `A` to `E`, derived from `evidence_score` in 20-point bands. |
| 3 | `evidence_score` | 0-100 discovery evidence score for sorting within priority. |
| 4 | `ms2_support` | `strong`, `moderate`, or `weak` summary of strict MS2 seed support. |
| 5 | `ms1_support` | `strong`, `moderate`, `weak`, or `missing` summary of MS1 peak support. |
| 6 | `rt_alignment` | `aligned`, `near`, `shifted`, or `missing` summary of MS1 apex vs seed RT. |
| 7 | `family_context` | `singleton`, `representative`, or `member` summary of duplicate-signal context. |
| 8 | `candidate_id` | `<sample_stem>#<best_ms2_scan_id>`. |
| 9 | `feature_family_id` | Strict same-MS1-peak family id. |
| 10 | `feature_family_size` | Count of candidates sharing the strict same-MS1-peak family. |
| 11 | `feature_superfamily_id` | Broader close-overlap MS1 peak family id. |
| 12 | `feature_superfamily_size` | Count of candidates in the broader close-overlap family. |
| 13 | `feature_superfamily_role` | `representative` or `member`. |
| 14 | `feature_superfamily_confidence` | `LOW` for singleton; `MEDIUM` for v1 peak-overlap grouping. `HIGH` is reserved for future stronger evidence. |
| 15 | `feature_superfamily_evidence` | Short evidence token such as `single_candidate` or `peak_boundary_overlap;apex_close`. |
| 16 | `precursor_mz` | Representative precursor m/z. |
| 17 | `product_mz` | Representative product m/z. |
| 18 | `observed_neutral_loss_da` | Representative observed neutral loss. |
| 19 | `best_seed_rt` | RT of representative seed scan. |
| 20 | `seed_event_count` | Number of strict NL seed events in the group. |
| 21 | `ms1_peak_found` | `TRUE` / `FALSE`. |
| 22 | `ms1_apex_rt` | MS1 candidate apex RT. |
| 23 | `ms1_area` | MS1 integrated area. |
| 24 | `ms2_product_max_intensity` | Maximum product-ion intensity among seed events. |
| 25 | `reason` | Short human-readable explanation. |

After those review columns, include provenance and boundary columns:

| Column | Meaning |
|---|---|
| `raw_file` | Source RAW filename. |
| `sample_stem` | RAW stem used in candidate id. |
| `best_ms2_scan_id` | Representative MS2 scan id. |
| `seed_scan_ids` | Semicolon-separated MS2 scan ids in the group. |
| `neutral_loss_tag` | Discovery NL profile name or tag. |
| `configured_neutral_loss_da` | Expected neutral-loss mass. |
| `neutral_loss_mass_error_ppm` | Representative or best mass error. |
| `rt_seed_min` | Minimum seed RT in group. |
| `rt_seed_max` | Maximum seed RT in group. |
| `ms1_search_rt_min` | Padded MS1 search window start. |
| `ms1_search_rt_max` | Padded MS1 search window end. |
| `ms1_seed_delta_min` | `ms1_apex_rt - best_seed_rt` when available. |
| `ms1_peak_rt_start` | MS1 peak boundary start. |
| `ms1_peak_rt_end` | MS1 peak boundary end. |
| `ms1_height` | MS1 peak height. |
| `ms1_trace_quality` | Simple trace-quality label or numeric summary. |

The implementation may add more provenance columns, but it must not push these
review columns later in the file.

### 5.5 CSV readability rules

The CSV will often be opened directly in Excel. It should be readable without a companion HTML report.

Rules:

- Sort rows by review priority and evidence strength by default.
- Keep `reason` short enough to scan in one cell.
- Use stable numeric formatting for RT, m/z, and mass error so equivalent rows do not churn across runs.
- Use numeric values, not display-only strings, for `ms1_area` and intensity fields so downstream tools can sort and filter.
- If no strict NL seeds are found, still write a CSV with headers and include a short run-level log message. Do not fail just because there are no candidates.
- If strict NL seeds exist but no MS1 peak is found for any candidate, write the rows as `LOW` priority rather than suppressing them.

## 6. Review Priority

Discovery v1 should use simple priority rules, not the existing targeted weighted scoring model.

Reasoning:

- targeted confidence answers "is this configured target detected?",
- discovery priority answers "is this unknown candidate worth reviewing?",
- these are related but not identical truth criteria.

### 6.1 Priority rules

Initial v1 priority:

| Priority | Criteria |
|---|---|
| `HIGH` | `seed_event_count >= 2`, MS1 peak found, and MS1 apex is inside the padded seed-group window. |
| `MEDIUM` | At least one strict NL seed and MS1 peak found, but seed count is one or MS1/MS2 RT alignment is weaker. |
| `LOW` | Strict NL seed exists, but MS1 peak is weak, missing, or trace quality is poor. |

No candidate without a strict NL seed should appear in v1.

### 6.2 Evidence score and tier

`review_priority` remains the coarse review queue. `evidence_score` provides
within-priority ranking without changing the meaning of `HIGH` / `MEDIUM` /
`LOW`. Evidence component columns expose why a score is high or low, so the CSV
does not rely on a black-box number.

Initial v1 evidence score uses existing fields only:

- MS1 peak presence,
- strict MS2 seed count,
- MS1 apex distance from the seed RT,
- MS2 product max intensity,
- MS1 area,
- MS1 trace quality,
- superfamily representative/member role.

The score is capped to 0-100. Tier bands are:

| Tier | Score range |
|---|---:|
| `A` | 80-100 |
| `B` | 60-79 |
| `C` | 40-59 |
| `D` | 20-39 |
| `E` | 0-19 |

Component labels are intentionally coarse:

| Component | Values |
|---|---|
| `ms2_support` | `strong`, `moderate`, `weak` |
| `ms1_support` | `strong`, `moderate`, `weak`, `missing` |
| `rt_alignment` | `aligned`, `near`, `shifted`, `missing` |
| `family_context` | `singleton`, `representative`, `member` |

### 6.3 Reason text

Reason text should be short. It should not reproduce every numeric field.

Examples:

```text
strong MS2 NL seed group; MS1 peak found near seed RT
single MS2 NL seed; MS1 peak found
strict NL seed found; weak MS1 trace
strict NL seed found; no MS1 peak in seed window
```

## 7. UX Principle

CSV is the v1 contract, not the final discovery UX.

The default one-file output is chosen to avoid the poor experience of producing several artifacts per raw file. That only works if the CSV itself behaves like a review surface, not a raw dump.

Design completeness after review: **8/10**.

A 10/10 version would include an interactive review UI or at least optional top-N plots, but that belongs in a later phase. For v1, the design target is:

- one file per raw by default,
- first 12 columns are enough for first-pass triage,
- provenance remains available without dominating the table,
- empty and low-evidence cases are explicit rather than surprising,
- no batch or GUI commitments leak into the first implementation.

The table must therefore be sorted for review:

1. `review_priority`,
2. `seed_event_count`,
3. `ms2_product_max_intensity`,
4. `ms1_area`,
5. `best_seed_rt`.

Future UX improvements should be opt-in and layered:

- optional event-detail CSV,
- optional top-N extracted plots,
- optional batch summary,
- later GUI discovery mode.

## 8. Architecture Direction

Discovery mode should not be bolted onto targeted extraction as another branch of target handling.

Recommended boundaries:

| Module area | Responsibility |
|---|---|
| discovery seed scanning | Read MS2 scans and create strict NL seed records. |
| discovery grouping | Convert seed records into conservative file-level groups. |
| discovery MS1 backfill | Extract MS1 XIC and validate grouped candidates. |
| discovery scoring/priority | Assign review priority and reason. |
| discovery CSV output | Render candidate-level CSV only. |
| CLI entry point | Run discovery mode for one raw file. |

Targeted modules may be reused for low-level utilities such as neutral-loss validation, XIC extraction, resolver calls, and area integration, but discovery workflow state should stay separate from targeted result models.

## 9. Validation Strategy

### 9.1 Unit-level validation

Use synthetic or small fake scan fixtures to validate:

- strict neutral-loss seed creation,
- no seed when observed neutral loss is outside tolerance,
- deterministic grouping by precursor/product/NL/RT proximity,
- separate groups when RT gap is too large,
- MS1 search window uses seed range plus padding,
- candidate id uses deterministic best scan selection,
- CSV has one row per grouped candidate.

### 9.2 Real-data smoke validation

Use one known FH example raw first, such as `TumorBC2312_DNA`, and compare qualitatively against FH Program2 output:

- strict NL seed count should be plausible relative to FH,
- repeated event rows should collapse into fewer candidate rows,
- candidates should contain MS1 apex and area,
- candidate ids should map back to Xcalibur scan ids,
- low-priority rows should explain weak or missing MS1 support.

### 9.3 Stop conditions

Stop and revisit design if:

- v1 candidate CSV becomes as noisy as FH event-level output,
- most candidates have no MS1 peak but are still ranked high,
- grouping merges clearly distinct RT peaks,
- candidate ids cannot be traced back to Xcalibur scan ids,
- implementation requires changing targeted extraction behavior.

## 10. Future Phases

### 10.1 Discovery v1.1

- Optional event-detail CSV.
- Optional top-N candidate plots.
- Better review sorting.
- Configurable neutral-loss profiles.

### 10.2 Discovery v2

- Peak-boundary-aware grouping.
- Batch-level consensus candidates.
- Missingness and recurrence summaries.
- Candidate overlap against known targeted list.

### 10.3 Discovery v3

- GUI discovery mode.
- Interactive review workflow.
- Candidate promotion into `targets.csv`.
- Visual MS1/MS2 evidence panels.

## 11. Open Questions

These should be answered during implementation planning, not by expanding v1 scope:

1. Should the first CLI accept one raw file only, or a folder but still process files independently?
2. Should neutral-loss profiles be internal constants first, or loaded from a small CSV?
3. Which existing resolver should discovery mode default to for MS1 backfill?
4. What are the initial values for `seed_rt_gap_min` and `ms1_search_padding_min`?
5. Should candidate CSV include both raw and smoothed MS1 apex RT, or only the resolver-selected apex RT?

## Implementation Notes

- The first implementation exposes the experimental CLI `xic-discovery-cli`.
- Default FH comparison smoke command:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run xic-discovery-cli --raw "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation\TumorBC2312_DNA.raw" --dll-dir "C:\Xcalibur\system\programs" --output-dir "output\discovery\TumorBC2312_DNA" --neutral-loss-tag DNA_dR --neutral-loss-da 116.0474 --resolver-mode local_minimum
```

- Small multi-RAW smoke command:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run xic-discovery-cli --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" --dll-dir "C:\Xcalibur\system\programs" --output-dir "output\discovery\tissue8" --neutral-loss-tag DNA_dR --neutral-loss-da 116.0474 --resolver-mode local_minimum
```

- If the exact RAW file is unavailable, use the known FH Program2 raw counterpart and record the path in the PR summary.
- Single-RAW or per-sample candidate CSV smoke checks:
  - `discovery_candidates.csv` exists.
  - Header starts with the fixed review columns.
  - Rows are candidate-level, not per MS2 scan.
  - Candidate IDs map to Xcalibur scan IDs.
  - At least one candidate has `ms1_area` when signal is valid.
- Multi-RAW batch index smoke checks:
  - `discovery_batch_index.csv` exists.
  - One index row exists per input RAW file.
  - Each index row points to a per-sample `discovery_candidates.csv`.
  - No top-level combined `discovery_candidates.csv` is written for `--raw-dir`.
  - Index rows summarize candidate and priority counts only; they do not imply cross-sample alignment.
- Targeted workbook tests remain unchanged.

## 12. Acceptance Criteria For This Spec

This spec is ready for implementation planning when:

- single-raw strict MS2-first discovery is accepted as v1,
- one default candidate-level CSV is accepted as the output contract,
- event-level detail and plots are accepted as opt-in future artifacts,
- MS1 XIC apex/height/area are accepted as core candidate fields,
- batch alignment and GUI mode are accepted as future phases,
- targeted extraction behavior remains unchanged.
