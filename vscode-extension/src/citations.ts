// citations.ts — `@key` の補完・ホバー・挿入コマンド。
//
// 元ネタは octavo/md.py の CITE_KEY / POSCITE 正規表現と揃えてある
// （`[\w][\w:.#$%&+?<>~/-]*`）。Zotero の Better BibTeX が作る citation key
// はだいたいこの文字集合に収まる。

import * as vscode from 'vscode';
import { BibCache, BibEntry } from './bib';

// citation key の1文字。パーサ（md.py）の CITE_KEY と揃えてある。
const KEY_CHAR = String.raw`[\w:.#$%&+?<>~/-]`;
const AT_KEY_AT_CURSOR = new RegExp(`@(${KEY_CHAR}*)$`);
const AT_KEY_WORD = new RegExp(`@${KEY_CHAR}+`);
const POSCITE_AT = new RegExp(String.raw`\\poscite\{(${KEY_CHAR}+)\}`, 'g');

function entryMarkdown(key: string, e: BibEntry | undefined, missing: boolean,
                       suggestion?: string): vscode.MarkdownString {
    const md = new vscode.MarkdownString(undefined, true);
    if (!e) {
        md.appendMarkdown(`**@${key}** — $(warning) ` +
            vscode.l10n.t('not a key in the .bib') + '\n\n');
        if (missing && suggestion) {
            md.appendMarkdown(vscode.l10n.t('Did you mean: {0}', `\`@${suggestion}\``) + '\n');
        }
        md.isTrusted = false;
        return md;
    }
    md.appendMarkdown(`**${e.title || vscode.l10n.t('(no title)')}**\n\n`);
    md.appendMarkdown(`${e.authors} (${e.year}) — *${e.type}*\n\n`);
    md.appendMarkdown(`\`@${key}\``);
    return md;
}

export class CitationCompletionProvider implements vscode.CompletionItemProvider {
    constructor(private readonly cache: BibCache) {}

    provideCompletionItems(
        document: vscode.TextDocument,
        position: vscode.Position,
    ): vscode.CompletionItem[] | undefined {
        const report = this.cache.current;
        if (!report) {
            return undefined;
        }
        const prefix = document.lineAt(position.line).text.slice(0, position.character);
        const m = AT_KEY_AT_CURSOR.exec(prefix);
        if (!m) {
            return undefined;
        }
        const typed = m[1];
        const range = new vscode.Range(
            position.translate(0, -typed.length), position);

        const entries = Object.values(report.entries);
        return entries.map((e) => {
            const item = new vscode.CompletionItem(e.key, vscode.CompletionItemKind.Reference);
            item.range = range;
            item.filterText = e.key;
            item.insertText = e.key;
            item.detail = `${e.authors} (${e.year})`;
            item.documentation = entryMarkdown(e.key, e, false);
            item.sortText = report.cited.includes(e.key) ? `0_${e.key}` : `1_${e.key}`;
            return item;
        });
    }
}

export class CitationHoverProvider implements vscode.HoverProvider {
    constructor(private readonly cache: BibCache) {}

    provideHover(
        document: vscode.TextDocument,
        position: vscode.Position,
    ): vscode.Hover | undefined {
        const report = this.cache.current;
        if (!report) {
            return undefined;
        }
        const line = document.lineAt(position.line).text;

        // \poscite{key}
        POSCITE_AT.lastIndex = 0;
        let m: RegExpExecArray | null;
        while ((m = POSCITE_AT.exec(line))) {
            const start = m.index;
            const end = start + m[0].length;
            if (position.character >= start && position.character <= end) {
                const key = m[1];
                const entry = report.entries[key];
                const range = new vscode.Range(position.line, start, position.line, end);
                return new vscode.Hover(
                    entryMarkdown(key, entry, report.missing.includes(key),
                        report.suggestions[key]),
                    range);
            }
        }

        // @key
        const wordRange = document.getWordRangeAtPosition(position, AT_KEY_WORD);
        if (!wordRange) {
            return undefined;
        }
        const key = document.getText(wordRange).slice(1);
        const entry = report.entries[key];
        return new vscode.Hover(
            entryMarkdown(key, entry, report.missing.includes(key), report.suggestions[key]),
            wordRange);
    }
}

export async function insertCitationCommand(cache: BibCache): Promise<void> {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        void vscode.window.showWarningMessage(
            vscode.l10n.t('No editor to insert a citation into.'));
        return;
    }
    let report = cache.current;
    if (!report) {
        report = await cache.refresh();
    }
    if (!report || Object.keys(report.entries).length === 0) {
        void vscode.window.showWarningMessage(
            vscode.l10n.t('No references loaded. Check octavo.config.py and literature.bib.'));
        return;
    }

    const items: (vscode.QuickPickItem & { key: string })[] = Object.values(report.entries)
        .sort((a, b) => (b.year || '').localeCompare(a.year || ''))
        .map((e) => ({
            key: e.key,
            label: e.title || e.key,
            description: `${e.authors} (${e.year})`,
            detail: e.key,
        }));

    const picked = await vscode.window.showQuickPick(items, {
        title: vscode.l10n.t('Insert a citation'),
        placeHolder: vscode.l10n.t(
            'Filter by author or title. Add anything missing on the Zotero side.'),
        matchOnDescription: true,
        matchOnDetail: true,
    });
    if (!picked) {
        return;
    }
    await editor.edit((builder) => {
        for (const sel of editor.selections) {
            builder.replace(sel, `@${picked.key}`);
        }
    });
}
