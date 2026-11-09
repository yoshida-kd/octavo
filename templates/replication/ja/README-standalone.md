# 再現用パッケージ — @@TITLE@@

このパッケージだけで、論文に載っている数値・図・表をもう一度作れる。必要なのは
[Quarto](https://quarto.org/) と、分析が使う R または Python のパッケージである。

## 中身

    analysis/       分析（Quarto の .qmd）
    data/           データ@@RAWNOTE@@
    data/HASHES.json  使ったデータのハッシュ値（sha256）
    assets/values/  論文に載せた数値と、そのときの実行環境の記録
    assets/figures/ assets/tables/  論文の図と表
    literature.bib    書誌
    renv.lock requirements.txt  使ったパッケージの版（ある場合）

## 環境を作る

@@SETUP@@

## もう一度実行する

このフォルダで:

@@RUN@@

コードの中のパスは、`.qmd` のあるフォルダから見た相対パスである。チャンクを1つずつ実行するときは、
作業フォルダを `analysis/` にする。

図は `assets/figures/` に、表は `assets/tables/` に CSV で書き出される。数値は HTML に
`名前: 値` の形で表示されるので、`assets/values/` の記録と比べられる。

## 実行環境

@@SESSION@@

## データのハッシュ値

`data/HASHES.json` に、そのとき使ったデータの sha256 が入っている。
