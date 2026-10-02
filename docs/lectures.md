# Making lecture notes

> This is the source of the lecture-notes guide. Read it at **<https://yoshida-kd.github.io/octavo/lectures/>**. <!-- pages:skip -->

From **one Markdown file**, lecture notes give you:

| What | Contents | Where |
|---|---|---|
| A4 handout | every session in one booklet, with a cover and contents | `build/typst/<name>.pdf` |
| A deck per session | one session each; the title slide has its title and date | `build/typst-slides/<name>-slides-<session>.pdf` |
| A handout per session | the A4 handout cut by session, keeping the page numbers of the whole | `build/handouts/<name>-<session>.pdf` |
| Speaker script (if you want one) | the slides on A4 with your notes underneath | `build/typst-notes/<name>-notes-<session>.pdf` |

Everything can be done in VS Code. This page assumes VS Code; the commands are
[at the end](#from-the-command-line). For installing, and for anything beyond lecture notes
(papers, the analysis), see the [guide](https://yoshida-kd.github.io/octavo/guide/).

---

## Getting started

1. Open the sidebar with the Octavo icon on the far left. If there is no project yet,
   **New project** makes one (for lecture notes alone, lecture notes are the only part you need).
2. Under Manuscripts, **Add a manuscript…** → **Lecture notes** → a name (e.g.
   `public-policy`). `lectures/public-policy.md` is made and opened.
3. Press the **PDF button** at the top right of the editor (Open Preview). The window splits
   in three:

   | Left | Middle | Right |
   |---|---|---|
   | the manuscript | the A4 handout | the deck for the session the cursor is in |

   Every save rebuilds them. The **screen button** at the top right picks what the right
   column shows: Slides, Speaker script, or nothing.
4. Open the lecture notes in the sidebar: inside are **the sessions** (click one to jump to
   it), **Make the session handouts** and **Settings for this document**.

---

## The shape of the manuscript

```markdown
---
title: Public Policy
subtitle: Lecture notes
author: Author Name
date: today
---

Text here goes to the handout only (e.g. how the course runs).

# Session 1: What is public policy?

## Introduction

### Today's aims

- Three things to take home

## Who makes policy?

### Government and the market

Text for both the handout and the slides.

#### A smaller point

# Session 2: Government
```

- The part between the `---` lines makes the cover. `date: today` is the day it was built.
- Headings come in three levels: **`#` is a session**, **`##` a section** and **`###` one
  slide**. `####` and below are small headings inside a slide (in the A4 handout they are all
  numbered headings: 1, 1.1, 1.1.1).
- A `##` section is shown in the slides' top-left corner (a setting adds a divider slide for
  each section).
- A session without sections may skip `##`: if a session has only `##` headings, each `##` is
  one slide.
- Whatever comes before the first `#` goes into the A4 handout only.
- Separate paragraphs with a blank line. Lists use `-`; indent a nested item by **two spaces**.

---

## Splitting into sessions

### By `#` (the usual way)

With nothing else written, each `#` heading is one session. The decks are named in order:
`<name>-01`, `<name>-02`, …. To keep a name when you insert a session before it, give the
heading an id:

```markdown
# Session 2: Government {#government}
```

The second deck is then `<name>-government` (`octavo build <name>-government`; its PDF is
`<name>-slides-government.pdf`).

### With session markers

When a session does not fit one `#` (two sections in one session, a session ending
mid-section), put a **marker** at the head of each session. As soon as there is one marker,
`#` becomes an ordinary heading with nothing to do with sessions:

```markdown
::: {.session #week3 date="2026-10-14"}
:::

# Session 3: Policy and government

## Who decides?

### The cabinet

## Bureaucracy

### Staff
```

- `#week3` names the session (its deck is `<name>-week3`).
- `date` (and `subtitle`) go on the session's title slide. The title is the session's first
  heading, which moves to the title slide. The levels are as without markers (`##` a section,
  `###` a slide).
- With `title="…"` on the marker, that becomes the title and the session's first heading
  stays on the slides as a section. A slide is still a `###`: which level is a slide is
  decided from the whole of the notes, so adding markers or titles never changes it.
- A session always starts on a new page of the A4 handout too (the per-session handouts are
  cut there).
- What comes before the first marker goes into the A4 handout only (a guidance session, say).
- Once there are markers, the decks follow them, not `#`: decks made before (`<name>-01`, …)
  are removed at the next build, so only the current ones are left in `build/`.
- A session with nothing after its marker yet (next week's, written as a reminder) gets no
  deck.
- The A4 handout does not print a marker's `title` or `date`: it shows the headings as
  written. `first_section` numbers the `#` headings, not the sessions.

---

## Slide breaks and titles

Normally each `###` is one slide. Where that does not fit, add a mark. None of these affect
the A4 handout.

| To | Write |
|---|---|
| start a new slide here | the two lines `::: {.slide}` and `:::` |
| give the new slide a title | `::: {.slide title="…"}` and `:::` |
| keep a heading on the same slide | `{.same-slide}` after the heading |
| shorten a title on the slides only | `{slide-title="…"}` after the heading |
| show no title on that slide (room for a figure) | `{.no-title}` after the heading |

```markdown
### A long heading for the handout {slide-title="Short title"}

First half of the text.

::: {.slide}
:::

Second half — on a new slide titled "Short title (cont.)".

### A heading that stays on this slide {.same-slide}
```

A `::: {.slide}` with no title takes the previous slide's title plus " (cont.)". The new
slide gets a heading at the slide level (normally `###`).

**Notes for what you will say** go in `::: notes`. They appear on neither the slides nor the
handout, only in the **speaker script** (pick Speaker script for the preview's right column).
The script shows each slide as projected, shrunk, two to an A4 page, with the notes written on
that slide underneath:

```markdown
::: notes
Ask the room first; give the answer after two minutes.
:::
```

---

## Different content in the handout and the slides

Fence a part to show it in one of them only:

```markdown
::: {.handout-only}
Space for students to write in, longer explanations, footnotes.
:::

::: {.slides-only}
A big figure or one short question.
:::
```

| Mark | Shown in |
|---|---|
| `.handout-only` | the A4 handout only |
| `.slides-only` | the slides and the speaker script only |
| `.no-slides` | everything but the slides and the speaker script |

(`.slide-only` is read as `.slides-only`.) Inside a list item, indent the fence to the item's
text, and **leave a blank line before every opening `:::`** — without it pandoc does not see a
block and prints the `:::`. For a few words, `[…]{.handout-only}` works inside a line:

```markdown
- Local government employs most officials.

  ::: {.handout-only}
  - Longer explanation for the handout.
  :::

  ::: {.slides-only}
  - One line for the slide.
  :::

- Grading: [midterm and final]{.handout-only}[see the handout]{.slides-only}.
```

**Check before submitting** (or `octavo lint`) points out a `:::` that will not be read as a
block, and a mark that matches no output (a misspelt `.handouts-only`, say), which would
otherwise vanish from both without a word.

---

## Cases, questions and other numbered blocks

```markdown
::: {.question #question-why title="Why government?"}
Why is government the main actor in public policy?
:::

::: case
No label is needed if nothing refers to it.
:::
```

| Kind | Heading | Numbers |
|---|---|---|
| `case` / `question` | Case / Question | one sequence for the two (Case 1.1, Question 1.2, …) |
| `aside` / `nb` / `memo` | Aside / Note / Addendum | none |
| `definition` / `theorem` / `example` and others | Definition / Theorem / Example | a sequence of their own |

- Neither a label (`#question-why`) nor a `title` is required. `::: case` alone is numbered.
- Numbers restart at each section (`#`), and are the same in the handout and the slides.
- With a **label** such as `#question-why`, writing `@question-why` in the text prints
  "Question 1.2" and links to the block. Start a label with the kind's name.

**Show a block again** (in a review session, say). Write no text, just point at it:

```markdown
::: {.restate #question-why}
:::
```

**List them** (a list of questions at the back, say):

```markdown
::: {.list-of .question .case}
:::

::: {.list-of .titles}
:::
```

The first lists the questions and cases with their text; the second (`.titles`) lists every
numbered block as number, title and page only.

---

## Figures, tables and references

Written as in a paper; see the guide's [Writing manuscripts](https://yoshida-kd.github.io/octavo/guide/#3-writing-manuscripts)
and [Citations](https://yoshida-kd.github.io/octavo/guide/#5-citations).

```markdown
![Spending over time](../assets/figures/trend.png){#fig-trend}

As @fig-trend shows, spending rose. See @yamada2020.
```

- Figures are placed with a path relative to the manuscript (`../`, since it sits in
  `lectures/`). On a slide they shrink to fit the space left.
- A source or note under a figure or table goes in `::: {.figure-note}` + `:::` right after
  it: small type, on the same page, footnotes allowed; on a slide the figure shrinks for it.
  See the guide's [Figures](https://yoshida-kd.github.io/octavo/guide/#figures).
- A photo you took goes in `figures/` and is placed from there
  (`![…](../figures/photo.jpg)`).
- A table you make by hand: **Add a table made by hand…** under Analysis in the sidebar opens
  it as a grid.
- References go in `literature.bib` and are cited as `@key`. A session that cites something
  gets a references slide at the end; the A4 handout lists them all at the back.

---

## URLs and footnotes

```markdown
See <https://www.e-stat.go.jp/> for the data, or the [statistics portal](https://www.e-stat.go.jp/).

The number of civil servants is small.[^count] A short note can go inline.^[Like this.]

[^count]: Counted in 2024. See <https://www.jinji.go.jp/>.
```

**URLs**
- Put a URL between `<` and `>` (`<https://…>`). Without them it is printed as text, not as a
  link.
- To link some words, write `[words](URL)`. A printed handout does not show that URL, so
  use the `<URL>` form for anything students should read on paper.
- In the PDF both open in the browser when clicked (in the preview too). They are black, like
  the text.

**Footnotes**
- Put `[^name]` where the footnote goes, and `[^name]: the footnote's text` on a line of its
  own. Any name will do (`[^1]` too); the numbers are added for you.
- A short one can be written in place: `^[the footnote's text]`.
- In the A4 handout a footnote goes at the foot of its page; on the slides, at the foot of its
  slide.
- **Write the footnote's text in the same session** (just below the paragraph is best). If
  they are all gathered at the end of the file, a session's deck cannot find them and prints
  `[^name]` as it is.

---

## Headings without a number

`{.unnumbered}` (or `{-}`) on a heading leaves it unnumbered in the A4 handout, and the next
numbered one keeps counting as if it were not there. `.unlisted` also keeps it out of the
contents. The slides look the same either way.

```markdown
# Guidance {.unnumbered}

## Next week {-}

## Not in the contents {.unnumbered .unlisted}
```

---

## Appendix

`{.appendix}` on a heading makes everything after it an appendix (A, B, …; on a new page of
the A4 handout):

```markdown
# Questions and cases {.appendix}

::: {.list-of .question .case}
:::
```

---

## Changing the look

Open the lecture notes in the sidebar and use **Settings for this document**. A value you
pick is written as one line at the top of the manuscript (between the `---` lines) and
applies to those notes only. You can also write the line yourself; the names are
exactly those in the second column (a misspelt one, such as `first-section-number`, is
reported when you build and has no effect).

| Setting | Line at the top | Default | What it changes |
|---|---|---|---|
| Number of the first section | `first_section: 0` | 1 | 0 numbers a guidance session "0" (its figures "Figure 0.1") |
| New page at | `handout_pagebreak: section` | each session | `section` each `#`; `none` only at session markers |
| Body font | `handout_font: …` | BIZ UDGothic | the A4 handout's text |
| Font size | `handout_fontsize: 10.5pt` | 11pt | the A4 handout's text |
| Date format | `date_format: "%Y-%m-%d"` | April 10, 2026 | the date on the cover and the title slides |
| Aspect ratio | `typst_slides_aspect: 4-3` | 16:9 | the slides |
| Accent colour | `typst_slides_accent: none` | navy | headings and other accents on the slides; `none` for black only |
| Section name in the top-left corner | `typst_slides_running_header: false` | on | the slides' top-left corner |

The A4 handout is set after the Japanese LaTeX class jsarticle (36 lines a page, paragraphs
indented by one character).

---

## Handing out

- **The A4 handout** and **the slides**: what the preview shows is already in `build/` (see
  the table at the top of this page for where).
- **Handouts per session**: for notes with session markers they are remade in the background
  every time you save (the status bar shows "Handouts" spinning, then ✓). To make them by
  hand, **Make the session handouts** in the sidebar. Page numbers and the numbers of
  figures and questions are those of the whole handout.
- Before handing out, **Check before submitting** under Tools in the sidebar finds labels
  that point nowhere and missing references.

---

## Quick reference

| To write | Write |
|---|---|
| a session | `# Title` (with markers: `::: {.session #id title="…" date="…"}` + `:::`) |
| a section | `## Title` |
| a slide | `### Title` |
| a small heading on a slide | `#### Title` |
| a fixed session name | `# Title {#id}` |
| a new slide here | `::: {.slide}` + `:::` (titled with `title="…"`) |
| a heading that stays on the slide | `### Title {.same-slide}` |
| a slide without its title | `### Title {.no-title}` |
| a heading without a number | `## Title {.unnumbered}` or `{-}` |
| another title on the slides | `### Title {slide-title="Short"}` |
| notes for what you say | `::: notes` … `:::` |
| handout only / slides only | `::: {.handout-only}` / `::: {.slides-only}`, in a line `[…]{.slides-only}` |
| a question (numbered) | `::: {.question #question-x title="…"}` … `:::` |
| point at a block | `@question-x` |
| show again / list | `::: {.restate #question-x}` / `::: {.list-of .question}` |
| a figure | `![Caption](../assets/figures/x.png){#fig-x}`, pointed at with `@fig-x` |
| its source or note | `::: {.figure-note}` … `:::` right after it |
| a number that is not a result | `[40%]{.no-lint}` |
| a reference | `@key` |
| a URL | `<https://…>`, or `[words](https://…)` on some words |
| a footnote | `[^name]` and `[^name]: text` (in the same session), or `^[text]` in place |
| an appendix | `# Title {.appendix}` |

---

## From the command line

Whatever VS Code does can also be done with commands:

```bash
octavo new lecture public-policy                          # lectures/public-policy.md
octavo build public-policy --to typst --compile           # A4 handout
octavo build public-policy --to typst-slides --compile    # one deck per session
octavo build public-policy-week3 --to typst-slides        # one session only
octavo build public-policy-week3 --to typst-notes         # its speaker script
octavo extract public-policy                              # build/handouts/, one PDF per session
octavo extract public-policy --session week3 --cover      # one session, with the cover and contents
octavo check                                              # before handing out
```

`octavo build` on the command line does not make the per-session handouts; run
`octavo extract` again after editing.
