# -*- coding: utf-8 -*-
"""octavo.config.py を読み込み、既定値を埋め、パスを絶対パスに解決する。

設定ファイルが生の Python 辞書なのは、YAML パーサ（PyYAML）への依存を避けるため。
octavo は標準ライブラリと pandoc だけで動く。

**文書（documents）** という単位で「どの原稿を、どの用途（profile）で、どの形式に
出すか」を決める。`octavo init` が作る設定は、種類ごとのフォルダをグロブで登録する
（papers/*/paper.md・slides/*.md・lectures/*.md）ので、`octavo new` で原稿を足しても
設定を書き換えなくてよい。documents を書かなければ draft.md / slides.md /
handout.md があればそれぞれ paper / slides / handout として登録される。
"""
from __future__ import annotations

import importlib.util
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from . import paths
from .i18n import t

BACKENDS = ('latex', 'typst', 'beamer', 'typst-slides', 'typst-notes', 'docx')
PROFILES = ('paper', 'handout', 'slides')

# --------------------------------------------------------------------------
# 既定値。ここに無いキーを octavo.config.py に書くと警告する（誤字よけ）。
# --------------------------------------------------------------------------
DEFAULTS: dict = {
    # ---- 原稿（documents を書かないときの手軽な指定）----------------------
    'draft': 'draft.md',           # 論文本文
    'appendix': None,              # 付録（使わないなら None）
    'slides': 'slides.md',         # 発表スライドの原稿（無ければ登録されない）
    'handout': 'handout.md',       # 授業用 A4 プリント（同上）

    # ---- 文書の定義（細かく決めたいときはこちら）--------------------------
    # {'講義1': {'src': 'lecture1.md', 'profile': 'handout',
    #            'targets': ['typst', 'beamer']}}
    # profile: 'paper' | 'handout' | 'slides'
    # 同じ原稿から A4 プリントとスライドを作るなら targets に両方書く。
    # src にグロブを書くと、当たった原稿がそれぞれ1つの文書になる（名前は `*` に
    # 当たった部分）。'split_slides': True なら、スライドは `#` 見出しごとに分ける。
    'documents': {},

    # ---- 出力先 -----------------------------------------------------------
    'out_dirs': {
        'latex': 'build/latex',
        'typst': 'build/typst',
        'beamer': 'build/slides',
        'typst-slides': 'build/typst-slides',
        'typst-notes': 'build/typst-notes',
        'docx': 'build/word',
    },

    # ---- 表・図 -----------------------------------------------------------
    # 分析スクリプトが表を .tex / .typ で直接吐く運用のときだけ使う。
    # 「本文の表番号」->「tables/ 内のファイル名（拡張子なし）」。
    # Word / スライドは外部 .tex を取り込めないので、対応があっても
    # マークダウンの表をそのまま使う。
    'table_map': {},
    'appendix_table_map': {},
    'table_dir': 'tables',
    'figure_dir': 'figures',
    # 形式ごとに使う図の拡張子。書かなければ latex/beamer=.pdf、他=.png
    'figure_ext': {},
    'figure_width': 1.0,           # \textwidth に対する比

    # ---- 分析（Quarto の .qmd）-------------------------------------------
    # 論文に出す数値・図・表を作る .qmd。グロブが使える。
    #   'analysis': ['analysis/*.qmd'],
    # データの更新も見張るなら、要素を辞書にして deps を書く。
    #   'analysis': [{'src': 'analysis/main.qmd', 'deps': ['data/*.csv']}],
    'analysis': [],
    'analysis_deps': [],           # 全部の .qmd に共通の依存（データ等）
    'analysis_to': None,           # quarto render --to（None なら .qmd 任せ）
    'analysis_args': [],           # quarto に渡す追加の引数
    'analysis_auto': True,         # octavo build のとき、古ければ自動で走らせる

    # ---- 分析が出した数値（本文の {{…}}）---------------------------------
    'results_dir': 'results',      # 値マニフェスト（*.json）の置き場
    'value_float_format': '.3f',   # 小数の既定書式（{{key:.2f}} が優先）
    'value_thousands_sep': True,   # 整数に桁区切りを入れる（1,523）
    # octavo lint が「直書きされた結果」と見なさない文字列。慣例的な定数
    #（0.05 / 1.96 等）は既定で見逃すので、それ以外を足すときだけ書く。
    'lint_accepted': [],           # 例: ['0.5', '2.5']

    # ---- 投稿規定（octavo check が突き合わせる。None なら見ない）----------
    'word_limit': None,            # 本文の語数の上限（例: 8000）
    'char_limit': None,            # 本文の文字数の上限（日本語の雑誌）
    'abstract_word_limit': None,   # 要旨の語数の上限（例: 150）
    'abstract_char_limit': None,   # 要旨の文字数の上限（例: 400）

    # ---- 匿名審査 ---------------------------------------------------------
    # octavo build --anonymous / octavo bundle --anonymous のときだけ効く。
    # 原稿側は ::: {.no-anonymous} … ::: で謝辞などを囲む。
    # 題扉から伏せるメタデータ:
    'anonymous_drop_meta': ['author', 'institute', 'thanks', 'email'],

    # ---- 複製パッケージ（octavo bundle --replication）----------------------
    # 入れないもの（グロブ）。原データは既定で入れない（--with-raw-data で入る）
    'replication_exclude': [],

    # ---- 書誌 -------------------------------------------------------------
    'bib_file': 'literature.bib',  # Zotero からの書き出し（正本、1ファイル）
    # 雑誌に合わせた書式。CSL スタイル ID（'apa', 'ieee',
    # 'modern-language-association' …）か .csl へのパス。
    # ID を書くと Zotero スタイルリポジトリから取得してキャッシュする。
    'csl': 'chicago-author-date',
    'csl_locale': None,            # 'ja-JP' 等。None なら lang から決める
    # 書誌一覧の直前に入れる見出し。None なら lang に応じた既定
    #（日本語なら「参考文献」、英語なら "References"）。'' なら見出し無し。
    'reference_section_title': None,
    'link_citations': True,        # 引用から書誌一覧へリンクを張る
    # スライドの末尾に書誌一覧を出すか。既定は出さない（枠に入らないため）。
    # 出すなら slides.md の末尾に「## 参考文献」と `::: {#refs}\n:::` を置く。
    'slides_bibliography': False,
    'poscite_lang': None,          # \poscite の言語。None なら lang
    'typst_citations': 'csl',      # 'csl' | 'native'
    'bib_accepted': {},            # {('key','no page range or DOI'): '理由'}（日本語の文言でも可）

    # ---- 言語・語彙 -------------------------------------------------------
    'lang': 'ja',                  # 'ja' | 'en'
    'crossref_vocab': 'both',      # 'ja' | 'en' | 'both'
    'east_asian_line_breaks': True,

    # ---- 見出し・目次（profile の既定を上書きしたいときだけ）--------------
    'toc': None,                   # None なら profile 任せ
    'number_sections': None,       # 同上
    'toc_depth': 2,

    # ---- メタデータ -------------------------------------------------------
    # 原稿の YAML front matter が優先。ここは既定値。
    'meta': {},                    # {'title':…, 'author':…, 'institute':…, 'date':…}

    # ---- 事例・論点・注意等の div ------------------------------------------
    # {'case': '事例', 'question': '論点', 'nb': '注意', 'memo': '付記'} のように
    # 書くと、`::: {.case #case:example} ... :::` が latex 出力では
    # \newtheorem 環境（ヘッダー側に \newtheorem{case}{事例}[section] が要る。
    # octavo template copy handout/handout-header.tex で写して足す）に、それ以外の形式では
    # 通し番号無しの「**事例.** …」に変換される。空なら何もしない。
    'theorem_envs': {},

    # ---- LaTeX ------------------------------------------------------------
    'latex_engine': 'lualatex',
    'latex_documentclass': None,   # None なら lang から（ja: ltjsarticle）
    'latex_classoptions': ['a4paper'],
    'latex_fontsize': '11pt',

    # ---- Typst ------------------------------------------------------------
    'typst_mainfont': None,        # A4 プリントの本文フォント。None なら typst.FONTS の serif

    # ---- Typst スライド（TeX 無しで組むスライド）--------------------------
    'typst_slides_aspect': '16-9',  # '16-9' | '4-3'
    # スライドの見出しに番号を振る。Typst の numbering 文字列（'1.' や '1.1'）。
    # None なら振らない（既定）。'1.1' は「#」の節と「##」の枚の2段が要る。
    'typst_slides_numbering': None,
    # 「#」の節を扉のスライドにするか。False なら扉を出さず、番号を進めるだけ
    # （節で区切りたいが枚数は増やしたくないとき）。
    'typst_slides_section_slides': True,
    # 差し色。'#0e2f92' のような16進。題・箇条書きの印・罫に使う。
    # None なら色を使わない（黒のまま）。既定は海の青（#25 で入れた「差し色を
    # 設定したときだけ体裁が変わる」ゲートにより、None にすればいつでも従来
    # どおりの黒一色に戻せる）。
    'typst_slides_accent': '#0e2f92',
    # 各スライドの左上に、いまの「#」の節を小さく出すか（既定は出さない）。
    'typst_slides_running_header': True,   # 左上にいまの節（無ければデッキの題）
    'typst_slides_font': None,      # None なら typst.FONTS の sans（BIZ UDGothic + Inter）

    # ---- Beamer -----------------------------------------------------------
    'beamer_theme': 'default',     # 'metropolis' 等（TeX Live に入っているもの）
    'beamer_colortheme': None,
    'beamer_fonttheme': None,
    'beamer_aspectratio': '169',   # '169' | '43'
    'beamer_slide_level': 2,       # '## 見出し' を1枚のスライドにする
    'beamer_classoptions': [],
    'beamer_notes': False,         # 発表者ノートを本体に刷り込む
    'beamer_toc': False,
    'beamer_figure_captions': False,
    'beamer_warn_lines': 28,       # 1枚が何行を超えたら「溢れそう」と言うか

    # ---- Word -------------------------------------------------------------
    'docx_reference': None,        # 見た目の雛形 .docx（--reference-doc）
    'docx_track_changes_ready': True,
}

PATH_KEYS = ('draft', 'appendix', 'slides', 'handout', 'table_dir', 'figure_dir',
             'results_dir', 'bib_file', 'docx_reference')


@dataclass
class Document:
    """1本の原稿と、その出し方。"""
    name: str
    src: Path
    profile: str = 'paper'
    targets: tuple = ('typst',)
    appendix: Path | None = None
    out: Path | None = None                 # 形式別 out_dirs を上書きする
    meta: dict = field(default_factory=dict)
    # スライドを `#` 見出しごとに別々に組むか（講義ノート1本 -> 回ごとのスライド）
    split_slides: bool = False
    # 分けたうちの1つなら、その回の印（'01' か見出しの {#id}）
    part: str | None = None

    def exists(self) -> bool:
        return self.src.is_file()


class Config:
    def __init__(self, root: Path, values: dict, source: Path | None = None):
        self.root = root
        self.source = source
        # 設定ファイルに**書いてある**鍵（既定のままのものとの区別。octavo config が使う）
        self.explicit = frozenset(values)
        unknown = sorted(set(values) - set(DEFAULTS))
        if unknown:
            print(t('warning: unknown keys in the config (ignored): {keys}',
                    keys=', '.join(unknown)), file=sys.stderr)

        v = {**DEFAULTS, **values}
        for k in ('out_dirs', 'figure_ext', 'meta', 'theorem_envs'):
            v[k] = {**DEFAULTS[k], **(values.get(k) or {})}

        for k in PATH_KEYS:
            if v.get(k) is not None:
                v[k] = (root / v[k]).resolve()
        v['out_dirs'] = {k: (root / p).resolve() for k, p in v['out_dirs'].items()}

        if v['latex_documentclass'] is None:
            v['latex_documentclass'] = 'ltjsarticle' if v['lang'] == 'ja' else 'article'
        if v['csl_locale'] is None:
            v['csl_locale'] = 'ja-JP' if v['lang'] == 'ja' else 'en-US'
        if v['reference_section_title'] is None:
            v['reference_section_title'] = '参考文献' if v['lang'] == 'ja' else 'References'

        self._v = v
        self._validate()
        self.documents = self._build_documents(values.get('documents') or {})

    # -- 参照 ---------------------------------------------------------------
    def __getitem__(self, k):
        return self._v[k]

    def __contains__(self, k):
        return k in self._v

    def get(self, k, default=None):
        return self._v.get(k, default)

    def out_dir(self, backend: str, doc: Document | None = None) -> Path:
        """出力先。main.* 方式（論文を完結させずに組む形式）は文書ごとにフォルダを分ける。

        main.typ / body.typ / abstract.typ は名前が決まっているので、論文が2本
        あると同じフォルダでは上書きし合う。完結した文書（プリント・スライド・
        Word）はファイル名が文書名なので、形式ごとの1フォルダに並べてよい。
        """
        if doc is not None and doc.out is not None:
            return doc.out
        base = self._v['out_dirs'][backend]
        if doc is not None and doc.profile == 'paper':
            from . import backends as be
            if not be.get(backend).always_standalone:
                return base / doc.name
        return base

    def sources(self) -> list:
        """原稿を横断して見るコマンド用に (文書名, パス, 付録か) を並べる。

        1つの文書が原稿と付録の**2ファイル**を持つことがあるので、
        checkbib / values / outline はここを通す。付録を数え落とす事故を
        1箇所で防ぐため（実際に octavo values が落としていた）。
        存在しないファイルは返さない。
        """
        out = []
        for name, d in self.documents.items():
            out.append((name, Path(d.src), False))
            if d.appendix:
                out.append((name, Path(d.appendix), True))
        return [(n, p, a) for n, p, a in out if p.is_file()]

    def rel(self, p: Path) -> str:
        """表示用のパス。論文はどれも paper.md なので、ファイル名だけでは区別できない。"""
        try:
            return Path(p).relative_to(self.root).as_posix()
        except ValueError:
            return str(p)

    def document(self, name: str) -> Document:
        """名前から文書を引く。`講義ノート-03` のような、分けたスライドの1回分も引ける。"""
        if name in self.documents:
            return self.documents[name]
        for d in self.documents.values():
            if d.split_slides and name.startswith(d.name + '-'):
                for part in self.parts(d):
                    if part.name == name:
                        return part
        raise SystemExit(t('no document called {name}', name=name) + '\n  '
                         + t('documents: {names}',
                             names=', '.join(self.documents) or t('(none)'))
                         + ('' if self.documents else '\n  ' + t(
                             'to add a manuscript: octavo new paper|slides|lecture <name>')))

    def parts(self, doc: Document) -> list:
        """`split_slides` の文書を `#` 見出しごとの文書に分ける（読むのは原稿の見出しだけ）。"""
        from . import md as mdlib
        if not doc.src.is_file():
            return []
        out = []
        for key, _title in mdlib.section_keys(mdlib.read(doc.src)):
            out.append(Document(name=f'{doc.name}-{key}', src=doc.src,
                                profile=doc.profile, targets=doc.targets,
                                out=doc.out, meta=dict(doc.meta), part=key))
        return out

    # -- 文書の組み立て -----------------------------------------------------
    def _build_documents(self, spec: dict) -> dict:
        docs: dict = {}
        if spec:
            for name, d in spec.items():
                if not isinstance(d, dict) or 'src' not in d:
                    sys.exit(t("documents['{name}'] needs at least 'src'", name=name))
                prof = d.get('profile', 'paper')
                if prof not in PROFILES:
                    sys.exit(t("documents['{name}'] has a bad profile: {got} "
                               '(one of {allowed})',
                               name=name, got=repr(prof), allowed='/'.join(PROFILES)))
                bad = [x for x in d.get('targets', ['typst'])
                       if x not in BACKENDS]
                if bad:
                    sys.exit(t("documents['{name}'] has bad targets: {bad}",
                               name=name, bad=', '.join(bad)))
                ap = d.get('appendix')
                common = dict(
                    profile=prof,
                    targets=tuple(d.get('targets', ['typst'])),
                    out=(self.root / d['out']).resolve() if d.get('out') else None,
                    meta=dict(d.get('meta') or {}),
                    split_slides=bool(d.get('split_slides', False)),
                )

                def add(nm: str, src: Path, appendix: Path | None) -> None:
                    if nm in docs:
                        sys.exit(t('two documents share the name {name}', name=nm)
                                 + f'\n  {docs[nm].src}\n  {src}\n  '
                                 + t('rename one of the manuscripts (or its folder)'))
                    docs[nm] = Document(name=nm, src=src, appendix=appendix, **common)

                # src にワイルドカードが使える。同じ扱いの原稿がたくさんある
                # （スライド10本、論文が数本）場合、1つ書けば全部登録される。
                #   'スライド': {'src': 'slides/*.md', …}        -> example-talk, …
                #   '論文': {'src': 'papers/*/paper.md',
                #            'appendix': 'papers/*/appendix.md', …} -> フォルダ名
                #   '講義*': {'src': 'lectures/*.md', …}          -> 講義lecture01, …
                # 文書名は最初の `*` に当たった部分（名前に * があればそこに差し込む）。
                # 何も当たらないのは「その種類の原稿がまだ無い」だけなので黙っている。
                if any(c in d['src'] for c in '*?['):
                    for p in sorted(self.root.glob(d['src'])):
                        stars = glob_captures(d['src'], p.relative_to(self.root))
                        stem = stars[0] if stars else p.stem
                        nm = name.replace('*', stem) if '*' in name else stem
                        apx = None
                        if ap:
                            cand = self.root / fill_stars(ap, stars)
                            apx = cand.resolve() if cand.is_file() or '*' not in ap else None
                        add(nm, p.resolve(), apx)
                else:
                    add(name, (self.root / d['src']).resolve(),
                        (self.root / ap).resolve() if ap else None)
            return docs

        # documents を書いていないときは draft/slides/handout から作る
        v = self._v
        if v['draft'] and Path(v['draft']).is_file():
            docs['paper'] = Document('paper', v['draft'], 'paper',
                                     ('typst',), v['appendix'])
        if v['slides'] and Path(v['slides']).is_file():
            docs['slides'] = Document('slides', v['slides'], 'slides', ('typst-slides',))
        if v['handout'] and Path(v['handout']).is_file():
            docs['handout'] = Document('handout', v['handout'], 'handout', ('typst',))
        if not docs and v['draft']:
            docs['paper'] = Document('paper', v['draft'], 'paper',
                                     ('typst',), v['appendix'])
        return docs

    # -- 検査 ---------------------------------------------------------------
    def _validate(self) -> None:
        v = self._v
        def bad(k, allowed):
            sys.exit(t('{key} must be {allowed} (got {got})',
                       key=k, allowed=allowed, got=repr(v[k])))
        if v['lang'] not in ('ja', 'en'):
            bad('lang', t("'ja' or 'en'"))
        if v['crossref_vocab'] not in ('ja', 'en', 'both'):
            bad('crossref_vocab', "'ja'/'en'/'both'")
        if v['typst_citations'] not in ('csl', 'native'):
            bad('typst_citations', t("'csl' or 'native'"))
        if v['typst_slides_aspect'] not in ('16-9', '4-3'):
            bad('typst_slides_aspect', t("'16-9' or '4-3'"))
        if v['typst_slides_numbering'] is not None and not isinstance(v['typst_slides_numbering'], str):
            bad('typst_slides_numbering',
                t("a Typst numbering string ('1.' and the like) or None"))
        acc = v['typst_slides_accent']
        if acc is not None and not (isinstance(acc, str)
                                    and re.fullmatch(r'#[0-9A-Fa-f]{6}', acc)):
            bad('typst_slides_accent', t("a hex colour like '#0e2f92', or None"))
        unknown = sorted(set(v['out_dirs']) - set(BACKENDS))
        if unknown:
            sys.exit(t('unknown formats in out_dirs: {names}', names=', '.join(unknown)))
        unknown = sorted(set(v['figure_ext']) - set(BACKENDS))
        if unknown:
            sys.exit(t('unknown formats in figure_ext: {names}', names=', '.join(unknown)))
        for k in ('analysis', 'analysis_deps', 'analysis_args',
                  'lint_accepted', 'anonymous_drop_meta', 'replication_exclude'):
            if not isinstance(v[k], (list, tuple)):
                sys.exit(t('{key} must be a list (got {got})', key=k, got=repr(v[k])))

    def describe(self) -> str:
        v = self._v
        docs = ', '.join(f'{d.name}({d.profile})' for d in self.documents.values())
        return (t('documents') + f' [{docs}] / ' + t('bib') + f' {Path(v["bib_file"]).name} / '
                f'CSL {v["csl"]} / lang {v["lang"]}')


def glob_captures(pattern: str, rel: Path) -> list:
    """グロブの `*` が、実際のパスのどこに当たったかを並べる。

    `papers/*/paper.md` と `papers/example-paper/paper.md` なら ['example-paper']。`**` は扱わない。
    """
    rx = ''.join('([^/]*)' if c == '*' else '[^/]' if c == '?' else re.escape(c)
                 for c in pattern)
    m = re.fullmatch(rx, rel.as_posix())
    return list(m.groups()) if m else []


def fill_stars(pattern: str, stars: list) -> str:
    """`papers/*/appendix.md` の `*` を、src のグロブで当たった部分で順に埋める。"""
    it = iter(stars)
    return re.sub(r'\*', lambda _: next(it, '*'), pattern)


def load(path: str | Path = 'octavo.config.py') -> Config:
    p = Path(path).resolve()
    if p.is_dir():
        p = p / 'octavo.config.py'
    if not p.exists():
        # 旧名（Galley / Galleykit）のころのプロジェクト。読みはしない（互換の
        # 仕組みは持たない）が、何をすればよいかは言う
        for stem in ('galleykit', 'galley'):
            old = p.with_name(f'{stem}.config.py')
            if p.name == 'octavo.config.py' and old.exists():
                sys.exit(t('{old} is from before the rename to Octavo — rename it to '
                           '{new}, analysis/{helper} to analysis/octavo.R, and in each '
                           '.qmd the source() line and gl_value() / gl_figure() / '
                           'gl_table() to ov_value() / ov_figure() / ov_table()',
                           old=old, new=p.name, helper=f'{stem}.R'))
        example = paths.example_config()
        sys.exit(t('no config file at {path}', path=p) + '\n'
                 + f'  cp {example} {p}\n  '
                 + t('then edit draft and bib_file in it.') + '\n  '
                 + t('Starting from nothing: octavo init my-paper'))

    spec = importlib.util.spec_from_file_location('octavo_config', p)
    mod = importlib.util.module_from_spec(spec)
    # 研究プロジェクトの直下に __pycache__/ を作らない（設定を読むだけのため）
    saved, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.dont_write_bytecode = saved
    if not hasattr(mod, 'CONFIG'):
        sys.exit(t('{path} has no CONFIG dictionary', path=p))
    return Config(p.parent, mod.CONFIG, source=p)
