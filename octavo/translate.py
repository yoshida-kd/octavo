# -*- coding: utf-8 -*-
"""日本語で書いた分析を、英語の再現用パッケージにする（`octavo bundle --replication`。既定で英語）。

Octavo は訳さない。文字列にはデータとの照合や正規表現（"本会議"、"令和|平成"）があり、機械的に
訳すと分析が壊れるからである。訳すのは人か AI で、ここがするのは次のことだけ。

- 日本語の残る行を、翻訳ファイル analysis/replication/<qmd の名前>.en.json（.R や .py は
  <名前>.R.en.json）に書き足す。分類は prose（地の文・前書き）、comments（コードのコメント）、code
  （コードの中の文字列など。訳してよいか確かめるもの）。中身は {"prose": {"元の行": "英語の行"}, …} で、
  訳が空のものは使わない
- パッケージの複製にだけ、行ごとに当てる。元の行が直されたら、未翻訳として書き足される
- 設定ファイルの日本語のコメントは複製から除き、表の先頭の注釈と HASHES.json の説明は英語にする
- それでも残る日本語（分析が書いた表の中身など）は、ファイルごとに知らせる

`verify` はパッケージそのものを一時フォルダで実行し、数値が記録と同じか比べる（書き出しのファイルを
比べるだけで、Quarto の出力は読まない）。プロジェクトの環境（renv、.venv）だけは借りるので、確かめられるのは
「ファイルが揃っていて、同じ数値が出ること」で、版を作り直せることではない。`--standalone` の
書き換えは数値を書き出さないので、書き換えの前に比べ、書き換えた後は実行できることと図表ができることを見る。
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import analysis as anamod
from . import dataset
from . import standalone as standmod
from .i18n import t, tag

JAPANESE = re.compile(r'[　-ヿ㐀-鿿＀-￯]')
KINDS = ('prose', 'comments', 'code')
SUBDIR = 'replication'           # analysis/ の下。パッケージには入れない
HELPERS = {'octavo.R': 'r', 'octavo_helper.py': 'python'}
SCRIPTS = {'.R': 'r', '.r': 'r', '.py': 'python'}
# 実行に借りるもの（パッケージには入れない）
ENVIRONMENT = ('.Rprofile', 'renv', '.venv')
# 古い版のヘルパーと handtables.py が書いた、表の先頭の注釈
TABLE_NOTES = ((re.compile(r'(octavo\.R|octavo_helper\.py) の ov_table\(\) が作ったファイル。手で直さない。'),
                r'Written by ov_table() in \1. Do not edit by hand.'),
               (re.compile(r'(\S+) が (\S+) から作ったファイル。手で直さない（\S+ を直す）。'),
                r'Written by \1 from \2. Do not edit by hand (edit \2).'))
# 中身を読んで知らせるファイルの種類
TEXT_SUFFIXES = ('.md', '.json', '.tex', '.typ', '.csv', '.txt')


def has_japanese(text: str) -> bool:
    return JAPANESE.search(text) is not None


def classify(text: str) -> dict:
    """日本語の残る行を、分類ごとに（出てくる順で重複なしに）返す。キーは前後の空白を除いた行。"""
    found: dict = {k: {} for k in KINDS}
    for part in standmod._split(text):
        if part[0] == 'text':
            for line in part[1]:
                if has_japanese(line):
                    found['prose'][line.strip()] = True
            continue
        _, lang, opening, lines, closing, _ = part
        if has_japanese(opening):
            found['code'][opening.strip()] = True
        masked = standmod.mask('\n'.join(lines), lang).split('\n')
        for line, m in zip(lines, masked):
            if not has_japanese(line):
                continue
            at = m.find(standmod.COMMENT)
            kind = 'code' if at < 0 or has_japanese(line[:at]) else 'comments'
            found[kind][line.strip()] = True
    return {k: list(v) for k, v in found.items()}


def classify_script(text: str, lang: str) -> dict:
    """.R / .py のファイルの、日本語の残る行。全体を1つのチャンクとして見る。"""
    found: dict = {k: {} for k in KINDS}
    for line, m in zip(text.split('\n'), standmod.mask(text, lang).split('\n')):
        if has_japanese(line):
            at = m.find(standmod.COMMENT)
            found['code' if at < 0 or has_japanese(line[:at]) else 'comments'][line.strip()] = True
    return {k: list(v) for k, v in found.items()}


def table_path(cfg, rel_file: str) -> Path:
    """analysis/x/y.qmd -> analysis/replication/x/y.en.json、analysis/x/y.R -> …/x/y.R.en.json"""
    rel = Path(rel_file).relative_to('analysis')
    name = rel.with_suffix('.en.json') if rel.suffix == '.qmd' else rel.with_name(rel.name + '.en.json')
    return Path(cfg.root) / 'analysis' / SUBDIR / name


def read_table(path: Path) -> dict:
    if not path.is_file():
        return {k: {} for k in KINDS}
    try:
        got = json.loads(path.read_text(encoding='utf-8'))
    except ValueError as e:
        raise SystemExit(t('cannot read {file}: {why}', file=path, why=e))
    if not isinstance(got, dict):
        raise SystemExit(t('cannot read {file}: {why}', file=path, why='{…}'))
    return {k: {o: v for o, v in (got.get(k) or {}).items() if isinstance(v, str)} for k in KINDS}


def _write_table(path: Path, table: dict) -> None:
    text = json.dumps(table, ensure_ascii=False, indent=1) + '\n'
    if not path.is_file() or path.read_text(encoding='utf-8') != text:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')


def apply_table(text: str, table: dict) -> str:
    """訳のある行を置き換える。字下げは元の行のまま。行の数は変えない前提にしない。"""
    done = {o: v for kind in KINDS for o, v in table[kind].items() if v.strip()}
    out = []
    for line in text.split('\n'):
        new = done.get(line.strip())
        out.append(line if new is None else line[:len(line) - len(line.lstrip())] + new)
    return '\n'.join(out)


def localize(cfg, dest: Path, say, without: tuple = ()) -> None:
    """パッケージの .qmd と .R / .py に訳を当て、足りない行を翻訳ファイルに書き足す。プロジェクトのものは
    触らない。without: 訳さないファイルの名前（パッケージから外れるヘルパー）。"""
    analysis = dest / 'analysis'
    files = [p for p in analysis.rglob('*') if p.is_file() and p.name not in without
             and (p.suffix == '.qmd' or p.suffix in SCRIPTS)]
    for path in sorted(files):
        rel = path.relative_to(dest).as_posix()
        text = path.read_text(encoding='utf-8', errors='replace')
        found = classify(text) if path.suffix == '.qmd' else classify_script(text, SCRIPTS[path.suffix])
        table_file = table_path(cfg, rel)
        table = read_table(table_file)
        lines = {o for k in KINDS for o in found[k]}
        unused = sum(1 for k in KINDS for o in table[k] if o not in lines)
        known = {o for k in KINDS for o in table[k]}
        fresh = 0
        for k in KINDS:
            for o in found[k]:
                if o not in known:
                    table[k][o] = ''
                    fresh += 1
        if fresh:
            _write_table(table_file, table)
        path.write_text(apply_table(text, table), encoding='utf-8')
        done = {o for k in KINDS for o, v in table[k].items() if v.strip()}
        if lines or unused:
            left = {k: sum(1 for o in found[k] if o not in done) for k in KINDS}
            say(f'{tag("translation")} ' + t(
                '{file}: {n} of {total} Japanese lines translated; to do: {prose} prose, {comments} comments, '
                '{code} in code ({table})', file=rel, n=len(lines & done), total=len(lines), table=
                table_file.relative_to(cfg.root).as_posix(), **{k: left[k] for k in KINDS}))
            if unused:
                say(f'{tag("translation")} ' + t(
                    '{table}: {n} {n|entry is|entries are} no longer in the .qmd',
                    table=table_file.relative_to(cfg.root).as_posix(), n=unused))


def clean_config(text: str) -> str:
    """設定ファイルの日本語のコメントを除く（読む人には要らない説明と、書きかけの例）。値は残す。"""
    out = []
    for line, m in zip(text.split('\n'), standmod.mask(text, 'python').split('\n')):
        at = m.find(standmod.COMMENT)
        if at < 0 or not has_japanese(line[at:]):
            out.append(line)
        elif line[:at].strip():
            out.append(line[:at].rstrip())
    return '\n'.join(out)


def localize_config(cfg, path: Path, say) -> None:
    """パッケージの設定ファイル。コメントを除き、日本語の残る値は package.en.json の訳を当てる。"""
    text = clean_config(path.read_text(encoding='utf-8'))
    lines = [l.strip() for l in text.split('\n') if has_japanese(l)]
    table_file = Path(cfg.root) / 'analysis' / SUBDIR / 'package.en.json'
    table = read_table(table_file)
    fresh = [l for l in lines if l not in table['code']]
    if fresh:
        table['code'].update({l: '' for l in fresh})
        _write_table(table_file, table)
    path.write_text(apply_table(text, table), encoding='utf-8')
    left = sum(1 for l in lines if not table['code'][l].strip())
    if left:
        say(f'{tag("translation")} ' + t('{file}: {n} {n|setting has|settings have} Japanese values; to do in {table}',
                                         file=path.name, n=left, table=table_file.relative_to(cfg.root).as_posix()))


def english_records(cfg, dest: Path) -> None:
    """Octavo 自身が書いた日本語の説明を、パッケージの中だけ英語にする。"""
    tables = dest / cfg.rel(Path(cfg['table_dir']))
    for p in sorted(tables.rglob('*')) if tables.is_dir() else ():
        if p.is_file() and p.suffix in TEXT_SUFFIXES:
            text = p.read_text(encoding='utf-8', errors='replace')
            new = text
            for pattern, repl in TABLE_NOTES:
                new = pattern.sub(repl, new)
            if new != text:
                p.write_text(new, encoding='utf-8')
    # requirements.txt のコメントはテンプレートの説明で、書式は設定ファイルと同じ（# から行末まで）
    requirements = dest / 'requirements.txt'
    if requirements.is_file():
        requirements.write_text(clean_config(requirements.read_text(encoding='utf-8')), encoding='utf-8')
    hashes = dest / 'data' / dataset.MANIFEST_NAME
    if hashes.is_file():
        try:
            got = json.loads(hashes.read_text(encoding='utf-8'))
        except ValueError:
            return
        if isinstance(got, dict) and has_japanese(str(got.get('_note', ''))):
            got['_note'] = dataset.NOTE['en']
            hashes.write_text(json.dumps(got, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def others_in_japanese(dest: Path) -> dict:
    """翻訳ファイルの外に日本語が残るファイルと、その行数。データと文献は、そのままが正しいので見ない。"""
    found = {}
    for p in sorted(dest.rglob('*')):
        rel = p.relative_to(dest)
        if not p.is_file() or p.suffix not in TEXT_SUFFIXES or rel.parts[0] in ('analysis', 'data') \
                or rel.as_posix() == 'README.md':
            continue
        n = sum(1 for line in p.read_text(encoding='utf-8', errors='replace').split('\n') if has_japanese(line))
        if n:
            found[rel.as_posix()] = n
    return found


def title(cfg, value: str) -> str:
    """README の表題。日本語なら analysis/replication/package.en.json の訳を使う。"""
    if not has_japanese(value):
        return value
    path = Path(cfg.root) / 'analysis' / SUBDIR / 'package.en.json'
    table = read_table(path)
    if value not in table['prose']:
        table['prose'][value] = ''
        _write_table(path, table)
    return table['prose'][value].strip() or value


def _user_values(path: Path) -> dict | None:
    try:
        got = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    return {k: v for k, v in got.items() if not k.startswith('_')}


def _link(src: Path, dst: Path) -> None:
    try:
        dst.symlink_to(src, src.is_dir())
    except OSError:              # Windows で権限がないとき
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)


class _Trial:
    """パッケージの複製を一時フォルダで実行する。プロジェクトで見えるのは、環境（ENVIRONMENT）だけ。"""

    def __init__(self, cfg, package: Path, say, plain: bool):
        self.cfg, self.say = cfg, say
        self.folder = Path(tempfile.mkdtemp(prefix='octavo-verify-'))
        self.root = self.folder / 'package'
        shutil.copytree(package, self.root)
        for name in ENVIRONMENT:
            src = Path(cfg.root) / name
            if src.exists() and not (self.root / name).exists():
                _link(src, self.root / name)
        self.raw = dataset.data_dir(cfg) / 'raw'
        self.raw_linked = False
        self.manual = [u for u in anamod.units(cfg) if u.src.is_file() and u.manual]
        self.env = dict(anamod._env(cfg))
        for name in ('OCTAVO_ROOT', 'OCTAVO_VALUES_DIR', 'OCTAVO_FIGURE_DIR', 'OCTAVO_TABLE_DIR'):
            self.env.pop(name, None)
        if not plain:
            self.env['OCTAVO_ROOT'] = str(self.root)
            for name, key in (('OCTAVO_VALUES_DIR', 'values_dir'), ('OCTAVO_FIGURE_DIR', 'figure_dir'),
                              ('OCTAVO_TABLE_DIR', 'table_dir')):
                self.env[name] = str(self.root / cfg.rel(Path(cfg[key])))

    def close(self) -> None:
        shutil.rmtree(self.folder, ignore_errors=True)

    def _render(self, rel: str):
        cmd = [anamod.quarto_exe(), 'render', str(self.root / rel)]
        if self.cfg['analysis_to']:
            cmd += ['--to', str(self.cfg['analysis_to'])]
        cmd += [str(a) for a in (self.cfg['analysis_args'] or ())]
        return subprocess.run(cmd, cwd=str(self.root), env=self.env, capture_output=True, text=True,
                              encoding='utf-8', errors='replace')

    def run(self, u, before=None) -> bool:
        """1本実行する。data/raw を入れていないパッケージで失敗したら、それを足してもう1度試し、
        原データが要るだけなのか、ほかにも足りないのかを見分ける。"""
        rel = anamod.key(self.cfg, u)
        if not (self.root / rel).is_file():
            self.say(f'{tag("verify")} ' + t('{unit} is not in the package: only analysis/ goes in', unit=rel))
            return False
        if before:
            before()
        r = self._render(rel)
        spare = self.root / 'data' / 'raw'
        if r.returncode != 0 and not self.raw_linked and not spare.exists() and self.raw.is_dir() \
                and any(self.raw.iterdir()):
            spare.parent.mkdir(parents=True, exist_ok=True)
            _link(self.raw.resolve(), spare)
            self.raw_linked = True
            if before:
                before()
            r = self._render(rel)
            if r.returncode == 0:
                self.say(f'{tag("verify")}{tag("note")} ' + t(
                    '{unit} needs data/raw, which is not in the package. Readers must get it themselves '
                    '(--with-raw-data adds it, once you have checked it may be shared)', unit=rel))
        if r.returncode != 0:
            tail = '\n'.join(((r.stdout or '') + (r.stderr or '')).strip().split('\n')[-15:])
            self.say(f'{tag("verify")} ' + t('failed: {unit}', unit=rel) + '\n' + tail)
            return False
        return True


def verify(cfg, package: Path, say) -> bool:
    """パッケージを一時フォルダで実行し、数値を記録と比べる。プロジェクトには何も書かない。"""
    if not shutil.which('quarto'):
        say(f'{tag("verify")} ' + t('no quarto, so nothing was checked'))
        return False
    us = [u for u in anamod.units(cfg) if u.src.is_file()]
    trial = _Trial(cfg, package, say, plain=False)
    ok, checked = True, 0
    try:
        values = trial.root / cfg.rel(Path(cfg['values_dir']))
        for u in us:
            rel = anamod.key(cfg, u)
            if u.manual:
                say(f'{tag("verify")} ' + t('{unit}: not run (manual)', unit=rel))
                continue
            made = values / f'{u.src.stem}.json'
            if not trial.run(u, before=lambda: made.unlink(missing_ok=True)):
                ok = False
                continue
            checked += 1
            want = _user_values(Path(cfg['values_dir']) / f'{u.src.stem}.json')
            got = _user_values(made)
            if want is None and got is None:
                say(f'{tag("verify")} ' + t('{unit}: ran; it records no values', unit=rel))
                continue
            want, got = want or {}, got or {}
            differ = sorted(k for k in set(want) | set(got) if want.get(k) != got.get(k))
            if differ:
                ok = False
                say(f'{tag("verify")} ' + t('{unit}: {n} of {total} values differ: {names}', unit=rel,
                                            n=len(differ), total=len(set(want) | set(got)),
                                            names=', '.join(differ[:12])))
            else:
                say(f'{tag("verify")} ' + t('{unit}: all {n} values match', unit=rel, n=len(want)))
    finally:
        trial.close()
    return _summary(us, checked, ok, say)


def _summary(us: list, checked: int, ok: bool, say) -> bool:
    skipped = sum(1 for u in us if u.manual)
    say(f'{tag("verify")} ' + t('checked {n} of {total} analyses; {m} not run (manual)',
                                n=checked, total=len(us), m=skipped))
    if not checked:
        say(f'{tag("verify")} ' + t('nothing was checked, so this says nothing about the package'))
        return False
    return ok


def verify_rewritten(cfg, package: Path, say) -> bool:
    """--standalone の書き換えの後を実行する。数値は書き出さないので、動くことと図表ができることを見る。"""
    if not shutil.which('quarto'):
        return False
    us = [u for u in anamod.units(cfg) if u.src.is_file()]
    trial = _Trial(cfg, package, say, plain=True)
    ok, checked = True, 0
    try:
        dirs = [trial.root / cfg.rel(Path(cfg[k])) for k in ('figure_dir', 'table_dir')]
        had = {p.stem for d in dirs if d.is_dir() for p in d.iterdir() if p.is_file()}
        fresh = not trial.manual        # 手動の分析の図表は作り直せないので、あるときは消さない
        if fresh:
            for d in dirs:
                for p in list(d.iterdir()) if d.is_dir() else ():
                    if p.is_file():
                        p.unlink()
        for u in us:
            if u.manual:
                continue
            if trial.run(u):
                checked += 1
                say(f'{tag("verify")} ' + t('{unit}: the rewritten .qmd runs', unit=anamod.key(cfg, u)))
            else:
                ok = False
        if fresh and ok:
            made = {p.stem for d in dirs if d.is_dir() for p in d.iterdir() if p.is_file()}
            gone = sorted(had - made)
            if gone:
                say(f'{tag("verify")}{tag("note")} ' + t(
                    'not made again by the rewritten analyses: {names} (left over from an older run, or a '
                    'part of the package that does not run)', names=', '.join(gone[:12])))
    finally:
        trial.close()
    return ok and checked > 0
