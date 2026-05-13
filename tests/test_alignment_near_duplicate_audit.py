from xic_extractor.alignment.near_duplicate_audit import (
    AlignmentNearDuplicateInput,
    count_near_duplicate_pairs,
)


def test_audit_counts_high_shared_unresolved_near_duplicate_pairs():
    rows = (
        AlignmentNearDuplicateInput(
            row_id="A",
            neutral_loss_tag="DNA_dR",
            mz=242.114,
            rt=12.5927,
            product_mz=126.066,
            observed_neutral_loss_da=116.048,
            present_samples=frozenset({"s1", "s2", "s3", "s4", "s5"}),
        ),
        AlignmentNearDuplicateInput(
            row_id="B",
            neutral_loss_tag="DNA_dR",
            mz=242.115,
            rt=12.5916,
            product_mz=126.066,
            observed_neutral_loss_da=116.048,
            present_samples=frozenset({"s1", "s2", "s3", "s4"}),
        ),
        AlignmentNearDuplicateInput(
            row_id="C",
            neutral_loss_tag="DNA_dR",
            mz=260.0,
            rt=9.0,
            product_mz=144.0,
            observed_neutral_loss_da=116.0,
            present_samples=frozenset({"s1", "s2", "s3", "s4"}),
        ),
    )

    summary = count_near_duplicate_pairs(
        rows,
        mz_ppm=5.0,
        rt_sec=2.0,
        product_ppm=10.0,
        observed_loss_ppm=10.0,
        min_shared_samples=3,
        min_overlap=0.8,
    )

    assert summary.near_pair_count == 1
    assert summary.high_shared_pair_count == 1
    assert summary.top_pairs[0].left_id == "A"
    assert summary.top_pairs[0].right_id == "B"
    assert summary.top_pairs[0].shared_count == 4
    assert summary.top_pairs[0].overlap_coefficient == 1.0
