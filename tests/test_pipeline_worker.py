from gui.workers.pipeline_worker import PipelineWorker


def _worker():
    return PipelineWorker.__new__(PipelineWorker)


def test_parse_nl_confirmed():
    stdout = (
        "Saved : C:\\output\\xic_results.xlsx\n"
        "  258.1085_RT detected (NL confirmed): 18/24\n"
        "  242.1136_RT detected (NL confirmed): 22/24\n"
        "  258.1085_NL116  OK:15  WARN:3  ND:6\n"
        "  242.1136_NL116  OK:20  WARN:2  ND:2\n"
    )
    result = _worker()._parse_summary(stdout, 24)
    assert result["total_files"] == 24 and result["nl_warn_count"] == 5
    targets = {item["label"]: item for item in result["targets"]}
    assert targets["258.1085"]["detected"] == 18
    assert targets["258.1085"]["nl_confirmed"] is True


def test_parse_no_nl():
    result = _worker()._parse_summary("Saved : C:\\o.xlsx\n  258.1085_RT detected: 3/5\n", 5)
    assert result["nl_warn_count"] == 0
    assert not {item["label"]: item for item in result["targets"]}["258.1085"]["nl_confirmed"]


def test_parse_empty():
    result = _worker()._parse_summary("", 0)
    assert result["targets"] == [] and result["excel_path"] == ""


def test_parse_istd_nd_warning():
    stdout = (
        "Saved : C:\\output\\xic_results.xlsx\n"
        "  d3-5-hmdC_RT detected (NL confirmed): 18/20\n"
        "  d3-5-hmdC_NL116  OK:15  WARN:3  ND:5\n"
        "ISTD_ND: d3-5-hmdC 18/20\n"
    )
    result = _worker()._parse_summary(stdout, 20)
    assert result["istd_warnings"] == [
        {"label": "d3-5-hmdC", "detected": 18, "total": 20}
    ]


def test_parse_no_istd_warnings():
    stdout = "Saved : C:\\o.xlsx\n  5-hmdC_RT detected (NL confirmed): 20/20\n"
    result = _worker()._parse_summary(stdout, 20)
    assert result["istd_warnings"] == []
