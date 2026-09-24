# -*- coding: utf-8 -*-
"""バックエンドの共通土台。

新しい出力形式を足すときは Backend を継承して backends/__init__.py の
REGISTRY に登録する。**共通の前処理はここに書かない**（それは md.py と build.py）。
ここに来るのは「その形式でしか意味を持たない書き方」だけ。
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from .. import bib as bibmod
from ..i18n import t, tag
from .. import md as mdlib
from .. import tmpl


def relpath(target: Path, start: Path) -> str:
    return Path(os.path.relpath(target, start)).as_posix()


# --------------------------------------------------------------------------
# プロファイル: 同じ原稿を「論文」「A4プリント」「スライド」のどれとして
# 組むか。目次・節番号・要旨の扱いと、条件付きブロックの取捨を決める。
# --------------------------------------------------------------------------
PROFILES = {
    'paper':   {'toc': False, 'number_sections': False, 'abstract': True,
                'standalone_fragmentable': False},
    'handout': {'toc': True,  'number_sections': True,  'abstract': False,
                'standalone_fragmentable': True},
    'slides':  {'toc': False, 'number_sections': False, 'abstract': False,
                'standalone_fragmentable': True},
}


@dataclass
class Ctx:
    """1回の変換で持ち回す状態。"""
    cfg: object
    backend: 'Backend'
    out_dir: Path
    profile: str = 'paper'
    doc_name: str = 'body'
    appendix: bool = False
    meta: dict = field(default_factory=dict)
    entries: dict = field(default_factory=dict)      # .bib の中身（poscite 用）
    values: dict = field(default_factory=dict)       # 分析が出した数値（{{…}} 用）
    csl: Path | None = None
    report: list = field(default_factory=list)
    shift_headings: int = -1
    anonymous: bool = False                         # 匿名審査用に組むか

    # -- 素性 ---------------------------------------------------------------
    @property
    def standalone(self) -> bool:
        """完結した文書を出すか（main.tex / main.typ を使わないか）。"""
        if self.backend.always_standalone:
            return True
        return self.profile != 'paper'

    def profile_opt(self, key: str):
        """profile の既定を config が上書きできる。"""
        if key == 'number_sections':
            return self._number_sections()
        override = self.cfg.get(key, None)
        if override is not None and key == 'toc':
            return override
        return PROFILES[self.profile][key]

    def _number_sections(self) -> bool:
        """節番号を pandoc に振らせるか。

        LaTeX と Typst は組版側が勝手に振るので pandoc に頼まない。Word は
        誰も振らないので、論文・プリントでは pandoc に文字として入れてもらう
        （そうしないと「第2節」という言及の相手が消える）。スライドには振らない。
        """
        if self.backend.is_slides:
            return False
        override = self.cfg.get('number_sections')
        if override is not None:
            return override
        if not self.backend.auto_numbers_sections:
            return False           # 番号はマークダウン段階で戻してある
        return PROFILES[self.profile]['number_sections']

    @property
    def keep_classes(self) -> set:
        """条件付きブロック（`::: {.slides-only}` 等）で「残す」印の集合。

        **出力形式で決める。**同じ講義ノートから A4 プリントとスライドの両方を
        作るとき、profile は 'handout' のまま動かないので、profile では
        出し分けられないため。

            beamer/typst-slides  slides, screen, <形式名>
            latex/typst/docx     print, doc, <形式名>, <profile>
        """
        b = self.backend.name
        keep = ({'slides', 'screen', b} if self.backend.is_slides
                else {'print', 'doc', b, self.profile})
        if self.anonymous:
            # `::: {.no-anonymous}` で囲んだ謝辞・自己紹介がこれで落ちる。
            # 新しい機構ではなく、既にある条件付きブロックに印を1つ足すだけ。
            keep.add('anonymous')
        return keep

    @property
    def table_map(self) -> dict:
        if not self.backend.uses_table_map:
            return {}
        return self.cfg['appendix_table_map'] if self.appendix else self.cfg['table_map']

    @property
    def lang(self) -> str:
        return self.meta.get('lang_short') or self.cfg['lang']

    # -- パス ---------------------------------------------------------------
    def rel(self, p: Path) -> str:
        return relpath(p, self.out_dir)

    def figure_path(self, name: str) -> Path:
        return self.cfg['figure_dir'] / f'{name}{self.backend.figure_ext(self.cfg)}'

    def table_path(self, name: str) -> Path:
        return self.cfg['table_dir'] / f'{name}{self.backend.table_ext}'

    def template(self, rel: str) -> Path:
        """ひな型の実際のパス。プロジェクト・ユーザーの上書きがあればそちら（tmpl.py）。"""
        return tmpl.find(rel, self.cfg.root)

    def say(self, s: str) -> None:
        self.report.append(s)


class Backend:
    # -- 素性 ---------------------------------------------------------------
    name = 'base'
    label = 'base'                  # 表示名（英語で書き、表示時に t() を通す）
    pandoc_to = 'plain'
    ext = '.txt'
    table_ext = '.txt'
    default_figure_ext = '.png'
    min_pandoc = (2, 8)
    binary = False                # pandoc に直接ファイルを書かせるか
    always_standalone = False     # profile によらず完結した文書を出すか
    uses_table_map = True         # 外部の表ファイル（.tex/.typ）を取り込めるか
    auto_numbers_captions = True  # 組版側がキャプションに番号を振るか
    auto_numbers_sections = True  # 組版側が節番号を振るか（LaTeX/Typst は振る）
    wants_abstract_file = False   # 要旨を別ファイルに書き出すか
    tidy_headings = True
    is_slides = False             # スライドか（条件付きブロックの 'slides' 印を持つ）
    keeps_notes = False           # `::: notes`（発表者ノート）を残すか
    notes_wrap: tuple | None = None   # 残すとき、div の代わりに囲むもの
    # main.tex / main.typ が匿名審査に対応しているかを見分ける目印（表示用）。
    anonymous_guard = ''
    # 手で書く体裁ファイルの名前（main.* 方式の形式だけ持つ）。**正本は原稿の隣**
    # （papers/<名前>/main.typ）に置き、組版のたびに out_dir へ写す。build/ の中に
    # 手で書くファイルを置くと、生成物として消したときに体裁ごと消える。
    main_name = ''

    # -- 図の拡張子（config の figure_ext で上書きできる）-------------------
    def figure_ext(self, cfg) -> str:
        return cfg['figure_ext'].get(self.name) or self.default_figure_ext

    # -- pandoc ------------------------------------------------------------
    def input_extras(self) -> tuple:
        return ()

    def pandoc_args(self, ctx: Ctx) -> list:
        return ['-t', self.pandoc_to, '--wrap=preserve']

    # -- 差し替え（マークダウン段階）---------------------------------------
    def fmt_table(self, m: re.Match, name: str | None, ctx: Ctx) -> str:
        return self.markdown_table(m, ctx)

    def fmt_figure(self, m: re.Match, ctx: Ctx) -> str:
        """既定は素のマークダウン画像に直す（pandoc の figure 扱いに任せる）。"""
        f, num = m.group('file'), m.group('num')
        cap = ' '.join(m.group('cap').split())
        rel = ctx.rel(ctx.figure_path(f))
        head = '' if self.auto_numbers_captions else (
            f'図{num}．' if ctx.lang == 'ja' else f'Figure {num}. ')
        ctx.say(f'{tag("figure")} {num} -> {rel}')
        return f'\n![{head}{cap}]({rel}){{#fig:{f}}}\n'

    def fmt_poscite(self, key: str, ctx: Ctx) -> str:
        """所有格引用。CSL に一本化しているので、著者名は .bib から自前で作り、
        年（と括弧・リンク）は citeproc の `[-@key]` に出させる。"""
        e = ctx.entries.get(key)
        lang = ctx.cfg['poscite_lang'] or ctx.lang
        if not e:
            ctx.say(f'{tag("warning")} ' + t('\\poscite{{{key}}}: no such key in the .bib', key=key))
            return f'[-@{key}]'
        who = bibmod.possessive(e, lang)
        return f'{who}[-@{key}]' if lang == 'ja' else f'{who} [-@{key}]'

    # -- 変換後 ------------------------------------------------------------
    def crossrefs(self, text: str, ctx: Ctx) -> str:
        return text

    def postprocess(self, text: str, ctx: Ctx) -> str:
        return re.sub(r'\n{3,}', '\n\n', text).strip() + '\n'

    def check(self, text: str, ctx: Ctx) -> None:
        pass

    def uses_anonymous_guard(self, text: str) -> bool:
        """main.tex / main.typ が匿名審査の切り替えを**実際に使っているか**。

        宣言（`\\newif\\ifanonymous`）やコメント行は数えない。数えると、
        雛型をそのまま使っているだけで「対応済み」と誤判定してしまう。
        """
        return False

    # -- main.tex / main.typ に渡すフラグ -----------------------------------
    def flags(self, ctx: Ctx) -> tuple | None:
        """(ファイル名, 中身) を返す。`main.tex` を持つ形式だけ実装する。

        題扉は `main.tex` / `main.typ` が持っていて Octavo は触らない。だから
        匿名審査の切り替えは**フラグを1つ渡して向こうに判断させる**。
        `\\input{flags}` / `#import "flags.typ"` を書いておけば、
        `octavo build --anonymous` のたびに中身が入れ替わる。
        """
        return None

    # -- 投稿用に固め直す（octavo bundle）-----------------------------------
    def flatten_assets(self, text: str) -> tuple:
        """外部ファイルへの参照を**ファイル名だけ**にする。

        投稿システムは階層を持てないことが多いので、`../../figures/fig1.pdf`
        のような相対パスを `fig1.pdf` に直し、参照しているパスの一覧を返す。
        呼び出し側（bundle.py）はそれを1つの場所に集める。

        (書き換えた本文, 参照していた相対パスの一覧) を返す。既定は何もしない。
        """
        return text, []

    def out_name(self, ctx: Ctx) -> str:
        if ctx.standalone:
            return ctx.doc_name + self.ext
        return ('appendix' if ctx.appendix else 'body') + self.ext

    def compile(self, ctx: Ctx, path: Path) -> list | None:
        return None

    def compile_main(self, ctx: Ctx) -> Path | None:
        """main.* 方式（paper profile）で `--compile` したとき組版するファイル。

        None なら組版しない。LaTeX は投稿先ごとに回し方（bibtex の有無など）が
        違うので main.tex 側に任せるが、`typst compile main.typ` は1通りしかない。
        """
        return None

    def next_step(self, ctx: Ctx) -> str:
        return ''

    # -- 共通のマークダウン表（table_map を使わない/使えないとき）-----------
    def markdown_table(self, m: re.Match, ctx: Ctx) -> str:
        """`**Table N. cap**` + 表 を pandoc のキャプション付き表に直す。

        組版側が番号を振る形式（LaTeX/Typst）では番号を落とし、振らない
        形式（Word）では番号を残す。表が本文の順に並んでいる限り、どちらでも
        本文中の「表3」という言及と実際の番号は一致する。
        """
        num, cap = m.group('num'), ' '.join(m.group('cap').split())
        body, note = m.group('body'), (m.group('note') or '').strip()
        head = '' if self.auto_numbers_captions else (
            f'表{num}．' if ctx.lang == 'ja' else f'Table {num}. ')
        out = f'\n{body}\n: {head}{cap}\n'
        if note:
            out += f'\n{note}\n'
        return out


# ---------------------------------------------------------------- 相互参照の共通処理

def apply_crossrefs(text: str, ctx: Ctx, *, table_ref, figure_ref, section_ref,
                    figure_labels) -> str:
    """「Table 3」「表3」「Section 4.1」「4.1節」を各形式の参照に変える。

    **pandoc の後に走らせること。**マークダウン段階でやると記号がエスケープされる。
    表は table_map に対応があるものだけ置き換える（マークダウンの表は組版側が
    番号を振るので、地の文は素のテキストのままにしておくのが正しい）。
    """
    pats = mdlib.crossref_patterns(ctx.cfg['crossref_vocab'])
    n = [0]
    tmap = {**ctx.cfg['table_map'], **ctx.cfg['appendix_table_map']} \
        if ctx.backend.uses_table_map else {}

    def sub_all(kind, make):
        nonlocal text
        for lang, pat in pats[kind]:
            text = pat.sub(lambda m, lg=lang: make(lg, m), text)

    def tab(lang, m):
        name = tmap.get(m.group(1))
        if not name:
            return m.group(0)
        n[0] += 1
        return table_ref(lang, m.group(1), name)
    sub_all('table', tab)

    bynum = figure_labels(text)

    def fig(lang, m):
        if m.group(1) not in bynum:
            return m.group(0)
        n[0] += 1
        return figure_ref(lang, m.group(1), bynum[m.group(1)])
    sub_all('figure', fig)

    def sec(lang, m):
        n[0] += 1
        return section_ref(lang, m.group(1), m.group(2))
    sub_all('section', sec)

    if n[0]:
        ctx.say(f'{tag("crossref")} ' + t('turned {n} into {n|a reference|references}', n=n[0]))
    return text
