#!/usr/bin/env bash
# Export the marimo notebook to a static WASM bundle in playground/dist/.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NOTEBOOK="$HERE/notebooks/mt1972_explorable.py"
OUT_DIR="$HERE/dist"

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

marimo export html-wasm "$NOTEBOOK" -o "$OUT_DIR" --mode run --force

echo
echo "Bundle written to: $OUT_DIR"
du -sh "$OUT_DIR"
