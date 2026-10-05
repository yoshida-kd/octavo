# -*- coding: utf-8 -*-
"""Typst 台本（発表者ノート）バックエンド。TeX が要らない。

スライドと**同じ原稿から**、投影するスライドの各ページを縮小して並べ、その下に
`::: notes` に書いた発表者ノートを置いた A4 縦を出す。教室で手元に置く紙、あるいは
画面の脇に出す PDF のためのもの。

    octavo build 講義-03 --to typst-notes --compile

スライドは**組んだスライドの PDF そのもの**を画像として貼る（Typst は PDF のページを
画像にできる）。だから台本の上の絵は、投影する画面と必ず同じになる（はみ出して
「（続き）」に分かれたページも、図の大きさも）。ノートがどのページのものかは、
スライド側（typst-slides）が落とした `::: notes` の場所に置く目印
（`<octavo-note-at>`）を `typst eval` で引いて決める。

組む（--compile）ときに、スライドも組み直す。ページの対応は
`<name>.notes.json` に書き、台本の .typ がそれを読む。
"""
from __future__ import annotations

import json
import os
import re
import subprocess

from .base import Backend, Ctx
from .latex import check_cjk
from ..i18n import t, tag
from .typst_slides import TypstSlidesBackend

# 囲みの印。ノートの中にも生の Typst の `]` は出る（図と注のまとまりなど）ので、
# 行末のコメントで見分ける
NOTE_OPEN = '#octavo-note[ // octavo-note'
NOTE_CLOSE = '] // octavo-note'
# 脚注の定義（`[^x]: …` と、その下の字下げした続き）。ノートの中の脚注が引く
FOOTNOTE_DEF = re.compile(r'^\[\^[^\]]+\]:')


class TypstNotesBackend(TypstSlidesBackend):
    name = 'typst-notes'
    label = 'Typst speaker script'
    keeps_notes = True
    notes_mark = None
    session_tag = 'notes'       # 講義ノートの回は <文書>-notes-<回>.pdf
    name_suffix = '-notes'      # 1本のスライドの台本は <名前>-notes.pdf（スライドと別の名前）
    # pandoc に渡る前に `::: notes` をこれで囲み直す。中身は Markdown のまま。
    notes_wrap = ('```{=typst}\n' + NOTE_OPEN + '\n```',
                  '```{=typst}\n' + NOTE_CLOSE + '\n```')

    # ノートの中の図は、紙の上で高さを抑える（スライドの絵は上にあるので小さくてよい）
    figure_box = 'height: 5cm'

    def template(self, ctx: Ctx) -> str:
        return ctx.template('slides/typst-notes.typ').read_text(encoding='utf-8')

    def pages_name(self, ctx: Ctx) -> str:
        return f'{ctx.doc_name}.notes.json'

    def deck_pdf(self, ctx: Ctx):
        from . import get
        stem = get('typst-slides').file_stem(ctx.doc_name, getattr(ctx.document, 'part', None))
        return ctx.cfg.out_dir('typst-slides', ctx.document) / f'{stem}.pdf'

    # -- 本文: ノートだけを取り出して、台本の関数に渡す ----------------------
    def final_markdown(self, body: str, ctx: Ctx) -> str:
        notes, defs, cur = [], [], None
        in_def = skip = False
        for line in body.split('\n'):
            bare = line.strip()
            if skip:                       # 開きの raw ブロックの閉じ（```）
                skip = False
                continue
            if cur is not None:
                if bare == NOTE_CLOSE and cur and cur[-1].strip() == '```{=typst}':
                    cur.pop()
                    notes.append(cur)
                    cur = None
                    continue
                cur.append(line)
                continue
            if bare == NOTE_OPEN:
                # 開きの raw ブロックの頭（```{=typst}）は直前の行に出ている
                cur, skip = [], True
                continue
            if FOOTNOTE_DEF.match(line):
                in_def = True
                defs.append(line)
                continue
            if in_def and (line.startswith((' ', '\t')) or not bare):
                defs.append(line)
                continue
            in_def = False
        ctx.say(f'{tag("script")} ' + t('{n} {n|note|notes} under the slides of {deck}',
                                         n=len(notes), deck=ctx.cfg.rel(self.deck_pdf(ctx))))
        deck = os.path.relpath(self.deck_pdf(ctx), ctx.out_dir).replace(os.sep, '/')
        call = f'#octavo-script(json("{self.pages_name(ctx)}"), "{deck}")'
        if not notes:
            return f'```{{=typst}}\n{call}\n```\n\n' + '\n'.join(defs)
        out = [f'```{{=typst}}\n{call}[\n```', '']
        for i, n in enumerate(notes):
            text = '\n'.join(n).strip('\n')
            # 箇条書きの中にあったノートは字下げされている。そろって外す
            ind = min((len(l) - len(l.lstrip()) for l in text.split('\n') if l.strip()),
                      default=0)
            out += ['\n'.join(l[ind:] for l in text.split('\n')), '']
            out += ['```{=typst}\n' + ('][' if i + 1 < len(notes) else ']') + '\n```', '']
        return '\n'.join(out + defs) + '\n'

    def fmt_ref(self, item, short: bool, ctx: Ctx) -> str:
        # 台本にはスライドの中身（図・節）がないので、参照は番号を文字で書く
        return Backend.fmt_ref(self, item, short, ctx)

    def check(self, typ: str, ctx: Ctx) -> None:
        check_cjk(typ, ctx, '.typ',
                  t('the CJK font in slides_font must be installed '
                    '(check with: typst fonts)'),
                  templates=[ctx.template('slides/typst-notes.typ'),
                             ctx.template('typst/crossref.typ')])

    # -- 組む: 先にスライドを組み、ノートのページを引く ------------------------
    def compile(self, ctx: Ctx, path):
        from .. import build
        r = build.build_one(ctx.cfg, ctx.document, 'typst-slides', do_compile=True,
                            **ctx.build_opts)
        deck = self.deck_pdf(ctx)
        if not r.ok or not deck.is_file():
            ctx.compile_error = (t('the slides could not be typeset, so the script has no '
                                   'pictures:') + '\n' + '\n'.join(r.report[-12:]))
            return None
        deck_typ = deck.with_suffix('.typ')
        root = self.root_arg(ctx)
        expr = ('(count: query(<octavo-deck-end>).map(it => it.location().page()).last(), '
                'pages: query(<octavo-note-at>).map(it => (it.value, it.location().page())))')
        q = subprocess.run(['typst', 'eval', expr, '--in', deck_typ.name, '--root', root],
                           cwd=str(deck.parent), capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
        if q.returncode != 0:
            ctx.compile_error = (t('could not read where the notes are in the slides '
                                   '(typst eval needs Typst 0.15):') + '\n'
                                 + (q.stdout + q.stderr).strip()[-800:])
            return None
        data = json.loads(q.stdout)
        # ノートの通し番号 -> スライドの物理ページ
        pages = [0] * (max((v for v, _ in data['pages']), default=-1) + 1)
        for v, page in data['pages']:
            pages[v] = page
        (ctx.out_dir / self.pages_name(ctx)).write_text(
            json.dumps({'count': data['count'], 'pages': pages}) + '\n', encoding='utf-8')
        ctx.say(f'{tag("script")} ' + t('{n} {n|slide|slides} from {deck}',
                                         n=data['count'], deck=ctx.cfg.rel(deck)))
        return ['typst', 'compile', '--root', root, path.name]

    def next_step(self, ctx: Ctx) -> str:
        return t('octavo build {name} --to typst-notes --compile (it typesets the slides '
                 'first and lays the notes under them)', name=ctx.doc_name)
