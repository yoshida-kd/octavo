# -*- coding: utf-8 -*-
"""雑誌に合わせた書式（CSL スタイル）の解決と取得。

`octavo.config.py` の `csl` に書けるもの:

  * `.csl` ファイルへのパス（プロジェクト相対でも絶対でも）
  * CSL スタイル ID（例 `apa`, `modern-language-association`）
    -> 下の探索順で見つける。無ければ Zotero スタイルリポジトリから取得して
       `octavo/csl/` にキャッシュする
  * 別名（下の ALIASES。`apa`, `mla`, `ieee` 等）

探索順:

  1. プロジェクト直下の `<csl>` / `csl/<id>.csl`
  2. octavo/csl/<id>.csl（共有キャッシュ）
  3. ネットワーク（`octavo csl get <id>` か build 時の自動取得）

pandoc の内蔵既定は chicago-author-date なので、それだけは .csl が無くても
`--csl` を省く形で通る（`resolve()` が None を返す）。
"""
from __future__ import annotations

import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

from .i18n import t

from . import __version__, paths

CACHE_DIR = paths.csl_cache_dir()

# 短い別名 -> CSL スタイル ID。ID そのものを書いてもよい。
ALIASES = {
    'apa': 'apa',
    'apa7': 'apa',
    'chicago': 'chicago-author-date',
    'chicago-ad': 'chicago-author-date',
    'chicago-note': 'chicago-note-bibliography',
    'apsa': 'american-political-science-association',
    'asa': 'american-sociological-association',
    'ama': 'american-medical-association',
    'mla': 'modern-language-association',
    'ieee': 'ieee',
    'acm': 'acm-sig-proceedings',
    'nature': 'nature',
    'science': 'science',
    'vancouver': 'vancouver',
    'harvard': 'harvard-cite-them-right',
    'elsevier': 'elsevier-harvard',
    'springer': 'springer-basic-author-date',
    'sage': 'sage-harvard',
    'wiley': 'american-political-science-association',   # 誌によるので要確認
}

SOURCES = (
    'https://raw.githubusercontent.com/citation-style-language/styles/master/{id}.csl',
    'https://www.zotero.org/styles/{id}',
)

INDEPENDENT_PARENT = re.compile(
    r'<link\s[^>]*href="https?://www\.zotero\.org/styles/([\w.-]+)"[^>]*'
    r'rel="independent-parent"', re.I)


class CSLError(RuntimeError):
    pass


def style_id(name: str) -> str:
    n = str(name).strip()
    n = re.sub(r'\.csl$', '', n)
    return ALIASES.get(n.lower(), n)


def find_local(name: str, project_root: Path | None = None) -> Path | None:
    """ダウンロードせずに探す。"""
    cands = []
    if project_root:
        cands += [project_root / name,
                  project_root / f'{name}.csl',
                  project_root / 'csl' / f'{style_id(name)}.csl']
    p = Path(name)
    if p.is_absolute():
        cands.append(p)
    cands.append(CACHE_DIR / f'{style_id(name)}.csl')
    for c in cands:
        if c.is_file() and c.suffix == '.csl':
            return c.resolve()
    return None


def fetch(name: str, dest_dir: Path | None = None, timeout: int = 20,
          _depth: int = 0) -> Path:
    """スタイルを取得してキャッシュに置く。従属スタイルなら親まで辿る。"""
    sid = style_id(name)
    dest_dir = dest_dir or CACHE_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f'{sid}.csl'

    last = None
    for tmpl in SOURCES:
        url = tmpl.format(id=sid)
        try:
            req = urllib.request.Request(url, headers={'User-Agent': f'octavo/{__version__}'})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                text = r.read().decode('utf-8')
            break
        except (urllib.error.URLError, OSError) as e:      # 次のソースを試す
            last = e
            text = None
    if text is None:
        raise CSLError(t('could not fetch the CSL style {id}: {why}',
                         id=repr(sid), why=last) + '\n  '
                       + t('style IDs are listed at https://www.zotero.org/styles')
                       + '\n  ' + t('to place it by hand: {path}', path=dest))
    if '<style' not in text:
        raise CSLError(f'{sid}: ' + t('what came back is not a CSL (check the ID)'))

    m = INDEPENDENT_PARENT.search(text)
    if m and _depth < 3:
        parent = m.group(1)
        print('  ' + t('{id} is a dependent style -> fetching its parent {parent}',
                        id=sid, parent=parent), file=sys.stderr)
        return fetch(parent, dest_dir, timeout, _depth + 1)

    dest.write_text(text, encoding='utf-8')
    return dest


def resolve(name: str | None, project_root: Path | None = None,
            allow_download: bool = True, quiet: bool = False) -> Path | None:
    """build から呼ぶ入口。None を返したら `--csl` を付けない（pandoc の既定）。"""
    if not name:
        return None
    local = find_local(name, project_root)
    if local:
        return local
    sid = style_id(name)
    if allow_download:
        try:
            p = fetch(sid)
            if not quiet:
                print('  ' + t('fetched the CSL: {path}', path=p), file=sys.stderr)
            return p
        except CSLError as e:
            if sid == 'chicago-author-date':
                if not quiet:
                    print('  ' + t('could not fetch the CSL, but chicago-author-date '
                                    "is pandoc's built-in default — carrying on"),
                          file=sys.stderr)
                return None
            raise
    if sid == 'chicago-author-date':
        return None
    raise CSLError(t('the CSL style {id} is not here.', id=repr(sid)) + '\n  '
                   + t('fetch it with: octavo csl get {id}', id=sid))


def cached() -> list:
    if not CACHE_DIR.exists():
        return []
    return sorted(p for p in CACHE_DIR.glob('*.csl'))


def title_of(path: Path) -> str:
    try:
        text = path.read_text(encoding='utf-8', errors='replace')[:4000]
    except OSError:
        return ''
    m = re.search(r'<title>(.*?)</title>', text, re.S)
    return ' '.join(m.group(1).split()) if m else ''
