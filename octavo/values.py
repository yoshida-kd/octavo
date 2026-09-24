# -*- coding: utf-8 -*-
"""分析（.qmd）が出した数値を、本文の `{{名前}}` に差し込む。

    results/analysis.json   ← .qmd が ov_value() で書く
    draft.md                 標本は {{n_obs}} 人、係数は {{coef_x}} だった
    -> 出力                  標本は 1,523 人、係数は 0.342 だった

**数値の出所を1つに保つ**のがこの仕組みの目的。原稿に手で数値を書くと、
分析をやり直したときに本文だけ古いまま残る。`{{…}}` にしておけば、
octavo build のたびに results/ の最新値が入る。

置き場は `results_dir`（既定 `results/`）の `*.json`。1つの .qmd が
1つの .json を持つ（`ov_value()` が原稿名から決める）ので、複数の分析が
同じファイルを取り合わない。名前が衝突したときは警告を出して後を採る。

JSON の形は2通り。どちらでもよい。

    {"n_obs": 1523, "coef_x": 0.342}
    {"coef_x": {"value": 0.342, "fmt": ".3f", "note": "モデル2"}}

書式は `{{coef_x:.2f}}` のように本文側でも指定できる（そちらが優先）。
何も指定が無ければ **整数は桁区切り、小数は `value_float_format`**（既定
`.3f`）。R の `nrow()` は整数、`coef()` は小数として出るので、たいてい
何も書かなくても意図どおりになる。
"""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from .i18n import t, tag

# `{{name}}` / `{{ name : .3f }}`。名前は英字始まりなので、LaTeX の
# `\newcommand{\x}{{\bf y}}` のような二重波括弧には当たらない。
PLACEHOLDER = re.compile(
    r'\{\{\s*(?P<name>[A-Za-z_][\w.]*)\s*(?::(?P<spec>[^{}]*?))?\s*\}\}')


class GitError(Exception):
    pass


@dataclass
class Value:
    name: str
    value: object
    fmt: str = ''            # JSON 側が持つ既定の書式
    note: str = ''           # 覚え書き（octavo values で出す）
    source: str = ''         # どのファイルから来たか


# ---------------------------------------------------------------- 読み込み

def files(cfg) -> list:
    """results_dir の *.json。`.` で始まるもの（作業用の刻印）は除く。"""
    d = Path(cfg['results_dir'])
    if not d.is_dir():
        return []
    return sorted(p for p in d.glob('*.json') if not p.name.startswith('.'))


def load(cfg) -> tuple[dict, list]:
    """(名前 -> Value, 報告の行) を返す。例外は投げない。"""
    out: dict = {}
    report: list = []
    for p in files(cfg):
        try:
            raw = json.loads(p.read_text(encoding='utf-8'))
        except (OSError, ValueError) as e:
            report.append(f'{tag("values")}{tag("warning")} '
                          + t('cannot read {file}: {why}', file=p.name, why=e))
            continue
        if not isinstance(raw, dict):
            report.append(f'{tag("values")}{tag("warning")} '
                          + t('{file} is not a dictionary (ignored)', file=p.name))
            continue
        for name, v in raw.items():
            if name.startswith('_'):
                continue                      # _generated 等のメタ情報
            if name in out and out[name].source != p.name:
                report.append(f'{tag("values")}{tag("warning")} ' + t(
                    '{name} is in both {first} and {second} ({second} wins)',
                    name=name, first=out[name].source, second=p.name))
            out[name] = _value(name, v, p.name)
    return out, report


def _value(name: str, v, source: str) -> Value:
    if isinstance(v, dict) and 'value' in v:
        return Value(name, v.get('value'), str(v.get('fmt') or ''),
                     str(v.get('note') or ''), source)
    return Value(name, v, '', '', source)


def placeholder_files(cfg) -> list:
    """`octavo init` が置いた**仮の値**のままのファイル名を返す。

    仮の値は本物と見分けが付かない（`n_obs: 1523` は実行結果に見える）。
    分析を1度も走らせていないのに `{{…}}` が全部埋まってしまい、
    **嘘の数字が入った PDF が警告なしに組める**ので、印を入れてある。
    `octavo.R` が書き直せば `_placeholder` ごと消える。
    """
    out: list = []
    for p in files(cfg):
        try:
            raw = json.loads(p.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if isinstance(raw, dict) and raw.get('_placeholder'):
            out.append(p.name)
    return out


def session_info(cfg) -> dict:
    """{ファイル名: 分析を走らせた環境} を返す。

    `.qmd` 側が値のファイルに `_session` として残す（何で・いつ走らせたか、
    パッケージの版）。replication package を出すときに要るので、値と同じ
    ファイルに置いて一緒に commit されるようにしてある。
    """
    out: dict = {}
    for p in files(cfg):
        try:
            raw = json.loads(p.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        s = raw.get('_session') if isinstance(raw, dict) else None
        if isinstance(s, dict):
            out[p.name] = s
    return out


# ---------------------------------------------------------------- 差し込み

def render(val: Value, spec: str, cfg) -> str:
    """1つの値を文字にする。"""
    fmt = spec or val.fmt
    v = val.value
    if fmt:
        try:
            return format(v, fmt)
        except (TypeError, ValueError):
            return str(v)
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, int):
        return f'{v:,}' if cfg['value_thousands_sep'] else str(v)
    if isinstance(v, float):
        try:
            return format(v, cfg['value_float_format'])
        except (TypeError, ValueError):
            return str(v)
    if isinstance(v, (list, tuple)):
        return ', '.join(str(x) for x in v)
    if v is None:
        return ''
    return str(v)


# 素のコードブロックとインラインコード。ここの `{{…}}` は「書き方の説明」
# なので置き換えない（原稿が本ツールの使い方や分析コードを載せる場合）。
# ```{=latex} のような**素通し**ブロックは対象外 — あれは組版に渡す中身
# なので、値が入ってほしい。
PLAIN_FENCE = re.compile(
    r'^(?P<ind>[ \t]*)(?P<ticks>`{3,}|~{3,})(?P<info>[^\n]*)\n'
    r'(?P<body>.*?)'
    r'^(?P=ind)(?P=ticks)[ \t]*$',
    re.S | re.M)
INLINE_CODE = re.compile(r'(?P<ticks>`+)(?![`\n])[^\n]*?(?P=ticks)(?!`)')
_MASK = '\x00octavo-code-%d\x00'


def mask_code(text: str) -> tuple:
    """置換したくない箇所を伏せる。(伏せた本文, 元に戻すための表) を返す。"""
    kept: list = []

    def hide(m) -> str:
        kept.append(m.group(0))
        return _MASK % (len(kept) - 1)

    def fence(m):
        if m.group('info').strip().startswith('{='):
            return m.group(0)              # ```{=latex} 等は素通し。値を入れる
        return hide(m)

    text = PLAIN_FENCE.sub(fence, text)
    return INLINE_CODE.sub(hide, text), kept


def unmask_code(text: str, kept: list) -> str:
    for i, original in enumerate(kept):
        text = text.replace(_MASK % i, original)
    return text


def substitute(text: str, values: dict, cfg, report: list | None = None) -> str:
    """本文の `{{…}}` を置き換える。値が無いところは**そのまま残す**。

    消してしまうと本文が静かに壊れるので、残したうえで報告に出す。
    """
    text, kept = mask_code(text)
    used: set = set()
    missing: list = []

    def sub(m):
        name = m.group('name')
        spec = (m.group('spec') or '').strip()
        val = values.get(name)
        if val is None:
            missing.append(name)
            return m.group(0)
        used.add(name)
        return render(val, spec, cfg)

    out = unmask_code(PLACEHOLDER.sub(sub, text), kept)
    if report is not None:
        if used:
            report.append(f'{tag("values")} ' + t('substituted {n}', n=len(used)))
        for name in sorted(set(missing)):
            # 波括弧そのものは呼ぶ側で足す（t() は `{{…}}` を文字どおり扱う）
            report.append(f'{tag("values")}{tag("warning")} ' + t(
                '{name} is not in {dir}/ (left as it is)',
                name='{{' + name + '}}', dir=Path(cfg['results_dir']).name))
    return out


# ---------------------------------------------------------------- 前回との差

SNAPSHOT_NAME = '.values-prev.json'


def snapshot_path(cfg) -> Path:
    return Path(cfg['results_dir']) / SNAPSHOT_NAME


def snapshot(cfg) -> None:
    """いまの値を「前回」として取っておく。

    分析を走らせる**直前**に呼ぶ。そうすると走らせたあとに
    `octavo values --diff` で「再推定で論文のどの数字が動いたか」が出る。
    査読対応で「何が変わったか」を人に説明するときに要る。
    """
    vals, _ = load(cfg)
    if not vals:
        return
    data = {'_taken': datetime.now().isoformat(timespec='seconds'),
            'values': {k: {'raw': v.value, 'text': render(v, '', cfg),
                           'source': v.source}
                       for k, v in vals.items()}}
    p = snapshot_path(cfg)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1) + '\n',
                 encoding='utf-8')


def read_snapshot(cfg) -> tuple:
    """(取った日時, {名前: {raw, text, source}}) を返す。無ければ ('', {})。"""
    try:
        d = json.loads(snapshot_path(cfg).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return '', {}
    if not isinstance(d, dict) or not isinstance(d.get('values'), dict):
        return '', {}
    return str(d.get('_taken', '')), d['values']


def _git(cfg, args: list) -> str:
    """cfg.root で git を回して標準出力を返す。失敗は GitError。"""
    try:
        r = subprocess.run(['git'] + args, cwd=str(cfg.root), capture_output=True,
                           text=True, encoding='utf-8', errors='replace')
    except OSError as e:
        raise GitError(t('cannot run git: {why}', why=e)) from e
    if r.returncode != 0:
        raise GitError((r.stderr or r.stdout).strip().split('\n')[0])
    return r.stdout


def load_at(cfg, ref: str) -> dict:
    """git の `ref` の時点の results/*.json を読む。

    R&R で要るのは「**投稿した版**と今の版」の比較で、`.values-prev.json`
    （前に分析を走らせた直前）ではない。版を刻む仕組みを新しく作らず、
    git のタグ・コミットに乗せる。`octavo values --diff v1-submitted` のように使う。
    """
    try:
        rel = Path(cfg['results_dir']).relative_to(cfg.root).as_posix()
    except ValueError as e:
        raise GitError(t('results_dir is outside the repository, so it cannot be '
                         'compared with git')) from e

    names = _git(cfg, ['ls-tree', '-r', '--name-only', ref, '--', rel]).split('\n')
    out: dict = {}
    for name in names:
        name = name.strip()
        base = name.rsplit('/', 1)[-1]
        if not name.endswith('.json') or base.startswith('.'):
            continue
        try:
            raw = json.loads(_git(cfg, ['show', f'{ref}:{name}']))
        except (GitError, ValueError):
            continue
        if not isinstance(raw, dict):
            continue
        for k, v in raw.items():
            if not k.startswith('_'):
                out[k] = _value(k, v, base)
    return out


def diff(cfg, ref: str = '') -> tuple:
    """(取った日時, 変わったもの, 増えたもの, 消えたもの) を返す。

    `ref` を渡すと **git のその時点**（`v1-submitted` のようなタグ）と比べる。
    渡さなければ「前に分析を走らせた直前」の控えと比べる。

    比べるのは**本文に出る文字**（書式を通したあと）。生の値が
    0.3419 から 0.3421 に動いても、`.3f` なら本文は 0.342 のままなので
    「変わっていない」と見なす。論文としてはそれが正しい。
    """
    if ref:
        taken = f'git {ref}'
        prev = {k: {'text': render(v, '', cfg), 'source': v.source}
                for k, v in load_at(cfg, ref).items()}
    else:
        taken, prev = read_snapshot(cfg)
    now, _ = load(cfg)
    now_text = {k: render(v, '', cfg) for k, v in now.items()}

    changed = [(k, prev[k].get('text', ''), now_text[k])
               for k in sorted(set(prev) & set(now_text))
               if prev[k].get('text', '') != now_text[k]]
    added = sorted(set(now_text) - set(prev))
    removed = sorted(set(prev) - set(now_text))
    return taken, changed, added, removed


def referenced(text: str) -> set:
    """本文が参照している値の名前を集める（コードの中は数えない）。"""
    masked, _ = mask_code(text)
    return {m.group('name') for m in PLACEHOLDER.finditer(masked)}
