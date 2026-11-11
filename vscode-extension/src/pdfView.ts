// pdfView.ts — PDF を Octavo のビューア（プレビューと同じ pdf.js の画面）で開き、書き換わるたびに読み直す。
//
// 「この Typst ファイルをプレビューする」（typst watch）が書き出す PDF を、ほかの拡張機能に頼らずに
// 見るためのもの。ふつうの PDF の開き方は変えない（priority は option。タブの「Open With…」か
// 「別のエディタで開く」で選べる）。原稿とは結びつかないので、カーソルに合わせる機能はない。
//
// 書き出しの途中を読むと壊れた PDF になるので、終わりの印（%%EOF）がまだなければ少し待って読み直す。
import * as path from 'path';
import * as vscode from 'vscode';
import { PdfPanel } from './preview';

export const PDF_VIEW_TYPE = 'octavo.pdf';

function complete(bytes: Uint8Array): boolean {
    const tail = Buffer.from(bytes.subarray(Math.max(0, bytes.length - 1024))).toString('latin1');
    return tail.includes('%%EOF');
}

export class PdfViewProvider implements vscode.CustomReadonlyEditorProvider {
    static register(context: vscode.ExtensionContext): vscode.Disposable {
        return vscode.window.registerCustomEditorProvider(
            PDF_VIEW_TYPE, new PdfViewProvider(vscode.Uri.joinPath(context.extensionUri, 'media')),
            // enableFindWidget: Ctrl+F（Mac は Cmd+F）で PDF の文字を探せる（プレビューと同じ）
            { webviewOptions: { retainContextWhenHidden: true, enableFindWidget: true } });
    }

    constructor(private readonly media: vscode.Uri) {}

    openCustomDocument(uri: vscode.Uri): vscode.CustomDocument {
        return { uri, dispose: () => undefined };
    }

    resolveCustomEditor(document: vscode.CustomDocument, webviewPanel: vscode.WebviewPanel): void {
        const uri = document.uri;
        const name = path.basename(uri.fsPath);
        const subs: vscode.Disposable[] = [];
        let timer: NodeJS.Timeout | undefined;
        let closed = false;
        const view = new PdfPanel(this.media, webviewPanel, name, () => {
            closed = true;
            clearTimeout(timer);
            subs.forEach((d) => d.dispose());
        }, () => undefined, () => undefined, false);

        const load = async (tries: number): Promise<void> => {
            if (closed) {
                return;
            }
            let bytes: Uint8Array;
            try {
                bytes = await vscode.workspace.fs.readFile(uri);
            } catch {
                if (tries > 0) {
                    later(tries - 1);
                } else {
                    view.error(vscode.l10n.t('Octavo: could not read {0}.', name));
                }
                return;
            }
            if (!complete(bytes) && tries > 0) {
                later(tries - 1);          // 書き出しの途中。次の変更の知らせを待たずに少しあとで
                return;
            }
            view.show(bytes, name);
        };
        const later = (tries: number, wait = 300): void => {
            clearTimeout(timer);
            timer = setTimeout(() => void load(tries), wait);
        };

        const watcher = vscode.workspace.createFileSystemWatcher(
            new vscode.RelativePattern(vscode.Uri.joinPath(uri, '..'), name));
        subs.push(watcher, watcher.onDidChange(() => later(10, 150)), watcher.onDidCreate(() => later(10, 150)));
        void load(10);
    }
}

/** path の PDF が書き出されるのを待って（最大 timeout ミリ秒）、Octavo のビューアで横に開く。 */
export async function openPdfWhenReady(pdf: vscode.Uri, timeout = 20000): Promise<boolean> {
    const until = Date.now() + timeout;
    for (;;) {
        try {
            await vscode.workspace.fs.stat(pdf);
            break;
        } catch {
            if (Date.now() > until) {
                return false;
            }
            await new Promise((r) => setTimeout(r, 300));
        }
    }
    await vscode.commands.executeCommand('vscode.openWith', pdf, PDF_VIEW_TYPE,
                                         { viewColumn: vscode.ViewColumn.Beside, preserveFocus: true });
    return true;
}
