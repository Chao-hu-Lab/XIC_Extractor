# Instrument QC HCD Audit v1 Decision

## Verdict

`hcd_audit_ready`

HCD/Product-ion audit plumbing is working and is now useful as a human review
surface. This branch should still not promote HCD into a hard pass/fail gate,
but the previously confusing review items were traced to stale or too-narrow
Mix STDs RT priors/windows and a cross-batch LEK prior.

## Real-Data Smoke

Run:

```powershell
uv --cache-dir .uv-cache run python scripts\run_instrument_qc.py `
  --raw-dir "C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R" `
  --output-dir output\instrument_qc\hcd_audit_v1_sdolek_whcd_review_20260520 `
  --mode sdolek `
  --method-doc "C:\Users\user\Desktop\NTU cancer\2025台大乳癌組織數據for Jia\20260105中研院台大Breast cancer tissue\20260105 中研院分析.docx" `
  --emit-mixstds `
  --mixstds-target-registry config\MixSTDs.csv `
  --emit-hcd-audit
```

Artifacts:

- `instrument_qc_sdolek_trend.tsv`
- `instrument_qc_mixstds_trend.tsv`
- `instrument_qc_hcd_audit.tsv`
- `instrument_qc_hcd_audit.json`
- `instrument_qc_trend_sdolek.xlsx`

MS1 trend hash guard:

- `instrument_qc_sdolek_trend.tsv`: row count/schema unchanged.
- `instrument_qc_mixstds_trend.tsv`: row count/schema unchanged.
- Updating `config\MixSTDs.csv` RT windows intentionally changes Mix STDs
  selected RT values for the affected targets.

## Observed Counts

- SDOLEK MS1 rows: 22
- Mix STDs MS1 rows: 192
- HCD audit rows: 214
- Mix STDs MS1 status:
  - `detected`: 192
- HCD statuses:
  - `hcd_supported`: 211
  - `no_product_match`: 3
- Activation:
  - `wHCD`: 22
  - `CIDwHCD`: 192
- Mapping source:
  - `label_base_letter`: 188
  - `sdolek_builtin`: 22
  - `unmapped`: 4

Workbook sheets:

- `Overview`
- `SDOLEK Trend`
- `Mix STDs Trend`
- `HCD Audit`
- `Manual Review Queue`
- `Diagnostics`

Manual review queue is a human-facing aggregate, not one raw row per issue.
Full row-level detail remains in `HCD Audit`.

- Review items: 0

## Interpretation

SDO/LEK:

- Every SDO/LEK detected MS1 row has `hcd_supported`.
- SDOLEK is now loaded as `activation_method=wHCD` from the method-detail table
  for `20260105 SDOLEK`, not from the short sequence-table method name alone.
- SDOLEK uses its own built-in SDO/LEK product table. It does not use the Mix
  STDs generic base pattern. Expected product count is 4 per SDO/LEK row
  because only wHCD products are searched for this method.
- Raw-only SDOLEK files that are present under the SDOLEK folder but not listed
  as exact sequence rows remain `match_status=unmatched`; they still inherit the
  unique docs-derived SDOLEK method context (`20260105 SDOLEK`, `wHCD`) so the
  HCD audit does not silently fall back to `unknown`.
- The HCD support suggests the selected SDO/LEK MS1 peaks are chemically
  plausible. It remains audit evidence, not a hard production gate.
- The old NoSplit LEK RT prior came from a different batch. The real 20260106
  LEK rows are internally stable enough for this QC surface, so the workbook no
  longer escalates cross-batch prior mismatch into `Manual Review Queue`.

Mix STDs:

- Most targets now have product-ion support. Rows that looked like product
  failures or non-detections were RT-window/prior problems: expected product or
  neutral-loss evidence existed elsewhere in the same run.
- HCD review now uses the uppercase base letter in the target label before
  fallback heuristics. For example, `5-hmdC` and `5-cadC` map to C,
  `8-oxo-dA` maps to A, Guo labels map to G, and U labels map to U. Isotope
  brackets such as `[13C,15N2]` are ignored before parsing the base letter.
  `Y` remains unmapped/manual-review because it should not be forced into a
  generic G/A/C/T/U pattern.
- U product-ion review uses initial audit-only masses:
  `U=112.0273`, `U+H=113.0346`, `U+H-NH3=96.0080`, `U+H-H2O=95.0240`,
  and `U_new=70.0293`.
  The uracil exact mass comes from PubChem/KEGG-style monoisotopic mass, and
  the 96/95/70 nominal fragment pattern is literature-supported for protonated
  uracil fragmentation. These remain audit evidence, not production gates.
- `CIDwHCD` is treated as mixed evidence, not as HCD-only. For Mix STDs, CID
  and HCD are both collision-based MS/MS evidence. Neutral-loss evidence uses
  the existing target `neutral_loss_da` pattern (`dR/R/MeR`) and is labeled with
  the acquisition context, for example `CIDwHCD:NL-116.0474`. HCD/base evidence
  still uses the base product pattern.
- `no_product_match` rows generally have nearby MS2 triggers: among rows with
  a precursor-matched MS2 scan, the apex-MS2 delta is small enough that RT drift
  alone does not explain most missing product matches.
- `5-hmdC` is no longer promoted to the manual queue when the same-sample
  isotope companion (`d3-5-hmdC`) has product/neutral-loss support. Its row-level
  RT-window evidence remains visible in `HCD Audit`, but it is not presented as
  a priority problem.
- `Y` remains outside the current base-product review scope. Its row-level facts
  remain in `HCD Audit`, but it is not a priority queue item until an explicit
  product group is supplied.
- `config\MixSTDs.csv` was updated for this batch:
  - `5-cadC`: `11.20-12.70` min.
  - `N6-6Ah-dA`: `19.30-20.80` min.
  - `t6A`: `30.30-33.90` min.
- After rerun, all 192 Mix STDs rows are MS1 detected. `5-cadC`,
  `N6-6Ah-dA`, and `t6A` now have in-window product/neutral-loss support.
- Remaining `target_rt_window_review` flags are row-level context only:
  isotope-supported `5-hmdC` cases and the unmapped `Y` row are not priority
  review items.

Blank:

- Blank remains out of compound identity scope.
- Current stance is `blank_defer`.
- Future value is baseline/carryover/wash sanity check, not target evidence.

## Next Gap

The next useful work is not changing production scoring. It is tightening HCD
review inputs and lifecycle interpretation:

1. Add explicit `hcd_base_group` or `hcd_product_group` for Mix STDs targets
   where heuristic mapping is weak or unmapped.
2. Decide whether `Y` needs an explicit product group or should remain outside
   HCD identity review.
3. Keep HCD/Product-ion support as audit evidence until multiple batches show
   the same behavior.
