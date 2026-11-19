---
title: Suggest writing rules from revisions
input: [text]
output: notes/ai/{name}.suggest-rules.md
---
The message lists sentences of an academic manuscript before and after the author revised them (from
`octavo writing --harvest`), and perhaps a coauthor's changes and comments. Find the revisions that follow
a pattern a writing rule could state, and propose candidate rules.

- Group the revisions by pattern. Propose a rule only for a pattern seen at least twice, or for a single
  revision that plainly states a general principle. Ignore changes of content (new facts, numbers,
  citations) and one-off corrections of typing errors.
- Write each candidate in this form, in the language of the manuscript:

      ## <a short name for the rule>
      Rule: <one sentence that can be checked against a sentence>
      Why: <one sentence>
      Bad: <a "Before" sentence, quoted>
      Good: <its "After" sentence, quoted>
      Source: harvest <the ids, such as H3, H7>

  Add `Stage: revise` when the rule is a check to make after drafting rather than something to keep in
  mind while drafting. Add `Flag: <a Python regular expression>` only when a word or phrase reliably marks
  the places to reread: it must match the Bad sentence and not the Good one.
- These are candidates for the author to judge. Do not claim more than the revisions show.
