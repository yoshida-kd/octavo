# =====================================================================
#  Octavo — hands numbers, figures and tables from the analysis (.qmd) to the paper (.md).
#
#  Usage (load it in the first chunk of the .qmd):
#
#      source(if (file.exists("octavo.R")) "octavo.R" else file.path("analysis", "octavo.R"))
#
#  (Rendering works in analysis/; running a single chunk, with VS Code's Run Cell for
#   instance, works in the project's root. So it looks in both places.)
#
#  Then, in the analysis:
#
#      ov_value("n_obs", nrow(d))                    -> {{n_obs}} in the text
#      ov_value("coef_x", coef(m)[["x"]])        -> {{coef_x}} in the text
#      ov_value("p_x", ov_pval(pv))                -> {{p_x}} in the text
#      ov_figure(gg, "trend")                        -> assets/figures/trend.{pdf,png}
#      ov_table(tab, "summary")                      -> assets/tables/summary.{tex,typ,md}
#      ov_palette(3) / ov_tint(col) / ov_scale_colour_cud()   colourblind-safe colours
#
#  Numbers collect in assets/values/<name of this .qmd>.json. octavo build reads them into
#  the {{...}} of the text. A figure goes in with ![Trend](../../assets/figures/trend.png){#fig-trend}
#  in the manuscript, and a table with the line `: Summary {#tbl-summary}` where it belongs.
#  Captions and numbers belong to the manuscript (refer to them with @fig-trend / @tbl-summary).
#
#  **Integers and decimals are kept apart.** An R integer (nrow() and so on) shows with a
#  thousands separator, "1,523"; a decimal (coef() and so on) shows with 3 digits by default,
#  "0.342". To fix the format, use ov_value(..., fmt = ".2f") or write {{coef_x:.2f}} in the text.
#
#  It depends on no package. ggplot2 is used only when ov_figure() is given a ggplot. LaTeX
#  tables use booktabs (\toprule and so on), so main.tex needs \usepackage{booktabs} (the
#  bundled main.tex and pandoc's default template have it). Typst tables use table.hline(),
#  so Typst 0.11 or later.
# =====================================================================

# ---------------------------------------------------------------- locations

ov_root <- function() {
  e <- Sys.getenv("OCTAVO_ROOT")
  if (nzchar(e) && dir.exists(e)) return(normalizePath(e, winslash = "/"))
  d <- normalizePath(getwd(), winslash = "/")
  repeat {
    if (file.exists(file.path(d, "octavo.config.py"))) return(d)
    up <- dirname(d)
    if (identical(up, d)) break
    d <- up
  }
  normalizePath(getwd(), winslash = "/")
}

# Where to write. octavo passes it in environment variables (values_dir in octavo.config.py and
# so on). When Quarto renders directly, it is under the default place, assets/.
ov_dir <- function(kind = c("values", "figures", "tables")) {
  kind <- match.arg(kind)
  env <- c(values = "OCTAVO_VALUES_DIR", figures = "OCTAVO_FIGURE_DIR",
           tables = "OCTAVO_TABLE_DIR")[[kind]]
  p <- Sys.getenv(env)
  if (!nzchar(p)) p <- file.path(ov_root(), "assets", kind)
  if (!dir.exists(p)) dir.create(p, recursive = TRUE, showWarnings = FALSE)
  p
}

# Where values go: by default a .json named after this .qmd. Each .qmd has its own file, so
# analyses do not compete for one. When nothing is being rendered (a chunk was run on its own)
# there is no telling which .qmd this is, so it returns NULL and no value is written. Written to
# a file of another name, a trial value would sit beside the rendered one under the same name
# and could reach the text.
ov_values_file <- function() {
  name <- getOption("octavo.values", NULL)
  if (is.null(name)) {
    inp <- NULL
    if (requireNamespace("knitr", quietly = TRUE)) {
      inp <- tryCatch(knitr::current_input(), error = function(e) NULL)
    }
    if (is.null(inp) || !nzchar(inp)) return(NULL)
    name <- tools::file_path_sans_ext(basename(inp))
  }
  file.path(ov_dir("values"), paste0(name, ".json"))
}


# ---------------------------------------------------------------- JSON

ov_json_str <- function(s) {
  s <- enc2utf8(as.character(s))
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub("\"", "\\\"", s, fixed = TRUE)
  s <- gsub("\n", "\\n", s, fixed = TRUE)
  s <- gsub("\r", "\\r", s, fixed = TRUE)
  s <- gsub("\t", "\\t", s, fixed = TRUE)
  paste0("\"", s, "\"")
}

# Integers as they are, decimals always with a decimal point. JSON does not tell them apart, so
# "1523" and "1523.0" are how Octavo chooses its default format.
ov_json_scalar <- function(x) {
  if (is.null(x)) return("\"NA\"")
  if (length(x) == 1L && is.na(x)) return("\"NA\"")
  if (is.logical(x)) return(if (isTRUE(x)) "true" else "false")
  if (is.factor(x)) x <- as.character(x)
  if (is.character(x)) return(ov_json_str(x))
  if (is.integer(x)) return(format(x, scientific = FALSE, trim = TRUE))
  if (is.numeric(x)) {
    if (!is.finite(x)) return(ov_json_str(as.character(x)))
    s <- format(x, digits = 15, scientific = FALSE, trim = TRUE)
    if (!grepl("[.eE]", s)) s <- paste0(s, ".0")
    return(s)
  }
  ov_json_str(as.character(x))
}

ov_write_lines <- function(txt, path) {
  con <- file(path, open = "wb")
  on.exit(close(con), add = TRUE)
  writeBin(charToRaw(enc2utf8(txt)), con)
  invisible(path)
}


# ---------------------------------------------------------------- numbers

.ov_store <- new.env(parent = emptyenv())

#' Record one number for the text of the paper.
#'
#' @param name the name written {{name}} in the text
#' @param x    the value (length 1): an integer, a decimal or a string
#' @param fmt  a Python format (".3f" and so on). Left out, Octavo's default
#' @param note a memo, shown by octavo check values
ov_value <- function(name, x, fmt = NULL, note = NULL) {
  if (!is.character(name) || length(name) != 1L || !nzchar(name)) {
    stop("ov_value: name must be one string")
  }
  if (!grepl("^[A-Za-z_][A-Za-z0-9_.]*$", name)) {
    stop("ov_value: name must start with a letter or _ and use only letters, digits, _ and . (", name, ")")
  }
  if (length(x) != 1L) {
    stop("ov_value: pass exactly one value (", name, " has length ", length(x), ")")
  }
  path <- ov_values_file()
  if (is.null(path)) {
    message("ov_value: ", name, " = ", format(x),
            " (not recorded: this chunk was run on its own; render the .qmd to record it)")
    return(invisible(x))
  }
  store <- if (is.null(.ov_store[[path]])) list() else .ov_store[[path]]
  store[[name]] <- list(value = x, fmt = fmt, note = note)
  .ov_store[[path]] <- store
  ov_write_values(path, store)
  invisible(x)
}

#' Record several at once: ov_values(n_obs = nrow(d), mean_x = mean(d$x))
ov_values <- function(...) {
  args <- list(...)
  nm <- names(args)
  if (is.null(nm) || any(!nzchar(nm))) stop("ov_values: give every value a name")
  for (i in seq_along(args)) ov_value(nm[i], args[[i]])
  invisible(args)
}

# A record for reproducibility: what this ran on, kept in the values file for the replication
# package. Octavo does not treat keys starting with `_` as values.
ov_session <- function() {
  si <- utils::sessionInfo()
  pkgs <- c(si$otherPkgs, si$loadedOnly)
  vers <- character(0)
  for (n in names(pkgs)) vers[[n]] <- as.character(pkgs[[n]]$Version)
  list(engine = "R",
       version = paste(si$R.version$major, si$R.version$minor, sep = "."),
       platform = si$platform,
       at = format(Sys.time(), "%Y-%m-%d %H:%M:%S"),
       packages = vers)
}

ov_session_json <- function() {
  s <- ov_session()
  pk <- s$packages
  pk_json <- if (length(pk)) {
    paste0("{", paste(paste0(vapply(names(pk), ov_json_str, character(1)), ": ",
                             vapply(unname(pk), ov_json_str, character(1))),
                      collapse = ", "), "}")
  } else {
    "{}"
  }
  paste0("{\"engine\": ", ov_json_str(s$engine),
         ", \"version\": ", ov_json_str(s$version),
         ", \"platform\": ", ov_json_str(s$platform),
         ", \"at\": ", ov_json_str(s$at),
         ", \"packages\": ", pk_json, "}")
}

ov_write_values <- function(path, store) {
  items <- character(0)
  for (n in names(store)) {
    v <- store[[n]]
    parts <- paste0("\"value\": ", ov_json_scalar(v$value))
    if (!is.null(v$fmt))  parts <- c(parts, paste0("\"fmt\": ", ov_json_str(v$fmt)))
    if (!is.null(v$note)) parts <- c(parts, paste0("\"note\": ", ov_json_str(v$note)))
    items <- c(items, paste0("  ", ov_json_str(n), ": {",
                             paste(parts, collapse = ", "), "}"))
  }
  stamp <- c(paste0("  \"_generated\": ",
                    ov_json_str(format(Sys.time(), "%Y-%m-%d %H:%M:%S"))),
             paste0("  \"_session\": ", ov_session_json()))
  ov_write_lines(paste0("{\n", paste(c(stamp, items), collapse = ",\n"), "\n}\n"),
                 path)
}

#' The usual way to write a p value. Below 0.001 it is "< .001".
ov_pval <- function(p, digits = 3) {
  if (length(p) != 1L || is.na(p)) return("NA")
  cut <- 10^(-digits)
  if (p < cut) return(paste0("< ", sub("^0", "", formatC(cut, format = "f", digits = digits))))
  sub("^0", "", formatC(p, format = "f", digits = digits))
}


# ---------------------------------------------------------------- figures

ov_device <- function(path, fmt, width, height, dpi) {
  # On macOS, cairo in CRAN's R does not work without XQuartz. Use the system's quartz
  # (Japanese text comes out as it is)
  mac <- identical(Sys.info()[["sysname"]], "Darwin")
  cairo <- !mac && isTRUE(capabilities("cairo"))
  if (fmt == "pdf") {
    if (mac) grDevices::quartz(file = path, type = "pdf", width = width, height = height)
    else if (cairo) grDevices::cairo_pdf(path, width = width, height = height)
    else grDevices::pdf(path, width = width, height = height)
  } else if (fmt == "png") {
    if (mac) {
      grDevices::png(path, width = width * dpi, height = height * dpi,
                     res = dpi, type = "quartz")
    } else if (cairo) {
      grDevices::png(path, width = width * dpi, height = height * dpi,
                     res = dpi, type = "cairo")
    } else {
      grDevices::png(path, width = width * dpi, height = height * dpi, res = dpi)
    }
  } else if (fmt == "svg") {
    grDevices::svg(path, width = width, height = height)
  } else {
    stop("ov_figure: unknown format ", fmt)
  }
}

#' Save a figure in assets/figures/. By default it writes both .pdf (for Typst and LaTeX) and
#' .png (for Word), so figure_ext in octavo.config.py works as it is.
#'
#' @param x      a ggplot, or a function that draws (base graphics)
#' @param name   the file name, no extension. Match ![](assets/figures/<name>.png) in the manuscript
ov_figure <- function(x, name, width = 6, height = 4, dpi = 300,
                      formats = c("pdf", "png")) {
  dir <- ov_dir("figures")
  out <- character(0)
  is_gg <- inherits(x, "ggplot")
  if (is_gg && !requireNamespace("ggplot2", quietly = TRUE)) {
    stop("ov_figure: passing a ggplot needs ggplot2")
  }
  for (fmt in formats) {
    path <- file.path(dir, paste0(name, ".", fmt))
    if (is_gg) {
      dev <- if (fmt == "pdf" && isTRUE(capabilities("cairo"))) {
        grDevices::cairo_pdf
      } else {
        NULL
      }
      if (is.null(dev)) {
        ggplot2::ggsave(path, plot = x, width = width, height = height, dpi = dpi)
      } else {
        ggplot2::ggsave(path, plot = x, width = width, height = height,
                        dpi = dpi, device = dev)
      }
    } else {
      ov_device(path, fmt, width, height, dpi)
      tryCatch({
        if (is.function(x)) x() else print(x)
      }, finally = grDevices::dev.off())
    }
    out <- c(out, path)
  }
  invisible(out)
}


# ---------------------------------------------------------------- colours
# Colours that stay distinct for people with colour-vision differences: the 8 colours of
# Okabe & Ito (2008). The rules for making a figure:
#   1. Choose colours from here
#   2. Do not tell things apart by colour alone (write values or names in the figure; emphasise
#      with bold, line type or position as well)
#   3. Give neighbouring areas different lightness too. Lighten an area that carries text with ov_tint()
#   4. Do not put red next to green, or yellow next to white

ov_cud <- c(blue = "#0072B2", orange = "#E69F00", green = "#009E73",
            vermillion = "#D55E00", skyblue = "#56B4E9", purple = "#CC79A7",
            yellow = "#F0E442", grey = "#999999", black = "#000000")

#' The colours. Given n, that many (most distinct first); given names, those colours
#'
#'   ov_palette(3)                   # blue, orange, green
#'   ov_palette(c("blue", "grey"))
ov_palette <- function(n = NULL) {
  if (is.character(n)) {
    bad <- setdiff(n, names(ov_cud))
    if (length(bad)) stop("ov_palette: unknown colour ", paste(bad, collapse = ", "),
                          " (", paste(names(ov_cud), collapse = " / "), ")")
    return(ov_cud[n])
  }
  order <- c("blue", "orange", "green", "vermillion", "skyblue", "purple",
             "yellow", "grey")
  if (is.null(n)) return(ov_cud[order])
  if (n > length(order)) stop("ov_palette: at most ", length(order), " colours (beyond that, tell things apart ",
                              "by line type, shape or direct labels)")
  ov_cud[order[seq_len(n)]]
}

#' Lighten a colour (p = 0 leaves it, 1 makes it white), for an area that carries black text
ov_tint <- function(col, p = 0.6) {
  m <- grDevices::col2rgb(col) / 255
  m <- m + (1 - m) * p
  out <- grDevices::rgb(m[1, ], m[2, ], m[3, ])
  names(out) <- names(col)
  out
}

#' Use these colours for ggplot2's colour and fill (only when you use ggplot2)
#'
#'   ggplot(d, aes(x, y, colour = g)) + geom_line() + ov_scale_colour_cud()
ov_scale_colour_cud <- function(...) {
  ggplot2::scale_colour_manual(values = unname(ov_palette()), ...)
}
ov_scale_fill_cud <- function(...) {
  ggplot2::scale_fill_manual(values = unname(ov_palette()), ...)
}


# ---------------------------------------------------------------- tables

ov_tex_escape <- function(s) {
  s <- as.character(s)
  # Move backslashes out of the way first. Otherwise the escaping of { } below would escape
  # the braces of the \textbackslash{} this puts in.
  s <- gsub("\\", "\u0001", s, fixed = TRUE)
  for (ch in c("&", "%", "$", "#", "_", "{", "}")) {
    s <- gsub(ch, paste0("\\", ch), s, fixed = TRUE)
  }
  s <- gsub("~", "\\textasciitilde{}", s, fixed = TRUE)
  s <- gsub("^", "\\textasciicircum{}", s, fixed = TRUE)
  gsub("\u0001", "\\textbackslash{}", s, fixed = TRUE)
}

ov_typ_escape <- function(s) {
  s <- as.character(s)
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  for (ch in c("#", "$", "@", "[", "]", "<", ">", "*", "_")) {
    s <- gsub(ch, paste0("\\", ch), s, fixed = TRUE)
  }
  s
}

# A data frame as a matrix of strings. Decimals to digits places, NA left empty.
ov_cells <- function(x, digits) {
  x <- as.data.frame(x, stringsAsFactors = FALSE, check.names = FALSE)
  cols <- lapply(x, function(col) {
    if (is.numeric(col) && !is.integer(col)) {
      out <- formatC(col, format = "f", digits = digits)
    } else {
      out <- as.character(col)
    }
    out[is.na(col)] <- ""
    out
  })
  m <- do.call(cbind, lapply(cols, as.character))
  if (is.null(dim(m))) m <- matrix(m, nrow = nrow(x))
  colnames(m) <- names(x)
  m
}

ov_align <- function(x, align) {
  if (!is.null(align)) return(strsplit(align, "")[[1]])
  x <- as.data.frame(x, stringsAsFactors = FALSE, check.names = FALSE)
  vapply(x, function(col) if (is.numeric(col)) "r" else "l", character(1))
}

# Group headings: c(Demand = 1, Hiring = 6) puts Demand before row 1 and Hiring before row 6.
# list(Demand = 1, ...) works too. Returns list(at = row numbers, label = headings)
ov_groups <- function(groups, n) {
  if (is.null(groups) || length(groups) == 0L) return(NULL)
  at <- as.integer(unlist(groups))
  lab <- names(groups)
  if (is.null(lab) || any(!nzchar(lab))) {
    stop("ov_table: write groups as c(heading = first row), for example c(Demand = 1, Hiring = 6)")
  }
  if (any(is.na(at)) || any(at < 1L) || any(at > n)) {
    stop("ov_table: rows in groups must be from 1 to ", n, " (the heading goes before that row)")
  }
  o <- order(at)
  list(at = at[o], label = lab[o])
}

# For each row, its group heading (if one goes before it) and whether to indent it
ov_row_plan <- function(n, grp, indent) {
  head <- rep(NA_character_, n)
  if (!is.null(grp)) head[grp$at] <- grp$label
  if (is.null(indent)) indent <- !is.null(grp)
  # Rows before the first group are not indented
  inside <- if (is.null(grp)) rep(FALSE, n) else seq_len(n) >= min(grp$at)
  list(head = head, indent = isTRUE(indent) & inside)
}

# Writes **only the contents** of the table. The caption and the label (#tbl-<name>) belong to
# the manuscript's `: Caption {#tbl-<name>}`, and Octavo wraps them around it when typesetting.
ov_tex_table <- function(cells, align, notes, plan, size) {
  nc <- ncol(cells)
  cn <- colnames(cells)
  head_row <- paste(ifelse(nzchar(cn), paste0("\\textbf{", ov_tex_escape(cn), "}"), ""),
                    collapse = " & ")
  rows <- character(0)
  for (i in seq_len(nrow(cells))) {
    if (!is.na(plan$head[i])) {
      rows <- c(rows, paste0("\\multicolumn{", nc, "}{l}{\\textbf{",
                             ov_tex_escape(plan$head[i]), "}} \\\\"))
    }
    r <- ov_tex_escape(cells[i, ])
    if (plan$indent[i]) r[1] <- paste0("\\hspace{1em}", r[1])
    rows <- c(rows, paste0(paste(r, collapse = " & "), " \\\\"))
  }
  tab <- paste0(
    "\\begin{tabular}{", paste(align, collapse = ""), "}\n",
    "\\toprule\n", head_row, " \\\\\n\\midrule\n",
    paste(rows, collapse = "\n"), "\n",
    "\\bottomrule\n\\end{tabular}\n")
  if (!is.null(size)) tab <- paste0("{\\fontsize{", size, "}{", round(size * 1.2, 2),
                                    "}\\selectfont\n", tab, "}\n")
  paste0(
    "% Written by ov_table() in octavo.R. Do not edit by hand.\n", tab,
    if (!is.null(notes)) {
      paste0("\\par\\vspace{2pt}\n{\\footnotesize ", ov_tex_escape(notes), "}\n")
    } else "")
}

ov_typ_table <- function(cells, align, notes, plan, size) {
  nc <- ncol(cells)
  typ_align <- c(l = "left", r = "right", c = "center")[align]
  cell <- function(v) paste0("[", ov_typ_escape(v), "]")
  cn <- colnames(cells)
  # A column with no heading (the row names) gets []. Typst warns about [**]
  head_row <- paste(ifelse(nzchar(cn), paste0("[*", ov_typ_escape(cn), "*]"), "[]"),
                    collapse = ", ")
  body <- character(0)
  for (i in seq_len(nrow(cells))) {
    if (!is.na(plan$head[i])) {
      body <- c(body, paste0("  table.cell(colspan: ", nc, ", align: left)[*",
                             ov_typ_escape(plan$head[i]), "*],"))
    }
    r <- vapply(cells[i, ], cell, "")
    if (plan$indent[i]) r[1] <- sub("^\\[", "[#h(1em)", r[1])
    body <- c(body, paste0("  ", paste(r, collapse = ", "), ","))
  }
  tbl <- paste0(
    "#table(\n",
    "  columns: ", nc, ",\n",
    "  align: (", paste(typ_align, collapse = ", "), "),\n",
    "  stroke: none,\n",
    "  table.hline(),\n",
    "  ", head_row, ",\n",
    "  table.hline(stroke: 0.5pt),\n",
    paste(body, collapse = "\n"), "\n",
    "  table.hline(),\n",
    ")\n")
  # Keep the text's justification out of the cells. The type size is size (pt)
  paste0(
    "// Written by ov_table() in octavo.R. Do not edit by hand.\n",
    "#set par(justify: false)\n",
    if (!is.null(size)) paste0("#set text(size: ", size, "pt)\n") else "",
    tbl,
    if (!is.null(notes)) {
      paste0("#v(2pt)\n#block(width: 100%, align(left, text(size: ",
             if (is.null(size)) 8 else round(size * 0.85, 2), "pt)[", ov_typ_escape(notes), "]))\n")
    } else "")
}

# For Word (Octavo puts it in as a table of the text). | in a cell is escaped. A Markdown table
# cannot span columns, so a group heading is a row with the heading in bold in the first column
ov_md_table <- function(cells, align, notes, plan, size) {
  nc <- ncol(cells)
  esc <- function(v) gsub("|", "\\|", v, fixed = TRUE)
  rule <- c(l = ":---", r = "---:", c = ":---:")[align]
  row <- function(v) paste0("| ", paste(esc(v), collapse = " | "), " |")
  rows <- character(0)
  for (i in seq_len(nrow(cells))) {
    if (!is.na(plan$head[i])) rows <- c(rows, row(c(paste0("**", plan$head[i], "**"), rep("", nc - 1L))))
    r <- cells[i, ]
    if (plan$indent[i]) r[1] <- paste0("\u00a0\u00a0", r[1])
    rows <- c(rows, row(r))
  }
  paste0(
    "<!-- Written by ov_table() in octavo.R. Do not edit by hand. -->\n\n",
    row(colnames(cells)), "\n",
    "|", paste(rule, collapse = "|"), "|\n",
    paste(rows, collapse = "\n"), "\n",
    if (!is.null(notes)) paste0("\n*", notes, "*\n") else "")
}

#' Save a table in assets/tables/ (.tex, .typ and .md, read by LaTeX, Typst and Word).
#' Write the line `: Caption {#tbl-<name>}` in the text and Octavo puts it there, and
#' @tbl-<name> refers to it. The caption belongs to the text (none is added here).
#'
#' @param x       a data.frame or matrix, or list(tex = "...", typ = "...", md = "...")
#'                (for strings made by modelsummary and the like, passed as they are)
#' @param name    the file name, no extension
#' @param notes   a note in small type under the table (left-aligned)
#' @param align   the alignment of each column, like "lrrr". Left out, numbers go right
#' @param groups  group headings. c(Demand = 1, Hiring = 6) puts Demand before row 1 and Hiring
#'                before row 6, as bold rows across the columns
#' @param indent  whether to indent the first column of rows under a group. Left out, TRUE if
#'                there are groups
#' @param size    the type size in pt (9.5, say). Left out, the same as the text
ov_table <- function(x, name, notes = NULL, align = NULL,
                     digits = 3, formats = c("tex", "typ", "md"),
                     groups = NULL, indent = NULL, size = NULL) {
  dir <- ov_dir("tables")
  out <- character(0)

  if (is.character(x) && length(x) == 1L) x <- list(tex = x)

  if (is.list(x) && !is.data.frame(x)) {
    if (is.null(names(x)) || any(!nzchar(names(x)))) {
      stop("ov_table: pass ready-made strings as list(tex = ..., typ = ..., md = ...)")
    }
    for (fmt in names(x)) {
      path <- file.path(dir, paste0(name, ".", fmt))
      ov_write_lines(paste0(x[[fmt]], "\n"), path)
      out <- c(out, path)
    }
    missing <- setdiff(formats, names(x))
    if (length(missing)) {
      warning("ov_table: ", name, " has no ", paste(missing, collapse = "/"),
              ", so the table will not appear in that format")
    }
    return(invisible(out))
  }

  cells <- ov_cells(x, digits)
  al <- ov_align(x, align)
  plan <- ov_row_plan(nrow(cells), ov_groups(groups, nrow(cells)), indent)
  for (fmt in formats) {
    path <- file.path(dir, paste0(name, ".", fmt))
    txt <- if (fmt == "tex") {
      ov_tex_table(cells, al, notes, plan, size)
    } else if (fmt == "typ") {
      ov_typ_table(cells, al, notes, plan, size)
    } else if (fmt == "md") {
      ov_md_table(cells, al, notes, plan, size)
    } else {
      stop("ov_table: unknown format ", fmt)
    }
    ov_write_lines(txt, path)
    out <- c(out, path)
  }
  invisible(out)
}
