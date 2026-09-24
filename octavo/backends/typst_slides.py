# -*- coding: utf-8 -*-
"""Typst スライド（学会報告・授業スライド）バックエンド。TeX が要らない。

**パッケージを使わない素の Typst** で組む。体裁は templates/slides/typst-slides.typ に
あり、Octavo はその前に題扉などの値（`#let octavo = (…)`）を、後ろに本文を
書いて完結した1つの .typ にする。アニメーション（段階表示）は持たない。

原稿の書き方は Beamer と同じ:

    ---
    title: 発表の題
    author: 著者名
    institute: 所属
    date: 2026-09-01
    ---

    # 第1部            <- 節の扉（「#」と「##」の両方があるとき）

    ## スライドの題     <- ここが1枚のスライドになる

    - 箇条書き

見出しが1段しか無ければ、その見出しが1枚ずつのスライドになる。
`::: notes`（発表者ノート）は PDF に出す場所が無いので落とす。
"""
from __future__ import annotations

import re

from .base import Ctx
from ..i18n import t, tag
from .latex import check_assets, check_cjk
from .typst import TypstBackend, font_expr, typst_escape

META_KEYS = ('title', 'subtitle', 'author', 'institute', 'date')


class TypstSlidesBackend(TypstBackend):
    name = 'typst-slides'
    label = 'Typst slides'
    always_standalone = True
    is_slides = True
    uses_table_map = False         # スライドに外部の表ファイルを持ち込まない
    auto_numbers_captions = False  # スライドの図表は通し番号を出さない
    wants_abstract_file = False

    def pandoc_args(self, ctx: Ctx) -> list:
        # 題扉とページの体裁は自前のテンプレートが持つので --standalone にしない
        return ['-t', self.writer(ctx), '--wrap=preserve',
                '--top-level-division=section']

    # -- 差し替え -----------------------------------------------------------
    def fmt_figure(self, m: re.Match, ctx: Ctx) -> str:
        """スライドの図は「枠に収まること」が最優先。残りの高さいっぱいに置く。

        番号は自動では振らない（スライドに通し番号の相互参照は無い）。ただし
        原稿が `**図1．…**` とキャプションを書いたのなら、それは見せたくて
        書いたものなので、図の下に小さく出す。黙って捨てない。
        """
        f, num = m.group('file'), m.group('num')
        cap = ' '.join(m.group('cap').split())
        rel = ctx.rel(ctx.figure_path(f))
        ctx.say(f'{tag("figure")} {num} -> {rel}')
        block = ('\n```{=typst}\n'
                 '#block(width: 100%, height: 1fr, align(center + horizon,\n'
                 f'  image("{rel}", width: 100%, height: 100%, fit: "contain")))\n')
        if not cap:
            return block + '```\n'
        label = self.caption_label(m, num, ctx)
        return (block
                + '#align(center, text(size: 0.62em, fill: luma(60))'
                + f'[*{typst_escape(label)}* {typst_escape(cap)}])\n'
                + '```\n')

    @staticmethod
    def caption_label(m: re.Match, num: str, ctx: Ctx) -> str:
        """図の見出し。原稿が書いた語に合わせる（「図1．」/「Figure 1.」）。

        英語でも「図」の書式で組んでいて、Figure1． と全角の句点が付いていた。"""
        word = re.search(r'\*\*(Figure|図)', m.group(0))
        english = word.group(1) == 'Figure' if word else ctx.lang != 'ja'
        return f'Figure {num}.' if english else f'図{num}．'

    # -- 変換後 -------------------------------------------------------------
    def crossrefs(self, typ: str, ctx: Ctx) -> str:
        # スライドの図表には番号もラベルも付けないので、「図1」は文字のまま残す
        return typ

    def postprocess(self, typ: str, ctx: Ctx) -> str:
        body = super().postprocess(typ, ctx)
        levels = {heading_level(l) for l in body.split('\n')} - {None}
        slide_level = 2 if {1, 2} <= levels else (min(levels) if levels else 1)
        if slide_level == 2:
            body = promote_sections_with_content(body)
        return (f'// octavo build --to {self.name} が作った。手で直さない。\n'
                + self.meta_block(ctx, slide_level) + '\n'
                + self.template(ctx).rstrip() + '\n\n'
                + body)

    def meta_block(self, ctx: Ctx, slide_level: int) -> str:
        cfg = ctx.cfg
        drop = set(cfg['anonymous_drop_meta'] or ()) if ctx.anonymous else set()
        sep = '、' if ctx.lang == 'ja' else ', '
        fields = []
        for k in META_KEYS:
            v = ctx.meta.get(k) if k not in drop else None
            if isinstance(v, (list, tuple)):
                v = sep.join(str(x) for x in v)
            fields.append(f'  {k}: ' + ('none' if v in (None, '') else
                                         f'[{_content_escape(str(v))}]'))
        num = cfg['typst_slides_numbering']
        acc = cfg['typst_slides_accent']
        fields += [f'  lang: "{ctx.lang}"',
                   f'  slide-level: {slide_level}',
                   f'  aspect: "{cfg["typst_slides_aspect"]}"',
                   '  numbering: ' + (f'"{num}"' if num else 'none'),
                   '  section-slides: '
                   + ('true' if cfg['typst_slides_section_slides'] else 'false'),
                   '  accent: ' + (f'rgb("{acc}")' if acc else 'none'),
                   '  running-header: '
                   + ('true' if cfg['typst_slides_running_header'] else 'false'),
                   '  font: ' + font_expr(ctx.lang, 'sans', cfg['typst_slides_font'])]
        return '#let octavo = (\n' + ',\n'.join(fields) + ',\n)\n'

    def template(self, ctx: Ctx) -> str:
        return ctx.template('slides/typst-slides.typ').read_text(encoding='utf-8')

    def check(self, typ: str, ctx: Ctx) -> None:
        check_assets(ctx, tables=[],
                     figures=re.findall(r'image\("[^"]*?/?([\w.-]+\.\w+)"', typ),
                     refs=re.findall(r'image\("([^"]+)"', typ))
        check_cjk(typ, ctx, '.typ',
                  t('the CJK font in typst_slides_font must be installed '
                    '(check with: typst fonts)'),
                  templates=[ctx.template('slides/typst-slides.typ')])
        m = re.search(r'slide-level: (\d)', typ)
        level = int(m.group(1)) if m else 1
        slides = sum(1 for l in typ.split('\n') if heading_level(l) == level)
        ctx.say(f'{tag("slides")} ' + t('{n} {n|slide|slides} (title and section slides not counted)',
                                         n=slides))


def promote_sections_with_content(typ: str) -> str:
    """「#」の直後に本文があるなら、節の扉ではなく題のある1枚にする。

    `# 今日の狙い` の下にいきなり箇条書きがある原稿や、citeproc が足す
    「参考文献」の見出しがこれに当たる。扉にすると中身が題の無い次の
    ページに流れてしまう。
    """
    lines = typ.split('\n')
    for i, line in enumerate(lines):
        if heading_level(line) != 1:
            continue
        j = i + 1
        while j < len(lines) and (not lines[j].strip()
                                  or re.fullmatch(r'<[^<>\s]+>', lines[j].strip())):
            j += 1
        if j < len(lines) and heading_level(lines[j]) is None:
            lines[i] = ('=' + line if line.startswith('=')
                        else line.replace('#heading(level: 1', '#heading(level: 2', 1))
    return '\n'.join(lines)


def heading_level(line: str) -> int | None:
    """pandoc の Typst 出力の見出しの深さ。見出しでなければ None。

    ふつうは `== 題`。番号を振らない見出し（citeproc の「参考文献」など）は
    `#heading(level: 1, numbering: none)[…]` で出てくる。
    """
    m = re.match(r'(=+) ', line) or re.match(r'#heading\(level: (\d+)', line)
    if not m:
        return None
    return len(m.group(1)) if m.group(1).startswith('=') else int(m.group(1))


def _content_escape(s: str) -> str:
    """`[…]` の中に置く文字列。角括弧も閉じないように逃がす。"""
    return typst_escape(s).replace('[', '\\[').replace(']', '\\]')
