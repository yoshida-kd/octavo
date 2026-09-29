# Changelog

Octavo's command-line tool (`octavo-kit` on PyPI) and this extension are
released together, under one version number.

## 0.3.0

- **The README is now an overview** — what Octavo does, a diagram, an example
  of the output, install and getting started. The full manual moved to
  [docs/guide.md](https://github.com/yoshida-kd/octavo/blob/main/docs/guide.md)
  ([日本語](https://github.com/yoshida-kd/octavo/blob/main/docs/guide.ja.md)).
- The Japanese wording was reviewed throughout (the CLI, the extension, the
  templates and the documentation), and the extension's Japanese messages are
  now polite form.
- **`octavo init` writes only the frame; the rest are parts you add.**
  An analysis is now added like a manuscript, with `octavo new analysis
  <name>` (the first one brings `octavo.R`, `data/`, `tables/` and
  `requirements.txt`), so a project that is only slides has no analysis in
  it. To start with parts, name them: `octavo init study --with
  analysis,paper`, `--with slides=talk`, or `--all` for all four. The
  project's `CLAUDE.md` gets a section for each kind of part as it is added.
  `octavo check` and `octavo env` say nothing about an analysis a project
  does not have.
- **Nothing written by default has to be deleted later.** No made-up
  analysis, placeholder values, figure or table, example bibliography,
  `notes/` or `refs/`; the project README is a few lines to finish yourself;
  a manuscript is bare headings. `--example` (on `init` and `new`) brings
  the examples back — an example manuscript also brings the example analysis
  and references it uses when the project has none.
- **Settings per document.** The citation style, output formats, submission
  limits and the look of slides can be written at the top of a manuscript
  (`csl: apa`, `targets: [typst, docx]`, `word_limit: 8000`, …) and then apply
  to that document only; `octavo config --doc <name>` shows and changes them.
- **The sidebar, reordered:** manuscripts, analysis, tools in the order they are
  used, then the project settings folded away. Each manuscript has **Settings
  for this document**; the citation style is picked from a list; adding a
  manuscript and adding an analysis are separate buttons.
- `octavo new paper` writes `appendix.md` only with `--appendix` and `main.tex`
  only with `--tex`; both can be run again on an existing paper to add just the
  missing file. A LaTeX build without `main.tex` says how to add it.
- **The extension:** New Project asks what to start with (any of the four
  parts, or none) and whether they are examples. The sidebar adds manuscripts
  and analyses and opens what it made (through `octavo new --json`), shows a
  paper's appendix or a button to add one, and adds `main.tex` from a paper's
  right-click menu.
- **Several projects in one workspace:** the extension uses the project of the
  file you are editing (the nearest `octavo.config.py` above it), stays with it
  while you look at files outside any project, and reloads the sidebar,
  citations and values when you move to another project. The sidebar shows
  which project it is on.
- `octavo doctor` and `setup.sh` notice R packages that were built for an older
  R and no longer load — left behind when R is upgraded, they break the
  analysis outside renv projects — and print the command that rebuilds them.
- `typst_slides_section_slides` now defaults to `False`: a `#` section no
  longer gets a divider slide of its own (it still advances the counter).
  Set it to `True` for the old behaviour.
- Fixed: a captioned figure on a slide was pushed onto a page of its own
  with no title; a paper's bibliography heading came out as a plain line of
  text (in Typst, LaTeX and Word).
- Fixed: an empty `## Abstract` swallowed the next section's heading, so the
  body's numbering started at 0.1; and an empty abstract now clears the
  previous `abstract.typ` / `abstract.tex`.

## 0.2.0

- **Installing the extension is enough.** On first start it checks the tools
  (`octavo doctor --json`) and offers **Set up**, which runs the bundled
  `setup.sh` in a terminal: pandoc, Typst, quarto, fonts, R (the latest from
  CRAN), renv, uv and the `octavo` command itself (from PyPI with uv). Also in
  the sidebar under Tools, to run again after an update.
- `octavo setup` runs the same script from a terminal (the package carries it);
  `setup.sh` now installs R from CRAN's apt repository on Ubuntu, points R at
  Posit Package Manager so renv gets prebuilt binaries, installs renv and uv,
  and speaks English or Japanese.
- `octavo env` (and **Set Up This Project's Analysis Environment** in the
  sidebar) makes the project's `.venv` with uv, installs `requirements.txt`,
  and sets up renv with knitr and rmarkdown — or restores it from `renv.lock`.
- A Python `.qmd` runs with the project's `.venv` without activating it.
- The extension finds `octavo` in `~/.local/bin` even when VS Code's `PATH`
  does not have it, and adds it to the terminals it opens.
- **Cross-references by label, numbered by section.** Figures, tables,
  equations and sections are labelled (`{#fig-trend}`, `: Caption {#tbl-desc}`,
  `$$ … $$ {#eq-model}`, `## Analysis {#sec-analysis}`) and referred to as
  `@fig-trend` — Quarto's syntax. Numbers are never typed: Typst and LaTeX
  number by section (Figure 2.1, Equation (2.1)), Word gets the numbers written
  in, slides and lecture decks match the handout. `crossref_numbering:
  'document'` numbers straight through. Equations can now be numbered and
  referred to. **This replaces the number-based references** (`## 1. …`,
  `**Figure 1.**` captions, "Table 1" in the prose, `table_map`), which are gone.
- `ov_table()` writes only the table's contents (`.tex`, `.typ` and a `.md` for
  Word); the manuscript's one line `: Caption {#tbl-<name>}` places it.
- **Math macros work everywhere.** A one-line `\newcommand` in the manuscript
  now reaches every part that is converted separately — a paper's body,
  abstract and appendix, and each session deck of lecture notes; before, it
  was dropped with the title block or never reached the abstract. The README
  has a new section on writing math.
- **Windows without WSL** works too (after Linux and macOS in priority):
  `setup.ps1` installs the tools with winget (and BIZ UD / Inter as user fonts),
  `octavo setup` runs it on Windows, and the extension runs `octavo` directly
  when WSL has no distribution, with PowerShell terminals. Yu Mincho / Yu Gothic
  are the last CJK fallback, as Hiragino is on a Mac.

## 0.1.0

First release of **Octavo**, the quantitative social science starter pack.

**The `octavo` command**

- One Markdown source to Typst (papers, A4 handouts, slides, speaker
  scripts), Word, and — with TeX — LaTeX and Beamer.
- Citations from one `.bib` file and a CSL style, the same in every format.
- Numbers, figures and tables pulled from Quarto (`.qmd`) analyses through
  `{{name}}`, `figures/` and `tables/` (R helper: `ov_value()`, `ov_figure()`,
  `ov_table()`); `octavo values`, `octavo lint` and `octavo check` make sure
  none is typed by hand or left stale.
- `octavo init` / `octavo new` for a research project with any number of
  papers, talks and lecture notes (English or Japanese).
- Blind review, submission packages, replication packages, tracked changes
  from a returned `.docx`, and `octavo release` to keep the PDF you sent.
- Every template can be replaced per project or per user
  (`octavo template list | copy | diff`).
- Messages in English or Japanese, with proper English plurals.
- Linux, WSL2 and macOS: `setup.sh` installs everything with apt or Homebrew,
  and `octavo doctor` gives hints for the system it runs on.

**The VS Code extension**

- Live PDF preview beside the manuscript, rebuilt on save; a third column for
  lecture notes (the session's deck or the speaker script).
- Octavo in the activity bar: manuscripts, common settings, tools.
- `@key` citation completion, hover and missing-key diagnostics; `.bib`-side
  diagnostics.
- `{{name}}` analysis-value completion, hover and diagnostics.
- Command-palette access to the `octavo` CLI, snippets, a `$octavo` problem
  matcher.
- English and Japanese, following VS Code's display language.
