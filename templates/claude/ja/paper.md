<!-- octavo:section paper -->
# 論文

```
papers/<name>/    論文。paper.md・main.typ（体裁）、必要なら appendix.md・main.tex（**これを書く**）
```

投稿先ごとの体裁（クラス・余白・タイトル部分・行間）は **`papers/<name>/main.typ`**
（LaTeX なら `main.tex`）に書く。**原稿の隣にある、手で管理するファイル。**Octavo は
これを生成し直さず、組版のたびに `build/` へコピーして使う（生成されるのは
`body.typ` / `abstract.typ` などの本文側）。

## PDF まで出す

```bash
octavo build <name> --compile           # main.typ を組んで PDF にする
octavo build <name> --to docx           # 共著者に渡す Word ファイル
# LaTeX で投稿するとき（TeX が要る。octavo setup --with-tex）
octavo new paper <name> --tex           # 体裁の main.tex を原稿の隣に足す（最初の1回）
octavo build <name> --to latex && cd build/latex/<name> && latexmk -lualatex main.tex
```

## 付録を足す

付録は論文のフォルダの `appendix.md` に書く。同じフォルダにあれば自動で本文と
結びつく（要らなければ消してよい）。

```bash
octavo new paper <name> --appendix   # appendix.md を足す（paper.md は触らない）
octavo build <name> --appendix
```

`papers/<name>/main.typ` の `#show: octavo-appendix` と `#include "appendix.typ"`
のコメントを外す（LaTeX なら `main.tex` の `\appendix` と `\input{appendix}`）。

付録も本文と**同じ扱い**を受ける。`{{…}}` も引用も相互参照もそのまま働き、
`octavo values` `octavo checkbib` `octavo outline` は付録も見る。見出しに
「付録A」とは書かない: 付録の節は組むときに A, B, … と振られ、付録の図・表・式は
A.1 になる。ラベルは本文と付録をまたいで使える（本文から `@tbl-definitions`）。

## 投稿する

投稿用にまとめ直すには:

```bash
octavo build <name>
octavo bundle <name>                 # submission-<name>.zip（パスを平らにして1つに）
octavo bundle <name> --dir --out submission   # zip にせずフォルダで
```

論文が1本だけなら `<name>` は省略できる。`octavo check` は投稿の分量の上限
（`word_limit` など）も見る。

### 匿名審査のとき

```bash
octavo build <name> --anonymous
octavo check --anonymous             # 自己引用の候補も出る
octavo bundle <name> --anonymous     # 著者名の残りを見てからまとめる
```

著者が分かる箇所は原稿側で条件付きブロックに入れておく。

```markdown
::: {.no-anonymous}
謝辞: 科研費…の助成を受けた。
:::
```

- `octavo bundle --anonymous` は、条件分岐で囲っていない著者名を見つけたら
  **失敗する**。消し忘れはここで止まる
- `octavo build --anonymous` を通していない出力はまとめさせない
- 自己引用を Author (年) に伏せるかは雑誌の規定。ツールは**候補を挙げるだけ**

### 共著者から Word が返ってきたら

```bash
octavo review 20260907_draft_tanaka.docx
```

**docx を paper.md に書き戻さないこと。** 戻ってきた docx では `{{n_obs}}` が
既に「1,523」という文字になっていて、書き戻すと数値の出所が原稿に固定される。
`octavo review` は変更履歴とコメントを**読むために**出す。反映は `paper.md` 側で
手で行う。

### 改訂（R&R）のとき

投稿した時点で、その版にタグを付けておく。`octavo release` はタグ（論文の名前入り）を打ち、
投稿した PDF を GitHub Release に残す（`build/` は git に入らないので、現物はここに残す）。

```bash
octavo release example-paper v1-submitted     # タグ example-paper-v1-submitted + PDF
# …（査読・改訂）…
octavo values --diff example-paper-v1-submitted    # 投稿版から数字がどう動いたか
```

### 採択されたら

```bash
octavo bundle --replication          # 再現用パッケージ（投稿用とは中身が別物）
```

原データは既定で入らない。再配布してよいデータか確かめてから
`--with-raw-data` を付ける。

## 論文でやらないこと

- **共著者の docx を paper.md に書き戻さない**（数値の出所が固定される）
- `main.typ` / `main.tex` を `build/` の中で直さない（原稿の隣のものが正本）
