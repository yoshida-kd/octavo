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

Each `##` is a slide (a `#` is a section in a talk, and a session break in
lecture notes). Figures are fitted into the slide. `::: notes` (speaker notes)
never appear on the projected deck; they go in the speaker script
(`--to typst-notes`).

With an analysis, course material and slides can use `{{...}}` values too — they
read the same `assets/values/`. **As in a paper, never type a number by hand.**
