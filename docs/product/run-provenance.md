# Run Provenance

Document status: product-topic source-of-truth summary.
Evidence label: `diagnostic_only` for this documentation-governance patch; this
page does not change CLI behavior, replay behavior, output schema, workbook
values, or matrix authority.

Run provenance records enough method and artifact context for a product run to
be reviewed, replayed, or compared without relying on branch-local command
diaries.

## Answers

Use this page to answer:

- Why `config_hash` is not a full method hash.
- Which provenance artifacts are public surfaces.
- What a method manifest should and should not own.
- Which historical command narratives can move to private notes.

## Does Not Answer

This page does not decide:

- Exact replay CLI semantics for every workflow.
- Sample metadata role behavior.
- Review action import or matrix activation authority.
- Current productization tier for method-manifest work.

## Current Contract

- `config_hash` and `target_config_hash` are useful fragments, not a complete
  method manifest.
- A method manifest is an additive run envelope: input artifact hashes, settings
  fragments, runtime/backend, CLI invocation when available, output pointers,
  and schema versions.
- Provenance writers render run context. They must not recompute domain evidence
  or change selected peaks, selected areas, confidence, counted detections,
  workbook values, or matrix values.
- Command diaries are not durable replay contracts. If a run matters, convert
  the stable command shape and artifact contract into a repo owner.

## Public Surfaces

| Surface | Role |
| --- | --- |
| `Run Metadata` workbook sheet | Human-readable run metadata |
| `config_hash` / `target_config_hash` | Configuration and target fragments |
| `method_manifest.json` | Machine-readable run envelope when enabled |
| CLI arguments and runner config | Replay inputs and behavior surface |
| Output schema versions | Contract for produced CSV/TSV/workbook sidecars |

## Workflow

1. A runner receives input artifacts, config, targets, CLI args, and runtime
   context.
2. Domain pipelines produce decisions and outputs.
3. Provenance code records method fragments and output pointers.
4. Replay or audit code validates source artifact hashes before trusting a
   manifest-driven rerun.

## Verification Gates

Before changing run provenance, require the relevant subset of:

- focused manifest serialization and validation tests;
- replay smoke for the documented runner path;
- output-schema tests when schema metadata changes;
- expected-diff framing if product values, selected peaks, areas, counted
  detections, or workbook sheets can change.

## Common Wrong Moves

- Treating a config hash as full method replay.
- Hiding replay-critical command shape only in a branch diary.
- Letting provenance sidecars recompute evidence or decisions.
- Expanding a targeted method-manifest slice into sample metadata, review
  roundtrip, or matrix activation without a separate contract.

## Source Owners

- [`docs/agent-parameter-settings.md`](../agent-parameter-settings.md)
- [`docs/product/sample-metadata-qc.md`](sample-metadata-qc.md)
- [`docs/product/review-roundtrip.md`](review-roundtrip.md)
- [`docs/product/productization.md`](productization.md)
- [`docs/superpowers/specs/2026-06-15-method-manifest-v1-spec.md`](../superpowers/specs/2026-06-15-method-manifest-v1-spec.md)

## Cleanup Rule

Command transcripts and run diaries can move to private notes after the durable
runner shape, artifact inputs, output schema, and provenance fields are
represented here or in runner docs.

## When To Update

Update this page when a new durable provenance artifact, replay mode, run
metadata key family, or method-hash rule becomes public.
