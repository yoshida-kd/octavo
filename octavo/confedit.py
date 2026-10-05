# -*- coding: utf-8 -*-
"""`octavo config` — 画面から変えられる設定の一覧と、その書き換え。

VS Code のアクティビティバーの「設定」はこれの薄い窓口（bib.ts と同じ方針）。
**どの鍵を画面に出すか・どう入力させるか・値として正しいか**は全部ここで決め、
拡張は `octavo config --json` の結果を並べて、選ばれた値を `octavo config set`
に渡すだけ。

`octavo.config.py` は手で書く Python なので、書き換えは慎重にやる:

  * 書き換えるのは `CONFIG = {` 直下（4字下げ）の **1行で書かれた** `'鍵': 値,`
    だけ。行末のコメントは残す。複数行にまたがる値は触らずに断る
  * なければ `CONFIG` の閉じ括弧の直前に1行足す（コメントアウトされた見本は
    そのまま残す）
  * 書く前に、書き換えた中身を**実際に設定として読んで**検証する。通らなければ
    ファイルは変えない（Config の検査がそのまま効く）
  * unset はその1行を消す（既定値に戻る）

ここにない鍵（documents・analysis・フォントの並びなど）は、構造が大きく画面で
選ばせる意味が薄いので、`octavo.config.py` を手で直す。

**文書ごとの設定**（`--doc NAME`）は、その原稿の冒頭（front matter）の1行を書き換える。
投稿先・発表ごとに変わるもの（CSL・投稿規定の上限・スライドの体裁・出力形式）だけで、
書かなければプロジェクトの設定が効く（config.DOC_KEYS / Config.for_document）。
"""
from __future__ import annotations

import ast
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from . import config as configmod
from .i18n import t


@dataclass(frozen=True)
class Knob:
    key: str
    section: str        # 'document' | 'slides' | 'limits'
    kind: str           # 'choice' | 'bool' | 'color' | 'int' | 'text' | 'suggest' | 'multi'
    label: str          # 英語の原文（表示は t() を通す）
    choices: tuple = ()  # choice / suggest / multi の選択肢。None は「使わない」
    docs: tuple = ()     # 原稿の冒頭で文書ごとに変えられる種類（profile）
    project: bool = True  # プロジェクトの設定として出すか
    least: int = 1        # int のときの最小値
    samples: tuple = ()   # choice の選択肢ごとの見本（選択肢と同じ順。画面で横に出す）


SLIDE_DOCS = ('slides', 'handout')      # 発表スライドと講義ノート（回ごとのスライド）
ALL_DOCS = ('paper', 'slides', 'handout', 'poster')

# 選ばせる CSL（よく使うもの）。ここにないものも名前を打てば使える（suggest）
CSL_CHOICES = ('chicago-author-date', 'apa', 'american-political-science-association',
               'american-sociological-association', 'modern-language-association',
               'chicago-note-bibliography', 'american-medical-association', 'ieee',
               'vancouver', 'nature')

# 画面に出す設定。**並びもこの順で出る。**
KNOBS = (
    Knob('lang', 'document', 'choice', 'Language of the documents', ('ja', 'en')),
    Knob('csl', 'document', 'suggest', 'Citation style (CSL)', CSL_CHOICES, docs=ALL_DOCS),
    Knob('outputs', 'document', 'multi', 'What to make', tuple(configmod.OUTPUTS),
         docs=ALL_DOCS, project=False),
    Knob('sessions', 'document', 'bool', 'Made of sessions (one deck each)',
         docs=ALL_DOCS, project=False),
    Knob('slides_select', 'slides', 'choice', 'What goes on the slides', ('all', 'marked'),
         docs=SLIDE_DOCS + ('paper',), project=False),
    Knob('slides_aspect', 'slides', 'choice', 'Aspect ratio', ('16-9', '4-3'),
         docs=SLIDE_DOCS),
    Knob('slides_accent', 'slides', 'color', 'Accent colour', docs=SLIDE_DOCS + ('poster',)),
    Knob('slides_running_header', 'slides', 'bool',
         'Section name in the top-left corner', docs=SLIDE_DOCS),
    Knob('slides_section_slides', 'slides', 'bool', 'Divider slide for each section',
         docs=SLIDE_DOCS),
    Knob('slides_numbering', 'slides', 'choice', 'Heading numbers',
         (None, '1.', '1.1'), docs=SLIDE_DOCS),
    Knob('citations_by_language', 'document', 'bool',
         'Japanese and English works in their own forms', docs=ALL_DOCS),
    Knob('japanese_citation_form', 'document', 'choice', 'Form of Japanese works',
         configmod.JA_FORMS, docs=ALL_DOCS,
         samples=('山田太郎・田中花子 (2020)「題」『誌名』12(3): 1–20.',
                  '山田太郎・田中花子（2020）「題」『誌名』12巻3号、1–20頁。',
                  '山田太郎・田中花子．2020．「題」『誌名』12巻3号、1–20頁。')),
    Knob('date_format', 'document', 'suggest', 'Date format',
         ('%Y年%-m月%-d日', '%Y-%m-%d', '%B %-d, %Y', '%-d %B %Y'), docs=('slides', 'handout')),
    Knob('first_section', 'handout', 'int', 'Number of the first section', docs=('handout',),
         least=0),
    Knob('toc', 'handout', 'bool', 'Table of contents', docs=('handout',), project=False),
    Knob('pagebreak', 'handout', 'choice', 'New page at',
         ('session', 'section', None), docs=('handout',)),
    Knob('font', 'handout', 'text', 'Body font', docs=('handout',)),
    Knob('fontsize', 'handout', 'choice', 'Font size',
         ('10pt', '10.5pt', '11pt', '12pt'), docs=('handout',)),
    Knob('poster_size', 'poster', 'suggest', 'Paper size', ('a0', 'a1', 'a2', 'b0', 'b1'),
         docs=('poster',)),
    Knob('poster_select', 'poster', 'choice', 'What goes on the poster', ('all', 'marked'),
         docs=('poster', 'paper', 'handout'), project=False),
    Knob('poster_orientation', 'poster', 'choice', 'Orientation', ('portrait', 'landscape'),
         docs=('poster',)),
    Knob('poster_grid', 'poster', 'suggest', 'Grid (columns x rows)', ('2x3', '3x2', '3x3', '2x4'),
         docs=('poster',)),
    Knob('word_limit', 'limits', 'int', 'Word limit (text)', docs=('paper',)),
    Knob('char_limit', 'limits', 'int', 'Character limit (text)', docs=('paper',)),
    Knob('abstract_word_limit', 'limits', 'int', 'Word limit (abstract)', docs=('paper',)),
    Knob('abstract_char_limit', 'limits', 'int', 'Character limit (abstract)',
         docs=('paper',)),
)
SECTIONS = {'document': 'Documents', 'handout': 'PDF (built-in layout)', 'slides': 'Slides',
            'limits': 'Submission limits', 'poster': 'Poster'}


class EditError(Exception):
    pass


def knob(key: str) -> Knob:
    # 前の名前: 出力の一覧は targets だった（前の拡張機能はこの名前で呼ぶ）
    key = {'targets': 'outputs'}.get(key, configmod.KEY_ALIASES.get(key, key))
    for k in KNOBS:
        if k.key == key:
            return k
    raise EditError(t('{key} cannot be changed from here — edit octavo.config.py',
                      key=key))


def parse_value(k: Knob, raw: str):
    """コマンド行の文字列を、その設定の型の値にする。

    `ast.literal_eval` に任せないのは、`16-9` が 7 になるから。
    """
    s = raw.strip()
    if s.lower() in ('none', 'null', ''):
        if k.kind in ('color', 'int') or (k.kind == 'choice' and None in k.choices):
            return None
        raise EditError(t('{key} cannot be empty', key=k.key))
    if k.kind == 'bool':
        if s.lower() in ('true', 'yes', 'on', '1'):
            return True
        if s.lower() in ('false', 'no', 'off', '0'):
            return False
        raise EditError(t('{key} takes true or false', key=k.key))
    if k.kind == 'int':
        try:
            n = int(s.replace(',', ''))
        except ValueError:
            raise EditError(t('{key} takes a whole number', key=k.key))
        if n < k.least:
            raise EditError(t('{key} takes a whole number', key=k.key))
        return n
    if k.kind == 'multi':
        got = [x.strip() for x in s.split(',') if x.strip()]
        if k.key == 'outputs':
            # 形式の名前（typst, docx）も出力の名前に直して受ける
            got = list(dict.fromkeys(configmod.OUTPUT_OF.get(x, x) for x in got))
        bad = [x for x in got if x not in k.choices]
        if bad or not got:
            raise EditError(t('{key} takes one or more of {allowed}', key=k.key,
                              allowed=' / '.join(k.choices)))
        return got
    if k.kind == 'choice' and s not in k.choices:
        shown = ' / '.join('None' if c is None else c for c in k.choices)
        raise EditError(t('{key} takes one of {allowed}', key=k.key, allowed=shown))
    return s


# ---------------------------------------------------------------- 読む
def show(cfg, doc=None) -> list:
    """画面に並べるもの。値は**効いている値**（既定を含む）。

    doc を渡すとその文書の設定: 文書の種類に合う鍵だけ、値は原稿の冒頭を重ねたもの、
    default はプロジェクトの値、explicit は原稿の冒頭に書いてあるか。
    """
    if doc is not None:
        view = cfg.for_document(doc)
        rows = []
        for k in KNOBS:
            if doc.profile not in k.docs:
                continue
            value, default = view.get(k.key), cfg.get(k.key)
            if k.key == 'outputs':
                value, default = list(doc.outputs), list(doc.config_outputs)
            elif k.key == 'sessions':
                value, default = bool(doc.sessions), False
            elif k.key == 'toc':
                # 書いていなければ回でできている文書だけ目次あり（組み込みの体裁の既定）
                value = bool(doc.sessions) if value is None else value
                default = bool(doc.sessions) if default is None else default
            rows.append({
                'key': k.key, 'section': k.section,
                'section_label': t(SECTIONS[k.section]),
                'label': t(k.label), 'kind': k.kind, 'choices': list(k.choices),
                'samples': list(k.samples),
                'value': value,
                'default': default,
                'explicit': k.key in view.doc_explicit
                or (k.key == 'outputs' and 'targets' in view.doc_explicit),
            })
        return rows
    rows = []
    for k in KNOBS:
        if not k.project:
            continue
        rows.append({
            'key': k.key,
            'section': k.section,
            'section_label': t(SECTIONS[k.section]),
            'label': t(k.label),
            'kind': k.kind,
            'choices': list(k.choices),
            'samples': list(k.samples),
            'value': cfg[k.key],
            'default': configmod.DEFAULTS.get(k.key),
            'explicit': k.key in cfg.explicit,
        })
    return rows


# ---------------------------------------------------------------- 書く
def _line_re(key: str):
    # CONFIG 直下（4字下げ）の 1行の代入。行末コメントは group 'tail' に残す
    return re.compile(r"^    (['\"])" + re.escape(key) + r"\1\s*:\s*(?P<val>.*?)\s*,"
                      r"(?P<tail>\s*#.*)?$", re.M)


def _edit_text(text: str, key: str, value, remove: bool = False) -> str:
    # 前の名前（typst_slides_accent など）で書いてある行は、今の名前に書き換えてから扱う。
    # そうしないと新しい名前の行が末尾に足され、同じ設定が2行になる
    for old in configmod.aliases_of(key):
        if not re.search(r"^    (['\"])" + re.escape(key) + r"\1\s*:", text, re.M):
            text = re.sub(r"^    (['\"])" + re.escape(old) + r"\1(\s*:)",
                          lambda m: f"    '{key}'{m.group(2)}", text, flags=re.M)
    m = _line_re(key).search(text)
    # 鍵の行はあるのに1行の形で読めない（値が次の行へ続く）なら、触らずに断る。
    # 見落とすと「書いていない」と判断して末尾にもう1つ足し、鍵が二重になる。
    head = re.search(r"^    (['\"])" + re.escape(key) + r"\1\s*:", text, re.M)
    if head and (not m or m.start() != head.start()):
        raise EditError(t('{key} spans several lines in octavo.config.py — edit it by '
                          'hand', key=key))
    if m:
        try:
            ast.literal_eval(m.group('val'))
        except (ValueError, SyntaxError):
            raise EditError(t('{key} spans several lines in octavo.config.py — edit it by '
                              'hand', key=key))
        if remove:
            start = m.start()
            end = text.find('\n', m.end())
            return text[:start] + (text[end + 1:] if end >= 0 else '')
        new = f"    '{key}': {value!r},{m.group('tail') or ''}"
        return text[:m.start()] + new + text[m.end():]
    if remove:
        return text                             # 書いていないなら既に既定
    # CONFIG の閉じ括弧（行頭の `}`）の直前に足す
    close = list(re.finditer(r'^\}\s*$', text, re.M))
    if not close:
        raise EditError(t('could not find the end of CONFIG in octavo.config.py'))
    at = close[-1].start()
    return text[:at] + f"    '{key}': {value!r},\n" + text[at:]


def _validate(path: Path, text: str) -> None:
    """書き換えた中身が設定として読めるかを、同じフォルダの一時ファイルで確かめる。"""
    fd, tmp = tempfile.mkstemp(prefix='.octavo-config-', suffix='.py', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            fh.write(text)
        try:
            configmod.load(tmp)
        except SystemExit as e:
            raise EditError(str(e.code) if e.code else t('the result is not a valid config'))
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


# ---------------------------------------------------------------- 原稿の冒頭
def _yaml_value(value) -> str:
    from . import md as mdlib
    if value is None:
        return 'none'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, int):
        return str(value)
    if isinstance(value, (list, tuple)):
        return '[' + ', '.join(str(x) for x in value) + ']'
    return mdlib._yq(value)


def _edit_front_matter(text: str, key: str, value, remove: bool = False) -> str:
    """冒頭の `鍵: 値` を1行だけ書き換える（なければ冒頭の最後に足す）。

    次の行へ続く値（`- …` の並びなど）は触らずに断る。冒頭がなければ作る。
    """
    from . import md as mdlib
    line = f'{key}: {_yaml_value(value)}'
    m = mdlib.FRONT_MATTER.match(text)
    if not m:
        return text if remove else f'---\n{line}\n---\n\n{text}'
    lines = m.group(1).split('\n')
    have = lambda k: next((i for i, l in enumerate(lines) if re.match(rf'{re.escape(k)}\s*:', l)), None)
    for old in configmod.aliases_of(key):
        i = have(old)
        if i is not None and have(key) is None:
            lines[i] = key + lines[i][len(old):]          # 前の名前の行を今の名前に
    at = have(key)
    if at is None:
        if remove:
            return text
        lines.append(line)
    else:
        nxt = lines[at + 1] if at + 1 < len(lines) else ''
        if nxt[:1].isspace() or nxt.lstrip().startswith('- '):
            raise EditError(t('{key} spans several lines in the manuscript — edit it by hand',
                              key=key))
        if remove:
            del lines[at]
        else:
            lines[at] = line
    return text[:m.start(1)] + '\n'.join(lines) + text[m.end(1):]


def set_doc_value(cfg, doc, key: str, raw: str | None) -> object:
    """文書ごとの設定を原稿の冒頭に書く。raw が None なら消す（プロジェクトの値に戻る）。"""
    k = knob(key)
    key = k.key
    if doc.profile not in k.docs:
        raise EditError(t('{key} cannot be set per document for this kind of manuscript',
                          key=key))
    src = Path(doc.src)
    text = src.read_text(encoding='utf-8')
    value = None if raw is None else parse_value(k, raw)
    new = _edit_front_matter(text, key, value, remove=raw is None)
    if key == 'outputs':
        # 前からの書き方（targets:）は outputs: に置き換える（両方あると紛らわしい）
        new = _edit_front_matter(new, 'targets', None, remove=True)
    if new == text:
        return value
    # 書く前に、書き換えた冒頭がその文書の設定として読めるかを確かめる
    import copy
    try:
        own = configmod.doc_settings(src, text=new)
        view = copy.copy(cfg)
        view._v = {**cfg._v, **own}
        view._validate()
    except SystemExit as e:
        raise EditError(str(e.code) if e.code else t('the result is not a valid config'))
    src.write_text(new, encoding='utf-8')
    return value


def set_value(path: Path, key: str, raw: str | None) -> object:
    """鍵を書き換える。raw が None なら消す（既定に戻す）。書いた値を返す。"""
    k = knob(key)
    key = k.key
    if not k.project:
        raise EditError(t('{key} is set per document — use --doc NAME', key=key))
    text = path.read_text(encoding='utf-8')
    if raw is None:
        new = _edit_text(text, key, None, remove=True)
        value = configmod.DEFAULTS.get(key)
    else:
        value = parse_value(k, raw)
        new = _edit_text(text, key, value)
    if new == text:
        return value
    _validate(path, new)
    path.write_text(new, encoding='utf-8')
    return value
