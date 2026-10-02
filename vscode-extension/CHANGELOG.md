# Changelog

Octavo's command-line tool (`octavo-kit` on PyPI) and this extension are
released together, under one version number.

## 0.6.1

- **Fixed: text after a "References" heading was dropped.** Everything from the first
  `References` / `参考文献` / `文献` heading to the end of the file was left out, so a reading
  list (`### 参考文献`) inside one session of lecture notes made **every later session vanish**
  from the handout and the decks, and an appendix written after a paper's `## References`
  disappeared — without a word. Now only a placeholder is dropped: a paper's last
  `## References` section as before, or such a section with nothing but a placeholder line or
  a comment under it; a reading list stays as written.
- **knitr and rmarkdown in your own R library.** Quarto needs them to run an R `.qmd` outside a
  project, and they disappear when an old R's packages are removed. `octavo setup` (and
  `octavo setup --r-editor` alone) installs them with `languageserver`, as ready-made binaries
  on Ubuntu; `octavo doctor` checks them.
- **No more `source …/.venv/bin/activate` in R terminals.** In a project with an R analysis and
  a `.venv`, the extension turns off the Python extension's terminal activation for that
  folder (once, with Undo; never over your own setting).
- **The `.qmd` HTML view steps aside for Quarto's Preview**: it closes when the Quarto
  extension's preview starts and stays closed while it runs.
- `selftest` shows the citations and the bibliography as they read when typeset, instead of
  fragments of LaTeX and Typst source. `octavo checkbib` reports a Japanese name written without
  a comma (`山田 太郎` reads 太郎 as the family name; write `山田, 太郎`).
- `octavo env` says that `renv::status()` reporting "out-of-sync" for unused packages is harmless.
- `typst_slides_font` can be set at the top of a manuscript too, like the other slide settings.
- pandoc's harmless "Invalid 'lang' value" warning (from the LaTeX babel workaround) is no
  longer printed.
- The guide, the lecture-notes page, the README and the web page: getting started in VS Code,
  `octavo env` before building the example (a fresh machine has no knitr/rmarkdown outside a
  project), consistent wording, and a few descriptions that did not match what Octavo does.

## 0.6.0

- **The preview follows the cursor.** Moving the cursor in a manuscript scrolls the PDF
  preview (and a lecture's deck) to the same place, found by the text of the line — or, when
  that is not in the PDF, the heading above it, or the line's position in the file. The
  preview can still be scrolled on its own; the ⇅ button in its toolbar turns the following
  on and off for the session, and `octavo.previewFollowCursor` sets it (on by default).
  Typst has nothing like SyncTeX, so this is a text search: a line whose words differ in the
  PDF (a value, a table cell) lands at the heading or the proportional position.
- **Opening a `.qmd` shows the HTML it last rendered**, to the right of the editor
  (`octavo.qmdPreview`, on by default; only in an Octavo project). Nothing is rendered by
  this, and saving the `.qmd` renders nothing either: run the analysis, and the page reloads by
  itself. It expects `embed-resources: true` (what a new `.qmd` has).
- **`octavo migrate` (temporary — removed in the next release)** moves an older project's
  `CLAUDE.md` into `AGENTS.md` (the text unchanged) and leaves `CLAUDE.md` pointing at it.
  `--dry-run` only says what it would do.
- **Python analyses.** `octavo new analysis <name> --engine python` (or **Analysis in Python**
  in VS Code) writes a `.qmd` in Python that loads `analysis/octavo_helper.py`: the same
  `ov_value` / `ov_figure` / `ov_table` / `ov_pval` / `ov_palette` / `ov_tint` as `octavo.R`,
  writing the same files, so the manuscript is written as for R. It takes a matplotlib Figure
  (or plotnine, or a function that draws) and a pandas DataFrame (or a dict, or a list of
  lists), and needs only the standard library itself. `requirements.txt` gets what Quarto needs
  to run Python (`ipykernel`, `nbformat`, `nbclient`, `pyyaml`). R and Python `.qmd` files can
  share a project; `octavo env` makes no renv for a project with no R `.qmd`.
- **The analysis environment is set up when the first analysis is added.** In VS Code, adding an
  analysis (or starting a project with one) runs `octavo env` right after, with a progress
  notification. On the command line, `--env` on `octavo init` / `octavo new analysis` does the
  same; `octavo new --json` says `env_needed`.
- **New project is one screen** (where, name, language, what to start with, examples), and a
  folder that is not a project yet gets a **New project** button in the sidebar instead of four
  empty sections. Adding an analysis asks R or Python.
- **The R extension stops asking for `languageserver` in every renv project.** It looks only
  inside the project's renv library, so it asked again in each one. `octavo setup` (and
  `octavo setup --r-editor` on its own) now installs `languageserver` with its dependencies into
  your own R library, and the extension offers once to add that library to the R extension's
  `r.libPaths`. `octavo doctor` shows it as a note.
- **When the octavo command is older than the extension**, adding something or making a project
  now says so and offers Set up, instead of showing the command's raw error.
- Adding the first analysis on a machine without uv offers Set up instead of failing.
- **The extension installs the Quarto, R and Python extensions with it** (an extension pack:
  `quarto.quarto`, `REditorSupport.r`, `ms-python.python`; each can be uninstalled on its own).
- **`AGENTS.md` is the project's working rules**, read by Claude Code, GitHub Copilot, Codex and
  Antigravity alike. `octavo init` writes it, and `CLAUDE.md` becomes one line (`@AGENTS.md`)
  that points Claude Code at it. A project that has only a `CLAUDE.md` keeps getting its
  sections appended there, as before.
- **A lecture's slides, handouts and scripts no longer share a file name**: a session's
  deck is `build/typst-slides/<name>-slides-<session>.pdf` and its script
  `build/typst-notes/<name>-notes-<session>.pdf`; the per-session handout stays
  `build/handouts/<name>-<session>.pdf`. A deck's script outside a lecture is
  `<name>-notes.pdf` (the deck stays `<name>.pdf`). Files under the old names are deleted
  when they are remade. The document names (`octavo build <name>-<session>`) do not change.
- Fixed: on a slide deck, a section heading with text straight under it (so it becomes a
  slide itself) was skipped by the grey running header, which showed the level above
  (the session's title) on that slide and the ones after it.

## 0.5.1

- **The speaker script shows the slides as projected**: each page of the typeset deck,
  shrunk, two to an A4 page, with the notes written on it underneath (`--to typst-notes`
  typesets the deck first).
- **A source or note under a figure or table**: `::: {.figure-note}` + `:::` right after it.
  It stays on the figure's page in small type, takes footnotes and links, and the figure
  shrinks for it on a slide. A footnote in a figure's title no longer breaks the figure.
- **`{.no-title}` on a slide's heading** (or `::: {.slide .no-title}`) gives a slide without
  its title (room for a figure).
- Figures on slides take all the height left: the space kept for the caption is the
  caption's real height, not a fixed three lines.
- **Handout-only / slides-only inside a list item now work**, and so does
  `[a few words]{.handout-only}` inside a line; `.slide-only` is read as `.slides-only`.
  `octavo lint` and `octavo check` point out a `:::` that pandoc will not read as a block
  (no blank line before it) and a `.…-only` mark that matches no output.
- **`[40%]{.no-lint}`** (or `::: {.no-lint}`) keeps a number that is not a result out of the
  hand-typed check; `lint_accepted` also takes the text around a number (`'midterm 40%'`).
- **A `.qmd` can mark itself as run by hand** in its front matter (`octavo:` →
  `manual: true`, `deps: [...]`), so the config's `analysis/*.qmd` can stay; an entry for that
  file in the config wins, and a file matched twice runs once.
- Lecture notes with session markers: a marker with `title="…"` no longer changes which
  heading is a slide (it stays `###`, decided from the whole notes); before, the session's `#`
  stayed in the deck and `##` became the slide.
- Lecture notes with session markers: a session with nothing in it yet gets no deck, and
  decks left from an earlier split are removed at the next build.
- A misspelt setting at the top of a manuscript (`first-section-number`) is reported when
  building; the lecture-notes page now lists each setting's name.
- **Asides (`aside`) are no longer numbered**, like `nb` and `memo`; cases
  and questions keep their shared numbering. To number asides again, add
  `'theorem_envs': {'aside': {'name': {'ja': '余談', 'en': 'Aside'}, 'counter': 'case'}}`
  to `octavo.config.py`.

## 0.5.0

- **Lecture handouts get a layout of their own.** The A4 handout is now set
  from `templates/handout/handout.typ` instead of pandoc's default template:
  the cover on a page of its own, the contents on pages i, ii, …, the body
  from page 1, and Japanese type after the LaTeX class jsarticle (11pt, a
  1.6× line pitch, 1-character paragraph indent, Gothic section heads). The
  body text is set in BIZ UDGothic with Inter. New keys, also settable at the top of the notes:
  `first_section` (`0` numbers a guidance session "0"), `handout_pagebreak`,
  `handout_font` (replaces `typst_mainfont`), `handout_fontsize`, and
  `date_format`; `date: today` prints the day it was built.
- **Session markers.** `::: {.session #third title="…" date="…"}` + `:::`
  marks where a session starts, so a session no longer has to be exactly one
  `#` heading. Its `title` / `subtitle` / `date` go on the session deck's title
  slide, and the deck keeps the handout's numbers. Notes without markers are
  split by `#` as before.
- **`octavo extract`** cuts the handout into one PDF per session
  (`build/handouts/`), keeping the page numbers of the whole
  (`--session`, `--pages 12-19`, `--cover`). In VS Code: "Make the session
  handouts" under lecture notes in the sidebar, and they are remade in the
  background each time notes with session markers are saved
  (`octavo.updateHandoutsOnSave`, on by default; it waits for the preview).
- **Cases, questions and other numbered blocks** in every format:
  `::: {.question #question-why title="…"}` is numbered by section like a
  figure ("Question 2.1"), referred to with `@question-why`, repeated with
  `::: {.restate #question-why}` and listed with `::: {.list-of .question}`.
  Built-in kinds: case, question, aside, nb, memo, theorem, lemma,
  proposition, corollary, definition, example, remark; `theorem_envs` renames
  or adds. `# Title {.appendix}` starts an appendix inside a file. Setting
  `theorem_envs` used to crash the build — fixed.
- **The preview's text can be selected** and its links clicked (contents,
  cross-references; URLs open in the browser), and ☰ lists the bookmarks.
- The table editor opens `data/**/*.csv` too (no heading merges there). New
  projects re-run the analysis when `data/raw/` changes.
- **A page on making lecture notes**, beside the guide on the web page: the
  steps in VS Code, every mark (sessions, slide breaks, handout-only and
  slides-only parts, numbered blocks, URLs and footnotes) with a quick
  reference, and the commands as a footnote.
- Links are black in handouts, slides and scripts (cross-references and
  restated blocks had taken the accent colour); an appendix starts a new page
  of the handout; a restated block no longer prints "(→ p. N)" — its number
  links back to the original.
- **Fixed:** an appendix heading on a session deck read "0.1" when slide
  headings are not numbered.
- **Fixed:** in lecture notes written as `#` session / `##` section / `###`
  slide, `::: {.slide}` made a new section instead of a new slide.
- **Fixed:** a deck (or paper) that cites nothing no longer gets an empty
  References slide or heading.
- **The guide moved to the web page** —
  <https://yoshida-kd.github.io/octavo/guide/> (日本語:
  <https://yoshida-kd.github.io/octavo/ja/guide/>) — and was rewritten for
  users: installation step by step for Linux, macOS and Windows (WSL or not),
  and without the notes meant for Octavo's own development (now in
  CONTRIBUTING.md).
- **Slide breaks and titles from the manuscript**: `::: {.slide}` + `:::` starts a new
  slide, `{.same-slide}` on a heading keeps it on the current slide, and
  `{slide-title="…"}` gives a heading another title on the slide.
- **The form of Japanese works is a choice** (`japanese_citation_form`: `standard`,
  `fullwidth`, `period`), and it and `citations_by_language` are in the sidebar's settings.
- `octavo lint` points out nested list items that are out of line.
- `octavo new analysis` writes a header ready to hand out as one HTML file
  (author, affiliation and email from `meta`, dates, contents, numbered
  sections, `embed-resources`). `octavo.R` gains `ov_palette()`, `ov_tint()`
  and `ov_scale_colour_cud()` / `ov_scale_fill_cud()` for colour-universal
  design.

## 0.4.0

- **A new project layout: what you make by hand, and what gets made.**
  `figures/` is for figures you make yourself (drawn in Typst, photos); what
  the analysis and `octavo build` write now lives under `assets/`:
  `assets/values/` (the numbers behind `{{…}}`, formerly `results/`),
  `assets/figures/` and `assets/tables/`. Manuscripts place figures from
  `assets/figures/`. The config key `results_dir` is now `values_dir`, and
  `figure_src_dir` is new. A project made with an earlier version keeps
  working if its `octavo.config.py` sets `values_dir: 'results'`,
  `figure_dir: 'figures'` and `table_dir: 'tables'`.
- **Figures stay sharp in PDF.** Typst output (papers, handouts, slides,
  scripts) now uses each figure's `.pdf`, as LaTeX does, instead of a PNG, so
  figures no longer blur when zoomed and the text in them can be searched.
  Word keeps the `.png`. Needs Typst 0.14 or newer (`octavo setup` installs
  0.15).
- **Tables you make by hand, edited as tables.** `octavo new table <name>`
  writes `tables/<name>.csv`; `octavo build` turns it into
  `assets/tables/<name>.typ` / `.tex` / `.md`, which the manuscript places
  with a caption line, like the analysis's tables. The layout comes from the
  contents: the first row is the heading, an empty heading cell merges into
  the one on its left (what Excel writes for merged cells), number columns are
  right-aligned and long-text columns wrap. The extension's "Edit as a Table"
  button (on a `.csv` tab) shows it as an editable table (add and move rows
  and columns, paste from Excel); Excel works too. New config key
  `table_src_dir`.
- **Japanese and English works in one bibliography.** In a Japanese document,
  citations and English works now follow the chosen style in English
  ("Smith et al. (2003)", “An Example Article.”), and works marked
  `langid = {japanese}` are written in one Japanese form whatever the style:
  山田太郎・田中花子 (2020)「…」『…』12(3): 1–20. Names in a citation are joined
  with ・ and "et al." becomes ほか. Before, the whole bibliography used the
  Japanese locale, giving "Smith ほか (2003年)". `citations_by_language: False`
  keeps the old behaviour.
- Fixed: adding a figure drawn in Typst from the extension tried to open a file
  under `assets/figures/` instead of `figures/<name>.typ`.
- The extension's snippets follow the current syntax (labels instead of typed
  numbers).
- **The web page opens in Japanese for Japanese browsers**: the English page
  moves to the Japanese one when the browser's first language is Japanese. A
  language picked with the link at the top is remembered in the browser and
  followed from then on; nothing is sent anywhere.
- The wording of the Japanese and English documentation, the web page, the
  templates and the Japanese messages was reviewed. "Markdown" is now written
  the same way everywhere, and the guide's chapter 1 is called "インストール".
- Fixed: the example analysis wrote `N = 1523` in a table note while the text
  said `1,523`; the messages about placeholder values no longer say they were
  written by `octavo init` (an example added with `octavo new --example` writes
  them too).

## 0.3.1

- **Figures drawn in Typst, where TikZ used to be.** `octavo new figure dag`
  writes `figures/dag.typ` with a small `diagram()` helper (boxes, and arrows
  from edge to edge; no packages), and `octavo build` turns it into
  `figures/dag.pdf` and `.png` whenever the `.typ` is newer. The manuscript
  places it like any figure (`![…](../../figures/dag.png){#fig-dag}`), so it
  appears in every format, is numbered and can be referred to. Parts shared
  between figures go in `figures/_parts.typ`. A `.typ` with an error stops the
  build; `octavo check` and `octavo release` notice a figure not drawn since
  its `.typ` changed. In the extension: **Add a figure drawn in Typst** in the
  sidebar, and saving a `.typ` rebuilds the preview.
- Fixed: code inside a fenced block (for instance `#import "@preview/…"` in a
  `` ```{=typst} `` block) was counted as a citation by `octavo checkbib` and
  `octavo check`.
- A web page: https://yoshida-kd.github.io/octavo/

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
  `setup.sh` in a terminal: pandoc, Typst, Quarto, fonts, R (the latest from
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
