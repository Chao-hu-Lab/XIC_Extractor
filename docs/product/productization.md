# Productization

Document status: product-topic source-of-truth summary.
Evidence label: `diagnostic_only` for this documentation-governance patch; this
page does not change maturity tier, active lane, writer authority, output
schema, review/replay behavior, selected values, selected area/counting, matrix
values, or matrix authority.

This page summarizes the durable current-state and promotion-boundary claims
from the dated current capability inventory in a shorter source-of-truth form.
The historical inventory remains provenance, not the live decision owner.

## Answers

Use this page to answer:

- Which existing XIC capabilities are already public or product-adjacent
  surfaces.
- Which capabilities are only `diagnostic_only`, `shadow_ready`, or
  `production_candidate` and must not silently write product outputs.
- Which owner decides productization tier, writer authority, schema, or
  validation verdict.
- Which promotion steps should happen before adding more reports or sidecars.

## Does Not Answer

This page does not decide:

- Current active lane, WIP limit, or promotion packet acceptance. Use the
  productization control plane.
- ProductWriter scope or accepted cells. Use the authority manifest and status
  index.
- Specific RAW-backed validation verdicts. Use retained validation packets and
  diagnostic ledger entries.
- Implementation details for a future PR. Use the relevant spec and tests.

## Authority Model

| Decision | Authority |
| --- | --- |
| Maturity tier, active lane, WIP owner, promotion packet gate | `docs/superpowers/plans/2026-06-15-productization-control-plane.md` |
| Machine-checkable productization state | `docs/superpowers/validation/productization_status_index_v1.tsv` |
| ProductWriter scope and accepted authority records | `docs/superpowers/specs/productization_authority_manifest.v1.json` |
| Validation retention and externalization | `docs/superpowers/validation/RETENTION.md` and `ARTIFACT_INVENTORY.tsv` |
| Product topic meaning | `docs/product/*.md` topic pages |
| Historical reasoning/provenance | dated reports, plans, specs, and private Obsidian notes |

If a dated report conflicts with this page, the control plane, status index, or
authority manifest, treat the dated report as historical.

## Current Product-Authorized Scopes

The current product-authorized write scopes are exactly:

- `backfill_policy_write_ready_rows`: 511 Backfill cells.
- `cid_nl_adopt_ready_feature_inclusion_95_cells`: 95 CID-NL Discovery cells.
- `backfill_expansion_clean_target_selective_activation_84_cells`: 84
  clean-target selective Backfill expansion cells.

The 666-cell Backfill expansion replay remains `production_candidate` with no
write authority, and broad 4613-row Backfill auto-write remains parked. This
summary mirrors the control plane, status index, and authority manifest; it does
not create a new tier, active lane, writer scope, or output behavior.

## Current Contract Map

| Area | Existing public or product-adjacent surface | Current limit | Promotion gate |
| --- | --- | --- | --- |
| Domain evidence | `EvidenceDecisionSemantics`, `EvidenceVector`, `PeakHypothesis`, `IntegrationResult`, targeted product projection | Not every writer is guaranteed to consume one canonical projection | Freeze/adapt canonical detection contract; do not replace the evidence spine |
| Targeted outputs | CSV/workbook product fields such as `Product State` and `Counted Detection` | Display fields are not the full audit trail | Schema version plus canonical projection adapter |
| Review workflow | `Review Queue`, candidate/boundary sidecars, HTML review report | Review decisions do not yet form a full import/reintegration/audit loop | `ReviewAction` import, recompute, and durable action log |
| Run provenance | `Run Metadata`, `config_hash`, `target_config_hash`, CLI/config loading | Hashes are fragments, not a complete method replay manifest | JSON method manifest with input hashes, settings, sample metadata, CLI args, runtime, and schema versions |
| Sample metadata and QC | injection-order source, ISTD rolling RT prior, instrument-QC sidecars | No first-class shared sample metadata contract for all product runs | `sample_metadata_v1` with QC/blank/calibrator/batch roles and provenance |
| Alignment | `AlignedCell`, `ProductionDecisionSet`, matrix/review/audit workbook and TSVs | Sidecars and validation profiles are not ProductWriter authority | Output-level contract plus expected-diff gate for any matrix-impacting change |
| Backfill | ProductWriter-gated scoped writer paths, authority manifest, expected-diff packets | Candidate/audit universe is not the writer pool; broad auto-write remains parked | Explicit authority contract, expected-diff evidence, and focused output tests |
| Calibration and normalization | calibration previews, QC evidence, activation gates | Shadow/diagnostic evidence must not write the primary matrix | Transfer oracle, blocked-row gate, expected diff, then explicit activation/export contract |
| Reports and diagnostics | HTML reports, TSV sidecars, diagnostic probes | Presentation and observability are not decision authority | Reports must consume canonical decisions; reusable probes belong in `tools/diagnostics/` |
| Mature-tool comparisons | Skyline/MZmine/OpenMS/XCMS comparison notes, smoke reports, expressibility runbooks | They define product floor and differentiators, not implementation authority | Promote only by writing a repo-owned method/contract change with tests and expected diff |
| Skyline expressibility | transition-list probes, smoke manifests, runbooks | Evaluation evidence only; not current export support or product-ready validation | Add explicit export/support contract before treating it as product surface |

## Promotion Priorities

The durable direction is promotion pipeline, not feature rebuild:

1. Preserve and formalize existing evidence/model-selection objects instead of
   rewriting them.
2. Make run replay explicit through method manifests.
3. Turn review worklists into review roundtrip plus audited recomputation.
4. Make sample metadata/QC a first-class contract before activation of
   correction/normalization behavior.
5. Align output-level naming and schema ownership before downstream consumers
   depend on a TSV or workbook change.

## Common Wrong Moves

- Treating `diagnostic_only`, `shadow_ready`, or `production_candidate` outputs
  as if they may write product matrices.
- Reading a dated report as newer authority than the control plane, status
  index, or authority manifest.
- Adding another sidecar/report when the missing piece is replay, schema
  versioning, review import, or activation authority.
- Treating `config_hash` as a full method hash.
- Rebuilding `EvidenceVector`, `PeakHypothesis`, or `IntegrationResult` instead
  of freezing/adapting the existing model.
- Moving a historical report to Obsidian before the stable public claim has a
  repo owner or same-path stub.

## Historical Provenance

This map was distilled from dated capability inventory and promotion-roadmap
work that has moved to private development history. The durable public state is
now this topic page plus the control plane, status index, and authority
manifest listed above.
