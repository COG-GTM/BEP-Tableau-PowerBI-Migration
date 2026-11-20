#!/usr/bin/env bash
# Render the Graphviz sources in this folder to PNG and SVG.
# Requires Graphviz (`sudo apt-get install -y graphviz fonts-dejavu`).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
for src in *.dot; do
  name="${src%.dot}"
  dot -Tpng -Gdpi=110 "$src" -o "$name.png"
  dot -Tsvg "$src" -o "$name.svg"
  echo "Rendered $name.png and $name.svg"
done
