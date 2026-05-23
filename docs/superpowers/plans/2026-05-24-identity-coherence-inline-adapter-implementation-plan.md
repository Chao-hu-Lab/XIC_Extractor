# Identity Coherence Inline Adapter Roadmap

The original inline-adapter implementation plan was too large to execute safely as one unit. Execute these plans in order instead:

1. `2026-05-24-identity-coherence-inline-adapter-slice1-source-mapping-plan.md`
   - Builds source mapping from `DiscoveryCandidate` + `OwnershipBuildResult` without RAW access.
   - Establishes deterministic request/source IDs and owner assignment handling.
2. `2026-05-24-identity-coherence-inline-adapter-slice2-trace-retrieval-plan.md`
   - Adds serial/process identity trace retrieval.
   - Supports `raw_workers` and `raw_xic_batch_size` as execution policy only.
   - Preserves request order and isolates extraction failures to affected chunks.
3. `2026-05-24-identity-coherence-inline-adapter-slice3-runner-cli-plan.md`
   - Builds diagnostic records and controls evaluation.
   - Wires the opt-in pipeline and CLI flags.
   - Runs final scope guards and prepares real 8RAW follow-on validation.

## Execution Rules

- Do not execute this roadmap directly; execute the slice plans.
- Commit each slice before starting the next one.
- Do not move RAW/XIC retrieval implementation, Backfill, final matrix, workbook, or report responsibilities into the identity-coherence domain package.
- `raw_workers` and `raw_xic_batch_size` may change throughput only. They must not change decisions, row IDs, TSV ordering, or identity evidence semantics.
- Controls remain validation-only. They must not alter identity decisions.

## Follow-On After Slice 3

After all three slices land, write a separate validation plan for real-data serial-vs-process parity on the agreed 8RAW subset with `raw_workers=8` and `raw_xic_batch_size=64`. That validation must treat the output as diagnostic evidence only, not as final Backfill or matrix behavior.
