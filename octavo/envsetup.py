# -*- coding: utf-8 -*-
"""プロジェクトの分析の環境（.venv と renv）を作る・揃える。

    octavo env

何度実行しても問題ない（あるものは作らず、足りないものだけ足す）。clone してきた
プロジェクトでは記録（requirements.txt / renv.lock）から環境を戻すことになる。

  Python  uv で `.venv` を作り、requirements.txt に書いたものを入れる
          （Python の .qmd は Quarto が ipykernel などで動かすので、それも入る）
  R       （R の .qmd があるときだけ）renv を入れ（なければ利用者のライブラリへ）、`renv::init()` か
          `renv::restore()`、Quarto の knitr エンジンに要る knitr / rmarkdown と、
          `.qmd` などが使っているのに入っていないパッケージ（外から持ち込んだ .qmd の
          `library(x)` など。renv::dependencies() で探す）を足して `renv::snapshot()`

R の分析が失敗したときにも、その .qmd が使っているのに入っていないパッケージを入れて
もう一度実行する（install_missing。analysis.run が呼ぶ）。

道具（uv・R）そのものは入れない。それは setup.sh（`octavo setup`）の役目。
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from .i18n import t

# Quarto が R の .qmd を render するのに要る（octavo.R 自体は素の R で動く）
R_NEEDS = ('knitr', 'rmarkdown')

# Rscript に渡す（一時ファイルにして）。repos が未設定（@CRAN@）なら CRAN のクラウドミラー。
# Linux で setup.sh を通していれば Rprofile.site が Posit Package Manager の
# ビルド済みパッケージを向いているので、それがそのまま使われる。
# 足りないパッケージを探して入れる（R_SCRIPT と MISSING_SCRIPT が使う）。
#   octavo_missing  渡した場所（.qmd やフォルダ）が library() / pkg:: で使っているのに、
#                   いまのライブラリ（renv のプロジェクトならその中）にないもの
#   octavo_install  入れる。まとめて入れて、だめなら1つずつ（CRAN にないものだけが残る）。
#                   入れたもの・入らなかったものを OCTAVO-INSTALLED: / OCTAVO-FAILED: の行で出す
R_FUNCTIONS = r'''
repos <- getOption("repos")
if (is.null(repos) || identical(unname(repos["CRAN"]), "@CRAN@"))
  repos <- c(CRAN = "https://cloud.r-project.org")
options(repos = repos)
octavo_missing <- function(paths) {
  deps <- tryCatch(unique(renv::dependencies(paths, quiet = TRUE)$Package),
                   error = function(e) character())
  deps <- deps[nzchar(deps) & deps != "R"]
  setdiff(deps, rownames(utils::installed.packages()))
}
octavo_install <- function(pkgs) {
  pkgs <- unique(pkgs)
  if (!length(pkgs)) return(character())
  try(renv::install(pkgs, prompt = FALSE), silent = TRUE)
  for (p in pkgs[!vapply(pkgs, requireNamespace, logical(1), quietly = TRUE)]) {
    try(renv::install(p, prompt = FALSE), silent = TRUE)
  }
  ok <- pkgs[vapply(pkgs, requireNamespace, logical(1), quietly = TRUE)]
  cat("\nOCTAVO-INSTALLED:", ok, "\n")
  cat("OCTAVO-FAILED:", setdiff(pkgs, ok), "\n")
  ok
}
'''

R_SCRIPT = R_FUNCTIONS + r'''
if (!requireNamespace("renv", quietly = TRUE)) {
  lib <- Sys.getenv("R_LIBS_USER")
  dir.create(lib, recursive = TRUE, showWarnings = FALSE)
  .libPaths(c(lib, .libPaths()))
  install.packages("renv", lib = lib)
}
changed <- FALSE
if (file.exists("renv.lock")) {
  renv::restore(prompt = FALSE)
} else if (!file.exists("renv/activate.R")) {
  renv::init(restart = FALSE)
  changed <- TRUE
}
need <- c(@@NEEDS@@)
miss <- need[!vapply(need, requireNamespace, logical(1), quietly = TRUE)]
# .qmd などが使っているのに入っていないもの（記録のあとで足した .qmd や、外から持ち込んだ .qmd）
miss <- unique(c(miss, octavo_missing(".")))
if (length(miss)) {
  if (length(octavo_install(miss))) changed <- TRUE
}
if (changed || !file.exists("renv.lock")) renv::snapshot(prompt = FALSE)
'''

# 分析が失敗したとき: その .qmd が使っているのに入っていないものを入れる（renv の
# プロジェクトの中で。入れたら renv.lock にも記録する）
MISSING_SCRIPT = R_FUNCTIONS + r'''
ok <- octavo_install(octavo_missing(c(@@PATHS@@)))
if (length(ok)) renv::snapshot(prompt = FALSE)
'''


# プロジェクトの外で使う R のパッケージを、利用者のライブラリ（R_LIBS_USER）に依存ごと入れる。
#   knitr・rmarkdown  Quarto が R の .qmd を組むのに要る（プロジェクトの renv の外で組むとき。
#                     R を上げて古いライブラリを消すと、これがなくなって分析が止まる）
#   languageserver    VS Code の R 拡張機能が補完などに使う。renv のプロジェクトでは R が
#                     プロジェクト専用のライブラリしか見ないので、R 拡張機能の r.libPaths で
#                     このライブラリを足す（そうしないとプロジェクトごとに「入れますか」と聞かれる）
# ホームで実行する（renv の外。sudo は要らない）。
R_EDITOR_SCRIPT = r'''
lib <- path.expand(Sys.getenv("R_LIBS_USER"))
dir.create(lib, recursive = TRUE, showWarnings = FALSE)
repos <- getOption("repos")
if (is.null(repos) || identical(unname(repos["CRAN"]), "@CRAN@"))
  repos <- c(CRAN = "https://cloud.r-project.org")
# Ubuntu などで Posit Package Manager を向いているなら、Linux 用のビルド済みを取る（renv が
# プロジェクトの中でしているのと同じ）。ソースからだと開発用のライブラリ（libuv など）が要る
os <- if (file.exists("/etc/os-release")) readLines("/etc/os-release", warn = FALSE) else ""
code <- sub("^VERSION_CODENAME=", "", grep("^VERSION_CODENAME=", os, value = TRUE))
if (length(code) == 1L && nzchar(code) && grepl("packagemanager.posit.co/cran/", repos[["CRAN"]], fixed = TRUE) &&
    !grepl("__linux__", repos[["CRAN"]], fixed = TRUE)) {
  repos[["CRAN"]] <- sub("/cran/", paste0("/cran/__linux__/", code, "/"), repos[["CRAN"]], fixed = TRUE)
  options(HTTPUserAgent = sprintf("R/%s R (%s)", getRversion(),
    paste(getRversion(), R.version$platform, R.version$arch, R.version$os)))
}
# renv の中では R 本体のライブラリ（.Library）と足したライブラリしか見えない。サイトライブラリに
# ある依存（callr など）も含めて、利用者のライブラリに全部そろえる
ap <- available.packages(repos = repos)
want <- c("knitr", "rmarkdown", "languageserver")
deps <- unique(c(want, unlist(tools::package_dependencies(
  want, db = ap, recursive = TRUE, which = c("Depends", "Imports", "LinkingTo")))))
base <- rownames(installed.packages(lib.loc = .Library))
need <- setdiff(deps, c(base, rownames(installed.packages(lib.loc = lib))))
if (length(need)) {
  install.packages(need, lib = lib, repos = repos)
} else {
  cat("   installed: knitr, rmarkdown, languageserver\n")
}
.libPaths(lib, include.site = FALSE)   # renv と同じ見え方（R 本体 + これだけ）で読めるか
ok <- all(vapply(want, requireNamespace, logical(1), quietly = TRUE))
cat("library: ", normalizePath(lib, winslash = "/", mustWork = FALSE), "\n", sep = "")
quit(save = "no", status = if (ok) 0 else 1)
'''


def r_editor() -> int:
    """`octavo setup --r-editor`: knitr・rmarkdown・languageserver を利用者のライブラリに入れる（sudo なし）。"""
    rscript = shutil.which('Rscript')
    if not rscript:
        _say(t('R is not installed, so this was skipped. octavo setup installs it'))
        return 1
    fd, path = tempfile.mkstemp(prefix='octavo-r-editor-', suffix='.R')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            fh.write(R_EDITOR_SCRIPT)
        ok = _call([rscript, path], Path.home(),
                   shown='Rscript <install.packages(c("knitr", "rmarkdown", "languageserver")) into R_LIBS_USER>')
    finally:
        os.unlink(path)
    _say(t('knitr, rmarkdown and languageserver are in your own R library. In VS Code, add that '
           'library to the R extension\'s r.libPaths so renv projects find languageserver too.') if ok
         else t('Could not install them (see above).'))
    return 0 if ok else 1


def has_requirements(path: Path) -> bool:
    """コメントと空行以外が1行でもあるか（ひな型のままなら入れるものはない）。"""
    if not path.exists():
        return False
    for line in path.read_text(encoding='utf-8').splitlines():
        s = line.strip()
        if s and not s.startswith('#'):
            return True
    return False


def _say(msg: str) -> None:
    # 子プロセスの出力と順番が入れ替わらないように毎回流す
    print(msg, flush=True)


def _call(cmd: list, cwd: Path, env: dict | None = None, shown: str = '') -> bool:
    _say('  $ ' + (shown or ' '.join(str(c) for c in cmd)))
    try:
        return subprocess.call([str(c) for c in cmd], cwd=str(cwd), env=env) == 0
    except OSError as e:
        _say('  ' + t('cannot run it: {why}', why=e))
        return False


def python_env(root: Path) -> bool | None:
    """`.venv` を作って requirements.txt を入れる。uv がなければ None（飛ばした）。"""
    uv = shutil.which('uv')
    _say('\n== Python (.venv)')
    if not uv:
        _say('  ' + t('uv is not installed, so this was skipped. octavo setup installs it'))
        return None
    venv = root / '.venv'
    ok = True
    if venv.exists():
        _say('  ' + t('.venv is already there'))
    else:
        ok = _call([uv, 'venv', venv], root, shown='uv venv .venv')
    req = root / 'requirements.txt'
    if ok and has_requirements(req):
        env = {**os.environ, 'VIRTUAL_ENV': str(venv)}
        ok = _call([uv, 'pip', 'install', '-r', req], root, env,
                   shown='uv pip install -r requirements.txt')
    elif ok:
        _say('  ' + t('requirements.txt lists nothing yet: add a package there, then run this again'))
    return ok


def r_env(root: Path) -> bool | None:
    """renv を用意して knitr / rmarkdown を入れる。R がなければ None（飛ばした）。"""
    rscript = shutil.which('Rscript')
    _say('\n== R (renv)')
    if not rscript:
        _say('  ' + t('R is not installed, so this was skipped. octavo setup installs it'))
        return None
    code = R_SCRIPT.replace('@@NEEDS@@', ', '.join(f'"{p}"' for p in R_NEEDS))
    # -e に複数行を渡すと Windows では引用符が崩れるので、どこでもファイルにして渡す
    fd, path = tempfile.mkstemp(prefix='octavo-env-', suffix='.R')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            fh.write(code)
        ok = _call([rscript, path], root,
                   shown='Rscript <renv::init() / restore(), then ' + ', '.join(R_NEEDS) + '>')
        if ok:
            # renv::status() は「入っていて記録もあるが、コードでは使っていない」だけでも
            # out-of-sync と言う（R に付いてくる MASS や boot、使わなくなったもの）。不安に
            # させないように先に言っておく
            _say('  ' + t('If renv::status() says "out-of-sync" only for packages the code does not use '
                          '(MASS or boot, which come with R, or ones you stopped using), that is '
                          'harmless: nothing is missing.'))
        return ok
    finally:
        os.unlink(path)


def install_missing(root: Path, qmds: list) -> tuple | None:
    """renv のプロジェクトで、qmds が使っているのに入っていない R のパッケージを入れる。

    (入れたもの, 入らなかったもの) を返す。renv のプロジェクトでない・R がないときは None
    （何もしない。環境を作るのは octavo env の役目）。
    """
    rscript = shutil.which('Rscript')
    if not rscript or not (Path(root) / 'renv' / 'activate.R').exists():
        return None
    paths = ', '.join('"' + Path(q).resolve().as_posix().replace('"', '\\"') + '"' for q in qmds)
    fd, path = tempfile.mkstemp(prefix='octavo-missing-', suffix='.R')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            fh.write(MISSING_SCRIPT.replace('@@PATHS@@', paths))
        # プロジェクトの根で実行する（.Rprofile が renv を有効にする）
        r = subprocess.run([rscript, path], cwd=str(root), capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
    except OSError:
        return None
    finally:
        os.unlink(path)
    return _installed_lines(r.stdout or '')


def _installed_lines(out: str) -> tuple:
    """R の OCTAVO-INSTALLED: / OCTAVO-FAILED: の行を読む。renv の進み具合の表示が
    改行なしで前に付くことがある（端末の制御文字）ので、行の途中からでも読む。"""
    got: dict = {'INSTALLED': [], 'FAILED': []}
    for m in re.finditer(r'OCTAVO-(INSTALLED|FAILED):([^\n]*)', out):
        got[m.group(1)] = m.group(2).split()
    return got['INSTALLED'], got['FAILED']


def pending(cfg) -> bool:
    """この分析の環境がまだ整っていないか（`.venv` か、R の分析なら renv がない）。
    拡張機能が「初めての分析」のあとに `octavo env` を実行するかどうかの判断に使う。"""
    from . import analysis as anamod
    root = Path(cfg.root)
    if not anamod.units(cfg):
        return False
    if not (root / 'renv' / 'activate.R').exists() and 'r' in anamod.engines(cfg):
        return True
    return not (root / '.venv').exists()


def run(cfg) -> int:
    root = Path(cfg.root)
    # 分析のないプロジェクト（スライドだけ、など）には環境を作らない
    from . import analysis as anamod
    if not (cfg['analysis'] and anamod.status(cfg)):
        _say(t('There is no analysis in this project, so there is nothing to set up. '
               'Add one with: {cmd}', cmd='octavo new analysis <name>'))
        return 0
    # R の .qmd がなければ renv は要らない（Python だけの分析に R を入れさせない）
    results = [python_env(root)]
    if 'r' in anamod.engines(cfg):
        results.append(r_env(root))
    if any(r is False for r in results):
        _say('\n' + t('Something failed (see above). Fix it and run octavo env again.'))
        return 1
    if all(r is None for r in results):
        _say('\n' + t('Neither uv nor R is installed. Run octavo setup first.')
             if len(results) > 1 else '\n' + t('uv is not installed. Run octavo setup first.'))
        return 1
    _say('\n' + (t('The analysis environment is ready. Commit requirements.txt and renv.lock.')
                 if len(results) > 1 else
                 t('The analysis environment is ready. Commit requirements.txt.')))
    return 0
