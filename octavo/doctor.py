# -*- coding: utf-8 -*-
"""環境の診断。「何が足りなくて、どの形式が出せないか」をはっきり言う。

    octavo doctor
    octavo doctor --verbose

WSL / Ubuntu サーバでの導入は setup.sh がまとめて面倒を見る。ここは
「入っているか」を見るだけで、勝手に入れない。
"""
from __future__ import annotations

import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

from . import csl as cslmod
from . import pandocrun
from . import paths
from .i18n import language, t

OK, WARN, NG = '  ok  ', ' note ', ' none '


def _run(cmd, timeout=20) -> tuple:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           encoding='utf-8', errors='replace')
        return r.returncode, (r.stdout or '') + (r.stderr or '')
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)


def _first_line(s: str) -> str:
    return (s.strip().split('\n') or [''])[0][:70]


def _kpsewhich(name: str) -> bool:
    if not shutil.which('kpsewhich'):
        return False
    code, out = _run(['kpsewhich', name])
    return code == 0 and out.strip() != ''


def is_wsl() -> bool:
    return 'microsoft' in platform.uname().release.lower()


def is_macos() -> bool:
    return platform.system() == 'Darwin'


def hint(key: str):
    """入れ方の案内。macOS では Homebrew の書き方を出す（無ければ共通のもの）。"""
    if is_macos() and key in HINTS_MACOS:
        return HINTS_MACOS[key]
    return HINTS.get(key)


def collect() -> dict:
    """調べた結果を素の辞書で返す（表示は report() 側）。"""
    f: dict = {}

    f['python'] = (sys.version_info >= (3, 9), platform.python_version())

    exe = shutil.which('pandoc')
    if exe:
        v = pandocrun.version_str()
        f['pandoc'] = (pandocrun.at_least(2, 8), f'{v}  ({exe})')
        f['pandoc_citeproc'] = (pandocrun.at_least(2, 11),
                                t('CSL citations (--citeproc built in)'))
        f['pandoc_typst'] = (pandocrun.at_least(3, 1), t('Typst output (-t typst)'))
    else:
        f['pandoc'] = (False, t('not found'))
        f['pandoc_citeproc'] = f['pandoc_typst'] = (False, '—')

    for name, label in (('lualatex', 'LuaLaTeX'), ('latexmk', 'latexmk'),
                        ('typst', 'Typst'), ('biber', t('biber (not needed with CSL)')),
                        ('fc-list', 'fontconfig'), ('git', 'git')):
        p = shutil.which(name)
        detail = p or t('not found')
        if p and name == 'typst':
            _, out = _run(['typst', '--version'])
            detail = f'{_first_line(out)}  ({p})'
            m = re.search(r'typst (\d+)\.(\d+)', out)
            tv = (int(m.group(1)), int(m.group(2))) if m else (0, 0)
            # Typst スライドの体裁（block の高さ 1fr）は 0.12 から
            f['typst_0_12'] = (tv >= (0, 12), _first_line(out))
        if p and name == 'lualatex':
            _, out = _run(['lualatex', '--version'])
            detail = f'{_first_line(out)}  ({p})'
        f[name] = (bool(p), detail)

    # 分析（Quarto + R）。無くても変換はできるので「不足」ではなく「注意」。
    exe = shutil.which('quarto')
    if exe:
        _, out = _run(['quarto', '--version'])
        f['quarto'] = (True, f'{_first_line(out)}  ({exe})')
    else:
        f['quarto'] = (False, t('not found (only needed to run a .qmd)'))
    exe = shutil.which('Rscript')
    if exe:
        _, out = _run(['Rscript', '--version'])
        f['R'] = (True, f'{_first_line(out)}  ({exe})')
        # renv は「分析の環境はプロジェクトごとに」の前提なのに、
        # setup.sh も入れないし R にも付いてこない。無ければここで言う。
        _, out = _run(['Rscript', '-e',
                       'cat(requireNamespace("renv", quietly = TRUE))'])
        has = out.strip().endswith('TRUE')
        f['renv'] = (has, t('installed') if has else t('not installed'))
    else:
        f['R'] = (False, t('not found (only needed if the .qmd is R)'))

    # TeX のクラス・パッケージ
    for cls, label in (('ltjsarticle.cls', t('Japanese document class ltjsarticle')),
                       ('luatexja.sty', 'luatexja'),
                       ('beamer.cls', 'Beamer'),
                       ('beamerthememetropolis.sty', t('Beamer theme metropolis')),
                       ('haranoaji.sty', t('Harano Aji fonts (for LaTeX)'))):
        f['tex:' + cls] = (_kpsewhich(cls), label)

    # 日本語フォント（LaTeX 用）。macOS には fontconfig が無いが、LuaLaTeX は
    # fc-list を使わずにフォントを探すので、無いことを問題として出さない。
    if is_macos() and not shutil.which('fc-list'):
        f['cjkfonts'] = (True, t('macOS: LuaLaTeX finds the system fonts itself'))
    elif shutil.which('fc-list'):
        _, out = _run(['fc-list', ':lang=ja', 'family'])
        fams = sorted({l.split(',')[0].strip() for l in out.strip().split('\n') if l.strip()})
        f['cjkfonts'] = (bool(fams), t('{n} {n|family|families}', n=len(fams))
                         + (('  ' + t('e.g.') + f' {", ".join(fams[:4])}')
                                                            if fams else ''))
    else:
        f['cjkfonts'] = (False, t('no fc-list, so this cannot be checked'))

    if shutil.which('typst'):
        _, out = _run(['typst', 'fonts'])
        cjk = [l for l in out.split('\n')
               if any(k in l for k in ('CJK', 'Noto Sans JP', 'Noto Serif JP',
                                       'IPA', 'Hiragino', 'Yu ', 'Harano'))]
        f['typst_cjk'] = (bool(cjk), (t('{n} found', n=len(cjk)) + '  '
                                      + t('e.g.') + f' {cjk[0].strip()}'
                                      if cjk else t('Typst can see no CJK font')))
        # 既定の書体（typst.FONTS）が見えるか。無くても Noto に落ちて組めるので
        # 「注意」止まり。何が足りないかと、入れ方を出す。
        from .backends.typst import FONTS
        families = {l.strip() for l in out.split('\n')}
        wanted = sorted({latin for latin, _ in FONTS.values()}
                        | {cjk_fonts[0] for _, cjk_fonts in FONTS.values()})
        lack = [w for w in wanted if w not in families]
        f['typst_default_fonts'] = (
            not lack,
            t('all there: {names}', names=', '.join(wanted)) if not lack
            else t('missing: {names} (a fallback font is used instead)',
                   names=', '.join(lack)))
    else:
        f['typst_cjk'] = (False, t('no typst, so this cannot be checked'))

    cached = cslmod.cached()
    # 表示の言語。ロケットが英語の機械で日本語のまま使いたい人が
    # OCTAVO_LANG に気づけるように、毎回ここに出す。
    import os as _os
    src = ('OCTAVO_LANG' if _os.environ.get('OCTAVO_LANG') else
           next((v for v in ('LC_ALL', 'LC_MESSAGES', 'LANG')
                 if _os.environ.get(v)), None))
    f['lang'] = (True, f'{language()}  ({src or t("no locale set")})'
                 + ('' if language() == 'ja'
                    else '  ' + t('— set OCTAVO_LANG=ja for Japanese')))

    f['csl'] = (True, t('{n} cached', n=len(cached))
                      + (f'  ({", ".join(p.stem for p in cached[:5])})' if cached else
                         '  ' + t('— fetch one with e.g. octavo csl get apa')))
    f['wsl'] = (True, 'WSL' if is_wsl() else
                ('macOS ' + platform.mac_ver()[0]).rstrip() if is_macos()
                else platform.system())
    return f


# 形式ごとに「これが無いと（ふだんの使い方では）出せない」もの。
# pandoc_citeproc はどの形式でも要る（引用を CSL で解決するため）。
# 引用を使わない下書きなら octavo build --no-citations で回避できる。
NEEDS = {
    'typst':    ['pandoc_typst', 'pandoc_citeproc', 'typst', 'typst_cjk'],
    'typst-slides': ['pandoc_typst', 'pandoc_citeproc', 'typst', 'typst_0_12', 'typst_cjk'],
    'typst-notes': ['pandoc_typst', 'pandoc_citeproc', 'typst', 'typst_cjk'],
    'docx':     ['pandoc', 'pandoc_citeproc'],
    'latex':    ['pandoc', 'pandoc_citeproc', 'lualatex', 'tex:ltjsarticle.cls'],
    'beamer':   ['pandoc', 'pandoc_citeproc', 'lualatex', 'tex:beamer.cls'],
}

# TeX は任意（setup.sh --with-tex で足す）。これらの形式が出せないことは
# 「不足」ではなく「注意」にとどめ、doctor の終了コードにも数えない。
TEX_TARGETS = ('latex', 'beamer')
TEX_TOOLS = ('lualatex', 'latexmk', 'biber', 'cjkfonts')

# 「足りない」一覧に出すときの短い名前
NEED_LABELS = {
    'pandoc': 'pandoc',
    'pandoc_citeproc': 'pandoc 2.11+ (CSL citations)',
    'pandoc_typst': 'pandoc 3.1+ (Typst output)',
    'lualatex': 'LuaLaTeX',
    'typst': 'typst',
    'typst_0_12': 'Typst 0.12 or newer',
    'typst_cjk': 'a CJK font for Typst',
    'cjkfonts': 'CJK fonts',
    'tex:ltjsarticle.cls': 'ltjsarticle (texlive-lang-japanese)',
    'tex:beamer.cls': 'beamer',
    'tex:luatexja.sty': 'luatexja',
}

REPO_URL = 'https://github.com/yoshida-kd/octavo'

# 無くても組める（代わりが使われる）ので「不足」ではなく「注意」で出すもの
SOFT_TOOLS = ('typst_default_fonts',)

HINTS = {
    'pandoc': 'sudo apt install pandoc (if it is old, take the .deb from GitHub)',
    'quarto': 'install the .deb from https://quarto.org/docs/get-started/ '
              '(not needed unless the analysis is a .qmd)',
    'R': 'sudo apt install r-base (same again)',
    'typst_default_fonts': 'sudo apt install fonts-morisawa-bizud-gothic fonts-morisawa-bizud-mincho fonts-inter (then fc-cache -f)',
    'renv': "mkdir -p \"$(Rscript -e 'cat(Sys.getenv(\"R_LIBS_USER\"))')\" && "
            "Rscript -e 'install.packages(\"renv\", repos = \"https://cloud.r-project.org\")'",
    'pandoc_citeproc': 'upgrade to pandoc 2.11 or newer (CSL citations need it)',
    'pandoc_typst': 'upgrade to pandoc 3.1 or newer',
    'lualatex': 'sudo apt install texlive-luatex texlive-lang-japanese',
    'latexmk': 'sudo apt install latexmk',
    'typst': 'install it from https://github.com/typst/typst/releases (cargo works too)',
    'typst_0_12': 'upgrade Typst (bash setup.sh installs the version this was tested on)',
    'biber': 'not needed with CSL. Only if you go back to biblatex: sudo apt install biber',
    'tex:ltjsarticle.cls': 'sudo apt install texlive-lang-japanese',
    'tex:luatexja.sty': 'sudo apt install texlive-lang-japanese',
    'tex:beamer.cls': 'sudo apt install texlive-latex-recommended',
    'tex:beamerthememetropolis.sty': 'sudo apt install texlive-latex-extra '
                                     '(or set beamer_theme to default if you '
                                     'do not use it)',
    'tex:haranoaji.sty': 'sudo apt install texlive-lang-japanese',
    'cjkfonts': 'sudo apt install fonts-noto-cjk fonts-noto-cjk-extra',
    'typst_cjk': 'sudo apt install fonts-noto-cjk (then fc-cache -f). For a font '
                 'kept elsewhere, point TYPST_FONT_PATHS at its folder',
    'fc-list': 'sudo apt install fontconfig',
}

# macOS（Homebrew）での入れ方。キーは HINTS と同じで、ここに無いものは HINTS を使う。
# 引数付きの brew は setup.sh と同じ名前（casks は font-… / quarto / mactex-no-gui）。
HINTS_MACOS = {
    'pandoc': 'brew install pandoc',
    'quarto': 'brew install --cask quarto (not needed unless the analysis is a .qmd)',
    'R': 'brew install r (or the installer from https://cran.r-project.org)',
    'typst_default_fonts': 'brew install --cask font-biz-udgothic font-biz-udmincho font-inter',
    'pandoc_citeproc': 'brew upgrade pandoc',
    'pandoc_typst': 'brew upgrade pandoc',
    'lualatex': 'brew install --cask mactex-no-gui (several GB; open a new terminal afterwards)',
    'latexmk': 'comes with MacTeX: brew install --cask mactex-no-gui',
    'typst': 'brew install typst',
    'typst_0_12': 'brew upgrade typst',
    'biber': 'not needed with CSL. Only if you go back to biblatex: it comes with MacTeX',
    'tex:ltjsarticle.cls': 'comes with MacTeX: brew install --cask mactex-no-gui',
    'tex:luatexja.sty': 'comes with MacTeX: brew install --cask mactex-no-gui',
    'tex:beamer.cls': 'comes with MacTeX: brew install --cask mactex-no-gui',
    'tex:beamerthememetropolis.sty': 'comes with MacTeX (or set beamer_theme to default '
                                     'if you do not use it)',
    'tex:haranoaji.sty': 'comes with MacTeX: brew install --cask mactex-no-gui',
    'cjkfonts': 'MacTeX brings the Harano Aji fonts LaTeX uses: brew install --cask mactex-no-gui',
    'fc-list': 'not needed on macOS',
    'typst_cjk': 'brew install --cask font-noto-sans-cjk-jp font-noto-serif-cjk-jp. For a '
                 'font kept elsewhere, point TYPST_FONT_PATHS at its folder',
}

LABELS = {
    'python': 'Python',
    'quarto': 'Quarto',
    'R': '  └ R (Rscript)',
    'renv': '      └ renv',
    'pandoc': 'pandoc',
    'pandoc_citeproc': '  └ CSL citations',
    'pandoc_typst': '  └ Typst output',
    'lualatex': 'LuaLaTeX',
    'latexmk': 'latexmk',
    'typst': 'Typst',
    'biber': 'biber',
    'fc-list': 'fontconfig',
    'git': 'git',
    'cjkfonts': 'CJK fonts',
    'typst_cjk': '  └ visible to Typst',
    'typst_default_fonts': '  └ default typefaces',
    'lang': 'display language',
    'csl': 'CSL cache',
    'wsl': 'how it runs',
}


def report(verbose: bool = False) -> int:
    # 印も訳す（幅は揃えたまま）。モジュールの定数は英語の原文
    OK, WARN, NG = t('  ok  '), t(' note '), t(' none ')
    f = collect()
    head = '== ' + t('Tools') + ' '
    print(head + '=' * max(4, 58 - len(head)))
    for k in ('wsl', 'python', 'pandoc', 'pandoc_citeproc', 'pandoc_typst',
              'typst', 'typst_cjk', 'typst_default_fonts', 'csl', 'lang'):
        if k not in f:
            continue
        ok, detail = f[k]
        # 既定の書体が無いのは「組めない」ではない（Noto に落ちる）ので注意止まり
        bad = WARN if k in SOFT_TOOLS else NG
        print(f'[{OK if ok else bad}] {t(LABELS.get(k, k)):<22} {detail}')

    head = '\n== ' + t('Analysis (only when you use a .qmd)') + ' '
    print(head + '=' * max(4, 59 - len(head)))
    for k in ('quarto', 'R', 'renv'):
        if k not in f:
            continue
        ok, detail = f[k]
        print(f'[{OK if ok else WARN}] {t(LABELS[k]):<22} {detail}')

    head = '\n== ' + t('TeX (only when you use LaTeX / Beamer)') + ' '
    print(head + '=' * max(4, 59 - len(head)))
    for k in TEX_TOOLS:
        ok, detail = f[k]
        print(f'[{OK if ok else WARN}] {t(LABELS.get(k, k)):<22} {detail}')
    for k, (ok, label) in sorted(f.items()):
        if k.startswith('tex:'):
            print(f'[{OK if ok else WARN}] {label}')

    head = '\n== ' + t('Formats you can produce') + ' '
    print(head + '=' * max(4, 59 - len(head)))
    missing_all = []
    tex_missing = False
    for target, needs in NEEDS.items():
        lack = [n for n in needs if not f.get(n, (False, ''))[0]]
        if not lack:
            print(f'[{OK}] {target}')
            continue
        if target in TEX_TARGETS:
            # pandoc の不足は typst / docx の行で「不足」として出ている
            tex_lack = [n for n in lack if not n.startswith('pandoc')]
            if tex_lack:
                tex_missing = True
                print(f'[{WARN}] {target:<13} ' + t(
                    'add TeX and this works (missing: {what})',
                    what=', '.join(t(NEED_LABELS.get(n, n)) for n in tex_lack)))
            else:
                missing_all += lack
                print(f'[{NG}] {target:<13} ' + t(
                    'missing: {what}',
                    what=', '.join(t(NEED_LABELS.get(n, n)) for n in lack)))
        else:
            missing_all += lack
            print(f'[{NG}] {target:<13} ' + t(
                'missing: {what}',
                what=', '.join(t(NEED_LABELS.get(n, n)) for n in lack)))

    if not f['quarto'][0] and verbose:
        print('\n  ' + t('For a .qmd:') + ' ' + t(hint('quarto')))
    if 'typst_default_fonts' in f and not f['typst_default_fonts'][0]:
        print('\n  ' + t('For the default typefaces:') + ' '
              + t(hint('typst_default_fonts')))
    if 'renv' in f and not f['renv'][0]:
        print('\n  ' + t('For renv:') + ' ' + t(hint('renv')))
    setup = paths.setup_script()
    # pip で入れたときは setup.sh が手元に無いので、取ってくる所から案内する。
    run = f'bash {setup}' if setup is not None else (
        f'git clone {REPO_URL} && bash octavo/setup.sh')
    if tex_missing:
        print('\n  ' + t('For LaTeX / Beamer too: {cmd} --with-tex', cmd=run))
    if missing_all:
        head = '\n== ' + t('What to add') + ' '
        print(head + '=' * max(4, 59 - len(head)))
        seen = set()
        for n in missing_all:
            h = hint(n)
            if h and h not in seen:
                seen.add(h)
                print('  ' + t(h))
        print('\n  ' + t('To install them all: {cmd}', cmd=run))
    else:
        print('\n  ' + t('Every everyday format (typst / docx) works.'))
    return 1 if missing_all else 0
