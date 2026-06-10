# Backfill / Alignment Architecture-Debt Audit

**Date:** 2026-06-10
**Scope:** the backfill/alignment subsystem only (`xic_extractor/alignment/*`,
the backfill/standard_peak/shadow/peakhypothesis modules in
`xic_extractor/diagnostics/*`). The "soul" subsystem, per the user.
**Status:** findings note — diagnostic only, authorizes no change. Input for
follow-up cleanup PRs / Codex review.
**Method:** four parallel evidence-first lenses (duplicate design;
over-fetching/over-coupling; dead field/config; apparatus liveness/orphan), each
required file:line + confidence. The two highest-value, most-deletable claims
were then **personally re-verified by grep** before being recorded as fact, per
the project's verify-before-design discipline.

**Explicitly out of scope (known/intentional, not flagged):** the apparatus
being `diagnostic_only` / `product_ready=False` is a deliberate state — the user
has not yet had the energy to push it to production. C4 (peak scoring vs
evidence spine) and C6 (owner-family vs hypothesis spine) are already cleaned up.

---

## Headline verdict (answers to the four questions asked)

1. **"One semantics, multiple systems"?** Yes, but *not* at the module level.
   A strict pass against the repo's own lifecycle-spec RETIRED criteria found
   **zero orphan modules** — all 20 scaffold modules are STAGED (referenced by
   specs/plans edited 2026-06-07…2026-06-10, all with schema tests). **Do not
   delete scaffold modules.** The real "multiple systems" problem is *inside*
   the scaffold: the same helper logic and the same decisions are re-implemented
   in several places.

2. **"Over-dependency on data"?** Yes, both flavors, and several are on hot
   loops: redundant RAW re-reads + recompute-what-upstream-already-has (perf),
   and functions taking whole objects to use a few fields (coupling).

3. **"Meaningless / outdated design"?** Yes, two kinds: genuinely dead (1
   function + 3 config params, both verified) and "designed but inert" (a batch
   of `backfill_*` cell fields that are serialized but never read by any
   decision — a smell, but not safe to delete).

4. **Structural defect?** One latent correctness risk (an inconsistent overlay
   sort key) plus two parallel deciders that should converge.

**Weight:** scaffold ≈ 17,500 LOC vs live-path ≈ 8,550 LOC — the apparatus is
~2× the production path. Heavy is not wrong (it is staged), but there is
substantial compressible duplication inside that weight.

---

## Personally verified (recorded as fact)

- **Dead function `_backfill_feature_sample`** — `owner_backfill.py:694-819`
  (~125 lines). Grep for `_backfill_feature_sample(` returns only the `def`;
  zero call sites anywhere (the only other mention is a doc describing how it was
  split). It still carries a full `source.extract_xic(...)` RAW re-read. The live
  path uses `_backfill_feature_sample_trace` instead. **Confirmed dead.**
- **Three dead config params** — `config.py:18,19,22`:
  `mz_bucket_neighbor_radius`, `anchor_priorities`, `anchor_min_scan_support_score`.
  Grep across `xic_extractor/` shows each appears only in its definition +
  `__post_init__` validation; zero consumption in any computation. (Contrast:
  `anchor_min_evidence_score` / `anchor_min_seed_events` ARE consumed in
  `edge_scoring.py:243-244` — the lens correctly separated the live from the dead
  anchor params.) **Confirmed dead.**

Everything below is lens-traced (agent), confidence as marked; spot-check before
acting on Tier 2+.

---

## Tier 1 — verified dead + mechanical duplication (safe cleanup)

Acceptance criterion: **Cleanup** — numerical equivalence / characterization
parity, no behavior change. Lowest risk; can ship as one move-only PR.

| Item | Evidence (file:line) | Confidence |
|---|---|---|
| Delete dead `_backfill_feature_sample` | `owner_backfill.py:694-819` (verified no caller) | HIGH |
| Delete 3 dead config params | `config.py:18,19,22` + their `_require_*` validators | HIGH |
| Extract `_group_by_family` (×3, letter-identical) | `backfill_shadow_policy.py:567`, `shadow_production_projection.py:712`, `retained_backfill_evidence_gate.py:757` | HIGH |
| Extract `_sha256_file` (×4, identical; settle `file_sha256` naming) | `backfill_shadow_policy.py:593`, `retained_backfill_evidence_gate.py:1011`, `standard_peak_ms1_authority_bundle.py:632`, `backfill_peakhypothesis_promotion.py:281` | HIGH |
| Extract `_numeric_equal` (×2, identical `rel_tol=1e-6, abs_tol=1e-9`) | `backfill_peakhypothesis_activation_acceptance.py:571`, `backfill_peakhypothesis_85raw_activation_transfer.py:508` | HIGH |
| Extract `_has_reason_token` (×2, identical) | `backfill_ms1_product_authority.py:395`, `standard_peak_ms1_authority_bundle.py:599` | HIGH |
| Extract `_rows_by_key` (×2, near-identical) | `backfill_evidence_projection.py:224`, `backfill_ms1_product_authority.py:151` | MED |

Suggested homes: a `diagnostics/_backfill_shared.py` for the diagnostics-side
utils; an `alignment/_backfill_util.py` for the alignment-side ones. Keep imports
in the allowed direction (`diagnostics → alignment`, which already exists).

---

## Tier 2 — over-fetching / over-coupling (perf; needs characterization parity)

Acceptance criterion: **Cleanup**, but because these touch hot loops, ship each
behind a characterization test that pins matrix/cell output byte-for-byte
(move-before-change). Connects to the existing alignment perf work (banded AsLS).

| Item | What's wasted | Evidence (file:line) | HOT | Confidence |
|---|---|---|---|---|
| `median_owner_area` recomputed per detected-sample/per-cell | re-iterates `feature.owners` + recomputes median; invariant per feature | `owner_area.py:19`; `owner_matrix.py:183` (HOT), `backfill_scope.py:216`, `owner_backfill.py:996` | YES | HIGH |
| `delivery_cell_projection` does 8 `getattr` chains per cell | invariant per feature, recomputed × samples | `owner_group_delivery.py:214`, called from `owner_matrix.py` + `owner_backfill.py` | YES | HIGH |
| `cells_by_cluster(matrix)` rebuilt 3-4× per pipeline run | full cell scan repeated | `primary_consolidation.py:58,133`; `claim_registry.py:41-66`; `pre_backfill_consolidation.py:52` | — | HIGH/MED |
| `_can_skip_for_production_equivalence` O(N²) full-features scan | per-feature linear scan of all features | `backfill_scope.py:273-290` (from `:99/:117`) | — | HIGH |
| `confirm_local_owners_with_backfill` re-reads already-fetched XIC window | ownership already pulled the trace; backfill re-pulls for all detected samples even when supersession will pre-fail | `backfill_scope.py:165`; `ownership.py:231`; `owner_backfill.py:154` | YES | MED |

Common fix pattern: precompute per-feature scalars/dicts (median area, delivery
projection, grouped cells) once, pass them down; gate the `confirm` re-fetch
behind the supersession pre-check using the owner area already in memory.

---

## Tier 3 — verify before acting (possible bug; inert-but-serialized fields)

These are NOT cleanup — they need a decision/verification first.

- **Latent overlay-selection inconsistency.** `_selected_overlay_row` is copied
  in 3 modules; `retained_backfill_evidence_gate.py:719` sorts with an **inverted
  key** vs `backfill_shadow_policy.py:539` and `shadow_production_projection.py:701`.
  For a family+sample with multiple overlay rows, the three modules can select
  **different** rows. Verify whether the inversion is intentional. If not, it is a
  correctness bug, not a DRY item — fixing it changes selected evidence, so it
  must go through behavior validation, not a cleanup PR.
- **"Inert" output-only cell fields.** A batch of `backfill_*` fields are loaded
  into `CellBackfillEvidence` and serialized to TSV but **never read by any
  decision `@property`** in `promotion_policy.py`: `backfill_ms1_product_authority_reason`,
  `backfill_ms1_product_authority_evidence_sha256`, `backfill_qc_reference_evidence_level`,
  `backfill_candidate_ms2_product_authority_reason`,
  `backfill_candidate_ms2_product_authority_evidence_sha256`,
  `backfill_ms2_trigger_scan_count`, `backfill_strict_nl_scan_count`,
  `backfill_ms2_trace_strength`, `backfill_dda_missing_nl_policy_status`,
  `backfill_family_ms2_required_tag_status`; plus provenance-only
  `backfill_seed_mz/rt`, `backfill_request_rt_min/rt_max/ppm`,
  `group_construction_role/delivery_role/membership_source`,
  `consolidation_winner/source_group_hypothesis_id`,
  `claim_winner/source_group_hypothesis_id`, `integration_audit`. These are a
  "designed but does nothing in decisions" smell. **Not safe to delete** — first
  confirm whether reviewers consume these TSV columns. If unused there too, they
  become removal candidates; if used for review, they stay (output-only is a
  legitimate role).

---

## Tier 4 — design decisions tied to staged productization (do NOT bundle as DRY)

These look like duplication but touch the staged productization flow; converging
them is a roadmap decision, governed by the relevant productization spec — not a
cleanup.

- **Two parallel "should this rescued cell fill?" deciders** (~60% overlap):
  `backfill_shadow_policy._shadow_decision` (`:279`, simpler, no
  product-authority chain) vs
  `shadow_production_projection._shadow_projection_decision` (`:366`, richer,
  authoritative). One lens suggested *retiring* `backfill_shadow_policy` — **but
  it is STAGED** (referenced by the 2026-06-07 productization docs, has a schema
  test asserting `backfill_shadow_policy_v0`). Whether it has been superseded by
  the projection decider is a **roadmap call only the user can make**, not a
  safe cleanup.
- **`_same_peak_verdict` resolution logic re-implemented ×3** —
  `normal_peak_decision.py:506`, `85raw_activation_trial.py:327`,
  `85raw_activation_transfer.py:450`. The "prefer manual, then machine"
  resolution should have one home (`_resolve_same_peak_verdict(manual, machine)`),
  with per-stage row-schema adapters kept separate. Cross-stage, so route through
  the productization spec.
- Lower-grade near-duplicates in the same family (do later, with the above):
  trial/transfer blockers share 5 checks (`85raw_activation_trial.py:302` vs
  `85raw_activation_transfer.py:204`); two activation-decision-row constructors
  emit the same `ACTIVATION_DECISION_COLUMNS`
  (`standard_peak_shadow_activation_inputs.py:347` vs `activation_bridge`); a
  trace-JSON validator is ~85% shared (`backfill_ms1_product_authority.py:403`
  vs `standard_peak_ms1_authority_bundle.py:543`); and
  `shadow_production_projection._product_authorized_same_peak_backfill` re-derives
  string-wise what `promotion_policy.py` defines canonically.

---

## Cross-lens reconciliation (important)

The duplicate-design lens and the orphan lens appear to conflict — one says
"retire `backfill_shadow_policy`", the other says "all scaffold is STAGED". The
orphan lens wins on liveness: **nothing here is an orphan to delete.** The
correct synthesis is: *consolidate the duplicated helper code (Tier 1) and the
duplicated decision logic (Tier 4), but keep every module*, because all are
referenced by recent staged work. The user's instinct that "the scaffold has a
lot of useless/duplicate design" is half-right: not useless modules to delete,
but duplicated code + parallel deciders to consolidate.

---

## Confidence / not-verified caveats

- Verified by me directly: the dead function and the 3 dead config params only.
- Everything in Tier 1 helper-extraction is mechanical (copy-paste), HIGH
  confidence, but a one-line grep per pair is cheap insurance before the PR.
- Tier 2 hot-path claims are agent-traced; confirm the call multiplicity
  (per-cell vs per-feature) by reading the loop before optimizing.
- Tier 3 overlay sort-inversion is the single item most likely to be a real bug
  — verify the sort keys side-by-side first.
- The output-only field list is "no decision reads it"; it does NOT establish
  "no reviewer uses the TSV column" — that is a separate check.

## Recommended execution order

1. **Tier 1** as one cleanup PR (delete dead function + 3 config + extract 5-6
   util groups), full test run to confirm numerical equivalence.
2. **Tier 3 overlay sort-key** — verify; if a bug, fix it on its own with
   behavior validation.
3. **Tier 2** perf items, each behind a characterization test.
4. **Tier 4** decider/verdict convergence — only via the productization spec,
   never bundled into a cleanup PR.

Tier 2+ items, before becoming work, should get the same two-round independent
critique that this session's spec went through.
