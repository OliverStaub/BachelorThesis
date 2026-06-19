#!/usr/bin/env bash
# Kompiliert die Thesis-Grafiken (TikZ/pgfplots) zu Standalone-SVGs fuer das
# Schlusspraesentations-Deck und kopiert sie samt vorhandener Bilddateien nach
# ../abschlusspraesentation/images/.
#
# Voraussetzungen (im LaTeX-Devcontainer vorhanden): latexmk, pdflatex,
# pdftocairo (poppler). Fallback pdf->svg: dvisvgm --pdf.
#
# Aufruf:  bash build-figures.sh
set -euo pipefail

cd "$(dirname "$0")"

REPO_ROOT="../../.."
# Die Folien referenzieren die Grafiken relativ (./images/...), daher liegen sie
# direkt neben slides.md unter <deck>/images/ (nicht in public/).
IMG_OUT="../abschlusspraesentation/images"
mkdir -p "$IMG_OUT"

# Standalone-Wrapper -> PDF -> SVG
FIGS=(
  onion_routing
  tor_cell
  tcp_vs_cells
  data_pipeline
  accuracy_overview
  openworld_pr
  defense_tradeoff
  perfmon
)

pdf_to_svg() {
  # $1 = basename ohne Endung
  if command -v pdftocairo >/dev/null 2>&1; then
    pdftocairo -svg "$1.pdf" "$1.svg"
  else
    dvisvgm --pdf "$1.pdf" -o "$1.svg"
  fi
}

for f in "${FIGS[@]}"; do
  echo ">>> kompiliere $f.tex"
  latexmk -pdf -interaction=nonstopmode -halt-on-error "$f.tex" >/dev/null
  pdf_to_svg "$f"
  cp "$f.svg" "$IMG_OUT/"
  echo "    -> $IMG_OUT/$f.svg"
done

# Bereits fertige Vektor-PDF aus der Arbeit: Konfusionsmatrizen (OFF/ON/Tamaraw, 80 Klassen)
echo ">>> konvertiere Konfusionsmatrix-PDF"
pdftocairo -svg "$REPO_ROOT/confusion_comparison_off_on_tamaraw_80.pdf" "$IMG_OUT/confusion_off_on_tamaraw_80.svg" \
  || dvisvgm --pdf "$REPO_ROOT/confusion_comparison_off_on_tamaraw_80.pdf" -o "$IMG_OUT/confusion_off_on_tamaraw_80.svg"
echo "    -> $IMG_OUT/confusion_off_on_tamaraw_80.svg"

# Topologie-Diagramme (sind bereits PNG-Includes in der Arbeit) direkt kopieren
echo ">>> kopiere Topologie-PNGs"
cp "$REPO_ROOT/images/ShadowSetup.png"  "$IMG_OUT/"
cp "$REPO_ROOT/images/Tamaraw-Setup.png" "$IMG_OUT/"
echo "    -> $IMG_OUT/ShadowSetup.png, $IMG_OUT/Tamaraw-Setup.png"

# Aufraeumen der LaTeX-Hilfsdateien
echo ">>> raeume auf"
for f in "${FIGS[@]}"; do
  latexmk -c "$f.tex" >/dev/null 2>&1 || true
done

echo
echo "Fertig. Erzeugte Assets in $IMG_OUT:"
ls -1 "$IMG_OUT"
