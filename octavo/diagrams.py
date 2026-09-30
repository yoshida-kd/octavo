"""Typst で描いた図（`figures/<name>.typ`）を `assets/figures/<name>.pdf` と `.png` にする。

TeX の頃の TikZ（standalone）の代わり。元（手で書く）は `figure_src_dir`（figures/）、
組んだもの（手で直さない）は `figure_dir`（assets/figures/）で、分析の図と同じ場所。
原稿は普通の図と同じく `![因果の図](../../assets/figures/dag.png){#fig-dag}` と書くので
（組むときに Typst・LaTeX は .pdf、Word は .png に差し替わる）、番号・参照・Word・
LaTeX・`octavo check` がどれもそのまま効く。原稿の中に Typst を直接書くと、
Typst の出力にしか図が出ず、ラベルも Octavo から見えない。

- `figures/*.typ` を1つずつ組む。**`_` で始まるものは組まない**（`_common.typ` の
  ように、ほかの図が `#import` する共通の部品のため）。それが変わったら全部を組み直す
- 組み直すのは、`.pdf` か `.png` がないか、`.typ`（か共通の部品）より古いときだけ
- `--root` はプロジェクトの直下。図から `#import "/figures/_parts.typ"` や
  `json("/assets/values/analysis.json")` と書ける
- Typst がなければ注意だけ出して続ける（組み済みの図はそのまま使える）。
  **組んで失敗したら止める** — 古い図のまま組むと、原稿と図が食い違うため
  （分析と同じ考え方）
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .i18n import t, tag

PPI = 250          # PNG（Word が使う）の解像度。Typst と LaTeX は .pdf を使う


def sources(cfg) -> list:
    """組む対象の `.typ`（`_` や `.` で始まるものは除く）。"""
    folder = Path(cfg['figure_src_dir'])
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.glob('*.typ') if not p.name.startswith(('_', '.')))


def _shared_mtime(cfg) -> float:
    folder = Path(cfg['figure_src_dir'])
    return max((p.stat().st_mtime for p in folder.glob('_*.typ')), default=0.0)


def watch_paths(cfg) -> list:
    """`octavo watch` が見張る `.typ`（共通の部品も含む）。"""
    folder = Path(cfg['figure_src_dir'])
    return sorted(folder.glob('*.typ')) if folder.is_dir() else []


def outputs(cfg, src: Path) -> tuple:
    """組んだ図の置き場（分析の図と同じ figure_dir）。"""
    out = Path(cfg['figure_dir'])
    return out / f'{src.stem}.pdf', out / f'{src.stem}.png'


def stale(cfg) -> list:
    """組み直しが要る `.typ`。"""
    shared = _shared_mtime(cfg)
    out = []
    for src in sources(cfg):
        newest = max(src.stat().st_mtime, shared)
        if any(not o.exists() or o.stat().st_mtime < newest for o in outputs(cfg, src)):
            out.append(src)
    return out


def run(cfg, report: list, force: bool = False) -> bool:
    """古い図を組む。False なら組むのに失敗した（変換に進まない）。"""
    todo = sources(cfg) if force else stale(cfg)
    if not todo:
        return True
    typst = shutil.which('typst')
    if typst is None:
        report.append(tag('figure') + ' ' + t(
            'Typst is not installed, so {n|this figure was|these # figures were} not drawn: {files}',
            n=len(todo), files=', '.join(cfg.rel(p) for p in todo)))
        return True
    for src in todo:
        pdf, png = outputs(cfg, src)
        pdf.parent.mkdir(parents=True, exist_ok=True)
        for dest, extra in ((pdf, []), (png, ['--format', 'png', '--ppi', str(PPI)])):
            r = subprocess.run([typst, 'compile', '--root', str(cfg.root), *extra,
                                str(src), str(dest)],
                               capture_output=True, text=True, encoding='utf-8')
            if r.returncode != 0:
                lines = [l for l in (r.stderr or r.stdout).strip().splitlines() if l.strip()]
                report.append(tag('figure') + ' ' + t('could not draw {file}', file=cfg.rel(src)))
                report += ['  ' + l for l in lines[:12]]
                return False
        report.append(tag('figure') + ' ' + t('drew {file} -> .pdf, .png', file=cfg.rel(src)))
    return True
