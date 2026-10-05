# -*- coding: utf-8 -*-
"""octavo の単体テスト。

    python3 -m unittest discover -s tests -v
    あるいは  python3 tests/test_octavo.py

pandoc が要るテストは、なければ自動で飛ばす。CSL 引用（pandoc 2.11 以上）が
ない環境でも通るように、変換のテストは --no-citations 相当で実行する。
"""
from __future__ import annotations

import ast
import contextlib
import io
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# 開発者自身の ~/.config/octavo/templates（ひな型の上書き）をテストに効かせない。
# 上書きを見るテストは、それぞれ XDG_CONFIG_HOME を自分の一時フォルダに向ける。
os.environ['XDG_CONFIG_HOME'] = tempfile.mkdtemp(prefix='octavo-test-config-')
sys.path.insert(0, str(ROOT))

import octavo                                                        # noqa: E402
from octavo import (analysis, audit, bib, build, bundle, check, theorems,      # noqa: E402
                      config, crossref, csl, dataset, doctor, envsetup, lint, md,
                      pandocrun, paths, review, scaffold, selftest, tmpl, values)
from octavo import backends as be                                    # noqa: E402
from octavo.backends.base import Ctx                                 # noqa: E402


def ded(s: str) -> str:
    return textwrap.dedent(s).lstrip('\n')


def make_project(dest: Path, docs=(('paper', 'paper'),), lang: str = 'ja',
                 example: bool = True, analysis: bool = True, legacy: bool = True,
                 **kw) -> Path:
    """octavo init のあと octavo new で分析と原稿を足す（テストで使うプロジェクト）。

    既定では見本（分析・仮の値・仮の図表・書誌・原稿の例・論文の付録）で作る。
    `init --example` と同じ中身だが、見本の論文（example-paper）は足さない
    （文書の数や名前を見るテストがあるため）。example=False なら骨組みだけ、
    analysis=False なら分析も足さない（init の既定と同じ）。

    legacy=True（既定）は前からの置き場所（papers/<名前>/paper.md・slides/・lectures/）の
    プロジェクト: 設定から docs/*/ の行を抜いてから足す。多くのテストがこの形で書いて
    あり、前からのプロジェクトが同じに動くことの確かめにもなっている。
    legacy=False は今の init のまま（docs/<名前>/<名前>.md）。
    """
    scaffold.init(dest, lang=lang, quiet=True, **kw)
    cfg = dest / 'octavo.config.py'
    if legacy:
        text = cfg.read_text(encoding='utf-8')
        text = re.sub(r"        'docs': \{\n            'src': 'docs/\*/',\n        \},\n", '', text)
        cfg.write_text(text, encoding='utf-8')
    if analysis:
        scaffold.new(cfg, 'analysis', 'analysis', quiet=True, example=example)
    for kind, name in docs:
        scaffold.new(cfg, kind, name, quiet=True, example=example,
                     appendix=example and kind == 'paper')
    return dest


ALL_KINDS = (('paper', 'paper'), ('slides', 'slides'), ('lecture', '講義'))

# テストで使う架空の著者名。ひな型は '著者名' という placeholder しか持たないので、
# 名前の突き合わせを試すところはここから取る。
AUTHOR = '佐藤 花子'


def contextlib_redirect():
    """わざと失敗させるときのエラー表示を黙らせる。"""
    import contextlib
    import io
    return contextlib.redirect_stderr(io.StringIO())
PAPER_MD = 'papers/paper/paper.md'

HAVE_PANDOC = shutil.which('pandoc') is not None
HAVE_QUARTO = shutil.which('quarto') is not None
HAVE_R = shutil.which('Rscript') is not None


# =====================================================================
class FrontMatter(unittest.TestCase):
    def test_scalars_and_lists(self):
        meta, body = md.split_front_matter(ded('''
            ---
            title: "論文の題: 副題つき"
            author:
              - 佐藤 花子
              - 共著 太郎
            date: 2026-08-11
            keywords: [a, b, c]
            ---

            本文。
        '''))
        self.assertEqual(meta['title'], '論文の題: 副題つき')
        self.assertEqual(meta['author'], ['佐藤 花子', '共著 太郎'])
        self.assertEqual(meta['keywords'], ['a', 'b', 'c'])
        self.assertEqual(body.strip(), '本文。')

    def test_no_front_matter(self):
        meta, body = md.split_front_matter('# 見出し\n')
        self.assertEqual(meta, {})
        self.assertEqual(body, '# 見出し\n')

    def test_yaml_block_quotes_when_needed(self):
        out = md.to_yaml_block({'title': 'A: B', 'author': ['x', 'y']})
        self.assertIn('title: "A: B"', out)
        self.assertIn('  - x', out)
        self.assertTrue(out.startswith('---'))


# =====================================================================
class Structure(unittest.TestCase):
    def test_split_abstract_with_wordcount(self):
        ab, rest = md.split_abstract(ded('''
            ## Abstract

            要旨の中身。

            *Word count: 120 words*

            ## 1. はじめに
        '''))
        self.assertEqual(ab, '要旨の中身。')
        self.assertNotIn('要旨の中身', rest)
        self.assertIn('はじめに', rest)

    def test_split_abstract_japanese_heading(self):
        ab, rest = md.split_abstract('## 要旨\n\n本文の要旨。\n\n## 1. はじめに\n')
        self.assertEqual(ab, '本文の要旨。')

    def test_an_empty_abstract_does_not_swallow_the_next_section(self):
        # 書き始めの原稿（見出しだけ）。次の節が要旨に移ると本文の番号がずれる
        text = '## Abstract\n\n## はじめに {#sec-intro}\n\n## 分析 {#sec-analysis}\n'
        ab, rest = md.split_abstract(text)
        self.assertEqual(ab, '')
        self.assertEqual(rest, '## はじめに {#sec-intro}\n\n## 分析 {#sec-analysis}\n')
        # 字数の行がずっと後ろにあっても、見出しをまたいで取らない
        ab, rest = md.split_abstract('## Abstract\n\n## はじめに\n\n本文\n\n*Word count: 10*\n')
        self.assertEqual(ab, '')
        self.assertIn('## はじめに', rest)

    def test_drop_references(self):
        out = md.drop_references('本文\n\n## 参考文献\n\n山田 2020\n')
        self.assertNotIn('山田 2020', out)
        self.assertIn('本文', out)

    def test_drop_references_only_at_heading(self):
        # 本文中に「参考文献」という語が出てきても落とさない
        out = md.drop_references('参考文献の整理について論じる。\n')
        self.assertIn('論じる', out)

    def test_strip_title_block(self):
        # `# 題` が1つだけで、あとに `##` の節が続くなら、それは題
        out = md.strip_title_block('# 題\n\n著者\n\n## はじめに\n\n本文\n')
        self.assertTrue(out.startswith('## はじめに'))

    def test_strip_title_block_keeps_top_level_sections(self):
        # `#` を節に使う原稿（`#` が2つ以上）は最初の見出しから
        src = '前置き\n\n# はじめに\n\n## 用語\n\n# 分析\n'
        self.assertTrue(md.strip_title_block(src).startswith('# はじめに'))

    def test_tidy_drops_rules_and_notes_but_not_headings(self):
        out = md.tidy_headings('## 分析 {#sec-analysis}\n\n---\n\n*(Typst では…)*\n\n本文\n')
        self.assertIn('## 分析 {#sec-analysis}', out)
        self.assertNotIn('---', out)
        self.assertNotIn('Typst では', out)


# =====================================================================
class ConditionalDivs(unittest.TestCase):
    SRC = ded('''
        共通の文。

        ::: {.slides-only}
        スライド専用。
        :::

        ::: {.handout-only}
        プリント専用。
        :::

        ::: {.no-web}
        ウェブ以外。
        :::

        ::: {.warning}
        ふつうの div。
        :::

        ::: notes
        発表者ノート。
        :::
    ''')

    def test_slides(self):
        out = md.filter_divs(self.SRC, {'slides', 'screen', 'beamer'}, keep_notes=True)
        self.assertIn('スライド専用', out)
        self.assertNotIn('プリント専用', out)
        self.assertIn('ウェブ以外', out)
        self.assertIn('発表者ノート', out)
        self.assertIn('::: notes', out)
        self.assertIn('::: {.warning}', out)          # 印のない div は囲みも残す
        self.assertNotIn('slides-only', out)          # 条件付きの囲みは外す

    def test_print(self):
        out = md.filter_divs(self.SRC, {'print', 'doc', 'latex', 'handout'})
        self.assertNotIn('スライド専用', out)
        self.assertIn('プリント専用', out)
        self.assertIn('ウェブ以外', out)
        self.assertNotIn('発表者ノート', out)

    def test_only_prefix_spelling(self):
        out = md.filter_divs('::: {.only-slides}\nX\n:::\n', {'slides'})
        self.assertIn('X', out)
        out = md.filter_divs('::: {.only-slides}\nX\n:::\n', {'print'})
        self.assertNotIn('X', out)

    def test_nested(self):
        src = ded('''
            ::: {.handout-only}
            外。
            ::: {.warning}
            中。
            :::
            :::
            後ろ。
        ''')
        out = md.filter_divs(src, {'slides'})
        self.assertNotIn('外。', out)
        self.assertNotIn('中。', out)
        self.assertIn('後ろ。', out)
        out = md.filter_divs(src, {'handout'})
        self.assertIn('外。', out)
        self.assertIn('中。', out)
        self.assertIn('::: {.warning}', out)


# =====================================================================
class TheoremBlocks(unittest.TestCase):
    """事例・論点などのブロック: 番号・参照・再掲・一覧。pandoc は呼ばない。"""

    SRC = ded("""
        # ガイダンス

        本文では @question-why と [-@case-civil] を指す。

        ::: nb
        私語は禁止する。
        :::

        # 公務員とは

        ::: {.case #case-civil}
        公務員は少ない。
        :::

        ::: {.question #question-why title="なぜか"}
        なぜ政府か。
        :::

        ::: {.list-of .question}
        :::
        """)

    def test_blocks_share_a_counter_and_reset_per_section(self):
        items = {it.label: it for it in crossref.number(self.SRC).items if it.label}
        self.assertEqual(items['case-civil'].number, '2.1')
        self.assertEqual(items['question-why'].number, '2.2')
        self.assertEqual(items['question-why'].word, '論点')
        self.assertEqual(items['question-why'].title, 'なぜか')

    def test_the_list_is_not_counted_as_a_block(self):
        kinds = [it.kind for it in crossref.number(self.SRC).items]
        self.assertEqual(kinds.count('question'), 1)

    def test_first_section_zero(self):
        items = {it.label or it.number: it for it in crossref.number(self.SRC, start=0).items}
        self.assertEqual(items['case-civil'].number, '1.1')
        secs = [it.number for it in crossref.number(self.SRC, start=0).items if it.kind == 'sec']
        self.assertEqual(secs, ['0', '1'])

    def test_references_to_blocks_are_not_citations(self):
        self.assertEqual(md.cited_keys(self.SRC), set())

    def test_config_adds_and_renames_kinds(self):
        cfg = {'lang': 'ja', 'theorem_envs': {'case': '事例その', 'claim': {
            'name': {'ja': '主張', 'en': 'Claim'}, 'counter': 'case'}, 'hint': {
            'name': 'ヒント', 'numbered': False}}}
        envs = crossref.theorem_envs(cfg)
        self.assertEqual(envs['case'].word, '事例その')
        self.assertEqual(envs['claim'].counter, 'case')
        self.assertIsNone(envs['hint'].counter)
        self.assertIn('claim', crossref.kinds_of(envs))
        self.assertNotIn('hint', crossref.kinds_of(envs))

    def test_restate_and_list_are_expanded_from_the_whole_document(self):
        envs = crossref.theorem_envs({'lang': 'ja', 'theorem_envs': {}})
        blocks = theorems.collect([(self.SRC, False)], envs, 'section')
        self.assertEqual([b.label for b in blocks], [None, 'case-civil', 'question-why'])
        out = theorems.expand('::: {.restate #question-why}\n:::\n', blocks, envs)
        self.assertIn('octavo-restated n=2', out)
        self.assertIn('なぜ政府か。', out)
        report = []
        theorems.expand('::: {.restate #question-nothing}\n:::\n', blocks, envs, report)
        self.assertIn('question-nothing', report[0])

    def test_labels_inside_a_copy_are_dropped(self):
        envs = crossref.theorem_envs({'lang': 'ja', 'theorem_envs': {}})
        src = '# A\n\n::: {.case #case-x}\n![図](a.png){#fig-a}\n:::\n\n::: {.restate #case-x}\n:::\n'
        out = theorems.expand(src, theorems.collect([(src, False)], envs, 'section'), envs)
        self.assertEqual(out.count('#fig-a'), 1)


class TheoremBlocksBuilt(unittest.TestCase):
    """組んだ出力（Typst の A4 プリント・LaTeX・Word）。"""

    BODY = ded("""
        ---
        title: 講義
        first_section: 0
        ---

        # ガイダンス

        @question-why を見る。

        ::: {.session #first title="第1回" date="2026-10-08"}
        :::

        # 公務員とは

        ::: {.question #question-why title="なぜか"}
        なぜ政府か。
        :::

        ::: nb
        注意の本文。
        :::

        # 論点集 {.appendix}

        ::: {.restate #question-why}
        :::
        """)

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        make_project(self.d / 'p', docs=(('lecture', 'notes'),), example=False, analysis=False)
        (self.d / 'p/lectures/notes.md').write_text(self.BODY, encoding='utf-8')
        self.cfg = config.load(self.d / 'p/octavo.config.py')

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def out(self, target: str, doc: str = 'notes') -> str:
        r = build.build_one(self.cfg, self.cfg.document(doc), target,
                            citations=False, offline=True)
        self.assertTrue(r.ok, '\n'.join(r.report))
        return r.outputs[0].read_text(encoding='utf-8') if target != 'docx' else ''

    @unittest.skipUnless(HAVE_PANDOC, 'pandoc が要る')
    def test_typst_handout(self):
        typ = self.out('typst')
        self.assertIn('first-section: 0', typ)
        self.assertIn('#octavo-theorem("case", [論点], lang: "ja", title: [なぜか])[', typ)
        self.assertIn('] <question-why>', typ)
        self.assertIn('numbered: false', typ)                  # 注意
        self.assertIn('#octavo-session("first", title: "第1回")', typ)
        self.assertIn('#show: octavo-appendix', typ)
        self.assertIn('#octavo-restate(word: [論点], lang: "ja", target: <question-why>, '
                      'number: "1.1"', typ)
        # 区切りがあるので `#` ごとの改ページはしない（区切りで必ず改ページ）
        self.assertIn('pagebreak: none', typ)

    @unittest.skipUnless(HAVE_PANDOC, 'pandoc が要る')
    def test_latex_handout(self):
        tex = self.out('latex')
        self.assertIn('\\begin{question}[なぜか]\\label{question-why}', tex)
        self.assertIn('\\newtheorem{question}[case]{論点}', tex)
        self.assertIn('\\setcounter{section}{-1}', tex)
        self.assertIn('\\appendix', tex)
        self.assertIn('論点\\ref{question-why}', tex)

    @unittest.skipUnless(HAVE_PANDOC and shutil.which('typst'), 'pandoc と typst が要る')
    def test_it_compiles_and_the_numbers_come_out(self):
        r = build.build_one(self.cfg, self.cfg.document('notes'), 'typst',
                            citations=False, offline=True, do_compile=True)
        self.assertTrue(r.ok, '\n'.join(r.report))
        if shutil.which('pdftotext'):
            text = subprocess.run(['pdftotext', '-enc', 'UTF-8', str(r.compiled), '-'], capture_output=True,
                                  text=True, encoding='utf-8').stdout
            self.assertIn('論点 1.1', text)                    # 参照と、ブロックの頭
            self.assertIn('ガイダンス', text)

    @unittest.skipUnless(HAVE_PANDOC and shutil.which('typst'), 'pandoc と typst が要る')
    def test_the_session_deck_keeps_the_handout_numbers(self):
        r = build.build_one(self.cfg, self.cfg.document('notes-first'), 'typst-slides',
                            citations=False, offline=True, do_compile=True)
        self.assertTrue(r.ok, '\n'.join(r.report))
        if shutil.which('pdftotext'):
            text = subprocess.run(['pdftotext', '-enc', 'UTF-8', str(r.compiled), '-'], capture_output=True,
                                  text=True, encoding='utf-8').stdout
            self.assertIn('論点 1.1', text)
            self.assertIn('2026 年 10 月 8 日', text)            # 区切りの date

    @unittest.skipUnless(HAVE_PANDOC, 'pandoc が要る')
    def test_session_outputs_name_what_they_are(self):
        """回ごとのスライド・台本は <文書>-slides-<回> / <文書>-notes-<回>（配布資料は <文書>-<回>）。"""
        out = self.cfg.out_dir('typst-slides', self.cfg.document('notes'))
        out.mkdir(parents=True, exist_ok=True)
        legacy = out / 'notes-first.pdf'                         # 前の版の名前
        legacy.write_bytes(b'old')
        r = build.build_one(self.cfg, self.cfg.document('notes-first'), 'typst-slides',
                            citations=False, offline=True)
        self.assertTrue(r.ok, '\n'.join(r.report))
        self.assertEqual(r.outputs[0].name, 'notes-slides-first.typ')
        self.assertFalse(legacy.exists())
        self.assertEqual(be.get('typst-notes').file_stem('notes-first', 'first'),
                         'notes-notes-first')
        self.assertEqual(be.get('typst-notes').file_stem('deck'), 'deck-notes')
        self.assertEqual(be.get('typst-slides').file_stem('deck'), 'deck')
        stale = out / 'notes-slides-gone.pdf'
        stale.write_bytes(b'old')
        gone = build.clear_old_sessions(self.cfg, self.cfg.document('notes'), 'typst-slides',
                                        ['notes-first'])
        self.assertEqual(gone, ['notes-slides-gone.pdf'])
        self.assertTrue((out / 'notes-slides-first.typ').exists())

    @unittest.skipUnless(HAVE_PANDOC and shutil.which('typst'), 'pandoc と typst が要る')
    def test_the_appendix_heading_on_a_deck_has_no_number_unless_slides_are_numbered(self):
        """番号を振らないスライドで、付録の見出しが「0.1」になっていた。"""
        def deck():
            r = build.build_one(self.cfg, self.cfg.document('notes-first'), 'typst-slides',
                                citations=False, offline=True, do_compile=True)
            self.assertTrue(r.ok, '\n'.join(r.report))
            return r
        typ = deck().outputs[0].read_text(encoding='utf-8')
        self.assertIn('#show: octavo-appendix.with(heading-numbering: none)', typ)
        if shutil.which('pdftotext'):
            text = subprocess.run(['pdftotext', '-enc', 'UTF-8', str(deck().compiled), '-'],
                                  capture_output=True, text=True, encoding='utf-8').stdout
            self.assertIn('論点集', text)
            self.assertNotIn('0.1', text)
        self.cfg._v['slides_numbering'] = '1.1'
        typ = deck().outputs[0].read_text(encoding='utf-8')
        self.assertIn('#show: octavo-appendix\n', typ)

    @unittest.skipUnless(HAVE_PANDOC and shutil.which('typst'), 'pandoc と typst が要る')
    def test_extract_cuts_one_pdf_per_session(self):
        from octavo import extract
        r = extract.run(self.cfg, 'notes', offline=True)
        self.assertEqual([k for k, _ in r['made']], ['first'])
        table = json.loads(r['table'].read_text(encoding='utf-8'))
        s = table['sessions'][0]
        self.assertEqual(s['key'], 'first')
        self.assertGreater(s['first'], table['body'] - 1)
        # 印字のページ番号は全体のまま（表紙・目次の後の本文が 1 から）
        self.assertEqual(s['shown_first'], str(s['first'] - table['body'] + 1))
        self.assertTrue(r['made'][0][1].is_file())
        self.assertEqual(r['made'][0][1].name, 'notes-first.pdf')
        with self.assertRaises(extract.ExtractError):
            extract.run(self.cfg, 'notes', sessions=['nope'], offline=True)

    @unittest.skipUnless(HAVE_PANDOC and shutil.which('typst'), 'pandoc と typst が要る')
    def test_extract_json_has_what_the_extension_reads(self):
        # extension.ts の octavo.extract が読むのは ok / error / made[].pdf
        from octavo import cli
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = cli.main(['extract', 'notes', '--json', '--offline',
                             '-c', str(self.d / 'p/octavo.config.py')])
        res = json.loads(buf.getvalue().strip().split('\n')[-1])
        self.assertEqual(code, 0)
        self.assertTrue(res['ok'])
        self.assertTrue(Path(res['made'][0]['pdf']).is_file())
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = cli.main(['extract', 'notes', '--json', '--offline', '-s', 'nope',
                             '-c', str(self.d / 'p/octavo.config.py')])
        res = json.loads(buf.getvalue().strip().split('\n')[-1])
        self.assertFalse(res['ok'])
        self.assertIn('nope', res['error'])

    @unittest.skipUnless(HAVE_PANDOC, 'pandoc が要る')
    def test_word_writes_the_numbers(self):
        self.out('docx')
        docx = self.cfg.out_dir('docx', self.cfg.document('notes')) / 'notes.docx'
        text = subprocess.run(['pandoc', str(docx), '-t', 'plain'], capture_output=True,
                              text=True).stdout
        self.assertIn('論点1.1（なぜか）', text)
        self.assertIn('付録A', text)

    @unittest.skipUnless(HAVE_PANDOC, 'pandoc が要る')
    def test_theorem_envs_in_the_config_does_not_crash_the_build(self):
        # 表示用の tag() をローカル変数が隠して、theorem_envs を書くと build が落ちていた
        cp = self.d / 'p/octavo.config.py'
        cp.write_text(cp.read_text(encoding='utf-8').replace(
            "CONFIG = {", "CONFIG = {\n    'theorem_envs': {'case': '事例', 'nb': '注意'},", 1),
            encoding='utf-8')
        self.cfg = config.load(cp)
        self.assertIn('\\begin{question}', self.out('latex'))
        self.assertIn('#octavo-theorem', self.out('typst'))

    def test_a_paper_body_imports_the_block_functions(self):
        from octavo.backends.typst import TypstBackend
        b = TypstBackend()
        ctx = Ctx(cfg=self.cfg, backend=b, out_dir=self.d, profile='paper')
        out = b.postprocess('#octavo-theorem("case", [事例])[x]\n', ctx)
        self.assertTrue(out.startswith('#import "crossref.typ": octavo-theorem'))


class SessionMarkers(unittest.TestCase):
    """回の区切り（`::: {.session}`）。"""

    SRC = ded("""
        ---
        title: 講義
        date: 2026-04-01
        ---

        前置き

        # ガイダンス

        ::: {.session #first title="第1回" subtitle="副" date="2026-10-08"}
        :::

        # 公務員とは

        ## 小節

        ::: {.session}
        :::

        # 政策と政府

        本文

        ```
        ::: {.session #fake}
        :::
        ```
        """)

    def test_markers_decide_the_sessions(self):
        self.assertEqual(md.section_keys(self.SRC), [('first', '第1回'), ('02', '政策と政府')])

    def test_the_marker_fills_the_title_slide(self):
        meta, body = md.split_front_matter(md.section_part(self.SRC, 'first'))
        self.assertEqual((meta['title'], meta['subtitle'], meta['date']), ('第1回', '副', '2026-10-08'))
        self.assertIn('# 公務員とは', body)                  # 題は区切りなので見出しは残る

    def test_without_a_title_the_first_heading_is_used_and_dropped(self):
        meta, body = md.split_front_matter(md.section_part(self.SRC, '02'))
        self.assertEqual((meta['title'], meta['subtitle']), ('政策と政府', '講義'))
        self.assertNotIn('# 政策と政府', body)
        self.assertIn('::: {.session #fake}', body)           # コードの中は区切りではない

    def test_section_numbers_before_a_session(self):
        # first: 前に `#` が1つ（ガイダンス）、回の中に自分の `#` がある
        self.assertEqual(md.session_start_sections(self.SRC, 'first'), (1, True))
        # 02: 題にした `#`（政策と政府）がこの回の節
        self.assertEqual(md.session_start_sections(self.SRC, '02'), (3, False))

    def test_heading_sessions_still_work_without_markers(self):
        src = '# 第1回\n\n本文\n\n# 第2回 {#second}\n\n本文\n'
        self.assertEqual(md.section_keys(src), [('01', '第1回'), ('second', '第2回')])
        self.assertEqual(md.session_start_sections(src, 'second'), (2, False))

    def test_spans_follow_the_markers(self):
        spans = md.section_spans(self.SRC)
        self.assertEqual([k for k, *_ in spans], ['first', '02'])
        lines = self.SRC.split('\n')
        self.assertTrue(lines[spans[0][2] - 1].startswith('::: {.session #first'))


class SlideMarks(unittest.TestCase):
    """スライドの区切りと題（`::: {.slide}`・`{.same-slide}`・`{slide-title=…}`）。"""

    SRC = ded("""
        # 公務員とは

        ## 定員の推移 {#sec-teiin slide-title="定員"}

        前半。

        ::: {.slide}
        :::

        後半。

        ## 細目 {.same-slide}

        細目の本文。

        ::: {.slide title="比べる"}
        :::

        ```
        ::: {.slide}
        :::
        ```
        """)

    def test_on_slides(self):
        out = md.slide_marks(self.SRC, True, 'ja')
        self.assertIn('## 定員 {#sec-teiin slide-title="定員"}', out)   # ラベルはそのまま
        self.assertIn('## 定員（続き） {.unnumbered}', out)
        self.assertIn('**細目**', out)
        self.assertIn('## 比べる {.unnumbered}', out)
        self.assertIn('```\n::: {.slide}\n:::\n```', out)               # コードの中は見ない

    def test_elsewhere_only_the_markers_go(self):
        out = md.slide_marks(self.SRC, False, 'ja')
        self.assertIn('## 定員の推移 {#sec-teiin slide-title="定員"}', out)
        self.assertIn('## 細目 {.same-slide}', out)
        self.assertNotIn('比べる', out)
        self.assertEqual(out.count('::: {.slide}'), 1)                   # コードの中の1つだけ

    def test_english_continuation(self):
        out = md.slide_marks('## Results\n\nA.\n\n::: {.slide}\n:::\n\nB.\n', True, 'en')
        self.assertIn('## Results (cont.) {.unnumbered}', out)

    def test_with_sections_and_slides_the_slide_is_the_deeper_one(self):
        """回のスライドで `##` 節・`###` スライドのとき、区切りは `###` の1枚になる
        （`##` の節になっていた）。`##` だけなら `##`。"""
        src = '## 節\n\n### 1枚目\n\n前半。\n\n::: {.slide}\n:::\n\n後半。\n\n#### 細目\n'
        out = md.slide_marks(src, True, 'ja')
        self.assertIn('### 1枚目（続き） {.unnumbered}', out)
        out = md.slide_marks('## 1枚目\n\nA.\n\n::: {.slide}\n:::\n', True, 'ja')
        self.assertIn('## 1枚目（続き） {.unnumbered}', out)

    @unittest.skipUnless(HAVE_PANDOC and shutil.which('typst'), 'pandoc と typst が要る')
    def test_a_deck_that_cites_nothing_has_no_references_slide(self):
        d = Path(tempfile.mkdtemp())
        try:
            make_project(d / 'p', docs=(('lecture', 'notes'),), example=False, analysis=False)
            (d / 'p/lectures/notes.md').write_text(ded("""
                # 第1回 {#one}

                ## 節

                ### 1枚目

                本文。
                """), encoding='utf-8')
            cfg = config.load(d / 'p/octavo.config.py')
            r = build.build_one(cfg, cfg.document('notes-one'), 'typst-slides', offline=True)
            self.assertTrue(r.ok, '\n'.join(r.report))
            typ = r.outputs[0].read_text(encoding='utf-8')
            self.assertNotIn('{#refs}', typ)
            self.assertNotIn('参考文献', typ.split('#let octavo')[0] + typ.split('\n= ', 1)[-1])
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_session_takes_its_slide_title(self):
        src = '# 第1回 とても長い題 {#first slide-title="第1回"}\n\n本文\n'
        self.assertEqual(md.section_keys(src), [('first', '第1回')])


class DisplayDate(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(build.display_date('2026-10-08', None, 'ja'), '2026年10月8日')
        self.assertEqual(build.display_date('2026-10-08', None, 'en'), 'October 8, 2026')
        self.assertEqual(build.display_date('2026-10-08', '%Y/%m/%d', 'ja'), '2026/10/08')
        self.assertEqual(build.display_date('2026年度前期', None, 'ja'), '2026年度前期')
        import datetime
        self.assertEqual(build.display_date('today', '%Y-%m-%d', 'ja'),
                         datetime.date.today().isoformat())


class ListIndents(unittest.TestCase):
    def test_shallow_and_mixed(self):
        src = '- a\n  - b\n    - c\n- d\n    - e\n\n1. one\n  - two\n   - three\n'
        self.assertEqual([(l, k) for l, k, _ in lint.list_indents(src)],
                         [(5, 'mixed'), (8, 'shallow')])

    def test_code_and_front_matter_are_skipped(self):
        src = '---\ntitle: x\n---\n\n```\n1. a\n  - b\n```\n'
        self.assertEqual(lint.list_indents(src), [])

    def test_consistent_four_spaces_is_fine(self):
        self.assertEqual(lint.list_indents('- a\n    - b\n        - c\n'), [])


class AnalysisHeader(unittest.TestCase):
    def test_the_qmd_header_takes_the_author_from_meta(self):
        d = Path(tempfile.mkdtemp())
        try:
            scaffold.init(d / 'p', lang='ja', quiet=True)
            cp = d / 'p/octavo.config.py'
            text = cp.read_text(encoding='utf-8').replace(
                "'author': '著者名',", "'author': '著者名', 'affiliation': '所属', "
                "'email': 'a@example.org',")
            cp.write_text(text, encoding='utf-8')
            scaffold.new(cp, 'analysis', 'model', quiet=True)
            qmd = (d / 'p/analysis/model.qmd').read_text(encoding='utf-8')
            self.assertIn('title: "model"', qmd)
            self.assertIn('  - name: "著者名"\n    affiliation: "所属"\n    email: "a@example.org"', qmd)
            self.assertIn('date-modified: today', qmd)
            self.assertIn('embed-resources: true', qmd)
            self.assertIn('lang: ja', qmd)
            self.assertNotIn('@@', qmd)
        finally:
            shutil.rmtree(d, ignore_errors=True)


# =====================================================================
class RebaseLinks(unittest.TestCase):
    """図のパスを「原稿から見た相対」から「出力先から見た相対」へ。

    原稿は `![](../assets/figures/x.png)` とエディタで見える形で書く。出力は
    build/ の下で階層が違うので、そのままコピーすると組版が file not found で
    落ちる。キャプション付きの図は fmt_figure が名前から作り直すので
    無事だったが、**キャプションのない図だけが素通りして落ちていた。**
    """

    def rebase(self, text: str, src: str, out: str) -> str:
        return md.rebase_links(text, Path('/p') / src, Path('/p') / out)

    def test_slides_and_papers_gain_a_level(self):
        self.assertEqual(
            self.rebase('![](../assets/figures/a.png)', 'slides', 'build/typst-slides'),
            '![](../../assets/figures/a.png)')
        self.assertEqual(
            self.rebase('![図](../../assets/figures/a.png "説明")',
                        'papers/x', 'build/typst/x'),
            '![図](../../../assets/figures/a.png "説明")')

    def test_angle_bracket_form(self):
        self.assertEqual(
            self.rebase('![](<../assets/figures/b.png>)', 'slides', 'build/typst-slides'),
            '![](<../../assets/figures/b.png>)')

    def test_external_targets_are_left_alone(self):
        for target in ('https://example.com/a.png', '/abs/a.png',
                       'data:image/png;base64,AAAA'):
            src = f'![]({target})'
            self.assertEqual(self.rebase(src, 'slides', 'build/typst-slides'), src)

    def test_plain_links_are_not_images(self):
        src = '[リンク](../notes/a.md)'
        self.assertEqual(self.rebase(src, 'slides', 'build/typst-slides'), src)

    def test_code_is_left_alone(self):
        # 原稿が「図はこう書く」と見本を載せることがある。そこを書き換えると
        # 読者に誤った内容を見せる（{{…}} で同じことをやって直した）
        src = ded("""
            ```markdown
            ![](../assets/figures/a.png)
            ```

            インラインは `![](../assets/figures/a.png)` と書く。
        """)
        self.assertEqual(self.rebase(src, 'slides', 'build/typst-slides'), src)

    def test_same_directory_is_untouched(self):
        src = '![](assets/figures/a.png)'
        self.assertEqual(self.rebase(src, 'x', 'x'), src)


class Citations(unittest.TestCase):
    def test_cited_keys(self):
        keys = md.cited_keys('@a2020 と [@b2019; @c-2018] と \\poscite{d2017}。\n'
                             'メールは foo@example.com。\n')
        self.assertLessEqual({'a2020', 'b2019', 'c-2018', 'd2017'}, keys)
        self.assertNotIn('example.com', keys)

    def test_cited_keys_skips_references_section(self):
        keys = md.cited_keys('@a2020\n\n## 参考文献\n\n@zzz9999\n')
        self.assertIn('a2020', keys)
        self.assertNotIn('zzz9999', keys)

    def test_poscite_expansion(self):
        out = md.replace_poscite('\\poscite{x}の議論', lambda k: f'[{k}]')
        self.assertEqual(out, '[x]の議論')


# =====================================================================
BIB = ded('''
    @article{smith2003,
      author = {Smith, Alice and Taylor, Bob},
      title = {An Example Article},
      journaltitle = {JPART},
      date = {2003},
      pages = {441--468},
      langid = {english},
    }

    @book{exampleorg2011,
      author = {{Example Organization}},
      title = {Report},
      publisher = {Example Organization},
      date = {2011},
      file = {/home/x/zotero/storage/ABC/report.pdf},
      abstract = {長い要約が入っている},
    }

    @article{yamada2020,
      author = {山田 太郎 and 田中 花子},
      title = {日本語の論文},
      journaltitle = {見本学会誌},
      date = {2020},
      langid = {japanese},
    }

    @article{noyear,
      author = {Someone, A.},
      title = {No Year},
      journaltitle = {J},
    }
''')


class BibTeX(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.p = self.dir / 'lit.bib'
        self.p.write_text(BIB, encoding='utf-8')
        self.e = bib.parse(self.p)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_parse(self):
        self.assertEqual(len(self.e), 4)
        self.assertEqual(self.e['smith2003']['type'], 'article')
        self.assertEqual(self.e['smith2003']['pages'], '441--468')

    def test_surnames(self):
        self.assertEqual(bib.surnames(self.e['smith2003']), ['Smith', 'Taylor'])
        self.assertEqual(bib.surnames(self.e['exampleorg2011']), ['Example Organization'])
        self.assertEqual(bib.surnames(self.e['yamada2020']), ['山田', '田中'])

    def test_possessive(self):
        self.assertEqual(bib.possessive(self.e['smith2003'], 'en'),
                         "Smith and Taylor's")
        self.assertEqual(bib.possessive(self.e['yamada2020'], 'ja'), '山田・田中')

    def test_year(self):
        self.assertEqual(bib.year(self.e['smith2003']), '2003')
        self.assertEqual(bib.year(self.e['noyear']), 'n.d.')

    def test_problems(self):
        bad, ok = bib.problems(self.e, set(self.e))
        kinds = {(k, w) for k, w, _ in bad}
        self.assertIn(('noyear', 'no year (shows as [n.d.])'), kinds)
        self.assertIn(('yamada2020', 'no page range or DOI'), kinds)

    def test_a_japanese_name_without_a_comma_is_reported(self):
        """「山田 太郎」は BibTeX では太郎が姓。「山田, 太郎」と書くよう知らせる。"""
        e = {'a': {'type': 'article', 'author': '山田 太郎 and 田中 花子', 'date': '2020',
                   'pages': '1--2', 'journaltitle': 'J', 'langid': 'japanese'},
             'b': {'type': 'article', 'author': '山田, 太郎 and {日本学会}', 'date': '2020',
                   'pages': '1--2', 'journaltitle': 'J', 'langid': 'japanese'}}
        bad, _ = bib.problems(e, {'a', 'b'})
        hits = [(k, d) for k, w, d in bad if w.startswith('Japanese name without a comma')]
        self.assertEqual(hits, [('a', '山田 太郎 -> 山田, 太郎')])

    def test_accepted_silences(self):
        acc = {('noyear', '年がない（[n.d.] と出る）'): '刊行年不明の資料'}
        bad, ok = bib.problems(self.e, set(self.e), acc)
        self.assertTrue(any(k == 'noyear' for k, _, _ in ok))
        self.assertFalse(any(k == 'noyear' and w.startswith('no year')
                             for k, w, _ in bad))

    def test_accepted_matches_either_language(self):
        """指摘は英語が元だが、日本語の表示を書き写した bib_accepted も効く。"""
        for issue in ('no page range or DOI', 'ページも DOI もない'):
            bad, ok = bib.problems(self.e, set(self.e), {('yamada2020', issue): '紀要'})
            self.assertIn('yamada2020', {k for k, _, _ in ok}, issue)
            self.assertEqual(bib.accepted_reason({('yamada2020', issue): '紀要'},
                                                 'yamada2020', 'no page range or DOI'), '紀要')

    def test_clean_drops_noise_only(self):
        out = self.dir / 'clean.bib'
        n, p = bib.clean(self.p, out)
        t = p.read_text(encoding='utf-8')
        self.assertNotIn('file =', t)
        self.assertNotIn('abstract =', t)
        self.assertIn('title = {Report}', t)
        self.assertEqual(len(bib.parse(p)), 4)
        self.assertEqual(self.p.read_text(encoding='utf-8'), BIB)   # 元は無傷

    def test_duplicates(self):
        p2 = self.dir / 'dup.bib'
        p2.write_text(BIB + ded('''
            @article{smith2003a,
              author = {Smith, Alice},
              title = {An Example Article},
              date = {2003},
            }
        '''), encoding='utf-8')
        self.assertTrue(bib.duplicates(bib.parse(p2)))


# =====================================================================
class CSL(unittest.TestCase):
    def test_aliases(self):
        self.assertEqual(csl.style_id('apsa'),
                         'american-political-science-association')
        self.assertEqual(csl.style_id('APA'), 'apa')
        self.assertEqual(csl.style_id('some-journal.csl'), 'some-journal')

    def test_find_local_prefers_project(self):
        d = Path(tempfile.mkdtemp())
        try:
            (d / 'csl').mkdir()
            f = d / 'csl' / 'apa.csl'
            f.write_text('<style><title>APA</title></style>', encoding='utf-8')
            self.assertEqual(csl.find_local('apa', d), f.resolve())
            self.assertEqual(csl.title_of(f), 'APA')
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_chicago_falls_back_to_pandoc_default(self):
        # キャッシュは空のものに差し替える。setup.sh は chicago-author-date を
        # 取っておくので、実機の csl/ を見るとこのテストは環境次第で落ちる
        d = Path(tempfile.mkdtemp())
        try:
            with unittest.mock.patch.object(csl, 'CACHE_DIR', d / 'cache'):
                self.assertIsNone(csl.resolve('chicago-author-date', d,
                                              allow_download=False))
        finally:
            shutil.rmtree(d, ignore_errors=True)


# =====================================================================
class ConfigAndDocuments(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def write(self, body: str) -> config.Config:
        (self.d / 'octavo.config.py').write_text('CONFIG = ' + body, encoding='utf-8')
        return config.load(self.d / 'octavo.config.py')

    def test_defaults_and_paths(self):
        (self.d / 'draft.md').write_text('# x\n', encoding='utf-8')
        cfg = self.write("{'lang': 'ja'}")
        self.assertEqual(cfg['latex_documentclass'], 'ltjsarticle')
        self.assertEqual(cfg['csl_locale'], 'ja-JP')
        self.assertEqual(cfg['reference_section_title'], '参考文献')
        self.assertTrue(Path(cfg['bib_file']).is_absolute())
        self.assertEqual(Path(cfg['bib_file']).name, 'literature.bib')

    def test_english_defaults(self):
        cfg = self.write("{'lang': 'en'}")
        self.assertEqual(cfg['latex_documentclass'], 'article')
        self.assertEqual(cfg['reference_section_title'], 'References')

    def test_documents_autodetected(self):
        for n in ('draft.md', 'slides.md', 'handout.md'):
            (self.d / n).write_text('# x\n', encoding='utf-8')
        cfg = self.write('{}')
        self.assertEqual(set(cfg.documents), {'paper', 'slides', 'handout'})
        self.assertEqual(cfg.documents['slides'].profile, 'slides')
        self.assertEqual(cfg.documents['handout'].targets, ('typst',))

    def test_documents_explicit(self):
        (self.d / 'a.md').write_text('# x\n', encoding='utf-8')
        cfg = self.write("{'documents': {'講義': {'src': 'a.md', "
                         "'profile': 'handout', 'targets': ['latex', 'beamer']}}}")
        d = cfg.document('講義')
        self.assertEqual(d.targets, ('latex', 'beamer'))
        self.assertEqual(Path(d.src).name, 'a.md')

    def test_documents_glob(self):
        (self.d / 'lectures').mkdir()
        for n in ('lecture01', 'lecture02', 'lecture03'):
            (self.d / 'lectures' / f'{n}.md').write_text('# x\n', encoding='utf-8')
        cfg = self.write("{'documents': {'講義*': {'src': 'lectures/*.md', "
                         "'profile': 'handout', 'targets': ['latex', 'beamer']}}}")
        self.assertEqual(sorted(cfg.documents),
                         ['講義lecture01', '講義lecture02', '講義lecture03'])
        self.assertEqual(cfg.documents['講義lecture02'].profile, 'handout')
        self.assertEqual(cfg.documents['講義lecture02'].targets, ('latex', 'beamer'))

    def test_glob_name_is_what_the_star_matched(self):
        """論文はフォルダ単位（papers/<名前>/paper.md）なので、名前はファイル名ではなくフォルダ名。"""
        for n in ('mypaper', 'another'):
            (self.d / 'papers' / n).mkdir(parents=True)
            (self.d / 'papers' / n / 'paper.md').write_text('# x\n', encoding='utf-8')
        (self.d / 'papers' / 'mypaper' / 'appendix.md').write_text('# A\n', encoding='utf-8')
        cfg = self.write("{'documents': {'papers': {'src': 'papers/*/paper.md', "
                         "'appendix': 'papers/*/appendix.md', 'profile': 'paper'}}}")
        self.assertEqual(sorted(cfg.documents), ['another', 'mypaper'])
        self.assertEqual(cfg.rel(cfg.document('mypaper').appendix), 'papers/mypaper/appendix.md')
        self.assertIsNone(cfg.document('another').appendix)      # ない付録は結ばない
        self.assertEqual([cfg.rel(p) for _, p, _ in cfg.sources()],
                         ['papers/another/paper.md', 'papers/mypaper/paper.md',
                          'papers/mypaper/appendix.md'])

    def test_a_glob_with_no_manuscript_yet_is_quiet(self):
        import contextlib
        import io
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            cfg = self.write("{'documents': {'slides': {'src': 'slides/*.md', "
                             "'profile': 'slides'}}}")
        self.assertEqual(cfg.documents, {})
        self.assertEqual(err.getvalue(), '')

    def test_same_name_from_two_globs_exits(self):
        for sub in ('slides', 'lectures'):
            (self.d / sub).mkdir()
            (self.d / sub / 'x.md').write_text('# x\n', encoding='utf-8')
        with self.assertRaises(SystemExit):
            self.write("{'documents': {"
                       "'slides': {'src': 'slides/*.md', 'profile': 'slides'},"
                       "'lectures': {'src': 'lectures/*.md', 'profile': 'handout'}}}")

    def test_each_paper_gets_its_own_out_dir(self):
        """main.typ / body.typ は名前が決まっているので、論文が2本あるとぶつかる。"""
        for n in ('a', 'b'):
            (self.d / f'{n}.md').write_text('# x\n', encoding='utf-8')
        cfg = self.write("{'documents': {'a': {'src': 'a.md', 'profile': 'paper'}, "
                         "'b': {'src': 'b.md', 'profile': 'slides'}}}")
        a, b = cfg.document('a'), cfg.document('b')
        self.assertEqual(cfg.out_dir('typst', a), cfg.out_dir('typst') / 'a')
        self.assertEqual(cfg.out_dir('latex', a), cfg.out_dir('latex') / 'a')
        # 完結した文書はファイル名が文書名なので、形式ごとの1フォルダでよい
        self.assertEqual(cfg.out_dir('docx', a), cfg.out_dir('docx'))
        self.assertEqual(cfg.out_dir('typst-slides', b), cfg.out_dir('typst-slides'))

    def test_split_sessions_are_documents_by_name(self):
        (self.d / 'lectures').mkdir()
        (self.d / 'lectures' / 'n.md').write_text(
            '# A\n\n## x\n\n# B {#bee}\n\n## y\n\n# C\n', encoding='utf-8')
        cfg = self.write("{'documents': {'lectures': {'src': 'lectures/*.md', "
                         "'profile': 'handout', 'targets': ['typst', 'typst-slides'], "
                         "'split_slides': True}}}")
        doc = cfg.document('n')
        self.assertEqual([p.name for p in cfg.parts(doc)], ['n-01', 'n-bee', 'n-03'])
        part = cfg.document('n-bee')
        self.assertEqual((part.part, part.src, part.targets), ('bee', doc.src, doc.targets))
        self.assertEqual(set(cfg.documents), {'n'})       # 回は documents に並べない
        with self.assertRaises(SystemExit):
            cfg.document('n-02')                          # 2回目は {#bee} の名前

    def test_out_dirs_merge_with_defaults(self):
        cfg = self.write("{'out_dirs': {'latex': 'tex'}}")
        self.assertEqual(Path(cfg.out_dir('latex')).name, 'tex')
        self.assertEqual(Path(cfg.out_dir('docx')).name, 'word')

    def test_bad_profile_exits(self):
        (self.d / 'a.md').write_text('x', encoding='utf-8')
        with self.assertRaises(SystemExit):
            self.write("{'documents': {'x': {'src': 'a.md', 'profile': 'nope'}}}")

    def test_bad_lang_exits(self):
        with self.assertRaises(SystemExit):
            self.write("{'lang': 'fr'}")


# =====================================================================
class CheckbibReport(unittest.TestCase):
    """`collect()` は octavo checkbib と VS Code 拡張の両方が読む唯一のロジック。"""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / 'draft.md').write_text(
            '# t\n\n@smith2003 と @missingkey1234 を引く。\n', encoding='utf-8')
        (self.d / 'literature.bib').write_text(BIB, encoding='utf-8')
        (self.d / 'octavo.config.py').write_text(
            "CONFIG = {'draft': 'draft.md', 'bib_file': 'literature.bib'}",
            encoding='utf-8')
        self.cfg = config.load(self.d / 'octavo.config.py')

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_collect_shape(self):
        r = check.collect(self.cfg)
        self.assertEqual(r.entry_count, 4)
        self.assertIn('smith2003', r.entries)
        self.assertEqual(r.entries['smith2003']['year'], '2003')
        self.assertIn('missingkey1234', r.missing)
        self.assertNotIn('smith2003', r.missing)
        self.assertEqual(r.problem_count, len(r.missing) + len(r.problems))

    def test_to_json_roundtrips(self):
        r = check.collect(self.cfg)
        data = json.loads(json.dumps(r.to_json(), ensure_ascii=False))
        self.assertEqual(data['missing'], r.missing)
        self.assertEqual(set(data['entries']), set(r.entries))

    def test_run_json_exit_code_reflects_missing(self):
        self.assertEqual(check.run_json(self.cfg), 1)
        (self.d / 'draft.md').write_text('@smith2003\n', encoding='utf-8')
        cfg2 = config.load(self.d / 'octavo.config.py')
        self.assertEqual(check.run_json(cfg2), 0)


# =====================================================================
class Registry(unittest.TestCase):
    def test_all_backends_present(self):
        self.assertEqual(set(be.ALL),
                         {'latex', 'typst', 'beamer', 'typst-slides',
                          'typst-notes', 'typst-poster', 'docx'})

    def test_resolve_targets(self):
        self.assertEqual(be.resolve_targets('latex,docx', 'paper'), ['latex', 'docx'])
        self.assertEqual(be.resolve_targets('print', 'paper'), ['typst', 'docx'])
        self.assertEqual(be.resolve_targets(None, 'slides'), ['typst-slides'])
        self.assertEqual(be.resolve_targets(None, 'paper'), ['typst'])
        self.assertEqual(len(be.resolve_targets('all', 'paper')), len(be.ALL))

    def test_unknown_target_exits(self):
        with self.assertRaises(SystemExit):
            be.resolve_targets('epub', 'paper')
        with self.assertRaises(SystemExit):
            be.resolve_targets('html', 'paper')
        with self.assertRaises(SystemExit):
            be.resolve_targets('revealjs', 'paper')

    def test_doctor_knows_what_every_backend_needs(self):
        """doctor.NEEDS にない形式は「出せるか」を一度も見てもらえない。

        バックエンドを足したときに**黙って**漏れる（doctor は何も言わない）ので、
        表そのものを突き合わせる。TEX_TARGETS も、TeX が要る形式だけが
        入っていること。
        """
        from octavo import doctor
        self.assertEqual(set(be.ALL) - set(doctor.NEEDS), set(),
                         'doctor.NEEDS にない形式がある')
        self.assertEqual(set(doctor.NEEDS) - set(be.ALL), set(),
                         'doctor.NEEDS に不明な形式がある')
        self.assertEqual(set(doctor.TEX_TARGETS), {'latex', 'beamer'})

    def test_every_backend_has_an_out_dir(self):
        from octavo import config as configmod
        self.assertEqual(set(be.ALL) - set(configmod.DEFAULTS['out_dirs']), set())
        self.assertEqual(set(configmod.BACKENDS), set(be.ALL))

    def test_the_vscode_target_list_is_in_sync(self):
        """拡張の「変換する…」の一覧は手で合わせる決まり（自動生成ではない）。"""
        src = (ROOT / 'vscode-extension' / 'src' / 'extension.ts').read_text(encoding='utf-8')
        listed = set(re.findall(r"\{ id: '([\w-]+)'", src))
        self.assertEqual(listed, set(be.OUTPUTS))
        self.assertEqual(set(be.OUTPUTS.values()), set(be.ALL))      # どの形式も出力の名前を持つ

    def test_figure_ext_defaults(self):
        cfg = {'figure_ext': {}}
        self.assertEqual(be.get('latex').figure_ext(cfg), '.pdf')
        self.assertEqual(be.get('docx').figure_ext(cfg), '.png')
        self.assertEqual(be.get('latex').figure_ext({'figure_ext': {'latex': '.png'}}),
                         '.png')


# =====================================================================
class Packaging(unittest.TestCase):
    """clone して使っても pip で入れても、同梱物が見つかること。

    wheel では `templates/` と `config.example*.py` が
    `octavo/` の下に取り込まれる（pyproject.toml の force-include）。
    ルート直下に同梱物を足したら、そこにも足すこと——
    `test_every_bundled_resource_is_in_the_wheel` がそれを見張る。
    """

    def pyproject(self) -> dict:
        # tomllib は 3.11 から。requires-python は 3.10 以上なので、
        # 設定を読むテストだけ 3.10 では飛ばす。
        tomllib = __import__('tomllib') if sys.version_info >= (3, 11) else None
        if tomllib is None:
            self.skipTest('tomllib がない（Python 3.10）')
        with open(ROOT / 'pyproject.toml', 'rb') as fh:
            return tomllib.load(fh)

    def test_repo_layout_is_found(self):
        self.assertTrue((paths.templates_dir() / 'analysis/common/analysis/octavo.R').exists())
        self.assertTrue(paths.example_config().exists())
        self.assertTrue(paths.example_config('ja').name.endswith('.ja.py'))
        self.assertIsNotNone(paths.setup_script())

    def test_installed_layout_falls_back_into_the_package(self):
        """repo 直下になければパッケージの中を見る（pip で入れたとき）。"""
        with tempfile.TemporaryDirectory() as tmp:
            with unittest.mock.patch.object(paths, 'REPO', Path(tmp)):
                self.assertEqual(paths.templates_dir(),
                                 paths.PKG / 'templates')
                self.assertEqual(paths.example_config(),
                                 paths.PKG / 'config.example.py')
                self.assertIsNone(paths.setup_script())

    def test_csl_cache_is_writable_wherever_it_lands(self):
        """site-packages には書けないので、pip で入れたらキャッシュ領域へ。"""
        self.assertEqual(paths.csl_cache_dir(), paths.REPO / 'csl')
        with tempfile.TemporaryDirectory() as tmp:
            with unittest.mock.patch.object(paths, 'REPO', Path(tmp)), \
                 unittest.mock.patch.dict(os.environ,
                                          {'XDG_CACHE_HOME': tmp + '/c'}):
                self.assertEqual(paths.csl_cache_dir(),
                                 Path(tmp) / 'c' / 'octavo' / 'csl')

    def test_console_script_and_version(self):
        proj = self.pyproject()['project']
        self.assertEqual(proj['scripts'], {'octavo': 'octavo.cli:main'})
        import octavo
        self.assertEqual(self.pyproject()['tool']['hatch']['version']['path'],
                         'octavo/__init__.py')
        self.assertTrue(octavo.__version__)

    def test_no_runtime_dependencies(self):
        """標準ライブラリだけで動かす（最初に決めた制約）。"""
        self.assertEqual(self.pyproject()['project']['dependencies'], [])

    def test_every_bundled_resource_is_in_the_wheel(self):
        inc = (self.pyproject()['tool']['hatch']['build']['targets']
               ['wheel']['force-include'])
        for src, dest in inc.items():
            self.assertTrue((ROOT / src).exists(), f'{src} がない')
            self.assertTrue(dest.startswith('octavo/'),
                            f'{dest} はパッケージの外')
        for name in ('templates', 'config.example.py', 'config.example.ja.py'):
            self.assertIn(name, inc, f'{name} が wheel に入らない')


# =====================================================================
class DocSettings(unittest.TestCase):
    """文書ごとの設定: 原稿の冒頭（front matter）に書けば、その文書だけプロジェクトの
    設定より優先する（CSL・投稿規定の上限・スライドの体裁・出力形式）。"""

    def setUp(self):
        from octavo import confedit
        self.ce = confedit
        self.d = Path(tempfile.mkdtemp())
        self.root = make_project(self.d / 'p', docs=(('paper', 'mine'), ('slides', 'deck')),
                                 example=False)
        self.cfgp = self.root / 'octavo.config.py'
        self.paper = self.root / 'papers/mine/paper.md'
        self.deck = self.root / 'slides/deck.md'

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def cfg(self):
        return config.load(self.cfgp)

    def test_the_front_matter_is_read_with_types(self):
        text = ('---\ntitle: T\ncsl: apa\nword_limit: 8,000\ntargets: [typst, docx]\n'
                'slides_section_slides: true\ntypst_slides_accent: none\n---\n\nbody\n')
        got = config.doc_settings(self.paper, text=text)
        self.assertEqual(got, {'csl': 'apa', 'word_limit': 8000, 'targets': ('typst', 'docx'),
                               'slides_section_slides': True,
                               'slides_accent': None})
        self.assertNotIn('title', got)                    # タイトル部分のものは設定ではない
        for bad in ('word_limit: many', 'targets: [html]', 'slides_section_slides: maybe'):
            with self.assertRaises(SystemExit):
                config.doc_settings(self.paper, text=f'---\n{bad}\n---\n')

    def test_a_document_overrides_the_project_and_only_itself(self):
        self.ce.set_value(self.cfgp, 'word_limit', '10000')
        self.ce.set_doc_value(self.cfg(), self.cfg().document('mine'), 'word_limit', '8000')
        self.ce.set_doc_value(self.cfg(), self.cfg().document('mine'), 'csl', 'apa')
        self.ce.set_doc_value(self.cfg(), self.cfg().document('mine'), 'targets', 'typst,docx')
        cfg = self.cfg()
        mine = cfg.for_document(cfg.document('mine'))
        self.assertEqual((mine['word_limit'], mine['csl']), (8000, 'apa'))
        self.assertEqual(mine.doc_explicit, {'word_limit', 'csl', 'outputs'})
        self.assertEqual(cfg['word_limit'], 10000)                     # プロジェクトはそのまま
        self.assertEqual(cfg.for_document(cfg.document('deck'))['csl'], cfg['csl'])
        self.assertEqual(cfg.document('mine').targets, ('typst', 'docx'))
        self.assertEqual(cfg.document('mine').config_targets, ('typst',))
        # 冒頭の他の行はそのまま、上限は論文ごとに見る
        head = self.paper.read_text(encoding='utf-8').split('---')[1]
        self.assertIn('title:', head)
        self.assertIn('outputs: [pdf, word]', head)
        limits = {lab: lim for lab, _, lim, _ in audit.length_problems(cfg)}
        self.assertIn(8000, limits.values())
        # 消せばプロジェクトの値に戻る
        self.ce.set_doc_value(cfg, cfg.document('mine'), 'word_limit', None)
        cfg = self.cfg()
        self.assertEqual(cfg.for_document(cfg.document('mine'))['word_limit'], 10000)

    def test_what_can_be_set_depends_on_the_kind(self):
        cfg = self.cfg()
        paper = {r['key'] for r in self.ce.show(cfg, cfg.document('mine'))}
        deck = {r['key'] for r in self.ce.show(cfg, cfg.document('deck'))}
        self.assertIn('word_limit', paper)
        self.assertNotIn('slides_aspect', paper)
        self.assertIn('slides_aspect', deck)
        self.assertNotIn('word_limit', deck)
        self.assertTrue({'csl', 'outputs'} <= paper & deck)
        with self.assertRaises(self.ce.EditError):
            self.ce.set_doc_value(cfg, cfg.document('deck'), 'word_limit', '5')
        with self.assertRaises(self.ce.EditError):
            self.ce.set_doc_value(cfg, cfg.document('deck'), 'slides_aspect', '5-4')
        with self.assertRaises(self.ce.EditError):
            self.ce.set_value(self.cfgp, 'targets', 'typst')             # 文書ごとだけ
        # CSL はよく使うものを選べ、ほかの名前も書ける
        row = next(r for r in self.ce.show(cfg) if r['key'] == 'csl')
        self.assertEqual(row['kind'], 'suggest')
        self.assertIn('apa', row['choices'])

    def test_a_manuscript_without_front_matter_gets_one(self):
        self.deck.write_text('## Only a slide\n', encoding='utf-8')
        cfg = self.cfg()
        self.ce.set_doc_value(cfg, cfg.document('deck'), 'slides_aspect', '4-3')
        self.assertEqual(self.deck.read_text(encoding='utf-8'),
                         '---\nslides_aspect: 4-3\n---\n\n## Only a slide\n')
        # 次の行へ続く値は触らずに断る
        self.deck.write_text('---\ntargets:\n  - typst-slides\n---\n', encoding='utf-8')
        with self.assertRaises(self.ce.EditError):
            self.ce.set_doc_value(self.cfg(), self.cfg().document('deck'), 'targets', 'docx')

    @unittest.skipUnless(HAVE_PANDOC, 'pandoc がない')
    def test_the_build_uses_the_document_settings(self):
        if not pandocrun.at_least(3, 1):
            self.skipTest('pandoc 3.1 以上が要る')
        cfg = self.cfg()
        self.ce.set_doc_value(cfg, cfg.document('deck'), 'slides_aspect', '4-3')
        cfg = self.cfg()
        r = build.build_one(cfg, cfg.document('deck'), 'typst-slides',
                            citations=False, offline=True)
        self.assertTrue(r.ok, '\n'.join(r.report))
        typ = (cfg.out_dir('typst-slides') / 'deck.typ').read_text(encoding='utf-8')
        self.assertIn('aspect: "4-3"', typ)
        self.assertTrue(any('slides_aspect: 4-3' in line for line in r.report), r.report)


class ConfEdit(unittest.TestCase):
    """`octavo config` — 画面から設定を変える口（VS Code のサイドバーが使う）。

    手で書く Python を書き換えるので、「その行だけ変わる」「コメントは残る」
    「通らない値では何も変わらない」を見張る。
    """

    def setUp(self):
        from octavo import confedit
        self.ce = confedit
        self.d = Path(tempfile.mkdtemp())
        make_project(self.d / 'p', docs=(('slides', 'deck'),))
        self.path = self.d / 'p' / 'octavo.config.py'
        self.orig = self.path.read_text(encoding='utf-8')

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_set_then_unset_restores_the_file_exactly(self):
        self.ce.set_value(self.path, 'word_limit', '8000')
        self.ce.set_value(self.path, 'slides_numbering', '1.1')
        self.assertIn("    'word_limit': 8000,\n", self.path.read_text(encoding='utf-8'))
        self.assertEqual(config.load(self.path)['word_limit'], 8000)
        self.ce.set_value(self.path, 'word_limit', None)
        self.ce.set_value(self.path, 'slides_numbering', None)
        self.assertEqual(self.path.read_text(encoding='utf-8'), self.orig)

    def test_an_existing_line_keeps_its_comment(self):
        self.assertIn("'slides_aspect': '16-9',", self.orig)
        self.ce.set_value(self.path, 'slides_aspect', '4-3')
        text = self.path.read_text(encoding='utf-8')
        line = next(l for l in text.split('\n') if "'slides_aspect'" in l
                    and not l.lstrip().startswith('#'))
        old = next(l for l in self.orig.split('\n') if "'slides_aspect'" in l
                   and not l.lstrip().startswith('#'))
        self.assertIn("'4-3'", line)
        self.assertEqual(line.split('#', 1)[1:], old.split('#', 1)[1:])

    def test_16_9_is_not_arithmetic(self):
        k = self.ce.knob('slides_aspect')
        self.assertEqual(self.ce.parse_value(k, '16-9'), '16-9')

    def test_a_bad_value_leaves_the_file_alone(self):
        for key, raw in (('slides_accent', 'blue'),        # Config が弾く
                         ('slides_aspect', '5-4'),         # 選択肢にない
                         ('word_limit', 'many'),
                         ('lang', 'fr')):
            with self.assertRaises(self.ce.EditError, msg=key):
                self.ce.set_value(self.path, key, raw)
            self.assertEqual(self.path.read_text(encoding='utf-8'), self.orig, key)

    def test_keys_that_are_not_offered_are_refused(self):
        with self.assertRaises(self.ce.EditError):
            self.ce.set_value(self.path, 'documents', '{}')

    def test_a_multi_line_value_is_not_touched(self):
        text = self.orig.replace("    'lang': 'ja',", "    'lang': (\n        'ja'),")
        self.path.write_text(text, encoding='utf-8')
        with self.assertRaises(self.ce.EditError):
            self.ce.set_value(self.path, 'lang', 'en')
        self.assertEqual(self.path.read_text(encoding='utf-8'), text)

    def test_show_marks_what_is_written_and_what_is_default(self):
        rows = {r['key']: r for r in self.ce.show(config.load(self.path))}
        self.assertTrue(rows['lang']['explicit'])
        self.assertFalse(rows['word_limit']['explicit'])
        self.assertEqual(rows['slides_running_header']['value'], True)
        self.assertEqual([r['key'] for r in self.ce.show(config.load(self.path))],
                         [k.key for k in self.ce.KNOBS if k.project])

    def test_every_offered_key_exists_in_the_defaults(self):
        for k in self.ce.KNOBS:
            if k.project:
                self.assertIn(k.key, config.DEFAULTS, k.key)
            if k.docs:                     # 原稿の冒頭に書けるものは DOC_KEYS にある
                self.assertIn(k.key, config.DOC_KEYS, k.key)


# =====================================================================
class Messages(unittest.TestCase):
    """画面に出す文字列。**原文は英語**で、日本語は lang_ja.py の対訳表。

    言語は OCTAVO_LANG、なければロケール（LC_ALL / LC_MESSAGES / LANG）。
    訳がなければ英語のまま出て落ちないので、**抜けは誰にも知らされない**。
    それを数えるのがこのクラス。
    """
    SRC = sorted(list((ROOT / 'octavo').glob('*.py'))
                 + list((ROOT / 'octavo' / 'backends').glob('*.py')))

    def used(self) -> set:
        """コードの中の `t('…')` / `tag('…')` の原文。

        構文木から拾う。引用符の種類や行またぎの連結、文字列の中の引用符を
        正規表現で追うと必ず取りこぼすため。
        """
        out: set = set()
        for f in self.SRC:
            if f.name in ('lang_ja.py', 'i18n.py'):
                continue
            tree = ast.parse(f.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not node.args:
                    continue
                name = getattr(node.func, 'id', None)
                first = node.args[0]
                if not isinstance(first, ast.Constant) or not isinstance(first.value, str):
                    continue
                if name == 't':
                    out.add(first.value)
                elif name == 'tag':
                    out.add(f'[{first.value}]')
        # 表から引いて t() に渡すもの（呼び出しの形では見えない）
        from octavo import cli, doctor
        for table in (doctor.NEED_LABELS, doctor.HINTS, doctor.HINTS_MACOS, doctor.LABELS):
            out |= set(table.values())
        out |= {why for _cmd, why in cli.USAGE_LINES}
        from octavo import confedit
        out |= {k.label for k in confedit.KNOBS} | set(confedit.SECTIONS.values())
        from octavo import selftest
        out |= {label for checks in selftest.CHECKS.values() for label, _ in checks}
        from octavo import backends as be
        out |= {b.label for b in be.REGISTRY.values()}
        from octavo import review
        out |= set(review.WARNING_LINES)
        # checkbib の指摘: bib.problems() の (key, 指摘, 詳細) の真ん中
        src = (ROOT / 'octavo' / 'bib.py').read_text(encoding='utf-8')
        fn = next(n for n in ast.walk(ast.parse(src))
                  if isinstance(n, ast.FunctionDef) and n.name == 'problems')
        out |= {n.elts[1].value for n in ast.walk(fn)
                if isinstance(n, ast.Tuple) and len(n.elts) == 3
                and isinstance(n.elts[0], ast.Name) and isinstance(n.elts[1], ast.Constant)}
        return out

    def test_language_comes_from_the_environment(self):
        from octavo import i18n
        cases = {('en_US.UTF-8', None): 'en', ('ja_JP.UTF-8', None): 'ja',
                 ('en_US.UTF-8', 'ja'): 'ja', ('ja_JP.UTF-8', 'en'): 'en',
                 ('C', None): 'en'}
        for (loc, explicit), want in cases.items():
            env = {'LANG': loc}
            env['OCTAVO_LANG'] = explicit if explicit else ''
            with unittest.mock.patch.dict(os.environ, env, clear=False):
                if not explicit:
                    os.environ.pop('OCTAVO_LANG', None)
                os.environ.pop('LC_ALL', None)
                os.environ.pop('LC_MESSAGES', None)
                self.assertEqual(i18n.language(), want, (loc, explicit))

    def test_every_message_has_a_japanese_translation(self):
        from octavo.lang_ja import MESSAGES
        used = self.used()
        self.assertGreater(len(used), 200, 't() がほとんど見つかっていない')
        self.assertEqual(used - set(MESSAGES), set(), '日本語訳がない文字列')

    def test_no_unused_translations(self):
        from octavo.lang_ja import MESSAGES
        self.assertEqual(set(MESSAGES) - self.used(), set(), '使われていない訳')

    def test_slots_match_between_the_two_languages(self):
        """`{name}` の名前が原文と訳で食い違うと、訳のほうだけ穴が空く。"""
        from octavo.lang_ja import MESSAGES
        from octavo.i18n import _PLURAL, _SLOT
        def names(s):
            return set(_SLOT.findall(s)) | {m[0] for m in _PLURAL.findall(s)}
        for en, ja in MESSAGES.items():
            # 単複の形 `{n|file|files}` は英語にしかなく、訳は `{n}` で書くので、
            # 「片方で使う名前が、もう片方でも（どちらかの形で）使われている」を見る
            self.assertLessEqual(set(_SLOT.findall(en)), names(ja), f'訳で穴が空く: {en!r}')
            self.assertLessEqual(set(_SLOT.findall(ja)), names(en), f'訳だけの名前: {en!r}')

    def test_plural_forms(self):
        from octavo import i18n
        with unittest.mock.patch.dict(os.environ, {'OCTAVO_LANG': 'en'}):
            self.assertEqual(i18n.t('made {n} {n|file|files}', n=1), 'made 1 file')
            self.assertEqual(i18n.t('made {n} {n|file|files}', n=0), 'made 0 files')
            self.assertEqual(i18n.t('made {n} {n|file|files}', n='1,523'), 'made 1,523 files')
            self.assertEqual(i18n.t('{n|the one is|all # are} fine', n=1), 'the one is fine')
            self.assertEqual(i18n.t('{n|the one is|all # are} fine', n=3), 'all 3 are fine')
            # 数でないもの（名前の並び）は複数として扱う
            self.assertEqual(i18n.t('{n|is|are}', n='a, b'), 'are')
            # {{…}} は差し込みでも単複でもない
            self.assertEqual(i18n.t('{{a|b|c}} {n}', n=1), '{{a|b|c}} 1')
        with unittest.mock.patch.dict(os.environ, {'OCTAVO_LANG': 'ja'}):
            self.assertEqual(i18n.t('made {n} {n|file|files}', n=1), '1 ファイル作った')

    def test_every_plural_form_is_in_english_only(self):
        """日本語の訳に単複の形を書いても意味がない（書いたら書き間違い）。"""
        from octavo.lang_ja import MESSAGES
        from octavo.i18n import _PLURAL
        self.assertEqual([ja for ja in MESSAGES.values() if _PLURAL.search(ja)], [])

    def test_a_missing_translation_falls_back_to_english(self):
        from octavo import i18n
        with unittest.mock.patch.dict(os.environ, {'OCTAVO_LANG': 'ja'}):
            self.assertEqual(i18n.t('no such message, surely'),
                             'no such message, surely')

    def test_braces_that_are_not_slots_are_left_alone(self):
        """`{{n_obs}}` や `\\label{}` を壊さないこと（str.format を使わない理由）。"""
        from octavo import i18n
        self.assertEqual(i18n.t('{{n_obs}} and {x}', x='1'), '{{n_obs}} and 1')
        self.assertEqual(i18n.t('\\label{} {x}', x='2'), '\\label{} 2')

    def test_the_japanese_output_really_is_japanese(self):
        from octavo import i18n
        with unittest.mock.patch.dict(os.environ, {'OCTAVO_LANG': 'ja'}):
            self.assertEqual(i18n.tag('figure'), '[図]')
            self.assertIn('組版', i18n.t('failed:') + i18n.tag('typeset'))


# =====================================================================
class VSCodeExtensionL10n(unittest.TestCase):
    """拡張の表示文字列が英語で書かれ、日本語訳が揃っていること。

    ここを Python 側のテストで見張るのは、リポジトリに JS のテスト基盤が
    ないため。tsc は「訳がない」を見つけてくれない（実行時に原文のまま
    出るだけ）ので、機械で数えられるこれだけは数えておく。
    """
    EXT = ROOT / 'vscode-extension'

    def manifest(self) -> str:
        return (self.EXT / 'package.json').read_text(encoding='utf-8')

    def nls(self, name: str) -> dict:
        return json.loads((self.EXT / name).read_text(encoding='utf-8'))

    def test_manifest_keys_resolve_in_both_languages(self):
        used = set(re.findall(r'%([\w.]+)%', self.manifest()))
        self.assertTrue(used, '%key% が1つもない')
        en, ja = self.nls('package.nls.json'), self.nls('package.nls.ja.json')
        self.assertEqual(used - set(en), set(), 'package.nls.json にないキー')
        self.assertEqual(used - set(ja), set(), 'package.nls.ja.json にないキー')
        self.assertEqual(set(en), set(ja), '英語と日本語でキーが違う')
        self.assertEqual(set(en) - used, set(), '使われていないキー')

    def test_marketplace_listing_is_complete(self):
        """Marketplace に出すのに要るものが揃っていること。

        LICENSE は vsce が拡張のフォルダの中にしか探さないので、ルートの
        コピーを置いている。コピーが食い違わないよう中身まで比べる。
        """
        m = json.loads(self.manifest())
        self.assertNotIn('private', m, '"private": true だと vsce publish が断る')
        icon = self.EXT / m['icon']
        self.assertEqual(icon.suffix, '.png', 'Marketplace のアイコンは PNG でないと通らない')
        self.assertEqual(icon.read_bytes()[:8], b'\x89PNG\r\n\x1a\n')
        self.assertEqual((self.EXT / 'LICENSE').read_text(encoding='utf-8'),
                         (ROOT / 'LICENSE').read_text(encoding='utf-8'),
                         'vscode-extension/LICENSE をルートの LICENSE からコピーし直す')
        self.assertTrue((self.EXT / 'CHANGELOG.md').is_file())
        # CLI と拡張は同じ版番号で出す（公開のタグ v<版> が両方を指す）
        import octavo
        self.assertEqual(m['version'], octavo.__version__)
        self.assertIn(f"## {m['version']}",
                      (self.EXT / 'CHANGELOG.md').read_text(encoding='utf-8'),
                      'CHANGELOG.md に今の版の節がない')

    def test_manifest_has_no_japanese_left(self):
        """訳に回し忘れた文字列が残っていないこと。

        例外は problemMatcher の正規表現で、これは CLI の**出力**（日本語）を
        拾うためのもの。表示文字列ではない。
        """
        for line in self.manifest().splitlines():
            if '"regexp"' in line:
                continue
            self.assertIsNone(re.search(r'[ぁ-んァ-ヶ一-龠]', line),
                              f'訳に出していない日本語: {line.strip()}')

    def test_every_runtime_string_has_a_japanese_translation(self):
        bundle = self.nls('l10n/bundle.l10n.ja.json')
        found = set()
        for f in sorted((self.EXT / 'src').glob('*.ts')):
            src = f.read_text(encoding='utf-8')
            # 'a' + 'b' のような行またぎの連結を1つの文字列に均す
            src = re.sub(r"'\s*\+\s*'", '', src)
            for lit in re.findall(r"vscode\.l10n\.t\(\s*'((?:[^'\\]|\\.)*)'", src):
                found.add(re.sub(r'\\(.)',
                                 lambda m: {'n': '\n', 't': '\t'}.get(m.group(1), m.group(1)),
                                 lit))
        self.assertTrue(found, 'vscode.l10n.t( が1つもない')
        self.assertEqual(found - set(bundle), set(), '日本語訳がない文字列')
        self.assertEqual(set(bundle) - found, set(), '使われていない訳')

    def test_l10n_folder_is_declared(self):
        pkg = json.loads(self.manifest())
        self.assertEqual(pkg.get('l10n'), './l10n')


# =====================================================================
class PreviewContract(unittest.TestCase):
    """拡張の preview.ts が読む JSON の**キー名**が、CLI の出すものと合うこと。

    拡張側は TypeScript の interface で受けるだけなので、Python 側でキーの
    綴りを変えても tsc は何も言わず、プレビューが黙って動かなくなる。
    ここで両側を突き合わせておく。
    """
    PREVIEW = ROOT / 'vscode-extension' / 'src' / 'preview.ts'

    SIDEBAR = ROOT / 'vscode-extension' / 'src' / 'sidebar.ts'

    def fields(self, name: str, src=None) -> set:
        """preview.ts（か src）の `interface X { … }` の項目名。

        1行で書いたものも複数行のものもあるので、`{` から対応する `}` まで
        数えて取る（正規表現だと次の interface まで飲み込む）。
        """
        text = (src or self.PREVIEW).read_text(encoding='utf-8')
        m = re.search(r'(?:export )?interface %s\s*\{' % name, text)
        self.assertIsNotNone(m, f'interface {name} がない')
        depth, i = 1, m.end()
        while depth and i < len(text):
            depth += {'{': 1, '}': -1}.get(text[i], 0)
            i += 1
        body = re.sub(r'//.*', '', text[m.end():i - 1])
        return set(re.findall(r'(\w+)\s*\??\s*:', body))

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        make_project(self.d / 'p', docs=ALL_KINDS)
        self.cfg_path = self.d / 'p' / 'octavo.config.py'

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def cli_json(self, *argv) -> dict:
        from octavo import cli
        import io, contextlib
        args = cli.make_parser().parse_args(list(argv) + ['-c', str(self.cfg_path)])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            args.func(args)
        return json.loads(buf.getvalue().strip().split('\n')[-1])

    def test_documents_json_has_every_field_the_preview_reads(self):
        got = self.cli_json('documents', '--json')
        self.assertEqual(self.fields('DocumentsReport') - set(got), set())
        doc = next(d for d in got['documents'] if d['name'] == '講義')
        self.assertEqual(self.fields('DocInfo') - set(doc), set())
        self.assertEqual(self.fields('Part') - set(doc['parts'][0]), set())

    def test_doctor_json_has_every_field_the_setup_reads(self):
        """拡張の setup.ts は doctor --json を見て「セットアップ」を出すかを決める。"""
        got = doctor.as_json()
        src = ROOT / 'vscode-extension' / 'src' / 'setup.ts'
        self.assertEqual(self.fields('DoctorReport', src) - set(got), set())
        if got['r_editor'] is not None:          # R がない機械では null
            self.assertEqual(self.fields('REditor', src) - set(got['r_editor']), set())
        self.assertEqual(got['version'], octavo.__version__)
        self.assertEqual(set(got['analysis']), set(doctor.ANALYSIS_TOOLS))

    def test_build_json_has_every_field_the_preview_reads(self):
        from octavo import cli
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cli.print_results_json([build.Result(doc='x', target='typst')])
        got = json.loads(buf.getvalue())
        self.assertEqual(self.fields('BuildReport') - set(got), set())
        self.assertEqual(self.fields('BuildOne') - set(got['results'][0]), set())

    def test_config_json_has_every_field_the_sidebar_reads(self):
        got = self.cli_json('config', '--json')
        self.assertEqual(self.fields('ConfigReport', self.SIDEBAR) - set(got), set())
        self.assertEqual(self.fields('Setting', self.SIDEBAR) - set(got['settings'][0]),
                         set())

    def test_config_set_json_has_what_the_sidebar_reads(self):
        from octavo import cli
        import io, contextlib
        args = cli.make_parser().parse_args(
            ['config', 'set', 'word_limit', 'lots', '--json', '-c', str(self.cfg_path)])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = args.func(args)
        got = json.loads(buf.getvalue())
        self.assertEqual(code, 1)
        self.assertEqual(self.fields('SetReport', self.SIDEBAR) - set(got), set())

    ANALYSIS = ROOT / 'vscode-extension' / 'src' / 'analysis.ts'

    def test_analysis_json_has_every_field_the_extension_reads(self):
        got = self.cli_json('analysis', '--json')
        self.assertEqual(self.fields('AnalysisReport', self.ANALYSIS) - set(got), set())
        self.assertTrue(got['units'])
        self.assertEqual(self.fields('AnalysisUnit', self.ANALYSIS) - set(got['units'][0]),
                         set())

    SCAFFOLD = ROOT / 'vscode-extension' / 'src' / 'scaffold.ts'

    def test_new_json_has_every_field_the_extension_reads(self):
        """「足す」は octavo new --json の open を開く。パスは拡張機能が組み立てない。"""
        got = self.cli_json('new', 'slides', 'added-deck', '--json')
        self.assertEqual(self.fields('NewReport', self.SCAFFOLD) - set(got), set())
        self.assertTrue(got['ok'])
        self.assertTrue(got['open'].endswith('added-deck.md'))
        got = self.cli_json('new', 'analysis', 'extra', '--json')
        self.assertTrue(got['open'].endswith('extra.qmd'))
        # 手で作る図と表は、元のファイル（組んだ assets/ のものではなく）を開く
        got = self.cli_json('new', 'figure', 'dag', '--json')
        self.assertEqual(Path(got['open']).parent.name, 'figures')
        self.assertTrue(Path(got['open']).is_file())
        got = self.cli_json('new', 'table', 'compare', '--json')
        self.assertEqual(Path(got['open']).parent.name, 'tables')
        self.assertTrue(Path(got['open']).is_file())
        # 既にある論文に付録を足すと、付録を開く
        paper = next(n for n, d in config.load(self.cfg_path).documents.items()
                     if d.profile == 'paper')
        got = self.cli_json('new', 'paper', paper, '--appendix', '--json')
        self.assertTrue(got['ok'])
        self.assertTrue(got['open'].endswith('appendix.md'))
        got = self.cli_json('new', 'paper', 'added-deck', '--json')     # 名前がぶつかる
        self.assertFalse(got['ok'])
        self.assertIn('added-deck', got['error'])

    def test_the_preview_never_runs_the_analysis(self):
        """プレビューの組み直しで重い分析が走らないこと（古ければ帯とボタンで知らせる）。"""
        text = self.PREVIEW.read_text(encoding='utf-8')
        self.assertIn("'--no-analysis'", text)
        from octavo import cli
        args = cli.make_parser().parse_args(['build', '--no-analysis'])
        self.assertTrue(args.no_analysis)

    def test_the_preview_asks_for_the_commands_that_exist(self):
        """preview.ts が叩くサブコマンドが CLI にあること。"""
        text = self.PREVIEW.read_text(encoding='utf-8')
        for sub in ('documents', 'build'):
            self.assertIn(f"'{sub}'", text)
        from octavo import cli
        parser = cli.make_parser()
        actions = [a for a in parser._actions if hasattr(a, 'choices') and a.choices]
        names = set()
        for a in actions:
            names |= set(a.choices)
        self.assertIn('documents', names)

    def test_the_targets_the_preview_can_pick_are_real_backends(self):
        text = self.PREVIEW.read_text(encoding='utf-8')
        picked = set(re.findall(r"'(typst[\w-]*|latex|beamer|docx)'", text))
        self.assertTrue(picked)
        self.assertEqual(picked - set(be.ALL), set())


# =====================================================================
class Placeholders(unittest.TestCase):
    """図がまだなくても組版が通るように置く仮の画像。"""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_png_is_valid(self):
        p = scaffold.write_placeholder_png(self.d / 'x.png', 32, 16)
        raw = p.read_bytes()
        self.assertEqual(raw[:8], b'\x89PNG\r\n\x1a\n')
        self.assertIn(b'IHDR', raw[:32])
        self.assertTrue(raw.rstrip().endswith(b'IEND\xaeB`\x82'))

    def test_pdf_offsets_are_consistent(self):
        p = scaffold.write_placeholder_pdf(self.d / 'x.pdf')
        raw = p.read_bytes()
        self.assertTrue(raw.startswith(b'%PDF-'))
        self.assertTrue(raw.rstrip().endswith(b'%%EOF'))
        start = int(raw.split(b'startxref')[1].split()[0])
        self.assertEqual(raw[start:start + 4], b'xref')
        # xref に並んだ位置に実際にオブジェクトがあるか
        table = raw[start:].split(b'\n')[3:8]      # xref / 0 N / 自由項目 の次から
        for i, line in enumerate(table, start=1):
            off = int(line.split()[0])
            self.assertEqual(raw[off:off + 5], f'{i} 0 o'.encode())

    def test_selftest_fixtures_are_coherent(self):
        self.assertIn('\\poscite{smith2003}', selftest.DRAFT)
        self.assertIn('@smith2003', selftest.BIB.replace('@article{', '@'))
        for key in ('smith2003', 'yamada2020', 'exampleorg2011'):
            self.assertIn(key, selftest.BIB)


# =====================================================================
class Values(unittest.TestCase):
    """分析が出した数値を本文の {{…}} に差し込む。"""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / 'draft.md').write_text('# x\n', encoding='utf-8')
        (self.d / 'assets' / 'values').mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def cfg(self, extra: str = '') -> config.Config:
        (self.d / 'octavo.config.py').write_text(
            "CONFIG = {'lang': 'ja'" + extra + '}', encoding='utf-8')
        return config.load(self.d / 'octavo.config.py')

    def results(self, name: str, obj: dict) -> None:
        (self.d / 'assets' / 'values' / f'{name}.json').write_text(
            json.dumps(obj, ensure_ascii=False), encoding='utf-8')

    def sub(self, text: str, cfg=None, report=None) -> str:
        cfg = cfg or self.cfg()
        vals, _ = values.load(cfg)
        return values.substitute(text, vals, cfg, report)

    def test_int_gets_thousands_separator(self):
        self.results('a', {'n_obs': 1523})
        self.assertEqual(self.sub('N は {{n_obs}} だった'), 'N は 1,523 だった')

    def test_thousands_separator_can_be_turned_off(self):
        self.results('a', {'n_obs': 1523})
        cfg = self.cfg(", 'value_thousands_sep': False")
        self.assertEqual(self.sub('{{n_obs}}', cfg), '1523')

    def test_float_uses_default_format(self):
        self.results('a', {'coef': 0.34219})
        self.assertEqual(self.sub('{{coef}}'), '0.342')

    def test_inline_spec_wins(self):
        self.results('a', {'coef': 0.34219})
        self.assertEqual(self.sub('{{coef:.1f}} と {{coef}}'), '0.3 と 0.342')

    def test_object_form_carries_its_own_format(self):
        self.results('a', {'coef': {'value': 0.34219, 'fmt': '.2f',
                                    'note': 'モデル2'}})
        self.assertEqual(self.sub('{{coef}}'), '0.34')
        vals, _ = values.load(self.cfg())
        self.assertEqual(vals['coef'].note, 'モデル2')

    def test_string_value_passes_through(self):
        self.results('a', {'p': '< .001'})
        self.assertEqual(self.sub('*p* {{p}}'), '*p* < .001')

    def test_spaces_inside_braces_are_allowed(self):
        self.results('a', {'n_obs': 12})
        self.assertEqual(self.sub('{{ n_obs }}'), '12')

    def test_missing_value_is_left_in_place_and_reported(self):
        self.results('a', {'n_obs': 12})
        rep: list = []
        out = self.sub('{{n_obs}} と {{nope}}', report=rep)
        self.assertEqual(out, '12 と {{nope}}')          # 消さずに残す
        self.assertTrue(any('nope' in r and '[warning]' in r for r in rep))

    def test_latex_double_braces_are_not_touched(self):
        self.results('a', {'n_obs': 12})
        raw = r'\newcommand{\x}{{\bf y}} と {{n_obs}}'
        self.assertEqual(self.sub(raw), r'\newcommand{\x}{{\bf y}} と 12')

    def test_underscore_and_dot_in_names(self):
        self.results('a', {'m1.coef_x': 1.5})
        self.assertEqual(self.sub('{{m1.coef_x}}'), '1.500')

    def test_meta_keys_are_not_values(self):
        self.results('a', {'_generated': '2026-01-01', 'n_obs': 3})
        vals, _ = values.load(self.cfg())
        self.assertEqual(set(vals), {'n_obs'})

    def test_collision_between_files_warns(self):
        self.results('a', {'n_obs': 1})
        self.results('b', {'n_obs': 2})
        _, rep = values.load(self.cfg())
        self.assertTrue(any('is in both' in r for r in rep))

    def test_broken_json_is_reported_not_raised(self):
        (self.d / 'assets' / 'values' / 'bad.json').write_text('{ oops', encoding='utf-8')
        vals, rep = values.load(self.cfg())
        self.assertEqual(vals, {})
        self.assertTrue(any('cannot read' in r for r in rep))

    def test_referenced_collects_names(self):
        self.assertEqual(values.referenced('{{a}} と {{b:.2f}} と {{a}}'),
                         {'a', 'b'})
    def test_inline_code_is_left_alone(self):
        self.results('a', {'n_obs': 12})
        self.assertEqual(self.sub('`{{n_obs}}` と {{n_obs}}'), '`{{n_obs}}` と 12')

    def test_fenced_code_is_left_alone(self):
        self.results('a', {'n_obs': 12})
        src = ded("""
            前 {{n_obs}}

            ```markdown
            書き方の説明: {{n_obs}}
            ```

            後 {{n_obs}}
            """)
        out = self.sub(src)
        self.assertIn('書き方の説明: {{n_obs}}', out)
        self.assertIn('前 12', out)
        self.assertIn('後 12', out)

    def test_raw_passthrough_block_still_gets_values(self):
        """```{=latex} は組版に渡る中身なので置換する。"""
        self.results('a', {'n_obs': 12})
        src = '```{=latex}\n\\textbf{{{n_obs}}}\n```\n'
        self.assertIn(r'\textbf{12}', self.sub(src))

    def test_referenced_ignores_code(self):
        self.assertEqual(values.referenced('`{{a}}` と {{b}}'), {'b'})

    def test_missing_inside_code_is_not_reported(self):
        self.results('a', {})
        rep: list = []
        self.sub('`{{nope}}`', report=rep)
        self.assertEqual(rep, [])


# =====================================================================
class AnalysisUnits(unittest.TestCase):
    """.qmd の登録と、再実行の要否。"""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / 'draft.md').write_text('# x\n', encoding='utf-8')
        (self.d / 'analysis').mkdir()
        (self.d / 'data').mkdir()
        for n in ('one.qmd', 'two.qmd'):
            (self.d / 'analysis' / n).write_text('---\n---\n', encoding='utf-8')
        (self.d / 'data' / 'x.csv').write_text('a,b\n', encoding='utf-8')

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def cfg(self, extra: str) -> config.Config:
        (self.d / 'octavo.config.py').write_text(
            "CONFIG = {'lang': 'ja', " + extra + '}', encoding='utf-8')
        return config.load(self.d / 'octavo.config.py')

    def test_glob_expands_to_every_qmd(self):
        us = analysis.units(self.cfg("'analysis': ['analysis/*.qmd']"))
        self.assertEqual([u.src.name for u in us], ['one.qmd', 'two.qmd'])

    def test_dict_form_carries_deps(self):
        cfg = self.cfg("'analysis': [{'src': 'analysis/one.qmd',"
                       " 'deps': ['data/*.csv']}]")
        us = analysis.units(cfg)
        self.assertEqual(len(us), 1)
        self.assertEqual([p.name for p in us[0].deps], ['x.csv'])

    def test_common_deps_apply_to_all(self):
        cfg = self.cfg("'analysis': ['analysis/*.qmd'],"
                       " 'analysis_deps': ['data/*.csv']")
        us = analysis.units(cfg)
        self.assertTrue(all(u.deps for u in us))

    def test_bad_entry_exits(self):
        with self.assertRaises(SystemExit):
            analysis.units(self.cfg("'analysis': [123]"))

    def test_non_list_analysis_exits(self):
        with self.assertRaises(SystemExit):
            self.cfg("'analysis': 'analysis/one.qmd'")

    def test_stale_until_stamped_then_fresh(self):
        cfg = self.cfg("'analysis': ['analysis/one.qmd']")
        u = analysis.units(cfg)[0]
        self.assertTrue(analysis.is_stale(cfg, u, {}))
        analysis.write_stamp(cfg, {analysis.key(cfg, u): {'newest': u.newest()}})
        self.assertFalse(analysis.is_stale(cfg, u, analysis.read_stamp(cfg)))

    def test_touching_a_dependency_makes_it_stale(self):
        cfg = self.cfg("'analysis': [{'src': 'analysis/one.qmd',"
                       " 'deps': ['data/*.csv']}]")
        u = analysis.units(cfg)[0]
        analysis.write_stamp(cfg, {analysis.key(cfg, u): {'newest': u.newest()}})
        self.assertFalse(analysis.is_stale(cfg, u, analysis.read_stamp(cfg)))
        later = time.time() + 10
        os.utime(self.d / 'data' / 'x.csv', (later, later))
        self.assertTrue(analysis.is_stale(cfg, u, analysis.read_stamp(cfg)))

    def test_stamp_lives_in_values_dir(self):
        cfg = self.cfg("'analysis': ['analysis/one.qmd']")
        self.assertEqual(analysis.stamp_path(cfg).parent, Path(cfg['values_dir']))

    def test_run_without_quarto_warns_but_succeeds(self):
        if shutil.which('quarto'):
            self.skipTest('Quarto があるので「ないとき」の挙動は試せない')
        cfg = self.cfg("'analysis': ['analysis/one.qmd']")
        rep: list = []
        n, ok = analysis.run(cfg, report=rep)
        self.assertEqual(n, 0)
        self.assertTrue(ok)                       # 変換までは止めない
        self.assertTrue(any('no quarto' in r for r in rep))

    def test_missing_qmd_is_reported(self):
        cfg = self.cfg("'analysis': ['analysis/nope.qmd']")
        rep: list = []
        analysis.run(cfg, report=rep)
        self.assertTrue(any('not found' in r for r in rep))

    def test_hidden_files_are_not_watched(self):
        (self.d / 'data' / '.DS_Store').write_text('x', encoding='utf-8')
        cfg = self.cfg("'analysis': ['analysis/one.qmd'],"
                       " 'analysis_deps': ['data/*']")
        deps = analysis.units(cfg)[0].deps
        self.assertEqual([p.name for p in deps], ['x.csv'])

    def test_watch_paths_include_qmd_and_deps(self):
        cfg = self.cfg("'analysis': ['analysis/*.qmd'],"
                       " 'analysis_deps': ['data/*.csv']")
        names = {p.name for p in analysis.watch_paths(cfg)}
        self.assertEqual(names, {'one.qmd', 'two.qmd', 'x.csv'})


# =====================================================================
class ValuesInPreprocess(unittest.TestCase):
    """前処理を通したときに数値が本当に入るか（pandoc は要らない）。"""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / 'assets' / 'values').mkdir(parents=True)
        (self.d / 'assets' / 'values' / 'a.json').write_text(
            '{"n_obs": 1523, "coef": 0.342}', encoding='utf-8')
        (self.d / 'draft.md').write_text(ded("""
            ---
            title: 題
            ---

            ## 要旨

            標本 {{n_obs}} 件の分析。

            ## 1. はじめに

            係数は {{coef}}（{{coef:.1f}}）だった。
            """), encoding='utf-8')
        (self.d / 'octavo.config.py').write_text(
            "CONFIG = {'lang': 'ja'}", encoding='utf-8')
        self.cfg = config.load(self.d / 'octavo.config.py')

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def preprocess(self):
        doc = self.cfg.document('paper')
        backend = be.get('latex')
        ctx = Ctx(cfg=self.cfg, backend=backend, out_dir=self.d,
                  profile=doc.profile, doc_name='paper')
        ctx.values, _ = values.load(self.cfg)
        body, abstract = build.preprocess(self.cfg, doc, backend, ctx,
                                          md.read(Path(doc.src)))
        return body, abstract, ctx

    def test_body_and_abstract_both_get_values(self):
        body, abstract, ctx = self.preprocess()
        self.assertIn('係数は 0.342（0.3）だった', body)
        self.assertIn('標本 1,523 件', abstract)
        self.assertNotIn('{{', body)
        self.assertTrue(any(r.startswith('[values]') for r in ctx.report))


# =====================================================================
class LectureSplit(unittest.TestCase):
    """講義ノート1本を `#` の回ごとのスライドに分ける。pandoc は呼ばない。"""

    SRC = ded("""
        ---
        title: 講義の見本
        date: 2026-04-10
        ---

        前置き（プリントだけ）

        # 第1回

        ## 狙い

        ```python
        # これは見出しではない
        ```

        # 第2回 {#second}

        ## 例

        # 参考文献
        """)

    def test_sessions_and_their_keys(self):
        self.assertEqual(md.section_keys(self.SRC),
                         [('01', '第1回'), ('second', '第2回')])

    def test_a_session_takes_the_title_slide(self):
        meta, body = md.split_front_matter(md.section_part(self.SRC, '01'))
        self.assertEqual(meta['title'], '第1回')
        self.assertEqual(meta['subtitle'], '講義の見本')     # ノート全体の題は副題に
        self.assertEqual(meta['date'], '2026-04-10')
        self.assertIn('## 狙い', body)
        self.assertIn('# これは見出しではない', body)          # コードの中は分けない
        self.assertNotIn('前置き', body)
        self.assertNotIn('# 第1回', body)               # 見出しはタイトル部分に回した
        self.assertNotIn('## 例', body)

    def test_unknown_session_is_none(self):
        self.assertIsNone(md.section_part(self.SRC, '02'))

    def test_run_builds_the_handout_once_and_slides_per_session(self):
        d = make_project(Path(tempfile.mkdtemp()) / 'p', docs=(('lecture', '講義'),))
        try:
            cfg = config.load(d / 'octavo.config.py')
            calls = []

            def fake(cfg, doc, target, **kw):
                calls.append((doc.name, target))
                return build.Result(doc=doc.name, target=target)

            with unittest.mock.patch.object(build, 'build_one', side_effect=fake):
                build.run(cfg, ['講義'])
                self.assertEqual(calls, [('講義', 'typst'), ('講義-01', 'typst-slides'),
                                         ('講義-02', 'typst-slides')])
                calls.clear()
                build.run(cfg, ['講義-02'], targets=['typst-slides'])
                self.assertEqual(calls, [('講義-02', 'typst-slides')])
        finally:
            shutil.rmtree(d.parent, ignore_errors=True)


# =====================================================================
class ProjectScaffold(unittest.TestCase):
    """octavo init が共通部分を作り、octavo new が原稿を足すか。"""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def make(self, lang='ja', docs=ALL_KINDS, **kw) -> Path:
        return make_project(self.d / 'proj', docs=docs, lang=lang, **kw)

    def test_init_makes_the_research_tree_and_no_manuscript(self):
        d = self.d / 'p'
        scaffold.init(d, quiet=True)
        for rel in ('figures/.gitkeep', 'literature.bib',
                    'octavo.config.py', 'AGENTS.md', 'CLAUDE.md', 'README.md', '.gitignore'):
            self.assertTrue((d / rel).exists(), rel)
        # 分析も原稿も、足すまではない
        for rel in ('draft.md', 'appendix.md', 'papers', 'slides', 'lectures', 'build',
                    'analysis', 'data', 'tables', 'results', 'requirements.txt'):
            self.assertFalse((d / rel).exists(), rel)
        self.assertEqual(config.load(d / 'octavo.config.py').documents, {})

    def test_init_writes_nothing_to_delete_later(self):
        """既定では見本を置かない。仮の値・仮の図表・見本の書誌・notes/refs は作らない。"""
        for lang in ('ja', 'en'):
            d = self.d / f'bare-{lang}'
            scaffold.init(d, lang=lang, quiet=True)
            for rel in ('results', 'assets/figures/trend.png', 'assets/figures/trend.pdf',
                        'assets/tables/summary.typ', 'notes', 'refs'):
                self.assertFalse((d / rel).exists(), rel)
            for f in d.rglob('*'):
                if f.is_file() and f.name != 'AGENTS.md':     # AGENTS.md は印の説明を持つ
                    text = f.read_text(encoding='utf-8', errors='replace')
                    self.assertNotIn('octavo:example', text, f)
                    self.assertNotIn('@article', text, f)
                    self.assertNotIn('set.seed', text, f)
            # README は自分で書き足す骨組み
            self.assertLess(len((d / 'README.md').read_text(encoding='utf-8').splitlines()), 20)
            self.assertEqual(lint.leftovers(config.load(d / 'octavo.config.py')), [])

    def test_new_writes_only_headings(self):
        d = self.make(docs=ALL_KINDS, example=False)
        for rel in ('papers/paper/paper.md', 'slides/slides.md', 'lectures/講義.md'):
            text = (d / rel).read_text(encoding='utf-8')
            self.assertNotIn('octavo:example', text, rel)
            self.assertNotIn('{{', text, rel)
            self.assertNotIn('<!--', text, rel)
            self.assertRegex(text, r'\n#{1,2} ', rel)
        cfg = config.load(d / 'octavo.config.py')
        self.assertEqual([k for k, _ in md.section_keys(
            (d / 'lectures/講義.md').read_text(encoding='utf-8'))], ['01'])
        self.assertFalse((d / 'papers/paper/appendix.md').exists())
        self.assertFalse((d / 'papers/paper/main.tex').exists())
        self.assertTrue((d / 'papers/paper/main.typ').is_file())
        self.assertIsNone(cfg.document('paper').appendix)

    def test_appendix_and_tex_can_be_added_to_an_existing_paper(self):
        d = self.make(docs=(('paper', 'mypaper'),), example=False)
        paper = d / 'papers/mypaper/paper.md'
        paper.write_text('# 書きかけ\n', encoding='utf-8')
        self.assertEqual(scaffold.new(d / 'octavo.config.py', 'paper', 'mypaper',
                                      appendix=True, tex=True, quiet=True), 0)
        self.assertEqual(paper.read_text(encoding='utf-8'), '# 書きかけ\n')   # 触らない
        self.assertTrue((d / 'papers/mypaper/appendix.md').is_file())
        self.assertTrue((d / 'papers/mypaper/main.tex').is_file())
        cfg = config.load(d / 'octavo.config.py')
        self.assertEqual(cfg.rel(cfg.document('mypaper').appendix), 'papers/mypaper/appendix.md')
        # 付録・main.tex は論文にだけ
        with contextlib_redirect():
            self.assertEqual(scaffold.new(d / 'octavo.config.py', 'slides', 'deck',
                                          appendix=True, quiet=True), 1)
        self.assertFalse((d / 'slides/deck.md').exists())

    def test_init_example_is_a_whole_example(self):
        d = self.d / 'demo'
        scaffold.init(d, quiet=True, example=True)
        for rel in ('assets/values/analysis.json', 'assets/figures/trend.png', 'assets/figures/trend.pdf',
                    'assets/tables/summary.typ', 'docs/example-paper/example-paper.md',
                    'docs/example-paper/appendix.md', 'docs/example-paper/main.typ'):
            self.assertTrue((d / rel).exists(), rel)
        self.assertIn('set.seed', (d / 'analysis/analysis.qmd').read_text(encoding='utf-8'))
        self.assertIn('@article', (d / 'literature.bib').read_text(encoding='utf-8'))
        cfg = config.load(d / 'octavo.config.py')
        self.assertEqual(list(cfg.documents), ['example-paper'])
        # 見本の論文の {{…}} は仮の値ですべて埋まり、見本だと分かる印がある
        vals, _ = values.load(cfg)
        used = set()
        for _, src, _ in cfg.sources():
            used |= values.referenced(src.read_text(encoding='utf-8'))
        self.assertTrue(used)
        self.assertEqual(used - set(vals), set())
        self.assertTrue(values.placeholder_files(cfg))
        self.assertTrue(lint.leftovers(cfg))

    def test_the_project_does_not_depend_on_what_is_added(self):
        """種類の違いは原稿のテンプレートだけ。init が作るものは同じ。"""
        a = make_project(self.d / 'a' / 'proj', docs=(('paper', 'x'),))
        b = make_project(self.d / 'b' / 'proj', docs=(('lecture', 'x'),))
        for rel in ('octavo.config.py', 'README.md', '.gitignore', 'analysis/analysis.qmd'):
            self.assertEqual((a / rel).read_text(encoding='utf-8'),
                             (b / rel).read_text(encoding='utf-8'), rel)
        # CLAUDE.md は足したものの節だけが違う
        common = lambda d: (d / 'AGENTS.md').read_text(encoding='utf-8').split(
            '<!-- octavo:section analysis -->')[0]
        self.assertEqual(common(a), common(b))

    def test_new_puts_each_kind_where_the_config_finds_it(self):
        d = self.make(docs=(('paper', 'mypaper'), ('slides', 'keynote'), ('slides', 'deck'),
                            ('lecture', 'intro')))
        cfg = config.load(d / 'octavo.config.py')
        self.assertEqual(sorted(cfg.documents), ['deck', 'intro', 'keynote', 'mypaper'])
        mypaper = cfg.document('mypaper')
        self.assertEqual(mypaper.profile, 'paper')
        self.assertEqual(cfg.rel(mypaper.src), 'papers/mypaper/paper.md')
        self.assertEqual(cfg.rel(mypaper.appendix), 'papers/mypaper/appendix.md')
        self.assertEqual(cfg.document('keynote').targets, ('typst-slides',))
        intro = cfg.document('intro')
        self.assertEqual((intro.profile, intro.split_slides), ('handout', True))
        self.assertEqual(intro.targets, ('typst', 'typst-slides'))
        # 論文の体裁は手で書くので、生成物ではなく原稿の隣に置く。main.tex は --tex のときだけ
        self.assertTrue((d / 'papers/mypaper/main.typ').is_file())
        self.assertFalse((d / 'papers/mypaper/main.tex').exists())
        self.assertFalse((d / 'build').exists())

    def test_layout_templates_follow_the_language(self):
        # 体裁は Typst も LaTeX も言語ごとに別のひな型がある
        ja = make_project(self.d / 'ja2', docs=(('paper', 'p'),), lang='ja')
        en = make_project(self.d / 'en2', docs=(('paper', 'p'),), lang='en')
        for d, typ_title, tex_title, avoid in (
                (ja, '論文タイトル', '論文タイトル', 'Title of the Paper'),
                (en, 'Title of the Paper', 'Paper Title', '論文タイトル')):
            scaffold.new(d / 'octavo.config.py', 'paper', 'p', tex=True, quiet=True)
            typ = (d / 'papers' / 'p' / 'main.typ').read_text(encoding='utf-8')
            tex = (d / 'papers' / 'p' / 'main.tex').read_text(encoding='utf-8')
            self.assertIn(typ_title, typ)
            self.assertNotIn(avoid, typ)
            self.assertIn(tex_title, tex)
            # 匿名審査の分岐と、付録を読む行のコメントは両方の言語で同じ形
            self.assertTrue(be.get('typst').uses_anonymous_guard(typ))
            self.assertTrue(be.get('latex').uses_anonymous_guard(tex))
            self.assertIn('// #include "appendix.typ"', typ)
            # \newif は \title より前（後ろだと Undefined control sequence）
            self.assertLess(tex.index(r'\newif\ifanonymous'), tex.index(r'\title{'))

    def test_new_refuses_a_taken_name(self):
        d = self.make(docs=(('slides', 'x'),))
        with contextlib_redirect():
            rc = scaffold.new(d / 'octavo.config.py', 'lecture', 'x', quiet=True)
        self.assertEqual(rc, 1)
        self.assertFalse((d / 'lectures' / 'x.md').exists())

    def test_new_refuses_names_that_are_not_one_path_part(self):
        d = self.make(docs=())
        for bad in ('a b', 'a/b', '.x', ''):
            with contextlib_redirect():
                rc = scaffold.new(d / 'octavo.config.py', 'slides', bad, quiet=True)
            self.assertEqual(rc, 1, bad)
        self.assertFalse((d / 'slides').exists())

    def test_no_old_paper_names_survive(self):
        # CLI/設定ファイル/R ヘルパー/環境変数は octavo 系に改名済み。
        # プロファイル名の 'paper' は論文の意味なので対象外。
        old = re.compile(r'paper\.config|paper\.R\b|\bpt_[a-z]|PAPER_[A-Z]'
                         r'|\bpaper (build|init|values|check)\b|--kind\b')
        for lang in ('ja', 'en'):
            d = make_project(self.d / lang, docs=ALL_KINDS, lang=lang)
            for f in d.rglob('*'):
                if f.is_file() and f.suffix not in ('.png', '.pdf', '.pyc'):
                    m = old.search(f.read_text(encoding='utf-8'))
                    self.assertIsNone(m, f'{f.relative_to(d)}: {m and m.group(0)}')

    def test_no_container(self):
        # devcontainer は廃止した。分析の環境は .venv と renv。
        d = self.make()
        self.assertFalse((d / '.devcontainer').exists())
        for f in d.rglob('*.md'):
            self.assertNotIn('devcontainer', f.read_text(encoding='utf-8'),
                             f.relative_to(d))

    def test_refs_and_notes_are_distinct_places(self):
        # 外から来た資料は refs/、自分が書いたメモは notes/。作るのは要るときに自分で
        d = self.make(docs=())
        self.assertFalse((d / 'refs').exists())
        self.assertFalse((d / 'notes').exists())
        # refs/ は git に入れる（入れて困るものだけ手で無視する方針）
        rules = [l.strip() for l in (d / '.gitignore').read_text(encoding='utf-8')
                 .splitlines() if l.strip() and not l.startswith('#')]
        self.assertNotIn('refs/', rules)
        claude = (d / 'AGENTS.md').read_text(encoding='utf-8')
        self.assertIn('refs/', claude)
        self.assertIn('notes/', claude)

    def test_templates_are_marked_as_templates(self):
        # ひな型の「例」には印が付いていて、octavo check が残りを数えられる
        d = self.make(docs=ALL_KINDS)
        cfg = config.load(d / 'octavo.config.py')
        marked = {lo.file for lo in lint.leftovers(cfg)}
        for f in ('papers/paper/paper.md', 'papers/paper/appendix.md',
                  'slides/slides.md', 'lectures/講義.md',
                  'analysis/analysis.qmd', 'literature.bib'):
            self.assertIn(f, marked, f)
        # 仮の値・仮の図にも、それと分かる印が入っている
        self.assertEqual(values.placeholder_files(cfg), ['analysis.json'])
        self.assertTrue(scaffold.is_placeholder(d / 'assets' / 'figures' / 'trend.png'))
        self.assertTrue(scaffold.is_placeholder(d / 'assets' / 'figures' / 'trend.pdf'))

    def test_analysis_env_scaffolding(self):
        d = self.make(docs=())
        # requirements.txt は最初から置く（renv.lock は octavo env が作る）
        req = (d / 'requirements.txt').read_text(encoding='utf-8')
        self.assertIn('octavo env', req)
        # 環境の中身は git に入れず、記録だけを入れる
        rules = [l.strip() for l in (d / '.gitignore').read_text(encoding='utf-8')
                 .splitlines() if l.strip() and not l.startswith('#')]
        for pat in ('.venv/', 'renv/library/'):
            self.assertIn(pat, rules)
        for keep in ('requirements.txt', 'renv.lock'):
            self.assertNotIn(keep, rules)
        # 作業の約束は .venv と renv を必ず使うと書く。README は再現の手順だけ
        text = (d / 'AGENTS.md').read_text(encoding='utf-8')
        self.assertIn('renv::snapshot()', text)
        self.assertIn('.venv', text)
        self.assertIn('octavo env', text)
        self.assertIn('octavo env', (d / 'README.md').read_text(encoding='utf-8'))

    def test_templates_render_cleanly(self):
        for lang in ('ja', 'en'):
            d = make_project(self.d / lang, docs=ALL_KINDS, lang=lang)
            for f in list(d.rglob('*.md')) + [d / 'octavo.config.py']:
                text = f.read_text(encoding='utf-8')
                where = f'{lang}/{f.relative_to(d)}'
                self.assertNotIn('@@', text, where)
                self.assertNotRegex(text, r'<!-- (if:|endif)', where)

    def test_claude_md_grows_with_what_is_added(self):
        d = self.d / 'proj'
        scaffold.init(d, quiet=True)
        claude = d / 'AGENTS.md'
        text = claude.read_text(encoding='utf-8')
        self.assertIn('「proj」', text)               # @@NAME@@ が埋まる
        for s in ('octavo new paper', 'octavo new slides', 'octavo new lecture',
                  'octavo new analysis'):
            self.assertIn(s, text)                    # 何を足せるかは最初から書いてある
        for s in ('data/raw', '投稿する', '講義ノート **1本から**'):
            self.assertNotIn(s, text)                 # 足していないものの約束はない
        cfg = d / 'octavo.config.py'
        scaffold.new(cfg, 'slides', 'talk', quiet=True)
        scaffold.new(cfg, 'lecture', 'course', quiet=True)     # スライドと同じ節
        scaffold.new(cfg, 'analysis', 'model', quiet=True)
        text = claude.read_text(encoding='utf-8')
        self.assertIn('講義ノート **1本から**', text)
        self.assertIn('ov_value', text)
        self.assertNotIn('投稿する', text)
        self.assertEqual(text.count('<!-- octavo:section slides -->'), 1)
        scaffold.new(cfg, 'paper', 'p', quiet=True)
        self.assertIn('投稿する', claude.read_text(encoding='utf-8'))
        # 自分で消した AGENTS.md は作り直さない（1行の CLAUDE.md には書き足さない）
        claude.unlink()
        scaffold.new(cfg, 'paper', 'q', quiet=True)
        self.assertFalse(claude.exists())

    def test_init_with_parts(self):
        self.assertEqual(scaffold.parse_parts('analysis, paper=mine'),
                         {'analysis': 'analysis', 'paper': 'mine'})
        with self.assertRaises(ValueError):
            scaffold.parse_parts('paper,flyer')
        d = self.d / 'study'
        scaffold.init(d, quiet=True, parts={'analysis': 'model', 'paper': 'p'})
        for rel in ('analysis/model.qmd', 'analysis/octavo.R', 'data/raw/README.md',
                    'requirements.txt', 'docs/p/p.md', 'docs/p/main.typ'):
            self.assertTrue((d / rel).exists(), rel)
        self.assertFalse((d / 'slides').exists())
        self.assertFalse((d / 'lectures').exists())
        self.assertEqual(list(config.load(d / 'octavo.config.py').documents), ['p'])
        # CLI: --all は4つとも、名前は部品の名前。不明な部品は止まる
        from octavo import cli
        with contextlib_redirect(), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(['init', str(self.d / 'all'), '--all']), 0)
            self.assertEqual(cli.main(['init', str(self.d / 'bad'), '--with', 'flyer']), 2)
        for rel in ('analysis/analysis.qmd', 'docs/paper/paper.md', 'docs/slides/slides.md',
                    'docs/lecture/lecture.md', 'docs/poster/poster.md'):
            self.assertTrue((self.d / 'all' / rel).exists(), rel)
        self.assertFalse((self.d / 'bad').exists())

    def test_an_example_brings_what_it_uses(self):
        """枠だけのプロジェクトに見本の原稿を足すと、見本の値・図表・書誌も入る。"""
        d = self.d / 'bare'
        scaffold.init(d, quiet=True)
        (d / 'literature.bib').write_text('@book{mine2024, title={Mine}}\n', encoding='utf-8')
        scaffold.new(d / 'octavo.config.py', 'slides', 'deck', quiet=True, example=True)
        cfg = config.load(d / 'octavo.config.py')
        vals, _ = values.load(cfg)
        used = values.referenced((d / 'docs/deck/deck.md').read_text(encoding='utf-8'))
        self.assertEqual(used - set(vals), set())
        self.assertTrue((d / 'assets/figures/trend.png').exists())
        bib = (d / 'literature.bib').read_text(encoding='utf-8')
        self.assertIn('mine2024', bib)                 # 書誌は上書きせず書き足す
        self.assertIn('yamada2020', bib)
        # 2本目は何も足さない（値も書誌も既にある）
        scaffold.new(d / 'octavo.config.py', 'paper', 'p', quiet=True, example=True)
        self.assertEqual((d / 'literature.bib').read_text(encoding='utf-8').count('yamada2020'), 1)
        self.assertEqual(sorted(p.name for p in (d / 'analysis').glob('*.qmd')), ['analysis.qmd'])
        # 自分の analysis.qmd があれば、見本はそれを上書きしない
        d2 = self.d / 'mine'
        scaffold.init(d2, quiet=True, parts={'analysis': 'analysis'})
        scaffold.new(d2 / 'octavo.config.py', 'paper', 'p', quiet=True, example=True)
        self.assertNotIn('set.seed', (d2 / 'analysis/analysis.qmd').read_text(encoding='utf-8'))
        self.assertIn('set.seed', (d2 / 'analysis/example.qmd').read_text(encoding='utf-8'))

    def test_new_analysis(self):
        d = self.d / 'talk'
        scaffold.init(d, quiet=True, parts={'slides': 'talk'})
        self.assertFalse((d / 'analysis').exists())
        cfg = d / 'octavo.config.py'
        self.assertEqual(scaffold.new(cfg, 'analysis', '01-clean.qmd', quiet=True), 0)
        self.assertEqual(scaffold.new(cfg, 'analysis', '02-model', quiet=True), 0)
        loaded = config.load(cfg)
        self.assertEqual([analysis.key(loaded, u) for u, _, _ in analysis.status(loaded)],
                         ['analysis/01-clean.qmd', 'analysis/02-model.qmd'])
        for rel in ('analysis/octavo.R', 'data/raw/README.md', 'data/derived/.gitkeep',
                    'assets/tables/.gitkeep', 'requirements.txt'):
            self.assertTrue((d / rel).exists(), rel)
        with contextlib_redirect():
            self.assertEqual(scaffold.new(cfg, 'analysis', 'x', appendix=True, quiet=True), 1)

    def test_check_says_nothing_about_an_analysis_there_is_not(self):
        d = self.d / 'talk'
        scaffold.init(d, quiet=True, parts={'slides': 'talk'})
        labels = [i.label for i in audit.collect(config.load(d / 'octavo.config.py'))]
        for s in ('analysis freshness', 'placeholder values', 'environment record'):
            self.assertNotIn(s, labels)

    def test_english_project_docs(self):
        d = self.make(lang='en', docs=())
        claude = (d / 'AGENTS.md').read_text(encoding='utf-8')
        readme = (d / 'README.md').read_text(encoding='utf-8')
        self.assertIn('About this repository', claude)
        self.assertIn('octavo new lecture', claude)
        self.assertNotIn('@@', claude)
        self.assertNotIn('@@', readme)

    def test_gitignore_keeps_raw_data_out_but_keeps_its_readme(self):
        text = (self.make(docs=()) / '.gitignore').read_text(encoding='utf-8')
        self.assertIn('data/raw/*', text)
        self.assertIn('!data/raw/README.md', text)
        self.assertIn('data/derived/*', text)

    @unittest.skipUnless(shutil.which('git'), 'git がない')
    def test_git_tracks_the_layout_but_no_generated_output(self):
        """手で書く main.typ / main.tex は原稿の隣。build/ は丸ごと生成物。"""
        d = self.make(docs=(('paper', 'mypaper'),))
        scaffold.new(d / 'octavo.config.py', 'paper', 'mypaper', tex=True, quiet=True)
        (d / 'build/typst/mypaper').mkdir(parents=True)
        (d / 'build/typst/mypaper/body.typ').write_text('x', encoding='utf-8')
        (d / 'build/typst/mypaper/main.typ').write_text('x', encoding='utf-8')
        (d / 'build/typst-slides').mkdir(parents=True)
        (d / 'build/typst-slides/talk.pdf').write_text('x', encoding='utf-8')
        subprocess.run(['git', 'init', '-q'], cwd=d, check=True)
        subprocess.run(['git', 'add', '-A'], cwd=d, check=True)
        files = subprocess.run(['git', 'ls-files'], cwd=d, check=True,
                               capture_output=True, text=True).stdout.split('\n')
        self.assertIn('papers/mypaper/main.typ', files)
        self.assertIn('papers/mypaper/main.tex', files)
        # build/ の下はコピーしたものも含めて1つも入らない
        self.assertFalse([f for f in files if f.startswith('build/')], files)

    def test_generated_config_registers_the_analysis(self):
        cfg = config.load(self.make(docs=()) / 'octavo.config.py')
        us = analysis.units(cfg)
        self.assertEqual([u.src.name for u in us], ['analysis.qmd'])
        self.assertEqual(Path(cfg['values_dir']).name, 'values')

    def test_manuscript_placeholders_resolve_out_of_the_box(self):
        """分析を1度も実行していなくても、どの原稿のテンプレートの {{…}} も埋まること。"""
        for lang in ('ja', 'en'):
            d = make_project(self.d / lang, docs=ALL_KINDS, lang=lang)
            cfg = config.load(d / 'octavo.config.py')
            vals, _ = values.load(cfg)
            for name, src, _ in cfg.sources():
                used = values.referenced(md.read(src))
                self.assertFalse(used - set(vals), f'{lang}/{name}')
                if name != 'paper' or src.name == 'paper.md':
                    self.assertTrue(used, f'{lang}/{cfg.rel(src)}')

    def test_lecture_template_splits_into_sessions(self):
        for lang in ('ja', 'en'):
            d = make_project(self.d / lang, docs=(('lecture', 'x'),), lang=lang)
            cfg = config.load(d / 'octavo.config.py')
            self.assertEqual([p.name for p in cfg.parts(cfg.document('x'))],
                             ['x-01', 'x-02'])


# =====================================================================
class MultipleSources(unittest.TestCase):
    """原稿+付録、そして分析を複数の .qmd に分けたとき。"""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / 'draft.md').write_text('# 本文 {{a}}\n', encoding='utf-8')
        (self.d / 'appendix.md').write_text('# 付録 {{b}} @tanaka2019\n',
                                            encoding='utf-8')
        (self.d / 'analysis').mkdir()
        (self.d / 'assets' / 'values').mkdir(parents=True)
        for n in ('01-clean', '02-model'):
            (self.d / 'analysis' / f'{n}.qmd').write_text('---\n---\n',
                                                          encoding='utf-8')
            (self.d / 'assets' / 'values' / f'{n}.json').write_text('{}', encoding='utf-8')

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def cfg(self, extra: str = '') -> config.Config:
        (self.d / 'octavo.config.py').write_text(
            "CONFIG = {'lang': 'ja', 'appendix': 'appendix.md'" + extra + '}',
            encoding='utf-8')
        return config.load(self.d / 'octavo.config.py')

    def test_sources_include_the_appendix(self):
        rows = self.cfg().sources()
        self.assertEqual([(n, p.name, a) for n, p, a in rows],
                         [('paper', 'draft.md', False),
                          ('paper', 'appendix.md', True)])

    def test_main_typ_is_compiled_after_the_appendix(self):
        # main.typ は付録も読み込むので、付録を書き出してから組む
        cfg = self.cfg()
        calls = []
        with unittest.mock.patch.object(
                build, 'build_one',
                side_effect=lambda cfg, doc, t, appendix, do_compile, **kw:
                calls.append((appendix, do_compile))):
            build.run(cfg, targets=['typst'], appendix=True, do_compile=True)
        self.assertEqual(calls, [(False, False), (True, True)])

    def test_compile_main_only_where_it_has_one_way_to_run(self):
        cfg = self.cfg()
        out = self.d / 'build' / 'typst'
        out.mkdir(parents=True)
        typ = Ctx(cfg=cfg, backend=be.get('typst'), out_dir=out, profile='paper')
        self.assertIsNone(be.get('typst').compile_main(typ))   # main.typ がまだない
        (out / 'main.typ').write_text('', encoding='utf-8')
        self.assertEqual(be.get('typst').compile_main(typ), out / 'main.typ')
        tex = Ctx(cfg=cfg, backend=be.get('latex'), out_dir=out, profile='paper')
        self.assertIsNone(be.get('latex').compile_main(tex))   # latexmk は main.tex 側で

    def test_typst_compile_can_read_figures_above_out_dir(self):
        # 根を上げないと body.typ の ../../figures が access denied になる
        cfg = self.cfg()
        out = self.d / 'build' / 'typst'
        out.mkdir(parents=True)
        ctx = Ctx(cfg=cfg, backend=be.get('typst'), out_dir=out, profile='paper')
        self.assertEqual(be.get('typst').compile(ctx, out / 'main.typ'),
                         ['typst', 'compile', '--root', '../..', 'main.typ'])

    def test_typst_root_survives_a_symlinked_folder(self):
        # macOS の /var -> /private/var と同じ形。out_dir だけリンク経由で渡っても
        # 根が / まで上がらないこと（CI の macos ジョブで見つかった）
        cfg = self.cfg()
        real = self.d / 'build' / 'typst'
        real.mkdir(parents=True)
        link = Path(tempfile.mkdtemp()) / 'via-link'
        try:
            link.symlink_to(self.d, target_is_directory=True)
        except OSError:
            self.skipTest('シンボリックリンクを作れない')
        try:
            ctx = Ctx(cfg=cfg, backend=be.get('typst'), out_dir=link / 'build' / 'typst',
                      profile='paper')
            self.assertEqual(be.get('typst').root_arg(ctx), '../..')
        finally:
            shutil.rmtree(link.parent, ignore_errors=True)

    def test_sources_skip_missing_files(self):
        (self.d / 'appendix.md').unlink()
        self.assertEqual([p.name for _, p, _ in self.cfg().sources()], ['draft.md'])

    def test_appendix_values_are_counted_as_referenced(self):
        """octavo values が付録の {{…}} を数え落とさないこと。"""
        cfg = self.cfg()
        seen = set()
        for _, src, _ in cfg.sources():
            seen |= values.referenced(md.read(src))
        self.assertEqual(seen, {'a', 'b'})

    def test_appendix_citations_are_checked(self):
        (self.d / 'literature.bib').write_text(
            '@book{tanaka2019, title={X}, date={2019}}\n', encoding='utf-8')
        r = check.collect(self.cfg())
        self.assertIn('appendix.md', r.cited_by_doc)
        self.assertIn('tanaka2019', r.cited)

    def test_config_order_is_the_run_order(self):
        """明示的に並べた .qmd は書いた順に走る（前段が後段の入力を作る場合）。"""
        cfg = self.cfg(", 'analysis': ['analysis/02-model.qmd',"
                       " 'analysis/01-clean.qmd']")
        self.assertEqual([u.src.stem for u in analysis.units(cfg)],
                         ['02-model', '01-clean'])

    def test_glob_runs_in_name_order(self):
        cfg = self.cfg(", 'analysis': ['analysis/*.qmd']")
        self.assertEqual([u.src.stem for u in analysis.units(cfg)],
                         ['01-clean', '02-model'])

    def test_orphan_results_are_found(self):
        cfg = self.cfg(", 'analysis': ['analysis/*.qmd']")
        self.assertEqual(analysis.orphan_results(cfg), [])
        (self.d / 'assets' / 'values' / 'old.json').write_text('{}', encoding='utf-8')
        self.assertEqual([p.name for p in analysis.orphan_results(cfg)],
                         ['old.json'])

    def test_no_orphans_reported_without_analysis(self):
        """分析を登録していないなら assets/values/ は手で置いたものなので黙る。"""
        (self.d / 'assets' / 'values' / 'manual.json').write_text('{}', encoding='utf-8')
        self.assertEqual(analysis.orphan_results(self.cfg()), [])

    def test_values_from_several_files_merge(self):
        (self.d / 'assets' / 'values' / '01-clean.json').write_text(
            '{"a": 1}', encoding='utf-8')
        (self.d / 'assets' / 'values' / '02-model.json').write_text(
            '{"b": 2.5}', encoding='utf-8')
        vals, warn = values.load(self.cfg())
        self.assertEqual(set(vals), {'a', 'b'})
        self.assertEqual(vals['a'].source, '01-clean.json')
        self.assertEqual(warn, [])

    def test_a_later_qmd_is_run_in_the_same_pass(self):
        """前段が後段の入力を書き換えたら、その回のうちに後段も走ること。

        todo を先に固定していると、後段が1回分あとに取り残される。
        Quarto は呼ばず、render を差し替えて順序だけ見る。
        """
        data = self.d / 'data'
        data.mkdir()
        (data / 'clean.csv').write_text('a\n', encoding='utf-8')
        cfg = self.cfg(", 'analysis': ["
                       "{'src': 'analysis/01-clean.qmd'},"
                       "{'src': 'analysis/02-model.qmd',"
                       " 'deps': ['data/*.csv']}]")
        # 02 は最新、01 だけが古い、という状態から始める
        stamp = {}
        for u in analysis.units(cfg):
            stamp[analysis.key(cfg, u)] = {'newest': u.newest()}
        analysis.write_stamp(cfg, stamp)
        later = time.time() + 10
        os.utime(self.d / 'analysis' / '01-clean.qmd', (later, later))

        ran = []

        def fake_render(cfg_, u, report):
            ran.append(u.src.stem)
            if u.src.stem == '01-clean':          # 前段が後段の入力を書き換える
                t = time.time() + 20
                os.utime(data / 'clean.csv', (t, t))
            return True

        with unittest.mock.patch.object(analysis, 'render', fake_render), \
                unittest.mock.patch.object(analysis.shutil, 'which',
                                           lambda name: '/usr/bin/' + name):
            n, ok = analysis.run(cfg, report=[])
        self.assertTrue(ok)
        self.assertEqual(ran, ['01-clean', '02-model'])
        self.assertEqual(n, 2)

    def _all_stale(self, extra):
        cfg = self.cfg(extra)
        analysis.write_stamp(cfg, {})             # 記録がない = 全部古い
        return cfg

    def _run(self, cfg, **kw):
        ran, report = [], []

        def fake_render(cfg_, u, rep):
            ran.append(u.src.stem)
            return True
        with unittest.mock.patch.object(analysis, 'render', fake_render), \
                unittest.mock.patch.object(analysis.shutil, 'which',
                                           lambda name: '/usr/bin/' + name):
            analysis.run(cfg, report=report, **kw)
        return ran, report

    MANUAL = (", 'analysis': [{'src': 'analysis/01-clean.qmd', 'manual': True},"
              "{'src': 'analysis/02-model.qmd'}]")

    def test_build_skips_a_manual_qmd_and_says_so(self):
        """時間のかかる .qmd（manual）は、組むたびには実行しない。"""
        cfg = self._all_stale(self.MANUAL)
        ran, report = self._run(cfg, auto=True)
        self.assertEqual(ran, ['02-model'])
        self.assertTrue(any('01-clean' in r and 'manual' in r for r in report), report)

    def test_analysis_run_includes_manual_ones(self):
        cfg = self._all_stale(self.MANUAL)
        ran, _ = self._run(cfg)
        self.assertEqual(ran, ['01-clean', '02-model'])

    def test_a_named_qmd_runs_even_when_fresh(self):
        cfg = self.cfg(self.MANUAL)
        analysis.write_stamp(cfg, {analysis.key(cfg, u): {'newest': u.newest() + 100}
                                   for u in analysis.units(cfg)})
        for name in ('analysis/02-model.qmd', '02-model.qmd', '02-model'):
            ran, _ = self._run(cfg, names=[name])
            self.assertEqual(ran, ['02-model'], name)
        with self.assertRaises(SystemExit):
            analysis.pick(cfg, ['nope'])

    def test_status_json_carries_manual_and_stale(self):
        cfg = self._all_stale(self.MANUAL)
        with unittest.mock.patch.object(analysis, 'quarto_version', lambda: ''):
            got = analysis.status_json(cfg)
        rows = {r['key']: r for r in got['units']}
        self.assertTrue(rows['analysis/01-clean.qmd']['manual'])
        self.assertFalse(rows['analysis/02-model.qmd']['manual'])
        self.assertEqual(got['stale'], 2)
        self.assertIsNone(got['quarto'])

    def test_manual_must_be_a_bool(self):
        with self.assertRaises(SystemExit):
            analysis.units(self.cfg(", 'analysis': [{'src': 'a.qmd', 'manual': 'yes'}]"))


# =====================================================================
class Lint(unittest.TestCase):
    """原稿に手入力された分析結果らしき数値を見つける。"""

    def find(self, text: str, accepted=()) -> list:
        return lint.scan(text, lint.CONVENTIONAL | set(accepted))

    def kinds(self, text: str) -> set:
        return {kind for _, kind, _, _ in self.find(text)}

    def hits(self, text: str) -> list:
        return [hit for _, _, hit, _ in self.find(text)]

    def test_finds_a_coefficient(self):
        self.assertEqual(self.hits('係数は 0.342 だった。'), ['0.342'])

    def test_finds_sample_size_and_pvalue(self):
        self.assertEqual(self.kinds('N = 1,523 で p < .001 だった。'),
                         {'n', 'pvalue'})

    def test_finds_percentage(self):
        self.assertEqual(self.hits('支持率は 42.3% だった。'), ['42.3%'])

    def test_conventional_constants_pass(self):
        self.assertEqual(self.find('有意水準 0.05、臨界値 1.96 を用いる。'), [])

    def test_accepted_from_config_passes(self):
        self.assertEqual(self.find('理論値は 2.25 である。', ['2.25']), [])

    def test_section_numbers_pass(self):
        self.assertEqual(self.find('第3.2節を参照。'), [])

    def test_table_rows_pass(self):
        self.assertEqual(self.find('| x | 1.234 |'), [])

    def test_headings_pass(self):
        self.assertEqual(self.find('## 2.1 結果'), [])

    def test_doi_and_links_pass(self):
        self.assertEqual(self.find('DOI: 10.1093/jopart/mug030'), [])
        self.assertEqual(self.find('[出典](http://a.b/1.234) を見よ。'), [])

    def test_code_passes(self):
        self.assertEqual(self.find('`p < 0.001` と書く。'), [])
        self.assertEqual(self.find('```r\ncoef <- 0.342\n```\n'), [])

    def test_placeholders_pass(self):
        """{{coef:.3f}} の書式指定を数値と取り違えない。"""
        self.assertEqual(self.find('係数は {{coef_x:.3f}} である。'), [])

    def test_front_matter_passes_and_line_numbers_survive(self):
        text = ded("""
            ---
            date: 2026-01-01
            ---

            係数は 0.342 だった。
            """)
        found = self.find(text)
        self.assertEqual([f[2] for f in found], ['0.342'])
        self.assertEqual(found[0][0], 5)          # 元のファイルでの行番号

    def test_collect_walks_appendix_too(self):
        d = Path(tempfile.mkdtemp())
        try:
            (d / 'draft.md').write_text('本文 0.342\n', encoding='utf-8')
            (d / 'appendix.md').write_text('付録 0.811\n', encoding='utf-8')
            (d / 'octavo.config.py').write_text(
                "CONFIG = {'lang': 'ja', 'appendix': 'appendix.md'}",
                encoding='utf-8')
            cfg = config.load(d / 'octavo.config.py')
            self.assertEqual({f.doc for f in lint.collect(cfg)},
                             {'paper', 'paper (appendix)'})
        finally:
            shutil.rmtree(d, ignore_errors=True)


# =====================================================================
class ValuesDiff(unittest.TestCase):
    """再推定で本文の数字がどう動いたか。"""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / 'assets' / 'values').mkdir(parents=True)
        (self.d / 'octavo.config.py').write_text(
            "CONFIG = {'lang': 'ja'}", encoding='utf-8')
        self.cfg = config.load(self.d / 'octavo.config.py')

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def write(self, obj: dict) -> None:
        (self.d / 'assets' / 'values' / 'a.json').write_text(
            json.dumps(obj), encoding='utf-8')

    def test_no_snapshot_yet(self):
        taken, changed, added, removed = values.diff(self.cfg)
        self.assertEqual((taken, changed, added, removed), ('', [], [], []))

    def test_changed_added_removed(self):
        self.write({'n_obs': 1523, 'coef': 0.342, 'old': 1.0})
        values.snapshot(self.cfg)
        self.write({'n_obs': 1608, 'coef': 0.342, 'new': 2.0})
        taken, changed, added, removed = values.diff(self.cfg)
        self.assertTrue(taken)
        self.assertEqual(changed, [('n_obs', '1,523', '1,608')])
        self.assertEqual((added, removed), (['new'], ['old']))

    def test_change_below_the_printed_precision_is_not_a_change(self):
        """本文が 0.342 のままなら「変わっていない」。"""
        self.write({'coef': 0.34219})
        values.snapshot(self.cfg)
        self.write({'coef': 0.34211})
        _, changed, _, _ = values.diff(self.cfg)
        self.assertEqual(changed, [])

    def test_diff_against_a_git_tag(self):
        """R&R で要るのは「投稿した版」との比較。git のタグに乗せる。"""
        if not shutil.which('git'):
            self.skipTest('git がない')

        def git(*args):
            subprocess.run(['git', *args], cwd=self.d, capture_output=True)

        self.write({'n_obs': 1523, 'coef': 0.342, 'dropped': 1.0})
        git('init', '-q')
        git('config', 'user.email', 'a@b')
        git('config', 'user.name', 't')
        git('add', '-A')
        git('commit', '-qm', 'v1')
        git('tag', 'v1-submitted')
        self.write({'n_obs': 1608, 'coef': 0.342, 'added': 2.0})

        taken, changed, added, removed = values.diff(self.cfg, 'v1-submitted')
        self.assertEqual(taken, 'git v1-submitted')
        self.assertEqual(changed, [('n_obs', '1,523', '1,608')])
        self.assertEqual((added, removed), (['added'], ['dropped']))

    def test_unknown_git_ref_is_reported_not_raised_silently(self):
        if not shutil.which('git'):
            self.skipTest('git がない')
        subprocess.run(['git', 'init', '-q'], cwd=self.d, capture_output=True)
        with self.assertRaises(values.GitError):
            values.diff(self.cfg, 'no-such-tag')

    def test_snapshot_is_not_read_as_a_values_file(self):
        self.write({'n_obs': 1})
        values.snapshot(self.cfg)
        vals, warn = values.load(self.cfg)
        self.assertEqual(set(vals), {'n_obs'})
        self.assertEqual(warn, [])


# =====================================================================
class Audit(unittest.TestCase):
    """octavo check がまとめる検査。"""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        make_project(self.d / 'p')
        self.root = self.d / 'p'
        self.cfg = config.load(self.root / 'octavo.config.py')

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def items(self, cfg=None) -> dict:
        return {i.label: i for i in audit.collect(cfg or self.cfg)}

    def test_a_fresh_project_is_fatal_only_for_the_placeholder_values(self):
        # 仮の値のまま組むと本文に仮の数字が入るので、これは致命的。
        # それ以外で新品のプロジェクトが引っかかってはいけない。
        bad = [i.label for i in audit.collect(self.cfg) if not i.ok and i.fatal]
        self.assertEqual(bad, ['placeholder values'])

    def test_real_values_clear_the_placeholder_item(self):
        # octavo.R が書き直すと _placeholder ごと消える
        (self.root / 'assets' / 'values' / 'analysis.json').write_text(
            '{"_generated": "2026-09-18 10:00:00", "n_obs": 1523, '
            '"coef_x": 0.342, "p_x": "< .001"}', encoding='utf-8')
        cfg = config.load(self.root / 'octavo.config.py')
        item = self.items(cfg)['placeholder values']
        self.assertTrue(item.ok)
        self.assertEqual([i.label for i in audit.collect(cfg)
                          if not i.ok and i.fatal], [])

    def test_template_leftovers_are_a_warning(self):
        item = self.items()['template leftovers']
        self.assertFalse(item.ok)
        self.assertFalse(item.fatal)
        self.assertTrue(any('paper.md' in l for l in item.lines))
        # 印を消せば黙る
        src = self.root / 'papers' / 'paper' / 'paper.md'
        src.write_text('\n'.join(l for l in src.read_text(encoding='utf-8')
                                 .splitlines() if 'octavo:example' not in l),
                       encoding='utf-8')
        left = {lo.file for lo in lint.leftovers(self.cfg)}
        self.assertNotIn('papers/paper/paper.md', left)

    def test_a_mark_named_in_prose_is_not_a_mark(self):
        # 英語のひな型は説明文で `octavo:example` と書くので、英語だけ数が多く出ていた
        src = self.root / 'papers' / 'paper' / 'paper.md'
        src.write_text('Blocks marked `octavo:example` are examples.\n', encoding='utf-8')
        self.assertNotIn('papers/paper/paper.md',
                         {lo.file for lo in lint.leftovers(self.cfg)})

    def test_placeholder_figures_are_a_warning(self):
        item = self.items()['placeholder figures and tables']
        self.assertFalse(item.ok)
        self.assertFalse(item.fatal)
        self.assertIn('assets/figures/trend.png', item.lines)
        self.assertIn('assets/tables/summary.typ', item.lines)       # 仮の表も
        # 本物の図に差し替えれば黙る（印は octavo init の書いたものにしかない）
        for ext in ('.png', '.pdf'):
            (self.root / 'assets' / 'figures' / f'trend{ext}').write_bytes(b'real figure')
        self.assertEqual([x for x in audit.placeholder_figures(self.cfg)
                          if x.startswith('assets/figures/')], [])

    def test_missing_figure_is_fatal(self):
        # 既定の形式は typst で、図は .pdf を使う（.png は Word 用）
        (self.root / 'assets' / 'figures' / 'trend.pdf').unlink()
        item = self.items()['figure files']
        self.assertFalse(item.ok)
        self.assertTrue(item.fatal)

    def test_missing_citation_key_is_fatal(self):
        p = self.root / PAPER_MD
        p.write_text(p.read_text(encoding='utf-8').replace('@yamada2020',
                                                           '@nosuch2020'),
                     encoding='utf-8')
        item = self.items(config.load(self.root / 'octavo.config.py'))['citation keys']
        self.assertFalse(item.ok)
        self.assertTrue(item.fatal)

    def test_unresolved_value_is_fatal(self):
        p = self.root / PAPER_MD
        p.write_text(p.read_text(encoding='utf-8') + '\n{{nope}}\n',
                     encoding='utf-8')
        item = self.items()['{{…}} in the text']
        self.assertFalse(item.ok)
        self.assertTrue(item.fatal)

    def test_raw_numbers_are_a_warning_not_fatal(self):
        p = self.root / PAPER_MD
        p.write_text(p.read_text(encoding='utf-8') + '\n係数は 0.342 だった。\n',
                     encoding='utf-8')
        item = self.items()['hand-typed numbers']
        self.assertFalse(item.ok)
        self.assertFalse(item.fatal)

    def test_a_missing_analysis_table_is_fatal(self):
        # 本文の `: 記述統計 {#tbl-summary}` は assets/tables/summary.* を差し込む
        self.assertTrue(self.items()['table files'].ok)
        (self.root / 'assets' / 'tables' / 'summary.typ').unlink()
        item = self.items()['table files']
        self.assertFalse(item.ok)
        self.assertTrue(item.fatal)
        self.assertTrue(any(line.endswith('summary.typ') for line in item.lines))

    def test_a_reference_to_no_label_is_fatal(self):
        self.assertTrue(self.items()['cross-references'].ok)
        p = self.root / PAPER_MD
        p.write_text(p.read_text(encoding='utf-8').replace('@fig-trend', '@fig-gone'),
                     encoding='utf-8')
        item = self.items(config.load(self.root / 'octavo.config.py'))['cross-references']
        self.assertFalse(item.ok)
        self.assertTrue(item.fatal)


# =====================================================================
class Bundle(unittest.TestCase):
    """投稿用にまとめ直す。"""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        make_project(self.d / 'p')
        self.root = self.d / 'p'
        self.cfg = config.load(self.root / 'octavo.config.py')
        out = self.cfg.out_dir('latex', self.cfg.document('paper'))
        out.mkdir(parents=True, exist_ok=True)
        (out / 'body.tex').write_text(
            '\\includegraphics[width=1.0\\textwidth]'
            '{../../../assets/figures/trend.pdf}\n'
            '\\inputtable{../../../assets/tables/summary}\n', encoding='utf-8')
        (out / 'abstract.tex').write_text('要旨。\n', encoding='utf-8')
        (self.root / 'assets' / 'tables' / 'summary.tex').write_text(
            '\\begin{table}\\end{table}\n', encoding='utf-8')

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_paths_are_flattened_and_assets_collected(self):
        dest = self.d / 'out'
        res = bundle.collect(self.cfg, 'latex', dest, self.cfg.document('paper'))
        self.assertTrue(res.ok, '\n'.join(res.report))
        names = {p.name for p in res.files}
        self.assertLessEqual({'body.tex', 'trend.pdf', 'summary.tex',
                              'literature.bib'}, names)
        body = (dest / 'body.tex').read_text(encoding='utf-8')
        self.assertIn('{trend.pdf}', body)
        self.assertIn('{summary}', body)
        self.assertNotIn('../../', body)

    def test_main_tex_does_not_overwrite_the_flattened_body(self):
        """main.tex の \\input{body} が、書き換え済みの body.tex を潰さない。"""
        dest = self.d / 'out'
        bundle.collect(self.cfg, 'latex', dest, self.cfg.document('paper'))
        self.assertNotIn('../../',
                         (dest / 'body.tex').read_text(encoding='utf-8'))

    def test_macro_definitions_and_comments_are_not_followed(self):
        """main.tex の \\newcommand や説明コメントを参照として拾わない。"""
        res = bundle.collect(self.cfg, 'latex', self.d / 'out', self.cfg.document('paper'))
        self.assertFalse([r for r in res.report if 'xxx' in r or '#1' in r],
                         '\n'.join(res.report))

    def test_optional_include_may_be_absent(self):
        """main.tex の \\IfFileExists{abstract.tex} はなくても欠落にしない。"""
        (self.cfg.out_dir('latex', self.cfg.document('paper')) / 'abstract.tex').unlink()
        res = bundle.collect(self.cfg, 'latex', self.d / 'out', self.cfg.document('paper'))
        self.assertTrue(res.ok, '\n'.join(res.report))

    def test_missing_reference_is_reported(self):
        (self.root / 'assets' / 'figures' / 'trend.pdf').unlink()
        res = bundle.collect(self.cfg, 'latex', self.d / 'out', self.cfg.document('paper'))
        self.assertFalse(res.ok)
        self.assertTrue(any('[missing]' in r for r in res.report))

    def test_typst_comment_lines_are_not_followed(self):
        """main.typ の `// #include "appendix.typ"` を辿ると、付録がないだけで欠落になる。"""
        text, refs = be.get('typst').flatten_assets(
            '// #include "appendix.typ"\n#include "body.typ"\n'
            '#image("../../../assets/figures/a.png")\n')
        self.assertEqual(refs, ['body.typ', '../../../assets/figures/a.png'])
        self.assertIn('// #include "appendix.typ"', text)

    def test_which_paper_to_bundle(self):
        self.assertEqual(bundle.pick_paper(self.cfg, None).name, 'paper')
        scaffold.new(self.root / 'octavo.config.py', 'paper', 'second', quiet=True)
        scaffold.new(self.root / 'octavo.config.py', 'slides', 'talk', quiet=True)
        cfg = config.load(self.root / 'octavo.config.py')
        with self.assertRaises(SystemExit):
            bundle.pick_paper(cfg, None)                  # 2本あるなら名前が要る
        self.assertEqual(bundle.pick_paper(cfg, 'second').name, 'second')

    def test_no_build_output_is_reported_not_raised(self):
        shutil.rmtree(self.cfg.out_dir('latex', self.cfg.document('paper')))
        res = bundle.collect(self.cfg, 'latex', self.d / 'out', self.cfg.document('paper'))
        self.assertFalse(res.ok)
        self.assertTrue(any('no output at' in r for r in res.report))


# =====================================================================
@unittest.skipUnless(HAVE_QUARTO and HAVE_R, 'Quarto と R が要る')
class AnalysisEndToEnd(unittest.TestCase):
    """**octavo.R を実際に実行する。**

    ここが通らないかぎり、分析側は「設計しただけ」の状態にとどまる。
    手元に Quarto と R があれば走り、なければ飛ぶ。CI は専用の job で
    Quarto と R を入れて、飛ばされていないことまで確かめている。
    """

    @classmethod
    def setUpClass(cls):
        cls.d = Path(tempfile.mkdtemp())
        make_project(cls.d / 'p')
        cls.cfg = config.load(cls.d / 'p' / 'octavo.config.py')
        # 出荷時の仮の値と仮の図を消す。**.qmd が本当に書いたか**を見るため。
        (Path(cls.cfg['values_dir']) / 'analysis.json').unlink()
        for ext in ('.pdf', '.png'):
            (Path(cls.cfg['figure_dir']) / f'trend{ext}').unlink()
        cls.report = []
        cls.ran, cls.ok = analysis.run(cls.cfg, force=True, report=cls.report)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def test_render_succeeded(self):
        self.assertTrue(self.ok, '\n'.join(self.report))
        self.assertEqual(self.ran, 1)

    def test_values_were_written(self):
        vals, warn = values.load(self.cfg)
        self.assertEqual(warn, [])
        self.assertIn('n_obs', vals)
        # nrow() は整数 -> 桁区切り、coef() は小数 -> 既定 3 桁
        self.assertEqual(values.render(vals['n_obs'], '', self.cfg), '1,523')
        self.assertIsInstance(vals['coef_x'].value, float)
        self.assertRegex(values.render(vals['coef_x'], '', self.cfg),
                         r'^-?\d+\.\d{3}$')
        self.assertEqual(vals['n_obs'].note, '分析に使った観測数')

    def test_session_was_recorded(self):
        sess = values.session_info(self.cfg)
        self.assertTrue(sess)
        one = next(iter(sess.values()))
        self.assertEqual(one['engine'], 'R')
        self.assertTrue(one['version'])
        self.assertIsInstance(one['packages'], dict)

    def test_figure_written_in_both_extensions(self):
        for ext in ('.pdf', '.png'):
            p = Path(self.cfg['figure_dir']) / f'trend{ext}'
            self.assertTrue(p.is_file(), p)
            self.assertGreater(p.stat().st_size, 500)

    def test_table_written_for_latex_and_typst(self):
        tex = (Path(self.cfg['table_dir']) / 'summary.tex') \
            .read_text(encoding='utf-8')
        typ = (Path(self.cfg['table_dir']) / 'summary.typ') \
            .read_text(encoding='utf-8')
        md_ = (Path(self.cfg['table_dir']) / 'summary.md').read_text(encoding='utf-8')
        # 表の中身だけ。表題とラベル（#tbl-summary）は原稿が持つ
        self.assertIn(r'\toprule', tex)
        self.assertNotIn(r'\caption', tex)
        self.assertNotIn(r'\label', tex)
        self.assertIn('#table(', typ)
        self.assertIn('table.hline()', typ)
        self.assertNotIn('#figure', typ)
        self.assertIn('| 変数 |', md_)                          # Word 用
        self.assertFalse(scaffold.is_placeholder(Path(self.cfg['table_dir']) / 'summary.typ'))

    def test_the_shipped_draft_resolves_completely(self):
        cited = values.referenced(md.read(self.cfg.document('paper').src))
        vals, _ = values.load(self.cfg)
        self.assertTrue(cited)
        self.assertFalse(cited - set(vals))

    def test_check_finds_nothing_fatal(self):
        bad = [i.label for i in audit.collect(self.cfg) if not i.ok and i.fatal]
        self.assertEqual(bad, [])


# =====================================================================
class DataFingerprint(unittest.TestCase):
    """data/HASHES.json —「同じデータで実行したか」の記録。"""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        (self.d / 'draft.md').write_text('# x\n', encoding='utf-8')
        (self.d / 'octavo.config.py').write_text("CONFIG = {'lang': 'ja'}",
                                                encoding='utf-8')
        (self.d / 'data' / 'raw').mkdir(parents=True)
        (self.d / 'data' / 'derived').mkdir()
        (self.d / 'data' / 'raw' / 'survey.csv').write_text('a,b\n1,2\n',
                                                            encoding='utf-8')
        (self.d / 'data' / 'derived' / 'clean.csv').write_text('a\n1\n',
                                                               encoding='utf-8')
        self.cfg = config.load(self.d / 'octavo.config.py')

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_scan_finds_files_and_skips_dotfiles(self):
        (self.d / 'data' / '.DS_Store').write_text('x', encoding='utf-8')
        self.assertEqual(sorted(dataset.scan(self.cfg)),
                         ['derived/clean.csv', 'raw/survey.csv'])

    def test_record_then_no_drift(self):
        n, p = dataset.write(self.cfg)
        self.assertEqual(n, 2)
        self.assertTrue(p.is_file())
        self.assertEqual(dataset.compare(self.cfg), [])

    def test_manifest_is_not_counted_as_data(self):
        dataset.write(self.cfg)
        self.assertNotIn('HASHES.json', dataset.scan(self.cfg))
        self.assertEqual(dataset.compare(self.cfg), [])

    def test_changed_file_is_caught(self):
        dataset.write(self.cfg)
        (self.d / 'data' / 'raw' / 'survey.csv').write_text('a,b\n9,9\n',
                                                            encoding='utf-8')
        drift = dataset.compare(self.cfg)
        self.assertEqual([(x.kind, x.path) for x in drift],
                         [('changed', 'raw/survey.csv')])

    def test_missing_and_untracked_are_caught(self):
        dataset.write(self.cfg)
        (self.d / 'data' / 'raw' / 'survey.csv').unlink()
        (self.d / 'data' / 'raw' / 'new.csv').write_text('x\n', encoding='utf-8')
        kinds = {x.kind for x in dataset.compare(self.cfg)}
        self.assertEqual(kinds, {'missing', 'untracked'})

    def test_no_record_means_no_drift(self):
        self.assertEqual(dataset.compare(self.cfg), [])


# =====================================================================
class TypstSlides(unittest.TestCase):
    """TeX 無しで組むスライド。pandoc を呼ばない部分。"""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        make_project(self.d / 'p', docs=ALL_KINDS)
        self.cfg = config.load(self.d / 'p' / 'octavo.config.py')
        self.backend = be.get('typst-slides')

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def ctx(self, **kw) -> Ctx:
        return Ctx(cfg=self.cfg, backend=self.backend, out_dir=self.d,
                   profile='handout', **kw)

    def figure(self, line: str, backend=None, **kw) -> str:
        backend = backend or self.backend
        ctx = Ctx(cfg=self.cfg, backend=backend, out_dir=self.d, profile='handout', **kw)
        m = crossref.IMAGE.match(line)
        return backend.fmt_figure(m, crossref.label_in(m.group('attr'), 'fig'), ctx)

    def test_a_figure_caption_and_label_make_a_numbered_figure(self):
        # キャプションとラベルがあれば番号付きの図（プリントと同じ番号、@fig-… の先）
        out = self.figure('![推移の説明](../assets/figures/trend.png){#fig-trend}')
        self.assertIn('image("', out)
        self.assertIn('#figure(', out)
        self.assertIn('caption: [推移の説明]', out)
        self.assertIn('<fig-trend>', out)

    def test_cjk_notice_ignores_the_template_and_comments(self):
        """英語の文書で毎回 [CJK] と出ていた。体裁の分岐・注釈の日本語は組まれない。"""
        from octavo.backends.latex import check_cjk
        for f in Path(self.cfg['table_dir']).glob('*'):
            f.unlink()                   # 日本語の仮の表は、ここでは数えさせない
        tpl = self.d / 'tpl.typ'
        tpl.write_text('#let case(b) = if lang == "ja" { "事例" } else { "Case" }\n',
                       encoding='utf-8')
        ctx = self.ctx()
        ctx.report = []
        check_cjk('// 手で直さない\n' + tpl.read_text(encoding='utf-8') + '\n= Title\n',
                  ctx, '.typ', 'hint', templates=[tpl])
        self.assertFalse(any('CJK' in r for r in ctx.report), ctx.report)
        check_cjk('= 見出し\n', ctx, '.typ', 'hint', templates=[tpl])
        self.assertTrue(any('CJK' in r for r in ctx.report), ctx.report)

    def test_a_figure_without_a_caption_stays_bare(self):
        out = self.figure('![](../assets/figures/trend.png)')
        self.assertIn('image("', out)
        self.assertNotIn('#figure(', out)

    def test_an_english_deck_does_not_count_the_numbering_rules_as_japanese(self):
        from octavo.backends.typst import crossref_rules
        ctx = self.ctx()
        ctx.report = []
        for f in Path(self.cfg['table_dir']).glob('*'):
            f.unlink()
        self.backend.check('#let octavo = (lang: "en")\n' + crossref_rules(ctx)
                           + '\n= Title\n', ctx)
        self.assertFalse(any('CJK' in r for r in ctx.report), ctx.report)

    def test_slide_options_default_to_the_old_layout_and_a_blue_accent(self):
        # #25: 差し色を書かないかぎり見た目（番号・扉・走りヘッダ）は変えない。
        # #28: 差し色そのものは既定でこの青が入る（None にすれば #25 の黒一色に戻せる）。
        typ = self.backend.meta_block(self.ctx(meta={}), 2)
        self.assertIn('numbering: none', typ)
        # 節の扉は既定で出さない（ユーザーの判断で True から変えた）
        self.assertIn('section-slides: false', typ)
        self.assertIn('accent: rgb("#0e2f92")', typ)
        # 左上の節名は既定で出す（#25 で既定を False にしたのを、ユーザーが戻した）
        self.assertIn('running-header: true', typ)

    def test_accent_can_still_be_turned_off_for_the_old_plain_look(self):
        self.cfg._v.update(slides_accent=None)
        typ = self.backend.meta_block(self.ctx(meta={}), 2)
        self.assertIn('accent: none', typ)

    def test_slide_options_reach_the_template(self):
        self.cfg._v.update(slides_numbering='1.1',
                           slides_section_slides=True,
                           slides_accent='#0e2f92',
                           slides_running_header=True)
        typ = self.backend.meta_block(self.ctx(meta={}), 2)
        self.assertIn('numbering: "1.1"', typ)
        self.assertIn('section-slides: true', typ)
        self.assertIn('accent: rgb("#0e2f92")', typ)
        self.assertIn('running-header: true', typ)

    def test_the_template_keys_the_restyling_off_the_accent(self):
        # 体裁の分岐は `styled`（= 差し色があるか）1つに集約してある。
        # 箇条書きの字下げだけは差し色と無関係に常に効く
        from octavo.paths import templates_dir
        tmpl = (templates_dir() / 'slides/typst-slides.typ').read_text(encoding='utf-8')
        self.assertIn('#let styled = octavo.accent != none', tmpl)
        self.assertRegex(tmpl, r'#set list\([^)]*indent: 1\.1em')
        self.assertNotRegex(tmpl.split('#let styled')[1].split('#set list')[0],
                            r'marker:')

    def test_a_bad_accent_or_numbering_is_refused(self):
        conf = self.d / 'p' / 'octavo.config.py'
        original = conf.read_text(encoding='utf-8')
        for key, bad in (('slides_accent', "'blue'"),
                         ('slides_accent', "'#ZZZ'"),
                         ('slides_numbering', '3')):
            with self.subTest(f'{key}={bad}'):
                conf.write_text(original.replace(
                    "    'slides_aspect': '16-9',",
                    f"    'slides_aspect': '16-9',\n    '{key}': {bad},"),
                    encoding='utf-8')
                with contextlib_redirect(), self.assertRaises(SystemExit):
                    config.load(conf)
        conf.write_text(original, encoding='utf-8')

    def test_the_numbering_rules_come_after_the_slide_template(self):
        # テンプレートの show heading は見出しを作り直すので、番号の体裁が先にあると
        # 節を数える処理まで届かず、節ごとの番号（図2.1）にならない
        typ = self.backend.postprocess('= 節\n== 枠\n本文\n', self.ctx(meta={}))
        self.assertLess(typ.index('#show heading: it =>'),
                        typ.index('#show: octavo-crossref-rules.with('))
        self.assertIn('section: auto', typ)
        self.assertIn('count-unnumbered: true', typ)

    def test_lecture_keeps_slide_blocks_and_drops_notes(self):
        doc = self.cfg.document('講義')
        ctx = self.ctx()
        body, _ = build.preprocess(self.cfg, doc, self.backend, ctx,
                                   doc.src.read_text(encoding='utf-8'))
        self.assertIn('スライドにだけ出る', body)
        self.assertNotIn('プリントにだけ出る', body)
        self.assertEqual(ctx.keep_classes, {'slides', 'slide', 'screen', 'typst-slides'})

    def test_notes_are_kept_only_where_they_can_be_shown(self):
        self.assertFalse(self.backend.keeps_notes)
        self.assertTrue(be.get('beamer').keeps_notes)

    def test_heading_with_content_becomes_a_titled_slide(self):
        from octavo.backends.typst_slides import promote_sections_with_content
        typ = ('= 背景\n<sec:1>\n== 問い\n<q>\n本文\n\n'
               '= 今日の狙い\n<aim>\n- 箇条\n\n'
               '#heading(level: 1, numbering: none)[参考文献]\n<bibliography>\n#block[x]\n\n'
               '= まとめ\n<end>\n')
        out = promote_sections_with_content(typ).split('\n')
        self.assertIn('= 背景', out)                    # 直後が見出し -> 節の扉のまま
        self.assertIn('== 今日の狙い', out)             # 直後が本文 -> 1枚
        self.assertIn('#heading(level: 2, numbering: none)[参考文献]', out)
        self.assertIn('= まとめ', out)                  # 最後で中身がない -> 扉のまま

    def test_meta_is_escaped_and_anonymous_drops_the_author(self):
        ctx = self.ctx(anonymous=True)
        ctx.meta = {'title': '題 [仮] #1', 'author': ['山田', '田中'], 'date': '2026'}
        block = self.backend.meta_block(ctx, 2)
        self.assertIn('title: [題 \\[仮\\] \\#1]', block)
        self.assertIn('author: none', block)            # anonymous_drop_meta に author
        self.assertIn('slide-level: 2', block)
        # 既定は等幅の BIZ UDゴシック、欧文だけ Inter、なければ Noto に落ちる
        self.assertIn('font: ((name: "Inter", covers: "latin-in-cjk"), '
                      '"BIZ UDGothic", "Noto Sans CJK JP", "Hiragino Kaku Gothic ProN", '
                      '"Yu Gothic", )',
                      block)

    def test_no_proportional_bizud_anywhere(self):
        """BIZ UD は等幅だけ。プロポーショナル（UDP）は使わない（ユーザーの指定）。"""
        from octavo.backends.typst import FONTS
        names = [n for latin, cjk in FONTS.values() for n in (latin, *cjk)]
        for tmpl in ('paper/ja/main.typ', 'paper/en/main.typ', 'slides/typst-slides.typ',
                     'slides/typst-notes.typ'):
            names += re.findall(r'"(BIZ [^"]+)"',
                                (ROOT / 'templates' / tmpl).read_text(encoding='utf-8'))
        self.assertTrue(any(n.startswith('BIZ UD') for n in names))
        self.assertFalse([n for n in names if n.startswith('BIZ UDP')])

    def test_english_decks_put_the_latin_font_first_without_covers(self):
        from octavo.backends.typst import font_expr
        self.assertTrue(font_expr('en', 'sans').startswith('("Inter", '))
        self.assertIn('covers: "latin-in-cjk"', font_expr('ja', 'sans'))

    def test_a_configured_font_list_is_used_as_is(self):
        self.cfg._v.update(slides_font=['Noto Sans CJK JP'])
        block = self.backend.meta_block(self.ctx(meta={}), 1)
        self.assertIn('font: ("Noto Sans CJK JP", )', block)

    def test_the_paper_layout_uses_the_same_fonts_as_the_handout(self):
        """main_ja.typ は手で持つ体裁なので、FONTS と同じ並びを書き写してある。"""
        from octavo.backends.typst import FONTS
        latin, cjk = FONTS['serif']
        for lang in ('ja', 'en'):
            text = (ROOT / 'templates' / f'paper/{lang}/main.typ').read_text(encoding='utf-8')
            for name in (latin, *cjk):
                self.assertIn(f'"{name}"', text, lang)

    def test_every_font_list_ends_with_what_a_bare_mac_or_windows_has(self):
        # 何も足していない Mac・Windows でも和文が組めること（ヒラギノ・游書体は最初からある）
        from octavo.backends.typst import FONTS, PLATFORM_FALLBACKS
        for kind, (_, cjk) in FONTS.items():
            for plat, names in PLATFORM_FALLBACKS.items():
                self.assertTrue(set(names) & set(cjk), f'{kind}: {plat} の受け皿がない')
            # 受け皿は並びの最後（ほかのどれもないときだけ使う）
            tail = cjk[-len(PLATFORM_FALLBACKS):]
            self.assertTrue(all(any(n in names for names in PLATFORM_FALLBACKS.values())
                                for n in tail), cjk)

    @unittest.skipUnless(shutil.which('pandoc'), 'pandoc がない')
    def test_the_handout_template_gets_the_font_list(self):
        # A4 プリントは自前のテンプレート（handout/handout.typ）で組む。pandoc には
        # --standalone も mainfont も渡さず、書体の並びは `#let octavo = (…)` で渡る
        from octavo.backends.typst import TypstBackend, handout_meta
        b = TypstBackend()
        ctx = Ctx(cfg=self.cfg, backend=b, out_dir=self.d, profile='handout')
        args = ' '.join(b.pandoc_args(ctx))
        self.assertNotIn('--standalone', args)
        self.assertNotIn('mainfont=', args)
        meta = handout_meta(ctx)
        # 講義ノートの本文はゴシック（明朝は使わない）
        font = meta.split('  font: ')[1].split('\n')[0]
        self.assertIn('BIZ UDGothic', font)
        self.assertNotIn('Mincho', font)
        self.assertIn('head-font: ((name: "Inter"', meta)

    def test_aspect_is_validated(self):
        (self.d / 'x.config.py').write_text(
            "CONFIG = {'slides_aspect': '16:9'}", encoding='utf-8')
        with self.assertRaises(SystemExit):
            config.load(self.d / 'x.config.py')

    def test_theorem_helpers_are_defined_before_first_use(self):
        # #show heading（節ごとにリセットする側）より前に定義されていないと
        # Typst の compile が「未定義の変数」で止まる。定義順そのものを固定する。
        from octavo.paths import templates_dir
        tmpl = (templates_dir() / 'slides/typst-slides.typ').read_text(encoding='utf-8')
        for name in ('theorem-counter', 'theorem-section', 'theorem(', 'labeled(',
                    'case(body)', 'question(body)', 'aside(body)', 'nb(body)',
                    'memo(body)', 'smallgray('):
            self.assertIn(name, tmpl)
        self.assertLess(tmpl.index('#let theorem-counter'),
                        tmpl.index('#show heading: it =>'))
        self.assertIn('theorem-counter.update(0)', tmpl)
        self.assertIn('theorem-section.step()', tmpl)

    @unittest.skipUnless(shutil.which('typst'), 'typst がない')
    def test_theorem_helpers_compile_and_reset_per_section(self):
        # 事例・論点・余談・注意・付記（旧ベーマープリアンブルの \newtheorem 相当）を
        # 原稿の素通しブロックから呼んで、節をまたいでも typst compile が通ることを見る。
        if not pandocrun.at_least(3, 1):
            self.skipTest('pandoc 3.1 以上が要る')
        slides_md = self.d / 'p' / 'slides' / 'slides.md'
        text = slides_md.read_text(encoding='utf-8')
        text += ded("""

            # 第2部

            ## 事例で確かめる

            ```{=typst}
            #case[○○の場合]
            #question[なぜ○○なのか]
            #aside[余談として]
            #nb[これは注意]
            #memo[これは付記]
            #smallgray[出典: テスト]
            ```
            """)
        slides_md.write_text(text, encoding='utf-8')
        r = build.build_one(self.cfg, self.cfg.document('slides'), 'typst-slides',
                            citations=False, offline=True, do_compile=True)
        self.assertTrue(r.ok, '\n'.join(r.report))
        self.assertIsNotNone(r.compiled, '\n'.join(r.report))
        self.assertTrue(r.compiled.exists())

    @unittest.skipUnless(HAVE_PANDOC and shutil.which('typst'), 'pandoc と typst が要る')
    def test_a_captioned_figure_stays_on_its_slide(self):
        """本文のあとのキャプションつきの図は、同じスライドの残りに収まる。

        図の中に「残りの高さ」の箱を入れていた頃は、画像が残りを使い切って
        キャプションの分だけはみ出し、図ごと題のない次のページに送られていた。
        """
        if not pandocrun.at_least(3, 1):
            self.skipTest('pandoc 3.1 以上が要る')
        slides_md = self.d / 'p' / 'slides' / 'slides.md'
        slides_md.write_text(ded("""
            ---
            title: 題
            ---

            ## 結果

            本文が1行ある。推移は@fig-trend。

            ![推移](../assets/figures/trend.png){#fig-trend}

            ## まとめ

            おわり
            """), encoding='utf-8')
        r = build.build_one(self.cfg, self.cfg.document('slides'), 'typst-slides',
                            citations=False, offline=True, do_compile=True)
        self.assertTrue(r.ok, '\n'.join(r.report))
        pdf = r.compiled.read_bytes()
        # タイトルスライド + 結果 + まとめ = 3 ページ（はみ出せば 4 になる）
        self.assertEqual(len(re.findall(rb'/Type\s*/Page(?!s)', pdf)), 3)


# =====================================================================
class TemplateOverrides(unittest.TestCase):
    """ひな型はプロジェクト → ユーザー → 同梱の順に探す（tmpl.py）。

    利用者が自分用に直す前提なので、直したものが init / new / build の
    すべてで本当に使われるかを見る。
    """

    def setUp(self):
        from octavo import tmpl
        self.tmpl = tmpl
        self.d = Path(tempfile.mkdtemp())
        self.home = self.d / 'config'
        self.env = unittest.mock.patch.dict(os.environ, {'XDG_CONFIG_HOME': str(self.home)})
        self.env.start()
        self.user = self.home / 'octavo' / 'templates'

    def tearDown(self):
        self.env.stop()
        shutil.rmtree(self.d, ignore_errors=True)

    def cli(self, *argv, cwd=None) -> tuple:
        from octavo import cli
        import io, contextlib
        out, err = io.StringIO(), io.StringIO()
        old = os.getcwd()
        os.chdir(cwd or self.d)
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = cli.main(list(argv))
        finally:
            os.chdir(old)
        return code, out.getvalue(), err.getvalue()

    def test_the_languages_ship_the_same_files(self):
        """ja と en で片方にしかないひな型があると、その言語のプロジェクトだけ欠ける。"""
        names = self.tmpl.bundled_names()
        for group in ('project', 'manuscripts', 'paper', 'replication'):
            ja = {n.split('/', 2)[2] for n in names if n.startswith(f'{group}/ja/')}
            en = {n.split('/', 2)[2] for n in names if n.startswith(f'{group}/en/')}
            self.assertTrue(ja, group)
            self.assertEqual(ja, en, group)

    def test_an_english_project_is_written_in_english(self):
        """init --lang en が日本語のひな型を置いていた（公開前に見つけた）。"""
        proj = make_project(self.d / 'p', docs=ALL_KINDS, lang='en')
        kana = re.compile(r'[\u3040-\u30ff]')
        for p in proj.rglob('*'):
            if p.is_file() and p.suffix in ('.md', '.qmd', '.py', '.bib', '.txt', '.json', '') \
                    and 'CLAUDE' not in p.name:
                text = p.read_text(encoding='utf-8', errors='replace')
                self.assertIsNone(kana.search(text), p.relative_to(proj))

    def test_every_file_init_writes_is_listed(self):
        """init が書くものはどれも template list に出る（＝コピーして直せる）。

        一度、名前が README.md のものを全部「説明書き」として落としていた。
        """
        names = set(self.tmpl.bundled_names())
        for lang in ('ja', 'en'):
            for top in ('project', 'analysis'):
                for rel in self.tmpl.tree([f'{top}/common', f'{top}/{lang}']):
                    self.assertTrue(f'{top}/common/{rel}' in names
                                    or f'{top}/{lang}/{rel}' in names, rel)
            self.assertIn(f'project/{lang}/README.md', names)
            self.assertIn(f'analysis/{lang}/data/raw/README.md', names)
            for section in ('common', 'analysis', 'paper', 'slides'):
                self.assertIn(f'claude/{lang}/{section}.md', names)

    @unittest.skipUnless((ROOT / '.git').exists() and shutil.which('git'), 'git の checkout ではない')
    def test_every_template_goes_public(self):
        """公開用ツリー（git archive）からひな型が1つも落ちないこと。

        `.gitattributes` の `CLAUDE.md export-ignore` が先頭の / 無しだったせいで、
        ひな型の project/*/CLAUDE.md まで公開ツリーから消えていた。
        """
        files = [f'templates/{n}' for n in self.tmpl.bundled_names()]
        out = subprocess.run(['git', '-C', str(ROOT), 'check-attr', 'export-ignore', '--', *files],
                             capture_output=True, text=True, check=True).stdout
        dropped = [line.split(':')[0] for line in out.splitlines() if line.endswith(': set')]
        self.assertEqual(dropped, [])

    def test_names_that_escape_are_refused(self):
        for bad in ('../x', '/etc/passwd', ''):
            with self.assertRaises(self.tmpl.TemplateError):
                self.tmpl.check_name(bad)

    def test_a_user_override_reaches_init_and_new(self):
        (self.user / 'project/ja/notes/reading').mkdir(parents=True)
        (self.user / 'project/ja/notes/reading/README.md').write_text('# 読書メモ @@NAME@@\n',
                                                                     encoding='utf-8')
        (self.user / 'paper/ja').mkdir(parents=True)
        (self.user / 'paper/ja/main.typ').write_text('// 自分の体裁\n', encoding='utf-8')
        proj = make_project(self.d / 'p', docs=(('paper', 'mypaper'),))
        self.assertEqual((proj / 'notes/reading/README.md').read_text(encoding='utf-8'),
                         '# 読書メモ p\n')
        self.assertEqual((proj / 'papers/mypaper/main.typ').read_text(encoding='utf-8'),
                         '// 自分の体裁\n')
        # 上書きしていないものは同梱のまま
        self.assertIn('octavo:example', (proj / 'papers/mypaper/paper.md').read_text(encoding='utf-8'))

    def test_the_project_beats_the_user_beats_the_bundled(self):
        proj = make_project(self.d / 'p', docs=())
        rel = 'slides/typst-slides.typ'
        self.assertEqual(self.tmpl.resolve(rel, proj)[0], self.tmpl.BUNDLED)
        (self.user / 'slides').mkdir(parents=True)
        (self.user / rel).write_text('// user\n', encoding='utf-8')
        self.assertEqual(self.tmpl.resolve(rel, proj)[0], self.tmpl.USER)
        (proj / 'templates/slides').mkdir(parents=True)
        (proj / 'templates' / rel).write_text('// project\n', encoding='utf-8')
        self.assertEqual(self.tmpl.resolve(rel, proj), (self.tmpl.PROJECT, proj / 'templates' / rel))

    def test_copy_list_and_diff(self):
        proj = make_project(self.d / 'p', docs=())
        rel = 'slides/typst-slides.typ'
        code, out, _ = self.cli('template', 'copy', rel, cwd=proj)
        self.assertEqual(code, 0)
        mine = proj / 'templates' / rel
        self.assertEqual(mine.read_bytes(), (paths.templates_dir() / rel).read_bytes())
        # 2回目は上書きしない
        code, _, err = self.cli('template', 'copy', rel, cwd=proj)
        self.assertEqual(code, 1)
        code, _, _ = self.cli('template', 'copy', rel, '--force', cwd=proj)
        self.assertEqual(code, 0)
        code, out, _ = self.cli('template', 'list', '--json', cwd=proj)
        rows = {r['name']: r['from'] for r in json.loads(out)['templates']}
        self.assertEqual(rows[rel], 'project')
        self.assertEqual(rows['slides/typst-notes.typ'], 'bundled')
        # 同梱と同じあいだは差分なし、直せば出る
        code, out, _ = self.cli('template', 'diff', rel, cwd=proj)
        self.assertNotIn('@@', out)
        mine.write_text(mine.read_text(encoding='utf-8') + '// mine\n', encoding='utf-8')
        code, out, _ = self.cli('template', 'diff', rel, cwd=proj)
        self.assertIn('+// mine', out)

    def test_copy_outside_a_project_needs_user(self):
        code, _, err = self.cli('template', 'copy', 'slides/typst-slides.typ')
        self.assertEqual(code, 1)
        self.assertIn('--user', err)
        code, _, _ = self.cli('template', 'copy', 'slides/typst-slides.typ', '--user')
        self.assertEqual(code, 0)
        self.assertTrue((self.user / 'slides/typst-slides.typ').is_file())
        code, _, _ = self.cli('template', 'copy', 'no/such.typ', '--user')
        self.assertEqual(code, 1)

    def test_headers_is_gone(self):
        """上書きの仕組みは1つだけ。`headers` はもう設定のキーではない。"""
        self.assertNotIn('headers', config.DEFAULTS)

    @unittest.skipUnless(HAVE_PANDOC, 'pandoc がない')
    def test_a_project_override_reaches_the_build(self):
        proj = make_project(self.d / 'p', docs=(('slides', 'deck'),))
        mine = proj / 'templates/slides/typst-slides.typ'
        mine.parent.mkdir(parents=True)
        mine.write_text((paths.templates_dir() / 'slides/typst-slides.typ')
                        .read_text(encoding='utf-8') + '\n// my-own-look\n', encoding='utf-8')
        cfg = config.load(proj / 'octavo.config.py')
        r = build.build_one(cfg, cfg.document('deck'), 'typst-slides',
                            citations=False, offline=True)
        self.assertTrue(r.ok, '\n'.join(r.report))
        self.assertIn('// my-own-look', r.outputs[0].read_text(encoding='utf-8'))


# =====================================================================
@unittest.skipUnless(shutil.which('git'), 'git がない')
class GitHubRelease(unittest.TestCase):
    """`octavo release`: 節目の版にタグを打ち、組んだ PDF を GitHub Release に付ける。

    本物の GitHub には行かない。`gh` は引数を書き残すだけの代役、push 先は
    手元の bare リポジトリ。
    """

    def setUp(self):
        from octavo import ghrelease
        self.gr = ghrelease
        self.d = Path(tempfile.mkdtemp())
        self.proj = make_project(self.d / 'p', docs=(('paper', 'mypaper'),))
        # 分析を実行した後の状態にする（仮の値ではなく、刻印も新しい）
        (self.proj / 'assets/values/analysis.json').write_text(
            '{"n_obs": 1523, "coef_x": 0.342, "se_x": 0.081, "p_x": "< .001"}\n',
            encoding='utf-8')
        cfg = config.load(self.proj / 'octavo.config.py')
        analysis.write_stamp(cfg, {analysis.key(cfg, u): {'newest': u.newest()}
                                   for u in analysis.units(cfg)})
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.email', 't@example.org')
        self.git('config', 'user.name', 't')
        self.git('add', '-A')
        self.git('commit', '-qm', 'first')
        subprocess.run(['git', 'init', '-q', '--bare', str(self.d / 'remote.git')], check=True)
        self.git('remote', 'add', 'origin', str(self.d / 'remote.git'))
        self.cfg = config.load(self.proj / 'octavo.config.py')

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def git(self, *args) -> str:
        return subprocess.run(['git', '-C', str(self.proj), *args], check=True,
                              capture_output=True, text=True).stdout

    def test_a_clean_project_passes(self):
        self.assertEqual(self.gr.preflight(self.cfg, 'mypaper', 'v1-submitted', need_gh=False),
                         'mypaper-v1-submitted')

    def test_every_problem_is_listed_at_once(self):
        """1つ直すたびに次の問題が出る、にならないように全部まとめて言う。"""
        self.git('tag', 'mypaper-v1')
        (self.proj / 'papers/mypaper/paper.md').write_text('changed\n', encoding='utf-8')
        (self.proj / 'assets/values/analysis.json').write_text(
            '{"_placeholder": "x", "n_obs": 1}\n', encoding='utf-8')
        with self.assertRaises(self.gr.ReleaseError) as cm:
            self.gr.preflight(self.cfg, 'mypaper', 'v1', need_gh=False)
        msg = str(cm.exception)
        self.assertIn('mypaper-v1', msg)                       # タグがもうある
        self.assertIn('papers/mypaper/paper.md', msg)          # コミットしていない
        self.assertIn('placeholder', msg)                   # 仮の値

    def test_a_stale_analysis_is_refused(self):
        qmd = self.proj / 'analysis/analysis.qmd'
        qmd.write_text(qmd.read_text(encoding='utf-8') + '\n', encoding='utf-8')
        self.git('commit', '-qam', 'edit the analysis')
        with self.assertRaises(self.gr.ReleaseError) as cm:
            self.gr.preflight(self.cfg, 'mypaper', 'v1', need_gh=False)
        self.assertIn('analysis/analysis.qmd', str(cm.exception))

    def test_bad_labels_and_unknown_documents(self):
        with self.assertRaises(self.gr.ReleaseError):
            self.gr.preflight(self.cfg, 'mypaper', 'v1 submitted', need_gh=False)
        with self.assertRaises(self.gr.ReleaseError):
            self.gr.preflight(self.cfg, 'nope', 'v1', need_gh=False)

    def test_outside_git(self):
        # Windows では .git の中のファイルが読み取り専用なので、書けるようにしてから消す
        def writable(f, p, _):
            os.chmod(p, 0o700)
            f(p)
        kw = {'onexc': writable} if sys.version_info >= (3, 12) else {'onerror': writable}
        shutil.rmtree(self.proj / '.git', **kw)
        with self.assertRaises(self.gr.ReleaseError):
            self.gr.preflight(self.cfg, 'mypaper', 'v1', need_gh=False)

    def test_attachments_are_named_after_the_version(self):
        """論文の PDF は main.pdf なので、そのままでは何の版か分からない。"""
        f = self.d / 'files'
        f.mkdir()
        for n in ('main.pdf', 'mypaper.docx', 'deck.pdf', 'deck-notes.pdf'):
            (f / n).write_bytes(b'x')
        R = build.Result
        got = self.gr.assets([
            R(doc='mypaper', target='typst', compiled=f / 'main.pdf'),
            R(doc='mypaper', target='docx', outputs=[f / 'mypaper.docx']),
            R(doc='deck', target='typst-slides', compiled=f / 'deck.pdf'),
            R(doc='deck', target='typst-notes', compiled=f / 'deck-notes.pdf'),
        ], 'v1')
        self.assertEqual([n for _, n in got],
                         ['mypaper-v1.pdf', 'mypaper-v1.docx',
                          'deck-v1-typst-slides.pdf', 'deck-v1-typst-notes.pdf'])

    @unittest.skipUnless(HAVE_PANDOC and shutil.which('typst'), 'pandoc か typst がない')
    @unittest.skipIf(os.name == 'nt', 'gh の代役が sh のスクリプト')
    def test_release_tags_pushes_and_uploads_the_fresh_pdf(self):
        bin_ = self.d / 'bin'
        bin_.mkdir()
        log = self.d / 'gh.log'
        gh = bin_ / 'gh'
        gh.write_text('#!/bin/sh\nprintf "%s\\n" "$@" >> ' + str(log) + '\n'
                      'for a in "$@"; do case "$a" in *.pdf) cp "$a" ' + str(self.d) + '/;; esac; done\n',
                      encoding='utf-8')
        gh.chmod(0o755)
        with unittest.mock.patch.dict(os.environ,
                                      {'PATH': f'{bin_}{os.pathsep}{os.environ["PATH"]}'}):
            with contextlib_redirect():
                import contextlib, io
                with contextlib.redirect_stdout(io.StringIO()):
                    code = self.gr.run(self.cfg, 'mypaper', 'v1', offline=True)
        self.assertEqual(code, 0)
        calls = log.read_text(encoding='utf-8')
        self.assertIn('release', calls)
        self.assertIn('mypaper-v1', calls)
        self.assertTrue((self.d / 'mypaper-v1.pdf').read_bytes().startswith(b'%PDF'))
        remote_tags = subprocess.run(['git', '-C', str(self.d / 'remote.git'), 'tag'],
                                     capture_output=True, text=True).stdout.split()
        self.assertEqual(remote_tags, ['mypaper-v1'])
        # 組んでも作業ツリーは汚れない（build/ は git の外）
        self.assertEqual(self.git('status', '--porcelain'), '')


# =====================================================================
class SectionSpans(unittest.TestCase):
    """講義ノートの「何行目から何行目までが第N回か」。

    VS Code のプレビューが、カーソルのある回のスライドを出すのに使う。
    回の拾い方は section_keys と同じ実装（_sections）を通ること。
    """
    DOC = ded("""
        ---
        title: 講義ノート
        ---

        前置き。どの回にも入らない。

        # 第1回 導入 {#intro}

        本文。

        ```
        # これは見出しではない
        ```

        # 第2回 理論

        本文2。

        # References
    """)

    def test_line_numbers_point_at_the_headings(self):
        lines = self.DOC.split('\n')
        spans = md.section_spans(self.DOC)
        self.assertEqual([k for k, _, _, _ in spans], ['intro', '02'])
        for _key, _title, start, _end in spans:
            self.assertTrue(lines[start - 1].startswith('# '))

    def test_the_spans_are_contiguous_and_stop_before_the_references(self):
        lines = self.DOC.split('\n')
        spans = md.section_spans(self.DOC)
        self.assertEqual(spans[0][3] + 1, spans[1][2])
        self.assertFalse(lines[spans[-1][3] - 1].startswith('# References'))

    def test_a_heading_inside_a_fence_is_not_a_session(self):
        self.assertEqual(len(md.section_spans(self.DOC)), 2)

    def test_the_keys_match_section_keys(self):
        self.assertEqual([(k, t) for k, t, _, _ in md.section_spans(self.DOC)],
                         md.section_keys(self.DOC))

    def test_no_front_matter_still_lines_up(self):
        doc = '# 一\n\na\n\n# 二\n\nb\n'
        spans = md.section_spans(doc)
        self.assertEqual([(k, a) for k, _, a, _ in spans], [('01', 1), ('02', 5)])

    def test_a_document_without_sections_has_no_spans(self):
        self.assertEqual(md.section_spans('ただの本文。\n'), [])


# =====================================================================
class TypstNotes(unittest.TestCase):
    """台本（発表者ノート）。スライドが落とす `::: notes` の行き先。"""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        make_project(self.d / 'p', docs=(('slides', 'deck'),))
        self.cfg = config.load(self.d / 'p' / 'octavo.config.py')
        self.src = ded("""
            ## スライドの題

            - 項目

            ::: notes
            ここで*例*を出す。
            :::
        """)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def filtered(self, backend_name: str) -> str:
        b = be.get(backend_name)
        ctx = Ctx(cfg=self.cfg, backend=b, out_dir=self.d, profile='slides')
        return md.filter_divs(self.src, ctx.keep_classes,
                              keep_notes=b.keeps_notes, report=[],
                              notes_wrap=b.notes_wrap)

    def test_slides_drop_the_notes(self):
        out = self.filtered('typst-slides')
        self.assertNotIn('例', out)
        self.assertNotIn('octavo-note', out)

    def test_notes_backend_wraps_them_in_raw_typst(self):
        out = self.filtered('typst-notes')
        self.assertIn('#octavo-note[', out)
        self.assertIn('ここで*例*を出す。', out)   # 中身は Markdown のまま
        self.assertNotIn('::: notes', out)
        # 開きと閉じが同じ数だけ出ること
        self.assertEqual(out.count('#octavo-note['), out.count('] // octavo-note'))

    def test_beamer_still_gets_the_div_itself(self):
        # beamer は div のまま pandoc に渡すと \note{} になる。包んではいけない
        out = self.filtered('beamer')
        self.assertIn('::: notes', out)
        self.assertNotIn('octavo-note', out)

    def test_it_keeps_the_same_content_as_the_deck(self):
        """取捨は typst-slides と同じ（is_slides）。違うのはノートと体裁だけ。"""
        slides = Ctx(cfg=self.cfg, backend=be.get('typst-slides'),
                     out_dir=self.d, profile='slides').keep_classes
        notes = Ctx(cfg=self.cfg, backend=be.get('typst-notes'),
                    out_dir=self.d, profile='slides').keep_classes
        self.assertEqual(slides - {'typst-slides'}, notes - {'typst-notes', 'script'})

    def test_a_figure_is_capped_so_the_note_fits_on_the_page(self):
        backend = be.get('typst-notes')
        ctx = Ctx(cfg=self.cfg, backend=backend, out_dir=self.d, profile='slides')
        m = crossref.IMAGE.match('![推移](../assets/figures/trend.png){#fig-trend}')
        out = backend.fmt_figure(m, 'fig-trend', ctx)
        self.assertIn('height: 5cm', out)
        self.assertNotIn('1fr', out)

    def test_the_two_templates_define_the_same_helpers(self):
        """同じ原稿が両方に通るので、`#case[…]` 等が片方にないと落ちる。"""
        import re as _re
        def helpers(name):
            text = (ROOT / 'templates' / name).read_text(encoding='utf-8')
            body = '\n'.join(l for l in text.split('\n')
                              if not l.lstrip().startswith('//'))
            return set(_re.findall(r'^#let ([\w-]+)', body, _re.M))
        slides = helpers('slides/typst-slides.typ')
        notes = helpers('slides/typst-notes.typ')
        self.assertEqual(slides - notes, set())
        self.assertEqual(notes - slides, {'octavo-note', 'octavo-script'})

    def test_helpers_are_defined_before_the_show_rule(self):
        text = (ROOT / 'templates' / 'slides/typst-notes.typ').read_text(encoding='utf-8')
        show = text.index('#show heading: it =>')
        for name in ('octavo-note', 'case', 'question', 'aside', 'nb', 'memo', 'octavo-untitled-slide'):
            self.assertLess(text.index(f'#let {name}'), show, name)

    @unittest.skipUnless(shutil.which('typst'), 'typst がない')
    def test_a_real_script_pdf_comes_out(self):
        """ノートと事例の両方を入れて、本当に typst compile まで通ること。"""
        if not pandocrun.at_least(3, 1):
            self.skipTest('pandoc 3.1 以上が要る')
        deck = self.d / 'p' / 'slides' / 'deck.md'
        deck.write_text(deck.read_text(encoding='utf-8') + ded("""

            ## 台本を試す

            - 見せる中身

            ```{=typst}
            #case[○○の場合]
            ```

            ::: notes
            ここは**話すだけ**。板書しない。
            :::
            """), encoding='utf-8')
        r = build.build_one(self.cfg, self.cfg.document('deck'), 'typst-notes',
                            citations=False, offline=True, do_compile=True)
        self.assertTrue(r.ok, '\n'.join(r.report))
        self.assertIsNotNone(r.compiled, '\n'.join(r.report))
        self.assertTrue(r.compiled.exists())
        # 台本はスライド（deck.pdf）と別の名前
        self.assertEqual(r.compiled.name, 'deck-notes.pdf')
        self.assertIn('#octavo-script(', r.outputs[0].read_text(encoding='utf-8'))
        # ノートは、スライドの PDF の中で書いてあったページに付く
        pages = json.loads((r.outputs[0].parent / 'deck.notes.json').read_text(encoding='utf-8'))
        deck_pdf = self.cfg.out_dir('typst-slides', self.cfg.document('deck')) / 'deck.pdf'
        self.assertTrue(deck_pdf.is_file())
        self.assertEqual(pages['pages'][-1], pages['count'])     # 最後に足したスライド
        if shutil.which('pdftotext'):
            text = subprocess.run(['pdftotext', '-enc', 'UTF-8', str(r.compiled), '-'],
                                  capture_output=True, text=True, encoding='utf-8').stdout
            self.assertIn('話すだけ', text)
            self.assertIn('台本を試す', text)        # スライドの絵（PDF のページ）の文字

    def test_the_deck_marks_where_each_note_was(self):
        b = be.get('typst-slides')
        ctx = Ctx(cfg=self.cfg, backend=b, out_dir=self.d, profile='slides')
        out = md.filter_divs(self.src + '\n::: notes\n2つ目\n:::\n', ctx.keep_classes,
                             keep_notes=False, notes_mark=b.notes_mark)
        self.assertIn('#metadata(0) <octavo-note-at>', out)
        self.assertIn('#metadata(1) <octavo-note-at>', out)
        self.assertNotIn('2つ目', out)

    def test_the_script_keeps_only_the_notes(self):
        b = be.get('typst-notes')
        doc = self.cfg.document('deck')
        ctx = Ctx(cfg=self.cfg, backend=b, out_dir=self.d, profile='slides', doc_name='deck',
                  document=doc)
        body = md.filter_divs('## 題\n\n見せる[^a]\n\n::: notes\n話す\n:::\n\n- 項目\n\n'
                              '  ::: notes\n  - 字下げ\n  :::\n\n[^a]: 脚注\n',
                              ctx.keep_classes, keep_notes=True, notes_wrap=b.notes_wrap)
        out = b.final_markdown(body, ctx)
        self.assertNotIn('見せる', out)
        self.assertIn('話す', out)
        self.assertIn('\n- 字下げ', out)                # 字下げは外す
        self.assertIn('[^a]: 脚注', out)
        self.assertIn('#octavo-script(json("deck.notes.json")', out)
        self.assertEqual(out.count('```{=typst}\n][\n```'), 1)


# =====================================================================
class PreviewCli(unittest.TestCase):
    """VS Code のプレビューが読む2つの口（`--json`）。

    拡張はここから「今のファイルはどの文書か」「PDF はどこに出たか」を
    引く。形を変えると拡張が黙って壊れるので、形そのものを見張る。
    """

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        make_project(self.d / 'p', docs=ALL_KINDS)
        self.cfg_path = self.d / 'p' / 'octavo.config.py'

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def run_cli(self, *argv) -> dict:
        from octavo import cli
        import io, contextlib
        args = cli.make_parser().parse_args(list(argv) + ['-c', str(self.cfg_path)])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            args.func(args)
        return json.loads(buf.getvalue().strip().split('\n')[-1])

    def test_documents_json_lists_every_manuscript(self):
        got = self.run_cli('documents', '--json')
        names = {d['name'] for d in got['documents']}
        self.assertEqual(names, {'paper', 'slides', '講義'})
        paper = next(d for d in got['documents'] if d['name'] == 'paper')
        self.assertEqual(paper['profile'], 'paper')
        self.assertTrue(paper['src'].endswith('paper.md'))
        self.assertTrue(paper['appendix'].endswith('appendix.md'))
        self.assertTrue(Path(paper['src']).is_absolute())

    def test_a_lecture_carries_its_sessions_with_line_numbers(self):
        got = self.run_cli('documents', '--json')
        lec = next(d for d in got['documents'] if d['name'] == '講義')
        self.assertTrue(lec['split_slides'])
        self.assertTrue(lec['parts'])
        lines = Path(lec['src']).read_text(encoding='utf-8').split('\n')
        for part in lec['parts']:
            self.assertTrue(part['name'].startswith('講義-'))
            self.assertTrue(lines[part['start_line'] - 1].startswith('# '))
            self.assertGreaterEqual(part['end_line'], part['start_line'])

    def test_a_lecture_says_whether_it_can_be_cut_into_handouts(self):
        """拡張は handouts を見て「回ごとの配布資料を作る」を出し、保存のたびに作り直す。
        回の区切り（::: {.session}）がなければ切り出せないので false。"""
        def lecture():
            return next(d for d in self.run_cli('documents', '--json')['documents']
                        if d['name'] == '講義')
        self.assertFalse(lecture()['handouts'])
        src = Path(lecture()['src'])
        text = src.read_text(encoding='utf-8')
        at = text.index('\n# ')
        src.write_text(text[:at] + '\n\n::: {.session #one}\n:::\n' + text[at:], encoding='utf-8')
        self.assertTrue(lecture()['handouts'])
        others = [d for d in self.run_cli('documents', '--json')['documents'] if d['name'] != '講義']
        self.assertFalse(any(d['handouts'] for d in others))

    def test_sessions_cover_the_cursor_without_gaps(self):
        """カーソル行から回を引くので、回と回のあいだに隙間があってはいけない。"""
        lec = next(d for d in self.run_cli('documents', '--json')['documents']
                   if d['name'] == '講義')
        for a, b in zip(lec['parts'], lec['parts'][1:]):
            self.assertEqual(a['end_line'] + 1, b['start_line'])

    def test_build_json_says_where_the_pdf_is(self):
        from octavo import cli
        import io, contextlib
        results = [build.Result(doc='paper', target='typst',
                                outputs=[Path('/tmp/body.typ')],
                                compiled=Path('/tmp/main.pdf'))]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = cli.print_results_json(results)
        got = json.loads(buf.getvalue())
        self.assertEqual(code, 0)
        self.assertTrue(got['ok'])
        self.assertEqual(got['results'][0]['compiled'], str(Path('/tmp/main.pdf')))
        self.assertEqual(got['results'][0]['outputs'], [str(Path('/tmp/body.typ'))])

    def test_build_json_reports_a_failure(self):
        from octavo import cli
        import io, contextlib
        results = [build.Result(doc='paper', target='typst', ok=False,
                                report=['[組版] 失敗'])]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = cli.print_results_json(results)
        got = json.loads(buf.getvalue())
        self.assertEqual(code, 1)
        self.assertFalse(got['ok'])
        self.assertIsNone(got['results'][0]['compiled'])
        self.assertIn('[組版] 失敗', got['results'][0]['report'])


# =====================================================================
class Anonymous(unittest.TestCase):
    """匿名審査用に組む。"""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        make_project(self.d / 'p')
        self.root = self.d / 'p'
        (self.root / PAPER_MD).write_text(ded("""
            ---
            title: 題
            ---

            ## 1. はじめに

            本文。

            ::: {.no-anonymous}
            謝辞: 科研費…の助成を受けた。
            :::

            ::: {.anonymous-only}
            [謝辞は査読後に記載]
            :::
            """), encoding='utf-8')
        self.cfg = config.load(self.root / 'octavo.config.py')
        # 著者名の突き合わせを試す側なので、名前はここで決める
        # （ひな型は '著者名' というただの placeholder）
        self.cfg['meta']['author'] = AUTHOR

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def body(self, anonymous: bool) -> str:
        doc = self.cfg.document('paper')
        backend = be.get('latex')
        ctx = Ctx(cfg=self.cfg, backend=backend, out_dir=self.root,
                  profile=doc.profile, doc_name='paper', anonymous=anonymous)
        ctx.values, _ = values.load(self.cfg)
        return build.preprocess(self.cfg, doc, backend, ctx, md.read(Path(doc.src)))[0]

    def test_acknowledgements_are_dropped_only_when_anonymous(self):
        self.assertIn('謝辞: 科研費', self.body(False))
        self.assertNotIn('謝辞は査読後', self.body(False))
        self.assertNotIn('謝辞: 科研費', self.body(True))
        self.assertIn('謝辞は査読後', self.body(True))

    def test_keep_classes_gets_the_flag(self):
        ctx = Ctx(cfg=self.cfg, backend=be.get('latex'), out_dir=self.root,
                  anonymous=True)
        self.assertIn('anonymous', ctx.keep_classes)

    def test_title_metadata_is_dropped(self):
        doc = self.cfg.document('paper')
        for anonymous, expected in ((False, True), (True, False)):
            ctx = Ctx(cfg=self.cfg, backend=be.get('docx'), out_dir=self.root,
                      profile='paper', anonymous=anonymous)
            ctx.meta = {'title': '題', 'author': AUTHOR, 'institute': '所属'}
            m = build._pandoc_meta(self.cfg, ctx)
            self.assertEqual('author' in m, expected)
            self.assertIn('title', m)

    def test_flags_file_contents(self):
        for anonymous, want in ((True, 'true'), (False, 'false')):
            ctx = Ctx(cfg=self.cfg, backend=be.get('latex'), out_dir=self.root,
                      anonymous=anonymous)
            name, text = be.get('latex').flags(ctx)
            self.assertEqual(name, 'flags.tex')
            self.assertIn(f'\\anonymous{want}', text)
            name, text = be.get('typst').flags(ctx)
            self.assertIn(f'#let anonymous = {want}', text)

    def test_guard_detection_ignores_declaration_and_comments(self):
        latex = be.get('latex')
        self.assertFalse(latex.uses_anonymous_guard(
            '\\newif\\ifanonymous\\anonymousfalse\n'))
        self.assertFalse(latex.uses_anonymous_guard('% \\ifanonymous を使う\n'))
        self.assertTrue(latex.uses_anonymous_guard(
            '\\newif\\ifanonymous\n\\ifanonymous\\else\\author{X}\\fi\n'))
        typst = be.get('typst')
        self.assertFalse(typst.uses_anonymous_guard('// #if anonymous と書く\n'))
        self.assertTrue(typst.uses_anonymous_guard('#if anonymous [A] else [B]\n'))

    def test_self_citations_are_found(self):
        (self.root / PAPER_MD).write_text('@sato2023 と @yamada2020。\n',
                                            encoding='utf-8')
        (self.root / 'literature.bib').write_text(
            '@article{sato2023, author={' + AUTHOR + '}, title={X}, date={2023}}\n'
            '@article{yamada2020, author={山田 太郎}, title={Y}, date={2020}}\n',
            encoding='utf-8')
        cfg = config.load(self.root / 'octavo.config.py')
        cfg['meta']['author'] = AUTHOR
        self.assertEqual(check.self_citations(cfg), ['sato2023'])

    def test_bundle_flags_an_unguarded_author_name(self):
        out = self.cfg.out_dir('latex', self.cfg.document('paper'))
        out.mkdir(parents=True, exist_ok=True)
        (out / 'body.tex').write_text('本文\n', encoding='utf-8')
        (out / 'main.tex').write_text('\\author{' + AUTHOR + '}\n', encoding='utf-8')
        (out / 'flags.tex').write_text('\\anonymoustrue\n', encoding='utf-8')
        dest = self.d / 'sub'
        res = bundle.collect(self.cfg, 'latex', dest, self.cfg.document('paper'))
        bundle.check_anonymous(self.cfg, 'latex', dest, res)
        self.assertFalse(res.ok)
        self.assertTrue(any('is still in' in r for r in res.report))

    def test_bundle_accepts_a_guarded_author_name(self):
        out = self.cfg.out_dir('latex', self.cfg.document('paper'))
        out.mkdir(parents=True, exist_ok=True)
        (out / 'body.tex').write_text('本文\n', encoding='utf-8')
        (out / 'main.tex').write_text(
            '\\ifanonymous\\author{[匿名]}\\else\\author{' + AUTHOR + '}\\fi\n',
            encoding='utf-8')
        (out / 'flags.tex').write_text('\\anonymoustrue\n', encoding='utf-8')
        dest = self.d / 'sub'
        res = bundle.collect(self.cfg, 'latex', dest, self.cfg.document('paper'))
        bundle.check_anonymous(self.cfg, 'latex', dest, res)
        self.assertTrue(res.ok, '\n'.join(res.report))
        self.assertTrue(any('does not reach the typeset output' in r for r in res.report))

    def test_bundle_refuses_when_the_build_was_not_anonymous(self):
        out = self.cfg.out_dir('latex', self.cfg.document('paper'))
        out.mkdir(parents=True, exist_ok=True)
        (out / 'body.tex').write_text('本文\n', encoding='utf-8')
        (out / 'flags.tex').write_text('\\anonymousfalse\n', encoding='utf-8')
        dest = self.d / 'sub'
        res = bundle.collect(self.cfg, 'latex', dest, self.cfg.document('paper'))
        bundle.check_anonymous(self.cfg, 'latex', dest, res)
        self.assertFalse(res.ok)
        self.assertTrue(any('no sign this was built anonymously' in r for r in res.report))


# =====================================================================
class WordReview(unittest.TestCase):
    """共著者が返してきた .docx から変更履歴を拾う。"""

    W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def make(self, body: str, comments: str = '') -> Path:
        import zipfile as zf
        p = self.d / 'back.docx'
        with zf.ZipFile(p, 'w') as z:
            z.writestr('word/document.xml',
                       f'<?xml version="1.0"?><w:document {self.W}><w:body>'
                       f'{body}</w:body></w:document>')
            if comments:
                z.writestr('word/comments.xml',
                           f'<?xml version="1.0"?><w:comments {self.W}>'
                           f'{comments}</w:comments>')
        return p

    def test_insertion_and_deletion(self):
        p = self.make(
            '<w:p><w:r><w:t>係数は 0.342</w:t></w:r>'
            '<w:ins w:id="1" w:author="田中" w:date="2026-09-05T10:11:00Z">'
            '<w:r><w:t>（有意）</w:t></w:r></w:ins>'
            '<w:del w:id="2" w:author="田中"><w:r><w:delText>。以上。</w:delText>'
            '</w:r></w:del></w:p>')
        paras = review.collect(p)
        self.assertEqual(len(paras), 1)
        kinds = [(c.kind, c.text) for c in paras[0].changes]
        self.assertEqual(kinds, [('ins', '（有意）'), ('del', '。以上。')])
        # 反映後の読み: 挿入は入り、削除は消える
        self.assertEqual(paras[0].context, '係数は 0.342（有意）')

    def test_comment_is_attached_to_its_paragraph(self):
        p = self.make(
            '<w:p><w:commentRangeStart w:id="7"/><w:r><w:t>先行研究</w:t></w:r>'
            '<w:commentRangeEnd w:id="7"/>'
            '<w:r><w:commentReference w:id="7"/></w:r></w:p>',
            '<w:comment w:id="7" w:author="田中" w:date="2026-09-05T10:20:00Z">'
            '<w:p><w:r><w:t>Sato (2021) にも触れては</w:t></w:r></w:p>'
            '</w:comment>')
        paras = review.collect(p)
        self.assertEqual([c.kind for c in paras[0].changes], ['comment'])
        self.assertEqual(paras[0].changes[0].text, 'Sato (2021) にも触れては')

    def test_a_comment_is_not_reported_twice(self):
        p = self.make(
            '<w:p><w:commentRangeStart w:id="1"/><w:r><w:t>x</w:t></w:r>'
            '<w:commentRangeEnd w:id="1"/>'
            '<w:r><w:commentReference w:id="1"/></w:r></w:p>',
            '<w:comment w:id="1" w:author="A"><w:p><w:r><w:t>note</w:t></w:r>'
            '</w:p></w:comment>')
        self.assertEqual(len(review.collect(p)[0].changes), 1)

    def test_untouched_paragraphs_are_skipped(self):
        p = self.make('<w:p><w:r><w:t>触っていない</w:t></w:r></w:p>')
        self.assertEqual(review.collect(p), [])

    def test_authors_are_counted(self):
        p = self.make(
            '<w:p><w:ins w:id="1" w:author="田中"><w:r><w:t>a</w:t></w:r></w:ins>'
            '<w:ins w:id="2" w:author="佐藤"><w:r><w:t>b</w:t></w:r></w:ins></w:p>')
        self.assertEqual(review.authors(review.collect(p)), {'田中': 1, '佐藤': 1})

    def test_a_non_docx_is_reported_not_raised(self):
        bad = self.d / 'x.docx'
        bad.write_text('これは zip ではない', encoding='utf-8')
        with self.assertRaises(review.DocxError):
            review.collect(bad)
        self.assertEqual(review.run(bad), 1)


# =====================================================================
class SubmissionChecks(unittest.TestCase):
    """投稿規定の分量と、複製パッケージ。"""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        make_project(self.d / 'p', docs=(('paper', 'paper'), ('slides', 'talk')))
        self.root = self.d / 'p'

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def cfg(self, extra: str = '') -> config.Config:
        (self.root / 'octavo.config.py').write_text(
            "CONFIG = {'lang': 'ja', 'analysis': ['analysis/*.qmd'], "
            "'documents': {'paper': {'src': 'papers/paper/paper.md', 'profile': 'paper'},"
            " 'talk': {'src': 'slides/talk.md', 'profile': 'slides'}}" + extra + '}',
            encoding='utf-8')
        return config.load(self.root / 'octavo.config.py')

    def test_no_limits_means_no_item(self):
        labels = [i.label for i in audit.collect(self.cfg())]
        self.assertNotIn('length', labels)

    def test_exceeding_a_limit_is_fatal(self):
        cfg = self.cfg(", 'word_limit': 5")
        item = {i.label: i for i in audit.collect(cfg)}['length']
        self.assertFalse(item.ok)
        self.assertTrue(item.fatal)

    def test_limits_apply_to_papers_only(self):
        """投稿規定は論文のもの。同じリポジトリのスライドを数えて落とさない。"""
        cfg = self.cfg(", 'word_limit': 5")
        lines = {i.label: i for i in audit.collect(cfg)}['length'].lines
        self.assertTrue(any('paper' in line for line in lines))
        self.assertFalse(any('talk' in line for line in lines))

    def test_within_a_limit_is_ok(self):
        cfg = self.cfg(", 'word_limit': 100000")
        item = {i.label: i for i in audit.collect(cfg)}['length']
        self.assertTrue(item.ok)

    def test_abstract_is_measured_separately(self):
        cfg = self.cfg(", 'abstract_char_limit': 5")
        over = [line for line in
                {i.label: i for i in audit.collect(cfg)}['length'].lines
                if 'abstract' in line]
        self.assertTrue(over)

    def test_replication_package_contents(self):
        cfg = self.cfg()
        (self.root / 'data' / 'derived' / 'clean.csv').write_text(
            'a\n1\n', encoding='utf-8')
        dest = self.d / 'rep'
        res = bundle.replication(cfg, dest)
        names = {p.relative_to(dest).as_posix() for p in res.files}
        self.assertIn('analysis/analysis.qmd', names)
        self.assertIn('assets/values/analysis.json', names)
        self.assertIn('data/HASHES.json', names)
        self.assertIn('data/derived/clean.csv', names)
        self.assertIn('analysis/octavo.R', names)
        self.assertIn('README.md', names)
        self.assertIn('literature.bib', names)

    def test_replication_keeps_the_project_layout(self):
        # 分析の書き出し先（assets/…）も、手で描いた図の元（figures/*.typ）も、プロジェクトと同じ場所
        cfg = self.cfg()
        (self.root / 'figures' / 'dag.typ').write_text('#box[]', encoding='utf-8')
        names = {p.relative_to(self.d / 'rep2').as_posix()
                 for p in bundle.replication(cfg, self.d / 'rep2').files}
        self.assertIn('figures/dag.typ', names)
        self.assertTrue(any(n.startswith('assets/figures/') for n in names), names)
        self.assertTrue(any(n.startswith('assets/tables/') for n in names), names)

    def test_raw_data_is_excluded_unless_asked(self):
        cfg = self.cfg()
        (self.root / 'data' / 'raw' / 'survey.csv').write_text(
            'a\n1\n', encoding='utf-8')
        plain = {p.name for p in bundle.replication(cfg, self.d / 'a').files}
        self.assertNotIn('survey.csv', plain)
        withraw = {p.name for p in
                   bundle.replication(cfg, self.d / 'b', with_raw=True).files}
        self.assertIn('survey.csv', withraw)

    def test_replication_readme_mentions_the_session(self):
        cfg = self.cfg()
        text = (bundle.replication(cfg, self.d / 'c').out / 'README.md') \
            .read_text(encoding='utf-8')
        self.assertNotIn('@@', text)
        self.assertIn('octavo data status', text)


class CitationsByLanguage(unittest.TestCase):
    """日本語の文書: 英語の文献は英語の決まりで、日本語の文献（langid）は日本語の形で組む。"""

    BIB = textwrap.dedent("""\
        @article{smith2003, author={Smith, John and Taylor, Ann and Brown, Bob and Green, Carl},
          title={An Example Article}, journaltitle={Journal of Examples}, date={2003},
          volume={4}, pages={1--10}, langid={english}}
        @article{yamada2020, author={山田, 太郎 and 田中, 花子}, title={日本語論文の例},
          journaltitle={見本学会誌}, date={2020}, volume={12}, pages={1--20}, langid={japanese}}
        @book{sato2018, author={佐藤, 一郎 and 鈴木, 次郎 and 高橋, 三郎 and 伊藤, 四郎},
          title={日本語の本}, publisher={見本出版}, date={2018}, langid={japanese}}
        @incollection{kato2015, author={加藤, 五郎}, title={論文集の章}, booktitle={論文集の名前},
          editor={中村, 六郎}, publisher={見本出版}, date={2015}, pages={10--20}, langid={japanese}}
        @article{ito2021, author={伊藤, 七子}, title={号と DOI}, journaltitle={見本学会誌},
          date={2021}, volume={3}, number={2}, pages={5--9}, doi={10.1234/abcd}, langid={japanese}}
        """)

    # APA のように、2人を & でつなぎ、年の前に , を置く書式（CSL はキャッシュで CI に無いので、ここで書く）
    APA_LIKE = textwrap.dedent("""\
        <?xml version="1.0" encoding="utf-8"?>
        <style xmlns="http://purl.org/net/xbiblio/csl" class="in-text" version="1.0">
          <info><title>t</title><id>t</id><updated>2020-01-01T00:00:00+00:00</updated></info>
          <citation et-al-min="3" et-al-use-first="1">
            <layout prefix="(" suffix=")" delimiter="; ">
              <group delimiter=", "><names variable="author"><name form="short" and="symbol"/></names>
              <date variable="issued"><date-part name="year"/></date></group></layout>
          </citation>
          <bibliography><layout><names variable="author"><name and="symbol"/></names>
            <text value=". "/><text variable="title" font-style="italic"/></layout></bibliography>
        </style>
        """)

    def filter_for(self, lang, **cfg_over):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'p'
            make_project(root, docs=(), lang=lang, analysis=False)
            cfg = config.load(root / 'octavo.config.py')
            cfg._v.update(cfg_over)
            ctx = Ctx(cfg=cfg, backend=be.get('typst'), out_dir=root, profile='paper')
            return build.citation_filter(cfg, ctx)

    def test_only_japanese_documents_use_the_filter(self):
        self.assertEqual(self.filter_for('ja').name, 'japanese.lua')
        self.assertIsNone(self.filter_for('en'))
        self.assertIsNone(self.filter_for('ja', citations_by_language=False))
        self.assertIsNone(self.filter_for('ja', csl_locale='en-US'))

    def run_filter(self, text, csl=None, form=None):
        with tempfile.TemporaryDirectory() as tmp:
            bib = Path(tmp) / 'r.bib'
            bib.write_text(self.BIB, encoding='utf-8')
            style = None
            if csl:
                style = Path(tmp) / 's.csl'
                style.write_text(csl, encoding='utf-8')
            lua = tmpl.find('citations/japanese.lua')
            args = pandocrun.citeproc_args(bib, style, 'ja-JP', '参考文献', lua_filter=lua)
            if form:
                args += ['-M', f'octavo-ja-form={form}']
            self.assertIn('--lua-filter', args)
            self.assertNotIn('--citeproc', args)
            return pandocrun.run(text, ['-f', 'markdown', '-t', 'plain', '--wrap=none', *args],
                                 cwd=Path(tmp))

    @unittest.skipUnless(HAVE_PANDOC and pandocrun.at_least(2, 19, 1), 'needs pandoc 2.19.1+')
    def test_japanese_entries_do_not_depend_on_the_style(self):
        out = self.run_filter('[@yamada2020]、[@sato2018]、[@kato2015]、[@ito2021]。\n',
                              self.APA_LIKE)
        self.assertIn('(山田・田中, 2020)', out)              # & も ・ に。年の前の , は書式のまま
        self.assertIn('(佐藤ほか, 2018)', out)
        self.assertIn('山田太郎・田中花子 (2020)「日本語論文の例」『見本学会誌』12: 1–20.', out)
        self.assertIn('加藤五郎 (2015)「論文集の章」中村六郎編『論文集の名前』見本出版, 10–20.', out)
        self.assertIn('伊藤七子 (2021)「号と DOI」『見本学会誌』3(2): 5–9. '
                      'https://doi.org/10.1234/abcd', out)
        self.assertNotIn('山田太郎.', out)                     # 書式の書誌の形（名前. 題）は使わない

    @unittest.skipUnless(HAVE_PANDOC and pandocrun.at_least(2, 19, 1), 'needs pandoc 2.19.1+')
    def test_the_form_of_japanese_works_can_be_chosen(self):
        text = '[@yamada2020]、[@sato2018]、[@kato2015]、[@ito2021]。\n'
        out = self.run_filter(text, form='fullwidth')
        self.assertIn('山田太郎・田中花子（2020）「日本語論文の例」『見本学会誌』12巻、1–20頁。', out)
        self.assertIn('佐藤一郎・鈴木次郎・高橋三郎・伊藤四郎（2018）『日本語の本』見本出版。', out)
        self.assertIn('加藤五郎（2015）「論文集の章」中村六郎編『論文集の名前』見本出版、10–20頁。', out)
        self.assertIn('伊藤七子（2021）「号と DOI」『見本学会誌』3巻2号、5–9頁。 '
                      'https://doi.org/10.1234/abcd', out)
        out = self.run_filter(text, form='period')
        self.assertIn('山田太郎・田中花子．2020．「日本語論文の例」『見本学会誌』12巻、1–20頁。', out)
        # 本文中の引用は書式（CSL）のまま
        self.assertIn('(山田・田中 2020)', out)

    def test_the_form_reaches_the_filter_only_when_it_is_used(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'p'
            make_project(root, docs=(), lang='ja', analysis=False)
            cfg = config.load(root / 'octavo.config.py')
            cfg._v['japanese_citation_form'] = 'period'
            ctx = Ctx(cfg=cfg, backend=be.get('typst'), out_dir=root, profile='paper')
            self.assertEqual(build.citation_form_args(cfg, ctx), ['-M', 'octavo-ja-form=period'])
            cfg._v['citations_by_language'] = False
            self.assertEqual(build.citation_form_args(cfg, ctx), [])

    def test_an_unknown_form_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'x.config.py'
            p.write_text("CONFIG = {'japanese_citation_form': 'nenpo'}", encoding='utf-8')
            with self.assertRaises(SystemExit), contextlib_redirect():
                config.load(p)

    @unittest.skipUnless(HAVE_PANDOC and pandocrun.at_least(2, 19, 1), 'needs pandoc 2.19.1+')
    def test_each_work_in_its_own_language(self):
        out = self.run_filter('@smith2003、[@yamada2020]、@sato2018。\n')
        self.assertIn('Smith et al. (2003)', out)            # 英語の文献は英語のまま
        self.assertIn('(山田・田中 2020)', out)
        self.assertIn('佐藤ほか (2018)', out)
        self.assertIn('Ann Taylor, Bob Brown, and Carl Green. 2003.', out)
        self.assertIn('“An Example Article.”', out)
        self.assertIn('山田太郎・田中花子 (2020)「日本語論文の例」『見本学会誌』12: 1–20.', out)
        self.assertIn('伊藤四郎 (2018)『日本語の本』見本出版.', out)
        self.assertNotIn('年', out)                          # ja-JP の「2003年」にならない
        self.assertNotIn('ほか (2003', out)


class MathMacros(unittest.TestCase):
    """数式のマクロ。論文の本文・要旨・付録と講義の回ごとのデッキは別々に pandoc に
    通すので、定義を集めてそれぞれに付け直す（さもないと、どこかで効かない）。"""

    SRC = ded("""
        ---
        title: T
        ---

        \\newcommand{\\E}{\\mathbb{E}}
        \\DeclareMathOperator{\\Cov}{Cov}

        ```latex
        \\newcommand{\\Shown}{only an example}
        ```

        ## 要旨

        期待値 $\\E[y]$。

        ## 1. はじめに

        本文でも $\\E[x]$。
        """)

    def test_definitions_outside_code_are_collected_once(self):
        got = md.math_macros(self.SRC, '\\newcommand{\\E}{\\mathbb{E}}\n\\renewcommand{\\x}{y}\n')
        self.assertEqual(got, ['\\newcommand{\\E}{\\mathbb{E}}',
                               '\\DeclareMathOperator{\\Cov}{Cov}',
                               '\\renewcommand{\\x}{y}'])
        self.assertEqual(md.math_macros('\\newcommandfoo\n'), [])

    def test_they_are_dropped_where_written_but_code_is_left_alone(self):
        out = md.drop_math_macros(self.SRC)
        self.assertNotIn('\\newcommand{\\E}', out)
        self.assertNotIn('\\DeclareMathOperator', out)
        self.assertIn('\\newcommand{\\Shown}', out)

    def test_every_part_gets_them(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        make_project(d / 'p', docs=(('paper', 'paper'),))
        cfg = config.load(d / 'p' / 'octavo.config.py')
        doc = cfg.document('paper')
        backend = be.get('typst')
        ctx = Ctx(cfg=cfg, backend=backend, out_dir=d, profile='paper')
        ctx.math_macros = md.math_macros(self.SRC)
        body, abstract = build.preprocess(cfg, doc, backend, ctx, self.SRC)
        for part in (body, abstract):
            self.assertIn('\\newcommand{\\E}{\\mathbb{E}}', part)
            self.assertEqual(part.count('\\newcommand{\\E}'), 1)   # 二重に定義しない

    def test_passed_through_definitions_leave_the_output(self):
        tex = '\\newcommand{\\E}{\\mathbb{E}}\n\\(\\mathbb{E}[x]\\)\n'
        self.assertEqual(md.drop_output_macros(tex, ['\\newcommand{\\E}{\\mathbb{E}}']),
                         '\\(\\mathbb{E}[x]\\)\n')

    @unittest.skipUnless(HAVE_PANDOC, 'pandoc がない')
    def test_body_abstract_appendix_and_sessions_all_expand(self):
        if not pandocrun.at_least(3, 1):
            self.skipTest('pandoc が古い')
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        root = make_project(d / 'p', docs=(('paper', 'paper'), ('lecture', 'lec')))
        # 論文: 定義は最初の見出しの前（題の周りと一緒に落とされやすい所）
        paper = root / 'papers' / 'paper' / 'paper.md'
        text = paper.read_text(encoding='utf-8')
        at = text.index('\n# ')
        text = text[:at] + '\n\n\\newcommand{\\E}{\\mathbb{E}}\n' + text[at:]
        text = re.sub(r'(\n# (?:要旨|Abstract)\s*\n+)', r'\1要旨で $\\E[y]$。\n\n', text, count=1)
        text = re.sub(r'(\n# はじめに[^\n]*\n)', r'\1\n本文で $\\E[x]$。\n', text, count=1)
        paper.write_text(text, encoding='utf-8')
        (root / 'papers' / 'paper' / 'appendix.md').write_text(
            '## 付録A．補足\n\n付録で $\\E[z]$。\n', encoding='utf-8')
        # 講義: 定義は最初の `#` の前（回ごとに分けると落ちる所）
        lec = root / 'lectures' / 'lec.md'
        text = lec.read_text(encoding='utf-8')
        at = text.index('\n# ')
        text = text[:at] + '\n\n\\newcommand{\\E}{\\mathbb{E}}\n' + text[at:]
        lec.write_text(re.sub(r'(\n# [^\n]*\n)', r'\1\n回で $\\E[w]$。\n', text), encoding='utf-8')
        cfg = config.load(root / 'octavo.config.py')

        for tgt, ext in (('typst', '.typ'), ('latex', '.tex')):
            for appendix in (False, True):
                r = build.build_one(cfg, cfg.document('paper'), tgt, appendix=appendix,
                                    citations=False, offline=True)
                self.assertTrue(r.ok, '\n'.join(r.report))
            out = cfg.out_dir(tgt, cfg.document('paper'))
            for f in ('body', 'abstract', 'appendix'):
                text = (out / (f + ext)).read_text(encoding='utf-8')
                self.assertIn('bb(E)' if tgt == 'typst' else '\\mathbb{E}', text, f + ext)
                self.assertNotIn('\\newcommand{\\E}', text, f + ext)   # main.tex で二重定義しない
        parts = cfg.parts(cfg.document('lec'))
        self.assertTrue(parts)
        for part in parts:
            r = build.build_one(cfg, part, 'typst-slides', citations=False, offline=True)
            self.assertTrue(r.ok, '\n'.join(r.report))
            deck = (cfg.out_dir('typst-slides', part) / f'lec-slides-{part.part}.typ').read_text(encoding='utf-8')
            self.assertIn('bb(E)', deck, part.name)


class CrossRefs(unittest.TestCase):
    """図・表・式・節のラベルと参照（crossref.py）。番号は組版が振り、原稿は名前で指す。"""

    SRC = ded("""
        ## はじめに {#sec-intro}

        @sec-analysisで述べる。推移は@fig-trendに、式は[-@eq-model]。

        ![推移](assets/figures/trend.png){#fig-trend}

        ![](assets/figures/bare.png)

        $$
        y = x
        $$

        ## 分析 {#sec-analysis}

        ### 細目 {#sec-detail}

        | a | b |
        |---|---|
        | 1 | 2 |

        : 記述統計 {#tbl-desc}

        : 分析の表 {#tbl-summary}

        $$
        y = a + b x
        $$ {#eq-model}

        ![キャプションだけの図](assets/figures/x.png)

        ## 補足 {.unnumbered}

        ```markdown
        ![見本](assets/figures/code.png){#fig-code}  と @fig-nowhere は数えない
        ```
        """)

    def items(self, **kw):
        return {(i.kind, i.label): i for i in crossref.number(self.SRC, **kw).items}

    def test_numbers_by_section(self):
        got = self.items()
        self.assertEqual(got[('sec', 'sec-intro')].number, '1')
        self.assertEqual(got[('sec', 'sec-detail')].number, '2.1')
        self.assertEqual(got[('fig', 'fig-trend')].number, '1.1')
        # キャプションのない図は数えない。ラベルのないキャプション付きの図は数える
        self.assertEqual(got[('fig', None)].number, '2.1')
        self.assertEqual(got[('tbl', 'tbl-desc')].number, '2.1')
        self.assertEqual(got[('tbl', 'tbl-summary')].number, '2.2')
        self.assertTrue(got[('tbl', 'tbl-summary')].external)     # 中身のないキャプション
        self.assertFalse(got[('tbl', 'tbl-desc')].external)
        # ラベルのない式は数えない
        self.assertEqual(got[('eq', 'eq-model')].number, '2.1')
        self.assertNotIn(('sec', None), got)                      # {.unnumbered}
        self.assertNotIn(('fig', 'fig-code'), got)                # コードの中

    def test_numbers_straight_through(self):
        got = self.items(mode='document')
        self.assertEqual(got[('fig', 'fig-trend')].number, '1')
        self.assertEqual(got[('fig', None)].number, '2')

    def test_appendix_letters(self):
        got = {(i.kind, i.label): i for i in crossref.number(self.SRC, appendix=True).items}
        self.assertEqual(got[('sec', 'sec-analysis')].number, 'B')
        self.assertEqual(got[('tbl', 'tbl-desc')].number, 'B.1')
        self.assertEqual(crossref.text_of(got[('sec', 'sec-analysis')], 'ja'), '付録B')
        self.assertEqual(crossref.text_of(got[('sec', 'sec-analysis')], 'en'), 'Appendix B')

    def test_a_session_deck_keeps_the_handout_number(self):
        got = {i.label: i for i in crossref.number('## 枠\n\n![図](a.png){#fig-a}\n',
                                                   top=1, section=3).items if i.label}
        self.assertEqual(got['fig-a'].number, '3.1')

    def test_references_end_at_japanese_and_skip_code_and_comments(self):
        refs = crossref.references(self.SRC + '\n<!-- @fig-hidden -->\n'
                                   'メール a@fig-x.jp、`@fig-code`\n')
        self.assertEqual([(lab, short) for lab, short, _ in refs],
                         [('sec-analysis', False), ('fig-trend', False), ('eq-model', True)])

    def test_replacement_and_unknown_labels(self):
        known = crossref.number(self.SRC).labels()
        report = []
        out = crossref.replace_references(
            self.SRC + '\n@tbl-nowhere\n', known,
            lambda it, short: crossref.text_of(it, 'ja', short), report)
        self.assertIn('第2節で述べる', out)
        self.assertIn('推移は図1.1に', out)
        self.assertIn('式は(2.1)', out)
        self.assertIn('??', out)
        self.assertIn('@fig-nowhere', out)                       # コードの中は触らない
        self.assertTrue(any('tbl-nowhere' in r for r in report))

    def test_equation_labels_go_inside_the_math(self):
        out = crossref.label_equations('$$\ny = x\n$$ {#eq-m}\n')
        self.assertIn('\\label{eq-m} $$', out)
        tagged = crossref.label_equations('$$ y = x $$ {#eq-m}\n', tag_for=lambda lab: '(2.1)')
        self.assertIn('\\qquad (2.1)', tagged)
        self.assertNotIn('{#eq-m}', tagged)

    def test_crossrefs_are_not_citations(self):
        keys = md.cited_keys('@smith2003 と @fig-trendに、[@tbl-desc] と @eq-model。')
        self.assertEqual(keys, {'smith2003'})

    def test_word_gets_numbers_written_in(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        make_project(d / 'p', docs=(('paper', 'paper'),))
        cfg = config.load(d / 'p' / 'octavo.config.py')
        backend = be.get('docx')
        ctx = Ctx(cfg=cfg, backend=backend, out_dir=d / 'out', profile='paper')
        body, known = build.apply_crossrefs(self.SRC, cfg.document('paper'), backend, ctx)
        self.assertIn('## 1. はじめに {#sec-intro}', body)
        self.assertIn('### 2.1　細目', body)
        self.assertIn('![図1.1　推移]', body)
        self.assertIn(': 表2.1　記述統計 {#tbl-desc}', body)
        self.assertIn('\\qquad (2.1) $$', body)
        self.assertIn('[第2節](#sec-analysis)', body)             # ブックマークへのリンク
        self.assertIn('(2.1)', body)

    def test_labels_and_link_targets_are_not_counted_as_prose(self):
        text = '## 分析 {#sec-analysis}\n\n![推移](../../assets/figures/trend.png){#fig-trend width=80%}\n'
        self.assertEqual(md.char_count(text), len('分析推移'))
        self.assertEqual(md.word_count('## Data {#sec-data}\n\nSee [the site](https://x.org).')[0], 4)

    def test_appendix_labels_resolve_natively_only_when_main_includes_the_appendix(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        root = make_project(d / 'p', docs=(('paper', 'paper'),))
        cfg = config.load(root / 'octavo.config.py')
        doc = cfg.document('paper')
        for target, expect_local in (('typst', False), ('docx', False)):
            backend = be.get(target)
            ctx = Ctx(cfg=cfg, backend=backend, out_dir=d / 'o', profile='paper')
            build.sibling_crossrefs(cfg, doc, backend, ctx, appendix=False)
            self.assertIn('tbl-definitions', ctx.crossrefs)            # 付録のラベルは知っている
            self.assertEqual('tbl-definitions' in ctx.crossref_local, expect_local, target)
        # main.typ の付録の読み込みを有効にすると、組版側が参照を張れる
        main = root / 'papers' / 'paper' / 'main.typ'
        main.write_text(main.read_text(encoding='utf-8').replace(
            '// #include "appendix.typ"', '#include "appendix.typ"'), encoding='utf-8')
        backend = be.get('typst')
        ctx = Ctx(cfg=cfg, backend=backend, out_dir=d / 'o', profile='paper')
        build.sibling_crossrefs(cfg, doc, backend, ctx, appendix=False)
        self.assertIn('tbl-definitions', ctx.crossref_local)
        self.assertEqual(backend.fmt_ref(ctx.crossrefs['tbl-definitions'], False, ctx),
                         '`#ref(<tbl-definitions>)`{=typst}')

    def test_check_reports_missing_duplicate_and_unused(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        root = make_project(d / 'p', docs=(('paper', 'paper'),))
        (root / 'papers' / 'paper' / 'paper.md').write_text(ded("""
            ## はじめに {#sec-intro}

            @fig-nowhere を見る。

            ![A](a.png){#fig-a}

            ![B](b.png){#fig-a}
            """), encoding='utf-8')
        got = crossref.collect(config.load(root / 'octavo.config.py'))
        self.assertEqual([w for _, w in got['missing']], ['@fig-nowhere'])
        self.assertEqual([w for _, w in got['duplicate']], ['#fig-a'])
        in_paper = lambda rows: [w for at, w in rows if at.startswith('papers/paper/paper.md')]
        self.assertEqual(in_paper(got['unused']), ['#fig-a'])


# =====================================================================
@unittest.skipUnless(HAVE_PANDOC, 'pandoc がない')
class EndToEnd(unittest.TestCase):
    """実際に pandoc を呼んで変換する。引用の解決は環境に依存するので外す。"""

    @classmethod
    def setUpClass(cls):
        cls.d = Path(tempfile.mkdtemp())
        make_project(cls.d / 'p', docs=ALL_KINDS)
        cls.cfg = config.load(cls.d / 'p' / 'octavo.config.py')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def build(self, doc, target):
        r = build.build_one(self.cfg, self.cfg.document(doc), target,
                            citations=False, offline=True)
        return r

    def test_latex_body(self):
        r = self.build('paper', 'latex')
        self.assertTrue(r.ok, '\n'.join(r.report))
        # main.tex は既定では作らない。なければ足し方を言う
        self.assertTrue(any('octavo new paper paper --tex' in line for line in r.report),
                        r.report)
        tex = (self.cfg.out_dir('latex', self.cfg.document('paper')) / 'body.tex').read_text(encoding='utf-8')
        self.assertIn(r'\section{はじめに}\label{sec-intro}', tex)
        self.assertIn(r'\includegraphics', tex)
        self.assertIn(r'第\ref{sec-intro}節', tex)
        self.assertIn(r'図\ref{fig-trend}', tex)
        self.assertIn(r'表\ref{tbl-summary}', tex)
        self.assertIn(r'\caption{記述統計}\label{tbl-summary}', tex)   # 分析の表を包む
        self.assertIn(r'\begin{equation}', tex)                         # ラベルのある式
        crossref_tex = (self.cfg.out_dir('latex', self.cfg.document('paper'))
                        / 'crossref.tex').read_text(encoding='utf-8')
        self.assertIn(r'\counterwithin{figure}{section}', crossref_tex)
        self.assertTrue((self.cfg.out_dir('latex', self.cfg.document('paper')) / 'abstract.tex').exists())

    def test_latex_has_no_yaml_leak(self):
        self.build('paper', 'latex')
        tex = (self.cfg.out_dir('latex', self.cfg.document('paper')) / 'body.tex').read_text(encoding='utf-8')
        self.assertNotIn('title:', tex)

    def test_handout_is_standalone(self):
        r = self.build('講義', 'latex')
        self.assertTrue(r.ok, '\n'.join(r.report))
        tex = (self.cfg.out_dir('latex') / '講義.tex').read_text(encoding='utf-8')
        self.assertIn(r'\begin{document}', tex)
        self.assertIn('ltjsarticle', tex)
        self.assertIn('プリントにだけ出る', tex)
        self.assertNotIn('スライドにだけ出る', tex)

    def test_beamer_drops_handout_only(self):
        r = self.build('講義', 'beamer')
        self.assertTrue(r.ok, '\n'.join(r.report))
        tex = (self.cfg.out_dir('beamer') / '講義.tex').read_text(encoding='utf-8')
        self.assertIn(r'\begin{frame}', tex)
        self.assertIn('スライドにだけ出る', tex)
        self.assertNotIn('プリントにだけ出る', tex)

    def test_docx_written(self):
        r = self.build('paper', 'docx')
        self.assertTrue(r.ok, '\n'.join(r.report))
        p = self.cfg.out_dir('docx') / 'paper.docx'
        self.assertTrue(p.exists())
        self.assertGreater(p.stat().st_size, 4000)

    def test_typst_refuses_on_old_pandoc(self):
        r = self.build('paper', 'typst')
        if pandocrun.at_least(3, 1):
            self.assertTrue(r.ok, '\n'.join(r.report))
        else:
            self.assertFalse(r.ok)
            self.assertIn('pandoc 3.1', '\n'.join(r.report))

    def test_typst_citations_are_formatted_by_csl(self):
        # 新しい pandoc は --citeproc でも #cite(<key>) を出す。CSL の書式が
        # 捨てられ、main.typ に書誌がないので typst compile も止まる
        if not pandocrun.at_least(3, 1):
            self.skipTest('pandoc 3.1 以上が要る')
        r = build.build_one(self.cfg, self.cfg.document('paper'), 'typst',
                            citations=True, offline=True)
        self.assertTrue(r.ok, '\n'.join(r.report))
        typ = (self.cfg.out_dir('typst', self.cfg.document('paper')) / 'body.typ').read_text(encoding='utf-8')
        self.assertNotIn('#cite(', typ)
        self.assertIn('2020', typ)

    def test_the_bibliography_heading_is_a_heading(self):
        """`##` で書いた原稿は段を1つ上げて変換する。pandoc が差し込む書誌の見出しにも
        それが効いて0段目（ただの段落）になっていた。"""
        if not pandocrun.at_least(3, 1):
            self.skipTest('pandoc 3.1 以上が要る')
        doc = self.cfg.document('paper')
        title = self.cfg['reference_section_title']
        r = build.build_one(self.cfg, doc, 'typst', citations=True, offline=True)
        self.assertTrue(r.ok, '\n'.join(r.report))
        typ = (self.cfg.out_dir('typst', doc) / 'body.typ').read_text(encoding='utf-8')
        self.assertIn(f'#heading(level: 1, numbering: none)[{title}]', typ)
        self.assertNotIn(f'\n{title}\n', typ)
        r = build.build_one(self.cfg, doc, 'latex', citations=True, offline=True)
        tex = (self.cfg.out_dir('latex', doc) / 'body.tex').read_text(encoding='utf-8')
        self.assertIn(f'\\section*{{{title}}}', tex)

    @unittest.skipUnless(shutil.which('typst'), 'typst がない')
    def test_typst_compiles_to_pdf(self):
        if not pandocrun.at_least(3, 1):
            self.skipTest('pandoc 3.1 以上が要る')
        for doc, target in (('paper', 'typst'),          # main.typ 方式
                            ('講義', 'typst'),           # 完結した文書
                            ('講義', 'typst-slides'),
                            ('講義-02', 'typst-slides'),  # 講義ノートを分けた1回分
                            ('slides', 'typst-slides')):
            r = build.build_one(self.cfg, self.cfg.document(doc), target,
                                citations=True, offline=True, do_compile=True)
            self.assertTrue(r.ok, '\n'.join(r.report))
            self.assertIsNotNone(r.compiled, '\n'.join(r.report))
            self.assertTrue(r.compiled.exists())

    def test_example_marks_never_reach_the_output(self):
        # ひな型の印は HTML コメントなので、組版には1つも出てはいけない
        # （閉じの印を段落に続けて書くと、キャプションに文字列として入る）
        for doc, target in (('paper', 'typst'), ('paper', 'latex'),
                            ('slides', 'typst-slides'), ('講義', 'typst')):
            r = build.build_one(self.cfg, self.cfg.document(doc), target,
                                citations=False, offline=True)
            self.assertTrue(r.ok, '\n'.join(r.report))
            for out in self.cfg.out_dir(target, self.cfg.document(doc)).glob('*'):
                if out.suffix in ('.typ', '.tex'):
                    self.assertNotIn('octavo:example',
                                     out.read_text(encoding='utf-8'),
                                     f'{doc} -> {target}: {out.name}')

    def test_an_uncaptioned_figure_path_is_rebased(self):
        # キャプションのない図は fmt_figure を通らないので、rebase_links が
        # 直していないと `../assets/figures/…` のまま出て組版が落ちる
        doc = self.cfg.document('slides')
        original = doc.src.read_text(encoding='utf-8')
        self.addCleanup(doc.src.write_text, original, encoding='utf-8')
        doc.src.write_text('---\ntitle: 図\n---\n\n## 図だけ\n\n'
                           '![](../assets/figures/trend.png)\n', encoding='utf-8')
        r = build.build_one(self.cfg, doc, 'typst-slides',
                            citations=False, offline=True)
        self.assertTrue(r.ok, '\n'.join(r.report))
        typ = (self.cfg.out_dir('typst-slides', doc)
               / 'slides.typ').read_text(encoding='utf-8')
        self.assertIn('../../assets/figures/trend.pdf', typ)     # Typst は .pdf（ベクター）
        self.assertNotIn('"../assets/figures/', typ)
        # 素通りしていたときは check が「OK」と言ってしまっていた
        self.assertFalse(any('not reachable from the output' in line for line in r.report),
                         '\n'.join(r.report))

    def test_a_path_that_resolves_nowhere_is_reported(self):
        doc = self.cfg.document('slides')
        original = doc.src.read_text(encoding='utf-8')
        self.addCleanup(doc.src.write_text, original, encoding='utf-8')
        doc.src.write_text('---\ntitle: 図\n---\n\n## 図だけ\n\n'
                           '![](../assets/figures/typo/trend.png)\n', encoding='utf-8')
        r = build.build_one(self.cfg, doc, 'typst-slides',
                            citations=False, offline=True)
        self.assertTrue(any('not reachable from the output' in line for line in r.report),
                        '\n'.join(r.report))

    def test_japanese_after_a_crossref_survives(self):
        # Typst の `@label` は非 ASCII が続く限りラベル名が伸びるので、
        # 「図1に示す」が `<fig:trendに示す>` になって組版が止まっていた。
        # 日本語では参照の直後に助詞が来るのがふつう。
        if not pandocrun.at_least(3, 1):
            self.skipTest('pandoc 3.1 以上が要る')
        src = self.cfg.document('paper').src
        original = src.read_text(encoding='utf-8')
        self.addCleanup(src.write_text, original, encoding='utf-8')
        src.write_text(
            '## Abstract\n\n要旨。\n\n'
            '## はじめに {#sec-intro}\n\n本文。\n\n'
            '## 分析\n\n@sec-introで述べたとおり、推移を@fig-trendに示す。\n\n'
            '![推移](../../assets/figures/trend.png){#fig-trend}\n',
            encoding='utf-8')
        r = build.build_one(self.cfg, self.cfg.document('paper'), 'typst',
                            citations=False, offline=True)
        self.assertTrue(r.ok, '\n'.join(r.report))
        typ = (self.cfg.out_dir('typst', self.cfg.document('paper'))
               / 'body.typ').read_text(encoding='utf-8')
        self.assertIn('#ref(<sec-intro>)で述べたとおり', typ)
        self.assertIn('#ref(<fig-trend>)に示す', typ)

    @unittest.skipUnless(shutil.which('typst'), 'typst がない')
    def test_a_crossref_followed_by_japanese_compiles(self):
        if not pandocrun.at_least(3, 1):
            self.skipTest('pandoc 3.1 以上が要る')
        self.test_japanese_after_a_crossref_survives()
        r = build.build_one(self.cfg, self.cfg.document('paper'), 'typst',
                            citations=False, offline=True, do_compile=True)
        self.assertTrue(r.ok, '\n'.join(r.report))
        self.assertTrue(r.compiled.exists())

    def test_a_fresh_paper_bundles_without_gaps(self):
        if not pandocrun.at_least(3, 1):
            self.skipTest('pandoc 3.1 以上が要る')
        doc = self.cfg.document('paper')
        r = build.build_one(self.cfg, doc, 'typst', citations=False, offline=True)
        self.assertTrue(r.ok, '\n'.join(r.report))
        res = bundle.collect(self.cfg, 'typst', self.d / 'sub', doc)
        self.assertTrue(res.ok, '\n'.join(res.report))
        self.assertLessEqual({'main.typ', 'body.typ', 'trend.pdf'},
                             {p.name for p in res.files})

    def test_a_session_deck_has_its_own_title(self):
        if not pandocrun.at_least(3, 1):
            self.skipTest('pandoc 3.1 以上が要る')
        r = self.build('講義-02', 'typst-slides')
        self.assertTrue(r.ok, '\n'.join(r.report))
        typ = (self.cfg.out_dir('typst-slides') / '講義-slides-02.typ').read_text(encoding='utf-8')
        self.assertIn('title: [第2回 タイトル（見本）]', typ)
        self.assertIn('subtitle: [講義の見本]', typ)
        self.assertIn('具体例', typ)
        self.assertNotIn('今日の狙い', typ)                 # 1回目の中身は入らない

    def test_missing_source_is_reported_not_raised(self):
        doc = config.Document('nope', self.d / 'nope.md')
        r = build.build_one(self.cfg, doc, 'latex', citations=False, offline=True)
        self.assertFalse(r.ok)
        self.assertIn('no manuscript at', '\n'.join(r.report))




class StaleRPackages(unittest.TestCase):
    """R を上げたあとに残る、古い R 向けのパッケージ（doctor が知らせる）。"""

    def test_the_r_output_is_read_per_library(self):
        out = ('/usr/local/lib/R/site-library\t51\t4.3\tFALSE\n'
               'Warning: something R said\n'
               '/usr/lib/R/library\t13\t4.2,4.3\tFALSE\n')
        with unittest.mock.patch('shutil.which', return_value='/usr/bin/Rscript'), \
                unittest.mock.patch.object(doctor, '_run', return_value=(0, out)) as run:
            rows = doctor.stale_r_libraries()
        self.assertIn('--vanilla', run.call_args[0][0])     # renv のプロジェクトの中でも R 本体を見る
        self.assertEqual(rows, [('/usr/local/lib/R/site-library', 51, '4.3', False),
                                ('/usr/lib/R/library', 13, '4.2,4.3', False)])
        with unittest.mock.patch('shutil.which', return_value=None):
            self.assertEqual(doctor.stale_r_libraries(), [])

    def test_the_rebuild_command_fits_the_library(self):
        with unittest.mock.patch('platform.system', return_value='Linux'):
            self.assertEqual(doctor.rebuild_command('/usr/lib/R/library', False), 'sudo apt upgrade')
            cmd = doctor.rebuild_command('/usr/local/lib/R/site-library', False)
            self.assertTrue(cmd.startswith('sudo Rscript -e "update.packages('), cmd)
            self.assertIn("lib.loc='/usr/local/lib/R/site-library', checkBuilt=TRUE", cmd)
            self.assertFalse(doctor.rebuild_command('/home/u/R/lib', True).startswith('sudo'))
        with unittest.mock.patch('platform.system', return_value='Windows'):
            self.assertFalse(doctor.rebuild_command('C:/R/library', False).startswith('sudo'))

    def test_doctor_says_how_to_rebuild_but_the_extension_is_not_asked_to_set_up(self):
        stale = [('/usr/local/lib/R/site-library', 51, '4.3', False)]
        with unittest.mock.patch.object(doctor, 'stale_r_libraries', return_value=stale), \
                unittest.mock.patch.dict(os.environ, {'OCTAVO_LANG': 'en'}):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                doctor.report()
            out = buf.getvalue()
            data = doctor.as_json()
        if shutil.which('Rscript'):
            self.assertIn('51 packages built for an older R (4.3) do not load', out)
            self.assertIn("update.packages(lib.loc='/usr/local/lib/R/site-library'", out)
            self.assertFalse(data['tools']['r_packages']['ok'])
        # 「セットアップ」では直らないので、拡張機能が見る analysis には入れない
        self.assertNotIn('r_packages', data['analysis'])


class MacOS(unittest.TestCase):
    """Mac 向けの出し分け。手元に Mac はないので、ここでは platform を差し替えて見る
    （実機に近い確認は CI の macos ジョブが Homebrew で入れて組むところまでやる）。"""

    def test_hints_are_homebrew_on_macos(self):
        from octavo import doctor
        with unittest.mock.patch('platform.system', return_value='Darwin'):
            self.assertTrue(doctor.is_macos())
            self.assertEqual(doctor.hint('pandoc'), 'brew install pandoc')
            self.assertIn('brew', doctor.hint('typst_default_fonts'))
            # Mac 用がないものは共通の案内
            with unittest.mock.patch.dict(doctor.HINTS, {'common-only': 'same everywhere'}):
                self.assertEqual(doctor.hint('common-only'), 'same everywhere')
        with unittest.mock.patch('platform.system', return_value='Linux'):
            self.assertIn('apt', doctor.hint('pandoc'))

    def test_no_apt_line_reaches_a_mac(self):
        """Mac 用の案内が抜けていると apt の行が Mac の人に出る。"""
        from octavo import doctor
        with unittest.mock.patch('platform.system', return_value='Darwin'):
            for key in doctor.HINTS:
                self.assertNotIn('apt ', doctor.hint(key), key)

    def test_the_mac_hints_name_real_keys(self):
        from octavo import doctor
        self.assertEqual(set(doctor.HINTS_MACOS) - set(doctor.HINTS), set())

    def test_doctor_runs_as_if_on_a_mac_without_fontconfig(self):
        from octavo import doctor
        real_which = shutil.which
        with unittest.mock.patch('platform.system', return_value='Darwin'), \
                unittest.mock.patch('platform.mac_ver', return_value=('15.4', ('', '', ''), '')), \
                unittest.mock.patch('shutil.which',
                                    side_effect=lambda n: None if n == 'fc-list' else real_which(n)):
            f = doctor.collect()
            self.assertEqual(f['wsl'][1], 'macOS 15.4')
            self.assertTrue(f['cjkfonts'][0])
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                doctor.report()
            self.assertNotIn('apt ', out.getvalue())

    def test_setup_sh_has_a_homebrew_path(self):
        text = (ROOT / 'setup.sh').read_text(encoding='utf-8')
        self.assertIn('Darwin', text)
        for pkg in ('pandoc', 'typst', 'quarto', 'font-biz-udmincho', 'mactex-no-gui'):
            self.assertIn(pkg, text)
        # Windows の bash は WSL の起動用（System32\\bash.exe）のことがあり、WSL が
        # ないと黙って失敗する。構文は Linux と macOS の CI が見る
        if shutil.which('bash') and os.name != 'nt':
            r = subprocess.run(['bash', '-n', str(ROOT / 'setup.sh')],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)



class ToolSetup(unittest.TestCase):
    """道具を入れる入口（setup.sh / octavo setup / 拡張機能の「セットアップ」）。

    apt や sudo を実際に実行するテストはない。setup.sh を拡張機能と同じ置き方
    （clone の外）で実行する確認は、apt と sudo を差し替えて手で行っている。
    """
    SETUP = ROOT / 'setup.sh'
    EXT = ROOT / 'vscode-extension'

    def test_setup_sh_parses_and_knows_its_flags(self):
        text = self.SETUP.read_text(encoding='utf-8')
        for flag in ('--octavo-version', '--no-r', '--no-quarto', '--with-tex', '--check'):
            self.assertIn(flag, text)
        self.assertRegex(text, r'\nUV_VER="\d+\.\d+\.\d+"')
        self.assertIn('uv tool install --force "octavo-kit', text)
        self.assertIn('cloud.r-project.org/bin/linux/ubuntu', text)
        self.assertIn('packagemanager.posit.co', text)
        self.assertIn('brew_one --cask r', text)
        if os.name != 'nt':            # Windows の bash は WSL の起動用のことがある
            r = subprocess.run(['bash', '-n', str(self.SETUP)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)

    @unittest.skipIf(os.name == 'nt', 'bash が WSL の起動用のことがある')
    def test_a_stale_clone_is_left_alone_but_named(self):
        """clone へのリンクは入れ替えない。古ければ git pull を案内する（黙っていると、
        拡張機能が「古い」と言い続けるのに「セットアップ」を押しても何も変わらない）。"""
        with tempfile.TemporaryDirectory() as d:
            # setup.sh はリンクを解決した先を出す（macOS の /var は /private/var）
            d = Path(d).resolve()
            home, clone = d / 'home', d / 'clone'
            (home / '.local' / 'bin').mkdir(parents=True)
            (clone / 'bin').mkdir(parents=True)
            (clone / 'octavo').mkdir()
            (clone / 'setup.sh').write_text('', encoding='utf-8')
            fake = clone / 'bin' / 'octavo'
            fake.write_text('#!/bin/sh\necho "octavo 0.1.0"\n', encoding='utf-8')
            fake.chmod(0o755)
            (home / '.local' / 'bin' / 'octavo').symlink_to(fake)
            script = d / 'setup.sh'                    # clone の外から実行する
            shutil.copy(self.SETUP, script)
            env = dict(os.environ, HOME=str(home), OCTAVO_LANG='en')

            def run(version):
                return subprocess.run(['bash', str(script), '--check', '--octavo-version', version],
                                      capture_output=True, text=True, encoding='utf-8',
                                      env=env, timeout=120).stdout

            out = run('0.2.0')
            self.assertIn('left alone, it points at a clone', out)
            self.assertIn('older than 0.2.0', out)
            self.assertIn(f'git -C "{clone}" pull', out)
            self.assertNotIn('uv tool install', out)
            self.assertNotIn('older than', run('0.1.0'))

    def test_doctor_json_says_whether_it_runs_from_a_clone(self):
        with unittest.mock.patch.object(paths, 'is_clone', return_value=True):
            self.assertEqual(doctor.as_json()['clone'], str(paths.REPO))
        with unittest.mock.patch.object(paths, 'is_clone', return_value=False):
            self.assertIsNone(doctor.as_json()['clone'])

    def test_every_message_is_in_both_languages(self):
        """拡張機能から英語の人も実行するので、say / msg は必ず2言語で書く。"""
        for n, line in enumerate(self.SETUP.read_text(encoding='utf-8').splitlines(), 1):
            s = line.strip()
            if re.match(r'(say|msg) ', s):
                self.assertTrue(s.endswith('\\') or re.search(r'"\s+"', s),
                                f'setup.sh:{n}: 片方の言語しかない: {s}')

    def test_cli_setup_passes_the_flags_and_the_version(self):
        from octavo import cli
        args = cli.make_parser().parse_args(['setup', '--no-r', '--check'])
        with unittest.mock.patch('subprocess.call', return_value=0) as call, \
                unittest.mock.patch.object(paths, 'on_windows', return_value=False), \
                unittest.mock.patch.object(paths, 'is_clone', return_value=False):
            self.assertEqual(cli.cmd_setup(args), 0)
        cmd = call.call_args[0][0]
        self.assertEqual(cmd[0], 'bash')
        self.assertEqual(Path(cmd[1]).name, 'setup.sh')
        self.assertIn('--no-r', cmd)
        self.assertIn('--check', cmd)
        self.assertEqual(cmd[cmd.index('--octavo-version') + 1], octavo.__version__)
        # clone からなら版を渡さない（setup.sh はリンクを張る）
        with unittest.mock.patch('subprocess.call', return_value=0) as call, \
                unittest.mock.patch.object(paths, 'on_windows', return_value=False):
            cli.cmd_setup(cli.make_parser().parse_args(['setup']))
        self.assertNotIn('--octavo-version', call.call_args[0][0])

    def test_the_wheel_carries_setup_sh(self):
        text = (ROOT / 'pyproject.toml').read_text(encoding='utf-8')
        self.assertIn('"setup.sh" = "octavo/setup.sh"', text)
        # wheel の中の setup.sh があっても clone 扱いにはしない（CSL を site-packages に書かない）
        with tempfile.TemporaryDirectory() as tmp:
            with unittest.mock.patch.object(paths, 'REPO', Path(tmp)):
                self.assertFalse(paths.is_clone())
                self.assertNotEqual(paths.csl_cache_dir().parent, paths.PKG)

    def test_the_extension_ships_the_same_setup_sh(self):
        pkg = json.loads((self.EXT / 'package.json').read_text(encoding='utf-8'))
        self.assertIn('copy-setup.mjs', pkg['scripts']['assets'])
        copy = (self.EXT / 'scripts' / 'copy-setup.mjs').read_text(encoding='utf-8')
        self.assertIn("['setup.sh', 'setup.ps1']", copy)
        self.assertIn("join(root, '..', name)", copy)
        self.assertIn("asAbsolutePath('setup')", (self.EXT / 'src' / 'setup.ts').read_text(encoding='utf-8'))
        runner = (self.EXT / 'src' / 'runner.ts').read_text(encoding='utf-8')
        self.assertIn("path.join(dir, 'setup.sh')", runner)
        self.assertIn("path.join(dir, 'setup.ps1')", runner)
        ignore = (self.EXT / '.vscodeignore').read_text(encoding='utf-8').split()
        self.assertFalse(any(p.startswith('setup') for p in ignore), '.vsix から setup/ が落ちる')
        for cmd in ('octavo.setup', 'octavo.envSetup'):
            self.assertIn(cmd, [c['command'] for c in pkg['contributes']['commands']])

    def test_setup_ps1_matches_setup_sh(self):
        """Windows 用は別のスクリプトだが、版と入れるものは setup.sh とそろえる。"""
        raw = (ROOT / 'setup.ps1').read_bytes()
        # BOM がないと Windows PowerShell 5.1 が日本語を読み違える
        self.assertTrue(raw.startswith(b'\xef\xbb\xbf'), 'setup.ps1 に BOM がない')
        ps1 = raw.decode('utf-8-sig')
        sh = self.SETUP.read_text(encoding='utf-8')
        for var in ('PANDOC_VER', 'TYPST_VER', 'QUARTO_VER', 'UV_VER'):
            v_sh = re.search(r'\n%s="([^"]+)"' % var, sh).group(1)
            v_ps = re.search(r"\n\$%s = '([^']+)'" % var, ps1).group(1)
            self.assertEqual(v_sh, v_ps, var)
        for pkg in ('JohnMacFarlane.Pandoc', 'Typst.Typst', 'Posit.Quarto', 'RProject.R',
                    'uv tool install --force', 'BIZUDMincho', 'BIZUDGothic', 'Inter'):
            self.assertIn(pkg, ps1)
        for flag in ('NoQuarto', 'NoR', 'OctavoVersion', 'Check'):
            self.assertIn('$' + flag, ps1)
        # 表示は2言語（Say / Info は日本語と英語を1つずつ取る）
        for n, line in enumerate(ps1.splitlines(), 1):
            s = line.strip()
            if re.match(r'(Say|Info) ', s):
                self.assertTrue(s.endswith('`') or re.search(r"""['"]\s+['"]""", s),
                                f'setup.ps1:{n}: 片方の言語しかない: {s}')

    def test_setup_sh_checks_r_packages_the_same_way_as_doctor(self):
        text = self.SETUP.read_text(encoding='utf-8')
        m = re.search(r"R_STALE='(.*?)'\n", text, re.S)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1).strip(), doctor.R_STALE.strip())

    def test_the_setup_scripts_install_languageserver_the_same_way(self):
        """VS Code の R 拡張機能用の languageserver は、setup.sh・setup.ps1・octavo setup --r-editor
        が同じ R のコードで、依存ごと利用者のライブラリに入れる。"""
        code = envsetup.R_EDITOR_SCRIPT.strip()
        sh = (ROOT / 'setup.sh').read_text(encoding='utf-8')
        m = re.search(r"R_EDITOR='(.*?)'\n", sh, re.S)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1).strip(), code)
        ps = (ROOT / 'setup.ps1').read_text(encoding='utf-8-sig')
        m = re.search(r"octavo-r-editor\.R'\n.*?@'\n(.*?)\n'@", ps, re.S)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1).strip(), code)
        self.assertIn('include.site = FALSE', code)       # renv と同じ見え方で確かめる
        self.assertIn('package_dependencies', code)       # 依存ごと（サイトライブラリは見えない）

    @unittest.skipIf(os.name == 'nt', 'bash が WSL の起動用のことがある')
    def test_setup_sh_names_the_rebuild_for_packages_of_an_older_r(self):
        """R を上げたあとに残った古い R 向けのパッケージは、入れ直すコマンドを言う。"""
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            fake = d / 'bin' / 'Rscript'
            fake.parent.mkdir()
            fake.write_text('#!/bin/sh\n'
                            'if [ "$1" = --vanilla ]; then\n'
                            '  printf "/usr/local/lib/R/site-library\\t51\\t4.3\\tFALSE\\n"\n'
                            '  printf "/home/u/R/lib\\t2\\t4.3\\tTRUE\\n"\n'
                            '  printf "/usr/lib/R/library\\t13\\t4.3\\tFALSE\\n"\n'
                            'else echo "Rscript (R) version 4.6.1"; fi\n', encoding='utf-8')
            fake.chmod(0o755)
            env = dict(os.environ, OCTAVO_LANG='en',
                       PATH=f'{fake.parent}{os.pathsep}{os.environ["PATH"]}')
            out = subprocess.run(['bash', str(self.SETUP), '--check', '--no-quarto'],
                                 capture_output=True, text=True, encoding='utf-8',
                                 env=env, timeout=120).stdout
            self.assertIn('built for an older R (4.3) do not load', out)
            self.assertIn("update.packages(lib.loc='/usr/local/lib/R/site-library'", out)
            self.assertIn('Rscript -e "update.packages(lib.loc=\'/home/u/R/lib\'', out)
            self.assertNotIn("sudo Rscript -e \"update.packages(lib.loc='/home/u/R/lib'", out)
            # apt の案内は Linux だけ（2つのライブラリで1回）
            self.assertEqual(out.count('sudo apt upgrade'),
                             1 if platform.system() == 'Linux' else 0)

    def test_no_variable_runs_into_japanese(self):
        """「$name）」は macOS の bash 3.2 が「name）」という変数に読み、set -u で止まる
        （brew の取得に失敗したとき、その失敗を知らせる行で落ちていた）。PowerShell も
        かなを変数名に含める。日本語の直前の変数は ${name} と書く。"""
        pat = re.compile(r'\$[A-Za-z_][A-Za-z0-9_]*[^\x00-\x7F]')
        for name in ('setup.sh', 'setup.ps1'):
            text = (ROOT / name).read_text(encoding='utf-8-sig')
            bad = [line.strip() for line in text.splitlines() if pat.search(line)]
            self.assertEqual(bad, [], name)

    @unittest.skipUnless(shutil.which('pwsh'), 'PowerShell がない')
    def test_setup_ps1_parses(self):
        script = ('$e=$null; [void][System.Management.Automation.Language.Parser]::ParseFile('
                  f"'{ROOT / 'setup.ps1'}',[ref]$null,[ref]$e); if ($e) {{ $e; exit 1 }}")
        r = subprocess.run(['pwsh', '-NoProfile', '-Command', script],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_cli_setup_on_windows_runs_the_powershell_one(self):
        from octavo import cli
        args = cli.make_parser().parse_args(['setup', '--no-quarto', '--check'])
        with unittest.mock.patch.object(paths, 'on_windows', return_value=True), \
                unittest.mock.patch.object(paths, 'is_clone', return_value=False), \
                unittest.mock.patch('subprocess.call', return_value=0) as call:
            self.assertEqual(cli.cmd_setup(args), 0)
        cmd = call.call_args[0][0]
        self.assertEqual(cmd[0], 'powershell')
        self.assertEqual(Path(cmd[cmd.index('-File') + 1]).name, 'setup.ps1')
        self.assertIn('-NoQuarto', cmd)
        self.assertIn('-Check', cmd)
        self.assertEqual(cmd[cmd.index('-OctavoVersion') + 1], octavo.__version__)
        # TeX は Windows では入れない（言うだけ）
        with unittest.mock.patch.object(paths, 'on_windows', return_value=True), \
                self.assertRaises(SystemExit):
            cli.cmd_setup(cli.make_parser().parse_args(['setup', '--with-tex']))

    @unittest.skipUnless(shutil.which('apt-get') and shutil.which('sudo'),
                         'apt のない環境（setup.sh --check は apt の道を見る）')
    def test_check_mode_changes_nothing(self):
        r = subprocess.run(['bash', str(self.SETUP), '--check', '--no-r'],
                           capture_output=True, text=True, timeout=300,
                           env={**os.environ, 'OCTAVO_LANG': 'en'})
        self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])
        self.assertIn('(not run) sudo apt-get install', r.stdout)


class ProjectEnv(unittest.TestCase):
    """`octavo env`。uv と Rscript は、呼ばれた引数を書き残すだけの代役に差し替える。"""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.root = make_project(self.d / 'p', lang='en')
        self.cfg = config.load(str(self.root / 'octavo.config.py'))
        self.bin = self.d / 'bin'
        self.bin.mkdir()
        self.log = self.d / 'calls.log'

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def fake(self, *names):
        for n in names:
            f = self.bin / n
            f.write_text('#!/bin/sh\n'
                         f'printf "%s " {n} "$@" >> "{self.log}"\n'
                         f'echo >> "{self.log}"\n'
                         # Rscript にはファイルで渡すので、その中身も残す
                         + (f'/bin/cat "$1" >> "{self.log}"\n' if n == 'Rscript' else ''),
                         encoding='utf-8')
            f.chmod(0o755)

    def run_env(self) -> int:
        # 本物の uv / Rscript が見えないように、代役のフォルダだけにする
        env = {**os.environ, 'PATH': str(self.bin)}
        with unittest.mock.patch.dict(os.environ, env, clear=True), \
                contextlib.redirect_stdout(io.StringIO()):
            return envsetup.run(self.cfg)

    def calls(self) -> list:
        return self.log.read_text(encoding='utf-8').splitlines() if self.log.exists() else []

    @unittest.skipIf(os.name == 'nt', 'sh の代役を使う')
    def test_venv_then_renv(self):
        self.fake('uv', 'Rscript')
        self.assertEqual(self.run_env(), 0)
        calls = self.calls()
        self.assertTrue(calls[0].startswith('uv venv '), calls)
        # ひな型の requirements.txt はコメントだけなので、入れるものはない
        self.assertFalse(any(' pip install ' in c for c in calls), calls)
        r = self.log.read_text(encoding='utf-8').split('Rscript ', 1)[1]
        for s in ('renv::init(', 'renv::restore(', '"knitr"', '"rmarkdown"', 'renv::snapshot('):
            self.assertIn(s, r)

    @unittest.skipIf(os.name == 'nt', 'sh の代役を使う')
    def test_requirements_are_installed_into_the_venv(self):
        self.fake('uv')
        with open(self.root / 'requirements.txt', 'a', encoding='utf-8') as fh:
            fh.write('pandas==2.3.1\n')
        (self.root / '.venv').mkdir()
        self.assertEqual(self.run_env(), 0)
        self.assertEqual([c.split()[:4] for c in self.calls()],
                         [['uv', 'pip', 'install', '-r']])

    def test_nothing_to_do_it_with(self):
        self.assertEqual(self.run_env(), 1)

    def test_requirements_with_only_comments_list_nothing(self):
        self.assertFalse(envsetup.has_requirements(self.root / 'requirements.txt'))
        self.assertFalse(envsetup.has_requirements(self.root / 'nope.txt'))

    def test_the_analysis_runs_with_the_project_venv(self):
        self.assertNotIn('QUARTO_PYTHON', analysis._env(self.cfg))
        py = analysis.venv_python(self.root / '.venv')    # Windows は Scripts\\python.exe
        py.parent.mkdir(parents=True)
        py.write_text('', encoding='utf-8')
        with unittest.mock.patch.dict(os.environ):
            os.environ.pop('QUARTO_PYTHON', None)
            # macOS の一時フォルダは /var -> /private/var のリンクなので、実体で比べる
            self.assertEqual(Path(analysis._env(self.cfg)['QUARTO_PYTHON']).resolve(),
                             py.resolve())


def names(paths) -> list:
    return [p.name for p in paths]


class TypstFigures(unittest.TestCase):
    """figures/<name>.typ（Typst で描く図）を octavo build が .pdf と .png にする。"""

    def setUp(self):
        from octavo import diagrams
        self.diagrams = diagrams
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / 'proj'
        make_project(self.root, docs=(('paper', 'mypaper'),), analysis=False)
        self.cfg = config.load(self.root / 'octavo.config.py')
        self.figs = self.root / 'figures'                  # 手で書く .typ
        self.out = self.root / 'assets' / 'figures'        # 組んだ .pdf / .png

    def tearDown(self):
        self.tmp.cleanup()

    def new_figure(self, name='dag', **kw):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return scaffold.new(self.root / 'octavo.config.py', 'figure', name, **kw)

    def test_new_figure_writes_a_typ_that_needs_drawing(self):
        self.assertEqual(self.new_figure('dag.typ'), 0)        # 拡張子は付けても付けなくても
        src = self.figs / 'dag.typ'
        text = src.read_text(encoding='utf-8')
        self.assertNotIn('@@', text)
        self.assertIn('#fig-dag', text)
        self.assertIn('#let diagram(', text)
        # 設定のパスは実体に解決される（macOS の /var -> /private/var など）ので名前で比べる
        self.assertEqual(names(self.diagrams.stale(self.cfg)), ['dag.typ'])
        # 見本の部分には印があり、octavo check が「ひな型の残り」として数える
        marks = [lo.file for lo in lint.leftovers(self.cfg)]
        self.assertIn('figures/dag.typ', marks)

    def test_an_english_project_gets_the_english_template(self):
        d = Path(self.tmp.name) / 'en'
        make_project(d, docs=(), lang='en', analysis=False)
        with contextlib.redirect_stdout(io.StringIO()):
            scaffold.new(d / 'octavo.config.py', 'figure', 'flow')
        text = (d / 'figures' / 'flow.typ').read_text(encoding='utf-8')
        self.assertNotIn('@@', text)
        self.assertNotRegex(text, r'[぀-ヿ]')
        self.assertIn('"Inter"', text)                 # 英語の文書の書体の並び

    def test_a_figure_from_the_analysis_is_not_overwritten(self):
        self.out.mkdir(parents=True, exist_ok=True)
        (self.out / 'trend.png').write_bytes(b'png')
        self.assertEqual(self.new_figure('trend'), 1)
        self.assertFalse((self.figs / 'trend.typ').exists())

    def test_staleness_and_shared_parts(self):
        self.figs.mkdir(exist_ok=True)
        src = self.figs / 'a.typ'
        src.write_text('x', encoding='utf-8')
        parts = self.figs / '_parts.typ'
        parts.write_text('#let y = 1', encoding='utf-8')
        self.assertEqual(names(self.diagrams.sources(self.cfg)), ['a.typ'])   # _ で始まるものは組まない
        for out in self.diagrams.outputs(self.cfg, src):
            out.write_bytes(b'drawn')
        future = time.time() + 5
        for out in self.diagrams.outputs(self.cfg, src):
            os.utime(out, (future, future))
        self.assertEqual(self.diagrams.stale(self.cfg), [])
        later = future + 5
        os.utime(parts, (later, later))                  # 共通の部品が変わったら組み直す
        self.assertEqual(names(self.diagrams.stale(self.cfg)), ['a.typ'])

    def test_without_typst_it_warns_and_goes_on(self):
        self.new_figure()
        report: list = []
        with unittest.mock.patch('shutil.which', return_value=None):
            self.assertTrue(self.diagrams.run(self.cfg, report))
        self.assertIn('figures/dag.typ', ' '.join(report))
        self.assertFalse((self.out / 'dag.png').exists())

    def test_check_reports_figures_not_drawn(self):
        self.new_figure()
        items = {i.label: i for i in audit.collect(self.cfg)}
        self.assertFalse(items['figures drawn in Typst'].ok)
        self.assertFalse(items['figures drawn in Typst'].fatal)

    def test_no_row_without_typst_figures(self):
        labels = [i.label for i in audit.collect(self.cfg)]
        self.assertNotIn('figures drawn in Typst', labels)

    @unittest.skipUnless(shutil.which('typst'), 'needs typst')
    def test_draws_pdf_and_png_and_stops_on_an_error(self):
        self.new_figure()
        report: list = []
        self.assertTrue(self.diagrams.run(self.cfg, report), report)
        self.assertEqual((self.out / 'dag.pdf').read_bytes()[:5], b'%PDF-')
        self.assertEqual((self.out / 'dag.png').read_bytes()[:4], b'\x89PNG')
        self.assertEqual(self.diagrams.stale(self.cfg), [])
        (self.figs / 'broken.typ').write_text('#undefined-thing\n', encoding='utf-8')
        report = []
        self.assertFalse(self.diagrams.run(self.cfg, report))
        self.assertIn('figures/broken.typ', report[0])
        self.assertIn('undefined-thing', '\n'.join(report))

    def test_code_in_a_raw_block_is_not_a_citation(self):
        """```{=typst} の `#import "@preview/…"` を引用キーと数えない。"""
        text = ('Text [@smith2003].\n\n```{=typst}\n#import "@preview/cetz:0.4.2"\n```\n\n'
              '```r\nemail <- "a@b"\n```\n')
        self.assertEqual(md.cited_keys(text), {'smith2003'})


class HandTables(unittest.TestCase):
    """tables/<name>.csv（手で作る表）を octavo build が assets/tables/ の3形式にする。"""

    def setUp(self):
        from octavo import handtables
        self.ht = handtables
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / 'proj'
        make_project(self.root, docs=(('paper', 'mypaper'),), analysis=False)
        self.cfg = config.load(self.root / 'octavo.config.py')
        self.src = self.root / 'tables'
        self.out = self.root / 'assets' / 'tables'

    def tearDown(self):
        self.tmp.cleanup()

    def new_table(self, name='compare', **kw):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return scaffold.new(self.root / 'octavo.config.py', 'table', name, **kw)

    def write(self, name, text, encoding='utf-8'):
        self.src.mkdir(exist_ok=True)
        (self.src / f'{name}.csv').write_bytes(text.encode(encoding))

    GROUPED = ',2020年,,2024年,\n地域,人数,割合,人数,割合\n北部,120,0.31,135,0.33\n'

    def test_merged_headings_make_two_heading_rows(self):
        tb = self.ht.parse(self.GROUPED)
        self.assertEqual((tb.head, tb.spans), (2, {1: 2, 3: 2}))
        self.assertEqual(tb.align, ['l', 'r', 'r', 'r', 'r'])
        typ = self.ht.to_typst(tb, 'tables/x.csv')
        self.assertIn('table.cell(colspan: 2, align: center, strong("2020年"))', typ)
        self.assertIn('table.hline(start: 3, end: 5, stroke: 0.5pt)', typ)
        tex = self.ht.to_latex(tb, 'tables/x.csv')
        self.assertIn(r'\multicolumn{2}{c}{\textbf{2024年}}', tex)
        self.assertIn(r'\cmidrule(lr){2-3} \cmidrule(lr){4-5}', tex)
        # Word（パイプ表）は結合できないので、見出しを1行にまとめる
        self.assertIn('| 地域 | 2020年 人数 | 2020年 割合 |', self.ht.to_markdown(tb, 'x'))

    def test_a_label_over_an_empty_cell_moves_down(self):
        """Excel で縦に結合した「地域」は、CSV では1行目にあり2行目が空になる。"""
        tb = self.ht.parse('地域,2020年,\n,人数,割合\n北部,1,2\n')
        self.assertEqual(tb.head, 2)
        self.assertEqual(tb.rows[:2], [['', '2020年', ''], ['地域', '人数', '割合']])

    def test_plain_tables_and_ragged_csv(self):
        tb = self.ht.parse('観点,A,B\n目的,短い\n\n罰則,あり,なし,\n\n')
        self.assertEqual(tb.head, 1)
        self.assertEqual(tb.spans, {})
        self.assertEqual(tb.rows, [['観点', 'A', 'B'], ['目的', '短い', ''], ['罰則', 'あり', 'なし']])
        long = self.ht.parse('観点,説明\n目的,' + 'とても長い説明の文章' * 4 + '\n')
        self.assertEqual(long.long, [False, True])
        self.assertIn('columns: (auto, 1fr,)', self.ht.to_typst(long, 'x'))
        # 数字の列: 桁区切り・括弧・負号・%・有意の印も数字、ダッシュは空欄あつかい
        nums = self.ht.parse('a,b\nx,"1,234"\ny,(0.05)\nz,−0.12***\nw,—\nv,12%\n')
        self.assertEqual(nums.align, ['l', 'r'])

    def test_cells_are_plain_text_in_every_format(self):
        tb = self.ht.parse('a,b\n"say ""hi"" \\ #x","@key *em* _u_ $5"\n')
        typ = self.ht.to_typst(tb, 'x')
        self.assertIn(r'"say \"hi\" \\ #x"', typ)
        md_ = self.ht.to_markdown(tb, 'x')
        self.assertIn(r'\@key \*em\* \_u\_ \$5', md_)
        tex = self.ht.to_latex(tb, 'x')
        self.assertIn(r'\_u\_ \$5', tex)

    def test_shift_jis_from_excel_is_read(self):
        self.write('sjis', '項目,内容\n見本,日本語\n', encoding='cp932')
        report: list = []
        self.assertTrue(self.ht.run(self.cfg, report), report)
        self.assertIn('Shift_JIS', report[0])
        self.assertIn('"日本語"', (self.out / 'sjis.typ').read_text(encoding='utf-8'))

    def test_new_table_then_build_makes_three_files(self):
        self.assertEqual(self.new_table('compare.csv'), 0)       # 拡張子は付けても付けなくても
        self.assertEqual((self.src / 'compare.csv').read_text(encoding='utf-8').splitlines()[0],
                         '項目,内容')
        self.assertEqual(names(self.ht.stale(self.cfg)), ['compare.csv'])
        report: list = []
        self.assertTrue(self.ht.run(self.cfg, report), report)
        for ext in ('.typ', '.tex', '.md'):
            self.assertTrue((self.out / f'compare{ext}').is_file(), ext)
        self.assertEqual(self.ht.stale(self.cfg), [])
        items = {i.label: i for i in audit.collect(self.cfg)}
        self.assertTrue(items['tables made by hand'].ok)
        # 再現用パッケージにも元の .csv が入る（プロジェクトと同じ場所に）
        with contextlib.redirect_stdout(io.StringIO()):
            rep = bundle.replication(self.cfg, Path(self.tmp.name) / 'rep')
        self.assertIn('tables/compare.csv',
                      [p.relative_to(Path(self.tmp.name) / 'rep').as_posix() for p in rep.files])

    def test_an_english_project_gets_the_english_template(self):
        d = Path(self.tmp.name) / 'en'
        make_project(d, docs=(), lang='en', analysis=False)
        with contextlib.redirect_stdout(io.StringIO()):
            scaffold.new(d / 'octavo.config.py', 'table', 'compare')
        self.assertNotRegex((d / 'tables' / 'compare.csv').read_text(encoding='utf-8'),
                            r'[぀-ヿ]')

    def test_a_table_from_the_analysis_is_not_overwritten(self):
        self.out.mkdir(parents=True, exist_ok=True)
        (self.out / 'summary.typ').write_text(
            '// octavo.R の ov_table() が作ったファイル。手で直さない。\n#table()\n',
            encoding='utf-8')
        self.assertEqual(self.new_table('summary'), 1)
        self.assertFalse((self.src / 'summary.csv').exists())
        # .csv を手で置いても、組むときに止める（どちらが組まれるかが順番で変わるため）
        self.write('summary', 'a,b\n1,2\n')
        report: list = []
        self.assertFalse(self.ht.run(self.cfg, report))
        self.assertIn('summary', report[0])
        items = {i.label: i for i in audit.collect(self.cfg)}
        self.assertFalse(items['tables made by hand'].ok)
        self.assertTrue(items['tables made by hand'].fatal)

    def test_a_placeholder_table_may_be_replaced(self):
        self.out.mkdir(parents=True, exist_ok=True)
        (self.out / 'summary.typ').write_text('// octavo:placeholder 仮の表\n#table()\n',
                                              encoding='utf-8')
        self.write('summary', 'a,b\n1,2\n')
        report: list = []
        self.assertTrue(self.ht.run(self.cfg, report), report)
        self.assertIn('tables/summary.csv', (self.out / 'summary.typ').read_text(encoding='utf-8'))

    def test_no_row_without_hand_tables(self):
        labels = [i.label for i in audit.collect(self.cfg)]
        self.assertNotIn('tables made by hand', labels)

    def test_a_bad_csv_stops_the_build(self):
        self.write('empty', '\n\n')
        report: list = []
        self.assertFalse(self.ht.run(self.cfg, report))
        self.assertIn('tables/empty.csv', '\n'.join(report))

    @unittest.skipUnless(shutil.which('typst'), 'needs typst')
    def test_the_typst_file_compiles(self):
        self.write('grouped', self.GROUPED)
        self.write('long', '観点,制度A,制度B\n目的,"' + 'とても長い説明の文章' * 5
                   + '\n二行目",短い\n')
        report: list = []
        self.assertTrue(self.ht.run(self.cfg, report), report)
        doc = self.root / 'doc.typ'
        doc.write_text('#figure(include "assets/tables/grouped.typ", kind: table)\n'
                       '#figure(include "assets/tables/long.typ", kind: table)\n',
                       encoding='utf-8')
        r = subprocess.run(['typst', 'compile', str(doc)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    @unittest.skipUnless(HAVE_PANDOC, 'needs pandoc')
    def test_the_manuscript_places_it_by_its_caption_line(self):
        self.write('compare', '観点,A\n目的,@nocite *x*\n')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(self.ht.run(self.cfg, []))
        paper = self.root / 'papers' / 'mypaper' / 'paper.md'
        paper.write_text(paper.read_text(encoding='utf-8').replace(
            '# はじめに {#sec-intro}',
            '# はじめに {#sec-intro}\n\n@tbl-compare を見る。\n\n: 比較 {#tbl-compare}\n'),
            encoding='utf-8')
        doc = self.cfg.document('mypaper')
        for target in ('typst', 'docx'):
            res = build.build_one(self.cfg, doc, target, citations=False, offline=True)
            self.assertFalse([l for l in res.report if 'missing' in l or 'がない' in l],
                             res.report)
        body = (self.cfg.out_dir('typst', doc) / 'body.typ').read_text(encoding='utf-8')
        self.assertIn('assets/tables/compare.typ', body)


class AssetsLayout(unittest.TestCase):
    """手で作るもの（figures/）と、分析と build が書くもの（assets/）の置き場。"""

    def test_defaults(self):
        d = config.DEFAULTS
        self.assertEqual((d['figure_src_dir'], d['table_src_dir'], d['figure_dir'],
                          d['table_dir'], d['values_dir']),
                         ('figures', 'tables', 'assets/figures', 'assets/tables',
                          'assets/values'))

    def test_vector_figures_everywhere_but_word(self):
        cfg = {'figure_ext': {}}
        for name in ('typst', 'typst-slides', 'typst-notes', 'latex', 'beamer'):
            self.assertEqual(be.get(name).figure_ext(cfg), '.pdf', name)
        self.assertEqual(be.get('docx').figure_ext(cfg), '.png')
        self.assertEqual(be.get('typst').figure_ext({'figure_ext': {'typst': '.png'}}), '.png')

    def test_a_hand_placed_photo_is_left_as_it_is(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'p'
            make_project(root, docs=(('paper', 'mypaper'),), analysis=False)
            cfg = config.load(root / 'octavo.config.py')
            doc = cfg.document('mypaper')
            ctx = Ctx(cfg=cfg, backend=be.get('typst'), out_dir=cfg.out_dir('typst', doc),
                      profile='paper', doc_name='mypaper')
            photo = os.path.relpath(root / 'figures' / 'site.png', ctx.out_dir)
            drawn = os.path.relpath(root / 'assets' / 'figures' / 'trend.png', ctx.out_dir)
            self.assertEqual(ctx.figure_target(photo), photo)
            self.assertTrue(ctx.figure_target(drawn).endswith('assets/figures/trend.pdf'))

    def test_a_new_project_writes_into_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'p'
            make_project(root, docs=(('paper', 'mypaper'),))      # 見本の分析つき
            self.assertTrue((root / 'figures').is_dir())            # 手で作る図の置き場
            for rel in ('assets/values/analysis.json', 'assets/figures/trend.pdf',
                        'assets/tables/summary.typ'):
                self.assertTrue((root / rel).is_file(), rel)
            for old in ('results', 'tables'):
                self.assertFalse((root / old).exists(), old)


class Website(unittest.TestCase):
    """site/（GitHub Pages に出すページ）は公開リポジトリにそのまま出る。"""

    PAGES = {'en': ROOT / 'site' / 'index.html', 'ja': ROOT / 'site' / 'ja' / 'index.html'}

    def read(self, lang):
        return self.PAGES[lang].read_text(encoding='utf-8')

    def test_nothing_is_loaded_from_elsewhere(self):
        """外部のスクリプト・スタイル・画像・フォントを読まない（訪問者の情報を外に出さない）。"""
        for lang in self.PAGES:
            html = self.read(lang)
            # インラインの script だけ（言語の自動切り替え）。外から読むものはない
            self.assertNotRegex(html, r'<script\b[^>]*\bsrc=', lang)
            loaded = re.findall(r'<(?:img|link|source|iframe)\b[^>]*\b(?:src|href)="([^"]+)"', html)
            loaded = [u for u in loaded if not u.endswith(('/', '.html'))]
            self.assertTrue(loaded, lang)
            for url in loaded:
                self.assertNotRegex(url, r'^(?:https?:)?//', f'{lang}: {url}')
        css = (ROOT / 'site' / 'style.css').read_text(encoding='utf-8')
        self.assertNotRegex(css, r'@import|url\(')

    def test_local_files_exist(self):
        """ページが指すファイルが、Pages に出すときの配置（docs/images -> images/）にあること。"""
        for lang, page in self.PAGES.items():
            for url in re.findall(r'(?:src|href)="([^"#:]+)"', self.read(lang)):
                if url.endswith('/'):
                    url += 'index.html'
                path = (page.parent / url).resolve()
                rel = path.relative_to((ROOT / 'site').resolve())
                if rel.parts[0] == 'images':
                    path = ROOT / 'docs' / Path(*rel.parts)
                for slug in ('guide', 'lectures'):
                    if slug in rel.parts:
                        # 手引きのページは docs/<slug>*.md から組む（site/build.sh）
                        path = ROOT / 'docs' / (f'{slug}.ja.md' if rel.parts[0] == 'ja'
                                                else f'{slug}.md')
                self.assertTrue(path.is_file(), f'{lang}: {url}')

    def test_no_personal_details(self):
        """ページに出る作者はハンドル名だけ。所属・実名・メールアドレス・手元のパスを書かない。"""
        for lang in self.PAGES:
            html = self.read(lang)
            self.assertNotRegex(html, r'@[\w.-]+\.(?:ac\.jp|edu|com|org)\b', lang)
            self.assertNotRegex(html, r'(?i)takahiro|/home/|university|大学', lang)
            self.assertIn('https://github.com/yoshida-kd"', html)

    def test_the_two_languages_match(self):
        """英日のページは同じ節・同じ数のリンクで、互いを指す。"""
        en, ja = self.read('en'), self.read('ja')
        count = lambda s, pat: len(re.findall(pat, s))
        for pat in (r'<h2>', r'<h3>', r'<pre>', r'<li>', r'<a '):
            self.assertEqual(count(en, pat), count(ja, pat), pat)
        self.assertIn('href="ja/"', en)
        self.assertIn('href="../"', ja)
        # 日本語は、HTML の改行が空白として出ないように、文の途中で改行しない
        self.assertNotRegex(ja, r'[^\x00-\x7f]\n[ \t]*[^<\s]')

    def test_the_language_switch_respects_a_choice(self):
        """英語版は日本語のブラウザだけを日本語版へ移し、リンクで選んだ人は動かさない。"""
        en, ja = self.read('en'), self.read('ja')
        self.assertIn("location.replace('ja/'", en)
        self.assertIn("localStorage.getItem('octavo-lang')", en)
        self.assertIn('data-lang="ja"', en)
        self.assertIn('data-lang="en"', ja)
        self.assertIn("localStorage.setItem('octavo-lang'", ja)
        self.assertNotIn('location.replace', ja)
        self.assertIn('hreflang="x-default"', en)

    def test_the_workflow_runs_only_on_the_public_repo(self):
        wf = (ROOT / '.github' / 'workflows' / 'pages.yml').read_text(encoding='utf-8')
        self.assertIn("if: github.repository == 'yoshida-kd/octavo'", wf)
        self.assertIn('cp docs/images/* _site/images/', wf)
        self.assertIn('sh site/build.sh _site', wf)


class GuidePages(unittest.TestCase):
    """手引き（docs/guide*.md）と講義ノートの手引き（docs/lectures*.md）、それを組んだ
    Pages のページ（site/build.sh）。"""

    GUIDES = {'en': ROOT / 'docs' / 'guide.md', 'ja': ROOT / 'docs' / 'guide.ja.md'}
    # 英語と日本語の組。どの組もコードと見出しの数がそろっている
    PAIRS = {'guide': GUIDES,
             'lectures': {'en': ROOT / 'docs' / 'lectures.md',
                          'ja': ROOT / 'docs' / 'lectures.ja.md'}}

    @staticmethod
    def code_blocks(text: str) -> list:
        """コードブロックの中身から、コメントと日本語の説明を除いたもの（英日で同じはず）。"""
        out = []
        for lang, body in re.findall(r'^```(\w*)\n(.*?)^```', text, re.S | re.M):
            lines = []
            for line in body.split('\n'):
                line = re.sub(r'\s+#\s.*$', '', line)            # シェル・Python のコメント
                line = re.sub(r'\s+//.*$', '', line)
                if lang == '' and re.search(r'[^\x00-\x7f]', line):
                    # 説明つきの一覧（フォルダーの中身・コマンド一覧）は、左の列だけ比べる
                    line = re.split(r'\s{2,}', line.strip())[0]
                lines.append(line.rstrip())
            out.append((lang, '\n'.join(lines).strip()))
        return out

    def test_the_two_guides_have_the_same_code(self):
        """日本語の手引きのコードは英語のものと同じ（訳すのはコメントだけ）。"""
        for name, pair in self.PAIRS.items():
            en = self.code_blocks(pair['en'].read_text(encoding='utf-8'))
            ja = self.code_blocks(pair['ja'].read_text(encoding='utf-8'))
            self.assertEqual(len(en), len(ja), name)
            for (le, e), (lj, j) in zip(en, ja):
                self.assertEqual(le, lj, name)
                if le in ('bash', 'powershell', 'markdown', 'python', 'typst', 'r'):
                    self.assertEqual(e, j, name)

    def test_the_two_guides_have_the_same_chapters(self):
        count = lambda p, pat: len(re.findall(pat, p.read_text(encoding='utf-8'), re.M))
        for name, pair in self.PAIRS.items():
            for pat in (r'^## ', r'^### ', r'^#### '):
                self.assertEqual(count(pair['en'], pat), count(pair['ja'], pat), (name, pat))

    def test_install_has_a_section_for_each_system(self):
        for lang, p in self.GUIDES.items():
            text = p.read_text(encoding='utf-8')
            for heading in ('### 1.1 Linux', '### 1.2 macOS', '### 1.3 Windows'):
                self.assertIn(heading + '\n', text, lang)

    def test_every_section_is_numbered(self):
        """節（###）と項（####）には章の番号から続く番号が付いている。"""
        for name, p in self.GUIDES.items():
            text = re.sub(r'^```.*?^```', '', p.read_text(encoding='utf-8'), flags=re.S | re.M)
            chapter = section = 0
            for level, title in re.findall(r'^(#{2,4}) (.*)$', text, re.M):
                if level == '##':
                    chapter, section = int(title.split('.')[0]), 0
                elif level == '###':
                    section += 1
                    self.assertTrue(title.startswith(f'{chapter}.{section} '), (name, title))
                else:
                    self.assertRegex(title, rf'^{chapter}\.{section}\.\d+ ', name)

    @unittest.skipUnless(HAVE_PANDOC, 'pandoc が要る')
    def test_the_pages_build_and_every_link_inside_works(self):
        d = Path(tempfile.mkdtemp())
        try:
            subprocess.run(['sh', str(ROOT / 'site' / 'build.sh'), str(d)], check=True,
                           capture_output=True)
            for lang, rel in (('en', 'guide/index.html'), ('ja', 'ja/guide/index.html'),
                              ('en', 'lectures/index.html'), ('ja', 'ja/lectures/index.html')):
                html = (d / rel).read_text(encoding='utf-8')
                ids = set(re.findall(r'\bid="([^"]+)"', html))
                broken = [a for a in re.findall(r'href="#([^"]+)"', html) if a not in ids]
                self.assertEqual(broken, [], lang)
                # 外から何も読まない
                self.assertNotRegex(html, r'<(?:script|img|link|iframe)\b[^>]*\b(?:src|href)="(?:https?:)?//', lang)
                # GitHub で読む人への案内は落ちている
                self.assertNotIn('pages:skip', html)
                # 言語の切り替えは同じページの別の言語へ
                other = rel.replace('ja/', '') if lang == 'ja' else 'ja/' + rel
                self.assertIn('/' + other.replace('index.html', '') + '"', html)
                if 'guide' in rel:
                    self.assertIn('Linux', html)
                if lang == 'ja':
                    # 本文の日本語の途中に改行（＝空白）がない（コードブロックの中は除く）
                    prose = re.sub(r'<pre\b.*?</pre>', '', html, flags=re.S)
                    self.assertNotRegex(prose, r'[^\x00-\x7f]\n[^<\s]')
        finally:
            shutil.rmtree(d, ignore_errors=True)


# =====================================================================
class OutputsAndDocs(unittest.TestCase):
    """文書は docs/<名前>/<名前>.md、作るものは冒頭の outputs、回は sessions。
    体裁は原稿の横の main.typ があればそれ、なければ組み込みのもの。"""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.root = make_project(self.d / 'p', docs=(('paper', 'mine'), ('lecture', 'course'),
                                                     ('slides', 'talk')),
                                 example=False, legacy=False)
        self.cfgp = self.root / 'octavo.config.py'

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def cfg(self):
        return config.load(self.cfgp)

    def write(self, name, text):
        p = self.root / 'docs' / name / f'{name}.md'
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
        return p

    def test_new_writes_into_docs_with_what_it_makes(self):
        for name in ('mine', 'course', 'talk'):
            self.assertTrue((self.root / f'docs/{name}/{name}.md').is_file(), name)
        self.assertTrue((self.root / 'docs/mine/main.typ').is_file())
        for old in ('papers', 'slides', 'lectures'):
            self.assertFalse((self.root / old).exists(), old)
        cfg = self.cfg()
        got = {n: (d.outputs, d.profile, d.sessions) for n, d in cfg.documents.items()}
        self.assertEqual(got, {'mine': (('pdf',), 'paper', False),
                               'course': (('pdf', 'slides'), 'handout', True),
                               'talk': (('slides',), 'slides', False)})
        self.assertTrue(all(d.derived for d in cfg.documents.values()))
        head = (self.root / 'docs/course/course.md').read_text(encoding='utf-8').split('---')[1]
        self.assertIn('outputs: [pdf, slides]', head)
        self.assertIn('sessions: true', head)

    def test_a_folder_without_its_manuscript_is_not_a_document(self):
        (self.root / 'docs/notes').mkdir()
        (self.root / 'docs/notes/scratch.md').write_text('# x\n', encoding='utf-8')
        self.assertNotIn('notes', self.cfg().documents)

    def test_outputs_take_the_output_names_and_the_old_format_names(self):
        p = self.write('wp', '---\noutputs: [pdf, word, script]\n---\n\n# A\n')
        cfg = self.cfg()
        self.assertEqual(cfg.document('wp').targets, ('typst', 'docx', 'typst-notes'))
        self.assertEqual(cfg.document('wp').outputs, ('pdf', 'word', 'script'))
        p.write_text('---\ntargets: [typst, docx]\n---\n\n# A\n', encoding='utf-8')
        self.assertEqual(self.cfg().document('wp').outputs, ('pdf', 'word'))
        with contextlib_redirect() as err:
            p.write_text('---\noutputs: [slides]\ntargets: [docx]\n---\n', encoding='utf-8')
            self.assertEqual(self.cfg().document('wp').outputs, ('slides',))
        for bad in ('[html]', '[pdf, flyer]'):
            p.write_text(f'---\noutputs: {bad}\n---\n', encoding='utf-8')
            with self.assertRaises(SystemExit):
                self.cfg()
        # 書かなければ pdf
        p.write_text('# A\n', encoding='utf-8')
        self.assertEqual(self.cfg().document('wp').outputs, ('pdf',))
        self.assertEqual(be.resolve_targets('pdf,slides,typst', 'paper'), ['typst', 'typst-slides'])
        with self.assertRaises(SystemExit):
            be.resolve_targets('flyer', 'paper')

    def test_the_layout_decides_paper_or_handout(self):
        self.write('wp', '# A\n')
        self.assertEqual(self.cfg().document('wp').profile, 'handout')
        (self.root / 'docs/wp/main.typ').write_text('', encoding='utf-8')
        self.assertEqual(self.cfg().document('wp').profile, 'paper')

    def test_session_markers_make_a_document_of_sessions(self):
        self.write('wp', '# A\n\n```\n::: {.session #x}\n:::\n```\n')
        self.assertFalse(self.cfg().document('wp').sessions)        # コードの中は数えない
        self.write('wp', '::: {.session #x}\n:::\n\n# A\n')
        doc = self.cfg().document('wp')
        self.assertTrue(doc.sessions)
        self.assertEqual([p.name for p in self.cfg().parts(doc)], ['wp-x'])
        self.write('wp', '---\nsessions: false\n---\n\n::: {.session #x}\n:::\n')
        self.assertFalse(self.cfg().document('wp').sessions)

    def ctx(self, doc, target='typst'):
        cfg = self.cfg()
        d = cfg.document(doc)
        return Ctx(cfg=cfg.for_document(d), backend=be.get(target), out_dir=self.root,
                   profile=d.profile, document=d)

    def test_contents_and_abstract_follow_sessions_in_the_builtin_layout(self):
        self.write('wp', '# A\n')
        self.assertFalse(self.ctx('wp').profile_opt('toc'))
        self.assertTrue(self.ctx('wp').profile_opt('abstract'))
        self.assertTrue(self.ctx('course').profile_opt('toc'))
        self.assertFalse(self.ctx('course').profile_opt('abstract'))
        self.write('wp', '---\ntoc: true\n---\n\n# A\n')
        self.assertTrue(self.ctx('wp').profile_opt('toc'))

    def test_a_single_heading_is_a_section_not_a_title(self):
        cfg = self.cfg()
        doc = cfg.document('mine')
        Path(doc.src).write_text('---\ntitle: T\n---\n\nLead.\n\n# Only\n\n## Sub\n',
                                 encoding='utf-8')
        ctx = self.ctx('mine')
        body, _ = build.preprocess(ctx.cfg, doc, ctx.backend, ctx, Path(doc.src).read_text(encoding='utf-8'))
        self.assertIn('# Only', body)
        self.assertIn('Lead.', body)

    def test_output_names_choose_what_is_kept(self):
        self.assertIn('pdf', self.ctx('mine').keep_classes)
        self.assertIn('word', self.ctx('mine', 'docx').keep_classes)
        self.assertIn('script', self.ctx('talk', 'typst-notes').keep_classes)
        src = '::: {.pdf-only}\nP\n:::\n\n::: {.word-only}\nW\n:::\n'
        out = md.filter_divs(src, self.ctx('mine').keep_classes)
        self.assertIn('P', out)
        self.assertNotIn('W', out)

    def test_newpage_becomes_each_outputs_page_break(self):
        src = 'a\n\n\\newpage\n\nb\n\n\\clearpage\n\n```\n\\newpage\n```\n'
        typ = md.page_breaks(src, be.get('typst').fmt_pagebreak(None))
        self.assertEqual(typ.count('#pagebreak()'), 2)
        self.assertIn('```\n\\newpage\n```', typ)                 # コードの中はそのまま
        self.assertIn('\\clearpage', md.page_breaks(src, be.get('latex').fmt_pagebreak(None)))
        self.assertIn('w:type="page"', md.page_breaks(src, be.get('docx').fmt_pagebreak(None)))
        self.assertNotIn('newpage', md.page_breaks(src, be.get('typst-slides').fmt_pagebreak(None))
                         .split('```')[0])

    def test_newslide_in_one_line(self):
        src = '## First\n\na\n\n\\newslide\n\nb\n\n\\newslide{Other}\n\nc\n\n\\newslide{}\n\nd\n'
        out = md.slide_marks(src, True, 'en')
        self.assertIn('## First (cont.) {.unnumbered}', out)
        self.assertIn('## Other {.unnumbered}', out)
        self.assertIn(md.UNTITLED_SLIDE, out)
        self.assertNotIn('newslide', md.slide_marks(src, False, 'en'))

    def test_renamed_keys_are_still_read(self):
        text = self.cfgp.read_text(encoding='utf-8').replace(
            "'documents'", "'typst_slides_accent': None,\n    'handout_fontsize': '12pt',\n    'documents'", 1)
        self.cfgp.write_text(text, encoding='utf-8')
        cfg = self.cfg()
        self.assertIsNone(cfg['slides_accent'])
        self.assertEqual(cfg['fontsize'], '12pt')
        # サイドバーから変えると、前の名前の行が今の名前になる（2行にしない）
        from octavo import confedit
        confedit.set_value(self.cfgp, 'slides_accent', '#123456')
        text = self.cfgp.read_text(encoding='utf-8')
        self.assertIn("'slides_accent': '#123456'", text)
        self.assertNotIn('typst_slides_accent', text)
        # 原稿の冒頭でも
        p = self.root / 'docs/talk/talk.md'
        p.write_text('---\noutputs: [slides]\ntypst_slides_aspect: 4-3\n---\n\n## A\n',
                     encoding='utf-8')
        cfg = self.cfg()
        self.assertEqual(cfg.for_document(cfg.document('talk'))['slides_aspect'], '4-3')
        self.assertEqual(config.doc_setting_typos(p), [])
        confedit.set_doc_value(cfg, cfg.document('talk'), 'slides_aspect', '16-9')
        self.assertIn('slides_aspect: 16-9', p.read_text(encoding='utf-8'))
        self.assertNotIn('typst_slides_aspect', p.read_text(encoding='utf-8'))

    def test_build_folders_are_named_after_the_outputs(self):
        cfg = self.cfg()
        rel = {o: cfg.rel(cfg.out_dir(b)) for o, b in config.OUTPUTS.items()}
        self.assertEqual(rel, {'pdf': 'build/pdf', 'word': 'build/word', 'tex': 'build/tex',
                               'slides': 'build/slides', 'beamer': 'build/beamer',
                               'script': 'build/script', 'poster': 'build/poster'})
        self.assertEqual(cfg.rel(cfg.out_dir('typst', cfg.document('mine'))), 'build/pdf/mine')
        # 設定の out_dirs と figure_ext は出力の名前でも形式の名前でも書ける
        text = self.cfgp.read_text(encoding='utf-8').replace(
            "    'documents'", "    'out_dirs': {'pdf': 'out/p', 'docx': 'out/w'},\n"
            "    'figure_ext': {'word': '.jpg'},\n    'documents'", 1)
        self.cfgp.write_text(text, encoding='utf-8')
        cfg = self.cfg()
        self.assertEqual(cfg.rel(cfg.out_dir('typst')), 'out/p')
        self.assertEqual(cfg.rel(cfg.out_dir('docx')), 'out/w')
        self.assertEqual(cfg['figure_ext'], {'docx': '.jpg'})

    @unittest.skipUnless(HAVE_PANDOC, 'pandoc が要る')
    def test_every_kind_builds_from_docs(self):
        if not pandocrun.at_least(3, 1):
            self.skipTest('pandoc 3.1 以上が要る')
        cfg = self.cfg()
        with contextlib.redirect_stdout(io.StringIO()):
            results = build.run(cfg, offline=True, citations=False)
        self.assertTrue(all(r.ok for r in results), [r.report for r in results if not r.ok])
        names = {(r.doc, r.target) for r in results}
        self.assertTrue({('mine', 'typst'), ('course', 'typst'), ('talk', 'typst-slides')} <= names)
        self.assertTrue((self.root / 'build/pdf/mine/body.typ').is_file())
        if shutil.which('typst'):
            with contextlib.redirect_stdout(io.StringIO()):
                r = build.build_one(cfg, cfg.document('mine'), 'typst', do_compile=True,
                                    offline=True, citations=False)
            self.assertTrue(r.ok, r.report)
            self.assertTrue((self.root / 'build/pdf/mine.pdf').is_file())     # 論文の PDF の写し
        self.assertTrue((self.root / 'build/pdf/course.typ').is_file())


# =====================================================================
class CommandCleanup(unittest.TestCase):
    """コマンドの整理: check values|cites|lint、build --sessions、template copy word、
    1行の \\session{…}。前からの書き方も残る。"""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.root = make_project(self.d / 'p', docs=(('paper', 'mine'),), legacy=False)
        self.cfgp = str(self.root / 'octavo.config.py')

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def cli(self, *argv):
        from octavo import cli
        with contextlib.redirect_stdout(io.StringIO()) as out, contextlib_redirect():
            rc = cli.main([*argv, '-c', self.cfgp])
        return rc, out.getvalue()

    def test_check_takes_one_part(self):
        for part, old in (('values', 'values'), ('cites', 'checkbib'), ('lint', 'lint')):
            new = self.cli('check', part, '--json')
            self.assertEqual(new, self.cli(old, '--json'), part)
            json.loads(new[1].strip().split('\n')[-1])
        self.assertIn('--diff', self.cli('check', 'values', '--diff')[1] + '--diff')

    def test_template_copy_word_is_used_for_word(self):
        if not HAVE_PANDOC:
            self.skipTest('pandoc が要る')
        rc, out = self.cli('template', 'copy', 'word')
        self.assertEqual(rc, 0, out)
        ref = self.root / 'templates/word/reference.docx'
        self.assertTrue(ref.is_file())
        self.assertNotEqual(self.cli('template', 'copy', 'word')[0], 0)    # 2度目は --force が要る
        cfg = config.load(self.cfgp)
        ctx = Ctx(cfg=cfg, backend=be.get('docx'), out_dir=self.root, profile='paper')
        args = be.get('docx').pandoc_args(ctx)
        self.assertIn(str(ref), args)
        self.assertIn('word/reference.docx', self.cli('template', 'list')[1])

    def test_a_one_line_session_marker_has_every_attribute(self):
        src = ('\\session{Week 1: Intro} {#w1 date="2026-10-14" subtitle="S" author="A" institute="I"}\n\n'
               '# A\n\ntext\n\n\\session{} {#w2}\n\n# B\n\n```\n\\session{not this}\n```\n')
        _, parts, _ = md._sections(src)
        self.assertEqual([(k, t) for k, t, _, _ in parts], [('w1', 'Week 1: Intro'), ('w2', 'B')])
        self.assertEqual(parts[0][3], {'id': 'w1', 'title': 'Week 1: Intro', 'date': '2026-10-14',
                                       'subtitle': 'S', 'author': 'A', 'institute': 'I'})
        self.assertTrue(md.has_session_markers(src))
        out = md.replace_session_markers(src, lambda a: '<' + a['id'] + '>')
        self.assertIn('<w1>', out)
        self.assertNotIn('\\session{Week', out)
        self.assertIn('\\session{not this}', out)                 # コードの中はそのまま

    def test_build_sessions_cuts_the_handouts(self):
        if not (HAVE_PANDOC and shutil.which('typst')):
            self.skipTest('pandoc と typst が要る')
        p = self.root / 'docs/c/c.md'
        p.parent.mkdir(parents=True)
        p.write_text('---\ntitle: C\noutputs: [pdf]\n---\n\n\\session{One} {#one}\n\n# A\n\nx\n\n'
                     '\\session{Two} {#two}\n\n# B\n\ny\n', encoding='utf-8')
        rc, out = self.cli('build', 'c', '--compile', '--sessions', '--no-analysis', '--offline')
        self.assertEqual(rc, 0, out)
        for key in ('one', 'two'):
            self.assertTrue((self.root / f'build/handouts/c-{key}.pdf').is_file(), out)


# =====================================================================
class Poster(unittest.TestCase):
    """ポスター（outputs: [poster]）: 一番上の見出し1つが1マス、既定は A0 縦・2列×3行。"""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.root = make_project(self.d / 'p', docs=(('poster', 'post'),), legacy=False)
        self.cfgp = self.root / 'octavo.config.py'
        self.src = self.root / 'docs/post/post.md'

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_new_poster_is_a_poster_document(self):
        doc = config.load(self.cfgp).document('post')
        self.assertEqual((doc.outputs, doc.profile), (('poster',), 'poster'))
        self.assertIn('<!-- octavo:section poster -->', (self.root / 'AGENTS.md').read_text(encoding='utf-8'))
        # 前からの置き場所のプロジェクトでは、docs/ が要ると言って断る
        old = make_project(self.d / 'old', docs=(), analysis=False)
        with contextlib_redirect():
            self.assertEqual(scaffold.new(old / 'octavo.config.py', 'poster', 'x', quiet=True), 1)

    def test_paper_sizes_and_grid(self):
        from octavo.backends import typst_poster as tp
        self.assertEqual(tp.paper_mm('a0', 'portrait'), (841, 1189))
        self.assertEqual(tp.paper_mm('a0', 'landscape'), (1189, 841))
        self.assertEqual(tp.paper_mm('b0', 'portrait'), (1030, 1456))            # JIS B
        self.assertEqual(tp.paper_mm('48x36in', 'landscape'), (48 * 25.4, 36 * 25.4))
        self.assertEqual(tp.grid_shape('3x2'), (3, 2))
        self.assertEqual(tp.grid_shape(['2', '3']), (2, 3))
        self.assertEqual(tp.row_ratios(['2', '1'], 2), [2.0, 1.0])
        for bad in ('a9', 'big'):
            with self.assertRaises(ValueError):
                tp.paper_mm(bad, 'portrait')
        self.src.write_text('---\noutputs: [poster]\nposter_rows: [1, 2]\n---\n\n# A\n', encoding='utf-8')
        with self.assertRaises(SystemExit):                    # 行の比が格子の行の数と合わない
            cfg = config.load(self.cfgp)
            cfg.for_document(cfg.document('post'))

    def test_cells_are_placed_like_the_grid(self):
        from octavo.backends import typst_poster as tp
        body = ('<!-- a note -->\n\n# A\n\na\n\n# B\n\n# C {span=2}\n\n# D {cell="1,3"}\n\n'
                '# E\n\n```\n# not a cell\n```\n')
        cells = tp.poster_cells(body)
        self.assertEqual([c['name'] for c in cells], ['A', 'B', 'C', 'D', 'E'])
        self.assertEqual(tp.place_cells(cells, 2, 3), '')
        self.assertEqual({c['name']: c['at'] for c in cells},
                         {'A': (1, 1), 'B': (2, 1), 'C': (1, 2), 'D': (1, 3), 'E': (2, 3)})
        cells = tp.poster_cells('# A {span=3}\n')
        self.assertIn('A', tp.place_cells(cells, 2, 3))           # 入りきらなければ止める

    def test_qr_is_well_formed(self):
        from octavo import qr
        m = qr.matrix('https://example.org/paper')
        self.assertEqual(len(m), 25)                              # 25 字 → 型番 2（21 + 4）
        finder = [[True] * 7, [True] + [False] * 5 + [True]]
        self.assertEqual(m[0][:7], finder[0])
        self.assertEqual(m[1][:7], finder[1])
        self.assertTrue(m[len(m) - 8][8])                         # 常に黒のモジュール
        self.assertIn('<svg', qr.svg('x'))

    @unittest.skipUnless(HAVE_PANDOC and shutil.which('typst'), 'pandoc と typst が要る')
    def test_it_typesets_and_reports_an_overflow(self):
        self.src.write_text('---\ntitle: T\noutputs: [poster]\nqr: https://example.org\n---\n\n'
                            '# Short\n\nx\n\n# Long\n\n' + 'word ' * 4000 + '\n', encoding='utf-8')
        cfg = config.load(self.cfgp)
        with contextlib.redirect_stdout(io.StringIO()):
            r = build.build_one(cfg, cfg.document('post'), 'typst-poster', do_compile=True,
                                offline=True, citations=False)
        self.assertTrue(r.ok, r.report)
        self.assertTrue((self.root / 'build/poster/post.pdf').is_file())
        self.assertTrue((self.root / 'build/poster/post-qr.svg').is_file())
        self.assertTrue(any('Long' in l and 'overflow' in l for l in r.report), r.report)
        self.assertFalse(any('Short' in l and 'overflow' in l for l in r.report), r.report)


# =====================================================================
class MarkedSelection(unittest.TestCase):
    """slides_select / poster_select: marked — 印（.on-slides / .on-poster）の所だけを出す。"""

    SRC = ('Intro.\n\n# S\n\n## A\n\nHandout only.\n\n### One\n\nNot this.\n\n'
           '::: {.on-slides}\n- picked\n:::\n\n::: notes\nsay\n:::\n\n### Two {.on-slides}\n\nWhole.\n\n'
           '#### Sub\n\nmore\n\n### Three\n\nText [short]{.on-slides} here.\n\n'
           '::: {.slides-only}\nonly slides\n:::\n\n```\n# code {.on-slides}\n```\n\n'
           '## B\n\nNothing.\n\n[^1]: note\n')

    def test_only_the_marked_parts_and_their_headings(self):
        out = md.select_marked(self.SRC, 'on-slides', ('slides-only',))
        for kept in ('# S', '## A', '### One', '- picked', '::: notes', '### Two {.on-slides}',
                     'Whole.', '#### Sub', 'more', '### Three', 'short', 'only slides', '[^1]: note'):
            self.assertIn(kept, out)
        for dropped in ('Intro.', 'Handout only.', 'Not this.', 'Text ', '## B', 'Nothing.',
                        '# code'):
            self.assertNotIn(dropped, out)
        self.assertNotIn('\n\n\n', out)

    def test_the_setting_is_checked_and_read_per_document(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        root = make_project(d / 'p', docs=(('lecture', 'lec'),), example=False, legacy=False)
        src = root / 'docs/lec/lec.md'
        src.write_text('---\noutputs: [pdf, slides]\nsessions: true\nslides_select: marked\n---\n\n'
                       '# One\n\n## A\n\n### S {.on-slides}\n\nx\n\n# Two\n\n## B\n\ny\n',
                       encoding='utf-8')
        cfg = config.load(root / 'octavo.config.py')
        doc = cfg.document('lec')
        self.assertEqual(build.marked_only(cfg.for_document(doc), be.get('typst-slides')),
                         ('on-slides', ('slides-only', 'only-slides', 'slide-only')))
        self.assertIsNone(build.marked_only(cfg.for_document(doc), be.get('typst')))
        self.assertEqual(build.unmarked_sessions(doc, 'on-slides'), {'02'})
        src.write_text('---\nslides_select: some\n---\n', encoding='utf-8')
        with self.assertRaises(SystemExit):
            cfg = config.load(root / 'octavo.config.py')
            cfg.for_document(cfg.document('lec'))

    @unittest.skipUnless(HAVE_PANDOC and shutil.which('typst'), 'pandoc と typst が要る')
    def test_a_deck_of_marked_parts_names_what_it_left_out_by_number(self):
        if not pandocrun.at_least(3, 1):
            self.skipTest('pandoc 3.1 以上が要る')
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        root = make_project(d / 'p', docs=(), legacy=False)
        src = root / 'docs/t/t.md'
        src.parent.mkdir(parents=True)
        src.write_text('---\noutputs: [slides]\nslides_select: marked\n---\n\n# A\n\n## One\n\n'
                       '![Trend](../../assets/figures/trend.png){#fig-trend}\n\n'
                       '## Two {.on-slides}\n\nSee @fig-trend.\n', encoding='utf-8')
        cfg = config.load(root / 'octavo.config.py')
        with contextlib.redirect_stdout(io.StringIO()):
            r = build.build_one(cfg, cfg.document('t'), 'typst-slides', do_compile=True,
                                offline=True, citations=False)
        self.assertTrue(r.ok, r.report)
        typ = (root / 'build/slides/t.typ').read_text(encoding='utf-8')
        self.assertNotIn('trend.pdf', typ)                      # 図は拾っていない
        self.assertNotIn('<fig-trend>', typ.split('#let octavo')[0] + typ.split('= Two')[-1])


# =====================================================================
class FixedNumbers(unittest.TestCase):
    """講義のデッキの図・表・式・ブロックの番号を、プリントでの番号に合わせる。"""

    def test_autolabel_names_what_gets_a_number(self):
        src = ('# A\n\n![Cap](a.png)\n\n![](b.png)\n\n![Has](c.png){#fig-has}\n\n| a |\n|---|\n| 1 |\n\n'
               ': Table cap\n\n::: question\nq\n:::\n\n::: {.nb}\nn\n:::\n\n```\n![Code](x.png)\n```\n')
        out = crossref.autolabel(src)
        self.assertEqual(out.count('\n'), src.count('\n'))           # 行の数は変えない
        labels = [it.label for it in crossref.number(out).items if it.kind != 'sec']
        self.assertEqual(len(labels), 4)
        self.assertTrue(all(labels))
        self.assertIn('fig-has', labels)
        self.assertNotIn('octavo', out.split('```')[1])               # コードの中はそのまま
        self.assertEqual(crossref.autolabel(src), out)                     # 何度でも同じ名前

    @unittest.skipUnless(HAVE_PANDOC and shutil.which('typst'), 'pandoc と typst が要る')
    def test_a_deck_keeps_the_handout_numbers(self):
        if not pandocrun.at_least(3, 1):
            self.skipTest('pandoc 3.1 以上が要る')
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        root = make_project(d / 'p', docs=(), legacy=False)
        src = root / 'docs/c/c.md'
        src.parent.mkdir(parents=True)
        src.write_text('---\noutputs: [pdf, slides]\nsessions: true\n---\n\n# W\n\n## A\n\n'
                       '::: {.pdf-only}\n![Only handout](../../assets/figures/trend.png)\n:::\n\n'
                       '### S\n\n![Both](../../assets/figures/trend.png){#fig-both}\n\n'
                       'See @fig-both.\n', encoding='utf-8')
        cfg = config.load(root / 'octavo.config.py')
        with contextlib.redirect_stdout(io.StringIO()):
            r = build.build_one(cfg, cfg.document('c-01'), 'typst-slides', do_compile=True,
                                offline=True, citations=False)
        self.assertTrue(r.ok, r.report)
        typ = (root / 'build/slides/c-slides-01.typ').read_text(encoding='utf-8')
        self.assertIn('"fig-both": "1.2"', typ)
        text = subprocess.run(['pdftotext', str(root / 'build/slides/c-slides-01.pdf'), '-'],
                              capture_output=True, text=True, encoding='utf-8').stdout \
            if shutil.which('pdftotext') else ''
        if text:
            self.assertIn('1.2', text)
            self.assertNotIn('1.1', text)


# =====================================================================
class MigrateToDocs(unittest.TestCase):
    """octavo migrate --docs: 前からの置き場所の原稿を docs/<名前>/ へ移す。"""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.root = make_project(self.d / 'p', docs=(('paper', 'mine'), ('lecture', 'course'),
                                                     ('slides', 'talk')))
        self.cfgp = self.root / 'octavo.config.py'

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def run_migrate(self, dry=False):
        from octavo import relocate
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = relocate.run(config.load(self.cfgp), dry_run=dry)
        return rc, out.getvalue()

    def test_check_says_they_can_be_moved(self):
        rows = {i.label: i for i in audit.collect(config.load(self.cfgp))}
        self.assertIn('migrate --docs', rows['where manuscripts live'].detail)
        self.assertTrue(rows['where manuscripts live'].ok)

    def test_a_dry_run_changes_nothing(self):
        before = sorted(p.relative_to(self.root) for p in self.root.rglob('*'))
        rc, out = self.run_migrate(dry=True)
        self.assertEqual(rc, 0)
        self.assertIn('docs/course/course.md', out)
        self.assertEqual(before, sorted(p.relative_to(self.root) for p in self.root.rglob('*')))

    def test_it_moves_them_and_they_mean_the_same(self):
        # 前の書き方の論文: `# 題` が1つだけで、節は `##`
        paper = self.root / 'papers/mine/paper.md'
        paper.write_text('---\ntitle: T\ntargets: [typst, docx]\n---\n\n# Old title\n\n## Intro\n\nText.\n',
                         encoding='utf-8')
        talk = self.root / 'slides/talk.md'
        talk.write_text(talk.read_text(encoding='utf-8') + '\n![x](../assets/figures/trend.png)\n',
                        encoding='utf-8')
        before = {n: (d.outputs, d.sessions, d.profile) for n, d in config.load(self.cfgp).documents.items()}
        rc, out = self.run_migrate()
        self.assertEqual(rc, 0, out)
        cfg = config.load(self.cfgp)
        after = {n: (d.outputs, d.sessions, d.profile) for n, d in cfg.documents.items()}
        self.assertEqual(before, after)
        self.assertTrue(all(d.derived for d in cfg.documents.values()))
        self.assertTrue((self.root / 'docs/mine/appendix.md').is_file())
        self.assertTrue((self.root / 'docs/mine/main.typ').is_file())
        self.assertFalse((self.root / 'papers/mine').exists())
        text = (self.root / 'docs/mine/mine.md').read_text(encoding='utf-8')
        head = text.split('---')[1]
        self.assertIn('outputs: [pdf, word]', head)
        self.assertNotIn('targets', head)
        self.assertNotIn('# Old title', text)                  # title: はもうあるので消すだけ
        self.assertIn('../../assets/figures/trend.png',
                      (self.root / 'docs/talk/talk.md').read_text(encoding='utf-8'))
        self.assertIn('sessions: true', (self.root / 'docs/course/course.md').read_text(encoding='utf-8'))
        self.assertIn("'docs/*/'", self.cfgp.read_text(encoding='utf-8'))
        # 2回目は何もしない
        rc, out = self.run_migrate()
        self.assertIn('nothing to move', out)

    def test_a_title_heading_moves_into_the_front_matter(self):
        from octavo import relocate
        mv = relocate.Move('x', Path('a'), Path('b'), front=['outputs: [pdf]'])
        got = relocate.rewrite('# The Title\n\n## Intro\n\nText.\n', mv, Path('/p/papers/x'),
                               Path('/p/docs/x'), True)
        self.assertTrue(got.startswith('---\ntitle: The Title\noutputs: [pdf]\n---\n'), got)
        self.assertNotIn('# The Title', got)

    @unittest.skipUnless(shutil.which('git'), 'git が要る')
    def test_it_uses_git_mv_and_stops_on_uncommitted_changes(self):
        def git(*a):
            return subprocess.run(['git', '-C', str(self.root), *a], capture_output=True, text=True)
        git('init', '-q')
        git('add', '-A')
        git('-c', 'user.email=a@b', '-c', 'user.name=a', 'commit', '-qm', 'x')
        talk = self.root / 'slides/talk.md'
        talk.write_text(talk.read_text(encoding='utf-8') + 'more\n', encoding='utf-8')
        rc, out = self.run_migrate()
        self.assertEqual(rc, 1)
        self.assertTrue(talk.is_file())
        git('checkout', '--', '.')
        rc, out = self.run_migrate()
        self.assertEqual(rc, 0, out)
        status = git('status', '--porcelain').stdout
        self.assertIn('R  papers/mine/main.typ -> docs/mine/main.typ', status)


# =====================================================================
class LectureRequests(unittest.TestCase):
    """講義ノートを書く中で出た不具合・要望（出し分け・囲みの検査・図表の注・題のない
    スライド・中身のない回・.qmd の冒頭の設定・綴り違いの知らせ）。"""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        make_project(self.d / 'p', docs=(('lecture', 'lec'),), example=False)
        self.cfg = config.load(self.d / 'p' / 'octavo.config.py')
        self.notes = self.d / 'p' / 'lectures' / 'lec.md'

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    SLIDES = {'slides', 'slide', 'screen', 'typst-slides'}
    PRINT = {'print', 'doc', 'typst', 'handout'}

    def test_conditional_blocks_inside_a_list_item(self):
        src = ded("""
            - 親.

              ::: {.handout-only}
              - プリントだけ
              :::

              ::: {.slides-only}
              - スライドだけ
              :::
            """)
        self.assertNotIn('スライドだけ', md.filter_divs(src, self.PRINT))
        self.assertIn('  - プリントだけ', md.filter_divs(src, self.PRINT))
        self.assertNotIn('プリントだけ', md.filter_divs(src, self.SLIDES))

    def test_inline_conditional_text(self):
        src = 'a [P]{.handout-only}[S]{.slides-only} [x]{#k .print-only} [l](u){.slides-only}'
        self.assertEqual(md.filter_divs(src, self.PRINT), 'a P [x]{#k} [l](u){.slides-only}')
        self.assertEqual(md.filter_divs(src, self.SLIDES), 'a S  [l](u){.slides-only}')

    def test_slide_only_means_slides_only(self):
        src = '::: {.slide-only}\nS\n:::\n'
        self.assertIn('S', md.filter_divs(src, self.SLIDES))
        self.assertNotIn('S', md.filter_divs(src, self.PRINT))

    def test_a_fence_shown_as_code_is_left_alone(self):
        src = '```\n::: {.slides-only}\nx\n:::\n```\n'
        self.assertEqual(md.filter_divs(src, self.PRINT), src)

    def test_lint_reports_blocks_pandoc_will_not_read(self):
        src = ded("""
            - 項目.
              ::: {.handout-only}
              - a
              :::

            ::: {.slids-only}
            :::

            [x]{.handouts-only} ::: {.no-slides}

            ```
            ::: {.whatever-only}
            ```
            """)
        got = [(k, fix) for _, k, _, fix in lint.div_problems(src)]
        self.assertIn(('literal', ''), got)
        self.assertIn(('unknown', 'slides-only'), got)
        self.assertIn(('unknown', 'handout-only'), got)
        self.assertEqual(len(got), 4)          # コードの中は見ない

    def test_no_lint_marks_and_phrases(self):
        src = ded("""
            成績: 中間40%, 期末[60%]{.no-lint}, 演習 30%.

            ::: {.no-lint}
            出席 10%
            :::
            """)
        hits = [h for _, _, h, _ in lint.scan(src, {'中間40%'})]
        self.assertEqual(hits, ['30%'])

    def test_a_misspelt_setting_is_named(self):
        self.notes.write_text('---\ntitle: x\nfirst-section-number: 0\nfont: y\n---\n# a\n',
                              encoding='utf-8')
        self.assertEqual(config.doc_setting_typos(self.notes),
                         [('first-section-number', 'first_section')])

    def test_figure_notes_find_their_figure_or_table(self):
        lines = ded("""
            ![T[^a]](x.png){#fig-a}

            ::: {.figure-note}
            src
            :::

            | a |
            |---|
            | 1 |

            : Cap {#tbl-b}

            ::: figure-note
            n
            :::

            text

            ::: {.figure-note}
            stray
            :::
            """).split('\n')
        found, stray = crossref.figure_notes(lines)
        self.assertEqual([(a, k) for a, _, _, k in found], [(0, 'fig'), (6, 'tbl')])
        self.assertEqual(len(stray), 1)
        self.assertEqual(crossref.IMAGE.match(lines[0]).group('alt'), 'T[^a]')

    @unittest.skipUnless(HAVE_PANDOC and shutil.which('typst'), 'pandoc と typst が要る')
    def test_a_figure_note_stays_with_its_figure(self):
        if not pandocrun.at_least(3, 1):
            self.skipTest('pandoc 3.1 以上が要る')
        self.notes.write_text(ded("""
            ---
            title: x
            ---

            # 回

            ## 節

            ### 図のスライド {.no-title}

            ![推移[^t]](../assets/figures/trend.png){#fig-trend}

            ::: {.figure-note}
            出典：見本の注。[^s]
            :::

            [^t]: 題の脚注。
            [^s]: 注の脚注。

            ### 次

            @fig-trend を見る。
            """), encoding='utf-8')
        (self.d / 'p' / 'assets' / 'figures').mkdir(parents=True, exist_ok=True)
        subprocess.run(['typst', 'compile', '-', str(self.d / 'p' / 'assets' / 'figures' / 'trend.pdf')],
                       input='#rect(width: 4cm, height: 2cm)', text=True, check=True,
                       encoding='utf-8', capture_output=True)
        doc = self.cfg.document('lec')
        r = build.build_one(self.cfg, doc, 'typst', citations=False, offline=True, do_compile=True)
        self.assertTrue(r.ok, '\n'.join(r.report))
        typ = r.outputs[0].read_text(encoding='utf-8')
        self.assertIn('#octavo-figure-group[', typ)
        self.assertIn('../../assets/figures/trend.pdf', typ)     # 題の脚注で道筋が崩れない
        part = self.cfg.parts(doc)[0]
        r = build.build_one(self.cfg, part, 'typst-slides', citations=False, offline=True,
                            do_compile=True)
        self.assertTrue(r.ok, '\n'.join(r.report))
        typ = r.outputs[0].read_text(encoding='utf-8')
        self.assertIn('#octavo-figure-group(size: 0.62em, h => [', typ)
        self.assertIn('#octavo-untitled-slide()', typ)
        self.assertNotIn('図のスライド', typ)
        self.assertNotIn('[^t]', typ)

    def test_no_title_only_on_slides(self):
        src = '## 節\n\n### 図だけ {.no-title}\n\n本文\n'
        self.assertIn(md.UNTITLED_SLIDE, md.slide_marks(src, True))
        self.assertNotIn('図だけ', md.slide_marks(src, True))
        self.assertEqual(md.slide_marks(src, False), src)

    def test_an_empty_session_gets_no_deck_and_old_decks_go(self):
        self.notes.write_text(ded("""
            ---
            title: x
            ---

            ::: {.session #one}
            :::

            # 一

            本文。

            ::: {.session #two title="予告"}
            :::
            """), encoding='utf-8')
        doc = self.cfg.document('lec')
        out = self.cfg.out_dir('typst-slides', doc)
        out.mkdir(parents=True, exist_ok=True)
        for name in ('lec-01.typ', 'lec-01.pdf', 'lec-two.typ', 'other.pdf'):
            (out / name).write_text('x', encoding='utf-8')
        self.assertEqual(build.empty_sessions(doc), {'two'})
        with unittest.mock.patch.object(build, 'build_one',
                               side_effect=lambda cfg, d, tgt, **k: build.Result(doc=d.name,
                                                                                 target=tgt)):
            rs = build.run(self.cfg, ['lec'], targets=['typst-slides'])
        self.assertEqual([r.doc for r in rs], ['lec-one', 'lec-two'])
        self.assertIn('nothing in it', '\n'.join(rs[1].report))
        self.assertEqual(sorted(p.name for p in out.iterdir()), ['other.pdf'])

    def test_the_slide_level_is_the_whole_notes(self):
        notes = '# A\n## a\n### s\n# B\n## b\n### t\n'
        self.assertEqual(md.lecture_slide_level(notes), 3)
        self.assertEqual(md.lecture_slide_level('# A\n## s\n# B\n## t\n'), 2)
        self.assertEqual(md.lecture_slide_level('```\n####### x\n```\n# A\n## s\n'), 2)

    @unittest.skipUnless(HAVE_PANDOC, 'pandoc が要る')
    def test_a_titled_marker_keeps_the_slides_at_the_third_level(self):
        """区切りに題を付けても、回の `#` がスライドに残っても、1枚は `###` のまま。"""
        if not pandocrun.at_least(3, 1):
            self.skipTest('pandoc 3.1 以上が要る')
        self.notes.write_text(ded("""
            ---
            title: x
            ---

            ::: {.session #week1 title="第1回 ガイダンス"}
            :::

            # 授業の案内

            ## 進め方

            ### 教科書

            本文。

            # 公務員の種類

            ## 種類

            ### 国家公務員

            本文。
            """), encoding='utf-8')
        part = self.cfg.document('lec-week1')
        r = build.build_one(self.cfg, part, 'typst-slides', citations=False, offline=True)
        self.assertTrue(r.ok, '\n'.join(r.report))
        typ = r.outputs[0].read_text(encoding='utf-8')
        self.assertIn('slide-level: 3,', typ)
        self.assertIn('=== 教科書', typ)

    def test_only_a_promoted_hash_heading_counts_as_a_section(self):
        from octavo.backends.typst_slides import promote_sections_with_content
        typ = '= 回\n\n== 節\n\n本文\n\n=== 1枚\n\n本文\n'
        out = promote_sections_with_content(typ, 3)
        self.assertIn('=== 節', out)
        self.assertNotIn('<octavo-section-step>', out)      # 「##」で節番号は進まない
        # 1枚にしても走りヘッダには節として出る（でないと上の「#」の題が出る）
        self.assertIn('#metadata([節]) <octavo-header-section>\n=== 節', out)
        out = promote_sections_with_content('= 回\n\n== 節 <sec-x>\n\n本文\n', 3)
        self.assertIn('#metadata([節]) <octavo-header-section>', out)
        out = promote_sections_with_content('= 回\n\n本文\n', 3)
        self.assertIn('<octavo-section-step>', out)
        self.assertIn('=== 回', out)

    def test_an_empty_last_session_does_not_take_the_previous_page(self):
        """後ろに何もない区切りは改ページせず、目印が前の回の最後のページに乗る。"""
        from octavo import extract
        marks = {'octavo-session': [{'key': 'one', 'page': 3, 'shown': '1'},
                                    {'key': 'two', 'page': 10, 'shown': '8'}],
                 'octavo-body': [{'page': 3, 'shown': '1'}],
                 'octavo-end': [{'page': 10, 'shown': '8'}]}
        with unittest.mock.patch.object(extract, '_marks', lambda typ, root, label: marks[label]):
            t = extract.page_table(Path('x.typ'), '.', skip={'two'})
        self.assertEqual([(s['key'], s['first'], s['last']) for s in t['sessions']],
                         [('one', 3, 10)])

    def test_no_title_and_no_lint_are_not_conditions(self):
        """`no-title` / `no-lint` は `no-slides` と同じ形だが、出し分けの印ではない。"""
        src = '### A\n\ntext\n\n::: {.slide .no-title}\n:::\n\nmore [40%]{.no-lint}\n'
        out = md.slide_marks(md.filter_divs(src, self.SLIDES), True)
        self.assertIn(md.UNTITLED_SLIDE, out)
        self.assertIn('[40%]{.no-lint}', out)
        self.assertEqual([k for _, k, _, _ in lint.div_problems(src)], [])

    def test_a_slide_figure_leaves_only_its_captions_height(self):
        from octavo.backends.typst_slides import fitted_figure
        out = fitted_figure('x.pdf', '推移', ' <fig-x>')
        self.assertIn('measure(figure(box(width: 100%, height: 0pt), caption: [推移])', out)
        self.assertIn('height: size.height - used', out)
        self.assertNotIn('3em', out)

    def test_a_qmd_says_it_runs_by_hand(self):
        q = self.d / 'p' / 'analysis' / '00-fetch.qmd'
        q.parent.mkdir(exist_ok=True)
        q.write_text('---\ntitle: x\noctavo:\n  manual: true\n  deps:\n    - "data/raw/*"\n'
                     'format: html\n---\n', encoding='utf-8')
        (self.d / 'p' / 'data' / 'raw').mkdir(parents=True, exist_ok=True)
        (self.d / 'p' / 'data' / 'raw' / 'a.csv').write_text('x', encoding='utf-8')
        self.assertEqual(analysis.qmd_settings(q), {'manual': True, 'deps': ['data/raw/*']})
        u = [u for u in analysis.units(self.cfg) if u.src.name == '00-fetch.qmd'][0]
        self.assertTrue(u.manual)
        # 同じ .qmd を個別にも書けば、そちらが優先で、1本として数える
        self.cfg._v['analysis'] = list(self.cfg['analysis']) + [
            {'src': 'analysis/00-fetch.qmd', 'manual': False}]
        us = [u for u in analysis.units(self.cfg) if u.src.name == '00-fetch.qmd']
        self.assertEqual(len(us), 1)
        self.assertFalse(us[0].manual)

    def test_aside_is_not_numbered(self):
        envs = crossref.theorem_envs(self.cfg)
        self.assertIsNone(envs['aside'].counter)
        self.assertEqual(envs['case'].counter, envs['question'].counter)

# =====================================================================
HELPER_PY = paths.templates_dir() / 'analysis/python/analysis/octavo_helper.py'
HAVE_UV = shutil.which('uv') is not None


def run_helper(d: Path, code: str, qmd: str = 'a.qmd') -> subprocess.CompletedProcess:
    """octavo_helper.py を、プロジェクトの根を OCTAVO_ROOT にして別プロセスで動かす。"""
    (d / 'analysis').mkdir(exist_ok=True)
    shutil.copy(HELPER_PY, d / 'analysis' / 'octavo_helper.py')
    env = {**os.environ, 'OCTAVO_ROOT': str(d), 'QUARTO_DOCUMENT_FILE': qmd, 'PYTHONUTF8': '1'}
    for k in ('OCTAVO_VALUES_DIR', 'OCTAVO_FIGURE_DIR', 'OCTAVO_TABLE_DIR', 'OCTAVO_VALUES_NAME'):
        env.pop(k, None)
    return subprocess.run([sys.executable, '-c',
                           'import sys; sys.path.insert(0, "analysis")\n'
                           'from octavo_helper import *\n' + code],
                          cwd=str(d), env=env, capture_output=True, text=True, encoding='utf-8')


class PythonHelper(unittest.TestCase):
    """analysis/octavo_helper.py（octavo.R の Python 版）。標準ライブラリだけで動く部分。"""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)

    def run_ok(self, code, **kw):
        r = run_helper(self.d, code, **kw)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def test_values_keep_integer_and_float_apart(self):
        self.run_ok('ov_value("n_obs", 1523, note="N")\n'
                    'ov_value("whole", 2.0)\n'
                    'ov_value("flag", True)\n'
                    'ov_value("missing", None)\n'
                    'ov_value("name", "日本語")\n'
                    'ov_value("p", ov_pval(0.0004))\n'
                    'ov_value("q", ov_pval(0.0421))\n')
        raw = (self.d / 'assets/values/a.json').read_text(encoding='utf-8')
        doc = json.loads(raw)
        self.assertIsInstance(doc['n_obs']['value'], int)
        self.assertIsInstance(doc['whole']['value'], float)       # 2.0 は小数のまま
        self.assertIn('"value": 2.0', raw)
        self.assertIs(doc['flag']['value'], True)
        self.assertEqual(doc['missing']['value'], 'NA')
        self.assertEqual(doc['name']['value'], '日本語')          # \uXXXX にしない
        self.assertEqual(doc['p']['value'], '< .001')
        self.assertEqual(doc['q']['value'], '.042')
        self.assertEqual(doc['n_obs']['note'], 'N')
        self.assertEqual(doc['_session']['engine'], 'Python')
        self.assertFalse(raw.startswith('﻿'))                # BOM なし

    def test_the_values_file_is_named_after_the_qmd(self):
        self.run_ok('ov_value("x", 1)', qmd='02-model.qmd')
        self.assertTrue((self.d / 'assets/values/02-model.json').is_file())

    def test_the_values_file_is_read_by_octavo(self):
        p = make_project(self.d / 'p', example=False)
        cfg = config.load(p / 'octavo.config.py')
        r = run_helper(p, 'ov_value("n_obs", 1523)\nov_value("coef_x", 0.34192)',
                       qmd='analysis.qmd')
        self.assertEqual(r.returncode, 0, r.stderr)
        vals, warn = values.load(cfg)
        self.assertEqual(warn, [])
        self.assertEqual(values.render(vals['n_obs'], '', cfg), '1,523')
        self.assertEqual(values.render(vals['coef_x'], '', cfg), '0.342')

    def test_a_bad_name_or_a_vector_is_refused(self):
        r = run_helper(self.d, 'ov_value("1bad", 1)')
        self.assertNotEqual(r.returncode, 0)
        r = run_helper(self.d, 'ov_value("many", [1, 2])')
        self.assertIn('値は1つだけ', r.stderr)

    def test_tables_are_contents_only_in_three_formats(self):
        self.run_ok('ov_table([["term", "est", "n"], ["x & y", 0.5, 10], ["z_1", 1.25, 20]],'
                    ' "summary", notes="注: 5%")')
        d = self.d / 'assets/tables'
        tex = (d / 'summary.tex').read_text(encoding='utf-8')
        typ = (d / 'summary.typ').read_text(encoding='utf-8')
        md_ = (d / 'summary.md').read_text(encoding='utf-8')
        self.assertIn(r'\toprule', tex)
        self.assertIn(r'x \& y & 0.500 & 10', tex)                # 小数は3桁、整数はそのまま
        self.assertNotIn(r'\caption', tex)                        # 表題は原稿が持つ
        self.assertIn(r'z\_1', typ)
        self.assertIn('align: (left, right, right)', typ)
        self.assertIn('table.hline(stroke: 0.5pt)', typ)
        self.assertIn('|:---|---:|---:|', md_)

    def test_a_ready_made_table_is_written_as_it_is(self):
        self.run_ok('ov_table({"tex": "\\\\begin{tabular}{l}x\\\\end{tabular}"}, "ready",'
                    ' formats=("tex",))')
        self.assertEqual((self.d / 'assets/tables/ready.tex').read_text(encoding='utf-8'),
                         '\\begin{tabular}{l}x\\end{tabular}\n')

    @unittest.skipUnless(HAVE_R, 'needs R')
    def test_tables_match_the_r_helper(self):
        """同じ表なら、R の ov_table() と Python の ov_table() は同じ中身を書く。"""
        self.run_ok('ov_table([["term", "est", "n"], ["x & y", 0.5, 10], ["z_1", 1.25, 20]],'
                    ' "t", notes="Note: 5%")')
        r_dir = self.d / 'r'
        r_dir.mkdir()
        code = ('source("%s")\nSys.setenv(OCTAVO_TABLE_DIR = "%s")\n'
                'tab <- data.frame(term = c("x & y", "z_1"), est = c(0.5, 1.25), n = c(10L, 20L))\n'
                'ov_table(tab, "t", notes = "Note: 5%%")\n'
                % ((paths.templates_dir() / 'analysis/common/analysis/octavo.R').as_posix(),
                   r_dir.as_posix()))
        r = subprocess.run(['Rscript', '-e', code], capture_output=True, text=True,
                           encoding='utf-8', env={**os.environ, 'OCTAVO_ROOT': str(self.d)})
        self.assertEqual(r.returncode, 0, r.stderr)
        for ext in ('tex', 'typ', 'md'):
            py = (self.d / 'assets/tables' / f't.{ext}').read_text(encoding='utf-8').split('\n', 1)[1]
            rr = (r_dir / f't.{ext}').read_text(encoding='utf-8').split('\n', 1)[1]
            self.assertEqual(py.strip(), rr.strip(), ext)

    def test_palette_and_tint(self):
        self.run_ok('assert ov_palette(3) == ["#0072B2", "#E69F00", "#009E73"]\n'
                    'assert ov_palette(["grey"]) == ["#999999"]\n'
                    'assert ov_tint("#000000", 1) == "#FFFFFF"\n'
                    'assert ov_tint("#0072B2", 0) == "#0072B2"\n')
        r = run_helper(self.d, 'ov_palette(9)')
        self.assertNotEqual(r.returncode, 0)

    def test_the_helper_has_no_third_party_import_at_the_top(self):
        tree = ast.parse(HELPER_PY.read_text(encoding='utf-8'))
        top = {n.module.split('.')[0] if isinstance(n, ast.ImportFrom) else a.name.split('.')[0]
               for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))
               for a in (n.names if isinstance(n, ast.Import) else [n])}
        self.assertLessEqual(top, set(sys.stdlib_module_names) | {'__future__'}
                             if hasattr(sys, 'stdlib_module_names') else top)


class PythonScaffold(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)

    def test_a_python_analysis_brings_the_python_helper_not_the_r_one(self):
        p = self.d / 'p'
        scaffold.init(p, lang='en', quiet=True)
        scaffold.new(p / 'octavo.config.py', 'analysis', 'model', quiet=True, engine='python')
        self.assertTrue((p / 'analysis/octavo_helper.py').is_file())
        self.assertFalse((p / 'analysis/octavo.R').exists())
        qmd = (p / 'analysis/model.qmd').read_text(encoding='utf-8')
        self.assertIn('```{python}', qmd)
        self.assertNotIn('```{r}', qmd)
        self.assertNotIn('@@', qmd)
        req = (p / 'requirements.txt').read_text(encoding='utf-8')
        for pkg in ('ipykernel', 'nbformat', 'nbclient', 'pyyaml'):
            self.assertIn(pkg, req.split())
        self.assertIn('<!-- octavo:section analysis-python -->',
                      (p / 'AGENTS.md').read_text(encoding='utf-8'))
        self.assertEqual(analysis.engine(p / 'analysis/model.qmd'), 'python')

    def test_r_and_python_can_live_in_one_project(self):
        p = self.d / 'p'
        scaffold.init(p, lang='ja', quiet=True)
        scaffold.new(p / 'octavo.config.py', 'analysis', 'a', quiet=True)
        scaffold.new(p / 'octavo.config.py', 'analysis', 'b', quiet=True, engine='python')
        self.assertTrue((p / 'analysis/octavo.R').is_file())
        self.assertTrue((p / 'analysis/octavo_helper.py').is_file())
        cfg = config.load(p / 'octavo.config.py')
        self.assertEqual(analysis.engines(cfg), {'r', 'python'})

    def test_requirements_are_added_once_and_names_already_there_are_kept(self):
        p = self.d / 'p'
        scaffold.init(p, lang='en', quiet=True)
        (p / 'requirements.txt').write_text('pandas==2.3.1\n', encoding='utf-8')
        cfg = p / 'octavo.config.py'
        scaffold.new(cfg, 'analysis', 'a', quiet=True, engine='python')
        scaffold.new(cfg, 'analysis', 'b', quiet=True, engine='python')
        lines = [ln for ln in (p / 'requirements.txt').read_text(encoding='utf-8').splitlines()
                 if ln.strip() and not ln.startswith('#')]
        self.assertEqual(sorted(lines), sorted(set(lines)))
        self.assertIn('pandas==2.3.1', lines)
        self.assertNotIn('pandas', lines)

    def test_the_examples_resolve_in_both_languages(self):
        for lang in ('ja', 'en'):
            p = self.d / lang
            scaffold.init(p, lang=lang, quiet=True, example=True,
                          parts={'analysis': 'analysis', 'paper': 'p'}, engine='python')
            qmd = (p / 'analysis/analysis.qmd').read_text(encoding='utf-8')
            self.assertIn('octavo:example', qmd)
            vals, _ = values.load(config.load(p / 'octavo.config.py'))
            self.assertTrue({'n_obs', 'coef_x', 'p_x'} <= set(vals))

    def test_an_unknown_engine_is_refused(self):
        p = self.d / 'p'
        scaffold.init(p, lang='en', quiet=True)
        with contextlib_redirect():
            self.assertEqual(scaffold.new(p / 'octavo.config.py', 'analysis', 'a',
                                          quiet=True, engine='julia'), 1)

    def test_engine_is_read_from_the_chunks(self):
        q = self.d / 'x.qmd'
        for text, want in (('```{r}\n1\n```\n', 'r'), ('```{python}\n1\n```\n', 'python'),
                           ('```{r}\n1\n```\n```{python}\n2\n```\n', 'r+python'),
                           ('---\njupyter: python3\n---\ntext\n', 'python'), ('text\n', 'r')):
            q.write_text(text, encoding='utf-8')
            self.assertEqual(analysis.engine(q), want, text)

    def test_env_is_pending_until_the_venv_exists_and_json_says_so(self):
        p = self.d / 'p'
        scaffold.init(p, lang='en', quiet=True)
        scaffold.new(p / 'octavo.config.py', 'analysis', 'a', quiet=True, engine='python')
        cfg = config.load(p / 'octavo.config.py')
        self.assertTrue(envsetup.pending(cfg))
        (p / '.venv').mkdir()
        self.assertFalse(envsetup.pending(cfg))       # Python だけなら renv は要らない
        scaffold.new(p / 'octavo.config.py', 'analysis', 'b', quiet=True)   # R の .qmd
        self.assertTrue(envsetup.pending(config.load(p / 'octavo.config.py')))

    def test_new_json_tells_the_extension_to_set_up_the_environment(self):
        p = self.d / 'p'
        scaffold.init(p, lang='en', quiet=True)
        from octavo import cli
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cli.main(['new', 'analysis', 'a', '--engine', 'python', '--json',
                      '-c', str(p / 'octavo.config.py')])
        res = json.loads(out.getvalue().strip().splitlines()[-1])
        self.assertTrue(res['ok'])
        self.assertTrue(res['env_needed'])
        self.assertTrue(res['open'].endswith('a.qmd'))

    def test_a_python_only_project_does_not_ask_for_r(self):
        p = self.d / 'p'
        scaffold.init(p, lang='en', quiet=True)
        scaffold.new(p / 'octavo.config.py', 'analysis', 'a', quiet=True, engine='python')
        cfg = config.load(p / 'octavo.config.py')
        with unittest.mock.patch.object(envsetup, 'python_env', return_value=True), \
                unittest.mock.patch.object(envsetup, 'r_env', return_value=True) as r_env, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(envsetup.run(cfg), 0)
        r_env.assert_not_called()


@unittest.skipUnless(HAVE_QUARTO and HAVE_UV, 'needs Quarto and uv')
class PythonAnalysisEndToEnd(unittest.TestCase):
    """**Python の .qmd を Quarto で実際に動かす**（`octavo env` で .venv を作るので、
    ネットワークも要る。つながらなければ飛ばす）。"""

    @classmethod
    def setUpClass(cls):
        cls.d = Path(tempfile.mkdtemp())
        p = cls.d / 'p'
        scaffold.init(p, lang='en', quiet=True, example=True,
                      parts={'analysis': 'analysis'}, engine='python')
        cls.cfg = config.load(p / 'octavo.config.py')
        (Path(cls.cfg['values_dir']) / 'analysis.json').unlink()      # .qmd が書いたかを見る
        for ext in ('.pdf', '.png'):
            (Path(cls.cfg['figure_dir']) / f'trend{ext}').unlink()
        with contextlib.redirect_stdout(io.StringIO()):
            rc = envsetup.run(cls.cfg)
        if rc != 0:
            raise unittest.SkipTest('could not set up .venv (offline?)')
        cls.report = []
        cls.ran, cls.ok = analysis.run(cls.cfg, force=True, report=cls.report)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def test_render_succeeded(self):
        self.assertTrue(self.ok, '\n'.join(self.report))

    def test_values_figure_and_table_were_written(self):
        vals, warn = values.load(self.cfg)
        self.assertEqual(warn, [])
        self.assertEqual(values.render(vals['n_obs'], '', self.cfg), '1,523')
        self.assertRegex(values.render(vals['coef_x'], '', self.cfg), r'^-?\d+\.\d{3}$')
        self.assertEqual(next(iter(values.session_info(self.cfg).values()))['engine'], 'Python')
        for ext in ('.pdf', '.png'):
            self.assertGreater((Path(self.cfg['figure_dir']) / f'trend{ext}').stat().st_size, 500)
        for ext in ('.tex', '.typ', '.md'):
            self.assertTrue((Path(self.cfg['table_dir']) / f'summary{ext}').is_file())


class ExtensionProjectForm(unittest.TestCase):
    """新しいプロジェクトの画面・同梱する拡張機能・サイドバーの空の状態。"""
    EXT = ROOT / 'vscode-extension'

    def manifest(self) -> dict:
        return json.loads((self.EXT / 'package.json').read_text(encoding='utf-8'))

    def test_the_companion_extensions_are_bundled_as_a_pack(self):
        pack = self.manifest()['extensionPack']
        self.assertEqual(sorted(p.lower() for p in pack),
                         ['ms-python.python', 'quarto.quarto', 'reditorsupport.r'])
        # Typst の拡張（tinymist）は入れない（利用者の指示）
        self.assertFalse([p for p in pack if 'tinymist' in p.lower() or 'typst' in p.lower()])
        # 必須の依存にはしない（外したい人が外せる）
        self.assertNotIn('extensionDependencies', self.manifest())

    def test_an_empty_sidebar_offers_a_new_project(self):
        welcome = self.manifest()['contributes']['viewsWelcome']
        self.assertTrue(any('octavo.init' in json.dumps(w) or w['contents'].startswith('%')
                            for w in welcome))
        nls = json.loads((self.EXT / 'package.nls.json').read_text(encoding='utf-8'))
        self.assertIn('command:octavo.init', nls['view.project.welcome'])
        for w in welcome:
            key = w['contents'].strip('%')
            self.assertIn(key, nls)
            self.assertIn(key, json.loads((self.EXT / 'package.nls.ja.json')
                                          .read_text(encoding='utf-8')))
        self.assertIn('return [];', (self.EXT / 'src/sidebar.ts').read_text(encoding='utf-8'))

    def test_every_id_the_form_script_uses_is_in_the_page(self):
        js = (self.EXT / 'media/project.js').read_text(encoding='utf-8')
        ts = (self.EXT / 'src/projectForm.ts').read_text(encoding='utf-8')
        for i in set(re.findall(r"\$\('([A-Za-z-]+)'\)", js)):
            if i.endswith('-'):
                continue
            self.assertRegex(ts, r'id="%s"' % re.escape(i), i)
        for p in ('analysis', 'paper', 'slides', 'lecture'):
            for pre in ('use-', 'name-', 'part-'):
                self.assertIn(f'id="{pre}${{id}}"', ts)
            self.assertIn(f"part('{p}'", ts)

    def test_the_form_builds_a_command_the_cli_accepts(self):
        """画面が組む引数（init <名前> --lang … --with … --engine python --example）を CLI が受ける。"""
        from octavo import cli
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        with contextlib.redirect_stdout(io.StringIO()):
            rc = cli.main(['init', str(d / 'x'), '--lang', 'en', '--with',
                           'analysis=model,paper,slides=talk', '--engine', 'python', '--example'])
        self.assertEqual(rc, 0)
        self.assertTrue((d / 'x/analysis/model.qmd').is_file())
        self.assertTrue((d / 'x/analysis/octavo_helper.py').is_file())
        self.assertTrue((d / 'x/docs/talk/talk.md').is_file())
        ts = (self.EXT / 'src/projectForm.ts').read_text(encoding='utf-8')
        for flag in ("'--lang'", "'--with'", "'--engine'", "'--example'"):
            self.assertIn(flag, ts)

    def test_every_id_the_preview_script_uses_is_in_its_page(self):
        js = (self.EXT / 'media/preview.js').read_text(encoding='utf-8')
        ts = (self.EXT / 'src/preview.ts').read_text(encoding='utf-8')
        for i in set(re.findall(r"getElementById\('([A-Za-z-]+)'\)", js)):
            self.assertRegex(ts, r'id="%s"' % re.escape(i), i)

    def test_following_the_cursor_and_the_qmd_preview_are_settings_that_can_be_turned_off(self):
        props = self.manifest()['contributes']['configuration']['properties']
        nls = json.loads((self.EXT / 'package.nls.json').read_text(encoding='utf-8'))
        ja = json.loads((self.EXT / 'package.nls.ja.json').read_text(encoding='utf-8'))
        for key in ('octavo.previewFollowCursor', 'octavo.qmdPreview'):
            self.assertIs(props[key]['default'], True)
            name = props[key]['description'].strip('%')
            self.assertIn(name, nls)
            self.assertIn(name, ja)
        # プレビュー側だけを自分でスクロールできる（スクロールそのものは奪わない）
        js = (self.EXT / 'media/preview.js').read_text(encoding='utf-8')
        self.assertNotIn("addEventListener('scroll'", js)
        # .qmd は保存しても組み直さない（見せるだけ）
        q = (self.EXT / 'src/qmdPreview.ts').read_text(encoding='utf-8')
        self.assertNotIn('onDidSaveTextDocument', q)
        self.assertNotIn('quarto render', q)

    def test_the_qmd_view_steps_aside_for_quarto_preview(self):
        q = (self.EXT / 'src/qmdPreview.ts').read_text(encoding='utf-8')
        self.assertIn("'Quarto Preview'", q)          # Quarto が開くターミナルの名前
        self.assertIn('quarto\\.previewView', q)     # その画面の viewType
        self.assertIn('quartoPreviewRunning()', q)

    def test_venv_activation_is_only_turned_off_for_r_projects_and_never_over_the_user(self):
        v = (self.EXT / 'src/venvActivation.ts').read_text(encoding='utf-8')
        for must in ("'.venv'", "'octavo.R'", 'ConfigurationTarget.WorkspaceFolder',
                     'globalValue', 'workspaceFolderValue', "vscode.l10n.t('Undo')"):
            self.assertIn(must, v)

    def test_adding_a_python_analysis_passes_the_engine_and_runs_the_env(self):
        ts = (self.EXT / 'src/scaffold.ts').read_text(encoding='utf-8')
        self.assertIn("flags.push('--engine', 'python')", ts)
        self.assertIn('report.env_needed', ts)


class DropReferences(unittest.TestCase):
    """参考文献節は「置き場所の印」だけを落とし、本文を消さない。"""

    def test_the_last_section_of_a_paper_is_dropped(self):
        src = '## Intro\n\nText.\n\n## References\n\n(dropped)\n'
        self.assertEqual(md.drop_references(src), '## Intro\n\nText.\n\n')

    def test_a_reading_list_inside_lecture_notes_keeps_the_rest(self):
        src = ('# S1\n\n### Slide\n\nA.\n\n### 参考文献\n\n- 山田 (2020)\n\n'
               '# S2\n\n### Slide B\n\nB.\n')
        out = md.drop_references(src)
        self.assertIn('# S2', out)
        self.assertIn('山田 (2020)', out)             # 読書案内は本文
        self.assertEqual([k for k, _ in md.section_keys(src)], ['01', '02'])

    def test_a_reading_list_in_the_last_session_is_kept(self):
        src = '# S1\n\n### Slide\n\nA.\n\n### 参考文献\n\n- 山田 (2020)\n'
        self.assertIn('山田 (2020)', md.drop_references(src))

    def test_a_placeholder_before_an_appendix_goes_but_the_appendix_stays(self):
        src = ('## Intro\n\nText.\n\n## References\n\n'
               '(This section is dropped at conversion time.)\n\n'
               '# Extra {.appendix}\n\n## Part {#sec-part}\n\nMore.\n')
        out = md.drop_references(src)
        self.assertNotIn('References', out)
        self.assertNotIn('dropped at conversion', out)
        self.assertIn('## Part {#sec-part}', out)
        self.assertEqual(out.count('\n'), src.count('\n'))   # 行の数は保つ

    def test_a_heading_inside_a_code_fence_is_not_a_section(self):
        src = '## Intro\n\n```\n## References\n```\n\nText after.\n'
        self.assertEqual(md.drop_references(src), src)


class AgentInstructions(unittest.TestCase):
    """プロジェクトの約束事は AGENTS.md（どの AI も読む）。CLAUDE.md はそれを指すだけ。"""

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.d, ignore_errors=True)

    def test_agents_md_is_the_source_and_claude_md_points_at_it(self):
        for lang in ('ja', 'en'):
            p = self.d / lang
            scaffold.init(p, lang=lang, quiet=True)
            scaffold.new(p / 'octavo.config.py', 'paper', 'p', quiet=True)
            self.assertIn('octavo:section common', (p / 'AGENTS.md').read_text(encoding='utf-8'))
            self.assertIn('octavo:section paper', (p / 'AGENTS.md').read_text(encoding='utf-8'))
            stub = (p / 'CLAUDE.md').read_text(encoding='utf-8')
            self.assertEqual(stub.splitlines()[0], '@AGENTS.md')
            self.assertNotIn('octavo:section', stub)            # 節は AGENTS.md だけに入る

    def test_with_agents_md_deleted_nothing_is_appended_to_the_one_line_claude_md(self):
        p = self.d / 'gone'
        scaffold.init(p, lang='en', quiet=True)
        stub = (p / 'CLAUDE.md').read_text(encoding='utf-8')
        (p / 'AGENTS.md').unlink()
        scaffold.new(p / 'octavo.config.py', 'paper', 'p', quiet=True)
        self.assertEqual((p / 'CLAUDE.md').read_text(encoding='utf-8'), stub)
        self.assertFalse((p / 'AGENTS.md').exists())
        moved, _ = scaffold.migrate_instructions(p, 'en', dry_run=True)
        self.assertFalse(moved)

    def test_a_project_from_before_still_gets_its_sections_in_claude_md(self):
        p = self.d / 'old'
        scaffold.init(p, lang='en', quiet=True)
        (p / 'AGENTS.md').unlink()
        (p / 'CLAUDE.md').write_text('# My rules\n\n<!-- octavo:section common -->\nold\n',
                                     encoding='utf-8')
        scaffold.new(p / 'octavo.config.py', 'slides', 's', quiet=True)
        self.assertFalse((p / 'AGENTS.md').exists())
        self.assertIn('octavo:section slides', (p / 'CLAUDE.md').read_text(encoding='utf-8'))

    def test_migrate_moves_the_rules_without_changing_them(self):
        """一時的な移行（この test ごと次の版で消す）。"""
        p = self.d / 'old'
        scaffold.init(p, lang='en', quiet=True)
        text = '# My rules\n\nmine, edited by hand\n'
        (p / 'AGENTS.md').unlink()
        (p / 'CLAUDE.md').write_text(text, encoding='utf-8')
        from octavo import cli
        with contextlib.redirect_stdout(io.StringIO()):
            cli.main(['migrate', '--dry-run', '-c', str(p / 'octavo.config.py')])
        self.assertFalse((p / 'AGENTS.md').exists())                 # 試しただけ
        with contextlib.redirect_stdout(io.StringIO()):
            cli.main(['migrate', '-c', str(p / 'octavo.config.py')])
        self.assertEqual((p / 'AGENTS.md').read_text(encoding='utf-8'), text)
        self.assertEqual((p / 'CLAUDE.md').read_text(encoding='utf-8').splitlines()[0], '@AGENTS.md')
        # 2回目は何もしない（AGENTS.md を上書きしない）
        (p / 'AGENTS.md').write_text('edited again\n', encoding='utf-8')
        with contextlib.redirect_stdout(io.StringIO()):
            cli.main(['migrate', '-c', str(p / 'octavo.config.py')])
        self.assertEqual((p / 'AGENTS.md').read_text(encoding='utf-8'), 'edited again\n')

    def test_the_sections_are_not_named_after_one_assistant(self):
        for lang in ('ja', 'en'):
            for f in (paths.templates_dir() / 'claude' / lang).glob('*.md'):
                if f.name == 'stub.md':
                    continue
                self.assertNotIn('Claude', f.read_text(encoding='utf-8'), f)


if __name__ == '__main__':
    unittest.main(verbosity=2)
