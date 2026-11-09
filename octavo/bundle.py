# -*- coding: utf-8 -*-
"""`octavo bundle` — 投稿システムに上げられる形にまとめ直す。

    octavo bundle                        論文が1本なら、その build/pdf/<名前>/ から
                                         submission-<名前>.zip
    octavo bundle example-paper --to latex 論文が複数あるときは名前を指定する
    octavo bundle --dir                  zip にせずフォルダで残す
    octavo bundle --out example-talk.zip
    octavo bundle --anonymous            匿名審査用（先に build --anonymous）
    octavo bundle --replication          受理後の複製パッケージ

雑誌の投稿システムはたいてい**階層を持てない**。`\\includegraphics{../../assets/figures/
fig1.pdf}` のままでは通らないので、参照しているファイルを1つの場所に集め、
本文側のパスを**ファイル名だけ**に書き換える。

書き換えの規則は形式ごとに違うので `Backend.flatten_assets()` に置いてある
（このモジュールは形式名で分岐しない）。`docx` のように1ファイルで完結する
形式は既定の実装が何もしないので、そのまま入るだけになる。

**元の build/ は触らない。**まとめるのは複製に対して行う。

`--replication` は別物を作る。投稿用が「組版に要るもの」なのに対し、
複製パッケージは「**もう一度この結果を出すのに要るもの**」— 分析（.qmd）、
ヘルパー、データ、値、図表、設定、そして `data/HASHES.json` と `_session`。
原データは**既定で入れない**（再配布できないことがある）。`--with-raw-data`
で明示的に入れる。`--standalone` は、中の `.qmd` を Octavo のヘルパーなしで読めるように
書き換える（standalone.py）。パッケージは既定で英語で、日本語の行は翻訳ファイルから当てる
（translate.py）。`--lang ja` はそのまま日本語で出す。`--verify` はパッケージそのものを実行して、
数値を記録と比べる。

**出力先に、Octavo が作ったのではないものがあれば消さない。**zip は一時フォルダで作るので、
同じ名前のフォルダ（`--out data.zip` の `data/`）には触らない。`--dir` のフォルダを作り直すのは、
前回 Octavo が書いたファイルしか入っていないときだけ（記録は build/.bundle-folders.json）。
"""
from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from . import analysis as anamod
from . import backends as be
from . import dataset
from . import standalone as standmod
from . import tmpl
from . import translate as transmod
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
            p = (out_dir / rel).resolve()
            if not p.is_file() and Path(rel).name == f'appendix{backend.ext}' \
                    and backend.splits_appendix(src.read_text(encoding='utf-8')):
                continue        # 付録を別の PDF にする体裁: 付録の無い論文なら要らない
            take(p, t('referenced by {name}', name=src.name))

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
    """まとめたものに著者が分かるものが残っていないか見る。

    タイトル部分は `main.tex` / `main.typ` が持っていて Octavo は書き換えない。だから
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
    'ja': {'setup_any': '分析が使う R や Python のパッケージを入れる。',
           'setup_r': ('次の版で R のパッケージを入れる（`renv.lock`）。実行すると、このフォルダに '
                       '`renv/` と `.Rprofile` ができる。'),
           'setup_py': '次の版で Python のパッケージを入れる（`requirements.txt`）。仮想環境の中で実行するとよい。',
           'manual': ('次の分析は上の手順に入れていない。手で実行する印が付いている（時間がかかる、データを取りに行く '
                      'など）もので、その結果はこのパッケージに入っている。'),
           'packages': '（パッケージ {n} 件）',
           'no_record': '（記録がない）',
           'no_session': ('（記録がない。`octavo analysis run` を1度実行すると '
                          '`assets/values/*.json` に `_session` として残る）'),
           'no_raw': '（原データは含めていない）'},
    'en': {'setup_any': 'Install the R or Python packages the analysis uses.',
           'setup_r': ('Install the R packages at the recorded versions (`renv.lock`). This adds `renv/` and '
                       '`.Rprofile` to this folder.'),
           'setup_py': 'Install the Python packages at the recorded versions (`requirements.txt`), best in a virtual environment.',
           'manual': ('These analyses are not in the steps above. They are marked to be run by hand (they take '
                      'long or fetch data, for instance), and their results are in this package.'),
           'packages': ' ({n} packages)',
           'no_record': '(none recorded)',
           'no_session': ('(none recorded — run `octavo analysis run` once and it is '
                          'kept in `assets/values/*.json` as `_session`)'),
           'no_raw': ' (raw data not included)'},
}


def replication_steps(cfg, dest: Path, lang: str) -> tuple:
    """手順書の「環境を作る」と「実行する」。順番は設定の順で、手動の分析は別に示す。"""
    notes = REPLICATION_NOTES[lang]
    us = [u for u in anamod.units(cfg) if (dest / anamod.key(cfg, u)).is_file()]
    engines = {anamod.engine(u.src) for u in us if u.src.is_file()}
    blocks = []
    if (not engines or any('r' in e.split('+') for e in engines)) and (dest / 'renv.lock').is_file():
        blocks.append(notes['setup_r'] + '\n\n'
                      '    Rscript -e \'install.packages("renv")\'\n'
                      '    Rscript -e \'renv::activate()\'\n'
                      '    Rscript -e \'renv::restore(prompt = FALSE)\'')
    if any('python' in e for e in engines) and (dest / 'requirements.txt').is_file():
        blocks.append(notes['setup_py'] + '\n\n    pip install -r requirements.txt')
    setup = '\n\n'.join(blocks) or notes['setup_any']
    auto = [anamod.key(cfg, u) for u in us if not u.manual]
    manual = [anamod.key(cfg, u) for u in us if u.manual]
    run = '\n'.join(f'    quarto render {k}' for k in auto) or '    quarto render analysis/*.qmd'
    if manual:
        run += '\n\n' + notes['manual'] + '\n\n' + '\n'.join(f'- `{k}`' for k in manual)
    return setup, run


def _standalone_dirs(cfg) -> dict:
    return {'values': cfg.rel(Path(cfg['values_dir'])), 'figures': cfg.rel(Path(cfg['figure_dir'])),
            'tables': cfg.rel(Path(cfg['table_dir']))}


def _convert(cfg, dest: Path, qmd: Path):
    snippet = lambda name: tmpl.read(f'replication/standalone/{name}', cfg.root)
    return standmod.convert(qmd.read_text(encoding='utf-8'), _standalone_dirs(cfg),
                            len(qmd.relative_to(dest).parts) - 1, snippet)


def _helpers_of(dest: Path) -> dict:
    return {dest / 'analysis' / name: lang for name, lang in transmod.HELPERS.items()}


def _helpers_kept(cfg, dest: Path) -> set:
    """--standalone のあとも残るヘルパーの言語（書き換えはしない）。訳す前に、何を訳すか決めるため。"""
    keeps: set = set()
    helpers = _helpers_of(dest)
    for qmd in sorted((dest / 'analysis').rglob('*.qmd')):
        keeps |= _convert(cfg, dest, qmd).keeps
    for p in sorted((dest / 'analysis').rglob('*')):
        if p.suffix in transmod.SCRIPTS and p.is_file() and p not in helpers \
                and standmod.uses_helper(p.read_text(encoding='utf-8', errors='replace')):
            keeps.add(transmod.SCRIPTS[p.suffix])
    return keeps


def make_standalone(cfg, dest: Path, res: Result) -> bool:
    """パッケージの中の .qmd からヘルパーを外す。プロジェクトの .qmd は触らない。

    ov_ が残るものは読み込みごと残すので、パッケージは動くまま。ヘルパーがどれにも要らなく
    なれば、ヘルパーと設定をパッケージから除く。除いたら True。"""
    analysis = dest / 'analysis'
    keeps: set = set()
    for qmd in sorted(analysis.rglob('*.qmd')):
        rel = qmd.relative_to(dest).as_posix()
        out = _convert(cfg, dest, qmd)
        qmd.write_text(out.text, encoding='utf-8')
        keeps |= out.keeps
        res.say(f'{tag("standalone")} ' + t('{file}: replaced {n} {n|call|calls}, left {m}',
                                            file=rel, n=out.replaced, m=len(out.left)))
        for left in out.left:
            res.say(f'  {rel}:{left.line}: {left.call} — {left.why}')
    helpers = _helpers_of(dest)
    for p in sorted(analysis.rglob('*')):
        if p.suffix in transmod.SCRIPTS and p.is_file() and p not in helpers \
                and standmod.uses_helper(p.read_text(encoding='utf-8', errors='replace')):
            keeps.add('python' if p.suffix == '.py' else 'r')
            res.say(f'{tag("standalone")} ' + t('{file} uses the helper; it is left as it is',
                                                file=p.relative_to(dest).as_posix()))
    for helper, lang in helpers.items():
        if lang not in keeps and helper.is_file():
            helper.unlink()
            res.files.remove(helper)
    if keeps:
        res.say(f'{tag("standalone")} ' + t('some analyses still use the helper, so it stays in the package '
                                            'and they run as they are'))
        return False
    return True


def replication(cfg, dest: Path, with_raw: bool = False, standalone: bool = False,
                lang: str | None = None, verify: bool = False) -> Result:
    """受理後に出す複製パッケージ。投稿用とは中身が違う。

    lang: パッケージの言語。読む人は国際的な読者が基本なので、省略すれば英語で、日本語の行は
    翻訳ファイルから当てる。'ja' は何も訳さず、手順書も日本語にする。"""
    lang = lang or 'en'
    res = Result()
    dest.mkdir(parents=True, exist_ok=True)
    excl = [str(x) for x in (cfg['replication_exclude'] or ())]

    def excluded(rel: str) -> bool:
        return any(Path(rel).match(pat) for pat in excl)

    def copy_tree(src: Path, rel_root: str, why: str, skip=None) -> int:
        if not src.is_dir():
            return 0
        n = 0
        for p in sorted(src.rglob('*')):
            if not p.is_file() or any(x.startswith('.') for x in
                                      p.relative_to(src).parts):
                continue
            if skip and skip(p):
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
    # Quarto の作業物と出力（<名前>_files/、.qmd の隣の HTML・PDF など）は、
    # 実行すればできるので入れない
    def quarto_output(p: Path) -> bool:
        parts = p.relative_to(cfg.root / 'analysis').parts
        if parts[0] == transmod.SUBDIR or any(x.endswith(('_files', '_cache')) for x in parts[:-1]):
            return True
        return p.suffix in anamod.RENDERED and p.with_suffix('.qmd').is_file()
    res.say(f'{tag("replication")} analysis '
            + str(copy_tree(cfg.root / 'analysis', 'analysis', t('analysis'),
                            skip=quarto_output)))
    # プロジェクトと同じ場所に置く（octavo.R の既定の置き場 assets/ がそのまま効く）。
    # 手で作った図（Typst の .typ など）と表（.csv）も、論文の図表の元なので入れる
    for d in (Path(cfg['values_dir']), Path(cfg['figure_dir']), Path(cfg['table_dir']),
              Path(cfg['figure_src_dir']), Path(cfg['table_src_dir'])):
        label = cfg.rel(d)
        res.say(f'{tag("replication")} {label} ' + str(copy_tree(d, label, label)))
    copy_file(Path(cfg['bib_file']), Path(cfg['bib_file']).name)
    # 使ったパッケージの版の記録。これがないと、同じ環境を作り直せない
    # _quarto.yml は実行の仕方を変えるので、これも一緒に
    for record in ('renv.lock', 'requirements.txt', '_quarto.yml'):
        copy_file(cfg.root / record, record)
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

    # -- ハッシュ値。データを入れなくても「何を使ったか」は残す --------------------
    if not dataset.manifest_path(cfg).is_file():
        dataset.write(cfg)
        res.say(f'{tag("replication")} ' + t('there was no data/HASHES.json, '
                                             'so it was written'))
    copy_file(dataset.manifest_path(cfg), 'data/HASHES.json')

    # -- 手順書 -------------------------------------------------------------
    notes = REPLICATION_NOTES[lang]
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
    config_copy = dest / Path(cfg.source).name if cfg.source else None
    if lang == 'en':
        title = transmod.title(cfg, title)
        # --standalone で外れるヘルパーと設定は、訳さない
        kept = _helpers_kept(cfg, dest) if standalone else set(transmod.HELPERS.values())
        transmod.localize(cfg, dest, res.say, without=tuple(
            name for name, helper_lang in transmod.HELPERS.items() if helper_lang not in kept))
        if config_copy and config_copy.is_file() and (kept or not standalone):
            transmod.localize_config(cfg, config_copy, res.say)
        transmod.english_records(cfg, dest)
    if verify and not transmod.verify(cfg, dest, res.say):
        res.ok = False
    # ヘルパーが要らなくなったパッケージには、設定も Octavo の手順も入れない
    free = standalone and make_standalone(cfg, dest, res)
    if verify and standalone and res.ok and not transmod.verify_rewritten(cfg, dest, res.say):
        res.ok = False
    if lang == 'en' and (others := transmod.others_in_japanese(dest)):
        res.say(f'{tag("translation")}{tag("note")} ' + t(
            'Japanese remains in these files, which Octavo does not translate (they come from the analysis '
            'or the settings): {files}',
            files=', '.join(f'{name} ({n})' for name, n in others.items())))
    if free and cfg.source:
        if config_copy.is_file():
            config_copy.unlink()
            res.files.remove(config_copy)
    page = 'README-standalone.md' if free else 'README.md'
    if free and not sess:
        session = notes['no_record']
    setup, steps = replication_steps(cfg, dest, lang)
    readme = (tmpl.read(f'replication/{lang}/{page}', cfg.root)
              .replace('@@TITLE@@', title)
              .replace('@@SESSION@@', session)
              .replace('@@SETUP@@', setup)
              .replace('@@RUN@@', steps)
              .replace('@@RAWNOTE@@',
                       '' if with_raw else notes['no_raw']))
    (dest / 'README.md').write_text(readme, encoding='utf-8')
    res.files.append(dest / 'README.md')

    res.out = dest
    return res


def pick_paper(cfg, name: str | None):
    """まとめる論文。名前がなければ、論文（profile paper）が1本だけのときそれを選ぶ。"""
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


# ---------------------------------------------------------------- 出力先

def _folder_record(cfg) -> Path:
    return Path(cfg.root) / 'build' / '.bundle-folders.json'


def _files_in(folder: Path) -> list:
    return sorted(p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file())


def _read_folders(cfg) -> dict:
    try:
        got = json.loads(_folder_record(cfg).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    return got if isinstance(got, dict) else {}


def _remember_folder(cfg, folder: Path) -> None:
    got = _read_folders(cfg)
    got[str(folder)] = _files_in(folder)
    path = _folder_record(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(got, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def check_out(cfg, final: Path, as_dir: bool) -> None:
    """出力先が、消してはいけないものを指していれば断る。何も消さないうちに呼ぶ。"""
    root = Path(cfg.root).resolve()
    if final == root or final in root.parents:
        raise SystemExit(t('{path} holds this project, so it cannot be the output', path=final))
    if as_dir:
        if final.is_file():
            raise SystemExit(t('{path} is a file. Choose another --out', path=final))
        if final.is_dir():
            files = _files_in(final)
            if files and not set(files) <= set(_read_folders(cfg).get(str(final), ())):
                raise SystemExit(t('{path} already exists and has files Octavo did not write, so it was left '
                                   'alone. Choose another --out, or move it', path=final))
    elif final.is_dir():
        raise SystemExit(t('{path} is a folder, so the zip cannot go there. Choose another --out, or move '
                           'the folder', path=final))
    elif final.is_file() and not zipfile.is_zipfile(final):
        raise SystemExit(t('{path} already exists and is not a zip, so it was left alone. Choose another '
                           '--out', path=final))


def run(cfg, target: str = 'typst', out: str | None = None,
        as_dir: bool = False, anonymous: bool = False,
        as_replication: bool = False, with_raw: bool = False,
        document: str | None = None, standalone: bool = False,
        lang: str | None = None, verify: bool = False) -> int:
    if standalone and not as_replication:
        raise SystemExit(t('--standalone goes with --replication'))
    if (lang or verify) and not as_replication:
        raise SystemExit(t('--lang and --verify go with --replication'))
    doc = None if as_replication else pick_paper(cfg, document)
    default = 'replication' if as_replication else f'submission-{doc.name}'
    name = out or (default + ('' if as_dir else '.zip'))
    final = (cfg.root / name).resolve()
    check_out(cfg, final, as_dir)
    if as_dir:
        if final.is_dir():
            shutil.rmtree(final)
        work = final
        return _gather(cfg, target, final, work, as_dir, anonymous, as_replication, with_raw, doc,
                       standalone, lang, verify)
    # zip は一時フォルダで作る。出力先の隣にある同じ名前のフォルダには触らない
    holder = Path(tempfile.mkdtemp(prefix='octavo-bundle-'))
    try:
        return _gather(cfg, target, final, holder / (final.stem or 'bundle'), as_dir, anonymous,
                       as_replication, with_raw, doc, standalone, lang, verify)
    finally:
        shutil.rmtree(holder, ignore_errors=True)


def _gather(cfg, target, final, work, as_dir, anonymous, as_replication, with_raw, doc,
            standalone, lang, verify) -> int:
    if as_replication:
        res = replication(cfg, work, with_raw=with_raw, standalone=standalone, lang=lang, verify=verify)
    else:
        res = collect(cfg, target, work, doc)
        if anonymous and res.files:
            check_anonymous(cfg, target, work, res)

    for line in res.report:
        print('  ' + line)
    if not res.ok and not res.files:
        return 1

    # 確かめて通らなかったものは、提出できる形にしない
    failed_check = as_replication and verify and not res.ok
    if as_dir:
        _remember_folder(cfg, final)
        print('\n' + t('gathered {n} {n|file|files} into {path}', n=len(res.files), path=final))
    elif failed_check:
        print('\n' + t('the package did not pass --verify, so no zip was made. Fix what is above and run it again'))
        return 1
    else:
        final.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(final, 'w', zipfile.ZIP_DEFLATED) as z:
            for p in sorted(res.files):
                # 複製パッケージは階層を保つ（投稿用だけ平らにする）
                z.write(p, p.relative_to(work).as_posix() if as_replication
                        else p.name)
        size = final.stat().st_size
        print('\n' + t('packed {n} {n|file|files} into {path} ({size} bytes)',
                       n=len(res.files), path=final, size=f'{size:,}'))
    for p in sorted(res.files):
        print('  ' + (p.relative_to(work).as_posix() if as_replication else p.name))
    if failed_check:
        print('\n' + t('the package did not pass --verify. Fix what is above before sending it'))
    elif not res.ok:
        print('\n' + t('something is missing, clashing, or not anonymised. Fix what '
                       'is above before submitting'))
    return 0 if res.ok else 1
