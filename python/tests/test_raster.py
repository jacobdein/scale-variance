"""Unit tests for the raster entry point.

The gold-standard check is ``fixture_mt1972_fig3`` — the 16×16 checkerboard
from Moellering & Tobler (1972) Figure 3 with published totals
``TSS=1152, TDF=255``.
"""

from __future__ import annotations

import warnings

import numpy as np
import pytest

from scalevar import ScaleVarianceResult, scale_variance_raster
from scalevar.errors import UnprojectedCRSError


def _load_raster_as_numpy(path) -> np.ndarray:
    import rasterio

    with rasterio.open(path) as src:
        return src.read(1).astype(np.float64)


def test_mt1972_fig3_matches_paper(mt1972_fig3):
    bundle = mt1972_fig3
    arr = _load_raster_as_numpy(bundle["input_path"])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # no-CRS warning is expected
        result = scale_variance_raster(
            arr,
            num_levels=bundle["meta"]["num_levels"],
            base_level_factor=bundle["meta"]["base_level_factor"],
            agg_fun=bundle["meta"]["agg_fun"],
        )

    totals = bundle["expected_totals"]
    assert result.total_ss == pytest.approx(totals["total_ss"], abs=1e-9)
    assert result.total_df == totals["total_df"]
    assert result.grand_mean == pytest.approx(totals["grand_mean"], abs=1e-12)

    expected = bundle["expected_components"]
    actual = result.components
    assert actual["level"].tolist() == expected["level"].tolist()
    np.testing.assert_allclose(
        actual["scale"].to_numpy(),
        expected["scale"].to_numpy(),
        atol=1e-10,
    )
    assert actual["df"].tolist() == expected["df"].tolist()
    for col in ["sum_squares", "mean_square", "ss_share", "ms_share", "ss_cumulative"]:
        np.testing.assert_allclose(
            actual[col].to_numpy(dtype=float),
            expected[col].to_numpy(dtype=float),
            atol=1e-10,
            rtol=1e-9,
            equal_nan=True,
        )


def test_mt1972_fig3_identities(mt1972_fig3):
    bundle = mt1972_fig3
    arr = _load_raster_as_numpy(bundle["input_path"])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = scale_variance_raster(arr)
    # Identity: Σ SS_n = TSS, Σ df_n = total_df, Σ ss_share = 1.
    assert result.components["sum_squares"].sum() == pytest.approx(result.total_ss, abs=1e-9)
    assert result.components["df"].sum() == result.total_df
    assert result.components["ss_share"].sum() == pytest.approx(1.0, abs=1e-10)


def test_mt1972_fig3_level_rasters_present(mt1972_fig3):
    bundle = mt1972_fig3
    arr = _load_raster_as_numpy(bundle["input_path"])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = scale_variance_raster(arr)
    assert result.level_rasters is not None
    assert set(result.level_rasters) == {f"level_{i}" for i in range(1, 6)}


def test_mt1972_fig3_return_sve(mt1972_fig3):
    bundle = mt1972_fig3
    arr = _load_raster_as_numpy(bundle["input_path"])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = scale_variance_raster(arr, return_sve=True)
    assert result.sve is not None
    assert result.sve.shape == (5, 16, 16)
    # Per-level SS reconstructs from SVE.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        per_level_ss = np.nansum(result.sve.reshape(5, -1), axis=1)
    np.testing.assert_allclose(
        per_level_ss,
        result.components["sum_squares"].to_numpy(),
        atol=1e-9,
    )


def test_raster_roundtrip_to_tabular(mt1972_fig3):
    """The raster path and an explicit tabular re-representation must agree."""
    from scalevar import scale_variance

    bundle = mt1972_fig3
    arr = _load_raster_as_numpy(bundle["input_path"])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ras = scale_variance_raster(arr)
    # Rebuild tabular and pass through scale_variance with the same id_cols.
    tab = ras.wide_table.reset_index(drop=True)
    id_cols = [c for c in tab.columns if c.startswith("id_level_")]
    tab2 = scale_variance(tab, value="_value", id_cols=id_cols)
    np.testing.assert_allclose(
        tab2.components["sum_squares"].to_numpy(),
        ras.components["sum_squares"].to_numpy(),
        atol=1e-10,
    )
    assert tab2.components["df"].tolist() == ras.components["df"].tolist()


def test_unprojected_crs_rejected():
    import numpy as np

    xr = pytest.importorskip("xarray")
    pytest.importorskip("rioxarray")  # activates the .rio accessor
    da = xr.DataArray(
        np.ones((16, 16), dtype=np.float64),
        dims=("y", "x"),
    ).rio.write_crs("EPSG:4326")
    with pytest.raises(UnprojectedCRSError, match="unprojected or geographic CRS"):
        scale_variance_raster(da)


def test_numpy_with_no_crs_warns_once(mt1972_fig3):
    bundle = mt1972_fig3
    arr = _load_raster_as_numpy(bundle["input_path"])
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        scale_variance_raster(arr)
    msgs = [str(w.message) for w in captured]
    assert any("no CRS" in m for m in msgs)


def test_returns_structured_result(mt1972_fig3):
    bundle = mt1972_fig3
    arr = _load_raster_as_numpy(bundle["input_path"])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = scale_variance_raster(arr)
    assert isinstance(result, ScaleVarianceResult)
    assert result.agg_fun == "mean"
    assert result.n_levels == 5
