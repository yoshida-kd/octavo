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
    # A manuscript lives in docs/<name>/<name>.md (its appendix.md and a paper's
    # main.typ layout in the same folder): one document per folder, named after it.
    # What it makes goes at the top of the manuscript:
    #   outputs: [pdf, slides]   # pdf / word / tex / slides / beamer / script (pdf if not written)
    #   sessions: true           # made of several class sessions (one deck each)
    'documents': {
        'docs': {'src': 'docs/*/'},
        # The older places are read too (written with profile, targets, split_slides):
        # 'papers': {'src': 'papers/*/paper.md', 'appendix': 'papers/*/appendix.md',
        #            'profile': 'paper', 'targets': ['typst']},
        # 'lectures': {'src': 'lectures/*.md', 'profile': 'handout',
        #              'targets': ['typst', 'typst-slides'], 'split_slides': True},
    },
    # Without documents, the older shortcuts (draft.md / slides.md / handout.md) are still read.

    # ================================================================
    # Bibliography (Zotero -> .bib -> journal style)
    # ================================================================
    # One .bib file is the source of truth — drop your Zotero export here
    # as-is.
    #   octavo checkbib                            cross-check citation keys
    'bib_file': 'literature.bib',

    # Target journal's citation style: a CSL style ID, or a path to a .csl
    # file.
    #   octavo csl list          styles you already have
    #   octavo csl get apa       fetch one (look up IDs at https://www.zotero.org/styles)
    # Short aliases also work: apa / chicago / ieee / mla / nature / ...
    'csl': 'chicago-author-date',
    # 'csl_locale': 'ja-JP',        # defaults based on lang
    # 'citations_by_language': True,  # Japanese documents: English works in English, Japanese ones (langid) the Japanese way
    # 'reference_section_title': 'References',   # set to '' to omit the heading

    # Bibliography issues you've reviewed and are deliberately leaving as-is
    # (octavo checkbib stops flagging these).
    # 'bib_accepted': {('yamada2020', 'no page range or DOI'): 'bulletin uses a running number instead'},

    # ================================================================
    # Language
    # ================================================================
    'lang': 'en',                 # 'ja' | 'en'
    # 'east_asian_line_breaks': True,   # don't insert spaces at Japanese line breaks

    # ================================================================
    # Figures & tables
    # ================================================================
    # made by hand: figures drawn in Typst (<name>.typ), photos, tables (<name>.csv)
    'figure_src_dir': 'figures',
    'table_src_dir': 'tables',
    # written by the analysis and octavo build (the manuscript places figures from here)
    'figure_dir': 'assets/figures',
    'table_dir': 'assets/tables',
    # 'figure_width': 1.0,              # fraction of \textwidth
    # 'figure_ext': {'typst': '.png'},  # override the defaults (Word .png, the rest .pdf)

    # Figure, table and equation numbers. The manuscript never types them; it
    # labels things ({#fig-…}) and refers to them by name (@fig-…)
    'crossref_numbering': 'section',  # 'section' (Figure 2.1) | 'document' (Figure 1)
    # Table of contents. None: only lecture-note handouts get one (not papers or slides); True / False for every document
    # 'toc': None,
    # 'toc_depth': 2,                  # heading depth listed (lecture notes: 1 = sessions only, 2 = sessions and sections)
    # 'first_section': 1,              # number of the first section (0 makes a guidance session "0")
    # How `date:` is shown on title slides and handouts; `date: today` is the build day.
    # None: 2026年10月14日 in Japanese, October 14, 2026 in English
    # 'date_format': '%Y-%m-%d',
    # Japanese works in a Japanese document: 'standard' (2020)「…」 | 'fullwidth' （2020）…巻…号、…頁。 | 'period' ．2020．…
    # 'japanese_citation_form': 'standard',

    # ================================================================
    # Analysis (Quarto .qmd)
    # ================================================================
    # The .qmd files that produce the paper's numbers, figures and tables.
    # octavo build runs `quarto render` on any .qmd that is newer than its
    # output (with Quarto missing it warns and carries on).
    #   analysis side: ov_value("n_obs", nrow(d)) / ov_figure(p, "trend")
    #                  ov_table(tab, "summary")        <- helpers from octavo.R
    #   manuscript:    {{n_obs}} / ![Trend](../../assets/figures/trend.png){#fig-trend} /
    #                  `: Descriptive statistics {#tbl-summary}` (the table goes there)
    'analysis': [],               # e.g. ['analysis/*.qmd']
    # To watch data files too, make an entry a dict instead of a string
    # 'analysis': [{'src': 'analysis/main.qmd', 'deps': ['data/*.csv']}],
    # 'analysis_deps': [],        # dependencies shared by every .qmd
    # 'analysis_to': None,        # quarto render --to (None leaves it to the .qmd)
    # 'analysis_args': [],        # extra arguments passed to quarto
    # 'analysis_auto': True,      # False to run only on `octavo analysis run`

    # Where the analysis writes its values, and the default format for {{...}}
    'values_dir': 'assets/values',
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
        # 'affiliation': 'Example University',   # these two go into a new .qmd's header
        # 'email': 'jane@example.org',
    },

    # ================================================================
    # Output directories (default: under build/)
    # ================================================================
    # 'out_dirs': {'latex': 'build/tex', 'docx': 'build/word'},

    # ================================================================
    # LaTeX
    # ================================================================
    # 'latex_engine': 'lualatex',
    # 'latex_documentclass': 'ltjsarticle',   # defaults based on lang
    # 'latex_classoptions': ['11pt', 'a4paper'],
    # The preamble: octavo template copy handout/handout-header.tex, then edit it

    # Numbered blocks (::: {.question #question-why}): case, question, aside, nb, memo,
    # theorem, … come built in. Rename one or add your own (the guide, "Writing manuscripts"):
    # 'theorem_envs': {'claim': {'name': {'ja': '主張', 'en': 'Claim'}, 'counter': 'case'}},

    # ================================================================
    # Typst
    # ================================================================
    # 'typst_citations': 'csl',     # 'csl' (same style as other formats) | 'native'
    # A4 handouts (lecture notes); the layout is templates/handout/handout.typ.
    # Font default: BIZ UDGothic, with Inter for Latin
    # 'font': ['BIZ UDMincho', 'Noto Serif CJK JP'],
    # 'fontsize': '11pt',
    # 'pagebreak': 'session',  # 'session' | 'section' (each #) | None (only at session markers)

    # ================================================================
    # Slides (Typst — no TeX needed)
    # ================================================================
    # 'slides_aspect': '16-9',   # '16-9' | '4-3'
    # Default: BIZ UDGothic with Inter for Latin; a list you write is used as-is
    # 'slides_font': ['BIZ UDGothic', 'Noto Sans CJK JP'],
    # Number the headings (a Typst numbering string). None = no numbers
    # 'slides_numbering': '1.1',
    # Give each '#' section a divider slide (default: no divider, the counter still advances)
    # 'slides_section_slides': True,
    # Accent colour. **Setting this switches the look**: titles in colour rather
    # than bold, ▶ list markers, "4 / 11" page numbers, coloured links.
    # Defaults to this blue; set to None for plain black instead
    # 'slides_accent': '#0e2f92',
    # The current '#' section small in the top-left corner (on by default;
    # the deck's title where there is no section)
    # 'slides_running_header': False,
    # To change the whole look, copy the bundled template and edit it (the guide, "Making it yours"):
    #   octavo template copy slides/typst-slides.typ

    # ================================================================
    # The speaker script (script) — the pages of the deck on A4, with the
    # ::: notes that the slides drop. Every slides_* key above
    # applies here too. Put it in a manuscript's outputs to build it every
    # time, or just ask for it: octavo build <name> --to script
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
    # `octavo template copy word` writes templates/word/reference.docx; adjust its
    # styles in Word and Word output uses it. To use another .docx, point to it here.
    # Its content doesn't matter — only the style definitions are used.
    # 'docx_reference': 'reference.docx',
}
