# -*- coding: utf-8 -*-
"""図・表・式・節のラベルと相互参照。

原稿は**番号を書かず、名前（ラベル）で指す**。番号は組版のときに振る。

    ## 分析 {#sec-analysis}

    推移を @fig-trend に、記述統計を @tbl-desc に示す。推定式は @eq-model。

    ![推移](../../assets/figures/trend.png){#fig-trend}

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

# ---------------------------------------------------------------- 事例・論点などのブロック
# `::: {.question #question-why title="…"}` … `:::`。ラベルの頭はクラス名。
# counter が同じものは番号を通しで振る（事例・論点は「事例1.1、論点1.2」）。
# counter が None のものは番号を付けない（参照もできない）。
THEOREMS = {
    'case':        ('事例', 'Case', 'case'),
    'question':    ('論点', 'Question', 'case'),
    'aside':       ('余談', 'Aside', None),
    'nb':          ('注意', 'Note', None),
    'memo':        ('付記', 'Addendum', None),
    'theorem':     ('定理', 'Theorem', 'theorem'),
    'lemma':       ('補題', 'Lemma', 'theorem'),
    'proposition': ('命題', 'Proposition', 'theorem'),
    'corollary':   ('系', 'Corollary', 'theorem'),
    'definition':  ('定義', 'Definition', 'theorem'),
    'example':     ('例', 'Example', 'theorem'),
    'remark':      ('注', 'Remark', None),
}


@dataclass(frozen=True)
class Env:
    name: str                  # クラス名（ラベルの頭）
    word: str                  # 見出し語（「論点」）
    counter: str | None        # 番号を共有する組の名前。None なら番号なし


def theorem_envs(cfg=None, lang: str | None = None) -> dict:
    """{クラス名: Env}。同梱の既定に config の theorem_envs を重ねる。

    config の書き方:  'case': '事例'（見出し語だけ変える）
                      'claim': {'name': '主張', 'counter': 'case'}（増やす・番号を共有）
                      'claim': {'name': {'ja': '主張', 'en': 'Claim'}, 'numbered': False}
    """
    lang = lang or (cfg['lang'] if cfg is not None else 'ja')
    ja = lang == 'ja'
    out = {k: Env(k, ja_w if ja else en_w, c) for k, (ja_w, en_w, c) in THEOREMS.items()}
    for k, v in ((cfg['theorem_envs'] or {}) if cfg is not None else {}).items():
        base = out.get(k)
        if isinstance(v, str):
            out[k] = Env(k, v, base.counter if base else k)
            continue
        v = dict(v or {})
        name = v.get('name', base.word if base else k)
        if isinstance(name, dict):
            name = name.get(lang) or name.get('en') or next(iter(name.values()))
        counter = v.get('counter', base.counter if base else k)
        if v.get('numbered') is False:
            counter = None
        out[k] = Env(k, str(name), counter)
    return out


def kinds_of(envs: dict | None = None) -> tuple:
    """参照できるラベルの頭（fig/tbl/eq/sec と、番号のあるブロックのクラス名）。"""
    envs = THEOREM_DEFAULT if envs is None else envs
    return KINDS + tuple(k for k, e in envs.items() if e.counter)


THEOREM_DEFAULT = {k: Env(k, ja, c) for k, (ja, _en, c) in THEOREMS.items()}


def _kind_alt(kinds) -> str:
    return '|'.join(sorted((re.escape(k) for k in kinds), key=len, reverse=True))


def _label_re(kinds) -> re.Pattern:
    return re.compile(r'#(?P<label>(?:' + _kind_alt(kinds) + r')-' + _NAME + r')(?![\w-])')


def _ref_re(kinds) -> re.Pattern:
    """本文の参照。`@fig-x` / `[@fig-x]`（どちらも「図2.1」）/ `[-@fig-x]`（「2.1」）。
    メールアドレスや引用キーの途中には当てない。直前が日本語なら当てる
    （「推定したのは@eq-modelで」。\\w は日本語にも当たるので使わない）。"""
    alt = _kind_alt(kinds)
    return re.compile(r'(?:\[(?P<short>-)?@(?P<blabel>(?:' + alt + r')-' + _NAME + r')\]'
                      r'|(?<![A-Za-z0-9_.@-])@(?P<label>(?:' + alt + r')-' + _NAME + r'))')


_RE_CACHE: dict = {}


def patterns(kinds=None) -> tuple:
    """(LABEL, REF) の正規表現。kinds を省くと既定のブロックまで。"""
    kinds = tuple(kinds or kinds_of())
    if kinds not in _RE_CACHE:
        _RE_CACHE[kinds] = (_label_re(kinds), _ref_re(kinds))
    return _RE_CACHE[kinds]


LABEL, REF = patterns()

FENCE = re.compile(r'^\s*(```+|~~~+)')
HEADING = re.compile(r'^(?P<hash>#{1,6})[ \t]+(?P<title>.*?)'
                     r'(?:[ \t]*\{(?P<attr>[^}]*)\})?[ \t]*$')
# 段落に画像が1つだけ（pandoc がこれを図にする）
# alt には角括弧が1段入ってよい（題に付けた脚注 `[^src]`、引用 `[@key]`）
IMAGE = re.compile(r'^!\[(?P<alt>(?:[^\[\]\\]|\\.|\[[^\[\]]*\])*)\]\((?P<path>[^)\s]+)(?P<title>\s+"[^"]*")?\)'
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
    word: str = ''             # 事例・論点などのブロックの見出し語
    title: str = ''            # ブロックの題（`title="…"`）


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
    if kind is not None:
        m = re.search(r'#(?P<label>' + re.escape(kind) + '-' + _NAME + r')(?![\w-])', attr)
        return m.group('label') if m else None
    m = LABEL.search(attr)
    return m.group('label') if m else None


def appendix_heading(attr: str | None) -> bool:
    """`# 論点集 {.appendix}` — ここから付録（節が A, B, …）。"""
    return bool(attr) and bool(re.search(r'(?:^|\s)\.appendix(?:\s|$)', attr))


DIV_OPEN = re.compile(r'^(:{3,})\s*(?:\{(?P<attr>[^}]*)\}|(?P<bare>[A-Za-z][\w-]*))\s*$')


def div_attr(m: re.Match) -> str:
    """`::: {.nb}` と `::: nb` を同じ属性の文字列（'.nb'）にする。"""
    return m.group('attr') if m.group('attr') is not None else '.' + m.group('bare')


def div_classes(attr: str) -> list:
    return re.findall(r'(?:^|\s)\.([A-Za-z][\w-]*)', attr)


# 再掲・一覧の div（クラスに論点などの名前を持つが、ブロックそのものではない）
NOT_BLOCKS = ('restate', 'list-of', 'octavo-restated')


def theorem_env(attr: str, envs: dict):
    """その div が事例・論点などのブロックなら Env、でなければ None。"""
    cls = div_classes(attr)
    if any(c in NOT_BLOCKS for c in cls):
        return None
    return next((envs[c] for c in cls if c in envs), None)


def attr_value(attr: str, key: str) -> str | None:
    """`title="なぜ…"` の値（引用符なしも可）。"""
    m = re.search(r'(?:^|\s)' + re.escape(key) + r'=(?:"((?:[^"\\]|\\.)*)"|\'([^\']*)\'|(\S+))',
                  attr)
    if not m:
        return None
    v = m.group(1) if m.group(1) is not None else (m.group(2) if m.group(2) is not None
                                                    else m.group(3))
    return v.replace('\\"', '"')


def unnumbered(attr: str | None) -> bool:
    return bool(attr) and bool(re.search(r'(?:^|\s)(?:\.unnumbered|-)(?:\s|$)', attr))


FIGURE_NOTE = 'figure-note'


def _block_start(lines: list, j: int) -> int:
    """j 行目を含む、空行で区切られた塊の最初の行。"""
    while j > 0 and lines[j - 1].strip():
        j -= 1
    return j


def figure_notes(lines: list) -> tuple:
    """図・表の直後の `::: {.figure-note}`（出典・注）。([(先頭, 開き, 閉じ, 'fig'|'tbl')], [離れた開きの行])。

    先頭は図なら画像の行、表なら表とキャプションの塊の最初の行。直前の塊が図でも表でも
    ない注は、2つ目の並びに入れる（ふつうの囲みとして組まれる）。
    """
    found, stray = [], []
    text = '\n'.join(lines)
    outside = {i for i, _ in _lines_outside_code(text)}
    i = 0
    while i < len(lines):
        if i not in outside:
            i += 1
            continue
        m = DIV_OPEN.match(lines[i].strip())
        if not (m and (m.group('bare') == FIGURE_NOTE
                       or FIGURE_NOTE in div_classes(m.group('attr') or ''))):
            i += 1
            continue
        depth, k = 1, i + 1
        while k < len(lines):
            st = lines[k].strip()
            if re.match(r'^:{3,}\s*$', st):
                depth -= 1
                if not depth:
                    break
            elif DIV_OPEN.match(st):
                depth += 1
            k += 1
        j = i - 1
        while j >= 0 and not lines[j].strip():
            j -= 1
        start, kind = None, None
        prev = lines[j].strip() if j >= 0 else ''
        if j >= 0 and IMAGE.match(prev):
            start, kind = j, 'fig'
        elif j >= 0 and (TABLE_CAPTION.match(prev) or TABLE_ROW.match(lines[j])):
            kind, start = 'tbl', _block_start(lines, j)
            above = _block_start(lines, start - 2) if start >= 2 and not lines[start - 1].strip() else None
            if above is not None:
                if TABLE_CAPTION.match(lines[start].strip()) and TABLE_ROW.match(lines[above]):
                    start = above                    # 表 / 空行 / キャプション
                elif TABLE_ROW.match(lines[start]) and above == start - 2 \
                        and TABLE_CAPTION.match(lines[above].strip()):
                    start = above                    # キャプション / 空行 / 表
        if start is None:
            stray.append(i)
        else:
            found.append((start, i, min(k, len(lines) - 1), kind))
        i = k + 1
    return found, stray


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
    """最上位の見出しの深さ。`#` があれば 1、なければ `##` を最上位とみなす
    （build.preprocess の shift_headings と同じ決め方）。"""
    return 1 if re.search(r'^# \S', md, re.M) else 2


def number(md: str, mode: str = 'section', appendix: bool = False,
           top: int | None = None, section: int | None = None, start: int = 1,
           envs: dict | None = None) -> Numbering:
    """文書の順に数える。

    mode      'section'（節ごと 2.1）か 'document'（通し 1, 2, …）
    appendix  付録のファイル（最上位の節が A, B, …）。`# 題 {.appendix}` の見出しから
              後ろも付録になる
    section   節の見出しがない部分（講義の回ごとのデッキ）に使う節番号
    start     最初の節の番号（講義のガイダンスを 0 にするなら 0）
    envs      事例・論点などのブロック（theorem_envs()）。省くと同梱の既定
    """
    top = top or top_level(md)
    envs = THEOREM_DEFAULT if envs is None else envs
    lines = md.split('\n')
    out = Numbering()
    heads = [0] * 7
    seen = False               # 最上位の節を1つでも過ぎたか（start が 0 だと番号が 0 になる）
    counts = {'fig': 0, 'tbl': 0, 'eq': 0}
    counts.update({e.counter: 0 for e in envs.values() if e.counter})

    def top_number() -> str:
        return (chr(ord('A') + heads[1] - 1) if appendix
                else str(heads[1] + start - 1))

    def sec_part() -> str | None:
        if mode != 'section':
            return None
        if seen:
            return top_number()
        return str(section) if section is not None else None

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
            if depth == 1 and appendix_heading(m.group('attr')) and not appendix:
                appendix = True
                heads = [0] * 7
            if depth < 1 or unnumbered(m.group('attr')):
                continue
            heads[depth] += 1
            for d in range(depth + 1, 7):
                heads[d] = 0
            if depth == 1:
                seen = True
                if mode == 'section':
                    counts = {k: 0 for k in counts}
            parts = [str(h) for h in heads[1:depth + 1]]
            parts[0] = top_number()
            out.items.append(Item('sec', label_in(m.group('attr'), 'sec'), '.'.join(parts),
                                  i, appendix, level=depth))
            continue

        m = DIV_OPEN.match(s)
        if m:
            attr = div_attr(m)
            env = theorem_env(attr, envs)
            if env is not None and env.counter:
                counts[env.counter] += 1
                out.items.append(Item(env.name, label_in(attr, env.name),
                                      fmt(counts[env.counter]), i, appendix,
                                      word=env.word, title=attr_value(attr, 'title') or ''))
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


AUTO_LABEL = 'octavo'          # 内部用のラベルの印（fig-octavo-1a2b3c4d）


def autolabel(md: str, envs: dict | None = None) -> str:
    """番号が付くのにラベルのないもの（キャプションのある図、表題のある表、番号の付く
    事例などのブロック）に、内部用のラベルを付ける。

    講義の回のデッキの番号を、プリントでの番号に合わせる（fixed_numbers）ために、
    プリントとデッキの両方で同じものを同じ名前で指せるようにする。名前は行の中身から
    作るので、どちらで組んでも同じになる（同じ行が2つあれば出てきた順の番号を足す）。
    行の数は変えない。
    """
    import hashlib
    envs = THEOREM_DEFAULT if envs is None else envs
    lines = md.split('\n')
    seen: dict = {}

    def name(kind: str, line: str) -> str:
        h = hashlib.sha1(line.strip().encode('utf-8')).hexdigest()[:8]
        seen[(kind, h)] = seen.get((kind, h), 0) + 1
        n = seen[(kind, h)]
        return f'{kind}-{AUTO_LABEL}-{h}' + (f'-{n}' if n > 1 else '')

    def with_label(line: str, attr, label: str, end: int | None = None) -> str:
        if attr is None:
            return line.rstrip() + '{#' + label + '}'
        return line.replace('{' + attr + '}', '{#' + label + (' ' + attr if attr.strip() else '') + '}', 1)

    for i, line in _lines_outside_code(md):
        s = line.strip()
        m = DIV_OPEN.match(s)
        if m:
            attr = div_attr(m)
            env = theorem_env(attr, envs)
            if env is not None and env.counter and not label_in(attr, env.name):
                lab = name(env.name, line)
                if m.group('attr') is None:
                    lines[i] = line.replace(m.group('bare'), '{.' + m.group('bare') + ' #' + lab + '}', 1)
                else:
                    lines[i] = with_label(line, m.group('attr'), lab)
            continue
        m = IMAGE.match(s)
        if m:
            if m.group('alt').strip() and not label_in(m.group('attr'), 'fig'):
                lines[i] = with_label(line, m.group('attr'), name('fig', line))
            continue
        m = TABLE_CAPTION.match(s)
        if m and (s.startswith(':') or s.startswith('Table:')) and not label_in(m.group('attr'), 'tbl'):
            if _is_table_neighbour(lines, i, -1) or _is_table_neighbour(lines, i, 1):
                lines[i] = with_label(line, m.group('attr'), name('tbl', line))
    return '\n'.join(lines)


def references(md: str, kinds=None) -> list:
    """本文の参照 [(ラベル, 番号だけか, 行番号)]。コードの中は見ない。

    再掲（`::: {.restate #question-why}`）の相手も参照として数える。
    """
    ref = patterns(kinds)[1]
    out = []
    for i, line in _lines_outside_code(md):
        m = DIV_OPEN.match(line.strip())
        if m and 'restate' in div_classes(div_attr(m)):
            lab = re.search(r'#(' + _NAME + ')', div_attr(m))
            if lab:
                out.append((lab.group(1), False, i))
            continue
        line = re.sub(r'`[^`\n]*`', '', line)
        for m in ref.finditer(line):
            lab = m.group('blabel') or m.group('label')
            out.append((lab, bool(m.group('short')), i))
    return out


def replace_references(md: str, known: dict, fmt, report: list | None = None,
                       kinds=None) -> str:
    """本文の `@fig-x` を fmt(Item, short) の返す文字列に置き換える。

    存在しないラベルは `??` にして報告する（組版を止めない。octavo check は止める）。
    """
    missing: list = []
    REF = patterns(kinds)[1]

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
    """番号を文字で書いた参照（Word と、組版側に相手がないとき）。"""
    n = f'({item.number})' if item.kind == 'eq' else item.number
    if short:
        return n
    if item.word:
        return f'{item.word}{n}' if lang == 'ja' else f'{item.word} {n}'
    key = 'app' if item.kind == 'sec' and item.appendix else item.kind
    return words(lang)[key].format(n=n)


def caption_head(kind: str, number: str, lang: str) -> str:
    """Word のキャプションの頭（「図2.1　」/「Figure 2.1. 」）。"""
    word = {'fig': ('図', 'Figure'), 'tbl': ('表', 'Table')}[kind]
    return f'{word[0]}{number}　' if lang == 'ja' else f'{word[1]} {number}. '


# ---------------------------------------------------------------- 検査（octavo check）

def collect(cfg) -> dict:
    """原稿ごとのラベルと参照を突き合わせる。

    missing    ないラベルへの参照・再掲（組むと ?? になる）  [(原稿:行, @label)]
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
        envs = theorem_envs(cfg)
        kinds = kinds_of(envs)
        for src, is_app in files:
            text = mdlib.read(src)
            where = cfg.rel(src)
            for it in number(text, cfg['crossref_numbering'], appendix=is_app,
                             envs=envs).items:
                if not it.label:
                    continue
                if it.label in labels:
                    out['duplicate'].append((f'{where}:{it.line + 1}', '#' + it.label))
                else:
                    labels[it.label] = (it, f'{where}:{it.line + 1}')
            refs += [(f'{where}:{line + 1}', lab) for lab, _, line in references(text, kinds)]
        cited = set()
        for at, lab in refs:
            cited.add(lab)
            if lab not in labels:
                out['missing'].append((at, '@' + lab))
        for lab, (it, at) in labels.items():
            if it.kind in ('fig', 'tbl', 'eq') and lab not in cited:
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
