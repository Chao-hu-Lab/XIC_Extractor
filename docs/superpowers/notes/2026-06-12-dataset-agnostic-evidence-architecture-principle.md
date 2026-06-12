# Dataset-Agnostic Evidence Architecture Principle

Date: 2026-06-12
Status: accepted architecture note

## Context

Recent preset and diagnostics work exposed a repeated failure mode: task-local
diagnostic paths were built to produce evidence quickly, then later required
architecture cleanup because reuse, ownership, and call-cost were not acceptance
criteria at implementation time.

The same risk applies at the scientific architecture level. The current 8RAW and
85RAW datasets are valuable because they expose real LC-MS/MS behavior and
runtime cost, but they are not the product boundary. Likewise, CID neutral-loss
logic is useful evidence, but the repo must not become a CID-NL-only identity
engine. Planned and partial evidence sources such as HCD product-ion evidence
and Delta Mass should fit the same evidence spine rather than creating parallel
matrix-writing paths.

## Decision

XIC Extractor should be treated as a dataset-agnostic, evidence-provider-agnostic
LC-MS evidence and model-selection pipeline.

8RAW and 85RAW are validation fixtures and stress oracles. CID-NL, HCD-PI, Delta
Mass, MS1 pattern, RT/iRT, shape, clean standards, library matches, and future
learned models are evidence providers. They feed `EvidenceVector`, model
selection, and `AuditTrail`; they do not define the permanent architecture by
themselves.

New diagnostics, performance work, and evidence-provider additions must start
with an architecture preflight: identify the existing owner/helper to reuse,
the product spine layer being advanced, the call-cost model, the public contract
at risk, and the validation gate that can close the decision.

## Alternatives Considered

### Keep building evidence-specific diagnostics first

- Pros: Fast to prototype; easy to produce an immediate sidecar or report.
- Cons: Repeats local parsers, selectors, writers, RAW access, and matrix
  projection logic; turns `diagnostic_only` paths into sticky architecture debt.
- Why not: This is exactly the pattern that caused repeated cleanup cycles.

### Make CID-NL and 85RAW the central architecture

- Pros: Matches the current strongest validation surface and existing domain
  intuition.
- Cons: Hard-codes one dataset shape and one fragmentation/evidence mechanism;
  blocks HCD-PI, Delta Mass, and future non-CID evidence from becoming first-
  class model inputs.
- Why not: The repo goal is broader than one dataset or one acquisition/evidence
  style.

### Evidence-provider-agnostic spine

- Pros: Keeps current CID-NL/85RAW work useful while allowing HCD-PI, Delta Mass,
  MS1 patterns, RT/iRT, standards, libraries, and future models to enter through
  the same hypothesis/evidence/model-selection path.
- Cons: Requires more discipline up front; early features need owner/cost/public
  contract preflight before implementation.
- Why: This preserves extensibility while reducing future cleanup cost.

## Consequences

Positive:

- New evidence sources have a clear home: evidence provider -> `EvidenceVector`
  -> model selection -> `AuditTrail` -> approved matrix/export contract.
- 8RAW/85RAW validation remains valuable without becoming a hard-coded product
  boundary.
- HCD-PI and Delta Mass can be introduced as first-class evidence families
  without bypassing existing identity, activation, and matrix contracts.
- Architecture review can reject local wrappers earlier, before they accumulate
  debt.

Negative:

- Prototype work needs a short architecture preflight before coding.
- Some quick diagnostic ideas may be delayed until an owner/reuse/cost model is
  named.

Risk and mitigation:

- Risk: Preflight becomes process overhead. Mitigation: keep it compact and
  require only the owner/helper, spine layer, call-cost model, contract risk,
  validation gate, and stop rule.
- Risk: Evidence providers become too abstract. Mitigation: each provider still
  needs concrete sidecar schemas, focused tests, and real-data validation before
  product activation.

## Operational Rule

Before implementing non-trivial diagnostics, preset performance optimization,
RAW-backed evidence, matrix activation, HCD-PI, Delta Mass, or CID-NL expansion,
use `.codex/skills/xic-architecture-preflight/SKILL.md`.
