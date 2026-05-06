"""URL-fragment serialization for the playground's reactive state.

The deployed playground encodes its current parameter set into the URL hash
fragment so visitors can share permalinks. Examples:

    #bf=2&af=mean&v=0.1.0&preset=classic
    #bf=4&af=median&v=0.1.0

`serialize_state` builds these strings; `deserialize_state` is a strict
validator. The reactive session must NEVER receive an unvalidated fragment
value — any malformed, out-of-range, or version-incompatible input returns
defaults plus a banner message that the UI displays instead.

URL keys are short (``bf``, ``af``) for compactness; the *Python snippet*
generated for paste-into-thesis always uses the library API names
(``base_level_factor``, ``agg_fun``). This module is the only translation
surface between the two vocabularies.
"""

from __future__ import annotations

from typing import TypedDict
from urllib.parse import parse_qsl, urlencode

SUPPORTED_BASE_FACTORS: tuple[int, ...] = (2, 3, 4)
SUPPORTED_AGG_FUNS: tuple[str, ...] = (
    "mean",
    "sum",
    "median",
    "modal",
    "min",
    "max",
    "sd",
    "var",
)

PRESETS: dict[str, dict[str, int | str]] = {
    "classic": {"base_level_factor": 2, "agg_fun": "mean"},
    "coarse-step": {"base_level_factor": 4, "agg_fun": "mean"},
}

DEFAULT_STATE: dict[str, int | str | None] = {
    "base_level_factor": 2,
    "agg_fun": "mean",
    "scalevar_version": "0.1.0",
    "preset": "classic",
}

MAX_FRAGMENT_BYTES = 4096


class State(TypedDict):
    base_level_factor: int
    agg_fun: str
    scalevar_version: str
    preset: str | None


def serialize_state(
    base_level_factor: int,
    agg_fun: str,
    scalevar_version: str,
    preset: str | None = None,
) -> str:
    """Encode state as a URL hash fragment (without the leading ``#``).

    Raises ``ValueError`` for inputs outside the allowlists — the playground
    should never produce an un-roundtrippable permalink.
    """
    if base_level_factor not in SUPPORTED_BASE_FACTORS:
        raise ValueError(f"base_level_factor must be in {SUPPORTED_BASE_FACTORS}")
    if agg_fun not in SUPPORTED_AGG_FUNS:
        raise ValueError(f"agg_fun must be in {SUPPORTED_AGG_FUNS}")
    if "dev" in scalevar_version:
        raise ValueError("dev-tagged versions are not deployable")
    if preset is not None and preset not in PRESETS:
        raise ValueError(f"unknown preset {preset!r}")

    params: list[tuple[str, str]] = [
        ("bf", str(base_level_factor)),
        ("af", agg_fun),
        ("v", scalevar_version),
    ]
    if preset is not None:
        params.append(("preset", preset))
    return urlencode(params)


def deserialize_state(
    fragment: str,
    deployed_version: str = "0.1.0",
) -> tuple[State, str | None]:
    """Parse a URL hash fragment into a validated state dict.

    Returns ``(state, banner)`` where ``banner`` is ``None`` on success or a
    user-visible error message on failure. On failure ``state`` is the
    defaults — the caller never has to deal with partially-valid input.
    """
    fragment = fragment.lstrip("#")
    defaults = _defaults()

    if len(fragment.encode("utf-8")) > MAX_FRAGMENT_BYTES:
        return defaults, (
            f"Permalink fragment exceeds {MAX_FRAGMENT_BYTES} bytes; "
            "loading defaults."
        )

    if not fragment:
        return defaults, None

    try:
        items = parse_qsl(fragment, strict_parsing=True, keep_blank_values=False)
    except ValueError:
        return defaults, "Permalink fragment is malformed; loading defaults."

    parsed: dict[str, str] = {}
    allowed_keys = {"bf", "af", "v", "preset"}
    for key, value in items:
        if key not in allowed_keys:
            return defaults, (
                f"Permalink fragment contains unknown key {key!r}; "
                "loading defaults."
            )
        if key in parsed:
            return defaults, (
                f"Permalink fragment has duplicate key {key!r}; "
                "loading defaults."
            )
        parsed[key] = value

    for required in ("bf", "af", "v"):
        if required not in parsed:
            return defaults, (
                f"Permalink fragment is missing required key {required!r}; "
                "loading defaults."
            )

    version = parsed["v"]
    if "dev" in version:
        return defaults, (
            f"This permalink references an unreleased dev build ({version}). "
            "Dev builds are not deployed; loading defaults."
        )

    if not _versions_compatible(version, deployed_version):
        return defaults, (
            f"This permalink was generated against scalevar {version}. "
            f"The deployed playground runs scalevar {deployed_version}; "
            "the result here may not match the original. To reproduce "
            f"locally, install the wheel for scalevar {version} from its "
            "GitHub Release and paste the snippet from the original "
            "Methods Appendix."
        )

    try:
        bf = int(parsed["bf"])
    except ValueError:
        return defaults, (
            f"base_level_factor must be one of {SUPPORTED_BASE_FACTORS}; "
            "loading defaults."
        )
    if bf not in SUPPORTED_BASE_FACTORS:
        return defaults, (
            f"base_level_factor must be one of {SUPPORTED_BASE_FACTORS}; "
            "loading defaults."
        )

    af = parsed["af"]
    if af not in SUPPORTED_AGG_FUNS:
        return defaults, (
            f"agg_fun must be one of {SUPPORTED_AGG_FUNS}; loading defaults."
        )

    preset = parsed.get("preset")
    if preset is not None and preset not in PRESETS:
        return defaults, (
            f"unknown preset {preset!r}; loading defaults."
        )

    state: State = {
        "base_level_factor": bf,
        "agg_fun": af,
        "scalevar_version": version,
        "preset": preset,
    }
    return state, None


def _defaults() -> State:
    return {
        "base_level_factor": 2,
        "agg_fun": "mean",
        "scalevar_version": "0.1.0",
        "preset": "classic",
    }


def _versions_compatible(permalink_version: str, deployed_version: str) -> bool:
    """Major.minor must match exactly; patch differences are silently OK."""
    pa = permalink_version.split(".")
    pb = deployed_version.split(".")
    if len(pa) < 2 or len(pb) < 2:
        return False
    return pa[0] == pb[0] and pa[1] == pb[1]
