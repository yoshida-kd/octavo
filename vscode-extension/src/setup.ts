// setup.ts — 道具がそろっているかを見て、足りなければ「準備する」を出す。
//
// そろっているかは `octavo doctor --json` が決める（ここで which を並べ直したりしない）。
// 入れるのは .vsix に同梱した setup.sh（リポジトリ直下のものの写し）。sudo の
// パスワードを打ってもらうのでターミナルで走らせ、閉じたらもう一度確かめる。
// octavo 本体も setup.sh が PyPI から入れるので、拡張機能を入れたあとは
// ボタン1つで済む（clone も pip も要らない）。
import * as os from 'os';
import * as vscode from 'vscode';
import { refreshWindowsPath, runCapture, runSetupScript, runStreaming } from './runner';

/** `octavo doctor --json` のうち、ここで読むもの。 */
export interface DoctorReport {
    version: string;
    ready: boolean;
    missing: string[];
    analysis: Record<string, boolean>;
}

export type ToolState =
    | { kind: 'ok'; report: DoctorReport }
    | { kind: 'no-cli' }
    | { kind: 'outdated'; have: string }
    | { kind: 'incomplete'; report: DoctorReport; lacks: string[] };

/** '0.1.10' と '0.1.9' を数として比べる。a < b なら負。 */
export function compareVersions(a: string, b: string): number {
    const pa = a.split('.').map((x) => parseInt(x, 10) || 0);
    const pb = b.split('.').map((x) => parseInt(x, 10) || 0);
    for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
        const d = (pa[i] ?? 0) - (pb[i] ?? 0);
        if (d !== 0) {
            return d;
        }
    }
    return 0;
}

export class SetupManager {
    private running = false;

    constructor(private readonly context: vscode.ExtensionContext,
                private readonly output: vscode.OutputChannel,
                private readonly onReady: () => void) {}

    private get version(): string {
        return String(this.context.extension.packageJSON.version ?? '0');
    }

    /** 準備を済ませたかを覚えておくキー。Remote-SSH ならサーバごとに別。 */
    private get hostKey(): string {
        return `${vscode.env.remoteName ?? 'local'}:${os.hostname()}:${this.version}`;
    }

    async check(): Promise<ToolState> {
        const r = await runCapture(os.homedir(), ['doctor', '--json'], 90000);
        const text = r.stdout.trim();
        const at = text.lastIndexOf('\n{');
        try {
            const report = JSON.parse(at >= 0 ? text.slice(at + 1) : text) as DoctorReport;
            if (compareVersions(report.version, this.version) < 0) {
                return { kind: 'outdated', have: report.version };
            }
            const lacks = [...report.missing,
                ...Object.entries(report.analysis).filter(([, ok]) => !ok).map(([k]) => k)];
            return lacks.length ? { kind: 'incomplete', report, lacks } : { kind: 'ok', report };
        } catch {
            // --json を知らない古い octavo か、octavo そのものが無い
            const v = await runCapture(os.homedir(), ['--version'], 20000);
            const m = /octavo (\S+)/.exec(v.stdout);
            return m ? { kind: 'outdated', have: m[1] } : { kind: 'no-cli' };
        }
    }

    private describe(state: ToolState): string {
        switch (state.kind) {
            case 'no-cli':
                return vscode.l10n.t('Octavo: the tools it needs (pandoc, Typst, quarto, R, …) are not installed yet.');
            case 'outdated':
                return vscode.l10n.t('Octavo: the octavo command ({0}) is older than this extension ({1}).',
                    state.have, this.version);
            case 'incomplete':
                return vscode.l10n.t('Octavo: some tools are missing: {0}', state.lacks.join(', '));
            default:
                return '';
        }
    }

    /** 起動時に一度。そろっていれば黙る。済ませた・断ったことは覚えておく。 */
    async checkOnStartup(): Promise<void> {
        const done = this.context.globalState.get<string[]>('octavo.setupDone', []);
        const dismissed = this.context.globalState.get<string[]>('octavo.setupDismissed', []);
        if (done.includes(this.hostKey) || dismissed.includes(this.hostKey)) {
            return;
        }
        const state = await this.check();
        if (state.kind === 'ok') {
            await this.remember('octavo.setupDone');
            return;
        }
        const setUp = vscode.l10n.t('Set up');
        const later = vscode.l10n.t('Not now');
        const never = vscode.l10n.t('Don\'t ask again');
        const picked = await vscode.window.showWarningMessage(this.describe(state), setUp, later, never);
        if (picked === setUp) {
            this.runSetup();
        } else if (picked === never) {
            await this.remember('octavo.setupDismissed');
        }
    }

    private async remember(key: string): Promise<void> {
        const list = this.context.globalState.get<string[]>(key, []);
        if (!list.includes(this.hostKey)) {
            await this.context.globalState.update(key, [...list, this.hostKey]);
        }
    }

    /** setup.sh をターミナルで走らせる。閉じたら確かめ直して結果を知らせる。 */
    runSetup(): void {
        if (this.running) {
            void vscode.window.showInformationMessage(vscode.l10n.t('Octavo: the setup is already running.'));
            return;
        }
        this.running = true;
        // setup/ には setup.sh と setup.ps1（Windows で直接動かすとき）がある
        const dir = this.context.asAbsolutePath('setup');
        const pressEnter = vscode.l10n.t('Press Enter to close this terminal');
        runSetupScript(dir, this.version, pressEnter, () => {
            this.running = false;
            void this.afterSetup();
        });
        void vscode.window.showInformationMessage(process.platform === 'win32'
            ? vscode.l10n.t('Octavo: the setup runs in the terminal. Windows may ask for '
                + 'permission for some installers. Close the terminal when it is done.')
            : vscode.l10n.t('Octavo: the setup runs in the terminal. It asks for your password '
                + 'once (sudo). Close the terminal when it is done.'));
    }

    private async afterSetup(): Promise<void> {
        await refreshWindowsPath();   // winget が足した PATH を拾う（Windows だけ）
        const state = await this.check();
        if (state.kind === 'ok') {
            await this.remember('octavo.setupDone');
            void vscode.window.showInformationMessage(vscode.l10n.t('Octavo: everything is ready.'));
            this.onReady();
            return;
        }
        const again = vscode.l10n.t('Run it again');
        const doctor = vscode.l10n.t('Diagnose the Environment (doctor)');
        const picked = await vscode.window.showWarningMessage(this.describe(state), again, doctor);
        if (picked === again) {
            this.runSetup();
        } else if (picked === doctor) {
            void vscode.commands.executeCommand('octavo.doctor');
        }
    }

    /** `octavo env`: プロジェクトの .venv と renv を用意する。出力は出力パネルへ。 */
    async setupProjectEnv(cwd: string): Promise<boolean> {
        const title = vscode.l10n.t('Octavo: setting up this project\'s analysis environment');
        this.output.appendLine(`\n== ${title}`);
        const code = await vscode.window.withProgress(
            { location: vscode.ProgressLocation.Notification, title, cancellable: true },
            (progress, token) => runStreaming(cwd, ['env'], (text) => {
                this.output.append(text);
                const last = text.trim().split('\n').pop()?.trim();
                if (last) {
                    progress.report({ message: last.slice(0, 120) });
                }
            }, token));
        if (code === 0) {
            void vscode.window.showInformationMessage(vscode.l10n.t(
                'Octavo: the analysis environment is ready (.venv and renv). Commit requirements.txt and renv.lock.'));
            return true;
        }
        const show = vscode.l10n.t('Show the output');
        void vscode.window.showErrorMessage(
            vscode.l10n.t('Octavo: setting up the analysis environment failed.'), show)
            .then((p) => { if (p === show) { this.output.show(); } });
        return false;
    }
}
