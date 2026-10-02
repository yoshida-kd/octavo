<!-- octavo:section analysis-python -->
# The analysis in Python

A `.qmd` with ```` ```{python} ```` chunks does the same job as an R one: the helper
`analysis/octavo_helper.py` (the Python counterpart of `octavo.R`, same names and the same files
written) hands values, figures and tables to the manuscript. **Everything above about never typing a
result applies unchanged.**

```python
# analysis/*.qmd  (the setup chunk loads the helper)
ov_value("n_obs", len(d))
ov_value("coef_x", model.params["x"])
ov_value("p_x", ov_pval(model.pvalues["x"]))
ov_figure(fig, "trend")          # a matplotlib Figure (or plotnine ggplot, or a function that draws)
ov_table(tab, "summary")         # a pandas DataFrame (or a dict / a list of lists)
```

- `int` (and NumPy integers) render as `1,523`, `float` as `0.342`. A float that happens to
  be whole (`2.0`) still renders with decimals. Pass `fmt=".2f"` or write `{{coef_x:.2f}}`
- `ov_figure(fig, name)` writes the `.pdf` and the `.png`. Call `fig.tight_layout()` first.
  Use the colours from `ov_palette()` (see the figure rules in this file)
- `ov_table()` writes the table's contents only; the caption line `: Caption {#tbl-name}` is
  in the manuscript. The index of a DataFrame is not written: `df.reset_index()` if it matters
- Packages are listed in `requirements.txt` (`ipykernel`, `nbformat`, `nbclient` and `pyyaml`
  are what Quarto itself needs — keep them) and installed with `octavo env`. **Never
  `pip install` into anything else.** `octavo analysis run` uses `.venv` by itself
- Do not name a script `octavo.py`: the helper is `octavo_helper.py` so it never shadows the
  `octavo` command's own package
