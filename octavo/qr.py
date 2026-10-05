# -*- coding: utf-8 -*-
"""QR コード（ポスターの題の帯に置く URL 用）。標準ライブラリだけで作る。

バイトモード・誤り訂正レベル M・型番 1〜40 の自動選択・8つのマスクから減点の最も
少ないものを選ぶ、という QR の規格（JIS X 0510 / ISO/IEC 18004）の基本の形だけを
持つ。出力は SVG（黒い正方形の並び。周りに4モジュールの余白）で、Typst が image()
で読める。アルゴリズムの組み立ては Project Nayuki の QR Code generator（MIT）に
ならった。
"""
from __future__ import annotations

# 誤り訂正レベル M のブロックごとの訂正語数と、ブロックの数（型番 1〜40。0 番目は使わない）
_ECC_PER_BLOCK = (0, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28,
                  26, 26, 26, 26, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28,
                  28, 28, 28, 28, 28)
_BLOCKS = (0, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5, 5, 8, 9, 9, 10, 10, 11, 13, 14, 16, 17, 17,
           18, 20, 21, 23, 25, 26, 28, 29, 31, 33, 35, 37, 38, 40, 43, 45, 47, 49)
_FORMAT_M = 0          # 誤り訂正レベル M の形式情報の2ビット


class QRError(ValueError):
    pass


def _raw_modules(ver: int) -> int:
    """データに使えるモジュールの数（機能パターンを除く）。"""
    n = (16 * ver + 128) * ver + 64
    if ver >= 2:
        k = ver // 7 + 2
        n -= (25 * k - 10) * k - 55
        if ver >= 7:
            n -= 36
    return n


def _data_codewords(ver: int) -> int:
    return _raw_modules(ver) // 8 - _ECC_PER_BLOCK[ver] * _BLOCKS[ver]


# ---------------------------------------------------------------- リード・ソロモン

def _gf_mul(x: int, y: int) -> int:
    z = 0
    for i in reversed(range(8)):
        z = (z << 1) ^ ((z >> 7) * 0x11D)
        z ^= ((y >> i) & 1) * x
    return z


def _rs_divisor(degree: int) -> list:
    out = [0] * (degree - 1) + [1]
    root = 1
    for _ in range(degree):
        for j in range(degree):
            out[j] = _gf_mul(out[j], root)
            if j + 1 < degree:
                out[j] ^= out[j + 1]
        root = _gf_mul(root, 0x02)
    return out


def _rs_remainder(data: list, divisor: list) -> list:
    out = [0] * len(divisor)
    for b in data:
        factor = b ^ out.pop(0)
        out.append(0)
        for i, coef in enumerate(divisor):
            out[i] ^= _gf_mul(coef, factor)
    return out


# ---------------------------------------------------------------- 符号化

def _codewords(text: str) -> tuple:
    """(型番, 誤り訂正を足して並べ替えた全語)。"""
    data = text.encode('utf-8')
    for ver in range(1, 41):
        count_bits = 8 if ver <= 9 else 16
        need = 4 + count_bits + 8 * len(data)
        if need <= _data_codewords(ver) * 8:
            break
    else:
        raise QRError('too long for a QR code')
    cap = _data_codewords(ver) * 8
    bits = [0, 1, 0, 0]                                    # バイトモード
    bits += [(len(data) >> i) & 1 for i in reversed(range(count_bits))]
    for b in data:
        bits += [(b >> i) & 1 for i in reversed(range(8))]
    bits += [0] * min(4, cap - len(bits))                  # 終端
    bits += [0] * (-len(bits) % 8)
    pad = 0xEC
    while len(bits) < cap:
        bits += [(pad >> i) & 1 for i in reversed(range(8))]
        pad ^= 0xEC ^ 0x11
    words = [int(''.join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]

    # ブロックに分け、それぞれに誤り訂正語を付けて、交互に並べる
    nblocks, ecc = _BLOCKS[ver], _ECC_PER_BLOCK[ver]
    raw = _raw_modules(ver) // 8
    short = nblocks - raw % nblocks
    short_len = raw // nblocks
    div = _rs_divisor(ecc)
    blocks, k = [], 0
    for i in range(nblocks):
        n = short_len - ecc + (0 if i < short else 1)
        dat = words[k:k + n]
        k += n
        rem = _rs_remainder(dat, div)
        if i < short:
            dat = dat + [0]                                # 長さをそろえる（後で飛ばす）
        blocks.append(dat + rem)
    out = []
    for i in range(len(blocks[0])):
        for j, b in enumerate(blocks):
            if i != short_len - ecc or j >= short:
                out.append(b[i])
    return ver, out


class _Matrix:
    def __init__(self, ver: int):
        self.ver = ver
        self.size = ver * 4 + 17
        self.mod = [[False] * self.size for _ in range(self.size)]
        self.fn = [[False] * self.size for _ in range(self.size)]

    def set_fn(self, x, y, dark):
        self.mod[y][x] = dark
        self.fn[y][x] = True

    def function_patterns(self):
        s = self.size
        for i in range(s):                                 # タイミングパターン
            self.set_fn(6, i, i % 2 == 0)
            self.set_fn(i, 6, i % 2 == 0)
        for cx, cy in ((3, 3), (s - 4, 3), (3, s - 4)):   # 位置検出パターン
            for dy in range(-4, 5):
                for dx in range(-4, 5):
                    x, y = cx + dx, cy + dy
                    if 0 <= x < s and 0 <= y < s:
                        d = max(abs(dx), abs(dy))
                        self.set_fn(x, y, d not in (2, 4))
        pos = self._align_positions()                      # 位置合わせパターン
        n = len(pos)
        for i in range(n):
            for j in range(n):
                if (i == 0 and j == 0) or (i == 0 and j == n - 1) or (i == n - 1 and j == 0):
                    continue
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        self.set_fn(pos[i] + dx, pos[j] + dy, max(abs(dx), abs(dy)) != 1)
        self.format_bits(0)                                # 場所だけ取っておく
        self.version_bits()

    def _align_positions(self) -> list:
        if self.ver == 1:
            return []
        n = self.ver // 7 + 2
        step = (self.ver * 8 + n * 3 + 5) // (n * 4 - 4) * 2
        out = [self.size - 7 - i * step for i in range(n - 1)] + [6]
        return out[::-1]

    def format_bits(self, mask: int):
        data = _FORMAT_M << 3 | mask
        rem = data
        for _ in range(10):
            rem = (rem << 1) ^ ((rem >> 9) * 0x537)
        bits = (data << 10 | rem) ^ 0x5412
        b = lambda i: (bits >> i) & 1 != 0
        s = self.size
        for i in range(6):
            self.set_fn(8, i, b(i))
        self.set_fn(8, 7, b(6))
        self.set_fn(8, 8, b(7))
        self.set_fn(7, 8, b(8))
        for i in range(9, 15):
            self.set_fn(14 - i, 8, b(i))
        for i in range(8):
            self.set_fn(s - 1 - i, 8, b(i))
        for i in range(8, 15):
            self.set_fn(8, s - 15 + i, b(i))
        self.set_fn(8, s - 8, True)                        # 常に黒のモジュール

    def version_bits(self):
        if self.ver < 7:
            return
        rem = self.ver
        for _ in range(12):
            rem = (rem << 1) ^ ((rem >> 11) * 0x1F25)
        bits = self.ver << 12 | rem
        for i in range(18):
            dark = (bits >> i) & 1 != 0
            a, b = self.size - 11 + i % 3, i // 3
            self.set_fn(a, b, dark)
            self.set_fn(b, a, dark)

    def place(self, words: list):
        bits = [(w >> (7 - i)) & 1 for w in words for i in range(8)]
        i = 0
        s = self.size
        right = s - 1
        while right >= 1:
            if right == 6:
                right = 5
            for vert in range(s):
                for j in range(2):
                    x = right - j
                    upward = ((right + 1) & 2) == 0
                    y = s - 1 - vert if upward else vert
                    if not self.fn[y][x] and i < len(bits):
                        self.mod[y][x] = bits[i] == 1
                        i += 1
            right -= 2

    def apply_mask(self, mask: int):
        for y in range(self.size):
            for x in range(self.size):
                if self.fn[y][x]:
                    continue
                flip = (
                    (x + y) % 2 == 0, y % 2 == 0, x % 3 == 0, (x + y) % 3 == 0,
                    (x // 3 + y // 2) % 2 == 0, x * y % 2 + x * y % 3 == 0,
                    (x * y % 2 + x * y % 3) % 2 == 0, ((x + y) % 2 + x * y % 3) % 2 == 0,
                )[mask]
                if flip:
                    self.mod[y][x] = not self.mod[y][x]

    def penalty(self) -> int:
        s, m = self.size, self.mod
        score = 0
        lines = [row for row in m] + [[m[y][x] for y in range(s)] for x in range(s)]
        for line in lines:
            run, prev = 0, None
            for v in line:
                if v == prev:
                    run += 1
                else:
                    if run >= 5:
                        score += run - 2
                    run, prev = 1, v
            if run >= 5:
                score += run - 2
            # 位置検出パターンに似た並び（1:1:3:1:1 と前後の白4つ）
            seq = ''.join('1' if v else '0' for v in line)
            for pat in ('10111010000', '00001011101'):
                start = seq.find(pat)
                while start != -1:
                    score += 40
                    start = seq.find(pat, start + 1)
        for y in range(s - 1):
            for x in range(s - 1):
                v = m[y][x]
                if v == m[y][x + 1] == m[y + 1][x] == m[y + 1][x + 1]:
                    score += 3
        dark = sum(v for row in m for v in row)
        total = s * s
        k = (abs(dark * 20 - total * 10) + total - 1) // total - 1
        score += k * 10
        return score


def matrix(text: str) -> list:
    """QR コードのモジュール（True が黒）の2次元の並び。"""
    ver, words = _codewords(text)
    best, best_score = None, None
    for mask in range(8):
        q = _Matrix(ver)
        q.function_patterns()
        q.place(words)
        q.apply_mask(mask)
        q.format_bits(mask)
        score = q.penalty()
        if best_score is None or score < best_score:
            best, best_score = q, score
    return best.mod


def svg(text: str, border: int = 4) -> str:
    """QR コードの SVG。1モジュール = 1 単位（大きさは置く側が決める）。"""
    m = matrix(text)
    n = len(m) + border * 2
    path = ''.join(f'M{x + border} {y + border}h1v1h-1z'
                   for y, row in enumerate(m) for x, v in enumerate(row) if v)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {n} {n}" '
            f'shape-rendering="crispEdges"><rect width="{n}" height="{n}" fill="#fff"/>'
            f'<path d="{path}" fill="#000"/></svg>\n')
