# Architecture Review — 2026-06-28

Doc placement: formal_repo_doc
Repo owner: docs/architecture-contract.md; docs/product/family-hypothesis-boundary.md

Codebase-wide module structure audit. Findings are prioritized by
maintenance pain (how often developers hit the problem × how confusing it
is). Structural moves still need domain review when they touch product
authority, score compatibility, family identity, hypotheses, or matrix
projection; those areas are not "just file moves."

Supporting dependency scan:
[`architecture-import-dependency-analysis-2026-06.md`](architecture-import-dependency-analysis-2026-06.md).

## Overall Assessment

Architecture direction is sound:

- Zero circular imports across 658 Python files
- Domain packages (`peak_detection/`, `discovery/`, `alignment/`,
  `configuration/`) never import from `gui/`, `scripts/`, `tools/`, or
  `output/`
- Dependency direction is consistently inward (IO/rendering → domain)
- GUI layer (28 files) and configuration/presets/output packages are
  well-scoped

Problems are mostly localized: individual modules grew too large or
accumulated mixed responsibilities without being split. The important
exception is the evidence/identity boundary. Several surfaces still use
legacy score and family vocabulary as compatibility adapters, and that can
mislead agents into treating score or family membership as product truth.

### Critical Red Lines

- Score, confidence, caps, and evidence tier are compatibility or evidence
  inputs. Product truth is owned by selected hypotheses and workflow
  projection (`TargetedProductProjection`, alignment projection, Backfill
  authority, ProductWriter gates).
- `family` / `feature_family_id` is a review/search/public compatibility
  container unless an explicit `CrossSamplePeakGroupHypothesis` or
  `PeakHypothesis` contract promotes a more precise identity.
- Family membership is not same-peak proof. Same-peak support needs a typed
  anchor, selected mode, or PeakHypothesis-level reason with provenance.
- Sidecars and review tokens are explanation surfaces. They do not write or
  count without authority manifests, expected-diff approval, and focused
  output tests.

### Codebase Statistics

| Metric | Value |
| --- | --- |
| Python files | 658 |
| Total lines | ~214k |
| Files over 400 lines | 65 |
| Files over 1000 lines | ~25 |
| Files over 2000 lines | 5 |

---

## Priority 1 — Evidence Authority Framed As Scoring

**Impact: HIGH — every developer touches this path.**

The current structure makes it too easy to describe the question "which peak
is product-valid?" as a scoring problem. That is the wrong mental model.
Scoring ranks or annotates candidate evidence; product authority comes from
selected hypotheses and workflow projection.

The compatibility and evidence-input path is spread across five files:

| File | Defines | Role |
| --- | --- | --- |
| `xic_extractor/peak_scoring_evidence.py` | `EvidenceSignal`, `EvidenceScore`, `score_evidence()` | Raw signal scoring |
| `xic_extractor/evidence_semantics.py` | `EvidenceSignalSet`, `EvidenceDecisionSemantics`, `decision_semantics_from_signal_set()` | Decision semantics |
| `xic_extractor/peak_detection/evidence_facts.py` | `CandidateEvidenceFacts`, `build_candidate_evidence_facts()` | Candidate fact extraction |
| `xic_extractor/peak_detection/scoring_models.py` | `Confidence`, `ScoredCandidate`, `ScoringContext` | Scoring models |
| `xic_extractor/peak_detection/candidate_scoring.py` | `score_candidate()` | Top-level scoring entry |

Tracing the compatibility flow requires reading all five and understanding
how `ConfidenceValue` → `Confidence` → `EvidenceDecisionSemantics` →
`projected_confidence_from_candidate_facts` chain together. The trace is
useful, but it must not be described as the final truth path for counted
detections or matrix presence.

### Suggested Structure

Do not create an `evidence_scoring/` package as the main abstraction. That
name re-centers score as product authority. Prefer a split that keeps
candidate facts, typed evidence semantics, compatibility scoring, and
workflow projection visibly separate:

```
xic_extractor/peak_detection/
├── evidence_facts.py          # CandidateEvidenceFacts, raw candidate facts
├── evidence_semantics_adapter.py  # bridge to shared EvidenceDecisionSemantics
├── legacy_scoring.py          # score_candidate(), ScoringContext compatibility
└── selection_decision.py      # selected-hypothesis projection input
```

Keep `evidence_semantics.py` role-neutral because it is shared by targeted
and untargeted paths. Keep `peak_scoring.py` as a compatibility facade while
public projections still expose legacy scoring fields.

### Preconditions

- Characterization tests pinning current confidence/reason outputs for
  representative targeted and untargeted inputs
- Explicit checks that counted detection, matrix presence, and product row
  state still flow through projection authority, not raw score or caps
- `evidence_semantics.py` is on both targeted and untargeted paths —
  verify both after the move

---

## Priority 2 — Family / Hypothesis Boundary Is Still Mixed

**Impact: HIGH — discovery, alignment, Backfill, and diagnostics all hit it.**

The codebase already has successor concepts such as
`CrossSamplePeakGroupHypothesis`, `group_hypothesis_id`, and
`PeakHypothesis`, but legacy `feature_family_id` remains a public row label
and compatibility key. That adapter state is valid only if the boundary is
explicit.

Observed red flags:

| Surface | Smell |
| --- | --- |
| `discovery/feature_family.py` | family assignment also writes evidence tier, score, family context, and representative role |
| `discovery/evidence_score.py` | superfamily representative/member changes score, making grouping look like confidence evidence |
| `alignment/owner_clustering.py` | `OwnerAlignedFeature` defaults `group_hypothesis_id` and `public_family_id` back to `feature_family_id` |
| `alignment/owner_group_delivery.py` | delivery helpers fall back from `group_hypothesis_id` to `feature_family_id` / `cluster_id` |
| `alignment/owner_backfill.py` | backfill cells and audits still key many operations by `feature_family_id` |

### Required Direction

- Treat discovery family IDs as per-sample review containers.
- Treat alignment `public_family_id` as stable public compatibility label.
- Treat `CrossSamplePeakGroupHypothesis` as cross-sample group identity.
- Treat `PeakHypothesis` as candidate chromatographic peak identity.
- Treat projection/ProductWriter as matrix/count authority.

### Preconditions

- Add or maintain a source-of-truth boundary doc for family vs hypothesis.
- Before moving owner/backfill code, map every public output that exposes
  `feature_family_id`, `group_hypothesis_id`, or `peak_hypothesis_id`.
- Characterization tests must cover identity sidecars, duplicate/collapse
  guards, and matrix row ordering.

---

## Priority 3 — `review_actions.py` (2090 lines, four responsibilities)

**Impact: HIGH — any review-related change requires understanding the
entire file.**

Current file mixes:

| Responsibility | What it contains |
| --- | --- |
| Schema | 16 column tuple constants (`*_COLUMNS`) |
| Models | 10 dataclass definitions |
| Business logic | `plan_review_action_applications()`, `plan_review_action_apply_changesets()` |
| I/O | Multiple `load_*()`, `write_*()` functions |

### Suggested Structure

```
xic_extractor/review_actions/
├── schema.py      # column tuple constants
├── models.py      # dataclasses
├── planning.py    # plan_review_action_applications(), changesets
├── io.py          # load_*, write_*
└── __init__.py    # re-export public API
```

### Preconditions

- Grep all callers of `from xic_extractor.review_actions import ...`
  and verify the re-export covers them
- No behavior change — pure structural move

---

## Priority 4 — `peak_detection/facade.py` Misnamed (577 lines)

**Impact: HIGH — name misleads developers about where core logic lives.**

Despite the name, this file contains ~15 private helper functions doing
core implementation work:

- `_augment_with_chrom_peak_segment_candidates()` — candidate enumeration
- `_append_or_merge_chrom_peak_segment_candidate()` — merge logic
- `_chrom_boundary_upgrade_candidate()` — candidate upgrade
- `_combine_proposal_sources()` — source combination
- `_detection_success()` / `_detection_failure()` — outcome construction

Compare to well-named facades in the same codebase:
`signal_processing.py` (28 lines), `config.py` (20 lines).

### Options

| Option | Trade-off |
| --- | --- |
| Rename to `peak_detection_engine.py` | Honest name, minimal diff |
| Extract chrom-peak-segment logic to `chrom_peak_segment_merge.py` | Reduces facade to ~200 lines, but more file moves |

### Preconditions

- Grep for `from xic_extractor.peak_detection.facade import` and
  `from xic_extractor.peak_detection import` to map all callers
- If extracting, add characterization tests for merge behavior first

---

## Priority 5 — `identity_coherence` Spread Across 6 Locations

**Impact: HIGH — unclear where to add new identity-coherence code.**

The concept lives in:

```
alignment/identity_coherence/                        # subpackage (main)
alignment/identity_coherence_validation/              # separate subpackage
alignment/identity_coherence_adapter.py               # root-level module
alignment/identity_coherence_record_builder.py        # root-level module
alignment/identity_coherence_source_mapping.py        # root-level module
alignment/identity_coherence_trace_retrieval.py       # root-level module
```

Additionally, `identity_coherence/__init__.py` re-exports 60+ symbols,
making the entire subpackage interior into public API and raising the cost
of any internal refactor.

### Suggested Structure

```
alignment/identity_coherence/
├── __init__.py              # ≤10 public symbols
├── models.py                # (existing)
├── adapter.py               # ← from identity_coherence_adapter.py
├── record_builder.py        # ← from identity_coherence_record_builder.py
├── source_mapping.py        # ← from identity_coherence_source_mapping.py
├── trace_retrieval.py       # ← from identity_coherence_trace_retrieval.py
└── validation/              # ← from identity_coherence_validation/
    ├── ...
```

Reduce `__init__.py` to export only the true public API (run functions,
primary models). Callers that need internals import the submodule
directly.

### Preconditions

- Map every `from xic_extractor.alignment.identity_coherence import X`
  and `from xic_extractor.alignment import identity_coherence_*` call
  site
- Move files one at a time, keeping re-exports until all callers are
  updated

---

## Priority 6 — `backfill_reconciliation_gallery.py` (7559 lines)

**Impact: MEDIUM — largest single file in the codebase, but in
diagnostics (not core execution path).**

Single file handling data aggregation, decision summaries, and chart
generation for backfill reconciliation galleries. At ~20× the recommended
module size.

### Suggested Structure

```
diagnostics/backfill_reconciliation_gallery/
├── data_loader.py          # data aggregation and loading
├── decision_summary.py     # reconciliation decision logic
├── chart_builder.py        # matplotlib/plotting code
├── layout.py               # gallery page layout and HTML assembly
└── __init__.py             # run_gallery() entry point
```

### Preconditions

- This is diagnostic-only code — lower blast radius, but still needs
  visual verification that gallery output is unchanged
- Split plotting code first (easiest seam)

---

## Priority 7 — Discovery vs Alignment MS1 Backfill Duplication

**Impact: MEDIUM — two independent implementations of the same
extraction pattern.**

| File | Lines | Context |
| --- | --- | --- |
| `discovery/ms1_backfill.py` | 701 | Single-sample MS1 backfill during discovery |
| `alignment/owner_backfill.py` | 961 | Cross-sample MS1 owner backfill during alignment |

Both call `signal_processing.find_peak_and_area()` in a known RT window.
That similarity is real, but only the trace-level operation is shared.
Discovery returns per-sample MS1 candidate fields; alignment owner backfill
also writes cells, group/family identity, region audit context, and rescue
reasons.

### Suggested Structure

Extract only the role-neutral trace core:

```
peak_detection/xic_peak_extraction.py
    extract_peak_in_window(trace, rt_window, ...) -> PeakResult
```

Both `discovery/ms1_backfill.py` and `alignment/owner_backfill.py` may call
this function, but ownership, family/group identity, Backfill status, audit
rows, and matrix behavior must remain in discovery/alignment owners.

### Preconditions

- Confirm the two implementations actually share logic (not just similar
  names) by diffing the core loops
- Characterization tests for both discovery and alignment backfill
  outputs

---

## Additional Observations (Lower Priority)

### Column Schema Definitions in 3 Places

- `alignment/shared_peak_identity_explanation/schema.py` (1512 lines,
  30+ column tuples)
- `alignment/tsv_writer.py` (defines 6 more column tuples)
- `review_actions.py` (defines 13 `*_COLUMNS` tuples)

Each domain should have one `schema.py`; writers import constants, never
define their own.

### Two `process_backend.py` Files

- `alignment/process_backend.py` — alignment multiprocess jobs
- `extraction/process_backend.py` — targeted extraction parallel jobs

Same filename, unrelated content. Rename with domain prefix
(`alignment_process_backend.py`, `extraction_process_backend.py`) to
avoid IDE/grep confusion.

### `alignment/process_backend.py` Mixes 3 Job Types (1177 lines)

Contains `OwnerBuild`, `OwnerBackfill`, and `IdentityTrace` job types
each with their own dataclass + runner + collector. Could split into one
file per job type with a shared executor.

### `product_activation.py` (2125 lines) — Model/Logic/IO Triple

Combines dataclass definitions, TSV I/O, peak hypothesis matrix
construction, and activation business decisions. Could split into
`activation_models.py`, `activation_io.py`, `activation_policy.py`.

### `machine_evidence_support.py` (2334 lines) — Multiple Evidence Types

Contains column constants, data reading, and 6 independent evidence
evaluation algorithms (CWT shape, Tier2 trace, MS2 pattern, MS1 pattern
coherence, matrix RT drift, RT mode). Each evidence type could be its own
module.

### `discovery/models.py` (474 lines) — Factory in Model

`DiscoveryCandidate.from_values()` contains business logic (calling
`assign_discovery_candidate_state()`, building candidate IDs).
`DiscoverySettings.__post_init__` has complex profile merging. Factory
logic should move to `discovery/candidate_factory.py`.

### `alignment/pipeline.py` (795 lines) — 35-Parameter Function

`run_alignment()` accepts 35 parameters and contains helper functions
that belong in submodules. Config resolution and output path logic could
be extracted.

### 9 Files Named `models.py`

Every subpackage has one, plus `xic_models.py` at root (inconsistent
naming). Not necessarily wrong — each is scoped to its package — but the
root-level `xic_models.py` should either be renamed to `models.py` or
moved into a package.

---

## What Not to Touch

These areas are already well-structured:

- **GUI layer** (28 files) — clean section/worker/view separation
- **configuration/** — focused on settings schema and validation
- **presets/** — small, well-scoped loader/apply/models
- **output/** — writers separated from domain logic
- **Root facades** `signal_processing.py` (28 lines), `config.py`
  (20 lines), `peak_scoring.py` (76 lines) — thin re-exports, good
  examples

---

## Execution Principles

All items in this review are **Engineering type** per the project's
acceptance criteria:

- **Characterization-test parity** required before and after each move
- **Move before change** — do not mix structural refactors with behavior
  changes
- **One PR per priority item** — keep diffs reviewable
- **Re-export facades** during transition to avoid breaking callers,
  remove after all callers are updated
