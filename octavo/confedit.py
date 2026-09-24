# -*- coding: utf-8 -*-
"""`octavo config` — 画面から変えられる設定の一覧と、その書き換え。

VS Code のアクティビティバーの「設定」はこれの薄い窓口（bib.ts と同じ方針）。
**どの鍵を画面に出すか・どう入力させるか・値として正しいか**は全部ここで決め、
拡張は `octavo config --json` の結果を並べて、選ばれた値を `octavo config set`
に渡すだけ。

`octavo.config.py` は手で書く Python なので、書き換えは慎重にやる:

  * 書き換えるのは `CONFIG = {` 直下（4字下げ）の **1行で書かれた** `'鍵': 値,`
    だけ。行末のコメントは残す。複数行にまたがる値は触らずに断る
  * 無ければ `CONFIG` の閉じ括弧の直前に1行足す（コメントアウトされた見本は
    そのまま残す）
  * 書く前に、書き換えた中身を**実際に設定として読んで**検証する。通らなければ
    ファイルは変えない（Config の検査がそのまま効く）
  * unset はその1行を消す（既定値に戻る）

ここに無い鍵（documents・analysis・フォントの並びなど）は、構造が大きく画面で
選ばせる意味が薄いので、`octavo.config.py` を手で直す。
"""
from __future__ import annotations

import ast
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from . import config as configmod
from .i18n import t


@dataclass(frozen=True)
class Knob:
    key: str
    section: str        # 'document' | 'slides' | 'limits'
    kind: str           # 'choice' | 'bool' | 'color' | 'int' | 'text'
    label: str          # 英語の原文（表示は t() を通す）
    choices: tuple = ()  # kind == 'choice' のとき。None は「使わない」


# 画面に出す設定。**並びもこの順で出る。**
KNOBS = (
    Knob('lang', 'document', 'choice', 'Language of the documents', ('ja', 'en')),
    Knob('csl', 'document', 'text', 'Citation style (CSL ID or alias)'),
    Knob('typst_slides_aspect', 'slides', 'choice', 'Aspect ratio', ('16-9', '4-3')),
    Knob('typst_slides_accent', 'slides', 'color', 'Accent colour'),
    Knob('typst_slides_running_header', 'slides', 'bool',
         'Section name in the top-left corner'),
    Knob('typst_slides_section_slides', 'slides', 'bool', 'Divider slide for each section'),
    Knob('typst_slides_numbering', 'slides', 'choice', 'Heading numbers',
         (None, '1.', '1.1')),
    Knob('word_limit', 'limits', 'int', 'Word limit (text)'),
    Knob('char_limit', 'limits', 'int', 'Character limit (text)'),
    Knob('abstract_word_limit', 'limits', 'int', 'Word limit (abstract)'),
    Knob('abstract_char_limit', 'limits', 'int', 'Character limit (abstract)'),
)
SECTIONS = {'document': 'Documents', 'slides': 'Slides', 'limits': 'Submission limits'}


class EditError(Exception):
    pass


def knob(key: str) -> Knob:
    for k in KNOBS:
        if k.key == key:
            return k
    raise EditError(t('{key} cannot be changed from here — edit octavo.config.py',
                      key=key))


def parse_value(k: Knob, raw: str):
    """コマンド行の文字列を、その設定の型の値にする。

    `ast.literal_eval` に任せないのは、`16-9` が 7 になるから。
    """
    s = raw.strip()
    if s.lower() in ('none', 'null', ''):
        if k.kind in ('color', 'int') or (k.kind == 'choice' and None in k.choices):
            return None
        raise EditError(t('{key} cannot be empty', key=k.key))
    if k.kind == 'bool':
        if s.lower() in ('true', 'yes', 'on', '1'):
            return True
        if s.lower() in ('false', 'no', 'off', '0'):
            return False
        raise EditError(t('{key} takes true or false', key=k.key))
    if k.kind == 'int':
        try:
            n = int(s.replace(',', ''))
        except ValueError:
            raise EditError(t('{key} takes a whole number', key=k.key))
        if n <= 0:
            raise EditError(t('{key} takes a whole number', key=k.key))
        return n
    if k.kind == 'choice' and s not in k.choices:
        shown = ' / '.join('None' if c is None else c for c in k.choices)
        raise EditError(t('{key} takes one of {allowed}', key=k.key, allowed=shown))
    return s


# ---------------------------------------------------------------- 読む
def show(cfg) -> list:
    """画面に並べるもの。値は**効いている値**（既定を含む）。"""
    rows = []
    for k in KNOBS:
        rows.append({
            'key': k.key,
            'section': k.section,
            'section_label': t(SECTIONS[k.section]),
            'label': t(k.label),
            'kind': k.kind,
            'choices': list(k.choices),
            'value': cfg[k.key],
            'default': configmod.DEFAULTS.get(k.key),
            'explicit': k.key in cfg.explicit,
        })
    return rows


# ---------------------------------------------------------------- 書く
def _line_re(key: str):
    # CONFIG 直下（4字下げ）の 1行の代入。行末コメントは group 'tail' に残す
    return re.compile(r"^    (['\"])" + re.escape(key) + r"\1\s*:\s*(?P<val>.*?)\s*,"
                      r"(?P<tail>\s*#.*)?$", re.M)


def _edit_text(text: str, key: str, value, remove: bool = False) -> str:
    m = _line_re(key).search(text)
    # 鍵の行はあるのに1行の形で読めない（値が次の行へ続く）なら、触らずに断る。
    # 見落とすと「書いていない」と判断して末尾にもう1つ足し、鍵が二重になる。
    head = re.search(r"^    (['\"])" + re.escape(key) + r"\1\s*:", text, re.M)
    if head and (not m or m.start() != head.start()):
        raise EditError(t('{key} spans several lines in octavo.config.py — edit it by '
                          'hand', key=key))
    if m:
        try:
            ast.literal_eval(m.group('val'))
        except (ValueError, SyntaxError):
            raise EditError(t('{key} spans several lines in octavo.config.py — edit it by '
                              'hand', key=key))
        if remove:
            start = m.start()
            end = text.find('\n', m.end())
            return text[:start] + (text[end + 1:] if end >= 0 else '')
        new = f"    '{key}': {value!r},{m.group('tail') or ''}"
        return text[:m.start()] + new + text[m.end():]
    if remove:
        return text                             # 書いていないなら既に既定
    # CONFIG の閉じ括弧（行頭の `}`）の直前に足す
    close = list(re.finditer(r'^\}\s*$', text, re.M))
    if not close:
        raise EditError(t('could not find the end of CONFIG in octavo.config.py'))
    at = close[-1].start()
    return text[:at] + f"    '{key}': {value!r},\n" + text[at:]


def _validate(path: Path, text: str) -> None:
    """書き換えた中身が設定として読めるかを、同じフォルダの一時ファイルで確かめる。"""
    fd, tmp = tempfile.mkstemp(prefix='.octavo-config-', suffix='.py', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            fh.write(text)
        try:
            configmod.load(tmp)
        except SystemExit as e:
            raise EditError(str(e.code) if e.code else t('the result is not a valid config'))
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def set_value(path: Path, key: str, raw: str | None) -> object:
    """鍵を書き換える。raw が None なら消す（既定に戻す）。書いた値を返す。"""
    k = knob(key)
    text = path.read_text(encoding='utf-8')
    if raw is None:
        new = _edit_text(text, key, None, remove=True)
        value = configmod.DEFAULTS.get(key)
    else:
        value = parse_value(k, raw)
        new = _edit_text(text, key, value)
    if new == text:
        return value
    _validate(path, new)
    path.write_text(new, encoding='utf-8')
    return value
