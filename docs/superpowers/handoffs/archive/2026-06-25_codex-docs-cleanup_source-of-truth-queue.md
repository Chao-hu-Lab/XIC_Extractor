# Repo Source-Of-Truth Queue

Status: review/control artifact.
Validation status: `diagnostic_only`.

This queue lists only documents or themes that must stay readable in the repo,
or that need an independent source-of-truth summary before private migration.
It intentionally omits files that can move directly to Obsidian as private
history.

No row authorizes moving, deleting, or `git rm`-ing source files.

## Newly Formalized Topic Owners

These product-topic pages now exist and should be the first repo-readable entry
point for their theme:

| Topic | Repo owner | Historical inputs absorbed |
| --- | --- | --- |
| Evidence Spine | `docs/product/evidence-spine.md` | shared targeted/untargeted peak identity specs and evidence-provider debates |
| Quant Matrix | `docs/product/quant-matrix.md` | final matrix, accepted Backfill, activation, sidecar, and matrix-authority contracts |
| Run Provenance | `docs/product/run-provenance.md` | method manifest, run metadata, replay, and command-diary cleanup rules |
| Review Roundtrip | `docs/product/review-roundtrip.md` | review actions, lockbox truth labels, expected-diff, and private review-rationale boundaries |
| Sample Metadata And QC | `docs/product/sample-metadata-qc.md` | sample metadata schema, injection-order parity, role/QC boundaries, and activation gates |
| Targeted Selection | `docs/product/targeted-selection.md` | targeted public behavior, selected hypotheses, boundary gates, reasons, and target-pair RT activation |
| Quantitation Context | `docs/product/quantitation-context.md` | bounded selected-peak trace context, morphology evidence, and area-impacting gates |
| Instrument QC And Calibration | `docs/product/instrument-qc-calibration.md` | clean-vs-biological QC roles, HCD audit limits, calibration no-go gates, and activation boundaries |

Existing product-topic owners remain:

- `docs/product/backfill.md`
- `docs/product/discovery.md`
- `docs/product/alignment.md`
- `docs/product/presets.md`
- `docs/product/productization.md`

## Must Stay In Repo For Now

These are not private-only history. They either remain active routing surfaces,
machine-checkable authority surfaces, or exact evidence refs from the control
plane.

| Source | Decision | Repo owner |
| --- | --- | --- |
| `docs/superpowers/plans/2026-06-15-productization-control-plane.md` | keep current path | active tier/lane/productization authority |
| `docs/superpowers/plans/README.md` | keep current path | plans routing index |
| `docs/superpowers/specs/README.md` | keep current path | specs/schema routing index |
| `docs/superpowers/plans/2026-06-19-backfill-quant-matrix-product-blueprint.md` | keep current path | Backfill and quant-matrix active roadmap |
| `docs/superpowers/specs/2026-06-15-method-manifest-v1-spec.md` | keep current path | `docs/product/run-provenance.md` plus control-plane evidence refs |
| `docs/superpowers/specs/2026-06-15-review-roundtrip-v1-spec.md` | keep current path | `docs/product/review-roundtrip.md` plus control-plane evidence refs |
| `docs/superpowers/specs/2026-06-15-sample-metadata-contract-v1-spec.md` | keep current path | `docs/product/sample-metadata-qc.md` plus control-plane evidence refs |
| `docs/superpowers/specs/2026-06-03-full-untarget-peak-hypothesis-final-matrix-contract.md` | keep current path | `docs/product/quant-matrix.md`, `docs/product/alignment.md`, `docs/product/evidence-spine.md` |
| `docs/superpowers/specs/peak_choice_truth_protocol.v1.md` | keep current path | `docs/product/review-roundtrip.md` and validation retention owners |
| `docs/superpowers/plans/2026-06-21-cid-nl-discovery-product-roadmap.md` | keep current path | current CID-NL Discovery lane boundary, summarized by `docs/product/discovery.md` |
| `docs/superpowers/notes/2026-05-28-pr70-alignment-matrix-handoff-raw-validation-note.md` | keep current path | retained PR70 matrix-handoff validation oracle |
| `docs/superpowers/notes/2026-05-19-seed-aware-backfill-review-index.md` | keep current path | compact seed-aware Backfill review index; shadow gate, not matrix authority |
| targeted public-behavior addenda | keep current paths | targeted selection/region/selected-hypothesis/RT activation public behavior |
| alignment public-behavior addenda | keep current paths | successor group identity, gap-fill semantics, alignment schema/versioning |
| Backfill integration policy spec | keep current path | seed guard, area-policy states, write-authority status |
| lockbox machine-readable artifacts | keep current paths unless checker-aware migration happens | checker/public-review artifacts, not private rationale |

## Needs Same-Path Stub Before Private Migration

These have stable public claims now represented elsewhere, but exact referrers
or privacy-sensitive historical detail mean the old path cannot simply vanish.

Completed stub batches are recorded in
`docs/superpowers/handoffs/archive/2026-06-25_codex-docs-cleanup_phase2-stub-readiness.md`.
The 52-file bulk private-history batch is indexed separately in
`docs/superpowers/handoffs/archive/2026-06-25_codex-docs-cleanup_bulk-private-history-stub-batch.md`.
The remaining 104 eligible notes/plans are indexed in
`docs/superpowers/handoffs/archive/2026-06-25_codex-docs-cleanup_remaining-notes-plans-stub-batch.md`.
Do not reprocess completed rows unless their formal owner docs need a new
source-of-truth correction.

| Source | Public owner | Why stub first |
| --- | --- | --- |
| `docs/superpowers/specs/2026-06-16-shared-target-untarget-peak-identity-spine-spec.md` | `docs/product/evidence-spine.md`; `docs/lcms-msms-evidence-rules.md` | control-plane evidence refs remain; detailed debug narrative should not be the public source of truth |
| `docs/superpowers/specs/2026-06-02-asls-primary-matrix-value-policy-spec.md` | `docs/lcms-msms-evidence-rules.md`; `docs/product/quant-matrix.md` | superseded historical policy still has companion refs; current area owner lives elsewhere |
| Deepresearch Backfill/resolver/mature-tool notes from Batch 1 | `docs/product/backfill.md`; `docs/product/presets.md`; `docs/product/productization.md` | deepresearch index and cleanup maps still cite exact paths |
| Skyline comparator run cluster from Batch 1 | `docs/product/productization.md` | runbook/smoke notes cite each other; keep sanitized stubs until consolidated |
| superseded Backfill/productization plan chain from 2026-06-05 to 2026-06-09 | `docs/product/backfill.md`; `docs/product/quant-matrix.md`; active specs | diagnostics index and goal/plan provenance still cite exact paths |
| `2026-06-18-backfill-evidence-lifecycle-blueprint.md` | `docs/product/backfill.md`; `docs/product/quant-matrix.md`; 2026-06-19 blueprint | superseded but contains durable lifecycle vocabulary now topic-owned |
| `2026-06-23-row-completion-confidence-benchmark-implementation-plan.md` | row-completion benchmark spec; `docs/product/quant-matrix.md` | implementation plan still cited by diagnostics index |
| handoff/productization closeout notes from 2026-05-27 to 2026-05-28 | `docs/product/productization.md`; `docs/product/run-provenance.md`; `docs/product/evidence-spine.md` | exact refs remain, but long closeout/rationale belongs in private history |
| Instrument QC notes from 2026-05-20 to 2026-05-21 | `docs/product/instrument-qc-calibration.md` | durable QC/calibration rules are topic-owned; detailed run context is private/history |
| owner quantitation context 8RAW closeout | `docs/product/quantitation-context.md`; `docs/product/quant-matrix.md` | stable bounded-context rule is topic-owned; sample-level detail needs privacy handling |
| Tier 2 sidecar provenance gate note | `docs/product/backfill.md`; `docs/product/alignment.md`; `docs/product/run-provenance.md` | provenance-valid sidecar gate is topic-owned; checkpoint note can shrink |
| superseded final-matrix identity specs from 2026-05-13 to 2026-05-14 | `docs/product/quant-matrix.md`; current final-matrix contract | older row-identity direction is superseded but exact refs remain |
| peak-pipeline cleanup/modernization overviews | targeted/quantitation/productization topic owners | dated sequencing contains private/local-path risk and needs sanitized stubs |

## Validation Artifact Owner Corrections

Validation, fixture, and lockbox rows should not use generic retention policy as
their only owner.

- `RETENTION.md` owns retention policy, not every validation family.
- `ARTIFACT_INVENTORY.tsv` owns the inventory, not the scientific or checker
  meaning of each bundle.
- retained validation families need family-level owners such as their own
  README, summary, manifest, or checks bundle.
- externalized full dumps must point back to the retained tracked artifact that
  replaces them in a clean checkout.
- checker-backed lockbox queues, templates, logs, public review packets, schemas,
  and label summaries stay repo-readable; private reviewer rationale can move to
  Obsidian.

## Remaining Work To Tell The User About

Only report later batches that reveal one of these outcomes:

- a new product topic is needed under `docs/product/`;
- an old spec/plan must stay repo-readable because it still owns public
  behavior, schema, authority, or current routing;
- a same-path stub is required because repo referrers remain;
- a validation artifact must remain repo-retained or checker-readable.

Do not report files that are merely private history, command narrative,
branch diary, or exploratory rationale after their public claims are already
owned by the repo.
