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

- **Live PDF preview** — the manuscript on the left, the PDF on the right.
  Lecture notes get a third column: the slide deck (or the speaker script)
  for the session the cursor is in.
- **Octavo in the activity bar** — your manuscripts, the common settings and
  the usual checks in one sidebar.
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
quarto, the fonts, R (the latest from CRAN), renv, [uv](https://docs.astral.sh/uv/)
and the `octavo` command. Over Remote-SSH or in a WSL window it installs on
that machine. Close the terminal when it is done, and the extension checks
again.

Run it again any time from the sidebar (**Tools → Install or Update the
Tools**) or the command palette (**Octavo: Install or Update the Tools**) — for
example after updating the extension, so the `octavo` command follows. TeX is
not installed; only the LaTeX and Beamer outputs need it (`octavo setup
--with-tex` from a terminal). See the
[Octavo README](https://github.com/yoshida-kd/octavo#readme) for the full
picture, including installing from a terminal.

## Getting started

1. Command palette → **Octavo: New Project (init)**, and open the folder it
   makes.
2. **Octavo: Add a Manuscript (new)** — a paper, a slide deck or lecture
   notes. If the project has an analysis, **Tools → Set Up This Project's
   Analysis Environment** in the sidebar makes its `.venv` (uv) and renv.
3. Open the manuscript and click the PDF icon in the editor title bar
   (**Octavo: Open the Live Preview**). Save, and the PDF follows.

The extension switches itself on in any workspace that has a
`octavo.config.py`.

## Features

- **Command palette** (`Octavo:`) for `build`, `watch`, `check`,
  `checkbib`, `doctor`, `selftest`, `init`, `new`, `analysis run`, `env` and
  `setup`.
- **Setup.** Checks the tools on first start (`octavo doctor --json`) and
  offers to install what is missing; the setup script is bundled, so the
  extension is the only thing you install by hand. The per-project analysis
  environment (`.venv` with uv, renv with knitr and rmarkdown) is one click too.
- **Sidebar.** Manuscripts (click to open; PDF and build buttons on each;
  lecture notes list their sessions and jump to them), settings (language,
  citation style, slide aspect / accent colour / running header / divider
  slides / heading numbers, submission limits — click one to change it), and
  tools. A setting is changed by `octavo config set`, which rewrites just
  that line of `octavo.config.py`, keeps its comment, and refuses a value the
  config would reject.
- **Live preview.** Rebuilds on save, keeps your scroll position across
  rebuilds, and shows build errors in the panel rather than swallowing them.
  "Preview: What Goes in the Third Column…" switches lecture notes between
  the deck, the speaker script and a plain two-column layout. The PDF is
  drawn by a bundled copy of [pdf.js]; nothing is fetched at runtime.
- **Analysis (Quarto).** The sidebar's Analysis section shows each `.qmd` as up
  to date, stale or manual, with a run button; an open `.qmd` gets a run button
  in the editor's title bar. The preview never runs the analysis itself: a bar
  above the PDF says when something is stale, and its button runs it and
  rebuilds. Progress shows in a notification and quarto's output in the Output
  panel, so no terminal is needed. For writing the `.qmd` itself (R chunk
  highlighting, running chunks one by one), add the official Quarto extension
  (`quarto.quarto`) alongside.
- **Citations.** Completion on `@` (with author and year), hover for the
  full entry (also on `\poscite{key}`), `Ctrl+Alt+@` to search and insert,
  squiggles on missing keys, and `.bib`-side problems (missing year, an
  organisation split into given/family name, duplicates) shown on the `.bib`.
- **Typst file preview.** With a `.typ` file open, "Preview This Typst File"
  runs `typst watch` on it directly — handy for a paper's hand-maintained
  `main.typ`.
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
Windows comes after them — it works, with less attention. With VS Code on
Windows:

1. **Open the folder through Remote-WSL** (recommended). The extension then
   runs inside WSL and everything is the Linux path.
2. **Open a Windows folder, with WSL installed.** The extension runs `octavo`
   through `wsl.exe` (`octavo.executionMode: "auto"` picks this when WSL has a
   distribution), translating paths (`C:\Users\you\proj` ⇄
   `/mnt/c/Users/you/proj`). **Set up** installs into WSL.
3. **Directly on Windows, no WSL.** `auto` picks this when WSL has no
   distribution (or set `octavo.executionMode` to `"local"`). **Set up** then
   runs the bundled `setup.ps1`: winget installs pandoc, Typst, quarto and R,
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
