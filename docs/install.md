# Installing Octavo

> This is the source of the install guide. Read it at **<https://yoshida-kd.github.io/octavo/install/>**. <!-- pages:skip -->

Octavo needs a few tools besides itself: **pandoc** (conversion), **Typst** (typesetting to
PDF), **Quarto**, **R** and **Python** (the analysis), the **fonts**, and **uv** (which
installs the `octavo` command). **The VS Code extension installs all of them with one
button.** Pick your system:

| You use | Read |
|---|---|
| Ubuntu or another Debian-like Linux — a PC, or a server you reach over SSH | [Linux](#1-linux) |
| A Mac | [macOS](#2-macos) |
| Windows | [Windows](#3-windows) — WSL (recommended) or Windows itself |

LaTeX is not included; it is optional ([LaTeX, if you want it](#6-latex-if-you-want-it)).
Once it is installed, the [quick guide](https://yoshida-kd.github.io/octavo/quickstart/) takes
you to your first PDF.

---

## 1. Linux

Ubuntu 24.04 is what Octavo is tested on; Debian and other Ubuntu versions work too (a font
the distribution doesn't package is replaced by Noto). You need a user who can use `sudo`.

1. Install [VS Code](https://code.visualstudio.com/) on the computer you work at.
   *If Octavo is to run on a server*, also install the **Remote - SSH** extension and
   connect to the server (**Remote-SSH: Connect to Host…**); everything below then happens
   on the server.
2. Install the **Octavo** extension (search "Octavo" in the Extensions view, publisher
   yoshida-kd). Over Remote-SSH, click **Install in SSH: …** so it lands on the server.
3. Open a folder. The extension checks the tools and offers **Set up**. Press it: a
   terminal opens, asks for your password once (for `sudo`), and installs everything.
   It takes a while the first time (R and the fonts are the large part).
4. When it finishes, the extension checks again. Nothing to report means you are done.

R is the latest release from CRAN, and its packages come ready-made from Posit Package
Manager instead of being compiled. Some of those need a system library when they load (igraph,
used by quanteda.textplots, needs GLPK); Set up installs those too.

<details>
<summary><strong>From a terminal instead</strong></summary>

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # uv
source ~/.local/bin/env                           # put uv on PATH in this terminal (or open a new one)
uv tool install octavo-kit                        # the octavo command
octavo setup                                      # pandoc, Typst, Quarto, fonts, R, renv (asks for your password)
octavo doctor                                     # everything should read ok
```

</details>

## 2. macOS

**First install Homebrew**, which Octavo uses to install everything else. Open Terminal and
run the one line from [brew.sh](https://brew.sh):

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow what it prints at the end (on Apple Silicon it asks you to add Homebrew to your
`PATH`), then open a new Terminal window.

1. Install [VS Code](https://code.visualstudio.com/) and the **Octavo** extension.
2. Open a folder and press **Set up** when the extension offers it. A terminal opens and
   installs everything through Homebrew (your password may be asked for R and Quarto).
3. If the extension says it cannot find `octavo` afterwards, quit VS Code completely
   (⌘Q) and start it again — it was started before the new command existed.

R is CRAN's own build, so CRAN's binary packages work.

<details>
<summary><strong>From a terminal instead</strong></summary>

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # uv
source ~/.local/bin/env                           # put uv on PATH in this terminal (or open a new one)
uv tool install octavo-kit                        # the octavo command
octavo setup                                      # pandoc, Typst, Quarto, fonts, R, renv (with Homebrew)
octavo doctor                                     # everything should read ok
```

</details>

## 3. Windows

There are two ways. **WSL is recommended**: Octavo is developed and tested on Linux first,
and WSL gives you exactly that inside Windows. Use Windows itself only if you cannot use WSL.

### 3.1 Windows with WSL (recommended)

1. Install WSL. Open PowerShell *as administrator* (right-click the Start button →
   *Terminal (Admin)*, or *Windows PowerShell (Admin)* on Windows 10) and run:

   ```powershell
   wsl --install
   ```

   Restart when it asks. Ubuntu then starts and asks you to choose a user name and password
   — remember the password, the setup asks for it.
2. Install [VS Code](https://code.visualstudio.com/) on Windows, then the **WSL** extension.
3. In VS Code, **WSL: Connect to WSL** (bottom-left corner). Open a folder *inside* Ubuntu
   (for example `/home/<user name>`).
4. Install the **Octavo** extension.
5. The Octavo extension offers **Set up**; press it and enter the Ubuntu password. From
   here on it is the [Linux](#1-linux) setup.

### 3.2 Windows itself (without WSL)

This uses [winget](https://learn.microsoft.com/windows/package-manager/winget/), which comes
with Windows 11 and current Windows 10 (if `winget` is not found, install *App Installer*
from the Microsoft Store). No administrator rights are needed. LaTeX is not installed on
Windows (install MiKTeX yourself if you need it).

Install [VS Code](https://code.visualstudio.com/) and the **Octavo** extension, open a folder,
and press **Set up**. On a PC without WSL the extension uses Windows' own tools. When it has
finished, restart VS Code so it sees the new commands.

<details>
<summary><strong>From a terminal instead</strong></summary>

Open PowerShell (not as administrator) and run:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"   # uv
```

Close PowerShell and open a new one (so it finds `uv`), then:

```powershell
uv tool install octavo-kit    # the octavo command
octavo setup                  # pandoc, Typst, Quarto, fonts, R, renv (with winget)
```

Open a new PowerShell once more and check:

```powershell
octavo doctor                 # everything should read ok
```

</details>

Two habits keep a project working on every system: write paths with `/`
(`../assets/figures/trend.png`), and keep the upper and lower case of file names exactly as
the manuscript writes them — Windows does not tell `Trend.png` from `trend.png`, Linux does.

## 4. Check that it works

- In the Octavo sidebar, **Tools → Diagnose the Environment** lists what is installed. Anything
  missing comes with what installs it; **Tools → Install or Update the Tools** fixes it.
- From the Command Palette (Ctrl+Shift+P, ⌘⇧P on a Mac), **Octavo: Check How Citations Come
  Out** typesets a small sample with English and Japanese references, a table, a figure and
  cross-references, and shows how the citations came out. Run it once per machine and read it.

## 5. Updating

Update the extension in the Extensions view (or let VS Code do it), then press
**Tools → Install or Update the Tools** in the Octavo sidebar: it brings the `octavo` command
and the tools up to the versions the extension expects. What is already there is skipped. The
extension also offers this by itself when the command is older than the extension.

## 6. LaTeX, if you want it

Everything above makes PDFs through Typst; LaTeX is only needed for the `tex` and `beamer`
outputs. On Linux, ask your AI assistant to run `octavo setup --with-tex` (or run it yourself;
it adds TeX Live, several GB). On a Mac, install [MacTeX](https://www.tug.org/mactex/); on
Windows, [MiKTeX](https://miktex.org/). The environment check lists TeX separately and does not
count it as missing.

## 7. The language Octavo speaks

The extension follows VS Code's display language; in a terminal, messages come out in English,
or in Japanese when your system is set to Japanese (`export OCTAVO_LANG=ja` or `en` chooses).
This is only the language of the messages. The language a project is *written* in is chosen
when you make the project.
