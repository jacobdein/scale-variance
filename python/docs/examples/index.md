# Examples

Three Jupyter notebooks, each under 5 seconds to run:

1. **[Tabular admin hierarchy](01_tabular_admin.ipynb)** — `scale_variance` on a non-spatial ragged hierarchy (counties → states → regions). No raster, no CRS, no geometry. Same code path as the hand-derived `fixture_irregular_admin`.
2. **[Synthetic multi-scale raster](02_raster_synthetic.ipynb)** — `scale_variance_raster` on a 128×128 raster built as a sum of sinusoids at three distinct frequencies. Shows the classic multi-peak lollipop plot and the per-scale SVE maps (`return_sve=True`).
3. **[Polygon hierarchy](03_polygon_hierarchy.ipynb)** — `create_hbins` + `join_hbins` + `scale_variance`. A 1 km × 1 km AOI in British National Grid with 400 random point observations joined to a 4-level nested grid. Also shows the `UnprojectedCRSError` safety behavior.

Source for all three lives in the repository at [`python/docs/examples/`](https://github.com/jacobdein/scale-variance/tree/main/python/docs/examples). They're regenerated from `_build_notebooks.py` — that script is the single source of truth for each notebook's content.
