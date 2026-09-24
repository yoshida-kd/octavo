// values.ts — `octavo values --json` の結果をキャッシュして配る。
//
// bib.ts と同じ考え方。**どの値があるか・どれが未解決かの判定は Python 側
// （octavo/values.py）に1箇所だけ**あり、ここはそれを JSON で受け取って
// 見せるだけ。`{{…}}` の解決規則を TypeScript 側で作り直さない。

import * as vscode from 'vscode';
import { dirOf, findConfig, runCapture } from './runner';

export interface ValueInfo {
    text: string;      // 本文に入る文字（書式を通したあと）
    source: string;    // どの results/*.json から来たか
    note: string;
}

export interface ValuesReport {
    results_dir: string;
    values: Record<string, ValueInfo>;
    referenced: Record<string, string[]>;   // 名前 -> それを使っている文書
    missing: string[];                      // 本文にあるのに値が無い
    unused: string[];
    orphans: string[];
    warnings: string[];
}

export class ValuesCache {
    private report: ValuesReport | undefined;
    private refreshing: Promise<ValuesReport | undefined> | undefined;

    private readonly onDidUpdateEmitter = new vscode.EventEmitter<ValuesReport | undefined>();
    readonly onDidUpdate = this.onDidUpdateEmitter.event;

    private readonly onErrorEmitter = new vscode.EventEmitter<string>();
    readonly onError = this.onErrorEmitter.event;

    get current(): ValuesReport | undefined {
        return this.report;
    }

    /** 実行中なら同じ Promise に相乗りする（保存が連続しても二重に走らせない）。 */
    async refresh(force = false): Promise<ValuesReport | undefined> {
        if (this.refreshing && !force) {
            return this.refreshing;
        }
        this.refreshing = this.doRefresh();
        try {
            return await this.refreshing;
        } finally {
            this.refreshing = undefined;
        }
    }

    private async doRefresh(): Promise<ValuesReport | undefined> {
        const configUri = await findConfig();
        if (!configUri) {
            this.report = undefined;
            return undefined;
        }
        // -c は付けない（bib.ts と同じ理由。cwd に任せる）。
        const result = await runCapture(dirOf(configUri), ['values', '--json']);

        // 未解決があると exit 1 になる設計なので、終了コードは見ない。
        const text = result.stdout.trim();
        if (!text) {
            this.onErrorEmitter.fire(result.stderr.trim() ||
                vscode.l10n.t('octavo values --json returned nothing'));
            return this.report;
        }
        try {
            const jsonStart = text.lastIndexOf('\n{');
            const jsonText = jsonStart >= 0 ? text.slice(jsonStart + 1) : text;
            this.report = JSON.parse(jsonText) as ValuesReport;
            this.onDidUpdateEmitter.fire(this.report);
            return this.report;
        } catch (e) {
            this.onErrorEmitter.fire(
                vscode.l10n.t('Could not read the values output as JSON: {0}', String(e)) +
                '\n' + text.slice(0, 500));
            return this.report;
        }
    }

    dispose(): void {
        this.onDidUpdateEmitter.dispose();
        this.onErrorEmitter.dispose();
    }
}
