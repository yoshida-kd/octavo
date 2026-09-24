# -*- coding: utf-8 -*-
"""原稿に**直書きされた分析結果らしき数値**を見つける。

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
    マークダウンの表（`|` で始まる行）    表の中身は数値でよい
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


def scan(text: str, accepted: set) -> list:
    """1本の原稿を見る。(行番号, 種類, 文字列, 行) の並びを返す。"""
    _, body = mdlib.split_front_matter(text)
    offset = len(text[:len(text) - len(body)].split('\n')) - 1
    masked, _ = valmod.mask_code(body)

    out = []
    for i, raw in enumerate(masked.split('\n'), start=1):
        if SKIP_LINE.match(raw) or '\x00octavo-code-' in raw:
            continue
        line = _scrub(raw)
        seen: set = set()
        for kind, pat in RULES:
            for m in pat.finditer(line):
                hit = m.group(0).strip()
                if hit in accepted or hit in seen:
                    continue
                # 小数だけの規則は、他の規則がすでに拾った箇所を重ねない
                if kind == 'decimal' and any(hit in s for s in seen):
                    continue
                seen.add(hit)
                out.append((offset + i, kind, hit, ' '.join(raw.split())[:78]))
    return out


# ---------------------------------------------------------------- ひな型の残り
# `octavo init` / `octavo new` が置いたひな型には、**例**の塊に印が入れてある。
#     <!-- octavo:example ここから -->  …  <!-- octavo:example ここまで -->
# 自分の中身に置き換えたら印ごと消す約束なので、残っていれば「まだひな型のまま」。
# 直書きの数値と同じで、**原稿に残っていてはいけないもの**なのでここが見る。

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
    ユーザーが自分で書いた文書に印が入ることは無い。
    """
    seen: list = []
    targets = [src for _, src, _ in cfg.sources()]
    targets += [u.src for u in anamod.units(cfg)]     # 設定の読み方は1箇所だけ
    targets.append(Path(cfg['bib_file']))
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


# ---------------------------------------------------------------- 直書きの数値

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

    found = collect(cfg)
    if not found:
        if not quiet and not left:
            print(t('found nothing that looks like a hand-typed result'))
        return 1 if left else 0

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


def leftovers_json(cfg) -> list:
    return [asdict(lo) for lo in leftovers(cfg)]


def as_json(cfg) -> list:
    return [asdict(f) | {'label': f.label()} for f in collect(cfg)]
