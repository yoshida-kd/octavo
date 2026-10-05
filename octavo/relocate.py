# -*- coding: utf-8 -*-
"""`octavo migrate --docs` — 前からの置き場所の原稿を docs/<名前>/<名前>.md へ移す。

前からの置き場所（papers/<名前>/paper.md・slides/<名前>.md・lectures/<名前>.md）は
そのままでも読めるので、移すかどうかは利用者が決める。移すときにすること:

1. 原稿を docs/<名前>/<名前>.md へ（git の中なら git mv で、履歴が続く）。論文は
   フォルダごとなので、横の appendix.md・main.typ・main.tex なども一緒に
2. 図のパスを新しい場所から見た相対に（論文は深さが同じなので変わらない）
3. 今の扱いを原稿の冒頭に書く（outputs、講義ノートなら sessions: true）。
   targets: は outputs: に置き換え、論文の1つだけの `# 題` は title: へ
4. 設定に docs/*/ がなければ足す（前からの行は残す。何も当たらなければ何もしない）

文書の名前は変わらないので、build/ の出力名・タグ・`octavo build <名前>` はそのまま。
"""
from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from . import md as mdlib
from .i18n import t

DOCS_ENTRY = "        'docs': {\n            'src': 'docs/*/',\n        },\n"


@dataclass
class Move:
    name: str
    src: Path                       # 原稿
    dest: Path                      # docs/<名前>/<名前>.md
    others: list = field(default_factory=list)   # 一緒に移すもの [(元, 先)]
    front: list = field(default_factory=list)    # 冒頭に書く行
    notes: list = field(default_factory=list)    # 知らせること


def plan(cfg) -> tuple:
    """(移すもの, 移せないものの説明) を返す。何も書き換えない。"""
    moves, skipped = [], []
    docs_dir = cfg.root / 'docs'
    for doc in cfg.documents.values():
        src = Path(doc.src)
        if doc.derived or not src.is_file():
            continue
        try:
            src.relative_to(cfg.root)
        except ValueError:
            continue
        dest = docs_dir / doc.name / f'{doc.name}.md'
        if dest.parent.exists():
            skipped.append(t('{name}: docs/{name}/ is already there, so it was left alone',
                             name=doc.name))
            continue
        mv = Move(doc.name, src, dest)
        # 論文はフォルダごと（papers/<名前>/）。横のものは全部その文書のもの
        own_folder = doc.profile == 'paper' and src.parent != cfg.root \
            and src.parent.name == doc.name
        if own_folder:
            for f in sorted(src.parent.iterdir()):
                if f != src and not f.name.startswith('.'):
                    mv.others.append((f, dest.parent / f.name))
        elif doc.appendix and Path(doc.appendix).is_file():
            mv.others.append((Path(doc.appendix), dest.parent / 'appendix.md'))
        mv.front.append('outputs: [' + ', '.join(doc.outputs) + ']')
        if doc.sessions:
            mv.front.append('sessions: true')
        text = src.read_text(encoding='utf-8')
        if doc.profile == 'paper':
            _, body = mdlib.split_front_matter(text)
            masked = _masked(body)
            first = re.search(r'^#{1,3}[ \t]+\S', masked, re.M)
            if first and masked[:first.start()].strip() \
                    and mdlib.strip_comments(masked[:first.start()]).strip():
                mv.notes.append(t('{name}: the text before the first heading used to be left out '
                                  'of a paper; it will now be typeset (delete it if it was a note)',
                                  name=doc.name))
        moves.append(mv)
    return moves, skipped


def _masked(text: str) -> str:
    from . import values as valmod
    return valmod.mask_code(text)[0]


def title_heading(text: str) -> tuple:
    """論文の `# 題` が1つだけで `##` が続くなら (題, 行の位置) を返す。なければ (None, None)。"""
    _, body = mdlib.split_front_matter(text)
    masked = _masked(body)
    h1 = list(re.finditer(r'^#[ \t]+(\S.*)$', masked, re.M))
    sub = re.search(r'^#{2,3}[ \t]+\S', masked, re.M)
    if len(h1) == 1 and sub and h1[0].start() < sub.start():
        return h1[0].group(1).strip(), h1[0]
    return None, None


def rewrite(text: str, mv: Move, old_dir: Path, new_dir: Path, is_paper: bool) -> str:
    """移した原稿の中身: 図のパス、冒頭の outputs / sessions、targets: と `# 題`。"""
    from .scaffold import with_front
    text = mdlib.rebase_links(text, old_dir, new_dir)
    meta, _ = mdlib.split_front_matter(text)
    m = mdlib.FRONT_MATTER.match(text)
    if m:
        # targets: は outputs: に置き換える
        head = '\n'.join(ln for ln in m.group(1).split('\n')
                         if not re.match(r'targets\s*:', ln))
        text = text[:m.start(1)] + head + text[m.end(1):]
    front = list(mv.front)
    if is_paper:
        title, h = title_heading(text)
        if title:
            # 題は冒頭の title: に。もうあれば見出しを消すだけ
            if 'title' not in meta:
                front.insert(0, 'title: ' + mdlib._yq(title))
            m = mdlib.FRONT_MATTER.match(text)
            off = m.end() if m else 0
            body = text[off:]
            line = re.search(r'^#[ \t]+' + re.escape(title) + r'[ \t]*\n?', body, re.M)
            if line:
                body = body[:line.start()] + body[line.end():]
            text = text[:off] + body
    return with_front(text, front)


def _git(root: Path, *args) -> subprocess.CompletedProcess:
    return subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True,
                          encoding='utf-8', errors='replace')


def _tracked(root: Path, p: Path) -> bool:
    return _git(root, 'ls-files', '--error-unmatch', str(p)).returncode == 0


def _move(root: Path, a: Path, b: Path, in_git: bool) -> None:
    b.parent.mkdir(parents=True, exist_ok=True)
    if in_git and _tracked(root, a):
        r = _git(root, 'mv', str(a), str(b))
        if r.returncode == 0:
            return
    shutil.move(str(a), str(b))


def add_docs_entry(config: Path) -> bool:
    """設定の documents に docs/*/ を足す。足したら True。書けない形なら False。"""
    text = config.read_text(encoding='utf-8')
    if re.search(r"'src'\s*:\s*'docs/\*/?'", text):
        return True
    m = re.search(r"^    (['\"])documents\1\s*:\s*\{\s*\n", text, re.M)
    if not m:
        return False
    config.write_text(text[:m.end()] + DOCS_ENTRY + text[m.end():], encoding='utf-8')
    return True


def run(cfg, dry_run: bool = False) -> int:
    moves, skipped = plan(cfg)
    root = cfg.root
    for line in skipped:
        print('  ' + line)
    if not moves:
        print(t('nothing to move: every manuscript is already in docs/'))
        return 0
    in_git = _git(root, 'rev-parse', '--is-inside-work-tree').returncode == 0
    if in_git and not dry_run:
        # 移す原稿や設定に作業中の変更があれば止める（git mv と書き換えが混ざらないように）
        paths = [str(m.src) for m in moves] + [str(a) for m in moves for a, _ in m.others]
        paths.append(str(cfg.source))
        dirty = _git(root, 'status', '--porcelain', '--', *paths).stdout.strip()
        if dirty:
            print(t('there are uncommitted changes in the manuscripts or the config — commit '
                    'them first, then run this again') + '\n' + dirty)
            return 1
    head = '(' + t('dry run') + ') ' if dry_run else ''
    for mv in moves:
        print(f'{head}{cfg.rel(mv.src)} -> {cfg.rel(mv.dest)}')
        for a, b in mv.others:
            print(f'{head}  {cfg.rel(a)} -> {cfg.rel(b)}')
        print(f'{head}  ' + t('front matter: {lines}', lines=', '.join(mv.front)))
        for n in mv.notes:
            print('  ' + t('note') + '  ' + n)
        if dry_run:
            continue
        doc = cfg.documents[mv.name]
        old_dir = mv.src.parent
        _move(root, mv.src, mv.dest, in_git)
        for a, b in mv.others:
            _move(root, a, b, in_git)
            if b.suffix == '.md':
                b.write_text(mdlib.rebase_links(b.read_text(encoding='utf-8'), old_dir, b.parent),
                             encoding='utf-8')
        mv.dest.write_text(rewrite(mv.dest.read_text(encoding='utf-8'), mv, old_dir,
                                   mv.dest.parent, doc.profile == 'paper'), encoding='utf-8')
        # 空になった論文のフォルダは消す
        try:
            if old_dir != root and not any(old_dir.iterdir()):
                old_dir.rmdir()
        except OSError:
            pass
    if dry_run:
        print(t('nothing was changed (drop --dry-run to move them)'))
        return 0
    if cfg.source and not add_docs_entry(Path(cfg.source)):
        print(t("add this to documents in octavo.config.py so docs/ is read:") + '\n' + DOCS_ENTRY)
    print(t('moved {n} {n|manuscript|manuscripts} into docs/. The document names are the same, '
            'so builds, tags and the preview carry on as before', n=len(moves)))
    return 0
