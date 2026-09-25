# -*- coding: utf-8 -*-
"""pandoc の呼び出しと版の判定。

pandoc の版によって使える機能が違うので、**呼ぶ前に判定して、駄目なら
理由をはっきり言って止める**。黙って劣化した出力を出さない。

    2.8  以上  --shift-heading-level-by
    2.11 以上  --citeproc（内蔵。それ以前は別体の pandoc-citeproc が要る）
    3.1  以上  -t typst
"""
from __future__ import annotations

import functools
import re
import shutil
import subprocess
import sys
from pathlib import Path
from .i18n import t


class PandocError(RuntimeError):
    pass


def _vtuple(s: str) -> tuple:
    return tuple(int(x) for x in re.findall(r'\d+', s)[:4])


@functools.lru_cache(maxsize=1)
def version() -> tuple:
    exe = shutil.which('pandoc')
    if not exe:
        raise PandocError(t('pandoc not found.') + '\n'
                          '  Ubuntu/WSL: sudo apt install pandoc\n'
                          '  macOS: brew install pandoc\n'
                          '  Windows: winget install JohnMacFarlane.Pandoc\n  '
                          + t('For a newer one, take the .deb from '
                              'https://github.com/jgm/pandoc/releases '
                              "(apt's is often old)"))
    out = subprocess.run([exe, '-v'], capture_output=True, text=True,
                         encoding='utf-8', errors='replace').stdout
    return _vtuple(out.split('\n')[0].split()[1])


def version_str() -> str:
    return '.'.join(map(str, version()))


def at_least(*want: int) -> bool:
    try:
        return version() >= tuple(want)
    except PandocError:
        return False


def require(*want: int, why: str = '') -> None:
    if not at_least(*want):
        need = '.'.join(map(str, want))
        raise PandocError(t('pandoc {need} or newer is required (this is {got})',
                            need=need, got=version_str())
                          + (f' — {why}' if why else '') + '\n  '
                          + t('take a newer .deb from '
                              'https://github.com/jgm/pandoc/releases'))


@functools.lru_cache(maxsize=1)
def has_builtin_citeproc() -> bool:
    return at_least(2, 11)


@functools.lru_cache(maxsize=None)
def writer_extensions(fmt: str) -> frozenset:
    """書き出し形式が知っている拡張の名前（有効・無効を問わない）。"""
    exe = shutil.which('pandoc')
    if not exe:
        return frozenset()
    out = subprocess.run([exe, f'--list-extensions={fmt}'], capture_output=True,
                         text=True, encoding='utf-8', errors='replace').stdout
    return frozenset(l[1:] for l in out.split() if l[:1] in '+-')


def input_format(east_asian: bool, extras: tuple = ()) -> str:
    """読み込み側の markdown 方言。"""
    ext = ['raw_attribute'] + list(extras)
    if east_asian:
        ext.append('east_asian_line_breaks')
    return 'markdown+' + '+'.join(dict.fromkeys(ext))


def run(md: str, args: list, cwd: Path | None = None,
        quiet: bool = False) -> str:
    """pandoc を走らせて標準出力を返す。失敗したら PandocError。"""
    cmd = ['pandoc'] + [str(a) for a in args]
    r = subprocess.run(cmd, input=md, capture_output=True, text=True,
                       encoding='utf-8', cwd=str(cwd) if cwd else None)
    if r.returncode != 0:
        raise PandocError(t('pandoc failed:') + '\n  ' + ' '.join(cmd)
                          + '\n' + r.stderr)
    if r.stderr.strip() and not quiet:
        for line in r.stderr.strip().split('\n'):
            print(f'  pandoc: {line}', file=sys.stderr)
    return r.stdout


def run_to_file(md: str, args: list, out: Path, cwd: Path | None = None,
                quiet: bool = False) -> None:
    """バイナリ出力（docx など）向け。pandoc に直接ファイルを書かせる。"""
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ['pandoc'] + [str(a) for a in args] + ['-o', str(out)]
    r = subprocess.run(cmd, input=md, capture_output=True, text=True,
                       encoding='utf-8', cwd=str(cwd) if cwd else None)
    if r.returncode != 0:
        raise PandocError(t('pandoc failed:') + '\n  ' + ' '.join(cmd)
                          + '\n' + r.stderr)
    if r.stderr.strip() and not quiet:
        for line in r.stderr.strip().split('\n'):
            print(f'  pandoc: {line}', file=sys.stderr)


def citeproc_args(bib: Path, csl: Path | None, locale: str | None,
                  ref_title: str | None, link_citations: bool = True,
                  suppress_bibliography: bool = False) -> list:
    """--citeproc 一式。CSL に一本化しているので全バックエンドが同じものを使う。

    suppress_bibliography=True は「引用は組むが、末尾の書誌一覧は出さない」。
    要旨だけを別ファイルに書き出すときと、スライドで使う。
    """
    require(2, 11, why=t('needed for CSL citation processing (--citeproc)'))
    args = ['--citeproc', '--bibliography', str(bib)]
    if csl:
        args += ['--csl', str(csl)]
    if locale:
        args += ['-M', f'lang={locale}']
    if ref_title and not suppress_bibliography:
        args += ['-M', f'reference-section-title={ref_title}']
    if link_citations:
        args += ['-M', 'link-citations=true']
    if suppress_bibliography:
        args += ['-M', 'suppress-bibliography=true']
    return args
