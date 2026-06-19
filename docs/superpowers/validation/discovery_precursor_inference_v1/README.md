# Discovery precursor inference validation v1

Date: 2026-06-19

Purpose: root-cause and validate the missing `d4-N6-2HE-dA`
`300.1605 -> 184.113` discovery row without running 85RAW or changing matrix
authority.

Root cause: CID-NL discovery treated the Thermo MS2 filter precursor as the
only exact precursor m/z. In the TumorBC2312_DNA RAW window, the MS2 filter
precursor can be an isolation/trigger mass such as `300.2028`, while the
observed product `184.1132` plus the configured dR neutral loss `116.0474`
infers the actual row hypothesis at `300.1606`. The old direct-only search
looked near `300.2028 - 116.0474 = 184.1554`, so it rejected the valid
`184.1132` product before grouping/alignment.

Validation command:

```powershell
.venv\Scripts\python.exe scripts\run_discovery.py --raw C:\Xcalibur\data\20260106_CSMU_NAA_Tissue_R\TumorBC2312_DNA.raw --dll-dir C:\Xcalibur\system\programs --output-dir docs\superpowers\validation\discovery_precursor_inference_v1\TumorBC2312_DNA --neutral-loss-tag DNA_dR --neutral-loss-da 116.0474 --rt-min 22 --rt-max 25 --ms2-precursor-tol-da 1.6 --resolver-mode local_minimum
```

Observed result in `TumorBC2312_DNA/discovery_candidates.csv`:

- `duplicate_candidate_ids=0`.
- `300.161 / 184.113` rows are emitted with
  `precursor_mz_basis=product_plus_neutral_loss`.
- `301.165 / 185.116` remains emitted as its own valid dR-tag row.

Boundary: this is a one-RAW discovery-path validation. It does not update the
existing activated default `quant_matrix.tsv`, does not run 85RAW, and does not
grant ProductWriter, Backfill, workbook, GUI, selected peak/area, or counted
detection authority.
