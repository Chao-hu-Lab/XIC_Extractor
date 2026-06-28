# Run Provenance

Run provenance records method and artifact context so a product run can be
reviewed, replayed, or compared without relying on branch-local command
diaries.

## Contract

- `config_hash` and `target_config_hash` are useful configuration fragments,
  not a complete method manifest. Do not treat them as full method replay.
- A method manifest is an additive run envelope: input artifact hashes,
  settings fragments, runtime/backend, CLI invocation when available, output
  pointers, and schema versions.
- Provenance writers render run context only. They must not recompute domain
  evidence or change selected peaks, areas, confidence, counted detections,
  workbook values, or matrix values.
- Command diaries are not durable replay contracts. If a run matters, convert
  the stable command shape and artifact contract into a repo owner.

## Surfaces

| Surface | Role |
| --- | --- |
| `Run Metadata` workbook sheet | Human-readable run metadata |
| `config_hash` / `target_config_hash` | Configuration and target fragments |
| `method_manifest.json` | Machine-readable run envelope when enabled |
| CLI arguments and runner config | Replay inputs and behavior surface |
| Output schema versions | Contract for produced CSV/TSV/workbook sidecars |

## Boundaries

- Owns: method manifest structure, run metadata keys, config hashes, output
  schema version tracking, and replay artifact validation.
- Does not own: exact replay CLI semantics for every workflow, sample metadata
  role behavior, review action import, matrix activation authority, or
  productization tier decisions.
- Expanding a targeted method-manifest slice into sample metadata, review
  roundtrip, or matrix activation requires a separate contract.

## Verification

- Manifest serialization and validation tests.
- Replay smoke for documented runner paths.
- Output-schema tests when schema metadata changes.
- Expected-diff framing if product values, selected peaks, areas, counted
  detections, or workbook sheets can change.

## Pitfalls

- Treating a config hash as full method replay.
- Hiding replay-critical command shape only in a branch diary.
- Letting provenance sidecars recompute evidence or decisions.

## See Also

- [Agent parameter settings](../agent-parameter-settings.md)
- [Sample metadata and QC](sample-metadata-qc.md)
- [Review roundtrip](review-roundtrip.md)
- [Productization](productization.md)
- [Method manifest v1 spec](../superpowers/specs/2026-06-15-method-manifest-v1-spec.md)
