// =====================================================================
//  Layout of an English paper (Typst)
//
//  **Hand-managed.** `octavo new paper <name>` puts it in docs/<name>/, next to
//  the manuscript. The title, authors, affiliation and date come from the top of the
//  manuscript (title, author, institute, email, date), so they need not be written
//  here. Every build copies it into
//  build/pdf/<name>/, so edit the copy under docs/. body.typ / abstract.typ /
//  appendix.typ are written by `octavo build` every time; do not edit them.
//
//  The page, headings and title block come from article.typ (written by
//  `octavo build` every time; after LaTeX's article class). To suit a journal, add
//  set / show rules after #show: octavo-article.with(…) below (say,
//  #set page(margin: 1in)), or copy it with: octavo template copy paper/article.typ
//
//    octavo build <name> --compile    # the PDF (and <name>-appendix.pdf if there is one)
//
//  The appendix is a separate PDF by default (appendix_separate: True). To put it
//  after the text instead, write appendix_separate: false in octavo.config.py or at
//  the top of the manuscript.
//
//  Citations are formatted by pandoc --citeproc with the CSL, the bibliography at
//  the end of body.typ (only with typst_citations: 'native' is the
//  #bibliography(...) below used).
//
//  The fonts come from article.typ (Libertinus Serif, with BIZ UDMincho or Noto for
//  the occasional Japanese word). `typst fonts` lists what is installed.
// =====================================================================

#import "article.typ": octavo-article, octavo-abstract, octavo-part, octavo-paper
#import "crossref.typ": octavo-crossref, octavo-appendix
// Blind review (octavo build --anonymous): article.typ leaves out the authors,
// affiliation and email (anonymous_drop_meta in octavo.config.py says which). To hide
// anything else, use #if anonymous { … } (flags.typ is rewritten on every build).
#import "flags.typ": anonymous

// Figure, table and equation numbers (a paper numbers straight through: Figure 1,
// and A1 in the appendix) and how @fig-… references read
#show: octavo-crossref
// The title, authors and so on come from the top of the manuscript; written here, they win
#show: octavo-article.with(
  // title: [A shorter title for the journal],
  // author: [Author Name],
  // counts: none,     // not to show the length (words, abstract, figures, tables) on page 1
)

#if octavo-part == "appendix" [
  #show: octavo-appendix
  #include "appendix.typ"
] else [
  #octavo-abstract(include "abstract.typ")
  #include "body.typ"
  // The appendix after the text (appendix_separate: false)
  #if not octavo-paper.appendix-separate [
    #pagebreak()
    #show: octavo-appendix
    #include "appendix.typ"
  ]
]

// ---- only with typst_citations: 'native' ------------------------------
// #pagebreak()
// #bibliography("../../../literature.bib", style: "chicago-author-date",
//               title: "References")
