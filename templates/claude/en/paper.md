<!-- octavo:section paper -->
# Papers

```
papers/<name>/    a paper: paper.md, main.typ (layout), and if needed appendix.md, main.tex (**this is what you write**)
```

Journal-specific layout (document class, margins, title block, leading) belongs in
**`papers/<name>/main.typ`** (or `main.tex` for LaTeX): **a file you own, sitting next
to the manuscript.** Octavo never regenerates it — it copies it into `build/` on every
build and typesets there (what it writes is `body.typ`, `abstract.typ` and the like).

## Producing a PDF

```bash
octavo build <name> --compile          # typeset main.typ into a PDF
octavo build <name> --to docx          # Word, to send to coauthors
# submitting in LaTeX (needs TeX: octavo setup --with-tex)
octavo new paper <name> --tex          # add the main.tex layout beside the manuscript (once)
octavo build <name> --to latex && cd build/latex/<name> && latexmk -lualatex main.tex
```

## Adding an appendix

Write the appendix in `appendix.md` in the paper's folder. Being next to
`paper.md` is enough to attach it (delete it if you don't need one).

```bash
octavo new paper <name> --appendix   # add appendix.md (paper.md is left alone)
octavo build <name> --appendix
```

Then uncomment `#show: octavo-appendix` and `#include "appendix.typ"` in
`papers/<name>/main.typ` (or `\appendix` and `\input{appendix}` in `main.tex`
for LaTeX).

The appendix gets **the same treatment** as the body: values, citations and
cross-references all work, and `octavo values`, `octavo checkbib` and
`octavo outline` read it. Don't write "Appendix A" in the headings: its sections
are lettered A, B, … when typeset, and its figures, tables and equations
numbered A.1, … Labels work across the paper and the appendix (the paper can
refer to `@tbl-definitions`).

## Submitting

To package it for submission:

```bash
octavo build <name>
octavo bundle <name>                 # submission-<name>.zip, paths flattened
octavo bundle <name> --dir --out submission   # a folder instead of a zip
```

With a single paper in the repository, `<name>` can be left out. `octavo check`
also compares the length with the submission limits (`word_limit` and so on).

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
manuscript. `octavo review` exists so you can **read** the tracked changes and
comments; you apply them by hand in `paper.md`.

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

## Never, in a paper

- **Never write a coauthor's docx back into `paper.md`** (it pins the numbers).
- Never fix `main.typ` / `main.tex` inside `build/` (the one beside the manuscript is the original).
