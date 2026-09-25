# -*- coding: utf-8 -*-
"""プロジェクトの分析の環境（.venv と renv）を作る・揃える。

    octavo env

何度走らせても平気（あるものは作らず、足りないものだけ足す）。clone してきた
プロジェクトでは記録（requirements.txt / renv.lock）から環境を戻すことになる。

  Python  uv で `.venv` を作り、requirements.txt に書いたものを入れる
  R       renv を入れ（無ければ利用者のライブラリへ）、`renv::init()` か
          `renv::restore()`、quarto の knitr エンジンに要る knitr / rmarkdown を
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

# quarto が R の .qmd を render するのに要る（octavo.R 自体は素の R で動く）
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


def has_requirements(path: Path) -> bool:
    """コメントと空行以外が1行でもあるか（ひな型のままなら入れるものは無い）。"""
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
    """`.venv` を作って requirements.txt を入れる。uv が無ければ None（飛ばした）。"""
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
    """renv を用意して knitr / rmarkdown を入れる。R が無ければ None（飛ばした）。"""
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


def run(cfg) -> int:
    root = Path(cfg.root)
    results = [python_env(root), r_env(root)]
    if any(r is False for r in results):
        _say('\n' + t('Something failed (see above). Fix it and run octavo env again.'))
        return 1
    if all(r is None for r in results):
        _say('\n' + t('Neither uv nor R is installed. Run octavo setup first.'))
        return 1
    _say('\n' + t('The analysis environment is ready. Commit requirements.txt and renv.lock.'))
    return 0
