# Schlusspräsentation (Abschlusspräsentation)

Slidev-Deck für die Modulendprüfung der Bachelorarbeit
"Praktische De-Anonymisierung im Tor-Netzwerk: Einfluss von Circuit Padding auf
Website-Fingerprinting im Shadow Netzwerk Simulator".

## Starten (ausserhalb des LaTeX-Devcontainers, dort fehlt Node)

- `pnpm install`
- `pnpm dev`
- <http://localhost:3030>

Folien bearbeiten in [slides.md](./slides.md).

## Grafiken

Alle Diagramme stammen ausschliesslich aus der Bachelorarbeit (LaTeX/TikZ/pgfplots).
Sie werden aus `../figures-src/` zu SVG kompiliert und liegen unter `images/` neben `slides.md`.
Die Folien referenzieren sie relativ (`./images/...`), damit Slidev sie zuverlässig einbindet.
Neu bauen:

```bash
bash ../figures-src/build-figures.sh
```

## Pipeline-Videos

Die Platzhalter in den Pipeline-Folien erwarten kurze Clips unter `images/videos/`
(siehe [../VIDEO-STORYBOARD.md](../VIDEO-STORYBOARD.md) für das Aufnahme-Drehbuch).

## Export (Fallback für den Prüfungstermin)

```bash
pnpm export   # -> slides-export.pdf
```
