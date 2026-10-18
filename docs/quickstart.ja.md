# クイックガイド

> これはクイックガイドの原稿です。読むなら **<https://yoshida-kd.github.io/octavo/ja/quickstart/>** で。 <!-- pages:skip -->

Octavo を入れてから、最初の PDF ができるまでを、6つの短い手順で説明します。それぞれの詳しい説明は
[手引き](https://yoshida-kd.github.io/octavo/ja/guide/)にあります。

## 1. インストール

**VS Code を使う場合**（かんたんな方法）:

1. [VS Code](https://code.visualstudio.com/) を入れ、続けて
   [Marketplace](https://marketplace.visualstudio.com/items?itemName=yoshida-kd.octavo) から
   **Octavo** 拡張機能を入れます。
2. フォルダを開くと、拡張機能が道具を確かめて「**セットアップ**」を勧めます。これを押します。
3. 終わればここまでです。R・Python・Quarto・pandoc・Typst・フォントと `octavo` コマンドが入ります。

<details>
<summary><strong>ターミナルを使う場合</strong>（Linux と macOS）</summary>

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install octavo-kit
octavo setup     # pandoc・Typst・Quarto・フォント・R を入れる
octavo doctor    # すべて ok になるはず
```

</details>

Windows では WSL をおすすめします。WSL の場合と Windows 本体の場合の手順は
[手引き](https://yoshida-kd.github.io/octavo/ja/guide/#13-windows)にあります。

## 2. プロジェクトを作る

**VS Code では**、空のフォルダを開き、Octavo のサイドバーで「**新しいプロジェクト**」を押します。
必要な部品（R か Python の分析、論文、スライド、講義ノート、ポスター）と、見本で埋めるかどうかを選びます。

<details>
<summary><strong>ターミナルでは</strong></summary>

```bash
octavo init study --with analysis,paper --example
cd study
octavo env       # 分析の環境（.venv と renv）
```

論文は `docs/paper/paper.md`、分析は `analysis/analysis.qmd` にできます。

</details>

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

VS Code では、原稿を開いて、エディタ右上の **PDF** のボタンを押します。横に PDF が出て、カーソルに
合わせて動き、保存するたびに作り直されます。

スライド・プリント・ポスター・Word も作るには、原稿の `outputs:` に並べます
（たとえば `outputs: [pdf, slides, word]`）。

<details>
<summary><strong>ターミナルでは</strong></summary>

```bash
octavo build --compile
```

PDF は `build/pdf/` にできます。

</details>

## 5. 確かめる

Octavo のサイドバーの「ツール」で「**投稿前に検査する (check)**」を押します。図や引用の抜け、
手で書いた数値、字数・語数の上限を見つけます。

<details>
<summary><strong>ターミナルでは</strong></summary>

```bash
octavo check
```

</details>

## 6. AI アシスタントと使う

どのプロジェクトにも、作業の約束事を書いた `AGENTS.md` があります。結果を原稿に手入力しない、
`data/raw` を書き換えない、生成されたものを直接直さない、といった内容です。Claude Code・
GitHub Copilot・Codex・Antigravity は、これを自分で読みます。分析や原稿の執筆を AI アシスタントに
頼んでも、最初から Octavo の流儀で作業してくれます。すり抜けたものは `octavo check` が見つけます。
詳しくは[手引き](https://yoshida-kd.github.io/octavo/ja/guide/#23-プロジェクトの中身)にあります。

## 7. このあとは

- [手引き](https://yoshida-kd.github.io/octavo/ja/guide/): すべての機能の詳しい説明。
- [講義ノートの作り方](https://yoshida-kd.github.io/octavo/ja/lectures/): 1本のファイルから、
  プリントと回ごとのスライド。
