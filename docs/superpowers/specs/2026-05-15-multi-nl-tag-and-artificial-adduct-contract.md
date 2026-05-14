# Multi-NL Tag And Artificial Adduct Contract

## Goal

Extend untargeted discovery beyond a single DNA `dR` neutral-loss profile while
keeping the final matrix identity clean. Multi-tag evidence should increase the
amount and quality of discovery evidence, not create one primary matrix row per
tag, one row per adduct, or one row per weak single-sample observation.

Phase A is neutral-loss only. The first multi-tag set is:

```text
dR / R / MeR
```

The FeatureHunter parameter tables are treated as discovery configuration and
annotation references:

- `Feature_List_urine_Malignancy_R.csv` defines the neutral-loss tag catalog
  used by Phase A. Product-ion rows may be parsed as deferred catalog metadata,
  but they are not selectable discovery profiles in this phase.
- `Artificial_Adduct_List.csv` defines expected ESI artifact m/z differences
  between related co-eluting features.

These references can support discovery, review, family consolidation, and
artifact annotation. They must not bypass the final matrix identity contract.

## Literature And Domain Basis

ESI-LC-MS can generate multiple detected features from one underlying analyte:
protonated ions, metal or solvent adducts, multimers, isotopes, neutral losses,
and in-source fragments. These related features usually have close retention
time or co-elution and predictable m/z relationships. Established tools such as
CAMERA and Binner use RT proximity, EIC or across-sample intensity correlation,
and known m/z relationships to annotate related ion features.

This project should follow the same direction but keep annotation separate from
primary matrix identity:

```text
multi-tag / adduct evidence
  -> richer family evidence and audit annotations
  -> one selected representative family in Matrix
  -> related or weak evidence retained in Review/Audit
```

References:

- Ion annotation-assisted LC-MS analysis:
  `https://proteomesci.biomedcentral.com/articles/10.1186/1477-5956-10-S1-S8`
- Binner feature annotation:
  `https://academic.oup.com/bioinformatics/article/36/6/1801/5603305`
- ESI complexity in untargeted metabolomics:
  `https://research.birmingham.ac.uk/en/publications/characterization-of-electrospray-ionization-complexity-in-untarge`
- LC-MS artifact ions:
  `https://www.chromatographyonline.com/view/the-origin-and-implications-of-artifact-ions-in-bioanalytical-lc-ms`

## Scope

### In Scope

- Parse FH `Feature_List` as a neutral-loss tag-profile catalog.
- Parse FH `Artificial_Adduct_List` as an artifact delta catalog.
- Support user-selected tag subsets.
- Support explicit `union` and `intersection` tag-selection modes.
- Record per-candidate and per-family tag evidence.
- Annotate likely artificial adduct relationships between feature families.
- Keep Primary Matrix output gated by `include_in_primary_matrix`.
- Preserve extra tag/adduct evidence in Review/Audit.
- Add diagnostics that show whether multi-tag discovery improves evidence or
  only inflates candidates.

### Out Of Scope

- Do not automatically expand targeted workbook labels from FH tag names.
- Do not use targeted labels inside production discovery or alignment logic.
- Do not implement product-ion tag matching in Phase A.
- Do not make `[M+H]+` mandatory for final row identity.
- Do not add a new Discovery worksheet in this phase.
- Do not connect iRT/LOESS into promotion gates in this phase.
- Do not change downstream DNP or MetaboAnalyst contracts.
- Do not merge DNA and RNA tag policies without an explicit selected-tag
  configuration.

## FH Feature List Contract

The FH feature list is a CSV with these relevant columns:

| Column | Meaning |
|---|---|
| `Tag No.` | Stable FH row number. |
| `Tag Category` | Tag type. Category `1` means neutral-loss evidence. Category `2` is product-ion metadata and is deferred in Phase A. |
| `Tag Parameters (Da or m/z)` | Neutral-loss mass for category `1`. |
| `Mass Tolerance (ppm)` | Per-tag mass tolerance. |
| `Intensity Cutoff (height)` | Per-tag signal floor. |
| trailing unlabeled note column | Human tag label such as `NL: dR`. |

Parsed tag profile fields:

| Field | Example | Notes |
|---|---|---|
| `tag_id` | `1` | From `Tag No.`. |
| `tag_kind` | `neutral_loss` | Phase A selectable profiles are neutral-loss only. |
| `tag_label` | `NL: dR` | Preserve the FH text but normalize whitespace. |
| `tag_name` | `dR` | Text after `NL:`. |
| `parameter_mz_or_da` | `116.047344` | Neutral-loss Da for Phase A selectable profiles. |
| `mass_tolerance_ppm` | `20` | Per-tag matching tolerance. |
| `intensity_cutoff` | `10000` | Minimum product intensity or ion height threshold. |

Category `2` rows are tolerated as deferred product-ion metadata so the full FH
feature list can be loaded. They must not be returned by default selected-profile
resolution, and selecting a `PI:` tag must fail clearly. Unknown categories are
rejected until a new contract defines their semantics.

## Tag Selection Contract

Tag selection is explicit. A multi-tag run must record both the catalog and the
selected profile set in metadata.

Minimum public configuration:

| Config | Meaning |
|---|---|
| `feature_list_path` | FH feature-list CSV. |
| `selected_tags` | List of neutral-loss tag names or labels selected by the user. Phase A starts with `dR,R,MeR`. |
| `tag_combine_mode` | `union` or `intersection`. |
| `tag_kind_filter` | Deferred. Phase A is always `neutral_loss`. |

Default compatibility behavior remains single-profile DNA `dR` discovery until
the user supplies a feature-list path and selected tags.

### Union Mode

`union` means a candidate may be seeded or supported by any selected tag.

Rules:

- A seed with one selected tag can become discovery evidence.
- Multiple matching tags on the same precursor/RT strengthen the same candidate.
- Union mode must not create separate primary matrix rows solely because the same
  precursor/RT has multiple tag labels.
- If multiple tags produce near-identical candidate identities, the tag evidence
  is merged at the family level.
- Cross-tag grouping uses sample identity, precursor m/z, and RT/MS1 peak
  overlap. Product m/z and observed neutral loss remain per-tag evidence and are
  not required to be equal across different selected tags.

### Intersection Mode

`intersection` means a family must carry evidence for all required selected tags
before it can claim intersection support.

Rules:

- Intersection is evaluated at family level by default, not necessarily in the
  same MS2 scan.
- Sample-level intersection can be reported as a stricter diagnostic, but it is
  not the default promotion rule.
- Missing one selected tag does not delete the candidate. It marks
  `tag_intersection_status = incomplete` and keeps the evidence in Review/Audit
  unless another gate promotes the family.

## Multi-Tag Evidence Schema

Discovery candidates and aligned families should expose these fields where the
surface can carry them:

| Field | Meaning |
|---|---|
| `selected_tag_count` | Number of selected tags in the run. |
| `matched_tag_count` | Number of selected tags observed for the candidate/family. |
| `matched_tag_names` | Semicolon-delimited normalized tag names in selected-tag order. |
| `primary_tag_name` | Best representative tag for sorting and compatibility. |
| `tag_combine_mode` | `single`, `union`, or `intersection`. |
| `tag_intersection_status` | `not_required`, `complete`, or `incomplete`. |
| `tag_evidence_json` | Compact JSON with per-tag ppm, RT, product m/z, intensity, and source scan counts. |

Primary Matrix outputs should not include `tag_evidence_json`. Review/Audit and
machine-readable diagnostics may include it.

## Artificial Adduct List Contract

The artificial adduct list is a CSV with these columns:

| Column | Meaning |
|---|---|
| `Artificial Adduct No.` | Stable FH row number. |
| `Artificial Adduct m/z` | Expected m/z difference between related features. |
| `Artificial Adduct Name` | Human adduct relation label, such as `M+Na-H`. |

Parsed artificial adduct fields:

| Field | Example |
|---|---|
| `adduct_id` | `1` |
| `mz_delta` | `21.981945` |
| `adduct_name` | `M+Na-H` |

Adduct matching is a relationship annotation between feature families, not a
new discovery seed and not a Phase A promotion/demotion gate.

Minimum matching evidence:

- family RT delta within an adduct RT window;
- absolute m/z delta matches a configured artificial-adduct delta within ppm or
  absolute Da tolerance;
- both families are visible in Review/Audit;
- if enough shared samples exist, report area correlation across shared detected
  samples.

Default diagnostic thresholds:

| Threshold | Default |
|---|---|
| `adduct_rt_window_min` | `0.05` |
| `adduct_mz_tolerance_ppm` | `10` |
| `adduct_min_shared_samples` | `3` |
| `adduct_area_spearman_warn` | `0.60` |

Correlation is supporting evidence, not a hard exclusion by default. Common
adducts may have weaker correlation than expected because ion competition,
matrix effects, and source conditions can vary.

## Representative Selection Contract

When a group of families appears to represent the same analyte or an artificial
adduct cluster, the Primary Matrix should prefer one representative and keep the
rest as Review/Audit rows.

Representative preference order:

1. Strongest `production_family` support under the existing final matrix
   identity contract.
2. Higher detected support across samples.
3. Lower duplicate pressure.
4. Better RT consistency after existing drift correction.
5. Stronger multi-tag support.
6. `[M+H]+`-consistent family if the evidence is otherwise comparable.
7. Higher median quantitative area as a last deterministic tie-breaker.

`[M+H]+` is a preference, not a hard requirement. If `[M+H]+` is absent or weak,
the best supported ion family may remain the representative.

## Final Matrix Identity Interaction

This contract does not change the three final identity tiers:

- `production_family`
- `provisional_discovery`
- `audit_family`

Multi-tag support can increase confidence, but it cannot by itself override:

- single-sample-only evidence;
- rescue-only/backfill-only evidence;
- duplicate-only evidence;
- ambiguous-only evidence;
- consolidation-loser demotion.

Backfill still cannot create final row identity. Artificial adduct related rows
are annotation-only in Phase A/B. Demotion requires a later representative-winner
plan after real-data evidence shows it will not remove valid ISTD or stable
biological signals.

## Diagnostics

A multi-tag/adduct diagnostic run must report:

- selected tags and combine mode;
- candidate counts per tag;
- overlap matrix between selected tags;
- families with multiple tag support;
- `intersection` complete/incomplete counts;
- artificial adduct pair count by adduct name;
- representative/loss relationship counts, annotation-only in Phase A/B;
- Primary Matrix row count delta versus single `dR` baseline;
- Review/Audit retained evidence count;
- targeted ISTD benchmark result when a targeted benchmark workbook is supplied.

The diagnostic should answer this question before production promotion changes:

> Did multi-tag evidence improve family confidence and artifact annotation, or
> did it only inflate weak candidates?

## Validation Gates

### Unit Gates

- FH feature-list parser handles category `1` and tolerates deferred category
  `2` rows without selecting them.
- FH parser rejects unknown tag categories.
- tag selection accepts neutral-loss tag names and full `NL:` labels.
- tag selection rejects `PI:` labels in Phase A.
- union mode merges multiple matching tags into one candidate/family evidence
  record.
- intersection mode marks incomplete evidence without deleting rows.
- artificial adduct parser loads all rows and rejects invalid deltas.
- adduct matcher flags close RT and expected m/z delta relationships.
- representative selector prefers `[M+H]+` only as a tie-breaker.

### Real-Data Gates

Run in this order:

1. Single-tag `dR` 8RAW baseline.
2. Multi-tag 8RAW union diagnostic with the first selected NL set:
   `dR`, `R`, `MeR`.
3. Multi-tag 8RAW intersection diagnostic on a deliberately narrow pair only
   after union behavior is inspectable.
4. Artificial-adduct annotation on the 8RAW alignment output.
5. Strict targeted ISTD benchmark comparison.
6. 85RAW only after 8RAW shows no Primary Matrix row inflation.

Stop before 85RAW if:

- targeted ISTD benchmark regresses, excluding known targeted-side
  `d3-N6-medA` area mismatch;
- Primary Matrix row count inflates without matching production support;
- artificial adduct annotation changes any primary matrix identity;
- Review/Audit loses candidate evidence instead of annotating it.
