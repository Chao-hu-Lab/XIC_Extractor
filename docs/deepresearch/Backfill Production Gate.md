# Backfill Production Gate

Status: `repo_stub_plus_obsidian`
Validation status: `diagnostic_only`

This file is a sanitized repo stub. The long research note was copied to
Obsidian as `[[Backfill Production Gate]]`; this stub preserves the public
decision needed by repo referrers.

## Public Summary

- Absolute `height >= 2e6` is a high-signal demonstrator or rollout guardrail,
  not a universal Backfill product hard gate.
- Low-height evidence should be judged through boundary/reintegration stability,
  local evidence, cohort RT/m/z context, expected-diff evidence, and provenance.
- The low-height heldout observation `19/20 pass + 1 boundary fail` is boundary
  risk evidence. It does not prove low-height cells are globally unusable.
- This note is design input only. It does not promote a writer, matrix rule,
  schema, CLI behavior, workbook output, or productization tier.

## Repo Sources Of Truth

- `docs/superpowers/plans/2026-06-15-productization-control-plane.md` owns the
  current Backfill product tier, writer scope, and explicit note that `height >=
  2e6` is not a product hard gate.
- `docs/lcms-msms-evidence-rules.md` owns durable LC-MS/MS evidence semantics.
- `docs/agent/product-validation-contract.md` owns product-readiness wording and
  public-surface discipline.
- `docs/superpowers/validation/productization_status_index_v1.tsv` and
  `docs/superpowers/specs/productization_authority_manifest.v1.json` own the
  machine-checkable Backfill authority state.

## Optional Private Context

- Obsidian note: `[[Backfill Production Gate]]`
- Status: `readback_verified`
- Contains: literature/research reasoning and long-form gate discussion.

## Next Safe Action

Before changing Backfill write behavior, update the formal owner docs and require
an expected-diff gate. Do not treat this stub or the private note as direct
matrix-writing authority.
