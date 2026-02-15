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

When browsing the internet, user traffic is typically encrypted through HTTPS. However, Internet Service Providers (ISPs) can still observe the IP addresses of connection attempts, thereby identifying which websites and services a user accesses. Furthermore the websites themselves can see what IP addresses are accessing them. To mitigate this visibility, several privacy-enhancing technologies exist, one of them is Tor.

The Tor Network is a decentralized communication service anonymizing internet traffic by encapsulating traffic in onion like encrypted layers. The traffic is then routed through three nodes which all decrypt one layer of the package. Therefore no single node learns both the origin and the destinationnd of the package. @tornews-2025

#figure(
  image("images/tor-schema.png", width: 80%),
  caption: [Overview of the Tor network architecture @sysdig-tor-2024],
) <fig-tor-schema>

The Tor Network is used by journalists, whistleblowers and activists to circumvent censorship and surveillance. However it is also used by malicious actors of all sort to evade law enforcement. @tornews-2025

As a result several techniques have been developed to de-anonymize Tor Network users. One of them is called Website Fingerprinter or WF. T


= Research Questions and Methods

== Research Question
What traffic features do website fingerprinting attacks on Tor exploit, and how do the different approaches compare in terms of classification accuracy?





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
