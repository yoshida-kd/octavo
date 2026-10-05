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

BACKENDS = ('latex', 'typst', 'beamer', 'typst-slides', 'typst-notes', 'typst-poster', 'docx')
PROFILES = ('paper', 'handout', 'slides', 'poster')

# 利用者が選ぶ「出力」の名前 -> 中で使う形式（backend）。原稿の冒頭の `outputs:`、
# `--to`、サイドバーはこの名前で話す。形式の名前（`typst` など）も同じ意味に受ける。
OUTPUTS = {
    'pdf': 'typst',
    'word': 'docx',
    'tex': 'latex',
    'slides': 'typst-slides',
    'beamer': 'beamer',
    'script': 'typst-notes',
    'poster': 'typst-poster',
}
OUTPUT_OF = {b: o for o, b in OUTPUTS.items()}
SLIDE_OUTPUTS = ('slides', 'beamer', 'script')


def backend_of(name: str) -> str | None:
    """出力の名前（pdf）か形式の名前（typst）を形式の名前に。知らない名前なら None。"""
    if name in OUTPUTS:
        return OUTPUTS[name]
    return name if name in BACKENDS else None

# --------------------------------------------------------------------------
# 既定値。ここにないキーを octavo.config.py に書くと警告する（誤字よけ）。
# --------------------------------------------------------------------------
DEFAULTS: dict = {
    # ---- 原稿（documents を書かないときの手軽な指定）----------------------
    'draft': 'draft.md',           # 論文本文
    'appendix': None,              # 付録（使わないなら None）
    'slides': 'slides.md',         # 発表スライドの原稿（なければ登録されない）
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
        # 鍵は中の形式の名前、フォルダは出力の名前（pdf / slides / script / word / tex / beamer）。
        # 設定に書くときはどちらの名前でもよい
        'latex': 'build/tex',
        'typst': 'build/pdf',
        'beamer': 'build/beamer',
        'typst-slides': 'build/slides',
        'typst-notes': 'build/script',
        'typst-poster': 'build/poster',
        'docx': 'build/word',
    },

    # ---- 表・図 -----------------------------------------------------------
    # 手で作るもの（figures/）と、作られるもの（assets/）を分ける。
    # assets/ は分析と octavo build が書くので手で直さない（git には入れる）。
    'figure_src_dir': 'figures',   # 手で作る図: Typst で描く <名前>.typ、写真など
    'figure_dir': 'assets/figures',   # 分析の図と、figures/*.typ から組んだ図
    'table_src_dir': 'tables',     # 手で作る表: <名前>.csv
    'table_dir': 'assets/tables',     # 分析の表と、tables/*.csv から作った表（.typ / .tex / .md）
    # 形式ごとに使う図の拡張子。書かなければ Word=.png、他（Typst・LaTeX）=.pdf
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
    'analysis_args': [],           # Quarto に渡す追加の引数
    'analysis_auto': True,         # octavo build のとき、古ければ自動で実行する

    # ---- 分析が出した数値（本文の {{…}}）---------------------------------
    'values_dir': 'assets/values',   # 分析が書く数値（*.json）の置き場
    'value_float_format': '.3f',   # 小数の既定書式（{{key:.2f}} が優先）
    'value_thousands_sep': True,   # 整数に桁区切りを入れる（1,523）
    # octavo lint が「手入力された結果」と見なさない文字列。慣例的な定数
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
    # タイトル部分から伏せるメタデータ:
    'anonymous_drop_meta': ['author', 'institute', 'thanks', 'email'],

    # ---- 複製パッケージ（octavo bundle --replication）----------------------
    # 入れないもの（グロブ）。原データは既定で入れない（--with-raw-data で入る）
    'replication_exclude': [],

    # ---- 書誌 -------------------------------------------------------------
    'bib_file': 'literature.bib',  # Zotero からエクスポートしたもの（正本、1ファイル）
    # 雑誌に合わせた書式。CSL スタイル ID（'apa', 'ieee',
    # 'modern-language-association' …）か .csl へのパス。
    # ID を書くと Zotero スタイルリポジトリから取得してキャッシュする。
    'csl': 'chicago-author-date',
    'csl_locale': None,            # 'ja-JP' 等。None なら lang から決める
    # 日本語の文書で、英語の文献は英語の決まりで、日本語の文献（.bib の langid = {japanese}）
    # は日本語の形（山田・田中、ほか、「」『』）で組む。False なら書誌全体を csl_locale で
    'citations_by_language': True,
    # その日本語の文献の形: 'standard'  山田太郎・田中花子 (2020)「題」『誌名』12(3): 1–20.
    #                      'fullwidth' 山田太郎・田中花子（2020）「題」『誌名』12巻3号、1–20頁。
    #                      'period'    山田太郎・田中花子．2020．「題」『誌名』12巻3号、1–20頁。
    'japanese_citation_form': 'standard',
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
    'crossref_numbering': 'section',   # 図表・式の番号: 'section'（節ごと 2.1）| 'document'（通し）
    'east_asian_line_breaks': True,

    # ---- 見出し・目次（profile の既定を上書きしたいときだけ）--------------
    'toc': None,                   # None なら profile 任せ
    'number_sections': None,       # 同上
    'toc_depth': 2,
    # 最初の節（最上位の見出し）の番号。講義のガイダンスを「0」にするなら 0。
    # 図表・式・事例などの番号（図0.1）もこれに従う
    'first_section': 1,

    # ---- 日付 -------------------------------------------------------------
    # タイトル部分の date: の書式（strftime。%-m / %-d は 0 を付けない月・日）。
    # None なら言語から（日本語: 2026年10月14日、英語: October 14, 2026）。
    # date: today と書けば組んだ日になる。2026-10-14 の形でない日付はそのまま出す
    'date_format': None,

    # ---- メタデータ -------------------------------------------------------
    # 原稿の YAML front matter が優先。ここは既定値。
    # {'title':…, 'author':…, 'institute':…, 'date':…,
    #  'affiliation':…, 'email':…}（affiliation と email は octavo new analysis の .qmd 用）
    'meta': {},

    # ---- 事例・論点などのブロック（`::: {.question #question-why title="…"}`）------
    # 同梱の既定: case 事例 / question 論点（この2つは番号を通しで振る）、
    # aside 余談 / nb 注意 / memo 付記（番号なし）、theorem 定理 / lemma / proposition / corollary /
    # definition / example（番号を通しで振る）、remark（番号なし）。
    # 見出し語を変える・増やすときだけ書く:
    #   {'case': '事例',                                    # 見出し語だけ変える
    #    'claim': {'name': '主張', 'counter': 'case'},      # 増やす（事例と通し番号）
    #    'hint': {'name': {'ja': 'ヒント', 'en': 'Hint'}, 'numbered': False}}
    'theorem_envs': {},

    # ---- LaTeX ------------------------------------------------------------
    'latex_engine': 'lualatex',
    'latex_documentclass': None,   # None なら lang から（ja: ltjsarticle）
    'latex_classoptions': ['a4paper'],
    'latex_fontsize': '11pt',

    # ---- Typst ------------------------------------------------------------
    # 講義ノート（A4 プリント）の体裁。templates/handout/handout.typ（octavo template copy
    # handout/handout.typ で差し替えられる）が読む。原稿の冒頭でも変えられる
    'font': None,          # None なら BIZ UDゴシック + Inter（typst.FONTS の sans）
    'fontsize': '11pt',
    # どこで改ページするか: 'session'（回の区切りごと。区切りを書いていなければ `#` ごと）、
    # 'section'（`#` ごと）、None（改ページしない。区切りでは必ず改ページする）
    'pagebreak': 'session',

    # ---- Typst スライド（TeX 無しで組むスライド）--------------------------
    'slides_aspect': '16-9',  # '16-9' | '4-3'
    # スライドの見出しに番号を振る。Typst の numbering 文字列（'1.' や '1.1'）。
    # None なら振らない（既定）。'1.1' は「#」の節と「##」の枚の2段が要る。
    'slides_numbering': None,
    # 「#」の節を扉のスライドにするか。False なら扉を出さず、番号を進めるだけ
    # （節で区切りたいが枚数は増やしたくないとき）。
    'slides_section_slides': False,
    # 差し色。'#0e2f92' のような16進。題・箇条書きの印・罫に使う。
    # None なら色を使わない（黒のまま）。既定は海の青（#25 で入れた「差し色を
    # 設定したときだけ体裁が変わる」ゲートにより、None にすればいつでも従来
    # どおりの黒一色に戻せる）。
    'slides_accent': '#0e2f92',
    # 各スライドの左上に、いまの「#」の節を小さく出すか（既定は出さない）。
    'slides_running_header': True,   # 左上にいまの節（なければデッキの題）
    'slides_font': None,      # None なら typst.FONTS の sans（BIZ UDGothic + Inter）

    # ---- ポスター（outputs: [poster]）--------------------------------------
    'poster_size': 'a0',            # 'a0' | 'a1' | 'a2' | 'b0' | 'b1'（JIS B）| '1189x841mm' のような寸法
    'poster_orientation': 'portrait',   # 'portrait'（縦）| 'landscape'（横）
    'poster_grid': '2x3',           # マスの格子（列×行）。原稿の一番上の見出し1つが1マス
    'poster_rows': None,            # 行の高さの比（[1, 2, 1] など）。None なら均等
    'poster_font': None,            # None なら typst.FONTS の sans（BIZ UDGothic + Inter）
    # スライド・ポスターに出す中身: 'all'（全部。.pdf-only などで外す）| 'marked'（印の所だけ。
    # ::: {.on-slides} / {.on-poster} の囲み、見出しに付けた {.on-slides} の節、[…]{.on-slides}）
    'slides_select': 'all',
    'poster_select': 'all',

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
    'docx_reference': None,        # 見た目の元にする .docx（--reference-doc）
    'docx_track_changes_ready': True,
}

# 名前を変えた鍵: 前の名前 -> 今の名前。設定ファイルにも原稿の冒頭にも、前の名前で
# 書いてあれば今の名前として読む（書き換えなくてよい）。
KEY_ALIASES = {
    'typst_slides_aspect': 'slides_aspect',
    'typst_slides_numbering': 'slides_numbering',
    'typst_slides_section_slides': 'slides_section_slides',
    'typst_slides_accent': 'slides_accent',
    'typst_slides_running_header': 'slides_running_header',
    'typst_slides_font': 'slides_font',
    'handout_font': 'font',
    'handout_fontsize': 'fontsize',
    'handout_pagebreak': 'pagebreak',
}


def aliases_of(key: str) -> list:
    """その鍵の前の名前。"""
    return [old for old, new in KEY_ALIASES.items() if new == key]


def renamed(values: dict) -> dict:
    """前の名前の鍵を今の名前に。両方書いてあれば今の名前が勝つ。"""
    out = {}
    for k, v in values.items():
        new = KEY_ALIASES.get(k)
        if new is None:
            out[k] = v
        elif new not in values:
            out[new] = v
    return out


PATH_KEYS = ('draft', 'appendix', 'slides', 'handout', 'table_dir', 'figure_dir',
             'figure_src_dir', 'table_src_dir', 'values_dir', 'bib_file', 'docx_reference')

# 原稿の冒頭（front matter）に書けば、その文書だけ設定より優先する鍵。
# 投稿先・発表ごとに変わるもの。書かなければ octavo.config.py の値が効く。
DOC_KEYS = ('csl', 'outputs', 'targets', 'sessions', 'toc', 'word_limit', 'char_limit', 'abstract_word_limit',
            'abstract_char_limit', 'slides_aspect', 'slides_accent',
            'slides_running_header', 'slides_section_slides',
            'slides_numbering', 'slides_font', 'first_section', 'date_format',
            'font',
            'fontsize', 'pagebreak', 'citations_by_language',
            'japanese_citation_form',
            'poster_size', 'poster_orientation', 'poster_grid', 'poster_rows', 'poster_font',
            'slides_select', 'poster_select')
JA_FORMS = ('standard', 'fullwidth', 'period')
LIST_DOC_KEYS = ('poster_grid', 'poster_rows')
INT_DOC_KEYS = ('word_limit', 'char_limit', 'abstract_word_limit', 'abstract_char_limit',
                'first_section')
BOOL_DOC_KEYS = ('slides_running_header', 'slides_section_slides',
                 'citations_by_language', 'sessions', 'toc')


def doc_setting_typos(src: Path, text: str | None = None) -> list:
    """原稿の冒頭の鍵のうち、文書ごとの設定の綴り違いらしいもの [(書いた鍵, 正しい鍵)]。

    冒頭にはタイトルや pandoc の鍵も並ぶので、知らない鍵を全部咎めはしない。
    DOC_KEYS のどれかに近いもの（`first-section-number` → `first_section`）だけ。
    黙って無視されると、効かないことに気づけない。
    """
    import difflib
    from . import md as mdlib
    if text is None:
        try:
            text = Path(src).read_text(encoding='utf-8')
        except OSError:
            return []
    meta, _ = mdlib.split_front_matter(text)
    out = []
    for k in meta:
        if k in DOC_KEYS or k in KEY_ALIASES:
            continue
        near = difflib.get_close_matches(k.replace('-', '_').lower(), DOC_KEYS, n=1, cutoff=0.7)
        if near:
            out.append((k, near[0]))
    return out


def doc_settings(src: Path, text: str | None = None) -> dict:
    """原稿の冒頭に書いてある文書ごとの設定（DOC_KEYS だけ、型をそろえて）。

    冒頭は Octavo の小さな YAML 読み（md.split_front_matter）で読むので値は文字列か
    文字列の並び。数・真偽・「無し」はここで直す。読めない値は SystemExit。
    """
    from . import md as mdlib
    if text is None:
        try:
            text = Path(src).read_text(encoding='utf-8')
        except OSError:
            return {}
    meta, _ = mdlib.split_front_matter(text)
    meta = renamed(meta)
    out: dict = {}
    for k in DOC_KEYS:
        if k not in meta:
            continue
        v = meta[k]
        if k in ('outputs', 'targets'):
            # どちらも中の形式の名前にそろえて返す（`targets:` は前からの書き方）
            v = [v] if isinstance(v, str) else list(v)
            v = [x.strip() for x in v if str(x).strip()]
            bad = [x for x in v if backend_of(x) is None]
            if bad or not v:
                sys.exit(t('{file}: {key} has unknown outputs: {bad}',
                           file=src, key=k, bad=', '.join(bad) or '[]')
                         + '\n  ' + t('available: {names}', names=', '.join(OUTPUTS)))
            out[k] = tuple(dict.fromkeys(backend_of(x) for x in v))
            continue
        if k in LIST_DOC_KEYS and isinstance(v, (list, tuple)):
            out[k] = [str(x).strip() for x in v]           # [1, 2, 1] の並びはそのまま
            continue
        s = str(v).strip()
        if s.lower() in ('none', 'null', '~', ''):
            out[k] = None
        elif k in INT_DOC_KEYS:
            try:
                out[k] = int(s.replace(',', ''))
            except ValueError:
                sys.exit(t('{file}: {key} must be a whole number (got {got})',
                           file=src, key=k, got=repr(s)))
        elif k in BOOL_DOC_KEYS:
            if s.lower() not in ('true', 'false', 'yes', 'no'):
                sys.exit(t('{file}: {key} must be true or false (got {got})',
                           file=src, key=k, got=repr(s)))
            out[k] = s.lower() in ('true', 'yes')
        else:
            out[k] = s
    return out


@dataclass
class Document:
    """1本の原稿と、その出し方。

    `targets` は中の形式の名前（typst など）。利用者に見せるのは `outputs`（pdf など）。
    `profile`（paper / handout / slides）は、設定に書いた旧来の文書ではそこに書いたもの、
    `docs/<名前>/` の文書（derived）では原稿の横の体裁ファイルと出力から決めたもの。
    """
    name: str
    src: Path
    profile: str = 'paper'
    targets: tuple = ('typst',)
    appendix: Path | None = None
    out: Path | None = None                 # 形式別 out_dirs を上書きする
    meta: dict = field(default_factory=dict)
    # 何回分かの授業でできているか。スライドは回ごとに別々に組む
    #（講義ノート1本 -> 回ごとのスライド）。設定の旧来の名前は split_slides
    sessions: bool = False
    # 分けたうちの1つなら、その回の印（'01' か見出しの {#id}）
    part: str | None = None
    # 設定ファイルの documents に書いた出力形式（原稿の冒頭の outputs がないときの値）
    config_targets: tuple = ('typst',)
    # profile を書かずに登録した文書（docs/<名前>/ など）。体裁は main.* の有無で決まり、
    # `# 題` を外さない、目次の既定は sessions に従う、など新しい決まりで組む
    derived: bool = False

    def exists(self) -> bool:
        return self.src.is_file()

    @property
    def split_slides(self) -> bool:
        return self.sessions

    @property
    def outputs(self) -> tuple:
        return tuple(OUTPUT_OF.get(b, b) for b in self.targets)

    @property
    def config_outputs(self) -> tuple:
        return tuple(OUTPUT_OF.get(b, b) for b in self.config_targets)


def derive_profile(src: Path, targets) -> str:
    """profile を書かずに登録した文書の profile。

    スライドしか出さないなら slides、原稿の横に自分の体裁（main.typ / main.tex）が
    あれば paper（体裁はそのファイル）、なければ handout（Octavo の組み込みの体裁）。
    """
    if targets and all(OUTPUT_OF.get(b) in SLIDE_OUTPUTS for b in targets):
        return 'slides'
    if targets and all(OUTPUT_OF.get(b) == 'poster' for b in targets):
        return 'poster'
    folder = Path(src).parent
    if (folder / 'main.typ').is_file() or (folder / 'main.tex').is_file():
        return 'paper'
    return 'handout'


class Config:
    def __init__(self, root: Path, values: dict, source: Path | None = None):
        values = renamed(values)
        self.root = root
        self.source = source
        # 設定ファイルに**書いてある**鍵（既定のままのものとの区別。octavo config が使う）
        self.explicit = frozenset(values)
        self.doc_explicit: frozenset = frozenset()     # for_document() が埋める
        unknown = sorted(set(values) - set(DEFAULTS))
        if unknown:
            print(t('warning: unknown keys in the config (ignored): {keys}',
                    keys=', '.join(unknown)), file=sys.stderr)

        v = {**DEFAULTS, **values}
        for k in ('out_dirs', 'figure_ext', 'meta', 'theorem_envs'):
            own = dict(values.get(k) or {})
            if k in ('out_dirs', 'figure_ext'):
                # 出力の名前（pdf など）で書いてあれば、中の形式の名前に
                own = {(backend_of(x) or x): y for x, y in own.items()}
            v[k] = {**DEFAULTS[k], **own}

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
        self.doc_spec = dict(values.get('documents') or {})
        self.documents = self._build_documents(self.doc_spec)

    # -- 参照 ---------------------------------------------------------------
    def __getitem__(self, k):
        return self._v[k]

    def __contains__(self, k):
        return k in self._v

    def get(self, k, default=None):
        return self._v.get(k, default)

    def for_document(self, doc: Document) -> 'Config':
        """その文書の設定。原稿の冒頭に書いた DOC_KEYS を、プロジェクトの設定に重ねる。

        変換はこれを使うので、スライドの体裁・CSL・投稿規定の上限を読む側は
        `cfg[鍵]` のままでよい。`doc_explicit` は原稿に書いてある鍵。
        """
        import copy
        own = doc_settings(doc.src)
        view = copy.copy(self)
        view._v = {**self._v, **own}
        view.doc_explicit = frozenset(own)
        try:
            view._validate()
        except SystemExit as e:
            sys.exit(f'{self.rel(doc.src)}: {e.code}')
        return view

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
                                config_targets=doc.config_targets,
                                out=doc.out, meta=dict(doc.meta), part=key,
                                sessions=doc.sessions, derived=doc.derived))
        return out

    # -- 文書の組み立て -----------------------------------------------------
    def _build_documents(self, spec: dict) -> dict:
        from . import md as mdlib
        docs: dict = {}
        if spec:
            for name, d in spec.items():
                if not isinstance(d, dict) or 'src' not in d:
                    sys.exit(t("documents['{name}'] needs at least 'src'", name=name))
                # profile を書いていない文書は、体裁ファイルと出力から決める（derived）
                derived = 'profile' not in d
                prof = d.get('profile', 'paper')
                if prof not in PROFILES:
                    sys.exit(t("documents['{name}'] has a bad profile: {got} "
                               '(one of {allowed})',
                               name=name, got=repr(prof), allowed='/'.join(PROFILES)))
                listed = d.get('outputs', d.get('targets', ['typst']))
                bad = [x for x in listed if backend_of(x) is None]
                if bad:
                    sys.exit(t("documents['{name}'] has bad targets: {bad}",
                               name=name, bad=', '.join(bad)))
                ap = d.get('appendix')
                common = dict(
                    targets=tuple(dict.fromkeys(backend_of(x) for x in listed)),
                    out=(self.root / d['out']).resolve() if d.get('out') else None,
                    meta=dict(d.get('meta') or {}),
                )
                split = bool(d.get('sessions', d.get('split_slides', False)))

                def add(nm: str, src: Path, appendix: Path | None) -> None:
                    if nm in docs:
                        sys.exit(t('two documents share the name {name}', name=nm)
                                 + f'\n  {docs[nm].src}\n  {src}\n  '
                                 + t('rename one of the manuscripts (or its folder)'))
                    try:
                        text = src.read_text(encoding='utf-8')
                    except OSError:
                        text = ''
                    own = doc_settings(src, text)            # 原稿の冒頭が優先
                    if 'outputs' in own and 'targets' in own and own['outputs'] != own['targets']:
                        print(t('{file}: both outputs and targets are written; outputs is used',
                                file=self.rel(src)), file=sys.stderr)
                    targets = own.get('outputs') or own.get('targets') or common['targets']
                    sessions = own.get('sessions')
                    if sessions is None:
                        sessions = split or mdlib.has_session_markers(
                            valmod_mask(text))
                    docs[nm] = Document(
                        name=nm, src=src, appendix=appendix,
                        profile=derive_profile(src, targets) if derived else prof,
                        targets=targets, config_targets=common['targets'],
                        out=common['out'], meta=common['meta'],
                        sessions=bool(sessions), derived=derived)

                # src にワイルドカードが使える。同じ扱いの原稿がたくさんある
                # （スライド10本、論文が数本）場合、1つ書けば全部登録される。
                #   'docs': {'src': 'docs/*/'}                   -> フォルダ名
                #   'スライド': {'src': 'slides/*.md', …}        -> example-talk, …
                #   '論文': {'src': 'papers/*/paper.md',
                #            'appendix': 'papers/*/appendix.md', …} -> フォルダ名
                # 文書名は最初の `*` に当たった部分（名前に * があればそこに差し込む）。
                # 何も当たらないのは「その種類の原稿がまだない」だけなので黙っている。
                # `/` で終わる src はフォルダごとに1文書: `<フォルダ>/<フォルダ名>.md` が原稿、
                # 横の appendix.md が付録。原稿のないフォルダは文書ではないので飛ばす。
                if d['src'].endswith('/'):
                    for folder in sorted(self.root.glob(d['src'].rstrip('/'))):
                        main = folder / f'{folder.name}.md'
                        if not folder.is_dir() or not main.is_file():
                            continue
                        nm = name.replace('*', folder.name) if '*' in name else folder.name
                        apx = folder / (ap or 'appendix.md')
                        add(nm, main.resolve(), apx.resolve() if apx.is_file() else None)
                elif any(c in d['src'] for c in '*?['):
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
        if v['crossref_numbering'] not in ('section', 'document'):
            bad('crossref_numbering', "'section'/'document'")
        if v['typst_citations'] not in ('csl', 'native'):
            bad('typst_citations', t("'csl' or 'native'"))
        if v['slides_aspect'] not in ('16-9', '4-3'):
            bad('slides_aspect', t("'16-9' or '4-3'"))
        if v['slides_numbering'] is not None and not isinstance(v['slides_numbering'], str):
            bad('slides_numbering',
                t("a Typst numbering string ('1.' and the like) or None"))
        if not isinstance(v['first_section'], int) or v['first_section'] < 0:
            bad('first_section', t('a whole number, 0 or more'))
        if v['japanese_citation_form'] not in JA_FORMS:
            bad('japanese_citation_form', "'" + "'/'".join(JA_FORMS) + "'")
        for k in ('slides_select', 'poster_select'):
            if v[k] not in ('all', 'marked'):
                bad(k, "'all'/'marked'")
        from .backends.typst_poster import paper_mm, grid_shape, row_ratios
        if v['poster_orientation'] not in ('portrait', 'landscape'):
            bad('poster_orientation', "'portrait'/'landscape'")
        try:
            paper_mm(v['poster_size'], v['poster_orientation'])
        except ValueError:
            bad('poster_size', t("'a0'/'a1'/'a2'/'b0'/'b1' or a size like '1189x841mm'"))
        try:
            cols, rows = grid_shape(v['poster_grid'])
        except ValueError:
            bad('poster_grid', t("columns x rows, like '2x3'"))
        try:
            row_ratios(v['poster_rows'], rows)
        except ValueError:
            bad('poster_rows', t('one positive number per row of poster_grid, like [1, 2, 1]'))
        if v['pagebreak'] not in ('session', 'section', None):
            bad('pagebreak', "'session'/'section'/None")
        if not re.fullmatch(r'\d+(?:\.\d+)?pt', str(v['fontsize'])):
            bad('fontsize', t("a size in points like '11pt'"))
        acc = v['slides_accent']
        if acc is not None and not (isinstance(acc, str)
                                    and re.fullmatch(r'#[0-9A-Fa-f]{6}', acc)):
            bad('slides_accent', t("a hex colour like '#0e2f92', or None"))
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


def valmod_mask(text: str) -> str:
    """コードの中を伏せた本文（例として書いた `::: {.session}` を区切りと取らない）。"""
    from . import values as valmod
    return valmod.mask_code(text)[0]


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
        example = paths.example_config()
        sys.exit(t('no config file at {path}', path=p) + '\n'
                 + f'  cp {example} {p}\n  '
                 + t('then edit bib_file in it.') + '\n  '
                 + t('To start from scratch: octavo init my-paper'))

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
