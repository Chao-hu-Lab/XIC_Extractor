# Productization

Productization is the capability map and promotion boundary for all XIC product
surfaces. It tracks which capabilities are public, which are diagnostic-only or
shadow-ready, and what steps are needed to promote them. If a dated report
conflicts with this page or the control plane/status index/authority manifest,
treat the dated report as historical.

## Authority Model

| Decision | Authority |
| --- | --- |
| Maturity tier, active lane, WIP owner, promotion packet gate | [Productization control plane](../superpowers/plans/2026-06-15-productization-control-plane.md) |
| Machine-checkable productization state | [Status index](../superpowers/validation/productization_status_index_v1.tsv) |
| ProductWriter scope and accepted authority records | [Authority manifest](../superpowers/schemas/productization_authority_manifest.v1.json) |
| Validation retention and externalization | [RETENTION.md](../superpowers/validation/RETENTION.md) and `ARTIFACT_INVENTORY.tsv` |
| Product topic meaning | `docs/product/*.md` topic pages |
| Historical reasoning/provenance | Dated reports, plans, specs, and private Obsidian notes |

## Current Product-Authorized Scopes

The current product-authorized write scopes are exactly:

- `backfill_policy_write_ready_rows`: 511 Backfill cells.
- `cid_nl_adopt_ready_feature_inclusion_95_cells`: 95 CID-NL Discovery cells.
- `backfill_expansion_clean_target_selective_activation_84_cells`: 84
  clean-target selective Backfill expansion cells.

The 666-cell Backfill expansion replay remains `production_candidate` with no
write authority, and broad 4613-row Backfill auto-write remains parked.

## Current Contract Map

| Area | Existing surface | Current limit | Promotion gate |
| --- | --- | --- | --- |
| Domain evidence | `EvidenceDecisionSemantics`, `EvidenceVector`, `PeakHypothesis`, `IntegrationResult`, targeted product projection | Not every writer consumes one canonical projection | Freeze/adapt canonical detection contract |
| Targeted outputs | CSV/workbook fields (`Product State`, `Counted Detection`) | Display fields are not the full audit trail | Schema version plus canonical projection adapter |
| Review workflow | `Review Queue`, candidate/boundary sidecars, HTML review report | No full import/reintegration/audit loop | `ReviewAction` import, recompute, and durable action log |
| Run provenance | `Run Metadata`, `config_hash`, `target_config_hash`, CLI/config loading | Hashes are fragments, not a complete replay manifest | JSON method manifest with input hashes, settings, sample metadata, CLI args, runtime, schema versions |
| Sample metadata/QC | Injection-order source, ISTD rolling RT prior, instrument-QC sidecars | No shared sample metadata contract for all product runs | `sample_metadata_v1` with QC/blank/calibrator/batch roles and provenance |
| Alignment | `AlignedCell`, `ProductionDecisionSet`, matrix/review/audit TSVs | Sidecars and validation profiles are not ProductWriter authority | Output-level contract plus expected-diff gate |
| Backfill | ProductWriter-gated scoped writer paths, authority manifest, expected-diff packets | Candidate/audit universe is not the writer pool; broad auto-write parked | Explicit authority contract, expected-diff evidence, focused output tests |
| Calibration/normalization | Calibration previews, QC evidence, activation gates | Shadow/diagnostic evidence must not write primary matrix | Transfer oracle, blocked-row gate, expected diff, then activation/export contract |
| Reports/diagnostics | HTML reports, TSV sidecars, diagnostic probes | Presentation and observability are not decision authority | Reports consume canonical decisions; reusable probes go in `tools/diagnostics/` |
| Mature-tool comparisons | Skyline/MZmine/OpenMS/XCMS notes, smoke reports, expressibility runbooks | Define product floor/differentiators, not implementation authority | Repo-owned method/contract change with tests and expected diff |
| Skyline expressibility | Transition-list probes, smoke manifests, runbooks | Evaluation evidence only, not export support | Explicit export/support contract before treating as product surface |

Dated method and literature reports are historical background after their
stable claims are absorbed here, in topic pages, and in
[Untargeted Method](untargeted-method.md). They cannot override the control
plane, status index, authority manifest, or the current owner docs.

## Boundaries

- **Owns**: capability map, maturity tiers, promotion boundaries, authority
  routing between topic pages.
- **Does not own**: current active lane or WIP limit (see control plane),
  ProductWriter scope or accepted cells (see authority manifest and status
  index), specific RAW-backed validation verdicts (see validation packets and
  diagnostic ledger), implementation details for future PRs (see relevant specs
  and tests).

## Promotion Priorities

1. Preserve and formalize existing evidence/model-selection objects instead of
   rewriting them.
2. Make run replay explicit through method manifests.
3. Turn review worklists into review roundtrip plus audited recomputation.
4. Make sample metadata/QC a first-class contract before activating
   correction/normalization behavior.
5. Align output-level naming and schema ownership before downstream consumers
   depend on a TSV or workbook change.

## Pitfalls

- Treating `diagnostic_only`, `shadow_ready`, or `production_candidate` outputs
  as if they may write product matrices.
- Reading a dated report as newer authority than the control plane, status
  index, or authority manifest.
- Adding another sidecar/report when the missing piece is replay, schema
  versioning, review import, or activation authority.
- Treating `config_hash` as a full method hash.
- Rebuilding `EvidenceVector`, `PeakHypothesis`, or `IntegrationResult` instead
  of freezing/adapting the existing model.

## See Also

- [Productization control plane](../superpowers/plans/2026-06-15-productization-control-plane.md)
- [Status index](../superpowers/validation/productization_status_index_v1.tsv)
- [Authority manifest](../superpowers/schemas/productization_authority_manifest.v1.json)
- [Validation retention](../superpowers/validation/RETENTION.md)
- [Untargeted Method](untargeted-method.md)
