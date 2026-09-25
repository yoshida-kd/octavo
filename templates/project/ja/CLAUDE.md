# このリポジトリについて

「@@NAME@@」の研究プロジェクト。**分析（Quarto の `.qmd`）から執筆（Markdown の
原稿）、組版（Typst / Word / LaTeX / Beamer）までを1つのリポジトリで完結させる。**
変換は [Octavo](https://github.com/yoshida-kd/octavo) の `octavo` コマンドが行う。

```
data/raw/         原データ。**読み取り専用**。出所は data/raw/README.md に書く
data/derived/     整形後のデータ。.qmd が作る。手で編集しない
analysis/*.qmd    分析。論文に出る数値・図・表はすべてここから出す
analysis/octavo.R .qmd 側のヘルパー（ov_value / ov_figure / ov_table）
results/*.json    .qmd が出した数値（本文の {{…}} が読む）。手で編集しない
figures/          .qmd が出した図（<name>.pdf と .png）。手で置いてもよい
tables/           .qmd が出した表（<name>.tex と .typ）
refs/             外から来た資料（コードブック・調査票・投稿規定）。git に入れる
notes/            自分が書いたメモ（読書・査読・作業）。原稿には入らない
papers/<name>/    論文。paper.md・appendix.md・main.typ（体裁）（**これを書く**）
slides/<name>.md  発表スライド（**これを書く**）
lectures/<name>.md 講義ノート。A4 プリントと、回ごとのスライドを作る（**これを書く**）
literature.bib    書誌。**文献管理ソフト（Zotero など）が正本**（書き出すたびに上書きされる）
templates/        Octavo のひな型をこのプロジェクト用に差し替えたもの（無ければ同梱のもの。octavo template list）
octavo.config.py  このプロジェクトの設定（原稿・書式・分析の登録）
build/            生成物。**手で書くものは1つも無い。丸ごと消してよい**
```

## 原稿の種類と名前

原稿は3種類あり、**どれも何本でも**このリポジトリに置ける（論文2本・スライド10本・
講義ノート3本、のように）。種類の違いは原稿のテンプレートと組み方だけで、分析・
書誌・図表は全部の原稿で共有する。

```bash
octavo new paper example-paper         # papers/example-paper/paper.md（+ appendix.md、main.typ / main.tex）
octavo new slides example-talk           # slides/example-talk.md
octavo new lecture example-lecture         # lectures/example-lecture.md
```

- **文書の名前はフォルダ名（論文）かファイル名（スライド・講義）。**`octavo build <name>`
  などはこの名前で指す。種類が違っても名前はぶつけない
- 原稿は `octavo new` で足す。`octavo.config.py` の `documents` はフォルダを丸ごと
  拾うので**書き換えなくてよい**。置き場所を変えると拾われなくなる
- 原稿を消すときは、ファイル（論文ならフォルダ）を消せば登録からも消える

# 守ること

## 1. 論文・資料に出る数値を、原稿に手で書かない

**これがこのリポジトリの最重要の約束。**係数・N・p 値・記述統計・割合、
どれも `.qmd` 側で `ov_value()` に登録し、原稿では `{{名前}}` と書く。

```r
# analysis/*.qmd
ov_value("n_obs", nrow(d))
ov_value("coef_x", coef(m)[["x"]])
ov_value("p_x", ov_pval(summary(m)$coefficients["x", "Pr(>|t|)"]))
```

```markdown
<!-- 原稿（papers/・slides/・lectures/ のどれでも） -->
標本は {{n_obs}} 件、x の係数は {{coef_x}}（*p* {{p_x}}）だった。
```

数値を直接書くと、推定をやり直したときに本文だけ古いまま残る。これは
**気づきにくく、見つかったときに最も痛い種類の誤り**なので、例外を作らない。原稿に生の数字を書き足す
必要があると思ったら、まず `.qmd` に `ov_value()` を足せないかを考えること。

- 書式は `{{coef_x:.2f}}`（Python の書式指定）で本文側から変えられる
- 整数（R の `nrow()`）は `1,523`、小数（`coef()`）は既定 3 桁
- `octavo values` で「本文が呼んでいる名前」と「results/ にある値」を突き合わせる。
  **原稿を触ったら必ず1回走らせる**

## 2. data/raw は読み取り専用

`data/raw/` の中身は書き換えない・上書きしない・整形しない。整形は `.qmd` で
行い、結果は `data/derived/` に書く。原データを直接直すと、どこで何が変わったか
が追えなくなる。

新しいデータを置いたら `data/raw/README.md` に**出所・取得日・利用条件**を書く
（`data/raw/` 自体は `.gitignore` で git に入らないので、この README だけが記録に残る）。

## 3. build/ の生成物は編集しない

`octavo build` が作るもの（`build/typst/`・`build/typst-slides/`・`build/word/` などの
中身）は、**編集しても次の build で消える。**直したいのは原稿か `.qmd` のほう。
`build/` に手で書くファイルは1つも無いので、丸ごと消してよい（git にも入らない）。

投稿先ごとの体裁（クラス・余白・題扉・行間）は **`papers/<name>/main.typ`**
（LaTeX なら `main.tex`）に書く。**原稿の隣にある、手で管理するファイル。**Octavo は
これを生成し直さず、組版のたびに `build/` へ写して使う（生成されるのは
`body.typ` / `abstract.typ` などの本文側）。

## 4. literature.bib は文献管理ソフトが正本

`literature.bib` は文献管理ソフト（Zotero など）から書き出したもので、次に書き出すと
**丸ごと上書きされる**ので、手で直しても消える。書誌の誤りは文献管理ソフトの側で直す。

- `octavo checkbib` — 本文が引いているキーが `.bib` にあるか、書誌が壊れていないか
- 直さないと決めた指摘は `octavo.config.py` の `bib_accepted` に理由付きで書く

## 5. 図・表・式・節は、番号ではなくラベルで指す

番号（見出しの「2.」、キャプションの「図1」）は**原稿に書かない**。組むときに
節ごと（図2.1・表2.1・式(2.1)）に振られる。原稿ではラベルを付けて、名前で指す:

| | 書き方 | 本文での参照 |
|---|---|---|
| 節 | `## 分析 {#sec-analysis}` | `@sec-analysis` → 第2節 |
| 図 | `![推移](../../figures/trend.png){#fig-trend}` | `@fig-trend` → 図2.1 |
| 表（原稿に書く） | マークダウンの表 + すぐ下に `: 記述統計 {#tbl-desc}` | `@tbl-desc` → 表2.1 |
| 表（分析が作る） | `: 記述統計 {#tbl-summary}` の1行だけ（`tables/summary.*` が入る） | `@tbl-summary` |
| 式 | `$$ … $$ {#eq-model}` | `@eq-model` → 式(2.1) |

- ラベルは `fig-` `tbl-` `eq-` `sec-` で始め、英数字と `-` `_` で書く。英数字以外で
  終わるので、日本語は空けずに続けてよい（`@fig-trendに示す`）。`[-@fig-trend]` は
  番号だけ（「2.1」）
- 節や図を足したり並べ替えたりしても、**参照を直す必要は無い**。無いラベルへの
  参照と、二重に付けたラベルは `octavo check` が止める
- 図の名前（`ov_figure(p, "trend")`）と表の名前（`ov_table(tab, "summary")`）は
  内容で付ける。番号は入れない。表のラベルは `tbl-<表の名前>` にすると、分析の
  表がそこに差し込まれる

図は `.png` を原稿に貼れば足りる（LaTeX 用の `.pdf` は Octavo が自動で探す）。
`ov_figure()` は両方を書き出す。パスは原稿から見た相対パスで書く（論文なら
`../../figures/`、スライド・講義なら `../figures/`。エディタのプレビューに出る）。

図・表・`{{…}}` は全部の原稿で共有する。論文の図をスライドに貼るときも、同じ
`figures/` のファイルを指せばよい（複製しない）。

## 6. ひな型は、ひな型だと分かるようにしてある

`octavo init` / `octavo new` が置いたものは**すべて例**で、そうと分かる印が入って
いる。中身を自分のものに置き換えたら、**印ごと消す。**

| 印 | どこに | 消え方 |
|---|---|---|
| `octavo:example` のコメント | 原稿・付録・`analysis.qmd`・`literature.bib` | 手で消す |
| `_placeholder` | `results/analysis.json` | `octavo analysis run` が書き直す |
| 枠と × だけの図 | `figures/trend.*` | `ov_figure()` が書き直す |
| 中身の無い表 | `tables/summary.*` | `ov_table()` が書き直す |

**`results/analysis.json` の仮の値は特に危ない。**分析を1度も走らせていなくても
`{{…}}` が全部解決してしまい、**嘘の数字の入った PDF が組める**。そうならないよう:

- `octavo check` は仮の値を**「致命的」**として止める
- `octavo build` は組むたびに `[値][注意] … 本文の数字は嘘` と言う
- `octavo values` も先頭で言う

印が残っているあいだは `octavo check` が「ひな型の残り」として数える。**仕上げる
前に0にする。**

# 手順

## 分析を足す・やり直す

1. `analysis/*.qmd` を編集する（データの読み込みは `data/` から）
2. `octavo analysis run` で走らせる（`octavo build` でも古ければ自動で走る）
3. `octavo values` で数値が出ているか確かめる
4. 原稿から `{{名前}}` で呼ぶ

`.qmd` を新しく足したら `octavo.config.py` の `analysis` が拾う（既定は
`analysis/*.qmd`）。重いデータを見張らせたいときは `deps` に足す。

## 分析の環境は .venv と renv で持つ（必ず）

**分析は素の R / Python では走らせない。**プロジェクトごとに環境を切り、
使ったパッケージを記録に残す。そうしないと、半年後の自分にも査読者にも
同じ結果が出せない。

- 用意する（clone のあとに戻す）のは `octavo env`: uv で `.venv` と
  `requirements.txt`、renv に knitr / rmarkdown
- Python: `.venv` の中でだけ動かす（`source .venv/bin/activate` か `uv run`）。
  パッケージは `requirements.txt` に版つきで足してから `octavo env`。
  ほかの場所に `pip install` しない
- R: renv のプロジェクトとして動かす。`install.packages()` のあとは必ず
  `renv::snapshot()`（`renv.lock` を commit する）

`.venv/` と `renv/library/` は git に入らない。**入るのは記録
（`requirements.txt` / `renv.lock`）だけ**なので、記録を怠ると環境が失われる。

プロジェクトは Linux・macOS・Windows のどれでも同じに動くように保つ:

- パスは相対パスで、`/` で書く（原稿・`.qmd`・設定のどこでも）。ドライブ名や
  `\` は書かない
- Python でテキストファイルを開くときは `encoding="utf-8"` を書く（Windows の
  既定はシステムの文字コード）
- ファイル名は大文字・小文字まで、原稿とコードに書いたとおりにする（Windows は
  `Fig1.png` と `fig1.png` を取り違えても通すが、Linux は通さない）

## 分析を複数の .qmd に分ける

分析が長くなったら分けてよい。`analysis/*.qmd` が拾うので、足すだけで登録される。
1本の `.qmd` が `results/<その .qmd の名前>.json` を持ち、本文からは区別なく
`{{名前}}` で呼べる。

**前段が後段の入力を作るとき**は、`octavo.config.py` で順に並べ、後段の `deps`
に前段の出力を入れる。ファイル名を `01-` `02-` で始めればグロブのままでもよい。

```python
'analysis': [
    {'src': 'analysis/01-clean.qmd', 'manual': True},        # data/derived/ を作る（重い）
    {'src': 'analysis/02-model.qmd', 'deps': ['data/derived/*']},
],
```

**データの整形のように時間がかかるものは別の `.qmd` にして `'manual': True`**
を付ける。`octavo build` もプレビューもそれを走らせず、古いと知らせるだけになる。
走らせるのは `octavo analysis run analysis/01-clean.qmd`（VS Code ならサイドバーの
「分析」のボタン）。

- 同じ名前を2つの `.qmd` が登録すると警告が出て**後が勝つ**。
  `octavo values` の出所欄で確かめる
- **`.qmd` を消したり名前を変えたら、対応する `results/*.json` も消す。**
  残すと本文が古い数値を拾い続ける（`octavo analysis` / `octavo values` が
  「対応する .qmd が無い値のファイル」として知らせる）

## 論文に付録を足す

付録は論文のフォルダの `appendix.md` に書く。同じフォルダにあれば自動で本文と
結びつく（要らなければ消してよい）。

```bash
octavo build <name> --appendix
```

`papers/<name>/main.typ` の `#show: octavo-appendix` と `#include "appendix.typ"`
のコメントを外す（LaTeX なら `main.tex` の `\appendix` と `\input{appendix}`）。

付録も本文と**同じ扱い**を受ける。`{{…}}` も引用も相互参照もそのまま働き、
`octavo values` `octavo checkbib` `octavo outline` は付録も見る。見出しに
「付録A」とは書かない: 付録の節は組むときに A, B, … と振られ、付録の図・表・式は
A.1 になる。ラベルは本文と付録をまたいで使える（本文から `@tbl-definitions`）。

## 原稿を書く・直す

```bash
octavo build                   # 全部の原稿を変換（分析が古ければ先に走る）
octavo build <name>            # 1本だけ
octavo values                  # {{…}} の未解決が無いか
octavo checkbib                # 引用キーが .bib にあるか
octavo outline                 # 見出し構成を見る
```

`octavo build --no-citations` は引用を解決せず速く回す（下書き確認用）。
`octavo build --no-analysis` は `.qmd` を走らせずいまの `results/` で変換する
（重い推定を待ちたくないとき）。

再推定したあとは **`octavo values --diff`** を見る。前に分析を走らせたときから
**本文のどの数字が動いたか**が出る。数字が動いたら、それを説明している
言い回し（「わずかに」「約」「有意に」）も直すこと。

## 仕上げる前に

```bash
octavo check          # 検査を1回にまとめる（致命的があれば非 0 で終わる）
octavo lint           # 直書きされた数値だけを詳しく
```

`octavo check` が見るもの: 原稿の実在 / 分析の鮮度 / 孤児になった値のファイル /
本文の `{{…}}` の未解決 / **仮の値のまま組もうとしていないか** / 引用キー /
書誌の傷 / **図と表のファイルが実在するか** / 仮の図 / ひな型の残り /
直書きの数値 / 分量 / データの指紋 / 分析環境の記録。

**「致命的」が出ているうちは投稿・配布しない。**「注意」は読んで判断する。

## データを差し替えたら

```bash
octavo data hash      # 指紋を記録し直す（data/HASHES.json は git に入れる）
octavo data status    # 記録と食い違っていないか
```

`data/` は git に入らないので、`data/HASHES.json` が「そのとき使ったデータ」の
唯一の記録になる。**差し替えた覚えが無いのに食い違うなら、それは事故。**

# 論文

## 投稿する

固め直しは:

```bash
octavo build <name>
octavo bundle <name>                 # submission-<name>.zip（パスを平らにして1つに）
octavo bundle <name> --dir --out example-talk   # zip にせずフォルダで
```

論文が1本だけなら `<name>` は省略できる。
### 匿名審査のとき

```bash
octavo build <name> --anonymous
octavo check --anonymous             # 自己引用の候補も出る
octavo bundle <name> --anonymous     # 著者名の残りを見てから固める
```

著者が分かる箇所は原稿側で条件付きブロックに入れておく。

```markdown
::: {.no-anonymous}
謝辞: 科研費…の助成を受けた。
:::
```

- `octavo bundle --anonymous` は、条件分岐で囲っていない著者名を見つけたら
  **失敗する**。消し忘れはここで止まる
- `octavo build --anonymous` を通していない出力は固めさせない
- 自己引用を Author (年) に伏せるかは雑誌の規定。ツールは**候補を挙げるだけ**

### 共著者から Word が返ってきたら

```bash
octavo review 20260907_draft_tanaka.docx
```

**docx を paper.md に書き戻さないこと。** 戻ってきた docx では `{{n_obs}}` が
既に「1,523」という文字になっていて、書き戻すと数値の出所が原稿に固定される
（このリポジトリの最重要の約束が壊れる）。`octavo review` は変更履歴と
コメントを**読むために**出す。反映は `paper.md` 側で手で行う。

### 改訂（R&R）のとき

投稿したところで版を刻んでおく。`octavo release` はタグ（論文の名前入り）を打ち、
投稿した PDF を GitHub Release に残す（`build/` は git に入らないので、現物はここに残す）。

```bash
octavo release example-paper v1-submitted     # タグ example-paper-v1-submitted + PDF
# …（査読・改訂）…
octavo values --diff example-paper-v1-submitted    # 投稿版から数字がどう動いたか
```

### 受理されたら

```bash
octavo bundle --replication          # 複製パッケージ（投稿用とは中身が別物）
```

原データは既定で入らない。再配布してよいデータか確かめてから
`--with-raw-data` を付ける。

## PDF まで出す

```bash
octavo build <name> --compile           # main.typ を組んで PDF にする
octavo build <name> --to docx           # 共著者に回す Word
# LaTeX で投稿するとき（TeX が要る。octavo setup --with-tex）
octavo build <name> --to latex && cd build/latex/<name> && latexmk -lualatex main.tex
```

# スライド・講義ノート

## 発表スライド

```bash
octavo build example-talk --compile        # slides/example-talk.md を PDF まで
```

## 講義ノート

講義ノート **1本から** A4 プリント（全回を1冊）と、**`#` 見出しの回ごとに別々の
スライド**を作る。`#` が1回分、`##` がスライド1枚。

```bash
octavo build example-lecture --to typst --compile           # A4 プリントを PDF まで
octavo build example-lecture --to typst-slides --compile    # スライドを回ごとに PDF まで
octavo build example-lecture-03 --to typst-slides           # 3回目だけ
```

- スライドの名前は `<講義ノートの名前>-01`, `-02`, …（`#` の出てきた順）。
  **途中に回を挿し込むと後ろの番号がずれる**ので、名前を固定したい回は見出しに
  id を付ける: `# 第2回 {#second}` → `example-lecture-second`
- 回のスライドの題扉は、その回の `#` 見出しが題、講義ノートの題が副題になる
- 最初の `#` より前はプリントにしか入らない

出し分けは条件付きブロックで書く。

```markdown
::: {.handout-only}
プリントにだけ出る（書き込み欄・詳しい注）
:::

::: {.slides-only}
スライドにだけ出る（図・短い問いかけ）
:::
```

## スライドに共通のこと

`##` が1枚（発表スライドの `#` は節の扉、講義ノートの `#` は回の区切り）。
図は枠に収まるように置かれ、番号は付かない。
`::: notes`（発表者ノート）は投影するスライドには出ず、台本（`--to typst-notes`）に出る。

授業資料・スライドにも `{{…}}` の数値差し込みが使える（同じ `results/` を読む）。
**論文と同じく、数値を手で書かない。**

# やらないこと

- **`results/*.json`・`figures/`・`tables/`・`build/` の生成物を手で書き換えない。**
  直したいのは常に `.qmd` か原稿のほう
- **原稿に分析結果の数字を直接書かない**（上の「守ること 1」）
- **`literature.bib` を手で編集しない**（文献管理ソフトの側で直す）
- **`data/raw/` を書き換えない**
- 数値が合わないとき、`{{…}}` を実数に置き換えて「とりあえず通す」ことをしない。
  値が無いなら `.qmd` に `ov_value()` を足すのが正しい直し方
- `octavo lint` が出した指摘を、確かめずに `lint_accepted` へ流し込まない。
  そこは「結果ではない」と判断したものだけを書く場所
- **共著者の docx を paper.md に書き戻さない**（数値の出所が固定される）
- **原稿を `octavo new` の置き場所の外に置かない**（`octavo.config.py` が拾わなくなる）
- **`data/HASHES.json` を手で書き換えない**。データを差し替えたときだけ
  `octavo data hash` で作り直す
- **ひな型の印（`octavo:example`）を、中身を書き換えずに消さない。**印は
  「ここはまだ例だ」という記録で、消すのは置き換えたときだけ
- `octavo.config.py` に知らないキーを足さない（起動時に警告が出る）

# 困ったとき

```bash
octavo doctor       # pandoc / LaTeX / Typst / quarto / R が揃っているか
octavo selftest     # 引用が実際にどう組まれるかを実物で見る
octavo analysis     # どの .qmd が古いか
```

`octavo` コマンド自体の仕様は Octavo 側の `README.ja.md` を見る。
