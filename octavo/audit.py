# -*- coding: utf-8 -*-
"""`octavo check` — 投稿の前に、まとめて1回で見る。

    octavo check
    octavo check --strict     注意も失敗として扱う
    octavo check --anonymous  匿名審査で出すときの検査も足す

散らばっている検査（`octavo checkbib` / `octavo values` / `octavo analysis` /
`octavo lint`）と、どこにも無かった検査（図と表のファイルが実在するか）を
1コマンドにまとめる。**判定そのものはここには書かない** — それぞれの
モジュールの `collect()` を呼ぶだけなので、単体のコマンドと食い違わない。

致命的（そのまま組むと壊れる・間違う）と、注意（人が判断する）を分ける。
既定では致命的があるときだけ 非0 で終わる。CI に置くなら `--strict`。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import analysis as anamod
from . import backends as be
from . import crossref as xref
from . import check as checkmod
from . import dataset
from . import lint as lintmod
from . import md as mdlib
from . import scaffold
from . import values as valmod
from .i18n import t

def marks() -> tuple:
    """[ ok ] / [ note ] / [fatal] の印。幅を揃えた文字列で持つ
    （全角は f-string の桁揃えで合わないため）。"""
    return (t('  ok  '), t(' note '), t('fatal '))


@dataclass
class Item:
    ok: bool
    fatal: bool                 # 落ちたときに致命的か
    label: str
    detail: str = ''
    lines: list = field(default_factory=list)     # 内訳（数行だけ出す）
    hint: str = ''


# ---------------------------------------------------------------- 図・表の実在

def figure_problems(cfg) -> list:
    """本文が貼っている図で、実ファイルが無いものを返す。

    figures/ の中の図は、出力形式ごとに拡張子が違う（LaTeX は .pdf、Word は .png）
    ので、**その文書が出す形式の分だけ**見る。それ以外の図は書いたとおりのパス。
    """
    fig_dir = Path(cfg['figure_dir']).resolve()
    need: dict = {}
    for name, src, _ in cfg.sources():
        doc = cfg.documents[name]
        exts = {be.get(x).figure_ext(cfg) for x in doc.targets}
        text = mdlib.read(src)
        for _, line in xref._lines_outside_code(text):
            m = xref.IMAGE.match(line.strip())
            if not m or '://' in m.group('path'):
                continue
            p = (Path(src).parent / m.group('path').strip('<>')).resolve()
            if p.parent == fig_dir:
                need.setdefault(p.with_suffix(''), set()).update(exts)
            else:
                need.setdefault(p, {''})
    missing = []
    for stem in sorted(need):
        for ext in sorted(need[stem]):
            p = Path(str(stem) + ext) if ext else stem
            if not p.exists():
                missing.append(p)
    return missing


def placeholder_figures(cfg) -> list:
    """`octavo init` が置いた仮の図・表（枠と×の図、中身の無い表）のままのものを返す。"""
    out = []
    for key in ('figure_dir', 'table_dir'):
        d = Path(cfg[key])
        if d.is_dir():
            out += [cfg.rel(p) for p in sorted(d.iterdir())
                    if p.is_file() and scaffold.is_placeholder(p)]
    return out


def table_problems(cfg) -> list:
    """分析が書いたはずの表（本文の `: 表題 {#tbl-名前}`）で、実ファイルが無いもの。

    形式ごとに読むファイルが違う（Typst は .typ、LaTeX は .tex、Word は .md）ので、
    その文書が出す形式の分だけ見る。
    """
    missing = []
    for name, _, stem in xref.external_tables(cfg):
        for ext in sorted({be.get(x).table_ext for x in cfg.documents[name].targets}):
            p = Path(cfg['table_dir']) / f'{stem}{ext}'
            if p not in missing and not p.exists():
                missing.append(p)
    return missing


def length_problems(cfg) -> list:
    """投稿規定の分量を超えていないか。(名前, いま, 上限, 単位) を返す。

    `[分量]` は build のたびに出ていたが、**規定と突き合わせてはいなかった**。
    語数超過は投稿できないという意味で致命的なので、ここで見る。
    数えるのは `{{…}}` を差し込んだあとの本文（`build` の数え方と同じ）。
    """
    out = []
    vals, _ = valmod.load(cfg)
    for name, src, is_appendix in cfg.sources():
        if is_appendix:
            continue                      # 付録に規定があることは稀
        if cfg.documents[name].profile != 'paper':
            continue                      # 規定は投稿する論文のもの。スライド・講義は見ない
        raw = mdlib.drop_math_macros(valmod.substitute(mdlib.read(src), vals, cfg))
        abstract, body = mdlib.split_abstract(mdlib.drop_references(raw))
        body = mdlib.strip_title_block(body)
        pairs = (
            (t('body word count'), mdlib.word_count(body)[0], cfg['word_limit'],
             t(' words')),
            (t('body character count'), mdlib.char_count(body), cfg['char_limit'],
             t(' characters')),
            (t('abstract word count'), mdlib.word_count(abstract)[0] if abstract else 0,
             cfg['abstract_word_limit'], t(' words')),
            (t('abstract character count'), mdlib.char_count(abstract) if abstract else 0,
             cfg['abstract_char_limit'], t(' characters')),
        )
        for label, got, limit, unit in pairs:
            if limit:
                out.append((t('{doc}: {what}', doc=name, what=label), got, int(limit), unit))
    return out


# ---------------------------------------------------------------- 本体


def collect(cfg, anonymous: bool = False) -> list:
    items: list = []

    # -- 原稿 ---------------------------------------------------------------
    srcs = cfg.sources()
    items.append(Item(
        ok=bool(srcs), fatal=True, label=t('manuscript'),
        detail=', '.join(cfg.rel(p) for _, p, _ in srcs) or t('none found'),
        hint=t('add one with octavo new paper|slides|lecture <name>, or check '
               'documents in octavo.config.py')))

    # -- 分析 ---------------------------------------------------------------
    if cfg['analysis']:
        rows = anamod.status(cfg)
        stale = [u for u, exists, old in rows if not exists or old]
        items.append(Item(
            ok=not stale, fatal=False, label=t('analysis freshness'),
            detail=t('{stale} of {n} {stale|is|are} stale', stale=len(stale), n=len(rows)) if stale
                   else t('{n|the one is|all # are} up to date', n=len(rows)),
            lines=[anamod.key(cfg, u) for u in stale],
            hint='octavo analysis run'))

        orphans = anamod.orphan_results(cfg)
        items.append(Item(
            ok=not orphans, fatal=False, label=t('value files'),
            detail=t('{n} with no matching .qmd', n=len(orphans)) if orphans
                   else t('every one matches a .qmd'),
            lines=[p.name for p in orphans],
            hint=t('if you deleted or renamed a .qmd, delete its .json too')))

    # -- 値 -----------------------------------------------------------------
    vals, warn = valmod.load(cfg)
    refs: dict = {}
    for name, src, is_appendix in srcs:
        label = f'{name}(' + t('appendix') + ')' if is_appendix else name
        for k in valmod.referenced(mdlib.read(src)):
            refs.setdefault(k, []).append(label)
    missing_vals = sorted(k for k in refs if k not in vals)
    items.append(Item(
        ok=not missing_vals and not warn, fatal=bool(missing_vals),
        label=t('{{…}} in the text'),
        detail=t('{n} unresolved', n=len(missing_vals)) if missing_vals
               else t('{n|the one resolves|all # resolve}', n=len(refs)),
        lines=['{{' + k + '}}  ' + '、'.join(refs[k]) for k in missing_vals] + warn,
        hint=t('octavo analysis run, or check the spelling of the name')))

    # -- 書誌 ---------------------------------------------------------------
    r = checkmod.collect(cfg)
    if cfg['analysis']:
        ph = valmod.placeholder_files(cfg)
        items.append(Item(
            ok=not ph, fatal=True, label=t('placeholder values'),
            detail=(t('the analysis has never run: {files} {n|is|are} the starter '
                      'values octavo init wrote', files=', '.join(ph), n=len(ph))
                    if ph else t('these are real values')),
            lines=ph,
            hint=t('run the analysis with octavo analysis run — as it is, the '
                   'numbers that get typeset are fake')))

    items.append(Item(
        ok=not r.missing, fatal=True, label=t('citation keys'),
        detail=t('{n} {n|key is|keys are} not in the .bib', n=len(r.missing)) if r.missing
               else t('{n|the one is|all # are} in the .bib', n=len(r.cited)),
        lines=r.missing, hint='octavo checkbib / octavo bib pull'))
    items.append(Item(
        ok=not r.problems and not r.duplicates, fatal=False, label=t('bib contents'),
        detail=(t('{n} to look at', n=len(r.problems))
                + (t(' / {n} duplicate {n|pair|pairs}', n=len(r.duplicates))
                   if r.duplicates else ''))
               if (r.problems or r.duplicates) else t('nothing wrong'),
        lines=[f"{p['key']}: {p['issue']}" for p in r.problems],
        hint=t('octavo checkbib (what you decide not to fix goes in bib_accepted)')))

    # -- 図・表 -------------------------------------------------------------
    figs = figure_problems(cfg)
    items.append(Item(
        ok=not figs, fatal=True, label=t('figure files'),
        detail=t('{n} missing', n=len(figs)) if figs
               else t('every figure the text uses is there'),
        lines=[str(p) for p in figs],
        hint=t('octavo analysis run, or put it in figures/')))
    tbls = table_problems(cfg)
    items.append(Item(
        ok=not tbls, fatal=True, label=t('table files'),
        detail=t('{n} missing', n=len(tbls)) if tbls
               else t('every table from the analysis is there'),
        lines=[str(p) for p in tbls], hint='octavo analysis run'))

    # -- 相互参照 -----------------------------------------------------------
    xr = xref.collect(cfg)
    bad = xr['missing'] + xr['duplicate']
    items.append(Item(
        ok=not bad, fatal=True, label=t('cross-references'),
        detail=(t('{n} {n|reference points|references point} at no label',
                  n=len(xr['missing']))
                + (' / ' + t('{n} {n|label is|labels are} used twice', n=len(xr['duplicate']))
                   if xr['duplicate'] else '')) if bad
               else t('every @fig- / @tbl- / @eq- / @sec- has its label'),
        lines=[f'{at}  {what}' for at, what in bad],
        hint=t('write the label on the figure, table, equation or heading: {example}',
               example='{#fig-name}')))
    items.append(Item(
        ok=not xr['unused'], fatal=False, label=t('unused labels'),
        detail=(t('{n} {n|figure, table or equation is|figures, tables or equations are} '
                  'never referred to', n=len(xr['unused']))
                if xr['unused'] else t('every labelled figure, table and equation is referred to')),
        lines=[f'{at}  {what}' for at, what in xr['unused']],
        hint=t('refer to it with @label, or drop the label')))

    # -- 直書きの数値 -------------------------------------------------------
    found = lintmod.collect(cfg)
    phf = placeholder_figures(cfg)
    items.append(Item(
        ok=not phf, fatal=False, label=t('placeholder figures and tables'),
        detail=(t('{n} {n|is still a placeholder|are still the placeholders} octavo init wrote', n=len(phf))
                if phf else t('no placeholders left')),
        lines=phf,
        hint=t('octavo analysis run (ov_figure() / ov_table() in the .qmd rewrite them)')))

    left = lintmod.leftovers(cfg)
    items.append(Item(
        ok=not left, fatal=False, label=t('template leftovers'),
        detail=(t('{n} octavo:example {n|mark|marks}', n=len(left))
                if left else t('no marks left')),
        lines=[f'{lo.file}:{lo.line}  {lo.excerpt}' for lo in left],
        hint=t('replace them with your own content, comment mark and all')))

    items.append(Item(
        ok=not found, fatal=False, label=t('hand-typed numbers'),
        detail=t('{n} found', n=len(found)) if found else t('none found'),
        lines=[f'{f.file}:{f.line}  {f.text}  [{f.label()}]' for f in found],
        hint=t('octavo lint (what is not a result goes in lint_accepted)')))

    # -- 分量（投稿規定）-----------------------------------------------------
    lengths = length_problems(cfg)
    over = [(lab, got, lim, u) for lab, got, lim, u in lengths if got > lim]
    if lengths:
        items.append(Item(
            ok=not over, fatal=bool(over), label=t('length'),
            detail=(t('{n} {n|is|are} over the limit', n=len(over)) if over
                    else t('within the limits')),
            lines=[t('{label}: {got}{unit} (limit {limit}{unit}, over by {excess}{unit})',
                     label=lab, got=f'{got:,}', limit=f'{lim:,}',
                     excess=f'{got - lim:,}', unit=u)
                   for lab, got, lim, u in over]
            or [f'{lab}: {got:,}{u} / {lim:,}{u}' for lab, got, lim, u in lengths],
            hint=t('cut it down, or check the journal rules')))

    # -- データの指紋 -------------------------------------------------------
    if dataset.data_dir(cfg).is_dir():
        recorded_at, recorded = dataset.read(cfg)
        drift = dataset.compare(cfg)
        items.append(Item(
            ok=bool(recorded) and not drift, fatal=False, label=t('data fingerprints'),
            detail=(t('nothing recorded ({n} {n|file|files} under data/)',
                      n=len(dataset.scan(cfg)))
                    if not recorded else
                    (t('{n} {n|differs|differ} from the record', n=len(drift)) if drift
                     else t('matches the record from {when} ({n} {n|file|files})',
                            when=recorded_at, n=len(recorded)))),
            lines=[f'[{d.label()}] {d.path}' for d in drift],
            hint=t('octavo data hash to record / status to check')))

    # -- 匿名審査（--anonymous のときだけ）----------------------------------
    if anonymous:
        mine = checkmod.self_citations(cfg)
        items.append(Item(
            ok=not mine, fatal=False, label=t('self-citations'),
            detail=t('{n} {n|candidate|candidates}', n=len(mine)) if mine else t('none found'),
            lines=mine,
            hint=t('for blind review, decide whether to mask them as Author (year) '
                   '— it depends on the journal')))

    # -- 再現性 -------------------------------------------------------------
    if cfg['analysis']:
        sess = valmod.session_info(cfg)
        items.append(Item(
            ok=bool(sess), fatal=False, label=t('environment record'),
            detail=(', '.join(f'{k}: {v.get("engine", "?")} {v.get("version", "")}'
                              for k, v in sess.items())
                    if sess else t('no _session in the value files')),
            hint=t('running the analysis once records it (for the replication '
                   'package)')))

    return items


# ---------------------------------------------------------------- 表示

def run(cfg, strict: bool = False, verbose: bool = False,
        anonymous: bool = False) -> int:
    items = collect(cfg, anonymous=anonymous)
    bad_fatal = [i for i in items if not i.ok and i.fatal]
    bad_warn = [i for i in items if not i.ok and not i.fatal]

    OK, WARN, NG = marks()
    width = max((len(i.label) for i in items), default=14)
    for i in items:
        mark = OK if i.ok else (NG if i.fatal else WARN)
        print(f'[{mark}] {i.label.ljust(width)}  {i.detail}')
        show = i.lines if (verbose or i.fatal) else i.lines[:3]
        for line in show:
            print(f'           {line}')
        if len(i.lines) > len(show):
            print('           ' + t('…and {n} more (--verbose for all of them)',
                                     n=len(i.lines) - len(show)))
        if not i.ok and i.hint:
            print(f'           -> {i.hint}')

    print()
    if bad_fatal:
        print(t('{n} fatal. Typesetting this would be wrong', n=len(bad_fatal)))
    elif bad_warn:
        print(t('nothing fatal ({n} to look at)', n=len(bad_warn)))
    else:
        print(t('All clear. Ready to submit'))
    return 1 if bad_fatal or (strict and bad_warn) else 0
