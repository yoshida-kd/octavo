# -*- coding: utf-8 -*-
"""ほかのプロジェクトやフォルダーのデータを、入力として使う。

    'inputs': {'prep': '../survey-prep', 'census': '/mnt/share/census-2020'},

同じ前処理済みデータを2つ以上のプロジェクトで使うとき、データを複製したり、
`.qmd` に `../` で始まるパスを書いたりしない。使う側が**名前を付けて宣言**し、
`.qmd` は `ov_input("prep", "data/derived/panel.parquet")` で読み、`deps` には
`prep:data/derived/panel.parquet` と書く。

相手はどんなフォルダーでもよい。Octavo のプロジェクトなら、その分析が古いかも
知らせられる（知らせるだけで、相手の分析は実行しない）。

場所がマシンごとに違うときは、環境変数 `OCTAVO_INPUT_<名前>` で差し替える
（設定は書き換えない）。**入力には書かない。** 読むだけ。
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .i18n import t

# 1文字の名前は使わせない（`C:/data` のドライブ名と見分けがつかなくなる）
NAME = re.compile(r'[A-Za-z][A-Za-z0-9_-]+\Z')
PREFIX = re.compile(r'([A-Za-z][A-Za-z0-9_-]+):(?![/\\]{2})(.*)\Z', re.S)


def env_name(name: str) -> str:
    """入力の場所を差し替える環境変数の名前（`prep` -> `OCTAVO_INPUT_PREP`）。"""
    return 'OCTAVO_INPUT_' + re.sub(r'[^A-Za-z0-9]', '_', name).upper()


@dataclass
class Input:
    name: str
    declared: str            # 設定に書いてある場所（そのまま）
    path: Path               # 実際に見る場所
    from_env: bool = False   # 環境変数で差し替えられている

    @property
    def exists(self) -> bool:
        return self.path.is_dir()

    @property
    def is_project(self) -> bool:
        return (self.path / 'octavo.config.py').is_file()


def problems(cfg) -> list:
    """`inputs` の書き方のまちがい（文の並び）。"""
    raw = cfg['inputs']
    if not raw:
        return []
    if not isinstance(raw, dict):
        return [t("inputs takes names and folders: {{'prep': '../survey-prep'}}")]
    out = []
    for name, where in raw.items():
        if not isinstance(name, str) or not NAME.match(name):
            out.append(t('input name {name}: use two or more letters, digits, - or _, '
                         'starting with a letter', name=repr(name)))
        elif not isinstance(where, str) or not where.strip():
            out.append(t('input {name}: give the folder as text', name=name))
    return out


def declared(cfg) -> dict:
    """{名前: Input}。書き方のおかしいものは入れない（problems が言う）。"""
    raw = cfg['inputs']
    out: dict = {}
    if not isinstance(raw, dict):
        return out
    for name, where in raw.items():
        if not (isinstance(name, str) and NAME.match(name)
                and isinstance(where, str) and where.strip()):
            continue
        env = os.environ.get(env_name(name), '').strip()
        p = Path(os.path.expanduser(env or where))
        if not p.is_absolute():
            p = Path(cfg.root) / p
        packed = Path(cfg.root) / 'inputs' / name
        if not env and packed.is_dir():
            # プロジェクトの中に写しがあれば、それを使う。再現パッケージがこの形で、
            # 設定の `../…` がたまたまそこにあっても、パッケージの外は読まない
            p = packed
        out[name] = Input(name=name, declared=where, path=p.resolve(), from_env=bool(env))
    return out


def split(dep: str, known) -> tuple:
    """`prep:data/x.csv` を ('prep', 'data/x.csv') に。入力でなければ (None, dep)。

    `名前:` の形でも、宣言されていない名前は ('?名前', 残り) にして返す（打ち間違いを
    「ファイルが無い」でなく「そういう入力は無い」と言えるように）。
    """
    m = PREFIX.match(dep)
    if not m:
        return None, dep
    name, rest = m.group(1), m.group(2).lstrip('/')
    return (name if name in known else '?' + name), rest


def env(cfg) -> dict:
    """.qmd に渡す環境変数（ヘルパーの ov_input() が読む）。"""
    return {env_name(i.name): str(i.path) for i in declared(cfg).values()}


def commit(path: Path) -> dict:
    """相手が git のリポジトリなら、そのコミットと、手元に変更があるか。"""
    if not shutil.which('git'):
        return {}
    try:
        r = subprocess.run(['git', '-C', str(path), 'rev-parse', 'HEAD'],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=30)
        if r.returncode != 0:
            return {}
        d = subprocess.run(['git', '-C', str(path), 'status', '--porcelain',
                            '--untracked-files=no'],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return {}
    out = {'commit': r.stdout.strip()}
    if d.returncode == 0 and d.stdout.strip():
        out['modified'] = True
    return out


def upstream_stale(inp: Input) -> list:
    """相手が Octavo のプロジェクトなら、古くなっている .qmd の名前。

    知らせるためだけに読む。**相手の分析は実行しない**（実行は持ち主のプロジェクトでする）。
    相手の設定が読めなければ、何も言わない。
    """
    if not inp.is_project:
        return []
    from . import analysis as anamod
    from . import config as configmod
    try:
        other = configmod.load(str(inp.path / 'octavo.config.py'))
        return [anamod.key(other, u) for u, exists, old in anamod.status(other)
                if exists and old]
    except (SystemExit, Exception):       # noqa: BLE001 — 相手の設定の不備でこちらを止めない
        return []


def describe(cfg) -> list:
    """octavo data inputs --json の中身。"""
    rows = []
    for i in declared(cfg).values():
        row = {'name': i.name, 'declared': i.declared, 'path': str(i.path),
               'exists': i.exists, 'from_env': i.from_env, 'env': env_name(i.name),
               'project': i.is_project}
        if i.exists:
            row.update(commit(i.path))
            row['stale'] = upstream_stale(i)
        rows.append(row)
    return rows
