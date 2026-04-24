"""Unit tests for the tabular core."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scalevar import (
    DuplicateIdColsError,
    InsufficientLevelsError,
    MissingColumnError,
    NonNumericValueError,
    ScaleVarianceResult,
    scale_variance,
)


def test_irregular_admin_matches_hand_derivation(irregular_admin):
    bundle = irregular_admin
    result = scale_variance(
        bundle["input"],
        value=bundle["meta"]["value"],
        id_cols=bundle["meta"]["id_cols"],
        agg_fun=bundle["meta"]["agg_fun"],
    )
    totals = bundle["expected_totals"]
    assert result.total_ss == pytest.approx(totals["total_ss"], abs=1e-9)
    assert result.total_df == totals["total_df"]
    assert result.grand_mean == pytest.approx(totals["grand_mean"], abs=1e-12)

    expected = bundle["expected_components"]
    actual = result.components
    # Integer columns match exactly, float columns within tolerance.
    assert actual["level"].tolist() == expected["level"].tolist()
    assert actual["df"].tolist() == expected["df"].tolist()
    for col in ["sum_squares", "mean_square", "ss_share", "ms_share", "ss_cumulative"]:
        np.testing.assert_allclose(
            actual[col].to_numpy(dtype=float),
            expected[col].to_numpy(dtype=float),
            atol=1e-10,
            rtol=1e-9,
            equal_nan=True,
        )


def test_irregular_admin_identities(irregular_admin):
    bundle = irregular_admin
    result = scale_variance(
        bundle["input"],
        value=bundle["meta"]["value"],
        id_cols=bundle["meta"]["id_cols"],
    )
    assert result.components["sum_squares"].sum() == pytest.approx(result.total_ss, abs=1e-9)
    assert result.components["df"].sum() == result.total_df
    assert result.components["ss_share"].sum() == pytest.approx(1.0, abs=1e-10)


def test_irregular_admin_elements_shapes(irregular_admin):
    bundle = irregular_admin
    result = scale_variance(
        bundle["input"],
        value=bundle["meta"]["value"],
        id_cols=bundle["meta"]["id_cols"],
    )
    assert set(result.elements) == {1, 2, 3}
    # Level 1: one row per county (24). Level 2: one row per state (6).
    # Level 3: one row per region (2).
    assert len(result.elements[1]) == 24
    assert len(result.elements[2]) == 6
    assert len(result.elements[3]) == 2
    for df in result.elements.values():
        assert list(df.columns) == ["id", "mean_child", "mean_parent", "sv", "sv_per_df"]


def test_scale_variance_returns_structured_result(irregular_admin):
    bundle = irregular_admin
    result = scale_variance(
        bundle["input"],
        value=bundle["meta"]["value"],
        id_cols=bundle["meta"]["id_cols"],
    )
    assert isinstance(result, ScaleVarianceResult)
    assert result.n_levels == 3
    assert result.agg_fun == "mean"
    assert result.na_handling == "drop_na"
    assert result.level_rasters is None
    assert result.sve is None


def test_dropna_excludes_rows(irregular_admin):
    bundle = irregular_admin.copy()
    df = bundle["input"].copy()
    # Null the first county's value — it should drop from the universe.
    df.loc[df.index[0], "value"] = np.nan
    result = scale_variance(df, value="value", id_cols=["county_id", "state_id", "region_id"])
    # N-1 non-NA rows = 23.
    assert result.total_df == 22
    # TSS should differ from the hand-derived full fixture since one row is gone.
    assert result.total_ss != bundle["expected_totals"]["total_ss"]


def test_all_equal_values_give_zero_variance():
    # Degenerate case: every value identical. All SS must be 0.
    df = pd.DataFrame(
        {
            "id_level_1": list(range(12)),
            "id_level_2": [0, 0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 3],
            "id_level_3": [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1],
            "value": [42.0] * 12,
        }
    )
    result = scale_variance(df, value="value", id_cols=["id_level_1", "id_level_2", "id_level_3"])
    assert result.total_ss == 0.0
    assert all(result.components["sum_squares"] == 0.0)
    assert result.grand_mean == pytest.approx(42.0)


def test_perfect_single_level_separation():
    # Values depend only on the coarsest level — that level should absorb 100% of ss_share.
    df = pd.DataFrame(
        {
            "id_level_1": list(range(8)),
            "id_level_2": [0, 0, 1, 1, 2, 2, 3, 3],
            "id_level_3": [0, 0, 0, 0, 1, 1, 1, 1],
            "value": [10.0, 10.0, 10.0, 10.0, 20.0, 20.0, 20.0, 20.0],
        }
    )
    result = scale_variance(df, value="value", id_cols=["id_level_1", "id_level_2", "id_level_3"])
    # All variance lives at the coarsest level (region).
    assert result.components.loc[2, "ss_share"] == pytest.approx(1.0, abs=1e-12)
    assert result.components.loc[0, "ss_share"] == pytest.approx(0.0, abs=1e-12)
    assert result.components.loc[1, "ss_share"] == pytest.approx(0.0, abs=1e-12)


def test_error_on_single_level():
    df = pd.DataFrame({"id": [1, 2, 3], "value": [1.0, 2.0, 3.0]})
    with pytest.raises(InsufficientLevelsError, match="at least two levels"):
        scale_variance(df, value="value", id_cols=["id"])


def test_error_on_missing_column():
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4], "value": [5.0, 6.0]})
    with pytest.raises(MissingColumnError):
        scale_variance(df, value="value", id_cols=["a", "missing"])
    with pytest.raises(MissingColumnError):
        scale_variance(df, value="nope", id_cols=["a", "b"])


def test_error_on_nonnumeric_value():
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4], "value": ["x", "y"]})
    with pytest.raises(NonNumericValueError):
        scale_variance(df, value="value", id_cols=["a", "b"])


def test_error_on_duplicate_id_cols():
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4], "value": [1.0, 2.0]})
    with pytest.raises(DuplicateIdColsError):
        scale_variance(df, value="value", id_cols=["a", "a"])


def test_error_on_unsupported_na_handling(irregular_admin):
    bundle = irregular_admin
    with pytest.raises(ValueError, match="drop_na"):
        scale_variance(
            bundle["input"],
            value="value",
            id_cols=["county_id", "state_id", "region_id"],
            na_handling="require_complete",
        )


def test_custom_agg_callable(irregular_admin):
    # A callable agg_fun should be accepted and the callable used verbatim.
    # For MEAN, custom and string forms must produce identical results.
    bundle = irregular_admin
    ref = scale_variance(
        bundle["input"],
        value="value",
        id_cols=["county_id", "state_id", "region_id"],
        agg_fun="mean",
    )

    def my_mean(arr: np.ndarray) -> float:
        return float(np.nanmean(arr))

    alt = scale_variance(
        bundle["input"],
        value="value",
        id_cols=["county_id", "state_id", "region_id"],
        agg_fun=my_mean,
    )
    np.testing.assert_allclose(
        alt.components["sum_squares"].to_numpy(),
        ref.components["sum_squares"].to_numpy(),
        atol=1e-10,
    )
    assert alt.agg_fun == "my_mean"
