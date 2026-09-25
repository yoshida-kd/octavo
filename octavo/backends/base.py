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
from .. import crossref as xref
from ..i18n import t, tag
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
    # 相互参照: ラベル -> crossref.Item（この原稿と、付録／ほかの回の分も）。
    # local は、この出力の中で組版側が参照を張れるラベル（論文なら本文と付録）
    crossrefs: dict = field(default_factory=dict)
    crossref_local: set = field(default_factory=set)
    crossref_section: int | None = None             # 講義の回ごとのデッキの節番号
    math_macros: list = field(default_factory=list)  # 数式のマクロの定義（本文と付録から）

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
        if not self.backend.numbers_itself:
            return False           # 番号はマークダウン段階で入れてある
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
    def lang(self) -> str:
        return self.meta.get('lang_short') or self.cfg['lang']

    # -- パス ---------------------------------------------------------------
    def rel(self, p: Path) -> str:
        return relpath(p, self.out_dir)

    def figure_target(self, path: str) -> str:
        """原稿の図のパス（out_dir からの相対に直したもの）を、この形式の拡張子に。

        figures/ の中の図だけ付け替える（ov_figure は .pdf と .png の両方を書く。
        LaTeX は .pdf、ほかは .png）。URL や figures/ の外の図はそのまま。
        """
        bare = path[1:-1] if path.startswith('<') else path
        if '://' in bare or bare.startswith(('data:', '#')):
            return path
        p = (self.out_dir / bare).resolve()
        if p.parent != Path(self.cfg['figure_dir']).resolve():
            return path
        return self.rel(p.with_suffix(self.backend.figure_ext(self.cfg)))

    def table_path(self, name: str, ext: str | None = None) -> Path:
        return self.cfg['table_dir'] / f'{name}{ext or self.backend.table_ext}'

    def numbering_mode(self) -> str:
        return self.cfg['crossref_numbering']

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
    # 図表・式・節の番号を組版側が振るか（LaTeX/Typst は振る）。振らない形式（Word）は
    # Octavo が数えて、見出し・キャプション・式・参照に文字で入れる
    numbers_itself = True
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
    def fmt_figure(self, m: re.Match, label: str | None, ctx: Ctx) -> str:
        """段落に1つだけの画像（crossref.IMAGE）。既定は画像リンクのまま pandoc に
        図にさせる（ラベルもキャプションの書式もそのまま渡る）。拡張子を形式に
        合わせ、幅の指定が無ければ figure_width を足す。"""
        attr = (m.group('attr') or '').strip()
        if 'width=' not in attr:
            w = int(float(ctx.cfg['figure_width']) * 100)
            attr = f'{attr} width={w}%'.strip()
        path = ctx.figure_target(m.group('path'))
        ctx.say(f'{tag("figure")} {label or m.group("alt")[:30] or "-"} -> {path}')
        return f'![{m.group("alt")}]({path}{m.group("title") or ""}){{{attr}}}'

    def fmt_external_table(self, name: str, caption: str, label: str, ctx: Ctx) -> str:
        """分析が書いた表（tables/<名前>）を差し込む。既定は Markdown 版（.md）を
        本文の表として入れ、キャプションを付ける（Word はこれ）。"""
        p = ctx.table_path(name, '.md')     # Word など、.typ も .tex も読めない形式
        if not p.is_file():
            ctx.say(f'{tag("table")} ' + t('{path} is missing (octavo analysis run, or '
                                           'ov_table() in the .qmd)', path=ctx.cfg.rel(p)))
            return f'**[{name}.md ?]**\n\n: {caption} {{#{label}}}'
        ctx.say(f'{tag("table")} {label} -> {ctx.cfg.rel(p)}')
        return p.read_text(encoding='utf-8').strip() + f'\n\n: {caption} {{#{label}}}'

    def fmt_ref(self, item: 'xref.Item', short: bool, ctx: Ctx) -> str:
        """本文の `@fig-…`。既定は番号を文字で書く（組版側が番号を振らない形式）。"""
        return xref.text_of(item, ctx.lang, short)

    def includes_appendix(self, layout: str) -> bool:
        """体裁のファイル（main.*）が付録を実際に読み込んでいるか（コメント行は数えない）。

        読み込んでいれば本文と付録は1つの文書なので、互いの参照を組版側が張れる。
        そうでなければ（Word は本文と付録が別のファイル）番号を文字で書く。"""
        return False

    def crossref_files(self, ctx: Ctx) -> list:
        """main.* 方式のとき out_dir に書く、番号と参照の体裁のファイル [(名前, 中身)]。"""
        return []

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
