# Productization Specs

Status: routing index

Specs define contracts, background, or historical designs. They are not
automatic implementation goals.

## Active Reading Order

1. Control plane for authority and maturity state.
2. Current handoff for continuation state.
3. Current roadmap/blueprint for phase order.
4. The specific spec named by the active goal.

## Current Public Schemas

- `production_acceptance_manifest_schema.v1.json`: Phase 2 Backfill
  `ProductionAcceptanceManifest v1` contract. This defines/checks the only
  future Backfill row artifact that may grant `write_authority=true`; it does
  not activate ProductWriter or the default quant matrix.
- `quant_matrix_version_schema.v1.json`: Phase 3 explicit
  `QuantMatrixVersion v1` activation output contract. It defines
  `quant_matrix`, `cell_provenance`, `row_summary`, expected-diff, and source
  summary invariants for manifest-authorized Backfill values; it does not
  change ProductWriter default extraction, workbook, GUI, selected peak/area,
  or counted-detection behavior.
- `quant_matrix_review_report_schema.v1.json`: Phase 4 review-only
  `QuantMatrixVersion` report contract. It defines review rows, summary JSON,
  and HTML report outputs for accepted Backfill versus detected cells,
  prevalence uncertainty, manifest/source hashes, manual-negative closure,
  doublet closure, and Gaussian-smoothed trace-primary/raw-trace-auxiliary
  display; it does not grant ProductWriter or matrix authority.
- `quant_matrix_promotion_readiness_schema.v1.json`: Phase 5 read-only
  promotion readiness contract. It defines readiness summary JSON and checks
  TSV outputs that separate contract correctness from scientific confidence;
  focused tests and 8RAW smoke evidence cannot claim `production_ready` without
  artifact-bound large-cohort, heldout-oracle/manual-review, and
  downstream-impact evidence.
- `quant_matrix_downstream_impact_smoke_schema.v1.json`: Phase 6 no-RAW
  downstream-impact smoke contract. It proves a real `QuantMatrixVersion`
  bundle improves numeric matrix coverage while preserving detected-only claims
  through sidecars; contract fixtures cannot satisfy promotion.
- `quant_matrix_validation_evidence_schema.v1.json`: no-RAW artifact-bound
  evidence packet consumed by Phase 5 promotion readiness. It records copied
  packet artifact paths/hashes, source artifact paths/hashes, tier metadata,
  and missing science evidence while staying read-only with
  `write_authority=false`; downstream-impact rows must validate the artifact
  content, not only a tier string.
- `quant_matrix_real_bundle_schema.v1.json`: Phase 7 real
  `QuantMatrixVersion` bundle schema. It assembles the current standard-peak
  Backfill authority replay into manifest, expected-diff, version, review,
  downstream-impact, and contract-only readiness artifacts while leaving
  ProductWriter defaults, workbook/GUI, selected peak/area, counted detection,
  broad Backfill, and production tier unchanged.
- `quant_matrix_promotion_packet_v2_schema.v1.json`: Phase 8 no-RAW promotion
  packet summary schema. It binds the Phase 7 real bundle, large-cohort
  evidence, heldout-oracle evidence, and real downstream-impact smoke into a
  `production_ready_candidate_packet` while still leaving ProductWriter
  defaults, workbook/GUI, selected peak/area, counted detection, broad Backfill,
  and default matrix authority unchanged.

## Rule

If a spec conflicts with the control plane, current handoff, or current
Backfill quant-matrix product blueprint, stop and resolve the conflict instead
of silently following the older spec.
