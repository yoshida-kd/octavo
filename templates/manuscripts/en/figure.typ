// The figure "@@NAME@@", drawn in Typst (where TikZ used to be).
// Every octavo build turns it into assets/figures/@@NAME@@.pdf and .png when those are older than this file.
// The manuscript places it like any other figure, with the caption and label on its side:
//   ![Caption](../../assets/figures/@@NAME@@.png){#fig-@@NAME@@}   (from slides and lecture notes: ../assets/figures/)
// The figure is set to the full text width; for less, write {#fig-@@NAME@@ width=60%}.
// Writing Typst: https://typst.app/docs/

#set page(width: auto, height: auto, margin: 4pt)
#set text(font: @@FONT@@, size: 10pt)

// ---- Parts (no packages; change them as you like)
// diagram(boxes, arrows) draws boxes and arrows from box to box.
//   boxes:  name: (x, y, [text])           x, y is the centre of the box, in cm; y grows downwards
//           name: (x, y, [text], (stroke: none))   no frame (fill: … changes the background)
//   arrows: ("name", "name")               drawn from the edge of one box to the edge of the other
//           ("name", "name", (dash: "dashed"))   dashed; (arrow: false) for a line with no head
// Text may contain math ([Income $Y$]). The size of the figure follows from where the boxes are.
// To share this between figures, move it to figures/_parts.typ (a name starting with `_` is
// not drawn as a figure) and write #import "/figures/_parts.typ": * in each.
// Free-form lines and shapes: Typst's line / rect / circle / polygon / place.

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

// ---- The figure
// octavo:example from here — once you have replaced it, delete these mark lines
#diagram(
  (
    x: (0, 0, [Cause $X$]),
    y: (3, 0, [Effect $Y$]),
    z: (1.5, -1.2, [Confounder $Z$]),
  ),
  (("x", "y"), ("z", "x"), ("z", "y")),
)
// octavo:example to here
