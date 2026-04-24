"""Shared test fixtures.

All hand-derived expected values live in ``tests/fixtures/`` at the repo
root; per-package unit tests load them from there so Python and R assert
against the same oracle.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"


def load_fixture(name: str) -> dict:
    """Return a loaded fixture bundle: ``meta``, ``input`` (frame or path),
    ``expected_components``, ``expected_totals``, ``expected_elements``."""
    fdir = FIXTURES_DIR / name
    meta = json.loads((fdir / "meta.json").read_text())
    bundle: dict = {"dir": fdir, "meta": meta}
    if meta["kind"] == "tabular":
        bundle["input"] = pd.read_csv(fdir / "input.csv")
    elif meta["kind"] == "raster":
        bundle["input_path"] = fdir / "input.tif"
    else:
        raise ValueError(f"Unknown fixture kind: {meta['kind']!r}")
    bundle["expected_components"] = pd.read_csv(fdir / "expected_components.csv")
    bundle["expected_totals"] = json.loads((fdir / "expected_totals.json").read_text())
    elements: dict[int, pd.DataFrame] = {}
    for p in sorted((fdir / "expected_elements").glob("level_*.csv")):
        lvl = int(p.stem.split("_")[1])
        elements[lvl] = pd.read_csv(p)
    bundle["expected_elements"] = elements
    return bundle


@pytest.fixture
def mt1972_fig3() -> dict:
    return load_fixture("fixture_mt1972_fig3")


@pytest.fixture
def irregular_admin() -> dict:
    return load_fixture("fixture_irregular_admin")
