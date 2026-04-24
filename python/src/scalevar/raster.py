"""Raster entry point: ``scale_variance_raster``.

Accepts ``xarray.DataArray`` (preferred, carries CRS) or ``numpy.ndarray``
(fallback, no CRS). Aggregates iteratively by ``base_level_factor`` in each
linear dimension using the configured aggregation function, then reduces to
the same tabular decomposition as :func:`scalevar.scale_variance`.

See ``docs/theory.md`` section "The raster case as a special case" for the
algebraic identity tying the iterative-aggregation raster path to the
irregular-case tabular core.
"""

from __future__ import annotations

import math
import warnings
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from scalevar._agg import resolve_agg_fun
from scalevar.errors import MultiLayerRasterError, UnprojectedCRSError
from scalevar.result import ScaleVarianceResult

if TYPE_CHECKING:
    from numpy.typing import NDArray


_UNPROJECTED_CRS_MESSAGE = (
    "scalevar: unprojected or geographic CRS detected.\n"
    "The scale variance method requires a projected CRS with linear units "
    "(e.g. meters), because it measures variance across cell sizes. Please "
    "project the input to an appropriate local projected CRS before calling "
    "this function — for example, British National Grid (EPSG:27700) in the "
    "UK, NAD83 / UTM zone N (EPSG:269NN) in the US, or any local equidistant "
    "projection suitable for your study area.\n"
    "Received CRS: {crs}"
)

_NO_CRS_WARNING = (
    "scalevar: input raster has no CRS; scale values are in raw pixel units"
)


def scale_variance_raster(
    raster: Any,
    num_levels: int | None = None,
    base_level_factor: int = 2,
    agg_fun: str | Callable[[NDArray[np.float64]], float] = "mean",
    na_handling: str = "drop_na",
    return_sve: bool = False,
) -> ScaleVarianceResult:
    """Decompose the variance of a raster across scales by successive aggregation.

    Parameters
    ----------
    raster
        A single-band raster. ``xarray.DataArray`` is preferred (CRS and
        transform are respected via the ``rio`` accessor if rioxarray is
        installed). ``numpy.ndarray`` is accepted as a fallback — treated as
        an un-georeferenced grid with resolution ``1.0`` per pixel.
    num_levels
        Number of aggregation levels including the original (level 1). If
        ``None``, the maximum feasible is computed from raster dimensions as
        ``floor(log_b(min(nrow, ncol))) + 1``.
    base_level_factor
        Integer ≥ 2. Linear aggregation factor per step. 2 (default) means a
        4:1 area ratio per level.
    agg_fun
        Aggregation function used to build coarser levels. See
        :data:`scalevar._agg.SUPPORTED_AGG_NAMES`.
    na_handling
        ``"drop_na"`` only in v0.1.
    return_sve
        If ``True``, include ``sve`` (a ``(num_levels, nrow, ncol)`` numpy
        array of squared differences mapped back to the finest grid) in the
        result. Default ``False`` to save memory on large inputs.

    Returns
    -------
    ScaleVarianceResult
        See :class:`scalevar.result.ScaleVarianceResult`. The ``level_rasters``
        and (optionally) ``sve`` fields are populated for raster input.
    """
    if na_handling != "drop_na":
        raise ValueError(
            f"v0.1 supports only na_handling='drop_na', got {na_handling!r}"
        )
    if not isinstance(base_level_factor, int) or base_level_factor < 2:
        raise ValueError(
            f"base_level_factor must be an integer >= 2, got {base_level_factor!r}"
        )

    arr, res_xy, input_crs, input_type = _normalize_raster_input(raster)
    _validate_crs(input_crs)

    nr, nc = arr.shape
    min_dim = min(nr, nc)
    max_possible = math.floor(math.log(min_dim, base_level_factor)) + 1
    if num_levels is None:
        num_levels = max_possible
    else:
        if not isinstance(num_levels, int) or num_levels < 1:
            raise ValueError(
                f"num_levels must be a positive integer, got {num_levels!r}"
            )
        if num_levels > max_possible:
            warnings.warn(
                f"Requested num_levels ({num_levels}) exceeds the maximum "
                f"feasible for this input ({max_possible}). Capping.",
                UserWarning,
                stacklevel=2,
            )
            num_levels = max_possible
    if num_levels < 2:
        raise ValueError(
            "need at least 2 levels to decompose variance — input raster "
            f"too small for base_level_factor={base_level_factor}"
        )

    # Truncate to dimensions divisible by factor^(num_levels-1) so every
    # aggregation step divides cleanly. For the canonical power-of-b inputs
    # this is a no-op.
    step_factor = base_level_factor ** (num_levels - 1)
    trimmed_nr = (nr // step_factor) * step_factor
    trimmed_nc = (nc // step_factor) * step_factor
    if trimmed_nr != nr or trimmed_nc != nc:
        warnings.warn(
            f"Raster dimensions ({nr}x{nc}) do not divide cleanly by "
            f"base_level_factor^(num_levels-1)={step_factor}; truncating to "
            f"({trimmed_nr}x{trimmed_nc}).",
            UserWarning,
            stacklevel=2,
        )
        arr = arr[:trimmed_nr, :trimmed_nc].copy()

    agg_callable, agg_name = resolve_agg_fun(agg_fun)

    level_arrays: list[NDArray[np.float64]] = [arr.astype(np.float64, copy=True)]
    for _ in range(1, num_levels):
        level_arrays.append(
            _block_reduce_2d(level_arrays[-1], base_level_factor, agg_callable, agg_name)
        )

    # Disaggregate each level back to finest-grid resolution so every original
    # cell carries its level-n parent's value. Factor^(level-1) repetitions.
    disagg_by_level: list[NDArray[np.float64]] = []
    for lvl, lvl_arr in enumerate(level_arrays, start=1):
        factor = base_level_factor ** (lvl - 1)
        disagg_by_level.append(_disaggregate(lvl_arr, factor))

    grid_shape = level_arrays[0].shape
    # Finest-level non-NA mask — the universe of valid cells for this analysis.
    valid = ~np.isnan(level_arrays[0])
    if not valid.any():
        raise ValueError("Input raster contains only NA values at level 1.")

    # Build a long-format dataframe to reuse the tabular decomposition logic.
    flat_valid_idx = np.flatnonzero(valid.ravel())
    rows, cols = np.unravel_index(flat_valid_idx, grid_shape)

    data: dict[str, Any] = {"_value": level_arrays[0].ravel()[flat_valid_idx]}
    id_cols: list[str] = []
    for lvl in range(1, num_levels + 1):
        factor = base_level_factor ** (lvl - 1)
        lvl_shape = level_arrays[lvl - 1].shape
        ids = (rows // factor) * lvl_shape[1] + (cols // factor)
        col = f"id_level_{lvl}"
        data[col] = ids
        id_cols.append(col)
    tab = pd.DataFrame(data)

    scales = [float(res_xy * (base_level_factor ** (lvl - 1))) for lvl in range(1, num_levels + 1)]

    from scalevar.tabular import scale_variance as _sv_tabular

    base = _sv_tabular(
        tab,
        value="_value",
        id_cols=id_cols,
        agg_fun=agg_fun,
        na_handling=na_handling,
    )

    # Override the components.scale column (tabular core fills NaN).
    components = base.components.copy()
    components["scale"] = scales

    level_rasters: dict[str, Any] = {}
    for lvl, lvl_arr in enumerate(level_arrays, start=1):
        level_rasters[f"level_{lvl}"] = _wrap_back_to_input_type(
            lvl_arr, input_type, raster, base_level_factor ** (lvl - 1)
        )

    sve: NDArray[np.float64] | None = None
    if return_sve:
        sve_layers = np.full((num_levels, grid_shape[0], grid_shape[1]), np.nan, dtype=np.float64)
        for lvl in range(1, num_levels + 1):
            if lvl < num_levels:
                diff = disagg_by_level[lvl] - disagg_by_level[lvl - 1]
            else:
                # Top contribution: disaggregated level num_levels → grand mean.
                diff = base.grand_mean - disagg_by_level[lvl - 1]
            sq = diff * diff
            sq[~valid] = np.nan
            sve_layers[lvl - 1] = sq
        sve = sve_layers

    return ScaleVarianceResult(
        components=components,
        total_ss=base.total_ss,
        total_df=base.total_df,
        grand_mean=base.grand_mean,
        n_levels=base.n_levels,
        agg_fun=agg_name,
        na_handling=na_handling,
        elements=base.elements,
        wide_table=base.wide_table,
        level_rasters=level_rasters,
        sve=sve,
    )


def _normalize_raster_input(
    raster: Any,
) -> tuple[NDArray[np.float64], float, Any, str]:
    """Return ``(array2d, mean_resolution, crs, input_type_tag)``.

    ``input_type_tag`` is one of ``"numpy"``, ``"xarray"``. ``crs`` is either
    ``None`` (no CRS attached) or whatever the input's accessor returned.
    """
    # Lazy import to keep xarray optional.
    try:
        import xarray as xr
    except ImportError:
        xr = None  # type: ignore[assignment]

    if xr is not None and isinstance(raster, xr.DataArray):
        return _from_xarray(raster)
    if isinstance(raster, np.ndarray):
        return _from_numpy(raster)
    raise TypeError(
        f"Unsupported raster input type: {type(raster).__name__}. "
        "Expected xarray.DataArray or numpy.ndarray."
    )


def _from_numpy(arr: NDArray[Any]) -> tuple[NDArray[np.float64], float, Any, str]:
    if arr.ndim == 3:
        if arr.shape[0] == 1:
            arr = arr[0]
        else:
            raise MultiLayerRasterError(
                f"numpy.ndarray has {arr.shape[0]} bands; select a single band explicitly."
            )
    if arr.ndim != 2:
        raise ValueError(f"Expected a 2-D raster, got shape {arr.shape}")
    warnings.warn(_NO_CRS_WARNING, UserWarning, stacklevel=3)
    return arr.astype(np.float64, copy=True), 1.0, None, "numpy"


def _from_xarray(da: Any) -> tuple[NDArray[np.float64], float, Any, str]:
    # Collapse single-band extra dims (band/time/etc. of size 1) without
    # swallowing a real multi-band input.
    squeezed = da
    for dim in list(da.dims):
        if da.sizes[dim] == 1 and dim not in ("y", "x", "lat", "lon", "latitude", "longitude"):
            squeezed = squeezed.squeeze(dim=dim, drop=True)
    if squeezed.ndim != 2:
        raise MultiLayerRasterError(
            f"xarray.DataArray has non-2D shape {tuple(squeezed.sizes.items())}; "
            "select a single band explicitly."
        )

    arr = np.asarray(squeezed.values, dtype=np.float64)

    crs: Any = None
    res: float = 1.0
    try:
        rio = squeezed.rio  # type: ignore[attr-defined]
    except AttributeError:
        warnings.warn(_NO_CRS_WARNING, UserWarning, stacklevel=3)
        return arr, res, None, "xarray"
    try:
        crs = rio.crs
    except Exception:
        crs = None
    try:
        res_tuple = rio.resolution()
        if res_tuple is not None:
            res = float((abs(res_tuple[0]) + abs(res_tuple[1])) / 2.0)
    except Exception:
        pass
    if crs is None:
        warnings.warn(_NO_CRS_WARNING, UserWarning, stacklevel=3)
    return arr, res, crs, "xarray"


def _validate_crs(crs: Any) -> None:
    if crs is None:
        return
    is_geo = False
    try:
        is_geo = bool(crs.is_geographic)
    except Exception:
        try:
            s = str(crs).lower()
            is_geo = "4326" in s or "wgs 84" in s or "wgs84" in s
        except Exception:
            is_geo = False
    if is_geo:
        raise UnprojectedCRSError(_UNPROJECTED_CRS_MESSAGE.format(crs=str(crs)))


def _block_reduce_2d(
    arr: NDArray[np.float64],
    factor: int,
    agg_callable: Callable[[NDArray[np.float64]], float],
    agg_name: str,
) -> NDArray[np.float64]:
    nr, nc = arr.shape
    nr2, nc2 = nr // factor, nc // factor
    trimmed = arr[: nr2 * factor, : nc2 * factor]
    blocks = trimmed.reshape(nr2, factor, nc2, factor)
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=RuntimeWarning)
        if agg_name == "mean":
            out = np.nanmean(blocks, axis=(1, 3))
        elif agg_name == "sum":
            out = np.nansum(blocks, axis=(1, 3))
        elif agg_name == "median":
            out = np.nanmedian(blocks, axis=(1, 3))
        elif agg_name == "min":
            out = np.nanmin(blocks, axis=(1, 3))
        elif agg_name == "max":
            out = np.nanmax(blocks, axis=(1, 3))
        elif agg_name == "sd":
            out = np.nanstd(blocks, axis=(1, 3), ddof=1)
        elif agg_name == "var":
            out = np.nanvar(blocks, axis=(1, 3), ddof=1)
        else:
            out = np.full((nr2, nc2), np.nan, dtype=np.float64)
            for i in range(nr2):
                for j in range(nc2):
                    block = trimmed[
                        i * factor : (i + 1) * factor,
                        j * factor : (j + 1) * factor,
                    ].ravel()
                    out[i, j] = agg_callable(block)
    return np.asarray(out, dtype=np.float64)


def _disaggregate(arr: NDArray[np.float64], factor: int) -> NDArray[np.float64]:
    if factor == 1:
        return arr
    return np.repeat(np.repeat(arr, factor, axis=0), factor, axis=1)


def _wrap_back_to_input_type(
    lvl_arr: NDArray[np.float64],
    input_type: str,
    original: Any,
    factor: int,
) -> Any:
    """Wrap an aggregated level's numpy array back into the input's native type.

    For ``xarray`` input, we attach a new DataArray with scaled-up resolution
    when possible. For ``numpy`` input, return the numpy array directly.
    """
    if input_type == "numpy":
        return lvl_arr
    try:
        import xarray as xr
    except ImportError:
        return lvl_arr
    try:
        # Thin stand-in — we drop the exact transform since level-wise
        # coordinates need rebuilding via rio. Good enough for v0.1 use
        # (users can re-attach via rioxarray if needed).
        return xr.DataArray(lvl_arr, dims=("y", "x"))
    except Exception:
        return lvl_arr
