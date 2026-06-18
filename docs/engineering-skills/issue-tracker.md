# Issue Tracker: GitHub

Issues and PRDs for this repo live in GitHub Issues. Use the `gh` CLI for issue
operations from inside the repository clone so it can infer the repository from
`git remote`.

## Conventions

- Create an issue: `gh issue create --title "..." --body "..."`
- Read an issue: `gh issue view <number> --comments`
- List issues: `gh issue list --state open --json number,title,body,labels,comments`
- Comment on an issue: `gh issue comment <number> --body "..."`
- Apply or remove labels: `gh issue edit <number> --add-label "..."`
  or `--remove-label "..."`
- Close an issue: `gh issue close <number> --comment "..."`

Use heredocs or files for multi-line issue bodies.

## Skill Semantics

When a skill says "publish to the issue tracker", create a GitHub issue.

When a skill says "fetch the relevant ticket", run
`gh issue view <number> --comments` and include labels in the local reasoning
when triage state matters.
