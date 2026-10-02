<!-- octavo:section analysis-python -->
# Python の分析

```` ```{python} ```` のチャンクを持つ `.qmd` も、R の `.qmd` と同じ働きをする。R の `octavo.R`
にあたる `analysis/octavo_helper.py` が、同じ名前の関数で、同じファイルを書き出して、数値・図・表を
原稿に渡す。**上に書いた「結果は原稿に書き込まない」は、そのまま当てはまる。**

```python
# analysis/*.qmd（最初のチャンクで補助を読み込んでいる）
ov_value("n_obs", len(d))
ov_value("coef_x", model.params["x"])
ov_value("p_x", ov_pval(model.pvalues["x"]))
ov_figure(fig, "trend")          # matplotlib の Figure（plotnine の ggplot、描画する関数でもよい）
ov_table(tab, "summary")         # pandas の DataFrame（辞書・リストのリストでもよい）
```

- `int`（NumPy の整数も）は `1,523`、`float` は `0.342` と出る。たまたま整数になった float
  （`2.0`）も小数で出る。書式は `fmt=".2f"` か、本文の `{{coef_x:.2f}}`
- `ov_figure(fig, 名前)` は `.pdf` と `.png` を書く。先に `fig.tight_layout()` を呼ぶ。
  色は `ov_palette()` から選ぶ（このファイルの図の約束を参照）
- `ov_table()` が書くのは表の中身だけ。表題の行 `: 表題 {#tbl-名前}` は原稿にある。
  DataFrame の index は書かれない（要るなら `df.reset_index()`）
- パッケージは `requirements.txt` に書き、`octavo env` で入れる（`ipykernel`・`nbformat`・
  `nbclient`・`pyyaml` は Quarto 自身に要るので消さない）。**ほかの場所へ `pip install`
  しない。** `octavo analysis run` は `.venv` を自分で使う
- スクリプトを `octavo.py` と名付けない。補助が `octavo_helper.py` なのは、`octavo` コマンド
  自身のパッケージを覆い隠さないため
