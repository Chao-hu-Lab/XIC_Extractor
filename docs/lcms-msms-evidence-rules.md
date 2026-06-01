# LC-MS/MS Evidence Rules

This document owns XIC Extractor's durable interpretation rules for LC-MS/MS
evidence. `AGENTS.md` keeps only the short guardrails; this file carries the
full domain contract.

## Core Rule

Prefer evidence chains over single-metric authority. RT, CWT, WIS, iRT, local
minima, RT models, shape similarity, product ions, neutral losses, adducts, and
in-source fragments are evidence inputs. None should silently overrule the
selected peak or matrix identity by itself.

Any evidence source that changes production behavior needs explicit config or
contract, machine-readable reason/status fields, and regression tests.

## RT And Identity

- Treat RT as contextual evidence, not a single hard identity veto.
- Large, reproducible, or unmodeled RT shifts may trigger ambiguity or
  confidence demotion, especially when inconsistent with biological ISTD
  transfer evidence.
- RT alone must not prove analyte absence or override co-eluting,
  candidate-aligned MS1/MS2 evidence unless an explicit hard RT exclusion policy
  exists.

## ISTD Evidence

- For ISTDs, when a coherent evidence chain exists, such as aligned MS1 peak
  shape/area plus candidate-aligned NL/product/MS2/trace evidence, do not
  downgrade only because of RT prior, RT window, or centrality concerns.
- If this changes, add an explicit contract doc and regression tests.
- When biological samples receive ISTDs, those ISTDs are the primary transfer
  evidence for real-matrix RT/response behavior because they share the sample
  matrix, ion suppression/enhancement, RT drift, and sample-prep context.

## Missing MS2 / Product / Neutral-Loss Evidence

- Treat missing DDA MS2/product/NL evidence as `not_observed` by default.
- Use missing evidence as negative evidence only when acquisition opportunity,
  local sensitivity, precursor selection or scan coverage, and comparable
  positive controls show that the evidence should have been observable.

## Product Ions, Neutral Losses, Adducts, And Fragments

- Product ions, neutral losses, adducts, and in-source fragments are candidate
  evidence only when co-eluting, boundary-aligned, and assigned to the same
  precursor or candidate.
- Shared class fragments or common neutral losses support class or substructure
  confidence, not analyte-specific proof by themselves.

## Source Roles

Keep source roles explicit when manifests, method docs, or target registries
declare them:

- SDO/LEK are dedicated clean standards and are expected only in their own
  standard samples.
- MixSTDs are non-biological clean standards containing ISTDs and external
  standards.
- Non-ISTD MixSTD targets are external standards; do not use them as required
  biological-sample anchors unless explicitly spiked or validated.

Clean standards can describe instrument behavior and support authentic reference
checks, RT-aware preview, and audit or library work. They cannot alone justify
production correction of biological matrices.

Calibration-derived production RT/area/scoring/matrix gate changes require
current-code biological transfer evidence, row-level coverage or exclusion
policy, and machine-readable GO/NO-GO blockers.

## Audit Versus Production

- Keep audit and production gates separate.
- Extrapolated, sparse, missing, or low-coverage evidence stays review-only until
  an explicit production policy exists.
- When manual EIC/MS2 review contradicts a diagnostic label, investigate whether
  the shared evidence rule, diagnostic wording, or reviewed row is wrong.
- Fix the shared rule and add regression tests when diagnostic logic is wrong;
  do not encode one-off sample or target exceptions as the primary solution.

## Targeted And Untargeted Boundary

- Targeted and untargeted workflows may use different priors and reporting, but
  shared evidence concepts such as traces, candidates, boundaries, regions,
  integration audit, and product/NL evidence should use common low-level models
  when this prevents schema drift.
- Do not force shared concrete implementations before the semantics match.
- Targeted outputs may serve as benchmarks, validation evidence, or shared
  low-level evidence, but must not leak target labels or targeted pass/fail logic
  into untargeted production matrix identity unless an approved contract says so.
