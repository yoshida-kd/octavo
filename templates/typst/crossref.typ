// =====================================================================
//  図・表・式・節の番号と、参照（@fig-… など）の体裁。
//
//  octavo build が組むたびにこれを使う（論文は build/…/crossref.typ に写し、
//  main.typ が #import する。A4 プリントとスライドは頭に埋め込む）。
//  自分の体裁にするなら octavo template copy typst/crossref.typ。
//
//    within   true なら節ごと（図2.1・式(2.1)）、false なら通し番号（図1）
//    section  auto  = 最上位の見出しが節
//             none  = 節は無い（見出しが1段のスライド）
//             整数  = 節の番号を決め打ち（講義の回ごとのデッキ。プリントと同じ番号にする）
//    count-unnumbered  番号を出さない見出しも節として数えるか（スライド。論文では
//             「要旨」のような番号なしの見出しを数えない）
//
//  式の番号はラベルのある式（$$ … $$ {#eq-…}）にだけ付く。
// =====================================================================

#let octavo-appendix-state = state("octavo-appendix", false)
// 節（最上位の見出し）を数える。見出しの番号を出さない文書（スライド）でも進む
// （Typst の counter(heading) は番号の無い見出しでは進まない）
#let octavo-section = counter("octavo-section")

// 付録に入るところで #show: octavo-appendix（節が A, B, … になり、図表も A.1 になる）
#let octavo-appendix(body) = {
  octavo-appendix-state.update(true)
  counter(heading).update(0)
  octavo-section.update(0)
  set heading(numbering: "A.1")
  body
}

#let octavo-crossref-rules(lang: "ja", within: true, section: auto,
                           count-unnumbered: false, body) = {
  // 節の番号（その場所で）。無ければ none
  let sec-at(loc) = {
    if not within or section == none { return none }
    if type(section) == int { return str(section) }
    let h = octavo-section.at(loc).first()
    if h == 0 { return none }
    if octavo-appendix-state.at(loc) { numbering("A", h) } else { str(h) }
  }
  let num(n, loc) = {
    let s = sec-at(loc)
    if s == none { str(n) } else { s + "." + str(n) }
  }
  let ja = lang == "ja"

  set figure(numbering: n => context num(n, here()))
  // 表のキャプションは表の上（和文でも英文でも論文の慣行）
  show figure.where(kind: table): set figure.caption(position: top)
  set math.equation(numbering: n => context "(" + num(n, here()) + ")")
  // キャプションの頭: 日本語は「図2.1　」、英語は「Figure 2.1. 」
  show figure.caption: it => {
    if it.numbering == none { return it }
    context {
      let n = num(it.counter.get().first(), here())
      let word = if it.kind == table { if ja { "表" } else { "Table" } }
                 else { if ja { "図" } else { "Figure" } }
      if ja [#strong[#word#n]#h(1em)#it.body] else [#strong[#word #n.]#h(0.5em)#it.body]
    }
  }

  // 節が変わったら図・表・式の番号を 1 から
  show heading.where(level: 1): it => {
    if it.numbering == none and not count-unnumbered { return it }
    octavo-section.step()
    if within and section == auto {
      counter(figure.where(kind: image)).update(0)
      counter(figure.where(kind: table)).update(0)
      counter(math.equation).update(0)
    }
    it
  }

  // ラベルの無い別行の数式には番号を付けない（番号を数えた分も戻す）
  show math.equation: it => {
    if it.block and not it.has("label") and it.numbering != none {
      counter(math.equation).update(v => v - 1)
      math.equation(it.body, block: true, numbering: none)
    } else { it }
  }

  // 参照: 「図2.1」「表2.1」「式(2.1)」「第2節」「付録A」。[-@…] は番号だけ
  show ref: it => {
    let el = it.element
    if el == none { return it }
    let loc = el.location()
    let short = it.supplement == []
    let body = if el.func() == figure {
      let n = num(el.counter.at(loc).first(), loc)
      let word = if el.kind == table { if ja { "表" } else { "Table" } }
                 else { if ja { "図" } else { "Figure" } }
      if short { n } else if ja { word + n } else { word + " " + n }
    } else if el.func() == math.equation {
      let n = "(" + num(counter(math.equation).at(loc).first(), loc) + ")"
      if short { n } else if ja { "式" + n } else { "Equation " + n }
    } else if el.func() == heading {
      let app = octavo-appendix-state.at(loc)
      let nums = if el.numbering != none { counter(heading).at(loc) }
                 else { octavo-section.at(loc) }
      let n = numbering(if app { "A.1" } else { "1.1" }, ..nums)
      if short { n }
      else if app { if ja { "付録" + n } else { "Appendix " + n } }
      else { if ja { "第" + n + "節" } else { "Section " + n } }
    } else { return it }
    link(loc, body)
  }
  body
}
