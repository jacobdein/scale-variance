# scalevar (Python)

**Scale variance decomposition for rasters and nested hierarchies.**

`scalevar` partitions the total variance of a variable measured across a nested hierarchy into the share attributable to each level of that hierarchy. It is a direct implementation of the method introduced by Moellering and Tobler (1972), *Geographical Variances*.

!!! tip "Try it in your browser"
    Drag a slider, watch the lollipop chart reshape, copy a paste-ready Python snippet for your thesis: **[open the interactive playground →](playground.md)**. Runs entirely in your browser via Pyodide; nothing is sent to a server.

## What it does

Given a quantity — raster pixels, survey points, administrative areas — measured at the finest level of a nested hierarchy, `scalevar` answers:

> Of the total variation in this quantity, how much is explained by differences within each hierarchical scale?

The decomposition follows a fully-nested fixed-effects ANOVA (Moellering & Tobler Eq. 12):

$$
SS_\text{total} = SS_\text{level 1} + SS_\text{level 2} + \cdots + SS_\text{level k}
$$

Each $SS_\text{level n}$ is the variation explained by moving from the finer level $n$ to the next coarser level $n{+}1$. Dividing by $SS_\text{total}$ gives the **share of variance attributable to that scale** — the output column `ss_share`, which sums to 1 across levels. See the [theory page](theory.md) for the full derivation.

## Two entry points

| You have… | Call |
|---|---|
| a raster (`xarray.DataArray` or `numpy.ndarray`) | [`scale_variance_raster`](api.md#scalevar.scale_variance_raster) |
| a tabular dataframe with id-per-level columns | [`scale_variance`](api.md#scalevar.scale_variance) |

Plus optional spatial helpers [`create_hbins`](api.md#scalevar.spatial.create_hbins) and [`join_hbins`](api.md#scalevar.spatial.join_hbins) for polygon-based workflows, behind the `[spatial]` extra.

## Install

```bash
pip install "scalevar[raster,spatial] @ git+https://github.com/jacobdein/scale-variance.git#subdirectory=python"
```

## Quick example

```python
import rioxarray as rxr
from scalevar import scale_variance_raster

ndvi = rxr.open_rasterio("ndvi.tif").squeeze()

result = scale_variance_raster(ndvi, base_level_factor=2, agg_fun="mean")
print(result.components)
```

See the [getting started guide](getting-started.md) and the three [worked examples](examples/index.md).

## Status

**v0.1.0** — Python package, shipped from GitHub. Validated against the 1972 paper's published totals (`TSS = 1152`, `TDF = 255` for the Figure 3 checkerboard) and a hand-derived ragged-admin fixture. Not yet on PyPI.

The R sibling package (`r/` in the repository) is planned for **v0.2.0** alongside a cross-language parity harness. See the project [ROADMAP](https://github.com/jacobdein/scale-variance/blob/main/ROADMAP.md) for details.

