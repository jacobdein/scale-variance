#!/usr/bin/env bash
# Export the marimo notebook to a static WASM bundle in playground/dist/
# and stage the scalevar wheel so micropip can install it from the same
# origin. (Production deploys read the wheel URL from
# playground-manifest.json instead — Sunday's CI step.)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
NOTEBOOK="$HERE/notebooks/mt1972_explorable.py"
OUT_DIR="$HERE/dist"

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

marimo export html-wasm "$NOTEBOOK" -o "$OUT_DIR" --mode run --force

# Build a fresh scalevar wheel and stage it next to the bundle.
python -m build --wheel "$REPO/python" --outdir "$OUT_DIR" >/dev/null
ls "$OUT_DIR"/scalevar-*.whl

echo
echo "Bundle written to: $OUT_DIR"
du -sh "$OUT_DIR"
