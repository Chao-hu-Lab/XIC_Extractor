from pathlib import Path

from tools.diagnostics import instrument_qc_sequence_manifest
from xic_extractor.instrument_qc.classification import InstrumentQCClass
from xic_extractor.instrument_qc.sequence_manifest import (
    ManifestMatchConfidence,
    ManifestMatchStatus,
    SequenceManifestRow,
)


def test_sequence_manifest_cli_writes_outputs(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    method_doc = tmp_path / "method.docx"
    method_doc.write_bytes(b"fake")
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    output_dir = tmp_path / "out"

    def fake_build_sequence_manifest(**kwargs):
        assert kwargs["method_doc"] == method_doc
        assert kwargs["raw_dir"] == raw_dir
        return (
            SequenceManifestRow(
                source_doc=str(method_doc),
                source_section="table:1:row:2",
                doc_display_name="SDOLEK-pretest",
                raw_stem="SDOLEK-pretest",
                injection_order=4,
                instrument_qc_class=InstrumentQCClass.SDOLEK,
                match_status=ManifestMatchStatus.MATCHED,
                match_confidence=ManifestMatchConfidence.HIGH,
                match_reason="matched",
            ),
        )

    monkeypatch.setattr(
        instrument_qc_sequence_manifest,
        "build_sequence_manifest",
        fake_build_sequence_manifest,
    )

    rc = instrument_qc_sequence_manifest.main(
        [
            "--method-doc",
            str(method_doc),
            "--raw-dir",
            str(raw_dir),
            "--output-dir",
            str(output_dir),
        ]
    )

    assert rc == 0
    assert (output_dir / "instrument_qc_sequence_manifest.tsv").exists()
    assert (output_dir / "instrument_qc_injection_order.csv").exists()
    assert (output_dir / "instrument_qc_sequence_manifest.json").exists()
    assert (output_dir / "instrument_qc_sequence_manifest.md").exists()
    assert "instrument_qc_sequence_manifest.tsv" in capsys.readouterr().out


def test_sequence_manifest_cli_rejects_missing_method_doc(
    tmp_path: Path,
    capsys,
) -> None:
    rc = instrument_qc_sequence_manifest.main(
        [
            "--method-doc",
            str(tmp_path / "missing.docx"),
            "--raw-dir",
            str(tmp_path),
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )

    assert rc == 2
    assert "method doc not found" in capsys.readouterr().err


def test_sequence_manifest_cli_rejects_sampleinfo_as_input(
    tmp_path: Path,
    capsys,
) -> None:
    sample_info = tmp_path / "SampleInfo.xlsx"
    sample_info.write_bytes(b"not a method doc")

    rc = instrument_qc_sequence_manifest.main(
        [
            "--method-doc",
            str(sample_info),
            "--raw-dir",
            str(tmp_path),
            "--output-dir",
            str(tmp_path / "out"),
        ]
    )

    assert rc == 2
    assert "SampleInfo" in capsys.readouterr().err
