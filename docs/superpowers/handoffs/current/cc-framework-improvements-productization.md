# XIC productization handoff

Updated: 2026-06-19 21:16 +08:00
Branch: `cc/framework-improvements`

This is the compact current-state snapshot. Tier authority remains in
`docs/superpowers/plans/2026-06-15-productization-control-plane.md`.

## Current Verdict

The default numeric matrix is usable for downstream analysis as the current
detected + 511 accepted-Backfill product output. The latest retention and
fixture cleanup did not change ProductWriter behavior, matrix values,
workbook/GUI behavior, selected peak/area, counted detection, default
extraction, scorer behavior, or Backfill authority.

The `d4-N6-2HE-dA` monoisotopic `300.1605 -> 184.113` absence was traced to
Discovery row creation and that Discovery generation path is fixed. The already
activated default matrix bundle still predates that fix, so do not claim the
activated `quant_matrix.tsv` contains that exact target row until a later
discovery/alignment/default-activation expected-diff rerun regenerates it.

Validation status for the current cleanup and retention reuse refactor:
`diagnostic_only`.

## Active References

- Control plane:
  `docs/superpowers/plans/2026-06-15-productization-control-plane.md`
- Validation retention policy/inventory:
  `docs/superpowers/validation/RETENTION.md`,
  `docs/superpowers/validation/ARTIFACT_INVENTORY.tsv`
- Fixture retention policy/inventory:
  `docs/superpowers/fixtures/RETENTION.md`,
  `docs/superpowers/fixtures/ARTIFACT_INVENTORY.tsv`
- Validation retention checker:
  `scripts/check_validation_artifact_retention.py`
- Fixture retention checker:
  `scripts/check_superpowers_fixture_retention.py`
- Shared retention mechanics:
  `xic_extractor/artifact_retention.py`,
  `xic_extractor/alignment/quant_matrix_artifacts.py`,
  `docs/superpowers/notes/2026-06-19-retention-reuse-duplication-ledger.md`
- Default matrix activation bundle:
  `docs/superpowers/validation/quant_matrix_default_product_activation_v1/`
- Externalized local validation artifacts:
  `local_validation_artifacts/externalized_superpowers_validation/`

## Product State

- Current tier: `product_ready_default_matrix_activated`.
- Product authority scope: `backfill_policy_write_ready_rows`.
- Current Backfill writer authority: exactly 511 accepted Backfill cells.
- Broad 4613-row Backfill remains parked.
- ProductWriter default matrix output is activated for detected values plus the
  current 511 accepted Backfill values.
- Large QuantMatrix provenance/review TSV validation dumps are no longer part
  of the tracked contract surface; they have tracked summary/hash/minimal
  fixture replacements and ignored local replay copies.
- The retention cleanup changes docs/artifact storage policy and metadata gates
  only. It does not alter product tier or write authority.
- The retention/QuantMatrix artifact reuse refactors deepen checker and
  JSON/path/hash/bundle replay mechanics only. They do not change maturity
  tier, active lane, matrix output, review authority, selected area/counting,
  or Backfill writer authority. No control-plane tier update is needed.

Status-index handoff anchors retained for the fail-closed checker: `product_ready_default_matrix_activated`; Broad Backfill auto-write remains parked; Goal 0/1 hardening added; machine-adjudicated without granting new writer authority; Goal 2 added Review Packet / Approval Workflow v1; lockbox_shadow_automation_experiment_v1; Goal 4 added Missing-Overlay Evidence Recovery v1; keep only as explanation/triage; Targeted MS1 shape identity limited rescue remains production-ready; GUI and broader targets remain blocked; `sample_metadata_v1` remains production-ready for no-output ordering; roles/batch/matrix/exclusion must not alter quant output; ReviewAction selected-candidate switch and manual-boundary area recompute remain parked; classification and planning only.
Do not reinterpret diagnostic/lockbox/review-packet surfaces as product
authority from this handoff alone.

## Validation Retention

`docs/superpowers/validation/RETENTION.md` defines which validation artifacts
belong in git. The current inventory has 304 rows:

- 126 `keep_contract`
- 39 `keep_summary`
- 4 `keep_minimal_fixture`
- 135 `externalize`

The validation surface now has 169 retained files and 0 `shrink_later` rows.
Three full QuantMatrix TSV dumps were externalized to ignored local storage:

- `quant_matrix_real_bundle_v1/quant_matrix_version/cell_provenance.tsv`
- `quant_matrix_real_bundle_v1/review/quant_matrix_review_rows.tsv`
- `quant_matrix_default_product_activation_v1/default_output/cell_provenance.tsv`

Tracked replacements are summary JSON files plus minimal fixtures. Contract
indexes, status files, source hashes, and checker inputs remain in git.
Rendered review HTML/PNG, QuantMatrix review HTML, duplicated
promotion-packet downstream input copies, and full provenance/review TSV dumps
are local replay artifacts, not durable version-controlled product contracts.
Clean checkout validation still reruns temporary QuantMatrix activation and
compares fresh `cell_provenance.tsv` hashes against tracked summary
`source_sha256` values before accepting externalized full TSVs.
The validation checker now reuses `xic_extractor.artifact_retention` for shared
policy/inventory/git/path mechanics; validation-specific rendered-reference and
externalized-local rules remain local.
QuantMatrix productization scripts now reuse
`xic_extractor.alignment.quant_matrix_artifacts` for bundle-relative artifact
resolution, source-summary hash checks, and `cell_provenance` rerun hash
binding. Promotion packet v2 build/check-only now materializes missing
externalized `cell_provenance.tsv` from tracked full TSV, a SHA-checked
externalized local copy, or a no-RAW activation replay. Durable summaries keep
bundle/reference paths; temp replay paths are not written into retained
artifacts.

Remaining validation work: keep future generated outputs out of
`docs/superpowers/validation` unless they are contract/index/hash/summary or
minimal fixture files.

## Fixture Retention

`docs/superpowers/fixtures/RETENTION.md` defines the canonical fixture-retention
policy. `docs/superpowers/fixtures/ARTIFACT_INVENTORY.tsv` inventories 28
retained fixture files, excluding the inventory file itself to avoid self-hash
churn:

- 4 `keep_contract`
- 3 `keep_manual_oracle`
- 1 `keep_manifest`
- 12 `keep_ledger_snapshot`
- 3 `keep_summary`
- 1 `needs_human_review`
- 4 `archive_later`

Active fixture paths remain stable. The dated packet
`docs/superpowers/fixtures/diagnostic_ledger_2026_05_28/README.md` records two
duplicate snapshot groups and historical hash-drift observations without
rewriting ledger conclusions.
The fixture checker now reuses `xic_extractor.artifact_retention` for shared
policy/inventory/git/path/metadata mechanics; fixture-specific authority,
ledger, and human-review rules remain local.

Remaining fixture work: resolve
`chrom_peak_segment_presence_review_manual_oracle_v1.tsv` as either an active
manual oracle with consumer coverage or an archived note-only oracle.

## Boundaries

- No RAW or 85RAW run was launched for this cleanup.
- No scorer was run.
- No ProductWriter/default extraction/workbook/GUI run was launched.
- No workbook/GUI/default extraction behavior changed.
- No current 511-cell writer authority or broad Backfill authority changed.
- Do not demote/delete the `301.165` isotope row.
- Externalized full QuantMatrix TSVs are local replay/audit copies only; clean
  checkout validation uses tracked summary/minimal fixture contracts.
- `docs/superpowers/fixtures/ARTIFACT_INVENTORY.tsv` metadata for three
  markdown policy/summary files was aligned to current working-tree bytes only.

## Verification

Fixture retention closeout passed: checker accepted 28 retained files with the
known `needs_human_review` warning, focused consumer pytest passed, and scoped
ruff passed.

Current validation retention closeout passed:

- retention checker passed with `169` retained validation files, `135`
  externalized artifacts, and `0` `shrink_later` rows
- strict retention checker with local externalized copies passed
- QuantMatrix real bundle, promotion packet v2, dry-run, closeout, and default
  activation check-only gates pass without RAW
- focused QuantMatrix retention/replay pytest: `49 passed`
- focused validation + fixture retention pytest: `21 passed`
- scoped ruff for validation retention checker/tests passed
- fixture consumer shard passed: `59 passed`

Retention reuse refactor smoke passed:

- focused ruff for `artifact_retention`, both retention checkers, and tests
- `tests/test_artifact_retention.py`,
  `tests/test_validation_artifact_retention.py`,
  `tests/test_superpowers_fixture_retention.py`: `27 passed`
- `uv run mypy xic_extractor`: passed
- `uv run python .codex/hooks/fixtures/assert_hook_outputs.py`: passed
- `git diff --check`: no whitespace errors; Windows line-ending warnings only
- secret/local-path scan over changed files: no matches
- QuantMatrix artifact reuse focused tests passed:
  `tests/test_quant_matrix_artifacts.py` plus default dry-run, promotion packet
  v2, product-ready closeout, and default product activation tests: `35 passed`
- Full pytest was attempted and stopped at unrelated stale candidate-id fixture:
  `tests/test_alignment_identity_coherence_pipeline.py::test_run_alignment_emits_identity_coherence_diagnostic_when_opted_in`.

## Next Actions

1. Commit the artifact reuse refactor if the diff is accepted.
2. Resolve the chrom-peak-segment manual oracle as active fixture or archive.
3. Deepen the next duplicated seam only when a third caller needs the same
   phase-local replay orchestration or schema-check mechanics.
4. Open a separate regeneration goal when the product matrix should materialize
   the `300.1605` target row.
