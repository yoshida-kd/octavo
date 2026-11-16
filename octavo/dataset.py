# -*- coding: utf-8 -*-
"""データのハッシュ値（`data/HASHES.json`）。

    octavo data hash      いまの data/ の中身を記録する
    octavo data status    記録と食い違っていないか見る

`_session`（分析を実行した環境）はソフトウェアの版しか残さない。再現性の
もう半分は「**同じデータで実行したか**」で、それを保証するのがここ。

`data/raw/` と `data/derived/` は `.gitignore` で git に入らない。つまり
リポジトリだけ渡されても中身は再現できない。`data/HASHES.json` は
**git に入る**ので、これが「そのとき使ったデータはこれだった」という
唯一の記録になる（`data/raw/README.md` の出所と対で意味を持つ）。

判定は `compare()` 1箇所。`octavo data status` も `octavo check` もそこを呼ぶ。
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from .i18n import t

MANIFEST_NAME = 'HASHES.json'
CHUNK = 1 << 20


@dataclass
class Drift:
    kind: str          # 'changed' | 'missing' | 'untracked'
    path: str
    detail: str = ''

    def label(self) -> str:
        return {'changed': t('contents differ'),
                'missing': t('recorded but gone'),
                'untracked': t('not recorded')}.get(self.kind, self.kind)


# HASHES.json に書く説明（プロジェクトのファイルなので、画面の言語でなく cfg['lang'] に従う）
NOTE = {
    'ja': ('octavo data hash が作る。data/ は git に入らないので、'
           'これが「そのとき使ったデータ」の唯一の記録になる。'),
    'en': ('Written by octavo data hash. data/ is not in git, so this is the only '
           'record of the data that was used.'),
}


def data_dir(cfg) -> Path:
    """`data/`。config は data/raw と data/derived しか知らないので、
    figure_dir 等と同じ並びで root 直下の `data` を見る。"""
    return cfg.root / 'data'


def manifest_path(cfg) -> Path:
    return data_dir(cfg) / MANIFEST_NAME


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        while True:
            b = f.read(CHUNK)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


# ---------------------------------------------------------------- 読み直さないための控え

def cache_path(cfg) -> Path:
    """ハッシュ値の控え（`~/.cache/octavo/hashes/`。消してもよい）。

    大きさと更新時刻が前に読んだときと同じファイルは、読み直さずに済ませるためのもの。
    マシンごとの時刻が入るので、プロジェクト（git）には置かない。
    """
    base = os.environ.get('XDG_CACHE_HOME') or (Path.home() / '.cache')
    name = hashlib.sha256(str(Path(cfg.root).resolve()).encode('utf-8')).hexdigest()[:16]
    return Path(base) / 'octavo' / 'hashes' / f'{name}.json'


class Cache:
    """{絶対パス: [大きさ, 更新時刻(ns), sha256]}。fast のときだけ信じ、いつも書き足す。"""

    def __init__(self, cfg, fast: bool):
        self.path, self.fast, self.dirty = cache_path(cfg), fast, False
        try:
            d = json.loads(self.path.read_text(encoding='utf-8'))
            self.data = d if isinstance(d, dict) else {}
        except (OSError, ValueError):
            self.data = {}
        self.seen: dict = {}

    def entry(self, p: Path) -> dict:
        st = p.stat()
        k = str(p)
        old = self.data.get(k)
        if self.fast and isinstance(old, list) and len(old) == 3 \
                and old[0] == st.st_size and old[1] == st.st_mtime_ns:
            digest = old[2]
        else:
            digest = sha256(p)
        self.seen[k] = [st.st_size, st.st_mtime_ns, digest]
        if self.seen[k] != old:
            self.dirty = True
        return {'sha256': digest, 'bytes': st.st_size}

    def save(self) -> None:
        if not (self.dirty or set(self.seen) != set(self.data)):
            return
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.seen), encoding='utf-8')
        except OSError:
            pass                      # 控えが書けなくても、判定は変わらない


# ---------------------------------------------------------------- 中身を読む

def counted(cfg, rel: str) -> bool:
    """この相対パス（data/ から）を記録に入れるか。

    `.` で始まるものと HASHES.json 自身は数えない。`data_hash_derived: False` なら、
    分析が作り直せる data/derived/ も数えない。
    """
    parts = rel.split('/')
    if parts[-1] == MANIFEST_NAME and len(parts) == 1:
        return False
    if any(part.startswith('.') for part in parts):
        return False
    return cfg['data_hash_derived'] or parts[0] != 'derived'


def scan(cfg, fast: bool = False, cache: Cache | None = None) -> dict:
    """data/ の中身を {相対パス: {sha256, bytes}} にする。

    fast: 大きさと更新時刻が前に読んだときと同じファイルは読み直さない（octavo check 用。
    数 GB のデータを毎回読まないため）。octavo data hash / status は全部読む。
    """
    root = data_dir(cfg)
    if not root.is_dir():
        return {}
    own = cache or Cache(cfg, fast)
    out: dict = {}
    for p in sorted(root.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if counted(cfg, rel):
            out[rel] = own.entry(p.resolve())
    if cache is None:
        own.save()
    return out


def input_files(cfg) -> dict:
    """{入力の名前: {相対パス: Path}}。**deps に書いた入力のファイルだけ**。

    入力のフォルダー全体は読まない（共有ドライブのデータ置き場は大きく、ほとんどは
    このプロジェクトに関係がない）。
    """
    from . import analysis as anamod
    from . import inputs as inputmod
    known = inputmod.declared(cfg)
    out: dict = {name: {} for name in known}
    if not known:
        return out
    for u in anamod.units(cfg):
        for p in u.deps:
            for name, inp in known.items():
                try:
                    rel = Path(p).relative_to(inp.path).as_posix()
                except ValueError:
                    continue
                out[name][rel] = Path(p)
                break
    return out


def scan_inputs(cfg, fast: bool = False, cache: Cache | None = None) -> dict:
    """{名前: {'path': 設定に書いた場所, 'commit': …, 'files': {相対パス: {sha256, bytes}}}}。"""
    from . import inputs as inputmod
    known = inputmod.declared(cfg)
    own = cache or Cache(cfg, fast)
    out: dict = {}
    for name, files in input_files(cfg).items():
        row = {'path': known[name].declared, **inputmod.commit(known[name].path),
               'files': {rel: own.entry(p) for rel, p in sorted(files.items())
                         if p.is_file()}}
        out[name] = row
    if cache is None:
        own.save()
    return out


def _manifest(cfg) -> dict:
    try:
        d = json.loads(manifest_path(cfg).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    return d if isinstance(d, dict) else {}


def read(cfg) -> tuple:
    """(記録した日時, {相対パス: {...}}) を返す。なければ ('', {})。"""
    d = _manifest(cfg)
    if not isinstance(d.get('files'), dict):
        return '', {}
    return str(d.get('_recorded', '')), d['files']


def read_inputs(cfg) -> dict:
    """記録にある入力（{名前: {'path', 'commit', 'files'}}）。"""
    got = _manifest(cfg).get('inputs')
    if not isinstance(got, dict):
        return {}
    return {k: v for k, v in got.items()
            if isinstance(v, dict) and isinstance(v.get('files'), dict)}


def write(cfg) -> tuple:
    """いまの中身を記録して (件数, パス) を返す。入力のファイルも数に入る。"""
    cache = Cache(cfg, False)
    files = scan(cfg, cache=cache)
    inputs = scan_inputs(cfg, cache=cache)
    cache.save()
    p = manifest_path(cfg)
    p.parent.mkdir(parents=True, exist_ok=True)
    body = {'_recorded': datetime.now().isoformat(timespec='seconds'),
            '_note': NOTE['ja' if cfg['lang'] == 'ja' else 'en'],
            'files': files}
    if inputs:
        body['inputs'] = inputs
    p.write_text(json.dumps(body, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return len(files) + sum(len(v['files']) for v in inputs.values()), p


def recorded_anything(cfg) -> bool:
    return bool(read(cfg)[1] or read_inputs(cfg))


def compare(cfg, fast: bool = False) -> list:
    """記録といまの中身の食い違い。記録がなければ空を返す（未記録は別に扱う）。

    入力のファイルは `名前:相対パス` で並ぶ。
    """
    if not recorded_anything(cfg):
        return []
    _, recorded = read(cfg)
    recorded = {rel: v for rel, v in recorded.items() if counted(cfg, rel)}
    cache = Cache(cfg, fast)
    now = scan(cfg, cache=cache)
    now_in = scan_inputs(cfg, cache=cache)
    cache.save()
    out: list = []

    def diff(was: dict, got: dict, prefix: str = '') -> None:
        for rel in sorted(was):
            if rel not in got:
                out.append(Drift('missing', prefix + rel))
            elif got[rel]['sha256'] != was[rel].get('sha256'):
                out.append(Drift('changed', prefix + rel,
                                 f"{was[rel].get('bytes', 0):,} -> "
                                 f"{got[rel]['bytes']:,} bytes"))
        for rel in sorted(set(got) - set(was)):
            out.append(Drift('untracked', prefix + rel))

    diff(recorded, now)
    was_in = read_inputs(cfg)
    # 宣言から外した入力の記録は比べない（もう使っていない）
    for name in sorted(now_in):
        diff(was_in.get(name, {}).get('files', {}), now_in[name]['files'], f'{name}:')
    return out


# ---------------------------------------------------------------- 表示

def track(cfg, files: list) -> int:
    """手で写し取ったデータなど、data/raw・data/derived の中のファイルを git に入れる。

    プロジェクトの .gitignore は data/raw/* と data/derived/* を除外している。ファイルを
    指して `!<パス>` を足す（深いところは、親のフォルダも除外から外す）。
    """
    import subprocess
    root = Path(cfg.root)
    gi = root / '.gitignore'
    if not files:
        print(t('usage: octavo data track data/raw/<file> …'), file=sys.stderr)
        return 2
    lines = gi.read_text(encoding='utf-8').split('\n') if gi.is_file() else []
    added, failed = [], 0
    for f in files:
        p = Path(f)
        full = (p if p.is_absolute() else Path.cwd() / p).resolve()
        if not full.is_file():
            full = (root / f).resolve()
        try:
            rel = full.relative_to(root.resolve()).as_posix()
        except ValueError:
            print(t('{path} is not inside the project', path=f), file=sys.stderr)
            failed += 1
            continue
        parts = rel.split('/')
        if not (len(parts) >= 3 and parts[0] == 'data' and parts[1] in ('raw', 'derived')):
            print(t('{path} is not under data/raw or data/derived (only those are ignored)',
                    path=rel), file=sys.stderr)
            failed += 1
            continue
        if not full.is_file():
            print(t('no such file: {path}', path=rel), file=sys.stderr)
            failed += 1
            continue
        want = []
        for depth in range(3, len(parts)):
            d = '/'.join(parts[:depth])
            want += [f'!{d}/', f'{d}/*']        # 親のフォルダを除外から外し、中は改めて除外
        want.append(f'!{rel}')
        for w in want:
            if w not in lines:
                # 除外の行（data/raw/* など）の後ろ、ほかの「!」の並びの終わりに入れる
                at = max([i for i, l in enumerate(lines) if l.startswith(('data/raw', 'data/derived', '!data/'))]
                         or [len(lines) - 1]) + 1
                lines.insert(at, w)
                added.append(w)
    if added:
        gi.write_text('\n'.join(lines).rstrip('\n') + '\n', encoding='utf-8')
        print(t('added to .gitignore:') + '\n' + '\n'.join(f'  {w}' for w in added))
    else:
        print(t('.gitignore already lets these through'))
    if shutil.which('git') and (root / '.git').exists():
        for f in files:
            full = (Path(f) if Path(f).is_absolute() else root / f)
            r = subprocess.run(['git', 'check-ignore', '-q', str(full)], cwd=str(root))
            if r.returncode == 0:
                print(t('{path} is still ignored — check .gitignore', path=f), file=sys.stderr)
                failed += 1
    return 1 if failed else 0


def run(cfg, action: str = 'status', files: list | None = None) -> int:
    if action == 'track':
        return track(cfg, files or [])
    if action == 'hash':
        n, p = write(cfg)
        print(t('Recorded fingerprints for {n} {n|file|files} in {path}', n=n, path=p))
        print('  ' + t('Keep this file in git — data/ itself is not, so this is '
                       'the only record there will be'))
        return 0

    recorded_at, recorded = read(cfg)
    if not recorded_anything(cfg):
        print(t('Nothing recorded yet. Make it with: octavo data hash'))
        n = len(scan(cfg))
        print('  ' + t('files under data/ right now: {n}', n=n))
        return 0

    drift = compare(cfg)
    was_in = read_inputs(cfg)
    print(t('Recorded {when}: {n} {n|file|files}', when=recorded_at,
            n=len(recorded) + sum(len(v['files']) for v in was_in.values())))
    for name, row in sorted(was_in.items()):
        print('  ' + t('input {name}: {n} {n|file|files}', name=name, n=len(row['files']))
              + (' · ' + t('commit {commit}', commit=str(row['commit'])[:12])
                 if row.get('commit') else '')
              + ('  ' + t('(with uncommitted changes)') if row.get('modified') else ''))
    if not drift:
        print(t('No drift. This is the same data as when it was recorded'))
        return 0
    print('\n' + t('{n} {n|difference|differences}:', n=len(drift)))
    for d in drift:
        print(f'  [{d.label()}] {d.path}' + (f'   {d.detail}' if d.detail else ''))
    print('\n  ' + t('If you replaced the data on purpose: octavo analysis run --force, '
                     'then octavo data hash to record it again'))
    print('  ' + t('If you did not, something went wrong — the raw data has been '
                   'overwritten'))
    return 1
