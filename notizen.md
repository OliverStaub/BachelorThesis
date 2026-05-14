1. research über correlation angriffe. eine einschätzung zu den verschiedenen 
Angriffen in der Einleitung schreiben !

2. 




15:58Claude responded: Beides, aber mit deutlichem Übergewicht auf der Forschungsseite.Beides, aber mit deutlichem Übergewicht auf der Forschungsseite. Die kurze Antwort: WF-Angriffe sind technisch real und reproduzierbar, aber dokumentierte Einsätze in freier Wildbahn sind dünn gesät.
Was man relativ sicher weiß:
In der akademischen Welt funktionieren die Angriffe — du arbeitest ja selbst mit DF und siehst F1-Werte um 83-93%. Das ist kein Papierwert, das ist messbar. Wang, Panchenko, Sirinam, Rimmer und Co. haben das über Jahre hinweg konsistent gezeigt.
Auf der praktischen Seite gibt es starke Indizien, aber wenig hartes Material:
China's GFW betreibt seit Jahren Traffic Analysis gegen Tor und obfs-Varianten. Die genauen Klassifikatoren sind nicht öffentlich, aber die Effekte (Blocking von Bridges, Probing) deuten auf flow-level fingerprinting hin, nicht zwingend WF im klassischen Sinn. Die Forschung von Fifield et al. zu GFW-Probing ist da der beste öffentliche Anker.
Russland hat ab 2021 Tor aktiv blockiert, und Berichte (u.a. von Roskomsvoboda, Tor Project) deuten auf DPI-basierte Erkennung hin. Wieder: eher Protokoll-Fingerprinting als Webseiten-Fingerprinting.
Strafverfolgung: Der bekannteste dokumentierte Fall ist „Operation Onymous" 2014, aber dort kamen vermutlich Schwachstellen in Hidden Services und nicht WF zum Einsatz. Das FBI hat mit CMU (SEI) bei Hidden-Service-Deanonymisierung kooperiert, was dem Tor Project zufolge traffic confirmation war — verwandt mit WF, aber nicht dasselbe. Mike Perrys Reaktionen darauf sind im Tor-Blog dokumentiert.
Was gegen flächendeckenden Praxiseinsatz spricht: das Base-Rate-Problem. In deinem Closed-World-Setup mit 100 Klassen ist 93% F1 stark. In der echten Welt mit Millionen möglicher Seiten kollabiert die Precision dramatisch — Juarez et al. (2014) „A Critical Evaluation of Website Fingerprinting Attacks" und Wang's Folgearbeiten haben das durchgekaut. Für gezielte Überwachung eines Verdächtigen mit bekannter Watchlist ist es brauchbar, für Mass Surveillance praktisch nicht.
Für deine Defense ist die ehrliche Einordnung: Du verteidigst gegen ein Angreifermodell, das in der Forschung gut etabliert ist und von ernstzunehmenden Gegnern wahrscheinlich gezielt eingesetzt wird, auch wenn die öffentliche Beweislage dünn ist. Das ist eine vertretbare Motivation — und genau die Art von „practical application" Frage, die Eskhita vermutlich hören will. Wenn du das im Defense nochmal aufgreifst, würde ich das Targeted-vs-Mass-Surveillance-Argument explizit machen.