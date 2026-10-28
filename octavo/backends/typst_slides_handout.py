# -*- coding: utf-8 -*-
"""配布用のスライド（出力の名前 slides-handout）。

投影するスライド（typst-slides）と同じ原稿・同じ体裁で、中身だけを変える。
`.screen-only` で囲んだもの（穴埋めの答えなど）は投影するスライドにだけ出て、こちらには
出ない。`.no-screen` で囲んだもの（配布用の空欄など）はこちらにだけ出る。`.slides-only` は
どちらのスライドにも出る。ファイルは <名前>-handout.pdf（講義ノートの回は
<文書>-slides-handout-<回>.pdf）。build/slides-handout/ に出る（投影するスライドと分ける）。
"""
from __future__ import annotations

from .typst_slides import TypstSlidesBackend


class TypstSlidesHandoutBackend(TypstSlidesBackend):
    name = 'typst-slides-handout'
    label = 'Typst slides (handout)'
    on_screen = False
    session_tag = 'slides-handout'
    name_suffix = '-handout'
    # 参考文献の別紙は投影するスライドの側が作る（同じものを2つ作らない）
    makes_reference_sheet = False
