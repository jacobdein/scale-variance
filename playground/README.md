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

```sh
cd playground
python -m venv .venv && source .venv/bin/activate
pip install -e ../python
pip install -e .
marimo edit notebooks/mt1972_explorable.py
```

## Build the WASM artifact

```sh
bash scripts/export_wasm.sh
python -m http.server --directory dist
```

Open <http://localhost:8000>.
