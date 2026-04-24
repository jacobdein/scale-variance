# API design

This document specifies the public API for both `scalevar` packages in language-neutral terms. Both implementations must conform; deviations (for idiomatic reasons) must be documented in each package's own README and mirrored in the parity tests.

## Design principles

1. **Raster is a first-class input.** Most users who care about scale variance are working with raster data — NDVI, land cover, elevation, species density, demographic grids. `scale_variance_raster` is the ergonomic primary API; it does the aggregation and builds the hierarchy internally.
2. **Tabular is the core.** Under the hood, every path reduces to a long-form dataframe with id-per-level columns and a value column. `scale_variance` (the tabular function) is the algorithmic core. Users whose hierarchy isn't a regular grid — ragged admin boundaries, taxonomic trees, watershed networks — call `scale_variance` directly.
3. **Hierarchy by column, not by nesting.** In the tabular core, the hierarchy is encoded as parent-ID columns — one per level — on the input frame. The core does not know or care whether those IDs come from a regular grid, H3 hexagons, watersheds, or admin boundaries.
4. **Return a structured result, not a printout.** Functions return a single object with named fields (named list in R, dataclass in Python). The object is easy to pickle/save and contains every intermediate the user might want.
5. **Explicit is better than magic.** Callers name columns.
6. **Parity over idiom where they conflict.** Field names in the returned object are identical across languages. Column types follow the host-language convention (integer vs numeric is fine); *names* do not drift.
7. **Narrow stays narrow.** No `scale_variance_batch`, no `compute_cell_values`, no domain-specific aggregation helpers. Those patterns are easy one-liners in the host language; bundling them in the package expands surface area without adding real value.

## Entry points

There are **two** public computation functions. Pick based on your input:

| You have… | Call |
| --- | --- |
| a raster (`SpatRaster` in R; `xarray.DataArray` or `numpy.ndarray` in Python) | `scale_variance_raster(...)` |
| a tabular dataframe with id-per-level columns and a value column | `scale_variance(...)` |

Plus two optional spatial helpers for polygon / point workflows: `create_hbins` (build nested 2× grids) and `join_hbins` (join observations to them to produce tabular input). These are opt-in and do not affect the core.

---

## `scale_variance_raster(raster, num_levels=None, base_level_factor=2, agg_fun="mean", na_handling="drop_na")`

**Purpose.** Decompose the variance of a raster across scales by successively aggregating it. Directly corresponds to the `compute_scale_variance_raster` function in the R reference at [`../reference/raster-R-implementation/scale-variance.R`](../reference/raster-R-implementation/scale-variance.R).

**Parameters.**

| Parameter | R type | Python type | Description |
| --- | --- | --- | --- |
| `raster` | `terra::SpatRaster` (single layer) | `xarray.DataArray` (2-D or 3-D with single band), or `numpy.ndarray` with optional `transform`/`crs` metadata | The input raster. If multiple bands/layers are present, an error is raised — callers should select a single band explicitly. |
| `num_levels` | `integer(1)` or `NULL` | `int \| None` | Number of aggregation levels including the original (level 1). If omitted, the maximum feasible is computed from raster dimensions as `floor(log_b(min(nrow, ncol))) + 1`. |
| `base_level_factor` | `integer(1)` | `int` | Integer ≥ 2. Linear aggregation factor per step. `2` (default) means 4:1 area ratio; `3` means 9:1; etc. Must divide dimensions cleanly at each step or the function truncates levels with a warning. |
| `agg_fun` | `character(1)` or function | `str \| Callable` | Aggregation function used to build coarser levels. Supported string values: `"mean"` (default), `"sum"`, `"median"`, `"modal"`, `"min"`, `"max"`, `"sd"`, `"var"`. For custom functions, pass a callable that reduces a 1-D numeric array to a scalar. |
| `na_handling` | `character(1)` | `str` | For v0.1, only `"drop_na"` is supported: level-1 cells with NA are excluded, parent values are computed from available children. Future work (v0.2): `"require_complete"`, `"error"`. |

**Returns.** A `ScaleVarianceResult` object (see below) with the common fields, plus raster-specific fields:

- `level_rasters` — list/dict of the aggregated rasters at each level, in the same type as the input.
- `sve` — optional multi-band raster of squared differences mapped back to the finest-level grid (one band per level). Returned if explicitly requested via `return_sve=True` (default `False`, to save memory on large inputs).

**CRS requirement.** Behavior depends on whether the input carries a CRS:

| Input has a CRS? | Is it projected? | Behavior |
| --- | --- | --- |
| No (e.g. plain `numpy.ndarray`, or `xarray.DataArray` without `rio` accessor / no `crs` attr) | N/A | Accepted. The `scale` column reports resolution in whatever units the raster uses (1.0 if none). A single warning is emitted at first call: `"scalevar: input raster has no CRS; scale values are in raw pixel units"`. |
| Yes | Yes (projected, linear units) | Accepted. Normal behavior. |
| Yes | No (geographic, e.g. EPSG:4326) | Errors with `UnprojectedCRSError` (Python) / `scalevar_crs_error` (R), using the exact message in the § below. |

This matches the newer raster R reference's permissive behavior on CRS-less inputs while still catching the Web Mercator class of bug that motivated the original correction note.

---

## `scale_variance(df, value, id_cols, agg_fun="mean", na_handling="drop_na")`

**Purpose.** The tabular core. Decompose the variance of `value` across the hierarchy defined by `id_cols`, following Moellering & Tobler 1972 (irregular case).

**Parameters.**

| Parameter | R type | Python type | Description |
| --- | --- | --- | --- |
| `df` | `data.frame` \| `tibble` | `pandas.DataFrame` | One row per finest-level observation. |
| `value` | `character(1)` | `str` | Name of the column holding the measured quantity. |
| `id_cols` | `character(k)` | `list[str]` of length `k` | Parent-ID column names, ordered from finest (level 1) to coarsest (level `k`). |
| `agg_fun` | `character(1)` or function | `str \| Callable` | Function used to compute parent values from children. Default `"mean"` — matches the paper. Accepts the same string values as `scale_variance_raster`, or a user callable. |
| `na_handling` | `character(1)` | `str` | For v0.1, `"drop_na"` only. |

**Returns.** A `ScaleVarianceResult` object (see next section).

**Errors.**

- Missing column names → `MissingColumnError` (Python) / `scalevar_missing_column_error` (R).
- `id_cols` empty or length 1 → `InsufficientLevelsError` ("need at least two levels to decompose variance"; a single level is just `var`).
- Any non-numeric `value` column → `NonNumericValueError`.
- Duplicate `id_cols` entries → `DuplicateIdColsError`.
- If a parent at level `n+1` has only one distinct level-`n` child (so it contributes 0 to SS and df), it is allowed — not an error. Document this in user-facing docs.

**Error contract.** All error messages are identical strings across R and Python. In R: `stop()` with `class = c("scalevar_<kind>_error", "error", "condition")`. In Python: a small exception hierarchy in `scalevar.errors`, all inheriting from `ValueError`. A parity fixture per error class asserts that both packages raise with the same message text.

---

## `ScaleVarianceResult` object

R: S3 class `"scale_variance_result"` wrapping a named list. Provide `print`, `summary`, `as.data.frame` (returns `components`).
Python: `@dataclass(frozen=True)` named `ScaleVarianceResult` with a `_repr_html_` method for Jupyter.

### Common fields (always present)

| Field | Shape | Description |
| --- | --- | --- |
| `components` | dataframe with one row per level | Per-level variance decomposition. |
| `total_ss` | scalar float | Total sum of squares around the grand mean (`TSS`). |
| `total_df` | scalar int | `N − 1`, where `N` is the count of non-NA finest-level cells. |
| `grand_mean` | scalar float | Mean of the value column after NA drop. |
| `n_levels` | scalar int | Number of user-supplied levels, `k`. |
| `agg_fun` | scalar str | Echo of the aggregation function name used. |
| `na_handling` | scalar str | Echo of the argument used. |

### The `components` dataframe

One row per level `1..k`. Columns:

| Column | Type | Description |
| --- | --- | --- |
| `level` | int | `1..k`, with 1 = finest. |
| `scale` | float | Representative "size" at this level. For rasters: mean cell resolution. For tabular input: `NA` unless the caller supplied a `scale_per_level` vector. |
| `sum_squares` | float | `SS_level_n` per the paper: `Σ (value_level_(n+1) − value_level_n)²`. |
| `df` | int | Degrees of freedom at this level. |
| `mean_square` | float | `SS / df`, with `NA` if `df == 0`. |
| `ss_share` | float | `SS_level_n / total_ss`. **Sums to 1 across levels** by the Moellering-Tobler identity (Eq. 12). This is the paper-canonical "variance share". |
| `ms_share` | float | `MS_level_n / sum(MS)`. Also sums to 1, but weighted differently. Reported for users who want a df-weighted share. |
| `ss_cumulative` | float | Cumulative sum of `ss_share` up to and including this level. |

**Invariants that parity tests must enforce.**

- `sum(components$ss_share) == 1.0` (within floating-point tolerance).
- `sum(components$sum_squares) == total_ss` (within tolerance).
- `components$mean_square == components$sum_squares / components$df` exactly where df > 0; NA where df == 0.
- `sum(components$df) == total_df`.

### `elements` (always present)

List/dict keyed by level number, one dataframe per level. Each dataframe has **one row per distinct level-`n` cell** (i.e. per child — the `id_level_n` side of the hierarchy) and columns:

- `id` — the level-`n` cell id (one row per distinct value of `id_level_n`).
- `mean_child` — that cell's level-`n` value (= `value_level_n`, constant within the level-`n` group by construction).
- `mean_parent` — the value of its level-`(n+1)` parent (= `value_level_(n+1)` for this cell).
- `sv` — `(mean_parent − mean_child)²`. Per-child contribution to `SS_level_n`. Summing `sv` across all rows of `elements[n]` recovers `SS_level_n`.
- `sv_per_df` — `sv / df_level_n`, useful for comparing rows across levels on a common denominator.

This matches the polygon R reference's `compute_sv_elements` behavior and the per-element semantic in [`theory.md`](theory.md) step 6.

For raster input, `elements[n]` can be reshaped back to a raster via `sve_to_raster()` (helper planned for v0.3; see [ROADMAP.md](../ROADMAP.md)). For tabular input, `elements[n]` is a pure dataframe.

### `wide_table` (always present)

A dataframe with one row per finest-level observation (after NA drop) and columns `value_level_1 ... value_level_(k+1)`. The working table used internally; exposed for inspection and downstream joining. For tabular input, it also carries forward the original `id_level_*` columns.

### Raster-specific fields (present only when input was a raster)

- `level_rasters` — list of the per-level aggregated rasters, keyed `level_1 .. level_k`, each in the input's raster type.
- `sve` — optional multi-band raster of squared differences (one band per level), returned only when `return_sve=True` is passed to `scale_variance_raster`. Same pixel grid as the input raster; `NA` where the input was `NA`.

---

## Spatial helpers (optional module)

Packaged as `scalevar.spatial` in Python (optional install via `pip install scalevar[spatial]`, which pulls in `geopandas`, `shapely`). In R, shipped as top-level functions in the same package with `sf` and `terra` in `Suggests:`, gated with `requireNamespace(..., quietly = TRUE)`.

### `create_hbins(aoi, base_cell_size, n_levels, base_level_factor=2)`

**Purpose.** Build a set of nested regular grids centered on an area of interest. Level 1 is the finest scale; each successive level multiplies the linear cell size by `base_level_factor`.

**Parameters.**

| Parameter | R type | Python type | Description |
| --- | --- | --- | --- |
| `aoi` | `sf` object | `geopandas.GeoDataFrame` \| `shapely.Geometry` | Area of interest. Must be in a **projected** CRS whose linear unit is meters (or equivalent). The function errors if passed a geographic CRS — see note below. |
| `base_cell_size` | `numeric(1)` | `float` | Side length of a level-1 cell in the CRS's linear units. |
| `n_levels` | `integer(1)` | `int` | Number of nested levels to generate. Must be ≥ 2. |
| `base_level_factor` | `integer(1)` | `int` | Linear scaling factor per level. Default `2` (matches the original bird study and the raster default). |

**Returns.** An `sf` / `GeoDataFrame` of all cells across all levels, with columns:

- `id` — unique integer ID per cell, stable across runs with the same parameters.
- `level` — integer level (1 = finest, `n_levels` = coarsest).
- `geometry` — the cell polygon.

The cells are aligned so that each level-`n+1` cell exactly contains `base_level_factor^2` level-`n` cells.

**CRS validation.** The original research used Web Mercator (EPSG:3857), which introduced ~37% distance distortion at London's latitude. The v0.1 function **refuses to run on geographic or unprojected CRSes** and emits a clear error with a pointer to the correction note. Callers must project their AOI first (e.g. British National Grid, EPSG:27700, for the UK). This is a behavioral *fix* versus the original code. See [`../reference/polygon-R-implementation/crs-correction-note.txt`](../reference/polygon-R-implementation/crs-correction-note.txt).

**Error contract for CRS validation.**

- R: `stop()` with `class = c("scalevar_crs_error", "error", "condition")`.
- Python: `raise scalevar.errors.UnprojectedCRSError(...)` where `UnprojectedCRSError` inherits from `ValueError`.
- **Exact message text** (identical across languages, used by `create_hbins` and `scale_variance_raster`):

  ```
  scalevar: unprojected or geographic CRS detected.
  The scale variance method requires a projected CRS with linear units (e.g. meters), because it measures variance across cell sizes. Please project the input to an appropriate local projected CRS before calling this function — for example, British National Grid (EPSG:27700) in the UK, NAD83 / UTM zone N (EPSG:269NN) in the US, or any local equidistant projection suitable for your study area.
  Received CRS: <user's CRS description here, e.g. "EPSG:4326 (WGS 84)">
  ```

- A parity fixture passes a WGS84 AOI and asserts both packages error with this exact text (substituting the received-CRS description).

### `join_hbins(observations, hbins, value_col=None, agg_fun="mean")`

**Purpose.** Assign each observation to the level-1 cell it falls in, compute per-cell values (if `value_col` supplied), and join parent IDs for every higher level — producing a tabular input ready for `scale_variance`.

**Parameters.**

| Parameter | Description |
| --- | --- |
| `observations` | Point layer (`sf` / `GeoDataFrame`) with at least a geometry column. |
| `hbins` | Output of `create_hbins`. |
| `value_col` | Optional column in `observations` to aggregate per cell. If `None`, the caller is expected to supply the value column themselves after the join. |
| `agg_fun` | Function used when aggregating points to cells. Same vocabulary as the core. |

**Returns.** A non-spatial dataframe with `id_level_1 ... id_level_k` integer columns and (if `value_col` was provided) an aggregated value column. Observations outside the AOI are dropped.

---

## Idiomatic conveniences

These may differ between packages without breaking parity:

- **R:** `scale_variance` should accept NSE column names via `rlang::enquo()` for the `value` argument (so `scale_variance(df, estD, c("id_level1","id_level2","id_level3"))` works). Under the hood this resolves to the same string-based resolution used by the Python package. Parity tests always pass strings.
- **Python:** `ScaleVarianceResult` has `_repr_html_` for Jupyter. R's S3 object's `print` method produces a readable summary.
- **Both:** offer a convenience helper `id_cols_from_pattern(df, pattern="id_level_{n}")` that returns the list of id columns in order. Optional; do not make the core function depend on it.

---

## Naming conventions

- **Public R functions:** `snake_case`, no dots. `scale_variance`, `scale_variance_raster`, `create_hbins`, `join_hbins`.
- **Public Python functions:** `snake_case`. Same names as R.
- **Python classes:** `PascalCase`. `ScaleVarianceResult`.
- **R result object:** S3 class `"scale_variance_result"`.

## What is NOT in v0.1

Explicitly out-of-scope for v0.1 — these were in earlier drafts or exist in the bird-study reference code and have been removed:

- **`scale_variance_batch`.** Looping over a grouping variable (e.g. Hill numbers `q=0,1,2`) is a one-liner in both languages. Not worth a wrapper.
- **`compute_cell_values`.** `df.groupby(id_col).agg(fn)` (Python) / `df |> group_by(id_col) |> summarise(value = fn(x))` (R). Domain-specific glue doesn't belong in the package.
- **Imputation, kriging, diversity estimation, any domain-specific helpers.** Stay narrow.

## Version and compatibility

- The v0.1 API above is the stable contract. Breaking changes require a major version bump.
- Internal fields of the result object beginning with `_` are not part of the stable contract; the fields documented above are.
- Both packages target the language baselines currently in broad use: R ≥ 4.1 (for native pipe support), Python ≥ 3.10 (for `match` and modern type hints).
