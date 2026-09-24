// valueui.ts — `{{名前}}` の補完・ホバー・赤波線。
//
// citations.ts が引用キーに対してやっていることを、分析が出した数値に
// 対してやる。名前の文字集合は octavo/values.py の PLACEHOLDER と
// 揃えてある（`[A-Za-z_][\w.]*`）。判定は Python 側が持っているので、
// ここは ValuesCache が持ってきた JSON を見せるだけ。

import * as vscode from 'vscode';
import { ValueInfo, ValuesCache, ValuesReport } from './values';

// values.py の PLACEHOLDER と揃える。
const NAME_CHAR = String.raw`[\w.]`;
const OPEN_AT_CURSOR = new RegExp(String.raw`\{\{\s*([A-Za-z_]${NAME_CHAR}*)?$`);
const PLACEHOLDER = new RegExp(
    String.raw`\{\{\s*(?<name>[A-Za-z_]${NAME_CHAR}*)\s*(?::(?<spec>[^{}]*?))?\s*\}\}`, 'g');

function valueMarkdown(name: string, v: ValueInfo | undefined): vscode.MarkdownString {
    const md = new vscode.MarkdownString(undefined, true);
    if (!v) {
        md.appendMarkdown(`**{{${name}}}** — $(warning) ` +
            vscode.l10n.t('no such value under results/') + '\n\n');
        md.appendMarkdown(vscode.l10n.t(
            'Run the analysis with `octavo analysis run`, or check the spelling.'));
        return md;
    }
    md.appendMarkdown(`**${v.text}**\n\n`);
    md.appendMarkdown(`\`{{${name}}}\` — ${v.source}\n`);
    if (v.note) {
        md.appendMarkdown(`\n${v.note}\n`);
    }
    md.appendMarkdown('\n' + vscode.l10n.t(
        'To change the formatting, write it as {0}.', '`{{' + name + ':.2f}}`'));
    return md;
}

export class ValueCompletionProvider implements vscode.CompletionItemProvider {
    constructor(private readonly cache: ValuesCache) {}

    provideCompletionItems(
        document: vscode.TextDocument,
        position: vscode.Position,
    ): vscode.CompletionItem[] | undefined {
        const report = this.cache.current;
        if (!report) {
            return undefined;
        }
        const prefix = document.lineAt(position.line).text.slice(0, position.character);
        const m = OPEN_AT_CURSOR.exec(prefix);
        if (!m) {
            return undefined;
        }
        const typed = m[1] ?? '';
        const range = new vscode.Range(position.translate(0, -typed.length), position);

        return Object.entries(report.values).map(([name, v]) => {
            const item = new vscode.CompletionItem(name, vscode.CompletionItemKind.Value);
            item.range = range;
            item.filterText = name;
            item.insertText = name;
            item.detail = v.text;
            item.documentation = valueMarkdown(name, v);
            // 使われていない値を下に沈めて、書きかけの本文で使う値を上に出す
            const used = (report.referenced[name] ?? []).length > 0;
            item.sortText = (used ? '0' : '1') + name;
            return item;
        });
    }
}

export class ValueHoverProvider implements vscode.HoverProvider {
    constructor(private readonly cache: ValuesCache) {}

    provideHover(
        document: vscode.TextDocument,
        position: vscode.Position,
    ): vscode.Hover | undefined {
        const report = this.cache.current;
        if (!report) {
            return undefined;
        }
        const line = document.lineAt(position.line).text;
        PLACEHOLDER.lastIndex = 0;
        let m: RegExpExecArray | null;
        while ((m = PLACEHOLDER.exec(line))) {
            const start = m.index;
            const end = start + m[0].length;
            if (position.character < start || position.character > end) {
                continue;
            }
            const name = m.groups?.name ?? '';
            const range = new vscode.Range(position.line, start, position.line, end);
            return new vscode.Hover(valueMarkdown(name, report.values[name]), range);
        }
        return undefined;
    }
}

/** 未解決の `{{…}}` に赤波線を引く。 */
export class ValueDiagnostics implements vscode.Disposable {
    private readonly collection =
        vscode.languages.createDiagnosticCollection('octavoValues');
    private readonly disposables: vscode.Disposable[] = [this.collection];

    constructor(cache: ValuesCache) {
        this.disposables.push(cache.onDidUpdate((r) => this.applyAll(r)));
    }

    private isEnabled(): boolean {
        return vscode.workspace.getConfiguration('octavo')
            .get<boolean>('diagnosticsOnSave', true);
    }

    applyAll(report: ValuesReport | undefined): void {
        if (!this.isEnabled()) {
            this.collection.clear();
            return;
        }
        for (const doc of vscode.workspace.textDocuments) {
            if (doc.languageId === 'markdown') {
                this.applyToMarkdown(doc, report);
            }
        }
    }

    applyToMarkdown(doc: vscode.TextDocument, report: ValuesReport | undefined): void {
        if (!report || report.missing.length === 0) {
            this.collection.delete(doc.uri);
            return;
        }
        const missing = new Set(report.missing);
        const text = doc.getText();
        const diags: vscode.Diagnostic[] = [];
        PLACEHOLDER.lastIndex = 0;
        let m: RegExpExecArray | null;
        while ((m = PLACEHOLDER.exec(text))) {
            const name = m.groups?.name ?? '';
            if (!missing.has(name)) {
                continue;
            }
            const range = new vscode.Range(doc.positionAt(m.index),
                                           doc.positionAt(m.index + m[0].length));
            const d = new vscode.Diagnostic(range,
                vscode.l10n.t('No such value under results/: {0}', name) + '\n' +
                vscode.l10n.t(
                    'Add ov_value("{0}", …) to the .qmd and run octavo analysis run, '
                    + 'or check the spelling.', name),
                vscode.DiagnosticSeverity.Warning);
            d.source = 'Octavo';
            d.code = 'missing-value';
            diags.push(d);
        }
        if (diags.length > 0) {
            this.collection.set(doc.uri, diags);
        } else {
            this.collection.delete(doc.uri);
        }
    }

    dispose(): void {
        this.disposables.forEach((d) => d.dispose());
    }
}
