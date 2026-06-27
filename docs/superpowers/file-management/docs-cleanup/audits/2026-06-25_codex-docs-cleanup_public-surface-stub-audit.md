# Public Surface Stub Audit

Status: `audit_only`

This report checks whether the repo has become a public-facing collection of
empty private-history stubs. At the time of the audit, 254 paths had already
been approved for removal; the final approved 360 removals were later included
in commit `634d568c`. This report does not authorize any additional `git rm`.

## Verdict

The current branch has a large stub forest. That is acceptable only as a migration intermediate state, not as the final public repo shape. The intended final shape is: formal repo docs stay complete and self-contained; private development history lives in Obsidian; compatibility stubs are removed after their repo referrers are updated.

## Counts

- Stub files scanned: 106.
- Referrer scan scope: tracked files plus untracked non-ignored source files, excluding this cleanup's generated audit artifacts.
- Need non-diagnostic public referrer cleanup before removal: 0.
- Diagnostic-provenance-only references: 0.
- Historical-referrer-only removal candidates: 0.
- No-repo-referrer removal candidates: 106.
- TSV inventory: `docs/superpowers/file-management/docs-cleanup/audits/2026-06-25_codex-docs-cleanup_public-surface-stub-audit.tsv`.
- Candidate deletion manifest: `docs/superpowers/file-management/docs-cleanup/2026-06-25_codex-docs-cleanup_git-rm-candidate-manifest.md`.
- Candidate deletion TSV: `docs/superpowers/file-management/docs-cleanup/2026-06-25_codex-docs-cleanup_git-rm-candidate-manifest.tsv`.

## Policy

- Do not present private-history stubs as public documentation.
- Keep formal repo source-of-truth docs self-contained.
- Keep same-path stubs only while exact repo referrers still need them.
- After referrers point at formal docs or archive indexes, remove stubs from version control in an explicit file-management patch.
- Do not use `git rm` until the user explicitly approves the exact candidate set.

## Top Non-Diagnostic Public Referrer Blockers

| Public refs | Stub | Sample public referrers |
| ---: | --- | --- |
| 0 | none | none |

## Next Patch Shape

1. No non-diagnostic public referrer blockers remain.
2. Treat `tools/diagnostics/INDEX.md` hits as historical provenance identifiers, not current source-of-truth links and not a reason to retain same-path private-history stubs.
3. Prepare an exact removal candidate set grouped as no-referrer, historical-referrer-only, and diagnostic-provenance-only stubs.
4. Keep only a small migration index explaining that private development history is in Obsidian.
5. Ask for explicit approval before running `git rm` on any candidate set.
