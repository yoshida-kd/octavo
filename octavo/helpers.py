# -*- coding: utf-8 -*-
"""プロジェクトの analysis/octavo.R・octavo_helper.py を今の版にする（octavo migrate --helper）。

ヘルパーはプロジェクトを作ったときのコピーで、Octavo を新しくしても変わらない。
ここでは **Octavo が出したどれかの版と1文字も違わないコピーだけ** を置き換える。
そうでないコピーは持ち主が手を入れたものなので、触らずに知らせる。
同じ中身は Octavo から取り戻せるので、控えは残さない。

KNOWN は、これまでに出した版の中身のハッシュ値（改行を LF に揃えた sha256）。
ひな型を変えたら、変える前のハッシュ値をここに足す（テストが履歴と突き合わせる）。
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from . import analysis as anamod
from . import tmpl
from .i18n import t

# 名前 -> (使う言語, ひな型)
HELPERS = {
    'octavo.R': ('r', 'analysis/common/analysis/octavo.R'),
    'octavo_helper.py': ('python', 'analysis/python/analysis/octavo_helper.py'),
}

KNOWN = {
    'octavo.R': {
        '1fc41a6eb0352a9317a6c440e427d984e35d4ddf8de331f048bc8c779ca59634',
        '25658298bf8045b4a845d375b8f9cc931756b8c43ca50244b7100db82b98d8dc',
        '55ad1f03979dd3f56fcbda75ec34eb6baa691481a352ae4d53e726848e58d57c',
        '7386c693693b9a607ecbb24e36070bee0e09db171b5e420a4fd6ebfdf7202e1a',
        'a43ec85b2f7059babd74fc934436f6ca538a19fc0eebc10f4432ba7230d1875b',
        '054d36c35adf4ec290e633dd5a7e7171f94de7477331e960e549031e60439356',
        'ce4a3ba3b0b0a80f3b5561c7db70828a95e4bf71adc8ef84994833ef7da5244b',
        'e14521c2e01ac1cd59c817040fb9744022874ae25ba8766a00115184983dad84',
        '62a1b664481b5f692b736557ce25db5d57d63a6de61d510b9b5489c32c0a41ca',
        '5675c81d4744a2466344bf7c683af120a1cc440b5463770290142d2737e01d81',
        'b3c5d4998bcae8227b267b79384089b342c813bbd4336bb37130b8ececa93f0d',
    },
    'octavo_helper.py': {
        '0a5639f2bf81edbd21e8eefe3fa054bd6a18c273f130643936de8639ca113626',
        '6fdf80c0775595a04c3729eb99145984705fa71999f1503abd260fd6f97ecebd',
        'ac27982a31114912d7e2c09074ed5240a8d8ad5ed15aac21986860cc69837ae9',
        '95f56c74ea49aecccdace560bddd7f89e2ac02e260f246faf9112b237c4f0182',
        '76da57c5a97e34d98b2c7f37f4fe8d3ed17f5695d8b144eee677c3b24dc14b67',
    },
}

# 数値を results/、図表を figures/・tables/ に書いていたころの版。今の版は
# octavo.config.py の置き場（既定は assets/）に書くので、置き換えると書き出し先が変わる。
WROTE_TO_RESULTS = {
    '1fc41a6eb0352a9317a6c440e427d984e35d4ddf8de331f048bc8c779ca59634',
    '25658298bf8045b4a845d375b8f9cc931756b8c43ca50244b7100db82b98d8dc',
    '55ad1f03979dd3f56fcbda75ec34eb6baa691481a352ae4d53e726848e58d57c',
    '7386c693693b9a607ecbb24e36070bee0e09db171b5e420a4fd6ebfdf7202e1a',
}


def fingerprint(data: bytes) -> str:
    """改行の違い（Windows の CRLF）を除いた中身のハッシュ値。"""
    return hashlib.sha256(data.replace(b'\r\n', b'\n')).hexdigest()


@dataclass
class Helper:
    """1つのヘルパーの今の状態。state は current / old / edited / missing / unused。"""
    name: str
    path: Path
    state: str
    new: bytes
    moves_outputs: bool = False


def status(cfg) -> list:
    """プロジェクトのヘルパーごとの状態。ないヘルパーは、その言語の .qmd があるときだけ missing。"""
    root = Path(cfg.root)
    used = anamod.engines(cfg)
    out = []
    for name, (lang, template) in HELPERS.items():
        path = root / 'analysis' / name
        new = tmpl.find(template, root).read_bytes()
        if not path.is_file():
            out.append(Helper(name, path, 'missing' if lang in used else 'unused', new))
            continue
        mine = fingerprint(path.read_bytes())
        if mine == fingerprint(new):
            state = 'current'
        elif mine in KNOWN[name]:
            state = 'old'
        else:
            state = 'edited'
        out.append(Helper(name, path, state, new, mine in WROTE_TO_RESULTS))
    return out


def outdated(cfg) -> list:
    """置き換えられる古いコピーの名前（ほかのコマンドが案内に使う）。"""
    return [h.name for h in status(cfg) if h.state == 'old']


def run(cfg, dry_run: bool = False) -> int:
    """octavo migrate --helper。手を入れてあるコピーは触らずに知らせる（失敗ではない）。"""
    from .syntax import write_like
    changed = replaced = 0
    rows = [h for h in status(cfg) if h.state != 'unused']
    if not rows:
        print(t('This project has no analysis, so there is no helper to update.'))
        return 0
    for h in rows:
        rel = cfg.rel(h.path)
        if h.state == 'current':
            print(t('{file}: already the current version', file=rel))
        elif h.state == 'edited':
            print(t('{file}: left as it is — it matches no version Octavo has shipped, so it has '
                    'been edited. To take the current version anyway, delete it and run this '
                    'again (the current one, to compare: {template})',
                    file=rel, template=tmpl.find(HELPERS[h.name][1], Path(cfg.root))))
        else:
            changed += 1
            if h.state == 'missing':
                line = (t('{file}: would be put back (an analysis here uses it)', file=rel) if dry_run
                        else t('{file}: put back (an analysis here uses it)', file=rel))
            else:
                replaced += 1
                line = (t('{file}: would be replaced with the current version', file=rel) if dry_run
                        else t('{file}: replaced with the current version', file=rel))
            print(line)
            if h.moves_outputs:
                print('  ' + t('note: the old copy wrote values to results/ and figures and tables to '
                               'figures/ and tables/; the current one writes where octavo.config.py '
                               'says (assets/ unless set)'))
            if not dry_run:
                h.path.parent.mkdir(parents=True, exist_ok=True)
                write_like(h.path, h.new.decode('utf-8'), h.path.read_bytes() if h.path.is_file() else b'')
    if changed and dry_run:
        print(t('nothing was changed (drop --dry-run to update it)'))
    elif replaced:
        print(t('The results on disk were made by the old copy; to make them again: {cmd}',
                cmd='octavo analysis run'))
    return 0
