<!-- octavo:section common -->
# About this repository

The "@@NAME@@" project. **Writing (Markdown) and typesetting (Typst / Word / LaTeX /
Beamer) live in this one repository**, and an analysis (Quarto `.qmd`) can be added.
Conversion is done by the `octavo` command from
[Octavo](https://github.com/yoshida-kd/octavo).

```
figures/          figures you make by hand: drawn in Typst (<name>.typ), photos
tables/           (make it when needed) tables you make by hand: <name>.csv
assets/           what goes into the manuscripts. **Written by the analysis and octavo build; never edited by hand** (kept in git)
  figures/        figures (<name>.pdf and .png): the analysis's, and those drawn from figures/*.typ
  tables/         tables (<name>.typ / .tex / .md): the analysis's, and those made from tables/*.csv
refs/             (make it when needed) material from elsewhere (codebooks, questionnaires, guidelines). kept in git
notes/            (make it when needed) things you wrote (reading, referee, working notes). never part of the manuscript
literature.bib    bibliography. **The reference manager (e.g. Zotero) is the source of truth** (its export overwrites it)
templates/        this project's own versions of Octavo's templates (absent = the bundled ones; octavo template list)
octavo.config.py  this project's configuration (sources, styling, analysis registration)
build/            generated output. **nothing here is written by hand; delete it freely**
```

The rules for an analysis, papers, and slides and lecture notes are appended to
this file as sections when each is first added.

## Adding things

Manuscripts (papers, slides, lecture notes) and analyses (`.qmd`) are added with
`octavo new`, **any number of each** (two papers, ten talks, three analyses). The
analysis, bibliography, figures and tables are shared by every manuscript.

```bash
octavo new paper example-paper         # docs/example-paper/example-paper.md and main.typ
octavo new paper example-paper --appendix   # add appendix.md (to an existing paper too)
octavo new paper example-paper --tex        # add main.tex for LaTeX (to an existing paper too)
octavo new slides example-talk           # docs/example-talk/example-talk.md
octavo new lecture example-lecture    # docs/example-lecture/example-lecture.md
octavo new analysis model             # analysis/model.qmd (and data/ etc. the first time)
octavo new figure dag                 # figures/dag.typ (a figure drawn in Typst, instead of TikZ)
octavo new table compare              # tables/compare.csv (a table you make by hand)
```

`octavo new` writes bare headings only. Add `--example` to get an example that
shows how things are written (with the example analysis and bibliography it uses).

- **A document is `docs/<name>/<name>.md`.** Its appendix (`appendix.md`) and a paper's
  layout (`main.typ`) sit in the same folder. `octavo build <name>` and friends take that name
- **What a document makes is `outputs:` at the top of the manuscript** (`pdf` / `word` /
  `tex` / `slides` / `beamer` / `script`; `pdf` when not written). The PDF's layout is the
  `main.typ` beside the manuscript if there is one, otherwise Octavo's built-in one.
  **A manuscript made of several class sessions says `sessions: true`** (one deck per session)
- The title goes in the front matter (`title:`); don't write a `# Title` heading
- `documents` and `analysis` in `octavo.config.py` pick up whole folders, so **they
  need no editing** — but a file placed elsewhere is not picked up
- To remove a manuscript, delete its folder
- Settings that change per journal or talk (`csl`, `outputs`, limits such as
  `word_limit`, `slides_*`) go **at the top of that manuscript**; anything not
  written there follows `octavo.config.py` (`octavo config --doc <name>` lists and changes them)
- A page break is `\newpage` on a line of its own; a slide break is `\newslide` (`\newslide{Title}`)

# Rules

## Don't edit build output

Whatever `octavo build` generates (the contents of `build/pdf/`,
`build/slides/`, `build/word/` and so on) **is erased by the next build.**
The thing to fix is the manuscript (or the `.qmd`). Nothing under `build/` is
written by hand, so the whole directory can be deleted (git does not track it).

## The reference manager owns literature.bib

`literature.bib` is exported from the reference manager (e.g. Zotero), and the next export
**overwrites the file wholesale**, so hand-edits are lost. Fix bibliographic errors there.

- `octavo check cites` — are the cited keys in the `.bib`, and is the `.bib` well-formed
- Findings you've decided not to fix go in `bib_accepted` in `octavo.config.py`, with a reason

## Figures, tables, equations and sections are referred to by label, not number

Numbers (the "2." of a heading, the "Figure 1" of a caption) are **never typed in
the manuscript**. They are assigned when typeset, by section (Figure 2.1, Table 2.1,
Equation (2.1)). In the manuscript, give things a label and refer to them by name:

| | How to write it | Referring to it |
|---|---|---|
| Section | `# Analysis {#sec-analysis}` | `@sec-analysis` → Section 2 |
| Figure | `![Trend](../../assets/figures/trend.png){#fig-trend}` | `@fig-trend` → Figure 2.1 |
| Table (typed in the manuscript) | a Markdown table + `: Descriptive statistics {#tbl-desc}` right below it | `@tbl-desc` → Table 2.1 |
| Table (made by the analysis) | just the line `: Descriptive statistics {#tbl-summary}` (`assets/tables/summary.*` goes there) | `@tbl-summary` |
| Table (made by hand) | `tables/compare.csv`, and just the line `: Comparison {#tbl-compare}` | `@tbl-compare` |
| Equation | `$$ … $$ {#eq-model}` | `@eq-model` → Equation (2.1) |

- Labels start with `fig-` `tbl-` `eq-` `sec-` and use letters, digits, `-` and `_`.
  `[-@fig-trend]` gives the number alone ("2.1")
- Adding or reordering sections and figures **never means fixing references**.
  `octavo check` stops on a reference to a missing label and on a label used twice

### Figure files (`.png` in the manuscript, `.pdf` in the typeset output)

**Write the `.png`** in the manuscript. Octavo swaps it per format when it builds (the
build's `[figure] fig-… -> …/trend.pdf` line records it):

| Output | File used | Why |
|---|---|---|
| The editor's preview | `.png` (what you wrote) | the preview cannot show a PDF figure |
| Typst (paper, handout, slides) and LaTeX | `.pdf` | vector: sharp at any zoom, and the text inside stays selectable and searchable |
| Word | `.png` | Word cannot embed a PDF figure |

`ov_figure()` and `figures/*.typ` write both the `.pdf` and the `.png`. A `.pdf` written
straight into the manuscript is used for typesetting but does not show in the editor's preview.

Write the path relative to the manuscript (`../../assets/figures/` from `docs/<name>/`). Figures are shared by every manuscript:
to show a paper's figure on a slide, point at the same file in `assets/figures/` — don't
copy it.

### Making figures (readable for every kind of colour vision)

1. Pick colours from the **colour-universal-design palette**: `ov_palette(3)` in R
   (blue, orange, green, …), `ov_scale_colour_cud()` / `ov_scale_fill_cud()` for ggplot2
2. **Never tell things apart by colour alone.** Write values and names inside the figure
   rather than relying on a legend; emphasise with weight, line type or position as well
3. Neighbouring areas differ in **lightness**, not just hue. Lighten an area that carries
   text with `ov_tint(colour, 0.6)`
4. Don't put red next to green, or yellow next to white

Diagrams such as boxes and arrows are drawn in Typst: `octavo new figure <name>` puts
`figures/<name>.typ`, and `octavo build` turns it into `.pdf` and `.png`, so the
manuscript references the `.png` like any figure (**never edit the drawn `.pdf` / `.png`**;
edit the `.typ`).

A comparison table in sentences or a table of hand-collected numbers goes in a CSV:
`octavo new table <name>` puts `tables/<name>.csv` (row 1 is the heading; an empty heading
cell right of a filled one merges into it), and `octavo build` makes the table in
`assets/tables/` (**edit the `.csv`**). Prefer this to typing a long Markdown table into the
manuscript.

A figure's or table's **source and notes** go in `::: {.figure-note}` + `:::` right after it
(after a table's caption line), not in an ordinary paragraph below: then they stay with it,
in small type, and shrink with it on a slide. **Photos and screenshots** go in `figures/` and
are placed from there (`../../figures/photo.jpg`); resize large ones first, and note where each
came from and whether it may be used in `figures/README.md`.

## Indenting nested lists

Line a nested item up with **its parent's text** (2 spaces under `- `, 3 under `1. `). The
width is not fixed, but keep one width within a manuscript. `octavo check lint` points out nested
items that are out of line, and lines under a numbered item indented too little to nest.

**Leave a blank line before every opening `:::`** (inside a list item too, indented to the
item's text); without it pandoc prints the `:::` as text. `octavo check lint` reports that, and a
`.xxx-only` mark that matches no output. A number in the prose that is not a result (a grading
split) is marked `[40%]{.no-lint}` so the hand-typed check skips it.

## The examples are marked as examples

By default `octavo init` / `octavo new` write only what you keep using (bare
headings, an empty bibliography, the frame of the analysis). **Examples** come only
with `--example`, and say so. Once you replace one with your own content, **delete
the mark too.**

| Mark | Where | How it goes away |
|---|---|---|
| an `octavo:example` comment | manuscripts, appendix, `.qmd`, `literature.bib` | delete it by hand |
| `_placeholder` | `assets/values/*.json` | `octavo analysis run` rewrites the file |
| a figure that is a box with an × | `assets/figures/trend.*` | `ov_figure()` rewrites it |
| a table with nothing in it | `assets/tables/summary.*` | `ov_table()` rewrites it |

**Placeholder values (`_placeholder`) are the dangerous one.** Every `{{...}}`
resolves even though the analysis has never run, so **a PDF full of fake numbers
typesets cleanly.** So `octavo check` treats them as **fatal**, and `octavo build`
and `octavo check values` say so every time.

While marks remain, `octavo check` counts them as leftovers. **Get that to zero
before you finish.**

# How to work

## Writing and revising

```bash
octavo build                   # convert every manuscript (a stale analysis runs first)
octavo build <name>            # just one
octavo check cites                # are the cited keys in the .bib?
octavo outline                 # show the heading structure
```

`octavo build --no-citations` skips citation resolution for a fast look.

The user often has the manuscript open in the editor while you work.

- Change a manuscript (`.md`) with the editing tool that goes through the editor; don't
  rewrite the file from the shell or a script (`sed` and the like) — the change does not show
  in the editor and the preview, and it collides with unsaved edits
- Ask the user to save the manuscript before you change it

## Before you finish

```bash
octavo check          # every check in one pass (non-zero exit on fatal findings)
octavo check lint           # just the numbers typed into the prose, in detail
```

**Do not submit or hand out anything while something is marked fatal.** Warnings are
for you to judge.

# Never

- **Never hand-edit `build/` output.** The thing to fix is always the manuscript.
- **Never hand-edit `literature.bib`** (fix it in the reference manager).
- Never dump `octavo check lint` findings into `lint_accepted` without checking them.
  That list is only for things you have decided are not results.
- **Never put a manuscript outside the places `octavo new` uses** (`octavo.config.py` won't pick it up).
- **Don't delete an `octavo:example` mark without replacing the content.** The mark
  records that a passage is still an example; it goes when the content does.
- Don't invent new keys in `octavo.config.py` — unknown keys are warned about at startup.

# When something is wrong

```bash
octavo doctor       # is pandoc / LaTeX / Typst / Quarto / R present?
octavo selftest     # see how citations actually typeset, on real output
```

For the `octavo` command itself, see Octavo's guide: https://yoshida-kd.github.io/octavo/guide/
