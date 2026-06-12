# Research-Line / Diagnostic-Machinery Triage

**Snapshot date:** 2026-06-12
**Branch when captured:** `cc/framework-improvements` (on top of
`codex/backfill-diagnostics-architecture`)
**Axis:** which accumulated architecture / diagnostics / tests still have
research value (keep) vs are used-up one-shot artifacts (safe to stop
maintaining). This is a maintenance triage, distinct from the clean-code
inventory and from the numerical dual-system audit.

> **This is a dated snapshot. Verify before acting.** The repo changes fast
> (Codex-driven) and notes lag code. Before deleting anything in Bucket B,
> re-confirm the cited evidence still holds. Related docs:
> `docs/diagnostic-ledger.md` (rerun policy),
> `docs/superpowers/notes/2026-06-05-dual-system-and-retired-path-product-behavior-audit-note.md`
> (which legacy paths still decide reported numbers),
> `docs/superpowers/notes/2026-06-01-phase7-linear-edge-deletion-note.md` and
> `2026-06-01-phase6b-final-retirement-go-note.md` (retirement authority).

## Anchor finding

The **AsLS-vs-linear-edge decision is closed**. `linear_edge` baseline
integration is retired and deleted from production:
`xic_extractor/peak_detection/baseline.py:17` defines
`LINEAR_EDGE_RETIRED_MESSAGE = "linear_edge baseline integration is retired; use
asls"`. The dual-system audit (2026-06-05) lists this retirement as **clean**
(rejection guard only, no behavioral leak). Therefore every P2-family tool that
exists to adjudicate AsLS vs linear-edge is a fired one-shot gate — see Bucket B.

The phase-gate **P-codes are not behavior-descriptive**; the owner could not
recall what P2 was. Decode:

| Code | Behavior |
| --- | --- |
| P1 | resolver default switch (`local_minimum` vs `region_first_safe_merge`) |
| P2 | area-integration baseline method (AsLS vs historical linear-edge) |
| P2b | AsLS promotion gate (shadow → production) |
| P2c | `asls_truth_validation` — linear-edge retirement truth gate (Tier A/B1/B2/C) |
| P7 | alignment parity + evidence-chain cost control / stabilization |

## Bucket A — Load-bearing (production runs it; keep regardless of research value)

Not "research" — these are wired into the live pipeline. Do not drop.

| Module | Why it is load-bearing |
| --- | --- |
| `xic_extractor/diagnostics/standard_peak_backfill_productization.py`, `standard_peak_backfill_chunk_consolidation.py`, `tools/diagnostics/standard_peak_backfill_preset.py` | dna_dr preset standard-peak publication writes back to the production `alignment_matrix.tsv` (`scripts/run_alignment.py` `standard_peak_backfill_enabled` path) |
| `shadow_production_projection.py`, `standard_peak_shadow_activation_inputs.py`, `retained_backfill_evidence_gate.py` | transitive deps of the above publication path |
| `xic_extractor/diagnostics/timing.py` | core timing instrumentation for alignment/discovery pipelines |
| `xic_extractor/peak_detection/legacy_savgol.py` | `resolver_mode=legacy_savgol` is still an accepted compatibility profile (intentional keep) |
| `xic_extractor/alignment/legacy_io.py` | alignment validation pipeline reads legacy workbooks (intentional keep) |

## Bucket B — Used-up / one-shot (decision closed; stop maintaining)

These exist to make a decision that has already fired. Keep as archival audit
trail if desired, but they will not re-run and need no maintenance.

| Module / asset | Evidence it is spent |
| --- | --- |
| `p2_asls_shadow_gate.py` | AsLS shadow vs retired linear-edge |
| `p2_baseline_truth_audit.py` (+ `xic_extractor/diagnostics/p2_baseline_truth_audit.py`) | adjudicates AsLS vs linear-edge baseline; decision closed |
| `p2b_asls_promotion_gate.py` | AsLS already promoted to production |
| `asls_truth_validation.py` + `asls_truth_validation_{models,manifests,synthetic,inputs,analysis}.py` | INDEX status: "retirement authority **consumed** by the 2026-06-01 Phase 6b/Phase 7 closeout" |
| `docs/superpowers/fixtures/asls_truth_*` (Tier A artifacts tree, plots, manifests, locks) | fixtures for the spent P2c gate (sizeable footprint) |
| `p1_resolver_default_gate.py` | resolver default decision closed (`keep_opt_in`: `local_minimum` default, region-first opt-in) |
| `backfill_peakhypothesis_raw85_winner_remap.py` | INDEX status: "legacy context only; 2026-06-09 output obsolete" |

Note: `region_first_safe_merge` itself and `legacy_savgol` are **intentionally
kept** (opt-in / compatibility), not Bucket B — do not remove them.

## Bucket C — Open but stuck at evaluation (owner decision per line)

Not production-wired, not closed — parked at trial/shadow/candidate stage. Each
needs an owner call: still pursuing it, or drop?

| Research line | Status | Decision needed |
| --- | --- | --- |
| `backfill_peakhypothesis_*` family (13 files; normal-peak backfill promotion) | trial / `production_candidate`; **not wired into `run_alignment`** (only its own tests + CLI import it). dna_dr only auto-backfills standard peaks, not normal peaks | Still want to extend backfill to normal peaks? If no → whole family is droppable |
| `backfill_evidence_reconciliation` gallery + `2026-06-07-...-productization-goal.md` | `shadow_ready`; gallery done, promotion only on manual slice | Productize reconciliation, or leave as diagnostic gallery? |
| `xic_extractor/alignment/identity_coherence/*` + 8 implementation plans | plans defined, no completion / validation note found | Still active, or superseded by the shared evidence spine? |
| `area_integration_uncertainty_*` | audit surface; no production gate | Stay audit-only, or promote to a gate? |

## Bucket D — Naming opacity (systemic)

The owner's complaint that names do not match behavior is well-founded:

- **P-codes** (`p1_/p2_/p2b_/p2c_/p7_`) carry no behavior meaning — annotate with
  behavior names everywhere (table above is the decode key).
- **Fixture names baked into module names**: the 7 `backfill_peakhypothesis_raw85_*`
  modules embed `raw85`. The architecture contract states 8RAW/85RAW are
  fixtures, **not** architecture boundaries; permanent module names should use
  the role (e.g. reference-alignment gate), not the dataset.
- **Stage jargon** (`shadow` / `trial` / `transfer` / `activation` / `promotion`
  / `hypothesis`) is scattered and does not signal experimental-vs-shipped.

## How to refresh this triage

1. Re-confirm the anchor: `grep LINEAR_EDGE_RETIRED_MESSAGE
   xic_extractor/peak_detection/baseline.py`.
2. Re-derive load-bearing set: what `scripts/run_alignment.py` /
   `run_extraction.py` import transitively (Bucket A).
3. Re-read INDEX status notes for "consumed" / "obsolete" / "legacy context"
   markers (Bucket B).
4. For Bucket C, check whether the line's goal/plan note moved past
   `shadow_ready` / `production_candidate`.
