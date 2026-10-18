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


def _get(url: str, timeout: int = TIMEOUT) -> str:
    req = urllib.request.Request(url, headers={'User-Agent': f'octavo/{__version__}',
                                               'Accept': '*/*'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', 'replace')


def _try(urls: list) -> tuple:
    last = None
    for u in urls:
        try:
            return _get(u), u
        except (urllib.error.URLError, OSError) as e:
            last = f'{u}: {e}'
    raise ZoteroError(last or t('nothing to connect to'))


def alive() -> str | None:
    """Zotero が応答するホストを返す。"""
    for h in hosts():
        try:
            _get(f'http://{h}:{PORT}/connector/ping', timeout=4)
            return h
        except (urllib.error.URLError, OSError):
            continue
    return None


# ---------------------------------------------------------------- Better BibTeX

def bbt_urls(host: str, kind: str, name: str, fmt: str) -> list:
    q = urllib.parse.quote(name)
    return [
        f'http://{host}:{PORT}/better-bibtex/export/{kind}?/1/{q}.{fmt}',
        f'http://{host}:{PORT}/better-bibtex/{kind}?/1/{q}.{fmt}',
        f'http://{host}:{PORT}/better-bibtex/export/{kind}?/0/{q}.{fmt}',
    ]


def bbt_available(host: str) -> bool:
    try:
        _get(f'http://{host}:{PORT}/better-bibtex/cayw?probe=probe', timeout=5)
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
    cols = {c['key']: {'name': c.get('data', {}).get('name', ''),
                       'parent': c.get('data', {}).get('parentCollection') or '',
                       'items': (c.get('meta') or {}).get('numItems', 0)} for c in raw if c.get('key')}
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


def merge_bib(texts: list) -> str:
    """いくつかの .bib を1つにする。同じキーの文献は最初のものだけ残す。"""
    seen, out = set(), []
    for text in texts:
        for m in re.finditer(r'@\w+\s*\{\s*([^,\s]+)\s*,.*?(?=\n@|\Z)', text, re.S):
            if m.group(1) not in seen:
                seen.add(m.group(1))
                out.append(m.group(0).strip())
    return '\n\n'.join(out) + ('\n' if out else '')


def api_collection_bib(host: str, key: str) -> str:
    out, start = [], 0
    while True:
        url = (f'http://{host}:{PORT}/api/users/0/collections/{key}/items'
               f'?format=bibtex&limit=100&start={start}')
        chunk = _get(url)
        if not chunk.strip():
            break
        out.append(chunk)
        if chunk.count('@') < 100:
            break
        start += 100
    return '\n'.join(out)


def api_library_bib(host: str) -> str:
    out, start = [], 0
    while True:
        url = (f'http://{host}:{PORT}/api/users/0/items'
               f'?format=bibtex&limit=100&start={start}&itemType=-attachment||note')
        chunk = _get(url)
        if not chunk.strip():
            break
        out.append(chunk)
        if chunk.count('@') < 100:
            break
        start += 100
    return '\n'.join(out)


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
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.read().decode('utf-8', 'replace'), int(r.headers.get('Total-Results') or 0)
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
            entry = (item.get(fmt) or '').strip()
            if not entry.startswith('@'):
                continue                       # メモ・添付だけのもの
            stable = _stable_key(item.get('data') or {})
            if stable:
                entry = re.sub(r'^(@\w+\s*\{)\s*[^,\s]+', lambda m: m.group(1) + stable, entry, count=1)
            else:
                unpinned += 1
            entries.append(entry)
        start += len(chunk)
        if not chunk or start >= total:
            return '\n\n'.join(entries) + ('\n' if entries else ''), unpinned


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
        try:
            if names and targets:
                texts, url = [], ''
                for c in targets:
                    text, url = _try(bbt_urls(host, 'collection', c['path'].replace(' / ', '/'), fmt))
                    texts.append(text)
                text = merge_bib(texts)
                url = url if len(targets) == 1 else t('{path} and {n} subcollections',
                                                      path=shown, n=len(targets) - len(names))
            elif names:
                texts = [_try(bbt_urls(host, 'collection', n.replace(' / ', '/'), fmt))[0] for n in names]
                text, url = merge_bib(texts), shown
            else:
                text, url = _try(bbt_urls(host, 'library', 'library', fmt))
            if text.strip().startswith('@'):
                return text, f'Better BibTeX ({url})'
        except ZoteroError:
            pass

    # 内蔵 API に落とす
    try:
        if names:
            if cols is None:
                cols = tree(api_collections(host))
                targets = _targets(names, cols)
            text = merge_bib([api_collection_bib(host, c['key']) for c in targets])
            src = t('Zotero local API / collection {name}', name=shown)
        else:
            text = api_library_bib(host)
            src = t('Zotero local API / the whole library')
    except urllib.error.HTTPError as e:
        raise ZoteroError(t('the Zotero local API is unavailable ({why}).', why=e)
                          + '\n  ' + t('it needs Zotero 7 or newer, with Settings '
                                       '-> Advanced -> "Allow other applications" '
                                       'turned on'))
    if not text.strip().startswith('@'):
        raise ZoteroError(t('no BibTeX came back (check the Zotero version and '
                            'settings)'))
    return text, src


def pull(dest: Path, collection=None, fmt: str = 'biblatex',
         backup: bool = True, source: str = 'auto') -> tuple:
    """.bib を取ってきて dest に書く。前の版は .bak に退避する。"""
    text, src = fetch(collection, fmt, source)
    n = text.count('\n@') + text.strip().startswith('@')
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
