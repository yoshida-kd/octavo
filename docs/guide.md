# Octavo guide

> This is the source of the guide. Read it at **<https://yoshida-kd.github.io/octavo/guide/>**. <!-- pages:skip -->

**The quantitative social science starter pack**

Octavo turns Markdown manuscripts into papers, handouts and slides — Typst (to PDF), Word,
and, if you have TeX, LaTeX and Beamer — with the citations from one `.bib` file and the
numbers, figures and tables from your Quarto analysis. This guide is the manual; the
[README](https://github.com/yoshida-kd/octavo#readme) is the short introduction.
[日本語の手引き](https://yoshida-kd.github.io/octavo/ja/guide/)

---

## 1. Install

Octavo needs a few tools besides itself: **pandoc** (conversion), **Typst** (typesetting to
PDF), **Quarto** and **R** (the analysis), the **fonts**, and **uv** (which installs the
`octavo` command). One setup installs all of them. Pick your system:

| You use | Read |
|---|---|
| Ubuntu or another Debian-like Linux — a PC, or a server you reach over SSH | [Linux](#linux) |
| A Mac | [macOS](#macos) |
| Windows | [Windows](#windows) — WSL (recommended) or Windows itself |

On every system there are two ways to do it: **with VS Code** (install the extension and
press one button) or **from a terminal** (four commands). They install the same things.
LaTeX is not included — it is optional (see [LaTeX, if you want it](#latex-if-you-want-it)).

### Linux

Ubuntu 24.04 is what Octavo is tested on; Debian and other Ubuntu versions work too (a font
the distribution doesn't package is replaced by Noto). You need a user who can use `sudo`.

**With VS Code**

1. Install [VS Code](https://code.visualstudio.com/) on the computer you work at.
   *If Octavo is to run on a server*, also install the **Remote - SSH** extension and
   connect to the server (**Remote-SSH: Connect to Host…**); everything below then happens
   on the server.
2. Install the **Octavo** extension (search "Octavo" in the Extensions view, publisher
   yoshida-kd). Over Remote-SSH, click **Install in SSH: …** so it lands on the server.
3. Open a folder. The extension checks the tools and offers **Set up**. Press it: a
   terminal opens, asks for your password once (for `sudo`), and installs everything.
   It takes a while the first time (R and the fonts are the large part).
4. When it finishes, the extension checks again. Nothing to report means you are done.

**From a terminal**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # uv
source ~/.local/bin/env                           # put uv on PATH in this terminal (or open a new one)
uv tool install octavo-kit                        # the octavo command
octavo setup                                      # pandoc, Typst, Quarto, fonts, R, renv (asks for your password)
octavo doctor                                     # everything should read ok
```

`octavo setup` adds CRAN's repository so that R is the latest release, and points R at
Posit Package Manager so packages install as ready-made binaries instead of compiling.

### macOS

**First install Homebrew**, which Octavo uses to install everything else. Open Terminal and
run the one line from [brew.sh](https://brew.sh):

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow what it prints at the end (on Apple Silicon it asks you to add Homebrew to your
`PATH`), then open a new Terminal window.

**With VS Code**

1. Install [VS Code](https://code.visualstudio.com/) and the **Octavo** extension.
2. Open a folder and press **Set up** when the extension offers it. A terminal opens and
   installs everything through Homebrew (your password may be asked for R and Quarto).
3. If the extension says it cannot find `octavo` afterwards, quit VS Code completely
   (⌘Q) and start it again — it was started before the new command existed.

**From a terminal**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # uv
source ~/.local/bin/env                           # put uv on PATH in this terminal (or open a new one)
uv tool install octavo-kit                        # the octavo command
octavo setup                                      # pandoc, Typst, Quarto, fonts, R, renv (with Homebrew)
octavo doctor                                     # everything should read ok
```

R is CRAN's own build (Homebrew's `r` cask), so CRAN's binary packages work.

### Windows

There are two ways. **WSL is recommended**: Octavo is developed and tested on Linux first,
and WSL gives you exactly that inside Windows. Use Windows itself only if you cannot use WSL.

#### Windows with WSL (recommended)

1. **Install WSL.** Open PowerShell *as administrator* (right-click the Start button →
   *Terminal (Admin)*, or *Windows PowerShell (Admin)* on Windows 10) and run:

   ```powershell
   wsl --install
   ```

   Restart when it asks. Ubuntu then starts and asks you to choose a user name and password
   — remember the password, the setup asks for it.
2. Install [VS Code](https://code.visualstudio.com/) on Windows, then the **WSL** extension
   and the **Octavo** extension.
3. In VS Code, **WSL: Connect to WSL** (bottom-left corner). Open a folder *inside* Ubuntu
   (for example `/home/<user name>`).
4. The Octavo extension offers **Set up**; press it and enter the Ubuntu password. From
   here on it is the [Linux](#linux) setup.

From a terminal instead: open *Ubuntu* from the Start menu and follow
[Linux → From a terminal](#linux).

#### Windows itself (without WSL)

This uses [winget](https://learn.microsoft.com/windows/package-manager/winget/), which comes
with Windows 11 and current Windows 10 (if `winget` is not found, install *App Installer*
from the Microsoft Store). No administrator rights are needed. LaTeX is not
installed on Windows (install MiKTeX yourself if you need it).

**With VS Code:** install [VS Code](https://code.visualstudio.com/) and the **Octavo**
extension, open a folder, and press **Set up**. On a PC without WSL the extension uses
Windows' own tools. When it has finished, restart VS Code so it sees the new commands.

**From a terminal:** open PowerShell (not as administrator) and run:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"   # uv
```

Close PowerShell and open a new one (so it finds `uv`), then:

```powershell
uv tool install octavo-kit    # the octavo command
octavo setup                  # pandoc, Typst, Quarto, fonts, R, renv (with winget)
```

Open a new PowerShell once more and check:

```powershell
octavo doctor                 # everything should read ok
```

Two habits keep a project working on every system: write paths with `/`
(`../assets/figures/trend.png`), and keep the upper and lower case of file names exactly as
the manuscript writes them — Windows does not tell `Trend.png` from `trend.png`, Linux does.

### Check that it works

```bash
octavo doctor       # what is installed; anything missing comes with the command that installs it
octavo selftest     # typesets a small sample and prints the citations as they come out
```

`octavo doctor` marks each tool ok, missing, or a note (nice to have). `octavo selftest`
builds a sample with English and Japanese references, a table, a figure and
cross-references in a temporary folder and shows how the citations came out — run it once
per machine and read it.

### Updating

```bash
uv tool upgrade octavo-kit    # the newest octavo
octavo setup                  # the tools it expects (safe to run again: what is there is skipped)
```

In VS Code, update the extension and run **Tools → Install or Update the Tools** in the
Octavo sidebar.

### LaTeX, if you want it

Everything above makes PDFs through Typst; LaTeX is only needed for the `latex` and
`beamer` formats. On Linux, `octavo setup --with-tex` adds TeX Live (several GB). On a Mac,
install [MacTeX](https://www.tug.org/mactex/); on Windows, [MiKTeX](https://miktex.org/).
`octavo doctor` lists TeX separately and does not count it as missing.

### The language Octavo speaks

Messages come out in English, or in Japanese when your system is set to Japanese.
`export OCTAVO_LANG=ja` (or `en`) chooses. This is only the language of the messages; the
language a project is *written* in is `lang` in its `octavo.config.py`
(`octavo init --lang ja|en`). The VS Code extension follows VS Code's language.

---

## 2. Your first project

### Try the example first

```bash
octavo init demo --all --example
cd demo
octavo build --compile        # runs the analysis, then typesets everything to PDF
```

This makes a project with an analysis of made-up data, a paper, a slide deck and lecture
notes that use it. The PDFs land in `build/`.

### Start your own

`octavo init` makes the frame of a project; everything else is added with `octavo new`,
as many of each as you like:

```bash
octavo init study --with analysis,paper   # the frame, an analysis and a paper
cd study
octavo env                                # the project's analysis environment (.venv and renv)
```

```bash
octavo new analysis model           # analysis/model.qmd (the first also brings octavo.R and data/)
octavo new paper example-paper      # papers/example-paper/: paper.md and the layout main.typ
octavo new paper example-paper --appendix   # add appendix.md (to an existing paper too)
octavo new paper example-paper --tex        # add main.tex for LaTeX (to an existing paper too)
octavo new slides example-talk      # slides/example-talk.md
octavo new lecture example-lecture  # lectures/example-lecture.md
octavo new figure dag               # figures/dag.typ, a figure drawn in Typst
octavo new table compare            # tables/compare.csv, a table you make by hand
```

`init --with` takes the same parts (`--with lecture`, `--with analysis,slides=talk`; `--all`
for every kind), and `--example` fills the parts with worked examples instead of bare
headings. A document is referred to by its name — the folder for a paper, the file name for
slides and lecture notes: `octavo build example-paper`.

### What is in a project

```
study/
  octavo.config.py   the project's settings
  literature.bib     the bibliography, exported from your reference manager
  CLAUDE.md          the project's working rules (also read by Claude Code)
  README.md          a few lines for you to finish
  papers/<name>/     paper.md, and main.typ (the journal layout)
  slides/<name>.md   talks
  lectures/<name>.md lecture notes
  analysis/          the .qmd files and octavo.R
  data/raw/          the data as you got it (not in git; describe it in data/raw/README.md)
  data/derived/      data the analysis made (not in git)
  figures/           figures you make: drawn in Typst (<name>.typ), photos
  tables/            tables you make (<name>.csv)
  assets/            what the analysis and octavo build write — never edited by hand
    values/          the numbers behind {{…}}
    figures/         figures (.pdf and .png)
    tables/          tables (.typ, .tex, .md)
  build/             the output; everything here can be deleted and rebuilt
```

`octavo.config.py` already finds every manuscript and analysis in these folders, so adding
one never means editing it.

### The analysis environment

Tools such as R and Quarto are installed once per machine. **The packages an analysis uses
belong to the project**:

```bash
octavo env    # .venv (uv) with requirements.txt, renv with knitr and rmarkdown
```

Run it again after adding a package to `requirements.txt`; after `install.packages()` in R,
run `renv::snapshot()`. Git keeps the records (`requirements.txt`, `renv.lock`), not the
installed packages, so a coauthor gets the same environment from the same command.

### Examples are marked as examples

What `--example` writes carries a mark — an `octavo:example` comment, `_placeholder` in the
values, a figure that is a box with an × — and `octavo check` counts what is left. Replace
the content and delete the mark with it. **Placeholder values are fatal in `octavo check`**:
before the analysis has ever run, every `{{…}}` still resolves, and the PDF would carry fake
numbers.

---

## 3. Writing manuscripts

| What | How you write it |
|---|---|
| Heading | `## Analysis {#sec-analysis}` — no number; the label makes it referable |
| Abstract | a `## Abstract` section (papers) |
| Citation | `@key`, `[@key; @key2]`, possessive `\poscite{key}` ("Smith and Taylor's (2003)") |
| A number from the analysis | `{{n_obs}}`, `{{coef_x:.2f}}` (§4) |
| Figure | `![Trend](../../assets/figures/trend.png){#fig-trend}` |
| Table | a Markdown table with `: Caption {#tbl-desc}` right below it, or the caption line alone for a table from the analysis or from `tables/` |
| Equation | `$$ … $$ {#eq-model}` |
| Reference | `@fig-trend` → "Figure 2.1" |
| Title, author, date | the YAML front matter at the top |

### Referring by label, never by number

Numbers are **never typed** — not in headings, captions or prose. Label things and refer by
name; the numbers are given when it is typeset, so adding or moving a section never means
fixing references.

```markdown
## Analysis {#sec-analysis}

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
  and `_` — Quarto's convention. Japanese may follow directly (`@fig-trendに示す`).
- `@fig-trend` reads "Figure 2.1" ("図2.1" in a Japanese document), `@eq-model`
  "Equation (2.1)", `@sec-analysis` "Section 2"; `[-@eq-model]` is the number alone.
- Numbering is by section (Figure 3.2 is the second figure of Section 3);
  `crossref_numbering: 'document'` numbers straight through.
- Numbered: headings (except `{.unnumbered}`), figures and tables with a caption, and
  equations with a label.
- A heading `# Title {.appendix}` starts an appendix within the file (A, B, …).
- `octavo check` stops on a label that does not exist or is used twice.

### Cases, questions and other numbered blocks

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

- Kinds: `case`, `question`, `aside` (one numbering: Case 1.1, Question 1.2), `nb`, `memo`
  (unnumbered), and `theorem`, `lemma`, `proposition`, `corollary`, `definition`, `example`
  (another numbering), `remark` (unnumbered). Numbered by section, like figures.
- The label starts with the kind (`#question-why`); `@question-why` reads "Question 1.2".
- **Write a block once.** `restate` repeats it elsewhere with its number, which links back
  to the original; `list-of` lists every block of the kinds given, with their text (add `.titles`
  for number, title and page only; `.list-of` alone lists every numbered kind).
- They look the same in every format: bold heading word, upright text (in Word, the
  paragraph style `Theorem`). Rename or add kinds with `theorem_envs`:

```python
'theorem_envs': {
    'case': 'Example case',
    'claim': {'name': {'ja': '主張', 'en': 'Claim'}, 'counter': 'case'},
    'hint': {'name': 'Hint', 'numbered': False},
},
```

### Math

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
  For an operator write `\newcommand{\Cov}{\operatorname{Cov}}`.
- Keep a value with a thousands separator outside the math (`$N$ = {{n_obs}}`); inside,
  the comma is set as punctuation.

### Figures

Write the `.png` in the manuscript, with the path relative to the manuscript
(`../../assets/figures/` from a paper, `../assets/figures/` from slides and lecture notes).
For each output Octavo picks the right file:

| Output | File used | Why |
|---|---|---|
| Typst (papers, handouts, slides) and LaTeX | `.pdf` | vector: sharp at any zoom, its text selectable |
| Word | `.png` | Word cannot embed a PDF figure |
| The editor's preview | `.png` | |

`ov_figure()` and figures drawn in Typst write both. `figure_width` sets the default width;
`{width=60%}` after a figure sets one.

**Drawing a figure in Typst (instead of TikZ).** `octavo new figure dag` writes
`figures/dag.typ` with a small `diagram()` helper — boxes and arrows:

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

`octavo build` draws it into `assets/figures/dag.pdf` and `.png` whenever the `.typ` changes,
and the manuscript places it like any figure. Anything Typst can draw works; parts several
figures share go in `figures/_parts.typ`; `json("/assets/values/analysis.json")` brings in
the analysis's numbers.

### Tables

A short table can be a Markdown table in the manuscript. Two other kinds are placed with a
caption line alone — `: Caption {#tbl-name}` with no table next to it:

- **From the analysis**: `ov_table(tab, "summary")` writes `assets/tables/summary.*`;
  the manuscript has `: Descriptive statistics {#tbl-summary}`.
- **Made by hand**: `octavo new table compare` writes `tables/compare.csv`; fill it in (in
  VS Code with **Edit as a Table**, or in Excel) and write `: The two schemes {#tbl-compare}`.
  The first row is the heading; an empty heading cell to the right of a filled one is merged
  into it (as Excel writes merged cells), and then the second row is a heading too. Number
  columns are right-aligned, and a column with long text wraps. The file is UTF-8 (Shift_JIS
  is read too); in Excel on Windows, open it through *Data → From Text/CSV*.

### Settings for one document

Settings that change per journal or talk can go at the top of that manuscript, and then
apply to it alone:

```markdown
---
title: Title of the Paper
csl: apa
word_limit: 8000
targets: [typst, docx]
---
```

| Key | For | What |
|---|---|---|
| `csl` | all | citation style |
| `targets` | all | output formats |
| `word_limit`, `char_limit`, `abstract_word_limit`, `abstract_char_limit` | papers | submission limits (`octavo check`) |
| `typst_slides_*` | slides, lecture notes | the look of the decks (§7) |
| `date_format` | slides, lecture notes | how the date is shown |
| `first_section`, `handout_pagebreak`, `handout_font`, `handout_fontsize` | lecture notes | the handout (§7) |

`octavo config --doc <name>` lists them and `set` / `unset` changes one line; in VS Code,
**Settings for this document** under each manuscript in the sidebar.

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

### Handing over numbers, figures and tables

A new `.qmd` already loads the helper `octavo.R`. Register what the paper shows:

| What | In the analysis | In the manuscript |
|---|---|---|
| A number | `ov_value("n_obs", nrow(d))` | `{{n_obs}}` |
| A figure | `ov_figure(p, "trend")` | `![Trend](../../assets/figures/trend.png){#fig-trend}` |
| A table | `ov_table(tab, "summary")` | `: Descriptive statistics {#tbl-summary}` |

- `ov_figure(x, name, width, height)` takes a ggplot or a function that draws; it writes the
  `.pdf` and the `.png`.
- `ov_table(x, name, notes, align)` takes a data frame; the caption belongs to the manuscript.
- `ov_pval(p)` formats a p-value (`.023`, `< .001`).
- `ov_palette(3)` gives colours that stay distinct for every kind of colour vision;
  `ov_tint(col, 0.6)` lightens one for an area with text on it; `ov_scale_colour_cud()` /
  `ov_scale_fill_cud()` for ggplot2.

The header of a new `.qmd` is ready to hand out as one HTML file: the author from `meta` in
`octavo.config.py` (with `affiliation` and `email` if you write them), the date, a contents
list and numbered sections.

### How numbers look

| Value | Example | Shown as |
|---|---|---|
| Whole number | `nrow(d)` | `1,523` |
| Decimal | `coef(m)[["x"]]` | `0.342` (3 places by default) |
| Text | `ov_pval(p)` | as it is |

`{{coef_x:.2f}}` in the manuscript, or `ov_value(..., fmt = ".2f")`, chooses the format. A
name with no value stays as `{{name}}` in the output and is reported.

### When the analysis runs

`octavo build` runs a `.qmd` when it, or a file it depends on, changed since the last run.

```bash
octavo analysis              # which are out of date
octavo analysis run          # run the out-of-date ones
octavo build --no-analysis   # build without running anything
octavo values --diff         # which numbers in the text changed at the last run
```

- If Quarto is missing, the build warns and goes on. If an analysis fails, the build stops —
  it would otherwise typeset around old numbers.
- Several `.qmd` files are normal: each writes its own `assets/values/<name>.json`, and the
  manuscript sees all their values. List them in order when one feeds another:

```python
'analysis': [
    {'src': 'analysis/01-clean.qmd', 'manual': True},       # slow: only octavo analysis run runs it
    {'src': 'analysis/02-model.qmd', 'deps': ['data/derived/*']},
],
```

- In VS Code the sidebar's **Analysis** section shows each `.qmd` and runs it with one
  button. The preview never runs the analysis; it says when something is out of date.

### Other languages than R

Octavo only reads files, so a Python or Julia `.qmd` works if it writes
`{"name": value}` into `assets/values/<anything>.json`, figures as `.pdf` and `.png` into
`assets/figures/`, and tables into `assets/tables/`.

---

## 5. Citations

Export your library from your reference manager (Zotero or any other) as BibTeX or BibLaTeX
to `literature.bib`. With Zotero, Better BibTeX's "Keep updated" export keeps it current and
the keys stable. **Octavo never edits the `.bib`.**

```bash
octavo checkbib           # keys cited but missing from the .bib, and problems in the .bib
octavo csl get apa        # fetch a journal's style
```

The style is one line in `octavo.config.py` (`'csl': 'apa'`), for every format at once. Style
IDs are listed at <https://www.zotero.org/styles>.

**Japanese and English works together.** In a Japanese document, English works and the
citations follow your style; works marked `langid = {japanese}` in the `.bib` take one Japanese
form whatever the style:

```
Smith et al. (2003), (山田・田中 2020), 佐藤ほか (2018)

Smith, John, Ann Taylor, Bob Brown, and Carl Green. 2003. "An Example Article." Journal of Examples 4: 1–10.
山田太郎・田中花子 (2020)「日本語論文の例」『見本学会誌』12(3): 1–20.
```

`japanese_citation_form` chooses the form of Japanese works (in the project or at the top of a
manuscript; in VS Code under the document's settings):

| Value | Japanese works look like |
|---|---|
| `'standard'` (default) | 山田太郎・田中花子 (2020)「題」『誌名』12(3): 1–20. |
| `'fullwidth'` | 山田太郎・田中花子（2020）「題」『誌名』12巻3号、1–20頁。 |
| `'period'` | 山田太郎・田中花子．2020．「題」『誌名』12巻3号、1–20頁。 |

`'fullwidth'` follows what articles in 年報行政研究 commonly print, and `'period'` what
author–date articles in 年報政治学 print; neither journal's rules prescribe a form, so
follow a journal's own instructions where it has them. `citations_by_language: False` sets the
whole bibliography in `csl_locale` instead.

`\poscite{key}` writes a possessive citation ("Smith and Taylor's (2003)", 「山田・田中(2020)」);
the joining of several authors is an approximation of the style's rules, so read it once.

---

## 6. Papers: from draft to submission

A paper is `papers/<name>/paper.md` plus `main.typ`, **the journal layout you keep by hand**
(title block, fonts, margins). `octavo build` writes the body into `build/typst/<name>/`
and `main.typ` typesets it; `--compile` makes the PDF.

```bash
octavo build example-paper --compile            # PDF
octavo build example-paper --to docx            # Word
octavo build example-paper --compile --appendix # with appendix.md
```

For an appendix, `octavo new paper <name> --appendix`, then uncomment
`#show: octavo-appendix` and `#include "appendix.typ"` in `main.typ`. Its sections are A, B, …
and labels work across both files.

### Before you submit

```bash
octavo check           # everything in one pass; fatal problems give a non-zero exit
octavo lint            # results typed into the text, and nested lists out of line
```

`octavo check` looks at: missing figures and tables, unresolved `{{…}}`, placeholder values,
out-of-date analysis, citation keys and the `.bib`, labels, template leftovers, submission
limits, and the data fingerprints. Limits are set in the config or the manuscript
(`word_limit: 8000`, `char_limit` for Japanese journals).

### Blind review

```markdown
::: {.no-anonymous}
Acknowledgements: this research was funded by ...
:::
```

```bash
octavo build example-paper --anonymous
octavo bundle example-paper --anonymous   # checks the package for your name
```

`--anonymous` drops `.no-anonymous` blocks (and keeps `.anonymous-only` ones), removes the
author from the title block, and switches `main.typ`'s title block. The next ordinary build
switches everything back.

### Packaging for the journal

```bash
octavo bundle example-paper    # submission-example-paper.zip: the files, flattened into one folder
```

### After you send it

- **Coauthors' Word edits**: `octavo review returned.docx` lists their tracked changes and
  comments. Apply them to `paper.md` yourself — the Word file has the numbers typed in, so it
  is never converted back.
- **Keep the version you sent**: `octavo release example-paper v1-submitted` tags the commit
  and puts the PDF on a GitHub Release (needs the `gh` command).
- **Revisions**: `octavo values --diff example-paper-v1-submitted` shows which numbers moved
  since that version.
- **Data**: `octavo data hash` records a fingerprint of `data/`; `octavo data status` says
  whether anything changed since.
- **Replication package**: `octavo bundle --replication` collects the analysis, the values,
  the figures and tables, the config and the fingerprints (raw data only with
  `--with-raw-data`).

---

## 7. Slides and lecture notes

### Slides

`slides/<name>.md`: with `#` and `##` headings, `#` is a section and `##` a slide; with one
level, each heading is a slide. The title slide comes from the front matter. Figures fit the
remaining space on the slide.

```bash
octavo build example-talk --compile
```

| Key | Default | What |
|---|---|---|
| `typst_slides_aspect` | `'16-9'` | or `'4-3'` |
| `typst_slides_accent` | `'#0e2f92'` | the accent colour; `None` for plain black |
| `typst_slides_numbering` | `None` | heading numbers (`'1.'`, `'1.1'`) |
| `typst_slides_section_slides` | `False` | a divider slide for each `#` section |
| `typst_slides_running_header` | `True` | the current section in the top-left corner |
| `typst_slides_font` | BIZ UDGothic + Inter | the font |

**Where slides break, and their titles**, can be set in the manuscript; the handout and
other outputs are not affected:

```markdown
## A long heading for the handout {slide-title="Short title"}

::: {.slide}
:::

### A heading that stays on the same slide {.same-slide}

::: {.slide title="Another title"}
:::
```

- `::: {.slide}` + `:::` starts a new slide there; without `title` it repeats the last
  slide's title with "(cont.)"
- `{.same-slide}` on a heading: no new slide; the heading is set in bold on the current one
- `{slide-title="…"}` replaces the heading's title on the slide only (for a session's `#`
  heading, it is the deck's title)

`::: notes` holds speaker notes: they never appear on the projected deck, and
`--to typst-notes` makes a **speaker script** (A4, one slide per page with its notes).
Slide decks show no bibliography unless you set `slides_bibliography: True` and end the
manuscript with a heading and `::: {#refs}` + `:::`.

### Lecture notes

How to make them in VS Code, and every mark you can write, is on one page:
[Making lecture notes](https://yoshida-kd.github.io/octavo/lectures/). This section is the summary.

One file gives **an A4 handout of all sessions** and **a slide deck per session**:

```bash
octavo build example-lecture --to typst --compile           # the handout
octavo build example-lecture --to typst-slides --compile    # one deck per session
octavo build example-lecture-03 --to typst-slides           # just one session
```

Without markers, **each `#` heading is a session**; inside it, `##` is a section and `###` a
slide (a session with only `##` headings makes each `##` a slide). Give a
heading an id to fix its deck's name (`# Second session {#second}` →
`example-lecture-second`); otherwise decks are numbered `-01`, `-02`, … in order.

**Marking sessions yourself.** When a session is not one `#` heading, put a marker where each
session begins; then the markers decide the sessions and headings are free:

```markdown
::: {.session #third title="Session 3: policy and government" subtitle="Public policy" date="2026-10-14"}
:::
```

`title`, `subtitle` and `date` go on that session's title slide (without `title`, its first
heading is used). Numbers in a deck are the handout's.

**What goes where.** Conditional blocks choose the output:

```markdown
::: {.handout-only}
Fill-in-the-blank space and detailed footnotes: handout only.
:::

::: {.slides-only}
Figures and short prompts: slides only.
:::
```

| Marker | Kept in |
|---|---|
| `.slides-only` | slides, speaker scripts |
| `.handout-only` | the handout |
| `.print-only` | anything printed (handout, paper, Word) |
| `.no-slides` | everything but slides |

**One PDF per session.** To hand out one session at a time:

```bash
octavo extract example-lecture                      # build/handouts/example-lecture-<id>.pdf, one per session
octavo extract example-lecture --session third      # one session (several, comma-separated, make one PDF)
octavo extract example-lecture --pages 12-19        # by printed page numbers
octavo extract example-lecture --session third --cover   # with the cover and contents in front
```

The whole handout is typeset once and each session's pages are cut from it, so page numbers,
contents and all numbers stay those of the whole. Sessions always begin on a new page.
`octavo build` does not make them, so in a terminal run `octavo extract` again after editing.
In VS Code, **Make the session handouts** under the lecture notes in the sidebar makes them,
and notes with session markers have them remade in the background on every save (turn that
off with the setting `octavo.updateHandoutsOnSave`).

**The handout's layout.** A cover page of its own, the contents on pages i, ii, …, the body
from page 1, and type after the Japanese LaTeX class jsarticle (11pt, a generous line pitch,
paragraphs indented by one character). The body is set in BIZ UDGothic. In the project or at
the top of the notes:

| Key | Default | What |
|---|---|---|
| `first_section` | `1` | `0` numbers a guidance session "0" (figures "0.1") |
| `handout_pagebreak` | `'session'` | a new page at each session; `'section'`: at each `#`; `None`: only at markers |
| `handout_font` | BIZ UDGothic + Inter | the body font |
| `handout_fontsize` | `'11pt'` | the type size |
| `date_format` | `'%B %-d, %Y'` (Japanese: `'%Y年%-m月%-d日'`) | how `date:` is shown; `date: today` is the day it was built |

---

## 8. Making it yours

### Templates

Everything Octavo typesets from — the handout and slide layouts, a paper's `main.typ`, the
manuscripts `octavo new` writes, the project `octavo init` writes — is a file you can replace.
Copy it and edit the copy; Octavo uses yours from then on:

```bash
octavo template list                              # which templates are in use, and from where
octavo template copy slides/typst-slides.typ      # into this project's templates/
octavo template copy paper/en/main.typ --user     # into ~/.config/octavo/templates/, for every project
octavo template diff slides/typst-slides.typ      # after updating Octavo: what changed in the original
```

| Template | Replace it to |
|---|---|
| `slides/typst-slides.typ`, `slides/typst-notes.typ` | change the look of decks and scripts |
| `handout/handout.typ` | change the lecture handout |
| `paper/<lang>/main.typ` | start every paper from your usual layout |
| `manuscripts/<lang>/*.md` | start manuscripts from your own skeleton |
| `typst/crossref.typ` | change how numbers and references look |
| `citations/japanese.lua` | change the form of Japanese works in the bibliography |

### Word styles

```bash
octavo reference-docx reference.docx
```

Open it in Word, change the styles (`Heading 1`, `Body Text`, `Theorem`, …), save it, and set
`'docx_reference': 'reference.docx'`.

### Fonts

| | Japanese | Latin |
|---|---|---|
| Papers | BIZ UDMincho | Libertinus Serif |
| Lecture handouts, slides | BIZ UDGothic | Inter |

`octavo setup` installs them. Without them Typst falls back to Noto CJK, or to the fonts the
system has (Hiragino on a Mac, Yu Gothic on Windows); `octavo doctor` says what is missing.
Change them with `handout_font`, `typst_slides_font`, or in a paper's `main.typ`.

---

## 9. Command reference

```
octavo build [documents...] [--to formats] [--compile] [--appendix] [--no-analysis] [--anonymous]
octavo watch [documents...] [--to formats]     rebuild on every save
octavo extract <lecture> [--session IDS] [--pages 12-19] [--cover]   one PDF per session
octavo documents                               the registered manuscripts
octavo config [--doc NAME] [set KEY VALUE | unset KEY]   show or change settings
octavo analysis [run [QMD]]                    is the analysis up to date / run it
octavo values [--unused] [--diff [ref]]        cross-check {{...}} against the analysis
octavo lint                                    results typed into the text, nested lists out of line
octavo check [--strict] [--anonymous]          everything before you submit
octavo bundle [name] [--anonymous] [--replication] [--with-raw-data]
octavo review returned.docx                    a coauthor's tracked changes
octavo release <document> <label>              tag, and the PDF to a GitHub Release
octavo data hash|status                        fingerprints of data/
octavo checkbib [--list] [--unused]            citation keys against the .bib
octavo csl get|list|which [ID]                 citation styles
octavo init <dir> [--lang ja|en] [--with PARTS | --all] [--example]
octavo new paper|slides|lecture|analysis|figure|table <name> [--example]
octavo template list|copy|diff [name] [--user]
octavo env                                     the project's .venv and renv
octavo setup [--with-tex] [--check]            install or update the tools
octavo doctor                                  what is installed
octavo selftest                                a sample typeset end to end
octavo reference-docx [out.docx]               a Word style file to edit
octavo outline [documents...]                  the heading structure
octavo targets                                 the output formats
```

Output formats (`--to`, comma-separated; `all` for every one):

| Format | Makes | Needs |
|---|---|---|
| `typst` | papers (with `main.typ`), handouts | Typst |
| `typst-slides` | slide decks | Typst |
| `typst-notes` | speaker scripts | Typst |
| `docx` | Word | pandoc only |
| `latex` | papers (with `main.tex`), handouts | TeX |
| `beamer` | slide decks | TeX |

---

## 10. VS Code

The [Octavo extension](https://marketplace.visualstudio.com/items?itemName=yoshida-kd.octavo)
puts all of this behind buttons:

- **Set up** installs the tools (§1); **Tools** in the sidebar also sets up the analysis
  environment, runs the analysis and the checks.
- **Preview**: the PDF beside the manuscript, rebuilt on every save; lecture notes get a third
  column with the deck (or the speaker script) for the session the cursor is in. Text can be
  selected, links followed, and ☰ lists the bookmarks.
- The sidebar lists manuscripts (with their settings), analyses and tools; open a paper to add
  an appendix, lecture notes with session markers to make per-session handouts (also remade on
  every save).
- Completion and checks for citations (`@`) and analysis values (`{{`).
- `.csv` files in `tables/` and `data/` open as editable tables.

It runs `octavo` wherever the folder is: locally, in WSL, or on a server over Remote-SSH.

---

## 11. What to check on your own machine

The test suite typesets every format with pandoc and Typst on Linux, macOS and Windows, and
runs the example analysis through Quarto and R. What it cannot see:

- **How citations look in your style** — run `octavo selftest` and read it.
- **Fonts** — look at your first PDF; `octavo doctor` lists missing fonts.
- **LaTeX** — no test compiles LaTeX output. Check your first LaTeX or Beamer PDF.
- **Your own R setup** — the example runs; your packages are yours to check.

If something looks wrong, please open an [issue](https://github.com/yoshida-kd/octavo/issues)
with the output of `octavo doctor`.
