# -*- coding: utf-8 -*-
"""Word（.docx）バックエンド。

pandoc が .docx を直接書く（中間の .tex は作らない）。見た目は
`--reference-doc` に渡す雛形 .docx の**スタイル定義**で決まる。雛形は

    octavo reference-docx word/reference.docx     （pandoc の既定から作る）

で作り、Word で「見出し 1」「本文」「表のキャプション」等のスタイルを直してから
`docx_reference` に指定する。中身は空でよい（スタイルだけ使う）。

Word には自動採番の相互参照が無い（pandoc も振らない）ので、**節・図・表・式の
番号は Octavo が数えて文字で入れる**（numbers_itself = False、数え方は crossref.py）。
本文の `@fig-trend` は「図2.1」になり、図のブックマークへのリンクが付く。
"""
from __future__ import annotations

import re
from pathlib import Path

from .. import crossref as xref
from .. import md as mdlib
from .base import Backend, Ctx
from ..i18n import t, tag


class DocxBackend(Backend):
    name = 'docx'
    label = 'Word (.docx)'
    pandoc_to = 'docx'
    ext = '.docx'
    table_ext = '.md'               # 分析が書いた表は Markdown 版を本文に入れる
    default_figure_ext = '.png'
    min_pandoc = (2, 8)
    binary = True
    always_standalone = True
    numbers_itself = False          # 番号は Octavo が文字で入れる

    def input_extras(self) -> tuple:
        return ('fenced_divs',)

    def pandoc_args(self, ctx: Ctx) -> list:
        args = ['-t', 'docx', '--wrap=preserve', '--standalone',
                '--top-level-division=section']
        ref = ctx.cfg['docx_reference']
        if ref and Path(ref).exists():
            args += ['--reference-doc', str(ref)]
            ctx.say(f'{tag("Word")} ' + t('using the styles from {file}', file=Path(ref).name))
        elif ref:
            ctx.say(f'{tag("Word")} ' + t('no reference document at {path} — '
                                           "pandoc's default look it is", path=ref))
        if ctx.profile_opt('toc'):
            args += ['--toc', f'--toc-depth={ctx.cfg["toc_depth"]}']
        if ctx.profile_opt('number_sections'):
            args += ['--number-sections']
        if ctx.cfg['docx_track_changes_ready']:
            args += ['-M', 'lang=' + ('ja-JP' if ctx.lang == 'ja' else 'en-US')]
        return args

    # -- 差し替え -----------------------------------------------------------
    def fmt_ref(self, item, short: bool, ctx: Ctx) -> str:
        """番号を文字で書き、図・表・節にはそのブックマーク（pandoc が張る）へリンクを
        付ける。式にはブックマークが無いので文字だけ。"""
        text = xref.text_of(item, ctx.lang, short)
        if item.kind == 'eq' or item.label not in ctx.crossref_local:
            return text
        return f'[{text}](#{item.label})'

    def check(self, text: str, ctx: Ctx) -> None:
        pass


def make_reference_docx(dest: Path) -> Path:
    """pandoc の既定の雛形 .docx を書き出す（Word で編集して使う）。"""
    import subprocess
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(['pandoc', '-o', str(dest), '--print-default-data-file',
                        'reference.docx'], capture_output=True)
    if r.returncode != 0 or not dest.exists():
        # pandoc 3 系は --print-default-data-file が標準出力に出る
        r = subprocess.run(['pandoc', '--print-default-data-file', 'reference.docx'],
                           capture_output=True)
        if r.returncode != 0:
            raise RuntimeError(t('could not get the default reference.docx out of '
                                 'pandoc:') + '\n'
                               + r.stderr.decode('utf-8', 'replace'))
        dest.write_bytes(r.stdout)
    return dest


def outline(md_text: str) -> list:
    """Word に渡す前に見出し構成を見せる（章立ての確認用）。"""
    out = []
    for line in mdlib.drop_references(md_text).split('\n'):
        m = re.match(r'^(#{1,4})\s+(.+?)(\s*\{#[^}]*\})?$', line)
        if m:
            out.append('  ' * (len(m.group(1)) - 1) + m.group(2))
    return out
