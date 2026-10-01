// 表の編集画面（tableEditor.ts の webview）。行と列を編集して、行の配列を送り返すだけ。
// CSV の読み書きは拡張機能の側（tableEditor.ts）がする。
(function () {
    const vscode = acquireVsCodeApi();
    const words = JSON.parse(document.body.dataset.words || '{}');
    const grid = document.getElementById('grid');
    let rows = [['']];
    let cur = { r: 0, c: 0 };
    let timer = null;

    const width = () => (rows[0] || []).length;

    function send(now) {
        clearTimeout(timer);
        const go = () => vscode.postMessage({ type: 'edit', rows });
        if (now) go(); else timer = setTimeout(go, 250);
    }

    // 見出しの結合（handtables.py と同じ決まり: 中身のあるセルの右隣の空セル）。
    // 結合があるのは tables/ の表だけ。data/ の CSV は1行目が列の名前で、空なら空のまま
    function merged(c) {
        if (!words.merges) return false;
        const top = rows[0];
        if (!top[c]) {
            for (let k = c - 1; k >= 0; k--) {
                if (top[k]) return true;
            }
        }
        return false;
    }
    function headRows() {
        const any = rows[0].some((_, c) => merged(c));
        return any && rows.length > 2 ? 2 : 1;
    }

    function fit(ta) {
        ta.style.height = 'auto';
        ta.style.height = ta.scrollHeight + 'px';
    }

    function colChars(c) {
        // 「← 結合」の印が入る列は、その幅も取る
        let n = merged(c) ? 2 * String(words.merge || '').length : 4;
        for (const r of rows) {
            for (const line of String(r[c]).split('\n')) {
                let w = 0;
                for (const ch of line) w += ch.charCodeAt(0) > 0x2e7f ? 2 : 1;
                n = Math.max(n, w);
            }
        }
        return Math.min(n + 1, 44);
    }

    function cellAt(r, c) {
        return grid.querySelector(`textarea[data-r="${r}"][data-c="${c}"]`);
    }

    function focusCell(r, c) {
        const ta = cellAt(r, c);
        if (ta) {
            ta.focus();
            cur = { r, c };
        }
    }

    function refreshHead() {
        const head = headRows();
        grid.querySelectorAll('tr').forEach((tr, r) => tr.classList.toggle('head', r < head));
        for (let c = 0; c < width(); c++) {
            const ta = cellAt(0, c);
            if (ta) ta.placeholder = merged(c) ? words.merge : '';
        }
    }

    function render() {
        const active = document.activeElement;
        const hadFocus = active && active.tagName === 'TEXTAREA';
        grid.textContent = '';
        const cols = [];
        for (let c = 0; c < width(); c++) cols.push(colChars(c));
        rows.forEach((row, r) => {
            const tr = document.createElement('tr');
            const num = document.createElement('th');
            num.textContent = String(r + 1);
            tr.appendChild(num);
            row.forEach((v, c) => {
                const td = document.createElement('td');
                const ta = document.createElement('textarea');
                ta.rows = 1;
                ta.cols = cols[c];
                ta.value = v;
                ta.dataset.r = String(r);
                ta.dataset.c = String(c);
                ta.spellcheck = false;
                td.appendChild(ta);
                tr.appendChild(td);
            });
            grid.appendChild(tr);
        });
        grid.querySelectorAll('textarea').forEach(fit);
        refreshHead();
        cur.r = Math.min(cur.r, rows.length - 1);
        cur.c = Math.min(cur.c, width() - 1);
        if (hadFocus) focusCell(cur.r, cur.c);
    }

    function pos(ta) {
        return { r: Number(ta.dataset.r), c: Number(ta.dataset.c) };
    }

    grid.addEventListener('focusin', (e) => {
        if (e.target.tagName === 'TEXTAREA') cur = pos(e.target);
    });

    grid.addEventListener('input', (e) => {
        const ta = e.target;
        if (ta.tagName !== 'TEXTAREA') return;
        const p = pos(ta);
        rows[p.r][p.c] = ta.value;
        fit(ta);
        if (p.r === 0) refreshHead();
        send(false);
    });

    grid.addEventListener('keydown', (e) => {
        const ta = e.target;
        if (ta.tagName !== 'TEXTAREA' || e.key !== 'Enter' || e.isComposing) return;
        e.preventDefault();
        const p = pos(ta);
        if (e.altKey) {
            // セルの中の改行（Excel と同じ Alt+Enter）
            const a = ta.selectionStart;
            ta.value = ta.value.slice(0, a) + '\n' + ta.value.slice(ta.selectionEnd);
            ta.selectionStart = ta.selectionEnd = a + 1;
            ta.dispatchEvent(new Event('input', { bubbles: true }));
            return;
        }
        if (e.shiftKey) {
            focusCell(Math.max(0, p.r - 1), p.c);
            return;
        }
        if (p.r === rows.length - 1) {
            rows.push(Array(width()).fill(''));
            render();
            send(true);
        }
        focusCell(p.r + 1, p.c);
    });

    // Excel からコピーした範囲（タブ区切り。セルの中の改行は "…" で囲まれる）
    function parseTsv(text) {
        const out = [];
        let row = [];
        let cell = '';
        let quoted = false;
        const s = text.replace(/\r\n?/g, '\n').replace(/\n$/, '');
        for (let i = 0; i < s.length; i++) {
            const ch = s[i];
            if (quoted) {
                if (ch === '"' && s[i + 1] === '"') { cell += '"'; i++; }
                else if (ch === '"') quoted = false;
                else cell += ch;
            } else if (ch === '"' && cell === '') quoted = true;
            else if (ch === '\t') { row.push(cell); cell = ''; }
            else if (ch === '\n') { row.push(cell); out.push(row); row = []; cell = ''; }
            else cell += ch;
        }
        row.push(cell);
        out.push(row);
        return out;
    }

    grid.addEventListener('paste', (e) => {
        const ta = e.target;
        if (ta.tagName !== 'TEXTAREA') return;
        const text = (e.clipboardData && e.clipboardData.getData('text/plain')) || '';
        if (!/[\t\n]/.test(text.replace(/\r?\n$/, ''))) return;   // 1つのセルならそのまま
        e.preventDefault();
        const block = parseTsv(text);
        const p = pos(ta);
        const need = p.c + Math.max(...block.map((r) => r.length));
        rows.forEach((r) => { while (r.length < need) r.push(''); });
        while (rows.length < p.r + block.length) rows.push(Array(width()).fill(''));
        block.forEach((line, i) => line.forEach((v, j) => { rows[p.r + i][p.c + j] = v; }));
        render();
        focusCell(p.r, p.c);
        send(true);
    });

    function swap(list, a, b) {
        const t = list[a];
        list[a] = list[b];
        list[b] = t;
    }

    const actions = {
        'row-add': () => { rows.splice(cur.r + 1, 0, Array(width()).fill('')); cur.r += 1; },
        'col-add': () => { rows.forEach((r) => r.splice(cur.c + 1, 0, '')); cur.c += 1; },
        'row-del': () => { if (rows.length > 1) rows.splice(cur.r, 1); },
        'col-del': () => { if (width() > 1) rows.forEach((r) => r.splice(cur.c, 1)); },
        'row-up': () => { if (cur.r > 0) { swap(rows, cur.r, cur.r - 1); cur.r -= 1; } },
        'row-down': () => { if (cur.r < rows.length - 1) { swap(rows, cur.r, cur.r + 1); cur.r += 1; } },
        'col-left': () => { if (cur.c > 0) { rows.forEach((r) => swap(r, cur.c, cur.c - 1)); cur.c -= 1; } },
        'col-right': () => { if (cur.c < width() - 1) { rows.forEach((r) => swap(r, cur.c, cur.c + 1)); cur.c += 1; } },
    };
    Object.keys(actions).forEach((id) => {
        document.getElementById(id).addEventListener('click', () => {
            actions[id]();
            render();
            focusCell(cur.r, cur.c);
            send(true);
        });
    });
    document.getElementById('as-text').addEventListener('click',
        () => vscode.postMessage({ type: 'text' }));

    window.addEventListener('message', (e) => {
        const m = e.data;
        if (m.type !== 'rows') return;
        const bad = document.getElementById('garbled');
        bad.textContent = m.garbled ? words.garbled : '';
        bad.style.display = m.garbled ? 'block' : 'none';
        grid.classList.toggle('locked', !!m.garbled);
        grid.querySelectorAll('textarea').forEach((ta) => { ta.readOnly = !!m.garbled; });
        // 自分の送った変更が戻ってきただけなら描き直さない（入力中のカーソルを保つ）
        if (JSON.stringify(m.rows) === JSON.stringify(rows)) return;
        rows = m.rows.length ? m.rows : [['']];
        render();
        grid.querySelectorAll('textarea').forEach((ta) => { ta.readOnly = !!m.garbled; });
    });

    vscode.postMessage({ type: 'ready' });
})();
