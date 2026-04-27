# Changelog

All notable changes to the `scalevar` packages are recorded here. This project follows [Semantic Versioning](https://semver.org/).

<!--changelog-start-->

## [v0.1.0] — 2026-04-24

First release. Python package ships from GitHub; the R sibling package is planned for v0.2 — see [ROADMAP.md](ROADMAP.md).

### Added

- **Python `scalevar` package** under `python/`. Installable via
  ```
  pip install "scalevar[raster,spatial] @ git+https://github.com/jacobdein/scale-variance.git#subdirectory=python"
  ```
- **`scale_variance(df, value, id_cols, agg_fun="mean", na_handling="drop_na")`** — tabular core. Implements the irregular-case decomposition of Moellering & Tobler (1972), Table 3. Accepts any pandas DataFrame with one column per hierarchy level (finest to coarsest) plus a numeric value column.
- **`scale_variance_raster(raster, num_levels=None, base_level_factor=2, agg_fun="mean", na_handling="drop_na", return_sve=False)`** — raster entry point. Accepts `xarray.DataArray` (preferred, carries CRS) or `numpy.ndarray` (fallback, no CRS). Aggregates iteratively by the base factor in each linear dimension and decomposes across the resulting scales.
- **`scalevar.spatial.create_hbins` and `scalevar.spatial.join_hbins`** behind the `[spatial]` extra, for polygon-hierarchy workflows. Both refuse unprojected / geographic CRSes with the exact message documented in [`docs/api-design.md`](docs/api-design.md) — a deliberate behavioral fix versus the original research codebase (see [`reference/polygon-R-implementation/crs-correction-note.txt`](reference/polygon-R-implementation/crs-correction-note.txt)).
- **Exception hierarchy**: `ScalevarError` (base, inherits from `ValueError`), `MissingColumnError`, `InsufficientLevelsError`, `NonNumericValueError`, `DuplicateIdColsError`, `UnprojectedCRSError`, `MultiLayerRasterError`.
- **`ScaleVarianceResult` dataclass** with fields `components`, `total_ss`, `total_df`, `grand_mean`, `n_levels`, `agg_fun`, `na_handling`, `elements`, `wide_table`, plus raster-only `level_rasters` and `sve`. `_repr_html_` for Jupyter.
- Aggregation functions: `"mean"`, `"sum"`, `"median"`, `"modal"`, `"min"`, `"max"`, `"sd"`, `"var"`, and arbitrary 1-D → scalar callables.
- **Hand-derived parity fixtures** at `tests/fixtures/`:
  - `fixture_mt1972_fig3` — 16×16 checkerboard from Moellering & Tobler (1972), Figure 3. Gold-standard: the paper's published `TSS = 1152`, `TDF = 255` match exactly. Ships with `derivation.md` spelling out every integer.
  - `fixture_irregular_admin` — 3-level ragged hierarchy (counties in states in regions). Hand-derived `TSS = 16080`, `TDF = 23`. Ships with `derivation.md`.
- **28 pytest tests** green. Includes identity closures (`Σ SS = TSS`, `Σ df = total_df`, `Σ ss_share = 1`), NA handling, every documented error class, tabular↔raster roundtrip, and CRS validation.
- **Three example notebooks** under `python/docs/examples/`: tabular admin hierarchy, synthetic multi-scale raster, polygon hierarchy.
- **Documentation site** powered by mkdocs-material at `python/mkdocs.yml` with auto-generated API reference via mkdocstrings. Deployed to GitHub Pages.
- **CI**: pytest + ruff across Python 3.10–3.13 on Ubuntu and macOS; docs build/deploy on push to main.

### Design notes

- **`ss_share` is the paper-canonical variance share** (`SS / TSS`, sums to 1). The polygon R reference's earlier `ms_share` normalization (`MS / Σ MS`) is also reported in `components.ms_share` for users who prefer a df-weighted share, but is not the default. See [`docs/theory.md`](docs/theory.md).
- **Direct aggregation from the raw value column** per level in the tabular core — matches the paper's `X̄_{i..}` as the mean over all level-1 cells under parent *i*, and matches the raster path exactly for the default `mean` aggregation on regular grids.
- **Sanity checks raise, not warn.** The identities `Σ SS = TSS` and `Σ df = total_df` are enforced at the end of every compute; a violation is a bug, not tolerated drift.
- **No imputation, no significance testing, no automated hierarchy construction.** Out of scope for v0.1 and onward; users wanting hypothesis tests should pipe `components.sum_squares` and `components.df` into `statsmodels` directly.

<!--changelog-end-->

[v0.1.0]: https://github.com/jacobdein/scale-variance/releases/tag/v0.1.0
