# Peak Selection Simplification Proposal

Date: 2026-04-22  
Status: Draft, aligned with branch reality  
Context: follow-up to [2026-04-22-current-peak-selection-decision-table.md](./2026-04-22-current-peak-selection-decision-table.md) and [2026-04-22-local-minimum-resolver-migration.md](../plans/2026-04-22-local-minimum-resolver-migration.md)

## Goal

Reduce brittle peak-selection behavior by:

- keeping `resolver_mode=legacy_savgol|local_minimum`
- making candidate generation more permissive
- moving more judgment into ranking / scoring / diagnostics
- reducing the number of RT-derived hard gates

This is not a rollback to intensity-only selection. It is a change in **where**
the system is allowed to say "no peak exists".

## What We Learned From Real Data

The branch already established four important facts:

1. `local_minimum` itself is worth keeping.
   - It surfaces candidate regions that the width-based legacy path misses.
   - It is still the right migration direction for low-abundance, messy-matrix
     data.

2. `paired anchor mismatch -> ND` was too harsh.
   - That hard reject has already been downgraded to diagnostic + confidence
     penalty.
   - This is now part of the current branch reality, not a future idea.

3. Some wrong `ND` calls were caused before paired RT logic even mattered.
   - The `15N5-8-oxodG` and `d3-N6-medA` misses showed that
     `resolver_peak_duration_max`, `resolver_min_scans`, and
     `resolver_min_ratio_top_edge` can make `local_minimum` return
     `PEAK_NOT_FOUND` even when a plausible peak exists.

4. That means the next generic fix is not "loosen one more RT rule".
   - The next generic fix is to stop using too many region-shape checks as
     candidate existence gates.

## Core Principle

Two principles govern the simplified design:

1. **Candidate generation should be generous.**
2. **Candidate ranking and scoring should be selective.**

Or in shorter form:

**Candidate generation 寬進, ranking / scoring 嚴出.**

The companion RT principle stays the same:

**Anchor should be evidence, not dictator.**

This applies to:

- target `NL anchor`
- paired `ISTD reference_rt`
- `delta-RT` prior

## Target State

### Hard rules to keep

| Rule | Why keep it hard |
| --- | --- |
| outer RT search window | bounds computation and obvious off-target peaks |
| basic no-signal / malformed-trace failure | true extraction failure, not a ranking issue |
| explicit file / reader errors | not a peak-selection decision |

### Rules to downgrade to soft evidence

| Current rule | Current role | Proposed role |
| --- | --- | --- |
| local-minimum `duration / min_scans / top-edge` region filters | candidate existence gate | region-quality flags + ranking/scoring penalty |
| target NL anchor shrinks XIC window aggressively | hard window control | moderate local bias, not sole authority |
| paired analyte `strict_preferred_rt=True` | hard nearest-RT selection | soft preferred-RT bonus |
| paired target `find_nl_anchor_rt(..., reference_rt=ISTD)` | hard bias during anchor choice | weak tie-break or optional hint |
| `delta-RT` prior in scorer | already soft | keep soft |

### Temporary branch behavior to keep for now

These are not the final design, but they should stay in place until the generic
candidate-softening work is done:

- `_paired_anchor_mismatch_diagnostic()` stays diagnostic + confidence penalty
- ISTD broad-peak recovery stays
- ISTD wider-window retry for anchor-clipped traces stays

Reason: they preserve currently recovered real-data rows while the more general
resolver redesign is still incomplete.

## Unified Execution Order

This is the single intended direction. It replaces the earlier split between
"resolver migration" and "selection simplification" as separate narratives.

### Phase 0: Preserve validated boundaries

Keep these as-is:

- `legacy_savgol` / `local_minimum` dual mode
- A/B comparison harness
- workbook comparison against
  `output/xic_results_20260420_0309.xlsx`
- shipped scoring/output schema

This phase is already in place.

### Phase 1: Convert local-minimum hard filters into quality flags

This is the next implementation focus.

Instead of letting these conditions erase the candidate:

- too broad
- too short
- too few scans
- low top/edge ratio
- edge-clipped

the resolver should emit a candidate plus region-quality metadata.

Expected outcome:

- fewer false `PEAK_NOT_FOUND`
- fewer target-specific escape-hatch recoveries
- better separation between "peak exists" and "peak is weak"

### Phase 2: Teach selector and scorer to consume region-quality metadata

Once candidates carry quality flags, downstream logic should:

- prefer strong candidates over weak ones
- keep weak candidates visible when they are the only plausible region
- map weakness into confidence, reason, and diagnostics

This is where uncertainty becomes explainable instead of disappearing into `ND`.

### Phase 3: Revisit RT-derived control rules

Only after Phases 1-2 are in place should the branch continue simplifying RT
rules:

1. paired `strict_preferred_rt=True`
2. paired ISTD influence on target `NL anchor`
3. anchor-centered extraction-window width

Reason: until the resolver stops over-pruning candidates, RT-path changes are
too hard to interpret.

### Phase 4: Decide whether `local_minimum` can become default

Do not switch the default until:

- focus targets look at least as explainable as the trusted workbook
- no unexpected ISTD catastrophe remains
- manual review of the chemistry says the new calls are directionally better

## Proposed Behavioral Matrix

| Situation | Current intended behavior after simplification |
| --- | --- |
| broad but plausible peak | keep candidate, mark weak if needed |
| edge-clipped region | keep candidate, penalize confidence, add diagnostic |
| multiple plausible peaks | best overall candidate wins, not just nearest RT |
| target has weak / noisy NL anchor | anchor helps ranking, does not dictate output |
| MS2 absent but MS1 pattern plausible | rely more on resolver + scoring, less on forced RT rules |

## Non-Goals

This proposal does **not** mean:

- remove NL logic entirely
- remove ISTD pairing entirely
- remove RT priors entirely
- make every decision intensity-only again
- switch `local_minimum` to default immediately

## Validation Standard

The branch is moving in the right direction if:

- output becomes easier to explain row by row
- `PEAK_NOT_FOUND` becomes rarer for chemically plausible weak peaks
- focus targets become more trend-consistent across injection order
- confidence reflects uncertainty instead of hiding rows as `ND`

Validation should be done in three layers:

1. resolver A/B compare
2. workbook compare against `output/xic_results_20260420_0309.xlsx`
3. target-specific domain review for:
   - `d3-N6-medA`
   - `d3-5-hmdC`
   - `8-oxo-Guo`
   - `8-oxodG`

## Bottom Line

The simplification path is now:

1. keep `local_minimum`
2. stop letting region-shape checks erase plausible candidates too early
3. move more judgment into ranking / scoring / diagnostics
4. only then continue downgrading RT-derived hard control

In short:

**RT should guide selection, and region quality should influence confidence, but
neither should prematurely erase a plausible candidate.**
