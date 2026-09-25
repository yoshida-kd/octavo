// =====================================================================
//  Octavo の Typst スライドの体裁（パッケージを使わない素の Typst）
//
//  octavo build --to typst-slides は、このファイルの**前に** `#let octavo = (…)`
//  を、**後ろに**本文を書いて、1つの完結した .typ にする。コンパイル時に
//  パッケージを取りに行かないので、ネットワークが無くても組める。
//
//  体裁を変えたいときは、このファイルをプロジェクト（またはユーザー）の
//  templates/ に写して直す。同じ名前で置けば同梱のものより優先される:
//    octavo template copy slides/typst-slides.typ          # このプロジェクトだけ
//    octavo template copy slides/typst-slides.typ --user   # 自分の全プロジェクト
//  使える値:
//
//    octavo.title / subtitle / author / institute / date   題扉（無ければ none）
//    octavo.lang          "ja" | "en"
//    octavo.slide-level   1 なら見出し1つが1枚。2 なら「#」が節の扉、「##」が1枚
//    octavo.aspect        "16-9" | "4-3"（typst_slides_aspect）
//    octavo.numbering     見出しの番号（typst_slides_numbering）。none なら振らない
//    octavo.section-slides 「#」の節を扉のスライドにするか（typst_slides_section_slides）
//    octavo.accent        差し色（typst_slides_accent）。none なら黒のまま
//    octavo.running-header 左上にいまの節（無ければデッキの題）を出すか（typst_slides_running_header）
//    octavo.font          本文フォントの候補（typst_slides_font）
//
//  事例・論点・余談・注意・付記（旧 Beamer プリアンブルの \newtheorem 相当）は、
//  原稿から ```{=typst}``` の素通しブロックで呼ぶ（{{…}}の値埋め込みも普通に効く）:
//
//      ```{=typst}
//      #case[ここに事例の本文]
//      ```
//
//  事例・論点・余談は「事例2.1」のように節ごとにリセットした番号を共有する
//  （3つで通し番号。元の \newtheorem[case]{question}{論点} 相当）。注意・付記は
//  番号を振らない。出典などを小さくグレーで出す #smallgray[出典: …] もある。
// =====================================================================

// 差し色。none のときは黒（本文色）をそのまま使う
#let accent = if octavo.accent == none { black } else { octavo.accent }
// **差し色を設定したときだけ体裁を変える。**書かなければ従来どおりの見た目
// （太字の題、`• ‣ –` の記号、通し番号だけのページ番号）のまま。
// 箇条書きの字下げだけは、差し色と関係なく常に効かせる（入れ子が読めない
// のは好みではなく欠陥だったため）。
#let styled = octavo.accent != none

#set page(
  paper: "presentation-" + octavo.aspect,
  // 走りヘッダを出すときだけ上を広げる
  margin: (x: 1.6cm, bottom: 1.3cm,
           top: if octavo.running-header { 1.5cm } else { 1.3cm }),
  // 左上に、いまいる「#」の節を小さく出す（節の扉を出さない設定でも出る）。
  // 節が無いデッキ（講義ノートを回ごとに分けた1回分など）や最初の節より前は、
  // デッキの題を出す。講義の1回分なら、それがその回の題になる。
  header: context {
    let n = counter(page).get().first()
    if n > 1 and octavo.running-header {
      let secs = if octavo.slide-level > 1 {
        query(selector(heading).before(here()))
          .filter(h => h.level < octavo.slide-level)
      } else { () }
      let label = if secs.len() > 0 { secs.last().body } else { octavo.title }
      if label != none {
        text(size: 12pt, fill: luma(120), label)
      }
    }
  },
  footer: context {
    let n = counter(page).get().first()
    if n > 1 {
      // 差し色を設定したときだけ「いま / 全部」にする
      let label = if styled { [#n / #counter(page).final().first()] } else { str(n) }
      align(right, text(size: 12pt, fill: luma(if styled { 120 } else { 130 }), label))
    }
  },
)
#set text(font: octavo.font, size: 22pt, lang: octavo.lang)
#set par(leading: 0.75em)
// 箇条書きの階層。**indent は常に入れる。**入れないと第2階層の印が第1階層の
// 本文とまったく同じ位置に来てしまい（Typst の list は indent の既定が 0）、
// 入れ子が目で追えない。記号は差し色を設定したときだけ変える。
#set list(spacing: 0.9em, indent: 1.1em, body-indent: 0.5em,
          marker: if styled {
            (text(fill: accent, size: 0.72em)[▶],
             text(fill: accent, size: 0.58em)[▶],
             text(fill: accent, size: 0.5em)[▶])
          } else { ([•], [‣], [–]) })
#set enum(spacing: 0.9em, indent: 1.1em)
// 差し色を設定しないときは black になるので、見た目は従来どおり
#show link: set text(fill: accent)

// 図表・式の番号と参照の体裁は、この前に Octavo が埋め込む crossref.typ が持つ
// （原稿の @fig-… が指す番号と、キャプションの番号が一致する）。スライドでは
// キャプションを小さく出す
#show figure.caption: set text(size: 0.62em, fill: luma(60))

// 見出しの番号（octavo.numbering が none なら振らない）
#set heading(numbering: octavo.numbering)

// 事例／論点／余談（`\newtheorem{case}{事例}[section]` 相当）のカウンタ。
// 節の扉が来るたびに #show heading（下）でリセット／進める。
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
    block(above: 0.8em, below: 0.8em, text(fill: accent)[
      *#label #tag#punct* #body
    ])
  }
}
// 注意／付記（`\newtheorem*` 相当）は番号を振らない
#let labeled(label, body) = {
  let punct = if octavo.lang == "ja" { "．" } else { "." }
  block(above: 0.8em, below: 0.8em, text(fill: accent)[
    *#label#punct* #body
  ])
}
#let case(body) = theorem(if octavo.lang == "ja" { "事例" } else { "Case" }, body)
#let question(body) = theorem(if octavo.lang == "ja" { "論点" } else { "Question" }, body)
#let aside(body) = theorem(if octavo.lang == "ja" { "余談" } else { "Aside" }, body)
#let nb(body) = labeled(if octavo.lang == "ja" { "注意" } else { "Note" }, body)
#let memo(body) = labeled(if octavo.lang == "ja" { "付記" } else { "Memo" }, body)
// 出典などを小さくグレーで（元のプリアンブルの \smallgray 相当）
#let smallgray(body) = text(fill: luma(120), size: 10pt, body)

// 見出しの深さで「節の扉」「1枚の題」「枠の中の小見出し」を分ける
#show heading: it => {
  // 枠の中の小見出しには番号を付けない（1枚の中の見出しなので邪魔になる）
  let num = if it.numbering != none and it.level <= octavo.slide-level {
    counter(heading).display(it.numbering) + h(0.45em)
  } else { [] }
  // 差し色があるときは色で立てる（太字にしない）。無ければ従来どおり太字の黒
  let w = if styled { "regular" } else { "bold" }
  if it.level < octavo.slide-level {
    // 節が変わるたびに事例／論点／余談の番号をリセットする（下の #theorem 参照）。
    // section-slides: false で扉を出さないときも、節としては数える。
    theorem-counter.update(0)
    theorem-section.step()
    // section-slides: false なら扉を出さず、番号を進めるだけ
    if octavo.section-slides {
      pagebreak(weak: true)
      v(1fr)
      align(center, text(size: 34pt, weight: w, fill: accent, num + it.body))
      v(1fr)
      pagebreak(weak: true)
    }
  } else if it.level == octavo.slide-level {
    pagebreak(weak: true)
    block(below: if styled { 0.9em } else { 0.8em },
          text(size: 30pt, weight: w, fill: accent, num + it.body))
  } else {
    block(above: 0.8em, below: 0.5em, text(weight: "bold", fill: accent, it.body))
  }
}

// 題扉
#if octavo.title != none {
  v(1fr)
  align(center, {
    text(size: 34pt, weight: if styled { "regular" } else { "bold" },
         fill: accent, octavo.title)
    if octavo.subtitle != none {
      v(0.3em)
      text(size: 24pt, fill: accent, octavo.subtitle)
    }
    v(1.4em)
    for part in (octavo.author, octavo.institute, octavo.date) {
      if part != none { block(above: 0.4em, text(size: 20pt, part)) }
    }
  })
  v(1fr)
  pagebreak(weak: true)
}
