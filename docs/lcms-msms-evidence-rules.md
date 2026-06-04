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
- Legacy morphology, shape, or trace-quality labels must not become hard
  product vetoes for ISTDs when finite positive RT/area, candidate-aligned
  product/NL/MS2 support, and role-aware RT context support the same selected
  peak. Keep the label visible as review evidence instead.
- If this changes, add an explicit contract doc and regression tests.
- When biological samples receive ISTDs, those ISTDs are the primary transfer
  evidence for real-matrix RT/response behavior because they share the sample
  matrix, ion suppression/enhancement, RT drift, and sample-prep context.

## Targeted Analyte / STD Pair Evidence

- For targeted analytes or STDs with an ISTD pair, anchor-guided selection must
  prefer a complete candidate peak near the ISTD-informed or product/NL-informed
  reference over a random small nearest peak.
- In paired targeted mode, the paired ISTD RT is the primary biological-matrix
  transfer anchor. A target-specific NL/product anchor may support the paired
  analyte/STD candidate only when it is close to the paired ISTD RT. A distant
  target-specific NL/product anchor must not move the extraction window away
  from the ISTD-supported RT region by itself, because that silently converts a
  random DDA/NL event into peak identity authority.
- ISTD-centered fallback opens the candidate search/review window only. It must
  not hard-backfill a missing paired STD/analyte into a counted detection; the
  selected row still needs the analyte/STD product policy to project as counted.
- Legacy morphology, shape, trace-quality, or `VERY_LOW` labels are review
  evidence, not direct product authority, when the selected analyte peak has
  finite positive RT/area, candidate-aligned product/NL/MS2 support, targeted
  anchor selection context, and no anchor, RT, or NL/product conflict.
- Analyte `NL_FAIL` and `NO_MS2` remain not-counted unless a separate approved
  analyte policy exists. Pair evidence must not silently convert missing or
  failed product evidence into a counted detection.
- Avoid encoding fixed RT-delta constants as product truth without current
  biological-matrix validation. If a distance threshold becomes production
  policy, it needs its own contract, artifact, and regression tests.
- Treat legacy scoring thresholds as calibration-sensitive heuristics. They may
  rank or annotate candidates, but they must not by themselves create a hard
  targeted detection or absence decision.

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
- Lessons learned from targeted validation should feed back into untargeted
  evidence calibration at the rule level: candidate completeness, anchor-aware
  RT context, candidate-aligned product/NL evidence, morphology review semantics,
  and legacy-score retirement. Do not copy targeted labels or per-row fixes into
  untargeted identity.
- Untargeted behavior should be optimized against known table-level outcomes as
  a global consistency problem, not a patch queue. A targeted-backed correction
  must name the shared evidence rule it changes, the known cases it improves,
  and the guard cases that prove it did not merely overfit one target/sample.
- In untargeted shared-identity activation, RAW-overlay or raw-mode grouping is a
  hypothesis source, not a permanent veto. It must not change product labels by
  itself, but it also must not mask a named wrong-peak conflict or a complete
  positive evidence chain with machine-observed MS1 shape/pattern and
  candidate-aligned MS2/NL support.
- `family_projection` rows are unresolved projection rows, not canonical
  identity proof. A canonical-only matrix surface may exclude them and report
  excluded row/cell counts, but that exclusion remains incomplete scope and must
  not pass a complete row-identity gate. The full legacy family matrix is
  canonical only after projection rows are replaced by explicit PeakHypothesis
  assignments or a reviewed product contract says those rows are out of scope.
