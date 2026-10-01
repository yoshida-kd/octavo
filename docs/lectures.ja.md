# 講義ノートの作り方

> これは講義ノートの手引きの原稿。読むなら **<https://yoshida-kd.github.io/octavo/ja/lectures/>** で。 <!-- pages:skip -->

講義ノートは、**1本の Markdown から**次のものを作る。

| できるもの | 中身 | 置き場所 |
|---|---|---|
| A4 プリント | 全回を1冊に。表紙・目次つき | `build/typst/<名前>.pdf` |
| 回ごとのスライド | 1回分ずつ。表紙はその回の題と日付 | `build/typst-slides/<名前>-<回>.pdf` |
| 回ごとの配布資料 | A4 プリントを回ごとに切り出したもの。ページ番号は全体のまま | `build/handouts/<名前>-<回>.pdf` |
| 台本（使うときだけ） | スライドを A4 に並べ、下に話すことのメモ | `build/typst-notes/<名前>-<回>.pdf` |

作業はすべて VS Code でできる。この手引きは VS Code を使う前提で書き、コマンドは最後に
[まとめて](#コマンドで使うなら)ある。インストールと、論文・分析など講義ノート以外のことは
[手引き](https://yoshida-kd.github.io/octavo/ja/guide/)を見る。

---

## 始める

1. 左端の Octavo のアイコンでサイドバーを開く。プロジェクトがまだなければ
   「**新しいプロジェクトを作成**」で作る（講義ノートだけなら、選ぶ部品は講義ノートだけでよい）。
2. 「原稿」の「**原稿を追加…**」→「**講義ノート**」→ 名前（例: `public-policy`）と選ぶと、
   `lectures/public-policy.md` ができて開く。
3. エディタの右上の **PDF のボタン**（プレビューを開く）を押す。画面が3つに分かれる:

   | 左 | 中 | 右 |
   |---|---|---|
   | 原稿 | A4 プリント | カーソルのある回のスライド |

   保存するたびに組み直される。右の列は、右上の**画面のボタン**で「スライド」「台本」
   「表示しない」から選べる。
4. サイドバーで講義ノートを開くと、中に**回の一覧**（押すとその回へ飛ぶ）、
   「**回ごとの配布資料を作る**」、「**この文書の設定**」が並ぶ。

---

## 原稿の形

```markdown
---
title: Public Policy
subtitle: Lecture notes
author: Author Name
date: today
---

Text here goes to the handout only (e.g. how the course runs).

# Session 1: What is public policy?

## Introduction

### Today's aims

- Three things to take home

## Who makes policy?

### Government and the market

Text for both the handout and the slides.

#### A smaller point

# Session 2: Government
```

- 冒頭の `---` で囲んだ部分が表紙になる。`date: today` は組んだ日になる。
- 見出しは3段が基本: **`#` が1回分**、**`##` が節**、**`###` がスライド1枚**。`####` から
  下はスライドの中の小見出し（A4 プリントではどれも番号つきの見出し: 1、1.1、1.1.1）。
- `##` の節はスライドの左上に出る（節ごとに扉のスライドを入れる設定もある）。
- 節に分けない回は `##` を飛ばしてよい。回の中が `##` だけなら、`##` が1枚になる。
- 最初の `#` より前に書いたことは、A4 プリントにだけ入る。
- 段落は空行で区切る。箇条書きは `-`、入れ子にするときは**2字下げる**。

---

## 回を分ける

### `#` で分ける（ふつうはこれ）

何も書かなければ、`#` 見出し1つが1回分になる。スライドの名前は出てきた順に
`<名前>-01`, `<名前>-02`, …。途中に回を挿し込んでも名前を変えたくなければ、見出しに id を
付ける:

```markdown
# Session 2: Government {#government}
```

これで2回目のスライドは `<名前>-government` になる。

### 区切りを書いて分ける

1回が `#` 1つに収まらないとき（1回で2つの節を進む、節の途中で回が終わる）は、各回の頭に
**区切り**を書く。区切りが1つでもあれば、`#` は回と関係のないふつうの見出しになる:

```markdown
::: {.session #week3 date="2026-10-14"}
:::

# Session 3: Policy and government

## Who decides?

### The cabinet

## Bureaucracy

### Staff
```

- `#week3` が回の名前（スライドは `<名前>-week3`）。
- `date`（と `subtitle`）はその回のスライドの表紙に出る。題は回の最初の見出しで、
  スライドでは表紙に移る。見出しの段は区切りなしと同じ（`##` 節・`###` 1枚）。
- 区切りに `title="…"` を書くと、それが表紙の題になり、回の最初の見出しも節としてスライドに
  残る。そのときも1枚は `###` のまま。どの段が1枚になるかは講義ノート全体で決まるので、区切りや
  題を足しても変わらない。
- 回の頭は A4 プリントでも必ず新しいページから始まる（回ごとの配布資料はそこで切る）。
- 最初の区切りより前は、A4 プリントにだけ入る（ガイダンスなど）。
- 区切りを書くと、スライドは `#` ではなく区切りごとになる。前に作られたスライド
  （`<名前>-01` など）は次に組むときに消え、`build/` には今のものだけが残る。
- 区切りの後にまだ何もない回（予告として置いた来週の回など）は、スライドを作らない。
- A4 プリントには区切りの `title` と `date` は出ない。見出しは書いたとおりに出る。
  `first_section` が番号を付けるのは回ではなく `#` の見出し。

---

## スライドの区切りと題

ふつうは `###` が1枚。原稿のままでは合わないところだけ、印を付けて直す。どの印も A4 プリントには
影響しない。

| したいこと | 書き方 |
|---|---|
| ここから新しいスライドにする | `::: {.slide}` と `:::` の2行 |
| 新しいスライドに題を付ける | `::: {.slide title="…"}` と `:::` |
| 見出しで改スライドしない | 見出しの後ろに `{.same-slide}` |
| スライドでだけ題を短くする | 見出しの後ろに `{slide-title="…"}` |
| そのスライドに題を出さない（図に場所を回す） | 見出しの後ろに `{.no-title}` |

```markdown
### A long heading for the handout {slide-title="Short title"}

First half of the text.

::: {.slide}
:::

Second half — on a new slide titled "Short title (cont.)".

### A heading that stays on this slide {.same-slide}
```

題を書かずに `::: {.slide}` で区切ると、直前のスライドの題に「（続き）」が付く。区切りで
できるスライドは、そのときの1枚の段（ふつうは `###`）の見出しになる。

**話すことのメモ**は `::: notes` に書く。スライドにもプリントにも出ず、**台本**にだけ出る
（プレビューの右の列で「台本」を選ぶと見える）。台本には投影するスライドがそのまま縮小して
A4 に2枚ずつ並び、それぞれの下にそのスライドに書いたノートが付く:

```markdown
::: notes
Ask the room first; give the answer after two minutes.
:::
```

---

## プリントとスライドで中身を変える

囲んだところを、どちらか一方にだけ出す:

```markdown
::: {.handout-only}
Space for students to write in, longer explanations, footnotes.
:::

::: {.slides-only}
A big figure or one short question.
:::
```

| 印 | 出るところ |
|---|---|
| `.handout-only` | A4 プリントだけ |
| `.slides-only` | スライドと台本だけ |
| `.no-slides` | スライド以外 |

（`.slide-only` は `.slides-only` と同じに読む。）箇条書きの中では囲みの行を項目の本文の桁に
そろえ、**開きの `:::` の前には必ず空行を入れる**。空行がないと pandoc は囲みと読まず、`:::` が
そのまま出る。短い文言なら、行の中で `[…]{.handout-only}` と書ける:

```markdown
- Local government employs most officials.

  ::: {.handout-only}
  - Longer explanation for the handout.
  :::

  ::: {.slides-only}
  - One line for the slide.
  :::

- Grading: [midterm and final]{.handout-only}[see the handout]{.slides-only}.
```

「**投稿前に検査する**」（か `octavo lint`）が、囲みとして読まれない `:::` と、どの出力にも
当たらない印（`.handouts-only` のような綴り違い）を知らせる。知らせがないと、両方から黙って消える。

---

## 事例・論点など、番号の付くブロック

```markdown
::: {.question #question-why title="Why government?"}
Why is government the main actor in public policy?
:::

::: case
No label is needed if nothing refers to it.
:::
```

| 種類 | 見出し | 番号 |
|---|---|---|
| `case` / `question` | 事例 / 論点 | 2つで通し番号（事例1.1、論点1.2、…） |
| `aside` / `nb` / `memo` | 余談 / 注意 / 付記 | なし |
| `definition` / `theorem` / `example` など | 定義 / 定理 / 例 | 別の通し番号 |

- ラベル（`#question-why`）も題（`title`）もなくてよい。`::: case` だけでも番号は付く。
- 番号は節（`#`）ごとに 1 から振り直す。A4 プリントとスライドで同じ番号になる。
- `#question-why` のような**ラベル**を付けておくと、本文で `@question-why` と書いた
  ところが「論点1.2」になり、押すとそのブロックへ飛ぶ。ラベルの頭は種類の名前にする。

**同じブロックをもう一度出す**（復習の回など）。中身は書かず、ラベルだけ指す:

```markdown
::: {.restate #question-why}
:::
```

**一覧にする**（巻末の論点集など）:

```markdown
::: {.list-of .question .case}
:::

::: {.list-of .titles}
:::
```

1つ目は論点と事例を本文ごと並べ、2つ目（`.titles`）は番号のある全ブロックを番号・題・
ページだけの目次にする。

---

## 図・表・文献

論文と同じ書き方。詳しくは手引きの[原稿を書く](https://yoshida-kd.github.io/octavo/ja/guide/#3-原稿を書く)と[文献](https://yoshida-kd.github.io/octavo/ja/guide/#5-文献)。

```markdown
![Spending over time](../assets/figures/trend.png){#fig-trend}

As @fig-trend shows, spending rose. See @yamada2020.
```

- 図は、原稿からの相対パスで貼る（`lectures/` の中から見るので `../`）。スライドでは残りの
  高さに収まるように縮む。
- 図表の出典・注は、そのすぐ後の `::: {.figure-note}` + `:::` に書く。小さい字で同じページに
  置かれ、脚注も付けられる。スライドでは注の分だけ図が縮む。手引きの
  [図](https://yoshida-kd.github.io/octavo/ja/guide/#図)を参照。
- 自分で撮った写真は `figures/` に置き、そこから貼る（`![…](../figures/photo.jpg)`）。
- 手で作る表は、サイドバーの「分析」→「**手で作る表を追加…**」で表の形の画面から作れる。
- 文献は `literature.bib` に入れ、`@キー` で引く。文献を引いた回のスライドには、最後に参考文献の
  スライドが付く。A4 プリントでは巻末にまとめて出る。

---

## URL と脚注

```markdown
See <https://www.e-stat.go.jp/> for the data, or the [statistics portal](https://www.e-stat.go.jp/).

The number of civil servants is small.[^count] A short note can go inline.^[Like this.]

[^count]: Counted in 2024. See <https://www.jinji.go.jp/>.
```

**URL**
- URL は `<` と `>` で囲む（`<https://…>`）。囲まずに書くと、文字として出るだけでリンクにならない。
- 文字にリンクを付けるなら `[文字](URL)`。印刷したプリントでは URL が見えないので、紙で
  読ませたいものは `<URL>` の形にする。
- PDF ではどちらも押すとブラウザーで開く（プレビューでも）。色は本文と同じ黒。

**脚注**
- 本文の脚注を付けるところに `[^名前]`、別の行に `[^名前]: 脚注の本文` と書く。名前は何でも
  よく（`[^1]` でも）、番号は自動で付く。
- 短いものは `^[脚注の本文]` で、その場に書ける。
- A4 プリントではそのページの下、スライドではその1枚の下に出る。
- **脚注の本文は同じ回の中に書く**（段落のすぐ下がよい）。原稿の最後にまとめると、回ごとの
  スライドでは本文が見つからず、`[^名前]` がそのまま出る。

---

## 番号を付けない見出し

見出しに `{.unnumbered}`（短く `{-}`）を付けると、A4 プリントで番号のない見出しになり、
次の番号はその見出しがなかったものとして続く。`.unlisted` も付けると目次にも載らない。
スライドの見た目は変わらない。

```markdown
# Guidance {.unnumbered}

## Next week {-}

## Not in the contents {.unnumbered .unlisted}
```

---

## 付録

見出しに `{.appendix}` を付けると、そこから後ろが付録になる（A, B, …。A4 プリントでは
新しいページから）:

```markdown
# Questions and cases {.appendix}

::: {.list-of .question .case}
:::
```

---

## 体裁を変える

サイドバーで講義ノートを開き、「**この文書の設定**」から選ぶ。選んだ値は原稿の冒頭
（`---` の中）に1行で書き込まれ、その講義ノートにだけ効く。手で書いてもよい。名前は
2列目のとおりに書く（`first-section-number` のような綴り違いは、組むときに知らせが出て、
効かない）。

| 設定 | 冒頭に書く行 | 既定 | 何が変わるか |
|---|---|---|---|
| 最初の節の番号 | `first_section: 0` | 1 | 0 にするとガイダンスが「0」（図は「図0.1」）になる |
| 改ページする位置 | `handout_pagebreak: section` | 回ごと | `section` で `#` ごと、`none` でしない |
| 本文の書体 | `handout_font: …` | BIZ UDゴシック | A4 プリントの本文 |
| 文字の大きさ | `handout_fontsize: 10.5pt` | 11pt | A4 プリントの本文 |
| 日付の書式 | `date_format: "%Y-%m-%d"` | 2026年4月10日 | 表紙の日付 |
| 縦横比 | `typst_slides_aspect: 4-3` | 16:9 | スライド |
| アクセントカラー | `typst_slides_accent: none` | 紺 | スライドの見出しなどの色。`none` で黒一色 |
| 左上の節名 | `typst_slides_running_header: false` | 出す | スライドの左上 |

A4 プリントの組み方は日本語 LaTeX の jsarticle にならう（1行40字、1ページ36行、段落の
頭は1字下げ）。

---

## 配る

- **A4 プリント**・**スライド**: プレビューに出ているものが、そのまま `build/` にある
  （置き場所はこのページの最初の表）。
- **回ごとの配布資料**: 回の区切りを書いた講義ノートなら、保存するたびに裏で作り直される
  （ステータスバーに「配布資料」が回り、✓ で終わり）。手で作るときは、サイドバーの
  「**回ごとの配布資料を作る**」。ページ番号・図や論点の番号は A4 プリント全体と同じ。
- 配る前に、サイドバーの「ツール」→「**投稿前に検査する**」で、指し先のないラベルや
  ない文献を確かめられる。

---

## 早見表

| 書くこと | 書き方 |
|---|---|
| 1回分 | `# 題`（区切りを書くなら `::: {.session #id title="…" date="…"}` + `:::`） |
| 節 | `## 題` |
| スライド1枚 | `### 題` |
| スライドの中の小見出し | `#### 題` |
| 回の名前を固定 | `# 題 {#id}` |
| ここから新しいスライド | `::: {.slide}` + `:::`（題は `title="…"`） |
| 改スライドしない見出し | `### 題 {.same-slide}` |
| 題のないスライド | `### 題 {.no-title}` |
| 番号のない見出し | `## 題 {.unnumbered}` か `{-}` |
| スライドでだけ別の題 | `### 題 {slide-title="短い題"}` |
| 話すことのメモ | `::: notes` … `:::` |
| プリントだけ / スライドだけ | `::: {.handout-only}` / `::: {.slides-only}`、行の中なら `[…]{.slides-only}` |
| 論点（番号つき） | `::: {.question #question-x title="…"}` … `:::` |
| ブロックを指す | `@question-x` |
| 再掲 / 一覧 | `::: {.restate #question-x}` / `::: {.list-of .question}` |
| 図 | `![キャプション](../assets/figures/x.png){#fig-x}`、指すのは `@fig-x` |
| 図表の出典・注 | すぐ後に `::: {.figure-note}` … `:::` |
| 結果でない数値 | `[40%]{.no-lint}` |
| 文献 | `@キー` |
| URL | `<https://…>`、文字に付けるなら `[文字](https://…)` |
| 脚注 | `[^名前]` と `[^名前]: 本文`（同じ回の中に）、短いものは `^[本文]` |
| 付録 | `# 題 {.appendix}` |

---

## コマンドで使うなら

VS Code でしていることは、どれもコマンドでもできる:

```bash
octavo new lecture public-policy                          # lectures/public-policy.md
octavo build public-policy --to typst --compile           # A4 handout
octavo build public-policy --to typst-slides --compile    # one deck per session
octavo build public-policy-week3 --to typst-slides        # one session only
octavo build public-policy-week3 --to typst-notes         # its speaker script
octavo extract public-policy                              # build/handouts/, one PDF per session
octavo extract public-policy --session week3 --cover      # one session, with the cover and contents
octavo check                                              # before handing out
```

コマンドの `octavo build` は回ごとの配布資料を作らない。原稿を直したら `octavo extract` も
実行し直す。
