# 執筆支援

> これは執筆支援の手引きの原稿。読むなら **<https://yoshida-kd.github.io/octavo/ja/writing/>** で。 <!-- pages:skip -->

Octavo は、自分が守っている書き方のルールと、信頼できる言い回し（フレーズバンク）を、原稿のいま書いて
いる部分に合わせて AI アシスタントに渡せる。書く前に段落の構成表を置いておき、書いたあとで本文と構成表の
食い違いを見ることもできる。このページは、その準備と使い方を、出てくる順に説明する。説明するのは Octavo
がファイルをどう扱うかで、どんなルールがよいかは書かない。中身は自分で決める。

Octavo はルールの中身を解釈しない。ファイルを選んで並べ、当てはまらないものと外した項目を除き、残りを
アシスタントが読む形に出すだけ。

---

## 1. パック

### 1.1 パックの置き場所

**パック**は Markdown のファイルを入れたフォルダー1つ。書き方のルールは `rules/`、フレーズバンクは
`phrases/` に入れ、`pack.md` を置いてもよい（任意）。パックを探す場所は2つ。

| 場所 | 使う範囲 |
|---|---|
| `~/.config/octavo/writing/<パック>/` | このマシンのすべてのプロジェクト |
| `<プロジェクト>/notes/writing/<パック>/` | そのプロジェクトだけ（プロジェクトと一緒に git に入る） |

両方に同じパックの同じ名前のファイルがあれば、プロジェクトのほうを使う。パックのフォルダーを作らずに
`notes/writing/rules/` と `notes/writing/phrases/` に直接置いたファイルは、`local` という名前のパックに
なり、いつもいちばん後ろに来る。前からのプロジェクトの `writing/` フォルダーも読む（`notes/writing/` の
ほうが勝つ）。

```text
~/.config/octavo/writing/
  general/
    pack.md
    rules/
      sentences.md
      paragraphs.md
    phrases/
      paragraphs.md
  field/
    pack.md
    rules/
      results.md
    phrases/
      introduction.md
      results.md
```

パックを別のリポジトリで管理しているなら、コピーせずにフォルダーをリンクする。

```bash
ln -s ~/projects/my-writing/packs ~/.config/octavo/writing
```

`octavo writing` で、見つかったファイルが、パック・言語・原稿の種類・節と一緒に一覧になる。

```bash
octavo writing
```

### 1.2 pack.md

```markdown
---
title: Empirical papers in my field
extends: general
sections: [puzzle, cases]
---

Rules and phrases for empirical papers. Comes after `general` and wins where they disagree.
```

| キー | 意味 |
|---|---|
| `title` | 一覧とサイドバーに出る名前（書かなければフォルダー名） |
| `extends` | このパックを使うとき、いつもその前に入るパック（並びか、名前1つ） |
| `sections` | 組み込みの節に、このパックが足す節の名前（3.4 を参照） |

本文の最初の段落は、サイドバーに出るパックの説明になる。

---

## 2. ファイルの書き方

### 2.1 ファイルと項目

ファイルは冒頭（フロントマター）から始め、その下の `##` の見出し1つが**項目**1つになる。コードブロックの
中の `##` は見出しにならず、`###` はその上の項目に含まれる。冒頭と最初の `##` の間の文章は、ファイルと
一緒に出る（項目の使い方を書いておくのによい）。

```markdown
---
title: Sentences
lang: en
applies: [paper, lecture]
---

How these rules are meant to be used, if it needs saying.

## One claim per sentence

Rule: Put one claim in a sentence.
Why: The reader need not look for where one claim ends.
Good: Staff numbers fell. How fast they fell differed between municipalities.
Bad: Staff numbers fell, but at different speeds across municipalities, which …
```

| 冒頭のキー | 値 | 書かないとき |
|---|---|---|
| `title` | 一覧に出るファイルの名前 | ファイル名 |
| `lang` | `en`、`ja` | どの言語の原稿でも読む |
| `applies` | `paper`、`slides`、`lecture`、`poster`、`all` | `all` |
| `section` | 節の名前1つか、その並び（3.4 を参照） | いつも読む |

### 2.2 ルール

ルールの項目は、書いたとおりに出る。Octavo が読み取るのは `Flag:` の行だけ（下）。ほかの行は、
アシスタントに伝えてある決まり（AGENTS.md の「各ルールの Rule に従う」）。

| 英語 | 日本語 | |
|---|---|---|
| `Rule:` | `規則:` | すること（いちばん大事な1行） |
| `Why:` | `理由:` | なぜか。ルールが想定していない場合にアシスタントが判断できるように |
| `Good:` | `良い例:` | ルールに沿った例 |
| `Bad:` | `悪い例:` | ルールに反する例 |
| `Flag:` | `検出:` | 正規表現。当たった原稿の行が、読み直す所として一覧に出る |

ほかの行（`Source:` や自分のメモ）も、そのまま出る。

**`Flag:`** は、語が出ている所でしか確かめられないルールのためのもの（"effect"、"significant"、
"Moreover," で始まる文など）。

```markdown
## "Effect" for a causal estimate only

Rule: Write "effect" only where the design identifies one; otherwise "association" or "difference".
Flag: \beffects?\b
Flag: (?i)\bimpacts?\b
```

- 1行に正規表現を1つ。`Flag:` の行は何行書いてもよい。書き方は Python の `re`。大文字と小文字は
  区別する（区別しないなら頭に `(?i)`）。原稿の1行ごとに当てるので、`^` は行の頭（1文1行で
  書いていれば文の頭）。Markdown で書いたとおりに見えるよう、`` ` `` で囲んでもよい。
- `section:` のあるファイルのルールは、その節の行にだけ当てる。
- 見出し、コード、コメント、別行立ての数式、`{{値}}`、引用とラベル（`@key`、`{#sec-x}`）、リンクの先には
  当てない。
- 当たった所は**読み直す所で、誤りではない**。正しい使い方にも当たる。一覧の出し方は 5.3。

### 2.3 フレーズ

フレーズの項目は、場面1つ、または**段落の種類**1つ。そこで使ってよい型を箇条書きで並べる。〈 〉の所は
埋める。`〈A / B〉` は、並べた言葉から1つを選ぶ。

```markdown
---
title: Results
lang: en
applies: [paper]
section: results
---

## The main result

When: The paragraph that reports the main estimate.
Contains: the table or figure; the estimate and its uncertainty; what it means for the hypothesis
Note: Say what the reader should see, then the estimate.
Source: own
- Open: Table 〈2〉 〈presents / reports〉 〈the estimates from X〉.
- Body: The coefficient on 〈X〉 is 〈positive〉 and 〈statistically〉 significant.
- Close: 〈These results〉 provide support for 〈H1〉.
```

| 行 | 日本語 | Octavo がすること |
|---|---|---|
| `When:` | `場面:` | そのまま出す。`--json` の `when` にもなる |
| `Note:` | `注意:` | そのまま出す。`--json` の `note` にもなる |
| `Source:` | `出典:` | そのまま出す。`--json` の `source` にもなる |
| `- Open:` / `- Body:` / `- Close:` | （同じ） | そのまま出す。段落の中の位置つきの型になる（`--json` の `position`） |
| ほかの箇条書き `- ` | | そのまま出す。位置のない型になる |
| `Contains:` | | そのまま出す。`--json` の `contains` にもなる |
| `Repeat: yes` | `繰り返し: yes` | そのまま出す。この種類の段落は続くのがふつうなので、続いても一覧は注を付けない（5.1） |
| ほかの行 | | そのまま出すだけで、読み取らない |

行の名前は行の頭で、`:` か `：` が続くときに当たる。箇条書きの型は、`octavo outline --paragraphs` が
本文の中から探すものになる（5.1）。

項目が**1つの段落の中の文の順**になっているフレーズのファイル（要旨: 問い、根拠、結果、意義）は、
冒頭に `entries: sentences` と書く。その項目は段落の種類ではないので、ある節のフレーズのファイルが
どれもそうなら、一覧はその節の段落に種類を求めない。

---

## 3. 原稿が読むものを選ぶ

### 3.1 パックとその順

選ばなければ、見つかったパックをすべて使う。選ぶときは**一般的なものから順に**並べる。食い違えば後ろの
ものが勝つ。パックの `extends` は、そのパックの前に自動で入る。

プロジェクト全体には `octavo.config.py` に:

```python
CONFIG = {
    'writing': ['general', 'field'],
}
```

その原稿だけには、原稿の冒頭に:

```markdown
---
title: My paper
writing: [field]
---
```

原稿の冒頭の `writing:` は、その原稿ではプロジェクトの設定に代わる。`local` はいつも最後に足される。
サイドバーでは、原稿の「**文章のルール**」→「**パックを選ぶ…**」で、一般的なものから1つずつ選ぶ。

### 3.2 項目を外す

使わないものは `writing_off` に書く。

| 書き方 | 外れるもの |
|---|---|
| `field/results` | パック `field` のファイル `results.md` 全体 |
| `results` | ファイル `results.md`（どのパックのものでも） |
| `field/results#the-main-result` | 項目1つ |
| `results#the-main-result` | その項目（どのパックのものでも） |

```markdown
---
writing_off: [general/sentences#one-claim-per-sentence]
---
```

ほかの設定と違い、`writing_off` はプロジェクトの分と原稿の分を**合わせて**使う。`#` の後ろは、項目の
見出しから作る **slug**：小文字にし、文字と数字以外の続きを `-` 1つにしたもの（`## One claim per
sentence` → `one-claim-per-sentence`。同じ見出しの2つ目は `-2` が付く）。**見出しを変えると slug も
変わり**、外した項目がまた使われる。そのとき `octavo check` は「writing_off に当たる項目がない」と出す。
サイドバーでは、項目を右クリック →「**この原稿では使わない**」。

### 3.3 読まれるファイル

| ファイルに | 読まれるのは |
|---|---|
| `section:` がない | いつも |
| `section: results` | 結果の節を書くときだけ |
| `section:` がなく、`--section-only` を付けた | 読まない（最初の節で読んである） |
| 原稿に合わない `applies:` | その原稿では読まない |
| 原稿と違う `lang:` | その原稿では読まない |

原稿の種類は出力から決まる。論文と回のない配布資料（`word` や `tex` を作るものも）は `paper`、回のある
講義ノートは `lecture`、スライド・台本・Beamer は `slides`、ポスターは `poster`。1つの原稿が
いくつかの種類になることもある。

### 3.4 行の節の決まり方

アシスタントが行を指して聞く（`--file … --line …`）と、Octavo はその行のすぐ上の見出しから浅い見出しへ
さかのぼり、節の名前に当たる最初の見出しを使う。見出しは、ラベルか言葉で節に当たる。1つの見出しの中では、先に出てくる言葉が勝つ（`Results
and robustness` → `results`）。パックが足した節は、組み込みの節より先に見る。`{.appendix}` の付いた
見出しとその後ろ、付録のファイルは `appendix`。

| 節 | その節になる見出しの言葉（見出しのどこかに含まれればよい。大文字・小文字は問わない） |
|---|---|
| `abstract` | abstract, 要旨, 概要 |
| `introduction` | introduction, overview, はじめに, 序論, 問題の所在 |
| `literature` | literature, previous research, prior research, existing research, related work, background, 先行研究 |
| `theory` | theor…, hypothes…, argument, framework, expectation, 理論, 仮説 |
| `design` | data, method, research design, empirical strategy, identification, measure, variable, estimation, sample, case selection, design, データ, 方法, 手法, リサーチデザイン, 分析の枠組み |
| `results` | result, finding, analysis, estimate, evidence, 結果, 分析 |
| `discussion` | discussion, robustness, sensitivity, limitation, mechanism, 考察, 頑健性, 限界 |
| `conclusion` | conclu…, implication, おわりに, 結論, 結び |
| `appendix` | appendix, supplement, 付録 |

パックが足した節（`sections: [puzzle]`）は、その名前の言葉で当たる（`puzzle`。`case-selection` なら
「case selection」）。どの節にも当たらない見出しの下では、`section:` のないファイルだけを読む。

**節の主張を言う見出し**には、これらの言葉が入らない。そのときは、ラベルで節を言う。ラベルは
言葉より先に見る。

```markdown
# Adding Capacity When the Volume of Work Rises {#sec-literature}
```

`{#sec-literature}`、`{#sec-literature-2}`、`{#sec-intro}` のような短い形は、どれもその節になる。
ほかのラベルは、見出しの言葉と同じに読む（`{#sec-data}` → `design`）。行の見出しから節が決まらない
ときは、`octavo writing --file … --line …` がそう知らせる（黙っていると、その節のルールとフレーズが
抜けたままになる）。`--section NAME` で節を手で言える。

### 3.5 読まれるものを見る

```bash
octavo writing --for my-paper
octavo writing --for my-paper --section results --print
octavo writing --for my-paper --section discussion --section-only --print
octavo writing --file docs/my-paper/my-paper.md --line 120 --print
```

1つ目は原稿が使うパックとファイルの一覧。`--print` を付けると重ねた本文が出る。これがアシスタントの
読むもの。`--all` ならすべての節。`--section-only` を付けると、`section:` のないファイル（分量の
大半で、どの節でも同じ）を除くので、別の節に移ったときに、その節で加わる分だけが出る。VS Code では、原稿にカーソルを置いて「**カーソルの所のルールを見る**」
（エディターの右クリック、またはサイドバーの原稿の「**文章のルール**」）。

---

## 4. 段落の構成表

### 4.1 印

パックのフレーズバンクが段落の種類ごとに書いてあれば、節を書く前に構成を決めておける。各段落のすぐ上に
印を1つ置き、その段落の種類と、段落が言う1文の主張を書く。

```markdown
## Results {#sec-results}

<!-- para: field/results#the-main-result | Divisions that changed more were redrawn more often -->
Divisions whose composition of work had shifted more were redrawn more often (@tbl-main).

<!-- para: field/results#the-size-of-the-effect | The effect is about a third of the mean -->

<!-- para: | Robust to dropping the largest ministries -->
```

- 種類はフレーズの項目で、`writing_off` と同じ書き方（`パック/ファイル#slug`、または `ファイル#slug`。
  2つのパックにあれば後ろのもの）。種類も主張も省ける。`<!-- para: | 主張 -->` は、種類をまだ決めて
  いない段落。
- 段落の本文は、印の**すぐ次の行から**。印の次が空行なら、まだ書いていない段落（構成表）。
- **印の前には空行を入れる。** 本文の行のすぐ後に印を書くと、pandoc はそれを上の段落の一部として読み、
  2つの段落がつながる。
- 印はコメントなので、PDF にもスライドにも Word にも出ない。
- **1つの主張を2〜3段落で書くとき**（"First, … / Second, …" を段落に分けた、表のあとに段落が続く）は、
  後ろの段落に `<!-- para: + -->` を付ける。同じ見出しの下の、すぐ上の印の続きになり、その種類を
  引き継ぐ。主張を足してもよい（`<!-- para: + | 主張 -->`）。

```markdown
<!-- para: field/theory#the-mechanism | Shifts in work make the old divisions costly -->
First, a division built for one kind of work ...

<!-- para: + -->
Second, the people who know the old work ...
```

- 印は、引用（`> **H1.** …` のような仮説の表示）や箇条書きの上にも置ける。そのときは、その塊を段落として
  数える。印がなければ、引用や箇条書きは段落に数えない。

### 4.2 段階ごとのコマンド

| 段階 | コマンド | 出るフレーズ |
|---|---|---|
| 節の構成を決める | `octavo writing --for DOC --section S --print` | その節の種類すべて（選ぶため） |
| 別の節に移る | `octavo writing --for DOC --section S --section-only --print` | その節のファイルだけ（もう読んだルールとフレーズは出ない） |
| 段落を1つ書く | 印の行で `octavo writing --file F --line N --print` | その種類の項目だけ |
| 種類を直接言う | `octavo writing --for DOC --kind field/results#the-main-result --print` | その項目 |

種類を指定しても、ルールは指定しないときと同じ。絞られるのはフレーズだけ。`--kind` は何度でも、また
コンマで区切っても書ける。種類は、その原稿が使うフレーズのファイル（選んだパックの、`applies` と
`lang` が合い、外していないもの）から、節を問わず探す。使わないファイルの種類は、警告して除く。

---

## 5. 書いたあと

### 5.1 構成の一覧

```bash
octavo outline my-paper --paragraphs
octavo outline my-paper --paragraphs --contains --lines 60-120
```

で、見出しごとに各段落の種類・主張・本文の最初の文が並ぶ。本文が構成表どおりのことを言っているかを
見比べられる。付く印は次のとおり。

| 印 | 意味 |
|---|---|
| 種類なし | 印のない本文の段落か、種類のない印（フレーズが `entries: sentences` の節では付けない。2.3） |
| 続きの相手がない | 同じ見出しの下で、上に印がない `<!-- para: + -->` |
| 不明な種類 | 選んだパックのどれにもない種類（近い名前を出す） |
| この原稿では使わない種類 | 種類はあるが、そのファイルの `applies` か `lang` が合わないか、外してある |
| 本文がまだない | 下に段落のない印 |
| 印の前に空行が要る | 本文の行のすぐ後にある印 |
| 同じ種類の段落が3つ目 | 注意だけ。1つの見出しの下で同じ種類が3つ続いた（2つ続くのはふつう）。`+` の段落は、続きの相手と合わせて1つに数える。`Repeat: yes` のある種類には付けない |

`--contains` を付けると、各段落の下に、その種類の `Contains:` の行が添えられる。書いたあとで段落と
照らすため（それぞれが入っているか）。Octavo は並べるだけで、照合はしない。`--lines 60-120` は、
その行の範囲の段落だけにする（節ごとに点検するとき）。

1つの見出しの下で同じ型が2回使われていれば、それも知らせる。型が使われたと見なすのは、〈 〉の外の
言葉がすべて、1つの文の中に同じ順で出るとき（`〈A / B〉` はどれか1つ）。大文字で始まる型は文の頭で、
`.` で終わる型は文の終わりで当たる。決まった言葉が2語に満たない型は探さない。比べるのは、その見出しの
節の型（と `section:` のないファイルの型）で、その原稿が使うものだけ。

### 5.2 著者への問い

本文に要る数字や出典が、原稿にも分析にもないとき、アシスタントはごまかして書かず、問いを残すように
指示されている。

```markdown
<!-- ask: the number of ministries in the sample -->
```

`octavo outline … --paragraphs` が問いを行番号つきで並べ、`octavo check` は答えて消すまで「**著者への
問い**」を警告として出す。

### 5.3 読み直す所

```bash
octavo writing --for my-paper --flags
```

ルールの `Flag:`（2.2）に当たった原稿と付録の行を、ルールごとに行番号つきで並べる。1つずつルールと
照らして読む。たいていは問題ない。`octavo check` は件数だけを出し（「**読み直す所**」）、警告には
しない。`--strict` でも止まらない。`--for` の代わりに `--file F` と書けば、そのファイルだけ。

---

## 6. アシスタントに使わせる

- **プロジェクトの AGENTS.md**（`octavo init` が書く）が、アシスタントに次のことを伝えている。文章を
  書いたり直したりする前に `octavo writing --file … --line … --print` を実行してルールに従うこと、
  フレーズバンクは型が合う所でだけ使うこと、印で構成を決め、一覧で確かめること、`ask` のコメントを
  残すこと、パックのファイルは直さないこと。これらの節がまだなかった頃のプロジェクトには、次で入る。

```bash
octavo migrate --rules
```

- **サイドバー**：各原稿の「**文章のルール**」に、その原稿が使うパックと、そのファイル・項目が並ぶ。
  「**パックを選ぶ…**」でその原稿の `writing:` を決め、項目を右クリックして外したり戻したりできる。
  「**カーソルの所のルールを見る**」で、アシスタントがカーソルの所で読むものが見られる。
- パックがあると、`octavo check` に「**文章のルール**」の行が出る。不明なパック名・節名、何にも
  当たらない `writing_off`、正規表現になっていない `Flag:` を知らせる。

---

## 7. うまくいかないとき

| 起きること | わけと、すること |
|---|---|
| `octavo writing` がルールはまだないと言う | Octavo 0.6.8 以前にはパックがない（セットアップで新しくする）。または、パックが `~/.config/octavo/writing/<パック>/` か `notes/writing/<パック>/` にない。リンク先が1段上や下だと何も出ない（パックのフォルダーには `rules/`・`phrases/`・`pack.md` のどれかが要る） |
| ある原稿にファイルが出てこない | `applies:` か `lang:` が原稿に合わない（3.3）。`octavo writing --for DOC --all` で、除いたファイルが `- ` 付きで並ぶ |
| ある節のファイルが読まれない | 行の上の見出しがどの節にも当たらない（3.4）か、節の名前の打ち間違い。`octavo check` が不明な節を知らせる |
| 「文章のルールのパック … がない」「extends に … とあるが、そのパックがない」 | `writing` かパックの `extends` にある名前のフォルダーがない |
| 「writing_off に当たる項目がない」 | 項目の見出しが変わって slug が変わった（3.2）。`octavo writing --for DOC --json` で新しい id をコピーするか、サイドバーから外し直す |
| 「印の前に空行が要る」 | 上の本文と印の間に空行を入れる（4.1） |
| 「不明な種類」 | 種類の打ち間違いか、その種類のパックがこの原稿で選ばれていない |
| 「この原稿では使わない種類」 | 種類のファイルの `applies` / `lang` がこの原稿に合わないか、`writing_off` で外してある |
