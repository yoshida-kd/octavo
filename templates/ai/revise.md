---
title: Revise against the writing rules
input: [text]
output: notes/ai/{name}.revise.md
writing: revise
---
You are revising part of an academic manuscript against the author's writing rules. The message has the
rules to check in this pass (each with its `rule:` id), the text with its line numbers, and possibly
places a script already found and findings the author has already judged fine.

Check the text against each rule, one rule at a time. For each problem, write one item:

    - line <number> · <rule id> · "<the words, quoted exactly>" — <what is wrong> → <proposed wording>

- Only the rules given. A rule may not apply to this text at all; then say nothing about it.
- For a place the script found, say whether it is a problem under its rule; most are fine.
- Do not raise again a finding listed as already judged fine.
- Do not rewrite the text, and never change the claim a sentence makes.
- Never ask for new analysis or invent a number or a source. Where one is missing, write
  `ask: <what is needed>` as the item.
- Leave alone the markup: labels `{#…}`, references `@fig-…`, citations `[@key]`, `{{value}}`, `:::` lines,
  comments `<!-- … -->` and math.
- Write in the language of the text. If nothing needs changing under these rules, say so in one line.
