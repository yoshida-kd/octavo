# Contributing

Issues and pull requests are welcome, in English or Japanese.

## Setup

No install step beyond Python itself — `octavo` is intentionally
stdlib-only (see [README.md](README.md)). For the full toolchain
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
output, and your pandoc/TeX/Typst versions (`pandoc --version`, etc.) — §10
of the README ("What is tested, and what to check yourself") says which parts
are covered by the test suite and which aren't.
