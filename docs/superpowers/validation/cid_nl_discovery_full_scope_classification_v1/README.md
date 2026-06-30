# CID-NL Discovery Full-Scope Classification v1

Doc placement: repo_support_doc
Doc kind: validation_artifact
Doc lifecycle: archived
Repo owner: docs/product/discovery.md
Doc exit rule: Keep until Discovery product docs or newer validation artifacts supersede this full-scope CID-NL classification gate.

Status: `pass`.

This is a no-RAW classification contract for the current CID-NL Discovery candidate universe. It proves that the 147 candidate cells are fully partitioned before any future product gate is considered.

## Buckets

- Accepted Discovery default bucket: `95` cells.
- Held outside the current bundle: `24` cells.
- Blocked by current paired-overlay evidence: `28` cells.
- Existing successor context preserved with no write: `337` cells.
- Omitted no-target context preserved with no write: `27` cells.

The accepted bucket is exactly the already activated 95-cell CID-NL Discovery default scope. Held and blocked rows are not review debt hidden behind another slice; they are explicit non-activation buckets.

## Authority Boundary

This classification checker does not change ProductWriter, default matrix, workbook, GUI, selected peak/area, or counted detections. CID-NL/MS2 evidence remains evidence-provider input. Candidate rows are not matrix rows.

## Replay Scope

The `--check-only` path verifies the retained compact summary, checks, and manifest. Source feature-gate output remains externalized; rebuild this contract from that output when source-level parity must be tested.

## Files

- Summary JSON: `docs/superpowers/validation/cid_nl_discovery_full_scope_classification_v1/cid_nl_discovery_full_scope_classification_summary.json`
- Compact manifest: `docs/superpowers/validation/cid_nl_discovery_full_scope_classification_v1/cid_nl_discovery_full_scope_classification_manifest.tsv`
- Checks TSV: `docs/superpowers/validation/cid_nl_discovery_full_scope_classification_v1/cid_nl_discovery_full_scope_classification_checks.tsv`
