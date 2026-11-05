# Octavo のインストール

> これはインストールの手引きの原稿。読むなら **<https://yoshida-kd.github.io/octavo/ja/install/>** で。 <!-- pages:skip -->

Octavo 本体のほかに、いくつかのツールを使う: **pandoc**（変換）、**Typst**（PDF に組む）、
**Quarto**・**R**・**Python**（分析）、**書体**、**uv**（`octavo` コマンドを入れる）。
**VS Code の拡張機能が、ボタン1つでこれを全部入れる。**使っている環境を選ぶ:

| 使っているもの | 読むところ |
|---|---|
| Ubuntu などの Debian 系 Linux（手元の PC でも、SSH でつなぐサーバーでも） | [Linux](#1-linux) |
| Mac | [macOS](#2-macos) |
| Windows | [Windows](#3-windows)（WSL を使う方法がおすすめ。Windows で直接も可） |

LaTeX は含まれない（なくてよい。[LaTeX を使うなら](#6-latex-を使うなら)を参照）。
入れ終わったら、[クイックガイド](https://yoshida-kd.github.io/octavo/ja/quickstart/)で
最初の PDF まで進める。

---

## 1. Linux

Octavo は Ubuntu 24.04 で確かめている。Debian やほかの版の Ubuntu でも動く（その
ディストリビューションにない書体は Noto で代わりに組む）。`sudo` を使える利用者で行う。

1. 手元の PC に [VS Code](https://code.visualstudio.com/) を入れる。
   *サーバーで Octavo を動かす場合*は、**Remote - SSH** 拡張機能も入れ、サーバーにつなぐ
   （**Remote-SSH: Connect to Host…**）。以下はすべてサーバーの上で行われる。
2. **Octavo** 拡張機能を入れる（拡張機能の画面で「Octavo」を検索。発行元は yoshida-kd）。
   Remote-SSH でつないでいるときは、**Install in SSH: …** を押してサーバー側に入れる。
3. フォルダーを開く。拡張機能がツールの有無を確かめ、**セットアップ**を勧めてくるので押す。
   ターミナルが開き、パスワード（`sudo` 用）を1回聞いてから全部を入れる。初回は時間が
   かかる（大きいのは R と書体）。
4. 終わると拡張機能がもう一度確かめる。何も言われなければ完了。

R は CRAN の最新版が入り、R のパッケージはコンパイルせずに Posit Package Manager から
出来合いのものが入る。そのなかには、読み込むときにシステムのライブラリを使うものがある
（quanteda.textplots が使う igraph は GLPK を使う）。それもセットアップが入れる。

<details>
<summary><strong>ターミナルで行うなら</strong></summary>

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # uv
source ~/.local/bin/env                           # このターミナルで uv を使えるようにする（新しく開き直してもよい）
uv tool install octavo-kit                        # octavo コマンド
octavo setup                                      # pandoc・Typst・Quarto・書体・R・renv（パスワードを聞かれる）
octavo doctor                                     # すべて ok になっていれば完了
```

</details>

## 2. macOS

**先に Homebrew を入れる。**Octavo はほかのものを Homebrew で入れる。ターミナルを開き、
[brew.sh](https://brew.sh) にある1行を実行する:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

最後に表示される指示に従い（Apple シリコンの Mac では Homebrew を `PATH` に足すよう
言われる）、ターミナルを新しく開き直す。

1. [VS Code](https://code.visualstudio.com/) と **Octavo** 拡張機能を入れる。
2. フォルダーを開き、拡張機能が勧める**セットアップ**を押す。ターミナルが開き、Homebrew で
   全部を入れる（R と Quarto でパスワードを聞かれることがある）。
3. そのあと拡張機能が `octavo` を見つけられないと言う場合は、VS Code を完全に終了して
   （⌘Q）起動し直す（新しいコマンドができる前に起動していたため）。

R は CRAN の配布するものなので、CRAN のパッケージがそのまま入る。

<details>
<summary><strong>ターミナルで行うなら</strong></summary>

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # uv
source ~/.local/bin/env                           # このターミナルで uv を使えるようにする（新しく開き直してもよい）
uv tool install octavo-kit                        # octavo コマンド
octavo setup                                      # pandoc・Typst・Quarto・書体・R・renv（Homebrew で）
octavo doctor                                     # すべて ok になっていれば完了
```

</details>

## 3. Windows

方法は2つある。**WSL を使う方法をすすめる。**Octavo は Linux を第一に作って確かめて
いて、WSL なら Windows の中でそれをそのまま使える。Windows で直接使うのは、WSL が
使えないときだけにする。

### 3.1 WSL を使う（おすすめ）

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
   ここから先は [Linux](#1-linux) と同じ。

### 3.2 Windows で直接使う（WSL なし）

[winget](https://learn.microsoft.com/ja-jp/windows/package-manager/winget/) を使う。
Windows 11 と最近の Windows 10 に入っている（`winget` が見つからなければ、Microsoft Store
から *アプリ インストーラー* を入れる）。管理者の権限は要らない。LaTeX は Windows では
入れない（使うなら MiKTeX を自分で入れる）。

[VS Code](https://code.visualstudio.com/) と **Octavo** 拡張機能を入れ、フォルダーを開いて
**セットアップ**を押す。WSL のない PC では、拡張機能は Windows のツールを使う。終わったら、
新しいコマンドが見えるように VS Code を起動し直す。

<details>
<summary><strong>ターミナルで行うなら</strong></summary>

PowerShell を（管理者でなく）開き、次を実行する:

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

## 4. 動くか確かめる

- Octavo のサイドバーの「**ツール**」→「**環境を診断する**」で、何が入っているかがわかる。
  足りないものには入れ方が付き、「**ツール**」→「**ツールをインストール・更新する**」で直る。
- コマンドパレット（Ctrl+Shift+P、Mac では ⌘⇧P）の「**Octavo: 引用の出力を確認する**」は、
  英語と日本語の文献・表・図・相互参照を含む小さな見本を組み、引用が実際にどう組まれたかを
  表示する。機械ごとに1回実行して、目で確かめる。

## 5. 更新する

拡張機能の画面で拡張機能を更新し（VS Code に任せてもよい）、Octavo のサイドバーの
「**ツール**」→「**ツールをインストール・更新する**」を押す。`octavo` コマンドとツールが、
拡張機能の求める版になる。入っているものは飛ばす。コマンドが拡張機能より古いときは、
拡張機能のほうからも勧めてくる。

## 6. LaTeX を使うなら

ここまでで入るのは Typst で PDF を作る一式で、LaTeX が要るのは `tex` と `beamer` の出力
だけ。Linux では、AI アシスタントに `octavo setup --with-tex` の実行を頼む（自分で実行しても
よい。TeX Live を足す。数 GB）。Mac は [MacTeX](https://www.tug.org/mactex/)、Windows は
[MiKTeX](https://miktex.org/) を入れる。環境の診断は TeX を別に扱い、なくても「不足」には
数えない。

## 7. 表示の言語

拡張機能は VS Code の表示言語に従う。ターミナルでは、メッセージは英語で出て、システムが
日本語なら日本語で出る（`export OCTAVO_LANG=ja` または `en` で選べる）。これはメッセージの
言語だけで、プロジェクトを*何語で書くか*は、プロジェクトを作るときに選ぶ。
