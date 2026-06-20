---
name: xic-validation-artifact-retention
description: Use when XIC validation, Gallery, overlay, RAW, TSV, PNG, trace JSON, workbook, report, or diagnostic output needs a retention decision, artifact inventory update, externalization rule, ignored-output policy, or version-control boundary.
---

# XIC Validation Artifact Retention

Use when deciding what validation artifacts belong in version control and what
must stay externalized under `output/`.

## Retention Contract

Before adding or preserving artifacts, state:

- artifact purpose: source, summary/index, guide, review surface, diagnostic
  output, heavy generated output, or scratch;
- owner path and whether a retained index already exists;
- tracked files versus ignored/externalized files;
- inventory or retention checker updates required;
- whether the artifact is a product contract or diagnostic evidence only.

## Default Policy

- Track compact source docs, guides, summaries, indexes, schemas, and tests.
- Do not track full generated workbooks, full TSV dumps, large PNG bundles,
  trace JSON, or generated galleries unless an approved public contract requires
  it.
- Do not add a second manifest/source of truth when an inventory/checker already
  owns retention.
- Diagnostic candidates are not matrix rows.

## References

- Retention classes, inventory/checker rules, and closeout checks:
  `references/retention-contract.md`
- Trigger and near-neighbor cases:
  `evals/trigger-cases.md`
- Portable skill interface metadata:
  `agents/interface.yaml`
