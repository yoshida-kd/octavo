// =====================================================================
//  図・表・式・節の番号と、参照（@fig-… など）の体裁。
//
//  octavo build が組むたびにこれを使う（論文は build/…/crossref.typ にコピーし、
//  main.typ が #import する。A4 プリントとスライドは頭に埋め込む）。
//  自分の体裁にするなら octavo template copy typst/crossref.typ。
//
//    within   true なら節ごと（図2.1・式(2.1)）、false なら通し番号（図1）
//    section  auto  = 最上位の見出しが節
//             none  = 節はない（見出しが1段のスライド）
//             整数  = 節の番号を決め打ち（講義の回ごとのデッキ。プリントと同じ番号にする）
//    count-unnumbered  番号を出さない見出しも節として数えるか（スライド。論文では
//             「要旨」のような番号なしの見出しを数えない）
//
//    offset   節の番号に足す数（first_section が 0 なら -1。ガイダンスが「0」になる）
//    preset   節の数え始め（講義の回ごとのデッキ: 講義ノートでその回より前にある節の数）
//    theorem-kinds  事例・論点などのブロックの番号の組（"case" など。figure の kind）
//
//  式の番号はラベルのある式（$$ … $$ {#eq-…}）にだけ付く。
//
//  事例・論点などのブロック（原稿の `::: {.question #question-why title="…"}`）は
//  #octavo-theorem、再掲・一覧（`::: {.restate #question-why}` / `::: {.list-of …}`）は
//  #octavo-restate になる。番号の付いたブロックは kind が番号の組の figure なので、
//  図・表と同じく節ごとに番号が振られ、@question-why で「論点2.1」と参照できる。
//  見た目（見出し語は太字、本文は立体。LaTeX の \theoremstyle{definition} 相当）は
//  #octavo-theorem-box が決める。
// =====================================================================

// ブロックの見た目。n は番号（文字列）か none、title は題か none
#let octavo-theorem-box(word, n, title, body, lang: "ja") = {
  let ja = lang == "ja"
  block(width: 100%, breakable: true, above: 1.2em, below: 1.2em, {
    set align(left)
    // 見出し語のある最初の段落は字下げしない（2つ目からはする）
    set par(first-line-indent: (amount: 1em, all: false))
    let head = if n == none { strong(word) } else if ja { strong[#word#n] }
               else { strong[#word #n] }
    let tt = if title == none { none } else if ja { [（#title）] } else { [ (#title).] }
    [#head#tt#h(if ja { 1em } else { 0.5em })#body]
  })
}

// 番号のあるブロックは figure（kind が番号の組、supplement が見出し語、caption が題）。
// 番号のないもの（注意・付記）はただの箱
#let octavo-theorem(kind, word, title: none, numbered: true, lang: "ja", body) = {
  if numbered {
    figure(kind: kind, supplement: word, caption: title, body)
  } else {
    octavo-theorem-box(word, none, title, body, lang: lang)
  }
}

// 再掲。target はもとのブロックのラベル（この文書の中にあれば番号を引き、もとの
// ブロックへのリンクにする）。ない（講義のほかの回にある）ときは number の文字をそのまま
// 出す。short なら題とページだけの1行（一覧の目次の形）。再掲そのものにはページを書かない
#let octavo-restate(target: none, word: [], number: none, title: none, short: false,
                    lang: "ja", body) = context {
  let ja = lang == "ja"
  let els = if target == none { () } else { query(target) }
  let head = if els.len() > 0 { ref(target) }
             else if number == none { word }
             else if ja [#word#number] else [#word #number]
  let page = if els.len() > 0 {
    let loc = els.first().location()
    let pn = loc.page-numbering()
    let shown = if pn == none { str(loc.page()) }
                else { numbering(pn, ..counter(page).at(loc)) }
    link(loc, if ja [p.~#shown] else [p.~#shown])
  } else { none }
  if short {
    block(width: 100%, above: 0.6em, below: 0.6em, {
      set par(first-line-indent: 0em, hanging-indent: 2em)
      [#strong(head)#h(1em)#if title != none { title }]
      if page != none { [#box(width: 1fr, repeat[.#h(0.3em)])#page] }
    })
  } else {
    block(width: 100%, breakable: true, above: 1.2em, below: 1.2em, {
      set align(left)
      set par(first-line-indent: (amount: 1em, all: false))
      let tt = if title == none { none } else if ja { [（#title）] } else { [ (#title).] }
      [#strong(head)#tt#h(if ja { 1em } else { 0.5em })#body]
    })
  }
}

#let octavo-appendix-state = state("octavo-appendix", false)
// 節（最上位の見出し）を数える。見出しの番号を出さない文書（スライド）でも進む
// （Typst の counter(heading) は番号のない見出しでは進まない）
#let octavo-section = counter("octavo-section")

// 付録に入るところで #show: octavo-appendix（節が A, B, … になり、図表も A.1 になる）。
// 見出しに番号を振らない文書（番号なしのスライド）は heading-numbering: none で呼ぶ
#let octavo-appendix(heading-numbering: "A.1", body) = {
  octavo-appendix-state.update(true)
  counter(heading).update(0)
  octavo-section.update(0)
  set heading(numbering: heading-numbering)
  body
}

#let octavo-crossref-rules(lang: "ja", within: true, section: auto,
                           count-unnumbered: false, offset: 0, preset: 0,
                           theorem-kinds: (), body) = {
  // 節の番号（その場所で）。なければ none
  let sec-at(loc) = {
    if not within or section == none { return none }
    if type(section) == int { return str(section) }
    let h = octavo-section.at(loc).first()
    if h == 0 { return none }
    if octavo-appendix-state.at(loc) { numbering("A", h) } else { str(h + offset) }
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
  // 事例・論点などのブロック
  show figure: it => {
    if type(it.kind) != str or it.kind not in theorem-kinds { return it }
    let n = if it.numbering == none { none } else { num(it.counter.get().first(), here()) }
    let title = if it.caption == none { none } else { it.caption.body }
    octavo-theorem-box(it.supplement, n, title, it.body, lang: lang)
  }
  // キャプションの頭: 日本語は「図2.1　」、英語は「Figure 2.1. 」
  show figure.caption: it => {
    if it.numbering == none { return it }
    if type(it.kind) == str and it.kind in theorem-kinds { return it }
    context {
      let n = num(it.counter.get().first(), here())
      let word = if it.kind == table { if ja { "表" } else { "Table" } }
                 else { if ja { "図" } else { "Figure" } }
      if ja [#strong[#word#n]#h(1em)#it.body] else [#strong[#word #n.]#h(0.5em)#it.body]
    }
  }

  // 節が変わったら図・表・式の番号を 1 から
  let new-section() = {
    octavo-section.step()
    if within and section == auto {
      counter(figure.where(kind: image)).update(0)
      counter(figure.where(kind: table)).update(0)
      counter(math.equation).update(0)
      for k in theorem-kinds { counter(figure.where(kind: k)).update(0) }
    }
  }
  show heading.where(level: 1): it => {
    if it.numbering == none and not count-unnumbered { return it }
    new-section()
    it
  }
  // スライドで「#」の直後に本文があると、その「#」は1枚のスライド（2段目）になる。
  // 節としては数えるので、その前に目印が置いてある
  show <octavo-section-step>: it => { new-section(); it }

  // ラベルのない別行の数式には番号を付けない（番号を数えた分も戻す）
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
      if type(el.kind) == str and el.kind in theorem-kinds {
        if short { n } else if ja [#el.supplement#n] else [#el.supplement #n]
      } else {
        let word = if el.kind == table { if ja { "表" } else { "Table" } }
                   else { if ja { "図" } else { "Figure" } }
        if short { n } else if ja { word + n } else { word + " " + n }
      }
    } else if el.func() == math.equation {
      let n = "(" + num(counter(math.equation).at(loc).first(), loc) + ")"
      if short { n } else if ja { "式" + n } else { "Equation " + n }
    } else if el.func() == heading {
      let app = octavo-appendix-state.at(loc)
      let nums = if el.numbering != none { counter(heading).at(loc) }
                 else { octavo-section.at(loc) }
      if not app and nums.len() > 0 { nums.at(0) = nums.at(0) + offset }
      let n = numbering(if app { "A.1" } else { "1.1" }, ..nums)
      if short { n }
      else if app { if ja { "付録" + n } else { "Appendix " + n } }
      else { if ja { "第" + n + "節" } else { "Section " + n } }
    } else { return it }
    link(loc, body)
  }
  if preset > 0 { octavo-section.update(preset) }
  body
}
