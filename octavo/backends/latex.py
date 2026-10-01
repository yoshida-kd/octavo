# -*- coding: utf-8 -*-
"""LaTeX（LuaLaTeX）バックエンド。

profile が 'paper' のときは body.tex（断片）を作り、main.tex は手で管理する。
profile が 'handout' のときは完結した .tex を出す（授業用 A4 プリント）。

引用は CSL（pandoc --citeproc）で解決済みの地の文として出るので、main.tex 側で
biblatex を読む必要はない。代わりに CSLReferences 環境の定義が要る
（templates/paper/csl-preamble.tex。同梱の main.tex には最初から入っている。standalone のときは pandoc の
既定テンプレートが定義を持っているので不要）。
"""
from __future__ import annotations

import re
from pathlib import Path

from .. import md as mdlib
from .. import crossref as xref
from .base import Backend, Ctx, missing_table
from ..i18n import t, tag


def latex_figure_note(part: str) -> str:
    """図表の直後の出典・注を小さい字で。LaTeX の図表は浮動体なので、注は図表の
    直後の本文に置く（浮動体が動くと離れることがある）。"""
    raw = {'open': '', 'middle': '\\par\\begingroup\\footnotesize',
           'close': '\\par\\endgroup'}[part]
    return f'\n```{{=latex}}\n{raw}\n```\n' if raw else ''


class LatexBackend(Backend):
    name = 'latex'
    label = 'LaTeX (LuaLaTeX)'
    pandoc_to = 'latex'
    ext = '.tex'
    table_ext = '.tex'
    default_figure_ext = '.pdf'
    min_pandoc = (2, 8)
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
            # 番号の振り方（節ごと／通し）。main.tex を持たないので、ここで前置きに足す
            ctx.out_dir.mkdir(parents=True, exist_ok=True)
            cr = ctx.out_dir / f'{ctx.doc_name}-crossref.tex'
            cr.write_text(crossref_tex(ctx), encoding='utf-8')
            args += ['--include-in-header', str(cr)]
            args += no_babel_for_japanese(ctx)
            if ctx.profile_opt('toc'):
                args += ['--toc', f'--toc-depth={ctx.cfg["toc_depth"]}']
        if ctx.profile_opt('number_sections'):
            args += ['--number-sections']
        return args

    # -- 差し替え -----------------------------------------------------------
    def fmt_figure_note(self, part: str, kind: str, ctx: Ctx) -> str:
        return latex_figure_note(part)

    def fmt_external_table(self, name: str, caption: str, label: str, ctx: Ctx) -> str:
        """分析が書いた表の中身（tables/<名前>.tex）を、table 環境・キャプション・
        ラベルで包んで入れる。中身の読み込みは \\inputtable（なければ目印を出す）。"""
        rel = ctx.rel(ctx.table_path(name))[:-len(self.table_ext)]
        if not ctx.table_path(name).is_file():
            ctx.say(f'{tag("table")} ' + missing_table(ctx, ctx.table_path(name), name))
        ctx.say(f'{tag("table")} {label} -> \\inputtable{{{rel}}}')
        return ('\n```{=latex}\n\\begin{table}[htbp]\n\\centering\n'
                f'\\caption{{{tex_escape(caption)}}}\\label{{{label}}}\n'
                f'\\inputtable{{{rel}}}\n\\end{{table}}\n```\n')

    def fmt_ref(self, item, short: bool, ctx: Ctx) -> str:
        return f'`{latex_ref(item, short, ctx)}`{{=latex}}'

    # -- 回の区切り・事例などのブロック ----------------------------------------
    def fmt_session(self, attrs: dict, ctx: Ctx) -> str:
        return '\n```{=latex}\n\\clearpage\n```\n' if ctx.standalone else ''

    def fmt_appendix_start(self, ctx: Ctx) -> str:
        brk = '\\clearpage\n' if ctx.standalone else ''
        return '\n```{=latex}\n' + brk + '\\appendix\n```\n'

    def fmt_theorem(self, env, item, title: str, body: str, ctx: Ctx) -> str:
        opt = f'[{tex_escape(title)}]' if title else ''
        lab = f'\\label{{{item.label}}}' if item is not None and item.label else ''
        return (f'```{{=latex}}\n\\begin{{{env.name}}}{opt}{lab}\n```\n\n'
                + body.strip('\n') + f'\n\n```{{=latex}}\n\\end{{{env.name}}}\n```')

    def fmt_restate(self, env, item, title: str, body: str, ctx: Ctx,
                    short: bool = False) -> str:
        ja = ctx.lang == 'ja'
        local = item is not None and item.label and item.label in ctx.crossref_local
        head = (latex_ref(item, False, ctx) if local
                else (xref.text_of(item, ctx.lang) if item is not None else env.word))
        tt = ''
        if title:
            tt = f'（{tex_escape(title)}）' if ja else f' ({tex_escape(title)}).'
        page = f'p.~\\pageref{{{item.label}}}' if local else ''
        if short:
            tail = f'\\dotfill{page}' if page else ''
            return f'```{{=latex}}\n\\par\\noindent\\textbf{{{head}}}\\quad {tt}{tail}\\par\n```'
        return (f'```{{=latex}}\n\\par\\medskip\\noindent\\textbf{{{head}}}{tt}\\quad\n```\n\n'
                + body.strip('\n')
                + '\n\n```{=latex}\n\\par\\medskip\n```')

    def includes_appendix(self, layout: str) -> bool:
        code = '\n'.join(split_comment(l)[0] for l in layout.split('\n'))
        return bool(re.search(r'\\(?:input|include)\{appendix(?:\.tex)?\}', code))

    def crossref_files(self, ctx: Ctx) -> list:
        return [('crossref.tex', crossref_tex(ctx))]

    def uses_anonymous_guard(self, text: str) -> bool:
        code = '\n'.join(split_comment(l)[0] for l in text.split('\n'))
        return bool(re.search(r'(?<!\\newif)\\ifanonymous', code))

    def flags(self, ctx: Ctx) -> tuple:
        return ('flags.tex',
                '% octavo build が毎回書き換える。手で直さない。\n'
                '\\newif\\ifanonymous\n'
                f'\\anonymous{"true" if ctx.anonymous else "false"}\n')

    # -- 投稿用にまとめ直す ---------------------------------------------------
    def flatten_assets(self, text: str) -> tuple:
        """`\\includegraphics{../../assets/figures/x.pdf}` を `{x.pdf}` にする。

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
            # 「有れば使う」ものなので、なくても欠落として数えない。
            if '#' not in code and '\\IfFileExists' not in code:
                code = GRAPHICS.sub(graphics, code)
                code = KEYED.sub(keyed, code)
            out.append(code + comment)
        return '\n'.join(out), refs

    # -- 変換後 -------------------------------------------------------------
    def postprocess(self, tex: str, ctx: Ctx) -> str:
        # pandoc 2.x の hypertarget ラッパを外す
        tex = re.sub(r'\\hypertarget\{[^}]*\}\{%\n(.*?)\}\n', r'\1\n', tex, flags=re.S)
        tex = numbered_equations(tex)

        # キャプションのない表に番号を消費させない
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
            # 定義がなくなったときだけ言う（毎回言うと読まれなくなる）
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
                + '   ' + t('({name} lives beside the manuscript)',
                          name='main.tex'))


# ---------------------------------------------------------------- 補助（他形式でも使う）

def latex_ref(item, short: bool, ctx: Ctx) -> str:
    """`図\\ref{fig-x}` / `Figure~\\ref{fig-x}`。式は \\eqref（括弧付きの番号）。"""
    ref = (f'\\eqref{{{item.label}}}' if item.kind == 'eq'
           else f'\\ref{{{item.label}}}')
    if short:
        return ref
    ja = ctx.lang == 'ja'
    if item.kind == 'sec':
        if item.appendix:
            return f'付録{ref}' if ja else f'Appendix~{ref}'
        return f'第{ref}節' if ja else f'Section~{ref}'
    if item.word:
        return f'{item.word}{ref}' if ja else f'{item.word}~{ref}'
    word = {'fig': ('図', 'Figure'), 'tbl': ('表', 'Table'), 'eq': ('式', 'Equation')}
    return f'{word[item.kind][0]}{ref}' if ja else f'{word[item.kind][1]}~{ref}'


def crossref_tex(ctx: Ctx) -> str:
    """番号の振り方。節ごと（既定）なら図・表・式を \\section ごとに数え直す。"""
    lines = ['% octavo build が毎回書き換える。手で直さない（振り方は crossref_numbering）。',
             '\\usepackage{amsmath}']
    if ctx.numbering_mode() == 'section':
        lines += ['\\counterwithin{figure}{section}',
                  '\\counterwithin{table}{section}',
                  '\\numberwithin{equation}{section}']
    lines += theorem_defs(ctx)
    if ctx.standalone:
        # 最初の節の番号（ガイダンスを 0 にする）と、`#` ごとの改ページ
        if ctx.first_section != 1:
            lines.append(f'\\AtBeginDocument{{\\setcounter{{section}}{{{ctx.first_section - 1}}}}}')
        brk = ctx.cfg['handout_pagebreak']
        if brk == 'section' or (brk == 'session' and not ctx.has_sessions):
            lines += ['\\let\\octavosection\\section',
                      '\\renewcommand{\\section}{\\clearpage\\octavosection}']
    return '\n'.join(lines) + '\n'


def theorem_defs(ctx: Ctx) -> list:
    """事例・論点などのブロックの \\newtheorem。番号の組ごとに最初の1つが番号を持ち、
    残りはそれを共有する（\\newtheorem{question}[case]{論点}）。ヘッダーで同じ名前を
    定義してあればそちらを使う（二重定義で止めない）。"""
    out = ['\\usepackage{amsthm}', '\\theoremstyle{definition}', '\\makeatletter']
    leader: dict = {}
    within = '[section]' if ctx.numbering_mode() == 'section' else ''
    for env in ctx.envs.values():
        if env.counter is None:
            d = f'\\newtheorem*{{{env.name}}}{{{env.word}}}'
        elif env.counter in leader:
            d = f'\\newtheorem{{{env.name}}}[{leader[env.counter]}]{{{env.word}}}'
        else:
            leader[env.counter] = env.name
            d = f'\\newtheorem{{{env.name}}}{{{env.word}}}{within}'
        out.append(f'\\@ifundefined{{{env.name}}}{{{d}}}{{}}')
    out.append('\\makeatother')
    return out


def numbered_equations(tex: str) -> str:
    """pandoc は別行の数式を `\\[ … \\]`（番号なし）で出す。ラベルのあるものだけ
    equation 環境にして番号を付ける。"""
    return re.sub(r'\\\[((?:(?!\\\]).)*?\\label\{eq-[^}]+\}(?:(?!\\\]).)*?)\\\]',
                  r'\\begin{equation}\1\\end{equation}', tex, flags=re.S)


def no_babel_for_japanese(ctx: Ctx) -> list:
    """日本語のとき babel / polyglossia を読み込ませない。

    引用の localization のために `-M lang=ja-JP` を渡す必要があるが、pandoc の
    LaTeX テンプレートはそれを見て babel を呼ぶ。日本語は babel にないので
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
        p = Path(ctx.cfg['figure_dir']) / (Path(f).stem + ctx.backend.figure_ext(ctx.cfg))
        # figures/ の外の図は、出力に書いたパスが辿れれば足りる（下で見る）
        if not p.exists() and any(Path(r).name == Path(f).name and _resolves(ctx, r)
                                  for r in refs):
            continue
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
