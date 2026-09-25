#!/usr/bin/env bash
# =====================================================================
#  octavo を動かすための導入。WSL / Ubuntu（apt）と macOS（Homebrew）。
#  Installs what octavo needs. WSL / Ubuntu (apt) and macOS (Homebrew).
#
#    bash setup.sh                ふだん使う一式 / the everyday set:
#                                 pandoc, Typst, quarto, fonts, R (CRAN), renv, uv, octavo
#    bash setup.sh --with-tex     TeX Live も / TeX Live too (LaTeX / Beamer; several GB)
#    bash setup.sh --minimal      pandoc と日本語フォントだけ / pandoc and CJK fonts only
#    bash setup.sh --no-typst     Typst を入れない / leave out Typst
#    bash setup.sh --no-quarto    quarto を入れない / leave out quarto
#    bash setup.sh --no-r         R を入れない / leave out R
#    bash setup.sh --no-cjk-fonts 日本語フォントを入れない / leave out CJK fonts
#    bash setup.sh --octavo-version X   octavo を PyPI の X で入れる / install octavo X from PyPI
#    bash setup.sh --check        何を入れるか見るだけ / only show what would be done
#
#  VS Code の拡張機能の「準備する」も、`octavo setup` も、これを走らせる。
#  Windows で直接使うときは setup.ps1（winget）が同じ役目をする。
#  The VS Code extension's "Set up" and `octavo setup` both run this file.
#  同じことを何度走らせても平気 / Safe to run again: what is there is skipped.
# =====================================================================
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PANDOC_MIN="2.11"          # --citeproc（CSL 引用）に要る
# 動作を確かめた版。入っているものがこれより古ければ GitHub から入れる。
# CI（.github/workflows/tests.yml）もここから版を読むので、上げるときはここだけ直す。
PANDOC_VER="3.11"
TYPST_VER="0.15.1"         # Typst スライドは 0.12 以上が要る
QUARTO_VER="1.10.18"       # 分析（.qmd）を render する
UV_VER="0.12.18"           # プロジェクトの .venv と octavo 本体を入れる
# R は版を固定しない（CRAN の最新）。パッケージはプロジェクトごとに renv で持つ。

WITH_TEX=0; WITH_TYPST=1; WITH_QUARTO=1; WITH_CJK=1; WITH_R=1; MINIMAL=0; DRY=0
OCTAVO_VERSION=""
while [ $# -gt 0 ]; do
  case "$1" in
    --minimal) MINIMAL=1; WITH_TEX=0; WITH_TYPST=0; WITH_QUARTO=0; WITH_R=0 ;;
    --with-tex) WITH_TEX=1 ;;
    --no-typst) WITH_TYPST=0 ;;
    --no-quarto) WITH_QUARTO=0 ;;
    --no-r) WITH_R=0 ;;
    --no-cjk-fonts) WITH_CJK=0 ;;
    --octavo-version) OCTAVO_VERSION="${2:-}"; shift ;;
    --check|--dry-run) DRY=1 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1"; exit 1 ;;
  esac
  shift
done

# 表示の言語。octavo 本体と同じく OCTAVO_LANG、無ければロケール。
case "${OCTAVO_LANG:-${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}}" in
  ja*) L=ja ;;
  *) L=en ;;
esac
m()    { if [ "$L" = ja ]; then printf '%s' "$1"; else printf '%s' "$2"; fi; }
say()  { printf '\n\033[1m== %s\033[0m\n' "$(m "$1" "$2")"; }
info() { printf '   %s\n' "$*"; }
msg()  { info "$(m "$1" "$2")"; }
run()  { if [ "$DRY" = 1 ]; then info "($(m '実行しない' 'not run')) $*"; else "$@"; fi; }

SUDO=""
if [ "$(id -u)" != 0 ] && [ "$(uname -s)" != Darwin ]; then
  command -v sudo >/dev/null && SUDO="sudo" || {
    m "root でもなく sudo も無い。パッケージを入れられない" \
      "Not root and no sudo, so nothing can be installed"; echo; exit 1; }
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

BIN="$HOME/.local/bin"
ORIG_PATH="$PATH"
export PATH="$BIN:$PATH"   # uv と octavo はここに入る

# ---------------------------------------------------------------------
# macOS: Homebrew で入れる。版は Homebrew の最新（Linux で固定している版以上）。
# 入っていても固定の版より古ければ brew upgrade する（Linux 側と同じ考え方）。
# brew は root で動かさないので sudo は使わない。
brew_one() {  # brew_one <formula|--cask> <名前>
  local kind="$1" name="$2"
  if [ "$kind" = --cask ]; then
    if brew list --cask "$name" >/dev/null 2>&1; then msg "入っている: $name" "installed: $name"; return; fi
    run brew install --cask "$name" || msg "入らなかった（後で brew install --cask $name）: $name" \
                                          "failed (later: brew install --cask $name): $name"
  else
    if brew list --formula "$name" >/dev/null 2>&1; then msg "入っている: $name" "installed: $name"; return; fi
    run brew install "$name" || msg "入らなかった（後で brew install $name）: $name" \
                                    "failed (later: brew install $name): $name"
  fi
}

brew_tool() {  # brew_tool <コマンド> <固定の版> <formula|--cask> <名前>
  local cmd="$1" want="$2" kind="$3" name="$4" have=""
  have="$("$cmd" --version 2>/dev/null | head -1 | grep -oE '[0-9]+(\.[0-9]+)+' | head -1 || true)"
  if [ -n "$have" ] && ver_ge "$have" "$want"; then
    msg "入っている: $cmd $have" "installed: $cmd $have"
  elif [ -n "$have" ] && brew list $kind "$name" >/dev/null 2>&1; then
    msg "いまの $have は動作を確かめた $want より古いので上げる" \
        "$have is older than the tested $want, upgrading"
    run brew upgrade $kind "$name"
  else
    [ -n "$have" ] && msg "いまの $have（Homebrew の外）は $want より古い。Homebrew のものを入れる" \
                          "$have (outside Homebrew) is older than $want; installing Homebrew's"
    run brew install $kind "$name"
  fi
}

install_macos() {
  say "環境" "System"
  info "macOS $(sw_vers -productVersion 2>/dev/null || echo '?')  ($(uname -m))"
  command -v brew >/dev/null || {
    m "Homebrew が無い。https://brew.sh の1行で入れてから、もう一度走らせること" \
      "Homebrew is missing. Install it with the one line at https://brew.sh, then run this again"
    echo; exit 1; }

  say "pandoc" "pandoc"
  brew_tool pandoc "$PANDOC_VER" "" pandoc
  if [ "$WITH_TYPST" = 1 ]; then
    say "Typst" "Typst"
    brew_tool typst "$TYPST_VER" "" typst
  fi
  if [ "$WITH_CJK" = 1 ]; then
    # 既定の書体（octavo/backends/typst.py の FONTS）。どれも無くても、
    # macOS に最初からあるヒラギノに落ちるので組版は止まらない。
    say "フォント" "Fonts"
    for c in font-biz-udmincho font-biz-udgothic font-inter \
             font-noto-serif-cjk-jp font-noto-sans-cjk-jp; do
      brew_one --cask "$c"
    done
  fi
  if [ "$WITH_QUARTO" = 1 ]; then
    say "quarto" "quarto"
    brew_tool quarto "$QUARTO_VER" --cask quarto
  fi
  if [ "$WITH_R" = 1 ]; then
    # CRAN の公式ビルド（cask）。formula の r と違い、CRAN のビルド済み
    # パッケージがそのまま使える。入れるときに管理者のパスワードを聞かれる。
    say "R（CRAN の最新）" "R (latest from CRAN)"
    if command -v Rscript >/dev/null; then
      msg "入っている: $(Rscript --version 2>&1 | head -1)" "installed: $(Rscript --version 2>&1 | head -1)"
    else
      brew_one --cask r
    fi
  fi
  if [ "$WITH_TEX" = 1 ]; then
    # 日本語（luatexja・ltjsarticle・原ノ味）と Beamer は MacTeX に全部入っている
    say "TeX（MacTeX。数 GB）" "TeX (MacTeX; several GB)"
    brew_one --cask mactex-no-gui
    msg "入れたらターミナルを開き直す（/Library/TeX/texbin が PATH に入る）" \
        "Open a new terminal afterwards (so /Library/TeX/texbin is on PATH)"
  fi
}

if [ "$(uname -s)" = Darwin ]; then
  install_macos
else
# ===== ここから Linux（apt）=====

# ---------------------------------------------------------------------
say "環境" "System"
. /etc/os-release 2>/dev/null || true
info "${PRETTY_NAME:-?}"
grep -qi microsoft /proc/version 2>/dev/null && msg "WSL の上で動いている" "running on WSL" || true
ARCH="$(dpkg --print-architecture 2>/dev/null || echo amd64)"
msg "アーキテクチャ: $ARCH" "architecture: $ARCH"

command -v apt-get >/dev/null || {
  m "apt が無い。Debian/Ubuntu 以外は手で入れること" \
    "No apt. On anything but Debian/Ubuntu, install the tools by hand"; echo; exit 1; }
if [ -n "$SUDO" ] && [ "$DRY" = 0 ]; then
  msg "パッケージを入れるのに管理者のパスワードを聞かれる（1回）" \
      "sudo will ask for your password (once) to install packages"
fi

# ---------------------------------------------------------------------
say "apt の更新" "Updating apt"
run $SUDO apt-get update -qq

# xz-utils: Typst の配布物（.tar.xz）を展開するのに要る。最小構成の Ubuntu には無い
PKGS=(pandoc fontconfig python3 curl ca-certificates xz-utils)
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
    msg "$p は apt に無いので飛ばす（Noto で組む）" "$p is not in apt, skipped (Noto is used)"
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

say "パッケージを入れる" "Installing packages"
info "${PKGS[*]}"
run $SUDO apt-get install -y --no-install-recommends "${PKGS[@]}"

# ---------------------------------------------------------------------
say "pandoc の版を確かめる" "Checking the pandoc version"
PV="$(pandoc -v 2>/dev/null | head -1 | awk '{print $2}' || echo 0)"
msg "いま: $PV" "now: $PV"
if ! ver_ge "$PV" "$PANDOC_VER"; then
  if ver_ge "$PV" "$PANDOC_MIN"; then
    msg "動作を確かめた $PANDOC_VER より古い（Typst の書き出しや引用の組み方が違うことがある）" \
        "older than the tested $PANDOC_VER (Typst output and citations may differ)"
  else
    msg "CSL 引用（--citeproc）に $PANDOC_MIN 以上が要る" "CSL citations (--citeproc) need $PANDOC_MIN or newer"
  fi
  DEB="pandoc-${PANDOC_VER}-1-${ARCH}.deb"
  URL="https://github.com/jgm/pandoc/releases/download/${PANDOC_VER}/${DEB}"
  msg "GitHub から $PANDOC_VER を入れる: $URL" "installing $PANDOC_VER from GitHub: $URL"
  if [ "$DRY" = 0 ]; then
    TMP="$(mktemp -d)"
    if curl -fsSL -o "$TMP/$DEB" "$URL"; then
      $SUDO apt-get install -y "$TMP/$DEB" || $SUDO dpkg -i "$TMP/$DEB"
      rm -rf "$TMP"
    else
      msg "取得できなかった。手で入れること: https://github.com/jgm/pandoc/releases" \
          "download failed. Install it by hand: https://github.com/jgm/pandoc/releases"
    fi
  fi
  msg "いま: $(pandoc -v 2>/dev/null | head -1 | awk '{print $2}')" \
      "now: $(pandoc -v 2>/dev/null | head -1 | awk '{print $2}')"
fi

# ---------------------------------------------------------------------
if [ "$WITH_TYPST" = 1 ]; then
  say "Typst" "Typst"
  TV="$(typst --version 2>/dev/null | awk '{print $2}' || true)"
  if [ -n "$TV" ] && ver_ge "$TV" "$TYPST_VER"; then
    msg "入っている: $(typst --version)" "installed: $(typst --version)"
  else
    [ -n "$TV" ] && msg "いまの $TV は動作を確かめた $TYPST_VER より古いので入れ直す" \
                        "$TV is older than the tested $TYPST_VER, reinstalling"
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
          msg "入れた: $(typst --version)" "installed: $(typst --version)"
        else
          msg "取得できなかった。https://github.com/typst/typst/releases から手で" \
              "download failed. Install it by hand from https://github.com/typst/typst/releases"
        fi
        rm -rf "$TMP"
      fi
    else
      msg "このアーキテクチャ用の配布が分からない。手で入れること" \
          "no known build for this architecture. Install it by hand"
    fi
  fi
fi

# ---------------------------------------------------------------------
say "フォントの登録" "Registering fonts"
run fc-cache -f >/dev/null
if [ "$DRY" = 0 ]; then
  N=$(fc-list :lang=ja family 2>/dev/null | wc -l)
  msg "日本語フォント $N 件" "$N CJK font families"
  command -v typst >/dev/null && \
    msg "Typst から見える CJK: $(typst fonts 2>/dev/null | grep -ci cjk || echo 0) 件" \
        "CJK fonts visible to Typst: $(typst fonts 2>/dev/null | grep -ci cjk || echo 0)" || true
fi

# ---------------------------------------------------------------------
# 分析（analysis/*.qmd）を render するのに要る。原稿の数値・図・表はここから来るので、
# 既定で入れる（要らなければ --no-quarto）。
if [ "$WITH_QUARTO" = 1 ]; then
  say "quarto" "quarto"
  QV="$(quarto --version 2>/dev/null | head -1 || true)"
  if [ -n "$QV" ] && ver_ge "$QV" "$QUARTO_VER"; then
    msg "入っている: $QV" "installed: $QV"
  else
    [ -n "$QV" ] && msg "いまの $QV は動作を確かめた $QUARTO_VER より古いので入れ直す" \
                        "$QV is older than the tested $QUARTO_VER, reinstalling"
    DEB="quarto-${QUARTO_VER}-linux-${ARCH}.deb"
    URL="https://github.com/quarto-dev/quarto-cli/releases/download/v${QUARTO_VER}/${DEB}"
    info "$URL"
    if [ "$DRY" = 0 ]; then
      TMP="$(mktemp -d)"
      if curl -fsSL -o "$TMP/$DEB" "$URL"; then
        $SUDO apt-get install -y "$TMP/$DEB" || $SUDO dpkg -i "$TMP/$DEB"
        msg "入れた: $(quarto --version 2>/dev/null | head -1)" "installed: $(quarto --version 2>/dev/null | head -1)"
      else
        msg "取得できなかった。https://quarto.org/docs/get-started/ から手で" \
            "download failed. Install it by hand from https://quarto.org/docs/get-started/"
      fi
      rm -rf "$TMP"
    fi
  fi
fi

# ---------------------------------------------------------------------
# R は CRAN の最新。Ubuntu では CRAN の apt リポジトリを足す（Ubuntu 標準の r-base は
# リリース時点の版で止まっている）。Debian などはそのディストリの r-base。
# パッケージを自分でビルドすることになっても止まらないように、よく要る開発用
# ライブラリも入れる（tidyverse が要求するもの一式）。
if [ "$WITH_R" = 1 ]; then
  say "R（CRAN の最新）" "R (latest from CRAN)"
  CRAN_LIST=/etc/apt/sources.list.d/cran-r.list
  if [ "${ID:-}" = ubuntu ] && [ -n "${VERSION_CODENAME:-}" ]; then
    if grep -rqs 'cloud.r-project.org/bin/linux/ubuntu' /etc/apt/sources.list /etc/apt/sources.list.d/; then
      msg "CRAN のリポジトリはもう足してある" "the CRAN repository is already there"
    else
      KEY=/etc/apt/keyrings/cran-ubuntu.asc
      msg "CRAN のリポジトリを足す（${VERSION_CODENAME}-cran40）" "adding the CRAN repository (${VERSION_CODENAME}-cran40)"
      run $SUDO install -d -m 0755 /etc/apt/keyrings
      if [ "$DRY" = 0 ]; then
        if curl -fsSL https://cloud.r-project.org/bin/linux/ubuntu/marutter_pubkey.asc \
             | $SUDO tee "$KEY" >/dev/null; then
          echo "deb [signed-by=$KEY] https://cloud.r-project.org/bin/linux/ubuntu ${VERSION_CODENAME}-cran40/" \
            | $SUDO tee "$CRAN_LIST" >/dev/null
        else
          msg "CRAN の鍵を取れなかった。Ubuntu 標準の r-base を入れる" \
              "could not fetch CRAN's key; installing Ubuntu's own r-base"
        fi
      fi
      run $SUDO apt-get update -qq
    fi
  else
    msg "Ubuntu ではないので、このディストリの r-base を入れる" "not Ubuntu, so this distribution's r-base is used"
  fi
  RPKGS=(r-base r-base-dev)
  for p in libcurl4-openssl-dev libssl-dev libxml2-dev libfontconfig1-dev \
           libharfbuzz-dev libfribidi-dev libfreetype-dev libpng-dev libtiff-dev libjpeg-dev; do
    apt-cache show "$p" >/dev/null 2>&1 && RPKGS+=("$p")
  done
  info "${RPKGS[*]}"
  run $SUDO apt-get install -y --no-install-recommends "${RPKGS[@]}"

  # パッケージは Posit Package Manager から。renv は Linux ではこの URL を
  # ビルド済みパッケージの URL に読み替えるので、tidyverse もコンパイル無しで入る。
  SITE=/etc/R/Rprofile.site
  if [ "$DRY" = 0 ] && [ -f "$SITE" ] && ! grep -q 'packagemanager.posit.co' "$SITE"; then
    $SUDO tee -a "$SITE" >/dev/null <<'EOS'

# octavo setup: CRAN packages from Posit Package Manager. On Linux, renv turns
# this URL into the one for prebuilt binaries, so nothing has to be compiled.
local({
  options(repos = c(CRAN = "https://packagemanager.posit.co/cran/latest"))
  options(HTTPUserAgent = sprintf("R/%s R (%s)", getRversion(), paste(getRversion(),
    R.version["platform"], R.version["arch"], R.version["os"])))
})
EOS
    msg "パッケージの取得先を Posit Package Manager にした（$SITE）" \
        "packages now come from Posit Package Manager ($SITE)"
  fi
fi

fi
# ===== Linux（apt）ここまで =====

# ---------------------------------------------------------------------
# renv は R に付いてこない。利用者のライブラリに入れる（sudo は要らない）。
if [ "$WITH_R" = 1 ] && command -v Rscript >/dev/null; then
  say "renv" "renv"
  if [ "$DRY" = 0 ]; then
    Rscript -e '
      if (requireNamespace("renv", quietly = TRUE)) {
        cat("   installed: renv", as.character(packageVersion("renv")), "\n")
      } else {
        lib <- Sys.getenv("R_LIBS_USER")
        dir.create(lib, recursive = TRUE, showWarnings = FALSE)
        repos <- getOption("repos")
        if (identical(unname(repos["CRAN"]), "@CRAN@")) repos <- c(CRAN = "https://cloud.r-project.org")
        install.packages("renv", lib = lib, repos = repos)
      }' || msg "renv を入れられなかった（後で octavo env が入れる）" "could not install renv (octavo env will try again)"
  fi
  msg "R: $(Rscript --version 2>&1 | head -1)" "R: $(Rscript --version 2>&1 | head -1)"
fi

# ---------------------------------------------------------------------
# uv: プロジェクトの .venv を作り（octavo env）、octavo 本体も入れる。~/.local/bin に入る。
say "uv" "uv"
UVV="$(uv --version 2>/dev/null | awk '{print $2}' || true)"
if [ -n "$UVV" ] && ver_ge "$UVV" "$UV_VER"; then
  msg "入っている: uv $UVV" "installed: uv $UVV"
else
  if [ "$DRY" = 0 ]; then
    curl -LsSf "https://astral.sh/uv/${UV_VER}/install.sh" | env UV_NO_MODIFY_PATH=1 sh \
      || msg "取得できなかった。https://docs.astral.sh/uv/ から手で" \
             "download failed. Install it by hand: https://docs.astral.sh/uv/"
  else
    info "($(m '実行しない' 'not run')) curl -LsSf https://astral.sh/uv/${UV_VER}/install.sh | sh"
  fi
fi

# ---------------------------------------------------------------------
# octavo 本体。clone から走らせたらそのシンボリックリンク、そうでなければ
# （拡張機能・octavo setup）PyPI の octavo-kit を uv で入れる。
# clone へのリンクが既にあるなら上書きしない（開発している人の環境を壊さない）。
say "octavo コマンド" "The octavo command"
run mkdir -p "$BIN"
is_clone() { [ -f "$1/bin/octavo" ] && [ -f "$1/setup.sh" ] && [ -d "$1/octavo" ]; }
LINKED=""
if [ -L "$BIN/octavo" ]; then
  LINKED="$(cd "$(dirname "$(readlink -f "$BIN/octavo")")/.." 2>/dev/null && pwd || true)"
fi
if is_clone "$HERE"; then
  run chmod +x "$HERE/bin/octavo" "$HERE/setup.sh"
  if [ "$DRY" = 0 ]; then
    ln -sf "$HERE/bin/octavo" "$BIN/octavo"
    info "$BIN/octavo -> $HERE/bin/octavo"
  fi
elif [ -n "$LINKED" ] && is_clone "$LINKED"; then
  msg "clone を使っているので入れ替えない: $BIN/octavo -> $LINKED" \
      "left alone, it points at a clone: $BIN/octavo -> $LINKED"
else
  HAVE="$("$BIN/octavo" --version 2>/dev/null | awk '{print $2}' || true)"
  if [ -n "$OCTAVO_VERSION" ] && [ "$HAVE" = "$OCTAVO_VERSION" ]; then
    msg "入っている: octavo $HAVE" "installed: octavo $HAVE"
  else
    run uv tool install --force "octavo-kit${OCTAVO_VERSION:+==$OCTAVO_VERSION}" \
      || msg "入らなかった（後で uv tool install octavo-kit）" "failed (later: uv tool install octavo-kit)"
  fi
fi
if [ "$DRY" = 0 ]; then
  case ":$ORIG_PATH:" in
    *":$BIN:"*) : ;;
    *) RC="$HOME/.bashrc"; [ "$(uname -s)" = Darwin ] && RC="$HOME/.zshrc"   # Mac の既定は zsh
       msg "ターミナルから使うなら、次の行を $RC に足す（VS Code の拡張機能には要らない）:" \
           "To use it from a terminal, add this line to $RC (the VS Code extension does not need it):"
       echo '       export PATH="$HOME/.local/bin:$PATH"' ;;
  esac
fi

# ---------------------------------------------------------------------
OCTAVO="$BIN/octavo"
if [ -x "$OCTAVO" ]; then
  say "よく使う CSL スタイルを取っておく" "Fetching common CSL styles"
  for S in chicago-author-date apa american-political-science-association \
           american-sociological-association ieee; do
    if [ "$DRY" = 0 ]; then
      "$OCTAVO" csl get "$S" >/dev/null 2>&1 && msg "取れた: $S" "fetched: $S" \
        || msg "取れなかった（後で octavo csl get $S）: $S" "failed (later: octavo csl get $S): $S"
    else
      info "($(m '実行しない' 'not run')) octavo csl get $S"
    fi
  done

  say "診断" "Diagnosis"
  if [ "$DRY" = 0 ]; then
    OCTAVO_LANG="$L" "$OCTAVO" doctor || true
  fi
fi

say "できあがり" "Done"
if [ "$L" = ja ]; then
cat <<'EOS'
   使いはじめる（VS Code なら、サイドバーの Octavo から同じことができる）:
     octavo init 2026-research           # プロジェクトのひな型を作る
     cd 2026-research
     octavo env                          # 分析の環境（.venv と renv）を用意する
     octavo new paper example-paper      # 論文を足す（何本でも）
     octavo new slides example-talk      # 発表スライド
     octavo new lecture example-lecture  # 講義ノート（A4 プリント + 回ごとのスライド）
     octavo build --compile              # 全部を PDF まで
EOS
else
cat <<'EOS'
   Getting started (in VS Code, the Octavo sidebar does the same):
     octavo init 2026-research           # write a project skeleton
     cd 2026-research
     octavo env                          # set up the analysis environment (.venv and renv)
     octavo new paper example-paper      # add a paper (as many as you like)
     octavo new slides example-talk      # a slide deck
     octavo new lecture example-lecture  # lecture notes (A4 handout + a deck per session)
     octavo build --compile              # everything, to PDF
EOS
fi
