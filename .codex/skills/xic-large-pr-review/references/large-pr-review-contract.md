# Large PR Review Contract

## Scope Check

Start with read-only state:

```powershell
git status --short --branch
gh pr view --json number,title,state,isDraft,baseRefName,headRefName,mergeable,commits,statusCheckRollup,url
$base = gh pr view --json baseRefName --jq ".baseRefName"
git diff --stat "origin/$base...HEAD"
git diff --name-only "origin/$base...HEAD"
```

If the worktree is dirty, say whether dirty files affect the review. Do not
revert or stage anything.

## Review Strategy

For mechanical writer migrations, verify representative callers and the shared
formatter rather than every identical call site. Check custom formatters, line
terminators, encodings, hidden schema fields, and row order.

When the PR mentions matrix-only, deep-audit, activation, or value delta, look
for evidence covering activation decisions, activation value delta, matrix cell
values, sample identity, matrix identity sidecars, row ordering, deterministic
duplicate policy, and publication-mode differences.

When the PR touches RAW access or overlay extraction, check batching/cache
changes preserve one output row per requested family/sample/seed, fallback
behavior, trace cropping back to the request window, and explicit counts for RAW
opens, XIC requests, batch calls, super-window groups, and trace points when
metrics exist.

## Stop Rules

Stop and report limitation when:

- PR base cannot be determined;
- CI status cannot be checked and no local gate can substitute;
- diff is too large for meaningful blast-radius mapping;
- a suspected issue cannot be grounded in a changed file, public contract, or
  focused test gap.

For subagent review, use `docs/agent-subagent-routing.md` only when the user
explicitly asks for subagents or runtime policy permits it.
