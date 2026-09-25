// =====================================================================
//  日本語論文テンプレート（Typst）
//
//  **このファイルは手で管理する。**octavo new paper <名前> が原稿と同じ
//  papers/<名前>/ に置くので、タイトル・著者・体裁を書き換える。組版のたびに
//  build/typst/<名前>/ へ写されるので、直すのは papers/ の側。body.typ /
//  abstract.typ は Octavo が自動生成するので直接編集しない。
//
//    octavo build <名前> --to typst
//    cd build/typst/<名前> && typst compile --root ../../.. main.typ
//    （--root が無いと ../../../figures を読めない。octavo build --compile なら自動）
//
//  引用の扱いは octavo.config.py の typst_citations で決まる:
//
//    'csl'（既定）   pandoc --citeproc が CSL で解決済みの文字列を body.typ に
//                   書き込む。書誌一覧も body.typ の末尾に入る。
//                   -> このファイルの #bibliography(...) は**使わない**
//    'native'       body.typ に Typst の #cite() が並ぶ。書誌は下の
//                   #bibliography(...) が組む
//
//  **注意: LaTeX と違い CJK フォントは同梱されない。**下の font 指定は
//  コンパイル環境に実際にフォントが入っていることが前提。
//    - `typst fonts` で一覧を確認
//    - Linux なら sudo apt install fonts-morisawa-bizud-mincho fonts-noto-cjk
//      macOS なら brew install --cask font-biz-udmincho
//      （octavo setup が入れる。BIZ UD が無ければ Noto、それも無ければ
//       ヒラギノ（macOS）か游明朝（Windows）に落ちる）
//    - 手元のフォントを使うなら typst compile --root ../../.. --font-path ../../../fonts main.typ
// =====================================================================

#set document(title: "論文タイトル", author: "著者名")
#set page(paper: "a4", margin: 25mm, numbering: "1")
// 欧文は Libertinus Serif、和文は等幅の BIZ UD明朝（無ければ Noto Serif CJK JP、
// 何も足していなければ macOS はヒラギノ明朝、Windows は游明朝）。
// covers: "latin-in-cjk" で英字・数字だけを欧文フォントに回し、「」、。などの
// 約物は和文フォントのまま残す。Octavo の A4 プリントと同じ並び。
#set text(font: ((name: "Libertinus Serif", covers: "latin-in-cjk"),
                 "BIZ UDMincho", "Noto Serif CJK JP", "Hiragino Mincho ProN",
                 "Yu Mincho", "Yu Gothic"),
          lang: "ja", size: 11pt)
#set par(justify: true, leading: 0.9em, first-line-indent: 1em)
#set heading(numbering: "1.1")
#show figure.caption: set text(size: 9pt)

// 図・表・式の番号（節ごとに 2.1）と、@fig-… の参照の体裁。crossref.typ は
// octavo build が毎回書く（振り方は octavo.config.py の crossref_numbering）。
#import "crossref.typ": octavo-crossref, octavo-appendix
#show: octavo-crossref

// 匿名審査の切り替え。octavo build --anonymous のたびに flags.typ が
// 書き換わる（#let anonymous = true / false）。
#import "flags.typ": anonymous

#align(center)[
  #text(size: 16pt, weight: "bold")[論文タイトル]
  #v(0.8em)
  #if anonymous [
    #text(size: 10pt)[［匿名審査のため著者名を伏せています］]
  ] else [
    著者名 \
    #text(size: 10pt)[所属] \
    #text(size: 10pt)[#link("mailto:email@example.ac.jp")]
  ]
]
#v(1.5em)

#heading(numbering: none)[要旨]
#include "abstract.typ"

#pagebreak()
#include "body.typ"

// ---- typst_citations: 'native' のときだけ有効にする -------------------
// #pagebreak()
// #bibliography("../../../literature.bib", style: "chicago-author-date",
//               title: "参考文献")

// 付録があるなら（先に octavo build <名前> --to typst --appendix）。
// octavo-appendix から先は節が A, B, …、図表・式が A.1 になる
// #pagebreak()
// #show: octavo-appendix
// #include "appendix.typ"
