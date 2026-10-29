# -*- coding: utf-8 -*-
"""原稿の「1文1行」を見張り、直す。

    octavo check lint     文の途中で改行している所を知らせる
    octavo fmt            既存の原稿を1文1行に直す（既定は差分を見せるだけ。--apply で書く）

直す相手は**地の文だけ**。表・見出し・コード・`:::` の囲み・HTML のコメント・数式・
front matter・箇条書きの印・字下げは、そのまま。

- 文の途中の改行（行末が文末でなく、次の行が同じ段落の続き）は、つなぐ。
  和文どうしは空白を入れず、欧文が絡むときは空白1つ
- 和文は、行の途中の「。」の後ろでも改行する（括弧・かぎ括弧の中は文の途中なので切らない）。
  欧文は略語（e.g. や Fig. 2）と文末を見分けられないので切らない
- 行末が半角空白2つ以上かバックスラッシュ（書き手が入れた強制改行）は、つながない
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from . import md as mdlib

END = '。．.!?！？…'
CLOSERS = '」』）)"\'”’】〕］]*_`~'
OPEN_BR = '「『（(［[【〔'
CLOSE_BR = '」』）)］]】〕'
TRAIL = re.compile(r'(?:\s*(?:\[[^\]]*\]|\{[^}]*\}|\^\[[^\]]*\]))+\s*$')
LIST_MARK = re.compile(r'^\s*(?:[-*+]|\d+[.)])\s')
BLOCK_START = re.compile(
    r'^\s*(?:#{1,6}(?:\s|$)|:{3,}|\||>|<|\\|:\s|\[\^[^\]]+\]:|\{#|\[[-A-Za-z0-9_]+\]:\s|'
    r'(?:-{3,}|={3,}|\*{3,}|_{3,})\s*$)')


def is_wide(ch: str) -> bool:
    return '　' <= ch <= '鿿' or '＀' <= ch <= '￯'


def ends_sentence(line: str) -> bool:
    s = line.rstrip()
    s = TRAIL.sub('', s)
    s = s.rstrip(CLOSERS)
    return bool(s) and s[-1] in END


def _kind(line: str) -> str:
    """'blank' | 'block' | 'item' | 'text'。"""
    if not line.strip():
        return 'blank'
    if BLOCK_START.match(line):
        return 'block'
    if LIST_MARK.match(line):
        return 'item'
    return 'text'


def _hard_break(line: str) -> bool:
    return line.endswith('  ') or line.rstrip().endswith('\\')


def _frozen(lines: list) -> set:
    """触らない行（0 始まり）: コード、数式、HTML のコメント。"""
    out, fence, math = set(), None, False
    in_comment = False
    for i, line in enumerate(lines):
        f = mdlib.FENCE_LINE.match(line)
        if f:
            fence = None if fence == f.group(1) else (fence or f.group(1))
            out.add(i)
            continue
        if fence:
            out.add(i)
            continue
        if in_comment:
            out.add(i)
            if '-->' in line:
                in_comment = False
            continue
        if '<!--' in line and '-->' not in line.split('<!--', 1)[1]:
            in_comment = True
            out.add(i)
            continue
        if line.strip().startswith('$$') or math:
            out.add(i)
            if line.count('$$') == 1:
                math = not math
            elif line.strip() == '$$':
                math = not math
            continue
    return out


def _body_start(text: str) -> int:
    """front matter を除いた本文の最初の行（0 始まり）。"""
    _, body = mdlib.split_front_matter(text)
    return text[:len(text) - len(body)].count('\n')


@dataclass
class Wrap:
    line: int            # 1 始まり。ここの行末が文の途中
    excerpt: str


def _joinable(lines: list, i: int, frozen: set) -> bool:
    """i 行目の行末の改行が、文の途中のものか。"""
    if i + 1 >= len(lines) or i in frozen or i + 1 in frozen:
        return False
    a, b = lines[i], lines[i + 1]
    ka, kb = _kind(a), _kind(b)
    if ka not in ('text', 'item') or kb != 'text':
        return False
    if _hard_break(a) or ends_sentence(a):
        return False
    # 見出しの下線（---）や表の区切りでなく、続きの文であること
    return True


def wrapped(text: str) -> list:
    """文の途中で改行している行 [Wrap]。"""
    lines = text.split('\n')
    start = _body_start(text)
    frozen = _frozen(lines)
    out = []
    for i in range(start, len(lines) - 1):
        if _joinable(lines, i, frozen):
            out.append(Wrap(i + 1, lines[i].strip()[:60]))
    return out


def split_sentences(line: str) -> list:
    """和文の1行を「。」で切る。括弧・かぎ括弧の中、インラインコードの中は切らない。"""
    parts, depth, buf, tick = [], 0, '', False
    i = 0
    while i < len(line):
        ch = line[i]
        buf += ch
        if ch == '`':
            tick = not tick
        elif not tick:
            if ch in OPEN_BR:
                depth += 1
            elif ch in CLOSE_BR:
                depth = max(0, depth - 1)
            elif ch == '。' and depth == 0:
                j = i + 1
                while j < len(line) and line[j] in CLOSE_BR + '*_':
                    buf += line[j]
                    j += 1
                # 文末の引用 [@key] / 脚注 ^[…] / 属性 {…} は前の文に付ける
                m = re.match(r'(?:\s*(?:\[[^\]]*\]|\^\[[^\]]*\]|\{[^}]*\}))+', line[j:])
                if m:
                    buf += m.group(0)
                    j += m.end()
                rest = line[j:]
                if rest.strip() and is_wide(rest.lstrip()[0]) or (rest.strip() and rest.lstrip()[0].isalnum()):
                    parts.append(buf.rstrip())
                    buf = ''
                    while j < len(line) and line[j] == ' ':
                        j += 1
                i = j - 1
        i += 1
    if buf.strip():
        parts.append(buf.rstrip())
    return parts or [line]


def rewrap(text: str, split: bool = True) -> str:
    """1文1行に直した原稿。"""
    lines = text.split('\n')
    start = _body_start(text)
    frozen = _frozen(lines)
    out: list = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if i < start or i in frozen:
            out.append(line)
            i += 1
            continue
        k = _kind(line)
        cur = line
        # つなぐ
        while k in ('text', 'item') and _joinable(lines, i, frozen) and not _hard_break(cur):
            nxt = lines[i + 1].strip()
            a = cur.rstrip()
            sep = '' if (is_wide(a[-1:] or ' ') or is_wide(nxt[:1] or ' ')) else ' '
            cur = a + sep + nxt
            i += 1
        if split and k == 'text' and not _hard_break(cur):
            out.extend(split_sentences(cur))
        else:
            out.append(cur)
        i += 1
    return '\n'.join(out)
