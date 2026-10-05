// =====================================================================
//  Octavo の Typst 台本（発表者ノート）の体裁 — 素の Typst、パッケージなし
//
//  octavo build --to script が、このファイルの**前に** `#let octavo = (…)`
//  を、**後ろに**本文を書いて1つの完結した .typ にする。使える値は
//  slides/typst-slides.typ とまったく同じ（同じ meta_block を通る）。
//
//  スライド（typst-slides）と対になっている。上に**組んだスライドの PDF のページ**を
//  縮小して貼り、その下に、そのページにあった `::: notes` を #octavo-note[…] として置く。
//  本文は #octavo-script(ページの対応, スライドの PDF)[ノート1][ノート2]… の1つだけ。
//  ページの対応（<name>.notes.json）は octavo build --compile が書く。
//
//  体裁を変えるなら octavo template copy slides/typst-notes.typ でコピーして直す
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

// 図表・式の番号と参照の体裁は、この前に Octavo が埋め込む crossref.typ が持つ
#show figure.caption: set text(size: 0.8em, fill: luma(60))
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

// -- 事例／論点・余談／注意／付記（typst-slides.typ と同じ） ------------
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
#let aside(body) = labeled(if octavo.lang == "ja" { "余談" } else { "Aside" }, body)
#let nb(body) = labeled(if octavo.lang == "ja" { "注意" } else { "Note" }, body)
#let memo(body) = labeled(if octavo.lang == "ja" { "付記" } else { "Memo" }, body)
#let smallgray(body) = text(fill: luma(120), size: 9pt, body)
// 題のないスライド（原稿の `### 題 {.no-title}`）。新しいページにするだけ
#let octavo-untitled-slide() = pagebreak(weak: true)

// -- 見出し -------------------------------------------------------------
// 1ページ＝スライド1枚。節（`#`）は扉を作らず、小さな見出しを置くだけ。
// -- 台本: スライドの各ページと、その下のノート ---------------------------
// data は (count: スライドのページ数, pages: (ノート1のページ, ノート2のページ, …))。
// ノートのないページは絵だけ。絵とノートは同じページに置く（絵だけ前のページに残さない）
#let octavo-script(data, deck, ..notes) = {
  let notes = notes.pos()
  for p in range(1, data.count + 1) {
    let mine = range(notes.len()).filter(i => data.pages.at(i, default: 0) == p)
    block(above: 1.4em, below: 0.5em, breakable: false, sticky: mine.len() > 0, {
      text(size: 8pt, fill: luma(130), [#p])
      v(0.2em, weak: true)
      align(center, box(stroke: 0.5pt + luma(170), image(deck, page: p, width: 85%)))
    })
    for i in mine { octavo-note(notes.at(i)) }
  }
}

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

// -- 頭の1行（表紙はスライドの1ページ目がそのまま下に出る） ----------------
#text(size: 9pt, fill: luma(120),
      (if octavo.title != none { [#octavo.title — ] })
      + if octavo.lang == "ja" { "発表者用の台本。投影する PDF とは別。" }
        else { "Speaker script — not the projected deck." })
