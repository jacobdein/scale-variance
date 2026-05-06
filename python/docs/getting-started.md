# Getting started

!!! tip "Try it before you install"
    The **[interactive playground](playground.md)** runs `scalevar` in your browser via Pyodide — no install needed to see what the decomposition does on the canonical Moellering & Tobler (1972) Figure 3 fixture.

## Install

`scalevar` is not on PyPI yet (scheduled for v0.3 — see the [roadmap](https://github.com/jacobdein/scale-variance/blob/main/ROADMAP.md)). For v0.1, install from GitHub:

```bash
# core only
pip install "scalevar @ git+https://github.com/jacobdein/scale-variance.git#subdirectory=python"

# with the raster extras (xarray + rioxarray + rasterio)
pip install "scalevar[raster] @ git+https://github.com/jacobdein/scale-variance.git#subdirectory=python"

# with the spatial extras (geopandas + shapely)
pip install "scalevar[spatial] @ git+https://github.com/jacobdein/scale-variance.git#subdirectory=python"

# everything
pip install "scalevar[raster,spatial] @ git+https://github.com/jacobdein/scale-variance.git#subdirectory=python"
```

## Which entry point do I use?

### I have a raster → [`scale_variance_raster`](api.md#scalevar.scale_variance_raster)

```python
import rioxarray as rxr
from scalevar import scale_variance_raster

ndvi = rxr.open_rasterio("ndvi.tif").squeeze()          # xarray.DataArray
# ndvi = rasterio.open("ndvi.tif").read(1)              # or numpy.ndarray

result = scale_variance_raster(
    ndvi,
    num_levels=None,          # auto: floor(log_b(min(nrow, ncol))) + 1
    base_level_factor=2,      # 4:1 aggregation per level
    agg_fun="mean",           # or "sum", "median", "modal", "min", "max", "sd", "var", or a callable
)

result.components        # per-level SS / df / mean_square / ss_share / ss_cumulative
result.total_ss
result.grand_mean
result.level_rasters     # dict of the aggregated rasters
```

A geographic CRS (like EPSG:4326) is rejected with an `UnprojectedCRSError` — scale variance measures variance across *cell sizes*, which needs a projected CRS with linear units. A raster with no CRS at all is accepted with a warning; scales report in raw pixel units.

Pass `return_sve=True` to also get a `(num_levels, nrow, ncol)` array of squared differences per level, mapped back to the finest grid — useful for visualizing *where* variance accumulates at each scale. The [raster example notebook](examples/02_raster_mt1972_fig3.ipynb) walks through the paper-canonical decomposition end-to-end.

### I have tabular data → [`scale_variance`](api.md#scalevar.scale_variance)

```python
import pandas as pd
from scalevar import scale_variance

df = pd.DataFrame({
    "county_id":  [1, 2, 3, 4, 5, 6, 7, 8],
    "state_id":   [1, 1, 2, 2, 3, 3, 4, 4],
    "region_id":  [1, 1, 1, 1, 2, 2, 2, 2],
    "value":      [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0],
})

result = scale_variance(
    df,
    value="value",
    id_cols=["county_id", "state_id", "region_id"],   # finest → coarsest
    agg_fun="mean",
)
```

`id_cols` is ordered finest-to-coarsest. Every row of the dataframe is one finest-level observation. Missing values in `value` are dropped before anything else.

### I have points and want a grid → `scalevar.spatial`

```python
import geopandas as gpd
from scalevar.spatial import create_hbins, join_hbins
from scalevar import scale_variance

aoi = gpd.read_file("aoi.geojson").to_crs("EPSG:27700")          # British National Grid

hbins = create_hbins(aoi, base_cell_size=100.0, n_levels=4)      # 100m / 200m / 400m / 800m
per_cell = join_hbins(observations, hbins, value_col="v", agg_fun="mean")

result = scale_variance(
    per_cell,
    value="v",
    id_cols=[f"id_level_{i}" for i in range(1, 5)],
)
```

See the [polygon example notebook](examples/03_polygon_hierarchy.ipynb) for the full walkthrough.

## The result object

Every entry point returns a [`ScaleVarianceResult`](api.md#scalevar.ScaleVarianceResult):

| Field | Description |
|---|---|
| `components` | One row per user-supplied level. Columns: `level`, `scale`, `sum_squares`, `df`, `mean_square`, `ss_share`, `ms_share`, `ss_cumulative`. |
| `total_ss` | Total sum of squares around the grand mean. |
| `total_df` | `N − 1` where `N` is the count of non-NA finest-level cells. |
| `grand_mean` | Mean of the value column after NA drop. |
| `n_levels` | Number of user-supplied levels, `k`. |
| `agg_fun` | Echo of the aggregation function name. |
| `na_handling` | Echo of the na_handling argument. |
| `elements` | Dict `{level: DataFrame}`. One row per distinct level-`n` cell; columns `id`, `mean_child`, `mean_parent`, `sv`, `sv_per_df`. Summing `sv` per level recovers `SS_level_n`. |
| `wide_table` | The working table used internally — one row per finest-level observation (after NA drop), with `value_level_1` ... `value_level_(k+1)` columns. |
| `level_rasters` | *(raster only)* dict of the per-level aggregated rasters. |
| `sve` | *(raster only, optional)* `(num_levels, nrow, ncol)` numpy array of squared differences, if `return_sve=True`. |

The paper-canonical "variance share" is `components.ss_share`, which sums to 1 by the Moellering-Tobler Eq. 12 identity. `components.ms_share` is an alternative normalization (`MS / Σ MS`) reported for users who want a df-weighted share — **not** the paper-canonical quantity.

## Sanity checks

Every result carries the identities from the theory:

```python
assert abs(result.components["sum_squares"].sum() - result.total_ss) < 1e-9
assert result.components["df"].sum() == result.total_df
assert abs(result.components["ss_share"].sum() - 1.0) < 1e-10
```

These are enforced inside the compute function — a violation raises rather than silently warns. If you ever see a `RuntimeError: scalevar internal error: Σ SS_n ≠ TSS ...`, please [file a bug](https://github.com/jacobdein/scale-variance/issues).

## Next

- [Tabular admin example notebook](examples/01_tabular_admin.ipynb)
- [Moellering & Tobler (1972) Figure 3 example notebook](examples/02_raster_mt1972_fig3.ipynb)
- [Polygon-hierarchy example notebook](examples/03_polygon_hierarchy.ipynb)
- [Full API reference](api.md)
- [Theory](theory.md)
