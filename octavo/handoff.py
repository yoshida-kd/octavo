# -*- coding: utf-8 -*-
"""Priorwork（先行研究のサーベイ）から受け取ったもの。受け取り場所は literature/priorwork/。

    octavo priorwork [--json]                 受け取ったものの一覧
    octavo priorwork resolve [--dry-run]      @PRIORWORK:<DOI> を .bib のキーに置き換える
    octavo priorwork link [SURVEY] [--dry-run]  添え状の Zotero コレクションを zotero_linked に足す

Priorwork は `export SURVEY --octavo` で、受け取り場所に本文（<survey>.md）と添え状（<survey>.json、
形式 priorwork-handoff 版 1）だけを書く。原稿・設定・.bib には書かない。原稿に取り込むのは
利用者と、その指示を受けたエージェント（AGENTS.md の約束）。

本文の引用は .bib のキーで `[@key]`。.bib にまだ無い論文は `@PRIORWORK:<DOI を小文字>`（DOI が
キーに書けない文字を含むなら `@{PRIORWORK:<DOI>}`、DOI が無ければ `@PRIORWORK:<姓><年>`）。
Zotero に入れて `octavo bib pull` すれば、resolve が DOI でキーに置き換えられる。

**添え状の形は Priorwork との約束**で、見本は tests/handoff.json（priorwork-dev の
tests/fixtures/handoff.json と同じ中身）。形を変えるときは版を上げ、両方の見本を一緒に直す。
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from . import bib as bibmod
from . import md as mdlib
from .i18n import t

INBOX = Path('literature') / 'priorwork'
FORMAT = 'priorwork-handoff'
VERSION = 1
PREFIX = 'PRIORWORK:'
# 原稿の中の印: @PRIORWORK:10.1/x か @{PRIORWORK:10.1/(x)}
MARK = re.compile(r'@\{PRIORWORK:([^}]*)\}|(?<![\w.@-])@PRIORWORK:([\w][\w:.#$%&+?<>~/-]*[\w])')
# Pandoc の引用キーにそのまま書ける文字（Priorwork の placeholder と同じ）
_KEY_SAFE = re.compile(r'^[A-Za-z0-9_][A-Za-z0-9_:.#$%&\-+?<>~/]*[A-Za-z0-9_]$')


def inbox(root: Path) -> Path:
    return Path(root) / INBOX


def placeholder(doi: str) -> str:
    """Priorwork が書く印（`@` の後ろ）。Priorwork の octavo.placeholder と同じ決まり。"""
    key = PREFIX + doi.lower()
    return key if _KEY_SAFE.match(key) and '}' not in key else '{' + key.replace('}', '') + '}'


def is_doi(s: str) -> bool:
    return bool(re.match(r'10\.\d{4,}/|10\.\d+/', s))


def marks(text: str) -> list:
    """本文の中の印の DOI（または姓と年）の並び（コードの中は見ない）。"""
    text = re.sub(r'^```.*?^```', '', text, flags=re.S | re.M)
    return [(m.group(1) or m.group(2) or '').strip() for m in MARK.finditer(text)]


def doi_keys(cfg) -> dict:
    """.bib の DOI（小文字）-> キー。"""
    out: dict = {}
    for key, e in bibmod.parse(Path(cfg['bib_file'])).items():
        doi = (e.get('doi') or '').strip().lower()
        doi = re.sub(r'^https?://(dx\.)?doi\.org/', '', doi)
        if doi and doi not in out:
            out[doi] = key
    return out


def replace(text: str, keys: dict) -> tuple:
    """印のうち、.bib に DOI があるものをキーに置き換える。(新しい本文, 置き換えた数, 残った印)。"""
    done, left = 0, []

    def sub(m):
        nonlocal done
        mark = (m.group(1) or m.group(2) or '').strip()
        key = keys.get(mark.lower()) if is_doi(mark) else None
        if key:
            done += 1
            return '@' + key
        left.append(mark)
        return m.group(0)
    parts = re.split(r'(^```.*?^```)', text, flags=re.S | re.M)
    out = ''.join(p if i % 2 else MARK.sub(sub, p) for i, p in enumerate(parts))
    return out, done, left


def _original(text: str, manifest: dict, keys: dict) -> str:
    """resolve が置き換えたキーを印に戻した本文（手で変えたかを sha256 で確かめるため）。"""
    for c in manifest.get('citations') or []:
        doi = (c.get('doi') or '').strip()
        if c.get('in_bib') or not doi:
            continue
        key = keys.get(doi.lower())
        if key:
            text = re.sub(r'(?<![\w.@-])@' + re.escape(key) + r'(?![\w:.#$%&+?<>~/-]*[\w])',
                          '@' + placeholder(doi), text)
    return text


def read(root: Path, cfg=None) -> list:
    """受け取り場所の添え状を読む。[{survey, topic, kind, …, warnings}]（読めないものは warnings に）。"""
    folder = inbox(root)
    keys = doi_keys(cfg) if cfg is not None else {}
    main = [n.strip().lower() for n in _names(cfg['zotero_collection'])] if cfg is not None else []
    linked = [n.strip().lower() for n in _names(cfg['zotero_linked'])] if cfg is not None else []
    out = []
    for p in sorted(folder.glob('*.json')) if folder.is_dir() else []:
        row: dict = {'json': str(p), 'warnings': []}
        try:
            m = json.loads(p.read_text(encoding='utf-8'))
        except (OSError, ValueError) as e:
            row['warnings'].append(t('unreadable: {why}', why=e))
            out.append(row)
            continue
        if not isinstance(m, dict) or m.get('format') != FORMAT:
            continue                                   # Priorwork の添え状ではない
        version = m.get('version') or 0
        if not isinstance(version, int) or version > VERSION:
            row['warnings'].append(t('a newer format (version {v}): read only what this Octavo knows; update Octavo',
                                     v=version))
        text_path = p.with_name(str(m.get('text') or p.with_suffix('.md').name))
        coll = m.get('zotero_collection') or None
        cname = (coll or {}).get('name') if isinstance(coll, dict) else None
        cites = [c for c in (m.get('citations') or []) if isinstance(c, dict)]
        row.update({
            'survey': m.get('survey') or p.stem, 'topic': m.get('topic') or '',
            'kind': m.get('kind') or '', 'lang': m.get('lang') or '',
            'written_at': m.get('written_at') or '', 'priorwork': m.get('priorwork') or '',
            'version': version, 'report': m.get('report') or '',
            'text': str(text_path), 'exists': text_path.is_file(),
            'collection': cname,
            'collection_in': ('main' if cname and cname.strip().lower() in main
                              else 'linked' if cname and cname.strip().lower() in linked else None),
            'citations': len(cites), 'not_in_bib': sum(1 for c in cites if not c.get('in_bib')),
            'cards': str(p.with_name(m['cards'])) if m.get('cards') else None,
        })
        if text_path.is_file():
            text = mdlib.read(text_path)
            left = marks(text)
            row['marks'] = len(left)
            row['resolvable'] = sum(1 for d in left if is_doi(d) and d.lower() in keys)
            sha = (m.get('sha256') or '').lower()
            row['edited'] = bool(sha) and sha not in (
                hashlib.sha256(text.encode('utf-8')).hexdigest(),
                hashlib.sha256(_original(text, m, keys).encode('utf-8')).hexdigest())
        else:
            row.update(marks=0, resolvable=0, edited=False)
            row['warnings'].append(t('the text {name} is missing', name=text_path.name))
        out.append(row)
    return out


def _names(value) -> list:
    if not value:
        return []
    return [value] if isinstance(value, str) else [v for v in value if isinstance(v, str)]


def files_to_resolve(cfg) -> list:
    """印を探すファイル: 原稿（付録も）と、受け取り場所の本文。"""
    out = [Path(src) for _, src, _ in cfg.sources()]
    folder = inbox(cfg.root)
    if folder.is_dir():
        out += sorted(p for p in folder.glob('*.md'))
    return out


def resolvable(cfg) -> int:
    """いま .bib のキーに置き換えられる印の数（bib pull のあとに知らせる）。"""
    keys = doi_keys(cfg)
    n = 0
    for p in files_to_resolve(cfg):
        try:
            n += sum(1 for d in marks(mdlib.read(p)) if is_doi(d) and d.lower() in keys)
        except OSError:
            continue
    return n


# ---------------------------------------------------------------- カード（採用論文の要点）

CARDS_FORMAT = 'priorwork-cards'
EVIDENCE = ('unchecked', 'abstract', 'fulltext')


def _cards_files(root: Path) -> list:
    folder = inbox(root)
    return sorted(folder.glob('*.cards.json')) if folder.is_dir() else []


def cards(root: Path, cfg=None) -> dict:
    """原稿の引用キー -> そのキーのカード [{survey, label, title, year, evidence, fields, doi}]。

    Priorwork のカード（<survey>.cards.json）を、どれも読む。キーは .bib のキーか印の中身
    （PRIORWORK:10.x/…）。印を resolve で .bib のキーにしたあとも引けるように、.bib の DOI からも
    引く。同じ論文がいくつものサーベイにあれば、すべて。
    """
    by_doi = doi_keys(cfg) if cfg is not None else {}
    out: dict = {}
    for p in _cards_files(root):
        try:
            m = json.loads(p.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if not isinstance(m, dict) or m.get('format') != CARDS_FORMAT:
            continue
        survey = m.get('survey') or p.name.split('.')[0]
        for c in m.get('papers') or []:
            if not isinstance(c, dict) or not c.get('key'):
                continue
            card = {'survey': survey, 'label': c.get('label') or '', 'title': c.get('title') or '',
                    'year': c.get('year'), 'evidence': c.get('evidence') or 'unchecked',
                    'fields': c.get('fields') or {}, 'doi': c.get('doi') or ''}
            keys = {c['key']}
            doi = (c.get('doi') or '').strip().lower()
            if doi and doi in by_doi:
                keys.add(by_doi[doi])            # .bib に入って resolve したあとのキー
            for k in keys:
                out.setdefault(k, []).append(card)
    return out


def unchecked(cfg, cited) -> list:
    """引いた論文のうち、カードが本文で確かめていない（fulltext でない）もの [(キー, 確認レベル, サーベイ)]。
    カードのない論文は数えない。"""
    got = cards(cfg.root, cfg)
    out = []
    for k in sorted(cited):
        cs = got.get(k)
        if cs and not any(c['evidence'] == 'fulltext' for c in cs):
            best = max(cs, key=lambda c: EVIDENCE.index(c['evidence']) if c['evidence'] in EVIDENCE else 0)
            out.append((k, best['evidence'], best['survey']))
    return out


# ---------------------------------------------------------------- 依頼（Octavo -> Priorwork）

REQUEST_FORMAT = 'priorwork-request'
REQUEST_KINDS = ('start', 'use-surveys', 'other')


def is_workspace(path) -> bool:
    """Priorwork のワークスペースか（根に .priorwork/ がある）。"""
    return bool(path) and (Path(path) / '.priorwork').is_dir()


def write_request(workspace: Path, project: Path, kind: str, text: str, manuscript=None) -> Path:
    """Priorwork のワークスペースの .priorwork/requests/<id>.json に依頼を書く（status は open）。"""
    import datetime
    now = datetime.datetime.now().replace(microsecond=0)
    base = f'{now.strftime("%Y%m%dT%H%M%S")}-{re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(project).name)}'
    folder = Path(workspace) / '.priorwork' / 'requests'
    folder.mkdir(parents=True, exist_ok=True)
    rid, n = base, 1
    while (folder / f'{rid}.json').exists():
        n += 1
        rid = f'{base}-{n}'
    data = {'format': REQUEST_FORMAT, 'version': 1, 'id': rid, 'from': 'octavo',
            'project': str(Path(project).resolve()),
            'manuscript': str(Path(manuscript).resolve()) if manuscript else None,
            'kind': kind if kind in REQUEST_KINDS else 'other', 'text': text,
            'created_at': now.isoformat(), 'status': 'open', 'survey': None, 'done_at': None, 'note': ''}
    path = folder / f'{rid}.json'
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return path


def requests(workspace: Path, project: Path) -> list:
    """このプロジェクトから出した依頼と、Priorwork が書き込んだ結果（新しい順）。"""
    folder = Path(workspace) / '.priorwork' / 'requests'
    me = str(Path(project).resolve())
    out = []
    for p in sorted(folder.glob('*.json'), reverse=True) if folder.is_dir() else []:
        try:
            m = json.loads(p.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if not isinstance(m, dict) or m.get('format') != REQUEST_FORMAT or m.get('project') != me:
            continue
        out.append({k: m.get(k) for k in ('id', 'kind', 'manuscript', 'created_at', 'status', 'survey',
                                          'done_at', 'note')} | {'path': str(p)})
    return out


def workspace_of(given=None):
    """Priorwork のワークスペース: 渡されたもの、無ければ環境変数 OCTAVO_PRIORWORK_WORKSPACE。"""
    import os
    return given or os.environ.get('OCTAVO_PRIORWORK_WORKSPACE') or None
