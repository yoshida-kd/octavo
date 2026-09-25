// octavo:placeholder 仮の表。octavo analysis run で analysis.qmd の ov_table() が書き直す
#table(
  columns: 3,
  stroke: none,
  table.hline(),
  [*変数*], [*平均*], [*標準偏差*],
  table.hline(stroke: 0.5pt),
  table.cell(colspan: 3)[（分析を走らせると入る）],
  table.hline(),
)
