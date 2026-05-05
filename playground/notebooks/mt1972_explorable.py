"""scalevar playground — MT1972 Figure 3 explorable.

Marimo notebook exported to WASM at scalevar.io/playground.
The fixture array is inlined so the WASM bundle does not have to ship
a side-channel data file. The inline literal matches
``tests/fixtures/fixture_mt1972_fig3/raster.npy`` (verified: TSS=1152, TDF=255).
"""

import marimo

__generated_with = "0.19.11"
app = marimo.App(width="medium")


@app.cell
def _setup():
    import marimo as mo
    return (mo,)


@app.cell
async def _install_scalevar():
    # scalevar is not on PyPI in v0.1; install the wheel that ships next to
    # the playground bundle. In production this URL points at the GitHub
    # Release wheel (read from playground-manifest.json); for local dev the
    # wheel lives at ./scalevar-0.1.0-py3-none-any.whl in the same dist/.
    import sys

    install_log = ""
    if sys.platform == "emscripten":
        import js
        import micropip

        # The cell runs inside pyodide's web worker; js.location there points
        # at the worker script (/assets/worker-*.js), not the page. Use the
        # origin and a server-root path so the resolved URL is independent of
        # where the worker bundle lives.
        origin = js.location.origin
        try:
            await micropip.install(f"{origin}/scalevar-0.1.0-py3-none-any.whl")
            install_log += "scalevar installed; "
        except Exception as exc:
            install_log += f"scalevar FAILED: {exc!r}; "
        try:
            # playground depends on scalevar + stdlib only; deps=False keeps
            # micropip from chasing marimo / matplotlib / etc.
            await micropip.install(
                f"{origin}/scalevar_playground-0.1.0-py3-none-any.whl",
                deps=False,
            )
            install_log += "playground installed."
        except Exception as exc:
            install_log += f"playground FAILED: {exc!r}."
    return (install_log,)


@app.cell(hide_code=True)
def _install_log_view(install_log, mo):
    # Show a status line only if something failed; on the happy path,
    # render nothing so the page lands on the title.
    bad = "FAILED" in install_log if install_log else False
    mo.callout(install_log, kind="danger") if bad else None
    return


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


@app.cell
def _imports():
    import warnings

    import matplotlib.pyplot as plt
    import numpy as np

    from scalevar import scale_variance_raster

    return np, plt, scale_variance_raster, warnings


@app.cell
def _fixture(np):
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


@app.cell
def _controls(mo):
    base_level_factor = mo.ui.slider(
        start=2, stop=4, step=1, value=2, label="base_level_factor"
    )
    agg_fun = mo.ui.dropdown(
        options=["mean", "sum", "median"],
        value="mean",
        label="agg_fun",
    )
    return agg_fun, base_level_factor


@app.cell
def _controls_view(agg_fun, base_level_factor, mo):
    mo.hstack([base_level_factor, agg_fun], justify="start")
    return


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
    raster_fig, raster_ax = plt.subplots(figsize=(4.0, 4.0))
    palette = {2: "#0072B2", 5: "#F0E442", 8: "#D55E00"}
    rgb = np.zeros(raster.shape + (3,))
    for v, hexcol in palette.items():
        c = np.array([int(hexcol[i : i + 2], 16) for i in (1, 3, 5)]) / 255.0
        rgb[raster == v] = c
    raster_ax.imshow(rgb, interpolation="nearest")
    for k in range(17):
        raster_ax.axhline(k - 0.5, color="white", lw=0.4, alpha=0.6)
        raster_ax.axvline(k - 0.5, color="white", lw=0.4, alpha=0.6)
    raster_ax.set_xticks([])
    raster_ax.set_yticks([])
    raster_ax.set_title("MT1972 Figure 3 — 16×16, values {2, 5, 8}")
    raster_fig.tight_layout()
    raster_fig
    return


@app.cell
def _lollipop(np, plt, result):
    comp = result.components
    x = np.arange(len(comp))
    lol_fig, lol_ax = plt.subplots(figsize=(7, 3.4))
    lol_ax.vlines(x, 0, comp["ss_share"], color="#222", linewidth=1.5)
    lol_ax.scatter(x, comp["ss_share"], s=70, color="#222", zorder=3)
    for xi, yi in zip(x, comp["ss_share"], strict=True):
        if yi > 0:
            lol_ax.text(xi, yi + 0.025, f"{yi * 100:.0f}%", ha="center", fontsize=10)
    lol_ax.set_xticks(x)
    lol_ax.set_xticklabels(
        [f"{int(s)}" if not np.isnan(s) else "—" for s in comp["scale"]]
    )
    lol_ax.set_xlabel("scale (pixels)")
    lol_ax.set_yticks([])
    ymax = max(comp["ss_share"].max(), 0.05) * 1.35
    lol_ax.set_ylim(0, ymax)
    lol_ax.axhline(0, color="#999", linewidth=0.6)
    for s in ("top", "right", "left"):
        lol_ax.spines[s].set_visible(False)
    lol_ax.spines["bottom"].set_visible(False)
    lol_ax.set_title("share of total variance by scale")
    lol_fig.tight_layout()
    lol_fig
    return


@app.cell
def _components_table(mo, result):
    mo.ui.table(result.components.round(6), selection=None)
    return


@app.cell
def _playground_imports():
    from playground import (
        generate_code_snippet,
        interpret_result,
        permalink,
    )

    return generate_code_snippet, interpret_result, permalink


@app.cell
def _current_state(agg_fun, base_level_factor):
    state = {
        "base_level_factor": base_level_factor.value,
        "agg_fun": agg_fun.value,
        "scalevar_version": "0.1.0",
        "preset": None,
    }
    return (state,)


@app.cell
def _appendix_button(mo):
    show_appendix = mo.ui.run_button(label="Generate Methods Appendix")
    return (show_appendix,)


@app.cell
def _appendix_button_view(show_appendix):
    show_appendix
    return


@app.cell
def _appendix(
    generate_code_snippet,
    interpret_result,
    mo,
    permalink,
    result,
    show_appendix,
    state,
):
    if not show_appendix.value:
        appendix = mo.md(
            r"_Set parameters above, then click **Generate Methods Appendix** "
            r"for a paste-ready Python snippet, paper-language interpretation, "
            r"and a permalink to share this exact view._"
        )
    else:
        snippet = generate_code_snippet(state)
        interpretation = interpret_result(result, state)
        url = permalink(state)
        bibtex = (
            "@article{moellering1972,\n"
            "  author  = {Moellering, Harold and Tobler, Waldo},\n"
            "  title   = {Geographical Variances},\n"
            "  journal = {Geographical Analysis},\n"
            "  volume  = {4}, number = {1}, pages = {34--50}, year = {1972}\n"
            "}"
        )
        appendix = mo.vstack(
            [
                mo.md("### Methods Appendix"),
                mo.md(f"**Interpretation.** {interpretation}"),
                mo.md("**Python (paste into your thesis or a notebook):**"),
                mo.md(f"```python\n{snippet}\n```"),
                mo.md(f"**Permalink:** [`{url}`]({url})"),
                mo.accordion(
                    {
                        "Cite the original paper (BibTeX)": mo.md(
                            f"```bibtex\n{bibtex}\n```"
                        ),
                        "Questions or bug reports": mo.md(
                            "Open an issue: "
                            "<https://github.com/jacobdein/scale-variance/issues>"
                        ),
                    }
                ),
            ]
        )
    appendix
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
