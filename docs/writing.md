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

A rule entry is printed as it is written; Octavo reads only its `Flag:` lines (below). The other lines
are the convention the assistant is told about (AGENTS.md: "follow each rule's Rule").

| English | Japanese | |
|---|---|---|
| `Rule:` | `規則:` | what to do (the one line that matters) |
| `Why:` | `理由:` | why, so the assistant can judge a case the rule did not foresee |
| `Good:` | `良い例:` | an example that follows it |
| `Bad:` | `悪い例:` | an example that breaks it |
| `Flag:` | `検出:` | a regular expression; the manuscript lines it matches are listed as places to reread |

Any other line (a `Source:`, a note of your own) is printed too.

**`Flag:`** is for a rule about a word that can only be checked where the word appears ("effect",
"significant", a sentence opening with "Moreover,").

```markdown
## "Effect" for a causal estimate only

Rule: Write "effect" only where the design identifies one; otherwise "association" or "difference".
Flag: \beffects?\b
Flag: (?i)\bimpacts?\b
```

- One regular expression per line, as many `Flag:` lines as needed; Python's `re` syntax. Upper and
  lower case differ unless the expression starts with `(?i)`. It is tried on each line of the
  manuscript, so `^` is the start of a line (with one sentence per line, the start of a sentence).
  It may be wrapped in `` ` `` so that Markdown shows it as written.
- A rule in a file with `section:` flags only lines of that section.
- Headings, code, comments, display math, `{{values}}`, citations and labels (`@key`, `{#sec-x}`) and
  link targets are not searched.
- A match is **a place to reread, not an error**: the word is flagged wherever it appears, right or
  wrong. The list is in 5.1.

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
| `Repeat: yes` | `繰り返し: yes` | printed; paragraphs of this kind normally follow one another, so the outline does not note a run of them (5.2) |
| any other line | | printed as it is; not read |

The field names are matched at the start of a line, with `:` or `：`. Frames — the list items — are
what `octavo outline --paragraphs` looks for in the text (5.2).

A phrase file whose entries are **the sentences of one paragraph, in order** (an abstract: the
question, the evidence, the finding, why it matters) says so at the top with `entries: sentences`.
Its entries are not kinds of paragraph, so where every phrase file for a section says this, the outline
does not ask that section's paragraphs for a kind.

### 2.4 When a rule is read, where it applies, and its id

A file's rules are read whenever its section is written. Some rules are better checked after drafting
than kept in mind while drafting, and some are notes on one word that matter only where the word is
used. A few more lines say so. Octavo reads them and leaves them out of what the assistant reads.

```markdown
## Doubled hedges
Id: doubled-hedges
Stage: revise
Rule: Keep one hedge where there are two.
Why: Two hedges read as doubt about the finding, not as caution.
Bad: The results may possibly suggest a link.
Good: The results may suggest a link.
Flag: (?i)\bmay possibly\b
Count: `(?i)\b(may|might|perhaps|possibly)\b` per paragraph > 2
```

| Line | Japanese | Values | Without it |
|---|---|---|---|
| `Stage:` | `段階:` | `draft`: read while drafting, and checked when revising. `revise`: only when revising (5.1). `lookup`: read only where its `Flag:` matches the manuscript (a usage note on one word) | `draft`, or the file's `stage:` |
| `Scope:` | `範囲:` | `sentence`, `paragraph`, `first-sentence`, `last-sentence` (the `Flag:` is tried on that sentence of each paragraph only), `section`, `document` (what the assistant is given with the rule when revising) | `sentence`, or the file's `scope:` |
| `Section:` | `節:` | a section or a list, for this entry only | the file's `section:` |
| `Id:` | | a fixed name for the entry, used in place of the slug of its heading. The old slug and any `Alias:` (`別名:`) still work | the heading's slug |
| `Replaces:` | `置き換え:` | `pack/file#id` of a more general pack: that entry is left out while this one is used | |
| `Count:` | `数える:` | `<regular expression> per sentence`, `per paragraph` or `per section`, then `> N`: a place to reread where it matches more than N times | |

- `Good:` and `Bad:` may be repeated, with one example each, or followed by `- ` lines. An exception
  goes on a line of its own, such as `Except:`, which is printed like any other line.
- Give an entry an `Id:` before projects turn it off by name; after that, its heading can change.
- `octavo writing --check` tries each `Flag:` on its rule's examples (6.1).

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
| no `section:`, with `--section-only` | left out (it was read at the first section) |
| `applies:` not matching the manuscript | never for this manuscript |
| `lang:` other than the manuscript's | never for this manuscript |

What kind of document a manuscript is comes from its outputs: a paper or a handout without sessions
(or one with `word` / `tex`) is `paper`; notes with sessions `lecture`; slides, scripts and Beamer
`slides`; a poster `poster`. One manuscript can be several.

### 3.4 The section of a line

When the assistant asks for a line (`--file … --line …`), Octavo goes up from the nearest heading
above it to shallower ones and takes the first heading that names a section. A heading names a
section by its label or by its words. Within a heading, the
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

**A heading that says what the section argues** has none of these words. Give it the section as its
label, which comes first:

```markdown
# Adding Capacity When the Volume of Work Rises {#sec-literature}
```

`{#sec-literature}`, `{#sec-literature-2}` and a shortening such as `{#sec-intro}` all name the
section; any other label is read like the heading's words (`{#sec-data}` → `design`). When a line's
heading names no section, `octavo writing --file … --line …` says so — otherwise the section's rules
and phrases would be missing without a word — and `--section NAME` gives the section by hand.

### 3.5 Seeing what is read

```bash
octavo writing --for my-paper
octavo writing --for my-paper --section results --print
octavo writing --for my-paper --section discussion --section-only --print
octavo writing --file docs/my-paper/my-paper.md --line 120 --print
```

The first lists the packs and files a manuscript uses; `--print` prints them layered, which is what the
assistant reads; `--all` takes every section. `--section-only` leaves out the files with no
`section:` — the larger part, and the same for every section — so that moving on to another section
prints only what that section adds. In VS Code: put the cursor in the manuscript and run
**Show the Rules for Where the Cursor Is** (the editor's right-click menu, or the manuscript's
**Writing rules** in the sidebar).

### 3.6 Keeping a pack's version

A pack you keep improving changes for every project at once. When the packs are in a git repository,
tag a version and name it with `@` where the pack is chosen:

```bash
git -C ~/projects/writing tag academic-en@v1
```

```python
CONFIG = {
    'writing': ['academic-en@v1', 'field'],
}
```

`academic-en@v1` reads the pack as it was at the tag `academic-en@v1` (else a tag or commit `v1`) of
the repository the pack is in, and keeps doing so however the pack's folder changes; `field`, with no
`@`, is read as it is now. A pack's `extends` can name a version the same way; a version in `writing`
wins. Files a project adds to the same pack in `notes/writing/<pack>/` are still layered on top. If
the version is not found, the pack is not used and Octavo warns — it never falls back to the folder as
it is now. `octavo writing` lists each pack's tagged versions. Moving a project on is changing `@v1` to
`@v2`.

The version read is written out under `~/.cache/octavo/writing/` (safe to delete). Git is needed.

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
- **One claim over two or three paragraphs** ("First, … / Second, …" set apart, or a paragraph that
  goes on after a table): mark the later ones `<!-- para: + -->`. Each continues the mark above it
  under the same heading and takes its kind; a claim of its own is optional (`<!-- para: + | claim -->`).

```markdown
<!-- para: field/theory#the-mechanism | Shifts in work make the old divisions costly -->
First, a division built for one kind of work ...

<!-- para: + -->
Second, the people who know the old work ...
```

- A mark may stand above a quotation (`> **H1.** …`, a displayed hypothesis) or a list; the block then
  counts as a paragraph. Without a mark, quotations and lists are not paragraphs.

### 4.2 Which command for which step

| Step | Command | Phrases printed |
|---|---|---|
| planning a section | `octavo writing --for DOC --section S --print` | every kind for that section, to choose from |
| moving on to another section | `octavo writing --for DOC --section S --section-only --print` | that section's files only, without the rules and phrases already read |
| writing one paragraph | `octavo writing --file F --line N --print` on its mark | that kind's entry only |
| naming kinds directly | `octavo writing --for DOC --kind field/results#the-main-result --print` | those entries |

With a kind, the rules are the same as without one; only the phrases narrow. `--kind` may be given more
than once, or with commas. A kind is looked for in the phrase files this manuscript uses — the chosen
packs, `applies` and `lang` matching, not turned off — whatever their section; a kind from a file it
does not use is left out with a warning.

---

## 5. Revising

### 5.1 octavo revise

```bash
octavo revise my-paper
octavo revise my-paper --section results --print
```

`octavo revise` gathers every place to reread in one manuscript into one list. It takes the matches of
the rules' `Flag:` and `Count:`, the usage notes whose word appears, the paragraph plan (5.2), the
questions (5.3), numbers typed into the prose, lines broken in the middle of a sentence, and the
sections of the other-language version that are behind. It also counts a few things itself:

| Check | What it reports |
|---|---|
| `octavo/long-sentence` | a sentence of more than 40 words (`revise_sentence_words`), or more than 100 characters in Japanese (`revise_sentence_chars`); 0 turns it off |
| `octavo/repeated-ending` | three Japanese sentences in a row with the same ending (〜である。) |
| `octavo/repeated-opening` | three sentences of a paragraph, or three paragraphs under one heading, that open the same way (This …, また、) |
| `octavo/abbreviation` | an abbreviation used before its definition, as in `regression discontinuity design (RDD)` |
| `octavo/term-variant` | a spelling listed under `variants` in `notes/writing/terms.csv` |

```csv
en,ja,variants
data set,データセット,dataset; data-set
```

Like a `Flag:`, each is a place to reread, not an error. Octavo never changes the text.

**Each run is a pass, and the passes are recorded** in `docs/<name>/revise.json` (keep it in git).

- A finding that was not there in the last pass is marked `*`.
- If a finding needs no change, `octavo revise my-paper --fine <key>` hides it until its sentence
  changes.
- A finding that disappears because you edited its paragraph is counted as fixed.

So the next pass shows what is new and what is still open. Over many passes, the record shows which
rules earn their place (6.2).

`--print` is what the assistant reads to revise:

- the rules to check, in passes of at most eight, grouped by their `Scope`, each with its id;
- the paragraphs changed since the last pass, with their line numbers (for rules about the whole
  manuscript, the headings and each paragraph's claim and first sentence instead);
- the places Octavo found;
- the findings already judged fine.

The assistant lists its findings with the line and the rule's id, and changes nothing until you have
decided. When you decide on one of its findings, it records your decision with `--verdict`
(AGENTS.md says so).

`octavo ai run revise docs/my-paper/my-paper.md` sends the same passes to the AI set up for
`octavo ai`, one request per pass; a local model handles a short list of rules better than a long one.
`octavo ai run proofread` sends the rules along with the passage.

### 5.2 The outline

```bash
octavo outline my-paper --paragraphs
octavo outline my-paper --paragraphs --contains --lines 60-120
```

lists each paragraph under its heading: the kind, the claim and the first sentence of the text, so you
can see whether the text says what the plan says. It marks:

| Mark | Meaning |
|---|---|
| no kind | a paragraph of text without a mark, or a mark without a kind (not in a section whose phrases are `entries: sentences`, 2.3) |
| continues nothing | a `<!-- para: + -->` with no mark above it under its heading |
| unknown kind | a kind no chosen pack has (a near name is suggested) |
| a kind this manuscript does not use | the kind exists, but its file's `applies` or `lang` does not match, or it is turned off |
| no text yet | a mark with no paragraph under it |
| needs a blank line | a mark right after a line of text |
| the third in a row | a note: three paragraphs of one kind in a row under one heading (two is normal). A `+` paragraph counts with the one it continues; a kind with `Repeat: yes` is never noted |

`--contains` adds, under each paragraph, the `Contains:` line of its kind, to read the paragraph
against after drafting (does it have each part?). Octavo only puts the two side by side.
`--lines 60-120` keeps the paragraphs in those lines, for checking one section at a time.

The outline also notes a frame used twice under one heading. A frame counts as used when every word outside 〈 〉
appears in order within one sentence (`〈A / B〉`: one of the words); a frame starting with a capital
must start the sentence, one ending in `.` must end it; frames with fewer than two fixed words are not
looked for. Only frames this manuscript uses, of the heading's own section (or of files with no
`section:`), are compared.

### 5.3 Questions for the author

Where the text needs a number or a source that is in neither the manuscript nor the analysis, the
assistant is told to leave a question instead of writing around it:

```markdown
<!-- ask: the number of ministries in the sample -->
```

`octavo outline … --paragraphs` lists the questions with their lines, and `octavo check` shows
**questions for the author** as a warning until each is answered and deleted.

### 5.4 Places to reread, rule by rule

```bash
octavo writing --for my-paper --flags
```

lists, rule by rule, the lines of the manuscript and its appendix that a rule's `Flag:` matches (2.2),
with their line numbers (it does not apply `Scope:`; `octavo revise` does). `octavo check` gives only
the count (**places to reread**), never as a warning, and `--strict` does not fail on it. `--file F` in
place of `--for` lists one file.

---

## 6. Improving the packs

### 6.1 Checking a pack

```bash
octavo writing --check
octavo writing --check --pack-dir ~/projects/writing/packs
```

checks every pack: field values it does not know, a `Flag:` or `Count:` that is not a regular
expression, an `Id:` used twice, a `Replaces:` that names no entry, a `Stage: lookup` without a
`Flag:`. It also tries each `Flag:` on its rule's examples: **a `Flag:` that misses a `Bad:` example is
a problem**; one that matches a `Good:` example is only a note, since a correct use may contain the
word. With `--pack-dir`, it checks the packs in a folder outside any project (where you keep and edit
them). It exits with 1 when there is a problem, so it can run before you publish a change to a pack.

### 6.2 What the record says

```bash
octavo writing --stats
```

adds up, rule by rule, what the passes of `octavo revise` recorded: how often each rule was found,
fixed, and judged fine. It also lists the rules with a `Flag:` or `Count:` that never matched.

| What you see | What it suggests |
|---|---|
| never found | the `Flag:` is too narrow, or the problem does not occur in your writing |
| mostly judged fine | the rule or its `Flag:` is too broad: narrow it, or make it a `Stage: lookup` note |
| mostly fixed | the rule earns its place; perhaps make it a drafting rule |

### 6.3 Rules from your own revisions

```bash
octavo writing --harvest v1-draft --for my-paper > notes/writing/harvest.md
octavo ai run suggest-rules notes/writing/harvest.md
```

Manuscripts are written one sentence per line, so the difference between a git version and now is a
list of sentences before and after you revised them. Commit a draft (the assistant's, or your own),
revise it, then run `--harvest` with that commit. `--docx` adds a coauthor's tracked changes and
comments. The `suggest-rules` task (or the assistant in chat) groups the revisions by pattern and
proposes candidate entries in the pack's form, quoting your before and after as `Bad:` and `Good:`.
They are candidates: you decide which become rules and where they go. Octavo never writes to a pack.

---

## 7. Letting the assistant use it

- **The project's AGENTS.md** (written by `octavo init`) tells the assistant to run `octavo writing
  --file … --line … --print` before writing prose, to follow the rules, to use the phrase bank only
  where a frame fits, to plan with marks and check with the outline, to leave `ask` comments, and not
  to edit the pack files. For revising, it tells the assistant to run `octavo revise … --print`, to
  list findings without rewriting until you decide, and to record your decisions. A project made before these sections existed gets them with:

```bash
octavo migrate --rules
```

- **The sidebar**: each manuscript's **Writing rules** shows the packs it uses, their files and
  entries. **Choose the Packs…** sets `writing:` for that manuscript; right-click an entry to turn it
  off or back on; **Show the Rules for Where the Cursor Is** shows what the assistant reads at the
  cursor. **Revising** lists the places `octavo revise` finds; click one to go to its line, or
  right-click it to mark it as needing no change.
- `octavo check` has a **writing rules** row when there are packs: unknown pack and section names,
  `writing_off` entries that name nothing, a `Flag:` that is not a regular expression, and the number
  of problems `octavo writing --check` finds.

---

## 8. When something goes wrong

| What you see | Why, and what to do |
|---|---|
| `octavo writing` says there are no rules | Octavo 0.6.8 or earlier has no packs (update it with Set up); or the packs are not under `~/.config/octavo/writing/<pack>/` or `notes/writing/<pack>/` — a link that points one folder too high or too low shows nothing (each pack folder needs `rules/`, `phrases/` or `pack.md`) |
| a file never appears for a manuscript | its `applies:` or `lang:` does not match the manuscript (3.3); `octavo writing --for DOC --all` lists the files left out with `- ` |
| a file's section is never read | the heading above the line names no section (3.4), or the section name is mistyped: `octavo check` warns about an unknown section |
| `no writing pack called …`, `extends …, but there is no pack called …` | a name in `writing` or in a pack's `extends` that no folder has |
| `… no version v1 …; the pack is not used` | the tag is missing or mistyped, or the pack is not in a git repository (3.6); `git tag --list` where the pack is shows the versions |
| `writing_off names nothing` | the entry's heading changed, so its slug changed (3.2); copy the new id from `octavo writing --for DOC --json` or turn it off again from the sidebar. Giving the entry an `Id:` prevents this (2.4) |
| a rule never comes when drafting | it has `Stage: revise` or `Stage: lookup` (2.4): it comes with `octavo revise`, or where its word appears |
| `octavo revise` shows no text in `--print` | no paragraph changed since the last pass; `--all` shows every paragraph |
| `needs a blank line before the mark` | put an empty line between the text above and the mark (4.1) |
| `unknown kind` | the kind is mistyped, or its pack is not chosen for this manuscript |
| `a kind this manuscript does not use` | the kind's file has `applies` / `lang` that do not fit this manuscript, or it is in `writing_off` |
