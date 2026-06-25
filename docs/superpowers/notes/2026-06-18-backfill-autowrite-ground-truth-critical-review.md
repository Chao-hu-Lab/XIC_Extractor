# Backfill Auto-Write Ground-Truth Critical Review

Status: `repo_stub_plus_obsidian`
Validation status: `diagnostic_only`
Original note date: 2026-06-18

This same-path public stub preserves the durable strategy decision and referrer
compatibility for the historical critical review. The long critique and
strategy-formation detail were moved to the private Obsidian note
`[[XIC Backfill Autowrite Ground Truth Critical Review]]` and read back before
this stub was written. Private vault access is optional and must not be required
to understand the product decision.

## Public Decision

Broad Backfill auto-write must remain on implementation hold. The current
decision is not to convert the 4613 candidate/audit rows into writable cells.

The stable product rule is:

- mechanically adjudicate candidate rows before any write;
- keep ProductWriter as the only matrix-writing authority;
- write only rows with explicit `write_ready` authority and expected-diff pass;
- keep current Backfill writer authority at the approved 511-cell scope unless
  a future expected-diff-backed authority update says otherwise;
- treat the 3015 trace-matched unresolved rows as truth/review/adjudication
  targets, not an auto-write pool;
- keep the 1087 `missing_overlay_path` rows blocked until trace evidence exists;
- do not derive writer predicates from `quality_blockers` or the round-trip
  reintegration oracle.

The later `backfill_broad_autowrite_feasibility_gate_v1` decision packet closes
this branch as `park_broad_backfill`. Reopen broad Backfill only with a genuinely
new independent evidence source for peak-choice / family identity plus an
expected-diff-backed authority contract.

## Repo Sources Of Truth

- Current Backfill tier, active lane, and writer authority:
  `docs/superpowers/plans/2026-06-15-productization-control-plane.md`
- Machine-checkable parked broad-autowrite state:
  `docs/superpowers/validation/productization_status_index_v1.tsv`
- ProductWriter authority manifest:
  `docs/superpowers/specs/productization_authority_manifest.v1.json`
- Mechanical adjudication schema and index:
  `docs/superpowers/specs/mechanical_adjudication_schema.v1.json`
  and `docs/superpowers/validation/mechanical_adjudication_index_v1.tsv`
- Current parked-lane decision packet:
  `docs/superpowers/notes/backfill_broad_autowrite_feasibility_gate_v1.md`

## Next Safe Action

Do not start degradation/model work, add another broad Backfill diagnostic
slice, or broaden ProductWriter authority from this historical review. Continue
only existing scoped writer hardening or non-broad lanes unless a future product
decision names a new independent truth source.

No tracked-file removal is authorized by this stub.
