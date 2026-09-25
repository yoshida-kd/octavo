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

## はじめに {#sec-intro}

<!-- octavo:example ここから ─ 引用の書き方の見本。`@キー` で地の文に、
     `[@キー; @キー2]` で括弧に入る。所有格（「山田の(2020)」）は
     \poscite に引用キーを渡す（下の1文がその例）。
     書誌は literature.bib（Zotero が正本）から組まれる。 -->
@yamada2020 は…と論じた。同じ論点は他にもある[@tanaka2019]。本稿は
\poscite{yamada2020}枠組みを用いる。

<!-- octavo:example ここまで -->

## 分析 {#sec-analysis}

<!-- octavo:example ここから ─ 数値と相互参照の見本。数値は原稿に書かず、
     `.qmd` の `ov_value()` に登録して `{{名前}}` で呼ぶ（桁は `{{coef_x:.2f}}`）。
     見出しの番号は書かない（組むときに振られる）。図・表・式・節には
     `{#fig-…}` `{#tbl-…}` `{#eq-…}` `{#sec-…}` でラベルを付け、本文では
     `@fig-trend` のように名前で指す（組むと「図2.1」「第1節」になる）。
     ラベルの名前は英数字で終わるので、日本語は空けずに続けて書ける（@fig-trendに）。
     分析を走らせる前の数字は仮の値、つまり嘘。 -->
@sec-introで述べたとおり、標本は {{n_obs}} 件である。推定したのは@eq-modelで、
x の係数は {{coef_x}}（*p* {{p_x}}）だった。記述統計を@tbl-summaryに、推移を
@fig-trendに示す。

$$
y_i = \beta_0 + \beta_1 x_i + \varepsilon_i
$$ {#eq-model}

<!-- octavo:example ここまで -->

<!-- octavo:example ここから ─ 表と図の書き方の見本。表は分析（ov_table()）が
     tables/summary.* に書いた中身が、この1行の場所に表題つきで入る。原稿に
     自分で書く表は、マークダウンの表のすぐ下に `: 表題 {#tbl-名前}` を置く -->
: 記述統計 {#tbl-summary}

![推移](../../figures/trend.png){#fig-trend}

<!-- octavo:example ここまで -->

## おわりに {#sec-conclusion}

## 参考文献

（この節は変換時に落とされる。書誌は literature.bib から組む）
