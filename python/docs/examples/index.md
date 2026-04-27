# Examples

Three Jupyter notebooks, each under 5 seconds to run:

1. **[Tabular admin hierarchy](01_tabular_admin.ipynb)** — `scale_variance` on a non-spatial ragged hierarchy (counties → states → regions). No raster, no CRS, no geometry. Same code path as the hand-derived `fixture_irregular_admin`.
2. **[Moellering & Tobler (1972) Figure 3](02_raster_mt1972_fig3.ipynb)** — the paper's canonical 16×16 checkerboard worked end-to-end through both `scale_variance_raster` and `scale_variance` (after a row-major flatten). Both paths produce identical components and reproduce the paper's published totals `TSS = 1152`, `TDF = 255`. Source for the README hero figure.
3. **[Polygon hierarchy](03_polygon_hierarchy.ipynb)** — `create_hbins` + `join_hbins` + `scale_variance`. A 1 km × 1 km AOI in British National Grid with 400 random point observations joined to a 4-level nested grid. Also shows the `UnprojectedCRSError` safety behavior.

Source for all three lives in the repository at [`python/docs/examples/`](https://github.com/jacobdein/scale-variance/tree/main/python/docs/examples). They're regenerated from `_build_notebooks.py` — that script is the single source of truth for each notebook's content.
