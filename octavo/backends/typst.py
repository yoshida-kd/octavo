# -*- coding: utf-8 -*-
"""Typst バックエンド（pandoc 3.1 以上が要る）。

引用の扱いは config の `typst_citations` で決まる。

  'csl'（既定）   pandoc --citeproc が CSL で解決した地の文を出す。他のバックエンドと
                 **同じ書式**になる。main.typ 側に bibliography() は書かない
  'native'       Typst の #cite() をそのまま出し、書誌は main.typ の
                 bibliography("literature.bib", style: …) に任せる。Typst の
                 スタイル名（"apa" 等）や CSL ファイルを Typst 側で指定する

表・図・poscite の差し替えは必ず raw block（```{=typst}）か raw span で包む。
素のテキストで挿入すると pandoc の smart 拡張が `"` を曲線引用符に変えて
Typst の文字列リテラルを壊す。
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from .. import pandocrun
from .base import Backend, Ctx, apply_crossrefs
from ..i18n import t, tag
from .latex import check_assets, check_cjk


class TypstBackend(Backend):
    name = 'typst'
    label = 'Typst'
    pandoc_to = 'typst'
    ext = '.typ'
    table_ext = '.typ'
    default_figure_ext = '.png'
    min_pandoc = (3, 1)
    uses_table_map = True
    auto_numbers_captions = True
    wants_abstract_file = True      # main.typ が #include "abstract.typ" で受ける
    anonymous_guard = '#if anonymous'
    main_name = 'main.typ'

    def input_extras(self) -> tuple:
        return ('raw_attribute',)

    def uses_citeproc(self, ctx: Ctx) -> bool:
        return ctx.cfg['typst_citations'] == 'csl'

    def writer(self, ctx: Ctx) -> str:
        """pandoc の `-t`。

        新しい pandoc は --citeproc で組んだ引用も Typst の #cite(<key>) で出す
        （citations 拡張が既定で有効）。それだと CSL の書式が捨てられ、main.typ に
        書誌が無いので typst compile が止まる。CSL で組むときは切る。
        """
        if self.uses_citeproc(ctx) and 'citations' in pandocrun.writer_extensions('typst'):
            return 'typst-citations'
        return 'typst'

    def pandoc_args(self, ctx: Ctx) -> list:
        args = ['-t', self.writer(ctx), '--wrap=preserve', '--top-level-division=section']
        if ctx.standalone:
            # pandoc の Typst テンプレートは mainfont を**1つしか**受け取らないので、
            # 候補の並び（欧文と和文を分ける covers を含む）は前置きの #set で渡す。
            # mainfont を渡さなければテンプレートは font を上書きしない。
            font = font_expr(ctx.lang, 'serif', ctx.cfg['typst_mainfont'])
            args += ['--standalone', '-V', f'header-includes=#set text(font: {font})']
            if ctx.profile_opt('toc'):
                args += ['--toc', f'--toc-depth={ctx.cfg["toc_depth"]}']
        if ctx.profile_opt('number_sections'):
            args += ['--number-sections']
        return args

    # -- 差し替え -----------------------------------------------------------
    def fmt_table(self, m: re.Match, name, ctx: Ctx) -> str:
        if not name:
            return self.markdown_table(m, ctx)
        rel = ctx.rel(ctx.table_path(name))
        ctx.say(f'{tag("table")} {m.group("num")} -> #include "{rel}"  '
                f'«{m.group("cap").strip()[:40]}»')
        return f'\n```{{=typst}}\n#include "{rel}"\n```\n'

    def fmt_figure(self, m: re.Match, ctx: Ctx) -> str:
        f, num = m.group('file'), m.group('num')
        cap = ' '.join(m.group('cap').split())
        rel = ctx.rel(ctx.figure_path(f))
        ctx.say(f'{tag("figure")} {num} -> {rel}')
        w = int(float(ctx.cfg['figure_width']) * 100)
        return ('\n```{=typst}\n#figure(\n'
                f'  image("{rel}", width: {w}%),\n'
                f'  caption: [{typst_escape(cap)}],\n'
                f') <fig:{f}>\n```\n')

    def fmt_poscite(self, key: str, ctx: Ctx) -> str:
        if self.uses_citeproc(ctx):
            return super().fmt_poscite(key, ctx)
        return (f'`#cite(<{key}>, form: "author")\'s '
                f'(#cite(<{key}>, form: "year"))`{{=typst}}')

    def uses_anonymous_guard(self, text: str) -> bool:
        code = '\n'.join(l.split('//', 1)[0] for l in text.split('\n'))
        return bool(re.search(r'#if\s+anonymous\b', code))

    def flags(self, ctx: Ctx) -> tuple:
        return ('flags.typ',
                '// octavo build が毎回書き換える。手で直さない。\n'
                f'#let anonymous = {"true" if ctx.anonymous else "false"}\n')

    # -- 投稿用に固め直す ---------------------------------------------------
    def flatten_assets(self, text: str) -> tuple:
        """**`//` のコメント行は見ない。**main.typ には `// #include "appendix.typ"`
        のように、使うときだけ外すコメントがあり、辿ると付録が無いだけで欠落扱いになる。"""
        refs: list = []

        def quoted(m):
            refs.append(m.group('path'))
            return f"{m.group('head')}\"{Path(m.group('path')).name}\""

        out = []
        for line in text.split('\n'):
            if not line.lstrip().startswith('//'):
                line = re.sub(r'(?P<head>image\()"(?P<path>[^"]+)"', quoted, line)
                line = re.sub(r'(?P<head>#include\s+)"(?P<path>[^"]+)"', quoted, line)
                line = re.sub(r'(?P<head>#bibliography\()"(?P<path>[^"]+)"', quoted, line)
            out.append(line)
        return '\n'.join(out), refs

    # -- 変換後 -------------------------------------------------------------
    def crossrefs(self, typ: str, ctx: Ctx) -> str:
        def figure_labels(text):
            out = {}
            for f in re.findall(r'<fig:([\w.-]+)>', text):
                m = re.match(r'fig([A-Z]?\d+)[_-]', f)
                if m:
                    out[m.group(1)] = f
            return out

        # Typst は参照だけで「図1」「Figure 1」に整形する（supplement）ので、
        # LaTeX と違って「図」「Table」を自分では付けない。
        #
        # **`@label` ではなく `#ref(<label>)` で書く。** `@label` のラベル名は
        # 非 ASCII でも続く限り伸びるので、「@fig:fig1_trendに示す」が
        # `<fig:fig1_trendに示す>` という存在しないラベルになって組版が止まる。
        # 日本語では参照の直後に助詞が来るのがふつうなので、これは例外ではない。
        # `#ref(…)` は閉じ括弧で必ず終わる。
        return apply_crossrefs(
            typ, ctx,
            table_ref=lambda lg, num, name: f'#ref(<{name}>)',
            figure_ref=lambda lg, num, lab: f'#ref(<fig:{lab}>)',
            section_ref=lambda lg, a, b: f'#ref(<sec:{a}{"-" + b if b else ""}>)',
            figure_labels=figure_labels)

    def check(self, typ: str, ctx: Ctx) -> None:
        check_assets(ctx,
                     tables=re.findall(r'#include "[^"]*?/?([\w.-]+)\.typ"', typ),
                     figures=re.findall(r'image\("[^"]*?/?([\w.-]+\.\w+)"', typ),
                     refs=(re.findall(r'image\("([^"]+)"', typ)
                           + re.findall(r'#include "([^"]+)"', typ)))
        check_cjk(typ, ctx, '.typ', t('main.typ must set a CJK font '
                                      '(check it is installed with: typst fonts)'))

    @staticmethod
    def root_arg(ctx: Ctx) -> str:
        """`typst compile --root` に渡す、out_dir から見たプロジェクトの根。

        Typst は既定で「組むファイルのあるフォルダ」より上を読ませない。body.typ は
        `../../figures/…` や `../../tables/…` を指すので、根を上げないと
        「access denied」で止まる。図・表の置き場が根の外に設定されていても届くよう、
        共通の祖先を取る。

        比べるのは**リンクを解いた実体どうし**。片方だけ解くと、macOS の
        /var（実体は /private/var）やリンクを挟んだフォルダで共通の祖先が / まで
        上がり、根がディスク全体になってしまう。
        """
        dirs = [ctx.cfg.root, ctx.out_dir, Path(ctx.cfg['figure_dir']),
                Path(ctx.cfg['table_dir'])]
        common = os.path.commonpath([str(Path(d).resolve()) for d in dirs])
        return Path(os.path.relpath(common, Path(ctx.out_dir).resolve())).as_posix()

    def compile(self, ctx: Ctx, path: Path) -> list:
        return ['typst', 'compile', '--root', self.root_arg(ctx), path.name]

    def compile_main(self, ctx: Ctx) -> Path | None:
        main = ctx.out_dir / 'main.typ'
        return main if main.is_file() else None

    def next_step(self, ctx: Ctx) -> str:
        if ctx.standalone:
            return (f'cd {ctx.out_dir} && typst compile --root {self.root_arg(ctx)} '
                    f'{self.out_name(ctx)}')
        return (f'cd {ctx.out_dir} && typst compile --root {self.root_arg(ctx)} main.typ'
                + '   ' + t('({name} lives beside the manuscript; octavo new writes it if missing)',
                          name='main.typ'))


# ---------------------------------------------------------------- フォント
# 既定のフォントは**ここ1か所**。スライド・台本（meta_block）も A4 プリント
# （pandoc_args）もここから取る。論文の main.typ は手で持つ体裁なので、
# templates/main_*.typ に同じ並びを書いてある（変えるなら両方）。
#
#   和文: 等幅の BIZ UD（プロポーショナルの BIZ UDP は使わない）-> 無ければ Noto CJK
#         -> それも無ければヒラギノ（macOS に最初から入っている。何も足していない
#            Mac で和文が豆腐にならないための最後の受け皿）
#   欧文: 和文フォントの欧文字形を使わず、欧文フォントで組む
#
# 日本語の文書では欧文フォントに `covers: "latin-in-cjk"` を付ける。これで
# 英字と数字だけが欧文フォントに行き、和欧で共通の約物（「」、。など）は
# 和文フォントのまま残る。英語の文書では欧文フォントをそのまま先頭に置く。
# 候補の後ろは、その機械に無ければ順に落ちるための保険。
FONTS = {
    'serif': ('Libertinus Serif', ('BIZ UDMincho', 'Noto Serif CJK JP', 'Hiragino Mincho ProN')),
    'sans': ('Inter', ('BIZ UDGothic', 'Noto Sans CJK JP', 'Hiragino Kaku Gothic ProN')),
}


def font_expr(lang: str, kind: str, override=None) -> str:
    """Typst の `font:` に渡す並び（Typst の式の文字列）。

    `override` は設定の typst_mainfont / typst_slides_font。文字列かリストで、
    書いてあればそれをそのまま使う（covers は付けない）。
    """
    if override:
        names = [override] if isinstance(override, str) else list(override)
        return '(' + ''.join(f'"{n}", ' for n in names) + ')'
    latin, cjk = FONTS[kind]
    first = (f'(name: "{latin}", covers: "latin-in-cjk")' if lang == 'ja'
             else f'"{latin}"')
    return '(' + first + ', ' + ''.join(f'"{n}", ' for n in cjk) + ')'


def typst_escape(s: str) -> str:
    """pandoc を通さず直接 Typst に埋める文字列（キャプション等）だけに使う。

    `*foo*` / `_foo_` はエスケープしない — Typst でも強調として働く。
    LaTeX 側では文字どおり出るので、そこだけ見え方が変わる。
    """
    return (s.replace('\\', '\\\\').replace('#', '\\#')
             .replace('@', '\\@').replace('<', '\\<').replace('$', '\\$'))
