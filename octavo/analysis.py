# -*- coding: utf-8 -*-
"""分析（Quarto の .qmd）を、必要なときだけ実行する。

原稿は .md、分析は .qmd。.qmd は「論文に出す数値・図・表」を
**プロジェクトの決まった場所に書き出す**（octavo.R の ov_value / ov_figure /
ov_table がやる）:

    assets/values/<原稿名>.json    本文の {{…}} に入る数値
    figures/<名前>.pdf/.png  図
    tables/<名前>.tex/.typ/.md   表の中身（本文の `: 表題 {#tbl-<名前>}` に差し込む）

octavo build は変換の前に .qmd の更新時刻を見て、**古ければ実行する**。
判定の記録は `assets/values/.analysis-stamp.json`。データ（.csv 等）も見たいなら
config の `analysis_deps` か、`analysis` の要素を辞書にして `deps` を書く。

    'analysis': ['analysis/*.qmd'],
    'analysis': [{'src': 'analysis/main.qmd', 'deps': ['data/*.csv']}],

時間のかかるもの（データの整形など）は別の .qmd に分け、`'manual': True` を
付ける。octavo build（とプレビュー）はそれを実行せず、古ければ知らせるだけに
する。実行するのは octavo analysis run（全部）か octavo analysis run <その .qmd>。

    'analysis': [{'src': 'analysis/01-clean.qmd', 'manual': True},
                 {'src': 'analysis/02-model.qmd', 'deps': ['data/derived/*']}],

Quarto が入っていない環境では**警告して素通りする**（変換そのものは
pandoc だけでできるため）。入っているのに render が失敗したときは、
古い数値のまま論文を組まないよう、呼び出し側が変換を止める。
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from . import values as valmod
from .i18n import language, t, tag

STAMP_NAME = '.analysis-stamp.json'


@dataclass
class Unit:
    """1本の .qmd と、その入力（更新を見張る相手）。"""
    src: Path
    deps: tuple = ()
    manual: bool = False          # 自動では実行しない（明示されたときだけ）

    def newest(self) -> float:
        ts = [self.src.stat().st_mtime] if self.src.exists() else [0.0]
        ts += [p.stat().st_mtime for p in self.deps if p.exists()]
        return max(ts)


def _expand(root: Path, pats) -> list:
    """グロブを開く。`.` で始まるものは拾わない。

    `data/*` のような見張りに `.DS_Store` や `.Rhistory`、エディタの一時
    ファイルが混ざると、触っていない .qmd が「古い」と判定されてしまう。
    """
    out: list = []
    for pat in pats or ():
        s = str(pat)
        if any(c in s for c in '*?['):
            out += [p.resolve() for p in sorted(root.glob(s))
                    if not p.name.startswith('.')]
        else:
            out.append((root / s).resolve())
    return out


def qmd_settings(src: Path) -> dict:
    """.qmd の冒頭の `octavo:` の下に書いた設定（manual / deps）。

        ---
        title: "原データを取る"
        octavo:
          manual: true
          deps: ["data/raw/*"]
        ---

    Quarto の設定と混ざらないよう `octavo:` の下にまとめる。読むのはこの2つだけ。
    """
    try:
        text = src.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return {}
    m = re.match(r'\A---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)', text.lstrip('\ufeff'), re.S)
    if not m:
        return {}
    out: dict = {}
    inside, key = False, None
    for raw in m.group(1).split('\n'):
        if not raw.strip() or raw.lstrip().startswith('#'):
            continue
        if not raw[:1].isspace():
            inside = bool(re.match(r'octavo\s*:\s*$', raw))
            key = None
            continue
        if not inside:
            continue
        item = re.match(r'\s*-\s+(.*)$', raw)
        if item and key == 'deps':
            out.setdefault('deps', []).append(item.group(1).strip().strip('"\''))
            continue
        kv = re.match(r'\s+(manual|deps)\s*:\s*(.*)$', raw)
        if not kv:
            continue
        key, val = kv.group(1), kv.group(2).strip()
        if key == 'manual':
            out['manual'] = val.lower() in ('true', 'yes')
        elif val.startswith('['):
            out['deps'] = [x.strip().strip('"\'') for x in val.strip('[]').split(',') if x.strip()]
        elif val:
            out['deps'] = [val.strip('"\'')]
    return out


def units(cfg) -> list:
    """config の `analysis` を Unit に開く。

    同じ .qmd を2つの項目が拾ったら（`analysis/*.qmd` と、その1本を個別に書いたもの）、
    1本として扱い、グロブでない項目の設定を使う。グロブで拾った .qmd は、冒頭の
    `octavo:` の設定（qmd_settings）で手動実行や見張る入力を足せる。
    """
    common = _expand(cfg.root, cfg['analysis_deps'])
    found: dict = {}            # パス -> (Unit, 個別に書いた項目か)
    for item in cfg['analysis'] or ():
        manual = False
        if isinstance(item, str):
            src_pat, deps = item, []
        elif isinstance(item, dict) and 'src' in item \
                and isinstance(item.get('manual', False), bool):
            src_pat, deps = item['src'], item.get('deps') or []
            manual = item.get('manual', False)
        else:
            sys.exit(t("analysis takes either 'analysis.qmd' or "
                       "{{'src': '…', 'deps': ['data/*.csv'], 'manual': True}} (got {got})",
                       got=repr(item)))
        explicit = not any(c in src_pat for c in '*?[')
        extra = _expand(cfg.root, deps)
        for p in _expand(cfg.root, [src_pat]):
            if p in found and (found[p][1] or not explicit):
                continue
            m, d = manual, list(extra)
            if not explicit:
                own = qmd_settings(p)
                m = own.get('manual', m)
                d += _expand(cfg.root, own.get('deps', []))
            found[p] = (Unit(src=p, deps=tuple(dict.fromkeys(common + d)), manual=m), explicit)
    return [u for u, _ in found.values()]


def key(cfg, u: Unit) -> str:
    try:
        return u.src.relative_to(cfg.root).as_posix()
    except ValueError:
        return u.src.as_posix()


# ---------------------------------------------------------------- 刻印

def stamp_path(cfg) -> Path:
    return Path(cfg['values_dir']) / STAMP_NAME


def read_stamp(cfg) -> dict:
    try:
        d = json.loads(stamp_path(cfg).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    return d if isinstance(d, dict) else {}


def write_stamp(cfg, data: dict) -> None:
    p = stamp_path(cfg)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n',
                 encoding='utf-8')


def is_stale(cfg, u: Unit, stamp: dict) -> bool:
    """前に実行したときより .qmd（か依存ファイル）が新しいか。"""
    rec = stamp.get(key(cfg, u))
    if not isinstance(rec, dict):
        return True
    try:
        return u.newest() > float(rec.get('newest', 0)) + 1e-6
    except (TypeError, ValueError):
        return True


# ---------------------------------------------------------------- 実行

def quarto_version() -> str:
    if not shutil.which('quarto'):
        return ''
    try:
        r = subprocess.run([quarto_exe(), '--version'], capture_output=True,
                           text=True, encoding='utf-8', errors='replace',
                           timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return ''
    return (r.stdout or '').strip().split('\n')[0] if r.returncode == 0 else ''


def venv_python(venv: Path) -> Path:
    """venv の中の python（Windows では Scripts\\python.exe）。"""
    return venv / 'Scripts' / 'python.exe' if os.name == 'nt' else venv / 'bin' / 'python'


def quarto_exe() -> str:
    """Quarto の実体。Windows では quarto.cmd のこともあり、名前だけでは起動できない。"""
    return shutil.which('quarto') or 'quarto'


def _env(cfg) -> dict:
    """.qmd 側（octavo.R）が置き場所を迷わないように渡す。

    プロジェクトに `.venv` があれば、Python の .qmd はその Python で動かす
    （QUARTO_PYTHON）。VS Code から実行すると venv を activate する場面がないので。
    """
    env = {**os.environ,
           'OCTAVO_ROOT': str(cfg.root),
           'OCTAVO_VALUES_DIR': str(cfg['values_dir']),
           'OCTAVO_FIGURE_DIR': str(cfg['figure_dir']),
           'OCTAVO_TABLE_DIR': str(cfg['table_dir'])}
    py = venv_python(Path(cfg.root) / '.venv')
    if py.exists() and not env.get('QUARTO_PYTHON'):
        env['QUARTO_PYTHON'] = str(py)
    return env


def render(cfg, u: Unit, report: list) -> bool:
    cmd = [quarto_exe(), 'render', str(u.src)]
    if cfg['analysis_to']:
        cmd += ['--to', str(cfg['analysis_to'])]
    cmd += [str(a) for a in (cfg['analysis_args'] or ())]

    Path(cfg['values_dir']).mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    try:
        r = subprocess.run(cmd, cwd=str(cfg.root), env=_env(cfg),
                           capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
    except OSError as e:
        report.append(f'{tag("analysis")} ' + t('cannot run it: {why}', why=e))
        return False
    took = time.time() - t0
    if r.returncode != 0:
        tail = '\n'.join(
            ((r.stdout or '') + (r.stderr or '')).strip().split('\n')[-25:])
        report.append(f'{tag("analysis")} ' + t('failed: {unit}', unit=key(cfg, u))
                      + '\n' + tail)
        return False
    report.append(f'{tag("analysis")} ' + t('ran {unit} ({secs}s)',
                                             unit=key(cfg, u), secs=f'{took:.1f}'))
    return True


def pick(cfg, names) -> list:
    """名前（`analysis/01-clean.qmd`、`01-clean.qmd`、`01-clean`）から Unit を選ぶ。"""
    us = units(cfg)
    out = []
    for n in names:
        want = str(n).replace('\\', '/')
        hit = [u for u in us if want in (key(cfg, u), u.src.name, u.src.stem)
               or Path(want).resolve() == u.src]
        if not hit:
            sys.exit(t('no registered analysis called {name}', name=n) + '\n  '
                     + t('registered: {names}',
                         names=', '.join(key(cfg, u) for u in us) or t('(none)')))
        out += [u for u in hit if u not in out]
    return out


def run(cfg, force: bool = False, report: list | None = None,
        names=None, auto: bool = False, on_start=None) -> tuple:
    """古い .qmd を実行する。(実行した本数, 失敗がなかったか) を返す。

    names  実行する .qmd を名指しする。**名指ししたものは古くなくても実行する**
           （わざわざ選んだのだから）。
    auto   octavo build から呼ぶとき。manual の .qmd は実行せず、古ければ言うだけ。
    on_start  1本実行する直前に key を渡して呼ぶ（長い分析の進み具合を見せる）。
    """
    report = report if report is not None else []
    us = units(cfg)
    if not us:
        return 0, True
    chosen = pick(cfg, names) if names else None
    if chosen is not None:
        force = True

    for u in us:
        if not u.src.is_file():
            report.append(f'{tag("analysis")}{tag("warning")} '
                          + t('not found: {unit}', unit=key(cfg, u)))
    us = [u for u in us if u.src.is_file()]
    if not us:
        return 0, True

    # 登録から外れた .qmd の記録は落としておく（消した分析が刻印に残り続ける）
    stamp = {k: v for k, v in read_stamp(cfg).items()
             if k in {key(cfg, u) for u in us}}
    if auto:
        for u in us:
            if u.manual and is_stale(cfg, u, stamp):
                report.append(f'{tag("analysis")}{tag("note")} ' + t(
                    '{unit} is stale but runs only when asked (manual) — '
                    'octavo analysis run {unit}', unit=key(cfg, u)))
        us = [u for u in us if not u.manual]
        if not us:
            return 0, True
    if chosen is not None:
        us = [u for u in us if u in chosen]
    todo = list(us) if force else [u for u in us if is_stale(cfg, u, stamp)]
    if not todo:
        report.append(f'{tag("analysis")} ' + t('{n|the one is|all # are} up to date (not running {n|it|them})',
                                                 n=len(us)))
        return 0, True

    if not shutil.which('quarto'):
        sep = '、' if language() == 'ja' else ', '
        report.append(f'{tag("analysis")}{tag("warning")} ' + t(
            'no quarto, so {units} cannot be run. The numbers in {dir}/ may be '
            'stale (octavo doctor says how to install it)',
            units=sep.join(key(cfg, u) for u in todo),
            dir=Path(cfg['values_dir']).name))
        return 0, True

    # **並び順に、その時点で判定し直しながら**実行する。分析を分けたとき、
    # 前の .qmd が data/derived/ を書き換えて後ろの .qmd を古くすることが
    # ある。todo を先に固定すると、そういう .qmd が1回分あとに取り残される。
    valmod.snapshot(cfg)          # 実行する前の値を「前回」として残す
    ok, ran = True, 0
    for u in us:
        if not (force or is_stale(cfg, u, stamp)):
            continue
        ran += 1
        if on_start:
            on_start(key(cfg, u))
        if render(cfg, u, report):
            stamp[key(cfg, u)] = {'newest': u.newest(), 'rendered_at': time.time()}
            write_stamp(cfg, stamp)
        else:
            ok = False
    return ran, ok


def orphan_results(cfg) -> list:
    """登録された .qmd に対応しない assets/values/*.json。

    .qmd を消した・名前を変えたとき、前に書いた値のファイルは残る。本文が
    まだその名前を参照していると、**古い数値が黙って入り続ける。**分析を
    複数に分けるほど起きやすいので、検査するコマンドで知らせる。

    手引き「R 以外で書く」のように手で置いた .json も引っかかるので、消せとは言わない
    （呼び出し側が「.qmd を消したなら消す」と添える）。
    """
    if not cfg['analysis']:
        return []
    stems = {u.src.stem for u in units(cfg)}
    return [p for p in valmod.files(cfg) if p.stem not in stems]


def status(cfg) -> list:
    """[(Unit, ある?, 古い?)] を返す（octavo analysis の表示用）。"""
    stamp = read_stamp(cfg)
    out = []
    for u in units(cfg):
        exists = u.src.is_file()
        out.append((u, exists, is_stale(cfg, u, stamp) if exists else True))
    return out


def status_json(cfg) -> dict:
    """octavo analysis --json（VS Code のサイドバーとプレビューが読む）。"""
    stamp = read_stamp(cfg)
    rows = []
    for u, exists, stale in status(cfg):
        rec = stamp.get(key(cfg, u))
        rows.append({'key': key(cfg, u), 'src': str(u.src), 'exists': exists,
                     'stale': stale, 'manual': u.manual, 'deps': len(u.deps),
                     'rendered_at': rec.get('rendered_at') if isinstance(rec, dict) else None})
    return {'quarto': quarto_version() or None, 'units': rows,
            'stale': sum(1 for r in rows if r['stale'])}


def watch_paths(cfg) -> list:
    """octavo watch が見張るべきファイル（.qmd と、その依存）。"""
    seen: list = []
    for u in units(cfg):
        for p in (u.src,) + tuple(u.deps):
            if p not in seen:
                seen.append(p)
    return seen
