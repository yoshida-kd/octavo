# -*- coding: utf-8 -*-
"""同梱物（テンプレート・設定の見本・CSL キャッシュ）の置き場を答える。

入れ方が2通りあるので、**置き場を直に書かずに必ずここを通す**。

  * clone して使う（`setup.sh` + `~/.local/bin/octavo` のシンボリックリンク）
    -> リポジトリ直下の `templates/` `config.example.py` `setup.sh` `csl/`
  * pip / uv で入れる（`uv tool install octavo-kit`）
    -> wheel に取り込まれた `octavo/templates/` `octavo/config.example*.py`
       `octavo/setup.sh`（`octavo setup` が走らせる）。
       CSL のキャッシュは site-packages に書けないので利用者のキャッシュ領域。

どちらか一方しか存在しないので、分岐は「repo 直下にあればそれ、無ければ
パッケージの中」の一段だけ。`pip install -e .` は repo 側が当たる。
"""
from __future__ import annotations

import os
from pathlib import Path

PKG = Path(__file__).resolve().parent
REPO = PKG.parent


def _pick(name: str) -> Path:
    """repo 直下にあればそれ、無ければパッケージの中。"""
    local = REPO / name
    return local if local.exists() else PKG / name


def templates_dir() -> Path:
    """同梱のひな型の置き場。**読むときは tmpl.py を通す**（利用者の上書きが効くように）。"""
    return _pick('templates')


def example_config(lang: str = 'en') -> Path:
    """`config.example.py` / `config.example.ja.py`。"""
    return _pick('config.example.ja.py' if lang == 'ja' else 'config.example.py')


def is_clone() -> bool:
    """clone したリポジトリから動いているか（wheel にも setup.sh は入るので、
    `bin/octavo` と一緒にあるかで見分ける）。"""
    return (REPO / 'setup.sh').exists() and (REPO / 'bin' / 'octavo').exists()


def on_windows() -> bool:
    """Windows で直接動いているか（WSL の中は Linux）。テストが差し替えられるよう関数にしてある。"""
    return os.name == 'nt'


def setup_script() -> Path | None:
    """道具を入れるスクリプト。Windows では `setup.ps1`、それ以外は `setup.sh`。

    repo 直下か、wheel の中。どちらにも無ければ None。
    """
    p = _pick('setup.ps1' if on_windows() else 'setup.sh')
    return p if p.exists() else None


def csl_cache_dir() -> Path:
    """取ってきた `.csl` を貯める場所（**書き込む**）。

    clone して使っているなら従来どおりリポジトリ直下の `csl/`
    （`.gitignore` 済み）。pip で入れたときは site-packages に書けないので
    `$XDG_CACHE_HOME/octavo/csl`（既定 `~/.cache/octavo/csl`）。
    """
    if is_clone():
        return REPO / 'csl'
    base = os.environ.get('XDG_CACHE_HOME') or (Path.home() / '.cache')
    return Path(base) / 'octavo' / 'csl'
