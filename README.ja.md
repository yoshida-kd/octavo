# Octavo

**計量社会科学スターターパック**

[![tests](https://github.com/yoshida-kd/octavo/actions/workflows/tests.yml/badge.svg)](https://github.com/yoshida-kd/octavo/actions/workflows/tests.yml)

[English README is here](README.md)

マークダウンで書いた**1つの原稿**を、**Typst（論文・プリント・スライド）/ Word / LaTeX / Beamer**
に出し分けるコマンドラインツール。文献は `.bib` と CSL の仕組みに
一本化してある。日本語と英語のどちらの原稿でも同じように動く。

同じ内容から「投稿先の書式に合わせた論文」「授業用の A4 プリント」
「発表スライド」を、節の本文・図表・参考文献をコピペし直すことなく
まとめて作りたい、という学術系のワークフロー向けに作られている。

```bash
octavo init 2026-research && cd 2026-research
octavo new paper example-paper        # 論文を足す（何本でも）
octavo new lecture example-lecture    # 講義ノートを足す
octavo build                          # 全部を作る
octavo build example-paper --to docx  # Word にする
octavo build example-lecture --to typst-slides --compile  # 回ごとのスライドを PDF まで
```

| 出力 | 使うもの | 出るもの |
|---|---|---|
| `typst` | Typst | `body.typ`（論文。手持ちの `main.typ` に差し込む）または完結した `.typ` |
| `typst-slides` | Typst | 完結したスライドの `.typ`（パッケージを使わない素の Typst） |
| `typst-notes` | Typst | そのスライドの台本。A4 縦で1ページ＝1枚、下に `::: notes` |
| `docx` | pandoc だけ | `.docx` |
| `latex` | LuaLaTeX（任意） | `body.tex`（論文。手持ちの `main.tex` に差し込む）または完結した `.tex` |
| `beamer` | LuaLaTeX（任意） | 完結したスライドの `.tex` |

既定は TeX 無しで出せる `typst` / `typst-slides` / `docx`。LaTeX / Beamer を使うときだけ
TeX Live を足す（`bash setup.sh --with-tex`）。

引用はすべて **CSL に一本化**してある。`octavo.config.py` の `csl` を
1行変えれば、LaTeX でも Typst でも Word でも同じ書式に切り替わる。
形式ごとに引用ロジックを持つ必要はない。

---

## 1. 入れる

動く環境は Linux（Ubuntu/Debian 系のマシン、Ubuntu サーバ、または Windows 上の
WSL2/Ubuntu）と macOS。`setup.sh` は Linux では apt、macOS では
[Homebrew](https://brew.sh) で入れる（Mac では先に Homebrew を入れておく）。

```bash
git clone https://github.com/yoshida-kd/octavo.git ~/octavo
bash ~/octavo/setup.sh     # pandoc / Typst / quarto / 日本語フォント
octavo doctor                    # 足りないものを言う
octavo selftest                  # 実際に1本通して引用の組み方を見る
```

`octavo selftest` は一時ディレクトリに小さな原稿（日本語と英語の文献、団体著者、
表、図、相互参照、`\poscite`）を作って変換し、**出てきた引用と書誌の実物を
印字する**。環境ごとに1度は通しておくと、CSL の書式が思ったとおりか目で
確かめられる。

### 表示の言語

メッセージ・`--help`・`octavo doctor` は、**既定は英語で、ロケール
（`LC_ALL` / `LC_MESSAGES` / `LANG`）が日本語なら日本語**になる。
`OCTAVO_LANG` があればそちらが優先:

```bash
export OCTAVO_LANG=ja    # ロケールが何であれ日本語
export OCTAVO_LANG=en    # 同じく英語
octavo doctor            # 「表示の言語」の行に、いま効いている設定が出る
```

ロケールが `en_US.UTF-8` の機械では既定が英語になるので、日本語で使うなら
shell の設定に `export OCTAVO_LANG=ja` を1行書いておくのが確実。

これは**画面の言語**だけの話。プロジェクトを何語で**書く**かは別の設定で、
`octavo.config.py` の `lang`（`octavo init --lang ja|en` が書く）が、原稿の
ひな型・生成される CLAUDE.md や README・引用の locale を決める。
「画面は日本語、論文は英語」はごく普通の組み合わせ。

### pip で入れる

外部の道具まで入れてくれるので、ふだんは上の `setup.sh` + シンボリックリンクが
よい。変換器だけ欲しくて pandoc / Typst / quarto は自分で入れるなら、`octavo` は
ふつうの Python パッケージとしても入る。

```bash
pipx install octavo-kit    # 仮想環境の中なら pip install octavo-kit でもよい
octavo doctor
```

（最近の Ubuntu / Debian では、仮想環境の外での素の `pip install` は PEP 668 で
断られる。`pipx` はコマンドごとに専用の環境を作って入れるので、それを勧めている。）

**Python の依存パッケージは無く**（標準ライブラリだけ）、テンプレートも同梱
するので `octavo init` / `octavo new` はそのまま動く。入らないのは `setup.sh`
そのもので、`octavo doctor` が「足すなら clone してこれを走らせろ」と案内する。
PyPI での配布名は `octavo-kit`（`octavo` という名前は PyPI が使わせない）で、
コマンドと Python のパッケージ名は `octavo`。

`setup.sh` は何度走らせても平気。既定では TeX Live を入れない。LaTeX や
Beamer も使うなら `bash setup.sh --with-tex`（数 GB ある）。`octavo doctor` は
TeX が無いことを「不足」ではなく「注意」として出す。分析（`.qmd`）を render する
quarto は既定で入る（要らなければ `--no-quarto`）。R や Python の処理系そのものは
入れない（どちらを使うかはプロジェクト次第）。

必要な版:

| | 最低 | 望ましい | 理由 |
|---|---|---|---|
| pandoc | 2.11 | 3.11 | 2.11 で `--citeproc`（CSL 引用）、3.1 で Typst 書き出し。3.11 で動作を確かめてある |
| Python | 3.9 | — | 標準ライブラリだけ使う（外部パッケージ不要） |
| LuaLaTeX（任意） | — | TeX Live 2021+ | `texlive-lang-japanese` が要る |
| Typst | — | 0.15 | Typst スライドは 0.12 以上。日本語フォントは同梱されない（`setup.sh` が入れる） |

macOS では `setup.sh` が `brew install pandoc typst`、`brew install --cask quarto`
と書体（`font-biz-udmincho` など）を入れ、`--with-tex` で MacTeX
（`mactex-no-gui`。日本語の LuaLaTeX と Beamer がすべて入っている）を足す。
`octavo doctor` の案内も Mac では `brew` の書き方になる。CI の `macos`
ジョブが、Homebrew で入れるところから組版まで毎回通している。

Windows から使う場合は WSL2（Ubuntu）上で動かすのが確実。原稿ファイルは
Linux 側のファイルシステム（または `/mnt/...` にマウントした Windows 側の
フォルダ）に置くとパス解決で困らない。

### 分析の環境はプロジェクトごとに（.venv と renv）

pandoc・Typst・quarto・Octavo はマシンに1つ（上の `setup.sh`）。**分析に使う
パッケージはプロジェクトごとに持つ。**`octavo init` は Python 側の足場として
`requirements.txt` を置き、`.gitignore` に `.venv/` と `renv/library/` を入れる。

```bash
cd 2026-research
python3 -m venv .venv && source .venv/bin/activate  # Python
pip install -r requirements.txt
Rscript -e 'renv::init()'                           # R
```

renv は R に付いてこないので、マシンに1度だけ入れておく（`octavo doctor` の
「分析」欄に有無が出る。個人用ライブラリのフォルダが無いと入れられないので、
それも作る）:

```bash
mkdir -p "$(Rscript -e 'cat(Sys.getenv("R_LIBS_USER"))')"
Rscript -e 'install.packages("renv", repos = "https://cloud.r-project.org")'
```

git に入るのは**記録だけ**（`requirements.txt` / `renv.lock`）で、環境の中身は
入らない。パッケージを入れたら `pip install` のあとに `requirements.txt` へ、
`install.packages()` のあとに `renv::snapshot()` へ。生成されるプロジェクトの
`README.md` / `CLAUDE.md` にも同じ約束が書いてある。

### 書体

Typst で組むものはすべて同じ既定を使う（`octavo/backends/typst.py::FONTS`
の1か所にある）:

| | 和文 | 英字・数字 | 無いとき |
|---|---|---|---|
| 論文・A4 プリント | BIZ UD明朝 | Libertinus Serif | Noto Serif CJK JP → ヒラギノ明朝 ProN |
| スライド・台本 | BIZ UDゴシック | Inter | Noto Sans CJK JP → ヒラギノ角ゴ ProN |

BIZ UD は**等幅**のほう（プロポーショナルの BIZ UDP は使わない）。日本語の
文書では欧文フォントは英字と数字だけを受け持ち（`covers: "latin-in-cjk"`）、
「」、。などの約物は和文フォントのまま。英語の文書では欧文フォントを先頭に
置くだけ。`setup.sh` がすべて入れる（`fonts-morisawa-bizud-gothic`・
`fonts-morisawa-bizud-mincho`・`fonts-inter`・`fonts-noto-cjk`。Mac では同じものを
Homebrew の cask で）。BIZ UD や Inter が無い機械でも Noto に落ちて組め、Mac で
何も足していなければ、最初から入っているヒラギノで組む。何が足りないかは `octavo doctor`
に出る。変えるなら `typst_mainfont`（A4 プリント）と `typst_slides_font`
（スライド・台本）、論文は `main.typ`。Google Fonts の「Noto Serif JP」は
`Noto Serif CJK JP` と名前が違うので見つからない。

---

## 2. 文書とプロファイル

Octavo は「**どの原稿を、どの用途で、どの形式に出すか**」を
`octavo.config.py` の `documents` で持つ。

`octavo init` が書く設定は、原稿の種類ごとのフォルダを**グロブで丸ごと**登録する。
だから `octavo new` で原稿を何本足しても設定は書き換えなくてよい。

```python
'documents': {
    'papers': {'src': 'papers/*/paper.md', 'appendix': 'papers/*/appendix.md',
               'profile': 'paper', 'targets': ['typst']},
    'slides': {'src': 'slides/*.md', 'profile': 'slides',
               'targets': ['typst-slides']},
    'lectures': {'src': 'lectures/*.md', 'profile': 'handout',
                 'targets': ['typst', 'typst-slides'], 'split_slides': True},
},
  # papers/example-paper/paper.md -> 文書 example-paper（付録は同じフォルダの appendix.md）
  # slides/example-talk.md          -> 文書 example-talk
  # lectures/example-lecture.md       -> 文書 example-lecture（スライドは example-lecture-01, -02, …）
```

- `src` にグロブを書くと、当たった原稿が**それぞれ1つの文書**になる。文書名は
  **最初の `*` に当たった部分**（論文ならフォルダ名、スライドならファイル名）。
  キーに `*` を入れれば、そこに差し込む（`'講義*': {'src': 'lectures/*.md'}` なら
  `講義lecture01`）
- `appendix` にも `*` が書ける。`src` と同じ部分で埋め、ファイルがあるときだけ結ぶ
- 同じ名前の文書が2つできたら止まる（種類が違っても `octavo build <name>` で
  区別できないため）
- グロブに何も当たらないのは「その種類の原稿がまだ無い」だけなので黙っている
- 1本ずつ書いてもよい: `'第3回': {'src': 'lecture03.md', 'profile': 'handout'}`

`documents` を書かなければ、置いてあるファイルから自動で決まる:

| ファイル | 文書名 | profile | 既定の出力 |
|---|---|---|---|
| `draft.md` | `paper` | `paper` | `typst` |
| `slides.md` | `slides` | `slides` | `typst-slides` |
| `handout.md` | `handout` | `handout` | `typst` |

**profile** は用途。目次・節番号・要旨の扱いと、`main.tex` を使うかどうかが変わる。

| profile | 目次 | 節番号 | 要旨 | LaTeX/Typst の出方 |
|---|---|---|---|---|
| `paper` | 無 | 無（組版側が振る） | 別ファイルに切り出す | `body.typ` + 手持ちの `main.typ`（LaTeX なら `body.tex` + `main.tex`） |
| `handout` | 有 | 有 | 本文のまま | 完結した1枚の `.typ` / `.tex` |
| `slides` | 無 | 無 | 本文のまま | 完結した1枚の `.typ`（Beamer なら `.tex`） |

`paper` だけ `main.typ` / `main.tex` を手で持つ方式なのは、投稿先ごとに版面をいじる必要が
あるから。授業資料と発表スライドは1ファイルで完結させたほうが速い。

出力先は形式ごとのフォルダ（`build/typst/` など）。完結した文書は `<文書名>.typ` の
ように並ぶが、`paper` の `main.*` 方式は `main.typ` / `body.typ` の名前が決まっていて
論文が2本あるとぶつかるので、**論文ごとに `build/typst/<文書名>/`** に分ける。

### `octavo init` と `octavo new`

`octavo init` は**原稿の種類を問わない共通部分**を作る。論文・スライド・講義ノートの
違いは原稿のテンプレートだけなので、プロジェクトの形は1つしかない。原稿は後から
`octavo new` で、どの種類でも何本でも足す。

```
2026-research/
  CLAUDE.md          Claude Code 向けの約束事（数値は手で書かない、等）
  README.md          人向けの手順書
  octavo.config.py   設定（原稿の種類ごとのグロブ、分析の登録）
  literature.bib     書誌（文献管理ソフトから書き出したもの）
  requirements.txt   分析に使う Python パッケージの記録（.venv に入れる）
  data/raw/          原データ。読み取り専用。git には入らない
    README.md        出所・取得日・利用条件を書く場所（これだけが記録に残る）
  data/derived/      整形後のデータ。.qmd が作る。git には入らない
  analysis/
    analysis.qmd     分析の例（推定 → ov_value / ov_figure / ov_table）
    octavo.R         分析側のヘルパー（ov_value / ov_figure / ov_table）
  results/
    analysis.json    分析を走らせる前でも {{…}} が埋まるための仮の値
  figures/  tables/  仮の図（枠と × だけ）つき
  refs/              外から来た資料（コードブック・投稿規定）。git に入れる
  notes/             自分が書いたメモ（読書・査読）。原稿には入らない
```

`octavo init` / `octavo new` が置くものは**すべて例**で、そうと分かる印が入って
いる。原稿・`analysis.qmd`・`literature.bib` には `octavo:example` のコメント、
`results/analysis.json` には `_placeholder`、仮の図は枠と × だけの絵。
自分の中身に置き換えたら印ごと消す。残りは `octavo check` が数える。
**仮の値のまま組むのは「致命的」**として止まる（分析を1度も走らせていなくても
`{{…}}` は全部解決してしまうので、嘘の数字が入った PDF が黙って作れてしまう）。

```bash
octavo new paper example-paper     # papers/example-paper/ に paper.md・appendix.md と、
                                 #   体裁の main.typ / main.tex
octavo new slides example-talk       # slides/example-talk.md
octavo new lecture example-lecture  # lectures/example-lecture.md
```

どの原稿のテンプレートも `{{…}}` と仮の図を使う例になっていて、足した直後から
`octavo build --compile` が最後まで通る。`octavo new` は `octavo.config.py` を
書き換えず、足したあとで設定を読み直して**本当に登録されたか**を確かめる。
名前が既存の文書とぶつかるとき（種類が違っても）は何も書かずに止まる。

`.gitignore` は `data/raw/` と `data/derived/` を除外する（大きいデータや
再配布できないデータを事故で commit しないため）。代わりに
`data/raw/README.md` だけは追跡され、そこにデータの出所を書く決まりにしてある。
`build/` は丸ごと除外する。**手で書く体裁（`main.typ` / `main.tex`）は原稿と同じ
`papers/<name>/` にあり**、組版のたびに `build/` へ写されるので、`build/` を消しても
体裁は消えない。

### 講義ノート: 1本から A4 プリントと回ごとのスライド

```bash
octavo new lecture example-lecture
octavo build example-lecture --to typst --compile         # A4 プリント（全回を1冊）を PDF まで
octavo build example-lecture --to typst-slides --compile  # スライドを回ごとに PDF まで
octavo build example-lecture-03 --to typst-slides         # 3回目だけ
```

講義ノートは `split_slides: True` の文書で、**`#` 見出しが1回分**。プリントは1本の
まま組み、スライドは `#` ごとに別々の文書（`example-lecture-01`, `-02`, …）として組む。

- 回のスライドでは、その回の `#` 見出しが題扉の題、講義ノートの `title` が副題になり、
  `##` が1枚ずつのスライドになる
- 名前の番号は `#` の出てきた順。**途中に回を挿し込むと後ろがずれる**ので、名前を
  固定したい回は見出しに id を付ける: `# 第2回 {#second}` → `example-lecture-second`
- 最初の `#` より前（ノート全体の前置き）はプリントにだけ入る
- コードブロックの中の `#` では分けない。`# 参考文献` 以降は落とす

出し分けたいところは**条件付きブロック**で書く。

```markdown
::: {.handout-only}
Fill-in-the-blank space and detailed footnotes: handout only.

(                                    )
:::

::: {.slides-only}
Figures and short prompts: slides only.
:::

::: notes
Speaker notes (in the speaker script and in Beamer; never on the projected deck)
:::
```

| 印 | 残る形式 |
|---|---|
| `.slides-only` / `.only-slides` | `typst-slides`, `typst-notes`, `beamer` |
| `.handout-only` / `.paper-only` | `latex`, `typst`, `docx`（その profile のとき） |
| `.print-only` | `latex`, `typst`, `docx` |
| `.no-slides` / `.not-slides` | 否定。その形式のときだけ落とす |
| `.notes` / `::: notes` | `beamer`、`typst-notes`（投影するスライドからは落ちる） |

印の無い div（`::: {.warning}` など）はそのまま通る。

---

## 3. 原稿の書き方

| 要素 | 書き方 | 備考 |
|---|---|---|
| 見出し | `## 1. 節題` / `### 1.1 小節` / `# 2. …` | 番号は `{#sec:1}` ラベルになり、組版側が振り直す |
| 付録 | `## 付録A．…` / `## Appendix A. …` | `{#sec:appA}` |
| 要旨 | `## Abstract` / `## 要旨` / `## 概要` | `*Word count: N words*` 行があれば一緒に切り離す |
| 参考文献節 | `## References` / `## 参考文献` | 変換時に落とす（書誌は `.bib` から組む） |
| 引用 | `@key`（地の文）、`[@key; @key2]`（括弧） | |
| 所有格引用 | `\poscite{key}` | "Smith and Taylor's (2003)" / 「山田・田中(2020)」 |
| 分析の数値 | `{{n_obs}}` / `{{coef:.2f}}` | `.qmd` が `results/*.json` に出した値が入る（§4） |
| 表 | `**表1．キャプション**` + マークダウン表 | `table_map` に対応があれば外部 `.tex`/`.typ` に差し替え |
| 図 | `![](figures/fig1_x.png)` + `**図1．** 説明` | 拡張子は形式ごとに付け替える（LaTeX は `.pdf`） |
| 相互参照 | 「表3」「図1」「第4.1節」「Table 3」「Section 4.1」 | LaTeX/Typst では自動でリンクになる |
| 題扉 | 先頭の YAML front matter | `title` / `author` / `institute` / `date` |

日本語と英語の語彙はどちらも既定で拾う（`crossref_vocab: 'both'`）。
相互参照は**原稿の言い回しを保つ**ので、「第2節」は `第\ref{sec:2}節`、
"Section 2" は `Section~\ref{sec:2}` になる。Typst では `#ref(<sec:2>)` の形で
出す（`@sec:2` と書くと、続く日本語までラベル名として飲み込まれる）。

### 図の拡張子

原稿には `.png` を1つ貼れば足りる。出力ごとに次を探す。

| 形式 | 探すファイル |
|---|---|
| `latex` / `beamer` | `figures/fig1_x.pdf` |
| `typst` / `typst-slides` / `typst-notes` / `docx` | `figures/fig1_x.png` |

`figure_ext` で変えられる。足りないファイルは変換時に「欠落」として出る。

### 表を外部ファイルにする（分析スクリプト連携）

R や Python が表を `.tex` / `.typ` で直接吐く運用なら、`table_map` に
「本文の表番号 → `tables/` のファイル名」を書く。

```python
'table_map': {'1': 'tbl1_summary', '2': 'tbl2_models'},
```

LaTeX なら `\inputtable{../../tables/tbl1_summary}`、Typst なら
`#include "../../tables/tbl1_summary.typ"` に差し替わり、相互参照は
**ファイルが実際に張っている `\label` を読んで**繋ぐ（推測しない）。

Word・スライドは外部 `.tex` を取り込めないので、その場合は
`table_map` があってもマークダウンの表がそのまま使われる。

---

## 4. 分析（Quarto）と原稿の分業

**原稿は `.md`、分析は `.qmd`。**論文に出る数値・図・表は原稿に手で書かず、
分析側が決まった場所に書き出したものを、変換のたびに差し込む。
数値の出所が1つになるので、推定をやり直したときに本文だけ古い、という
食い違いが起きない。

```
analysis/*.qmd  --quarto render-->  results/*.json   本文の {{…}}
                                    figures/*.pdf|png  図
                                    tables/*.tex|typ   表

manuscripts + the three above  --octavo build-->  Typst / Word / LaTeX / Beamer
```

### 4.1 受け渡しの3つの口

`octavo init` は `analysis/` に `octavo.R`（ヘルパー）と `analysis.qmd`（例）を
置く。`.qmd` の最初のチャンクで読み込む。

```r
root <- Sys.getenv("OCTAVO_ROOT", unset = "")
source(if (nzchar(root)) file.path(root, "analysis", "octavo.R") else "octavo.R")
```

| 渡すもの | 分析側（.qmd） | 原稿側（.md） |
|---|---|---|
| 数値 | `ov_value("n_obs", nrow(d))` | `{{n_obs}}` |
| 図 | `ov_figure(p, "fig1_trend")` | `![](figures/fig1_trend.png)` + `**図1．** 説明` |
| 表 | `ov_table(tab, "tbl1_summary")` | `**表1．…**` ＋ config の `table_map: {'1': 'tbl1_summary'}` |

- `ov_value(name, x, fmt = NULL, note = NULL)` — 値を1つ登録する。
  `results/<この .qmd の名前>.json` に貯まる。`ov_values(a = 1, b = 2)` でまとめ書きも可。
- `ov_figure(x, name, width, height, dpi)` — `figures/` に **`.pdf` と `.png` の両方**を
  書く。LaTeX は `.pdf`、Word と Typst は `.png` を使う既定にそのまま乗る。
  `x` は ggplot でも、base graphics を描く関数でもよい。
- `ov_table(x, name, caption, notes, align)` — `tables/` に **`.tex` と `.typ` の
  両方**を書く。`x` は data.frame か、出来合いの文字列を入れた
  `list(tex = …, typ = …)`。LaTeX には `\label{tab:<name>}`、Typst には
  `<name>` のラベルが入るので、本文の「表1」がそのまま参照として繋がる。
- `ov_pval(p)` — p 値を慣例どおり（`0.023` → `.023`、`< .001`）文字にする。

### 4.2 数値の書式

`{{名前}}` の見え方は値の型で決まる。

| 値 | R での例 | 出力 |
|---|---|---|
| 整数 | `nrow(d)`（integer） | `1,523`（桁区切り） |
| 小数 | `coef(m)[["x"]]`（double） | `0.342`（`value_float_format`、既定 `.3f`） |
| 文字 | `ov_pval(p)` | そのまま |

桁を変えたいときは本文側で `{{coef_x:.2f}}`、あるいは分析側で
`ov_value("coef_x", x, fmt = ".2f")` と書く。本文側の指定が優先。
書式は Python の書式指定（`.2f` / `,` / `.1%` など）がそのまま使える。

**値が見つからないときは `{{名前}}` をそのまま残して警告する。**黙って消すと
本文が静かに壊れるため。`octavo values` で突き合わせを一覧できる。

### 4.3 いつ走るか

`octavo build` は変換の前に `.qmd` の更新時刻を見て、**前に走らせたときより
新しければ** `quarto render` を走らせる。記録は `results/.analysis-stamp.json`。

```python
'analysis': ['analysis/*.qmd'],
  # データの更新も見張るなら
'analysis': [{'src': 'analysis/main.qmd', 'deps': ['data/*.csv']}],
'analysis_deps': [],       # 全部の .qmd に共通の依存
'analysis_to': None,       # quarto render --to（None なら .qmd の指定に従う）
'analysis_args': [],       # quarto に渡す追加の引数
'analysis_auto': True,     # False にすると octavo analysis run のときだけ走る
'results_dir': 'results',
'value_float_format': '.3f',
'value_thousands_sep': True,
```

- `octavo build --no-analysis` — 走らせない（いまの `results/` のまま変換する）
- `octavo build --force-analysis` — 古くなくても走らせ直す
- `octavo analysis` — どれが古いか、値がいくつあるかを見る
- `octavo analysis run [--force]` — 古いものを走らせる（手動のものも含む）
- `octavo analysis run analysis/01-clean.qmd` — その1本だけを走らせる（古くなくても）
- `octavo values [--unused] [--json]` — 本文の `{{…}}` と `results/` の突き合わせ
- `octavo values --diff` — **前に分析を走らせたときから、本文の数字がどう動いたか**

**時間のかかる `.qmd` は `'manual': True` にする**（次の節）。`octavo build` は
それを走らせず、古ければ知らせるだけにする。走らせるのは `octavo analysis run`。

**VS Code では、ここまでをすべてボタンで操作できる。**サイドバーの「分析」に
`.qmd` ごとの状態（最新・古い・手動）と走らせるボタンが並び、`.qmd` を開いて
いればエディタ右上のボタンでその1本を走らせられる。**プレビューは分析を走らせ
ない**。古い分析があれば PDF の上に帯が出るので、そこのボタンで走らせると、
終わったあとにプレビューが組み直される。進み具合は右下の通知に、quarto の出力は
「出力」パネルの Octavo に出る。

**quarto が入っていなければ警告して素通りする**（変換自体は pandoc だけでできる）。
入っているのに `render` が失敗したときは、古い数値のまま論文を組まないよう
**変換を止める**。止めたくないときは `--no-analysis`。

`octavo analysis run` は走らせる**直前**の値を控えに取る。だから再推定のあとで

```
$ octavo values --diff
Compared with 2026-09-07 10:12:33

Changed (2):
  n_obs                             1,523  ->  1,608
  coef_x                          0.342  ->  0.311
```

のように、**論文のどの数字が動いたか**が分かる。比べるのは本文に出る文字なので、
`0.3419` が `0.3421` になっても（`.3f` なら本文は `0.342` のまま）差分には出ない。
数字が動いたら、それを説明している言い回し（「わずかに」「約」）も直すこと。

### 4.4 分析を複数に分ける・付録を足す

**分析は最初から複数ファイルを想定している。**`analysis` はグロブなので、
`.qmd` を足せばそれだけで登録される。

```python
'analysis': ['analysis/*.qmd'],
```

1本の `.qmd` は `results/<その .qmd の名前>.json` を持つ。ファイルが分かれて
いても本文からは区別なく `{{名前}}` で呼べる（`octavo` が全部の `*.json` を
読んで1つにまとめる）。**同じ名前を2つの `.qmd` が書いたときは警告を出して
後を採る**ので、`octavo values` の `source` 欄で出所を確かめること。

**前段の `.qmd` が後段の入力を作る**ときは、**書いた順に走る**ことと、
後段の `deps` に前段の出力を入れることの2つを守る。

```python
'analysis': [
    {'src': 'analysis/01-clean.qmd', 'manual': True},       # data/derived/ を作る（重い）
    {'src': 'analysis/02-model.qmd', 'deps': ['data/derived/*']},
    {'src': 'analysis/03-robustness.qmd', 'deps': ['data/derived/*']},
],
```

**データの整形のように時間がかかり、しかも滅多に変わらないものは別の `.qmd` に
分けて `'manual': True` を付ける。**`octavo build` もプレビューもそれを走らせず、
古くなったら「手動の分析が古い」と知らせるだけ。走らせるのは
`octavo analysis run`（古いもの全部）か `octavo analysis run analysis/01-clean.qmd`、
VS Code ならサイドバーのボタン。整形が走って `data/derived/` が変われば、
後段（`02-model` など）は `deps` を見て古くなり、次に組むときに走る。

グロブ1本（`analysis/*.qmd`）で済ませるなら、ファイル名を `01-` `02-` で
始めておけば名前順に走る。どちらの書き方でも、`01-clean` が
`data/derived/` を書き換えたら、**同じ 1 回の `octavo build` の中で**
`02-model` も走り直す（判定は1本ずつ、その時点でやり直している）。

`.qmd` を消したり名前を変えたりすると、前に書いた `results/<古い名前>.json`
が残る。本文がまだその名前を参照していると**古い数値が黙って入り続ける**ので、
`octavo analysis` と `octavo values` が「対応する `.qmd` が無い値のファイル」
として知らせる。

#### 付録

付録は論文のフォルダの `appendix.md` に書く（`octavo new paper` が置く）。
`documents` の `'appendix': 'papers/*/appendix.md'` が、同じフォルダの論文と結ぶ。

```python
  # 付録の表を外部ファイルにするなら、本文とは別の対応表を使う
'appendix_table_map': {'A1': 'tblA1_robustness'},
```

```bash
octavo build example-paper --to typst --appendix  # body.typ と appendix.typ の両方を作る
```

`papers/example-paper/main.typ` 側の `#include "appendix.typ"`（LaTeX なら `main.tex` の
`\appendix` と `\input{appendix}`）のコメントを外す。

付録も本文と**同じ扱い**を受ける。`{{…}}` の差し込み、引用の解決、
条件付きブロック、相互参照はそのまま働き、`octavo values` `octavo checkbib`
`octavo outline` も付録を見る（表示では `example-paper (付録)` と出る）。
番号は本文と分けて `付録A．` `図A1` `表A1`、ファイル名は
`figA1_balance` / `tblA1_robustness` にする。

### 4.5 R 以外で書く

同梱のヘルパーは R 向けだが、`octavo` 側が見ているのは**置き場所と形だけ**なので、
Python でも Julia でも規約に合わせれば動く。

- `results/<何か>.json` に `{"名前": 値}` を書く。整数と小数は JSON 上で
  区別される（`1523` と `1523.0` で既定の書式が変わる）。`{"名前":
  {"value": …, "fmt": ".2f", "note": "…"}}` の形も読む。`_` で始まるキーは無視する
- 図は `figures/<name>.pdf` と `.png`、表は `tables/<name>.tex` と `.typ`

---

## 5. 文献（.bib → 雑誌の書式）

### 用意する

文献管理ソフト（Zotero など）から BibTeX / BibLaTeX で書き出した `.bib` を、
`bib_file` の場所（既定は `literature.bib`）に置く。Zotero なら Better BibTeX の
自動書き出し（Keep updated）を使うと、書誌を直すたびに `.bib` も追随し、
引用キーも途中で変わらない。

### 検査する

```bash
octavo checkbib           # 引用キーと .bib の突き合わせ
octavo checkbib --list    # 引いている文献の一覧
octavo checkbib --unused  # .bib にあって引いていないもの
```

見るもの:

- 引いているのに `.bib` に無いキー（**組版で ?? になる**）。打ち間違いなら
  近いキーを候補として出す
- 年がない / 著者がない / 掲載誌名がない / ページも DOI もない
- 団体名が姓名に割れている（`Organization, Example` のような文献管理ソフトの入力事故）
- 日本語を含むのに `langid` が無い
- 同じ文献の二重取り込み

**Octavo は `.bib` を書き換えない。**直すのは文献管理ソフトの側。承知のうえで
直さないものは `bib_accepted` に理由と一緒に書けば黙る。

```python
'bib_accepted': {('yamada2020', 'no page range or DOI'): 'bulletin uses a running number instead'},
```

`octavo bib clean` は `file` / `abstract` / `keywords` を落とした軽い写しを
**別名で**書き出す（元のファイルは触らない）。

### 雑誌に合わせる

```bash
octavo csl list                                         # 手元にあるもの
octavo csl get modern-language-association   # 取ってくる
octavo csl which                                        # いま使われるもの
```

`octavo.config.py` の1行を変えるだけで全形式に効く。

```python
'csl': 'apa',  # 別名。chicago / ieee / mla / nature / …
```

スタイル ID は <https://www.zotero.org/styles> で探す。従属スタイル
（親を指すだけのもの）を指定した場合は自動で親まで辿る。取ったものは
`octavo/csl/` にキャッシュされ、以後はオフラインでも使える。

`chicago-author-date` は pandoc の内蔵既定なので、`.csl` が無くても動く。

### `\poscite` の仕組み

CSL には「著者の所有格」という形が無い。そこで Octavo は `.bib` から
著者の姓を読んで自分で組み立て、**年と括弧とリンクだけを citeproc に出させる**。

```
\poscite{smith2003}   →   Smith and Taylor's [-@smith2003]
                      →   Smith and Taylor's (2003)
\poscite{yamada2020}  →   山田・田中[-@yamada2020]
                      →   山田・田中(2020)
```

姓の連結（`and` / `et al.` / 「・」「ほか」）は CSL の細部までは真似ていない
近似。厳密に合わせたい雑誌では出力を確認すること。

---

## 6. コマンド

```
octavo build [documents...] [--to formats] [--appendix] [--compile] [--no-citations]
                                              [--no-analysis] [--force-analysis] [--json]
octavo watch [documents...] [--to formats]     原稿・.qmd を保存するたびに作り直す
octavo documents [--json]                      登録されている原稿の一覧
octavo config [set KEY VALUE | unset KEY] [--json]  よく使う設定を見る・変える
octavo analysis [status|run] [--force]         分析 (.qmd) の状態を見る／走らせる
octavo values [--unused] [--diff [ref]] [--json]  本文の {{…}} と results/
octavo lint [--json]                           原稿に直書きされた数値を探す
octavo check [--strict] [--anonymous]          投稿前にまとめて検査する
octavo bundle [--anonymous] [--replication] [--with-raw-data]
octavo review returned.docx [--comments|--insertions] [--json]
octavo data [status|hash]                      データの指紋（sha256）
octavo checkbib [--list] [--unused]
octavo bib clean                           .bib から組版に要らない項目を落とした軽量版を作る
octavo csl get|list|which [ID]
octavo doctor
octavo init <dir> [--lang ja|en]
octavo new paper|slides|lecture <name>        原稿を足す
octavo template list|copy|diff [name] [--user]  自分用のひな型（§7）
octavo release <document> <label> [--dry-run]   この版にタグ、PDF を GitHub Release へ
octavo selftest [--to formats] [--csl ID] [--keep]   引用の組み方を実物で確かめる
octavo reference-docx [out.docx]        Word の雛形を作る
octavo outline [documents...]           見出し構成を見る
octavo targets                          出せる形式の一覧
```

`--to` は `typst,docx` のようにコンマ区切り。`all` / `print`（typst+docx）も
使える。`--compile` は完結した文書なら `typst compile` / `latexmk` を回し、
`paper` profile の Typst なら `main.typ` を組む（付録があれば付録を書き出して
から）。`paper` profile の LaTeX は投稿先ごとに回し方が違うので、`main.tex` 側で
`latexmk` を回す。

`--no-citations` は引用を解決せずに変換する。書きながら見た目だけ確かめたい
ときに速い。`--no-analysis` は `.qmd` を走らせず、いまの `results/` のまま
変換する（重い推定を待ちたくないとき）。`--anonymous` は匿名審査用に組む
（下記）。

### 投稿前に検査する

`octavo check` は、散らばっている検査を1回にまとめる。**致命的**（そのまま
組むと壊れる・間違う）と**注意**（人が判断する）を分け、既定では致命的が
あるときだけ非 0 で終わる。

```
$ octavo check
[  ok  ] sources          papers/example-paper/paper.md, papers/example-paper/appendix.md, slides/example-talk.md
[ warn ] analysis         1 of 2 stale
           analysis/02-model.qmd
           -> octavo analysis run
[fatal ] figure files     1 missing
           figures/fig2_effect.pdf
           -> octavo analysis run, or drop it into figures/
```

見るもの: 原稿の実在 / 分析の鮮度 / 孤児になった値のファイル / 本文の `{{…}}`
の未解決 / **仮の値のまま組もうとしていないか** / 引用キー / 書誌の傷 /
**図と表のファイルが実在するか** / 仮の図 / **ひな型の残り** / 直書きの数値 /
分量 / データの指紋 / 分析環境の記録。CI に置くなら `--strict`（注意も失敗にする）。

このうち**仮の値だけが「致命的」**なのは、分析を1度も走らせていないプロジェクト
でも `{{…}}` が全部解決してしまい、嘘の数字の入った PDF が黙って組めるため。
`octavo build` も組むたびに `[値][注意]` を出す。

`octavo lint` は「ひな型の残り」と「直書きの数値」を詳しく出す。

```
$ octavo lint
3 things that look like results typed into the manuscript

  example-paper
      51: N = 1,523   [sample size]
          The coefficient was 0.342 (SE 0.081) with N = 1,523.
```

「数値を原稿に手で書かない」という約束を機械で見張るためのもの。表・見出し・
コードブロック・DOI・リンク・`{{…}}` の書式指定は見ない。慣例的な定数
（`0.05`、`1.96` など）は既定で見逃し、それ以外で結果でないものは
`octavo.config.py` の `lint_accepted` に書く。

### 投稿規定の分量

`octavo.config.py` に上限を書くと、`octavo check` が突き合わせる。書かなければ
見ない。超えていれば**致命的**（そのままでは投稿できないため）。

```python
'word_limit': 8000,           # 本文の語数
'char_limit': 20000,          # 本文の文字数（日本語の雑誌）
'abstract_word_limit': 150,
'abstract_char_limit': 400,
```

数えるのは `{{…}}` を差し込んだあとの本文で、要旨・参考文献・題扉は本文から
外す（`octavo build` が毎回出す `[分量]` と同じ数え方）。付録は数えない。

### 匿名審査（blind review）

著者が分かる箇所を伏せた版を作る。**新しい書き方は要らない** — 既にある
条件付きブロックに `anonymous` という印が増えるだけ。

```markdown
::: {.no-anonymous}
Acknowledgements: this research was funded by ...
:::

::: {.anonymous-only}
[Acknowledgements withheld for review]
:::
```

```bash
octavo build example-paper --anonymous
octavo bundle example-paper --anonymous  # 漏れが無いか見てから固める
octavo check --anonymous               # 自己引用の候補も出す
```

`--anonymous` は3つのことをする。

1. `.no-anonymous` を落とし、`.anonymous-only` を出す
2. 題扉のメタデータから `anonymous_drop_meta`（既定は著者・所属・謝辞・
   メール）を落とす
3. `build/typst/<論文>/flags.typ`（LaTeX は `build/latex/<論文>/flags.tex`）に切り替えを書く。
   **毎回書き換える**ので、匿名で組んだあと普通に組み直せば必ず戻る

**題扉は `main.typ` / `main.tex` が持っていて Octavo は書き換えない。**同梱の
体裁（`templates/paper/{ja,en}/main.{tex,typ}`）は `\ifanonymous`（Typst は
`#if anonymous`）で著者行を囲んであるので、そのまま使えば切り替わる。

`octavo bundle --anonymous` は固めたあとに**著者名が残っていないか**を見る。

- 条件分岐で囲っていない場所に名前があれば**失敗**（消し忘れ）
- 囲ってあれば組版には出ないが、`.tex` の中には文字として残る旨を伝える
  （ソースごと出す雑誌向け）
- `octavo build --anonymous` を通していなければ固めさせない

自己引用（`.bib` の著者に自分が入っている引用）は `octavo check --anonymous`
が候補として挙げる。伏せるかどうかは雑誌の規定によるので、**挙げるだけ**。

### 投稿用に固め直す

雑誌の投稿システムはたいてい階層を持てない。`octavo bundle` は
`image("../../figures/fig1.png")` を `image("fig1.png")` に（LaTeX なら
`\includegraphics{../../figures/fig1.pdf}` を `{fig1.pdf}` に）書き換え、
参照しているファイルを1つに集めて zip にする。既定は Typst で、LaTeX で
投稿するなら `--to latex` を付ける。固めるのは**論文1本**なので名前を渡す
（リポジトリに論文が1本しか無ければ省略できる）。

```bash
octavo build example-paper
octavo bundle example-paper                     # submission-example-paper.zip
octavo bundle example-paper --dir --out example-talk  # zip にせずフォルダで
```

`main.tex` の `\newcommand` やコメント行、`main.typ` の `//` コメント行は参照として拾わない。
`\IfFileExists{abstract.tex}` のように守られた `\input` は、無くても
欠落として数えない。**`build/` 自体は触らない**（複製に対して行う）。

### 共著者の Word 修正を見る

共著者は Word で赤入れして返してくる。`octavo review` はそれを一覧にする。

```bash
octavo review 20260907_draft_tanaka.docx
octavo review returned.docx --comments     # コメントだけ
```

```
20260907_draft_tanaka.docx: 3 changes in 2 paragraphs
  Hanako Tanaka: 3

  paragraph 1: The sample had 1,523 cases and the coefficient was 0.342 (statistically sign
    [inserted] Hanako Tanaka  2026-09-05 10:11
       (statistically significant)

  paragraph 2: We then turn to the robustness checks.
    [deleted] Hanako Tanaka  2026-09-05 10:14
       in detail
    [comment] Hanako Tanaka  2026-09-05 10:20
      Cite the new replication here?
```

**往復変換はしない。**戻ってきた `.docx` の中では `{{n_obs}}` が既に
「1,523」という文字になっている。docx → md で書き戻すと、このツールの中心
（数値の出所を1つに保つ）がその瞬間に壊れる。だから**変更履歴とコメントだけ
を取り出して見せ、反映は人が `paper.md` 側で行う**。それが唯一安全な戻し方で、
この設計はその判断の結果。

読み方は `.docx`（zip）の中身を直接見るので、pandoc も追加の依存も要らない。

### 渡した版を残す（`octavo release`）

`build/` は git に入れない。中身はすべて git にあるものから作り直せるから。
ただ、**実際に渡した PDF そのもの**は、Octavo・pandoc・Typst・フォントの版が
変わると同じには作り直せない。そこで節目（共著者に回す、投稿する、発表する）
にだけ、その PDF を手元の外に置く:

```bash
octavo release example-paper v1-submitted
```

今のコミットにタグ `example-paper-v1-submitted` を打って push し、GitHub Release を
作って、その場で組んだ PDF（文書が Word も作るなら Word も）を
`example-paper-v1-submitted.pdf` として添付する。Release の本文には、コミットと
Octavo・pandoc・Typst の版を書き残す。ファイルは GitHub に置かれ、git の履歴には
入らないので、リポジトリは膨らまない。

コミットしていない変更がある（タグが組んだものを指さなくなる）、分析が古い・
仮の値のまま、タグがもうある、のどれかなら出さない（理由はまとめて全部出す）。
組むのはその場で、分析は走らせない（走らせるとコミットの後で `results/` が
変わる）。`--dry-run` は確認と組版だけ、`--anonymous` は匿名版を出す。
[GitHub CLI](https://cli.github.com/)（`gh auth login` 済み）と、`origin` という
名前の GitHub のリモートが要る。

### 改訂で何が変わったかを示す（R&R）

`octavo values --diff` に **git のタグやコミット**を渡すと、その版と比べる。
`octavo release` が打ったタグもそのまま使える。

```bash
octavo release example-paper v1-submitted   # 投稿したところで（git tag だけでもよい）
# …（査読・改訂）…
octavo values --diff example-paper-v1-submitted
```

```
Compared with git example-paper-v1-submitted

Changed (2):
  n_obs                             1,523  ->  1,608
  coef_x                          0.342  ->  0.311
```

版を刻む仕組みは新しく作っていない。本文の差分は git が持っているので、
**足りなかった「その版のときの数値」だけ**を git から読む。

### データの指紋

`_session`（分析を走らせた環境）はソフトウェアの版しか残さない。再現性の
もう半分は「**同じデータで走らせたか**」で、それを保証するのがこちら。

```bash
octavo data hash     # いまの data/ の中身を記録する
octavo data status   # 記録と食い違っていないか見る
```

`data/raw/` と `data/derived/` は `.gitignore` で git に入らない。つまり
`data/HASHES.json` が「そのとき使ったデータはこれだった」という**唯一の
記録**になる（`data/raw/README.md` の出所と対で意味を持つ）。`octavo check`
も食い違いを見る。

### 受理後の複製パッケージ

投稿用が「組版に要るもの」なのに対し、複製パッケージは「**もう一度この結果を
出すのに要るもの**」。中身が別物なので別の作り方をする。

```bash
octavo bundle --replication                 # replication.zip
octavo bundle --replication --with-raw-data # 原データも入れる
```

入るのは `analysis/`（`octavo.R` ごと）`results/` `figures/` `tables/`
`data/derived/` `data/HASHES.json` `octavo.config.py` `literature.bib` と、
再現の手順書（`_session` の記録つき）。**原データは既定で入れない** —
再配布できないことがあるため、`--with-raw-data` で明示する。
`replication_exclude` にグロブを書けば個別に外せる。

---

## 7. 自分用にする: ひな型と Word のスタイル

### ひな型を差し替える

Octavo が書き出すもの・組版に使うもの（プロジェクトのひな型、原稿のひな型、
論文の `main.typ` / `main.tex`、スライドや配布資料の体裁）はすべて `templates/`
の下のファイルで、**どれも自分のものに差し替えられる**。同じ相対パスで
`<プロジェクト>/templates/`（そのプロジェクトだけ）か `~/.config/octavo/templates/`
（自分の全プロジェクト）に置けば、プロジェクト → 自分 → 同梱 の順に探して、
最初に見つかったものを丸ごと使う。

```bash
octavo template list                             # 何がどこから効いているか
octavo template copy slides/typst-slides.typ     # このプロジェクトの templates/ に写して直す
octavo template copy paper/en/main.typ --user    # いつもの体裁を、以後の全論文に
octavo template diff slides/typst-slides.typ     # 自分のものと同梱のものの違い
```

よく使うもの:

| ひな型 | 使われる所 | 差し替えると |
|---|---|---|
| `slides/typst-slides.typ`, `slides/typst-notes.typ` | スライドと台本の組版 | 見た目が変わる |
| `paper/<言語>/main.typ`, `main.tex` | `octavo new paper` | いつもの体裁から論文を始められる |
| `manuscripts/<言語>/*.md` | `octavo new` | 自分の骨組みから原稿を始められる |
| `project/<言語>/…` | `octavo init` | 新しいプロジェクトの中身が変わる。そこに**足した**ファイルも毎回入る |
| `handout/handout-header.tex`, `slides/beamer-header-<言語>.tex` | LaTeX / Beamer | プリアンブルが変わる |

写したものは、その後の同梱の変更には追随しない。Octavo を更新したら
`octavo template diff <name>` で違いを見る。全部の一覧は
[`templates/README.md`](templates/README.md)。

### Word のスタイル

```bash
octavo reference-docx reference.docx
```

pandoc の既定の雛形が出るので、Word で「見出し 1」「本文」「Table Caption」
などのスタイルを直して保存し、設定に書く。

```python
'docx_reference': 'reference.docx',
```

中身は空でよい（スタイル定義だけ使う）。Word には LaTeX のような自動採番の
相互参照が無いので、**図表番号はキャプションに文字として入る**
（「表1．記述統計」）。本文の「表3」という言及はそのままの文字列で残る。
原稿の並び順どおりに番号を振っているかぎり食い違わない。

節番号も同じで、**原稿が持っていた番号（`## 1. はじめに` の「1.」）を
そのまま文字として戻す**。pandoc の `--number-sections` は Word では効かず、
数え直すと「1, 2, 付録A」のような並びが崩れるため、原稿の番号を使う。

---

## 8. 形式ごとの違い（知っておくこと）

| | LaTeX | Typst | Word |
|---|---|---|---|
| 日本語フォント | haranoaji が TeX Live 同梱。設定不要 | **同梱されない。**`setup.sh` が入れる（「書体」の節。`typst fonts` で確認） | Word 側の設定 |
| 節番号 | 組版側が振る | 組版側が振る | **原稿の番号を文字で戻す** |
| 図表番号 | 自動 | 自動 | キャプションに文字で入れる |
| 相互参照 | `\ref` でリンク | `#ref(<label>)` でリンク | 文字のまま |
| 外部の表ファイル | `\inputtable` | `#include` | 使えない |
| キャプション中の `**強調**` | 文字どおり出る | 実際に太字になる | — |
| 書誌 | `CSLReferences` 環境（`main.tex` に定義が要る） | 本文に埋まる | 段落として入る |

Typst で `typst_citations: 'native'` にすると、CSL ではなく Typst の
`bibliography()` に任せる（`main.typ` 側の設定が効く）。既定は `'csl'`。

**スライドには書誌一覧を出さない**（枠に入りきらないため）。出したいときは
スライドの原稿の末尾に見出しと空の `::: {#refs}` を置き、`slides_bibliography`
を `True` にする。

```markdown
## References

::: {#refs}
:::
```

### Typst スライド

`typst-slides` は**パッケージを使わない素の Typst** で組む。組むときにネットワークは
要らない（Typst 0.12 以上）。段階表示などのアニメーションは持たない。

- `#` と `##` の両方があれば、`#` が節の扉、`##` が1枚のスライド。見出しが1段
  だけなら、その見出しが1枚ずつになる。`#` の直下にいきなり本文があれば、節の扉
  ではなく題のある1枚になる
- 図は残りの高さいっぱいに収まるように置く。図表に番号は付けない
- 題扉は front matter の `title` / `subtitle` / `author` / `institute` / `date`
- 体裁は `templates/slides/typst-slides.typ`。変えるなら
  `octavo template copy slides/typst-slides.typ` で写して直す（§7）。設定で変えられるのは:

| キー | 既定 | 何が変わるか |
|---|---|---|
| `typst_slides_aspect` | `'16-9'` | `'16-9'` / `'4-3'` |
| `typst_slides_font` | BIZ UDゴシック + Inter | フォントの並び。書けばそのまま使う（「書体」参照） |
| `typst_slides_numbering` | `None` | 見出しの番号。Typst の numbering 文字列（`'1.'` / `'1.1'`）。`'1.1'` は `#` の節が要る |
| `typst_slides_section_slides` | `True` | `False` で `#` の節が扉のスライドを作らず、番号だけ進める |
| `typst_slides_accent` | `'#0e2f92'` | 差し色。`None` にすると黒一色。**`None` 以外なら体裁が切り替わる**（下記） |
| `typst_slides_running_header` | `True` | 左上にいまの `#` の節を小さく出す（節が無ければデッキの題。講義の1回分など） |

  **差し色（既定でこの青が入っている）があるときだけ見た目が変わる。**
  従来どおりの黒一色（太字の題、`• ‣ –` の記号、通し番号だけのページ番号）に
  したいときは `typst_slides_accent` を `None` にする。差し色があると題を
  色で立てて太字をやめ、箇条書きの印を `▶` にし、ページ番号を「4 / 11」の
  形にし、リンクにも色が付く。
  箇条書きの**字下げだけは差し色と関係なく常に効く**（入れ子の第2階層が第1階層の
  本文と同じ位置に来て、階層が読めなかったため）。

- 事例・論点・余談・注意・付記に相当する5つの関数が使える。原稿から
  ```` ```{=typst} ```` の素通しブロックで呼ぶ（中の `{{…}}` も普通に置き換わる）:
  `#case[…]` / `#question[…]` / `#aside[…]` は1つのカウンタを共有し、`#`
  の節が変わるたびにリセットして節番号込みで振る（例: `事例2.1`）。`#nb[…]` /
  `#memo[…]` は番号を振らない。`#smallgray[…]` は出典などを小さくグレーで出す。
  Beamer にはこれらは無い。

### 台本（`typst-notes`）

`::: notes` は投影するスライドからは落ちる — 画面に出す場所が無いため。その
行き先がこれ。**同じ原稿**から、条件付きブロックの取捨もスライドと同じまま、
A4 縦で1ページ＝1枚、下に罫で囲んだノートを付けて組む。

```bash
octavo build example-lecture-03 --to typst-notes --compile
```

`typst_slides_*` の設定はそのまま効く（同じ meta block を通る）。事例・論点など
5つの関数も同じ名前で使えるので、`#case[…]` を使ったスライドの原稿がそのまま
台本になる。体裁は `templates/slides/typst-notes.typ` で、変え方は同じ（§7）。図はノートが同じページに収まる
ように高さ 6cm で抑える。毎回出したいなら文書の `targets` に足し、要るときだけ
なら `--to` で指す。

### LaTeX と日本語

日本語のとき、standalone の LaTeX/Beamer では pandoc に babel を読ませない。
引用の localization には `lang` メタデータが要るが、pandoc のテンプレートが
それを babel の言語名に写そうとして壊れた行を書くため（和文の面倒は
luatexja が見るので babel は要らない）。

---

## 9. 中身の構成

```
octavo/
  octavo                   入口（これを PATH に通す）
  pyproject.toml           pip で入れるための設定（配布名 octavo-kit・コマンド octavo）
  setup.sh                 Linux / WSL2（apt）と macOS（Homebrew）への導入
  config.example.py        設定のひな形（英語）
  config.example.ja.py     同じひな形の日本語版。キーは英語版と1対1で揃える
  octavo/
    cli.py                 サブコマンド
    config.py              octavo.config.py の読み込みと既定値
    md.py                  形式に依存しない前処理（見出し・表・図・条件付きブロック）
    values.py              分析が出した数値を本文の {{…}} に差し込む／前回との差分
    analysis.py            .qmd の鮮度判定と quarto render
    lint.py                原稿に直書きされた数値を探す
    audit.py               octavo check（検査をまとめる）
    bundle.py              octavo bundle（投稿用・複製パッケージ）
    review.py              共著者が返してきた .docx の赤入れを読む
    ghrelease.py           octavo release（版にタグを打ち、PDF を GitHub Release へ）
    dataset.py             データの指紋（data/HASHES.json）
    build.py               前処理 → pandoc → 後処理の1本道
    pandocrun.py           pandoc の呼び出しと版の判定
    bib.py                 .bib の解析と検査
    csl.py                 CSL スタイルの解決と取得
    paths.py               同梱物の置き場（clone か pip かを吸収する）
    tmpl.py                ひな型を探す（プロジェクト → 自分 → 同梱）
    confedit.py            octavo config（サイドバーに出す設定と、その1行だけの書き換え）
    i18n.py                表示の言語（OCTAVO_LANG）。画面に出す文字列は t() を通す
    lang_ja.py             その日本語訳（コードに書く原文は英語）
    check.py               octavo checkbib
    doctor.py              octavo doctor
    selftest.py            octavo selftest
    scaffold.py            octavo init（研究プロジェクト一式・仮の図）と octavo new（原稿を足す）
    backends/
      base.py              Backend の土台と相互参照の共通処理
      latex.py  typst.py  typst_slides.py  typst_notes.py  beamer.py  docx.py
  templates/                ひな型の一式。どれも差し替えられる（§7、templates/README.md）
    project/                octavo init が書くプロジェクトの木（common/ ＋ ja/ か en/）
      common/analysis/octavo.R   分析側のヘルパー（ov_value / ov_figure / ov_table）
    manuscripts/            octavo new が置く原稿（paper / appendix / slides / lecture）
    paper/                  言語ごとの main.typ / main.tex と csl-preamble.tex
    slides/  handout/      octavo build が使う体裁（Typst・Beamer・LaTeX の配布資料）
  csl/                      取ってきた CSL のキャッシュ
  tests/test_octavo.py    単体テスト
```

**形式を1つ足すときは `backends/` に1ファイル書いて `REGISTRY` に登録するだけ。**
`build.py` は形式名で分岐しない。

```bash
python3 tests/test_octavo.py       # 足りない道具が要る項目は自動で飛ばす
```

`octavo init` は原稿のテンプレートが参照する図の**仮の中身**（灰色の枠だけの PNG と PDF）も
置く。図を差し替える前でも `octavo build --compile` が最後まで通る。

---

## 10. 何が確かめられていて、何を自分で確かめるか

何かを本番で使う前に、この節は読んでほしい。

**テストで確かめていて、CI が push のたびに走らせるもの:**

- 見本の原稿から全形式を書き出すこと（Typst、Typst のスライドと台本、Word、
  LaTeX / Beamer の*ソース*まで）と、Typst を `typst compile` で PDF まで組むこと
  （CSL 引用、図表、相互参照、`main.typ` 方式と完結した文書の両方）
- `octavo init` + `octavo new` で論文・スライド・講義ノートを足したプロジェクトを、
  リポジトリの外に入れた wheel から作って組むこと
- 見出しのラベル化、日英の相互参照、条件付きブロックの出し分け、
  表・図の差し替え、front matter の受け渡し
- `.bib` の解析・検査、`\poscite` の展開、CSL スタイルの解決（キャッシュから）
- 数値の差し込み（`{{…}}` の書式・欠落の扱い・ファイル間の衝突・コード
  ブロックを避けること）と、`.qmd` の鮮度判定（更新時刻と刻印の比較、
  依存ファイルの追随、連鎖する `.qmd`）
- 同梱の分析の見本を `octavo.R` ごと `quarto render` し、`results/`・`figures/`・
  `tables/` に書かれた中身を検査すること
- 直書きの数値の検出、`octavo check` の判定、`octavo bundle` のパス平坦化
- 匿名審査の出し分け（条件付きブロック・題扉・フラグ・漏れの検出）、
  投稿規定の分量、データの指紋、`.docx` の変更履歴の読み取り、
  git の版との数値の比較、複製パッケージの中身
- VS Code 拡張のコンパイルとパッケージ化、および拡張と CLI の間の JSON の約束
  （VS Code の中での動きは自動では見ていない）

**自動では確かめていないもの。最初に使うときに自分の環境で確かめること:**

- **CSL 引用そのもの。**手元の pandoc の版に依存する（2.11 未満は
  `--citeproc` 自体を持たない）。**入れたらまず `octavo selftest` を
  走らせること**（そのために作ったコマンド）
- **Typst の日本語フォント。**Typst は CJK フォントを同梱しない。BIZ UD も
  Noto CJK も無いと別のフォントで組まれるので、最初の PDF は目で見ること
  （既定の書体のどれが見えるかは `octavo doctor` に出る）
- **LuaLaTeX の本組版。**CI は LaTeX を組まない。`ltjsarticle` / `luatexja` / beamer テーマの
  組み合わせは、フォントが揃った環境で最初の1回を目で見ること
  （`octavo doctor` で不足は分かる）
- **自分の分析の環境。**見本の分析は CI で走っているが、自分の R の版や
  パッケージで動くかは最初の1回を確かめること
- **CSL の生ダウンロード。**キャッシュ経由の解決はよく検証されているが、
  ネットワーク越しの取得はネットワーク環境に依存する

想定と違う挙動に気づいたら、`octavo doctor` の出力と pandoc / TeX / Typst の
版を添えて issue を立ててほしい。

---

## 11. VS Code 拡張

`vscode-extension/` に、この CLI を VS Code から使うための拡張が入っている。
コマンドパレットから `build` / `checkbib` / `doctor` などを呼べるほか、
マークダウン上で `@` と打つと `.bib` の文献を補完し、`{{` と打つと分析が
出した値を補完する。無い引用キーと、解決できない `{{…}}` には赤波線が出る
（判定は `octavo checkbib --json` と `octavo values --json` を読むだけで、
Python 側とロジックが二重にならないようにしてある）。Windows の VS Code から使う場合は
`wsl.exe` 経由で自動的に WSL 内の `octavo` を呼ぶ。詳しくは
`vscode-extension/README.md`。**プレビュー**もここにある — 原稿の隣の列に
組み上がった PDF が出て保存のたびに組み直し、講義ノートなら3列目にカーソルの
ある回のスライドが出る（台本に切り替えたり、2分割に戻したりできる）。

表示は既定が英語で、VS Code を日本語で使っていれば日本語になり、CLI にも
同じ言語を渡す。

```bash
cd vscode-extension
npm ci && npm run compile
npx @vscode/vsce package   # .vsix ができる。VS Code に「VSIX からインストール」
```

---

## Contributing

Issue・PR 歓迎(日本語でも可)。[CONTRIBUTING.md](CONTRIBUTING.md) を参照。

## ライセンス

MIT — [LICENSE](LICENSE) を参照。
