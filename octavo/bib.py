# -*- coding: utf-8 -*-
"""BibTeX/BibLaTeX（Zotero の書き出し）を読む・検査する。

**このツールは .bib を書き換えない。**正本は書誌管理ソフト側。直したい項目は
Zotero で直して書き出し直すのが原則。例外は `octavo bib clean`（別名で軽量版を
書き出すだけで、元のファイルには触らない）。
"""
from __future__ import annotations

import re
from pathlib import Path

from .i18n import catalog, t

CORP_WORDS = {'organization', 'organisation', 'office', 'bureau', 'development',
              'association', 'commission', 'ministry', 'agency', 'department',
              'institute', 'university', 'bank', 'nations', 'council',
              '省', '庁', '機構', '協会', '学会', '委員会', '研究所', '大学'}

# Zotero が付けるが組版には不要で、.bib を無駄に重くするフィールド
NOISY_FIELDS = ('file', 'abstract', 'keywords', 'annotation', 'copyright',
                'shorttitle', 'langid_orig')

CJK = re.compile(r'[　-ヿ㐀-䶿一-鿿]')


# ---------------------------------------------------------------- パーサ

def parse(path: Path) -> dict:
    """波括弧を数えて読む簡易パーサ。複数行のフィールドも拾う。

    返り値: {key: {'type':…, '_src':…, '_order':…, フィールド名: 値, …}}
    """
    if not path.exists():
        return {}
    t = path.read_text(encoding='utf-8', errors='replace')
    out: dict = {}
    i = 0
    order = 0
    entry_re = re.compile(r'@(\w+)\s*\{\s*([^,\s}]+)\s*,')
    while True:
        m = entry_re.search(t, i)
        if not m:
            break
        if m.group(1).lower() in ('comment', 'preamble', 'string'):
            i = m.end()
            continue
        j, depth, k = m.end(), 1, m.end()
        while k < len(t) and depth:
            depth += (t[k] == '{') - (t[k] == '}')
            k += 1
        body, i = t[j:k - 1], k
        out[m.group(2)] = {'type': m.group(1).lower(), '_src': path.name,
                           '_order': order, **_fields(body)}
        order += 1
    return out


def _fields(body: str) -> dict:
    f, p = {}, 0
    field_re = re.compile(r'(\w+)\s*=\s*')
    while True:
        fm = field_re.search(body, p)
        if not fm:
            break
        q = fm.end()
        if q < len(body) and body[q] in '{"':
            open_c, close_c = ('{', '}') if body[q] == '{' else ('"', '"')
            d, r = 1, q + 1
            while r < len(body) and d:
                if open_c == '{':
                    d += (body[r] == '{') - (body[r] == '}')
                elif body[r] == close_c and body[r - 1] != '\\':
                    d -= 1
                r += 1
            val = body[q + 1:r - 1]
        else:
            r = body.find(',', q)
            r = len(body) if r < 0 else r
            val = body[q:r]
        f[fm.group(1).lower()] = ' '.join(val.split())
        p = r
    return f


# ---------------------------------------------------------------- 著者名

def _surname(name: str) -> str:
    """1人分の author 文字列から姓（narrative citation で出る形）を取る。"""
    name = name.strip()
    if name.startswith('{') and name.endswith('}'):      # 団体名 {Example Organization}
        return name[1:-1].strip()
    name = name.replace('{', '').replace('}', '')
    if ',' in name:                                      # "Smith, Alice"
        return name.split(',')[0].strip()
    if CJK.search(name):                                 # 「田中 太郎」は姓が先
        return name.split()[0].strip() if name.split() else name
    parts = name.split()
    return parts[-1] if parts else name                  # "Alice Smith"


def surnames(entry: dict) -> list:
    au = entry.get('author') or entry.get('editor') or ''
    if not au:
        return []
    return [_surname(a) for a in re.split(r'\s+and\s+', au) if a.strip()]


def year(entry: dict) -> str:
    v = entry.get('date') or entry.get('year') or entry.get('pubstate') or ''
    m = re.search(r'\d{4}', v)
    return m.group(0) if m else (v[:12] or 'n.d.')


def narrative_authors(entry: dict, lang: str = 'en') -> str:
    """本文中に地の文で出す著者表記。CSL の細部までは真似ない（近似）。"""
    names = surnames(entry)
    if not names:
        return '?'
    ja = lang == 'ja' or any(CJK.search(n) for n in names)
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f'{names[0]}・{names[1]}' if ja else f'{names[0]} and {names[1]}'
    return f'{names[0]}ほか' if ja else f'{names[0]} et al.'


def possessive(entry: dict, lang: str = 'en') -> str:
    """\\poscite{} の著者部分。年（と括弧）は citeproc に出させる。

    英語: "Smith and Taylor's" → 後ろに citeproc の "(2003)" が付く
    日本語: 「田中」→ 後ろに「（2003）」。「の」は原稿側で書く
    """
    a = narrative_authors(entry, lang)
    if lang == 'ja' or CJK.search(a):
        return a
    return a + ("'" if a.endswith('s') and not a.endswith('et al.') else "'s")


# ---------------------------------------------------------------- 検査

def problems(entries: dict, keys, accepted: dict | None = None) -> tuple:
    """引いているキーについて、書誌の傷を洗う。(未承知, 承知のうえ) を返す。"""
    accepted = accepted or {}
    bad = []
    for k in sorted(keys):
        e = entries.get(k)
        if e is None:
            continue
        if not (e.get('date') or e.get('year') or e.get('pubstate')):
            bad.append((k, 'no year (shows as [n.d.])', ''))
        au = e.get('author', '') or e.get('editor', '')
        if not au:
            bad.append((k, 'no author', ''))
        else:
            first = re.split(r'\s+and\s+', au)[0]
            if ',' in first and first.split(',')[0].strip().lower() in CORP_WORDS:
                bad.append((k, 'organization name split into surname and given name', first))
        if e['type'] in ('article', 'article-journal') and not e.get('pages') \
                and not e.get('pubstate') and not e.get('doi'):
            bad.append((k, 'no page range or DOI', (e.get('journaltitle') or
                                                   e.get('journal') or '')[:40]))
        if e['type'] in ('article',) and not (e.get('journaltitle') or e.get('journal')):
            bad.append((k, 'no journal title', ''))
        if e['type'] in ('book', 'incollection', 'inbook') and not e.get('publisher'):
            bad.append((k, 'no publisher', ''))
        if not re.fullmatch(r'[\w:.#$%&+?<>~/-]+', k):
            bad.append((k, 'key contains characters that break typesetting', ''))
        if CJK.search(' '.join(str(x) for x in e.values())) and not e.get('langid'):
            bad.append((k, 'contains Japanese but has no langid', t('set Language to ja in Zotero')))
    ok = [(k, w, d) for k, w, d in bad if accepted_reason(accepted, k, w) is not None]
    return [x for x in bad if accepted_reason(accepted, x[0], x[1]) is None], ok


def accepted_reason(accepted: dict, key: str, issue: str):
    """bib_accepted に書いた理由。無ければ None。

    指摘の文言は英語が元で、日本語の表示のまま書き写されることもあるので、
    どちらで書いてあっても当たるようにする。"""
    for w in (issue, catalog('ja').get(issue)):
        if w and (key, w) in (accepted or {}):
            return accepted[(key, w)]
    return None


def duplicates(entries: dict) -> list:
    """著者姓＋年＋タイトル頭で見た重複（Zotero の二重取り込みでよく出る）。"""
    seen: dict = {}
    dups = []
    for k, e in entries.items():
        sig = (tuple(surnames(e)[:1]), year(e),
               re.sub(r'\W', '', (e.get('title') or ''))[:24].lower())
        if not sig[2]:
            continue
        if sig in seen:
            dups.append((seen[sig], k))
        else:
            seen[sig] = k
    return dups


def clean(path: Path, out: Path, drop=NOISY_FIELDS) -> tuple:
    """.bib から組版に要らないフィールドを落とした写しを書く（元は触らない）。"""
    t = path.read_text(encoding='utf-8', errors='replace')
    n = 0
    for fld in drop:
        pat = re.compile(r'^\s*%s\s*=\s*\{' % fld, re.M | re.I)
        while True:
            m = pat.search(t)
            if not m:
                break
            d, r = 1, m.end()
            while r < len(t) and d:
                d += (t[r] == '{') - (t[r] == '}')
                r += 1
            while r < len(t) and t[r] in ', \t':
                r += 1
            if r < len(t) and t[r] == '\n':
                r += 1
            t = t[:m.start()] + t[r:]
            n += 1
    out.write_text(t, encoding='utf-8')
    return n, out
