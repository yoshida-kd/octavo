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

## 1. Introduction

<!-- octavo:example start — how citations are written: `@<key>` in text and
     `[@<key>; @<key2>]` in parentheses. For the possessive ("Yamada's (2020)")
     pass the key to \poscite, as the sentence below does.
     The bibliography is built from literature.bib (Zotero owns it). -->
@yamada2020 argued that … The same point is made elsewhere [@tanaka2019].
This paper follows \poscite{yamada2020} framework.

<!-- octavo:example end -->

## 2. Analysis

<!-- octavo:example start — numbers and cross-references. Numbers are not typed:
     register them with `ov_value()` in the .qmd and call them as `{{name}}`
     (`{{coef_x:.2f}}` sets the digits). Writing "Section 1" and "Figure 1"
     makes links in Typst / LaTeX ("Table 1" does once an external table is in
     table_map; Word always keeps plain text). Until you run the analysis these
     are octavo init's placeholders, i.e. fake. -->
As stated in Section 1, the sample has {{n_obs}} cases. The coefficient on
x is {{coef_x}} (*p* {{p_x}}). Table 1 reports descriptive
statistics and Figure 1 the trend.

<!-- octavo:example end -->

<!-- octavo:example start — how a table and a figure look. The numbers are fake -->
**Table 1. Descriptive statistics**

| Variable | Mean | SD |
|---|---|---|
| x | 1.2 | 0.3 |
| y | 3.4 | 0.8 |

![](../../figures/fig1_trend.png)

**Figure 1.** Trend

<!-- octavo:example end -->

## 3. Conclusion

## References
