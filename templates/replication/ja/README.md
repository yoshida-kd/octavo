# 再現用パッケージ — @@TITLE@@

このパッケージだけで、論文に載っている数値・図・表をもう一度作れる。

## 中身

    analysis/       分析（Quarto の .qmd）とヘルパー octavo.R
    data/           データ@@RAWNOTE@@
    data/HASHES.json  使ったデータのハッシュ値（sha256）
    assets/values/  分析が出した数値（本文に入るもの）と実行環境の記録
    assets/figures/ assets/tables/  論文の図と表
    figures/        Typst で手で描いた図（<名前>.typ。あれば）
    octavo.config.py  設定
    literature.bib    書誌

## もう一度実行する

    quarto render analysis/*.qmd

あるいは [Octavo](https://github.com/yoshida-kd/octavo) があれば

    octavo analysis run --force
    octavo values --diff      # 前と同じ数字が出たか

## 実行環境

@@SESSION@@

## データのハッシュ値

`data/HASHES.json` に、そのとき使ったデータの sha256 が入っている。
手元のデータが同じものか確かめるには:

    octavo data status
