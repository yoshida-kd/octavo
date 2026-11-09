# Octavo リファレンス

> これはリファレンスの原稿です。**<https://yoshida-kd.github.io/octavo/ja/reference/>** で読めます。 <!-- pages:skip -->

このページは、Octavo のプロジェクトで作業する **AI アシスタント**と、細かいところまで知りたい人のために書いている。VS Code から Octavo を使う人は、[手引き](https://yoshida-kd.github.io/octavo/ja/guide/)を読めばよい。

同じ文章が Octavo に同梱されていて、入っている版に合ったものが読める:

```bash
octavo docs                       # 節の一覧
octavo docs 3.8                   # 番号で1つの節
octavo docs posters               # 見出しの言葉で
octavo docs --search slides_select   # その言葉が出てくる節すべて
octavo docs --all                 # 全部
```

`--lang ja` で日本語、`--lang en` で英語になる（既定は表示の言語）。そのプロジェクトの決まりはプロジェクトの `AGENTS.md` にある。このページは Octavo の仕組みを書いたもの。

---

## 1. 守ること

### 1.1 決まり

- **分析の結果を原稿に手入力しない。** 数値は分析から `{{name}}` で、図と表は `assets/` のファイルで入る。本文に結果の数字が書いてあれば、それは誤り（`octavo check lint` が見つける）。
- **図・表・式・節・ブロックの番号を手で書かない。** ラベルを付け（`{#fig-trend}`）、それで参照する（`@fig-trend`）。
- **生成物を直さない**: `build/` と `assets/`（値・図・表）。直すのは `.qmd`、`figures/*.typ`、`tables/*.csv`、原稿のほう。
- **`data/raw/` に書き込まない。** 分析が書くのは `data/derived/`。
- **`.bib`（`bib_file`。たいてい `literature/literature.bib`）を直さない。** 利用者の文献管理ソフトからエクスポートしたもの。`literature/priorwork/` も直さない（Priorwork の受け取り箱）。
- 原稿は **1行に1文** で書く（`octavo fmt` が外れているところを示す）。
- 時間のかかること・外に出ることは、実行する前に尋ねる: `manual` の分析の `octavo analysis run`、`octavo release`、`octavo bib tidy --apply`。
- 変更したら `octavo check` を実行する（致命的な問題があれば終了コードが 0 でない）。

### 1.2 プロジェクトの様子を調べる

ファイルを手で読むより、これを使う。どれも `--json` が付く。

```bash
octavo documents --json       # 文書の一覧: ファイル、作るもの、回とその行
octavo config --json          # 変えられる設定、その値と選択肢
octavo config --doc my-paper --json   # 1つの文書の設定（冒頭がプロジェクトに優先）
octavo analysis --json        # .qmd ごとに: 最新、古い、手動
octavo check values --json    # 本文の {{…}} と分析が書いた値
octavo check cites --json     # 引用キーと .bib
octavo check --json           # 提出前の全部
octavo doctor --json          # 何が入っているか
```

---

## 2. プロジェクト

### 2.1 プロジェクトの中身

```
study/
  octavo.config.py   プロジェクトの設定（Python の辞書、CONFIG = {...}）
  literature/        literature.bib と priorwork/（Priorwork が届けるもの）
  AGENTS.md          AI アシスタント向けのプロジェクトの決まり
  CLAUDE.md          1行、@AGENTS.md
  README.md
  docs/<name>/       <name>.md（原稿）、appendix.md、main.typ（論文の体裁）、main.tex
  analysis/          .qmd と octavo.R / octavo_helper.py
  data/raw/          入手したままのデータ（git に入れない。出所は README.md に書く）
  data/derived/      分析が作ったデータ（git に入れない）
  data/HASHES.json   data/ のハッシュ値（git に入れる）
  figures/           手で作る図: Typst で描く <name>.typ、共通部品 _parts.typ、写真
  tables/            手で作る表: <name>.csv
  notes/writing/     文章のルールと表現集（パック）
  templates/         Octavo のテンプレートのプロジェクト用のコピー
  assets/values/     <qmd>.json: {{…}} の数値
  assets/figures/    <name>.pdf と .png
  assets/tables/     <name>.typ・.tex・.md（表の中身だけ）
  build/             出力。出力ごとのフォルダ。消してよい
  requirements.txt   Python のパッケージ（git に入れる）
  renv.lock          R のパッケージ（git に入れる）
```

設定はフォルダをパターン（`docs/*/`、`analysis/*.qmd`）で登録しているので、文書や分析を足しても設定は書き換えない。

### 2.2 文書とその名前

文書は `docs/<name>/<name>.md` で、名前は `<name>`（`octavo build my-paper`）。隣の `appendix.md` がその付録。何を作るかは冒頭の `outputs:`（[4.1](#41-出力)）。回でできている文書には、スライドと台本のために回ごとの文書もある: 順に `<name>-01`、`<name>-02`、…、id のある回は `<name>-<id>`（[3.10](#310-回)）。`octavo documents` がすべてを示す。

### 2.3 プロジェクトに足す

```bash
octavo init study --lang en --with analysis,paper=my-paper   # 枠といくつかの部分
octavo init study --all --example                           # すべての種類を見本入りで
octavo new analysis model                     # analysis/model.qmd（1本目は octavo.R・data/ も）
octavo new analysis model --engine python     # Python で（octavo_helper.py も）
octavo new paper my-paper                     # docs/my-paper/my-paper.md と main.typ
octavo new paper my-paper --appendix          # appendix.md を足す（あとからでも）
octavo new paper my-paper --tex               # main.tex を足す
octavo new paper other --lang ja              # プロジェクトと別の言語の原稿
octavo new slides talk
octavo new lecture course
octavo new poster poster
octavo new figure dag                         # figures/dag.typ
octavo new table compare                      # tables/compare.csv
octavo env                                    # 分析の環境（.venv・renv）
```

`--example` は部分を見本で埋める。書いたものには印が付き（`octavo:example` のコメント、値の `_placeholder`、×の付いた箱の図）、`octavo check` が残りを数える。仮の値は `octavo check` で致命的。`--env` は同時に環境も用意する。ある文書に `new` すると、足りないファイルだけを足す。`new --json` は作ったものと、環境がまだかどうか（`env_needed`）を返す。

### 2.4 前の版で作ったプロジェクト

```bash
octavo migrate --docs --dry-run    # papers/<n>/paper.md、slides/、lectures/ -> docs/<n>/<n>.md
octavo migrate --syntax --dry-run  # ::: {.session}、::: {.slide}、.handout-only -> \session{}、\newslide、.no-slides
octavo migrate --rules --dry-run   # AGENTS.md の Octavo の節 -> 今の文章（差分を表示）
octavo migrate                     # CLAUDE.md だけのプロジェクトの決まりを AGENTS.md へ
```

どれも、コミットしていない変更があれば `--allow-dirty` なしでは断る。`--docs` は文書の名前を保ち、図のパスを直し、`outputs`/`sessions` を書き、設定に `docs/*/` を足す。`--syntax` は前後ですべての文書を組み、すべての出力が同じときだけ書き換えを残す。`--rules` は `<!-- octavo:section X -->` の部分をテンプレートのものに置き換える（その中に書いたものも置き換わる。最初の節より前は残る）。古い設定（`profile` / `targets` のある `papers/*/paper.md`）もそのまま組める。

---

## 3. 原稿の書き方

### 3.1 冒頭（front matter）

```markdown
---
title: Title of the Paper
subtitle: A subtitle
author: [Author One, Author Two]
institute: Example University
email: one@example.org
date: today
lang: en
outputs: [pdf, word]
abstract_word_limit: 150
---
```

- `title` などが、タイトル部分・表紙・タイトルスライドになる。`# Title` の見出しは書かない（`#` の見出しは節）。
- `date: today` は組んだ日。書式は `date_format`。
- `lang`（`ja` / `en`）は、プロジェクトと違うときの原稿の言語。
- その文書だけの設定もここに書ける（[5.2](#52-文書ごとの設定)）。
- `nocite: ["@key"]` は、引用していないが文献一覧に載せるもの。
- Octavo は冒頭を自前の小さな読み取りで読む: YAML のコメント（`# …`）は書かない。1行に1つの値、並びは `[a, b]`。

### 3.2 見出し・ラベル・参照

```markdown
# Analysis {#sec-analysis}

@fig-trend shows the trend and @tbl-desc the descriptive statistics.
We estimate @eq-model (see also [-@eq-model]).

![Trend](../../assets/figures/trend.png){#fig-trend}

| Variable | Mean |
|----------|------|
| x        | 1.2  |

: Descriptive statistics {#tbl-desc}

$$
y_i = \beta_0 + \beta_1 x_i + \varepsilon_i
$$ {#eq-model}
```

- `#` がいちばん上の節（論文は `##` から始めてもよい）。見出しに番号は書かない。
- ラベル: `fig-`、`tbl-`、`eq-`、`sec-`（またはブロックの種類。[3.3](#33-番号付きのブロック)）に、ASCII の英数字・`-`・`_` が続く。日本語をすぐ後ろに続けてよい（`@fig-trendに示す`）。
- `@fig-trend` は「図2.1」（英語では "Figure 2.1"）、`@eq-model` は「式(2.1)」、`@sec-analysis` は「第2節」、`[-@eq-model]` は番号だけ。
- 番号が付くもの: 見出し（`{.unnumbered}` / `{-}` を除く）、キャプションのある図と表、ラベルのある式。キャプションもラベルもない図表は数えない。
- `crossref_numbering`: `'document'`（通し番号。論文の既定）か `'section'`（2.1。講義ノート・スライド・ポスターの既定）。付録は A1 か A.1。
- `{.unlisted}` は見出しを目次に載せない。
- 無いラベル・二重のラベルで `octavo check` は止まる。使っていないラベルは注意。

### 3.3 番号付きのブロック

```markdown
::: {.question #question-why title="Why is government the main actor?"}
Why is government at the centre of public policy?
:::

::: nb
Unnumbered blocks need no label.
:::

::: {.restate #question-why}
:::

::: {.list-of .question}
:::
```

| 種類 | 番号 |
|---|---|
| `case`、`question` | 1つの通し（事例1.1、論点1.2） |
| `theorem`、`lemma`、`proposition`、`corollary`、`definition`、`example` | もう1つの通し |
| `aside`、`nb`、`memo`、`remark` | なし |

- ラベルは種類から始める（`#question-why`）。`@question-why` は「論点1.2」。
- `restate` は番号付きでもう一度示す。`list-of` は指定した種類をすべて並べる（`.titles` は番号・題・ページだけ、`.list-of` だけなら番号付きのすべての種類）。
- 番号は図と同じく `#` の節ごとに戻る。Word では段落スタイル `Theorem`。
- 設定の `theorem_envs` で名前を変えたり種類を足したりする:

```python
'theorem_envs': {
    'case': 'Example case',
    'claim': {'name': {'ja': '主張', 'en': 'Claim'}, 'counter': 'case'},
    'hint': {'name': 'Hint', 'numbered': False},
},
```

### 3.4 数式

```markdown
The estimate is $\hat\beta = {{coef_x:.3f}}$, with $y_i \sim \mathcal{N}(\mu, \sigma^2)$.

$$
\begin{aligned}
y_i &= \beta_0 + \beta_1 x_i + \varepsilon_i \\
\operatorname{Var}(\varepsilon_i) &= \sigma^2
\end{aligned}
$$
```

- LaTeX の書き方で書く。Typst の数式、Word の数式になり、LaTeX ではそのまま。
- `$…$` の内側に空白を入れない。ドル記号そのものは `\$`。別行立ての式は前後に空行を置いて単独の行に。`align` ではなく `aligned`。
- 1行の `\newcommand{\E}{\mathbb{E}}` はどこに書いても（本文でも付録でも）全体で効く。演算子は `\newcommand{\Cov}{\operatorname{Cov}}`（`\DeclareMathOperator` ではなく）。
- 桁区切りのある値は数式の外に置く（`$N$ = {{n_obs}}`）。

### 3.5 図

```markdown
![Officials by level of government[^src]](../assets/figures/staff.png){#fig-staff width=70%}

::: {.figure-note}
Source: National Personnel Authority, *Annual Report 2025*.[^checked]
:::

[^src]: Full-time staff only.
[^checked]: Retrieved 1 October 2026.
```

- パスは原稿からの相対: `docs/<name>/` からは `../../assets/figures/x.png`。`.png` と書く。Typst と LaTeX は隣の `.pdf` を、Word は `.png` を使う（`figure_ext` で変えられる）。
- `figure_width` が既定の幅。`{width=…}` で個別に（スライドでは無視され、残りの場所いっぱいになる）。
- 図の直後（表ならキャプションの行の後）の `::: {.figure-note}` に出典や注を書く: 小さな字で同じページに、キャプションには入らない。
- 写真は `figures/` に置いてそこから貼る。`.jpg` と `.png` はどの出力でも使える。Octavo は縮めない。
- **Typst で描く図**: `figures/<name>.typ`（`octavo new figure <name>` が `diagram(nodes, edges)` 付きで書く）を、それか `figures/_*.typ` が変わるたびに `octavo build` が `assets/figures/<name>.pdf` と `.png` に描く。Typst の根はプロジェクトなので、`json("/assets/values/analysis.json")` で分析の数値が読める。

```typst
#diagram(
  (
    z: (2, 0, [Background $Z$]),
    x: (0, 1.6, [Education $X$]),
    y: (4, 1.6, [Income $Y$]),
  ),
  (("z", "x"), ("z", "y"), ("x", "y")),
)
```

### 3.6 表

- **原稿の中に**: Markdown の表の下に `: Caption {#tbl-name}`。
- **分析から**: `ov_table(tab, "summary")` が `assets/tables/summary.{typ,tex,md}`（中身だけ）を書く。原稿はキャプションの行だけで置く: `: Descriptive statistics {#tbl-summary}`。
- **手で作る**: `tables/<name>.csv` を `octavo build` が同じ3つのファイルにし、同じように置く。1行目が見出し。中身のあるセルの右の空いた1行目のセルはそれと結合し、そのとき2行目も見出しになる。数字だけの列は右寄せ、長い文の列は折り返す。セルは文字としてそのまま。UTF-8（BOM 付きも可）か Shift_JIS を読む。Octavo は BOM を書かない。VS Code では表として編集できる（「表として編集」）。
- `assets/tables/` に、どちらが作ったのでもないファイル（`octavo build が … から作った` の見出しも `octavo:placeholder` もない）があれば、上書きしないようにビルドを止める。

### 3.7 引用

- `@key`、`[@key, p. 3]`、`[@key; @key2]`、`[-@key]`（年だけ）。所有格は `\poscite{key}`（"Smith and Taylor's (2003)"。日本語では後ろに「の」を書く）。
- 文献一覧は最後に入る。論文の最後の節の `# References` は場所を示すだけ。別の場所に置くには `::: {#refs}` + `:::`。
- `@PRIORWORK:<doi>` / `@{PRIORWORK:<doi>}` は、Priorwork が引用したがまだ `.bib` にない論文の印（[7.3](#73-priorwork)）。
- `@fig-…`、`@tbl-…`、`@eq-…`、`@sec-…` とブロックのラベルは参照で、引用ではない。

### 3.8 一部の出力にだけ入れる

```markdown
::: {.no-slides}
Fill-in-the-blank space and detailed footnotes: handout only.
:::

::: {.slides-only}
Figures and short prompts: slides only.
:::
```

| クラス | 残るところ |
|---|---|
| `.no-slides` | スライドと台本のほかすべて（ふつうの「プリントだけ」） |
| `.slides-only`（`.slide-only`） | スライドと台本 |
| `.pdf-only`、`.word-only`、`.tex-only`、`.poster-only` | その出力だけ |
| `.print-only` | PDF・Word・LaTeX |
| `.screen-only` / `.no-screen` | 投影するスライドだけ / それ以外すべて（`slides-handout` と使う） |
| `.no-anonymous` / `.anonymous-only` | `--anonymous` で落とす / そのときだけ残す |
| `.on-slides` / `.on-poster` | `slides_select` / `poster_select` が `marked` のとき、スライド・ポスターに選ぶ |

- `only-X`、`X-only`、`no-X`、`not-X` は、どの出力名・バックエンド名・プロファイルでも使える。
- 行の中では `[words]{.slides-only}`。箇条書きの中ではフェンスを字下げしてよい。**開きの `:::` の前には空行が要る**（pandoc が文字として出してしまうものと、どの出力にも当たらないクラスを `octavo check` が知らせる）。
- `::: notes` は話すことのメモ。台本（と Beamer）だけに残る。
- 結果でない数字は `[40%]{.no-lint}` か `::: {.no-lint}` で `octavo check lint` から外す。設定の `lint_accepted` に認める文字列を並べてもよい。
- 前の `.handout-only` もまだ使える（講義ノートでは `.no-slides` と同じ）。

### 3.9 改ページ・スライドの区切り・スライドの題

```markdown
## A long heading for the handout {slide-title="Short title"}

\newslide

### A heading that stays on the same slide {.same-slide}

\newslide{Another title}
```

- `\newpage`（か `\clearpage`）を単独の行に: PDF・Word・LaTeX で改ページ。
- `\newslide`: 前のスライドの題に「（続き）」を付けた新しいスライド。`\newslide{Title}` で題を、`\newslide{}` で題なし。スライド以外では無視。前の書き方は `::: {.slide title="…"}` + `:::`。
- `{.same-slide}`: 見出しを今のスライドに太字で置く。
- `{slide-title="…"}`: スライドでだけ別の題（回の `#` ならスライドの束の題）。
- 見出しの `{.no-title}`: 題を出さない新しいスライド（プリントには見出しが残る）。
- はみ出したスライドは「題（続き）」の新しいスライドに続き、ビルドがそう言う。題のないスライドのはみ出しは知らせるだけ。
- **スライドの階層**: スライドだけの文書（`outputs: [slides]`）で `#` と `##` があれば `##` が1枚、1階層だけなら見出しごとに1枚。講義ノートではノート全体から1度だけ決める: ふつうは `#` が回、`##` が節、`###` が1枚。

### 3.10 回

```markdown
\session{Session 3: policy and government} {#third subtitle="Public policy" date="2026-10-14"}
```

- 冒頭に `sessions: true`: `#` の見出しごとに1回（回ごとにスライドの束と台本が1つ）。見出しの `{#id}` が名前になり（`<name>-<id>`）、なければ `<name>-01`、`-02`、…。
- **区切り**: `\session{…}` の行（か前の `::: {.session …}`）が1つでもあれば、区切りが回を決め、`#` はふつうの見出しになる。波かっこの中が題（空なら回の最初の見出しが題になる）。`{…}` には `#id`、`subtitle`、`date`、`author`、`institute`。最初の区切りより前はプリントだけ。
- 区切りの後に何もない回はスライドを作らない。なくなった回のスライドは次のビルドで消える。
- 回はプリントでも改ページから始まる。スライドの番号はプリントの番号。

### 3.11 脚注・URL・付録

- `[^name]` + `[^name]: text`、または行の中に `^[text]`。講義ノートでは脚注の本文を同じ回に書く（ほかの回に書いた脚注はその回のスライドから見えない）。
- `<https://…>` は URL が見えるリンク。`[words](https://…)` は印刷すると URL が見えない。
- `# Title {.appendix}` からが付録（A、B、…）。論文の `appendix.md` も同じ。プリントでは本文・文献・付録の順（別の PDF にすることは [4.2](#42-論文) と [4.3](#43-講義のプリント)）。

### 3.12 1行に1文

```bash
octavo fmt my-paper            # 文の途中の改行、1行に複数の文がある所を示す
octavo fmt my-paper --apply    # 書き換える
```

`fmt` は文の途中の改行をつなぎ、日本語の行をかっこの外の「。」ごとに改行する。コード・数式・コメント・表・見出し・`:::` の行・強制改行には触れず、英語の行は分けない。

---

## 4. 出力

### 4.1 出力

| 出力 | 作るもの | 置き場 |
|---|---|---|
| `pdf` | PDF。原稿の横に `main.typ` があれば論文の体裁、なければ組み込みの A4 プリント | `build/pdf/<name>.pdf`（論文は `build/pdf/<name>/main.pdf` とそのコピー `build/pdf/<name>.pdf`） |
| `slides` | スライド（回ごとに1つ） | `build/slides/<name>.pdf`、`<name>-slides-<session>.pdf` |
| `slides-handout` | `.screen-only` を除き `.no-screen` を入れたスライド | `build/slides-handout/` |
| `script` | 縮めたスライドとその `::: notes`（A4） | `build/script/<name>-notes.pdf`、`<name>-notes-<session>.pdf` |
| `poster` | ポスター | `build/poster/<name>.pdf` |
| `word` | Word | `build/word/<name>.docx` |
| `tex` | LaTeX のソース（原稿の横に `main.tex` があればそれ）。組むには TeX が要る | `build/tex/` |
| `beamer` | LaTeX のスライド | `build/beamer/` |

```bash
octavo build                          # every document, every output it names
octavo build my-paper --to word       # one document, one output
octavo build --compile                # typeset to PDF as well
octavo build course-third --to slides # one session's deck
octavo build --to all --compile
octavo targets                        # the output names
```

- `outputs:` がなければ `pdf`。前の名前（`typst`、`typst-slides`、`typst-notes`、`docx`、`latex`）と `targets:` も同じように読む。
- `--no-analysis` は分析を実行せずに組む。`--json` は出力の場所（`compiled`）を返す。
- `octavo watch` は保存のたびに組み直す。

### 4.2 論文

- 原稿の横の `main.typ` は利用者が手で持つ体裁。今のものはほぼ空で、`#show: octavo-article.with(…)` だけ。体裁そのものは `article.typ` で、ビルドのたびに横に書き直す（日本語は LaTeX の jsarticle、英語は article 11pt に倣う）。題・著者・`institute`・`email`・日付は冒頭から入る（`octavo-article.with` の `auto`）。そこに書けば上書きする。投稿先に合わせる変更は `#show` の行の後に書くか、`octavo template copy paper/article.typ`。
- 1ページ目に分量（注を除いた・含めた語数または字数、要旨、図・表の数）が出る。`counts: none` で消える。
- `# Abstract` が要旨。`article.typ` より前に作った論文は自分の `main.typ` のまま。移るには `main.typ` の名前を変えて `octavo new paper <name>`。
- 付録（`appendix.md`）は別の PDF `build/pdf/<name>-appendix.pdf` になり、A-1、A-2、… と番号が付く。本文と付録の間の参照は番号の文字で入る。`appendix_separate: false` で本文の後ろに1つの PDF にする。
- `--anonymous` は [8.2](#82-匿名の査読)。

### 4.3 講義のプリント

`pdf` に `main.typ` のない文書は、組み込みの A4 の体裁になる: 表紙、i、ii、… の目次、1から始まる本文、jsarticle に倣った組み方（11pt、1ページ36行）、BIZ UDゴシックと Inter。

| キー | 既定 | 内容 |
|---|---|---|
| `first_section` | `1` | `0` でガイダンスの回を「0」にする |
| `pagebreak` | `'session'` | `'section'`: `#` ごと、`None`: 区切りでだけ |
| `font`、`fontsize` | BIZ UDゴシック + Inter、`'11pt'` | |
| `toc` | `sessions` のときオン | 目次 |
| `date_format` | `'%Y年%-m月%-d日'`（英語は `'%B %-d, %Y'`） | |
| `appendix_separate` | `True` | 付録を `<name>-appendix.pdf` に |
| `appendix_after_references` | `True` | `False`: 本文・付録・文献の順 |

**回ごとの PDF** は、全体を組んだものから切り出す（ページ番号・目次・番号は全体のまま）:

```bash
octavo build course --sessions                     # build/handouts/course-<session>.pdf
octavo extract course --session third --cover      # 1つ以上の回（カンマ区切り）を表紙付きで
octavo extract course --pages 12-19                # 印刷されたページ番号で
```

### 4.4 スライド

| キー | 既定 | 内容 |
|---|---|---|
| `slides_aspect` | `'16-9'` | `'4-3'` |
| `slides_accent` | `'#0e2f92'` | `None` で黒だけ |
| `slides_numbering` | `None` | 見出しの番号（`'1.'`、`'1.1'`） |
| `slides_section_slides` | `False` | `#` の節ごとに区切りのスライド |
| `slides_running_header` | `True` | 左上に節の名前 |
| `slides_font` | BIZ UDゴシック + Inter | |
| `slides_bibliography` | 講義のスライドは `slide`、発表は `off` | `slide`、`off`、`sheet`（A4 の `<deck>-references.pdf`）、`both` |
| `slides_select` | `all` | `marked`: `.on-slides` の部分とその上の見出しだけ |

前の名前 `typst_slides_*` も読む。図はスライドの残りの場所に合わせる。

### 4.5 ポスター

```markdown
---
title: Counting how policy is made
author: [Author One, Author Two]
institute: Example University
event: Example Conference 2026
date: 2026-10-14
logo: ../../figures/logo.png
qr: https://example.org/paper
qr_label: The paper
outputs: [poster]
poster_grid: 3x2
poster_rows: [2, 1]
---

# Question

# Results {span=2}

# Notes {cell="3,2"}
```

| 書き方 | 意味 |
|---|---|
| `#` の見出しごと | 1つのマス。左上から順に埋める |
| `{span=2}` / `{rows=2}` | 2列分の幅 / 2行分の高さ |
| `{cell="3,2"}` | 3列目・2行目（1から数える） |
| `poster_size` | `a0`（既定）、`a1`、`a2`、`b0`、`b1`（JIS の B）、または `1189x841mm` |
| `poster_orientation` | `portrait`（既定）、`landscape` |
| `poster_grid`、`poster_rows` | 列 x 行（`2x3`）、行の高さの比 |
| `logo`、`qr`、`qr_label` | 題の帯の左のロゴ、右の QR コード |
| `poster_select: marked` | `.on-poster` の部分だけ（論文からポスターも: `outputs: [pdf, poster]`） |
| `poster_font` | 書体 |

マスに収まらない中身はビルドのときに知らせ、PDF に赤で示す。置けないマスがあればビルドを止める。

### 4.6 Word と LaTeX

- Word では見出し・キャプション・式に番号を文字で書き入れ、参照はリンクにする。`octavo template copy word` で `templates/word/reference.docx` を書き出し、Word でスタイルを直す（別のものは `docx_reference`）。
- LaTeX には TeX が要る（Linux では `octavo setup --with-tex`）。論文の横の `main.tex` がその体裁で、Octavo は latexmk を実行しない。Octavo のテストは LaTeX を組んでいない。

---

## 5. 設定

### 5.1 octavo.config.py

`CONFIG = {...}`、Python の辞書。知らないキーは注意が出る。主なキー:

| キー | 内容 |
|---|---|
| `documents` | どのファイルが文書か（`{'docs': {'src': 'docs/*/'}}`） |
| `analysis` | `.qmd`: `[{'src': 'analysis/*.qmd'}]`、`manual`、`deps` も |
| `bib_file` | `.bib` |
| `csl`、`csl_locale` | 引用のスタイル（zotero.org/styles の ID かパス）とそのロケール |
| `japanese_citation_form`、`citations_by_language` | 文献一覧の日本語文献（[7.1](#71-bib-とスタイル)） |
| `lang` | プロジェクトの言語（`ja` / `en`） |
| `meta` | `title`、`author`、`affiliation`、`email` の既定 |
| `crossref_numbering` | `'document'` / `'section'` |
| `theorem_envs` | 番号付きブロックの種類 |
| `figure_width`、`figure_ext` | 図 |
| `values_dir`、`figure_dir`、`table_dir`、`figure_src_dir`、`table_src_dir` | フォルダ |
| `value_float_format`、`value_thousands_sep` | 数値の見え方 |
| `word_limit`、`char_limit`、`abstract_word_limit`、`abstract_char_limit` | 投稿の分量の上限 |
| `anonymous_drop_meta` | `--anonymous` で消す冒頭のキー |
| `lint_accepted`、`bib_accepted` | 認める検出 |
| `slides_*`、`poster_*`、`first_section`、`pagebreak`、`font`、`fontsize`、`toc`、`date_format` | 見た目（[4](#4-出力)） |
| `appendix_separate`、`appendix_after_references` | 付録 |
| `docx_reference` | Word のスタイル |
| `zotero_collection`、`zotero_linked`、`zotero_write` | Zotero（[7.2](#72-zotero)） |
| `writing`、`writing_off` | 文章のルールのパック（[9](#9-ai-アシスタントのための文章のルール)） |
| `replication_exclude` | 再現用パッケージから除くもの |
| `out_dirs` | 出力の置き場 |

### 5.2 文書ごとの設定

次のキーは原稿の冒頭にも書け、そのときはその文書だけに効く（名前は設定と同じ）: `outputs`、`sessions`、`lang`、`csl`、`csl_locale`、`reference_section_title`、`japanese_citation_form`、`citations_by_language`、`crossref_numbering`、`word_limit`、`char_limit`、`abstract_word_limit`、`abstract_char_limit`、`slides_*`、`poster_*`、`first_section`、`pagebreak`、`font`、`fontsize`、`toc`、`date_format`、`appendix_separate`、`appendix_after_references`、`writing`、`writing_off`。綴りを誤ったキーはビルドのときに知らせる。ビルドは `[settings] 原稿から: …` と表示する。

### 5.3 コマンドで設定を変える

```bash
octavo config                                  # 設定とその値
octavo config set slides_aspect 4-3            # octavo.config.py の1行
octavo config unset slides_aspect
octavo config --doc my-paper set word_limit 8000   # 原稿の冒頭の1行
```

`set` は書く前に確かめ、複数行にわたる値は書き換えない。

---

## 6. 分析

### 6.1 結果が原稿に届くまで

```
analysis/*.qmd  --quarto-->  assets/values/<qmd>.json   本文の {{name}}
                             assets/figures/*.pdf|png   図
                             assets/tables/*            表
```

Octavo は R を読まず、Quarto の出力も読まない。`quarto render` を実行し、このファイルを読むだけ。`.qmd` ごとに `assets/values/<その名前>.json` を持ち、原稿からはすべてが見える（同じ名前が2つにあれば注意が出て、後のものが勝つ）。値のない名前は `{{name}}` のまま残り、知らせる。

### 6.2 R の補助（octavo.R）

```r
source(if (file.exists("octavo.R")) "octavo.R" else file.path("analysis", "octavo.R"))

ov_value("n_obs", nrow(d))              # {{n_obs}}
ov_value("coef_x", coef(m)[["x"]])      # {{coef_x}}、{{coef_x:.2f}}
ov_value("p_x", ov_pval(pv))            # ".023"、"< .001"
ov_figure(p, "trend")                   # ggplot か描く関数 -> trend.pdf、trend.png
ov_table(tab, "summary")                # データフレーム -> summary.typ、.tex、.md
```

- この `source()` の行は、Render のとき（作業フォルダは `analysis/`）にも、チャンクだけを実行するとき（Run Cell。プロジェクトの直下）にも `octavo.R` を見つける。よそから持ってきた `.qmd` も同じ行にする。
- `ov_figure(x, name, width, height)`、`ov_table(x, name, notes, align, groups, indent, size)`: `groups = c(Demand = 1, Hiring = 6)` は1行目と6行目の前に見出しの行を入れ、その下の行を字下げする。`size = 9.5` はポイントでの文字の大きさ。
- `ov_palette(n)`、`ov_tint(col, 0.6)`、`ov_scale_colour_cud()`、`ov_scale_fill_cud()`: どの色覚でも見分けられる色。
- Render の外（チャンクだけの実行）では、どの `.qmd` のものか分からないので、`ov_value()` は値を
  表示するだけで何も記録しない。`options(octavo.values = "<qmd の名前>")` を指定すれば書く。図と表の
  関数はいつもどおり書く。
- `ov_root()` はプロジェクトのフォルダ（`file.path(ov_root(), "data", "raw", "x.csv")`）。
- `octavo.R` に要るのは素の R だけ（ggplot を渡したときだけ ggplot2）。値のファイルの `_session` に R とパッケージの版を残す。

### 6.3 Python の補助（octavo_helper.py）

```python
ov_value("n_obs", len(d))
ov_value("coef_x", model.params["x"])
ov_figure(fig, "trend")
ov_table(tab, "summary")
```

名前も書くファイルも R と同じ。`ov_table` の groups は0から数える。`ov_style()`（図を作る前に）は日本語の書体と埋め込める書体を設定する。要るのは標準ライブラリだけ（渡されたときだけ matplotlib・pandas）。`requirements.txt` には `ipykernel`、`nbformat`、`nbclient`、`pyyaml` が入る。

### 6.4 数値の見え方

| 値 | 例 | 表示 |
|---|---|---|
| 整数 | `nrow(d)`、`len(d)` | `1,523` |
| 小数 | `coef(m)[["x"]]` | `0.342`（`value_float_format`、3桁） |
| 文字 | `ov_pval(p)` | そのまま |

本文の `{{name:.2f}}` か `ov_value(..., fmt = ".2f")` で書式を決める。ちょうど整数になる小数も小数のまま（`2.000`）出る。わざとそうしている。

### 6.5 分析を実行するとき

```bash
octavo analysis                   # 古くなった .qmd
octavo analysis run               # 古いものをすべて実行（手動のものも）
octavo analysis run analysis/02-model.qmd   # これを、最新でも実行
octavo analysis mark-fresh analysis/00-fetch.qmd   # 実行せずに最新として記録
octavo analysis run --keep-cache   # 実行結果も残す（analysis prose のため）
octavo analysis prose analysis/02-model.qmd   # 地の文だけ変わった: コードを実行せず HTML を更新
octavo check values --diff        # 前回の実行で変わった本文の数値
octavo check values --diff my-paper-v1-submitted   # git のタグから
```

- `octavo build` は、`.qmd` か `deps` のファイルの中身が前回の実行から変わったときに実行する（ブランチの切り替えや clone し直しでは古くならない）。`.qmd` が失敗すればビルドを止める。Quarto がなければ注意だけ。
- `manual: True`（時間のかかるデータの整形・取得）: `octavo build` は実行せず、古いことを知らせるだけ。
- 1つがもう1つの材料になるときは順に並べる。実行がそこに来たときに古さを確かめ直す。

```python
'analysis': [
    {'src': 'analysis/01-clean.qmd', 'manual': True},
    {'src': 'analysis/02-model.qmd', 'deps': ['data/derived/*']},
],
```

- `.qmd` が自分の冒頭で同じことを言ってもよい（設定にそのファイルの項目があればそちらが勝つ）:

````markdown
---
title: "Fetch the raw data"
octavo:
  manual: true
---

```{r}
out <- "../data/raw/survey.csv"
if (file.exists(out)) knitr::knit_exit("Already fetched. Move the file away to fetch again.")
```

```{r}
download.file("https://example.org/survey.csv", out)
```
````

- 生データの取得は専用の `analysis/00-fetch-<source>.qmd`（手動）にし、ファイルがあれば取得を飛ばし（`knitr::knit_exit()` を単独のチャンクに）、出所と日付を `data/raw/README.md` に書く。

### 6.6 環境とパッケージ

```bash
octavo env                          # requirements.txt から .venv（uv）。renv に knitr・rmarkdown と .qmd が使うパッケージ
octavo analysis missing analysis/model.qmd   # 使っているのに入っていない R のパッケージ
octavo analysis install analysis/model.qmd   # それをプロジェクトの renv に入れる
```

- `octavo env` は `library(x)` / `x::f()` が使うパッケージをすべて入れる。R の `.qmd` が失敗したときは、それが使っていて足りないものを入れてもう一度実行する。どちらも `renv.lock` に記録する。CRAN にないものは、入れるコマンド（`renv::install("user/repo")`）とともに名前を出す。
- R で `install.packages()` したら `renv::snapshot()`。git に入れるのは `requirements.txt` と `renv.lock` で、ライブラリそのものは入れない。
- Linux では、パッケージは Posit Package Manager からビルド済みで入る。読み込むときにシステムのライブラリが要るものがある（quanteda.textplots が使う igraph は GLPK が要る）: `octavo setup` が入れ、`octavo doctor` が知らせ（「システムのライブラリ」）、「cannot open shared object file」で失敗したときは apt の行を出す。
- 記録はあるが使っていないパッケージについての `renv::status()` の「out-of-sync」は害がない。
- Python の分析だけのプロジェクトには renv を作らない。`octavo analysis run` は `.venv` を自分で使う。

### 6.7 .qmd だけのプロジェクト、ほかの言語

プロジェクトに原稿がなくてもよい: Quarto で書くレポートは `analysis/` に置き、`octavo env` / `octavo analysis run` が面倒を見る。原稿がないことを `octavo check` と `octavo build` は問題にしない。出力は `.qmd` の横にできる。Quarto の Typst の PDF で原稿と同じ書体を使うには:

```yaml
format:
  typst:
    papersize: a4
    include-in-header:
      text: |
        #set text(font: ((name: "Libertinus Serif", covers: "latin-in-cjk"), "BIZ UDMincho", "Noto Serif CJK JP"))
```

ほかの言語も、`assets/values/<任意>.json` に `{"name": value}` を、`assets/figures/` に図（`.pdf` と `.png`）を、`assets/tables/` に表を書けば使える。

---

## 7. 文献・Zotero・Priorwork

### 7.1 .bib とスタイル

- `bib_file`（新しいプロジェクトは `literature/literature.bib`）は文献管理ソフトからエクスポートする（Zotero なら Better BibTeX の「自動更新」でキーが変わらない）。Octavo は書かない。
- `csl` がすべての出力のスタイル。`octavo csl get <id>` で取得し、`octavo csl list` で手元にあるものを示す。
- 日本語の文書では、`langid = {japanese}` の文献はスタイルによらず1つの日本語の形になる。`japanese_citation_form`: `standard`（山田太郎・田中花子 (2020)「題」『誌名』12(3): 1–20.）、`fullwidth`（（2020）…12巻3号、1–20頁。）、`period`（．2020．…）。`citations_by_language: False` で全体を `csl_locale` で組む。`.bib` の日本語の名前にはカンマが要る（`山田, 太郎`）。

### 7.2 Zotero

```bash
octavo bib collections            # コレクションの一覧（入れ子）
octavo bib pull                   # zotero_collection（とその下）から .bib を取得
octavo bib login --user-id 1234567   # ウェブ API のキー（標準入力から読む）
octavo bib tidy                   # 案: 引用しているのにメインにないもの、メインにあるのに引用していないもの
octavo bib tidy --apply --keys smith2020,doe2019
```

- `zotero_collection` はメインのコレクション（名前、パス `'A / B'`、またはその並び）で、`.bib` に入るのはこれ。`zotero_linked` はそれに材料を出すコレクション（サーベイごとに1つ）で、`.bib` には入らない。
- 同じ機械の Zotero はローカル API で読む（Better BibTeX が先）。なければウェブ API で、キーは `~/.config/octavo/zotero.env`（プロジェクトには置かない）。
- `bib tidy --apply` には `'zotero_write': True` と書き込みのできるキーが要る。メインのコレクションへの出し入れだけで、項目を消したり直したりしない。Better BibTeX で引用キーを固定していない項目は外さない。実行する前に利用者に尋ねる。

### 7.3 Priorwork

Priorwork（先行研究サーベイの別のツール）は `literature/priorwork/` に書く: `<survey>.md`（本文。`.bib` のキーで引用する）、`<survey>.json`（目録。`draft`、`synthesis`、`complete`）、`<survey>.cards.json`（論文ごとのカード）。ほかの場所には書かない。

```bash
octavo priorwork                  # 届いたもの
octavo priorwork resolve --dry-run   # @PRIORWORK:<doi> -> .bib のキー（論文が .bib に入ったら）
octavo priorwork link             # サーベイのコレクション -> zotero_linked
octavo priorwork cards --json     # カード（引用キーごと）
octavo priorwork ask --workspace <folder> --kind start
octavo priorwork requests
```

**届いたものを原稿に取り込む**: 本文を原稿と合わせて読む。`complete` では、足す文がどの文に属するかを引用している（「場所」/ "Where"）。どこに入れるかを提案して利用者の答えを待ち、引用は書かれたまま残し、受け取り箱は直さない。`octavo check cites` は `PRIORWORK:` の印を分けて示し、Priorwork が要旨しか読んでいない引用文献を知らせる。

---

## 8. 確かめる・投稿の後

### 8.1 octavo check

```bash
octavo check                 # 全部。致命的な問題があれば終了コードが 0 でない
octavo check --strict        # 注意も数える
octavo check values          # {{…}} と値
octavo check cites           # 引用キーと .bib、.bib の問題
octavo check lint            # 本文に手入力した結果、ずれた入れ子の箇条書き
```

致命的: 図や表のファイルがない、解決しない `{{…}}`、仮の値、古い分析、無い引用キー、無い・二重のラベル、分量の上限を超えた。注意: ひな型の残り、使っていないラベル、`:::` の問題、文章のルールの名前、データのハッシュ値。

### 8.2 匿名の査読

```markdown
::: {.no-anonymous}
Acknowledgements: this research was funded by ...
:::
```

```bash
octavo build my-paper --anonymous
octavo bundle my-paper --anonymous     # まとめたファイルに著者名がないかも確かめる
```

`--anonymous` は `.no-anonymous` を落とし、`.anonymous-only` を残し、`anonymous_drop_meta` のキーを消し、`main.typ` のタイトル部分を切り替える（`flags.typ`）。次のふつうのビルドで元に戻る。

### 8.3 送った後

```bash
octavo bundle my-paper                 # submission-my-paper.zip。投稿システム向けに1つのフォルダにまとめる
octavo review returned.docx            # 共著者の変更履歴とコメント
octavo release my-paper v1-submitted   # タグ my-paper-v1-submitted と、GitHub Release に PDF（gh）
octavo data hash                       # data/HASHES.json
octavo data status                     # それから data/ が変わったか
octavo data track data/raw/typed.csv   # data/ の中のファイルを1つ git に入れる
octavo bundle --replication            # 分析・値・図・表・設定・ハッシュ値
octavo bundle --replication --standalone  # 同じものを、ヘルパーのいらない .qmd で
octavo bundle --replication --standalone --verify   # パッケージそのものを実行して確かめる
```

- `review` は読むだけ。戻ってきた `.docx` を原稿に戻すことはしない（数値が手入力の文字になっている）。変更は原稿に入れ直す。
- `release` は、コミットしていない変更・仮の値・古い分析があれば断り、分析は実行しない。先に利用者に尋ねる。
- `--replication` は、`--with-raw-data` がなければ生データを入れない。
- `--standalone` は、パッケージの中の複製だけを書き換える（プロジェクトの `.qmd` は変えない）。`ov_value()` は値の表示に、
  `ov_figure()` は `ggsave()` / `savefig()` に、`ov_table()` は CSV の書き出しに、`ov_root()` は相対パスに、`ov_pval()` / `ov_tint()` は
  ファイルの中に定義した小さな関数になる。置き換えるのは確実なものだけで、行の頭から始まる1文であること、関数やブロックの外にあること、
  名前が文字列で書かれていることが条件である。それ以外は理由とともに一覧に出して、そのまま残す。1つでも残った `.qmd` はヘルパーを読み込んだままに
  なるので、パッケージは実行できる。送る前に一度実行すること。分析が使うパッケージは、読む人が入れることになる。
- **パッケージは英語になる。**`--lang ja` のときだけ、何も訳さず、README も日本語にする。Octavo は翻訳しない。`analysis/` の `.qmd`・`.R`・`.py` の日本語の行を
  `analysis/replication/<名前>.en.json`（スクリプトは `<名前>.R.en.json`）の `prose`（地の文）、`comments`（コメント）、`code`（コードの中）に書き出し、人か AI が埋めた行をパッケージの複製にだけ当てる。
  あとで直した行は未翻訳に戻る。`package.en.json` には README の表題と、日本語の設定の値が入る。**`code` のうち、データと照合する文字列（値による絞り込み、正規表現）は訳を空のままにする。**
  パッケージの設定ファイルからは、日本語のコメントを除く。ほかのファイルに残る日本語（表の見出し、数値の覚え書きなど）は、一覧で知らせるだけで変えない。データ、文献、図の中の文字はそのままにする。
- `--verify` は**パッケージそのもの**を一時フォルダで実行し（手動の分析は除く）、数値を `assets/values` と比べる。分析に要るファイルがパッケージに入っていなければ、ここで分かる。
  `renv` と `.venv` はプロジェクトのものを借りるので、パッケージの版を入れ直せるかどうかは確かめない。`data/raw` がないときだけ失敗する分析は、原データを入れないのは認められているので、その旨を知らせて数値を比べる。
  `--standalone` では、書き換えた `.qmd` も実行する。数値は記録しないので、動くことと、作られなかった図表を確かめる。確かめられたものが1本もなければ（手動の分析だけ、Quarto がない）失敗とし、zip は作らない。
- パッケージの README には、記録した版のパッケージを入れるコマンドと、分析を設定の順に実行するコマンドが入る。手動の分析は別に示す。
- **Octavo が書いたのではないものを、出力で置き換えない。**zip は一時フォルダで作るので、同じ名前のフォルダ（`replication/`、`--out data.zip` のときの `data/`）には触らない。すでにある zip 以外のファイルは断る。
  `--dir` がフォルダを作り直すのは、前回 Octavo が書いたファイル（`build/` に記録する）しか入っていないときだけで、それ以外は何も変えずに止まる。

---

## 9. AI アシスタントのための文章のルール

利用者の書き方のルールと、信頼できる言い回しのフレーズバンクは、パックにまとめた Markdown のファイル。**文章を書く・直す前に `octavo writing --file <ファイル> --line <行> --print` を実行し、出てきたものに従う。** パックの用意の仕方と例は [執筆支援](https://yoshida-kd.github.io/octavo/ja/writing/) に。

### 9.1 パックとファイル

- パックはフォルダー `<パック>/` で、`rules/*.md`・`phrases/*.md` と、任意の `pack.md`（`title`、`extends`、`sections`）を入れる。置き場所は `~/.config/octavo/writing/`（すべてのプロジェクト）か `notes/writing/`（そのプロジェクト。前からの `writing/` も読む）。同じパックの同じ名前のファイルはプロジェクトのものが勝つ。`rules/`・`phrases/` に直接置いたファイルはパック `local` で、いつも最後。
- ファイルの冒頭: `title`、`lang`（`en`/`ja`。なければどの言語でも）、`applies`（`paper`、`slides`、`lecture`、`poster`、`all`。既定 `all`）、`section`（なければいつも読む）。`##` の見出し1つが項目1つで、id は `パック/ファイル#slug`（小文字にし、英数字以外の続きを `-` に。同じ見出しの2つ目は `-2`）。
- ルールは書いたとおりに出る。フレーズでは `When:` / `Note:` / `Source:`（場面 / 注意 / 出典）が JSON の欄になり（`Contains:` も）、箇条書きが型になる（`- Open:` / `- Body:` / `- Close:` は段落の中の位置）。〈 〉は埋める所、`〈A / B〉` は選ぶ言葉。ほかの行はそのまま出るだけで、読み取らない。

### 9.2 原稿が読むもの

- パック: 設定か原稿の冒頭の `writing`（冒頭のものが設定に代わる）に、一般的なものから並べる。後ろが勝つ。`extends` はその前に入る。選ばなければすべてのパック（extends を前に、あとは名前順）。`local` は最後。
- `writing_off`（設定と冒頭の分を**合わせる**）: `パック/ファイル`、`ファイル`、`パック/ファイル#slug`、`ファイル#slug`。
- ファイルを除くのは、`applies` が原稿の種類（出力から決まる）に合わないとき、`lang` が原稿と違うとき、外されたとき、聞かれた節と違う `section` があるとき。`--all` は最後の条件だけを外す。
- 行の節: すぐ上の見出しから浅い見出しへさかのぼり、節に当たる最初の見出しを使う（パックが足した節が先。1つの見出しの中では先に出る言葉）。組み込みの節は `abstract`、`introduction`、`literature`、`theory`、`design`、`results`、`discussion`、`conclusion`、`appendix`（`{.appendix}` の見出しとその後ろ、付録のファイル）。それぞれの言葉は [執筆支援 3.4](https://yoshida-kd.github.io/octavo/ja/writing/#34-行の節の決まり方) の表に。

### 9.3 コマンド

```bash
octavo writing
octavo writing --for my-paper --section results --print
octavo writing --file docs/my-paper/my-paper.md --line 120 --print
octavo writing --for my-paper --kind field/results#the-main-result --print
octavo outline my-paper --paragraphs
```

- `--for DOC` か `--file F` で原稿を言う。`--line N`（`--file` と）で節と段落の印を見つける。`--section S` は節を指定する。`--all` はすべての節。`--kind K`（何度でも、コンマ区切りでも）は段落の種類。`--print` は重ねた本文。`--json`。
- 種類があるとき（`--kind` か、`--line` の行の印から）、ルールは変わらず、フレーズはその項目だけになる。その原稿が使うフレーズのファイル（選んだパックの、`applies`・`lang` が合い、外していないもの）から、節を問わず探す。ほかのファイルの種類は警告して除く。

### 9.4 段落の印と著者への問い

- 段落のすぐ上に `<!-- para: <種類> | <主張> -->`。本文は次の行から。印の次が空行なら、まだ書いていない段落。印の前には空行を置く（ないと pandoc が上の段落とつなぐ）。種類は `writing_off` の id と同じに解決する（`ファイル#slug` は後ろのパックのもの）。
- `octavo outline … --paragraphs` の印: `no-kind`、`unknown-kind`（と `near`）、`unused-kind`（この原稿では使わないファイルの種類）、`no-text`、`joined`、`same-kind`（1つの見出しの下で同じ種類の3つ目。注意だけ）。繰り返し: 1つの見出しの下の2つの文に当たった型（〈 〉の外の言葉がすべて1つの文の中に同じ順で出る。大文字で始まる型は文の頭、`.` で終わる型は文の終わり。決まった言葉が2語に満たない型は探さない。その見出しの節か、`section:` のないファイルの型で、その原稿が使うものだけ）。
- `<!-- ask: … -->`: 一覧に出る。`octavo check` は消すまで「著者への問い」を警告する。コードブロックの中の印は読まない。

### 9.5 JSON

- `octavo writing --json`（原稿を言わないとき）: `rules`、`phrases`（ファイル: `path`、`title`、`lang`、`applies`、`section`、`entries`、`where`、`pack`、`kind`）、`packs`（`name`、`title`、`path`、`where`、`extends`、`sections`、`description`、`files`）、`sections`、`warnings`。
- `octavo writing --for|--file … --json`: `doc`、`packs`、`chosen`、`chosen_here`、`kinds`、`lang`、`section`、`heading`、`sections`、`off`、`off_here`、`paragraph_kinds`（種類がなければ null）、`paragraph`（`line`、`kind`、`claim`、`body_line`、`first_sentence`。`--line` がなければ null）、`warnings`、`text`（`--print` のとき）と `files`: `id`、`pack`、`kind`、`path`、`title`、`lang`、`applies`、`section`、`where`、`used`、`skipped`（`applies`、`lang`、`off`、`section`、`kind` か null）、`items`（`id`、`title`、`slug`、`line`、`off`。フレーズには `when`、`note`、`source`、`lines` = [`position`、`text`]、`contains`、種類を言ったときは `picked` も）。
- `octavo outline … --paragraphs --json`: 原稿のファイルごとの並び: `doc`、`file`、`appendix`、`paragraphs`（`line`、`body_line`、`kind`、`id`、`title`、`claim`、`first_sentence`、`heading`、`heading_line`、`heading_level`、`problems`、`near`）、`repeats`（`heading`、`heading_line`、`id`、`text`、`lines`、`section`）、`asks`（`line`、`text`）。

### 9.6 何も出ないとき

- ルールがまったく出ない: Octavo 0.6.8 以前にはパックがない。またはフォルダーが `~/.config/octavo/writing/<パック>/` か `notes/writing/<パック>/` にない（リンクが1段ずれていると何も出ない）。
- ある原稿にファイルが出ない: `applies` / `lang`（`octavo writing --for DOC --all` で除いたものが見える）。ある節が読まれない: 見出しがどの節にも当たらないか、節の名前の打ち間違い（`octavo check`）。
- 「writing_off に当たる項目がない」: 項目の見出しが変わり、slug が変わった。
- 「印の前に空行が要る」: 印の上に空行を入れる。

---

## 10. テンプレート

```bash
octavo template list                              # テンプレートと、使っているものの出どころ
octavo template copy slides/typst-slides.typ      # このプロジェクトの templates/ へ
octavo template copy paper/en/main.typ --user     # ~/.config/octavo/templates/ へ
octavo template diff slides/typst-slides.typ      # コピーしてから同梱のものが変わった所
```

探す順: プロジェクトの `templates/`、`~/.config/octavo/templates/`、同梱のもの。コピーはファイルを丸ごと置き換える。

| テンプレート | 対象 |
|---|---|
| `slides/typst-slides.typ`、`slides/typst-notes.typ` | スライドと台本 |
| `poster/typst-poster.typ` | ポスター |
| `handout/handout.typ` | A4 のプリント |
| `paper/article.typ`、`paper/<lang>/main.typ` | 論文 |
| `manuscripts/<lang>/*.md` | `octavo new` が書くもの |
| `typst/crossref.typ` | 番号と参照の見た目 |
| `citations/japanese.lua` | 文献一覧の日本語文献 |
| `claude/<lang>/*.md` | AGENTS.md の節 |

書体: 論文は BIZ UD明朝 + Libertinus Serif、プリントとスライドは BIZ UDゴシック + Inter（なければ Noto CJK、ヒラギノ、游）。

---

## 11. コマンド

```
octavo build [documents...] [--to outputs] [--compile] [--appendix] [--sessions] [--no-analysis] [--anonymous] [--json]
octavo watch [documents...] [--to outputs]
octavo extract <lecture> [--session IDS] [--pages 12-19] [--cover]
octavo documents [--json]
octavo outline [documents...] [--paragraphs] [--json]
octavo targets
octavo config [--doc NAME] [set KEY VALUE | unset KEY] [--json]
octavo analysis [--json] | run [QMD...] [--keep-cache] | mark-fresh QMD | prose QMD | missing QMD | install QMD
octavo env
octavo check [--strict] [--anonymous] [--json]
octavo check values [--unused] [--diff [REF]] [--json]
octavo check cites [--list] [--unused] [--json]
octavo check lint [--json]
octavo fmt [name] [--apply]
octavo bib pull|tidy|collections|login
octavo csl get|list|which [ID]
octavo priorwork [resolve|link|cards|ask|requests] [--dry-run] [--json]
octavo writing [--for DOC --section S | --file F --line N] [--kind KIND] [--print] [--json]
octavo bundle [name] [--anonymous] [--replication] [--with-raw-data] [--standalone] [--lang en|ja] [--verify]
octavo review returned.docx [--json]
octavo release <document> <label>
octavo data hash|status|track
octavo init <dir> [--lang ja|en] [--with PARTS | --all] [--engine r|python] [--example] [--env]
octavo new paper|slides|lecture|poster|analysis|figure|table <name> [--lang ja|en] [--example] [--appendix] [--tex] [--engine r|python] [--env] [--json]
octavo template list|copy|diff [name] [--user]
octavo migrate [--docs|--syntax|--rules] [--dry-run] [--allow-dirty]
octavo setup [--with-tex] [--check] [--r-editor]
octavo doctor [--json]
octavo selftest
octavo docs [section] [--search WORD] [--all] [--lang ja|en]
```

前の名前 `octavo values`、`octavo checkbib`、`octavo lint`、`octavo reference-docx` も使える。表示の言語は `OCTAVO_LANG`（`ja` / `en`）、なければシステムの言語。

---

## 12. うまくいかないとき

- **道具が足りない**: `octavo doctor` がそれと入れるコマンドを示す。`octavo setup` がすべてを入れ、更新する。
- **Quarto の Preview で .qmd を実行して「there is no package called …」**: Octavo から実行する（`octavo analysis run <qmd>`）か、`octavo analysis install <qmd>`。
- **チャンクだけを実行して「cannot open file 'octavo.R'」**: その `.qmd` は `source("octavo.R")` で読んでいる。[6.2](#62-r-の補助octavor) の行にする。
- **パッケージは入るのに読み込めない**（「cannot open shared object file」）: システムのライブラリが足りない。`octavo doctor` が apt の行を示す。
- **ラベルが解決しない、図がない**: `octavo check` がどれがどこかを言う。
- **PDF の数値が違う**: 分析を実行し直す（`octavo analysis run`）。手で書かない。
- **スライドがはみ出す**: ビルドがそれを言う。`\newslide` を入れるか、削るか、図を小さくする。
- **引用の形がおかしい**: `octavo selftest` が組んだ形を示す。`.bib` の項目は `octavo check cites` で確かめる。
