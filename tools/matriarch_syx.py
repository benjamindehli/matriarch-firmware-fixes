# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Benjamin Dehli
"""Read and patch Moog Matriarch firmware .syx files.

Format (reverse engineered from v1.3.0):
  F0 04 17 <payload> F7    -- one SysEx message, Moog (04), Matriarch (17)
  payload = 00-padding + records. A record starts with byte 01, then N triplets.
  triplet = [0x40 | b15..b12] [b11..b6] [b5..b0]  -> one 16-bit word
  header record: 0012 0010 ... with its checksum at word 14
  data record:   0013 0088 0080 0000 addrLo addrHi cksum <128 data words> 0000
  cksum = sum of all other words in the record (mod 2^16).
  Addresses are TI C28x word addresses (the image loads at 0x88000).

Patching works in place on the original file: only the triplets of the records
that change are re-encoded, so every other byte stays identical to Moog's file.
"""

import struct

CKSUM_INDEX = {0x12: 14, 0x13: 6}


def decode_word(b0, b1, b2):
    return ((b0 & 0x0F) << 12) | (b1 << 6) | b2


def encode_word(w):
    return bytes((0x40 | (w >> 12), (w >> 6) & 0x3F, w & 0x3F))


class Record:
    def __init__(self, offset, words):
        self.offset = offset  # file offset of the first triplet byte
        self.words = words

    @property
    def cmd(self):
        return self.words[0]

    @property
    def addr(self):
        return self.words[4] | (self.words[5] << 16)

    @property
    def length(self):
        return self.words[2]

    def checksum_ok(self):
        k = CKSUM_INDEX[self.cmd]
        return (sum(self.words) - self.words[k]) & 0xFFFF == self.words[k]

    def fix_checksum(self):
        k = CKSUM_INDEX[self.cmd]
        self.words[k] = (sum(self.words) - self.words[k]) & 0xFFFF


class Firmware:
    def __init__(self, path):
        with open(path, 'rb') as f:
            self.raw = bytearray(f.read())
        if self.raw[:3] != b'\xf0\x04\x17' or self.raw[-1] != 0xF7:
            raise ValueError('not a Matriarch firmware SysEx file')
        self.records = []
        d, i = self.raw, 1
        while i < len(d) - 1:
            if d[i] == 0x01 and 0x40 <= d[i + 1] < 0x80:  # a final lone 01 precedes F7
                j, words = i + 1, []
                while j + 2 < len(d) - 1 and 0x40 <= d[j] < 0x80:
                    words.append(decode_word(d[j], d[j + 1], d[j + 2]))
                    j += 3
                self.records.append(Record(i + 1, words))
                i = j
            else:
                i += 1
        bad = [r for r in self.records if not r.checksum_ok()]
        if bad:
            raise ValueError(f'{len(bad)} records with bad checksum')

    @property
    def version(self):
        """Firmware version from the header record, e.g. '1.3.0'."""
        header = self.records[0].words
        return f'{header[6]}.{header[7]}.{header[8]}'

    def data_records(self):
        return [r for r in self.records if r.cmd == 0x13]

    def _locate(self, addr):
        for r in self.data_records():
            if r.addr <= addr < r.addr + r.length:
                return r, 7 + addr - r.addr
        raise KeyError(f'address 0x{addr:x} not in image')

    def read(self, addr, n=1):
        out = []
        for a in range(addr, addr + n):
            r, k = self._locate(a)
            out.append(r.words[k])
        return out

    def write(self, addr, words):
        touched = set()
        for a, w in zip(range(addr, addr + len(words)), words):
            r, k = self._locate(a)
            r.words[k] = w
            touched.add(id(r))
        for r in self.records:
            if id(r) in touched:
                r.fix_checksum()
                self.raw[r.offset : r.offset + 3 * len(r.words)] = b''.join(encode_word(w) for w in r.words)

    def image(self):
        mem = {}
        for r in self.data_records():
            for k in range(r.length):
                mem[r.addr + k] = r.words[7 + k]
        lo, hi = min(mem), max(mem) + 1
        return lo, b''.join(struct.pack('<H', mem.get(a, 0xFFFF)) for a in range(lo, hi))

    def save(self, path):
        with open(path, 'wb') as f:
            f.write(self.raw)
