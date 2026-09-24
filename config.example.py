# -*- coding: utf-8 -*-
"""Per-project configuration. Copy this file to get started.

    cp octavo/config.example.py my-paper/octavo.config.py

(日本語版: config.example.ja.py)

At run time, `octavo` reads this CONFIG dict via `--config` (defaults to
octavo.config.py in the current directory). Every path here is resolved
relative to the directory octavo.config.py lives in.

Anything not set here falls back to the defaults in octavo/config.py's
DEFAULTS. An unknown key triggers a warning (typo protection).
"""

CONFIG = {
    # ================================================================
    # Documents
    # ================================================================
    # The simple way: if draft.md / slides.md / handout.md exist, each is
    # registered automatically as a paper / slide deck / A4 handout.
    'draft': 'draft.md',
    # 'appendix': 'appendix.md',
    # 'slides': 'slides.md',
    # 'handout': 'handout.md',

    # For finer control, use this instead (writing it disables the
    # draft/slides/handout shortcuts above). profile is one of 'paper',
    # 'handout' (A4 print), or 'slides'. List both targets if you want a
    # handout and slides built from the same source.
    # 'documents': {
    #     'paper':  {'src': 'draft.md',  'profile': 'paper',
    #                'targets': ['typst', 'docx'], 'appendix': 'appendix.md'},
    #     'slides': {'src': 'slides.md', 'profile': 'slides',
    #                'targets': ['typst-slides']},
    #     'week1':  {'src': 'lecture01.md', 'profile': 'handout',
    #                'targets': ['typst', 'typst-slides']},
    #     # src accepts wildcards too. Each match becomes a document named
    #     # after what the first * matched (a * in the key is filled with it).
    #     # This is the shape octavo init writes; it picks up octavo new's files
    #     'papers': {'src': 'papers/*/paper.md', 'appendix': 'papers/*/appendix.md',
    #                'profile': 'paper', 'targets': ['typst']},
    #     # split_slides: build the slides per `#` heading (lecture notes ->
    #     # <name>-01, -02, ...). The handout stays one document
    #     'lectures': {'src': 'lectures/*.md', 'profile': 'handout',
    #                  'targets': ['typst', 'typst-slides'], 'split_slides': True},
    # },

    # ================================================================
    # Bibliography (Zotero -> .bib -> journal style)
    # ================================================================
    # One .bib file is the source of truth — drop your Zotero export here
    # as-is.
    #   octavo bib pull --collection "My Paper"    pull directly from Zotero
    #   octavo checkbib                            cross-check citation keys
    'bib_file': 'literature.bib',

    # Target journal's citation style: a CSL style ID, or a path to a .csl
    # file.
    #   octavo csl list          styles you already have
    #   octavo csl get apa       fetch one (look up IDs at https://www.zotero.org/styles)
    # Short aliases also work: apa / chicago / ieee / mla / nature / ...
    'csl': 'chicago-author-date',
    # 'csl_locale': 'ja-JP',        # defaults based on lang
    # 'reference_section_title': 'References',   # set to '' to omit the heading

    # Bibliography issues you've reviewed and are deliberately leaving as-is
    # (octavo checkbib stops flagging these).
    # 'bib_accepted': {('yamada2020', 'no page range or DOI'): 'bulletin uses a running number instead'},

    # ================================================================
    # Language
    # ================================================================
    'lang': 'en',                 # 'ja' | 'en'
    'crossref_vocab': 'both',     # recognize both "Table 1" and Japanese "表1"
    # 'east_asian_line_breaks': True,   # don't insert spaces at Japanese line breaks

    # ================================================================
    # Figures & tables
    # ================================================================
    'figure_dir': 'figures',
    'table_dir': 'tables',
    # 'figure_width': 1.0,              # fraction of \textwidth
    # 'figure_ext': {'latex': '.pdf', 'docx': '.png'},   # override the defaults

    # Only needed if an analysis pipeline (R / Python / qmd) writes tables
    # directly as .tex or .typ. Maps "table number in the text" -> "filename
    # under tables/ (no extension)". Leave empty and the Markdown table in
    # the source is used as-is. Word and slide decks can't embed external
    # table files, so the Markdown table is used there regardless.
    'table_map': {},              # e.g. {'1': 'tbl1_summary', '2': 'tbl2_models'}
    'appendix_table_map': {},     # e.g. {'A1': 'appA1_robustness'}

    # ================================================================
    # Analysis (Quarto .qmd)
    # ================================================================
    # The .qmd files that produce the paper's numbers, figures and tables.
    # octavo build runs `quarto render` on any .qmd that is newer than its
    # output (with quarto missing it warns and carries on).
    #   analysis side: ov_value("n_obs", nrow(d)) / ov_figure(p, "fig1_x")
    #                  ov_table(tab, "tbl1_summary")   <- helpers from octavo.R
    #   manuscript:    {{n_obs}} / ![](figures/fig1_x.png) / table_map
    'analysis': [],               # e.g. ['analysis/*.qmd']
    # To watch data files too, make an entry a dict instead of a string
    # 'analysis': [{'src': 'analysis/main.qmd', 'deps': ['data/*.csv']}],
    # 'analysis_deps': [],        # dependencies shared by every .qmd
    # 'analysis_to': None,        # quarto render --to (None leaves it to the .qmd)
    # 'analysis_args': [],        # extra arguments passed to quarto
    # 'analysis_auto': True,      # False to run only on `octavo analysis run`

    # Where the analysis writes its values, and the default format for {{...}}
    'results_dir': 'results',
    # 'value_float_format': '.3f',   # doubles ({{coef:.2f}} in the text wins)
    # 'value_thousands_sep': True,   # write integers as 1,523

    # Strings octavo lint should not treat as a result typed into the prose.
    # Conventional constants (0.05, 1.96, ...) are ignored by default.
    # 'lint_accepted': ['2.5'],

    # ================================================================
    # Submission limits, blind review, replication package
    # ================================================================
    # Set a limit and octavo check compares against it. Left unset, it looks
    # at nothing.
    # 'word_limit': 8000,             # words in the body
    # 'char_limit': 20000,            # characters in the body (Japanese journals)
    # 'abstract_word_limit': 150,
    # 'abstract_char_limit': 400,

    # Metadata dropped from the title block under blind review
    # (octavo build --anonymous). In the manuscript, wrap acknowledgements
    # and the like in  ::: {.no-anonymous} ... :::
    # 'anonymous_drop_meta': ['author', 'institute', 'thanks', 'email'],

    # Globs kept out of the replication package (octavo bundle --replication).
    # Raw data is excluded by default (--with-raw-data puts it back).
    # 'replication_exclude': ['data/derived/huge-intermediate.rds'],

    # ================================================================
    # Title block (the source file's own YAML front matter takes
    # precedence; these are just fallback defaults)
    # ================================================================
    'meta': {
        # 'title': 'Paper Title',
        # 'author': 'Jane Doe',
        # 'institute': 'Example University',
    },

    # ================================================================
    # Output directories (default: under build/)
    # ================================================================
    # 'out_dirs': {'latex': 'build/latex', 'docx': 'build/word'},

    # ================================================================
    # LaTeX
    # ================================================================
    # 'latex_engine': 'lualatex',
    # 'latex_documentclass': 'ltjsarticle',   # defaults based on lang
    # 'latex_classoptions': ['11pt', 'a4paper'],
    # The preamble: octavo template copy handout/handout-header.tex, then edit it

    # 事例/論点/注意のような番号付きdivを使うなら（README §2参照）:
    # 'theorem_envs': {'case': '事例', 'question': '論点', 'nb': '注意'},

    # ================================================================
    # Typst
    # ================================================================
    # 'typst_citations': 'csl',     # 'csl' (same style as other formats) | 'native'
    # A4 handouts. Default: BIZ UDMincho with Libertinus Serif for Latin (see README)
    # 'typst_mainfont': ['BIZ UDMincho', 'Noto Serif CJK JP'],

    # ================================================================
    # Slides (Typst — no TeX needed)
    # ================================================================
    # 'typst_slides_aspect': '16-9',   # '16-9' | '4-3'
    # Default: BIZ UDGothic with Inter for Latin; a list you write is used as-is
    # 'typst_slides_font': ['BIZ UDGothic', 'Noto Sans CJK JP'],
    # Number the headings (a Typst numbering string). None = no numbers
    # 'typst_slides_numbering': '1.1',
    # Let a '#' section advance the counter without a divider slide
    # 'typst_slides_section_slides': False,
    # Accent colour. **Setting this switches the look**: titles in colour rather
    # than bold, ▶ list markers, "4 / 11" page numbers, coloured links.
    # Defaults to this blue; set to None for plain black instead
    # 'typst_slides_accent': '#0e2f92',
    # The current '#' section small in the top-left corner (on by default;
    # the deck's title where there is no section)
    # 'typst_slides_running_header': False,
    # To change the whole look, copy the bundled template and edit it (README §7):
    #   octavo template copy slides/typst-slides.typ

    # ================================================================
    # The speaker script (typst-notes) — the same deck, A4, with the
    # ::: notes that typst-slides drops. Every typst_slides_* key above
    # applies here too. Put it in a document's targets to build it every
    # time, or just ask for it: octavo build <name> --to typst-notes
    # Its look: octavo template copy slides/typst-notes.typ, then edit it
    # ================================================================

    # ================================================================
    # Slides (Beamer — only if TeX is installed)
    # ================================================================
    # 'beamer_theme': 'metropolis',    # default is 'default'
    # 'beamer_aspectratio': '169',
    # 'beamer_slide_level': 2,         # '## heading' becomes one slide
    # 'beamer_notes': False,           # True prints speaker notes into the PDF
    # 'slides_bibliography': False,    # True adds a bibliography slide at the end

    # ================================================================
    # Word
    # ================================================================
    # Generate a template with `octavo reference-docx reference.docx`, adjust
    # its styles in Word, then point to it here. Its content doesn't matter
    # — only the style definitions are used.
    # 'docx_reference': 'reference.docx',
}
