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

# Projektplan

<img src="/images/projektplan.png" class="w-1/1 mx-auto mt-8" />

<div class="text-xs text-gray-500 mt-0 text-right">
  Eigene Darstellung
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

<img src="/images/wflib.jpg" class="w-3/4 ml-auto mt-42" />

<div class="text-xs text-gray-500 mt-4 text-right col-span-2">
  Quelle: https://github.com/FIND-Lab/Website-Fingerprinting-Library
</div>

---

# WFLib Training und Evaluation

<img src="/images/pipeline2.svg" class="w-full mt-12" />

<div class="text-xs text-gray-500 mt-4 text-right col-span-2">
  Eigene Darstellung
</div>

---

# Erste Resultate

---

# Evaluation

- Closed World Szenario, stark eingeschränkt

---

# Probleme / Herausforderungen

- Sonderzeichen in URL's
- Veraltete Packages etc.

---

# Learnings

- Rechenauswändige Simulationen (16h pro Simulation)
- Speicherplatz
- Ich habe die Komplexität unterschätzt

---

# Nächste Schritte

- Weitere Simulationen, Optimierungen
- Schreiben
- Evaluation und Einordnung der Ergebnisse


---
layout: cover
dragPos:
  square: 0,-520,0,0
---

# Vielen Dank

Fragen ?
