# -*- coding: utf-8 -*-
"""図・表・式・節のラベルと相互参照。

原稿は**番号を書かず、名前（ラベル）で指す**。番号は組版のときに振る。

    ## 分析 {#sec-analysis}

    推移を @fig-trend に、記述統計を @tbl-desc に示す。推定式は @eq-model。

    ![推移](../../figures/trend.png){#fig-trend}

    | 変数 | 平均 |
    |------|------|
    | x    | 1.2  |

    : 記述統計 {#tbl-desc}

    $$
    y_i = \\beta_0 + \\beta_1 x_i + \\varepsilon_i
    $$ {#eq-model}

書き方は Quarto と同じ（`fig-` / `tbl-` / `eq-` / `sec-` の頭で種類が決まる）。
`[-@fig-trend]` は番号だけ（「2.1」）。ラベルの名前は ASCII の英数字と `-` `_`
だけで、それ以外の文字で終わる — だから「@fig-trendに示す」の「に」は名前に入らない。

番号の振り方（`crossref_numbering`）は既定が 'section'（節ごと: 図2.1・式(2.1)）、
'document' なら通し番号。Typst と LaTeX は組版側に振らせ（体裁はテンプレートの
crossref.typ / crossref.tex）、Word は自分では振らないので**ここで数えた番号を
文字で入れる**。数え方は組版側と同じにしてある: 番号が付くのは、見出し（番号なし
`{.unnumbered}` / `{-}` を除く）、キャプションのある図、キャプションのある表、
ラベルのある別行の数式。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .i18n import t, tag

KINDS = ('fig', 'tbl', 'eq', 'sec')
_NAME = r'[A-Za-z0-9](?:[A-Za-z0-9_-]*[A-Za-z0-9])?'
LABEL = re.compile(r'#(?P<label>(?:fig|tbl|eq|sec)-' + _NAME + r')(?![\w-])')
# 本文の参照。`@fig-x` / `[@fig-x]`（どちらも「図2.1」）/ `[-@fig-x]`（「2.1」）。
# メールアドレスや引用キーの途中には当てない。直前が日本語なら当てる
# （「推定したのは@eq-modelで」。\w は日本語にも当たるので使わない）。
REF = re.compile(r'(?:\[(?P<short>-)?@(?P<blabel>(?:fig|tbl|eq|sec)-' + _NAME + r')\]'
                 r'|(?<![A-Za-z0-9_.@-])@(?P<label>(?:fig|tbl|eq|sec)-' + _NAME + r'))')

FENCE = re.compile(r'^\s*(```+|~~~+)')
HEADING = re.compile(r'^(?P<hash>#{1,6})[ \t]+(?P<title>.*?)'
                     r'(?:[ \t]*\{(?P<attr>[^}]*)\})?[ \t]*$')
# 段落に画像が1つだけ（pandoc がこれを図にする）
IMAGE = re.compile(r'^!\[(?P<alt>(?:[^\]\\]|\\.)*)\]\((?P<path>[^)\s]+)(?P<title>\s+"[^"]*")?\)'
                   r'(?:\{(?P<attr>[^}]*)\})?[ \t]*$')
# 表のキャプション（`: キャプション {#tbl-x}` / `Table: …`）
TABLE_CAPTION = re.compile(r'^(?:Table)?:[ \t]+(?P<cap>.*?)(?:[ \t]*\{(?P<attr>[^}]*)\})?[ \t]*$')
TABLE_ROW = re.compile(r'^\s*[|+]')
# 別行の数式の閉じ（`$$` か `… $$`）に付いたラベル
EQ_END = re.compile(r'^(?P<pre>.*?)\$\$[ \t]*\{(?P<attr>[^}]*)\}[ \t]*$')


@dataclass
class Item:
    kind: str                  # 'fig' | 'tbl' | 'eq' | 'sec'
    label: str | None          # 付いていなければ None（番号は振られる）
    number: str                # '2.1'、節なら '2'・'2.1'・'A'
    line: int                  # 原稿（渡したテキスト）の中の行番号
    appendix: bool = False
    level: int = 0             # 節の深さ（1 が最上位）
    external: bool = False     # 分析が書いた表（中身は tables/<名前> にある）


@dataclass
class Numbering:
    items: list = field(default_factory=list)

    def labels(self) -> dict:
        return {i.label: i for i in self.items if i.label}

    def duplicates(self) -> list:
        seen, dup = set(), []
        for i in self.items:
            if i.label and i.label in seen and i.label not in dup:
                dup.append(i.label)
            seen.add(i.label)
        return dup


def label_in(attr: str | None, kind: str | None = None) -> str | None:
    """`{#fig-x width=80%}` の中のラベル。kind を渡せばその種類のときだけ。"""
    if not attr:
        return None
    m = LABEL.search(attr)
    if not m:
        return None
    return m.group('label') if kind is None or m.group('label').startswith(kind + '-') else None


def unnumbered(attr: str | None) -> bool:
    return bool(attr) and bool(re.search(r'(?:^|\s)(?:\.unnumbered|-)(?:\s|$)', attr))


def _lines_outside_code(md: str):
    """(行番号, 行) をコードブロックと HTML コメントの外だけ。

    ひな型の説明コメントには `@fig-trend` のような見本が書いてある。それを
    参照として数えない（1行の中のコメントも消してから渡す）。
    """
    fence = None
    comment = False
    for i, line in enumerate(md.split('\n')):
        if comment:
            if '-->' in line:
                comment = False
            continue
        m = FENCE.match(line)
        if m:
            mark = m.group(1)[0] * 3
            if fence is None:
                fence = mark
            elif mark == fence:
                fence = None
            continue
        if fence is not None:
            continue
        line = re.sub(r'<!--.*?-->', '', line)
        if '<!--' in line:
            comment = True
            line = line[:line.index('<!--')]
            if not line.strip():
                continue
        yield i, line


def _is_table_neighbour(lines: list, i: int, step: int) -> bool:
    j = i + step
    while 0 <= j < len(lines) and not lines[j].strip():
        j += step
    return 0 <= j < len(lines) and bool(TABLE_ROW.match(lines[j]))


def top_level(md: str) -> int:
    """最上位の見出しの深さ。`#` があれば 1、無ければ `##` を最上位とみなす
    （build.preprocess の shift_headings と同じ決め方）。"""
    return 1 if re.search(r'^# \S', md, re.M) else 2


def number(md: str, mode: str = 'section', appendix: bool = False,
           top: int | None = None, section: int | None = None) -> Numbering:
    """文書の順に数える。

    mode      'section'（節ごと 2.1）か 'document'（通し 1, 2, …）
    appendix  付録のファイル（最上位の節が A, B, …）
    section   節の見出しが無い部分（講義の回ごとのデッキ）に使う節番号
    """
    top = top or top_level(md)
    lines = md.split('\n')
    out = Numbering()
    heads = [0] * 7
    counts = {'fig': 0, 'tbl': 0, 'eq': 0}

    def sec_part() -> str | None:
        if mode != 'section':
            return None
        if heads[1]:
            return chr(ord('A') + heads[1] - 1) if appendix else str(heads[1])
        return str(section) if section else None

    def fmt(n: int) -> str:
        s = sec_part()
        return f'{s}.{n}' if s else str(n)

    in_math = False
    for i, line in _lines_outside_code(md):
        s = line.strip()
        # 別行の数式（`$$` で始まり `$$` で終わる。1行でも複数行でも）
        if not in_math and s.startswith('$$'):
            rest = s[2:]
            if '$$' in rest:                      # 1行で閉じる
                m = EQ_END.match(s)
                lab = label_in(m.group('attr'), 'eq') if m else None
                if lab:
                    counts['eq'] += 1
                    out.items.append(Item('eq', lab, fmt(counts['eq']), i, appendix))
                continue
            in_math = True
            continue
        if in_math:
            if '$$' in s:
                in_math = False
                m = EQ_END.match(s)
                lab = label_in(m.group('attr'), 'eq') if m else None
                if lab:
                    counts['eq'] += 1
                    out.items.append(Item('eq', lab, fmt(counts['eq']), i, appendix))
            continue

        m = HEADING.match(line)
        if m:
            depth = len(m.group('hash')) - top + 1
            if depth < 1 or unnumbered(m.group('attr')):
                continue
            heads[depth] += 1
            for d in range(depth + 1, 7):
                heads[d] = 0
            if depth == 1 and mode == 'section':
                counts = {k: 0 for k in counts}
            parts = [str(h) for h in heads[1:depth + 1]]
            if appendix:
                parts[0] = chr(ord('A') + heads[1] - 1)
            out.items.append(Item('sec', label_in(m.group('attr'), 'sec'), '.'.join(parts),
                                  i, appendix, level=depth))
            continue

        m = IMAGE.match(s)
        if m:
            lab = label_in(m.group('attr'), 'fig')
            if m.group('alt').strip() or lab:
                counts['fig'] += 1
                out.items.append(Item('fig', lab, fmt(counts['fig']), i, appendix))
            continue

        m = TABLE_CAPTION.match(s)
        if m and (s.startswith(':') or s.startswith('Table:')):
            lab = label_in(m.group('attr'), 'tbl')
            real = _is_table_neighbour(lines, i, -1) or _is_table_neighbour(lines, i, 1)
            if not real and not lab:
                continue                           # 表でも差し込みでもない行
            counts['tbl'] += 1
            out.items.append(Item('tbl', lab, fmt(counts['tbl']), i, appendix,
                                  external=not real))
    return out


def references(md: str) -> list:
    """本文の参照 [(ラベル, 番号だけか, 行番号)]。コードの中は見ない。"""
    out = []
    for i, line in _lines_outside_code(md):
        line = re.sub(r'`[^`\n]*`', '', line)
        for m in REF.finditer(line):
            lab = m.group('blabel') or m.group('label')
            out.append((lab, bool(m.group('short')), i))
    return out


def replace_references(md: str, known: dict, fmt, report: list | None = None) -> str:
    """本文の `@fig-x` を fmt(Item, short) の返す文字列に置き換える。

    知らないラベルは `??` にして報告する（組版を止めない。octavo check は止める）。
    """
    missing: list = []

    def one(m: re.Match) -> str:
        lab = m.group('blabel') or m.group('label')
        item = known.get(lab)
        if item is None:
            if lab not in missing:
                missing.append(lab)
            return '??'
        return fmt(item, bool(m.group('short')))

    out = md.split('\n')
    for i, line in _lines_outside_code(md):
        if not REF.search(line):
            continue
        # インラインコードの中は置き換えない（コメントは _lines_outside_code が外してある）
        whole = out[i]
        parts = re.split(r'(`[^`\n]*`|<!--.*?-->)', whole)
        out[i] = ''.join(p if p.startswith(('`', '<!--')) else REF.sub(one, p)
                         for p in parts)
    if report is not None and missing:
        report.append(f'{tag("crossref")} ' + t(
            'no such {n|label|labels}: {names} (written as ??)',
            n=len(missing), names=', '.join('@' + x for x in missing)))
    return '\n'.join(out)


def label_equations(md: str, tag_for=None) -> str:
    """`$$ … $$ {#eq-x}` を pandoc が読める形にする。

    既定はラベルを数式の中へ `\\label{eq-x}` として入れる（pandoc の Typst は
    `<eq-x>`、LaTeX は `\\label{}` にする）。tag_for(label) を渡すと、代わりに
    その文字列（Word の「(2.1)」）を式の右に置く。
    """
    out = []
    for i, line in enumerate(md.split('\n')):
        m = EQ_END.match(line.rstrip()) if '$$' in line and '{' in line else None
        lab = label_in(m.group('attr'), 'eq') if m else None
        if not lab:
            out.append(line)
            continue
        inside = (f' \\qquad {tag_for(lab)} ' if tag_for else f' \\label{{{lab}}} ')
        out.append(m.group('pre') + inside + '$$')
    return '\n'.join(out)


# ---------------------------------------------------------------- 参照の言葉

def words(lang: str) -> dict:
    """参照に付ける語。日本語は「図2.1」「第2節」、英語は「Figure 2.1」「Section 2」。"""
    if lang == 'ja':
        return {'fig': '図{n}', 'tbl': '表{n}', 'eq': '式{n}',
                'sec': '第{n}節', 'app': '付録{n}'}
    return {'fig': 'Figure {n}', 'tbl': 'Table {n}', 'eq': 'Equation {n}',
            'sec': 'Section {n}', 'app': 'Appendix {n}'}


def text_of(item: Item, lang: str, short: bool = False) -> str:
    """番号を文字で書いた参照（Word と、組版側に相手が無いとき）。"""
    n = f'({item.number})' if item.kind == 'eq' else item.number
    if short:
        return n
    key = 'app' if item.kind == 'sec' and item.appendix else item.kind
    return words(lang)[key].format(n=n)


def caption_head(kind: str, number: str, lang: str) -> str:
    """Word のキャプションの頭（「図2.1　」/「Figure 2.1. 」）。"""
    word = {'fig': ('図', 'Figure'), 'tbl': ('表', 'Table')}[kind]
    return f'{word[0]}{number}　' if lang == 'ja' else f'{word[1]} {number}. '


# ---------------------------------------------------------------- 検査（octavo check）

def collect(cfg) -> dict:
    """原稿ごとのラベルと参照を突き合わせる。

    missing    無いラベルへの参照（組むと ?? になる）        [(原稿:行, @label)]
    duplicate  同じラベルが2回                              [(原稿:行, #label)]
    unused     どこからも参照されていない図・表・式のラベル    [(原稿:行, #label)]

    論文の本文と付録は1つの文書として見る（互いに参照できる）。
    """
    from . import md as mdlib
    out = {'missing': [], 'duplicate': [], 'unused': []}
    by_doc: dict = {}
    for name, src, is_app in cfg.sources():
        by_doc.setdefault(name, []).append((src, is_app))
    for files in by_doc.values():
        labels: dict = {}
        refs: list = []
        for src, is_app in files:
            text = mdlib.read(src)
            where = cfg.rel(src)
            for it in number(text, cfg['crossref_numbering'], appendix=is_app).items:
                if not it.label:
                    continue
                if it.label in labels:
                    out['duplicate'].append((f'{where}:{it.line + 1}', '#' + it.label))
                else:
                    labels[it.label] = (it, f'{where}:{it.line + 1}')
            refs += [(f'{where}:{line + 1}', lab) for lab, _, line in references(text)]
        cited = set()
        for at, lab in refs:
            cited.add(lab)
            if lab not in labels:
                out['missing'].append((at, '@' + lab))
        for lab, (it, at) in labels.items():
            if it.kind != 'sec' and lab not in cited:
                out['unused'].append((at, '#' + lab))
    return out


def external_tables(cfg) -> list:
    """分析が書いた表の差し込み [(文書名, 原稿, 名前)]（`: 表題 {#tbl-名前}` だけの行）。"""
    from . import md as mdlib
    out = []
    for name, src, is_app in cfg.sources():
        for it in number(mdlib.read(src), cfg['crossref_numbering'], appendix=is_app).items:
            if it.external and it.label:
                out.append((name, src, it.label[len('tbl-'):]))
    return out
