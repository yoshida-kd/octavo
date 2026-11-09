# Moves a colour towards white (p = 0 leaves it, p = 1 is white).
tint <- function(col, p = 0.6) {
  m <- grDevices::col2rgb(col) / 255
  m <- m + (1 - m) * p
  out <- grDevices::rgb(m[1, ], m[2, ], m[3, ])
  names(out) <- names(col)
  out
}
