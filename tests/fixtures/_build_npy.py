"""Build derived ``.npy`` artifacts from source-of-truth fixture rasters.

The Pyodide runtime that powers the ``scalevar.io`` playground cannot ship
``rasterio`` (it requires GDAL). The playground therefore loads the MT1972
Figure 3 raster from a plain ``numpy`` ``.npy`` file. This script reads the
canonical ``input.tif`` via ``rasterio`` (available in CI / dev environments)
and writes ``raster.npy`` alongside it.

Re-run with:

    python tests/fixtures/_build_npy.py

The ``.tif`` remains the source of truth for parity tests; ``raster.npy`` is
a derived artifact and is regenerated deterministically from it.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio

FIXTURES_DIR = Path(__file__).resolve().parent


def build_npy(fixture_dir: Path) -> Path:
    tif_path = fixture_dir / "input.tif"
    npy_path = fixture_dir / "raster.npy"
    with rasterio.open(tif_path) as src:
        if src.count != 1:
            raise ValueError(f"{tif_path} has {src.count} bands; expected 1")
        array = src.read(1)
    np.save(npy_path, array)
    return npy_path


def main() -> None:
    targets = [FIXTURES_DIR / "fixture_mt1972_fig3"]
    for fixture in targets:
        out = build_npy(fixture)
        arr = np.load(out)
        print(f"wrote {out.relative_to(FIXTURES_DIR.parent.parent)} "
              f"shape={arr.shape} dtype={arr.dtype}")


if __name__ == "__main__":
    main()
