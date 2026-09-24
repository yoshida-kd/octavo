# -*- coding: utf-8 -*-
"""Beamer（学会報告・授業スライド）バックエンド。

**完結した .tex を出す**（main.tex は使わない）。スライドは題扉・テーマ・
フォントまで含めて1ファイルで完結させたほうが取り回しがよい。

原稿の書き方:

    ---
    title: 発表の題
    author: 著者名
    institute: 所属
    date: 2026-09-01
    ---

    # 第1部（section。目次に出る）

    ## スライドの題            <- ここが1枚のスライドになる（beamer_slide_level）

    - 箇条書き

    ::: notes
    ここは発表者ノート（--to beamer で beamer_notes: true のとき出る）
    :::

授業資料を1本の原稿から作る場合は、条件付きブロックで出し分ける:

    ::: {.slides-only}
    スライドにだけ出す
    :::

    ::: {.handout-only}
    A4 プリントにだけ出す（板書用の空欄など）
    :::
"""
from __future__ import annotations

import re
from pathlib import Path

from .base import Backend, Ctx
from ..i18n import t, tag
from .latex import check_assets, check_cjk, no_babel_for_japanese, tex_escape


class BeamerBackend(Backend):
    name = 'beamer'
    label = 'Beamer slides'
    pandoc_to = 'beamer'
    ext = '.tex'
    table_ext = '.tex'
    default_figure_ext = '.pdf'
    min_pandoc = (2, 8)
    always_standalone = True
    is_slides = True
    keeps_notes = True
    uses_table_map = False        # スライドに longtable を持ち込まない
    auto_numbers_captions = False  # スライドの図表は通し番号を出さない

    def input_extras(self) -> tuple:
        return ('raw_tex', 'fenced_divs')

    def pandoc_args(self, ctx: Ctx) -> list:
        cfg = ctx.cfg
        args = ['-t', 'beamer', '--wrap=preserve', '--standalone',
                f'--pdf-engine={cfg["latex_engine"]}',
                f'--slide-level={cfg["beamer_slide_level"]}']
        if cfg['beamer_theme']:
            args += ['-V', f'theme={cfg["beamer_theme"]}']
        if cfg['beamer_colortheme']:
            args += ['-V', f'colortheme={cfg["beamer_colortheme"]}']
        if cfg['beamer_fonttheme']:
            args += ['-V', f'fonttheme={cfg["beamer_fonttheme"]}']
        if cfg['beamer_aspectratio']:
            args += ['-V', f'aspectratio={cfg["beamer_aspectratio"]}']
        for opt in cfg['beamer_classoptions']:
            args += ['-V', f'classoption={opt}']
        if cfg['beamer_notes']:
            args += ['-V', 'classoption=notes=show']
        lang = 'ja' if ctx.lang == 'ja' else 'en'
        args += ['--include-in-header',
                 str(ctx.template(f'slides/beamer-header-{lang}.tex'))]
        if ctx.cfg['beamer_toc']:
            args += ['--toc', '--toc-depth=1']
        return args + no_babel_for_japanese(ctx)

    # -- 差し替え -----------------------------------------------------------
    def fmt_figure(self, m: re.Match, ctx: Ctx) -> str:
        """スライドの図は「枠に収まること」が最優先。高さで制限する。"""
        f = m.group('file')
        cap = ' '.join(m.group('cap').split())
        rel = ctx.rel(ctx.figure_path(f))
        ctx.say(f'{tag("figure")} {m.group("num")} -> {rel}')
        if not ctx.cfg['beamer_figure_captions']:
            return ('\n```{=latex}\n\\begin{center}\n'
                    f'\\includegraphics[width=\\linewidth,height=0.7\\textheight,'
                    f'keepaspectratio]{{{rel}}}\n\\end{{center}}\n```\n')
        return ('\n```{=latex}\n\\begin{figure}\n\\centering\n'
                f'\\includegraphics[width=\\linewidth,height=0.62\\textheight,'
                f'keepaspectratio]{{{rel}}}\n'
                f'\\caption{{{tex_escape(cap)}}}\n\\end{{figure}}\n```\n')

    # -- 変換後 -------------------------------------------------------------
    def postprocess(self, tex: str, ctx: Ctx) -> str:
        tex = re.sub(r'\n{3,}', '\n\n', tex)
        return tex.strip() + '\n'

    def check(self, tex: str, ctx: Ctx) -> None:
        check_assets(ctx, tables=[], figures=re.findall(
            r'\\includegraphics(?:\[[^\]]*\])?\{[^}]*?/?([\w.-]+)\}', tex),
            refs=re.findall(r'\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}', tex))
        check_cjk(tex, ctx, '.tex',
                  t('keep luatexja-preset in the Beamer header '
                    '(templates/slides/beamer-header-ja.tex)'),
                  templates=[ctx.template(
                      f"slides/beamer-header-{'ja' if ctx.lang == 'ja' else 'en'}.tex")])
        frames = len(re.findall(r'\\begin\{frame\}', tex))
        ctx.say(f'{tag("slides")} ' + t('{n} {n|frame|frames}', n=frames))
        long = [f for f in re.findall(r'\\begin\{frame\}.*?\\end\{frame\}', tex, re.S)
                if f.count('\n') > ctx.cfg['beamer_warn_lines']]
        if long:
            ctx.say(f'{tag("slides")} ' + t(
                '{n} {n|frame looks|frames look} likely to overflow (over {limit} lines) — '
                'split {n|it|them}, or use a smaller font',
                n=len(long), limit=ctx.cfg['beamer_warn_lines']))

    def compile(self, ctx: Ctx, path: Path) -> list:
        return ['latexmk', f'-{ctx.cfg["latex_engine"]}', '-interaction=nonstopmode',
                '-halt-on-error', path.name]

    def next_step(self, ctx: Ctx) -> str:
        return f'cd {ctx.out_dir} && latexmk -{ctx.cfg["latex_engine"]} {self.out_name(ctx)}'
