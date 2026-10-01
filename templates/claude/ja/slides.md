<!-- octavo:section slides -->
# スライド・講義ノート

```
slides/<name>.md   発表スライド（**これを書く**）
lectures/<name>.md 講義ノート。A4 プリントと、回ごとのスライドを作る（**これを書く**）
```

## 発表スライド

```bash
octavo build example-talk --compile        # slides/example-talk.md を PDF まで
```

## 講義ノート

講義ノート **1本から** A4 プリント（全回を1冊）と、**`#` 見出しの回ごとに別々の
スライド**を作る。`#` が1回分、`##` が節、`###` がスライド1枚（回の中が `##` だけなら
`##` が1枚）。

```bash
octavo build example-lecture --to typst --compile           # A4 プリントを PDF まで
octavo build example-lecture --to typst-slides --compile    # スライドを回ごとに PDF まで
octavo build example-lecture-03 --to typst-slides           # 3回目だけ
```

- スライドの名前は `<講義ノートの名前>-01`, `-02`, …（`#` の出てきた順）。
  **途中に回を挿し込むと後ろの番号がずれる**ので、名前を固定したい回は見出しに
  id を付ける: `# 第2回 {#second}` → `example-lecture-second`
- 各回のスライドのタイトルスライドは、その回の `#` 見出しがタイトル、講義ノートのタイトルがサブタイトルになる
- 最初の `#` より前はプリントにしか入らない

### 回の区切りを自分で書く

1回が `#` 1つに収まらない（`#` 2つで1回、回が節の途中から始まる）ときは、**回の区切り**を
書く。原稿に1つでもあれば区切りが回を決め、`#` / `##` は節・小節として自由に使える:

```markdown
::: {.session #third title="第3回 政策と政府" date="2026-10-14"}
:::
```

- 区切りから次の区切りの直前までが1回分。`#third` がスライドの名前になる
  （`example-lecture-third`）。`title` / `subtitle` / `date` はその回のタイトルスライドに出る。
  `title` を書かなければ、その回の最初の見出しが題になる
- スライドは見出しで区切る。`::: {.slide}` + `:::` で区切りを足し、見出しに `{.same-slide}` で
  区切りを外し、`{slide-title="…"}` でスライドの題だけ変える
- A4 プリントでは区切りで必ず改ページするので、`octavo extract example-lecture` で
  全体の PDF から**回ごとの PDF** を切り出せる（`build/handouts/example-lecture-third.pdf`。
  ページ番号は全体のまま）。`--session third` で1回分、`--pages 12-19` でページ番号で、
  `--cover` で表紙と目次を付ける

### 事例・論点など、番号の付くブロック

```markdown
::: {.question #question-why title="政府が担い手なのはなぜか"}
なぜ政府が公共政策の中心的な担い手となっているのか。
:::
```

- 種類: `case` 事例・`question` 論点・`aside` 余談（3つで通し番号: 事例1.1、論点1.2）、
  `nb` 注意・`memo` 付記（番号なし）、ほかに `theorem` 定理・`definition` 定義など。
  参照は `@question-why` → 「論点1.2」（ラベルの頭は種類の名前）
- `::: {.restate #question-why}` + `:::` で、同じブロックを元の番号とページへの
  リンク付きで再掲する。`::: {.list-of .question}` + `:::` で一覧（`.titles` を足すと題だけ）。
  **ブロックは1か所に書き、本文を写さない**

### A4 プリントの体裁

講義ノートの冒頭に `first_section: 0` と書くと最初の節（ガイダンス）が 0 になる。
`date: today` は組んだ日になる。表紙は独立した1ページ、目次はローマ数字、本文は 1 から。
組み方は日本語 LaTeX の jsarticle を基準にしている。体裁の全体は
`templates/handout/handout.typ`（変えるなら `octavo template copy handout/handout.typ`）。

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

`##` が1枚（発表スライドの `#` は節、講義ノートの `#` は回の区切り）。
図は枠に収まるように置かれる。
`::: notes`（発表者ノート）は投影するスライドには出ず、台本（`--to typst-notes`）に出る。

分析があれば、授業資料・スライドにも `{{…}}` の数値差し込みが使える（同じ
`assets/values/` を読む）。**論文と同じく、数値を手で書かない。**
