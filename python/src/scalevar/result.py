"""Result object for scale-variance decompositions.

``ScaleVarianceResult`` is the single structured return value of both
:func:`scalevar.scale_variance` and :func:`scalevar.scale_variance_raster`.
The field names are part of the v0.1 public API contract and must stay
identical across the Python and R sibling packages — see
``docs/api-design.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class ScaleVarianceResult:
    """Scale-variance decomposition result.

    Parameters
    ----------
    components
        Per-level variance decomposition. One row per user-supplied level,
        columns ``level``, ``scale``, ``sum_squares``, ``df``, ``mean_square``,
        ``ss_share``, ``ms_share``, ``ss_cumulative``. ``ss_share`` is the
        paper-canonical variance share (Moellering & Tobler 1972 Eq. 12);
        ``ms_share`` is an alternate df-weighted normalization.
    total_ss
        Total sum of squares around the grand mean (TSS).
    total_df
        ``N - 1`` where ``N`` is the count of non-NA finest-level cells.
    grand_mean
        Mean of the value column after NA drop.
    n_levels
        Number of user-supplied levels (``k``).
    agg_fun
        Echo of the aggregation function name used.
    na_handling
        Echo of the na_handling argument used.
    elements
        Per-level dict mapping level number to a dataframe. Each dataframe has
        one row per distinct level-``n`` cell with columns ``id``, ``mean_child``,
        ``mean_parent``, ``sv``, ``sv_per_df``.
    wide_table
        Working table with one row per finest-level observation (after NA drop)
        and columns ``value_level_1`` ... ``value_level_(k+1)``. Carries forward
        the original ``id_*`` columns for tabular input.
    level_rasters
        Raster-only. Dict of aggregated rasters keyed ``level_1`` ... ``level_k``,
        each in the input's raster type. ``None`` for tabular input.
    sve
        Raster-only, optional. Multi-band raster of squared differences mapped
        back to the finest-level grid (one band per level), returned only when
        ``return_sve=True`` was passed to :func:`scale_variance_raster`.
    """

    components: pd.DataFrame
    total_ss: float
    total_df: int
    grand_mean: float
    n_levels: int
    agg_fun: str
    na_handling: str
    elements: dict[int, pd.DataFrame]
    wide_table: pd.DataFrame
    level_rasters: dict[str, Any] | None = None
    sve: Any | None = None

    def __repr__(self) -> str:
        return (
            f"ScaleVarianceResult(n_levels={self.n_levels}, "
            f"total_ss={self.total_ss:.6g}, total_df={self.total_df}, "
            f"grand_mean={self.grand_mean:.6g}, agg_fun={self.agg_fun!r})"
        )

    def _repr_html_(self) -> str:
        header = (
            f"<p><b>ScaleVarianceResult</b> — "
            f"n_levels={self.n_levels}, "
            f"total_ss={self.total_ss:.6g}, "
            f"total_df={self.total_df}, "
            f"grand_mean={self.grand_mean:.6g}, "
            f"agg_fun={self.agg_fun!r}</p>"
        )
        body = self.components.to_html(index=False, float_format=lambda x: f"{x:.6g}")
        return header + (body or "")
