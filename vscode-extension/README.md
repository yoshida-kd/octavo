# Octavo for VS Code

**The quantitative social science starter pack**

[日本語版 README はこちら / Japanese README](README.ja.md)

Write a paper, a conference deck or a course handout in **one Markdown file**
and see the typeset PDF beside it, rebuilt on every save. This extension is
the editor side of [Octavo](https://github.com/yoshida-kd/octavo), a
command-line tool that turns one Markdown source into Typst (papers,
handouts, slides), Word, and — if you have TeX — LaTeX and Beamer, with
.bib/CSL citations and the numbers, figures and tables pulled straight
from your Quarto analysis instead of typed by hand.

![A paper page and a slide built by Octavo from its example project](https://raw.githubusercontent.com/yoshida-kd/octavo/main/docs/images/showcase-en.png)

- **Live PDF preview** — the manuscript on the left, the PDF on the right,
  rebuilt on every save and scrolled to where your cursor is. Lecture notes get a third column: the slide deck (or the speaker script)
  for the session the cursor is in.
- **Octavo in the activity bar** — your manuscripts (each with its own
  settings), the analysis, and the tools in the order you use them.
- **Citations** — `@key` completion and hover from your `.bib`, and a
  squiggle under every key that doesn't exist.
- **Analysis values** — completion, hover and diagnostics for the
  `{{name}}` placeholders your analysis fills in.

## Requirements

Linux, macOS, WSL2 (Ubuntu) or a server reached through Remote-SSH (on macOS,
install [Homebrew](https://brew.sh) first). **That is all you need to have:**
the first time the extension starts, it checks what is installed and, if
anything is missing, offers **Set up**. That runs the setup script it carries in
a terminal, asks for your password once (sudo), and installs pandoc, Typst,
Quarto, the fonts, R (the latest from CRAN), renv, [uv](https://docs.astral.sh/uv/)
and the `octavo` command. Over Remote-SSH or in a WSL window it installs on
that machine. Close the terminal when it is done, and the extension checks
again.

Run it again any time from the sidebar (**Tools → Install or Update the
Tools**) or the command palette (**Octavo: Install or Update the Tools**) — for
example after updating the extension, so the `octavo` command follows. TeX is
not installed; only the LaTeX and Beamer outputs need it (`octavo setup
--with-tex` from a terminal). See the
[Octavo guide](https://yoshida-kd.github.io/octavo/guide/#1-install) for the full
picture, including installing from a terminal.

## Getting started

1. In a folder that is not a project yet the sidebar offers **New project**
   (also: command palette → **Octavo: New Project (init)**). One screen asks
   where, the name, the language, and what to start with — an analysis (in R
   or Python), a paper, slides, lecture notes, any of them or none — and
   whether they are **examples** to look at first or **empty**, holding only
   what you keep using. With an analysis chosen, its environment (`.venv`, and
   renv for R) is set up right after.
2. Add more from the Octavo sidebar: **Add a manuscript…** (a paper, a slide
   deck or lecture notes, opened as soon as it is made) and **Add an analysis
   (.qmd)…** (R or Python; the first one sets the environment up too), and on a paper **Add an appendix** / right-click **Add main.tex
   (LaTeX)**. With an analysis, **Tools → Set Up This Project's Analysis
   Environment** makes its `.venv` (uv) and renv.
3. Open the manuscript and click the PDF icon in the editor title bar
   (**Octavo: Open the Live Preview**). Save, and the PDF follows.

The extension switches itself on in any workspace that has an
`octavo.config.py`. A workspace may hold several projects: the extension uses
the one the file you are editing belongs to.

## Features

- **Command palette** (`Octavo:`) for `build`, `watch`, `check`,
  `checkbib`, `doctor`, `selftest`, `init`, `new`, `analysis run`, `env` and
  `setup`.
- **Setup.** Checks the tools on first start (`octavo doctor --json`) and
  offers to install what is missing; the setup script is bundled, so the
  extension is the only thing you install by hand. The per-project analysis
  environment (`.venv` with uv, renv with knitr and rmarkdown) is one click too.
- **Sidebar**, top to bottom: **Manuscripts** (click to open; PDF and build
  buttons on each; lecture notes list their sessions; a paper shows its
  appendix or a button to add one; **Settings for this document** — citation
  style, output formats, slide look or submission limits, written at the top
  of that manuscript), **Analysis** (each `.qmd` and whether it is stale),
  **Tools** in the order you use them (install → diagnose → analysis
  environment → run the analysis → check the bibliography → check before
  submitting), and **Settings**, the project's defaults, folded away. The
  citation style is picked from a list (or typed), output formats are ticked.
  A change goes through `octavo config set`, which rewrites just that one line
  (of the manuscript, or of `octavo.config.py`, keeping its comment) and
  refuses a value the config would reject.
- **Live preview.** Rebuilds on save, keeps your scroll position across
  rebuilds, and shows build errors in the panel rather than swallowing them.
  "Preview: What Goes in the Third Column…" switches lecture notes between
  the deck, the speaker script and a plain two-column layout. Text can be
  selected and copied, links (contents, cross-references, URLs) work — a URL
  opens in your browser — and ☰ lists the PDF's bookmarks. The PDF is
  drawn by a bundled copy of [pdf.js]; nothing is fetched at runtime.
- **Handouts per session.** For lecture notes with session markers, "Make the
  session handouts" under the notes in the sidebar cuts the A4 handout into one
  PDF per session in `build/handouts/` (`octavo extract`), keeping the page
  numbers of the whole. They are remade in the background each time the notes
  are saved (setting `octavo.updateHandoutsOnSave`).
- **Analysis (Quarto).** The sidebar's Analysis section shows each `.qmd` as up
  to date, stale or manual, with a run button; an open `.qmd` gets a run button
  in the editor's title bar. The preview never runs the analysis itself: a bar
  above the PDF says when something is stale, and its button runs it and
  rebuilds. Progress shows in a notification and Quarto's output in the Output
  panel, so no terminal is needed. For writing the `.qmd` itself (chunk
  highlighting, running chunks one by one), the official Quarto, R and Python
  extensions are installed with Octavo (an extension pack — each can be
  uninstalled on its own).
- **Follows the cursor.** Moving the cursor in a manuscript scrolls the PDF preview to the same place; the preview can still be scrolled on its own, and the ⇅ button (or `octavo.previewFollowCursor`) turns the following off.
- **A `.qmd` shows its HTML.** Opening one in an Octavo project shows the HTML it last rendered beside it, and reloads when the analysis runs again (`octavo.qmdPreview` turns it off). Nothing is rendered by opening or saving.
- **Citations.** Completion on `@` (with author and year), hover for the
  full entry (also on `\poscite{key}`), `Ctrl+Alt+@` to search and insert,
  squiggles on missing keys, and `.bib`-side problems (missing year, an
  organisation split into given/family name, duplicates) shown on the `.bib`.
- **Typst file preview.** With a `.typ` file open, "Preview This Typst File"
  runs `typst watch` on it directly — handy for a paper's hand-maintained
  `main.typ`.
- **Tables made by hand.** The **Edit as a Table** button on a `.csv` tab (and
  every table added from the sidebar) shows it as a table: type into
  the cells, add or move rows and columns, Enter for the next row, Alt+Enter
  for a line break in a cell, paste a range copied from Excel. Leave a heading
  cell empty to merge it into the one on its left. `octavo build` turns it into
  the table the manuscript's `: Caption {#tbl-<name>}` line places. "Edit as
  text" gets the plain CSV back. Data you type in by hand (`data/**/*.csv`)
  opens the same way; there the first row is just the column names.
- **Snippets** for tables, figures, possessive citations and conditional
  blocks (`ptable`, `pfigure`, `pposcite`, `phandout`, `pslides`, `pnotes`, …).
- **English and Japanese**, following VS Code's display language — and the
  extension passes the same language on to the `octavo` command.

All the checking is done by the `octavo` command itself (`octavo checkbib
--json` and friends); the extension only displays the result, so what it
underlines can never disagree with what the command says.

## macOS and Windows

Octavo runs on Linux and macOS (the extension calls `octavo`, and looks in
`~/.local/bin` — where the setup puts it — even when that is not on VS Code's
`PATH`; an `octavo` kept elsewhere can be named in full in `octavo.command`).
Development and testing put Linux first, then macOS, then Windows. Octavo works on
Windows too, and WSL is recommended there (as in the guide). With VS Code on Windows:

1. **Open the folder through Remote-WSL** (recommended). The extension then
   runs inside WSL and everything is the Linux path.
2. **Open a Windows folder, with WSL installed.** The extension runs `octavo`
   through `wsl.exe` (`octavo.executionMode: "auto"` picks this when WSL has a
   distribution), translating paths (`C:\Users\you\proj` ⇄
   `/mnt/c/Users/you/proj`). **Set up** installs into WSL.
3. **Directly on Windows, no WSL.** `auto` picks this when WSL has no
   distribution (or set `octavo.executionMode` to `"local"`). **Set up** then
   runs the bundled `setup.ps1`: winget installs pandoc, Typst, Quarto and R,
   BIZ UD and Inter go into your user fonts, and uv installs `octavo`. Windows
   may ask for permission for some installers. The extension's terminals are
   PowerShell. TeX is not installed on Windows.

## Settings

| Key | Default | Meaning |
|---|---|---|
| `octavo.executionMode` | `"auto"` | `"local"` \| `"wsl"` \| `"auto"` |
| `octavo.wslDistro` | `""` | passed as `wsl.exe -d <name>`; empty uses the default distro (`wsl -l -v` lists them) |
| `octavo.command` | `"octavo"` | the command to run (a full path works too) |
| `octavo.configPath` | `""` | point explicitly at `octavo.config.py` |
| `octavo.diagnosticsOnSave` | `true` | run `checkbib` on every save to update squiggles |
| `octavo.defaultTargets` | `[]` | formats for "Build…" without prompting each time |
| `octavo.previewLectureColumn` | `"slides"` | the third preview column for lecture notes: `"slides"`, `"notes"` (the speaker script) or `"none"` |
| `octavo.typstCommand` | `"typst"` | the command run by "Preview This Typst File" |
| `octavo.typstAutoOpenPdf` | `true` | open the `.pdf` when the Typst file preview starts (via [LaTeX Workshop] if installed) |

Settings of the *project* — citation style, slide look, submission limits —
live in `octavo.config.py` and are editable from the sidebar.

## Tasks

The extension registers a `$octavo` problem matcher:

```jsonc
{
  "label": "octavo build",
  "type": "shell",
  "command": "octavo build --to typst,docx",
  "problemMatcher": ["$octavo"]
}
```

## Known limitations

- Squiggles apply to open Markdown documents, and to a `.bib` the extension
  host can read. With VS Code on Windows going through `wsl.exe`, a `.bib`
  under the WSL home (outside `/mnt/`) gets no squiggles of its own — keep it
  inside the project, or use Remote-WSL.
- `checkbib` runs as a fresh process on every save; with a `.bib` of
  thousands of entries that can take a noticeable moment. Turn
  `octavo.diagnosticsOnSave` off and run "Check the Bibliography" by hand if
  so.
- The same Windows-through-`wsl.exe` setup reads a PDF outside `/mnt/`
  through `base64`, which is slower for a long document. Remote-WSL avoids it.
- The Typst file preview opens the PDF through LaTeX Workshop's
  `latex-workshop-pdf-hook` editor, which is not a public API. If a future
  release of that extension changes it, only the auto-open stops; `typst
  watch` keeps running.

## Building from source

```bash
git clone https://github.com/yoshida-kd/octavo.git
cd octavo/vscode-extension
npm ci
npx @vscode/vsce package    # -> octavo-<version>.vsix
```

Install the `.vsix` from the Extensions view (`…` → "Install from VSIX…"),
or open `vscode-extension/` in VS Code and press `F5` to run it in an
Extension Development Host.

## License

MIT

[pdf.js]: https://mozilla.github.io/pdf.js/
[LaTeX Workshop]: https://marketplace.visualstudio.com/items?itemName=James-Yu.latex-workshop
