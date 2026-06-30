# Superpowers Documentation Layout

Doc placement: repo_support_doc
Doc kind: manifest
Doc lifecycle: active
Repo owner: docs/project-layout.md
Doc exit rule: Update when docs/superpowers directory routing or repo/Obsidian boundary rules change.

Status: `routing_index`

`docs/superpowers/` keeps public, repo-readable planning and evidence artifacts
that are still useful to future agents and reviewers. It is not a dumping ground
for private branch history. Long development diaries, command narratives,
discarded reasoning, and local context belong in Obsidian or ignored local
storage after their stable public claims are represented in formal repo docs.

## Directory Map

| Directory | Purpose | Do not put here |
| --- | --- | --- |
| `plans/` | active control planes, named roadmaps, and intentionally retained public plans | private implementation diary or branch scratch |
| `specs/` | public specs, schema contracts, design contracts, and retained formal behavior docs | command transcripts or local validation chronology |
| `validation/` | checker-readable validation packets, inventories, summaries, lockbox artifacts, and compact evidence | unbounded generated dumps or private reviewer rationale |
| `fixtures/` | small test/checker fixtures and expected-output oracles | full validation bundles |
| `productization/status/` | machine-readable or checker-facing productization status anchors | branch handoff state |
| `productization/evidence/` | compact public productization evidence summaries | active branch handoff or private diary |
| `file-management/` | approved cleanup manifests, referrer audits, migration queues, and placement evidence | product behavior specs or handoff logs |
| `closeouts/` | intentionally public branch closeout summaries and PR-body seeds | active handoff next actions |
| `handoffs/` | ignored local active handoff workspace plus rare tracked compatibility stubs | productization anchors, file-management manifests, or closeout summaries |
| `notes/`, `goals/`, `reports/`, `pulse-reports/` | retained legacy or public-readable remnants pending further normalization | new private history by default |

## Public Repo Boundary

The public repo should keep:

- formal source-of-truth docs under `docs/product/`, `docs/agent/`, and the
  top-level architecture/evidence contracts;
- compact public evidence, closeout summaries, and migration indexes that are
  safe for public review;
- schema contracts, test fixtures, validation inventories, and small summaries
  when code or tests still depend on them;
- product/user-facing HTML reading artifacts when they are still useful as
  complete public documentation.

The public repo should not keep hundreds of same-path private-history stubs as
the final state. Those stubs are temporary compatibility surfaces while repo
referrers, tests, and diagnostic provenance are audited.

Branch-story or worktree-report HTML belongs to the same cleanup decision as
handoff history; it should not block private-history stub removal unless the
repo deliberately keeps it as a public artifact.

## Current Cleanup Evidence

The current docs-cleanup control surface lives under
`docs/superpowers/file-management/docs-cleanup/`. Tracked topic indexes were
retired because `docs/product/` is the durable topic layer. If a cleanup pass
needs browsable topic pages, generate them to ignored `output/docs-topic-indexes/`.

Retained cleanup evidence:

- `docs/superpowers/file-management/docs-cleanup/2026-06-29_docs-superpowers-routing-manifest.md`
- `docs/superpowers/file-management/docs-cleanup/2026-06-29_docs-superpowers-topic-clusters.tsv`
- optional ignored topic indexes under `output/docs-topic-indexes/`

Completed or archived support:

- `docs/superpowers/file-management/docs-cleanup/2026-06-29_obsidian-source-copy-stub-batch.md`
- `docs/superpowers/file-management/docs-cleanup/audits/2026-06-25_codex-docs-cleanup_public-surface-stub-audit.md`
- `docs/superpowers/file-management/docs-cleanup/2026-06-25_codex-docs-cleanup_git-rm-candidate-manifest.md`
- `docs/superpowers/file-management/docs-cleanup/2026-06-25_codex-docs-cleanup_file-management-approval-plan.md`

The 6/25 files are archived approval and audit evidence. They are not the
current routing queue, and they do not authorize additional deletion. Any
removal still requires an exact approved path set and a separate
file-management patch.

## Validation Layout Debt

`validation/` remains intentionally mixed for now because scripts, tests,
hashes, inventories, and productization status artifacts reference many exact
paths. Do not move the validation tree wholesale. A validation relocation must
be a focused checker-aware migration that updates referrers, retention rows,
hashes, schemas, tests, and docs in the same patch.
