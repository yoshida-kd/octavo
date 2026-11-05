# -*- coding: utf-8 -*-
"""段落の構成表: 段落の直前の `<!-- para: 種類 | 主張 -->` を読む。

    <!-- para: polisci/results#the-main-result | Divisions whose composition shifted more were redrawn more often -->
    Divisions whose composition of work had shifted more ...

- 種類は `パック/ファイル#見出しの slug`（`writing_off` と同じ書き方。`ファイル#slug` でもよい）。
  フレーズバンクの項目1つが段落の種類1つ。主張は1文。どちらも任意（`<!-- para: | 主張 -->` なら
  種類はまだ決めていない）
- コメントなので組版には届かない。本文がまだ無い段落もコメントだけで置ける（構成表を先に作るため）
- 本文の行のすぐ後に（空行を挟まずに）コメントを書くと、pandoc は前の段落とつないでしまう。
  `octavo outline --paragraphs` がそれを知らせる

ここでは原稿を段落に分けて、コメントと本文を対応させるだけ。種類が実在するかは
writing.py のパックと照らす（`kind_index`）。
"""
from __future__ import annotations

import difflib
import re

from . import md as mdlib

PARA_START = re.compile(r'^\s*<!--\s*para\s*:', re.I)
PARA = re.compile(r'<!--\s*para\s*:(.*?)-->', re.S | re.I)
POSITION = re.compile(r'^\s*[-*+]\s+(Open|Body|Close)\s*:\s*(.*)$', re.I)
ITEM = re.compile(r'^\s*[-*+]\s+(.*)$')
FIELD = re.compile(r'^(When|Note|Source|場面|注意|出典)\s*[:：]\s*(.*)$')
FIELD_NAMES = {'場面': 'when', '注意': 'note', '出典': 'source'}
# 段落ではない塊の頭（構成表の印が無くても数えない）
NOT_PROSE = re.compile(r'^\s*(?:```|~~~|[-*+]\s|\d+[.)]\s|\||!\[|:\s|\\|\[\^[^\]]*\]:|<|>|\$\$|\{\{<)')
ABBREV = ('e.g.', 'i.e.', 'et al.', 'cf.', 'vs.', 'etc.', 'Fig.', 'Figs.', 'Eq.', 'No.', 'pp.', 'p.',
          'Ch.', 'Sec.', 'Vol.', 'Mr.', 'Ms.', 'Dr.', 'St.', 'U.S.', 'U.K.')


def split_mark(inner: str) -> tuple:
    """コメントの中身を (種類, 主張) に。最初の `|` で切る。"""
    inner = ' '.join(inner.split())
    kind, _, claim = inner.partition('|')
    return kind.strip(), claim.strip()


def parse(text: str) -> list:
    """原稿を段落の並びに。各段落は dict:

    line / end_line   コメントの行（1から。無ければ None）
    kind / claim      コメントに書いた種類と主張（コメントが無ければ None）
    body_line / body_end / body   本文の行と本文（無ければ None / ''）
    prose             本文が文章の段落か（箇条書き・表・図・数式などでない）
    joined            コメントが本文の行の直後にある（pandoc は前の段落とつなぐ）
    heading / heading_line / heading_level   直前の見出し
    """
    lines = text.split('\n')
    start = 0
    m = mdlib.FRONT_MATTER.match(text)
    if m:
        start = text[:m.end()].count('\n')
    paras: list = []
    heading = (None, None, 0)
    block: list = []            # 今の本文の塊 [(行番号, 行)]
    pending = None              # 本文を待っているコメント
    fence = None
    math = False
    prev_text = False           # 1つ前の行が本文の行か

    def flush():
        nonlocal block, pending
        if block:
            body = '\n'.join(x for _, x in block)
            p = pending or new(None, None, None, None, False)
            p.update(body_line=block[0][0], body_end=block[-1][0], body=body,
                     prose=not NOT_PROSE.match(block[0][1]))
            paras.append(p)
        elif pending:
            paras.append(pending)
        block, pending = [], None

    def new(line, end, kind, claim, joined):
        return {'line': line, 'end_line': end, 'kind': kind, 'claim': claim,
                'body_line': None, 'body_end': None, 'body': '', 'prose': False,
                'joined': joined, 'heading': heading[0], 'heading_line': heading[1],
                'heading_level': heading[2]}

    i = start
    while i < len(lines):
        raw = lines[i]
        n = i + 1
        s = raw.strip()
        if fence:
            if s.startswith(fence):
                fence = None
            block.append((n, raw))
            i += 1
            continue
        f = re.match(r'\s*(```+|~~~+)', raw)
        if f:
            fence = f.group(1)
            block.append((n, raw))
            prev_text = False
            i += 1
            continue
        if PARA_START.match(raw):
            # 段落の印。`-->` まで（何行でも）
            j = i
            chunk = raw
            while '-->' not in chunk and j + 1 < len(lines):
                j += 1
                chunk += '\n' + lines[j]
            mm = PARA.search(chunk)
            kind, claim = split_mark(mm.group(1) if mm else chunk.split(':', 1)[1])
            joined = prev_text
            flush()
            pending = new(n, j + 1, kind, claim, joined)
            prev_text = False
            i = j + 1
            continue
        if s.startswith('<!--'):
            # ほかのコメントは読み飛ばす（段落を切らない）
            j = i
            while '-->' not in lines[j] and j + 1 < len(lines):
                j += 1
            i = j + 1
            continue
        if not s:
            # 本文はコメントのすぐ下の行から。空行が来たら、コメントだけの段落（本文はまだ無い）
            if block or pending:
                flush()
            prev_text = False
            i += 1
            continue
        h = re.match(r'(#{1,6})\s+(.+?)\s*$', raw)
        if h and not math:
            flush()
            title = re.sub(r'\s*\{[^}]*\}\s*$', '', h.group(2)).strip()
            heading = (title, n, len(h.group(1)))
            prev_text = False
            i += 1
            continue
        if s.startswith(':::') and not math:
            flush()
            prev_text = False
            i += 1
            continue
        if s == '$$':
            math = not math
        elif s.startswith('$$') and not s.endswith('$$'):
            math = True
        elif math and s.endswith('$$'):
            math = False
        block.append((n, raw))
        prev_text = True
        i += 1
    flush()
    return paras


def at_line(paras: list, line: int):
    """line 行目の段落（コメントの行、本文の行、その間の空行のどれか）。"""
    for p in paras:
        first = p['line'] or p['body_line']
        last = p['body_end'] or p['end_line']
        if first and last and first <= line <= last:
            return p
    return None


def _flat(body: str) -> str:
    out = ''
    for ln in body.split('\n'):
        ln = ln.strip()
        if not ln:
            continue
        if out and not (mdlib.has_cjk(out[-1]) and mdlib.has_cjk(ln[0])):
            out += ' '
        out += ln
    return out


def first_sentence(body: str, limit: int = 240) -> str:
    """本文の最初の文（人が主張と見比べるため。厳密でなくてよい）。"""
    s = _flat(body)
    s = re.sub(r'^(?:[-*+]|\d+[.)])\s+', '', s)
    jp = s.find('。')
    cut = None
    for m in re.finditer(r'[.!?]["\'”’)\]]*(?=\s+["“(\[]?[A-Z0-9])', s):
        before = s[:m.end()]
        if any(before.endswith(a) for a in ABBREV) or re.search(r'(?:^|\s)[A-Z]\.$', before):
            continue
        cut = m.end()
        break
    if jp >= 0 and (cut is None or jp < cut):
        cut = jp + 1
    out = s[:cut] if cut else s
    return out if len(out) <= limit else out[:limit - 1].rstrip() + '…'


# ---------------------------------------------------------------- フレーズの項目
def entry_fields(block: str) -> dict:
    """フレーズの項目（`## 見出し` からの塊）を when / note / source / lines に。

    lines は [{'position': 'open'|'body'|'close'|None, 'text': …}]（`- Open: …` の Open など）。
    """
    out = {'when': '', 'note': '', 'source': '', 'lines': []}
    for ln in block.split('\n')[1:]:
        f = FIELD.match(ln.strip())
        if f:
            out[FIELD_NAMES.get(f.group(1), f.group(1).lower())] = f.group(2).strip()
            continue
        p = POSITION.match(ln)
        if p:
            out['lines'].append({'position': p.group(1).lower(), 'text': p.group(2).strip()})
            continue
        it = ITEM.match(ln)
        if it:
            out['lines'].append({'position': None, 'text': it.group(1).strip()})
    return out


def resolve(kind: str, index: dict):
    """種類の書き方（`パック/ファイル#slug` か `ファイル#slug`）を、実在する項目の id に。"""
    if not kind:
        return None
    if kind in index:
        return kind
    hits = [k for k in index if k.split('/', 1)[-1] == kind]
    return hits[-1] if hits else None          # 同じ名前が2つのパックにあれば後ろ（具体的なほう）


def suggest(kind: str, index: dict) -> list:
    names = list(index) + [k.split('/', 1)[-1] for k in index]
    return difflib.get_close_matches(kind, names, n=2, cutoff=0.6)


# ---------------------------------------------------------------- 同じ型の使い回し
def _alternatives(text: str) -> list:
    """`A / B` を（〈 〉の外の ` / ` で）分ける。"""
    out, buf, depth = [], '', 0
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == '〈':
            depth += 1
        elif ch == '〉':
            depth = max(0, depth - 1)
        if depth == 0 and text.startswith(' / ', i):
            out.append(buf)
            buf = ''
            i += 3
            continue
        buf += ch
        i += 1
    return [x.strip() for x in out + [buf] if x.strip()]


def _literal(part: str) -> str:
    """型の言葉の部分を正規表現に（空白はいくつでも、英語の語は語の切れ目で）。"""
    if not part:
        return ''
    out = r'\s+'.join(re.escape(w) for w in part.split())
    if re.match(r'[A-Za-z0-9]', part):
        out = r'\b' + out
    if re.search(r'[A-Za-z0-9]$', part):
        out += r'\b'
    return out


def frame_pattern(text: str):
    """フレーズの行を本文から探す正規表現に。差し替える所（〈 〉）は何でも当たる。

    言葉が2語に満たない型（「〈X〉.」など）は探さない（どの文にも当たってしまう）。
    """
    pats = []
    for alt in _alternatives(text):
        parts = re.split(r'〈[^〉]*〉', alt)
        words = sum(len(re.findall(r'[A-Za-z]{2,}|[぀-鿿]{2,}', p)) for p in parts)
        if words < 2:
            continue
        lit = [_literal(p.strip(' .。,、')) for p in parts]
        body = r'.{1,120}?'.join(x for x in lit if x) if len(lit) > 1 else lit[0]
        if not body:
            continue
        pats.append(body)
    if not pats:
        return None
    return re.compile('|'.join(pats), re.I)


# ---------------------------------------------------------------- 構成表の確認（逆アウトライン）
def review(text: str, index: dict) -> dict:
    """原稿の段落を、種類・主張・本文の最初の文と、印（problems）にして並べる。

    index は writing.kind_index()。印は人が見るためのもので、どれも致命的ではない:
      no-kind       種類の無い段落（印が無い、または種類が空）
      unknown-kind  パックに無い種類（打ち間違い）。near に似た名前
      no-text       本文がまだ無いコメント
      joined        コメントが本文の行の直後（空行が無いので、組むと前の段落とつながる）
      same-kind     同じ見出しの下で、すぐ前の段落と同じ種類
    repeats は、同じ見出しの下で同じフレーズの行が2回以上使われている所。
    """
    paras = parse(text)
    rows, prev = [], {}
    for p in paras:
        if p['kind'] is None and not p['prose']:
            continue
        kind = p['kind'] or ''
        hit = resolve(kind, index) if kind else None
        marks, near = [], []
        if not kind:
            marks.append('no-kind')
        elif hit is None:
            marks.append('unknown-kind')
            near = suggest(kind, index)
        if p['kind'] is not None and not p['body'].strip():
            marks.append('no-text')
        if p['joined']:
            marks.append('joined')
        region = p['heading_line']
        if hit and prev.get(region) == hit:
            marks.append('same-kind')
        prev[region] = hit
        rows.append({'line': p['line'] or p['body_line'], 'body_line': p['body_line'],
                     'kind': p['kind'], 'id': hit, 'title': index[hit]['title'] if hit else None,
                     'claim': p['claim'],
                     'first_sentence': first_sentence(mdlib.strip_comments(p['body'])) if p['body'] else '',
                     'heading': p['heading'], 'heading_line': p['heading_line'],
                     'heading_level': p['heading_level'], 'problems': marks, 'near': near})
    return {'paragraphs': rows, 'repeats': repeats(paras, index)}


def repeats(paras: list, index: dict) -> list:
    """同じ見出しの下で2回以上使われたフレーズの行（ルールの "Vary the frames" の確認）。"""
    frames = []
    seen = set()
    for kid, it in index.items():
        for ln in it.get('lines', []):
            if ln['text'] in seen:
                continue
            seen.add(ln['text'])
            pat = frame_pattern(ln['text'])
            if pat:
                frames.append((kid, ln['text'], pat))
    by_region: dict = {}
    for p in paras:
        if p['body'].strip() and p['prose']:
            by_region.setdefault((p['heading_line'], p['heading']), []).append(p)
    out = []
    for (hline, htitle), ps in by_region.items():
        best: dict = {}             # 当たった所が同じなら、言葉のいちばん長い型を1つだけ
        for kid, text, pat in frames:
            where = []
            for p in ps:
                where += [p['body_line']] * len(pat.findall(_flat(mdlib.strip_comments(p['body']))))
            if len(where) >= 2:
                weight = len(re.sub(r'〈[^〉]*〉', '', text))
                key = tuple(where)
                if key not in best or weight > best[key][0]:
                    best[key] = (weight, {'heading': htitle, 'heading_line': hline, 'id': kid,
                                          'text': text, 'lines': where})
        out += [v for _, v in best.values()]
    return out
