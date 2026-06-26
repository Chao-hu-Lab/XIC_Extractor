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
> `docs/product/quant-matrix.md` (which values write reported numbers), and
> `docs/product/peak-model-selection.md` (current retirement authority for
> legacy area-integration behavior).

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
| P2 | retired area-integration baseline-method gate (AsLS vs historical linear-edge) |
| P2b | retired AsLS promotion gate (shadow → production) |
| P2c | retired `asls_truth_validation` linear-edge retirement truth gate (Tier A/B1/B2/C) |
| P7 | alignment parity + evidence-chain cost control / stabilization |

## Bucket A — Load-bearing (production runs it; keep regardless of research value)

Not "research" — these are wired into the live pipeline. Do not drop. Current
verification: `scripts/run_alignment.py` still enables the standard-peak
publication runner from preset runtime options, and the built-in `dna_dr` preset
publishes accepted standard-peak values back into the default
`alignment_matrix.tsv` / `alignment_matrix_identity.tsv` surface.

| Module | Why it is load-bearing |
| --- | --- |
| `xic_extractor/diagnostics/standard_peak_backfill_productization.py`, `standard_peak_backfill_chunk_consolidation.py`, `tools/diagnostics/standard_peak_backfill_preset.py` | dna_dr preset standard-peak publication writes back to the production `alignment_matrix.tsv` (`scripts/run_alignment.py` `standard_peak_backfill_enabled` path) |
| `shadow_production_projection.py`, `standard_peak_shadow_activation_inputs.py`, `retained_backfill_evidence_gate.py` | transitive deps of the above publication path |
| `xic_extractor/diagnostics/timing.py` | core timing instrumentation for alignment/discovery pipelines |
| `xic_extractor/peak_detection/legacy_savgol.py` | `resolver_mode=legacy_savgol` is still an accepted compatibility profile (intentional keep) |
| `xic_extractor/alignment/legacy_io.py` | alignment validation pipeline reads legacy workbooks (intentional keep) |

## Bucket B — Decision-closed gates retired from active tooling

These existed to make decisions that have already fired. They are not future
maintenance surfaces. In the 2026-06-12 cleanup pass, active P2/P2b/P2c
linear-edge decision tooling and tests were removed from `tools/diagnostics/`,
`xic_extractor/diagnostics/`, and `tests/`. Old narrative notes can still
mention the historical transition, but active code must not provide a
linear-edge comparator, fallback, or truth gate.

AsLS / linear-edge status is especially closed:

- AsLS is the production baseline integration method for current matrix values.
- `linear_edge` is retired as a selectable baseline method. Current product and
  config surfaces reject it with `LINEAR_EDGE_RETIRED_MESSAGE = "linear_edge
  baseline integration is retired; use asls"`.
- Remaining active-code linear-edge references should be rejection guards only.
  Historical docs may describe the old transition, but they are not runnable
  decision surfaces.
- Missing or challenged current AsLS evidence must be handled by current product,
  boundary, or review contracts. It must not fall back to linear-edge and must
  not reopen P2/P2b/P2c.

| Retired surface | Retirement action |
| --- | --- |
| `p2_asls_shadow_gate.py` + `tests/test_p2_asls_shadow_gate.py` | Deleted from active tooling. The old AsLS-vs-linear-edge shadow comparator is not a current baseline selector. |
| `p2_baseline_truth_audit.py`, `xic_extractor/diagnostics/p2_baseline_truth_audit.py`, `tests/test_p2_baseline_truth_audit.py` | Deleted from active tooling. Old linear-edge comparator columns are no longer an active reader contract. |
| `p2b_asls_promotion_gate.py` + `tests/test_p2b_asls_promotion_gate.py` | Deleted from active tooling. AsLS promotion is complete; new area/boundary/model gates need their own contracts. |
| `asls_truth_validation.py` + `asls_truth_validation_{models,manifests,synthetic,inputs,analysis}.py` + matching tests + `docs/superpowers/fixtures/asls_truth_*` | Deleted from active tooling and fixture artifacts. The P2c linear-edge retirement truth gate is consumed and must not be rerun. |
| `area_integration_uncertainty_*` legacy rollback read | Removed from the active C4 audit path. C4 now uses current reported baseline only and remains a boundary/integration uncertainty audit. |
| `p1_resolver_default_gate.py` | resolver default decision closed. Current public/config token is `region_first_safe_merge`, while alignment production maps that token to `local_minimum`; the gate itself is no longer an active decision surface |
| `backfill_peakhypothesis_raw85_winner_remap.py` | INDEX status: "legacy context only; 2026-06-09 output obsolete"; do not generalize this to the whole PeakHypothesis backfill family |

Note: `region_first_safe_merge` itself and `legacy_savgol` are **intentionally
kept** (public/config token / compatibility resolver), not Bucket B — do not
remove them.

## Bucket C — Open but stuck at evaluation (owner decision per line)

These are not closed. They differ in wiring and maturity, so do not treat the
whole bucket as "dead research." Each needs an owner call: actively pursue,
preserve as opt-in diagnostic/support infrastructure, or retire.

| Research line | Status | Decision needed |
| --- | --- | --- |
| `backfill_peakhypothesis_*` family (12 package modules + 12 CLI facades + matching tests; normal-peak backfill promotion) | trial / `production_candidate`; **not wired into `run_alignment`**. dna_dr only auto-backfills standard peaks, not normal peaks. This is the normal-analyte backfill expansion candidate: evidence rows → require-backfill decisions → activation bridge/acceptance → matrix-diff smoke. | Still want to extend automatic backfill to normal analyte peaks? If yes → this is the priority C line to finish through activation owner, not another 85RAW rerun. If no → define the exact family and retire it deliberately. |
| `backfill_evidence_reconciliation` gallery + `2026-06-07-...-productization-goal.md` | `shadow_ready` support infrastructure. It builds a reconciliation group index plus human review gallery so backfill evidence can move from observability to a reviewed, allowlisted product decision path. It is used by standard-peak backfill as group/index or optional gallery support, but the renderer itself does **not** mutate `alignment_matrix.tsv`, product decisions, or workbook schemas. | Keep as the backfill review/support substrate. Do not promote the gallery itself into product authority; productization must remain a separate allowlist + activation + 8RAW/85RAW validation contract. |
| `xic_extractor/alignment/identity_coherence/*` + validation helpers/plans | functional opt-in production diagnostic. `run_alignment` wires it behind `emit_identity_coherence_diagnostic=False` by default and emits an `identity_coherence/` sidecar without changing the matrix. Existing tests cover opt-in execution, disabled no-op behavior, worker policy forwarding, and error propagation. | Preserve as opt-in diagnostic. Do not pursue default-on/gate behavior unless a future contract defines the falsification policy, expected matrix/public-surface effect, and validation oracle. |
| `area_integration_uncertainty_*` | dormant audit surface; no production gate. The baseline-comparison motivation is partly spent after AsLS/linear-edge closeout, but boundary/integration uncertainty still matters for future abnormal or non-normal peaks where different boundaries on the same peak can materially change area. | Preserve as cold audit oracle. Do not promote to gate now, and do not retire unless a future boundary policy replaces this evidence or explicitly declares it obsolete. |

## Bucket D — Naming opacity (systemic)

The owner's complaint that names do not match behavior is well-founded:

- **P-codes** (`p1_/p2_/p2b_/p2c_/p7_`) carry no behavior meaning — annotate with
  behavior names everywhere (table above is the decode key).
- **Fixture names baked into module names**: the PeakHypothesis backfill family
  has dataset-shaped package modules and matching CLI facades
  (`backfill_peakhypothesis_85raw_*` and `backfill_peakhypothesis_raw85_*`).
  The architecture contract states 8RAW/85RAW are fixtures, **not** architecture
  boundaries; permanent module names should use the role (e.g.
  reference-alignment gate), not the dataset.
- **Stage jargon** (`shadow` / `trial` / `transfer` / `activation` / `promotion`
  / `hypothesis`) is scattered and does not signal experimental-vs-shipped.

## Actioned maintenance decisions

2026-06-12 follow-up after owner agreement on A/B/D:

- Bucket A is now mirrored in `tools/diagnostics/INDEX.md` with load-bearing
  notes for the standard-peak publication path, including
  `standard_peak_backfill_preset.py` as the direct `run_alignment` preset bridge.
- Bucket B is now retired from active linear-edge decision tooling. P2/P2b/P2c
  AsLS-vs-linear-edge gates, tests, and `asls_truth_*` fixtures were removed;
  `linear_edge` remains only as product/config rejection guard text and
  historical documentation.
- Bucket C wording is corrected: C2 is a backfill review/support substrate, C3
  is a functional opt-in diagnostic, and C4 is a cold boundary/integration audit
  that no longer reads linear-edge rollback columns.
- Bucket D is now codified in `docs/architecture-contract.md`: new permanent
  modules and CLI entry points should use product/evidence role names instead of
  fixture-shaped names such as `8raw` / `85raw` or opaque P-codes.
- C1 normal-peak backfill remains the active Bucket C product-expansion question.

## How to refresh this triage

1. Re-confirm the anchor: `grep LINEAR_EDGE_RETIRED_MESSAGE
   xic_extractor/peak_detection/baseline.py`.
2. Re-derive load-bearing set: what `scripts/run_alignment.py` /
   `run_extraction.py` import transitively, plus preset runtime options such as
   `standard_peak_backfill` (Bucket A).
3. Re-read INDEX status notes for "consumed" / "obsolete" / "legacy context"
   markers (Bucket B).
4. For Bucket C, check whether the line's goal/plan note moved past
   `shadow_ready` / `production_candidate`.
