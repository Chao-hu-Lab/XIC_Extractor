# PR70 Alignment Matrix Handoff RAW Validation Note

Doc placement: repo_support_doc
Doc kind: validation_artifact
Doc lifecycle: active
Repo owner: docs/product/quant-matrix.md
Doc exit rule: Retire or demote after the product-priority reset spec points to a newer quant-matrix validation oracle or the diagnostic ledger owns the replacement rerun contract.

## Verdict

Status: `production_ready` for this PR's alignment matrix handoff behavior.

This validation covers the Matrix Behavior change where `alignment_matrix.tsv`
and the optional `alignment_results.xlsx` Matrix projection consume
`AlignedCell.matrix_area`, which prefers selected `IntegrationResult` area and
falls back only through the named `legacy_area_fallback` path.

The production claim is scoped to this PR. It does not retire unrelated legacy
paths, promote new baseline policy, change resolver defaults, or claim broader
Phase2 cleanup readiness.

## Inputs

- 8RAW discovery index:
  `local_validation_artifacts/discovery/accepted_p8b/8raw/discovery_batch_index.csv`
- 85RAW discovery index:
  `local_validation_artifacts/discovery/accepted_p8b/85raw/discovery_batch_index.csv`
- RAW root:
  `$env:XIC_RAW_ROOT`
- DLL dir:
  `$env:THERMO_RAWFILE_READER_DLL_DIR`
- Python runtime:
  `.venv\Scripts\python.exe`

The validation first exposed a path-governance bug: the accepted discovery
inputs existed only under another worktree's ignored `output/`, and the batch
indexes contained absolute `candidate_csv` / `review_csv` paths back to that
worktree. The inputs were promoted into `local_validation_artifacts/` and the
indexes were rewritten there so future branches can reuse them without depending
on `.worktrees/<branch>/output/`.

Chronology note: the completed 8RAW and 85RAW foreground runs were launched
before this artifact-store promotion, using the accepted P8b discovery inputs
from their original generated location. After promotion, both stable-store batch
indexes were preflighted successfully and verified to contain no stale worktree
references. The hash parity results below are therefore valid for this PR, while
the commands below document the stable rerun shape future branches should use.

The current worktree uses a `.venv` junction to the existing repo runtime at
`$env:XIC_REPO_ROOT/.venv`, so canonical 85RAW preflight sees
the executable under the active worktree `.venv`.

## Stable Rerun Commands

8RAW preflight and run shape:

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment --discovery-batch-index "local_validation_artifacts/discovery/accepted_p8b/8raw/discovery_batch_index.csv" --raw-dir $env:XIC_RAW_ROOT --dll-dir $env:THERMO_RAWFILE_READER_DLL_DIR --output-dir output/pr70_alignment_matrix_handoff_validation/alignment/8raw_validation_minimal_superwindow --expected-sample-count 8 --output-level validation-minimal --resolver-mode region_first_safe_merge --backfill-scope production-equivalent --audit-evidence-mode none --performance-profile validation-fast --owner-backfill-window-strategy super-window --owner-backfill-superwindow-span-factor 2 --timing-output output/pr70_alignment_matrix_handoff_validation/alignment/8raw_validation_minimal_superwindow\timing.json --timing-live-output output/pr70_alignment_matrix_handoff_validation/alignment/8raw_validation_minimal_superwindow\timing.live.json
```

85RAW preflight and run shape:

```powershell
.venv\Scripts\python.exe -m scripts.run_alignment --discovery-batch-index "local_validation_artifacts/discovery/accepted_p8b/85raw/discovery_batch_index.csv" --raw-dir $env:XIC_RAW_ROOT --dll-dir $env:THERMO_RAWFILE_READER_DLL_DIR --output-dir output/pr70_alignment_matrix_handoff_validation/alignment/85raw_validation_minimal_superwindow --expected-sample-count 85 --output-level validation-minimal --resolver-mode region_first_safe_merge --backfill-scope production-equivalent --audit-evidence-mode none --performance-profile validation-fast --owner-backfill-window-strategy super-window --owner-backfill-superwindow-span-factor 2 --timing-output output/pr70_alignment_matrix_handoff_validation/alignment/85raw_validation_minimal_superwindow\timing.json --timing-live-output output/pr70_alignment_matrix_handoff_validation/alignment/85raw_validation_minimal_superwindow\timing.live.json
```

## 8RAW Result

- Preflight: pass before run; stable-store preflight pass after artifact
  promotion.
- Run: pass, exit code `0`.
- Sample count: `8`.
- Candidate count: `3,343`.
- Output dir:
  `output/pr70_alignment_matrix_handoff_validation/alignment/8raw_validation_minimal_superwindow`

Primary artifact hash parity against accepted P8b 8RAW:

| Artifact | Result |
|---|---|
| `alignment_matrix.tsv` | byte-identical |
| `alignment_review.tsv` | byte-identical |
| `alignment_cells.tsv` | byte-identical |

Key timing:

| Stage | Seconds |
|---|---:|
| `alignment.build_owners` | 11.03 |
| `alignment.backfill_scope` | 2.00 |
| `alignment.owner_backfill` | 14.07 |
| `alignment.write_outputs` | 1.07 |

## 85RAW Result

- Preflight: pass before run, canonical 85RAW contract enforced; stable-store
  preflight pass after artifact promotion.
- Run: pass, exit code `0`.
- Sample count: `85`.
- Candidate count: `30,289`.
- Output dir:
  `output/pr70_alignment_matrix_handoff_validation/alignment/85raw_validation_minimal_superwindow`

Primary artifact hash parity against accepted P8b 85RAW:

| Artifact | Result |
|---|---|
| `alignment_matrix.tsv` | byte-identical |
| `alignment_review.tsv` | byte-identical |
| `alignment_cells.tsv` | byte-identical |

Key timing:

| Stage | Seconds |
|---|---:|
| `alignment.build_owners` | 24.29 |
| `alignment.backfill_scope` | 98.48 |
| `alignment.owner_backfill` | 204.62 |
| `alignment.write_outputs` | 81.74 |

## Interpretation

The Matrix Behavior implementation is production-ready because:

- synthetic contract tests passed before RAW validation;
- 8RAW and 85RAW foreground validation both completed;
- validation used the canonical `validation-minimal + production-equivalent +
  validation-fast + super-window + timing heartbeat` shape;
- primary downstream artifacts are byte-identical to accepted P8b outputs.

This means selected `IntegrationResult` projection does not change the current
production matrix delivery surface for the accepted 8RAW/85RAW datasets while
establishing the new handoff contract for future matrix behavior.

## Remaining Risk

- This does not prove broader baseline, resolver, CWT, ASLS, or Phase2 cleanup
  decisions.
- The first validation attempt found accepted discovery inputs only in another
  worktree. That is now corrected by `local_validation_artifacts/`; future runs
  should use the stable paths above and not `.worktrees/<branch>/output/`.
