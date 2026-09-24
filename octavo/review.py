# -*- coding: utf-8 -*-
"""`octavo review <戻ってきた.docx>` — 共著者の赤入れを一覧にする。

    octavo review 20260907_draft_tanaka.docx
    octavo review コメントだけ.docx --comments

共著者は Word で直して返してくる。いまのところ、それを `draft.md` に移すのは
目で見て手で写す作業だった。ここはその作業の**入力側**を作る。

**往復変換はしない。**戻ってきた `.docx` の中では `{{n_obs}}` が既に
`1,523` という文字になっている。docx → md で書き戻すと、このツールの中心
（数値の出所を1つに保つ）がその瞬間に壊れる。だから**変更履歴とコメントだけ
を取り出して見せる**。反映は人が `draft.md` 側で行う。それが唯一安全な
戻し方で、この設計はその判断の結果。

読み方は `.docx` の中身（zip）を直接見る。pandoc も外部パッケージも要らない
（`selftest.py` が既に同じ手で `word/document.xml` を読んでいる）。

    word/document.xml   w:ins（挿入）/ w:del（削除）/ コメントの位置
    word/comments.xml   コメントの本文と書いた人
"""
from __future__ import annotations

import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from xml.etree import ElementTree
from .i18n import language, t

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


class DocxError(Exception):
    pass


@dataclass
class Change:
    kind: str            # 'ins' | 'del' | 'comment'
    author: str
    date: str
    text: str

    def label(self) -> str:
        return {'ins': t('inserted'), 'del': t('deleted'),
                'comment': t('comment')}[self.kind]


@dataclass
class Para:
    """1段落ぶんの赤入れ。"""
    index: int                                   # 何段落目か（1 始まり）
    context: str                                 # その段落（変更を反映した読み）
    changes: list = field(default_factory=list)  # list[Change]


def _text_of(el) -> str:
    """要素の下にある w:t / w:delText を拾って繋ぐ。"""
    out = []
    for node_el in el.iter():
        if node_el.tag in (f'{W}t', f'{W}delText') and node_el.text:
            out.append(node_el.text)
    return ''.join(out)


def _read_comments(z: zipfile.ZipFile) -> dict:
    """{コメント id: Change} を返す。comments.xml が無ければ空。"""
    try:
        xml = z.read('word/comments.xml')
    except KeyError:
        return {}
    out: dict = {}
    for c in ElementTree.fromstring(xml).iter(f'{W}comment'):
        cid = c.get(f'{W}id', '')
        out[cid] = Change(kind='comment',
                          author=c.get(f'{W}author', t('(unknown)')),
                          date=(c.get(f'{W}date', '') or '')[:16].replace('T', ' '),
                          text=' '.join(_text_of(c).split()))
    return out


def collect(path: Path) -> list:
    """docx を読んで list[Para] を返す。変更もコメントも無い段落は入れない。"""
    if not path.is_file():
        raise DocxError(t('no such file: {path}', path=path))
    try:
        with zipfile.ZipFile(path) as z:
            comments = _read_comments(z)
            body = ElementTree.fromstring(z.read('word/document.xml'))
    except (OSError, KeyError, zipfile.BadZipFile, ElementTree.ParseError) as e:
        raise DocxError(t('cannot read {path} as a .docx ({why})',
                          path=path, why=e)) from e

    out: list = []
    for i, para in enumerate(body.iter(f'{W}p'), start=1):
        changes: list = []
        parts: list = []                 # 変更を反映した読み（挿入を含み削除を除く）
        for node in para:
            if node.tag == f'{W}ins':
                txt = _text_of(node)
                if txt.strip():
                    changes.append(Change('ins', node.get(f'{W}author', t('(unknown)')),
                                          (node.get(f'{W}date', '') or '')[:16]
                                          .replace('T', ' '), txt))
                parts.append(txt)
            elif node.tag == f'{W}del':
                txt = _text_of(node)
                if txt.strip():
                    changes.append(Change('del', node.get(f'{W}author', t('(unknown)')),
                                          (node.get(f'{W}date', '') or '')[:16]
                                          .replace('T', ' '), txt))
            elif node.tag == f'{W}commentRangeStart':
                cid = node.get(f'{W}id', '')
                if cid in comments and comments[cid] not in changes:
                    changes.append(comments[cid])
            else:
                # 範囲を持たないコメントは w:r の中の commentReference だけ。
                # w:r もそれ以外も同じ扱いにして、拾い漏らさないようにする。
                for ref in node.iter(f'{W}commentReference'):
                    cid = ref.get(f'{W}id', '')
                    if cid in comments and comments[cid] not in changes:
                        changes.append(comments[cid])
                parts.append(_text_of(node))

        if changes:
            out.append(Para(index=i, context=' '.join(''.join(parts).split()),
                            changes=changes))
    return out


def authors(paras: list) -> dict:
    """{書いた人: 件数}。誰がどれだけ入れたかを先に見せる。"""
    counts: dict = {}
    for p in paras:
        for c in p.changes:
            counts[c.author] = counts.get(c.author, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


# ---------------------------------------------------------------- 表示

WARNING_LINES = (
    'This list is **for reading**. Do not copy the docx back into the manuscript.',
    'In the returned docx, {{n_obs}} is already the literal text "1,523";',
    'writing it back pins the number into the manuscript (and breaks what this tool is for).',
    'Make the edits in the .md, and change numbers in the .qmd.',
)


def run(path: Path, only: str = '', quiet: bool = False) -> int:
    try:
        paras = collect(path)
    except DocxError as e:
        print(str(e))
        return 1

    if only:
        paras = [Para(p.index, p.context, [c for c in p.changes if c.kind == only])
                 for p in paras]
        paras = [p for p in paras if p.changes]

    if not paras:
        print(f'{path.name}: ' + t('no tracked changes and no comments'))
        print('  ' + t("without Word's Track Changes on, edits leave no trace"))
        return 0

    n = sum(len(p.changes) for p in paras)
    print(f'{path.name}: ' + t('{n} {n|change|changes} in {paras} {paras|paragraph|paragraphs}',
                                n=n, paras=len(paras)))
    who = authors(paras)
    if who:
        sep = '、' if language() == 'ja' else ', '
        print('  ' + sep.join(t('{who}: {n}', who=a, n=c) for a, c in who.items()))
    print()

    for p in paras:
        print('  ' + t('paragraph {n}', n=p.index) + f': {p.context[:76]}')
        for c in p.changes:
            head = f'    [{c.label()}] {c.author}'
            print(head + (f'  {c.date}' if c.date else ''))
            print(f'      {c.text[:120]}')
        print()

    if not quiet:
        print('\n'.join('  ' + t(line) for line in WARNING_LINES))
    return 0


def as_json(path: Path) -> list:
    return [asdict(p) for p in collect(path)]
