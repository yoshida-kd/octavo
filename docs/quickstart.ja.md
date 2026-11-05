# クイックガイド

> これはクイックガイドの原稿です。読むなら **<https://yoshida-kd.github.io/octavo/ja/quickstart/>** で。 <!-- pages:skip -->

Octavo を入れてから、最初の PDF ができるまでを、VS Code での6つの短い手順で説明します。それぞれの
詳しい説明は[手引き](https://yoshida-kd.github.io/octavo/ja/guide/)にあります。

## 1. インストール

1. [VS Code](https://code.visualstudio.com/) を入れ、続けて
   [Marketplace](https://marketplace.visualstudio.com/items?itemName=yoshida-kd.octavo) から
   **Octavo** 拡張機能を入れます。
2. フォルダを開くと、拡張機能が道具を確かめて「**セットアップ**」を勧めます。これを押します。
3. 終わればここまでです。R・Python・Quarto・pandoc・Typst・フォントと `octavo` コマンドが入ります。


Windows では WSL をおすすめします。環境ごとの手順と、ターミナルで入れる方法は
[Octavo のインストール](https://yoshida-kd.github.io/octavo/ja/install/)にあります。

## 2. プロジェクトを作る

空のフォルダを開き、Octavo のサイドバーで「**新しいプロジェクトを作成**」を押します。
必要な部品（R か Python の分析、論文、スライド、講義ノート、ポスター）と、見本で埋めるかどうかを選びます。


## 3. 書く

分析で出した数値を、名前で原稿に渡します。分析（`.qmd`）では次のように登録します:

```r
ov_value("n_obs", nrow(d))
ov_figure(p, "trend")
```

原稿（`docs/paper/paper.md`）では、数値を名前で呼び、図はラベルで参照します:

```markdown
---
title: Title of the Paper
outputs: [pdf]
---

# Analysis {#sec-analysis}

We analyse {{n_obs}} observations. @fig-trend shows the trend.

![Trend](../../assets/figures/trend.png){#fig-trend}
```

結果の数値や番号を手で書くことはありません。`{{n_obs}}` や `@fig-trend` は文書を作るときに埋まり、
分析をやり直しても、節を並べ替えても、正しいままです。

## 4. 作る

原稿を開いて、エディタ右上の **PDF** のボタンを押します。横に PDF が出て、カーソルに
合わせて動き、保存するたびに作り直されます。

スライド・プリント・ポスター・Word も作るには、原稿の `outputs:` に並べます
（たとえば `outputs: [pdf, slides, word]`）。


## 5. 確かめる

Octavo のサイドバーの「ツール」で「**投稿前に検査する (check)**」を押します。図や引用の抜け、
手で書いた数値、字数・語数の上限を見つけます。


## 6. AI アシスタントと使う

どのプロジェクトにも、作業の約束事を書いた `AGENTS.md` があります。結果を原稿に手入力しない、
`data/raw` を書き換えない、生成されたものを直接直さない、といった内容です。Claude Code・
GitHub Copilot・Codex・Antigravity は、これを自分で読みます。分析や原稿の執筆を AI アシスタントに
頼んでも、最初から Octavo の流儀で作業してくれます。この手引きにボタンのないこと（匿名の版、
投稿用のまとめなど）も頼めます。すり抜けたものは「**投稿前に検査する**」が見つけます。詳しくは
[手引き](https://yoshida-kd.github.io/octavo/ja/guide/#10-ai-アシスタントと使う)にあります。

## 7. このあとは

- [手引き](https://yoshida-kd.github.io/octavo/ja/guide/): すべての機能の詳しい説明。
- [リファレンス](https://yoshida-kd.github.io/octavo/ja/reference/): すべてのコマンドと設定
  （AI アシスタント向け）。
- [講義ノートの作り方](https://yoshida-kd.github.io/octavo/ja/lectures/): 1本のファイルから、
  プリントと回ごとのスライド。
