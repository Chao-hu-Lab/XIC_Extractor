from pathlib import Path

from xic_extractor.discovery.models import (
    DISCOVERY_BRIEF_COLUMNS,
    DiscoveryBatchOutputs,
    DiscoveryRunOutputs,
)


EXPECTED_BRIEF_COLUMNS = (
    "review_priority",
    "evidence_tier",
    "evidence_score",
    "ms2_support",
    "ms1_support",
    "rt_alignment",
    "family_context",
    "candidate_id",
    "precursor_mz",
    "best_seed_rt",
    "ms1_area",
    "seed_event_count",
    "neutral_loss_tag",
    "review_note",
)


def test_discovery_brief_columns_are_stable_csv_contract() -> None:
    assert DISCOVERY_BRIEF_COLUMNS == EXPECTED_BRIEF_COLUMNS
    assert len(DISCOVERY_BRIEF_COLUMNS) == 14


def test_discovery_run_outputs_carries_two_csv_paths() -> None:
    outputs = DiscoveryRunOutputs(
        candidates_csv=Path("a.csv"),
        review_csv=Path("b.csv"),
    )
    assert outputs.candidates_csv == Path("a.csv")
    assert outputs.review_csv == Path("b.csv")


def test_discovery_batch_outputs_carries_index_and_per_sample() -> None:
    per_sample = (
        DiscoveryRunOutputs(
            candidates_csv=Path("s1/c.csv"),
            review_csv=Path("s1/r.csv"),
        ),
    )
    batch = DiscoveryBatchOutputs(
        batch_index_csv=Path("idx.csv"),
        per_sample=per_sample,
    )
    assert batch.batch_index_csv == Path("idx.csv")
    assert batch.per_sample == per_sample
