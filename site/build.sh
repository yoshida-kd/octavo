#!/bin/sh
# 手引き（docs/guide*.md）・授業資料の作り方（docs/lectures*.md）・インストール（docs/install*.md）・
# 執筆支援（docs/writing*.md）・リファレンス（docs/reference*.md）・クイックガイド（docs/quickstart*.md）を、
# Pages に出す HTML にする。
#   sh site/build.sh <出力先>   ->  <出力先>/guide/index.html・<出力先>/ja/guide/index.html
#                                  <出力先>/lectures/index.html・<出力先>/ja/lectures/index.html
#                                  <出力先>/quickstart/index.html・<出力先>/ja/quickstart/index.html
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
    -V root="$7" -V home="$8" -V slug="$9" -V "nav_$9=1" -o "$2"
}

page "$repo/docs/guide.md" "$out/guide/index.html" en "Octavo guide" \
  "How to use Octavo in VS Code: projects, writing manuscripts, the analysis, citations, papers, slides and posters." \
  "Contents" "../" "../" guide
page "$repo/docs/guide.ja.md" "$out/ja/guide/index.html" ja "Octavo 手引き" \
  "VS Code での Octavo の使い方。プロジェクト、原稿の書き方、分析、文献、論文、スライドとポスター。" \
  "目次" "../../" "../" guide
page "$repo/docs/lectures.md" "$out/lectures/index.html" en "Making course materials" \
  "How to make lecture notes with Octavo in VS Code: one Markdown file for the A4 handout, a deck per session and per-session handouts." \
  "Contents" "../" "../" lectures
page "$repo/docs/lectures.ja.md" "$out/ja/lectures/index.html" ja "授業資料の作り方" \
  "Octavo で講義ノートを作る手引き。1本の Markdown から A4 プリント・回ごとのスライド・回ごとの配布資料を VS Code で。" \
  "目次" "../../" "../" lectures
page "$repo/docs/writing.md" "$out/writing/index.html" en "Writing support" \
  "Writing rules and a phrase bank for your AI assistant, chosen for each part of a manuscript; paragraph plans and questions for the author." \
  "Contents" "../" "../" writing
page "$repo/docs/writing.ja.md" "$out/ja/writing/index.html" ja "執筆支援" \
  "原稿のいま書いている部分に合わせて、書き方のルールとフレーズバンクを AI アシスタントに渡す。段落の構成表と著者への問い。" \
  "目次" "../../" "../" writing
page "$repo/docs/install.md" "$out/install/index.html" en "Installing Octavo" \
  "Installing Octavo on Linux, macOS and Windows: the VS Code extension sets up R, Python, Quarto, pandoc, Typst and the fonts with one button." \
  "Contents" "../" "../" install
page "$repo/docs/install.ja.md" "$out/ja/install/index.html" ja "Octavo のインストール" \
  "Linux・macOS・Windows への Octavo のインストール。VS Code 拡張機能が、R・Python・Quarto・pandoc・Typst・書体をボタン1つで入れる。" \
  "目次" "../../" "../" install
page "$repo/docs/reference.md" "$out/reference/index.html" en "Octavo reference" \
  "Every command, setting and piece of manuscript syntax in Octavo, written for AI assistants. The same text comes with Octavo: octavo docs." \
  "Contents" "../" "../" reference
page "$repo/docs/reference.ja.md" "$out/ja/reference/index.html" ja "Octavo リファレンス" \
  "Octavo のコマンド・設定・原稿の書き方のすべて。AI アシスタント向け。同じ文章が Octavo に同梱されている（octavo docs）。" \
  "目次" "../../" "../" reference
page "$repo/docs/quickstart.md" "$out/quickstart/index.html" en "Octavo quick guide" \
  "From installing Octavo to your first PDF in six short steps: install, make a project, write, build, check." \
  "Contents" "../" "../" quickstart
page "$repo/docs/quickstart.ja.md" "$out/ja/quickstart/index.html" ja "Octavo クイックガイド" \
  "Octavo を入れてから最初の PDF ができるまでの6つの手順。インストール、プロジェクト作成、執筆、ビルド、チェック。" \
  "目次" "../../" "../" quickstart
