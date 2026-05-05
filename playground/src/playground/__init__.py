"""Pure-function helpers for the scalevar marimo playground.

The marimo notebook (``playground/notebooks/mt1972_explorable.py``) drives
the reactive UI; this package holds the testable pure functions for
permalink serialization, code-snippet generation, and paper-language
interpretation.
"""

from .interpret import CAVEAT_COLLAPSING_AGGS, CAVEAT_MODAL, interpret_result
from .snippet import FIXTURE_LITERAL, generate_code_snippet, permalink, wheel_url
from .state import (
    DEFAULT_STATE,
    PRESETS,
    SUPPORTED_AGG_FUNS,
    SUPPORTED_BASE_FACTORS,
    State,
    deserialize_state,
    serialize_state,
)

__all__ = [
    "CAVEAT_COLLAPSING_AGGS",
    "CAVEAT_MODAL",
    "DEFAULT_STATE",
    "FIXTURE_LITERAL",
    "PRESETS",
    "SUPPORTED_AGG_FUNS",
    "SUPPORTED_BASE_FACTORS",
    "State",
    "deserialize_state",
    "generate_code_snippet",
    "interpret_result",
    "permalink",
    "serialize_state",
    "wheel_url",
]
