# Octavo

**計量社会科学スターターパック**

[![tests](https://github.com/yoshida-kd/octavo/actions/workflows/tests.yml/badge.svg)](https://github.com/yoshida-kd/octavo/actions/workflows/tests.yml)

[English README](https://github.com/yoshida-kd/octavo/blob/main/README.md)

論文・スライド・講義ノートはマークダウンで書き、分析は Quarto で行う。分析が出した
数値・図・表は Octavo がどの文書にも差し込み、PDF（Typst）と Word に組む（TeX が
あれば LaTeX にも）。文献は1つの `.bib` から、好きな CSL の書式で組まれる。

![Octavo の仕組み: 分析が数値・図・表を書き、原稿はそれを名前で呼び、octavo build が PDF と Word を作る](https://raw.githubusercontent.com/yoshida-kd/octavo/main/docs/images/flow-ja.svg)

## できあがるもの

![見本のプロジェクトから組んだ論文の1ページとスライド](https://raw.githubusercontent.com/yoshida-kd/octavo/main/docs/images/showcase-ja.png)

見本のプロジェクト（`octavo init demo --all --example`）から組んだ論文の1ページと
スライド。係数・表・図は分析から入り、式・表・図の番号と参考文献は組むときに振られる。

- **数値を手で書かない。** 分析で登録し（`ov_value("n_obs", nrow(d))`）、原稿では
  名前で呼ぶ（`{{n_obs}}`）。分析をやり直せば、どの文書の数値も一緒に変わる。
  原稿に手入力された数値や、仮の値のままの数値は `octavo check` が知らせる。
- **1つの原稿から、いくつもの文書。** 投稿先の体裁の論文、発表スライド、A4 の
  プリントと回ごとのスライドになる講義ノート。発表者用の台本も、共著者に回す Word も。
- **ラベルで参照する**: `@fig-trend` は「図2.1」になり、節を並べ替えても崩れない。
- **TikZ なしで図を描く**: `octavo new figure` で置いた Typst のファイルに箱と矢印の図を
  描けば、普通の図と同じように使える。
- **投稿とその後まで**: 分量の上限、匿名審査、投稿用の zip、共著者が Word で入れた
  変更履歴の読み出し、投稿時から動いた数値の一覧、再現用パッケージ。
- **VS Code 拡張**: PDF のライブプレビュー、ここに挙げたことをまとめたサイドバー、
  ボタン1つのセットアップ。
- Linux・macOS・Windows、英語と日本語。

## 入れる

**VS Code なら**、[Octavo 拡張](https://marketplace.visualstudio.com/items?itemName=yoshida-kd.octavo)
を入れ、聞かれたら「**セットアップ**」を押す。pandoc・Typst・Quarto・R・フォントと
`octavo` コマンドが入る。

**ターミナルなら**:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # uv（まだなければ）
uv tool install octavo-kit                        # octavo コマンド
octavo setup                                      # pandoc / Typst / Quarto / フォント / R
octavo doctor                                     # 足りないものを教えてくれる
```

## 始め方

まず動くところを見る（分析・論文・スライド・講義ノートの見本）:

```bash
octavo init demo --all --example
cd demo
octavo build --compile        # 分析を実行してから、全部を PDF まで組む
```

自分のプロジェクトは、要る部品から始める:

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

```markdown
The sample has {{n_obs}} cases (@fig-trend).

![Trend](../../figures/trend.png){#fig-trend}
```

## 手引き

使い方はすべて[手引き](https://github.com/yoshida-kd/octavo/blob/main/docs/guide.ja.md)にある:

1. [入れる](https://github.com/yoshida-kd/octavo/blob/main/docs/guide.ja.md#1-入れる)
2. [文書とプロファイル](https://github.com/yoshida-kd/octavo/blob/main/docs/guide.ja.md#2-文書とプロファイル) — `octavo init` と `octavo new`、講義ノート、文書ごとの設定
3. [原稿の書き方](https://github.com/yoshida-kd/octavo/blob/main/docs/guide.ja.md#3-原稿の書き方) — 相互参照、数式、表
4. [分析（Quarto）と原稿](https://github.com/yoshida-kd/octavo/blob/main/docs/guide.ja.md#4-分析quartoと原稿の分業)
5. [文献](https://github.com/yoshida-kd/octavo/blob/main/docs/guide.ja.md#5-文献bib--雑誌の書式)
6. [コマンド](https://github.com/yoshida-kd/octavo/blob/main/docs/guide.ja.md#6-コマンド) — 点検、匿名審査、投稿、改訂、再現
7. [自分用にする](https://github.com/yoshida-kd/octavo/blob/main/docs/guide.ja.md#7-自分用にする-テンプレートと-word-のスタイル) — テンプレートと Word のスタイル
8. [形式ごとの違い](https://github.com/yoshida-kd/octavo/blob/main/docs/guide.ja.md#8-形式ごとの違い知っておくこと)
9. [中身の構成](https://github.com/yoshida-kd/octavo/blob/main/docs/guide.ja.md#9-中身の構成)
10. [何が確かめられているか](https://github.com/yoshida-kd/octavo/blob/main/docs/guide.ja.md#10-何が確かめられていて何を自分で確かめるか)
11. [VS Code 拡張](https://github.com/yoshida-kd/octavo/blob/main/docs/guide.ja.md#11-vs-code-拡張)

## 貢献とライセンス

Issue や Pull Request を歓迎する。
[CONTRIBUTING.md](https://github.com/yoshida-kd/octavo/blob/main/CONTRIBUTING.md) を見る。
MIT ライセンス。
