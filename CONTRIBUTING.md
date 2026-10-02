# Contributing

Issues and pull requests are welcome, in English or Japanese.

## Setup

No install step beyond Python itself — `octavo` is intentionally
stdlib-only. Installing it as a user is in [the guide](https://yoshida-kd.github.io/octavo/guide/#1-install). For the full toolchain
(pandoc/Typst) needed to actually build output, run `bash setup.sh`
(add `--with-tex` for LaTeX/Beamer).

## Running tests

```bash
python3 tests/test_octavo.py
```

Tests run with citations off and skip anything that needs a pandoc/TeX/Typst
version newer than what's installed — a skip is expected in a minimal
environment, not a failure. CI (`.github/workflows/tests.yml`) runs the same
suite across Python 3.9–3.14 on every push and pull request.

## Where things are

```
octavo/
  bin/octavo               entry point (put this on your PATH)
  pyproject.toml           packaging (pip install; distribution octavo-kit, command octavo)
  setup.sh                 installs the tools on Linux / WSL2 (apt) and macOS (Homebrew);
                           octavo setup and the extension's "Set up" both run it
  setup.ps1                the same for Windows itself (winget)
  config.example.py        configuration template (English)
  config.example.ja.py     the same template in Japanese — keep the two in key-for-key sync
  octavo/
    cli.py                 subcommands
    config.py              loads octavo.config.py and defines defaults
    md.py                  format-agnostic preprocessing (headings, tables, figures, conditional blocks)
    values.py              substitutes analysis values into the {{...}}; diffs against the last run
    analysis.py            staleness check for .qmd files and quarto render
    diagrams.py            figures drawn in Typst (figures/*.typ -> assets/figures/)
    handtables.py          tables made by hand (tables/*.csv -> assets/tables/)
    lint.py                finds results typed into the manuscript, and nested lists out of line
    theorems.py            cases, questions and other numbered blocks; restating and listing them
    extract.py             octavo extract (one PDF per session, cut from the handout)
    audit.py               octavo check (gathers every check)
    bundle.py              octavo bundle (submission and replication packages)
    review.py              reads tracked changes out of a coauthor's .docx
    ghrelease.py           octavo release (tag a version, PDF to a GitHub Release)
    dataset.py             data fingerprints (data/HASHES.json)
    build.py               the preprocess -> pandoc -> postprocess pipeline
    pandocrun.py           invoking pandoc and checking its version
    bib.py                 .bib parsing and validation
    csl.py                 resolving and fetching CSL styles
    paths.py               where the bundled templates live (repo checkout vs. pip install)
    tmpl.py                finds a template: the project's, then yours, then the bundled one
    confedit.py            octavo config: which settings the sidebar offers, and the line-level edit
    i18n.py                the display language (OCTAVO_LANG); t() wraps every message
    lang_ja.py             the Japanese of every message (the source strings are English)
    check.py               octavo checkbib
    doctor.py              octavo doctor (--json is what the extension reads)
    envsetup.py            octavo env (the project's .venv and renv)
    selftest.py            octavo selftest
    scaffold.py            octavo init (the research project tree; --example adds the examples) and octavo new (add a manuscript)
    backends/
      base.py              the Backend base class and shared cross-reference logic
      latex.py  typst.py  typst_slides.py  typst_notes.py  beamer.py  docx.py
  templates/                every template, each replaceable (§7; templates/README.md)
    project/                the frame octavo init writes (ja/ or en/)
    claude/                 the project CLAUDE.md, one section per kind of part
    analysis/               what the first analysis brings (common/analysis/octavo.R and python/analysis/octavo_helper.py — the helpers —, data/raw/README.md, requirements.txt)
    example/                what an example uses (placeholder values and tables, two made-up references)
    manuscripts/            what octavo new writes (paper / appendix / slides / lecture / analysis.qmd; example/ for --example)

The user's manual is `docs/guide.md` and `docs/guide.ja.md` (Markdown); `site/build.sh`
turns them into the pages at <https://yoshida-kd.github.io/octavo/guide/> when a release
reaches `main`. In the Japanese one, every code block is the English one's with only the
comments translated.

## Before opening a PR

- Keep new dependencies out of `octavo/` — the stdlib-only constraint is
  deliberate (it's what keeps `setup.sh` simple on the WSL2/Ubuntu deploy
  target this tool is built for).
- Adding a new output format? `octavo/backends/base.py` documents the
  `Backend` interface; `build.py` and `cli.py` should never need to branch
  on format name — add a new file under `backends/` and register it in
  `backends/__init__.py::REGISTRY` instead. `octavo/config.py::BACKENDS`
  needs the new name too.
- Run the test suite before pushing; a red CI run on a PR is expected to be
  fixed before it's merged.
- Small, focused PRs are easier to review than large ones that mix
  refactors with behavior changes.

## Reporting a bug

Please include: the command you ran, the full error/output, `octavo doctor`
output, and your pandoc/TeX/Typst versions (`pandoc --version`, etc.). [What to
check on your own machine](https://yoshida-kd.github.io/octavo/guide/#11-what-to-check-on-your-own-machine)
in the guide says which parts the test suite covers and which it doesn't.
