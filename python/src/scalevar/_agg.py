"""Aggregation-function resolution shared by the tabular and raster paths.

String-name agg functions mirror the set supported by ``terra::aggregate`` in
the R package (see ``docs/api-design.md``). Callables are accepted as-is;
we pass them a 1-D numpy array and expect a scalar back.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray


def _nanmodal(a: NDArray[np.float64]) -> float:
    """Most-frequent non-NA value. Ties broken by smallest value (matches
    the terra::modal default). Returns NaN on an all-NaN or empty input."""
    mask = ~np.isnan(a)
    if not mask.any():
        return float("nan")
    values, counts = np.unique(a[mask], return_counts=True)
    top = counts.max()
    return float(values[counts == top].min())


_AGG_FUNCS: dict[str, Callable[[NDArray[np.float64]], float]] = {
    "mean": lambda a: float(np.nanmean(a)) if np.any(~np.isnan(a)) else float("nan"),
    "sum": lambda a: float(np.nansum(a)) if np.any(~np.isnan(a)) else float("nan"),
    "median": lambda a: float(np.nanmedian(a)) if np.any(~np.isnan(a)) else float("nan"),
    "modal": _nanmodal,
    "min": lambda a: float(np.nanmin(a)) if np.any(~np.isnan(a)) else float("nan"),
    "max": lambda a: float(np.nanmax(a)) if np.any(~np.isnan(a)) else float("nan"),
    "sd": lambda a: float(np.nanstd(a, ddof=1)) if np.sum(~np.isnan(a)) > 1 else float("nan"),
    "var": lambda a: float(np.nanvar(a, ddof=1)) if np.sum(~np.isnan(a)) > 1 else float("nan"),
}

SUPPORTED_AGG_NAMES: tuple[str, ...] = tuple(sorted(_AGG_FUNCS))


def resolve_agg_fun(
    agg_fun: str | Callable[[NDArray[np.float64]], float],
) -> tuple[Callable[[NDArray[np.float64]], float], str]:
    """Return (callable, canonical_name) for an agg_fun argument.

    Accepts a string from :data:`SUPPORTED_AGG_NAMES` or an arbitrary callable
    that takes a 1-D numpy array and returns a scalar.
    """
    if callable(agg_fun):
        name = getattr(agg_fun, "__name__", "custom")
        return agg_fun, name
    if isinstance(agg_fun, str):
        if agg_fun not in _AGG_FUNCS:
            raise ValueError(
                f"Unsupported agg_fun {agg_fun!r}. "
                f"Supported strings: {list(SUPPORTED_AGG_NAMES)}. "
                "You may also pass a callable."
            )
        return _AGG_FUNCS[agg_fun], agg_fun
    raise TypeError(f"agg_fun must be a str or callable, got {type(agg_fun).__name__}")
