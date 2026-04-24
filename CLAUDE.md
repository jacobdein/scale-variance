# CLAUDE.md — build brief for `scalevar`

This file is the working handoff to Claude Code. Read it end-to-end before writing any code. Then read, in order: `docs/theory.md`, `docs/api-design.md`, `docs/parity-testing.md`, and `reference/README.md`. The original 1972 paper is at `reference/Moellering-1972-Geographical Variances.pdf`.

## The goal

Build two open-source packages, `scalevar` (R) and `scalevar` (Python), that implement the scale-variance decomposition of Moellering & Tobler (1972). Both must conform to the API in `docs/api-design.md` and produce numerically equivalent results on every fixture in `tests/fixtures/`. Target an initial release tag of **v0.1.0**, published to GitHub only. CRAN / PyPI publication is deliberately deferred. Long-term target: a JOSS paper once the API is stable and adopted.

The package is being extracted from a real research codebase that developed the method in two passes:

1. A polygon-based workflow for a bird diversity scale-dependence study in London (2023–2024).
2. A raster-based workflow for a follow-on environmental factors study using NDVI and land-cover rasters (2025).

**The raster implementation is the canonical reference for v0.1 behavior.** It is cleaner, more faithful to the paper, and covers the main use case. The polygon implementation is retained for traceability and because its nested-grid generator (`create_hbins`) is still useful as an optional helper. See `reference/README.md` for full provenance of the two references.

You do **not** need to port the domain-specific scaffolding from either study (eBird filtering, iNEXT diversity estimation, kriging, land-cover class masking, the paper's plotting code). Only the general-purpose scale-variance algorithm and its immediate helpers belong here.

## The non-goals

- **No FFI.** No Rust or C++ core. Pure R and pure Python, two standalone implementations that share fixtures and an API spec.
- **No CRAN / PyPI publication in v0.1.** Ship from GitHub, validate the API, then publish in v0.2.
- **No domain-specific helpers.** No `scale_variance_batch`, no `compute_cell_values`, no bird-specific or ecology-specific wrappers. See `docs/api-design.md` § "What is NOT in v0.1." Users can write one-liners in the host language; bundling them adds surface area without value.
- **No spatial coupling in the tabular core.** `scale_variance(df, value, id_cols)` operates on a dataframe with integer ID columns and a value column. Spatial and raster functionality lives in clearly separated modules and is opt-in via `Suggests` (R) / extras (Python).
- **No significance testing, no imputation, no automated hierarchy construction.** See `docs/theory.md` § "What we do not implement."

## Two entry points, one core

The packages expose two public computation functions (see `docs/api-design.md` for full signatures):

- `scale_variance_raster(raster, num_levels, base_level_factor, agg_fun)` — ergonomic primary API for raster input. Uses `terra::aggregate` (R) or `xarray` / `numpy` mean-pool equivalents (Python).
- `scale_variance(df, value, id_cols, agg_fun)` — tabular core. Every path reduces to this.

Plus two optional spatial helpers: `create_hbins` (nested grid generator) and `join_hbins` (join points to grid). These are opt-in.

## Execution order

Work in this order. Do not skip ahead — each step de-risks the next.

1. **Read the docs.** `docs/theory.md`, `docs/api-design.md`, `docs/parity-testing.md`, `reference/README.md`. Skim `reference/raster-R-implementation/scale-variance.R` (the canonical R reference) and `reference/polygon-R-implementation/5 - compute scale variance.R` (the earlier form, kept for traceability). Confirm you can state, in one paragraph, what `scale_variance` does and how `SS_total = Σ SS_level_n` closes the decomposition identity. If you cannot, re-read.
2. **Generate the shared fixtures.** Build the `tests/fixtures/` bundles listed in `docs/parity-testing.md`. Start with `fixture_mt1972_fig3` — this is the gold-standard acceptance test; its expected values (`TSS = 1152`, `TDF = 255`) come directly from the 1972 paper. Then `fixture_even_3level_perfect`, `fixture_even_with_nas`, `fixture_irregular_admin` (with a `derivation.md`), and the raster-specific fixtures. Only once fixtures exist should implementation begin.
3. **Implement the Python package first.** Rationale: Python's testing toolchain is faster to iterate on, and pandas/numpy map cleanly onto the math. Start with the tabular core `scale_variance`; validate against `fixture_irregular_admin` and `fixture_even_3level_perfect`. Then add `scale_variance_raster` on top, validated against `fixture_mt1972_fig3` and the raster fixtures.
4. **Cross-check against the R reference.** Run the raster R reference (`reference/raster-R-implementation/scale-variance.R`) on every raster fixture and record its outputs. Reconcile any discrepancies per the workflow in `docs/parity-testing.md`. If the R reference is wrong on an edge case, record it in `reference/known-issues.md`.
5. **Implement the R package.** Behavioral parity with Python is the gate. Use `terra::aggregate` for the raster path — the R reference already does this.
6. **Build the parity harness** (`tests/run_parity.py`) and wire it into CI (`.github/workflows/parity.yml`). Must dispatch on fixture kind (tabular vs raster).
7. **Write the spatial polygon helpers** (`create_hbins`, `join_hbins`) in both packages. Refuse unprojected CRSes — see `reference/polygon-R-implementation/crs-correction-note.txt`. This is a deliberate behavioral fix relative to the original bird-study code.
8. **Write examples and vignettes.** Each package ships:
   - A **non-spatial tabular example** — a small synthetic admin hierarchy (region → state → county) with random values. Shows `scale_variance` on non-spatial data.
   - A **raster example** — either generate a synthetic 128×128 raster with known multi-scale structure (e.g. sum of sinusoids at multiple frequencies) or use a small subset of an open-licensed raster. Shows `scale_variance_raster` end-to-end and plots the components as a lollipop / barplot.
   - A **polygon-hierarchy example** — build `create_hbins` on a tiny AOI, join random point observations, call `scale_variance`. Shows the polygon path.
   - Keep examples fast: under 5 seconds to run.
9. **Polish.** Package websites (`pkgdown` for R, `mkdocs-material` for Python), README quick-starts that actually work, `NEWS.md` / `CHANGELOG.md`.

## Repository layout (target state)

```
scale-variance/
├── README.md                         # DONE — update to reflect raster-first API before tagging
├── CLAUDE.md                         # this file
├── LICENSE                           # DONE — MIT
├── CITATION.cff                      # DONE
├── ROADMAP.md                        # DONE
├── .gitignore                        # DONE
├── docs/
│   ├── theory.md                     # DONE
│   ├── api-design.md                 # DONE
│   └── parity-testing.md             # DONE
├── reference/
│   ├── README.md                     # DONE — explains the two R references
│   ├── Moellering-1972-Geographical Variances.pdf  # DONE
│   ├── raster-R-implementation/      # DONE — canonical for v0.1, read-only artifact
│   │   ├── scale-variance.R
│   │   ├── scale-variance-example.R
│   │   ├── ndvi-landcover-pipeline.R
│   │   └── scale_variance_summary.csv
│   └── polygon-R-implementation/     # DONE — historical, read-only artifact
│       ├── 1 - create hbins.R
│       ├── 2 - join hbin IDs.R
│       ├── 5 - compute scale variance.R
│       └── crs-correction-note.txt
├── r/                                # R package root — YOU BUILD
│   ├── DESCRIPTION
│   ├── NAMESPACE
│   ├── R/
│   ├── tests/testthat/
│   ├── inst/parity/parity_runner.R
│   ├── man/
│   └── vignettes/
├── python/                           # Python package root — YOU BUILD
│   ├── pyproject.toml
│   ├── src/scalevar/
│   ├── tests/
│   └── docs/
└── tests/
    ├── fixtures/                     # YOU BUILD
    │   ├── fixture_mt1972_fig3/
    │   ├── fixture_even_3level_perfect/
    │   ├── fixture_even_with_nas/
    │   ├── fixture_irregular_admin/
    │   ├── fixture_raster_mean_vs_sum/
    │   ├── fixture_landcover_binary/
    │   ├── fixture_base_factor_3/
    │   ├── fixture_edge_single_level/
    │   ├── fixture_crs_unprojected_aoi/
    │   └── _generate_random.py + five random fixtures
    └── run_parity.py                 # YOU BUILD
```

## Conventions

### R package
- Package name: `scalevar`. License: MIT. Depends: R ≥ 4.1.
- `DESCRIPTION` uses `Imports:` for hard dependencies only (`rlang`, `dplyr`, `tidyr`, `tibble`). `sf` and `terra` go in `Suggests:`, gated with `requireNamespace(..., quietly = TRUE)`.
- Follow `styler::style_pkg()` defaults. Document with `roxygen2`. Build pkgdown site for the docs.
- S3 class on the result object: `"scale_variance_result"`. Provide `print`, `summary`, `as.data.frame`.
- Tests with `testthat (>= 3.0)`, edition 3.
- Do not use the tidyverse meta-package; import individual packages.

### Python package
- Package name: `scalevar`. Distribution name on PyPI (eventually): `scalevar`. License: MIT. Python ≥ 3.10.
- Use `pyproject.toml`-only configuration, hatchling or setuptools. No `setup.py`. No `setup.cfg`.
- Hard dependencies: `numpy`, `pandas`. Optional extras:
  - `raster`: `xarray`, `rioxarray` (preferred for CRS-aware rasters)
  - `spatial`: `geopandas`, `shapely`
- Use `ruff` (lint + format), `mypy --strict`, `pytest`. Type hints on every public function.
- Result object: `@dataclass(frozen=True)` named `ScaleVarianceResult` with a `_repr_html_` method for Jupyter.
- Raster input dispatch: accept `xarray.DataArray` (preferred, carries CRS), `numpy.ndarray` (fallback, CRS unknown). Do not require `rioxarray` for basic use — make CRS validation conditional on `rioxarray` being available.

### Both
- Semantic versioning. v0.1.0 is the first tag.
- Never silently diverge from the behavior documented in `docs/api-design.md`. If an idiom forces a deviation, update `docs/api-design.md` in the same commit and add a fixture annotation.
- Docstrings / roxygen blocks must cite Moellering & Tobler on the main functions, with a brief sentence linking to `docs/theory.md`.

## Behavior rules to internalize

From `docs/theory.md` and the canonical raster R reference, the package must:

1. **Drop NA rows at the finest level before anything else.** Do not propagate NAs through the aggregation.
2. **Append a synthetic top level** whose value is the grand mean of the (post-NA-drop) level-1 values. The decomposition runs against this synthetic level at the top.
3. **Compute parent values from available children using the configured `agg_fun`** (default `mean`), not from a regular expected fan-out. Supported strings: `mean`, `sum`, `median`, `modal`, `min`, `max`, `sd`, `var`. Callables are also accepted.
4. **Degrees of freedom per level.** Two equivalent forms — pick whichever is natural for the input: `Σ_(parents at level n+1) (distinct children at level n − 1)` for tabular, or `N_nonNA_level_n − N_nonNA_level_(n+1)` for raster. The theory doc proves their equivalence.
5. **`ss_share` is the paper-canonical "variance share".** `ss_share_n = SS_level_n / TSS`, sums to 1 across levels. **Also report `ms_share = MS_n / sum(MS)`** for users who want a df-weighted share, but `ss_share` is the default and the column users will reach for first. **Do not** replicate the polygon reference's choice of normalizing MS to sum to 1 as the primary output — that was a deviation from the paper and is corrected here.
6. **Sanity checks at end of compute.** Assert `|Σ SS_n − TSS| < 1e-9` (relative) and `Σ df_n == total_df`. On failure, raise — do not silently warn. Violations imply a bug, not tolerated drift.
7. **Cell polygons / raster geometry never enter the tabular core.** They live in the raster path and the polygon helpers only.

## Things Claude Code should *not* decide unilaterally

Bring these back to the human if they come up:

- Any change to the API surface documented in `docs/api-design.md`.
- Renaming the package, the result object, or any public field name.
- Adding or removing fixtures from the parity suite.
- Changing the v0.1 scope (e.g. adding CRAN publication, adding helpers that were explicitly removed).
- Picking a different license.
- Reintroducing `scale_variance_batch` or `compute_cell_values` — these were deliberately cut.

Minor internal refactors, dependency pinning details, CI matrix choices, doc site theming, commit messages — you decide.

## Definition of done for v0.1.0

- [ ] `r/` and `python/` each implement the API in `docs/api-design.md` and pass all fixtures in `tests/fixtures/`, including the `fixture_mt1972_fig3` gold-standard.
- [ ] Parity harness in CI, green on every supported R × Python combo, dispatching correctly between tabular and raster fixtures.
- [ ] Spatial helpers exist and refuse unprojected CRSes with identical error messages in both packages.
- [ ] Raster helpers accept the documented input types (R: `terra::SpatRaster`; Python: `xarray.DataArray`, `numpy.ndarray`).
- [ ] Each package has a README with working quick-starts and three vignettes/notebooks: non-spatial tabular, raster, polygon-hierarchy.
- [ ] `pkgdown` site for R, `mkdocs-material` site for Python, both deployed via GitHub Pages.
- [ ] `CITATION.cff` references Moellering & Tobler 1972 (already done — verify before tagging).
- [ ] Tag `v0.1.0` on the default branch with a populated GitHub Release note derived from `NEWS.md` / `CHANGELOG.md`.

Open a PR per logical chunk. Keep the commit history clean — the research community will read it, and the eventual JOSS submission will reference it.
