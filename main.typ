// --------------------------------------------------------------------------
//  DOCUMENT INFORMATION (edit these)
// --------------------------------------------------------------------------

#let thesis-language = "en"
#let author-name = "Oliver TODO"               // TODO
#let author-city = "Zürich (Switzerland)"
#let thesis-title = "Practical De-Anonymization in the Tor Network"
#let thesis-subtitle = "Timing Leaks, Traffic Correlation, and Website Fingerprinting"
#let thesis-year = "2026"
#let defense-date = "TODO"                      // TODO
#let defense-location = "Rotkreuz"
#let external-expert = "TODO"                   // TODO
#let industry-partner = "TODO"                  // TODO — or "none"
#let study-program = "Information & Cyber Security"
#let supervisor = "TODO"                        // TODO
#let dean = "TODO"                              // TODO

#let jury-members = (
  "Prof. Dr. Name Surname from Lucerne University of Applied Sciences and Arts, Switzerland (President of the Jury)",
  "Prof. Dr. Name Surname from Lucerne University of Applied Sciences and Arts, Switzerland (Thesis Supervisor)",
  "Prof. Dr. Name Surname from Lucerne University of Applied Sciences and Arts, Switzerland (External Expert)",
)


// --------------------------------------------------------------------------
//  FONT & PAGE SETUP
// --------------------------------------------------------------------------

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
)

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
//  ACRONYMS (expand as needed)
// --------------------------------------------------------------------------

#let acronyms = (
  "hslu": ("HSLU", "Lucerne University of Applied Sciences and Arts"),
  "tor": ("Tor", "The Onion Router"),
  "wf": ("WF", "Website Fingerprinting"),
  "isp": ("ISP", "Internet Service Provider"),
  "nn": ("NN", "Neural Network"),
  "ids": ("IDS", "Intrusion Detection System"),
)

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


// ==========================================================================
//  FRONT MATTER (no page numbers in header; Roman numeral counting optional)
// ==========================================================================

#set page(numbering: none)

#align(center)[
  // TODO: Uncomment and point to actual HSLU logo
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
  #text(size: 14pt)[Bachelor Thesis]

  #v(0.5cm)
  #text(size: 12pt)[Study Program: #study-program]

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
//  I  — ABSTRACT
// --------------------------------------------------------------------------

#pagebreak()
#heading(numbering: none)[Abstract]

// TODO: Write your abstract here
The content of your thesis in brief.


// --------------------------------------------------------------------------
//  II — TABLE OF CONTENTS  +  Lists
// --------------------------------------------------------------------------

#pagebreak()
#outline(title: "Contents", depth: 2)


// ==========================================================================
//  MAIN CONTENT — Arabic page numbering starts at 1
// ==========================================================================

#set page(numbering: "1")
#counter(page).update(1)


// ══════════════════════════════════════════════════════════════════════════
//  1  Problem Statement, Research Questions, and Vision
// ══════════════════════════════════════════════════════════════════════════

= Problem Statement, Research Questions, and Vision

// TODO: What goals and research questions does the project pursue?
// State the significance, impact, and relevance for all stakeholders.
// Include a reference to the task description in the appendix.

== Problem Statement

The Tor network is widely considered secure, yet theoretical studies demonstrate that timing analyses and traffic correlation attacks can compromise user anonymity. However, practical investigations under controlled, local conditions remain scarce.

== Research Questions

// Use a custom command or simple numbered list:
+ Can Website Fingerprinting attacks successfully de-anonymize Tor users in a locally simulated Shadow network?
+ To what extent do Tor's built-in circuit padding mechanisms reduce detection accuracy of such attacks?
+ What bandwidth and latency overhead do these defenses introduce?

== Vision

// TODO: Describe the overarching goal / desired outcome of the thesis.


// ══════════════════════════════════════════════════════════════════════════
//  2  State of Research
// ══════════════════════════════════════════════════════════════════════════

= State of Research

== The Tor Network
When browsing the internet, user traffic is typically encrypted through HTTPS. However, Internet Service Providers (ISPs) can still observe the IP addresses of connection attempts, thereby identifying which websites and services a user accesses. Furthermore the websites themselves can see what IP addresses are accessing them. To mitigate this visibility, several privacy-enhancing technologies have been developed, one of them being Tor.

The Tor Network is a decentralized communication service anonymizing internet traffic by encapsulating traffic in onion like encrypted layers. The traffic is then routed through three nodes which all decrypt one layer of the package. Therefore no single node learns both the origin and the destinationnd of the package. @tornews-2025

#figure(
  image("images/tor-schema.png", width: 80%),
  caption: [Overview of the Tor network architecture @sysdig-tor-2024],
) <fig-tor-schema>

The Tor Network is used by journalists, whistleblowers and activists to circumvent censorship and surveillance. However it is also used by malicious actors of all sort to evade law enforcement. @tornews-2025

As a result several techniques have been developed to de-anonymize Tor Network users. One of them is called Website Fingerprinter or WF.

In a WF attack, a passive observer — such as an ISP or a compromised entry node — analyses patterns in the encrypted traffic from the user, and compares against pre-recorded fingerprints from known webistes.@juarez2014critical. 
Some of the compared patterns include 

 such as packet sizes, timing, and direction, to infer which website a Tor user is visiting. Over the past decade, various WF approaches have been proposed, ranging from statistical classifiers to deep learning models, with varying degrees of success. This proposal aims to survey these approaches and compare them with respect to the traffic features they exploit and the classification accuracy they achieve.

This chapter reviews existing research on Tor anonymization, website fingerprinting attacks, traffic analysis techniques, and circuit padding defenses.

== WF Attack


// ══════════════════════════════════════════════════════════════════════════
//  3  Ideas and Concepts
// ══════════════════════════════════════════════════════════════════════════

= Ideas and Concepts

// TODO: How do you plan to achieve the stated goals?
// Record initial ideas, sketch solution approaches.
// If multiple paths exist, justify your chosen direction.


// ══════════════════════════════════════════════════════════════════════════
//  4  Method(s)
// ══════════════════════════════════════════════════════════════════════════

= Method(s)

// TODO: State and justify your project methodology / process model.
// Describe planned scientific methods (quantitative/qualitative).
// Reference schedules and milestones (appendix or Ch. 5).

== Phase 1: Shadow Network Setup

Tor network simulation using Shadow/tornettools, Wikipedia mirror cloning, and wget2-based client configuration.

== Phase 2: Baseline Data Collection

Packet capture and feature extraction from client nodes; training and evaluation of WF classifiers (e.g.\ Deep Fingerprinting CNN).

== Phase 3: Circuit Padding Activation

Configuration of Tor's built-in padding mechanisms at various levels and corresponding data collection.

== Phase 4: Comparison and Analysis

Comparative analysis of detection rates with and without padding, overhead measurement, and trade-off quantification.


// ══════════════════════════════════════════════════════════════════════════
//  5  Implementation
// ══════════════════════════════════════════════════════════════════════════

= Implementation

// This is the MAIN chapter!
// Implement your ideas/concepts (Ch. 3), building on the state of
// research (Ch. 2), following the chosen methods (Ch. 4).
// Document decisions, difficulties, and limitations.

== Baseline WF Attack Results

// Results without padding countermeasures.

== Circuit Padding Configuration

// Details of padding setup and data collection.


// ══════════════════════════════════════════════════════════════════════════
//  6  Validation and Evaluation
// ══════════════════════════════════════════════════════════════════════════

= Validation and Evaluation

// Validation: Does the solution do the RIGHT thing?
// Evaluation: How WELL does it meet the requirements?

== Performance Overhead

// Measurement of bandwidth and latency impacts.

== Limitations

// Discussion of Shadow simulation limitations vs. real-world scenarios.


// ══════════════════════════════════════════════════════════════════════════
//  7  Outlook
// ══════════════════════════════════════════════════════════════════════════

= Outlook

// Reflect on your own work, point out unsolved problems, and
// suggest ideas for future development.

== Ethical Considerations

Reflection on ethical aspects of the research.

== Future Work

// TODO


// ══════════════════════════════════════════════════════════════════════════
//  8  Appendices
// ══════════════════════════════════════════════════════════════════════════

= Appendices

== Task Description

// TODO: Include the signed task description (Aufgabenstellung).

== Project Management

// TODO: Project plan, milestones, time tracking.


// ══════════════════════════════════════════════════════════════════════════
//  9  Lists of Abbreviations, Figures, Tables, AI Tools, and Formulas
// ══════════════════════════════════════════════════════════════════════════

= Lists of Abbreviations, Figures, Tables, AI Tools, and Formulas

== List of Abbreviations

#for (key, value) in acronyms {
  [*#value.at(0)* — #value.at(1) \ ]
}

== List of Figures

#outline(title: none, target: figure.where(kind: image))

== List of Tables

#outline(title: none, target: figure.where(kind: table))

== AI Tools Declaration

// TODO: List all AI tools used during the thesis (e.g. ChatGPT, Claude, Copilot)
// and describe how they were used.


// ══════════════════════════════════════════════════════════════════════════
//  10  Bibliography
// ══════════════════════════════════════════════════════════════════════════

// TODO: Uncomment when you have a .bib file ready.
#show bibliography: it => {
  show heading: none
  it
}
= Bibliography
#bibliography("references.bib", style: "apa")
