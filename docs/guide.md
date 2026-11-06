# Octavo guide

> This is the source of the guide. Read it at **<https://yoshida-kd.github.io/octavo/guide/>**. <!-- pages:skip -->

**The quantitative social science starter pack**

Octavo turns Markdown manuscripts into papers, handouts, slides and posters, with the
citations from one `.bib` file and the numbers, figures and tables from your Quarto analysis.
This guide is for people who use it **in VS Code**: everything here is a button, a menu or
something you write in the manuscript.

- Not installed yet? [Installing Octavo](https://yoshida-kd.github.io/octavo/install/).
- In a hurry? The [quick guide](https://yoshida-kd.github.io/octavo/quickstart/).
- Course materials: [Making course materials](https://yoshida-kd.github.io/octavo/lectures/).
- Writing rules for your AI assistant: [Writing support](https://yoshida-kd.github.io/octavo/writing/).
- Everything else — every command and every setting — is in the
  [reference](https://yoshida-kd.github.io/octavo/reference/), written for your AI assistant.
  Anything this guide does not give a button for, ask the assistant.

[日本語の手引き](https://yoshida-kd.github.io/octavo/ja/guide/)

---

## 1. Around the screen

### 1.1 The sidebar

The Octavo icon on the far left opens the sidebar. It has five sections:

| Section | What is in it |
|---|---|
| **Manuscripts** | every manuscript, with a **Preview** and a **Build to PDF** button on each; open one to see its sessions (lecture notes), its appendix, **Settings for this document** and **Writing rules** |
| **Analysis** | every `.qmd`, marked up to date, out of date or manual, with ▶ to run it; **Run the stale ones** and **Add an analysis** |
| **Tools** | in the order you need them: install the tools, check the environment, set up the project's analysis environment, run the analysis, check the bibliography, **Check before submitting** |
| **From Priorwork** | only when a literature survey has delivered something ([5.5](#55-with-a-literature-survey-priorwork)) |
| **Settings** | the project's defaults, folded |

The **+** at the top of the sidebar adds a manuscript, an analysis, a figure or a table. A
right-click on a paper offers **Add an appendix**, **Add main.tex (LaTeX)** and **Ask Priorwork
for the Literature**.

### 1.2 The preview

Open a manuscript and press the **PDF** button at the top right of the editor. The PDF opens
beside it and is rebuilt every time you save.

- It scrolls to where your cursor is (the ⇅ button in its toolbar turns that off). You can
  still scroll it on its own.
- Text can be selected, links followed, and ☰ lists the bookmarks. Click in the PDF and press
  Ctrl+F (⌘F on a Mac) to search it.
- For slides and lecture notes, the **screen** button at the top right picks a third column:
  the deck for the session the cursor is in, the speaker script, or nothing.
- The preview never runs the analysis. When something is out of date, a bar above the PDF
  says so, with a button to run it.
- It closes when you close the manuscript.

### 1.3 What your AI assistant does for you

Every project has an `AGENTS.md` with its working rules, and Claude Code, GitHub Copilot, Codex
and Antigravity read it by themselves. The assistant also knows how to look things up in
Octavo's reference, so when this guide says "ask your AI assistant", you can say it in your own
words: *"make the anonymous version for review"*, *"package the paper for the journal"*, *"show
me which numbers changed since I submitted"*. More in [10](#10-working-with-an-ai-assistant).

---

## 2. Projects

### 2.1 Try the example first

Open an empty folder in VS Code. The Octavo sidebar offers **New project**; press it, choose
every part and tick **Fill them with examples**. You get an analysis of made-up data, a paper,
a slide deck, lecture notes and a poster that use it, and the analysis environment is set up
right after (the first time takes a few minutes). Open the paper and press the **PDF** button.

### 2.2 Start your own

**New project** is one screen:

- **Where**: in a new folder, or in the open folder.
- **Language of the writing**: Japanese or English. It chooses the templates, the headings
  ("Figure" or 「図」) and the citation forms. A manuscript in the other language can be added
  later.
- **What to start with**: an analysis (in R or Python), a paper, slides, lecture notes, a
  poster. Pick only what you need now; anything can be added later.
- **Fill them with examples**, or start from bare headings.

### 2.3 Adding to a project

The **+** at the top of the sidebar (or **Add a manuscript…** under Manuscripts, **Add an
analysis** under Analysis) asks what to add and its name:

| Add | It writes |
|---|---|
| Paper | `docs/<name>/<name>.md` and `main.typ`, the layout |
| Talk slides | `docs/<name>/<name>.md` |
| Lecture notes | `docs/<name>/<name>.md` |
| Poster | `docs/<name>/<name>.md` |
| Analysis in R / in Python | `analysis/<name>.qmd` (the first also brings the helper and `data/`) |
| Figure drawn in Typst | `figures/<name>.typ` |
| Table made by hand | `tables/<name>.csv`, opened as a grid |

What a manuscript makes is written at its top, and can be changed at any time ([3.6](#36-what-it-makes-and-settings-for-one-document)).
Whatever you add, nothing in `octavo.config.py` needs editing.

### 2.4 What is in a project

```
study/
  octavo.config.py   the project's settings
  literature/        literature.bib (the bibliography, exported from your reference manager) and,
                     in priorwork/, what Priorwork delivers
  AGENTS.md          the project's working rules for AI assistants
  CLAUDE.md          one line that points Claude Code at AGENTS.md
  README.md          a few lines for you to finish
  docs/<name>/       <name>.md (the manuscript), and appendix.md and main.typ (the journal layout) if any
  analysis/          the .qmd files and the helper (octavo.R, or octavo_helper.py for Python)
  data/raw/          the data as you got it (not in git; describe it in data/raw/README.md)
  data/derived/      data the analysis made (not in git)
  figures/           figures you make: drawn in Typst (<name>.typ), photos
  tables/            tables you make (<name>.csv)
  assets/            what the analysis and Octavo write — never edited by hand
  build/             the output, a folder per output (pdf/, slides/, word/, …); can be deleted
```

The rule of the folders: **what you make** (`docs/`, `analysis/`, `figures/`, `tables/`,
`data/raw/`) and **what is made for you** (`assets/`, `build/`, `data/derived/`) are kept
apart. Never edit the second kind; change what it is made from.

### 2.5 Examples are marked as examples

What **Fill them with examples** writes is marked: a comment in the manuscript, a mark in the
made-up numbers, a figure that is a box with an ×. **Check before submitting** counts what is
left, and refuses to pass a project whose numbers are still the made-up ones (before the
analysis has run, the PDF would carry fake numbers). Replace the content and delete the mark
with it.

### 2.6 A project made with an earlier version

It keeps building as before. **Check before submitting** says when its manuscripts, its
notation or its `AGENTS.md` can be brought up to date; ask your AI assistant to do it. It first
shows what it would change, and keeps a rewrite of the notation only if every output comes out
the same.

---

## 3. Writing manuscripts

| What | How you write it |
|---|---|
| Heading | `# Analysis {#sec-analysis}` — `#` is the top section; no number; the label makes it referable |
| Abstract | a `# Abstract` section |
| Citation | `@key`, `[@key; @key2]`, possessive `\poscite{key}` ("Smith and Taylor's (2003)") |
| A number from the analysis | `{{n_obs}}`, `{{coef_x:.2f}}` (§4) |
| Figure | `![Trend](../../assets/figures/trend.png){#fig-trend}` |
| Table | a Markdown table with `: Caption {#tbl-desc}` right below it, or the caption line alone for a table from the analysis or from `tables/` |
| Equation | `$$ … $$ {#eq-model}` |
| Reference | `@fig-trend` → "Figure 2.1" |
| Title, author, date | the lines between `---` at the top |

Typing `@` offers the citation keys and `{{` the analysis's values; a key that is not in the
`.bib` is underlined when you save.

### 3.1 Referring by label, never by number

Numbers are **never typed** — not in headings, captions or prose. Label things and refer by
name; the numbers are given when it is typeset, so adding or moving a section never means
fixing references.

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

- Labels start with `fig-`, `tbl-`, `eq-` or `sec-` and continue with letters, digits, `-`
  and `_`. Japanese may follow directly (`@fig-trendに示す`).
- `@fig-trend` reads "Figure 2.1" ("図2.1" in a Japanese document), `@eq-model`
  "Equation (2.1)", `@sec-analysis` "Section 2"; `[-@eq-model]` is the number alone.
- A paper numbers straight through (Figure 1, Figure 2; in the appendix Figure A1); lecture
  notes, slides and posters number by section (Figure 3.2 is the second figure of Section 3).
  **Settings for this document** changes it.
- Numbered: headings (except `{.unnumbered}`), figures and tables with a caption, and
  equations with a label.
- A heading `# Title {.appendix}` starts an appendix within the file (A, B, …).
- **Check before submitting** stops on a label that does not exist or is used twice.

### 3.2 Cases, questions and other numbered blocks

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

- Kinds: `case`, `question` (one numbering: Case 1.1, Question 1.2), `aside`, `nb`, `memo`
  (unnumbered), and `theorem`, `lemma`, `proposition`, `corollary`, `definition`, `example`
  (another numbering), `remark` (unnumbered).
- The label starts with the kind (`#question-why`); `@question-why` reads "Question 1.2".
- **Write a block once.** `restate` repeats it elsewhere with its number; `list-of` lists every
  block of the kinds given (add `.titles` for number, title and page only).
- To rename a kind or add one, ask your AI assistant (the setting is `theorem_envs`).

### 3.3 Math

Write LaTeX notation between dollar signs; it becomes Typst math, Word equations, or stays
LaTeX.

```markdown
The estimate is $\hat\beta = {{coef_x:.3f}}$, with $y_i \sim \mathcal{N}(\mu, \sigma^2)$.

$$
\begin{aligned}
y_i &= \beta_0 + \beta_1 x_i + \varepsilon_i \\
\operatorname{Var}(\varepsilon_i) &= \sigma^2
\end{aligned}
$$
```

- Inline `$x$` has no space inside the dollars; a literal dollar is `\$`.
- Display math sits on its own lines with blank lines around it. For several lines use
  `aligned`, not `align`.
- A one-line `\newcommand{\E}{\mathbb{E}}` anywhere in the manuscript works everywhere.
- Keep a value with a thousands separator outside the math (`$N$ = {{n_obs}}`).

### 3.4 Figures

Write the `.png` in the manuscript, with the path relative to the manuscript
(`../../assets/figures/` from a manuscript in `docs/<name>/`). The PDF gets the sharp `.pdf`
beside it, Word the `.png`; the analysis writes both. `{width=60%}` after a figure sets its
width.

**A source or note under a figure or table** goes in `::: {.figure-note}` right after it
(after a table's caption line): small type, on the same page, not part of the caption. On a
slide the figure shrinks to leave room for it.

```markdown
![Officials by level of government[^src]](../assets/figures/staff.png){#fig-staff}

::: {.figure-note}
Source: National Personnel Authority, *Annual Report 2025*.[^checked]
:::

[^src]: Full-time staff only.
[^checked]: Retrieved 1 October 2026.
```

**Photos and other images you have** go in `figures/` and are placed from there. Octavo does
not shrink them, so resize a large photo first (about 2,000 pixels on the long side is plenty).

```markdown
![The council chamber](../figures/chamber.jpg){#fig-chamber width=70%}
```

**A diagram drawn in Typst (instead of TikZ).** **+** → **Figure drawn in Typst** writes
`figures/<name>.typ` with a small helper for boxes and arrows:

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

It is drawn into `assets/figures/` whenever you build, and placed like any figure. Anything
Typst can draw works; your AI assistant can draw one from a description.

### 3.5 Tables

A short table can be a Markdown table in the manuscript. Two other kinds are placed with a
caption line alone — `: Caption {#tbl-name}` with no table next to it:

- **From the analysis**: `ov_table(tab, "summary")` in the `.qmd`, and
  `: Descriptive statistics {#tbl-summary}` in the manuscript ([4.2](#42-handing-over-numbers-figures-and-tables)).
- **Made by hand**: **+** → **Table made by hand** opens a grid (also **Edit as a Table** at
  the top of any `.csv` in `tables/` or `data/`). The first row is the heading; leave a heading
  cell empty to the right of a filled one to merge them, and then the second row is a heading
  too. Number columns are right-aligned, and a column with long text wraps. Excel can open the
  file too (on Windows, through *Data → From Text/CSV*).

### 3.6 What it makes, and settings for one document

**What a document makes is `outputs:` at the top of the manuscript.** Without it, a PDF.

```markdown
---
title: Title of the Paper
outputs: [pdf, word]
---
```

| Output | What it makes |
|---|---|
| `pdf` | a PDF: the paper's layout if there is a `main.typ` beside the manuscript, otherwise the A4 handout layout (a cover and contents) |
| `word` | Word |
| `slides` | slides |
| `slides-handout` | the same slides to hand out ([7.1](#71-slides)) |
| `script` | the speaker script (each slide with its `::: notes`) |
| `poster` | a poster ([7.2](#72-posters)) |
| `tex`, `beamer` | LaTeX, LaTeX slides (need TeX) |

**A manuscript made of class sessions says `sessions: true`** (see
[Making course materials](https://yoshida-kd.github.io/octavo/lectures/)). The title goes in
`title:`; don't write a `# Title` heading — a `#` heading is a section.

**Settings for this document**, under each manuscript in the sidebar, changes the settings
that differ per journal or talk: the citation style, word and character limits, the look of
slides and posters, the handout's layout, numbering. A value you choose is written as one line
at the top of the manuscript and applies to it alone; what is not written there follows the
project's **Settings**.

### 3.7 Page breaks and slide breaks

Each goes on a line of its own:

```markdown
\newpage

\newslide

\newslide{Another title}
```

- `\newpage` starts a new page (PDF, Word, LaTeX). Slides ignore it.
- `\newslide` starts a new slide, titled like the one before with " (cont.)".
  `\newslide{Title}` gives it that title, and `\newslide{}` makes a slide with no title (more
  room for a figure). Outputs other than slides ignore it.

### 3.8 One sentence to a line

Write each sentence on a line of its own. Changes then show sentence by sentence in git, and
your AI assistant edits one sentence without touching the next. **Check before submitting**
points out lines broken in the middle of a sentence; your AI assistant can put a whole
manuscript right in one go.

---

## 4. The analysis

**The manuscript never contains a result.** Numbers, figures and tables are made by the
analysis (`.qmd`) and pulled in on every build, so re-running an estimation can never leave
the text describing the old one.

```
analysis/*.qmd  --quarto-->  assets/values/*.json      {{…}} in the text
                             assets/figures/*.pdf|png  figures
                             assets/tables/*           tables
```

### 4.1 Adding an analysis

**Add an analysis** (under Analysis in the sidebar) asks R or Python and a name, writes
`analysis/<name>.qmd` and opens it. The first analysis also sets up the project's **analysis
environment** — its own R and Python packages (renv and `.venv`), recorded in `renv.lock` and
`requirements.txt` so a coauthor gets the same ones. Later, **Tools → Set Up This Project's
Analysis Environment** does it again (after adding a package to `requirements.txt`, say).

Opening a `.qmd` shows the HTML it last rendered beside it, following the cursor; it is
updated when the analysis runs, never by opening or saving.

### 4.2 Handing over numbers, figures and tables

A new `.qmd` already loads its helper. Register what the paper shows:

| What | In the analysis | In the manuscript |
|---|---|---|
| A number | `ov_value("n_obs", nrow(d))` | `{{n_obs}}` |
| A figure | `ov_figure(p, "trend")` | `![Trend](../../assets/figures/trend.png){#fig-trend}` |
| A table | `ov_table(tab, "summary")` | `: Descriptive statistics {#tbl-summary}` |

- `ov_figure(p, name)` takes a ggplot (or a function that draws) and writes the `.pdf` and the
  `.png`. `ov_table(tab, name)` takes a data frame; the caption belongs to the manuscript.
- `ov_pval(p)` formats a p-value (`.023`, `< .001`). `ov_palette(3)` gives colours that stay
  distinct for every kind of colour vision.
- Running one chunk on its own (Run Cell) shows `ov_value()`'s value without recording it:
  only running the whole `.qmd` changes the numbers in the manuscript.
- A `.qmd` brought in from elsewhere loads the helper with this line (the same in every new
  `.qmd`; it works both when rendering and when you run a chunk on its own):

```r
source(if (file.exists("octavo.R")) "octavo.R" else file.path("analysis", "octavo.R"))
```

### 4.3 How numbers look

| Value | Example | Shown as |
|---|---|---|
| Whole number | `nrow(d)` | `1,523` |
| Decimal | `coef(m)[["x"]]` | `0.342` (3 places by default) |
| Text | `ov_pval(p)` | as it is |

`{{coef_x:.2f}}` in the manuscript chooses the format. A name with no value stays as
`{{name}}` in the PDF and is reported.

### 4.4 When the analysis runs

- **Building** runs a `.qmd` when it, or a file it depends on, changed since the last run. What
  counts is the contents: switching git branches and back does not make a `.qmd` out of date.
- The **preview** never runs it; the bar above the PDF says when something is out of date, with
  **Run** and **Mark as up to date** (when you know nothing it uses has changed).
- The sidebar's **Analysis** shows each `.qmd`; ▶ runs one, **Run the stale ones** all of them.
  An open `.qmd` has ▶ at the top right of the editor too.
- **A slow step** (cleaning the data, fetching it from the web) goes in its own `.qmd` marked
  manual: building never runs it, only you do. Write at its top:

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

  Have it skip the fetch when the file is already there, and write where it came from and
  when into `data/raw/README.md` — that file is the only record once `data/raw/` is out of git.
- If an analysis fails, building stops — it would otherwise typeset around old numbers.

### 4.5 R packages

**R packages a `.qmd` uses are installed for you**, a `.qmd` brought in from elsewhere included.
Opening or saving an R `.qmd` checks for packages it uses that are not installed and offers to
install them; running it from the sidebar installs them by itself. They go into the project's
environment and are recorded in `renv.lock`. A package that is not on CRAN (GitHub,
Bioconductor) is named, with how to install it — or ask your AI assistant.

### 4.6 Python

Pick **Analysis in Python** and the `.qmd` is written in Python, with the same functions under
the same names; the manuscript is written exactly as for R:

```python
ov_value("n_obs", len(d))              # {{n_obs}}
ov_value("coef_x", model.params["x"])
ov_figure(fig, "trend")                # a matplotlib Figure
ov_table(tab, "summary")               # a pandas DataFrame
```

R and Python `.qmd` files can live in one project.

### 4.7 Using Octavo with `.qmd` files alone

A project need not have a manuscript. A report or an assignment written entirely in Quarto can
live in `analysis/`, and Octavo looks after its environment and runs it (▶). Its output lands
beside the `.qmd`, as Quarto always writes it; use the Quarto extension's **Preview** to look
at a PDF.

---

## 5. Citations

### 5.1 The bibliography

Export your library from your reference manager (Zotero or any other) as BibTeX or BibLaTeX to
`literature/literature.bib`. With Zotero, Better BibTeX's "Keep updated" export keeps it current
and the keys stable. **Octavo never edits the `.bib`.** **Tools → Check the Bibliography** finds
keys you cite that are not in it, and entries that look incomplete.

### 5.2 The style

**Settings → Citation style (CSL)** (or **Settings for this document**, for one paper) offers the
common styles; type an ID from <https://www.zotero.org/styles> for any other. It applies to every
output at once.

`\poscite{key}` writes a possessive citation ("Smith and Taylor's (2003)"); the joining of several
authors is an approximation of the style's rules, so read it once.

The bibliography goes at the end. A `# References` heading as a paper's last section only marks
its place. To put it somewhere else, write `::: {#refs}` and `:::` there.

### 5.3 Japanese and English works together

In a Japanese document, English works and the citations follow your style; works marked
`langid = {japanese}` in the `.bib` take one Japanese form whatever the style. **Settings →
Form of Japanese works** chooses the form:

| Choice | Japanese works look like |
|---|---|
| standard (default) | 山田太郎・田中花子 (2020)「題」『誌名』12(3): 1–20. |
| full-width | 山田太郎・田中花子（2020）「題」『誌名』12巻3号、1–20頁。 |
| period | 山田太郎・田中花子．2020．「題」『誌名』12巻3号、1–20頁。 |

The full-width form follows what articles in 年報行政研究 commonly print, the period form what
author–date articles in 年報政治学 print; neither journal's rules prescribe a form, so follow a
journal's own instructions where it has them.

### 5.4 Zotero

If Zotero runs on the same machine:

- **Settings → Main Zotero collection (the .bib)** chooses the collection the `.bib` is fetched from, from
  the same tree as in Zotero (the collections under it come too).
- **Tools → Pull References from Zotero** fetches it.

If Zotero does not run on this machine (a server over SSH, say), **Use the Zotero Web API (API
Key)…** asks for an API key from <https://www.zotero.org/settings/keys> once; the key is kept in
your own settings, not in the project. Pin the citation keys in Better BibTeX so they are the
same through the web.

**Keeping the main collection tidy.** Collections that only feed the paper — one per literature
survey, say — are **linked collections** (**Choose the Linked Zotero Collections**); they never go
into the `.bib`. **Tidy the Main Zotero Collection** compares the main collection with what the
manuscripts cite and lists, as a tick list, the papers to add (cited, found in a linked collection
or the library) and to take out (in it, but cited nowhere). Untick what to leave and confirm. It
only changes which collections an entry is in; it never deletes or edits one. It needs the setting
**Let octavo bib tidy change the Zotero collection** and a key with write access; the button asks.

### 5.5 With a literature survey (Priorwork)

If you gather the literature with [Priorwork](https://yoshida-kd.github.io/priorwork/):

1. Right-click the paper → **Ask Priorwork for the Literature**. The request is copied; paste it
   to the agent in your Priorwork window. (Set your Priorwork workspace once in **From Priorwork**,
   and the request is sent there as a file instead.)
2. Priorwork reads the manuscript (never changing it), gathers the included papers in a Zotero
   collection of the survey's own, and delivers its writing — a draft, a synthesis, or additions
   to the manuscript in progress — into `literature/priorwork/`.
3. **From Priorwork** in the sidebar lists what arrived. **Copy a Request to Take It into the
   Manuscript** gives you a request for your AI assistant: it reads the delivery with the
   manuscript, proposes where each part goes, and waits for your answer.
4. A paper not in your `.bib` yet is cited as `@PRIORWORK:<DOI>`. Put it in Zotero, pull, then
   **Replace the Marks with the .bib Keys**.

Resting the cursor on a citation shows Priorwork's card for that paper: its question and
findings, and whether Priorwork read it in full or only the abstract.

---

## 6. Papers: from draft to submission

A paper is `docs/<name>/<name>.md` plus `main.typ`, **the layout you keep** (whatever a journal
wants). The title, authors, affiliation, e-mail and date come from the top of the manuscript
(`title:`, `author:`, `institute:`, `email:`, `date:`).

**The layout** follows LaTeX: jsarticle for a Japanese paper, article (11pt) for an English one.
Page 1 shows the length: the words or characters of the text without and with the notes, the
abstract's, and the number of figures and tables. To suit a journal (margins, fonts, a title
block of its own), ask your AI assistant to change `main.typ`.

**The appendix** (right-click the paper → **Add an appendix**) is typeset as a PDF of its own
beside the paper's, whenever there is one. Its sections are A, B, …, its figures and tables A1,
A2, …, and its pages A-1, A-2, …. **Settings for this document** can put it after the text in one
PDF instead.

### 6.1 Before you submit

**Tools → Check Before Submitting** looks at everything in one pass: missing figures and tables,
unresolved `{{…}}`, made-up values, an analysis out of date, citation keys, labels, template
leftovers, results typed into the text, blocks that will not be read as written, and the
submission limits. Set the limits in **Settings for this document** (word limit, character limit
for Japanese journals, the abstract's).

A number that is not a result (a grading split, a year) is kept out of the "typed result" check
by writing it `[40%]{.no-lint}`.

### 6.2 Blind review

Mark what identifies you:

```markdown
::: {.no-anonymous}
Acknowledgements: this research was funded by ...
:::
```

Then ask your AI assistant for the anonymous version (and the package for the journal): the
marked parts, the authors, the affiliation and the e-mail are left out, and the package is
checked for your name. The next ordinary build switches everything back.

### 6.3 After you send it

Ask your AI assistant for these; each is one command it knows.

- **Packaging for the journal**: the files, flattened into one folder or zip.
- **Coauthors' Word edits**: a list of their tracked changes and comments. Apply them to the
  manuscript yourself — the Word file has the numbers typed in, so it is never converted back.
- **Keeping the version you sent**: a git tag, and the PDF on a GitHub Release.
- **Revisions**: which numbers moved since the version you sent.
- **Data**: a record of what `data/` held, and whether it has changed since.
- **A replication package**: the analysis, the values, the figures and tables, the settings and
  the record of the data (raw data only if you say so).

---

## 7. Slides and posters

Lecture notes — one file for an A4 handout and a deck per session — have a page of their own:
[Making course materials](https://yoshida-kd.github.io/octavo/lectures/).

### 7.1 Slides

A manuscript with `outputs: [slides]`: with `#` and `##` headings, `#` is a section and `##` a
slide; with one level, each heading is a slide. The title slide comes from the top of the
manuscript, and figures fit the room left on the slide. **Settings for this document** sets the
aspect ratio, the accent colour, heading numbers, a divider slide for each section and the section
name in the corner.

```markdown
## A long heading for the handout {slide-title="Short title"}

\newslide

### A heading that stays on the same slide {.same-slide}

\newslide{Another title}
```

- `{slide-title="…"}` replaces a heading's title on the slide only.
- `{.same-slide}` keeps a heading on the current slide, in bold.
- `{.no-title}` on a heading: a new slide with no title, so a figure gets the room.
- A slide with more than fits goes on over a new slide titled "Title (cont.)", and the build
  says so; put a `\newslide` where you want it to break instead.

`::: notes` holds what you will say: it never appears on the slides, only in the **speaker
script** (add `script` to `outputs:`, or pick it for the preview's third column) — each slide as
projected, shrunk, with its notes underneath.

**A deck to hand out.** Add `slides-handout` to `outputs:` and the same slides come out a second
time: what you mark `.screen-only` is on the projected deck only, what you mark `.no-screen` on the
handed-out deck only.

```markdown
The sample has [1,523 cases]{.screen-only}[\_\_\_\_\_\_]{.no-screen}.
```

**References on slides**: **Settings for this document → References of the slides** — a last slide
in small type, none, an A4 sheet of the deck's references beside it, or both.

### 7.2 Posters

For a poster session. A manuscript with `outputs: [poster]` (**+** → **Poster**) becomes one
PDF, by default **A0 portrait**, with **each `#` heading as one cell** filling a 2×3 grid from the
top left.

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
| `{span=2}` / `{rows=2}` after a heading | a cell two columns wide / two rows high |
| `{cell="3,2"}` | put it in column 3, row 2 |
| `logo` / `qr` / `qr_label` | logos on the left of the title band, a QR code (made from the URL) on the right |

**Settings for this document** sets the paper size (A0–A2, B0, B1), the orientation and the
grid; `poster_rows` at the top sets the rows' heights. Content that does not fit in its cell is reported when you build and
marked in red in the PDF: cut it or make the cell bigger. To make a poster from a paper, write
`outputs: [pdf, poster]` and mark what goes on the poster with `.on-poster` (written like
`.on-slides` in lecture notes).

---

## 8. Writing rules for your AI assistant

Rules on how you write, and a bank of phrasings you trust, can be handed to the AI assistant that
helps with the prose. They are Markdown files gathered in **packs**, in `~/.config/octavo/writing/`
for every project or in the project's `notes/writing/`. Before the assistant writes or revises a part
of a manuscript, it reads the rules and the phrases for that part, and follows them. A section can
also be planned paragraph by paragraph before it is written, and checked against the plan afterwards.

- Each manuscript in the sidebar has **Writing rules**: the packs it uses, their files and entries
  (right-click an entry to turn it off for that manuscript), **Choose the Packs…** (most general
  first; where two disagree, the later one wins) and **Show the Rules for Where the Cursor Is**
  (also in the editor's right-click menu) — what the assistant reads there.
- How to make a pack, write its files, choose what each manuscript reads, plan paragraphs and check
  them: **[Writing support](https://yoshida-kd.github.io/octavo/writing/)**.

---

## 9. Making it yours

- **Settings** (the project's defaults) and **Settings for this document** cover what changes
  often. Click a setting to change it; a filled dot means it is written, an empty one that the
  default is used.
- **The look of anything** — the slides, the handout, a paper's layout, how numbers and
  references read, the manuscripts a new document starts from — comes from a template you can
  replace, for one project or for all of yours. Ask your AI assistant to copy the template and
  change it as you describe; after an Octavo update it can show what changed in the original.
- **Word styles**: ask the assistant for a Word style file, open it in Word, change the styles
  (`Heading 1`, `Body Text`, …) and save it; Word output uses it from then on.
- **Fonts**: papers are set in BIZ UDMincho with Libertinus Serif, handouts and slides in BIZ
  UDGothic with Inter. Set up installs them. **Settings for this document → Body font** changes the
handout's; for anything else, ask your AI assistant.

---

## 10. Working with an AI assistant

The project's `AGENTS.md` holds its rules — never type a result into the manuscript, never edit
`data/raw` or what is generated, never edit the `.bib` — and is read by Claude Code, GitHub
Copilot, Codex and Antigravity. Octavo's [reference](https://yoshida-kd.github.io/octavo/reference/)
comes with Octavo itself, so the assistant can look up any command or setting for the version
you have installed. **Check before submitting** catches anything that slips through.

Things to ask, in your own words:

- "Write the analysis of `data/raw/survey.csv` and put the numbers in the results section."
- "Add a robustness section with the model without the outliers."
- "Make the anonymous version and the package for the journal."
- "Which numbers in the paper changed since I submitted it?"
- "Take the Priorwork draft into the literature review."
- "Draw the causal diagram in Typst: Z causes X and Y, X causes Y."
- "Change the slides to 4:3 and make the accent dark green."

---

## 11. What to check on your own machine

Octavo's tests typeset every output on Linux, macOS and Windows, and run the example analysis
through Quarto, in R and in Python. What they cannot see:

- **How citations look in your style** — run **Octavo: Check How Citations Come Out** from the
  Command Palette and read it.
- **Fonts** — look at your first PDF; **Tools → Diagnose the Environment** lists missing fonts.
- **LaTeX** — no test compiles LaTeX output. Check your first LaTeX or Beamer PDF.
- **Your own R setup** — the example runs; your packages are yours to check.

If something looks wrong, please open an [issue](https://github.com/yoshida-kd/octavo/issues)
with what **Diagnose the Environment** shows.
