# -*- coding: utf-8 -*-
"""`octavo bundle --replication --standalone` — Octavo を知らない人が読める .qmd にする。

複製パッケージの `.qmd` の `ov_value()` などを、R / Python の素の書き方に置き換える:

    ov_value("n_obs", nrow(d))   -> cat("n_obs:", format(nrow(d)), "\\n")
    ov_figure(p, "trend")        -> ggplot2::ggsave(file.path("..", "assets", "figures", "trend.pdf"), …)
    ov_table(tab, "summary")     -> write.csv(tab, file.path("..", "assets", "tables", "summary.csv"), …)
    file.path(ov_root(), "data") -> file.path("..", "data")

パッケージの中の複製だけを書き換える。プロジェクトの `.qmd` は触らない。一方通行の書き出しで、
ここで作ったものを Octavo が読むことはない（分析から値を受け取る仕組みはファイルのままで、
このモジュールとは関係がない）。

**R の構文解析はしない。**文字列とコメントを見分け、括弧を数えるだけの字句の処理で、確実に
置き換えられる書き方（行頭から始まる1文の呼び出しで、名前が文字列）だけを置き換える。
それ以外（変数に入れた名前、関数やループの中、式の一部、ggplot か分からない図）は `Left` として
一覧にし、そのまま残す。ov_ が残った `.qmd` はヘルパーを読み込んだままにするので、**書き換えの
結果が動かなくなることはない**（読みやすさが足りないだけ）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .i18n import t

# 配色。ヘルパーの ov_cud / ov_palette の順と揃える（テストが両方のヘルパーと比べる）
CUD = {'blue': '#0072B2', 'orange': '#E69F00', 'green': '#009E73',
       'vermillion': '#D55E00', 'skyblue': '#56B4E9', 'purple': '#CC79A7',
       'yellow': '#F0E442', 'grey': '#999999', 'black': '#000000'}
ORDER = ('blue', 'orange', 'green', 'vermillion', 'skyblue', 'purple', 'yellow', 'grey')

COMMENT = '\x01'
TOKEN = re.compile(r'(?<![\w.])ov_\w+')
ANY_TOKEN = re.compile(r'\bov_\w+')
OPENING = re.compile(r'^(`{3,})\{(r|python)\b[^}]*\}\s*$')
STATEMENTS = ('ov_value', 'ov_values', 'ov_figure', 'ov_table')
# 行の終わりにあると、次の行へ続く（次の行の ov_ は1文ではない）
CONTINUES = ('+', '-', '*', '/', '%', '|>', '<-', '=', ',', '(', '[', '{', '\\', '&')
LEADS = re.compile(r'\s*(%>%|\|>|\+)')
LITERAL = re.compile(r'''^\s*(["'])((?:(?!\1)[^\\\n])*)\1\s*$''')
SIGNATURES = {
    'ov_value': ('name', 'x', 'fmt', 'note'),
    'ov_figure': ('x', 'name', 'width', 'height', 'dpi', 'formats'),
    'ov_table': ('x', 'name', 'notes', 'align', 'digits', 'formats', 'groups', 'indent', 'size'),
}
# 表は data.frame になるものだけ置き換える。出来合いの文字列（list(tex = …) など）は置き換えない
READY_MADE = re.compile(r'list\(|modelsummary|kable|paste|sprintf|\bgt\(|as_latex|as_text|["\']tex["\']|\[\[')


@dataclass
class Left:
    """置き換えなかった呼び出し。"""
    line: int
    call: str
    why: str


@dataclass
class Result:
    text: str
    replaced: int = 0
    left: list = field(default_factory=list)      # list[Left]
    keeps: set = field(default_factory=set)       # ヘルパーを読み込んだままの言語（'r' / 'python'）


def mask(code: str, lang: str) -> str:
    """同じ長さの文字列を返す。文字列の中身は空白、コメントは COMMENT になる。改行はそのまま。"""
    out = list(code)
    n = len(code)
    i = 0

    def blank(lo: int, hi: int, ch: str = ' ') -> None:
        for k in range(lo, min(hi, n)):
            if out[k] != '\n':
                out[k] = ch

    while i < n:
        c = code[i]
        if c == '#':
            end = code.find('\n', i)
            end = n if end < 0 else end
            blank(i, end, COMMENT)
            i = end
        elif lang == 'r' and c in 'rR' and (i == 0 or not (code[i - 1].isalnum() or code[i - 1] in '._')) \
                and (m := re.match(r'''[rR](["'])(-*)([(\[{])''', code[i:i + 40])):
            close = {'(': ')', '[': ']', '{': '}'}[m.group(3)] + m.group(2) + m.group(1)
            end = code.find(close, i + m.end())
            end = n if end < 0 else end + len(close)
            blank(i, end)
            i = end
        elif c in '"\'`' and (lang == 'r' or c != '`'):
            triple = lang == 'python' and code[i:i + 3] == c * 3
            quote = c * 3 if triple else c
            k = i + len(quote)
            while k < n:
                if code[k] == '\\':
                    k += 2
                elif code.startswith(quote, k):
                    break
                elif code[k] == '\n' and lang == 'python' and not triple:
                    break
                else:
                    k += 1
            blank(i + len(quote), k)
            i = k + len(quote)
        else:
            i += 1
    return ''.join(out)


def _close(m: str, at: int) -> int | None:
    """m[at] の開き括弧に対応する閉じ括弧の位置。"""
    depth = 0
    for k in range(at, len(m)):
        if m[k] in '([{':
            depth += 1
        elif m[k] in ')]}':
            depth -= 1
            if depth == 0:
                return k
    return None


def _depth(m: str, pos: int) -> int:
    return sum(1 if c in '([{' else -1 for c in m[:pos] if c in '([{)]}')


def _args(code: str, m: str, lo: int, hi: int) -> list:
    """code[lo:hi] を、括弧の外のカンマで (名前 or None, 値の始まり, 値の終わり) に分ける。"""
    parts, depth, start = [], 0, lo
    for k in range(lo, hi):
        if m[k] in '([{':
            depth += 1
        elif m[k] in ')]}':
            depth -= 1
        elif m[k] == ',' and depth == 0:
            parts.append((start, k))
            start = k + 1
    parts.append((start, hi))
    out = []
    for a, b in parts:
        # 引数の前後のコメントは値に入れない（閉じ括弧の前に残ると、括弧ごとコメントになる）
        while b > a and (m[b - 1].isspace() or m[b - 1] == COMMENT):
            b -= 1
        while a < b and (m[a].isspace() or m[a] == COMMENT):
            a += 1
        if a == b:
            continue
        named = re.match(r'([A-Za-z_.][\w.]*)\s*=(?!=)', m[a:b])
        out.append((named.group(1), a + named.end(), b) if named else (None, a, b))
    return out


def _bind(sig: tuple, args: list) -> dict | None:
    """引数を名前に割り当てる。知らない名前があれば None。"""
    bound: dict = {}
    for name, a, b in args:
        if name is not None:
            if name not in sig:
                return None
            bound[name] = (a, b)
    free = [p for p in sig if p not in bound]
    for name, a, b in args:
        if name is None:
            if not free:
                return None
            bound[free.pop(0)] = (a, b)
    return bound


def _literal(text: str) -> str | None:
    m = LITERAL.match(text)
    return m.group(2) if m else None


class _Chunk:
    """1つの言語の書き方（パスの書き方、図と表の保存）と、変換中の状態。"""

    def __init__(self, lang: str, dirs: dict, up: int, res: Result, needs: dict):
        self.lang, self.dirs, self.up, self.res, self.needs = lang, dirs, up, res, needs
        self.r = lang == 'r'
        self.base_line = 0
        self.code = ''
        self.m = ''
        self.all_mask = ''

    def path(self, *parts: str) -> str:
        if self.r:
            return 'file.path(' + ', '.join(f'"{p}"' for p in ['..'] * self.up + list(parts)) + ')'
        self.needs['pathlib'] = True
        return ' / '.join([f'Path("{"/".join([".."] * self.up)}")'] + [f'"{p}"' for p in parts])

    def root(self) -> str:
        if self.r:
            return '"' + '/'.join(['..'] * self.up) + '"'
        self.needs['pathlib'] = True
        return f'Path("{"/".join([".."] * self.up)}")'

    def leave(self, at: int, end: int, why: str) -> None:
        call = re.sub(r'\s+', ' ', self.code[at:end]).strip()
        call = call[:57] + '...' if len(call) > 60 else call
        self.res.left.append(Left(self.base_line + self.code.count('\n', 0, at), call, why))
        self.res.keeps.add(self.lang)

    # -- 式の中に書けるもの ---------------------------------------------
    def colours(self, names: list) -> str:
        if self.r:
            return 'c(' + ', '.join(f'{k} = "{CUD[k]}"' for k in names) + ')'
        return '[' + ', '.join(f'"{CUD[k]}"' for k in names) + ']'

    def palette(self, arg: str) -> list | None:
        arg = arg.strip()
        if not arg:
            return list(ORDER)
        if re.fullmatch(r'\d+L?', arg):
            n = int(arg.rstrip('L'))
            return list(ORDER[:n]) if n <= len(ORDER) else None
        names = re.findall(r'''["'](\w+)["']''', arg)
        if names and re.fullmatch(r'''(c\(|\[)?\s*(["']\w+["']\s*,?\s*)+[)\]]?''', arg) \
                and all(k in CUD for k in names):
            return names
        return None

    def expression(self, lo: int, hi: int) -> str:
        """code[lo:hi] の中の ov_ を置き換えた文字列。"""
        out, pos = [], lo
        for tok in TOKEN.finditer(self.m, lo, hi):
            name, a, b = tok.group(), tok.start(), tok.end()
            if a < pos:
                continue
            opens = b if self.m[b:b + 1] == '(' else None
            close = _close(self.m, opens) if opens is not None else None
            inner = self.code[opens + 1:close] if close else ''
            new = None
            if name == 'ov_root' and close and not inner.strip():
                new = self.root()
            elif name == 'ov_dir' and close:
                kind = _literal(inner) if inner.strip() else 'values'
                if kind in self.dirs:
                    new = self.path(*self.dirs[kind].split('/'))
            elif name == 'ov_palette' and close:
                names = self.palette(inner)
                if names is not None:
                    new = self.colours(names)
            elif name == 'ov_cud' and opens is None:
                new = self.colours(list(CUD))
                if not self.r:
                    new = '{' + ', '.join(f'"{k}": "{v}"' for k, v in CUD.items()) + '}'
            elif name in ('ov_scale_colour_cud', 'ov_scale_fill_cud') and close and self.r:
                kind = 'colour' if 'colour' in name else 'fill'
                values = 'unname(' + self.colours(list(ORDER)) + ')'
                rest = (', ' + inner) if inner.strip() else ''
                new = f'ggplot2::scale_{kind}_manual(values = {values}{rest})'
            if new is not None:
                out += [self.code[pos:a], new]
                pos = close + 1 if close else b
                self.res.replaced += 1
                continue
            rename = {'ov_pval': 'format_p', 'ov_tint': 'tint', 'ov_style': 'setup_fonts'}.get(name)
            if rename and opens is not None and (self.lang == 'python' or name != 'ov_style'):
                self.needs['snippets'].add(rename)
                out += [self.code[pos:a], rename]
                pos = b
                self.res.replaced += 1
                continue
            end = close + 1 if close else b
            if name in STATEMENTS:
                self.leave(a, end, t('it is part of a larger expression'))
            else:
                self.leave(a, end, t('it has no plain equivalent here'))
        out.append(self.code[pos:hi])
        return ''.join(out)

    # -- 1文の呼び出し --------------------------------------------------
    def is_statement(self, a: int) -> str | None:
        """code[a] の ov_ が1文として置き換えられるか。置き換えられないなら理由。"""
        line_start = self.code.rfind('\n', 0, a) + 1
        if line_start != a:
            return t('it does not start its line')
        if _depth(self.m, a) != 0:
            return t('it is inside a function or a block')
        for prev in reversed(self.m[:line_start].split('\n')):
            s = prev.split(COMMENT)[0].rstrip()
            if s:
                if s.endswith(CONTINUES):
                    return t('it continues the line before')
                break
        return None

    def assignments(self, name: str) -> list:
        """name に代入している文の右辺（字句のうえで）。一番外の文だけを見る。"""
        got = []
        for hit in re.finditer(r'(?m)^' + re.escape(name) + r'(?:\s*,\s*\w+)*\s*(?:<-|=(?!=))', self.all_mask):
            k = hit.end()
            while True:
                nl = self.all_mask.find('\n', k)
                nl = len(self.all_mask) if nl < 0 else nl
                s = self.all_mask[hit.end():nl].split(COMMENT)[0].rstrip()
                if nl >= len(self.all_mask) or (_depth(self.all_mask[hit.end():nl], nl - hit.end()) <= 0
                                                and not s.endswith(CONTINUES)):
                    break
                k = nl + 1
            got.append(self.all_mask[hit.end():nl])
        return got

    def figure_kind(self, x: str) -> str | None:
        x = x.strip()
        if self.r:
            if re.match(r'(function\s*\(|\\\s*\()', x):
                return 'function'
            if 'ggplot(' in mask(x, 'r'):
                return 'ggplot'
            # ggplot を返す自作の関数を呼んでいる: dantai_plot("都道府県")
            called = re.match(r'([\w.]+)\(', x)
            if called:
                return 'ggplot' if any('function' in s and 'ggplot(' in s
                                       for s in self.assignments(called.group(1))) else None
            rhs = self.assignments(x)
            if any(re.match(r'\s*(function\s*\(|\\\s*\()', s) for s in rhs):
                return 'function'
            return 'ggplot' if any('ggplot(' in s for s in rhs) else None
        rhs = self.assignments(x)
        if re.search(r'(?m)^def ' + re.escape(x) + r'\(', self.all_mask):
            return 'function'
        if any('ggplot(' in s for s in rhs):
            return 'plotnine'
        if any(re.search(r'plt\.(figure|subplots)\(|\.figure\b|Figure\(', s) for s in rhs):
            return 'matplotlib'
        return None

    def statement(self, name: str, a: int, close: int) -> str | None:
        """置き換えた文字列。置き換えられなければ（一覧に載せて）None。"""
        end = close + 1
        args = _args(self.code, self.m, self.m.index('(', a) + 1, close)
        if name == 'ov_values':
            if any(k is None for k, _, _ in args) or not args:
                self.leave(a, end, t('its values have no names'))
                return None
            lines, prev = [], self.m.index('(', a) + 1
            for k, x, y in args:
                # 値のあいだのコメントは、読む人のものなので残す
                gap = zip(self.code[prev:x].split('\n'), self.m[prev:x].split('\n'))
                lines += [raw[ml.index(COMMENT):] for raw, ml in gap if COMMENT in ml]
                lines.append(self.show(k, self.expression(x, y), None))
                prev = y
            return '\n'.join(lines)
        bound = _bind(SIGNATURES[name], args)
        if bound is None:
            self.leave(a, end, t('it has an argument Octavo does not know'))
            return None
        text = lambda key: self.code[bound[key][0]:bound[key][1]] if key in bound else None
        label = _literal(text('name') or '')
        if label is None:
            self.leave(a, end, t('its name is not written as a string'))
            return None
        if name == 'ov_value':
            return self.value(a, end, label, bound, text)
        if name == 'ov_figure':
            return self.figure(a, end, label, bound, text)
        return self.table(a, end, label, bound, text)

    def show(self, label: str, value: str, fmt: str | None) -> str:
        value = value.strip()
        if self.r:
            shown = f'sprintf("%{fmt}", {value})' if fmt and re.fullmatch(r'\.\d+f', fmt) else f'format({value})'
            return f'cat("{label}:", {shown}, "\\n")'
        return f'print("{label}:", format({value}, "{fmt}"))' if fmt else f'print("{label}:", {value})'

    def value(self, a, end, label, bound, text) -> str | None:
        if 'x' not in bound:
            self.leave(a, end, t('it has an argument Octavo does not know'))
            return None
        fmt = None
        if 'fmt' in bound:
            fmt = _literal(text('fmt'))
            if fmt is None and text('fmt').strip() not in ('NULL', 'None'):
                self.leave(a, end, t('its format is not written as a string'))
                return None
        lines = [self.show(label, self.expression(*bound['x']), fmt)]
        note = _literal(text('note') or '')
        return '\n'.join(([f'# {note}'] if note else []) + lines)

    def formats(self, raw: str | None, default: tuple) -> list | None:
        if raw is None:
            return list(default)
        got = re.findall(r'''["'](\w+)["']''', raw)
        return got if got and re.fullmatch(r'''\s*(c\(|\(|\[)?\s*(["']\w+["']\s*,?\s*)+[)\]]?\s*''', raw) else None

    def figure(self, a, end, label, bound, text) -> str | None:
        if 'x' not in bound:
            self.leave(a, end, t('it has an argument Octavo does not know'))
            return None
        x = self.expression(*bound['x']).strip()
        kind = self.figure_kind(x)
        if kind is None:
            self.leave(a, end, t('it cannot tell what kind of figure this is'))
            return None
        fmts = self.formats(text('formats'), ('pdf', 'png'))
        if fmts is None:
            self.leave(a, end, t('its formats are not written out'))
            return None
        size = {k: self.expression(*bound[k]).strip() for k in ('width', 'height', 'dpi') if k in bound}
        self.needs['dirs'].add('figures')
        where = self.dirs['figures'].split('/')
        if self.r and kind == 'function':
            w, h, dpi = size.get('width', '6'), size.get('height', '4'), size.get('dpi', '300')
            call = f'{x}()' if re.fullmatch(r'[\w.]+', x) else f'({x})()'
            lines = []
            for f in fmts:
                path = self.path(*where, f'{label}.{f}')
                if f == 'pdf':
                    lines.append(f'if (capabilities("cairo")) cairo_pdf({path}, width = {w}, height = {h}) '
                                 f'else pdf({path}, width = {w}, height = {h})')
                elif f == 'png':
                    lines.append(f'png({path}, width = {w}, height = {h}, units = "in", res = {dpi})')
                else:
                    self.leave(a, end, t('its formats are not written out'))
                    return None
                lines += [call, 'invisible(dev.off())']
            return '\n'.join(lines)
        if self.r:
            w, h, dpi = size.get('width', '6'), size.get('height', '4'), size.get('dpi', '300')
            lines = []
            for f in fmts:
                extra = (', device = if (capabilities("cairo")) cairo_pdf else "pdf"' if f == 'pdf'
                         else f', dpi = {dpi}')
                lines.append(f'ggplot2::ggsave({self.path(*where, f"{label}.{f}")}, plot = {x}, '
                             f'width = {w}, height = {h}{extra})')
            return '\n'.join(lines)
        self.needs['snippets'].add('setup_fonts')
        dpi = size.get('dpi', '300')
        lines = ['setup_fonts()']
        if kind == 'function':
            w, h = size.get('width', '6'), size.get('height', '4')
            lines += ['import matplotlib.pyplot as plt', f'drawn = plt.figure(figsize=({w}, {h}))', f'{x}()']
            for f in fmts:
                lines.append(f'drawn.savefig({self.path(*where, f"{label}.{f}")}, dpi={dpi}, format="{f}")')
            lines.append('plt.close(drawn)')
            return '\n'.join(lines)
        if kind == 'plotnine':
            w, h = size.get('width', '6'), size.get('height', '4')
            for f in fmts:
                lines.append(f'{x}.save(str({self.path(*where, f"{label}.{f}")}), width={w}, height={h}, '
                             f'dpi={dpi}, verbose=False)')
            return '\n'.join(lines)
        if ('width' in size) != ('height' in size):
            self.leave(a, end, t('only one of width and height is given'))
            return None
        if 'width' in size:
            lines.append(f'{x}.set_size_inches({size["width"]}, {size["height"]})')
        for f in fmts:
            lines.append(f'{x}.savefig({self.path(*where, f"{label}.{f}")}, dpi={dpi}, format="{f}")')
        return '\n'.join(lines)

    def table(self, a, end, label, bound, text) -> str | None:
        if 'x' not in bound:
            self.leave(a, end, t('it has an argument Octavo does not know'))
            return None
        raw = text('x').strip()
        sources = [raw] + (self.assignments(raw) if re.fullmatch(r'[\w.]+', raw) else [])
        if _literal(raw) is not None or any(READY_MADE.search(s) for s in sources):
            self.leave(a, end, t('it may be a ready-made table, not a data frame'))
            return None
        x = self.expression(*bound['x']).strip()
        self.needs['dirs'].add('tables')
        where = self.dirs['tables'].split('/')
        path = self.path(*where, f'{label}.csv')
        note = _literal(text('notes') or '')
        head = [f'# {note}'] if note else []
        if self.r:
            return '\n'.join(head + [f'write.csv({x}, {path}, row.names = FALSE)'])
        self.needs['pandas'] = True
        return '\n'.join(head + [f'pd.DataFrame({x}).to_csv({path}, index=False)'])

    # -- チャンク全体 ---------------------------------------------------
    def rewrite(self, code: str, line: int) -> str:
        self.code, self.base_line = code, line
        self.m = mask(code, self.lang)
        out, pos = [], 0
        for tok in TOKEN.finditer(self.m):
            name, a, b = tok.group(), tok.start(), tok.end()
            if a < pos or name not in STATEMENTS or self.m[b:b + 1] != '(':
                continue
            close = _close(self.m, b)
            if close is None:
                continue
            rest = self.m[close + 1:].split('\n')
            ends = not rest[0].split(COMMENT)[0].strip()
            follows = LEADS.match(next((x for x in rest[1:] if x.split(COMMENT)[0].strip()), ''))
            why = self.is_statement(a) or (None if ends and not follows
                                           else t('it continues on the line after'))
            if why:
                self.leave(a, close + 1, why)
                out.append(self.expression_skip(pos, close + 1, a))
                pos = close + 1
                continue
            new = self.statement(name, a, close)
            if new is None:
                out.append(self.expression(pos, a))
                out.append(code[a:close + 1])
            else:
                out += [self.expression(pos, a), new]
                self.res.replaced += 1
            pos = close + 1
        out.append(self.expression(pos, len(code)))
        return ''.join(out)

    def expression_skip(self, lo: int, hi: int, keep: int) -> str:
        """lo から keep までは置き換え、keep から hi までの呼び出しはそのまま残す。"""
        return self.expression(lo, keep) + self.code[keep:hi]


def _clean_comments(code: str, lang: str) -> str:
    """Octavo に触れるコメントを消す（`#|` はチャンクの設定なので残す）。"""
    m = mask(code, lang)
    out = []
    for raw, ml in zip(code.split('\n'), m.split('\n')):
        at = ml.find(COMMENT)
        if at < 0 or raw[at:].startswith('#|') \
                or not re.search(r'octavo|OCTAVO|\bov_\w+', raw[at:]):
            out.append(raw)
        elif raw[:at].strip():
            out.append(raw[:at].rstrip())
    return '\n'.join(out)


LOADERS = {
    'r': (re.compile(r'^\s*source\(.*octavo\.R.*\)\s*(#.*)?$'),
          re.compile(r'^\s*\w+\s*(<-|=)\s*Sys\.getenv\(["\']OCTAVO_ROOT["\'].*\)\s*(#.*)?$')),
    'python': (re.compile(r'^\s*from\s+octavo_helper\s+import\b.*$'),
               re.compile(r'^\s*import\s+octavo_helper\b.*$'),
               re.compile(r'^\s*\w+\s*=\s*os\.environ\.get\(["\']OCTAVO_ROOT["\']\).*$'),
               re.compile(r'^\s*sys\.path\.insert\(.*\broot\b.*$')),
}
HELPER_NAMED = re.compile(r'octavo\.R|octavo_helper|OCTAVO_')
PLAIN_IMPORT = re.compile(r'^\s*import\s+(os\s*,\s*sys|sys\s*,\s*os|os|sys)\s*$')


def _setup_lines(lang: str, needs: dict, dirs: dict, up: int, snippet) -> list:
    lines = []
    if lang == 'python':
        if needs['pathlib']:
            lines.append('from pathlib import Path')
        if needs['pandas']:
            lines.append('import pandas as pd')
    chunk = _Chunk(lang, dirs, up, Result(''), {'pathlib': False, 'pandas': False,
                                                'snippets': set(), 'dirs': set()})
    for kind in sorted(needs['dirs']):
        p = chunk.path(*dirs[kind].split('/'))
        lines.append(f'dir.create({p}, recursive = TRUE, showWarnings = FALSE)' if lang == 'r'
                     else f'({p}).mkdir(parents=True, exist_ok=True)')
    ext = 'R' if lang == 'r' else 'py'
    for name in sorted(needs['snippets']):
        lines.append(snippet(f'{name}.{ext}').rstrip('\n'))
    return lines


def _split(text: str) -> list:
    """本文とチャンクに分ける: ('text', 行のリスト) / ('chunk', 言語, 開き, 行のリスト, 閉じ, 行番号)。"""
    parts, buf = [], []
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        m = OPENING.match(lines[i])
        if m:
            end = next((k for k in range(i + 1, len(lines))
                        if lines[k].rstrip() == m.group(1)), None)
            if end is not None:
                if buf:
                    parts.append(('text', buf))
                    buf = []
                parts.append(('chunk', m.group(2), lines[i], lines[i + 1:end], lines[end], i + 2))
                i = end + 1
                continue
        buf.append(lines[i])
        i += 1
    parts.append(('text', buf))
    return parts


def _clean_prose(text: str, first: bool) -> str:
    """Octavo の印と Octavo に触れるコメント、front matter の `octavo:` を消す。"""
    text = re.sub(r'(?si)<!--(?:(?!-->).)*?octavo(?:(?!-->).)*?-->\n?\n?', '', text)
    if first and text.startswith('---\n'):
        end = text.find('\n---', 3)
        if end > 0:
            head = re.sub(r'(?m)^octavo:.*\n(?:[ \t]+.*\n)*', '', text[:end + 1])
            text = head + text[end + 1:]
    return text


def convert(text: str, dirs: dict, up: int, snippet) -> Result:
    """.qmd の中身を変換する。

    dirs: {'values': 'assets/values', 'figures': …, 'tables': …}（プロジェクトの根からの相対）
    up: .qmd のフォルダから根までの段数（analysis/ なら 1）。Quarto は .qmd の場所で実行する
    snippet: 'format_p.R' のような名前から、差し込む定義の文字列を返す関数
    """
    res = Result('')
    parts = _split(text)
    needs = {lang: {'pathlib': False, 'pandas': False, 'snippets': set(), 'dirs': set()}
             for lang in ('r', 'python')}
    mask_of = {lang: '\n'.join(mask('\n'.join(p[3]), lang) for p in parts
                               if p[0] == 'chunk' and p[1] == lang) for lang in ('r', 'python')}

    new_parts = []
    for p in parts:
        if p[0] == 'text':
            prose = '\n'.join(p[1])
            for hit in re.finditer(r'`(?:r|\{r\}|\{python\})\s[^`]*\bov_\w+[^`]*`', prose):
                line = text[:text.find(hit.group())].count('\n') + 1
                res.left.append(Left(line, hit.group(), t('it is inline code in the prose')))
                res.keeps.add('python' if 'python' in hit.group() else 'r')
            new_parts.append(('text', prose))
            continue
        _, lang, opening, lines, closing, line = p
        chunk = _Chunk(lang, dirs, up, res, needs[lang])
        chunk.all_mask = mask_of[lang]
        new_parts.append(('chunk', lang, opening, chunk.rewrite('\n'.join(lines), line), closing))

    # どちらの言語についても ov_ が残らなければ、ヘルパーの読み込みを消す。消す場所に、要る準備を書く
    placed = set()
    out = []
    for p in new_parts:
        if p[0] == 'text':
            out.append(_clean_prose(p[1], not out))
            continue
        _, lang, opening, code, closing = p
        lines = code.split('\n')
        setup = _setup_lines(lang, needs[lang], dirs, up, snippet)
        at = next((i for i, l in enumerate(lines) if any(x.match(l) for x in LOADERS[lang])), None)
        if lang not in res.keeps and at is not None:
            lines = [l for l in lines if not any(x.match(l) for x in LOADERS[lang])]
        elif at is not None:
            at += 1
        if lang not in placed and setup and at is not None:
            lines[at:at] = setup
            placed.add(lang)
        out.append((lang, opening, '\n'.join(lines), closing))

    # 読み込みが見つからなかった言語は、その言語の最初のチャンクの頭に書く
    for lang in ('r', 'python'):
        setup = _setup_lines(lang, needs[lang], dirs, up, snippet)
        if lang in placed or not setup:
            continue
        for i, p in enumerate(out):
            if isinstance(p, tuple) and p[0] == lang:
                lines = p[2].split('\n')
                at = 0
                while at < len(lines) and lines[at].startswith('#|'):
                    at += 1
                lines[at:at] = setup
                out[i] = (p[0], p[1], '\n'.join(lines), p[3])
                break

    # os / sys を読み込みのためだけに import していたなら、それも消す。ヘルパーの名前が残るなら一覧へ
    py = '\n'.join(mask(p[2], 'python') for p in out if isinstance(p, tuple) and p[0] == 'python')
    plain_import_used = re.search(r'\b(os|sys)\.', py)
    final = []
    for p in out:
        if not isinstance(p, tuple):
            final.append(p)
            continue
        lang, opening, code, closing = p
        if lang == 'python' and lang not in res.keeps and not plain_import_used:
            code = '\n'.join(l for l in code.split('\n') if not PLAIN_IMPORT.match(l))
        if lang not in res.keeps:
            code = _clean_comments(code, lang)
            hit = HELPER_NAMED.search(code)
            if hit:
                res.left.append(Left(0, hit.group(), t('the helper is loaded in a way Octavo does not recognise')))
                res.keeps.add(lang)
        if not [l for l in code.split('\n') if l.strip() and not l.startswith('#|')]:
            final.append(None)      # 読み込みだけのチャンクは、チャンクごと消す
            continue
        final.append(f'{opening}\n{code}\n{closing}')

    res.text = '\n'.join(x for x in final if x is not None)
    res.left.sort(key=lambda x: x.line)
    return res


def uses_helper(text: str) -> bool:
    """.R や .py のファイルが、Octavo のヘルパーに頼っているか（字句のうえで）。"""
    return bool(ANY_TOKEN.search(text) or HELPER_NAMED.search(text))
