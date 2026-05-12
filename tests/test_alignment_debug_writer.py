from pathlib import Path

from xic_extractor.alignment.debug_writer import (
    write_ambiguous_ms1_owners_tsv,
    write_event_to_ms1_owner_tsv,
)
from xic_extractor.alignment.ownership_models import (
    AmbiguousOwnerRecord,
    OwnerAssignment,
)


def test_event_to_owner_debug_tsv(tmp_path: Path):
    path = write_event_to_ms1_owner_tsv(
        tmp_path / "event_to_ms1_owner.tsv",
        (
            OwnerAssignment(
                "s1#6095",
                "OWN-s1-000001",
                "primary",
                "primary_identity_event",
            ),
            OwnerAssignment(
                "s1#6096",
                "OWN-s1-000001",
                "supporting",
                "owner_exact_apex_match",
            ),
        ),
    )

    assert path.read_text(encoding="utf-8").splitlines() == [
        "candidate_id\towner_id\tassignment_status\treason",
        "s1#6095\tOWN-s1-000001\tprimary\tprimary_identity_event",
        "s1#6096\tOWN-s1-000001\tsupporting\towner_exact_apex_match",
    ]


def test_ambiguous_owner_debug_tsv(tmp_path: Path):
    path = write_ambiguous_ms1_owners_tsv(
        tmp_path / "ambiguous_ms1_owners.tsv",
        (
            AmbiguousOwnerRecord(
                "AMB-s1-000001",
                "s1",
                ("s1#8001", "s1#8002"),
                "owner_multiplet_ambiguity",
            ),
        ),
    )

    assert path.read_text(encoding="utf-8").splitlines() == [
        "ambiguity_id\tsample_stem\tcandidate_ids\treason",
        "AMB-s1-000001\ts1\ts1#8001;s1#8002\towner_multiplet_ambiguity",
    ]
