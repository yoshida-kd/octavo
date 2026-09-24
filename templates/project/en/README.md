# @@NAME@@

Analysis, writing and typesetting in a single repository. Conversion is done by
the `octavo` command from
[Octavo](https://github.com/yoshida-kd/octavo).

## Where things go

| Directory | Contents |
|---|---|
| `data/raw/` | raw data. **read-only**, and gitignored (record provenance in `data/raw/README.md`) |
| `data/derived/` | cleaned data, written by the `.qmd` files. gitignored |
| `analysis/` | the analysis (`.qmd`) and its helper `octavo.R`. Every number, figure and table you present starts here |
| `results/` | values emitted by the `.qmd` (`*.json`), read by `{{...}}` in the prose |
| `figures/` `tables/` | figures and tables written by the `.qmd` |
| `papers/<name>/` | a paper (`paper.md`, `appendix.md`, and the layout `main.typ` / `main.tex`) |
| `slides/<name>.md` | a talk |
| `lectures/<name>.md` | lecture notes (A4 handout + one slide deck per session) |
| `refs/` | **material from elsewhere** (codebooks, questionnaires, submission guidelines). kept in git |
| `notes/` | **things you wrote** (reading and referee notes); never part of the manuscript |
| `build/` | generated output. **nothing here is hand-written**, so delete it freely |
| `templates/` | (only if you make one) this project's own versions of Octavo's templates — start one with `octavo template copy slides/typst-slides.typ` and edit it |

The bibliography is `literature.bib` (exported from your reference manager, e.g. Zotero),
and the configuration is `octavo.config.py`. Papers themselves live in the reference
manager, so don't keep their PDFs in `refs/`.

## Telling the template from the real thing

Everything `octavo init` / `octavo new` writes carries a **mark saying it is a
template**. Delete the mark along with the content once it is yours.

| Mark | Where | How it goes away |
|---|---|---|
| a `octavo:example` comment | manuscripts, appendix, `analysis.qmd`, `literature.bib` | delete the block, comment and all |
| `_placeholder` | `results/analysis.json` | `octavo analysis run` rewrites the file |
| a figure that is a box with an × | `figures/fig1_trend.*` | `ov_figure()` in the `.qmd` rewrites it |

`octavo check` counts what is left. The placeholder values in
`results/analysis.json` are **fatal**: typesetting before the analysis has ever
run puts fake numbers in the prose. Every build prints a `[値][注意]` line too.

## Adding manuscripts

Papers, talks and lecture notes — any number of each.

```bash
octavo new paper example-paper      # papers/example-paper/paper.md
octavo new slides example-talk        # slides/example-talk.md
octavo new lecture example-lecture # lectures/example-lecture.md
```

`octavo.config.py` needs no editing (it picks up whole folders). The name for
`octavo build <name>` is the folder name for a paper and the file name otherwise.

## The one rule that matters

**Never type a result into the manuscript.** Register it in the `.qmd` and refer
to it by name in the prose.

```r
# analysis/analysis.qmd
ov_value("n_obs", nrow(d))
ov_value("coef_x", coef(m)[["x"]])
```

```markdown
<!-- papers/example-paper/paper.md -->
The sample has {{n_obs}} cases and the coefficient is {{coef_x}}.
```

Then re-running the estimation updates the prose too. `octavo values`
cross-checks the manuscript against `results/`.

## Usage

```bash
octavo build                   # convert every manuscript (a stale analysis runs first)
octavo build example-paper       # just one
octavo build example-paper --to typst,docx   # pick formats

octavo analysis                # which .qmd is stale?
octavo analysis run            # run the analysis
octavo values                  # is every {{...}} in the prose resolvable?
octavo checkbib                # are the cited keys in the .bib?
octavo watch --to typst        # rebuild on every save
```

All the way to a PDF:

```bash
octavo build --compile                                   # typeset into a PDF
octavo build example-lecture --to typst-slides --compile  # lecture notes -> a deck per session
```

## The analysis environment (.venv and renv)

The analysis runs in this project's own environment. **Never against a bare R or
Python.**

```bash
python3 -m venv .venv                  # once
source .venv/bin/activate              # every session, before rendering a .qmd too
pip install -r requirements.txt
```

```r
renv::init()       # once (writes renv.lock and .Rprofile)
renv::snapshot()   # always, after install.packages()
```

renv itself does not come with R. If you get `there is no package called
‘renv’`, install it once per machine first (and create your personal library
folder — without it `install.packages()` has nowhere to write and fails):

```bash
mkdir -p "$(Rscript -e 'cat(Sys.getenv("R_LIBS_USER"))')"
Rscript -e 'install.packages("renv", repos = "https://cloud.r-project.org")'
```

`octavo doctor` shows whether it is there, under "Analysis".

Record every package you add in `requirements.txt` / `renv.lock`. `.venv/` and
`renv/library/` are not in git, so **the records are the environment.**

Octavo itself (pandoc, Typst, quarto) lives outside the project, once per machine:
`bash setup.sh` in the Octavo repository, or `bash setup.sh --with-tex` if you
also want LaTeX / Beamer.

## Getting started

1. `octavo doctor` — check that pandoc / Typst / quarto / R are present (LaTeX is optional)
2. Set up the analysis environment (above): `python3 -m venv .venv` and `renv::init()`
3. Put your raw data in `data/raw/` and record its provenance in `data/raw/README.md`
4. Replace `analysis/analysis.qmd` with your own analysis
5. `octavo analysis run`, then `octavo values` to confirm the numbers came out
6. Add a manuscript with `octavo new paper|slides|lecture <name>` and write it
7. Once a paper has a target journal, run `octavo csl get <style-id>` and align
   `csl` in `octavo.config.py` and the layout in `papers/<name>/main.typ`

The working agreements for Claude Code are in `CLAUDE.md`.
