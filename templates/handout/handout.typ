// =====================================================================
//  Octavo の A4 プリント（講義ノート）の体裁
//
//  octavo build --to typst は、このファイルの**前に** `#let octavo = (…)` を、
//  **後ろに**番号と参照の決まり（typst/crossref.typ）と本文を書いて、1つの完結した
//  .typ にする。体裁を変えたいときは、このファイルをコピーして直す（同じ名前で
//  置けば同梱のものより優先される）:
//    octavo template copy handout/handout.typ          # このプロジェクトだけ
//    octavo template copy handout/handout.typ --user   # 自分の全プロジェクト
//
//  使える値:
//    octavo.title / subtitle / author / institute / date   表紙（なければ none）
//    octavo.lang          "ja" | "en"
//    octavo.font          本文フォントの候補（handout_font）
//    octavo.head-font     見出しのフォントの候補（ゴシック）
//    octavo.bold-font     太字のフォントの候補（和文はゴシック）
//    octavo.fontsize      本文の文字の大きさ（handout_fontsize、既定 11pt）
//    octavo.toc           目次を出すか / octavo.toc-depth 目次の深さ
//    octavo.numbering     見出しに番号を振るか
//    octavo.first-section 最初の節の番号（first_section。ガイダンスを 0 にするなら 0）
//    octavo.pagebreak     "section"（`#` ごとに改ページ）か none。回の区切り
//                         （#octavo-session）では常に改ページする
//
//  和文の組み方は、日本語 LaTeX の標準クラス jsarticle（奥村晴彦氏、jsclasses.dtx）
//  を基準にしている。値の出どころ（jsarticle の 11pt は 10pt の設計を \mag で
//  1.095 倍にしたもの）:
//    行送り     10pt の本文に 16pt（1.6 倍）。11pt（\mag 1.095）なら 17.52pt
//    本文の幅   紙幅の 0.76 倍を超えない全角幅の整数倍
//    本文の行数 (紙の高さ×0.83 − 10pt − headsep − footskip − topskip) ÷ 行送り の切り捨て
//               （footskip は紙の高さの 0.03367 倍、topskip は 1.38 全角、
//               headsep = footskip − topskip。いずれも拡大前の設計の値）
//    上の余白   (紙の高さ − 本文の高さ − 10pt − headsep − footskip) ÷ 2 + headheight(20pt) + headsep
//    段落       字下げ 1 全角、段落の間は空けない（見出しの直後の段落も字下げする）
//    太字       和文はゴシック（\bfseries が和文ではゴシックになるのと同じ）
//  書体は jsarticle と違う: 本文も明朝ではなくゴシック（BIZ UDゴシック）。線の太さが均一で、
//  読みに困難のある読み手にも、画面で読む人にも読みやすい
//    見出し     節は \Large（1.4 倍）、小節は \large（1.2 倍）、小小節は本文の大きさ。
//               どれも前に 1 行、節・小節は後ろに半行。ゴシック（\headfont）
//    箇条書き   1 段目の字下げは 3 全角（leftmargini）
//  jsarticle との違い（Typst で再現しないもの・変えたもの）:
//    - 和文の文字の大きさ。jsarticle の和文は公称の 0.962 倍（11pt で約 10.5pt）だが、
//      Typst は和文も欧文も同じ大きさで組むので 11pt。そのぶん本文の幅は同じまま
//      1 行の字数が少ない（jsarticle 11pt の 42 字に対して 40 字）
//    - 和欧文間の空き（四分）と約物の詰めは Typst の既定（cjk-latin-spacing）に任せる
//    - 句読点（「，．」か「、。」か）は原稿に書いたとおりに出す
//    - 表紙は独立した 1 ページ、目次はローマ数字のページ、本文は 1 から
// =====================================================================

#let ja = octavo.lang == "ja"
#let size = octavo.fontsize
// jsarticle の \mag にあたる倍率（設計は 10pt）。jsarticle のオプションの表の値
// （11pt は 1.1 ではなく 1.095）。表にない大きさは比で
#let mags = ("9pt": 0.913, "10pt": 1.0, "11pt": 1.095, "12pt": 1.2, "14pt": 1.44)
#let mag = mags.at(repr(size), default: size / 10pt)

// ---- 版面（jsarticle の式。設計の値に mag を掛けて実寸にする）------------------
#let ph = 297mm / mag                         // 設計上の紙の高さ
#let pw = 210mm / mag
#let zw-design = 9.62216pt                    // 設計上の全角幅（ltjsarticle の和文 0.962216 倍）
#let footskip = 0.03367 * ph
#let topskip = 1.38 * zw-design
#let headsep = footskip - topskip
#let lines = calc.floor((0.83 * ph - 10pt - headsep - footskip - topskip) / 16pt)
#let text-height = lines * 16pt + topskip
#let top-d = (ph - text-height - 10pt - headsep - footskip) / 2 + 20pt + headsep
// 本文の幅: jsarticle の幅（紙幅の 0.76 倍を全角の整数倍に切り捨て）を、Typst の全角
// （= 文字の大きさ）の整数倍に切り捨てる
#let width = calc.floor(calc.floor(0.76 * pw / zw-design) * zw-design * mag / size) * size
#let pitch = 16pt * mag                       // 行送り（10pt の設計で 16pt）

// 1 行の箱を文字の大きさちょうど（1 全角）にして、行の間（leading）で行送りを決める。
// 欧文の既定（字の上端＝大文字の高さ）のままだと、和文の行送りが字によってぶれる
#set text(font: octavo.font, size: size, lang: octavo.lang,
          region: if ja { "JP" } else { "US" },
          top-edge: 0.88em, bottom-edge: -0.12em)
#set par(justify: true, leading: pitch - size, spacing: pitch - size,
         first-line-indent: (amount: if ja { 1em } else { 1.5em }, all: ja))

#let margin-top = top-d * mag + (topskip * mag - 0.88 * size)
#set page(
  paper: "a4",
  margin: (x: (210mm - width) / 2, top: margin-top,
           bottom: 297mm - margin-top - (lines - 1) * pitch - size - 0.5pt),
  footer-descent: footskip * mag - 0.88 * size,
  numbering: none,
)

// ---- 見出し ------------------------------------------------------------
#let off = octavo.first-section - 1
#set heading(numbering: if octavo.numbering {
  (..n) => {
    let v = n.pos()
    v.at(0) = v.at(0) + off
    numbering("1.1", ..v)
  }
} else { none })
#show heading: it => {
  let (scale, after) = if it.level == 1 { (1.4, 0.5) }
                       else if it.level == 2 { (1.2, 0.5) } else { (1.0, 0) }
  if it.level == 1 and octavo.pagebreak == "section" { pagebreak(weak: true) }
  set text(font: octavo.head-font, weight: "bold", size: scale * size)
  set par(first-line-indent: 0em, justify: false)
  block(above: pitch, below: after * pitch + (pitch - size), sticky: true, {
    if it.numbering != none {
      counter(heading).display(it.numbering)
      h(if ja { 1em } else { 0.75em })
    }
    it.body
  })
}

// ---- 箇条書き・表・そのほか（pandoc の既定テンプレートが持っていた定義も）------------
#set list(indent: 1em, body-indent: 1em, spacing: pitch - size)
#set enum(indent: 1em, body-indent: 0.8em, spacing: pitch - size)
#set terms(hanging-indent: 1.5em)
#set table(inset: 6pt, stroke: none)
#show figure.where(kind: table): set figure.caption(position: top)
#let horizontalRule = line(start: (25%, 0%), end: (75%, 0%))
#let divider = if "divider" in std { divider } else { horizontalRule }
#show raw: set text(font: ("DejaVu Sans Mono",), size: 0.9em)
#show footnote.entry: set par(first-line-indent: 0em)
// 太字はゴシックの太字（jsarticle の \bfseries と同じ）
#show strong: set text(font: octavo.bold-font)

// ---- 回の区切り（原稿の `::: {.session …}`）----------------------------------
// 回の頭は必ず新しいページから（octavo extract がページで切り出すため）。
// 目印（metadata）から、回ごとの開始ページを octavo extract が読む
// 目印に入れる値（context の中で呼ぶ）: 物理ページと、印字されるページ番号
#let octavo-page-mark(key: none, title: none) = {
  let pn = here().page-numbering()
  (key: key, title: title, page: here().page(),
   shown: if pn == none { none } else { numbering(pn, ..counter(page).get()) })
}
#let octavo-session(key, title: none) = {
  pagebreak(weak: true)
  context [#metadata(octavo-page-mark(key: key, title: title)) <octavo-session>]
}

// ---- 表紙と目次 -----------------------------------------------------------
#let names(v) = if v == none { none } else if type(v) == array { v.join(if ja { "、" } else { ", " }) } else { v }
#if octavo.title != none {
  set par(first-line-indent: 0em, justify: false)
  align(center, {
    v(4 * pitch)
    text(font: octavo.head-font, weight: "bold", size: 1.728 * size, octavo.title)
    if octavo.subtitle != none {
      v(0.8 * pitch)
      text(font: octavo.head-font, size: 1.2 * size, octavo.subtitle)
    }
    v(2 * pitch)
    for part in (names(octavo.author), names(octavo.institute), octavo.date) {
      if part != none { text(size: 1.2 * size, part); v(0.5 * pitch) }
    }
  })
}
#if octavo.toc {
  if octavo.title != none { pagebreak() }
  set page(numbering: "i")
  counter(page).update(1)
  outline(depth: octavo.toc-depth, indent: auto)
}
#if octavo.title != none or octavo.toc { pagebreak() }
#set page(numbering: "1")
#counter(page).update(1)
#context [#metadata(octavo-page-mark()) <octavo-body>]
