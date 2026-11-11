# -*- coding: utf-8 -*-
"""日本語の文献の形（japanese_citation_form）。参考文献の一覧の1件をどう組むか。

形は templates/citations/japanese-forms.json に部品ごとに書いてある（組み込みは standard /
fullwidth / period）。プロジェクトの octavo.config.py の japanese_citation_forms で、形を足したり、
組み込みの形の部品を変えたりできる（`base` に土台の形の名前、変えたい部品だけを書く）。
templates/ の上書きの決まり（プロジェクト → 利用者 → 同梱）で、JSON ごと置き換えてもよい。

部品は `{author}` のような差し込み口を持つ文字列。差し込む値がない部品は、まるごと出さない
（号のない論文に「号」だけが残らない）。組むのは citations/japanese.lua で、ここは形を集めて
フィルターに渡す（-M octavo-ja-<部品>=…）のと、設定の画面の見本を作るだけ。本文中の引用
（山田・田中 2020）は CSL の書式のままで、ここでは変えない。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import tmpl
from .i18n import t

FILE = 'citations/japanese-forms.json'

# 部品と、使える差し込み口
FIELDS = {
    'head': ('author', 'year'),          # 著者と年: 山田太郎・田中花子（2020）
    'article_title': ('title',),          # 論文・章の題: 「題」
    'book_title': ('title',),             # 本の題: 『題』
    'container': ('container',),          # 載っている誌名・本: 『誌名』
    'editor': ('editor',),                # 編者: 中村六郎編
    'volume': ('volume',),                # 巻: 12巻 / 12
    'issue': ('issue',),                  # 号（巻のあと）: 3号 / (3)
    'issue_alone': ('issue',),            # 号（巻がないとき）
    'pages': ('pages',),                  # 論文の頁: 1–20頁
    'pages_sep': (),                      # 巻・号と頁のあいだ: 、 / ": "
    'chapter_pages': ('pages',),          # 章の頁（出版社のあと）: 、10–20頁
    'stop': (),                           # 1件の終わり: 。 / .
}
SLOT = re.compile(r'\{(\w+)\}')


class FormError(ValueError):
    pass


def _bundled(root) -> dict:
    return json.loads(tmpl.find(FILE, Path(root) if root else None).read_text(encoding='utf-8'))


def _resolve(raw: dict) -> dict:
    """base をたどって、どの形も部品がそろった辞書にする。"""
    out: dict = {}

    def one(name, seen=()):
        if name in out:
            return out[name]
        if name in seen:
            raise FormError(t('japanese_citation_forms: {name} is its own base', name=name))
        spec = raw[name]
        if not isinstance(spec, dict):
            raise FormError(t('japanese_citation_forms: {name} must be a dictionary', name=name))
        base = spec.get('base')
        if base is not None and base not in raw:
            raise FormError(t('japanese_citation_forms: the base of {name} ({base}) is not a form',
                              name=name, base=base))
        full = dict(one(base, (*seen, name))) if base else {}
        for k, v in spec.items():
            if k == 'base':
                continue
            if k not in FIELDS:
                raise FormError(t('japanese_citation_forms: {name} has an unknown part {part} '
                                  '(the parts: {parts})', name=name, part=k, parts=', '.join(FIELDS)))
            if not isinstance(v, str):
                raise FormError(t('japanese_citation_forms: {name}.{part} must be a string',
                                  name=name, part=k))
            bad = [s for s in SLOT.findall(v) if s not in FIELDS[k]]
            if bad:
                raise FormError(t('japanese_citation_forms: {name}.{part} cannot use {slot} '
                                  '(it can use: {slots})', name=name, part=k, slot='{' + bad[0] + '}',
                                  slots=', '.join('{' + s + '}' for s in FIELDS[k]) or '-'))
            full[k] = v
        missing = [k for k in FIELDS if k not in full]
        if missing:
            raise FormError(t('japanese_citation_forms: {name} lacks {parts} (give a base, or write them)',
                              name=name, parts=', '.join(missing)))
        out[name] = full
        return full

    for name in raw:
        one(name)
    return out


def forms(root, extra=None) -> dict:
    """{名前: 部品の辞書}。同梱（か上書き）の JSON に、設定の japanese_citation_forms を重ねる。"""
    shipped = _resolve(_bundled(root))
    if not extra:
        return shipped
    if not isinstance(extra, dict):
        raise FormError(t('japanese_citation_forms must be a dictionary of forms'))
    raw = dict(shipped)
    for name, spec in extra.items():
        if isinstance(spec, dict) and name in shipped and 'base' not in spec:
            spec = {**shipped[name], **spec}                  # 組み込みの形の部品だけを変える
        raw[name] = spec
    return _resolve(raw)


def of(cfg) -> dict:
    return forms(cfg.root, cfg['japanese_citation_forms'])


def fill(pattern: str, **slots) -> str:
    """差し込み口を埋める。値のない口が1つでもあれば ''（japanese.lua の fill と同じ）。"""
    if any(not slots.get(s) for s in SLOT.findall(pattern)):
        return ''
    return SLOT.sub(lambda m: slots[m.group(1)], pattern)


def sample(form: dict) -> str:
    """設定の画面に出す見本（論文1件）。組み方は japanese.lua と同じ。"""
    vol = fill(form['volume'], volume='12') + fill(form['issue'], issue='3')
    return (fill(form['head'], author='山田太郎・田中花子', year='2020')
            + fill(form['article_title'], title='題') + fill(form['container'], container='誌名')
            + vol + form['pages_sep'] + fill(form['pages'], pages='1–20') + form['stop'])


def meta_args(form: dict) -> list:
    """フィルターに渡すメタデータ（-M は文字列のまま渡り、前後の空白も残る）。"""
    out = []
    for k in FIELDS:
        out += ['-M', f'octavo-ja-{k.replace("_", "-")}={form[k]}']
    return out
