---
theme: default
title: Zwischenpräsentation
layout: cover
hideInToc: true
---

# Zwischenpräsentation
Praktische De-Anonymisierung im Tor-Netzwerk: Einfluss von Circuit Padding auf Website-Fingerprinting im Shadow Netzwerk Simulator

Oliver Staub  
Betreuer: Dr. Radwan Eskhita  
Experte: Enrico Senger

HSLU · Bachelorarbeit · April 2026


---
hideInToc: true
---

# Agenda

<Toc />

---

# Motivation

<div class="grid grid-cols-2 gap-12 mt-8">

<div>

**Tor verspricht Anonymität** — Millionen Nutzer:innen verlassen sich darauf:
- Journalist:innen in autoritären Staaten
- Whistleblower
- Privatsphäre-bewusste Nutzer:innen

</div>

<div>

**Aber:** Verkehrsmuster bleiben sichtbar.

Ein passiver Beobachter zwischen Nutzer und Tor-Guard kann anhand von Paket-richtungen erkennen, **welche Website besucht wurde.**

</div>

</div>

<div class="mt-24 text-center text-xl opacity-80">
→ Website-Fingerprinting (WF)
</div>


---

# Hintergrund: Website-Fingerprinting

<div class="grid grid-cols-2 gap-8 mt-6">

<div>

**Angriffsmodell**

- Lokaler passiver Angreifer (z.B. ISP, Wifi-Betreiber)
- Beobachtet verschlüsselten Tor-Traffic
- Klassifiziert Traffic-Muster mit ML / Deep Learning

**Deep Fingerprinting (DF)**

- Sirinam et al. 2018
- >98% Accuracy im Closed-World-Setting

</div>

<div>

**Verteidigung: Circuit Padding**

- Seit Tor 0.4.1 verfügbar
- Sendet Dummy-Pakete nach definierten Mustern
- Verschleiert reale Traffic-Charakteristik

**Offene Frage**

Wie effektiv schützt Circuit Padding **in einer mit shadow simulierten Tor-Umgebung** gegen DF?

</div>

</div>

<div class="text-xs text-gray-500 mt-6 text-right">
  Vgl. Sirinam et al. (2018), Kadianakis (2021)
</div>

---

# Methodik

<div class="grid grid-cols-2 gap-8 mt-4">

<div>

**Setting: Closed-World**

- ca. 80 monitored Websites
- Mehrere Visits pro Website
- Vereinfachung gegenüber Open-World

**Simulation: Shadow**

- Diskrete Event-Simulation realer Tor-Software
- Reproduzierbar, kontrollierbar, isoliert
- Skaliertes Tor-Netzwerk via `tornettools`

</div>

<div>

**Datenerhebung**

- `wget2`-Clients besuchen Websites über Tor
- pcap-Capture an den Clients
- Konvertierung zu DF-kompatiblem Format (.npz)

**Klassifikation: Deep Fingerprinting**

- CNN aus WFLib
- Train/Valid/Test-Split
- Vergleich: **mit vs. ohne Circuit Padding**

</div>

</div>

<div class="text-xs text-gray-500 mt-4 text-right">
  Eigene Methodik
</div>

---

# Simulation Übersicht

<img src="/images/uebersicht.svg" class="w-6/10 mx-auto mt-8" />

<div class="text-xs text-gray-500 mt-4 text-right">
  Eigene Darstellung
</div>

---
layout: two-cols-header
---

# Daten Pipeline

::left::

<img src="/images/pipeline1.svg" class="w-full mt-4" />

<div class="text-xs text-gray-500 mt-4 text-right col-span-2">
  Eigene Darstellung
</div>

::right::

```txt
Sample 150:  Website class = 40  (532 packets)
First 100 packet directions:
  +1 -1 -1 +1 -1 +1 -1 -1 +1 -1
  +1 -1 +1 -1 +1 -1 +1 +1 -1 -1
  ...
```

<div class="text-xs text-gray-500 mt-4 text-right col-span-2">
  .npz Beispielinhalt
</div>

---

# WFLib Training und Evaluation

<img src="/images/pipeline2.svg" class="w-full mt-12" />

<div class="text-xs text-gray-500 mt-4 text-right col-span-2">
  Eigene Darstellung
</div>

---

# Erste Resultate

<table class="text-sm mx-auto">
  <thead class="border-b-2">
    <tr>
      <th class="px-4 py-2 text-left">Experiment</th>
      <th class="px-4 py-2">Seiten</th>
      <th class="px-4 py-2">Visits</th>
      <th class="px-4 py-2">Samples</th>
      <th class="px-4 py-2">Accuracy</th>
      <th class="px-4 py-2">F1</th>
      <th class="px-4 py-2 text-gray-500">Baseline</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td class="px-4 py-2">baseline-5</td>
      <td class="px-4 py-2 text-center">5</td>
      <td class="px-4 py-2 text-center">100</td>
      <td class="px-4 py-2 text-center">500</td>
      <td class="px-4 py-2 text-center font-bold">92.0%</td>
      <td class="px-4 py-2 text-center">92.1%</td>
      <td class="px-4 py-2 text-center text-gray-500">20.0%</td>
    </tr>
    <tr>
      <td class="px-4 py-2">baseline-20</td>
      <td class="px-4 py-2 text-center">20</td>
      <td class="px-4 py-2 text-center">150</td>
      <td class="px-4 py-2 text-center">3000</td>
      <td class="px-4 py-2 text-center font-bold">92.7%</td>
      <td class="px-4 py-2 text-center">92.7%</td>
      <td class="px-4 py-2 text-center text-gray-500">5.0%</td>
    </tr>
    <tr>
      <td class="px-4 py-2">baseline-80</td>
      <td class="px-4 py-2 text-center">80</td>
      <td class="px-4 py-2 text-center">150</td>
      <td class="px-4 py-2 text-center">12000</td>
      <td class="px-4 py-2 text-center font-bold">82.4%</td>
      <td class="px-4 py-2 text-center">81.4%</td>
      <td class="px-4 py-2 text-center text-gray-500">1.2%</td>
    </tr>
  </tbody>
</table>

<div class="mt-4 text-sm opacity-80 text-center">
  DF erreicht Accuracy deutlich über der Baseline.
</div>

<table class="text-sm mx-auto">
  <thead class="border-b-2">
    <tr>
      <th class="px-4 py-2 text-left">Padding-Modus</th>
      <th class="px-4 py-2">Accuracy</th>
      <th class="px-4 py-2">F1</th>
      <th class="px-4 py-2">Δ Accuracy</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td class="px-4 py-2 font-semibold">OFF</td>
      <td class="px-4 py-2 text-center bg-red-100 font-bold">92.7%</td>
      <td class="px-4 py-2 text-center">92.7%</td>
      <td class="px-4 py-2 text-center text-gray-400">—</td>
    </tr>
    <tr>
      <td class="px-4 py-2 font-semibold">REDUCED</td>
      <td class="px-4 py-2 text-center bg-yellow-100 font-bold">86.7%</td>
      <td class="px-4 py-2 text-center">86.3%</td>
      <td class="px-4 py-2 text-center">−6.0 pp</td>
    </tr>
    <tr>
      <td class="px-4 py-2 font-semibold">ON</td>
      <td class="px-4 py-2 text-center bg-green-100 font-bold">83.3%</td>
      <td class="px-4 py-2 text-center">82.8%</td>
      <td class="px-4 py-2 text-center">−9.4 pp</td>
    </tr>
  </tbody>
</table>

<div class="mt-4 text-sm opacity-80 text-center">
  Circuit Padding reduziert die Accuracy.
</div>

---

# Projektplan

<img src="/images/projektplan.png" class="w-1/1 mx-auto mt-8" />

<div class="text-xs text-gray-500 mt-0 text-right">
  Eigene Darstellung
</div>


---

# Learnings & Herausforderungen

<div class="grid grid-cols-2 gap-8 mt-6">

<div>

**Technisch**

- Rechenintensive Simulationen (~16h pro Run)
- Hoher Speicherplatzbedarf (pcaps, Modelle)
- Veraltete Pakete & Toolchain-Inkompatibilitäten
- Sonderzeichen in URLs brechen Capture-Pipeline

</div>

<div>

**Konzeptionell**

- Komplexität der Simulationen anfangs unterschätzt
- Closed-World ≠ Real-World:
  - Single-Tab Browsing
  - Nur Wikipedia-Seiten
  - Keine Paket-Fragmentierung
- Einordnung der Resultate erfordert Vorsicht

</div>

</div>


---
layout: cover
dragPos:
  square: 0,-520,0,0
---

# Vielen Dank

Fragen ?
