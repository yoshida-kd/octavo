# -*- coding: utf-8 -*-
"""octavo migrate --syntax: 原稿の記法を、前からの書き方から今の書き方へ書き換える。

    ::: {.session #id title="題" date="…"}   ->  \\session{題} {#id date="…"}
    :::
    ::: {.slide title="題"}                  ->  \\newslide{題}
    :::
    ::: {.slide .no-title}                   ->  \\newslide{}
    ::: {.slide}                             ->  \\newslide
    .handout-only / .no-handout              ->  .no-slides / .slides-only

前からの書き方もそのまま組めるので、これは書き換えたい人のためのもの。
**書き換えたあとに組み直し、出力が前と1文字も変わらないことを確かめる。**
違えばその文書は元に戻す。

`.handout-only` は A4 プリントの体裁の PDF・Word・LaTeX のどれにも残り、スライドと台本には
出ない。プリントの体裁の文書なら `.no-slides` と同じ（`.pdf-only` は PDF だけなので違う）。
ただし `.no-slides` はポスターにも出るので、ポスターも作る文書と、プリントの体裁でない文書
では意味が変わる。その文書では書き換えずに知らせる。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import md as mdlib
from .i18n import t

SESSION_KEYS = ('subtitle', 'date', 'author', 'institute')
# `.handout-only` `only-handout` `no-handout` `not-handout`（点のない囲みの名前も）
HANDOUT = re.compile(r'(?<![\w-])(\.?)(handout-only|only-handout|no-handout|not-handout)(?![\w-])')
HANDOUT_NEW = {'handout-only': 'no-slides', 'only-handout': 'no-slides',
               'no-handout': 'slides-only', 'not-handout': 'slides-only'}
SPAN_ATTR = re.compile(r'(\]\{)([^}]*)(\})')


@dataclass
class Change:
    line: int            # 1 始まり（書き換える前の原稿の行）
    old: str
    new: str             # 空なら行を消す


@dataclass
class Plan:
    path: Path
    text: str            # 書き換えたあとの全文
    changes: list = field(default_factory=list)
    left: list = field(default_factory=list)      # [(行, 理由)] 書き換えなかったもの


def write_like(path: Path, text: str, original: bytes) -> None:
    """元のファイルと同じ改行（CRLF か LF）で書く（Windows で改行が変わらないように）。"""
    nl = '\r\n' if b'\r\n' in original else '\n'
    path.write_bytes(text.replace('\r\n', '\n').replace('\n', nl).encode('utf-8'))


def _empty_until_close(lines: list, i: int) -> int | None:
    """i の次から空行だけを挟んで閉じの `:::` があれば、その行。"""
    j = i + 1
    while j < len(lines) and not lines[j].strip():
        j += 1
    return j if j < len(lines) and mdlib.DIV_CLOSE.match(lines[j]) else None


def _hidden_lines(text: str) -> set:
    """コードブロックと HTML のコメントの中の行（0 始まり）。"""
    out, fence = set(), None
    for i, line in enumerate(text.split('\n')):
        f = mdlib.FENCE_LINE.match(line)
        if f:
            fence = None if fence == f.group(1) else (fence or f.group(1))
            out.add(i)
        elif fence:
            out.add(i)
    for m in re.finditer(r'<!--.*?-->', text, re.S):
        a = text.count('\n', 0, m.start())
        out.update(range(a, a + m.group(0).count('\n') + 1))
    return out


def _quote(v: str) -> str | None:
    return None if '"' in v else f'"{v}"'


def _session_line(attr: str) -> str | None:
    """`::: {.session …}` の属性から `\\session{題} {…}`。書き表せなければ None。"""
    a = mdlib.session_attrs(attr)
    # 知っている属性のほかに何か書いてあれば、書き換えない（意味を落とさない）
    rest = re.sub(r'(?:^|\s)\.session(?=\s|$)', ' ', attr)
    rest = re.sub(r'(?:^|\s)#[\w.:-]+', ' ', rest)
    rest = re.sub(r'(?:^|\s)(?:title|subtitle|date|author|institute)=(?:"[^"]*"|\S+)', ' ', rest)
    if rest.strip():
        return None
    title = a.get('title', '')
    if '}' in title or '{' in title:
        return None
    attrs = []
    if 'id' in a:
        attrs.append('#' + a['id'])
    for k in SESSION_KEYS:
        if k in a:
            q = _quote(a[k])
            if q is None:
                return None
            attrs.append(f'{k}={q}')
    return f'\\session{{{title}}}' + (' {' + ' '.join(attrs) + '}' if attrs else '')


def _newslide(attr: str) -> str | None:
    """`::: {.slide …}` の属性から `\\newslide…`。書き表せなければ None。"""
    from . import crossref as xref
    rest = re.sub(r'(?:^|\s)\.(?:slide|no-title)(?=\s|$)', ' ', attr)
    rest = re.sub(r'(?:^|\s)title=(?:"[^"]*"|\S+)', ' ', rest)
    if rest.strip():
        return None
    if mdlib.NO_TITLE.search(attr):
        return '\\newslide{}'
    title = xref.attr_value(attr, 'title')
    if title is None or not title.strip():
        return '\\newslide'
    if '{' in title or '}' in title:
        return None
    return f'\\newslide{{{title.strip()}}}'


def plan(path: Path, text: str, handout_ok: bool, handout_why: str) -> Plan:
    """1つの原稿の書き換え。handout_ok なら `.handout-only` も書き換える（でなければ
    handout_why を理由にして残す）。コードと HTML のコメントの中は見ない。"""
    lines = text.split('\n')
    out = Plan(path, text)
    new = list(lines)
    hidden = _hidden_lines(text)
    skip_close: set = set()
    for i, line in enumerate(lines):
        if i in skip_close:
            new[i] = None
            continue
        if i in hidden:                    # コードやコメントの中
            continue
        m = mdlib.SESSION_OPEN.match(line)
        if m:
            close = _empty_until_close(lines, i)
            repl = _session_line(m.group('attr'))
            if repl is None:
                out.left.append((i + 1, t('a session marker with attributes the one-line form '
                                          'cannot hold')))
                continue
            new[i] = repl
            out.changes.append(Change(i + 1, line, repl))
            if close is not None:
                for j in range(i + 1, close):
                    new[j] = None          # 区切りの中の空行
                skip_close.add(close)
            else:
                # 中身のある区切り: 中身はその回の頭に残り、閉じの行が落ちる（今と同じ）
                depth, cl = 1, None
                for j in range(i + 1, len(lines)):
                    if mdlib.DIV_CLOSE.match(lines[j]):
                        depth -= 1
                        if depth == 0:
                            cl = j
                            break
                    elif mdlib.DIV_OPEN.match(lines[j]):
                        depth += 1
                if cl is not None:
                    skip_close.add(cl)
            continue
        m = mdlib.SLIDE_MARK.match(line)
        if m:
            close = _empty_until_close(lines, i)
            repl = _newslide(m.group('attr')) if close is not None else None
            if repl is None:
                out.left.append((i + 1, t('a slide marker with contents or other attributes')))
                continue
            new[i] = repl
            out.changes.append(Change(i + 1, line, repl))
            for j in range(i + 1, close):
                new[j] = None
            skip_close.add(close)
            continue
        # `.handout-only` など（囲みの開きと、行の中の [..]{.…}）
        targets = []
        d = mdlib.DIV_OPEN.match(line.strip())
        if d and not mdlib.DIV_CLOSE.match(line.strip()):
            targets.append('div')
        if SPAN_ATTR.search(line):
            targets.append('span')
        if not targets or not HANDOUT.search(line):
            continue
        if not handout_ok:
            out.left.append((i + 1, handout_why))
            continue

        def fix(s: str) -> str:
            return HANDOUT.sub(lambda h: h.group(1) + HANDOUT_NEW[h.group(2)], s)
        if 'div' in targets:
            changed = fix(line)
        else:
            changed = SPAN_ATTR.sub(lambda sp: sp.group(1) + fix(sp.group(2)) + sp.group(3), line)
        if changed != line:
            new[i] = changed
            out.changes.append(Change(i + 1, line, changed))
    for c in sorted(skip_close):
        out.changes.append(Change(c + 1, lines[c], ''))
    out.changes.sort(key=lambda c: c.line)
    out.text = '\n'.join(x for x in new if x is not None)
    return out


def handout_rule(cfg, doc) -> tuple[bool, str]:
    """この文書で `.handout-only` を `.no-slides` に書き換えてよいか、だめならその理由。"""
    from .config import OUTPUT_OF
    if doc.profile != 'handout':
        return False, t('.handout-only: this document is not in the handout layout, so '
                        '.handout-only shows in none of its outputs — left as it is')
    if 'poster' in {OUTPUT_OF.get(x, x) for x in doc.targets}:
        return False, t('.handout-only: this document also makes a poster, where '
                        '.no-slides shows but .handout-only does not — left as it is')
    return True, ''


# ---------------------------------------------------------------- 実行

def _outputs(results) -> dict:
    """組んだ出力の中身 {path: bytes}（比べるため）。docx は本文の XML。"""
    import zipfile
    got = {}
    for r in results:
        for p in r.outputs:
            p = Path(p)
            if not p.is_file():
                continue
            if p.suffix == '.docx':
                try:
                    with zipfile.ZipFile(p) as z:
                        got[str(p)] = z.read('word/document.xml')
                except (OSError, KeyError, zipfile.BadZipFile):
                    got[str(p)] = p.read_bytes()
            else:
                got[str(p)] = p.read_bytes()
    return got


def _build(cfg, doc) -> dict:
    import contextlib
    import io
    from . import build
    with contextlib.redirect_stdout(io.StringIO()):
        res = build.run(cfg, [doc.name], appendix=bool(doc.appendix), offline=True,
                        citations=False)
    return _outputs(res)


def run(cfg, dry_run: bool = False, check: bool = True, allow_dirty: bool = False) -> int:
    import shutil
    from . import config as configmod
    from .relocate import _git
    plans = []              # [(doc, [Plan])]
    for doc in cfg.documents.values():
        ok, why = handout_rule(cfg, doc)
        ps = []
        for p in [doc.src] + ([doc.appendix] if doc.appendix and Path(doc.appendix).is_file() else []):
            ps.append(plan(Path(p), mdlib.read(p), ok, why))
        plans.append((doc, ps))
    total = sum(len(p.changes) for _, ps in plans for p in ps)
    for doc, ps in plans:
        for p in ps:
            for line, why in p.left:
                print(f'  {cfg.rel(p.path)}:{line}  ' + t('left as it is') + f' — {why}')
    if not total:
        print(t('nothing to rewrite: the manuscripts already use the current notation'))
        return 0
    head = '(' + t('dry run') + ') ' if dry_run else ''
    for doc, ps in plans:
        for p in ps:
            for c in p.changes:
                new = c.new if c.new else '(' + t('line removed') + ')'
                print(f'{head}{cfg.rel(p.path)}:{c.line}  {c.old.strip()}  ->  {new}')
    if dry_run:
        print(t('nothing was changed (drop --dry-run to rewrite them)'))
        return 0
    root = cfg.root
    if not allow_dirty and _git(root, 'rev-parse', '--is-inside-work-tree').returncode == 0:
        paths = [str(p.path) for _, ps in plans for p in ps if p.changes]
        dirty = _git(root, 'status', '--porcelain', '--', *paths).stdout.strip()
        if dirty:
            print(t('there are uncommitted changes in the manuscripts — commit them first, so '
                    'the rewrite is a change of its own') + '\n' + dirty + '\n\n' + t(
                'next: {commit}, then {migrate} (or {dirty} to rewrite them as they are)',
                commit='git commit -am "…"', migrate='octavo migrate --syntax',
                dirty='octavo migrate --syntax --allow-dirty'))
            return 1
    can_check = check and shutil.which('pandoc') is not None
    if check and not can_check:
        print(t('pandoc is not found, so the outputs could not be compared before and after'))
    failed = 0
    for doc, ps in plans:
        todo = [p for p in ps if p.changes]
        if not todo:
            continue
        before = _build(cfg, doc) if can_check else None
        originals = {p.path: p.path.read_bytes() for p in todo}
        for p in todo:
            write_like(p.path, p.text, originals[p.path])
        if before is None:
            print(t('rewrote {name}', name=doc.name))
            continue
        after = _build(configmod.load(cfg.source), configmod.load(cfg.source).document(doc.name))
        diff = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
        if diff:
            for path, data in originals.items():
                path.write_bytes(data)
            _build(cfg, doc)                      # 出力も前の原稿のものに戻す
            failed += 1
            print(t('{name}: the outputs changed, so it was put back as it was:', name=doc.name))
            for k in diff[:8]:
                print('    ' + cfg.rel(Path(k)))
        else:
            print(t('rewrote {name} — every output is the same as before ({n} {n|file|files})',
                    name=doc.name, n=len(after)))
    return 1 if failed else 0
