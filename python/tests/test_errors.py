"""Error-class and message-text tests.

Error messages are part of the v0.1 public contract (see
``docs/api-design.md``) — they must stay character-for-character identical
to the R sibling package. A later parity fixture will cross-check.
"""

from __future__ import annotations

import pandas as pd
import pytest

from scalevar import (
    DuplicateIdColsError,
    InsufficientLevelsError,
    MissingColumnError,
    MultiLayerRasterError,
    NonNumericValueError,
    ScalevarError,
    UnprojectedCRSError,
)


def test_error_hierarchy():
    # Every scalevar error derives from ValueError for easy catching.
    for cls in (
        MissingColumnError,
        InsufficientLevelsError,
        NonNumericValueError,
        DuplicateIdColsError,
        UnprojectedCRSError,
        MultiLayerRasterError,
    ):
        assert issubclass(cls, ScalevarError)
        assert issubclass(cls, ValueError)


def test_error_messages_are_identifiable():
    # Ensure each error type emits a distinct, matchable string. The exact
    # text is not frozen here — see the parity fixture — but the keywords
    # must remain discoverable.
    from scalevar import scale_variance

    df = pd.DataFrame({"id": [1, 2], "value": [1.0, 2.0]})
    try:
        scale_variance(df, value="value", id_cols=["id"])
    except InsufficientLevelsError as e:
        assert "at least two levels" in str(e)
    else:
        pytest.fail("expected InsufficientLevelsError")


def test_unprojected_crs_message_structure():
    # The exact template is in scalevar.raster._UNPROJECTED_CRS_MESSAGE and
    # shared with create_hbins in scalevar.spatial. We only check the
    # anchor phrases here; parity fixtures assert the full text across R.
    from scalevar.raster import _UNPROJECTED_CRS_MESSAGE

    msg = _UNPROJECTED_CRS_MESSAGE.format(crs="EPSG:4326 (WGS 84)")
    assert "unprojected or geographic CRS detected" in msg
    assert "projected CRS with linear units" in msg
    assert "EPSG:27700" in msg
    assert "EPSG:4326" in msg
