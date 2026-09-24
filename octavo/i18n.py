# -*- coding: utf-8 -*-
"""表示する文字列の言語。

**コードに直接書く文字列は英語**で、日本語は `lang_ja.py` の対訳表に置く。
表示するときは `t()` を通す:

    from .i18n import t
    print(t('Built {n} files', n=len(made)))

言語の決め方は上から順に、最初に見つかったもの:

    OCTAVO_LANG=ja / en        明示（`ja` で始まれば日本語、それ以外は英語）
    LC_ALL / LC_MESSAGES / LANG  ロケール（`ja` で始まれば日本語）
    どれも無ければ英語

**訳が無ければ英語のまま出る**（落ちない）。日本語で使うなら
`export OCTAVO_LANG=ja` を shell の設定に1行書いておくのが確実で、
ロケールが `en_US.UTF-8` のままの機械でも日本語で出る。

埋め込みは `{name}` の名前つきだけを見る。`str.format` を使わないのは、
文言に `{{n_obs}}` や `\\label{}` のような**本物の波括弧**が混じるため
（テンプレートで `str.format` を避けているのと同じ理由。scaffold.py 参照）。
対応する名前が渡されなかった `{…}` はそのまま素通りする。

ここで訳すのは **CLI が画面に出すものだけ**。`octavo init` が書き出す
CLAUDE.md や README、複製パッケージの README は「プロジェクトの言語」
（`octavo.config.py` の `lang`）で決まるもので、こことは別。
"""
from __future__ import annotations

import os
import re

# `{name}` だけを差し込み口として見る。`{{n_obs}}` のような**二重の波括弧は
# 文字どおり**（原稿に書く値の書き方を説明する文言に出てくる）。
_SLOT = re.compile(r'(?<!\{)\{(\w+)\}(?!\})')
# 英語の単数・複数: `{n|file|files}` は n が 1 なら file、それ以外は files。
# 形の中の `#` はその数になる（`{n|the one is|all # are}`）。日本語には要らないので、
# 訳は `{n}` だけを使えばよい。
_PLURAL = re.compile(r'(?<!\{)\{(\w+)\|([^{}|]*)\|([^{}|]*)\}(?!\})')


def _count(v):
    """差し込む値を数として読む。'1,523' のような書式済みの文字列も受ける。"""
    if isinstance(v, int):
        return v
    try:
        return int(str(v).replace(',', ''))
    except ValueError:
        return None


def _plural(m: re.Match, kw: dict) -> str:
    name, one, other = m.groups()
    if name not in kw:
        return m.group(0)
    form = one if _count(kw[name]) == 1 else other
    return form.replace('#', str(kw[name]))


def _pick() -> str:
    """環境から言語を決める。返すのは 'ja' か 'en'。"""
    explicit = os.environ.get('OCTAVO_LANG')
    if explicit:
        return 'ja' if explicit.lower().startswith('ja') else 'en'
    for var in ('LC_ALL', 'LC_MESSAGES', 'LANG'):
        v = os.environ.get(var)
        if v:
            return 'ja' if v.lower().startswith('ja') else 'en'
    return 'en'


def language() -> str:
    """いま使う言語。**毎回環境を見る**（テストが差し替えられるように）。"""
    return _pick()


def catalog(lang: str | None = None) -> dict:
    if (lang or language()) != 'ja':
        return {}
    from .lang_ja import MESSAGES
    return MESSAGES


def tag(name: str) -> str:
    """レポート行の頭に付く `[図]` `[組版]` のような印。

    **印も訳す**（日本語で読むなら `[figure]` では意味が無い）。そのぶん
    自分の出力を読み返す側（selftest の `[中止]` 判定など）は、文字列を
    書かずに必ずこの関数を通すこと。VS Code の problemMatcher は拡張側に
    あって呼べないので、あちらは両方の言語を並べて書いてある。
    """
    return t(f'[{name}]')


def t(s: str, **kw) -> str:
    """表示用の文字列。訳が無ければ英語のまま返す。"""
    out = catalog().get(s, s)
    if not kw:
        return out
    out = _PLURAL.sub(lambda m: _plural(m, kw), out)
    return _SLOT.sub(lambda m: str(kw[m.group(1)]) if m.group(1) in kw else m.group(0),
                     out)
