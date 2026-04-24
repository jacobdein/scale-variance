"""Exception hierarchy for scalevar.

Error messages are part of the public API contract (see ``docs/api-design.md``
Error Contract section) and must stay identical to the R sibling package.
"""

from __future__ import annotations


class ScalevarError(ValueError):
    """Base class for all scalevar user-facing errors.

    Inherits from :class:`ValueError` so that callers can catch
    ``ValueError`` if they want a single guard for input problems without
    importing scalevar's exception hierarchy.
    """


class MissingColumnError(ScalevarError):
    """Raised when a named column is not present on the input dataframe."""


class InsufficientLevelsError(ScalevarError):
    """Raised when fewer than two id columns are supplied.

    A single-level "hierarchy" is just :func:`numpy.var` — there is no scale
    to decompose across.
    """


class NonNumericValueError(ScalevarError):
    """Raised when the value column is not numeric."""


class DuplicateIdColsError(ScalevarError):
    """Raised when ``id_cols`` contains the same column name twice."""


class UnprojectedCRSError(ScalevarError):
    """Raised when a geographic (unprojected) CRS is passed to a function
    that needs metric coordinates to report cell sizes meaningfully.

    Applies to :func:`scalevar.spatial.create_hbins` and to
    :func:`scalevar.raster.scale_variance_raster` for inputs that carry a
    geographic CRS. Rasters with no CRS at all are accepted with a warning
    (see ``docs/api-design.md``).
    """


class MultiLayerRasterError(ScalevarError):
    """Raised when a multi-band / multi-layer raster is passed.

    Callers should select a single band explicitly before calling
    :func:`scalevar.raster.scale_variance_raster`.
    """
