---
title: 発表の題
subtitle: 副題
author: @@AUTHOR@@
institute: 所属
date: 2026-01-01
---

<!-- octavo:example このスライドは octavo new が置いたひな型。`octavo:example` の
     印が付いた塊は例なので、自分の内容にしたら印ごと消す。
     `##` が1枚、`#` が節の扉。 -->

# 背景

<!-- octavo:example ここから -->
## 何が問題か

- 箇条書きは1枚に4〜5行まで
- `##` の見出しが1枚のスライドになる（`#` は節の扉）

::: notes
発表者ノート。投影するスライドには出ず、台本（octavo build <name> --to typst-notes）に出る。
:::

## 先行研究

@yamada2020 は…と論じた。[@tanaka2019] も参照。

<!-- octavo:example ここまで -->

# 分析

<!-- octavo:example ここから -->
## 結果

標本は {{n_obs}} 件（数値は原稿に書かず、分析から差し込む）。推移は@fig-trend。

![推移](../figures/trend.png){#fig-trend}

<!-- octavo:example ここまで -->

## まとめ
