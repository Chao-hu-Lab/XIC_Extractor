# Product Priority Reset: Qualitative Selection Decision Contract

**Date:** 2026-05-28
**Status:** decision + same-PR behavior correction spec
**Working branch:** `codex/product-priority-reset`

## Verdict

Handoff productization must stop accepting low-impact scaffold as mainline
progress. The next mainline decision is qualitative selected-peak acceptance:

> Can the current selected peak, identity, RT explanation, and boundary behavior
> support the next narrow production-behavior PR?

This spec does not declare product-wide production readiness. It now authorizes
one same-PR correction because the first gate pass already resolved to `NO_GO`:
replace the weak-seed / high-backfill-dependency promotion proxy with a
cell-evidence-backed untargeted promotion policy, and recalibrate discovery
evidence scoring only where it feeds that promotion policy.

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
- The post-gate next action is the tiered backfill machine-decision PR. It must
  keep normal downstream correction/statistics on the primary-only
  `alignment_matrix.tsv`, while exposing provisional rows to review/gate
  diagnostics through a deterministic projection contract.

## Supersession

This spec consumes the already-completed PR70 matrix handoff behavior. It does
not replace, reopen, or revalidate PR70.

Until `QUAL_SELECTION_READY_FOR_NEXT_BEHAVIOR_PR` resolves, this spec supersedes
older next-action wording that would continue scaffold, dual-write, writer,
report, or Phase2 cleanup work as handoff mainline progress. Method-preserving
cleanup may occur only as explicitly approved non-mainline maintenance that does
not touch the product-decision write surface and is not counted as Phase2
progress.

The current handoff mainline decision is still qualitative selected-peak and
matrix-delivery acceptance. This PR is not merge-ready until the gate returns
exactly one classification after the cell-evidence-backed promotion correction
is implemented and reviewed.

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
  `local_validation_artifacts/discovery/accepted_p8b/8raw/discovery_batch_index.csv`
- 85RAW discovery index:
  `local_validation_artifacts/discovery/accepted_p8b/85raw/discovery_batch_index.csv`
- RAW root: `$env:XIC_RAW_ROOT`
- DLL dir: `$env:THERMO_RAWFILE_READER_DLL_DIR`
- Python runtime: `.venv\Scripts\python.exe` from the active worktree, after
  verifying that `.venv` exists or is a junction to the canonical repo runtime.
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
Test-Path .venv\Scripts\python.exe
.venv\Scripts\python.exe -m scripts.run_alignment `
  --discovery-batch-index <accepted-discovery-batch-index.csv> `
  --raw-dir $env:XIC_RAW_ROOT `
  --dll-dir $env:THERMO_RAWFILE_READER_DLL_DIR `
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
| Resolver / selected-row hotfix | `retired-provenance:230f58c7688e` | strict ISTD hotfix PASS; `15N5-8-oxodG` boundary restoration; `d3-N6-medA` same-surface explanation |
| Identity coherence | `docs/superpowers/validation/identity_coherence_v04_8raw_acceptance_handoff.md` | reviewed controls manifest hash, 5/5 positive controls PASS, 3/3 decoys rejected |
| ASLS / baseline interpretation | `retired-provenance:65420d0c9a87` | area shift alone is not a blocker when identity, RT, boundary, and primary delivery are accepted |
| Diagnostic inventory | `tools/diagnostics/INDEX.md` | existing gate / audit tools considered before any new diagnostic |

## Gate Rules

## Same-PR Behavior Correction: Option B

The first Phase 1 implementation restored primary delivery for the reviewed
`d3-N6-medA` case, but post-implementation review hardened the trusted-seed
contract and reclassified the same artifacts as `NO_GO` because several primary
rows still depended on weak-seed / high-backfill promotion proxies. The next
change stays in this PR and replaces that proxy with a cell-evidence-backed
promotion policy.

### Scope Boundary

This correction touches only untargeted discovery / alignment matrix promotion:

- in scope: discovery evidence components that feed untargeted family promotion,
  single-dR weak-seed / high-backfill-dependency classification, primary matrix
  promotion reasons, tests, and validation notes;
- out of scope: targeted extractor peak picking, targeted workbook behavior,
  targeted `peak_scoring.py` weights, ASLS / linear-edge production promotion,
  CWT production behavior, resolver defaults, and baseline defaults;
- targeted evidence may be used only as a benchmark, manual-truth example, or
  validation oracle. Targeted pass/fail rules must not become untargeted
  production identity logic.

The manual `TumorBC2289_DNA / d3-5-medC` and
`TumorBC2290_DNA / d3-5-medC` EIC examples illustrate a DDA-limited MS2 case:
coherent MS1 / RT / local-apex evidence can support a backfilled cell even when
MS2 seed-event evidence differs between adjacent samples. They may be cited in
the validation note, but they are not required code fixtures for this PR.

Targeted peak scoring is a follow-up issue, not part of this PR. The issue
should be titled `Revisit targeted peak scoring weights with DDA-limited ISTD
examples` and should evaluate `no_ms2`, `ms2_trace_weak`, RT prior, shape, and
CWT support using `TumorBC2289_DNA / d3-5-medC`,
`TumorBC2290_DNA / d3-5-medC`, and any later reviewed ISTD examples.

### Promotion Policy

Backfill execution remains cell-level. The code must not reinterpret owner
backfill as filling a whole family at once. The promotion gate must distinguish:

- cell-level evidence: each rescued cell's RT, local apex, MS1 shape, scan
  support, local dominance, and candidate-aligned chemical evidence;
- row-level risk: family rescue burden, detected / rescued counts, duplicate
  pressure, weak-seed pressure, and review priority.

Allowed production promotion paths:

- `minimum detected support`: high-backfill promotion requires either at least
  two detected identity cells or one detected seed plus product-authorized
  same-peak rescue evidence. A single detected seed can remain visible as a
  risky provisional row, but cannot be promoted only because owner backfill found
  local MS1 peaks in other samples;
- `RT + chemical`: the cell has candidate-aligned fragment, product, or neutral
  loss evidence in the same selected region;
- `RT + MS1 shape`: DDA / MS2 evidence is weak or absent, but the rescued cell
  matches the detected-seed or family shape and has acceptable local apex
  support;
- `RT + MS1 continuity`: the selected apex is inside the expected local RT
  region, local apex support is present, neighboring MS1 interference is below
  the blocking threshold, and at least one additional MS1 support signal is
  present: acceptable scan support, trace continuity, selected-peak dominance,
  or shape similarity tied to detected-seed / family evidence.

Family-level rescue burden no longer hard-blocks production by itself. It may
emit a warning flag, lower identity confidence, cap promotion confidence, or
raise review priority. It becomes a hard block only when paired with missing or
negative cell-level evidence.

Hard blocks:

- `q_detected == 0` / rescue-only row;
- duplicate claim pressure for the same sample peak;
- local apex outside the allowed RT region;
- high neighboring MS1 interference without a supported selected apex;
- low MS1 assessable coverage that prevents shape / local-apex evaluation;
- extreme backfill burden with weak or unavailable cell-level support.

The implementation must keep machine-readable reasons, not only PASS / FAIL. The
required row-level decision surface is `alignment_review.tsv` using its existing
`identity_reason` and `row_flags` columns unless an approved implementation plan
explicitly adds a new public schema. Diagnostics or sidecars may contain detailed
cell evidence, but they cannot be the only place where the production decision
reason exists. If a sidecar is used, it must be versioned, required by the gate,
and covered by contract tests.

Canonical `identity_reason` values:

- `cell_evidence_supported_backfill`;
- `dda_limited_ms2_but_ms1_shape_supported`;
- `neighboring_ms1_interference_blocked`;
- `low_ms1_assessable_coverage_blocked`;
- `rescue_only_blocked`.

Supplemental `row_flags` modifiers:

- `high_backfill_dependency_capped`;
- preserved existing risk context such as `rescue_heavy` and `weak_seed`.

Reason placement:

- `identity_reason` carries the canonical final production or blocking reason for
  any row whose decision changes because of this policy. Supported rescued-heavy
  production rows use `cell_evidence_supported_backfill` or
  `dda_limited_ms2_but_ms1_shape_supported`. Blocked rows use the matching
  `_blocked` reason.
- `row_flags` carries supplemental modifiers and preserved risk context, such as
  `rescue_heavy`, `weak_seed`, and `high_backfill_dependency_capped`.
- `primary_evidence` continues to describe the upstream evidence source, such as
  owner / family evidence. It must not be overloaded with promotion-policy
  verdicts.

### Discovery Scoring Role

Discovery `evidence_score` remains useful for ranking and summaries. This PR
must not globally retune total `evidence_score` semantics. Instead, it adds or
derives promotion-only gate components that prevent total score from becoming
the only trusted-seed or production-promotion criterion. The gate should consume:

- MS1 presence and local MS1 peak quality;
- scan support and trace continuity;
- RT coherence relative to seed / family / local apex;
- candidate-aligned chemical evidence;
- DDA-limited support where missing MS2 can be explained by coherent MS1 shape
  and local apex;
- neighboring interference or low selected-peak dominance.

Scoring changes are bounded to promotion use:

- owner-backfill cells must emit scan support from the production XIC trace and
  selected boundary. `trace_quality=owner_backfill` is provenance, not support;
- seed-event count and product intensity must not act as veto-like authority in
  DDA-limited cases unless paired with negative cell-level MS1 evidence;
- MS1 shape, scan support, local apex support, selected-peak dominance, and low
  interference become gate-readable evidence components;
- keep total `evidence_score` available for sorting, watch queues, and review
  priority;
- avoid changing targeted `peak_scoring.py` or targeted workbook output.

If public TSV schemas cannot safely accept new columns in this PR, use typed
internal summaries or sidecar diagnostics. Production decisions must still cite
component reasons in `alignment_review.tsv` rather than only total score. Any
implementation that changes the emitted `evidence_score` value itself must first
add a before / after ranking collateral table and an explicit allowed-delta rule;
the default plan should avoid that global score change.

### Acceptance

8RAW must close first:

- all 13 current `risky_weak_seed_backfill` primary rows are classified by the
  new policy as supported or blocked;
- `FAM000264 / d3-N6-medA` passes only through the general cell-evidence-backed
  policy, not a target or family exception;
- any newly promoted or newly blocked row appears in a collateral table with its
  reason and row-level risk flags.
- `review-only` is not a GO state for these 13 rows. At most three named
  unresolved rows may return `INCONCLUSIVE_NEEDS_NAMED_MINIMAL_EVIDENCE`; more
  than three unresolved rows, or a repeated inconclusive after the named minimal
  check, returns `NO_GO_FIX_SELECTION_OR_BOUNDARY_FIRST`.

85RAW validates generalization:

- all five current 85RAW hardened risky weak-seed rows are classified by the new
  policy;
- strict `AREA_MISMATCH` for known quantitative follow-up rows remains a
  quantitative surface, not a qualitative blocker;
- every 85RAW production status, identity reason, confidence, or row-flag delta
  relative to the pre-correction run must be listed in a delta table, or the gate
  must assert zero delta outside the five named risky rows;
- any unlisted or unexplained production delta is `NO_GO`. Any listed collateral
  delta outside the five named risky rows must include family id, old / new
  status, old / new reason, evidence components, and whether the row was
  supported by cell-level evidence.

Rollback / `NO_GO` conditions:

- promotion can still occur from total `evidence_score` alone;
- rescue-only rows enter production;
- duplicate claim pressure is not blocked or capped;
- local apex / shape / interference cannot be assessed but the row is promoted;
- 8RAW passes only because of a target-specific exception;
- any 85RAW production delta is unlisted or unexplained.

### Required Tests

The implementation plan must include focused tests before RAW validation:

- promotion policy tests proving total `evidence_score` alone cannot promote a
  weak-seed / high-backfill row;
- rescued-cell tests proving `RT + local apex + low interference` without MS1
  shape, scan support, trace continuity, selected-peak dominance, or chemical
  evidence does not promote;
- positive DDA-limited tests proving a rescued cell with RT coherence, MS1 shape
  or continuity, local apex support, and low interference can be promoted with a
  capped / warning reason;
- hard-block tests for rescue-only rows, duplicate claim pressure, low MS1
  assessable coverage, high neighboring interference, and extreme backfill with
  unavailable cell-level support;
- discovery evidence tests proving promotion components can change without
  globally changing emitted total `evidence_score` semantics;
- output contract tests proving `alignment_review.tsv` carries the required
  `identity_reason` / `row_flags` values and that any required sidecar, if
  introduced, has a versioned schema and stable headers;
- delta-table tests proving newly promoted, newly blocked, and reason-changed
  rows are listed with old / new status, old / new reason, and evidence
  components.

Coverage must bind to the production path, not diagnostics alone:

- `tests/test_alignment_matrix_identity.py`, or an explicitly named equivalent,
  must cover changed `include_in_primary_matrix`, `identity_reason`, confidence,
  and `row_flags` behavior through `decide_matrix_identity_row()` /
  `build_matrix_identity_decisions()`;
- `tests/test_single_dr_production_gate_decision_report.py`, or equivalent,
  must prove the hardened gate classifies supported, blocked, and capped rows
  using the same policy as production;
- `tests/test_discovery_evidence.py`, or equivalent, must prove any new
  promotion components do not globally change emitted total `evidence_score`
  semantics unless the implementation explicitly chooses the before / after
  collateral-table path;
- TSV writer / output contract tests must prove `alignment_review.tsv` emits the
  canonical `identity_reason` and supplemental `row_flags` values without adding
  unexpected columns in the no-new-column mode;
- any versioned sidecar introduced by the implementation must have schema/header
  tests and must be required by the gate. Optional diagnostics alone cannot
  satisfy this contract.

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
- no required risky weak-seed / high-backfill row remains `review-only` after
  the allowed named minimal evidence pass;
- known area shifts are explained by baseline/integration behavior and do not
  contradict selected peak, identity, RT, boundary, or primary matrix delivery;
- primary machine delivery remains `alignment_matrix.tsv`, `alignment_review.tsv`,
  and `alignment_cells.tsv`; no large human report is required to make the
  decision.

The stronger `GO_FOR_NEXT_PRODUCT_DECISION_PR` additionally requires:

- the current production behavior change has a foreground 85RAW
  `validation-minimal` run with heartbeat artifacts;
- single-dR production gate diagnostics, interpreted under the new
  cell-evidence-backed policy, show no unsupported weak-seed, unsupported
  extreme-backfill, or duplicate rescue-pressure hard gate candidate;
- 85RAW production status, identity reason, confidence, and row-flag deltas are
  fully listed or asserted zero outside the named risky rows;
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

- Tiered backfill machine decision: immediate next product-decision PR after
  Phase 1b. It should include one-detected-seed provisional retention,
  deterministic projection from existing review/cell fields, tests, and docs.
  It must keep `alignment_matrix.tsv` primary-only and make review/gate
  diagnostics the named consumer for provisional rows.
- ASLS / linear-edge: high-value quantitative behavior candidate. It is
  deferred until after the tiered backfill PR so the quantitative PR can focus
  on area/baseline behavior. Linear-edge retirement remains blocked by its own
  Tier C / retirement prerequisites.
- Boundary width: high-value behavior candidate when row-level ownership failure
  or over-wide boundaries affect selection. It is deferred with ASLS unless a
  new gate names it as the active blocker.
- CWT: audit-only under P5a. A real CWT upgrade would be a separate hypothesis
  source decision, not an implicit production input.
- Phase2 cleanup: deferred as handoff mainline. Method-preserving cleanup may
  occur only as explicitly approved non-mainline maintenance before this gate
  resolves.

## Phase Roadmap

This PR is the Product Priority Reset Phase 1 PR. Because the first gate pass
returned `NO_GO` for weak-seed / high-backfill promotion policy, the PR may also
include the narrow Phase 1b correction defined above. It must include the
decision contract, short roadmap, implementation plan / goal, reviewed Phase 1b
behavior correction, and final gate result before merge. It must not include
unrelated Phase 2 cleanup, ASLS / linear-edge retirement, CWT production
promotion, resolver-default changes, or targeted picker scoring changes.

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

### Phase 1b: Same-PR Promotion Policy Correction

If Phase 1 returns `NO_GO` only because the weak-seed / high-backfill promotion
policy is too proxy-driven, implement Option B in this PR:

- keep owner backfill cell-level;
- replace family-level rescue burden as a standalone veto with
  cell-evidence-backed promotion;
- adjust discovery evidence scoring only where it feeds untargeted promotion;
- preserve machine-readable reasons and collateral promotion tables;
- re-run the Phase 1 gate after implementation review.

### Phase 2: Next Product Behavior Move

Phase 2 is chosen only after Phase 1 / Phase 1b closes:

- If the final gate returns `GO`, the next PR is the tiered backfill
  machine-decision PR.
- The tiered PR must include the complete narrow scope: one-detected-seed
  provisional retention, deterministic projection helper, tests, docs, and
  review/gate diagnostic consumption. It must not add Tier 2 routing, a new
  sidecar, or a three-pipeline split unless the approved plan explicitly proves
  the existing projection cannot express the contract.
- After the tiered PR lands, choose the highest-value remaining behavior
  decision from the accepted evidence. The expected candidates are ASLS /
  linear-edge behavior, boundary ownership behavior, CWT productization if the
  evidence points there, or targeted picker scoring if its follow-up issue is
  accepted as the next product decision.
- If the final gate returns `NO_GO`, fix the named selector, identity, RT
  explanation, boundary, or cell-evidence-backed promotion failure first.
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

Write the next goal around this decision contract and the tiered backfill
machine-decision PR, not around another scaffold:

1. collect the fixed review rows and artifact freshness evidence;
2. run only the existing oracles needed to classify those rows;
3. return `GO_FOR_NEXT_NARROW_BEHAVIOR_PR`,
   `GO_FOR_NEXT_PRODUCT_DECISION_PR`,
   `NO_GO_FIX_SELECTION_OR_BOUNDARY_FIRST`, or
   `INCONCLUSIVE_NEEDS_NAMED_MINIMAL_EVIDENCE`;
4. if the classification is `GO`, start the Tiered Backfill Machine Decision
   Contract PR;
5. keep ASLS / linear-edge quantitative behavior and boundary guard deferred
   until after the tiered PR unless a new blocker changes priority.
