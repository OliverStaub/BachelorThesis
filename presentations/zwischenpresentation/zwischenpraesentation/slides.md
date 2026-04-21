---
theme: default
title: Zwischenpräsentation
---

# Zwischenpräsentation

Bachelorarbeit Tor Deanonymisierung mit WF

---
hideInToc: true
---

# Agenda

<Toc />

---

# Projektplan

<img src="/images/projektplan.png" class="w-1/1 mx-auto mt-8" />

<div class="text-xs text-gray-500 mt-4 text-right">
  Eigene Darstellung
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
