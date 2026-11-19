# -*- coding: utf-8 -*-
"""自分の直しを、ルールの案の材料に: `octavo writing --harvest REF [--for DOC] [--docx F]`。

原稿は一文一行なので、git の版 REF と今の原稿の差分は、そのまま「直す前の文 / 直した後の文」の
対になる（AI の下書きを commit してから著者が直したなら、その commit を REF に）。共著者の docx の
変更とコメント（`octavo review` が読むもの）も足せる。

**出すのは材料だけ。** ルールの案を作るのは AI（`octavo ai run suggest-rules <このファイル>` か
チャットの AI）で、採るかどうかは人が決める。Octavo はパックに何も書かない。
"""
from __future__ import annotations

import difflib
import re
import shutil
import subprocess
from pathlib import Path

from . import md as mdlib
from .i18n import t

SKIP = re.compile(r'^\s*(?:#|<!--|:::|```|~~~|\||!\[|\$\$|$)')


class HarvestError(Exception):
    pass


def _old(root: Path, ref: str, rel: str) -> str | None:
    if not shutil.which('git'):
        raise HarvestError(t('git is not installed'))
    r = subprocess.run(['git', '-C', str(root), 'show', f'{ref}:{rel}'], capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if r.returncode != 0:
        if 'exists on disk, but not in' in r.stderr or 'does not exist in' in r.stderr:
            return None
        raise HarvestError(r.stderr.strip() or t('git show {ref}:{file} failed', ref=ref, file=rel))
    return r.stdout


def _norm(s: str) -> str:
    return ' '.join(s.split())


def pairs(cfg, ref: str, docs=None) -> list:
    """[{'doc','file','line','before','after'}]: REF から書き換わった文（行）の対。"""
    root = Path(cfg.root)
    out = []
    for name, src, _app in cfg.sources():
        if docs and name not in docs:
            continue
        rel = cfg.rel(src)
        old = _old(root, ref, rel)
        if old is None:
            continue
        a, b = old.split('\n'), mdlib.read(src).split('\n')
        sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op != 'replace':
                continue
            olds = [x for x in a[i1:i2] if not SKIP.match(x)]
            news = [(j1 + k + 1, x) for k, x in enumerate(b[j1:j2]) if not SKIP.match(x)]
            if not olds or not news:
                continue
            if len(olds) == len(news):
                rows = [(n, o, x) for o, (n, x) in zip(olds, news)]
            else:
                rows = [(news[0][0], ' '.join(x.strip() for x in olds), ' '.join(x.strip() for _, x in news))]
            for n, before, after in rows:
                if _norm(before) != _norm(after):
                    out.append({'doc': name, 'file': rel, 'line': n, 'before': before.strip(),
                                'after': after.strip()})
    return out


def docx_changes(path: Path) -> list:
    """[{'context', 'changes': [{'kind','author','text'}]}]（共著者の変更とコメント）。"""
    from . import review as reviewmod
    try:
        paras = reviewmod.collect(Path(path))
    except reviewmod.DocxError as e:
        raise HarvestError(str(e)) from e
    return [{'context': p.context, 'changes': [{'kind': c.kind, 'author': c.author, 'text': c.text}
                                               for c in p.changes]} for p in paras]


def render(ref: str, got: list, docx: list | None = None, docx_name: str = '') -> str:
    out = [f'<!-- octavo writing --harvest {ref} -->', '',
           '# ' + t('Sentences the author revised since {ref}', ref=ref), '']
    if not got:
        out += [t('(no sentence changed)'), '']
    for i, p in enumerate(got, 1):
        out += [f"## H{i} — {p['file']}:{p['line']}", '', f"- Before: {p['before']}", f"- After: {p['after']}", '']
    if docx is not None:
        out += ['# ' + t("A coauthor's changes and comments in {file}", file=docx_name), '']
        for i, p in enumerate(docx, 1):
            out += [f'## D{i}', '', f"- Context: {p['context']}"]
            out += [f"- {c['kind']} ({c['author']}): {c['text']}" for c in p['changes']] + ['']
    return '\n'.join(out).rstrip() + '\n'
