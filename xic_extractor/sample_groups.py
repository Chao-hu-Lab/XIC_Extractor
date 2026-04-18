import re

_QC_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9])QC(?:[\s_-]*\d+)?(?![A-Za-z0-9])",
    re.IGNORECASE,
)


def classify_sample_group(sample_name: str) -> str:
    if _QC_TOKEN_RE.search(sample_name):
        return "QC"

    normalized = sample_name.upper()
    if normalized.startswith("TUMOR"):
        return "Tumor"
    if normalized.startswith("NORMAL"):
        return "Normal"
    if normalized.startswith("BENIGNFAT"):
        return "Benignfat"
    return "Other"
