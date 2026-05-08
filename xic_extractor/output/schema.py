from dataclasses import dataclass


@dataclass(frozen=True)
class OutputColumn:
    name: str
    advanced: bool = False
    description: str = ""


MS1_SUFFIXES: tuple[str, ...] = (
    "RT",
    "Int",
    "Area",
    "PeakStart",
    "PeakEnd",
    "PeakWidth",
)

LONG_COLUMNS: tuple[OutputColumn, ...] = (
    OutputColumn("SampleName"),
    OutputColumn("Group"),
    OutputColumn("Target"),
    OutputColumn("Role"),
    OutputColumn("ISTD Pair"),
    OutputColumn("RT", description="smoothed peak apex RT (min)"),
    OutputColumn("Area", description="raw integrated area"),
    OutputColumn("NL"),
    OutputColumn("Int", advanced=True, description="raw apex intensity"),
    OutputColumn("PeakStart", advanced=True),
    OutputColumn("PeakEnd", advanced=True),
    OutputColumn("PeakWidth", advanced=True),
    OutputColumn("Confidence"),
    OutputColumn("Reason"),
)
LONG_HEADERS: tuple[str, ...] = tuple(column.name for column in LONG_COLUMNS)
LONG_ADVANCED_HEADERS: frozenset[str] = frozenset(
    column.name for column in LONG_COLUMNS if column.advanced
)

DIAGNOSTIC_HEADERS: tuple[str, ...] = (
    "SampleName",
    "Target",
    "Issue",
    "Reason",
)

SCORE_BREAKDOWN_HEADERS: tuple[str, ...] = (
    "SampleName",
    "Target",
    "Final Confidence",
    "Detection Counted",
    "Caps",
    "Raw Score",
    "Support",
    "Concerns",
    "Base Score",
    "Positive Points",
    "Negative Points",
    "symmetry",
    "local_sn",
    "nl_support",
    "rt_prior",
    "rt_centrality",
    "noise_shape",
    "peak_width",
    "Quality Penalty",
    "Quality Flags",
    "Total Severity",
    "Confidence",
    "Prior RT",
    "Prior Source",
)
