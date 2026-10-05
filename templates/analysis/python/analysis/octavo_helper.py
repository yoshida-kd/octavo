# =====================================================================
#  Octavo — 分析（.qmd）から論文（.md）へ、数値・図・表を渡す（Python 版）。
#
#  analysis/octavo.R と同じ約束をそのまま守る。書き出すファイルも形も同じなので、
#  原稿の側は R の分析のときと何も変わらない。
#
#  使い方（.qmd の最初のチャンクで読み込む）:
#
#      import os, sys
#      root = os.environ.get("OCTAVO_ROOT")
#      sys.path.insert(0, os.path.join(root, "analysis") if root else ".")
#      from octavo_helper import *
#
#  そのあと分析の中で:
#
#      ov_value("n_obs", len(d))                 -> 本文の {{n_obs}}
#      ov_value("coef_x", model.params["x"])     -> 本文の {{coef_x}}
#      ov_value("p_x", ov_pval(model.pvalues["x"]))
#      ov_figure(fig, "trend")                   -> assets/figures/trend.{pdf,png}
#      ov_table(df, "summary")                   -> assets/tables/summary.{tex,typ,md}
#      ov_palette(3) / ov_tint(col)              色覚に配慮した配色
#
#  数値は assets/values/<この .qmd の名前>.json に貯まる。octavo build が読んで
#  本文の {{…}} に差し込む。図は原稿に ![推移](../../assets/figures/trend.png){#fig-trend}
#  と書けば入り、表は原稿に `: 記述統計 {#tbl-summary}` の1行を書けばそこに入る。
#  キャプションと番号は原稿の側（@fig-trend / @tbl-summary で参照できる）。
#
#  **整数と小数を区別する。**Python の int（len() など）は桁区切り付きで
#  「1,523」、float（係数など）は既定 3 桁で「0.342」になる。NumPy の整数・
#  小数も同じ扱い。書式を決め打ちしたいときは ov_value(..., fmt=".2f") か、
#  本文側で {{coef_x:.2f}} と書く。
#
#  標準ライブラリだけで動く。matplotlib / plotnine は図を渡したときだけ、
#  pandas は DataFrame を表に渡したときだけ要る（リストや辞書でも渡せる）。
#  表の LaTeX 出力は booktabs（\toprule 等）を使う。Typst の表は table.hline() を
#  使うので Typst 0.11 以上。
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


# ---------------------------------------------------------------- 置き場所

def ov_root() -> Path:
    """プロジェクトの根。octavo が OCTAVO_ROOT で渡す。直接 render したときは上へたどる。"""
    e = os.environ.get('OCTAVO_ROOT')
    if e and os.path.isdir(e):
        return Path(e).resolve()
    d = Path.cwd().resolve()
    for p in (d, *d.parents):
        if (p / 'octavo.config.py').exists():
            return p
    return d


def ov_dir(kind: str = 'values') -> Path:
    """書き出し先。octavo が環境変数で渡す（octavo.config.py の values_dir など）。
    Quarto で直接 render したときは、既定の置き場 assets/ の下。"""
    env = {'values': 'OCTAVO_VALUES_DIR', 'figures': 'OCTAVO_FIGURE_DIR',
           'tables': 'OCTAVO_TABLE_DIR'}
    if kind not in env:
        raise ValueError(f'ov_dir: kind は {" / ".join(env)} のどれか（{kind!r}）')
    p = os.environ.get(env[kind])
    d = Path(p) if p else ov_root() / 'assets' / kind
    d.mkdir(parents=True, exist_ok=True)
    return d


def _values_file() -> Path:
    """値の書き出し先。既定は「この .qmd と同じ名前の .json」。1本の .qmd が
    1つのファイルを持つので、複数の分析が同じファイルを取り合わない。"""
    name = os.environ.get('OCTAVO_VALUES_NAME')
    if not name:
        doc = os.environ.get('QUARTO_DOCUMENT_FILE')  # Quarto が .qmd のファイル名を渡す
        name = Path(doc).stem if doc else 'values'
    return ov_dir('values') / f'{name}.json'


def _write(path: Path, text: str) -> Path:
    # BOM なしの UTF-8、改行は \n（Windows でも変えない）
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(text)
    return path


# ---------------------------------------------------------------- 数値

_store: dict = {}


def _scalar(x, name: str):
    """JSON に書ける1つの値にする。整数は int、小数は float のまま（区別が要る）。"""
    if x is None or type(x).__name__ in ('NAType', 'NaTType'):     # pandas の欠損も
        return 'NA'
    if isinstance(x, (str, bool, int, float)):
        pass
    elif hasattr(x, 'item') and getattr(x, 'size', 1) == 1:   # NumPy のスカラー・要素1の配列
        return _scalar(x.item(), name)
    elif hasattr(x, '__len__'):
        n = len(x)
        if n != 1:
            raise ValueError(f'ov_value: 値は1つだけ渡す（{name} は長さ {n}）')
        return _scalar(x.iloc[0] if hasattr(x, 'iloc') else list(x)[0], name)
    elif isinstance(x, (datetime.date, datetime.datetime)):
        return x.isoformat()
    else:
        try:                                                    # Decimal など
            return float(x)
        except (TypeError, ValueError):
            return str(x)
    if isinstance(x, float) and not math.isfinite(x):
        return 'NA' if math.isnan(x) else str(x)                # inf は文字で
    return x


def ov_value(name: str, x, fmt: str | None = None, note: str | None = None):
    """論文の本文に出す数値を1つ登録する。

    name  本文で {{name}} と書く名前（英字か _ で始め、英数字・_ ・. だけ）
    x     値（長さ1）。整数・小数・文字のいずれでもよい
    fmt   Python の書式指定（".3f" 等）。省略なら Octavo 側の既定
    note  覚え書き。octavo check values で表示される
    """
    import re
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]*', name):
        raise ValueError(f'ov_value: name は英字か _ で始め、英数字・_ ・. だけを使う（{name!r}）')
    v = _scalar(x, name)
    path = _values_file()
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
    """複数まとめて登録する。ov_values(n_obs=len(d), mean_x=d.x.mean())"""
    for k, v in kw.items():
        ov_value(k, v)
    return kw


def _session() -> dict:
    """再現性の記録。何で実行したかを値のファイルに一緒に残す（`_` で始まるキーは
    Octavo が値として扱わない）。読み込んだパッケージだけを記録する。"""
    pkgs: dict = {}
    try:
        from importlib import metadata
        # packages_distributions は 3.10 から。それ以前は import 名 = 配布名とみなす
        owner = getattr(metadata, 'packages_distributions', lambda: {})()
        for top in {m.split('.')[0] for m in list(sys.modules)}:
            for dist in owner.get(top, (top,)):
                try:
                    pkgs.setdefault(dist, metadata.version(dist))
                except metadata.PackageNotFoundError:
                    pass
    except Exception:           # 記録に失敗しても分析は止めない
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
    """p 値の慣例的な書き方。0.001 未満は "< .001"。"""
    p = _scalar(p, 'p')
    if not isinstance(p, (int, float)) or isinstance(p, bool) or math.isnan(p):
        return 'NA'
    cut = 10.0 ** -digits
    if p < cut:
        return '< ' + f'{cut:.{digits}f}'.lstrip('0')
    return f'{p:.{digits}f}'.lstrip('0')


# ---------------------------------------------------------------- 配色
# 色覚の多様性に配慮した配色（カラーユニバーサルデザイン）。Okabe & Ito (2008) の
# 8 色。図を作るときの約束（プロジェクトの CLAUDE.md）:
#   1. 色はここから選ぶ
#   2. 色だけで区別しない（値や名前を図の中に直接書く。強調は太字・線種・位置でも）
#   3. 隣り合う面は明るさも変える。文字を載せる面は ov_tint() で白に寄せる
#   4. 赤と緑、黄と白を隣り合わせない

ov_cud = {'blue': '#0072B2', 'orange': '#E69F00', 'green': '#009E73',
          'vermillion': '#D55E00', 'skyblue': '#56B4E9', 'purple': '#CC79A7',
          'yellow': '#F0E442', 'grey': '#999999', 'black': '#000000'}
_ORDER = ('blue', 'orange', 'green', 'vermillion', 'skyblue', 'purple', 'yellow', 'grey')


def ov_palette(n=None):
    """CUD の色を返す。n を渡すとその数だけ（見分けやすい順）、名前（のリスト）を渡すとその色。

        ov_palette(3)                    # 青・橙・緑
        ov_palette(["blue", "grey"])
    """
    if n is None:
        return [ov_cud[k] for k in _ORDER]
    if isinstance(n, str):
        n = [n]
    if isinstance(n, (list, tuple)):
        bad = [k for k in n if k not in ov_cud]
        if bad:
            raise ValueError(f'ov_palette: 知らない色 {", ".join(bad)}（{" / ".join(ov_cud)}）')
        return [ov_cud[k] for k in n]
    if n > len(_ORDER):
        raise ValueError(f'ov_palette: 色は {len(_ORDER)} まで（それより多いなら'
                         '色ではなく線種・形・直接の文字で区別する）')
    return [ov_cud[k] for k in _ORDER[:n]]


def ov_tint(col, p: float = 0.6):
    """色を白に寄せる（p = 0 でそのまま、1 で白）。面の上に黒い文字を載せるときに。
    色は "#RRGGBB"（または CUD の名前）。リストを渡せばリストで返す。"""
    if isinstance(col, (list, tuple)):
        return [ov_tint(c, p) for c in col]
    h = ov_cud.get(col, col).lstrip('#')
    rgb = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    return '#' + ''.join(f'{round(c + (255 - c) * p):02X}' for c in rgb)


# ---------------------------------------------------------------- 図

# 和文の図に使う書体（Octavo の既定の書体の順。入っているものの最初を使う）
_CJK_FONTS = ('BIZ UDGothic', 'Noto Sans CJK JP', 'Hiragino Sans', 'Hiragino Kaku Gothic ProN',
              'Yu Gothic', 'IPAexGothic', 'TakaoPGothic', 'VL Gothic')


def ov_style() -> None:
    """matplotlib の既定を整える。PDF に文字を文字のまま埋め込み（検索・選択できる）、
    和文の書体があれば使う。ov_figure() も呼ぶが、図を作る**前**に呼んでおくと、
    その図の文字にも効く（.qmd の最初のチャンクで）。matplotlib が無ければ何もしない。"""
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
    """図を assets/figures/ に保存する。既定で .pdf（Typst・LaTeX 用）と .png（Word 用）
    の両方を書くので、octavo.config.py の figure_ext をそのまま使える。

    x       matplotlib の Figure、plotnine の ggplot、あるいは「描画する関数」
            （中で matplotlib.pyplot に描く。呼ぶ前に新しい図を用意する）
    name    ファイル名（拡張子なし）。原稿の ![](assets/figures/<name>.png) と揃える
    width / height  インチ。省略なら Figure の大きさ（関数・ggplot は 6 x 4）
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
        if hasattr(x, 'savefig'):                       # matplotlib の Figure
            if width or height:
                w0, h0 = x.get_size_inches()
                x.set_size_inches(width or w0, height or h0)
            x.savefig(path, dpi=dpi, format=fmt)
        elif hasattr(x, 'save'):                        # plotnine の ggplot
            x.save(str(path), width=width or 6, height=height or 4, dpi=dpi, verbose=False)
        else:
            raise TypeError('ov_figure: matplotlib の Figure、plotnine の ggplot、'
                            f'描画する関数のどれかを渡す（{type(x).__name__}）')
        out.append(path)
    if closer:
        closer(x)
    return out


# ---------------------------------------------------------------- 表

def _tex_escape(s: str) -> str:
    s = s.replace('\\', '\u0001')                       # 先に印に逃がす（波括弧の二重エスケープを避ける）
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
    return type(v).__name__ in ('NAType', 'NaTType')    # pandas の欠損


def _plain(v):
    return v.item() if hasattr(v, 'item') and getattr(v, 'size', 1) == 1 else v


def _columns(x):
    """表の入力を (見出し, 列ごとの値のリスト) にする。DataFrame・辞書（列名: 値のリスト）・
    辞書のリスト（行）・リストのリスト（1行目が見出し）。"""
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
    raise TypeError('ov_table: DataFrame・辞書（列名: 値のリスト）・辞書のリスト・'
                    '1行目が見出しのリストのリスト、のどれかを渡す')


def _cells(cols, digits):
    out = []
    for col in cols:
        cell = []
        for v in col:
            if _missing(v):
                cell.append('')
            elif isinstance(v, float):
                cell.append(f'{v:.{digits}f}')               # 小数は digits 桁に揃える
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


def _tex_table(heads, rows, align, notes):
    head = ' & '.join('\\textbf{' + _tex_escape(h) + '}' for h in heads)
    body = ' \\\\\n'.join(' & '.join(_tex_escape(c) for c in r) for r in rows)
    return ('% octavo_helper.py の ov_table() が作ったファイル。手で直さない。\n'
            '\\begin{tabular}{' + ''.join(align) + '}\n\\toprule\n' + head + ' \\\\\n\\midrule\n'
            + (body + ' \\\\\n' if rows else '') + '\\bottomrule\n\\end{tabular}\n'
            + (f'\\par\\vspace{{2pt}}\n{{\\footnotesize {_tex_escape(notes)}}}\n' if notes else ''))


def _typ_table(heads, rows, align, notes):
    word = {'l': 'left', 'r': 'right', 'c': 'center'}
    cell = lambda v: '[' + _typ_escape(v) + ']'
    head = ', '.join('[*' + _typ_escape(h) + '*]' for h in heads)
    body = '\n'.join('  ' + ', '.join(cell(c) for c in r) + ',' for r in rows)
    return ('// octavo_helper.py の ov_table() が作ったファイル。手で直さない。\n'
            '#table(\n'
            f'  columns: {len(heads)},\n'
            f'  align: ({", ".join(word[a] for a in align)}),\n'
            '  stroke: none,\n  table.hline(),\n'
            f'  {head},\n  table.hline(stroke: 0.5pt),\n'
            + (body + '\n' if rows else '') + '  table.hline(),\n)\n'
            + (f'#v(2pt)\n#text(size: 8pt)[{_typ_escape(notes)}]\n' if notes else ''))


def _md_table(heads, rows, align, notes):
    esc = lambda v: v.replace('|', '\\|')
    rule = {'l': ':---', 'r': '---:', 'c': ':---:'}
    row = lambda v: '| ' + ' | '.join(esc(c) for c in v) + ' |'
    return ('<!-- octavo_helper.py の ov_table() が作ったファイル。手で直さない。 -->\n\n'
            + row(heads) + '\n|' + '|'.join(rule[a] for a in align) + '|\n'
            + '\n'.join(row(r) for r in rows) + '\n'
            + (f'\n*{notes}*\n' if notes else ''))


_RENDER = {'tex': _tex_table, 'typ': _typ_table, 'md': _md_table}


def ov_table(x, name: str, notes: str | None = None, align: str | None = None,
             digits: int = 3, formats=('tex', 'typ', 'md')):
    """表を assets/tables/ に保存する（.tex・.typ・.md。Typst・LaTeX・Word がそれぞれ読む）。
    本文に `: 表題 {#tbl-<name>}` の1行を書けば、Octavo がそこに差し込み、
    @tbl-<name> で参照できる。キャプションは本文が持つ（ここでは付けない）。

    x       DataFrame、辞書（列名: 値のリスト）、辞書のリスト、1行目が見出しのリストのリスト。
            あるいは {"tex": "…", "typ": "…", "md": "…"}（statsmodels の as_latex() など
            が作った文字列をそのまま渡すとき）
    name    ファイル名（拡張子なし）
    notes   表の下に小さく出す注
    align   "lrrr" のように列ごとの寄せを決める。省略なら数値は右
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
            warnings.warn(f'ov_table: {name} に {"/".join(miss)} がない。その形式では表が入らない')
        return out
    heads, cols = _columns(x)
    rows = _cells(cols, digits)
    al = _align(cols, align)
    for fmt in formats:
        if fmt not in _RENDER:
            raise ValueError(f'ov_table: 不明な形式 {fmt}')
        out.append(_write(d / f'{name}.{fmt}', _RENDER[fmt](heads, rows, al, notes)))
    return out
