"""Methods-Appendix code snippet generator.

Emits a self-contained Python script the user can paste into a notebook or
thesis. The snippet:

- Installs scalevar via the wheel URL of its GitHub Release (``scalevar`` is
  not on PyPI in v0.1).
- Inlines the 16×16 MT1972 Figure 3 fixture as a numpy literal so the user
  does not need access to ``tests/fixtures/...``.
- Imports only from ``scalevar.__all__`` so a future API rename can't make
  the snippet silently wrong.
- Uses the library API names (``base_level_factor``, ``agg_fun``), not the
  short URL keys.
"""

from __future__ import annotations

from .state import State

GITHUB_REPO = "jacobdein/scale-variance"
PLAYGROUND_BASE_URL = "https://jacobdein.github.io/scale-variance/playground/"

# 16x16 MT1972 Figure 3 fixture (verbatim copy of
# tests/fixtures/fixture_mt1972_fig3/raster.npy). Inlined here so the
# generated snippet stands alone — the user does not need this repo's
# fixture path.
FIXTURE_LITERAL: tuple[tuple[int, ...], ...] = (
    (2, 5, 2, 5, 2, 5, 2, 5, 5, 8, 5, 8, 5, 8, 5, 8),
    (5, 2, 5, 2, 5, 2, 5, 2, 8, 5, 8, 5, 8, 5, 8, 5),
    (2, 5, 2, 5, 2, 5, 2, 5, 5, 8, 5, 8, 5, 8, 5, 8),
    (5, 2, 5, 2, 5, 2, 5, 2, 8, 5, 8, 5, 8, 5, 8, 5),
    (2, 5, 2, 5, 2, 5, 2, 5, 5, 8, 5, 8, 5, 8, 5, 8),
    (5, 2, 5, 2, 5, 2, 5, 2, 8, 5, 8, 5, 8, 5, 8, 5),
    (2, 5, 2, 5, 2, 5, 2, 5, 5, 8, 5, 8, 5, 8, 5, 8),
    (5, 2, 5, 2, 5, 2, 5, 2, 8, 5, 8, 5, 8, 5, 8, 5),
    (5, 8, 5, 8, 5, 8, 5, 8, 2, 5, 2, 5, 2, 5, 2, 5),
    (8, 5, 8, 5, 8, 5, 8, 5, 5, 2, 5, 2, 5, 2, 5, 2),
    (5, 8, 5, 8, 5, 8, 5, 8, 2, 5, 2, 5, 2, 5, 2, 5),
    (8, 5, 8, 5, 8, 5, 8, 5, 5, 2, 5, 2, 5, 2, 5, 2),
    (5, 8, 5, 8, 5, 8, 5, 8, 2, 5, 2, 5, 2, 5, 2, 5),
    (8, 5, 8, 5, 8, 5, 8, 5, 5, 2, 5, 2, 5, 2, 5, 2),
    (5, 8, 5, 8, 5, 8, 5, 8, 2, 5, 2, 5, 2, 5, 2, 5),
    (8, 5, 8, 5, 8, 5, 8, 5, 5, 2, 5, 2, 5, 2, 5, 2),
)


def wheel_url(version: str) -> str:
    return (
        f"https://github.com/{GITHUB_REPO}/releases/download/"
        f"v{version}/scalevar-{version}-py3-none-any.whl"
    )


def permalink(state: State) -> str:
    from .state import serialize_state

    return PLAYGROUND_BASE_URL + "#" + serialize_state(
        base_level_factor=state["base_level_factor"],
        agg_fun=state["agg_fun"],
        scalevar_version=state["scalevar_version"],
        preset=state["preset"],
    )


def _format_fixture() -> str:
    rows = []
    for row in FIXTURE_LITERAL:
        rows.append("    [" + ", ".join(str(v) for v in row) + "],")
    return "\n".join(rows)


def generate_code_snippet(state: State) -> str:
    """Emit a paste-ready Python script for the given playground state."""
    version = state["scalevar_version"]
    bf = state["base_level_factor"]
    af = state["agg_fun"]
    url = wheel_url(version)
    perma = permalink(state)
    fixture_block = _format_fixture()

    return f"""\
# scalevar {version} — Methods Appendix from scalevar.io/playground
# Permalink: {perma}
# Reproduces the Moellering & Tobler (1972) Figure 3 decomposition.

# scalevar is not on PyPI in v0.1; install the wheel from the GitHub Release.
# pip install "scalevar @ {url}"

import numpy as np
from scalevar import scale_variance_raster

# MT1972 Figure 3 raster, inlined (16x16 = 256 ints).
# Source: tests/fixtures/fixture_mt1972_fig3/input.tif in the scale-variance repo.
raster = np.array([
{fixture_block}
], dtype=np.float64)

result = scale_variance_raster(raster, base_level_factor={bf}, agg_fun={af!r})
print(f"TSS = {{result.total_ss:.0f}}, TDF = {{result.total_df}}")
print(result.components[["level", "scale", "ss_share"]])
"""
