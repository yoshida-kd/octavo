<!-- octavo:section poster -->
# Posters

```
docs/<name>/<name>.md   a poster (outputs: [poster] at the top)
```

```bash
octavo build <name> --compile      # build/poster/<name>.pdf
```

- **Each top-level heading (`#`) is one cell.** By default the cells fill a 2×3 grid from the
  top left
- After a heading: `{span=2}` (two columns), `{rows=2}` (two rows), `{cell="2,3"}` (column 2, row 3)
- The paper and the grid are set at the top: `poster_size: a0` (a1, a2, b0, b1, or a size like
  `1189x841mm`), `poster_orientation: landscape`, `poster_grid: 3x2`, `poster_rows: [2, 1]`
  (the rows' height ratios)
- The title band shows `title`, `subtitle`, `author`, `institute`, `event`, `date`, `logo:`
  (image paths, any number), `qr:` (a URL, made into a QR code) and `qr_label:`
- Figures fit the room left in their cell. **Content that does not fit in its cell is reported
  as an overflow when you build** — cut the text or make the cell bigger (`span`, `rows`,
  `poster_rows`)
- The works you cite go in the last cell (`# References`)
- From a paper's manuscript: `outputs: [pdf, poster]` and `poster_select: marked`, and mark what
  goes on the poster with `.on-poster` (blocks, headings, `[…]{.on-poster}`)
