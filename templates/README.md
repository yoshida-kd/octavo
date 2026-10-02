# Templates

Everything Octavo writes or typesets from lives here, and **every file can be
replaced with your own**. Put a file with the same relative path in either of

| Where | Applies to |
|---|---|
| `<project>/templates/` | that project only |
| `~/.config/octavo/templates/` (`$XDG_CONFIG_HOME/octavo/templates/`) | all your projects |

Octavo looks in the project first, then in your own folder, then here. A
replacement is used **as a whole** — it is not merged with the bundled file.

```bash
octavo template list                              # what is in use, and from where
octavo template copy slides/typst-slides.typ      # into this project's templates/, to edit
octavo template copy paper/ja/main.typ --user     # into ~/.config/octavo/templates/
octavo template diff slides/typst-slides.typ      # yours against the bundled one
```

After updating Octavo, `octavo template diff` shows what changed in the
bundled version since you copied it.

| Folder | Used by | What |
|---|---|---|
| `project/<lang>/` | `octavo init` | the frame every project shares, copied as a tree (`gitignore` becomes `.gitignore`, a trailing `.tmpl` is dropped). A file you **add** under your own `project/<lang>/` is written into every new project too; one under your own `project/common/` is written whatever the language |
| `claude/<lang>/` | `octavo init`, `octavo new` | the project's rules for AI assistants, written to `AGENTS.md` (which Claude Code, GitHub Copilot, Codex and Antigravity read): `common.md` at `init`, and `analysis.md` / `analysis-python.md` / `paper.md` / `slides.md` appended when that kind of part is first added (each starts with an `octavo:section` mark). `stub.md` is the one-line `CLAUDE.md` that points Claude Code at it |
| `analysis/common/`, `analysis/python/`, `analysis/<lang>/` | the first `octavo new analysis` (`common` for R, `python` for `--engine python`) | `analysis/octavo.R` or `analysis/octavo_helper.py` (the helper), `data/raw/README.md`, `requirements.txt`; `analysis/python-requirements.txt` is what a Python analysis adds to `requirements.txt` |
| `manuscripts/<lang>/` | `octavo new` | `paper.md`, `appendix.md`, `slides.md`, `lecture.md` — bare headings — `analysis.qmd` / `analysis-python.qmd`, the frame of an analysis, `figure.typ`, a figure drawn in Typst (`octavo new figure`), and `table.csv`, a table made by hand (`octavo new table`) |
| `manuscripts/<lang>/example/` | `octavo new --example` | `paper.md`, `appendix.md`, `slides.md`, `lecture.md` and `analysis.qmd` again, as worked examples |
| `example/<lang>/` | `--example` | what an example uses: placeholder values (`assets/values/<name>.json`) and `assets/tables/summary.*` (marked `octavo:placeholder`), and two made-up references appended to `literature.bib` |
| `paper/<lang>/` | `octavo new paper` | the layout `main.typ` / `main.tex` copied next to each paper |
| `paper/csl-preamble.tex` | — | the `CSLReferences` definition, for a journal's own `main.tex` |
| `slides/` | `octavo build` | the Typst deck and speaker script, and the Beamer header |
| `handout/` | `octavo build` | the A4 handout's layout: `handout.typ` (Typst; cover, contents, jsarticle-style type) and `handout-header.tex` (the LaTeX header) |
| `citations/japanese.lua` | `octavo build` | a pandoc filter for Japanese documents: English works formatted in English, Japanese works (`langid = {japanese}`) as 山田・田中, ほか, 「」 and 『』 (`citations_by_language`) |
| `typst/crossref.typ` | `octavo build` | how figures, tables, equations and sections are numbered and how `@fig-…` references read, in every Typst output (papers import it as `crossref.typ`) |
| `replication/<lang>/` | `octavo bundle --replication` | the README that goes into the replication package |

In the text files, `@@NAME@@` becomes the project or document name and
`@@AUTHOR@@` the author from `octavo.config.py` (`@@DOCUMENTS@@` in the config
template is the `documents` block Octavo generates).

---

## テンプレート（日本語）

Octavo が書き出すもの・組版に使うものはすべてここにあり、**どれも自分のものに
差し替えられる**。同じ相対パスで `<プロジェクト>/templates/`（そのプロジェクト
だけ）か `~/.config/octavo/templates/`（自分の全プロジェクト）に置けば、
プロジェクト → 自分 → 同梱 の順に探して最初に見つかったものを使う。差し替えは
丸ごとで、同梱のものとは混ぜない。

`octavo template list` で何が効いているか、`octavo template copy <名前> [--user]`
でコピーして直し始める、`octavo template diff <名前>` で同梱との違い（Octavo を
更新したあとに同梱の側で何が変わったか）が見られる。
どのフォルダが何に使われるかは、上の英語の表を参照。
