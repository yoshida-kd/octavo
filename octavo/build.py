# -*- coding: utf-8 -*-
"""変換の本体。

前処理 → pandoc → 後処理、という1本の流れをここに置く。形式ごとの違いは
すべて backends/ 側の Backend が持つ。**この関数が形式名で分岐しない**ことを
保つのが、形式を足しやすくしておく肝。
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from . import backends as be
from . import bib as bibmod
from . import crossref as xref
from . import config as confmod
from . import csl as cslmod
from . import md as mdlib
from . import pandocrun
from . import theorems
from . import values as valmod
from .backends.base import Ctx
from .i18n import t, tag


@dataclass
class Result:
    doc: str
    target: str
    outputs: list = field(default_factory=list)
    report: list = field(default_factory=list)
    next_step: str = ''
    compiled: Path | None = None
    ok: bool = True


# ------------------------------------------------------------ 体裁ファイル

def sync_layout(cfg, doc, ctx: Ctx) -> None:
    """手で書く体裁ファイル（main.typ / main.tex）を原稿の隣から out_dir へコピーする。

    正本は `papers/<名前>/main.typ`。組版は out_dir で行い、body.typ や
    abstract.typ はそこに生成されるので、組む直前に同じ場所へコピーしておく。
    こうしておくと `build/` は丸ごと生成物になり、消しても体裁は残る。
    """
    name = ctx.backend.main_name
    if ctx.standalone or not name:
        return
    src = Path(doc.src).parent / name
    dest = ctx.out_dir / name
    if not src.is_file():
        # main.tex は既定では作らない（TeX は任意）。足し方をここで言う
        cmd = f'octavo new paper {doc.name}' + (' --tex' if name.endswith('.tex') else '')
        ctx.say(f'{tag("layout")} ' + t('no {file} beside the manuscript — add it with: {cmd}',
                                         file=cfg.rel(src), cmd=cmd))
        return
    text = src.read_text(encoding='utf-8')
    if not dest.is_file() or dest.read_text(encoding='utf-8') != text:
        dest.write_text(text, encoding='utf-8')
    ctx.say(f'{tag("layout")} {cfg.rel(src)}')


# ---------------------------------------------------------------- 前処理

def citation_filter(cfg, ctx: Ctx):
    """日本語の文書なら、文献を言語ごとに組むフィルター（citations/japanese.lua）。

    pandoc の citeproc は書誌全体を1つの言語で組むので、日本語（ja-JP）のままだと英語の
    文献まで「Smith ほか (2003年)」になる。フィルターは英語の決まりで組んでから、
    日本語の文献（langid = {japanese}）だけを「山田・田中」「」『』の形に直す。
    """
    if not cfg['citations_by_language'] or not str(cfg['csl_locale']).startswith('ja'):
        return None
    return ctx.template('citations/japanese.lua')


def citation_form_args(cfg, ctx: Ctx) -> list:
    """日本語の文献の形（japanese_citation_form）を、フィルターにメタデータで渡す。"""
    if citation_filter(cfg, ctx) is None:
        return []
    return ['-M', f'octavo-ja-form={cfg["japanese_citation_form"]}']


def preprocess(cfg, doc, backend, ctx: Ctx, raw: str) -> tuple:
    """原稿を pandoc に渡せる形にする。(markdown, abstract) を返す。"""
    meta, body = mdlib.split_front_matter(raw)
    # 分析が出した数値を先に入れる。以降の処理（要旨の切り出し、表・図の
    # 差し替え、分量の勘定）はすべて「数値が入ったあとの本文」を見る。
    body = valmod.substitute(body, ctx.values, cfg, ctx.report)
    ctx.meta = {**(cfg['meta'] or {}), **doc.meta, **meta}
    if 'lang' in ctx.meta:
        ctx.meta['lang_short'] = str(ctx.meta['lang'])[:2]
    if ctx.meta.get('date'):
        ctx.meta['date'] = display_date(ctx.meta['date'], cfg['date_format'], ctx.lang)

    body = mdlib.drop_references(body)
    # 数式のマクロは抜いておき、最後に頭へ付け直す（要旨にも）
    body = mdlib.drop_math_macros(body)
    macros = '\n'.join(ctx.math_macros)

    abstract = ''
    if ctx.profile_opt('abstract'):
        abstract, body = mdlib.split_abstract(body)
    if doc.profile == 'paper' and not doc.derived:
        # 旧来の論文だけ: 最初の見出しより前と、1つだけの `# 題` を捨てる。
        # docs/<名前>/ の文書は題を冒頭の title: にだけ書く約束なので、見出しはすべて本文
        body = mdlib.strip_title_block(body)

    body = select_marked(cfg, doc, backend, ctx, body)
    body = mdlib.filter_divs(body, ctx.keep_classes,
                             keep_notes=backend.keeps_notes,
                             report=ctx.report,
                             notes_wrap=backend.notes_wrap,
                             notes_mark=backend.notes_mark)
    # スライドの区切りと題（`::: {.slide}`、`{.same-slide}`、`{slide-title=…}`）
    body = mdlib.slide_marks(body, backend.is_slides, ctx.lang, level=ctx.slide_level)
    # 改ページ（`\newpage`）。スライドでは何もしない（区切りは `\newslide`）
    body = mdlib.page_breaks(body, backend.fmt_pagebreak(ctx))
    # 回の区切り（A4 プリントでは改ページと、octavo extract が読む目印）
    if mdlib.has_session_markers(body):
        ctx.has_sessions = True
        body = mdlib.replace_session_markers(body, lambda a: backend.fmt_session(a, ctx))
    # 再掲・一覧を、元のブロックの写しにする（写した本文の参照も後で解決される）
    body = theorems.expand(body, ctx.theorem_blocks, ctx.envs, ctx.report)
    body = mdlib.replace_poscite(body, lambda k: backend.fmt_poscite(k, ctx))
    if doc.profile in ('paper', 'handout') and backend.tidy_headings:
        body = mdlib.tidy_headings(body)
    body, known = apply_crossrefs(body, doc, backend, ctx)
    if abstract:
        abstract = xref.replace_references(
            abstract, known, lambda it, short: backend.fmt_ref(it, short, ctx), ctx.report,
            kinds=xref.kinds_of(ctx.envs))

    # 見出しの深さ: `# 見出し` があるならそのまま、なければ `##` を最上位とみなす
    ctx.shift_headings = 0 if re.search(r'^# \S', body, re.M) else -1

    # 要旨を本文に戻す形式（main.tex を持たないもの）
    # （印の所だけで組むなら戻さない。載せたい要旨は `# Abstract {.on-poster}` と印を付ける）
    if abstract and not backend.wants_abstract_file and ctx.standalone \
            and not marked_only(cfg, backend):
        head = '要旨' if ctx.lang == 'ja' else 'Abstract'
        lead = '#' if ctx.shift_headings == 0 else '##'
        body = f'{lead} {head} {{.unnumbered}}\n\n{abstract}\n\n{body}'

    if macros:
        body = f'{macros}\n\n{body}'
        if abstract:
            abstract = f'{macros}\n\n{abstract}'
    if ctx.standalone:
        body = mdlib.to_yaml_block(_pandoc_meta(cfg, ctx)) + body
    return body, abstract


PRINTED = ('typst', 'docx', 'latex')


def fixes_numbers(doc, backend) -> bool:
    """このデッキの番号をプリントの番号に合わせるか。プリントも作る文書の Typst のスライドと
    台本だけ（スライドしか作らない発表には、合わせる相手がない）。"""
    return backend.fixed_numbering and any(b in doc.targets for b in PRINTED)


def handout_numbers(cfg, doc, ctx: Ctx) -> dict:
    """プリントでの番号（ラベル -> crossref.Item）。原稿全体を、プリントと同じ出し分けで数える。"""
    _, body = mdlib.split_front_matter(mdlib.read(Path(doc.src)))
    body = mdlib.drop_math_macros(mdlib.drop_references(body))
    body = xref.autolabel(body, ctx.envs)
    keep = {'print', 'doc', 'typst', 'pdf', doc.profile} | ({'anonymous'} if ctx.anonymous else set())
    body = mdlib.filter_divs(body, keep)
    return xref.number(body, ctx.numbering_mode(), start=ctx.first_section,
                       envs=ctx.envs).labels()


def marked_only(cfg, backend) -> tuple | None:
    """この出力が「印の所だけ」で組むなら (印のクラス, 一緒に残す囲み)。"""
    sel = backend.select_mark
    return (sel[1], sel[2]) if sel and cfg[sel[0]] == 'marked' else None


def select_marked(cfg, doc, backend, ctx: Ctx, body: str) -> str:
    """`slides_select: marked` などのとき、印の所だけを残す（md.select_marked）。

    拾わなかった図・表・節を指す参照は、文書全体での番号を文字で書く（スライドに
    ないラベルを Typst が探して止まらないように）。そのため全体の番号を先に数えておく。
    講義の回のデッキは sibling_crossrefs が講義ノート全体から数えてある。
    """
    sel = marked_only(cfg, backend)
    if not sel:
        return body
    if doc.part is None:
        whole = mdlib.filter_divs(body, ctx.keep_classes, keep_notes=backend.keeps_notes)
        ctx.crossrefs = {**xref.number(whole, ctx.numbering_mode(), start=ctx.first_section,
                                       envs=ctx.envs).labels(), **ctx.crossrefs}
    picked = mdlib.select_marked(body, *sel)
    ctx.say(f'{tag("select")} ' + t('only the parts marked .{mark} ({key}: marked)',
                                    mark=sel[0], key=backend.select_mark[0]))
    return picked


def display_date(value, fmt: str | None, lang: str) -> str:
    """タイトル部分の日付。`today` は組んだ日、`2026-10-14` は date_format の形に。
    それ以外（「2026年度前期」など）はそのまま。"""
    import datetime
    s = str(value).strip()
    if s.lower() in ('today', 'now'):
        d = datetime.date.today()
    else:
        m = re.fullmatch(r'(\d{4})-(\d{1,2})-(\d{1,2})', s)
        if not m:
            return s
        try:
            d = datetime.date(*(int(x) for x in m.groups()))
        except ValueError:
            return s
    fmt = fmt or ('%Y年%-m月%-d日' if lang == 'ja' else '%B %-d, %Y')
    # %-m / %-d（0 を付けない）は Windows の strftime にないので、先に自分で埋める
    fmt = fmt.replace('%-m', str(d.month)).replace('%-d', str(d.day))
    months = ('January', 'February', 'March', 'April', 'May', 'June', 'July',
              'August', 'September', 'October', 'November', 'December')
    # %B もロケールに左右されないように英語の月名で埋める
    fmt = fmt.replace('%B', months[d.month - 1])
    return d.strftime(fmt)


def apply_crossrefs(body: str, doc, backend, ctx: Ctx) -> tuple:
    """図・表・式・節のラベルと参照（crossref.py）。(本文, 知っているラベル) を返す。

    1. この原稿を文書の順に数える（番号を組版側が振らない形式のために）
    2. Word など番号を振らない形式なら、見出し・キャプション・式に番号を文字で入れる
    3. 本文の `@fig-…` を形式ごとの参照に
    4. 図を形式に合わせ、分析が書いた表（中身のないキャプション）を差し込む
    どの段も行を増減させないので、1 で覚えた行番号が 2 まで使える（4 は最後）。
    """
    top = 1 if ctx.crossref_section is not None else xref.top_level(body)
    nums = xref.number(body, ctx.numbering_mode(), appendix=ctx.appendix, top=top,
                       section=ctx.section_before, start=ctx.section_start,
                       envs=ctx.envs)
    for lab in nums.duplicates():
        ctx.say(f'{tag("crossref")} ' + t('the label {label} is used twice', label='#' + lab))
    here = nums.labels()
    ctx.crossref_local |= set(here)
    known = {**ctx.crossrefs, **here}

    lines = body.split('\n')
    if not backend.numbers_itself:
        for it in nums.items:
            lines[it.line] = _number_in_text(lines[it.line], it, ctx)
        body = xref.label_equations('\n'.join(lines),
                                    tag_for=lambda lab: f'({known[lab].number})')
    else:
        body = xref.label_equations(body)
    body = xref.replace_references(
        body, known, lambda it, short: backend.fmt_ref(it, short, ctx), ctx.report,
        kinds=xref.kinds_of(ctx.envs))

    lines = body.split('\n')
    external = {it.line: it for it in nums.items if it.external}
    # 図・表の直後の出典・注（`::: {.figure-note}`）。図表と1つにまとめて組む
    groups, stray = xref.figure_notes(lines)
    for i in stray:
        ctx.say(f'{tag("figure")} ' + t('line {n}: ::: {.figure-note} is not right after a figure '
                                        'or table, so it is set as a plain paragraph', n=i + 1))
    noted = {g[0] for g in groups if g[3] == 'fig'}
    appendix_started = ctx.appendix
    for i, line in xref._lines_outside_code(body):
        s = line.strip()
        m = xref.IMAGE.match(s)
        if m:
            lines[i] = backend.fmt_figure(m, xref.label_in(m.group('attr'), 'fig'), ctx,
                                          note=i in noted)
            continue
        it = external.get(i)
        if it:
            cap = xref.TABLE_CAPTION.match(s).group('cap')
            lines[i] = backend.fmt_external_table(it.label[len('tbl-'):], cap, it.label, ctx)
            continue
        h = xref.HEADING.match(line)
        if h and not appendix_started and xref.appendix_heading(h.group('attr')):
            # `# 論点・事例集 {.appendix}` — ここから付録（A, B, …）
            appendix_started = True
            lines[i] = backend.fmt_appendix_start(ctx) + '\n' + lines[i]
    for start, open_, close, kind in groups:
        lines[close] = backend.fmt_figure_note('close', kind, ctx)
        lines[open_] = backend.fmt_figure_note('middle', kind, ctx)
        head = backend.fmt_figure_note('open', kind, ctx)
        if head:
            lines[start] = head + '\n' + lines[start]
    # 事例・論点などのブロックと、再掲・一覧の写し
    lines = theorems.render(lines, {it.line: it for it in nums.items if it.kind in ctx.envs},
                            ctx.theorem_blocks, ctx.envs, backend, ctx)
    return '\n'.join(lines), known


def _number_in_text(line: str, it, ctx: Ctx) -> str:
    """番号を振らない形式（Word）のために、見出し・キャプションへ番号を書き込む。"""
    if it.kind == 'sec':
        if ctx.profile == 'slides':
            return line
        m = xref.HEADING.match(line)
        if it.appendix and it.level == 1:
            head = f'付録{it.number}．' if ctx.lang == 'ja' else f'Appendix {it.number}. '
        elif it.level == 1:
            head = f'{it.number}. '
        else:
            head = f'{it.number}　' if ctx.lang == 'ja' else f'{it.number} '
        return f'{m.group("hash")} {head}{line[m.start("title"):].lstrip()}'
    if it.kind == 'fig':
        return re.sub(r'!\[', '![' + xref.caption_head('fig', it.number, ctx.lang), line, count=1)
    if it.kind == 'tbl':
        return re.sub(r'^(\s*(?:Table)?:[ \t]+)',
                      lambda m: m.group(1) + xref.caption_head('tbl', it.number, ctx.lang),
                      line, count=1)
    return line


def sibling_crossrefs(cfg, doc, backend, ctx: Ctx, appendix: bool) -> None:
    """この出力の外にあるラベル（論文の付録／本文、講義のほかの回）を ctx に入れる。

    論文の本文と付録は、main.* が付録を読み込んでいれば1つの文書なので、互いの
    参照は組版側が張れる（local）。読み込んでいない（同梱の main.* の既定）か、
    Word のように別のファイルになるなら、番号を文字で書く — そうしないと組版が
    「ラベルがない」で止まり、Word ではリンクが切れる。講義の回ごとのデッキも別の
    PDF なので、ほかの回への参照は番号を文字で書く。
    """
    def prepared(path: Path, is_appendix: bool) -> str:
        _, body = mdlib.split_front_matter(mdlib.read(path))
        body = mdlib.drop_math_macros(mdlib.drop_references(body))
        if ctx.profile_opt('abstract') and not is_appendix:
            _, body = mdlib.split_abstract(body)
        if doc.profile == 'paper' and not doc.derived and not is_appendix:
            body = mdlib.strip_title_block(body)
        # 再掲に写す本文にも、数値と図のパスの直しが要る（行の数は変わらない）
        body = mdlib.rebase_links(body, Path(path).parent, ctx.out_dir)
        body = valmod.substitute(body, ctx.values, cfg)
        return mdlib.filter_divs(body, ctx.keep_classes, keep_notes=backend.keeps_notes)

    mode = ctx.numbering_mode()
    envs = ctx.envs
    first = ctx.first_section
    if doc.part is not None and not appendix:
        whole = mdlib.read(Path(doc.src))
        before, own = mdlib.session_start_sections(whole, doc.part)
        if own:
            # 回のデッキに自分の `#` がある: 講義ノートでその前にある `#` の数から数え始める
            ctx.crossref_preset = before
        elif before > 0:
            # `#` のない回: 講義ノートでいまいる節の番号を決め打ちにする
            ctx.crossref_section = before + first - 1
        text = prepared(Path(doc.src), False)
        ctx.crossrefs = xref.number(text, mode, start=first, envs=envs).labels()
        ctx.theorem_blocks = theorems.collect([(text, False)], envs, mode, first)
        return
    sources = [(prepared(Path(doc.appendix if appendix else doc.src), appendix), appendix)]
    other = doc.src if appendix else doc.appendix
    if doc.profile == 'paper' and other and Path(other).is_file():
        text = prepared(Path(other), not appendix)
        sources.append((text, not appendix))
        sources.sort(key=lambda x: x[1])          # 本文、付録の順
        items = xref.number(text, mode, appendix=not appendix, envs=envs).labels()
        ctx.crossrefs = items
        layout = Path(doc.src).parent / backend.main_name if backend.main_name else None
        if layout and layout.is_file() and backend.includes_appendix(
                layout.read_text(encoding='utf-8')):
            ctx.crossref_local |= set(items)
    ctx.theorem_blocks = theorems.collect(sources, envs, mode, first)


def _pandoc_meta(cfg, ctx: Ctx) -> dict:
    """standalone 出力のタイトル部分に渡すメタデータ。

    匿名審査のときは著者が分かるものを落とす。**落とすキーは config で
    決める**（雑誌によって何を伏せるかが違うため）。
    """
    keys = ('title', 'subtitle', 'author', 'institute', 'date', 'keywords',
            'abstract', 'description', 'thanks')
    drop = set(cfg['anonymous_drop_meta'] or ()) if ctx.anonymous else set()
    m = {k: v for k, v in ctx.meta.items() if k in keys and k not in drop}
    m.setdefault('lang', 'ja-JP' if ctx.lang == 'ja' else 'en-US')
    return m


# ---------------------------------------------------------------- 1形式ぶんの変換

def build_one(cfg, doc, target: str, appendix: bool = False,
              do_compile: bool = False, offline: bool = False,
              citations: bool = True, anonymous: bool = False) -> Result:
    """例外は投げない。失敗は Result.ok = False と report で返す。"""
    try:
        return _build_one(cfg, doc, target, appendix, do_compile, offline,
                          citations, anonymous)
    except (pandocrun.PandocError, cslmod.CSLError, OSError) as e:
        r = Result(doc=doc.name, target=target, ok=False)
        r.report.append(f'{tag("stopped")} {e}')
        return r


def _build_one(cfg, doc, target: str, appendix: bool, do_compile: bool,
               offline: bool, citations: bool, anonymous: bool = False) -> Result:
    backend = be.get(target)
    res = Result(doc=doc.name, target=target)

    try:
        pandocrun.require(*backend.min_pandoc,
                          why=t('needed to write {what}', what=t(backend.label)))
    except pandocrun.PandocError as e:
        res.ok = False
        res.report.append(f'{tag("stopped")} {e}')
        return res

    src = doc.appendix if appendix else doc.src
    if not src or not Path(src).is_file():
        res.ok = False
        res.report.append(f'{tag("stopped")} ' + t('no manuscript at {path}', path=src))
        return res

    # 原稿の冒頭に書いた文書ごとの設定（CSL・上限・スライドの体裁）を重ねる。
    # 付録も本体の原稿の設定で組む
    cfg = cfg.for_document(doc)

    out_dir = cfg.out_dir(target, doc)
    out_dir.mkdir(parents=True, exist_ok=True)

    ctx = Ctx(cfg=cfg, backend=backend, out_dir=out_dir, profile=doc.profile,
              doc_name=doc.name if not appendix else f'{doc.name}-appendix',
              appendix=appendix, anonymous=anonymous, document=doc,
              build_opts={'offline': offline, 'citations': citations,
                          'anonymous': anonymous})
    if cfg.doc_explicit:
        shown = {k: (', '.join(doc.outputs) if k in ('outputs', 'targets') else cfg[k])
                 for k in sorted(cfg.doc_explicit)}
        ctx.say(f'{tag("settings")} ' + t('from the manuscript: {settings}', settings=', '.join(
            f'{k}: {v}' for k, v in shown.items())))
    for wrote, key in confmod.doc_setting_typos(doc.src):
        ctx.say(f'{tag("settings")} ' + t('{wrote} is not a setting and is ignored — did you mean {key}?',
                                         wrote=wrote, key=key))
    if anonymous:
        ctx.say(f'{tag("anonymous")} ' + t('building with anything identifying hidden '
                                          '(::: {.no-anonymous} blocks and the '
                                          'title-block metadata)'))
    ctx.entries = bibmod.parse(cfg['bib_file'])
    ctx.values, warn = valmod.load(cfg)
    for line in warn:
        ctx.say(line)
    # 仮の値のまま組むと、本文に仮の数字が入る。毎回言う（build が黙っていると
    # 気づけない唯一の種類の誤り。手書きの assets/values/*.json には印がないので鳴らない）
    for f in valmod.placeholder_files(cfg):
        ctx.say(f'{tag("values")}{tag("note")} ' + t(
            '{file} is still the starter values octavo wrote. The numbers in '
            'the text are fake (octavo analysis run makes them real)', file=f))

    sync_layout(cfg, doc, ctx)
    backend.prepare(ctx)

    raw = mdlib.read(Path(src))
    # 数式のマクロは本文と付録で共有する（回ごとに分ける前の、ファイル全体から集める）
    ctx.math_macros = mdlib.math_macros(*(
        mdlib.read(Path(p)) for p in (doc.src, doc.appendix) if p and Path(p).exists()))
    sibling_crossrefs(cfg, doc, backend, ctx, appendix)
    if fixes_numbers(doc, backend) and not appendix:
        # スライドの図・表・式・ブロックの番号を、プリントでの番号に合わせる
        raw = xref.autolabel(raw, ctx.envs)
        handout = handout_numbers(cfg, doc, ctx)
        ctx.fixed_numbers = {lab: it.number for lab, it in handout.items()}
        ctx.crossrefs = {**ctx.crossrefs, **handout}
    if doc.part is not None and not appendix:
        # 1枚の見出しの段は、回に分ける前の講義ノート全体で決める（回の区切りを
        # 書いても変わらないように）
        ctx.slide_level = mdlib.lecture_slide_level(valmod.mask_code(raw)[0])
        raw = mdlib.section_part(raw, doc.part)
        if raw is None:
            res.ok = False
            res.report.append(f'{tag("stopped")} ' + t(
                '{file} has no session {part} (the `#` heading is gone, or its '
                '{#id} changed)', file=Path(src).name, part=doc.part))
            return res
        ctx.say(f'{tag("split")} ' + t('building only session {part} of {file}',
                                       part=doc.part, file=Path(src).name))
    # 図のパスは原稿から見た相対で書かれている。out_dir は原稿と階層の深さが
    # 違うので、コピーする前に out_dir から見た相対に振り直す（さもないと
    # `../assets/figures/…` が `build/assets/figures/…` を指して組版が落ちる）。
    raw = mdlib.rebase_links(raw, Path(src).parent, out_dir)
    body, abstract = preprocess(cfg, doc, backend, ctx, raw)

    # ---- CSL -------------------------------------------------------------
    use_citeproc = citations
    if target == 'typst' and cfg['typst_citations'] == 'native':
        use_citeproc = False
    if not citations:
        ctx.say(f'{tag("bib")} ' + t('--no-citations: leaving citations unresolved '
                                    '(for a draft)'))
    cite_args: list = []
    if use_citeproc:
        try:
            ctx.csl = cslmod.resolve(cfg['csl'], cfg.root,
                                     allow_download=not offline, quiet=True)
        except cslmod.CSLError as e:
            res.ok = False
            res.report.append(f'{tag("stopped")} {e}')
            return res
        # スライドは既定で書誌一覧を出さない（枠に入りきらないため）。
        # 出したいときは slides.md の末尾に見出しと `::: {#refs}` を置き、
        # config の slides_bibliography を True にする。
        # 回でできていない文書のスライド（発表のデッキ）が対象。講義の回のデッキには出す
        suppress = ((doc.profile == 'slides'
                     or (doc.derived and backend.is_slides and not doc.sessions))
                    and not cfg['slides_bibliography'])
        ref_title = cfg['reference_section_title'] or None
        # 何も引いていなければ書誌の見出しを書き足さない（講義の回のスライドに、空の
        # 「参考文献」の1枚が付いていた）
        cites = (bool(mdlib.cited_keys(body, xref.kinds_of(ctx.envs)))
                 or bool(re.search(r'^nocite:', body, re.M)))
        if ref_title and not suppress and (ctx.shift_headings < 0 or backend.places_bibliography) \
                and cites \
                and not re.search(r'\{#refs\}', body):
            # 見出しを `##` で書く原稿は段を1つ上げて変換する。pandoc が差し込む書誌の
            # 見出しにもそれが効いて0段目（ただの段落）になるので、1段深い見出しと
            # 書誌の置き場所を自分で書き足す（上げたあとでちょうど1段目になる）
            body = (body.rstrip('\n') + f"\n\n{'#' * (1 - ctx.shift_headings)} {ref_title}"
                    " {.unnumbered}\n\n::: {#refs}\n:::\n")
            ref_title = None
        cite_args = pandocrun.citeproc_args(
            cfg['bib_file'], ctx.csl, cfg['csl_locale'],
            ref_title, cfg['link_citations'],
            suppress_bibliography=suppress, lua_filter=citation_filter(cfg, ctx))
        cite_args += citation_form_args(cfg, ctx)
        ctx.say(f'{tag("bib")} {Path(cfg["bib_file"]).name} + '
                + (ctx.csl.name if ctx.csl
                   else t("pandoc's default (chicago-author-date)"))
                + (' ' + t('(no bibliography list)') if suppress else ''))

    # 形式によっては、pandoc に渡す前に本文を組み替える（台本はノートだけにする）
    body = backend.final_markdown(body, ctx)

    # ---- pandoc ----------------------------------------------------------
    fmt = pandocrun.input_format(cfg['east_asian_line_breaks'], backend.input_extras())
    args = ['-f', fmt] + backend.pandoc_args(ctx) + cite_args
    if ctx.shift_headings:
        args += [f'--shift-heading-level-by={ctx.shift_headings}']
    args += ['--resource-path',
             os.pathsep.join(str(p) for p in (out_dir, cfg.root, cfg['figure_dir']))]

    out_path = out_dir / backend.out_name(ctx)
    if ctx.standalone and out_path.stem != ctx.doc_name:
        # 印の付かない前の版の名前（<文書>-<回>.pdf など）の出力は消す。残すと紛らわしい
        for ext in (backend.ext, '.pdf'):
            legacy = out_dir / f'{ctx.doc_name}{ext}'
            if legacy.is_file():
                legacy.unlink()
    try:
        if backend.binary:
            pandocrun.run_to_file(body, args, out_path, cwd=out_dir)
            text = ''
        else:
            text = mdlib.drop_output_macros(pandocrun.run(body, args, cwd=out_dir),
                                            ctx.math_macros)
            text = backend.postprocess(text, ctx)
            out_path.write_text(text, encoding='utf-8')
    except pandocrun.PandocError as e:
        res.ok = False
        res.report.append(f'{tag("stopped")} {e}')
        return res

    backend.check(text, ctx)
    res.outputs.append(out_path)
    ctx.say(f'{tag("wrote")} {out_path}')

    # main.tex / main.typ に渡すフラグ。**毎回書く**ので、匿名で組んだあと
    # 普通に組み直せば元に戻る（消し忘れで匿名版のまま出す事故を防ぐ）。
    flags = backend.flags(ctx)
    if flags and not ctx.standalone:
        (out_dir / flags[0]).write_text(flags[1], encoding='utf-8')
        res.outputs.append(out_dir / flags[0])
    # 番号と参照の体裁（main.* が読み込む）。これも毎回書く
    if not ctx.standalone:
        for name, text_ in backend.crossref_files(ctx):
            (out_dir / name).write_text(text_, encoding='utf-8')
            res.outputs.append(out_dir / name)

    # ---- 要旨を別ファイルに出す形式 --------------------------------------
    # 要旨がまだ空でも書く。main.* が読むのでなければ組めず、前の中身が残れば古い要旨が出る
    if not abstract and backend.wants_abstract_file and not appendix and not ctx.standalone:
        p = out_dir / f'abstract{backend.ext}'
        p.write_text('', encoding='utf-8')
        res.outputs.append(p)
    if abstract and backend.wants_abstract_file and not appendix:
        ab_args = ['-f', fmt] + backend.pandoc_args(ctx)
        drop = ('--standalone', '--toc', '--number-sections', '-s')
        ab_args = [a for a in ab_args
                   if a not in drop and not a.startswith('--toc-depth')]
        if use_citeproc:
            # 要旨に書誌一覧を付けない（本文の末尾に1回だけ出す）
            ab_args += pandocrun.citeproc_args(
                cfg['bib_file'], ctx.csl, cfg['csl_locale'], None,
                cfg['link_citations'], suppress_bibliography=True,
                lua_filter=citation_filter(cfg, ctx)) + citation_form_args(cfg, ctx)
        try:
            ab = mdlib.drop_output_macros(
                pandocrun.run(abstract, ab_args, cwd=out_dir, quiet=True), ctx.math_macros)
        except pandocrun.PandocError:
            ab = abstract
        ab = re.sub(r'\\hypertarget\{[^}]*\}\{%\n(.*?)\}\n', r'\1\n', ab, flags=re.S)
        p = out_dir / f'abstract{backend.ext}'
        p.write_text(ab.strip() + '\n', encoding='utf-8')
        res.outputs.append(p)
        ctx.say(f'{tag("abstract")} {p}')

    # ---- 分量 ------------------------------------------------------------
    if doc.profile == 'paper' and not appendix:
        # 数値を入れたあとの本文で数える（`{{n_obs}}` のままでは字数が狂う）
        counted = mdlib.drop_math_macros(mdlib.drop_references(
            valmod.substitute(mdlib.read(Path(src)), ctx.values, cfg)))
        excl, incl = mdlib.word_count(counted)
        chars = mdlib.char_count(counted)
        ctx.say(f'{tag("length")} ' + t(
            'words (without/with tables): {excl} / {incl}   characters '
            '(without spaces): {chars}',
            excl=f'{excl:,}', incl=f'{incl:,}', chars=f'{chars:,}'))

    res.report = ctx.report
    res.next_step = backend.next_step(ctx)

    # ---- 組版まで実行する ------------------------------------------------
    if do_compile:
        cmd = backend.compile(ctx, out_path)
        if ctx.compile_error:
            res.ok = False
            res.report.append(f'{tag("typeset")} ' + t('failed:') + '\n' + ctx.compile_error)
            return res
        if cmd and not ctx.standalone:
            main = backend.compile_main(ctx)
            if main:
                out_path = main
                cmd = backend.compile(ctx, main)
            else:
                cmd = None
                res.report.append(f'{tag("typeset")} ' + t(
                    'this is the main.* arrangement, so --compile does not typeset '
                    'it ({next})', next=backend.next_step(ctx)))
        if cmd:
            if not shutil.which(cmd[0]):
                res.report.append(f'{tag("typeset")} ' + t('no {cmd}, so it was '
                                                           'skipped', cmd=cmd[0]))
            else:
                res.report.append(f'{tag("typeset")} ' + ' '.join(cmd))
                r = subprocess.run(cmd, cwd=str(out_dir), capture_output=True,
                                   text=True, encoding='utf-8', errors='replace')
                if r.returncode != 0:
                    res.ok = False
                    tail = '\n'.join((r.stdout + r.stderr).strip().split('\n')[-25:])
                    res.report.append(f'{tag("typeset")} ' + t('failed:') + '\n' + tail)
                else:
                    pdf = out_path.with_suffix('.pdf')
                    res.compiled = pdf if pdf.exists() else None
                    res.report.append(f'{tag("typeset")} '
                                      + t('made {path}', path=res.compiled or out_dir))
                    backend.after_compile(ctx, out_path)       # res.report は ctx.report と同じもの
                    if res.compiled and not ctx.standalone:
                        # 論文は main.pdf（体裁ファイルの名前）。探しやすいように、文書の名前の
                        # 写しを1つ上に置く（build/pdf/<名前>.pdf）
                        named = out_dir.parent / f'{doc.name}.pdf'
                        shutil.copyfile(res.compiled, named)
                        res.outputs.append(named)
    return res


# ---------------------------------------------------------------- まとめ

def empty_sessions(doc) -> set:
    """中身のない回（区切りの後に見出しも本文もない）の印。"""
    try:
        _, parts, _ = mdlib._sections(mdlib.read(doc.src))
    except OSError:
        return set()
    return {key for key, _t, text, _a in parts if not mdlib.strip_comments(text).strip()}


def unmarked_sessions(doc, mark: str) -> set:
    """印の所だけで組むとき、印が1つもない回（スライドにするものがない）の印。"""
    try:
        _, parts, _ = mdlib._sections(mdlib.read(doc.src))
    except OSError:
        return set()
    rx = re.compile(r'\.' + re.escape(mark) + r'(?![\w-])')
    return {key for key, _t, text, _a in parts if not rx.search(text)}


def clear_old_sessions(cfg, doc, tgt: str, built: list) -> list:
    """回ごとのスライドの出力のうち、いまの講義ノートにない回のもの（`<文書>-<印>.typ/.pdf`）を消す。

    区切りを足す・回の id を変えると、前の名前の PDF が残ってどれが新しいか分からなくなる。
    build/ は全部作り直せるので消してよいが、ほかの文書の出力は消さない（名前が
    `<文書>-` で始まる別の文書もありうる）。
    """
    out_dir = cfg.out_dir(tgt, doc)
    if not out_dir.is_dir():
        return []
    others = set(cfg.documents) - {doc.name}
    backend = be.get(tgt)
    # 出力は <文書>-slides-<回>.pdf など。台本のページの対応は <文書>-<回>.notes.json
    keep = {backend.file_stem(b, b[len(doc.name) + 1:]) for b in built}
    keep_json = set(built)
    gone = []
    for f in sorted(out_dir.iterdir()):
        stem = f.name.split('.')[0]          # 台本のページの対応は <名前>.notes.json
        if f.suffix not in ('.typ', '.pdf', '.tex', '.json') or not stem.startswith(doc.name + '-'):
            continue
        if stem in (keep_json if f.suffix == '.json' else keep) or stem in others or any(stem.startswith(o + '-') for o in others
                                                 if len(o) > len(doc.name)):
            continue
        try:
            f.unlink()
            gone.append(f.name)
        except OSError:
            pass
    return gone


def run(cfg, doc_names=None, targets=None, appendix: bool = False,
        do_compile: bool = False, offline: bool = False,
        citations: bool = True, anonymous: bool = False) -> list:
    """複数の文書 × 複数の形式をまとめて作る。"""
    docs = [cfg.document(n) for n in (doc_names or list(cfg.documents))]
    if not docs:
        sys.exit(t('no documents to build. Add a manuscript with '
                   'octavo new paper|slides|lecture <name>, or write it into '
                   'documents in octavo.config.py'))
    results = []
    for doc in docs:
        tgts = targets or list(doc.targets)
        # 講義ノート: プリントは1本のまま、スライドは `#` の回ごとに別々に組む
        parts = cfg.parts(doc) if doc.sessions and doc.part is None else None
        # main.* 方式は本文と付録を1つの PDF に組むので、付録を書いてから組む
        with_appendix = bool(appendix and doc.appendix)
        defer = with_appendix and doc.profile == 'paper'
        for tgt in tgts:
            if parts is not None and be.get(tgt).is_slides:
                if not parts:
                    r = Result(doc=doc.name, target=tgt, ok=False)
                    r.report.append(f'{tag("stopped")} ' + t(
                        '{file} has no `#` headings, so the slides cannot be split '
                        'by session', file=doc.src.name))
                    results.append(r)
                empty = empty_sessions(doc)
                sel = marked_only(cfg.for_document(doc), be.get(tgt))
                unmarked = unmarked_sessions(doc, sel[0]) if sel else set()
                built = []
                for part in parts:
                    if part.part in unmarked and part.part not in empty:
                        r = Result(doc=part.name, target=tgt, ok=True)
                        r.report.append(f'{tag("split")} ' + t(
                            'session {key} has nothing marked .{mark}, so it gets no slides',
                            key=part.part, mark=sel[0]))
                        results.append(r)
                        continue
                    if part.part in empty:
                        # 予告だけ置いた回など。表紙だけのスライドは作らない
                        r = Result(doc=part.name, target=tgt, ok=True)
                        r.report.append(f'{tag("split")} ' + t(
                            'session {key} has nothing in it yet, so it gets no slides',
                            key=part.part))
                        results.append(r)
                        continue
                    built.append(part.name)
                    results.append(build_one(cfg, part, tgt, do_compile=do_compile,
                                             offline=offline, citations=citations,
                                             anonymous=anonymous))
                gone = clear_old_sessions(cfg, doc, tgt, built)
                if gone and results:
                    results[-1].report.append(f'{tag("split")} ' + t(
                        'removed {n} old session {n|file|files} that no longer match the '
                        'notes: {files}', n=len(gone), files=', '.join(gone)))
                continue
            results.append(build_one(cfg, doc, tgt, appendix=False,
                                     do_compile=do_compile and not defer,
                                     offline=offline,
                                     citations=citations, anonymous=anonymous))
            if with_appendix:
                results.append(build_one(cfg, doc, tgt, appendix=True,
                                         do_compile=do_compile, offline=offline,
                                         citations=citations,
                                         anonymous=anonymous))
    return results
