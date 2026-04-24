"""Smoke tests for the optional spatial module.

Full parity against R will come via ``fixture_crs_unprojected_aoi``. This
module only verifies the Python helpers wire up and refuse geographic CRSes.
"""

from __future__ import annotations

import pytest


def _geopandas_or_skip():
    return pytest.importorskip("geopandas")


def test_import():
    # Smoke: the module imports at all.
    from scalevar import spatial

    assert hasattr(spatial, "create_hbins")
    assert hasattr(spatial, "join_hbins")


def test_create_hbins_rejects_geographic_crs():
    gpd = _geopandas_or_skip()
    from shapely.geometry import box

    from scalevar.errors import UnprojectedCRSError
    from scalevar.spatial import create_hbins

    aoi = gpd.GeoDataFrame(geometry=[box(0, 0, 1, 1)], crs="EPSG:4326")
    with pytest.raises(UnprojectedCRSError, match="unprojected or geographic CRS"):
        create_hbins(aoi, base_cell_size=0.1, n_levels=2)


def test_create_hbins_projected_aoi_returns_gdf():
    gpd = _geopandas_or_skip()
    from shapely.geometry import box

    from scalevar.spatial import create_hbins

    # British National Grid, meters — a small 100m × 100m AOI.
    aoi = gpd.GeoDataFrame(
        geometry=[box(530000, 180000, 530100, 180100)], crs="EPSG:27700"
    )
    hbins = create_hbins(aoi, base_cell_size=25.0, n_levels=3, base_level_factor=2)
    assert {"id", "level", "geometry"}.issubset(hbins.columns)
    assert sorted(hbins["level"].unique()) == [1, 2, 3]
    # Unique ids across all rows.
    assert hbins["id"].is_unique
    # Each level's cells tile the coarsest-level extent: level-1 cell count should
    # equal 4 × level-2 count, etc. (with `factor = 2`).
    counts = hbins["level"].value_counts()
    assert counts[1] == counts[2] * 4
    assert counts[2] == counts[3] * 4


def test_join_hbins_roundtrip():
    gpd = _geopandas_or_skip()
    from shapely.geometry import Point, box

    from scalevar.spatial import create_hbins, join_hbins

    aoi = gpd.GeoDataFrame(
        geometry=[box(0, 0, 100, 100)], crs="EPSG:27700"
    )
    hbins = create_hbins(aoi, base_cell_size=25.0, n_levels=2, base_level_factor=2)
    pts = gpd.GeoDataFrame(
        {"v": [1.0, 2.0, 3.0, 4.0]},
        geometry=[Point(10, 10), Point(40, 40), Point(60, 60), Point(85, 85)],
        crs="EPSG:27700",
    )
    joined = join_hbins(pts, hbins, value_col="v")
    assert {"id_level_1", "id_level_2", "v"}.issubset(joined.columns)
    # 4 distinct finest-cell ids for 4 points in 4 different level-1 cells.
    assert joined["id_level_1"].nunique() == 4
