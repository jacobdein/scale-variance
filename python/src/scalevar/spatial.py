"""Optional spatial helpers: :func:`create_hbins`, :func:`join_hbins`.

These require the ``[spatial]`` extra (``geopandas``, ``shapely``). They are
not imported eagerly by :mod:`scalevar` — call sites must import from this
submodule so the core stays installable without the geo stack.

Both helpers deliberately **refuse** geographic (unprojected) CRSes — see
``reference/polygon-R-implementation/crs-correction-note.txt`` for the
Web-Mercator incident that motivated this behavioral fix.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from scalevar._agg import resolve_agg_fun
from scalevar.errors import UnprojectedCRSError
from scalevar.raster import _UNPROJECTED_CRS_MESSAGE

if TYPE_CHECKING:
    import geopandas as gpd
    import pandas as pd


def _require_geopandas() -> Any:
    try:
        import geopandas as gpd

        return gpd
    except ImportError as exc:
        raise ImportError(
            "scalevar.spatial requires geopandas. Install with "
            "`pip install scalevar[spatial]`."
        ) from exc


def _assert_projected(aoi_like: Any) -> None:
    gpd = _require_geopandas()
    crs = None
    if hasattr(aoi_like, "crs") or isinstance(aoi_like, gpd.GeoSeries | gpd.GeoDataFrame):
        crs = aoi_like.crs
    if crs is None or getattr(crs, "is_geographic", False):
        raise UnprojectedCRSError(
            _UNPROJECTED_CRS_MESSAGE.format(crs=str(crs))
        )


def create_hbins(
    aoi: Any,
    base_cell_size: float,
    n_levels: int,
    base_level_factor: int = 2,
) -> gpd.GeoDataFrame:
    """Build a set of nested regular grids centered on ``aoi``.

    Level 1 is the finest scale. Each successive level multiplies the linear
    cell size by ``base_level_factor``. The grids align so every level-``n+1``
    cell exactly contains ``base_level_factor²`` level-``n`` cells.

    Parameters
    ----------
    aoi
        Area of interest as a ``geopandas.GeoDataFrame`` or
        ``geopandas.GeoSeries``. Must be in a projected CRS (linear units).
        A geographic CRS raises :class:`scalevar.errors.UnprojectedCRSError`.
    base_cell_size
        Side length of a level-1 cell in the CRS's linear units.
    n_levels
        Number of nested levels to generate. Must be ≥ 2.
    base_level_factor
        Linear scaling factor per level. Default 2.

    Returns
    -------
    geopandas.GeoDataFrame
        Columns ``id`` (unique integer across all levels), ``level`` (1..k),
        ``geometry`` (cell polygon).
    """
    gpd = _require_geopandas()
    from shapely.geometry import box as shp_box

    if n_levels < 2:
        raise ValueError("n_levels must be >= 2")
    if not isinstance(base_level_factor, int) or base_level_factor < 2:
        raise ValueError("base_level_factor must be an integer >= 2")
    if base_cell_size <= 0:
        raise ValueError("base_cell_size must be positive")

    _assert_projected(aoi)

    minx, miny, maxx, maxy = aoi.total_bounds
    dx, dy = maxx - minx, maxy - miny
    coarsest_cell = base_cell_size * (base_level_factor ** (n_levels - 1))
    # Align the grid so every level-k cell contains an integer number of
    # level-1 cells and so the grid is centered on the AOI.
    n_coarsest_x = max(1, int((dx + coarsest_cell - 1) // coarsest_cell))
    n_coarsest_y = max(1, int((dy + coarsest_cell - 1) // coarsest_cell))
    total_w = n_coarsest_x * coarsest_cell
    total_h = n_coarsest_y * coarsest_cell
    x0 = minx + dx / 2 - total_w / 2
    y0 = miny + dy / 2 - total_h / 2

    rows: list[dict[str, Any]] = []
    next_id = 0
    for lvl in range(1, n_levels + 1):
        cell = base_cell_size * (base_level_factor ** (lvl - 1))
        ncols = int(total_w / cell)
        nrows = int(total_h / cell)
        for j in range(nrows):
            for i in range(ncols):
                x_lo = x0 + i * cell
                y_lo = y0 + j * cell
                rows.append(
                    {
                        "id": next_id,
                        "level": lvl,
                        "geometry": shp_box(x_lo, y_lo, x_lo + cell, y_lo + cell),
                    }
                )
                next_id += 1
    return gpd.GeoDataFrame(rows, crs=aoi.crs)


def join_hbins(
    observations: gpd.GeoDataFrame,
    hbins: gpd.GeoDataFrame,
    value_col: str | None = None,
    agg_fun: str | Callable[[Any], float] = "mean",
) -> pd.DataFrame:
    """Assign each observation to its level-1 cell and join parent IDs at
    every higher level.

    Parameters
    ----------
    observations
        Point layer with a geometry column. CRS must match ``hbins``.
    hbins
        Output of :func:`create_hbins`.
    value_col
        Optional value column on ``observations`` to aggregate per cell.
    agg_fun
        Aggregation function if ``value_col`` is supplied. Default ``"mean"``.

    Returns
    -------
    pandas.DataFrame
        Columns ``id_level_1`` ... ``id_level_k`` and (if ``value_col``)
        the aggregated value column. Observations outside the hbin extent
        are dropped.
    """
    gpd = _require_geopandas()

    if observations.crs != hbins.crs:
        raise ValueError(
            f"observations CRS ({observations.crs}) != hbins CRS ({hbins.crs})"
        )
    _assert_projected(observations)

    levels = sorted(hbins["level"].unique())
    if levels[0] != 1:
        raise ValueError("hbins must include level 1")

    joined = observations.copy()
    for lvl in levels:
        sub = hbins.loc[hbins["level"] == lvl, ["id", "geometry"]]
        joined_lvl = gpd.sjoin(joined, sub, how="left", predicate="within")
        joined[f"id_level_{lvl}"] = joined_lvl["id"].to_numpy()
        if "index_right" in joined.columns:
            joined = joined.drop(columns=["index_right"])

    keep_cols = [f"id_level_{lvl}" for lvl in levels]
    if value_col is not None:
        if value_col not in observations.columns:
            raise ValueError(f"value_col {value_col!r} not on observations")
        keep_cols = [*keep_cols, value_col]

    tab = joined.loc[:, keep_cols].dropna(subset=[f"id_level_{levels[0]}"])
    for col in [c for c in keep_cols if c.startswith("id_level_")]:
        tab[col] = tab[col].astype(int)

    if value_col is None:
        return tab.reset_index(drop=True)

    agg_callable, _ = resolve_agg_fun(agg_fun)
    agg_map = tab.groupby(f"id_level_{levels[0]}", sort=False)[value_col].apply(
        lambda s: agg_callable(s.to_numpy(dtype=float))
    )
    # One row per finest-level cell — if value_col was supplied, drop to per-cell.
    per_cell = (
        tab.drop_duplicates(subset=[f"id_level_{levels[0]}"])
        .set_index(f"id_level_{levels[0]}")
        .drop(columns=[value_col])
    )
    per_cell[value_col] = agg_map
    return per_cell.reset_index()
