<!-- octavo:section poster -->
# ポスター

```
docs/<name>/<name>.md   ポスター（冒頭に outputs: [poster]）
```

```bash
octavo build <name> --compile      # build/poster/<name>.pdf
```

- **一番上の段の見出し（`#`）1つが1マス。**既定は2列×3行の格子に、左上から順に入る
- 見出しの後ろに `{span=2}`（2列ぶん）・`{rows=2}`（2行ぶん）・`{cell="2,3"}`（2列目の3行目）
- 冒頭で判型と格子を決める: `poster_size: a0`（a1・a2・b0・b1、`1189x841mm` のような寸法も）、
  `poster_orientation: landscape`、`poster_grid: 3x2`、`poster_rows: [2, 1]`（行の高さの比）
- 題の帯には `title`・`subtitle`・`author`・`institute`・`event`・`date`、`logo:`（画像のパス。
  いくつでも）、`qr:`（URL。QR コードになる）、`qr_label:`
- 図はマスの残りの高さに収まる。**マスに入りきらない中身は、組むと「はみ出し」と知らせる。**
  そのときは文を削るか、マスを大きくする（`span`・`rows`・`poster_rows`）
- 引いた文献は最後のマス（`# 参考文献`）に入る
- 論文の原稿から作るなら `outputs: [pdf, poster]` と `poster_select: marked`。ポスターに載せる所に
  `.on-poster` の印（囲み・見出し・`[…]{.on-poster}`）を付ける
