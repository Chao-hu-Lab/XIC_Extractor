# Skyline Expressibility Runbook

Status: `diagnostic_only`

This runbook prepares the next executable comparison against Skyline. It does
not claim Skyline has been run on the fixture yet.

## Inputs

- Candidate Skyline transition list:
  `docs/superpowers/reports/2026-06-15-skyline-three-pair-transition-list.csv`
- XIC decision oracle:
  `docs/superpowers/reports/2026-06-15-xic-skyline-expressibility-oracle.csv`
- XIC reference workbook:
  `local_validation_artifacts/targeted_gt_workbooks/8raw/xic_results_20260512_1151.xlsx`
- Candidate same-sample mzML manifest:
  `docs/superpowers/reports/2026-06-15-skyline-8raw-mzml-manifest.csv`

The mzML manifest is useful for the first expressibility test only. It does
not test XIC's Thermo RAW fidelity or skipped-conversion workflow advantage.

## Install / Locate Gate

Current workstation checks did not locate a MacCoss Skyline executable on
`PATH`, and package-manager search did not find a usable MacCoss Skyline package.
The official Skyline 25.1 Unplugged ZIP was downloaded under `output/` and
`SkylineCmd.exe` runs in place.

Before execution, locate one of:

- `C:\Program Files\Skyline\Skyline.exe`
- `C:\Program Files\Skyline\SkylineCmd.exe`
- an unpacked Skyline "Unplugged" install containing `Skyline.exe` and
  `SkylineCmd.exe`

Current local executable:

`output/external_tools/skyline/Skyline-64_25_1_0_237/Skyline-64_25_1_0_237/Application Files/Skyline_25_1_0_237/SkylineCmd.exe`

Current smoke:

`Skyline (64-bit) 25.1.0.237 (519d29babc)`

Official install references gathered for this preflight:

- MacCoss Lab Skyline resource summary:
  <https://maccosslab.org/resources/>
- Skyline small molecule quantification tutorial:
  <https://skyline.ms/tutorials/25-1/SmallMoleculeQuantification/en/>
- ProteoWizard/Skyline data-access project:
  <https://proteowizard.sourceforge.io/>

If installer access requires account login or license acceptance, stop and let
the human complete that step. Do not script around a click-through agreement.

## Manual Import Path

1. Open Skyline.
2. Create a new empty small-molecule document.
3. Use `Edit > Insert > Transition List`.
4. Paste or import:
   `2026-06-15-skyline-three-pair-transition-list.csv`.
5. In the Skyline column-identification dialog, map the columns in this order:
   `Molecule List Name`, `Molecule Name`, `Label Type`, `Note`,
   `Precursor m/z`, `Precursor Charge`, `Product m/z`, `Product Charge`,
   `Cone Voltage`, `Explicit Collision Energy`, `Explicit Retention Time`.
6. Verify that the six precursor rows import as three molecule pairs, with each
   analyte represented by a `light` precursor and its ISTD represented by a
   `heavy` precursor. If Skyline imports the heavy ISTD as a separate molecule,
   the input is not a valid native light/heavy ratio test.
7. Import the matching data files only if they are the same sample set used by
   `xic_results_20260512_1151.xlsx`. The checked local mzML manifest can be
   used for a first expressibility run, but a RAW-backed run remains a separate
   fidelity test.
8. Export a Skyline report with at least:
   target name, replicate/sample, RT, area, transition/product information,
   peak-picked status, and any available notes/annotations.

## CLI Path

Use the CLI only after `SkylineCmd.exe` is located. The exact command depends on
the Skyline install and report template, so this runbook intentionally does not
pretend to have a working command before the executable exists.

Candidate command shape:

```powershell
& "C:\Program Files\Skyline\SkylineCmd.exe" --help
```

The first executable smoke check is help/version output, not RAW import.

## Pass / Partial / Fail

Full pass:

- Skyline imports all six transition-list rows.
- Skyline exports RT and area for all target/ISTD pairs.
- Skyline can encode or export neutral-loss evidence as reusable method state.
- Skyline can preserve the XIC distinction between `accepted` and
  `review only, not counted` without a custom post-export script.

Partial pass:

- Skyline extracts comparable RT/area and supports manual review, but the
  `not_counted` decision must be reconstructed outside Skyline.

Fail:

- Skyline can quantify chromatograms but cannot carry the evidence policy that
  decides whether an observed area is formally counted.

## Why This Is The Right First Test

The strongest XIC differentiator is not peak extraction. It is the product
projection layer: a measured area is not automatically a counted detection.
The `8-oxo-Guo` case is therefore more valuable than another clean positive
control because it tests decision authority, not only quantitation.
