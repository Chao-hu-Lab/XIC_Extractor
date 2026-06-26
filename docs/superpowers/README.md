# Development History Archive

Status: `migration_index`

This tree used to hold a large amount of branch planning, implementation
history, reviews, and research notes. That material is being externalized to a
private Obsidian vault because it can include incomplete reasoning, local
workflow details, and development history that should not be treated as public
product documentation.

## Public Repo Boundary

The public repo should keep:

- formal source-of-truth docs under `docs/product/`, `docs/agent/`, and the
  top-level architecture/evidence contracts;
- concise migration indexes, handoffs, and closeout summaries that are safe for
  public review;
- schema contracts, test fixtures, validation inventories, and small summaries
  when code or tests still depend on them.
- product/user-facing HTML reading artifacts when they are still useful as
  complete public documentation.

The public repo should not keep hundreds of same-path private-history stubs as
the final state. Those stubs are temporary compatibility surfaces while repo
referrers, tests, and diagnostic provenance are audited.

Branch-story or worktree-report HTML belongs to the same cleanup decision as
handoff history; it should not block private-history stub removal unless the
repo deliberately keeps it as a public artifact.

## Migration State

Current audit artifacts:

- `docs/superpowers/handoffs/archive/2026-06-25_codex-docs-cleanup_public-surface-stub-audit.md`
- `docs/superpowers/handoffs/archive/2026-06-25_codex-docs-cleanup_git-rm-candidate-manifest.md`
- `docs/superpowers/handoffs/archive/2026-06-25_codex-docs-cleanup_file-management-approval-plan.md`

No file deletion is authorized by these artifacts. Any removal requires an
explicit approved path set and a separate file-management patch.
