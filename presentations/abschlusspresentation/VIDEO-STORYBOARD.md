# Drehbuch: Pipeline-Clips für die Schlusspräsentation

Fünf kurze Screen-Recordings, je einer pro Pipeline-Schritt. Sie ersetzen die Live-Demo, weil echte
Läufe Stunden dauern. **Tipp:** Nutze für die Aufnahmen ein bereits abgeschlossenes Experiment
(vorhandene Daten), damit nichts in Echtzeit gewartet werden muss. Wo doch gewartet wird, die Aufnahme
schneiden oder im Schnitt beschleunigen.

**Allgemein**
- Terminal gross und gut lesbar (Schrift ~16–18 pt, heller/dunkler Kontrast, Fenster ~1280×720).
- shadowctl-Befehle laufen aus `src/simulation/`, ML-Befehle aus `src/ml/` (venv aktiviert).
- Pro Clip 10–30 Sekunden anstreben. Datei als MP4 (H.264) in `abschlusspraesentation/images/videos/` ablegen.
- Nach dem Ablegen in `slides.md` den gestrichelten Platzhalter durch das vorbereitete `<video>`-Tag ersetzen.

---

## Clip 1 — `shadowctl run` → `images/videos/01-run.mp4`
**Folie:** Schritt 1 — Experiment definieren & starten
**Zeigen:** Wie ein Experiment mit einem einzigen Befehl angestossen wird.

Befehl (tippen, dann Enter):
```bash
cd src/simulation
python3 shadowctl.py run exp-demo \
  --pages 20 --visits 50 --monitors 10 --padding off
```
**Im Bild sichtbar am Ende:** die ersten Ausgabezeilen (Generierung der Config, Push auf den Server,
"simulation started" o. ä.). Sobald die Simulation läuft, **Aufnahme stoppen** (nicht warten).
**Dauer:** ~15 s.

---

## Clip 2 — `status` / `logs -f` → `images/videos/02-status.mp4`
**Folie:** Schritt 2 — Fortschritt überwachen
**Zeigen:** Statusabfrage eines laufenden oder abgeschlossenen Experiments.

```bash
python3 shadowctl.py status --name exp-demo --tail 20
python3 shadowctl.py logs   --name exp-demo -f
```
**Im Bild sichtbar:** Status (running/completed), Fortschrittszeile, ein paar Live-Logzeilen.
Bei `logs -f` nach wenigen Zeilen mit Ctrl+C abbrechen und Aufnahme stoppen.
**Dauer:** ~15–20 s.

---

## Clip 3 — `pull-results` → `images/videos/03-pull.mp4`
**Folie:** Schritt 3 — Resultate herunterladen
**Zeigen:** Download der pcaps und Logs vom Server. Am besten mit einem **fertigen** Experiment.

```bash
python3 shadowctl.py pull-results --name exp-demo
```
**Im Bild sichtbar:** rsync-/Download-Fortschritt, am Ende der lokale Zielpfad
(`exp-demo/results/shadow.data/...`). Kurz mit `ls` den Ordner zeigen.
**Dauer:** ~15 s (lange Übertragung herausschneiden).

---

## Clip 4 — Training & Test → `images/videos/04-ml.mp4`
**Folie:** Schritt 4 — pcap → npz & DF trainieren/testen
**Zeigen:** Konvertierung und DF-Klassifikation. Training über 30 Epochen dauert — **beschleunigen/schneiden**.

```bash
cd src/ml && source venv/bin/activate
bash run_df.sh --pcap \
  --schedule    ../simulation/exp-demo/shadow.config.schedule.json \
  --shadow-data ../simulation/exp-demo/results/shadow.data/ \
  --dataset     ExpDemo
```
**Im Bild sichtbar:** Konvertierungs-Logausgabe, dann der Trainings-Fortschrittsbalken (ein paar Epochen
zeigen, Rest wegschneiden), am Ende die Test-Metriken (Accuracy / Precision / Recall / F1).
**Dauer:** ~20–30 s (Epochen-Mitte herausschneiden oder Zeitraffer).

---

## Clip 5 — Report in die CSV → `images/videos/05-report.mp4`
**Folie:** Schritt 5 — Report in die ExperimentLogs.csv
**Zeigen:** Die Ergebniszeile erscheint in der CSV. Schöner Abschluss der Pipeline.

Vorher kurz die (leere) Vorlage zeigen, dann anhängen, dann das Ergebnis:
```bash
# vorher: nur die Kopfzeile / bisherige Zeilen
column -t -s, ExperimentLogs.template.csv | head

# Report-Zeile erzeugen und anhängen
python3 report.py -e exp-demo -d ExpDemo >> ../../ExperimentLogs.csv

# nachher: neue Zeile sichtbar
tail -n 1 ../../ExperimentLogs.csv
```
**Im Bild sichtbar am Ende:** die neu angehängte Zeile mit Accuracy/F1 — die Pipeline ist durchgelaufen.
**Dauer:** ~15 s.

---

### Einbau in die Folien (nach der Aufnahme)
In `slides.md` ist pro Schritt dieser auskommentierte Block vorbereitet — Platzhalter-`div` löschen und Block aktivieren:
```html
<video controls class="mt-6 mx-auto rounded-lg shadow-lg" style="max-height: 300px">
  <source src="./images/videos/01-run.mp4" type="video/mp4" />
</video>
```
