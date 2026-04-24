# Reference materials

## The paper

`Moellering-1972-Geographical Variances.pdf` — Moellering, H., & Tobler, W. (1972), *Geographical Variances*, Geographical Analysis 4(1), 34–50. The foundational method. Every implementation choice in `scalevar` traces back to this paper. In particular, Table 3 ("Formulae for the Variances: Irregular Case") is what the `scale_variance` core implements, and Figure 3 (the 16×16 checkerboard matrix) is the canonical parity fixture.

## Two R reference implementations

The `scalevar` packages are being extracted from a research codebase that contains **two** implementations of the method, developed at different times for different data types. Both are authoritative for v0.1.

### `raster-R-implementation/` — canonical for v0.1

Written after the polygon implementation, for a remote-sensing / land-cover study. This is the cleaner, more faithful-to-paper implementation, and is **the primary target for v0.1 behavior**.

- `scale-variance.R` — the `compute_scale_variance_raster` function. Takes a `terra::SpatRaster`, aggregates it across levels with a user-specified function (`mean`, `sum`, `median`, `modal`, …), computes the SS/df/MS decomposition per level. Normalizes proportions as `SS / TSS` (matches Moellering & Tobler Eq. 12). Already parameterized over `base_level_factor` (2, 3, 4, …) and auto-detects level count from raster dimensions.
- `scale-variance-example.R` — runnable examples, including Example 4 which reproduces Moellering & Tobler Fig 3 (expected: `TSS = 1152`, `TDF = 255`). This is the gold-standard fixture for parity testing.
- `ndvi-landcover-pipeline.R` — the research pipeline: applies `compute_scale_variance_raster` to NDVI and several binary land-cover class rasters over Greater London. Demonstrates the intended real-world usage pattern.
- `scale_variance_summary.csv` — the resulting variance-by-scale summary across NDVI and six land-cover classes (water, urban, suburban, woods, vegetation, arable). Useful sanity-check data.

### `polygon-R-implementation/` — earlier, historical, more constrained

The original implementation from the bird diversity study. Retained for historical traceability and because the spatial grid construction (`create_hbins`) and hierarchical polygon workflow is still useful for non-raster data (e.g. irregular admin boundaries, ad-hoc polygon hierarchies).

- `5 - compute scale variance.R` — polygon-form `compute_scale_variance`. Operates on an `sf` polygon layer with per-cell values, computes parent means via `st_within` joins, normalizes by **mean squares summed to 1** (not SS/TSS — this is a deviation from the paper that the raster version corrects).
- `1 - create hbins.R` — nested 2× grid generator. Referenced for the `create_hbins` optional spatial helper in the packages.
- `2 - join hbin IDs.R` — joins point observations to the nested grid to produce a tabular input.
- `crs-correction-note.txt` — the post-publication correction note explaining the Web Mercator distortion. The packages' spatial helpers refuse unprojected CRSes as a deliberate behavioral fix.

## Known normalization discrepancy

The two references disagree on how to express the components as proportions:

- **raster** (correct, paper-canonical): `ss_share = SS_level / TSS`. Sums to 1 across levels. Matches Moellering & Tobler Eq. 10 / 12.
- **polygon** (incorrect but intuitive): `ms_share = MS_level / sum(MS)`. Sums to 1, but weights by inverse df at each level — a different quantity from what the paper defines.

Both are reported in the packages under distinct names (`ss_share` and `ms_share`) so users can pick, but the default everywhere is `ss_share`. The polygon reference is **not** the ground truth for this field; the raster reference and the paper are.
