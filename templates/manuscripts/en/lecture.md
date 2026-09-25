---
title: Example Lecture Notes
author: @@AUTHOR@@
date: 2026-04-10
---

<!-- octavo:example These lecture notes are the template octavo new wrote. Blocks
     marked `octavo:example` are examples — delete each one, marker and all, once
     it's yours.

     From this one file:
       octavo build @@NAME@@ --to typst          A4 handout (all sessions in one)
       octavo build @@NAME@@ --to typst-slides   slides (one deck per `#` session)
     Decks are named @@NAME@@-01, @@NAME@@-02, … in order of appearance.
     To keep a deck's name when inserting sessions, give the heading an id
     (`# Session 2: title (example) {#second}` -> @@NAME@@-second).
     Anything before the first `#` (like this) appears in the handout only. -->

# Session 1: title (example)

<!-- octavo:example start — how one session is put together -->
## Today's goals

- Make the A4 handout and the slides **from this one source**
- One `#` is one session. Its title becomes the deck's title slide; each `##` is a slide
- Use conditional blocks for what should differ

::: {.handout-only}
Handout only: blanks to fill in, longer notes.

(                                                        )
:::

::: {.slides-only}
Slides only: a figure or a short question.
:::

## Terms

- **Term A** … explanation
- **Term B** … explanation

<!-- octavo:example end -->

# Session 2: title (example)

<!-- octavo:example start -->
## An example

Following @yamada2020. The survey has {{n_obs}} respondents; @fig-trend shows
the trend.

![Trend](../figures/trend.png){#fig-trend}

## Summary and assignment

- Today's summary

::: {.handout-only}
**Assignment** Read … before next week.
:::

<!-- octavo:example end -->
