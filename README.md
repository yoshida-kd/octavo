# Octavo

**The quantitative social science starter pack**

[![tests](https://github.com/yoshida-kd/octavo/actions/workflows/tests.yml/badge.svg)](https://github.com/yoshida-kd/octavo/actions/workflows/tests.yml)

[日本語の README](https://github.com/yoshida-kd/octavo/blob/main/README.ja.md)

Write your papers, slides and lecture notes in Markdown, keep the analysis in
Quarto, and let Octavo place the analysis's numbers, figures and tables in every
document — then typeset them to PDF (with Typst) and Word, or LaTeX if you have
TeX. Citations come from one `.bib` file, in any CSL style.

![How Octavo works: the analysis and the files you make by hand give the numbers, figures and tables; the manuscript refers to them by name and says what to make; octavo build makes the PDF, slides, a poster, Word and LaTeX](https://raw.githubusercontent.com/yoshida-kd/octavo/main/docs/images/flow-en.svg)

## What you get

![A paper page and a slide built from the example project](https://raw.githubusercontent.com/yoshida-kd/octavo/main/docs/images/showcase-en.png)

A page of a paper and a slide, both built from the example project
(`octavo init demo --all --example`). The coefficient, the table and the figure
come from the analysis; the equation, table and figure numbers and the
references are filled in when it is typeset.

- **No number is typed by hand.** The analysis registers it
  (`ov_value("n_obs", nrow(d))`) and the manuscript calls it by name (`{{n_obs}}`).
  Re-run the analysis and every document follows. `octavo check` points out
  numbers typed into the prose, and values that are only placeholders.
- **R or Python.** The analysis is a Quarto `.qmd` in R or in Python; both come
  with the same helpers (`ov_value`, `ov_figure`, `ov_table`), and the project's
  `.venv` and renv are set up for you.
- **One source, several documents.** A paper in your journal's layout, a talk,
  lecture notes that become an A4 handout plus one slide deck per session, and an A0
  conference poster — with speaker scripts, and Word for coauthors.
- **References by label**: `@fig-trend` becomes "Figure 2.1", and stays right
  when you reorder sections.
- **Diagrams without TikZ**: `octavo new figure` gives you a Typst file to draw
  boxes and arrows in; it becomes a figure like any other.
- **Tables by hand, edited as tables**: `octavo new table` gives you a CSV that
  the VS Code extension edits as a grid (Excel works too); it becomes a table
  like the analysis's.
- **Submission and beyond**: word limits, blind review, a submission zip,
  reading a coauthor's tracked changes in Word, "what moved since I submitted",
  and a replication package.
- **A VS Code extension** with a live PDF preview that follows the cursor, a
  sidebar for everything above, and one-click setup.
- **Ready for your AI assistant**: every project keeps its working rules in
  `AGENTS.md` — never type a result into the manuscript, `data/raw` is read-only, and
  so on — and Claude Code, GitHub Copilot, Codex and Antigravity all read it, so the
  assistant knows them from the start.
- Linux, macOS and Windows; English and Japanese.

## Install

**With VS Code**, install the [Octavo extension](https://marketplace.visualstudio.com/items?itemName=yoshida-kd.octavo)
and press **Set up** when it asks: it installs pandoc, Typst, Quarto, R, the
fonts and the `octavo` command.

**From a terminal**:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # uv, if you don't have it yet
uv tool install octavo-kit                        # the octavo command
octavo setup                                      # pandoc / Typst / Quarto / fonts / R
octavo doctor                                     # reports anything still missing
```

## Getting started

**With VS Code**:

1. Open a folder and the Octavo icon in the activity bar. In a folder that is not a
   project yet it offers **New project**: choose where, the language, the parts you
   need (an analysis in R or Python, a paper, slides, lecture notes) and whether to
   fill them with examples. An analysis gets its environment set up right after.
2. Open a manuscript and press the **PDF** button at the top right of the editor: the
   PDF appears beside it, is rebuilt on every save, and follows your cursor.
3. Add more from the **+** at the top of the Octavo sidebar.

**From a terminal**, start with the example project — an analysis, a paper, slides and lecture notes:

```bash
octavo init demo --all --example
cd demo
octavo env                    # the project's analysis environment (.venv and renv)
octavo build --compile        # runs the analysis, then typesets everything to PDF
```

Then your own project, starting with the parts you need:

```bash
octavo init study --with analysis,paper
cd study
octavo env                    # the project's analysis environment (.venv and renv)
octavo build paper --compile  # after writing analysis/analysis.qmd and docs/paper/paper.md
octavo check                  # before you submit
```

In the analysis, register what the paper shows; in the manuscript, refer to it:

```r
ov_value("n_obs", nrow(d))
ov_figure(p, "trend")
```

```python
ov_value("n_obs", len(d))
ov_figure(fig, "trend")
```

```markdown
The sample has {{n_obs}} cases (@fig-trend).

![Trend](../../assets/figures/trend.png){#fig-trend}
```

## Documentation

[The guide](https://yoshida-kd.github.io/octavo/guide/) covers everything:

1. [Install](https://yoshida-kd.github.io/octavo/guide/#1-install) — Linux, macOS and Windows, step by step
2. [Your first project](https://yoshida-kd.github.io/octavo/guide/#2-your-first-project) — `octavo init` and `octavo new`, the analysis environment
3. [Writing manuscripts](https://yoshida-kd.github.io/octavo/guide/#3-writing-manuscripts) — references, numbered blocks, math, figures, tables
4. [The analysis](https://yoshida-kd.github.io/octavo/guide/#4-the-analysis) — numbers, figures and tables from Quarto
5. [Citations](https://yoshida-kd.github.io/octavo/guide/#5-citations)
6. [Papers](https://yoshida-kd.github.io/octavo/guide/#6-papers-from-draft-to-submission) — checking, blind review, submitting, revisions
7. [Slides, lecture notes and posters](https://yoshida-kd.github.io/octavo/guide/#7-slides-lecture-notes-and-posters) — sessions, per-session handouts, posters
8. [Making it yours](https://yoshida-kd.github.io/octavo/guide/#8-making-it-yours) — templates, Word styles, fonts
9. [Command reference](https://yoshida-kd.github.io/octavo/guide/#9-command-reference)
10. [VS Code](https://yoshida-kd.github.io/octavo/guide/#10-vs-code)
11. [What to check on your own machine](https://yoshida-kd.github.io/octavo/guide/#11-what-to-check-on-your-own-machine)

## Contributing and license

Issues and pull requests are welcome — see
[CONTRIBUTING.md](https://github.com/yoshida-kd/octavo/blob/main/CONTRIBUTING.md).
MIT License.
