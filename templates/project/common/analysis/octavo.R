# =====================================================================
#  Octavo — 分析（.qmd）から論文（.md）へ、数値・図・表を渡す。
#
#  使い方（.qmd の最初のチャンクで読み込む）:
#
#      root <- Sys.getenv("OCTAVO_ROOT", unset = "")
#      if (!nzchar(root)) root <- if (file.exists("octavo.R")) "." else ".."
#      source(file.path(root, "octavo.R"))
#
#  そのあと分析の中で:
#
#      ov_value("n_obs", nrow(d))                    -> 本文の {{n_obs}}
#      ov_value("coef_x", coef(m)[["x"]])        -> 本文の {{coef_x}}
#      ov_value("p_x", ov_pval(pv))                -> 本文の {{p_x}}
#      ov_figure(gg, "fig1_trend")                   -> figures/fig1_trend.{pdf,png}
#      ov_table(tab, "tbl1_summary", caption = "記述統計")
#                                                    -> tables/tbl1_summary.{tex,typ}
#
#  数値は results/<この .qmd の名前>.json に貯まる。octavo build が読んで
#  本文の {{…}} に差し込む。図は原稿に ![](figures/fig1_trend.png) と
#  **図1．説明** を書けば拾われ、表は octavo.config.py の table_map に
#  {'1': 'tbl1_summary'} と書けば差し込まれる。
#
#  **整数と小数を区別する。**R の整数（nrow() など）は桁区切り付きで
#  「1,523」、小数（coef() など）は既定 3 桁で「0.342」になる。書式を
#  決め打ちしたいときは ov_value(..., fmt = ".2f") か、本文側で
#  {{coef_x:.2f}} と書く。
#
#  外部パッケージには依存しない。ggplot2 は ov_figure() に ggplot を
#  渡したときだけ使う。表の LaTeX 出力は booktabs（\toprule 等）を使う
#  ので、main.tex 側で \usepackage{booktabs} が要る（同梱の main.tex
#  と pandoc の既定テンプレートは読み込み済み）。Typst の
#  表は table.hline() を使うので Typst 0.11 以上。
# =====================================================================

# ---------------------------------------------------------------- 置き場所

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

ov_dir <- function(kind = c("results", "figures", "tables")) {
  kind <- match.arg(kind)
  env <- c(results = "OCTAVO_RESULTS_DIR", figures = "OCTAVO_FIGURE_DIR",
           tables = "OCTAVO_TABLE_DIR")[[kind]]
  p <- Sys.getenv(env)
  if (!nzchar(p)) p <- file.path(ov_root(), kind)
  if (!dir.exists(p)) dir.create(p, recursive = TRUE, showWarnings = FALSE)
  p
}

# 値の書き出し先。既定は「この .qmd と同じ名前の .json」。1本の .qmd が
# 1つのファイルを持つので、複数の分析が同じファイルを取り合わない。
ov_values_file <- function() {
  name <- getOption("octavo.values", NULL)
  if (is.null(name)) {
    inp <- NULL
    if (requireNamespace("knitr", quietly = TRUE)) {
      inp <- tryCatch(knitr::current_input(), error = function(e) NULL)
    }
    name <- if (!is.null(inp) && nzchar(inp)) {
      tools::file_path_sans_ext(basename(inp))
    } else {
      "values"
    }
  }
  file.path(ov_dir("results"), paste0(name, ".json"))
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

# 整数はそのまま、小数は必ず小数点を付けて書く。JSON には整数と小数の
# 区別が無いので、「1523」と「1523.0」で Octavo 側の既定書式が変わる。
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


# ---------------------------------------------------------------- 数値

.ov_store <- new.env(parent = emptyenv())

#' 論文の本文に出す数値を1つ登録する。
#'
#' @param name 本文で {{name}} と書く名前
#' @param x    値（長さ1）。整数・小数・文字のいずれでもよい
#' @param fmt  Python の書式指定（".3f" 等）。省略なら Octavo 側の既定
#' @param note 覚え書き。octavo values で表示される
ov_value <- function(name, x, fmt = NULL, note = NULL) {
  if (!is.character(name) || length(name) != 1L || !nzchar(name)) {
    stop("ov_value: name は長さ1の文字列")
  }
  if (!grepl("^[A-Za-z_][A-Za-z0-9_.]*$", name)) {
    stop("ov_value: name は英字か _ で始め、英数字・_ ・. だけを使う（", name, "）")
  }
  if (length(x) != 1L) {
    stop("ov_value: 値は1つだけ渡す（", name, " は length ", length(x), "）")
  }
  path <- ov_values_file()
  store <- if (is.null(.ov_store[[path]])) list() else .ov_store[[path]]
  store[[name]] <- list(value = x, fmt = fmt, note = note)
  .ov_store[[path]] <- store
  ov_write_values(path, store)
  invisible(x)
}

#' 複数まとめて登録する。ov_values(n_obs = nrow(d), mean_x = mean(d$x))
ov_values <- function(...) {
  args <- list(...)
  nm <- names(args)
  if (is.null(nm) || any(!nzchar(nm))) stop("ov_values: 全部に名前を付ける")
  for (i in seq_along(args)) ov_value(nm[i], args[[i]])
  invisible(args)
}

# 再現性の記録。replication package を出すときに要る「何で走らせたか」を
# 値のファイルに一緒に残す。`_` で始まるキーは Octavo 側が値として扱わない。
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

#' p 値の慣例的な書き方。0.001 未満は "< .001"。
ov_pval <- function(p, digits = 3) {
  if (length(p) != 1L || is.na(p)) return("NA")
  cut <- 10^(-digits)
  if (p < cut) return(paste0("< ", sub("^0", "", formatC(cut, format = "f", digits = digits))))
  sub("^0", "", formatC(p, format = "f", digits = digits))
}


# ---------------------------------------------------------------- 図

ov_device <- function(path, fmt, width, height, dpi) {
  cairo <- isTRUE(capabilities("cairo"))
  if (fmt == "pdf") {
    if (cairo) grDevices::cairo_pdf(path, width = width, height = height)
    else grDevices::pdf(path, width = width, height = height)
  } else if (fmt == "png") {
    if (cairo) {
      grDevices::png(path, width = width * dpi, height = height * dpi,
                     res = dpi, type = "cairo")
    } else {
      grDevices::png(path, width = width * dpi, height = height * dpi, res = dpi)
    }
  } else if (fmt == "svg") {
    grDevices::svg(path, width = width, height = height)
  } else {
    stop("ov_figure: 知らない形式 ", fmt)
  }
}

#' 図を figures/ に保存する。既定で .pdf（LaTeX 用）と .png（Word・Typst 用）
#' の両方を書くので、octavo.config.py の figure_ext をそのまま使える。
#'
#' @param x      ggplot、あるいは「描画する関数」（base graphics）
#' @param name   ファイル名（拡張子なし）。原稿の ![](figures/<name>.png) と揃える
ov_figure <- function(x, name, width = 6, height = 4, dpi = 300,
                      formats = c("pdf", "png")) {
  dir <- ov_dir("figures")
  out <- character(0)
  is_gg <- inherits(x, "ggplot")
  if (is_gg && !requireNamespace("ggplot2", quietly = TRUE)) {
    stop("ov_figure: ggplot を渡すには ggplot2 が要る")
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


# ---------------------------------------------------------------- 表

ov_tex_escape <- function(s) {
  s <- as.character(s)
  # バックスラッシュを先に印に逃がす。そうしないと、この行が入れた
  # \textbackslash{} の波括弧を、下の { } のエスケープが二重に潰す。
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

# データフレームを「文字の行列」にする。小数は digits 桁に揃え、NA は空欄。
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

ov_tex_table <- function(cells, align, caption, notes, label) {
  head_row <- paste(paste0("\\textbf{", ov_tex_escape(colnames(cells)), "}"),
                    collapse = " & ")
  body <- apply(cells, 1, function(r) paste(ov_tex_escape(r), collapse = " & "))
  paste0(
    "% octavo.R の ov_table() が作ったファイル。手で直さない。\n",
    "\\begin{table}[htbp]\n\\centering\n",
    if (!is.null(caption)) paste0("\\caption{", ov_tex_escape(caption), "}\n") else "",
    "\\label{", label, "}\n",
    "\\begin{tabular}{", paste(align, collapse = ""), "}\n",
    "\\toprule\n", head_row, " \\\\\n\\midrule\n",
    paste(body, collapse = " \\\\\n"), " \\\\\n",
    "\\bottomrule\n\\end{tabular}\n",
    if (!is.null(notes)) {
      paste0("\\par\\vspace{2pt}\n{\\footnotesize ", ov_tex_escape(notes), "}\n")
    } else "",
    "\\end{table}\n")
}

ov_typ_table <- function(cells, align, caption, notes, label) {
  typ_align <- c(l = "left", r = "right", c = "center")[align]
  cell <- function(v) paste0("[", ov_typ_escape(v), "]")
  head_row <- paste(paste0("[*", ov_typ_escape(colnames(cells)), "*]"), collapse = ", ")
  body <- apply(cells, 1, function(r) paste0("    ", paste(vapply(r, cell, ""), collapse = ", "), ","))
  tbl <- paste0(
    "  table(\n",
    "    columns: ", ncol(cells), ",\n",
    "    align: (", paste(typ_align, collapse = ", "), "),\n",
    "    stroke: none,\n",
    "    table.hline(),\n",
    "    ", head_row, ",\n",
    "    table.hline(stroke: 0.5pt),\n",
    paste(body, collapse = "\n"), "\n",
    "    table.hline(),\n",
    "  )")
  inner <- if (is.null(notes)) {
    paste0("#figure(\n", tbl, ",\n")
  } else {
    paste0("#figure(\n  [\n  #", sub("^  ", "", tbl), "\n",
           "  #v(2pt)\n  #text(size: 8pt)[", ov_typ_escape(notes), "]\n  ],\n")
  }
  paste0(
    "// octavo.R の ov_table() が作ったファイル。手で直さない。\n",
    inner,
    if (!is.null(caption)) paste0("  caption: [", ov_typ_escape(caption), "],\n") else "",
    ") <", label, ">\n")
}

#' 表を tables/ に保存する（.tex と .typ）。octavo.config.py の table_map に
#' {'1': '<name>'} と書けば、本文の **表1．…** がこのファイルに差し替わる。
#'
#' @param x       data.frame / matrix、あるいは list(tex = "…", typ = "…")
#'                （modelsummary 等が作った文字列をそのまま渡すとき）
#' @param name    ファイル名（拡張子なし）
#' @param caption 表題
#' @param notes   表の下に小さく出す注
#' @param align   "lrrr" のように列ごとの寄せを決める。省略なら数値は右
ov_table <- function(x, name, caption = NULL, notes = NULL, align = NULL,
                     digits = 3, formats = c("tex", "typ")) {
  dir <- ov_dir("tables")
  out <- character(0)

  if (is.character(x) && length(x) == 1L) x <- list(tex = x)

  if (is.list(x) && !is.data.frame(x)) {
    if (is.null(names(x)) || any(!nzchar(names(x)))) {
      stop("ov_table: 出来合いの文字列を渡すときは list(tex = …, typ = …) の形にする")
    }
    for (fmt in names(x)) {
      path <- file.path(dir, paste0(name, ".", fmt))
      ov_write_lines(paste0(x[[fmt]], "\n"), path)
      out <- c(out, path)
    }
    missing <- setdiff(formats, names(x))
    if (length(missing)) {
      warning("ov_table: ", name, " に ", paste(missing, collapse = "/"),
              " が無い。その形式では本文のマークダウン表が使われる")
    }
    return(invisible(out))
  }

  cells <- ov_cells(x, digits)
  al <- ov_align(x, align)
  for (fmt in formats) {
    path <- file.path(dir, paste0(name, ".", fmt))
    txt <- if (fmt == "tex") {
      ov_tex_table(cells, al, caption, notes, paste0("tab:", name))
    } else if (fmt == "typ") {
      # Typst 側のラベルは**ファイル名そのもの**。Octavo の相互参照
      # （@tbl1_summary）がこの名前を指すため、変えないこと。
      ov_typ_table(cells, al, caption, notes, name)
    } else {
      stop("ov_table: 知らない形式 ", fmt)
    }
    ov_write_lines(txt, path)
    out <- c(out, path)
  }
  invisible(out)
}
