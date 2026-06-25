# Qualitative Selection Acceptance Gate Note

Status: `repo_stub_plus_obsidian`
Validation status: `production_candidate`
Original note date: 2026-05-28

This same-path public stub preserves the durable decision and referrer
compatibility for the historical validation note. The long validation diary and
command transcript were moved to the private Obsidian note
`[[XIC Qualitative Selection Acceptance Gate History]]` and read back before
this stub was written. Private vault access is optional and must not be required
to understand the product decision.

## Public Decision

The Phase 1b qualitative selected-peak / Backfill promotion blocker is closed
for the current production-equivalent alignment path.

The earlier `NO_GO` conclusion was still valid, but the root cause was narrower
than Backfill itself: `owner_backfill` was being used as a support label without
emitting the independent `scan_support_score` required by the shared promotion
policy. The accepted behavior is now:

- owner-backfill cells compute `scan_support_score` from the extracted XIC trace
  and selected peak boundary;
- `trace_quality=owner_backfill` remains insufficient as independent support by
  itself;
- high-backfill promotion requires either at least two detected identity cells
  or one detected seed plus product-authorized same-peak rescue evidence;
- a single detected seed cannot promote a mostly backfilled row from local MS1
  peak presence alone;
- supported high-backfill rows are capped at medium confidence and marked with
  `high_backfill_dependency_capped`.

This does not declare the whole product `production_ready`. It means this
qualitative promotion blocker no longer blocks the next product-decision PR.

## Repo Sources Of Truth

- Current rerun policy and compact gate summary:
  `docs/diagnostic-ledger.md`
- Current productization tier, active lane, and matrix authority:
  `docs/superpowers/plans/2026-06-15-productization-control-plane.md`
- Machine-checkable productization state:
  `docs/superpowers/validation/productization_status_index_v1.tsv`
- Product writer authority:
  `docs/superpowers/specs/productization_authority_manifest.v1.json`
- Validated 85RAW command-profile provenance:
  `docs/agent-parameter-settings.md`

## Next Safe Action

Do not rerun Phase 1b just to re-prove the owner-backfill scan-support fix.
Rerun only after current code changes owner-backfill trace support emission,
promotion policy, selected peak boundaries, product authorization semantics, or
the cited artifacts become stale or contradictory.

No tracked-file removal is authorized by this stub.
