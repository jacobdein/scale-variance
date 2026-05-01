"""scalevar playground — MT1972 Figure 3 explorable.

Marimo notebook exported to WASM at scalevar.io/playground.
The fixture array is inlined so the WASM bundle does not have to ship
a side-channel data file. The inline literal matches
``tests/fixtures/fixture_mt1972_fig3/raster.npy`` (verified: TSS=1152, TDF=255).
"""

import marimo

__generated_with = "0.9.0"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _intro(mo):
    mo.md(
        r"""
        # Scale variance — Moellering & Tobler (1972), Figure 3

        Drag the sliders. Watch the lollipop reshape. The 16×16 raster is the
        same checkerboard-of-checkerboards used in the original 1972 paper.
        With `base_level_factor=2` and `agg_fun='mean'` the playground reproduces
        the paper's published totals (`TSS = 1152`, `TDF = 255`) exactly.
        """
    )
    return


@app.cell(hide_code=True)
def _imports():
    import warnings

    import matplotlib.pyplot as plt
    import numpy as np

    from scalevar import scale_variance_raster

    return np, plt, scale_variance_raster, warnings


@app.cell(hide_code=True)
def _fixture(np):
    # MT1972 Figure 3, 16x16, values {2, 5, 8}.
    # Inlined to keep the WASM bundle self-contained.
    raster = np.array(
        [
            [2, 5, 2, 5, 2, 5, 2, 5, 5, 8, 5, 8, 5, 8, 5, 8],
            [5, 2, 5, 2, 5, 2, 5, 2, 8, 5, 8, 5, 8, 5, 8, 5],
            [2, 5, 2, 5, 2, 5, 2, 5, 5, 8, 5, 8, 5, 8, 5, 8],
            [5, 2, 5, 2, 5, 2, 5, 2, 8, 5, 8, 5, 8, 5, 8, 5],
            [2, 5, 2, 5, 2, 5, 2, 5, 5, 8, 5, 8, 5, 8, 5, 8],
            [5, 2, 5, 2, 5, 2, 5, 2, 8, 5, 8, 5, 8, 5, 8, 5],
            [2, 5, 2, 5, 2, 5, 2, 5, 5, 8, 5, 8, 5, 8, 5, 8],
            [5, 2, 5, 2, 5, 2, 5, 2, 8, 5, 8, 5, 8, 5, 8, 5],
            [5, 8, 5, 8, 5, 8, 5, 8, 2, 5, 2, 5, 2, 5, 2, 5],
            [8, 5, 8, 5, 8, 5, 8, 5, 5, 2, 5, 2, 5, 2, 5, 2],
            [5, 8, 5, 8, 5, 8, 5, 8, 2, 5, 2, 5, 2, 5, 2, 5],
            [8, 5, 8, 5, 8, 5, 8, 5, 5, 2, 5, 2, 5, 2, 5, 2],
            [5, 8, 5, 8, 5, 8, 5, 8, 2, 5, 2, 5, 2, 5, 2, 5],
            [8, 5, 8, 5, 8, 5, 8, 5, 5, 2, 5, 2, 5, 2, 5, 2],
            [5, 8, 5, 8, 5, 8, 5, 8, 2, 5, 2, 5, 2, 5, 2, 5],
            [8, 5, 8, 5, 8, 5, 8, 5, 5, 2, 5, 2, 5, 2, 5, 2],
        ],
        dtype=float,
    )
    return (raster,)


@app.cell(hide_code=True)
def _controls(mo):
    base_level_factor = mo.ui.slider(
        start=2, stop=4, step=1, value=2, label="base_level_factor"
    )
    agg_fun = mo.ui.dropdown(
        options=["mean", "sum", "median"],
        value="mean",
        label="agg_fun",
    )
    mo.hstack([base_level_factor, agg_fun], justify="start")
    return agg_fun, base_level_factor


@app.cell
def _compute(agg_fun, base_level_factor, raster, scale_variance_raster, warnings):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # numpy array carries no CRS — expected
        result = scale_variance_raster(
            raster,
            base_level_factor=base_level_factor.value,
            agg_fun=agg_fun.value,
        )
    return (result,)


@app.cell
def _summary(mo, result):
    mo.md(
        f"**TSS** = {result.total_ss:.1f} &nbsp;&nbsp; "
        f"**total_df** = {result.total_df} &nbsp;&nbsp; "
        f"**grand_mean** = {result.grand_mean:.3f}"
    )
    return


@app.cell
def _raster_plot(np, plt, raster):
    fig, ax = plt.subplots(figsize=(4.0, 4.0))
    palette = {2: "#0072B2", 5: "#F0E442", 8: "#D55E00"}
    rgb = np.zeros(raster.shape + (3,))
    for v, hexcol in palette.items():
        c = np.array([int(hexcol[i : i + 2], 16) for i in (1, 3, 5)]) / 255.0
        rgb[raster == v] = c
    ax.imshow(rgb, interpolation="nearest")
    for k in range(17):
        ax.axhline(k - 0.5, color="white", lw=0.4, alpha=0.6)
        ax.axvline(k - 0.5, color="white", lw=0.4, alpha=0.6)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("MT1972 Figure 3 — 16×16, values {2, 5, 8}")
    fig.tight_layout()
    fig
    return


@app.cell
def _lollipop(np, plt, result):
    comp = result.components
    x = np.arange(len(comp))
    fig, ax = plt.subplots(figsize=(7, 3.4))
    ax.vlines(x, 0, comp["ss_share"], color="#222", linewidth=1.5)
    ax.scatter(x, comp["ss_share"], s=70, color="#222", zorder=3)
    for xi, yi in zip(x, comp["ss_share"], strict=True):
        if yi > 0:
            ax.text(xi, yi + 0.025, f"{yi * 100:.0f}%", ha="center", fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels(
        [f"{int(s)}" if not np.isnan(s) else "—" for s in comp["scale"]]
    )
    ax.set_xlabel("scale (pixels)")
    ax.set_yticks([])
    ymax = max(comp["ss_share"].max(), 0.05) * 1.35
    ax.set_ylim(0, ymax)
    ax.axhline(0, color="#999", linewidth=0.6)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_visible(False)
    ax.set_title("share of total variance by scale")
    fig.tight_layout()
    fig
    return


@app.cell
def _components_table(mo, result):
    mo.ui.table(result.components.round(6), selection=None)
    return


@app.cell(hide_code=True)
def _footer(mo):
    mo.md(
        r"""
        ---
        Source: Moellering, H., & Tobler, W. (1972). *Geographical Variances*.
        *Geographical Analysis* 4(1), 34–50. The decomposition is computed by
        [`scalevar`](https://github.com/jacobdein/scale-variance) running entirely
        in your browser via Pyodide; nothing is sent to a server.
        """
    )
    return


if __name__ == "__main__":
    app.run()
