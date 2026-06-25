# Gaussian15 MS1 Peak-Group NL Scope Production-Ready Closeout

Status: `repo_stub_plus_obsidian`
Validation status: `production_ready`
Original note date: 2026-06-05

This same-path public stub preserves the durable closeout decision and referrer
compatibility for the historical validation note. The long validation diary and
command transcript were moved to the private Obsidian note
`[[XIC Gaussian15 Peak Group NL Scope History]]` and read back before this stub
was written. Private vault access is optional and must not be required to
understand the product decision.

## Public Decision

Targeted candidate MS2/NL evidence ownership under Gaussian15 MS1 peak-group
scope is `production_ready`.

Selected `chrom_peak_segment` candidates must not borrow active strict NL
support from a different Gaussian15 MS1 peak group. Strict NL scans outside the
selected group remain diagnostic/conflict context for another chromatographic
event, not active support for the current candidate. Repeated DDA/NL triggers
inside one selected Gaussian15 MS1 peak group are one chromatographic support
event with multiple scans; they must not be treated as multiple independent MS1
peak supports.

This closeout does not claim every biological identity is final. Missing
DDA/NL, targeted RT/ISTD conflict, low local quality, and manual EIC/MS2
adjudication remain separate evidence surfaces.

## Repo Sources Of Truth

- Current rerun policy and compact closeout facts:
  `docs/diagnostic-ledger.md`
- Durable MS2/NL and Gaussian15 peak-group evidence semantics:
  `docs/lcms-msms-evidence-rules.md`
- Current productization tier and active product authority:
  `docs/superpowers/plans/2026-06-15-productization-control-plane.md`
- Machine-checkable productization state:
  `docs/superpowers/validation/productization_status_index_v1.tsv`

## Next Safe Action

Do not rerun 85RAW just to re-prove scoped NL ownership behavior. Rerun only
after current code changes targeted candidate MS2/NL evidence ownership, chrom
peak segment selection, candidate-table projection, or the cited artifacts
become stale or contradictory.

No tracked-file removal is authorized by this stub.
