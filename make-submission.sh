#!/usr/bin/env bash
# Assemble the digital deliverable for the bachelor thesis.
# Produces ./submission/ containing source code, thesis sources + PDF,
# experiment configs, npz datasets, trained model checkpoints and result JSONs.
# Excluded: raw pcaps (hundreds of GB, reproducible via shadowctl.py),
# Python virtualenvs, third-party WFlib code (cloneable from upstream),
# LaTeX build artefacts, editor/OS clutter.
#
# Re-runnable: wipes ./submission/ at the start.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
OUT="$ROOT/submission"

echo ">> Wiping $OUT"
rm -rf "$OUT"
mkdir -p "$OUT"

EXCLUDES=(
  # Bulk pcaps: hundreds of GB, regeneratable.
  --exclude='*.pcap'
  # Python virtualenvs and bytecode.
  --exclude='venv/'
  --exclude='__pycache__/'
  --exclude='*.pyc'
  # OS / editor clutter.
  --exclude='.DS_Store'
  --exclude='~$*'
  --exclude='.vscode/'
  --exclude='.devcontainer/'
  # Git internals (the submission is not a clone).
  --exclude='.git/'
  --exclude='.gitmodules'
  --exclude='.gitignore'
  # LaTeX build artefacts (keep .pdf and .bbl).
  --exclude='*.aux'
  --exclude='*.fdb_latexmk'
  --exclude='*.fls'
  --exclude='*.toc'
  --exclude='*.lof'
  --exclude='*.out'
  --exclude='*.synctex.gz'
)

echo ">> Copying src/simulation (without pcaps)"
mkdir -p "$OUT/src"
rsync -a "${EXCLUDES[@]}" src/simulation "$OUT/src/"

echo ">> Copying src/ml (without venv and third-party WFlib code)"
rsync -a "${EXCLUDES[@]}" \
  --exclude='wflib/WFlib/' \
  --exclude='wflib/exp/' \
  --exclude='wflib/scripts/' \
  --exclude='wflib/figures/' \
  --exclude='wflib/WFlib.egg-info/' \
  --exclude='wflib/README.md' \
  --exclude='wflib/LICENSE' \
  src/ml "$OUT/src/"

echo ">> Copying src/thesis (LaTeX source + final PDF)"
rsync -a "${EXCLUDES[@]}" src/thesis "$OUT/src/"

echo ">> Copying top-level result artefacts"
cp ExperimentLogs.csv "$OUT/"
[ -f ExperimentLogs.xlsx ] && cp ExperimentLogs.xlsx "$OUT/"
cp documentation.md "$OUT/"
cp README.md "$OUT/"
mkdir -p "$OUT/images" && rsync -a "${EXCLUDES[@]}" images/ "$OUT/images/"
cp confusion_*.pdf "$OUT/" 2>/dev/null || true
cp confusion_*.svg "$OUT/" 2>/dev/null || true

echo ">> Writing INHALT.md"
cat > "$OUT/INHALT.md" <<'EOF'
# Inhalt dieses Datenträgers

Detaillierte Beschreibung im Anhang "Begleitende Materialien" der
Bachelorarbeit (`src/thesis/hslu_thesis.pdf`).

## Kurzer Überblick

| Pfad | Inhalt |
|------|--------|
| `src/thesis/hslu_thesis.pdf` | finale Bachelorarbeit |
| `src/thesis/` | LaTeX-Quellen der Bachelorarbeit |
| `src/simulation/` | Shadow-Simulationsskripte und Experimentkonfigurationen |
| `src/simulation/exp-*/` | pro Experiment: shadow.config.yaml, schedule.json, conf/, sim.log |
| `src/ml/` | Skripte der ML-Pipeline (pcap_to_npz, run_df.sh, correlation.py, ...) |
| `src/ml/datasets/` | eigene Hilfsdatensätze (Cell-Trace-Vergleich) |
| `src/ml/wflib/datasets/` | WFlib-Datensätze pro Experiment (.npz, .labels.json) |
| `src/ml/wflib/checkpoints/` | trainierte DF-Modelle (`max_f1.pth`) |
| `src/ml/wflib/logs/` | Ergebnis-JSONs der Trainings- und Testläufe |
| `ExperimentLogs.csv` / `.xlsx` | aggregierte Resultattabelle aller Läufe |
| `documentation.md` | Gesamtbeschreibung der Pipeline |
| `images/results/` | generierte Diagramme |
| `confusion_*.pdf` / `.svg` | Confusion-Matrix-Visualisierungen |

## Nicht enthalten

- **Rohe Pcap-Dateien** (insgesamt etwa 250 GB). Reproduzierbar mit
  `python3 src/simulation/shadowctl.py run <name> ...` aus den
  hier enthaltenen Konfigurationsdateien.
- **Python-Virtualenvs** (recreatable via `python3 -m venv` und den
  requirements in `documentation.md`).
- **WFlib-Codebasis** (geklont von
  `https://github.com/Xinhao-Deng/Website-Fingerprinting-Library`,
  Commit-Verweis siehe `documentation.md`). Eigene Datensätze und
  trainierte Modelle liegen unverändert unter `src/ml/wflib/datasets/`
  bzw. `src/ml/wflib/checkpoints/`.
EOF

echo
echo ">> Submission ready at $OUT"
du -sh "$OUT"
