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


def build_raster_synthetic() -> nbf.NotebookNode:
    title = (
        "# 2 — Synthetic multi-scale raster\n"
        "\n"
        "Constructs a 128×128 raster as a sum of sinusoids at three different "
        "spatial frequencies. Because each frequency lives cleanly at a specific "
        "aggregation scale, `scale_variance_raster` should show most of the variance "
        "at a handful of levels."
    )
    cells = [
        ("md", "## Setup"),
        (
            "code",
            "import numpy as np\n"
            "import matplotlib.pyplot as plt\n"
            "\n"
            "from scalevar import scale_variance_raster\n"
            "\n"
            "rng = np.random.default_rng(20260424)",
        ),
        ("md", "## Build the input\n\n"
               "Three cosine components at wavelengths 64, 16, and 4 pixels — "
               "corresponding roughly to level-4, level-3, and level-1 aggregations "
               "with `base_level_factor=2` — plus a small noise floor."),
        (
            "code",
            "n = 128\n"
            "y, x = np.mgrid[0:n, 0:n].astype(float)\n"
            "\n"
            "coarse  = 1.0 * np.cos(2*np.pi*x/64) * np.cos(2*np.pi*y/64)\n"
            "medium  = 0.6 * np.cos(2*np.pi*x/16) * np.cos(2*np.pi*y/16)\n"
            "fine    = 0.3 * np.cos(2*np.pi*x/4)  * np.cos(2*np.pi*y/4)\n"
            "noise   = 0.05 * rng.standard_normal((n, n))\n"
            "\n"
            "raster = coarse + medium + fine + noise\n"
            "\n"
            "fig, ax = plt.subplots(figsize=(5, 5))\n"
            "im = ax.imshow(raster, cmap='RdBu_r', vmin=-1.8, vmax=1.8, origin='lower')\n"
            "ax.set_title('synthetic 128×128 raster')\n"
            "ax.set_xticks([]); ax.set_yticks([])\n"
            "fig.colorbar(im, ax=ax, shrink=0.75)\n"
            "fig.tight_layout()\n"
            "plt.show()",
        ),
        ("md", "## Decompose across 8 levels\n\n"
               "`num_levels=None` (default) auto-picks `floor(log_b(min(nrow, ncol))) + 1 = 8` "
               "levels for a 128×128 base-2 hierarchy."),
        (
            "code",
            "import warnings\n"
            "with warnings.catch_warnings():\n"
            "    warnings.simplefilter('ignore')  # numpy array carries no CRS — expected\n"
            "    result = scale_variance_raster(raster, agg_fun='mean')\n"
            "\n"
            "print(f'TSS        = {result.total_ss:.2f}')\n"
            "print(f'grand_mean = {result.grand_mean:.4f}')\n"
            "print(f'n_levels   = {result.n_levels}')\n"
            "result.components.round(4)",
        ),
        ("md", "## Plot the scale-variance lollipop\n\n"
               "On a log x-axis the three structural peaks (4-pixel, 16-pixel, "
               "64-pixel wavelengths) should be visible."),
        (
            "code",
            "fig, ax = plt.subplots(figsize=(8, 4))\n"
            "comp = result.components\n"
            "ax.vlines(comp['scale'], 0, comp['ss_share'], color='#333', linewidth=1.5)\n"
            "ax.scatter(comp['scale'], comp['ss_share'], s=60, color='#4c78a8', zorder=3)\n"
            "ax.set_xscale('log', base=2)\n"
            "ax.set_xlabel('scale (pixels)')\n"
            "ax.set_ylabel('share of total variance')\n"
            "ax.set_title('Scale variance — synthetic multi-scale raster')\n"
            "ax.grid(True, which='both', alpha=0.2)\n"
            "for _, row in comp.iterrows():\n"
            "    ax.text(row['scale'], row['ss_share'] + 0.01, f\"{row['ss_share']*100:.0f}%\",\n"
            "            ha='center', fontsize=8)\n"
            "fig.tight_layout()\n"
            "plt.show()",
        ),
        ("md", "## Sanity checks\n\nThe same identities as the tabular case."),
        (
            "code",
            "assert abs(result.components['sum_squares'].sum() - result.total_ss) < 1e-7\n"
            "assert result.components['df'].sum() == result.total_df\n"
            "assert abs(result.components['ss_share'].sum() - 1.0) < 1e-10\n"
            "'identities hold'",
        ),
        ("md", "## Optional: inspect the per-cell SVE rasters\n\n"
               "Passing `return_sve=True` returns `sve` as a `(num_levels, nrow, ncol)` "
               "numpy array — each band is the squared difference at one scale, mapped "
               "back to the finest grid. Useful for visualizing **where** variance "
               "accumulates at each scale."),
        (
            "code",
            "with warnings.catch_warnings():\n"
            "    warnings.simplefilter('ignore')\n"
            "    result_sve = scale_variance_raster(raster, agg_fun='mean', return_sve=True)\n"
            "\n"
            "fig, axes = plt.subplots(2, 4, figsize=(12, 6))\n"
            "for lvl, ax in enumerate(axes.ravel(), start=1):\n"
            "    band = result_sve.sve[lvl-1]\n"
            "    scale = result_sve.components.loc[lvl-1, 'scale']\n"
            "    share = result_sve.components.loc[lvl-1, 'ss_share']\n"
            "    im = ax.imshow(band, cmap='magma', origin='lower')\n"
            "    ax.set_title(f'level {lvl} — scale={scale:.0f}\\n{share*100:.1f}% of TSS', fontsize=9)\n"
            "    ax.set_xticks([]); ax.set_yticks([])\n"
            "fig.suptitle('scale variance elements — squared differences per level')\n"
            "fig.tight_layout()\n"
            "plt.show()",
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
        ("02_raster_synthetic.ipynb", build_raster_synthetic),
        ("03_polygon_hierarchy.ipynb", build_polygon_hierarchy),
    ]:
        nb = builder()
        path = HERE / name
        print(f"Building + executing {path.relative_to(HERE.parents[2])}...")
        execute(nb, path)
        print(f"  → wrote {path.name}")


if __name__ == "__main__":
    main()
