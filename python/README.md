# scalevar (Python)

Moellering-Tobler scale-variance decomposition for rasters and nested hierarchies.

## Status

**v0.1 development.** Not yet released on PyPI. Install from source during the v0.1 build-out:

```bash
git clone https://github.com/jacobdein/scale-variance
cd scale-variance/python
pip install -e ".[raster,spatial,dev]"
```

## What it does

Given a quantity measured at the finest level of a nested hierarchy (raster pixels, counties in states, observations in grid cells), `scalevar` partitions the total variance across the levels of the hierarchy. The output tells you what fraction of the variation lives at each scale.

Implements the irregular-case formulation of Moellering & Tobler (1972), *Geographical Variances*, Geographical Analysis 4(1), 34-50.

## Quick start

### Raster

```python
import rioxarray
from scalevar import scale_variance_raster

r = rioxarray.open_rasterio("ndvi.tif").squeeze()
result = scale_variance_raster(r, agg_fun="mean")
print(result.components)
```

### Tabular

```python
import pandas as pd
from scalevar import scale_variance

df = pd.read_csv("counties.csv")
result = scale_variance(
    df,
    value="population_density",
    id_cols=["county_id", "state_id", "region_id"],
)
print(result.components)
print(f"TSS={result.total_ss}, grand_mean={result.grand_mean}")
```

## See also

- Top-level [README](../README.md) for project scope.
- [docs/theory.md](../docs/theory.md) for the mathematical formulation.
- [docs/api-design.md](../docs/api-design.md) for the stable v0.1 API contract (shared with the R sibling).
- [reference/](../reference/) for the 1972 paper and the original R implementations from which this is extracted.
