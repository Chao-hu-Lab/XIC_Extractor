# Untargeted Alignment Output Contract

## Summary

Untargeted alignment must separate production delivery from machine contracts,
debug evidence, and validation artifacts.

The production user should not need to understand every intermediate TSV to use
the result. The developer still needs stable machine-readable artifacts for
diffs, validation, and root-cause analysis.

The output contract is:

```text
production delivery is XLSX + HTML
machine TSV exports are opt-in or validation-level contracts
debug evidence stays available but is not default delivery
algorithm semantics must be clean before output is called production-ready
```

## Product Surfaces

| Surface | Default? | Audience | Purpose |
|---|---:|---|---|
| `alignment_results.xlsx` | yes | User, downstream pipeline | Production package: matrix first, review and metadata in the same workbook. |
| `review_report.html` | yes | User, developer | Visual QC entry point using summarized debug evidence. |
| `alignment_matrix.tsv` | no | Developer, validation, non-Excel downstream | Canonical machine export for diffable area matrix. |
| `alignment_review.tsv` | no | Developer, validation | Machine-readable feature-family review table. |
| `alignment_cells.tsv` | no | Developer | Per-cell provenance and debug evidence. |
| `alignment_matrix_status.tsv` | no | Developer | Status matrix for debugging detected/rescued/absent/unchecked behavior. |
| legacy validation TSVs | no | Developer | Replacement-decision evidence against FH, metabCombiner, and combine-fix outputs. |

Default production output should not emit duplicated representations of the same
matrix unless a plan explicitly changes this contract.

## Production Workbook Contract

`alignment_results.xlsx` is the production artifact.

Required sheets:

1. `Matrix`
   - First sheet.
   - Area matrix for downstream analysis.
   - Rows are final aligned feature-family rows.
   - Columns begin with stable feature metadata, then sample columns.
   - Blank means missing, unchecked, absent, not applicable, zero, negative, or
     non-finite. Do not write `0` for missing values.
2. `Review`
   - Human review summary.
   - Compact. It should help the user decide which rows need attention.
   - It must not become a copy of `alignment_cells.tsv`.
3. `Metadata`
   - Generated timestamp, schema version, resolver mode, input paths, source
     discovery batch, software version or commit when available.

Optional future sheets must be approved by a plan. Candidate examples:

- hidden `Status` sheet, only if a downstream or review workflow needs it.
- hidden `Debug` sheet, only if it replaces a default debug TSV.

The workbook may be named `alignment_matrix.xlsx` only if the first sheet is the
matrix and extra sheets remain supporting context. `alignment_results.xlsx` is
preferred when the workbook includes review and metadata sheets.

## HTML Review Contract

`review_report.html` is the visual QC entry point.

It should show patterns that a table cannot make obvious:

- detected/rescued/unchecked distribution,
- high duplicate-pressure or ownership-conflict rows,
- anchor versus non-anchor feature-family behavior,
- area or status heatmaps,
- suspicious rows that need manual inspection.

HTML must not simply restate the workbook tables. A chart is justified only when
it reduces ambiguity or exposes a batch-level pattern.

HTML may consume debug evidence internally, but the raw debug tables should not
be emitted by default.

## TSV Contract

TSV files are still important, but they are not the production default.

Use TSVs when:

- CI or validation needs stable text diffs.
- Legacy pipeline comparison needs simple loaders.
- A non-Excel downstream tool explicitly requests text input.
- Debugging requires per-cell provenance.

Do not emit both XLSX and equivalent TSV matrices by default. If both are
emitted, the command or output level must make the duplication explicit, for
example `--emit-machine-tsv` or `--debug-output`.

If TSV export is enabled:

- `alignment_matrix.tsv` must match the `Matrix` sheet values.
- `alignment_review.tsv` must match the `Review` sheet row identity and core
  counts.
- `alignment_cells.tsv` and `alignment_matrix_status.tsv` remain deeper debug
  outputs.
- `owner_edge_evidence.tsv` (debug/validation only) contains owner-pair edge
  evidence for pairs that survive the hard-gate envelope prefilter. Owner pairs
  the envelope rejects (same sample, neutral-loss-tag mismatch, or precursor m/z
  outside `max_ppm`) are trivially blocked and are not written. This is the
  post-2026-05-15 contract: earlier runs with drift priors emitted every
  O(n^2) pair because the prefilter was incorrectly disabled whenever the
  evidence sink was active. See
  `2026-05-15-alignment-clustering-performance-spec.md` (Tier 0).

## Status Semantics

Status labels are part of the public scientific contract.

Required meanings:

| Status | Meaning |
|---|---|
| `detected` | Original MS2/discovery evidence supports this feature in this sample. |
| `rescued` / `backfilled` | MS1 re-extraction found a peak for an anchored feature, but it was not an original MS2-triggered detection in that sample. |
| `absent` | Checked and no acceptable peak was found. |
| `unchecked` | Not checked, usually because the feature is not eligible for backfill or the raw trace could not be evaluated. |
| `duplicate_assigned` | A candidate peak was assigned to another feature-family row. This must not be silently encoded as ordinary `absent` in production summaries. |

Open implementation decision:

- The code may use one internal enum or several strings, but production output
  must preserve the semantic difference between original detection, MS1 rescue,
  unchecked, true absence, and duplicate assignment.

## Algorithm Readiness Blockers

These are not output-format details. They block production readiness because they
change what the output means.

1. `rescued` or MS1-backfilled cells must not create feature-family merge
   eligibility.
   - Merge eligibility should be based on original detected evidence.
   - Rescued/present overlap may be secondary consistency evidence only.
2. Family-centered integration must not label pure MS1 backfill as `detected`.
   - `detected` should mean original discovery/MS2 evidence exists for that
     sample-feature cell.
3. Duplicate ownership cannot be represented as ordinary absence.
   - If a cell loses ownership to another feature family, production output must
     either expose `duplicate_assigned` or aggregate it into a clearly labeled
     review/QC signal.
4. CID-only evidence cannot be described as full MS2-pattern protection.
   - Current CID data supports neutral-loss/product compatibility.
   - HCD/full-fragment signature compatibility is a future method extension, not
     a current guarantee.
5. Feature-family identity must be stable.
   - Validation and downstream docs should use `feature_family_id` and
     `family_center_*` terminology, not stale `cluster_id` wording, unless an
     explicit compatibility alias is documented.
6. Multi-tag discovery/config must be designed before production readiness.
   - Current discovery runs one neutral-loss profile at a time.
   - R/dR targets such as `8-oxo-Guo` are a known production-readiness blocker,
     not an owner-family checkpoint failure.
   - Do not add target-specific exceptions to output or alignment logic to hide
     missing multi-tag support.

## Output Levels

Future CLI and GUI work should use output levels instead of many unrelated flags.

| Level | Expected artifacts |
|---|---|
| `production` | `alignment_results.xlsx`, `review_report.html` |
| `machine` | production artifacts plus `alignment_matrix.tsv`, `alignment_review.tsv` |
| `debug` | machine artifacts plus `alignment_cells.tsv`, `alignment_matrix_status.tsv`, detailed diagnostics |
| `validation` | machine artifacts plus legacy comparison TSVs and validation summaries |

Until output levels are implemented, flags should map cleanly onto these levels.
Avoid adding one-off flags that blur production and debug outputs.

## Change Control

Before adding or changing an alignment output artifact, answer:

1. Is this production, machine, debug, or validation?
2. Who reads it?
3. What decision does it help?
4. Does it duplicate an existing artifact?
5. If it duplicates an artifact, why is the duplicate necessary?
6. Does it require a schema/version update?
7. Does it require workbook, TSV, HTML, and validation loader tests?

If a future plan conflicts with this document, update this contract first. Silent
drift is not allowed.

## Relationship To Existing Plans

This contract supersedes any older plan text that calls `alignment_review.tsv`
and `alignment_matrix.tsv` the production default.

Older TSV-focused plans may remain useful for implementation staging and
validation, but final production UX must follow this document unless explicitly
changed by a later approved contract.
