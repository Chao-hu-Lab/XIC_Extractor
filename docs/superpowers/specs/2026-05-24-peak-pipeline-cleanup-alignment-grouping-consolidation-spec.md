# C6 — Alignment Grouping Consolidation Spec

**Date:** 2026-05-24
**Status:** Cleanup slice draft v0.1
**Overview:** [Peak pipeline cleanup roadmap overview](2026-05-24-peak-pipeline-cleanup-roadmap-overview-spec.md)
**Precondition:** Phase 1 (P1-P6) validated and stable, **and** P3
(third-party shadow comparison) findings recorded under
`docs/superpowers/notes/`. The scope of this spec (A / B / C) is set after
reading the P3 findings note.

## Purpose

Consolidate the five-plus stages of alignment grouping into a smaller set
of grouping primitives. Today each stage has its own tolerance handling,
tie-break rule, and adjacency definition. The behavior is correct for the
DNA adductomics use case but the code surface is large and the rules drift
between stages.

This refactor **may** introduce behavioral changes depending on findings —
see the Scope Decision section below.

## Current State

Modules under `xic_extractor/alignment/` that perform "group entities that
should be treated as one":

- `clustering.py` — main per-NL-tag greedy clustering (the production
  entrypoint that combines compatibility checks, sort key, eject-and-reattach,
  finalization). This is the most central grouping module and the most
  likely target for an algorithm upgrade (Scope B).
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
- `identity_coherence_adapter.py` and `identity_gates.py` — identity
  coherence layer

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

## Scope Decision (set during P3 review)

This spec deliberately leaves the implementation scope partially open until
P3 third-party comparison reports findings. Three possible scopes:

### Scope A: Pure refactor

Extract three grouping primitives:

- `group_by_tolerance(items, key, tolerance_fn)` — base grouping that all
  five stages reduce to
- `eject_and_reattach(clusters, candidate, compatibility_fn)` — shared
  resort/attach logic
- `tie_break_sort(items, sort_key_fn)` — shared tie-break ordering

Each stage becomes a thin adapter on top of the primitives. Behavior is
byte-identical. Code surface shrinks by an estimated 30-40%.

### Scope B: Refactor + selective algorithm upgrade

Same as Scope A, plus replace one or more stages with a graph-based or
EM-iterative grouping (e.g. `owner_clustering.py`'s greedy clustering
upgraded to graph community detection). This introduces behavior changes
and requires its own validation cycle.

### Scope C: Defer to a separate spec

If P3 evidence shows alignment is not the bottleneck (e.g. third-party
tools agree with current alignment on the strict ISTD set), defer C6 in
favor of other cleanup priorities.

The choice is made by the methodology owner after reviewing the P3 findings
note. This spec lands as Scope A by default unless an explicit Scope B / C
note is recorded.

## Required Change (Scope A baseline)

### Step 1 — Inventory grouping primitives

For each stage listed in Current State, document:

- input type
- grouping key
- tolerance signature
- tie-break rule
- ejection / reattachment behavior
- output type

Build a comparison table. Identify the union of behaviors and the per-stage
specialization.

### Step 2 — Define the three primitives

Implement in a new module `xic_extractor/alignment/grouping_primitives.py`:

```text
def group_by_tolerance(items, *, key_fn, tolerance_fn, compatibility_fn): ...
def eject_and_reattach(clusters, candidate, *, compatibility_fn, tie_break_fn): ...
def tie_break_sort(items, *, sort_key_fn): ...
```

Each primitive is unit-tested independently.

### Step 3 — Migrate stages to use primitives

For each stage, replace the inlined grouping logic with calls to the
primitives. Stage-specific tolerance and tie-break functions are passed as
arguments.

After migration, each stage file is significantly shorter and shows only
domain-specific decisions (which tolerances, which tie-breaks), not the
generic grouping mechanics.

### Step 4 — Delete dead helper functions

After migration, several helper functions (per-stage `_attach_to_*`,
`_partition_*`, `_finalize_*`) have no remaining callers. Delete them.

## Validation Contract

Behavioral parity required for Scope A:

1. Run 8RAW with Phase 1 final state + C1a + C2 + C5 + C1b + C3
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

For Scope B (algorithm upgrade), validation is materially different: the
upgrade is treated as a new behavioral change with its own ISTD benchmark.
Scope B requires a separate spec.

## Rollback Condition

For Scope A: revert the refactor if any of:

- hash mismatch on alignment TSVs
- a previously-undetected stage-specific behavior is dropped by the
  primitives (e.g. one stage's tie-break depended on a side effect that the
  primitive does not preserve)

For Scope B: not applicable in this spec; that scope opens a separate
behavior-validation cycle.

## What This Spec Does Not Change (Scope A)

- alignment behavior (production output identical)
- backfill semantics
- identity coherence verdicts
- TSV column names

## Open Questions

- The exact count of grouping stages is empirical; the "five-plus" estimate
  is based on file count, not call-graph analysis. The Step 1 inventory may
  reveal that some stages are already calling shared helpers.
- The "ejection and reattachment" pattern appears in at least three places
  with slightly different semantics. Are the differences intentional? The
  inventory step must catalog and resolve this before introducing a shared
  primitive.
- Scope B candidates: which stage benefits most from a graph-based or
  EM-iterative upgrade? Likely `owner_clustering.py` based on the earlier
  methodology review, but P3 third-party evidence may point elsewhere.
- The `identity_coherence_adapter.py` is the newest of the layers and was
  designed with a cleaner abstraction. Should the primitives be modeled
  after its API, or designed fresh? Lean toward modeling on identity
  coherence since it has the most recent design discipline.

## Acceptance Owner

Methodology owner reviews P3 findings, sets the scope (A / B / C), records
the decision. Engineering owner runs parity validation if Scope A, schedules
follow-up spec if Scope B, records deferral note if Scope C.
