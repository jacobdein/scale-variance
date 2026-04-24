# Roadmap

## v0.1.0 — Working R + Python packages on GitHub

Scope locked. Ship from GitHub; no CRAN / PyPI publication yet.

- Core `scale_variance` decomposition implementing the Moellering & Tobler (1972) irregular case.
- Raster-first entry point `scale_variance_raster` with configurable `base_level_factor` (2×, 3×, 4×, …) and configurable `agg_fun` (`mean`, `sum`, `median`, `modal`, …).
- Optional spatial helpers `create_hbins` and `join_hbins` for polygon-based workflows, refusing unprojected CRSes (a deliberate fix relative to the original bird-diversity study code).
- Parity between R and Python enforced by a shared fixture suite in `tests/fixtures/` and a parity harness in CI. Gold-standard fixture: Moellering & Tobler Fig 3 (`TSS = 1152`, `TDF = 255`).
- Per-package unit tests, vignette / notebook examples for three cases (non-spatial tabular, raster, polygon hierarchy), documentation site.
- `CITATION.cff` pointing at the 1972 paper.

Definition of done is in [`CLAUDE.md`](CLAUDE.md).

## v0.2.0 — First public release

- Configurable `na_handling`: `"drop_na"` (current default), `"require_complete"` (raise on any NA at level 1), `"error"` (strictest — raise on NAs or unexpected fan-out).
- Publish R package to r-universe and submit to CRAN.
- Publish Python package to PyPI.
- Accept feedback from early users; harden error messages.

## v0.3.0 — Richer raster integration

- Python: robust CRS validation via `rioxarray`; support for `xarray.Dataset` multi-variable inputs (compute scale variance for each variable in one call, returning a dict of results).
- R: `stars` cube support alongside `terra::SpatRaster`.
- Helper `sve_to_raster(result, level)` to reshape `elements[[n]]` back into a SpatRaster / DataArray for mapping where variance accumulates.
- Multi-band / multi-variable plotting helpers (patchwork / matplotlib) that recreate the figure style used in the research paper — as a "getting started" notebook, not a function export.

## v0.4.0 — Generalized hierarchies

The raster path already handles 2×, 3×, 4× nesting via `base_level_factor`. Extend the tabular path to make non-grid hierarchies ergonomic.

- `build_parent_ids(geometries, containing_geometries_per_level)` helper for user-supplied hierarchies of non-grid shape (hexagons / H3, admin boundaries, watershed trees).
- A worked vignette: scale variance on hex bins (H3).
- A worked vignette: scale variance on an irregular admin hierarchy (counties → states → census regions).

## v0.5.0 / v1.0 — JOSS submission

- Paper writeup in `paper/paper.md` + `paper/paper.bib` per the JOSS template.
- Stable API; semver commitment.
- At least 3–5 external users / citations / downstream tools demonstrating adoption.
- Optional: publication alongside a domain paper applying `scalevar` to a new dataset.

## Later / under consideration

- Bootstrap confidence intervals for the variance components. Optional; would reintroduce a sampling interpretation (Type II ANOVA) that the original fixed-effects framing does not include. Needs a design doc before committing.
- Performance benchmarking harness. Not expected to matter for typical sizes; revisit if a user shows up with 10M+ finest-level cells or multi-gigapixel rasters.
- Rust core and FFI bindings. Considered and rejected for v0.1. Revisit only if real perf need emerges and the user community can maintain the Rust layer.
- Integration with Google Earth Engine (`rgee`, Python `earthengine-api`) for cloud-scale raster inputs.
- A CLI entry point for ad-hoc analyses (`scalevar raster input.tif --agg mean --out components.csv`).
