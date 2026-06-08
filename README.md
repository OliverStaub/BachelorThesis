# Website Fingerprinting + Circuit Padding im Shadow-Simulator

Reproduktions- und Weiterführungsanleitung zur Bachelorarbeit

> **Praktische De-Anonymisierung im Tor-Netzwerk: Einfluss von Circuit Padding auf Website-Fingerprinting im Shadow Netzwerk Simulator**
> Oliver Staub, HSLU, Betreuung Dr. Radwan Eskhita

Dieses Repository enthält die komplette Pipeline, um in einem **deterministisch
simulierten Tor-Netzwerk** (Shadow) einen **Deep-Fingerprinting-Angriff (DF)**
durchzuführen und zu messen, wie stark **Tor Circuit Padding** und **Tamaraw**
die Erkennungsrate senken. Zusätzlich existiert ein Pcap-basierter
**Traffic-Correlation-Angriff**.

Diese Datei ist der **Einstiegspunkt** und beschreibt Aufbau, Bedienung und
Reproduktion. Für vertiefende Erläuterungen (Architektur-Diagramm, Tamaraw,
Correlation im Detail) siehe [documentation.md](documentation.md). Die
inhaltlichen Konventionen und der Forschungsstand stehen in
[CLAUDE.md](CLAUDE.md).

---

## Inhalt

1. [Überblick & Datenfluss](#1-überblick--datenfluss)
2. [Verzeichnisstruktur](#2-verzeichnisstruktur)
3. [Referenz aller Python-Skripte](#3-referenz-aller-python-skripte)
4. [Setup (lokal + Server)](#4-setup-lokal--server)
5. [Ein Experiment durchführen (Schritt für Schritt)](#5-ein-experiment-durchführen-schritt-für-schritt)
6. [Auswertung & Plots](#6-auswertung--plots)
7. [Experimente weiterführen / erweitern](#7-experimente-weiterführen--erweitern)
8. [Bekannte Einschränkungen](#8-bekannte-einschränkungen)
9. [Bisherige Ergebnisse](#9-bisherige-ergebnisse)

---

## 1. Überblick & Datenfluss

```
shadowctl.py run                      (Laptop, steuert Server via SSH)
  └─ tornettools generate             Basis-Tor-Netz erzeugen (Server)
  └─ generate-wf-config.py            Monitor- + Zimserver-Hosts in YAML einfügen,
                                      schedule.json schreiben (lokal)
  └─ push + simulate                  Shadow-Simulation starten (Server)
        │
        ▼
  Shadow-Simulation                   Monitor-Hosts holen je 1 Seite via wget2
  (pcaps auf Monitor-Hosts)           durch Tor, NEWNYM zwischen Besuchen
        │  pull-results
        ▼
  pcap_to_npz.py                      pcaps + schedule.json → WFlib .npz
        │                             (X = Richtungssequenzen ±1, y = Klassen)
        ▼
  WFlib  dataset_split → train (DF) → test → Accuracy / F1
```

Angreifermodell: passiver Beobachter auf ISP-Ebene, der den verschlüsselten
Tor-Verkehr beim Client sieht (Closed-World, ergänzt um ein Open-World-Experiment).

---

## 2. Verzeichnisstruktur

```
.
├── README.md                  ← diese Datei (Einstieg + Reproduktion)
├── documentation.md           Vertiefende Pipeline-Doku (Tamaraw, Correlation)
├── CLAUDE.md                  Projektstand, Konventionen, Forschungsmethodik
├── ExperimentLogs.csv         Ergebnis-Tracker (alle Experimente)
├── images/results/            Generierte Thesis-Charts
├── confusion_*.{pdf,svg,png}  Confusion-Matrix-Visualisierungen
├── perfmon-logs/              Server-Ressourcen-Telemetrie (dstat/perfmon)
├── src/
│   ├── simulation/            Shadow-Simulationssteuerung (siehe Tabelle)
│   │   ├── generated/urls.txt aktuelle URL-Liste (aus ZIM erzeugt)
│   │   ├── conf/              torrc-Vorlagen + tamaraw_cert.txt
│   │   ├── setup-wf-server.sh einmaliges Server-Setup
│   │   └── exp-*/             ein Unterordner pro Experiment (Config + Ergebnisse)
│   ├── ml/                    ML-Pipeline + Auswertung (siehe Tabelle)
│   │   ├── run_df.sh          End-to-end: convert → split → train → test
│   │   ├── datasets/          .npz-Datensätze
│   │   ├── wflib/             WFlib-Submodul (PyTorch DF-Klassifikator)
│   │   └── venv/              Python-Environment
│   └── thesis/               LaTeX-Quelle der Arbeit
├── submission/               Eingefrorene Kopie des Codes für die Abgabe
└── explainwf-popets2023/     Referenzartefakt Jansen & Wails 2023 (gitignored)
```

**Wichtig:** Alle `shadowctl.py`-Aufrufe aus `src/simulation/` ausführen, alle
ML-Aufrufe aus `src/ml/` (relative Pfade hängen davon ab).

---

## 3. Referenz aller Python-Skripte

### `src/simulation/` — Simulationsinfrastruktur

| Datei | Läuft auf | Zweck |
|-------|-----------|-------|
| [shadowctl.py](src/simulation/shadowctl.py) | Laptop | **Hauptsteuerung.** Fernsteuerung der Simulation per SSH zum Server. Subcommands: `download-data`, `stage`, `generate`, `pull-config`, `push-config`, `simulate`, `status`, `logs`, `pull-results`, `stop`, `list`, `run` (alles in einem). |
| [generate-wf-config.py](src/simulation/generate-wf-config.py) | Laptop | Fügt Monitor- und Zimserver-Hosts in eine tornettools-Config ein, verteilt Seiten auf Ports, schreibt `schedule.json` (Besuchsplan + Klassenlabels). Implementiert Padding-, Tamaraw- und Open-World-Logik. |
| [generate-urls.py](src/simulation/generate-urls.py) | Server | Zieht zufällige Wikipedia-Artikel aus der ZIM-Datei und schreibt `urls.txt` (nur ASCII-sichere Artikelnamen `[A-Za-z0-9_.-]`). |
| [zimsrv.py](src/simulation/zimsrv.py) | in Shadow | Minimaler HTTP-Server, der **eine** Wikipedia-ZIM-Datei ausliefert (libzim-Bindings). Ersetzt zimply/kiwix-serve (Kompatibilitätsprobleme). Eine Instanz pro Port/Seite. |
| [newnym.py](src/simulation/newnym.py) | in Shadow | Sendet `SIGNAL NEWNYM` an den Tor-Control-Port → frischer Circuit zwischen Besuchen (Circuit-Isolation). |
| [perfmon.py](src/simulation/perfmon.py) | Server | Eigenständiger Ressourcen-Logger (CPU, RAM, Disk, Netz) während der Simulation. Args: `--interval`, `--log-dir`, `--mount`. Schreibt nach `perfmon-logs/`. |

### `src/ml/` — Datenkonvertierung, Training, Auswertung

| Datei | Zweck | Wichtigste Argumente |
|-------|-------|----------------------|
| [pcap_to_npz.py](src/ml/pcap_to_npz.py) | **Kernkonvertierung.** Shadow-pcaps + `schedule.json` → WFlib `.npz` (Richtungssequenzen ±1, 5000 Werte/Sample). Labels aus dem Zielport im Schedule. | `--schedule`, `--shadow-data`, `--output` |
| [explainwf_to_npz.py](src/ml/explainwf_to_npz.py) | Konvertiert die Cell-Traces (GWF-Format) aus Jansen & Wails 2023 nach WFlib `.npz` (für Vergleichsläufe). | `--input`, `--output` |
| [pcap_overhead.py](src/ml/pcap_overhead.py) | Misst pro Besuch Bytes/Pakete je Richtung aus Monitor-pcaps → **Defense-Overhead**. Optional Vergleich gegen Baseline, CSV-Export. | `--schedule`, `--shadow-data`, `--baseline-schedule`, `--baseline-shadow-data`, `--csv` |
| [correlation.py](src/ml/correlation.py) | **Traffic-Correlation-Angriff.** Liest Guard/Monitor- + Exit-Relay-pcaps, bint Paket-Timestamps (100 ms), berechnet Pearson/Cosine/Cross-Correlation, erzeugt ROC-Kurven + AUC. | `--schedule`, `--shadow-data`, `--output`, `-v` |
| [report.py](src/ml/report.py) | Erzeugt aus einem fertigen Experiment eine CSV-Zeile für `ExperimentLogs.csv` (oder Markdown-Tabelle). | `--experiment`/`-e`, `--dataset`/`-d`, `--all`, `--header`, `--markdown` |
| [plot_confusion.py](src/ml/plot_confusion.py) | Confusion-Matrix-Heatmaps aus trainierten WFlib-Modellen. Einzeln, Vergleich (mehrere `--dataset`) oder Differenz (`--diff`). | `--dataset …`, `--labels …`, `--diff`, `--output`, `--device` |
| [plot_results.py](src/ml/plot_results.py) | Generiert die Thesis-Ergebnis-Charts (Padding-Vergleich, Accuracy-vs-Pages …) aus `ExperimentLogs.csv`. | `--csv`, `--output` |
| [plot_perfmon.py](src/ml/plot_perfmon.py) | Visualisiert die Server-Ressourcennutzung aus den perfmon/dstat-Logs. | `--logs`, `--output` |
| [export_perfmon_csv.py](src/ml/export_perfmon_csv.py) | Downsampled die perfmon-Telemetrie auf kleine CSVs für pgfplots in der Thesis. | `--logs`, `--output`, `--samples` |

### Shell-Skripte

| Datei | Zweck |
|-------|-------|
| [src/simulation/setup-wf-server.sh](src/simulation/setup-wf-server.sh) | Einmaliges Server-Setup. Phasen: `build` (wget2), `copy` (libzim + Helper-Skripte), `urls [N]`, `wfdef` (WFDefProxy/Go), `wfdef-cert` (Tamaraw-Bridge-Cert). |
| [src/ml/run_df.sh](src/ml/run_df.sh) | End-to-end: convert → split → train (DF) → test in einem Aufruf. |

---

## 4. Setup (lokal + Server)

### 4.1 Lokales Environment

```bash
cd src/ml
python3 -m venv venv
source venv/bin/activate            # bash/zsh; fish: source venv/bin/activate.fish

pip install numpy torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install tqdm pandas scikit-learn einops timm pytorch-metric-learning captum pyyaml dpkt
pip install -e wflib/
```

> Ohne Aktivierung kann man die venv-Python direkt aufrufen:
> `./venv/bin/python3 script.py`.

### 4.2 Server-Setup (einmalig)

Server: `shadowsrv-001.prod.projects.ls.eee.intern` (32 Kerne, 126 GB RAM, 156 GB Disk).

**a) Build-Abhängigkeiten (manuell, braucht TTY für sudo):**

```bash
ssh projectadmin@shadowsrv-001.prod.projects.ls.eee.intern
# auf dem Server, in EINER Zeile einfügen:
sudo apt-get update && sudo apt-get install -y git autoconf automake libtool libtool-bin pkg-config libgnutls28-dev libpcre2-dev flex texinfo gettext autopoint libnghttp2-dev libbrotli-dev libzstd-dev lzip
exit
```

**b) wget2 bauen + Helper-Skripte kopieren (automatisiert vom Laptop):**

```bash
bash src/simulation/setup-wf-server.sh build   # wget2 mit SOCKS-Patch
bash src/simulation/setup-wf-server.sh copy    # libzim + newnym.py/zimsrv.py/generate-urls.py
```

**c) Wikipedia-ZIM auf den Server laden:**

```bash
ssh projectadmin@shadowsrv-001.prod.projects.ls.eee.intern
mkdir -p ~/wikidata && cd ~/wikidata
wget https://dumps.wikimedia.org/other/kiwix/zim/wikipedia/wikipedia_en_simple_all_maxi_2026-02.zim
mv wikipedia_en_simple_all_maxi_2026-02.zim wikipedia_en_all_maxi.zim   # stabiler Pfad
exit
```

> ZIM-Snapshots rotieren. Bei 404 die aktuelle Liste unter
> <https://dumps.wikimedia.org/other/kiwix/zim/wikipedia/> prüfen und das Datum anpassen.

**d) URL-Liste erzeugen:**

```bash
bash src/simulation/setup-wf-server.sh urls 80   # 80 Seiten ab Port 8000
```

**e) (Optional) Tamaraw-Bridge vorbereiten:**

```bash
bash src/simulation/setup-wf-server.sh wfdef        # Go + WFDefProxy bauen
bash src/simulation/setup-wf-server.sh wfdef-cert   # Bridge-Cert → conf/tamaraw_cert.txt
```

### 4.3 Tor-Metrikdaten stagen (einmal pro Tor-Monat)

```bash
cd src/simulation
python3 shadowctl.py download-data --month 2025-01
python3 shadowctl.py stage         --month 2025-01
```

---

## 5. Ein Experiment durchführen (Schritt für Schritt)

Alles aus `src/simulation/` mit aktivierter venv.

### 5.1 Simulation starten

```bash
cd src/simulation
source ../ml/venv/bin/activate

# Baseline, 20 Seiten, 80 Besuche, 20 Monitore, Padding aus:
python3 shadowctl.py run exp-baseline-20 \
    --pages 20 --visits 80 --monitors 20 --padding off
```

Wichtigste `run`-Flags (Defaults in Klammern):

| Flag | Bedeutung |
|------|-----------|
| `--pages N` (5) | Anzahl Zielseiten = Anzahl Klassen |
| `--visits N` (50) | Besuche pro Seite (Trainingssamples/Klasse; DF braucht ≥80) |
| `--monitors N` (20) | Anzahl Monitor-Hosts (parallele Captures) |
| `--padding {off,on,reduced}` | Tor Circuit Padding |
| `--defense {none,tamaraw}` | Tamaraw via PT-Bridge (orthogonal zu `--padding`) |
| `--open-world` | Open-World: `--monitored-pages` (80) voll, Rest `--unmonitored-visits` (10) |
| `--correlation` | zusätzlich Exit-Relay-pcaps für den Correlation-Angriff |
| `--scale` (0.01) | Netzgrösse (79 Relays bei 0.01) |

### 5.2 Fortschritt prüfen

```bash
python3 shadowctl.py status --name exp-baseline-20
python3 shadowctl.py logs   --name exp-baseline-20 -f      # live
```

### 5.3 Ergebnisse holen & konvertieren

Sobald `status` `COMPLETED` zeigt:

```bash
python3 shadowctl.py pull-results --name exp-baseline-20

cd ../ml && source venv/bin/activate
python3 pcap_to_npz.py \
    --schedule    ../simulation/exp-baseline-20/shadow.config.schedule.json \
    --shadow-data ../simulation/exp-baseline-20/results/shadow.data/ \
    --output      wflib/datasets/Baseline20.npz
```

### 5.4 DF trainieren & testen

Bequem per Skript:

```bash
./run_df.sh --pcap \
    --schedule    ../simulation/exp-baseline-20/shadow.config.schedule.json \
    --shadow-data ../simulation/exp-baseline-20/results/shadow.data/ \
    --dataset Baseline20
```

Oder manuell (entspricht den Thesis-Hyperparametern):

```bash
cd wflib
python3 exp/dataset_process/dataset_split.py --dataset Baseline20
python3 -u exp/train.py --dataset Baseline20 --model DF --device cpu \
    --feature DIR --seq_len 5000 --train_epochs 30 --batch_size 128 \
    --learning_rate 2e-3 --optimizer Adamax --num_workers 0 \
    --eval_metrics Accuracy Precision Recall F1-score \
    --save_metric F1-score --save_name max_f1
python3 -u exp/test.py --dataset Baseline20 --model DF --device cpu \
    --feature DIR --seq_len 5000 --batch_size 256 --num_workers 0 \
    --eval_metrics Accuracy Precision Recall F1-score --load_name max_f1
```

### 5.5 Ergebnis in den Tracker schreiben

```bash
cd src/ml
python3 report.py -e exp-baseline-20 -d Baseline20 >> ../../ExperimentLogs.csv
```

---

## 6. Auswertung & Plots

```bash
cd src/ml && source venv/bin/activate

# Confusion-Matrix eines Modells (oder Vergleich mehrerer Datensätze):
python3 plot_confusion.py --dataset Baseline20 --output ../../confusion_baseline20.pdf
python3 plot_confusion.py --dataset Baseline20 Padding20 --labels OFF ON \
    --output ../../confusion_comparison_20.pdf

# Alle Thesis-Ergebnis-Charts aus ExperimentLogs.csv:
python3 plot_results.py

# Defense-Overhead (z. B. Tamaraw vs. Baseline):
python3 pcap_overhead.py \
    --schedule    ../simulation/exp-tamaraw-20/shadow.config.schedule.json \
    --shadow-data ../simulation/exp-tamaraw-20/results/shadow.data/ \
    --baseline-schedule    ../simulation/exp-baseline-20/shadow.config.schedule.json \
    --baseline-shadow-data ../simulation/exp-baseline-20/results/shadow.data/

# Server-Ressourcen während der Läufe:
python3 plot_perfmon.py
python3 export_perfmon_csv.py        # kleine CSVs für pgfplots
```

Den Correlation-Angriff (separater `--correlation`-Lauf nötig) sowie die
Tamaraw-Details beschreibt [documentation.md](documentation.md).

---

## 7. Experimente weiterführen / erweitern

Anknüpfungspunkte für Folgearbeiten:

- **Correlation-Angriff end-to-end auswerten.** `correlation.py` ist gebaut,
  aber laut Projektstand nie vollständig durchgelaufen. Einen `--correlation`-Lauf
  starten und `correlation.py` auf die Ergebnisse anwenden
  (siehe [documentation.md](documentation.md), Abschnitt Traffic Correlation).
- **Weitere Defenses.** Neben `--padding` und `--defense tamaraw` lassen sich in
  [generate-wf-config.py](src/simulation/generate-wf-config.py) zusätzliche
  PT-basierte Defenses (z. B. WTF-PAD-Varianten) einhängen.
- **Andere Klassifikatoren.** WFlib bringt neben DF weitere Modelle (Tik-Tok,
  RF, Var-CNN …) mit. In `run_df.sh` bzw. `train.py` `--model` ändern.
- **Grösserer Massstab / Open-World.** `--scale` und `--open-world` erhöhen
  Realismus, stossen aber an die RAM-Grenze (siehe unten).
- **Timing-Features.** Aktuell nutzt DF nur Richtung (`--feature DIR`).
  Mit Timing-Features (`pcap_to_npz.py` liefert Timestamps mit) liessen sich
  zeitbasierte Defenses schärfer untersuchen.

Neue Skripte sollten dem bestehenden Muster folgen (argparse mit Modul-Docstring,
relative Pfade zu `src/simulation/<exp>/...`) und in der Tabelle in
[Abschnitt 3](#3-referenz-aller-python-skripte) ergänzt werden.

---

## 8. Bekannte Einschränkungen

- **Disk:** 156 GB füllen sich schnell mit pcaps. `--guard-pcap-relays` klein
  halten, alte `shadow.data/` nach `pull-results` löschen.
- **RAM:** 126 GB limitieren auf ~300 simulierte Hosts. Open-World mit 580
  Seiten verursacht OOM.
- **Shadow-pcaps** nutzen Linktyp 101 (raw IP), nicht Ethernet; `eth0.pcap`
  statt `lo.pcap` verwenden.
- **URL-Whitelist:** nur `[A-Za-z0-9_.-]` in Artikelnamen, sonst bricht Shadows
  YAML-Parser oder die HTTP-URL.
- **DF-Datenbedarf:** ≥80 Trainingssamples pro Klasse für sinnvolle Accuracy.

Vollständige Liste der Config-Quirks in [CLAUDE.md](CLAUDE.md) → "Known Issues".

---

## 9. Bisherige Ergebnisse

Quelle der Wahrheit ist [ExperimentLogs.csv](ExperimentLogs.csv). Auszug
(Closed-World, sofern nicht anders vermerkt):

| Experiment | Seiten | Padding | Accuracy | F1 |
|-----------|--------|---------|----------|-----|
| exp-baseline-20 | 20 | OFF | 92.7% | 92.7% |
| exp-padding-20 | 20 | ON | 83.3% | 82.8% |
| exp-reduced-20 | 20 | Reduced | 86.7% | 86.3% |
| exp-baseline-80 | 80 | OFF | 82.4% | 81.4% |
| exp-padding-80 | 80 | ON | 78.6% | 76.9% |
| exp-openworld | 280 (80 mon.) | OFF | 68.3% | 69.8% |
| exp-tamaraw-20-v2 | 20 | Tamaraw | 39.3% | 38.6% |
| exp-tamaraw-80 | 80 | Tamaraw | 31.6% | 29.2% |

Kernbefund: Circuit Padding senkt die DF-Accuracy moderat (~9 pp bei 20 Seiten),
Tamaraw deutlich stärker (auf ~39 %), bleibt aber über der Zufallsbasis.
Interpretation und Open-World-Besonderheiten in [CLAUDE.md](CLAUDE.md).
