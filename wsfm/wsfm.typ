//  WSFM Forschungsskizze – HSLU Template
//  Compile with: typst compile forschungsskizze.typ
//  Watch mode:   typst watch forschungsskizze.typ


// --- CONFIGURATION --------------------------------------------------------
#let author-name = "Oliver NACHNAME"
#let module-name = "Wissenschaftliches Schreiben & Forschungsmethodik (WSFM)"
#let semester = "HS 2025"
#let submission-date = "20. Februar 2026"
#let thesis-title = "Website Fingerprinting im Tor-Netzwerk: Reproduktion und Evaluation unter simulierten Laborbedingungen"
#let supervisor = "Dr. Radwan Eskhita"
#let group = "Gruppe 2"


// --- PAGE & TEXT SETUP ----------------------------------------------------
#set text(
  font: "New Computer Modern",   // classic LaTeX look — alternatives: "Linux Libertine", "Source Serif Pro"
  size: 12pt,
  lang: "en",                    // change to "de" if writing in German
)

#set page(
  paper: "a4",
  margin: (top: 2.5cm, bottom: 2.5cm, left: 3cm, right: 3cm),
)

#set par(
  justify: true,
  leading: 0.65em,
  first-line-indent: 0em,        // no indent — change to 1.5em for traditional style
)

// Spacing between paragraphs
#show par: set block(spacing: 0.8em)

// --- HEADING STYLES -------------------------------------------------------
#set heading(numbering: "1.1")

#show heading.where(level: 1): it => {
  v(1.5em)
  text(size: 16pt, weight: "bold")[
    #if it.numbering != none {
      counter(heading).display()
      h(0.5em)
    }
    #it.body
  ]
  v(1em)
}

#show heading.where(level: 2): it => {
  v(1em)
  text(size: 13pt, weight: "bold")[
    #if it.numbering != none {
      counter(heading).display()
      h(0.4em)
    }
    #it.body
  ]
  v(0.6em)
}


// --- TITLE PAGE (no page number) ------------------------------------------
#set page(numbering: none)

#align(center)[
  // Uncomment and adjust path if you have the HSLU logo:
  // #image("hslu-logo.png", width: 6cm)
  // #v(1cm)

  #text(size: 11pt)[
    Hochschule Luzern – Informatik \
    #module-name \
    #semester
  ]

  #v(4cm)

  #text(size: 20pt, weight: "bold")[
    Forschungsskizze
  ]

  #v(0.5cm)

  #text(size: 14pt)[
    #thesis-title
  ]

  #v(3cm)

  #text(size: 12pt)[
    #author-name \
    #group
  ]

  #v(1cm)

  #text(size: 12pt)[
    Betreuer: #supervisor
  ]

  #v(1fr)

  #text(size: 12pt)[
    #submission-date
  ]
]


// --- TABLE OF CONTENTS ----------------------------------------------------
#pagebreak()
#outline(title: "Contents", depth: 2)


// --- MAIN CONTENT (page numbering starts here) ----------------------------
#pagebreak()
#set page(numbering: "1")
#counter(page).update(1)


// ==========================================================================
//  SECTION 1: Background, Problem Statement, Objectives
//  Target: ~1,500 characters (incl. spaces)
// ==========================================================================

= Background, Problem Statement, and Objectives

// TODO: Write in your own words — do NOT copy the Aufgabenstellung!
// Tip: Check character count with `wc -m` or an online tool.

#lorem(80)


// ==========================================================================
//  SECTION 2: Research Questions and Methods
//  Target: ~1,500 characters (incl. spaces)
// ==========================================================================

= Research Questions and Methods

// TODO: State each research question, then describe and justify the method.

== Research Question 1

#lorem(40)

== Research Question 2

#lorem(40)

== Research Question 3

#lorem(40)


// ==========================================================================
//  SECTION 3: Personal Reflection
//  Target: ~1,000 characters (incl. spaces)
// ==========================================================================

= Personal Reflection

// TODO: Honest assessment — challenges, limitations, what you'd do differently.

#lorem(60)


// ==========================================================================
//  SECTION 4: Literature Review
//  Target: ~2,000–3,000 characters (incl. spaces)
//  Requirements: min. 3 sources (min. 1 methods, min. 1 domain)
// ==========================================================================

= Literature Review

// TODO: Summarize each source and explain its relevance to your work.
// Remember: correct APA7 in-text citations!

== Deep Fingerprinting (Sirinam et al., 2018)

// Domain literature — the core WF attack you are reproducing
#lorem(60)

== Data-Explainable Website Fingerprinting (Jansen et al., 2023)

// Domain literature — Shadow-based WF methodology
#lorem(60)

== Research Methods Literature

// Methods literature — e.g., experimental research design, network simulation methodology
#lorem(60)


// ==========================================================================
//  BIBLIOGRAPHY (APA7)
// ==========================================================================

// Option A: Use a .bib file (recommended)
// Create a file called "references.bib" with your BibTeX entries and uncomment:
// #bibliography("references.bib", style: "apa")

// Option B: Manual bibliography (if you don't want to use BibTeX)
#pagebreak()
#heading(numbering: none)[References]

// TODO: Replace with your actual references in APA7 format.
// These are examples:

Sirinam, P., Imani, M., Juarez, M., & Wright, M. (2018). Deep fingerprinting: Undermining website fingerprinting defenses with deep learning. _Proceedings of the 2018 ACM SIGSAC Conference on Computer and Communications Security_, 1928–1943. https://doi.org/10.1145/3243734.3243768

#v(0.8em)

Jansen, R., Wails, R., & Johnson, A. (2023). Data-explainable website fingerprinting with network simulation. _Proceedings on Privacy Enhancing Technologies_, 2023(1), 1–20.

#v(0.8em)

// TODO: Add your methods literature source here


// ==========================================================================
//  APPENDIX: Aufgabenstellung
// ==========================================================================

#pagebreak()
#heading(numbering: none)[Appendix: Aufgabenstellung]
