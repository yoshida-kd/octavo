// 図「@@NAME@@」。Typst で描く（TeX の頃の TikZ の代わり）。
// octavo build のたびに、このファイルより古ければ assets/figures/@@NAME@@.pdf と .png に組まれる。
// 原稿では普通の図と同じく、キャプションとラベルを原稿の側に書く:
//   ![キャプション](../../assets/figures/@@NAME@@.png){#fig-@@NAME@@}   （スライド・講義ノートからは ../assets/figures/）
// 図は本文の幅いっぱいに置かれる。小さくするなら {#fig-@@NAME@@ width=60%} のように書く。
// Typst の書き方: https://typst.app/docs/

#set page(width: auto, height: auto, margin: 4pt)
#set text(font: @@FONT@@, size: 10pt)

// ---- 部品（パッケージは使わない。自由に書き換えてよい）
// diagram(箱, 矢印) で、箱と、箱から箱への矢印の図を描く。
//   箱:   名前: (x, y, [文字])            x, y は箱の中心。単位は cm で、y は下に向かって増える
//         名前: (x, y, [文字], (stroke: none))   枠なし（fill: … で塗りも変えられる）
//   矢印: ("名前", "名前")                矢印は箱の縁から縁へ引かれる
//         ("名前", "名前", (dash: "dashed"))   破線。(arrow: false) なら矢じりなしの線
// 文字には数式も書ける（[所得 $Y$]）。図の大きさは箱の位置から決まる。
// 何枚もの図で使うなら、figures/_parts.typ（`_` で始まる名前は図として組まれない）に
// 移して、各図で #import "/figures/_parts.typ": * と書く。
// 自由な線や図形は Typst の line / rect / circle / polygon / place でも描ける。

#let diagram(nodes, edges, unit: 1cm, stroke: 0.6pt, gap: 2pt, head: 5pt) = context {
  let n = (:)
  for (key, spec) in nodes {
    let (x, y, body) = spec.slice(0, 3)
    let style = spec.at(3, default: (:))
    let b = box(stroke: style.at("stroke", default: stroke), inset: 6pt, radius: 3pt,
                fill: style.at("fill", default: white), body)
    let s = measure(b)
    n.insert(key, (x: (x * unit).pt(), y: (y * unit).pt(), w: s.width.pt(), h: s.height.pt(), b: b))
  }
  let x0 = calc.min(..n.values().map(v => v.x - v.w / 2))
  let y0 = calc.min(..n.values().map(v => v.y - v.h / 2))
  let x1 = calc.max(..n.values().map(v => v.x + v.w / 2))
  let y1 = calc.max(..n.values().map(v => v.y + v.h / 2))
  let pt(x, y) = ((x - x0) * 1pt, (y - y0) * 1pt)
  let reach(v, dx, dy) = calc.min(
    if dx == 0 { float.inf } else { v.w / 2 / calc.abs(dx) },
    if dy == 0 { float.inf } else { v.h / 2 / calc.abs(dy) })
  box(width: (x1 - x0) * 1pt, height: (y1 - y0) * 1pt, {
    for e in edges {
      let (a, b) = (n.at(e.at(0)), n.at(e.at(1)))
      let style = e.at(2, default: (:))
      let (dx, dy) = (b.x - a.x, b.y - a.y)
      let len = calc.sqrt(dx * dx + dy * dy)
      let (ux, uy) = (dx / len, dy / len)
      let (s, t) = (reach(a, ux, uy) + gap.pt(), reach(b, ux, uy) + gap.pt())
      let (sx, sy) = (a.x + ux * s, a.y + uy * s)
      let (ex, ey) = (b.x - ux * t, b.y - uy * t)
      let h = head.pt()
      let arrow = style.at("arrow", default: true)
      let (lx, ly) = if arrow { (ex - ux * h * 0.8, ey - uy * h * 0.8) } else { (ex, ey) }
      place(line(start: pt(sx, sy), end: pt(lx, ly),
                 stroke: (thickness: stroke, dash: style.at("dash", default: none))))
      if arrow {
        place(polygon(fill: black, pt(ex, ey),
          pt(ex - ux * h - uy * h / 2.4, ey - uy * h + ux * h / 2.4),
          pt(ex - ux * h + uy * h / 2.4, ey - uy * h - ux * h / 2.4)))
      }
    }
    for v in n.values() {
      place(dx: (v.x - v.w / 2 - x0) * 1pt, dy: (v.y - v.h / 2 - y0) * 1pt, v.b)
    }
  })
}

// ---- 図
// octavo:example ここから ─ 書き換えたら、この印の行ごと消す
#diagram(
  (
    x: (0, 0, [原因 $X$]),
    y: (3, 0, [結果 $Y$]),
    z: (1.5, -1.2, [交絡 $Z$]),
  ),
  (("x", "y"), ("z", "x"), ("z", "y")),
)
// octavo:example ここまで
