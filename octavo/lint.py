# -*- coding: utf-8 -*-
"""原稿に**手入力された分析結果らしき数値**を見つける。

    octavo lint

このツールの中心的な約束は「論文に出る数値を原稿に手で書かない」こと
（`.qmd` の `ov_value()` に登録して本文では `{{名前}}` と書く）。ところが
その約束は、いまのところ人が覚えているかどうかに掛かっている。ここは
それを機械で見張る。

見つけるのは「結果らしい書き方」であって、数値そのものではない:

    0.342 / 12.34          小数（係数・平均・標準偏差）
    N = 1,523 / n = 84     標本サイズ
    p < .001 / p = 0.03    p 値
    12.3%                  パーセント
    (0.081)                括弧の中の小数（標準誤差）

**見ない場所**（数字があって当たり前のところ）:

    コードブロック・インラインコード      values.py の伏せ字と同じ扱い
    Markdown の表（`|` で始まる行）    表の中身は数値でよい
    見出し（`## 2.1 …`）                  節番号
    front matter                          日付など
    URL・DOI（`10.1093/…`）               版数のような小数

慣例的な定数（`0.05`、`1.96` など）は既定で見逃す。追加は
`octavo.config.py` の `lint_accepted` に**一致する文字列**を並べる。

    'lint_accepted': ['0.5', '2.5'],   # 理論値としてよく書くもの

判定は `collect()` 1箇所だけにある。`octavo lint` も `octavo check` も
そこを呼ぶので、食い違わない。
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path

from . import analysis as anamod
from . import diagrams
from . import md as mdlib
from . import values as valmod
from .i18n import t

# 慣例として本文に書く数値。結果ではないので既定で見逃す。
CONVENTIONAL = {
    '0.05', '.05', '0.01', '.01', '0.001', '.001', '0.10', '.10', '0.1',
    '1.96', '2.58', '1.645', '0.5', '95%', '99%', '90%',
}

RULES = (
    ('pvalue',  re.compile(r'\b[pP]\s*[<>=≦≧]\s*0?\.\d+')),
    ('n',       re.compile(r'\b[Nn]\s*=\s*\d[\d,]*')),
    ('percent', re.compile(r'\d+(?:\.\d+)?\s*[%％]')),
    ('se',      re.compile(r'[(（]\s*-?\d+\.\d+\s*[)）]')),
    ('decimal', re.compile(r'(?<![\w.])-?\d+\.\d{2,}(?![\d.])')),
)

def KIND_LABEL(kind: str) -> str:
    return {
        'pvalue':  t('p value'),
        'n':       t('sample size'),
        'percent': t('percentage'),
        'se':      t('decimal in parentheses (a standard error?)'),
        'decimal': t('decimal'),
    }.get(kind, kind)

# 見ない場所
SKIP_LINE = re.compile(r'^\s*(?:\||#{1,6}\s|>\s*\||:\s)')
LINK = re.compile(r'\[[^\]]*\]\([^)]*\)|<https?://[^>]*>|https?://\S+')
DOI = re.compile(r'\b10\.\d{4,9}/\S+')
ATTR = re.compile(r'\{[#.][^}]*\}')                    # {#sec:1} 等


@dataclass
class Finding:
    doc: str            # 文書名（付録なら「名前(付録)」）
    file: str           # ファイル名
    line: int           # 1 始まり
    kind: str
    text: str           # 引っかかった文字列
    excerpt: str        # その行（見せる用に詰めたもの）

    def label(self) -> str:
        return KIND_LABEL(self.kind)


def _scrub(line: str) -> str:
    """1行から「数字があって当たり前の部分」を消す。"""
    line = LINK.sub(' ', line)
    line = DOI.sub(' ', line)
    line = ATTR.sub(' ', line)
    line = valmod.PLACEHOLDER.sub(' ', line)          # {{coef:.2f}} の .2f
    return line


NUMBER_ONLY = re.compile(r'^[\d.,%％\s-]+$')
NO_LINT_SPAN = re.compile(r'\[((?:[^\[\]\n]|\[[^\[\]\n]*\])*)\]\{[^{}\n]*\.no-lint\b[^{}\n]*\}')


def _drop_no_lint(body: str) -> str:
    """`[40%]{.no-lint}` と `::: {.no-lint}` … `:::` の中を見ないようにする（行の数は保つ）。

    結果でない数値だと一番よく知っているのは書いた人なので、原稿の側で印を付けられる。
    """
    body = NO_LINT_SPAN.sub(lambda m: ' ' * len(m.group(0)), body)
    out, depth, skip_at = [], 0, None
    for line in body.split('\n'):
        bare = line.strip()
        if mdlib.DIV_OPEN.match(bare) and not mdlib.DIV_CLOSE.match(bare):
            m = mdlib.DIV_OPEN.match(bare)
            depth += 1
            if skip_at is None and 'no-lint' in mdlib._classes(m.group(2), m.group(3)):
                skip_at = depth
            out.append('' if skip_at else line)
            continue
        if mdlib.DIV_CLOSE.match(bare) and depth:
            out.append('' if skip_at else line)
            if skip_at == depth:
                skip_at = None
            depth -= 1
            continue
        out.append('' if skip_at else line)
    return '\n'.join(out)


def scan(text: str, accepted: set) -> list:
    """1本の原稿を見る。(行番号, 種類, 文字列, 行) の並びを返す。"""
    _, body = mdlib.split_front_matter(text)
    offset = len(text[:len(text) - len(body)].split('\n')) - 1
    masked, _ = valmod.mask_code(body)
    shown = masked.split('\n')                      # 見せる行は印を消す前のもの
    masked = _drop_no_lint(masked)
    # 「中間レポート40%」のように前後ごと書いた lint_accepted は、その行にあれば見逃す
    phrases = [a for a in accepted if not NUMBER_ONLY.match(a)]

    out = []
    for i, raw in enumerate(masked.split('\n'), start=1):
        if SKIP_LINE.match(raw) or '\x00octavo-code-' in raw:
            continue
        line = _scrub(raw)
        here = [a for a in phrases if a in raw]
        seen: set = set()
        for kind, pat in RULES:
            for m in pat.finditer(line):
                hit = m.group(0).strip()
                if hit in accepted or hit in seen or any(hit in a for a in here):
                    continue
                # 小数だけの規則は、他の規則がすでに拾った箇所を重ねない
                if kind == 'decimal' and any(hit in s for s in seen):
                    continue
                seen.add(hit)
                out.append((offset + i, kind, hit, ' '.join(shown[i - 1].split())[:78]))
    return out


# ---------------------------------------------------------------- ひな型の残り
# `octavo init` / `octavo new` が置いたひな型には、**例**の塊に印が入れてある。
#     <!-- octavo:example ここから -->  …  <!-- octavo:example ここまで -->
# 自分の中身に置き換えたら印ごと消す約束なので、残っていれば「まだひな型のまま」。
# 手入力の数値と同じで、**原稿に残っていてはいけないもの**なのでここが見る。

EXAMPLE_MARK = 'octavo:example'
# 説明文の中で `octavo:example` と名前を出しているだけのものは印ではない
_MARK = re.compile(r'(?<!`)' + re.escape(EXAMPLE_MARK))


@dataclass
class Leftover:
    file: str
    line: int
    excerpt: str


def leftovers(cfg) -> list:
    """ひな型の印が残っているファイルを返す。list[Leftover]。

    見るのは、ひな型を書いた先（原稿・付録・登録された .qmd・書誌）だけ。
    ユーザーが自分で書いた文書に印が入ることはない。
    """
    seen: list = []
    targets = [src for _, src, _ in cfg.sources()]
    targets += [u.src for u in anamod.units(cfg)]     # 設定の読み方は1箇所だけ
    targets.append(Path(cfg['bib_file']))
    targets += diagrams.sources(cfg)                  # octavo new figure の見本の図
    for path in targets:
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            if _MARK.search(line):
                seen.append(Leftover(file=cfg.rel(path), line=i,
                                     excerpt=line.strip()[:70]))
    return seen


# ---------------------------------------------------------------- 手入力の数値

def collect(cfg) -> list:
    """設定にある原稿（付録も）を全部見る。list[Finding] を返す。"""
    accepted = CONVENTIONAL | {str(x) for x in (cfg['lint_accepted'] or ())}
    out: list = []
    for name, src, is_appendix in cfg.sources():
        label = f'{name} ' + t('(appendix)') if is_appendix else name
        for line, kind, hit, excerpt in scan(mdlib.read(src), accepted):
            out.append(Finding(doc=label, file=cfg.rel(src), line=line,
                               kind=kind, text=hit, excerpt=excerpt))
    return out


# ---------------------------------------------------------------- 囲み（:::）の書き違い
# どちらも警告は出ずに、黙って崩れるか消える:
#   開きの `:::` の前に空行がないと、pandoc は囲みにせず `:::` を文字として本文に出す
#   出し分けの名前の打ち間違い（`.slide-only` など）は、どの出力にも出ずに消える

# 出し分けの印に使える名前（Ctx.keep_classes が入れるもの）
def _known_conditions() -> set:
    from . import config as configmod
    from .backends.base import PROFILES
    return ({'slides', 'slide', 'screen', 'print', 'doc', 'anonymous', 'lint'}
            | set(configmod.BACKENDS) | set(PROFILES))


@dataclass
class DivIssue:
    file: str
    line: int           # 1 始まり
    kind: str           # 'literal'（囲みとして読まれない）| 'unknown'（知らない出し分け）
    excerpt: str
    suggest: str = ''   # unknown のとき、近い名前


def div_problems(text: str) -> list:
    """[(行番号, 種類, 行, 近い名前)]。コードの中は見ない。"""
    import difflib
    _, body = mdlib.split_front_matter(text)
    offset = text[:len(text) - len(body)].count('\n')
    masked, _ = valmod.mask_code(body)
    # コメントの中（書きかけの区切りを寝かせてあるなど）は見ない。行の数は保つ
    masked = re.sub(r'<!--.*?-->', lambda m: '\n' * m.group(0).count('\n'), masked, flags=re.S)
    known = _known_conditions()
    out = []
    prev = ''
    for i, line in enumerate(masked.split('\n'), start=1):
        bare = line.strip()
        is_open = bool(mdlib.DIV_OPEN.match(bare)) and not mdlib.DIV_CLOSE.match(bare)
        if is_open:
            p = prev.strip()
            # 直前が囲みの開き・閉じ・見出しなら空行がなくても読まれる
            if p and not (mdlib.DIV_OPEN.match(p) or mdlib.DIV_CLOSE.match(p) or p.startswith('#')):
                out.append((offset + i, 'literal', bare, ''))
        elif ':::' in bare and not mdlib.DIV_CLOSE.match(bare) and '\x00octavo-code-' not in bare:
            out.append((offset + i, 'literal', bare, ''))
        conds = []
        if is_open:
            m = mdlib.DIV_OPEN.match(bare)
            conds += mdlib._classes(m.group(2), m.group(3))
        for m in mdlib.SPAN.finditer(line):
            conds += [x[1:] for x in m.group(2).split() if x.startswith('.')]
        for c in conds:
            if not mdlib.is_condition(c):
                continue
            mo, mn = mdlib.ONLY.match(c), mdlib.NOT.match(c)
            what = (mo.group(1) or mo.group(2)) if mo else (mn.group(1) if mn else None)
            if what is None or what in known:
                continue
            near = difflib.get_close_matches(what, sorted(known), n=1, cutoff=0.6)
            fix = ''
            if near:
                fix = c.replace(what, near[0])
            out.append((offset + i, 'unknown', bare, fix))
        prev = line
    return out


def div_issues(cfg) -> list:
    out = []
    for _name, src, _app in cfg.sources():
        for line, kind, excerpt, fix in div_problems(mdlib.read(src)):
            out.append(DivIssue(cfg.rel(src), line, kind, excerpt[:60], fix))
    return out


def div_issue_text(it: DivIssue) -> str:
    if it.kind == 'literal':
        return t('not read as a block — put a blank line before the opening :::')
    if it.suggest:
        return t('shown in no output — did you mean .{name}?', name=it.suggest)
    return t('shown in no output — not a name octavo knows (slides, handout, print, …)')


# ---------------------------------------------------------------- 表示

def run(cfg, quiet: bool = False) -> int:
    left = leftovers(cfg)
    if left:
        print(t('{n} {n|place is|places are} still the template (replace {n|it|them} '
                'with your own content and delete the octavo:example {n|mark|marks})',
                n=len(left)) + '\n')
        last = None
        for lo in left:
            if lo.file != last:
                print(f'  {lo.file}')
                last = lo.file
            print(f'    {lo.line:>4}: {lo.excerpt}')
        print()

    indents = indent_issues(cfg)
    if indents:
        print(t('{n} nested list {n|item is|items are} out of line (line a nested item up '
                'with its parent\'s text: 2 spaces under "- ", 3 under "1. ")', n=len(indents))
              + '\n')
        last = None
        for it in indents:
            if it.file != last:
                print(f'  {it.file}')
                last = it.file
            why = (t('too shallow to nest (it becomes a separate list)') if it.kind == 'shallow'
                   else t('a different width from the rest of this file'))
            print(f'    {it.line:>4}: {it.excerpt}   [{why}]')
        print()

    divs = div_issues(cfg)
    if divs:
        print(t('{n} ::: {n|block is|blocks are} written so that pandoc or octavo will not '
                'read {n|it|them} as meant', n=len(divs)) + '\n')
        last = None
        for it in divs:
            if it.file != last:
                print(f'  {it.file}')
                last = it.file
            print(f'    {it.line:>4}: {it.excerpt}   [{div_issue_text(it)}]')
        print()

    found = collect(cfg)
    if not found:
        if not quiet and not left and not indents and not divs:
            print(t('found nothing that looks like a hand-typed result'))
        return 1 if (left or indents or divs) else 0

    print(t('{n} {n|looks like a hand-typed number|look like hand-typed numbers} '
            '(if {n|it is a result, move it|they are results, move them} to '
            'ov_value() in the .qmd)', n=len(found)) + '\n')
    last = None
    for f in found:
        if f.file != last:
            print(f'  {f.file}')
            last = f.file
        print(f'    {f.line:>4}: {f.text}   [{f.label()}]')
        print(f'          {f.excerpt}')
    print('\n  ' + t('If it is a result:  add ov_value("name", value) to the .qmd '
                     'and write {{name}} in the text'))
    print('  ' + t('If it is not:       add the string to lint_accepted in '
                   'octavo.config.py'))
    return 1


def as_json(cfg) -> list:
    return [asdict(f) | {'label': f.label()} for f in collect(cfg)]


# ---------------------------------------------------------------- 箇条書きの字下げ
# 入れ子の箇条書きは、子の項目を親の本文の桁（`- ` なら 2、`1. ` なら 3）に揃える。
# それより浅いと pandoc は入れ子にしない（番号付きの下の 2 字は入れ子にならない）。
# 幅（2 か 4 か）は決めないが、1つの原稿の中で混ざっていると崩れに気づきにくい。

LIST_ITEM = re.compile(r'^(?P<indent>[ \t]*)(?P<marker>[-*+]|\d+[.)])(?P<gap>[ \t]+)\S')


@dataclass
class IndentIssue:
    file: str
    line: int           # 1 始まり
    kind: str           # 'shallow'（入れ子にならない）| 'mixed'（幅が混ざっている）
    excerpt: str


def _width(s: str) -> int:
    return len(s.replace('\t', '    '))


def list_indents(text: str) -> list:
    """[(行番号, 種類, 行)]。コードブロックと front matter は見ない。"""
    _, body = mdlib.split_front_matter(text)
    offset = text[:len(text) - len(body)].count('\n')
    out = []
    stack: list = []            # [(字下げ, 本文の桁, 印が - か)]
    steps: list = []            # [(字下げの差, 行番号, 行)] `-` の項目の下の入れ子だけ
    fence = None
    for i, line in enumerate(body.split('\n')):
        f = mdlib.FENCE_LINE.match(line)
        if f:
            fence = None if fence == f.group(1) else (fence or f.group(1))
            continue
        if fence:
            continue
        if not line.strip():
            continue
        m = LIST_ITEM.match(line)
        if not m:
            if not line[:1].isspace():
                stack = []          # 字下げのない本文で箇条書きが終わる
            continue
        ind = _width(m.group('indent'))
        col = ind + len(m.group('marker')) + _width(m.group('gap'))
        bullet = m.group('marker') in '-*+'
        while stack and ind < stack[-1][0]:
            stack.pop()
        if stack and ind == stack[-1][0]:
            stack[-1] = (ind, col, bullet)
            continue
        if stack and ind > stack[-1][0]:
            parent_ind, parent_col, parent_bullet = stack[-1]
            if ind < parent_col:
                # 入れ子にならない。親は変えずに次の行を見る
                out.append((offset + i + 1, 'shallow', line.strip()))
                continue
            if parent_bullet:
                steps.append((ind - parent_ind, offset + i + 1, line.strip()))
            stack.append((ind, col, bullet))
            continue
        stack = [(ind, col, bullet)]
    widths = [w for w, _, _ in steps]
    if len(set(widths)) > 1:
        common = max(set(widths), key=widths.count)
        out += [(ln, 'mixed', ex) for w, ln, ex in steps if w != common]
    return sorted(out)


def indent_issues(cfg) -> list:
    out = []
    for _name, src, _app in cfg.sources():
        for line, kind, excerpt in list_indents(mdlib.read(src)):
            out.append(IndentIssue(cfg.rel(src), line, kind, excerpt[:60]))
    return out
