"""Build and execute the three example notebooks.

Re-run with:

    python python/scripts/_build_notebooks.py

This script is the source of truth for each notebook's content. It constructs
the notebooks programmatically via ``nbformat`` and executes them with
``nbconvert`` so the committed ``.ipynb`` files carry rendered outputs and
plots — users can preview them on the docs site without running anything.
"""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf
from nbconvert.preprocessors import ExecutePreprocessor

HERE = Path(__file__).resolve().parents[1] / "docs" / "examples"


def _nb(title_md: str, cells: list[tuple[str, str]]) -> nbf.NotebookNode:
    """cells: [(kind, source)] where kind is 'md' or 'code'."""
    nb = nbf.v4.new_notebook()
    nb.metadata = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "pygments_lexer": "ipython3"},
    }
    nb.cells = [nbf.v4.new_markdown_cell(title_md)]
    for kind, src in cells:
        if kind == "md":
            nb.cells.append(nbf.v4.new_markdown_cell(src))
        else:
            nb.cells.append(nbf.v4.new_code_cell(src))
    return nb


def build_tabular_admin() -> nbf.NotebookNode:
    title = (
        "# 1 — Tabular admin hierarchy\n"
        "\n"
        "Shows `scale_variance` applied to a non-spatial, ragged hierarchy — "
        "counties within states within regions. No raster, no CRS, no geometry. "
        "This is the same family of problem as the fixture `fixture_irregular_admin` "
        "in the parity suite. The expected totals here are hand-verifiable."
    )
    cells = [
        ("md", "## Setup"),
        (
            "code",
            "import pandas as pd\n"
            "import numpy as np\n"
            "import matplotlib.pyplot as plt\n"
            "\n"
            "from scalevar import scale_variance",
        ),
        ("md", "## Build a ragged hierarchy\n\n"
               "Six states, two regions, 24 counties with deliberately irregular "
               "fan-out (some states have three counties, others five). Values are "
               "constructed so that each region-level mean differs cleanly from the "
               "others — that's the signal at the coarsest scale."),
        (
            "code",
            "rows = [\n"
            "    # (county_id, state_id, region_id, value)\n"
            "    (1, 1, 1, 10), (2, 1, 1, 20), (3, 1, 1, 30),\n"
            "    (4, 2, 1, 8), (5, 2, 1, 14), (6, 2, 1, 20), (7, 2, 1, 26), (8, 2, 1, 32),\n"
            "    (9, 3, 2, 40), (10, 3, 2, 50), (11, 3, 2, 60),\n"
            "    (12, 4, 2, 38), (13, 4, 2, 44), (14, 4, 2, 50), (15, 4, 2, 56), (16, 4, 2, 62),\n"
            "    (17, 5, 2, 70), (18, 5, 2, 80), (19, 5, 2, 90),\n"
            "    (20, 6, 2, 68), (21, 6, 2, 74), (22, 6, 2, 80), (23, 6, 2, 86), (24, 6, 2, 92),\n"
            "]\n"
            "df = pd.DataFrame(rows, columns=['county_id', 'state_id', 'region_id', 'value'])\n"
            "df.head()",
        ),
        ("md", "## Decompose"),
        (
            "code",
            "result = scale_variance(\n"
            "    df,\n"
            "    value='value',\n"
            "    id_cols=['county_id', 'state_id', 'region_id'],\n"
            "    agg_fun='mean',\n"
            ")\n"
            "\n"
            "print(f'TSS        = {result.total_ss:.1f}')\n"
            "print(f'grand_mean = {result.grand_mean}')\n"
            "print(f'total_df   = {result.total_df}')\n"
            "result.components.round(4)",
        ),
        ("md",
            "About two-thirds of the total variance lives at the **region** level "
            "(the coarsest), about 22% at the **state** level, and only about 10% "
            "within states — which matches the design (values were chosen to put "
            "most of the signal at the top). The identity `Σ SS_n = TSS` holds "
            "exactly.\n"),
        (
            "code",
            "assert abs(result.components['sum_squares'].sum() - result.total_ss) < 1e-9\n"
            "assert result.components['df'].sum() == result.total_df\n"
            "assert abs(result.components['ss_share'].sum() - 1.0) < 1e-10\n"
            "'identities hold'",
        ),
        ("md", "## Plot the variance share by scale"),
        (
            "code",
            "fig, ax = plt.subplots(figsize=(7, 3.5))\n"
            "labels = ['counties→states', 'states→regions', 'regions→grand mean']\n"
            "bars = ax.bar(labels, result.components['ss_share'], color=['#4c78a8', '#f58518', '#e45756'])\n"
            "ax.set_ylabel('share of total variance')\n"
            "ax.set_ylim(0, 1)\n"
            "ax.set_title('Scale variance — admin hierarchy')\n"
            "for bar, share in zip(bars, result.components['ss_share'], strict=True):\n"
            "    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,\n"
            "            f'{share*100:.1f}%', ha='center', fontsize=9)\n"
            "fig.tight_layout()\n"
            "plt.show()",
        ),
        ("md", "## Inspecting elements (where variance accumulates per level)\n\n"
               "`result.elements[n]` gives one row per distinct level-`n` cell, "
               "each row showing that cell's contribution `sv = (parent − child)²`."),
        (
            "code",
            "# Which states contribute the most to within-state variance?\n"
            "states = result.elements[2].sort_values('sv', ascending=False)\n"
            "states",
        ),
        ("md",
            "All six states contribute equally at the state→region step because "
            "deviations `|region_mean − state_mean|` are symmetric in this toy "
            "example. The full fixture (`tests/fixtures/fixture_irregular_admin`) "
            "exercises the same code path with hand-derived expected values at "
            "every level."),
    ]
    return _nb(title, cells)


def build_raster_mt1972_fig3() -> nbf.NotebookNode:
    title = (
        "# 2 — Moellering & Tobler (1972) Figure 3\n"
        "\n"
        "Reproduces the worked example from the original 1972 paper. "
        "A 16×16 raster of integer values `{2, 5, 8}` arranged as a checkerboard "
        "of checkerboards: a fine 2×2 alternation nested inside a coarse 2×2 "
        "quadrant pattern. The paper reports `TSS = 1152` and `TDF = 255`; the "
        "scale-variance decomposition concentrates equally at the **finest** and "
        "**coarsest** scales (50% / 50%), with zeros in between.\n"
        "\n"
        "We run the example twice, end-to-end:\n"
        "\n"
        "1. Through `scale_variance_raster` on the raster directly.\n"
        "2. Through `scale_variance` on the same data flattened to a tabular "
        "   nested hierarchy.\n"
        "\n"
        "Both paths return identical components — by design."
    )
    cells = [
        ("md", "## Setup"),
        (
            "code",
            "import numpy as np\n"
            "import pandas as pd\n"
            "import matplotlib.pyplot as plt\n"
            "\n"
            "from scalevar import scale_variance, scale_variance_raster",
        ),
        ("md", "## Build the input — the 16×16 Figure 3 raster\n\n"
               "Top-left 8×8 quadrant: a `{2, 5}` checkerboard. "
               "Top-right and bottom-left 8×8: `{5, 8}` checkerboards. "
               "Bottom-right 8×8: `{2, 5}` again. "
               "Two structural scales by construction: a 2-pixel alternation and an 8-pixel quadrant pattern."),
        (
            "code",
            "raster = np.array([\n"
            "    [2, 5, 2, 5, 2, 5, 2, 5, 5, 8, 5, 8, 5, 8, 5, 8],\n"
            "    [5, 2, 5, 2, 5, 2, 5, 2, 8, 5, 8, 5, 8, 5, 8, 5],\n"
            "    [2, 5, 2, 5, 2, 5, 2, 5, 5, 8, 5, 8, 5, 8, 5, 8],\n"
            "    [5, 2, 5, 2, 5, 2, 5, 2, 8, 5, 8, 5, 8, 5, 8, 5],\n"
            "    [2, 5, 2, 5, 2, 5, 2, 5, 5, 8, 5, 8, 5, 8, 5, 8],\n"
            "    [5, 2, 5, 2, 5, 2, 5, 2, 8, 5, 8, 5, 8, 5, 8, 5],\n"
            "    [2, 5, 2, 5, 2, 5, 2, 5, 5, 8, 5, 8, 5, 8, 5, 8],\n"
            "    [5, 2, 5, 2, 5, 2, 5, 2, 8, 5, 8, 5, 8, 5, 8, 5],\n"
            "    [5, 8, 5, 8, 5, 8, 5, 8, 2, 5, 2, 5, 2, 5, 2, 5],\n"
            "    [8, 5, 8, 5, 8, 5, 8, 5, 5, 2, 5, 2, 5, 2, 5, 2],\n"
            "    [5, 8, 5, 8, 5, 8, 5, 8, 2, 5, 2, 5, 2, 5, 2, 5],\n"
            "    [8, 5, 8, 5, 8, 5, 8, 5, 5, 2, 5, 2, 5, 2, 5, 2],\n"
            "    [5, 8, 5, 8, 5, 8, 5, 8, 2, 5, 2, 5, 2, 5, 2, 5],\n"
            "    [8, 5, 8, 5, 8, 5, 8, 5, 5, 2, 5, 2, 5, 2, 5, 2],\n"
            "    [5, 8, 5, 8, 5, 8, 5, 8, 2, 5, 2, 5, 2, 5, 2, 5],\n"
            "    [8, 5, 8, 5, 8, 5, 8, 5, 5, 2, 5, 2, 5, 2, 5, 2],\n"
            "], dtype=float)\n"
            "\n"
            "fig, ax = plt.subplots(figsize=(4.2, 4.2))\n"
            "palette = {2: '#0072B2', 5: '#F0E442', 8: '#D55E00'}\n"
            "rgb = np.zeros(raster.shape + (3,))\n"
            "for v, hexcol in palette.items():\n"
            "    c = np.array([int(hexcol[i:i+2], 16) for i in (1, 3, 5)]) / 255.0\n"
            "    rgb[raster == v] = c\n"
            "ax.imshow(rgb, interpolation='nearest')\n"
            "for k in range(17):\n"
            "    ax.axhline(k - 0.5, color='white', lw=0.4, alpha=0.6)\n"
            "    ax.axvline(k - 0.5, color='white', lw=0.4, alpha=0.6)\n"
            "ax.set_xticks([]); ax.set_yticks([])\n"
            "ax.set_title('Figure 3 — 16×16 raster, values {2, 5, 8}')\n"
            "fig.tight_layout()\n"
            "plt.show()",
        ),
        ("md", "## Path 1 — `scale_variance_raster`\n\n"
               "`num_levels=None` lets the package auto-pick "
               "`floor(log_2(16)) + 1 = 5` levels. The `{2, 5, 8}` cell counts "
               "are `64 / 128 / 64`, so the grand mean is exactly **5**, and "
               "`TSS = 64·9 + 128·0 + 64·9 = 1152` — the paper's number."),
        (
            "code",
            "import warnings\n"
            "with warnings.catch_warnings():\n"
            "    warnings.simplefilter('ignore')  # numpy array carries no CRS — expected\n"
            "    raster_result = scale_variance_raster(raster, agg_fun='mean')\n"
            "\n"
            "print(f'TSS        = {raster_result.total_ss}')\n"
            "print(f'total_df   = {raster_result.total_df}')\n"
            "print(f'grand_mean = {raster_result.grand_mean}')\n"
            "raster_result.components.round(6)",
        ),
        ("md", "## Plot the scale-variance lollipop\n\n"
               "Two equal peaks at the finest and coarsest scales, zeros in "
               "between — the structural fingerprint of two nested checkerboards."),
        (
            "code",
            "comp = raster_result.components\n"
            "x = np.arange(len(comp))\n"
            "fig, ax = plt.subplots(figsize=(7, 3.4))\n"
            "ax.vlines(x, 0, comp['ss_share'], color='#222', linewidth=1.5)\n"
            "ax.scatter(x, comp['ss_share'], s=70, color='#222', zorder=3)\n"
            "for xi, yi in zip(x, comp['ss_share'], strict=True):\n"
            "    if yi > 0:\n"
            "        ax.text(xi, yi + 0.025, f'{yi*100:.0f}%', ha='center', fontsize=10)\n"
            "ax.set_xticks(x)\n"
            "ax.set_xticklabels([f\"{int(s)}\" for s in comp['scale']])\n"
            "ax.set_xlabel('scale (pixels)')\n"
            "ax.set_yticks([])\n"
            "ax.set_ylim(0, max(comp['ss_share']) * 1.35)\n"
            "ax.axhline(0, color='#999', linewidth=0.6)\n"
            "for s in ('top', 'right', 'left'):\n"
            "    ax.spines[s].set_visible(False)\n"
            "ax.spines['bottom'].set_visible(False)\n"
            "ax.set_title('share of total variance by scale')\n"
            "fig.tight_layout()\n"
            "plt.show()",
        ),
        ("md", "## Path 2 — `scale_variance` on the same data, flattened\n\n"
               "Build a 256-row dataframe with one row per cell. `id_level1` is "
               "the cell's row-major index; the parent IDs follow the 2× nested "
               "blocking structure (`id_level{n+1}` groups together `2 × 2` "
               "siblings of `id_level{n}`, on the level-`n` grid)."),
        (
            "code",
            "rows, cols = raster.shape\n"
            "rr, cc = np.mgrid[0:rows, 0:cols]\n"
            "tab = pd.DataFrame({\n"
            "    'value':     raster.ravel(),\n"
            "    'id_level1': (rr * cols + cc).ravel() + 1,\n"
            "    'id_level2': ((rr // 2) * (cols // 2)  + (cc // 2)).ravel() + 1,\n"
            "    'id_level3': ((rr // 4) * (cols // 4)  + (cc // 4)).ravel() + 1,\n"
            "    'id_level4': ((rr // 8) * (cols // 8)  + (cc // 8)).ravel() + 1,\n"
            "    'id_level5': np.ones(rows * cols, dtype=int),\n"
            "})\n"
            "tab.head()",
        ),
        (
            "code",
            "tab_result = scale_variance(\n"
            "    tab,\n"
            "    value='value',\n"
            "    id_cols=['id_level1', 'id_level2', 'id_level3', 'id_level4', 'id_level5'],\n"
            "    agg_fun='mean',\n"
            ")\n"
            "print(f'TSS        = {tab_result.total_ss}')\n"
            "print(f'total_df   = {tab_result.total_df}')\n"
            "print(f'grand_mean = {tab_result.grand_mean}')\n"
            "tab_result.components.round(6)",
        ),
        ("md", "## Both paths agree on every component\n\n"
               "The tabular core has no notion of pixel size, so its `scale` "
               "column is `NaN` (only the raster path knows the cell size). All "
               "other columns — `sum_squares`, `df`, `mean_square`, `ss_share`, "
               "`ms_share`, `ss_cumulative` — match exactly."),
        (
            "code",
            "shared_cols = ['level', 'sum_squares', 'df', 'mean_square',\n"
            "               'ss_share', 'ms_share', 'ss_cumulative']\n"
            "pd.testing.assert_frame_equal(\n"
            "    raster_result.components[shared_cols].reset_index(drop=True),\n"
            "    tab_result.components[shared_cols].reset_index(drop=True),\n"
            ")\n"
            "'raster path == tabular path'",
        ),
        ("md", "## Sanity checks against the paper\n\n"
               "Both paths must close the decomposition identity exactly, and "
               "must reproduce Moellering & Tobler's published totals."),
        (
            "code",
            "for label, res in [('raster', raster_result), ('tabular', tab_result)]:\n"
            "    assert res.total_ss == 1152.0,           f'{label}: TSS != 1152'\n"
            "    assert res.total_df == 255,              f'{label}: TDF != 255'\n"
            "    assert res.grand_mean == 5.0,            f'{label}: grand_mean != 5'\n"
            "    assert abs(res.components['sum_squares'].sum() - res.total_ss) < 1e-9\n"
            "    assert res.components['df'].sum() == res.total_df\n"
            "    assert abs(res.components['ss_share'].sum() - 1.0) < 1e-12\n"
            "'all checks pass — matches the 1972 paper'",
        ),
    ]
    return _nb(title, cells)


def build_polygon_hierarchy() -> nbf.NotebookNode:
    title = (
        "# 3 — Polygon hierarchy (create_hbins + join_hbins)\n"
        "\n"
        "Demonstrates the polygon path: build a nested regular grid over an AOI, "
        "join random point observations to the grid, and decompose the per-cell "
        "aggregated value across scales.\n"
        "\n"
        "Requires the `[spatial]` extra: `pip install scalevar[spatial]`."
    )
    cells = [
        ("md", "## Setup"),
        (
            "code",
            "import numpy as np\n"
            "import matplotlib.pyplot as plt\n"
            "import geopandas as gpd\n"
            "from shapely.geometry import Point, box\n"
            "\n"
            "from scalevar import scale_variance\n"
            "from scalevar.spatial import create_hbins, join_hbins\n"
            "\n"
            "rng = np.random.default_rng(20260424)",
        ),
        ("md", "## Build a tiny AOI in a projected CRS\n\n"
               "A 1 km × 1 km square in **British National Grid** (EPSG:27700). "
               "Geographic CRSes like EPSG:4326 are deliberately refused by "
               "`create_hbins` — see the project's crs-correction-note for "
               "why."),
        (
            "code",
            "aoi = gpd.GeoDataFrame(\n"
            "    geometry=[box(530_000, 180_000, 531_000, 181_000)],\n"
            "    crs='EPSG:27700',\n"
            ")\n"
            "aoi",
        ),
        ("md", "## Build nested hbins\n\n"
               "Level 1 = 62.5 m cells, level 2 = 125 m, level 3 = 250 m, level 4 = 500 m."),
        (
            "code",
            "hbins = create_hbins(aoi, base_cell_size=62.5, n_levels=4, base_level_factor=2)\n"
            "hbins.groupby('level').size().rename('n_cells').to_frame()",
        ),
        ("md", "## Scatter random point observations and join them"),
        (
            "code",
            "n_pts = 400\n"
            "minx, miny, maxx, maxy = aoi.total_bounds\n"
            "xs = rng.uniform(minx, maxx, size=n_pts)\n"
            "ys = rng.uniform(miny, maxy, size=n_pts)\n"
            "# Give each point a value that covaries with its coarse location —\n"
            "# i.e. variance mostly lives at the coarsest scale.\n"
            "values = 100.0 * ((xs - minx) / (maxx - minx)) + 2.0 * rng.standard_normal(n_pts)\n"
            "pts = gpd.GeoDataFrame(\n"
            "    {'v': values},\n"
            "    geometry=[Point(x, y) for x, y in zip(xs, ys, strict=True)],\n"
            "    crs='EPSG:27700',\n"
            ")\n"
            "\n"
            "per_cell = join_hbins(pts, hbins, value_col='v', agg_fun='mean')\n"
            "per_cell.head()",
        ),
        ("md", "## Decompose\n\n"
               "`id_level_1` is the finest cell; `id_level_{2..4}` are its ancestors. "
               "Pass these columns to `scale_variance`."),
        (
            "code",
            "result = scale_variance(\n"
            "    per_cell,\n"
            "    value='v',\n"
            "    id_cols=['id_level_1', 'id_level_2', 'id_level_3', 'id_level_4'],\n"
            ")\n"
            "\n"
            "print(f'TSS        = {result.total_ss:.2f}')\n"
            "print(f'grand_mean = {result.grand_mean:.2f}')\n"
            "print(f'total_df   = {result.total_df}')\n"
            "result.components.round(4)",
        ),
        ("md", "## Visualize the finest level alongside variance-share\n\n"
               "Because the values are a linear gradient in x, the variance "
               "should concentrate at the coarsest scale — confirming the scale "
               "decomposition recovers the structure you put in."),
        (
            "code",
            "fig, (ax_map, ax_bars) = plt.subplots(1, 2, figsize=(11, 4.5),\n"
            "                                      gridspec_kw={'width_ratios': [1, 1]})\n"
            "\n"
            "lvl1 = hbins[hbins['level'] == 1].merge(per_cell[['id_level_1', 'v']],\n"
            "                                       left_on='id', right_on='id_level_1')\n"
            "lvl1.plot(column='v', ax=ax_map, cmap='viridis', edgecolor='white', linewidth=0.1)\n"
            "ax_map.set_title('level-1 per-cell mean of the point observations')\n"
            "ax_map.set_xticks([]); ax_map.set_yticks([])\n"
            "\n"
            "ax_bars.bar(result.components['level'], result.components['ss_share'],\n"
            "            color=['#4c78a8', '#f58518', '#e45756', '#54a24b'])\n"
            "ax_bars.set_xticks(result.components['level'])\n"
            "ax_bars.set_xticklabels(['L1', 'L2', 'L3', 'L4'])\n"
            "ax_bars.set_ylabel('share of total variance')\n"
            "ax_bars.set_title('variance share by level')\n"
            "fig.tight_layout()\n"
            "plt.show()",
        ),
        ("md", "## CRS safety\n\n"
               "`create_hbins` refuses geographic CRSes outright — the error "
               "message is the same across `create_hbins` and "
               "`scale_variance_raster` and will match the R sibling exactly in v0.2."),
        (
            "code",
            "from scalevar import UnprojectedCRSError\n"
            "\n"
            "bad_aoi = gpd.GeoDataFrame(geometry=[box(-0.1, 51.5, 0.1, 51.7)], crs='EPSG:4326')\n"
            "try:\n"
            "    create_hbins(bad_aoi, base_cell_size=0.01, n_levels=3)\n"
            "except UnprojectedCRSError as e:\n"
            "    print(str(e))",
        ),
    ]
    return _nb(title, cells)


def execute(nb: nbf.NotebookNode, path: Path) -> None:
    ep = ExecutePreprocessor(timeout=120, kernel_name="python3")
    ep.preprocess(nb, {"metadata": {"path": str(path.parent)}})
    with path.open("w") as f:
        nbf.write(nb, f)


def main() -> None:
    HERE.mkdir(exist_ok=True, parents=True)
    for name, builder in [
        ("01_tabular_admin.ipynb", build_tabular_admin),
        ("02_raster_mt1972_fig3.ipynb", build_raster_mt1972_fig3),
        ("03_polygon_hierarchy.ipynb", build_polygon_hierarchy),
    ]:
        nb = builder()
        path = HERE / name
        print(f"Building + executing {path.relative_to(HERE.parents[2])}...")
        execute(nb, path)
        print(f"  → wrote {path.name}")


if __name__ == "__main__":
    main()
