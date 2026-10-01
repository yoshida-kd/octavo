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
from .. import crossref as xref
from .base import Backend, Ctx, missing_table
from ..i18n import t, tag
from .latex import check_assets, check_cjk


class TypstBackend(Backend):
    name = 'typst'
    label = 'Typst'
    pandoc_to = 'typst'
    ext = '.typ'
    table_ext = '.typ'
    default_figure_ext = '.pdf'
    min_pandoc = (3, 1)
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
        書誌がないので typst compile が止まる。CSL で組むときは切る。
        """
        if self.uses_citeproc(ctx) and 'citations' in pandocrun.writer_extensions('typst'):
            return 'typst-citations'
        return 'typst'

    def pandoc_args(self, ctx: Ctx) -> list:
        # A4 プリントも --standalone にしない。表紙・目次・版面は自前のテンプレート
        # （templates/handout/handout.typ）が持ち、postprocess で前後を付けて完結させる。
        # pandoc の既定テンプレートは表紙の後の改ページ・目次のページ番号・字下げなどを
        # 差し替える口がないため
        return ['-t', self.writer(ctx), '--wrap=preserve', '--top-level-division=section']

    def postprocess(self, typ: str, ctx: Ctx) -> str:
        body = super().postprocess(typ, ctx)
        if ctx.is_handout:
            return (f'// octavo build --to {self.name} が作った。手で直さない。\n'
                    + handout_meta(ctx) + '\n'
                    + ctx.template('handout/handout.typ').read_text(encoding='utf-8').rstrip()
                    + '\n\n' + crossref_rules(ctx) + '\n' + body
                    + '\n\n#context [#metadata(octavo-page-mark()) <octavo-end>]\n')
        if not ctx.standalone and re.search(r'#octavo-(?:theorem|restate)\b', body):
            # body.typ / appendix.typ は main.typ から #include されるので、main.typ の
            # import は届かない。ブロックの関数だけ自分で読む
            body = ('#import "crossref.typ": octavo-theorem, octavo-restate\n\n' + body)
        return body

    # -- 差し替え -----------------------------------------------------------
    def fmt_external_table(self, name: str, caption: str, label: str, ctx: Ctx) -> str:
        """分析が書いた表の中身（tables/<名前>.typ）を、キャプションとラベルを付けて入れる。"""
        p = ctx.table_path(name)
        if not p.is_file():
            ctx.say(f'{tag("table")} ' + missing_table(ctx, p, name))
        rel = ctx.rel(p)
        ctx.say(f'{tag("table")} {label} -> #include "{rel}"')
        return ('\n```{=typst}\n#figure(\n'
                f'  include "{rel}",\n'
                f'  caption: [{typst_escape(caption)}],\n'
                f'  kind: table,\n) <{label}>\n```\n')

    def fmt_ref(self, item, short: bool, ctx: Ctx) -> str:
        """`#ref(<label>)`。体裁（「図2.1」など）は crossref.typ の show ref が決める。

        **`@label` ではなく `#ref(<label>)` で書く。** `@label` のラベル名は非 ASCII
        でも続く限り伸びるので、「@fig-trendに示す」が存在しないラベルになる。
        この出力の中にない相手（講義のほかの回）は番号を文字で書く。
        """
        if item.label not in ctx.crossref_local:
            return xref.text_of(item, ctx.lang, short)
        sup = ', supplement: []' if short else ''
        return f'`#ref(<{item.label}>{sup})`{{=typst}}'

    # -- 回の区切り・事例などのブロック ----------------------------------------
    def fmt_session(self, attrs: dict, ctx: Ctx) -> str:
        if not ctx.is_handout:
            return ''
        title = attrs.get('title')
        tt = f', title: {typst_string(title)}' if title else ''
        return f'\n```{{=typst}}\n#octavo-session({typst_string(attrs["id"])}{tt})\n```\n'

    def fmt_appendix_start(self, ctx: Ctx) -> str:
        # A4 プリントでは付録を新しいページから始める
        brk = '#pagebreak(weak: true)\n' if ctx.is_handout else ''
        # 見出しに番号を振らないスライドでは、付録でも振らない（振ると「0.1」が出る）
        bare = ctx.backend.is_slides and not ctx.cfg['typst_slides_numbering']
        show = 'octavo-appendix.with(heading-numbering: none)' if bare else 'octavo-appendix'
        return '\n```{=typst}\n' + brk + f'#show: {show}\n```\n'

    def fmt_theorem(self, env, item, title: str, body: str, ctx: Ctx) -> str:
        """`#octavo-theorem(…)[` 本文（Markdown のまま） `] <ラベル>`。"""
        args = [f'"{env.counter or env.name}"', f'[{_content_escape(env.word)}]',
                f'lang: "{ctx.lang}"']
        if title:
            args.append(f'title: [{_content_escape(title)}]')
        if not env.counter:
            args.append('numbered: false')
        lab = f' <{item.label}>' if item is not None and item.label else ''
        return ('```{=typst}\n#octavo-theorem(' + ', '.join(args) + ')[\n```\n\n'
                + body.strip('\n') + '\n\n```{=typst}\n]' + lab + '\n```')

    def fmt_restate(self, env, item, title: str, body: str, ctx: Ctx,
                    short: bool = False) -> str:
        args = [f'word: [{_content_escape(env.word)}]', f'lang: "{ctx.lang}"']
        if item is not None:
            if item.label and item.label in ctx.crossref_local:
                args.append(f'target: <{item.label}>')
            args.append(f'number: "{item.number}"')
        if title:
            args.append(f'title: [{_content_escape(title)}]')
        if short:
            return '```{=typst}\n#octavo-restate(' + ', '.join(args + ['short: true']) + ')[]\n```'
        return ('```{=typst}\n#octavo-restate(' + ', '.join(args) + ')[\n```\n\n'
                + body.strip('\n') + '\n\n```{=typst}\n]\n```')

    def includes_appendix(self, layout: str) -> bool:
        code = '\n'.join(l.split('//', 1)[0] for l in layout.split('\n'))
        return bool(re.search(r'#include\s+"appendix\.typ"', code))

    def crossref_files(self, ctx: Ctx) -> list:
        return [('crossref.typ',
                 '// octavo build が毎回書き換える。体裁を変えるなら\n'
                 '// octavo template copy typst/crossref.typ\n\n'
                 + crossref_template(ctx)
                 + '\n#let octavo-crossref = octavo-crossref-rules.with('
                 + crossref_args(ctx) + ')\n')]

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

    # -- 投稿用にまとめ直す ---------------------------------------------------
    def flatten_assets(self, text: str) -> tuple:
        """**`//` のコメント行は見ない。**main.typ には `// #include "appendix.typ"`
        のように、使うときだけ外すコメントがあり、辿ると付録がないだけで欠落扱いになる。"""
        refs: list = []

        def quoted(m):
            refs.append(m.group('path'))
            return f"{m.group('head')}\"{Path(m.group('path')).name}\""

        out = []
        for line in text.split('\n'):
            if not line.lstrip().startswith('//'):
                line = re.sub(r'(?P<head>image\()"(?P<path>[^"]+)"', quoted, line)
                line = re.sub(r'(?P<head>(?<![\w-])#?include\s+)"(?P<path>[^"]+)"', quoted, line)
                line = re.sub(r'(?P<head>#bibliography\()"(?P<path>[^"]+)"', quoted, line)
            out.append(line)
        return '\n'.join(out), refs

    # -- 変換後 -------------------------------------------------------------
    def check(self, typ: str, ctx: Ctx) -> None:
        check_assets(ctx,
                     tables=re.findall(r'(?<![\w-])#?include "[^"]*?/?([\w.-]+)\.typ"', typ),
                     figures=re.findall(r'image\("[^"]*?/?([\w.-]+\.\w+)"', typ),
                     refs=(re.findall(r'image\("([^"]+)"', typ)
                           + re.findall(r'(?<![\w-])#?include "([^"]+)"', typ)))
        # A4 プリントは番号の体裁（crossref.typ）を頭に埋め込んでいる。その中の
        # 「図」「表」は英語の文書では組まれないので数えない
        check_cjk(typ, ctx, '.typ', t('main.typ must set a CJK font '
                                      '(check it is installed with: typst fonts)'),
                  templates=([ctx.template('typst/crossref.typ')]
                             + ([ctx.template('handout/handout.typ')] if ctx.is_handout else []))
                  if ctx.standalone else [])

    @staticmethod
    def root_arg(ctx: Ctx) -> str:
        """`typst compile --root` に渡す、out_dir から見たプロジェクトの根。

        Typst は既定で「組むファイルのあるフォルダ」より上を読ませない。body.typ は
        `../../assets/figures/…` や `../../assets/tables/…` を指すので、根を上げないと
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
                + '   ' + t('({name} lives beside the manuscript)',
                          name='main.typ'))


# ---------------------------------------------------------------- フォント
# 既定のフォントは**ここ1か所**。スライド・台本（meta_block）も A4 プリント
# （pandoc_args）もここから取る。論文の main.typ は手で持つ体裁なので、
# templates/main_*.typ に同じ並びを書いてある（変えるなら両方）。
#
#   和文: 等幅の BIZ UD（プロポーショナルの BIZ UDP は使わない）-> なければ Noto CJK
#         -> それもなければヒラギノ（macOS）・游明朝／游ゴシック（Windows。游明朝が
#            ない Windows もあるので明朝の最後にも游ゴシック）。どちらも
#            その OS に最初から入っていて、何も足していない機械で和文が豆腐に
#            ならないための最後の受け皿
#   欧文: 和文フォントの欧文字形を使わず、欧文フォントで組む
#
# 日本語の文書では欧文フォントに `covers: "latin-in-cjk"` を付ける。これで
# 英字と数字だけが欧文フォントに行き、和欧で共通の約物（「」、。など）は
# 和文フォントのまま残る。英語の文書では欧文フォントをそのまま先頭に置く。
# 候補の後ろは、その機械になければ順に落ちるための保険。
FONTS = {
    'serif': ('Libertinus Serif', ('BIZ UDMincho', 'Noto Serif CJK JP', 'Hiragino Mincho ProN',
                                   'Yu Mincho', 'Yu Gothic')),
    'sans': ('Inter', ('BIZ UDGothic', 'Noto Sans CJK JP', 'Hiragino Kaku Gothic ProN',
                       'Yu Gothic')),
}
# OS ごとの最後の受け皿（その OS に最初から入っている和文書体）。ほかの OS では
# 見えないのが当たり前なので、「書体が見えるか」を確かめるときは除く。
PLATFORM_FALLBACKS = {
    'darwin': ('Hiragino Mincho ProN', 'Hiragino Kaku Gothic ProN'),
    'win32': ('Yu Mincho', 'Yu Gothic'),
}
# 游明朝は日本語の言語機能を足したときに入る追加フォントで、英語の Windows には
# ないことがある（游ゴシックは常にある）。だから明朝の並びの最後にも游ゴシック。
OPTIONAL_FONTS = ('Yu Mincho',)


def font_expr(lang: str, kind: str, override=None) -> str:
    """Typst の `font:` に渡す並び（Typst の式の文字列）。

    `override` は設定の handout_font / typst_slides_font。文字列かリストで、
    書いてあればそれをそのまま使う（covers は付けない）。
    """
    if override:
        names = [override] if isinstance(override, str) else list(override)
        return '(' + ''.join(f'"{n}", ' for n in names) + ')'
    latin, cjk = FONTS[kind]
    first = (f'(name: "{latin}", covers: "latin-in-cjk")' if lang == 'ja'
             else f'"{latin}"')
    return '(' + first + ', ' + ''.join(f'"{n}", ' for n in cjk) + ')'


def typst_string(s: str) -> str:
    """Typst の文字列リテラル（"…"）。"""
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"') + '"'


def typst_escape(s: str) -> str:
    """pandoc を通さず直接 Typst に埋める文字列（キャプション等）だけに使う。

    `*foo*` / `_foo_` はエスケープしない — Typst でも強調として働く。
    LaTeX 側では文字どおり出るので、そこだけ見え方が変わる。
    """
    return (s.replace('\\', '\\\\').replace('#', '\\#')
             .replace('@', '\\@').replace('<', '\\<').replace('$', '\\$'))


# ---------------------------------------------------------------- 番号と参照の体裁

def crossref_template(ctx: Ctx) -> str:
    return ctx.template('typst/crossref.typ').read_text(encoding='utf-8')


def crossref_args(ctx: Ctx, section: str = 'auto') -> str:
    within = 'true' if ctx.numbering_mode() == 'section' else 'false'
    slides = 'true' if ctx.backend.is_slides else 'false'
    kinds = sorted({e.counter for e in ctx.envs.values() if e.counter})
    return (f'lang: "{ctx.lang}", within: {within}, section: {section}, '
            f'count-unnumbered: {slides}, offset: {ctx.first_section - 1}, '
            f'preset: {ctx.crossref_preset}, '
            'theorem-kinds: (' + ''.join(f'"{k}", ' for k in kinds) + ')')


def handout_meta(ctx: Ctx) -> str:
    """A4 プリントのテンプレート（handout/handout.typ）に渡す `#let octavo = (…)`。"""
    cfg = ctx.cfg
    drop = set(cfg['anonymous_drop_meta'] or ()) if ctx.anonymous else set()
    fields = []
    for k in ('title', 'subtitle', 'author', 'institute', 'date'):
        v = ctx.meta.get(k) if k not in drop else None
        if isinstance(v, (list, tuple)):
            fields.append(f'  {k}: (' + ''.join(f'[{_content_escape(str(x))}], ' for x in v) + ')')
        else:
            fields.append(f'  {k}: ' + ('none' if v in (None, '') else
                                         f'[{_content_escape(str(v))}]'))
    brk = cfg['handout_pagebreak']
    if brk == 'session':
        # 区切りがあれば区切り（いつも改ページする）、なければ `#` が回
        brk = None if ctx.has_sessions else 'section'
    main = cfg['handout_font']
    fields += [f'  lang: "{ctx.lang}"',
               # 講義ノートの本文はゴシック（BIZ UDゴシック + Inter）。線の太さが均一で、
               # 読みに困難のある読み手にも、画面で読む人にも明朝より読みやすい
               '  font: ' + font_expr(ctx.lang, 'sans', main),
               '  head-font: ' + font_expr(ctx.lang, 'sans'),
               '  bold-font: ' + font_expr(ctx.lang, 'sans'),
               f'  fontsize: {cfg["handout_fontsize"]}',
               '  toc: ' + ('true' if ctx.profile_opt('toc') else 'false'),
               f'  toc-depth: {int(cfg["toc_depth"])}',
               '  numbering: ' + ('true' if _numbers_sections(ctx) else 'false'),
               f'  first-section: {ctx.first_section}',
               '  pagebreak: ' + (f'"{brk}"' if brk else 'none')]
    return '#let octavo = (\n' + ',\n'.join(fields) + ',\n)\n'


def _numbers_sections(ctx: Ctx) -> bool:
    override = ctx.cfg.get('number_sections')
    if override is not None:
        return bool(override)
    from .base import PROFILES
    return PROFILES[ctx.profile]['number_sections']


def _content_escape(s: str) -> str:
    """`[…]` の中に置く文字列。角括弧も閉じないように逃がす。"""
    return typst_escape(s).replace('[', '\\[').replace(']', '\\]')


def crossref_rules(ctx: Ctx, section: str = 'auto') -> str:
    """文書に埋め込む形（A4 プリント・スライド）。

    スライドでは体裁のテンプレートの**後ろ**に置く。テンプレートの show heading は
    見出しを作り直す（`it` を返さない）ので、先にあると節を数える処理まで届かない。
    """
    return (crossref_template(ctx)
            + f'\n#show: octavo-crossref-rules.with({crossref_args(ctx, section)})\n')
