# -*- coding: utf-8 -*-
"""講義ノート（A4 プリント）から、回ごとの配布資料を切り出す（octavo extract）。

全体の PDF を1冊組み、その中の「回の区切り（`::: {.session #id}`）から次の区切りの
直前まで」のページだけを、別の PDF にする。**組み直さずにページで切る**ので、
ページ番号・目次・図表や論点の番号は全体の PDF とまったく同じになる（本文 p.12–19
を切り出せば、その PDF でも 12–19 と印字されている）。

  1. octavo build と同じ手順で <名前>.typ を書く（分析は実行しない）
  2. typst で全体の PDF を組み、区切りの目印（templates/handout/handout.typ の
     octavo-session）から、回ごとの物理ページと印字のページ番号を読む
  3. 対応表を build/typst/<名前>.pages.json に書く
  4. `typst compile --pages` で回ごとの PDF を build/handouts/<名前>-<id>.pdf に書く

ページの切り出しにも Typst を使う（qpdf などを足さない）。回の頭は必ず改ページ
しているので、前後の回が同じページに混ざることはない。
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from . import backends as be
from . import build as buildmod
from .i18n import t, tag


class ExtractError(Exception):
    pass


def _run(cmd: list, cwd: Path) -> str:
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if r.returncode != 0:
        tail = '\n'.join((r.stdout + r.stderr).strip().split('\n')[-15:])
        raise ExtractError(t('typst failed:') + '\n' + tail)
    return r.stdout


def _marks(typ: Path, root: str, label: str) -> list:
    """<label> の目印の値。`typst eval`（0.15 から）か、古い typst なら `typst query`。"""
    expr = f'query(<{label}>).map(it => it.value)'
    try:
        out = _run(['typst', 'eval', expr, '--in', typ.name, '--root', root], typ.parent)
    except ExtractError:
        out = _run(['typst', 'query', '--root', root, typ.name, f'<{label}>',
                    '--field', 'value'], typ.parent)
    return json.loads(out or '[]')


def page_table(typ: Path, root: str, skip=()) -> dict:
    """{'body': 本文の最初の物理ページ, 'last': 最後の物理ページ,
        'sessions': [{'key', 'title', 'first', 'last', 'shown_first', 'shown_last'}]}

    skip は中身のない回の印。その目印は数えない: 後ろに何もない区切りでは改ページが
    起きず、目印が前の回の最後のページに乗るので、数えると前の回の最後のページが
    次の回に取られる。
    """
    sessions = [m for m in _marks(typ, root, 'octavo-session') if m.get('key') not in skip]
    body = _marks(typ, root, 'octavo-body')
    end = _marks(typ, root, 'octavo-end')
    if not end:
        raise ExtractError(t('{file} has no page marks (was it written by octavo build '
                             '--to typst from a lecture handout?)', file=typ.name))
    last = end[-1]['page']
    shown_of: dict = {}
    for m in sessions + body + end:
        shown_of[m['page']] = m.get('shown')
    out = []
    for i, m in enumerate(sessions):
        nxt = sessions[i + 1]['page'] - 1 if i + 1 < len(sessions) else last
        out.append({'key': m['key'], 'title': m.get('title'),
                    'first': m['page'], 'last': max(nxt, m['page']),
                    'shown_first': m.get('shown')})
    # 最後のページの印字番号は、本文の最初のページとの差から出す（アラビア数字のとき）
    b = body[0] if body else {'page': 1, 'shown': '1'}
    for s in out:
        try:
            s['shown_last'] = str(int(b['shown']) + s['last'] - b['page'])
        except (TypeError, ValueError):
            s['shown_last'] = None
    return {'body': b['page'], 'last': last, 'sessions': out}


def parse_pages(spec: str, table: dict) -> list:
    """`--pages 12-19,21`（印字のページ番号）を物理ページの範囲 [(a, b)] にする。"""
    out = []
    for part in spec.split(','):
        m = re.fullmatch(r'\s*(\d+)\s*(?:-\s*(\d+))?\s*', part)
        if not m:
            raise ExtractError(t('--pages takes page numbers like 12-19 or 3,5 (got {got})',
                                 got=spec))
        a = int(m.group(1))
        b = int(m.group(2) or a)
        out.append((table['body'] + a - 1, table['body'] + b - 1))
    return out


def run(cfg, name: str, sessions: list | None = None, pages: str | None = None,
        cover: bool = False, offline: bool = False) -> dict:
    """切り出す。{'pdf': 全体, 'table': 対応表のパス, 'made': [(印, PDF)], 'report': […]}"""
    doc = cfg.document(name)
    if doc.profile != 'handout':
        raise ExtractError(t('{name} is not lecture notes (profile handout); only a '
                             'lecture handout can be cut into sessions', name=name))
    if not shutil.which('typst'):
        raise ExtractError(t('typst is needed to cut the handout (octavo setup installs it)'))
    res = buildmod.build_one(cfg, doc, 'typst', offline=offline)
    report = list(res.report)
    if not res.ok:
        raise ExtractError('\n'.join(report))
    ctx_dir = cfg.out_dir('typst', doc)
    typ = ctx_dir / f'{doc.name}.typ'
    root = be.get('typst').root_arg(_Ctx(cfg, ctx_dir))
    _run(['typst', 'compile', '--root', root, typ.name], ctx_dir)
    empty = buildmod.empty_sessions(doc)
    table = page_table(typ, root, skip=empty)
    table_path = ctx_dir / f'{doc.name}.pages.json'
    table_path.write_text(json.dumps(table, ensure_ascii=False, indent=2) + '\n',
                          encoding='utf-8')
    report.append(f'{tag("pages")} {cfg.rel(table_path)}')

    by_key = {s['key']: s for s in table['sessions']}
    jobs: list = []                       # [(印, [(a, b)])]
    if pages:
        jobs.append(('p' + re.sub(r'[^\d,-]', '', pages).replace(',', '_'),
                     parse_pages(pages, table)))
    elif sessions:
        unknown = [k for k in sessions if k not in by_key]
        if unknown:
            raise ExtractError(t('no session {names} in {file} (sessions: {known})',
                                 names=', '.join(unknown), file=cfg.rel(doc.src),
                                 known=', '.join(by_key) or t('(none)')))
        jobs.append(('+'.join(sessions), [(by_key[k]['first'], by_key[k]['last'])
                                          for k in sessions]))
    else:
        if not table['sessions']:
            raise ExtractError(t('{file} has no session markers (::: {{.session #id}}), so '
                                 'there is nothing to cut. --pages 12-19 cuts by page '
                                 'number', file=cfg.rel(doc.src)))
        jobs = [(s['key'], [(s['first'], s['last'])]) for s in table['sessions']]

    out_dir = Path(cfg['out_dirs']['typst']).parent / 'handouts'
    out_dir.mkdir(parents=True, exist_ok=True)
    for key in sorted(empty):
        # 中身のない回の配布資料は作らない。前に作った（前の回の続きが入った）ものは消す
        old = out_dir / f'{doc.name}-{key}.pdf'
        if old.is_file():
            old.unlink()
        report.append(f'{tag("handout")} ' + t('{key}: nothing in it yet, so no handout',
                                                key=key))
    made = []
    for key, ranges in jobs:
        if cover and table['body'] > 1:
            ranges = [(1, table['body'] - 1)] + ranges
        spec = ','.join(f'{a}-{b}' if a != b else str(a) for a, b in ranges)
        dest = out_dir / f'{doc.name}-{key}.pdf'
        _run(['typst', 'compile', '--root', root, '--pages', spec,
              typ.name, str(dest.resolve())], ctx_dir)
        made.append((key, dest))
        report.append(f'{tag("handout")} ' + t('{key}: pages {pages} -> {file}', key=key,
                                                pages=spec, file=cfg.rel(dest)))
    return {'pdf': ctx_dir / f'{doc.name}.pdf', 'table': table_path, 'made': made,
            'sessions': table['sessions'], 'report': report}


class _Ctx:
    """TypstBackend.root_arg に要るものだけ（cfg と out_dir）。"""
    def __init__(self, cfg, out_dir: Path):
        self.cfg = cfg
        self.out_dir = out_dir
