# scalevar

**Scale variance decomposition for hierarchical data.**

`scalevar` partitions the total variance of a variable measured across a nested hierarchy into the share attributable to each level of that hierarchy. It is a direct implementation of the method introduced by Moellering and Tobler (1972), *Geographical Variances*.

Two reference implementations live in this repository:

- **R package** in `r/` — idiomatic tidyverse-friendly API, publishable to CRAN / r-universe.
- **Python package** in `python/` — idiomatic pandas / numpy / xarray API, publishable to PyPI.

Both packages share a common algorithmic core, language-agnostic tests, and identical return shapes so that results are bit-for-bit comparable across languages.

## What is scale variance?

Given a quantity measured across observation units — raster pixels, survey points, administrative areas — and a nested hierarchy that groups those units into successively coarser parents, scale variance answers:

> Of the total variation in this quantity, how much is explained by differences *within* each hierarchical scale?

The decomposition follows a fully-nested fixed-effects ANOVA (Moellering & Tobler Eq. 12):

```
SS_total  =  SS_level_1  +  SS_level_2  +  ...  +  SS_level_k
```

Each `SS_level_n` is the variation explained by moving from the finer level `n` to the next coarser level `n+1`. Dividing by `SS_total` gives the **share of variance attributable to that scale** — the output column `ss_share`, which sums to 1 across levels.

See [`docs/theory.md`](docs/theory.md) for the full derivation, and the 1972 paper at [`reference/Moellering-1972-Geographical Variances.pdf`](reference/Moellering-1972-Geographical%20Variances.pdf).

## Why a package?

The method is simple but fiddly in practice: hierarchies can be ragged, missing values need consistent handling, degrees-of-freedom accounting differs by case, and the paper-canonical normalization (`SS / TSS`) is easy to confuse with the intuitive-but-different `MS / Σ MS`. Reimplementing it ad hoc — as the authors have done more than once while developing this method in research projects — is error-prone. `scalevar` gives a tested, documented, citeable primitive.

## What `scalevar` is good for

The method is not intrinsically spatial. It applies to any nested hierarchy where you have a scalar value at the finest level:

- **Raster analysis.** NDVI, land cover, elevation, species density, population density, nighttime lights — anywhere you want to ask "at what scale does most of the variation live?"
- **Polygon hierarchies.** Admin boundaries (tract → county → state), watershed hierarchies, political districts.
- **Non-spatial hierarchies.** Taxonomic trees (species → genus → family), organizational structures, temporal bins (hour → day → week).

A thin optional spatial module builds regular nested grids on top of `sf` / `geopandas` for users who want the Moellering & Tobler workflow out of the box.

## Quick start (target API — implementation in progress)

### Raster input (the main path)

**Python**

```python
import rioxarray as rxr
from scalevar import scale_variance_raster

ndvi = rxr.open_rasterio("ndvi.tif").squeeze()   # or numpy.ndarray

result = scale_variance_raster(ndvi, base_level_factor=2, agg_fun="mean")
print(result.components)
#    level    scale  sum_squares    df  mean_square  ss_share  ms_share  ss_cumulative
# 0      1     15.6     183621.4  ...    ...         0.050     ...       0.050
# 1      2     31.2     319056.9  ...    ...         0.087     ...       0.137
# ...
```

**R**

```r
library(terra)
library(scalevar)

ndvi <- rast("ndvi.tif")
result <- scale_variance_raster(ndvi, base_level_factor = 2, agg_fun = "mean")
result$components
```

### Tabular input (custom hierarchies)

**Python**

```python
import pandas as pd
from scalevar import scale_variance

df = pd.DataFrame({
    "id_level1": [1, 2, 3, 4, 5, 6, 7, 8],
    "id_level2": [1, 1, 2, 2, 1, 1, 2, 2],
    "id_level3": [1, 1, 1, 1, 1, 1, 1, 1],
    "value":     [1.0, 2.0, 3.0, 4.0, 1.5, 2.5, 3.5, 4.5],
})

result = scale_variance(df, value="value",
                        id_cols=["id_level1", "id_level2", "id_level3"])
```

## Citation

If you use `scalevar` in research, please cite the original method:

> Moellering, H., & Tobler, W. (1972). Geographical Variances. *Geographical Analysis*, 4(1), 34–50. https://doi.org/10.1111/j.1538-4632.1972.tb00455.x

A `CITATION.cff` file is provided with machine-readable citation metadata.

## License

MIT — see [`LICENSE`](LICENSE).

## Status

Pre-release. See [`ROADMAP.md`](ROADMAP.md) for v0.1 scope and what comes next. The working design brief for building this out is in [`CLAUDE.md`](CLAUDE.md). The reference implementations the packages are being extracted from live in [`reference/`](reference/) — see that folder's README for their provenance.
