# -*- coding: utf-8 -*-
"""octavo — マークダウン草稿から LaTeX / Typst / Beamer / Word を作る。

使うのは CLI（`octavo`）から。ライブラリとして直接叩くこともできる:

    from octavo import config, build
    cfg = config.load('my-paper/octavo.config.py')
    build.run(cfg, targets=['latex', 'docx'])
"""

__version__ = '0.1.0'
