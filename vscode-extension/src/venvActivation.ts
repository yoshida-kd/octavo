// venvActivation.ts — R のターミナルに `.venv` の activate が流れ込むのを止める。
//
// Python 拡張機能は、ターミナルを開くたびに `source …/.venv/bin/activate` を打ち込む
// （python.terminal.activateEnvironment、既定 true）。R の分析と .venv の両方を持つ
// Octavo のプロジェクトでは、R のターミナル（R 拡張機能が開く）にもそれが入り、R が
// 「unexpected symbol」と言う。害はないが、受講生には壊れたように見える。
// Octavo は .venv を自分で使う（分析は QUARTO_PYTHON で .venv の Python を指す）ので、
// そのプロジェクトのフォルダの設定でだけ止める。利用者がどこかでこの設定を書いていれば
// 触らない。止めたことは一度だけ知らせ、その場で戻せる。
import * as vscode from 'vscode';
import { findConfig } from './runner';

const KEY = 'octavo.venvActivationHandled';

async function exists(uri: vscode.Uri): Promise<boolean> {
    try {
        await vscode.workspace.fs.stat(uri);
        return true;
    } catch {
        return false;
    }
}

function userChose(conf: vscode.WorkspaceConfiguration, key: string): boolean | undefined {
    const ins = conf.inspect(key);
    if (!ins) {
        return undefined;            // その拡張機能が入っていない
    }
    return ins.globalValue !== undefined || ins.workspaceValue !== undefined
        || ins.workspaceFolderValue !== undefined;
}

export async function quietVenvActivation(context: vscode.ExtensionContext,
                                          log: (s: string) => void): Promise<void> {
    const config = await findConfig();
    if (!config) {
        return;
    }
    const folder = vscode.workspace.getWorkspaceFolder(config);
    if (!folder) {
        return;
    }
    const handled = context.globalState.get<string[]>(KEY, []);
    if (handled.includes(folder.uri.toString())) {
        return;
    }
    // R の分析（octavo.R）と .venv の両方があるプロジェクトだけ。Python だけなら
    // ターミナルで .venv が有効になるほうが便利なので、そのままにする
    const root = vscode.Uri.joinPath(config, '..');
    if (!(await exists(vscode.Uri.joinPath(root, '.venv')))
            || !(await exists(vscode.Uri.joinPath(root, 'analysis', 'octavo.R')))) {
        return;
    }
    const py = vscode.workspace.getConfiguration('python', folder.uri);
    const envs = vscode.workspace.getConfiguration('python-envs', folder.uri);
    const pyChose = userChose(py, 'terminal.activateEnvironment');
    if (pyChose === undefined || pyChose) {
        return;                      // Python 拡張機能がない、または利用者が決めている
    }
    const T = vscode.ConfigurationTarget.WorkspaceFolder;
    let setEnvs = false;
    try {
        await py.update('terminal.activateEnvironment', false, T);
        // 新しい Python Environments 拡張機能は上の設定も見るが、こちらが書いてあれば
        // こちらを優先するので、書かれていなければ揃えておく
        if (userChose(envs, 'terminal.autoActivationType') === false) {
            await envs.update('terminal.autoActivationType', 'off', T);
            setEnvs = true;
        }
    } catch (e) {
        log(`[venv] could not change the setting: ${String(e)}`);
        return;
    }
    await context.globalState.update(KEY, [...handled, folder.uri.toString()]);
    log('[venv] turned off python.terminal.activateEnvironment for this folder');
    const undo = vscode.l10n.t('Undo');
    const picked = await vscode.window.showInformationMessage(vscode.l10n.t(
        'Octavo: in this project, terminals no longer run the .venv activate command (the Python extension typed it into R terminals too, where R reports an error). Octavo uses .venv by itself.'),
        vscode.l10n.t('OK'), undo);
    if (picked === undo) {
        await py.update('terminal.activateEnvironment', undefined, T);
        if (setEnvs) {
            await envs.update('terminal.autoActivationType', undefined, T);
        }
    }
}
