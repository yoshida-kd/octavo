# Writing support

> This is the source of the writing-support guide. Read it at **<https://yoshida-kd.github.io/octavo/writing/>**. <!-- pages:skip -->

Octavo can hand your AI assistant the rules you write by and the phrasings you trust, for the part of
the manuscript being written; it can hold a plan of the paragraphs before they are written, and show
afterwards where the text and the plan disagree. This page is how to set that up and use it, in the
order you meet it. It explains what Octavo does with the files, not what makes a good rule: what goes
in them is yours.

Octavo does not interpret a rule. It chooses the files, puts them in order, leaves out the ones that do
not apply and the entries you turned off, and prints the rest for the assistant to read.

---

## 1. Packs

### 1.1 Where packs go

A **pack** is a folder of Markdown files: `rules/` for how you write, `phrases/` for the phrase bank,
and an optional `pack.md`. Packs are looked for in two places:

| Place | For |
|---|---|
| `~/.config/octavo/writing/<pack>/` | every project on this machine |
| `<project>/notes/writing/<pack>/` | this project only (kept in git with it) |

A file with the same pack and file name in both places is taken from the project. Files placed
directly in `notes/writing/rules/` and `notes/writing/phrases/`, with no pack folder, form a pack
called `local`, which always comes last. An older project's `writing/` folder is still read
(`notes/writing/` wins over it).

```text
~/.config/octavo/writing/
  general/
    pack.md
    rules/
      sentences.md
      paragraphs.md
    phrases/
      paragraphs.md
  field/
    pack.md
    rules/
      results.md
    phrases/
      introduction.md
      results.md
```

If you keep your packs in a repository of their own, link the folder rather than copying it:

```bash
ln -s ~/projects/my-writing/packs ~/.config/octavo/writing
```

`octavo writing` lists what it found, with each file's pack, language, kinds of document and section.

```bash
octavo writing
```

### 1.2 pack.md

```markdown
---
title: Empirical papers in my field
extends: general
sections: [puzzle, cases]
---

Rules and phrases for empirical papers. Comes after `general` and wins where they disagree.
```

| Key | Meaning |
|---|---|
| `title` | the name shown in lists and in the sidebar (default: the folder name) |
| `extends` | packs that come before this one whenever it is used (a list, or one name) |
| `sections` | section names this pack adds to the built-in ones (see 3.4) |

The first paragraph of the body is the pack's description in the sidebar.

---

## 2. Writing the files

### 2.1 A file and its entries

A file starts with front matter; every `##` heading below it is one **entry**. A `##` inside a code
block is not a heading, and `###` belongs to the entry above it. Text between the front matter and the
first `##` is printed with the file (a good place for how the entries are meant to be used).

```markdown
---
title: Sentences
lang: en
applies: [paper, lecture]
---

How these rules are meant to be used, if it needs saying.

## One claim per sentence

Rule: Put one claim in a sentence.
Why: The reader need not look for where one claim ends.
Good: Staff numbers fell. How fast they fell differed between municipalities.
Bad: Staff numbers fell, but at different speeds across municipalities, which …
```

| Front matter | Values | When it is left out |
|---|---|---|
| `title` | the file's name in lists | the file name |
| `lang` | `en`, `ja` | the file is read for every language |
| `applies` | `paper`, `slides`, `lecture`, `poster`, `all` | `all` |
| `section` | a section name, or a list (see 3.4) | the file is always read |

### 2.2 Rules

A rule entry is printed as it is written; Octavo reads none of its lines. The lines below are the
convention the assistant is told about (AGENTS.md: "follow each rule's Rule").

| English | Japanese | |
|---|---|---|
| `Rule:` | `規則:` | what to do (the one line that matters) |
| `Why:` | `理由:` | why, so the assistant can judge a case the rule did not foresee |
| `Good:` | `良い例:` | an example that follows it |
| `Bad:` | `悪い例:` | an example that breaks it |

Any other line (a `Source:`, a note of your own) is printed too.

### 2.3 Phrases

A phrase entry is one situation, or one **kind of paragraph**, with the frames you may use there as a
list. Parts in 〈 〉 are filled in; `〈A / B〉` is a choice between the words given.

```markdown
---
title: Results
lang: en
applies: [paper]
section: results
---

## The main result

When: The paragraph that reports the main estimate.
Contains: the table or figure; the estimate and its uncertainty; what it means for the hypothesis
Note: Say what the reader should see, then the estimate.
Source: own
- Open: Table 〈2〉 〈presents / reports〉 〈the estimates from X〉.
- Body: The coefficient on 〈X〉 is 〈positive〉 and 〈statistically〉 significant.
- Close: 〈These results〉 provide support for 〈H1〉.
```

| Line | Japanese | What Octavo does with it |
|---|---|---|
| `When:` | `場面:` | printed; also `when` in `--json` |
| `Note:` | `注意:` | printed; also `note` in `--json` |
| `Source:` | `出典:` | printed; also `source` in `--json` |
| `- Open:` / `- Body:` / `- Close:` | (the same) | printed; each is a frame with its place in the paragraph (`position` in `--json`) |
| `- ` any other list item | | printed; a frame with no place |
| `Contains:` | | printed; also `contains` in `--json` |
| any other line | | printed as it is; not read |

The field names are matched at the start of a line, with `:` or `：`. Frames — the list items — are
what `octavo outline --paragraphs` looks for in the text (5.1).

---

## 3. Choosing what a manuscript reads

### 3.1 Packs and their order

Without a choice, every pack found is used. To choose, list them **most general first**: where two
disagree, the later one wins. A pack's `extends` are put in front of it on their own.

In `octavo.config.py`, for the whole project:

```python
CONFIG = {
    'writing': ['general', 'field'],
}
```

and at the top of a manuscript, for that manuscript:

```markdown
---
title: My paper
writing: [field]
---
```

The manuscript's `writing:` replaces the project's for that manuscript. `local` is always added last.
In the sidebar: the manuscript's **Writing rules** → **Choose the Packs…**, one at a time, most general
first.

### 3.2 Turning entries off

`writing_off` names what not to use:

| Written | Turns off |
|---|---|
| `field/results` | the whole file `results.md` of the pack `field` |
| `results` | the file `results.md` in whichever pack has it |
| `field/results#the-main-result` | one entry |
| `results#the-main-result` | that entry in whichever pack has it |

```markdown
---
writing_off: [general/sentences#one-claim-per-sentence]
---
```

Unlike other settings, the project's `writing_off` and the manuscript's are **added together**. The
part after `#` is the entry's heading made into a **slug**: lower case, every run of characters other
than letters and digits turned into `-` (`## One claim per sentence` → `one-claim-per-sentence`; a
second entry with the same heading gets `-2`). **Changing a heading changes its slug**, and the entry
comes back on; `octavo check` then reports `writing_off names nothing`. In the sidebar, right-click an
entry → **Turn Off for This Manuscript**.

### 3.3 Which files are read

| The file has | It is read |
|---|---|
| no `section:` | always |
| `section: results` | only when writing the results section |
| `applies:` not matching the manuscript | never for this manuscript |
| `lang:` other than the manuscript's | never for this manuscript |

What kind of document a manuscript is comes from its outputs: a paper or a handout without sessions
(or one with `word` / `tex`) is `paper`; notes with sessions `lecture`; slides, scripts and Beamer
`slides`; a poster `poster`. One manuscript can be several.

### 3.4 The section of a line

When the assistant asks for a line (`--file … --line …`), Octavo goes up from the nearest heading
above it to shallower ones and takes the first heading that names a section. Within a heading, the
word that comes first wins (`Results and robustness` → `results`). A pack's own sections are tried
before the built-in ones. A heading with `{.appendix}`, anything after it, and the appendix file are
`appendix`.

| Section | Headings that name it (any part of the heading, any case) |
|---|---|
| `abstract` | abstract, 要旨, 概要 |
| `introduction` | introduction, overview, はじめに, 序論, 問題の所在 |
| `literature` | literature, previous research, prior research, existing research, related work, background, 先行研究 |
| `theory` | theor…, hypothes…, argument, framework, expectation, 理論, 仮説 |
| `design` | data, method, research design, empirical strategy, identification, measure, variable, estimation, sample, case selection, design, データ, 方法, 手法, リサーチデザイン, 分析の枠組み |
| `results` | result, finding, analysis, estimate, evidence, 結果, 分析 |
| `discussion` | discussion, robustness, sensitivity, limitation, mechanism, 考察, 頑健性, 限界 |
| `conclusion` | conclu…, implication, おわりに, 結論, 結び |
| `appendix` | appendix, supplement, 付録 |

A section a pack adds (`sections: [puzzle]`) is named by its own words (`puzzle`; `case-selection`
matches "case selection"). A heading that names no section reads only the files with no `section:`.

### 3.5 Seeing what is read

```bash
octavo writing --for my-paper
octavo writing --for my-paper --section results --print
octavo writing --file docs/my-paper/my-paper.md --line 120 --print
```

The first lists the packs and files a manuscript uses; `--print` prints them layered, which is what the
assistant reads; `--all` takes every section. In VS Code: put the cursor in the manuscript and run
**Show the Rules for Where the Cursor Is** (the editor's right-click menu, or the manuscript's
**Writing rules** in the sidebar).

---

## 4. The paragraph plan

### 4.1 Marks

When a pack's phrase bank is written as kinds of paragraph, a section can be planned before it is
drafted: one mark directly above each paragraph, with its kind and the one sentence it claims.

```markdown
## Results {#sec-results}

<!-- para: field/results#the-main-result | Divisions that changed more were redrawn more often -->
Divisions whose composition of work had shifted more were redrawn more often (@tbl-main).

<!-- para: field/results#the-size-of-the-effect | The effect is about a third of the mean -->

<!-- para: | Robust to dropping the largest ministries -->
```

- The kind is a phrase entry, written like `writing_off` (`pack/file#slug`, or `file#slug`, taken from
  the later pack when two have it). Both parts are optional: `<!-- para: | claim -->` has no kind yet.
- The paragraph's text starts **on the line right after** the mark. A mark followed by a blank line is
  a paragraph not yet written: the plan.
- **Leave a blank line before a mark.** A mark right after a line of text is read by pandoc as part of
  the paragraph above, joining the two.
- Marks are comments: they never reach the PDF, the slides or Word.

### 4.2 Which command for which step

| Step | Command | Phrases printed |
|---|---|---|
| planning a section | `octavo writing --for DOC --section S --print` | every kind for that section, to choose from |
| writing one paragraph | `octavo writing --file F --line N --print` on its mark | that kind's entry only |
| naming kinds directly | `octavo writing --for DOC --kind field/results#the-main-result --print` | those entries |

With a kind, the rules are the same as without one; only the phrases narrow. `--kind` may be given more
than once, or with commas. A kind is looked for in the phrase files this manuscript uses — the chosen
packs, `applies` and `lang` matching, not turned off — whatever their section; a kind from a file it
does not use is left out with a warning.

---

## 5. After drafting

### 5.1 The outline

```bash
octavo outline my-paper --paragraphs
```

lists each paragraph under its heading: the kind, the claim and the first sentence of the text, so you
can see whether the text says what the plan says. It marks:

| Mark | Meaning |
|---|---|
| no kind | a paragraph of text without a mark, or a mark without a kind |
| unknown kind | a kind no chosen pack has (a near name is suggested) |
| a kind this manuscript does not use | the kind exists, but its file's `applies` or `lang` does not match, or it is turned off |
| no text yet | a mark with no paragraph under it |
| needs a blank line | a mark right after a line of text |
| the third in a row | a note: three paragraphs of one kind in a row under one heading (two is normal) |

and notes a frame used twice under one heading. A frame counts as used when every word outside 〈 〉
appears in order within one sentence (`〈A / B〉`: one of the words); a frame starting with a capital
must start the sentence, one ending in `.` must end it; frames with fewer than two fixed words are not
looked for. Only frames this manuscript uses, of the heading's own section (or of files with no
`section:`), are compared.

### 5.2 Questions for the author

Where the text needs a number or a source that is in neither the manuscript nor the analysis, the
assistant is told to leave a question instead of writing around it:

```markdown
<!-- ask: the number of ministries in the sample -->
```

`octavo outline … --paragraphs` lists the questions with their lines, and `octavo check` shows
**questions for the author** as a warning until each is answered and deleted.

---

## 6. Letting the assistant use it

- **The project's AGENTS.md** (written by `octavo init`) tells the assistant to run `octavo writing
  --file … --line … --print` before writing or revising prose, to follow the rules, to use the phrase
  bank only where a frame fits, to plan with marks and check with the outline, to leave `ask` comments,
  and not to edit the pack files. A project made before these sections existed gets them with:

```bash
octavo migrate --rules
```

- **The sidebar**: each manuscript's **Writing rules** shows the packs it uses, their files and
  entries. **Choose the Packs…** sets `writing:` for that manuscript; right-click an entry to turn it
  off or back on; **Show the Rules for Where the Cursor Is** shows what the assistant reads at the
  cursor.
- `octavo check` has a **writing rules** row when there are packs: unknown pack and section names, and
  `writing_off` entries that name nothing.

---

## 7. When something goes wrong

| What you see | Why, and what to do |
|---|---|
| `octavo writing` says there are no rules | Octavo 0.6.8 or earlier has no packs (update it with Set up); or the packs are not under `~/.config/octavo/writing/<pack>/` or `notes/writing/<pack>/` — a link that points one folder too high or too low shows nothing (each pack folder needs `rules/`, `phrases/` or `pack.md`) |
| a file never appears for a manuscript | its `applies:` or `lang:` does not match the manuscript (3.3); `octavo writing --for DOC --all` lists the files left out with `- ` |
| a file's section is never read | the heading above the line names no section (3.4), or the section name is mistyped: `octavo check` warns about an unknown section |
| `no writing pack called …`, `extends …, but there is no pack called …` | a name in `writing` or in a pack's `extends` that no folder has |
| `writing_off names nothing` | the entry's heading changed, so its slug changed (3.2); copy the new id from `octavo writing --for DOC --json` or turn it off again from the sidebar |
| `needs a blank line before the mark` | put an empty line between the text above and the mark (4.1) |
| `unknown kind` | the kind is mistyped, or its pack is not chosen for this manuscript |
| `a kind this manuscript does not use` | the kind's file has `applies` / `lang` that do not fit this manuscript, or it is in `writing_off` |
