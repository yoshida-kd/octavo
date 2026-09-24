# -*- coding: utf-8 -*-
"""Typst 台本（発表者ノート）バックエンド。TeX が要らない。

スライドと**同じ原稿から**、1ページ＝1枚のスライドの A4 縦を出す。各ページは
上がそのスライドの中身（小さめ）、下が `::: notes` に書いた発表者ノート。
教室で手元に置く紙、あるいは画面の脇に出す PDF のためのもの。

    octavo build 講義-03 --to typst-notes --compile

スライド側（typst-slides）は `::: notes` を落とす — 投影する画面に出す場所が
無いため。**落としたものの行き先がここ**。だから中身の取捨（`::: {.slides-only}`
など）はスライドとまったく同じで、違うのはノートを残すことと体裁だけ。

`::: notes` は div のまま pandoc に渡しても Typst では何の印も残らないので、
`notes_wrap` で生の Typst に包んで `#octavo-note[ … ]` にする（beamer は div の
まま渡すと `\\note{}` になるので、そちらは包まない）。
"""
from __future__ import annotations

import re

from .base import Ctx
from .latex import check_assets, check_cjk
from .typst import typst_escape
from ..i18n import t, tag
from .typst_slides import TypstSlidesBackend, heading_level


class TypstNotesBackend(TypstSlidesBackend):
    name = 'typst-notes'
    label = 'Typst speaker script'
    keeps_notes = True
    # pandoc に渡る前に `::: notes` をこれで囲み直す。中身は Markdown のまま。
    notes_wrap = ('```{=typst}\n#octavo-note[\n```',
                  '```{=typst}\n]\n```')

    def fmt_figure(self, m: re.Match, ctx: Ctx) -> str:
        """A4 の紙にノートと同居するので、図は高さを決め打ちで抑える。

        スライド側の `height: 1fr`（残り全部）をそのまま使うと、図のある回は
        ノートが次のページへ押し出される。
        """
        f, num = m.group('file'), m.group('num')
        cap = ' '.join(m.group('cap').split())
        rel = ctx.rel(ctx.figure_path(f))
        ctx.say(f'{tag("figure")} {num} -> {rel}')
        block = ('\n```{=typst}\n'
                 '#block(width: 100%, align(center,\n'
                 f'  image("{rel}", width: 100%, height: 6cm, fit: "contain")))\n')
        if not cap:
            return block + '```\n'
        label = self.caption_label(m, num, ctx)
        return (block
                + '#align(center, text(size: 0.8em, fill: luma(60))'
                + f'[*{typst_escape(label)}* {typst_escape(cap)}])\n'
                + '```\n')

    def template(self, ctx: Ctx) -> str:
        return ctx.template('slides/typst-notes.typ').read_text(encoding='utf-8')

    def check(self, typ: str, ctx: Ctx) -> None:
        check_assets(ctx, tables=[],
                     figures=re.findall(r'image\("[^"]*?/?([\w.-]+\.\w+)"', typ),
                     refs=re.findall(r'image\("([^"]+)"', typ))
        check_cjk(typ, ctx, '.typ',
                  t('the CJK font in typst_slides_font must be installed '
                    '(check with: typst fonts)'),
                  templates=[ctx.template('slides/typst-notes.typ')])
        m = re.search(r'slide-level: (\d)', typ)
        level = int(m.group(1)) if m else 1
        slides = sum(1 for l in typ.split('\n') if heading_level(l) == level)
        # 行まるごとで数える。テンプレートの説明文にも `#octavo-note[…]` と
        # 書いてあるので、単なる部分一致だと1つ多く数える。
        notes = sum(1 for l in typ.split('\n') if l.strip() == '#octavo-note[')
        ctx.say(f'{tag("script")} ' + t('{slides} {slides|slide|slides} / {notes} {notes|note|notes}',
                                         slides=slides, notes=notes))
        if slides and not notes:
            ctx.say(f'{tag("script")} ' + t('not one `::: notes` — this is just the '
                                             'deck on paper'))
