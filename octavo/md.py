# -*- coding: utf-8 -*-
"""出力形式に依存しない前処理。

ここに置くのは「LaTeX でも Typst でも Word でも同じようにやること」だけ。
出力構文（\\inputtable や #figure や ![](…)）の組み立ては backends/ 側。

英語の原稿（Table / Figure / Section, References, Abstract）と日本語の原稿
（表 / 図 / 節, 参考文献, 要旨・概要）の両方を既定で認識する。混在可。
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from .i18n import t, tag

# ---------------------------------------------------------------- 語彙

ABSTRACT_HEADS = ('Abstract', '要旨', '概要', 'アブストラクト')
REFERENCES_HEADS = ('References', 'Bibliography', 'Works Cited',
                    '参考文献', '引用文献', '文献')

CROSSREF_PATTERNS = {
    'en': {
        'table': re.compile(r'\bTable (\w+)\b(?!\.)'),
        'figure': re.compile(r'\bFigure (\w+)\b(?!\.)'),
        'section': re.compile(r'\bSection\s*(?:~|\\textasciitilde\{\})?\s*(\d+)(?:\.(\d+))?\b'),
    },
    'ja': {
        'table': re.compile(r'表\s*([A-Z]?\d+)(?![.．:：0-9])'),
        'figure': re.compile(r'図\s*([A-Z]?\d+)(?![.．:：0-9])'),
        'section': re.compile(r'第?\s*(\d+)(?:[.．](\d+))?\s*節'),
    },
}


def crossref_patterns(vocab: str) -> dict:
    """{種類: [(語彙, 正規表現), …]} を返す。

    語彙（'ja' / 'en'）を一緒に返すのは、置き換えるときに「表\\ref{…}」と
    「Table~\\ref{…}」を書き分けるため。原稿の書き方をそのまま保つ。
    """
    langs = ('ja', 'en') if vocab == 'both' else (vocab,)
    return {kind: [(lg, CROSSREF_PATTERNS[lg][kind]) for lg in langs]
            for kind in ('table', 'figure', 'section')}


# ---------------------------------------------------------------- front matter

FRONT_MATTER = re.compile(r'\A---\s*\n(.*?)\n---\s*\n', re.S)


def split_front_matter(md: str) -> tuple[dict, str]:
    """先頭の YAML front matter を取り出す。

    PyYAML には依存しない。対応するのは論文の題扉に要る範囲だけ:

        title: 論文のタイトル
        subtitle: 副題
        author:
          - 著者名
          - 共著者
        institute: 所属
        date: 2026-08-11
        keywords: [a, b]

    入れ子の辞書やブロックスカラー（`|`）は読まない。必要になったら
    octavo.config.py の `meta` に書くこと。
    """
    m = FRONT_MATTER.match(md)
    if not m:
        return {}, md
    meta: dict = {}
    key = None
    for raw in m.group(1).split('\n'):
        if not raw.strip() or raw.lstrip().startswith('#'):
            continue
        if re.match(r'\s*-\s+', raw) and key:                    # リストの続き
            meta.setdefault(key, [])
            if not isinstance(meta[key], list):
                meta[key] = []
            meta[key].append(_unquote(re.sub(r'^\s*-\s+', '', raw)))
            continue
        km = re.match(r'([\w-]+)\s*:\s*(.*)$', raw)
        if not km:
            continue
        key, val = km.group(1), km.group(2).strip()
        if val == '':
            meta[key] = []                                       # 次行からリスト
        elif val.startswith('[') and val.endswith(']'):
            meta[key] = [_unquote(x) for x in val[1:-1].split(',') if x.strip()]
        else:
            meta[key] = _unquote(val)
    meta = {k: v for k, v in meta.items() if v != []}
    return meta, md[m.end():]


def _unquote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in '"\'':
        return s[1:-1]
    return s


def to_yaml_block(meta: dict) -> str:
    """メタデータを pandoc に渡す YAML ブロックにする（standalone 出力用）。"""
    if not meta:
        return ''
    lines = ['---']
    for k, v in meta.items():
        if isinstance(v, (list, tuple)):
            lines.append(f'{k}:')
            lines += [f'  - {_yq(x)}' for x in v]
        elif isinstance(v, bool):
            lines.append(f'{k}: {"true" if v else "false"}')
        else:
            lines.append(f'{k}: {_yq(v)}')
    lines += ['---', '']
    return '\n'.join(lines)


def _yq(v) -> str:
    s = str(v)
    if s and (s[0] in '[{&*!|>%@`"\'#-' or ':' in s or '\n' in s):
        return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'
    return s


# ---------------------------------------------------------------- 本文の切り分け

FIRST_SECTION = r'^#{1,3} (?:\d+[.．]?[ 　]|Appendix |付録)'


def strip_title_block(md: str, first_section_pat: str = FIRST_SECTION) -> str:
    """本文より前（タイトル・著者・草稿注記）を捨てる。

    本文の先頭は `first_section_pat` にマッチする最初の見出し（既定は
    「## 1. …」のような番号付き見出し）。見つからなければ何もしない
    （番号を振らない原稿もあるため）。
    """
    m = re.search(first_section_pat, md, re.M)
    return md[m.start():] if m else md


def split_abstract(md: str) -> tuple[str, str]:
    """`## Abstract` / `## 要旨` 節を本文から切り離して別に返す。"""
    heads = '|'.join(re.escape(h) for h in ABSTRACT_HEADS)
    m = re.search(rf'^#{{1,3}} (?:{heads})\s*\n+(.+?)\n\s*\*(?:Word count|字数|文字数):.*?\*\s*\n',
                  md, re.S | re.M)
    if not m:
        m = re.search(rf'^#{{1,3}} (?:{heads})\s*\n+(.+?)(?=\n---|\n#{{1,3}} |\Z)', md, re.S | re.M)
    if not m:
        return '', md
    return m.group(1).strip(), md[:m.start()] + md[m.end():]


def drop_references(md: str) -> str:
    """原稿末尾の参考文献節を落とす（書誌は .bib から組む）。"""
    pat = re.compile(r'^#{1,3} (?:%s)\s*$' % '|'.join(re.escape(h) for h in REFERENCES_HEADS),
                     re.M)
    m = pat.search(md)
    return md[:m.start()] if m else md


# ---------------------------------------------------------------- 回ごとに分ける
# 講義ノート1本（`#` が1回分）から、回ごとに別々のスライドを組むための部品。

SECTION_HEADING = re.compile(r'^#[ 　]+(?P<title>.*?)[ 　]*(?:\{(?P<attr>[^}]*)\})?[ 　]*$')
FENCE_LINE = re.compile(r'^\s*(```|~~~)')


def _sections(body: str) -> tuple[str, list, list]:
    """(最初の `#` より前, [(印, 題, 中身)], [見出しの行番号]) に分ける。

    コードブロックの中の `#` は見ない。印は見出しに `{#id}` があればその id、
    無ければ出てきた順の2桁（'01'）。回を途中に挿し込むと番号がずれて出力の
    ファイル名も変わるので、名前を固定したい回には `{#id}` を付ける。

    3つ目の行番号（`drop_references(body)` の中での0始まり）は section_spans
    のためだけにある。**見出しの拾い方を2箇所に書かない**ための持ち回りで、
    回ごとのスライドと「カーソルのある回」は必ず同じ答えになる。
    """
    lines = drop_references(body).split('\n')
    head: list = []
    parts: list = []
    at: list = []
    fence = None
    for i, line in enumerate(lines):
        f = FENCE_LINE.match(line)
        if f:
            fence = None if fence == f.group(1) else (fence or f.group(1))
        m = None if fence or f else SECTION_HEADING.match(line)
        if m:
            ident = re.search(r'#([\w.:-]+)', m.group('attr') or '')
            key = ident.group(1) if ident else f'{len(parts) + 1:02d}'
            parts.append([key, m.group('title'), []])
            at.append(i)
        elif parts:
            parts[-1][2].append(line)
        else:
            head.append(line)
    return '\n'.join(head), [(k, t, '\n'.join(b)) for k, t, b in parts], at


def section_spans(md: str) -> list:
    """[(印, 題, 開始行, 終了行)] — **1始まりの、原稿そのものの行番号**。

    VS Code 拡張が「カーソルのある回」を出すために使う（`octavo documents
    --json`）。front matter の分だけずらしてあるので、エディタの行番号と
    そのまま突き合わせられる。末尾の参考文献節はどの回にも入らない。
    """
    _, body = split_front_matter(md)
    offset = md[:len(md) - len(body)].count('\n')
    _, parts, at = _sections(body)
    kept = drop_references(body).split('\n')
    if len(kept) > 1 and kept[-1] == '':
        kept.pop()          # 末尾の改行が作る空要素。参考文献節の行に食い込む
    last = len(kept) - 1
    out = []
    for i, (key, title, _text) in enumerate(parts):
        end = at[i + 1] - 1 if i + 1 < len(at) else last
        out.append((key, title, offset + at[i] + 1, offset + end + 1))
    return out


def section_keys(md: str) -> list:
    """[(印, 題)] — 原稿を `#` 見出しで分けたときの各回。"""
    _, body = split_front_matter(md)
    return [(k, t) for k, t, _ in _sections(body)[1]]


def section_part(md: str, key: str) -> str | None:
    """1回分だけの原稿を返す。無ければ None。

    その回の `#` 見出しは題扉に回す（題 = 見出し、副題 = 原稿全体の題）。
    見出しのまま残すと、題扉のすぐ後に同じ題の扉がもう1枚出るため。
    最初の `#` より前（ノート全体の前置き）はどの回にも入れない。
    """
    meta, body = split_front_matter(md)
    for k, title, text in _sections(body)[1]:
        if k != key:
            continue
        whole = meta.get('title')
        meta = {**meta, 'title': title}
        if whole:
            meta['subtitle'] = whole
        return to_yaml_block(meta) + text.lstrip('\n')
    return None


NUMBERED_HEADING = re.compile(
    r'^(?P<hash>\#{1,5})[ 　]+(?P<num>\d+(?:[.．]\d+)*)(?:[.．][ 　]*|[ 　]+)'
    r'(?P<title>\S.*?)(?P<attr>\s*\{[^}]*\})?\s*$', re.M)

APPENDIX_HEADING = re.compile(
    r'^(?P<hash>\#{1,5})\s+(?:Appendix|付録)\s*(?P<let>[A-Z])[.．]?[ 　]*'
    r'(?P<title>.*?)(?P<attr>\s*\{[^}]*\})?\s*$', re.M)

APPENDIX_SUB = re.compile(
    r'^(?P<hash>\#{2,5})[ 　]+(?P<let>[A-Z])[.．](?P<num>\d+)[.．]?[ 　]*'
    r'(?P<title>\S.*?)(?P<attr>\s*\{[^}]*\})?\s*$', re.M)


def tidy_headings(md: str) -> str:
    """節番号は組版系に振らせ、原稿の番号は `{#sec:…}` ラベルとして残す。

    「## 1. はじめに」「# 2. 本題」「### 1.2 用語」「## 付録A．追加分析」の
    どれでも拾う。見出しの深さは問わない（原稿によって `#` から始まったり
    `##` から始まったりするため）。既に `{#…}` が付いている見出しは触らない。
    """
    md = re.sub(r'^\s*---\s*$', '', md, flags=re.M)                       # 水平線
    md = re.sub(r'^\*\((?:In the )?(?:LaTeX|Typst|Word|Beamer).*?\)\*\s*$', '',
                md, flags=re.M | re.I)                                    # 作業用の注記

    def numbered(m):
        if m.group('attr'):
            return m.group(0)
        label = re.sub(r'[.．]', '-', m.group('num'))
        return f'{m.group("hash")} {m.group("title")} {{#sec:{label}}}'

    def appendix(m):
        if m.group('attr'):
            return m.group(0)
        title = m.group('title').strip() or ('付録' + m.group('let'))
        return f'{m.group("hash")} {title} {{#sec:app{m.group("let")}}}'

    def appendix_sub(m):
        if m.group('attr'):
            return m.group(0)
        return (f'{m.group("hash")} {m.group("title")} '
                f'{{#sec:app{m.group("let")}-{m.group("num")}}}')

    md = APPENDIX_HEADING.sub(appendix, md)
    md = APPENDIX_SUB.sub(appendix_sub, md)
    md = NUMBERED_HEADING.sub(numbered, md)
    md = re.sub(r'\n{3,}', '\n\n', md)
    return md.strip() + '\n'


SEC_LABELLED = re.compile(r'^(?P<hash>\#{1,5})[ 　]+(?P<title>.*?)[ 　]*'
                          r'\{#sec:(?P<num>[\w-]+)\}[ 　]*$', re.M)


def restore_heading_numbers(md: str, lang: str = 'ja') -> str:
    """`## はじめに {#sec:1}` を `## 1. はじめに {#sec:1}` に戻す。

    Word は節番号を自分では振らない。pandoc の `--number-sections` は Word では
    効かない（Word 側のスタイルに任せる作りのため）。かといって番号が無いと、
    本文の「第2節」という言及の相手が消える。

    そこで **原稿が持っていた番号をそのまま戻す**。数え直さないので、
    「1, 2, 付録A」のような並びも原稿どおりになる。
    """
    def sub(m):
        num = m.group('num')
        if num.startswith('app'):
            rest = num[3:]
            letter, _, sub_no = rest.partition('-')
            if sub_no:
                head = f'{letter}.{sub_no}　' if lang == 'ja' else f'{letter}.{sub_no} '
            else:
                head = f'付録{letter}．' if lang == 'ja' else f'Appendix {letter}. '
        else:
            dotted = num.replace('-', '.')
            head = f'{dotted}. ' if '.' not in dotted else f'{dotted} '
        return f'{m.group("hash")} {head}{m.group("title")} {{#sec:{num}}}'

    return SEC_LABELLED.sub(sub, md)


# ---------------------------------------------------------------- 表・図

TABLE_CAPTION = re.compile(
    r'^\*\*(?:Table|表)\s*(?P<num>[A-Z]?\d+)\s*[.．:：]\s*(?P<cap>[^*]+)\*\*\s*\n+'
    r'(?P<body>(?:\|.*\n)+)'
    r'(?P<note>(?:\n?\*[^\n]*\*\s*\n)?)',
    re.M)

FIGURE_BLOCK = re.compile(
    r'!\[[^\]]*\]\((?P<dir>[\w./-]*?)(?P<file>[\w.-]+?)\.(?:png|pdf|jpg|jpeg|svg)\)\s*\n+'
    r'\*\*(?:Figure|図)\s*(?P<num>[A-Z]?\d+)\s*[.．:：]\*\*\s*(?P<cap>.+?)(?=\n\s*\n|\Z)', re.S)


def replace_tables(md: str, table_map: dict, formatter, report: list) -> str:
    """`**Table N. Caption**` + マークダウン表 + 任意の注 を formatter で置き換える。

    formatter(match, name) の name は table_map の値。対応が無ければ None を渡す
    （バックエンドはマークダウンの表をそのまま使うか、キャプションを付け直す）。
    """
    hit = [0]

    def sub(m):
        hit[0] += 1
        return formatter(m, table_map.get(m.group('num')))

    new_md, n = TABLE_CAPTION.subn(sub, md)
    if table_map and not n:
        report.append(f'{tag("table")} ' + t(
            'table_map is set but not one `**Table N. …**` caption was found — '
            'check the format'))
    return new_md


# 画像リンク: `![alt](path)` / `![alt](path "title")` / `![alt](<path>)`
IMAGE_LINK = re.compile(r'(!\[[^\]]*\]\()\s*(<[^>]*>|[^)\s]+)((?:\s+"[^"]*")?\s*\))')

_SCHEME = re.compile(r'^[A-Za-z][A-Za-z0-9+.-]*://')
_WINDRIVE = re.compile(r'^[A-Za-z]:[\\/]')


def _is_external(target: str) -> bool:
    """書き換えてはいけない指し先か（URL・絶対パス・データ URI）。"""
    return (target.startswith(('/', '#', 'data:'))
            or _SCHEME.match(target) is not None
            or _WINDRIVE.match(target) is not None)


def rebase_links(md: str, src_dir: Path, out_dir: Path) -> str:
    """図のパスを「原稿から見た相対」から「出力先から見た相対」に直す。

    原稿は図を**原稿から見た相対パス**で書く（`slides/x.md` なら `../figures/…`、
    `papers/<名前>/paper.md` なら `../../figures/…`）。エディタのプレビューに
    図が出るようにするためで、これは原稿の側の正しい書き方。

    ところが出力は `build/typst-slides/` や `build/typst/<名前>/` に置かれ、
    原稿と階層の深さが同じとはかぎらない。そのまま写すと、同じ `../figures/…`
    が `build/figures/…` を指してしまい、typst compile が file not found で
    止まる（原稿は正しいのに組版だけ落ちる）。

    そこで原稿のパスをいったん実体に解決し、出力先から見た相対に振り直す。
    URL・絶対パス・データ URI はそのまま通す。
    """
    src_dir, out_dir = Path(src_dir).resolve(), Path(out_dir).resolve()
    if src_dir == out_dir:
        return md

    # コードブロック・インラインコードの中は書き換えない。原稿が「図はこう書く」と
    # 見本を載せていることがあり、そこを出力先からの相対に直すと読者に嘘を見せる
    # （`{{…}}` で同じことをやって直した経緯がある）。
    from . import values as valmod
    md, kept = valmod.mask_code(md)

    def one(m: 're.Match') -> str:
        target = m.group(2)
        bare = target[1:-1] if target.startswith('<') else target
        if not bare or _is_external(bare):
            return m.group(0)
        rel = Path(os.path.relpath((src_dir / bare).resolve(), out_dir)).as_posix()
        return m.group(1) + (f'<{rel}>' if target.startswith('<') else rel) + m.group(3)

    return valmod.unmask_code(IMAGE_LINK.sub(one, md), kept)


def replace_figures(md: str, formatter, report: list) -> str:
    new_md, n = FIGURE_BLOCK.subn(formatter, md)
    if not n and '![' in md:
        report.append(f'{tag("figure")} ' + t(
            'no figure with a `**Figure N.**` caption was found '
            '(a bare image link passes through unchanged)'))
    return new_md


# ---------------------------------------------------------------- 条件付きブロック

DIV_OPEN = re.compile(r'^(:{3,})\s*(?:\{([^}]*)\}|([A-Za-z][\w.-]*))\s*$')
DIV_CLOSE = re.compile(r'^:{3,}\s*$')

# 「この用途のときだけ出す」印。`.slides-only` でも `.only-slides` でもよい。
ONLY = re.compile(r'^(?:only-(.+)|(.+)-only)$')
NOT = re.compile(r'^(?:no|not)-(.+)$')


def _classes(attr: str | None, bare: str | None) -> list:
    if bare:
        return [bare]
    if not attr:
        return []
    out = []
    for tok in attr.split():
        if tok.startswith('.'):
            out.append(tok[1:])
        elif '=' not in tok and not tok.startswith('#'):
            out.append(tok)
    return out


def filter_divs(md: str, keep: set, keep_notes: bool = False,
                report: list | None = None,
                notes_wrap: tuple | None = None) -> str:
    """用途に合わない条件付きブロックを落とす。

        ::: {.slides-only}   スライドのときだけ
        ::: {.handout-only}  A4 プリントのときだけ
        ::: {.no-slides}     スライド以外
        ::: notes            発表者ノート（残すのは beamer と typst-notes）

    `notes_wrap` を渡すと、`::: notes` の囲みをそのまま残さずに (開き, 閉じ)
    で囲み直す。beamer は pandoc に div のまま渡すと `\note{}` になるが、
    Typst の台本（typst-notes）はそうならないので、生の Typst で
    `#octavo-note[ … ]` に包むために使う。中身は素の Markdown のままなので、
    箇条書きも強調も引用もふつうに組める。

    印の付いていない div（`::: {.warning}` など）はそのまま通す。
    条件付き div は、残す場合も囲みを外して中身だけにする（LaTeX 側に
    知らない環境を渡さないため）。
    """
    out: list = []
    stack: list = []          # [(kind, drop)] kind: 'plain' | 'cond'
    dropped = 0

    def dropping() -> bool:
        return any(d for _, d in stack)

    for line in md.split('\n'):
        opening = DIV_OPEN.match(line) and not DIV_CLOSE.match(line)
        if opening:
            m = DIV_OPEN.match(line)
            cls = _classes(m.group(2), m.group(3))
            if dropping():
                stack.append(('plain', False))
                continue
            if 'notes' in cls or 'speaker-notes' in cls:
                if keep_notes and notes_wrap:
                    stack.append(('notes', False))
                    out.append(notes_wrap[0])
                elif keep_notes:
                    stack.append(('plain', False))
                    out.append(line)
                else:
                    stack.append(('cond', True))
                    dropped += 1
                continue
            cond = [c for c in cls if ONLY.match(c) or NOT.match(c)]
            if cond:
                want = True
                for c in cond:
                    mo = ONLY.match(c)
                    if mo:
                        want = want and ((mo.group(1) or mo.group(2)) in keep)
                    mn = NOT.match(c)
                    if mn:
                        want = want and (mn.group(1) not in keep)
                stack.append(('cond', not want))
                dropped += (not want)
                continue                                  # 囲みは常に外す
            stack.append(('plain', False))
            out.append(line)
            continue

        if DIV_CLOSE.match(line) and stack:
            kind, drop = stack.pop()
            if drop or dropping() or kind == 'cond':
                continue
            if kind == 'notes' and notes_wrap:
                out.append(notes_wrap[1])
                continue
            out.append(line)
            continue

        if dropping():
            continue
        out.append(line)

    if dropped and report is not None:
        report.append(f'{tag("conditional")} ' + t('dropped {n} {n|block that does|blocks that do} '
                                                    'not belong in this output', n=dropped))
    return '\n'.join(out)


# ---------------------------------------------------------------- 事例・論点等のdiv

THEOREM_ID = re.compile(r'#([\w:.-]+)')


def _bold_prefix(label: str, body: str) -> str:
    """`\\newtheorem` が無いバックエンド向けの素のMarkdownでの代用表現。"""
    lines = body.split('\n')
    for i, ln in enumerate(lines):
        if ln.strip():
            lines[i] = f'**{label}.** {ln.lstrip()}'
            return '\n'.join(lines)
    return f'**{label}.**'


def replace_theorem_divs(md: str, envs: dict, raw: bool,
                         report: list | None = None) -> str:
    """`octavo.config.py` の `theorem_envs`（例: `{'case': '事例', 'nb': '注意'}`）に
    挙げたクラスの div を、\\newtheorem 環境（`raw=True`）か、素のボールド
    段落（`raw=False`、通し番号は付かない）に変換する。

        ::: {.case #case:example}
        見本の事例をここに書く.
        :::

        ::: nb
        私語は厳禁.
        :::

    `raw=True` のとき、ヘッダー側に対応する `\\newtheorem{case}{事例}[section]`
    （`octavo template copy handout/handout-header.tex` で写して足す）が要る。
    `theorem_envs` に無いクラスの div はそのまま通す。`filter_divs` の後に呼ぶこと。
    """
    if not envs:
        return md
    out: list = []
    stack: list = []   # 各フレーム: {'theorem': bool, 'cls', 'label', 'lines'}
    hits = 0

    def emit(line: str) -> None:
        for frame in reversed(stack):
            if frame['theorem']:
                frame['lines'].append(line)
                return
        out.append(line)

    for line in md.split('\n'):
        opening = DIV_OPEN.match(line) and not DIV_CLOSE.match(line)
        if opening:
            m = DIV_OPEN.match(line)
            cls_list = _classes(m.group(2), m.group(3))
            theorem_cls = next((c for c in cls_list if c in envs), None)
            if theorem_cls:
                idm = THEOREM_ID.search(m.group(2) or '')
                stack.append({'theorem': True, 'cls': theorem_cls,
                             'label': idm.group(1) if idm else None, 'lines': []})
            else:
                stack.append({'theorem': False})
                emit(line)
            continue

        if DIV_CLOSE.match(line) and stack:
            frame = stack.pop()
            if not frame['theorem']:
                emit(line)
                continue
            hits += 1
            body = '\n'.join(frame['lines'])
            if raw:
                tag = f"\\label{{{frame['label']}}}" if frame['label'] else ''
                rendered = f"\\begin{{{frame['cls']}}}{tag}\n{body}\n\\end{{{frame['cls']}}}"
            else:
                rendered = _bold_prefix(envs[frame['cls']], body)
            for ln in rendered.split('\n'):
                emit(ln)
            continue

        emit(line)

    if hits and report is not None:
        how = t('newtheorem environments') if raw else t('bold paragraphs, unnumbered')
        report.append(f'{tag("theorem divs")} ' + t('converted {n} theorem {n|div|divs} ({how})',
                                                   n=hits, how=how))
    return '\n'.join(out)


# ---------------------------------------------------------------- \poscite

POSCITE = re.compile(r'\\poscite\{([\w:.#$%&+?<>~/-]+)\}')


def replace_poscite(md: str, formatter) -> str:
    """所有格引用 `\\poscite{key}`（"Smith and Taylor's (2003)"）を展開する。"""
    return POSCITE.sub(lambda m: formatter(m.group(1)), md)


CITE_KEY = re.compile(r'(?<![\w.@-])@([\w][\w:.#$%&+?<>~/-]*)')


def cited_keys(md: str) -> set:
    """本文が引いている citation key を集める（参考文献節より前だけ）。"""
    body = drop_references(md)
    body = re.sub(r'`[^`\n]*`', '', body)          # インラインコード内は無視
    body = re.sub(r'^```.*?^```', '', body, flags=re.S | re.M)
    keys = set(CITE_KEY.findall(body)) | set(POSCITE.findall(body))
    return {k.rstrip('.,;:') for k in keys}


# ---------------------------------------------------------------- 検査

CJK = re.compile(r'[\u3000-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uff00-\uffef]')


def has_cjk(text: str) -> bool:
    return bool(CJK.search(text))


def cjk_lines(text: str) -> list:
    return [' '.join(l.split())[:70] for l in text.split('\n') if CJK.search(l)]


COMMENT = re.compile(r'<!--.*?-->', re.S)


def strip_comments(md: str) -> str:
    """HTML コメントを落とす。

    コメントは組版に届かないので、投稿規定の分量に数えてはいけない
    （`octavo new` のひな型は説明をコメントで書く）。コードブロックの中に
    書かれたコメントまで落ちるが、分量は目安なので許容する。
    """
    return COMMENT.sub('', md)


def word_count(md: str) -> tuple[int, int]:
    """語数（表を除く / 含む）。日本語混じりでは目安。"""
    md = strip_comments(md)

    def wc(t: str) -> int:
        return len(re.sub(r'[*_>#`]', ' ', t).split())
    excl = wc('\n'.join(l for l in md.split('\n') if not l.strip().startswith('|')))
    return excl, wc(md)


def char_count(md: str) -> int:
    """日本語論文向け: 空白・改行・マークダウン記号を除いた文字数。"""
    return len(re.sub(r'[\s*_>#`|]', '', strip_comments(md)))


def read(path: Path) -> str:
    return path.read_text(encoding='utf-8')
