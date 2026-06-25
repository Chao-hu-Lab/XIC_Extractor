# Replay Executor Validation Note

Status: `repo_stub_plus_obsidian`
Validation status: `production_ready` for targeted CLI replay parity; not full
exact artifact replay
Original note date: 2026-06-15

This same-path public stub preserves the durable replay validation decision and
referrer compatibility for the historical validation note. The long validation
diary and command transcript were moved to the private Obsidian note
`[[XIC Replay Executor Validation History]]` and read back before this stub was
written. Private vault access is optional and must not be required to understand
the product decision.

## Public Decision

`xic-extractor-cli --replay-manifest` is validated for targeted CLI CSV/workbook
replay parity on the reviewed 8RAW and 85RAW replay surfaces.

Accepted scope:

- the reviewed replay runs were `run_ok` and `gate_ok`;
- CSV replay parity passed for the reviewed 8RAW and 85RAW surfaces.
- Workbook analytical parity passed for the reviewed 8RAW and 85RAW surfaces
  under the normalized workbook comparison contract.
- Replay mode rejects runtime override flags before opening RAW.

Explicit non-claims:

- this is not full byte-exact artifact replay;
- timestamped workbook hash capture remains absent by design for this lane;
- GUI replay parity is not covered;
- this does not alter selected peak, selected area, confidence, reason, counted
  detection, matrix values, existing CSV columns, or workbook sheet order.

## Repo Sources Of Truth

- Current rerun policy and compact replay closeout facts:
  `docs/diagnostic-ledger.md`
- Replay public-surface contract and residual exact-replay blockers:
  `docs/superpowers/specs/2026-06-15-method-manifest-v1-spec.md`
- Current productization tier and active product authority:
  `docs/superpowers/plans/2026-06-15-productization-control-plane.md`
- Machine-checkable productization state:
  `docs/superpowers/validation/productization_status_index_v1.tsv`

## Next Safe Action

Do not rerun replay validation just to re-prove the accepted replay surfaces.
Rerun only after current code changes method-manifest binding, replay CLI
behavior, settings/targets artifact resolution, CSV/workbook writer semantics,
or the cited artifacts become stale or contradictory.

No tracked-file removal is authorized by this stub.
