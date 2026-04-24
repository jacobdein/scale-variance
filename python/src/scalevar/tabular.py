"""Tabular core: ``scale_variance``.

The algorithmic heart of the package. Every other entry point (raster,
polygon-hierarchy) reduces to producing a tabular input with id-per-level
columns and calling this function — or, for efficiency, mirroring its
logic against the native data structure (the raster path currently does
the latter to avoid an O(num_cells × num_levels) materialization).

Implements the irregular-case formulation of Moellering & Tobler (1972),
Table 3. See ``docs/theory.md`` for the derivation and algorithm steps.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from scalevar._agg import resolve_agg_fun
from scalevar.errors import (
    DuplicateIdColsError,
    InsufficientLevelsError,
    MissingColumnError,
    NonNumericValueError,
)
from scalevar.result import ScaleVarianceResult

if TYPE_CHECKING:
    from numpy.typing import NDArray


def scale_variance(
    df: pd.DataFrame,
    value: str,
    id_cols: Sequence[str],
    agg_fun: str | Callable[[NDArray[np.float64]], float] = "mean",
    na_handling: str = "drop_na",
) -> ScaleVarianceResult:
    """Decompose the variance of ``value`` across a nested hierarchy.

    The hierarchy is encoded as one column per level on ``df``, ordered from
    finest (``id_cols[0]``, level 1) to coarsest (``id_cols[-1]``, level k).
    Every finest-level observation is one row.

    Follows the irregular-case algorithm of Moellering & Tobler (1972),
    Table 3. See :doc:`../../docs/theory.md` for the step-by-step derivation.

    Parameters
    ----------
    df
        One row per finest-level observation.
    value
        Name of the numeric column holding the measured quantity.
    id_cols
        Parent-ID column names, ordered finest → coarsest.
    agg_fun
        Function used to compute parent values from child values at each
        level. Default ``"mean"`` — matches the paper. See
        :data:`scalevar._agg.SUPPORTED_AGG_NAMES` for string options; any
        callable that reduces a 1-D array to a scalar also works.
    na_handling
        ``"drop_na"`` (v0.1 only): rows with NA ``value`` are excluded and
        parent values are computed from available children.

    Returns
    -------
    ScaleVarianceResult
        See :class:`scalevar.result.ScaleVarianceResult`.

    References
    ----------
    Moellering, H., & Tobler, W. (1972). Geographical Variances.
    *Geographical Analysis*, 4(1), 34-50.
    """
    if na_handling != "drop_na":
        raise ValueError(
            f"v0.1 supports only na_handling='drop_na', got {na_handling!r}. "
            "'require_complete' and 'error' are planned for v0.2."
        )

    id_cols = list(id_cols)
    if len(id_cols) < 2:
        raise InsufficientLevelsError(
            "need at least two levels to decompose variance"
        )
    if len(set(id_cols)) != len(id_cols):
        raise DuplicateIdColsError(
            f"id_cols contains duplicate entries: {id_cols}"
        )
    missing = [c for c in [value, *id_cols] if c not in df.columns]
    if missing:
        raise MissingColumnError(f"columns not found on input df: {missing}")
    if not pd.api.types.is_numeric_dtype(df[value]):
        raise NonNumericValueError(
            f"value column {value!r} is not numeric (dtype={df[value].dtype})"
        )

    agg_callable, agg_name = resolve_agg_fun(agg_fun)
    k = len(id_cols)

    cols = [value, *id_cols]
    work = df.loc[:, cols].dropna(subset=[value]).reset_index(drop=True).copy()
    n_valid = len(work)
    if n_valid == 0:
        raise ValueError("no non-NA rows in value column")

    grand_mean = float(work[value].astype(float).mean())

    # value_level_1 = raw value. For level n >= 2 we aggregate the raw level-1
    # values directly per id_level_n — the paper-canonical (direct) semantic.
    # For agg_fun='mean' or 'sum' this is equivalent to iterative aggregation
    # from the previous level; for other functions (median, modal, min, max),
    # direct aggregation over level-1 cells is what ``docs/theory.md`` spells
    # out and what the tabular core exposes.
    wide = work.copy()
    wide["value_level_1"] = wide[value].astype(float)
    for n in range(2, k + 1):
        id_col = id_cols[n - 1]
        wide[f"value_level_{n}"] = _groupwise_agg(wide, id_col, "value_level_1", agg_callable)
    wide[f"value_level_{k + 1}"] = grand_mean

    # SS per level: Σ over original cells of (value_level_{n+1} − value_level_n)².
    sum_squares: list[float] = []
    for n in range(1, k + 1):
        diff = wide[f"value_level_{n + 1}"].to_numpy() - wide[f"value_level_{n}"].to_numpy()
        sum_squares.append(float(np.sum(diff * diff)))

    # df per level, per-parent form:
    #   df_n = Σ over level-(n+1) parents of (distinct level-n children − 1)
    # For n = k the single synthetic top parent covers everything.
    df_per_level: list[int] = []
    for n in range(1, k + 1):
        child_col = id_cols[n - 1]
        if n < k:
            parent_col = id_cols[n]
            counts = wide.groupby(parent_col, sort=False)[child_col].nunique()
            df_per_level.append(int((counts - 1).clip(lower=0).sum()))
        else:
            df_per_level.append(int(wide[child_col].nunique() - 1))

    total_ss = float(np.sum((wide["value_level_1"].to_numpy() - grand_mean) ** 2))
    total_df = n_valid - 1

    # Sanity checks — see docs/theory.md closing identity.
    ss_sum = float(sum(sum_squares))
    if abs(ss_sum - total_ss) > 1e-9 * max(abs(total_ss), 1.0):
        raise RuntimeError(
            f"scalevar internal error: Σ SS_n ({ss_sum}) ≠ TSS ({total_ss}). "
            "This indicates a bug, not tolerated drift; please file an issue."
        )
    df_sum = sum(df_per_level)
    if df_sum != total_df:
        raise RuntimeError(
            f"scalevar internal error: Σ df_n ({df_sum}) ≠ total_df ({total_df}). "
            "This indicates a bug, not tolerated drift; please file an issue."
        )

    components = _build_components(
        sum_squares=sum_squares,
        df_per_level=df_per_level,
        total_ss=total_ss,
        scales=[float("nan")] * k,
    )
    elements = _build_elements(wide=wide, id_cols=id_cols, df_per_level=df_per_level)

    return ScaleVarianceResult(
        components=components,
        total_ss=total_ss,
        total_df=total_df,
        grand_mean=grand_mean,
        n_levels=k,
        agg_fun=agg_name,
        na_handling=na_handling,
        elements=elements,
        wide_table=wide.drop(columns=[value]).assign(**{value: wide[value]}),
        level_rasters=None,
        sve=None,
    )


def _groupwise_agg(
    frame: pd.DataFrame,
    group_col: str,
    value_col: str,
    agg_callable: Callable[[NDArray[np.float64]], float],
) -> pd.Series:
    """Apply ``agg_callable`` per group and broadcast back to the row order.

    pandas' ``groupby(...).transform(func)`` only accepts a narrow set of
    vectorized reducers; for arbitrary scalar-returning callables we go
    through ``apply`` on a numpy array and re-align.
    """
    agg_map = frame.groupby(group_col, sort=False)[value_col].apply(
        lambda s: agg_callable(s.to_numpy(dtype=np.float64))
    )
    return frame[group_col].map(agg_map).astype(float)


def _build_components(
    sum_squares: list[float],
    df_per_level: list[int],
    total_ss: float,
    scales: list[float],
) -> pd.DataFrame:
    k = len(sum_squares)
    mean_square = [
        (s / d) if d > 0 else float("nan")
        for s, d in zip(sum_squares, df_per_level, strict=True)
    ]
    ss_share = [
        (s / total_ss) if total_ss > 0 else 0.0 for s in sum_squares
    ]
    ms_valid = [m for m in mean_square if not np.isnan(m)]
    ms_sum = float(sum(ms_valid)) if ms_valid else 0.0
    ms_share = [
        (m / ms_sum) if (ms_sum > 0 and not np.isnan(m)) else float("nan")
        for m in mean_square
    ]
    cumulative = np.cumsum(np.array(ss_share, dtype=float)).tolist()

    return pd.DataFrame(
        {
            "level": list(range(1, k + 1)),
            "scale": scales,
            "sum_squares": sum_squares,
            "df": df_per_level,
            "mean_square": mean_square,
            "ss_share": ss_share,
            "ms_share": ms_share,
            "ss_cumulative": cumulative,
        }
    )


def _build_elements(
    wide: pd.DataFrame,
    id_cols: Sequence[str],
    df_per_level: Sequence[int],
) -> dict[int, pd.DataFrame]:
    """Per-level tables keyed by level number.

    One row per distinct level-``n`` id. ``mean_child`` is that cell's
    level-``n`` value, ``mean_parent`` is its level-``(n+1)`` parent's value
    (both constant within a level-``n`` group by construction), and ``sv``
    is ``(mean_parent − mean_child)²`` — the per-child contribution to
    ``SS_level_n``. ``sv_per_df`` is ``sv / df_n`` for cross-level comparison.

    Matches the polygon R reference's ``compute_sv_elements`` behavior and
    the per-element semantic of ``docs/theory.md`` step 6.
    """
    out: dict[int, pd.DataFrame] = {}
    k = len(id_cols)
    for n in range(1, k + 1):
        child_col = id_cols[n - 1]
        value_n = f"value_level_{n}"
        value_np1 = f"value_level_{n + 1}"
        grouped = (
            wide.groupby(child_col, sort=True)[[value_n, value_np1]]
            .first()
            .reset_index()
            .rename(columns={child_col: "id", value_n: "mean_child", value_np1: "mean_parent"})
        )
        grouped["sv"] = (grouped["mean_parent"] - grouped["mean_child"]) ** 2
        df_n = df_per_level[n - 1]
        grouped["sv_per_df"] = (
            grouped["sv"] / df_n if df_n > 0 else float("nan")
        )
        out[n] = grouped
    return out
