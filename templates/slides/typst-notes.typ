// =====================================================================
//  Octavo の Typst 台本（発表者ノート）の体裁 — 素の Typst、パッケージなし
//
//  octavo build --to typst-notes が、このファイルの**前に** `#let octavo = (…)`
//  を、**後ろに**本文を書いて1つの完結した .typ にする。使える値は
//  slides/typst-slides.typ とまったく同じ（同じ meta_block を通る）。
//
//  スライド（typst-slides）と対になっている。**中身の取捨は同じ**で、違うのは
//  A4 縦1ページ＝スライド1枚で組むことと、スライド側が落とす `::: notes` を
//  #octavo-note[…] として下に置くこと。
//
//  体裁を変えるなら octavo template copy slides/typst-notes.typ で写して直す
//  （typst-slides.typ と同じやり方）。
//
//  事例／論点／余談／注意／付記と #smallgray は typst-slides.typ と同じ名前で
//  同じように使える（原稿は ```{=typst}``` の素通しブロックから呼ぶ）。
//  **同じ名前を両方の体裁で必ず定義すること** — 同じ原稿が両方に通るため。
//  ProjectScaffold::test_slide_and_notes_templates_define_the_same_helpers が
//  片方に足し忘れると落ちる。
// =====================================================================

#let accent = if octavo.accent == none { black } else { octavo.accent }
#let styled = octavo.accent != none

#set page(
  paper: "a4",
  margin: (x: 2cm, top: 2cm, bottom: 1.6cm),
  header: context {
    let n = counter(page).get().first()
    if n > 1 and octavo.title != none {
      text(size: 9pt, fill: luma(130), octavo.title)
    }
  },
  footer: context {
    let n = counter(page).get().first()
    align(right, text(size: 9pt, fill: luma(130),
                      [#n / #counter(page).final().first()]))
  },
)
#set text(font: octavo.font, size: 11pt, lang: octavo.lang)
#set par(leading: 0.68em)
#set list(spacing: 0.6em, indent: 1.1em, body-indent: 0.5em,
          marker: if styled {
            (text(fill: accent, size: 0.72em)[▶],
             text(fill: accent, size: 0.58em)[▶],
             text(fill: accent, size: 0.5em)[▶])
          } else { ([•], [‣], [–]) })
#set enum(spacing: 0.6em, indent: 1.1em)
#show link: set text(fill: accent)

// スライドと同じく、組版側の図表番号は振らない（番号は原稿のキャプションが持つ）
#show figure: set figure(numbering: none, supplement: none)
#show figure.where(kind: table): set figure.caption(position: top)
#set heading(numbering: octavo.numbering)

// -- 発表者ノート -------------------------------------------------------
// `::: notes` がこれになる。紙の上でスライドの中身と見分けがつくように、
// 左に差し色の罫を立てて一段落とす。**投影する PDF には出ない。**
#let octavo-note(body) = block(
  width: 100%, above: 1.1em, inset: (left: 0.8em, y: 0.5em),
  stroke: (left: 2pt + (if styled { accent } else { luma(150) })),
  {
    text(size: 9pt, weight: "bold", fill: luma(110),
         if octavo.lang == "ja" { "ノート" } else { "Notes" })
    v(0.25em)
    set text(size: 10pt)
    body
  },
)

// -- 事例／論点／余談・注意／付記（typst-slides.typ と同じ） ------------
#let theorem-counter = counter("octavo-theorem")
#let theorem-section = counter("octavo-theorem-section")
#let theorem(label, body) = {
  theorem-counter.step()
  context {
    let n = theorem-counter.get().first()
    let tag = if octavo.slide-level > 1 {
      str(theorem-section.get().first()) + "." + str(n)
    } else { str(n) }
    let punct = if octavo.lang == "ja" { "．" } else { "." }
    block(above: 0.7em, below: 0.7em, text(fill: accent)[
      *#label #tag#punct* #body
    ])
  }
}
#let labeled(label, body) = {
  let punct = if octavo.lang == "ja" { "．" } else { "." }
  block(above: 0.7em, below: 0.7em, text(fill: accent)[
    *#label#punct* #body
  ])
}
#let case(body) = theorem(if octavo.lang == "ja" { "事例" } else { "Case" }, body)
#let question(body) = theorem(if octavo.lang == "ja" { "論点" } else { "Question" }, body)
#let aside(body) = theorem(if octavo.lang == "ja" { "余談" } else { "Aside" }, body)
#let nb(body) = labeled(if octavo.lang == "ja" { "注意" } else { "Note" }, body)
#let memo(body) = labeled(if octavo.lang == "ja" { "付記" } else { "Memo" }, body)
#let smallgray(body) = text(fill: luma(120), size: 9pt, body)

// -- 見出し -------------------------------------------------------------
// 1ページ＝スライド1枚。節（`#`）は扉を作らず、小さな見出しを置くだけ。
#show heading: it => {
  let num = if it.numbering != none and it.level <= octavo.slide-level {
    counter(heading).display(it.numbering) + h(0.45em)
  } else { [] }
  if it.level < octavo.slide-level {
    theorem-counter.update(0)
    theorem-section.step()
    pagebreak(weak: true)
    block(below: 1em, text(size: 15pt, weight: "bold", fill: accent,
                           num + it.body))
    line(length: 100%, stroke: 0.5pt + luma(180))
  } else if it.level == octavo.slide-level {
    pagebreak(weak: true)
    block(below: 0.8em, {
      text(size: 16pt, weight: "bold", fill: accent, num + it.body)
      v(0.25em)
      line(length: 100%, stroke: 0.5pt + luma(180))
    })
  } else {
    block(above: 0.7em, below: 0.4em, text(weight: "bold", fill: accent, it.body))
  }
}

// -- 表紙（1ページだけの簡単なもの） ------------------------------------
#if octavo.title != none {
  block(text(size: 20pt, weight: "bold", fill: accent, octavo.title))
  if octavo.subtitle != none {
    block(above: 0.4em, text(size: 14pt, fill: accent, octavo.subtitle))
  }
  v(0.8em)
  for part in (octavo.author, octavo.institute, octavo.date) {
    if part != none { block(above: 0.3em, text(size: 11pt, part)) }
  }
  v(0.8em)
  text(size: 9pt, fill: luma(120),
       if octavo.lang == "ja" { "発表者用の台本。投影する PDF とは別。" }
       else { "Speaker script — not the projected deck." })
}
