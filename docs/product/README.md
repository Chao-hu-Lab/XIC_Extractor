# Product Topic Index

Document status: canonical product-topic routing index.
Evidence label: `diagnostic_only` for this documentation-governance patch; the
product evidence state remains owned by the control plane, status index, and
authority manifest.

This directory holds compact, public, repo-readable summaries for product
topics that otherwise sprawl across dated plans, specs, validation packets, and
private working notes.

The current first-pass topics are not a complete taxonomy. They are the topics
already known to need representative repo docs during the Obsidian cleanup:

| Topic | Start here | Scope |
| --- | --- | --- |
| Backfill | [`backfill.md`](backfill.md) | ProductWriter authority, accepted quant values, expansion gates, and parked broad autowrite decisions |
| Discovery | [`discovery.md`](discovery.md) | Untargeted feature discovery, candidate/review outputs, and seed evidence handoff |
| Alignment | [`alignment.md`](alignment.md) | Cross-sample alignment outputs, owner construction, backfill evidence sidecars, and matrix handoff contracts |
| Presets | [`presets.md`](presets.md) | Resolver and alignment preset behavior, reproducibility rules, and preset public-surface risk |
| Productization | [`productization.md`](productization.md) | Current-state capability map, promotion boundaries, and authority routing |
| Evidence Spine | [`evidence-spine.md`](evidence-spine.md) | Shared evidence carriers, peak hypotheses, and targeted/untargeted product-projection boundaries |
| Peak Model Selection | [`peak-model-selection.md`](peak-model-selection.md) | Selected-hypothesis model-selection invariants, parity requirements, expected-diff gates, and legacy scoring retirement boundaries |
| Quant Matrix | [`quant-matrix.md`](quant-matrix.md) | Product-facing matrix values, Backfill activation boundaries, sidecars, and matrix authority routing |
| Run Provenance | [`run-provenance.md`](run-provenance.md) | Method manifests, run metadata, replay context, and command-diary cleanup boundaries |
| Review Roundtrip | [`review-roundtrip.md`](review-roundtrip.md) | Review action import, lockbox evidence, expected-diff gates, and private review-rationale boundaries |
| Sample Metadata And QC | [`sample-metadata-qc.md`](sample-metadata-qc.md) | Sample identity/order/role/QC metadata, safe-current-use boundaries, and activation gates |
| Targeted Selection | [`targeted-selection.md`](targeted-selection.md) | Targeted public behavior, selected hypotheses, region/boundary gates, reasons, and target-pair RT activation |
| Quantitation Context | [`quantitation-context.md`](quantitation-context.md) | Bounded trace context for selected peak integration, morphology evidence, and area-impacting gates |
| Instrument QC And Calibration | [`instrument-qc-calibration.md`](instrument-qc-calibration.md) | Clean-vs-biological QC roles, HCD audit limits, calibration readiness, and activation boundaries |

Add another file here when a product topic has durable public rules but no
single small repo entry point. Do not add a topic here just to preserve a branch
diary, implementation transcript, or private review thread.

## Topic Page Contract

Product topic pages are internal public repo docs for developers, reviewers, and
future agents. They are closer to guide/concept pages than end-user tutorials:
they explain what a subsystem means, which surfaces are public, and where the
actual authority lives.

Each product topic page should answer these questions:

| Section | Required question |
| --- | --- |
| Answers | What decisions can a reader settle from this page alone? |
| Does Not Answer | Which decisions still require another authority owner? |
| Current Contract | What durable rules are safe to cite in review or implementation? |
| Public Surfaces | Which packages, CLIs, files, presets, schemas, or outputs are affected? |
| Workflow | What is the normal path from input/candidate to output/decision? |
| Verification Gates | What checks or evidence are needed before changing behavior? |
| Common Wrong Moves | Which recurring mistakes should this page prevent? |
| Source Owners | Which canonical files win if there is a conflict? |
| When To Update | What change requires this topic page, and possibly another owner, to change? |

Do not mark a topic page as product evidence just because it summarizes product
rules. Evidence labels describe what this branch verified; authority owners
describe which artifacts may change product behavior.

## Authority Boundary

These files summarize durable public rules and route readers to the owner docs.
They do not replace:

- Productization control plane:
  [`docs/superpowers/plans/2026-06-15-productization-control-plane.md`](../superpowers/plans/2026-06-15-productization-control-plane.md)
- Machine-checkable product state:
  [`docs/superpowers/validation/productization_status_index_v1.tsv`](../superpowers/validation/productization_status_index_v1.tsv)
- ProductWriter authority manifest:
  [`docs/superpowers/specs/productization_authority_manifest.v1.json`](../superpowers/specs/productization_authority_manifest.v1.json)
- LC-MS/MS evidence rules:
  [`docs/lcms-msms-evidence-rules.md`](../lcms-msms-evidence-rules.md)
- Architecture boundaries:
  [`docs/architecture-contract.md`](../architecture-contract.md)
- Runner and command contracts:
  [`docs/agent-parameter-settings.md`](../agent-parameter-settings.md)

If a topic file conflicts with one of those owners, treat the owner as
authoritative and update this summary.

## Non-Goals

- Do not copy dated plans into this directory.
- Do not include sample-level private investigation detail, local paths, RAW
  layout, or command transcripts.
- Do not change maturity tier, active lane, writer authority, matrix behavior,
  schema, selected area/counting, or validation verdict from this index.
