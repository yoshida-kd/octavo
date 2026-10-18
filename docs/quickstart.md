# Quick guide

> This is the source of the quick guide. Read it at **<https://yoshida-kd.github.io/octavo/quickstart/>**. <!-- pages:skip -->

From installing Octavo to your first PDF, in six short steps. Every step has a longer
version in the [guide](https://yoshida-kd.github.io/octavo/guide/).

## 1. Install

**With VS Code** (the easy way):

1. Install [VS Code](https://code.visualstudio.com/), then the **Octavo** extension from the
   [Marketplace](https://marketplace.visualstudio.com/items?itemName=yoshida-kd.octavo).
2. Open a folder. The extension checks your tools and offers **Set up**. Press it.
3. When it finishes, you are done. R, Python, Quarto, pandoc, Typst, the fonts and the
   `octavo` command are installed.

<details>
<summary><strong>From a terminal</strong> (Linux and macOS)</summary>

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install octavo-kit
octavo setup     # pandoc, Typst, Quarto, fonts, R
octavo doctor    # everything should read ok
```

</details>

On Windows, WSL is recommended; the steps for WSL and for Windows itself are in
[the guide](https://yoshida-kd.github.io/octavo/guide/#13-windows).

## 2. Make a project

**In VS Code**, open an empty folder and press **New project** in the Octavo sidebar. Choose
the parts you need (an analysis in R or Python, a paper, slides, lecture notes, a poster)
and whether to fill them with examples.

<details>
<summary><strong>In a terminal</strong></summary>

```bash
octavo init study --with analysis,paper --example
cd study
octavo env       # the analysis environment (.venv and renv)
```

The paper is `docs/paper/paper.md` and the analysis is `analysis/analysis.qmd`.

</details>

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

In VS Code, open the manuscript and press the **PDF** button at the top right of the editor.
The PDF appears beside it, follows your cursor and is rebuilt on every save.

To get slides, a handout, a poster or a Word file as well, list them in the manuscript's
`outputs:`, for example `outputs: [pdf, slides, word]`.

<details>
<summary><strong>In a terminal</strong></summary>

```bash
octavo build --compile
```

The PDF is in `build/pdf/`.

</details>

## 5. Check

In the Octavo sidebar, press **Check before submitting (check)** under Tools. It finds missing
figures and citations, numbers typed by hand and word limits.

<details>
<summary><strong>In a terminal</strong></summary>

```bash
octavo check
```

</details>

## 6. Use an AI assistant

Every project has an `AGENTS.md` with its working rules: never type a result into the
manuscript, never edit `data/raw`, never edit what is generated. Claude Code, GitHub Copilot,
Codex and Antigravity read it on their own, so you can ask the assistant to write the analysis
or the manuscript and it works the Octavo way from the start. `octavo check` catches anything
that slips through. More in [the guide](https://yoshida-kd.github.io/octavo/guide/#23-what-is-in-a-project).

## 7. Where next

- [The guide](https://yoshida-kd.github.io/octavo/guide/): everything in detail.
- [Making lecture notes](https://yoshida-kd.github.io/octavo/lectures/): a handout and a deck
  per session from one file.
