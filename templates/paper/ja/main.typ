// =====================================================================
//  日本語論文の体裁（Typst）
//
//  **このファイルは手で管理する。**octavo new paper <名前> が原稿と同じ
//  docs/<名前>/ に置く。表題・著者・所属・日付は原稿の冒頭（title・author・institute・
//  email・date）から取るので、ここには書かなくてよい。組版のたびに
//  build/pdf/<名前>/ へコピーされるので、直すのは docs/ の側。body.typ /
//  abstract.typ / appendix.typ は Octavo が毎回書くので直接編集しない。
//
//  版面・見出し・表題まわりは article.typ（octavo build が毎回書く。jsarticle に
//  準じた体裁）が決める。雑誌に合わせるなら、下の #show: octavo-article.with(…) の
//  あとに set / show を足す（例: #set page(margin: 25mm)）か、
//  octavo template copy paper/article.typ でコピーして直す。
//
//    octavo build <名前> --compile    # PDF（付録があれば <名前>-appendix.pdf も）
//
//  付録は既定で別の PDF（appendix_separate: True）。本文の続きに付けるなら、
//  octavo.config.py か原稿の冒頭に appendix_separate: false と書く。
//
//  引用は既定で pandoc --citeproc が CSL で組み、書誌一覧も body.typ の末尾に入る
//  （typst_citations: 'native' のときだけ、下の #bibliography(...) を使う）。
//
//  フォントは article.typ が持つ（BIZ UD明朝 + Libertinus Serif。なければ Noto、
//  macOS はヒラギノ、Windows は游明朝）。`typst fonts` で入っているものを確かめる。
// =====================================================================

#import "article.typ": octavo-article, octavo-abstract, octavo-part, octavo-paper
#import "crossref.typ": octavo-crossref, octavo-appendix
// 匿名審査（octavo build --anonymous）では、article.typ が著者・所属・メールを出さない
//（伏せるものは octavo.config.py の anonymous_drop_meta）。ほかにも伏せたいものがあれば
// #if anonymous { … } で分ける（flags.typ は組むたびに書き換わる）
#import "flags.typ": anonymous

// 図・表・式の番号（論文の既定は通し番号: 図1、付録は図A1）と、@fig-… の参照の体裁
#show: octavo-crossref
// 表題・著者などは原稿の冒頭から。ここに書けば、そちらが優先される
#show: octavo-article.with(
  // title: [投稿先に合わせた短い表題],
  // author: [著者名],
  // counts: none,     // 1ページ目の分量（本文の字数・要旨・図表の数）を出さないなら
)

#if octavo-part == "appendix" [
  #show: octavo-appendix
  #include "appendix.typ"
] else [
  #octavo-abstract(include "abstract.typ")
  #include "body.typ"
  // 付録を本文の続きに付けるとき（appendix_separate: false）
  #if not octavo-paper.appendix-separate [
    #pagebreak()
    #show: octavo-appendix
    #include "appendix.typ"
  ]
]

// ---- typst_citations: 'native' のときだけ有効にする -------------------
// #pagebreak()
// #bibliography("../../../literature.bib", style: "chicago-author-date",
//               title: "参考文献")
