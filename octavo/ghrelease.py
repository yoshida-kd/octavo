# -*- coding: utf-8 -*-
"""節目の版を残す: git のタグと、組んだ PDF を付けた GitHub Release（`octavo release`）。

    octavo release example-paper v1-submitted
      -> タグ example-paper-v1-submitted（注釈つき）を今のコミットに打って push し、
         GitHub Release を作って、その場で組み直した PDF（と Word）を添付する

`build/` は git に入れない（生成物で、git にある材料から作り直せる）。それでも
「共著者に渡した版」「投稿した版」の**現物**は、Octavo や Typst の版が変わると
同じには作り直せないので、節目にだけ外（GitHub）へ置く。git の履歴には入れない。

添付するものとタグの指すコミットが食い違わないように、次を確かめてから組む:
作業ツリーがきれい（コミットしていない変更が無い）、分析が古くない、仮の値のまま
ではない、そのタグがまだ無い、`gh` が使える。組むのは**この場で**、分析は走らせない
（走らせると results/ が変わってコミットとずれる）。

タグの名前は `values --diff <タグ>`（R&R で「投稿版から何が動いたか」）にもそのまま使える。
GitHub とのやり取りは `gh`（GitHub CLI）に任せる。Octavo 自身は標準ライブラリだけ。
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from . import __version__
from . import analysis as anamod
from . import build as buildmod
from . import values as valuesmod
from .i18n import t


class ReleaseError(Exception):
    pass


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True,
                          encoding='utf-8', errors='replace')


def tag_name(doc: str, label: str) -> str:
    return f'{doc}-{label}'


def preflight(cfg, doc_name: str, label: str, need_gh: bool = True) -> str:
    """組む前の確認。問題があれば ReleaseError（全部まとめて）。タグ名を返す。"""
    problems: list = []
    root = cfg.root
    if not shutil.which('git'):
        raise ReleaseError(t('git is not installed'))
    if _git(root, 'rev-parse', '--is-inside-work-tree').returncode != 0:
        raise ReleaseError(t('this project is not a git repository (git init, then commit)'))
    try:
        cfg.document(doc_name)
    except SystemExit as e:
        raise ReleaseError(str(e)) from None

    tag = tag_name(doc_name, label)
    if _git(root, 'check-ref-format', f'refs/tags/{tag}').returncode != 0:
        problems.append(t('{tag} cannot be a git tag name', tag=tag))
    elif _git(root, 'rev-parse', '-q', '--verify', f'refs/tags/{tag}').returncode == 0:
        problems.append(t('the tag {tag} already exists', tag=tag))

    dirty = _git(root, 'status', '--porcelain').stdout.splitlines()
    if dirty:
        problems.append(t('there are uncommitted changes — commit them first, so the tag '
                          'points at what gets typeset:') + ''.join(
                              '\n    ' + line for line in dirty[:10]))
    if valuesmod.placeholder_files(cfg):
        problems.append(t('the analysis values are still the placeholders octavo init '
                          'wrote — run the analysis first'))
    stamp = anamod.read_stamp(cfg)
    stale = [cfg.rel(u.src) for u in anamod.units(cfg) if anamod.is_stale(cfg, u, stamp)]
    if stale:
        problems.append(t('the analysis is stale ({files}) — run octavo analysis run, '
                          'commit results/, then release', files=', '.join(stale)))
    if _git(root, 'remote', 'get-url', 'origin').returncode != 0:
        problems.append(t('there is no remote called origin to push the tag to'))
    if need_gh:
        if not shutil.which('gh'):
            problems.append(t('the GitHub CLI (gh) is not installed: '
                              'https://cli.github.com/ (then gh auth login)'))
        elif subprocess.run(['gh', 'auth', 'status'], capture_output=True).returncode != 0:
            problems.append(t('gh is not logged in (gh auth login)'))
    if problems:
        raise ReleaseError('\n'.join('  - ' + p for p in problems))
    return tag


def assets(results: list, label: str) -> list:
    """添付するファイル。[(元のパス, 添付するときの名前)]。

    論文の PDF は main.pdf なので、そのままでは何の版か分からない。
    `<文書>-<ラベル>.pdf` にし、同じ名前が重なるときだけ形式名を足す。
    """
    picked = []
    for r in results:
        files = [r.compiled] if r.compiled else []
        files += [Path(o) for o in r.outputs if Path(o).suffix == '.docx']
        picked += [(r, Path(f)) for f in files if Path(f).is_file()]
    names = [f'{r.doc}-{label}{p.suffix}' for r, p in picked]
    out = []
    for (r, p), name in zip(picked, names):
        if names.count(name) > 1:
            name = f'{r.doc}-{label}-{r.target}{p.suffix}'
        out.append((p, name))
    return out


def notes(cfg, tag: str, sha: str, files: list) -> str:
    """Release の本文。何から・何で組んだかを残す（作り直したときに比べられるように）。"""
    from . import pandocrun
    try:
        pandoc = pandocrun.version_str()
    except Exception:
        pandoc = '?'
    typst = subprocess.run(['typst', '--version'], capture_output=True, text=True,
                           encoding='utf-8', errors='replace').stdout.strip() \
        if shutil.which('typst') else '-'
    lines = [
        f'`{tag}` — commit `{sha}`',
        '',
        f'- Octavo {__version__}',
        f'- pandoc {pandoc}',
        f'- {typst}',
        '',
    ] + [f'- `{name}`' for _, name in files]
    return '\n'.join(lines) + '\n'


def run(cfg, doc_name: str, label: str, targets=None, anonymous: bool = False,
        offline: bool = False, dry_run: bool = False) -> int:
    import sys
    try:
        tag = preflight(cfg, doc_name, label, need_gh=not dry_run)
    except ReleaseError as e:
        print(t('not released:') + '\n' + str(e), file=sys.stderr)
        return 1

    doc = cfg.document(doc_name)
    results = buildmod.run(cfg, doc_names=[doc_name], targets=targets,
                           appendix=bool(getattr(doc, 'appendix', None)),
                           do_compile=True, offline=offline, anonymous=anonymous)
    bad = [r for r in results if not r.ok]
    if bad:
        for r in bad:
            print(f'== {r.doc} -> {r.target}', file=sys.stderr)
            for line in r.report:
                print('  ' + line, file=sys.stderr)
        print(t('not released: the build failed'), file=sys.stderr)
        return 1
    files = assets(results, label)
    if not files:
        print(t('not released: nothing was typeset to attach (no PDF or Word file)'),
              file=sys.stderr)
        return 1

    sha = _git(cfg.root, 'rev-parse', '--short', 'HEAD').stdout.strip()
    body = notes(cfg, tag, sha, files)
    print(t('tag {tag} on {sha}, with:', tag=tag, sha=sha))
    for p, name in files:
        print(f'  {name}  ({cfg.rel(p)})')
    if dry_run:
        print(t('(dry run — nothing tagged, pushed or uploaded)'))
        return 0

    root = cfg.root
    r = _git(root, 'tag', '-a', tag, '-m', f'{doc_name} {label}')
    if r.returncode != 0:
        print(r.stderr, file=sys.stderr)
        return 1
    r = _git(root, 'push', 'origin', f'refs/tags/{tag}')
    if r.returncode != 0:
        print(r.stderr + '\n' + t('the tag was made here but not pushed: '
                                  'git push origin {tag}', tag=tag), file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        tmpd = Path(tmp)
        upload = []
        for p, name in files:
            shutil.copyfile(p, tmpd / name)
            upload.append(str(tmpd / name))
        (tmpd / 'notes.md').write_text(body, encoding='utf-8')
        r = subprocess.run(['gh', 'release', 'create', tag, *upload,
                            '--title', f'{doc_name} {label}',
                            '--notes-file', str(tmpd / 'notes.md')],
                           cwd=root, capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
    if r.returncode != 0:
        print(r.stderr + '\n' + t('the tag {tag} is pushed, but the release was not '
                                  'made. Run octavo release again after deleting the '
                                  'tag (git tag -d {tag} && git push origin :refs/tags/{tag}), '
                                  'or attach the files by hand with gh release create',
                                  tag=tag), file=sys.stderr)
        return 1
    print(r.stdout.strip())
    return 0
