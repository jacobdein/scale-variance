"""scalevar — Moellering-Tobler scale-variance decomposition.

Implements the irregular-case formulation of Moellering & Tobler (1972),
*Geographical Variances*, Geographical Analysis 4(1), 34-50. See
``docs/theory.md`` in the repository for the derivation and ``docs/api-design.md``
for the stable v0.1 API contract shared with the R sibling package.

Public API:

- :func:`scale_variance` — tabular core. Decompose variance across a nested
  hierarchy encoded as id-per-level columns on a dataframe.
- :func:`scale_variance_raster` — raster entry point. Aggregates a raster by
  successive factors and decomposes its variance across the resulting scales.
- :class:`ScaleVarianceResult` — the structured result object returned by both.
- Spatial helpers :func:`create_hbins` and :func:`join_hbins` live in
  :mod:`scalevar.spatial` and require the optional ``[spatial]`` extra.
"""

from scalevar.errors import (
    DuplicateIdColsError,
    InsufficientLevelsError,
    MissingColumnError,
    MultiLayerRasterError,
    NonNumericValueError,
    ScalevarError,
    UnprojectedCRSError,
)
from scalevar.raster import scale_variance_raster
from scalevar.result import ScaleVarianceResult
from scalevar.tabular import scale_variance

__all__ = [
    "DuplicateIdColsError",
    "InsufficientLevelsError",
    "MissingColumnError",
    "MultiLayerRasterError",
    "NonNumericValueError",
    "ScaleVarianceResult",
    "ScalevarError",
    "UnprojectedCRSError",
    "scale_variance",
    "scale_variance_raster",
]

__version__ = "0.1.1"
