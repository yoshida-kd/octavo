# -*- coding: utf-8 -*-
"""プロジェクトごとの設定。コピーして使う。

    cp octavo/config.example.ja.py my-paper/octavo.config.py

(English version: config.example.py)

`octavo` は実行時に `--config`（既定はカレントの octavo.config.py）から
この CONFIG を読む。パスはすべて octavo.config.py があるディレクトリからの
相対で解決される。

ここに書いていない項目は octavo/config.py の DEFAULTS が既定値。
知らないキーを書くと警告が出る（誤字よけ）。
"""

CONFIG = {
    # ================================================================
    # 原稿
    # ================================================================
    # 手軽な指定。draft.md / slides.md / handout.md が置いてあれば、
    # それぞれ論文 / 発表スライド / A4 プリントとして自動で登録される。
    'draft': 'draft.md',
    # 'appendix': 'appendix.md',
    # 'slides': 'slides.md',
    # 'handout': 'handout.md',

    # 細かく決めたいときはこちら（書くと上の draft/slides/handout は無視される）。
    # profile は 'paper'（論文）/ 'handout'（A4 プリント）/ 'slides'（スライド）。
    # 同じ原稿からプリントとスライドの両方を作るなら targets に両方書く。
    # 'documents': {
    #     'paper':  {'src': 'draft.md',  'profile': 'paper',
    #                'targets': ['typst', 'docx'], 'appendix': 'appendix.md'},
    #     'slides': {'src': 'slides.md', 'profile': 'slides',
    #                'targets': ['typst-slides']},
    #     '第1回':  {'src': 'lecture01.md', 'profile': 'handout',
    #                'targets': ['typst', 'typst-slides']},
    #     # src にはワイルドカードも書ける。当たった原稿がそれぞれ文書になり、
    #     # 名前は最初の * に当たった部分（キーに * があればそこに差し込む）。
    #     # octavo init が書くのはこの形で、octavo new で足した原稿を拾う
    #     'papers': {'src': 'papers/*/paper.md', 'appendix': 'papers/*/appendix.md',
    #                'profile': 'paper', 'targets': ['typst']},
    #     # split_slides: スライドを `#` 見出しごとに別々に組む（講義ノート ->
    #     # <名前>-01, -02, …）。プリントは1本のまま
    #     'lectures': {'src': 'lectures/*.md', 'profile': 'handout',
    #                  'targets': ['typst', 'typst-slides'], 'split_slides': True},
    # },

    # ================================================================
    # 書誌（Zotero → .bib → 雑誌の書式）
    # ================================================================
    # 正本は1つの .bib。Zotero の書き出しをそのまま置く。
    #   octavo bib pull --collection "論文X"    Zotero から直接取ってくる
    #   octavo checkbib                         引用キーとの突き合わせ
    'bib_file': 'literature.bib',

    # 投稿先の書式。CSL のスタイル ID か .csl へのパス。
    #   octavo csl list          手元にあるもの
    #   octavo csl get apa       取ってくる（https://www.zotero.org/styles で ID を探す）
    # 別名も使える: apa / chicago / ieee / mla / nature / …
    'csl': 'chicago-author-date',
    # 'csl_locale': 'ja-JP',        # 既定は lang から決まる
    # 'reference_section_title': '参考文献',   # '' にすると見出しを入れない

    # 承知のうえで直さない書誌の傷（octavo checkbib が黙る）
    # 'bib_accepted': {('yamada2020', 'ページも DOI もない'): '紀要で通し番号が無い'},

    # ================================================================
    # 言語
    # ================================================================
    'lang': 'ja',                 # 'ja' | 'en'
    # 'east_asian_line_breaks': True,   # 日本語の行間改行で空白を入れない

    # ================================================================
    # 図・表
    # ================================================================
    'figure_dir': 'figures',
    'table_dir': 'tables',
    # 'figure_width': 1.0,              # \textwidth に対する比
    # 'figure_ext': {'latex': '.pdf', 'docx': '.png'},   # 既定を変えるとき

    # 図・表・式の番号。原稿には番号を書かず {#fig-…} などのラベルで指す（@fig-…）
    'crossref_numbering': 'section',  # 'section'（節ごと 図2.1）| 'document'（通し 図1）

    # ================================================================
    # 分析（Quarto の .qmd）
    # ================================================================
    # 論文に出す数値・図・表を作る .qmd。octavo build は .qmd が新しければ
    # 自動で quarto render を走らせる（quarto が無ければ警告して素通り）。
    #   分析側: ov_value("n_obs", nrow(d)) / ov_figure(p, "trend")
    #           ov_table(tab, "summary")          ← octavo.R のヘルパー
    #   原稿側: {{n_obs}} / ![推移](figures/trend.png){#fig-trend} /
    #           `: 記述統計 {#tbl-summary}`（分析が作った表がここに入る）
    'analysis': [],               # 例: ['analysis/*.qmd']
    # データの更新も見張るなら、要素を辞書にする
    # 'analysis': [{'src': 'analysis/main.qmd', 'deps': ['data/*.csv']}],
    # 'analysis_deps': [],        # 全部の .qmd に共通の依存
    # 'analysis_to': None,        # quarto render --to（None なら .qmd 任せ）
    # 'analysis_args': [],        # quarto に渡す追加の引数
    # 'analysis_auto': True,      # False で octavo analysis run のときだけ走る

    # 分析が出した数値の置き場と、{{…}} の既定の書式
    'results_dir': 'results',
    # 'value_float_format': '.3f',   # 小数（{{coef:.2f}} が優先）
    # 'value_thousands_sep': True,   # 整数を 1,523 と書く

    # octavo lint が「直書きされた結果」と見なさない文字列。
    # 慣例的な定数（0.05 / 1.96 等）は既定で見逃す。
    # 'lint_accepted': ['2.5'],

    # ================================================================
    # 投稿規定・匿名審査・複製パッケージ
    # ================================================================
    # 上限を書くと octavo check が突き合わせる。書かなければ見ない。
    # 'word_limit': 8000,             # 本文の語数
    # 'char_limit': 20000,            # 本文の文字数（日本語の雑誌）
    # 'abstract_word_limit': 150,
    # 'abstract_char_limit': 400,

    # 匿名審査（octavo build --anonymous）で題扉から落とすメタデータ。
    # 原稿側は  ::: {.no-anonymous} … :::  で謝辞などを囲む。
    # 'anonymous_drop_meta': ['author', 'institute', 'thanks', 'email'],

    # 複製パッケージ（octavo bundle --replication）に入れないもの（グロブ）。
    # 原データは既定で入らない（--with-raw-data で入る）。
    # 'replication_exclude': ['data/derived/巨大な中間ファイル.rds'],

    # ================================================================
    # 題扉（原稿の YAML front matter が優先。ここは既定値）
    # ================================================================
    'meta': {
        # 'title': '論文タイトル',
        # 'author': '山田 太郎',
        # 'institute': '○○大学',
    },

    # ================================================================
    # 出力先（既定は build/ の下）
    # ================================================================
    # 'out_dirs': {'latex': 'build/latex', 'docx': 'build/word'},

    # ================================================================
    # LaTeX
    # ================================================================
    # 'latex_engine': 'lualatex',
    # 'latex_documentclass': 'ltjsarticle',   # 既定は lang から
    # 'latex_classoptions': ['11pt', 'a4paper'],
    # プリアンブルは octavo template copy handout/handout-header.tex で写して直す

    # ================================================================
    # Typst
    # ================================================================
    # 'typst_citations': 'csl',     # 'csl'（他形式と同じ書式）| 'native'
    # A4 プリント。既定は BIZ UD明朝＋欧文 Libertinus Serif（README の「書体」）
    # 'typst_mainfont': ['BIZ UDMincho', 'Noto Serif CJK JP'],

    # ================================================================
    # スライド（Typst。TeX 無しで組む）
    # ================================================================
    # 'typst_slides_aspect': '16-9',   # '16-9' | '4-3'
    # 既定は BIZ UDゴシック＋欧文 Inter。並びを書けばそのまま使う
    # 'typst_slides_font': ['BIZ UDGothic', 'Noto Sans CJK JP'],
    # 見出しに番号を振る（Typst の numbering 文字列）。None なら振らない
    # 'typst_slides_numbering': '1.1',
    # '#' の節を扉のスライドにしない（番号だけ進める）
    # 'typst_slides_section_slides': False,
    # 差し色。**これを書くと体裁が切り替わる**（題を色で立てて太字をやめる、
    # 箇条書きの印を ▶ に、ページ番号を「4 / 11」に、リンクにも色）。
    # 既定はこの青。従来どおり黒一色にしたいときは None にする
    # 'typst_slides_accent': '#0e2f92',
    # 左上にいまの '#' の節を小さく出す（既定で出る。節が無ければデッキの題）
    # 'typst_slides_running_header': False,
    # 体裁ごと変えるなら、同梱のひな型を写して直す（README §7）:
    #   octavo template copy slides/typst-slides.typ

    # ================================================================
    # 台本（typst-notes）。同じスライドを A4 で、typst-slides が落とす
    # ::: notes を付けて組む。上の typst_slides_* はそのまま効く。
    # 毎回作るなら文書の targets に足す。要るときだけなら
    #   octavo build <名前> --to typst-notes
    # 体裁は octavo template copy slides/typst-notes.typ で写して直す
    # ================================================================

    # ================================================================
    # スライド（Beamer。TeX を入れたときだけ）
    # ================================================================
    # 'beamer_theme': 'metropolis',    # 既定は 'default'
    # 'beamer_aspectratio': '169',
    # 'beamer_slide_level': 2,         # '## 見出し' が1枚
    # 'beamer_notes': False,           # True で発表者ノートを刷り込む
    # 'slides_bibliography': False,    # True でスライド末尾に書誌一覧を出す

    # ================================================================
    # Word
    # ================================================================
    # octavo reference-docx reference.docx で雛形を作り、Word でスタイルを
    # 整えてから指定する。中身は空でよい（スタイル定義だけ使う）。
    # 'docx_reference': 'reference.docx',
}
