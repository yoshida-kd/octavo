# -*- coding: utf-8 -*-
"""octavo — the command line entry point.

The one-line summary shown by `--help` is in `usage_text()` below, so
it can be translated like everything else on screen.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import __version__
from . import analysis as analysismod
from . import audit as auditmod
from .i18n import language, t, tag
from . import backends as be
from . import bib as bibmod
from . import bundle as bundlemod
from . import build as buildmod
from . import check as checkmod
from . import config as configmod
from . import csl as cslmod
from . import dataset
from . import doctor as doctormod
from . import envsetup
from . import lint as lintmod
from . import paths
from . import md as mdlib
from . import review as reviewmod
from . import scaffold
from . import values as valmod
from . import zotero as zoteromod


# ---------------------------------------------------------------- 表示

USAGE_LINES = (
    ('octavo build', 'build everything the config says'),
    ('octavo build example-paper --to docx', 'build document example-paper as Word'),
    ('octavo build --to all --compile', 'build every format, typeset them too'),
    ('octavo watch --to beamer', 'rebuild whenever a manuscript is saved'),
    ('octavo documents', 'list the registered manuscripts'),
    ('octavo config [set KEY VALUE]', 'show or change the common settings'),
    ('octavo analysis', 'is the analysis (.qmd) up to date?'),
    ('octavo analysis run', 'run the stale .qmd through quarto'),
    ('octavo values', 'cross-check {{…}} against results/'),
    ('octavo values --diff [ref]', 'what moved since last time (or a git version)'),
    ('octavo lint', 'find results typed into the manuscript'),
    ('octavo check', 'one audit before submitting'),
    ('octavo bundle [paper name]', 'repackage it for a submission system'),
    ('octavo review returned.docx', "list a coauthor's tracked changes"),
    ('octavo data hash|status', 'record / check the data fingerprints'),
    ('octavo checkbib', 'cross-check citation keys against the .bib'),
    ('octavo bib pull --collection X', 'fetch the .bib from Zotero'),
    ('octavo csl get apa', "fetch a journal's style (CSL)"),
    ('octavo doctor', 'diagnose the environment'),
    ('octavo setup', 'install the tools (pandoc, Typst, quarto, R, uv, fonts)'),
    ('octavo env', "set up this project's .venv and renv"),
    ('octavo init 2026-study', 'write a project skeleton'),
    ('octavo new paper|slides|lecture name', 'add a manuscript'),
    ('octavo template list', 'which templates are in use, and how to make your own'),
    ('octavo release name v1-submitted', 'tag this version, PDF to a GitHub Release'),
)


def usage_text() -> str:
    """`--help` の先頭に出る一覧。"""
    width = max(len(c) for c, _ in USAGE_LINES)
    return (t('octavo — build LaTeX / Typst / Beamer / Word from a Markdown '
              'manuscript.') + '\n\n'
            + '\n'.join(f'    {c.ljust(width)}  {t(w)}' for c, w in USAGE_LINES))


def print_results(results: list, verbose: bool = True) -> int:
    bad = 0
    for r in results:
        head = f'== {r.doc} -> {t(be.get(r.target).label)} '
        print('\n' + head + '=' * max(4, 62 - len(head)))
        for line in r.report:
            print('  ' + line)
        if not r.ok:
            bad += 1
        elif r.next_step and verbose:
            print('  ' + t('next:') + ' ' + r.next_step)
    made = [o for r in results for o in r.outputs]
    print('\n' + t('made {n} {n|file|files}', n=len(made))
          + (' / ' + t('{n} failed', n=bad) if bad else ''))
    return 1 if bad else 0


# ---------------------------------------------------------------- 各コマンド

def run_analysis(cfg, args, quiet: bool = False) -> int:
    """変換の前に、古い .qmd を走らせる。0 なら変換に進んでよい。

    quarto が無いだけなら止めない（変換自体は pandoc だけでできる）。
    走らせて**失敗した**ときだけ止める — 古い数値のまま論文を組むと、
    本文と分析が静かに食い違うため。
    """
    if getattr(args, 'no_analysis', False) or not cfg['analysis']:
        return 0
    force = getattr(args, 'force_analysis', False)
    if not cfg['analysis_auto'] and not force:
        return 0
    report: list = []
    _, ok = analysismod.run(cfg, force=force, report=report, auto=True)
    if report and not quiet:
        head = '== ' + t('Analysis') + ' '
        print(head + '=' * max(4, 62 - len(head)))
        for line in report:
            print('  ' + line)
    if not ok:
        print('\n' + t('the analysis failed. Building around stale numbers would '
                       'contradict the text, so this stops here.') + '\n  '
              + t('Fix it, then octavo build. To build with results/ as it is: '
                  'octavo build --no-analysis'), file=sys.stderr)
        return 1
    return 0


def cmd_build(args) -> int:
    cfg = configmod.load(args.config)
    quiet = getattr(args, 'json', False)
    docs = args.documents or None
    # 名前と形式の打ち間違いは、時間のかかる分析を走らせる前に止める
    for name in docs or ():
        cfg.document(name)
    targets = be.resolve_targets(args.to, 'paper') if args.to else None
    if run_analysis(cfg, args, quiet=quiet):
        return 1
    if targets is None and docs is None and not quiet:
        print(cfg.describe())
    results = buildmod.run(cfg, doc_names=docs, targets=targets,
                           appendix=args.appendix, do_compile=args.compile,
                           offline=args.offline, citations=not args.no_citations,
                           anonymous=args.anonymous)
    if quiet:
        return print_results_json(results)
    return print_results(results)


def print_results_json(results: list) -> int:
    """変換の結果を機械可読に出す（VS Code のプレビューが読む）。

    `compiled` が組み上がった PDF。**ここが唯一の「PDF はどこか」の答え**で、
    拡張側で out_dirs や拡張子から組み立て直さないためにある。
    """
    import json as _json
    print(_json.dumps({
        'ok': all(r.ok for r in results),
        'results': [{
            'doc': r.doc,
            'target': r.target,
            'ok': r.ok,
            'outputs': [str(o) for o in r.outputs],
            'compiled': str(r.compiled) if r.compiled else None,
            'report': list(r.report),
        } for r in results],
    }, ensure_ascii=False))
    return 0 if all(r.ok for r in results) else 1


def cmd_documents(args) -> int:
    """設定に登録されている原稿の一覧。`--json` は VS Code の
    プレビューが「今開いているファイルはどの文書か」を引くのに使う。"""
    cfg = configmod.load(args.config)
    rows = []
    for d in cfg.documents.values():
        row = {
            'name': d.name,
            'src': str(d.src),
            'rel': cfg.rel(d.src),
            'appendix': str(d.appendix) if d.appendix else None,
            'profile': d.profile,
            'targets': list(d.targets),
            'split_slides': bool(d.split_slides),
            'exists': d.exists(),
            'parts': [],
        }
        if d.split_slides and d.exists():
            text = mdlib.read(d.src)
            for key, title, start, end in mdlib.section_spans(text):
                row['parts'].append({
                    'name': f'{d.name}-{key}', 'key': key, 'title': title,
                    'start_line': start, 'end_line': end,
                })
        rows.append(row)

    if args.json:
        import json as _json
        print(_json.dumps({
            'root': str(cfg.root),
            'config': str(cfg.source) if cfg.source else None,
            'documents': rows,
        }, ensure_ascii=False))
        return 0

    if not rows:
        print(t('no documents registered. Add one with e.g. octavo new paper <name>'))
        return 0
    for r in rows:
        mark = '' if r['exists'] else ' ' + t('(no manuscript)')
        print(f"  {r['name']:<20} {r['profile']:<8} "
              f"{', '.join(r['targets']):<22} {r['rel']}{mark}")
        if r['appendix']:
            print(f"  {'':<20} " + t('appendix') + f": {cfg.rel(Path(r['appendix']))}")
        for part in r['parts']:
            print(f"  {'':<22} {part['name']:<18} {part['title']} "
                  + t('(lines {a}-{b})', a=part['start_line'], b=part['end_line']))
    return 0


def cmd_config(args) -> int:
    """画面から変えられる設定の一覧と書き換え（VS Code のサイドバーが使う）。"""
    from . import confedit
    cfg = configmod.load(args.config)
    path = cfg.source
    if args.action in ('set', 'unset'):
        if not args.key or (args.action == 'set' and args.value is None):
            print(t('usage: octavo config set KEY VALUE / octavo config unset KEY'),
                  file=sys.stderr)
            return 2
        try:
            value = confedit.set_value(path, args.key,
                                       None if args.action == 'unset' else args.value)
        except confedit.EditError as e:
            if args.json:
                import json as _json
                print(_json.dumps({'ok': False, 'error': str(e)}, ensure_ascii=False))
            else:
                print(str(e), file=sys.stderr)
            return 1
        if args.json:
            import json as _json
            print(_json.dumps({'ok': True, 'key': args.key, 'value': value},
                              ensure_ascii=False))
        else:
            print(t('{key} = {value}  ({path})', key=args.key, value=repr(value),
                    path=cfg.rel(path)))
        return 0

    rows = confedit.show(cfg)
    if args.json:
        import json as _json
        print(_json.dumps({'config': str(path), 'settings': rows}, ensure_ascii=False))
        return 0
    section = None
    for r in rows:
        if r['section'] != section:
            section = r['section']
            print(('\n' if section != rows[0]['section'] else '') + r['section_label'])
        mark = '' if r['explicit'] else '  ' + t('(default)')
        print(f"  {r['key']:<30} {r['value']!r}{mark}")
    return 0


def cmd_watch(args) -> int:
    cfg = configmod.load(args.config)
    docs = args.documents or None
    targets = be.resolve_targets(args.to, 'paper') if args.to else None
    watched = _watch_targets(cfg, docs)
    print(t('watching: {files}', files=', '.join(p.name for p in watched))
          + '\n  ' + t('Ctrl-C to stop'))
    stamps = {p: p.stat().st_mtime for p in watched if p.exists()}
    while True:
        try:
            time.sleep(1.0)
            now = {p: p.stat().st_mtime for p in watched if p.exists()}
            if now != stamps:
                stamps = now
                print('\n--- ' + t('something changed, rebuilding') + ' '
                      + time.strftime('%H:%M:%S'))
                if run_analysis(cfg, args):
                    continue
                results = buildmod.run(cfg, doc_names=docs, targets=targets,
                                       appendix=args.appendix,
                                       do_compile=args.compile, offline=True,
                                       citations=not args.no_citations)
                print_results(results, verbose=False)
        except KeyboardInterrupt:
            print('\n' + t('stopped'))
            return 0


def _watch_targets(cfg, docs) -> list:
    out = []
    # 名前で引く（講義ノートを分けた1回分 `講義-03` も、元の原稿を見張る）
    for d in ([cfg.document(n) for n in docs] if docs else cfg.documents.values()):
        out += [Path(d.src)] + ([Path(d.appendix)] if d.appendix else [])
    out.append(Path(cfg['bib_file']))
    out += analysismod.watch_paths(cfg)          # .qmd とそのデータ
    if cfg.source:
        out.append(Path(cfg.source))
    return [p for p in out if p]


def cmd_analysis(args) -> int:
    cfg = configmod.load(args.config)
    if args.json and args.action != 'run':
        import json as _json
        print(_json.dumps(analysismod.status_json(cfg), ensure_ascii=False))
        return 0
    rows = analysismod.status(cfg)
    if not rows:
        print(t('no analysis is registered. Write this in octavo.config.py:')
              + "\n    'analysis': ['analysis/*.qmd'],")
        return 0

    if args.action == 'run':
        report: list = []
        _, ok = analysismod.run(
            cfg, force=args.force, report=report, names=args.names or None,
            on_start=lambda k: print('  ' + t('running {unit}…', unit=k), flush=True))
        for line in report:
            print('  ' + line)
        return 0 if ok else 1
    if args.names:
        sys.exit(t('name a .qmd only with run: octavo analysis run {names}',
                   names=' '.join(args.names)))

    ver = analysismod.quarto_version()
    print('quarto: ' + (ver or t('not found (see octavo doctor)')))
    print(t('results go in: {path}', path=cfg['results_dir']) + '\n')
    stale = manual_stale = 0
    for u, exists, out_of_date in rows:
        if not exists:
            mark = t('gone')
        elif out_of_date:
            mark = t('stale')
            if u.manual:
                manual_stale += 1
            else:
                stale += 1
        else:
            mark = t('fresh')
        if u.manual:
            mark += ' · ' + t('manual')
        deps = '  ' + t('({n} watched {n|input|inputs})', n=len(u.deps)) if u.deps else ''
        print(f'  [{mark}] {analysismod.key(cfg, u)}{deps}')

    vals, warn = valmod.load(cfg)
    for line in warn:
        print('  ' + line)
    print('\n' + t('{values} {values|value|values} in {files} {files|file|files}',
                   values=len(vals), files=len(valmod.files(cfg))))
    _say_orphans(analysismod.orphan_results(cfg))
    if stale:
        print('\n' + t('{n} {n|is|are} stale. Run {n|it|them} with octavo analysis run '
                       '(octavo build runs {n|it|them} too)', n=stale))
    if manual_stale:
        print(('' if stale else '\n') + t(
            '{n} manual {n|one is|ones are} stale. octavo build does not run {n|it|them}: '
            'run {n|it|them} with octavo analysis run', n=manual_stale))
    return 0


def cmd_values(args) -> int:
    cfg = configmod.load(args.config)
    if args.diff is not None:
        return _values_diff(cfg, args.diff)
    vals, warn = valmod.load(cfg)

    refs: dict = {}
    for name, src, is_appendix in cfg.sources():
        label = f'{name}(' + t('appendix') + ')' if is_appendix else name
        for k in valmod.referenced(mdlib.read(src)):
            refs.setdefault(k, []).append(label)
    missing = sorted(k for k in refs if k not in vals)
    unused = sorted(k for k in vals if k not in refs)
    orphans = analysismod.orphan_results(cfg)

    if args.json:
        import json as _json
        print(_json.dumps({
            'results_dir': str(cfg['results_dir']),
            'values': {k: {'text': valmod.render(v, '', cfg), 'source': v.source,
                           'note': v.note} for k, v in vals.items()},
            'referenced': refs,
            'missing': missing,
            'unused': unused,
            'orphans': [p.name for p in orphans],
            'placeholder': valmod.placeholder_files(cfg),
            'warnings': warn,
        }, ensure_ascii=False))
        return 1 if missing else 0

    for line in warn:
        print(line)
    ph = valmod.placeholder_files(cfg)
    if ph:
        sep = '、' if language() == 'ja' else ', '
        print(tag('placeholder') + ' ' + t(
            '{files} {n|is|are} still the starter values octavo init wrote.',
            files=sep.join(ph), n=len(ph)))
        print('  ' + t('Building now puts fake numbers in the text -> '
                      'octavo analysis run') + '\n')
    print(t('{n} {n|value|values} in {path} ({files} {files|file|files})',
            n=len(vals), path=cfg['results_dir'],
            files=len(valmod.files(cfg))) + '\n')
    for k in sorted(vals):
        v = vals[k]
        where = ('、' if language() == 'ja' else ', ').join(refs.get(k, [])) or '—'
        note = f'  « {v.note} »' if v.note else ''
        print(f'  {k:<24} {valmod.render(v, "", cfg):>14}   '
              f'{v.source} -> {where}{note}')
    if missing:
        print('\n' + t('in the text but with no value (left as they are):'))
        for k in missing:
            print('  {{' + k + '}}  '
                  + ('、' if language() == 'ja' else ', ').join(refs[k]))
        print('  -> ' + t('run the analysis with octavo analysis run, and check '
                          'the spelling of the names'))
    if unused and args.unused:
        print('\n' + t('values nothing uses:'))
        for k in unused:
            print(f'  {k}')
    _say_orphans(orphans)
    if not missing:
        print('\n' + t('every {{…}} in the text resolves'))
    return 1 if missing else 0


def _values_diff(cfg, ref: str = '') -> int:
    """前に分析を走らせたとき（か git の版）から、本文の数字がどう動いたか。"""
    try:
        taken, changed, added, removed = valmod.diff(cfg, ref)
    except valmod.GitError as e:
        print(t('cannot compare with git: {why}', why=e), file=sys.stderr)
        print('  ' + t('to mark a version, tag it: git tag v1-submitted'),
              file=sys.stderr)
        return 1
    if not taken:
        print(t('nothing to compare with. Run octavo analysis run once and the '
                'values from just before are kept as the reference'))
        return 0
    print(t('compared with {when}', when=taken) + '\n')
    if changed:
        print(t('{n} {n|value|values} changed:', n=len(changed)))
        for name, before, after in changed:
            print(f'  {name:<24} {before:>14}  ->  {after}')
    for label, names in ((t('added'), added), (t('gone'), removed)):
        if names:
            print('\n' + t('{label} {n}:', label=label, n=len(names)))
            for n in names:
                print(f'  {n}')
    if not (changed or added or removed):
        print(t('none of the numbers the text prints have changed'))
    else:
        print('\n  ' + t('check that the words around them ("slightly", "about" '
                          'and the like) still hold'))
    return 0


def _say_orphans(orphans: list) -> None:
    """.qmd を消した・改名したときに残る値のファイルを知らせる。"""
    if not orphans:
        return
    print('\n' + t('value files with no matching .qmd:'))
    for p in orphans:
        print(f'  {p.name}')
    print('  -> ' + t('if you deleted or renamed the .qmd, delete this too (stale '
                      'numbers keep reaching the text). If you wrote it by hand, '
                      'leave it'))


def cmd_lint(args) -> int:
    cfg = configmod.load(args.config)
    if args.json:
        import json as _json
        print(_json.dumps(lintmod.as_json(cfg), ensure_ascii=False))
        return 0
    return lintmod.run(cfg)


def cmd_check(args) -> int:
    cfg = configmod.load(args.config)
    return auditmod.run(cfg, strict=args.strict, verbose=args.verbose,
                        anonymous=args.anonymous)


def cmd_bundle(args) -> int:
    cfg = configmod.load(args.config)
    targets = be.resolve_targets(args.to, 'paper') if args.to else ['typst']
    if len(targets) != 1:
        print(t('bundle packs one format at a time (--to typst, say)'),
              file=sys.stderr)
        return 1
    return bundlemod.run(cfg, targets[0], out=args.out, as_dir=args.dir,
                         anonymous=args.anonymous,
                         as_replication=args.replication,
                         with_raw=args.with_raw_data, document=args.document)


def cmd_review(args) -> int:
    if args.json:
        import json as _json
        try:
            print(_json.dumps(reviewmod.as_json(Path(args.docx)),
                              ensure_ascii=False))
        except reviewmod.DocxError as e:
            print(str(e), file=sys.stderr)
            return 1
        return 0
    only = 'comment' if args.comments else ('ins' if args.insertions else '')
    return reviewmod.run(Path(args.docx), only=only)


def cmd_data(args) -> int:
    cfg = configmod.load(args.config)
    return dataset.run(cfg, args.action)


def cmd_checkbib(args) -> int:
    cfg = configmod.load(args.config)
    if args.json:
        return checkmod.run_json(cfg)
    return checkmod.run(cfg, show_list=args.list, show_unused=args.unused)


def cmd_bib(args) -> int:
    if args.action == 'collections':
        try:
            for name in zoteromod.collections():
                print('  ' + name)
        except zoteromod.ZoteroError as e:
            print(str(e), file=sys.stderr)
            return 1
        return 0

    cfg = configmod.load(args.config)
    if args.action == 'pull':
        dest = Path(args.out) if args.out else Path(cfg['bib_file'])
        try:
            n, src = zoteromod.pull(dest, args.collection, args.format)
        except zoteromod.ZoteroError as e:
            print(str(e), file=sys.stderr)
            return 1
        print(t('wrote {n} {n|entry|entries} to {path} (from {source})',
                n=n, path=dest, source=src))
        return checkmod.run(cfg, show_list=False, show_unused=False)
    if args.action == 'clean':
        src = Path(cfg['bib_file'])
        out = Path(args.out) if args.out else src.with_name(src.stem + '.clean.bib')
        n, p = bibmod.clean(src, out)
        print(t('dropped {n} needless {n|field|fields} and wrote {path} (the '
                'original is untouched)', n=n, path=p))
        return 0
    return 1


def cmd_csl(args) -> int:
    if args.action == 'list':
        rows = cslmod.cached()
        if not rows:
            print(t('the cache is empty. Fetch one with e.g. octavo csl get apa'))
        for p in rows:
            print(f'  {p.stem:<44} {cslmod.title_of(p)}')
        print('\n' + t('kept in: {path}', path=cslmod.CACHE_DIR))
        print(t('aliases:') + ' ' + ', '.join(sorted(cslmod.ALIASES)))
        return 0
    if args.action == 'get':
        try:
            p = cslmod.fetch(args.name)
        except cslmod.CSLError as e:
            print(str(e), file=sys.stderr)
            return 1
        print(f'{p}\n  {cslmod.title_of(p)}')
        print('\n  ' + t("write  'csl': '{id}',  in octavo.config.py", id=p.stem))
        return 0
    if args.action == 'which':
        cfg = configmod.load(args.config)
        try:
            p = cslmod.resolve(cfg['csl'], cfg.root, allow_download=False)
        except cslmod.CSLError as e:
            print(str(e), file=sys.stderr)
            return 1
        if p is None:
            print(t("pandoc's built-in chicago-author-date is used (no .csl file)"))
        else:
            print(f'{p}\n  {cslmod.title_of(p)}')
        return 0
    return 1


def cmd_doctor(args) -> int:
    if args.json:
        import json as _json
        print(_json.dumps(doctormod.as_json(), ensure_ascii=False))
        return 0
    return doctormod.report(verbose=args.verbose)


def cmd_setup(args) -> int:
    script = paths.setup_script()
    if paths.on_windows():
        # Windows は setup.ps1（winget）。TeX はそこでは入れない
        if script is None:
            sys.exit(t('setup.ps1 is missing, so this cannot run here'))
        if args.with_tex:
            sys.exit(t('On Windows, octavo setup does not install TeX. Install MiKTeX or '
                       'TeX Live yourself if you need LaTeX / Beamer.'))
        cmd = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script)]
        for flag, ps in (('no_quarto', '-NoQuarto'), ('no_r', '-NoR'), ('check', '-Check')):
            if getattr(args, flag):
                cmd.append(ps)
        if not paths.is_clone():
            cmd += ['-OctavoVersion', __version__]
        return subprocess.call(cmd)
    if script is None or not shutil.which('bash'):
        sys.exit(t('setup.sh or bash is missing, so this cannot run here'))
    cmd = ['bash', str(script)]
    for flag in ('with_tex', 'no_quarto', 'no_r', 'check'):
        if getattr(args, flag):
            cmd.append('--' + flag.replace('_', '-'))
    # clone でなければ CLI も PyPI から入れ直す。版はいま動いているものに合わせる
    if not paths.is_clone():
        cmd += ['--octavo-version', __version__]
    return subprocess.call(cmd)


def cmd_env(args) -> int:
    return envsetup.run(configmod.load(args.config))


def cmd_init(args) -> int:
    return scaffold.init(Path(args.dir), lang=args.lang, force=args.force)


def cmd_new(args) -> int:
    return scaffold.new(Path(args.config), args.kind, args.name, force=args.force)


def cmd_reference_docx(args) -> int:
    from .backends.docx import make_reference_docx
    dest = Path(args.out)
    make_reference_docx(dest)
    print(t('Wrote {path}. Open it in Word, set up the styles (Heading 1, Body '
            'Text, Table Caption and so on), then write this in '
            'octavo.config.py:', path=dest)
          + f"\n  'docx_reference': '{dest.name}',")
    return 0


def cmd_outline(args) -> int:
    from .backends.docx import outline
    cfg = configmod.load(args.config)
    for name, src, is_appendix in cfg.sources():
        if args.documents and name not in args.documents:
            continue
        doc = cfg.documents[name]
        head = f'{name} ' + t('(appendix)') if is_appendix else name
        print(f'== {head}  ({cfg.rel(src)}, profile={doc.profile})')
        for line in outline(mdlib.read(src)):
            print('  ' + line)
    return 0


def cmd_selftest(args) -> int:
    from . import selftest
    targets = be.resolve_targets(args.to, 'paper') if args.to else None
    return selftest.run(targets=targets, csl=args.csl, keep=args.keep,
                        offline=args.offline)


def cmd_release(args) -> int:
    """節目の版をタグにし、組んだ PDF を GitHub Release に付ける（ghrelease.py）。"""
    from . import ghrelease
    cfg = configmod.load(args.config)
    targets = be.resolve_targets(args.to, 'paper') if args.to else None
    return ghrelease.run(cfg, args.document, args.label, targets=targets,
                         anonymous=args.anonymous, offline=args.offline,
                         dry_run=args.dry_run)


def cmd_template(args) -> int:
    """ひな型の一覧・写し・同梱との差分（上書きの仕組みは tmpl.py）。"""
    from . import tmpl
    cp = Path(args.config).resolve()
    if cp.is_dir():
        cp = cp / 'octavo.config.py'
    root = cp.parent if cp.is_file() else None
    try:
        name = tmpl.check_name(args.name) if args.name else None
    except tmpl.TemplateError:
        print(t('not a template name: {name}', name=args.name), file=sys.stderr)
        return 2
    bundled = tmpl.bundled_names()

    if args.action == 'list':
        rows = []
        for rel in bundled:
            layer, path = tmpl.resolve(rel, root)
            rows.append({'name': rel, 'from': layer, 'path': str(path)})
        for rel, layer, path in tmpl.overrides(root):
            if rel not in bundled:
                rows.append({'name': rel, 'from': layer, 'path': str(path)})
        dirs = {n: str(d) for n, d in tmpl.layers(root)}
        if args.json:
            import json as _json
            print(_json.dumps({'layers': dirs, 'templates': rows}, ensure_ascii=False))
            return 0
        label = {tmpl.PROJECT: t('this project'), tmpl.USER: t('yours'),
                 tmpl.BUNDLED: ''}
        width = max(len(r['name']) for r in rows)
        for r in rows:
            print(f"  {r['name'].ljust(width)}  {label[r['from']]}".rstrip())
        print('\n' + t('Looked for in this order (the first one found is used):'))
        for n, d in tmpl.layers(root):
            print(f'  {n:<8} {d}')
        print(t('Start your own with octavo template copy <name> [--user].'))
        return 0

    if not name:
        print(t('which template? (octavo template list shows them)'), file=sys.stderr)
        return 2
    if name not in bundled:
        print(t('no bundled template called {name} (octavo template list shows them)',
                name=name), file=sys.stderr)
        return 1
    source = tmpl.templates_dir() / name

    if args.action == 'copy':
        if args.user:
            dest = tmpl.user_dir() / name
        elif root is not None:
            dest = tmpl.project_dir(root) / name
        else:
            print(t('not inside a project (no octavo.config.py here) — '
                    'add --user to copy it for all your projects'), file=sys.stderr)
            return 1
        if dest.exists() and not args.force:
            print(t('{path} is already there (--force overwrites it)', path=dest),
                  file=sys.stderr)
            return 1
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(source.read_bytes())
        print(t('wrote {path} — edit it; it is used instead of the bundled one',
                path=dest))
        return 0

    # diff: 同梱の側が変わったか（Octavo を更新したあとに見る）
    layer, path = tmpl.resolve(name, root)
    if layer == tmpl.BUNDLED:
        print(t('{name} is not overridden — the bundled one is in use', name=name))
        return 0
    import difflib
    diff = list(difflib.unified_diff(
        source.read_text(encoding='utf-8').splitlines(keepends=True),
        path.read_text(encoding='utf-8').splitlines(keepends=True),
        fromfile=f'bundled/{name}', tofile=str(path)))
    if not diff:
        print(t('{path} is the same as the bundled one', path=path))
        return 0
    sys.stdout.writelines(diff)
    return 0


def cmd_targets(args) -> int:
    for name, b in be.REGISTRY.items():
        print(f'  {name:<10} {b.label:<26} pandoc {".".join(map(str, b.min_pandoc))}+')
    print('\n' + t('profiles:') + ' ' + ', '.join(be.PROFILES))
    return 0


# ---------------------------------------------------------------- 入口

def make_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog='octavo', description=usage_text(),
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--version', action='version', version=f'octavo {__version__}')
    sub = ap.add_subparsers(dest='cmd', required=True)

    def with_config(p):
        p.add_argument('--config', '-c', default='octavo.config.py',
                       help=t('where octavo.config.py is (default: here)'))
        return p

    p = with_config(sub.add_parser('build', help=t('build the manuscripts')))
    p.add_argument('documents', nargs='*', help=t('document names (default: all of them)'))
    p.add_argument('--to', '-t',
                   help=t('output formats: {list} / all / print. Several, '
                          'comma-separated', list='/'.join(be.ALL)))
    p.add_argument('--appendix', action='store_true', help=t('build the appendix too'))
    p.add_argument('--compile', action='store_true',
                   help=t('typeset it as well (latexmk / typst compile)'))
    p.add_argument('--offline', action='store_true', help=t('do not go and fetch a CSL'))
    p.add_argument('--no-citations', action='store_true',
                   help=t('leave citations unresolved (a fast look at a draft)'))
    p.add_argument('--no-analysis', action='store_true',
                   help=t('do not run the .qmd (build with results/ as it is)'))
    p.add_argument('--force-analysis', action='store_true',
                   help=t('run the .qmd again even if it is not stale'))
    p.add_argument('--anonymous', action='store_true',
                   help=t('build for blind review (hide anything identifying)'))
    p.add_argument('--json', action='store_true',
                   help=t('print the results as machine-readable JSON (including where the PDF landed)'))
    p.set_defaults(func=cmd_build)

    p = with_config(sub.add_parser('config', help=t('show or change the common settings')))
    p.add_argument('action', nargs='?', default='show', choices=['show', 'set', 'unset'])
    p.add_argument('key', nargs='?')
    p.add_argument('value', nargs='?')
    p.add_argument('--json', action='store_true', help=t('machine-readable JSON'))
    p.set_defaults(func=cmd_config)

    p = with_config(sub.add_parser('documents', help=t('list the registered manuscripts')))
    p.add_argument('--json', action='store_true', help=t('machine-readable JSON'))
    p.set_defaults(func=cmd_documents)

    p = with_config(sub.add_parser('watch', help=t('watch the manuscripts and rebuild')))
    p.add_argument('documents', nargs='*')
    p.add_argument('--to', '-t')
    p.add_argument('--appendix', action='store_true')
    p.add_argument('--compile', action='store_true')
    p.add_argument('--no-citations', action='store_true')
    p.add_argument('--no-analysis', action='store_true')
    p.set_defaults(func=cmd_watch)

    p = with_config(sub.add_parser('analysis', help=t('run the analysis (.qmd)')))
    p.add_argument('action', nargs='?', default='status',
                   choices=['status', 'run'],
                   help=t('status=see whether it is up to date (default) / run=run it'))
    p.add_argument('names', nargs='*',
                   help=t('with run: only these .qmd (run even if not stale)'))
    p.add_argument('--force', action='store_true',
                   help=t('run it again even if it is not stale'))
    p.add_argument('--json', action='store_true', help=t('machine-readable JSON'))
    p.set_defaults(func=cmd_analysis)

    p = with_config(sub.add_parser('values',
                                   help=t('cross-check {{…}} in the text against results/')))
    p.add_argument('--unused', action='store_true',
                   help=t('also list values the text does not use'))
    p.add_argument('--diff', nargs='?', const='', metavar='REF',
                   help=t('what changed since the analysis last ran; pass a git tag or commit to compare with that version'))
    p.add_argument('--json', action='store_true', help=t('machine-readable JSON'))
    p.set_defaults(func=cmd_values)

    p = with_config(sub.add_parser('lint', help=t('find results typed into the manuscript')))
    p.add_argument('--json', action='store_true', help=t('machine-readable JSON'))
    p.set_defaults(func=cmd_lint)

    p = with_config(sub.add_parser('check', help=t('one audit before submitting')))
    p.add_argument('--strict', action='store_true',
                   help=t('treat warnings as failures too (for CI)'))
    p.add_argument('--verbose', '-v', action='store_true',
                   help=t('print every detail'))
    p.add_argument('--anonymous', action='store_true',
                   help=t('add the blind-review checks as well (self-citations and the like)'))
    p.set_defaults(func=cmd_check)

    p = with_config(sub.add_parser('bundle', help=t('repackage it for submission')))
    p.add_argument('document', nargs='?',
                   help=t('which paper to pack (you can leave this out if there is only one)'))
    p.add_argument('--to', '-t', help=t('format (default: typst)'))
    p.add_argument('--out', help=t('where to write it (default: submission-<name>.zip)'))
    p.add_argument('--dir', action='store_true', help=t('leave it as a folder instead of a zip'))
    p.add_argument('--anonymous', action='store_true',
                   help=t('for blind review (run octavo build --anonymous first)'))
    p.add_argument('--replication', action='store_true',
                   help=t('make the post-acceptance replication package (a different set of files)'))
    p.add_argument('--with-raw-data', action='store_true',
                   help=t('put data/raw in the --replication package too (check it may be shared)'))
    p.set_defaults(func=cmd_bundle)

    p = sub.add_parser('review', help=t("read a coauthor's tracked changes out of a .docx"))
    p.add_argument('docx', help=t('the .docx that came back'))
    p.add_argument('--comments', action='store_true', help=t('comments only'))
    p.add_argument('--insertions', action='store_true', help=t('insertions only'))
    p.add_argument('--json', action='store_true', help=t('machine-readable JSON'))
    p.set_defaults(func=cmd_review)

    p = with_config(sub.add_parser('data', help=t('data fingerprints')))
    p.add_argument('action', nargs='?', default='status',
                   choices=['status', 'hash'],
                   help=t('status=check against the record (default) / hash=write the record'))
    p.set_defaults(func=cmd_data)

    p = with_config(sub.add_parser('checkbib', help=t('cross-check citation keys against the .bib')))
    p.add_argument('--list', action='store_true', help=t('list the references you cite'))
    p.add_argument('--unused', action='store_true', help=t('also list entries you never cite'))
    p.add_argument('--json', action='store_true',
                   help=t('print one line of machine-readable JSON (for the VS Code extension and friends)'))
    p.set_defaults(func=cmd_checkbib)

    p = with_config(sub.add_parser('bib', help=t('talk to Zotero')))
    p.add_argument('action', choices=['pull', 'collections', 'clean'])
    p.add_argument('--collection', help=t('Zotero collection name (leave it out for the whole library)'))
    p.add_argument('--format', default='biblatex', choices=['biblatex', 'bibtex'])
    p.add_argument('--out', help=t('where to write it (default: bib_file from the config)'))
    p.set_defaults(func=cmd_bib)

    p = with_config(sub.add_parser('csl', help=t("the journal's style (CSL)")))
    p.add_argument('action', choices=['get', 'list', 'which'])
    p.add_argument('name', nargs='?', help=t('a style ID or an alias'))
    p.set_defaults(func=cmd_csl)

    p = sub.add_parser('doctor', help=t('diagnose the environment'))
    p.add_argument('--verbose', '-v', action='store_true')
    p.add_argument('--json', action='store_true', help=t('machine-readable JSON'))
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser('setup', help=t('install the tools (pandoc, Typst, quarto, R, uv, fonts)'))
    p.add_argument('--with-tex', action='store_true', help=t('TeX Live too (several GB)'))
    p.add_argument('--no-quarto', action='store_true', help=t('leave out quarto'))
    p.add_argument('--no-r', action='store_true', help=t('leave out R'))
    p.add_argument('--check', action='store_true', help=t('only show what would be installed'))
    p.set_defaults(func=cmd_setup)

    p = with_config(sub.add_parser('env', help=t("set up this project's .venv and renv")))
    p.set_defaults(func=cmd_env)

    p = sub.add_parser('init', help=t('write a project skeleton (add manuscripts with octavo new)'))
    p.add_argument('dir')
    p.add_argument('--lang', default='ja', choices=['ja', 'en'])
    p.add_argument('--force', action='store_true', help=t('overwrite files that are already there'))
    p.set_defaults(func=cmd_init)

    p = with_config(sub.add_parser('new', help=t('add a manuscript (paper, slides or lecture notes)')))
    p.add_argument('kind', choices=list(scaffold.KINDS),
                   help=t('paper=a paper / slides=talk slides / lecture=lecture notes (an A4 handout + a deck per session)'))
    p.add_argument('name', help=t('the document name (it becomes the file or folder name)'))
    p.add_argument('--force', action='store_true', help=t('overwrite files that are already there'))
    p.set_defaults(func=cmd_new)

    p = sub.add_parser('reference-docx', help=t('write a Word reference .docx'))
    p.add_argument('out', nargs='?', default='reference.docx')
    p.set_defaults(func=cmd_reference_docx)

    p = with_config(sub.add_parser('outline', help=t('show the heading structure')))
    p.add_argument('documents', nargs='*')
    p.set_defaults(func=cmd_outline)

    p = sub.add_parser('selftest',
                       help=t('build a small manuscript for real and show how the citations come out'))
    p.add_argument('--to', '-t', help=t('formats (default: everything that works)'))
    p.add_argument('--csl', default='chicago-author-date', help=t('the style to try'))
    p.add_argument('--keep', action='store_true', help=t('keep what it built'))
    p.add_argument('--offline', action='store_true')
    p.set_defaults(func=cmd_selftest)

    p = with_config(sub.add_parser(
        'release', help=t('tag this version and put its PDF on a GitHub Release')))
    p.add_argument('document', help=t('the document name'))
    p.add_argument('label', help=t('what this version is, e.g. v1-submitted '
                                   '(the tag becomes <document>-<label>)'))
    p.add_argument('--to', '-t', help=t('formats (default: the document\'s targets)'))
    p.add_argument('--anonymous', action='store_true',
                   help=t('build for blind review (hide anything identifying)'))
    p.add_argument('--offline', action='store_true', help=t('do not go and fetch a CSL'))
    p.add_argument('--dry-run', action='store_true',
                   help=t('check and build, but tag, push and upload nothing'))
    p.set_defaults(func=cmd_release)

    p = with_config(sub.add_parser(
        'template', help=t('list, copy or compare the templates you can override')))
    p.add_argument('action', choices=['list', 'copy', 'diff'])
    p.add_argument('name', nargs='?', help=t('the template, e.g. slides/typst-slides.typ'))
    p.add_argument('--user', action='store_true',
                   help=t('copy it for all your projects (~/.config/octavo/templates)'))
    p.add_argument('--force', action='store_true', help=t('overwrite files that are already there'))
    p.add_argument('--json', action='store_true', help=t('machine-readable JSON'))
    p.set_defaults(func=cmd_template)

    p = sub.add_parser('targets', help=t('list the output formats'))
    p.set_defaults(func=cmd_targets)
    return ap


def main(argv=None) -> int:
    if os.name == 'nt':
        # Windows では、パイプ（VS Code の拡張機能が読む）への出力が既定で
        # CP932 などになり、日本語が化けたり └ のような字で止まったりする。
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.reconfigure(encoding='utf-8', errors='replace')
            except (AttributeError, ValueError):
                pass
    args = make_parser().parse_args(argv)
    try:
        return args.func(args) or 0
    except KeyboardInterrupt:
        return 130


if __name__ == '__main__':
    sys.exit(main())
