# Changelog

Octavo's command-line tool (`octavo-kit` on PyPI) and this extension are
released together, under one version number.

## 0.6.8

- **Less scattered project folders.** A new project keeps its bibliography in `literature/literature.bib`
  (`bib_file` in `octavo.config.py`), next to `literature/priorwork/` where Priorwork delivers — one
  folder for everything about the literature. A project from before keeps `literature.bib` at its root
  and nothing changes for it (move it and edit `bib_file` if you like). Writing rules and the phrase bank
  go in `notes/writing/rules/` and `notes/writing/phrases/`; an older `writing/` folder is read too, and
  a file of the same name in `notes/writing/` wins.
- **Lecture notes: the appendix comes after the references, and is a PDF of its own.** A heading
  with `{.appendix}` used to put the appendix between the text and the references, with the
  page numbers running on. Now the handout is text, references, appendix; the appendix's pages
  are numbered A-1, A-2, … from 1, and it is also made as `<name>-appendix.pdf` (the handout and
  the per-session handouts leave it out). Papers number the appendix's pages A-1, … too, whether it
  is a PDF of its own or follows the text. To go back: `appendix_separate: false` keeps it in one
  PDF, `appendix_after_references: false` restores the old order (text, appendix, references).
- **`lang` per document.** Write `lang: en` at the top of a manuscript and that document is typeset
  in English (references read "Section 2", "Table A1"; the citation locale, the reference list's
  heading and the LaTeX class follow) in a Japanese project, or the other way round.
  `reference-section-title:` and `csl_locale:` work at the top of a manuscript too.
  `octavo new paper <name> --lang en` starts from the English templates (and writes `lang:`);
  adding `--appendix` or `--tex` later follows the manuscript's own `lang`.
- **`octavo fmt`** puts manuscripts one sentence to a line: it joins lines broken in the middle of a
  sentence and breaks a Japanese line after each 。 (never inside 「」 or （）, code, tables, math
  or comments). It shows the changes; `--apply` writes them (git clean, or `--allow-dirty`).
  `octavo check lint` lists the lines broken mid-sentence.
- **Tables from the analysis**: `ov_table()` takes `groups` (a bold heading row across the columns,
  rows under it indented), `indent` and `size` (points); the note is left-aligned; the table no
  longer inherits the body's justified text; an empty column heading is written `[]` instead of
  `[**]` (Typst warned "no text within stars" for every table).
- **Slides count figures and tables straight through** when their sections show no number (a deck
  with `slides_numbering` unset) unless the document also makes the handout, whose numbers the deck
  follows. `crossref_numbering: 'section'` brings the old numbers back. A figure or table with
  neither a caption nor a label is no longer counted.
- **A failed Typst build shows the `error:` first**, not the end of the output (where warnings
  about fonts of other systems could hide it).
- An empty abstract (nothing, or only a comment) no longer prints the "Abstract" heading.
- **`octavo data track data/raw/<file>`** lets git take a file under `data/` (it adds the `!` lines
  to `.gitignore`).
- **Sidebar, From Priorwork**: shown whenever the project is connected (a workspace or a Zotero
  collection is set), with rows for the Priorwork workspace, the main and linked Zotero
  collections and the Zotero key, and each survey saying which collection joins it to the project
  (main, linked or not yet).

- **A paper's title, authors, affiliation, e-mail and date come from the top of the manuscript**
  (`title:`, `author:`, `institute:`, `email:`, `date:`) instead of being written again in
  `main.typ`; `--anonymous` leaves out the authors, affiliation and e-mail. A `main.typ` made by
  0.6.7 that still names them keeps working (what it writes wins); one that shows the placeholders
  ("Title of the Paper") should lose those lines — or be remade: rename it and
  `octavo new paper <name>`.

## 0.6.7

- **A main Zotero collection and linked ones.** `zotero_collection` is the project's main collection
  (what goes into `literature.bib`); the new `zotero_linked` names collections that only feed it —
  one per literature survey, say — and never go into the `.bib`. Both are chosen from the sidebar.
- **`octavo bib tidy` keeps the main collection to what the manuscripts cite.** It lists the papers
  cited but not in the main collection (and the linked collection each is in — or, for one in none of
  them, where it is in the whole library) and those in it that nothing cites. With `--apply` — and only when the project sets `'zotero_write': True` — it adds and
  takes out entries through the Zotero web API (the key needs write access). It changes only which
  collections an entry is in, never deletes or edits one, and never takes out an entry whose citation
  key is not pinned. In the sidebar: **Tidy the Main Zotero Collection**, with the plan to untick.
- **`[-@key]` citations are counted** by `octavo checkbib` / `check` and the editor's diagnostics.
  A citation that leaves out the author's name was missed, so a missing key there went unreported.
- The request copied for Priorwork now asks for each survey's own collection, to be linked.
- **Papers number straight through**: Figure 1, Table 2, Equation (3), and A1, A2, … in the
  appendix. Lecture notes, slides and posters keep numbering by section (Figure 2.1). A paper
  that should keep the old numbers: `crossref_numbering: 'section'` in `octavo.config.py` or at
  the top of the manuscript.
- **A paper's appendix is its own PDF** (`build/pdf/<name>-appendix.pdf`), typeset whenever there
  is an `appendix.md` (no `--appendix` needed); references between the two are written as
  numbers. `appendix_separate: false` puts it after the text instead.
- **A paper is laid out after LaTeX**: jsarticle for Japanese, article (11pt) for English — the
  page, headings, title block and abstract — and page 1 shows its length (characters or words,
  without and with notes, the abstract's, the figures and tables). The layout is `article.typ`,
  written by `octavo build` every time; a new paper's `main.typ` holds only its title and authors.
  A paper made before keeps its `main.typ` and looks as before; `octavo template diff
  paper/ja/main.typ` (or `en`) shows the new one.
- **Reference lists read better** in papers, handouts and slides: a hanging indent, no stretched
  spaces, a little room between entries, and English quotation marks in a Latin face in a
  Japanese document. On slides the list is in small type.
- **`slides_bibliography` for every deck, per document**: `slide`, `off`, `sheet` (an A4 PDF of
  the deck's references beside it) or `both`. Lecture decks still get the slide and talks none by
  default; `true` / `false` keep working.
- **Slides to hand out** (`slides-handout` in `outputs:`): the same deck without what is marked
  `.screen-only` and with what is marked `.no-screen`, in `build/slides-handout/`.
- **R packages for a `.qmd` run from Quarto's Preview**: in VS Code, opening or saving an R
  `.qmd` checks for packages it uses that are not installed and offers to install them
  (`octavo analysis missing|install <qmd>`; `octavo.checkRPackages` turns it off).
- **Writing rules and a phrase bank for your AI assistant**: Markdown files in `writing/rules/`
  and `writing/phrases/` (or `~/.config/octavo/writing/`), listed by `octavo writing`; the
  project's `AGENTS.md` asks the assistant to follow them.
- The project rules ask the AI assistant to write one sentence per line (and the example
  manuscripts do); `octavo migrate --rules` brings an existing project's AGENTS.md up to date.
- `nocite:` at the top of a manuscript now reaches the bibliography (it was dropped).
- **Writing from Priorwork arrives in `literature/priorwork/`** (the text and a manifest). `octavo
  priorwork` lists it, `octavo priorwork resolve` replaces `@PRIORWORK:<DOI>` with the `.bib` key
  once the paper is in Zotero and pulled, and `octavo priorwork link` adds the survey's Zotero
  collection to `zotero_linked`. The sidebar's **From Priorwork** does the same and copies a request
  for your AI assistant; the project's `AGENTS.md` says how to bring the writing into the manuscript
  (propose, wait for the answer, keep the citations, never edit the inbox). `octavo check cites`
  lists Priorwork's marks apart from other missing keys, and `@{…}` citation keys are now counted.
- **Priorwork's cards on `[@key]`**: resting the cursor on a citation shows the paper's card from
  the surveys that included it (question, findings, and whether it was checked in the full text);
  `octavo check cites` notes cited papers not read in full.
- **Requests to Priorwork without the clipboard**: with `octavo.priorworkWorkspace` set, **Ask
  Priorwork for the Literature** writes the request into the Priorwork workspace
  (`.priorwork/requests/`), and **From Priorwork** shows whether it was received, done or declined
  (`octavo priorwork ask|requests`).

## 0.6.6

- **The `.qmd` HTML view follows the cursor**, like the PDF preview: it looks for the start of the
  line you are on (a line of code inside a chunk, or the text of a paragraph or heading) in the
  rendered page and scrolls there, falling back to the heading above. Code folded closed by
  Quarto is skipped, and the page does not move when the spot is already in view. The setting is
  the same `octavo.previewFollowCursor`.
- **Search the text of the preview and of a `.qmd`'s HTML view.** Click in the view and press
  Ctrl+F (Cmd+F on a Mac): VS Code's find box opens for the PDF's text (every page) and for the
  analysis's HTML. Before, neither view could be searched.
- **R packages that need compiling now install on a plain Ubuntu / WSL.** When R's package
  source is not set, Octavo used to take CRAN's own server, which on Linux hands out source only
  (quanteda, igraph and the like need a compiler and development libraries, which a fresh WSL
  Ubuntu lacks), so `octavo env` and the automatic install for a failing `.qmd` stopped with
  "could not install". It now takes Posit Package Manager on Linux (ready-made packages; renv
  turns the URL into the one for your Ubuntu, and `renv.lock` keeps a URL that works on a Mac too)
  and falls back to CRAN's cloud mirror when that is unreachable or the system is not Linux. A
  source you have set yourself is left alone.
- **`octavo doctor`** says, on Linux, when R's package source is one that compiles everything,
  with the line to put in `~/.Rprofile`.
- When an R package cannot be installed, Octavo no longer says only "not on CRAN?": on Linux it
  points at compiling (ready-made packages from Posit Package Manager, or
  `sudo apt install build-essential gfortran libglpk-dev libxml2-dev`) and shows the end of R's
  output.

## 0.6.5

- **A quick guide** (`/quickstart/`, `/ja/quickstart/` on the web page): install, make a
  project, write, build, check and the AI assistants, in one short page with the terminal
  steps folded. The web page's top is simpler (a short lead, a one-line install band, the
  diagram and the sample, the features), and its home links to the quick guide.
- On Linux, `octavo setup` no longer installs the system `python3`: uv brings the Python that
  `octavo` and a project's `.venv` use (checked with no system Python on the path:
  `uv tool install`, `octavo env` and a Python analysis through Quarto all work).
- The Japanese guides' footer is Japanese, and a settings table in the lecture-notes guide
  that had been split across two lines is whole again.
- **The Zotero collection is a setting.** `zotero_collection` in `octavo.config.py` names
  the collection `octavo bib pull` fetches the `.bib` from, so it is no longer typed each
  time (`--collection` still overrides it). **Choose the Zotero Collection** in the sidebar
  picks it from Zotero's collections (`octavo bib collections --json`), with a way to reload
  after making one in Zotero, or to type the name when Zotero is not running there.
- **Ask Priorwork for the literature.** Right-click a paper in the sidebar → **Ask Priorwork
  for the Literature** copies a request, with the manuscript's path and the Zotero
  collection, to paste into the agent's chat in your Priorwork workspace. Priorwork reads
  the manuscript and writes the draft of the literature review with `[@key]` citations from
  the project's `.bib`.
- **Zotero's collections are a tree.** `zotero_collection` takes a path (`'Research / Make
  or buy'`; a name alone still works when it is used once), `octavo bib pull` also fetches
  the collections under it (one `.bib`, each entry once), and the sidebar's list is shaped
  like Zotero's. So several Priorwork surveys for one paper can each use a collection under
  the project's.
- **Several collections, and the Zotero web API.** `zotero_collection` can be a list, so a
  survey on a topic can serve several papers (and a paper several surveys); the sidebar's
  picker lets you check any number of collections. Where Zotero does not run (a server over
  SSH), `octavo bib pull` and the picker read the Zotero web API: `octavo bib login` (or
  **Use the Zotero Web API (API Key)…**) keeps the key in `~/.config/octavo/zotero.env`, and
  the citation keys come from Better BibTeX's pinned keys.
- **Choosing collections goes folder by folder**: only the top folders are listed, choosing one
  opens it, and you mark the collections to use (with "Up", "Mark this folder" and a search over
  all folders). **Ask Priorwork for the Literature** can also ask to use surveys already in
  Priorwork for the paper.

## 0.6.4

- **R packages a `.qmd` uses are installed for you**, including a `.qmd` brought in from
  elsewhere: `octavo env` now installs every package the project's `library(x)` / `x::f()`
  use that is missing (before, only the first `octavo env` did, through `renv::init()`), and when
  an R `.qmd` fails while running, Octavo installs what it uses and is missing and runs it once
  more. Both record the additions in `renv.lock`. A package not on CRAN is named, with the
  command to install it yourself.
- **Projects with only `.qmd` files.** For a report or an assignment written entirely in
  Quarto, the `.qmd`'s output (beside it, as always) is the result. With no manuscript,
  `octavo check` and `octavo build` no longer fail as long as there is a `.qmd`.
- The New project form in VS Code listed pre-`docs/` paths; fixed.
- Fixed: Quarto's `analysis/.quarto/` folder went into git (the ignore line only matched the
  project's top folder), and the replication package carried Quarto's `<name>_files/` and the
  HTML beside each `.qmd`. Projects made before keep their `.gitignore`: change `/.quarto/` to
  `.quarto/` there by hand.

## 0.6.3

- **Whether an analysis is out of date is decided by its contents.** Switching git branches
  and back, a pull or a fresh clone no longer makes an unchanged `.qmd` stale.
  `octavo analysis mark-fresh <qmd>` records one as up to date without running it (for a
  `.qmd` that fetches raw data and must not run twice). The guide shows how such a `.qmd`
  ends as a success when the data is already there (`knitr::knit_exit()`).
- The preview's "out of date" bar can be hidden until something else changes, has
  **Mark as up to date**, and says differently when only a manually run analysis changed.
- **The preview follows changes made on disk** — by an AI assistant or another tool — not only
  saves in the editor, and an editor without unsaved edits is reloaded from disk; if the
  manuscript also has unsaved edits, it says so and offers to compare or to load the file on
  disk. The rules `octavo init` writes ask AI assistants to edit
  manuscripts through the editor, not by rewriting the file from the shell.
- **A slide that does not fit goes on over a slide titled "Title (cont.)"** instead of an
  untitled page, and `octavo build` says so (a `\newslide` chooses where it breaks). Slides that
  fit are not touched; an untitled slide that does not fit is reported.
- **`octavo migrate --syntax`** rewrites the older notation (`::: {.session}`, `::: {.slide}`,
  `.handout-only`) into `\session{…}`, `\newslide` and `.no-slides`, keeping the rewrite only if
  every output stays the same. **`octavo migrate --rules`** brings Octavo's sections of
  `AGENTS.md` up to date and shows the difference.
- `\newslide` under a `#` heading that is itself a slide continues its title
  ("Title (cont.)"); with no title to continue it makes an untitled slide rather than one titled
  "(cont.)" alone.
- An empty list item (`- `) right under a heading no longer turns the heading into
  "### Title" one level up (pandoc read the `-` as the heading's underline).
- The A4 handout has space above and below figures and tables, and between a figure and its
  caption (jsarticle's `\intextsep` and `\abovecaptionskip`).
- `octavo check` knows the output names (`.pdf-only`, `.word-only`, …), and no longer says a
  block right after `\newslide`, `\session{…}` or `\newpage` is not read as a block.
- `octavo migrate --allow-dirty` goes ahead with uncommitted changes; without it, the message
  says what to run next.
- **"Handout only" is written `.no-slides`** in the guide, the examples, the snippet and the rules
  `octavo new` adds (it shows in the PDF, Word and LaTeX); `.pdf-only` is for the PDF alone. The
  older `.handout-only` still works and means the same in lecture notes. The rules also say which
  heading level makes a slide.

## 0.6.2

- **One kind of document: what it makes is chosen at its top.** A manuscript lives in
  `docs/<name>/<name>.md` and says what to make with `outputs:` — `pdf`, `word`, `tex`,
  `slides`, `beamer`, `script` (`pdf` when not written). The PDF's layout is the `main.typ`
  beside the manuscript if there is one (a paper), otherwise Octavo's built-in one (the A4
  handout). `sessions: true` marks a manuscript made of class sessions (one deck each; a
  manuscript with `::: {.session}` markers is one without saying so). `octavo new paper|slides|lecture`
  are templates that write these lines. `--to` takes the output names too.
- **Older projects keep working unchanged** (`papers/`, `slides/`, `lectures/`, `targets:`,
  `profile`, `split_slides`). `octavo migrate --docs` moves their manuscripts into `docs/`
  (figure paths, front matter and the config included; `--dry-run` to look first), and
  `octavo check` says when there is something to move.
- **`\newpage`** on a line of its own is a page break in the PDF, Word and LaTeX;
  **`\newslide`**, `\newslide{Title}` and `\newslide{}` break slides (the older
  `::: {.slide}` still works).
- **Settings renamed after the outputs**: `typst_slides_*` → `slides_*`,
  `handout_font` / `handout_fontsize` / `handout_pagebreak` → `font` / `fontsize` /
  `pagebreak`. The old names are still read, in the config and at the top of a manuscript; the
  sidebar rewrites such a line under the new name when you change it.
- `toc` (table of contents) can be set per document; in the built-in layout it is on for a
  manuscript made of sessions and off otherwise. A document without sessions in the built-in
  layout sets its abstract at the top of the text.
- `.pdf-only`, `.word-only` and the other output names work in conditional blocks
  (`.handout-only` and `.paper-only` still do).
- In a `docs/` manuscript every `#` heading is a section — the title goes in the front matter
  (`title:`). The paper templates now start their sections at `#`, like lecture notes; papers
  written from `##` build the same.
- **`build/` is arranged by output**: `build/pdf/`, `build/slides/`, `build/script/`,
  `build/word/`, `build/tex/`, `build/beamer/` (and `build/handouts/` as before) instead of
  `typst/`, `typst-slides/`, `typst-notes/`, `latex/`, `slides/` (which held Beamer). A paper's
  PDF is also copied to `build/pdf/<name>.pdf` beside its `main.pdf`. Delete `build/` once to drop
  the old folders; `out_dirs` in the config takes either kind of name.
- **Posters** (`outputs: [poster]`, `octavo new poster <name>`): A0 portrait by default
  (`poster_size` a0/a1/a2/b0/b1 or any size, `poster_orientation`), and each top-level heading is
  a cell in a 2×3 grid (`poster_grid`, `poster_rows`); `{span=2}`, `{rows=2}` and `{cell="2,3"}`
  join and place cells. The title band carries the title, authors, affiliation, event and date,
  logos (`logo:`) and a QR code made from a URL (`qr:`). Figures fit their cell, the bibliography
  is the last cell, and a cell whose content does not fit is reported after the build (and
  marked in red on the PDF).
- **Only the marked parts on the slides or the poster**: with `slides_select: marked` (or
  `poster_select: marked`) at the top of a manuscript, the slides get only what is marked
  `.on-slides` — a `::: {.on-slides}` block, a section whose heading has `{.on-slides}`, or
  `[…]{.on-slides}` in a line — plus the headings above it; the rest stays in the handout. A
  reference to something left out is written as its handout number, and a session with nothing
  marked gets no deck. `.on-poster` does the same for a poster made from a paper.
- **A lecture deck keeps the handout's numbers.** Figures, tables, equations and numbered blocks
  on the slides (and in the speaker script) carry the number they have in the handout, even when
  some figures are in the handout only (`.pdf-only`) or were not picked for the slides — before,
  the deck counted only what it had, so its numbers could drift from the handout's.
- **The preview closes with its manuscript**: closing the last tab of the manuscript (and of its
  appendix) closes the PDF preview beside it. The setting `octavo.previewCloseWithManuscript` turns
  this off.
- **Commands tidied** (the old ones all still work): `octavo check values|cites|lint` runs one
  of the checks (`octavo values`, `checkbib`, `lint`); `octavo build <notes> --sessions` also
  cuts the per-session handouts (`octavo extract` stays for picking sessions or pages);
  `octavo template copy word` writes `templates/word/reference.docx`, which Word output then
  uses (`octavo reference-docx` still works); `octavo env` says what it sets up (the project's
  R and Python packages).
- **A session marker on one line**: `\session{Title} {#id date="…" subtitle="…" author="…"
  institute="…"}`, everything optional — the same as `::: {.session …}` + `:::`, which still works.
- `octavo extract`'s and a missing session's messages showed `{{…}}` with doubled braces.
- The sidebar's settings for a document offer *What to make*, *Made of sessions* and *Table of
  contents*.

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
