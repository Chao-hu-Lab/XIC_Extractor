# Discovery precursor inference validation v1

Doc placement: repo_support_doc
Doc kind: validation_artifact
Doc lifecycle: archived
Repo owner: docs/product/discovery.md
Doc exit rule: Keep until Discovery product docs or newer validation artifacts cover the same precursor-inference root cause and replay evidence.

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
.venv\Scripts\python.exe scripts\run_discovery.py --raw <raw-data>/TumorBC2312_DNA.raw --dll-dir $env:THERMO_RAWFILE_READER_DLL_DIR --output-dir docs/superpowers\validation\discovery_precursor_inference_v1\TumorBC2312_DNA --neutral-loss-tag DNA_dR --neutral-loss-da 116.0474 --rt-min 22 --rt-max 25 --ms2-precursor-tol-da 1.6 --resolver-mode local_minimum
```

Observed result in `TumorBC2312_DNA/discovery_candidates.csv`:

- `duplicate_candidate_ids=0`.
- Candidate ids include row identity suffixes; stale `sample#scan` ids should
  be regenerated before alignment replay.
- `300.161 / 184.113` rows are emitted with
  `precursor_mz_basis=product_plus_neutral_loss` and
  `neutral_loss_error_basis=configured_loss_inferred_precursor`.
- `301.165 / 185.116` remains emitted as its own valid dR-tag row.
- Full candidate rows include `neutral_loss_error_basis`,
  `precursor_mz_basis`, `scan_precursor_mz`, `scan_precursor_delta_da`, and
  `max_scan_precursor_abs_delta_da`.
- The checker validates row-id suffix coherence against `sample_stem`,
  `best_ms2_scan_id`, `precursor_mz`, and `product_mz`, rejects duplicate
  candidate ids, and rejects invalid basis enums.

Checker command:

```powershell
uv run python scripts/check_discovery_precursor_inference_artifact.py --check-only --summary-json docs/superpowers\validation\discovery_precursor_inference_v1\discovery_precursor_inference_check_summary.json
```

Checker result:

- `status=pass`.
- `expected_row_count=157`.
- `discovery_candidates.csv` SHA-256:
  `D08CD512410DA303A961CD4CA6D39938FBAAEB32AE0F3FDCEC038E3561455405`.
- Retained CSV headers were normalized to the current Discovery schema after
  family-abstraction removal; this refresh did not rerun RAW or change row
  count.

Boundary: this is a one-RAW discovery-path validation. It does not update the
existing activated default `quant_matrix.tsv`, does not run 85RAW, and does not
grant ProductWriter, Backfill, workbook, GUI, selected peak/area, or counted
detection authority.
