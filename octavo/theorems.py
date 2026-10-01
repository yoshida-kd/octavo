# -*- coding: utf-8 -*-
"""事例・論点などのブロックと、その再掲・一覧。

原稿の書き方:

    ::: {.question #question-why title="政府が担い手なのはなぜか"}
    なぜ政府が公共政策の中心的な担い手となっているのか.
    :::

    ::: {.restate #question-why}        <- 同じブロックをここにもう一度（元の番号で）
    :::

    ::: {.list-of .question}            <- 論点の一覧（本文つき）。`.titles` で題だけ
    :::

番号は図表と同じ仕組み（crossref.number）で振り、参照は `@question-why`（「論点2.1」）。
どの種類があるかは crossref.theorem_envs。

**定義は1か所、出力は何度でも**: 再掲と一覧は、原稿の複製を持たずに、組むたびに
元のブロックの中身をそこへ写す。写すのは前処理の早い段階（数値の埋め込みの後、
参照の置き換えの前）なので、写した本文の中の `@fig-…` も普通に解決される。
形式ごとの見た目は Backend.fmt_theorem / fmt_restate。
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from . import crossref as xref

DIV_OPEN = xref.DIV_OPEN
DIV_CLOSE = re.compile(r'^:{3,}\s*$')
FENCE = re.compile(r'^\s*(```+|~~~+)')
RESTATED = 'octavo-restated'


@dataclass
class Block:
    env: xref.Env
    label: str | None
    title: str
    body: str
    item: xref.Item | None = None     # 文書全体で数えた番号（番号のない種類は None）


def _divs(lines: list, want) -> list:
    """[(開きの行, 閉じの行, 属性)] — want(クラス) が真の div だけ、いちばん外側のもの。"""
    out = []
    fence = None
    stack: list = []          # [(開きの行, 属性 or None)]
    for i, line in enumerate(lines):
        if '\n' in line:
            # 図・表の差し替えで1つの行に入った複数行（```{=typst} … ```）。囲みの開け閉め
            # だけ数えて、div の開き・閉じとしては見ない
            for sub in line.split('\n'):
                f = FENCE.match(sub)
                if f:
                    mark = f.group(1)[0] * 3
                    fence = mark if fence is None else (None if mark == fence else fence)
            continue
        f = FENCE.match(line)
        if f:
            mark = f.group(1)[0] * 3
            fence = mark if fence is None else (None if mark == fence else fence)
            continue
        if fence:
            continue
        m = DIV_OPEN.match(line.strip())
        if m and not DIV_CLOSE.match(line.strip()):
            attr = xref.div_attr(m)
            hit = want(xref.div_classes(attr), attr)
            inside = any(a is not None for _, a in stack)
            stack.append((i, attr if hit and not inside else None))
            continue
        if DIV_CLOSE.match(line.strip()) and stack:
            start, attr = stack.pop()
            if attr is not None:
                out.append((start, i, attr))
    return out


def collect(sources: list, envs: dict, mode: str, start: int = 1) -> list:
    """文書全体（本文と付録）のブロック [Block]、文書の順。

    sources は [(本文の Markdown, 付録か)]。番号は crossref.number で数える
    （組版側と同じ数え方）。
    """
    out = []
    for text, is_app in sources:
        nums = xref.number(text, mode, appendix=is_app, start=start, envs=envs)
        by_line = {it.line: it for it in nums.items if it.kind in envs}
        lines = text.split('\n')
        for s, e, attr in _divs(lines, lambda cls, a: xref.theorem_env(a, envs) is not None):
            env = xref.theorem_env(attr, envs)
            out.append(Block(env, xref.label_in(attr, env.name),
                             xref.attr_value(attr, 'title') or '',
                             '\n'.join(lines[s + 1:e]), by_line.get(s)))
    return out


def _strip_labels(body: str) -> str:
    """写した本文から図表・式のラベルを外す（同じラベルが2つにならないように）。"""
    return re.sub(r'#(?:fig|tbl|eq|sec)-[A-Za-z0-9_-]+', '', body)


def expand(md: str, blocks: list, envs: dict, report: list | None = None) -> str:
    """`::: {.restate #x}` と `::: {.list-of …}` を、元のブロックの写しに置き換える。

    写しは `::: {.octavo-restated n=<番号> [short=1]}` の div（本文つき）になり、
    render が形式ごとの見た目にする。
    """
    lines = md.split('\n')
    spots = _divs(lines, lambda cls, a: 'restate' in cls or 'list-of' in cls)
    if not spots:
        return md
    by_label = {b.label: i for i, b in enumerate(blocks) if b.label}
    missing = []
    for s, e, attr in reversed(spots):
        cls = xref.div_classes(attr)
        if 'restate' in cls:
            m = re.search(r'#([\w.:-]+)', attr)
            idx = by_label.get(m.group(1)) if m else None
            if idx is None:
                missing.append(m.group(1) if m else '?')
                rep = []
            else:
                rep = [idx]
            short = False
        else:
            kinds = [c for c in cls if c in envs]
            rep = [i for i, b in enumerate(blocks)
                   if (b.env.name in kinds if kinds else b.env.counter)]
            short = 'titles' in cls
        chunks = []
        for i in rep:
            b = blocks[i]
            chunks += [f'::: {{.{RESTATED} n={i}{" short=1" if short else ""}}}',
                       '' if short else _strip_labels(b.body), ':::', '']
        lines[s:e + 1] = chunks or ['']
    if missing and report is not None:
        from .i18n import t, tag
        report.append(f'{tag("crossref")} ' + t(
            'nothing to restate for {names} (no block with that label)',
            names=', '.join('#' + x for x in missing)))
    return '\n'.join(lines)


def render(lines: list, items_by_line: dict, blocks: list, envs: dict,
           backend, ctx) -> list:
    """ブロックと写しの div を、形式ごとの見た目に置き換える（lines は行の並び。
    差し替えた後も行の数は変えない — 図・表の差し替えと同じ持ち回り）。"""
    def want(cls, attr):
        return RESTATED in cls or xref.theorem_env(attr, envs) is not None
    for s, e, attr in reversed(_divs(lines, want)):
        cls = xref.div_classes(attr)
        body = '\n'.join(lines[s + 1:e])
        if RESTATED in cls:
            b = blocks[int(xref.attr_value(attr, 'n'))]
            out = backend.fmt_restate(b.env, b.item, b.title, body, ctx,
                                      short=xref.attr_value(attr, 'short') == '1')
        else:
            env = xref.theorem_env(attr, envs)
            out = backend.fmt_theorem(env, items_by_line.get(s),
                                      xref.attr_value(attr, 'title') or '', body, ctx)
        lines[s] = out
        for j in range(s + 1, e + 1):
            lines[j] = ''
    return lines
