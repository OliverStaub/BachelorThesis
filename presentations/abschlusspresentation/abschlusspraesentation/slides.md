---
theme: default
title: Schlusspräsentation
layout: cover
hideInToc: true
---

# Schlusspräsentation
Praktische De-Anonymisierung im Tor-Netzwerk: Einfluss von Circuit Padding auf Website-Fingerprinting im Shadow Netzwerk Simulator

Oliver Staub  
Betreuer: Dr. Radwan Eskhita  
Experte: Enrico Senger

HSLU · Bachelorarbeit · Juni 2026


---
layout: center
hideInToc: true
---

<video controls autoplay muted playsinline class="mx-auto rounded-lg shadow-lg" style="max-height: 500px">
  <source src="./images/videos/PitchBAA.mp4" type="video/mp4" />
</video>


---
hideInToc: true
---

# Agenda

<Toc />

---

# Forschungsfrage

<div class=" mt-8">

**Forschungsfrage**

- Wie verändert sich die Erkennungsrate des **DF**-Angriffs mit unterschiedlichen **Circuit-Padding-Settings**?
- Welche **Limitationen** simulierter und laborbasierter WF-Angriffe sind in der Literatur dokumentiert, und wie sind die Ergebnisse dieser Arbeit einzuordnen?
</div>

<div class="mt-5">

**Ziele**

- Aufbau einer **Shadow-Simulationsumgebung** in einer VM von labservices.ch
- Erstellung eines **Website-Fingerprinting-Datasets**
- Durchführung eines **Deep-Fingerprinting**-(DF)-Angriffs mit dem Tool **WFlib**

</div>

---

# Motivation

<div class="grid grid-cols-2 gap-8 mt-8">

<div class="border border-gray-200 rounded-lg p-4">

**Mehrere öffentlich bekannte Angriffe auf Tor**

- z.B. aufwendige **Korrelationsangriffe**
- Cookie-Tracking
- Circuit Fingerprinting

</div>

<div class="border border-gray-200 rounded-lg p-4">

**Alternative Angriffsmöglichkeit**

- **Website-Fingerprinting** nutzt einen **lokalen, passiven** Beobachter am Eingang
- Analysiert Paketrichtungen
- Viele Untersuchungen in der wisschenschaftlichen Literatur

</div>

</div>

---

# Methodik

<div class="grid grid-cols-2 gap-8 mt-4">

<div>

**Simulation: Shadow**

- Reproduzierbare NetzwerkSimulationen
- Modellierung Tor-Netzwerk via `tornettools` (Scale 0.01)

**Szenarien**

- Closed-World: 20 und 80 Seiten
- Open-World: 80 überwachte Seiten in 280

</div>

<div>

**Datenerhebung**

- Clients besuchen Wikipedia-Seiten über Tor
- pcap-Capture an den Monitor-Hosts

**Klassifikation: Deep Fingerprinting**

- DF aus WFlib
- Vergleich der Padding-Modi: OFF · Reduced · ON · Tamaraw

</div>

</div>



---
hideInToc: true
---

# Tor Zellen vs TCP Pakete

<div class="grid grid-cols-2 gap-6 mt-15">

<div>

<img src="./images/tor_cell.svg" class="w-full" />

<div class="text-xs text-gray-500 mt-1 text-center">Aufbau einer Tor-Zelle</div>

</div>

<div>

<img src="./images/tcp_vs_cells.svg" class="w-full mt-6" />

<div class="text-xs text-gray-500 mt-1 text-center">TCP-Segmente vs. feste Tor-Zellen</div>

</div>

</div>

<div class="text-sm opacity-80 mt-4 text-center">
Tor sendet Daten in <b>fixen Zellen</b>. Inhalt und Länge sind verschleiert, aber <b>Richtung und Zeitpunkt</b> der Pakete bleiben beobachtbar.
</div>


---
hideInToc: true
---

# Versuchsaufbau im Shadow-Simulator

<img src="./images/ShadowSetup.png" class="h-90 mx-auto mt-4" />

<div class="text-xs text-gray-500 mt-2 text-right">Eigene Darstellung (Bachelorarbeit, Kap. 5)</div>


---
hideInToc: true
---

# Beispiel: generierte Shadow-Konfiguration

```yaml {all}
monitor0:
  bandwidth_down: 100 megabit
  bandwidth_up: 100 megabit
  host_options:
    pcap_enabled: true
    pcap_capture_size: 65535 B
  processes:
  - path: ~/.local/bin/tor
    args: --defaults-torrc torrc-defaults -f torrc
    start_time: 240
    expected_final_state: running
  - path: /home/projectadmin/wget2_noinstall
    args: --page-requisites --max-threads=30 ...
          http://129.114.108.192:8000/Eurovision_Song_Contest_2018
    start_time: 1200
  - path: /usr/bin/python3
    args: /home/projectadmin/newnym.py
    start_time: 1229
  - path: /home/projectadmin/wget2_noinstall
    args: --page-requisites --max-threads=30 ...
          http://129.114.108.192:8010/Ionizing_radiation
    start_time: 1230
```

<div class="text-xs text-gray-500 mt-1 text-right">Eigene Darstellung (Bachelorarbeit, Kap. 5, Listing 5.1)</div>

---
hideInToc: true
---

# Werkzeug: die shadowctl-Pipeline

<div class="text-sm opacity-80 mb-3">
Die Befehle in der Reihenfolge, in der wir sie ausführen, von der Idee bis zur Resultats-CSV:
</div>

```bash
# 1 · Simulation durchführen
python3 shadowctl.py run 
python3 shadowctl.py status
python3 shadowctl.py pull-results

# 2 · WF-Angriff durchführen
python3 pcap_to_npz.py  
python3 dataset_split.py
python3 train.py 
python3 test.py

# 3 · Report schreiben
python3 report.py
```

---
hideInToc: true
---

# Schritt 1 — Experiment definieren & starten

<div class="flex justify-center mt-24">
<div class="font-mono text-xl bg-gray-100 rounded-xl px-8 py-6 shadow-sm leading-relaxed">
python3 shadowctl.py run exp-demo \<br/>
&nbsp;&nbsp;--pages 20 --visits 50 --monitors 10 --padding off
</div>
</div>

<!--
Generiert die Shadow-Konfiguration, fügt Monitor- und Wikipedia-Knoten hinzu, schiebt die Config auf den Server und startet die Simulation.
-->

---
layout: center
hideInToc: true
---

<video controls autoplay muted playsinline class="mx-auto rounded-lg shadow-lg" style="max-height: 500px">
  <source src="./images/videos/01-run.mp4" type="video/mp4" />
</video>


---
hideInToc: true
---

# Schritt 2 — Fortschritt überwachen

<div class="flex justify-center mt-24">
<div class="font-mono text-xl bg-gray-100 rounded-xl px-8 py-6 shadow-sm leading-relaxed">
python3 shadowctl.py status --name exp-demo --tail 20
</div>
</div>

<!--
Zeigt, ob die Simulation läuft, abgeschlossen oder fehlgeschlagen ist, samt Fortschritt und fehlgeschlagenen Seitenabrufen.
-->

---
layout: center
hideInToc: true
---

<video controls autoplay muted playsinline class="mx-auto rounded-lg shadow-lg" style="max-height: 500px">
  <source src="./images/videos/02-status.mp4" type="video/mp4" />
</video>


---
hideInToc: true
---

# Schritt 3 — Resultate herunterladen

<div class="flex justify-center mt-24">
<div class="font-mono text-xl bg-gray-100 rounded-xl px-8 py-6 shadow-sm leading-relaxed">
python3 shadowctl.py pull-results --name exp-demo
</div>
</div>

<!--
Holt Monitor-pcaps, schedule.json und Logs vom Server auf den lokalen Rechner.
-->

---
layout: center
hideInToc: true
---

<video controls autoplay muted playsinline class="mx-auto rounded-lg shadow-lg" style="max-height: 500px">
  <source src="./images/videos/03-pull.mp4" type="video/mp4" />
</video>


---
layout: two-cols-header
hideInToc: true
---

# Datenformat: von Pcaps zu Richtungssequenzen

<img src="./images/data_pipeline.svg" class="w-full mt-3" />

<div class="text-xs text-gray-500 mt-1 col-span-2">Eigene Darstellung (Bachelorarbeit, Kap. 5)</div>

::left::

<div class="text-sm font-semibold mt-3 mb-1">ExpDemo.npz <span class="text-gray-500 font-normal">— Richtungssequenzen (X, y)</span></div>

```txt
Sample 150:  Klasse = 12  (532 Pakete)
Erste Paketrichtungen:
  +1 -1 -1 +1 -1 +1 -1 -1 +1 -1
  +1 -1 +1 -1 +1 -1 +1 +1 -1 -1
  ...
```

<div class="text-xs text-gray-500 mt-1">
+1 = ausgehend, -1 = eingehend, 5000 Werte pro Sample
</div>

---
hideInToc: true
---

# Schritt 4 — pcap → npz & DF trainieren/testen

<div class="flex justify-center mt-16">
<div class="font-mono text-lg bg-gray-100 rounded-xl px-8 py-6 shadow-sm leading-relaxed">
cd src/ml && source venv/bin/activate<br/>
bash run_df.sh --pcap \<br/>
&nbsp;&nbsp;--schedule&nbsp;&nbsp;&nbsp;../simulation/exp-demo/shadow.config.schedule.json \<br/>
&nbsp;&nbsp;--shadow-data ../simulation/exp-demo/results/shadow.data/ \<br/>
&nbsp;&nbsp;--dataset&nbsp;&nbsp;&nbsp;&nbsp;ExpDemo
</div>
</div>

<!--
Konvertiert die Pcaps, splittet in Train/Valid/Test und trainiert das DF-Netz (--feature DIR --seq_len 5000 --train_epochs 30), danach Test mit Accuracy, Precision, Recall, F1.
-->

---
layout: center
hideInToc: true
---

<video controls autoplay muted playsinline class="mx-auto rounded-lg shadow-lg" style="max-height: 500px">
  <source src="./images/videos/04-ml.mp4" type="video/mp4" />
</video>


---
hideInToc: true
---

# Schritt 5 — Report in die ExperimentLogs.csv

```bash
python3 report.py -e exp-demo -d ExpDemo >> ../../ExperimentLogs.csv
```

<table class="text-xs mx-auto mt-5">
  <thead class="border-b-2">
    <tr>
      <th class="px-3 py-1 text-left">Experiment</th>
      <th class="px-3 py-1">Pages</th>
      <th class="px-3 py-1">Padding</th>
      <th class="px-3 py-1">Samples</th>
      <th class="px-3 py-1">Accuracy</th>
      <th class="px-3 py-1">F1</th>
      <th class="px-3 py-1 text-gray-500">Baseline</th>
    </tr>
  </thead>
  <tbody>
    <tr >
      <td class="px-3 py-1">exp-demo</td>
      <td class="px-3 py-1 text-center">20</td>
      <td class="px-3 py-1 text-center">OFF</td>
      <td class="px-3 py-1 text-center">1000</td>
      <td class="px-3 py-1 text-center font-bold">67.0%</td>
      <td class="px-3 py-1 text-center">65.4%</td>
      <td class="px-3 py-1 text-center text-gray-500">5.0%</td>
    </tr>
  </tbody>
</table>

<div class="text-xs opacity-70 mt-2 text-left">
Die vollständige CSV hat 32 Spalten (Netzwerk, Stichprobe, Metriken). Vorlage: <code>ExperimentLogs.template.csv</code>
</div>

---
layout: center
hideInToc: true
---

<video controls autoplay muted playsinline class="mx-auto rounded-lg shadow-lg" style="max-height: 500px">
  <source src="./images/videos/05-report.mp4" type="video/mp4" />
</video>

<!-- 
---
hideInToc: true
---

# Kennzahlen der Klassifikation

<div class="text-sm opacity-80 mb-2">
Der DF-Klassifikator ordnet jeden Besuch einer Seite zu. Pro Klasse zählt man richtige und falsche Zuordnungen:
</div>

<div class="grid grid-cols-2 gap-10 mt-2">

<div>

<table class="text-sm mx-auto">
  <thead>
    <tr>
      <th class="px-3 py-2"></th>
      <th class="px-3 py-2">wirklich X</th>
      <th class="px-3 py-2">wirklich nicht X</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td class="px-3 py-2 font-semibold">vorhergesagt X</td>
      <td class="px-3 py-2 text-center bg-green-100">TP</td>
      <td class="px-3 py-2 text-center bg-red-100">FP</td>
    </tr>
    <tr>
      <td class="px-3 py-2 font-semibold">vorhergesagt nicht X</td>
      <td class="px-3 py-2 text-center bg-red-100">FN</td>
      <td class="px-3 py-2 text-center bg-green-100">TN</td>
    </tr>
  </tbody>
</table>

<div class="text-xs text-gray-500 mt-2 text-center">
TP / TN = richtig · FP = Fehlalarm · FN = verpasst
</div>

</div>

<div class="text-sm leading-relaxed">

**Accuracy** — Anteil aller korrekt zugeordneten Besuche  
`(TP + TN) / alle`

**Precision** — wie viele der als X erkannten wirklich X sind  
`TP / (TP + FP)`

**Recall** — wie viele der echten X erkannt werden  
`TP / (TP + FN)`

**F1** — harmonisches Mittel aus Precision und Recall  
`2 · (Precision · Recall) / (Precision + Recall)`

</div>

</div>

<div class="text-xs text-gray-500 mt-4 text-center">
Werte makro-gemittelt über alle Klassen · Random-Basis = 1 / Klassenanzahl (5 % bei 20, 1.2 % bei 80 Klassen)
</div> -->

---

# Resultate

<img src="./images/accuracy_overview.svg" class="w-6/10 mx-auto mt-1" />

<div class="text-xs text-gray-500 mt-1 text-right">Eigene Darstellung (Bachelorarbeit, Kap. 6)</div>

---
hideInToc: true
---

# Tamaraw im Vergleich: Konfusionsmatrizen

<img src="./images/confusion_off_on_tamaraw_80.svg" class="w-full mx-auto mt-6" />

<div class="text-sm opacity-80 mt-3 text-center">
Unter Circuit Padding (Mitte) bleibt die Diagonale erhalten. Unter Tamaraw (rechts) löst sie sich weitgehend auf.
</div>

<div class="text-xs text-gray-500 mt-1 text-right">Eigene Darstellung (Bachelorarbeit, Kap. 6)</div>

---
hideInToc: true
---

# Kosten-Nutzen-Verhältnis

<div class="grid grid-cols-2 gap-6 mt-2">

<div>

<img src="./images/defense_tradeoff.svg" class="w-full mt-8" />

</div>

<div>

<table class="text-sm mt-6">
  <thead class="border-b-2">
    <tr>
      <th class="px-3 py-1 text-left">Modus</th>
      <th class="px-3 py-1">Overhead</th>
      <th class="px-3 py-1">Δ Accuracy</th>
    </tr>
  </thead>
  <tbody>
    <tr><td class="px-3 py-1">Reduced</td><td class="px-3 py-1 text-center">+1.3%</td><td class="px-3 py-1 text-center">−4.9 pp</td></tr>
    <tr><td class="px-3 py-1">ON</td><td class="px-3 py-1 text-center">+3.0%</td><td class="px-3 py-1 text-center">−3.8 pp</td></tr>
    <tr><td class="px-3 py-1">Tamaraw</td><td class="px-3 py-1 text-center">+1063%</td><td class="px-3 py-1 text-center">−50.8 pp</td></tr>
  </tbody>
</table>

<div class="text-sm opacity-80 mt-4">
Circuit Padding: geringe Kosten, moderater Schutz. Tamaraw: starker Schutz, aber überproportionaler Bandbreitenaufschlag.
</div>

</div>

</div>

<div class="text-xs text-gray-500 mt-2 text-right">Eigene Darstellung (Bachelorarbeit, Kap. 6)</div>

---
hideInToc: true
---

# Ressourcen während der Simulation

<img src="./images/perfmon.svg" class="h-95 mx-auto mt-2" />

<div class="text-xs text-gray-500 mt-1 text-right">Eigene Darstellung (Bachelorarbeit, Kap. 6)</div>

---

# Fazit & Limitationen

<div class="grid grid-cols-2 gap-8 mt-6">

<div>

**Fazit**

- DF erreicht im Closed-World hohe Accuracy
- Circuit Padding senkt diese nur moderat
- Tamaraw schützt deutlich stärker
- Beitrag: reproduzierbare WF-Pipeline

</div>

<div>

**Limitationen**

- Ein Lauf pro Konfiguration, fester Seed, Netzwerk-Scale 0.01
- Homogener Korpus (Simple-English-Wikipedia), 150 Visits pro Klasse
- Closed-World ≠ Real-World (Single-Tab, nur Wikipedia)
- Simulation statt Live-Tor-Netzwerk

</div>

</div>



<!-- ---
layout: default
---

# Was das ausgerollte Circuit Padding wirklich tut

<div class="text-sm opacity-70 mb-4">
Einordnung der gemessenen Verteidigung — und warum der WF-Effekt klein ausfällt
</div>

- **Die zwei Maschinen-Paare verschleiern nur den _Setup_ client-seitiger
  Onion-Service-Circuits** — die ersten 10 Zellen, damit Intro- und
  Rendezvous-Circuits wie gewöhnliche Web-Circuits aussehen. Timing wird
  dabei nicht verschleiert.
  <span class="text-xs opacity-60">(padding-spec.txt, §3 + §3.3)</span>

- **Auf Clearnet-Circuits werden sie nicht aktiv.** Die Maschinen starten erst
  bei `INTRODUCE1` bzw. `REND_ESTABLISHED` — Zelltypen, die beim Surfen über
  Exit-Knoten (z. B. Wikipedia) nie auftreten.
  <span class="text-xs opacity-60">(§3.3.2, §3.3.3)</span>

- **Konsistent dazu in den Messungen nur ~3 % Mehrverkehr bei `ON`.** Das
  Padding greift auf diesem Verkehr faktisch nicht — daher der schwache,
  innerhalb der Streuung liegende WF-Effekt.


<div class="absolute bottom-8 right-6 text-xs opacity-50">
Quelle: github.com/torproject/torspec → padding-spec.txt · Proposal 302
</div>

<!--
PRESENTER NOTES — Belege aus padding-spec.txt (torproject/torspec):
https://github.com/torproject/torspec/blob/main/padding-spec.txt


Linie 352

1) ZWECK DER MASCHINEN — §3 (Einleitung Circuit-level padding)
   "At present, Tor uses this system to deploy two pairs of circuit padding
   machines, to obscure differences between the setup phase of client-side
   onion service circuits, up to the first 10 cells."
   -> Nur ZWEI Maschinen-Paare ausgerollt. §3.3: Service-Seite NICHT abgedeckt.

2) TIMING WIRD NICHT BERÜHRT — §3.3
   "Note that inter-arrival timing is not obfuscated by this defense."
   -> Eingriff beschränkt auf eine kurze Setup-Zellsequenz, nicht das Timing.
   Gute Antwort auf "könnte es nicht subtil doch wirken?".

3) AKTIVIERUNG NUR BEI ONION-SETUP — §3.3.2 / §3.3.3
   Intro-Maschine: Padding startet, nachdem INTRODUCE1 gesendet wurde.
   Rendezvous-Maschine: Negotiation erst nach REND_ESTABLISHED.
   -> Auf Clearnet/Exit-Circuits treten diese Zellen nie auf -> keine Aktivierung.

4) EIGENE MESSUNG — Tabelle 6.1 / Abb. 6.1
   exp-padding-80 vs. exp-baseline-80 = +3.0 % Bytes. Bei 20 Klassen 635 vs.
   638 Pakete. Mehrverkehr zu klein, um die Accuracy-Differenz (9.4 Pp bei 20
   Klassen) zu erklären -> v. a. Seed-/Pfad-Streuung.

5) REDUCED OHNE EIGENE WIRKUNG — §3.4, circpad_padding_reduced
   "only circuit padding machines marked as 'reduced'/'low overhead' will be
   used. (Currently no such machines are marked as 'reduced overhead')."
   -> circuit-level Reduced selektiert nichts -> erklärt die "Inversion".

=== WICHTIGE KLARSTELLUNG (häufige Falle) ===
Es gibt ZWEI getrennte, laut §1 "completely orthogonal" Padding-Systeme:
  - CONNECTION-level (§2): CELL_PADDING gegen Netflow-Metadaten.
    Schalter ConnectionPadding / ReducedConnectionPadding (nf_ito_*-Parameter).
    Läuft auf der Guard-Verbindung, AUCH bei Clearnet. HAT echte reduced-Werte.
  - CIRCUIT-level (§3): RELAY_COMMAND_DROP, die Onion-Setup-Maschinen.
    Schalter CircuitPadding / ReducedCircuitPadding. DAS variiert die Arbeit.
Wenn ein Prüfer sagt "reduced padding tut doch etwas": ja — aber das ist
ReducedCONNECTIONPadding (§2.5), NICHT der circuit-level-Schalter dieser Arbeit.

=== WAHRSCHEINLICHE PRÜFERFRAGE ===
"Warum verteidigt Tor dann gegen Website Fingerprinting kaum?"
Antwort: Tut es im ausgelieferten Zustand auch nicht. Das Framework (WTF-PAD,
Prop 254) KÖNNTE WF-Maschinen tragen, aber keine ist deployt, weil keine reine
Padding-Verteidigung bisher ihren Overhead rechtfertigt. Die zwei aktiven
Maschinen sind reine Circuit-Fingerprinting-Verteidigung für Onion-Setup.

=== FALLE VERMEIDEN ===
Nicht "Circuit Padding ist nur bei Onion Services aktiv" pauschal sagen.
Besser: "die aktuell AUSGEROLLTEN circuit-level Maschinen". Das Framework ist
allgemein; nur die deployten Maschinen sind onion-spezifisch.
-->

---
hideInToc: true
---

# Ausblick

<div class="grid grid-cols-2 gap-8 mt-6">

<div>

**Robustere Messung**

- Mehrere Seeds pro Konfiguration
- Grössere Netzwerk-Scale
- Heterogenerer, realistischerer Web-Korpus

</div>

<div>

**Erweiterte Fragestellungen**

- Erkennung von Tor-Verkehr als vorgelagerter Schritt
- Weitere Verteidigungen und Padding-Maschinen
- Mehr Klassen im Open-World-Setting

</div>

</div>

---
layout: cover
hideInToc: true
---

# Vielen Dank

Fragen ?
