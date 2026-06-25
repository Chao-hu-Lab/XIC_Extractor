# Gaussian15 MS1 Morphology Production-Ready Closeout

Status: `repo_stub_plus_obsidian`
Validation status: `production_ready`
Original note date: 2026-06-05

This same-path public stub preserves the durable closeout decision and referrer
compatibility for the historical validation note. The long validation diary and
command transcript were moved to the private Obsidian note
`[[XIC Gaussian15 MS1 Morphology Closeout History]]` and read back before this
stub was written. Private vault access is optional and must not be required to
understand the product decision.

## Public Decision

The Gaussian15 MS1 morphology ownership transition is `production_ready`.

Active product-facing primary matrix area now requires typed
`primary_matrix_area_source=gaussian15_positive_asls_residual`. Historical
`asls_baseline_corrected` area remains compatibility/debug evidence only and
must not write product area. Missing typed morphology facts fail closed as
`missing_ms1_morphology_area`.

This closeout does not claim every matrix identity is biologically final. MS2/NL
opportunity, RT/ISTD context, duplicate claims, rescue-heavy rows, and manual
EIC/MS2 adjudication remain separate identity-quality surfaces.

## Repo Sources Of Truth

- Current rerun policy and compact closeout facts:
  `docs/diagnostic-ledger.md`
- Durable Gaussian15 morphology and area-owner semantics:
  `docs/lcms-msms-evidence-rules.md`
- Current productization tier and active product authority:
  `docs/superpowers/plans/2026-06-15-productization-control-plane.md`
- Machine-checkable productization state:
  `docs/superpowers/validation/productization_status_index_v1.tsv`

## Next Safe Action

Do not rerun 85RAW just to re-prove ASLS fallback retirement. Rerun only after a
new production behavior change, a new target/default validation contract, or a
current artifact contradicts the closeout facts in `docs/diagnostic-ledger.md`.

No tracked-file removal is authorized by this stub.
