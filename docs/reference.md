# Octavo reference

> This is the source of the reference. Read it at **<https://yoshida-kd.github.io/octavo/reference/>**. <!-- pages:skip -->

This page is written for **AI assistants** working in an Octavo project, and for anyone who
wants every detail. People who use Octavo from VS Code should read the
[guide](https://yoshida-kd.github.io/octavo/guide/) instead.

The same text comes with Octavo, matching the installed version:

```bash
octavo docs                       # the list of sections
octavo docs 3.8                   # one section, by number
octavo docs posters               # or by words from its heading
octavo docs --search slides_select   # every section that mentions a word
octavo docs --all                 # everything
```

`--lang ja` gives the Japanese text. The project's `AGENTS.md` holds the rules for this
project; this page is how Octavo works.

---

## 1. What to keep to

### 1.1 The rules

- **Never type a result into a manuscript.** Numbers come from the analysis as `{{name}}`,
  figures and tables as files in `assets/`. A number in the prose that is a result is a bug
  (`octavo check lint` finds them).
- **Never type a number for a figure, table, equation, section or block.** Label it
  (`{#fig-trend}`) and refer to it (`@fig-trend`).
- **Never edit what is generated**: `build/` and `assets/` (values, figures, tables). Change the
  `.qmd`, the `figures/*.typ`, the `tables/*.csv` or the manuscript instead.
- **Never write to `data/raw/`**; the analysis writes `data/derived/`.
- **Never edit the `.bib`** (`bib_file`, usually `literature/literature.bib`): it is exported
  from the user's reference manager. Never edit `literature/priorwork/`: it is Priorwork's inbox.
- Write a manuscript **one sentence to a line** (`octavo fmt` shows where it is not).
- Ask before running anything slow or outward-facing: `octavo analysis run` on a `manual`
  analysis, `octavo release`, `octavo bib tidy --apply`.
- After a change, run `octavo check` (the exit code is non-zero on a fatal problem).

### 1.2 Finding out about a project

Prefer these to reading the files by hand; each has `--json`.

```bash
octavo documents --json       # every document: its file, outputs, sessions and their lines
octavo config --json          # the settings that can be changed, their values and choices
octavo config --doc my-paper --json   # the same for one document (front matter over project)
octavo analysis --json        # each .qmd: up to date, out of date, manual
octavo check values --json    # {{…}} in the text against the values the analysis wrote
octavo check cites --json     # citation keys against the .bib
octavo check --json           # everything before submitting
octavo doctor --json          # what is installed
```

---

## 2. Projects

### 2.1 What is in a project

```
study/
  octavo.config.py   the project's settings (a Python dict, CONFIG = {...})
  literature/        literature.bib, and priorwork/ (what Priorwork delivers)
  AGENTS.md          the project's rules for AI assistants
  CLAUDE.md          one line, @AGENTS.md
  README.md
  docs/<name>/       <name>.md (a manuscript), appendix.md, main.typ (a paper's layout), main.tex
  analysis/          the .qmd files and octavo.R / octavo_helper.py
  data/raw/          data as obtained (not in git; README.md records where it came from)
  data/derived/      data the analysis made (not in git)
  data/HASHES.json   fingerprints of data/ (in git)
  figures/           hand-made figures: <name>.typ drawn in Typst, _parts.typ shared parts, photos
  tables/            hand-made tables: <name>.csv
  notes/writing/     writing rules and phrases (packs)
  templates/         the project's own copies of Octavo's templates
  assets/values/     <qmd>.json: the numbers behind {{…}}
  assets/figures/    <name>.pdf and .png
  assets/tables/     <name>.typ, .tex, .md (the table's contents only)
  build/             the output, a folder per output; can be deleted
  requirements.txt   the Python packages (in git)
  renv.lock          the R packages (in git)
```

The config registers every folder by a pattern (`docs/*/`, `analysis/*.qmd`), so adding a
document or an analysis never means editing it.

### 2.2 Documents and their names

A document is `docs/<name>/<name>.md`, named `<name>` (`octavo build my-paper`). `appendix.md`
beside it is its appendix. What it makes is `outputs:` in its front matter ([4.1](#41-outputs)).
A document made of sessions also has one document per session for its slides and script:
`<name>-01`, `<name>-02`, … in order, or `<name>-<id>` for a session with an id
([3.10](#310-sessions)). `octavo documents` lists them all.

### 2.3 Adding to a project

```bash
octavo init study --lang en --with analysis,paper=my-paper   # the frame and some parts
octavo init study --all --example                           # every kind, filled with examples
octavo new analysis model                     # analysis/model.qmd (the first also brings octavo.R, data/)
octavo new analysis model --engine python     # in Python (brings octavo_helper.py)
octavo new paper my-paper                     # docs/my-paper/my-paper.md and main.typ
octavo new paper my-paper --appendix          # add appendix.md (to an existing paper too)
octavo new paper my-paper --tex               # add main.tex
octavo new paper other --lang ja              # a manuscript in another language than the project
octavo new slides talk
octavo new lecture course
octavo new poster poster
octavo new figure dag                         # figures/dag.typ
octavo new table compare                      # tables/compare.csv
octavo env                                    # the analysis environment (.venv, renv)
```

`--example` fills a part with a worked example; what it writes is marked (`octavo:example`
comments, `_placeholder` in values, a crossed box as figure) and `octavo check` counts what is
left. Placeholder values are fatal in `octavo check`. `--env` sets up the environment in the
same step. `new` on an existing document adds only the files it lacks. `new --json` says what
it made and whether the environment is still to be set up (`env_needed`).

### 2.4 Projects from earlier versions

```bash
octavo migrate --docs --dry-run    # papers/<n>/paper.md, slides/, lectures/ -> docs/<n>/<n>.md
octavo migrate --syntax --dry-run  # ::: {.session}, ::: {.slide}, .handout-only -> \session{}, \newslide, .no-slides
octavo migrate --rules --dry-run   # Octavo's sections of AGENTS.md -> the current text (shows the diff)
octavo migrate                     # a CLAUDE.md-only project's rules into AGENTS.md
```

All refuse an uncommitted project unless `--allow-dirty`. `--docs` keeps the document names,
fixes figure paths, writes `outputs`/`sessions` and adds `docs/*/` to the config. `--syntax`
builds every document before and after and keeps the rewrite only if every output is
identical. `--rules` replaces each `<!-- octavo:section X -->` part with the template's
(anything written inside it is replaced; text before the first section is kept). Old configs
(`papers/*/paper.md` with `profile` / `targets`) still build unchanged.

---

## 3. Writing manuscripts

### 3.1 Front matter

```markdown
---
title: Title of the Paper
subtitle: A subtitle
author: [Author One, Author Two]
institute: Example University
email: one@example.org
date: today
lang: en
outputs: [pdf, word]
abstract_word_limit: 150
---
```

- `title` and the rest make the title block, the cover or the title slide. Do not write a
  `# Title` heading: a `#` heading is a section.
- `date: today` is the day of the build; `date_format` sets the form.
- `lang` (`ja` / `en`) is the manuscript's language when it differs from the project's.
- Settings for this document only can go here too ([5.2](#52-settings-for-one-document)).
- `nocite: ["@key"]` lists works that are not cited but go in the bibliography.
- Octavo reads the front matter with a small reader of its own: no YAML comments (`# …`) in it,
  one value per line, lists as `[a, b]`.

### 3.2 Headings, labels and references

```markdown
# Analysis {#sec-analysis}

@fig-trend shows the trend and @tbl-desc the descriptive statistics.
We estimate @eq-model (see also [-@eq-model]).

![Trend](../../assets/figures/trend.png){#fig-trend}

| Variable | Mean |
|----------|------|
| x        | 1.2  |

: Descriptive statistics {#tbl-desc}

$$
y_i = \beta_0 + \beta_1 x_i + \varepsilon_i
$$ {#eq-model}
```

- `#` is the top section (a paper may start at `##` too). Headings carry no number.
- Labels: `fig-`, `tbl-`, `eq-`, `sec-` (or a block's kind, [3.3](#33-numbered-blocks))
  followed by ASCII letters, digits, `-` and `_`. Japanese may follow directly
  (`@fig-trendに示す`).
- `@fig-trend` prints "Figure 2.1" (「図2.1」 in Japanese), `@eq-model` "Equation (2.1)",
  `@sec-analysis` "Section 2"; `[-@eq-model]` the number alone.
- Numbered: headings (not `{.unnumbered}` / `{-}`), figures and tables with a caption,
  equations with a label. A figure or table with neither caption nor label is not counted.
- `crossref_numbering`: `'document'` (1, 2, …; the default for papers) or `'section'` (2.1;
  the default for lecture notes, slides and posters). In the appendix: A1 or A.1.
- `{.unlisted}` keeps a heading out of the contents.
- `octavo check` stops on a label that is missing or used twice; an unused label is a warning.

### 3.3 Numbered blocks

```markdown
::: {.question #question-why title="Why is government the main actor?"}
Why is government at the centre of public policy?
:::

::: nb
Unnumbered blocks need no label.
:::

::: {.restate #question-why}
:::

::: {.list-of .question}
:::
```

| Kinds | Numbering |
|---|---|
| `case`, `question` | one sequence (Case 1.1, Question 1.2) |
| `theorem`, `lemma`, `proposition`, `corollary`, `definition`, `example` | another sequence |
| `aside`, `nb`, `memo`, `remark` | none |

- The label starts with the kind (`#question-why`); `@question-why` prints "Question 1.2".
- `restate` repeats a block with its number; `list-of` lists every block of the kinds given
  (`.titles`: number, title and page only; `.list-of` alone: every numbered kind).
- Numbers reset per `#` section, like figures. Word: paragraph style `Theorem`.
- `theorem_envs` in the config renames or adds kinds:

```python
'theorem_envs': {
    'case': 'Example case',
    'claim': {'name': {'ja': '主張', 'en': 'Claim'}, 'counter': 'case'},
    'hint': {'name': 'Hint', 'numbered': False},
},
```

### 3.4 Math

```markdown
The estimate is $\hat\beta = {{coef_x:.3f}}$, with $y_i \sim \mathcal{N}(\mu, \sigma^2)$.

$$
\begin{aligned}
y_i &= \beta_0 + \beta_1 x_i + \varepsilon_i \\
\operatorname{Var}(\varepsilon_i) &= \sigma^2
\end{aligned}
$$
```

- LaTeX notation; it becomes Typst math, Word equations, or stays LaTeX.
- No space inside `$…$`; a literal dollar is `\$`. Display math on its own lines with blank
  lines around. `aligned`, not `align`.
- A one-line `\newcommand{\E}{\mathbb{E}}` anywhere (body or appendix) works everywhere; for
  an operator `\newcommand{\Cov}{\operatorname{Cov}}` (not `\DeclareMathOperator`).
- Keep a value with a thousands separator out of math (`$N$ = {{n_obs}}`).

### 3.5 Figures

```markdown
![Officials by level of government[^src]](../assets/figures/staff.png){#fig-staff width=70%}

::: {.figure-note}
Source: National Personnel Authority, *Annual Report 2025*.[^checked]
:::

[^src]: Full-time staff only.
[^checked]: Retrieved 1 October 2026.
```

- Paths are relative to the manuscript: `../../assets/figures/x.png` from `docs/<name>/`.
  Write `.png`: Typst and LaTeX outputs take the `.pdf` beside it, Word the `.png`
  (`figure_ext` changes this).
- `figure_width` is the default width; `{width=…}` sets one (ignored on slides, where a figure
  fills the room left).
- `::: {.figure-note}` right after a figure (after a table's caption line) holds its source or
  note: small type, same page, not in the caption.
- Photos go in `figures/` and are placed from there; `.jpg` and `.png` work everywhere.
  Octavo does not resize them.
- **Figures drawn in Typst**: `figures/<name>.typ` (`octavo new figure <name>` writes one with
  a `diagram(nodes, edges)` helper) is drawn by `octavo build` into
  `assets/figures/<name>.pdf` and `.png` whenever it or `figures/_*.typ` changes. Typst's root
  is the project: `json("/assets/values/analysis.json")` reads the analysis's numbers.

```typst
#diagram(
  (
    z: (2, 0, [Background $Z$]),
    x: (0, 1.6, [Education $X$]),
    y: (4, 1.6, [Income $Y$]),
  ),
  (("z", "x"), ("z", "y"), ("x", "y")),
)
```

### 3.6 Tables

- **In the manuscript**: a Markdown table, then `: Caption {#tbl-name}` below it.
- **From the analysis**: `ov_table(tab, "summary")` writes `assets/tables/summary.{typ,tex,md}`
  (contents only); the manuscript places it with a caption line alone,
  `: Descriptive statistics {#tbl-summary}`.
- **Made by hand**: `tables/<name>.csv`, drawn by `octavo build` into the same three files and
  placed the same way. Row 1 is the heading; an empty row-1 cell right of a filled one is merged
  into it, and then row 2 is a heading too; number-only columns are right-aligned; a column
  with long text wraps. Cells are plain text. UTF-8 (a BOM is accepted) or Shift_JIS; Octavo
  never writes a BOM. In VS Code the user edits it as a grid (*Edit as a Table*).
- An output file in `assets/tables/` made by neither (no `octavo build が … から作った` header,
  no `octavo:placeholder`) stops the build: it would be overwritten.

### 3.7 Citations

- `@key`, `[@key, p. 3]`, `[@key; @key2]`, `[-@key]` (year only); possessive
  `\poscite{key}` ("Smith and Taylor's (2003)"; in Japanese the の is written after it).
- The bibliography goes at the end. A paper's last section `# References` only marks the
  place; `::: {#refs}` + `:::` puts it elsewhere.
- `@PRIORWORK:<doi>` / `@{PRIORWORK:<doi>}` marks a paper Priorwork cited that is not in the
  `.bib` yet ([7.3](#73-priorwork)).
- `@fig-…`, `@tbl-…`, `@eq-…`, `@sec-…` and block labels are references, not citations.

### 3.8 Content for some outputs only

```markdown
::: {.no-slides}
Fill-in-the-blank space and detailed footnotes: handout only.
:::

::: {.slides-only}
Figures and short prompts: slides only.
:::
```

| Class | Kept in |
|---|---|
| `.no-slides` | everything but slides and scripts (the usual "handout only") |
| `.slides-only` (`.slide-only`) | slides and scripts |
| `.pdf-only`, `.word-only`, `.tex-only`, `.poster-only` | that output only |
| `.print-only` | PDF, Word, LaTeX |
| `.screen-only` / `.no-screen` | the projected deck only / everything but it (with `slides-handout`) |
| `.no-anonymous` / `.anonymous-only` | dropped / kept under `--anonymous` |
| `.on-slides` / `.on-poster` | picked for slides / posters when `slides_select` / `poster_select` is `marked` |

- `only-X`, `X-only`, `no-X`, `not-X` work for any output name, backend name or profile.
- `[words]{.slides-only}` works inside a line. Fences may be indented inside a list item;
  **an opening `:::` needs a blank line before it** (`octavo check` reports one that pandoc
  would print as text, and a class that matches no output).
- `::: notes` is speaker notes: only the script (and Beamer) keeps them.
- `[40%]{.no-lint}` or `::: {.no-lint}` keeps a number that is not a result out of
  `octavo check lint`; `lint_accepted` in the config lists accepted text.
- The older `.handout-only` still works (in lecture notes, the same as `.no-slides`).

### 3.9 Page breaks, slide breaks and slide titles

```markdown
## A long heading for the handout {slide-title="Short title"}

\newslide

### A heading that stays on the same slide {.same-slide}

\newslide{Another title}
```

- `\newpage` (or `\clearpage`) on a line of its own: a new page in PDF, Word and LaTeX.
- `\newslide`: a new slide titled like the last one plus " (cont.)"; `\newslide{Title}`;
  `\newslide{}` untitled. Ignored outside slides. Older form: `::: {.slide title="…"}` + `:::`.
- `{.same-slide}`: the heading stays on the current slide, in bold.
- `{slide-title="…"}`: another title on the slide (for a session's `#`, the deck's title).
- `{.no-title}` on a heading: a new slide without its title (the handout keeps the heading).
- A slide that overflows continues on a new "Title (cont.)" slide and the build says so; an
  untitled slide that overflows is only reported.
- **The slide level**: in a deck (`outputs: [slides]` alone) with `#` and `##`, `##` is a slide;
  with one level, every heading. In lecture notes it is decided once from the whole notes:
  normally `#` session, `##` section, `###` slide.

### 3.10 Sessions

```markdown
\session{Session 3: policy and government} {#third subtitle="Public policy" date="2026-10-14"}
```

- `sessions: true` in the front matter: each `#` heading is a session (one deck and one script
  each). A `{#id}` on the heading names it (`<name>-<id>`); otherwise `<name>-01`, `-02`, ….
- **Markers**: once there is a `\session{…}` line (or an older `::: {.session …}` div), the
  markers decide the sessions and `#` is an ordinary heading. The braces hold the title (empty:
  the session's first heading becomes the title); `{…}` takes `#id`, `subtitle`, `date`,
  `author`, `institute`. Text before the first marker is in the handout only.
- A session with nothing after its marker gets no deck; decks of sessions that no longer exist
  are deleted at the next build.
- Each session starts on a new page of the handout. Numbers in a deck are the handout's.

### 3.11 Footnotes, URLs, appendix

- `[^name]` + `[^name]: text`, or `^[text]` inline. In lecture notes, keep a footnote's text
  in the same session (a deck cannot see one written elsewhere).
- `<https://…>` is a link that shows the URL; `[words](https://…)` does not show it in print.
- `# Title {.appendix}` starts the appendix (A, B, …) within the file; a paper's `appendix.md`
  is the same. In a handout the order is text, references, appendix (see [4.2](#42-papers) and
  [4.3](#43-lecture-handouts) for separate PDFs).

### 3.12 One sentence to a line

```bash
octavo fmt my-paper            # shows where lines break mid-sentence or hold several sentences
octavo fmt my-paper --apply    # rewrites them
```

`fmt` joins lines broken inside a sentence and breaks a Japanese line after each 。 outside
brackets. It leaves code, math, comments, tables, headings, `:::` lines and hard breaks alone,
and never splits English lines.

---

## 4. Outputs

### 4.1 Outputs

| Output | Makes | Lands in |
|---|---|---|
| `pdf` | a PDF: a paper's layout if `main.typ` is beside the manuscript, otherwise the built-in A4 handout | `build/pdf/<name>.pdf` (a paper: `build/pdf/<name>/main.pdf` and a copy at `build/pdf/<name>.pdf`) |
| `slides` | slides (one deck per session) | `build/slides/<name>.pdf`, `<name>-slides-<session>.pdf` |
| `slides-handout` | the decks without `.screen-only`, with `.no-screen` | `build/slides-handout/` |
| `script` | each slide shrunk, with its `::: notes` (A4) | `build/script/<name>-notes.pdf`, `<name>-notes-<session>.pdf` |
| `poster` | a poster | `build/poster/<name>.pdf` |
| `word` | Word | `build/word/<name>.docx` |
| `tex` | LaTeX source (`main.tex` beside the manuscript if any); needs TeX to compile | `build/tex/` |
| `beamer` | LaTeX slides | `build/beamer/` |

```bash
octavo build                          # every document, every output it names
octavo build my-paper --to word       # one document, one output
octavo build --compile                # typeset to PDF as well
octavo build course-third --to slides # one session's deck
octavo build --to all --compile
octavo targets                        # the output names
```

- Without `outputs:`, a document makes `pdf`. The older names (`typst`, `typst-slides`,
  `typst-notes`, `docx`, `latex`) and `targets:` are read the same way.
- `--no-analysis` builds without running the analysis; `--json` reports where each output
  landed (`compiled`).
- `octavo watch` rebuilds on every save.

### 4.2 Papers

- `main.typ` beside the manuscript is the layout the user keeps by hand. A current one is
  nearly empty: `#show: octavo-article.with(…)`; the layout is `article.typ`, rewritten beside
  it on every build (after LaTeX's jsarticle for Japanese, article 11pt for English). Title,
  authors, `institute`, `email` and date come from the front matter (`auto` in
  `octavo-article.with`); writing them there overrides. Journal changes go after the `#show`
  line, or `octavo template copy paper/article.typ`.
- Page 1 shows the length (words or characters with and without notes, the abstract, figures,
  tables); `counts: none` hides it.
- `# Abstract` is the abstract. A paper made before `article.typ` keeps its own `main.typ`; to
  move it, rename `main.typ` and run `octavo new paper <name>`.
- The appendix (`appendix.md`) is a PDF of its own, `build/pdf/<name>-appendix.pdf`, numbered
  A-1, A-2, …; references between the two are written as numbers. `appendix_separate: false`
  puts it after the text in one PDF.
- `--anonymous` ([8.2](#82-blind-review)).

### 4.3 Lecture handouts

A document whose `pdf` has no `main.typ` gets the built-in A4 layout: a cover, the contents on
pages i, ii, …, the body from page 1, type after jsarticle (11pt, 36 lines a page), BIZ UDGothic
with Inter.

| Key | Default | What |
|---|---|---|
| `first_section` | `1` | `0` numbers a guidance session "0" |
| `pagebreak` | `'session'` | `'section'`: at each `#`; `None`: only at markers |
| `font`, `fontsize` | BIZ UDGothic + Inter, `'11pt'` | |
| `toc` | on with `sessions` | the contents |
| `date_format` | `'%B %-d, %Y'` (Japanese `'%Y年%-m月%-d日'`) | |
| `appendix_separate` | `True` | the appendix as `<name>-appendix.pdf` |
| `appendix_after_references` | `True` | `False`: text, appendix, references |

**One PDF per session**, cut from the typeset whole (page numbers, contents and numbers stay
those of the whole):

```bash
octavo build course --sessions                     # build/handouts/course-<session>.pdf
octavo extract course --session third --cover      # one or more sessions (comma-separated), with the cover
octavo extract course --pages 12-19                # by printed page numbers
```

### 4.4 Slides

| Key | Default | What |
|---|---|---|
| `slides_aspect` | `'16-9'` | `'4-3'` |
| `slides_accent` | `'#0e2f92'` | `None`: black only |
| `slides_numbering` | `None` | heading numbers (`'1.'`, `'1.1'`) |
| `slides_section_slides` | `False` | a divider slide per `#` section |
| `slides_running_header` | `True` | the section in the top-left corner |
| `slides_font` | BIZ UDGothic + Inter | |
| `slides_bibliography` | lecture decks `slide`, talks `off` | `slide`, `off`, `sheet` (an A4 `<deck>-references.pdf`), `both` |
| `slides_select` | `all` | `marked`: only `.on-slides` content and the headings above it |

The older names `typst_slides_*` are read too. Figures fill the room left on their slide.

### 4.5 Posters

```markdown
---
title: Counting how policy is made
author: [Author One, Author Two]
institute: Example University
event: Example Conference 2026
date: 2026-10-14
logo: ../../figures/logo.png
qr: https://example.org/paper
qr_label: The paper
outputs: [poster]
poster_grid: 3x2
poster_rows: [2, 1]
---

# Question

# Results {span=2}

# Notes {cell="3,2"}
```

| Write | Means |
|---|---|
| each `#` heading | one cell, filling the grid from the top left |
| `{span=2}` / `{rows=2}` | two columns wide / two rows high |
| `{cell="3,2"}` | column 3, row 2 (from 1) |
| `poster_size` | `a0` (default), `a1`, `a2`, `b0`, `b1` (JIS B), or `1189x841mm` |
| `poster_orientation` | `portrait` (default), `landscape` |
| `poster_grid`, `poster_rows` | columns x rows (`2x3`), the rows' height ratios |
| `logo`, `qr`, `qr_label` | logos on the left of the title band, a QR code on the right |
| `poster_select: marked` | only `.on-poster` content (a poster from a paper: `outputs: [pdf, poster]`) |
| `poster_font` | the typeface |

Content that does not fit its cell is reported when building and marked in red. A cell that
cannot be placed stops the build.

### 4.6 Word and LaTeX

- Word gets numbers written into headings, captions and equations, and references as links.
  `octavo template copy word` writes `templates/word/reference.docx` to restyle in Word
  (`docx_reference` names another).
- LaTeX needs TeX (`octavo setup --with-tex` on Linux). `main.tex` beside a paper is its
  layout; Octavo never runs latexmk on it. Nothing in Octavo's tests compiles LaTeX.

---

## 5. Settings

### 5.1 octavo.config.py

`CONFIG = {...}`, a Python dict. Unknown keys are warned about. The main keys:

| Key | What |
|---|---|
| `documents` | which files are documents (`{'docs': {'src': 'docs/*/'}}`) |
| `analysis` | the `.qmd` files: `[{'src': 'analysis/*.qmd'}]`, with `manual`, `deps` |
| `bib_file` | the `.bib` |
| `csl`, `csl_locale` | citation style (an ID from zotero.org/styles, or a path), its locale |
| `japanese_citation_form`, `citations_by_language` | Japanese works in the bibliography ([7.1](#71-the-bib-and-the-style)) |
| `lang` | the project's language (`ja` / `en`) |
| `meta` | `title`, `author`, `affiliation`, `email` defaults |
| `crossref_numbering` | `'document'` / `'section'` |
| `theorem_envs` | numbered block kinds |
| `figure_width`, `figure_ext` | figures |
| `values_dir`, `figure_dir`, `table_dir`, `figure_src_dir`, `table_src_dir` | the folders |
| `value_float_format`, `value_thousands_sep` | how numbers look |
| `word_limit`, `char_limit`, `abstract_word_limit`, `abstract_char_limit` | submission limits |
| `anonymous_drop_meta` | front-matter keys `--anonymous` removes |
| `lint_accepted`, `bib_accepted` | accepted findings |
| `slides_*`, `poster_*`, `first_section`, `pagebreak`, `font`, `fontsize`, `toc`, `date_format` | looks ([4](#4-outputs)) |
| `appendix_separate`, `appendix_after_references` | the appendix |
| `docx_reference` | Word styles |
| `zotero_collection`, `zotero_linked`, `zotero_write` | Zotero ([7.2](#72-zotero)) |
| `writing`, `writing_off` | writing-rule packs ([9](#9-writing-rules-for-ai-assistants)) |
| `replication_exclude` | left out of the replication package |
| `out_dirs` | where outputs land |

### 5.2 Settings for one document

These keys can also go in a manuscript's front matter, and then apply to it alone (the same
names as in the config): `outputs`, `sessions`, `lang`, `csl`, `csl_locale`,
`reference_section_title`, `japanese_citation_form`, `citations_by_language`,
`crossref_numbering`, `word_limit`, `char_limit`, `abstract_word_limit`,
`abstract_char_limit`, `slides_*`, `poster_*`, `first_section`, `pagebreak`, `font`,
`fontsize`, `toc`, `date_format`, `appendix_separate`, `appendix_after_references`,
`writing`, `writing_off`. A misspelt key is reported when building. A build prints
`[settings] from the manuscript: …`.

### 5.3 Changing settings from the command line

```bash
octavo config                                  # the settings and their values
octavo config set slides_aspect 4-3            # one line in octavo.config.py
octavo config unset slides_aspect
octavo config --doc my-paper set word_limit 8000   # one line in the manuscript's front matter
```

`set` validates before writing and refuses a value that spans several lines.

---

## 6. The analysis

### 6.1 How results reach the manuscript

```
analysis/*.qmd  --quarto-->  assets/values/<qmd>.json   {{name}} in the text
                             assets/figures/*.pdf|png   figures
                             assets/tables/*            tables
```

Octavo never parses R or reads Quarto's output: it runs `quarto render` and reads these files.
Each `.qmd` owns `assets/values/<its name>.json`; the manuscript sees all of them (a name in two
files: warned, the later wins). A name with no value stays as `{{name}}` and is reported.

### 6.2 The R helper (octavo.R)

```r
source(if (file.exists("octavo.R")) "octavo.R" else file.path("analysis", "octavo.R"))

ov_value("n_obs", nrow(d))              # {{n_obs}}
ov_value("coef_x", coef(m)[["x"]])      # {{coef_x}}, {{coef_x:.2f}}
ov_value("p_x", ov_pval(pv))            # ".023", "< .001"
ov_figure(p, "trend")                   # a ggplot or a function that draws -> trend.pdf, trend.png
ov_table(tab, "summary")                # a data frame -> summary.typ, .tex, .md
```

- The `source()` line finds `octavo.R` both when rendering (working folder `analysis/`) and
  when a chunk is run on its own (Run Cell: the project folder). A `.qmd` brought in from
  elsewhere should use the same line.
- `ov_figure(x, name, width, height)`; `ov_table(x, name, notes, align, groups, indent, size)`:
  `groups = c(Demand = 1, Hiring = 6)` puts heading rows before rows 1 and 6 and indents
  the rows under them; `size = 9.5` is the type size in points.
- `ov_palette(n)`, `ov_tint(col, 0.6)`, `ov_scale_colour_cud()`, `ov_scale_fill_cud()`:
  colours that stay distinct for every kind of colour vision.
- Outside a render (a chunk run on its own) `ov_value()` prints the value and records nothing,
  since it cannot tell which `.qmd` it belongs to; `options(octavo.values = "<qmd name>")` makes
  it write. The figure and table functions write as usual.
- `ov_root()` is the project folder (`file.path(ov_root(), "data", "raw", "x.csv")`).
- `octavo.R` needs base R only (ggplot2 only when given a ggplot). Its `_session` record in
  the values file keeps R and package versions.

### 6.3 The Python helper (octavo_helper.py)

```python
ov_value("n_obs", len(d))
ov_value("coef_x", model.params["x"])
ov_figure(fig, "trend")
ov_table(tab, "summary")
```

Same names and files as R; `ov_table` groups count from 0. `ov_style()` (before making a
figure) sets a Japanese font and embeddable fonts. Needs the standard library only (matplotlib,
pandas when handed one). `requirements.txt` gets `ipykernel`, `nbformat`, `nbclient`, `pyyaml`.

### 6.4 How numbers look

| Value | Example | Shown as |
|---|---|---|
| integer | `nrow(d)`, `len(d)` | `1,523` |
| double | `coef(m)[["x"]]` | `0.342` (`value_float_format`, 3 places) |
| text | `ov_pval(p)` | as it is |

`{{name:.2f}}` in the text or `ov_value(..., fmt = ".2f")` sets the format. A whole double
still shows decimals (`2.000`): that is deliberate.

### 6.5 When the analysis runs

```bash
octavo analysis                   # which .qmd are out of date
octavo analysis run               # run every out-of-date one (manual ones too)
octavo analysis run analysis/02-model.qmd   # this one, even if up to date
octavo analysis mark-fresh analysis/00-fetch.qmd   # record it as up to date without running
octavo analysis run --keep-cache   # also keep the results, for analysis prose
octavo analysis prose analysis/02-model.qmd   # only the prose changed: update the HTML, run no code
octavo check values --diff        # numbers in the text that changed at the last run
octavo check values --diff my-paper-v1-submitted   # since a git tag
```

- `octavo build` runs a `.qmd` when its contents, or a `deps` file's, changed since the last
  run (a branch switch or a fresh clone does not count). A failing `.qmd` stops the build;
  missing Quarto only warns.
- `manual: True` (slow data cleaning, fetching): `octavo build` never runs it, only reports it
  out of date.
- List `.qmd` files in order when one feeds another; each is re-checked as the run reaches it.

```python
'analysis': [
    {'src': 'analysis/01-clean.qmd', 'manual': True},
    {'src': 'analysis/02-model.qmd', 'deps': ['data/derived/*']},
],
```

- A `.qmd` can say the same in its own front matter (an explicit config entry wins):

````markdown
---
title: "Fetch the raw data"
octavo:
  manual: true
---

```{r}
out <- "../data/raw/survey.csv"
if (file.exists(out)) knitr::knit_exit("Already fetched. Move the file away to fetch again.")
```

```{r}
download.file("https://example.org/survey.csv", out)
```
````

- Fetch raw data in its own `analysis/00-fetch-<source>.qmd` (manual), skip the fetch when
  the file is there (`knitr::knit_exit()` in a chunk of its own), and record the source and
  date in `data/raw/README.md`.

### 6.6 The environment and packages

```bash
octavo env                          # .venv (uv) from requirements.txt; renv with knitr, rmarkdown and every package the .qmd use
octavo analysis missing analysis/model.qmd   # R packages it uses that are not installed
octavo analysis install analysis/model.qmd   # install them into the project's renv
```

- `octavo env` installs every package a `library(x)` / `x::f()` uses; when an R `.qmd` fails,
  Octavo installs what it uses and is missing, then runs it once more. Both record in
  `renv.lock`. Not-on-CRAN packages are named with the command (`renv::install("user/repo")`).
- After `install.packages()` in R, `renv::snapshot()`. Git keeps `requirements.txt` and
  `renv.lock`, never the libraries.
- On Linux, packages come from Posit Package Manager as binaries. Some need a system library
  when they load (igraph, used by quanteda.textplots, needs GLPK): `octavo setup` installs
  them, `octavo doctor` reports them (*system libraries*), and a failure "cannot open shared
  object file" comes with the apt line.
- `renv::status()` "out-of-sync" for recorded but unused packages is harmless.
- A project of Python analyses only gets no renv. `octavo analysis run` uses `.venv` itself.

### 6.7 Projects of .qmd files alone, other languages

A project need not have a manuscript: a report written in Quarto lives in `analysis/`, and
`octavo env` / `octavo analysis run` look after it; `octavo check` and `octavo build` do not
count the missing manuscript as a problem. Its output lands beside the `.qmd`. To use the
manuscripts' typefaces in a Quarto Typst PDF:

```yaml
format:
  typst:
    papersize: a4
    include-in-header:
      text: |
        #set text(font: ((name: "Libertinus Serif", covers: "latin-in-cjk"), "BIZ UDMincho", "Noto Serif CJK JP"))
```

Any other language works by writing `{"name": value}` into `assets/values/<anything>.json`,
figures (`.pdf` and `.png`) into `assets/figures/`, tables into `assets/tables/`.

---

## 7. Bibliography, Zotero and Priorwork

### 7.1 The .bib and the style

- `bib_file` (new projects: `literature/literature.bib`) is exported from the reference
  manager (Zotero with Better BibTeX's *Keep updated* keeps the keys stable). Octavo never
  writes it.
- `csl` sets the style for every output; `octavo csl get <id>` fetches one,
  `octavo csl list` lists what is cached.
- In a Japanese document, works with `langid = {japanese}` take one Japanese form whatever the
  style; `japanese_citation_form`: `standard` (山田太郎・田中花子 (2020)「題」『誌名』12(3): 1–20.),
  `fullwidth` （2020）…12巻3号、1–20頁。, `period` ．2020．…. `citations_by_language: False` sets
  everything in `csl_locale`. Japanese names in the `.bib` need a comma (`山田, 太郎`).

### 7.2 Zotero

```bash
octavo bib collections            # the collections, nested
octavo bib pull                   # the .bib from zotero_collection (and the collections under it)
octavo bib login --user-id 1234567   # the web API key, read from stdin
octavo bib tidy                   # the plan: cited but not in the main collection, in it but cited nowhere
octavo bib tidy --apply --keys smith2020,doe2019
```

- `zotero_collection` is the main collection (a name, a path `'A / B'`, or a list); it is what
  goes into the `.bib`. `zotero_linked` are collections that feed it (one per survey), never in
  the `.bib`.
- Zotero on the same machine is read through its local API (Better BibTeX first); otherwise
  the web API with the key in `~/.config/octavo/zotero.env` (never in the project).
- `bib tidy --apply` needs `'zotero_write': True` and a key with write access. It only adds
  entries to, or takes them out of, the main collection; it never deletes or edits an entry,
  and never takes out an entry whose citation key is not pinned in Better BibTeX. Ask the
  user before applying.

### 7.3 Priorwork

Priorwork (a separate tool for literature surveys) writes into `literature/priorwork/`:
`<survey>.md` (the text, citing with the `.bib`'s keys), `<survey>.json` (a manifest:
`draft`, `synthesis` or `complete`) and `<survey>.cards.json` (a card per paper). It writes
nowhere else.

```bash
octavo priorwork                  # what arrived
octavo priorwork resolve --dry-run   # @PRIORWORK:<doi> -> the .bib key, once the paper is in the .bib
octavo priorwork link             # the survey's collection -> zotero_linked
octavo priorwork cards --json     # the cards, by citation key
octavo priorwork ask --workspace <folder> --kind start
octavo priorwork requests
```

**Taking a delivery into the manuscript**: read the text with the manuscript; for a
`complete` delivery each addition quotes the sentence it belongs to ("Where" / 「場所」). Propose
where each part goes and wait for the user's answer; keep the citations as written; never edit
the inbox. `octavo check cites` lists `PRIORWORK:` marks apart, and notes cited papers that
Priorwork read only in the abstract.

---

## 8. Checking and after submitting

### 8.1 octavo check

```bash
octavo check                 # everything; non-zero exit on a fatal problem
octavo check --strict        # warnings count too
octavo check values          # {{…}} against the values
octavo check cites           # citation keys against the .bib, problems in the .bib
octavo check lint            # results typed into the text, nested lists out of line
```

Fatal: missing figure or table files, unresolved `{{…}}`, placeholder values, an analysis out
of date, missing citation keys, missing or duplicate labels, submission limits exceeded.
Warnings: template leftovers, unused labels, `:::` problems, writing-rule names, the data
fingerprints.

### 8.2 Blind review

```markdown
::: {.no-anonymous}
Acknowledgements: this research was funded by ...
:::
```

```bash
octavo build my-paper --anonymous
octavo bundle my-paper --anonymous     # and checks the package for the author's name
```

`--anonymous` drops `.no-anonymous`, keeps `.anonymous-only`, removes `anonymous_drop_meta`
keys and switches `main.typ`'s title block (`flags.typ`). The next ordinary build switches back.

### 8.3 After sending it

```bash
octavo bundle my-paper                 # submission-my-paper.zip, flattened for a journal system
octavo review returned.docx            # a coauthor's tracked changes and comments
octavo release my-paper v1-submitted   # tag my-paper-v1-submitted, the PDF on a GitHub Release (gh)
octavo data hash                       # data/HASHES.json
octavo data status                     # has data/ changed since
octavo data track data/raw/typed.csv   # let git take one file under data/
octavo bundle --replication            # analysis, values, figures, tables, config, fingerprints
octavo bundle --replication --standalone  # the same, with .qmd files that do not need the helpers
octavo bundle --replication --standalone --verify   # and run the package itself to check it
```

- `review` only reads; a returned `.docx` is never converted back (its numbers are typed in).
  Apply the changes to the manuscript.
- `release` refuses uncommitted changes, placeholder values and an analysis out of date; it
  never runs the analysis. Ask the user first.
- `--replication` leaves raw data out unless `--with-raw-data`.
- `--standalone` rewrites the copies in the package, never the project's `.qmd` files: `ov_value()` prints
  the value, `ov_figure()` becomes `ggsave()` / `savefig()`, `ov_table()` writes a CSV, `ov_root()` a relative
  path, and `ov_pval()` / `ov_tint()` small functions defined in the file. It replaces calls it can be sure of:
  a statement of its own at the start of a line, outside functions and blocks, with its name written as a
  string. Others are listed with the reason and stay as they are; a `.qmd` with any left keeps loading the
  helper, so the package still runs. Run a package once before sending it: the packages your analysis needs
  are the reader's to install.
- **A package is in English** unless `--lang ja`, which translates nothing and writes the README in Japanese.
  Octavo does not translate: it writes each Japanese line of a `.qmd`, `.R` or `.py` under `analysis/` into
  `analysis/replication/<name>.en.json` (`<name>.R.en.json` for a script), under `prose`, `comments` or `code`,
  and applies the lines you or an AI fill in, to the package's copy only. A line you later change comes back as
  to do; `package.en.json` holds the README's title and any Japanese settings. **Under `code`, keep what code
  compares with data** (a filter on a value, a regular expression): leave its translation empty. The package's
  copy of the settings loses its Japanese comments. Other files with Japanese left in them (a table's labels, a
  value's note) are listed, not changed. Data, the bibliography and text inside figures are left as they are.
- `--verify` runs **the package itself** in a temporary folder, without manual analyses, and compares the values
  with `assets/values`, so it finds a file the analysis needs that did not go into the package. It borrows the
  project's `renv` and `.venv`, so it does not check that the package versions can be installed. An analysis that
  fails only without `data/raw` is reported and compared, since leaving raw data out is allowed. With
  `--standalone` it also runs the rewritten `.qmd` files, which record no values, and says which figures and
  tables did not come out again. It fails if nothing could be checked (only manual analyses, or no Quarto), and
  then no zip is made.
- The package's README gives the commands to install the recorded package versions and to run the analyses in
  the configured order; manual analyses are listed apart.
- **The output never replaces what Octavo did not write.** A zip is built in a temporary folder, so a folder of
  the same name (`replication/`, or `data/` with `--out data.zip`) is not touched, and an existing file that is
  not a zip is refused. `--dir` makes its folder again only if it holds nothing but the files Octavo wrote there
  last time (recorded in `build/`); otherwise it stops and changes nothing.

---

## 9. Writing rules for AI assistants

The user's rules on how they write, and a bank of trusted phrasings, are Markdown files in packs.
**Before writing or revising prose, run `octavo writing --file <file> --line <line> --print` and follow
what it prints.** How to set packs up, with examples: [Writing support](https://yoshida-kd.github.io/octavo/writing/).

### 9.1 Packs and files

- A pack is a folder `<pack>/` with `rules/*.md`, `phrases/*.md` and an optional `pack.md` (`title`,
  `extends`, `sections`), in `~/.config/octavo/writing/` (every project) or `notes/writing/` (the
  project; the older `writing/` is read too). The same pack and file name: the project's wins. Files
  directly in `rules/` / `phrases/` are the pack `local`, always last.
- A file's front matter: `title`, `lang` (`en`/`ja`; none = every language), `applies` (`paper`,
  `slides`, `lecture`, `poster`, `all`; default `all`), `section` (none = always read). Each `##`
  heading is one entry; its id is `pack/file#slug` (lower case, non-alphanumeric runs -> `-`, a repeat
  gets `-2`).
- Rules are printed as written. In phrases, `When:` / `Note:` / `Source:` (場面 / 注意 / 出典) become
  JSON fields, as does `Contains:`; list items are frames (`- Open:` / `- Body:` / `- Close:` give their
  position), 〈 〉 are slots and `〈A / B〉` a choice; other lines are printed and not read.

### 9.2 What a manuscript reads

- Packs: `writing` in the config or the front matter (the front matter replaces the config's), most
  general first, the later winning; `extends` are put in front; none chosen = every pack (extends
  first, then by name); `local` last.
- `writing_off` (config **plus** front matter): `pack/file`, `file`, `pack/file#slug` or `file#slug`.
- A file is left out when its `applies` does not match the manuscript's kinds (from its outputs), its
  `lang` differs from the manuscript's, it is turned off, or it has a `section` other than the one
  asked for. `--all` drops only the last condition.
- The section of a line: from the nearest heading up to shallower ones, the first that names a
  section (a pack's own sections first; in one heading the word that comes first). Built-in sections:
  `abstract`, `introduction`, `literature`, `theory`, `design`, `results`, `discussion`,
  `conclusion`, `appendix` (a `{.appendix}` heading, what follows it, the appendix file). The words for
  each are in the table in [Writing support 3.4](https://yoshida-kd.github.io/octavo/writing/#34-the-section-of-a-line).

### 9.3 Commands

```bash
octavo writing
octavo writing --for my-paper --section results --print
octavo writing --file docs/my-paper/my-paper.md --line 120 --print
octavo writing --for my-paper --kind field/results#the-main-result --print
octavo outline my-paper --paragraphs
```

- `--for DOC` or `--file F` names the manuscript; `--line N` (with `--file`) finds the section and the
  paragraph's mark; `--section S` overrides the section; `--all` takes every section; `--kind K`
  (repeatable, comma-separated) names paragraph kinds; `--print` prints the layered text; `--json`.
- With a kind (from `--kind`, or from the mark on `--line`), rules are unchanged and phrases are only
  those entries, from the phrase files this manuscript uses (chosen packs, matching `applies` / `lang`,
  not turned off; any section). A kind from another file is left out with a warning.

### 9.4 Paragraph marks and questions

- `<!-- para: <kind> | <claim> -->` directly above a paragraph; the text starts on the next line; a
  mark followed by a blank line is an unwritten paragraph; leave a blank line before a mark (otherwise
  pandoc joins it to the paragraph above). Kinds resolve like `writing_off` ids (`file#slug` from the
  later pack).
- `octavo outline … --paragraphs` problems: `no-kind`, `unknown-kind` (+ `near`), `unused-kind` (in a
  file this manuscript does not use), `no-text`, `joined`,
  `same-kind` (the third in a row under one heading, a note). Repeats: a frame matched in two sentences
  under one heading (every word outside 〈 〉 in order within one sentence; a capitalised frame starts
  the sentence, one ending in `.` ends it; fewer than two fixed words are not looked for; only frames of
  that heading's section or with no `section:`, among the files this manuscript uses).
- `<!-- ask: … -->`: listed by the outline; `octavo check` warns ("questions for the author") until
  deleted. Marks in code blocks are not read.

### 9.5 JSON

- `octavo writing --json` (no manuscript): `rules`, `phrases` (files: `path`, `title`, `lang`,
  `applies`, `section`, `entries`, `where`, `pack`, `kind`), `packs` (`name`, `title`, `path`, `where`,
  `extends`, `sections`, `description`, `files`), `sections`, `warnings`.
- `octavo writing --for|--file … --json`: `doc`, `packs`, `chosen`, `chosen_here`, `kinds`, `lang`,
  `section`, `heading`, `sections`, `off`, `off_here`, `paragraph_kinds` (null without kinds),
  `paragraph` (`line`, `kind`, `claim`, `body_line`, `first_sentence`; null without `--line`),
  `warnings`, `text` (with `--print`) and `files`: `id`, `pack`, `kind`, `path`, `title`, `lang`,
  `applies`, `section`, `where`, `used`, `skipped` (`applies`, `lang`, `off`, `section`, `kind` or
  null), `items` (`id`, `title`, `slug`, `line`, `off`; phrases also `when`, `note`, `source`, `lines`
  = [`position`, `text`], `contains`, and `picked` when kinds are given).
- `octavo outline … --paragraphs --json`: a list per manuscript file: `doc`, `file`, `appendix`,
  `paragraphs` (`line`, `body_line`, `kind`, `id`, `title`, `claim`, `first_sentence`, `heading`,
  `heading_line`, `heading_level`, `problems`, `near`), `repeats` (`heading`, `heading_line`, `id`,
  `text`, `lines`, `section`), `asks` (`line`, `text`).

### 9.6 When nothing comes out

- No rules at all: Octavo 0.6.8 or earlier has no packs; or the folders are not at
  `~/.config/octavo/writing/<pack>/` / `notes/writing/<pack>/` (a link one level off shows nothing).
- A file missing for one manuscript: `applies` / `lang` (`octavo writing --for DOC --all` shows what
  was left out); a section never read: the heading names no section, or the section is mistyped
  (`octavo check`).
- `writing_off names nothing`: the entry's heading, hence its slug, changed.
- `needs a blank line before the mark`: add an empty line above the mark.

---

## 10. Templates

```bash
octavo template list                              # every template and where the one in use comes from
octavo template copy slides/typst-slides.typ      # into templates/ of this project
octavo template copy paper/en/main.typ --user     # into ~/.config/octavo/templates/
octavo template diff slides/typst-slides.typ      # what changed in Octavo's own since the copy
```

Lookup: the project's `templates/`, then `~/.config/octavo/templates/`, then Octavo's; a
copy replaces the whole file.

| Template | For |
|---|---|
| `slides/typst-slides.typ`, `slides/typst-notes.typ` | decks and scripts |
| `poster/typst-poster.typ` | posters |
| `handout/handout.typ` | the A4 handout |
| `paper/article.typ`, `paper/<lang>/main.typ` | papers |
| `manuscripts/<lang>/*.md` | what `octavo new` writes |
| `typst/crossref.typ` | how numbers and references look |
| `citations/japanese.lua` | Japanese works in the bibliography |
| `claude/<lang>/*.md` | the sections of AGENTS.md |

Fonts: papers BIZ UDMincho + Libertinus Serif, handouts and slides BIZ UDGothic + Inter
(Noto CJK, Hiragino or Yu as fallbacks).

---

## 11. Commands

```
octavo build [documents...] [--to outputs] [--compile] [--appendix] [--sessions] [--no-analysis] [--anonymous] [--json]
octavo watch [documents...] [--to outputs]
octavo extract <lecture> [--session IDS] [--pages 12-19] [--cover]
octavo documents [--json]
octavo outline [documents...] [--paragraphs] [--json]
octavo targets
octavo config [--doc NAME] [set KEY VALUE | unset KEY] [--json]
octavo analysis [--json] | run [QMD...] [--keep-cache] | mark-fresh QMD | prose QMD | missing QMD | install QMD
octavo env
octavo check [--strict] [--anonymous] [--json]
octavo check values [--unused] [--diff [REF]] [--json]
octavo check cites [--list] [--unused] [--json]
octavo check lint [--json]
octavo fmt [name] [--apply]
octavo bib pull|tidy|collections|login
octavo csl get|list|which [ID]
octavo priorwork [resolve|link|cards|ask|requests] [--dry-run] [--json]
octavo writing [--for DOC --section S | --file F --line N] [--kind KIND] [--print] [--json]
octavo bundle [name] [--anonymous] [--replication] [--with-raw-data] [--standalone] [--lang en|ja] [--verify]
octavo review returned.docx [--json]
octavo release <document> <label>
octavo data hash|status|track
octavo init <dir> [--lang ja|en] [--with PARTS | --all] [--engine r|python] [--example] [--env]
octavo new paper|slides|lecture|poster|analysis|figure|table <name> [--lang ja|en] [--example] [--appendix] [--tex] [--engine r|python] [--env] [--json]
octavo template list|copy|diff [name] [--user]
octavo migrate [--docs|--syntax|--rules] [--dry-run] [--allow-dirty]
octavo setup [--with-tex] [--check] [--r-editor]
octavo doctor [--json]
octavo selftest
octavo docs [section] [--search WORD] [--all] [--lang ja|en]
```

The older names `octavo values`, `octavo checkbib`, `octavo lint` and `octavo reference-docx`
still work. Messages follow `OCTAVO_LANG` (`ja` / `en`), else the system's language.

---

## 12. When something goes wrong

- **A tool is missing**: `octavo doctor` names it and the command that installs it;
  `octavo setup` installs or updates them all.
- **"there is no package called …"** running a `.qmd` from Quarto's Preview: run it through
  Octavo (`octavo analysis run <qmd>`), or `octavo analysis install <qmd>`.
- **"cannot open file 'octavo.R'"** when a chunk runs on its own: the `.qmd` loads it with
  `source("octavo.R")`; use the line in [6.2](#62-the-r-helper-octavor).
- **A package installs but does not load** ("cannot open shared object file"): a system
  library is missing; `octavo doctor` shows the apt line.
- **A label does not resolve, a figure is missing**: `octavo check` says which and where.
- **A number in the PDF is wrong**: rerun the analysis (`octavo analysis run`); never type it.
- **A slide overflows**: the build names it; add `\newslide`, cut, or shrink a figure.
- **Citations look wrong**: `octavo selftest` prints them as typeset; check the `.bib` entry
  with `octavo check cites`.
