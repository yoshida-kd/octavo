# Octavo 手引き

> これは手引きの原稿。読むなら **<https://yoshida-kd.github.io/octavo/ja/guide/>** で。 <!-- pages:skip -->

**計量社会科学スターターパック**

Octavo は、Markdown で書いた原稿から論文・配布資料・スライドを作る。Typst（PDF まで）と
Word、TeX があれば LaTeX と Beamer にも出せる。引用は1つの `.bib` から、数値・図・表は
Quarto の分析から入る。この手引きは使い方の全体で、短い紹介は
[README](https://github.com/yoshida-kd/octavo/blob/main/README.ja.md) にある。
[English guide](https://yoshida-kd.github.io/octavo/guide/)

---

## 1. インストール

Octavo 本体のほかに、いくつかのツールを使う: **pandoc**（変換）、**Typst**（PDF に組む）、
**Quarto** と **R**（分析）、**書体**、**uv**（`octavo` コマンドを入れる）。セットアップを
1回すれば全部入る。使っている環境を選ぶ:

| 使っているもの | 読むところ |
|---|---|
| Ubuntu などの Debian 系 Linux（手元の PC でも、SSH でつなぐサーバーでも） | [Linux](#11-linux) |
| Mac | [macOS](#12-macos) |
| Windows | [Windows](#13-windows)（WSL を使う方法がおすすめ。Windows で直接も可） |

どの環境でも、やり方は2通りある。**VS Code で**（拡張機能を入れてボタンを押す）か、
**ターミナルで**（コマンド4つ）。入るものは同じ。LaTeX は含まれない（なくてよい。
[LaTeX を使うなら](#16-latex-を使うなら)を参照）。

### 1.1 Linux

Octavo は Ubuntu 24.04 で確かめている。Debian やほかの版の Ubuntu でも動く（その
ディストリビューションにない書体は Noto で代わりに組む）。`sudo` を使える利用者で行う。

**VS Code で**

1. 手元の PC に [VS Code](https://code.visualstudio.com/) を入れる。
   *サーバーで Octavo を動かす場合*は、**Remote - SSH** 拡張機能も入れ、サーバーにつなぐ
   （**Remote-SSH: Connect to Host…**）。以下はすべてサーバーの上で行われる。
2. **Octavo** 拡張機能を入れる（拡張機能の画面で「Octavo」を検索。発行元は yoshida-kd）。
   Remote-SSH でつないでいるときは、**Install in SSH: …** を押してサーバー側に入れる。
3. フォルダーを開く。拡張機能がツールの有無を確かめ、**セットアップ**を勧めてくるので押す。
   ターミナルが開き、パスワード（`sudo` 用）を1回聞いてから全部を入れる。初回は時間が
   かかる（大きいのは R と書体）。
4. 終わると拡張機能がもう一度確かめる。何も言われなければ完了。

**ターミナルで**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # uv
source ~/.local/bin/env                           # このターミナルで uv を使えるようにする（新しく開き直してもよい）
uv tool install octavo-kit                        # octavo コマンド
octavo setup                                      # pandoc・Typst・Quarto・書体・R・renv（パスワードを聞かれる）
octavo doctor                                     # すべて ok になっていれば完了
```

`octavo setup` は、R が最新版になるよう CRAN の配布元を登録し、R のパッケージの取得先を
Posit Package Manager にする。プロジェクトの renv は、そこからコンパイルなしの出来合いで
パッケージを入れる。

### 1.2 macOS

**先に Homebrew を入れる。**Octavo はほかのものを Homebrew で入れる。ターミナルを開き、
[brew.sh](https://brew.sh) にある1行を実行する:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

最後に表示される指示に従い（Apple シリコンの Mac では Homebrew を `PATH` に足すよう
言われる）、ターミナルを新しく開き直す。

**VS Code で**

1. [VS Code](https://code.visualstudio.com/) と **Octavo** 拡張機能を入れる。
2. フォルダーを開き、拡張機能が勧める**セットアップ**を押す。ターミナルが開き、Homebrew で
   全部を入れる（R と Quarto でパスワードを聞かれることがある）。
3. そのあと拡張機能が `octavo` を見つけられないと言う場合は、VS Code を完全に終了して
   （⌘Q）起動し直す（新しいコマンドができる前に起動していたため）。

**ターミナルで**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # uv
source ~/.local/bin/env                           # このターミナルで uv を使えるようにする（新しく開き直してもよい）
uv tool install octavo-kit                        # octavo コマンド
octavo setup                                      # pandoc・Typst・Quarto・書体・R・renv（Homebrew で）
octavo doctor                                     # すべて ok になっていれば完了
```

R は CRAN の配布するもの（Homebrew の `r` cask）なので、CRAN のパッケージがそのまま入る。

### 1.3 Windows

方法は2つある。**WSL を使う方法をすすめる。**Octavo は Linux を第一に作って確かめて
いて、WSL なら Windows の中でそれをそのまま使える。Windows で直接使うのは、WSL が
使えないときだけにする。

#### 1.3.1 WSL を使う（おすすめ）

1. WSL を入れる。PowerShell を*管理者として*開き（スタートボタンを右クリック →
   *ターミナル（管理者）*、Windows 10 では *Windows PowerShell（管理者）*）、次を実行する:

   ```powershell
   wsl --install
   ```

   再起動を求められたら再起動する。そのあと Ubuntu が起動し、利用者名とパスワードを
   決めるよう求めてくる。パスワードはセットアップで聞かれるので覚えておく。
2. Windows に [VS Code](https://code.visualstudio.com/) を入れ、**WSL** 拡張機能を入れる。
3. VS Code の左下から **WSL: Connect to WSL** でつなぎ、Ubuntu の*中の*フォルダーを開く
   （たとえば `/home/<ユーザー名>`）。
4. **Octavo** 拡張機能を入れる。
5. Octavo 拡張機能が勧める**セットアップ**を押し、Ubuntu のパスワードを入れる。
   ここから先は [Linux](#11-linux) と同じ。

ターミナルで行う場合は、スタートメニューから *Ubuntu* を開き、
[Linux の「ターミナルで」](#11-linux)の手順に従う。

<details class="fold">
<summary><h4 id="132-windows-で直接使うwsl-なし">1.3.2 Windows で直接使う（WSL なし）</h4></summary>

[winget](https://learn.microsoft.com/ja-jp/windows/package-manager/winget/) を使う。
Windows 11 と最近の Windows 10 に入っている（`winget` が見つからなければ、Microsoft Store
から *アプリ インストーラー* を入れる）。管理者の権限は要らない。LaTeX は Windows では
入れない（使うなら MiKTeX を自分で入れる）。

**VS Code で:** [VS Code](https://code.visualstudio.com/) と **Octavo** 拡張機能を入れ、
フォルダーを開いて**セットアップ**を押す。WSL のない PC では、拡張機能は Windows の
ツールを使う。終わったら、新しいコマンドが見えるように VS Code を起動し直す。

**ターミナルで:** PowerShell を（管理者でなく）開き、次を実行する:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"   # uv
```

PowerShell を閉じて新しく開き直し（`uv` が見つかるように）、続ける:

```powershell
uv tool install octavo-kit    # octavo コマンド
octavo setup                  # pandoc・Typst・Quarto・書体・R・renv（winget で）
```

もう一度 PowerShell を開き直して確かめる:

```powershell
octavo doctor                 # すべて ok になっていれば完了
```

</details>

どの環境でも同じように動くプロジェクトにするための習慣が2つある。パスは `/` で書く
（`../assets/figures/trend.png`）。ファイル名の大文字・小文字は原稿の書き方とそろえる
（Windows は `Trend.png` と `trend.png` を区別しないが、Linux は区別する）。

### 1.4 動くか確かめる

```bash
octavo doctor       # 何が入っているか。足りないものには入れ方が付く
octavo selftest     # 小さな見本を組み、引用が実際にどう組まれたかを表示する
```

`octavo doctor` はツールごとに ok・不足・注意（あるとよいもの）を出す。`octavo selftest` は、
英語と日本語の文献・表・図・相互参照を含む見本を一時フォルダーで組み、引用が実際にどう
組まれたかを表示する。機械ごとに1回実行して、目で確かめる。

### 1.5 更新する

```bash
uv tool upgrade octavo-kit    # 最新の octavo
octavo setup                  # それが使うツール（何度実行してもよい。入っているものは飛ばす）
```

VS Code では、拡張機能を更新し、Octavo のサイドバーの「**ツール**」→「**ツールを
インストール・更新する**」を実行する。

### 1.6 LaTeX を使うなら

ここまでで入るのは Typst で PDF を作る一式で、LaTeX が要るのは `latex` と `beamer` の形式
だけ。Linux では `octavo setup --with-tex` で TeX Live を足す（数 GB）。Mac は
[MacTeX](https://www.tug.org/mactex/)、Windows は [MiKTeX](https://miktex.org/) を入れる。
`octavo doctor` は TeX を別に扱い、なくても「不足」には数えない。

### 1.7 表示の言語

メッセージは英語で出る。システムが日本語なら日本語で出る。`export OCTAVO_LANG=ja`
（または `en`）で選べる。これはメッセージの言語だけで、プロジェクトを*何語で書くか*は
その `octavo.config.py` の `lang`（`octavo init --lang ja|en`）で決まる。VS Code の拡張機能は
VS Code の表示言語に従う。

---

## 2. 最初のプロジェクト

> **VS Code なら**、ここに書いたことはコマンドを打たずにできる。まだプロジェクトでないフォルダ
> では Octavo のサイドバーが「**新しいプロジェクト**」を出す（場所・言語・最初に置くもの・見本。
> 分析を選ぶと環境まで整える）。原稿・分析・図・表は、あとからサイドバーの **+** で追加する。
> 下のコマンドは、そのボタンが実行しているものである。[10. VS Code](#10-vs-code) も参照。

### 2.1 まず見本を動かす

```bash
octavo init demo --all --example
cd demo
octavo env                    # このプロジェクトの分析の環境（.venv と renv）
octavo build --compile        # 分析を実行してから、全部を PDF まで組む
```

架空のデータの分析と、それを使う論文・スライド・講義ノートの入ったプロジェクトができる。
PDF は `build/` にできる。

### 2.2 自分のプロジェクトを始める

`octavo init` はプロジェクトの枠だけを作る。ほかはすべて `octavo new` で足し、どれもいくつでも
置ける:

```bash
octavo init study --with analysis,paper   # 枠と、分析と、論文
cd study
octavo env                                # このプロジェクトの分析環境（.venv と renv）
```

```bash
octavo new analysis model           # analysis/model.qmd（初回は octavo.R と data/ も）
octavo new analysis model --engine python   # 同じものを Python で書く（octavo_helper.py を置く）
octavo new paper example-paper      # docs/example-paper/: example-paper.md と体裁の main.typ
octavo new paper example-paper --appendix   # 付録 appendix.md を足す（既にある論文にも）
octavo new paper example-paper --tex        # LaTeX 用の main.tex を足す（既にある論文にも）
octavo new slides example-talk      # docs/example-talk/example-talk.md
octavo new lecture example-lecture  # docs/example-lecture/example-lecture.md
octavo new poster example-poster    # docs/example-poster/example-poster.md
octavo new figure dag               # figures/dag.typ（Typst で描く図）
octavo new table compare            # tables/compare.csv（手で作る表）
```

`init --with` にも同じ部品を書ける（`--with lecture`、`--with analysis,slides=talk`。`--all`
で全種類。`--engine python` で分析を Python にする）。`--example` を付けると、見出しだけの骨組みの代わりに書き方の見本が入る。`init` や `new analysis` に `--env` を付けると、分析の環境も同じ手順で整える。

**1つの文書は `docs/<name>/<name>.md`。**付録（`appendix.md`）や論文の体裁（`main.typ`）も同じ
フォルダーに置く。文書は名前で指す: `octavo build example-paper`。`paper`・`slides`・`lecture` は
ひな型の違いで、どれも同じ「文書」になる。何を作るかは原稿の冒頭で決める
（[3.6](#36-何を作るかと文書ごとの設定)）。

### 2.3 プロジェクトの中身

```
study/
  octavo.config.py   このプロジェクトの設定
  literature.bib     書誌（文献管理ソフトからエクスポートする）
  AGENTS.md          このプロジェクトの約束（AI アシスタント向け。Claude Code・GitHub Copilot・Codex・Antigravity が読む）
  CLAUDE.md          Claude Code に AGENTS.md を読ませるだけの1行
  README.md          自分で書き足す数行
  docs/<name>/       <name>.md（原稿）と、あれば appendix.md・main.typ（投稿先の体裁）
  analysis/          .qmd と補助（R なら octavo.R、Python なら octavo_helper.py）
  data/raw/          入手したままのデータ（git に入らない。data/raw/README.md に出所を書く）
  data/derived/      分析が作ったデータ（git に入らない）
  figures/           自分で作る図: Typst で描く <name>.typ、写真など
  tables/            自分で作る表（<name>.csv）
  assets/            分析と octavo build が書くもの。手で直さない
    values/          {{…}} の数値
    figures/         図（.pdf と .png）
    tables/          表（.typ・.tex・.md）
  build/             出力。出力ごとのフォルダー（pdf/・slides/・script/・word/・tex/・handouts/）。丸ごと消しても作り直せる
```

`octavo.config.py` はこれらのフォルダーの原稿と分析を最初から拾うので、足すたびに書き換える
必要はない。

**前の版で作ったプロジェクト**は、原稿が `papers/<name>/paper.md`・`slides/<name>.md`・
`lectures/<name>.md` にある。そのままで今までどおり組める。`docs/` に揃えるなら
`octavo migrate --docs`（`--dry-run` で何をするかだけ見る）。原稿を移し、図のパスと冒頭の
`outputs` / `sessions` を書き、設定に `docs/*/` を足す。文書の名前は変わらない。`octavo check`
も、移せる原稿があれば知らせる。

### 2.4 分析の環境

R や Quarto などのツールは機械に1回入れる。**分析で使うパッケージはプロジェクトごとに持つ**:

```bash
octavo env    # .venv（uv）に requirements.txt を、renv に knitr と rmarkdown を入れる
```

分析がすべて Python のプロジェクトには renv は作らない。VS Code では自分で実行しなくてよい。**最初の分析を追加したとき**（分析を入れてプロジェクトを作ったとき）に、続けて環境を整え、進み具合は通知に出る。

`requirements.txt` にパッケージを足したらもう一度実行する。R で `install.packages()` したら
`renv::snapshot()` を実行する。git に入るのは記録（`requirements.txt`・`renv.lock`）だけで、
共著者は同じコマンドで同じ環境を作れる。

- `renv::status()` が「out-of-sync」と言っても、それがコードで使っていないパッケージ（R に付いて
  くる MASS や boot、使わなくなったもの）だけなら無害。足りないものはない。
- プロジェクトの外で Quarto が R の `.qmd` を組むには、knitr と rmarkdown が要る。`octavo setup`
  がそれらを（VS Code の R 拡張機能用の `languageserver` も）自分の R のライブラリに入れる。
  古い R のパッケージを消したあとなどは、`octavo setup --r-editor` でそれだけを入れ直せる。

### 2.5 見本の見分け方

`--example` が書くものには印がある。`octavo:example` のコメント、値の `_placeholder`、枠と ×
だけの図。`octavo check` が残りを数える。中身を置き換えたら印も消す。**仮の値は
`octavo check` で「致命的」になる。**分析を1度も実行していなくても `{{…}}` は全部
解決してしまい、仮の数字の入った PDF ができるため。

---

## 3. 原稿を書く

| 何を | 書き方 |
|---|---|
| 見出し | `# 分析 {#sec-analysis}`。`#` が一番上の節（`##` から始めても組める）。番号は書かない。ラベルで参照できる |
| 要旨 | `# 要旨` の節 |
| 引用 | `@key`、`[@key; @key2]`、所有格は `\poscite{key}`（「山田・田中(2020)」） |
| 分析の数値 | `{{n_obs}}`、`{{coef_x:.2f}}`（§4） |
| 図 | `![推移](../../assets/figures/trend.png){#fig-trend}` |
| 表 | Markdown の表のすぐ下に `: 表題 {#tbl-desc}`。分析の表と `tables/` の表は表題の行だけ |
| 式 | `$$ … $$ {#eq-model}` |
| 参照 | `@fig-trend` →「図2.1」 |
| 題・著者・日付 | 冒頭の YAML（front matter） |

### 3.1 番号ではなくラベルで指す

番号は**原稿に書かない**。見出しにも、キャプションにも、地の文にも。ラベルを付けて名前で
指せば、番号は組むときに振られる。節を足したり動かしたりしても、参照を直す必要はない。

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

- ラベルは `fig-`・`tbl-`・`eq-`・`sec-` で始め、英数字と `-`・`_` で続ける（Quarto と同じ）。
  直後に日本語を続けてよい（`@fig-trendに示す`）。
- `@fig-trend` は「図2.1」、`@eq-model` は「式(2.1)」、`@sec-analysis` は「第2節」になる。
  `[-@eq-model]` は番号だけ。
- 番号は節ごと（第3節の2つ目の図は図3.2）。`crossref_numbering: 'document'` で通し番号。
- 番号が付くのは、見出し（`{.unnumbered}` を除く）、キャプションのある図と表、ラベルのある式。
- `# 題 {.appendix}` の見出しから後ろは、同じファイルの中で付録になる（A, B, …）。
- 存在しないラベルと、2回付けたラベルは `octavo check` が止める。

### 3.2 事例・論点など、番号の付くブロック

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

- 種類: `case` 事例・`question` 論点（2つで通し番号: 事例1.1、論点1.2）、
  `aside` 余談・`nb` 注意・`memo` 付記（番号なし）、`theorem` 定理・`lemma` 補題・`proposition` 命題・
  `corollary` 系・`definition` 定義・`example` 例（別の通し番号）、`remark` 注（番号なし）。
  図と同じく節ごとに振る。
- ラベルの頭は種類の名前（`#question-why`）。`@question-why` は「論点1.2」になる。
- **ブロックは1か所に書く。**`restate` は同じブロックを番号付きで再掲し（番号を押すと元の
  ブロックへ飛ぶ）、`list-of` は指定した種類のブロックを本文ごと並べる（`.titles` を足すと番号・題・
  ページだけ。`.list-of` だけなら番号のある種類すべて）。
- どの形式でも同じ見た目（見出し語は太字、本文は立体。Word では段落スタイル `Theorem`）。
  見出し語を変える・種類を足すなら `theorem_envs`:

```python
'theorem_envs': {
    'case': 'Example case',
    'claim': {'name': {'ja': '主張', 'en': 'Claim'}, 'counter': 'case'},
    'hint': {'name': 'Hint', 'numbered': False},
},
```

### 3.3 数式

ドル記号で囲んで LaTeX の書き方で書く。Typst の数式、Word の数式になり、LaTeX ではそのまま。

```markdown
The estimate is $\hat\beta = {{coef_x:.3f}}$, with $y_i \sim \mathcal{N}(\mu, \sigma^2)$.

$$
\begin{aligned}
y_i &= \beta_0 + \beta_1 x_i + \varepsilon_i \\
\operatorname{Var}(\varepsilon_i) &= \sigma^2
\end{aligned}
$$
```

- 文中の `$x$` はドルの内側に空白を入れない。ドル記号そのものは `\$`。
- 別行の数式はそれだけの行に書き、前後を空行にする。複数行は `align` ではなく `aligned`。
- 1行の `\newcommand{\E}{\mathbb{E}}` を原稿のどこかに書けば、どの形式でも使える。
  演算子は `\newcommand{\Cov}{\operatorname{Cov}}` と書く。
- 桁区切りのある値は数式の外に置く（`$N$ = {{n_obs}}`）。中に置くとカンマが区切りとして
  組まれる。

### 3.4 図

原稿には `.png` を、原稿から見た相対パスで書く（論文なら `../../assets/figures/`、
スライドと講義ノートなら `../assets/figures/`）。出力ごとに Octavo が使うファイルを選ぶ:

| 出力 | 使うファイル | なぜ |
|---|---|---|
| Typst（論文・プリント・スライド）と LaTeX | `.pdf` | ベクターなので拡大しても粗くならず、図の中の文字も選べる |
| Word | `.png` | Word は PDF の図を貼れない |
| エディタのプレビュー | `.png` | |

`ov_figure()` と Typst で描いた図は両方を書く。既定の幅は `figure_width`、図ごとには
`{width=60%}` で決める。

**図表の出典・注**は、図（表なら表題の行）のすぐ後の `::: {.figure-note}` に書く。中身は
ふつうの Markdown で、リンクも脚注も書ける。図表と一緒に小さい字で組まれ、同じページに
置かれ、図表の題には入らない。スライドでは注の分だけ図が縮む。題にも脚注を付けられる:

```markdown
![Officials by level of government[^src]](../assets/figures/staff.png){#fig-staff}

::: {.figure-note}
Source: National Personnel Authority, *Annual Report 2025*.[^checked]
:::

[^src]: Full-time staff only.
[^checked]: Retrieved 1 October 2026.
```

**自分で撮った写真など、手元の画像**（写真・画面の写し）は、Typst の図の元と同じ
`figures/` に置き、そこから直接貼る。`.jpg` も `.png` もどの出力でも使える。Octavo は
縮めないので、大きな写真は先に縮めておく（長い辺が 2,000 ピクセルほどで足りる）。そのままだと
PDF が重くなる。どこから来た画像か、使ってよいかは、データの `data/raw/README.md` と同じく
`figures/README.md` に1行書いておくとよい。

```markdown
![The council chamber](../figures/chamber.jpg){#fig-chamber width=70%}
```

**Typst で図を描く（TikZ の代わり）。**`octavo new figure dag` が、箱と矢印を描く小さな
`diagram()` 付きの `figures/dag.typ` を置く:

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

`octavo build` が `.typ` の変更を見て `assets/figures/dag.pdf` と `.png` に描き、原稿からは
ほかの図と同じように貼る。Typst で描けるものは何でも使える。複数の図で共有する部品は
`figures/_parts.typ` に置き、`json("/assets/values/analysis.json")` で分析の数値も使える。

### 3.5 表

短い表は原稿に Markdown の表で書いてよい。ほかの2種類は、表題の行だけ（隣に表のない
`: 表題 {#tbl-名前}`）で置く:

- **分析が作る表**: `ov_table(tab, "summary")` が `assets/tables/summary.*` を書き、原稿には
  `: 記述統計 {#tbl-summary}`。
- **手で作る表**: `octavo new table compare` が `tables/compare.csv` を置く。VS Code の
  「表として編集」か Excel で埋め、原稿には `: 2つの制度 {#tbl-compare}`。1行目が見出しで、
  中身のある見出しのセルの右隣を空にすると結合する（Excel が結合したセルを書き出す形）。
  そのときは2行目も見出しになる。数だけの列は右寄せ、長い文の列は折り返す。ファイルは
  UTF-8（Shift_JIS も読める）。Windows の Excel では *データ → テキストまたは CSV から*
  で開く。

### 3.6 何を作るかと文書ごとの設定

**何を作るかは、原稿の冒頭の `outputs:` で決める。**書かなければ `pdf`。

```markdown
---
title: Title of the Paper
outputs: [pdf, word]
---
```

| 出力 | できるもの |
|---|---|
| `pdf` | PDF。体裁は、原稿の横に `main.typ` があればそれ（論文）、なければ Octavo の組み込みのもの（A4。表紙・目次） |
| `word` | Word |
| `tex` | LaTeX（TeX が要る。原稿の横に `main.tex` があればそれ） |
| `slides` | スライド |
| `script` | 発表の台本（スライドの各ページと `::: notes`） |
| `poster` | ポスター（[7.3](#73-ポスター)） |
| `beamer` | LaTeX のスライド（TeX が要る） |

**何回分かの授業でできている原稿は `sessions: true`** と書く。`#` 見出し1つ（か `::: {.session}`
の区切り1つ）が1回分になり、スライドと台本は回ごとに別のファイルになる（[7.2](#72-講義ノート)）。
区切りを書いた原稿は、書かなくても回でできているものとする。

題は冒頭の `title:` に書く。本文に `# 題` は書かない（`#` の見出しは節になる）。

**そのほかの設定**も、投稿先や発表ごとに変わるものは原稿の冒頭に書けば、その文書にだけ効く:

```markdown
---
title: Title of the Paper
csl: apa
word_limit: 8000
---
```

| キー | 対象 | 何か |
|---|---|---|
| `outputs`・`sessions` | すべて | 何を作るか・回でできているか（上） |
| `csl` | すべて | 引用の書式 |
| `japanese_citation_form`・`citations_by_language` | すべて | 日本語の文献の組み方（§5） |
| `word_limit`・`char_limit`・`abstract_word_limit`・`abstract_char_limit` | すべて | 投稿規定の上限（`octavo check`） |
| `slides_*` | スライド | スライドの体裁（§7） |
| `slides_select`・`poster_select` | スライド・ポスター | `marked` で、印（`.on-slides`・`.on-poster`）の所だけを出す（§7） |
| `date_format` | すべて | 日付の出し方 |
| `toc` | 組み込みの体裁の PDF | 目次（既定は `sessions` があればあり） |
| `first_section`・`pagebreak`・`font`・`fontsize` | 組み込みの体裁の PDF | 番号の始まり・改ページ・書体（§7） |

`octavo config --doc <name>` で一覧し、`set` / `unset` でその1行を書き換える。VS Code では
サイドバーの各原稿の下の「**この文書の設定**」。

### 3.7 改ページとスライドの区切り

どちらも、その行に1つだけ書く:

```markdown
\newpage

\newslide

\newslide{Another title}
```

- `\newpage` は改ページ（PDF・Word・LaTeX）。スライドでは何もしない。
- `\newslide` はそこから新しいスライド。題は直前のスライドの題に「（続き）」が付く。
  `\newslide{題}` はその題で、`\newslide{}` は題のない1枚（図に高さを回せる）。
  スライド以外の出力では何もしない。

---

## 4. 分析

**原稿には結果を書かない。**数値・図・表は分析（`.qmd`）が作り、組むたびに取り込まれる。
推定をやり直しても、本文が古い結果のまま残ることはない。

```
analysis/*.qmd  --quarto-->  assets/values/*.json      本文の {{…}}
                             assets/figures/*.pdf|png  図
                             assets/tables/*           表
```

### 4.1 数値・図・表を渡す

新しい `.qmd` は、最初から補助（R なら `octavo.R`、Python なら `octavo_helper.py`。下を参照）を読み込んでいる。論文に出すものを登録する:

| 何を | 分析で | 原稿で |
|---|---|---|
| 数値 | `ov_value("n_obs", nrow(d))` | `{{n_obs}}` |
| 図 | `ov_figure(p, "trend")` | `![推移](../../assets/figures/trend.png){#fig-trend}` |
| 表 | `ov_table(tab, "summary")` | `: 記述統計 {#tbl-summary}` |

- `ov_figure(x, name, width, height)` は ggplot か、描く関数を受け取り、`.pdf` と `.png` を書く。
- `ov_table(x, name, notes, align)` は data.frame を受け取る。表題は原稿が持つ。
- `ov_pval(p)` は p 値を慣例の形にする（`.023`、`< .001`）。
- `ov_palette(3)` は色覚の違いがあっても見分けやすい色を返す。`ov_tint(col, 0.6)` は文字を
  載せる面のために色を白に寄せる。ggplot2 なら `ov_scale_colour_cud()` /
  `ov_scale_fill_cud()`。

新しい `.qmd` の冒頭は、そのまま1つの HTML で配れる形になっている。著者は
`octavo.config.py` の `meta` から（`affiliation` と `email` も書いてあれば入る）、日付・目次・
節番号付き。

### 4.2 数値の出方

| 値 | 例 | 出方 |
|---|---|---|
| 整数 | `nrow(d)` | `1,523` |
| 小数 | `coef(m)[["x"]]` | `0.342`（既定は小数3桁） |
| 文字列 | `ov_pval(p)` | そのまま |

書式は原稿の `{{coef_x:.2f}}` か、`ov_value(..., fmt = ".2f")` で決める。値のない名前は
`{{name}}` のまま出力に残り、そう知らされる。

### 4.3 分析が実行されるとき

`octavo build` は、`.qmd` か、それが使うファイルが前回から変わっていれば実行する。

```bash
octavo analysis              # どれが古いか
octavo analysis run          # 古いものを実行する
octavo build --no-analysis   # 何も実行せずに組む
octavo check values --diff   # 前回の実行で本文のどの数値が変わったか
```

- Quarto がなければ警告して先に進む。分析が失敗したら組むのを止める（古い数値のまま組んで
  しまうため）。
- `.qmd` がいくつあってもよい。それぞれが `assets/values/<名前>.json` を書き、原稿からは
  全部の値が見える。前の分析の結果を次の分析が使うなら、順に並べる:

```python
'analysis': [
    {'src': 'analysis/01-clean.qmd', 'manual': True},       # 時間がかかるので octavo analysis run のときだけ実行
    {'src': 'analysis/02-model.qmd', 'deps': ['data/derived/*']},
],
```

- 同じことを `.qmd` の冒頭の `octavo:` の下に書いてもよい。設定の `analysis/*.qmd` は
  そのままにできる: `manual: true`（`octavo analysis run` のときだけ実行）と `deps`（ほかに
  見張るファイル）。設定にその `.qmd` を個別に書いてあれば、そちらが優先。
- **原データをネットから取得する処理**（API、ダウンロード、データを取得する R パッケージ）は、
  手で実行する別の `.qmd` にする: `analysis/00-fetch-<取得元>.qmd` に `manual: true`。
  `data/raw/` にもうあるファイルは上書きせずに止まるようにし、取得元と取得日を
  `data/raw/README.md` に書く（`data/raw/` を git に入れないなら、残る記録はそれだけ）。

```yaml
---
title: "Fetch the raw data"
octavo:
  manual: true
---
```

- VS Code ではサイドバーの「**分析**」に `.qmd` ごとの状態が出て、ボタンで実行できる。
  プレビューは分析を実行せず、古いものがあれば知らせる。

### 4.4 Python で書く

`--engine python` を付ける（VS Code では「**Python の分析**」を選ぶ）と、`.qmd` が Python で
書かれる。`analysis/octavo_helper.py` を読み込み、これが同じ名前の関数で同じファイルを書くので、
原稿の書き方は R のときと変わらない:

```python
ov_value("n_obs", len(d))              # {{n_obs}}
ov_value("coef_x", model.params["x"])
ov_figure(fig, "trend")                # matplotlib の Figure（plotnine の ggplot、描く関数でもよい）
ov_table(tab, "summary")               # pandas の DataFrame（辞書、リストのリストでもよい）
```

- `int`（NumPy の整数も）は `1,523`、`float` は `0.342` と出る。R と同じ。
- `ov_palette()`・`ov_tint()`・`ov_pval()` もある。補助は標準ライブラリだけで動き、matplotlib と
  pandas は、図や DataFrame を渡したときだけ使う。
- `requirements.txt` に Quarto が Python を動かすのに要るもの（`ipykernel`・`nbformat`・
  `nbclient`・`pyyaml`）が入り、`octavo env` が `.venv` に入れる。`octavo analysis run` はその
  `.venv` を自分で使う。R と Python の `.qmd` は1つのプロジェクトに同居できる。

### 4.5 他の言語

Octavo はファイルを読むだけなので、Julia などの `.qmd` でも、`{"name": value}` を
`assets/values/<好きな名前>.json` に、図を `.pdf` と `.png` で `assets/figures/` に、表を
`assets/tables/` に書けば同じように使える。

---

## 5. 文献

文献管理ソフト（Zotero など）から BibTeX か BibLaTeX で `literature.bib` にエクスポート
する。Zotero なら Better BibTeX の「Keep updated」で自動的にエクスポートすると、ファイルが最新に
保たれ、キーも変わらない。**Octavo は `.bib` を書き換えない。**

```bash
octavo check cites        # 本文の引用キーが .bib にあるか、.bib に問題がないか
octavo csl get apa        # 投稿先の書式を取得する
```

書式は `octavo.config.py` の1行（`'csl': 'apa'`）で、全部の形式に効く。スタイルの ID は
<https://www.zotero.org/styles> で探せる。

**日本語と英語の文献を1つの書誌に。**日本語の文書では、英語の文献と本文中の引用は選んだ
書式どおりに、`.bib` で `langid = {japanese}` とした文献は書式によらず1つの日本語の形で組む:

```
Smith et al. (2003), (山田・田中 2020), 佐藤ほか (2018)

Smith, John, Ann Taylor, Bob Brown, and Carl Green. 2003. "An Example Article." Journal of Examples 4: 1–10.
山田太郎・田中花子 (2020)「日本語論文の例」『見本学会誌』12(3): 1–20.
```

日本語の文献の形は `japanese_citation_form` で選ぶ（プロジェクトの設定か原稿の冒頭。VS Code では
その文書の設定）:

| 値 | 日本語の文献の形 |
|---|---|
| `'standard'`（既定） | 山田太郎・田中花子 (2020)「題」『誌名』12(3): 1–20. |
| `'fullwidth'` | 山田太郎・田中花子（2020）「題」『誌名』12巻3号、1–20頁。 |
| `'period'` | 山田太郎・田中花子．2020．「題」『誌名』12巻3号、1–20頁。 |

`'fullwidth'` は『年報行政研究』に載った論文の文献一覧に多い形、`'period'` は『年報政治学』の
著者・年方式の論文に見られる形にならった。どちらの雑誌も投稿規程で文献の書き方は決めて
いないので、投稿先に指示があればそれに従う。`citations_by_language: False` にすると、書誌全体を
`csl_locale` の言語で組む。

文献の一覧は最後に置かれる。論文の最後の節の `# 参考文献` は、その置き場所の印にすぎない
（下に書いたものは一覧に置き換わる）。講義ノートの中で読書案内を並べた同じ名前の見出しは、
書いたとおりに残る。一覧を別の場所に置くには、そこに `::: {#refs}` と `:::` を書く。

`\poscite{key}` は所有格の引用（「山田・田中(2020)」「Smith and Taylor's (2003)」）。
著者が多いときのつなぎ方は書式の決まりの近似なので、1度出力を確かめる。

---

## 6. 論文: 下書きから投稿まで

論文は `docs/<name>/<name>.md` と、**手で持つ投稿先の体裁** `main.typ`（タイトル部分・
書体・余白）の組。`octavo build` が本文を `build/pdf/<name>/` に書き、`main.typ` がそれを
組む。`--compile` で PDF まで作る（`build/pdf/<name>/main.pdf`。同じものを `build/pdf/<name>.pdf`
にも置く）。

```bash
octavo build example-paper --compile            # PDF
octavo build example-paper --to word            # Word
octavo build example-paper --compile --appendix # appendix.md も
```

付録は `octavo new paper <name> --appendix` で足し、`main.typ` の `#show: octavo-appendix`
と `#include "appendix.typ"` のコメントを外す。付録の節は A, B, … になり、ラベルは本文と
付録をまたいで使える。

### 6.1 投稿の前に

```bash
octavo check           # 検査をまとめて。致命的な問題があれば終了コードが 0 以外になる
octavo check lint      # 手入力の数値と、字下げの揃っていない入れ子の箇条書き
```

`octavo check` が見るもの: 図と表のファイルの欠け、解決しない `{{…}}`、仮の値、古い分析、
引用キーと `.bib`、ラベル、見本の残り、書いたとおりに読まれない `:::` の囲み、投稿規定の分量、
データのハッシュ値。結果でない数値（成績の配分、年など）を手入力の数値の検査から外すには、
本文で `[40%]{.no-lint}`、段落ごとなら `::: {.no-lint}` … `:::` で囲むか、前後の文字ごと
`lint_accepted` に書く（`'中間レポート40%'`）。分量の上限は
設定か原稿の冒頭に書く（`word_limit: 8000`、日本語の雑誌なら `char_limit`）。

### 6.2 匿名審査

```markdown
::: {.no-anonymous}
Acknowledgements: this research was funded by ...
:::
```

```bash
octavo build example-paper --anonymous
octavo bundle example-paper --anonymous   # 投稿用のファイルに自分の名前が残っていないか確かめる
```

`--anonymous` は `.no-anonymous` のブロックを落とし（`.anonymous-only` は残し）、タイトル
部分から著者を外し、`main.typ` のタイトル部分を切り替える。次にふつうに組めば全部元に戻る。

### 6.3 投稿先に出すファイルをまとめる

```bash
octavo bundle example-paper    # submission-example-paper.zip（ファイルを1つのフォルダーにまとめたもの）
```

### 6.4 送ったあと

- **共著者の Word での直し**: `octavo review returned.docx` が変更履歴とコメントを一覧に
  する。反映は自分で原稿に行う（Word のファイルには数値が文字で入っているので、
  原稿に戻す変換はしない）。
- **送った版を残す**: `octavo release example-paper v1-submitted` がその時点にタグを打ち、
  PDF を GitHub Release に置く（`gh` コマンドが要る）。
- **改訂**: `octavo check values --diff example-paper-v1-submitted` で、その版から動いた数値が分かる。
- **データ**: `octavo data hash` が `data/` のハッシュ値を記録し、`octavo data status` が
  そのあと変わったかを見る。
- **再現用パッケージ**: `octavo bundle --replication` が、分析・値・図表・設定・ハッシュ値を
  まとめる（原データは `--with-raw-data` のときだけ）。

---

## 7. スライド・講義ノート・ポスター

### 7.1 スライド

スライドだけの文書（`outputs: [slides]`）は、`#` と `##` があれば `#` が節、`##` が1枚のスライド。見出しが1段なら
その見出しが1枚ずつ。タイトルスライドは冒頭の YAML から作る。図はスライドの残りの高さに
収まるように置かれる。

```bash
octavo build example-talk --compile
```

| キー | 既定 | 何か |
|---|---|---|
| `slides_aspect` | `'16-9'` | または `'4-3'` |
| `slides_accent` | `'#0e2f92'` | アクセントカラー。`None` で黒一色 |
| `slides_numbering` | `None` | 見出しの番号（`'1.'`、`'1.1'`） |
| `slides_section_slides` | `False` | `#` の節ごとに扉のスライドを作る |
| `slides_running_header` | `True` | 左上にいまの節を出す |
| `slides_font` | BIZ UDゴシック + Inter | 書体 |

前の名前（`typst_slides_aspect` など）で書いてあっても読む。

**スライドの区切りと題**は原稿で決められる。A4 プリントなどほかの出力には影響しない:

```markdown
## A long heading for the handout {slide-title="Short title"}

\newslide

### A heading that stays on the same slide {.same-slide}

\newslide{Another title}
```

- `\newslide` で、そこから新しいスライドにする。題は直前のスライドの題に「（続き）」を付けたもの。
  `\newslide{題}` はその題、`\newslide{}` は題のない1枚（[3.7](#37-改ページとスライドの区切り)）。
  前からの `::: {.slide title="…"}` + `:::` も同じ意味
- 見出しに `{.same-slide}`: 新しいスライドにせず、いまのスライドに太字の小見出しとして続ける
- `{slide-title="…"}`: スライドでだけ見出しの題を差し替える（回の `#` 見出しなら、その回の
  スライドの題になる）

- 見出しに `{.no-title}`: 題のない新しいスライドにする。図に高さを回せる（左上の節名は残り、
  プリントの見出しはそのまま）

`::: notes` には発表者ノートを書く。投影するスライドには出ず、`--to script` で
**台本**ができる。組んだスライドの各ページを縮小して並べ、その下にそのページのノートを置く
（A4 に2枚ずつ）。先にスライドを組むので、絵は投影する画面と同じになる。スライドには書誌一覧を出さない。出すなら
`slides_bibliography: True` にし、原稿の最後に見出しと `::: {#refs}` + `:::` を置く。

### 7.2 講義ノート

VS Code での作り方と書き方は、[講義ノートの作り方](https://yoshida-kd.github.io/octavo/ja/lectures/)に1ページでまとめてある。
ここは要点だけ。

冒頭に `outputs: [pdf, slides]` と `sessions: true` を書いた1本（`octavo new lecture` が書く）から、
**全回をまとめた A4 プリント**と**回ごとのスライド**ができる:

```bash
octavo build example-lecture --to pdf --compile      # A4 プリント
octavo build example-lecture --to slides --compile   # 回ごとのスライド
octavo build example-lecture-03 --to slides          # 1回分だけ
```

区切りを書いていなければ、**`#` 見出しが1回分**で、その中の `##` が節、`###` がスライド
1枚（回の中が `##` だけなら `##` が1枚）。デッキの名前を固定したい回は見出しに id を付ける（`# 第2回 {#second}` → `octavo build example-lecture-second`、`example-lecture-slides-second.pdf`）。
付けなければ出てきた順に `-01`, `-02`, …。

**回の区切りを自分で書く。**1回が `#` 1つに収まらないときは、各回の頭に区切りを書く。
区切りがあれば区切りが回を決め、見出しは自由に使える:

```markdown
\session{Session 3: policy and government} {#third subtitle="Public policy" date="2026-10-14"}
```

`\session{…}` の中がその回の題、`{…}` には `#id`（回の名前）・`subtitle`・`date`・`author`・
`institute` を書ける（どれも省ける。題を省くなら `\session{}`）。題・副題・日付はその回の
タイトルスライドに出る（題がなければ回の最初の見出しが題になる）。前からの
`::: {.session #third title="…"}` + `:::` も同じ意味。デッキの図・表・式・事例などの番号はプリントと同じ（プリントだけの図や、スライドに拾わなかった図があっても、番号はプリントのまま）。どの段が1枚のスライドになるかは講義ノート
全体で決まる（ふつうは `###`）ので、区切りを足しても変わらない。

**出し分け。**条件付きブロックで、どの出力に入れるかを決める:

```markdown
::: {.pdf-only}
Fill-in-the-blank space and detailed footnotes: handout only.
:::

::: {.slides-only}
Figures and short prompts: slides only.
:::
```

| 印 | 残る出力 |
|---|---|
| `.slides-only` | スライド・台本 |
| `.pdf-only` | PDF（A4 プリント・論文） |
| `.word-only` | Word |
| `.print-only` | 紙に出るもの（PDF・Word・LaTeX） |
| `.no-slides` | スライドと台本以外 |

前からの `.handout-only` も使える（組み込みの体裁の PDF・Word・LaTeX に残る）。

**一部だけをスライドにする。**冒頭に `slides_select: marked` と書くと、スライドには `.on-slides`
の印の所（`::: {.on-slides}` の囲み、見出しに `{.on-slides}` を付けた節、行の中の
`[…]{.on-slides}`）と、その上の見出しだけが出る。印のない所はプリントにだけ出る。拾わなかった
図などへの参照はプリントでの番号を文字で書き、印のない回はスライドを作らない。

**回ごとの PDF。**1回分ずつ配るなら:

```bash
octavo build example-lecture --sessions             # 回ごとに build/handouts/example-lecture-<id>.pdf
octavo extract example-lecture --session third      # 1回分（カンマ区切りで複数なら1つの PDF）
octavo extract example-lecture --pages 12-19        # 印字のページ番号で
octavo extract example-lecture --session third --cover   # 表紙と目次を前に付ける
```

プリント全体を1回だけ組み、各回のページを切り出すので、ページ番号・目次・番号はすべて全体の
まま。回の頭は必ず新しいページから始まる。ターミナルでは `octavo build <name> --sessions` で
組むときに一緒に作る（付けなければ回ごとの PDF は作り直されない）。VS Code では、サイドバーで講義
ノートを開いた中の「**回ごとの配布資料を作る**」で作れるほか、区切りのある講義ノートを保存する
たびに裏で作り直される（設定の `octavo.updateHandoutsOnSave` で止められる）。

**A4 プリントの体裁。**表紙は独立した1ページ、目次は i, ii, … のページ、本文は 1 ページ
から。組み方は日本語 LaTeX の jsarticle にならう（11pt、ゆったりした行送り、段落の頭は
1字下げ）。本文の書体は BIZ UDゴシック。プロジェクトの設定か、講義ノートの冒頭で変えられる:

| キー | 既定 | 何か |
|---|---|---|
| `first_section` | `1` | `0` にするとガイダンスが「0」になる（図は「0.1」） |
| `pagebreak` | `'session'` | 回ごとに改ページ。`'section'` は `#` ごと、`None` は区切りでだけ |
| `font` | BIZ UDゴシック + Inter | 本文の書体 |
| `fontsize` | `'11pt'` | 文字の大きさ |
| `toc` | `true` | 目次（回のない文書では `false`） |
| `date_format` | `'%Y年%-m月%-d日'`（英語は `'%B %-d, %Y'`） | `date:` の出し方。`date: today` は組んだ日 |

### 7.3 ポスター

学会のポスター発表用。冒頭に `outputs: [poster]` と書いた原稿（`octavo new poster <name>` が書く）
から、1枚の PDF（`build/poster/<name>.pdf`）を組む。既定は **A0 縦**で、**一番上の段の見出し
（`#`）1つが1マス**になり、2列×3行の格子に左上から順に入る。

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
| 見出しの後ろの `{span=2}` / `{rows=2}` | 2列ぶん / 2行ぶんのマス |
| `{cell="3,2"}` | 3列目の2行目に置く（1 から数える。ほかのマスは空いている所へ順に） |
| `poster_size` | `a0`（既定）・`a1`・`a2`・`b0`・`b1`（日本の B 列）、または `1189x841mm` のような寸法 |
| `poster_orientation` | `portrait`（縦、既定）か `landscape`（横） |
| `poster_grid` / `poster_rows` | 格子（列×行、既定 `2x3`）と、行の高さの比（既定は均等） |
| `logo` / `qr` / `qr_label` | 題の帯の左のロゴ（いくつでも）、右の QR コード（URL から作る）とその下の文字 |

論文の原稿からポスターも作るなら、`outputs: [pdf, poster]` と `poster_select: marked` と書き、
ポスターに載せる所に `.on-poster` の印を付ける（スライドの `.on-slides` と同じ書き方）。

文字の大きさと余白は判型に合わせて伸び縮みする。図はマスの残りの高さに収まる。引いた文献は
最後のマス（`# References`）に入る。**マスに入りきらない中身は、組むと「はみ出し」と
知らせる**（PDF でもそのマスの右下に赤い印が付く）。文を削るか、マスを大きくする。色は
`slides_accent`、書体は `poster_font`。体裁は `octavo template copy poster/typst-poster.typ` で
変えられる。

---

## 8. 自分用にする

### 8.1 テンプレート

Octavo が組むときに使うもの — A4 プリントとスライドの体裁、論文の `main.typ`、`octavo new`
が書く原稿、`octavo init` が書くプロジェクト — はどれも差し替えられるファイル。コピーして
直せば、以後はそちらが使われる:

```bash
octavo template list                              # どのテンプレートを、どこから使っているか
octavo template copy slides/typst-slides.typ      # このプロジェクトの templates/ へ
octavo template copy paper/en/main.typ --user     # ~/.config/octavo/templates/ へ（全部のプロジェクトで）
octavo template diff slides/typst-slides.typ      # Octavo を更新したあと: 元のほうで何が変わったか
```

| テンプレート | 差し替えると |
|---|---|
| `slides/typst-slides.typ`・`slides/typst-notes.typ` | スライドと台本の見た目が変わる |
| `poster/typst-poster.typ` | ポスターの見た目が変わる |
| `handout/handout.typ` | 講義ノートの A4 プリントが変わる |
| `paper/<lang>/main.typ` | 新しい論文がいつもの体裁で始まる |
| `manuscripts/<lang>/*.md` | 新しい原稿が自分の骨組みで始まる |
| `typst/crossref.typ` | 番号と参照の見た目が変わる |
| `citations/japanese.lua` | 書誌の日本語文献の形が変わる |

### 8.2 Word のスタイル

```bash
octavo template copy word          # templates/word/reference.docx（--user で全部のプロジェクトに）
```

できたファイルを Word で開いてスタイル（`Heading 1`・`Body Text`・`Theorem` など）を直して
保存すると、以後の Word の出力はこれで組まれる。設定の `docx_reference` に別の .docx を書けば、
そちらが優先する（前からの `octavo reference-docx` も使える）。

### 8.3 書体

| | 和文 | 欧文 |
|---|---|---|
| 論文 | BIZ UD明朝 | Libertinus Serif |
| 講義ノートの A4 プリント・スライド | BIZ UDゴシック | Inter |

`octavo setup` が入れる。ない機械では Noto CJK か、その OS にある書体（Mac はヒラギノ、
Windows は游ゴシック）で組む。足りないものは `octavo doctor` に出る。変えるなら
`font`・`slides_font`、論文は `main.typ`。

---

## 9. コマンド一覧

```
octavo build [documents...] [--to outputs] [--compile] [--appendix] [--sessions] [--no-analysis] [--anonymous]
octavo watch [documents...] [--to outputs]                           保存のたびに組み直す
octavo extract <lecture> [--session IDS] [--pages 12-19] [--cover]   一部の回やページだけを1つの PDF に
octavo documents                                                     登録されている原稿
octavo config [--doc NAME] [set KEY VALUE | unset KEY]               設定を見る・変える
octavo analysis [run [QMD]]                                          分析が最新か見る・実行する
octavo check [--strict] [--anonymous]                                投稿・配布の前の検査をまとめて
octavo check values [--unused] [--diff [ref]]                        {{...}} と分析の値を突き合わせる
octavo check cites [--list] [--unused]                               引用キーと .bib を突き合わせる
octavo check lint                                                    手入力の数値と、字下げの揃っていない入れ子の箇条書き
octavo bundle [name] [--anonymous] [--replication] [--with-raw-data]
octavo review returned.docx                                          共著者の変更履歴
octavo release <document> <label>                                    タグを打ち、PDF を GitHub Release へ
octavo data hash|status                                              data/ のハッシュ値
octavo csl get|list|which [ID]                                       引用の書式
octavo init <dir> [--lang ja|en] [--with PARTS | --all] [--engine r|python] [--example] [--env]
octavo new paper|slides|lecture|analysis|figure|table <name> [--example] [--engine r|python] [--env]
octavo template list|copy|diff [name] [--user]                       テンプレート（copy word で Word のスタイルのファイル）
octavo env                                                           このプロジェクトの R と Python のパッケージ（.venv と renv）
octavo setup [--with-tex] [--check] [--r-editor]                     ツールを入れる・更新する
octavo doctor                                                        何が入っているか
octavo selftest                                                      見本を最後まで組んでみる
octavo outline [documents...]                                        見出しの構成
octavo targets                                                       出力の一覧
octavo migrate [--docs] [--dry-run]                                  前からのプロジェクトを今の形に（--docs は原稿を docs/ へ）
```

出力（原稿の冒頭の `outputs:` と `--to` に、カンマ区切りで。`--to all` で全部）:

| 出力 | 作るもの | 要るもの |
|---|---|---|
| `pdf` | PDF（`main.typ` があれば論文の体裁、なければ組み込みの体裁） | Typst |
| `slides` | スライド | Typst |
| `script` | 台本 | Typst |
| `poster` | ポスター | Typst |
| `word` | Word | pandoc だけ |
| `tex` | LaTeX（`main.tex` があれば論文の体裁） | TeX |
| `beamer` | スライド | TeX |

前の形式の名前（`typst`・`typst-slides`・`typst-notes`・`docx`・`latex`）も同じ意味に受ける。

---

## 10. VS Code

[Octavo 拡張機能](https://marketplace.visualstudio.com/items?itemName=yoshida-kd.octavo)を
入れると、ここまでのことがボタンでできる:

- **セットアップ**でツールを入れる（§1）。サイドバーの「**ツール**」から、分析環境の準備・
  分析の実行・検査もできる。
- **プレビュー**: 原稿の隣に PDF を出し、保存のたびに組み直す。講義ノートなら3列目に、
  カーソルのある回のスライド（か台本）が出る。文字を選べ、リンクをたどれ、☰ でしおりを開ける。
- **新しいプロジェクト**は1つの画面で決める: 場所・名前・言語・最初に置くもの（R か Python の分析、論文、スライド、講義ノート）・見本で埋めるか。分析を選ぶと、続けて環境まで整える。まだプロジェクトでないフォルダでは、サイドバーが最初にこれを勧める。
- 拡張機能は **Quarto**・**R**・**Python** の拡張機能も一緒に入れる（拡張機能パック。どれも個別に外せる）。R 拡張機能は補完などに R の `languageserver` パッケージを使うが、renv のプロジェクトではプロジェクトごとに「入れますか」と聞いてくる。Octavo は一度だけ、自分の R のライブラリに入れて R 拡張機能の設定 `r.libPaths` に足すことを勧める（ターミナルなら `octavo setup --r-editor`。`octavo setup` も入れる）。
- サイドバーには原稿（とその設定）・分析・ツールが並ぶ。論文を開くと付録を足せ、
  回の区切りのある講義ノートを開くと回ごとの配布資料を作れる（保存のたびにも作り直される）。
- プレビューは、原稿のカーソルの位置までスクロールする（プレビューだけを自分でスクロールすることもできる。ツールバーの ⇅ ボタンか、設定 `octavo.previewFollowCursor` で止められる）。
- Octavo のプロジェクトで `.qmd` を開くと、最後に出力された HTML（同じフォルダの `<名前>.html`）を隣の列に出し、分析を実行し直すと読み直す。開く・保存するだけでは何も出力しない。Quarto 拡張機能の **Preview** を動かしているあいだは、こちらは閉じて出さない（設定 `octavo.qmdPreview` で全部止められる）。
- R の分析と `.venv` の両方があるプロジェクトでは、Python 拡張機能が新しいターミナルに `.venv` の activate を打ち込まないようにする（R のターミナルでは `unexpected symbol` のエラーになるため）。一度だけ知らせ、**元に戻す**こともできる。自分でその設定を書いていれば触らない。
- 引用（`@`）と分析の値（`{{`）の補完と検査。
- `tables/` と `data/` の `.csv` は、タイトルバーの「**表として編集**」のボタンで表の形にして編集できる。

フォルダーのある場所で `octavo` を実行する。手元でも、WSL でも、Remote-SSH でつないだ
サーバーでも。

---

## 11. 自分の機械で確かめること

テストは Linux・macOS・Windows で全形式を pandoc と Typst で組み、見本の分析を Quarto で（R でも
Python でも）実行している。テストでは分からないこと:

- **自分の書式で引用がどう組まれるか** — `octavo selftest` を実行して読む。
- **書体** — 最初の PDF を目で見る。足りない書体は `octavo doctor` に出る。
- **LaTeX** — LaTeX の出力を組むテストはない。最初の LaTeX / Beamer の PDF を確かめる。
- **自分の R の環境** — 見本は動く。自分のパッケージは自分で確かめる。

おかしいと思ったら、`octavo doctor` の出力を添えて [issue](https://github.com/yoshida-kd/octavo/issues)
を開いてほしい。
