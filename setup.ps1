# =====================================================================
#  octavo を Windows で動かすための導入（winget）。Linux / macOS は setup.sh。
#  Installs what octavo needs on Windows (winget). Linux / macOS: setup.sh.
#
#    powershell -ExecutionPolicy Bypass -File setup.ps1
#        ふだん使う一式 / the everyday set:
#        pandoc, Typst, quarto, fonts, R (CRAN), renv, uv, octavo
#    -NoQuarto               quarto を入れない / leave out quarto
#    -NoR                    R を入れない / leave out R
#    -OctavoVersion X        octavo を PyPI の X で入れる / install octavo X from PyPI
#    -Check                  何を入れるか見るだけ / only show what would be done
#
#  Windows は Linux・macOS の次の扱い。TeX（LaTeX / Beamer）はここでは入れない。
#  Windows comes after Linux and macOS. TeX (LaTeX / Beamer) is not installed here.
#  VS Code の拡張機能の「準備する」も、`octavo setup` も、これを走らせる。
#  同じことを何度走らせても平気 / Safe to run again: what is there is skipped.
# =====================================================================
param(
    [switch]$NoQuarto,
    [switch]$NoR,
    [string]$OctavoVersion = '',
    [switch]$Check
)
$ErrorActionPreference = 'Continue'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 動作を確かめた版（setup.sh と同じ数字にそろえる。テストが見張っている）
$PANDOC_VER = '3.11'
$TYPST_VER = '0.15.1'
$QUARTO_VER = '1.10.18'
$UV_VER = '0.12.18'
# R は版を固定しない（CRAN の最新）。パッケージはプロジェクトごとに renv で持つ。

$lang = if ($env:OCTAVO_LANG) { $env:OCTAVO_LANG } else { (Get-Culture).Name }
$JA = $lang -like 'ja*'
function M([string]$ja, [string]$en) { if ($JA) { $ja } else { $en } }
function Say([string]$ja, [string]$en) { Write-Host ''; Write-Host ('== ' + (M $ja $en)) -ForegroundColor Cyan }
function Info([string]$ja, [string]$en) { Write-Host ('   ' + (M $ja $en)) }

$BIN = Join-Path $HOME '.local\bin'

# winget や uv が PATH を書き換えても、このプロセスには届かない。登録簿から読み直す。
function Update-Path {
    $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = "$BIN;$machine;$user"
}

function Version-Of([string]$cmd, [string[]]$arg) {
    $exe = Get-Command $cmd -ErrorAction SilentlyContinue
    if (-not $exe) { return $null }
    # Rscript --version は標準エラーに出すので、そちらも読む
    $out = (& $exe.Source @arg 2>&1 | Select-Object -First 1 | Out-String)
    if ($out -match '(\d+(\.\d+)+)') { return [version]($Matches[1]) }
    return $null
}

# winget-Install <コマンド> <版の引数> <winget の ID> <固定の版（空なら最新）>
function Winget-Install([string]$cmd, [string[]]$arg, [string]$id, [string]$want) {
    $have = Version-Of $cmd $arg
    if ($have -and (-not $want -or $have -ge [version]$want)) {
        Info "入っている: $cmd $have" "installed: $cmd $have"
        return
    }
    if ($have) { Info "いまの $have は動作を確かめた $want より古いので入れ直す" "$have is older than the tested $want, reinstalling" }
    $wargs = @('install', '--id', $id, '--exact', '--silent',
               '--accept-package-agreements', '--accept-source-agreements')
    if ($want) { $wargs += @('--version', $want) }
    if ($Check) { Info "(実行しない) winget $($wargs -join ' ')" "(not run) winget $($wargs -join ' ')"; return }
    & winget @wargs
    if ($LASTEXITCODE -ne 0) {
        Info "入らなかった（後で winget install --id $id）" "failed (later: winget install --id $id)"
    }
    Update-Path
}

# ---------------------------------------------------------------------
Say '環境' 'System'
Write-Host "   Windows $([Environment]::OSVersion.Version)  ($env:PROCESSOR_ARCHITECTURE)"
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Info 'winget が無い。Microsoft Store の「アプリ インストーラー」を入れてから、もう一度走らせること' `
         'winget is missing. Install "App Installer" from the Microsoft Store, then run this again'
    exit 1
}
Info 'インストーラーが管理者の許可を求めることがある（R・quarto）' `
     'Some installers ask for administrator permission (R, quarto)'
Update-Path

# ---------------------------------------------------------------------
Say 'pandoc' 'pandoc'
Winget-Install 'pandoc' @('--version') 'JohnMacFarlane.Pandoc' $PANDOC_VER

Say 'Typst' 'Typst'
Winget-Install 'typst' @('--version') 'Typst.Typst' $TYPST_VER

if (-not $NoQuarto) {
    Say 'quarto' 'quarto'
    Winget-Install 'quarto' @('--version') 'Posit.Quarto' $QUARTO_VER
}

# ---------------------------------------------------------------------
# 既定の書体（octavo/backends/typst.py の FONTS）。Windows にも BIZ UD は入っているが
# 名前が違う（「BIZ UDMincho Medium」）ので、Linux・Mac と同じ名前の Google Fonts 版を
# 利用者のフォントとして入れる（管理者は要らない）。無くても游明朝・游ゴシックに落ちる。
Say 'フォント' 'Fonts'
$FONT_DIR = Join-Path $env:LOCALAPPDATA 'Microsoft\Windows\Fonts'
$FONT_REG = 'HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Fonts'
$GF = 'https://raw.githubusercontent.com/google/fonts/main/ofl'
$fonts = @(
    @{ File = 'BIZUDMincho-Regular.ttf'; Name = 'BIZ UDMincho (TrueType)'; Url = "$GF/bizudmincho/BIZUDMincho-Regular.ttf" },
    @{ File = 'BIZUDMincho-Bold.ttf'; Name = 'BIZ UDMincho Bold (TrueType)'; Url = "$GF/bizudmincho/BIZUDMincho-Bold.ttf" },
    @{ File = 'BIZUDGothic-Regular.ttf'; Name = 'BIZ UDGothic (TrueType)'; Url = "$GF/bizudgothic/BIZUDGothic-Regular.ttf" },
    @{ File = 'BIZUDGothic-Bold.ttf'; Name = 'BIZ UDGothic Bold (TrueType)'; Url = "$GF/bizudgothic/BIZUDGothic-Bold.ttf" }
)
$interNeeded = -not (Test-Path (Join-Path $FONT_DIR 'Inter-Regular.ttf'))
if (-not $Check) {
    New-Item -ItemType Directory -Force -Path $FONT_DIR | Out-Null
    if (-not (Test-Path $FONT_REG)) { New-Item -Path $FONT_REG -Force | Out-Null }
}
foreach ($f in $fonts) {
    $dest = Join-Path $FONT_DIR $f.File
    if (Test-Path $dest) { Info "入っている: $($f.File)" "installed: $($f.File)"; continue }
    if ($Check) { Info "(実行しない) $($f.Url)" "(not run) $($f.Url)"; continue }
    try {
        Invoke-WebRequest -UseBasicParsing -Uri $f.Url -OutFile $dest
        New-ItemProperty -Path $FONT_REG -Name $f.Name -Value $dest -PropertyType String -Force | Out-Null
        Info "入れた: $($f.File)" "installed: $($f.File)"
    } catch {
        Info "取れなかった: $($f.File)（游明朝・游ゴシックで組む）" "could not fetch $($f.File) (Yu Mincho / Yu Gothic is used)"
    }
}
if ($interNeeded) {
    $url = 'https://github.com/rsms/inter/releases/download/v4.1/Inter-4.1.zip'
    if ($Check) {
        Info "(実行しない) $url" "(not run) $url"
    } else {
        try {
            $tmp = Join-Path ([IO.Path]::GetTempPath()) ('octavo-inter-' + [guid]::NewGuid())
            New-Item -ItemType Directory -Force -Path $tmp | Out-Null
            Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile (Join-Path $tmp 'inter.zip')
            Expand-Archive -Path (Join-Path $tmp 'inter.zip') -DestinationPath $tmp -Force
            foreach ($style in 'Regular', 'Bold', 'Italic', 'BoldItalic') {
                $file = "Inter-$style.ttf"
                $dest = Join-Path $FONT_DIR $file
                Copy-Item (Join-Path $tmp "extras\ttf\$file") $dest -Force
                New-ItemProperty -Path $FONT_REG -Name "Inter $style (TrueType)" -Value $dest -PropertyType String -Force | Out-Null
            }
            Remove-Item -Recurse -Force $tmp
            Info '入れた: Inter' 'installed: Inter'
        } catch {
            Info '取れなかった: Inter（Typst の既定の書体で組む）' 'could not fetch Inter (a fallback font is used)'
        }
    }
} else {
    Info '入っている: Inter' 'installed: Inter'
}

# ---------------------------------------------------------------------
# R は CRAN の Windows 版の最新。パッケージは CRAN のビルド済みがそのまま使えるので、
# Linux のような取得先の設定は要らない。R のインストーラーは PATH に足さないので、
# 利用者の PATH に bin を足す（octavo doctor と octavo env が Rscript を見つけられるように）。
function Add-RToPath {
    if (Get-Command Rscript -ErrorAction SilentlyContinue) { return }
    $rbin = Get-ChildItem (Join-Path $env:ProgramFiles 'R') -Directory -ErrorAction SilentlyContinue |
            Sort-Object { [version](($_.Name -replace '^R-', '') -replace '[^\d.]', '') } |
            Select-Object -Last 1 | ForEach-Object { Join-Path $_.FullName 'bin' }
    if ($rbin -and (Test-Path (Join-Path $rbin 'Rscript.exe')) -and -not $Check) {
        $user = [Environment]::GetEnvironmentVariable('Path', 'User')
        [Environment]::SetEnvironmentVariable('Path', ($user.TrimEnd(';') + ";$rbin").TrimStart(';'), 'User')
        Update-Path
        Info "R を利用者の PATH に足した: $rbin" "added R to your PATH: $rbin"
    }
}

if (-not $NoR) {
    Say 'R（CRAN の最新）' 'R (latest from CRAN)'
    Add-RToPath          # 入っているのに PATH に無いだけなら、入れ直さない
    Winget-Install 'Rscript' @('--version') 'RProject.R' ''
    Add-RToPath
    if ((Get-Command Rscript -ErrorAction SilentlyContinue) -and -not $Check) {
        Say 'renv' 'renv'
        # 複数行を引数で渡すと Windows PowerShell が中の " を崩すので、ファイルにして渡す
        $rfile = Join-Path ([IO.Path]::GetTempPath()) 'octavo-renv.R'
        Set-Content -Path $rfile -Encoding ASCII -Value @'
if (requireNamespace("renv", quietly = TRUE)) {
  cat("   installed: renv", as.character(packageVersion("renv")), "\n")
} else {
  lib <- Sys.getenv("R_LIBS_USER")
  dir.create(lib, recursive = TRUE, showWarnings = FALSE)
  install.packages("renv", lib = lib, repos = "https://cloud.r-project.org")
}
'@
        & Rscript $rfile
        Remove-Item $rfile -ErrorAction SilentlyContinue
    }
}

# ---------------------------------------------------------------------
# uv: プロジェクトの .venv を作り（octavo env）、octavo 本体も入れる。~/.local/bin に入る。
Say 'uv' 'uv'
$uvv = Version-Of 'uv' @('--version')
if ($uvv -and $uvv -ge [version]$UV_VER) {
    Info "入っている: uv $uvv" "installed: uv $uvv"
} elseif ($Check) {
    Info "(実行しない) irm https://astral.sh/uv/$UV_VER/install.ps1 | iex" "(not run) irm https://astral.sh/uv/$UV_VER/install.ps1 | iex"
} else {
    $env:UV_NO_MODIFY_PATH = '1'
    try {
        Invoke-RestMethod "https://astral.sh/uv/$UV_VER/install.ps1" | Invoke-Expression
    } catch {
        Info '取得できなかった。https://docs.astral.sh/uv/ から手で' 'download failed. Install it by hand: https://docs.astral.sh/uv/'
    }
    Update-Path
}

# ---------------------------------------------------------------------
# octavo 本体（PyPI の octavo-kit）。~/.local/bin を利用者の PATH に足す（uv の入れ先）。
Say 'octavo コマンド' 'The octavo command'
$have = $null
if (Get-Command octavo -ErrorAction SilentlyContinue) {
    $v = (& octavo --version 2>$null)
    if ($v -match 'octavo (\S+)') { $have = $Matches[1] }
}
if ($OctavoVersion -and $have -eq $OctavoVersion) {
    Info "入っている: octavo $have" "installed: octavo $have"
} elseif ($Check) {
    Info "(実行しない) uv tool install --force octavo-kit$(if ($OctavoVersion) { "==$OctavoVersion" })" `
         "(not run) uv tool install --force octavo-kit$(if ($OctavoVersion) { "==$OctavoVersion" })"
} else {
    $spec = if ($OctavoVersion) { "octavo-kit==$OctavoVersion" } else { 'octavo-kit' }
    & uv tool install --force $spec
    if ($LASTEXITCODE -ne 0) { Info '入らなかった（後で uv tool install octavo-kit）' 'failed (later: uv tool install octavo-kit)' }
}
$user = [Environment]::GetEnvironmentVariable('Path', 'User')
if (-not $Check -and -not (($user -split ';') -contains $BIN)) {
    [Environment]::SetEnvironmentVariable('Path', ($user.TrimEnd(';') + ";$BIN").TrimStart(';'), 'User')
    Info "$BIN を利用者の PATH に足した（新しく開いたターミナルから効く）" "added $BIN to your PATH (for terminals opened from now on)"
}
Update-Path

# ---------------------------------------------------------------------
if ((Get-Command octavo -ErrorAction SilentlyContinue) -and -not $Check) {
    Say 'よく使う CSL スタイルを取っておく' 'Fetching common CSL styles'
    foreach ($s in 'chicago-author-date', 'apa', 'american-political-science-association',
                   'american-sociological-association', 'ieee') {
        & octavo csl get $s *> $null
        if ($LASTEXITCODE -eq 0) { Info "取れた: $s" "fetched: $s" }
        else { Info "取れなかった（後で octavo csl get $s）: $s" "failed (later: octavo csl get $s): $s" }
    }
    Say '診断' 'Diagnosis'
    $env:OCTAVO_LANG = if ($JA) { 'ja' } else { 'en' }
    & octavo doctor
}

Say 'できあがり' 'Done'
if ($JA) {
    Write-Host '   使いはじめる（VS Code なら、サイドバーの Octavo から同じことができる）:'
    Write-Host '     octavo init 2026-research           # プロジェクトのひな型を作る'
    Write-Host '     cd 2026-research'
    Write-Host '     octavo env                          # 分析の環境（.venv と renv）を用意する'
    Write-Host '     octavo new paper example-paper      # 論文を足す（何本でも）'
    Write-Host '     octavo build --compile              # 全部を PDF まで'
} else {
    Write-Host '   Getting started (in VS Code, the Octavo sidebar does the same):'
    Write-Host '     octavo init 2026-research           # write a project skeleton'
    Write-Host '     cd 2026-research'
    Write-Host '     octavo env                          # set up the analysis environment (.venv and renv)'
    Write-Host '     octavo new paper example-paper      # add a paper (as many as you like)'
    Write-Host '     octavo build --compile              # everything, to PDF'
}
exit 0
