# P3 — Third-Party Shadow Comparison Spec

**Date:** 2026-05-24
**Status:** Diagnostic slice draft v0.1
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

### Prerequisite: mzML Conversion

asari and MassCube both consume mzML, not Thermo `.raw` files. This spec
treats mzML conversion as a **prerequisite step owned outside this spec**:

- mzML conversion must be performed once per RAW file before any shadow
  runner can execute
- conversion tool is the project's existing choice (msconvert via
  ProteoWizard, ThermoRawFileParser, or an internal emit-mzML path); the
  decision is recorded in `tools/diagnostics/README.md` at implementation
  time, not in this spec
- the shadow runner accepts mzML paths only; it does not invoke conversion
  itself

If no project-standard conversion path exists yet, P3 implementation must
not silently introduce one — escalate to a separate conversion spec.

Out of scope for this spec:

- non-LC-MS/MS modes
- conversion of `.raw` to mzML (see prerequisite above)

## Required Adapters

Two thin adapters under `tools/diagnostics/`:

### `tools/diagnostics/asari_shadow_runner.py`

- accept a list of mzML paths plus an output directory
- invoke the asari per-sample feature extraction interface (CLI or Python
  API as documented by the installed asari version; exact entry point name
  is determined at implementation time, not asserted by this spec)
- collect the asari feature table output
- emit `output/shadow_comparison_asari_<dataset>.tsv` with columns:
  - `sample_stem`
  - `mz_observed_asari`
  - `rt_apex_min_asari`
  - `peak_start_min_asari`
  - `peak_end_min_asari`
  - `area_asari`
  - `snr_asari`
  - `confidence_asari` (asari-native flag)

### `tools/diagnostics/masscube_shadow_runner.py`

- same shape as the asari adapter, using the MassCube Python API
- emit `output/shadow_comparison_masscube_<dataset>.tsv` with the analogous
  column set

### `tools/diagnostics/shadow_comparison_join.py`

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
- MassCube license (unconfirmed at the time of this spec; check repo)
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
3. document any version pin under `tools/diagnostics/README.md`

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

- Does asari produce per-sample feature tables that can be matched 1:1 to our
  per-sample `alignment_cells.tsv`, or does it produce post-alignment feature
  IDs that need a different join key? Verify before implementing the join.
- Does MassCube expose a per-sample API, or only batch? If batch only, the
  matcher needs to consume MassCube's own feature IDs.
- Should the matcher use the internal `precursor_mz` and `rt_apex_min` as
  anchors, or should it use cluster-center coordinates? Per-sample is more
  honest about peak-picking disagreement; cluster-center hides feature-level
  disagreement.
- mzML conversion: which tool is the project's reference? msconvert,
  ThermoRawFileParser, or the internal raw_reader's emit-mzML mode?

## Cleanup Hook

Implementation should keep diagnostic scripts isolated from production code
so Phase 2 work (especially C6 alignment grouping consolidation) is not
forced to reckon with diagnostic dependencies:

- all asari / MassCube runner code lives under `tools/diagnostics/`. The
  `xic_extractor/` production package must not import from this directory.
- the join report (`shadow_comparison_<dataset>.tsv`) is an output artifact
  only. No production module reads it back.
- asari / MassCube live in an **isolated venv**. The main project
  `pyproject.toml` does not gain these dependencies. C2 / C6 can later
  delete or move the diagnostic scripts without touching production
  dependencies.
- if the diagnostic runner needs a project utility (e.g. mzML conversion),
  import a stable project helper when that helper does not pull optional
  third-party packages into production. Keep only the asari / MassCube
  adapter and dependency-launch code isolated in `tools/diagnostics/`; do not
  duplicate maintained project utilities just to keep the diagnostic script
  deletable.

## Acceptance Owner

Diagnostic report reviewed by the methodology owner. Findings recorded under
`docs/superpowers/notes/2026-MM-DD-third-party-shadow-findings.md`. No
production change is gated on this; the note records the evidence and any
follow-up decisions.
