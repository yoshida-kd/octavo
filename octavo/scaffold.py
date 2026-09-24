# -*- coding: utf-8 -*-
"""`octavo init` — プロジェクトのひな型を作る。`octavo new` — 原稿を足す。

    octavo init 2026-研究                 分析・書誌・手順書の一式（原稿は無し）
    octavo new paper example-paper          papers/example-paper/paper.md（+ appendix.md, main.*）
    octavo new slides example-talk            slides/example-talk.md
    octavo new lecture 講義の見本          lectures/講義の見本.md（プリント1本 + 回ごとのスライド）

論文・スライド・講義の違いは**原稿のテンプレート**（templates/manuscripts/<言語>/*.md）と、
設定の documents に書く扱い（profile・targets）だけ。プロジェクトの形は1つで、
どの種類の原稿も何本でも同じリポジトリに置ける。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from . import tmpl
from .i18n import t



# ---------------------------------------------------------------- 原稿の種類
# `octavo new <種類>` が置く場所と、init が設定に書くグロブは**この表から作る**。
# 片方だけ書き換えて「足したのに登録されない」事故を起こさないため。

KINDS = {
    'paper': {
        'group': 'papers',
        'src': 'papers/{}/paper.md',
        'appendix': 'papers/{}/appendix.md',
        'profile': 'paper',
        'targets': ['typst'],
        'comment': {'ja': ['論文。付録・体裁（main.typ / main.tex）は同じフォルダに置く',
                           "Word も出すなら targets に 'docx' を足す"],
                    'en': ['Papers. The appendix and the layout (main.typ / main.tex) sit in the same folder',
                           "add 'docx' to targets for Word as well"]},
    },
    'slides': {
        'group': 'slides',
        'src': 'slides/{}.md',
        'profile': 'slides',
        'targets': ['typst-slides'],
        'comment': {'ja': ['発表スライド'], 'en': ['Talk slides']},
    },
    'lecture': {
        'group': 'lectures',
        'src': 'lectures/{}.md',
        'profile': 'handout',
        'targets': ['typst', 'typst-slides'],
        'split_slides': True,
        'comment': {'ja': ['講義ノート。A4 プリントは1本、スライドは `#` の回ごとに <名前>-01, -02, …'],
                    'en': ['Lecture notes. One A4 handout, and a deck per `#` session: <name>-01, -02, …']},
    },
}


DOCUMENTS_HEAD = {
    'ja': ["    # octavo new paper|slides|lecture <名前> で原稿を足す。ここは書き換えなくてよい",
           "    # （グロブに当たった原稿がそれぞれ1つの文書になり、名前は `*` の部分）"],
    'en': ["    # Add manuscripts with octavo new paper|slides|lecture <name>; no need to edit this",
           "    # (each file a glob matches is one document, named after what `*` matched)"],
}


def documents_block(lang: str = 'ja') -> str:
    """設定の `documents` の部分。KINDS から作る（`@@DOCUMENTS@@` に入る）。"""
    lang = 'ja' if lang == 'ja' else 'en'
    lines = DOCUMENTS_HEAD[lang] + ["    'documents': {"]
    for kind, k in KINDS.items():
        lines += [f"        # {c}" for c in k['comment'][lang]]
        body = [f"'src': '{k['src'].format('*')}'"]
        if k.get('appendix'):
            body.append(f"'appendix': '{k['appendix'].format('*')}'")
        body += [f"'profile': '{k['profile']}'", f"'targets': {k['targets']!r}"]
        if k.get('split_slides'):
            body.append("'split_slides': True")
        lines.append(f"        '{k['group']}': {{")
        lines += [f'            {b},' for b in body]
        lines.append('        },')
    lines.append('    },')
    return '\n'.join(lines)


# ---------------------------------------------------------------- 仮の図
# 図がまだ無い段階でも `octavo build --compile` が最後まで通るように、
# 中身の無い図を置いておく。外部ライブラリは使わない。
#
# **仮の図だと分かるようにしてある。**組んだ PDF を見た人には対角線の × で、
# `octavo check` には埋め込んだ印（PNG は tEXt チャンク、PDF はコメント行）で
# 伝わる。差し替えれば印ごと消えるので、残っていれば仮のままということ。

PLACEHOLDER_MARK = 'octavo:placeholder'


def is_placeholder(path: Path) -> bool:
    """octavo init が置いた仮の図のままか。読めなければ False。"""
    try:
        head = path.read_bytes()[:4096]
    except OSError:
        return False
    return PLACEHOLDER_MARK.encode() in head

def write_placeholder_png(path: Path, w: int = 960, h: int = 540) -> Path:
    import struct
    import zlib

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack('>I', len(data)) + tag + data
                + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff))

    # 枠と、隅から隅への × 2本。組んだものを見れば仮の図だと一目で分かる
    rows = bytearray()
    for y in range(h):
        rows.append(0)                                  # filter type: None
        for x in range(w):
            edge = x < 3 or y < 3 or x >= w - 3 or y >= h - 3
            # 2本の対角線（太さは高さに対する許容幅で出す）
            cross = (abs(y * w - x * h) < w * 2
                     or abs(y * w - (w - x) * h) < w * 2)
            v = 150 if (edge or cross) else 235
            rows += bytes((v, v, v))
    # tEXt チャンクに印を入れる（画には出ないが、check が読める）
    text = b'Comment\x00' + PLACEHOLDER_MARK.encode()
    png = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
           + chunk(b'tEXt', text)
           + chunk(b'IDAT', zlib.compress(bytes(rows), 6))
           + chunk(b'IEND', b''))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)
    return path


def write_placeholder_pdf(path: Path, w: int = 480, h: int = 270) -> Path:
    """1ページだけの最小の PDF（枠・×・説明文字）。xref の位置は自分で数える。"""
    content = (f'0.6 w 0.55 0.55 0.55 RG\n4 4 {w - 8} {h - 8} re S\n'
               f'4 4 m {w - 4} {h - 4} l S\n'
               f'4 {h - 4} m {w - 4} 4 l S\n'
               'BT /F1 12 Tf 0.35 0.35 0.35 rg '
               f'{w / 2 - 62:.0f} {h / 2 - 4:.0f} Td (placeholder figure) Tj ET\n')
    objs = [
        '<</Type/Catalog/Pages 2 0 R>>',
        '<</Type/Pages/Kids[3 0 R]/Count 1>>',
        f'<</Type/Page/Parent 2 0 R/MediaBox[0 0 {w} {h}]'
        '/Resources<</Font<</F1 5 0 R>>>>/Contents 4 0 R>>',
        f'<</Length {len(content)}>>stream\n{content}endstream',
        '<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>',
    ]
    # 先頭のコメントが check の読む印（PDF の文法上ただのコメント）
    out = f'%PDF-1.4\n%{PLACEHOLDER_MARK}\n'
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f'{i} 0 obj\n{body}\nendobj\n'
    xref_at = len(out)
    out += f'xref\n0 {len(objs) + 1}\n0000000000 65535 f \n'
    out += ''.join(f'{o:010d} 00000 n \n' for o in offsets)
    out += (f'trailer\n<</Size {len(objs) + 1}/Root 1 0 R>>\n'
            f'startxref\n{xref_at}\n%%EOF\n')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(out.encode('latin-1'))
    return path


# ---------------------------------------------------------------- 実行

def render(text: str, subs: dict, markdown: bool = False) -> str:
    """`@@NAME@@` を差し替える。

    ひな型は `{}` を多く含むので（`{{n_obs}}`、`\\label{}`、設定の辞書）
    str.format は使わず、`@@名前@@` の置換にしてある。
    """
    for k, v in subs.items():
        text = text.replace(f'@@{k}@@', v)
    return re.sub(r'\n{3,}', '\n\n', text) if markdown else text


def render_template(name: str, subs: dict, root: Path | None = None) -> str:
    """ひな型を1つ読んで差し替える（上書きがあればそちら。tmpl.py）。"""
    return render(tmpl.read(name, root), subs, name.endswith('.md'))


def project_target(rel: str) -> str:
    """`project/<言語>/` の中の名前から、プロジェクトに書く名前へ。

    `gitignore` -> `.gitignore`（本物の .gitignore をひな型の木に置くと、
    Octavo 自身のリポジトリでそれが効いてしまう）、末尾の `.tmpl` は外す
    （`octavo.config.py.tmpl` は `@@DOCUMENTS@@` のせいで Python として読めない）。
    """
    parts = rel.split('/')
    if parts[-1] == 'gitignore':
        parts[-1] = '.gitignore'
    if parts[-1].endswith('.tmpl'):
        parts[-1] = parts[-1][:-len('.tmpl')]
    return '/'.join(parts)


def _write(p: Path, text: str, force: bool, made: list,
           root: Path | None = None) -> None:
    def show() -> str:
        try:
            return p.relative_to(root).as_posix() if root else p.name
        except ValueError:
            return p.name
    if p.exists() and not force:
        made.append('  ' + t('left alone') + f'  {show()} ' + t('(already there)'))
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')
    made.append('  ' + t('made') + f'  {show()}')



def init(dest: Path, lang: str = 'ja', force: bool = False,
         quiet: bool = False) -> int:
    """プロジェクトの共通部分を作る。原稿は置かない（`octavo new` で足す）。"""
    dest = dest.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    made: list = []
    name = dest.name

    # プロジェクトの木（templates/project/common + project/<言語>）をそのまま写す。
    # ユーザーの上書き（~/.config/octavo/templates/project/…）も同じ木に重なる。
    suffix = 'ja' if lang == 'ja' else 'en'
    subs = {'NAME': name, 'DOCUMENTS': documents_block(suffix)}
    for rel, src in tmpl.tree(['project/common', f'project/{suffix}']).items():
        text = render(src.read_text(encoding='utf-8'), subs, rel.endswith('.md'))
        _write(dest / project_target(rel), text, force, made, dest)
    for d in ('figures', 'tables', 'data/derived'):
        (dest / d).mkdir(parents=True, exist_ok=True)
        (dest / d / '.gitkeep').touch()

    # 原稿のテンプレートが参照している図。差し替える前でも組版が通るように置いておく。
    if not (dest / 'figures' / 'fig1_trend.png').exists() or force:
        write_placeholder_png(dest / 'figures' / 'fig1_trend.png')
        write_placeholder_pdf(dest / 'figures' / 'fig1_trend.pdf')
        made.append('  ' + t('made')
                    + '  ' + t('figures/fig1_trend.png (and .pdf — placeholders)'))

    if quiet:
        return 0
    print(t('Wrote a project skeleton in {path}:', path=dest))
    for m in made:
        print(m)
    print('\n' + t('Next:'))
    print(f'  cd {dest}')
    print('  octavo doctor'.ljust(38) + '# ' + t('see whether the tools are there'))
    print('  python3 -m venv .venv && source .venv/bin/activate'.ljust(38)
          + '   # ' + t('the analysis environment (Python)'))
    print("  Rscript -e 'renv::init()'".ljust(38) + '# ' + t('the analysis environment (R)'))
    print(('  octavo new paper <' + t('name') + '>').ljust(38)
          + '# ' + t('add a manuscript (as many as you like)'))
    print('  octavo new slides <' + t('name') + '>')
    print('  octavo new lecture <' + t('name') + '>')
    print('  ' + t('(put the raw data in data/raw/ and say where it came from in '
                   'data/raw/README.md)'))
    print('  ' + t('(rewrite analysis/analysis.qmd as your own analysis)'))
    print('  octavo build'.ljust(38) + '# '
          + t('build it (a stale analysis runs first)'))
    print('\n  ' + t('The working rules are in CLAUDE.md, the walkthrough in README.md.'))
    return 0


# ---------------------------------------------------------------- 原稿を足す

NAME_OK = re.compile(r'[^\s/\\.][^\s/\\]*')


def new(config: Path, kind: str, name: str, force: bool = False,
        quiet: bool = False) -> int:
    """原稿を1本足す。octavo.config.py は書き換えない（init が書いたグロブが拾う）。"""
    from . import config as configmod
    if kind not in KINDS:
        print(t('unknown kind: {kind} (one of {allowed})',
                kind=kind, allowed=' / '.join(KINDS)), file=sys.stderr)
        return 1
    if not NAME_OK.fullmatch(name):
        print(t('that name will not do: {name} (no spaces, no / or \\, and it '
                'cannot start with a dot)', name=repr(name)), file=sys.stderr)
        return 1
    cfg = configmod.load(config)
    k = KINDS[kind]
    root = cfg.root
    src = root / k['src'].format(name)
    if name in cfg.documents and not (force and cfg.documents[name].src == src.resolve()):
        print(t('a document called {name} already exists ({path})',
                name=name, path=cfg.rel(cfg.documents[name].src)) + '\n  '
              + t('octavo build <name> could not tell them apart — pick another'),
              file=sys.stderr)
        return 1

    lang = 'ja' if cfg['lang'] == 'ja' else 'en'
    author = cfg['meta'].get('author') or ''
    if isinstance(author, (list, tuple)):
        author = author[0] if author else ''
    subs = {'NAME': name, 'AUTHOR': str(author)}
    made: list = []
    _write(src, render_template(f'manuscripts/{lang}/{kind}.md', subs, root),
           force, made, root)
    if k.get('appendix'):
        _write(root / k['appendix'].format(name),
               render_template(f'manuscripts/{lang}/appendix.md', subs, root),
               force, made, root)

    # 足した原稿を設定が本当に拾うかを、読み直して確かめる
    cfg = configmod.load(config)
    doc = cfg.documents.get(name)
    if doc is None:
        made.append('  ' + t('note') + '  ' + t(
            'documents in octavo.config.py is not picking up {glob} — check it',
            glob=k['src'].format('*')))
    elif k['profile'] == 'paper':
        # 論文の体裁（投稿先ごとに手で書く）。**原稿と同じフォルダ**に置く。
        # 組版のたびに build/ へ写されるので、build/ は丸ごと消してよい。
        for ext in ('.typ', '.tex'):
            try:
                text = tmpl.read(f'paper/{lang}/main{ext}', root)
            except tmpl.TemplateError:
                continue
            _write(src.parent / f'main{ext}', text, force, made, root)

    if quiet:
        return 0
    for m in made:
        print(m)
    print('\n' + t('Next:'))
    steps = {
        'lecture': [(f'octavo build {name} --to typst --compile',
                     t('the A4 handout, through to PDF')),
                    (f'octavo build {name} --to typst-slides --compile',
                     t('the slides, one PDF per session')),
                    (f'octavo build {name}-01 --to typst-slides',
                     t('just one session'))],
        'slides': [(f'octavo build {name} --compile', t('the slides, through to PDF'))],
        'paper': [(f'octavo build {name} --compile',
                   t('typeset main.typ through to PDF')),
                  (f'octavo build {name} --to docx',
                   t('a Word file for your coauthors'))],
    }[kind]
    width = max(len(c) for c, _ in steps)
    for cmd, why in steps:
        print(f'  {cmd.ljust(width)}   # {why}')
    return 0
