#!/bin/sh
# 手引き（docs/guide*.md）と講義ノートの手引き（docs/lectures*.md）を、Pages に出す HTML にする。
#   sh site/build.sh <出力先>   ->  <出力先>/guide/index.html・<出力先>/ja/guide/index.html
#                                  <出力先>/lectures/index.html・<出力先>/ja/lectures/index.html
# .github/workflows/pages.yml とテストが使う。原稿は Markdown のまま docs/ に置く。
#
# 見出しの id は GitHub と同じ作り方（gfm_auto_identifiers）にする。手引きの中の
# `#linux` のようなリンクが、GitHub で読んでも Pages で読んでも同じ所へ飛ぶように。
# 日本語の行の途中の改行は空白にしない（east_asian_line_breaks）。
set -eu
out=${1:?usage: sh site/build.sh <output dir>}
here=$(cd "$(dirname "$0")" && pwd)
repo=$(dirname "$here")

# 色分けはしない（ページの色はダークモードに合わせて切り替わるので、pandoc の固定の色が合わない）
if pandoc --help | grep -q -- '--syntax-highlighting'; then
  nohl=--syntax-highlighting=none
else
  nohl=--no-highlight
fi

page() {  # page <原稿> <出力> <言語> <題> <説明> <目次の見出し> <根> <トップ> <フォルダー名>
  mkdir -p "$(dirname "$2")"
  # `<!-- pages:skip -->` の付いた行（GitHub で読む人への「ページで読んで」）は落とす
  grep -v -- '<!-- pages:skip -->' "$1" | pandoc -f markdown+gfm_auto_identifiers+east_asian_line_breaks -t html5 \
    --template "$here/guide.html" --toc --toc-depth=3 --wrap=none "$nohl" \
    -V lang="$3" -V "$3=1" -M pagetitle="$4" -V description="$5" -V toclabel="$6" \
    -V root="$7" -V home="$8" -V slug="$9" -o "$2"
}

page "$repo/docs/guide.md" "$out/guide/index.html" en "Octavo guide" \
  "The full manual for Octavo: installing it on Linux, macOS and Windows, writing manuscripts, the analysis, citations, papers, slides and lecture notes." \
  "Contents" "../" "../" guide
page "$repo/docs/guide.ja.md" "$out/ja/guide/index.html" ja "Octavo 手引き" \
  "Octavo の手引き。Linux・macOS・Windows へのインストール、原稿の書き方、分析、文献、論文、スライドと講義ノート。" \
  "目次" "../../" "../" guide
page "$repo/docs/lectures.md" "$out/lectures/index.html" en "Making lecture notes" \
  "How to make lecture notes with Octavo in VS Code: one Markdown file for the A4 handout, a deck per session and per-session handouts." \
  "Contents" "../" "../" lectures
page "$repo/docs/lectures.ja.md" "$out/ja/lectures/index.html" ja "講義ノートの作り方" \
  "Octavo で講義ノートを作る手引き。1本の Markdown から A4 プリント・回ごとのスライド・回ごとの配布資料を VS Code で。" \
  "目次" "../../" "../" lectures
