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
| Ubuntu or another Debian-like Linux — a PC, or a server you reach over SSH | [Linux](#11-linux) |
| A Mac | [macOS](#12-macos) |
| Windows | [Windows](#13-windows) — WSL (recommended) or Windows itself |

On every system there are two ways to do it: **with VS Code** (install the extension and
press one button) or **from a terminal** (four commands). They install the same things.
LaTeX is not included — it is optional (see [LaTeX, if you want it](#16-latex-if-you-want-it)).

### 1.1 Linux

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
Posit Package Manager, from which a project's renv installs packages as ready-made binaries
instead of compiling them.

### 1.2 macOS

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

### 1.3 Windows

There are two ways. **WSL is recommended**: Octavo is developed and tested on Linux first,
and WSL gives you exactly that inside Windows. Use Windows itself only if you cannot use WSL.

#### 1.3.1 Windows with WSL (recommended)

1. Install WSL. Open PowerShell *as administrator* (right-click the Start button →
   *Terminal (Admin)*, or *Windows PowerShell (Admin)* on Windows 10) and run:

   ```powershell
   wsl --install
   ```

   Restart when it asks. Ubuntu then starts and asks you to choose a user name and password
   — remember the password, the setup asks for it.
2. Install [VS Code](https://code.visualstudio.com/) on Windows, then the **WSL** extension.
3. In VS Code, **WSL: Connect to WSL** (bottom-left corner). Open a folder *inside* Ubuntu
   (for example `/home/<user name>`).
4. Install the **Octavo** extension.
5. The Octavo extension offers **Set up**; press it and enter the Ubuntu password. From
   here on it is the [Linux](#11-linux) setup.

From a terminal instead: open *Ubuntu* from the Start menu and follow
[Linux → From a terminal](#11-linux).

<details class="fold">
<summary><h4 id="132-windows-itself-without-wsl">1.3.2 Windows itself (without WSL)</h4></summary>

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

</details>

Two habits keep a project working on every system: write paths with `/`
(`../assets/figures/trend.png`), and keep the upper and lower case of file names exactly as
the manuscript writes them — Windows does not tell `Trend.png` from `trend.png`, Linux does.

### 1.4 Check that it works

```bash
octavo doctor       # what is installed; anything missing comes with the command that installs it
octavo selftest     # typesets a small sample and prints the citations as they come out
```

`octavo doctor` marks each tool ok, missing, or a note (nice to have). `octavo selftest`
builds a sample with English and Japanese references, a table, a figure and
cross-references in a temporary folder and shows how the citations came out — run it once
per machine and read it.

### 1.5 Updating

```bash
uv tool upgrade octavo-kit    # the newest octavo
octavo setup                  # the tools it expects (safe to run again: what is there is skipped)
```

In VS Code, update the extension and run **Tools → Install or Update the Tools** in the
Octavo sidebar.

### 1.6 LaTeX, if you want it

Everything above makes PDFs through Typst; LaTeX is only needed for the `latex` and
`beamer` formats. On Linux, `octavo setup --with-tex` adds TeX Live (several GB). On a Mac,
install [MacTeX](https://www.tug.org/mactex/); on Windows, [MiKTeX](https://miktex.org/).
`octavo doctor` lists TeX separately and does not count it as missing.

### 1.7 The language Octavo speaks

Messages come out in English, or in Japanese when your system is set to Japanese.
`export OCTAVO_LANG=ja` (or `en`) chooses. This is only the language of the messages; the
language a project is *written* in is `lang` in its `octavo.config.py`
(`octavo init --lang ja|en`). The VS Code extension follows VS Code's language.

---

## 2. Your first project

> **In VS Code** you can do all of this without typing a command: the Octavo sidebar offers
> **New project** in a folder that is not a project yet (where, the language, the parts, the
> examples — an analysis also gets its environment set up), and its **+** adds manuscripts,
> analyses, figures and tables later. The commands below are what those buttons run; see
> [10. VS Code](#10-vs-code).

### 2.1 Try the example first

```bash
octavo init demo --all --example
cd demo
octavo env                    # the project's analysis environment (.venv and renv)
octavo build --compile        # runs the analysis, then typesets everything to PDF
```

This makes a project with an analysis of made-up data, a paper, a slide deck and lecture
notes that use it. The PDFs land in `build/`.

### 2.2 Start your own

`octavo init` makes the frame of a project; everything else is added with `octavo new`,
as many of each as you like:

```bash
octavo init study --with analysis,paper   # the frame, an analysis and a paper
cd study
octavo env                                # the project's analysis environment (.venv and renv)
```

```bash
octavo new analysis model           # analysis/model.qmd (the first also brings octavo.R and data/)
octavo new analysis model --engine python   # the same, written in Python (brings octavo_helper.py)
octavo new paper example-paper      # docs/example-paper/: example-paper.md and the layout main.typ
octavo new paper example-paper --appendix   # add appendix.md (to an existing paper too)
octavo new paper example-paper --tex        # add main.tex for LaTeX (to an existing paper too)
octavo new slides example-talk      # docs/example-talk/example-talk.md
octavo new lecture example-lecture  # docs/example-lecture/example-lecture.md
octavo new poster example-poster    # docs/example-poster/example-poster.md
octavo new figure dag               # figures/dag.typ, a figure drawn in Typst
octavo new table compare            # tables/compare.csv, a table you make by hand
```

`init --with` takes the same parts (`--with lecture`, `--with analysis,slides=talk`; `--all`
for every kind; `--engine python` makes the analysis one in Python), and `--example` fills the
parts with worked examples instead of bare headings. Add `--env` to `init` or `new analysis`
to set up the analysis environment in the same step.

**A document is `docs/<name>/<name>.md`.** Its appendix (`appendix.md`) and a paper's layout
(`main.typ`) sit in the same folder. A document is referred to by its name:
`octavo build example-paper`. `paper`, `slides` and `lecture` are different templates; each makes
the same kind of document. What a document makes is decided at the top of the manuscript
([3.6](#36-what-it-makes-and-settings-for-one-document)).

### 2.3 What is in a project

```
study/
  octavo.config.py   the project's settings
  literature.bib     the bibliography, exported from your reference manager
  AGENTS.md          the project's working rules for AI assistants (Claude Code, GitHub Copilot, Codex, Antigravity read it)
  CLAUDE.md          one line that points Claude Code at AGENTS.md
  README.md          a few lines for you to finish
  docs/<name>/       <name>.md (the manuscript), and appendix.md and main.typ (the journal layout) if any
  analysis/          the .qmd files and the helper (octavo.R, or octavo_helper.py for Python)
  data/raw/          the data as you got it (not in git; describe it in data/raw/README.md)
  data/derived/      data the analysis made (not in git)
  figures/           figures you make: drawn in Typst (<name>.typ), photos
  tables/            tables you make (<name>.csv)
  assets/            what the analysis and octavo build write — never edited by hand
    values/          the numbers behind {{…}}
    figures/         figures (.pdf and .png)
    tables/          tables (.typ, .tex, .md)
  build/             the output, a folder per output (pdf/, slides/, script/, word/, tex/, handouts/); everything here can be deleted and rebuilt
```

`octavo.config.py` already finds every manuscript and analysis in these folders, so adding
one never means editing it.

**A project made with an earlier version** keeps its manuscripts in `papers/<name>/paper.md`,
`slides/<name>.md` and `lectures/<name>.md`, and builds as before. To move them into `docs/`,
run `octavo migrate --docs` (`--dry-run` shows what it would do): it moves the manuscripts,
fixes the figure paths, writes `outputs` / `sessions` at the top and adds `docs/*/` to the
config. The document names stay the same. `octavo check` also says when there is something to move.

### 2.4 The analysis environment

Tools such as R and Quarto are installed once per machine. **The packages an analysis uses
belong to the project**:

```bash
octavo env    # .venv (uv) with requirements.txt, renv with knitr and rmarkdown
```

A project whose analyses are all in Python gets no renv. In VS Code you do not have to run it: **adding the first analysis** (or starting a project with one) sets the environment up right after, with the progress in a notification.

Run it again after adding a package to `requirements.txt`; after `install.packages()` in R,
run `renv::snapshot()`. Git keeps the records (`requirements.txt`, `renv.lock`), not the
installed packages, so a coauthor gets the same environment from the same command.

- `renv::status()` may say "out-of-sync" for packages that are recorded and installed but not
  used in the code (MASS or boot, which come with R, or ones you stopped using). That is
  harmless: nothing is missing.
- Outside a project, Quarto needs knitr and rmarkdown to run an R `.qmd`. `octavo setup` puts
  them (and `languageserver` for VS Code's R extension) in your own R library;
  `octavo setup --r-editor` does just that, for instance after removing an old R's packages.

### 2.5 Examples are marked as examples

What `--example` writes carries a mark — an `octavo:example` comment, `_placeholder` in the
values, a figure that is a box with an × — and `octavo check` counts what is left. Replace
the content and delete the mark with it. **Placeholder values are fatal in `octavo check`**:
before the analysis has ever run, every `{{…}}` still resolves, and the PDF would carry fake
numbers.

---

## 3. Writing manuscripts

| What | How you write it |
|---|---|
| Heading | `# Analysis {#sec-analysis}` — `#` is the top section (starting at `##` also works); no number; the label makes it referable |
| Abstract | a `# Abstract` section |
| Citation | `@key`, `[@key; @key2]`, possessive `\poscite{key}` ("Smith and Taylor's (2003)") |
| A number from the analysis | `{{n_obs}}`, `{{coef_x:.2f}}` (§4) |
| Figure | `![Trend](../../assets/figures/trend.png){#fig-trend}` |
| Table | a Markdown table with `: Caption {#tbl-desc}` right below it, or the caption line alone for a table from the analysis or from `tables/` |
| Equation | `$$ … $$ {#eq-model}` |
| Reference | `@fig-trend` → "Figure 2.1" |
| Title, author, date | the YAML front matter at the top |

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
  and `_` — Quarto's convention. Japanese may follow directly (`@fig-trendに示す`).
- `@fig-trend` reads "Figure 2.1" ("図2.1" in a Japanese document), `@eq-model`
  "Equation (2.1)", `@sec-analysis` "Section 2"; `[-@eq-model]` is the number alone.
- Numbering is by section (Figure 3.2 is the second figure of Section 3);
  `crossref_numbering: 'document'` numbers straight through.
- Numbered: headings (except `{.unnumbered}`), figures and tables with a caption, and
  equations with a label.
- A heading `# Title {.appendix}` starts an appendix within the file (A, B, …).
- `octavo check` stops on a label that does not exist or is used twice.

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

- Kinds: `case`, `question` (one numbering: Case 1.1, Question 1.2), `aside`, `nb`,
  `memo` (unnumbered), and `theorem`, `lemma`, `proposition`, `corollary`, `definition`, `example`
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
  For an operator write `\newcommand{\Cov}{\operatorname{Cov}}`.
- Keep a value with a thousands separator outside the math (`$N$ = {{n_obs}}`); inside,
  the comma is set as punctuation.

### 3.4 Figures

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

**A source or note under a figure or table** goes in `::: {.figure-note}` right after it
(after a table's caption line). It is ordinary Markdown — links and footnotes work — set in
small type with the figure, kept on the same page, and left out of the figure's title. On a
slide the figure shrinks to leave room for it. A footnote can go in the title too:

```markdown
![Officials by level of government[^src]](../assets/figures/staff.png){#fig-staff}

::: {.figure-note}
Source: National Personnel Authority, *Annual Report 2025*.[^checked]
:::

[^src]: Full-time staff only.
[^checked]: Retrieved 1 October 2026.
```

**Photos and other images you have** (a photo you took, a screenshot) go in `figures/`, next to
the Typst figure sources, and are placed straight from there; `.jpg` and `.png` work in every
output. Octavo does not shrink them, so resize a large photo first (about 2,000 pixels on the
long side is plenty) or the PDF gets heavy. Where an image came from and whether you may use
it is worth a line in `figures/README.md`, as `data/raw/README.md` does for data.

```markdown
![The council chamber](../figures/chamber.jpg){#fig-chamber width=70%}
```

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

### 3.5 Tables

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

### 3.6 What it makes, and settings for one document

**What a document makes is `outputs:` at the top of the manuscript.** Without it, `pdf`.

```markdown
---
title: Title of the Paper
outputs: [pdf, word]
---
```

| Output | What it makes |
|---|---|
| `pdf` | a PDF. Its layout is the `main.typ` beside the manuscript if there is one (a paper), otherwise Octavo's built-in one (A4, with a cover and contents) |
| `word` | Word |
| `tex` | LaTeX (needs TeX; uses the `main.tex` beside the manuscript if there is one) |
| `slides` | slides |
| `script` | the speaker script (each page of the deck with its `::: notes`) |
| `poster` | a poster ([7.3](#73-posters)) |
| `beamer` | LaTeX slides (needs TeX) |

**A manuscript made of several class sessions says `sessions: true`.** One `#` heading (or one
`::: {.session}` marker) is one session, and the slides and the script come out as one file per
session ([7.2](#72-lecture-notes)). A manuscript with markers is made of sessions without saying so.

The title goes in the front matter (`title:`). Don't write a `# Title` heading — a `#` heading is a section.

**Other settings** that change per journal or talk can also go at the top of the manuscript,
and then apply to it alone:

```markdown
---
title: Title of the Paper
csl: apa
word_limit: 8000
---
```

| Key | For | What |
|---|---|---|
| `outputs`, `sessions` | all | what it makes, made of sessions (above) |
| `csl` | all | citation style |
| `japanese_citation_form`, `citations_by_language` | all | Japanese works in the bibliography (§5) |
| `word_limit`, `char_limit`, `abstract_word_limit`, `abstract_char_limit` | all | submission limits (`octavo check`) |
| `slides_*` | slides | the look of the decks (§7) |
| `slides_select`, `poster_select` | slides, posters | `marked`: only what is marked (`.on-slides`, `.on-poster`) goes on them (§7) |
| `date_format` | all | how the date is shown |
| `toc` | PDF in the built-in layout | table of contents (on by default when `sessions` is) |
| `first_section`, `pagebreak`, `font`, `fontsize` | PDF in the built-in layout | first section number, page breaks, typeface (§7) |

`octavo config --doc <name>` lists them and `set` / `unset` changes one line; in VS Code,
**Settings for this document** under each manuscript in the sidebar.

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
  height for a figure). Outputs other than slides ignore it.

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

### 4.1 Handing over numbers, figures and tables

A new `.qmd` already loads its helper: `octavo.R` for R, `octavo_helper.py` for Python (see below). Register what the paper shows:

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

### 4.2 How numbers look

| Value | Example | Shown as |
|---|---|---|
| Whole number | `nrow(d)` | `1,523` |
| Decimal | `coef(m)[["x"]]` | `0.342` (3 places by default) |
| Text | `ov_pval(p)` | as it is |

`{{coef_x:.2f}}` in the manuscript, or `ov_value(..., fmt = ".2f")`, chooses the format. A
name with no value stays as `{{name}}` in the output and is reported.

### 4.3 When the analysis runs

`octavo build` runs a `.qmd` when it, or a file it depends on, changed since the last run.

```bash
octavo analysis              # which are out of date
octavo analysis run          # run the out-of-date ones
octavo build --no-analysis   # build without running anything
octavo check values --diff   # which numbers in the text changed at the last run
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

- A `.qmd` can say this itself, at the top under `octavo:`, so the config's
  `analysis/*.qmd` can stay as it is: `manual: true` (only `octavo analysis run` runs it) and
  `deps` (more files to watch). An entry for that file in the config wins over it.
- **Fetching raw data from the web** (an API, a download, an R package that fetches) goes in
  its own `.qmd`, run by hand: `analysis/00-fetch-<source>.qmd` with `manual: true`. Have it
  stop rather than overwrite a file already in `data/raw/`, and write where it came from and
  when into `data/raw/README.md` — that file is the only record once `data/raw/` is ignored.

```yaml
---
title: "Fetch the raw data"
octavo:
  manual: true
---
```

- In VS Code the sidebar's **Analysis** section shows each `.qmd` and runs it with one
  button. The preview never runs the analysis; it says when something is out of date.

### 4.4 Python

Add `--engine python` (or pick **Analysis in Python** in VS Code) and the `.qmd` is written in
Python. It loads `analysis/octavo_helper.py`, which has the same functions under the same names
and writes the same files, so the manuscript is written exactly as for R:

```python
ov_value("n_obs", len(d))              # {{n_obs}}
ov_value("coef_x", model.params["x"])
ov_figure(fig, "trend")                # a matplotlib Figure (or a plotnine ggplot, or a function that draws)
ov_table(tab, "summary")               # a pandas DataFrame (or a dict, or a list of lists)
```

- An `int` (also a NumPy integer) is shown as `1,523`, a `float` as `0.342`, as in R.
- `ov_palette()`, `ov_tint()` and `ov_pval()` are there too. The helper needs only the standard
  library; matplotlib and pandas are used only when you hand it a figure or a DataFrame.
- `requirements.txt` gets what Quarto needs to run Python (`ipykernel`, `nbformat`, `nbclient`,
  `pyyaml`), and `octavo env` installs it into `.venv`, which `octavo analysis run` uses by
  itself. R and Python `.qmd` files can live in one project.

### 4.5 Other languages

Octavo only reads files, so a Julia or other `.qmd` works if it writes
`{"name": value}` into `assets/values/<anything>.json`, figures as `.pdf` and `.png` into
`assets/figures/`, and tables into `assets/tables/`.

---

## 5. Citations

Export your library from your reference manager (Zotero or any other) as BibTeX or BibLaTeX
to `literature.bib`. With Zotero, Better BibTeX's "Keep updated" export keeps it current and
the keys stable. **Octavo never edits the `.bib`.**

```bash
octavo check cites        # keys cited but missing from the .bib, and problems in the .bib
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

The bibliography goes at the end. A `# References` heading as a paper's last section only
marks its place (whatever is under it is replaced); a heading of that name with a reading list
under it inside lecture notes is kept as written. To put the bibliography somewhere else, write
`::: {#refs}` and `:::` there.

`\poscite{key}` writes a possessive citation ("Smith and Taylor's (2003)", 「山田・田中(2020)」);
the joining of several authors is an approximation of the style's rules, so read it once.

---

## 6. Papers: from draft to submission

A paper is `docs/<name>/<name>.md` plus `main.typ`, **the journal layout you keep by hand**
(title block, fonts, margins). `octavo build` writes the body into `build/pdf/<name>/`
and `main.typ` typesets it; `--compile` makes the PDF (`build/pdf/<name>/main.pdf`, with a copy
at `build/pdf/<name>.pdf`).

```bash
octavo build example-paper --compile            # PDF
octavo build example-paper --to word            # Word
octavo build example-paper --compile --appendix # with appendix.md
```

For an appendix, `octavo new paper <name> --appendix`, then uncomment
`#show: octavo-appendix` and `#include "appendix.typ"` in `main.typ`. Its sections are A, B, …
and labels work across both files.

### 6.1 Before you submit

```bash
octavo check           # everything in one pass; fatal problems give a non-zero exit
octavo check lint      # results typed into the text, and nested lists out of line
```

`octavo check` looks at: missing figures and tables, unresolved `{{…}}`, placeholder values,
out-of-date analysis, citation keys and the `.bib`, labels, template leftovers, `:::` blocks
that will not be read as written, submission limits, and the data fingerprints. A number that
is not a result (a grading split, a year) is kept out of the hand-typed check by
`[40%]{.no-lint}` in the text, `::: {.no-lint}` … `:::` around a passage, or the text around
it in `lint_accepted` (`'midterm 40%'`). Limits are set in the config or the manuscript
(`word_limit: 8000`, `char_limit` for Japanese journals).

### 6.2 Blind review

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

### 6.3 Packaging for the journal

```bash
octavo bundle example-paper    # submission-example-paper.zip: the files, flattened into one folder
```

### 6.4 After you send it

- **Coauthors' Word edits**: `octavo review returned.docx` lists their tracked changes and
  comments. Apply them to the manuscript yourself — the Word file has the numbers typed in, so it
  is never converted back.
- **Keep the version you sent**: `octavo release example-paper v1-submitted` tags the commit
  and puts the PDF on a GitHub Release (needs the `gh` command).
- **Revisions**: `octavo check values --diff example-paper-v1-submitted` shows which numbers moved
  since that version.
- **Data**: `octavo data hash` records a fingerprint of `data/`; `octavo data status` says
  whether anything changed since.
- **Replication package**: `octavo bundle --replication` collects the analysis, the values,
  the figures and tables, the config and the fingerprints (raw data only with
  `--with-raw-data`).

---

## 7. Slides, lecture notes and posters

### 7.1 Slides

A document that makes only slides (`outputs: [slides]`): with `#` and `##` headings, `#` is a section and `##` a slide; with one
level, each heading is a slide. The title slide comes from the front matter. Figures fit the
remaining space on the slide.

```bash
octavo build example-talk --compile
```

| Key | Default | What |
|---|---|---|
| `slides_aspect` | `'16-9'` | or `'4-3'` |
| `slides_accent` | `'#0e2f92'` | the accent colour; `None` for plain black |
| `slides_numbering` | `None` | heading numbers (`'1.'`, `'1.1'`) |
| `slides_section_slides` | `False` | a divider slide for each `#` section |
| `slides_running_header` | `True` | the current section in the top-left corner |
| `slides_font` | BIZ UDGothic + Inter | the font |

The older names (`typst_slides_aspect` and so on) are still read.

**Where slides break, and their titles**, can be set in the manuscript; the handout and
other outputs are not affected:

```markdown
## A long heading for the handout {slide-title="Short title"}

\newslide

### A heading that stays on the same slide {.same-slide}

\newslide{Another title}
```

- `\newslide` starts a new slide there, titled like the last one with "(cont.)";
  `\newslide{Title}` gives that title and `\newslide{}` a slide with no title
  ([3.7](#37-page-breaks-and-slide-breaks)). The older `::: {.slide title="…"}` + `:::` means the same
- `{.same-slide}` on a heading: no new slide; the heading is set in bold on the current one
- `{slide-title="…"}` replaces the heading's title on the slide only (for a session's `#`
  heading, it is the deck's title)

- `{.no-title}` on a slide's heading: a new slide with no title, so a figure gets the room
  (the section name stays in the top-left corner; the handout keeps the heading)

`::: notes` holds speaker notes: they never appear on the projected deck, and
`--to script` makes a **speaker script**: each page of the typeset deck, shrunk, with the
notes written on it underneath (A4, two slides a page). It typesets the deck first, so the
pictures are exactly what is projected.
Slide decks show no bibliography unless you set `slides_bibliography: True` and end the
manuscript with a heading and `::: {#refs}` + `:::`.

### 7.2 Lecture notes

How to make them in VS Code, and every mark you can write, is on one page:
[Making lecture notes](https://yoshida-kd.github.io/octavo/lectures/). This section is the summary.

One file gives **an A4 handout of all sessions** and **a slide deck per session**:

```bash
octavo build example-lecture --to pdf --compile      # the handout
octavo build example-lecture --to slides --compile   # one deck per session
octavo build example-lecture-03 --to slides          # just one session
```

Without markers, **each `#` heading is a session**; inside it, `##` is a section and `###` a
slide (a session with only `##` headings makes each `##` a slide). Give a
heading an id to fix its deck's name (`# Second session {#second}` →
`octavo build example-lecture-second`, `example-lecture-slides-second.pdf`); otherwise decks
are numbered `-01`, `-02`, … in order.

**Marking sessions yourself.** When a session is not one `#` heading, put a marker where each
session begins; then the markers decide the sessions and headings are free:

```markdown
\session{Session 3: policy and government} {#third subtitle="Public policy" date="2026-10-14"}
```

The braces of `\session{…}` hold the session's title, and `{…}` can carry `#id` (the session's
name), `subtitle`, `date`, `author` and `institute` (all optional; `\session{}` for no title).
Title, subtitle and date go on that session's title slide (without a title, its first heading is
used). The older `::: {.session #third title="…"}` + `:::` means the same. The numbers of figures, tables, equations and blocks in a deck are the handout's (even when some figures are in the handout only or were not picked for the slides). Which level is a slide is decided from
the whole of the notes (normally `###`), so adding markers does not change it.

**What goes where.** Conditional blocks choose the output:

```markdown
::: {.pdf-only}
Fill-in-the-blank space and detailed footnotes: handout only.
:::

::: {.slides-only}
Figures and short prompts: slides only.
:::
```

| Marker | Kept in |
|---|---|
| `.slides-only` | slides, speaker scripts |
| `.pdf-only` | the PDF (handout, paper) |
| `.word-only` | Word |
| `.print-only` | anything printed (PDF, Word, LaTeX) |
| `.no-slides` | everything but slides and speaker scripts |

The older `.handout-only` still works (kept in the built-in layout's PDF, Word and LaTeX).

**Only part of the notes on the slides.** With `slides_select: marked` at the top, the slides get
only what is marked `.on-slides` (a `::: {.on-slides}` block, a section whose heading has
`{.on-slides}`, `[…]{.on-slides}` in a line) and the headings above it; the rest goes into the
handout only. A reference to something not picked is written as its number in the handout, and
a session with nothing marked gets no deck.

**One PDF per session.** To hand out one session at a time:

```bash
octavo build example-lecture --sessions             # build/handouts/example-lecture-<id>.pdf, one per session
octavo extract example-lecture --session third      # one session (several, comma-separated, make one PDF)
octavo extract example-lecture --pages 12-19        # by printed page numbers
octavo extract example-lecture --session third --cover   # with the cover and contents in front
```

The whole handout is typeset once and each session's pages are cut from it, so page numbers,
contents and all numbers stay those of the whole. Sessions always begin on a new page.
In a terminal, `octavo build <name> --sessions` makes them along with the build (without it they
are not remade).
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
| `pagebreak` | `'session'` | a new page at each session; `'section'`: at each `#`; `None`: only at markers |
| `font` | BIZ UDGothic + Inter | the body font |
| `fontsize` | `'11pt'` | the type size |
| `toc` | `true` | the table of contents (`false` for a document without sessions) |
| `date_format` | `'%B %-d, %Y'` (Japanese: `'%Y年%-m月%-d日'`) | how `date:` is shown; `date: today` is the day it was built |

### 7.3 Posters

For a poster session. A manuscript with `outputs: [poster]` at the top (`octavo new poster <name>`
writes one) becomes one PDF, `build/poster/<name>.pdf`. By default it is **A0 portrait**, and
**each top-level heading (`#`) is one cell**, filling a 2×3 grid from the top left.

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
| `{cell="3,2"}` | put it in column 3, row 2 (counting from 1; the others fill the free cells in order) |
| `poster_size` | `a0` (default), `a1`, `a2`, `b0`, `b1` (the Japanese B series), or a size like `1189x841mm` |
| `poster_orientation` | `portrait` (default) or `landscape` |
| `poster_grid` / `poster_rows` | the grid (columns x rows, `2x3` by default) and the rows' height ratios (equal by default) |
| `logo` / `qr` / `qr_label` | logos on the left of the title band (any number), a QR code on the right (made from the URL) and the text under it |

To make a poster from a paper's manuscript, write `outputs: [pdf, poster]` and
`poster_select: marked`, and mark what goes on the poster with `.on-poster` (written like
`.on-slides` for slides).

Type size and margins scale with the paper. Figures fit the room left in their cell. The works
you cite go in the last cell (`# References`). **Content that does not fit in its cell is
reported as an overflow when you build** (and marked in red at the cell's corner in the PDF):
cut it or make the cell bigger. The colour is `slides_accent` and the typeface `poster_font`;
`octavo template copy poster/typst-poster.typ` changes the look.

---

## 8. Making it yours

### 8.1 Templates

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
| `poster/typst-poster.typ` | changes the look of posters |
| `handout/handout.typ` | change the lecture handout |
| `paper/<lang>/main.typ` | start every paper from your usual layout |
| `manuscripts/<lang>/*.md` | start manuscripts from your own skeleton |
| `typst/crossref.typ` | change how numbers and references look |
| `citations/japanese.lua` | change the form of Japanese works in the bibliography |

### 8.2 Word styles

```bash
octavo template copy word          # templates/word/reference.docx (--user: for all your projects)
```

Open it in Word, change the styles (`Heading 1`, `Body Text`, `Theorem`, …) and save it: Word
output uses it from then on. A `.docx` named in `docx_reference` in the config comes first (the
older `octavo reference-docx` still works).

### 8.3 Fonts

| | Japanese | Latin |
|---|---|---|
| Papers | BIZ UDMincho | Libertinus Serif |
| Lecture handouts, slides | BIZ UDGothic | Inter |

`octavo setup` installs them. Without them Typst falls back to Noto CJK, or to the fonts the
system has (Hiragino on a Mac, Yu Gothic on Windows); `octavo doctor` says what is missing.
Change them with `font`, `slides_font`, or in a paper's `main.typ`.

---

## 9. Command reference

```
octavo build [documents...] [--to outputs] [--compile] [--appendix] [--sessions] [--no-analysis] [--anonymous]
octavo watch [documents...] [--to outputs]                           rebuild on every save
octavo extract <lecture> [--session IDS] [--pages 12-19] [--cover]   some sessions, or pages, as one PDF
octavo documents                                                     the registered manuscripts
octavo config [--doc NAME] [set KEY VALUE | unset KEY]               show or change settings
octavo analysis [run [QMD]]                                          is the analysis up to date / run it
octavo check [--strict] [--anonymous]                                everything before you submit
octavo check values [--unused] [--diff [ref]]                        cross-check {{...}} against the analysis
octavo check cites [--list] [--unused]                               citation keys against the .bib
octavo check lint                                                    results typed into the text, nested lists out of line
octavo bundle [name] [--anonymous] [--replication] [--with-raw-data]
octavo review returned.docx                                          a coauthor's tracked changes
octavo release <document> <label>                                    tag, and the PDF to a GitHub Release
octavo data hash|status                                              fingerprints of data/
octavo csl get|list|which [ID]                                       citation styles
octavo init <dir> [--lang ja|en] [--with PARTS | --all] [--engine r|python] [--example] [--env]
octavo new paper|slides|lecture|analysis|figure|table <name> [--example] [--engine r|python] [--env]
octavo template list|copy|diff [name] [--user]                       templates (copy word: a Word style file to edit)
octavo env                                                           the project's R and Python packages (.venv, renv)
octavo setup [--with-tex] [--check] [--r-editor]                     install or update the tools
octavo doctor                                                        what is installed
octavo selftest                                                      a sample typeset end to end
octavo outline [documents...]                                        the heading structure
octavo targets                                                       the outputs
octavo migrate [--docs] [--dry-run]                                  bring an older project up to date (--docs: manuscripts into docs/)
```

Outputs (in `outputs:` at the top of a manuscript and after `--to`, comma-separated; `--to all` for every one):

| Output | Makes | Needs |
|---|---|---|
| `pdf` | a PDF (the paper layout with `main.typ`, otherwise the built-in one) | Typst |
| `slides` | slide decks | Typst |
| `script` | speaker scripts | Typst |
| `poster` | posters | Typst |
| `word` | Word | pandoc only |
| `tex` | LaTeX (the paper layout with `main.tex`) | TeX |
| `beamer` | slide decks | TeX |

The older format names (`typst`, `typst-slides`, `typst-notes`, `docx`, `latex`) are read the same way.

---

## 10. VS Code

The [Octavo extension](https://marketplace.visualstudio.com/items?itemName=yoshida-kd.octavo)
puts all of this behind buttons:

- **Set up** installs the tools (§1); **Tools** in the sidebar also sets up the analysis
  environment, runs the analysis and the checks.
- **Preview**: the PDF beside the manuscript, rebuilt on every save; lecture notes get a third
  column with the deck (or the speaker script) for the session the cursor is in. Text can be
  selected, links followed, and ☰ lists the bookmarks.
- **New project** is one screen: where, the name, the language, what to start with (an analysis in R or Python, a paper, slides, lecture notes) and whether to fill them with examples. With an analysis chosen, the environment is set up right after. In a folder that is not a project yet, the sidebar offers it first.
- The extension also installs **Quarto**, **R** and **Python** extensions with it (an extension pack; you can uninstall any of them). The R extension uses the R package `languageserver` for completion and the like, and in a renv project it asks to install it, project after project. Octavo offers once to install it in your own R library and add that library to the R extension's `r.libPaths` (in a terminal: `octavo setup --r-editor`; `octavo setup` installs it too).
- The sidebar lists manuscripts (with their settings), analyses and tools; open a paper to add
  an appendix, lecture notes with session markers to make per-session handouts (also remade on
  every save).
- The preview scrolls to where the cursor is in the manuscript (it can still be scrolled on its own; the ⇅ button in its toolbar, or the setting `octavo.previewFollowCursor`, turns that off).
- Opening a `.qmd` in an Octavo project shows the HTML it last rendered (`<name>.html` beside it) in the next column, and reloads it when the analysis runs again. Nothing is rendered by opening or saving it. While the Quarto extension's own **Preview** is running, this view closes and stays closed (`octavo.qmdPreview` turns it off altogether).
- In a project with an R analysis and a `.venv`, the extension stops the Python extension from typing the `.venv` activate command into new terminals (in an R terminal it is an error: `unexpected symbol`). It says so once, with **Undo**; it leaves the setting alone if you have set it yourself.
- Completion and checks for citations (`@`) and analysis values (`{{`).
- A `.csv` file in `tables/` or `data/` gets an **Edit as a Table** button in its title bar that opens it as a grid.

It runs `octavo` wherever the folder is: locally, in WSL, or on a server over Remote-SSH.

---

## 11. What to check on your own machine

The test suite typesets every format with pandoc and Typst on Linux, macOS and Windows, and
runs the example analysis through Quarto, in R and in Python. What it cannot see:

- **How citations look in your style** — run `octavo selftest` and read it.
- **Fonts** — look at your first PDF; `octavo doctor` lists missing fonts.
- **LaTeX** — no test compiles LaTeX output. Check your first LaTeX or Beamer PDF.
- **Your own R setup** — the example runs; your packages are yours to check.

If something looks wrong, please open an [issue](https://github.com/yoshida-kd/octavo/issues)
with the output of `octavo doctor`.
