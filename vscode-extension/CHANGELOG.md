# Changelog

Octavo's command-line tool (`octavo-kit` on PyPI) and this extension are
released together, under one version number.

## 0.1.0

First release of **Octavo**, the quantitative social science starter pack.
(It was briefly published as Galley and then Galleykit; neither is maintained.
A project from those days is recognised and `octavo` says what to rename.)

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
