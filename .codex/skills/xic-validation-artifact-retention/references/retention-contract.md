# Retention Contract

## Classes

- Source: scripts, tests, docs, guide templates, schemas.
- Summary/index: compact human or machine index that points to heavy artifacts.
- Guide/review surface: small HTML or Markdown meant for durable human review.
- Diagnostic output: generated evidence used for a decision but not product
  behavior.
- Heavy output: full TSV dumps, workbooks, trace JSON, PNG bundles, generated
  galleries, and large replay folders.
- Scratch: temporary investigation files with no durable value.

## Rules

- Search existing retention inventory and checker before adding new retention
  machinery.
- Track only the smallest artifact that preserves reviewability.
- Keep heavy generated outputs under task-specific `output/` paths and ignored
  unless an explicit public contract says otherwise.
- Update artifact inventory or retention checker when tracked guide/index files
  change size, path, or role.
- Do not use a retained diagnostic artifact as proof of product readiness without
  the matching product gate.

## Closeout Checks

- `git status` shows no accidental full table, workbook, or PNG bundle.
- `git diff --check` passes for retained text files.
- Secret/local-path scan has no credentials or machine-specific absolute paths.
- Retention checker passes when relevant.
