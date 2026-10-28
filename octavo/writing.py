# -*- coding: utf-8 -*-
"""文章の決まり（ルール）とフレーズバンク。AI に渡して、それに沿って書かせるためのもの。

    octavo writing           どのファイルを読めばよいかの一覧（AI はこれを見て読む）
    octavo writing --json    同じものを機械可読で

置き場所は2つ。同じ名前のファイルがあればプロジェクトのほうを使う:

  1. プロジェクト   <プロジェクト>/writing/
  2. 自分の全部     $XDG_CONFIG_HOME/octavo/writing/（既定 ~/.config/octavo/writing/）

その下に rules/*.md（ルール）と phrases/*.md（フレーズバンク）。どちらも Markdown で、
冒頭に任意で title / lang（ja・en）/ applies（paper・slides・lecture・poster・all）を書き、
1つの項目を `## 見出し` 1つで書く:

  ルール       ## 規則の名前 の下に「規則:」「理由:」「良い例:」「悪い例:」の行
               （英語なら Rule: / Why: / Good: / Bad:。規則のほかは任意）
  フレーズ     ## 場面の名前 の下に、使ってよい表現を箇条書き（`- `）で。差し替える所は
               〈分野〉のように山括弧で。「場面:」「注意:」「出典:」の行は任意

Octavo は中身を解釈しない（AI がそのまま読む）。ここでするのは、どこにあるかと、
項目の数を数えることだけ。ルールを練るのは利用者（ほかのリポジトリでもよい）。
"""
from __future__ import annotations

import re
from pathlib import Path

from . import md as mdlib
from . import tmpl

KINDS = ('rules', 'phrases')


def user_dir() -> Path:
    return tmpl.user_dir().parent / 'writing'


def files(root: Path) -> dict:
    """{'rules': [(Path, 'project'|'user')], 'phrases': […]}。プロジェクトが同じ名前を上書きする。"""
    out: dict = {}
    for kind in KINDS:
        found: dict = {}
        for where, base in (('user', user_dir()), ('project', Path(root) / 'writing')):
            d = base / kind
            if d.is_dir():
                for p in sorted(d.glob('*.md')):
                    if p.name.lower() != 'readme.md':
                        found[p.name] = (p, where)
        out[kind] = [found[k] for k in sorted(found)]
    return out


def describe(path: Path) -> dict:
    """1つのファイルの title / lang / applies と、項目（`## 見出し`）の数。"""
    text = mdlib.read(path)
    meta, body = mdlib.split_front_matter(text)
    applies = meta.get('applies') or ['all']
    if isinstance(applies, str):
        applies = [x.strip() for x in applies.strip('[]').split(',') if x.strip()]
    body = re.sub(r'^```.*?^```', '', body, flags=re.S | re.M)
    return {'path': str(path), 'title': meta.get('title') or path.stem,
            'lang': meta.get('lang') or '', 'applies': applies,
            'entries': len(re.findall(r'^##\s+\S', body, re.M))}


def collect(root: Path) -> dict:
    return {kind: [{**describe(p), 'where': where} for p, where in found]
            for kind, found in files(root).items()}
