---
title: ポスターのタイトル
subtitle: サブタイトル
author: @@AUTHOR@@
institute: 所属
event: 見本学会 2026年度大会
date: 2026-01-01
qr: https://example.org/paper
poster_rows: [1, 2, 1]
qr_label: 論文はこちら
---

<!-- octavo:example このポスターは octavo new が置いたひな型。`octavo:example` の
     印が付いた塊は例なので、自分の内容にしたら印ごと消す。
     一番上の見出し（`#`）1つが1マス。既定は2列×3行に左上から順に入る。
     見出しの後ろに {span=2}（2列ぶん）・{rows=2}（2行ぶん）・{cell="2,3"}（2列目の3行目）。
     格子と判型は冒頭の poster_grid: 2x3・poster_size: a0・poster_orientation: landscape。
     入りきらないマスは、組むと知らせが出る。 -->

# 問い

<!-- octavo:example ここから -->
@yamada2020 は、政策の担い手が政府に集まる理由を制度の側から論じた。本研究はそれを
数えられる形にし、次の2点を問う。

- 政府が担う政策の割合は、時期によって変わるか
- 変わるなら、何がそれを動かすか

<!-- octavo:example ここまで -->

# データと方法

<!-- octavo:example ここから -->
標本は {{n_obs}} 件（数値は原稿に書かず、分析から差し込む）。@eq-model を最小二乗法で
推定する。記述統計は@tbl-summary のとおり。

$$
y_i = \beta_0 + \beta_1 x_i + \varepsilon_i
$$ {#eq-model}

: 記述統計 {#tbl-summary}

<!-- octavo:example ここまで -->

# 結果 {span=2}

<!-- octavo:example ここから ─ 図はマスの残りの高さに収まる -->
x の係数は {{coef_x}}（*p* {{p_x}}）。推移は@fig-trend。

![推移](../../assets/figures/trend.png){#fig-trend}

<!-- octavo:example ここまで -->

# まとめ

<!-- octavo:example ここから -->
- x が大きいほど y も大きい（係数 {{coef_x}}）
- 傾きは期間を通じて安定している
- 次は、担い手ごとに分けて推定する

<!-- octavo:example ここまで -->

# 参考文献

（この節には、引いた文献の一覧が入る）
