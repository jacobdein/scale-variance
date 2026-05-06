# scalevar (Python)

**Scale variance decomposition for rasters and nested hierarchies.**

A direct Python implementation of the method introduced by Moellering and Tobler (1972), *Geographical Variances*.

> **Try it in your browser**: the [interactive playground](https://jacobdein.github.io/scale-variance/playground/) runs `scalevar` end-to-end via Pyodide — no install needed to see the decomposition on the paper's canonical 16×16 fixture.

## Install

`scalevar` is not yet on PyPI. For v0.1, install from GitHub:

```bash
# core only
pip install "scalevar @ git+https://github.com/jacobdein/scale-variance.git#subdirectory=python"

# with raster + spatial extras
pip install "scalevar[raster,spatial] @ git+https://github.com/jacobdein/scale-variance.git#subdirectory=python"
```

Python ≥ 3.10. Hard dependencies: `numpy`, `pandas`. Optional extras:

- `[raster]` — `xarray`, `rioxarray`, `rasterio` (for CRS-aware raster input)
- `[spatial]` — `geopandas`, `shapely` (for `create_hbins` / `join_hbins`)
- `[dev]` — `pytest`, `ruff`, `mypy`
- `[docs]` — `mkdocs-material`, `mkdocs-jupyter`, `mkdocstrings[python]`, `matplotlib`, `jupyter` (to rebuild the docs site and notebooks)

## Quick start

### Raster

```python
import rioxarray
from scalevar import scale_variance_raster

r = rioxarray.open_rasterio("ndvi.tif").squeeze()

result = scale_variance_raster(r, base_level_factor=2, agg_fun="mean")
print(result.components)
#    level  scale  sum_squares   df  mean_square  ss_share  ms_share  ss_cumulative
# 0      1   10.0       1.8e+5  ...          ...     0.050       ...          0.050
# ...
print(f"TSS={result.total_ss:.0f}, grand_mean={result.grand_mean:.3f}")
```

### Tabular

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
    id_cols=["county_id", "state_id", "region_id"],
)
```

### Polygon hierarchy

```python
import geopandas as gpd
from scalevar.spatial import create_hbins, join_hbins
from scalevar import scale_variance

aoi = gpd.read_file("aoi.geojson").to_crs("EPSG:27700")    # British National Grid
hbins = create_hbins(aoi, base_cell_size=100.0, n_levels=4)
per_cell = join_hbins(observations, hbins, value_col="v", agg_fun="mean")

result = scale_variance(
    per_cell,
    value="v",
    id_cols=[f"id_level_{i}" for i in range(1, 5)],
)
```

`create_hbins` **refuses geographic CRSes** (EPSG:4326 and friends) — scale variance measures variance across cell *sizes*, which needs linear units. Project first.

## What's in the result

[`ScaleVarianceResult`](../docs/api-design.md#scalevarianceresult-object) has fields:

- `components` — one row per level, with `sum_squares`, `df`, `mean_square`, `ss_share`, `ss_cumulative`, and raster scale.
- `total_ss`, `total_df`, `grand_mean`, `n_levels`, `agg_fun`, `na_handling`.
- `elements` — dict `{level: DataFrame}` with one row per distinct level-`n` cell showing its contribution to `SS_level_n`.
- `wide_table` — the working table used internally (exposed for inspection).
- `level_rasters` and optional `sve` — raster-only.

The paper-canonical variance share is `components.ss_share` (sums to 1). `components.ms_share` is an alternative `MS / Σ MS` normalization reported alongside.

## Documentation

- **Docs site**: <https://jacobdein.github.io/scale-variance/> (built from `python/docs/`, deployed via GitHub Pages).
- **Example notebooks**: [`docs/examples/`](docs/examples/)
  - [`01_tabular_admin.ipynb`](docs/examples/01_tabular_admin.ipynb) — tabular admin hierarchy
  - [`02_raster_mt1972_fig3.ipynb`](docs/examples/02_raster_mt1972_fig3.ipynb) — Moellering & Tobler (1972) Figure 3, run through both the raster and tabular entry points
  - [`03_polygon_hierarchy.ipynb`](docs/examples/03_polygon_hierarchy.ipynb) — polygon hierarchy
- **Top-level docs** — the language-agnostic theory, API contract, and parity testing plan:
  - [`../docs/theory.md`](../docs/theory.md)
  - [`../docs/api-design.md`](../docs/api-design.md)
  - [`../docs/parity-testing.md`](../docs/parity-testing.md)

## Status

**v0.1.1** — this package. Validated against the 1972 paper's published totals for Figure 3 (`TSS = 1152`, `TDF = 255`). 28 pytest tests green for the library; 248 more for the [playground](https://jacobdein.github.io/scale-variance/playground/) sibling. Not yet on PyPI — ship from GitHub for now (v0.3 decision point).

The R sibling package (`r/` in the repository) is planned for **v0.2.0** alongside a cross-language parity harness that will validate both implementations against the shared [`tests/fixtures/`](../tests/fixtures/) suite. See the project [ROADMAP](../ROADMAP.md) and [CHANGELOG](../CHANGELOG.md).

## License

MIT — see [`LICENSE`](../LICENSE).
