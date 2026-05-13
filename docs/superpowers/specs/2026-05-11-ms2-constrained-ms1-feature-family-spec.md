# MS2-Constrained MS1 Feature Family Spec

## Summary

Untargeted alignment should not be an FH-style MS2-trigger table, and it should
not become an mz/RT-only MS1 feature table.

The intended model is:

```text
MS2/NL evidence constrains chemical identity.
MS1 peak evidence decides which triggers belong to one chromatographic feature.
MS1 backfill measures missing samples.
MS1 ownership prevents duplicate area claims.
Output must preserve those meanings instead of flattening them into one status.
```

This spec fixes the algorithm contract before more output or visualization work.

## Problem

The current implementation has drifted from the intended model:

- `rescued` / MS1-backfilled cells can contribute to feature-family merge
  evidence.
- family-centered MS1 integration labels any found peak as `detected`, even when
  the sample had no original MS2/discovery event.
- duplicate MS1 peak ownership can be encoded as ordinary `absent`.

Those behaviors make the output look cleaner, but they blur identity,
measurement, and reporting. The result is hard to trust.

## Core Definitions

| Term | Meaning |
|---|---|
| MS2 event cluster | Cross-sample grouping of original discovery candidates constrained by NL tag, m/z, RT, product m/z, and observed neutral loss. |
| Original detected evidence | A sample has a discovery candidate that belongs to the feature or event cluster before MS1 backfill. |
| MS1 feature family | One chromatographic feature represented by one or more compatible MS2 event clusters. |
| Family-centered integration | Re-extracting MS1 XIC at the family center to measure a sample. |
| Backfill / rescued | Family-centered MS1 integration found a peak in a sample without original detected evidence. |
| Duplicate assignment | A sample-level MS1 peak is claimed by multiple feature families, so one row owns the area and the others must be marked as duplicate-assigned, not ordinary absent. |

## Decision Layers

### Layer 1: MS2 Event Cluster Identity

This decides whether original discovery candidates represent the same
NL-compatible chemical hypothesis.

```text
+-------------+----------+----------+------------+----------------------+------------------+
| Same NL tag | m/z near | RT near  | Product/NL | Full MS2 pattern     | Same event clust |
+-------------+----------+----------+------------+----------------------+------------------+
| no          | any      | any      | any        | any                  | NO               |
| yes         | no       | any      | any        | any                  | NO               |
| yes         | yes      | no       | any        | any                  | NO               |
| yes         | yes      | yes      | conflict   | any                  | NO               |
| yes         | yes      | yes      | compatible | unavailable (CID v1) | YES, CID/NL only |
| yes         | yes      | yes      | compatible | compatible (future)  | YES, stronger    |
| yes         | yes      | yes      | compatible | conflict (future)    | NO               |
+-------------+----------+----------+------------+----------------------+------------------+
```

CID v1 must describe this as `CID/NL-compatible`, not full MS2 pattern matching.

### Layer 2: MS1 Feature Family Identity

This decides whether compatible event clusters are actually one chromatographic
feature.

```text
+-------------------+------------------+------------------+------------+--------------+
| Shared detected   | Rescued overlap  | MS1 peak overlap | Apex near  | Same family  |
+-------------------+------------------+------------------+------------+--------------+
| no                | no/yes           | any              | any        | NO           |
| yes, too few      | any              | any              | any        | NO / REVIEW  |
| yes               | any              | no               | no         | NO           |
| yes               | any              | yes              | yes/no     | YES          |
| yes               | any              | no               | yes        | YES, cautious|
| no                | yes only         | yes              | yes        | NO           |
+-------------------+------------------+------------------+------------+--------------+
```

Hard rule:

```text
rescued/backfilled overlap cannot create family merge eligibility
```

Backfill can support measurement completeness, but it must not prove identity.
Otherwise the algorithm becomes circular:

```text
guess two clusters are related -> backfill both near the same center -> use that
backfill result as proof that they are related
```

### Layer 3: Per-Sample Measurement Status

This decides what a sample-cell means after family-centered integration.

```text
+-------------------+-----------------------+--------------------+--------------------+
| Original detected | Family MS1 peak found | Ownership conflict | Cell status        |
+-------------------+-----------------------+--------------------+--------------------+
| yes               | yes                   | no                 | detected           |
| yes               | yes                   | loses ownership    | duplicate_assigned |
| yes               | no                    | no                 | absent             |
| no                | yes                   | no                 | rescued            |
| no                | yes                   | loses ownership    | duplicate_assigned |
| no                | no                    | no                 | absent             |
| not eligible      | any                   | no                 | unchecked          |
| malformed trace   | any                   | any                | unchecked          |
+-------------------+-----------------------+--------------------+--------------------+
```

`detected` means original discovery/MS2 evidence exists for the sample-feature
cell. `rescued` means MS1 measurement was found without original detected
evidence.

### Layer 4: Matrix Value

This decides what enters the area matrix.

```text
+--------------------+--------------+------------------------------+
| Cell status        | Area > 0      | Matrix value                 |
+--------------------+--------------+------------------------------+
| detected           | yes          | area                         |
| rescued            | yes          | area                         |
| absent             | any          | blank                        |
| unchecked          | any          | blank                        |
| duplicate_assigned | any          | blank + review/QC disclosure |
| non-finite/<=0     | any          | blank                        |
+--------------------+--------------+------------------------------+
```

Production output may keep the matrix cell blank for `duplicate_assigned`, but
review/HTML/metadata must preserve that it was duplicate-assigned rather than
ordinary absence.

## Required Code Behavior

1. Feature-family merge eligibility uses original detected cells only.
2. Feature-family evidence strings that say `shared_detected` must count detected
   samples only.
3. Family-centered integration sets:
   - `detected` when the sample had original event membership and the family
     XIC peak is found.
   - `rescued` when the sample had no original event membership, the family is
     eligible for backfill, and the family XIC peak is found.
   - `absent` when checked and no acceptable peak is found.
   - `unchecked` when not eligible or the trace cannot be evaluated.
4. Duplicate ownership losers use status `duplicate_assigned`, not `absent`.
5. Matrix area writers write values only for `detected` and `rescued`.
6. Status/debug outputs preserve `duplicate_assigned`.
7. Review counts must not hide duplicate assignments. Either expose a
   duplicate-assigned count or include a deterministic reason phrase.

## Non-Goals

- Do not implement XLSX or HTML production output in this algorithm cleanup.
- Do not tune ppm/RT thresholds.
- Do not add HCD/full-fragment pattern matching.
- Do not replace the discovery pipeline.
- Do not remove TSV writers; they remain machine/debug/validation surfaces.

## Acceptance Criteria

- A pair of event clusters with rescued-only overlap does not become one
  `MS1FeatureFamily`.
- Shared detected counts ignore rescued cells.
- Family-centered integration preserves detected versus rescued semantics.
- Duplicate peak ownership no longer encodes losers as ordinary absence.
- Existing matrix value contract remains blank for absent, unchecked,
  duplicate-assigned, zero, negative, and non-finite area.
- Narrow tests for feature-family, family integration, and TSV writers pass.
- No real RAW validation is required for this cleanup, but 8-raw validation is
  recommended before using the outputs for method judgment.
