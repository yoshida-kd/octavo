# -*- coding: utf-8 -*-
"""`octavo selftest` — 実際に1本通して、引用が組めているかを目で確かめる。

この道具でいちばん壊れやすいのは「CSL で引用がどう組まれるか」で、そこは
pandoc の版と CSL スタイルに依存するため、環境ごとに1度は通しておきたい。

    octavo selftest                  出せる形式すべて
    octavo selftest --to latex,docx
    octavo selftest --csl apa --keep  作った一式を残して中を見る

一時ディレクトリに小さな原稿（日本語＋英語の文献、表、図、相互参照、
\\poscite）を作り、変換して、**出てきた引用と書誌の実物を印字する。**
"""
from __future__ import annotations

import re
import shutil
import tempfile
import zipfile
from pathlib import Path

from . import backends as be
from . import build as buildmod
from . import config as configmod
from . import pandocrun
from .i18n import t, tag

BIB = '''\
@article{smith2003,
  author = {Smith, Alice and Taylor, Bob},
  title = {An Example Article},
  journaltitle = {Journal of Examples},
  volume = {13},
  number = {4},
  pages = {441--468},
  date = {2003},
  doi = {10.1093/jopart/mug030},
  langid = {english},
}

@article{yamada2020,
  author = {山田, 太郎 and 田中, 花子},
  title = {日本語文献の組み方},
  journaltitle = {見本学会誌},
  volume = {12},
  pages = {1--20},
  date = {2020},
  langid = {japanese},
}

@book{exampleorg2011,
  author = {{Example Organization}},
  title = {An Example Report},
  publisher = {Example Organization},
  location = {Washington, DC},
  date = {2011},
}
'''

DRAFT = '''\
---
title: 自己診断用の原稿
author: Octavo
date: 2026-01-01
---

## 要旨

引用が組めているかを見るための短い要旨。@smith2003 を1つだけ引く。

## はじめに {#sec-intro}

地の文の引用は @yamada2020 のように書く。括弧に入れるなら
[@smith2003; @exampleorg2011] とする。所有格は \\poscite{smith2003}の議論、
日本語なら\\poscite{yamada2020}の指摘、のように書く。

相互参照はラベルで書く: @sec-analysis、@tbl-desc、@fig-trend、@eq-model。

::: notes
発表者ノート。typst-slides では落ち、typst-notes では台本に残る。
:::

分析が出した数値は {{n_obs}} 件、係数 {{coef_x}}（*p* {{p_x}}）のように
差し込まれる（assets/values/selftest.json から）。

## 分析 {#sec-analysis}

| 変数 | 平均 | 標準偏差 |
|---|---|---|
| x | 1.2 | 0.3 |
| y | 3.4 | 0.8 |

: 記述統計 {#tbl-desc}

*注: 架空の数値。*

$$
y_i = \\beta_0 + \\beta_1 x_i
$$ {#eq-model}

![推移](assets/figures/trend.png){#fig-trend}

## 参考文献
'''

CONFIG = '''\
CONFIG = {{
    'draft': 'draft.md',
    'bib_file': 'literature.bib',
    'csl': {csl!r},
    'lang': 'ja',
}}
'''

# 分析（.qmd）が出す値の代わり。Quarto も R も呼ばずに、差し込みだけを試す。
VALUES = '''\
{
  "n_obs": 1523,
  "coef_x": 0.342,
  "p_x": "< .001"
}
'''


def _placeholder_png(path: Path) -> None:
    from .scaffold import write_placeholder_png
    write_placeholder_png(path)


def _placeholder_pdf(path: Path) -> None:
    from .scaffold import write_placeholder_pdf
    write_placeholder_pdf(path)


# ---------------------------------------------------------------- 検査

def _docx_text(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read('word/document.xml').decode('utf-8', 'replace')
        return re.sub(r'<[^>]+>', '', xml)
    except (OSError, KeyError, zipfile.BadZipFile) as e:
        return t('(cannot read it: {error})', error=e)


def _sample(text: str, pat: str, n: int = 1) -> list:
    return [' '.join(m.split())[:110] for m in re.findall(pat, text)][:n]


CHECKS = {
    'latex': [
        ('the analysis values are filled in',
         lambda t: '1,523' in t and '{{n_obs}}' not in t),
        ('citations are resolved', lambda t: '@smith2003' not in t and 'Smith' in t),
        ('the bibliography is there', lambda t: 'CSLReferences' in t),
        ('cross-references are \\ref', lambda t: r'第\ref{sec-analysis}節' in t
         and r'式\eqref{eq-model}' in t),
        ('the figure is in, with its label', lambda t: r'\label{fig-trend}' in t),
        ('the labelled equation is numbered', lambda t: r'\begin{equation}' in t),
    ],
    'typst': [
        ('the analysis values are filled in',
         lambda t: '1,523' in t and '{{n_obs}}' not in t),
        ('citations are resolved by CSL',
         lambda t: '@smith2003' not in t and '#cite(' not in t and 'Smith' in t),
        ('cross-references are #ref(<label>)',
         lambda t: '#ref(<sec-analysis>)' in t and '#ref(<eq-model>)' in t),
        ('the figure, table and equation carry their labels',
         lambda t: '<fig-trend>' in t and '<tbl-desc>' in t and '<eq-model>' in t),
    ],
    'typst-slides': [
        ('the analysis values are filled in',
         lambda t: '1,523' in t and '{{n_obs}}' not in t),
        ('citations are resolved by CSL',
         lambda t: '#cite(' not in t and 'Smith' in t),
        ('the layout template is included', lambda t: '#let octavo = (' in t),
        ('the speaker notes are dropped', lambda t: '#octavo-note[' not in t),
    ],
    'typst-notes': [
        # 台本はスライドの絵（組んだデッキの各ページ）と、その下のノートだけを持つ
        ('the layout template is included', lambda t: '#let octavo = (' in t),
        ('the slides are placed as pictures', lambda t: '#octavo-script(' in t),
        ('the speaker notes are kept', lambda t: '#octavo-note[' in t),
    ],
    'beamer': [
        ('the analysis values are filled in',
         lambda t: '1,523' in t and '{{n_obs}}' not in t),
        ('frames are created', lambda t: r'\begin{frame}' in t),
        ('citations are resolved', lambda t: '@smith2003' not in t and 'Smith' in t),
    ],
    'docx': [
        ('the analysis values are filled in',
         lambda t: '1,523' in t and '{{n_obs}}' not in t),
        ('citations are resolved', lambda t: 'Smith' in t and '@smith2003' not in t),
        ('the bibliography is there', lambda t: 'Journal of Examples' in t),
        ('the Japanese text is there', lambda t: '山田' in t),
        ('numbers are written in (Word does not number)',
         lambda t: '図2.1' in t and '表2.1' in t and '(2.1)' in t),
    ],
}


REF_HEADS = ('参考文献', 'References', 'Bibliography', '文献')


def readable_citations(cfg, doc, offline: bool) -> tuple:
    """(本文で引用を含む段落, 文献一覧の項目)。Word の出力を pandoc で文章に戻して読む。"""
    r = buildmod.build_one(cfg, doc, 'docx', offline=offline)
    if not r.ok or not r.outputs:
        raise RuntimeError('; '.join(r.report[-2:]) or 'docx')
    plain = pandocrun.run('', ['-f', 'docx', '-t', 'plain', '--wrap=none', str(r.outputs[0])],
                          quiet=True)
    paras = [' '.join(p.split()) for p in re.split(r'\n\s*\n', plain) if p.strip()]
    at = max((i for i, p in enumerate(paras) if p in REF_HEADS), default=len(paras))
    keys = ('Smith', '山田', 'Example Organization')
    text = [p for p in paras[:at] if any(k in p for k in keys)]
    return text, paras[at + 1:]


def show_citations(cfg, doc, csl: str, offline: bool) -> None:
    import textwrap
    print('== ' + t('How the citations read (CSL {csl}, as typeset)', csl=csl))
    try:
        text, refs = readable_citations(cfg, doc, offline)
    except Exception as e:                       # 見せられなくても、検査の結果は出す
        print('   ' + t('could not show them: {why}', why=e) + '\n')
        return
    for head, items in ((t('In the text'), text), (t('Bibliography'), refs)):
        print(f'   {head}:')
        for p in items:
            print(textwrap.fill(p, width=96, initial_indent='     ', subsequent_indent='       '))
    print()


def run(targets=None, csl: str = 'chicago-author-date', keep: bool = False,
        offline: bool = False) -> int:
    tmp = Path(tempfile.mkdtemp(prefix='octavo-selftest-'))
    proj = tmp / 'selftest'
    (proj / 'assets' / 'figures').mkdir(parents=True)
    (proj / 'draft.md').write_text(DRAFT, encoding='utf-8')
    (proj / 'literature.bib').write_text(BIB, encoding='utf-8')
    (proj / 'octavo.config.py').write_text(CONFIG.format(csl=csl), encoding='utf-8')
    (proj / 'assets' / 'values').mkdir()
    (proj / 'assets' / 'values' / 'selftest.json').write_text(VALUES, encoding='utf-8')
    _placeholder_png(proj / 'assets' / 'figures' / 'trend.png')
    _placeholder_pdf(proj / 'assets' / 'figures' / 'trend.pdf')

    cfg = configmod.load(proj / 'octavo.config.py')
    doc = cfg.document('paper')

    print(f'pandoc {pandocrun.version_str()} / CSL {csl}')
    print(t('working in: {path}', path=proj) + '\n')

    names = targets or list(be.ALL)
    ng = 0
    for name in names:
        backend = be.get(name)
        print(f'== {name}  ({t(backend.label)})')
        if not pandocrun.at_least(*backend.min_pandoc):
            print('   ' + t('skipped: needs pandoc {ver} or newer',
                            ver='.'.join(map(str, backend.min_pandoc))) + '\n')
            continue
        r = buildmod.build_one(cfg, doc, name, offline=offline)
        if not r.ok:
            ng += 1
            for line in r.report:
                if line.startswith(tag('stopped')):
                    print('   ' + line)
            print()
            continue

        out = r.outputs[0]
        text = _docx_text(out) if name == 'docx' else \
            out.read_text(encoding='utf-8', errors='replace')

        for label, fn in CHECKS.get(name, []):
            ok = False
            try:
                ok = bool(fn(text))
            except Exception:
                ok = False
            ng += not ok
            print(f'   [{"ok" if ok else "NG"}] {t(label)}')

        print(f'   -> {out}  ({out.stat().st_size:,} bytes)\n')

    # 本題: 引用と文献一覧が、組み上がりでどう読めるか。形式ごとのソースの断片ではなく、
    # Word の出力（pandoc だけで作れる）を文章に戻して、そのまま見せる
    show_citations(cfg, doc, csl, offline)

    if keep:
        print(t('kept: {path}', path=proj))
    else:
        shutil.rmtree(tmp, ignore_errors=True)
    print(t('nothing wrong') if not ng else t('{n} to look at', n=ng))
    return 1 if ng else 0
