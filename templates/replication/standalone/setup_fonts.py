# Keeps text as text in PDF figures, and uses a Japanese font if one is installed.
def setup_fonts():
    import matplotlib as mpl
    from matplotlib import font_manager
    mpl.rcParams["pdf.fonttype"] = 42
    mpl.rcParams["axes.unicode_minus"] = False
    have = {f.name for f in font_manager.fontManager.ttflist}
    wanted = ("BIZ UDGothic", "Noto Sans CJK JP", "Hiragino Sans", "Hiragino Kaku Gothic ProN",
              "Yu Gothic", "IPAexGothic", "TakaoPGothic", "VL Gothic")
    ja = [f for f in wanted if f in have]
    if ja:
        mpl.rcParams["font.sans-serif"] = ja + [f for f in mpl.rcParams["font.sans-serif"] if f not in ja]
        mpl.rcParams["font.family"] = "sans-serif"
