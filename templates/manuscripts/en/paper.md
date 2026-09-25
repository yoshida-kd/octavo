---
title: Title of the Paper
author: @@AUTHOR@@
date: 2026-01-01
---

<!-- octavo:example This manuscript is the template octavo new wrote. Blocks marked
     `octavo:example` are examples — delete each one, marker and all, once you've
     replaced it with your own text. octavo check reports the markers that are
     still there. The working agreements are in CLAUDE.md. -->

## Abstract

<!-- octavo:example start -->
Write the abstract here. A `## Abstract` section is split off from the body: it
becomes abstract.typ / abstract.tex for Typst and LaTeX, and the opening section
in Word.

<!-- octavo:example end -->

## Introduction {#sec-intro}

<!-- octavo:example start — how citations are written: `@<key>` in text and
     `[@<key>; @<key2>]` in parentheses. For the possessive ("Yamada's (2020)")
     pass the key to \poscite, as the sentence below does.
     The bibliography is built from literature.bib (Zotero owns it). -->
@yamada2020 argued that … The same point is made elsewhere [@tanaka2019].
This paper follows \poscite{yamada2020} framework.

<!-- octavo:example end -->

## Analysis {#sec-analysis}

<!-- octavo:example start — numbers and cross-references. Numbers are not typed:
     register them with `ov_value()` in the .qmd and call them as `{{name}}`
     (`{{coef_x:.2f}}` sets the digits). Headings carry no numbers (the
     typesetter numbers them). Label figures, tables, equations and sections
     with `{#fig-…}` `{#tbl-…}` `{#eq-…}` `{#sec-…}` and refer to them by name,
     like `@fig-trend` (typeset as "Figure 2.1", "Section 1"). Until you run the
     analysis these numbers are octavo init's placeholders, i.e. fake. -->
As stated in @sec-intro, the sample has {{n_obs}} cases. We estimate @eq-model;
the coefficient on x is {{coef_x}} (*p* {{p_x}}). @tbl-summary reports
descriptive statistics and @fig-trend the trend.

$$
y_i = \beta_0 + \beta_1 x_i + \varepsilon_i
$$ {#eq-model}

<!-- octavo:example end -->

<!-- octavo:example start — how a table and a figure are written. The table is
     what the analysis (ov_table()) wrote to tables/summary.*; this one line
     puts it here with its caption. A table you type yourself is a Markdown
     table with `: Caption {#tbl-name}` right below it -->
: Descriptive statistics {#tbl-summary}

![Trend](../../figures/trend.png){#fig-trend}

<!-- octavo:example end -->

## Conclusion {#sec-conclusion}

## References

(This section is dropped at conversion time; the bibliography is built from literature.bib.)
