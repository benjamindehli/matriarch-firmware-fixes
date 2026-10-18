// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Benjamin Dehli
//
// Read and patch Moog Matriarch firmware .syx files. A port of tools/matriarch_syx.py,
// see that file for the format description. Patching works in place: only the records
// that change are re-encoded, so every other byte stays identical to Moog's file.

const CKSUM_INDEX = { 0x12: 14, 0x13: 6 };

function decodeWord(b0, b1, b2) {
    return ((b0 & 0x0f) << 12) | (b1 << 6) | b2;
}

function encodeWord(w) {
    return [0x40 | (w >> 12), (w >> 6) & 0x3f, w & 0x3f];
}

function sum16(words, skip) {
    let s = 0;
    words.forEach((w, i) => {
        if (i !== skip) s += w;
    });
    return s & 0xffff;
}

export class FirmwareError extends Error {}

export class Firmware {
    /** @param {ArrayBuffer | Uint8Array} bytes The contents of a .syx file. Not modified. */
    constructor(bytes) {
        const d = new Uint8Array(bytes).slice();
        if (d.length < 8 || d[0] !== 0xf0 || d[d.length - 1] !== 0xf7) {
            throw new FirmwareError("This isn't a SysEx file.");
        }
        if (d[1] !== 0x04 || d[2] !== 0x17) {
            throw new FirmwareError("This SysEx file isn't Matriarch firmware.");
        }
        this.raw = d;
        this.records = [];
        let i = 1;
        while (i < d.length - 1) {
            // A final lone 01 precedes F7, so require a triplet start byte after it.
            if (d[i] === 0x01 && d[i + 1] >= 0x40 && d[i + 1] < 0x80) {
                let j = i + 1;
                const words = [];
                while (j + 2 < d.length - 1 && d[j] >= 0x40 && d[j] < 0x80) {
                    words.push(decodeWord(d[j], d[j + 1], d[j + 2]));
                    j += 3;
                }
                this.records.push({ offset: i + 1, words });
                i = j;
            } else {
                i += 1;
            }
        }
        if (this.records.length === 0 || this.records[0].words[0] !== 0x12) {
            throw new FirmwareError("This SysEx file isn't Matriarch firmware.");
        }
        const bad = this.records.filter((r) => !Firmware.checksumOk(r)).length;
        if (bad) {
            throw new FirmwareError(`The file is damaged: ${bad} records have a bad checksum.`);
        }
    }

    static checksumOk(record) {
        const k = CKSUM_INDEX[record.words[0]];
        return k !== undefined && sum16(record.words, k) === record.words[k];
    }

    /** Firmware version from the header record, e.g. "1.3.0". */
    get version() {
        const h = this.records[0].words;
        return `${h[6]}.${h[7]}.${h[8]}`;
    }

    dataRecords() {
        return this.records.filter((r) => r.words[0] === 0x13);
    }

    locate(addr) {
        for (const r of this.dataRecords()) {
            const start = r.words[4] | (r.words[5] << 16);
            if (addr >= start && addr < start + r.words[2]) return [r, 7 + addr - start];
        }
        throw new FirmwareError(`Address 0x${addr.toString(16)} isn't in the firmware image.`);
    }

    read(addr, n = 1) {
        const out = [];
        for (let a = addr; a < addr + n; a++) {
            const [r, k] = this.locate(a);
            out.push(r.words[k]);
        }
        return out;
    }

    write(addr, words) {
        const touched = new Set();
        words.forEach((w, i) => {
            const [r, k] = this.locate(addr + i);
            r.words[k] = w;
            touched.add(r);
        });
        for (const r of touched) {
            const k = CKSUM_INDEX[r.words[0]];
            r.words[k] = sum16(r.words, k);
            r.words.forEach((w, n) => this.raw.set(encodeWord(w), r.offset + 3 * n));
        }
    }

    /** The (possibly patched) file contents. */
    bytes() {
        return this.raw.slice();
    }
}
