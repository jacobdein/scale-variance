"""Render the README hero figure for ``scalevar``.

Re-run with::

    python python/docs/_static/build_hero.py

Loads the gold-standard Moellering & Tobler (1972) Figure 3 fixture from
``tests/fixtures/fixture_mt1972_fig3/`` (input raster + paper-validated
expected components) and emits a single SVG with three panels:

    [16x16 raster of {2, 5, 8}]  -->  [lollipop of ss_share by scale]

The figure is intentionally minimal — no gridlines, no legend frame, no chart
chrome — so it carries on small README thumbnails and PyPI rendering.

The raster grid and lollipop chart are drawn to the same axis height so the
"-->" reads as one operation: input on the left, output on the right.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "fixture_mt1972_fig3"
OUT_PATH = Path(__file__).resolve().parent / "scalevar_hero.svg"


# Three-tone grayscale ramp for {2, 5, 8}: low value -> light, high -> dark.
PALETTE = {
    2: "#ededed",
    5: "#9a9a9a",
    8: "#3a3a3a",
}
LOLLIPOP = "#222222"
ARROW = "#666666"
TEXT = "#222222"


def load_inputs() -> tuple[np.ndarray, pd.DataFrame]:
    with rasterio.open(FIXTURE_DIR / "input.tif") as src:
        raster = src.read(1).astype(int)
    components = pd.read_csv(FIXTURE_DIR / "expected_components.csv")
    return raster, components


def render(raster: np.ndarray, components: pd.DataFrame, out_path: Path) -> None:
    plt.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": False,
            "axes.spines.bottom": False,
        }
    )

    fig = plt.figure(figsize=(9.5, 3.6))
    gs = fig.add_gridspec(
        nrows=1,
        ncols=3,
        width_ratios=[1.05, 0.18, 1.6],
        wspace=0.05,
    )

    # ---- left: raster -----------------------------------------------------
    ax_r = fig.add_subplot(gs[0, 0])
    nrow, ncol = raster.shape
    color_arr = np.zeros((nrow, ncol, 3))
    for value, hex_col in PALETTE.items():
        rgb = np.array(
            [int(hex_col[1:3], 16), int(hex_col[3:5], 16), int(hex_col[5:7], 16)]
        ) / 255.0
        color_arr[raster == value] = rgb
    ax_r.imshow(color_arr, interpolation="nearest", origin="upper")
    # Subtle hairline grid so individual cells are readable on both light
    # and dark grayscale tones.
    for k in range(nrow + 1):
        ax_r.axhline(k - 0.5, color="#444444", linewidth=0.4, alpha=0.18)
    for k in range(ncol + 1):
        ax_r.axvline(k - 0.5, color="#444444", linewidth=0.4, alpha=0.18)
    ax_r.set_xticks([])
    ax_r.set_yticks([])
    ax_r.set_xlim(-0.5, ncol - 0.5)
    ax_r.set_ylim(nrow - 0.5, -0.5)

    # ---- middle: arrow ----------------------------------------------------
    ax_a = fig.add_subplot(gs[0, 1])
    ax_a.set_xticks([])
    ax_a.set_yticks([])
    ax_a.set_xlim(0, 1)
    ax_a.set_ylim(0, 1)
    ax_a.annotate(
        "",
        xy=(0.92, 0.5),
        xytext=(0.08, 0.5),
        xycoords="axes fraction",
        arrowprops={
            "arrowstyle": "-|>",
            "color": ARROW,
            "lw": 1.6,
            "shrinkA": 0,
            "shrinkB": 0,
        },
    )
    ax_a.text(
        0.5,
        0.62,
        "scale_variance_raster",
        ha="center",
        va="bottom",
        fontsize=8.5,
        color=TEXT,
        family="monospace",
    )

    # ---- right: lollipop --------------------------------------------------
    ax_l = fig.add_subplot(gs[0, 2])
    levels = components["level"].to_numpy()
    scales = components["scale"].astype(int).to_numpy()
    shares = components["ss_share"].to_numpy()
    x = np.arange(len(levels))

    ax_l.vlines(x, 0, shares, color=LOLLIPOP, linewidth=1.5)
    ax_l.scatter(x, shares, s=70, color=LOLLIPOP, zorder=3)
    # Label only the non-zero peaks; keep the chart clean.
    for xi, yi in zip(x, shares, strict=True):
        if yi > 0:
            ax_l.text(
                xi,
                yi + 0.025,
                f"{yi * 100:.0f}%",
                ha="center",
                va="bottom",
                fontsize=10,
                color=TEXT,
            )
    ax_l.set_xticks(x)
    ax_l.set_xticklabels([f"{s}" for s in scales])
    ax_l.tick_params(axis="x", length=0, pad=4, colors=TEXT)
    ax_l.set_yticks([])
    ax_l.set_ylim(0, max(shares) * 1.35 if max(shares) > 0 else 1.0)
    ax_l.set_xlim(-0.6, len(x) - 0.4)
    ax_l.axhline(0, color="#999999", linewidth=0.6)
    ax_l.set_xlabel("scale (pixels)", fontsize=9, color=TEXT, labelpad=2)
    ax_l.text(
        -0.55,
        max(shares) * 1.30 if max(shares) > 0 else 1.0,
        "share of total variance",
        ha="left",
        va="top",
        fontsize=9,
        color="#666666",
    )

    fig.savefig(out_path, format="svg", bbox_inches="tight", transparent=True)
    plt.close(fig)


def main() -> None:
    raster, components = load_inputs()
    render(raster, components, OUT_PATH)
    print(f"Wrote {OUT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
