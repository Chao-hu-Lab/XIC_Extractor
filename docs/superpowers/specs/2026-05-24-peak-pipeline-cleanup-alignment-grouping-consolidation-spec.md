# C6 — Alignment Grouping Consolidation Spec

**Date:** 2026-05-24
**Status:** Superseded-for-implementation v0.4 — replaced by stage-semantics
value assessment; old generic-primitives plan is historical rationale only
**Overview:** [Peak pipeline cleanup roadmap overview](2026-05-24-peak-pipeline-cleanup-roadmap-overview-spec.md)
**Current reassessment:** [Peak pipeline cleanup current-state reassessment](2026-06-01-peak-pipeline-cleanup-current-state-reassessment-spec.md)
**Current C6 design:** [C6 alignment stage semantics and value assessment](2026-06-01-c6-alignment-stage-semantics-value-assessment-design.md)
**One-goal execution contract:** [Peak pipeline cleanup one-goal phase contract](2026-06-01-peak-pipeline-cleanup-one-goal-phase-contract-spec.md)
**Precondition for any future implementation:** follow the current C6 design,
complete stage semantics/value inventory, and name golden parity surfaces. The
old P3 / Scope A wording below is historical only.

## 2026-06-01 Brainstorming Outcome

Do not execute the generic-primitives plan below literally. Current alignment
code has graph, owner, loser, review, matrix-identity, and downstream delivery
semantics that are too specific for a blind `group_by_tolerance` extraction.

The accepted C6 direction is now captured in
[C6 alignment stage semantics and value assessment](2026-06-01-c6-alignment-stage-semantics-value-assessment-design.md).
C6 starts with semantic inventory and value assessment. It may select a later
cleanup slice only after parity surfaces are named.

That design settles:

- which alignment stages are true generic grouping versus identity/gate policy,
  review/audit policy, or matrix delivery;
- which stage has the strongest characterization oracle;
- which TSVs are golden parity surfaces for any future refactor;
- whether any shared primitive is justified by identical semantics rather than
  similar-looking code.

## Historical Purpose (Non-Executable)

Consolidate the five-plus stages of alignment grouping into a smaller set
of grouping primitives. Today each stage has its own tolerance handling,
tie-break rule, and adjacency definition. The behavior is correct for the
DNA adductomics use case but the code surface is large and the rules drift
between stages.

This historical refactor proposal must not be executed as written. It is
retained only for stage inventory, risk notes, and parity surfaces. If future
brainstorming shows an algorithm upgrade or different stage split is needed,
that belongs in a separate behavior spec, not in this historical C6 sketch.

## Current State

Modules under `xic_extractor/alignment/` that perform "group entities that
should be treated as one":

- `clustering.py` — main per-NL-tag greedy clustering (the production
  entrypoint that combines compatibility checks, sort key, eject-and-reattach,
  finalization). The old plan suspected shared mechanics here, but that is not
  implementation permission. Any future cleanup must start from a row-level
  C6-B/C disposition in the current stage-semantics design, with a named parity
  oracle, and must preserve this algorithm exactly.
- `ownership.py` — build sample-local owners from candidates
- `owner_clustering.py` — cluster owners across samples (a second
  clustering pass at the owner granularity)
- `feature_family.py` — group clusters into families
- `family_integration.py` — integrate per-family rows into the final matrix
  via per-cluster grouping decisions
- `pre_backfill_consolidation.py` — consolidate before backfill
- `primary_consolidation.py` — consolidate primary rows after backfill
- `backfill.py` and `owner_backfill.py` — backfill detected vs rescued
- `folding.py` — near-duplicate folding
- `near_duplicate_audit.py` — audit duplicates
- `claim_registry.py` — MS1 peak claim handling (acts as a grouping
  arbitrator when multiple owners claim the same MS1 peak)
- `matrix_identity.py` — matrix identity formation (the final grouping pass
  that decides which rows become primary / provisional / audit identities)
- `identity_coherence_adapter.py` and `identity_gates.py` are **not grouping
  cleanup targets** for C6. They are identity/evidence gates. C6 may read them
  during inventory to avoid semantic drift, but must not consolidate them into
  generic grouping primitives unless a separate identity contract says so.

Each has its own:

- ppm tolerance handling
- RT tolerance handling
- product-mz tolerance handling
- observed-neutral-loss tolerance handling
- tie-break rule (anchor priority, evidence score, area, m/z, RT, sample
  stem, candidate ID)
- duplicate-detection threshold
- "eject and reattach" logic for overlapping clusters

The handoff progress checklist §8 has already noted that some diagnostic
tools are too broad and should be split. This spec is about the production
side of the same observation.

## Historical Non-Executable Scope

The scope below is the old generic-primitives proposal. Future agents may reuse
it as a checklist of suspected duplicate mechanics, but must not treat it as an
approved implementation plan. The accepted stage-semantics design only permits
future implementation from a row-level disposition with a named parity oracle.

The old proposal claimed it would extract three grouping primitives:

- `group_by_tolerance(items, key, tolerance_fn)` — base grouping that all
  five stages reduce to
- `eject_and_reattach(clusters, candidate, compatibility_fn)` — shared
  resort/attach logic
- `tie_break_sort(items, sort_key_fn)` — shared tie-break ordering

Each stage becomes a thin adapter on top of the primitives. Behavior is
byte-identical. Code surface shrinks by an estimated 30-40%.

Out of scope:

- graph-based grouping, EM-style grouping, or any algorithm upgrade
- new tolerances, new tie-break priority, or new ejection behavior
- identity coherence gate consolidation

If P3 evidence shows alignment is not the bottleneck, C6 may simply be
deferred. If P3 evidence shows an algorithmic bottleneck, write a separate
behavior-change spec.

## Historical Non-Executable Implementation Sketch

### Historical Step 1 — Inventory grouping primitives

For each stage listed in Current State, document:

- input type
- grouping key
- tolerance signature
- tie-break rule
- ejection / reattachment behavior
- output type

Build a comparison table. Identify the union of behaviors and the per-stage
specialization.

### Historical Step 2 — Define the three primitives

Implement in a new module `xic_extractor/alignment/grouping_primitives.py`:

```text
def group_by_tolerance(items, *, key_fn, tolerance_fn, compatibility_fn): ...
def eject_and_reattach(clusters, candidate, *, compatibility_fn, tie_break_fn): ...
def tie_break_sort(items, *, sort_key_fn): ...
```

Each primitive is unit-tested independently.

### Historical Step 3 — Migrate stages to use primitives

For each stage, replace the inlined grouping logic with calls to the
primitives. Stage-specific tolerance and tie-break functions are passed as
arguments.

After migration, each stage file is significantly shorter and shows only
domain-specific decisions (which tolerances, which tie-breaks), not the
generic grouping mechanics.

### Historical Step 4 — Helper retirement after proven migration

The old proposal assumed several helper functions (per-stage `_attach_to_*`,
`_partition_*`, `_finalize_*`) would have no remaining callers after a proven
migration. A future rewrite must re-verify caller state before retiring any
helper.

## Historical Parity Surfaces To Reuse

Behavioral parity required:

1. Run 8RAW with Phase 1 final state and P3 findings recorded
2. Apply C6 Scope A refactor
3. Re-run 8RAW
4. All alignment TSVs hash-identical:
   - `alignment_matrix.tsv`
   - `alignment_review.tsv`
   - `alignment_cells.tsv`
   - `alignment_cell_integration_audit.tsv`
   - any seed-aware / family overlay / cell region audit TSVs
5. Identity coherence verdicts unchanged
6. Backfill detected / rescued / absent labels unchanged

## Rollback Condition

Revert the refactor if any of:

- hash mismatch on alignment TSVs
- a previously-undetected stage-specific behavior is dropped by the
  primitives (e.g. one stage's tie-break depended on a side effect that the
  primitive does not preserve)

## What This Spec Does Not Change

- alignment behavior (production output identical)
- backfill semantics
- identity coherence verdicts
- TSV column names

## Open Questions

- Historical package-layout / primitive questions above are superseded. Current
  open questions live in the stage-semantics value-assessment design and should
  be answered row-by-row, not by reopening a broad grouping-primitive refactor.
- The exact count of grouping stages is empirical; the original "five-plus"
  estimate is based on file count, not call-graph analysis. The current C6
  design replaces this with a CodeGraph-assisted module-family map.
- The "ejection and reattachment" pattern appears in at least three places
  with slightly different semantics. Are the differences intentional? The
  inventory step must catalog and resolve this before introducing a shared
  primitive.
- Algorithm-upgrade candidates are intentionally not answered by C6. If P3
  points to `owner_clustering.py` or another stage as a bottleneck, open a
  separate behavior spec with its own validation thresholds.
- The `identity_coherence_adapter.py` is the newest of the layers and was
  designed with a cleaner abstraction. Should the primitives be modeled
  after its API, or designed fresh? Lean toward modeling on identity
  coherence since it has the most recent design discipline.

## Acceptance Owner

Methodology owner reviews P3 findings and records whether C6 should proceed
as a row-level C6-B/C slice or be deferred. Engineering owner runs parity
validation if a later implementation proceeds. Any algorithm upgrade is
scheduled as a separate spec.
