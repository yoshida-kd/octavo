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

# ---------------------------------------------------------------- front matter

FRONT_MATTER = re.compile(r'\A---\s*\n(.*?)\n---\s*\n', re.S)


def split_front_matter(md: str) -> tuple[dict, str]:
    """先頭の YAML front matter を取り出す。

    PyYAML には依存しない。対応するのは論文のタイトル部分に要る範囲だけ:

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

def strip_title_block(md: str) -> str:
    """本文より前（タイトル・著者・草稿注記）を捨てる。

    本文の先頭は最初の見出し（要旨は先に切り離してある）。ただし `# 題` が
    **1つだけ**あって、その後に `##` の節が続くなら、それは題なので `##` から。
    見出しがなければ何もしない。
    """
    h1 = list(re.finditer(r'^#[ \t]+\S', md, re.M))
    sub = re.search(r'^#{2,3}[ \t]+\S', md, re.M)
    if len(h1) == 1 and sub and h1[0].start() < sub.start():
        return md[sub.start():]
    m = re.search(r'^#{1,3}[ \t]+\S', md, re.M)
    return md[m.start():] if m else md


def split_abstract(md: str) -> tuple[str, str]:
    """`## Abstract` / `## 要旨` 節を本文から切り離して別に返す。"""
    heads = '|'.join(re.escape(h) for h in ABSTRACT_HEADS)
    # 要旨の中身に見出しは入らない。空の要旨（見出しのすぐ後に次の節）で次の節の
    # 見出しまで飲み込むと、本文の節が1つ要旨へ移って番号がずれる
    heading = re.compile(r'^#{1,3} ', re.M)
    m = re.search(rf'^#{{1,3}} (?:{heads})\s*\n+(.+?)\n\s*\*(?:Word count|字数|文字数):.*?\*\s*\n',
                  md, re.S | re.M)
    if m and heading.search(m.group(1)):
        m = None
    if not m:
        m = re.search(rf'^#{{1,3}} (?:{heads})[ \t]*\n(.*?)(?=^---|^#{{1,3}} |\Z)', md, re.S | re.M)
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


SESSION_OPEN = re.compile(r'^:{3,}\s*\{(?P<attr>(?:[^}]*\s)?\.session(?:\s[^}]*)?)\}\s*$')


def session_attrs(attr: str) -> dict:
    """区切りの属性（id・title・subtitle・date・author・institute）。"""
    from . import crossref as xref
    out = {}
    m = re.search(r'(?:^|\s)#([\w.:-]+)', attr)
    if m:
        out['id'] = m.group(1)
    for k in ('title', 'subtitle', 'date', 'author', 'institute'):
        v = xref.attr_value(attr, k)
        if v is not None:
            out[k] = v
    return out


def _marker_lines(lines: list) -> list:
    """[(開きの行, 閉じの行 or None, 属性)]。コードブロックの中は見ない。

    区切りは中身を持たない div（`::: {.session …}` のすぐ後に `:::`）。中身を
    書いた場合は、閉じの行だけを落として中身はその回の頭に残す。
    """
    out = []
    fence = None
    i = 0
    while i < len(lines):
        line = lines[i]
        f = FENCE_LINE.match(line)
        if f:
            fence = None if fence == f.group(1) else (fence or f.group(1))
            i += 1
            continue
        m = None if fence else SESSION_OPEN.match(line)
        if m:
            depth, close = 1, None
            for j in range(i + 1, len(lines)):
                if DIV_CLOSE.match(lines[j]):
                    depth -= 1
                    if depth == 0:
                        close = j
                        break
                elif DIV_OPEN.match(lines[j]):
                    depth += 1
            out.append((i, close, session_attrs(m.group('attr'))))
        i += 1
    return out


def has_session_markers(md: str) -> bool:
    return bool(_marker_lines(md.split('\n')))


def _sections(body: str) -> tuple[str, list, list]:
    """(最初の区切りより前, [(印, 題, 中身, 属性)], [区切りの行番号]) に分ける。

    区切りは `::: {.session #id title="…"}` + `:::`。原稿に1つもなければ、
    `#` 見出しが回の区切りになる（見出しの題が回の題）。

    コードブロックの中は見ない。印は区切り（または見出し）に `#id` があればその id、
    なければ出てきた順の2桁（'01'）。回を途中に挿し込むと番号がずれて出力の
    ファイル名も変わるので、名前を固定したい回には id を付ける。

    3つ目の行番号（`drop_references(body)` の中での0始まり）は section_spans
    のためだけにある。**区切りの拾い方を2箇所に書かない**ための持ち回りで、
    回ごとのスライドと「カーソルのある回」は必ず同じ答えになる。
    """
    lines = drop_references(body).split('\n')
    markers = _marker_lines(lines)
    head: list = []
    parts: list = []
    at: list = []
    if markers:
        skip = {c for _, c, _ in markers if c is not None}
        starts = {o: a for o, _, a in markers}
        for i, line in enumerate(lines):
            if i in starts:
                a = starts[i]
                key = a.get('id') or f'{len(parts) + 1:02d}'
                parts.append([key, a.get('title'), [], a])
                at.append(i)
            elif i in skip:
                continue
            elif parts:
                parts[-1][2].append(line)
            else:
                head.append(line)
        out = []
        for key, title, text, a in parts:
            text = '\n'.join(text)
            if title is None:
                h = re.search(r'^#{1,6}[ 　]+(.*?)[ 　]*(?:\{[^}]*\})?[ 　]*$', text, re.M)
                title = h.group(1) if h else key
            out.append((key, title, text, a))
        return '\n'.join(head), out, at
    fence = None
    for i, line in enumerate(lines):
        f = FENCE_LINE.match(line)
        if f:
            fence = None if fence == f.group(1) else (fence or f.group(1))
        m = None if fence or f else SECTION_HEADING.match(line)
        if m:
            ident = re.search(r'#([\w.:-]+)', m.group('attr') or '')
            key = ident.group(1) if ident else f'{len(parts) + 1:02d}'
            # スライドの題を別に決めてあれば（{slide-title="…"}）、それが回の題
            from . import crossref as xref
            title = xref.attr_value(m.group('attr') or '', 'slide-title') or m.group('title')
            parts.append([key, title, [], None])
            at.append(i)
        elif parts:
            parts[-1][2].append(line)
        else:
            head.append(line)
    return '\n'.join(head), [(k, t, '\n'.join(b), a) for k, t, b, a in parts], at


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
    for i, (key, title, _text, _a) in enumerate(parts):
        end = at[i + 1] - 1 if i + 1 < len(at) else last
        out.append((key, title, offset + at[i] + 1, offset + end + 1))
    return out


def section_keys(md: str) -> list:
    """[(印, 題)] — 原稿を回に分けたときの各回。"""
    _, body = split_front_matter(md)
    return [(k, t) for k, t, _, _ in _sections(body)[1]]


def section_part(md: str, key: str) -> str | None:
    """1回分だけの原稿を返す。なければ None。

    タイトル部分は、区切りに書いた title / subtitle / date / author / institute が
    優先。書いていなければ、題 = 回の最初の見出し（`#` で分ける原稿ならその `#`）、
    副題 = 原稿全体の題、日付などは原稿の front matter のまま。題にした見出しが
    回の頭にあれば落とす（残すとタイトルスライドのすぐ後に同じ題のスライドが出る）。
    最初の区切りより前（ノート全体の前置き）はどの回にも入れない。
    """
    meta, body = split_front_matter(md)
    for k, title, text, a in _sections(body)[1]:
        if k != key:
            continue
        marked = a is not None
        a = a or {}
        whole = meta.get('title')
        meta = {**meta, 'title': title}
        meta.pop('subtitle', None)
        if a.get('subtitle'):
            meta['subtitle'] = a['subtitle']
        elif whole:
            meta['subtitle'] = whole
        for f in ('date', 'author', 'institute'):
            if a.get(f):
                meta[f] = a[f]
        text = text.lstrip('\n')
        if marked and not a.get('title'):
            # 題にした見出しが回の頭にあれば落とす
            text = re.sub(r'\A#{1,6}[ 　]+.*\n?', '', text, count=1)
        return to_yaml_block(meta) + text.lstrip('\n')
    return None


def session_start_sections(md: str, key: str) -> tuple[int, bool]:
    """回のデッキの節番号を講義ノート全体とそろえるための (前の節の数, 回に `#` があるか)。

    区切りより前にある番号付きの `#` 見出しを数える。`#` で分ける原稿では、回そのものが
    `#` なので (その回の順番, False)。
    """
    meta, body = split_front_matter(md)
    _, parts, at = _sections(body)
    keys = [p[0] for p in parts]
    if key not in keys:
        return 0, False
    idx = keys.index(key)
    if parts[idx][3] is None:
        return idx + 1, False
    lines = drop_references(body).split('\n')
    fence, before = None, 0
    for line in lines[:at[idx]]:
        f = FENCE_LINE.match(line)
        if f:
            fence = None if fence == f.group(1) else (fence or f.group(1))
            continue
        m = None if fence else SECTION_HEADING.match(line)
        if m and not re.search(r'(?:^|\s)(?:\.unnumbered|-)(?:\s|$)', m.group('attr') or ''):
            before += 1
    # 題を取った `#` 見出しを落とした回は、その `#` がこの回の節
    a = parts[idx][3]
    first = next((l for l in parts[idx][2].split('\n') if l.strip()), '')
    m = SECTION_HEADING.match(first)
    if not a.get('title') and m and not re.search(
            r'(?:^|\s)(?:\.unnumbered|-)(?:\s|$)', m.group('attr') or ''):
        before += 1
    part = section_part(md, key) or ''
    _, ptext = split_front_matter(part)
    own = any(SECTION_HEADING.match(l) for l in ptext.split('\n') if not FENCE_LINE.match(l))
    return before, own


SLIDE_MARK = re.compile(r'^:{3,}\s*\{(?P<attr>(?:[^}]*\s)?\.slide(?:\s[^}]*)?)\}\s*$')
ANY_HEADING = re.compile(r'^(?P<hash>#{1,6})[ 　]+(?P<title>.*?)[ 　]*(?:\{(?P<attr>[^}]*)\})?[ 　]*$')


def slide_marks(md: str, slides: bool, lang: str = 'ja') -> str:
    """スライドの区切りと題を原稿で決める書き方を、出力に合わせて直す。

        ::: {.slide title="題"}     ここから新しいスライド（title を省くと直前の題に「（続き）」）
        :::
        ## 見出し {.same-slide}      この見出しでは新しいスライドにしない（前のスライドに続ける）
        ## 長い見出し {slide-title="短い題"}   スライドでだけ題を差し替える

    スライド（slides=True）では、区切りを1枚分の見出しに、`.same-slide` の見出しを
    太字の段落に、`slide-title` を見出しの題にする。それ以外の出力では、区切りを落とし、
    見出しはそのまま（属性は pandoc が無視する）。
    """
    from . import crossref as xref
    lines = md.split('\n')
    # スライド1枚になる見出しの段（typst-slides の決め方と同じ）: いちばん浅い段と
    # その1つ下があれば下の段、なければいちばん浅い段。講義の回は `#` が題になって
    # いるので、`##` 節・`###` スライドなら `###`、`##` だけなら `##`
    levels, fence = set(), None
    for line in lines:
        f = FENCE_LINE.match(line)
        if f:
            fence = None if fence == f.group(1) else (fence or f.group(1))
            continue
        h = None if fence else ANY_HEADING.match(line)
        if h:
            levels.add(len(h.group('hash')))
    top = min(levels) if levels else 1
    depth = top + 1 if (top + 1 in levels or not levels) else top
    cont = '（続き）' if lang == 'ja' else ' (cont.)'
    out, last_title, fence = [], '', None
    i = 0
    while i < len(lines):
        line = lines[i]
        f = FENCE_LINE.match(line)
        if f:
            fence = None if fence == f.group(1) else (fence or f.group(1))
            out.append(line)
            i += 1
            continue
        if fence:
            out.append(line)
            i += 1
            continue
        m = SLIDE_MARK.match(line)
        if m:
            # 中身のない div。閉じの `:::` まで飛ばす
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            end = j if j < len(lines) and DIV_CLOSE.match(lines[j]) else i
            if slides:
                title = xref.attr_value(m.group('attr'), 'title') or (last_title + cont).strip()
                out += ['', '#' * depth + ' ' + title + ' {.unnumbered}', '']
            i = end + 1
            continue
        h = ANY_HEADING.match(line)
        if h and slides and h.group('attr'):
            attr = h.group('attr')
            if re.search(r'(?:^|\s)\.same-slide(?:\s|$)', attr):
                out.append('**' + h.group('title') + '**')
                i += 1
                continue
            short = xref.attr_value(attr, 'slide-title')
            if short:
                line = f"{h.group('hash')} {short} {{{attr}}}"
                h = ANY_HEADING.match(line)
        if h and len(h.group('hash')) == depth:
            last_title = h.group('title')
        out.append(line)
        i += 1
    return '\n'.join(out)


def replace_session_markers(md: str, fmt) -> str:
    """区切りの div を fmt(属性) の返す文字列にする（A4 プリントの改ページと目印）。"""
    lines = md.split('\n')
    marks = _marker_lines(lines)
    if not marks:
        return md
    opens = {o: a for o, _, a in marks}
    closes = {c for _, c, _ in marks if c is not None}
    out = []
    n = 0
    for i, line in enumerate(lines):
        if i in opens:
            n += 1
            a = dict(opens[i])
            a.setdefault('id', f'{n:02d}')
            out.append(fmt(a))
        elif i not in closes:
            out.append(line)
    return '\n'.join(out)


def tidy_headings(md: str) -> str:
    """論文・プリントの本文から、組版に要らない行を落とす（水平線と作業用の注記）。

    見出しの番号は原稿に書かない（組版が振る）。参照は `{#sec-…}` のラベルで。
    """
    md = re.sub(r'^\s*---\s*$', '', md, flags=re.M)                       # 水平線
    md = re.sub(r'^\*\((?:In the )?(?:LaTeX|Typst|Word|Beamer).*?\)\*\s*$', '',
                md, flags=re.M | re.I)                                    # 作業用の注記
    md = re.sub(r'\n{3,}', '\n\n', md)
    return md.strip() + '\n'


# ---------------------------------------------------------------- 表・図

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

    原稿は図を**原稿から見た相対パス**で書く（`slides/x.md` なら `../assets/figures/…`、
    `papers/<名前>/paper.md` なら `../../assets/figures/…`）。エディタのプレビューに
    図が出るようにするためで、これは原稿の側の正しい書き方。

    ところが出力は `build/typst-slides/` や `build/typst/<名前>/` に置かれ、
    原稿と階層の深さが同じとはかぎらない。そのままコピーすると、同じ `../assets/figures/…`
    が `build/assets/figures/…` を指してしまい、typst compile が file not found で
    止まる（原稿は正しいのに組版だけ落ちる）。

    そこで原稿のパスをいったん実体に解決し、出力先から見た相対に振り直す。
    URL・絶対パス・データ URI はそのまま通す。
    """
    src_dir, out_dir = Path(src_dir).resolve(), Path(out_dir).resolve()
    if src_dir == out_dir:
        return md

    # コードブロック・インラインコードの中は書き換えない。原稿が「図はこう書く」と
    # 見本を載せていることがあり、そこを出力先からの相対に直すと読者に誤った内容を見せる
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
    未知の環境を渡さないため）。
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


# ---------------------------------------------------------------- \poscite

POSCITE = re.compile(r'\\poscite\{([\w:.#$%&+?<>~/-]+)\}')


def replace_poscite(md: str, formatter) -> str:
    """所有格引用 `\\poscite{key}`（"Smith and Taylor's (2003)"）を展開する。"""
    return POSCITE.sub(lambda m: formatter(m.group(1)), md)


CITE_KEY = re.compile(r'(?<![\w.@-])@([\w][\w:.#$%&+?<>~/-]*)')


def cited_keys(md: str, kinds=None) -> set:
    """本文が引いている citation key を集める（参考文献節より前だけ）。

    kinds は相互参照のラベルの頭（crossref.kinds_of）。省くと同梱の既定。
    """
    from . import crossref as xref
    kinds = tuple(kinds or xref.kinds_of())
    body = drop_references(md)
    # コードブロック（```{=typst} の `#import "@preview/…"` なども）を先に消す。
    # インラインコードを先に消すと、``` の最初の `` が空のインラインコードとして
    # 食われ、ブロックが丸ごと残る
    body = re.sub(r'^```.*?^```', '', body, flags=re.S | re.M)
    body = re.sub(r'`[^`\n]*`', '', body)          # インラインコード内は無視
    keys = set(CITE_KEY.findall(body)) | set(POSCITE.findall(body))
    # `@fig-…` などは相互参照で、引用ではない（crossref.py）
    return {k.rstrip('.,;:') for k in keys
            if not any(k.startswith(x + '-') for x in kinds)}


# ---------------------------------------------------------------- 検査

CJK = re.compile(r'[\u3000-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uff00-\uffef]')


def has_cjk(text: str) -> bool:
    return bool(CJK.search(text))


def cjk_lines(text: str) -> list:
    return [' '.join(l.split())[:70] for l in text.split('\n') if CJK.search(l)]


# ---------------------------------------------------------------- 数式のマクロ
# `\newcommand{\E}{\mathbb{E}}` のような1行の定義。pandoc（latex_macros）が数式の
# 中で展開するので、どの形式でも効く。ただし論文の要旨・付録・講義の回ごとの
# デッキは別々に pandoc に通すので、定義を集めてそれぞれの頭に付け直す
# （そうしないと、定義が本文の頭にあれば要旨で、要旨の前にあれば本文で効かない）。
MACRO_LINE = re.compile(r'^\\(?:newcommand|renewcommand|providecommand|'
                        r'DeclareMathOperator\*?)(?![A-Za-z]).*$')


def _macro_lines(md: str):
    """コードブロックの外にある定義の行を (行番号, 行) で。"""
    fence = None
    for i, line in enumerate(md.split('\n')):
        m = FENCE_LINE.match(line)
        if m:
            fence = None if fence == m.group(1) else (fence or m.group(1))
            continue
        if fence is None and MACRO_LINE.match(line.strip()):
            yield i, line.strip()


def math_macros(*texts: str) -> list:
    """原稿（と付録）にある数式のマクロの定義。同じ行は1回だけ、書いた順に。"""
    return list(dict.fromkeys(line for md in texts for _, line in _macro_lines(md)))


def drop_math_macros(md: str) -> str:
    """定義の行を抜く（付け直すので二重にしない。pandoc は再定義を警告して無視する）。"""
    drop = {i for i, _ in _macro_lines(md)}
    if not drop:
        return md
    return '\n'.join(l for i, l in enumerate(md.split('\n')) if i not in drop)


def drop_output_macros(text: str, macros: list) -> str:
    """pandoc の LaTeX 出力に素通りした定義の行を抜く。

    数式の中は pandoc がもう展開している。本文・要旨・付録のそれぞれに付け直した
    定義を残すと、main.tex が全部を読んだところで同じ名前の二重定義になる。
    """
    if not macros:
        return text
    want = set(macros)
    return '\n'.join(l for l in text.split('\n') if l.strip() not in want)


COMMENT = re.compile(r'<!--.*?-->', re.S)


def strip_comments(md: str) -> str:
    """HTML コメントを落とす。

    コメントは組版に届かないので、投稿規定の分量に数えてはいけない
    （`octavo new` のひな型は説明をコメントで書く）。コードブロックの中に
    書かれたコメントまで落ちるが、分量は目安なので許容する。
    """
    return COMMENT.sub('', md)


def _prose(md: str) -> str:
    """分量を数える対象だけにする。コメント、`{#fig-…}` などの属性、リンク先
    （図のファイル名・URL）は組まれた本文に出ないので数えない（リンクの文字は残す）。"""
    md = strip_comments(md)
    md = re.sub(r'\{[#.][^}\n]*\}', '', md)
    md = re.sub(r'(!?\[[^\]\n]*\])\([^)\n]*\)', r'\1', md)
    return re.sub(r'!?\[([^\]\n]*)\]', r'\1', md)


def word_count(md: str) -> tuple[int, int]:
    """語数（表を除く / 含む）。日本語混じりでは目安。"""
    md = _prose(md)

    def wc(t: str) -> int:
        return len(re.sub(r'[*_>#`]', ' ', t).split())
    excl = wc('\n'.join(l for l in md.split('\n') if not l.strip().startswith('|')))
    return excl, wc(md)


def char_count(md: str) -> int:
    """日本語論文向け: 空白・改行・Markdown 記号を除いた文字数。"""
    return len(re.sub(r'[\s*_>#`|]', '', _prose(md)))


def read(path: Path) -> str:
    return path.read_text(encoding='utf-8')
