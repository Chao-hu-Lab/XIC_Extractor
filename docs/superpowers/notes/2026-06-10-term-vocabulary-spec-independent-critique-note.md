# Independent Two-Round Critique: Term-Level Vocabulary Disambiguation Spec

**Date:** 2026-06-10
**Spec under review:**
[2026-06-10-term-level-vocabulary-disambiguation-spec.md](../specs/2026-06-10-term-level-vocabulary-disambiguation-spec.md)
**Method:** two independent adversarial passes in separate contexts (local
self-critique layer + root framing layer), per the project's spec/plan
critique discipline. Neither critic saw the author's drafting reasoning.

---

## Outcome (both rounds converge)

**REDUCE SCOPE.** Kill the "rename campaign across 6 schema-coupled term
clusters" framing. Keep only two independently-motivated fixes; replace the rest
with a glossary doc.

The two rounds were run separately and arrived at the same place from different
layers: the root critic killed the framing (sunk-cost salvage, glossary beats
rename), and the local critic showed that even the kept parts contain concrete
errors (wrong coupling class, hidden downstream dependency, missing prerequisite
tests). Convergence from two layers is a strong signal the verdict is right.

## Honest origin note (the framing problem)

This spec was produced after the session's original "is the untargeted pipeline
over-conservative?" thesis largely collapsed: three flagged behaviors (60s
no-drift RT wall, complete-link grouping, fail-closed matrix writes) were
verified as deliberate, already-specced design; two semantic claims
(`has_anchor` always-True, a `backfilled` status) were refuted. The term-level
rename spec was the pivot after that collapse. The root critic correctly applied
the project rule *沉沒成本不是論點 / "if I started today, would I design this?"*
and found the 4 word-cluster renames fail that test — they exist mainly to give
the collapsed review a deliverable. The author accepts this.

---

## Round 1 — Local layer (internal consistency, claim accuracy, coverage)

Blockers:

1. **`authority` (b) coupling class is WRONG.** Spec calls
   `standard_peak_ms1_authority_bundle` `internal_only` ("rename freely"). But it
   has `SCHEMA_VERSION = "standard_peak_ms1_authority_bundle_v0"`
   (`standard_peak_ms1_authority_bundle.py:29`), is imported by
   `standard_peak_backfill_productization.py:26`, and hardcodes its name as an
   output directory (`tools/diagnostics/standard_peak_ms1_authority_bundle.py:81`).
   It is `schema_coupled`. An executor following "free move-only PR" would omit
   the required migration. **This proves the rename framing is error-prone even
   for the author.**

2. **A1 "no rescue-count change" is incomplete.** `_candidate_outcome`
   (`owner_backfill.py:479`) does `if cell.trace_quality == "owner_backfill_unassessable": return "unassessable"`. Splitting the label breaks this equality;
   all sub-types fall through and the `candidate_outcome` column in
   `alignment_owner_backfill_candidate_audit.tsv` (`tsv_writer.py:636`) changes.
   True that the primary matrix is unaffected, but an output TSV column changes —
   the spec must call this out and update `_candidate_outcome` as part of the
   split.

3. **C6 parity tests do not exist.** Only one assertion references the label
   (`tests/test_alignment_owner_backfill.py:459`), covering one of five sites.
   The A1 exit rule names "C6 cell-status parity tests" as a prerequisite that
   must be *built first*; A1 is therefore not "immediately executable" as the
   execution order implies.

Coverage gaps (genuine overloads the spec missed — for the glossary, not rename):

4. **`review_only` — 3 meanings:** hypothesis review reason
   (`cross_sample_peak_groups.py:35` Literal), region-audit verdict
   (`region_model_selection.py:26` `ProductAction`), machine-decision audit
   blocker (`machine_decision.py:43` `_AUDIT_BLOCKERS`). The first two both live
   in alignment and share "produces no output" intent — as hazardous as the
   `gate` (a)/(b) pair the spec did catalog.

5. **`primary` — 3 meanings:** matrix role (`machine_decision.py:19`
   `MatrixRole`), owner assignment status (`ownership_models.py:9`
   `OwnerAssignmentStatus`), consolidation outcome (`primary_winner/loser`).

Corrections to spec claims:

6. `consolidation_state` is **confirmed** in `alignment_cells.tsv`
   (`tsv_writer.py:329`; `2026-06-02-cross-sample-peak-group-public-behavior-addendum.md:222`),
   not "likely" as the spec hedged.

Local verdict: not internally sound enough to execute as written; the three
blockers reinforce — not contradict — the root verdict to reduce scope.

---

## Round 2 — Root layer (framing, value/cost, structural risk)

Verdict: **REDUCE SCOPE TO {A1 label-split + `consolidation_state` provenance};
downgrade `shadow`/`gate`/`authority`/`calibration` to a glossary; kill the
rename-campaign framing.**

1. **Sunk-cost/salvage — FAILS the project's own test.** The two pieces with
   independent origins survive (A1 ties to a real batch-poisoning bug at
   `raw_xic_batch_size=64`, `scripts/run_alignment.py:37`; `consolidation_state`
   is a verified provenance ambiguity). The four word-cluster renames do not —
   nobody starting fresh prioritizes renaming overloaded words across
   schema-coupled surfaces over the C4/C6 active-overlap migrations the
   module-level inventory says to do first.

2. **Value vs cost — glossary wins for clusters 1–4.** The spec's own coupling
   table marks nearly everything `schema_coupled`; each rename = migration +
   parity test + version bump + shim, ×6, in a Codex-fast repo. The spec never
   argues why a glossary/comment can't solve the same reader-confusion at zero
   schema churn. `calibration` self-admits filename prefixes already
   disambiguate → drop, don't "defer."

3. **Framing — re-opens a deliberate defer.** The module-level inventory routes
   by module ownership and explicitly fences off "TSV/CLI/public contracts
   without a separate spec"; it deferred naming on purpose. "All the `shadow`s"
   couples four unrelated module migrations to one English word — the opposite
   of module-ownership routing. "Overloaded word" is not a coherent unit of
   cleanup; the module/contract is, with vocabulary captured as a glossary.

4. **Structural risk — unmitigated.** A half-finished rename makes vocabulary
   transiently worse (two names per concept). In a Codex-fast repo a 6-cluster
   sequenced campaign is the textbook stranded-half-rename: new code lands on old
   terms faster than the campaign retires them. No freeze, no single-PR
   completion guarantee. A glossary has none of this risk.

5. **The kernel worth keeping:** (a) A1 label split — but it is the *cheaper
   half*; the batch-poisoning *behavior* fix (per-item `OSError` retry) is the
   one that actually stops data degradation, and it stays sequenced after the #6
   recovery measurement. (b) `consolidation_state` provenance — **additive form
   only** (add a `consolidation_stage` field; do NOT migrate the existing value
   strings).

---

## Integrated recommendation (pending user review)

Replace the single rename-campaign spec with:

1. **A glossary doc** under `docs/` mapping each overloaded term → its per-site
   meaning (include `shadow`×4, `gate`×4, `authority`×3, `calibration`×3,
   `consolidation_state` two-writer, **plus** the missed `review_only`×3 and
   `primary`×3). Linked from both inventories. Zero schema churn; complete on
   write; survives Codex velocity. **This is the actual remedy for
   reader-confusion.**

2. **Targeted fix — A1 `owner_backfill_unassessable` split**, with the local
   corrections folded in: also update `_candidate_outcome:479`; write the C6
   parity tests as the first step (they do not exist yet); flag the audit-TSV
   `candidate_outcome` column change; keep the batch-poisoning *behavior* fix
   separate and sequenced after #6. State plainly the label split only makes the
   poisoning *visible*; the retry fix is what *stops* it.

3. **Targeted fix — `consolidation_state` additive provenance field** (direction
   (i) only).

4. **The single genuine safety rename** — `standard_peak_shadow_activation_inputs`
   under-states its pre-write effect. If reviewers actually misread it, do it as
   one targeted PR; otherwise a glossary entry + docstring captures most of the
   value. `schema_coupled` (`SCHEMA_VERSION = "standard_peak_shadow_activation_inputs_v1"`),
   so even this is a migration, not free.

**Drop:** the `gate`/`authority`/`calibration` renames and the `shadow` renames
beyond item 4. They go to the glossary.

The author's instinct that overloaded vocabulary is a real reviewer hazard is
correct; the error was the remedy (rename where a glossary does the job).
