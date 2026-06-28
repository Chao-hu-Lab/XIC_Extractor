# Family Abstraction Removal — Structural Refactoring Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the "family" abstraction layer from the discovery and alignment pipeline, replacing it with correctly-scoped concepts (peak anchor, cross-sample group, typed evidence facts).

**Architecture:** The current "family" concept conflates three unrelated concerns: (1) per-sample MS1 peak identity (strict family), (2) chromatographic proximity grouping (superfamily), and (3) cross-sample chemical-entity grouping (alignment family). This plan separates them into independent concepts with clear ownership boundaries. Phase 1 cleans up discovery (remove superfamily, rename family → peak_anchor). Phase 2 clarifies alignment semantics (docstrings only). Evidence typed-facts migration is deferred to a separate Science-type plan.

**Tech Stack:** Python 3.11+, pytest, dataclasses

## Global Constraints

- **Output column names are public contracts.** `feature_family_id` and `public_family_id` column names in CSV/TSV output files MUST NOT be renamed. Internal Python identifiers can change; output column headers cannot.
- **`feature_family_id` stays as the dataclass field name — no @property alias.** `alignment/csv_io.py` constructs `DiscoveryCandidate(feature_family_id=...)` directly, and all `replace(candidate, feature_family_id=...)` calls use this name. Adding a read-only `peak_anchor_id` @property would create permanent dual-naming with no migration endpoint (writes always use old name, reads use new name, grep finds half the story). Instead, keep `feature_family_id` as the sole field name. The semantic shift to "peak anchor" is expressed through module/function naming (`peak_anchor.py`, `assign_peak_anchors`), not through dataclass field aliases.
- **`evidence_score` field stays on DiscoveryCandidate.** `alignment/ownership.py` (line 769) reads `getattr(candidate, "evidence_score", 0)` and `identity_gates.py` uses `evidence_score >= 60` as a seed quality gate. Removing the field would silently degrade all seeds to "weak." Phase 3 adds typed facts alongside evidence_score, not in place of it.
- **`alignment/csv_io.py` must be updated when fields are removed.** `_parse_candidate_row()` passes removed field names as constructor kwargs — omitting this causes `TypeError` at runtime.
- **move-before-change discipline.** Structural renames happen in dedicated commits before any behavior changes.
- **Each task must leave tests green.** Run `uv run pytest --tb=short -q` after every task.
- **Diagnostic tools are out of scope.** `tools/diagnostics/family_ms1_*` read from output TSVs. Since output column names don't change, they keep working. Internal diagnostic naming can be updated in a follow-up.
- **Alignment grouping logic is frozen.** The `_complete_link_groups` algorithm in `cross_sample_peak_groups.py` is not touched. Only naming and documentation change in alignment.
- **Project type: Engineering.** Acceptance = characterization-test parity + maintainability gain. Evidence typed-facts migration (Phase 3) is deferred to a separate Science-type plan.

---

## Phase 1: Discovery — Remove Family Abstraction

### Task 1: Lift evidence scoring out of superfamily assignment

Currently `score_discovery_evidence` is called inside `_assign_superfamilies` (feature_family.py:88–100). This couples evidence scoring to superfamily logic. Lift it into a standalone step so superfamily removal doesn't break evidence scoring.

**Files:**
- Modify: `xic_extractor/discovery/feature_family.py` (lines 12–18, 49–105)
- Test: `tests/test_discovery_feature_family.py` (existing tests must stay green)

**Interfaces:**
- Consumes: `DiscoveryCandidate`, `DiscoverySettings`, `score_discovery_evidence`
- Produces: `assign_feature_families` unchanged public signature, same output values

- [ ] **Step 1: Refactor `assign_feature_families` to separate scoring from superfamily grouping**

Extract the `score_discovery_evidence` call from inside `_assign_superfamilies` into `assign_feature_families` as a third step:

```python
def assign_feature_families(
    candidates: tuple[DiscoveryCandidate, ...],
    *,
    settings: DiscoverySettings | None = None,
) -> tuple[DiscoveryCandidate, ...]:
    family_assigned = _assign_strict_families(candidates)
    superfamily_assigned = _assign_superfamilies(family_assigned, settings=settings)
    return _score_all_evidence(superfamily_assigned, settings=settings)
```

Move the scoring loop from `_assign_superfamilies` (lines 88–100) into a new function:

```python
def _score_all_evidence(
    candidates: tuple[DiscoveryCandidate, ...],
    *,
    settings: DiscoverySettings | None = None,
) -> tuple[DiscoveryCandidate, ...]:
    scored: list[DiscoveryCandidate] = []
    for candidate in candidates:
        discovery_evidence = score_discovery_evidence(candidate, settings=settings)
        scored.append(
            replace(
                candidate,
                evidence_score=discovery_evidence.score,
                evidence_tier=discovery_evidence.tier,
                ms2_support=discovery_evidence.ms2_support,
                ms1_support=discovery_evidence.ms1_support,
                rt_alignment=discovery_evidence.rt_alignment,
                family_context=discovery_evidence.family_context,
            )
        )
    return tuple(scored)
```

And remove the scoring lines from `_assign_superfamilies` — it should only assign superfamily fields (id, size, role, confidence, evidence), not call `score_discovery_evidence`.

- [ ] **Step 2: Run tests to verify zero behavior change**

Run: `uv run pytest tests/test_discovery_feature_family.py -v`
Expected: ALL PASS, identical evidence_score and family_context values.

- [ ] **Step 3: Commit**

```
git add xic_extractor/discovery/feature_family.py
git commit -m "refactor(discovery): lift evidence scoring out of superfamily assignment"
```

---

### Task 2: Remove superfamily concept from discovery

Superfamily was a band-aid for raw-trace peak fragmentation. With gaussian-smoothed traces, the grouping is no longer needed. This is an accepted behavior change: evidence_score will change by ±5 points (superfamily weight removed), and superfamily fields will disappear from output.

**Files:**
- Modify: `xic_extractor/discovery/feature_family.py` — delete superfamily logic
- Modify: `xic_extractor/discovery/models.py` — remove superfamily fields + columns
- Modify: `xic_extractor/discovery/evidence_score.py` — remove `classify_family_context`, remove superfamily weight
- Modify: `xic_extractor/discovery/evidence_config.py` — remove superfamily weights
- Modify: `xic_extractor/discovery/csv_writer.py` — remove superfamily sort keys, update review note
- Modify: `xic_extractor/alignment/csv_io.py` — remove superfamily kwargs from `_parse_candidate_row`, update `_CANDIDATE_UNESCAPE_FIELDS` and `_INT_FIELDS`
- Modify: `tests/test_discovery_feature_family.py` — remove superfamily tests, update score assertions
- Modify: `tests/test_discovery_evidence.py` (if exists) — update

**Interfaces:**
- Consumes: Task 1's refactored `assign_feature_families`
- Produces: `assign_feature_families` still returns `tuple[DiscoveryCandidate, ...]` but without superfamily fields populated

- [ ] **Step 1: Remove superfamily fields from DiscoveryCandidate and column schemas**

In `xic_extractor/discovery/models.py`:

Remove from `DISCOVERY_CANDIDATE_REVIEW_COLUMNS`:
```python
# DELETE these lines (48–52):
    "feature_superfamily_id",
    "feature_superfamily_size",
    "feature_superfamily_role",
    "feature_superfamily_confidence",
    "feature_superfamily_evidence",
```

Remove from `DISCOVERY_BRIEF_COLUMNS`:
```python
# DELETE this line (119):
    "family_context",
```

Remove from `DiscoveryCandidate` dataclass:
```python
# DELETE these fields (263–267):
    feature_superfamily_id: str = ""
    feature_superfamily_size: int = 1
    feature_superfamily_role: str = "representative"
    feature_superfamily_confidence: str = "LOW"
    feature_superfamily_evidence: str = "single_candidate"
```

Remove `family_context` field (line 225):
```python
# DELETE:
    family_context: str
```

In `from_values()` (line 332), remove the `family_context="singleton"` kwarg.

- [ ] **Step 2: Remove superfamily logic from feature_family.py**

Delete these functions entirely:
- `_assign_superfamilies` (lines 49–105)
- `_matching_superfamily_index` (lines 118–128)
- `_same_feature_superfamily` (lines 148–162)
- `_superfamily_ids` (lines 175–185)
- `_representative` (lines 208–222)
- `_SUPERFAMILY_APEX_DELTA_MIN` (line 7)
- `_SUPERFAMILY_OVERLAP_RATIO_MIN` (line 8)
- `_PRIORITY_RANK` (line 9)

Update `assign_feature_families`:
```python
def assign_feature_families(
    candidates: tuple[DiscoveryCandidate, ...],
    *,
    settings: DiscoverySettings | None = None,
) -> tuple[DiscoveryCandidate, ...]:
    family_assigned = _assign_strict_families(candidates)
    return _score_all_evidence(family_assigned, settings=settings)
```

- [ ] **Step 3: Remove superfamily scoring from evidence_score.py**

Delete `classify_family_context` (lines 169–174).

Remove `family_context` from `DiscoveryEvidence` dataclass:
```python
@dataclass(frozen=True)
class DiscoveryEvidence:
    score: int
    tier: str
    ms2_support: str
    ms1_support: str
    rt_alignment: str
```

Remove from `score_discovery_evidence`:
```python
# DELETE line 36:
    family_context = classify_family_context(candidate)

# DELETE lines 84–88:
    if candidate.feature_superfamily_size > 1:
        if candidate.feature_superfamily_role == "representative":
            score += weights.superfamily_representative
        else:
            score += weights.superfamily_member

# UPDATE return (remove family_context):
    return DiscoveryEvidence(
        score=score,
        tier=evidence_tier_from_score(score),
        ms2_support=ms2_support,
        ms1_support=ms1_support,
        rt_alignment=rt_alignment,
    )
```

Remove superfamily weights from `evidence_config.py`:
```python
# DELETE these fields from DiscoveryEvidenceWeights:
    superfamily_representative: int = 5
    superfamily_member: int = -5
```

- [ ] **Step 4: Update csv_writer.py**

Remove superfamily sort keys from `_candidate_sort_key`:
```python
def _candidate_sort_key(candidate: DiscoveryCandidate) -> tuple[Any, ...]:
    area_is_missing = candidate.ms1_area is None
    area_desc = 0.0 if candidate.ms1_area is None else -candidate.ms1_area
    return (
        _PRIORITY_RANK.get(candidate.review_priority, len(_PRIORITY_RANK)),
        -candidate.evidence_score,
        -candidate.feature_family_size,
        candidate.feature_family_id,
        -candidate.seed_event_count,
        -candidate.ms2_product_max_intensity,
        area_is_missing,
        area_desc,
        candidate.best_seed_rt,
    )
```

Update `build_discovery_review_note` to remove family_context:
```python
def build_discovery_review_note(candidate: DiscoveryCandidate) -> str:
    return (
        f"{candidate.ms2_support} MS2; "
        f"{candidate.ms1_support} MS1; "
        f"{candidate.rt_alignment} RT"
    )
```

- [ ] **Step 5: Update `_score_all_evidence` to match new DiscoveryEvidence**

In `feature_family.py`, the `_score_all_evidence` function (from Task 1) no longer needs to set `family_context`:
```python
def _score_all_evidence(
    candidates: tuple[DiscoveryCandidate, ...],
    *,
    settings: DiscoverySettings | None = None,
) -> tuple[DiscoveryCandidate, ...]:
    scored: list[DiscoveryCandidate] = []
    for candidate in candidates:
        discovery_evidence = score_discovery_evidence(candidate, settings=settings)
        scored.append(
            replace(
                candidate,
                evidence_score=discovery_evidence.score,
                evidence_tier=discovery_evidence.tier,
                ms2_support=discovery_evidence.ms2_support,
                ms1_support=discovery_evidence.ms1_support,
                rt_alignment=discovery_evidence.rt_alignment,
            )
        )
    return tuple(scored)
```

- [ ] **Step 6: Update `alignment/csv_io.py` to remove superfamily constructor kwargs**

In `xic_extractor/alignment/csv_io.py`:

**Update `_CANDIDATE_UNESCAPE_FIELDS`** (line 24): remove `"feature_superfamily_id"`.

**Update `_INT_FIELDS`** (line 33): remove `"feature_superfamily_size"`.

**Update `_parse_candidate_row`** (lines 311–336): remove all superfamily constructor kwargs:
```python
# DELETE these lines from DiscoveryCandidate(...) constructor call:
    feature_superfamily_id=_machine_field(...),
    feature_superfamily_size=_parse_int(...),
    feature_superfamily_role=_required_text(...),
    feature_superfamily_confidence=_required_text(...),
    feature_superfamily_evidence=_required_text(...),

# ALSO DELETE:
    family_context=_required_text(...),
```

**Note:** `feature_family_id` and `feature_family_size` kwargs STAY — they are NOT superfamily fields.

- [ ] **Step 7: Update tests**

In `tests/test_discovery_feature_family.py`:

**Delete these test functions entirely:**
- `test_assign_feature_superfamilies_groups_close_overlapping_ms1_peaks`
- `test_assign_feature_superfamilies_selects_one_representative`
- `test_assign_feature_superfamilies_keeps_distant_or_weak_overlap_separate`
- `test_assign_feature_superfamilies_does_not_chain_across_broad_rt_region`
- `test_assign_feature_superfamilies_is_stable_across_input_order`
- `test_assign_feature_families_labels_superfamily_context`

**Update `test_assign_feature_families_assigns_evidence_score_and_tier`:**
- Remove `assert by_id["Sample#10"].family_context == "singleton"` (line 287)
- The evidence_score value for `Sample#10` may change by up to ±5 due to superfamily weight removal. Update assertions if needed (tier A threshold is 80, the strong candidate likely still scores A without the +5 bonus).

**Update `_candidate` helper:**
- Remove `family_context="singleton"` from the DiscoveryCandidate constructor call.
- Remove superfamily field defaults.

**Update `test_assign_feature_families_threads_custom_evidence_settings`:**
- The score delta is no longer affected by superfamily weight. Verify the new expected delta (+5 from ms1_peak_present 30 vs 25).

- [ ] **Step 8: Run full test suite**

Run: `uv run pytest --tb=short -q`
Expected: ALL PASS

- [ ] **Step 9: Commit**

```
git add -A
git commit -m "refactor(discovery): remove superfamily concept

Superfamily was a band-aid for raw-trace peak fragmentation. With
gaussian-smoothed traces the grouping is no longer needed. Evidence
scoring no longer uses ±5 superfamily weight.

BREAKING: discovery_candidates.csv no longer includes superfamily
columns. discovery_review.csv no longer includes family_context."
```

---

### Task 3: Rename discovery family → peak anchor

The remaining "strict family" in discovery is really "peak anchor" — candidates that share the same MS1 chromatographic peak. Rename to clarify the concept.

**Files:**
- Rename: `xic_extractor/discovery/feature_family.py` → `xic_extractor/discovery/peak_anchor.py`
- Modify: `xic_extractor/discovery/models.py` — no field changes (feature_family_id stays as-is)
- Modify: `xic_extractor/discovery/pipeline.py` — update import
- Rename: `tests/test_discovery_feature_family.py` → `tests/test_discovery_peak_anchor.py`

**Interfaces:**
- Consumes: `DiscoveryCandidate` with `feature_family_id` still present (output compat)
- Produces: `assign_peak_anchors(candidates, settings=) -> tuple[DiscoveryCandidate, ...]`

**Key constraint:** `feature_family_id` and `feature_family_size` stay as the sole dataclass field names. No @property alias is added — the "peak anchor" semantic shift is expressed through module/function names only. All existing `replace(candidate, feature_family_id=...)` calls and `csv_io.py` constructor kwargs continue to work unchanged.

- [ ] **Step 1: Rename feature_family.py → peak_anchor.py and update functions**

Rename file:
```
git mv xic_extractor/discovery/feature_family.py xic_extractor/discovery/peak_anchor.py
```

In the new `peak_anchor.py`, rename:
```python
# assign_feature_families → assign_peak_anchors
def assign_peak_anchors(
    candidates: tuple[DiscoveryCandidate, ...],
    *,
    settings: DiscoverySettings | None = None,
) -> tuple[DiscoveryCandidate, ...]:
    anchored = _assign_peak_anchors(candidates)
    return _score_all_evidence(anchored, settings=settings)


# _assign_strict_families → _assign_peak_anchors
def _assign_peak_anchors(
    candidates: tuple[DiscoveryCandidate, ...],
) -> tuple[DiscoveryCandidate, ...]:
    groups: list[list[DiscoveryCandidate]] = []
    for candidate in candidates:
        group_index = _matching_anchor_index(candidate, groups)
        if group_index is None:
            groups.append([candidate])
        else:
            groups[group_index].append(candidate)

    anchor_ids = _anchor_ids(groups)
    assigned_by_candidate_id: dict[str, DiscoveryCandidate] = {}
    for group, anchor_id in zip(groups, anchor_ids, strict=True):
        group_size = len(group)
        for candidate in group:
            assigned_by_candidate_id[candidate.candidate_id] = replace(
                candidate,
                feature_family_id=anchor_id,
                feature_family_size=group_size,
            )

    return tuple(
        assigned_by_candidate_id[candidate.candidate_id]
        for candidate in candidates
    )


# _matching_family_index → _matching_anchor_index
def _matching_anchor_index(
    candidate: DiscoveryCandidate,
    groups: list[list[DiscoveryCandidate]],
) -> int | None:
    for index, group in enumerate(groups):
        if any(_same_peak_anchor(candidate, existing) for existing in group):
            return index
    return None


# _same_feature_family → _same_peak_anchor
def _same_peak_anchor(
    first: DiscoveryCandidate,
    second: DiscoveryCandidate,
) -> bool:
    return (
        first.raw_file == second.raw_file
        and first.sample_stem == second.sample_stem
        and first.neutral_loss_tag == second.neutral_loss_tag
        and first.ms1_peak_found
        and second.ms1_peak_found
        and _peak_bounds_present(first)
        and _peak_bounds_present(second)
        and _apex_matches(first, second)
        and _peak_intervals_overlap(first, second)
    )


# _family_ids → _anchor_ids
def _anchor_ids(groups: list[list[DiscoveryCandidate]]) -> list[str]:
    sorted_groups = sorted(groups, key=_group_sort_key)
    anchor_id_by_key: dict[tuple[str, ...], str] = {}
    for index, group in enumerate(sorted_groups, start=1):
        anchor_id_by_key[_group_identity_key(group)] = (
            f"{group[0].sample_stem}@F{index:04d}"
        )
    return [anchor_id_by_key[_group_identity_key(group)] for group in groups]
```

Note: the ID format `@F{index:04d}` stays the same for output compatibility.

- [ ] **Step 2: Update pipeline.py import**

```python
# OLD:
from xic_extractor.discovery.feature_family import assign_feature_families

# NEW:
from xic_extractor.discovery.peak_anchor import assign_peak_anchors
```

Update call sites (lines 71 and 108):
```python
# OLD:
        candidates = assign_feature_families(discovered, settings=settings)

# NEW:
        candidates = assign_peak_anchors(discovered, settings=settings)
```

Update timing stage name:
```python
# OLD:
    with recorder.stage("discover.feature_family", ...):

# NEW:
    with recorder.stage("discover.peak_anchor", ...):
```

- [ ] **Step 3: Rename test file and update**

```
git mv tests/test_discovery_feature_family.py tests/test_discovery_peak_anchor.py
```

Update imports and function names in the test file:
```python
from xic_extractor.discovery.peak_anchor import assign_peak_anchors

# Update all calls from assign_feature_families → assign_peak_anchors
# Assertions keep using candidate.feature_family_id (it's the actual field)
```

- [ ] **Step 4: Run full test suite**

Run: `uv run pytest --tb=short -q`
Expected: ALL PASS

- [ ] **Step 5: Commit**

```
git add -A
git commit -m "refactor(discovery): rename family → peak_anchor

Strict family was really 'peak anchor' — candidates sharing the same
MS1 chromatographic peak. Module renamed feature_family.py → peak_anchor.py,
functions renamed accordingly. feature_family_id field unchanged (output
contract)."
```

---

## Phase 2: Alignment — Semantic Clarification

### Task 4: Clarify alignment identity semantics

Alignment's "family" is actually "cross-sample chemical-entity group" and uses completely different criteria (m/z + RT + product + NL + edge evidence) from discovery's peak anchor. This task clarifies the semantic boundary without changing any logic or output.

**Files:**
- Modify: `xic_extractor/alignment/cross_sample_peak_groups.py` — docstrings
- Modify: `xic_extractor/alignment/owner_clustering.py` — docstrings on OwnerAlignedFeature
- Modify: `xic_extractor/alignment/family_compatibility.py` — module docstring
- Modify: `xic_extractor/alignment/owner_family_successor_contract.py` — docstrings
- Modify: `docs/product/family-hypothesis-boundary.md` — update to reflect new naming
- Test: existing alignment tests must stay green (no logic change)

**Interfaces:**
- Consumes: nothing from Phase 1 (alignment is independent)
- Produces: no API changes, only documentation and docstrings

- [ ] **Step 1: Add clarifying docstrings to CrossSamplePeakGroupHypothesis**

In `xic_extractor/alignment/cross_sample_peak_groups.py`, add module docstring:

```python
"""Cross-sample peak group construction.

This module groups SampleLocalMS1Owner instances into cross-sample chemical-
entity groups using m/z, RT, product m/z, observed neutral loss, and edge
evidence.  The output ``CrossSamplePeakGroupHypothesis`` is the primary
cross-sample identity unit.

``public_family_id`` is a *display label* preserved for output compatibility.
It is NOT an identity anchor — use ``group_hypothesis_id`` for identity
decisions within the pipeline.
"""
```

Add docstring to `CrossSamplePeakGroupHypothesis`:
```python
@dataclass(frozen=True)
class CrossSamplePeakGroupHypothesis:
    """Cross-sample chemical-entity group hypothesis.

    Identity semantics:
    - ``group_hypothesis_id``: primary identity key for pipeline decisions.
    - ``public_family_id``: display label for output compatibility.
      Identical to ``group_hypothesis_id`` in current implementation.
    - ``feature_family_id`` property: legacy output alias for ``public_family_id``.
    """
```

- [ ] **Step 2: Add clarifying docstrings to OwnerAlignedFeature**

In `xic_extractor/alignment/owner_clustering.py`, add docstring:

```python
@dataclass(frozen=True)
class OwnerAlignedFeature:
    """Compatibility facade for cross-sample owner grouping.

    ``feature_family_id`` here is a cross-sample group label, NOT the same
    concept as discovery's per-sample peak anchor.  Use ``group_hypothesis_id``
    for identity decisions.  ``feature_family_id`` is retained only because
    output surfaces (alignment_review.tsv, alignment_cells.tsv) use it as a
    column name.
    """
```

- [ ] **Step 3: Add module docstring to family_compatibility.py**

```python
"""Cross-sample group compatibility checks.

Despite the legacy module name 'family_compatibility', these functions check
whether two cross-sample groups represent the same chemical entity using m/z,
RT, product m/z, and observed neutral loss tolerances.  They do NOT check
discovery-layer peak-anchor membership.

A future rename to ``group_compatibility.py`` is planned but deferred to
minimize merge conflicts with active branches.
"""
```

- [ ] **Step 4: Update family-hypothesis-boundary.md**

Replace the current document with updated framing that reflects the new naming:

```markdown
# Peak Anchor, Cross-Sample Group, and Hypothesis Boundary

This page defines the durable boundary between per-sample peak anchors,
cross-sample group hypotheses, peak hypotheses, and product projections.

## Contract

- `peak_anchor_id` (discovery `feature_family_id`) groups candidates that
  share the same MS1 chromatographic peak within a single sample.  It is a
  per-sample trace-identity label, not a chemical identity claim.
- `CrossSamplePeakGroupHypothesis` owns cross-sample group identity:
  membership, owner edge evidence, hard split gates, review-only records,
  and group delivery metadata.  Use `group_hypothesis_id` for identity.
- `PeakHypothesis` owns candidate chromatographic identity: the physical
  peak candidate, selected integration, typed evidence, and selected-
  hypothesis decision semantics.
- Workflow projection owns product decisions.

## Roles

| Concept | Owns | Must not own |
| --- | --- | --- |
| Discovery `peak_anchor_id` / output `feature_family_id` | Per-sample MS1 peak identity and review grouping | Cross-sample identity, Backfill promotion, selected-peak truth |
| Alignment `public_family_id` (display label) | Stable public row label for output compatibility | Canonical identity proof — use `group_hypothesis_id` instead |
| `CrossSamplePeakGroupHypothesis` | Cross-sample owner/group identity via `group_hypothesis_id` | Per-peak integration truth or ProductWriter authority |
| `PeakHypothesis` | Candidate peak identity, evidence context, selected hypothesis semantics | Cross-sample grouping policy or final matrix writing |
| Product projection / ProductWriter | Counted detection, product state, matrix value authority | Low-level evidence extraction or review-only grouping |
```

(Keep remaining sections — Migration Rule, Design Red Lines, Verification, See Also — updated to use "peak anchor" and "cross-sample group" terminology.)

- [ ] **Step 5: Run alignment tests to verify zero change**

Run: `uv run pytest tests/test_alignment_family_compatibility.py tests/test_alignment_owner_family_successor_contract.py -v`
Expected: ALL PASS (no logic changed, only docstrings and docs)

- [ ] **Step 6: Commit**

```
git add -A
git commit -m "docs(alignment): clarify family as display label, group_hypothesis_id as identity

Add module and class docstrings explaining that alignment 'family' is a
cross-sample chemical-entity group, not the same concept as discovery's
per-sample peak anchor. public_family_id is a display label; use
group_hypothesis_id for pipeline identity decisions."
```

---

## Scope Deferred to Future Plans

The following are explicitly out of scope for this plan:

1. **Typed evidence classification (Phase 3)** — Replace `evidence_score` weighted sum with `DiscoveryEvidenceFacts` typed categorical classification (`classify_discovery_evidence`). This is a **Science-type** change requiring:
   - Ground truth definition (which candidates should be tier A/B/C)
   - 8RAW parity test: new tier vs old tier disagreement rate
   - Alignment seed quality non-regression (evidence_score stays populated alongside typed facts)
   - Explicit documentation that `evidence_tier` and `evidence_score` may diverge
   Track as a separate plan with its own validation cycle. The user's recurring request「證據不要講求分數」is the motivation.

2. **Alignment evidence_score → typed facts migration** — `identity_gates.py` uses `evidence_score >= 60` for seed quality classification, `ownership.py` sorts by evidence_score, `csv_io.py` parses it. Replacing these consumers with typed-facts checks requires spike-in recovery and seed quality parity validation. Depends on Phase 3 above.

3. **Diagnostic tool naming** — `tools/diagnostics/family_ms1_*` modules use "family" internally. Since they read from output TSVs (column names unchanged), they keep working. Cosmetic renames can be done in a follow-up.

4. **Alignment file renames** — `family_compatibility.py` → `group_compatibility.py`, `owner_family_successor_contract.py` → `owner_group_successor_contract.py`. Deferred to minimize merge conflicts with active branches.

5. **Peak detection evidence system convergence** — The `CandidateEvidenceFacts` / `EvidenceDecisionSemantics` typed-facts system already exists in `xic_extractor/peak_detection/`. Converging discovery evidence with this system is a future unification task.
