# Octavo for VS Code

**計量社会科学スターターパック**

[English README is here](README.md)

論文・学会のスライド・授業の配布資料を **1つの Markdown** で書き、組み上がった
PDF を隣に置いて、保存するたびに組み直す。この拡張は
[Octavo](https://github.com/yoshida-kd/octavo) のエディタ側。Octavo は1つの
Markdown から Typst（論文・配布資料・スライド）と Word、TeX があれば LaTeX と
Beamer を作るコマンドラインの道具で、引用は .bib と CSL で揃え、数値・図・表は
手で打たずに Quarto の分析から直接差し込む。

- **PDF のライブプレビュー** — 左に原稿、右に PDF。講義ノートなら3列目に、
  カーソルのある回のスライド（または話す台本）が出る。
- **アクティビティバーの Octavo** — 原稿、よく使う設定、いつもの検査を
  1つのサイドバーに。
- **引用** — `.bib` から `@key` を補完・ホバーし、存在しないキーに波線を引く。
- **分析の値** — 分析が埋める `{{name}}` の補完・ホバー・診断。

## 必要なもの

この拡張は `octavo` コマンドを動かすもので、コマンドそのものは同梱していない。
Linux、macOS、WSL2（Ubuntu）、または Remote-SSH でつなぐサーバーで
（macOS では先に [Homebrew](https://brew.sh) を入れておく）:

```bash
git clone https://github.com/yoshida-kd/octavo.git ~/octavo
bash ~/octavo/setup.sh      # octavo 本体と pandoc・Typst・quarto・フォント
octavo doctor               # まだ足りないものを教えてくれる
```

pandoc（3.1 以上）と Typst（0.12 以上）を自分で入れるなら:

```bash
pipx install octavo-kit     # コマンドは octavo
```

TeX は任意で、LaTeX と Beamer の出力にだけ要る。全体像は
[Octavo の README](https://github.com/yoshida-kd/octavo/blob/HEAD/README.ja.md) を参照。

## 始め方

1. コマンドパレット →「**Octavo: 新しいプロジェクトを作る (init)**」で作り、
   できたフォルダを開く。
2. 「**Octavo: 新しい原稿を足す (new)**」で論文・スライド・講義ノートを足す。
3. 原稿を開き、エディタ右上の PDF のアイコン（「**Octavo: プレビューを開く**」）
   を押す。保存すれば PDF がついてくる。

`octavo.config.py` のあるワークスペースなら、拡張は自動で動き出す。

## できること

- **コマンドパレット**（`Octavo:`）から `build`・`watch`・`check`・`checkbib`・
  `doctor`・`selftest`・`init`・`new`・`analysis run`。
- **サイドバー**: 原稿（クリックで開く。それぞれに PDF と組版のボタン。
  講義ノートは回の一覧が出てその回へ飛べる）、設定（言語・引用の書式・
  スライドの縦横比／差し色／左上の節名／節の扉／見出しの番号・投稿規定の上限。
  クリックで変える）、道具。設定は `octavo config set` で変わり、
  `octavo.config.py` のその1行だけを書き換えてコメントは残し、設定として
  通らない値なら書き換えない。
- **プレビュー**: 保存で組み直し、組み直してもスクロール位置を保ち、失敗は
  握り潰さずパネルに出す。「プレビュー: 3列目に何を出すか…」で、講義ノートの
  3列目をスライド／台本／出さない（2分割）から選ぶ。PDF は同梱の [pdf.js] で
  描くので、実行時に何かを取りに行くことはない。
- **分析（Quarto）**: サイドバーの「分析」に `.qmd` ごとの状態（最新・古い・手動）と
  走らせるボタン。`.qmd` を開いているときはエディタ右上のボタンでその1本を走らせる。
  プレビューは分析を走らせず、古い分析があれば PDF の上の帯で知らせ、そのボタンで
  走らせると終わったあと組み直す。進み具合は通知に、quarto の出力は「出力」パネルに
  出るので、ターミナルを使わずに済む。`.qmd` そのものを書く（R のチャンクの色分け・
  1つずつの実行）には、公式の Quarto 拡張（`quarto.quarto`）を一緒に入れるとよい。
- **引用**: `@` で補完（著者と年つき）、ホバーで文献の全体（`\poscite{key}` も）、
  `Ctrl+Alt+@` で検索して挿入、無いキーに波線、`.bib` 側の問題（年が無い、
  団体名が姓と名に割れている、重複）は `.bib` の上に出す。
- **Typst ファイルのプレビュー**: `.typ` を開いて「Typstファイルを直接watchで
  プレビュー」で `typst watch` を直接回す。論文の手で保守する `main.typ` を
  いじるときに便利。
- **スニペット**: 表・図・所有格の引用・条件つきブロック（`ptable`・`pfigure`・
  `pposcite`・`phandout`・`pslides`・`pnotes` など）。
- **英語と日本語**: VS Code の表示言語に従い、`octavo` コマンドにも同じ言語を
  渡す。

検査はすべて `octavo` コマンド側（`octavo checkbib --json` など）が行い、拡張は
結果を表示するだけ。だから拡張の波線とコマンドの言うことが食い違うことはない。

## macOS・Windows で使う

Octavo は Linux と macOS で動く（Mac ではそのまま `octavo` を呼ぶ。
`octavo` が見つからないと言われたら、`octavo.command` に
`~/.local/bin/octavo` のようなフルパスを書く）。Windows の VS Code からは2通り:

1. **Remote-WSL でフォルダを開く**（おすすめ）。拡張が WSL の中で動き、
   `octavo` を直接呼ぶ。
2. **Windows のフォルダをそのまま開く**。拡張は `wsl.exe` 経由で `octavo` を
   呼び（`octavo.executionMode: "auto"`）、パスを変換する
   （`C:\Users\you\proj` ⇄ `/mnt/c/Users/you/proj`）。WSL 側の `PATH` に
   `octavo` が要る。

## 設定

| キー | 既定 | 意味 |
|---|---|---|
| `octavo.executionMode` | `"auto"` | `"local"` \| `"wsl"` \| `"auto"` |
| `octavo.wslDistro` | `""` | `wsl.exe -d <name>` に渡す。空なら既定のディストリ（`wsl -l -v` で一覧） |
| `octavo.command` | `"octavo"` | 実行するコマンド（フルパスでもよい） |
| `octavo.configPath` | `""` | `octavo.config.py` の場所を明示する |
| `octavo.diagnosticsOnSave` | `true` | 保存のたびに `checkbib` を走らせて波線を更新する |
| `octavo.defaultTargets` | `[]` | 「変換する…」で毎回聞かずに使う形式 |
| `octavo.previewLectureColumn` | `"slides"` | 講義ノートのプレビューの3列目: `"slides"`・`"notes"`（台本）・`"none"` |
| `octavo.typstCommand` | `"typst"` | 「Typstファイルを直接watchでプレビュー」で走らせるコマンド |
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
- `checkbib` は保存のたびに新しいプロセスで走るので、数千件の `.bib` だと少し
  待つことがある。気になるなら `octavo.diagnosticsOnSave` を切り、「文献を
  チェックする」を手で実行する。
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
