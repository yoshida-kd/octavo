// diagnostics.ts — 無い引用キーに赤波線、.bib の傷に警告を出す。
//
// 判定は Python 側（octavo/check.py）の結果をそのまま使う。ここでは
// 「その結果を、開いているドキュメントのどこに置くか」だけを決める。

import * as vscode from 'vscode';
import { BibCache, CheckbibReport } from './bib';
import { resolvePathFromTool } from './runner';

function escapeRegExp(s: string): string {
    return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

const KEY_CHAR = String.raw`[\w:.#$%&+?<>~/-]`;

function missingKeyPatterns(key: string): RegExp[] {
    const k = escapeRegExp(key);
    return [
        // @key（地の文・括弧の中どちらも）。直前が単語文字/@/.-でないこと。
        new RegExp(String.raw`(?<![\w.@-])@${k}(?!${KEY_CHAR})`, 'g'),
        // \poscite{key}
        new RegExp(String.raw`\\poscite\{${k}\}`, 'g'),
    ];
}

export class DiagnosticsManager implements vscode.Disposable {
    private readonly collection = vscode.languages.createDiagnosticCollection('octavo');
    private readonly disposables: vscode.Disposable[] = [this.collection];

    constructor(cache: BibCache) {
        this.disposables.push(cache.onDidUpdate((report) => void this.applyAll(report)));
    }

    private isEnabled(): boolean {
        return vscode.workspace.getConfiguration('octavo')
            .get<boolean>('diagnosticsOnSave', true);
    }

    async applyAll(report: CheckbibReport | undefined): Promise<void> {
        if (!this.isEnabled()) {
            this.collection.clear();
            return;
        }
        for (const doc of vscode.workspace.textDocuments) {
            if (doc.languageId === 'markdown') {
                this.applyToMarkdown(doc, report);
            }
        }
        await this.applyToBibFile(report);
    }

    applyToMarkdown(doc: vscode.TextDocument, report: CheckbibReport | undefined): void {
        if (!report || report.missing.length === 0) {
            this.collection.delete(doc.uri);
            return;
        }
        const text = doc.getText();
        const diags: vscode.Diagnostic[] = [];
        for (const key of report.missing) {
            const suggestion = report.suggestions[key];
            const message = vscode.l10n.t('Citation key not in the .bib: {0}', key) +
                (suggestion ? vscode.l10n.t(' (did you mean @{0}?)', suggestion) : '') +
                '\n' + vscode.l10n.t(
                    '{0} is the source of truth. Add it in Zotero and export again.',
                    report.bib_file.split(/[\\/]/).pop() ?? '');
            for (const pattern of missingKeyPatterns(key)) {
                let m: RegExpExecArray | null;
                while ((m = pattern.exec(text))) {
                    const start = doc.positionAt(m.index);
                    const end = doc.positionAt(m.index + m[0].length);
                    const d = new vscode.Diagnostic(new vscode.Range(start, end), message,
                        vscode.DiagnosticSeverity.Warning);
                    d.source = 'Octavo';
                    d.code = 'missing-citation';
                    diags.push(d);
                }
            }
        }
        if (diags.length > 0) {
            this.collection.set(doc.uri, diags);
        } else {
            this.collection.delete(doc.uri);
        }
    }

    private async applyToBibFile(report: CheckbibReport | undefined): Promise<void> {
        if (!report) {
            return;
        }
        const uri = resolvePathFromTool(report.bib_file);
        if (!uri) {
            return; // WSL のホーム以下など、Windows 側から直接は開けない場所
        }
        const unaccepted = report.problems;
        if (unaccepted.length === 0 && report.duplicates.length === 0) {
            this.collection.delete(uri);
            return;
        }

        let bibDoc: vscode.TextDocument;
        try {
            bibDoc = await vscode.workspace.openTextDocument(uri);
        } catch {
            return; // ファイルが無い/読めない
        }
        const text = bibDoc.getText();
        const diags: vscode.Diagnostic[] = [];

        const rangeForKey = (key: string): vscode.Range => {
            const m = new RegExp(String.raw`@\w+\s*\{\s*${escapeRegExp(key)}\s*,`).exec(text);
            if (!m) {
                return new vscode.Range(0, 0, 0, 0);
            }
            const start = bibDoc.positionAt(m.index);
            const end = bibDoc.positionAt(m.index + m[0].length);
            return new vscode.Range(start, end);
        };

        for (const p of unaccepted) {
            const d = new vscode.Diagnostic(rangeForKey(p.key),
                `${p.key}: ${p.issue}${p.detail ? '　' + p.detail : ''}\n` +
                vscode.l10n.t(
                    'List it in bib_accepted in octavo.config.py, with a reason, to silence this.'),
                vscode.DiagnosticSeverity.Information);
            d.source = 'Octavo';
            d.code = 'bib-quality';
            diags.push(d);
        }
        for (const [a, b] of report.duplicates) {
            const d = new vscode.Diagnostic(rangeForKey(a),
                vscode.l10n.t('{0} and {1} may be the same reference imported twice.', a, b),
                vscode.DiagnosticSeverity.Information);
            d.source = 'Octavo';
            d.code = 'bib-duplicate';
            diags.push(d);
        }
        this.collection.set(uri, diags);
    }

    dispose(): void {
        this.disposables.forEach((d) => d.dispose());
    }
}
