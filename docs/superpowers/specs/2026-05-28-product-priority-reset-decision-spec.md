# Product Priority Reset: Qualitative Selection Decision Contract

**Date:** 2026-05-28
**Status:** decision spec, not implementation
**Working branch:** `codex/product-priority-reset`

## Verdict

Handoff productization must stop accepting low-impact scaffold as mainline
progress. The next mainline decision is qualitative selected-peak acceptance:

> Can the current selected peak, identity, RT explanation, and boundary behavior
> support the next narrow production-behavior PR?

This spec does not declare product-wide production readiness. It authorizes only
one next action: build or run a narrow qualitative acceptance gate that resolves
the decision above as `GO`, `NO_GO`, or `INCONCLUSIVE`.

## Current State To Preserve

- PR70 matrix handoff behavior is already `production_ready` for its scoped
  change: `alignment_matrix.tsv` and optional workbook Matrix projection consume
  `AlignedCell.matrix_area`, which prefers selected `IntegrationResult` area and
  falls back only through the named legacy path.
- PR70 does not retire unrelated legacy paths, promote a new baseline policy,
  change resolver defaults, or claim Phase2 cleanup readiness.
- AsLS Phase 1 is closed for the supported audit-promotion scope. Baseline-driven
  area differences are not blockers only when identity, RT, boundary, and primary
  delivery outputs remain accepted.
- Linear-edge deletion remains blocked until its own retirement prerequisites are
  satisfied.
- CWT P5a remains audit-only evidence honesty. It must not be treated as a
  production scoring, boundary, or selector source in this reset.

## Supersession

This spec consumes the already-completed PR70 matrix handoff behavior. It does
not replace, reopen, or revalidate PR70.

Until `QUAL_SELECTION_READY_FOR_NEXT_BEHAVIOR_PR` resolves, this spec supersedes
older next-action wording that would continue scaffold, dual-write, writer,
report, or Phase2 cleanup work as handoff mainline progress. Method-preserving
cleanup may occur only as explicitly approved non-mainline maintenance that does
not touch the product-decision write surface and is not counted as Phase2
progress.

The only current handoff mainline decision is the qualitative selected-peak gate
defined below. This PR is not merge-ready until that gate returns exactly one
classification.

## Mainline Entry Rule

A future handoff PR may enter the mainline only if it closes one product
decision, changes production behavior under an approved contract, removes a
misleading legacy path, or strengthens the downstream machine contract.

The following are not handoff mainline progress by themselves:

- wording-only source-of-truth cleanup;
- writer/header/projection tests that do not affect the selected production
  path;
- debug TSV, HTML, XLSX, or sidecar expansion;
- broad architecture scaffolding without a named consumer migration;
- external-tool shadow comparison that cannot close a `GO` / `NO_GO` decision.

## Operational Gate Contract

### Decision

Resolve:

`QUAL_SELECTION_READY_FOR_NEXT_BEHAVIOR_PR`

This means the accepted row set shows coherent selected peak, identity, RT
explanation, boundary ownership, and primary matrix delivery for the current
production-equivalent alignment path. A `GO` authorizes writing the next narrow
behavior PR. It is not a claim that the whole product is production-ready.

The main agent may assemble the gate note and subagents may review it, but the
final `GO` / `NO_GO` / `INCONCLUSIVE` classification must be stated in the gate
note and accepted by the user before it is used to start a behavior-changing PR.

### Scope

The gate scope is fixed to the current accepted validation surfaces:

- 8RAW discovery index:
  `C:\Users\user\Desktop\XIC_Extractor\local_validation_artifacts\discovery\accepted_p8b\8raw\discovery_batch_index.csv`
- 85RAW discovery index:
  `C:\Users\user\Desktop\XIC_Extractor\local_validation_artifacts\discovery\accepted_p8b\85raw\discovery_batch_index.csv`
- RAW root: `C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R`
- DLL dir: `C:\Xcalibur\system\programs`
- Python runtime: `C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe`
  unless the active worktree has a verified `.venv` junction.
- Machine delivery files: `alignment_matrix.tsv`, `alignment_review.tsv`,
  `alignment_cells.tsv`

The Phase 1 gate must use this fixed review manifest:

| Kind | Sample / scope | Label or control | Decision / family / seed | Required oracle |
| --- | --- | --- | --- | --- |
| positive ISTD | `BenignfatBC1151_DNA` | `d3-5-hmdC` | `ICD000285` / `ICF000285` / `BenignfatBC1151_DNA#5012` | V0.4 positive-control PASS; targeted ISTD benchmark PASS; selected peak / boundary row coherent |
| positive ISTD | `BenignfatBC1055_DNA` | `d3-5-medC` | `ICD000092` / `ICF000092` / `BenignfatBC1055_DNA#9537` | V0.4 positive-control PASS; 8RAW benchmark PASS; 85RAW WARN explained without selected-peak failure |
| positive ISTD | `BenignfatBC1055_DNA` | `15N5-8-oxodG` | `ICD000206` / `ICF000206` / `BenignfatBC1055_DNA#13111` | V0.4 positive-control PASS; strict benchmark hotfix PASS; boundary restoration row below remains coherent |
| positive ISTD | `TumorBC2312_DNA` | `d3-N6-medA` | `ICD002276` / `ICF002276` / `TumorBC2312_DNA#21195` | V0.4 positive-control PASS; large RT delta explained by accepted target drift / same-surface evidence |
| positive ISTD | `NormalBC2263_DNA` | `d3-dG-C8-MeIQx` | `ICD001456` / `ICF001456` / `NormalBC2263_DNA#35245` | V0.4 positive-control PASS; targeted ISTD benchmark PASS |
| identity decoy aggregate | reviewed controls manifest hash `A08F197E31E5F33C35035AB082488DC9F0B5494075BF6930CF9F4EBA42DE1FC6` | `identity_decoy_specificity` | 3 reviewed decoys, 0 promoted, 3/3 rejected | V0.4 `reviewed_controls_manifest=pass` and `identity_decoy_specificity=pass` |
| prior blocker | `NormalBC2312_DNA` | `15N5-8-oxodG` | `FAM000538` | hotfix boundary restoration remains `peak_start_rt=16.3855`, `peak_end_rt=16.86`, status PASS |
| prior warning | `NormalBC2312_DNA` | `d3-N6-medA` | target-derived seed from `config/MixSTDs.csv` m/z / RT / NL and stable 8RAW discovery candidates | mixed-surface warning remains explained only if the current alignment row is uniquely addressable by `source_candidate_id` or an equivalent current artifact key |

The individual reviewed decoy row IDs are not recorded in the current
authoritative handoff note. Do not invent them. If row-level decoy inspection is
needed, first restore the reviewed controls manifest matching the hash above;
otherwise decoy evidence is the aggregate V0.4 acceptance row only.

The `d3-N6-medA / NormalBC2312_DNA` prior-warning row is not allowed to pass as
note-only GO support. The gate may derive a row key from `config/MixSTDs.csv`
(`label=d3-N6-medA`) plus the accepted 8RAW discovery candidates, then verify
that the current alignment selected row matches exactly one such
`source_candidate_id`. If no unique current row key exists, return
`INCONCLUSIVE_NEEDS_NAMED_MINIMAL_EVIDENCE` with that row as the blocker.

Controls remain validation yardsticks. They must not be used as identity
promotion evidence.

### Freshness Rule

Before using an artifact as gate evidence:

- the discovery index must live under `local_validation_artifacts/`, not a
  sibling worktree `output/`;
- the discovery index must contain no stale `.worktrees/<branch>/output/`
  `candidate_csv` or `review_csv` references;
- 8RAW and 85RAW runs must pass expected sample count preflight;
- reused artifacts must record the command shape, sample count, output path, and
  primary-file hash or byte-parity result;
- if 8RAW is `INCONCLUSIVE`, do not run 85RAW just to inspect what happens.
- if 8RAW is `NO_GO`, stop and fix the named selection / identity / boundary
  failure before any 85RAW run;
- if 8RAW is `GO`, reuse existing fresh 85RAW parity evidence first. In this PR,
  run a new foreground 85RAW refresh only if existing 85RAW evidence is stale,
  the refresh can change the Phase 1 classification, and the active worktree has
  a verified `.venv` runner compatible with `--expected-sample-count 85`.
  Otherwise return `INCONCLUSIVE_NEEDS_NAMED_MINIMAL_EVIDENCE` with the missing
  executable preflight as the blocker instead of relaunching a known-bad shape.

Use the documented validation-minimal surface by default:

```powershell
& "C:\Users\user\Desktop\XIC_Extractor\.venv\Scripts\python.exe" -m scripts.run_alignment `
  --discovery-batch-index <accepted-discovery-batch-index.csv> `
  --raw-dir C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R `
  --dll-dir C:\Xcalibur\system\programs `
  --output-dir <task-specific-output-dir> `
  --expected-sample-count <8-or-85> `
  --output-level validation-minimal `
  --resolver-mode region_first_safe_merge `
  --backfill-scope production-equivalent `
  --audit-evidence-mode none `
  --performance-profile validation-fast `
  --owner-backfill-window-strategy super-window `
  --owner-backfill-superwindow-span-factor 2 `
  --timing-output <task-specific-output-dir>\timing.json `
  --timing-live-output <task-specific-output-dir>\timing.live.json
```

The command requests `region_first_safe_merge` because this is the handoff-facing
resolver context being tested. The authoritative production-equivalent alignment
metadata is still expected to record `resolver_mode=local_minimum`: current
`scripts.run_alignment` intentionally maps `region_first_safe_merge` back to
`local_minimum` for production matrix output while safe-merge remains audit
context. A gate note must treat `local_minimum` metadata as expected, not as a
command-shape failure.

### Existing Oracles

The next gate must reuse existing oracles before creating any new diagnostic:

- PR70 matrix handoff validation note and primary artifact parity;
- targeted ISTD benchmark;
- P1 area / RT gate;
- identity coherence V0.4 reviewed controls and decoys;
- evidence spine consistency reports, using same-surface comparisons where
  mixed-surface warnings were previously identified;
- area integration uncertainty audit;
- P2b AsLS promotion gate and P2c truth-validation outputs for baseline-related
  area interpretation;
- manual EIC only for named `INCONCLUSIVE` rows.

Authoritative references for the first Phase 1 pass:

| Oracle | Authoritative reference | Required evidence |
| --- | --- | --- |
| PR70 matrix handoff | `docs/superpowers/notes/2026-05-28-pr70-alignment-matrix-handoff-raw-validation-note.md` | 8RAW and 85RAW primary artifact parity for `alignment_matrix.tsv`, `alignment_review.tsv`, `alignment_cells.tsv` |
| Resolver / selected-row hotfix | `docs/superpowers/notes/2026-05-24-resolver-default-switch-validation-note.md` | strict ISTD hotfix PASS; `15N5-8-oxodG` boundary restoration; `d3-N6-medA` same-surface explanation |
| Identity coherence | `docs/superpowers/validation/identity_coherence_v04_8raw_acceptance_handoff.md` | reviewed controls manifest hash, 5/5 positive controls PASS, 3/3 decoys rejected |
| ASLS / baseline interpretation | `docs/superpowers/notes/2026-05-27-asls-minimal-closeout-note.md` | area shift alone is not a blocker when identity, RT, boundary, and primary delivery are accepted |
| Diagnostic inventory | `tools/diagnostics/INDEX.md` | existing gate / audit tools considered before any new diagnostic |

## Gate Rules

### `GO`

Return `GO_FOR_NEXT_NARROW_BEHAVIOR_PR` when all row-level qualitative checks
pass and the next step is a narrow behavior PR. Return
`GO_FOR_NEXT_PRODUCT_DECISION_PR` when the same row-level checks pass and the
post-change 85RAW watch also shows no new named qualitative blocker.

Both GO states require:

- artifact freshness checks pass;
- every required review row has row-addressable evidence for selected peak,
  identity, RT explanation, and boundary ownership;
- the `d3-N6-medA / NormalBC2312_DNA` prior-warning row resolves to exactly one
  current alignment row by `source_candidate_id` or an equivalent current
  artifact key;
- no required row has active wrong-peak, wrong-identity, unexplained RT drift, or
  boundary ownership failure;
- known area shifts are explained by baseline/integration behavior and do not
  contradict selected peak, identity, RT, boundary, or primary matrix delivery;
- primary machine delivery remains `alignment_matrix.tsv`, `alignment_review.tsv`,
  and `alignment_cells.tsv`; no large human report is required to make the
  decision.

The stronger `GO_FOR_NEXT_PRODUCT_DECISION_PR` additionally requires:

- the current production behavior change has a foreground 85RAW
  `validation-minimal` run with heartbeat artifacts;
- single-dR production gate diagnostics show no risky weak-seed, extreme
  backfill, or duplicate rescue-pressure hard gate candidate;
- any remaining strict area benchmark failure is explicitly classified as a
  quantitative follow-up surface, not a qualitative delivery blocker.

### `NO_GO`

Return `NO_GO_FIX_SELECTION_OR_BOUNDARY_FIRST` if any required row proves:

- selected peak is wrong;
- identity is incoherent or contradicted by reviewed controls / decoys;
- RT drift is not explained by existing target RT diagnostics or same-surface
  comparison;
- boundary is wide or misplaced enough to change apex ownership, identity
  support, or integration ownership;
- primary matrix delivery is stale, missing, or inconsistent with the reviewed
  selected row.

### `INCONCLUSIVE`

Return `INCONCLUSIVE_NEEDS_NAMED_MINIMAL_EVIDENCE` only when the blocking unknown
is one pass containing at most three named evidence items. The output must
identify for each item:

- sample;
- target label or family / decision id;
- m/z and RT or window;
- current status;
- missing evidence;
- cheapest allowed next check.

Allowed follow-up is limited to minimal artifact refresh or manual EIC for the
named row. A new broad diagnostic, new report surface, or new external tool is
not allowed unless it is demonstrably the cheapest way to answer that single
missing item.

If a second consecutive `INCONCLUSIVE` is reached after the allowed minimal
follow-up, stop and reclassify as `NO_GO_FIX_SELECTION_OR_BOUNDARY_FIRST` with a
named blocker list. Do not keep adding manual EIC rows one at a time.

## Stop Rules

Until this decision resolves:

- do not start Phase2 cleanup as a mainline task;
- do not add ML/DL, a new resolver family, or broad model-selection architecture;
- do not add writer/report TSV/XLSX/HTML surfaces as proof of product progress;
- do not use external untargeted tools as blockers for targeted ISTD identity
  unless they identify a concrete wrong-peak or wrong-identity row;
- do not treat area shift alone as a qualitative blocker when identity, RT,
  boundary, and primary output are accepted.

## Mode Labels For Adjacent Work

- ASLS / linear-edge: next quantitative behavior candidate, but linear-edge
  retirement remains blocked by its own Tier C / retirement prerequisites.
- Boundary width: eligible next behavior candidate if the qualitative gate finds
  row-level ownership failure or over-wide boundaries that affect selection.
- CWT: audit-only under P5a. A real CWT upgrade would be a separate hypothesis
  source decision, not an implicit production input.
- Phase2 cleanup: deferred as handoff mainline. Method-preserving cleanup may
  occur only as explicitly approved non-mainline maintenance before this gate
  resolves.

## Phase Roadmap

This PR is the Phase 1 PR. It must include the decision contract, a short
roadmap, the Phase 1 implementation plan / goal, and the Phase 1 gate result
before merge. It must not include Phase 2 behavior changes.

### Phase 1: Qualitative Selection Acceptance Gate

Resolve `QUAL_SELECTION_READY_FOR_NEXT_BEHAVIOR_PR` using the operational gate
contract above. This phase may refresh minimal artifacts or perform named-row
manual EIC review only when the existing artifacts are stale or inconclusive.

Output: one gate note with a single machine-readable line:

```markdown
Final Classification: <GO_FOR_NEXT_NARROW_BEHAVIOR_PR | GO_FOR_NEXT_PRODUCT_DECISION_PR | NO_GO_FIX_SELECTION_OR_BOUNDARY_FIRST | INCONCLUSIVE_NEEDS_NAMED_MINIMAL_EVIDENCE>
```

The note may mention why the other classifications do not apply, but the
`Final Classification:` line is the only authoritative classification field.

If Phase 1 returns `GO`, the gate note must name one recommended next product
decision or Phase 2 PR target and justify why it follows from the reviewed rows.

### Phase 2: First Production Behavior Move

Phase 2 is chosen only after Phase 1:

- If Phase 1 returns `GO`, choose the highest-value behavior decision from the
  accepted evidence. The expected candidates are ASLS / linear-edge behavior,
  boundary ownership behavior, or CWT productization if the evidence points
  there.
- If Phase 1 returns `NO_GO`, fix the named selector, identity, RT explanation,
  or boundary failure first.
- If Phase 1 returns `INCONCLUSIVE`, resolve only the named missing evidence and
  re-run the Phase 1 classification. Do not start broad model selection or new
  diagnostic infrastructure.

### Phase 3: Product-Led Phase2 Cleanup / Retirement

Phase 3 consumes the original Phase2 cleanup work, but only after a product
behavior decision has settled the relevant legacy path.

- If ASLS / linear-edge behavior is settled, use the original cleanup specs as
  input for rollback-column deprecation, C5 single-entry integration, C1a
  relocation, and eventual C1b retirement.
- If boundary behavior is settled, clean only the boundary heuristics, audit
  labels, or legacy compatibility paths made obsolete by that behavior.
- If CWT remains audit-only, do not treat CWT as a cleanup target. It must either
  stay externalized as audit evidence or receive a separate production hypothesis
  source decision.

Phase 3 must not run as an independent cleanup track. Cleanup follows product
decisions; it does not decide them.

## Next Step

Write the next goal around this decision contract, not around another scaffold:

1. collect the fixed review rows and artifact freshness evidence;
2. run only the existing oracles needed to classify those rows;
3. return `GO_FOR_NEXT_NARROW_BEHAVIOR_PR`,
   `GO_FOR_NEXT_PRODUCT_DECISION_PR`,
   `NO_GO_FIX_SELECTION_OR_BOUNDARY_FIRST`, or
   `INCONCLUSIVE_NEEDS_NAMED_MINIMAL_EVIDENCE`;
4. choose the next behavior PR only after this classification.
