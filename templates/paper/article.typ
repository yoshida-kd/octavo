// =====================================================================
//  Octavo の論文の体裁（main.typ が #import する）
//
//  octavo build が組むたびに、このファイルの前に `#let octavo-paper = (…)` を書いて
//  build/pdf/<名前>/article.typ に置く。main.typ は表題・著者を渡すだけにして、
//  版面・見出し・表題まわりはここで決める（体裁の手直しが、前からある論文にも届く）。
//  雑誌に合わせて変えるなら、main.typ で `#show: octavo-article.with(…)` のあとに
//  set / show を足すか、このファイルをコピーして直す:
//    octavo template copy paper/article.typ
//
//  使える値（octavo-paper）:
//    lang         "ja" | "en"
//    title / subtitle / author / affiliation / email / date
//                 原稿の冒頭の title・subtitle・author・institute（または affiliation）・email・
//                 date（なければ none。author はいくつもなら並び）。匿名審査（--anonymous）では
//                 anonymous_drop_meta に挙げたもの（既定は著者・所属・メール）が none になる
//    anonymous    匿名審査で組んでいるか
//    serif / sans 本文（明朝）と見出し・太字（ゴシック）のフォントの候補
//    counts       1ページ目に出す分量（none なら出さない）:
//                 (chars, chars-notes, words, words-notes, abstract-chars, abstract-words,
//                  figures, tables)
//    appendix-separate  付録を別の PDF にするか（appendix_separate）
//  付録だけの PDF は `typst compile --input octavo-part=appendix main.typ appendix.pdf`
//  （octavo build が組む）。octavo-part がそれを受ける。
//
//  和文（lang: "ja"）は日本語 LaTeX の標準クラス jsarticle（11pt）、欧文は LaTeX の
//  article（11pt、a4paper）の版面に合わせる。値の出どころ:
//    jsarticle  A4 プリント（handout/handout.typ）と同じ式。\mag 1.095、行送り 16pt×mag、
//               本文の幅は紙幅の 0.76 倍を全角の整数倍に、行数は (紙の高さ×0.83 − …) ÷ 行送り。
//               見出しは \Large・\large（1.4 倍・1.2 倍）のゴシック、本文は明朝
//    article    size11.clo の値（TeX の pt。1in = 72.27pt）: 本文 10.95pt、行送り 13.6pt、
//               本文の幅 360pt、本文の高さ = (紙の高さ − 3.5in) ÷ 行送り の切り捨て × 行送り
//               + \topskip 11pt、上下は \headheight 12pt・\headsep 25pt・\footskip 30pt を
//               含めて中央、段落の字下げ 17pt。見出しは \Large 14.4pt・\large 12pt の太字
//    表題       \maketitle: 表題 \LARGE、著者・日付 \large。要旨は \small で左右を下げる
// =====================================================================

#let octavo-part = sys.inputs.at("octavo-part", default: "body")
#let ja = octavo-paper.lang == "ja"
#let tpt = 1in / 72.27                       // TeX の pt

// ---- 版面 ----------------------------------------------------------------
#let size = if ja { 11pt } else { 10.95 * tpt }
#let geometry = if ja {
  let mag = 1.095
  let ph = 297mm / mag
  let pw = 210mm / mag
  let zw-design = 9.62216pt
  let footskip = 0.03367 * ph
  let topskip = 1.38 * zw-design
  let headsep = footskip - topskip
  let lines = calc.floor((0.83 * ph - 10pt - headsep - footskip - topskip) / 16pt)
  let text-height = lines * 16pt + topskip
  let top-d = (ph - text-height - 10pt - headsep - footskip) / 2 + 20pt + headsep
  let width = calc.floor(calc.floor(0.76 * pw / zw-design) * zw-design * mag / size) * size
  let pitch = 16pt * mag
  let top = top-d * mag + (topskip * mag - 0.88 * size)
  (width: width, pitch: pitch, top: top,
   bottom: 297mm - top - (lines - 1) * pitch - size - 0.5pt,
   footer: footskip * mag - 0.88 * size, indent: 1em)
} else {
  let pitch = 13.6 * tpt
  let topskip = 11 * tpt
  let n = calc.floor((297mm - 3.5in) / pitch)
  let text-height = n * pitch + topskip
  let headheight = 12 * tpt
  let headsep = 25 * tpt
  let footskip = 30 * tpt
  let topmargin = (297mm - 2in - headheight - headsep - text-height - footskip) / 2
  let text-top = 1in + topmargin + headheight + headsep
  let top = text-top + topskip - 0.88 * size
  (width: 360 * tpt, pitch: pitch, top: top,
   bottom: 297mm - top - (n - 1) * pitch - size - 0.5pt,
   footer: footskip - 0.88 * size, indent: 17 * tpt)
}
#let pitch = geometry.pitch

// 分量の行（1ページ目、著者の下）
#let octavo-counts(c) = {
  let n(x) = {
    let s = str(x)
    let out = ""
    for (i, ch) in s.clusters().rev().enumerate() {
      if i > 0 and calc.rem(i, 3) == 0 { out = "," + out }
      out = ch + out
    }
    out
  }
  let parts = if ja {
    ("本文 " + n(c.chars) + "字（脚注を含めて " + n(c.chars-notes) + "字）",
     if c.abstract-chars > 0 { "要旨 " + n(c.abstract-chars) + "字" },
     "図 " + str(c.figures), "表 " + str(c.tables))
  } else {
    (n(c.words) + " words (" + n(c.words-notes) + " with notes)",
     if c.abstract-words > 0 { "abstract " + n(c.abstract-words) + " words" },
     str(c.figures) + if c.figures == 1 { " figure" } else { " figures" },
     str(c.tables) + if c.tables == 1 { " table" } else { " tables" })
  }
  text(size: 0.85em, parts.filter(p => p != none).join(if ja { "　" } else { " · " }))
}

// 要旨: 小さめの字で、左右を下げる（\small と quotation）
#let octavo-abstract(body) = {
  if octavo-part == "appendix" { return }
  // 要旨が空なら見出しも出さない
  if body == [] or body == [ ] { return }
  set par(first-line-indent: (amount: geometry.indent, all: ja))
  align(center, text(font: if ja { octavo-paper.sans } else { octavo-paper.serif }, weight: "bold",
                     size: 0.9 * size,
                     if ja { "要旨" } else { "Abstract" }))
  v(0.3 * pitch)
  pad(x: if ja { 2em } else { 2.5em }, text(size: 0.9 * size, body))
  v(pitch)
}

// main.typ で渡さなかった（auto の）ものは原稿の冒頭から。none なら出さない
#let octavo-article(title: auto, subtitle: auto, author: auto, affiliation: auto, email: auto,
                    date: auto, counts: auto, body) = {
  let pick(v, key) = if v == auto { octavo-paper.at(key, default: none) } else { v }
  let names(v) = if type(v) == array { v.join(if ja { "、" } else { ", " }) } else { v }
  let title = pick(title, "title")
  let subtitle = pick(subtitle, "subtitle")
  let author = names(pick(author, "author"))
  let affiliation = names(pick(affiliation, "affiliation"))
  let email = pick(email, "email")
  let date = pick(date, "date")
  if author == none and octavo-paper.at("anonymous", default: false) {
    author = if ja { [［匿名審査のため著者名を伏せています］] } else { [[Author details removed for blind review]] }
  }
  set document(title: title) if title != none
  set page(paper: "a4",
           margin: (x: (210mm - geometry.width) / 2, top: geometry.top, bottom: geometry.bottom),
           footer-descent: geometry.footer,
           numbering: if octavo-part == "appendix" { (..n) => "A-" + str(n.pos().first()) } else { "1" })
  // 1行の箱を字の大きさちょうどにして、行の間で行送りを決める（和文の行送りが字でぶれない）
  set text(font: octavo-paper.serif, size: size, lang: octavo-paper.lang,
           region: if ja { "JP" } else { "US" }, top-edge: 0.88em, bottom-edge: -0.12em)
  set par(justify: true, leading: pitch - size, spacing: pitch - size,
          first-line-indent: (amount: geometry.indent, all: ja))
  set heading(numbering: "1.1")
  show heading: it => {
    let (scale, above, below) = if ja {
      if it.level == 1 { (1.4, pitch, 0.5 * pitch) } else if it.level == 2 { (1.2, pitch, 0.5 * pitch) }
      else { (1.0, pitch, 0pt) }
    } else {
      if it.level == 1 { (14.4 / 10.95, 3.5 * 0.43 * size, 2.3 * 0.43 * size) }
      else if it.level == 2 { (12 / 10.95, 3.25 * 0.43 * size, 1.5 * 0.43 * size) }
      else { (1.0, 3.25 * 0.43 * size, 1.5 * 0.43 * size) }
    }
    set text(font: if ja { octavo-paper.sans } else { octavo-paper.serif }, weight: "bold",
             size: scale * size)
    set par(first-line-indent: 0em, justify: false)
    block(above: above, below: below + (pitch - size), sticky: true, {
      if it.numbering != none {
        counter(heading).display(it.numbering)
        h(1em)
      }
      it.body
    })
  }
  set list(indent: 1em, body-indent: 0.8em, spacing: pitch - size)
  set enum(indent: 1em, body-indent: 0.8em, spacing: pitch - size)
  // 図・表の上下は \intextsep（12pt）、図とキャプションのあいだは \abovecaptionskip（10pt。jsarticle は 5pt）
  let float-sep = if ja { 12pt * 1.095 } else { 12 * tpt }
  state("octavo-float-sep", none).update(float-sep)
  set figure(gap: if ja { 5pt * 1.095 } else { 10 * tpt })
  show figure: it => if it.kind in (image, table) {
    context if state("octavo-in-figure-group", false).get() { it }
      else { block(above: float-sep, below: float-sep, it) }
  } else { it }
  show figure.caption: set text(size: 0.9em)
  show footnote.entry: set text(size: 0.82em)
  show footnote.entry: set par(first-line-indent: 0em)
  show strong: set text(font: octavo-paper.sans) if ja       // 和文の太字はゴシック
  show raw: set text(font: ("DejaVu Sans Mono",), size: 0.9em)

  // ---- 表題 ----
  {
    set par(first-line-indent: 0em, justify: false)
    align(center, {
      v(2em)
      if octavo-part == "appendix" {
        text(size: 1.2 * size, if ja { "付録" } else { "Online Appendix" })
        v(0.4 * pitch)
      }
      if title != none {
        text(font: if ja { octavo-paper.sans } else { octavo-paper.serif },
             weight: if ja { "bold" } else { "regular" }, size: 1.728 * size, title)
      }
      if subtitle != none and octavo-part != "appendix" {
        v(0.4 * pitch)
        text(size: 1.2 * size, subtitle)
      }
      if octavo-part != "appendix" {
        v(1.5 * pitch)
        for part in (author, affiliation, if email != none { link("mailto:" + email) }, date) {
          if part != none { text(size: 1.2 * size, part); v(0.3 * pitch) }
        }
        let c = if counts == auto { octavo-paper.counts } else { counts }
        if c != none { v(0.5 * pitch); octavo-counts(c) }
      }
      v(1.5 * pitch)
    })
  }
  body
}
