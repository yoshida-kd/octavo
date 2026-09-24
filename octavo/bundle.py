# -*- coding: utf-8 -*-
"""`octavo bundle` — 投稿システムに上げられる形に固め直す。

    octavo bundle                        論文が1本なら、その build/typst/<名前>/ から
                                         submission-<名前>.zip
    octavo bundle example-paper --to latex 論文が複数あるときは名前を指定する
    octavo bundle --dir                  zip にせずフォルダで残す
    octavo bundle --out example-talk.zip
    octavo bundle --anonymous            匿名審査用（先に build --anonymous）
    octavo bundle --replication          受理後の複製パッケージ

雑誌の投稿システムはたいてい**階層を持てない**。`\\includegraphics{../../figures/
fig1.pdf}` のままでは通らないので、参照しているファイルを1つの場所に集め、
本文側のパスを**ファイル名だけ**に書き換える。

書き換えの規則は形式ごとに違うので `Backend.flatten_assets()` に置いてある
（このモジュールは形式名で分岐しない）。`docx` のように1ファイルで完結する
形式は既定の実装が何もしないので、そのまま入るだけになる。

**元の build/ は触らない。**固めるのは複製に対して行う。

`--replication` は別物を作る。投稿用が「組版に要るもの」なのに対し、
複製パッケージは「**もう一度この結果を出すのに要るもの**」— 分析（.qmd）、
ヘルパー、データ、値、図表、設定、そして `data/HASHES.json` と `_session`。
原データは**既定で入れない**（再配布できないことがある）。`--with-raw-data`
で明示的に入れる。
"""
from __future__ import annotations

import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from . import backends as be
from . import dataset
from . import tmpl
from . import values as valmod
from .backends.base import Ctx
from .i18n import language, t, tag


@dataclass
class Result:
    out: Path | None = None
    files: list = field(default_factory=list)
    report: list = field(default_factory=list)
    ok: bool = True

    def say(self, s: str) -> None:
        self.report.append(s)


def collect(cfg, target: str, dest: Path, doc) -> Result:
    """文書の出力と、そこから参照されているファイルを dest に集める。"""
    backend = be.get(target)
    out_dir = cfg.out_dir(target, doc)
    res = Result()
    # 完結した文書（Word 等）は形式ごとのフォルダに他の文書と並んでいるので、
    # その文書のファイルだけを取る。main.* 方式はフォルダごとその文書のもの。
    ctx = Ctx(cfg=cfg, backend=backend, out_dir=out_dir, profile=doc.profile,
              doc_name=doc.name)
    pattern = backend.out_name(ctx) if ctx.standalone else f'*{backend.ext}'

    if not out_dir.is_dir():
        res.ok = False
        res.say(f'{tag("stopped")} ' + t('no output at {dir} (run octavo build '
                                         '--to {target} first)',
                                         dir=out_dir, target=target))
        return res

    dest.mkdir(parents=True, exist_ok=True)
    taken: dict = {}          # ファイル名 -> 元のパス（同名の衝突を見つける）

    def take(src: Path, why: str) -> None:
        name = src.name
        if name in taken:
            # 既に入れてある。本文どうしの相互参照（main.tex の \input{body}）
            # がここに来るので、**書き換え済みの中身を上書きしない**。
            if taken[name] != src.resolve():
                res.say(f'{tag("clash")} ' + t('two files share the name {name} '
                                               '({a} and {b}) — rename one',
                                               name=name, a=taken[name], b=src))
                res.ok = False
            return
        if not src.is_file():
            res.say(f'{tag("missing")} {why}: {src}')
            res.ok = False
            return
        taken[name] = src.resolve()
        shutil.copy2(src, dest / name)
        res.files.append(dest / name)

    # -- 本文（形式のテキスト）。参照を平らにしてから書き出す --------------
    texts = [] if backend.binary else sorted(
        p for p in out_dir.glob(pattern) if p.is_file())
    if not texts and not backend.binary:
        res.ok = False
        res.say(f'{tag("stopped")} ' + t('no {pattern} in {dir} (run octavo build '
                                         '{doc} --to {target} first)',
                                         pattern=pattern, dir=out_dir,
                                         doc=doc.name, target=target))
        return res

    # 先に本文を全部（平らにして）書き出し、名前を押さえる。そのあとで
    # 参照を集める — 順序が逆だと、本文が本文を上書きしてしまう。
    flattened: list = []
    for src in texts:
        flat, refs = backend.flatten_assets(src.read_text(encoding='utf-8'))
        (dest / src.name).write_text(flat, encoding='utf-8')
        res.files.append(dest / src.name)
        taken[src.name] = src.resolve()
        flattened.append((src, refs))

    for src, refs in flattened:
        for rel in refs:
            take((out_dir / rel).resolve(), t('referenced by {name}', name=src.name))

    # -- binary な形式（Word 等）はそのまま入れる --------------------------
    if backend.binary:
        for src in sorted(out_dir.glob(pattern)):
            take(src, t('output'))

    # -- 書誌。CSL で解決済みなので組版には要らないが、投稿時に求められる --
    bib = Path(cfg['bib_file'])
    if bib.is_file():
        take(bib, t('bibliography'))

    res.out = dest
    return res


# ---------------------------------------------------------------- 匿名審査

def check_anonymous(cfg, target: str, dest: Path, res: Result) -> None:
    """固めたものに著者が分かるものが残っていないか見る。

    題扉は `main.tex` / `main.typ` が持っていて Octavo は書き換えない。だから
    最後にここで**文字として残っていないか**を見る。ただし
    `\\ifanonymous` / `#if anonymous` で囲ってあるなら、組んだときには出ない
    ので致命的ではない（.tex ごと出す雑誌のために、注意としては言う）。
    """
    names = cfg['meta'].get('author') or []
    if isinstance(names, str):
        names = [names]
    inst = cfg['meta'].get('institute')
    needles = [str(x) for x in list(names) + ([inst] if inst else []) if str(x).strip()]
    backend = be.get(target)
    guard = backend.anonymous_guard

    flag_seen = False
    for p in sorted(dest.iterdir()):
        if not p.is_file() or p.suffix not in ('.tex', '.typ', '.md'):
            continue
        text = p.read_text(encoding='utf-8', errors='replace')
        if p.name in ('flags.tex', 'flags.typ'):
            flag_seen = 'true' in text
            continue
        guarded = backend.uses_anonymous_guard(text)
        for needle in needles:
            if needle not in text:
                continue
            if guarded:
                res.say(f'{tag("anonymous")} ' + t(
                    '{file} switches on {guard}, so it does not reach the typeset '
                    'output. But **{needle} is still in the source file** — delete '
                    'it if the journal wants the .tex itself',
                    file=p.name, guard=guard, needle=needle))
            else:
                res.say(f'{tag("anonymous")} ' + t(
                    '{needle} is still in {file} (guard it with {guard}, or delete '
                    'it by hand)', needle=needle, file=p.name,
                    guard=guard or t('a conditional')))
                res.ok = False

    if not flag_seen:
        res.say(f'{tag("anonymous")} ' + t('no sign this was built anonymously. Run '
                                           'octavo build --anonymous --to <format> '
                                           'first'))
        res.ok = False

    from . import check as checkmod
    mine = checkmod.self_citations(cfg)
    if mine:
        sep = '、' if language() == 'ja' else ', '
        res.say(f'{tag("anonymous")} ' + t(
            '{n} possible {n|self-citation|self-citations}: {keys} (whether to mask '
            '{n|it|them} depends on the journal)', n=len(mine), keys=sep.join(mine)))


# ---------------------------------------------------------------- 複製パッケージ

# 手順書の中の短い文言。手順書そのものは templates/replication/<lang>/README.md。
REPLICATION_NOTES = {
    'ja': {'packages': '（パッケージ {n} 件）',
           'no_session': ('（記録が無い。`octavo analysis run` を1度走らせると '
                          '`results/*.json` に `_session` として残る）'),
           'no_raw': '（原データは含めていない）'},
    'en': {'packages': ' ({n} packages)',
           'no_session': ('(none recorded — run `octavo analysis run` once and it is '
                          'kept in `results/*.json` as `_session`)'),
           'no_raw': ' (raw data not included)'},
}


def replication(cfg, dest: Path, with_raw: bool = False) -> Result:
    """受理後に出す複製パッケージ。投稿用とは中身が違う。"""
    res = Result()
    dest.mkdir(parents=True, exist_ok=True)
    excl = [str(x) for x in (cfg['replication_exclude'] or ())]

    def excluded(rel: str) -> bool:
        return any(Path(rel).match(pat) for pat in excl)

    def copy_tree(src: Path, rel_root: str, why: str) -> int:
        if not src.is_dir():
            return 0
        n = 0
        for p in sorted(src.rglob('*')):
            if not p.is_file() or any(x.startswith('.') for x in
                                      p.relative_to(src).parts):
                continue
            rel = f'{rel_root}/{p.relative_to(src).as_posix()}'
            if excluded(rel):
                continue
            out = dest / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, out)
            res.files.append(out)
            n += 1
        return n

    def copy_file(src: Path, rel: str) -> None:
        if not src.is_file():
            return
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)
        res.files.append(out)

    # -- 分析と成果物 -------------------------------------------------------
    # ヘルパー（octavo.R）は analysis/ の中にあるので、これ1回で入る
    res.say(f'{tag("replication")} analysis '
            + str(copy_tree(cfg.root / 'analysis', 'analysis', t('analysis'))))
    for d, label in ((Path(cfg['results_dir']), 'results'),
                     (Path(cfg['figure_dir']), 'figures'),
                     (Path(cfg['table_dir']), 'tables')):
        res.say(f'{tag("replication")} {label} ' + str(copy_tree(d, label, label)))
    copy_file(Path(cfg['bib_file']), Path(cfg['bib_file']).name)
    if cfg.source:
        copy_file(Path(cfg.source), Path(cfg.source).name)

    # -- データ。原データは明示しないと入れない -----------------------------
    data = dataset.data_dir(cfg)
    n = copy_tree(data / 'derived', 'data/derived', t('data'))
    res.say(f'{tag("replication")} data/derived {n}')
    if with_raw:
        n = copy_tree(data / 'raw', 'data/raw', t('raw data'))
        res.say(f'{tag("replication")} data/raw {n} '
                + t('(make sure this data may be redistributed)'))
    else:
        res.say(f'{tag("replication")} ' + t('data/raw is not included '
                                             '(--with-raw-data adds it, once you '
                                             'have checked it may be shared)'))

    # -- 指紋。データを入れなくても「何を使ったか」は残す --------------------
    if not dataset.manifest_path(cfg).is_file():
        dataset.write(cfg)
        res.say(f'{tag("replication")} ' + t('there was no data/HASHES.json, '
                                             'so it was written'))
    copy_file(dataset.manifest_path(cfg), 'data/HASHES.json')

    # -- 手順書 -------------------------------------------------------------
    notes = REPLICATION_NOTES['ja' if cfg['lang'] == 'ja' else 'en']
    sess = valmod.session_info(cfg)
    if sess:
        lines = []
        for f, v in sess.items():
            pk = v.get('packages') or {}
            lines.append(f'- `{f}`: {v.get("engine", "?")} {v.get("version", "")}'
                         f' / {v.get("platform", "")}'
                         + (notes['packages'].replace('{n}', str(len(pk))) if pk else ''))
        session = '\n'.join(lines)
    else:
        session = notes['no_session']
    title = str(cfg['meta'].get('title') or cfg.root.name)
    readme = (tmpl.read(f"replication/{'ja' if cfg['lang'] == 'ja' else 'en'}/README.md",
                        cfg.root)
              .replace('@@TITLE@@', title)
              .replace('@@SESSION@@', session)
              .replace('@@RAWNOTE@@',
                       '' if with_raw else notes['no_raw']))
    (dest / 'README.md').write_text(readme, encoding='utf-8')
    res.files.append(dest / 'README.md')

    res.out = dest
    return res


def pick_paper(cfg, name: str | None):
    """固める論文。名前が無ければ、論文（profile paper）が1本だけのときそれを選ぶ。"""
    if name:
        return cfg.document(name)
    papers = [d for d in cfg.documents.values() if d.profile == 'paper']
    if len(papers) == 1:
        return papers[0]
    if not papers:
        raise SystemExit(t('there is no paper. Name the document to package '
                           '(octavo bundle <name>)'))
    raise SystemExit(t('there is more than one paper. Name the one to package: '
                       'octavo bundle <name>') + '\n  '
                     + t('papers: {names}', names=', '.join(d.name for d in papers)))


def run(cfg, target: str = 'typst', out: str | None = None,
        as_dir: bool = False, anonymous: bool = False,
        as_replication: bool = False, with_raw: bool = False,
        document: str | None = None) -> int:
    doc = None if as_replication else pick_paper(cfg, document)
    default = 'replication' if as_replication else f'submission-{doc.name}'
    name = out or (default + ('' if as_dir else '.zip'))
    final = (cfg.root / name).resolve()
    work = final if as_dir else final.with_suffix('')

    if work.exists():
        shutil.rmtree(work, ignore_errors=True)
    if as_replication:
        res = replication(cfg, work, with_raw=with_raw)
    else:
        res = collect(cfg, target, work, doc)
        if anonymous and res.files:
            check_anonymous(cfg, target, work, res)

    for line in res.report:
        print('  ' + line)
    if not res.ok and not res.files:
        return 1

    if as_dir:
        print('\n' + t('gathered {n} {n|file|files} into {path}', n=len(res.files), path=final))
    else:
        with zipfile.ZipFile(final, 'w', zipfile.ZIP_DEFLATED) as z:
            for p in sorted(res.files):
                # 複製パッケージは階層を保つ（投稿用だけ平らにする）
                z.write(p, p.relative_to(work).as_posix() if as_replication
                        else p.name)
        shutil.rmtree(work, ignore_errors=True)
        size = final.stat().st_size
        print('\n' + t('packed {n} {n|file|files} into {path} ({size} bytes)',
                       n=len(res.files), path=final, size=f'{size:,}'))
    for p in sorted(res.files):
        print('  ' + (p.relative_to(work).as_posix() if as_replication else p.name))
    if not res.ok:
        print('\n' + t('something is missing, clashing, or not anonymised. Fix what '
                       'is above before submitting'))
    return 0 if res.ok else 1
