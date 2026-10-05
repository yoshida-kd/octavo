// =====================================================================
//  Octavo のポスター（学会のポスター発表）の体裁
// =====================================================================
//  octavo build --to poster は、このファイルの**前に** `#let octavo = (…)` を、
//  **後ろに**本文（マスを並べた #octavo-poster(…)）を書いて、1つの .typ にする。
//  体裁を変えるなら octavo template copy poster/typst-poster.typ でコピーして直す。
//
//  octavo（Octavo が書く値）:
//    title / subtitle / author / institute / event / date   題の帯に出すもの（none なら出さない）
//    logos        ロゴの画像のパス（out_dir から見た相対）の並び。左端に並ぶ
//    qr           QR コードの SVG のパス（none なら出さない）。右端に置く
//    qr-label     QR の下の小さな文字（none なら出さない）
//    width / height   紙の大きさ（mm。横置きなら入れ替えて渡される）
//    scale        A0 を 1 とした大きさの比（文字や余白をこれで伸び縮みさせる）
//    columns      列の数 / rows: 行の高さの比の並び（(1fr, 2fr, 1fr) など）
//    accent       アクセントカラー（none なら黒）
//    font / lang  本文の書体の候補・言語
//
//  本文は `#octavo-poster(octavo-cell(…)[…], …)`。マスは原稿の一番上の段の見出し1つ。
//  octavo-cell の span / rows は結合する列・行の数、at は (列, 行)（1 から）か none。
// =====================================================================

#let s = octavo.scale
#let accent = if octavo.accent != none { octavo.accent } else { black }
#let gap = 12mm * s

#set page(width: octavo.width * 1mm, height: octavo.height * 1mm,
          margin: (x: 25mm * s, y: 22mm * s))
#set text(font: octavo.font, size: 28pt * s, lang: octavo.lang)
#set par(justify: true, leading: 0.6em)
#set list(indent: 0.6em, body-indent: 0.5em)
#set enum(indent: 0.6em, body-indent: 0.5em)
#show link: set text(fill: black)

// マスの題（原稿の一番上の段の見出し）: アクセントカラーの帯
#show heading.where(level: 1): it => block(
  width: 100%, fill: accent, inset: (x: 0.5em, y: 0.3em), below: 0.6em, radius: 4pt * s,
  text(fill: white, weight: "bold", size: 1.25em, it.body))
#show heading.where(level: 2): it => block(above: 0.8em, below: 0.4em,
  text(fill: accent, weight: "bold", size: 1.08em, it.body))
#show heading.where(level: 3): it => block(above: 0.6em, below: 0.3em,
  text(weight: "bold", it.body))
#show figure.caption: set text(size: 0.8em)

// 1つのマス。中身が入りきらなければ右下に印を付け、組んだあとに Octavo が知らせる
#let octavo-cell(span: 1, rows: 1, at: none, name: "", body) = (
  span: span, rows: rows, at: at, name: name, body: body)

#let octavo-box(c) = block(
  width: 100%, height: 100%, inset: 0.5em, stroke: (paint: accent.lighten(55%), thickness: 1.5pt * s),
  radius: 6pt * s, clip: true,
  layout(size => {
    let h = measure(block(width: size.width, c.body)).height
    c.body
    if h > size.height + 0.5pt {
      place(bottom + right, dx: 0.3em, dy: 0.3em,
            box(fill: red, inset: 0.3em, text(fill: white, size: 0.7em, weight: "bold")[
              #if octavo.lang == "ja" [はみ出し] else [overflow]]))
      [#metadata((name: c.name, over: (h - size.height) / 1mm)) <octavo-overflow>]
    }
  }))

#let octavo-title-band() = {
  let side(items) = stack(dir: ltr, spacing: gap * 0.6, ..items)
  let logos = octavo.logos.map(p => image(p, height: 34mm * s))
  let qr = if octavo.qr != none {
    stack(spacing: 0.3em, image(octavo.qr, height: 40mm * s),
          if octavo.qr-label != none { align(center, text(size: 0.6em, octavo.qr-label)) })
  }
  block(width: 100%, below: gap, stroke: (bottom: (paint: accent, thickness: 4pt * s)),
        inset: (bottom: 0.6em),
    grid(columns: (auto, 1fr, auto), column-gutter: gap, align: (left + horizon, center + horizon, right + horizon),
      if logos.len() > 0 { side(logos) },
      {
        if octavo.title != none { text(size: 2.8em, weight: "bold", fill: accent, octavo.title) }
        if octavo.subtitle != none { linebreak(); text(size: 1.4em, octavo.subtitle) }
        if octavo.author != none { v(0.3em); text(size: 1.15em, octavo.author) }
        if octavo.institute != none { linebreak(); text(size: 0.95em, octavo.institute) }
        let foot = (octavo.event, octavo.date).filter(x => x != none)
        if foot.len() > 0 { v(0.2em); text(size: 0.85em, fill: luma(80), foot.join[ · ]) }
      },
      qr))
}

#let octavo-poster(..cells) = {
  octavo-title-band()
  let cs = cells.pos().map(c => {
    let pos = if c.at != none { (x: c.at.at(0) - 1, y: c.at.at(1) - 1) } else { (:) }
    grid.cell(colspan: c.span, rowspan: c.rows, ..pos, octavo-box(c))
  })
  block(width: 100%, height: 1fr,
    grid(columns: (1fr,) * octavo.columns, rows: octavo.rows, gutter: gap, ..cs))
}
