# -*- coding: utf-8 -*-
"""言語違いの原稿（`docs/<名前>/<名前>.<言語>.md`）と主の原稿の対応を見張る。

片方を書いてからもう片方を作ることも、両方を並べて書くこともある。どちらでも、節ごとに
「対応がとれているか」「最後に合わせてから、どちらが変わったか」が分かればよい。

- **節の対応**: 見出しにラベル（`{#sec-…}`）があればそれで、なければ親の節の中の同じ深さの
  見出しの順番で対応させる。冒頭の title / subtitle / abstract も1つの節（`_front`）として扱う。
  付録（`appendix.md` と `appendix.<言語>.md`）も同じ。
- **中身の突き合わせ**: 対応する節どうしで、図表・式・節への参照（`@fig-…`）、置いたラベル、
  引用、`{{値}}` の名前を比べる。訳すと文は変わるが、これらは変わらないはず。
- **合わせた記録**: `octavo translation <文書> --mark` が、節ごとに両方の中身のハッシュ値を
  `docs/<名前>/translation.json`（git に入れる）に書く。あとで片方を直すと、その節が
  「主の原稿が変わった」などと出る。

Octavo は訳さない。`--print` は、AI か人が訳す・合わせるための材料（両方の節と食い違い、
対訳表 `notes/writing/terms.csv`）を出すだけ。
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import crossref as xref
from . import md as mdlib
from . import values as valmod
from .i18n import t

RECORD = 'translation.json'
TERMS = Path('notes') / 'writing' / 'terms.csv'
FRONT = '_front'
PREAMBLE = '_preamble'
FRONT_KEYS = ('title', 'subtitle', 'abstract')
LABEL_IN_ATTR = re.compile(r'#([\w:.-]+)')

# 節の状態
SYNCED, UNSYNCED = 'synced', 'unsynced'
MAIN_CHANGED, OTHER_CHANGED, BOTH_CHANGED = 'main-changed', 'other-changed', 'both-changed'
ONLY_MAIN, ONLY_OTHER = 'only-main', 'only-other'


@dataclass
class Section:
    key: str
    title: str
    line: int                  # 見出しの行（1 から。_front は 1）
    text: str                  # 見出しの行と、次の見出しまでの本文（下の節は含めない）
    part: str = 'body'         # body | appendix

    def digest(self) -> str:
        norm = '\n'.join(ln.rstrip() for ln in self.text.strip().split('\n'))
        return hashlib.sha256(norm.encode('utf-8')).hexdigest()[:16]


def sections(md: str, part: str = 'body') -> list:
    """原稿を節に分ける。鍵はラベル、なければ「親の鍵/深さ.番号」。"""
    meta, body = mdlib.split_front_matter(md)
    prefix = '' if part == 'body' else f'{part}:'
    head_lines = len(md.split('\n')) - len(body.split('\n'))
    out = []
    front = '\n'.join(f'{k}: {meta[k]}' for k in FRONT_KEYS if meta.get(k))
    if front and part == 'body':
        out.append(Section(FRONT, t('title and abstract'), 1, front, part))
    lines = mdlib.drop_references(body).split('\n')
    heads, fence = [], None
    for i, line in enumerate(lines):
        f = mdlib.FENCE_LINE.match(line)
        if f:
            fence = None if fence == f.group(1) else (fence or f.group(1))
            continue
        h = None if fence else xref.HEADING.match(line)
        if h:
            heads.append((i, len(h.group('hash')), h.group('title').strip().rstrip('#').strip(),
                          h.group('attr') or ''))
    first = heads[0][0] if heads else len(lines)
    pre = '\n'.join(lines[:first]).strip()
    if pre:
        out.append(Section(prefix + PREAMBLE, t('before the first heading'), head_lines + 1, pre, part))
    stack: list = []           # [(深さ, 鍵)]
    count: dict = {}           # (親の鍵, 深さ) -> ラベルのない見出しの数
    for n, (i, depth, title, attr) in enumerate(heads):
        while stack and stack[-1][0] >= depth:
            stack.pop()
        parent = stack[-1][1] if stack else ''
        lab = LABEL_IN_ATTR.search(attr)
        if lab:
            key = prefix + lab.group(1)
        else:
            c = count[(parent, depth)] = count.get((parent, depth), 0) + 1
            key = f'{parent}/h{depth}.{c}' if parent else f'{prefix}h{depth}.{c}'
        stack.append((depth, key))
        end = heads[n + 1][0] if n + 1 < len(heads) else len(lines)
        out.append(Section(key, title, head_lines + i + 1, '\n'.join(lines[i:end]), part))
    return out


@dataclass
class Facts:
    refs: set = field(default_factory=set)
    labels: set = field(default_factory=set)
    cites: set = field(default_factory=set)
    values: set = field(default_factory=set)


def facts(text: str, kinds) -> Facts:
    """訳しても変わらないはずのもの: 参照・ラベル・引用・値の名前。"""
    label_re, ref_re = xref.patterns(kinds)
    masked, _ = valmod.mask_code(text)
    heading_free = '\n'.join(ln for ln in masked.split('\n') if not xref.HEADING.match(ln))
    return Facts(
        refs={m.group('label') or m.group('blabel') for m in ref_re.finditer(masked)},
        labels={m.group('label') for m in label_re.finditer(heading_free)},
        cites=set(mdlib.cited_keys(text, kinds)),
        values={m.group('name') for m in valmod.PLACEHOLDER.finditer(masked)})


def pairs(cfg) -> list:
    """[(主の文書, 言語違いの文書)]。"""
    return [(cfg.documents[d.translation_of], d) for d in cfg.documents.values()
            if d.translation_of and d.translation_of in cfg.documents]


def find_pair(cfg, name: str, lang: str | None = None) -> tuple:
    """文書の名前（主でも言語違いでも）から (主, 言語違い)。見つからなければ SystemExit。"""
    doc = cfg.document(name)
    if doc.translation_of:
        return cfg.documents[doc.translation_of], doc
    others = [d for d in cfg.translations(doc.name) if lang is None or d.lang == lang]
    if len(others) == 1:
        return doc, others[0]
    if not others:
        raise SystemExit(t('{name} has no manuscript in another language (add one with: '
                           'octavo new {kind} {name} --lang {lang})', name=doc.name,
                           kind='paper' if doc.profile == 'paper' else 'slides',
                           lang='en' if (cfg.for_document(doc)['lang'] == 'ja') else 'ja'))
    raise SystemExit(t('{name} has manuscripts in several languages; say which with --lang',
                       name=doc.name))


def record_path(main) -> Path:
    return Path(main.src).parent / RECORD


def load_record(main) -> dict:
    try:
        rec = json.loads(record_path(main).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    return rec if isinstance(rec, dict) else {}


def _sections_of(doc) -> list:
    out = sections(mdlib.read(doc.src)) if Path(doc.src).is_file() else []
    if doc.appendix and Path(doc.appendix).is_file():
        out += sections(mdlib.read(doc.appendix), 'appendix')
    return out


@dataclass
class Row:
    key: str
    state: str
    main: Section | None
    other: Section | None
    differs: dict = field(default_factory=dict)     # {'refs': ([主だけ], [言語違いだけ]), …}

    def as_json(self, cfg, main_doc, other_doc) -> dict:
        def side(s, d):
            if s is None:
                return None
            src = d.appendix if s.part == 'appendix' else d.src
            return {'title': s.title, 'line': s.line, 'file': cfg.rel(Path(src))}
        return {'key': self.key, 'state': self.state, 'main': side(self.main, main_doc),
                'other': side(self.other, other_doc),
                'differs': {k: {'main_only': a, 'other_only': b} for k, (a, b) in self.differs.items()}}


def status(cfg, main, other) -> list:
    """節ごとの対応（Row の並び）。主の原稿の順、言語違いにしかない節はその後ろ。"""
    kinds = xref.kinds_of(xref.theorem_envs(cfg))
    ms, os_ = _sections_of(main), _sections_of(other)
    om = {s.key: s for s in os_}
    rec = load_record(main).get(other.lang or '', {})
    rows = []
    for s in ms:
        o = om.get(s.key)
        if o is None:
            rows.append(Row(s.key, ONLY_MAIN, s, None))
            continue
        r = rec.get(s.key) if isinstance(rec.get(s.key), dict) else None
        if r is None:
            state = UNSYNCED
        else:
            mc, oc = r.get('main') != s.digest(), r.get('other') != o.digest()
            state = BOTH_CHANGED if mc and oc else MAIN_CHANGED if mc else OTHER_CHANGED if oc else SYNCED
        fa, fb = facts(s.text, kinds), facts(o.text, kinds)
        differs = {}
        for name in ('refs', 'labels', 'cites', 'values'):
            a, b = getattr(fa, name), getattr(fb, name)
            if a != b:
                differs[name] = (sorted(a - b), sorted(b - a))
        rows.append(Row(s.key, state, s, o, differs))
    keys = {s.key for s in ms}
    rows += [Row(o.key, ONLY_OTHER, None, o) for o in os_ if o.key not in keys]
    return rows


def mark(cfg, main, other, keys=None) -> list:
    """対応する節の今の中身を「合わせた」と記録する。keys がなければ対応する節すべて。
    戻り値は記録した鍵。知らない鍵は SystemExit。"""
    rows = {r.key: r for r in status(cfg, main, other) if r.main is not None and r.other is not None}
    if keys:
        bad = [k for k in keys if k not in rows]
        if bad:
            raise SystemExit(t('no section in both manuscripts: {keys}', keys=', '.join(bad)))
    chosen = list(keys) if keys else list(rows)
    rec = load_record(main)
    mine = rec.setdefault(other.lang or '', {})
    for k in chosen:
        mine[k] = {'main': rows[k].main.digest(), 'other': rows[k].other.digest()}
    # 両方の原稿から消えた節の記録は落とす
    live = {r.key for r in status(cfg, main, other)}
    for k in [k for k in mine if k not in live]:
        del mine[k]
    p = record_path(main)
    p.write_text(json.dumps(rec, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    return chosen


def state_text(state: str) -> str:
    return {SYNCED: t('matched'), UNSYNCED: t('never matched'),
            MAIN_CHANGED: t('the main manuscript changed'), OTHER_CHANGED: t('this language changed'),
            BOTH_CHANGED: t('both changed'), ONLY_MAIN: t('only in the main manuscript'),
            ONLY_OTHER: t('only in this language')}[state]


def differs_text(differs: dict) -> list:
    names = {'refs': t('references'), 'labels': t('labels'), 'cites': t('citations'),
             'values': t('values')}
    out = []
    for k, (a, b) in differs.items():
        bits = []
        if a:
            bits.append(t('only in the main manuscript: {items}', items=', '.join(a)))
        if b:
            bits.append(t('only in this language: {items}', items=', '.join(b)))
        out.append(f'{names[k]}: ' + '; '.join(bits))
    return out


def material(cfg, main, other, key: str) -> str:
    """節 key を訳す・合わせるための材料（AI か人に渡す）。原稿は書き換えない。"""
    rows = {r.key: r for r in status(cfg, main, other)}
    if key not in rows:
        raise SystemExit(t('no section called {key} (octavo translation {doc} lists them)',
                           key=key, doc=main.name))
    r = rows[key]
    mlang = cfg.for_document(main)['lang']
    olang = cfg.for_document(other)['lang']
    out = [t('# Section {key}: {state}', key=key, state=state_text(r.state)), '',
           t('The main manuscript ({main_lang}) and the one in {other_lang} should say the same thing. '
             'Translate or adjust the side that is behind; keep every label, reference (@fig-…), '
             'citation and {{value}} exactly as it is; do not translate them.',
             main_lang=mlang, other_lang=olang), '']
    for title, s, d in ((t('Main manuscript'), r.main, main),
                        (t('Manuscript in {lang}', lang=olang), r.other, other)):
        src = (d.appendix if s is not None and s.part == 'appendix' else d.src)
        out.append(f'## {title} — {cfg.rel(Path(src))}' + (f':{s.line}' if s else ''))
        out += ['', s.text.strip() if s else t('(not written yet)'), '']
    if r.differs:
        out += [t('## What differs'), ''] + [f'- {x}' for x in differs_text(r.differs)] + ['']
    terms = Path(cfg.root) / TERMS
    if terms.is_file():
        out += [t('## Terms ({file})', file=TERMS.as_posix()), '',
                terms.read_text(encoding='utf-8').strip(), '']
    out.append(t('When the two agree, record it with: octavo translation {doc} --mark {key}',
                 doc=other.name, key=key))
    return '\n'.join(out) + '\n'


def collect(cfg) -> list:
    """octavo check のための注意: [(文書の名前, 行)]。"""
    out = []
    for main, other in pairs(cfg):
        rows = status(cfg, main, other)
        for r in rows:
            if r.state in (ONLY_MAIN, ONLY_OTHER):
                s = r.main or r.other
                out.append((other.name, f'{r.key} ({s.title}): {state_text(r.state)}'))
            elif r.differs:
                out.append((other.name, f'{r.key}: ' + '; '.join(differs_text(r.differs))))
        stale = [r.key for r in rows if r.state in (MAIN_CHANGED, OTHER_CHANGED, BOTH_CHANGED)]
        if stale:
            out.append((other.name, t('changed since they were last matched: {keys}',
                                      keys=', '.join(stale))))
    return out
