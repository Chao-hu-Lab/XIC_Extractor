# Superpowers Fixture Retention Policy

Status: living policy for `docs/superpowers/fixtures`.
Scope: durable fixtures, manual oracles, expected-diff contracts, schema
fixtures, short manifests, and dated diagnostic-ledger snapshots.

## Keep In Git

- Manual oracle rows reviewed by a human.
- Expected-diff, activation, and mode-window contracts consumed by tools,
  tests, specs, or validation artifacts.
- Schema fixtures that lock writer/checker columns.
- Dated diagnostic-ledger snapshots that are referenced by
  `docs/diagnostic-ledger.md` or a dated packet README.
- Small manifests and README files that explain a fixture group.

## Do Not Add By Default

- Full generated output dumps that are not human-reviewed fixtures.
- Recomputed diagnostic outputs without a ledger note, source command, or hash.
- Duplicate copies when a source fixture plus summary is enough.
- Result files that belong under ignored local output or
  `local_validation_artifacts/`.

## Decisions

| Decision | Meaning |
| --- | --- |
| `keep_contract` | Active schema, expected-diff, activation, or mode-window contract consumed by tools/tests/specs. |
| `keep_manual_oracle` | Human-reviewed oracle or manual negative fixture that must remain stable for review and validation. |
| `keep_manifest` | Short manifest or lock file. |
| `keep_ledger_snapshot` | Dated diagnostic-ledger evidence snapshot with a source/hash story. |
| `keep_summary` | Short summary, README, or policy file explaining a fixture group. |
| `needs_human_review` | Temporary keep for a manual-looking fixture that lacks a direct checker/test consumer or clear owner decision. |
| `archive_later` | Temporary keep that needs later move/summary after references, duplicate state, or hash drift is resolved. |
| `externalize` | Full generated dump should live outside the tracked fixture surface. |
| `remove_generated` | Reproducible, unreferenced generated file that is not a human oracle or ledger snapshot. |

## Product Boundary

Fixture retention cleanup must not change ProductWriter behavior, selected
peak/area, counted detections, workbook/GUI behavior, Backfill authority,
matrix values, output schemas, or maturity tier claims.
