//  WSFM Research Proposal – HSLU Template
//  Compile with: typst compile wsfm.typ
//  Watch mode:   typst watch wsfm.typ


// --- CONFIGURATION --------------------------------------------------------
#let author-name = "Oliver LASTNAME"
#let module-name = "Scientific Writing & Research Methods (WSFM)"
#let semester = "Fall 2025"
#let submission-date = "February 20, 2026"
#let thesis-title = "Website Fingerprinting in the Tor Network: Reproduction and Evaluation under Simulated Laboratory Conditions"
#let supervisor = ""
#let group = "Group 2"


#set text(
  font: "New Computer Modern",
  size: 12pt,
  lang: "en",                  
)

#set page(
  paper: "a4",
  margin: (top: 2.5cm, bottom: 2.5cm, left: 3cm, right: 3cm),
)

#set par(
  justify: true,
  leading: 0.65em,
  first-line-indent: 0em,
)

#show par: set par(spacing: 0.8em)
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


#set page(numbering: none)

#align(center)[
  // #image("hslu-logo.png", width: 6cm)
  // #v(1cm)

  #text(size: 11pt)[
    Lucerne University of Applied Sciences – Computer Science \
    #module-name \
    #semester
  ]

  #v(4cm)

  #text(size: 20pt, weight: "bold")[
    Research Proposal
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
    Supervisor: #supervisor
  ]

  #v(1fr)

  #text(size: 12pt)[
    #submission-date
  ]
]


#pagebreak()
#outline(title: "Contents", depth: 2)


#pagebreak()
#set page(numbering: "1")
#counter(page).update(1)


= Background, Problem Statement, and Objectives

// TODO: Write in your own words — do NOT copy the assignment!


Tor is an acronym for The Onion Router. The Onion Router is a distributed Protocol with the goal o


- vor und Nachteile aufzeigen
- Wo wird es genutzt und eingesetzt
- Probleme
- Moegliche Attack angels und so





= Research Questions and Methods

To what extent can the Deep Fingerprinting attack be reproduced in a Shadow-simulated Tor network, and how does classification accuracy compare to results reported on live Tor traffic?



= Personal Reflection

// TODO: Honest assessment — challenges, limitations, what you'd do differently.

#lorem(60)



= Literature Review

// TODO: Summarize each source and explain its relevance to your work.
// Remember: correct APA7 in-text citations!

== Deep Fingerprinting (Sirinam et al., 2018)

#lorem(60)

== Data-Explainable Website Fingerprinting (Jansen et al., 2023)

#lorem(60)

== Research Methods Literature

#lorem(60)


// ==========================================================================
//  BIBLIOGRAPHY (APA7)
// ==========================================================================

#bibliography("references.bib", style: "apa")

#pagebreak()
#heading(numbering: none)[References]


// ==========================================================================
//  APPENDIX: Assignment
// ==========================================================================

#pagebreak()
#heading(numbering: none)[Appendix: Assignment]
