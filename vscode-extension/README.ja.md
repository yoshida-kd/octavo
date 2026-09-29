# Octavo for VS Code

**計量社会科学スターターパック**

[English README is here](README.md)

論文・学会のスライド・授業の配布資料を **1つの Markdown** で書き、組み上がった
PDF を隣に置いて、保存するたびに組み直す。この拡張は
[Octavo](https://github.com/yoshida-kd/octavo) のエディタ側。Octavo は1つの
Markdown から Typst（論文・配布資料・スライド）と Word、TeX があれば LaTeX と
Beamer を作るコマンドラインのツールで、引用は .bib と CSL で揃え、数値・図・表は
手で打たずに Quarto の分析から直接差し込む。

![Octavo が見本のプロジェクトから組んだ論文の1ページとスライド](https://raw.githubusercontent.com/yoshida-kd/octavo/main/docs/images/showcase-ja.png)

- **PDF のライブプレビュー** — 左に原稿、右に PDF。講義ノートなら3列目に、
  カーソルのある回のスライド（または話す台本）が出る。
- **アクティビティバーの Octavo** — 原稿（それぞれの設定つき）、分析、使う順に
  並んだツールを1つのサイドバーに。
- **引用** — `.bib` から `@key` を補完・ホバーし、存在しないキーに波線を引く。
- **分析の値** — 分析が埋める `{{name}}` の補完・ホバー・診断。

## 必要なもの

Linux、macOS、WSL2（Ubuntu）、または Remote-SSH でつなぐサーバー（macOS では
先に [Homebrew](https://brew.sh) を入れておく）。**用意するのはこれだけ**で、
拡張機能は最初に起動したときにツールがそろっているかを確かめ、足りなければ
**「セットアップ」** を出す。押すと同梱の準備用スクリプトがターミナルで実行され、
パスワードを1回聞いたあと（sudo）、pandoc・Typst・quarto・フォント・
R（CRAN の最新）・renv・[uv](https://docs.astral.sh/uv/)・`octavo` コマンドを入れる。
Remote-SSH や WSL のウィンドウなら、その先のマシンに入る。終わったらターミナルを
閉じると、拡張機能がもう一度確かめる。

サイドバーの **「ツール → ツールをインストール・更新する」** やコマンドパレットの
**「Octavo: ツールをインストール・更新する (setup)」** からいつでもやり直せる（拡張機能を
更新したら、`octavo` コマンドもそれに合わせて上がる）。TeX は入れない。LaTeX と
Beamer の出力にだけ要る（ターミナルから `octavo setup --with-tex`）。ターミナルから
入れる方法も含めた全体像は
[Octavo の手引き](https://github.com/yoshida-kd/octavo/blob/main/docs/guide.ja.md#1-入れる) を参照。

## 始め方

1. コマンドパレット →「**Octavo: 新しいプロジェクトを作成 (init)**」で作り、
   できたフォルダを開く。最初に置くもの（分析・論文・スライド・講義ノート。
   いくつでも、なしでもよい）と、それを**見本**（まず動きを見るため）にするか
   **空**（使い続けるものだけ）にするかを選ぶ。
2. あとは Octavo のサイドバーから足す: 「**原稿を追加…**」（論文・スライド・
   講義ノート。できたらすぐ開く）、「**分析（.qmd）を追加…**」、論文の「**付録を追加**」と右クリックの
   「**LaTeX 用の main.tex を追加**」。分析を使うなら **「ツール → このプロジェクトの
   分析環境を用意する」** で `.venv`（uv）と renv ができる。
3. 原稿を開き、エディタ右上の PDF のアイコン（「**Octavo: プレビューを開く**」）
   を押す。保存すれば PDF がついてくる。

`octavo.config.py` のあるワークスペースなら、拡張は自動で動き出す。1つのワークスペースに
プロジェクトがいくつあってもよく、編集しているファイルの入っているプロジェクトを使う。

## できること

- **コマンドパレット**（`Octavo:`）から `build`・`watch`・`check`・`checkbib`・
  `doctor`・`selftest`・`init`・`new`・`analysis run`・`env`・`setup`。
- **セットアップ**: 最初に起動したときにツールを確かめ（`octavo doctor --json`）、足りない
  ものを入れるかを聞く。セットアップ用のスクリプトを同梱しているので、手で入れるのは
  拡張機能だけ。プロジェクトごとの分析の環境（uv の `.venv`、knitr と rmarkdown
  入りの renv）もボタン1つ。
- **サイドバー**（上から）: **原稿**（クリックで開く。それぞれに PDF と組版のボタン。
  講義ノートは回の一覧、論文は付録か付録を足すボタン。「**この文書の設定**」で
  引用の書式・出力形式・スライドの体裁・投稿規定の上限をその原稿の冒頭に書く）、
  **分析**（`.qmd` ごとの状態）、使う順に並んだ**ツール**（入れる → 診断 → 分析の環境 →
  分析を実行する → 書誌の確認 → 投稿前の点検）、畳んである**設定**（プロジェクトの
  既定）。引用の書式は一覧から選ぶか打ち込み、出力形式はチェックで選ぶ。変更は
  `octavo config set` を通り、その1行（原稿か `octavo.config.py`。コメントは残す）だけを
  書き換え、設定として通らない値なら書き換えない。
- **プレビュー**: 保存で組み直し、組み直してもスクロール位置を保ち、失敗は
  握り潰さずパネルに出す。「プレビュー: 3列目に表示するもの…」で、講義ノートの
  3列目をスライド／台本／表示しない（2分割）から選ぶ。PDF は同梱の [pdf.js] で
  描くので、実行時に何かを取りに行くことはない。
- **分析（Quarto）**: サイドバーの「分析」に `.qmd` ごとの状態（最新・古い・手動）と
  実行するボタン。`.qmd` を開いているときはエディタ右上のボタンでその1本を実行する。
  プレビューは分析を実行せず、古い分析があれば PDF の上の帯で知らせ、そのボタンで
  実行すると終わったあと組み直す。進み具合は通知に、quarto の出力は「出力」パネルに
  出るので、ターミナルを使わずに済む。`.qmd` そのものを書く（R のチャンクの色分け・
  1つずつの実行）には、公式の Quarto 拡張（`quarto.quarto`）を一緒に入れるとよい。
- **引用**: `@` で補完（著者と年つき）、ホバーで文献の全体（`\poscite{key}` も）、
  `Ctrl+Alt+@` で検索して挿入、ないキーに波線、`.bib` 側の問題（年がない、
  団体名が姓と名に割れている、重複）は `.bib` の上に出す。
- **Typst ファイルのプレビュー**: `.typ` を開いて「この Typst ファイルをプレビューする」で
  `typst watch` を直接回す。論文の手で管理する `main.typ` をいじるときに便利。
- **スニペット**: 表・図・所有格の引用・条件つきブロック（`ptable`・`pfigure`・
  `pposcite`・`phandout`・`pslides`・`pnotes` など）。
- **英語と日本語**: VS Code の表示言語に従い、`octavo` コマンドにも同じ言語を
  渡す。

検査はすべて `octavo` コマンド側（`octavo checkbib --json` など）が行い、拡張は
結果を表示するだけ。だから拡張の波線とコマンドの言うことが食い違うことはない。

## macOS・Windows で使う

Octavo は Linux と macOS で動く（拡張は `octavo` を呼び、セットアップが入れる先の
`~/.local/bin` は VS Code の `PATH` になくても探す。ほかの場所に置いた `octavo` は
`octavo.command` にフルパスで書く）。Windows はその次の扱い（動くが、手のかけ方は少ない）。Windows の VS Code からは:

1. **Remote-WSL でフォルダを開く**（おすすめ）。拡張が WSL の中で動き、
   すべて Linux と同じになる。
2. **WSL を入れた Windows で、Windows のフォルダを開く**。拡張は `wsl.exe` 経由で
   `octavo` を呼び（WSL にディストリがあれば `octavo.executionMode: "auto"` が
   これを選ぶ）、パスを変換する（`C:\Users\you\proj` ⇄ `/mnt/c/Users/you/proj`）。
   「セットアップ」は WSL の中に入れる。
3. **WSL を使わず Windows で直接**。WSL にディストリがなければ `auto` がこれを選ぶ
   （`octavo.executionMode` を `"local"` にしてもよい）。「セットアップ」は同梱の
   `setup.ps1` を実行し、winget で pandoc・Typst・quarto・R を、利用者のフォントに
   BIZ UD と Inter を、uv で `octavo` を入れる。インストーラーによっては Windows が
   許可を求める。拡張が開くターミナルは PowerShell。Windows では TeX は入れない。

## 設定

| キー | 既定 | 意味 |
|---|---|---|
| `octavo.executionMode` | `"auto"` | `"local"` \| `"wsl"` \| `"auto"` |
| `octavo.wslDistro` | `""` | `wsl.exe -d <name>` に渡す。空なら既定のディストリ（`wsl -l -v` で一覧） |
| `octavo.command` | `"octavo"` | 実行するコマンド（フルパスでもよい） |
| `octavo.configPath` | `""` | `octavo.config.py` の場所を明示する |
| `octavo.diagnosticsOnSave` | `true` | 保存のたびに `checkbib` を実行して波線を更新する |
| `octavo.defaultTargets` | `[]` | 「変換する…」で毎回聞かずに使う形式 |
| `octavo.previewLectureColumn` | `"slides"` | 講義ノートのプレビューの3列目: `"slides"`・`"notes"`（台本）・`"none"` |
| `octavo.typstCommand` | `"typst"` | 「この Typst ファイルをプレビューする」で実行するコマンド |
| `octavo.typstAutoOpenPdf` | `true` | Typst ファイルのプレビュー開始時に `.pdf` を開く（[LaTeX Workshop] があればそれで） |

引用の書式・スライドの見た目・投稿規定の上限といった**プロジェクトの**設定は
`octavo.config.py` にあり、サイドバーから変えられる。

## タスクから使う

拡張は `$octavo` という problem matcher を登録する:

```jsonc
{
  "label": "octavo build",
  "type": "shell",
  "command": "octavo build --to typst,docx",
  "problemMatcher": ["$octavo"]
}
```

## 既知の制限

- 波線が付くのは開いている Markdown と、拡張から読める `.bib` だけ。Windows の
  VS Code から `wsl.exe` 経由で使っていて `.bib` が WSL のホーム（`/mnt/` の外）に
  あると、`.bib` 自体には波線が出ない。プロジェクトの中に置くか、Remote-WSL を
  使えば解消する。
- `checkbib` は保存のたびに新しいプロセスで実行されるので、数千件の `.bib` だと少し
  待つことがある。気になるなら `octavo.diagnosticsOnSave` を切り、「文献を
  検査する」を手で実行する。
- 同じく `wsl.exe` 経由のとき、`/mnt/` の外にある PDF は `base64` を通して
  読むので、長い文書だと遅い。Remote-WSL なら起きない。
- Typst ファイルのプレビューは LaTeX Workshop の `latex-workshop-pdf-hook`
  エディタで PDF を開くが、これは公開 API ではない。将来の版で変わっても、
  止まるのは自動で開く部分だけで、`typst watch` は動き続ける。

## ソースからビルドする

```bash
git clone https://github.com/yoshida-kd/octavo.git
cd octavo/vscode-extension
npm ci
npx @vscode/vsce package    # -> octavo-<version>.vsix
```

拡張機能ビューの「…」→「VSIX からのインストール…」で入れるか、
`vscode-extension/` を VS Code で開いて `F5` で Extension Development Host を
起動する。

## ライセンス

MIT

[pdf.js]: https://mozilla.github.io/pdf.js/
[LaTeX Workshop]: https://marketplace.visualstudio.com/items?itemName=James-Yu.latex-workshop
