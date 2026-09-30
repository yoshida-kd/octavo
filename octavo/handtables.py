"""手で作る表（`tables/<name>.csv`）を `assets/tables/<name>.typ` / `.tex` / `.md` にする。

分析の表（ov_table）と同じ置き場・同じ形のファイルを書くので、原稿は `: 表題 {#tbl-<name>}`
の1行を置くだけ。番号・参照・Word・`octavo check` はそのまま効く。CSV なのは、拡張機能の
表の画面でも Excel でも編集できるから。設定は持たず、中身から決める:

- 1行目が見出し。見出しの中身のあるセルの右隣が空なら、そのセルを横に広げる（結合）。
  Excel で結合したセルを CSV に保存すると、ちょうどこの形になる。1行目に結合があれば
  2行目も見出しにし、2行目が空の列は1行目の見出しを2行目に下ろす
- 数字だけの列は右揃え、それ以外は左揃え
- 長い文章の列は幅を広げて折り返し（比較表）、短い列は中身の幅
- 文字コードは UTF-8（BOM があってもよい）。読めなければ Shift_JIS（日本語版の Excel）

組み直すのは、書いたファイルがないか CSV より古いときだけ。同じ名前の表を分析も書いて
いたら（`ov_table` の印がある）止める — どちらが組まれるかが実行の順で変わるため。
"""
from __future__ import annotations

import csv
import io
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from .i18n import t, tag

FORMATS = ('.typ', '.tex', '.md')
MADE_BY = 'octavo build'          # 書いたファイルの1行目に入る（自分のものか見分ける）
LONG = 30                         # これより幅のあるセルを持つ列は「長い文章の列」
NUMBER = re.compile(r'[(\[]?[-+−–]?[\d,]*\.?\d+(?:[eE][-+]?\d+)?[%％]?[)\]]?\**[a-z†‡]*')
BLANKISH = {'', '-', '–', '—', '―', '.', '…'}


class TableError(Exception):
    pass


@dataclass
class Table:
    rows: list                          # 文字列の行（列の数はそろえてある）
    head: int = 1                       # 見出しの行数（1 か 2）
    spans: dict = field(default_factory=dict)   # 見出し1行目: 列 -> 横に広がる列数
    align: list = field(default_factory=list)   # 列ごとの 'l' / 'r'
    long: list = field(default_factory=list)    # 列ごとに、長い文章の列か

    @property
    def ncols(self) -> int:
        return len(self.rows[0]) if self.rows else 0


# ---------------------------------------------------------------- 読む

def read_text(path: Path) -> tuple:
    """(文字列, 使った文字コード)。UTF-8 で読めなければ Shift_JIS（cp932）で読む。"""
    data = path.read_bytes()
    try:
        return data.decode('utf-8-sig'), 'utf-8'
    except UnicodeDecodeError:
        pass
    try:
        return data.decode('cp932'), 'shift_jis'
    except UnicodeDecodeError:
        raise TableError(t('{file} is neither UTF-8 nor Shift_JIS — save it as UTF-8 CSV',
                           file=path.name)) from None


def _width(s: str) -> int:
    return sum(2 if unicodedata.east_asian_width(c) in 'WF' else 1 for c in s)


def _numeric(s: str) -> bool:
    return bool(NUMBER.fullmatch(s.replace(' ', '')))


def parse(text: str) -> Table:
    rows = [[c.strip() for c in r] for r in csv.reader(io.StringIO(text))]
    while rows and not any(rows[-1]):           # 末尾の空行
        rows.pop()
    rows = [r for r in rows if r]
    if not rows:
        raise TableError(t('the table is empty'))
    n = max(len(r) for r in rows)
    rows = [r + [''] * (n - len(r)) for r in rows]
    while n > 1 and not any(r[n - 1] for r in rows):     # 右端の空の列
        rows = [r[:-1] for r in rows]
        n -= 1

    tb = Table(rows=rows)
    top = rows[0]
    j = 0
    while j < n:
        k = j + 1
        if top[j]:
            while k < n and not top[k]:
                k += 1
            if k - j > 1:
                tb.spans[j] = k - j
        j = k
    if tb.spans and len(rows) > 2:
        tb.head = 2
        # 結合していない見出しの下が空なら、見出しを2行目に下ろす（縦の結合の代わり）
        spanned = {c for j, w in tb.spans.items() for c in range(j, j + w)}
        for c in range(n):
            if c not in spanned and top[c] and not rows[1][c]:
                rows[1][c], top[c] = top[c], ''

    body = rows[tb.head:]
    for c in range(n):
        cells = [r[c] for r in body if r[c] not in BLANKISH]
        tb.align.append('r' if cells and all(_numeric(x) for x in cells) else 'l')
        tb.long.append(max((_width(line) for r in body for line in r[c].splitlines()),
                           default=0) > LONG)
    return tb


# ---------------------------------------------------------------- 書く

def _typ_str(s: str) -> str:
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'


def to_typst(tb: Table, source: str) -> str:
    cols = ', '.join('1fr' if lg else 'auto' for lg in tb.long)
    aligns = ', '.join('right' if a == 'r' else 'left' for a in tb.align)
    out = [f'// {MADE_BY} が {source} から作ったファイル。手で直さない（{source} を直す）。',
           '#table(', f'  columns: ({cols},),', f'  align: ({aligns},),',
           '  stroke: none,', '  table.hline(),']
    for i, row in enumerate(tb.rows[:tb.head]):
        cells = []
        c = 0
        while c < tb.ncols:
            w = tb.spans.get(c, 1) if i == 0 else 1
            txt = f'strong({_typ_str(row[c])})' if row[c] else '[]'
            if w > 1:
                cells.append(f'table.cell(colspan: {w}, align: center, {txt})')
            else:
                cells.append(txt)
            c += w
        out.append('  ' + ', '.join(cells) + ',')
        if i == 0 and tb.head == 2:
            out += [f'  table.hline(start: {j}, end: {j + w}, stroke: 0.5pt),'
                    for j, w in sorted(tb.spans.items())]
    out.append('  table.hline(stroke: 0.5pt),')
    for row in tb.rows[tb.head:]:
        out.append('  ' + ', '.join(_typ_str(x) for x in row) + ',')
    out += ['  table.hline(),', ')', '']
    return '\n'.join(out)


def _tex_escape(s: str) -> str:
    for a, b in (('\\', '\x00'), ('&', r'\&'), ('%', r'\%'), ('$', r'\$'),
                 ('#', r'\#'), ('_', r'\_'), ('{', r'\{'), ('}', r'\}'),
                 ('~', r'\textasciitilde{}'), ('^', r'\textasciicircum{}')):
        s = s.replace(a, b)
    return s.replace('\x00', r'\textbackslash{}')


def to_latex(tb: Table, source: str) -> str:
    nlong = sum(tb.long)
    # 長い文章の列は p{} で折り返す（短い列の分を残して、行の幅を分け合う）
    width = f'{0.8 / nlong:.2f}' if nlong else ''
    spec = ''.join(f'p{{{width}\\linewidth}}' if lg else a for a, lg in zip(tb.align, tb.long))

    def cell(s: str, c: int) -> str:
        sep = r'\newline ' if tb.long[c] else ' '
        return sep.join(_tex_escape(x) for x in s.splitlines())

    out = [f'% {MADE_BY} が {source} から作ったファイル。手で直さない（{source} を直す）。',
           f'\\begin{{tabular}}{{{spec}}}', r'\toprule']
    for i, row in enumerate(tb.rows[:tb.head]):
        cells = []
        c = 0
        while c < tb.ncols:
            w = tb.spans.get(c, 1) if i == 0 else 1
            txt = f'\\textbf{{{cell(row[c], c)}}}' if row[c] else ''
            cells.append(f'\\multicolumn{{{w}}}{{c}}{{{txt}}}' if w > 1 else txt)
            c += w
        out.append(' & '.join(cells) + r' \\')
        if i == 0 and tb.head == 2:
            out.append(' '.join(f'\\cmidrule(lr){{{j + 1}-{j + w}}}'
                                for j, w in sorted(tb.spans.items())))
    out.append(r'\midrule')
    for row in tb.rows[tb.head:]:
        out.append(' & '.join(cell(x, c) for c, x in enumerate(row)) + r' \\')
    out += [r'\bottomrule', r'\end{tabular}', '']
    return '\n'.join(out)


def _md_escape(s: str) -> str:
    """セルは文字どおり（Typst・LaTeX と同じ）。@ を引用に、* を強調にさせない。"""
    s = re.sub(r'([\\`*_\[\]<>@$~^#|])', r'\\\1', s)
    return s.replace('\n', ' ')


def to_markdown(tb: Table, source: str) -> str:
    """Word 用のパイプ表。結合はできないので、2行の見出しは「上 下」と1つにまとめる。"""
    head = list(tb.rows[0])
    if tb.head == 2:
        group = [''] * tb.ncols
        for j, w in tb.spans.items():
            for c in range(j, j + w):
                group[c] = tb.rows[0][j]
        head = [' '.join(x for x in (g, s) if x)
                for g, s in zip(group, tb.rows[1])]

    def row(cells) -> str:
        return '| ' + ' | '.join(_md_escape(x) for x in cells) + ' |'

    rule = '|' + '|'.join('---:' if a == 'r' else ':---' for a in tb.align) + '|'
    out = [f'<!-- {MADE_BY} が {source} から作ったファイル。手で直さない（{source} を直す）。 -->',
           '', row(head), rule] + [row(r) for r in tb.rows[tb.head:]] + ['']
    return '\n'.join(out)


WRITERS = {'.typ': to_typst, '.tex': to_latex, '.md': to_markdown}


# ---------------------------------------------------------------- 組む

def sources(cfg) -> list:
    """`tables/*.csv`（`_` や `.` で始まるものは除く）。"""
    folder = Path(cfg['table_src_dir'])
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.glob('*.csv') if not p.name.startswith(('_', '.')))


def watch_paths(cfg) -> list:
    return sources(cfg)


def outputs(cfg, src: Path) -> list:
    out = Path(cfg['table_dir'])
    return [out / f'{src.stem}{ext}' for ext in FORMATS]


def stale(cfg) -> list:
    out = []
    for src in sources(cfg):
        m = src.stat().st_mtime
        if any(not o.exists() or o.stat().st_mtime < m for o in outputs(cfg, src)):
            out.append(src)
    return out


def _foreign(path: Path) -> bool:
    """分析（ov_table）が書いた表か。octavo init の仮の表は上書きしてよい。"""
    try:
        first = path.read_text(encoding='utf-8').split('\n', 1)[0]
    except (OSError, UnicodeDecodeError):
        return False
    return MADE_BY not in first and 'octavo:placeholder' not in first


def conflicts(cfg) -> list:
    """同じ名前の表を分析も書いている CSV。"""
    return [src for src in sources(cfg)
            if any(o.exists() and _foreign(o) for o in outputs(cfg, src))]


def run(cfg, report: list, force: bool = False) -> bool:
    """古い表を書く。False なら失敗した（変換に進まない）。"""
    clash = conflicts(cfg)
    if clash:
        for src in clash:
            report.append(tag('table') + ' ' + t(
                '{file} and the analysis both make the table {name} — rename one of them',
                file=cfg.rel(src), name=src.stem))
        return False
    for src in (sources(cfg) if force else stale(cfg)):
        try:
            text, enc = read_text(src)
            tb = parse(text)
        except (TableError, csv.Error) as e:
            report.append(tag('table') + ' ' + t('could not read {file}: {why}',
                                                 file=cfg.rel(src), why=str(e)))
            return False
        rel = cfg.rel(src)
        for dest in outputs(cfg, src):
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(WRITERS[dest.suffix](tb, rel), encoding='utf-8')
        note = ' ' + t('(read as Shift_JIS)') if enc == 'shift_jis' else ''
        report.append(tag('table') + ' ' + t('made {file} -> .typ, .tex, .md', file=rel) + note)
    return True
