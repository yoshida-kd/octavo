---
title: 論文の題
author: @@AUTHOR@@
date: 2026-01-01
---

<!-- octavo:example この原稿は octavo new が置いたひな型。`octavo:example` の印が
     付いた塊は**例**なので、自分の内容に置き換えたら印のコメントごと消す。
     印が残っているあいだは octavo check が「ひな型の残り」として知らせる。
     書き方の約束は CLAUDE.md にある。 -->

## Abstract

<!-- octavo:example ここから -->
ここに要旨を書く。`## Abstract` か `## 要旨` の節は本文から切り離され、
Typst / LaTeX では abstract.typ / abstract.tex に、Word では冒頭の節になる。

<!-- octavo:example ここまで -->

## 1. はじめに

<!-- octavo:example ここから ─ 引用の書き方の見本。`@キー` で地の文に、
     `[@キー; @キー2]` で括弧に入る。所有格（「山田の(2020)」）は
     \poscite に引用キーを渡す（下の1文がその例）。
     書誌は literature.bib（Zotero が正本）から組まれる。 -->
@yamada2020 は…と論じた。同じ論点は他にもある[@tanaka2019]。本稿は
\poscite{yamada2020}枠組みを用いる。

<!-- octavo:example ここまで -->

## 2. 分析

<!-- octavo:example ここから ─ 数値と相互参照の見本。数値は原稿に書かず、
     `.qmd` の `ov_value()` に登録して `{{名前}}` で呼ぶ（桁は `{{coef_x:.2f}}`）。
     「第1節」「図1」と書けば Typst / LaTeX では自動でリンクになる
     （「表1」は table_map に外部の表を登録したとき。Word では常に文字のまま）。
     分析を走らせる前の数字は仮の値、つまり嘘。 -->
第1節で述べたとおり、標本は {{n_obs}} 件である。x の係数は
{{coef_x}}（*p* {{p_x}}）だった。記述統計を表1に、推移を図1に示す。

<!-- octavo:example ここまで -->

<!-- octavo:example ここから ─ 表と図の書き方の見本。中身は嘘の数値 -->
**表1．記述統計**

| 変数 | 平均 | 標準偏差 |
|---|---|---|
| x | 1.2 | 0.3 |
| y | 3.4 | 0.8 |

*注: サンプルは …*

![](../../figures/fig1_trend.png)

**図1．** 推移

<!-- octavo:example ここまで -->

## 3. おわりに

## 参考文献

（この節は変換時に落とされる。書誌は literature.bib から組む）
