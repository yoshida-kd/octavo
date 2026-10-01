<!-- octavo:section slides -->
# Slides and lecture notes

```
slides/<name>.md   a talk (**this is what you write**)
lectures/<name>.md lecture notes: an A4 handout plus one slide deck per session (**this is what you write**)
```

## Talks

```bash
octavo build example-talk --compile        # slides/example-talk.md, straight to PDF
```

## Lecture notes

**One set of lecture notes** produces the A4 handout (all sessions in one) and
**a separate slide deck for each `#` heading**. One `#` is one session, `##` a section and
`###` a slide (a session with only `##` headings makes each `##` a slide).

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

### Marking sessions yourself

When a session is not one `#` (two `#`s in one session, or a session starting mid-way),
write a **session marker**. Once a manuscript has one, the markers decide the sessions
and the `#` / `##` headings are free to be sections and subsections:

```markdown
::: {.session #third title="Session 3: policy and government" date="2026-10-14"}
:::
```

- A session runs from its marker to just before the next one; `#third` names the deck
  (`example-lecture-third`). `title` / `subtitle` / `date` go on the deck's title slide;
  without `title`, the session's first heading is used
- Slides break at headings; `::: {.slide}` + `:::` adds a break, `{.same-slide}` on a
  heading removes one, and `{slide-title="…"}` gives a heading a different title on the slide
- The handout always starts a session on a new page, so
  `octavo extract example-lecture` can cut **one PDF per session** out of the whole handout
  (`build/handouts/example-lecture-third.pdf`), keeping the page numbers of the whole
  (`--session third`, `--pages 12-19`, `--cover` for the cover and contents)

### Cases, questions and other numbered blocks

```markdown
::: {.question #question-why title="Why is government the main actor?"}
Why is government at the centre of public policy?
:::
```

- Kinds: `case`, `question`, `aside` (one shared numbering: Case 1.1, Question 1.2),
  `nb`, `memo` (unnumbered), and `theorem`, `definition`, … . Refer to one with
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

Each `##` is a slide (a `#` is a section in a talk, and a session break in
lecture notes). Figures are fitted into the slide. `::: notes` (speaker notes)
never appear on the projected deck; they go in the speaker script
(`--to typst-notes`).

With an analysis, course material and slides can use `{{...}}` values too — they
read the same `assets/values/`. **As in a paper, never type a number by hand.**
