# @@NAME@@

分析から執筆・組版までを1つのリポジトリで行う。変換は
[Octavo](https://github.com/yoshida-kd/octavo) の `octavo` コマンド。

## 置き場所

| ディレクトリ | 何を置くか |
|---|---|
| `data/raw/` | 原データ。**読み取り専用**。git には入らない（出所は `data/raw/README.md` に書く） |
| `data/derived/` | 整形後のデータ。`.qmd` が作る。git には入らない |
| `analysis/` | 分析（`.qmd`）とヘルパー `octavo.R`。論文・資料に出る数値・図・表はすべてここから出す |
| `results/` | `.qmd` が出した数値（`*.json`）。本文の `{{…}}` が読む |
| `figures/` `tables/` | `.qmd` が出した図と表 |
| `papers/<name>/` | 論文（`paper.md`・`appendix.md` と、体裁の `main.typ` / `main.tex`） |
| `slides/<name>.md` | 発表スライド |
| `lectures/<name>.md` | 講義ノート（A4 プリント + 回ごとのスライド） |
| `refs/` | **外から来た資料**（コードブック・調査票・投稿規定）。git に入れる |
| `notes/` | **自分が書いたメモ**（読書メモ・査読メモ）。原稿には入らない |
| `build/` | 生成物。**手で書くものは無い**ので、丸ごと消してよい |
| `templates/` | （作ったときだけ）Octavo のひな型をこのプロジェクト用に差し替えたもの。`octavo template copy slides/typst-slides.typ` などで写して直す |

書誌は `literature.bib`（Zotero などの文献管理ソフトから書き出したもの）、設定は
`octavo.config.py`。論文の PDF は文献管理ソフトが持つので `refs/` には置かない。

## ひな型と本物を見分ける

`octavo init` / `octavo new` が置いたものには、**ひな型だと分かる印**が入っている。
自分の中身に置き換えたら、印ごと消す。

| 印 | どこに | 消し方 |
|---|---|---|
| `octavo:example` のコメント | 原稿・付録・`analysis.qmd`・`literature.bib` | 中身を書いたらコメントごと削除 |
| `_placeholder` | `results/analysis.json` | `octavo analysis run`（分析が書き直す） |
| 枠と × だけの図 | `figures/trend.*` | `.qmd` の `ov_figure()` が書き直す |
| 中身の無い表 | `tables/summary.*` | `.qmd` の `ov_table()` が書き直す |

`octavo check` が残りを数える。とくに **`results/analysis.json` の仮の値は
「致命的」**で、分析を1度も走らせないまま組むと本文に嘘の数字が入るため。
組むたびに `[値][注意]` の行も出る。

## 原稿を足す

論文・スライド・講義ノートは、どれも何本でも置ける。

```bash
octavo new paper example-paper      # papers/example-paper/paper.md
octavo new slides example-talk        # slides/example-talk.md
octavo new lecture example-lecture      # lectures/example-lecture.md
```

`octavo.config.py` を書き換える必要は無い（フォルダごと拾う）。
`octavo build <name>` の名前は、論文ならフォルダ名、スライド・講義ならファイル名。

## いちばん大事な約束

**論文・資料に出る数値を原稿に手で書かない。** `.qmd` で登録し、原稿では名前で呼ぶ。

```r
# analysis/analysis.qmd
ov_value("n_obs", nrow(d))
ov_value("coef_x", coef(m)[["x"]])
```

```markdown
<!-- papers/example-paper/paper.md -->
標本は {{n_obs}} 件、係数は {{coef_x}} だった。
```

こうしておくと、推定をやり直したときに本文の数字も一緒に変わる。
`octavo values` で本文と `results/` の突き合わせができる。

## 使い方

```bash
octavo build                   # 全部の原稿を変換（分析が古ければ先に走る）
octavo build example-paper       # 1本だけ
octavo build example-paper --to typst,docx   # 形式を指定

octavo analysis                # どの .qmd が古いか
octavo analysis run            # 分析を走らせる
octavo values                  # 本文の {{…}} が全部埋まるか
octavo checkbib                # 引用キーが .bib にあるか
octavo watch --to typst        # 保存するたびに作り直す
```

PDF まで:

```bash
octavo build --compile                          # 組版して PDF にする
octavo build example-lecture --to typst-slides --compile   # 講義ノートを回ごとのスライドに
```

## 分析の環境（.venv と renv）

分析はプロジェクトごとの環境で走らせる。**素の R / Python では走らせない。**
環境はコマンド1つで作れる（VS Code なら Octavo のサイドバーの **「ツール →
このプロジェクトの分析の環境を用意する」**）:

```bash
octavo env
```

uv で `.venv` を作って `requirements.txt` に書いたものを入れ、R では renv
（`renv.lock` と `.Rprofile`）を用意して、quarto が要る knitr と rmarkdown を入れる。
clone してきた直後なら `renv.lock` から同じパッケージを戻す。何度走らせても平気。

- Python: パッケージを `requirements.txt` に書いて、もう一度 `octavo env`。
  `octavo analysis run` は `.venv` を勝手に使う。ターミナルでその中で作業するなら
  `source .venv/bin/activate`（か `uv run python …`）
- R: プロジェクトの中で `install.packages()` したら、必ず `renv::snapshot()`

`.venv/` と `renv/library/` は git に入らないので、**記録
（`requirements.txt` / `renv.lock`）だけが環境の正本**になる。

Octavo 本体（pandoc・Typst・quarto・R・uv）はプロジェクトの外、マシンに1つ。
VS Code の拡張機能の「準備する」か、ターミナルで `octavo setup`。

## 最初にやること

1. `octavo doctor` — pandoc / Typst / quarto / R が揃っているか見る（LaTeX は任意）
2. 分析の環境を作る（上の「分析の環境」）— `octavo env`
3. `data/raw/` に原データを置き、`data/raw/README.md` に出所を書く
4. `analysis/analysis.qmd` を自分の分析に書き換える
5. `octavo analysis run` → `octavo values` で数値が出ているか確かめる
6. `octavo new paper|slides|lecture <name>` で原稿を足して書く
7. 論文の投稿先が決まったら `octavo csl get <スタイルID>` と
   `octavo.config.py` の `csl`、`papers/<name>/main.typ` の体裁を合わせる

Claude Code で作業するときの約束は `CLAUDE.md` に書いてある。
