# Lockbox Static Review Bundle

Status: rendered review artifact externalized from git.

Tracked in this directory:

- `bundle_index.tsv`: the contract/index used by label-import and challenge-pack
  scripts.
- this README.

Not tracked after retention cleanup:

- `index.html`
- `cases/*.html`
- `plots/*.png`

Local copies are moved under:

```text
local_validation_artifacts/externalized_superpowers_validation/lockbox_static_review_v1/
```

Regenerate with:

```powershell
uv run python scripts/build_lockbox_static_review_bundle.py
```

This bundle is a human visual-review surface only. It does not grant product
authority, matrix writes, workbook changes, selected peak/area changes, counted
detection changes, GUI changes, or Backfill authority.
