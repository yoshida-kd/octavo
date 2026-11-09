# =====================================================================
#  Octavo — hands numbers, figures and tables from the analysis (.qmd) to the paper (.md)
#  (the Python version).
#
#  It keeps the same promises as analysis/octavo.R and writes the same files in the same
#  form, so nothing changes on the manuscript's side.
#
#  Usage (load it in the first chunk of the .qmd):
#
#      import os, sys
#      root = os.environ.get("OCTAVO_ROOT")
#      sys.path.insert(0, os.path.join(root, "analysis") if root else ".")
#      from octavo_helper import *
#
#  Then, in the analysis:
#
#      ov_value("n_obs", len(d))                 -> {{n_obs}} in the text
#      ov_value("coef_x", model.params["x"])     -> {{coef_x}} in the text
#      ov_value("p_x", ov_pval(model.pvalues["x"]))
#      ov_figure(fig, "trend")                   -> assets/figures/trend.{pdf,png}
#      ov_table(df, "summary")                   -> assets/tables/summary.{tex,typ,md}
#      ov_palette(3) / ov_tint(col)              colourblind-safe colours
#
#  Numbers collect in assets/values/<name of this .qmd>.json. octavo build reads them into
#  the {{...}} of the text. A figure goes in with ![Trend](../../assets/figures/trend.png){#fig-trend}
#  in the manuscript, and a table with the line `: Summary {#tbl-summary}` where it belongs.
#  Captions and numbers belong to the manuscript (refer to them with @fig-trend / @tbl-summary).
#
#  **Integers and decimals are kept apart.** A Python int (len() and so on) shows with a
#  thousands separator, "1,523"; a float (a coefficient, say) shows with 3 digits by default,
#  "0.342". NumPy's integers and floats are treated the same. To fix the format, use
#  ov_value(..., fmt=".2f") or write {{coef_x:.2f}} in the text.
#
#  It runs on the standard library alone. matplotlib / plotnine are needed only when you pass
#  a figure, pandas only when you pass a DataFrame as a table (lists and dicts work too).
#  LaTeX tables use booktabs (\toprule and so on). Typst tables use table.hline(), so
#  Typst 0.11 or later.
# =====================================================================
from __future__ import annotations

import datetime
import json
import math
import os
import platform
import sys
from pathlib import Path

__all__ = ['ov_root', 'ov_dir', 'ov_value', 'ov_values', 'ov_pval', 'ov_figure',
           'ov_table', 'ov_palette', 'ov_tint', 'ov_style', 'ov_cud']


# ---------------------------------------------------------------- locations

def ov_root() -> Path:
    """The project's root. octavo passes it in OCTAVO_ROOT; rendered directly, it looks upwards."""
    e = os.environ.get('OCTAVO_ROOT')
    if e and os.path.isdir(e):
        return Path(e).resolve()
    d = Path.cwd().resolve()
    for p in (d, *d.parents):
        if (p / 'octavo.config.py').exists():
            return p
    return d


def ov_dir(kind: str = 'values') -> Path:
    """Where to write. octavo passes it in environment variables (values_dir in octavo.config.py
    and so on). When Quarto renders directly, it is under the default place, assets/."""
    env = {'values': 'OCTAVO_VALUES_DIR', 'figures': 'OCTAVO_FIGURE_DIR',
           'tables': 'OCTAVO_TABLE_DIR'}
    if kind not in env:
        raise ValueError(f'ov_dir: kind must be one of {" / ".join(env)} ({kind!r})')
    p = os.environ.get(env[kind])
    d = Path(p) if p else ov_root() / 'assets' / kind
    d.mkdir(parents=True, exist_ok=True)
    return d


def _values_file() -> Path | None:
    """Where values go: by default a .json named after this .qmd. Each .qmd has its own file, so
    analyses do not compete for one.

    Run outside Quarto (a single cell), there is no telling which .qmd this is, so it returns
    None and no value is written. Written to a file of another name, a trial value would sit
    beside the real one under the same name and could reach the text."""
    name = os.environ.get('OCTAVO_VALUES_NAME')
    if not name:
        doc = os.environ.get('QUARTO_DOCUMENT_FILE')  # Quarto passes the .qmd's file name
        if not doc:
            return None
        name = Path(doc).stem
    return ov_dir('values') / f'{name}.json'


def _write(path: Path, text: str) -> Path:
    # UTF-8 without a BOM, \n for newlines (on Windows too)
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    return path


# ---------------------------------------------------------------- numbers

_store: dict = {}


def _scalar(x, name: str):
    """One value JSON can hold. Integers stay int and decimals float (the difference matters)."""
    if x is None or type(x).__name__ in ('NAType', 'NaTType'):     # pandas' missing values too
        return 'NA'
    if isinstance(x, (str, bool, int, float)):
        pass
    elif hasattr(x, 'item') and getattr(x, 'size', 1) == 1:   # a NumPy scalar or one-element array
        return _scalar(x.item(), name)
    elif hasattr(x, '__len__'):
        n = len(x)
        if n != 1:
            raise ValueError(f'ov_value: pass exactly one value ({name} has length {n})')
        return _scalar(x.iloc[0] if hasattr(x, 'iloc') else list(x)[0], name)
    elif isinstance(x, (datetime.date, datetime.datetime)):
        return x.isoformat()
    else:
        try:                                                    # Decimal and so on
            return float(x)
        except (TypeError, ValueError):
            return str(x)
    if isinstance(x, float) and not math.isfinite(x):
        return 'NA' if math.isnan(x) else str(x)                # inf as a string
    return x


def ov_value(name: str, x, fmt: str | None = None, note: str | None = None):
    """Record one number for the text of the paper.

    name  the name written {{name}} in the text (a letter or _, then letters, digits, _ and .)
    x     the value (length 1): an integer, a decimal or a string
    fmt   a Python format (".3f" and so on). Left out, Octavo's default
    note  a memo, shown by octavo check values
    """
    import re
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]*', name):
        raise ValueError(f'ov_value: name must start with a letter or _ and use only letters, digits, _ and . ({name!r})')
    v = _scalar(x, name)
    path = _values_file()
    if path is None:
        print(f'ov_value: {name} = {v} (not recorded: this cell was run on its own; render the '
              f'.qmd to record it)')
        return x
    store = _store.setdefault(str(path), {})
    item: dict = {'value': v}
    if fmt is not None:
        item['fmt'] = fmt
    if note is not None:
        item['note'] = note
    store[name] = item
    _write_values(path, store)
    return x


def ov_values(**kw):
    """Record several at once: ov_values(n_obs=len(d), mean_x=d.x.mean())"""
    for k, v in kw.items():
        ov_value(k, v)
    return kw


def _session() -> dict:
    """A record for reproducibility: what this ran on, kept in the values file (Octavo does not
    treat keys starting with `_` as values). Only the packages that were loaded are listed."""
    pkgs: dict = {}
    try:
        from importlib import metadata
        # packages_distributions came in 3.10. Before that, take the import name as the distribution name
        owner = getattr(metadata, 'packages_distributions', lambda: {})()
        for top in {m.split('.')[0] for m in list(sys.modules)}:
            for dist in owner.get(top, (top,)):
                try:
                    pkgs.setdefault(dist, metadata.version(dist))
                except metadata.PackageNotFoundError:
                    pass
    except Exception:           # Failing to record must not stop the analysis
        pass
    return {'engine': 'Python', 'version': platform.python_version(),
            'platform': platform.platform(),
            'at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'packages': dict(sorted(pkgs.items()))}


def _write_values(path: Path, store: dict) -> None:
    doc = {'_generated': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
           '_session': _session(), **store}
    _write(path, json.dumps(doc, ensure_ascii=False, indent=1) + '\n')


def ov_pval(p, digits: int = 3) -> str:
    """The usual way to write a p value. Below 0.001 it is "< .001"."""
    p = _scalar(p, 'p')
    if not isinstance(p, (int, float)) or isinstance(p, bool) or math.isnan(p):
        return 'NA'
    cut = 10.0 ** -digits
    if p < cut:
        return '< ' + f'{cut:.{digits}f}'.lstrip('0')
    return f'{p:.{digits}f}'.lstrip('0')


# ---------------------------------------------------------------- colours
# Colours that stay distinct for people with colour-vision differences: the 8 colours of
# Okabe & Ito (2008). The rules for making a figure:
#   1. Choose colours from here
#   2. Do not tell things apart by colour alone (write values or names in the figure; emphasise
#      with bold, line type or position as well)
#   3. Give neighbouring areas different lightness too. Lighten an area that carries text with ov_tint()
#   4. Do not put red next to green, or yellow next to white

ov_cud = {'blue': '#0072B2', 'orange': '#E69F00', 'green': '#009E73',
          'vermillion': '#D55E00', 'skyblue': '#56B4E9', 'purple': '#CC79A7',
          'yellow': '#F0E442', 'grey': '#999999', 'black': '#000000'}
_ORDER = ('blue', 'orange', 'green', 'vermillion', 'skyblue', 'purple', 'yellow', 'grey')


def ov_palette(n=None):
    """The colours. Given n, that many (most distinct first); given names, those colours.

        ov_palette(3)                    # blue, orange, green
        ov_palette(["blue", "grey"])
    """
    if n is None:
        return [ov_cud[k] for k in _ORDER]
    if isinstance(n, str):
        n = [n]
    if isinstance(n, (list, tuple)):
        bad = [k for k in n if k not in ov_cud]
        if bad:
            raise ValueError(f'ov_palette: unknown colour {", ".join(bad)} ({" / ".join(ov_cud)})')
        return [ov_cud[k] for k in n]
    if n > len(_ORDER):
        raise ValueError(f'ov_palette: at most {len(_ORDER)} colours (beyond that, tell things apart '
                         'by line type, shape or direct labels)')
    return [ov_cud[k] for k in _ORDER[:n]]


def ov_tint(col, p: float = 0.6):
    """Lighten a colour (p = 0 leaves it, 1 makes it white), for an area that carries black text.
    The colour is "#RRGGBB" or one of the names. Given a list, it returns a list."""
    if isinstance(col, (list, tuple)):
        return [ov_tint(c, p) for c in col]
    h = ov_cud.get(col, col).lstrip('#')
    rgb = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    return '#' + ''.join(f'{round(c + (255 - c) * p):02X}' for c in rgb)


# ---------------------------------------------------------------- figures

# Fonts for Japanese in figures (in the order of Octavo's defaults; the first one installed is used)
_CJK_FONTS = ('BIZ UDGothic', 'Noto Sans CJK JP', 'Hiragino Sans', 'Hiragino Kaku Gothic ProN',
              'Yu Gothic', 'IPAexGothic', 'TakaoPGothic', 'VL Gothic')


def ov_style() -> None:
    """Set matplotlib's defaults. PDFs keep text as text (it can be searched and selected), and a
    Japanese font is used if there is one. ov_figure() calls this too, but call it **before**
    making a figure for it to reach that figure's text (in the first chunk of the .qmd).
    Without matplotlib it does nothing."""
    try:
        import matplotlib as mpl
        from matplotlib import font_manager
    except ImportError:
        return
    mpl.rcParams['pdf.fonttype'] = 42
    mpl.rcParams['axes.unicode_minus'] = False
    have = {f.name for f in font_manager.fontManager.ttflist}
    ja = [f for f in _CJK_FONTS if f in have]
    if ja:
        mpl.rcParams['font.sans-serif'] = ja + [
            f for f in mpl.rcParams['font.sans-serif'] if f not in ja]
        mpl.rcParams['font.family'] = 'sans-serif'


def ov_figure(x, name: str, width: float | None = None, height: float | None = None,
              dpi: int = 300, formats=('pdf', 'png')):
    """Save a figure in assets/figures/. By default it writes both .pdf (for Typst and LaTeX) and
    .png (for Word), so figure_ext in octavo.config.py works as it is.

    x       a matplotlib Figure, a plotnine ggplot, or a function that draws
            (on matplotlib.pyplot; a new figure is made before calling it)
    name    the file name, no extension. Match ![](assets/figures/<name>.png) in the manuscript
    width / height  inches. Left out, the Figure's size (6 x 4 for a function or a ggplot)
    """
    ov_style()
    d = ov_dir('figures')
    out = []
    closer = None
    if callable(x) and not hasattr(x, 'savefig') and not hasattr(x, 'save'):
        import matplotlib.pyplot as plt
        fig = plt.figure(figsize=(width or 6, height or 4))
        x()
        x, closer = fig, plt.close
    for fmt in formats:
        path = d / f'{name}.{fmt}'
        if hasattr(x, 'savefig'):                       # a matplotlib Figure
            if width or height:
                w0, h0 = x.get_size_inches()
                x.set_size_inches(width or w0, height or h0)
            x.savefig(path, dpi=dpi, format=fmt)
        elif hasattr(x, 'save'):                        # a plotnine ggplot
            x.save(str(path), width=width or 6, height=height or 4, dpi=dpi, verbose=False)
        else:
            raise TypeError('ov_figure: pass a matplotlib Figure, a plotnine ggplot, '
                            f'or a function that draws ({type(x).__name__})')
        out.append(path)
    if closer:
        closer(x)
    return out


# ---------------------------------------------------------------- tables

def _tex_escape(s: str) -> str:
    s = s.replace('\\', '\u0001')                       # move it out of the way first (so its braces are not escaped twice)
    for ch in '&%$#_{}':
        s = s.replace(ch, '\\' + ch)
    s = s.replace('~', '\\textasciitilde{}').replace('^', '\\textasciicircum{}')
    return s.replace('\u0001', '\\textbackslash{}')


def _typ_escape(s: str) -> str:
    s = s.replace('\\', '\\\\')
    for ch in '#$@[]<>*_':
        s = s.replace(ch, '\\' + ch)
    return s


def _missing(v) -> bool:
    if v is None:
        return True
    if isinstance(v, float) and math.isnan(v):
        return True
    return type(v).__name__ in ('NAType', 'NaTType')    # pandas' missing values


def _plain(v):
    return v.item() if hasattr(v, 'item') and getattr(v, 'size', 1) == 1 else v


def _columns(x):
    """The table's input as (headings, a list of values per column). A DataFrame, a dict (column
    name: list of values), a list of dicts (rows) or a list of lists (the first is the headings)."""
    if hasattr(x, 'columns') and hasattr(x, 'to_dict'):             # DataFrame
        heads = [str(c) for c in x.columns]
        return heads, [[_plain(v) for v in x.iloc[:, i].tolist()] for i in range(len(heads))]
    if isinstance(x, dict):
        heads = [str(k) for k in x]
        return heads, [[_plain(v) for v in x[k]] for k in x]
    rows = list(x)
    if rows and isinstance(rows[0], dict):
        heads = [str(k) for k in rows[0]]
        return heads, [[_plain(r.get(h)) for r in rows] for h in rows[0]]
    if rows and isinstance(rows[0], (list, tuple)):
        heads = [str(c) for c in rows[0]]
        return heads, [[_plain(r[i]) if i < len(r) else None for r in rows[1:]]
                       for i in range(len(heads))]
    raise TypeError('ov_table: pass a DataFrame, a dict (column name: list of values), a list of dicts, '
                    'or a list of lists whose first row is the headings')


def _cells(cols, digits):
    out = []
    for col in cols:
        cell = []
        for v in col:
            if _missing(v):
                cell.append('')
            elif isinstance(v, float):
                cell.append(f'{v:.{digits}f}')               # decimals to digits places
            else:
                cell.append(str(v))
        out.append(cell)
    return [list(r) for r in zip(*out)] if out else []


def _align(cols, align):
    if align:
        return list(align)
    def number(col):
        vals = [v for v in col if not _missing(v)]
        return bool(vals) and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                                  for v in vals)
    return ['r' if number(c) else 'l' for c in cols]


def _plan(n, groups, indent):
    """For each row, (its group heading or None, whether to indent). groups is {heading: first row, from 0}."""
    head = [None] * n
    for label, at in (groups or {}).items():
        if not isinstance(at, int) or isinstance(at, bool) or not 0 <= at < n:
            raise ValueError(f'ov_table: rows in groups must be from 0 to {n - 1} ({label}: {at}). '
                             'The heading goes before that row')
        head[at] = str(label)
    first = min((a for a in (groups or {}).values()), default=n)
    use = bool(groups) if indent is None else bool(indent)
    return [(head[i], use and i >= first) for i in range(n)]


def _tex_table(heads, rows, align, notes, plan, size):
    n = len(heads)
    head = ' & '.join('\\textbf{' + _tex_escape(h) + '}' if h else '' for h in heads)
    lines = []
    for r, (grp, ind) in zip(rows, plan):
        if grp:
            lines.append(f'\\multicolumn{{{n}}}{{l}}{{\\textbf{{{_tex_escape(grp)}}}}} \\\\')
        cells = [_tex_escape(c) for c in r]
        if ind and cells:
            cells[0] = '\\hspace{1em}' + cells[0]
        lines.append(' & '.join(cells) + ' \\\\')
    tab = ('\\begin{tabular}{' + ''.join(align) + '}\n\\toprule\n' + head + ' \\\\\n\\midrule\n'
           + ''.join(l + '\n' for l in lines) + '\\bottomrule\n\\end{tabular}\n')
    if size:
        tab = f'{{\\fontsize{{{size}}}{{{round(size * 1.2, 2)}}}\\selectfont\n' + tab + '}\n'
    return ('% Written by ov_table() in octavo_helper.py. Do not edit by hand.\n' + tab
            + (f'\\par\\vspace{{2pt}}\n{{\\footnotesize {_tex_escape(notes)}}}\n' if notes else ''))


def _typ_table(heads, rows, align, notes, plan, size):
    word = {'l': 'left', 'r': 'right', 'c': 'center'}
    n = len(heads)
    # A column with no heading (the row names) gets []. Typst warns about [**]
    head = ', '.join('[*' + _typ_escape(h) + '*]' if h else '[]' for h in heads)
    lines = []
    for r, (grp, ind) in zip(rows, plan):
        if grp:
            lines.append(f'  table.cell(colspan: {n}, align: left)[*{_typ_escape(grp)}*],')
        cells = ['[' + _typ_escape(c) + ']' for c in r]
        if ind and cells:
            cells[0] = '[#h(1em)' + cells[0][1:]
        lines.append('  ' + ', '.join(cells) + ',')
    note_size = round(size * 0.85, 2) if size else 8
    # Keep the text's justification out of the cells. The type size is size (pt)
    return ('// Written by ov_table() in octavo_helper.py. Do not edit by hand.\n'
            '#set par(justify: false)\n'
            + (f'#set text(size: {size}pt)\n' if size else '')
            + '#table(\n'
            f'  columns: {n},\n'
            f'  align: ({", ".join(word[a] for a in align)}),\n'
            '  stroke: none,\n  table.hline(),\n'
            f'  {head},\n  table.hline(stroke: 0.5pt),\n'
            + ''.join(l + '\n' for l in lines) + '  table.hline(),\n)\n'
            + (f'#v(2pt)\n#block(width: 100%, align(left, text(size: {note_size}pt)[{_typ_escape(notes)}]))\n'
               if notes else ''))


def _md_table(heads, rows, align, notes, plan, size):
    esc = lambda v: v.replace('|', '\\|')
    rule = {'l': ':---', 'r': '---:', 'c': ':---:'}
    row = lambda v: '| ' + ' | '.join(esc(c) for c in v) + ' |'
    lines = []
    for r, (grp, ind) in zip(rows, plan):
        # A Markdown table cannot span columns, so a group heading is a row with the heading in bold in the first column
        if grp:
            lines.append(row([f'**{grp}**'] + [''] * (len(heads) - 1)))
        r = list(r)
        if ind and r:
            r[0] = '\u00a0\u00a0' + r[0]
        lines.append(row(r))
    return ('<!-- Written by ov_table() in octavo_helper.py. Do not edit by hand. -->\n\n'
            + row(heads) + '\n|' + '|'.join(rule[a] for a in align) + '|\n'
            + '\n'.join(lines) + '\n'
            + (f'\n*{notes}*\n' if notes else ''))


_RENDER = {'tex': _tex_table, 'typ': _typ_table, 'md': _md_table}


def ov_table(x, name: str, notes: str | None = None, align: str | None = None,
             digits: int = 3, formats=('tex', 'typ', 'md'),
             groups: dict | None = None, indent: bool | None = None, size: float | None = None):
    """Save a table in assets/tables/ (.tex, .typ and .md, read by LaTeX, Typst and Word).
    Write the line `: Caption {#tbl-<name>}` in the text and Octavo puts it there, and
    @tbl-<name> refers to it. The caption belongs to the text (none is added here).

    x       a DataFrame, a dict (column name: list of values), a list of dicts, or a list of
            lists whose first row is the headings. Or {"tex": "...", "typ": "...", "md": "..."}
            (for strings made by statsmodels' as_latex() and the like, passed as they are)
    name    the file name, no extension
    notes   a note in small type under the table (left-aligned)
    align   the alignment of each column, like "lrrr". Left out, numbers go right
    groups  group headings. {'Demand': 0, 'Hiring': 5} puts Demand before row 0 and Hiring
            before row 5, as bold rows across the columns
    indent  whether to indent the first column of rows under a group. Left out, True if
            there are groups
    size    the type size in pt (9.5, say). Left out, the same as the text
    """
    d = ov_dir('tables')
    out = []
    if isinstance(x, str):
        x = {'tex': x}
    if isinstance(x, dict) and x and set(x) <= set(_RENDER) and all(isinstance(v, str) for v in x.values()):
        for fmt, text in x.items():
            out.append(_write(d / f'{name}.{fmt}', text.rstrip('\n') + '\n'))
        miss = [f for f in formats if f not in x]
        if miss:
            import warnings
            warnings.warn(f'ov_table: {name} has no {"/".join(miss)}, so the table will not appear in that format')
        return out
    heads, cols = _columns(x)
    rows = _cells(cols, digits)
    al = _align(cols, align)
    plan = _plan(len(rows), groups, indent)
    for fmt in formats:
        if fmt not in _RENDER:
            raise ValueError(f'ov_table: unknown format {fmt}')
        out.append(_write(d / f'{name}.{fmt}', _RENDER[fmt](heads, rows, al, notes, plan, size)))
    return out
