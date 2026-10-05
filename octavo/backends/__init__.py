# -*- coding: utf-8 -*-
"""出力形式の登録所。

新しい形式を足すときは Backend を継承したクラスを作り、REGISTRY に足すだけ。
build.py と cli.py は REGISTRY しか見ない。
"""
from __future__ import annotations

from ..config import OUTPUTS, OUTPUT_OF, backend_of
from ..i18n import t
from .base import Backend, Ctx, PROFILES     # noqa: F401
from .beamer import BeamerBackend
from .docx import DocxBackend
from .latex import LatexBackend
from .typst import TypstBackend
from .typst_notes import TypstNotesBackend
from .typst_poster import TypstPosterBackend
from .typst_slides import TypstSlidesBackend

REGISTRY = {b.name: b for b in (
    LatexBackend(), TypstBackend(), BeamerBackend(), TypstSlidesBackend(),
    TypstNotesBackend(), TypstPosterBackend(), DocxBackend(),
)}

# 用途ごとの既定の出力形式（`octavo build` で --to を省いたとき）
# TeX は任意（setup.sh --with-tex）なので、既定は TeX 無しで出せる Typst。
PROFILE_DEFAULT_TARGETS = {
    'paper': ('typst',),
    'handout': ('typst',),
    'slides': ('typst-slides',),
    'poster': ('typst-poster',),
}

ALL = tuple(REGISTRY)


def get(name: str) -> Backend:
    """形式の名前（typst）か出力の名前（pdf）から Backend を引く。"""
    try:
        return REGISTRY[backend_of(name) or name]
    except KeyError:
        raise SystemExit(t('unknown output format: {name}', name=name) + '\n  '
                         + t('available: {names}', names=', '.join(OUTPUTS)))


def resolve_targets(spec: str | None, profile: str) -> list:
    """--to の文字列を形式名のリストにする。"""
    if not spec:
        return list(PROFILE_DEFAULT_TARGETS.get(profile, ('typst',)))
    if spec in ('all', 'ALL'):
        return list(ALL)
    if spec == 'print':
        return ['typst', 'docx']
    out = []
    for name in spec.replace(' ', '').split(','):
        if name:
            b = get(name).name          # 不明な名前ならここで落ちる。出力の名前は形式の名前に
            if b not in out:
                out.append(b)
    return out
