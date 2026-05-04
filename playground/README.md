# scalevar-playground

Interactive in-browser explorable for the Moellering & Tobler (1972) scale-variance
decomposition, deployed at `https://jacobdein.github.io/scale-variance/playground/`.

This is a top-level project sibling to `python/` and `r/`. It depends on
`scalevar` but is **not** part of it — the library stays small; the playground
is an app.

## Layout

- `notebooks/mt1972_explorable.py` — the marimo notebook exported to WASM.
- `src/playground/` — pure-Python helpers (state serialization, snippet
  generation, paper-language interpretation). Tested independently.
- `tests/test_playground.py` — pytest suite for the helpers.
- `scripts/export_wasm.sh` — runs `marimo export html-wasm` into `dist/`.

## Develop locally

`scalevar` is not on PyPI in v0.1 (CLAUDE.md). `pyproject.toml` declares it as
a `[tool.uv.sources]` editable path reference to the sibling `../python/`, so
`uv sync` resolves it from the working tree.

```sh
cd playground
uv sync
uv run marimo edit notebooks/mt1972_explorable.py
```

## Build and serve the WASM artifact

```sh
uv run bash scripts/export_wasm.sh
uv run python -m http.server --directory dist
```

Open <http://localhost:8000>.
