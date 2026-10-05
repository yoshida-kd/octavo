---
title: Poster Title
subtitle: Subtitle
author: @@AUTHOR@@
institute: Affiliation
event: Example Conference 2026
date: 2026-01-01
qr: https://example.org/paper
poster_rows: [1, 2, 1]
qr_label: The paper
---

<!-- octavo:example This poster is a template octavo new put here. Blocks marked
     `octavo:example` are examples: replace them, mark and all, with your own.
     Each top-level heading (`#`) is one cell; by default they fill a 2×3 grid from the
     top left. After a heading: {span=2} (two columns), {rows=2} (two rows),
     {cell="2,3"} (column 2, row 3). The grid and the paper are poster_grid: 2x3,
     poster_size: a0 and poster_orientation: landscape at the top. A cell that does not fit
     is reported when you build. -->

# Question

<!-- octavo:example start -->
@yamada2020 explained from the institutions why policy gathers around government. This
study makes that countable and asks two things.

- Does the share of policy made by government change over time?
- If it does, what moves it?

<!-- octavo:example end -->

# Data and methods

<!-- octavo:example start -->
The sample has {{n_obs}} observations (numbers come from the analysis, never typed in).
We estimate @eq-model by least squares; @tbl-summary gives the descriptive statistics.

$$
y_i = \beta_0 + \beta_1 x_i + \varepsilon_i
$$ {#eq-model}

: Descriptive statistics {#tbl-summary}

<!-- octavo:example end -->

# Results {span=2}

<!-- octavo:example start — a figure fits the room left in its cell -->
The coefficient on x is {{coef_x}} (*p* {{p_x}}). @fig-trend shows the trend.

![Trend](../../assets/figures/trend.png){#fig-trend}

<!-- octavo:example end -->

# Conclusion

<!-- octavo:example start -->
- The larger x, the larger y (coefficient {{coef_x}})
- The slope is stable across the period
- Next: estimate it separately for each actor

<!-- octavo:example end -->

# References

(The works you cite are listed in this cell.)
