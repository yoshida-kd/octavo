# -*- coding: utf-8 -*-
"""プロジェクトの分析の環境（.venv と renv）を作る・揃える。

    octavo env

何度実行しても問題ない（あるものは作らず、足りないものだけ足す）。clone してきた
プロジェクトでは記録（requirements.txt / renv.lock）から環境を戻すことになる。

  Python  uv で `.venv` を作り、requirements.txt に書いたものを入れる
          （Python の .qmd は Quarto が ipykernel などで動かすので、それも入る）
  R       （R の .qmd があるときだけ）renv を入れ（なければ利用者のライブラリへ）、`renv::init()` か
          `renv::restore()`、Quarto の knitr エンジンに要る knitr / rmarkdown を
          足して `renv::snapshot()`

道具（uv・R）そのものは入れない。それは setup.sh（`octavo setup`）の役目。
"""
from __future__ import annotations

import os
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
R_SCRIPT = r'''
repos <- getOption("repos")
if (is.null(repos) || identical(unname(repos["CRAN"]), "@CRAN@"))
  repos <- c(CRAN = "https://cloud.r-project.org")
options(repos = repos)
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
if (length(miss)) {
  renv::install(miss, prompt = FALSE)
  changed <- TRUE
}
if (changed || !file.exists("renv.lock")) renv::snapshot(prompt = FALSE)
'''


# VS Code の R 拡張機能が補完などに使う languageserver。renv のプロジェクトでは R が
# プロジェクト専用のライブラリしか見ないので、プロジェクトごとに「入れますか」と聞かれ続ける。
# 利用者のライブラリ（R_LIBS_USER）に一度だけ入れ、R 拡張機能の r.libPaths でそこを足す。
# ホームで実行する（renv の外。Linux なら Rprofile.site の Posit のビルド済みパッケージが使われる）。
R_EDITOR_SCRIPT = r'''
lib <- path.expand(Sys.getenv("R_LIBS_USER"))
dir.create(lib, recursive = TRUE, showWarnings = FALSE)
repos <- getOption("repos")
if (is.null(repos) || identical(unname(repos["CRAN"]), "@CRAN@"))
  repos <- c(CRAN = "https://cloud.r-project.org")
# renv の中では R 本体のライブラリ（.Library）と足したライブラリしか見えない。サイトライブラリに
# ある依存（callr など）も含めて、利用者のライブラリに全部そろえる
ap <- available.packages(repos = repos)
deps <- unique(c("languageserver", unlist(tools::package_dependencies(
  "languageserver", db = ap, recursive = TRUE, which = c("Depends", "Imports", "LinkingTo")))))
base <- rownames(installed.packages(lib.loc = .Library))
need <- setdiff(deps, c(base, rownames(installed.packages(lib.loc = lib))))
if (length(need)) {
  install.packages(need, lib = lib, repos = repos)
} else {
  cat("   installed: languageserver\n")
}
.libPaths(lib, include.site = FALSE)   # renv と同じ見え方（R 本体 + これだけ）で読めるか
ok <- requireNamespace("languageserver", quietly = TRUE)
cat("library: ", normalizePath(lib, winslash = "/", mustWork = FALSE), "\n", sep = "")
quit(save = "no", status = if (ok) 0 else 1)
'''


def r_editor() -> int:
    """`octavo setup --r-editor`: languageserver を利用者のライブラリに入れる（sudo なし）。"""
    rscript = shutil.which('Rscript')
    if not rscript:
        _say(t('R is not installed, so this was skipped. octavo setup installs it'))
        return 1
    fd, path = tempfile.mkstemp(prefix='octavo-r-editor-', suffix='.R')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            fh.write(R_EDITOR_SCRIPT)
        ok = _call([rscript, path], Path.home(),
                   shown='Rscript <install.packages("languageserver") into R_LIBS_USER>')
    finally:
        os.unlink(path)
    _say(t('languageserver is in your own R library. In VS Code, add that library to the R '
           'extension\'s r.libPaths so renv projects find it too.') if ok
         else t('Could not install languageserver (see above).'))
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
        return _call([rscript, path], root,
                     shown='Rscript <renv::init() / restore(), then ' + ', '.join(R_NEEDS) + '>')
    finally:
        os.unlink(path)


def pending(cfg) -> bool:
    """この分析の環境がまだ整っていないか（`.venv` か、R の分析なら renv がない）。
    拡張機能が「初めての分析」のあとに `octavo env` を走らせるかどうかの判断に使う。"""
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
