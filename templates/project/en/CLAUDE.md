# About this repository

Research project for "@@NAME@@". **Analysis (Quarto `.qmd`), writing (Markdown),
and typesetting (Typst / Word / LaTeX / Beamer) all live in this one repository.**
Conversion is done by the `octavo` command from
[Octavo](https://github.com/yoshida-kd/octavo).

```
data/raw/         raw data. **read-only.** record provenance in data/raw/README.md
data/derived/     cleaned data, written by the .qmd files. never edited by hand
analysis/*.qmd    the analysis. every number, figure and table you present starts here
analysis/octavo.R the analysis-side helper (ov_value / ov_figure / ov_table)
results/*.json    values emitted by the .qmd (read by {{...}} in the text). never hand-edited
figures/          figures written by the .qmd (<name>.pdf and .png). may also be added by hand
tables/           tables written by the .qmd (<name>.tex and .typ)
refs/             material from elsewhere (codebooks, questionnaires, guidelines). kept in git
notes/            things you wrote (reading, referee, working notes). never part of the manuscript
papers/<name>/    a paper: paper.md, appendix.md, main.typ (layout) (**this is what you write**)
slides/<name>.md  a talk (**this is what you write**)
lectures/<name>.md lecture notes: an A4 handout plus one slide deck per session (**this is what you write**)
literature.bib    bibliography. **The reference manager (e.g. Zotero) is the source of truth** (its export overwrites it)
templates/        this project's own versions of Octavo's templates (absent = the bundled ones; octavo template list)
octavo.config.py  this project's configuration (sources, styling, analysis registration)
build/            generated output. **nothing here is written by hand; delete it freely**
```

## Kinds of manuscript, and their names

There are three kinds of manuscript, and **any number of each** can live in this
repository (two papers, ten talks, three sets of lecture notes). The kinds differ
only in their template and how they are typeset; the analysis, bibliography,
figures and tables are shared by all of them.

```bash
octavo new paper example-paper         # papers/example-paper/paper.md (+ appendix.md, main.typ / main.tex)
octavo new slides example-talk           # slides/example-talk.md
octavo new lecture example-lecture    # lectures/example-lecture.md
```

- **A document's name is its folder name (papers) or file name (slides, lectures).**
  `octavo build <name>` and friends take that name. Names must not collide, even
  across kinds
- Add manuscripts with `octavo new`. `documents` in `octavo.config.py` picks up
  whole folders, so **it needs no editing** — but a file placed elsewhere is not picked up
- To remove a manuscript, delete its file (a paper: its folder)

# Rules

## 1. Never type a result into the manuscript

**This is the central promise of this repository.** Coefficients, N, p-values,
descriptive statistics, proportions — every one of them is registered with
`ov_value()` in a `.qmd` and referenced as `{{name}}` in the prose.

```r
# analysis/*.qmd
ov_value("n_obs", nrow(d))
ov_value("coef_x", coef(m)[["x"]])
ov_value("p_x", ov_pval(summary(m)$coefficients["x", "Pr(>|t|)"]))
```

```markdown
<!-- any manuscript: papers/, slides/ or lectures/ -->
The sample has {{n_obs}} cases; the coefficient on x is
{{coef_x}} (*p* {{p_x}}).
```

A number typed by hand survives the re-estimation that changed it, leaving the
prose describing a result that no longer exists. That is the hardest kind of error to
spot and the most costly to be caught on, so there are no exceptions. If you feel the need
to write a raw figure into the text, first ask whether a `ov_value()` belongs in
the `.qmd` instead.

- Formatting can be overridden from the prose: `{{coef_x:.2f}}` (a Python format spec)
- Integers (R's `nrow()`) render as `1,523`; doubles (`coef()`) get 3 decimals by default
- `octavo values` cross-checks the names the prose asks for against what's in
  `results/`. **Run it every time the manuscript is touched.**

## 2. data/raw is read-only

Never rewrite, overwrite or clean anything under `data/raw/`. Cleaning happens in
a `.qmd`, and the result goes to `data/derived/`. Editing raw data in place makes
it impossible to say later what changed and when.

When you add data, record its **provenance, retrieval date and terms of use** in
`data/raw/README.md` — `data/raw/` itself is gitignored, so that README is the
only trace that survives in version control.

## 3. Don't edit build output

Whatever `octavo build` generates (the contents of `build/typst/`,
`build/typst-slides/`, `build/word/` and so on) **is erased by the next build.**
The thing to fix is the manuscript or the `.qmd`. Nothing under `build/` is written
by hand, so the whole directory can be deleted (git does not track it).

Journal-specific layout (document class, margins, title block, leading) belongs in
**`papers/<name>/main.typ`** (or `main.tex` for LaTeX): **a file you own, sitting next
to the manuscript.** Octavo never regenerates it — it copies it into `build/` on every
build and typesets there (what it writes is `body.typ`, `abstract.typ` and the like).

## 4. The reference manager owns literature.bib

`literature.bib` is exported from the reference manager (e.g. Zotero), and the next export
**overwrites the file wholesale**, so hand-edits are lost. Fix bibliographic errors there.

- `octavo checkbib` — are the cited keys in the `.bib`, and is the `.bib` well-formed
- Findings you've decided not to fix go in `bib_accepted` in `octavo.config.py`, with a reason

## 5. Figure and table naming (get it wrong and cross-references break)

Octavo turns "Figure 1" / "Table 1" in the prose into real typeset cross-references,
and it **reads the number out of the file name**. Off-convention names don't link.

| | Naming | Example | In the prose |
|---|---|---|---|
| Figure | `fig<number>_<slug>` | `fig1_trend` | `![](../../figures/fig1_trend.png)` + `**Figure 1.** Trend` |
| Table | `tbl<number>_<slug>` | `tbl1_summary` | `**Table 1. ...**` + `table_map` in the config |
| Appendix figure | `fig<letter><number>_...` | `figA1_balance` | "Figure A1" |

Reference the `.png` in the manuscript; Octavo finds the `.pdf` for LaTeX on its own.
`ov_figure()` writes both. Write the path relative to the manuscript (`../../figures/`
from a paper, `../figures/` from slides and lectures) so editor previews work; Octavo
looks at **the file name only** and finds it in `figures/`.

Figures, tables and `{{...}}` values are shared by every manuscript. To show a
paper's figure on a slide, point at the same file in `figures/` — don't copy it.

To swap a table for an external file in `tables/`, map "table number → file name"
in `table_map` in `octavo.config.py`. Without an entry, the Markdown table in the
manuscript is typeset as-is (which is always what Word and slides get).

## 6. The templates are marked as templates

Everything `octavo init` / `octavo new` writes is an **example**, and says so.
Once you replace it with your own content, **delete the mark too.**

| Mark | Where | How it goes away |
|---|---|---|
| a `octavo:example` comment | manuscripts, appendix, `analysis.qmd`, `literature.bib` | delete it by hand |
| `_placeholder` | `results/analysis.json` | `octavo analysis run` rewrites the file |
| a figure that is a box with an × | `figures/fig1_trend.*` | `ov_figure()` rewrites it |

**The placeholder values are the dangerous one.** Every `{{...}}` resolves even
though the analysis has never run, so **a PDF full of fake numbers typesets
cleanly.** Against that:

- `octavo check` treats placeholder values as **fatal**
- `octavo build` prints `[値][注意] … 本文の数字は嘘` on every run
- `octavo values` says it first thing

While marks remain, `octavo check` counts them as leftovers. **Get that to zero
before you finish.**

# How to work

## Adding or re-running an analysis

1. Edit `analysis/*.qmd` (load data from `data/`)
2. `octavo analysis run` (or just `octavo build` — stale analyses run automatically)
3. `octavo values` to confirm the numbers came out
4. Reference them from the manuscript as `{{name}}`

A new `.qmd` is picked up by the `analysis` glob in `octavo.config.py`
(`analysis/*.qmd` by default). Add heavy inputs to `deps` to have them watched too.

## The analysis environment is .venv and renv (always)

**Never run the analysis against a bare R or Python.** Each project gets its own
environment, and every package used is recorded. Without that, neither you in six
months nor a reviewer can reproduce the result.

- Python: run inside `.venv` (`source .venv/bin/activate`), and add each package
  to `requirements.txt` with its version
- R: run in a project where `renv::init()` has been done, and always follow
  `install.packages()` with `renv::snapshot()` (commit `renv.lock`)

`.venv/` and `renv/library/` are not in git. **Only the records
(`requirements.txt` / `renv.lock`) are**, so failing to record loses the environment.

## Splitting the analysis across several .qmd files

Split the analysis whenever it gets long — `analysis/*.qmd` picks up new files
automatically. Each `.qmd` owns `results/<its own name>.json`, and the split is
invisible from the manuscript: every `{{name}}` resolves the same way.

**When one file produces another's input**, order them in `octavo.config.py` and
list the upstream output in the downstream `deps`. Prefixing file names with
`01-`, `02-` achieves the same thing under a plain glob.

```python
'analysis': [
    {'src': 'analysis/01-clean.qmd', 'manual': True},        # writes data/derived/ (slow)
    {'src': 'analysis/02-model.qmd', 'deps': ['data/derived/*']},
],
```

**Put slow steps such as data cleaning in their own `.qmd` marked `'manual': True`.**
Neither `octavo build` nor the preview runs it; they only say it is stale. Run it with
`octavo analysis run analysis/01-clean.qmd` (in VS Code, the button in the sidebar's
Analysis section).

- If two `.qmd` files register the same name it warns and **the later one wins**;
  check the source column in `octavo values`.
- **When you delete or rename a `.qmd`, delete its `results/*.json` too.** Left
  behind, the manuscript keeps picking up stale numbers (`octavo analysis` and
  `octavo values` flag these as value files with no matching `.qmd`).

## Adding an appendix to a paper

Write the appendix in `appendix.md` in the paper's folder. Being next to
`paper.md` is enough to attach it (delete it if you don't need one). To swap
appendix tables for external files:

```python
'appendix_table_map': {'A1': 'tblA1_robustness'},   # appendix tables use their own map
```

```bash
octavo build <name> --appendix
```

Then uncomment `#include "appendix.typ"` in `papers/<name>/main.typ`
(or `\appendix` and `\input{appendix}` in `main.tex` for LaTeX).

The appendix gets **the same treatment** as the body: values, citations and
cross-references all work, and `octavo values`, `octavo checkbib` and
`octavo outline` read it. Number it separately from the body
(`## Appendix A. ...`, figures as `figA1_balance`, tables as `tblA1_robustness`).

## Writing and revising

```bash
octavo build                   # convert every manuscript (a stale analysis runs first)
octavo build <name>            # just one
octavo values                  # any unresolved {{...}}?
octavo checkbib                # are the cited keys in the .bib?
octavo outline                 # show the heading structure
```

`octavo build --no-citations` skips citation resolution for a fast look.
`octavo build --no-analysis` converts against the current `results/` without
re-running anything — what you want when an estimation is slow.

After a re-estimation, read **`octavo values --diff`**: it shows **which numbers
in the paper moved** since the analysis last ran. When one moves, fix the prose
around it too ("slightly", "about", "significantly").

## Before you finish

```bash
octavo check          # every check in one pass (non-zero exit on fatal findings)
octavo lint           # just the numbers typed into the prose, in detail
```

`octavo check` covers: sources exist / analysis freshness / orphaned value files /
unresolved `{{...}}` / **placeholder values still in place** / citation keys /
bibliography quality / **figure and table files actually existing** / placeholder
figures / template leftovers / results typed into the prose / submission limits /
data fingerprints / recorded analysis environment.

**Do not submit or hand out anything while something is marked fatal.** Warnings are
for you to judge.

## When the data changes

```bash
octavo data hash      # re-record the fingerprints (commit data/HASHES.json)
octavo data status    # does anything differ from the record?
```

`data/` isn't in git, so `data/HASHES.json` is the only record of which data was
used. **Drift you didn't cause is an accident, not a nuisance.**

# Papers

## Submitting

To repackage:

```bash
octavo build <name>
octavo bundle <name>                 # submission-<name>.zip, paths flattened
octavo bundle <name> --dir --out example-talk   # a folder instead of a zip
```

With a single paper in the repository, `<name>` can be left out.
### For blind review

```bash
octavo build <name> --anonymous
octavo check --anonymous             # also lists self-citation candidates
octavo bundle <name> --anonymous     # checks for leaks before packaging
```

Wrap anything identifying in a conditional block in the manuscript:

```markdown
::: {.no-anonymous}
Acknowledgements: funded by ...
:::
```

- `octavo bundle --anonymous` **fails** if it finds an author name outside a
  conditional. That is where a forgotten name gets caught.
- It refuses to package output that wasn't built with `--anonymous`.
- Whether to mask a self-citation is the journal's rule; the tool **only lists
  candidates**.

### When a coauthor sends Word back

```bash
octavo review 20260907_draft_tanaka.docx
```

**Never write the docx back into `paper.md`.** In the returned file `{{n_obs}}`
is already the literal "1,523"; writing it back pins the number into the
manuscript and breaks this repository's central promise. `octavo review` exists
so you can **read** the tracked changes and comments; you apply them by hand in
`paper.md`.

### For a revision (R&R)

Mark the version you submitted. `octavo release` tags it (with the paper's name
in the tag) and keeps the submitted PDF on a GitHub Release (`build/` is not in
git, so that is where the actual file survives):

```bash
octavo release example-paper v1-submitted     # tag example-paper-v1-submitted + the PDF
# ... review, revise ...
octavo values --diff example-paper-v1-submitted    # what moved since submission
```

### After acceptance

```bash
octavo bundle --replication          # a different set from the submission zip
```

Raw data is excluded by default. Add `--with-raw-data` only after checking it
may be redistributed.

## Producing a PDF

```bash
octavo build <name> --compile          # typeset main.typ into a PDF
octavo build <name> --to docx          # Word, to send to coauthors
# submitting in LaTeX (needs TeX: setup.sh --with-tex)
octavo build <name> --to latex && cd build/latex/<name> && latexmk -lualatex main.tex
```

# Slides and lecture notes

## Talks

```bash
octavo build example-talk --compile        # slides/example-talk.md, straight to PDF
```

## Lecture notes

**One set of lecture notes** produces the A4 handout (all sessions in one) and
**a separate slide deck for each `#` heading**. One `#` is one session; each `##`
is a slide.

```bash
octavo build example-lecture --to typst --compile           # A4 handout, straight to PDF
octavo build example-lecture --to typst-slides --compile    # one PDF deck per session
octavo build example-lecture-03 --to typst-slides           # just the third session
```

- Decks are named `<notes name>-01`, `-02`, … in order of the `#` headings.
  **Inserting a session renumbers the ones after it**, so give a heading an id
  to pin its name: `# Second session {#second}` → `example-lecture-second`
- A session deck's title slide takes the `#` heading as its title and the notes'
  title as its subtitle
- Anything before the first `#` goes into the handout only

Conditional blocks decide what goes where.

```markdown
::: {.handout-only}
handout only (fill-in blanks, longer notes)
:::

::: {.slides-only}
slides only (figures, short prompts)
:::
```

## Common to all slides

Each `##` is a slide (a `#` is a section divider in a talk, and a session break in
lecture notes). Figures are fitted into the
slide and are not numbered. `::: notes` (speaker notes) never appear on the projected
deck; they go in the speaker script (`--to typst-notes`).

Course material and slides can use `{{...}}` values too — they read the same
`results/`. **As in a paper, never type a number by hand.**

# Never

- **Never hand-edit anything generated: `results/*.json`, `figures/`, `tables/`,
  `build/` output.** The thing to fix is always the `.qmd` or the manuscript.
- **Never type an analysis result into the manuscript** (see Rule 1).
- **Never hand-edit `literature.bib`** (fix it in the reference manager).
- **Never modify `data/raw/`.**
- When a number doesn't line up, never replace `{{...}}` with a literal to "make it
  build". If the value is missing, the correct fix is a `ov_value()` in the `.qmd`.
- Never dump `octavo lint` findings into `lint_accepted` without checking them.
  That list is only for things you have decided are not results.
- **Never write a coauthor's docx back into `paper.md`** (it pins the numbers).
- **Never put a manuscript outside the places `octavo new` uses** (`octavo.config.py` won't pick it up).
- **Never hand-edit `data/HASHES.json`.** Regenerate it with `octavo data hash`
  only when the data itself changed.
- **Don't delete a `octavo:example` mark without replacing the content.** The mark
  records that a passage is still an example; it goes when the content does.
- Don't invent new keys in `octavo.config.py` — unknown keys are warned about at startup.

# When something is wrong

```bash
octavo doctor       # is pandoc / LaTeX / Typst / quarto / R present?
octavo selftest     # see how citations actually typeset, on real output
octavo analysis     # which .qmd is stale?
```

For the `octavo` command itself, see `README.md` in Octavo.
