Hello World!




Im Gegensatz zu Jansen soll ein WF Angriff aus Sicht eines ISP’s simuliert werden.

Phase 1: Shadow Setup
Tor-Netzwerk mit tornettools aufsetzen, Wikipedia-Mirror als Zielseiten klonen, wget2-Clients konfigurieren

Phase 2: Baseline Datenerhebung
Pcap-Captures an Client-Nodes, Feature-Extraktion (Paketgrössen, Richtungen, Timestamps), WF-Classifier (k-FP, DF) auf Baseline trainieren und evaluieren

Phase 3: Circuit Padding aktivieren
Tors built-in Padding-Mechanismen konfigurieren (verschiedene Stufen), gleiche Datenerhebung wiederholen

Phase 4: Vergleich & Analyse
Erkennungsraten mit/ohne Padding vergleichen, Overhead messen (Bandbreite, Latenz), Trade-off quantifizieren

Phase 5: Dokumentation
Ergebnisse, Limitations (Shadow vs. Real World), ethische Reflexion
