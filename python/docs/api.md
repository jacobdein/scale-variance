# API reference

Everything on this page is part of the stable v0.1 public API contract. See the shared language-agnostic spec at [`docs/api-design.md`](https://github.com/jacobdein/scale-variance/blob/main/docs/api-design.md) in the repository root — the R sibling (v0.2.0) will conform to the same contract.

## Top-level functions

::: scalevar.scale_variance

::: scalevar.scale_variance_raster

## Result object

::: scalevar.ScaleVarianceResult
    options:
      members:
        - components
        - total_ss
        - total_df
        - grand_mean
        - n_levels
        - agg_fun
        - na_handling
        - elements
        - wide_table
        - level_rasters
        - sve

## Spatial helpers

Import from `scalevar.spatial`. Requires the `[spatial]` extra:

```bash
pip install "scalevar[spatial] @ git+https://github.com/jacobdein/scale-variance.git#subdirectory=python"
```

::: scalevar.spatial.create_hbins

::: scalevar.spatial.join_hbins

## Errors

All scalevar errors derive from [`ScalevarError`](#scalevar.ScalevarError) which itself derives from `ValueError`, so callers who want a single guard can catch `ValueError`.

::: scalevar.ScalevarError

::: scalevar.MissingColumnError

::: scalevar.InsufficientLevelsError

::: scalevar.NonNumericValueError

::: scalevar.DuplicateIdColsError

::: scalevar.UnprojectedCRSError

::: scalevar.MultiLayerRasterError
