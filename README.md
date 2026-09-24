# Octavo

**The quantitative social science starter pack**

[![tests](https://github.com/yoshida-kd/octavo/actions/workflows/tests.yml/badge.svg)](https://github.com/yoshida-kd/octavo/actions/workflows/tests.yml)

[日本語版 README はこちら / Japanese README](README.ja.md)

A command-line tool that converts a **single Markdown source file** into
**Typst (papers, handouts, slides), Word (.docx), LaTeX, and Beamer**, with unified
citations from one `.bib` file and a CSL style across all of them. Works equally well for
English and Japanese documents.

It was built for an academic workflow where the same underlying content
often needs to become several different documents: a journal-formatted
paper, an A4 handout for a class, and slides for a talk — all sharing the
same section text, figures, tables, and bibliography, without hand-copying
between them.

```bash
octavo init 2026-research && cd 2026-research
octavo new paper example-paper        # add a paper (any number of them)
octavo new lecture example-lecture    # add lecture notes
octavo build                          # build everything
octavo build example-paper --to docx  # just Word
octavo build example-lecture --to typst-slides --compile  # one PDF deck per session
```

| Output   | Toolchain     | Produces |
|----------|---------------|----------|
| `typst`  | Typst         | `body.typ` (paper, dropped into a hand-maintained `main.typ`) or a fully standalone `.typ` |
| `typst-slides` | Typst   | a standalone slide-deck `.typ` (plain Typst, no packages) |
| `typst-notes` | Typst    | the speaker script for that deck — A4, one page per slide, `::: notes` underneath |
| `docx`   | pandoc only   | `.docx` |
| `latex`  | LuaLaTeX (optional) | `body.tex` (paper, dropped into a hand-maintained `main.tex`) or a fully standalone `.tex` |
| `beamer` | LuaLaTeX (optional) | a standalone slide-deck `.tex` |

The defaults are `typst`, `typst-slides` and `docx`, which need no TeX. Add TeX Live only
if you use LaTeX or Beamer (`bash setup.sh --with-tex`).

Citations are **unified through CSL**: change one `csl` setting in
`octavo.config.py` and every format — LaTeX, Typst, Word — switches
bibliography style together. There is no per-format citation logic to keep
in sync.

---

## 1. Install

Octavo runs on Linux — a native Ubuntu/Debian box, an Ubuntu server, or
Ubuntu-on-WSL2 on Windows — and on macOS. `setup.sh` installs with apt on Linux
and with [Homebrew](https://brew.sh) on macOS (install Homebrew first).

```bash
git clone https://github.com/yoshida-kd/octavo.git ~/octavo
bash ~/octavo/setup.sh      # installs pandoc / Typst / quarto / CJK fonts
octavo doctor                     # reports anything still missing
octavo selftest                   # one real end-to-end citation check
```

`octavo selftest` builds a small sample document in a temp directory
(English and Japanese references, an organization-as-author entry, a
table, a figure, cross-references, `\poscite`) and **prints the actual
rendered citations and bibliography**. Run it once per machine so you can
eyeball whether the CSL formatting looks right before trusting real output.

### The language it speaks

Messages, `--help` and `octavo doctor` come out in **English by default, and in
Japanese when your locale is Japanese** (`LC_ALL` / `LC_MESSAGES` / `LANG`).
`OCTAVO_LANG` overrides that either way:

```bash
export OCTAVO_LANG=ja     # Japanese, whatever the locale says
export OCTAVO_LANG=en     # English, likewise
octavo doctor             # the "display language" row shows what is in effect
```

This is the **interface** language only. What language a project is *written*
in is a separate setting — `lang` in `octavo.config.py`, which `octavo init
--lang ja|en` writes — and it decides the manuscript templates, the generated
CLAUDE.md and README, and the citation locale. A Japanese interface with an
English paper is a perfectly ordinary combination.

### Installing with pip instead

`setup.sh` + the symlink it makes is the recommended route, because it also
installs the external tools. If you only want the converter and will install
pandoc / Typst / quarto yourself, `octavo` is a normal Python package:

```bash
pipx install octavo-kit     # or `pip install octavo-kit` inside a virtualenv
octavo doctor
```

(A plain `pip install` outside a virtualenv is refused on recent Ubuntu/Debian —
PEP 668 — which is why `pipx` is the suggestion: it gives the command its own
environment.)

It has **no Python dependencies** (standard library only) and carries its own
templates, so `octavo init` / `octavo new` work the same way. What you don't
get is `setup.sh` itself — `octavo doctor` then tells you to clone the repo for
it. On PyPI it is `octavo-kit` (PyPI does not allow the name `octavo`); the command
and the Python module are `octavo`.

`setup.sh` is idempotent — safe to re-run. It does not install TeX Live by
default; add it with `bash setup.sh --with-tex` (several GB) if you also use
LaTeX or Beamer. `octavo doctor` reports a missing TeX as a warning, not as
something missing. quarto (which renders the `.qmd` analysis) is installed by
default; skip it with `--no-quarto`. R and Python themselves are not installed —
which one a project uses is the project's business.

Version requirements:

| | Minimum | Recommended | Why |
|---|---|---|---|
| pandoc | 2.11 | 3.11 | 2.11 adds `--citeproc` (CSL citations); 3.1 adds Typst export; verified on 3.11 |
| Python | 3.9 | — | standard library only — no external packages required |
| LuaLaTeX (optional) | — | TeX Live 2021+ | needs `texlive-lang-japanese` for Japanese documents |
| Typst | — | 0.15 | Typst slides need 0.12+. CJK fonts aren't bundled (`setup.sh` installs them) |

On macOS, `setup.sh` runs `brew install pandoc typst`, `brew install --cask quarto`
and the font casks (`font-biz-udmincho` and friends), and `--with-tex` adds MacTeX
(`mactex-no-gui`, which has Japanese LuaLaTeX and Beamer included). `octavo doctor`
gives its hints as `brew` commands there. The CI `macos` job goes from a Homebrew
install to typeset PDFs on every push.

If you're on Windows, running Octavo inside WSL2 (Ubuntu) works well;
just make sure your source files live on the Linux filesystem (or a
Windows-side folder mounted under `/mnt/...`) so paths resolve normally.

### The analysis environment is per project (.venv and renv)

pandoc, Typst, quarto and Octavo live once per machine (`setup.sh` above).
**The packages an analysis uses belong to the project.** `octavo init` lays the
Python groundwork — a `requirements.txt`, plus `.venv/` and `renv/library/` in
the project's `.gitignore`.

```bash
cd 2026-research
python3 -m venv .venv && source .venv/bin/activate   # Python
pip install -r requirements.txt
Rscript -e 'renv::init()'                            # R
```

renv does not come with R, so install it once per machine (`octavo doctor`
shows whether it is there, under "Analysis"; the personal library folder has to
exist first or `install.packages()` has nowhere to write):

```bash
mkdir -p "$(Rscript -e 'cat(Sys.getenv("R_LIBS_USER"))')"
Rscript -e 'install.packages("renv", repos = "https://cloud.r-project.org")'
```

Git holds **only the records** (`requirements.txt` / `renv.lock`), never the
environment itself. Add a package to `requirements.txt` after `pip install`, and
run `renv::snapshot()` after `install.packages()`. The generated project's
`README.md` / `CLAUDE.md` say the same thing.

### Typefaces

Every Typst output uses the same defaults (they live in one place,
`octavo/backends/typst.py::FONTS`):

| | Japanese text | Latin letters and digits | Fallback |
|---|---|---|---|
| Papers, A4 handouts | BIZ UDMincho | Libertinus Serif | Noto Serif CJK JP → Hiragino Mincho ProN |
| Slides, speaker scripts | BIZ UDGothic | Inter | Noto Sans CJK JP → Hiragino Kaku Gothic ProN |

The BIZ UD faces are the **fixed-width** ones (not the proportional BIZ UDP
variants). In a Japanese document the Latin font only takes Latin letters and
digits (`covers: "latin-in-cjk"`), so Japanese punctuation stays with the
Japanese font; in an English document the Latin font simply comes first.
`setup.sh` installs all of them (`fonts-morisawa-bizud-gothic`,
`fonts-morisawa-bizud-mincho`, `fonts-inter`, `fonts-noto-cjk`, or the matching
Homebrew casks on a Mac); on a machine without BIZ UD or Inter, Typst falls back
to Noto, and on a Mac with nothing added, to the Hiragino fonts macOS ships —
`octavo doctor` says which are missing. Override with `typst_mainfont`
(handouts) and `typst_slides_font` (slides and scripts), or edit a paper's
`main.typ`. Note that Google Fonts' "Noto Serif JP" is a different family name
from `Noto Serif CJK JP` and won't be found.

---

## 2. Documents and profiles

Octavo tracks "**which source file, for what purpose, into which
format(s)**" in the `documents` section of `octavo.config.py`.

The config `octavo init` writes registers each kind of manuscript **by folder,
with a glob**, so adding manuscripts with `octavo new` never requires editing it.

```python
'documents': {
    'papers': {'src': 'papers/*/paper.md', 'appendix': 'papers/*/appendix.md',
               'profile': 'paper', 'targets': ['typst']},
    'slides': {'src': 'slides/*.md', 'profile': 'slides',
               'targets': ['typst-slides']},
    'lectures': {'src': 'lectures/*.md', 'profile': 'handout',
                 'targets': ['typst', 'typst-slides'], 'split_slides': True},
},
# papers/example-paper/paper.md  -> document example-paper (appendix: appendix.md next to it)
# slides/example-talk.md           -> document example-talk
# lectures/example-lecture.md   -> document example-lecture (decks example-lecture-01, -02, ...)
```

- A glob in `src` makes **each matching file its own document**, named after
  **what the first `*` matched** (the folder for papers, the file name for slides).
  A `*` in the key is filled in with it (`'lecture-*': {'src': 'lectures/*.md'}`
  gives `lecture-lecture01`)
- `appendix` may use `*` too; it is filled with the same match and attached only
  if the file exists
- Two documents with the same name stop the run (even of different kinds —
  `octavo build <name>` couldn't tell them apart)
- A glob that matches nothing just means "none of this kind yet", so it stays quiet
- Single entries work too: `'week3': {'src': 'lecture03.md', 'profile': 'handout'}`

If you don't write `documents` at all, it's inferred from whichever of
these files exist:

| File | Document name | Profile | Default output |
|---|---|---|---|
| `draft.md` | `paper` | `paper` | `typst` |
| `slides.md` | `slides` | `slides` | `typst-slides` |
| `handout.md` | `handout` | `handout` | `typst` |

A **profile** describes the document's purpose. It controls the table of
contents, section numbering, how the abstract is handled, and whether a
hand-maintained `main.tex` preamble is used.

| profile | TOC | Section numbers | Abstract | LaTeX/Typst output |
|---|---|---|---|---|
| `paper` | no | no (typesetting engine numbers it) | split into its own file | `body.typ` + your own `main.typ` (LaTeX: `body.tex` + `main.tex`) |
| `handout` | yes | yes | left in the body | one standalone `.typ` / `.tex` |
| `slides` | no | no | left in the body | one standalone `.typ` (Beamer: `.tex`) |

Only `paper` uses the external `main.typ` / `main.tex` pattern, because journal
submissions each need their own preamble tweaks. Handouts and slide decks
are faster to keep as single, self-contained files.

Output goes to one folder per format (`build/typst/`, ...). Standalone documents
sit side by side as `<document>.typ`, but the `main.*` pattern has fixed names
(`main.typ`, `body.typ`) that two papers would overwrite, so **each paper gets
`build/typst/<document>/`**.

### `octavo init` and `octavo new`

`octavo init` creates **the part that doesn't depend on what you write**. Papers,
talks and lecture notes differ only in their manuscript template, so there is
just one project layout; manuscripts of any kind, and any number of them, are
added afterwards with `octavo new`.

```
2026-research/
  CLAUDE.md          working agreements for Claude Code (never type a result, ...)
  README.md          the human-facing walkthrough
  octavo.config.py   configuration (a glob per kind of manuscript, analysis registration)
  literature.bib     bibliography (exported from your reference manager)
  requirements.txt   the Python packages the analysis uses (installed into .venv)
  data/raw/          raw data. read-only, gitignored
    README.md        where provenance, retrieval date and terms are recorded
  data/derived/      cleaned data, written by the .qmd. gitignored
  analysis/
    analysis.qmd     a worked example (estimate -> ov_value / ov_figure / ov_table)
    octavo.R         the analysis-side helper (ov_value / ov_figure / ov_table)
  results/
    analysis.json    starter values so {{...}} resolves before R is ever run
  figures/  tables/  with placeholder figures (a box with an ×)
  refs/              material from elsewhere (codebooks, guidelines). kept in git
  notes/             things you wrote (reading, referee notes). never in the manuscript
```

Everything `octavo init` / `octavo new` writes is an **example and says so**:
a `octavo:example` comment in the manuscripts, `analysis.qmd` and
`literature.bib`, `_placeholder` in `results/analysis.json`, and a figure that
is just a box with an ×. Delete the mark along with the content once it's yours;
`octavo check` counts what is left. **Placeholder values are fatal** — before the
analysis has ever run every `{{...}}` still resolves, so a PDF full of fake
numbers would otherwise typeset without a word of warning.

```bash
octavo new paper example-paper      # papers/example-paper/: paper.md, appendix.md
                                  #   and the layout main.typ / main.tex
octavo new slides example-talk        # slides/example-talk.md
octavo new lecture example-lecture # lectures/example-lecture.md
```

Every manuscript template uses `{{...}}` values and the placeholder figure, so
`octavo build --compile` succeeds right after `octavo new`. `octavo new` never
edits `octavo.config.py`; it re-reads the config afterwards to confirm the new
manuscript really is registered, and refuses (writing nothing) when the name is
already taken — even by a document of another kind.

The `.gitignore` excludes `data/raw/` and `data/derived/` so that large or
non-redistributable data can't be committed by accident. `data/raw/README.md`
is the one tracked exception — by convention, that's where data provenance
is written down. `build/` is excluded in full: **the hand-written layout
(`main.typ` / `main.tex`) lives next to the manuscript in `papers/<name>/`** and is
copied into `build/` on every build, so deleting `build/` never loses it.

### Lecture notes: one file, an A4 handout and a deck per session

```bash
octavo new lecture example-lecture
octavo build example-lecture --to typst --compile          # A4 handout (all sessions), straight to PDF
octavo build example-lecture --to typst-slides --compile   # one PDF deck per session
octavo build example-lecture-03 --to typst-slides          # just the third session
```

Lecture notes are a `split_slides: True` document, and **each `#` heading is one
session**. The handout is built from the whole file; the slides are built per
`#`, as separate documents (`example-lecture-01`, `-02`, ...).

- A session deck's title slide takes the `#` heading as its title and the notes'
  `title` as its subtitle; each `##` is a slide
- Numbers follow the order of the `#` headings. **Inserting a session renumbers the
  ones after it**, so give a heading an id to pin its name:
  `# Second session {#second}` → `example-lecture-second`
- Anything before the first `#` (an overall preamble) goes into the handout only
- A `#` inside a code block doesn't split; `# References` and everything after is dropped

Content that should only appear in one output goes inside **conditional
blocks**:

```markdown
::: {.handout-only}
Fill-in-the-blank space and detailed footnotes: handout only.

(                                    )
:::

::: {.slides-only}
Figures and short prompts: slides only.
:::

::: notes
Speaker notes (in the speaker script and in Beamer; never on the projected deck)
:::
```

| Marker | Kept for |
|---|---|
| `.slides-only` / `.only-slides` | `typst-slides`, `typst-notes`, `beamer` |
| `.handout-only` / `.paper-only` | `latex`, `typst`, `docx` (when that profile is active) |
| `.print-only` | `latex`, `typst`, `docx` |
| `.no-slides` / `.not-slides` | negation — dropped only for that format |
| `.notes` / `::: notes` | `beamer`, `typst-notes` (dropped from the projected deck) |

Divs without a recognized marker (e.g. `::: {.warning}`) pass through
unchanged.

---

## 3. Writing the source

| Element | Syntax | Notes |
|---|---|---|
| Heading | `## 1. Section Title` / `### 1.1 Subsection` / `# 2. ...` | numbers become `{#sec:1}` labels; the typesetting engine renumbers them |
| Appendix | `## Appendix A. ...` (or `## 付録A．…`) | becomes `{#sec:appA}` |
| Abstract | `## Abstract` (or `## 要旨` / `## 概要`) | a `*Word count: N words*` line, if present, is split out with it |
| References heading | `## References` (or `## 参考文献`) | dropped at conversion time — the bibliography is built from `.bib` instead |
| Citation | `@key` (inline), `[@key; @key2]` (parenthetical) | |
| Possessive citation | `\poscite{key}` | e.g. "Smith and Taylor's (2003)" |
| Analysis value | `{{n_obs}}` / `{{coef:.2f}}` | filled in from what the `.qmd` wrote to `results/*.json` (§4) |
| Table | `**Table 1. Caption**` + a Markdown table | replaced with an external `.tex`/`.typ` file if `table_map` has an entry |
| Figure | `![](figures/fig1_x.png)` + `**Figure 1.** Caption` | the extension is swapped per output format (LaTeX gets `.pdf`) |
| Cross-reference | "Table 3", "Figure 1", "Section 4.1" (in either language) | becomes an automatic link in LaTeX/Typst |
| Title block | YAML front matter at the top of the file | `title` / `author` / `institute` / `date` |

Both English and Japanese cross-reference phrasing are recognized by
default (`crossref_vocab: 'both'`), and the **source's own wording is
preserved**: "Section 2" becomes `Section~\ref{sec:2}`, while a Japanese
"第2節" becomes `第\ref{sec:2}節`. Typst gets the `#ref(<sec:2>)` form, because
`@sec:2` would swallow any Japanese that follows it into the label name.

### Figure extensions

You only need to drop one `.png` into your source. Each output format
looks for its preferred extension automatically:

| Format | Looks for |
|---|---|
| `latex` / `beamer` | `figures/fig1_x.pdf` |
| `typst` / `typst-slides` / `typst-notes` / `docx` | `figures/fig1_x.png` |

Configurable via `figure_ext`. A missing file is reported as a "missing
figure" at build time rather than failing silently.

### External table files (for analysis-script pipelines)

If an R or Python script writes tables directly as `.tex` / `.typ`, map
table numbers to filenames under `tables/` with `table_map`:

```python
'table_map': {'1': 'tbl1_summary', '2': 'tbl2_models'},
```

For LaTeX this becomes `\inputtable{../../tables/tbl1_summary}`; for Typst,
`#include "../../tables/tbl1_summary.typ"`. Cross-references are resolved
by **reading the `\label` the external file actually defines**, not by
guessing.

Word and slide decks can't embed external table files, so the Markdown
table is used as a fallback there even when `table_map` has an entry.

---

## 4. Analysis (Quarto) and manuscript, kept apart

**The manuscript is `.md`; the analysis is `.qmd`.** Numbers, figures and
tables that appear in the paper are never typed into the manuscript — the
analysis writes them to fixed locations, and each build pulls them in.
There is exactly one source for every number, so re-running an estimation
can't leave the prose describing the old one.

```
analysis/*.qmd  --quarto render-->  results/*.json     the {{...}} in the text
                                    figures/*.pdf|png  figures
                                    tables/*.tex|typ   tables

manuscripts + the three above  --octavo build-->  Typst / Word / LaTeX / Beamer
```

### 4.1 The three channels

`octavo init` puts `octavo.R` (the helper) and an example `analysis.qmd` in
`analysis/`. Load it in the first chunk:

```r
root <- Sys.getenv("OCTAVO_ROOT", unset = "")
source(if (nzchar(root)) file.path(root, "analysis", "octavo.R") else "octavo.R")
```

| What | In the analysis (.qmd) | In the manuscript (.md) |
|---|---|---|
| A number | `ov_value("n_obs", nrow(d))` | `{{n_obs}}` |
| A figure | `ov_figure(p, "fig1_trend")` | `![](figures/fig1_trend.png)` + `**Figure 1.** Caption` |
| A table | `ov_table(tab, "tbl1_summary")` | `**Table 1. ...**` plus `table_map: {'1': 'tbl1_summary'}` in the config |

- `ov_value(name, x, fmt = NULL, note = NULL)` — registers one value into
  `results/<name of this .qmd>.json`. `ov_values(a = 1, b = 2)` registers several.
- `ov_figure(x, name, width, height, dpi)` — writes **both `.pdf` and `.png`**
  into `figures/`, which is exactly what the default `figure_ext` mapping
  expects (LaTeX takes the PDF; Word and Typst take the PNG). `x` may be a
  ggplot or a function that draws with base graphics.
- `ov_table(x, name, caption, notes, align)` — writes **both `.tex` and `.typ`**
  into `tables/`. `x` is a data frame, or `list(tex = ..., typ = ...)` if you
  already have rendered strings. The LaTeX file carries `\label{tab:<name>}`
  and the Typst file carries `<name>`, so "Table 1" in the prose resolves to it.
- `ov_pval(p)` — formats a p-value by convention (`0.023` → `.023`, `< .001`).

### 4.2 Number formatting

How `{{name}}` renders is decided by the value's type.

| Value | Example in R | Output |
|---|---|---|
| Integer | `nrow(d)` (integer) | `1,523` (thousands separator) |
| Double | `coef(m)[["x"]]` | `0.342` (`value_float_format`, default `.3f`) |
| String | `ov_pval(p)` | as-is |

Override with `{{coef_x:.2f}}` in the manuscript, or
`ov_value("coef_x", x, fmt = ".2f")` in the analysis; the manuscript wins.
The spec is a Python format spec (`.2f`, `,`, `.1%`, ...).

**A name with no value is left in place as `{{name}}` and reported** —
silently deleting it would quietly break the text. `octavo values` lists the
whole cross-check.

### 4.3 When it runs

Before converting, `octavo build` compares each `.qmd`'s mtime against the
last run recorded in `results/.analysis-stamp.json`, and runs
`quarto render` only for the ones that are newer.

```python
'analysis': ['analysis/*.qmd'],
# to watch data files too:
'analysis': [{'src': 'analysis/main.qmd', 'deps': ['data/*.csv']}],
'analysis_deps': [],        # dependencies shared by every .qmd
'analysis_to': None,        # quarto render --to (None: whatever the .qmd says)
'analysis_args': [],        # extra arguments passed to quarto
'analysis_auto': True,      # False: only run via octavo analysis run
'results_dir': 'results',
'value_float_format': '.3f',
'value_thousands_sep': True,
```

- `octavo build --no-analysis` — don't run anything; convert with `results/` as-is
- `octavo build --force-analysis` — re-run even when nothing changed
- `octavo analysis` — what's stale, and how many values exist
- `octavo analysis run [--force]` — run the stale ones (manual ones included)
- `octavo analysis run analysis/01-clean.qmd` — run just that one (even if it isn't stale)
- `octavo values [--unused] [--json]` — cross-check `{{...}}` against `results/`
- `octavo values --diff` — **what changed in the paper's numbers since the last run**

**Mark a slow `.qmd` `'manual': True`** (next section). `octavo build` then leaves
it alone and only tells you when it is stale; `octavo analysis run` runs it.

**In VS Code all of this is a button.** The sidebar's Analysis section lists each
`.qmd` as up to date, stale or manual, with a run button, and an open `.qmd` gets a
run button in the editor's title bar. **The preview never runs the analysis**: when
something is stale, a bar above the PDF says so, and its button runs it and rebuilds
the preview afterwards. Progress shows in a notification, quarto's output in the
Output panel (Octavo).

**If quarto isn't installed, this step warns and is skipped** (conversion
itself only needs pandoc). If quarto *is* installed and `render` fails, the
build **stops** rather than typesetting a paper around stale numbers. Use
`--no-analysis` if you want it to proceed anyway.

`octavo analysis run` snapshots the values **just before** it runs, so after a
re-estimation:

```
$ octavo values --diff
Compared with 2026-09-07 10:12:33

Changed (2):
  n_obs                             1,523  ->  1,608
  coef_x                          0.342  ->  0.311
```

The comparison is on the text that reaches the paper, so `0.3419` becoming
`0.3421` is not a change (both print as `0.342` under `.3f`). When a number
moves, check the prose around it too ("slightly", "about").

### 4.4 Splitting the analysis, and adding an appendix

**Multiple analysis files are the expected case.** `analysis` takes globs, so
dropping in another `.qmd` is all it takes to register it.

```python
'analysis': ['analysis/*.qmd'],
```

Each `.qmd` owns `results/<name of that .qmd>.json`. The split is invisible from
the manuscript — every `{{name}}` resolves the same way, because `octavo` reads
all of `results/*.json` into one namespace. **If two `.qmd` files write the same
name, it warns and the later one wins**, so check the `source` column of
`octavo values` when a number looks off.

When **one `.qmd` produces another's input**, do two things: order them, and
list the upstream output in the downstream `deps`.

```python
'analysis': [
    {'src': 'analysis/01-clean.qmd', 'manual': True},        # writes data/derived/ (slow)
    {'src': 'analysis/02-model.qmd', 'deps': ['data/derived/*']},
    {'src': 'analysis/03-robustness.qmd', 'deps': ['data/derived/*']},
],
```

**Put slow steps that rarely change — data cleaning, say — in their own `.qmd`
and mark it `'manual': True`.** Neither `octavo build` nor the preview runs it; they
only say that a manual analysis is stale. Run it with `octavo analysis run` (every
stale one), `octavo analysis run analysis/01-clean.qmd`, or the sidebar button in
VS Code. When it rewrites `data/derived/`, the downstream `.qmd` (through `deps`)
turns stale and runs at the next build.

With a single glob (`analysis/*.qmd`), prefixing file names with `01-`, `02-`
gives the same ordering. Either way, if `01-clean` rewrites `data/derived/`,
`02-model` re-runs **within that same `octavo build`** — staleness is re-checked
one file at a time, as each is reached.

Deleting or renaming a `.qmd` leaves its old `results/<old name>.json` behind. If
the manuscript still references those names, **stale numbers keep flowing in
silently**, so `octavo analysis` and `octavo values` report them as value files
with no matching `.qmd`.

#### The appendix

Keep the appendix in `appendix.md` in the paper's folder (`octavo new paper`
puts one there). `'appendix': 'papers/*/appendix.md'` in `documents` attaches it
to the paper in the same folder.

```python
# external table files for the appendix use their own map
'appendix_table_map': {'A1': 'tblA1_robustness'},
```

```bash
octavo build example-paper --to typst --appendix   # writes both body.typ and appendix.typ
```

Then uncomment `#include "appendix.typ"` in `papers/example-paper/main.typ`
(or `\appendix` and `\input{appendix}` in `main.tex`).

The appendix gets **exactly the same treatment** as the body: value
substitution, citation resolution, conditional blocks and cross-references all
work, and `octavo values`, `octavo checkbib` and `octavo outline` all read it
(shown as `example-paper (appendix)`). Number it separately from the body — `Appendix A.`,
"Figure A1", "Table A1" — with file names like `figA1_balance` and
`tblA1_robustness`.

### 4.5 Using something other than R

The bundled helper is R, but `octavo` only ever looks at **locations and
shapes**, so Python or Julia work just as well if they follow the convention.

- Write `{"name": value}` into `results/<anything>.json`. Integers and
  doubles are distinguished by JSON itself (`1523` vs `1523.0` select
  different default formatting). The form `{"name": {"value": ..., "fmt":
  ".2f", "note": "..."}}` is also read. Keys starting with `_` are ignored.
- Figures go to `figures/<name>.pdf` and `.png`; tables to
  `tables/<name>.tex` and `.typ`.

---

## 5. Citations (.bib → journal style)

### Getting the .bib

Export BibTeX / BibLaTeX from your reference manager (Zotero or any other)
and put the file where `bib_file` points (`literature.bib` by default). With
Zotero, Better BibTeX's automatic export ("Keep updated") keeps the file in
step with your library and keeps citation keys stable.

### Checking your bibliography

```bash
octavo checkbib            # cross-check citation keys against .bib
octavo checkbib --list     # list everything currently cited
octavo checkbib --unused   # entries in .bib that are never cited
```

What it flags:

- citation keys used in the text but missing from `.bib` (these render as
  `??` in the typeset output) — near-miss typos get a suggested key
- missing year / author / journal name / no page range or DOI
- an organization name your reference manager has mistakenly split into given/family
  name (e.g. `Organization, Example`)
- Japanese-language entries missing a `langid`
- duplicate imports of the same reference

**Octavo never edits your `.bib` file.** Fix issues in your reference manager. If
you've decided a flagged issue is fine as-is, silence it with a reason in
`bib_accepted`:

```python
'bib_accepted': {('yamada2020', 'no page range or DOI'): 'bulletin uses a running number instead'},
```

`octavo bib clean` writes a **separate**, lighter copy with `file` /
`abstract` / `keywords` stripped out — your original file is never
touched.

### Matching a journal's style

```bash
octavo csl list                                          # styles you already have
octavo csl get modern-language-association    # fetch one
octavo csl which                                         # the one currently in use
```

One line in `octavo.config.py` affects every output format:

```python
'csl': 'apa',   # short alias, or: chicago / ieee / mla / nature / ...
```

Look up style IDs at <https://www.zotero.org/styles>. Dependent styles
(ones that just point at a parent style) are resolved automatically.
Fetched styles are cached under `octavo/csl/`, so subsequent builds
work offline.

`chicago-author-date` is pandoc's built-in default, so it works even with
no `.csl` file at all.

### How `\poscite` works

CSL has no notion of a possessive citation form. Octavo reads the
author surnames straight out of `.bib`, assembles the possessive phrase
itself, and lets citeproc render only the year, parentheses, and link:

```
\poscite{smith2003}   →   Smith and Taylor's [-@smith2003]
                      →   Smith and Taylor's (2003)
\poscite{yamada2020}  →   山田・田中[-@yamada2020]
                      →   山田・田中(2020)
```

Joining multiple authors ("and" / "et al." / Japanese "・"/"ほか") is an
approximation, not a full re-implementation of CSL's own naming rules —
double-check the rendered output for journals that care about exact
formatting.

---

## 6. Commands

```
octavo build [documents...] [--to formats] [--appendix] [--compile] [--no-citations]
                                              [--no-analysis] [--force-analysis] [--json]
octavo watch [documents...] [--to formats]     rebuild whenever a source or .qmd is saved
octavo documents [--json]                      list the registered manuscripts
octavo config [set KEY VALUE | unset KEY] [--json]  show or change the common settings
octavo analysis [status|run] [--force]         inspect / run the .qmd analyses
octavo values [--unused] [--diff [ref]] [--json]  cross-check {{...}} against results/
octavo lint [--json]                           find results typed into the manuscript
octavo check [--strict] [--anonymous]          one pre-submission audit
octavo bundle [--anonymous] [--replication] [--with-raw-data]
octavo review returned.docx [--comments|--insertions] [--json]
octavo data [status|hash]                      fingerprint the data (sha256)
octavo checkbib [--list] [--unused]
octavo bib clean                           a lighter copy of the .bib without fields typesetting ignores
octavo csl get|list|which [ID]
octavo doctor
octavo init <dir> [--lang ja|en]
octavo new paper|slides|lecture <name>        add a manuscript
octavo template list|copy|diff [name] [--user]  your own templates (§7)
octavo release <document> <label> [--dry-run]   tag this version, PDF to a GitHub Release
octavo selftest [--to formats] [--csl ID] [--keep]   verify citation rendering end-to-end
octavo reference-docx [out.docx]        generate a Word style template
octavo outline [documents...]           show the heading structure
octavo targets                          list available output formats
```

`--to` takes a comma-separated list, e.g. `typst,docx`. `all` and `print`
(shorthand for `typst+docx`) are also accepted. `--compile` runs
`typst compile` / `latexmk` on standalone documents, and for the `paper`
profile's Typst output compiles `main.typ` (after writing the appendix, if
any). For the `paper` profile's LaTeX output, run `latexmk` on `main.tex`
yourself — how it has to be run differs from journal to journal.

`--no-citations` skips citation resolution — useful for a fast visual
check while drafting. `--no-analysis` skips running the `.qmd` files and
converts with whatever is currently in `results/`, which is what you want
when an estimation is slow.

### One audit before submitting

`octavo check` runs every check in one pass, separating **fatal** (the output
would be broken or wrong) from **warnings** (a human decides). By default it
exits non-zero only on fatal findings.

```
$ octavo check
[  ok  ] sources          papers/example-paper/paper.md, papers/example-paper/appendix.md, slides/example-talk.md
[ warn ] analysis         1 of 2 stale
           analysis/02-model.qmd
           -> octavo analysis run
[fatal ] figure files     1 missing
           figures/fig2_effect.pdf
           -> octavo analysis run, or drop it into figures/
```

It covers: sources exist / analysis freshness / orphaned value files /
unresolved `{{...}}` / **placeholder values still in place** / citation keys /
bibliography quality / **figure and table files actually existing** /
placeholder figures / **template leftovers** / results typed into the prose /
submission limits / data fingerprints / recorded analysis environment.
Use `--strict` in CI to fail on warnings too.

**Placeholder values are the one fatal item here**, because a project whose
analysis has never run still resolves every `{{...}}` and would typeset fake
numbers silently. `octavo build` also prints a warning on every run.

`octavo lint` reports the template leftovers and the "typed into the prose"
part in detail.

```
$ octavo lint
3 things that look like results typed into the manuscript

  example-paper
      51: N = 1,523   [sample size]
          The coefficient was 0.342 (SE 0.081) with N = 1,523.
```

This is the machine-checkable version of "never type a result into the
manuscript". Tables, headings, code blocks, DOIs, links and `{{...}}` format
specs are skipped, and conventional constants (`0.05`, `1.96`, ...) are ignored
by default; add anything else that isn't a result to `lint_accepted`.

### Word and character limits

Put the journal's limits in `octavo.config.py` and `octavo check` enforces them.
Omit them and nothing is checked. Exceeding one is **fatal** — you cannot submit.

```python
'word_limit': 8000,            # body text
'char_limit': 20000,           # body text, for Japanese journals
'abstract_word_limit': 150,
'abstract_char_limit': 400,
```

Counting happens after `{{...}}` substitution, with the abstract, references and
title block taken out of the body (the same counting `octavo build` reports as
`[length]`). The appendix is not counted.

### Blind review

Produce a version with everything identifying removed. **No new syntax** — the
conditional blocks you already have simply gain an `anonymous` flag.

```markdown
::: {.no-anonymous}
Acknowledgements: this research was funded by ...
:::

::: {.anonymous-only}
[Acknowledgements withheld for review]
:::
```

```bash
octavo build example-paper --anonymous
octavo bundle example-paper --anonymous   # checks for leaks before packaging
octavo check --anonymous                # also lists self-citation candidates
```

`--anonymous` does three things:

1. drops `.no-anonymous` blocks and keeps `.anonymous-only` ones
2. removes `anonymous_drop_meta` (author, institute, thanks, email by default)
   from the title-block metadata
3. writes the switch into `build/typst/<paper>/flags.typ` (`build/latex/<paper>/flags.tex` for LaTeX).
   It is **rewritten on every build**, so a normal build always restores the
   non-anonymous version — you cannot leave it on by accident.

**The title block lives in `main.typ` / `main.tex`, which Octavo never rewrites.** The bundled
layouts (`templates/paper/{ja,en}/main.{tex,typ}`) wrap the author line in
`\ifanonymous` (`#if anonymous` for Typst), so they switch as they are.

`octavo bundle --anonymous` then checks the packaged files for leaks:

- a name outside any conditional → **failure** (you forgot)
- a name inside one → won't be typeset, but you're told it still sits in the
  `.tex` source (for journals that want sources)
- no `octavo build --anonymous` behind it → refused

Self-citations (cited works whose authors include you) are listed by
`octavo check --anonymous`. Whether to mask them depends on the journal, so it
**only lists candidates**.

### Repackaging for submission

Journal submission systems rarely accept a directory tree. `octavo bundle`
rewrites `image("../../figures/fig1.png")` to `image("fig1.png")` (for LaTeX,
`\includegraphics{../../figures/fig1.pdf}` to `{fig1.pdf}`), collects every
referenced file into one place, and zips it. Typst is the default; pass
`--to latex` to package a LaTeX submission. It packages **one paper**, so give
its name (it can be left out when the repository has a single paper).

```bash
octavo build example-paper
octavo bundle example-paper                      # submission-example-paper.zip
octavo bundle example-paper --dir --out example-talk # a folder instead of a zip
```

`\newcommand` definitions and comment lines in `main.tex`, and `//` comment lines
in `main.typ`, are not followed, and
an `\input` guarded by `\IfFileExists{...}` isn't counted as missing when it
isn't there. **`build/` itself is never touched** — the work happens on a copy.

### Reading a coauthor's Word edits

Coauthors mark up Word and send it back. `octavo review` lists what they did.

```bash
octavo review 20260907_draft_tanaka.docx
octavo review returned.docx --comments      # comments only
```

```
20260907_draft_tanaka.docx: 3 changes in 2 paragraphs
  Hanako Tanaka: 3

  paragraph 1: The sample had 1,523 cases and the coefficient was 0.342 (statistically sign
    [inserted] Hanako Tanaka  2026-09-05 10:11
       (statistically significant)

  paragraph 2: We then turn to the robustness checks.
    [deleted] Hanako Tanaka  2026-09-05 10:14
       in detail
    [comment] Hanako Tanaka  2026-09-05 10:20
      Cite the new replication here?
```

**There is no round trip, deliberately.** In the returned `.docx`, `{{n_obs}}`
is already the literal text "1,523". Converting docx → md would, at that
moment, break the one thing this tool exists to guarantee. So it **extracts the
tracked changes and comments only** and you apply them to `paper.md` yourself.
That is the only safe direction, and this design is the consequence.

It reads the `.docx` (a zip) directly, so no pandoc and no extra dependency.

### Keeping the version you sent (`octavo release`)

`build/` stays out of git — everything in it can be rebuilt from what git holds.
What cannot be rebuilt exactly is **the PDF you actually sent**: a newer Octavo,
pandoc, Typst or font changes the result. So at the milestones (to coauthors,
submitted, presented) put that PDF somewhere outside your machine:

```bash
octavo release example-paper v1-submitted
```

This tags the current commit `example-paper-v1-submitted`, pushes the tag, and makes
a GitHub Release with the freshly typeset PDF (and Word file, if the document
builds one) attached as `example-paper-v1-submitted.pdf`. The release notes record
the commit and the Octavo / pandoc / Typst versions. The files live on GitHub,
not in the git history, so the repository doesn't grow.

It refuses — listing every reason at once — when there are uncommitted changes
(the tag has to point at what was typeset), the analysis is stale or still the
placeholders, or the tag already exists. It builds on the spot and never runs the
analysis (that would change `results/` after the commit). `--dry-run` checks and
builds but tags and uploads nothing; `--anonymous` releases the blind version.
It needs the [GitHub CLI](https://cli.github.com/) (`gh auth login`) and a
GitHub remote called `origin`.

### Showing what changed in a revision (R&R)

Give `octavo values --diff` a **git tag or commit** and it compares against that
version — the tags `octavo release` makes work as they are.

```bash
octavo release example-paper v1-submitted   # at submission (or just git tag it)
# ... review, revise ...
octavo values --diff example-paper-v1-submitted
```

```
Compared with git example-paper-v1-submitted

Changed (2):
  n_obs                             1,523  ->  1,608
  coef_x                          0.342  ->  0.311
```

No new versioning machinery: git already holds the manuscript diff, so Octavo
only supplies **the part git couldn't give you — the numbers as of that version**.

### Fingerprinting the data

`_session` records the software the analysis ran under. The other half of
reproducibility is **whether it ran on the same data**, and that is this.

```bash
octavo data hash      # record what's in data/ right now
octavo data status    # has anything drifted from the record?
```

`data/raw/` and `data/derived/` are gitignored, which makes
`data/HASHES.json` the **only surviving record** of which data was used (paired
with the provenance in `data/raw/README.md`). `octavo check` reports drift too.

### The replication package (after acceptance)

Submission packaging collects "what typesetting needs". A replication package
collects "**what reproducing this result needs**" — a different set.

```bash
octavo bundle --replication                  # replication.zip
octavo bundle --replication --with-raw-data  # include the raw data too
```

It contains `analysis/` (helper included), `results/`, `figures/`, `tables/`,
`data/derived/`, `data/HASHES.json`, `octavo.config.py`, `literature.bib`, and a
generated README with the recorded `_session`. **Raw data is excluded by
default** — it often can't be redistributed — so `--with-raw-data` is explicit.
Use `replication_exclude` globs to drop individual files.

---

## 7. Making it yours: templates and Word styles

### Your own templates

Everything Octavo writes or typesets from — the project skeleton, the
manuscript templates, a paper's `main.typ` / `main.tex`, the slide and handout
looks — is a file under `templates/`, and **each can be replaced with your
own**. Put a file with the same relative path in `<project>/templates/` (that
project only) or `~/.config/octavo/templates/` (all your projects). Octavo
looks in the project first, then your folder, then the bundled templates, and
uses the first it finds, as a whole.

```bash
octavo template list                              # what is in use, and from where
octavo template copy slides/typst-slides.typ      # into this project's templates/, to edit
octavo template copy paper/en/main.typ --user     # your journal layout for every new paper
octavo template diff slides/typst-slides.typ      # yours against the bundled one
```

A few that are worth knowing:

| Template | Used by | Replace it to |
|---|---|---|
| `slides/typst-slides.typ`, `slides/typst-notes.typ` | every slide build | change the look of decks and scripts |
| `paper/<lang>/main.typ`, `main.tex` | `octavo new paper` | start every paper from your usual layout |
| `manuscripts/<lang>/*.md` | `octavo new` | start manuscripts from your own skeleton |
| `project/<lang>/…` | `octavo init` | change what a new project contains — files you **add** there are written into every new project too |
| `handout/handout-header.tex`, `slides/beamer-header-<lang>.tex` | LaTeX / Beamer builds | change the LaTeX preamble |

A copy doesn't follow later changes to the bundled template. After updating
Octavo, `octavo template diff <name>` shows what differs. The full list is in
[`templates/README.md`](templates/README.md).

### Word styles

```bash
octavo reference-docx reference.docx
```

This produces pandoc's default template. Open it in Word, adjust the
`Heading 1`, `Body Text`, `Table Caption`, etc. styles to taste, save it,
and point the config at it:

```python
'docx_reference': 'reference.docx',
```

Its actual content doesn't matter — only the style definitions are used.
Word has no LaTeX-style auto-numbered cross-references, so **table/figure
numbers are written into the caption as literal text** (e.g. "Table 1.
Descriptive Statistics"), and in-text mentions like "Table 3" stay as
plain text too. As long as the numbering in your source is sequential,
these stay consistent.

Section numbers work the same way: **the numbers already present in the
source** (the "1." in `## 1. Introduction`) are restored as literal text.
pandoc's `--number-sections` doesn't work for Word, and renumbering from
scratch would break sequences like "1, 2, Appendix A" — so the source's
own numbering is used instead.

---

## 8. Differences between formats (worth knowing)

| | LaTeX | Typst | Word |
|---|---|---|---|
| Japanese fonts | `haranoaji` ships with TeX Live — no setup needed | **not bundled** — `setup.sh` installs them (see Typefaces; check with `typst fonts`) | handled by Word itself |
| Section numbers | typesetting engine numbers them | typesetting engine numbers them | **source's own numbers restored as text** |
| Table/figure numbers | automatic | automatic | written into the caption as text |
| Cross-references | linked via `\ref` | linked via `#ref(<label>)` | plain text |
| External table files | `\inputtable` | `#include` | not supported |
| `**bold**` inside captions | rendered literally | rendered as actual bold | — |
| Bibliography | `CSLReferences` environment (needs a definition in `main.tex`) | embedded in the body | plain paragraphs |

Setting `typst_citations: 'native'` hands citations to Typst's own
`bibliography()` function instead of CSL (driven by `main.typ`). The
default is `'csl'`.

**Slide decks don't get a bibliography list** by default (no room in the
frame). To include one, add a heading and an empty `::: {#refs}` at the
end of the slide manuscript and set `slides_bibliography: True`.

```markdown
## References

::: {#refs}
:::
```

### Typst slides

`typst-slides` is **plain Typst with no packages**, so compiling needs no
network (Typst 0.12+). There are no animations or incremental reveals.

- With both `#` and `##` headings, `#` makes a section divider and `##` a slide;
  with a single heading level, each heading is a slide. A `#` heading followed
  directly by content becomes a titled slide rather than a divider
- Figures are fitted into the remaining height of the slide; figures and tables
  are not numbered
- The title slide comes from `title` / `subtitle` / `author` / `institute` /
  `date` in the front matter
- The look lives in `templates/slides/typst-slides.typ`; to change it, copy it
  with `octavo template copy slides/typst-slides.typ` and edit the copy (§7).
  The config keys are:

| Key | Default | What it changes |
|---|---|---|
| `typst_slides_aspect` | `'16-9'` | `'16-9'` / `'4-3'` |
| `typst_slides_font` | BIZ UDGothic + Inter | font list, used as-is when set (see Typefaces) |
| `typst_slides_numbering` | `None` | heading numbers, as a Typst numbering string (`'1.'` / `'1.1'`); `'1.1'` needs `#` sections |
| `typst_slides_section_slides` | `True` | `False` makes a `#` section advance the counter without producing a divider slide |
| `typst_slides_accent` | `'#0e2f92'` | accent colour, or `None` for plain black. **Any non-`None` value switches the look** (below) |
| `typst_slides_running_header` | `True` | prints the current `#` section small in the top-left corner (the deck's title where there is none — a lecture session, say) |

  **The look only changes when an accent colour is set** — which it is by
  default (the blue above). Set `typst_slides_accent` to `None` for the plain
  look instead: bold titles, `• ‣ –` markers, a plain page number. With an
  accent, titles are set in the accent colour instead of bold, list markers
  become `▶`, the page number becomes "4 / 11", and links are coloured too.
  **List indentation is fixed regardless of the accent** — nested items used to
  start exactly where their parent's text did, so the hierarchy was unreadable.

- Five theorem-like helpers are available from a raw ```` ```{=typst} ```` passthrough
  block (values in `{{…}}` still resolve inside one): `#case[…]` / `#question[…]` /
  `#aside[…]` share one counter that resets each `#` section and includes the section
  number (e.g. `Case 2.1`); `#nb[…]` / `#memo[…]` are unnumbered. `#smallgray[…]` sets
  small gray text (for a source line under a figure, say). Beamer does not have these.

### The speaker script (`typst-notes`)

`::: notes` is dropped from the projected deck — there is nowhere on a slide to
put it. `typst-notes` is where it goes: **the same source**, same conditional
blocks, but A4 portrait with one page per slide and the notes in a ruled box
underneath.

```bash
octavo build example-lecture-03 --to typst-notes --compile
```

It reuses every `typst_slides_*` setting (same meta block), and the five
theorem-like helpers work there too — a deck that uses `#case[…]` builds as a
script unchanged. The look lives in `templates/slides/typst-notes.typ`, and is
changed the same way (§7). Figures are capped at 6cm high so
the notes still fit on the page. Add it to a document's `targets` to get it on
every build, or ask for it with `--to` when you need it.

### LaTeX and Japanese

For Japanese documents, standalone LaTeX/Beamer output deliberately skips
loading `babel`. Citation localization needs the `lang` metadata, but
pandoc's template tries to map that into a babel language name and emits
a broken line in the process (Japanese typesetting is handled by
`luatexja`, which doesn't need babel at all).

---

## 9. Project layout

```
octavo/
  octavo                   entry point (put this on your PATH)
  pyproject.toml           packaging (pip install; distribution octavo-kit, command octavo)
  setup.sh                 install script for Linux / WSL2 (apt) and macOS (Homebrew)
  config.example.py        configuration template (English)
  config.example.ja.py     the same template in Japanese — keep the two in key-for-key sync
  octavo/
    cli.py                 subcommands
    config.py              loads octavo.config.py and defines defaults
    md.py                  format-agnostic preprocessing (headings, tables, figures, conditional blocks)
    values.py              substitutes analysis values into the {{...}}; diffs against the last run
    analysis.py            staleness check for .qmd files and quarto render
    lint.py                finds results typed into the manuscript
    audit.py               octavo check (gathers every check)
    bundle.py              octavo bundle (submission and replication packages)
    review.py              reads tracked changes out of a coauthor's .docx
    ghrelease.py           octavo release (tag a version, PDF to a GitHub Release)
    dataset.py             data fingerprints (data/HASHES.json)
    build.py               the preprocess -> pandoc -> postprocess pipeline
    pandocrun.py           invoking pandoc and checking its version
    bib.py                 .bib parsing and validation
    csl.py                 resolving and fetching CSL styles
    paths.py               where the bundled templates live (repo checkout vs. pip install)
    tmpl.py                finds a template: the project's, then yours, then the bundled one
    confedit.py            octavo config: which settings the sidebar offers, and the line-level edit
    i18n.py                the display language (OCTAVO_LANG); t() wraps every message
    lang_ja.py             the Japanese of every message (the source strings are English)
    check.py               octavo checkbib
    doctor.py              octavo doctor
    selftest.py            octavo selftest
    scaffold.py            octavo init (the research project tree, placeholder figures) and octavo new (add a manuscript)
    backends/
      base.py              the Backend base class and shared cross-reference logic
      latex.py  typst.py  typst_slides.py  typst_notes.py  beamer.py  docx.py
  templates/                every template, each replaceable (§7; templates/README.md)
    project/                the project skeleton octavo init writes (common/ + ja/ or en/)
      common/analysis/octavo.R   the analysis-side helper (ov_value / ov_figure / ov_table)
    manuscripts/            what octavo new writes (paper / appendix / slides / lecture)
    paper/                  main.typ / main.tex per language, and csl-preamble.tex
    slides/  handout/       the looks used by octavo build (Typst, Beamer, LaTeX handout)
  csl/                      cache of fetched CSL styles
  tests/test_octavo.py    unit tests
```

**Adding a new output format** means writing one file under `backends/`
and registering it in `REGISTRY` — `build.py` never branches on format
name.

```bash
python3 tests/test_octavo.py        # anything needing a missing tool is skipped automatically
```

`octavo init` also drops in **placeholder figures** (a PNG and a PDF showing a
box with an ×, carrying a `octavo:placeholder` mark that `octavo check` reads)
that the example source references, so `octavo build --compile` succeeds
end-to-end even before you've added real figures.

---

## 10. What is tested, and what to check yourself

Please read this section before trusting the output for something that
matters.

**Covered by the test suite, run in CI on every push:**

- Building every format from sample sources (Typst, Typst slides and scripts,
  Word, and the LaTeX / Beamer *source*), and Typst all the way to a PDF with
  `typst compile` — CSL citations, figures, tables, cross-references, the
  `main.typ` pattern and standalone documents
- A project made from scratch with `octavo init` + `octavo new` (a paper, a
  talk, lecture notes), from a wheel installed outside the repository
- Heading-to-label conversion, English/Japanese cross-references,
  conditional-block filtering, table/figure substitution, front-matter
  handling
- `.bib` parsing and validation, `\poscite` expansion, CSL style
  resolution from cache
- Value substitution (`{{...}}` formatting, missing names, collisions between
  result files, leaving code blocks alone) and `.qmd` staleness detection
  (mtime vs. stamp, dependency tracking, chained `.qmd` files)
- `quarto render` of the bundled example analysis with `octavo.R`, checking
  what it writes to `results/`, `figures/` and `tables/`
- Raw-number detection, the `octavo check` verdicts, and `octavo bundle` path flattening
- Blind-review filtering (conditional blocks, title metadata, the build flag and
  leak detection), submission length limits, data fingerprints, reading tracked
  changes out of a `.docx`, diffing values against a git ref, and the contents
  of the replication package
- The VS Code extension compiling and packaging, and the JSON contract between
  it and the CLI (its behaviour inside VS Code is not automated)

**Not exercised automatically — check these on your own machine the first
time:**

- **Actual CSL citation rendering.** This depends on the version of
  pandoc installed on your system; older pandoc (< 2.11) lacks
  `--citeproc` entirely. Run `octavo selftest` — that's exactly what it's
  for.
- **Japanese fonts in Typst.** Typst bundles no CJK fonts; without BIZ UD
  or Noto CJK another font is substituted, so look at your first PDF
  (`octavo doctor` reports which of the default typefaces Typst can see).
- **LuaLaTeX compilation.** Nothing in CI compiles LaTeX. The `ltjsarticle` /
  `luatexja` / Beamer theme combination should be visually checked the first time, on a
  machine with the right fonts installed (`octavo doctor` reports what's
  missing).
- **Your own analysis environment.** The example analysis runs in CI, but
  whether your R version and packages work is worth checking once.
- **Live CSL style downloads** — cached resolution is well-tested; live
  fetches depend on your network access.

If you hit something that looks wrong, please open an issue with the
`octavo doctor` output and the pandoc/TeX/Typst versions involved.

---

## 11. VS Code extension

`vscode-extension/` contains a VS Code extension that wraps this CLI. It
adds command-palette access to `build` / `checkbib` / `doctor` and friends,
`@`-triggered citation completion from your `.bib` file in Markdown,
`{{`-triggered completion and hovers for the values your analysis produced,
and red squiggles under citation keys and `{{...}}` names that don't resolve. All validation logic
lives in the Python side (`octavo checkbib --json`) — the extension is a
thin client, not a second implementation. When VS Code itself runs on
Windows, the extension shells out through `wsl.exe` to run `octavo` inside
WSL automatically. It also has a **live preview**: the typeset PDF sits in the
column beside the manuscript and rebuilds on every save, and lecture notes get
a third column with the deck for the session the cursor is in (switchable to
the speaker script, or off for a plain two-column layout).
See `vscode-extension/README.md` for details.

Its interface is English by default and Japanese when VS Code runs in
Japanese, and it passes the same language on to the CLI.

```bash
cd vscode-extension
npm ci && npm run compile
npx @vscode/vsce package    # produces a .vsix — install via "Install from VSIX..." in VS Code
```

---

## Contributing

Issues and pull requests are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
