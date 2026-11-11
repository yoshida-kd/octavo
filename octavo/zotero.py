# -*- coding: utf-8 -*-
"""Zotero から .bib を引いてくる。

Zotero が動いている機械で HTTP を叩くだけ。手で「右クリック → エクスポート」を
する代わりになる。使える口は2つあり、上から順に試す。

  1. Better BibTeX（BBT）の口   http://127.0.0.1:23119/better-bibtex/…
     キーが安定する（citation key が変わらない）ので論文にはこちらが向く。
  2. Zotero 内蔵のローカル API  http://127.0.0.1:23119/api/users/0/…
     Zotero 7 以降。設定 → 詳細 →「他のアプリケーションとの通信を許可」が要る。
  3. Zotero のウェブ API        https://api.zotero.org/users/<ID>/…
     Zotero が手元で動いていないとき（SSH でつないだサーバーなど）。API キーとユーザー ID が要る
     （環境変数 ZOTERO_API_KEY / ZOTERO_USER_ID か、`octavo bib login` が書く ~/.config/octavo/zotero.env）。
     キーは Zotero の citationKey（Better BibTeX が書く）か、Extra の「Citation Key: …」を使う。
     無ければ Zotero が付けるキーになるので、Better BibTeX でキーを固定（Pin）しておくとよい。

**WSL から Windows の Zotero を見る場合の注意。**Zotero は 127.0.0.1 にしか
listen しないので、WSL2 からは（ミラーモードでなければ）届かない。その場合は
WSL2 のネットワークモードを mirrored にするか（`.wslconfig` の
`networkingMode=mirrored`、Windows 11 22H2+）、Zotero 側で「右クリック →
ライブラリをエクスポート」して `.bib` を手で `bib_file` の場所に置くこと。

**コレクションは複数書ける。**`zotero_collection` は1つの名前（パス）か、その並び。並びなら、
すべてを1つの .bib にまとめる（1つのテーマのサーベイを、いくつもの論文で使えるように）。

**コレクションは木。**Zotero のコレクションは入れ子にできるので、指定はパス（`親 / 子`。
区切りの空白は問わない）で受ける。名前だけでも、ほかに同じ名前が無ければ通る。取ってくるのは
そのコレクションと、その下のコレクションすべての文献（論文ごとのコレクションを「理論」「方法」の
ように分けても、まとめて1つの .bib になる）。同じキーの文献は1つにする。

**メインと関連。**`zotero_collection` がメイン（.bib になる）。`zotero_linked` は関連のコレクション
（Priorwork の調査ごとなど）で、.bib には入れない。`octavo bib tidy` はメインを「原稿が引いている
文献とぴったり同じ」に保つための計画を立てる: 引いているのにメインに無い文献（関連のどこにあるか）と、
メインにあるのに引いていない文献。`zotero_write: True` のときだけ `--apply` で Zotero を書き換える。
書き換えはウェブ API で、**文献のコレクションの所属だけ**（メインに足す・メインから外す）。文献その
ものは消さず、中身も書き換えない。外した文献はライブラリと、ほかのコレクションに残る。
キーを固定していない文献は、Zotero が付けるキーと .bib のキーが食い違いうるので、外す候補にしない。
"""
from __future__ import annotations

import json
import platform
import re
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from . import __version__
from .i18n import t

PORT = 23119
TIMEOUT = 30
# Better BibTeX は大きなコレクションの初めての書き出しに時間がかかる（キャッシュを作る）
BBT_TIMEOUT = 120
# 混んでいる・一時的に落ちているときに、やり直す回数と、待つ長さの上限（秒）
RETRIES = 3
MAX_WAIT = 30


class ZoteroError(RuntimeError):
    pass


# ---------------------------------------------------------------- 接続先

def _wsl_host_ip() -> str | None:
    """WSL2 から見た Windows 側の IP。"""
    if 'microsoft' not in platform.uname().release.lower():
        return None
    try:
        txt = Path('/etc/resolv.conf').read_text()
        m = re.search(r'^nameserver\s+([\d.]+)', txt, re.M)
        if m:
            return m.group(1)
    except OSError:
        pass
    if shutil.which('ip'):
        r = subprocess.run(['ip', 'route', 'show', 'default'],
                           capture_output=True, text=True)
        m = re.search(r'via\s+([\d.]+)', r.stdout)
        if m:
            return m.group(1)
    return None


def hosts() -> list:
    out = ['127.0.0.1']
    h = _wsl_host_ip()
    if h:
        out.append(h)
    return out


def _wait_for(e) -> float:
    """やり直す前に待つ秒数（Retry-After か Backoff の見出し。無ければ少し）。"""
    headers = getattr(e, 'headers', None) or {}
    for name in ('Retry-After', 'Backoff'):
        try:
            return min(MAX_WAIT, float(headers.get(name) or ''))
        except (TypeError, ValueError):
            continue
    return 2.0


def _transient(e) -> bool:
    """やり直せば通るかもしれない失敗か（混雑・一時的な停止・時間切れ・つながらない）。"""
    if isinstance(e, urllib.error.HTTPError):
        return e.code in (429, 500, 502, 503, 504)
    return isinstance(e, (urllib.error.URLError, TimeoutError, ConnectionError))


def _open(req, timeout: int, retries: int = RETRIES) -> tuple:
    """(本文, 見出し)。一時的な失敗は、言われた時間（上限あり）だけ待ってやり直す。"""
    import time
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode('utf-8', 'replace'), r.headers
        except (urllib.error.URLError, OSError) as e:
            if attempt == retries or not _transient(e):
                raise
            time.sleep(_wait_for(e))
    raise AssertionError('unreachable')


def _get_full(url: str, timeout: int = TIMEOUT, retries: int = 1) -> tuple:
    req = urllib.request.Request(url, headers={'User-Agent': f'octavo/{__version__}',
                                               'Accept': '*/*'})
    return _open(req, timeout, retries)


def _get(url: str, timeout: int = TIMEOUT, retries: int = 1) -> str:
    return _get_full(url, timeout, retries)[0]


def _try(urls: list, timeout: int = TIMEOUT) -> tuple:
    """順に試して、最初に答えたものの (本文, URL)。どれもだめなら、いちばん意味のある失敗で ZoteroError。

    「その書き方の口は無い」（404 など）は次を試す。時間切れ・つながらないは、ほかの書き方を
    試しても同じなので、そこで止める（やり直しは _get がする）。"""
    last = None
    for u in urls:
        try:
            return _get(u, timeout), u
        except urllib.error.HTTPError as e:
            last = f'{u}: {e}'
        except (urllib.error.URLError, OSError) as e:
            raise ZoteroError(f'{u}: {e}')
    raise ZoteroError(last or t('nothing to connect to'))


def alive() -> str | None:
    """Zotero が応答するホストを返す。"""
    for h in hosts():
        try:
            _get(f'http://{h}:{PORT}/connector/ping', timeout=4, retries=0)
            return h
        except (urllib.error.URLError, OSError):
            continue
    return None


# ---------------------------------------------------------------- Better BibTeX

def bbt_urls(host: str, kind: str, name: str, fmt: str, key: str = '') -> list:
    """Better BibTeX の書き出しの口（版によって書き方が違うので、いくつか）。key はコレクションのキー
    （名前に / を含むコレクションも、キーなら1つに決まる）。"""
    out = []
    for q in [urllib.parse.quote(name)] + ([urllib.parse.quote(key)] if key else []):
        out += [f'http://{host}:{PORT}/better-bibtex/export/{kind}?/1/{q}.{fmt}',
                f'http://{host}:{PORT}/better-bibtex/{kind}?/1/{q}.{fmt}',
                f'http://{host}:{PORT}/better-bibtex/export/{kind}?/0/{q}.{fmt}']
    return out


def bbt_available(host: str) -> bool:
    try:
        _get(f'http://{host}:{PORT}/better-bibtex/cayw?probe=probe', timeout=5, retries=0)
        return True
    except (urllib.error.URLError, OSError):
        return False


# ---------------------------------------------------------------- 内蔵ローカル API

def api_collections(host: str) -> list:
    out, start = [], 0
    while True:
        chunk = json.loads(_get(f'http://{host}:{PORT}/api/users/0/collections?limit=100&start={start}'))
        out += chunk
        if len(chunk) < 100:
            return out
        start += 100


def tree(raw: list) -> list:
    """ローカル API のコレクションを、Zotero と同じ木の順（親の直後に子、同じ親の中は名前順）の
    [{key, name, parent, path, depth, items}] にする。items はそのコレクションだけの文献の数。"""
    # ごみ箱に入れたコレクション（Zotero 7。data.deleted）と、その下のコレクションは無いものとする。
    # デスクトップで消しても、ごみ箱を空にするまでは API が返してくる
    trashed = {c['key'] for c in raw if c.get('key') and (c.get('data') or {}).get('deleted')}
    parent_of = {c['key']: (c.get('data') or {}).get('parentCollection') or '' for c in raw if c.get('key')}

    def gone(k, seen=()):
        return k in trashed or (parent_of.get(k) in parent_of and k not in seen
                                and gone(parent_of[k], (*seen, k)))
    cols = {c['key']: {'name': c.get('data', {}).get('name', ''),
                       'parent': c.get('data', {}).get('parentCollection') or '',
                       'items': (c.get('meta') or {}).get('numItems', 0)}
            for c in raw if c.get('key') and not gone(c['key'])}
    children: dict = {}
    for k, c in cols.items():
        children.setdefault(c['parent'] if c['parent'] in cols else '', []).append(k)
    out: list = []

    def walk(parent: str, prefix: str, depth: int, seen: frozenset) -> None:
        for k in sorted(children.get(parent, []), key=lambda k: cols[k]['name'].lower()):
            if k in seen:
                continue
            path = f"{prefix} / {cols[k]['name']}" if prefix else cols[k]['name']
            out.append({'key': k, 'name': cols[k]['name'], 'parent': parent, 'path': path,
                        'depth': depth, 'items': cols[k]['items']})
            walk(k, path, depth + 1, seen | {k})
    walk('', '', 0, frozenset())
    return out


def _norm_path(p: str) -> str:
    return '/'.join(x.strip().lower() for x in p.split('/'))


def resolve(name: str, cols: list) -> dict:
    """パス・名前・キーで1つのコレクションを決める。見つからない・決まらなければ ZoteroError。"""
    q = name.strip()
    hits = ([c for c in cols if c['key'] == q]
            or [c for c in cols if _norm_path(c['path']) == _norm_path(q)]
            or [c for c in cols if c['name'].strip().lower() == q.lower()])
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise ZoteroError(t('no collection called {name}.', name=repr(name)) + '\n  '
                          + t('available: {names}', names=', '.join(c['path'] for c in cols)))
    raise ZoteroError(t('more than one collection is called {name}; give the path (parent / child): '
                        '{paths}', name=repr(name), paths=', '.join(c['path'] for c in hits)))


def subtree(key: str, cols: list) -> list:
    """そのコレクションと、その下のコレクションすべて（木の順）。"""
    keys = {key}
    for c in cols:                 # 木の順なので、親は子より先に出てくる
        if c['parent'] in keys:
            keys.add(c['key'])
    return [c for c in cols if c['key'] in keys]


ENTRY = re.compile(r'@\w+\s*[{(]\s*([^,\s]+)\s*,.*?(?=\n@\w+\s*[{(]|\Z)', re.S)


def merge_bib(texts: list) -> str:
    """いくつかの .bib を1つにする。同じキーの文献は最初のものだけ残す。"""
    seen, out = set(), []
    for text in texts:
        for m in ENTRY.finditer(text):
            if m.group(1) not in seen:
                seen.add(m.group(1))
                out.append(m.group(0).strip())
    return '\n\n'.join(out) + ('\n' if out else '')


def count_entries(text: str) -> int:
    return sum(1 for m in ENTRY.finditer(text) if not m.group(0).lower().startswith(('@comment', '@string', '@preamble')))


def _pinned(item: dict, fmt: str) -> tuple:
    """(1件の書誌, キーを固定してあるか)。固定したキー（Better BibTeX の citationKey か、Extra の
    Citation Key:）があれば、書誌のキーをそれに替える。どの口から取っても同じキーになるように。"""
    entry = (item.get(fmt) or '').strip()
    stable = _stable_key(item.get('data') or {})
    if stable and entry.startswith('@'):
        entry = re.sub(r'^(@\w+\s*\{)\s*[^,\s]+', lambda m: m.group(1) + stable, entry, count=1)
    return entry, bool(stable)


def _local_bib(host: str, path: str, fmt: str) -> str:
    """ローカル API の文献（添付・メモを除いた、いちばん上の文献）を、件数の見出しを見て最後まで。"""
    base = f'http://{host}:{PORT}/api/users/0{path}'
    out, start = [], 0
    while True:
        text, headers = _get_full(f'{base}?format=json&include=data,{fmt}&limit=100&start={start}')
        chunk = json.loads(text)
        if chunk and not any(fmt in it for it in chunk):
            # 書誌を一緒に返さない版: 書誌だけを、同じ並びで取り直す（キーは Zotero の付けたもの）
            text, _ = _get_full(f'{base}?format={fmt}&limit=100&start={start}')
            out.append(text.strip())
        else:
            out += [e for e, _ in (_pinned(it, fmt) for it in chunk) if e.startswith('@')]
        start += len(chunk)
        total = int(headers.get('Total-Results') or 0)
        if not chunk or start >= total:
            return '\n\n'.join(x for x in out if x) + ('\n' if out else '')


def api_collection_bib(host: str, key: str, fmt: str = 'biblatex') -> str:
    return _local_bib(host, f'/collections/{key}/items/top', fmt)


def api_library_bib(host: str, fmt: str = 'biblatex') -> str:
    return _local_bib(host, '/items/top', fmt)


# ---------------------------------------------------------------- ウェブ API

WEB = 'https://api.zotero.org'


def credentials_path() -> Path:
    return Path.home() / '.config' / 'octavo' / 'zotero.env'


def credentials() -> tuple:
    """(API キー, ユーザー ID)。環境変数が先、無ければ ~/.config/octavo/zotero.env。無ければ ('', '')。"""
    import os
    key, uid = os.environ.get('ZOTERO_API_KEY', ''), os.environ.get('ZOTERO_USER_ID', '')
    if not (key and uid):
        try:
            for line in credentials_path().read_text(encoding='utf-8').splitlines():
                name, _, value = line.partition('=')
                if name.strip() == 'ZOTERO_API_KEY' and not key:
                    key = value.strip()
                elif name.strip() == 'ZOTERO_USER_ID' and not uid:
                    uid = value.strip()
        except OSError:
            pass
    return key, uid


def save_credentials(key: str, uid: str) -> Path:
    """ウェブ API のキーを ~/.config/octavo/zotero.env に書く（本人だけが読める）。プロジェクトには書かない。"""
    import os
    path = credentials_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8') as fh:
        fh.write(f'ZOTERO_API_KEY={key.strip()}\nZOTERO_USER_ID={uid.strip()}\n')
    os.chmod(path, 0o600)
    return path


def _web_get(path: str, params: dict) -> tuple:
    key, uid = credentials()
    url = f'{WEB}/users/{uid}{path}?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'User-Agent': f'octavo/{__version__}',
                                               'Zotero-API-Key': key, 'Zotero-API-Version': '3'})
    try:
        text, headers = _open(req, TIMEOUT)
        return text, int(headers.get('Total-Results') or 0)
    except urllib.error.HTTPError as e:
        if e.code in (403, 404):
            raise ZoteroError(t('the Zotero web API refused ({why}). Check the API key and the user ID '
                                '(octavo bib login)', why=e))
        raise ZoteroError(t('the Zotero web API failed ({why})', why=e))
    except (urllib.error.URLError, OSError) as e:
        raise ZoteroError(t('cannot reach the Zotero web API ({why})', why=e))


def web_collections() -> list:
    out, start = [], 0
    while True:
        text, total = _web_get('/collections', {'format': 'json', 'limit': 100, 'start': start})
        chunk = json.loads(text)
        out += chunk
        start += len(chunk)
        if not chunk or start >= total:
            return out


def _stable_key(data: dict) -> str:
    """Better BibTeX が書いた citationKey、または Extra の「Citation Key: …」。無ければ ''。"""
    if data.get('citationKey'):
        return data['citationKey'].strip()
    m = re.search(r'^\s*Citation Key:\s*(\S+)', data.get('extra') or '', re.M | re.I)
    return m.group(1) if m else ''


def web_bib(collection_key: str | None, fmt: str) -> tuple:
    """(.bib のテキスト, キーを固定していない文献の数)。collection_key が None ならライブラリ全体。"""
    path = f'/collections/{collection_key}/items/top' if collection_key else '/items/top'
    entries, unpinned, start = [], 0, 0
    while True:
        text, total = _web_get(path, {'format': 'json', 'include': f'data,{fmt}', 'limit': 100,
                                      'start': start})
        chunk = json.loads(text)
        for item in chunk:
            entry, pinned = _pinned(item, fmt)
            if not entry.startswith('@'):
                continue                       # メモ・添付だけのもの
            unpinned += not pinned
            entries.append(entry)
        start += len(chunk)
        if not chunk or start >= total:
            return '\n\n'.join(entries) + ('\n' if entries else ''), unpinned


def _web_patch(item_key: str, version: int, data: dict) -> None:
    """1つの文献を書き換える（ウェブ API）。version が Zotero 側と違えば（その間に変わった）止める。"""
    key, uid = credentials()
    url = f'{WEB}/users/{uid}/items/{item_key}'
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), method='PATCH',
                                 headers={'User-Agent': f'octavo/{__version__}', 'Zotero-API-Key': key,
                                          'Zotero-API-Version': '3', 'Content-Type': 'application/json',
                                          'If-Unmodified-Since-Version': str(version)})
    try:
        _open(req, TIMEOUT)
        return
    except urllib.error.HTTPError as e:
        if e.code == 403:
            raise WriteRefused(t('the Zotero API key cannot write. At zotero.org/settings/keys, allow '
                                 '"Allow write access" for the key'))
        if e.code == 412:
            raise ZoteroError(t('changed in Zotero meanwhile; run octavo bib tidy again'))
        raise ZoteroError(t('the Zotero web API failed ({why})', why=e))
    except (urllib.error.URLError, OSError) as e:
        raise ZoteroError(t('cannot reach the Zotero web API ({why})', why=e))


class WriteRefused(ZoteroError):
    """キーに書き込みの権限が無い。1つで分かるので、残りも試さない。"""


def _cache_path() -> Path:
    import os
    base = os.environ.get('XDG_CACHE_HOME') or (Path.home() / '.cache')
    return Path(base) / 'octavo' / f'zotero-{credentials()[1] or "unknown"}.json'


def _entry(it: dict) -> dict | None:
    data = it.get('data') or {}
    if data.get('itemType') in ('note', 'attachment', 'annotation') or data.get('deleted'):
        return None                            # メモ・添付・ごみ箱の文献
    stable = _stable_key(data)
    return {'item': it.get('key') or data.get('key', ''),
            'version': it.get('version') or data.get('version') or 0,
            'collections': list(data.get('collections') or []),
            'cite': stable, 'pinned': bool(stable), 'title': data.get('title') or ''}


def _read_all(path: str, params: dict) -> list:
    out, start = [], 0
    while True:
        text, total = _web_get(path, {**params, 'format': 'json', 'include': 'data', 'limit': 100,
                                      'start': start})
        chunk = json.loads(text)
        out += chunk
        start += len(chunk)
        if not chunk or start >= total:
            return out


def synced_items(collection_keys, whole_library: bool = False) -> list:
    """文献 [{item, version, collections, cite, pinned, title}]。cite は固定したキー、無ければ Zotero の
    書き出しのキー。読むのは collection_keys のコレクション（whole_library ならライブラリ全体）。

    手元に写しを持つ（~/.cache/octavo/。消してもよい）。初めてのコレクションはまるごと読み、そのあとは
    ライブラリの中で前の版より後に変わった文献と、消えた文献だけを読む（Zotero の同期と同じ since）。
    コレクションに足した・外した文献も版が上がるので、それで写しの所属が今のものになる。"""
    path = _cache_path()
    try:
        cache = json.loads(path.read_text(encoding='utf-8'))
        since, items = int(cache['version']), dict(cache['items'])
        read, whole = set(cache.get('read', [])), bool(cache.get('whole'))
    except (OSError, ValueError, KeyError, TypeError):
        since, items, read, whole = 0, {}, set(), False
    newest, changed = since, []

    def take(raw):
        nonlocal newest
        for it in raw:
            newest = max(newest, int(it.get('version') or 0))
            e = _entry(it)
            key = it.get('key') or ''
            if e is None:
                items.pop(key, None)
            else:
                items[key] = e
                changed.append(e)

    if since:                                   # 前の写しからの変わり目
        take(_read_all('/items/top', {'since': since}))
        text, _ = _web_get('/deleted', {'since': since})
        for key in (json.loads(text) or {}).get('items', []):
            items.pop(key, None)
    if whole_library and not whole:
        take(_read_all('/items/top', {}))
        whole = True
    for key in collection_keys:
        if not whole and key not in read:       # 初めてのコレクションは、まるごと
            take(_read_all(f'/collections/{key}/items/top', {}))
        read.add(key)
    # キーを固定していない文献は、Zotero の書き出しのキーを（読んだものだけ）まとめて読む
    loose = list({e['item']: e for e in changed if not e['pinned']}.values())
    for i in range(0, len(loose), 50):         # itemKey は一度に 50 まで
        batch = loose[i:i + 50]
        text, _ = _web_get('/items', {'format': 'json', 'include': 'biblatex', 'limit': 50,
                                      'itemKey': ','.join(x['item'] for x in batch)})
        keys = {}
        for it in json.loads(text):
            m = re.match(r'\s*@\w+\s*\{\s*([^,\s]+)', it.get('biblatex') or '')
            if m:
                keys[it.get('key')] = m.group(1)
        for x in batch:
            x['cite'] = keys.get(x['item'], '')
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps({'version': newest, 'read': sorted(read), 'whole': whole, 'items': items},
                                  ensure_ascii=False), encoding='utf-8')
        tmp.replace(path)
    except OSError:
        pass                                   # 写しを書けなくても、今回の計画は立てられる
    return list(items.values())


def tidy_plan(main, linked, cited, whole_library: bool = False) -> dict:
    """メインのコレクションを「引いている文献とぴったり同じ」にする計画（Zotero は書き換えない）。

    main / linked は設定の zotero_collection / zotero_linked、cited は原稿が引いているキー。
    返すもの: add（引いているのにメインに無く、関連にある文献。where は 'linked'。whole_library なら、
    関連にも無いものをライブラリ全体から探す: where は 'library'）、remove（メインにあって引いていない
    文献。キーを固定したものだけ）、unpinned（メインにあってキーを固定していない文献）、
    not_found（引いているが、メインにも関連にも無いキー）。
    """
    names = as_list(main)
    if not names:
        raise ZoteroError(t('set the main collection first (zotero_collection): octavo bib tidy keeps '
                            'that one collection in step with the manuscripts'))
    if not all(credentials()):
        raise ZoteroError(t('octavo bib tidy reads Zotero through the web API: octavo bib login'))
    cols = tree(web_collections())
    by_key = {c['key']: c for c in cols}
    home = resolve(names[0], cols)
    in_main = _targets(names, cols)
    main_keys = {c['key'] for c in in_main}
    in_linked = [c for c in _targets(as_list(linked), cols) if c['key'] not in main_keys]
    library = synced_items([c['key'] for c in in_main + in_linked], whole_library)

    main_items = {it['item']: it for it in library if main_keys & set(it['collections'])}
    main_cites = {it['cite'] for it in main_items.values()}

    cited = set(cited)
    add, found = [], set()
    for c in in_linked:                        # 関連のコレクションの順に（どこから来たかを示す）
        for it in library:
            k = it['cite']
            if (c['key'] in it['collections'] and k in cited and k not in main_cites and k not in found
                    and it['item'] not in main_items):
                found.add(k)
                add.append({'key': k, 'item': it['item'], 'version': it['version'],
                            'collections': it['collections'], 'title': it['title'], 'from': c['path'],
                            'pinned': it['pinned'], 'where': 'linked'})
    for it in (library if whole_library else ()):   # 関連にも無ければ、ライブラリ全体から（頼まれたときだけ）
        k = it['cite']
        if k in cited and k not in main_cites and k not in found and it['item'] not in main_items:
            found.add(k)
            paths = [by_key[x]['path'] for x in it['collections'] if x in by_key]
            add.append({'key': k, 'item': it['item'], 'version': it['version'],
                        'collections': it['collections'], 'title': it['title'],
                        'from': ', '.join(paths) or t('the library (in no collection)'),
                        'pinned': it['pinned'], 'where': 'library'})
    remove, unpinned = [], []
    for it in main_items.values():
        if it['cite'] in cited:
            continue
        if not it['pinned']:
            unpinned.append({'key': it['cite'], 'title': it['title']})
            continue
        remove.append({'key': it['cite'], 'item': it['item'], 'version': it['version'],
                       'collections': it['collections'], 'title': it['title'],
                       'from': [by_key[k]['path'] for k in it['collections'] if k in main_keys]})
    not_found = sorted(cited - main_cites - found)
    return {'main': home['path'], 'main_key': home['key'], 'main_keys': sorted(main_keys),
            'linked': [c['path'] for c in in_linked],
            'add': sorted(add, key=lambda x: x['key']), 'remove': sorted(remove, key=lambda x: x['key']),
            'unpinned': sorted(unpinned, key=lambda x: x['key']), 'not_found': not_found}


def tidy_apply(plan: dict, keys=None) -> tuple:
    """計画どおりに Zotero を書き換える（keys を渡せば、そのキーの文献だけ）。(済んだキー, [(キー, 理由)])。
    書き換えるのは文献の collections だけ: メインに足す・メインのコレクション（とその下）から外す。"""
    keys = None if keys is None else set(keys)
    main_keys = set(plan['main_keys'])
    done, failed = [], []
    jobs = [(x, x['collections'] + [plan['main_key']]) for x in plan['add']]
    jobs += [(x, [k for k in x['collections'] if k not in main_keys]) for x in plan['remove']]
    for x, collections in jobs:
        if keys is not None and x['key'] not in keys:
            continue
        try:
            _web_patch(x['item'], x['version'], {'collections': collections})
            done.append(x['key'])
        except WriteRefused as e:
            failed.append((x['key'], str(e)))
            break
        except ZoteroError as e:
            failed.append((x['key'], str(e)))
    return done, failed


# ---------------------------------------------------------------- 入口

SOURCES = ('auto', 'local', 'web')


def as_list(collection) -> list:
    """設定の zotero_collection（None・名前・並び）を、名前の並びにする。"""
    if not collection:
        return []
    if isinstance(collection, str):
        return [collection]
    return [c for c in collection if isinstance(c, str) and c.strip()]


def _source(source: str) -> tuple:
    """('local', ホスト) か ('web', '')。auto: 手元の Zotero が応答すればそれ、無ければウェブ API。"""
    if source in ('auto', 'local'):
        host = alive()
        if host:
            return 'local', host
        if source == 'local' or not all(credentials()):
            raise ZoteroError(t(
                'Zotero is not answering ({where}).', where=' / '.join(
                    f'{h}:{PORT}' for h in hosts())) + '\n  - '
                + t('is Zotero running?') + '\n  - '
                + t('is Settings -> Advanced -> "Allow other applications on this '
                    'computer to communicate with Zotero" on?') + '\n  - '
                + t('are you reaching for a Windows Zotero from inside WSL? (then '
                    'either put WSL2 in mirrored networking mode, or export the '
                    'library from Zotero by hand and put it at bib_file)') + '\n  - '
                + t('on a server without Zotero, use the Zotero web API: octavo bib login'))
    if not all(credentials()):
        raise ZoteroError(t('the Zotero web API needs an API key and your user ID: octavo bib login'))
    return 'web', ''


def _targets(names: list, cols: list) -> list:
    """指定したコレクションと、その下のすべて（重複なし、木の順）。"""
    keys = []
    for name in names:
        for c in subtree(resolve(name, cols)['key'], cols):
            if c['key'] not in keys:
                keys.append(c['key'])
    return [c for c in cols if c['key'] in keys]


def fetch(collection=None, fmt: str = 'biblatex', source: str = 'auto') -> tuple:
    """(bib のテキスト, どこから取ったかの説明) を返す。collection は None・名前・名前の並び。"""
    names = as_list(collection)
    kind, host = _source(source)
    shown = ', '.join(names)

    if kind == 'web':
        if not names:
            text, unpinned = web_bib(None, fmt)
        else:
            parts, unpinned = [], 0
            for c in _targets(names, tree(web_collections())):
                part, n = web_bib(c['key'], fmt)
                parts.append(part)
                unpinned += n
            text = merge_bib(parts)
        src = t('Zotero web API / {what}', what=shown or t('the whole library'))
        if unpinned:
            src += ' — ' + t('{n} {n|entry has|entries have} no pinned citation key (pin keys in '
                             'Better BibTeX to keep them stable)', n=unpinned)
        return text, src

    # コレクションは木: 指定（パス・名前・キー）を決め、その下のコレクションも取る。
    # 一覧はローカル API でしか読めないので、読めなければ指定をそのまま BBT のパスとして使う
    cols, targets = None, []
    if names:
        try:
            cols = tree(api_collections(host))
        except (urllib.error.URLError, OSError, ValueError):
            cols = None
        targets = _targets(names, cols) if cols is not None else []

    if bbt_available(host):
        # Better BibTeX が入っているなら、それで取る。答えなかったからといって内蔵の API に
        # 落とすと、文献のキーが（固定していないものは）変わり、原稿の引用が切れる。止めて知らせる
        try:
            if names and targets:
                texts = [_try(bbt_urls(host, 'collection', c['path'].replace(' / ', '/'), fmt, c['key']),
                              BBT_TIMEOUT)[0] for c in targets]
                url = shown if len(targets) == len(names) else t(
                    '{path} and {n} subcollections', path=shown, n=len(targets) - len(names))
            elif names:
                texts = [_try(bbt_urls(host, 'collection', n.replace(' / ', '/'), fmt), BBT_TIMEOUT)[0]
                         for n in names]
                url = shown
            else:
                texts = [_try(bbt_urls(host, 'library', 'library', fmt), BBT_TIMEOUT)[0]]
                url = t('the whole library')
        except ZoteroError as e:
            raise ZoteroError(t('Better BibTeX did not export the references ({why}).', why=e) + '\n  '
                              + t('Octavo does not switch to another way of reading Zotero here, because the '
                                  'citation keys could change. Try again (a large collection can take a '
                                  'while the first time), or use --source web.'))
        bad = [x for x in texts if x.strip() and not x.lstrip().startswith('@')]
        if bad:
            raise ZoteroError(t('Better BibTeX answered with something that is not BibTeX: {start}',
                                start=bad[0].strip()[:120]))
        return merge_bib(texts), f'Better BibTeX ({url})'

    # 内蔵 API に落とす
    try:
        if names:
            if cols is None:
                cols = tree(api_collections(host))
                targets = _targets(names, cols)
            text = merge_bib([api_collection_bib(host, c['key'], fmt) for c in targets])
            src = t('Zotero local API / collection {name}', name=shown)
        else:
            text = api_library_bib(host, fmt)
            src = t('Zotero local API / the whole library')
    except urllib.error.HTTPError as e:
        raise ZoteroError(t('the Zotero local API is unavailable ({why}).', why=e)
                          + '\n  ' + t('it needs Zotero 7 or newer, with Settings '
                                       '-> Advanced -> "Allow other applications" '
                                       'turned on'))
    if text.strip() and not text.strip().startswith('@'):
        raise ZoteroError(t('no BibTeX came back (check the Zotero version and '
                            'settings)'))
    return text, src


def pull(dest: Path, collection=None, fmt: str = 'biblatex',
         backup: bool = True, source: str = 'auto') -> tuple:
    """.bib を取ってきて dest に書く。前の版は .bak に退避する。"""
    text, src = fetch(collection, fmt, source)
    n = count_entries(text)
    if n == 0 and dest.exists() and count_entries(dest.read_text(encoding='utf-8', errors='replace')):
        # 一時的な失敗や設定の誤りで、今ある .bib を空にしないように
        raise ZoteroError(t('Zotero gave no references ({source}), so {path} was left as it is. If the '
                            'collection really is empty now, delete the file and pull again.',
                            source=src, path=dest))
    dest.parent.mkdir(parents=True, exist_ok=True)
    if backup and dest.exists():
        bak = dest.with_suffix(dest.suffix + '.bak')
        bak.write_text(dest.read_text(encoding='utf-8', errors='replace'),
                       encoding='utf-8')
    dest.write_text(text, encoding='utf-8')
    return n, src


def collections(source: str = 'auto') -> list:
    """コレクションの木（`tree()` の形）。手元の Zotero か、ウェブ API から。"""
    kind, host = _source(source)
    if kind == 'web':
        return tree(web_collections())
    try:
        return tree(api_collections(host))
    except urllib.error.HTTPError as e:
        raise ZoteroError(t('cannot list the collections ({why})', why=e))
