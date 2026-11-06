# Quick guide

> This is the source of the quick guide. Read it at **<https://yoshida-kd.github.io/octavo/quickstart/>**. <!-- pages:skip -->

From installing Octavo to your first PDF, in six short steps, all in VS Code. Every step has a
longer version in the [guide](https://yoshida-kd.github.io/octavo/guide/).

## 1. Install

1. Install [VS Code](https://code.visualstudio.com/), then the **Octavo** extension from the
   [Marketplace](https://marketplace.visualstudio.com/items?itemName=yoshida-kd.octavo).
2. Open a folder. The extension checks your tools and offers **Set up**. Press it.
3. When it finishes, you are done. R, Python, Quarto, pandoc, Typst, the fonts and the
   `octavo` command are installed.


On Windows, WSL is recommended. The steps for each system, and for a terminal, are in
[Installing Octavo](https://yoshida-kd.github.io/octavo/install/).

## 2. Make a project

Open an empty folder and press **New project** in the Octavo sidebar. Choose
the parts you need (an analysis in R or Python, a paper, slides, lecture notes, a poster)
and whether to fill them with examples.


## 3. Write

Hand a number from the analysis to the manuscript by name. In the analysis (`.qmd`):

```r
ov_value("n_obs", nrow(d))
ov_figure(p, "trend")
```

In the manuscript (`docs/paper/paper.md`), call them by name and refer to the figure by its label:

```markdown
---
title: Title of the Paper
outputs: [pdf]
---

# Analysis {#sec-analysis}

We analyse {{n_obs}} observations. @fig-trend shows the trend.

![Trend](../../assets/figures/trend.png){#fig-trend}
```

You never type a result or a number: `{{n_obs}}` and `@fig-trend` are filled in when the
document is built, and they stay right when you re-run the analysis or reorder sections.

## 4. Build

Open the manuscript and press the **PDF** button at the top right of the editor.
The PDF appears beside it, follows your cursor and is rebuilt on every save.

To get slides, a handout, a poster or a Word file as well, list them in the manuscript's
`outputs:`, for example `outputs: [pdf, slides, word]`.


## 5. Check

In the Octavo sidebar, press **Check before submitting (check)** under Tools. It finds missing
figures and citations, numbers typed by hand and word limits.


## 6. Use an AI assistant

Every project has an `AGENTS.md` with its working rules: never type a result into the
manuscript, never edit `data/raw`, never edit what is generated. Claude Code, GitHub Copilot,
Codex and Antigravity read it on their own, so you can ask the assistant to write the analysis
or the manuscript and it works the Octavo way from the start; anything this guide has no button
for (an anonymous version, a package for the journal), ask it too. **Check before submitting**
catches anything that slips through. More in
[the guide](https://yoshida-kd.github.io/octavo/guide/#10-working-with-an-ai-assistant).

## 7. Where next

- [The guide](https://yoshida-kd.github.io/octavo/guide/): everything in detail.
- [The reference](https://yoshida-kd.github.io/octavo/reference/): every command and setting, for
  your AI assistant.
- [Making course materials](https://yoshida-kd.github.io/octavo/lectures/): a handout and a deck
  per session from one file.
