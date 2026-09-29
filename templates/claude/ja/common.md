<!-- octavo:section common -->
# このリポジトリについて

「@@NAME@@」のプロジェクト。**原稿（Markdown）から組版（Typst / Word / LaTeX / Beamer）
まで**を1つのリポジトリで行う。分析（Quarto の `.qmd`）も足せる。変換は
[Octavo](https://github.com/yoshida-kd/octavo) の `octavo` コマンドが行う。

```
figures/          図（<name>.pdf と .png）。分析が書くか、手で置く
refs/             （要れば作る）外から来た資料（コードブック・調査票・投稿規定）。git に入れる
notes/            （要れば作る）自分が書いたメモ（読書・査読・作業）。原稿には入らない
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
octavo new paper example-paper         # papers/example-paper/paper.md と main.typ
octavo new paper example-paper --appendix   # 付録 appendix.md を足す（既にある論文にも）
octavo new paper example-paper --tex        # LaTeX 用の main.tex を足す（既にある論文にも）
octavo new slides example-talk           # slides/example-talk.md
octavo new lecture example-lecture         # lectures/example-lecture.md
octavo new analysis model                  # analysis/model.qmd（初回は data/ なども）
```

`octavo new` が置く原稿は見出しの骨組みだけ。書き方の見本を見たいときは
`--example` を付ける（見本の原稿と、それが使う見本の分析・書誌が入る）。

- **文書の名前はフォルダ名（論文）かファイル名（スライド・講義）。**`octavo build <name>`
  などはこの名前で指す。種類が違っても名前はぶつけない
- `octavo.config.py` の `documents` と `analysis` はフォルダを丸ごと拾うので
  **書き換えなくてよい**。置き場所を変えると拾われなくなる
- 原稿を消すときは、ファイル（論文ならフォルダ）を消せば登録からも消える
- 投稿先・発表ごとに変わる設定（`csl`・`targets`・`word_limit` などの上限・
  `typst_slides_*`）は、その**原稿の冒頭**に書く。書いていないものは `octavo.config.py`
  に従う（`octavo config --doc <name>` で一覧・変更）

# 守ること

## build/ の生成物は編集しない

`octavo build` が作るもの（`build/typst/`・`build/typst-slides/`・`build/word/` などの
中身）は、**編集しても次の build で消える。**直したいのは原稿（か `.qmd`）のほう。
`build/` に手で書くファイルは1つもないので、丸ごと消してよい（git にも入らない）。

## literature.bib は文献管理ソフトが正本

`literature.bib` は文献管理ソフト（Zotero など）からエクスポートしたもので、次にエクスポートすると
**丸ごと上書きされる**ので、手で直しても消える。書誌の誤りは文献管理ソフトの側で直す。

- `octavo checkbib` — 本文が引いているキーが `.bib` にあるか、書誌が壊れていないか
- 直さないと決めた指摘は `octavo.config.py` の `bib_accepted` に理由付きで書く

## 図・表・式・節は、番号ではなくラベルで指す

番号（見出しの「2.」、キャプションの「図1」）は**原稿に書かない**。組むときに
節ごと（図2.1・表2.1・式(2.1)）に振られる。原稿ではラベルを付けて、名前で指す:

| | 書き方 | 本文での参照 |
|---|---|---|
| 節 | `## 分析 {#sec-analysis}` | `@sec-analysis` → 第2節 |
| 図 | `![推移](../../figures/trend.png){#fig-trend}` | `@fig-trend` → 図2.1 |
| 表（原稿に書く） | マークダウンの表 + すぐ下に `: 記述統計 {#tbl-desc}` | `@tbl-desc` → 表2.1 |
| 表（分析が作る） | `: 記述統計 {#tbl-summary}` の1行だけ（`tables/summary.*` が入る） | `@tbl-summary` |
| 式 | `$$ … $$ {#eq-model}` | `@eq-model` → 式(2.1) |

- ラベルは `fig-` `tbl-` `eq-` `sec-` で始め、英数字と `-` `_` だけで書く。日本語は
  ラベルに含まれないので、直後に続けてよい（`@fig-trendに示す`）。`[-@fig-trend]` は
  番号だけ（「2.1」）
- 節や図を足したり並べ替えたりしても、**参照を直す必要はない**。ないラベルへの
  参照と、二重に付けたラベルは `octavo check` が止める

図は `.png` を原稿に貼れば足りる（LaTeX 用の `.pdf` は Octavo が自動で探す）。
パスは原稿から見た相対パスで書く（論文なら `../../figures/`、スライド・講義なら
`../figures/`。エディタのプレビューに出る）。図は全部の原稿で共有する。論文の図を
スライドに貼るときも、同じ `figures/` のファイルを指せばよい（複製しない）。

## 見本は、見本だと分かるようにしてある

`octavo init` / `octavo new` が既定で置くのは、そのまま使い続けるもの（見出しの骨組み・
空の書誌・分析の枠）だけ。`--example` を付けたときだけ**見本**が入り、そうと分かる印が
付いている。中身を自分のものに置き換えたら、**印ごと消す。**

| 印 | どこに | 消え方 |
|---|---|---|
| `octavo:example` のコメント | 原稿・付録・`.qmd`・`literature.bib` | 手で消す |
| `_placeholder` | `results/*.json` | `octavo analysis run` が書き直す |
| 枠と × だけの図 | `figures/trend.*` | `ov_figure()` が書き直す |
| 中身のない表 | `tables/summary.*` | `ov_table()` が書き直す |

**仮の値（`_placeholder`）は特に危ない。**分析を1度も実行していなくても
`{{…}}` が全部解決してしまい、**仮の数字の入った PDF が組める**。そうならないよう
`octavo check` は仮の値を**「致命的」**として止め、`octavo build` と `octavo values` も
毎回そう言う。

印が残っているあいだは `octavo check` が「ひな型の残り」として数える。**仕上げる
前に0にする。**

# 手順

## 原稿を書く・直す

```bash
octavo build                   # 全部の原稿を変換（分析が古ければ先に実行される）
octavo build <name>            # 1本だけ
octavo checkbib                # 引用キーが .bib にあるか
octavo outline                 # 見出し構成を見る
```

`octavo build --no-citations` は引用を解決せず速く回す（下書き確認用）。

## 仕上げる前に

```bash
octavo check          # 検査を1回にまとめる（致命的があれば非 0 で終わる）
octavo lint           # 手入力された数値だけを詳しく
```

**「致命的」が出ているうちは投稿・配布しない。**「注意」は読んで判断する。

# やらないこと

- **`build/` の生成物を手で書き換えない。**直したいのは常に原稿のほう
- **`literature.bib` を手で編集しない**（文献管理ソフトの側で直す）
- `octavo lint` が出した指摘を、確かめずに `lint_accepted` へ流し込まない。
  そこは「結果ではない」と判断したものだけを書く場所
- **原稿を `octavo new` の置き場所の外に置かない**（`octavo.config.py` が拾わなくなる）
- **ひな型の印（`octavo:example`）を、中身を書き換えずに消さない。**印は
  「ここはまだ例だ」という記録で、消すのは置き換えたときだけ
- `octavo.config.py` に不明なキーを足さない（起動時に警告が出る）

# 困ったとき

```bash
octavo doctor       # pandoc / LaTeX / Typst / quarto / R が揃っているか
octavo selftest     # 引用が実際にどう組まれるかを実物で見る
```

`octavo` コマンド自体の仕様は Octavo の手引きを見る: https://github.com/yoshida-kd/octavo/blob/main/docs/guide.ja.md
