# -*- coding: utf-8 -*-
"""LaTeX（LuaLaTeX）バックエンド。

profile が 'paper' のときは body.tex（断片）を作り、main.tex は手で管理する。
profile が 'handout' のときは完結した .tex を出す（授業用 A4 プリント）。

引用は CSL（pandoc --citeproc）で解決済みの地の文として出るので、main.tex 側で
biblatex を読む必要は無い。代わりに CSLReferences 環境の定義が要る
（templates/paper/csl-preamble.tex。同梱の main.tex には最初から入っている。standalone のときは pandoc の
既定テンプレートが定義を持っているので不要）。
"""
from __future__ import annotations

import re
from pathlib import Path

from .. import md as mdlib
from .base import Backend, Ctx, apply_crossrefs
from ..i18n import t, tag


class LatexBackend(Backend):
    name = 'latex'
    label = 'LaTeX (LuaLaTeX)'
    pandoc_to = 'latex'
    ext = '.tex'
    table_ext = '.tex'
    default_figure_ext = '.pdf'
    min_pandoc = (2, 8)
    uses_table_map = True
    auto_numbers_captions = True
    wants_abstract_file = True      # main.tex が \input{abstract} で受ける
    anonymous_guard = '\\ifanonymous'
    main_name = 'main.tex'

    def input_extras(self) -> tuple:
        return ('raw_tex',)

    def pandoc_args(self, ctx: Ctx) -> list:
        args = ['-t', 'latex', '--wrap=preserve', '--top-level-division=section']
        if ctx.standalone:
            args += ['--standalone', f'--pdf-engine={ctx.cfg["latex_engine"]}']
            args += ['-V', f'documentclass={ctx.cfg["latex_documentclass"]}']
            if ctx.cfg['latex_fontsize']:
                args += ['-V', f'fontsize={ctx.cfg["latex_fontsize"]}']
            for opt in ctx.cfg['latex_classoptions']:
                args += ['-V', f'classoption={opt}']
            args += ['--include-in-header', str(ctx.template('handout/handout-header.tex'))]
            args += no_babel_for_japanese(ctx)
            if ctx.profile_opt('toc'):
                args += ['--toc', f'--toc-depth={ctx.cfg["toc_depth"]}']
        if ctx.profile_opt('number_sections'):
            args += ['--number-sections']
        return args

    # -- 差し替え -----------------------------------------------------------
    def fmt_table(self, m: re.Match, name, ctx: Ctx) -> str:
        if not name:
            return self.markdown_table(m, ctx)
        rel = ctx.rel(ctx.table_path(name))[:-len(self.table_ext)]
        ctx.say(f'{tag("table")} {m.group("num")} -> \\inputtable{{{rel}}}  '
                f'«{m.group("cap").strip()[:40]}»')
        return f'\n```{{=latex}}\n\\inputtable{{{rel}}}\n```\n'

    def fmt_figure(self, m: re.Match, ctx: Ctx) -> str:
        f, num = m.group('file'), m.group('num')
        cap = ' '.join(m.group('cap').split())
        rel = ctx.rel(ctx.figure_path(f))
        ctx.say(f'{tag("figure")} {num} -> {rel}')
        width = ctx.cfg['figure_width']
        return ('\n```{=latex}\n\\begin{figure}[htbp]\n\\centering\n'
                f'\\includegraphics[width={width}\\textwidth]{{{rel}}}\n'
                f'\\caption{{{tex_escape(cap)}}}\n\\label{{fig:{f}}}\n'
                '\\end{figure}\n```\n')

    def uses_anonymous_guard(self, text: str) -> bool:
        code = '\n'.join(split_comment(l)[0] for l in text.split('\n'))
        return bool(re.search(r'(?<!\\newif)\\ifanonymous', code))

    def flags(self, ctx: Ctx) -> tuple:
        return ('flags.tex',
                '% octavo build が毎回書き換える。手で直さない。\n'
                '\\newif\\ifanonymous\n'
                f'\\anonymous{"true" if ctx.anonymous else "false"}\n')

    # -- 投稿用に固め直す ---------------------------------------------------
    def flatten_assets(self, text: str) -> tuple:
        """`\\includegraphics{../../figures/x.pdf}` を `{x.pdf}` にする。

        **行コメントとマクロ定義は見ない。**main.tex には
        `\\newcommand{\\inputtable}[1]{...\\input{#1}...}` という定義や、
        使い方を書いたコメント行があり、そこを拾うと存在しないファイルを
        探しに行くため。
        """
        refs: list = []

        def graphics(m):
            refs.append(m.group('path'))
            return f"{m.group('head')}{{{Path(m.group('path')).name}}}"

        def keyed(m):
            refs.append(m.group('path') + '.tex')     # 拡張子は書かれない
            return f"{m.group('cmd')}{{{Path(m.group('path')).name}}}"

        out = []
        for line in text.split('\n'):
            code, comment = split_comment(line)
            # マクロ定義（#1）は触らない。\IfFileExists で守られた \input は
            # 「有れば使う」ものなので、無くても欠落として数えない。
            if '#' not in code and '\\IfFileExists' not in code:
                code = GRAPHICS.sub(graphics, code)
                code = KEYED.sub(keyed, code)
            out.append(code + comment)
        return '\n'.join(out), refs

    # -- 変換後 -------------------------------------------------------------
    def crossrefs(self, tex: str, ctx: Ctx) -> str:
        def label_of(name: str) -> str:
            """外部の表ファイルが実際に張っているラベルを読む（推測しない）。"""
            p = ctx.cfg['table_dir'] / f'{name}.tex'
            if p.exists():
                m = re.search(r'\\label\{([^}]+)\}', p.read_text(encoding='utf-8'))
                if m:
                    return m.group(1)
            return f'tab:{name}'

        def figure_labels(text):
            out = {}
            for f in re.findall(r'\\label\{fig:([\w.-]+)\}', text):
                m = re.match(r'fig([A-Z]?\d+)[_-]', f)
                if m:
                    out[m.group(1)] = f
            return out

        def wrap(lang, kind, ref):
            """原稿の書き方（日本語/英語）をそのまま保つ。"""
            if lang == 'ja':
                return {'table': f'表{ref}', 'figure': f'図{ref}',
                        'section': f'第{ref}節'}[kind]
            return {'table': f'Table~{ref}', 'figure': f'Figure~{ref}',
                    'section': f'Section~{ref}'}[kind]

        return apply_crossrefs(
            tex, ctx,
            table_ref=lambda lg, num, name: wrap(lg, 'table',
                                                 f'\\ref{{{label_of(name)}}}'),
            figure_ref=lambda lg, num, lab: wrap(lg, 'figure', f'\\ref{{fig:{lab}}}'),
            section_ref=lambda lg, a, b: wrap(
                lg, 'section', f'\\ref{{sec:{a}{"-" + b if b else ""}}}'),
            figure_labels=figure_labels)

    def postprocess(self, tex: str, ctx: Ctx) -> str:
        # pandoc 2.x の hypertarget ラッパを外す
        tex = re.sub(r'\\hypertarget\{[^}]*\}\{%\n(.*?)\}\n', r'\1\n', tex, flags=re.S)

        # キャプションの無い表に番号を消費させない
        def unnumber(m):
            b = m.group(0)
            return b if r'\caption' in b else b + '\n\\addtocounter{table}{-1}'
        tex = re.sub(r'\\begin\{longtable\}.*?\\end\{longtable\}', unnumber, tex, flags=re.S)
        return re.sub(r'\n{3,}', '\n\n', tex).strip() + '\n'

    def check(self, tex: str, ctx: Ctx) -> None:
        check_assets(ctx,
                     tables=[Path(x).name for x in
                             re.findall(r'\\inputtable\{([^}]+)\}', tex)],
                     figures=re.findall(
                         r'\\includegraphics(?:\[[^\]]*\])?\{[^}]*?/?([\w.-]+)\}', tex),
                     refs=re.findall(
                         r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', tex))
        check_cjk(tex, ctx, '.tex',
                  t('keep luatexja / ltjsarticle in main.tex'),
                  templates=[ctx.template('handout/handout-header.tex')]
                  if ctx.standalone else [])
        if r'\begin{CSLReferences}' in tex and not ctx.standalone:
            # 同梱の main.tex は定義を持っている。投稿先の main.tex に差し替えて
            # 定義が無くなったときだけ言う（毎回言うと読まれなくなる）
            main = ctx.out_dir / self.main_name
            if main.is_file() and 'CSLReferences' not in main.read_text(encoding='utf-8'):
                ctx.say(f'{tag("bib")} ' + t(
                    'main.tex does not define the CSLReferences environment the '
                    'bibliography uses — octavo template copy paper/csl-preamble.tex '
                    'has the definition'))

    def compile(self, ctx: Ctx, path: Path) -> list:
        return ['latexmk', f'-{ctx.cfg["latex_engine"]}', '-interaction=nonstopmode',
                '-halt-on-error', path.name]

    def next_step(self, ctx: Ctx) -> str:
        if ctx.standalone:
            return f'cd {ctx.out_dir} && latexmk -{ctx.cfg["latex_engine"]} {self.out_name(ctx)}'
        return (f'cd {ctx.out_dir} && latexmk -{ctx.cfg["latex_engine"]} main.tex'
                + '   ' + t('({name} lives beside the manuscript; octavo new writes it if missing)',
                          name='main.tex'))


# ---------------------------------------------------------------- 補助（他形式でも使う）

def no_babel_for_japanese(ctx: Ctx) -> list:
    """日本語のとき babel / polyglossia を読み込ませない。

    引用の localization のために `-M lang=ja-JP` を渡す必要があるが、pandoc の
    LaTeX テンプレートはそれを見て babel を呼ぶ。日本語は babel に無いので
    `\\usepackage[shorthands=off,main=]{babel}` という**壊れた行**が出る
    （pandoc 2.x で確認）。

    `-V lang=` はテンプレート変数だけを空にする。metadata の lang は
    そのまま残るので citeproc の localization には効いたまま、テンプレート側の
    `$if(lang)$` だけが偽になり、babel/polyglossia の塊ごと消える。
    和文の面倒は luatexja が見るので、これで困らない。
    """
    return ['-V', 'lang='] if ctx.lang == 'ja' else []


GRAPHICS = re.compile(r'(?P<head>\\includegraphics(?:\[[^\]]*\])?)'
                      r'\{(?P<path>[^{}#]+)\}')
KEYED = re.compile(r'(?P<cmd>\\(?:inputtable|input|include))'
                   r'\{(?P<path>[^{}#]+)\}')


def split_comment(line: str) -> tuple:
    """LaTeX の行を (コード, コメント) に割る。`\\%` はコメントではない。"""
    m = re.search(r'(?<!\\)%', line)
    return (line, '') if not m else (line[:m.start()], line[m.start():])


def tex_escape(s: str) -> str:
    """pandoc を通さず直接 LaTeX に埋める文字列（キャプション等）だけに使う。"""
    for a, b in (('\\', '\x00'), ('&', r'\&'), ('%', r'\%'), ('$', r'\$'),
                 ('#', r'\#'), ('_', r'\_'), ('{', r'\{'), ('}', r'\}'),
                 ('~', r'\textasciitilde{}'), ('^', r'\textasciicircum{}')):
        s = s.replace(a, b)
    return s.replace('\x00', r'\textbackslash{}')


FIG_EXT_TRY = ('.pdf', '.png', '.jpg', '.jpeg', '.svg', '.eps')


def _resolves(ctx: Ctx, ref: str) -> bool:
    """出力に書かれた指し先が、out_dir から実際に辿れるか。"""
    if ref.startswith(('/', 'data:')) or '://' in ref:
        return True                       # URL・絶対パスは組版側の責任
    p = ctx.out_dir / ref
    if p.suffix:
        return p.exists()
    # LaTeX は拡張子を省ける
    return any(p.with_suffix(e).exists() for e in FIG_EXT_TRY)


def check_assets(ctx: Ctx, tables, figures, refs=()) -> None:
    miss = 0
    for name in sorted(set(tables)):
        p = ctx.cfg['table_dir'] / f'{name}{ctx.backend.table_ext}'
        miss += not p.exists()
        ctx.say(_mark(p) + f'{p.parent.name}/{p.name}')
    for f in sorted(set(figures)):
        p = ctx.figure_path(Path(f).stem)
        miss += not p.exists()
        ctx.say(_mark(p) + f'{p.parent.name}/{p.name}')
    if miss:
        ctx.say(f'{tag("assets")} ' + t('{n} missing — typesetting will fail as it is',
                                          n=miss))

    # 上はファイル名だけを見ている。**出力に書かれたパスそのもの**が out_dir から
    # 辿れるかは別の話で、そこを見ていなかったために「OK」と言いながら組版が
    # file not found で落ちることがあった。
    broken = sorted({r for r in set(refs) if not _resolves(ctx, r)})
    for r in broken:
        ctx.say('  ' + t('unresolved {ref} — not reachable from the output ({dir}/)',
                          ref=r, dir=ctx.out_dir.name))
    if broken:
        ctx.say(f'{tag("assets")} ' + t('{n} {n|reference points|references point} '
                                          'nowhere — typesetting will fail as it is',
                                          n=len(broken)))


def _mark(p: Path) -> str:
    """資産の在り／無しの印。VS Code の problemMatcher が「欠落」を拾う。"""
    return '  ' + (t('OK') if p.exists() else t('MISSING')) + '   '


def _uncommented(text: str, suffix: str) -> str:
    """行ごと注釈の行を落とす。組版に届かないので、日本語があっても書体は要らない。

    生成物の先頭の注釈（「手で直さない」）、octavo.R が表に書く注釈、スライドの
    体裁の説明はどれも日本語で、英語の文書でも毎回 [CJK] と出ていた。"""
    mark = '%' if suffix == '.tex' else '//'
    return '\n'.join(l for l in text.split('\n') if not l.lstrip().startswith(mark))


def check_cjk(text, ctx: Ctx, table_suffix: str, hint: str, templates=()) -> None:
    """本文と表に日本語があれば、日本語の書体が要ると知らせる。

    templates は出力に丸ごと入っている体裁のファイル。その中の日本語（言語で
    分岐する見出しや警告の文言）は英語の文書では組まれないので、数えない。"""
    for tpl in templates:
        text = text.replace(Path(tpl).read_text(encoding='utf-8').rstrip(), '')
    hits = mdlib.cjk_lines(_uncommented(text, table_suffix))
    tdir = ctx.cfg['table_dir']
    tbls = sorted(p.name for p in tdir.glob(f'*{table_suffix}')
                  if mdlib.has_cjk(_uncommented(
                      p.read_text(encoding='utf-8', errors='replace'), table_suffix))) \
        if tdir.exists() else []
    if hits or tbls:
        ctx.say(f'{tag("CJK")} ' + t('{lines} {lines|line|lines} of text / {files} table {files|file|files} — {hint}',
                                      lines=len(hits), files=len(tbls), hint=hint))
