// rpackages.ts — R の .qmd が使っているのに入っていないパッケージを、開いた・保存したときに知らせる。
//
// Octavo は `octavo build` / `octavo analysis run` で .qmd が失敗すると、足りないパッケージを入れて
// やり直す。けれども Quarto の Preview から実行すると Octavo を通らないので、R の
// 「パッケージがない」で止まるだけになる。そこで .qmd を開いた・保存したときに
// `octavo analysis missing <qmd> --json` で調べ（ネットワークに触れない。0.5 秒ほど）、
// 足りなければ「入れる」ボタンを出す。入れるのは `octavo analysis install <qmd>`（renv の
// プロジェクトに入れて renv.lock に記録する）。renv がまだなければ `octavo env` を勧める。
import * as path from 'path';
import * as vscode from 'vscode';
import { dirOf, findConfig, runCapture, runStreaming } from './runner';
import { showIfOldCli } from './setup';

interface MissingReport { ok: boolean; renv: boolean; missing: string[] }
interface InstallReport { ok: boolean; installed?: string[]; failed?: string[]; error?: string }

function lastJson<T>(text: string): T | undefined {
    const s = text.trim();
    const at = s.lastIndexOf('\n{');
    try {
        return JSON.parse(at >= 0 ? s.slice(at + 1) : s) as T;
    } catch {
        return undefined;
    }
}

export class RPackageCheck implements vscode.Disposable {
    private readonly subs: vscode.Disposable[] = [];
    /** 「今は入れない」と答えた組（ファイルと足りないものの組）。同じことを何度も聞かない */
    private readonly declined = new Set<string>();
    private readonly running = new Set<string>();

    constructor(private readonly log: (line: string) => void) {
        this.subs.push(
            vscode.workspace.onDidOpenTextDocument((d) => void this.check(d)),
            vscode.workspace.onDidSaveTextDocument((d) => void this.check(d)),
        );
        for (const d of vscode.workspace.textDocuments) {
            void this.check(d);
        }
    }

    dispose(): void {
        this.subs.forEach((s) => s.dispose());
    }

    private async check(doc: vscode.TextDocument): Promise<void> {
        if (doc.uri.scheme !== 'file' || !doc.uri.fsPath.endsWith('.qmd')
            || !/^```\s*\{r[\s,}]/m.test(doc.getText())
            || !vscode.workspace.getConfiguration('octavo').get<boolean>('checkRPackages', true)) {
            return;
        }
        const configUri = await findConfig();
        if (!configUri) {
            return;
        }
        const cwd = dirOf(configUri);
        const rel = path.relative(cwd, doc.uri.fsPath);
        if (rel.startsWith('..') || this.running.has(rel)) {
            return;
        }
        this.running.add(rel);
        try {
            const qmd = rel.split(path.sep).join('/');
            const r = await runCapture(cwd, ['analysis', 'missing', qmd, '--json'], 120000);
            if (r.code !== 0 && showIfOldCli(r.stderr)) {
                return;
            }
            const got = lastJson<MissingReport>(r.stdout);
            if (!got?.ok || !got.missing.length) {
                return;
            }
            const key = `${rel}:${got.missing.join(',')}`;
            if (this.declined.has(key)) {
                return;
            }
            const name = path.basename(doc.uri.fsPath);
            const pkgs = got.missing.join(', ');
            if (!got.renv) {
                const env = vscode.l10n.t('Set Up the Environment (env)');
                const picked = await vscode.window.showWarningMessage(
                    vscode.l10n.t('{0} uses R packages that are not installed: {1}. Set up the analysis environment first; it installs them too.', name, pkgs),
                    env);
                if (picked === env) {
                    await vscode.commands.executeCommand('octavo.envSetup');
                } else {
                    this.declined.add(key);
                }
                return;
            }
            const install = vscode.l10n.t('Install');
            const picked = await vscode.window.showWarningMessage(
                vscode.l10n.t('{0} uses R packages that are not installed: {1}', name, pkgs), install);
            if (picked !== install) {
                this.declined.add(key);
                return;
            }
            await this.install(cwd, qmd, pkgs);
        } finally {
            this.running.delete(rel);
        }
    }

    private async install(cwd: string, qmd: string, pkgs: string): Promise<void> {
        let text = '';
        const code = await vscode.window.withProgress(
            { location: vscode.ProgressLocation.Notification, cancellable: true,
              title: vscode.l10n.t('Installing R packages: {0}', pkgs) },
            (_p, token) => runStreaming(cwd, ['analysis', 'install', qmd, '--json'], (s) => {
                text += s;
            }, token));
        const got = lastJson<InstallReport>(text);
        this.log(text.trim());
        if (code === 0 && got?.ok) {
            void vscode.window.showInformationMessage(
                vscode.l10n.t('Installed {0} (recorded in renv.lock).', (got.installed ?? []).join(', ') || pkgs));
            return;
        }
        void vscode.window.showErrorMessage(got?.error
            ?? vscode.l10n.t('Could not install {0}. See the Octavo output for the details.', (got?.failed ?? []).join(', ') || pkgs));
    }
}
