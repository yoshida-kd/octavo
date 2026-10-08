<!-- octavo:section slides -->
# Slides and lecture notes

```
docs/<name>/<name>.md   a talk (outputs: [slides]) or lecture notes (outputs: [pdf, slides], sessions: true)
```

## Talks

```bash
octavo build example-talk --compile        # docs/example-talk/example-talk.md, straight to PDF
```

## Lecture notes

**One set of lecture notes** produces the A4 handout (all sessions in one) and
**a separate slide deck for each `#` heading**. One `#` is one session, `##` a section and
`###` a slide (a session with only `##` headings makes each `##` a slide).

```bash
octavo build example-lecture --to pdf --compile      # A4 handout, straight to PDF
octavo build example-lecture --to slides --compile   # one PDF deck per session
octavo build example-lecture-03 --to slides          # just the third session
```

- Session decks are named `<notes name>-01`, `-02`, … in order of the `#` headings (the PDF is
  `build/slides/<notes name>-slides-01.pdf`).
  **Inserting a session renumbers the ones after it**, so give a heading an id
  to pin its name: `# Second session {#second}` → `example-lecture-second`
- A session deck's title slide takes the `#` heading as its title and the notes'
  title as its subtitle
- Anything before the first `#` goes into the handout only

### Marking sessions yourself

When a session is not one `#` (two `#`s in one session, or a session starting mid-way),
write a **session marker**. Once a manuscript has one, the markers decide the sessions
and the `#` / `##` headings are free to be sections and subsections:

```markdown
\session{Session 3: policy and government} {#third date="2026-10-14"}
```

- A session runs from its marker to just before the next one; `#third` names the deck
  (`example-lecture-third`). the title in `\session{…}` and `subtitle` / `date` go on the deck's title slide;
  without a title (`\session{}`), the session's first heading is used. The older
  `::: {.session …}` + `:::` means the same
- Normally everything goes on the slides (handout-only material is `.no-slides`). With
  `slides_select: marked` at the top, the slides get only what is marked `.on-slides` (blocks,
  sections whose heading has it, `[…]{.on-slides}`) and the headings above it — in such a
  document, mark what should be on the slides
- Slides break at headings; `\newslide` (`\newslide{Title}`) on a line of its own adds a break, `{.same-slide}` on a
  heading removes one, and `{slide-title="…"}` gives a heading a different title on the slide
- The handout always starts a session on a new page, so
  `octavo build example-lecture --sessions` can cut **one PDF per session** out of the whole handout
  (`build/handouts/example-lecture-third.pdf`), keeping the page numbers of the whole
  (`--session third`, `--pages 12-19`, `--cover` for the cover and contents)

### Cases, questions and other numbered blocks

```markdown
::: {.question #question-why title="Why is government the main actor?"}
Why is government at the centre of public policy?
:::
```

- Kinds: `case`, `question` (one shared numbering: Case 1.1, Question 1.2),
  `aside`, `nb`, `memo` (unnumbered), and `theorem`, `definition`, … . Refer to one with
  `@question-why` → "Question 1.2" (the label starts with the kind)
- `::: {.restate #question-why}` + `:::` repeats it elsewhere with its number and a link
  back; `::: {.list-of .question}` + `:::` lists them all (`.titles` for titles only).
  **Write a block once; never copy its text**

### The handout's layout

`first_section: 0` in the notes' front matter numbers the first section 0 (a guidance
session); `date: today` prints the day it was built. The cover is a page of its own, the
contents are numbered i, ii, and the body starts at 1. The type follows the Japanese LaTeX
class jsarticle; the whole layout is `templates/handout/handout.typ`
(`octavo template copy handout/handout.typ` to change it).

Conditional blocks decide what goes where (`.no-slides` for the handout only — PDF, Word and
LaTeX; `.slides-only`; `.pdf-only` for the PDF alone; inside a line, `[…]{.slides-only}`).

```markdown
::: {.no-slides}
handout only (fill-in blanks, longer notes)
:::

::: {.slides-only}
slides only (figures, short prompts)
:::
```

## Common to all slides

A slide is the level just below the shallowest heading (a talk: `#` section, `##` slide;
lecture notes: `#` session, `##` section, `###` slide; with one level only, that level).
Figures are fitted into the slide. A slide that does not fit runs onto the next page and
`octavo build` says so — split it with `\newslide` or shorten it. `::: notes` (speaker notes)
never appear on the projected deck; they go in the speaker script
(`--to script`).

With an analysis, course material and slides can use `{{...}}` values too — they
read the same `assets/values/`. **As in a paper, never type a number by hand.**
