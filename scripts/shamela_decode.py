#!/usr/bin/env python3
"""Extract stored-field text from Maktaba Shamela Linux (shamela.ws) Lucene .fdt files.

Usage: python3.14 shamela_decode.py <path-to-.fdt> [more.fdt ...]

Stage 1 (working): locate LZ4-compressed stored-field blobs inside each .fdt by
brute-force scan and check the Arabic text ratio.
Stage 2 (next): structured parse of the Lucene90 chunk/packed-ints layout so we
can map outputs to (book_key, page) instead of raw blob order.
"""
import struct, sys

def lz4_block(src, i, maxout=1 << 20):
    out = bytearray()
    n = len(src)
    while i < n:
        tok = src[i]; i += 1
        lit = tok >> 4
        if lit == 15:
            while True:
                b = src[i]; i += 1; lit += b
                if b < 255: break
        out += src[i:i + lit]; i += lit
        if i >= n: break
        off = src[i] | (src[i + 1] << 8); i += 2
        if not 0 < off <= len(out): raise ValueError('bad offset')
        ml = tok & 0xF
        if ml == 15:
            while True:
                b = src[i]; i += 1; ml += b
                if b < 255: break
        ml += 4
        st = len(out) - off
        for j in range(ml):
            out.append(out[st + j])
            if len(out) > maxout: raise ValueError('runaway')
    return bytes(out)

def extract(path):
    data = open(path, 'rb').read()
    assert data[0:4] == b'\x3f\xd7\x6c\x17', 'not a Lucene stored-fields file'
    ln = data[4]
    name = data[5:5 + ln].decode()
    ver = struct.unpack('>i', data[5 + ln:9 + ln])[0]
    print(f'== {path}: codec={name} version={ver} size={len(data)}')
    blobs = 0
    p = 9 + ln
    N = len(data)
    while p < N - 10:
        try:
            blob = lz4_block(data, p)
        except Exception:
            p += 1; continue
        arabic = sum(1 for b in blob if 0xd8 <= b <= 0xdb)
        if len(blob) > 50 and arabic / max(1, len(blob)) > 0.2:
            blobs += 1
            first = blob[:80].decode('utf-8', 'replace').replace('\n', ' ')
            print(f'   blob@{p} ({len(blob)}B): {first}')
        p += 1
    print(f'   -> {blobs} text blobs found')
    return blobs

if __name__ == '__main__':
    for path in sys.argv[1:]:
        extract(path)
