// =========================================================================
// Lucerne University of Applied Sciences and Arts
// HSLU-I: Thesis Template — Typst Version
//
// Converted from the official LaTeX template (v0.4, 2025-03-11)
// Font: Latin Modern Roman (= LaTeX's Computer Modern)
// =========================================================================


// --------------------------------------------------------------------------
//  DOCUMENT INFORMATION (edit these)
// --------------------------------------------------------------------------

#let thesis-language = "en"  // "en" or "de"
#let author-name = "Author Name"
#let author-city = "Lucerne (Switzerland)"
#let thesis-title = "Thesis Title"
#let thesis-subtitle = "subtitle"
#let thesis-year = "2024"
#let defense-date = "October 27th, 2024"
#let defense-location = "Lucerne"
#let external-expert = "Expert Name"
#let industry-partner = "Company Name"
#let supervisor = "Prof. Dr. Name Surname"
#let dean = "Prof. Dr. Name Surname"
#let acknowledgments-text = "Thanks to my family, relatives and friends for all the support given to finish this thesis."

#let jury-members = (
  "Prof. Dr. Name Surname from Lucerne University of Applied Sciences and Arts, Switzerland (President of the Jury)",
  "Prof. Dr. Name Surname from Lucerne University of Applied Sciences and Arts, Switzerland (Thesis Supervisor)",
  "Prof. Dr. Name Surname from Lucerne University of Applied Sciences and Arts, Switzerland (External Expert)",
)


// --------------------------------------------------------------------------
//  FONT & PAGE SETUP
// --------------------------------------------------------------------------

// Latin Modern Roman is the OpenType version of LaTeX's Computer Modern.
// Install it from: https://www.gust.org.pl/projects/e-foundry/latin-modern
// Fallback: "New Computer Modern" also works.
#set text(
  font: "New Computer Modern",
  size: 12pt,
  lang: if thesis-language == "de" { "de" } else { "en" },
)

#set page(
  paper: "a4",
  margin: (top: 2.5cm, bottom: 2.5cm, left: 3cm, right: 3cm),
)

#set par(
  justify: true,
  leading: 0.65em,  // similar to LaTeX's default line spacing
)

// Use Latin Modern Math for equations (matches LaTeX math rendering)
#show math.equation: set text(font: "New Computer Modern Math")

// Heading styles (approximating LaTeX book class)
#set heading(numbering: "1.1")

#show heading.where(level: 1): it => {
  pagebreak(weak: true)
  v(2em)
  text(size: 24pt, weight: "bold")[
    #if it.numbering != none {
      counter(heading).display()
      h(0.5em)
    }
    #it.body
  ]
  v(1.5em)
}

#show heading.where(level: 2): it => {
  v(1.2em)
  text(size: 17pt, weight: "bold")[
    #if it.numbering != none {
      counter(heading).display()
      h(0.4em)
    }
    #it.body
  ]
  v(0.8em)
}

#show heading.where(level: 3): it => {
  v(1em)
  text(size: 14pt, weight: "bold")[
    #if it.numbering != none {
      counter(heading).display()
      h(0.4em)
    }
    #it.body
  ]
  v(0.6em)
}


// --------------------------------------------------------------------------
//  ACRONYMS / GLOSSARY (define inline or import)
// --------------------------------------------------------------------------

// Simple acronym dictionary — expand as needed
#let acronyms = (
  "hslu": ("HSLU", "Lucerne University of Applied Sciences and Arts"),
  "cww": ("CWW", "Computing with Words"),
  "nn": ("NN", "Neural Network"),
)

// Track which acronyms have been used (first use shows long form)
#let acr-used = state("acr-used", (:))

#let acr(key) = {
  context {
    let used = acr-used.get()
    if key in used {
      acronyms.at(key).at(0)
    } else {
      acr-used.update(d => { d.insert(key, true); d })
      [#acronyms.at(key).at(1) (#acronyms.at(key).at(0))]
    }
  }
}


// --------------------------------------------------------------------------
//  TITLE PAGE
// --------------------------------------------------------------------------

// Disable page numbering for front matter initially
#set page(numbering: none)

#align(center)[
  // HSLU logo — replace with actual logo path
  // #image("figs/hslu-logo.png", width: 6cm)

  #v(1cm)

  #text(size: 11pt)[
    Lucerne University of Applied Sciences and Arts
  ]

  #v(3cm)

  #text(size: 24pt, weight: "bold")[#thesis-title]

  #v(0.5cm)

  #text(size: 14pt)[#thesis-subtitle]

  #v(2cm)

  #text(size: 14pt)[
    Bachelor Thesis
  ]

  #v(1cm)

  #text(size: 12pt)[
    #author-name \
    #author-city
  ]

  #v(2cm)

  #text(size: 12pt)[
    Defense Date: #defense-date \
    Defense Location: #defense-location
  ]

  #v(1cm)

  #text(size: 12pt)[
    Supervisor: #supervisor \
    External Expert: #external-expert \
    Industry Partner: #industry-partner
  ]

  #v(1fr)

  #text(size: 12pt)[#thesis-year]
]


// --------------------------------------------------------------------------
//  ACKNOWLEDGMENTS
// --------------------------------------------------------------------------

#pagebreak()

#heading(numbering: none)[Acknowledgments]

#acknowledgments-text


// --------------------------------------------------------------------------
//  ABSTRACT
// --------------------------------------------------------------------------

#pagebreak()

#heading(numbering: none)[Abstract]

The content of your thesis in brief.


// --------------------------------------------------------------------------
//  TABLE OF CONTENTS, LIST OF FIGURES, LIST OF TABLES
// --------------------------------------------------------------------------

#pagebreak()
#outline(title: "Contents", depth: 1)

#pagebreak()
#outline(title: "List of Figures", target: figure.where(kind: image))

#pagebreak()
#outline(title: "List of Tables", target: figure.where(kind: table))


// --------------------------------------------------------------------------
//  ACRONYM LIST
// --------------------------------------------------------------------------

#pagebreak()
#heading(numbering: none)[List of Acronyms]

#for (key, value) in acronyms {
  [*#value.at(0)* — #value.at(1) \ ]
}


// --------------------------------------------------------------------------
//  MAIN CONTENT — page numbering starts here
// --------------------------------------------------------------------------

#set page(numbering: "1")
#counter(page).update(1)

= Main Content

This is a template of #acr("hslu") and then. This section usually comprises different chapters and subchapters.

== First Section

Followed by a brief introduction, the section may comprise several subsections explaining various concepts and referring to external results.

=== First Subsection

Content may also refer to special expressions that have to be explained in a separate section. Here we also have #acr("cww") enough space to discuss the concept of #acr("nn") and so on.


// --------------------------------------------------------------------------
//  BIBLIOGRAPHY
// --------------------------------------------------------------------------

// Uses APA 7 style — change to "ieee" if you want IEEE like the LaTeX original
#bibliography("references.bib", style: "ieee")


// --------------------------------------------------------------------------
//  APPENDIX
// --------------------------------------------------------------------------

// Reset heading numbering to letters for appendix
#set heading(numbering: "A.1")
#counter(heading).update(0)

= Appendix

Additional materials go here.
