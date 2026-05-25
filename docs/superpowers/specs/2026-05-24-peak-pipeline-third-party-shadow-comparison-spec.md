# P3 — Third-Party Shadow Comparison Spec

**Date:** 2026-05-24
**Status:** 8RAW diagnostic completed; external tooling not retained
**Overview:** [Peak pipeline modernization overview](2026-05-24-peak-pipeline-modernization-overview-spec.md)
**Parallel to:** P4, P5
**Precondition:** P2 AsLS shadow column emitted (recommended; not strictly
required)

## Purpose

Compare the in-house peak picking / integration / RT correction outputs
against two modern third-party Python LC-MS pipelines:

- `asari` (Li et al. 2023, Nat Commun) — sensitivity-focused untargeted
  pipeline, pure Python, BSD-3
- `MassCube` (Yu et al. 2025, Nat Commun) — speed-focused untargeted pipeline,
  Gaussian-filter edge detection, pure Python

Both are claimed to outperform XCMS / MZmine 3 / MS-DIAL on standard
benchmarks. This spec uses them as external reference oracles, not as
replacement engines.

2026-05-25 disposition: the 8RAW P3 audit produced only limited asari support
and no usable MassCube output. It does not clear P2b and does not justify P6
RT-correction escalation. The temporary runner / normalizer / joiner code is
not retained as maintained Phase 1 code; preserve the findings note and local
output artifacts as diagnostic evidence only.

## Why Third-Party Reference

Internal benchmarks rely on the strict ISTD set and the identity coherence
controls. These are self-consistent but not independent. A third-party
pipeline that disagrees on a feature is decision evidence regardless of which
party is correct, because the disagreement narrows the failure space.

Disagreement classification:

- internal selects a peak, third-party does not -> investigate false-positive
  on the internal side
- third-party selects a peak, internal does not -> investigate false-negative
  on the internal side
- both select with > 20% area difference -> investigate boundary or baseline

## In-Scope Datasets

- 8RAW strict ISTD acceptance set, already used for P1 / P2 validation
- 85RAW production cohort, when 8RAW comparison reports a verdict

### Experimental mzML Input Constraint

Production XIC_Extractor continues to read Thermo `.raw` files directly. P3
must not introduce `.raw` to mzML conversion as a project prerequisite, a
production fallback, or a hidden preprocessing step.

asari and MassCube consume mzML. For P3, mzML is allowed only as a
user-provided experimental input to third-party shadow tools:

- the shadow runner accepts explicit mzML paths or an explicit mzML directory
- the shadow runner must not invoke conversion tools
- missing mzML files make the third-party shadow run `inconclusive`, not a
  request to convert `.raw`
- the internal comparator remains the current `.raw`-derived alignment output
- all reports must record the mzML source directory and state that mzML was an
  external experimental input
- third-party optional fields such as peak boundaries, S/N, and native
  confidence must stay empty with an explicit native schema status when the
  installed tool does not document an equivalent field; do not invent or infer
  those fields from unrelated columns

Out of scope for this spec:

- non-LC-MS/MS modes
- conversion of `.raw` to mzML
- changing production file-reading assumptions away from direct `.raw`

## Temporary Adapters Used By The Diagnostic Slice

The original diagnostic slice used temporary adapters under
`tools/diagnostics/`. These files are not retained as maintained code after
the 2026-05-25 review, but the adapter contract is preserved here as run
provenance in case a future external-shadow audit is redesigned:

### Historical `tools/diagnostics/asari_shadow_runner.py`

- accept a list of mzML paths plus an output directory
- invoke the asari feature extraction interface (CLI or Python API as
  documented by the installed asari version; exact entry point name and native
  schema are verified at implementation time)
- collect the asari feature table output
- emit `output/shadow_comparison_asari_<dataset>.tsv` in the standardized
  third-party feature schema:
  - `tool`, `sample_stem`, `feature_id`, `mz_observed`, `rt_apex_min`,
    `peak_start_min`, `peak_end_min`, `area`, `snr`, `confidence`,
    `native_schema_status`, `source_path`
- for `asari==1.17.0`, `preferred_Feature_table.tsv` is batch-level. The
  adapter pivots sample columns into sample-level rows and converts native
  `rtime`, `rtime_left_base`, and `rtime_right_base` from seconds to minutes.
  Feature-level aggregate columns such as `peak_area` are not sample rows.

### Historical `tools/diagnostics/masscube_shadow_runner.py`

- same shape as the asari adapter, using the documented MassCube CLI or Python
  API only after the installed version's supported entry point is verified
- emit `output/shadow_comparison_masscube_<dataset>.tsv` in the same
  standardized third-party feature schema, but only after native MassCube m/z,
  RT, and area semantics are verified. Until then, emit
  `unsupported_native_output` rather than guessing.

### Historical `tools/diagnostics/shadow_comparison_join.py`

- consume internal `alignment_cells.tsv` plus the explicit coordinate source
  needed for labels and target/reference coordinates. `alignment_cells.tsv`
  alone is not sufficient: it is a family/cell output and does not guarantee
  `label`, `mz_target`, or `rt_target_min` columns.
- for the 8RAW strict ISTD comparison, join cells through the strict target
  registry / targeted benchmark table so the report can emit target label,
  expected m/z, and expected RT
- for the 85RAW cohort, use feature-family coordinates
  (`feature_family_id`, family-center m/z / RT, or the accepted family
  coordinate artifact) rather than pretending target labels exist for every
  row
- match internal rows to asari and MassCube feature rows by
  `(sample_stem, m/z within preferred_ppm, rt_apex_min within max_rt_sec)`
- for strict ISTD comparison, report `asari_only` / `masscube_only` only when
  the third-party feature also falls within a strict target m/z/RT window.
  Off-target untargeted features are not internal ISTD misses.
- missing or unavailable third-party feature TSVs degrade to pairwise or
  `inconclusive` output rather than crashing the join report
- emit `output/shadow_comparison_<dataset>.tsv` with columns:
  - `sample_stem`, `label`, `mz_target`, `rt_target_min`
  - `area_internal`, `area_internal_baseline_corrected`,
    `area_internal_baseline_corrected_asls` (if P2 enabled)
  - `area_asari`, `area_masscube`
  - `rt_apex_min_internal`, `rt_apex_min_asari`, `rt_apex_min_masscube`
  - `area_rel_diff_asari_pct`, `area_rel_diff_masscube_pct`
  - `internal_coordinate_source` (`strict_target_registry`,
    `feature_family_center`, or another recorded source)
  - `match_status` (`triple_match`, `pair_match_asari`,
    `pair_match_masscube`, `internal_only`, `asari_only`, `masscube_only`)
  - `verdict` (free text from the matcher)

## Verdict Categories

The join report classifies each row into one of:

- `agree_within_5pct` — areas agree within 5% relative
- `agree_within_20pct` — areas agree within 20% relative
- `disagree_low_internal` — internal area below the third-party by > 20%
- `disagree_high_internal` — internal area above the third-party by > 20%
- `internal_missing_third_party_present` — coverage gap on the internal side
- `third_party_missing_internal_present` — coverage gap on third-party side
- `boundary_mismatch` — areas agree but peak boundaries differ by > 0.05 min

## Validation Use

This spec produces shadow evidence only. It does not change any production
output. The shadow evidence is used by humans to decide:

- whether the P1 resolver switch was the right call
- whether the P2 AsLS shadow correctly fixes matrix hump cases
- whether the current alignment / RT correction is causing systematic
  disagreement
- whether to escalate to P6 OBI-Warp RT shadow

## License Verification Required Before Shadow Run

Before adding either tool as a dependency, verify:

- asari license (BSD-3 confirmed in package metadata; verify final repo as
  of the run date)
- MassCube license (verify installed package metadata at run time). The
  2026-05-25 isolated P3 install of `masscube==1.2.20` reported
  `CC BY-NC 4.0`, so MassCube-derived outputs must be treated as local
  diagnostic artifacts unless redistribution is separately reviewed.
- both packages' dependency footprints do not conflict with the project's
  current `pyproject.toml`

If license is incompatible with project distribution, the shadow run can
still proceed locally but the result cannot be redistributed; record the
constraint in the diagnostic README.

## Installation Plan

Recommended order:

1. `uv pip install asari-metabolomics` in an isolated venv used only by the
   shadow runner
2. `uv pip install masscube` in the same isolated venv
3. document any version pin in the run findings note

Avoid mixing third-party dependencies into the main `xic_extractor`
environment. The shadow runner subprocesses the third-party tools from the
isolated venv.

## What This Spec Does Not Change

- internal peak detection, scoring, alignment, or matrix identity
- internal output schemas
- production area or RT values

## Rollback / Removal

Remove the diagnostic scripts and uninstall the third-party packages from the
isolated venv. No production change to revert.

## Open Questions

- Resolved for `asari==1.17.0`: it produces a batch-level feature table with
  sample abundance columns. The P3 adapter pivots this into sample-level rows
  before joining.
- Does MassCube expose a per-sample API, or only batch? If batch only, the
  matcher needs to consume MassCube's own feature IDs.
- Should the matcher use the internal `precursor_mz` and `rt_apex_min` as
  anchors, or should it use cluster-center coordinates? Per-sample is more
  honest about peak-picking disagreement; cluster-center hides feature-level
  disagreement.
- Which user-provided mzML directory should be used for each shadow run? For
  the current 8RAW P3 validation, the source is
  `C:\Users\user\Desktop\NTU cancer\NTU Tissue preprocess\mzml`.

## Cleanup Hook

Implementation should keep diagnostic scripts isolated from production code
so Phase 2 work (especially C6 alignment grouping consolidation) is not
forced to reckon with diagnostic dependencies. For the completed 8RAW audit,
no live P3 diagnostic scripts are retained in the worktree:

- no asari / MassCube runner, normalizer, or joiner code should be treated as
  maintained project code after the 2026-05-25 P3 review.
- the join report (`shadow_comparison_<dataset>.tsv`) is an output artifact
  only. No production module reads it back.
- asari / MassCube live in an **isolated venv**. The main project
  `pyproject.toml` does not gain these dependencies.
- if the diagnostic runner needs a project utility, import a stable project
  helper only when that helper does not pull optional third-party packages
  into production. Keep only the asari / MassCube adapter and
  dependency-launch code isolated in `tools/diagnostics/`; do not duplicate
  maintained project utilities just to keep the diagnostic script deletable.

## Acceptance Owner

Diagnostic report reviewed by the methodology owner. Findings recorded under
`docs/superpowers/notes/2026-MM-DD-third-party-shadow-findings.md`. No
production change is gated on this; the note records the evidence and any
follow-up decisions.
