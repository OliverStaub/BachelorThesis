# Praktische De-Anonymisierung im Tor-Netzwerk: Timing-Leaks, Traffic-Korrelation und Website-Fingerprinting unter Laborbedingungen

## Ausgangslage und Problemstellung

Tor gilt als sicher, aber theoretische Studien zeigen, dass Timing-Analysen und Traffic-Korrelationen Nutzer deanonymisieren können. Praktische Untersuchungen fehlen, besonders unter kontrollierten, lokalen Bedingungen.

**Forschungsfragen:**

- Welche Muster verraten Nutzer trotz Tor?
- Lassen sich Website-Fingerprinting-Angriffe lokal und ohne externe Infrastruktur reproduzieren?
- Wie effektiv sind Abwehrmassnahmen wie Circuit Padding oder Dummy Traffic?

**Innovation:** Untersuchung erfolgt komplett auf lokalem Test-Setup, kein Zugriff auf reale Exit-Nodes, keine Kosten.

## Ziel der Arbeit und erwartete Resultate

- **Aufbau eines lokalen Tor-Testnetzwerks** — Tor-Instances auf einem oder mehreren Rechnern simulieren (Guard, Middle, Exit). Nutzung von Docker-Containern oder virtuellen Maschinen (VirtualBox/VMware) für isolierte Experimente.
- **Traffic-Analyse-Framework entwickeln** — Capture von Metadaten: Paketgrössen, Richtungen, Timestamps. Keine Entschlüsselung von Inhalten.
- **Simulation von Timing- und Korrelationsangriffen** — Statistical Disclosure Attacks und einfache Traffic-Korrelation. Evaluation unter kontrollierten Bedingungen, mehrere parallele Clients.
- **Website-Fingerprinting lokal testen** — Auswahl von 20–50 Webseiten in lokaler Umgebung oder über Tor-Testnetz. ML-Modelle: einfache CNNs oder RNNs, Training auf lokal generierten Packet-Sequences.
- **Evaluation von Gegenmassnahmen** — Traffic-Padding-Tests: Messen von Angriffsresistenz vs. Performance.
- **Ethische Dokumentation** — Kein Zugriff auf externe Nutzer.

## Gewünschte Methoden, Vorgehen

| Phase | Beschreibung |
|-------|-------------|
| **Phase 1: Lokales Tor-Testnetz** | Docker oder VM-Setup für Guard, Middle, Exit. Monitoring: Wireshark/tcpdump für Metadaten. |
| **Phase 2: Traffic-Generierung** | Lokaler Client simuliert Webseitenaufrufe über Test-Tor-Circuits. Paketgrössen, Timing, Richtungswechsel aufzeichnen. |
| **Phase 3: Analyse** | Timing-Analyse, Traffic-Korrelation. Website-Fingerprinting mit lokalem ML-Training. |
| **Phase 4: Gegenmassnahmen** | Circuit Padding, Dummy-Traffic, Pluggable Transports testen. Vergleich der Wirksamkeit: Attack Success Rate vs. Overhead. |
| **Phase 5: Dokumentation** | Ergebnisse, Empfehlungen, ethische Reflexion. |

## Kreativität, Varianten, Innovation

- **Variante A:** ML-Modelle nur auf Metadaten trainieren, ohne reale Webseiten-IPs — vollständig lokal und reproduzierbar.
- **Variante B:** Erweiterung durch verschiedene Tor-Konfigurationen: unterschiedliche Circuit-Längen, Padding-Optionen.
- **Variante C:** Hardware-nahe Messungen mit Raspberry Pi (lokal) für Timing-Angriffe simulieren.

> **Hinweis:** Externen VPS nur wenn Budget erlaubt.

## Sonstige Bemerkungen (Anforderungen, Vorkenntnisse)

Linux, Netzwerkprotokolle, Python (Scapy, Pandas), Grundkenntnisse ML