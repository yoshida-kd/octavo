# -*- coding: utf-8 -*-
"""ポスター（学会のポスター発表）のバックエンド。TeX が要らない。

体裁は templates/poster/typst-poster.typ。Octavo はその前に値（`#let octavo = (…)`）を、
後ろに本文を書いて1つの .typ にする（スライドと同じ形）。

原稿の一番上の段の見出し1つが1つの**マス**になり、既定では2列×3行の格子に左上から
順に入る。見出しの属性で結合と場所を決められる:

    # 結果 {span=2}            2列ぶん
    # モデル {rows=2}          2行ぶん
    # 補足 {cell="2,3"}        2列目の3行目（1 から数える）

格子は原稿の冒頭の `poster_grid: 2x3`（列×行）、行の高さの比は `poster_rows: [1, 2, 1]`。
題の帯には title / subtitle / author / institute（affiliation）/ event / date と、
`logo:`（画像。いくつでも）、`qr:`（URL。Octavo が QR コードの図を作る）を出す。
マスに入りきらない中身は、組んだあとに知らせる（`<octavo-overflow>` の印）。
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from .. import md as mdlib
from .. import qr as qrmod
from ..i18n import t, tag
from .base import Ctx
from .latex import check_assets, check_cjk
from .typst import TypstBackend, crossref_rules, font_expr, typst_escape, typst_string
from .typst_slides import TypstSlidesBackend

# 判型（mm、縦置きの幅×高さ）。b0 / b1 は日本の B 列（JIS）
SIZES = {'a0': (841, 1189), 'a1': (594, 841), 'a2': (420, 594),
         'b0': (1030, 1456), 'b1': (728, 1030)}
CUSTOM_SIZE = re.compile(r'(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)\s*(mm|cm|in)')
UNIT_MM = {'mm': 1.0, 'cm': 10.0, 'in': 25.4}


def paper_mm(size: str, orientation: str) -> tuple:
    """(幅, 高さ) を mm で。知らない判型なら ValueError。"""
    s = str(size).strip().lower()
    if s in SIZES:
        w, h = SIZES[s]
    else:
        m = CUSTOM_SIZE.fullmatch(s)
        if not m:
            raise ValueError(size)
        k = UNIT_MM[m.group(3)]
        w, h = float(m.group(1)) * k, float(m.group(2)) * k
    if orientation == 'landscape':
        w, h = max(w, h), min(w, h)
    else:
        w, h = min(w, h), max(w, h)
    return w, h


def grid_shape(value) -> tuple:
    """`2x3` / `[2, 3]` を (列, 行) に。"""
    if isinstance(value, (list, tuple)):
        parts = [str(x) for x in value]
    else:
        parts = re.split(r'\s*[x×,]\s*', str(value).strip())
    if len(parts) != 2 or not all(p.strip().isdigit() and int(p) > 0 for p in parts):
        raise ValueError(value)
    return int(parts[0]), int(parts[1])


def row_ratios(value, rows: int) -> list:
    """行の高さの比（`[1, 2, 1]`）。書いていなければ均等。"""
    if value in (None, '', []):
        return [1] * rows
    items = value if isinstance(value, (list, tuple)) else re.split(r'[\s,]+', str(value).strip())
    out = []
    for x in items:
        x = str(x).strip().removesuffix('fr')
        out.append(float(x))
    if len(out) != rows or any(v <= 0 for v in out):
        raise ValueError(value)
    return out


class TypstPosterBackend(TypstBackend):
    name = 'typst-poster'
    label = 'Typst poster'
    always_standalone = True
    wants_abstract_file = False
    places_bibliography = True       # 書誌はマスの1つにする（本文の後ろに足されると格子の外に出る）
    handout_layout = False           # 体裁は poster/typst-poster.typ
    select_mark = ('poster_select', 'on-poster', ('poster-only', 'only-poster'))

    def pandoc_args(self, ctx: Ctx) -> list:
        return ['-t', self.writer(ctx), '--wrap=preserve', '--top-level-division=section']

    # 図はスライドと同じく、マスの残りの高さに収める（幅いっぱいにするとマスからはみ出す）
    figure_box = 'height: 1fr'
    fmt_figure = TypstSlidesBackend.fmt_figure
    fmt_figure_note = TypstSlidesBackend.fmt_figure_note

    # -- 本文をマスに分ける ---------------------------------------------------
    def final_markdown(self, body: str, ctx: Ctx) -> str:
        # 頭のメタデータ（YAML）はマスではない。そのまま前に置く
        m = mdlib.FRONT_MATTER.match(body)
        head, body = (body[:m.end()], body[m.end():]) if m else ('', body)
        cells = poster_cells(body)
        problem = place_cells(cells, *ctx.poster_grid)
        if problem:
            from ..pandocrun import PandocError
            raise PandocError(problem)
        out = [head.rstrip('\n'), '```{=typst}\n#octavo-poster(\n```']
        for c in cells:
            args = [f'span: {c["span"]}', f'rows: {c["rows"]}',
                    'at: ' + (f'({c["at"][0]}, {c["at"][1]})' if c['at'] else 'none'),
                    f'name: {typst_string(c["name"])}']
            out.append('```{=typst}\noctavo-cell(' + ', '.join(args) + ')[\n```')
            out.append(c['text'])
            out.append('```{=typst}\n],\n```')
        out.append('```{=typst}\n)\n```')
        ctx.say(f'{tag("poster")} ' + t('{n} {n|cell|cells} in a {cols}×{rows} grid',
                                         n=len(cells), cols=ctx.poster_grid[0],
                                         rows=ctx.poster_grid[1]))
        return '\n\n'.join(out) + '\n'

    # -- 変換後 -------------------------------------------------------------
    def postprocess(self, typ: str, ctx: Ctx) -> str:
        body = super().postprocess(typ, ctx)
        return (f'// octavo build --to {self.name} が作った。手で直さない。\n'
                + self.meta_block(ctx) + '\n'
                + ctx.template('poster/typst-poster.typ').read_text(encoding='utf-8').rstrip()
                + '\n\n' + crossref_rules(ctx, 'none') + '\n' + body + '\n')

    def prepare(self, ctx: Ctx) -> None:
        """判型と格子を設定から読む（final_markdown と meta_block の前に1度）。"""
        cfg = ctx.cfg
        ctx.poster_paper = paper_mm(cfg['poster_size'], cfg['poster_orientation'])
        ctx.poster_grid = grid_shape(cfg['poster_grid'])
        ctx.poster_rows = row_ratios(cfg['poster_rows'], ctx.poster_grid[1])

    def meta_block(self, ctx: Ctx) -> str:
        cfg, meta = ctx.cfg, ctx.meta
        drop = set(cfg['anonymous_drop_meta'] or ()) if ctx.anonymous else set()
        sep = '、' if ctx.lang == 'ja' else ', '

        def content(*keys):
            for k in keys:
                v = meta.get(k) if k not in drop else None
                if isinstance(v, (list, tuple)):
                    v = sep.join(str(x) for x in v)
                if v not in (None, ''):
                    return '[' + typst_escape(str(v)).replace('[', '\\[').replace(']', '\\]') + ']'
            return 'none'

        src_dir = Path(ctx.document.src).parent if ctx.document is not None else cfg.root
        logos = meta.get('logo') or meta.get('logos') or []
        if isinstance(logos, str):
            logos = [logos]
        logo_paths = [typst_string(Path(os.path.relpath((src_dir / p).resolve(), ctx.out_dir)).as_posix())
                      for p in logos if 'logo' not in drop]
        qr_path = 'none'
        url = meta.get('qr')
        if url:
            name = f'{ctx.doc_name}-qr.svg'
            (ctx.out_dir / name).write_text(qrmod.svg(str(url)), encoding='utf-8')
            qr_path = typst_string(name)
        w, h = ctx.poster_paper
        cols, _rows = ctx.poster_grid
        acc = cfg['slides_accent']
        fields = [
            f'  title: {content("title")}', f'  subtitle: {content("subtitle")}',
            f'  author: {content("author")}', f'  institute: {content("institute", "affiliation")}',
            f'  event: {content("event")}', f'  date: {content("date")}',
            '  logos: (' + ''.join(p + ', ' for p in logo_paths) + ')',
            f'  qr: {qr_path}', f'  qr-label: {content("qr_label")}',
            f'  width: {w:g}', f'  height: {h:g}',
            f'  scale: {min(w, h) / 841:.4f}',
            f'  columns: {cols}',
            '  rows: (' + ''.join(f'{r:g}fr, ' for r in ctx.poster_rows) + ')',
            '  accent: ' + (f'rgb("{acc}")' if acc else 'none'),
            f'  lang: "{ctx.lang}"',
            '  font: ' + font_expr(ctx.lang, 'sans', cfg['poster_font']),
        ]
        return '#let octavo = (\n' + ',\n'.join(fields) + ',\n)\n'

    def check(self, typ: str, ctx: Ctx) -> None:
        check_assets(ctx, tables=re.findall(r'(?<![\w-])#?include "[^"]*?/?([\w.-]+)\.typ"', typ),
                     figures=re.findall(r'image\("[^"]*?/?([\w.-]+\.(?:png|pdf|svg|jpe?g))"', typ),
                     refs=re.findall(r'image\("([^"]+)"', typ))
        check_cjk(typ, ctx, '.typ',
                  t('the CJK font in poster_font must be installed (check with: typst fonts)'),
                  templates=[ctx.template('poster/typst-poster.typ'),
                             ctx.template('typst/crossref.typ')])

    def after_compile(self, ctx: Ctx, typ: Path) -> None:
        """組んだあと、マスに入りきらなかった中身を知らせる。"""
        from .. import extract
        try:
            over = extract._marks(typ, self.root_arg(ctx), 'octavo-overflow')
        except Exception:                                     # 印を読めない古い typst など
            return
        for o in over:
            ctx.say(f'{tag("poster")} ' + t(
                'the cell {name} overflows by about {mm} mm — shorten it, make the cell bigger '
                '(span=, rows=, poster_rows) or the text smaller',
                name=o.get('name') or '?', mm=f'{float(o.get("over", 0)):.0f}'))


def place_cells(cells: list, cols: int, rows: int) -> str:
    """マスの場所を決める（c['at'] を (列, 行)、1 から）。入りきらなければその説明を返す。

    場所を指定したマス（cell=）を先に置き、残りを左上から順に、結合の大きさが入る最初の
    空きへ置く。Typst の格子は結合したマスを次の行へ送らずに止まるので、ここで全部決める。
    """
    used = [[False] * cols for _ in range(rows)]

    def fits(x, y, c):
        if x + c['span'] > cols or y + c['rows'] > rows:
            return False
        return not any(used[yy][xx] for yy in range(y, y + c['rows'])
                       for xx in range(x, x + c['span']))

    def take(x, y, c):
        for yy in range(y, y + c['rows']):
            for xx in range(x, x + c['span']):
                used[yy][xx] = True
        c['at'] = (x + 1, y + 1)

    for c in [c for c in cells if c['at']]:
        x, y = c['at'][0] - 1, c['at'][1] - 1
        if not fits(x, y, c):
            return t('the cell {name} does not fit at {at} in the {cols}×{rows} grid (it is outside '
                     'the grid or on top of another cell)', name=c['name'] or '-',
                     at=f'{x + 1},{y + 1}', cols=cols, rows=rows)
        take(x, y, c)
    for c in [c for c in cells if not c['at']]:
        spot = next(((x, y) for y in range(rows) for x in range(cols) if fits(x, y, c)), None)
        if spot is None:
            return t('the cell {name} has no room left in the {cols}×{rows} grid — make the grid '
                     'bigger (poster_grid) or join fewer cells', name=c['name'] or '-',
                     cols=cols, rows=rows)
        take(*spot, c)
    return ''


def poster_cells(body: str) -> list:
    """本文を一番上の段の見出しごとのマスに分ける。最初の見出しより前の文は1つのマスにする。"""
    from .. import crossref as xref
    lines = body.split('\n')
    # コードブロックの中の `#` はマスの見出しではない（行の数は変えずに伏せる）
    masked, fence = [], None
    for line in lines:
        f = mdlib.FENCE_LINE.match(line)
        if f:
            fence = None if fence == f.group(1) else (fence or f.group(1))
            masked.append('')
        else:
            masked.append('' if fence else line)
    levels = [len(m.group(1)) for m in (re.match(r'^(#{1,6})[ \t]+\S', l) for l in masked) if m]
    top = min(levels) if levels else 1
    cells, cur = [], None
    for i, line in enumerate(lines):
        m = re.match(rf'^#{{{top}}}[ \t]+(?P<title>.*?)[ \t]*(?:\{{(?P<attr>[^}}]*)\}})?[ \t]*$',
                     masked[i])
        if m:
            attr = m.group('attr') or ''
            cur = {'name': m.group('title'), 'span': 1, 'rows': 1, 'at': None, 'lines': [line]}
            for k in ('span', 'rows'):
                v = xref.attr_value(attr, k)
                if v and v.isdigit() and int(v) > 0:
                    cur[k] = int(v)
            at = xref.attr_value(attr, 'cell')
            if at:
                parts = re.split(r'\s*[,x]\s*', at.strip())
                if len(parts) == 2 and all(p.isdigit() and int(p) > 0 for p in parts):
                    cur['at'] = (int(parts[0]), int(parts[1]))
            cells.append(cur)
        elif cur is None:
            if line.strip():
                cur = {'name': '', 'span': 1, 'rows': 1, 'at': None, 'lines': [line]}
                cells.append(cur)
        else:
            cur['lines'].append(line)
    for c in cells:
        c['text'] = '\n'.join(c.pop('lines')).strip('\n')
    # 見出しのない、コメントだけの頭（見本の説明など）はマスにしない
    return [c for c in cells if c['name'] or mdlib.strip_comments(c['text']).strip()]
