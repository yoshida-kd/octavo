# -*- coding: utf-8 -*-
"""文章の決まり（ルール）とフレーズバンク。AI に渡して、それに沿って書かせるためのもの。

    octavo writing                         パックとファイルの一覧
    octavo writing --for DOC [--section S] その原稿が使う分（節を言えばその節のフレーズも）
    octavo writing --file F --line N       その行の見出しから節を選ぶ（原稿は F から決まる）
    octavo writing ... --print             一覧ではなく、重ねた本文（AI はこれを読む）
    octavo writing ... --section-only      いつも読むファイルを除いて、その節のファイルだけ（節を移ったとき）
    octavo writing --for DOC --flags       ルールの `Flag:` に当たった行（読み直す所）
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
フレーズのファイルに `entries: sentences` と書くと、その項目は段落の種類ではなく、1つの段落の中の
文の順（要旨など）。節のフレーズがそういうファイルだけなら、その節の段落に種類は求めない。
1つの項目を `## 見出し` 1つで書く:

  ルール       ## 規則の名前 の下に「規則:」「理由:」「良い例:」「悪い例:」の行
               （英語なら Rule: / Why: / Good: / Bad:。規則のほかは任意）。
               `Flag: 正規表現`（`検出:` でもよい。1行に1つ、何行でも）を書くと、当たった原稿の行を
               `--flags` が並べる。使い方の正誤は判断しない（人か AI が読み直す所を示すだけ）
  フレーズ     ## 場面の名前 の下に、使ってよい表現を箇条書き（`- `）で。差し替える所は
               〈分野〉のように山括弧で。「場面:」「注意:」「出典:」の行は任意

Octavo は中身を解釈しない（AI がそのまま読む）。ここでするのは、パックを選んで並べ、
節と原稿の種類・言語で絞り、`## 見出し` で項目を切って使わないものを除くことだけ。
読む欄は、フレーズの When / Note / Source / Contains / Repeat と行の Open / Body / Close
（paragraphs.py）、ルールの Flag だけ。
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
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


# 項目の中の、Octavo が読む欄（1行に1つ。``` の中は読まない）。AI に渡すときは外す
ENTRY_FIELD = re.compile(r'^\s*(Id|ID|Alias|別名|Stage|段階|Section|節|Scope|範囲|Replaces|置き換え'
                         r'|Count|数える|Good|良い例|Bad|悪い例)\s*[:：]\s*(.*?)\s*$')
FIELD_KEYS = {'id': 'id', 'alias': 'alias', '別名': 'alias', 'stage': 'stage', '段階': 'stage',
              'section': 'section', '節': 'section', 'scope': 'scope', '範囲': 'scope',
              'replaces': 'replaces', '置き換え': 'replaces', 'count': 'count', '数える': 'count',
              'good': 'good', '良い例': 'good', 'bad': 'bad', '悪い例': 'bad'}
# 渡すときに外す欄（例は AI が読むので残す）
MACHINE_FIELDS = ('id', 'alias', 'stage', 'section', 'scope', 'replaces', 'count')
# いつ読むか。draft = 書くときに読み、推敲でも当てる（既定）、revise = 推敲のときだけ、
# lookup = Flag の語が本文にあるときだけ
STAGES = ('draft', 'revise', 'lookup')
STAGE_NAMES = {'both': 'draft', '執筆': 'draft', '推敲': 'revise', '参照': 'lookup'}
# どこに当てるか（推敲で、何を AI に渡し、Flag をどこに当てるか）
SCOPES = ('sentence', 'paragraph', 'first-sentence', 'last-sentence', 'section', 'document')
COUNT = re.compile(r'^(?P<pat>.+?)\s+per\s+(?P<unit>sentence|paragraph|section)\s*(?P<op>>=|>|≥)\s*(?P<n>\d+)\s*$')


def _unquote(src: str) -> str:
    src = src.strip()
    if len(src) > 2 and src.startswith('`') and src.endswith('`'):
        return src[1:-1]
    return src


def _example(text: str) -> str:
    """良い例・悪い例の1行から、引用の印と括弧を外した文。"""
    s = re.sub(r'^\s*(?:>\s?|[-*+]\s+)', '', text).strip()
    if len(s) > 1 and s[0] in '"“「\'' and s[-1] in '"”」\'':
        s = s[1:-1]
    return s.strip()


def entry_meta(block: str) -> dict:
    """項目の塊から Octavo が読む欄を。値の無い Good: / Bad: は、続く `- ` か `> ` の行が例。"""
    out = {'id': '', 'aliases': [], 'stage': '', 'section': [], 'scope': '', 'replaces': [],
           'counts': [], 'good': [], 'bad': [], 'flags': [], 'problems': []}
    fence, collecting = False, None
    for ln in block.split('\n')[1:]:
        if re.match(r'\s*(```|~~~)', ln):
            fence = not fence
            collecting = None
            continue
        if fence:
            continue
        m = FLAG.match(ln)
        if m:
            out['flags'].append(_unquote(m.group(1)))
            collecting = None
            continue
        m = ENTRY_FIELD.match(ln)
        if m:
            key, value = FIELD_KEYS[m.group(1).lower() if m.group(1).isascii() else m.group(1)], m.group(2)
            collecting = None
            if key == 'id':
                out['id'] = slug(value) if value else ''
            elif key == 'alias':
                out['aliases'] += [slug(x) for x in _as_list(value)]
            elif key == 'stage':
                v = value.strip().lower()
                v = STAGE_NAMES.get(v, v)
                if v in STAGES:
                    out['stage'] = v
                else:
                    out['problems'].append(t('unknown Stage {value} (stages: {names})', value=value,
                                             names=', '.join(STAGES)))
            elif key == 'section':
                out['section'] = _as_list(value)
            elif key == 'scope':
                v = value.strip().lower()
                if v in SCOPES:
                    out['scope'] = v
                else:
                    out['problems'].append(t('unknown Scope {value} (scopes: {names})', value=value,
                                             names=', '.join(SCOPES)))
            elif key == 'replaces':
                out['replaces'] += _as_list(value)
            elif key == 'count':
                c = COUNT.match(value)
                if c:
                    out['counts'].append({'pattern': _unquote(c.group('pat')), 'unit': c.group('unit'),
                                          'over': int(c.group('n')) - (1 if c.group('op') != '>' else 0)})
                else:
                    out['problems'].append(t('Count should read "<pattern> per paragraph > N" '
                                             '(sentence, paragraph or section): {value}', value=value))
            elif key in ('good', 'bad'):
                if value:
                    out[key].append(_example(value))
                else:
                    collecting = key
            continue
        if collecting and re.match(r'\s*(?:[-*+]\s+|>)', ln):
            out[collecting].append(_example(ln))
        elif ln.strip():
            collecting = None
    return out


def for_reader(block: str) -> str:
    """AI に渡す形: Octavo だけが読む欄（Id・Stage・Flag・Count など）を外す。"""
    keep, fence = [], False
    for ln in block.split('\n'):
        if re.match(r'\s*(```|~~~)', ln):
            fence = not fence
        if not fence:
            m = ENTRY_FIELD.match(ln)
            if FLAG.match(ln) or (m and FIELD_KEYS[m.group(1).lower() if m.group(1).isascii()
                                                   else m.group(1)] in MACHINE_FIELDS):
                continue
        keep.append(ln)
    return '\n'.join(keep).rstrip()


def describe(path: Path) -> dict:
    """1つのファイルの title / lang / applies / section と、項目（`## 見出し`）。

    項目には Octavo が読む欄（entry_meta）も付ける。`Id:` があればそれが slug（見出しを直しても
    変わらない）で、見出しから作った slug と `Alias:` は別名として残る。`Stage:` と `Scope:` は
    ファイルの冒頭の stage / scope が既定、`Section:` はファイルの section を項目だけ上書きする。
    """
    text = mdlib.read(path)
    meta, body = mdlib.split_front_matter(text)
    offset = text[:len(text) - len(body)].count('\n')
    _, entries = _split_entries(body)
    fstage = STAGE_NAMES.get(str(meta.get('stage') or '').strip().lower(),
                             str(meta.get('stage') or '').strip().lower())
    fstage = fstage if fstage in STAGES else 'draft'
    fscope = str(meta.get('scope') or '').strip().lower()
    fscope = fscope if fscope in SCOPES else 'sentence'
    fsections = _as_list(meta.get('section')) or ['all']
    seen: dict = {}
    items = []
    for title, block, line in entries:
        em = entry_meta(block)
        made = slug(title)
        s = em['id'] or made
        seen[s] = seen.get(s, 0) + 1
        if seen[s] > 1:
            if em['id']:
                em['problems'].append(t('Id {id} is used twice in this file', id=em['id']))
            s = f'{s}-{seen[s]}'
        aliases = [a for a in dict.fromkeys(em['aliases'] + ([made] if em['id'] and made != s else []))
                   if a != s]
        items.append({'title': title, 'slug': s, 'line': offset + line + 1, 'aliases': aliases,
                      'stage': em['stage'] or fstage, 'scope': em['scope'] or fscope,
                      'sections': em['section'] or fsections, 'replaces': em['replaces'],
                      'flags': em['flags'], 'counts': em['counts'], 'good': em['good'],
                      'bad': em['bad'], 'problems': em['problems']})
    return {'path': str(path), 'title': meta.get('title') or path.stem,
            'lang': meta.get('lang') or '', 'applies': _as_list(meta.get('applies')) or ['all'],
            'section': _as_list(meta.get('section')) or ['all'],
            'entry_kind': 'sentences' if str(meta.get('entries') or '').strip().lower() == 'sentences'
            else 'paragraphs',
            'entries': len(items), 'items': items}


# ---------------------------------------------------------------- 見つける
# ---------------------------------------------------------------- パックの版
# `writing: ['academic-en@v2']`（extends にも書ける）は、そのパックを今のフォルダではなく git の版から
# 読む。版は、パックのある git リポジトリのタグ `academic-en@v2`、無ければ `v2`（タグでも commit でも）。
# 読んだ版は ~/.cache/octavo/writing/ に書き出す（commit ごと。消してもよい）。パックを直し続けても、
# 版を書いたプロジェクトは、書き換えるまで同じルールで書ける。
PIN = re.compile(r'^(?P<name>[^@\s]+)@(?P<ref>[^@\s]+)$')
PACK_FILE = re.compile(r'^(?:pack\.md|(?:rules|phrases)/[^/]+\.md)$')


def split_pins(wanted) -> tuple:
    """`writing` の並びを (パック名の並び, {名前: 版})。wanted が None なら (None, {})。"""
    if wanted is None:
        return None, {}
    names, pins = [], {}
    for x in _as_list(wanted):
        m = PIN.match(x)
        if m:
            names.append(m.group('name'))
            pins.setdefault(m.group('name'), m.group('ref'))
        else:
            names.append(x)
    return names, pins


def cache_dir() -> Path:
    base = os.environ.get('XDG_CACHE_HOME') or (Path.home() / '.cache')
    return Path(base) / 'octavo' / 'writing'


def _git(d: Path, *args, binary: bool = False):
    if binary:
        return subprocess.run(['git', '-C', str(d), *args], capture_output=True)
    return subprocess.run(['git', '-C', str(d), *args], capture_output=True, text=True, encoding='utf-8',
                          errors='replace')


def _repo(d: Path):
    """(リポジトリの一番上, その中でのパックの場所) か None（git が無い・リポジトリの外）。"""
    if not shutil.which('git'):
        return None
    d = d.resolve()
    r = _git(d, 'rev-parse', '--show-toplevel')
    if r.returncode != 0 or not r.stdout.strip():
        return None
    top = Path(r.stdout.strip()).resolve()
    try:
        rel = d.relative_to(top).as_posix()
    except ValueError:
        return None
    return top, '' if rel == '.' else rel


def versions(d: Path, name: str) -> list:
    """そのパックの版（タグ `名前@版` の版の部分）。古い順。"""
    got = _repo(Path(d))
    if got is None:
        return []
    r = _git(got[0], 'tag', '--list', f'{name}@*', '--sort=version:refname')
    return [x.split('@', 1)[1] for x in r.stdout.split() if '@' in x] if r.returncode == 0 else []


def pinned(d: Path, name: str, ref: str):
    """パックのフォルダ d の版 ref を書き出した場所と commit。(Path, sha) か None（その版が無い）。"""
    got = _repo(Path(d))
    if got is None:
        return None
    top, rel = got
    sha = None
    for cand in (f'{name}@{ref}', ref):
        r = _git(top, 'rev-parse', '--verify', '--quiet', f'{cand}^{{commit}}')
        if r.returncode == 0 and r.stdout.strip():
            sha = r.stdout.strip()
            break
    if sha is None:
        return None
    dest = cache_dir() / f'{name}-{sha}'
    if (dest / '.complete').is_file():
        return dest, sha
    r = _git(top, 'ls-tree', '-r', '-z', '--name-only', sha, '--', rel or '.', binary=True)
    if r.returncode != 0:
        return None
    paths = [x.decode('utf-8', 'replace') for x in r.stdout.split(b'\0') if x]
    inside = [(p, p[len(rel) + 1:] if rel else p) for p in paths if not rel or p.startswith(rel + '/')]
    inside = [(p, q) for p, q in inside if PACK_FILE.match(q)]
    if not inside:
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=f'.{name}-', dir=dest.parent))
    try:
        for p, q in inside:
            body = _git(top, 'show', f'{sha}:{p}', binary=True)
            if body.returncode != 0:
                return None
            (tmp / q).parent.mkdir(parents=True, exist_ok=True)
            (tmp / q).write_bytes(body.stdout)
        (tmp / '.complete').write_text(f'{name}@{ref} {sha}\n', encoding='utf-8')
        try:
            os.replace(tmp, dest)
        except OSError:            # ほかのプロセスが先に書いた
            if not (dest / '.complete').is_file():
                raise
    finally:
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)
    return dest, sha


def pin_warnings(got: dict) -> list:
    """版を書いたのに、その版が見つからなかったパック（今のフォルダは読まない）。"""
    return [t('{pack}: no version {ref} (a git tag {pack}@{ref} or {ref} where the pack is); the pack '
              'is not used', pack=n, ref=p['pin'])
            for n, p in sorted(got.items()) if p.get('pin') and not p.get('commit')]


def packs(root: Path | None, dirs: list | None = None, pins: dict | None = None) -> dict:
    """{パック名: {'name', 'title', 'path', 'where', 'extends', 'sections', 'files': {(kind, ファイル名): (Path, where)}}}

    dirs を渡すと、置き場所の代わりにそれを読む（プロジェクトの外で、パックを作っている所から
    点検するため）。1つのパックのフォルダ（pack.md があるもの）を渡してもよい。

    pins（{名前: 版}）のパックは、git のその版から読む（上の「パックの版」）。版のある置き場所の
    分だけがその版になり、版の無い置き場所（プロジェクトで足したファイルなど）は今のまま重なる。
    どこにも版が無ければ、そのパックのファイルは読まない（pin_warnings が知らせる）。extends に
    `名前@版` があれば、load() がそれも版として読み直す。
    """
    return _packs(root, dirs, dict(pins or {}))


def load(root: Path, wanted, pins: dict | None = None) -> tuple:
    """使うパックを読む: (packs, 並び, 警告)。wanted が None なら全部。

    使うパックの extends に `名前@版` があれば、その版で読み直す（`writing` に書いた版が勝つ）。
    使わないパックの extends は効かない。
    """
    pins = dict(pins or {})
    for _ in range(8):
        got = packs(root, pins=pins)
        order, warnings = choose(got, wanted)
        more = {n: r for x in order for n, r in got[x].get('extends_pins', {}).items() if n not in pins}
        if not more:
            break
        pins.update(more)
    return got, order, pin_warnings(got) + warnings


def _packs(root: Path | None, dirs: list | None, pins: dict) -> dict:
    out: dict = {}

    def pack(name, where, d):
        p = out.setdefault(name, {'name': name, 'title': name if name != LOCAL else t('loose files'),
                                  'path': str(d), 'where': where, 'extends': [], 'sections': [],
                                  'description': '', 'files': {}})
        if name in pins and name != LOCAL:
            p['pin'] = pins[name]
            got = pinned(d, name, pins[name])
            if got is not None:
                d, p['commit'] = got[0], got[1]
                p['files'] = {}        # 版より前の置き場所の分は使わない
        p['path'], p['where'] = str(d), where
        meta_file = d / 'pack.md'
        if name != LOCAL and meta_file.is_file():
            meta, body = mdlib.split_front_matter(mdlib.read(meta_file))
            p['title'] = meta.get('title') or name
            ext, ext_pins = split_pins(_as_list(meta.get('extends')))
            p['extends'], p['extends_pins'] = ext, ext_pins
            p['sections'] = _as_list(meta.get('sections'))
            p['description'] = body.strip().split('\n\n')[0] if body.strip() else ''
        for kind in KINDS:
            k = d / kind
            if k.is_dir():
                for f in sorted(k.glob('*.md')):
                    if f.name.lower() != 'readme.md':
                        p['files'][(kind, f.name)] = (f, where)

    for where, base in ([('pack-dir', Path(d)) for d in dirs] if dirs is not None else bases(root)):
        if not base.is_dir():
            continue
        if where == 'pack-dir' and (base / 'pack.md').is_file():
            pack(base.resolve().name, where, base)
            continue
        if any((base / k).is_dir() for k in KINDS):
            pack(LOCAL, where, base)
        for d in sorted(base.iterdir()):
            if d.is_dir() and not d.name.startswith('.') and d.name not in KINDS \
                    and ((d / 'pack.md').is_file() or any((d / k).is_dir() for k in KINDS)):
                pack(d.name, where, d)
    for p in out.values():
        if p.get('pin') and not p.get('commit'):
            # その版がどこにも無い。今のフォルダを黙って使うと、版を書いた意味が無くなる
            p['files'], p['extends'], p['extends_pins'] = {}, [], {}
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


def extends_warnings(got: dict) -> list:
    """`extends` に書いたのに見つからないパック（打ち間違いは黙って効かなくなるので知らせる）。"""
    return [t('{pack}: extends {name}, but there is no pack called {name} (packs: {names})',
              pack=n, name=e, names=', '.join(sorted(got)))
            for n in sorted(got) for e in got[n]['extends'] if e not in got]


def _source(root, name: str, p: dict) -> Path:
    """パックの今のフォルダ（版から読んだなら、書き出した所ではなく元の所）。"""
    if not p.get('commit'):
        return Path(p['path'])
    for _, base in reversed(bases(root)) if root is not None else []:
        if (base / name).is_dir():
            return base / name
    return Path(p['path'])


def known_sections(got: dict) -> list:
    out = list(SECTIONS)
    for p in got.values():
        out += [s for s in p['sections'] if s not in out]
    return out


def collect(root: Path, pins: dict | None = None) -> dict:
    """すべてのパックのファイル（前からの形: kind ごとの並び）と、パック・警告。

    パックごとに、版を書いたならその版（pin）と commit、git のタグにある版の並び（versions）も。
    """
    got, _, warnings = load(root, None, pins)
    valid = set(known_sections(got)) | {'all'}
    out: dict = {kind: [] for kind in KINDS}
    warnings = extends_warnings(got) + warnings
    for name in default_order(got):
        for (kind, _), (path, where) in sorted(got[name]['files'].items()):
            d = {**describe(path), 'where': where, 'pack': name, 'kind': kind}
            d.pop('items')
            out[kind].append(d)
            warnings += [t('{file}: unknown section {name} (sections: {names})', file=path, name=s,
                           names=', '.join(known_sections(got)))
                         for s in d['section'] if s not in valid]
    out['packs'] = [{k: v for k, v in got[n].items() if k not in ('files', 'extends_pins')}
                    | {'files': len(got[n]['files']), 'pin': got[n].get('pin'),
                       'commit': got[n].get('commit'),
                       'versions': [] if n == LOCAL else versions(_source(root, n, got[n]), n)}
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

    近い見出しから順に、より浅い見出しへさかのぼり、最初に節に当たったものを使う。1つの見出しでは、
    ラベル（`{#sec-literature}`）が節の名前ならそれ、次に見出しの言葉、最後にラベルの言葉
    （`{#sec-data}` → design）。内容を言う見出し（"Adding Capacity When Work Rises"）には節の
    言い方が入らないので、ラベルが手がかりになる。
    """
    if appendix:
        return 'appendix', None
    heads = _headings(text, line)
    if any(a for _, _, a, _ in heads):
        return 'appendix', next(tt for _, tt, a, _ in reversed(heads) if a)
    depth = 7
    for level, title, _, label in reversed(heads):
        if level >= depth:
            continue
        depth = level
        s = label_section(label, known) or match_section(title, known) \
            or match_section(label.replace('-', ' '), known)
        if s:
            return s, title
    return None, None


def heading_at(text: str, line: int):
    """line 行目のすぐ上の見出し（無ければ None）。節が決まらなかったことを知らせるため。"""
    heads = _headings(text, line)
    return heads[-1][1] if heads else None


def label_section(label: str, known: list):
    """ラベル（`sec-` を除いたもの）が節の名前か、節の名前に `-…` が続くもの（`literature-2`）、
    1つの節の名前の頭4文字以上（`intro`）なら、その節。"""
    for name in sorted(known, key=len, reverse=True):
        if label == name or label.startswith(name + '-'):
            return name
    short = [name for name in known if len(label) >= 4 and name.startswith(label)]   # sec-intro
    return short[0] if len(short) == 1 else None


def _headings(text: str, line: int) -> list:
    """line 行目までの見出し [(深さ, 見出し, 付録か, ラベル)]。ラベルは `{#sec-x}` の x（無ければ ''）。"""
    meta_end = 0
    m = mdlib.FRONT_MATTER.match(text)
    if m:
        meta_end = text[:m.end()].count('\n')
    heads = []
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
            label = re.search(r'\{[^}]*#(?:sec-)?([\w-]+)[^}]*\}\s*$', title)
            heads.append((len(h.group(1)), re.sub(r'\s*\{[^}]*\}\s*$', '', title).strip(),
                          bool(re.search(r'\{[^}]*\.appendix\b', title)),
                          label.group(1).lower() if label else ''))
    return heads


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


def select(cfg, doc, section=None, every=False, kinds=None, section_only=False, stage: str = 'draft',
           lookup_in: list | None = None) -> dict:
    """その原稿が使うパック・ファイル・項目。section が None なら、いつも読むファイルだけ。

    section_only なら、いつも読むファイル（`section:` の無いもの）を除く。節を移るたびに同じ
    ルールをもう一度読ませないため（最初の1回は付けずに読む）。

    kinds（段落の種類の並び。`パック/ファイル#slug` か `ファイル#slug`）を渡すと、フレーズは
    その項目だけになる（節・原稿の種類を問わず、ファイルをまたいでよい）。ルールは今までどおり。

    stage は 'draft'（書くとき。`Stage: revise` のルールは除く）か 'revise'（推敲。すべて）。
    `Stage: lookup` のルールは、lookup_in（[(本文, 付録か)]）の中にその Flag の語があるときだけ使う。
    項目ごとの skipped は、使わないわけ（stage / lookup / section / always / replaced）か None。
    """
    root = Path(cfg.root)
    view = cfg.for_document(doc)
    own = configmod.doc_settings(doc.src)
    got, order, warnings = load(root, *split_pins(view.get('writing')))
    if view.get('writing') is None:
        warnings = extends_warnings(got) + warnings
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
            elif fid in off or stem in off:
                reason = 'off'
            for it in d['items']:
                it['id'] = f'{fid}#{it["slug"]}'
                names = [it['slug']] + it['aliases']
                it['off'] = any(f'{fid}#{n}' in off or f'{stem}#{n}' in off for n in names)
                it['skipped'] = None
                if every:
                    continue
                isecs = it['sections']
                if kind == 'rules' and stage == 'draft' and it['stage'] == 'revise':
                    it['skipped'] = 'stage'
                elif kind == 'rules' and it['stage'] == 'lookup':
                    it['skipped'] = 'lookup'
                elif 'all' not in isecs and section not in isecs:
                    it['skipped'] = 'section'
                elif section_only and 'all' in isecs:
                    it['skipped'] = 'always'
            if reason is None and not every:
                if not d['items']:
                    if 'all' not in secs and section not in secs:
                        reason = 'section'
                    elif section_only and 'all' in secs:
                        reason = 'always'
                elif all(it['skipped'] for it in d['items']):
                    why = {it['skipped'] for it in d['items']}
                    reason = next(w for w in ('section', 'always', 'stage', 'lookup') if w in why)
            if kind == 'phrases':
                _, entries = _split_entries(mdlib.split_front_matter(mdlib.read(path))[1])
                for it, (_, block, _) in zip(d['items'], entries):
                    it.update(paramod.entry_fields(block))
            out_files.append({**d, 'pack': name, 'kind': kind, 'where': where, 'id': fid,
                              'used': reason is None, 'skipped': reason,
                              'excluded': reason if reason in ('applies', 'lang', 'off') else None})
    _replace(out_files, warnings)
    if lookup_in and not every:
        _trigger(out_files, lookup_in, known_sections(got), section)
    picked: list = []
    if kinds is not None:
        index = kind_index({'files': out_files})
        every = kind_index({'files': out_files}, usable=False)
        for k in kinds:
            hit = paramod.resolve(k, index)
            if hit is None:
                elsewhere = paramod.resolve(k, every)
                if elsewhere:
                    warnings.append(t('{kind} is not used for this manuscript ({why})', kind=elsewhere,
                                      why=every[elsewhere]['why']))
                    continue
                near = paramod.suggest(k, index)
                warnings.append(t('no paragraph kind called {kind}', kind=k)
                                + (' ' + t('(did you mean {names}?)', names=', '.join(near)) if near else ''))
            elif hit not in picked:
                picked.append(hit)
        for f in out_files:
            if f['kind'] != 'phrases':
                continue
            for it in f['items']:
                it['picked'] = it['id'] in picked
            f['used'] = any(it['picked'] for it in f['items'])
            f['skipped'] = None if f['used'] else 'kind'
    unknown = [x for x in off if not any(x in (f['id'], f['id'].split('/', 1)[1])
                                         or any(x in item_names(f, i) for i in f['items'])
                                         for f in out_files)]
    warnings += [t('writing_off names nothing: {id}', id=x) for x in unknown]
    return {'doc': doc.name, 'packs': order,
            'versions': {n: {'pin': got[n]['pin'], 'commit': got[n].get('commit')}
                         for n in order if got.get(n, {}).get('pin')},
            'chosen': view.get('writing') is not None,
            'paragraph_kinds': picked if kinds is not None else None, 'paragraph': None,
            'chosen_here': 'writing' in own, 'kinds': sorted(doc_kinds_), 'lang': lang,
            'section': section, 'section_only': bool(section_only), 'sections': known, 'off': off,
            'off_here': _as_list(own.get('writing_off')), 'files': out_files,
            'warnings': warnings}


def item_names(f: dict, it: dict) -> list:
    """項目を指す書き方すべて（`パック/ファイル#slug`、`ファイル#slug`、別名でも）。"""
    stem = f['id'].split('/', 1)[1]
    return [f"{f['id']}#{n}" for n in [it['slug']] + it.get('aliases', [])] \
        + [f"{stem}#{n}" for n in [it['slug']] + it.get('aliases', [])]


def _replace(out_files: list, warnings: list) -> None:
    """`Replaces: パック/ファイル#id` の項目があれば、その先の項目を使わない（子のパックが親の項目を
    置き換える）。置き換える側のファイルがこの原稿で使えるとき（applies・lang が合う）だけ。"""
    where: dict = {}
    for f in out_files:
        for it in f['items']:
            for n in item_names(f, it):
                where.setdefault(n, it)
    for f in out_files:
        if f.get('excluded'):
            continue
        for it in f['items']:
            if it['off']:
                continue
            for target in it.get('replaces', []):
                hit = where.get(target)
                if hit is None:
                    warnings.append(t('{id}: Replaces {target}, but there is no such entry',
                                      id=it['id'], target=target))
                elif hit is not it:
                    hit['replaced_by'] = it['id']
                    if not hit.get('skipped'):
                        hit['skipped'] = 'replaced'
    for f in out_files:
        if f['used'] and f['items'] and all(it.get('skipped') or it['off'] for it in f['items']) \
                and any(it.get('skipped') == 'replaced' for it in f['items']):
            f['used'], f['skipped'] = False, 'replaced'


def _trigger(out_files: list, texts: list, known: list, section) -> None:
    """`Stage: lookup` の項目を、Flag の語が本文（節を決めたものはその節の行）にあれば使う。"""
    specs = []
    for f in out_files:
        if f['kind'] != 'rules' or f.get('excluded'):
            continue
        for it in f['items']:
            if it.get('skipped') != 'lookup' or it['off'] or not it['flags']:
                continue
            pats = []
            for src in it['flags']:
                try:
                    pats.append((src, re.compile(src)))
                except re.error:
                    continue
            secs = it['sections'] if 'all' not in it['sections'] or section is None else [section]
            if pats:
                specs.append({'id': it['id'], 'sections': secs, 'patterns': pats, 'item': it, 'file': f})
    if not specs:
        return
    hit = set()
    for text, is_appendix in texts:
        hit |= set(find_flags(text, specs, known, is_appendix))
    for sp in specs:
        if sp['id'] in hit:
            sp['item']['skipped'] = None
            sp['item']['triggered'] = True
            sp['file']['used'], sp['file']['skipped'] = True, None


def kind_index(sel: dict, usable: bool = True) -> dict:
    """段落の種類（フレーズの項目）の id -> 項目。選んだパックのフレーズのファイルから。

    usable なら、その原稿で使うもの（applies・lang が合い、writing_off で外していない）だけ。
    節は問わない。usable=False ならすべてで、各項目の why に使わないわけ（なければ None）。
    """
    out = {}
    for f in sel['files']:
        if f['kind'] != 'phrases':
            continue
        for it in f['items']:
            why = f.get('excluded') or ('off' if it['off'] else None) \
                or ('replaced' if it.get('replaced_by') else None)
            if usable and why:
                continue
            out[it['id']] = {**it, 'file': f['id'], 'file_title': f['title'],
                             'sections': it.get('sections') or f['section'], 'why': why}
    return out


def pack_labels(sel: dict) -> list:
    """使うパックの名前。版から読んだものは `名前@版`。"""
    v = sel.get('versions') or {}
    return [f"{n}@{v[n]['pin']}" if n in v else n for n in sel['packs']]


def render(sel: dict, heading: str | None = None, ids: bool = False) -> str:
    """選んだ分を1つの Markdown に（AI が読むもの）。使わない項目は除く。"""
    lines = [f"<!-- octavo writing: {sel['doc']}"
             + (f", section: {sel['section']}" if sel['section'] else '')
             + (f' (heading "{heading}")' if heading else '') + ' -->',
             '<!-- ' + t('packs, general first: {order}. Where two disagree, the later one wins.',
                         order=' → '.join(pack_labels(sel)) or t('(none)')) + ' -->', '']
    if sel.get('no_section'):
        lines[2:2] = ['<!-- ' + sel['no_section'] + ' -->']
    if sel.get('section_only'):
        lines[2:2] = ['<!-- ' + t('only the files for this section; the rules and phrases read for every '
                                  'section are left out (run without --section-only for those)') + ' -->']
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
                        lines += [for_reader(block), '']
                elif not it['off'] and not it.get('skipped'):
                    lines += [entry_text(block, it['id'] if ids else None), '']
    return '\n'.join(lines).rstrip() + '\n'


def entry_text(block: str, rid: str | None = None) -> str:
    """項目を AI に渡す形に。rid を渡すと、見出しの下にその id を書く（推敲の指摘に名指しさせるため）。"""
    text = for_reader(block)
    if rid:
        head, _, rest = text.partition('\n')
        text = head + f'\n<!-- rule: {rid} -->' + ('\n' + rest if rest else '')
    return text


def sentence_sections(sel: dict) -> set:
    """フレーズが段落の種類ではなく文の順になっている節（要旨など）。

    その節を名指しするフレーズのファイル（この原稿で使うもの）が、どれも `entries: sentences`
    のとき。そういう節の段落には種類が無いので、構成表は「種類が無い」と言わない。
    """
    by_section: dict = {}
    for f in sel['files']:
        if f['kind'] != 'phrases' or f.get('excluded'):
            continue
        for sec in f['section']:
            if sec != 'all':
                by_section.setdefault(sec, []).append(f['entry_kind'] == 'sentences')
    return {sec for sec, got in by_section.items() if all(got)}


# ---------------------------------------------------------------- ルールの Flag（読み直す所）
FLAG = re.compile(r'^\s*(?:Flag|検出)\s*[:：]\s*(.+?)\s*$')
# 当てない所: コメント、コード、値、引用、属性とラベル、リンクの先
_NOT_TEXT = re.compile(r'<!--.*?-->|`+[^`\n]+`+|\{\{.*?\}\}|\[[^\]\n]*@[^\]\n]*\]|(?<![\w.])-?@[\w:.#$%&+?<>~/-]+'
                       r'|\{[^}\n]*\}|(?<=\])\([^)\n]*\)')
FLAG_TEXT = 110                 # 一覧に出す行の長さ（当たった所のまわり）


def flags(sel: dict) -> tuple:
    """この原稿で使うルールの `Flag:` と `Count:`。([{'id','title','file','sections','scope','stage',
    'patterns','counts'}], 警告)。

    正規表現は Python の re の書き方で、大文字小文字を区別する（しないなら頭に `(?i)`）。
    `…` で囲んであれば外す。壊れたものは使わずに、ファイルの名前つきで知らせる。
    """
    out, warnings = [], []
    for f in sel['files']:
        if f['kind'] != 'rules' or f.get('excluded'):
            continue
        for it in f['items']:
            if it['off'] or it.get('replaced_by'):
                continue
            pats, counts = [], []
            for src in it['flags']:
                try:
                    pats.append((src, re.compile(src)))
                except re.error as e:
                    warnings.append(t('{file}: the Flag under "{title}" is not a regular expression '
                                      '({pattern}: {why})', file=f['path'], title=it['title'],
                                      pattern=src, why=str(e)))
            for c in it['counts']:
                try:
                    counts.append({**c, 're': re.compile(c['pattern'])})
                except re.error as e:
                    warnings.append(t('{file}: the Count under "{title}" is not a regular expression '
                                      '({pattern}: {why})', file=f['path'], title=it['title'],
                                      pattern=c['pattern'], why=str(e)))
            if pats or counts:
                out.append({'id': it['id'], 'title': it['title'], 'file': f['id'],
                            'sections': it.get('sections') or f['section'], 'scope': it['scope'],
                            'stage': it['stage'], 'patterns': pats, 'counts': counts})
    return out, warnings


def _excerpt(line: str, start: int, end: int) -> str:
    line = line.rstrip()
    if len(line) <= FLAG_TEXT:
        return line.strip()
    a = max(0, min(start - FLAG_TEXT // 3, len(line) - FLAG_TEXT))
    b = min(len(line), a + FLAG_TEXT)
    return ('…' if a else '') + line[a:b].strip() + ('…' if b < len(line) else '')


def find_flags(text: str, found: list, known: list, appendix: bool = False) -> dict:
    """本文の行に Flag を当てる。{ルールの id: [{'line','match','text'}]}（1行につき1つ）。

    見出し・コード・コメント・数式の塊は読まない。行の中のコード・値・引用・ラベル・リンクの先は
    伏せてから当てる。節を決めたルールは、その節の行だけ。
    """
    lines = text.split('\n')
    start = 0
    m = mdlib.FRONT_MATTER.match(text)
    if m:
        start = text[:m.end()].count('\n')
    out: dict = {}
    fence = None
    comment = math = False
    section = section_at(text, start, known, appendix)[0]
    for i in range(start, len(lines)):
        raw = lines[i]
        s = raw.strip()
        if fence:
            if s.startswith(fence):
                fence = None
            continue
        f = re.match(r'\s*(```+|~~~+)', raw)
        if f:
            fence = f.group(1)
            continue
        if comment:
            if '-->' not in raw:
                continue
            comment = False
            raw = ' ' * (raw.index('-->') + 3) + raw[raw.index('-->') + 3:]
        if s == '$$' or (s.startswith('$$') and not s[2:].rstrip().endswith('$$')):
            math = not math
            continue
        if math:
            if s.endswith('$$'):
                math = False
            continue
        if re.match(r'#{1,6}\s', raw):
            section = section_at(text, i + 1, known, appendix)[0]
            continue
        if not s or s.startswith(':::'):
            continue
        shown = _NOT_TEXT.sub(lambda mm: ' ' * len(mm.group(0)), raw)
        if '<!--' in shown:                     # 閉じていないコメントの始まり
            shown = shown[:shown.index('<!--')]
            comment = True
        if not shown.strip():
            continue
        for fl in found:
            if 'all' not in fl['sections'] and section not in fl['sections']:
                continue
            for _, pat in fl['patterns']:
                hit = pat.search(shown)
                if hit and hit.group(0):
                    out.setdefault(fl['id'], []).append(
                        {'line': i + 1, 'match': hit.group(0),
                         'text': _excerpt(raw, hit.start(), hit.end())})
                    break
    return out


def flag_report(cfg, doc, only: Path | None = None) -> dict:
    """その原稿（本文と付録。only があればそのファイルだけ）で、ルールの Flag に当たった行。

    {'doc', 'rules': [{'id','title','file','patterns','hits': [{'file','line','match','text'}]}],
     'count', 'warnings'}。rules は、当たったものだけ（パックの順）。
    """
    sel = select(cfg, doc, every=True)
    found, warnings = flags(sel)
    hits: dict = {}
    if found:
        for name, src, is_appendix in cfg.sources():
            if name != doc.name or (only is not None and Path(src).resolve() != Path(only).resolve()):
                continue
            got = find_flags(mdlib.read(src), found, sel['sections'], is_appendix)
            for rid, rows in got.items():
                hits.setdefault(rid, []).extend({'file': cfg.rel(src), **r} for r in rows)
    rules = [{'id': fl['id'], 'title': fl['title'], 'file': fl['file'],
              'patterns': [src for src, _ in fl['patterns']], 'hits': hits[fl['id']]}
             for fl in found if fl['id'] in hits]
    return {'doc': doc.name, 'rules': rules, 'count': sum(len(r['hits']) for r in rules),
            'warnings': warnings}


# ---------------------------------------------------------------- パックの点検
def check_packs(got: dict) -> list:
    """パックの中身の点検。[{'file','line','id','problem'}]（パックの順、ファイルの行の順）。

    - 読めない欄（Stage・Scope の値、Count の形、正規表現でない Flag / Count）、同じ Id の二度使い
    - Flag を項目の例に当てる: 悪い例（Bad:）のどれにも当たらない、良い例（Good:）に当たる。
      良い例に当たるのは、その語を正しく使った例なら当然なので note（level）。ほかは problem
    - `Stage: lookup` なのに Flag が無い（いつまでも読まれない）
    - `Replaces:` の先が、どのパックにも無い
    """
    out = []
    every: dict = {}
    rows = []
    known = known_sections(got)
    for name in default_order(got):
        for (kind, fname), (path, _) in sorted(got[name]['files'].items()):
            d = describe(path)
            fid = f'{name}/{Path(fname).stem}'
            f = {'id': fid}
            for it in d['items']:
                it['id'] = f'{fid}#{it["slug"]}'
                for n in item_names(f, it):
                    every.setdefault(n, it)
                rows.append((kind, path, it))
            for sec in d['section']:
                if sec != 'all' and sec not in known:
                    out.append({'file': str(path), 'line': 1, 'id': fid, 'level': 'problem',
                                'problem': t('unknown section {name} (sections: {names})', name=sec,
                                             names=', '.join(known))})
    for kind, path, it in rows:
        def say(problem, it=it, path=path, level='problem'):
            out.append({'file': str(path), 'line': it['line'], 'id': it['id'], 'problem': problem,
                        'level': level})
        for p in it['problems']:
            say(p)
        for sec in it['sections']:
            if sec != 'all' and sec not in known:
                say(t('unknown section {name} (sections: {names})', name=sec, names=', '.join(known)))
        for target in it['replaces']:
            if target not in every:
                say(t('Replaces {target}, but there is no such entry', target=target))
        if kind != 'rules':
            continue
        pats = []
        for src in it['flags']:
            try:
                pats.append(re.compile(src))
            except re.error as e:
                say(t('the Flag {pattern} is not a regular expression ({why})', pattern=src, why=str(e)))
        for c in it['counts']:
            try:
                re.compile(c['pattern'])
            except re.error as e:
                say(t('the Count {pattern} is not a regular expression ({why})', pattern=c['pattern'],
                      why=str(e)))
        if it['stage'] == 'lookup' and not it['flags']:
            say(t('Stage: lookup needs a Flag: the entry is read only when its Flag matches the text'))
        if not pats:
            continue

        def hits(example):
            shown = _NOT_TEXT.sub(lambda mm: ' ' * len(mm.group(0)), example)
            return any((m := p.search(shown)) and m.group(0) for p in pats)
        for ex in it['bad']:
            if not hits(ex):
                say(t('the Flag misses the Bad example: {text}', text=ex))
        for ex in it['good']:
            if hits(ex) and it['stage'] != 'lookup':
                say(t('the Flag matches the Good example: {text}', text=ex), level='note')
    return out
