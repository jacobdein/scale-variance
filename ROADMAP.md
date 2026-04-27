# Roadmap

## v0.1.0 — Python package on GitHub

Ship-from-GitHub scope. No PyPI submission yet.

- Python `scalevar` package under `python/`, installable via `pip install git+https://github.com/jacobdein/scale-variance.git#subdirectory=python`.
- Core `scale_variance` tabular decomposition implementing the Moellering & Tobler (1972) irregular case.
- Raster-first entry point `scale_variance_raster` with configurable `base_level_factor` (2×, 3×, 4×, …) and configurable `agg_fun` (`mean`, `sum`, `median`, `modal`, …). Accepts `xarray.DataArray` and `numpy.ndarray`.
- Optional spatial helpers `create_hbins` and `join_hbins` behind the `[spatial]` extra. Refuses unprojected CRSes (a deliberate fix relative to the original bird-diversity study code — see [`reference/polygon-R-implementation/crs-correction-note.txt`](reference/polygon-R-implementation/crs-correction-note.txt)).
- Shared hand-derived fixture suite under `tests/fixtures/`: `fixture_mt1972_fig3` (gold standard — `TSS = 1152`, `TDF = 255` from the paper) and `fixture_irregular_admin` (ragged 3-level, hand-derived). Both ship with a `derivation.md`.
- Three example notebooks: non-spatial tabular, Moellering & Tobler (1972) Figure 3 (raster + tabular), polygon-hierarchy.
- `mkdocs-material` documentation site under `python/docs/`, deployed via GitHub Pages.
- Python-only CI workflow running `pytest` + `ruff`.

Definition of done is in [`CLAUDE.md`](CLAUDE.md).

## v0.2.0 — R sibling + parity

The R package was always planned — it's deferred from v0.1 to let Python ship and stabilize first, then validated against the R implementation via a shared parity harness.

- R `scalevar` package under `r/`, installable via `remotes::install_github("jacobdein/scale-variance", subdir = "r")`.
- Behavioral parity with the v0.1 Python package on every fixture in `tests/fixtures/` — gold standard is `fixture_mt1972_fig3`.
- Remaining fixtures land here: `fixture_even_3level_perfect`, `fixture_even_with_nas`, `fixture_raster_mean_vs_sum`, `fixture_landcover_binary`, `fixture_base_factor_3`, `fixture_edge_single_level`, `fixture_crs_unprojected_aoi`, plus 5 random raster + 5 random tabular fixtures with a deterministic generator.
- Parity harness at `tests/run_parity.py` + R runner at `r/inst/parity/parity_runner.R`, wired into CI at `.github/workflows/parity.yml`.
- `pkgdown` site for R deployed alongside Python docs.
- PyPI and r-universe submissions decision point at this tag.

## v0.3.0 — Richer NA handling + public release

- Configurable `na_handling`: `"drop_na"` (current default), `"require_complete"` (raise on any NA at level 1), `"error"` (strictest — raise on NAs or unexpected fan-out).
- Publish R package to r-universe and submit to CRAN.
- Publish Python package to PyPI.
- Accept feedback from early users; harden error messages.

## v0.4.0 — Richer raster integration

- Python: robust CRS validation via `rioxarray`; support for `xarray.Dataset` multi-variable inputs (compute scale variance for each variable in one call, returning a dict of results).
- R: `stars` cube support alongside `terra::SpatRaster`.
- Helper `sve_to_raster(result, level)` to reshape `elements[[n]]` back into a SpatRaster / DataArray for mapping where variance accumulates.
- Multi-band / multi-variable plotting helpers (patchwork / matplotlib) that recreate the figure style used in the research paper — as a "getting started" notebook, not a function export.

## v0.5.0 — Generalized hierarchies

The raster path already handles 2×, 3×, 4× nesting via `base_level_factor`. Extend the tabular path to make non-grid hierarchies ergonomic.

- `build_parent_ids(geometries, containing_geometries_per_level)` helper for user-supplied hierarchies of non-grid shape (hexagons / H3, admin boundaries, watershed trees).
- A worked vignette: scale variance on hex bins (H3).
- A worked vignette: scale variance on an irregular admin hierarchy (counties → states → census regions).

## v0.6.0 / v1.0 — JOSS submission

- Paper writeup in `paper/paper.md` + `paper/paper.bib` per the JOSS template.
- Stable API; semver commitment.
- At least 3–5 external users / citations / downstream tools demonstrating adoption.
- Optional: publication alongside a domain paper applying `scalevar` to a new dataset.

## Later / under consideration

- Bootstrap confidence intervals for the variance components. Optional; would reintroduce a sampling interpretation (Type II ANOVA) that the original fixed-effects framing does not include. Needs a design doc before committing.
- Performance benchmarking harness. Not expected to matter for typical sizes; revisit if a user shows up with 10M+ finest-level cells or multi-gigapixel rasters.
- Rust core and FFI bindings. Considered and rejected for v0.1 / v0.2. Revisit only if real perf need emerges and the user community can maintain the Rust layer.
- Integration with Google Earth Engine (`rgee`, Python `earthengine-api`) for cloud-scale raster inputs.
- A CLI entry point for ad-hoc analyses (`scalevar raster input.tif --agg mean --out components.csv`).
