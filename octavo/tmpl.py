# -*- coding: utf-8 -*-
"""ひな型（テンプレート）を探す。**同梱のものは利用者が上書きできる前提。**

同じ相対パス（`slides/typst-slides.typ`、`paper/ja/main.typ` …）で、次の順に探す。

  1. プロジェクト  `<プロジェクト>/templates/`   そのプロジェクトだけに効く
  2. ユーザー      `$XDG_CONFIG_HOME/octavo/templates/`（既定 `~/.config/octavo/templates/`）
                   その人の全プロジェクトに効く
  3. 同梱          Octavo に付いてくるもの（paths.templates_dir()）

上書きは**丸ごと差し替え**で、差分を当てる仕組みではない。同梱のものを写して
直し始めるのが `octavo template copy`、どれが効いているかを見るのが
`octavo template list`、Octavo を更新したあとに同梱の側で何が変わったかを見るのが
`octavo template diff`。

`octavo init` はまだプロジェクトが無いので 2 と 3 だけを見る。プロジェクトの
ひな型（`project/…`）は**木ごと**重ねるので、ユーザーの側に足したファイル
（`project/ja/notes/reading/README.md` など）はそのまま新しいプロジェクトに入る。

ここを通さずに `templates_dir() / …` を直に読むと上書きが効かなくなる。
"""
from __future__ import annotations

import os
from pathlib import Path, PurePosixPath

from .paths import templates_dir

PROJECT, USER, BUNDLED = 'project', 'user', 'bundled'

# 同梱の templates/ の直下にあるが、ひな型ではないもの（説明書き）。
# `project/ja/README.md` などはひな型なので、直下のものだけを除く。
NOT_TEMPLATES = {'README.md'}


class TemplateError(Exception):
    pass


def user_dir() -> Path:
    base = os.environ.get('XDG_CONFIG_HOME') or (Path.home() / '.config')
    return Path(base) / 'octavo' / 'templates'


def project_dir(root: Path) -> Path:
    return Path(root) / 'templates'


def layers(root: Path | None = None) -> list:
    """[(層の名前, フォルダ)] を優先度の高い順に。"""
    out = []
    if root is not None:
        out.append((PROJECT, project_dir(root)))
    out.append((USER, user_dir()))
    out.append((BUNDLED, templates_dir()))
    return out


def check_name(rel: str) -> str:
    """利用者が打った相対パスを確かめて、`/` 区切りに揃えて返す。"""
    p = PurePosixPath(rel.replace('\\', '/'))
    if p.is_absolute() or '..' in p.parts or not p.parts:
        raise TemplateError(rel)
    return p.as_posix()


def resolve(rel: str, root: Path | None = None) -> tuple:
    """(層の名前, 実際のパス)。どの層にも無ければ TemplateError。"""
    rel = check_name(rel)
    for name, d in layers(root):
        p = d / rel
        if p.is_file():
            return name, p
    raise TemplateError(rel)


def find(rel: str, root: Path | None = None) -> Path:
    return resolve(rel, root)[1]


def read(rel: str, root: Path | None = None) -> str:
    return find(rel, root).read_text(encoding='utf-8')


def bundled_names() -> list:
    """同梱のひな型の相対パス（`/` 区切り）を並べて返す。"""
    base = templates_dir()
    names = (p.relative_to(base).as_posix() for p in base.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts)
    return sorted(n for n in names if n not in NOT_TEMPLATES)


def tree(prefixes, root: Path | None = None) -> dict:
    """prefix の下のファイルを全層から集める。{prefix からの相対パス: 実際のパス}。

    同じ相対パスなら優先度の高い層が勝つ。prefix を複数渡すと後ろのものが勝つ
    （`project/common` の上に `project/ja` を重ねる、の順）。
    """
    out: dict = {}
    for prefix in prefixes:
        for _, d in reversed(layers(root)):          # 低い層から重ねる
            base = d / prefix
            if not base.is_dir():
                continue
            for p in sorted(base.rglob('*')):
                if p.is_file() and '__pycache__' not in p.parts:
                    out[p.relative_to(base).as_posix()] = p
    return out


def overrides(root: Path | None = None) -> list:
    """上書きしているもの。[(相対パス, 層の名前, パス)]。

    同梱に無い名前（プロジェクトのひな型に足したファイルなど）も含める。
    """
    out = []
    for name, d in layers(root)[:-1]:
        if not d.is_dir():
            continue
        for p in sorted(d.rglob('*')):
            rel = p.relative_to(d).as_posix()
            if p.is_file() and rel not in NOT_TEMPLATES:
                out.append((rel, name, p))
    return out
