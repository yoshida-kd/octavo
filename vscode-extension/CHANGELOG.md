# Changelog

Octavo's command-line tool (`octavo-kit` on PyPI) and this extension are
released together, under one version number.

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
