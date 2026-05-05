"""Tests for the playground's pure-function helpers.

Verifies the contract that the reactive marimo notebook depends on:
state round-trips losslessly, malformed permalinks surface a banner instead
of poisoning the compute path, generated snippets actually run and produce
the same numbers the playground would show, and the paper-language
interpretation covers every documented branch.
"""

from __future__ import annotations

import itertools
import re
import subprocess
import sys
import warnings

import numpy as np
import pytest

import scalevar
from playground import (
    CAVEAT_COLLAPSING_AGGS,
    CAVEAT_MODAL,
    FIXTURE_LITERAL,
    PRESETS,
    SUPPORTED_AGG_FUNS,
    SUPPORTED_BASE_FACTORS,
    deserialize_state,
    generate_code_snippet,
    interpret_result,
    permalink,
    serialize_state,
    wheel_url,
)


DEPLOYED_VERSION = "0.1.0"


# ---------------------------------------------------------------------------
# state.py — round-trip and negative parser
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bf,af,version,preset",
    list(
        itertools.product(
            SUPPORTED_BASE_FACTORS,
            SUPPORTED_AGG_FUNS,
            ["0.1.0", "0.1.5", "0.1.99"],  # patch-compatible with deployed 0.1.0
            [None, *PRESETS.keys()],
        )
    ),
)
def test_state_round_trip(bf, af, version, preset):
    fragment = serialize_state(bf, af, version, preset)
    state, banner = deserialize_state(fragment, deployed_version=DEPLOYED_VERSION)
    assert banner is None, f"unexpected banner: {banner}"
    assert state["base_level_factor"] == bf
    assert state["agg_fun"] == af
    assert state["scalevar_version"] == version
    assert state["preset"] == preset


def test_serialize_rejects_unknown_inputs():
    with pytest.raises(ValueError):
        serialize_state(5, "mean", "0.1.0")
    with pytest.raises(ValueError):
        serialize_state(2, "geomean", "0.1.0")
    with pytest.raises(ValueError):
        serialize_state(2, "mean", "0.1.0.dev0")
    with pytest.raises(ValueError):
        serialize_state(2, "mean", "0.1.0", preset="not-a-preset")


@pytest.mark.parametrize(
    "fragment,banner_substring",
    [
        ("not-a-fragment", "malformed"),
        ("bf=2&af=mean", "missing required key 'v'"),
        ("bf=99&af=mean&v=0.1.0", "base_level_factor must"),
        ("bf=2&af=geomean&v=0.1.0", "agg_fun must"),
        ("bf=2&af=mean&v=0.1.0&unknown=x", "unknown key 'unknown'"),
        ("bf=2&af=mean&v=0.1.0&bf=3", "duplicate key 'bf'"),
        ("bf=2&af=mean&v=0.1.0.dev0", "unreleased dev build"),
        ("bf=2&af=mean&v=0.2.0", "may not match"),  # minor mismatch
        ("bf=2&af=mean&v=1.0.0", "may not match"),  # major mismatch
        ("bf=2&af=mean&v=0.1.0&preset=fancy", "unknown preset"),
        ("bf=2&af=mean&v=0.1.0&padding=" + "x" * 5000, "exceeds 4096 bytes"),
    ],
)
def test_negative_parser_surfaces_banner_and_defaults(fragment, banner_substring):
    state, banner = deserialize_state(fragment, deployed_version=DEPLOYED_VERSION)
    assert banner is not None, "expected a banner for malformed input"
    assert banner_substring in banner, (
        f"banner {banner!r} did not contain {banner_substring!r}"
    )
    # On any failure we hand back the defaults — never partial state.
    assert state["base_level_factor"] == 2
    assert state["agg_fun"] == "mean"
    assert state["scalevar_version"] == "0.1.0"


def test_empty_fragment_loads_defaults_silently():
    state, banner = deserialize_state("", deployed_version=DEPLOYED_VERSION)
    assert banner is None
    assert state["base_level_factor"] == 2
    assert state["agg_fun"] == "mean"


def test_leading_hash_is_tolerated():
    state, banner = deserialize_state(
        "#bf=3&af=median&v=0.1.0", deployed_version=DEPLOYED_VERSION
    )
    assert banner is None
    assert state["base_level_factor"] == 3
    assert state["agg_fun"] == "median"


# ---------------------------------------------------------------------------
# snippet.py — wheel URL, no PyPI, fixture inlined, runs in clean env
# ---------------------------------------------------------------------------


def _state_for(bf=2, af="mean", version="0.1.0", preset="classic"):
    return {
        "base_level_factor": bf,
        "agg_fun": af,
        "scalevar_version": version,
        "preset": preset,
    }


def test_snippet_does_not_promise_pypi():
    snip = generate_code_snippet(_state_for())
    assert "pip install scalevar==" not in snip
    assert 'pip install "scalevar @ ' in snip
    assert wheel_url("0.1.0") in snip


def test_snippet_uses_library_vocabulary_not_url_shorthand():
    snip = generate_code_snippet(_state_for(bf=3, af="median"))
    assert "base_level_factor=3" in snip
    assert 'agg_fun=' in snip and "'median'" in snip
    # `bf=` and `af=` are URL keys; they must not leak into the snippet
    # except inside the permalink comment.
    non_permalink = "\n".join(
        ln for ln in snip.splitlines() if not ln.startswith("# Permalink:")
    )
    assert "bf=" not in non_permalink
    assert re.search(r"\baf=", non_permalink) is None


def test_snippet_imports_only_from_public_api():
    snip = generate_code_snippet(_state_for())
    imports = [
        m.group(1)
        for m in re.finditer(r"from scalevar import ([\w, ]+)", snip)
    ]
    for chunk in imports:
        for sym in (s.strip() for s in chunk.split(",")):
            assert sym in scalevar.__all__, f"{sym} not in scalevar.__all__"


def test_snippet_inlines_the_fixture():
    snip = generate_code_snippet(_state_for())
    # The 16x16 fixture must be embedded as a literal — no fixture path
    # references that the user wouldn't have on their machine. The
    # provenance comment is allowed to mention the source path; runnable
    # code must not.
    runnable = "\n".join(
        ln for ln in snip.splitlines() if not ln.lstrip().startswith("#")
    )
    assert "tests/fixtures" not in runnable
    # The first row of the literal must appear verbatim.
    first_row = "[" + ", ".join(str(v) for v in FIXTURE_LITERAL[0]) + "]"
    assert first_row in snip


def test_snippet_runs_in_clean_env_and_matches_paper(tmp_path):
    """Write the snippet to a tempfile, run it with the installed scalevar
    (no internet, no wheel install), and assert TSS=1152, TDF=255."""
    snip = generate_code_snippet(_state_for())
    # Strip the wheel-install comment (we can't reach the GitHub Release in
    # offline tests; the working scalevar is already importable here).
    runnable = "\n".join(
        ln for ln in snip.splitlines() if not ln.startswith("# pip install")
    )
    script = tmp_path / "snippet.py"
    script.write_text(runnable)
    proc = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "TSS = 1152" in proc.stdout
    assert "TDF = 255" in proc.stdout


def test_permalink_round_trips_through_deserialize():
    state = _state_for(bf=4, af="median", preset="agg-contrast")
    url = permalink(state)
    fragment = url.split("#", 1)[1]
    parsed, banner = deserialize_state(fragment, deployed_version=DEPLOYED_VERSION)
    assert banner is None
    assert parsed == state


# ---------------------------------------------------------------------------
# interpret.py — every branch + caveats + numeric rounding
# ---------------------------------------------------------------------------


def _mt1972_raster() -> np.ndarray:
    return np.array(FIXTURE_LITERAL, dtype=float)


def _result_for(bf, af, raster=None):
    if raster is None:
        raster = _mt1972_raster()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return scalevar.scale_variance_raster(
            raster, base_level_factor=bf, agg_fun=af
        )


@pytest.mark.parametrize("preset_name,preset", PRESETS.items())
def test_interpret_returns_non_empty_for_every_preset(preset_name, preset):
    bf = preset["base_level_factor"]
    af = preset["agg_fun"]
    state = _state_for(bf=bf, af=af, preset=preset_name)
    text = interpret_result(_result_for(bf, af), state)
    assert text and len(text) > 50
    assert f"base_level_factor={bf}" in text
    assert f"agg_fun={af!r}" in text


def test_interpret_includes_modal_caveat():
    # interpret_result picks the caveat from state['agg_fun']; the underlying
    # scalevar call uses 'mean' because non-mean aggregations on the MT1972
    # fixture violate the decomposition identity and scalevar rightly raises.
    # The playground catches that error at the call site (see failure-mode
    # table); here we are testing the interpretation layer in isolation.
    state = _state_for(af="modal", preset=None)
    text = interpret_result(_result_for(2, "mean"), state)
    assert CAVEAT_MODAL[:40] in text


@pytest.mark.parametrize("af", ["min", "max", "sd", "var"])
def test_interpret_includes_collapsing_caveat(af):
    state = _state_for(af=af, preset=None)
    text = interpret_result(_result_for(2, "mean"), state)
    assert CAVEAT_COLLAPSING_AGGS[:40] in text


def test_interpret_no_caveat_for_safe_agg_funs():
    for af in ("mean", "sum", "median"):
        state = _state_for(af=af)
        text = interpret_result(_result_for(2, "mean"), state)
        assert CAVEAT_MODAL[:40] not in text
        assert CAVEAT_COLLAPSING_AGGS[:40] not in text


def test_interpret_finest_dominant_branch():
    """Random noise: variance concentrates at the finest scale."""
    rng = np.random.default_rng(0)
    raster = rng.normal(size=(16, 16))
    state = _state_for()
    text = interpret_result(_result_for(2, "mean", raster), state)
    assert "dominated by local detail" in text


def test_interpret_coarsest_dominant_branch():
    """Smooth gradient: variance concentrates at the coarsest scale."""
    grad = np.tile(np.arange(16, dtype=float), (16, 1))
    state = _state_for()
    text = interpret_result(_result_for(2, "mean", grad), state)
    assert "coarsest available scale" in text


def test_interpret_middle_dominant_branch():
    """MT1972 fixture has 50/50 at finest+coarsest. Build a raster whose
    middle level dominates by repeating an 8x8 block (each 8x8 region is
    constant), so all variance lives at level 4 (scale 8) only — same
    distribution shape as the coarsest branch. To get a *middle*-dominant
    raster, repeat 4x4 blocks: variance is at level 3 (scale 4)."""
    block = np.array([[1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 1, 1]])
    # Lay out a 4x4 grid of 4x4 blocks, alternating values.
    tile = np.zeros((16, 16))
    for i in range(4):
        for j in range(4):
            tile[i * 4 : (i + 1) * 4, j * 4 : (j + 1) * 4] = (
                10 if (i + j) % 2 == 0 else 0
            )
    state = _state_for()
    text = interpret_result(_result_for(2, "mean", tile), state)
    assert "dominant scale is level" in text


def test_interpret_numeric_rounding_uses_percent_no_decimal():
    """A 0.473 share must render as '47%', not '0.473' or '47.3%'."""
    rng = np.random.default_rng(42)
    raster = rng.normal(size=(8, 8))
    result = _result_for(2, "mean", raster)
    finest = float(result.components["ss_share"][0])
    expected_pct = f"{round(finest * 100)}%"
    state = _state_for()
    text = interpret_result(result, state)
    assert expected_pct in text
    assert f"{finest:.3f}" not in text  # raw float must not appear
