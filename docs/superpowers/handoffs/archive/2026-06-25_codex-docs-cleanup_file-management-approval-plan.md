# File-Management Approval Plan

Status: `approved_no_referrer_batches_staged_no_commit`

This plan records the non-code file-management patch for private-history stubs.
The two explicitly approved no-referrer batches have been staged for removal.
This plan does not authorize any additional deletion or `git rm`.

## Objective

Move the repo from a temporary same-path stub forest to a mature public-doc
shape:

- formal source-of-truth docs remain in version control;
- concise public migration indexes remain in version control;
- private development history remains in Obsidian;
- same-path private-history stubs leave version control only after their exact
  candidate set is approved.

## Inputs

- Public-surface audit:
  `docs/superpowers/handoffs/archive/2026-06-25_codex-docs-cleanup_public-surface-stub-audit.md`
- Exact candidate manifest:
  `docs/superpowers/handoffs/archive/2026-06-25_codex-docs-cleanup_git-rm-candidate-manifest.md`
- Exact candidate TSV:
  `docs/superpowers/handoffs/archive/2026-06-25_codex-docs-cleanup_git-rm-candidate-manifest.tsv`

## Current Candidate Set

The user approved the original `removal_candidate_no_repo_referrers` group of
254 paths, and that exact group is staged for removal. After public,
diagnostic-provenance, historical, fixture-provenance, and HTML-story referrer
hygiene, the refreshed audit reported the candidates below. The user then
explicitly approved the refreshed 106-path `removal_candidate_no_repo_referrers`
group, and that exact group is also staged for removal. No commit has been made.

| Candidate group | Count | Risk | Proposed handling |
| --- | ---: | --- | --- |
| `removal_candidate_no_repo_referrers` | 106 | Low | Approved by the user and staged with `git rm -f`; no further action before commit review. |
| `removal_candidate_after_historical_referrer_cleanup` | 0 | n/a | Historical referrers were rewritten to formal owners or opaque retired-provenance identifiers. |
| `diagnostic_provenance_only` | 0 | n/a | Diagnostic index provenance was rewritten to opaque retired-provenance identifiers. |

The audit currently reports `keep_temporarily_update_public_referrers = 0`, so
no public, diagnostic-provenance, historical, or fixture-provenance referrer
blocks the remaining candidate set.

## Remaining Evaluation After First Batch

Read-only review and referrer hygiene closed the previous risk lanes:

- Public referrers now point to formal owners such as `docs/product/`,
  `docs/diagnostic-ledger.md`, and the productization control plane.
- `tools/diagnostics/INDEX.md` and old historical plans/specs now use opaque
  `retired-provenance:*` identifiers instead of readable private-history paths.
- Branch-story HTML now links to formal product docs rather than retired stub
  specs.
- The retained diagnostic fixture now records retired provenance identifiers for
  reused historical oracle rows instead of exact private-history note paths.

The exact refreshed approval set was the `removal_candidate_no_repo_referrers`
group in the TSV manifest. It contained 106 paths and has been staged for
deletion. Any additional deletion needs a new exact path set and user approval.

## What Must Stay In Repo

- `docs/product/README.md` and topic pages.
- `docs/deepresearch/README.md` as a public-safe research takeaway index.
- `docs/superpowers/README.md` as the migration boundary index.
- Handoff rules and current branch handoff files that are still active.
- Test-backed fixtures and schema contracts under `docs/validation/` and
  `tests/fixtures/`.
- Validation inventories, lockboxes, status indexes, authority manifests, and
  machine-readable artifacts that checkers still consume.
- Product-facing or user-facing HTML reports that remain useful as complete
  reading artifacts.

## What Should Not Stay Long Term

- Same-path private-history stubs whose full content already lives in Obsidian.
- Dated implementation diaries, branch scratch notes, and planning transcripts
  that no current checker or public doc depends on.
- Research-note stubs whose durable public takeaways have already been folded
  into `docs/deepresearch/README.md` and `docs/product/`.
- Branch-story or worktree-report HTML that only packages dated handoff/story
  context and is not a product/user-facing artifact.

## HTML Story Artifacts

The audit treats tracked `.html` files as referrers. The two branch-story HTML
files that previously pointed at retired spec stubs now point to formal product
docs instead, so they no longer block candidate cleanup. The HTML files
themselves are not part of the current deletion candidate set.

## Approval Sequence

1. Review the TSV candidate list and spot-check representative paths in each
   group.
2. First approved batch: staged removal of the original 254 no-referrer paths is
   complete.
3. Second approved batch: staged removal of the refreshed 106 no-referrer paths
   is complete.
4. Approve any further group or exact path subset separately before another
   `git rm`.
5. Re-run the public-surface audit after removal if the manifest/report should
   be refreshed for commit review.
6. Re-run focused tests that consume docs or fixtures.
7. Keep this plan and the audit report as the public explanation for why
   private-history files left version control.

## Productization Control Plane

No productization control-plane tier or active-lane update is required for this
file-management plan. It changes only documentation placement and migration
governance. It does not change maturity tier, active lane, writer authority,
output schema, review/replay behavior, selected values, selected area/counting,
matrix values, or matrix authority.
