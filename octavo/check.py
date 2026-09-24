# -*- coding: utf-8 -*-
"""引用キーと書誌（.bib）の突き合わせ。

    octavo checkbib
    octavo checkbib --list      引いている文献を一覧する
    octavo checkbib --unused    .bib にあって引いていないものも出す
    octavo checkbib --json      機械可読（VS Code 拡張などが読む）

見るもの:

  1. 本文が引いているキーが .bib にあるか（**無ければ組版で ?? になる**）
  2. .bib の記述が壊れていないか（年なし・団体名が姓名に割れている・ページなし）
  3. 同じ文献が二重に入っていないか（Zotero の取り込み事故）

書誌の正本は Zotero。**このツールは .bib を書き換えない。**
承知のうえで直さない項目は octavo.config.py の `bib_accepted` に書く。

`collect()` が検査そのもの（構造化データを返す）で、`run()`（文字で表示）と
`run_json()`（JSON で吐く）はその結果を整形して出すだけ。**判定ロジックは
1箇所にしか無い**ので、`octavo checkbib` と VS Code 拡張の診断が食い違わない。
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import bib as bibmod
from . import md as mdlib
from .i18n import t, tag


@dataclass
class Entry:
    key: str
    type: str
    authors: str            # 表示用に組み立てた著者（narrative_authors）
    year: str
    title: str


@dataclass
class Problem:
    key: str
    issue: str
    detail: str = ''
    accepted: bool = False
    reason: str = ''         # accepted のときの bib_accepted の理由


@dataclass
class Report:
    bib_file: str
    entry_count: int
    entries: dict = field(default_factory=dict)        # key -> Entry
    cited: list = field(default_factory=list)           # 重複を除いた引用キー
    cited_by_doc: dict = field(default_factory=dict)    # 原稿の相対パス -> [key, …]
    missing: list = field(default_factory=list)         # cited だが .bib に無い
    suggestions: dict = field(default_factory=dict)     # missing key -> 近いキー
    duplicates: list = field(default_factory=list)      # [[key, key], …]
    problems: list = field(default_factory=list)        # list[Problem]（未承知のみ）
    accepted: list = field(default_factory=list)        # list[Problem]（承知のうえ）
    unused: list = field(default_factory=list)          # .bib にあって引いていない

    @property
    def problem_count(self) -> int:
        return len(self.missing) + len(self.problems)

    def to_json(self) -> dict:
        d = asdict(self)
        return d


def collect(cfg) -> Report:
    bib_path = Path(cfg['bib_file'])
    entries = bibmod.parse(bib_path)

    per_doc: dict = {}
    cited: set = set()
    for _, src, _ in cfg.sources():
        k = mdlib.cited_keys(mdlib.read(src))
        per_doc[cfg.rel(src)] = sorted(k)
        cited |= k

    r = Report(bib_file=str(bib_path), entry_count=len(entries),
               cited=sorted(cited), cited_by_doc=per_doc)

    for k, e in entries.items():
        r.entries[k] = Entry(key=k, type=e.get('type', ''),
                             authors=bibmod.narrative_authors(e),
                             year=bibmod.year(e),
                             title=e.get('title', '')).__dict__

    r.missing = sorted(k for k in cited if k not in entries)
    r.suggestions = {k: s for k in r.missing if (s := _near(k, entries))}

    r.duplicates = [list(p) for p in bibmod.duplicates(entries)]

    bad, accepted = bibmod.problems(entries, cited, cfg['bib_accepted'])
    r.problems = [Problem(key=k, issue=t(w), detail=d).__dict__
                  for k, w, d in bad]
    r.accepted = [Problem(key=k, issue=t(w), detail=d, accepted=True,
                          reason=bibmod.accepted_reason(cfg['bib_accepted'], k, w) or '').__dict__
                 for k, w, d in accepted]

    r.unused = sorted(set(entries) - cited)
    return r


# ---------------------------------------------------------------- 匿名審査

def self_citations(cfg) -> list:
    """本文が引いている文献のうち、**著者に自分が入っているもの**を返す。

    匿名審査では自己引用を "Author (2023)" などに伏せることが多い。どれを
    伏せるかは雑誌の規定と本人の判断なので、ここは**候補を挙げるだけ**。

    突き合わせるのは姓だけ（`meta.author` の最後の語、日本語なら先頭の姓）。
    同姓の別人を拾うことはあるが、**見落とすより挙げすぎるほうが安全**。
    """
    names = cfg['meta'].get('author') or []
    if isinstance(names, str):
        names = [names]
    mine = set()
    for full in names:
        parts = str(full).replace('\u3000', ' ').split()
        if not parts:
            continue
        mine.add(parts[0])          # 日本語（姓が先）
        mine.add(parts[-1])         # 英語（姓が後）
    if not mine:
        return []

    entries = bibmod.parse(Path(cfg['bib_file']))
    cited: set = set()
    for _, src, _ in cfg.sources():
        cited |= mdlib.cited_keys(mdlib.read(src))
    out = []
    for key in sorted(cited):
        e = entries.get(key)
        if e and (set(bibmod.surnames(e)) & mine):
            out.append(key)
    return out


# ---------------------------------------------------------------- 文字で表示

def run(cfg, show_list: bool = False, show_unused: bool = False) -> int:
    r = collect(cfg)
    if not r.entries:
        print(t('the bibliography is unreadable or empty: {path}', path=r.bib_file))
        return 1

    print(f'{Path(r.bib_file).name}: ' + t('{n} {n|entry|entries}', n=r.entry_count))
    for fname, keys in r.cited_by_doc.items():
        print(f'  {fname}: ' + t('{n} {n|citation|citations}', n=len(keys)))
    print(t('total (without duplicates): {n}', n=len(r.cited)))

    if r.missing:
        print('\n' + tag('fatal') + ' '
              + t('{n} {n|key is|keys are} not in the .bib — {n|it typesets|they typeset} as ??', n=len(r.missing)))
        for k in r.missing:
            near = r.suggestions.get(k, '')
            print(f'   {k}' + ('   ' + t('did you mean: {key}', key=near) if near else ''))

    if r.duplicates:
        print('\n' + tag('careful') + ' '
              + t('{n} {n|pair looks|pairs look} like the same reference twice', n=len(r.duplicates)))
        for a, b in r.duplicates:
            print(f'   {a}  /  {b}')

    if r.problems:
        print('\n' + tag('bib flaws') + ' '
              + t('{n} — fix {n|it|them} in Zotero and export again', n=len(r.problems)))
        for p in r.problems:
            print(f'   {p["key"]:<28} {p["issue"]}  {p["detail"]}')
    if r.accepted:
        print('\n' + tag('accepted') + ' '
              + t('{n} — listed in bib_accepted as not worth fixing', n=len(r.accepted)))
        for p in r.accepted:
            print(f'   {p["key"]:<28} {p["issue"]}  … {p["reason"]}')

    if show_unused:
        print('\n' + tag('unused') + ' '
              + t('{n} {n|is|are} in the .bib but never cited ({n|it does|they do} not reach the output)',
                  n=len(r.unused)))
        for k in r.unused[:60]:
            e = r.entries[k]
            print(f'   {k:<28} {e["authors"]} {e["year"]}')
        if len(r.unused) > 60:
            print('   ' + t('… and {n} more', n=len(r.unused) - 60))

    if show_list:
        print('\n' + t('References cited:'))
        for k in r.cited:
            e = r.entries.get(k)
            if e:
                print(f'   {k:<28} {e["authors"]:<26} {e["year"]}  {e["title"][:44]}')
            else:
                print(f'   {k:<28} ?')

    print('\n' + (t('nothing wrong') if not r.problem_count
                  else t('{n} to deal with', n=r.problem_count)))
    return 1 if r.missing else 0


def run_json(cfg) -> int:
    r = collect(cfg)
    print(json.dumps(r.to_json(), ensure_ascii=False, indent=None))
    return 1 if r.missing else 0


def _near(key: str, entries: dict) -> str:
    """打ち間違いらしきキーの候補を1つだけ出す。"""
    import difflib
    m = difflib.get_close_matches(key, list(entries), n=1, cutoff=0.75)
    return m[0] if m else ''
