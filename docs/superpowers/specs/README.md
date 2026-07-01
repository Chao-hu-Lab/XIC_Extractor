# Transient Specs

Doc placement: repo_support_doc
Doc kind: manifest
Doc lifecycle: active
Repo owner: docs/project-layout.md
Doc exit rule: Update when transient spec lifecycle or docs/superpowers routing changes.

Status: `transient_markdown_lane`

`docs/superpowers/specs/` is for short-lived, human-readable Markdown specs
that need to stay in the repo while development is active.

Rules:

- Only Markdown files belong here.
- JSON schemas and authority manifests belong in `docs/superpowers/schemas/`.
- Validation packets, inventories, fixtures, HTML stories, and workbooks belong
  in their explicit validation, fixture, product, ignored output, or Obsidian
  lanes.
- Every new spec must declare `Doc placement`, `Doc kind`, `Doc lifecycle`,
  `Repo owner`, and `Doc exit rule`.
- A spec must name the product owner that will absorb the durable decision.
- When implementation lands, update the product owner, run product-absorption
  review, source-copy the original long-form spec to Obsidian, then remove the
  repo original through `tools/diagnostics/retire_docs.py --evidence <json>`.
- Stage the matching
  `docs/superpowers/file-management/docs-cleanup/*retirement-evidence*.json`
  packet with any lifecycle-managed deletion; the placement guard blocks direct
  deletion without matching `source_hash` and a clean exact-referrer state.
- `tools/diagnostics/docs_management_audit.py --repo-only
  --fail-on-completed-transient` is the repo-visible gate for completed specs
  that were not retired or reduced to an allowed stub state.
- Keep a same-path repo stub only while the spec is still active or exact repo
  referrers cannot yet be retargeted to the owner.

Specs are not durable product authority. They are active development contracts
with an exit path. Normal completed-spec exit is `pass_can_retire`, not a
permanent repo stub.
