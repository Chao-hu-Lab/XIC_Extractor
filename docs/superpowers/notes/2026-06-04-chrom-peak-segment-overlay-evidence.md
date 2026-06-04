# Chrom Peak Segment Overlay Evidence

Date: 2026-06-04
Status: `production_candidate_slice` for boundary/area candidate enumeration;
presence/product selection remains `defer` after manual review identified one
expected peak change

## Decision Closed

The current boundary failure is not primarily an AsLS baseline failure. For the
representative 8RAW blockers, the baseline is usually plausible, while the
product path still lacks a first-class chromatographic peak segment layer before
model selection chooses what to quantify.

## What Changed

- Added a `ChromPeakSegment` enumerator that follows the mature
  tool shape observed in OpenMS, MZmine, XCMS, and Skyline: enumerate
  chromatographic peak segments first, then let evidence/model selection choose
  a segment, then integrate raw signal over explicit bounds.
- The enumerator uses Gaussian15 morphology as evidence only. Product area is
  still calculated from raw XIC residual over the chosen segment bounds with the
  supplied AsLS baseline.
- Added segment overlays to `tools/diagnostics/selected_envelope_plot_review.py`.
  The plot index now records segment status, count, projected segment class,
  projected RT bounds, projected AsLS area, and stop reason.
- Added a scoped product-candidate adapter:
  `chrom_peak_segment` candidates are now added only for scored
  `region_first_safe_merge` extraction. Unscored resolver behavior and direct
  `find_peak_candidates()` compatibility remain unchanged.
- Same-apex resolver candidates now upgrade to the `chrom_peak_segment`
  boundary instead of keeping two competing candidates with the same apex and
  different RT intervals.
- Evidence semantics now project `chrom_peak_segment` as
  `chrom_peak_segment_context`. It can support MS1 trace coherence with other
  evidence, but by itself remains review-only and cannot act as a single-source
  product authority.

## 8RAW Blocker Plot Review

Input:

`output/selected_full_envelope_realdata_preflight/fe4_8raw_selected_envelope_current_branch_20260604/tissue_8raw_region_first_safe_merge/selected_envelope_diagnostics.tsv`

Output:

`output/selected_full_envelope_realdata_preflight/fe4_8raw_selected_envelope_current_branch_20260604/selected_envelope_plot_review_chrom_segments/`

Selection:

- `max_high_risk=29`
- `max_accepted_increase=0`
- `max_accepted_decrease=0`

Projected segment classes among the 29 blockers:

- `isolated_peak`: 16
- `separate_peak`: 11
- `shoulder_candidate`: 2

Original blocker classes:

- `overmerge_rejected`: 16
- `split_supported`: 7
- `context_apex_conflict`: 6

## Interpretation

The selected-envelope branch can sometimes recover the right broad peak, but it
is still the wrong abstraction for product behavior. It expands from an already
selected candidate. Mature tools make the chromatographic segment an explicit
object first, then score/select/justify the segment. The new overlay shows that
many blocker rows already have visible candidate segments that a product
model-selection layer could reason over.

For `TumorBC2263_DNA / 8-oxodG`, the projected segment covers the expected
16-minute peak. The legacy resolver interval is visibly left-shifted, while the
baseline itself is not the dominant problem.

For `Breast_Cancer_Tissue_pooled_QC5 / 8-oxodG`, the context contains multiple
segments. This should not be fixed by a wider envelope rule. It needs segment
enumeration plus evidence selection.

## Product Candidate Smoke

8RAW targeted validation was run after wiring `chrom_peak_segment` into scored
candidate enumeration:

- Smoke run:
  `output/validation_harness_chrom_segment_candidate/chrom_segment_candidate_smoke_20260604/tissue_8raw_region_first_safe_merge/xic_results_process_w4.xlsx`
- Audit run with candidate and score outputs:
  `output/validation_harness_chrom_segment_candidate/chrom_segment_candidate_audit_20260604/tissue_8raw_region_first_safe_merge/xic_results_process_w4.xlsx`
- `peak_candidates.tsv` had 289 rows, including 110 `chrom_peak_segment` rows.
- 25 selected rows used `chrom_peak_segment`; selected chrom rows were split by
  confidence as 15 `HIGH`, 1 `LOW`, and 9 `VERY_LOW`.
- The candidate source appears in both `Analyte` and `ISTD` rows, so this is not
  an ISTD-only patch.

After adding same-apex boundary upgrade, a second 8RAW audit was run:

- Output workbook:
  `output/validation_harness_chrom_segment_candidate/chrom_segment_candidate_merge_audit_20260604/tissue_8raw_region_first_safe_merge/xic_results_process_w4.xlsx`
- `peak_candidates.tsv` had 210 rows, including the same 110 rows with
  `chrom_peak_segment` provenance.
- 76 selected rows used `chrom_peak_segment`: 29 `Analyte`, 47 `ISTD`.
- Selected chrom confidence split: 61 `HIGH`, 1 `MEDIUM`, 1 `LOW`, 13
  `VERY_LOW`.
- 50 selected rows changed area relative to the pre-merge audit; all changed
  rows increased area and no selected row decreased area.
- Largest selected-area increases were bounded expansions, for example
  `NormalBC2263_DNA / 8-oxo-Guo / Analyte` increased 12.56% by moving from
  13.83934-14.04556 to 13.63340-14.25208 min, and
  `TumorBC2312_DNA / d3-5-medC / ISTD` increased 7.75% by moving from
  12.06247-12.26929 to 11.86018-12.46294 min.
- A follow-up no-warning audit after guarding `peak_widths()` fallback wrote:
  `output/validation_harness_chrom_segment_candidate/chrom_segment_candidate_merge_nowarn_20260604/tissue_8raw_region_first_safe_merge/xic_results_process_w4.xlsx`.
  It preserved the same counts (`selected_chrom=76`,
  `selected_area_changed=50`, `selected_area_decreased=0`,
  max increase 12.56%) and no longer emitted zero-width / zero-prominence
  `PeakPropertyWarning` noise.
- The segment-native gate manifest is now:
  `output/validation_harness_chrom_segment_candidate/chrom_segment_candidate_merge_nowarn_20260604/chrom_peak_segment_gate/chrom_peak_segment_gate_manifest.json`.
  It reports `gate_decision=defer`, with the reason split:
  `boundary_gate_decision=promote`, `presence_gate_decision=defer`,
  `boundary_blocking_reasons=[]`, and `presence_blocking_reasons=[
  manual_presence_review_expected_peak_change_rows]`.
  The boundary slice had `selected_area_increased_count=50`,
  `selected_area_decreased_count=0`, and max selected-area increase 12.56%.
  The presence slice had 14 selected `chrom_peak_segment` review-only `Analyte`
  rows; 13 are manually accepted as review-only/not-counted, while
  `BenignfatBC1055_DNA / 8-oxodG` is now marked
  `expected_peak_change` with `select_right_chrom_segment_review_only`.
  The reviewed rows are grouped as `8-oxo-Guo=4`, `8-oxodG=3`,
  `dG-C8-MeIQx=3`, `N6-HE-dA=2`, `5-hmdC=1`, and `N6-medA=1`.
  The old selected-envelope sidecar remains advisory-only with
  `selected_envelope_gate_stale_for_segment_candidates`.

New diagnostic plots:

`output/validation_harness_chrom_segment_candidate/chrom_segment_candidate_merge_audit_20260604/selected_envelope_plot_review/`

- 30 high-risk externalized rows plotted.
- Boundary classes: 21 `overmerge_rejected`, 5 `context_apex_conflict`, 4
  `split_supported`.
- Projected segment classes: 23 `isolated_peak`, 4 `separate_peak`, 3
  `shoulder_candidate`.

Segment-native presence-review plots:

`output/validation_harness_chrom_segment_candidate/chrom_segment_candidate_merge_nowarn_20260604/chrom_peak_segment_review_plots/`

- 14 `chrom_peak_segment_review_only` rows plotted from the segment-native gate
  review TSV.
- Selected segment classes: 7 `isolated_peak`, 7 `separate_peak`.
- Legacy selected-envelope boundary classes among these rows: 7
  `overmerge_rejected`, 3 `no_change`, 2 `split_supported`, 1
  `context_apex_conflict`, and 1 `low_sn`.
- This plot set closes the observability gap for review-only rows that the old
  selected-envelope selector would not necessarily draw, especially
  accept/no-change rows with presence risk.

The selected-envelope diagnostic sidecar is now partly stale as a promotion
gate: after the segment candidate slice, `selected_envelope_diagnostics.tsv`
reported 21 `accept_candidate` and 75 `externalize` rows in the second audit.
That does not mean the segment slice failed; it means the old selected-envelope
gate is no longer the right product owner and must be replaced by a
segment-native gate.

## Verification

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_chrom_peak_segments.py tests/test_selected_envelope_plot_review.py
# 16 passed

$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor/peak_detection/chrom_peak_segments.py tools/diagnostics/selected_envelope_plot_review.py tests/test_chrom_peak_segments.py tests/test_selected_envelope_plot_review.py
# All checks passed

$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_evidence_semantics.py tests/test_peak_selection_decision.py tests/test_signal_processing_selection.py tests/test_chrom_peak_segments.py tests/test_selected_envelope_plot_review.py
# 54 passed

$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_evidence_semantics.py tests/test_peak_selection_decision.py tests/test_signal_processing_selection.py tests/test_signal_processing.py tests/test_scoring_factory.py tests/test_chrom_peak_segments.py tests/test_selected_envelope_plot_review.py
# 96 passed

$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_chrom_peak_segment_candidate_gate.py tests/test_evidence_semantics.py tests/test_peak_selection_decision.py tests/test_signal_processing_selection.py tests/test_signal_processing.py tests/test_scoring_factory.py tests/test_chrom_peak_segments.py tests/test_selected_envelope_plot_review.py
# 101 passed

$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor/peak_detection/chrom_peak_candidate_adapter.py xic_extractor/peak_detection/chrom_peak_segments.py xic_extractor/peak_detection/facade.py xic_extractor/evidence_semantics.py xic_extractor/peak_detection/selection_decision.py xic_extractor/peak_detection/model_selection.py tests/test_signal_processing_selection.py tests/test_evidence_semantics.py tests/test_peak_selection_decision.py tests/test_chrom_peak_segments.py tests/test_selected_envelope_plot_review.py tools/diagnostics/selected_envelope_plot_review.py
# All checks passed

$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor tools/diagnostics/chrom_peak_segment_candidate_gate.py tools/diagnostics/selected_envelope_plot_review.py
# Success: no issues found in 284 source files

$env:UV_CACHE_DIR='.uv-cache'; uv run pytest -q tests/test_chrom_peak_segment_candidate_gate.py
# 6 passed

$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check tools/diagnostics/chrom_peak_segment_candidate_gate.py tests/test_chrom_peak_segment_candidate_gate.py
# All checks passed

$env:UV_CACHE_DIR='.uv-cache'; uv run mypy tools/diagnostics/chrom_peak_segment_candidate_gate.py
# Success: no issues found in 1 source file
```

RAW-backed plot command:

```powershell
.venv\Scripts\python.exe tools\diagnostics\selected_envelope_plot_review.py --selected-envelope-diagnostics-tsv output\selected_full_envelope_realdata_preflight\fe4_8raw_selected_envelope_current_branch_20260604\tissue_8raw_region_first_safe_merge\selected_envelope_diagnostics.tsv --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation --dll-dir C:\Xcalibur\system\programs --config-dir config --output-dir output\selected_full_envelope_realdata_preflight\fe4_8raw_selected_envelope_current_branch_20260604\selected_envelope_plot_review_chrom_segments --max-high-risk 29 --max-accepted-increase 0 --max-accepted-decrease 0
```

RAW-backed second audit command:

```powershell
.venv\Scripts\python.exe scripts\validation_harness.py --suite tissue-8raw --run-id chrom_segment_candidate_merge_audit_20260604 --output-root output\validation_harness_chrom_segment_candidate --parallel-mode process --parallel-workers 4 --setting emit_peak_candidates=true --setting emit_score_breakdown=true

.venv\Scripts\python.exe scripts\validation_harness.py --suite tissue-8raw --run-id chrom_segment_candidate_merge_nowarn_20260604 --output-root output\validation_harness_chrom_segment_candidate --parallel-mode process --parallel-workers 4 --setting emit_peak_candidates=true --setting emit_score_breakdown=true

.venv\Scripts\python.exe tools\diagnostics\chrom_peak_segment_candidate_gate.py --peak-candidates-tsv output\validation_harness_chrom_segment_candidate\chrom_segment_candidate_merge_nowarn_20260604\tissue_8raw_region_first_safe_merge\peak_candidates.tsv --baseline-peak-candidates-tsv output\validation_harness_chrom_segment_candidate\chrom_segment_candidate_audit_20260604\tissue_8raw_region_first_safe_merge\peak_candidates.tsv --selected-envelope-diagnostics-tsv output\validation_harness_chrom_segment_candidate\chrom_segment_candidate_merge_nowarn_20260604\tissue_8raw_region_first_safe_merge\selected_envelope_diagnostics.tsv --manual-presence-review-tsv docs\superpowers\fixtures\chrom_peak_segment_presence_review_manual_oracle_v1.tsv --output-dir output\validation_harness_chrom_segment_candidate\chrom_segment_candidate_merge_nowarn_20260604\chrom_peak_segment_gate

.venv\Scripts\python.exe tools\diagnostics\selected_envelope_plot_review.py --selected-envelope-diagnostics-tsv output\validation_harness_chrom_segment_candidate\chrom_segment_candidate_merge_audit_20260604\tissue_8raw_region_first_safe_merge\selected_envelope_diagnostics.tsv --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation --dll-dir C:\Xcalibur\system\programs --config-dir config --output-dir output\validation_harness_chrom_segment_candidate\chrom_segment_candidate_merge_audit_20260604\selected_envelope_plot_review --max-high-risk 30 --max-accepted-increase 0 --max-accepted-decrease 0

.venv\Scripts\python.exe tools\diagnostics\selected_envelope_plot_review.py --selected-envelope-diagnostics-tsv output\validation_harness_chrom_segment_candidate\chrom_segment_candidate_merge_nowarn_20260604\tissue_8raw_region_first_safe_merge\selected_envelope_diagnostics.tsv --chrom-peak-segment-review-rows-tsv output\validation_harness_chrom_segment_candidate\chrom_segment_candidate_merge_nowarn_20260604\chrom_peak_segment_gate\chrom_peak_segment_review_rows.tsv --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation --dll-dir C:\Xcalibur\system\programs --config-dir config --output-dir output\validation_harness_chrom_segment_candidate\chrom_segment_candidate_merge_nowarn_20260604\chrom_peak_segment_review_plots --max-high-risk 0 --max-accepted-increase 0 --max-accepted-decrease 0
```

## Next Product Direction

`ChromPeakSegment` is now the scoped product-candidate source for scored
region-first extraction, and the first segment-native gate is in place. The
remaining work is not to promote `selected_full_envelope`; it is to use the new
gate split correctly:

1. Boundary/area promotion can proceed as a `production_candidate_slice`: the
   current 8RAW comparison shows no selected area decreases after the segment
   boundary upgrade.
2. Presence/detection promotion is now blocked by one concrete product-selection
   mismatch: `BenignfatBC1055_DNA / 8-oxodG` should choose the right
   `chrom_peak_segment` row under late-injection RT drift and plausible
   analyte/ISTD area ratio evidence.
3. The segment-native review plots should keep tracking false-pick, plausible
   DDA-missing, low-S/N, or RT/shape conflict cases. Future area-decrease rows
   should be added to the same review path.
4. Retire `selected_full_envelope` as a product boundary policy once segment
   selection closes the 8RAW blocker classes and the presence review confirms
   no new false-pick behavior.

Until the expected peak-change rule is implemented and rerun, this slice is
`production_candidate`, not `production_ready`.
