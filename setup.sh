#!/usr/bin/env bash
# =====================================================================
#  octavo を動かすための導入。WSL / Ubuntu サーバ（apt）と macOS（Homebrew）。
#
#    bash setup.sh                ふだん使う一式（pandoc・Typst・quarto・フォント）
#    bash setup.sh --with-tex     TeX Live も入れる（LaTeX / Beamer を使うとき。数 GB）
#    bash setup.sh --minimal      pandoc と日本語フォントだけ
#    bash setup.sh --no-typst     Typst を入れない
#    bash setup.sh --no-quarto    quarto を入れない（分析を .qmd で書かないとき）
#    bash setup.sh --no-cjk-fonts 日本語フォントを入れない
#    bash setup.sh --check        何を入れるか見るだけ（実行しない）
#
#  同じことを何度走らせても平気（入っているものは飛ばす）。
# =====================================================================
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PANDOC_MIN="2.11"          # --citeproc（CSL 引用）に要る
# 動作を確かめた版。入っているものがこれより古ければ GitHub から入れる。
# CI（.github/workflows/tests.yml）もここから版を読むので、上げるときはここだけ直す。
PANDOC_VER="3.11"
TYPST_VER="0.15.1"         # Typst スライドは 0.12 以上が要る
QUARTO_VER="1.10.18"       # 分析（.qmd）を render する

WITH_TEX=0; WITH_TYPST=1; WITH_QUARTO=1; WITH_CJK=1; MINIMAL=0; DRY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --minimal) MINIMAL=1; WITH_TEX=0; WITH_TYPST=0; WITH_QUARTO=0 ;;
    --with-tex) WITH_TEX=1 ;;
    --no-typst) WITH_TYPST=0 ;;
    --no-quarto) WITH_QUARTO=0 ;;
    --no-cjk-fonts) WITH_CJK=0 ;;
    --check|--dry-run) DRY=1 ;;
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
    *) echo "知らない引数: $1"; exit 1 ;;
  esac
  shift
done

say()  { printf '\n\033[1m== %s\033[0m\n' "$*"; }
info() { printf '   %s\n' "$*"; }
run()  { if [ "$DRY" = 1 ]; then info "(実行しない) $*"; else "$@"; fi; }

SUDO=""
if [ "$(id -u)" != 0 ]; then
  command -v sudo >/dev/null && SUDO="sudo" || {
    echo "root でもなく sudo も無い。パッケージを入れられない"; exit 1; }
fi

# $1 >= $2 か（版の比較）。sort -V は古い macOS の sort に無く、macOS の bash は
# 3.2 なので、それで動く書き方にしてある。
ver_ge() {
  local IFS=. i x y
  local -a a b
  a=($1); b=($2)
  for i in 0 1 2 3; do
    x="${a[i]:-0}"; y="${b[i]:-0}"
    x="${x%%[!0-9]*}"; y="${y%%[!0-9]*}"
    x=$((10#${x:-0})); y=$((10#${y:-0}))
    [ "$x" -gt "$y" ] && return 0
    [ "$x" -lt "$y" ] && return 1
  done
  return 0
}

# ---------------------------------------------------------------------
# macOS: Homebrew で入れる。版は Homebrew の最新（Linux で固定している版以上）。
# 入っていても固定の版より古ければ brew upgrade する（Linux 側と同じ考え方）。
# brew は root で動かさないので sudo は使わない。
brew_one() {  # brew_one <formula|--cask> <名前>
  local kind="$1" name="$2"
  if [ "$kind" = --cask ]; then
    if brew list --cask "$name" >/dev/null 2>&1; then info "入っている: $name"; return; fi
    run brew install --cask "$name" || info "入らなかった（後で brew install --cask $name）: $name"
  else
    if brew list --formula "$name" >/dev/null 2>&1; then info "入っている: $name"; return; fi
    run brew install "$name" || info "入らなかった（後で brew install $name）: $name"
  fi
}

brew_tool() {  # brew_tool <コマンド> <固定の版> <formula|--cask> <名前>
  local cmd="$1" want="$2" kind="$3" name="$4" have=""
  have="$("$cmd" --version 2>/dev/null | head -1 | grep -oE '[0-9]+(\.[0-9]+)+' | head -1 || true)"
  if [ -n "$have" ] && ver_ge "$have" "$want"; then
    info "入っている: $cmd $have"
  elif [ -n "$have" ] && brew list $kind "$name" >/dev/null 2>&1; then
    info "いまの $have は動作を確かめた $want より古いので上げる"
    run brew upgrade $kind "$name"
  else
    [ -n "$have" ] && info "いまの $have（Homebrew の外）は $want より古い。Homebrew のものを入れる"
    run brew install $kind "$name"
  fi
}

install_macos() {
  say "環境"
  info "macOS $(sw_vers -productVersion 2>/dev/null || echo '?')  ($(uname -m))"
  command -v brew >/dev/null || {
    echo "Homebrew が無い。https://brew.sh の1行で入れてから、もう一度走らせること"; exit 1; }

  say "pandoc"
  brew_tool pandoc "$PANDOC_VER" "" pandoc
  if [ "$WITH_TYPST" = 1 ]; then
    say "Typst"
    brew_tool typst "$TYPST_VER" "" typst
  fi
  if [ "$WITH_CJK" = 1 ]; then
    # 既定の書体（octavo/backends/typst.py の FONTS）。どれも無くても、
    # macOS に最初からあるヒラギノに落ちるので組版は止まらない。
    say "フォント"
    for c in font-biz-udmincho font-biz-udgothic font-inter \
             font-noto-serif-cjk-jp font-noto-sans-cjk-jp; do
      brew_one --cask "$c"
    done
  fi
  if [ "$WITH_QUARTO" = 1 ]; then
    say "quarto"
    brew_tool quarto "$QUARTO_VER" --cask quarto
  fi
  if [ "$WITH_TEX" = 1 ]; then
    # 日本語（luatexja・ltjsarticle・原ノ味）と Beamer は MacTeX に全部入っている
    say "TeX（MacTeX。数 GB）"
    brew_one --cask mactex-no-gui
    info "入れたらターミナルを開き直す（/Library/TeX/texbin が PATH に入る）"
  fi
}

if [ "$(uname -s)" = Darwin ]; then
  install_macos
  R_HINT="brew install r"
else
R_HINT="sudo apt install r-base"
# ===== ここから Linux（apt）=====

# ---------------------------------------------------------------------
say "環境"
. /etc/os-release 2>/dev/null || true
info "${PRETTY_NAME:-不明な OS}"
grep -qi microsoft /proc/version 2>/dev/null && info "WSL の上で動いている" || true
ARCH="$(dpkg --print-architecture 2>/dev/null || echo amd64)"
info "アーキテクチャ: $ARCH"

command -v apt-get >/dev/null || {
  echo "apt が無い。Debian/Ubuntu 以外は手で入れること"; exit 1; }

# ---------------------------------------------------------------------
say "apt の更新"
run $SUDO apt-get update -qq

# xz-utils: Typst の配布物（.tar.xz）を展開するのに要る。最小構成の Ubuntu には無い
PKGS=(pandoc fontconfig python3 python3-venv curl ca-certificates xz-utils)
if [ "$WITH_CJK" = 1 ]; then
  PKGS+=(fonts-noto-cjk fonts-noto-cjk-extra)
fi
# 既定の書体（octavo/backends/typst.py の FONTS）。和文は等幅の BIZ UD、
# スライドの欧文は Inter。古い Ubuntu には無いパッケージもあるので、
# apt が知っているものだけ足す（無ければ Typst が Noto に落ちるので組版は止まらない）。
OPTIONAL_FONTS=(fonts-inter)
if [ "$WITH_CJK" = 1 ]; then
  OPTIONAL_FONTS+=(fonts-morisawa-bizud-gothic fonts-morisawa-bizud-mincho)
fi
for p in "${OPTIONAL_FONTS[@]}"; do
  if apt-cache show "$p" >/dev/null 2>&1; then
    PKGS+=("$p")
  else
    info "$p は apt に無いので飛ばす（Noto で組む）"
  fi
done
if [ "$MINIMAL" = 0 ]; then
  PKGS+=(librsvg2-bin poppler-utils imagemagick)
fi
if [ "$WITH_TEX" = 1 ]; then
  PKGS+=(texlive-luatex texlive-lang-japanese texlive-latex-recommended
         texlive-latex-extra texlive-fonts-recommended texlive-plain-generic
         latexmk)
fi

say "パッケージを入れる"
info "${PKGS[*]}"
run $SUDO apt-get install -y --no-install-recommends "${PKGS[@]}"

# ---------------------------------------------------------------------
say "pandoc の版を確かめる"
PV="$(pandoc -v 2>/dev/null | head -1 | awk '{print $2}' || echo 0)"
info "いま: $PV"
if ! ver_ge "$PV" "$PANDOC_VER"; then
  if ver_ge "$PV" "$PANDOC_MIN"; then
    info "動作を確かめた $PANDOC_VER より古い（Typst の書き出しや引用の組み方が違うことがある）"
  else
    info "CSL 引用（--citeproc）に $PANDOC_MIN 以上が要る"
  fi
  DEB="pandoc-${PANDOC_VER}-1-${ARCH}.deb"
  URL="https://github.com/jgm/pandoc/releases/download/${PANDOC_VER}/${DEB}"
  info "GitHub から $PANDOC_VER を入れる: $URL"
  if [ "$DRY" = 0 ]; then
    TMP="$(mktemp -d)"
    if curl -fsSL -o "$TMP/$DEB" "$URL"; then
      $SUDO apt-get install -y "$TMP/$DEB" || $SUDO dpkg -i "$TMP/$DEB"
      rm -rf "$TMP"
    else
      info "取得できなかった。手で入れること: https://github.com/jgm/pandoc/releases"
    fi
  fi
  info "いま: $(pandoc -v 2>/dev/null | head -1 | awk '{print $2}')"
fi

# ---------------------------------------------------------------------
if [ "$WITH_TYPST" = 1 ]; then
  say "Typst"
  TV="$(typst --version 2>/dev/null | awk '{print $2}' || true)"
  if [ -n "$TV" ] && ver_ge "$TV" "$TYPST_VER"; then
    info "入っている: $(typst --version)"
  else
    [ -n "$TV" ] && info "いまの $TV は動作を確かめた $TYPST_VER より古いので入れ直す"
    case "$ARCH" in
      amd64) T_ARCH=x86_64-unknown-linux-musl ;;
      arm64) T_ARCH=aarch64-unknown-linux-musl ;;
      *) T_ARCH="" ;;
    esac
    if [ -n "$T_ARCH" ]; then
      URL="https://github.com/typst/typst/releases/download/v${TYPST_VER}/typst-${T_ARCH}.tar.xz"
      info "$URL"
      if [ "$DRY" = 0 ]; then
        TMP="$(mktemp -d)"
        if curl -fsSL "$URL" | tar -xJ -C "$TMP" --strip-components=1; then
          $SUDO install -m 0755 "$TMP/typst" /usr/local/bin/typst
          info "入れた: $(typst --version)"
        else
          info "取得できなかった。https://github.com/typst/typst/releases から手で"
        fi
        rm -rf "$TMP"
      fi
    else
      info "このアーキテクチャ用の配布が分からない。手で入れること"
    fi
  fi
fi

# ---------------------------------------------------------------------
say "フォントの登録"
run fc-cache -f >/dev/null
if [ "$DRY" = 0 ]; then
  N=$(fc-list :lang=ja family 2>/dev/null | wc -l)
  info "日本語フォント $N 件"
  command -v typst >/dev/null && \
    info "Typst から見える CJK: $(typst fonts 2>/dev/null | grep -ci cjk || echo 0) 件"
fi

# ---------------------------------------------------------------------
# 分析（analysis/*.qmd）を render するのに要る。原稿の数値・図・表はここから来るので、
# 既定で入れる（要らなければ --no-quarto）。
if [ "$WITH_QUARTO" = 1 ]; then
  say "quarto"
  QV="$(quarto --version 2>/dev/null | head -1 || true)"
  if [ -n "$QV" ] && ver_ge "$QV" "$QUARTO_VER"; then
    info "入っている: $QV"
  else
    [ -n "$QV" ] && info "いまの $QV は動作を確かめた $QUARTO_VER より古いので入れ直す"
    DEB="quarto-${QUARTO_VER}-linux-${ARCH}.deb"
    URL="https://github.com/quarto-dev/quarto-cli/releases/download/v${QUARTO_VER}/${DEB}"
    info "$URL"
    if [ "$DRY" = 0 ]; then
      TMP="$(mktemp -d)"
      if curl -fsSL -o "$TMP/$DEB" "$URL"; then
        $SUDO apt-get install -y "$TMP/$DEB" || $SUDO dpkg -i "$TMP/$DEB"
        info "入れた: $(quarto --version 2>/dev/null | head -1)"
      else
        info "取得できなかった。https://quarto.org/docs/get-started/ から手で"
      fi
      rm -rf "$TMP"
    fi
  fi
fi

fi
# ===== Linux（apt）ここまで =====

# ---------------------------------------------------------------------
# 分析に使う言語そのものは入れない（どちらを使うかはプロジェクト次第）。
# パッケージはプロジェクトごとに .venv / renv で持つ（octavo init が足場を置く）。
say "分析の言語（任意）"
if command -v Rscript >/dev/null; then
  info "R: $(Rscript --version 2>&1 | head -1)"
  info "  プロジェクトごとに renv::init() → renv::snapshot()"
else
  info "R が無い。.qmd を R で書くなら: $R_HINT"
fi
info "Python: $(python3 -V 2>&1)"
info "  プロジェクトごとに python3 -m venv .venv → pip install -r requirements.txt"

# ---------------------------------------------------------------------
say "よく使う CSL スタイルを取っておく"
for S in chicago-author-date apa american-political-science-association \
         american-sociological-association ieee; do
  if [ "$DRY" = 0 ]; then
    python3 "$HERE/bin/octavo" csl get "$S" >/dev/null 2>&1 && info "取れた: $S" \
      || info "取れなかった（後で octavo csl get $S）: $S"
  else
    info "(実行しない) octavo csl get $S"
  fi
done

# ---------------------------------------------------------------------
say "octavo コマンドを PATH に置く"
BIN="$HOME/.local/bin"
run mkdir -p "$BIN"
run chmod +x "$HERE/bin/octavo" "$HERE/setup.sh"
if [ "$DRY" = 0 ]; then
  ln -sf "$HERE/bin/octavo" "$BIN/octavo"
  info "$BIN/octavo -> $HERE/bin/octavo"
  case ":$PATH:" in
    *":$BIN:"*) : ;;
    *) RC="$HOME/.bashrc"; [ "$(uname -s)" = Darwin ] && RC="$HOME/.zshrc"   # Mac の既定は zsh
       info "PATH に $BIN が無い。次の行を $RC に足すこと:"
       echo '       export PATH="$HOME/.local/bin:$PATH"' ;;
  esac
fi

# ---------------------------------------------------------------------
say "診断"
if [ "$DRY" = 0 ]; then
  python3 "$HERE/bin/octavo" doctor || true
fi

say "できあがり"
cat <<'EOS'
   使いはじめる:
     octavo init 2026-research           # プロジェクトのひな型を作る
     cd 2026-research
     octavo new paper example-paper      # 論文を足す（何本でも）
     octavo new slides example-talk      # 発表スライド
     octavo new lecture example-lecture  # 講義ノート（A4 プリント + 回ごとのスライド）
     octavo build --compile              # 全部を PDF まで
EOS
