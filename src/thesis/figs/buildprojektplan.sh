#!/usr/bin/env bash
# Builds standalone figures in this folder (currently: projektplan).
# Produces projektplan.pdf and projektplan.png next to the .tex source.
set -euo pipefail

cd "$(dirname "$0")"

NAME="projektplan"

latexmk -pdf -interaction=nonstopmode -halt-on-error "${NAME}.tex"

gs -dBATCH -dNOPAUSE -dQUIET \
   -sDEVICE=png16m -r300 \
   -dTextAlphaBits=4 -dGraphicsAlphaBits=4 \
   -sOutputFile="${NAME}.png" "${NAME}.pdf"

latexmk -c "${NAME}.tex" >/dev/null

echo "Built ${NAME}.pdf and ${NAME}.png"
