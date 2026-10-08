# -*- coding: utf-8 -*-
"""`octavo init` — プロジェクトの枠を作る。`octavo new` — 原稿や分析を足す。

    octavo init 2026-research             枠だけ（設定・書誌・AGENTS.md・README・figures/）
    octavo init study --with analysis,paper   分析と論文から始める（--all なら4つとも）
    octavo init demo --example            見本つき（仮のデータの分析と、見本の論文1本）
    octavo new analysis model             analysis/model.qmd（1本目は octavo.R・data/ なども）
    octavo new paper example-paper        papers/example-paper/paper.md と main.typ
                                          （--appendix で appendix.md、--tex で main.tex も）
    octavo new slides example-talk        slides/example-talk.md
    octavo new lecture example-lecture    lectures/example-lecture.md（プリント1本 + 回ごとのスライド）

既定で置くのは、後で消さずに使い続けるものだけ。見本（仮のデータ・仮の値・仮の図表・
見本の書誌・原稿の中の例）は --example のときだけ置く。AGENTS.md（と、それを読むだけの CLAUDE.md）は共通の節から
始まり、部品の種類を初めて足したときにその節（templates/claude/<言語>/）が足される。

論文・スライド・講義の違いは**原稿のテンプレート**（templates/manuscripts/<言語>/*.md）と、
設定の documents に書く扱い（profile・targets）だけ。どの種類の原稿も何本でも
同じリポジトリに置ける。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from . import md as mdlib
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
        'front': ['outputs: [pdf]'],
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
        'front': ['outputs: [slides]'],
        'comment': {'ja': ['発表スライド'], 'en': ['Talk slides']},
    },
    'lecture': {
        'group': 'lectures',
        'src': 'lectures/{}.md',
        'profile': 'handout',
        'targets': ['typst', 'typst-slides'],
        'split_slides': True,
        'front': ['outputs: [pdf, slides]', 'sessions: true'],
        'comment': {'ja': ['講義ノート。A4 プリントは1本、スライドは `#` の回ごとに <名前>-01, -02, …'],
                    'en': ['Lecture notes. One A4 handout, and a deck per `#` session: <name>-01, -02, …']},
    },
    # ポスターは docs/ の形にだけある（前からの置き場所はない。設定にも書かない）
    'poster': {
        'group': 'docs',
        'src': 'docs/{0}/{0}.md',
        'profile': 'poster',
        'targets': ['typst-poster'],
        'front': ['outputs: [poster]'],
        'docs_only': True,
        'comment': {'ja': [], 'en': []},
    },
}


# 新しい原稿の置き場所: docs/<名前>/<名前>.md（付録・体裁ファイルも同じフォルダ）
DOCS_SRC = 'docs/*/'

DOCUMENTS_HEAD = {
    'ja': ["    # octavo new paper|slides|lecture <名前> で原稿を足す。ここは書き換えなくてよい",
           "    # docs/<名前>/<名前>.md が1つの文書。何を作るかは原稿の冒頭の outputs: で決める",
           "    # （pdf / word / tex / slides / beamer / script）。その下の3つは前からの置き場所"],
    'en': ["    # Add manuscripts with octavo new paper|slides|lecture <name>; no need to edit this",
           "    # docs/<name>/<name>.md is one document; what it makes is outputs: in its front",
           "    # matter (pdf / word / tex / slides / beamer / script). The three below are the older places"],
}


def uses_docs(cfg) -> bool:
    """このプロジェクトの設定が docs/<名前>/ を登録しているか（新しい原稿をそこへ置くか）。"""
    return any(isinstance(d, dict) and str(d.get('src', '')).rstrip('/') == DOCS_SRC.rstrip('/')
               for d in cfg.doc_spec.values())


def doc_path(cfg, kind: str, name: str) -> Path:
    """`octavo new <kind> <name>` が原稿を置く場所。"""
    if uses_docs(cfg):
        return cfg.root / 'docs' / name / f'{name}.md'
    return cfg.root / KINDS[kind]['src'].format(name)


def appendix_path(cfg, kind: str, name: str) -> Path:
    if uses_docs(cfg):
        return cfg.root / 'docs' / name / 'appendix.md'
    return cfg.root / KINDS[kind]['appendix'].format(name)


def with_front(text: str, lines: list) -> str:
    """原稿の冒頭（front matter）の終わりに行を足す。もう書いてある鍵は足さない。"""
    m = re.match(r'---\n(.*?\n)---\n', text, re.S)
    if not m:
        return '---\n' + ''.join(f'{x}\n' for x in lines) + '---\n\n' + text
    have = {ln.split(':', 1)[0].strip() for ln in m.group(1).split('\n') if ':' in ln}
    add = ''.join(f'{x}\n' for x in lines if x.split(':', 1)[0].strip() not in have)
    return f'---\n{m.group(1)}{add}---\n' + text[m.end():]


def documents_block(lang: str = 'ja') -> str:
    """設定の `documents` の部分。KINDS から作る（`@@DOCUMENTS@@` に入る）。"""
    lang = 'ja' if lang == 'ja' else 'en'
    lines = DOCUMENTS_HEAD[lang] + ["    'documents': {",
                                    "        'docs': {",
                                    f"            'src': '{DOCS_SRC}',",
                                    '        },']
    for kind, k in KINDS.items():
        if k.get('docs_only'):
            continue
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
# 図がまだない段階でも `octavo build --compile` が最後まで通るように、
# 中身のない図を置いておく。外部ライブラリは使わない。
#
# **仮の図だと分かるようにしてある。**組んだ PDF を見た人には対角線の × で、
# `octavo check` には埋め込んだ印（PNG は tEXt チャンク、PDF はコメント行）で
# 伝わる。差し替えれば印ごと消えるので、残っていれば仮のままということ。

PLACEHOLDER_MARK = 'octavo:placeholder'


def is_placeholder(path: Path) -> bool:
    """octavo が置いた仮の図のままか。読めなければ False。"""
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



EXAMPLE_PAPER = 'example-paper'

# `init --with` / `--all` で選べる部品。名前を書かなければ部品の名前になる
# （paper なら papers/paper/）。分析を先に置くのは、原稿の見本がその値を使うから。
PARTS = ('analysis', 'paper', 'slides', 'lecture', 'poster')

# AGENTS.md の節（templates/claude/<言語>/<節>.md。置き場の名前は昔のまま）。スライドと講義ノートは同じ節。
# 部品を足したとき、その節がまだなければ末尾に書き足す（印で見分ける）。
CLAUDE_SECTION = {'analysis': 'analysis', 'paper': 'paper',
                  'slides': 'slides', 'lecture': 'slides', 'poster': 'poster'}
SECTION_MARK = '<!-- octavo:section {} -->'


def parse_parts(spec: str) -> dict:
    """`analysis,paper=mypaper` -> {'analysis': 'analysis', 'paper': 'mypaper'}。

    不明な部品や、使えない名前は ValueError（メッセージは表示用）。
    """
    out: dict = {}
    for item in filter(None, (s.strip() for s in spec.split(','))):
        kind, _, name = item.partition('=')
        kind, name = kind.strip(), (name.strip() or kind.strip())
        if kind not in PARTS:
            raise ValueError(t('unknown part: {part} (one of {allowed})',
                               part=kind, allowed=', '.join(PARTS)))
        out[kind] = name
    return out


def _lang(value) -> str:
    return 'ja' if value == 'ja' else 'en'


# プロジェクトの約束事（AI に読ませるもの）の正本は AGENTS.md。Claude Code・GitHub Copilot・
# OpenAI の Codex・Antigravity など、どれもこれを読む。CLAUDE.md は「AGENTS.md を読む」
# だけの1行（Claude 専用の約束があれば、利用者がそこへ足す）。
INSTRUCTIONS = 'AGENTS.md'


def _points_at_agents(text: str) -> bool:
    """AGENTS.md を読むだけの CLAUDE.md か（1行目が `@AGENTS.md`。下に説明のコメントがあってもよい）。"""
    first = next((ln.strip() for ln in text.splitlines() if ln.strip()), '')
    return first == '@AGENTS.md'


def instruction_file(root: Path) -> Path | None:
    """節を書き足す先。AGENTS.md があればそれ。なければ、CLAUDE.md に中身があれば
    それ（AGENTS.md ができる前のプロジェクト）。どちらもなければ（消してあれば）None。"""
    agents = root / INSTRUCTIONS
    if agents.is_file():
        return agents
    claude = root / 'CLAUDE.md'
    if claude.is_file() and not _points_at_agents(claude.read_text(encoding='utf-8')):
        return claude
    return None


def migrate_instructions(root: Path, lang: str, dry_run: bool = False) -> tuple:
    """一時的な移行（次の版で消す）: AGENTS.md ができる前のプロジェクトの CLAUDE.md を
    AGENTS.md に移し、CLAUDE.md は AGENTS.md を読むだけの1行にする。

    中身は1文字も変えずに移す（利用者が足した約束もそのまま）。戻り値は
    (動いたか, 表示用の1行)。すでに移してあるときと、CLAUDE.md がないときは何もしない。
    """
    claude, agents = root / 'CLAUDE.md', root / INSTRUCTIONS
    if agents.is_file():
        return False, t('AGENTS.md is already there, so there is nothing to move.')
    if not claude.is_file():
        return False, t('There is no CLAUDE.md, so there is nothing to move.')
    text = claude.read_text(encoding='utf-8')
    if _points_at_agents(text):
        return False, t('CLAUDE.md already only points at AGENTS.md.')
    if not dry_run:
        agents.write_text(text, encoding='utf-8')
        claude.write_text(render_template(f'claude/{_lang(lang)}/stub.md', {'NAME': root.name}, root),
                          encoding='utf-8')
    return True, t('Moved the rules from CLAUDE.md to AGENTS.md; CLAUDE.md now points at it.')


SECTION_LINE = re.compile(r'^<!-- octavo:section ([\w-]+) -->\s*$', re.M)


def rules_update(root: Path, lang: str) -> tuple:
    """約束事のファイル（AGENTS.md か、前からの CLAUDE.md）の Octavo の節を、今のひな型に
    差し替えた全文。(ファイル, 前の全文, 新しい全文, [差し替えた節]) か、ファイルがなければ None。

    節は `<!-- octavo:section X -->` の行から次の節の行（なければ末尾）まで。最初の節より
    前は残す。ひな型のない節（自分で付けた名前など）も残す。節の中に書き足したところは
    差し替えで消えるので、呼ぶ側が差分を見せる。
    """
    p = instruction_file(root)
    if p is None:
        return None
    old = p.read_text(encoding='utf-8')
    marks = list(SECTION_LINE.finditer(old))
    if not marks:
        return p, old, old, []
    out = [old[:marks[0].start()]]
    changed = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(old)
        part = old[m.start():end]
        name = m.group(1)
        try:
            frag = render_template(f'claude/{_lang(lang)}/{name}.md', {'NAME': root.name}, root)
        except (OSError, SystemExit, tmpl.TemplateError):     # ひな型のない節（自分で付けた名前など）
            frag = None
        if frag is None or not frag.startswith(m.group(0).rstrip()):
            out.append(part)
            continue
        tail = '\n\n' if i + 1 < len(marks) else '\n'
        frag = frag.rstrip('\n') + tail
        if frag.rstrip() != part.rstrip():
            changed.append(name)
        out.append(frag if frag.rstrip() != part.rstrip() else part)
    return p, old, ''.join(out), changed


def add_claude_section(root: Path, lang: str, section: str, made: list) -> None:
    """約束事のファイルに節がなければ末尾に書き足す。ファイルを消してあれば何もしない。"""
    p = instruction_file(root)
    if p is None:
        return
    text = p.read_text(encoding='utf-8')
    if SECTION_MARK.format(section) in text:
        return
    frag = render_template(f'claude/{lang}/{section}.md', {'NAME': root.name}, root)
    p.write_text(text.rstrip('\n') + '\n\n' + frag, encoding='utf-8')
    made.append('  ' + t('appended') + f'  {p.name} ' + t('({section} section)', section=section))


def init(dest: Path, lang: str = 'ja', force: bool = False,
         quiet: bool = False, example: bool = False, parts: dict | None = None,
         engine: str = 'r') -> int:
    """プロジェクトの共通部分を作る。原稿も分析も置かない（`octavo new` で足す）。

    parts（{部品: 名前}）があれば、その部品を `octavo new` と同じに足す。
    example なら見本にする。部品を指定しない example は、見本の分析と論文1本。
    """
    dest = dest.resolve()
    dest.mkdir(parents=True, exist_ok=True)
    made: list = []
    name = dest.name

    # 共通の部分（templates/project/<言語>）をそのままコピーする。ユーザーの上書き
    # （~/.config/octavo/templates/project/…）も同じ木に重なる。
    suffix = _lang(lang)
    subs = {'NAME': name, 'DOCUMENTS': documents_block(suffix)}
    for rel, src in tmpl.tree(['project/common', f'project/{suffix}']).items():
        text = render(src.read_text(encoding='utf-8'), subs, rel.endswith('.md'))
        _write(dest / project_target(rel), text, force, made, dest)
    _write(dest / INSTRUCTIONS, render_template(f'claude/{suffix}/common.md', {'NAME': name}),
           force, made, dest)
    _write(dest / 'CLAUDE.md', render_template(f'claude/{suffix}/stub.md', {'NAME': name}),
           force, made, dest)
    (dest / 'figures').mkdir(parents=True, exist_ok=True)
    (dest / 'figures' / '.gitkeep').touch()

    if example and not parts:
        parts = {'analysis': 'analysis', 'paper': EXAMPLE_PAPER}
    parts = parts or {}
    for kind in PARTS:
        if kind in parts:
            rc = new(dest / 'octavo.config.py', kind, parts[kind], force=force, quiet=True,
                     example=example, appendix=example and kind == 'paper', made=made,
                     engine=engine)
            if rc:
                return rc

    if quiet:
        return 0
    print(t('Wrote a project skeleton in {path}:', path=dest))
    for m in made:
        print(m)
    print('\n' + t('Next:'))
    print(f'  cd {dest}')
    print('  octavo doctor'.ljust(38) + '# ' + t('see whether the tools are there'))
    if 'analysis' in parts:
        print('  octavo env'.ljust(38) + '# ' + t('the analysis environment (.venv and renv)'))
        print('  ' + t('(put the raw data in data/raw/ and say where it came from in '
                       'data/raw/README.md)'))
    for kind in ('paper', 'slides', 'lecture'):
        if kind in parts:
            print(f'  octavo build {parts[kind]} --compile'.ljust(38) + '# '
                  + (t('typeset the example (fake data — for looking only)') if example
                     else t('typeset it through to PDF')))
    print(('  octavo new paper|slides|lecture <' + t('name') + '>').ljust(38)
          + '# ' + t('add a manuscript (as many as you like)'))
    print(('  octavo new analysis <' + t('name') + '>').ljust(38)
          + '# ' + t('add an analysis (.qmd)'))
    print('\n  ' + t('The working rules are in AGENTS.md; the manual is Octavo\'s guide.'))
    return 0


# ---------------------------------------------------------------- 原稿・分析を足す

NAME_OK = re.compile(r'[^\s/\\.][^\s/\\]*')


def qmd_header(cfg, name: str, lang: str) -> dict:
    """`.qmd` の冒頭に入れる値。著者・所属・メールは octavo.config.py の meta から
    （meta の affiliation がなければ institute）。date は作った日、更新日は quarto が
    組むたびに入れる（date-modified: today）。"""
    import datetime
    meta = cfg['meta'] or {}

    def q(v) -> str:
        return '"' + str(v).replace('\\', '\\\\').replace('"', '\\"') + '"'
    authors = meta.get('author') or []
    authors = [authors] if isinstance(authors, str) else list(authors)
    aff = meta.get('affiliation') or meta.get('institute')
    email = meta.get('email')
    block = ''
    if authors:
        block = 'author:\n'
        for a in authors:
            block += f'  - name: {q(a)}\n'
            if aff:
                block += f'    affiliation: {q(aff)}\n'
            if email:
                block += f'    email: {q(email)}\n'
    return {'NAME': name, 'TITLE': name, 'AUTHOR': block,
            'DATE': datetime.date.today().isoformat(), 'LANG': lang}


ENGINES = ('r', 'python')


def add_requirements(root: Path, made: list) -> None:
    """Python の分析に要るもの（Quarto が Python を動かすもの・補助が使うもの）を
    requirements.txt に足す。すでに書いてある名前は足さない。"""
    lines = tmpl.read('analysis/python-requirements.txt', root).splitlines()
    p = root / 'requirements.txt'
    text = p.read_text(encoding='utf-8') if p.is_file() else ''

    def pkg(line: str) -> str:
        return re.split(r'[<>=!~\[ ;#]', line.strip(), maxsplit=1)[0].lower().replace('_', '-')
    have = {pkg(ln) for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith('#')}
    add = [ln for ln in lines if ln.strip().startswith('#') or pkg(ln) not in have]
    if not any(not ln.strip().startswith('#') for ln in add):
        return
    p.write_text(text.rstrip('\n') + ('\n\n' if text.strip() else '') + '\n'.join(add) + '\n',
                 encoding='utf-8')
    made.append('  ' + t('appended') + '  requirements.txt ' + t('(for Python analyses)'))


def _new_analysis(cfg, name: str, lang: str, force: bool, example: bool,
                  made: list, engine: str = 'r') -> Path:
    """analysis/<name>.qmd を置く。分析の部分（octavo.R か octavo_helper.py・data/・
    assets/tables/・requirements.txt）は、まだないものだけ置く（2本目からは何も言わない）。
    engine は R か Python か。両方使うプロジェクトでは、それぞれの補助が1つずつ置かれる。"""
    root = cfg.root
    python = engine == 'python'
    folders = [f'analysis/{lang}'] + (['analysis/python'] if python else ['analysis/common'])
    for rel, src in tmpl.tree(folders, root).items():
        if force or not (root / rel).exists():
            _write(root / rel, render(src.read_text(encoding='utf-8'), {'NAME': root.name},
                                      rel.endswith('.md')), True, made, root)
    if python:
        add_requirements(root, made)
    for d in (root / 'data/derived', Path(cfg['table_dir'])):
        d.mkdir(parents=True, exist_ok=True)
        (d / '.gitkeep').touch()
    folder = f'manuscripts/{lang}/example' if example else f'manuscripts/{lang}'
    qmd = root / 'analysis' / f'{name}.qmd'
    _write(qmd, render_template(f'{folder}/analysis{"-python" if python else ""}.qmd',
                                qmd_header(cfg, name, lang), root),
           force, made, root)
    if example:
        # 見本の値・表・図。分析を実行する前でも見本の原稿が組めるように置く
        ex = tmpl.tree([f'example/{lang}'], root)
        values_dir = Path(cfg['values_dir'])
        _write(values_dir / f'{name}.json',
               ex['values/analysis.json'].read_text(encoding='utf-8'), force, made, root)
        for rel, src in ex.items():
            if rel.startswith('tables/'):
                _write(Path(cfg['table_dir']) / Path(rel).name,
                       src.read_text(encoding='utf-8'), force, made, root)
        fig = Path(cfg['figure_dir'])
        if force or not (fig / 'trend.png').exists():
            write_placeholder_png(fig / 'trend.png')
            write_placeholder_pdf(fig / 'trend.pdf')
            made.append('  ' + t('made') + '  ' + t('{path} (and .pdf — placeholders)',
                                                  path=cfg.rel(fig / 'trend.png')))
    add_claude_section(root, lang, 'analysis', made)
    if python:
        add_claude_section(root, lang, 'analysis-python', made)
    return qmd


def _example_support(cfg, lang: str, force: bool, made: list) -> None:
    """見本の原稿が使うもの（見本の値・図表・書誌）がなければ足す。"""
    from . import values as valmod
    root = cfg.root
    have, _ = valmod.load(cfg)
    if not {'n_obs', 'coef_x', 'p_x'} <= set(have):
        # 自分の analysis.qmd があるなら、それを見本で上書きしない
        name = 'example' if (root / 'analysis' / 'analysis.qmd').exists() else 'analysis'
        _new_analysis(cfg, name, lang, force, True, made)
    bib = Path(cfg['bib_file'])
    text = bib.read_text(encoding='utf-8') if bib.is_file() else ''
    if 'yamada2020' not in text:
        entries = tmpl.tree([f'example/{lang}'], root)['literature.bib']
        bib.write_text(text.rstrip('\n') + ('\n\n' if text.strip() else '')
                       + entries.read_text(encoding='utf-8'), encoding='utf-8')
        made.append('  ' + t('appended') + f'  {cfg.rel(bib)} ' + t('(example entries)'))


def _new_figure(cfg, name: str, lang: str, force: bool, quiet: bool, made: list) -> int:
    """Typst で描く図 `figures/<name>.typ` を置く（組むのは octavo build。diagrams.py）。"""
    from .backends.typst import font_expr
    src = Path(cfg['figure_src_dir']) / f'{name}.typ'
    out = Path(cfg['figure_dir'])
    # 同じ名前の図がもうある（分析の ov_figure が書いたものなど）なら、組むと上書き
    # してしまうので断る
    taken = [p for p in (out / f'{name}.pdf', out / f'{name}.png') if p.exists()]
    if taken and not src.exists() and not force:
        print(t('{path} is already there (a figure from the analysis?) — drawing '
                '{name}.typ would overwrite it. Pick another name',
                path=cfg.rel(taken[0]), name=name), file=sys.stderr)
        return 1
    subs = {'NAME': name, 'FONT': font_expr(lang, 'sans')}
    _write(src, render_template(f'manuscripts/{lang}/figure.typ', subs, cfg.root),
           force, made, cfg.root)
    if quiet:
        return 0
    for m in made:
        print(m)
    print('\n' + t('Next:'))
    fig = cfg.rel(out)
    steps = [('octavo build', t('draws it into {files}', files=f'{fig}/{name}.pdf, .png')),
             (f'![…](../../{fig}/{name}.png){{#fig-{name}}}',
              t('in a paper (from slides or lecture notes: ../{folder}/)', folder=fig))]
    width = max(len(c) for c, _ in steps)
    for cmd, why in steps:
        print(f'  {cmd.ljust(width)}   # {why}')
    return 0


def _new_table(cfg, name: str, lang: str, force: bool, quiet: bool, made: list) -> int:
    """手で作る表 `tables/<name>.csv` を置く（assets/tables/ に書くのは octavo build）。"""
    from . import handtables
    src = Path(cfg['table_src_dir']) / f'{name}.csv'
    # 分析の ov_table が書いた同じ名前の表があるなら、作ると上書きしてしまうので断る
    taken = [p for p in handtables.outputs(cfg, src) if p.exists() and handtables._foreign(p)]
    if taken and not src.exists() and not force:
        print(t('{path} is already there (a table from the analysis?) — making '
                '{name}.csv would overwrite it. Pick another name',
                path=cfg.rel(taken[0]), name=name), file=sys.stderr)
        return 1
    _write(src, render_template(f'manuscripts/{lang}/table.csv', {}, cfg.root),
           force, made, cfg.root)
    if quiet:
        return 0
    for m in made:
        print(m)
    print('\n' + t('Next:'))
    steps = [(cfg.rel(src), t('fill it in (in VS Code, the Edit as a Table button; '
                              'Excel works too)')),
             (f': … {{#tbl-{name}}}', t('the caption line in the manuscript places it')),
             ('octavo build', t('makes {files}',
                                files=f'{cfg.rel(Path(cfg["table_dir"]))}/{name}.typ, .tex, .md'))]
    width = max(len(c) for c, _ in steps)
    for cmd, why in steps:
        print(f'  {cmd.ljust(width)}   # {why}')
    return 0


def new(config: Path, kind: str, name: str, force: bool = False,
        quiet: bool = False, example: bool = False, appendix: bool = False,
        tex: bool = False, made: list | None = None, engine: str = 'r') -> int:
    """原稿・分析・図・表を1本足す。octavo.config.py は書き換えない（init が書いたグロブが拾う）。

    既にある原稿の名前なら、ないファイルだけを足す（`--appendix` / `--tex` を後から）。
    """
    from . import config as configmod
    if kind not in KINDS and kind not in ('analysis', 'figure', 'table'):
        print(t('unknown kind: {kind} (one of {allowed})',
                kind=kind, allowed=' / '.join([*KINDS, 'analysis', 'figure', 'table'])),
              file=sys.stderr)
        return 1
    ext = {'analysis': '.qmd', 'figure': '.typ', 'table': '.csv'}.get(kind)
    if ext and name.endswith(ext):
        name = name[:-len(ext)]
    if not NAME_OK.fullmatch(name):
        print(t('that name will not do: {name} (no spaces, no / or \\, and it '
                'cannot start with a dot)', name=repr(name)), file=sys.stderr)
        return 1
    if engine not in ENGINES:
        print(t('unknown engine: {engine} (one of {allowed})',
                engine=engine, allowed=' / '.join(ENGINES)), file=sys.stderr)
        return 1
    if (appendix or tex) and kind != 'paper':
        print(t('--appendix and --tex are for papers only'), file=sys.stderr)
        return 1
    cfg = configmod.load(config)
    root = cfg.root
    lang = _lang(cfg['lang'])
    quiet_made = made is not None
    made = made if made is not None else []

    if kind == 'analysis':
        qmd = _new_analysis(cfg, name, lang, force, example, made, engine)
        if quiet or quiet_made:
            return 0
        for m in made:
            print(m)
        print('\n' + t('Next:'))
        steps = [(f'octavo analysis run {cfg.rel(qmd)}', t('run it')),
                 ('octavo values', t('see the values it wrote')),
                 ('octavo env', t('the analysis environment (.venv and renv)'))]
        width = max(len(c) for c, _ in steps)
        for cmd, why in steps:
            print(f'  {cmd.ljust(width)}   # {why}')
        return 0

    if kind == 'figure':
        return _new_figure(cfg, name, lang, force, quiet or quiet_made, made)
    if kind == 'table':
        return _new_table(cfg, name, lang, force, quiet or quiet_made, made)

    k = KINDS[kind]
    in_docs = uses_docs(cfg)
    if k.get('docs_only') and not in_docs:
        print(t('a {kind} needs the docs/ layout: run octavo migrate --docs first, or add '
                "'docs': {'src': 'docs/*/'} to documents in octavo.config.py", kind=kind),
              file=sys.stderr)
        return 1
    src = doc_path(cfg, kind, name)
    if name in cfg.documents and cfg.documents[name].src != src.resolve():
        print(t('a document called {name} already exists ({path})',
                name=name, path=cfg.rel(cfg.documents[name].src)) + '\n  '
              + t('octavo build <name> could not tell them apart — pick another'),
              file=sys.stderr)
        return 1

    author = cfg['meta'].get('author') or ''
    if isinstance(author, (list, tuple)):
        author = author[0] if author else ''
    subs = {'NAME': name, 'AUTHOR': str(author)}
    if example:
        _example_support(cfg, lang, force, made)
    folder = f'manuscripts/{lang}/example' if example else f'manuscripts/{lang}'
    text = render_template(f'{folder}/{kind}.md', subs, root)
    if in_docs:
        # 何を作るか（outputs）と回でできているか（sessions）を原稿の冒頭に書く。
        # ひな型の図のパスは前からの置き場所から見た相対なので、新しい場所から見た相対に
        text = with_front(text, k['front'])
        text = mdlib.rebase_links(text, (root / k['src'].format(name)).parent, src.parent)
    _write(src, text, force, made, root)
    if appendix:
        ap = render_template(f'{folder}/appendix.md', subs, root)
        if in_docs:
            ap = mdlib.rebase_links(ap, (root / k['appendix'].format(name)).parent, src.parent)
        _write(appendix_path(cfg, kind, name), ap, force, made, root)
    add_claude_section(root, lang, CLAUDE_SECTION[kind], made)

    # 足した原稿を設定が本当に拾うかを、読み直して確かめる
    cfg = configmod.load(config)
    doc = cfg.documents.get(name)
    if doc is None:
        made.append('  ' + t('note') + '  ' + t(
            'documents in octavo.config.py is not picking up {glob} — check it',
            glob=DOCS_SRC if in_docs else k['src'].format('*')))
    elif k['profile'] == 'paper':
        # 論文の体裁（投稿先ごとに手で書く）。**原稿と同じフォルダ**に置く。
        # 組版のたびに build/ へ写されるので、build/ は丸ごと消してよい。
        for ext in ('.typ', '.tex') if tex else ('.typ',):
            try:
                text = tmpl.read(f'paper/{lang}/main{ext}', root)
            except tmpl.TemplateError:
                continue
            _write(src.parent / f'main{ext}', text, force, made, root)

    if quiet or quiet_made:
        return 0
    for m in made:
        print(m)
    print('\n' + t('Next:'))
    steps = {
        'lecture': [(f'octavo build {name} --to pdf --compile',
                     t('the A4 handout, through to PDF')),
                    (f'octavo build {name} --to slides --compile',
                     t('the slides, one PDF per session')),
                    (f'octavo build {name}-01 --to slides',
                     t('just one session'))],
        'slides': [(f'octavo build {name} --compile', t('the slides, through to PDF'))],
        'poster': [(f'octavo build {name} --compile', t('the poster, through to PDF'))],
        'paper': [(f'octavo build {name} --compile',
                   t('typeset main.typ through to PDF')),
                  (f'octavo build {name} --to word',
                   t('a Word file for your coauthors'))]
                 + ([] if appendix else [(f'octavo new paper {name} --appendix',
                                          t('add an appendix later'))])
                 + ([] if tex else [(f'octavo new paper {name} --tex',
                                     t('add main.tex, to typeset with LaTeX'))]),
    }[kind]
    width = max(len(c) for c, _ in steps)
    for cmd, why in steps:
        print(f'  {cmd.ljust(width)}   # {why}')
    return 0
