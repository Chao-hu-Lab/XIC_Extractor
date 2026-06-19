# Validation Artifact Retention Policy

Status: living policy for `docs/superpowers/validation`.
Scope: version-controlled validation artifacts only.

This directory is a product-evidence index, not a full result dump. Keep enough
state to audit, regenerate, and review product claims; externalize bulky rendered
outputs and full-run tables unless they are the smallest durable contract source.

## Decisions

Use one of these retention decisions in `ARTIFACT_INVENTORY.tsv`.

| Decision | Meaning |
| --- | --- |
| `keep_contract` | Keep in git. Artifact is a schema-bound contract, authority/status index, unique source manifest, or checker input that must be present on a clean checkout. |
| `keep_summary` | Keep in git. Artifact summarizes a generated bundle with source paths, hashes, row counts, commands, or status. |
| `keep_minimal_fixture` | Keep in git. Artifact is a small golden slice required by focused tests/checkers. |
| `shrink_later` | Still in git for now, but should be reduced to a summary plus minimal fixture in a later focused cleanup. |
| `externalize` | Move out of git. Keep local/release artifact copies under ignored artifact storage and preserve regeneration metadata in git. |
| `delete_generated` | Remove from git. Artifact is purely generated and reproducible from tracked scripts plus retained inputs. |

## Keep In Git

- Validation README files, short notes, and source-backed summaries.
- JSON/TSV manifests that are the only source of a contract or case universe.
- Status and authority indexes checked by productization scripts.
- Minimal golden fixtures used by tests or checkers.
- Synthetic fixture TSVs with only the rows needed to exercise
  readiness/checker branches are `keep_minimal_fixture`, not `shrink_later`.
- Hash/source summaries and generation commands for externalized artifacts.

## Do Not Keep Full Dumps By Default

- Full `cell_provenance.tsv`, review-row TSVs, and downstream-impact input
  copies when they can be regenerated from retained scripts and manifests.
- Rendered HTML reports, review galleries, and packet pages.
- PNG plots and other binary review media.
- Duplicated inputs copied into validation packets when a retained
  source-summary/hash is sufficient.

## Externalization Convention

When externalizing tracked validation output, move the local copy under:

```text
local_validation_artifacts/externalized_superpowers_validation/<relative path>
```

That directory is ignored by git. Keep a tracked README, summary JSON, or
inventory row with the original path, tracked replacement/summary, local
externalized path, source script, hash/row-count evidence, and regeneration
command where available.

## Local Gate

Run the inventory checker before PR or closeout:

```powershell
uv run python scripts/check_validation_artifact_retention.py
```

This default gate is clean-checkout safe: it checks the tracked inventory,
current validation file surface, rendered HTML/PNG references, and
`shrink_later` debt without requiring ignored local rendered files.

On the machine that still has externalized local review artifacts, also run:

```powershell
uv run python scripts/check_validation_artifact_retention.py --require-externalized-local
```

Use `--strict` only for a focused shrink cleanup where all `shrink_later` rows
are expected to be removed.

## Product Boundary

Retention cleanup must not change ProductWriter behavior, default extraction,
matrix values, workbook/GUI behavior, selected peak/area, counted detection, or
Backfill authority. If a retained artifact is referenced by
`productization_status_index_v1.tsv` or a checker default, do not externalize it
until the checker/status contract is updated in the same goal and verified.
