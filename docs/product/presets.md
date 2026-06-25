# Presets

Document status: product-topic source-of-truth summary.
Evidence label: `diagnostic_only` for this documentation-governance patch; this
page does not change preset behavior, defaults, or product authority.

Presets are explicit bundles of resolver settings, alignment settings, and
post-alignment stages. They are reproducibility surfaces and public behavior
surfaces; they are not product authority by themselves.

## Answers

Use this page to answer:

- Which preset surfaces are public and repeatable.
- Whether a preset can grant matrix-writing authority.
- Which docs and files own resolver or alignment preset behavior.
- What evidence is needed before changing a default or silent preset behavior.

## Does Not Answer

This page does not decide:

- ProductWriter authority or accepted publication scope.
- Exact command recipe for every validation run. Use runner docs and task
  artifacts.
- Release readiness for a preset-backed workflow. Use the control plane,
  status index, authority manifest, and product-ready checkers.

## Current Contract

- Changing a default preset or silent resolver behavior changes public
  behavior. It needs expected-diff framing, focused tests, and relevant evidence.
- The GUI local profile can expose explicit preset buttons. It must not silently
  overwrite user intent.
- Preset runs should be reproducible from documented CLI/config surfaces and
  metadata, not from branch-local command diaries.
- Product publication still requires the productization authority path. A
  preset can enable required sidecars and checkers, but it does not itself
  grant matrix-writing authority.

## Public Surfaces

| Surface | Role |
| --- | --- |
| `xic_extractor/presets/` | Preset loading and code surface |
| `xic_extractor/presets/data/` | Built-in TOML preset resources |
| `scripts/run_alignment.py --preset ...` | CLI path that activates alignment presets |
| Resolver settings in config/GUI | Public behavior surface for peak detection choices |
| Runner metadata and sidecars | Provenance for preset-backed runs |

## Resolver Presets

| Preset | Role |
| --- | --- |
| `legacy_savgol` | Historical resolver behavior and compatibility baseline |
| `local_minimum` | Local-minimum resolver path used by newer validation slices |

Resolver changes should be documented through public settings, focused tests,
and diagnostic-ledger conclusions when they affect expected results.

## Alignment Presets

Alignment preset code lives under `xic_extractor/presets/`; built-in TOML
resources live under `xic_extractor/presets/data/`.

| Preset | Role |
| --- | --- |
| `dna_dr.toml` | DNA dR alignment preset surface |
| `dna_dr_product_ready.toml` | Product-readiness-oriented DNA dR preset surface with stronger checker expectations |

Rules:

- Prefer preset surfaces over hand-written long command recipes for repeatable
  validation.
- Built-in product-facing presets should emit the expected lightweight seed
  audit and `alignment_backfill_cell_evidence.tsv` where required by the runner
  contract.
- Backfill expansion replay is not automatically included in every preset. It
  is enabled only when sample universe, expected-diff, and authority constraints
  match the documented gate.
- Non-standard peaks and candidate-only evidence stay outside automatic
  publication policy unless the authority manifest and product contract say
  otherwise.

## Workflow

1. A user or validation run selects a resolver or alignment preset explicitly.
2. The runner loads built-in TOML resources or documented custom preset input.
3. The preset sets repeatable behavior and may enable sidecars, audits, or
   post-alignment stages.
4. Output and provenance surfaces record the preset-backed run.
5. Product publication, if any, still requires authority manifest and expected
   productization gates.

## Verification Gates

Before changing preset behavior, require the relevant subset of:

- focused tests for preset loading and default selection;
- expected-diff framing for default or silent behavior changes;
- runner smoke check for documented CLI/config surfaces;
- product-ready preset checker when a preset claims product-readiness support;
- productization owner update if preset behavior changes matrix authority,
  selected values, schema, or publication scope.

## Common Wrong Moves

- Treating a preset as ProductWriter authority.
- Replacing documented preset surfaces with branch-local command recipes.
- Silently changing resolver defaults without expected-diff evidence.
- Assuming Backfill expansion replay is included just because a preset is
  product-facing.

## Source Owners

- [`docs/agent-parameter-settings.md`](../agent-parameter-settings.md)
- [`xic_extractor/presets/`](../../xic_extractor/presets/)
- [`xic_extractor/presets/data/`](../../xic_extractor/presets/data/)
- [`docs/superpowers/plans/2026-06-15-productization-control-plane.md`](../superpowers/plans/2026-06-15-productization-control-plane.md)
- [`docs/superpowers/validation/productization_status_index_v1.tsv`](../superpowers/validation/productization_status_index_v1.tsv)
- [`docs/superpowers/specs/productization_authority_manifest.v1.json`](../superpowers/specs/productization_authority_manifest.v1.json)
- [`docs/diagnostic-ledger.md`](../diagnostic-ledger.md)

## Cleanup Rule

Preset calibration diaries, one-off run observations, and branch-specific command
recipes belong in private notes after the stable preset behavior, public command
shape, and validation conclusion are represented here or in the source owners.

## When To Update

Update this page when a built-in preset is added, renamed, retired, or given a
new public behavior guarantee. If the change affects defaults, selected values,
output schema, review/replay behavior, or matrix authority, update runner docs,
tests, and productization owners first.
