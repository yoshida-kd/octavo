# Octavo 手引き

**計量社会科学スターターパック**

使い方をすべて書いた手引き。Octavo が何をするものか、どう始めるかは
[README](../README.ja.md) を見る。[English guide](guide.md)

Markdown で書いた**1つの原稿**を、**Typst（論文・プリント・スライド）/ Word / LaTeX / Beamer**
に出し分けるコマンドラインツール。文献は `.bib` と CSL の仕組みに
一本化してある。日本語と英語のどちらの原稿でも同じように動く。

同じ内容から「投稿先の書式に合わせた論文」「授業用の A4 プリント」
「発表スライド」を、節の本文・図表・参考文献をコピペし直すことなく
まとめて作りたい、という学術系のワークフロー向けに作られている。

```bash
octavo init 2026-research && cd 2026-research
octavo new analysis model             # 分析（.qmd）を足す
octavo new paper example-paper        # 論文を足す（何本でも）
octavo new lecture example-lecture    # 講義ノートを足す
octavo new figure dag                 # Typst で描く図を足す（TikZ の代わり）
octavo new table compare              # 手で作る表を足す（.csv）
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

既定は TeX なしで出力できる `typst` / `typst-slides` / `docx`。LaTeX / Beamer を使うときだけ
TeX Live を足す（`bash setup.sh --with-tex`）。

引用はすべて **CSL に一本化**してある。`octavo.config.py` の `csl` を
1行変えれば、LaTeX でも Typst でも Word でも同じ書式に切り替わる。
形式ごとに引用ロジックを持つ必要はない。

---

## 1. インストール

対応する環境は Linux（Ubuntu/Debian 系のマシン、Ubuntu サーバ、または Windows 上の
WSL2/Ubuntu）と macOS（Mac では先に [Homebrew](https://brew.sh) を入れておく）。

**VS Code で使うなら、拡張機能を入れるだけでよい。**
[Octavo の拡張機能](../vscode-extension/README.ja.md)は最初に起動したときにツールが
そろっているかを確かめ、足りなければ **「セットアップ」** を出す。押すとターミナルで
`setup.sh`（拡張機能に同梱してある）が実行され、パスワードを1回聞いたあと、pandoc・
Typst・Quarto・フォント・R（CRAN の最新）・renv・uv・`octavo` コマンドそのものを
入れる。clone も pip も要らない。Remote-SSH や WSL のウィンドウなら、その先の
マシンに入る。拡張機能を更新したときなどは、Octavo のサイドバーの
**「ツール → ツールをインストール・更新する」** からいつでもやり直せる。

**ターミナルから**なら、同じことが `octavo setup`:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # uv（まだなければ）
uv tool install octavo-kit                        # octavo コマンド
octavo setup                                      # pandoc / Typst / Quarto / フォント / R / renv
octavo doctor                                     # 足りないものを報告する
octavo selftest                                   # 実際に1本通して引用の組み方を見る
```

clone して使うこともできる（`setup.sh` が `~/.local/bin/octavo` を clone に向ける）:

```bash
git clone https://github.com/yoshida-kd/octavo.git ~/octavo
bash ~/octavo/setup.sh
```

`octavo selftest` は一時ディレクトリに小さな原稿（日本語と英語の文献、団体著者、
表、図、相互参照、`\poscite`）を作って変換し、**出てきた引用と書誌の実物を
表示する**。環境ごとに1度は通しておくと、CSL の書式が思ったとおりか目で
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

### `setup.sh` がすること

`octavo setup` も拡張機能も、`setup.sh`（パッケージに同梱）を実行する。何度
実行しても安全で、入っていて十分新しいものは飛ばす。Linux では apt で:

- pandoc・Typst・Quarto を動作を確かめた版で（それより新しければそのまま）、
  それとフォント
- **R は CRAN の最新**。Ubuntu では CRAN の apt リポジトリを足す（ほかの Debian 系は
  そのディストリの `r-base`）。tidyverse などのパッケージが要る開発用ライブラリも
  一緒に入れる。さらに R のパッケージの取得先を
  [Posit Package Manager](https://packagemanager.posit.co) にする
  （`/etc/R/Rprofile.site`）ので、Linux でも renv が**ビルド済みのパッケージ**を
  入れ、コンパイルを待たずに済む
- renv（利用者の R ライブラリへ）と [uv](https://docs.astral.sh/uv/)
  （`~/.local/bin` へ）
- `octavo` コマンドを PyPI から `uv tool install` で。ただし clone から実行したとき、
  または `~/.local/bin/octavo` がすでに clone を指しているときは、そちらを残す

macOS では同じことを Homebrew で: `brew install pandoc typst`、
`brew install --cask quarto r`（`r` は CRAN の公式ビルド）と書体
（`font-biz-udmincho` など）。`octavo doctor` の案内も Mac では `brew` の書き方に
なる。CI の `macos` ジョブが、Homebrew で入れるところから組版まで毎回通している。

Windows で直接使うときは、`setup.ps1` が同じことを winget でする（下の Windows を参照）。

TeX Live は入れない。LaTeX や Beamer も使うなら `--with-tex`（数 GB。Mac では
MacTeX）。`octavo doctor` は TeX がないことを「不足」ではなく「注意」として出す。
`--no-quarto` と `--no-r` でそれぞれを外せ、`--check` は何をするかを見るだけ。

`octavo` のパッケージ自体は **Python の依存パッケージがなく**（標準ライブラリだけ）、
テンプレートも同梱している。PyPI での配布名は `octavo-kit`（`octavo` という名前は
PyPI が使わせない）で、コマンドと Python のパッケージ名は `octavo`。uv の代わりに
`pipx install octavo-kit` でも入る。

必要な版:

| | 最低 | 望ましい | 理由 |
|---|---|---|---|
| pandoc | 2.11 | 3.11 | 2.11 で `--citeproc`（CSL 引用）、3.1 で Typst 出力。3.11 で動作を確かめてある |
| Python | 3.9 | — | 標準ライブラリだけ使う（外部パッケージ不要） |
| LuaLaTeX（任意） | — | TeX Live 2021+ | `texlive-lang-japanese` が要る |
| Typst | — | 0.15 | 0.14 以上（図を PDF のまま埋め込む）。日本語フォントは同梱されない（`setup.sh` が入れる） |

### Windows

優先するのは Linux、次が macOS、Windows はその次（動くが、手のかけ方は2つより
少ない）。使い方は2通り:

- **WSL2（Ubuntu）で使う（おすすめ）**。すべて上の Linux の手順になる。VS Code
  では Remote-WSL でフォルダを開き、ファイルは Linux 側（か `/mnt/...` の下）に置く。
- **Windows で直接使う**。`octavo setup`（と、WSL にディストリがないときの拡張機能の
  「セットアップ」）は `setup.sh` の代わりに `setup.ps1` を実行する。winget で pandoc・
  Typst・Quarto・R（CRAN の最新。R のインストーラーは `PATH` を触らないので、R の
  `bin` を利用者の `PATH` に足す）を入れ、BIZ UD と Inter を利用者のフォントとして
  入れ（管理者は要らない。なければ游明朝・游ゴシックで組む）、renv を R の
  ライブラリに、`octavo` コマンドを uv で入れる。Windows では TeX は入れない（LaTeX / Beamer が要るなら
  MiKTeX か TeX Live を自分で）。CI の `windows` ジョブが `setup.ps1` を本当に
  実行し、テスト・`octavo env`・分析・PDF まで通している。

  ```powershell
  powershell -c "irm https://astral.sh/uv/install.ps1 | iex"   # uv
  uv tool install octavo-kit                                   # octavo コマンド
  octavo setup                                                 # setup.ps1 を実行する
  ```

原稿と分析の書き方はどの OS でも同じ。プロジェクトをどこでも動くように保つ
習慣が2つある: パスは `/` で書く（`../assets/figures/fig1.png`。Windows もこれを読む。
`\` は Markdown では記号の打ち消しになる）、Python でテキストファイルを開くときは
`encoding="utf-8"` を書く（Windows の既定はシステムの文字コード）。ファイル名の
大文字・小文字も原稿の書き方とそろえる（Windows は `Fig1.png` と `fig1.png` を
区別しないが、Linux は区別する）。

### 分析の環境はプロジェクトごとに（.venv と renv）

pandoc・Typst・Quarto・R・Octavo はマシンに1つ（上の `setup.sh`）。**分析に使う
パッケージはプロジェクトごとに持ち**、それを用意するのはコマンド1つ:

```bash
cd 2026-research
octavo env      # uv で .venv（+ requirements.txt）、renv（+ knitr, rmarkdown）
```

VS Code なら Octavo のサイドバーの **「ツール → このプロジェクトの分析環境を
用意する」**。`octavo env` は uv で `.venv` を作って `requirements.txt` に書いた
ものを入れ、R では `renv::init()`（`.qmd` がすでに使っているパッケージも入る）の
あとに knitr と rmarkdown（Quarto が R の `.qmd` を render するのに要る）を足して
`renv.lock` を書く。clone してきたプロジェクトなら `renv.lock` から戻す。何度
実行しても安全で、`requirements.txt` に足したものを入れるのもこれ。

git に入るのは**記録だけ**（`requirements.txt` / `renv.lock`）で、環境の中身は
入らない。Python のパッケージは `requirements.txt` に書いて `octavo env`、R では
`install.packages()` のあとに `renv::snapshot()`。Python の `.qmd` はプロジェクトの
`.venv` で動く（`QUARTO_PYTHON` を渡す）ので、`octavo analysis run` の前に
activate する必要はない。生成されるプロジェクトの `README.md` / `CLAUDE.md` にも
同じ約束が書いてある。

### 書体

Typst で組むものはすべて同じ既定を使う（`octavo/backends/typst.py::FONTS`
の1か所にある）:

| | 和文 | 英字・数字 | ないとき |
|---|---|---|---|
| 論文・A4 プリント | BIZ UD明朝 | Libertinus Serif | Noto Serif CJK JP → ヒラギノ明朝 ProN |
| スライド・台本 | BIZ UDゴシック | Inter | Noto Sans CJK JP → ヒラギノ角ゴ ProN |

BIZ UD は**等幅**のほう（プロポーショナルの BIZ UDP は使わない）。日本語の
文書では欧文フォントは英字と数字だけを受け持ち（`covers: "latin-in-cjk"`）、
「」、。などの約物は和文フォントのまま。英語の文書では欧文フォントを先頭に
置くだけ。`setup.sh` がすべて入れる（`fonts-morisawa-bizud-gothic`・
`fonts-morisawa-bizud-mincho`・`fonts-inter`・`fonts-noto-cjk`。Mac では同じものを
Homebrew の cask で）。BIZ UD や Inter がない機械でも Noto に落ちて組め、Mac で
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
- グロブに何も当たらないのは「その種類の原稿がまだない」だけなので黙っている
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
| `paper` | なし | なし（組版側が振る） | 別ファイルに切り出す | `body.typ` + 手持ちの `main.typ`（LaTeX なら `body.tex` + `main.tex`） |
| `handout` | あり | あり | 本文のまま | 完結した1枚の `.typ` / `.tex` |
| `slides` | なし | なし | 本文のまま | 完結した1枚の `.typ`（Beamer なら `.tex`） |

`paper` だけ `main.typ` / `main.tex` を手で持つ方式なのは、投稿先ごとに版面をいじる必要が
あるから。授業資料と発表スライドは1ファイルで完結させたほうが速い。

出力先は形式ごとのフォルダ（`build/typst/` など）。完結した文書は `<文書名>.typ` の
ように並ぶが、`paper` の `main.*` 方式は `main.typ` / `body.typ` の名前が決まっていて
論文が2本あるとぶつかるので、**論文ごとに `build/typst/<文書名>/`** に分ける。

### `octavo init` と `octavo new`

`octavo init` が作るのは**枠だけ**、つまり何に使うプロジェクトでも共通の部分。
分析と原稿はそこに**足す部品**で、`octavo new` でどれも何本でも足せる。最初から
置きたい部品は `init` に並べてもよい。

```
2026-research/
  CLAUDE.md          Claude Code 向けの約束事。部品の種類を足すたびに節が足される
  README.md          自分で書き足す数行（何の研究か、再現のしかた）
  octavo.config.py   設定（原稿の種類ごとのグロブ、分析の登録）
  literature.bib     書誌（文献管理ソフトからエクスポートしたもの。最初は空）
  figures/           手で作る図: Typst で描く <name>.typ、写真など
  tables/            手で作る表: <name>.csv
  assets/            分析と octavo build が書くもの。手で直さない（git には入れる）
    values/          本文の {{…}} の数値（<qmd の名前>.json）
    figures/         図（.pdf と .png）。分析の図と、figures/*.typ から組んだ図
    tables/          表（.typ / .tex / .md）。分析の表と、tables/*.csv から作った表
```

原稿は図を `assets/figures/` から貼る（`figures/` に置いた写真はそこから）。フォルダは
`octavo.config.py` で変えられる（`figure_src_dir`・`table_src_dir`・`figure_dir`・`table_dir`・`values_dir`）。

```bash
octavo new analysis model           # analysis/model.qmd — 1本目は octavo.R、data/raw/（+ README.md）、
                                    #   data/derived/、assets/tables/、requirements.txt も置く
octavo new paper example-paper      # papers/example-paper/ に paper.md と体裁の main.typ
octavo new paper example-paper --appendix   # appendix.md を足す（既にある論文にも）
octavo new paper example-paper --tex        # LaTeX 用の main.tex を足す（既にある論文にも）
octavo new slides example-talk      # slides/example-talk.md
octavo new lecture example-lecture  # lectures/example-lecture.md
octavo new figure dag               # figures/dag.typ — Typst で描く図
octavo new table compare            # tables/compare.csv — 手で作る表
```

最初から部品を置くなら、`init` に並べる:

```bash
octavo init talk --with slides=talk               # スライドだけ（分析なし）
octavo init study --with analysis,paper           # 分析と論文
octavo init course --with lecture,analysis
octavo init 2026-research --all                   # 分析・論文・スライド・講義ノートを全部
```

部品の名前は、書かなければ部品そのもの（`papers/paper/`、`slides/slides.md`）。
`paper=名前` のように書けば、その名前になる。

**既定で置くものに、後で消すものはない**: 足した原稿は見出しの骨組みだけでそのまま
組め、分析は `.qmd` の枠だけ。`refs/`（外から来た資料）や `notes/`（自分が書いた
メモ）は、要るときに自分で作る。`octavo new` は `octavo.config.py` を書き換えず、
足したあとで設定を読み直して**本当に登録されたか**を確かめる。名前が別の文書と
ぶつかるときは何も書かずに止まる。既にある論文の名前を渡すと、足りないファイル
（`--appendix` / `--tex`）だけを足し、ほかには触らない。分析のないプロジェクトでは、
`octavo check` は分析の検査をせず、`octavo env` もすることがない。

#### 見本: `--example`

```bash
octavo init demo --example          # 仮のデータの分析と、papers/example-paper/
octavo build example-paper --compile
octavo init course --with lecture --example   # 並べた部品を、どれも見本で
octavo new slides talk --example    # どのプロジェクトにも、どの種類の見本も置ける
```

見本の原稿は、見本の分析の値と図、実在しない2件の書誌を使う。そのため
`--example` は、プロジェクトにまだそれらがなければ一緒に足す（書誌は
`literature.bib` の末尾に書き足し、上書きはしない）。

見本は、すべての経路（値・図・分析の表・引用・相互参照・付録）が一緒に動くところを
見せる。どれも**見本だと分かる印**が入っている。原稿・`analysis.qmd`・`literature.bib` には
`octavo:example` のコメント、`assets/values/analysis.json` には `_placeholder`、仮の図は
枠と × だけの絵。自分の中身に置き換えたら印ごと消す。残りは `octavo check` が数える。
**仮の値のまま組むのは「致命的」**として止まる（分析を1度も実行していなくても
`{{…}}` は全部解決してしまうので、仮の数字が入った PDF が黙って作れてしまう）。

`.gitignore` は `data/raw/` と `data/derived/` を除外する（大きいデータや
再配布できないデータを事故で commit しないため）。代わりに
`data/raw/README.md` だけは追跡され、そこにデータの出所を書く決まりにしてある。
`build/` は丸ごと除外する。**手で書く体裁（`main.typ` / `main.tex`）は原稿と同じ
`papers/<name>/` にあり**、組版のたびに `build/` へコピーされるので、`build/` を消しても
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

- 回のスライドでは、その回の `#` 見出しがタイトル、講義ノートの `title` がサブタイトルになり、
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

印のない div（`::: {.warning}` など）はそのまま通る。

---

### 文書ごとの設定

`octavo.config.py` はプロジェクト全体の設定。投稿先や発表ごとに変わるものは、
**原稿の冒頭**に書けばその文書にだけ効く:

```markdown
---
title: Title of the Paper
csl: apa
word_limit: 8000
targets: [typst, docx]
---
```

| キー | 対象 | 何か |
|---|---|---|
| `csl` | すべての原稿 | 引用の書式 |
| `targets` | すべての原稿 | 出力形式（`octavo build <name>` が作るもの） |
| `word_limit`, `char_limit`, `abstract_word_limit`, `abstract_char_limit` | 論文 | 投稿規定の上限（`octavo check` が見る） |
| `typst_slides_aspect`, `typst_slides_accent`, `typst_slides_running_header`, `typst_slides_section_slides`, `typst_slides_numbering` | スライド・講義ノート | スライドの体裁 |

書いていないものはプロジェクトの設定に従う。`octavo config --doc <name>` でその文書の
設定を一覧し、`octavo config --doc <name> set KEY VALUE` / `unset KEY` で原稿のその1行を
書き換える（VS Code ではサイドバーの各原稿の下の「**この文書の設定**」）。変換のときに、
どの設定を原稿から取ったかが出る。

## 3. 原稿の書き方

| 要素 | 書き方 | 備考 |
|---|---|---|
| 見出し | `## 分析 {#sec-analysis}` | 番号は書かない（組版が振る）。ラベルで参照できる |
| 付録 | 別ファイルの `appendix.md`（§4.4） | 節は A, B, …、図などは A.1, … になる |
| 要旨 | `## Abstract` / `## 要旨` / `## 概要` | `*Word count: N words*` 行があれば一緒に切り離す |
| 参考文献節 | `## References` / `## 参考文献` | 変換時に落とす（書誌は `.bib` から組む） |
| 引用 | `@key`（地の文）、`[@key; @key2]`（括弧） | |
| 所有格引用 | `\poscite{key}` | "Smith and Taylor's (2003)" / 「山田・田中(2020)」 |
| 分析の数値 | `{{n_obs}}` / `{{coef:.2f}}` | `.qmd` が `assets/values/*.json` に出した値が入る（§4） |
| 数式 | `$\hat\beta$`（文中）、`$$ … $$`（別行） | LaTeX の書き方。どの形式にも変換される（下の「数式」） |
| 表 | Markdown の表 + すぐ下に `: 表題 {#tbl-desc}` | 分析の表と、手で作る表（`tables/*.csv`）なら表題の行だけ（下） |
| 式 | `$$ … $$ {#eq-model}` | ラベルを付ければ番号が付く |
| 図 | `![表題](assets/figures/trend.png){#fig-trend}` | 拡張子は形式ごとに付け替える（LaTeX は `.pdf`） |
| 相互参照 | `@fig-trend` `@tbl-desc` `@eq-model` `@sec-analysis` | 「図2.1」「表2.1」「式(2.1)」「第2節」（下の「相互参照」） |
| タイトル部分 | 先頭の YAML front matter | `title` / `author` / `institute` / `date` |

### 相互参照

**番号は原稿に書かない** — 見出しにも、キャプションにも、地の文にも。図・表・式・節に
ラベルを付けて名前で指せば、番号は組むときに振られる。節や図を足しても、動かしても、
消しても、参照を直す必要はない。

```markdown
## Analysis {#sec-analysis}

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

- ラベルは Quarto と同じ書き方: `fig-` `tbl-` `eq-` `sec-` のあとに、英数字と `-` `_` だけが使える。
  そのため、日本語は空けずに続けて書ける（`@fig-trendに示す`）。
- `@fig-trend` は「図2.1」（英語の文書では "Figure 2.1"）、`@tbl-desc` は「表2.1」、
  `@eq-model` は「式(2.1)」、`@sec-analysis` は「第2節」、付録の節は「付録A」になる。
  `[-@eq-model]` は番号だけ（「(2.1)」）。
- **既定は節ごとの番号**: 第3節の2つめの図は 3.2 で、式も節ごとに振り直す。
  `crossref_numbering: 'document'` にすれば通し番号（図1, 2, …）。
- 番号が付くのは、見出し（`{.unnumbered}` を除く）、キャプションのある図、キャプションの
  ある表、ラベルのある式。
- ラベルは論文と付録、講義ノートの回どうしをまたいで使える（回ごとのデッキでは、
  ほかの回への参照は、プリントでの番号を文字で書く）。
- `octavo check` は、存在しないラベルへの参照（変換では `??` になる）と、2回付けたラベルで
  止める。どこからも参照されていない図・表・式のラベルは注意として出す。

形式ごとのやり方: **Typst と LaTeX は組版側が番号を振る**。体裁は `crossref.typ` /
`crossref.tex` にあり、`octavo build` がビルドのフォルダに書く（論文は `main.typ` /
`main.tex` が読み込み、プリントとスライドには埋め込まれる。体裁を変えるなら
`octavo template copy typst/crossref.typ`）。**Word は何も番号を振らない**ので、
Octavo が見出し・キャプション・式に番号を文字で入れ、参照はそこへのリンクにする。
**スライド**もプリントと同じ番号で図・表・式を振る。講義の回ごとのデッキはプリントでの
節の番号を引き継ぐので、「図2.1」は投影でも紙でも同じ図を指す。

### 数式

数式は LaTeX の書き方で、ドル記号で囲んで書く（pandoc の読み方）。Typst（論文・
プリント・スライド・台本）では Typst の数式に、Word では Word の数式に、LaTeX /
Beamer ではそのまま出る。1つの原稿から全部に効く。

```markdown
The estimate is $\hat\beta = {{coef_x:.3f}}$, with $y_i \sim \mathcal{N}(\mu, \sigma^2)$.

$$
\hat\beta = (X^\top X)^{-1} X^\top y
$$

$$
\begin{aligned}
y_i &= \beta_0 + \beta_1 x_i + \varepsilon_i \\
\operatorname{Var}(\varepsilon_i) &= \sigma^2
\end{aligned}
$$
```

- **文中** `$…$`: ドルのすぐ内側に空白を入れない（`$x$`。`$ x $` は数式にならない）。
  閉じの `$` の直後に数字を続けない。ドル記号そのものは `\$`（`\$20`）。
- **別行** `$$…$$`: 前後に空行を置いて、独立した行に書く。`aligned`・`cases`・
  `matrix` / `pmatrix`・`\frac`・`\sum_{i=1}^{N}`・`\left( … \right)`・
  `\underbrace{…}_{…}`・`\mathbb`・`\mathcal`・`\operatorname`・`\text{…}`
  （`\text` の中の日本語も可）はどれも通る。複数行は `align` ではなく `aligned` で
  （`$$` の中の `align` は、Typst と Word は通しても LaTeX ではエラーになる）。
- **マクロ**: 1行の `\newcommand{\E}{\mathbb{E}}` を原稿のどこかに書けば、どの形式でも
  効く。Octavo は定義を原稿と付録から集め、別々に変換する部分（本文・要旨・付録・
  講義ノートの回ごとのスライド）のそれぞれに渡すので、冒頭に1組書けば足りる。
  演算子名は `\DeclareMathOperator` ではなく `\newcommand{\Cov}{\operatorname{Cov}}`
  と書く（LaTeX では前者はプリアンブルでしか使えない）。
- **分析の数値**は数式の中にも書ける: `$\hat\beta = {{coef_x}}$` は pandoc に渡る前に
  `$\hat\beta = 0.342$` になる。桁区切りのある値は数式の外に出すほうがよい
  （`$N$ = {{n_obs}}`）。数式の中ではカンマが区切り記号として組まれ、`1, 523` になる。
- **`octavo lint` は数式の中も見る**: 手で打った `$\hat\beta = 0.418$` は地の文の結果と
  同じく指摘される。`$\alpha = 0.05$`・`$x^2$`・`$\beta_1$` は指摘しない。
- **番号付きの式**: 閉じの `$$` の後ろにラベルを付けると（`$$ … $$ {#eq-model}`）、
  式に番号（節ごとに (2.1)）が付き、`@eq-model` で参照できる。ラベルのない別行の
  数式には番号を付けない。

### 図の拡張子

原稿には `.png` を書く（エディタの Markdown プレビューに出る）。`assets/figures/` の
図は、出力ごとに次のファイルを使う。

| 形式 | 使うファイル |
|---|---|
| `typst` / `typst-slides` / `typst-notes` / `latex` / `beamer` | `assets/figures/trend.pdf` — ベクター。拡大してもぼやけず、図の中の文字も検索できる |
| `docx` | `assets/figures/trend.png` — Word は PDF を図として入れられない |

`figure_ext` で変えられる（新しい Word でもベクターにするなら `{'docx': '.svg'}`。ただし分析の
図を SVG にできるのは R に cairo がある環境だけで、Mac は XQuartz がないと作れない）。
`assets/figures/` の外の図（`figures/` に置いた写真など）は、書いたとおりに使う。足りないファイルは変換時に「欠落」として出る。

### Typst で図を描く（TikZ の代わり）

箱と矢印の図、因果グラフ、フローチャートなどは、TeX の standalone TikZ のように、専用の
ファイルに Typst で描く。Octavo がそれを通常の図として組み込むので、どの出力形式でも使え、
番号が付き、参照できる。

```bash
octavo new figure dag       # figures/dag.typ（小さな diagram() と見本入り）
octavo build                # dag.typ のほうが新しければ assets/figures/dag.pdf と .png を組む
```

```markdown
@fig-dag に仮説を示す。

![仮説](../../assets/figures/dag.png){#fig-dag width=60%}
```

`.typ` の中では、`diagram()` に箱（中心の位置を cm で、と文字）と矢印（箱から箱へ。
縁から縁に引かれる）を並べる。図の大きさは箱の位置から決まる:

```typst
#diagram(
  (
    z: (2, 0, [Background $Z$]),
    x: (0, 1.6, [Education $X$]),
    y: (4, 1.6, [Income $Y$]),
    u: (4, 3, [Unobserved $U$], (stroke: none)),    // 枠なし
  ),
  (("z", "x"), ("z", "y"), ("x", "y"),
   ("u", "y", (dash: "dashed"))),                   // 破線。(arrow: false) なら矢じりなし
)
```

- パッケージは使わない。`diagram()` はファイルに書き込まれた40行ほどの Typst で、
  自由に書き換えてよい。Typst の `line`・`rect`・`circle`・`polygon`・`place` も
  そのまま使える。本格的な幾何が要るなら CeTZ などのパッケージも使える
  （`#import "@preview/cetz:…"`。初回にダウンロードされる）
- 名前が `_` で始まるファイルは図として組まない。何枚もの図で使う部品は
  `figures/_parts.typ` に置き、`#import "/figures/_parts.typ": *` と書く（`/` で
  始まるパスはプロジェクトのフォルダから）。これを変えると、全部の図が組み直される
- 図に分析の数値を出せる: `#let v = json("/assets/values/analysis.json")` として `#v.n_obs`
- キャプション・ラベル・大きさ（`width=`）は、どの図とも同じく原稿の側に書く。
  原稿に Typst を直接書いても（`` ```{=typst} `` のブロック）組めるが、Typst の出力に
  しか出ず、そこに書いたラベルは Octavo から見えない
- Typst が入っていなければ注意だけ出して、組み済みの図を使う。`.typ` に誤りがあれば
  build は止まり、Typst のメッセージを出す（そのままだと古い図が載るため）。`.typ` を
  直したあと組まれていない図は `octavo check` が注意し、`octavo release` は止まる。
  `.typ` を保存すると、開いているプレビューが組み直される

### 分析が作った表

分析が作った表も、原稿には書き写さない。`ov_table()` が表の中身を `assets/tables/<名前>.typ`・
`.tex`・`.md` に書き、原稿には表題の行だけを、ラベル `tbl-<名前>` を付けて置く:

```markdown
: Descriptive statistics {#tbl-summary}
```

上にも下にも表がない表題の行は、「分析の表 `summary` をここに入れる」という意味になる。
Typst は `.typ` を読み込み、LaTeX は `.tex` を表題とラベルつきの `table` 環境の中に
`\inputtable` し、Word には Markdown 版が入る。`@tbl-summary` でほかの表と同じく
参照できる。原稿が出す形式に要るファイルがなければ `octavo check` が止める。

### 手で作る表（CSV）

分析から出てこない表 — 概念や制度を文章で並べる比較表、文献から集めた数字、授業の小さな表 —
は、原稿に Markdown の表として書いてもよいが、列が多いと打つのが面倒で、長い文章は
セルに収まりにくい。そういう表は CSV にする: `tables/<名前>.csv`（`table_src_dir`）。
`octavo build` がそれを `ov_table()` と同じ `assets/tables/<名前>.typ`・`.tex`・`.md` にするので、
原稿には分析の表と同じく表題の行だけを置く:

```bash
octavo new table compare     # tables/compare.csv（書き始めのひな型）
```

```markdown
@tbl-compare sets the two side by side.

: The two schemes compared {#tbl-compare}
```

VS Code では、`.csv` のタブの右上の**「表として編集」**ボタンで表の形になる（サイドバーから
足した表は、はじめからこの形で開く）。行と列の追加・移動、Enter で次の行、
Alt+Enter でセルの中の改行、Excel でコピーした範囲の貼り付け。「テキストで編集」で CSV の
まま開ける）。Excel や LibreOffice で編集してもよい。設定はなく、見た目は中身から決まる:

- 1行目が見出し。**見出しの中身のあるセルの右隣が空なら、そのセルと結合する** — Excel で
  見出しのセルを結合して CSV に保存すると、ちょうどこの形になる。結合があれば2行目も見出しに
  なり（上の見出しが下の列をまとめる）、1行目の見出しの下が空なら、その見出しは2行目に下りる:

  ```
  ,2020,,2024,
  Region,N,Share,N,Share
  North,120,0.31,135,0.33
  ```

- 数字だけの列（`1,234`、`(0.05)`、`−0.12`、`12%`、`0.31***`。`-` や `—` は空欄あつかい）は
  右揃え、それ以外は左揃え
- 長い文章の列は余った幅を取って折り返す（Typst は `1fr`、LaTeX は `p{}`）。ほかの列は中身の幅
- セルは文字どおりに出る。`*`・`@`・`#` はどの形式でも書いたままになる
- Typst と LaTeX は分析の表と同じ罫線（上・見出しの下・下）で、結合した見出しの下には
  短い線を引く。Word は Markdown の表なので結合できず、2行の見出しは1つにまとめる（`2020 N`）
- 文字コードは UTF-8 で読み（BOM があってもよい）、UTF-8 でなければ Shift_JIS で読む
  （日本語版の Excel がそう保存することがある）。Octavo と拡張機能は BOM を付けない。
  **Windows の Excel で UTF-8 の CSV を開く**と日本語が化けることがあるので、
  「データ → テキストまたは CSV から」で UTF-8 を選んで開くか、VS Code で編集する

`.csv` を直したあと作られていない表は `octavo check` が注意し、`octavo release` は止まる。
分析の `ov_table()` と同じ名前の表は build を止める（どちらが組まれるかが実行の順で変わるため）。
`.csv` を保存すると、開いているプレビューが組み直される。

---

## 4. 分析（Quarto）と原稿の分業

**原稿は `.md`、分析は `.qmd`。**論文に出る数値・図・表は原稿に手で書かず、
分析側が決まった場所に書き出したものを、変換のたびに差し込む。
数値の出所が1つになるので、推定をやり直したときに本文だけ古い、という
食い違いが起きない。

```
analysis/*.qmd  --quarto render-->  assets/values/*.json   本文の {{…}}
                                    assets/figures/*.pdf|png  図
                                    assets/tables/*.tex|typ|md  表

manuscripts + the three above  --octavo build-->  Typst / Word / LaTeX / Beamer
```

### 4.1 受け渡しの3つの口

`octavo new analysis <name>` は `analysis/` に `.qmd` の枠を置き、1本目のときは
ヘルパーの `octavo.R` も置く（`--example` なら分析の例になる）。枠の最初の
チャンクが、すでに読み込んでいる:

```r
root <- Sys.getenv("OCTAVO_ROOT", unset = "")
source(if (nzchar(root)) file.path(root, "analysis", "octavo.R") else "octavo.R")
```

| 渡すもの | 分析側（.qmd） | 原稿側（.md） |
|---|---|---|
| 数値 | `ov_value("n_obs", nrow(d))` | `{{n_obs}}` |
| 図 | `ov_figure(p, "trend")` | `![推移](../../assets/figures/trend.png){#fig-trend}` |
| 表 | `ov_table(tab, "summary")` | `: 記述統計 {#tbl-summary}`（表題の行だけ） |

- `ov_value(name, x, fmt = NULL, note = NULL)` — 値を1つ登録する。
  `assets/values/<この .qmd の名前>.json` に貯まる。`ov_values(a = 1, b = 2)` でまとめ書きも可。
- `ov_figure(x, name, width, height, dpi)` — `assets/figures/` に **`.pdf` と `.png` の両方**を
  書く。Typst と LaTeX は `.pdf`（拡大してもぼやけない）、Word は `.png` を使う既定にそのまま乗る。
  `x` は ggplot でも、base graphics を描く関数でもよい。
- `ov_table(x, name, notes, align)` — `assets/tables/` に表の**中身**を `.tex`・`.typ`・`.md`
  で書く。`x` は data.frame か、出来合いの文字列を入れた
  `list(tex = …, typ = …, md = …)`。表題とラベルは原稿が持つ（`: 表題 {#tbl-<name>}`）
  ので、`caption` の引数はない。
- `ov_pval(p)` — p 値を慣例の書き方（`0.023` → `.023`、`< .001`）の文字列にする。

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

### 4.3 いつ実行されるか

`octavo build` は変換の前に `.qmd` の更新時刻を見て、**前に実行したときより
新しければ** `quarto render` を実行する。記録は `assets/values/.analysis-stamp.json`。

```python
'analysis': ['analysis/*.qmd'],
  # データの更新も監視するなら
'analysis': [{'src': 'analysis/main.qmd', 'deps': ['data/*.csv']}],
'analysis_deps': [],       # 全部の .qmd に共通の依存
'analysis_to': None,       # quarto render --to（None なら .qmd の指定に従う）
'analysis_args': [],       # Quarto に渡す追加の引数
'analysis_auto': True,     # False にすると octavo analysis run のときだけ実行される
'values_dir': 'assets/values',
'value_float_format': '.3f',
'value_thousands_sep': True,
```

- `octavo build --no-analysis` — 実行しない（いまの `assets/values/` のまま変換する）
- `octavo build --force-analysis` — 古くなくても再実行する
- `octavo analysis` — どれが古いか、値がいくつあるかを見る
- `octavo analysis run [--force]` — 古いものを実行する（手動のものも含む）
- `octavo analysis run analysis/01-clean.qmd` — その1本だけを実行する（古くなくても）
- `octavo values [--unused] [--json]` — 本文の `{{…}}` と `assets/values/` の突き合わせ
- `octavo values --diff` — **前に分析を実行したときから、本文の数字がどう動いたか**

**時間のかかる `.qmd` は `'manual': True` にする**（次の節）。`octavo build` は
それを実行せず、古ければ知らせるだけにする。実行するのは `octavo analysis run`。

**VS Code では、ここまでをすべてボタンで操作できる。**サイドバーの「分析」に
`.qmd` ごとの状態（最新・古い・手動）と実行するボタンが並び、`.qmd` を開いて
いればエディタ右上のボタンでその1本を実行できる。**プレビューは分析を実行
しない**。古い分析があれば PDF の上に帯が出るので、そこのボタンで実行すると、
終わったあとにプレビューが組み直される。進み具合は右下の通知に、Quarto の出力は
「出力」パネルの Octavo に出る。

**Quarto が入っていなければ警告して素通りする**（変換自体は pandoc だけでできる）。
入っているのに `render` が失敗したときは、古い数値のまま論文を組まないよう
**変換を止める**。止めたくないときは `--no-analysis`。

`octavo analysis run` は実行する**直前**の値を控えに取る。だから再推定のあとで

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

1本の `.qmd` は `assets/values/<その .qmd の名前>.json` を持つ。ファイルが分かれて
いても本文からは区別なく `{{名前}}` で呼べる（`octavo` が全部の `*.json` を
読んで1つにまとめる）。**同じ名前を2つの `.qmd` が書いたときは警告を出して
後を採る**ので、`octavo values` の `source` 欄で出所を確かめること。

**前段の `.qmd` が後段の入力を作る**ときは、**書いた順に実行される**ことと、
後段の `deps` に前段の出力を入れることの2つを守る。

```python
'analysis': [
    {'src': 'analysis/01-clean.qmd', 'manual': True},       # data/derived/ を作る（重い）
    {'src': 'analysis/02-model.qmd', 'deps': ['data/derived/*']},
    {'src': 'analysis/03-robustness.qmd', 'deps': ['data/derived/*']},
],
```

**データの整形のように時間がかかり、しかも滅多に変わらないものは別の `.qmd` に
分けて `'manual': True` を付ける。**`octavo build` もプレビューもそれを実行せず、
古くなったら「手動の分析が古い」と知らせるだけ。実行するのは
`octavo analysis run`（古いもの全部）か `octavo analysis run analysis/01-clean.qmd`、
VS Code ならサイドバーのボタン。整形が実行されて `data/derived/` が変われば、
後段（`02-model` など）は `deps` を見て古くなり、次に組むときに実行される。

グロブ1本（`analysis/*.qmd`）で済ませるなら、ファイル名を `01-` `02-` で
始めておけば名前順に実行される。どちらの書き方でも、`01-clean` が
`data/derived/` を書き換えたら、**同じ 1 回の `octavo build` の中で**
`02-model` も再実行される（判定は1本ずつ、その時点でやり直している）。

`.qmd` を消したり名前を変えたりすると、前に書いた `assets/values/<古い名前>.json`
が残る。本文がまだその名前を参照していると**古い数値が黙って入り続ける**ので、
`octavo analysis` と `octavo values` が「対応する `.qmd` がない値のファイル」
として知らせる。

#### 付録

付録は論文のフォルダの `appendix.md` に書く（`octavo new paper <name> --appendix` が置く）。
`documents` の `'appendix': 'papers/*/appendix.md'` が、同じフォルダの論文と結ぶ。

```bash
octavo build example-paper --to typst --appendix  # body.typ と appendix.typ の両方を作る
```

`papers/example-paper/main.typ` 側の `#show: octavo-appendix` と `#include "appendix.typ"`
（LaTeX なら `main.tex` の `\appendix` と `\input{appendix}`）のコメントを外す。

付録も本文と**同じ扱い**を受ける。`{{…}}` の差し込み、引用の解決、
条件付きブロック、相互参照はそのまま働き、`octavo values` `octavo checkbib`
`octavo outline` も付録を見る（表示では `example-paper (付録)` と出る）。
見出しに「付録A」とは書かない: 付録の節は組むときに A, B, … と振られ、付録の
図・表・式は A.1, … になる。ラベルは本文と付録をまたいで使える。

### 4.5 R 以外で書く

同梱のヘルパーは R 向けだが、`octavo` 側が見ているのは**置き場所と形だけ**なので、
Python でも Julia でも規約に合わせれば動く。

- `assets/values/<何か>.json` に `{"名前": 値}` を書く。整数と小数は JSON 上で
  区別される（`1523` と `1523.0` で既定の書式が変わる）。`{"名前":
  {"value": …, "fmt": ".2f", "note": "…"}}` の形も読む。`_` で始まるキーは無視する
- 図は `assets/figures/<name>.pdf` と `.png`、表は `assets/tables/<name>.tex` と `.typ`

---

## 5. 文献（.bib → 雑誌の書式）

### 用意する

文献管理ソフト（Zotero など）から BibTeX / BibLaTeX で書き出した `.bib` を、
`bib_file` の場所（既定は `literature.bib`）に置く。Zotero なら Better BibTeX の
自動エクスポート（Keep updated）を使うと、書誌を直すたびに `.bib` も追随し、
引用キーも途中で変わらない。

### 日本語と英語の文献を1つの書誌に

pandoc は書誌全体を1つの言語で組むので、日本語の文書では英語の文献まで
「Smith ほか (2003年)」になり、英語の題が「」に入っていた。日本語で投稿する雑誌の多くは、
欧文献と和文献に別の書き方を決めているので、日本語の文書（`lang: 'ja'`）では Octavo も
そうする:

- **本文の中の引用と英語の文献**は、選んだ書式（`csl`）を英語の決まりでそのまま使う
  （Chicago、APA、APSA など）。引用の中の日本語の名前は、*and* / *&* の代わりに「・」で
  つなぎ、*et al.* は「ほか」にする
- **`.bib` で日本語と印を付けた文献**（`langid = {japanese}`）は、**書式にかかわらず**、
  `.bib` の中身から1つの日本語の形で書く:

```
Smith et al. (2003), (山田・田中 2020), 佐藤ほか (2018)

Smith, John, Ann Taylor, Bob Brown, and Carl Green. 2003. "An Example Article." Journal of Examples 4: 1–10.
山田太郎・田中花子 (2020)「日本語論文の例」『見本学会誌』12(3): 1–20.
佐藤一郎・鈴木次郎・高橋三郎・伊藤四郎 (2018)『日本語の本』見本出版.
加藤五郎 (2015)「論文集の章」中村六郎編『論文集の名前』見本出版, 10–20.
```

論文と章の題は「」、本と雑誌の名前は『』、年は名前のあとに括弧で入れ（同じ年の2本は、書式が
付ける a / b も）、`.bib` に DOI か URL があれば最後に付ける。`langid` のない日本語の文献は
英語の決まりのまま組まれる（`octavo checkbib` が一覧にする）。`citations_by_language: False`
にすると、書誌全体を `csl_locale` の言語で組む。日本語の形は pandoc のフィルター
`templates/citations/japanese.lua` にあり、和文献の書き方に独自の決まりがある雑誌には、
プロジェクト用の写しを作って直す（`octavo template copy citations/japanese.lua`、§7）。

### 検査する

```bash
octavo checkbib           # 引用キーと .bib の突き合わせ
octavo checkbib --list    # 引いている文献の一覧
octavo checkbib --unused  # .bib にあって引いていないもの
```

見るもの:

- 引いているのに `.bib` にないキー（**組版で ?? になる**）。打ち間違いなら
  近いキーを候補として出す
- 年がない / 著者がない / 掲載誌名がない / ページも DOI もない
- 団体名が姓名に割れている（`Organization, Example` のような文献管理ソフトの入力事故）
- 日本語を含むのに `langid` がない
- 同じ文献の二重取り込み

**Octavo は `.bib` を書き換えない。**直すのは文献管理ソフトの側。直さないと決めた
ものは `bib_accepted` に理由と一緒に書けば黙る。

```python
'bib_accepted': {('yamada2020', 'no page range or DOI'): 'bulletin uses a running number instead'},
```

`octavo bib clean` は `file` / `abstract` / `keywords` を落とした軽いコピーを
**別名で**書き出す（元のファイルは触らない）。

### 雑誌に合わせる

```bash
octavo csl list                                         # 手元にあるもの
octavo csl get modern-language-association   # 取得する
octavo csl which                                        # いま使われるもの
```

`octavo.config.py` の1行を変えるだけで全形式に効く。

```python
'csl': 'apa',  # 別名。chicago / ieee / mla / nature / …
```

スタイル ID は <https://www.zotero.org/styles> で探す。従属スタイル
（親を指すだけのもの）を指定した場合は自動で親まで辿る。取ったものは
`octavo/csl/` にキャッシュされ、以後はオフラインでも使える。

`chicago-author-date` は pandoc の内蔵既定なので、`.csl` がなくても動く。

### `\poscite` の仕組み

CSL には「著者の所有格」という形がない。そこで Octavo は `.bib` から
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
octavo config [--doc NAME] [set KEY VALUE | unset KEY] [--json]  設定を見る・変える（--doc はその文書の設定）
octavo analysis [status|run] [--force]         分析 (.qmd) の状態を見る／実行する
octavo values [--unused] [--diff [ref]] [--json]  本文の {{…}} と assets/values/
octavo lint [--json]                           原稿に手入力された数値を探す
octavo check [--strict] [--anonymous]          投稿前にまとめて検査する
octavo bundle [--anonymous] [--replication] [--with-raw-data]
octavo review returned.docx [--comments|--insertions] [--json]
octavo data [status|hash]                      データのハッシュ値（sha256）
octavo checkbib [--list] [--unused]
octavo bib clean                           .bib から組版に要らない項目を落とした軽量版を作る
octavo csl get|list|which [ID]
octavo doctor [--json]
octavo setup [--with-tex] [--no-quarto] [--no-r] [--check]   ツールを入れる（setup.sh を実行する）
octavo env                                     プロジェクトの .venv（uv）と renv を用意する
octavo init <dir> [--lang ja|en] [--with PARTS | --all] [--example]
octavo new paper|slides|lecture|analysis|figure|table <name> [--example] [--json]   原稿・分析・図・表を足す
octavo new paper <name> --appendix|--tex      appendix.md / main.tex を足す（後からでも）
octavo template list|copy|diff [name] [--user]  自分用のテンプレート（§7）
octavo release <document> <label> [--dry-run]   この版にタグ、PDF を GitHub Release へ
octavo selftest [--to formats] [--csl ID] [--keep]   引用の組み方を実物で確かめる
octavo reference-docx [out.docx]        Word のスタイル定義用 docx を作る
octavo outline [documents...]           見出し構成を見る
octavo targets                          出力できる形式の一覧
```

`--to` は `typst,docx` のようにコンマ区切り。`all` / `print`（typst+docx）も
使える。`--compile` は完結した文書なら `typst compile` / `latexmk` を回し、
`paper` profile の Typst なら `main.typ` を組む（付録があれば付録を書き出して
から）。`paper` profile の LaTeX は投稿先ごとに回し方が違うので、`main.tex` 側で
`latexmk` を回す。

`--no-citations` は引用を解決せずに変換する。書きながら見た目だけ確かめたい
ときに速い。`--no-analysis` は `.qmd` を実行せず、いまの `assets/values/` のまま
変換する（重い推定を待ちたくないとき）。`--anonymous` は匿名審査用に組む
（下記）。

### 投稿前に検査する

`octavo check` は、散らばっている検査を1回にまとめる。**致命的**（そのまま
組むと壊れる・間違う）と**注意**（人が判断する）を分け、既定では致命的が
あるときだけ終了コードが 0 以外になる。

```
$ octavo check
[  ok  ] sources          papers/example-paper/paper.md, papers/example-paper/appendix.md, slides/example-talk.md
[ warn ] analysis         1 of 2 stale
           analysis/02-model.qmd
           -> octavo analysis run
[fatal ] figure files     1 missing
           assets/figures/effect.pdf
           -> octavo analysis run (or octavo build, for a figure drawn in Typst)
```

見るもの: 原稿の実在 / 分析が最新か / 対応する .qmd がなくなった値のファイル / 本文の `{{…}}`
の未解決 / **仮の値のまま組もうとしていないか** / 引用キー / 書誌の不備 /
**図と表のファイルが実在するか** / 仮の図 / **ひな型の残り** / 手入力の数値 /
分量 / データのハッシュ値 / 分析環境の記録。CI に置くなら `--strict`（注意も失敗にする）。

このうち**仮の値だけが「致命的」**なのは、分析を1度も実行していないプロジェクト
でも `{{…}}` が全部解決してしまい、仮の数字の入った PDF が黙って組めるため。
`octavo build` も組むたびに `[値][注意]` を出す。

`octavo lint` は「ひな型の残り」と「手入力の数値」を詳しく出す。

```
$ octavo lint
3 things that look like results typed into the manuscript

  example-paper
      51: N = 1,523   [sample size]
          The coefficient was 0.342 (SE 0.081) with N = 1,523.
```

「数値を原稿に手で書かない」という約束を機械的に確認するためのもの。表・見出し・
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

数えるのは `{{…}}` を差し込んだあとの本文で、要旨・参考文献・タイトル部分は本文から
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
octavo bundle example-paper --anonymous  # 漏れがないか見てからまとめる
octavo check --anonymous               # 自己引用の候補も出す
```

`--anonymous` は3つのことをする。

1. `.no-anonymous` を落とし、`.anonymous-only` を出す
2. タイトル部分のメタデータから `anonymous_drop_meta`（既定は著者・所属・謝辞・
   メール）を落とす
3. `build/typst/<論文>/flags.typ`（LaTeX は `build/latex/<論文>/flags.tex`）に切り替えを書く。
   **毎回書き換える**ので、匿名で組んだあと普通に組み直せば必ず戻る

**タイトル部分は `main.typ` / `main.tex` が持っていて Octavo は書き換えない。**同梱の
体裁（`templates/paper/{ja,en}/main.{tex,typ}`）は `\ifanonymous`（Typst は
`#if anonymous`）で著者行を囲んであるので、そのまま使えば切り替わる。

`octavo bundle --anonymous` はまとめたあとに**著者名が残っていないか**を見る。

- 条件分岐で囲っていない場所に名前があれば**失敗**（消し忘れ）
- 囲ってあれば組版には出ないが、`.tex` の中には文字として残る旨を伝える
  （ソースごと出す雑誌向け）
- `octavo build --anonymous` を通していなければまとめさせない

自己引用（`.bib` の著者に自分が入っている引用）は `octavo check --anonymous`
が候補として挙げる。伏せるかどうかは雑誌の規定によるので、**挙げるだけ**。

### 投稿用にまとめ直す

雑誌の投稿システムはたいてい階層を持てない。`octavo bundle` は
`image("../../assets/figures/fig1.png")` を `image("fig1.png")` に（LaTeX なら
`\includegraphics{../../assets/figures/fig1.pdf}` を `{fig1.pdf}` に）書き換え、
参照しているファイルを1つに集めて zip にする。既定は Typst で、LaTeX で
投稿するなら `--to latex` を付ける。まとめるのは**論文1本**なので名前を渡す
（リポジトリに論文が1本しかなければ省略できる）。

```bash
octavo build example-paper
octavo bundle example-paper                     # submission-example-paper.zip
octavo bundle example-paper --dir --out submission  # zip にせずフォルダで
```

`main.tex` の `\newcommand` やコメント行、`main.typ` の `//` コメント行は参照として拾わない。
`\IfFileExists{abstract.tex}` のように守られた `\input` は、なくても
欠落として数えない。**`build/` 自体は触らない**（変更はコピーに対して行う）。

### 共著者の Word 修正を見る

共著者は Word の変更履歴つきで返してくる。`octavo review` はそれを一覧にする。

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

変更履歴とコメントは `.docx`（zip）の中身を直接読むので、pandoc も追加の依存も要らない。

### 渡した版を残す（`octavo release`）

`build/` は git に入れない。中身はすべて git にあるものから作り直せるから。
ただ、**実際に渡した PDF そのもの**は、Octavo・pandoc・Typst・フォントの版が
変わると同じには作り直せない。そこで節目（共著者に送る、投稿する、発表する）
にだけ、その PDF を手元の外に置く:

```bash
octavo release example-paper v1-submitted
```

現在のコミットにタグ `example-paper-v1-submitted` を打って push し、GitHub Release を
作って、その場で組んだ PDF（文書が Word も作るなら Word も）を
`example-paper-v1-submitted.pdf` として添付する。Release の本文には、コミットと
Octavo・pandoc・Typst の版を書き残す。ファイルは GitHub に置かれ、git の履歴には
入らないので、リポジトリは膨らまない。

コミットしていない変更がある（タグが組んだものを指さなくなる）、分析が古い・
仮の値のまま、タグがもうある、のどれかなら出さない（理由はまとめて全部出す）。
組むのはその場で、分析は実行しない（実行するとコミットの後で `assets/values/` が
変わる）。`--dry-run` は確認と組版だけ、`--anonymous` は匿名版を出す。
[GitHub CLI](https://cli.github.com/)（`gh auth login` 済み）と、`origin` という
名前の GitHub のリモートが要る。

### 改訂で何が変わったかを示す（R&R）

`octavo values --diff` に **git のタグやコミット**を渡すと、その版と比べる。
`octavo release` が打ったタグもそのまま使える。

```bash
octavo release example-paper v1-submitted   # 投稿した時点で（git tag だけでもよい）
# …（査読・改訂）…
octavo values --diff example-paper-v1-submitted
```

```
Compared with git example-paper-v1-submitted

Changed (2):
  n_obs                             1,523  ->  1,608
  coef_x                          0.342  ->  0.311
```

バージョンを管理する仕組みは新しく作っていない。本文の差分は git が持っているので、
**足りなかった「その版のときの数値」だけ**を git から読む。

### データのハッシュ値

`_session`（分析を実行した環境）はソフトウェアの版しか残さない。再現性の
もう半分は「**同じデータで実行したか**」で、それを保証するのがこちら。

```bash
octavo data hash     # いまの data/ の中身を記録する
octavo data status   # 記録と食い違っていないか見る
```

`data/raw/` と `data/derived/` は `.gitignore` で git に入らない。つまり
`data/HASHES.json` が「そのとき使ったデータはこれだった」という**唯一の
記録**になる（`data/raw/README.md` の出所と対で意味を持つ）。`octavo check`
も食い違いを見る。

### 採択後の再現用パッケージ

投稿用が「組版に要るもの」なのに対し、再現用パッケージは「**もう一度この結果を
出すのに要るもの**」。中身が別物なので別の作り方をする。

```bash
octavo bundle --replication                 # replication.zip
octavo bundle --replication --with-raw-data # 原データも入れる
```

入るのは `analysis/`（`octavo.R` ごと）`assets/`（数値・図・表）`figures/`
`data/derived/` `data/HASHES.json` `octavo.config.py` `literature.bib` と、
再現の手順書（`_session` の記録つき）。**原データは既定で入れない** —
再配布できないことがあるため、`--with-raw-data` で明示する。
`replication_exclude` にグロブを書けば個別に外せる。

---

## 7. 自分用にする: テンプレートと Word のスタイル

### テンプレートを差し替える

Octavo が書き出すもの・組版に使うもの（プロジェクトの初期ファイル、原稿のひな型、
論文の `main.typ` / `main.tex`、スライドや配布資料の体裁）はすべて `templates/`
の下のファイルで、**どれも自分のものに差し替えられる**。同じ相対パスで
`<プロジェクト>/templates/`（そのプロジェクトだけ）か `~/.config/octavo/templates/`
（自分の全プロジェクト）に置けば、プロジェクト → 自分 → 同梱 の順に探して、
最初に見つかったものを丸ごと使う。

```bash
octavo template list                             # 何がどこから効いているか
octavo template copy slides/typst-slides.typ     # このプロジェクトの templates/ にコピーして直す
octavo template copy paper/en/main.typ --user    # いつもの体裁を、以後の全論文に
octavo template diff slides/typst-slides.typ     # 自分のものと同梱のものの違い
```

よく使うもの:

| テンプレート | 使われる所 | 差し替えると |
|---|---|---|
| `slides/typst-slides.typ`, `slides/typst-notes.typ` | スライドと台本の組版 | 見た目が変わる |
| `paper/<言語>/main.typ`, `main.tex` | `octavo new paper` | いつもの体裁から論文を始められる |
| `manuscripts/<言語>/*.md` | `octavo new` | 自分の骨組みから原稿を始められる（`--example` は `manuscripts/<言語>/example/`） |
| `project/<言語>/…` | `octavo init` | 新しいプロジェクトの中身が変わる。そこに**足した**ファイルも毎回入る |
| `handout/handout-header.tex`, `slides/beamer-header-<言語>.tex` | LaTeX / Beamer | プリアンブルが変わる |

コピーしたものは、その後の同梱の変更には追随しない。Octavo を更新したら
`octavo template diff <name>` で違いを見る。全部の一覧は
[`templates/README.md`](../templates/README.md)。

### Word のスタイル

```bash
octavo reference-docx reference.docx
```

pandoc の既定のスタイル定義が書き出されるので、Word で「見出し 1」「本文」「Table Caption」
などのスタイルを直して保存し、設定に書く。

```python
'docx_reference': 'reference.docx',
```

中身は空でよい（スタイル定義だけ使う）。Word は自分では何も番号を振らないので、
**番号は Octavo が文字で入れる**: 見出し（「2. 分析」）、キャプション（「表2.1　記述統計」）、
式（「(2.1)」）、そして本文の `@ラベル`（「表2.1」。その表へのリンクつき）。数え方は
Typst・LaTeX と同じ。

---

## 8. 形式ごとの違い（知っておくこと）

| | LaTeX | Typst | Word |
|---|---|---|---|
| 日本語フォント | haranoaji が TeX Live 同梱。設定不要 | **同梱されない。**`setup.sh` が入れる（「書体」の節。`typst fonts` で確認） | Word 側の設定 |
| 節番号 | 組版側が振る | 組版側が振る | **Octavo が文字で入れる** |
| 図・表・式の番号 | 自動（`crossref.tex`） | 自動（`crossref.typ`） | Octavo が文字で入れる |
| 相互参照（`@fig-…`） | `\ref` / `\eqref` | `#ref(<label>)` | 番号を文字で。リンクつき |
| 分析が作った表 | `.tex` を `\inputtable` | `.typ` を `include` | `.md` |
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
要らない（Typst 0.14 以上）。段階表示などのアニメーションは持たない。

- `#` と `##` の両方があれば、`#` が節、`##` が1枚のスライド。見出しが1段
  だけなら、その見出しが1枚ずつになる。節は `typst_slides_section_slides` を
  `True` にしたときだけ扉のスライドになる。`#` の直下にいきなり本文があれば、
  タイトルつきの1枚になる
- 図は残りの高さいっぱいに収まるように置く。図・表・式にはプリントと同じ番号が付き、`@ラベル` で参照できる
- タイトル部分は front matter の `title` / `subtitle` / `author` / `institute` / `date`
- 体裁は `templates/slides/typst-slides.typ`。変えるなら
  `octavo template copy slides/typst-slides.typ` でコピーして直す（§7）。設定で変えられるのは:

| キー | 既定 | 何が変わるか |
|---|---|---|
| `typst_slides_aspect` | `'16-9'` | `'16-9'` / `'4-3'` |
| `typst_slides_font` | BIZ UDゴシック + Inter | フォントの並び。書けばそのまま使う（「書体」参照） |
| `typst_slides_numbering` | `None` | 見出しの番号。Typst の numbering 文字列（`'1.'` / `'1.1'`）。`'1.1'` は `#` の節が要る |
| `typst_slides_section_slides` | `False` | `True` で `#` の節ごとに扉のスライドを作る。`False` なら番号だけ進める |
| `typst_slides_accent` | `'#0e2f92'` | アクセントカラー。`None` にすると黒一色。**`None` 以外なら体裁が切り替わる**（下記） |
| `typst_slides_running_header` | `True` | 左上にいまの `#` の節を小さく出す（節がなければデッキのタイトル。講義の1回分など） |

  **アクセントカラー（既定でこの青が入っている）があるときだけ見た目が変わる。**
  従来どおりの黒一色（太字の題、`• ‣ –` の記号、通し番号だけのページ番号）に
  したいときは `typst_slides_accent` を `None` にする。アクセントカラーがあると題を
  色で立てて太字をやめ、箇条書きの印を `▶` にし、ページ番号を「4 / 11」の
  形にし、リンクにも色が付く。
  箇条書きの**字下げだけはアクセントカラーと関係なく常に効く**（入れ子の第2階層が第1階層の
  本文と同じ位置に来て、階層が読めなかったため）。

- 事例・論点・余談・注意・付記に相当する5つの関数が使える。原稿から
  ```` ```{=typst} ```` の素通しブロックで呼ぶ（中の `{{…}}` も普通に置き換わる）:
  `#case[…]` / `#question[…]` / `#aside[…]` は1つのカウンタを共有し、`#`
  の節が変わるたびにリセットして節番号込みで振る（例: `事例2.1`）。`#nb[…]` /
  `#memo[…]` は番号を振らない。`#smallgray[…]` は出典などを小さくグレーで出す。
  Beamer にはこれらはない。

### 台本（`typst-notes`）

`::: notes` は投影するスライドからは落ちる — 画面に出す場所がないため。その
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
それを babel の言語名に対応づけようとして壊れた行を書くため（和文の面倒は
luatexja が見るので babel は要らない）。

---

## 9. 中身の構成

```
octavo/
  bin/octavo               入口（これを PATH に通す）
  pyproject.toml           pip で入れるための設定（配布名 octavo-kit・コマンド octavo）
  setup.sh                 Linux / WSL2（apt）と macOS（Homebrew）にツールを入れる。
                           octavo setup も拡張機能の「セットアップ」もこれを実行する
  setup.ps1                同じことを Windows で直接（winget）
  config.example.py        設定のひな型（英語）
  config.example.ja.py     同じひな型の日本語版。キーは英語版と1対1で揃える
  octavo/
    cli.py                 サブコマンド
    config.py              octavo.config.py の読み込みと既定値
    md.py                  形式に依存しない前処理（見出し・表・図・条件付きブロック）
    values.py              分析が出した数値を本文の {{…}} に差し込む／前回との差分
    analysis.py            .qmd の鮮度判定と quarto render
    diagrams.py            Typst で描く図（figures/*.typ -> assets/figures/）
    handtables.py          手で作る表（tables/*.csv -> assets/tables/）
    lint.py                原稿に手入力された数値を探す
    audit.py               octavo check（検査をまとめる）
    bundle.py              octavo bundle（投稿用・再現用パッケージ）
    review.py              共著者が返してきた .docx の変更履歴を読む
    ghrelease.py           octavo release（版にタグを打ち、PDF を GitHub Release へ）
    dataset.py             データのハッシュ値（data/HASHES.json）
    build.py               前処理 → pandoc → 後処理の1本道
    pandocrun.py           pandoc の呼び出しと版の判定
    bib.py                 .bib の解析と検査
    csl.py                 CSL スタイルの解決と取得
    paths.py               同梱物の置き場（clone か pip かを吸収する）
    tmpl.py                テンプレートを探す（プロジェクト → 自分 → 同梱）
    confedit.py            octavo config（サイドバーに出す設定と、その1行だけの書き換え）
    i18n.py                表示の言語（OCTAVO_LANG）。画面に出す文字列は t() を通す
    lang_ja.py             その日本語訳（コードに書く原文は英語）
    check.py               octavo checkbib
    doctor.py              octavo doctor（--json は拡張機能が読む）
    envsetup.py            octavo env（プロジェクトの .venv と renv）
    selftest.py            octavo selftest
    scaffold.py            octavo init（研究プロジェクト一式。--example で見本も）と octavo new（原稿を足す）
    backends/
      base.py              Backend の土台と相互参照の共通処理
      latex.py  typst.py  typst_slides.py  typst_notes.py  beamer.py  docx.py
  templates/                テンプレートの一式。どれも差し替えられる（§7、templates/README.md）
    project/                octavo init が書く枠（ja/ か en/）
    claude/                 プロジェクトの CLAUDE.md。部品の種類ごとの節
    analysis/               1本目の分析が一緒に置くもの（common/analysis/octavo.R — ヘルパー —、data/raw/README.md、requirements.txt）
    example/                見本が使うもの（仮の値と表、実在しない2件の書誌）
    manuscripts/            octavo new が置くもの（paper / appendix / slides / lecture / analysis.qmd。--example は example/）
    paper/                  言語ごとの main.typ / main.tex と csl-preamble.tex
    slides/  handout/      octavo build が使う体裁（Typst・Beamer・LaTeX の配布資料）
  csl/                      取得した CSL のキャッシュ
  tests/test_octavo.py    単体テスト
```

**形式を1つ足すときは `backends/` に1ファイル書いて `REGISTRY` に登録するだけ。**
`build.py` は形式名で分岐しない。

```bash
python3 tests/test_octavo.py       # 足りないツールが要る項目は自動で飛ばす
```

`octavo init` は原稿のテンプレートが参照する図の**仮の中身**（灰色の枠だけの PNG と PDF）も
置く。図を差し替える前でも `octavo build --compile` が最後まで通る。

---

## 10. 何が確かめられていて、何を自分で確かめるか

何かを本番で使う前に、この節は読んでほしい。

**テストで確かめていて、CI が push のたびに実行するもの:**

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
- 同梱の分析の見本を `octavo.R` ごと `quarto render` し、`assets/values/`・`assets/figures/`・
  `assets/tables/` に書かれた中身を検査すること
- 手入力の数値の検出、`octavo check` の判定、`octavo bundle` のパス平坦化
- 匿名審査の出し分け（条件付きブロック・タイトル部分・フラグ・漏れの検出）、
  投稿規定の分量、データのハッシュ値、`.docx` の変更履歴の読み取り、
  git の版との数値の比較、再現用パッケージの中身
- VS Code 拡張のコンパイルとパッケージ化、および拡張と CLI の間の JSON の約束
  （VS Code の中での動きは自動では見ていない）

**自動では確かめていないもの。最初に使うときに自分の環境で確かめること:**

- **CSL 引用そのもの。**手元の pandoc の版に依存する（2.11 未満は
  `--citeproc` 自体を持たない）。**入れたらまず `octavo selftest` を
  実行すること**（そのために作ったコマンド）
- **Typst の日本語フォント。**Typst は CJK フォントを同梱しない。BIZ UD も
  Noto CJK もないと別のフォントで組まれるので、最初の PDF は目で見ること
  （既定の書体のどれが見えるかは `octavo doctor` に出る）
- **LuaLaTeX の本組版。**CI は LaTeX を組まない。`ltjsarticle` / `luatexja` / beamer テーマの
  組み合わせは、フォントが揃った環境で最初の1回を目で見ること
  （`octavo doctor` で不足は分かる）
- **自分の分析の環境。**見本の分析は CI で実行されているが、自分の R の版や
  パッケージで動くかは最初の1回を確かめること
- **CSL の生ダウンロード。**キャッシュ経由の解決はよく検証されているが、
  ネットワーク越しの取得はネットワーク環境に依存する

想定と違う挙動に気づいたら、`octavo doctor` の出力と pandoc / TeX / Typst の
版を添えて issue を立ててほしい。

---

## 11. VS Code 拡張

`vscode-extension/` に、この CLI を VS Code から使うための拡張が入っている。
コマンドパレットから `build` / `checkbib` / `doctor` などを呼べるほか、
Markdown 上で `@` と打つと `.bib` の文献を補完し、`{{` と打つと分析が
出した値を補完する。ない引用キーと、解決できない `{{…}}` には赤波線が出る
（判定は `octavo checkbib --json` と `octavo values --json` を読むだけで、
Python 側とロジックが二重にならないようにしてある）。最初に起動したときにツールが
そろっているかを確かめ（`octavo doctor --json`）、足りなければ同梱の `setup.sh` を
実行する（§1）。Windows の VS Code から使う場合は
`wsl.exe` 経由で自動的に WSL 内の `octavo` を呼ぶ。詳しくは
`vscode-extension/README.md`。**プレビュー**もここにある — 原稿の隣の列に
組み上がった PDF が出て保存のたびに組み直し、講義ノートなら3列目にカーソルの
ある回のスライドが出る（台本に切り替えたり、2分割に戻したりできる）。手で作る表
（`tables/*.csv`）は表の形で編集できる。

表示は既定が英語で、VS Code を日本語で使っていれば日本語になり、CLI にも
同じ言語を渡す。

```bash
cd vscode-extension
npm ci && npm run compile
npx @vscode/vsce package   # .vsix ができる。VS Code に「VSIX からインストール」
```

---

## Contributing

Issue・PR 歓迎（日本語でも可）。[CONTRIBUTING.md](../CONTRIBUTING.md) を参照。

## ライセンス

MIT — [LICENSE](../LICENSE) を参照。
