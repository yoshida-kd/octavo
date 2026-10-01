<!-- octavo:section analysis -->
# 分析

```
data/raw/         原データ。**読み取り専用**。出所は data/raw/README.md に書く
data/derived/     整形後のデータ。.qmd が作る。手で編集しない
analysis/*.qmd    分析。原稿に出る数値・図・表はすべてここから出す
analysis/octavo.R .qmd 側のヘルパー（ov_value / ov_figure / ov_table）
assets/values/    .qmd が出した数値（<qmd の名前>.json。本文の {{…}} が読む）。手で編集しない
assets/tables/    .qmd が出した表（<name>.typ / .tex / .md）
assets/figures/   .qmd が出した図（<name>.pdf / .png）
requirements.txt  分析に使う Python パッケージの記録（renv.lock と並ぶ環境の記録）
```

## 分析結果の数値を、原稿に手で書かない

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
- `octavo values` で「本文が呼んでいる名前」と「assets/values/ にある値」を突き合わせる。
  **原稿を触ったら必ず1回実行する**
- 図の名前（`ov_figure(p, "trend")`）と表の名前（`ov_table(tab, "summary")`）は
  内容で付ける。番号は入れない。表のラベルは `tbl-<表の名前>` にすると、分析の
  表がそこに差し込まれる。`ov_figure()` は `.pdf` と `.png` の両方を書き出す

## data/raw は読み取り専用

`data/raw/` の中身は書き換えない・上書きしない・整形しない。整形は `.qmd` で
行い、結果は `data/derived/` に書く。原データを直接直すと、どこで何が変わったか
が追えなくなる。

新しいデータを置いたら `data/raw/README.md` に**出所・取得日・利用条件**を書く
（`data/raw/` 自体は `.gitignore` で git に入らないので、この README だけが記録に残る）。

**手で写し取るデータ**（官公庁の PDF や図から数字を拾う、など）も `data/raw/` に置く。
写し取っている間は行を足してよいが、**写し終えたら取得したデータと同じ扱い**にする。
誤りを直すときは出典と照らし合わせ、直したことを `data/raw/README.md` に書く。
手で作ったものは取り直せないので、再配布に問題がなければ `.gitignore` に
`!data/raw/<ファイル>.csv` を足して git に入れる。CSV は VS Code の表の画面でも編集できる。

## 分析を足す・やり直す

1. `analysis/*.qmd` を編集する（データの読み込みは `data/` から）。新しく足すなら
   `octavo new analysis <name>`
2. `octavo analysis run` で実行する（`octavo build` でも古ければ自動で実行される）
3. `octavo values` で数値が出ているか確かめる
4. 原稿から `{{名前}}` で呼ぶ

`.qmd` は `octavo.config.py` の `analysis`（既定は `analysis/*.qmd`）が拾う。重い
データの変更も検知させたいときは `deps` に足す。`octavo build --no-analysis` は `.qmd` を
実行せずいまの `assets/values/` で変換する（重い推定を待ちたくないとき）。

再推定したあとは **`octavo values --diff`** を見る。前に分析を実行したときから
**本文のどの数字が動いたか**が出る。数字が動いたら、それを説明している
言い回し（「わずかに」「約」「有意に」）も直すこと。

## 分析の環境は .venv と renv で持つ（必ず）

**分析は素の R / Python では実行しない。**プロジェクトごとに環境を切り、
使ったパッケージを記録に残す。そうしないと、半年後の自分にも査読者にも
同じ結果が出せない。

- 用意する（clone のあとに戻す）のは `octavo env`: uv で `.venv` と
  `requirements.txt`、renv に knitr / rmarkdown
- Python: `.venv` の中でだけ動かす（`octavo analysis run` は自動で `.venv` を使う。手で
  動かすなら `uv run` か activate）。パッケージは `requirements.txt` に版つきで足してから `octavo env`。
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

分析が長くなったら分けてよい（`octavo new analysis <name>` で足すだけで登録される）。
1本の `.qmd` が `assets/values/<その .qmd の名前>.json` を持ち、本文からは区別なく
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
を付ける。`octavo build` もプレビューもそれを実行せず、古いと知らせるだけになる。
実行するのは `octavo analysis run analysis/01-clean.qmd`（VS Code ならサイドバーの
「分析」のボタン）。設定のグロブはそのままで、`.qmd` の冒頭に `octavo:` と
`  manual: true`（と `  deps: [...]`）を書いてもよい。

**原データをネットから取る処理**（API・ダウンロード）もこの形にする:
`analysis/00-fetch-<取得元>.qmd` に `manual: true`。`data/raw/` にもうあるファイルは上書きせずに
止まるようにし、取得元と取得日を `data/raw/README.md` に書く。

- 同じ名前を2つの `.qmd` が登録すると警告が出て**後が勝つ**。
  `octavo values` の出所欄で確かめる
- **`.qmd` を消したり名前を変えたら、対応する `assets/values/*.json` も消す。**
  残すと本文が古い数値を拾い続ける（`octavo analysis` / `octavo values` が
  「対応する .qmd がない値のファイル」として知らせる）

## データを差し替えたら

```bash
octavo data hash      # ハッシュ値を記録し直す（data/HASHES.json は git に入れる）
octavo data status    # 記録と食い違っていないか
```

`data/` は git に入らないので、`data/HASHES.json` が「そのとき使ったデータ」の
唯一の記録になる。**差し替えた覚えがないのに食い違うなら、原データが書き換えられている。**

## 分析でやらないこと

- **`assets/values/*.json`・`assets/tables/`・`assets/figures/` を手で書き換えない。**
  直したいのは常に `.qmd` のほう
- **原稿に分析結果の数字を直接書かない**（上の「分析結果の数値を、原稿に手で書かない」）
- **`data/raw/` を書き換えない**
- 数値が合わないとき、`{{…}}` を実数に置き換えて「とりあえず通す」ことをしない。
  値がないなら `.qmd` に `ov_value()` を足すのが正しい直し方
- **`data/HASHES.json` を手で書き換えない**。データを差し替えたときだけ
  `octavo data hash` で作り直す
- 困ったら `octavo analysis`（どの `.qmd` が古いか）
