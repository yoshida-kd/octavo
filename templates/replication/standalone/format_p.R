# Writes a p-value the usual way: "< .001", ".042".
format_p <- function(p, digits = 3) {
  if (length(p) != 1L || is.na(p)) return("NA")
  cut <- 10^(-digits)
  if (p < cut) return(paste0("< ", sub("^0", "", formatC(cut, format = "f", digits = digits))))
  sub("^0", "", formatC(p, format = "f", digits = digits))
}
