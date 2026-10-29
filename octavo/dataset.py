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


def scan(cfg) -> dict:
    """data/ の中身を {相対パス: {sha256, bytes}} にする。

    `.` で始まるものと HASHES.json 自身は数えない。
    """
    root = data_dir(cfg)
    if not root.is_dir():
        return {}
    out: dict = {}
    for p in sorted(root.rglob('*')):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if p.name == MANIFEST_NAME or any(part.startswith('.')
                                          for part in rel.split('/')):
            continue
        out[rel] = {'sha256': sha256(p), 'bytes': p.stat().st_size}
    return out


def read(cfg) -> tuple:
    """(記録した日時, {相対パス: {...}}) を返す。なければ ('', {})。"""
    try:
        d = json.loads(manifest_path(cfg).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return '', {}
    if not isinstance(d, dict) or not isinstance(d.get('files'), dict):
        return '', {}
    return str(d.get('_recorded', '')), d['files']


def write(cfg) -> tuple:
    """いまの中身を記録して (件数, パス) を返す。"""
    files = scan(cfg)
    p = manifest_path(cfg)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(
        {'_recorded': datetime.now().isoformat(timespec='seconds'),
         '_note': NOTE['ja' if cfg['lang'] == 'ja' else 'en'],
         'files': files}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    return len(files), p


def compare(cfg) -> list:
    """記録といまの中身の食い違い。記録がなければ空を返す（未記録は別に扱う）。"""
    _, recorded = read(cfg)
    if not recorded:
        return []
    now = scan(cfg)
    out: list = []
    for rel in sorted(recorded):
        if rel not in now:
            out.append(Drift('missing', rel))
        elif now[rel]['sha256'] != recorded[rel].get('sha256'):
            out.append(Drift('changed', rel,
                             f"{recorded[rel].get('bytes', 0):,} -> "
                             f"{now[rel]['bytes']:,} bytes"))
    for rel in sorted(set(now) - set(recorded)):
        out.append(Drift('untracked', rel))
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
    if not recorded:
        print(t('Nothing recorded yet. Make it with: octavo data hash'))
        n = len(scan(cfg))
        print('  ' + t('files under data/ right now: {n}', n=n))
        return 0

    drift = compare(cfg)
    print(t('Recorded {when}: {n} {n|file|files}', when=recorded_at, n=len(recorded)))
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
