# Rule-First Development Workflow

## Why This Exists

Major XIC work should not become a treadmill of tiny slices, ad hoc patches, or
mixed responsibilities. Small slices are useful while a rule is immature, but
the goal is a defensible rule that can classify or transform the full relevant
scope.

This applies beyond Discovery. It can guide Backfill, product gates, review
actions, artifact retention, validation strategy, algorithm thresholds, and
handoff/report workflows.

## Phase 1: Demonstration Set

Pick examples that reveal the rule, not just easy wins.

Include:

- clear positives;
- clear rejects;
- boundary cases;
- known failure modes;
- examples that expose responsibility conflicts;
- at least one tempting case where the visible signal is not enough to justify
  the product action.

Output:

- named demo set;
- why each group is representative;
- what failure mode or product question it covers.

## Phase 2: Rule Extraction

Turn observations into a small product or workflow rule.

The rule should answer:

- what input evidence is sufficient;
- what identity/provenance/state must be preserved;
- what action becomes accepted, held, rejected, preserved, or omitted;
- what evidence cannot prove the action by itself;
- which near-neighbor responsibility is explicitly excluded.

Reject rules that read like nested dataset-specific patches. If the rule needs
many qualifiers, keep it as calibration and do not promote.

## Phase 3: Rule Freeze

Before applying broadly, freeze:

- input artifact paths and hashes;
- full relevant scope definition;
- output schema;
- expected-diff or expected-output contract;
- provenance/audit fields;
- ambiguity labels;
- human-review boundary;
- stop rule.

If this changes maturity tier, active lane, authority, review/replay behavior,
schema, output, selected area/counting, or matrix authority, update the
productization control plane.

## Phase 4: Full-Scope Application

Run the frozen rule over the full relevant scope.

Typical buckets:

- accepted output/product rows or cells;
- held/ambiguous review items;
- rejected items;
- preserved context;
- omitted no-action items.

The scope can be bounded by a real product question, such as "current CID-NL
DNA_dR Discovery candidates" or "current Backfill approved-evidence universe".
It should not be bounded merely to make the pass count look clean.

## Phase 5: Ambiguous-Only Review

Do not ask humans to review obvious pass/fail rows.

Human or AI review should focus on:

- rule conflicts;
- weak identity or provenance;
- responsibility-boundary ambiguity;
- evidence that is visually tempting but not authority-bearing;
- cases where the rule says hold but the user may supply domain truth.

Output review decisions back into the rule, an explicit override contract, or a
hold bucket. Do not silently convert review notes into product authority.

## Phase 6: One Delivery

Deliver the accepted set as one bounded result.

Depending on the work, that may be:

- product activation;
- algorithm rule change;
- validation gate;
- review workflow;
- artifact-retention contract;
- release-slice checker;
- handoff/report surface.

Required evidence should match the risk: expected diff, exact keyset/value
checks, row/sample identity, provenance, artifact retention, no unrelated drift,
and control-plane/handoff updates when the public surface changes.

## Stop Conditions

Stop and split the work if:

- the full relevant scope is undefined;
- ambiguous rows dominate in a way that shows the rule is not mature;
- a near-neighbor responsibility starts leaking into the rule;
- examples are being used as product authority rather than calibration;
- the work needs a new public surface, authority, schema, or output change that
  has no expected-diff/expected-output contract.
