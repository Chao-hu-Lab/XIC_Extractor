# Dual-System and Retired-Path Product-Behavior Audit

**Date:** 2026-06-05
**Branch:** `codex/cleanup-retirement-foundation`
**Status:** Investigation / discussion input — **no decision, no code change.** Read-only audit intended as input for a product-direction conversation with Codex.
**Method:** 5 parallel read-only explorer agents (alignment / peak-region-evidence / extraction-output / qc-discovery-config-gui / contracts-vs-diagnostics), followed by direct file reads to verify the highest-impact claims.

## Framing

This repo is **not accidentally maintaining two systems.** It is **mid-migration**:
an `owner → successor` rebuild where the new system (Gaussian15 evidence owner,
typed decision semantics, cross-sample peak groups) is built and runs in
**shadow / parity**, while the **legacy system remains the default authority** on
most live paths.

Two retirements are **clean** (only rejection guards remain, no behavioral leak):
`linear_edge` baseline and the `arbitrated` resolver. Those are done correctly.

The concern is the **migration seams**: a handful of legacy paths are not dead
code — under specific conditions they still decide the **reported area** or the
**detection call**. For a quantitative LC-MS tool the peak picker and the
integrator *are* the measurement, so the audit focuses on one question:

> **Is the final reported area / detection call always produced by a single,
> well-defined method?**

Today the answer is "not guaranteed."

Because this is **cleanup-type work, the acceptance criterion is numerical
equivalence between the old and new path.** Each item below is framed as: are the
two paths equivalent, and if not, which one wins.

---

## Tier 1 — Materially affects reported numbers / detection (MS-relevant)

### T1-1. Two contradictory defaults for the peak resolver  *(verified)*

- `xic_extractor/configuration/models.py:17` — `ExtractionConfig.resolver_mode` dataclass default is `"legacy_savgol"`.
- `xic_extractor/settings_schema.py:27` — `CANONICAL_SETTINGS_DEFAULTS["resolver_mode"]` is `"region_first_safe_merge"`.

The GUI/settings path is correct (canonical default wins). But **any code that
constructs `ExtractionConfig(...)` without going through settings** (scripts,
fixtures, future modules) silently gets `legacy_savgol` — a different peak-picking
algorithm, hence different boundaries and areas. `peak_detection/facade.py:241,263,358`
and `recovery.py:40` reinforce this with `getattr(config, "resolver_mode", "legacy_savgol")`
fallbacks. **The two defaults disagreeing is a bug regardless of whether it fires today.**

### T1-2. Instrument QC uses a third resolver, hardcoded, ignoring user settings  *(verified)*

- `xic_extractor/instrument_qc/pipeline_extraction.py:114-127` — `_peak_config()` hardcodes
  `resolver_mode="local_minimum"` (plus its own `smooth_window=7`, `smooth_polyorder=2`, etc.).

Net effect: three resolvers can be in play at once — `region_first_safe_merge`
(sample default), `legacy_savgol` (dataclass default), `local_minimum` (QC). QC
peaks and sample peaks are picked by **different algorithms.**

MS read: a fixed QC peak picker is often *intentional* for system suitability
(QC must stay comparable over time, not drift with user-tuned sample params).
Flagged not as a bug but to confirm the empirical consequence: **QC area and
sample area are not produced by the same algorithm — any analysis that compares
QC area directly to sample area is unsafe.**

### T1-3. The alignment matrix can mix in a legacy scalar integration  *(code verified; trigger frequency UNVERIFIED)*

- `xic_extractor/alignment/owner_matrix.py:91-102`:
  ```python
  selected_integration=(
      getattr(owner, "selected_integration", None)
      or integration_from_values(..., boundary_sources=("alignment_owner_scalar_legacy",))
  )
  ```
- This value flows to `AlignedCell.matrix_area` (`alignment/matrix.py:93`) and into `alignment_matrix.tsv`.

When `owner.selected_integration` is None/falsy, the final matrix area comes from
the **legacy scalar fallback**, not the new evidence-based integration. A single
matrix column can therefore carry **mixed integration provenance**
(new-evidence vs legacy-scalar) across samples.

**Open empirical question:** how often is `SampleLocalMS1Owner.selected_integration`
unset on real runs? That decides whether this is a theoretical seam or something
happening on every matrix. Answerable from data (`ownership.py` fill path + a
one-shot count).

### T1-4. VERY_LOW-confidence peaks are counted as detected via a legacy rule  *(injection verified; downstream effect per Agent C, not re-verified end-to-end)*

- `xic_extractor/extraction/result_assembly.py:764-765`:
  ```python
  if result.confidence.upper() == "VERY_LOW" and not conflict_reasons:
      reasons.append("legacy_confidence_review")
  ```
- Per Agent C's trace: a non-empty `review_reasons` with empty `not_counted_reasons`
  resolves to `detected_flagged` (counted_detection=True) in
  `peak_detection/targeted_product_projection.py:136-147`.

MS read: the whole point of the Gaussian15 / typed-evidence successor appears to
be replacing the legacy confidence heuristic — yet the legacy confidence system
still **pushes VERY_LOW-confidence peaks into counted detection.** That directly
inflates the present/absent call. This is a science-level threshold decision, not
cosmetics, and signals the evidence-honesty migration is not yet closed.

### T1-5. Two Excel paths report different detection counts; one fabricates a science field  *(verified)*

- Memory path: `xic_extractor/output/excel_pipeline.py` runs with `require_projection=True`.
- CSV-first path: `xic_extractor/output/workbook_inputs.py:52` — `_wide_to_long_rows`
  **hardcodes `"Confidence": "HIGH"`** and emits no `targeted_product_projection` columns.
  Reached when `xic_results_long.csv` is absent and the run goes through
  `scripts/csv_to_excel.py` / `keep_intermediate_csv`.

When the long CSV is missing, `require_projection=False`, `sheet_summary` falls
back to legacy detection logic, and **the same run summarized two ways yields
different counted-detection numbers** — with the CSV-first path stamping every
row `Confidence=HIGH`. Hardcoding a confidence value is **fabricating a scientific
field**, not legacy residue. Report-integrity issue; highest priority to close.

---

## Tier 2 — Currently inert dead code, but latent hazards

These do **not** change output today, but they inflate the API surface and are
re-wiring traps:

- **Alignment legacy object model (dead):** `alignment/compatibility.py`,
  `alignment/folding.py`, and `models.AlignmentCluster` are test-only. `AlignmentCluster`
  is still exported in `alignment/__init__.py` and appears in `matrix.py` /
  `pre_backfill_consolidation.py` Union types, but is **never instantiated at
  runtime** — it makes readers think the old object model is still live.
- **`alignment/owner_clustering.py` is now a thin facade** over
  `cross_sample_peak_groups.py`; `OwnerAlignedFeature` vs `CrossSamplePeakGroupHypothesis`
  duplicate ~30 lines of field-by-field copy. This is a **known transitional state
  with an explicit exit rule** (`owner_family_successor_contract.py`) — retire only
  after parity.
- **`xic_extractor/peak_scoring.py` is an empty re-export shim** with no caller
  (C4 spec Superseded; kept intentionally).
- **`extraction/peak_candidate_table.py:467` `append_peak_candidate_rows` and
  `extraction/peak_candidate_boundaries.py:160` `append_peak_candidate_boundary_rows`**
  are still public, unretired, and call `build_peak_hypotheses` independently
  (bypassing the handoff spine), so their `selected` marker can diverge from the
  product selection. No live caller today — the most likely future misuse trap.

---

## Tier 3 — Diagnostics has become a second system + contract gaps

- **Diagnostics re-implements TSV IO and has already drifted:**
  `tools/diagnostics/asls_truth_validation_inputs.py:960` reads with `encoding="utf-8"`,
  while `p2_baseline_truth_audit.py`, `p2_asls_shadow_gate.py`, and the canonical
  `xic_extractor/diagnostics/diagnostic_io.py` use `utf-8-sig`. **If a TSV carries
  a BOM (common from Excel), the three local copies behave differently** — column
  names get a `﻿` prefix → schema validation failure or silent key miss.
- **`tools/diagnostics/area_integration_uncertainty_io.py:153-157` violates the
  team's own Phase 6 retirement contract:** it **silently reads the deprecated
  `area_baseline_corrected_linear_edge` rollback column** and takes a
  `linear_edge_compatible` path, whereas `cleanup-retirement-one-pass-goal.md:219-220`
  requires diagnostic readers to *fail with an actionable regeneration message.*
  Feeding an old artifact yields a plausible-but-inconsistent `baseline_fraction`
  with no error.
- **`_integrate_historical_linear_edge_baseline` (diagnostics) is intentionally
  retained** as a frozen historical comparator ("retained only for locked
  retirement evidence") — **leave it alone**; it cannot drift.
- **Documentation gap:** roadmap-v2 records R1 complete, but
  `plans/2026-05-26-diagnostic-cleanup-cluster1-3-plan.md` tasks are all `[ ]`. The
  two docs define "R1" differently; a reader of one will mis-judge the state.

---

## What is cleanly retired (credit)

- **`linear_edge` baseline** — fully removed from product code; only rejection
  guards remain (`peak_detection/baseline.py:132`, `configuration/settings.py:469`,
  `peak_detection/integration_audit.py:49`, `alignment/tsv_writer.py:287`), backed by
  a static-scan guard test. No leak.
- **`arbitrated` resolver** — only rejection guards remain
  (`settings_schema.py:15`, `configuration/settings.py:327`, `peak_detection/facade.py:244`);
  private functions gone. `_combine_proposal_sources` retained for preferred-RT
  recovery per the documented exception.

---

## MS-expert opinion (priority order for the discussion)

Acceptance lens = numerical equivalence between old/new path.

1. **T1-5 (fabricated `Confidence=HIGH`)** — close first; report-integrity, not an
   equivalence question.
2. **T1-1 (resolver default mismatch)** — align `models.py` dataclass default to
   canonical, or drop the default and force explicit passing. The mismatch is a bug
   independent of current triggering.
3. **T1-3 (legacy scalar in the matrix)** — first get the empirical trigger rate
   for `selected_integration is None`; if non-zero, converge to a single integrator
   so one matrix column has one integration provenance.
4. **T1-4 (VERY_LOW → counted)** — finish the evidence-honesty migration; this is a
   threshold/science decision, best decided together with the typed-decision cutover.
5. **Tier 3 diagnostics drift / silent rollback read** — affects diagnostic output
   and *retirement-decision evidence*; medium, but it can mislead a "should we
   retire" judgment.
6. **Tier 2 dead code** — low risk; retire via the existing exit rules. **Correct
   the seams, do not rewrite the pipeline.**

## Open product-direction questions (for Codex)

1. **Integration provenance:** is a single integrator the product goal, or is the
   legacy scalar fallback (T1-3) an accepted gap-fill? Needs the empirical
   `selected_integration is None` rate first.
2. **Detection threshold:** should VERY_LOW-confidence peaks count as detected
   (T1-4)? This is where legacy confidence and the new typed-evidence successor
   disagree in spirit.
3. **Resolver authority:** is `legacy_savgol` slated for the same raise-on-use
   retirement as `linear_edge` / `arbitrated`, or kept as a fallback? That decides
   whether T1-1's `getattr(..., "legacy_savgol")` fallbacks stay.
4. **QC vs sample peak picker (T1-2):** confirm the independent QC resolver is
   intentional and that no downstream analysis compares QC area to sample area.

## Verification status

| ID | Claim | How verified |
|----|-------|--------------|
| T1-1 | resolver default `legacy_savgol` vs `region_first_safe_merge` | direct read of both files |
| T1-2 | QC hardcodes `local_minimum` | direct read `pipeline_extraction.py:114-127` |
| T1-3 | legacy scalar fallback exists & writes `alignment_owner_scalar_legacy` | direct read `owner_matrix.py:91-102`; **trigger frequency unverified** |
| T1-4 | `legacy_confidence_review` injected for VERY_LOW | injection verified `result_assembly.py:764-765`; **downstream→counted per Agent C, not re-verified** |
| T1-5 | `_wide_to_long_rows` hardcodes `Confidence=HIGH`, no projection | direct read `workbook_inputs.py:29-56` |
| Tier 2/3 | dead-code, diagnostics drift, contract gaps | agent-reported with file:line; not all personally re-read |

## Key files

- `xic_extractor/configuration/models.py:17` — resolver default (T1-1)
- `xic_extractor/settings_schema.py:27` — canonical default (T1-1)
- `xic_extractor/instrument_qc/pipeline_extraction.py:114-127` — QC resolver hardcode (T1-2)
- `xic_extractor/alignment/owner_matrix.py:91-102` — legacy scalar fallback (T1-3)
- `xic_extractor/extraction/result_assembly.py:764-765` — legacy_confidence_review (T1-4)
- `xic_extractor/output/workbook_inputs.py:29-56` — fabricated Confidence=HIGH (T1-5)
- `tools/diagnostics/area_integration_uncertainty_io.py:153-157` — silent rollback read (Tier 3)
- `tools/diagnostics/asls_truth_validation_inputs.py:960` — encoding drift (Tier 3)
- `docs/superpowers/plans/2026-06-01-cleanup-retirement-one-pass-goal.md` — retirement contract
