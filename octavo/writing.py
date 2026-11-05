# -*- coding: utf-8 -*-
"""文章の決まり（ルール）とフレーズバンク。AI に渡して、それに沿って書かせるためのもの。

    octavo writing                         パックとファイルの一覧
    octavo writing --for DOC [--section S] その原稿が使う分（節を言えばその節のフレーズも）
    octavo writing --file F --line N       その行の見出しから節を選ぶ（原稿は F から決まる）
    octavo writing ... --print             一覧ではなく、重ねた本文（AI はこれを読む）
    octavo writing ... --json              同じものを機械可読で

置き場所は2つ（同じパックの同じ名前のファイルなら、後ろのほうを使う）:

  1. 自分の全部     $XDG_CONFIG_HOME/octavo/writing/（既定 ~/.config/octavo/writing/）
  2. プロジェクト   <プロジェクト>/notes/writing/（前からの <プロジェクト>/writing/ も読む）

**パック**は、その下のフォルダ1つ（`academic-en/` など）。中に `pack.md`（任意。冒頭に
title / extends / sections）と `rules/*.md`・`phrases/*.md`。置き場所の直下に
`rules/`・`phrases/` があれば、それは名前 `local` のパック（前からの置き方）で、いつも
いちばん後ろに重なる。

使うパックは設定 `writing`（プロジェクト）か原稿の冒頭の `writing:`（その原稿だけ）に、
一般的なものから順に並べる。`extends` に書いたパックは、その前に自動で入る。ぶつかったら
後ろが勝つ。書かなければ見つかったパックを全部使う。`writing_off` に `パック/ファイル#見出し`
（または `パック/ファイル`）を並べると、その項目（ファイル）を使わない（設定と原稿の分を合わせる）。

ファイルの冒頭には title / lang（ja・en）/ applies（paper・slides・lecture・poster・all）/
section（下の SECTIONS か、パックが sections で足した名前。書かなければ、いつも読む）。
1つの項目を `## 見出し` 1つで書く:

  ルール       ## 規則の名前 の下に「規則:」「理由:」「良い例:」「悪い例:」の行
               （英語なら Rule: / Why: / Good: / Bad:。規則のほかは任意）
  フレーズ     ## 場面の名前 の下に、使ってよい表現を箇条書き（`- `）で。差し替える所は
               〈分野〉のように山括弧で。「場面:」「注意:」「出典:」の行は任意

Octavo は中身を解釈しない（AI がそのまま読む）。ここでするのは、パックを選んで並べ、
節と原稿の種類・言語で絞り、`## 見出し` で項目を切って使わないものを除くことだけ。
"""
from __future__ import annotations

import re
from pathlib import Path

from . import config as configmod
from . import md as mdlib
from . import paragraphs as paramod
from . import tmpl
from .i18n import t

KINDS = ('rules', 'phrases')
LOCAL = 'local'

# 組み込みの節と、原稿の見出しから節を選ぶための言い方（小文字で、見出しのどこかに含まれれば当たる。
# いくつも当たれば、見出しの中で先に出るもの）
SECTIONS = {
    'abstract': ('abstract', '要旨', '概要'),
    'introduction': ('introduction', 'overview', 'はじめに', '序論', '問題の所在'),
    'literature': ('literature', 'previous research', 'prior research', 'existing research',
                   'related work', 'background', '先行研究'),
    'theory': ('theor', 'hypothes', 'argument', 'framework', 'expectation', '理論', '仮説'),
    'design': ('data', 'method', 'research design', 'empirical strategy', 'identification',
               'measure', 'variable', 'estimation', 'sample', 'case selection', 'design',
               'データ', '方法', '手法', 'リサーチデザイン', '分析の枠組み'),
    'results': ('result', 'finding', 'analysis', 'estimate', 'evidence', '結果', '分析'),
    'discussion': ('discussion', 'robustness', 'sensitivity', 'limitation', 'mechanism',
                   '考察', '頑健性', '限界'),
    'conclusion': ('conclu', 'implication', 'おわりに', '結論', '結び'),
    'appendix': ('appendix', 'supplement', '付録'),
}
# 原稿の種類（applies に書く名前）。出力から決める
APPLIES = ('paper', 'slides', 'lecture', 'poster', 'all')


def user_dir() -> Path:
    return tmpl.user_dir().parent / 'writing'


def bases(root: Path) -> list:
    """置き場所。後ろのものが前のものを上書きする: 自分の全部 < 前からの writing/ < notes/writing/"""
    return [('user', user_dir()), ('project', Path(root) / 'writing'),
            ('project', Path(root) / 'notes' / 'writing')]


def _as_list(v) -> list:
    if v is None:
        return []
    if isinstance(v, str):
        v = v.strip()
        if v.startswith('[') and v.endswith(']'):
            v = v[1:-1]
        return [x.strip().strip('"\'') for x in re.split(r'[,;]', v) if x.strip()]
    return [str(x).strip() for x in v if str(x).strip()]


def slug(title: str) -> str:
    s = re.sub(r'[^\w]+', '-', title.strip().lower()).strip('-')
    return s or 'entry'


def _split_entries(body: str) -> tuple:
    """本文を (冒頭の文, [(見出し, 本文, 行の位置)]) に。``` の中の ## は見出しにしない。"""
    head, entries, cur = [], [], None
    fence = False
    for i, line in enumerate(body.split('\n')):
        if re.match(r'\s*(```|~~~)', line):
            fence = not fence
        m = None if fence else re.match(r'##\s+(.+?)\s*#*\s*$', line)
        if m and not line.startswith('###'):
            cur = [m.group(1), [line], i]
            entries.append(cur)
        elif cur is None:
            head.append(line)
        else:
            cur[1].append(line)
    return '\n'.join(head).strip(), [(e[0], '\n'.join(e[1]).rstrip(), e[2]) for e in entries]


def describe(path: Path) -> dict:
    """1つのファイルの title / lang / applies / section と、項目（`## 見出し`）。"""
    text = mdlib.read(path)
    meta, body = mdlib.split_front_matter(text)
    offset = text[:len(text) - len(body)].count('\n')
    _, entries = _split_entries(body)
    seen: dict = {}
    items = []
    for title, _, line in entries:
        s = slug(title)
        seen[s] = seen.get(s, 0) + 1
        if seen[s] > 1:
            s = f'{s}-{seen[s]}'
        items.append({'title': title, 'slug': s, 'line': offset + line + 1})
    return {'path': str(path), 'title': meta.get('title') or path.stem,
            'lang': meta.get('lang') or '', 'applies': _as_list(meta.get('applies')) or ['all'],
            'section': _as_list(meta.get('section')) or ['all'],
            'entries': len(items), 'items': items}


# ---------------------------------------------------------------- 見つける
def packs(root: Path) -> dict:
    """{パック名: {'name', 'title', 'path', 'where', 'extends', 'sections', 'files': {(kind, ファイル名): (Path, where)}}}"""
    out: dict = {}

    def pack(name, where, d):
        p = out.setdefault(name, {'name': name, 'title': name if name != LOCAL else t('loose files'),
                                  'path': str(d), 'where': where, 'extends': [], 'sections': [],
                                  'description': '', 'files': {}})
        p['path'], p['where'] = str(d), where
        meta_file = d / 'pack.md'
        if name != LOCAL and meta_file.is_file():
            meta, body = mdlib.split_front_matter(mdlib.read(meta_file))
            p['title'] = meta.get('title') or name
            p['extends'] = _as_list(meta.get('extends'))
            p['sections'] = _as_list(meta.get('sections'))
            p['description'] = body.strip().split('\n\n')[0] if body.strip() else ''
        for kind in KINDS:
            k = d / kind
            if k.is_dir():
                for f in sorted(k.glob('*.md')):
                    if f.name.lower() != 'readme.md':
                        p['files'][(kind, f.name)] = (f, where)

    for where, base in bases(root):
        if not base.is_dir():
            continue
        if any((base / k).is_dir() for k in KINDS):
            pack(LOCAL, where, base)
        for d in sorted(base.iterdir()):
            if d.is_dir() and not d.name.startswith('.') and d.name not in KINDS \
                    and ((d / 'pack.md').is_file() or any((d / k).is_dir() for k in KINDS)):
                pack(d.name, where, d)
    return out


def files(root: Path) -> dict:
    """{'rules': [(Path, 'project'|'user')], 'phrases': […]}（すべてのパック）。"""
    got = packs(root)
    out: dict = {kind: [] for kind in KINDS}
    for name in default_order(got):
        for (kind, _), v in sorted(got[name]['files'].items()):
            out[kind].append(v)
    return out


def default_order(got: dict) -> list:
    """指定が無いときの並び: extends を前に、あとは名前の順。local はいちばん後ろ。"""
    names = sorted(n for n in got if n != LOCAL)
    order: list = []

    def add(n, stack=()):
        if n in order or n not in got or n in stack:
            return
        for e in got[n]['extends']:
            add(e, stack + (n,))
        order.append(n)
    for n in names:
        add(n)
    return order + ([LOCAL] if LOCAL in got else [])


def choose(got: dict, wanted) -> tuple:
    """使うパックの並びと警告。wanted が None なら全部。"""
    if wanted is None:
        return default_order(got), []
    order: list = []
    warnings: list = []

    def add(n, stack=()):
        if n in order or n in stack:
            return
        if n not in got:
            warnings.append(t('no writing pack called {name} (packs: {names})', name=n,
                              names=', '.join(sorted(got)) or t('(none)')))
            return
        for e in got[n]['extends']:
            add(e, stack + (n,))
        order.append(n)
    for n in _as_list(wanted):
        add(n)
    if LOCAL in got and LOCAL not in order:
        order.append(LOCAL)
    return order, warnings


def known_sections(got: dict) -> list:
    out = list(SECTIONS)
    for p in got.values():
        out += [s for s in p['sections'] if s not in out]
    return out


def collect(root: Path) -> dict:
    """すべてのパックのファイル（前からの形: kind ごとの並び）と、パック・警告。"""
    got = packs(root)
    valid = set(known_sections(got)) | {'all'}
    out: dict = {kind: [] for kind in KINDS}
    warnings: list = []
    for name in default_order(got):
        for (kind, _), (path, where) in sorted(got[name]['files'].items()):
            d = {**describe(path), 'where': where, 'pack': name, 'kind': kind}
            d.pop('items')
            out[kind].append(d)
            warnings += [t('{file}: unknown section {name} (sections: {names})', file=path, name=s,
                           names=', '.join(known_sections(got)))
                         for s in d['section'] if s not in valid]
    out['packs'] = [{k: v for k, v in got[n].items() if k != 'files'} | {'files': len(got[n]['files'])}
                    for n in default_order(got)]
    out['sections'] = known_sections(got)
    out['warnings'] = warnings
    return out


# ---------------------------------------------------------------- 原稿に合わせる
def doc_kinds(doc) -> set:
    """原稿の種類（applies の名前）。出力から決める。"""
    outs = set(doc.outputs)
    kinds = set()
    if doc.profile == 'paper' or (doc.profile == 'handout' and not doc.sessions) or outs & {'word', 'tex'}:
        kinds.add('paper')
    if doc.sessions:
        kinds.add('lecture')
    if outs & {'slides', 'beamer', 'script', 'slides-handout'} or doc.profile == 'slides':
        kinds.add('slides')
    if 'poster' in outs or doc.profile == 'poster':
        kinds.add('poster')
    return kinds or {'paper'}


def doc_for_file(cfg, path: Path):
    """そのファイルを原稿（か付録）にしている文書。"""
    p = Path(path).resolve()
    for d in cfg.documents.values():
        if Path(d.src).resolve() == p or (d.appendix and Path(d.appendix).resolve() == p):
            return d
    return None


def section_at(text: str, line: int, known: list, appendix: bool = False) -> tuple:
    """line 行目（1から）が属す見出しから節を選ぶ。(節, その見出し)。当たらなければ (None, None)。

    近い見出しから順に、より浅い見出しへさかのぼり、最初に節に当たったものを使う。
    """
    if appendix:
        return 'appendix', None
    meta_end = 0
    m = mdlib.FRONT_MATTER.match(text)
    if m:
        meta_end = text[:m.end()].count('\n')
    heads = []                  # (行, 深さ, 見出し, 付録か)
    fence = False
    for i, raw in enumerate(text.split('\n')[:max(line, 0)]):
        if i < meta_end:
            continue
        if re.match(r'\s*(```|~~~)', raw):
            fence = not fence
            continue
        h = None if fence else re.match(r'(#{1,6})\s+(.+?)\s*$', raw)
        if h:
            title = h.group(2)
            heads.append((len(h.group(1)), re.sub(r'\s*\{[^}]*\}\s*$', '', title).strip(),
                          bool(re.search(r'\{[^}]*\.appendix\b', title))))
    if any(a for _, _, a in heads):
        return 'appendix', next(tt for _, tt, a in reversed(heads) if a)
    depth = 7
    for level, title, _ in reversed(heads):
        if level >= depth:
            continue
        depth = level
        s = match_section(title, known)
        if s:
            return s, title
    return None, None


def match_section(title: str, known: list):
    """見出しに当たる節。パックが足した節を先に見る（組み込みの言い方より具体的なので）。"""
    own = [n for n in known if n not in SECTIONS]
    return (_match(title, own) if own else None) or _match(title, [n for n in known if n in SECTIONS])


def _match(title: str, known: list):
    low = title.lower()
    best = None
    for name in known:
        words = SECTIONS.get(name, (name.replace('-', ' '),))
        for w in words:
            at = low.find(w)
            if at >= 0 and (best is None or at < best[0]):
                best = (at, name)
    return best[1] if best else None


def select(cfg, doc, section=None, every=False, kinds=None) -> dict:
    """その原稿が使うパック・ファイル・項目。section が None なら、いつも読むファイルだけ。

    kinds（段落の種類の並び。`パック/ファイル#slug` か `ファイル#slug`）を渡すと、フレーズは
    その項目だけになる（節・原稿の種類を問わず、ファイルをまたいでよい）。ルールは今までどおり。
    """
    root = Path(cfg.root)
    got = packs(root)
    view = cfg.for_document(doc)
    own = configmod.doc_settings(doc.src)
    order, warnings = choose(got, view.get('writing'))
    off = list(dict.fromkeys(_as_list(cfg.get('writing_off')) + _as_list(own.get('writing_off'))))
    known = known_sections(got)
    if section is not None and section not in known:
        raise SystemExit(t('unknown section {name} (sections: {names})', name=section,
                           names=', '.join(known)))
    doc_kinds_ = doc_kinds(doc)
    lang = view.get('lang') or ''
    out_files = []
    for name in order:
        for (kind, fname), (path, where) in sorted(got[name]['files'].items(),
                                                     key=lambda x: (KINDS.index(x[0][0]), x[0][1])):
            d = describe(path)
            stem = Path(fname).stem
            fid = f'{name}/{stem}'
            secs = d['section']
            reason = None
            if 'all' not in d['applies'] and not doc_kinds_ & set(d['applies']):
                reason = 'applies'
            elif d['lang'] and lang and d['lang'] != lang:
                reason = 'lang'
            elif fid in off:
                reason = 'off'
            elif not every and 'all' not in secs and section not in secs:
                reason = 'section'
            for it in d['items']:
                it['id'] = f'{fid}#{it["slug"]}'
                it['off'] = it['id'] in off or f'{stem}#{it["slug"]}' in off
            if kind == 'phrases':
                _, entries = _split_entries(mdlib.split_front_matter(mdlib.read(path))[1])
                for it, (_, block, _) in zip(d['items'], entries):
                    it.update(paramod.entry_fields(block))
            out_files.append({**d, 'pack': name, 'kind': kind, 'where': where, 'id': fid,
                              'used': reason is None, 'skipped': reason})
    picked: list = []
    if kinds is not None:
        index = kind_index({'files': out_files})
        for k in kinds:
            hit = paramod.resolve(k, index)
            if hit is None:
                near = paramod.suggest(k, index)
                warnings.append(t('no paragraph kind called {kind}', kind=k)
                                + (' ' + t('(did you mean {names}?)', names=', '.join(near)) if near else ''))
            elif hit not in picked:
                picked.append(hit)
                if index[hit]['off']:
                    warnings.append(t('{kind} is turned off in writing_off, but this paragraph names it',
                                      kind=hit))
        for f in out_files:
            if f['kind'] != 'phrases':
                continue
            for it in f['items']:
                it['picked'] = it['id'] in picked
            f['used'] = any(it['picked'] for it in f['items'])
            f['skipped'] = None if f['used'] else 'kind'
    unknown = [x for x in off if not any(x == f['id'] or any(x in (i['id'], i['id'].split('/', 1)[1])
                                                              for i in f['items']) for f in out_files)]
    warnings += [t('writing_off names nothing: {id}', id=x) for x in unknown]
    return {'doc': doc.name, 'packs': order, 'chosen': view.get('writing') is not None,
            'paragraph_kinds': picked if kinds is not None else None, 'paragraph': None,
            'chosen_here': 'writing' in own, 'kinds': sorted(doc_kinds_), 'lang': lang,
            'section': section, 'sections': known, 'off': off,
            'off_here': _as_list(own.get('writing_off')), 'files': out_files,
            'warnings': warnings}


def kind_index(sel: dict) -> dict:
    """段落の種類（フレーズの項目）の id -> 項目。選んだパックのフレーズのファイルすべてから。"""
    return {it['id']: {**it, 'file': f['id'], 'file_title': f['title']}
            for f in sel['files'] if f['kind'] == 'phrases' for it in f['items']}


def render(sel: dict, heading: str | None = None) -> str:
    """選んだ分を1つの Markdown に（AI が読むもの）。使わない項目は除く。"""
    lines = [f"<!-- octavo writing: {sel['doc']}"
             + (f", section: {sel['section']}" if sel['section'] else '')
             + (f' (heading "{heading}")' if heading else '') + ' -->',
             '<!-- ' + t('packs, general first: {order}. Where two disagree, the later one wins.',
                         order=' → '.join(sel['packs']) or t('(none)')) + ' -->', '']
    para = sel.get('paragraph')
    if para and (para.get('kind') or para.get('claim')):
        lines += ['<!-- ' + t('this paragraph (line {line}): kind {kind}', line=para['line'],
                              kind=para.get('kind') or t('(none yet)'))
                  + ('; ' + t('it claims: {claim}', claim=para['claim']) if para.get('claim') else '')
                  + ' -->', '']
    picking = sel.get('paragraph_kinds') is not None
    for kind, head in (('rules', t('Writing rules (follow them)')),
                       ('phrases', t('Phrase bank (frames to draw on where they fit; most sentences need none)'))):
        used = [f for f in sel['files'] if f['kind'] == kind and f['used']]
        if not used:
            continue
        lines += [f'# {head}', '']
        for f in used:
            text = mdlib.read(Path(f['path']))
            _, body = mdlib.split_front_matter(text)
            pre, entries = _split_entries(body)
            lines += [f"# {f['pack']}: {f['title']}", f"<!-- {f['id']} -->", '']
            if pre:
                lines += [pre, '']
            for it, (_, block, _) in zip(f['items'], entries):
                if picking and kind == 'phrases':
                    if it.get('picked'):
                        lines += [block, '']
                elif not it['off']:
                    lines += [block, '']
    return '\n'.join(lines).rstrip() + '\n'
