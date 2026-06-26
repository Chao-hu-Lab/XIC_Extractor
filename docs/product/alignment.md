# Alignment

Document status: product-topic source-of-truth summary.
Evidence label: `diagnostic_only` for this documentation-governance patch; this
page does not change alignment schemas, runner behavior, or product authority.

Alignment is the cross-sample handoff layer. It consumes explicit discovery or
accepted input, builds owners and aligned matrices, and writes machine-readable
contracts for review and downstream product decisions.

This topic file summarizes the durable public contract. It does not grant
ProductWriter authority by itself.

## Answers

Use this page to answer:

- What alignment consumes and writes.
- Which alignment outputs are public machine handoff surfaces.
- Where alignment stops and discovery, output rendering, diagnostics, and
  ProductWriter authority begin.
- Which owner docs to read before changing alignment runner profiles or output
  contracts.

## Does Not Answer

This page does not decide:

- Product activation, writer authority, or accepted Backfill values.
- Discovery seed generation or candidate evidence truth.
- Workbook/HTML rendering behavior.
- Whether a specific RAW tier is production-ready.

## Current Contract

- Alignment inputs must be explicit: accepted target input, discovery batch
  index, or documented local validation input. Do not rely on old worktree
  output paths as durable inputs.
- `validation-minimal` is the standard fast public validation profile for
  alignment behavior unless a stronger gate is explicitly requested.
- Alignment may write matrix, review, identity, evidence, and conditional
  provenance sidecars. Sidecars explain the run and support review; they do not
  become product authority without the authority manifest and expected-diff
  contract.
- Product activation is a separate decision owned by productization control
  plane, status index, authority manifest, and output tests.
- Successor/group identity, gap-fill semantics, and workbook metadata versioning
  are public behavior when they affect alignment outputs. They must stay
  repo-readable through the relevant public-behavior addenda or this topic page.
- `alignment_review.tsv` tokens are review context. Positive support for
  promoted behavior must come from provenance-valid sidecars or explicit
  authority records, not from display tokens alone.
- Alignment output filenames, row ordering, column schema, schema-version
  signals, and identity/provenance sidecars are public contracts. Dated
  implementation plans may move to private history only after those contracts
  remain represented here, in named specs, and in focused tests.
- Runner scripts orchestrate inputs, profiles, and output locations. Reusable
  grouping, ownership, identity, writer, and sidecar behavior belongs in package
  modules or explicit specs, not in branch-local command diaries.

## Public Surfaces

| Output | Role |
| --- | --- |
| `alignment_matrix.tsv` | Cross-sample aligned values |
| `alignment_review.tsv` | Human/machine review summary |
| `alignment_matrix_identity.tsv` | Identity and owner traceability |
| `alignment_backfill_cell_evidence.tsv` | Backfill-related cell evidence sidecar |
| `alignment_run_metadata.json` | Conditional run settings and provenance sidecar when enabled by the runner |
| `alignment-results-v2/v3` metadata | Workbook/report schema-version signals for public behavior changes |

## Ownership Boundaries

| Area | Owns | Does not own |
| --- | --- | --- |
| Alignment | Cross-sample grouping, owner construction, primary consolidation, sidecar emission | Discovery seed creation, workbook rendering, product writer authority |
| Discovery | Candidate generation and per-sample review surfaces | Cross-sample matrix authority |
| Output | Rendering TSV/XLSX/HTML artifacts from domain decisions | Recomputing evidence or selecting authority |
| Diagnostics | Audits and observability | Product behavior unless promoted through public contract |

## Workflow

1. Alignment consumes explicit accepted input, discovery batch index, or
   documented local validation input.
2. The runner applies the requested profile or preset and constructs owners,
   aligned rows, identity sidecars, and review surfaces.
3. `validation-minimal` emits the standard fast machine handoff outputs unless a
   stronger review mode is explicitly requested.
4. Conditional provenance or skipped-evidence sidecars may be emitted by runner
   settings.
5. Product activation, if any, is evaluated separately through the
   productization authority path.

## Verification Gates

Before changing alignment behavior, require the relevant subset of:

- focused tests for changed TSV schemas, row ordering, identity sidecars, or
  owner construction;
- runner/profile smoke check for documented command shapes;
- expected-diff and authority review if matrix values become product-facing;
- downstream consumer check when output filenames or columns change;
- RAW-tier evidence label that matches the claim, such as synthetic, 8RAW, or
  85RAW, without promoting a lower tier as production readiness.

## Common Wrong Moves

- Treating alignment sidecars as ProductWriter authority.
- Using old worktree output paths as durable inputs.
- Changing output columns without updating specs, tests, and downstream
  handoff docs.
- Claiming product readiness from `validation-minimal` alone.
- Treating a gap-filled or successor-group sidecar row as product authority
  without a matching output contract.
- Letting `alignment_review.tsv` support tokens promote rows without
  provenance-valid source sidecars.

## Source Owners

- This file owns durable public Alignment output, matrix-handoff, owner-family,
  and cross-sample behavior. Dated alignment specs are migration/history stubs
  after their stable claims are absorbed here.
- [`docs/architecture-contract.md`](../architecture-contract.md)
- [`docs/agent-parameter-settings.md`](../agent-parameter-settings.md)
- [`docs/agent/product-validation-contract.md`](../agent/product-validation-contract.md)
- [`docs/diagnostic-ledger.md`](../diagnostic-ledger.md)
- [`docs/superpowers/specs/productization_authority_manifest.v1.json`](../superpowers/specs/productization_authority_manifest.v1.json)
- [`docs/superpowers/specs/2026-06-02-cross-sample-peak-group-public-behavior-addendum.md`](../superpowers/specs/2026-06-02-cross-sample-peak-group-public-behavior-addendum.md)
- [`docs/superpowers/specs/2026-06-01-c6-alignment-stage-semantics-value-assessment-design.md`](../superpowers/specs/2026-06-01-c6-alignment-stage-semantics-value-assessment-design.md)

## Cleanup Rule

Alignment plans and closeout notes often contain useful history but should not
remain the only public explanation of matrix handoff behavior. Formalize stable
output contracts, runner profiles, and ownership boundaries here or in the
source owners before moving long history to Obsidian. Same-path stubs can remain
for old sidecar provenance checkpoint refs.

## When To Update

Update this page when alignment gains a durable input rule, output surface,
runner profile, preset interaction, or recurring wrong-move rule. If the change
affects output schema, replay/review behavior, matrix values, or ProductWriter
authority, update the owning spec, tests, and productization owners first.
