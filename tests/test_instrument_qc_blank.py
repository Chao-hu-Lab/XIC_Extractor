from xic_extractor.instrument_qc.blank import probe_blank_tic_bpc_capability


class _UnsupportedRaw:
    def extract_xic(self) -> None:
        raise NotImplementedError


class _SupportedRaw:
    def extract_tic(self) -> None:
        raise NotImplementedError

    def extract_bpc(self) -> None:
        raise NotImplementedError


def test_blank_tic_bpc_probe_reports_current_raw_reader_unsupported() -> None:
    result = probe_blank_tic_bpc_capability(_UnsupportedRaw())

    assert result.status == "unsupported"
    assert result.tic_supported is False
    assert result.bpc_supported is False
    assert "TIC/BPC" in result.reason


def test_blank_tic_bpc_probe_detects_supported_source() -> None:
    result = probe_blank_tic_bpc_capability(_SupportedRaw())

    assert result.status == "supported"
    assert result.tic_supported is True
    assert result.bpc_supported is True
