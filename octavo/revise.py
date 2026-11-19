# -*- coding: utf-8 -*-
"""推敲: 原稿の「読み直す所」を1つの一覧に。AI に渡す材料を回に分け、判断を記録して次の回へ。

    octavo revise DOC [--file F] [--section S | --lines A-B] [--all]   読み直す所の一覧（回を記録する）
    octavo revise DOC ... --print [--pass N]                          AI に渡す材料（ルール・本文・指摘）
    octavo revise DOC --fine KEY …                                    Octavo の指摘を「これでよい」に
    octavo revise DOC --verdict RULE LINE fixed|fine                  AI（か人）の指摘への判断を記録
    octavo revise DOC … --json                                        機械可読（回は記録しない）

**Octavo は文章を直さず、判断もしない。** ここで集めるのは、ほかのモジュールがもう見つけている
もの（ルールの Flag・lint・段落の計画とのずれ・ask・2言語の遅れ）と、ここで数える次のものだけ:

  ルールの Count     `Count: <正規表現> per paragraph > N`（文・段落・節あたりの数）
  ルールの Scope     first-sentence / last-sentence のルールの Flag は、段落の最初・最後の文だけに当てる
  組み込みの点検     長すぎる文、同じ文末（日本語）・同じ書き出しの連続、定義より前の略語、
                    notes/writing/terms.csv の別表記

**反復が前提。** 回ごとに `docs/<名前>/revise.json` に段落の指紋と指摘を残し、次の回は前の回から
変わった段落と、まだ判断していない指摘を示す。「これでよい」とした指摘は、その文（段落の指摘ならその段落）が変わるまで出ない。
指摘が消えたのが段落を直したからなら「直した」と数える。ルールごとの数（当たった・直した・これで
よい）は `octavo writing --stats` が並べる。パックを手入れする材料（当たらないルール、却下ばかりの
ルール）。
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import md as mdlib
from . import paragraphs as paramod
from . import writing as writingmod
from .i18n import t

RECORD = 'revise.json'
KEEP_PASSES = 3                 # 記録に残す回（同じ本文の回は1つにまとめる）
RULES_PER_PASS = 8              # AI に1回で渡すルールの数（小さなモデルでも抜けにくい数）
TERMS = Path('notes') / 'writing' / 'terms.csv'
RUN = 3                         # 同じ文末・書き出しがこれだけ続いたら知らせる
# 組み込みの点検の id（ルールの id と同じ形。writing --stats でも並ぶ）
BUILTIN = {
    'octavo/long-sentence': lambda: t('a long sentence'),
    'octavo/repeated-ending': lambda: t('the same sentence ending again and again'),
    'octavo/repeated-opening': lambda: t('the same opening again and again'),
    'octavo/abbreviation': lambda: t('an abbreviation used before it is defined'),
    'octavo/term-variant': lambda: t('a variant of a term in terms.csv'),
}
CHECKS = ('rule', 'count', 'lookup', 'octavo', 'outline', 'ask', 'lint', 'translation', 'ai')
TEXT_SCOPES = ('sentence', 'paragraph', 'first-sentence', 'last-sentence')
LIST_HEAD = re.compile(r'^\s*(?:[-*+]|\d+[.)]|>)\s+')
MATH = re.compile(r'\$[^$\n]+\$')
ABBR = re.compile(r'(?<![\w-])([A-Z][A-Za-z0-9&]*[A-Z0-9]s?)(?![\w-])')
WORD = re.compile(r"[A-Za-z0-9][\w'’-]*")


def _sha(text: str, n: int = 16) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:n]


def mask(line: str) -> str:
    """当てない所（コード・値・引用・ラベル・リンクの先・数式・箇条書きの印）を空白に。"""
    line = LIST_HEAD.sub(lambda m: ' ' * len(m.group(0)), line)
    line = MATH.sub(lambda m: ' ' * len(m.group(0)), line)
    return writingmod._NOT_TEXT.sub(lambda m: ' ' * len(m.group(0)), line)


@dataclass
class Unit:
    """推敲で見る1つの段落（箇条書き・引用の塊も）。"""
    file: str
    path: Path
    appendix: bool
    line: int
    end: int
    heading: str | None
    heading_line: int | None
    section: str | None
    kind: str | None
    claim: str | None
    fp: str
    lines: list                                       # [(行番号, 元の行)]
    sentences: list = field(default_factory=list)     # [(行番号, 伏せた文)]


def _sentences(lines: list) -> list:
    """伏せた本文を文に分け、各文の始まりの行と一緒に。1文が何行にまたがってもよい。"""
    flat, at = '', []
    for n, raw in lines:
        s = mask(mdlib.strip_comments(raw)).strip()
        if not s:
            continue
        if flat and not (mdlib.has_cjk(flat[-1]) and mdlib.has_cjk(s[0])):
            flat += ' '
        at.append((len(flat), n))
        flat += s
    out, pos = [], 0
    while pos < len(flat):
        while pos < len(flat) and flat[pos] == ' ':
            pos += 1
        rest = flat[pos:]
        if not rest:
            break
        cut = paramod._cut(rest) or len(rest)
        text = ' '.join(rest[:cut].split())
        if text:
            line = next(n for off, n in reversed(at) if off <= pos)
            out.append((line, text))
        pos += cut
    return out


def units(cfg, doc, known: list) -> list:
    """その原稿（本文と付録）の段落。見出し・表・図・コード・数式の塊は入れない。"""
    out = []
    for name, src, app in cfg.sources():
        if name != doc.name:
            continue
        text = mdlib.read(src)
        all_lines = text.split('\n')
        secs: dict = {}
        for p in paramod.parse(text):
            if not p['body'].strip() or p['body_line'] is None:
                continue
            if not p['prose'] and not LIST_HEAD.match(p['body']):
                continue
            hl = p['heading_line']
            if hl not in secs:
                secs[hl] = writingmod.section_at(text, p['body_line'], known, app)[0]
            body = [(n, all_lines[n - 1]) for n in range(p['body_line'], p['body_end'] + 1)]
            u = Unit(cfg.rel(src), Path(src), app, p['body_line'], p['body_end'], p['heading'], hl, secs[hl],
                     p['kind'], p['claim'], _sha('\n'.join(x.rstrip() for _, x in body)), body)
            u.sentences = _sentences(body)
            if u.sentences:
                out.append(u)
    return out


def _excerpt(text: str, match: str = '') -> str:
    at = text.find(match) if match else 0
    return writingmod._excerpt(text, max(at, 0), max(at, 0) + len(match))


def _finding(check, rule, title, u, line, match, text, note='') -> dict:
    return {'check': check, 'rule': rule, 'title': title, 'file': u.file if u else '',
            'line': line, 'para': u.fp if u else '', 'match': match, 'text': text, 'note': note,
            'section': u.section if u else None}


# ---------------------------------------------------------------- ルールの Flag と Count
def rule_findings(found: list, us: list) -> list:
    out = []
    for fl in found:
        for u in us:
            if 'all' not in fl['sections'] and u.section not in fl['sections']:
                continue
            ss = u.sentences
            if fl['scope'] == 'first-sentence':
                ss = ss[:1]
            elif fl['scope'] == 'last-sentence':
                ss = ss[-1:]
            check = 'lookup' if fl['stage'] == 'lookup' else 'rule'
            for line, s in ss:
                for _, pat in fl['patterns']:
                    m = pat.search(s)
                    if m and m.group(0):
                        out.append(_finding(check, fl['id'], fl['title'], u, line, m.group(0),
                                            _excerpt(s, m.group(0))))
                        break
        for c in fl['counts']:
            out += _counts(fl, c, us)
    return out


def _counts(fl: dict, c: dict, us: list) -> list:
    out = []
    use = [u for u in us if 'all' in fl['sections'] or u.section in fl['sections']]

    def say(u, line, n, sample):
        out.append(_finding('count', fl['id'], fl['title'], u, line, str(n), sample,
                            t('{n} matches of {pattern} in one {unit}; the rule allows {limit}',
                              n=n, pattern=c['pattern'], unit=c['unit'], limit=c['over'])))
    if c['unit'] == 'sentence':
        for u in use:
            for line, s in u.sentences:
                n = len([m for m in c['re'].finditer(s) if m.group(0)])
                if n > c['over']:
                    say(u, line, n, _excerpt(s))
    elif c['unit'] == 'paragraph':
        for u in use:
            n = sum(len([m for m in c['re'].finditer(s) if m.group(0)]) for _, s in u.sentences)
            if n > c['over']:
                say(u, u.line, n, _excerpt(u.sentences[0][1]))
    else:
        groups: dict = {}
        for u in use:
            groups.setdefault((u.file, u.heading_line), []).append(u)
        for g in groups.values():
            n = sum(len([m for m in c['re'].finditer(s) if m.group(0)]) for u in g for _, s in u.sentences)
            if n > c['over']:
                say(g[0], g[0].line, n, g[0].heading or _excerpt(g[0].sentences[0][1]))
    return out


# ---------------------------------------------------------------- 組み込みの点検
def _ending(s: str) -> str:
    s = re.sub(r'[\s。．.!?！？」』)）\]]+$', '', s)
    tail = s[-2:]
    return tail if len(tail) == 2 and mdlib.has_cjk(tail) else ''


def _first_word(s: str) -> str:
    m = re.match(r'\s*["“(]?([A-Za-z][\w’\'-]*)', s)
    return m.group(1).lower() if m else ''


def _opener(s: str) -> str:
    """段落の書き出し: 英語は最初の語、日本語は頭から8文字以内の「、」まで（また、・さらに、）。"""
    if mdlib.has_cjk(s[:1]):
        at = s.find('、')
        return s[:at + 1] if 0 < at <= 8 else ''
    return _first_word(s)


def long_sentences(us: list, words: int, chars: int) -> list:
    out = []
    for u in us:
        for line, s in u.sentences:
            if mdlib.has_cjk(s):
                n = len(re.sub(r'\s', '', s))
                over = chars and n > chars
                note = t('{n} characters (revise_sentence_chars: {limit})', n=n, limit=chars)
            else:
                n = len(WORD.findall(s))
                over = words and n > words
                note = t('{n} words (revise_sentence_words: {limit})', n=n, limit=words)
            if over:
                out.append(_finding('octavo', 'octavo/long-sentence', BUILTIN['octavo/long-sentence'](), u,
                                    line, str(n), _excerpt(s), note))
    return out


def repeats(us: list) -> list:
    """同じ文末（日本語）・同じ書き出しの文が段落の中で RUN 回続く、同じ書き出しの段落が見出しの下で
    RUN 回続く。続いた3つ目から。"""
    out = []
    for u in us:
        for key, rule, what in ((_ending, 'octavo/repeated-ending', 'ending'),
                                (_first_word, 'octavo/repeated-opening', 'opening')):
            run, last = 0, None
            for line, s in u.sentences:
                k = key(s)
                run = run + 1 if k and k == last else 1
                last = k
                if k and run >= RUN:
                    note = t('{n} sentences in a row end with {text}', n=run, text=k) if what == 'ending' \
                        else t('{n} sentences in a row open with {text}', n=run, text=k)
                    out.append(_finding('octavo', rule, BUILTIN[rule](), u, line, k, _excerpt(s, ''), note))
    run, last, region = 0, None, None
    for u in us:
        k = _opener(u.sentences[0][1])
        if (u.file, u.heading_line) != region:
            region, run, last = (u.file, u.heading_line), 0, None
        run = run + 1 if k and k == last else 1
        last = k
        if k and run >= RUN:
            out.append(_finding('octavo', 'octavo/repeated-opening', BUILTIN['octavo/repeated-opening'](), u,
                                u.line, k, _excerpt(u.sentences[0][1]),
                                t('{n} paragraphs in a row open with {text}', n=run, text=k)))
    return out


def _is_abbr(token: str) -> bool:
    core = token[:-1] if token.endswith('s') and token[:-1].isupper() else token
    return sum(1 for c in core if c.isupper()) >= 2


def abbreviations(us: list) -> list:
    """定義（`Regression discontinuity design (RDD)`、`RDD（回帰不連続デザイン）`）より前に使った略語。
    定義のある略語だけ（US・OLS のように定義しないものは見ない）。最初の1回だけ知らせる。"""
    seq = [(u, line, s) for u in us for line, s in u.sentences]
    defined: dict = {}
    for i, (_, _, s) in enumerate(seq):
        for m in re.finditer(r'[(（]\s*([A-Z][A-Za-z0-9&]*[A-Z0-9]s?)\s*[)）;；,，]', s):
            if _is_abbr(m.group(1)):
                defined.setdefault(m.group(1), (i, m.start()))
        for m in re.finditer(r'(?<![\w-])([A-Z][A-Za-z0-9&]*[A-Z0-9]s?)\s*[(（]([^)）]{4,})[)）]', s):
            inner = m.group(2)
            if _is_abbr(m.group(1)) and (' ' in inner.strip() or mdlib.has_cjk(inner)):
                defined.setdefault(m.group(1), (i, m.start()))
    out, told = [], set()
    for i, (u, line, s) in enumerate(seq):
        for m in ABBR.finditer(s):
            a = m.group(1)
            if a in told or a not in defined or not _is_abbr(a):
                continue
            di, dpos = defined[a]
            if (i, m.start()) < (di, dpos):
                told.add(a)
                du, dline, _ = seq[di]
                out.append(_finding('octavo', 'octavo/abbreviation', BUILTIN['octavo/abbreviation'](), u, line, a,
                                    _excerpt(s, a), t('{abbr} is defined later, at {file}:{line}', abbr=a,
                                                      file=du.file, line=dline)))
    return out


def read_terms(root: Path, lang: str) -> list:
    """terms.csv の (使う語, [別表記])。見出しの行に variants（avoid・別表記）の列があるときだけ。
    使う語は原稿の言語（ja・en）の列、無ければ最初の列。"""
    p = Path(root) / TERMS
    if not p.is_file():
        return []
    rows = list(csv.reader(io.StringIO(p.read_text(encoding='utf-8-sig'))))
    if not rows:
        return []
    head = [h.strip().lower() for h in rows[0]]
    vcol = next((i for i, h in enumerate(head) if h in ('variants', 'avoid', '別表記', 'ゆれ')), None)
    if vcol is None:
        return []
    lcol = head.index(lang) if lang in head else 0
    out = []
    for r in rows[1:]:
        if len(r) <= max(vcol, lcol) or not r[lcol].strip():
            continue
        vs = [v.strip() for v in re.split(r'[;|／]|\s/\s', r[vcol]) if v.strip() and v.strip() != r[lcol].strip()]
        if vs:
            out.append((r[lcol].strip(), vs))
    return out


def term_variants(us: list, terms: list) -> list:
    out = []
    pats = []
    for pref, vs in terms:
        for v in vs:
            rx = re.compile(r'(?<![\w])' + re.escape(v) + r'(?![\w])', re.I) if v.isascii() \
                else re.compile(re.escape(v))
            pats.append((pref, v, rx))
    for u in us:
        for line, s in u.sentences:
            for pref, v, rx in pats:
                m = rx.search(s)
                if m and pref.lower() not in s[max(0, m.start() - len(pref)):m.end() + len(pref)].lower():
                    out.append(_finding('octavo', 'octavo/term-variant', BUILTIN['octavo/term-variant'](), u,
                                        line, m.group(0), _excerpt(s, m.group(0)),
                                        t('terms.csv writes {term}', term=pref)))
    return out


# ---------------------------------------------------------------- ほかのモジュールの分
def _unit_at(us: list, file: str, line: int):
    for u in us:
        if u.file == file and u.line <= line <= u.end:
            return u
    return None


def _line_finding(check, rule, title, us, file, line, text, note='', section=None) -> dict:
    u = _unit_at(us, file, line)
    f = _finding(check, rule, title, u, line, '', text, note)
    f['file'] = file
    if u is None:
        f['para'] = _sha(f'{file}:{text}')
        f['section'] = section
    return f


def others(cfg, doc, us: list, sel: dict) -> list:
    from . import cli as climod
    from . import lint as lintmod
    out = []
    index = writingmod.kind_index(sel)
    every = writingmod.kind_index(sel, usable=False)
    unplanned = writingmod.sentence_sections(sel)
    files = {}
    for name, src, app in cfg.sources():
        if name == doc.name:
            files[cfg.rel(src)] = (src, app)
    for rel, (src, app) in files.items():
        text = mdlib.read(src)
        marked = any(p['kind'] is not None for p in paramod.parse(text))
        got = paramod.review(text, index, sel['sections'], app, every=every, unplanned=unplanned)
        if marked:
            for r in got['paragraphs']:
                for prob in r['problems']:
                    out.append(_line_finding('outline', f'outline/{prob}', climod.PARA_PROBLEMS[prob](), us, rel,
                                             r['line'], r['first_sentence'] or (r['claim'] or ''),
                                             r['claim'] or ''))
            for rp in got['repeats']:
                out.append(_line_finding('outline', 'outline/repeated-frame', t('the same phrase-bank line twice'),
                                         us, rel, rp['lines'][-1], rp['text'],
                                         t('also at line {lines}', lines=', '.join(map(str, rp['lines'][:-1])))))
        for a in got['asks']:
            out.append(_line_finding('ask', 'ask', t('a question for the author'), us, rel, a['line'], a['text']))
    for f in lintmod.collect(cfg):
        if f.file in files:
            out.append(_line_finding('lint', f'lint/{f.kind}', f.label(), us, f.file, f.line, f.excerpt))
    for w in lintmod.wrap_issues(cfg):
        if w.file in files:
            out.append(_line_finding('lint', 'lint/wrapped', t('a line broken in the middle of a sentence'), us,
                                     w.file, w.line, w.excerpt))
    if getattr(doc, 'translation_of', None):
        from . import translation as trmod
        main = cfg.document(doc.translation_of)
        for r in trmod.status(cfg, main, doc):
            if r.state in (trmod.MAIN_CHANGED, trmod.BOTH_CHANGED, trmod.UNSYNCED, trmod.ONLY_MAIN) or r.differs:
                side = r.other or r.main
                rel = cfg.rel(Path(doc.src))
                note = '; '.join(trmod.differs_text(r.differs)) if r.differs else ''
                out.append(_line_finding('translation', f'translation/{r.state}', trmod.state_text(r.state), us,
                                         rel, side.line if r.other else 1, f'{r.key} ({side.title})', note))
    return out


# ---------------------------------------------------------------- まとめる
def record_path(cfg, doc) -> Path:
    return Path(doc.src).parent / RECORD


def load_record(cfg, doc) -> dict:
    p = record_path(cfg, doc)
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding='utf-8')).get(doc.name, {})
    except (ValueError, OSError):
        return {}


def save_record(cfg, doc, rec: dict) -> None:
    p = record_path(cfg, doc)
    every = {}
    if p.is_file():
        try:
            every = json.loads(p.read_text(encoding='utf-8'))
        except ValueError:
            every = {}
    every[doc.name] = rec
    p.write_text(json.dumps(every, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8')


def _keys(found: list) -> None:
    seen: dict = {}
    for f in found:
        # 段落の指紋は入れない: 同じ段落のほかの文を直しても、残った指摘は同じ指摘のまま
        base = '|'.join((f['check'], f['rule'], f['text'], f['match'], f['note']))
        seen[base] = seen.get(base, 0) + 1
        f['key'] = _sha(f'{base}|{seen[base]}', 10)


def _base(rec: dict, fps: set):
    """比べる相手の回: 本文が今と同じ回は飛ばして、その前の回。"""
    passes = rec.get('passes') or []
    if passes and set(passes[-1]['paragraphs']) == fps:
        return passes[-2] if len(passes) >= 2 else None
    return passes[-1] if passes else None


def collect(cfg, doc) -> dict:
    """その原稿全体の、推敲で見るもの。範囲で絞るのは view() で。"""
    view_cfg = cfg.for_document(doc)
    got = writingmod.packs(Path(cfg.root))
    known = writingmod.known_sections(got)
    sel = writingmod.select(cfg, doc, every=True)
    found_rules, warnings = writingmod.flags(sel)
    us = units(cfg, doc, known)
    found = rule_findings(found_rules, us)
    found += long_sentences(us, int(view_cfg.get('revise_sentence_words') or 0),
                            int(view_cfg.get('revise_sentence_chars') or 0))
    found += repeats(us)
    found += abbreviations(us)
    found += term_variants(us, read_terms(Path(cfg.root), view_cfg.get('lang') or ''))
    found += others(cfg, doc, us, sel)
    found.sort(key=lambda f: (f['file'], f['line'], CHECKS.index(f['check']), f['rule']))
    _keys(found)
    rec = load_record(cfg, doc)
    fps = {u.fp for u in us}
    base = _base(rec, fps)
    fine = {k for k, v in (rec.get('verdicts') or {}).items() if v.get('verdict') == 'fine'}
    # 新しいか: 記録した最後の回に無かった。変わった段落: 本文が今と違う、その前の回から
    last = (rec.get('passes') or [None])[-1]
    for f in found:
        f['state'] = 'fine' if f['key'] in fine else \
            ('new' if last is None or f['key'] not in last['findings'] else 'seen')
    changed = {u.fp for u in us if base is None or u.fp not in set(base['paragraphs'])}
    return {'doc': doc.name, 'sel': sel, 'units': us, 'findings': found, 'warnings': warnings,
            'record': rec, 'changed': changed, 'base': base['at'] if base else None,
            'sections': known}


def record_pass(cfg, doc, got: dict) -> None:
    """この回を記録する。新しく出た指摘を「当たった」、段落を直して消えた指摘を「直した」と数える。"""
    rec = got['record']
    fps = sorted({u.fp for u in got['units']})
    cur = {'at': datetime.now().isoformat(timespec='seconds'), 'paragraphs': fps,
           'findings': {f['key']: {'rule': f['rule'], 'check': f['check'], 'para': f['para']}
                        for f in got['findings']}}
    passes = rec.setdefault('passes', [])
    tally = rec.setdefault('tally', {})
    prev = passes[-1] if passes else None
    before = prev['findings'] if prev else {}
    for k, f in cur['findings'].items():
        if k not in before:
            tally.setdefault(f['rule'], {'found': 0, 'fixed': 0, 'fine': 0})['found'] += 1
    for k, f in before.items():
        if k not in cur['findings'] and f['para'] not in set(fps):
            tally.setdefault(f['rule'], {'found': 0, 'fixed': 0, 'fine': 0})['fixed'] += 1
    if prev and set(prev['paragraphs']) == set(fps):
        passes[-1] = cur
    else:
        passes.append(cur)
    del passes[:-KEEP_PASSES]
    # 段落が無くなった「これでよい」は要らない（指紋が変われば、もう当たらない）
    keys = set(cur['findings'])
    rec['verdicts'] = {k: v for k, v in (rec.get('verdicts') or {}).items()
                       if k in keys or (v.get('check') == 'ai' and v.get('para') in set(fps))}
    save_record(cfg, doc, rec)


def judge(cfg, doc, got: dict, rule: str, line: int | None, verdict: str, key: str | None = None,
          note: str = '', file: str | None = None) -> dict:
    """指摘への判断を記録する。key があれば Octavo の指摘、なければ AI（か人）の指摘（rule と line）。"""
    rec = got['record']
    if key:
        hits = [f for f in got['findings'] if f['key'].startswith(key)]
        if len(hits) != 1:
            raise ValueError(t('no finding {key}', key=key) if not hits
                             else t('{key} matches several findings; give more of it', key=key))
        f = hits[0]
        rule, line, para, check, file = f['rule'], f['line'], f['para'], f['check'], f['file']
        key = f['key']
    else:
        u = next((u for u in got['units'] if (file is None or u.file == file) and u.line <= line <= u.end), None)
        if u is None:
            raise ValueError(t('line {line} is not in a paragraph of {doc}', line=line, doc=doc.name))
        para, check, file = u.fp, 'ai', u.file
        key = 'ai-' + _sha(f'{rule}|{para}|{note}|{line}', 8)
    rec.setdefault('verdicts', {})[key] = {'rule': rule, 'verdict': verdict, 'line': line, 'file': file,
                                           'para': para, 'check': check, 'note': note,
                                           'at': datetime.now().isoformat(timespec='seconds')}
    rec.setdefault('tally', {}).setdefault(rule, {'found': 0, 'fixed': 0, 'fine': 0})[verdict] += 1
    save_record(cfg, doc, rec)
    return rec['verdicts'][key]


def in_range(f_or_u, file: str | None, lines: tuple | None, section: str | None) -> bool:
    fl = f_or_u['file'] if isinstance(f_or_u, dict) else f_or_u.file
    ln = f_or_u['line'] if isinstance(f_or_u, dict) else f_or_u.line
    sec = f_or_u['section'] if isinstance(f_or_u, dict) else f_or_u.section
    if file is not None and fl != file:
        return False
    if lines is not None:
        a, b = lines
        end = ln if isinstance(f_or_u, dict) else f_or_u.end
        if end < a or (b is not None and ln > b):
            return False
    if section is not None and sec != section:
        return False
    return True


def view(got: dict, file=None, lines=None, section=None, every=False) -> dict:
    """範囲と状態で絞った一覧（every なら「これでよい」も）。"""
    fs = [f for f in got['findings'] if in_range(f, file, lines, section) and (every or f['state'] != 'fine')]
    us = [u for u in got['units'] if in_range(u, file, lines, section)]
    return {'doc': got['doc'], 'base': got['base'], 'findings': fs,
            'paragraphs': len(us), 'changed': sum(1 for u in us if u.fp in got['changed']),
            'warnings': got['warnings'],
            'fine': sum(1 for f in got['findings'] if f['state'] == 'fine' and in_range(f, file, lines, section))}


# ---------------------------------------------------------------- AI に渡す材料
def revise_rules(got: dict, us: list, found: list) -> list:
    """推敲で当てるルール（書くときのものも）。lookup は範囲に当たったものだけ。[(ファイル, 項目, 本文)]"""
    secs = {u.section for u in us}
    triggered = {f['rule'] for f in found if f['check'] == 'lookup'}
    out = []
    for f in got['sel']['files']:
        if f['kind'] != 'rules' or f.get('excluded'):
            continue
        _, entries = writingmod._split_entries(mdlib.split_front_matter(mdlib.read(Path(f['path'])))[1])
        for it, (_, block, _) in zip(f['items'], entries):
            if it['off'] or it.get('replaced_by'):
                continue
            if it['stage'] == 'lookup' and it['id'] not in triggered:
                continue
            if 'all' not in it['sections'] and not secs & set(it['sections']):
                continue
            out.append((f, it, block))
    return out


def _numbered(u: Unit) -> list:
    return [f'{n:>5}| {raw}' for n, raw in u.lines]


def passes(got: dict, file=None, lines=None, section=None, every=False) -> list:
    """AI に渡す回: [{'title', 'scope', 'rules': [id], 'text'}]。ルールを範囲（文と段落・節・文書）ごとに
    RULES_PER_PASS ずつ束ね、それぞれに要る本文を付ける。文と段落の回は前の回から変わった段落だけ
    （every なら全部）、節の回はそういう段落のある節、文書の回は見出しと段落の主張と最初の文。"""
    us = [u for u in got['units'] if in_range(u, file, lines, section)]
    fs = [f for f in got['findings'] if in_range(f, file, lines, section)]
    todo = [u for u in us if every or u.fp in got['changed']]
    rules = revise_rules(got, us, fs)
    groups = {'text': [], 'section': [], 'document': []}
    for f, it, block in rules:
        g = 'text' if it['scope'] in TEXT_SCOPES else it['scope']
        groups[g].append((f, it, block))
    out = []
    for g, rs in groups.items():
        for i in range(0, len(rs), RULES_PER_PASS):
            chunk = rs[i:i + RULES_PER_PASS]
            out.append({'scope': g, 'rules': [it['id'] for _, it, _ in chunk],
                        'body': [writingmod.entry_text(block, it['id']) for _, it, block in chunk]})
    for p in out:
        if p['scope'] == 'text':
            p['units'] = todo
        elif p['scope'] == 'section':
            regions = {(u.file, u.heading_line) for u in todo}
            p['units'] = [u for u in us if (u.file, u.heading_line) in regions]
        else:
            p['units'] = us
    if not out:
        out.append({'scope': 'text', 'rules': [], 'body': [], 'units': todo})
    fine = [v for v in (got['record'].get('verdicts') or {}).values()
            if v.get('verdict') == 'fine' and v.get('para') in {u.fp for u in us}]
    n = len(out)
    for i, p in enumerate(out, 1):
        p['title'] = t('pass {i} of {n}: {what}', i=i, n=n, what={
            'text': t('sentences and paragraphs'), 'section': t('sections'),
            'document': t('the whole manuscript')}[p['scope']])
        p['text'] = _pass_text(got, p, fs if i == 1 else [], fine, every)
    return out


def _pass_text(got, p, fs, fine, every) -> str:
    out = [f"<!-- octavo revise: {got['doc']} — {p['title']} -->",
           '<!-- ' + t('List each problem with its line, the rule id, the words quoted and a proposed wording. '
                       'Do not rewrite the text, and do not ask for new analysis.') + ' -->', '']
    if p['body']:
        out += ['# ' + t('Rules to check'), ''] + [b + '\n' for b in p['body']]
    out += ['# ' + t('Text'), '']
    if not p['units']:
        out += [t('(no paragraph changed since the last pass; --all for every paragraph)'), '']
    elif p['scope'] == 'document':
        last = object()
        for u in p['units']:
            if u.heading_line != last:
                last = u.heading_line
                out += [f'## {u.heading or ""}  ({u.file}:{u.heading_line})' if u.heading else f'## ({u.file})']
            out.append(f'- {u.line}: ' + (f'[{u.kind}] ' if u.kind else '') + (f'{u.claim} — ' if u.claim else '')
                       + paramod.first_sentence('\n'.join(x for _, x in u.lines)))
        out.append('')
    else:
        last = object()
        for u in p['units']:
            if (u.file, u.heading_line) != last:
                last = (u.file, u.heading_line)
                out += [f'## {u.heading or ""}  ({u.file}:{u.heading_line or 1})', '']
            if u.kind or u.claim:
                out.append('<!-- ' + t('planned: {kind} | {claim}', kind=u.kind or '', claim=u.claim or '') + ' -->')
            out += _numbered(u) + ['']
    if fs:
        out += ['# ' + t('Places Octavo found (read each; most may be fine)'), '']
        for f in fs:
            if f['state'] == 'fine':
                continue
            out.append(f"- {f['file']}:{f['line']}  [{f['rule']}] {f['title']}"
                       + (f" — {f['note']}" if f['note'] else '') + (f": {f['text']}" if f['text'] else ''))
        out.append('')
    if fine:
        out += ['# ' + t('Already judged fine (do not raise again)'), '']
        out += [f"- {v.get('file', '')}:{v['line']}  [{v['rule']}]" + (f" {v['note']}" if v.get('note') else '')
                for v in fine] + ['']
    return '\n'.join(out).rstrip() + '\n'


def rules_text(got: dict, file=None, lines=None, section=None) -> str:
    """校正に添えるルール（回に分けない）。"""
    us = [u for u in got['units'] if in_range(u, file, lines, section)]
    fs = [f for f in got['findings'] if in_range(f, file, lines, section)]
    rs = revise_rules(got, us, fs)
    if not rs:
        return ''
    return '\n'.join(['# ' + t('Rules to check'), ''] + [writingmod.entry_text(b, it['id']) + '\n'
                                                       for _, it, b in rs]).rstrip() + '\n'


# ---------------------------------------------------------------- 数
def stats(cfg, docs=None) -> dict:
    """ルールごとの数（記録から）と、一度も当たっていない、機械で当てられるルール。"""
    tally: dict = {}
    fired = set()
    names = docs or list(cfg.documents)
    checkable: dict = {}
    for name in names:
        doc = cfg.document(name)
        rec = load_record(cfg, doc)
        for rule, n in (rec.get('tally') or {}).items():
            row = tally.setdefault(rule, {'found': 0, 'fixed': 0, 'fine': 0, 'docs': []})
            for k in ('found', 'fixed', 'fine'):
                row[k] += n.get(k, 0)
            row['docs'].append(name)
            if n.get('found') or n.get('fixed') or n.get('fine'):
                fired.add(rule)
        if rec:
            sel = writingmod.select(cfg, doc, every=True)
            for fl in writingmod.flags(sel)[0]:
                checkable.setdefault(fl['id'], fl['title'])
    rows = [{'rule': r, **v} for r, v in sorted(tally.items())]
    never = [{'rule': r, 'title': ti} for r, ti in checkable.items() if r not in fired]
    return {'rules': rows, 'never': never}
