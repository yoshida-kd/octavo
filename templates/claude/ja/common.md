<!-- octavo:section common -->
# このリポジトリについて

「@@NAME@@」のプロジェクト。**原稿（Markdown）から組版（Typst / Word / LaTeX / Beamer）
まで**を1つのリポジトリで行う。分析（Quarto の `.qmd`）も足せる。変換は
[Octavo](https://github.com/yoshida-kd/octavo) の `octavo` コマンドが行う。

```
figures/          手で作る図: Typst で描く <name>.typ、写真など
tables/           （必要なら作る）手で作る表: <name>.csv
assets/           原稿に差し込まれるもの。**分析と octavo build が書くので手で直さない**（git には入れる）
  figures/        図（<name>.pdf と .png）。分析の図と、figures/*.typ から組んだ図
  tables/         表（<name>.typ / .tex / .md）。分析の表と、tables/*.csv から作った表
refs/             （必要なら作る）外から来た資料（コードブック・調査票・投稿規定）。git に入れる
notes/            （必要なら作る）自分が書いたメモ（読書・査読・作業）。原稿には入らない
literature.bib    書誌。**文献管理ソフト（Zotero など）が正本**（エクスポートするたびに上書きされる）
templates/        Octavo のひな型をこのプロジェクト用に差し替えたもの（なければ同梱のものを使う。`octavo template list`）
octavo.config.py  このプロジェクトの設定（原稿・書式・分析の登録）
build/            生成物。**手で書くものは1つもない。丸ごと消してよい**
```

分析・論文・スライド・講義ノートの約束は、それぞれを足したときにこのファイルの
末尾に節として書き足される。

## 足すもの

原稿（論文・スライド・講義ノート）と分析（`.qmd`）は `octavo new` で足す。
**どれも何本でも**置ける（論文2本・スライド10本・分析3本、のように）。分析・
書誌・図表は全部の原稿で共有する。

```bash
octavo new paper example-paper         # docs/example-paper/example-paper.md と main.typ
octavo new paper example-paper --appendix   # 付録 appendix.md を足す（既にある論文にも）
octavo new paper example-paper --tex        # LaTeX 用の main.tex を足す（既にある論文にも）
octavo new slides example-talk           # docs/example-talk/example-talk.md
octavo new lecture example-lecture         # docs/example-lecture/example-lecture.md
octavo new analysis model                  # analysis/model.qmd（初回は data/ なども）
octavo new figure dag                      # figures/dag.typ（Typst で描く図。TikZ の代わり）
octavo new table compare                   # tables/compare.csv（手で作る表）
```

`octavo new` が置く原稿は見出しの骨組みだけ。書き方の見本を見たいときは
`--example` を付ける（見本の原稿と、それが使う見本の分析・書誌が入る）。

- **1つの文書は `docs/<name>/<name>.md`。**付録（`appendix.md`）や論文の体裁（`main.typ`）も
  同じフォルダに置く。`octavo build <name>` などはこの名前で指す
- **何を作るかは原稿の冒頭の `outputs:`**（`pdf` / `word` / `tex` / `slides` / `beamer` /
  `script`。書かなければ `pdf`）。PDF の体裁は、原稿の横に `main.typ` があればそれ、
  なければ Octavo の組み込みのもの。**何回分かの授業でできている原稿は `sessions: true`**
  （スライドが回ごとに分かれる）
- 題は冒頭の `title:` に書く。本文に `# 題` は書かない
- `octavo.config.py` の `documents` と `analysis` はフォルダを丸ごと拾うので
  **書き換えなくてよい**。置き場所を変えると拾われなくなる
- 原稿を消すときは、そのフォルダを消せば登録からも消える
- 投稿先・発表ごとに変わる設定（`csl`・`outputs`・`word_limit` などの上限・
  `slides_*`）は、その**原稿の冒頭**に書く。書いていないものは `octavo.config.py`
  に従う（`octavo config --doc <name>` で一覧・変更）
- 改ページは1行の `\newpage`、スライドの区切りは1行の `\newslide`（`\newslide{題}`）

# 守ること

## build/ の生成物は編集しない

`octavo build` が作るもの（`build/pdf/`・`build/slides/`・`build/word/` などの
中身）は、**編集しても次の build で消える。**直したいのは原稿（か `.qmd`）のほう。
`build/` に手で書くファイルは1つもないので、丸ごと消してよい（git にも入らない）。

## literature.bib は文献管理ソフトが正本

`literature.bib` は文献管理ソフト（Zotero など）からエクスポートしたもので、次にエクスポートすると
**丸ごと上書きされる**ので、手で直しても消える。書誌の誤りは文献管理ソフトの側で直す。

- `octavo check cites` — 本文が引いているキーが `.bib` にあるか、書誌が壊れていないか
- 直さないと決めた指摘は `octavo.config.py` の `bib_accepted` に理由付きで書く

## 図・表・式・節は、番号ではなくラベルで指す

番号（見出しの「2.」、キャプションの「図1」）は**原稿に書かない**。組むときに
節ごと（図2.1・表2.1・式(2.1)）に振られる。原稿ではラベルを付けて、名前で指す:

| | 書き方 | 本文での参照 |
|---|---|---|
| 節 | `# 分析 {#sec-analysis}` | `@sec-analysis` → 第2節 |
| 図 | `![推移](../../assets/figures/trend.png){#fig-trend}` | `@fig-trend` → 図2.1 |
| 表（原稿に書く） | Markdown の表 + すぐ下に `: 記述統計 {#tbl-desc}` | `@tbl-desc` → 表2.1 |
| 表（分析が作る） | `: 記述統計 {#tbl-summary}` の1行だけ（`assets/tables/summary.*` が入る） | `@tbl-summary` |
| 表（手で作る） | `tables/compare.csv` を作り、`: 比較 {#tbl-compare}` の1行だけ | `@tbl-compare` |
| 式 | `$$ … $$ {#eq-model}` | `@eq-model` → 式(2.1) |

- ラベルは `fig-` `tbl-` `eq-` `sec-` で始め、英数字と `-` `_` だけで書く。日本語は
  ラベルに含まれないので、直後に続けてよい（`@fig-trendに示す`）。`[-@fig-trend]` は
  番号だけ（「2.1」）
- 節や図を足したり並べ替えたりしても、**参照を直す必要はない**。存在しないラベルへの
  参照と、二重に付けたラベルは `octavo check` が止める

### 図のファイル（原稿には `.png`、組版には `.pdf`）

原稿には **`.png` を書く**。組むときに Octavo が形式ごとに差し替える（ビルドの出力の
`[figure] fig-… -> …/trend.pdf` がその記録）:

| 出力 | 使われるファイル | なぜ |
|---|---|---|
| エディタのプレビュー | `.png`（原稿に書いたもの） | プレビューは PDF の図を表示できない |
| Typst（論文・プリント・スライド）・LaTeX | `.pdf` | ベクターなので拡大しても粗くならず、図の中の文字も選択・検索できる |
| Word | `.png` | Word は PDF の図を貼れない |

`ov_figure()` と `figures/*.typ` は `.pdf` と `.png` の両方を書くので、どちらも揃っている。
原稿に `.pdf` を直接書いても組版には使われるが、エディタのプレビューには出ない。

パスは原稿から見た相対パスで書く（`docs/<name>/` の原稿からは `../../assets/figures/`）。図は全部の原稿で共有する。論文の図をスライドに貼るときも、
同じ `assets/figures/` のファイルを指せばよい（複製しない）。

### 図を作るときの約束（色覚の多様性に配慮する）

1. 色は**カラーユニバーサルデザイン（CUD）の配色**から選ぶ。R なら `ov_palette(3)`
   （青・橙・緑…）、ggplot2 なら `ov_scale_colour_cud()` / `ov_scale_fill_cud()`
2. **色だけで区別しない。**値や名前を図の中に直接書き、凡例に頼らない。強調は色に加えて
   太字・線種・位置でも示す
3. 隣り合う面は色相だけでなく**明るさも変える**。文字を載せる面は `ov_tint(色, 0.6)` で
   白に寄せる
4. 赤と緑、黄と白を隣り合わせない

箱と矢印の図などは `octavo new figure <name>` で `figures/<name>.typ` を置いて Typst で描く。
`octavo build` が `.pdf` と `.png` に組むので、原稿からは普通の図と同じく `.png` を貼る
（**組まれた `.pdf` / `.png` は手で直さない**。直すのは `.typ`）。

文章の比較表や手で集めた数字の表は、`octavo new table <name>` で `tables/<name>.csv` を置いて
書く（1行目が見出し。見出しのセルの右隣を空にすると横に結合する）。`octavo build` が
`assets/tables/` に表を作る（**直すのは `.csv`**）。長い表を Markdown の表で原稿に打つより
こちらがよい。

図表の**出典・注**は、下にふつうの段落で書かず、そのすぐ後（表なら表題の行の後）の
`::: {.figure-note}` + `:::` に書く。図表と離れず、小さい字で組まれ、スライドでは図と一緒に縮む。
**写真・画面の写し**は `figures/` に置いてそこから貼る（`../../figures/photo.jpg`）。大きな写真は
先に縮め、どこから来たか・使ってよいかを `figures/README.md` に書く。

## 箇条書きの字下げ

入れ子の箇条書きは、**子の項目を親の本文の桁に揃える**（`- ` の下なら 2 字、`1. ` の
下なら 3 字）。幅は決めていないが、1つの原稿の中では揃える。`octavo check lint` が、揃って
いない入れ子と、番号付きの項目の下で字下げが足りずに入れ子にならない行を知らせる。

**開きの `:::` の前には必ず空行を入れる**（箇条書きの中でも。項目の本文の桁にそろえる）。
空行がないと pandoc が `:::` を文字のまま出す。`octavo check lint` がこれと、どの出力にも当たらない
`.xxx-only` の印を知らせる。本文の結果でない数値（成績の配分など）は `[40%]{.no-lint}` と
印を付けると、手入力の数値の検査が見ない。

## 見本は、見本だと分かるようにしてある

`octavo init` / `octavo new` が既定で置くのは、そのまま使い続けるもの（見出しの骨組み・
空の書誌・分析の枠）だけ。`--example` を付けたときだけ**見本**が入り、そうと分かる印が
付いている。中身を自分のものに置き換えたら、**印ごと消す。**

| 印 | どこに | 消え方 |
|---|---|---|
| `octavo:example` のコメント | 原稿・付録・`.qmd`・`literature.bib` | 手で消す |
| `_placeholder` | `assets/values/*.json` | `octavo analysis run` が書き直す |
| 枠と × だけの図 | `assets/figures/trend.*` | `ov_figure()` が書き直す |
| 中身のない表 | `assets/tables/summary.*` | `ov_table()` が書き直す |

**仮の値（`_placeholder`）は特に危ない。**分析を1度も実行していなくても
`{{…}}` が全部解決してしまい、**仮の数字の入った PDF が組める**。そうならないよう
`octavo check` は仮の値を**「致命的」**として止め、`octavo build` と `octavo check values` も
毎回そう言う。

印が残っているあいだは `octavo check` が「ひな型の残り」として数える。**仕上げる
前に0にする。**

# 手順

## 原稿を書く・直す

```bash
octavo build                   # 全部の原稿を変換（分析が古ければ先に実行される）
octavo build <name>            # 1本だけ
octavo check cites                # 引用キーが .bib にあるか
octavo outline                 # 見出し構成を見る
```

`octavo build --no-citations` は引用を解決せず速く回す（下書き確認用）。

## 仕上げる前に

```bash
octavo check          # 検査を1回にまとめる（致命的があれば終了コードが 0 以外になる）
octavo check lint           # 手入力された数値だけを詳しく
```

**「致命的」が出ているうちは投稿・配布しない。**「注意」は読んで判断する。

# やらないこと

- **`build/` の生成物を手で書き換えない。**直したいのは常に原稿のほう
- **`literature.bib` を手で編集しない**（文献管理ソフトの側で直す）
- `octavo check lint` が出した指摘を、確かめずに `lint_accepted` へ流し込まない。
  そこは「結果ではない」と判断したものだけを書く場所
- **原稿を `octavo new` の置き場所の外に置かない**（`octavo.config.py` が拾わなくなる）
- **ひな型の印（`octavo:example`）を、中身を書き換えずに消さない。**印は
  「ここはまだ例だ」という記録で、消すのは置き換えたときだけ
- `octavo.config.py` に不明なキーを足さない（起動時に警告が出る）

# 困ったとき

```bash
octavo doctor       # pandoc / LaTeX / Typst / Quarto / R が揃っているか
octavo selftest     # 引用が実際にどう組まれるかを実物で見る
```

`octavo` コマンド自体の仕様は Octavo の手引きを見る: https://yoshida-kd.github.io/octavo/ja/guide/
