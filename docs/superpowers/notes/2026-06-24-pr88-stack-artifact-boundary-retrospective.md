# PR88-PR92 Stack Artifact Boundary Retrospective

Date: 2026-06-24

Status: workflow incident note. This does not change product maturity tier,
active lane, matrix authority, selected values, counted detections, schemas, or
runtime behavior.

## Verdict

Stop patching PR88 CI failures one by one. The failure mode is structural:
PR88 through PR92 were split from a large productization branch after several
global ledgers, validation artifacts, and externalized review outputs had
already become coupled.

The correct recovery path is to establish an artifact-boundary prerequisite and
then retarget the stack, not to keep refreshing hashes or test assumptions in
each PR.

## Observed Stack Shape

Open stack at the time of the incident:

| PR | Head branch | Intended theme | Actual risk |
| --- | --- | --- | --- |
| #88 | `codex/pr03-quant-matrix-foundation` | QuantMatrix foundation | Also owns validation artifact retention, lockbox rendered-output externalization, discovery row identity hardening, CI/test assumptions, and status-index churn. |
| #89 | `codex/pr04-cid-nl-discovery-activation` | CID-NL discovery activation | Depends on discovery schema and productization ledgers introduced or churned by #88. |
| #90 | `codex/pr05-backfill-clean-target` | Clean-target backfill activation | Depends on the same productization control-plane/status vocabulary. |
| #91 | `codex/pr06-dna-dr-product-ready-performance` | DNA-dR preset performance | Mostly runtime/product work, but still touches shared control-plane and preset surfaces. |
| #92 | `codex/pr07-row-completion-confidence` | Row-completion confidence shadow gate | Again updates the same global productization ledgers and handoff surfaces. |

Repeated global files across the stack included:

- `docs/superpowers/validation/productization_status_index_v1.tsv`
- `docs/superpowers/plans/2026-06-15-productization-control-plane.md`
- `docs/superpowers/handoffs/current/cc-framework-improvements-productization.md`
- `docs/superpowers/validation/ARTIFACT_INVENTORY.tsv`
- `docs/superpowers/validation/bounded_non_broad_lane_acceptance_v1.tsv`

This made the PRs behave as different snapshots of one global productization
state rather than independent reviewable slices.

## Root Causes

1. The split was performed after global state had already been mutated.
   The branch history looked linear, but the review/CI surface was not separable.
2. Artifact retention cleanup was mixed into a product PR.
   Removing tracked generated outputs without making default checks independent
   from ignored local artifacts created reverse coupling to `output/` and
   `local_validation_artifacts/`.
3. Global ledgers were updated in every PR.
   Each PR rewrote the productization status index, control plane, and active
   handoff, so a merge of one PR invalidated assumptions in the next.
4. Hash cascades were treated as repairable red checks.
   Recomputing artifact hashes fixed symptoms but preserved the design flaw:
   intermediate PRs still depended on the whole stack's artifact snapshot.
5. Discovery schema hardening was bundled into QuantMatrix foundation.
   Candidate row identity parsing is a discovery/alignment contract and should
   not be hidden inside a QuantMatrix promotion PR.
6. CI failures were interpreted too locally.
   The repeated failures were a signal that the stack boundary was wrong, not
   evidence that another small test patch was the right next action.

## Corrective Rules

- Before repairing a stacked PR, build a stack map: PR base/head, commit themes,
  repeated files, tracked versus externalized artifacts, and local-output CI
  assumptions.
- If multiple PRs mutate the same global ledger, stop. Move ledger updates to a
  prerequisite boundary PR or a final rollup PR.
- Default CI may not require ignored `output/`, `.worktrees/`, rendered review
  files, or `local_validation_artifacts/` bytes.
- Externalized artifacts must be represented by tracked summaries, minimal
  fixtures, manifests, row counts, and hash strings. Presence and byte-hash
  checks for the ignored local bytes must be explicit opt-in local validation.
- A PR that externalizes artifacts must also own the default-check fallback. Do
  not rely on a later cleanup PR to make the earlier PR CI-valid.
- Schema hardening belongs with the product surface it protects. Do not bury a
  discovery/alignment parser contract inside an unrelated matrix foundation PR.
- After the same CI failure shape repeats twice, stop and classify the coupling
  before adding another fix commit.

## Recovery Plan

1. Freeze #88-#92. Do not continue merge-repair commits while the boundary is
   unclear.
2. Create a small prerequisite PR from current `master` that owns artifact
   boundary semantics only:
   - no product behavior change;
   - no maturity-tier or active-lane change;
   - default CI independent from ignored local artifacts;
   - opt-in local flags for rendered/externalized byte checks;
   - docs and tests proving the default/local distinction.
3. Rebuild #88 as QuantMatrix foundation only:
   - keep QuantMatrix package code, scripts, schemas, small fixtures, and
     focused tests;
   - remove lockbox rendered-output cleanup, discovery parser hardening, and
     broad status-index churn unless they are required prerequisites already
     landed.
4. Move discovery row identity hardening to its own PR or to the CID-NL
   discovery activation PR where the contract belongs.
5. Replace per-PR global ledger rewrites with scope-local manifests. Use a final
   rollup PR to update the productization status index, control plane, and
   active handoff once the product slices are merged.
6. Retarget #89-#92 one at a time after #88 is self-contained. A later PR should
   fail only for its own scope, not because it inherited stale artifact state.

## Lesson

This was an agent process failure: the split optimized for commit-history
preservation but did not first prove review/CI independence. Future stacked PR
work must treat artifact boundaries and global ledgers as first-class ownership
surfaces, not as mechanical files to refresh after CI turns red.
