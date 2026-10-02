// project.js — 「新しいプロジェクト」の画面。入力を集めて拡張機能に渡すだけで、
// 何が作られるかの決まりは CLI（octavo init）が持つ。ここにある「作られるもの」の
// 一覧は、見て分かるようにするための目安。
(function () {
    const vscode = acquireVsCodeApi();
    const words = JSON.parse(document.body.getAttribute('data-words') || '{}');
    const $ = (id) => document.getElementById(id);
    const NAME_OK = /^[^\s/\\.][^\s/\\]*$/;
    const PARTS = ['analysis', 'paper', 'slides', 'lecture'];
    let busy = false;

    const checked = (id) => $(id).checked;
    const radio = (n) => (document.querySelector('input[name="' + n + '"]:checked') || {}).value;

    function chosen() {
        return PARTS.filter((p) => checked('use-' + p));
    }

    function partName(p) {
        return $('name-' + p).value.trim();
    }

    function problems() {
        const bad = [];
        if (radio('mode') === 'new') {
            const n = $('name').value.trim();
            if (!n || !NAME_OK.test(n)) bad.push('name');
            if (!$('where').value) bad.push('where');
        }
        for (const p of chosen()) {
            if (!NAME_OK.test(partName(p))) bad.push('name-' + p);
        }
        return bad;
    }

    function summary() {
        const here = radio('mode') === 'here';
        const base = here ? words.workspaceName : ($('name').value.trim() || '<' + words.nameWord + '>');
        const L = [base + '/',
                   '  octavo.config.py   literature.bib   AGENTS.md   README.md',
                   '  figures/'];
        for (const p of chosen()) {
            const n = partName(p) || p;
            if (p === 'analysis') {
                const py = radio('engine') === 'python';
                L.push('  analysis/' + n + '.qmd   analysis/' + (py ? 'octavo_helper.py' : 'octavo.R'),
                       '  data/   assets/   requirements.txt');
            } else if (p === 'paper') {
                L.push('  papers/' + n + '/paper.md   main.typ');
            } else if (p === 'slides') {
                L.push('  slides/' + n + '.md');
            } else {
                L.push('  lectures/' + n + '.md');
            }
        }
        return L.join('\n');
    }

    function refresh() {
        for (const p of PARTS) {
            $('part-' + p).classList.toggle('off', !checked('use-' + p));
        }
        $('where-row').style.display = radio('mode') === 'new' ? '' : 'none';
        $('name-row').style.display = radio('mode') === 'new' ? '' : 'none';
        $('summary').textContent = summary();
        $('note').textContent = checked('use-analysis') ? words.envNote : '';
        const bad = problems();
        for (const el of document.querySelectorAll('input[type=text]')) {
            el.classList.remove('bad');
        }
        // 入力しかけの欄を赤くはしない（作ろうとして初めて示す）
        $('create').disabled = busy;
    }

    function create() {
        const bad = problems();
        $('error').textContent = '';
        if (bad.length) {
            for (const id of bad) $(id).classList.add('bad');
            $('error').textContent = words.fix;
            return;
        }
        busy = true;
        $('create').disabled = true;
        $('create').textContent = words.working;
        vscode.postMessage({
            type: 'create',
            data: {
                mode: radio('mode'),
                where: $('where').value,
                name: $('name').value.trim(),
                lang: radio('lang'),
                engine: radio('engine'),
                parts: chosen().map((p) => ({ kind: p, name: partName(p) })),
                example: checked('example'),
            },
        });
    }

    for (const el of document.querySelectorAll('input')) {
        el.addEventListener('input', refresh);
        el.addEventListener('change', refresh);
    }
    $('browse').addEventListener('click', () => vscode.postMessage({ type: 'browse' }));
    $('create').addEventListener('click', create);
    $('cancel').addEventListener('click', () => vscode.postMessage({ type: 'cancel' }));

    window.addEventListener('message', (e) => {
        const m = e.data;
        if (m.type === 'where') {
            $('where').value = m.path;
            refresh();
        } else if (m.type === 'failed') {
            busy = false;
            $('create').textContent = words.create;
            $('error').textContent = m.message;
            refresh();
        }
    });
    refresh();
    vscode.postMessage({ type: 'ready' });
})();
