"""Paper-language interpretation of a ``ScaleVarianceResult``.

The playground renders a one-paragraph plain-English description of the
current decomposition, designed so a grad student can paste it into the
Methods chapter of a thesis with light editing.

Two distinct caveats are emitted as named module constants so the test
suite can assert their presence by substring rather than reproducing the
literal copy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .state import State

if TYPE_CHECKING:
    from scalevar import ScaleVarianceResult

CAVEAT_MODAL = (
    "Modal aggregation breaks ties deterministically by smallest non-NA "
    "value (matching `terra::modal` and `scalevar._agg._nanmodal`). On "
    "small fixtures with many ties, the result is well-defined but reflects "
    "this convention rather than meaningful pattern. Pedagogically, prefer "
    "mean / median for first-encounter intuition."
)

CAVEAT_COLLAPSING_AGGS = (
    "This aggregation collapses parent variance rather than averaging it; "
    "the resulting decomposition is mathematically valid but no longer "
    "matches the paper's intuition. Useful for advanced exploration; "
    "misleading as a first encounter."
)

_COLLAPSING_AGGS = frozenset({"min", "max", "sd", "var"})


def caveat_for(agg_fun: str) -> str | None:
    if agg_fun == "modal":
        return CAVEAT_MODAL
    if agg_fun in _COLLAPSING_AGGS:
        return CAVEAT_COLLAPSING_AGGS
    return None


def interpret_result(result: ScaleVarianceResult, state: State) -> str:
    """Render a paper-language paragraph for the given result + state."""
    bf = state["base_level_factor"]
    af = state["agg_fun"]

    comp = result.components
    n_levels = len(comp)
    shares = list(comp["ss_share"])
    dfs = list(comp["df"])

    pct = lambda s: f"{round(s * 100)}%"  # noqa: E731

    # Level 1 (finest) is always present in a non-degenerate decomposition.
    finest_share = shares[0]
    next_finest_share = shares[1] if n_levels > 1 else 0.0

    # Pick the dominant non-synthetic level (excludes the synthetic top
    # level, which is the last row and has df==0 by construction).
    non_synthetic_idx = [i for i in range(n_levels) if dfs[i] > 0]
    if not non_synthetic_idx:
        coarsest = (
            "All non-degenerate levels have zero degrees of freedom — no "
            "scale carries a meaningful share at this configuration."
        )
    else:
        dominant_i = max(non_synthetic_idx, key=lambda i: shares[i])
        if dominant_i == 0 and shares[0] > 0.5:
            coarsest = (
                "Most variance lives at the finest grain — at this scale "
                "your data is dominated by local detail."
            )
        elif dominant_i == non_synthetic_idx[-1]:
            coarsest = (
                "Most variance is at the coarsest available scale — the "
                "data may be more variable at scales beyond what this "
                "view captures."
            )
        else:
            scale_val = comp["scale"][dominant_i]
            scale_str = (
                f"around {int(scale_val)} pixels"
                if scale_val == scale_val  # NaN-safe
                else f"level {dominant_i + 1}"
            )
            coarsest = (
                f"The dominant scale is level {dominant_i + 1} — the data "
                f"has a characteristic patch size {scale_str}."
            )

    paragraph = (
        f"At base_level_factor={bf} with agg_fun={af!r}, the decomposition "
        f"partitions the raster's total variance into {n_levels} levels. "
        f"The finest level holds {pct(finest_share)} of the variation; "
        f"the next-finest holds {pct(next_finest_share)}. {coarsest}"
    )

    caveat = caveat_for(af)
    if caveat:
        paragraph = f"{paragraph}\n\n{caveat}"

    return paragraph
