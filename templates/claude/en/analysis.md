<!-- octavo:section analysis -->
# The analysis

```
data/raw/         raw data. **read-only.** record provenance in data/raw/README.md
data/derived/     cleaned data, written by the .qmd files. never edited by hand
analysis/*.qmd    the analysis. every number, figure and table you present starts here
analysis/octavo.R the analysis-side helper (ov_value / ov_figure / ov_table)
assets/values/    values emitted by the .qmd (<qmd name>.json, read by {{...}} in the text). never hand-edited
assets/tables/    tables written by the .qmd (<name>.typ / .tex / .md)
assets/figures/   figures written by the .qmd (<name>.pdf / .png)
requirements.txt  the Python packages the analysis uses (with renv.lock, the record of the environment)
```

## Never type a result into the manuscript

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
  `assets/values/`. **Run it every time the manuscript is touched.**
- Name figures (`ov_figure(p, "trend")`) and tables (`ov_table(tab, "summary")`) by
  their content, never with a number. Label the table `tbl-<table name>` and the
  analysis's table is put there. `ov_figure()` writes both the `.pdf` and the `.png`

## data/raw is read-only

Never rewrite, overwrite or clean anything under `data/raw/`. Cleaning happens in
a `.qmd`, and the result goes to `data/derived/`. Editing raw data in place makes
it impossible to say later what changed and when.

When you add data, record its **provenance, retrieval date and terms of use** in
`data/raw/README.md` — `data/raw/` itself is gitignored, so that README is the
only trace that survives in version control.

**Data you transcribe by hand** (numbers read off a government PDF or a chart) goes in
`data/raw/` too. While you are transcribing, add rows freely; **once it is done, treat it
like downloaded data.** To fix a mistake, check it against the source and note the fix in
`data/raw/README.md`. Hand-made data cannot be fetched again, so unless it can't be shared,
add `!data/raw/<file>.csv` to `.gitignore` to keep it in git. The CSV can be edited in
VS Code's table view as well.

## Adding or re-running an analysis

1. Edit `analysis/*.qmd` (load data from `data/`). To add one, `octavo new analysis <name>`
2. `octavo analysis run` (or just `octavo build` — stale analyses run automatically)
3. `octavo values` to confirm the numbers came out
4. Reference them from the manuscript as `{{name}}`

The `analysis` glob in `octavo.config.py` (`analysis/*.qmd` by default) picks up
every `.qmd`. Add heavy inputs to `deps` to have them watched too.
`octavo build --no-analysis` converts against the current `assets/values/` without
re-running anything — what you want when an estimation is slow.

After a re-estimation, read **`octavo values --diff`**: it shows **which numbers
in the paper moved** since the analysis last ran. When one moves, fix the prose
around it too ("slightly", "about", "significantly").

## The analysis environment is .venv and renv (always)

**Never run the analysis against a bare R or Python.** Each project gets its own
environment, and every package used is recorded. Without that, neither you in six
months nor a reviewer can reproduce the result.

- Set it up (or restore it after a clone) with `octavo env`: `.venv` via uv
  plus `requirements.txt`, and renv with knitr / rmarkdown
- Python: run inside `.venv` (`octavo analysis run` uses it by itself; by hand, use
  `uv run` or activate it). Add each
  package to `requirements.txt` with its version, then `octavo env` — don't
  `pip install` into anything else
- R: run in the renv project, and always follow `install.packages()` with
  `renv::snapshot()` (commit `renv.lock`)

`.venv/` and `renv/library/` are not in git. **Only the records
(`requirements.txt` / `renv.lock`) are**, so failing to record loses the environment.

The project has to work on Linux, macOS and Windows alike:

- Paths are relative and written with `/` — in the manuscript, the `.qmd` and
  the config. Never a drive letter or a `\`
- In Python, open text files with `encoding="utf-8"` (Windows defaults to its
  own code page)
- A file's name, upper and lower case included, is exactly what the manuscript
  and the code write (Windows would forgive `Fig1.png` for `fig1.png`; Linux won't)

## Splitting the analysis across several .qmd files

Split the analysis whenever it gets long (`octavo new analysis <name>` is all it
takes). Each `.qmd` owns `assets/values/<its own name>.json`, and the split is invisible
from the manuscript: every `{{name}}` resolves the same way.

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
Analysis section). The `.qmd` can say it itself instead, so the glob in the config stays:
`octavo:` then `  manual: true` (and `  deps: [...]`) in its front matter.

**Fetching raw data** (an API, a download) is such a step: `analysis/00-fetch-<source>.qmd`
with `manual: true`. It stops rather than overwrite a file already in `data/raw/`, and the
source and date go into `data/raw/README.md`.

- If two `.qmd` files register the same name it warns and **the later one wins**;
  check the source column in `octavo values`.
- **When you delete or rename a `.qmd`, delete its `assets/values/*.json` too.** Left
  behind, the manuscript keeps picking up stale numbers (`octavo analysis` and
  `octavo values` flag these as value files with no matching `.qmd`).

## When the data changes

```bash
octavo data hash      # re-record the fingerprints (commit data/HASHES.json)
octavo data status    # does anything differ from the record?
```

`data/` isn't in git, so `data/HASHES.json` is the only record of which data was
used. **Drift you didn't cause is an accident, not a nuisance.**

## Never, in the analysis

- **Never hand-edit what the analysis generates: `assets/values/`, `assets/tables/`,
  `assets/figures/`.** The thing to fix is always the `.qmd`.
- **Never type an analysis result into the manuscript** (see above).
- **Never modify `data/raw/`.**
- When a number doesn't line up, never replace `{{...}}` with a literal to "make it
  build". If the value is missing, the correct fix is an `ov_value()` in the `.qmd`.
- **Never hand-edit `data/HASHES.json`.** Regenerate it with `octavo data hash`
  only when the data itself changed.
- When something is off, `octavo analysis` says which `.qmd` is stale.
