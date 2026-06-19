# Superpowers Fixtures

`docs/superpowers/fixtures/` is the durable fixture surface for agent-supervised
validation work. It is not a generated result dump.

Use this directory for:

- human-reviewed manual oracles;
- expected-diff and activation contracts;
- writer/checker schema fixtures;
- short manifests;
- dated diagnostic-ledger snapshots with source/hash context.

Before adding or changing files here:

1. Add or update the row in `ARTIFACT_INVENTORY.tsv`.
2. Record the current file SHA256, owner scope, consumer/reference, and
   retention decision.
3. Keep generated full outputs in ignored local artifact paths unless they are
   explicitly promoted as a human-reviewed fixture.

Reference files:

- `RETENTION.md` defines allowed retention decisions.
- `ARTIFACT_INVENTORY.tsv` indexes the current tracked fixture surface.
- `diagnostic_ledger_2026_05_28/README.md` explains the frozen dated ledger
  packet.

`ARTIFACT_INVENTORY.tsv` is checked by schema and row coverage; it is excluded
from self-hash checks to avoid checksum churn.
