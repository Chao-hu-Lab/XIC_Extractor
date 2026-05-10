# Alignment Legacy Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a validation harness that compares XIC alignment outputs against legacy FH, metabCombiner, and combine-fix artifacts without changing discovery, clustering, backfill, or output schemas.

**Architecture:** Plan 4 consumes Plan 3 outputs (`alignment_review.tsv`, `alignment_matrix.tsv`) plus optional legacy artifacts. It normalizes sample names, matches features by m/z and RT, compares presence/area patterns on shared samples, and writes two validation TSVs. This is a parallel validation and replacement-decision aid, not a new alignment algorithm.

**Tech Stack:** Python, csv, pathlib, argparse, openpyxl for xlsx input, pytest, existing alignment TSV contracts, no RAW reader dependency.

---

## Summary

Plan 4 answers one question:

```text
Is the new XIC alignment output plausible enough to compare against, and eventually replace, the legacy FH -> mzmine/metabCombiner -> combine-fix workflow?
```

It does not require bit-for-bit agreement. The old workflow and XIC workflow use different evidence chains:

- FH/program2 is MS2-event driven.
- metabCombiner merges FH-style and MZmine-derived feature matrices.
- combine-fix is a curated integration surface.
- XIC alignment uses per-sample discovery candidates, NL-compatible clustering, and MS1 backfill from RAW.

Therefore Plan 4 validates feature identity proximity, sample-level presence agreement, and obvious matrix failures. It reports area agreement as advisory only.

## Scope

In scope:

- Load Plan 3 XIC alignment outputs.
- Load legacy FH alignment TSV.
- Load metabCombiner FH-format TSV, including both the FH block and MZmine peak-area block when present.
- Load combine-fix xlsx first worksheet.
- Normalize sample names across file families.
- Match XIC clusters to legacy rows with deterministic one-to-one m/z + RT matching.
- Compare presence/absence and positive area values on shared samples.
- Write default validation outputs:
  - `alignment_validation_summary.tsv`
  - `alignment_legacy_matches.tsv`
- Add `xic-align-validate-cli`.
- Synthetic tests and real-file smoke commands.

Out of scope:

- Reading RAW files.
- Running discovery or alignment automatically.
- Changing Plan 1 clustering rules.
- Changing Plan 2 backfill rules.
- Changing Plan 3 alignment output schema.
- Replacing legacy workflow automatically.
- Tuning match thresholds based on one validation run.
- HTML, GUI, Excel validation reports.

## Validation Philosophy

This harness is a decision aid, not a pass/fail truth oracle.

Hard blockers:

- XIC alignment files cannot be parsed.
- Required legacy files cannot be parsed when provided.
- No shared sample names exist within the chosen validation scope between XIC and a provided legacy source.
- XIC alignment matrix has duplicate `cluster_id` rows.
- A legacy matrix has duplicate feature IDs after loading.
- XIC alignment has zero clusters.

Warnings:

- A provided legacy source has zero matched features.
- More than 10% of samples inside the chosen validation scope fail to match on both XIC and legacy sides.
- Median matched `distance_score` is greater than `0.5`.
- 90th percentile matched `distance_score` is greater than `0.8`.

Advisory only:

- Area scale differences.
- Log-area correlation.
- XIC-only features.
- Legacy-only features.

Replacement strategy:

1. Use Plan 4 reports to find parser, sample-name, and gross matching failures.
2. Use 8-raw validation to inspect obvious mismatches quickly.
3. Use 85-raw validation only after 8-raw parser and matching outputs are stable.
4. Treat "no blockers, explainable warnings" as ready for manual scientific review.
5. Treat "manual review agrees with representative matches and misses" as the point where a later PR may promote XIC alignment as the preferred pipeline.

## Input Contracts

### XIC Alignment Inputs

Required:

- `alignment_review.tsv`
- `alignment_matrix.tsv`

`alignment_review.tsv` provides feature metadata:

```text
cluster_id
neutral_loss_tag
cluster_center_mz
cluster_center_rt
cluster_product_mz
cluster_observed_neutral_loss_da
has_anchor
member_count
detected_count
rescued_count
absent_count
unchecked_count
present_rate
rescued_rate
representative_samples
representative_candidate_ids
warning
reason
```

`alignment_matrix.tsv` provides sample columns:

```text
cluster_id
neutral_loss_tag
cluster_center_mz
cluster_center_rt
<sample_1>
<sample_2>
```

Rules:

- Join review and matrix rows by `cluster_id`.
- `cluster_center_mz` and `cluster_center_rt` must agree between review and matrix when both are present.
- Blank, zero, negative, and non-finite areas are treated as missing for validation.
- Positive finite areas are treated as present.

### Legacy FH Alignment TSV

Example source:

```text
C:\Users\user\Desktop\MS Data process package\MS-data aligner\output\program2_DNA\program2_DNA_v4_alignment_standard.tsv
```

Expected columns:

```text
alignment_id
Mz
RT
program2_DNA_program1_TumorBC2312_DNA
```

Rules:

- Feature ID = `alignment_id`.
- m/z column = `Mz`.
- RT column = `RT`, in minutes.
- Sample columns are all columns after `RT`.
- Strip `program2_DNA_program1_` from sample column names.
- Blank, zero, negative, and non-finite areas are missing.

### metabCombiner FH-Format TSV

Example source:

```text
C:\Users\user\Desktop\NTU cancer\Processed Data\DNA\Mzmine\new_test\metabcombiner_fh_format_20260429_130630.tsv
```

This file can contain two matrix blocks:

1. FH-style block:
   - Feature center from `Mz` and `RT`.
   - Sample columns between `RT` and `MZmine ID`.
   - Source label: `metabcombiner_fh_block`.
2. MZmine block:
   - Feature center from `MZmine m/z` and `MZmine RT (min)`.
   - Sample columns ending with `.mzML Peak area`.
   - Source label: `metabcombiner_mzmine_block`.

Rules:

- If `MZmine ID`, `MZmine m/z`, and `MZmine RT (min)` are missing, load only the FH-style block.
- MZmine sample name = column name with `.mzML Peak area` removed.
- Blank, zero, negative, and non-finite areas are missing.
- Feature IDs:
  - FH-style block: `metabcombiner_fh:{row_number:06d}`.
  - MZmine block: `metabcombiner_mzmine:{MZmine ID}` when present, otherwise `metabcombiner_mzmine:{row_number:06d}`.

### combine-fix XLSX

Example source:

```text
C:\Users\user\Desktop\NTU cancer\Processed Data\DNA\Mzmine\new_test\metabcombiner_fh_format_20260422_213805_combined_fix_20260422_223242.xlsx
```

Rules:

- Read the first worksheet by default.
- Required columns: `Mz`, `RT`.
- Sample columns are all columns after `RT` until a recognized metadata column.
- Recognized metadata columns start with `MZmine` or end with `.mzML Peak area`.
- Source label: `combine_fix`.
- Feature ID = `combine_fix:{row_number:06d}`.
- Blank, zero, negative, and non-finite areas are missing.

## Sample Name Normalization

Use one normalization function for all sources:

```python
def normalize_sample_name(value: str) -> str:
    name = Path(value).name
    for suffix in (".raw", ".mzML", ".RAW", ".MZML"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    if name.endswith(".mzML Peak area"):
        name = name[: -len(".mzML Peak area")]
    for prefix in ("program2_DNA_program1_", "program2_RNA_program1_"):
        if name.startswith(prefix):
            name = name[len(prefix):]
    name = name.replace("Breast_Cancer_Tissue_pooled_QC_", "Breast_Cancer_Tissue_pooled_QC")
    return name.strip()
```

Do not fuzzy-match arbitrary sample names. If a sample remains unmatched after these deterministic rules, report it in summary metrics.

## Sample Scope Contract

Legacy files can contain more samples than the XIC validation run. This is normal for 8-raw validation against a full 85-sample legacy matrix and must not be reported as a sample-name failure.

Validation therefore has an explicit `sample_scope`:

```text
sample_scope = "xic" | "legacy" | "intersection"
default = "xic"
```

Definitions:

- `xic_samples`: normalized `alignment_matrix.tsv` sample columns.
- `legacy_samples`: normalized legacy matrix sample columns.
- `scope_samples`:
  - `xic`: all `xic_samples`, preserving XIC sample order.
  - `legacy`: all `legacy_samples`, preserving legacy sample order.
  - `intersection`: samples present in both, preserving XIC sample order.
- `shared_samples`: `scope_samples` present in both XIC and legacy.
- `failed_sample_match_count`: `scope_samples` not present in both XIC and legacy.
- `failed_sample_match_rate = failed_sample_match_count / len(scope_samples)`.
- `out_of_scope_legacy_sample_count`: legacy samples not included in `scope_samples`.

Rules:

- Default `sample_scope="xic"` is used for 8-raw and 85-raw validation. It asks: "for the samples XIC just processed, does the legacy matrix contain comparable columns?"
- Legacy samples outside the XIC subset are `out_of_scope_legacy_sample_count` and `INFO`, not `WARN`.
- If `scope_samples` is empty, `failed_sample_match_rate` is blank and the source is `BLOCK`.
- If `shared_samples` is empty, the source is `BLOCK`.
- If `failed_sample_match_rate > 0.10`, the source is `WARN`.
- Per-feature presence metrics are computed only on `shared_samples`.

## Feature Matching Contract

For each legacy source, match features to XIC clusters independently.

Default thresholds:

```text
match_ppm = 20.0
match_rt_sec = 60.0
match_distance_warn_median = 0.5
match_distance_warn_p90 = 0.8
```

Candidate pair is eligible when:

```text
abs(mz_delta_ppm) <= match_ppm
abs(rt_delta_sec) <= match_rt_sec
```

Distance score:

```text
distance_score = max(abs(mz_delta_ppm) / match_ppm, abs(rt_delta_sec) / match_rt_sec)
```

Matching rule:

1. Build all eligible XIC cluster × legacy feature pairs.
2. Sort by `distance_score`, then `abs(rt_delta_sec)`, then `abs(mz_delta_ppm)`, then `cluster_id`, then `legacy_feature_id`.
3. Greedily accept a pair only when neither side has already been matched.
4. Leave unmatched XIC clusters and unmatched legacy features as unmatched.

This is one-to-one validation matching. It does not change alignment clusters and does not introduce chain merging.

Distance warnings use `distance_score`, not raw tolerance exceedance. Matched pairs already passed the hard ppm/RT thresholds, so warnings must detect loose-but-eligible matches:

- `median_distance_score > match_distance_warn_median` is `WARN`.
- `p90_distance_score > match_distance_warn_p90` is `WARN`.

## Metric Contract

For each matched feature pair, compute on `shared_samples` from the Sample Scope Contract:

```text
shared_sample_count
xic_present_count
legacy_present_count
both_present_count
xic_only_count
legacy_only_count
both_missing_count
present_jaccard
log_area_pearson
```

Definitions:

- Present = positive finite area.
- Missing = blank, zero, negative, non-finite, or absent sample value.
- `present_jaccard = both_present_count / (both_present_count + xic_only_count + legacy_only_count)`.
- If the denominator is zero, `present_jaccard` is blank.
- `log_area_pearson` uses `log10(area)` for samples where both XIC and legacy are present.
- If fewer than 3 paired positive areas exist, `log_area_pearson` is blank.
- Do not compare raw area scale as a pass/fail metric.
- Sparse overlap rule: when `both_present_count + xic_only_count + legacy_only_count <= 2`, a match with `both_present_count >= 1` is considered sparse-overlap `OK`. Otherwise the normal `present_jaccard >= 0.5` rule decides `OK`.

## Output Contract

### Default File 1: `alignment_validation_summary.tsv`

One row per metric per source.

Columns:

```text
source
metric
value
threshold
status
note
```

Statuses:

- `OK`: metric is structurally healthy.
- `WARN`: report should be reviewed but output is still usable.
- `BLOCK`: validation is not trustworthy until fixed.
- `INFO`: informational metric with no gate.

Required metrics per source:

```text
xic_feature_count
legacy_feature_count
matched_feature_count
unmatched_xic_count
unmatched_legacy_count
xic_sample_count
legacy_sample_count
sample_scope
scope_sample_count
shared_sample_count
failed_sample_match_count
failed_sample_match_rate
out_of_scope_legacy_sample_count
median_abs_mz_delta_ppm
median_abs_rt_delta_sec
median_distance_score
p90_distance_score
median_present_jaccard
median_log_area_pearson
```

Required global metrics:

```text
provided_source_count
blocker_count
warning_count
replacement_readiness
```

`replacement_readiness` values:

- `blocked`: one or more `BLOCK` rows exist.
- `review`: zero blockers but one or more `WARN` rows exist.
- `manual_review_ready`: zero blockers and zero warnings.

### Default File 2: `alignment_legacy_matches.tsv`

One row per matched XIC cluster × legacy feature pair.

Columns:

```text
source
xic_cluster_id
legacy_feature_id
xic_mz
legacy_mz
mz_delta_ppm
xic_rt
legacy_rt
rt_delta_sec
distance_score
shared_sample_count
xic_present_count
legacy_present_count
both_present_count
xic_only_count
legacy_only_count
both_missing_count
present_jaccard
log_area_pearson
status
note
```

Match row statuses:

- `OK`: `present_jaccard >= 0.5`.
- `OK`: sparse-overlap exception when `both_present_count + xic_only_count + legacy_only_count <= 2` and `both_present_count >= 1`.
- `REVIEW`: no shared samples, blank `present_jaccard` without sparse overlap, `present_jaccard < 0.5`, or large area-pattern disagreement.

Do not write unmatched feature rows to this default file. Unmatched counts belong in `alignment_validation_summary.tsv`.

## CLI Contract

Command:

```powershell
xic-align-validate-cli `
  --alignment-dir output\alignment\tissue85 `
  --legacy-fh-tsv "C:\Users\user\Desktop\MS Data process package\MS-data aligner\output\program2_DNA\program2_DNA_v4_alignment_standard.tsv" `
  --legacy-metabcombiner-tsv "C:\Users\user\Desktop\NTU cancer\Processed Data\DNA\Mzmine\new_test\metabcombiner_fh_format_20260429_130630.tsv" `
  --legacy-combine-fix-xlsx "C:\Users\user\Desktop\NTU cancer\Processed Data\DNA\Mzmine\new_test\metabcombiner_fh_format_20260422_213805_combined_fix_20260422_223242.xlsx" `
  --sample-scope xic `
  --output-dir output\alignment_validation\tissue85
```

Required arguments:

- `--alignment-dir`, or both `--alignment-review` and `--alignment-matrix`.
- At least one legacy artifact argument:
  - `--legacy-fh-tsv`
  - `--legacy-metabcombiner-tsv`
  - `--legacy-combine-fix-xlsx`

Optional arguments:

- `--output-dir`, default `output\alignment_validation`.
- `--match-ppm`, default `20.0`.
- `--match-rt-sec`, default `60.0`.
- `--sample-scope`, choices `xic`, `legacy`, `intersection`, default `xic`.
- `--match-distance-warn-median`, default `0.5`.
- `--match-distance-warn-p90`, default `0.8`.

Exit codes:

- `0`: validation reports written, even if summary contains `WARN` or `BLOCK`.
- `2`: user/input error, malformed files, missing required inputs, or no legacy source provided.

The command never reads RAW files and never runs discovery or alignment.

## File Structure

Create:

- `xic_extractor/alignment/legacy_io.py`
  - models for loaded XIC and legacy matrices.
  - load XIC alignment review/matrix TSV.
  - load FH alignment TSV.
  - load metabCombiner TSV.
  - load combine-fix xlsx.
  - normalize sample names.
- `xic_extractor/alignment/validation_compare.py`
  - one-to-one feature matching.
  - per-match sample presence metrics.
  - summary metric aggregation.
- `xic_extractor/alignment/validation_writer.py`
  - write `alignment_validation_summary.tsv`.
  - write `alignment_legacy_matches.tsv`.
  - own TSV formatting and Excel formula escaping.
- `xic_extractor/alignment/validation_pipeline.py`
  - orchestrate input loading, comparison, and output writing.
  - accept injected loaders/writers for tests.
- `scripts/run_alignment_validation.py`
  - CLI wrapper.
- `tests/test_alignment_legacy_io.py`
- `tests/test_alignment_validation_compare.py`
- `tests/test_alignment_validation_writer.py`
- `tests/test_alignment_validation_pipeline.py`
- `tests/test_run_alignment_validation.py`

Modify:

- `pyproject.toml`
  - add `xic-align-validate-cli = "scripts.run_alignment_validation:main"`.
- `docs/superpowers/plans/2026-05-10-untargeted-cross-sample-alignment.md`
  - link Plan 4 and remove the pending wording.

## Tasks

### Task 0: Dependency Check

**Files:**
- Read: `docs/superpowers/plans/2026-05-10-alignment-clustering-plan.md`
- Read: `docs/superpowers/plans/2026-05-10-alignment-ms1-backfill-plan.md`
- Read: `docs/superpowers/plans/2026-05-11-alignment-output-cli-plan.md`

- [ ] Confirm Plan 3 output contract exists.

Run:

```powershell
Select-String -SimpleMatch "alignment_review.tsv" docs\superpowers\plans\2026-05-11-alignment-output-cli-plan.md
Select-String -SimpleMatch "alignment_matrix.tsv" docs\superpowers\plans\2026-05-11-alignment-output-cli-plan.md
```

Expected: both commands find output contract lines.

- [ ] Confirm no implementation accidentally imports RAW readers in validation modules.

Run before implementation:

```powershell
Test-Path xic_extractor\alignment\validation_pipeline.py
```

Expected: `False`.

### Task 1: Legacy And XIC Input Loaders

**Files:**
- Create: `xic_extractor/alignment/legacy_io.py`
- Test: `tests/test_alignment_legacy_io.py`

- [ ] Write red tests:
  - `normalize_sample_name()` strips `program2_DNA_program1_`, `.raw`, `.mzML`, and `.mzML Peak area`.
  - `normalize_sample_name()` maps `Breast_Cancer_Tissue_pooled_QC_1` to `Breast_Cancer_Tissue_pooled_QC1`.
  - XIC loader joins review and matrix by `cluster_id`.
  - XIC loader rejects duplicate matrix `cluster_id`.
  - FH loader reads `alignment_id`, `Mz`, `RT`, and program2 sample columns.
  - metabCombiner loader returns `metabcombiner_fh_block` and `metabcombiner_mzmine_block` when both blocks exist.
  - combine-fix loader reads the first worksheet and treats zeros/blanks as missing.
  - all loaders treat positive finite area as present and zero/blank/non-finite as missing.

Example test fixtures:

```python
FH_TEXT = (
    "alignment_id\tMz\tRT\tprogram2_DNA_program1_TumorBC2312_DNA\n"
    "ALN00001\t242.1144\t12.3515\t661257\n"
    "ALN00002\t242.1337\t19.5400\t0\n"
)

XIC_REVIEW_TEXT = (
    "cluster_id\tneutral_loss_tag\tcluster_center_mz\tcluster_center_rt\t"
    "cluster_product_mz\tcluster_observed_neutral_loss_da\thas_anchor\t"
    "member_count\tdetected_count\trescued_count\tabsent_count\tunchecked_count\t"
    "present_rate\trescued_rate\trepresentative_samples\trepresentative_candidate_ids\t"
    "warning\treason\n"
    "ALN000001\tDNA_dR\t242.1144\t12.35\t126.067\t116.047\tTrue\t1\t1\t0\t0\t0\t1\t0\tTumorBC2312_DNA\tC1\t\tanchor cluster\n"
)

XIC_MATRIX_TEXT = (
    "cluster_id\tneutral_loss_tag\tcluster_center_mz\tcluster_center_rt\tTumorBC2312_DNA\n"
    "ALN000001\tDNA_dR\t242.1144\t12.35\t1000\n"
)
```

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_legacy_io.py -v
```

Expected red: missing `xic_extractor.alignment.legacy_io`.

- [ ] Implement:
  - `LoadedFeature(feature_id, mz, rt_min, sample_areas, metadata)`.
  - `LoadedMatrix(source, features, sample_order)`.
  - `LoadedXicAlignment(review_features, matrix)`.
  - `normalize_sample_name(value: str) -> str`.
  - `load_xic_alignment(review_tsv: Path, matrix_tsv: Path) -> LoadedMatrix`.
  - `load_fh_alignment_tsv(path: Path) -> LoadedMatrix`.
  - `load_metabcombiner_tsv(path: Path) -> tuple[LoadedMatrix, ...]`.
  - `load_combine_fix_xlsx(path: Path, sheet_name: str | None = None) -> LoadedMatrix`.

- [ ] Re-run and commit:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_legacy_io.py -v
git add xic_extractor\alignment\legacy_io.py tests\test_alignment_legacy_io.py
git commit -m "feat(alignment): load legacy validation matrices"
```

### Task 2: Feature Matching And Metrics

**Files:**
- Create: `xic_extractor/alignment/validation_compare.py`
- Test: `tests/test_alignment_validation_compare.py`

- [ ] Write red tests:
  - eligible pairs require both ppm and RT thresholds.
  - one-to-one matching keeps the closest pair and leaves second choices unmatched.
  - tie-breaking is deterministic by `cluster_id` then `legacy_feature_id`.
  - presence metrics count XIC-only, legacy-only, both-present, and both-missing cells.
  - blank/zero legacy values are missing, not low area.
  - `present_jaccard` is blank when both sides have no present values.
  - `log_area_pearson` is blank when fewer than 3 paired positive values exist.
  - summary marks no shared samples inside the selected sample scope as `BLOCK`.
  - `sample_scope="xic"` treats legacy-only columns as `out_of_scope_legacy_sample_count`, not sample-name failure.
  - `sample_scope="legacy"` counts legacy samples missing from XIC as `failed_sample_match_count`.
  - summary marks `failed_sample_match_rate > 0.10` as `WARN`.
  - summary marks `median_distance_score > 0.5` as `WARN`.
  - summary marks `p90_distance_score > 0.8` as `WARN`.
  - match status uses sparse-overlap `OK` only when union-present count is `<= 2` and `both_present_count >= 1`.

Example matching fixture:

```python
xic = LoadedMatrix(
    source="xic",
    sample_order=("S1", "S2", "S3"),
    features=(
        LoadedFeature("ALN000001", 242.1144, 12.35, {"S1": 100.0, "S2": None, "S3": 300.0}, {}),
        LoadedFeature("ALN000002", 300.0000, 20.00, {"S1": None, "S2": 50.0, "S3": None}, {}),
    ),
)
legacy = LoadedMatrix(
    source="fh_alignment",
    sample_order=("S1", "S2", "S3"),
    features=(
        LoadedFeature("LEGACY001", 242.1145, 12.36, {"S1": 10.0, "S2": 20.0, "S3": None}, {}),
    ),
)
```

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_validation_compare.py -v
```

Expected red: missing `xic_extractor.alignment.validation_compare`.

- [ ] Implement:
  - `FeatureMatch` dataclass with the columns required by `alignment_legacy_matches.tsv`.
  - `SummaryMetric` dataclass with `source`, `metric`, `value`, `threshold`, `status`, `note`.
  - `match_legacy_source(xic, legacy, match_ppm=20.0, match_rt_sec=60.0) -> tuple[FeatureMatch, ...]`.
  - `summarize_legacy_source(xic, legacy, matches, sample_scope="xic", match_ppm=20.0, match_rt_sec=60.0, match_distance_warn_median=0.5, match_distance_warn_p90=0.8) -> tuple[SummaryMetric, ...]`.
  - `summarize_global(metrics) -> tuple[SummaryMetric, ...]`.

- [ ] Re-run and commit:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_validation_compare.py -v
git add xic_extractor\alignment\validation_compare.py tests\test_alignment_validation_compare.py
git commit -m "feat(alignment): compare legacy validation matrices"
```

### Task 3: Validation TSV Writers

**Files:**
- Create: `xic_extractor/alignment/validation_writer.py`
- Test: `tests/test_alignment_validation_writer.py`

- [ ] Write red tests:
  - summary TSV header exactly matches this plan.
  - matches TSV header exactly matches this plan.
  - floats are formatted with `"{value:.6g}"`.
  - blank optional numeric fields are written as blank.
  - text values starting with `=`, `+`, `-`, or `@` are Excel-formula escaped.

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_validation_writer.py -v
```

Expected red: missing `xic_extractor.alignment.validation_writer`.

- [ ] Implement:
  - `write_validation_summary_tsv(path: Path, metrics: Sequence[SummaryMetric]) -> None`.
  - `write_legacy_matches_tsv(path: Path, matches: Sequence[FeatureMatch]) -> None`.
  - tab delimiter, UTF-8, newline-safe writes.
  - local `_escape_tsv_text()` helper matching Plan 3 Excel formula escaping rules.

- [ ] Re-run and commit:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_validation_writer.py -v
git add xic_extractor\alignment\validation_writer.py tests\test_alignment_validation_writer.py
git commit -m "feat(alignment): write legacy validation reports"
```

### Task 4: Validation Pipeline

**Files:**
- Create: `xic_extractor/alignment/validation_pipeline.py`
- Test: `tests/test_alignment_validation_pipeline.py`

- [ ] Write red tests:
  - pipeline loads XIC alignment once.
  - pipeline accepts any combination of FH, metabCombiner, and combine-fix legacy sources.
  - pipeline rejects a run with zero legacy sources.
  - pipeline passes `sample_scope` and match-distance warning thresholds to summary generation.
  - pipeline writes exactly summary and matches TSV by default.
  - pipeline does not import or call RAW reader helpers.
  - writer failure leaves no partial output pair from the failed run.

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_validation_pipeline.py -v
```

Expected red: missing `xic_extractor.alignment.validation_pipeline`.

- [ ] Implement:
  - `AlignmentValidationOutputs(summary_tsv: Path, matches_tsv: Path)`.
  - `run_alignment_validation(alignment_review, alignment_matrix, output_dir, legacy_fh_tsv=None, legacy_metabcombiner_tsv=None, legacy_combine_fix_xlsx=None, match_ppm=20.0, match_rt_sec=60.0, sample_scope="xic", match_distance_warn_median=0.5, match_distance_warn_p90=0.8)`.
  - load each provided legacy source.
  - compare each loaded legacy matrix independently.
  - write summary and matches to temp paths, then replace final paths after both writes succeed.

- [ ] Re-run and commit:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_validation_pipeline.py -v
git add xic_extractor\alignment\validation_pipeline.py tests\test_alignment_validation_pipeline.py
git commit -m "feat(alignment): orchestrate legacy validation"
```

### Task 5: CLI Entry Point

**Files:**
- Create: `scripts/run_alignment_validation.py`
- Modify: `pyproject.toml`
- Test: `tests/test_run_alignment_validation.py`

- [ ] Write red tests:
  - CLI resolves `--alignment-dir` into `alignment_review.tsv` and `alignment_matrix.tsv`.
  - CLI accepts explicit `--alignment-review` and `--alignment-matrix`.
  - CLI passes legacy paths, ppm/RT thresholds, sample scope, and distance warning thresholds to `run_alignment_validation()`.
  - CLI rejects missing alignment files with exit code `2`.
  - CLI rejects zero legacy sources with exit code `2`.
  - CLI rejects invalid `--sample-scope` values with exit code `2`.
  - pyproject registers `xic-align-validate-cli`.

Run:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_run_alignment_validation.py -v
```

Expected red: missing `scripts.run_alignment_validation` and pyproject entry point.

- [ ] Implement `scripts/run_alignment_validation.py` using the style of `scripts/run_alignment.py`.
- [ ] Add pyproject script:

```toml
xic-align-validate-cli = "scripts.run_alignment_validation:main"
```

- [ ] Re-run and commit:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_run_alignment_validation.py -v
git add scripts\run_alignment_validation.py pyproject.toml tests\test_run_alignment_validation.py
git commit -m "feat(alignment): add legacy validation CLI"
```

### Task 6: Roadmap And Real-Data Commands

**Files:**
- Modify: `docs/superpowers/plans/2026-05-10-untargeted-cross-sample-alignment.md`
- Modify: `docs/superpowers/plans/2026-05-11-alignment-legacy-validation-plan.md`

- [ ] Update roadmap index:
  - Plan 4 links to this file.
  - Execution order says Plans 1-4 are written.
  - Plan 4 is described as validation and replacement-decision support.

- [ ] Add real-data validation command block to this plan.

8-raw smoke sequence:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run xic-discovery-cli --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" --dll-dir "C:\Xcalibur\system\programs" --output-dir "output\discovery\tissue8_alignment_v1" --neutral-loss-tag DNA_dR --neutral-loss-da 116.0474 --resolver-mode local_minimum
$env:UV_CACHE_DIR='.uv-cache'; uv run xic-align-cli --discovery-batch-index "output\discovery\tissue8_alignment_v1\discovery_batch_index.csv" --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\validation" --dll-dir "C:\Xcalibur\system\programs" --output-dir "output\alignment\tissue8_alignment_v1" --resolver-mode local_minimum
$env:UV_CACHE_DIR='.uv-cache'; uv run xic-align-validate-cli --alignment-dir "output\alignment\tissue8_alignment_v1" --legacy-fh-tsv "C:\Users\user\Desktop\MS Data process package\MS-data aligner\output\program2_DNA\program2_DNA_v4_alignment_standard.tsv" --legacy-metabcombiner-tsv "C:\Users\user\Desktop\NTU cancer\Processed Data\DNA\Mzmine\new_test\metabcombiner_fh_format_20260429_130630.tsv" --legacy-combine-fix-xlsx "C:\Users\user\Desktop\NTU cancer\Processed Data\DNA\Mzmine\new_test\metabcombiner_fh_format_20260422_213805_combined_fix_20260422_223242.xlsx" --sample-scope xic --output-dir "output\alignment_validation\tissue8_alignment_v1"
```

85-raw validation sequence:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run xic-discovery-cli --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R" --dll-dir "C:\Xcalibur\system\programs" --output-dir "output\discovery\tissue85_alignment_v1" --neutral-loss-tag DNA_dR --neutral-loss-da 116.0474 --resolver-mode local_minimum
$env:UV_CACHE_DIR='.uv-cache'; uv run xic-align-cli --discovery-batch-index "output\discovery\tissue85_alignment_v1\discovery_batch_index.csv" --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R" --dll-dir "C:\Xcalibur\system\programs" --output-dir "output\alignment\tissue85_alignment_v1" --resolver-mode local_minimum
$env:UV_CACHE_DIR='.uv-cache'; uv run xic-align-validate-cli --alignment-dir "output\alignment\tissue85_alignment_v1" --legacy-fh-tsv "C:\Users\user\Desktop\MS Data process package\MS-data aligner\output\program2_DNA\program2_DNA_v4_alignment_standard.tsv" --legacy-metabcombiner-tsv "C:\Users\user\Desktop\NTU cancer\Processed Data\DNA\Mzmine\new_test\metabcombiner_fh_format_20260429_130630.tsv" --legacy-combine-fix-xlsx "C:\Users\user\Desktop\NTU cancer\Processed Data\DNA\Mzmine\new_test\metabcombiner_fh_format_20260422_213805_combined_fix_20260422_223242.xlsx" --sample-scope xic --output-dir "output\alignment_validation\tissue85_alignment_v1"
```

- [ ] Run stale wording checks:

```powershell
$stalePlan4Pattern = "Plan 4 is a roadmap " + "placeholder"
Select-String -SimpleMatch $stalePlan4Pattern docs\superpowers\plans\2026-05-10-untargeted-cross-sample-alignment.md
Select-String -SimpleMatch "Plan 4: Legacy Pipeline Validation" docs\superpowers\plans\2026-05-10-untargeted-cross-sample-alignment.md
```

Expected:

- First command has no matches.
- Second command finds the Plan 4 link line.

- [ ] Commit:

```powershell
git add docs\superpowers\plans\2026-05-10-untargeted-cross-sample-alignment.md docs\superpowers\plans\2026-05-11-alignment-legacy-validation-plan.md
git commit -m "docs(alignment): define legacy validation plan"
```

## Validation

Run after implementation:

```powershell
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_legacy_io.py tests/test_alignment_validation_compare.py tests/test_alignment_validation_writer.py tests/test_alignment_validation_pipeline.py tests/test_run_alignment_validation.py -v
$env:UV_CACHE_DIR='.uv-cache'; uv run pytest tests/test_alignment_csv_io.py tests/test_alignment_tsv_writer.py tests/test_alignment_pipeline.py tests/test_run_alignment.py -v
$env:UV_CACHE_DIR='.uv-cache'; uv run ruff check xic_extractor tests scripts
$env:UV_CACHE_DIR='.uv-cache'; uv run mypy xic_extractor
```

No RAW validation is required for unit completion. Real-data commands in Task 6 are the handoff for manual validation after Plans 1-3 are implemented.

## Acceptance Criteria

- `xic-align-validate-cli` exists.
- Validation reads XIC Plan 3 alignment outputs.
- Validation reads FH alignment TSV.
- Validation reads metabCombiner TSV and separates FH/MZmine blocks when available.
- Validation reads combine-fix xlsx first sheet.
- Validation writes exactly `alignment_validation_summary.tsv` and `alignment_legacy_matches.tsv`.
- Missing and zero legacy values are treated as missing.
- Sample name normalization is deterministic and tested.
- Validation sample scope defaults to XIC sample order so 8-raw validation against a full legacy matrix does not create false sample-name warnings.
- Feature matching is one-to-one, deterministic, and threshold-bound.
- Match-distance warnings use median/p90 `distance_score` thresholds, not impossible post-filter tolerance exceedance.
- Sparse-overlap match status has a numeric rule.
- Reports distinguish `BLOCK`, `WARN`, `OK`, and `INFO`.
- Validation modules do not import RAW readers.
- Roadmap no longer labels Plan 4 as pending.

## Self-Review Notes

- This plan keeps validation separate from discovery/alignment execution.
- This plan avoids using legacy outputs as strict numeric truth.
- This plan gives the user a compact replacement-decision surface without expanding the normal alignment deliverables.
- This plan leaves GUI, HTML, and automatic workflow replacement to separate product decisions.
