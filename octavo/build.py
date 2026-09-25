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
from . import csl as cslmod
from . import md as mdlib
from . import pandocrun
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
    """手で書く体裁ファイル（main.typ / main.tex）を原稿の隣から out_dir へ写す。

    正本は `papers/<名前>/main.typ`。組版は out_dir で行い、body.typ や
    abstract.typ はそこに生成されるので、組む直前に同じ場所へ写しておく。
    こうしておくと `build/` は丸ごと生成物になり、消しても体裁は残る。
    """
    name = ctx.backend.main_name
    if ctx.standalone or not name:
        return
    src = Path(doc.src).parent / name
    dest = ctx.out_dir / name
    if not src.is_file():
        return
    text = src.read_text(encoding='utf-8')
    if not dest.is_file() or dest.read_text(encoding='utf-8') != text:
        dest.write_text(text, encoding='utf-8')
    ctx.say(f'{tag("layout")} {cfg.rel(src)}')


# ---------------------------------------------------------------- 前処理

def preprocess(cfg, doc, backend, ctx: Ctx, raw: str) -> tuple:
    """原稿を pandoc に渡せる形にする。(markdown, abstract) を返す。"""
    meta, body = mdlib.split_front_matter(raw)
    # 分析が出した数値を先に入れる。以降の処理（要旨の切り出し、表・図の
    # 差し替え、分量の勘定）はすべて「数値が入ったあとの本文」を見る。
    body = valmod.substitute(body, ctx.values, cfg, ctx.report)
    ctx.meta = {**(cfg['meta'] or {}), **doc.meta, **meta}
    if 'lang' in ctx.meta:
        ctx.meta['lang_short'] = str(ctx.meta['lang'])[:2]

    body = mdlib.drop_references(body)
    # 数式のマクロは抜いておき、最後に頭へ付け直す（要旨にも）
    body = mdlib.drop_math_macros(body)
    macros = '\n'.join(ctx.math_macros)

    abstract = ''
    if ctx.profile_opt('abstract'):
        abstract, body = mdlib.split_abstract(body)
    if doc.profile == 'paper':
        body = mdlib.strip_title_block(body)

    body = mdlib.filter_divs(body, ctx.keep_classes,
                             keep_notes=backend.keeps_notes,
                             report=ctx.report,
                             notes_wrap=backend.notes_wrap)
    body = mdlib.replace_theorem_divs(body, cfg['theorem_envs'],
                                      raw=backend.name == 'latex', report=ctx.report)
    body = mdlib.replace_poscite(body, lambda k: backend.fmt_poscite(k, ctx))
    if doc.profile in ('paper', 'handout') and backend.tidy_headings:
        body = mdlib.tidy_headings(body)
    body, known = apply_crossrefs(body, doc, backend, ctx)
    if abstract:
        abstract = xref.replace_references(
            abstract, known, lambda it, short: backend.fmt_ref(it, short, ctx), ctx.report)

    # 見出しの深さ: `# 見出し` があるならそのまま、無ければ `##` を最上位とみなす
    ctx.shift_headings = 0 if re.search(r'^# \S', body, re.M) else -1

    # 要旨を本文に戻す形式（main.tex を持たないもの）
    if abstract and not backend.wants_abstract_file and ctx.standalone \
            and doc.profile == 'paper':
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


def apply_crossrefs(body: str, doc, backend, ctx: Ctx) -> tuple:
    """図・表・式・節のラベルと参照（crossref.py）。(本文, 知っているラベル) を返す。

    1. この原稿を文書の順に数える（番号を組版側が振らない形式のために）
    2. Word など番号を振らない形式なら、見出し・キャプション・式に番号を文字で入れる
    3. 本文の `@fig-…` を形式ごとの参照に
    4. 図を形式に合わせ、分析が書いた表（中身の無いキャプション）を差し込む
    どの段も行を増減させないので、1 で覚えた行番号が 2 まで使える（4 は最後）。
    """
    top = 1 if ctx.crossref_section is not None else xref.top_level(body)
    nums = xref.number(body, ctx.numbering_mode(), appendix=ctx.appendix, top=top,
                       section=ctx.crossref_section)
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
        body, known, lambda it, short: backend.fmt_ref(it, short, ctx), ctx.report)

    lines = body.split('\n')
    external = {it.line: it for it in nums.items if it.external}
    for i, line in xref._lines_outside_code(body):
        s = line.strip()
        m = xref.IMAGE.match(s)
        if m:
            lines[i] = backend.fmt_figure(m, xref.label_in(m.group('attr'), 'fig'), ctx)
            continue
        it = external.get(i)
        if it:
            cap = xref.TABLE_CAPTION.match(s).group('cap')
            lines[i] = backend.fmt_external_table(it.label[len('tbl-'):], cap, it.label, ctx)
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
    「ラベルが無い」で止まり、Word ではリンクが切れる。講義の回ごとのデッキも別の
    PDF なので、ほかの回への参照は番号を文字で書く。
    """
    def prepared(path: Path, is_appendix: bool) -> str:
        _, body = mdlib.split_front_matter(mdlib.read(path))
        body = mdlib.drop_math_macros(mdlib.drop_references(body))
        if doc.profile == 'paper' and not is_appendix:
            _, body = mdlib.split_abstract(body)
            body = mdlib.strip_title_block(body)
        return mdlib.filter_divs(body, ctx.keep_classes, keep_notes=backend.keeps_notes)

    mode = ctx.numbering_mode()
    if doc.part is not None and not appendix:
        whole = mdlib.read(Path(doc.src))
        keys = [k for k, _ in mdlib.section_keys(whole)]
        if doc.part in keys:
            ctx.crossref_section = keys.index(doc.part) + 1
        ctx.crossrefs = xref.number(prepared(Path(doc.src), False), mode).labels()
        return
    other = doc.src if appendix else doc.appendix
    if doc.profile == 'paper' and other and Path(other).is_file():
        items = xref.number(prepared(Path(other), not appendix), mode,
                            appendix=not appendix).labels()
        ctx.crossrefs = items
        layout = Path(doc.src).parent / backend.main_name if backend.main_name else None
        if layout and layout.is_file() and backend.includes_appendix(
                layout.read_text(encoding='utf-8')):
            ctx.crossref_local |= set(items)


def _pandoc_meta(cfg, ctx: Ctx) -> dict:
    """standalone 出力の題扉に渡すメタデータ。

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

    out_dir = cfg.out_dir(target, doc)
    out_dir.mkdir(parents=True, exist_ok=True)

    ctx = Ctx(cfg=cfg, backend=backend, out_dir=out_dir, profile=doc.profile,
              doc_name=doc.name if not appendix else f'{doc.name}-appendix',
              appendix=appendix, anonymous=anonymous)
    if anonymous:
        ctx.say(f'{tag("anonymous")} ' + t('building with anything identifying hidden '
                                          '(::: {.no-anonymous} blocks and the '
                                          'title-block metadata)'))
    ctx.entries = bibmod.parse(cfg['bib_file'])
    ctx.values, warn = valmod.load(cfg)
    for line in warn:
        ctx.say(line)
    # 仮の値のまま組むと、本文に嘘の数字が入る。毎回言う（build が黙っていると
    # 気づけない唯一の種類の誤り。手書きの results/*.json には印が無いので鳴らない）
    for f in valmod.placeholder_files(cfg):
        ctx.say(f'{tag("values")}{tag("note")} ' + t(
            '{file} is still the starter values octavo init wrote. The numbers in '
            'the text are fake (octavo analysis run makes them real)', file=f))

    sync_layout(cfg, doc, ctx)

    raw = mdlib.read(Path(src))
    # 数式のマクロは本文と付録で共有する（回ごとに分ける前の、ファイル全体から集める）
    ctx.math_macros = mdlib.math_macros(*(
        mdlib.read(Path(p)) for p in (doc.src, doc.appendix) if p and Path(p).exists()))
    sibling_crossrefs(cfg, doc, backend, ctx, appendix)
    if doc.part is not None and not appendix:
        raw = mdlib.section_part(raw, doc.part)
        if raw is None:
            res.ok = False
            res.report.append(f'{tag("stopped")} ' + t(
                '{file} has no session {part} (the `#` heading is gone, or its '
                '{{#id}} changed)', file=Path(src).name, part=doc.part))
            return res
        ctx.say(f'{tag("split")} ' + t('building only session {part} of {file}',
                                       part=doc.part, file=Path(src).name))
    # 図のパスは原稿から見た相対で書かれている。out_dir は原稿と階層の深さが
    # 違うので、写す前に out_dir から見た相対に振り直す（さもないと
    # `../figures/…` が `build/figures/…` を指して組版が落ちる）。
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
        suppress = (doc.profile == 'slides' and not cfg['slides_bibliography'])
        cite_args = pandocrun.citeproc_args(
            cfg['bib_file'], ctx.csl, cfg['csl_locale'],
            cfg['reference_section_title'] or None, cfg['link_citations'],
            suppress_bibliography=suppress)
        ctx.say(f'{tag("bib")} {Path(cfg["bib_file"]).name} + '
                + (ctx.csl.name if ctx.csl
                   else t("pandoc's default (chicago-author-date)"))
                + (' ' + t('(no bibliography list)') if suppress else ''))

    # ---- pandoc ----------------------------------------------------------
    fmt = pandocrun.input_format(cfg['east_asian_line_breaks'], backend.input_extras())
    args = ['-f', fmt] + backend.pandoc_args(ctx) + cite_args
    if ctx.shift_headings:
        args += [f'--shift-heading-level-by={ctx.shift_headings}']
    args += ['--resource-path',
             os.pathsep.join(str(p) for p in (out_dir, cfg.root, cfg['figure_dir']))]

    out_path = out_dir / backend.out_name(ctx)
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
    if abstract and backend.wants_abstract_file and not appendix:
        ab_args = ['-f', fmt] + backend.pandoc_args(ctx)
        drop = ('--standalone', '--toc', '--number-sections', '-s')
        ab_args = [a for a in ab_args
                   if a not in drop and not a.startswith('--toc-depth')]
        if use_citeproc:
            # 要旨に書誌一覧を付けない（本文の末尾に1回だけ出す）
            ab_args += pandocrun.citeproc_args(
                cfg['bib_file'], ctx.csl, cfg['csl_locale'], None,
                cfg['link_citations'], suppress_bibliography=True)
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

    # ---- 組版まで走らせる ------------------------------------------------
    if do_compile:
        cmd = backend.compile(ctx, out_path)
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
    return res


# ---------------------------------------------------------------- まとめ

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
        parts = cfg.parts(doc) if doc.split_slides else None
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
                for part in parts:
                    results.append(build_one(cfg, part, tgt, do_compile=do_compile,
                                             offline=offline, citations=citations,
                                             anonymous=anonymous))
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
