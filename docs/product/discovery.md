# Discovery

Discovery is the untargeted feature-discovery lane. It turns seed evidence and
MS1 traces into reviewable candidates. It does not directly publish product
matrices; publication requires the separate Backfill/ProductWriter authority
path.

## Contract

- Discovery produces candidate and review surfaces, not final product authority.
- Seed evidence can include MS2 neutral loss, precursor inference, MS1 trace
  support, and future evidence providers.
- Standard per-sample outputs: `discovery_candidates.csv` (archival/alignment
  detail) and `discovery_review.csv` (compact human review).
- Discovery `feature_family_id` remains a public output header and dataclass
  field, but its Discovery meaning is a per-sample peak anchor label for
  candidates sharing the same discovered MS1 peak. It must not be treated as
  cross-sample identity, selected-peak truth, or Backfill promotion authority by
  itself.
- The peak-anchor schema migration intentionally removed legacy
  `family_context`, `feature_superfamily_id`, `feature_superfamily_size`,
  `feature_superfamily_role`, `feature_superfamily_confidence`, and
  `feature_superfamily_evidence` columns from `discovery_candidates.csv` and
  `discovery_review.csv`. There is no compatibility adapter for those columns;
  downstream consumers must read the current column constants or tolerate the
  missing legacy fields.
- Batch discovery handoff uses explicit index files. Do not depend on old
  worktree-local output directories as durable inputs.
- Minimal output modes are for fast inspection; standard outputs are the public
  machine handoff surfaces.
- Discovery UX and review surfaces are public handoffs when they define
  filenames, columns, row identity, output level, or downstream consumption.
- CID-NL Discovery is a bounded accepted slice, separate from Backfill. Future
  expansion needs successor-level tag context, MS1/quant support, provenance,
  value-delta framing, expected matrix effect, and explicit expected-diff review.
- Do not introduce vendor RAW-to-mzML conversion as an implicit product
  dependency without a separate public contract.

## Surfaces

| Surface | Role |
| --- | --- |
| `xic_extractor/discovery/` | Discovery domain package |
| `scripts/run_discovery.py` | Discovery CLI entry point |
| `discovery_candidates.csv` | Detailed candidate table for archival or downstream handoff |
| `discovery_review.csv` | Compact review table |
| `discovery_batch_index.csv` | Batch handoff index for downstream alignment |

## Boundaries

- **Owns**: candidate generation, per-sample review surfaces, seed evidence
  handoff, batch index for downstream alignment.
- **Does not own**: ProductWriter authority or Backfill promotion (see
  [backfill.md](backfill.md)), final evidence truth for a candidate feature
  (see [evidence rules](../lcms-msms-evidence-rules.md)), or release-slice
  readiness (see [productization.md](productization.md)).
- A Discovery slice must use Discovery vocabulary and authority; it must not
  reopen broad Backfill or expand the Backfill authority manifest by accident.

## Verification

Before changing discovery behavior, require the relevant subset of:

- Schema or snapshot tests for candidate, review, and batch-index outputs.
- Focused tests for seed evidence and MS1 trace handoff behavior.
- Performance/output-level review if a minimal or standard mode changes.
- Evidence-rule review if a new evidence provider changes candidate meaning.
- Downstream alignment handoff check when filenames or columns change.
  `tests/test_discovery_csv.py` and `tests/test_discovery_review_csv.py` own the
  current peak-anchor output schema.

## Pitfalls

- Treating `discovery_review.csv` as a product matrix.
- Treating discovery family membership, evidence tier, or review priority as a
  ProductWriter decision.
- Depending on old worktree output directories instead of explicit batch index.
- Hiding discovery output-contract changes in dated implementation notes.
- Treating a new evidence provider as ProductWriter authority without Backfill
  activation.
- Dragging CID-NL Discovery decisions into the Backfill lane.
- Starting untargeted performance work before timing/locality evidence
  identifies the bottleneck and correctness gate.

## See Also

- [Architecture contract](../architecture-contract.md) -- package ownership and
  dependency direction
- [Alignment](alignment.md) -- cross-sample handoff boundary
- [Peak anchor and group boundary](family-hypothesis-boundary.md) -- Discovery
  peak anchors, cross-sample groups, and PeakHypothesis authority
- [Evidence rules](../lcms-msms-evidence-rules.md) -- evidence semantics
- [CID-NL Discovery roadmap](../superpowers/plans/2026-06-21-cid-nl-discovery-product-roadmap.md) -- product lane boundary
- [Untargeted performance spec](../superpowers/specs/2026-05-12-untargeted-performance-architecture-spec.md) -- RAW-locality and request-batching direction
