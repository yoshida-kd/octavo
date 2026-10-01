// tableEditor.ts — 手で作る表（tables/<名前>.csv）や、手で打ち込むデータ（data/**/*.csv）を
// 表の形で編集する画面。
//
// 中身は普通のテキスト文書（CSV）のまま。画面で直すと文書を書き換え、文書が外で
// 変わる（テキストで直す・元に戻す）と画面を描き直す。保存・元に戻す・未保存の印は
// VS Code の文書の仕組みにそのまま任せる。見出しの結合・揃えなどの決まりは CLI
// （handtables.py）だけが持ち、ここは CSV の行と列を編集するだけ。
import * as vscode from 'vscode';

/** CSV を行の配列に（RFC 4180: "…" の中の , と改行と "" を扱う）。 */
export function parseCsv(text: string): string[][] {
    const rows: string[][] = [];
    let row: string[] = [];
    let cell = '';
    let quoted = false;
    const s = text.replace(/^﻿/, '');
    for (let i = 0; i < s.length; i++) {
        const c = s[i];
        if (quoted) {
            if (c === '"') {
                if (s[i + 1] === '"') {
                    cell += '"';
                    i++;
                } else {
                    quoted = false;
                }
            } else {
                cell += c;
            }
        } else if (c === '"' && cell === '') {
            quoted = true;
        } else if (c === ',') {
            row.push(cell);
            cell = '';
        } else if (c === '\n' || c === '\r') {
            if (c === '\r' && s[i + 1] === '\n') i++;
            row.push(cell);
            rows.push(row);
            row = [];
            cell = '';
        } else {
            cell += c;
        }
    }
    if (cell !== '' || row.length) {
        row.push(cell);
        rows.push(row);
    }
    const width = Math.max(1, ...rows.map((r) => r.length));
    return rows.map((r) => [...r, ...Array(width - r.length).fill('')]);
}

function quote(cell: string): string {
    return /[",\r\n]|^\s|\s$/.test(cell) ? '"' + cell.replace(/"/g, '""') + '"' : cell;
}

/** 行の配列を CSV に（末尾の改行つき）。改行コードは元の文書に合わせる。 */
export function toCsv(rows: string[][], eol: string): string {
    return rows.map((r) => r.map(quote).join(',')).join(eol) + eol;
}

export class TableEditorProvider implements vscode.CustomTextEditorProvider {
    static readonly viewType = 'octavo.tableEditor';

    constructor(private readonly context: vscode.ExtensionContext) {}

    static register(context: vscode.ExtensionContext): vscode.Disposable {
        return vscode.Disposable.from(
            vscode.window.registerCustomEditorProvider(
                TableEditorProvider.viewType, new TableEditorProvider(context),
                { webviewOptions: { retainContextWhenHidden: true } }),
            // .csv のタブの右上のボタン。ふだんの .csv はテキストで開き、押すと表の画面にする
            // （tables/ という名前のフォルダは Octavo 以外のプロジェクトにもあるので、既定にしない）
            vscode.commands.registerCommand('octavo.editTable', async (uri?: vscode.Uri) => {
                const target = uri ?? vscode.window.activeTextEditor?.document.uri;
                if (target) {
                    await vscode.commands.executeCommand('vscode.openWith', target,
                                                         TableEditorProvider.viewType);
                }
            }));
    }

    resolveCustomTextEditor(document: vscode.TextDocument, panel: vscode.WebviewPanel): void {
        const media = vscode.Uri.joinPath(this.context.extensionUri, 'media');
        panel.webview.options = { enableScripts: true, localResourceRoots: [media] };
        // 結合の決まりがあるのは手で作る表（tables/）だけ。data/ の CSV などは1行目が列の名前
        const isTable = /(^|\/)tables\/[^/]+\.csv$/i.test(document.uri.path);
        panel.webview.html = this.html(panel.webview, media, isTable);

        const eol = (): string => (document.eol === vscode.EndOfLine.CRLF ? '\r\n' : '\n');
        // 画面から来た変更をいま文書に書いているところか（その変更で描き直さない）
        let writing = false;
        const send = (): void => {
            const text = document.getText();
            void panel.webview.postMessage({
                type: 'rows', rows: parseCsv(text),
                // UTF-8 として読めていない（Shift_JIS のまま開いた）ときの印
                garbled: text.includes('�'),
            });
        };

        const subs = [
            vscode.workspace.onDidChangeTextDocument((e) => {
                if (e.document.uri.toString() === document.uri.toString() && !writing
                    && e.contentChanges.length) {
                    send();
                }
            }),
            panel.webview.onDidReceiveMessage(async (m: { type: string; rows?: string[][] }) => {
                if (m.type === 'ready') {
                    send();
                } else if (m.type === 'edit' && m.rows) {
                    const text = toCsv(m.rows, eol());
                    if (text === document.getText()) return;
                    const edit = new vscode.WorkspaceEdit();
                    edit.replace(document.uri,
                                 new vscode.Range(0, 0, document.lineCount, 0), text);
                    writing = true;
                    try {
                        await vscode.workspace.applyEdit(edit);
                    } finally {
                        writing = false;
                    }
                } else if (m.type === 'text') {
                    await vscode.commands.executeCommand('vscode.openWith', document.uri, 'default');
                }
            }),
        ];
        panel.onDidDispose(() => subs.forEach((s) => s.dispose()));
    }

    private html(w: vscode.Webview, media: vscode.Uri, isTable: boolean): string {
        const nonce = Array.from({ length: 32 },
            () => 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'[
                Math.floor(Math.random() * 62)]).join('');
        const uri = (f: string): vscode.Uri => w.asWebviewUri(vscode.Uri.joinPath(media, f));
        const csp = [`default-src 'none'`, `style-src ${w.cspSource}`,
                     `script-src 'nonce-${nonce}'`].join('; ');
        // 画面の文言（webview の中からは vscode.l10n を呼べないので、ここで訳して渡す）
        const words = {
            merges: isTable,
            merge: vscode.l10n.t('← merged'),
            garbled: vscode.l10n.t('This file does not look like UTF-8 (perhaps Excel saved it as Shift_JIS). Editing it here would lose characters: reopen it with the encoding Shift_JIS (the encoding in the status bar), or save it from Excel as "CSV UTF-8".'),
        };
        const esc = (s: string): string => s.replace(/&/g, '&amp;').replace(/"/g, '&quot;')
            .replace(/</g, '&lt;');
        const button = (id: string, label: string, title: string): string =>
            `<button id="${id}" title="${esc(title)}">${esc(label)}</button>`;
        return `<!DOCTYPE html>
<html lang="${vscode.env.language}">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="${csp}">
<link rel="stylesheet" href="${uri('table.css')}">
</head>
<body data-words="${esc(JSON.stringify(words))}">
<div id="bar">
  ${button('row-add', vscode.l10n.t('+ Row'), vscode.l10n.t('Add a row below the current one'))}
  ${button('col-add', vscode.l10n.t('+ Column'), vscode.l10n.t('Add a column to the right of the current one'))}
  ${button('row-up', '↑', vscode.l10n.t('Move the row up'))}
  ${button('row-down', '↓', vscode.l10n.t('Move the row down'))}
  ${button('col-left', '←', vscode.l10n.t('Move the column left'))}
  ${button('col-right', '→', vscode.l10n.t('Move the column right'))}
  ${button('row-del', vscode.l10n.t('− Row'), vscode.l10n.t('Delete the current row'))}
  ${button('col-del', vscode.l10n.t('− Column'), vscode.l10n.t('Delete the current column'))}
  <span class="spacer"></span>
  ${button('as-text', vscode.l10n.t('Edit as text'), vscode.l10n.t('Open the .csv in the text editor'))}
</div>
<div id="garbled"></div>
<div id="help">${esc(isTable
        ? vscode.l10n.t('The first row is the heading. Leave a heading cell empty to merge it into the cell on its left. Enter: next row, Alt+Enter: a line break in the cell. You can paste a range copied from Excel.')
        : vscode.l10n.t('The first row holds the column names. Enter: next row, Alt+Enter: a line break in the cell. You can paste a range copied from Excel.'))}</div>
<div id="grid-host"><table id="grid"></table></div>
<script nonce="${nonce}" src="${uri('table.js')}"></script>
</body>
</html>`;
    }
}
