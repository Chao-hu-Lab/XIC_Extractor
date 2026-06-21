# Untargeted LC-MS Feature Discovery Background

Date: 2026-06-21

Status: background research / concept alignment. This note is not product
authority, not a schema change, and not a ProductWriter activation decision.

## Why this note exists

The current CID-NL discussion was drifting because two questions were mixed:

1. **Feature inclusion:** did untargeted discovery find a real MS1 feature with
   credible evidence?
2. **Identity replacement:** should that feature replace, merge with, or dedupe
   an older row?

For untargeted LC-MS, the first question is intentionally broad-recall. If a
candidate has a credible neutral-loss tag and a real MS1 chromatographic peak,
the default posture should be: this is a feature candidate worth carrying
forward, not a failure just because an older source row also has a peak.

The second question is stricter. Replacement, merge, and ProductWriter authority
need identity/dedupe evidence because they can change matrix row identity,
double count signal, or move old cells to a new row.

## Short answer

Untargeted LC-MS workflows normally build a **feature table**: rows are
chromatographic features described by m/z, retention time, and sample
intensities. Identification or annotation is a later layer. Mature tools and
workflows repeatedly separate these concerns:

- MZmine describes the preprocessing goal as turning raw LC-MS data into a list
  of features and intensities across samples, then exporting those feature lists
  for downstream identification, library search, statistics, and visualization
  ([MZmine untargeted LC-MS workflow](https://mzmine.github.io/mzmine_documentation/workflows/lcmsworkflow/lcms-workflow.html)).
- XCMS describes preprocessing as chromatographic peak detection, sample
  alignment, and correspondence analysis to create feature abundances
  ([xcms LC-MS preprocessing](https://sneumann.github.io/xcms/articles/xcms.html)).
- OpenMS / pyOpenMS states the universal untargeted workflow consists of
  feature detection in individual files and linking them to consensus features
  with common m/z and RT values; adduct detection and MS2 annotation are
  additional optional steps
  ([pyOpenMS untargeted preprocessing](https://github.com/openms/pyopenms-docs/blob/master/docs/source/user_guide/untargeted_metabolomics_preprocessing.rst)).
- GNPS Feature-Based Molecular Networking expects a feature quantification
  table plus an MS/MS spectral summary from upstream processing tools; it does
  not replace feature detection
  ([GNPS FBMN documentation](https://ccms-ucsd.github.io/GNPSDocumentation/featurebasedmolecularnetworking/)).

So the better framing for CID-NL is:

> CID-NL/MS2 evidence helps discover, annotate, and prioritize MS1-backed
> features. It should not be reduced to "successor must replace source."

## Core concepts

### Feature

A feature is an observed LC-MS signal, typically anchored by m/z and RT, with a
chromatographic shape and intensity/area in one or more samples. In our repo's
future-facing vocabulary, a product row should be a `PeakHypothesis`, not merely
a legacy family id.

Feature existence is not the same as compound identification. A feature may be:

- fully identified with a standard;
- putatively annotated by MS/MS/library/evidence;
- class-annotated by diagnostic fragments or neutral losses;
- unknown but still quantitatively useful.

This matters for untargeted analysis: unknown or partially annotated features
are still valid rows for discovery and statistics if the MS1 evidence is sound.
The MSI reporting framework explicitly separates identification confidence
levels, with Level 1 requiring authentic-standard comparison and lower levels
covering putative annotations or unknowns
([MSI CIMR summary](https://github.com/MSI-Metabolomics-Standards-Initiative/CIMR)).

### Annotation / evidence

MS/MS spectra, diagnostic product ions, neutral losses, isotope patterns,
adducts, library hits, CCS, and RT priors are evidence attached to a feature.
They increase confidence or explain chemical class, but they are not the only
reason a feature row may exist.

Recent reviews and tools emphasize that LC-MS untargeted metabolomics often has
limited structural annotation coverage. TidyMass2 notes that only a minority of
features are typically annotated through MS2 spectral matching, while many
unannotated features still carry biological information
([TidyMass2 Nature Communications](https://www.nature.com/articles/s41467-026-68464-7)).

### Feature inclusion

Feature inclusion asks:

> Is this a real enough MS1 feature to be carried in the untargeted matrix or
> reviewable feature table?

For CID-NL specifically, a strong inclusion argument is:

- neutral-loss / product-ion evidence supports a tag or compound class;
- the inferred or scan-anchored precursor maps to a real MS1 chromatographic
  peak;
- the feature has stable provenance: sample, m/z, RT window, peak bounds,
  intensity/area, and MS2 scan linkage;
- duplicates, isotopes, adducts, and co-isolation are handled or at least
  flagged.

If these are true, "the old source row also has a peak" is not a reason to reject
the new feature. It only means we have a dedupe/replacement question.

### Identity replacement / dedupe

Identity replacement asks:

> Should the new feature replace, merge with, or dedupe an older row?

This is where source-vs-successor overlays are useful. They are not asking
"does successor exist?" They are asking whether the successor should inherit or
rewrite an old identity relationship.

Possible outcomes:

- **new feature:** successor is valid and should exist separately;
- **replacement:** successor is valid and source was a stale/incorrect row;
- **merge/dedupe:** both evidence paths refer to the same underlying feature or
  ion state;
- **co-existing features:** both rows have real peaks and should not be merged
  without stronger identity evidence;
- **review-only:** evidence is too ambiguous, chimeric, noisy, or duplicate.

This distinction is central. A successor can be a valid untargeted feature even
when it is not valid as a replacement for source.

## How CID-NL fits

CID-NL Discovery is not merely "look for one NL tag and see whether MS1 has a
peak", but that is the correct minimum intuition:

1. Find MS2 scans with a diagnostic product / neutral-loss relationship.
2. Infer or verify a precursor feature candidate.
3. Check whether the corresponding MS1 trace has a chromatographic peak.
4. Attach the tag/evidence to the MS1-backed feature.
5. Decide product role separately: new row, replacement, merge/dedupe,
   review-only, or reject.

The previous deep-research note already reached the same mature-tool conclusion:
row identity should be MS1-feature-first, while scan precursor and
`product + neutral loss` are evidence paths
([repo note](LC-MS%20CID%20Neutral%20Loss%20Discovery.md)).

## What this changes in our interpretation

The old wording "successor authority candidate" was too replacement-heavy for
an untargeted workflow. It made it sound as if a discovered successor had to
prove source was wrong before it could matter. That is not the right default.

Better terms:

- `nl_ms1_feature_candidate`: NL-supported MS1 feature candidate.
- `feature_inclusion_supported`: enough evidence to carry as a feature row or
  product candidate.
- `identity_relationship_unresolved`: feature may be real, but relationship to
  old source is not settled.
- `replacement_supported`: evidence supports successor replacing source.
- `coexisting_feature_supported`: both source and successor can remain distinct.
- `dedupe_or_merge_needed`: likely same underlying feature/ion family, but
  requires controlled merge policy.

For the 78 paired overlays, the key question should not be "which one wins?"
for every row. It should be:

1. Does successor have NL evidence plus MS1 feature support?
2. If yes, is it a new/co-existing feature, a replacement, or a dedupe case?
3. Which cells, if any, can be written without duplicate counting or identity
   drift?

## Practical product rule for XIC Extractor

Use a two-gate model:

### Gate A: feature inclusion gate

Accept a CID-NL discovered feature into the untargeted candidate/product path
when:

- MS1 peak exists and is not a noise-only trace;
- CID-NL/MS2 evidence is tied to the feature by RT/m/z/provenance;
- candidate row identity is stable enough to emit as a `PeakHypothesis` or
  reviewable candidate;
- duplicate/isotope/adduct/co-isolation risk is represented in sidecars.

This gate is broad-recall by design.

### Gate B: identity authority gate

Allow replacement, merge, dedupe, or old-cell migration only when:

- source and successor relationship is explicit;
- sample-level evidence supports one identity relationship;
- duplicate counting is prevented;
- old and new row provenance are preserved;
- expected diff is defined before ProductWriter or default matrix behavior
  changes.

This gate is conservative by design.

## Source / Successor redefinition for current artifacts

Current Gallery language should be read like this:

- `Source`: previous/legacy row identity or old hypothesis.
- `Successor`: new CID-NL / Discovery-derived hypothesis linked to source by a
  migration/differential review artifact.

That relationship is useful for dedupe/replacement review, but it is too narrow
for untargeted feature inclusion. If source and successor both have peaks, the
correct interpretation may be:

- both are real features;
- successor should be included as a feature candidate;
- replacement is unresolved or not supported.

Therefore, "both have full peak shapes" should not be scored as automatic
failure. It should usually become either `coexisting_feature_supported` or
`identity_relationship_unresolved`, depending on dedupe evidence.

## Consequences for the current CID-NL gate

The next product decision should be reframed:

Old framing:

> Can the 147 successor writes replace source authority?

Better framing:

> Which CID-NL/MS1-supported successor hypotheses deserve feature inclusion, and
> which of them also justify source replacement, merge, or dedupe?

This preserves the Backfill/ProductWriter safety boundary while respecting the
untargeted goal of broad feature discovery.

## What can still block product matrix inclusion

Even in an untargeted workflow, feature inclusion is not "anything with a bump".
Reasonable blockers are:

- no real MS1 chromatographic peak;
- poor S/N or unstable trace quality;
- NL/MS2 evidence cannot be tied to the MS1 peak by RT/m/z/provenance;
- likely chimeric MS2 with multiple plausible features and no dominant owner;
- duplicate isotope/adduct/same-feature row inflation;
- candidate would write the same sample value into multiple product rows;
- expected diff is unknown for any public-surface activation.

These are QC and identity-control blockers, not arguments against broad
untargeted discovery.

## Repo-facing design implication

The repo's existing direction already supports this if we keep the layers
separate:

- `DiscoveryCandidate` states such as `ms1_feature_nl_supported` and
  `ms1_feature_nl_rescued` are feature/evidence states.
- `PeakHypothesis` should be the internal matrix row identity.
- `alignment_matrix.tsv` / workbook `Matrix` should stay clean; identity and
  provenance belong in sidecars.
- CID-NL/MS2 evidence should feed `EvidenceVector` / identity facts, not bypass
  them into ProductWriter authority.

## Sources checked

- MZmine untargeted LC-MS workflow:
  <https://mzmine.github.io/mzmine_documentation/workflows/lcmsworkflow/lcms-workflow.html>
- XCMS LC-MS preprocessing:
  <https://sneumann.github.io/xcms/articles/xcms.html>
- pyOpenMS untargeted preprocessing:
  <https://github.com/openms/pyopenms-docs/blob/master/docs/source/user_guide/untargeted_metabolomics_preprocessing.rst>
- OpenMS FeatureFinderMetabo:
  <https://openms.de/documentation/TOPP_FeatureFinderMetabo.html>
- MS-DIAL overview/tutorial:
  <https://systemsomicslab.github.io/compms/msdial/main.html>
  and <https://systemsomicslab.github.io/mtbinfo.github.io/MS-DIAL/tutorial.html>
- GNPS Feature-Based Molecular Networking:
  <https://ccms-ucsd.github.io/GNPSDocumentation/featurebasedmolecularnetworking/>
- MSI / CIMR metabolite identification levels:
  <https://github.com/MSI-Metabolomics-Standards-Initiative/CIMR>
- Trackable/scalable LC-MS processing and feature correspondence issues:
  <https://www.nature.com/articles/s41467-023-39889-1>
- TidyMass2 and annotation bottleneck:
  <https://www.nature.com/articles/s41467-026-68464-7>
