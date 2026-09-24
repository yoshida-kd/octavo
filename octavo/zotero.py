# -*- coding: utf-8 -*-
"""Zotero から .bib を引いてくる。

Zotero が動いている機械で HTTP を叩くだけ。手で「右クリック → 書き出し」を
する代わりになる。使える口は2つあり、上から順に試す。

  1. Better BibTeX（BBT）の口   http://127.0.0.1:23119/better-bibtex/…
     キーが安定する（citation key が変わらない）ので論文にはこちらが向く。
  2. Zotero 内蔵のローカル API  http://127.0.0.1:23119/api/users/0/…
     Zotero 7 以降。設定 → 詳細 →「他のアプリケーションとの通信を許可」が要る。

**WSL から Windows の Zotero を見る場合の注意。**Zotero は 127.0.0.1 にしか
listen しないので、WSL2 からは（ミラーモードでなければ）届かない。その場合は
WSL2 のネットワークモードを mirrored にするか（`.wslconfig` の
`networkingMode=mirrored`、Windows 11 22H2+）、Zotero 側で「右クリック →
ライブラリを書き出す」して `.bib` を手で `bib_file` の場所に置くこと。
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
    txt = _get(f'http://{host}:{PORT}/api/users/0/collections?limit=200')
    return json.loads(txt)


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


# ---------------------------------------------------------------- 入口

def fetch(collection: str | None = None, fmt: str = 'biblatex') -> tuple:
    """(bib のテキスト, どこから取ったかの説明) を返す。"""
    host = alive()
    if not host:
        raise ZoteroError(t(
            'Zotero is not answering ({where}).', where=' / '.join(
                f'{h}:{PORT}' for h in hosts())) + '\n  - '
            + t('is Zotero running?') + '\n  - '
            + t('is Settings -> Advanced -> "Allow other applications on this '
                'computer to communicate with Zotero" on?') + '\n  - '
            + t('are you reaching for a Windows Zotero from inside WSL? (then '
                'either put WSL2 in mirrored networking mode, or export the '
                'library from Zotero by hand and put it at bib_file)'))

    if bbt_available(host):
        try:
            if collection:
                text, url = _try(bbt_urls(host, 'collection', collection, fmt))
            else:
                text, url = _try(bbt_urls(host, 'library', 'library', fmt))
            if text.strip().startswith('@'):
                return text, f'Better BibTeX ({url})'
        except ZoteroError:
            pass

    # 内蔵 API に落とす
    try:
        if collection:
            cols = api_collections(host)
            hit = [c for c in cols
                   if c.get('data', {}).get('name', '').strip() == collection.strip()]
            if not hit:
                names = ', '.join(sorted(c.get('data', {}).get('name', '') for c in cols))
                raise ZoteroError(t('no collection called {name}.',
                                    name=repr(collection))
                                  + '\n  ' + t('there is: {names}', names=names))
            text = api_collection_bib(host, hit[0]['key'])
            src = t('Zotero local API / collection {name}', name=collection)
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


def pull(dest: Path, collection: str | None = None, fmt: str = 'biblatex',
         backup: bool = True) -> tuple:
    """.bib を取ってきて dest に書く。前の版は .bak に退避する。"""
    text, src = fetch(collection, fmt)
    n = text.count('\n@') + text.strip().startswith('@')
    dest.parent.mkdir(parents=True, exist_ok=True)
    if backup and dest.exists():
        bak = dest.with_suffix(dest.suffix + '.bak')
        bak.write_text(dest.read_text(encoding='utf-8', errors='replace'),
                       encoding='utf-8')
    dest.write_text(text, encoding='utf-8')
    return n, src


def collections() -> list:
    host = alive()
    if not host:
        raise ZoteroError(t('Zotero is not answering'))
    try:
        return sorted(c.get('data', {}).get('name', '') for c in api_collections(host))
    except urllib.error.HTTPError as e:
        raise ZoteroError(t('cannot list the collections ({why})', why=e))
