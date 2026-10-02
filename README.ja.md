# Octavo

**計量社会科学スターターパック**

[![tests](https://github.com/yoshida-kd/octavo/actions/workflows/tests.yml/badge.svg)](https://github.com/yoshida-kd/octavo/actions/workflows/tests.yml)

[English README](https://github.com/yoshida-kd/octavo/blob/main/README.md)

論文・スライド・講義ノートは Markdown で書き、分析は Quarto で行う。分析が出した
数値・図・表は Octavo がどの文書にも差し込み、PDF（Typst）と Word に仕上げる（TeX が
あれば LaTeX にも）。文献は1つの `.bib` から、好きな CSL スタイルで整形される。

![Octavo の仕組み: 分析と手で作ったファイルから数値・図・表ができ、原稿はそれを名前で呼び、octavo build が PDF と Word を作る](https://raw.githubusercontent.com/yoshida-kd/octavo/main/docs/images/flow-ja.svg)

## できあがるもの

![見本のプロジェクトから組んだ論文の1ページとスライド](https://raw.githubusercontent.com/yoshida-kd/octavo/main/docs/images/showcase-ja.png)

見本のプロジェクト（`octavo init demo --all --example`）から組んだ論文の1ページと
スライド。係数・表・図は分析から取り込まれ、式・表・図の番号と参考文献は組版のときに自動で付く。

- **数値を手入力しない。** 分析で登録し（`ov_value("n_obs", nrow(d))`）、原稿では
  名前で呼ぶ（`{{n_obs}}`）。分析を再実行すれば、すべての文書の数値がまとめて更新される。
  本文に手入力された数値や、仮の値のままの数値は `octavo check` が知らせる。
- **R でも Python でも。** 分析は Quarto の `.qmd` で、R でも Python でも書ける。どちらにも
  同じ補助関数（`ov_value`・`ov_figure`・`ov_table`）があり、プロジェクトの `.venv` と renv も
  用意される。
- **1つの原稿から、いくつもの文書。** 投稿先の書式に合わせた論文、発表スライド、A4 の
  プリントと回ごとのスライドを兼ねる講義ノート。発表者用の台本も、共著者に回す Word も出せる。
- **ラベルで参照する**: `@fig-trend` は「図2.1」になり、節を並べ替えても、番号は正しいまま。
- **TikZ なしで図を描く**: `octavo new figure` で置いた Typst のファイルに箱と矢印の図を
  描けば、通常の図と同じように使える。
- **手で作る表も表の形で編集**: `octavo new table` で置いた CSV を VS Code 拡張が表の
  形で編集する（Excel でもよい）。分析の表と同じように使える。
- **投稿から採択後まで**: 分量の上限、匿名審査、投稿用の zip、共著者が Word で入れた
  変更履歴の読み取り、投稿した版から変わった数値の一覧、再現用パッケージ。
- **VS Code 拡張**: カーソルに合わせて動く PDF のライブプレビュー、上の機能を操作できる
  サイドバー、ボタン1つのセットアップ。
- **AI アシスタントと使える**: プロジェクトごとの約束事（結果を原稿に手入力しない、`data/raw`
  は書き換えない、など）を `AGENTS.md` に置く。Claude Code・GitHub Copilot・Codex・Antigravity
  のどれもが読むので、AI アシスタントは最初からその約束を知っている。
- Linux・macOS・Windows、英語と日本語。

## インストール

**VS Code なら**、[Octavo 拡張](https://marketplace.visualstudio.com/items?itemName=yoshida-kd.octavo)
をインストールし、案内が出たら「**セットアップ**」を押す。pandoc・Typst・Quarto・R・フォントと
`octavo` コマンドがまとめて入る。

**ターミナルなら**:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # uv（まだなければ）
uv tool install octavo-kit                        # octavo コマンド
octavo setup                                      # pandoc / Typst / Quarto / フォント / R
octavo doctor                                     # 足りないものを報告する
```

## 始め方

**VS Code なら**:

1. フォルダを開き、アクティビティバーの Octavo のアイコンを押す。まだプロジェクトでない
   フォルダなら「**新しいプロジェクト**」が出るので、場所・言語・最初に置くもの（R か Python
   の分析、論文、スライド、講義ノート）と、見本で埋めるかを選ぶ。分析を選ぶと、続けてその
   環境まで整う。
2. 原稿を開き、エディタ右上の **PDF** のボタンを押す。横に PDF が出て、保存のたびに組み直され、
   カーソルに合わせて動く。
3. あとは Octavo のサイドバーの上の **+** から追加する。

**ターミナルなら**、まずは見本で動作を確かめる（分析・論文・スライド・講義ノート）:

```bash
octavo init demo --all --example
cd demo
octavo env                    # このプロジェクトの分析の環境（.venv と renv）
octavo build --compile        # 分析を実行してから、全部を PDF まで組む
```

自分のプロジェクトは、必要な部品だけで始める:

```bash
octavo init study --with analysis,paper
cd study
octavo env                    # このプロジェクトの分析の環境（.venv と renv）
octavo build paper --compile  # analysis/analysis.qmd と papers/paper/paper.md を書いたら
octavo check                  # 投稿する前に
```

分析では論文に出すものを登録し、原稿ではそれを呼ぶ:

```r
ov_value("n_obs", nrow(d))
ov_figure(p, "trend")
```

```python
ov_value("n_obs", len(d))
ov_figure(fig, "trend")
```

```markdown
The sample has {{n_obs}} cases (@fig-trend).

![Trend](../../assets/figures/trend.png){#fig-trend}
```

## 手引き

使い方はすべて[手引き](https://yoshida-kd.github.io/octavo/ja/guide/)にある:

1. [インストール](https://yoshida-kd.github.io/octavo/ja/guide/#1-インストール) — Linux・macOS・Windows を順に
2. [最初のプロジェクト](https://yoshida-kd.github.io/octavo/ja/guide/#2-最初のプロジェクト) — `octavo init` と `octavo new`、分析の環境
3. [原稿を書く](https://yoshida-kd.github.io/octavo/ja/guide/#3-原稿を書く) — 参照、番号の付くブロック、数式、図、表
4. [分析](https://yoshida-kd.github.io/octavo/ja/guide/#4-分析) — Quarto から数値・図・表を
5. [文献](https://yoshida-kd.github.io/octavo/ja/guide/#5-文献)
6. [論文](https://yoshida-kd.github.io/octavo/ja/guide/#6-論文-下書きから投稿まで) — 点検、匿名審査、投稿、改訂
7. [スライドと講義ノート](https://yoshida-kd.github.io/octavo/ja/guide/#7-スライドと講義ノート) — 回の区切り、回ごとの配布資料
8. [自分用にする](https://yoshida-kd.github.io/octavo/ja/guide/#8-自分用にする) — テンプレート、Word のスタイル、書体
9. [コマンド一覧](https://yoshida-kd.github.io/octavo/ja/guide/#9-コマンド一覧)
10. [VS Code](https://yoshida-kd.github.io/octavo/ja/guide/#10-vs-code)
11. [自分の機械で確かめること](https://yoshida-kd.github.io/octavo/ja/guide/#11-自分の機械で確かめること)

## 貢献とライセンス

Issue や Pull Request を歓迎する。詳しくは
[CONTRIBUTING.md](https://github.com/yoshida-kd/octavo/blob/main/CONTRIBUTING.md) を参照。
MIT ライセンス。
