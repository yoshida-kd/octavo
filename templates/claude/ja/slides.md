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
スライド**を作る。`#` が1回分、`##` がスライド1枚。

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
